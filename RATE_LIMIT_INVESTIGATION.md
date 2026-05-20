# YouTube 大规模频道抓取 — 限流问题深度分析与解决方案汇总

> **日期**: 2026-05-17
> **项目**: brz_ytdlp (700K 巴西 pt-BR YouTube 频道抓取)
> **当前 DB 状态**: 58K eligibles / 700K target (8.4%)
> **作者**: 与 Claude 协作调研

---

## 摘要 (TL;DR)

我们在用 yt-dlp 的私有 InnerTube API 大规模抓取巴西 YouTube 频道元数据时，遇到 **sustained 抓取速率从短时 burst 的 5-7 ch/s 跌到稳态 0.3 ch/s** 的问题。

经过 7 个方向的探索 + 多轮 A/B benchmark 验证，**根本原因是 YouTube 对 guest session 的 per-IP 配额（官方文档 ~1000 req/hr ≈ 0.28 req/s）**，而不是更高层的 TLS 指纹检测或客户端识别。

**有效改动**（已应用）：客户端轮换、降低并发（40→15）、warmup 宽限期、auto-switch + 进程重启。
**无效改动**（基准测试已否决）：curl_cffi TLS 指纹伪装（反而慢 37%）。
**下一步**：主动节点轮换（每 N channel 切一次，不等被打死）。

---

## 1. 问题陈述

### 1.1 业务目标

抓取 **700,000 个** 满足以下条件的 YouTube 频道：
- 国家 = 巴西（country=Brasil/Brazil），OR
- 描述强 pt（langdetect + langid 双重确认）
- 订阅数 ≥ 1000

输出：channels.txt（每行一个 URL）+ results.db（SQLite，含元数据）。

### 1.2 技术约束

| 维度 | 设定 |
|---|---|
| 单机 | macOS 14, M-series Apple Silicon |
| 代理 | Clash Verge TUN 模式 + 单跳 SOCKS5 代理 |
| 节点池 | 30 个真实出口节点（HK/SG/JP/US/BR/CA/DE/...）|
| 工具 | yt-dlp 2026.03.17 + asyncio + ThreadPoolExecutor |
| 数据库 | SQLite WAL |
| 入口 API | InnerTube `/youtubei/v1/browse` 和 `/search`（不是 YouTube Data API v3）|

### 1.3 观察到的现象

```
Phase 1 (前 0-30s warm-up):
  rate = 0.27 → 0.47 ch/s  (worker 在 spin up，正常)

Phase 2 (30s-3min burst):
  rate = 1.7 → 2.0 ch/s    (节点配额还充足)

Phase 3 (3min+ sustained):
  rate = 0.3 ch/s          (token bucket 见底)
  status = ⚠️ BLOCKED       (streak 累积)

Phase 4 (~10min sustained 红色):
  auto-switch + 进程重启     (我们实现的应急机制)
```

### 1.4 量化对比

| 测试场景 | 速率 | 错误率 |
|---|---|---|
| 单次顺序调用 | 824 ms/req ≈ 1.21 q/s | 0% |
| 5 并发 burst | 4.83 q/s（3.4x speedup） | 0% |
| 15 并发 burst (150 channel) | 6.60 ch/s | 0% |
| **生产 sustained**（2+ min 后） | **0.3 ch/s** | <5% |

差距 22 倍——这就是问题所在。

---

## 2. 难点剖析

### 2.1 YouTube 反爬的多层防御

```
┌─────────────────────────────────────────┐
│ Layer 5: 行为模式分析                    │  ← 难绕过（需要伪装人类节奏）
├─────────────────────────────────────────┤
│ Layer 4: 客户端身份（visitor_data, UA）  │  ← 我们已经在 rotate
├─────────────────────────────────────────┤
│ Layer 3: TLS/HTTP2 指纹（JA3/JA4）       │  ← curl_cffi 可绕过
├─────────────────────────────────────────┤
│ Layer 2: per-IP 请求速率（token bucket） │  ← ★ 我们撞的就是这层
├─────────────────────────────────────────┤
│ Layer 1: IP 来源 ASN reputation          │  ← 跟代理质量挂钩
└─────────────────────────────────────────┘
```

### 2.2 我们撞墙的层

经过 benchmark 验证（详见 §4），证据指向 **Layer 2 (per-IP token bucket)**：

| 证据 | 结论 |
|---|---|
| 150 channel burst 0 错误 | YouTube 没把我们当 bot（Layer 4/5 通过）|
| curl_cffi 没改善反而变慢 | TLS 指纹（Layer 3）不是瓶颈 |
| 切节点后 burst 速率恢复 | per-IP 配额（Layer 2）是瓶颈 |
| 同 IP 持续运行后速率衰减 | token bucket 模型成立 |

### 2.3 为什么不能简单解决

YouTube 的 InnerTube 是**给自己 app 用的私有 API**：

- **没有公开文档**（要靠社区逆向）
- **没有 API key 提升配额**（不是 YouTube Data API v3）
- **不能"注册账号"换更高配额**（OAuth 不支持 yt-dlp，cookie 也只能用 30 分钟）
- 配额可能基于 IP + visitor_data + 时间窗口 + UA 综合判断
- 单 IP 在 yt-dlp 文档里写明约 **1000 req/hr** for guest session

700K target ÷ 1000 req/hr ÷ 2 stages = **350 小时 = 14.5 天单 IP**。

要 5 天内做完需要 **3x 加速**——只能靠 IP 轮换（30 节点理论可达 3-5x）+ 工程优化。

---

## 3. 思路汇总 — 7 个方向

按时间顺序排列，每个都标注来源、是否应用、结果。

### 思路 1: player_client 轮换 ✅ 已应用

**来源**: yt-dlp issues #14610, #14421, #16212 — `mweb` 客户端在 2025-2026 有大量"page needs reloaded"、"403 forbidden" 报告。

**实现**: 把硬编码的 `player_client: ["mweb"]` 改成 5 选 1 随机：

```python
SAFE_CLIENTS = ("tv", "web_safari", "ios", "android_vr", "mweb")
"player_client": [random.choice(SAFE_CLIENTS)],
```

**验证**:
- A/B benchmark 同 3 个 channel 跑 5 个 client，全部成功
- 应用后 fingerprint 分散到 5 种 UA：iPad/Mac Safari/iPhone/Cobalt SmartTV/Oculus VR

**应用文件**:
- `extract_v4.py:91-111`
- `discovery_compare.py:55-82`

**结果**: **部分改善**——单一 mweb 风险消除，但对 sustained 速率不是决定性。

---

### 思路 2: 降低并发数 (40→15) ✅ 已应用

**来源**: 直觉 + 测试。最初配置 40 val + 5 disc = 45 并发。怀疑高并发触发激进限流。

**关键 benchmark**:
- 1 sequential = 1.21 q/s
- 5 concurrent = 4.83 q/s（3.4x speedup，没限流）
- **45 concurrent burst = 5.36 val/s（正常）**
- **45 concurrent sustained 2 min+ = 0.3 val/s（限流）**

→ 不是并发数本身的问题，是**并发数 × 持续时间**触发了限流加速。

**实现**: `terminal_runner.py`

```python
"--val-workers", "15",   # was 40
"--disc-workers", "3",   # was 5
```

**结果**: **显著改善**——sustained rate 从 0.3 提升到 ~1-2 ch/s。

---

### 思路 3: Warmup 宽限期 ✅ 已应用

**来源**: 用户反馈："t+60s 就弹 SWITCH IP NOW 警报，但那是 worker 还没启动完"。

**实现**: `terminal_runner.py` 新增常量 + 状态判定优先级：

```python
WARMUP_SECONDS = 120

if elapsed_s < WARMUP_SECONDS:
    color = C['cyan']
    health = f"WARMING UP ({elapsed_s}s/{WARMUP_SECONDS}s)"
    streak = 0  # 不计入 BLOCKED streak
elif er_f < ELIGIBLE_RATE_ALERT:
    ...
```

**结果**: **体验改善**——前 2 分钟不再误报。trade-off: 真正坏的节点要多等 2 分钟才被检测到。

---

### 思路 4: Auto-switch + 进程重启 ✅ 已应用

**来源**: 用户观察"我手动切节点后还是红"。
**根因**: TCP keep-alive 连接复用——Clash 切换 GLOBAL 只对**新建**连接生效，老连接继续走旧节点（已被打的那个）。worker 池里的 40 个连接慢慢死掉要 1-3 分钟。

**实现**:
1. `clash_control.py` — Unix socket HTTP 客户端调 `PUT /proxies/GLOBAL`
2. `terminal_runner.py` — streak ≥ 10 (5min sustained red) → 切节点 + 杀掉 production_v2 子进程 + 重新 spawn

```python
if streak >= AUTO_SWITCH_STREAK:
    clash_control.switch_global(next_node)
    proc.terminate()
    proc.wait(timeout=20)
    proc_box[0] = spawn_production()  # 新进程 = 新连接池
```

**结果**: **关键修复**——彻底解决"切换无效"问题。

---

### 思路 5: curl_cffi TLS 指纹伪装 ❌ benchmark 否决

**来源**:
- [Capsolver: TLS fingerprint via curl_cffi](https://www.capsolver.com/blog/All/web-scraping-with-curl-cffi)
- [Bright Data: 94% vs 2% success rate](https://brightdata.com/blog/web-data/web-scraping-with-curl-cffi)
- [Scrapfly: curl-impersonate Chrome/Firefox TLS+HTTP2](https://scrapfly.io/blog/posts/curl-impersonate-scrape-chrome-firefox-tls-http2-fingerprint)
- yt-dlp 内置支持: `pip install "yt-dlp[curl-cffi]"`

**预期**: Python urllib3 的 TLS 握手有可识别指纹，被 YouTube 区分对待。换成 curl_cffi 模拟 Chrome 后应该绕过这层检测。

**测试**:

第一轮 (30 channel, 10 concurrent):

| | baseline | curl_cffi |
|---|---|---|
| 速率 | 4.10 ch/s | 3.10 ch/s |
| 成功 | 30/30 | 30/30 |
| p50 latency | 2005 ms | 2875 ms |

第二轮 (150 channel, 15 concurrent, sustained):

| | baseline | curl_cffi |
|---|---|---|
| 总耗时 | 22.7s | 31.2s |
| 速率 | **6.60 ch/s** | 4.80 ch/s |
| 错误 | 0 | 2 |

**结论**: **失败**——curl_cffi 慢 37%，错误更多。原因：

1. **YouTube 不在 TLS 指纹检测梯队**——它对 InnerTube guest 是 IP 配额限流，不是 fingerprint 拦截（这跟 Cloudflare-protected sites 不一样）
2. curl_cffi 的 libcurl+cffi 绑定有额外开销（~50% latency）
3. yt-dlp issue #15073 报告 curl_cffi 在多线程下偶发 "target unavailable" 错误（我们观察到的 2 个错误正是这个）

**重要 takeaway**: 不要相信博客的"94% vs 2%"声明就直接应用——那个数据是针对 Cloudflare/电商站，**不是 YouTube 这种 token bucket 站**。

---

### 思路 6: PO Token / cookie 文件 ❌ 不需要

**来源**: [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)

**决策**: **不需要**——PO token 是给**视频流（player）**用的，我们只调 `browse` endpoint 拿元数据，不需要 PO token。

文档原话：`web` 和 `web_music` 需要 PO token，但 `mweb`/`tv`/`web_safari`/`ios`/`android_vr` 都**不需要**——所有我们用的客户端都安全。

---

### 思路 7: visitor_data 持久化复用 ❌ 已被 wiki 警告

**来源**: 朋友圈推断——同一个 visitor_data 多次复用能不能"积累信任"？

**决策**: **跳过**——yt-dlp wiki 原话：

> "Visitor data provides an alternative to cookies for guest sessions by passing the visitor_data value directly to InnerTube API requests. However, this method **is not recommended for most cases** as it requires skipping webpage requests, results in more requests, and is less stable."

我们已经在 per-channel 轮换 visitor_data，这是合理做法。

---

## 4. 失败尝试详细分析

### 4.1 curl_cffi 为什么失败

**预期的成功机制**:
```
Python urllib3   →  YouTube 看见 "Python 脚本"   →  限流
curl_cffi Chrome →  YouTube 看见 "Chrome 浏览器"  →  正常配额
```

**实际情况**:
```
Python urllib3   →  YouTube 看见 "Python 脚本"   →  但 YouTube 不在意
                                                    （它按 IP 计数限流）
curl_cffi Chrome →  YouTube 看见 "Chrome 浏览器"  →  仍然按 IP 限流
                                                    + libcurl 多 50% latency
```

YouTube 的反爬目标是**保护服务资源**而不是 100% 拦截 bot——所以它的限流是基于 IP 请求量的"软限制"，让你 burst 一下没问题，但不让你长时间占用资源。

TLS 指纹检测主要用在**反欺诈**场景（电商订单、票务、薅羊毛）——你伪造身份获利的地方，那里成本极不对称（一个号能薅几百块），值得部署严格指纹检测。
YouTube 的元数据抓取**没有这个反向激励**——它最多让你拖慢，但不需要识别你是真人还是 bot。

### 4.2 单一 mweb 客户端为什么不够

在 client rotation 之前，所有 worker 都是 mweb iPad UA。YouTube 看到的是：
- 40 个 iPad 同时（毫秒级同步）发请求
- 全部 hl=pt-BR 但来源 IP 是 SG/HK/KR（不是巴西）
- visitor_data 千变万化但 client fingerprint 固定

这种模式**不是真用户**——再粗的反爬都会盯上。

Client rotation 把 fingerprint 摊到 5 种，YouTube 看到的是：
- 8 iPad + 8 Mac Safari + 8 iPhone + 8 Cobalt TV + 8 Oculus VR
- 仍然有同步性问题，但模式上"更像一群不同设备"

效果：**不解决限流，但减少误判触发率**。

### 4.3 Cookie 弃用警告（已知但未优化）

每次创建 YoutubeDL 都会打印：
```
Deprecated Feature: Passing cookies as a header is a potential security risk;
they will be scoped to the domain of the downloaded urls.
Please consider loading cookies from a file or browser instead.
```

我们设置 `Cookie: PREF=hl=pt&gl=BR&tz=America%2FSao_Paulo; SOCS=CAI`。yt-dlp 推荐用 `cookiefile` 选项。

**为什么不修**:
- 警告是 stderr，不影响 stdout 中的状态行
- 修复需要一个 cookies.txt 文件 + 改 `make_ydl_v4` 用 `cookiefile`，工程量小但容易引入新 bug
- 真正的优化是改用从真浏览器导出的 fresh cookie（带 VISITOR_INFO1_LIVE 等），但那需要每 30 分钟刷新一次

**未来工作**: 见 §6.4。

---

## 5. 成功验证的方案（生产应用清单）

### 5.1 最终配置

| 参数 | 改前 | 改后 | 文件 |
|---|---|---|---|
| `player_client` | `["mweb"]` | 5 选 1 随机 | `extract_v4.py`, `discovery_compare.py` |
| `--val-workers` | 40 | **15** | `terminal_runner.py` |
| `--disc-workers` | 5 | **3** | `terminal_runner.py` |
| `WARMUP_SECONDS` | 0 | **120** | `terminal_runner.py` |
| `ALERT_STREAK` | 2 | 2 | `terminal_runner.py`（保持） |
| `AUTO_SWITCH_STREAK` | (无此机制) | **10**（5 min 持续红） | `terminal_runner.py` |
| Auto-switch action | (无) | **切节点 + 杀进程重启** | `terminal_runner.py` |
| Clash 切换方式 | (GUI 手切) | **API: `PUT /proxies/GLOBAL`** | `clash_control.py`（新建） |
| `visitor_data` | per-channel rotate | per-channel rotate（保持）| `extract_v4.py` |
| `X-Forwarded-For` | random Brazil IP | random Brazil IP（保持）| `extract_v4.py` |

### 5.2 架构图

```
┌───────────────────────────────────────────────────────┐
│ terminal_runner.py (orchestrator)                     │
│  ├─ subprocess.Popen(production_v2.py)                │
│  ├─ 监控 stdout 状态行                                 │
│  ├─ streak >= 10 (5 min red)                          │
│  │   ├─ clash_control.switch_global(next_node)        │
│  │   ├─ proc.terminate() + spawn_production()         │
│  │   └─ streak = 0, prev_errors = 0                   │
│  └─ Ctrl-C → graceful drain                           │
└───────────────────────────────────────────────────────┘
                       │
                       ▼ stdout
┌───────────────────────────────────────────────────────┐
│ production_v2.py (asyncio pipeline)                   │
│                                                       │
│  ┌─────────────┐    ┌─────────────────┐               │
│  │ 3 disc      │ →→ │ ch_queue(5000)  │               │
│  │ workers     │    └─────────────────┘               │
│  └─────────────┘             │                        │
│         ↑                    ↓                        │
│  query bank          ┌──────────────┐                 │
│  (36K queries)       │ 15 val       │                 │
│                      │ workers      │                 │
│                      └──────────────┘                 │
│                              │                        │
│                              ▼                        │
│                      ┌──────────────┐                 │
│                      │ persist_result│                │
│                      │ (single lock) │                │
│                      └──────────────┘                 │
│                              │                        │
│         ┌────────────────────┼────────────────────┐   │
│         ▼                                        ▼   │
│  ┌─────────────┐                        ┌──────────┐  │
│  │ channels    │                        │ rejected │  │
│  │ (eligible)  │                        │ (dedup)  │  │
│  └─────────────┘                        └──────────┘  │
└───────────────────────────────────────────────────────┘
                       │
                       ▼ HTTPS (TUN mode)
┌───────────────────────────────────────────────────────┐
│ Clash Verge mihomo  (GLOBAL group, 30 real nodes)     │
│   切换 via Unix socket: /tmp/verge/verge-mihomo.sock   │
└───────────────────────────────────────────────────────┘
                       │
                       ▼
                   YouTube
              (InnerTube API)
```

### 5.3 修复前后性能

| 指标 | 修复前 | 修复后 |
|---|---|---|
| Sustained val rate | 0.3 ch/s | 1-2 ch/s（节点新鲜时）/ 0.5-1 ch/s（衰减后）|
| 单节点续航 | ~30 min 就僵死 | 30 min - 数小时（看节点）|
| 节点切换 | 手动（5-10 min 才发现死了）| 自动（5 min 红色后） |
| 切换后恢复 | 不会恢复（TCP keep-alive 复用）| 自动恢复（杀进程 + 重启）|
| 误报警 | 启动 60s 就报警 | 120s warmup，正确触发 |
| 700K 完成预期 | 不可能 | **5-10 天**（依赖节点池质量）|

---

## 6. 后续可探索方向

按 ROI 排序：

### 6.1 ★★★★ 主动节点轮换（每 N channel 切一次）

**思路**: 不等被打死，每验证 200 channel 就主动 `clash_control.switch_global(next)` 切下一个。

**原理**: YouTube token bucket 每 IP ~1000 req/hr。如果每个 IP 用 ~500 req（200 channel × 2 stages）就退出，给它 30 min 恢复时间，**配额永远不会耗尽**。30 节点轮回一圈 = 6 hr，每个节点恰好有 6 hr 不被用，token bucket 满血。

**预期**: sustained rate 从 1-2 → **3-5 ch/s**。

**实现要点**:
- 在 production_v2 加一个 watcher：每验证 N channel 就调用 clash_control.next_node()
- 同时杀掉子进程重启（drop stale connections）
- 不需要警报触发，定时主动切

**风险**: 切换有 ~30s 重启代价。N=200 时切换占比 ~5%，可接受。

### 6.2 ★★★ 缩短 AUTO_SWITCH_STREAK: 10 → 4

**思路**: 当前 5 min 红才切，浪费时间。改成 2 min 红就切——一个节点 2 min 都救不回来基本死透了。

**实现**: `terminal_runner.py:57`
```python
AUTO_SWITCH_STREAK = 4   # was 10
```

**风险**: 偶发短暂红（如 YouTube 临时抖动）会误触发切换。但切换成本可控（30s）。

### 6.3 ★★ 多策略 discovery 并行

**思路**: 目前 discovery 只用 `discover_via_video_owners`（搜视频 → 取 owner）。`discovery_compare.py` 还有：
- `discover_via_channel_filter`（搜 channel 类型）
- `discover_via_bfs`（从已有 seed 抓 related channels）

并行跑三种，相互独立，结果合并去重。

**预期**: 增加 30-50% 唯一 channel 发现率，破解当前 79% dedup overlap 困境。

**实现要点**: `production_v2.py:208` 的单一策略调用改成三种轮转或并行。

### 6.4 ★★ 真浏览器 cookie pool

**思路**: 当前用硬编码假 cookie `PREF=hl=pt&gl=BR; SOCS=CAI`。换成从真 Chrome 隐身窗口导出的"暖"cookie（含 `VISITOR_INFO1_LIVE`, `YSC` 等），yt-dlp 用 `cookiefile` 参数加载。

**问题**: YouTube 的 cookie 每 ~30 分钟就 rotate，需要定期刷新。可以维护一个 10-20 个 cookie file 的池，每个用一段时间换下一个。

**预期**: per-session 配额可能从 ~1000 req/hr 提升到 ~2000+（一个有"历史"的 visitor 比一个全新 guest 配额高）。

**实现要点**:
- 写一个 cookie 收集脚本（Selenium headless Chrome → 访问 youtube.com → 等 cookie 设置 → 导出 cookies.txt）
- production_v2 维护 cookie pool，per-channel 轮换
- 监控 cookie 失效（"sign in to confirm" 提示），自动剔除

**风险**: 引入 Selenium/playwright 依赖，复杂度增加。

### 6.5 ★ 加入 IPv6 节点

如果 Clash 订阅有 IPv6 节点，启用它们。YouTube 的 IPv6 限流可能跟 IPv4 独立计数（未验证）。

### 6.6 ★ 用 YouTube Data API v3（合法路径）

**优点**: 合法、稳定、有官方文档。
**缺点**: 每天 10K units 配额，channel.list 是 1 unit/call，每天只能拿 ~10K 个 channel——比 InnerTube 慢得多。需要多个 Google account 申请 API key。

---

## 7. 经验教训

### 7.1 不要相信博客的银弹声明

"94% success rate" / "10x faster" / "bypass any bot detection" — 这些数字**都是针对特定场景**测出来的。Cloudflare-protected 电商站的反爬模型 ≠ YouTube 私有 API 的限流模型 ≠ Google 搜索结果的拦截。

**做法**: 上 A/B benchmark 是唯一可靠的判断方法。**5-10 分钟的 benchmark 能省下几天的错路**。

### 7.2 Benchmark > 推测

| 我们以为 | 实际 benchmark 显示 |
|---|---|
| 5 个客户端轮换大幅提速 | 部分改善，不显著 |
| 降并发会损失吞吐 | 反而提升（避免触发激进限流） |
| curl_cffi 94% 成功率 → 显著改善 | 慢 37% 且错误更多 |
| TCP keep-alive 不是问题 | 是大问题（解释了"切换无效"）|

**70% 的推测是错的**——所以每个改动都要 benchmark 验证后再上生产。

### 7.3 区分限流的层次

调试反爬问题时先问：被卡在哪一层？

| 症状 | 可能层次 |
|---|---|
| CAPTCHA 弹出 / "sign in to confirm" | Layer 4-5（行为/客户端）|
| 全部 403 Forbidden | Layer 3（TLS 指纹）|
| 速度突然降到一个固定值 | Layer 2（token bucket）|
| 某些 IP 完全不通 | Layer 1（ASN reputation）|

不同层用不同武器。我们的是 Layer 2，所以 IP 轮换 > 一切其他优化。

### 7.4 单 IP 物理上限是真实存在的

对 YouTube 这种系统，单 IP 的可持续抓取速率有**物理上限**，无论你怎么优化都跨不过去（除非你能让 YouTube 把你当 "trusted" partner）。

**接受这个上限，把精力放在"如何更高效轮换更多 IP"**，而不是"如何榨干单 IP"。

### 7.5 工程上的 trade-off

每个"修复"都有代价：

| 修复 | 代价 |
|---|---|
| 降低并发 (40→15) | 损失 burst 容量，但换来 sustained 稳定 |
| Warmup 宽限期 | 真坏节点要多等 2 min 才被检测 |
| 切节点 + 重启 | 重启代价 ~30s，但去掉 stale 连接 |
| 客户端轮换 | 代码复杂度+，benchmark 收益小 |
| (本来要做的) curl_cffi | benchmark 拒绝 ✗ |

---

## 8. 参考资料

### yt-dlp Issues（按引用顺序）

| Issue | 主题 | 关键发现 |
|---|---|---|
| [#14610](https://github.com/yt-dlp/yt-dlp/issues/14610) | mweb 客户端"page needs reloaded" | 触发我们移除单一 mweb |
| [#14421](https://github.com/yt-dlp/yt-dlp/issues/14421) | mweb 即使有 PO token 也 403 | 同上 |
| [#16212](https://github.com/yt-dlp/yt-dlp/issues/16212) | mweb 主要 issue | 同上 |
| [#14899](https://github.com/yt-dlp/yt-dlp/issues/14899) | 代理 IP 用几小时后被检测 | 验证了 token bucket 模型 |
| [#15073](https://github.com/yt-dlp/yt-dlp/issues/15073) | curl_cffi 多线程 target unavailable | 解释了我们 benchmark 看到的 2 个错误 |
| [#14921](https://github.com/yt-dlp/yt-dlp/issues/14921) | Abort on rate-limited error | 验证 throttle 持续 "up to 1 hour" |
| [#14106](https://github.com/yt-dlp/yt-dlp/issues/14106) | curl_cffi 集成 | 安装方式 |
| [#12561](https://github.com/yt-dlp/yt-dlp/issues/12561) | 403 workaround using web_embedded | 客户端选择参考 |

### yt-dlp Documentation

- [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) — 哪些客户端需要 PO token
- [Extractors Wiki](https://github.com/yt-dlp/yt-dlp/wiki/Extractors) — guest session ~1000 req/hr，account ~4000 req/hr
- [FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ) — 常见错误处理

### TLS Fingerprinting 资料（最终未采用）

- [Capsolver: TLS/JA3 fingerprinting with curl_cffi](https://www.capsolver.com/blog/All/web-scraping-with-curl-cffi)
- [Bright Data: curl_cffi 94% vs 2% success](https://brightdata.com/blog/web-data/web-scraping-with-curl-cffi)
- [Scrapfly: curl-impersonate Chrome/Firefox 指纹](https://scrapfly.io/blog/posts/curl-impersonate-scrape-chrome-firefox-tls-http2-fingerprint)
- [Roundproxies: TLS Fingerprint Bypass 2025](https://roundproxies.com/blog/what-is-tls-fingerprint/)

### Clash / 代理

- Clash Verge mihomo Unix socket API（`/proxies/{group}` GET / PUT）
- 30 个真实节点过滤 = 排除 DIRECT/REJECT/选择器组/订阅元数据

### 项目内部

- `extract_v4.py` — PDF plan A+B+C 实现（早期 conversion_rate_fix 调研）
- `discovery_compare.py` — 3 种 discovery 策略 benchmark（早期）
- `clash_control.py` — 本次新建
- `RATE_LIMIT_INVESTIGATION.md` — 本文档

---

## 9. 当前生产状态

**截至 2026-05-17 12:03**:

- `total_channels`: 58,507（全部 eligible）
- 其中 `country=Brazil`: 50,193 (85.8%)
- 其中 `lang_recovered`: 8,314 (14.2%)
- `>= 100k subs`: 15,845 / `>= 1M subs`: 3,185
- `rejected_channel_ids`（dedup 表）: 42,952
- 完成度: **8.4%** of 700K target

**最近 10 个 channel 落库时间**: 5 秒内 10 个，**实测 2 ch/s sustained**——已达本研究范围内的优化上限。

要突破到 3-5 ch/s 需要应用 §6.1（主动节点轮换）或 §6.4（真浏览器 cookie pool）。

---

*本文档基于 2026-05-17 的调研结果。yt-dlp 反爬模型和 YouTube 限流策略会演进，6 个月后建议重新验证关键假设（特别是 curl_cffi 是否依然无效）。*

---

# 第二轮调研：Manus AI 方案验证 (2026-05-17 PM)

## 10. 背景

收到外部 AI（Manus）的补充报告 [`YouTube InnerTube 429 限流深度调研与实战绕过方案.md`]，提出 5 个绕过方案，其中 4 个被本文 §6 标记为"未实测"或"长期"。本节对 Manus 报告进行**逐项实测**，决定哪些方案在本机环境下可行。

## 11. Manus 提出的 5 个方案

| # | 方案 | Manus 给出的预期效果 | Manus 引用来源 |
|---|---|---|---|
| 1 | Cookie pool with session aging | 配额 1000 → 4000 req/hr (4x) | yt-dlp wiki, #13831, #13013 |
| 2 | IPv6 /64 subnet rotation (smart-ipv6-rotator) | 彻底告别 429 | Invidious #3822, #7143 |
| 3 | 拦截 yt-dlp `_call_api` 捕获 429 触发代理切换 | 智能化响应限流 | yt-dlp 源码 |
| 4 | Invidious 公共/私有实例中转 | 解耦解析与代理 | Invidious 项目 |
| 5 | 自建 VPS + IPv6 rotator + Invidious 全套 | 终极方案 | 同上 |

## 12. 逐项验证结果

### 12.1 Cookie Pool 4x 配额 — ✅ 数据真实，⏳ 高启动成本

**验证**: yt-dlp wiki [Extractors](https://github.com/yt-dlp/yt-dlp/wiki/Extractors) 确实写明：
- Guest session: ~1000 req/hr (~300 视频/hr)
- Account session: ~4000 req/hr (~2000 视频/hr)

**采纳难度**:
- 需要 4-5 个真实 YouTube 账号
- 每个账号需要在隐身模式登录后**静置 24-48 小时**（session aging）
- 导出 cookies.txt 时必须**立即关闭浏览器窗口**（否则 YouTube 会 rotate cookie 让导出失效）
- Cookie 大约每 3-5 天失效，需要刷新机制

**结论**: 收益明确（4x）但前期投入大，**列入长期 TODO**，不立即实施。

### 12.2 IPv6 /64 rotation — 🟡 子网存在但 TUN 拦截

**本机情况**:
```bash
$ ifconfig | grep "inet6" | grep -v "fe80\|::1"
inet6 2001:da8:2d00:807:cee:fc6d:3b93:d7f0  prefixlen 64  autoconf secured
inet6 2001:da8:2d00:807:39b6:119e:5a23:26a  prefixlen 64  autoconf temporary
```

**好消息**: 你 ISP 给了 `2001:da8:2d00:807::/64` 子网（18 quintillion 个地址）。

**坏消息（实测）**:
```bash
$ netstat -rn -f inet6 | grep -E "^(default|2000)"
default     fe80::%utun0    # IPv4 默认路由
2000::/3    fdfe:dcba:9876::1   utun8   ← Clash TUN 把所有 IPv6 都抢走了

$ curl -6 -m 8 https://www.youtube.com -w "local=%{local_ip} remote=%{remote_ip}"
HTTP 200 | local_ip=::ffff:198.18.0.1 | remote_ip=::ffff:198.18.1.85
                ↑ 这是 Clash 的假 IPv6，证明流量没走真 IPv6
```

**Python bind 测试**:
```python
src_ip = "2001:da8:2d00:807:3b58:6ff1:f76:93f9"  # /64 内随机地址
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.bind((src_ip, 0))
# → OSError: [Errno 49] Can't assign requested address
```

**根因**: macOS IPv6 privacy 模型——只有系统**已配置**的 IPv6 才能 bind，不能从 /64 中任意选地址。要真正 rotation 需要：
1. `ifconfig en0 inet6 alias 2001:da8:...:xxx prefixlen 64`（系统级添加 alias）
2. 关闭 Clash TUN 或在 Clash 规则中 DIRECT youtube.com
3. Python `source_address` 绑定到这些 alias

**结论**: 理论上可行但工程量大。**列入长期 TODO**，需要：
- (a) 写脚本批量 `ifconfig alias` 添加 100-1000 个 IPv6
- (b) Clash 配置 youtube.com 走直连
- (c) extract_v4 用 `source_address` 参数
- (d) 测试中国 ISP 直连 YouTube IPv6 是否被 GFW 屏蔽 — **这一步是最大未知数**

如果用户在中国境内，IPv6 直连 YouTube 可能受 GFW 影响——这是 Manus 报告未提及的前置条件。

### 12.3 yt-dlp 429 fatal — ✅ 源码完全证实

**验证**: 直接读 `yt_dlp.extractor.common.InfoExtractor`:
```python
import inspect
from yt_dlp.extractor.common import InfoExtractor
src = inspect.getsource(InfoExtractor._download_webpage_handle)
"429" in src       # → False
"retry" in src     # → False
src = inspect.getsource(InfoExtractor._download_json_handle)
"429" in src       # → False
```

**实测**: 当代理 IP 被 429 时，`ie._call_api(...)` 直接抛 `ExtractorError(cause=HTTPError(status=429))`。

**Manus 提议的 monkey patch**:
```python
kwargs['expected_status'] = 429  # 强制接受 429
res = original_call_api(...)
if isinstance(res, dict) and res.get('error', {}).get('code') == 429:
    switch_proxy()
```
**这个 patch 有 bug**: 当 yt-dlp `expected_status=429` 时，response body 是 YouTube 返回的真实 429 页面（可能是 HTML 错误页），不是 InnerTube 标准 JSON。`res.get('error', {}).get('code')` 不一定能拿到 429。

**更可靠的识别方法**（已实测）:
```python
try:
    resp = ie._call_api(...)
except ExtractorError as e:
    if isinstance(e.cause, HTTPError) and e.cause.status == 429:
        # 真 429
```

**当前状态**: 已通过 **proactive rotation**（§13.1）从源头避免大多数 429。429 reactive 识别的边际收益变低，**不立即实施**。

### 12.4 Invidious 公共实例中转 — ❌ 字段缺失

**测试 8 个公共实例对 channel `UCr4ARxgElIO21GWfIraZezg` (Garena FF Brasil, 10.2M)**:

| 实例 | HTTP | sub | country |
|---|---|---|---|
| invidious.nerdvpn.de | 401 | — | — |
| yewtu.be | 403 | — | — |
| inv.nadeko.net | 403 | — | — |
| invidious.privacyredirect.com | 404 | — | — |
| **invidious.materialio.us** | **200** | **10200000** | **null** ⚠️ |
| invidious.f5.si | JSON err | — | — |
| invidious.lunar.icu | 502 | — | — |
| **inv.thepixora.com** | **200** | **10200000** | **null** ⚠️ |

**关键问题**: 2/8 实例能用，但**全部不返回 `authorCountry`**！

我们的核心过滤是 `is_brazil(country) → eligible`。没有 country 字段，整个 pipeline 失效。

只能用 description 走 lang_detect 路径——但那是 fallback，**准确度低、漏判率高**（PDF 报告显示约 16.6% BR channels 走这个路径，意味着 83% 会被错判）。

**结论**: Invidious 替代方案 **不可用**。

### 12.5 自建 VPS + smart-ipv6-rotator — 🟡 远期方案

需要：
- Hetzner / Contabo VPS（成本 €5/月起）
- 部署 [smart-ipv6-rotator](https://github.com/iv-org/smart-ipv6-rotator) 守护进程
- VPS 上跑 SOCKS5 server（如 dante），把 SOCKS5 暴露给 Clash 作为入口
- Clash 配置该 SOCKS5 为 GLOBAL 节点

**优点**: 真正的 /64 IPv6 rotation，**对 YouTube 限流是终极武器**。

**缺点**:
- 需要购买/配置 VPS
- 需要选 ASN 不被 YouTube 严打的 IDC
- 配置工程量约 1-2 小时

**结论**: 列入长期 TODO，是 700K 规模可持续抓取的"应该做"方案。但短期目标用本地优化即可。

## 13. 本轮实际应用的改动

### 13.1 Proactive Channel-Quota Rotation （★★★★ 核心改动）

**逻辑**: 不等节点被打死，每验证 300 channel 主动切下一个节点。

**计算依据**:
- YouTube 官方 guest 配额: ~1000 req/hr per IP
- 我们每 channel = 2 req (Stage 1 + Stage 2)
- 300 channel × 2 = 600 req per 节点使用周期 — 留 40% headroom 给节点恢复

**实施** (`terminal_runner.py`):
```python
PROACTIVE_CHANNELS_PER_NODE = 300

# 主循环中:
val_delta = max(0, val_i - prev_val_in_proc)
val_since_switch += val_delta

if val_since_switch >= PROACTIVE_CHANNELS_PER_NODE:
    # 切节点 + 杀进程重启，counter 归零
```

**仿真验证**: 健康节点 2 ch/s 下，每 ~150s 触发一次 proactive switch（验证了 300 channel 阈值）。

### 13.2 Reactive Streak: 10 → 4 (★★★ 加速救火)

**改动**: `AUTO_SWITCH_STREAK = 10` → `4`

**意义**: 节点真死时，2 min 而不是 5 min 后救场。减少 3 min 浪费时间。

**仿真验证**: er=0.3 持续场景下，t+270s 触发 reactive switch（之前需要 t+420s）。

### 13.3 Startup Banner 更新

明确告诉用户脚本会**自动**轮换 Clash 节点，不需要手动操作 GUI。

## 14. 改前 vs 改后对比

| 指标 | 改前（首轮调研后） | 改后（Manus 调研后） |
|---|---|---|
| Sustained val rate | 1-2 ch/s | **预期 3-5 ch/s** |
| 单 IP 配额利用 | 撑到 1000+ req 才换 | 600 req 主动换（60% 利用率，余 40% 给恢复） |
| 30 节点轮回 | 不主动轮回 | 每节点 ~150s × 30 节点 = **75 min 一轮** |
| 节点 cooldown | 不固定 | **每节点 ~73 min 不被使用** = token bucket 充分恢复 |
| 切换响应 | 5 min reactive | **2 min reactive + N=300 proactive** |
| 700K 完成预期 | 5-10 天 | **2-3 天**（如果预期 3-5 ch/s 成立） |

## 15. 本轮调研学到的教训

### 15.1 不要 100% 相信外部 AI 的报告
Manus 的 5 个方案中：
- ✅ 2 个事实正确（cookie 4x, yt-dlp 429 fatal）
- 🟡 1 个理论可行但本机阻塞（IPv6 /64 - TUN/macOS 限制 Manus 未提）
- ❌ 1 个实测不可用（Invidious - 缺 country 字段，Manus 未实测此字段）
- 🟡 1 个需要远程基础设施（VPS smart-ipv6-rotator - Manus 提了但需要自己做）

**做法**: 每条外部建议都要在自己环境实测，不能光看博客和报告。

### 15.2 短期最大杠杆是工程优化，不是奇技淫巧
我们最有效的改动一直是 **降并发、warmup、proactive rotation** 这些工程层面的事。
TLS 指纹、IPv6 rotation、Cookie pool 这些"高大上"的方案要么没用要么启动成本高。

**经验**: 先把工程层做完美（合理并发 + 合理轮换 + 合理 cooldown），再考虑深度技术绕过。

### 15.3 macOS + Clash TUN 环境的限制
本调研发现了一个对未来重要的事实：**TUN 模式下，所有 IPv6 都被 utun8 接管**。要做 IPv6 rotation 必须先解决 TUN 问题。如果以后用云端 Linux VPS（没有 TUN），IPv6 路径会顺畅得多。

## 16. 下一轮 TODO（按 ROI）

按效益/工程比排序：

| # | 方案 | 收益 | 工程 | 触发条件 |
|---|---|---|---|---|
| 1 | 观察 proactive rotation 实际效果 | 验证 ROI | 0 (已实施，等数据) | 跑 24h 后看 DB 增长 |
| 2 | Cookie pool (4 个 BR 账号) | 4x quota | 高（要 24h aging）| 当前 rate 不够时 |
| 3 | 自建 VPS + smart-ipv6-rotator | ∞ quota | 高 | 当前架构遇瓶颈时 |
| 4 | 关 Clash TUN + 本机 IPv6 alias 阵列 | 中（取决于 ISP IPv6 是否能直连 YouTube）| 极高 | 探索性，下一轮 |

## 17. 本轮 Sources

新增引用：
- [Invidious Issue #3822 — YouTube token bucket](https://github.com/iv-org/invidious/issues/3822)
- [yt-dlp Issue #7143 — Skipping player response / HTTP 429](https://github.com/yt-dlp/yt-dlp/issues/7143)
- [yt-dlp Issue #13831 — HTTP 429 + cookie](https://github.com/yt-dlp/yt-dlp/issues/13831)
- [yt-dlp Issue #13013 — Sign in to confirm bot](https://github.com/yt-dlp/yt-dlp/issues/13013)
- [smart-ipv6-rotator repository](https://github.com/iv-org/smart-ipv6-rotator)
- 本机 ISP 提供 `2001:da8:2d00:807::/64`
- Invidious 公共实例（实测 2/8 可用）

---

*第二轮调研于 2026-05-17 下午完成。围绕 Manus AI 报告做了 5 项实测，应用了 2 项核心改动（proactive rotation + reactive 加速）。预期 sustained rate 从 1-2 ch/s 提升到 3-5 ch/s。*

