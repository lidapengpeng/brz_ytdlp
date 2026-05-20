# Long-Term Research Index — `brz_ytdlp` 700K BR YouTube 抓取项目

> 日期: 2026-05-19
> 文件夹: `/Users/dapeng/Desktop/word/brz_ytdlp/long_term_research/`
> 目的: 长期专项调研档案，每个主题对应一个文档，可持续迭代细化

---

## 项目当前状态快照（2026-05-19）

| 维度 | 现状 |
|---|---|
| DB 中 eligibles | ~59,000 |
| 目标 | 700,000 |
| 完成度 | **8.4%** |
| 当前 sustained eligible rate | **4.86 e/s**（单 IP，已修 shuffle bug 后）|
| 历史峰值 | 9.77 e/s (DB ~10K 时期) |
| 主要瓶颈 | per-IP token bucket（YouTube guest ~1000 req/hr）+ dedup overlap 81% |

---

## 4 个长期研究方向

### 📘 [05 — Query Bank 多样性](05_query_bank_diversity.md)
**问题**: 当前 36K queries 是字母后缀变体（`X` + `X canal` + `X brasil` + `X oficial`）的笛卡尔积，**91% 是冗余变体**，造成 81% dedup 重叠率。

**核心发现**:
- YouTube Suggest API 实测：94 个种子单层调用产出 1,165 新 queries，**1,132 (97.2%) 不在现有 bank 中**
- 三层 BFS suggest 扩展 + 巴西文化 taxonomy + hashtag 挖矿，预期 dedup 81% → 30-50%

**预期收益**: e/s 4.86 → **8-10**，700K 完成时间 40 天 → **16-24 天**

**Quick Wins**: 已可立即落地 §5.1（`expand_via_suggest.py` BFS + 删除冗余后缀）

---

### 📘 [06 — BFS Discovery（从已有 BR seeds 扩展）](06_bfs_discovery.md)
**问题**: query-based discovery 撞 dedup 墙，需要开辟全新 cid 池。

**v1 核心发现**:
- ⚠️ **`/channels` tab 已被 YouTube 废弃**（`params=EghjaGFubmVscw==` 等同 home tab）—— yt-dlp 源码确认
- 实测 41 个真实 BR seed × 38 new cids，**BR 转化率 63.2%**（vs query-based 12%）—— **4-5x 效率**
- 中型 seed (10K-100K subs) 的 related 比 huge seed 更稀有

**v2 扩展（2026-05-19 PM 第二轮）**:
- 调研 [anvaka/allytrelated](https://github.com/anvaka/allytrelated)（pre-2023 BFS 覆盖 3M channel 的先行项目）
- 实测 `FEwhat_to_watch`/`FEtrending`/`FEexplore`/`FEtopics` 全部不可用（200 但空 / 400）
- 输出 **7 个新测试方案矩阵 (A-G)**，按 ROI 排序

**v3 全部 7 方案实测落地（2026-05-19 晚）**:
- ✅ 实测 7 个方案，留 4 个砍 3 个
- 🏆 **方案 A (watchEndpoint + lockupViewModel)**: **10.8 new/seed (3.32x v1 baseline)** —— v2 最佳新发现
- ✅ **方案 B (YouTube Music BR)**: 98 unique new cid per scan from 3 endpoints
- 🟡 方案 C (depth-2): 28-58% 衰减，mid 可考虑、huge 不值
- 🗑 方案 D/E/F/G 全部 ≤0 boost（client/locale、widget、sitemap、playlist）—— 砍
- 17 个脚本 + JSON dump 持久化在 `v2_experiments/` 

**预期收益**: v1 +25-35K, **加 v3 方案 A 后再 +100K** (基于 10.8/seed × 57K seeds × 40% BR conv)

**集成成本**: v1 ~70 行；v3 watchnext ~120 行；v3 music_scanner ~80 行

---

### 📘 [07 — Cookie Pool（账号 Cookie 池）](07_cookie_pool.md)
**问题**: guest session 1000 req/hr，account session 4000 req/hr（**理论 4x**）。

**核心发现**:
- 实际预期 sustained **2x 而不是 4x**（IP layer limits 仍然存在）
- 2026 年 cookie 寿命**已恶化到 3-5 天**（yt-dlp issue #13964），auto-refresh 必须
- 完整 Playwright PoC 脚本（incognito 登录 + 立即关闭 context）含在文档
- SQLite cookie_pool schema + `extract_v4.py:make_ydl_v4()` 加 `cookiefile` 参数

**结论**: Plan B —— **优先 IPv6 rotation（§08），cookie pool 不立即上**

**前置准备**: 代码改造（让 `make_ydl_v4` 支持 cookiefile）可以先做，未来切换零成本

---

### 📘 [08 — IPv6 /64 VPS 轮换](08_ipv6_vps_rotation.md)
**问题**: 本机 macOS + Clash TUN 路径行不通（路由表+bind 限制），需要 VPS 方案。

**核心发现**:
- ⚠️ Manus 推荐的 `smart-ipv6-rotator` **不适合**（12h 才换 1 静态地址，不是 per-connection）
- ✅ **正确方案**: **Hetzner CAX11 (€3.79/月) + TREVORproxy AnyIP 模式 + ssh -L 隧道**
- TREVORproxy 用 Linux AnyIP 把整个 /64 作为本机所有地址池，**每个 SOCKS5 connection 随机绑定一个 /128**
- ⚠️ **重要**: YouTube 按 /64 段限流（不是单 /128），"18 quintillion IP" 是夸大

**预期收益**: 单 VPS +5-10 e/s for $4/月；3 台地理分散 = **+15-30 e/s aggregate**

**集成成本**: **零代码改动**（本机 brz_ytdlp 不需要改，只在 Clash 加节点）

---

## 综合优先级矩阵（ROI 排序）

| # | 主题 | 工程量 | 收益 | 何时做 |
|---|---|---|---|---|
| **6** | BFS Discovery | **低**（~70 行）| **中-高**（25-35K 新 eligibles）| **本周** |
| **5** | Query Bank 扩充 | 中（脚本 + 重组）| 中（dedup 81→50%）| **本周** |
| **8** | IPv6 /64 VPS rotation | 中-高（VPS + 部署）| **极高**（+15-30 e/s）| **2-3 周内** |
| **7** | Cookie Pool | 高（账号 + Playwright + maint）| 中（2x，预期 +5 e/s）| 6+ 后（Plan B）|

**建议落地顺序**:
1. **本周**: 跑 BFS（§06）+ 扩 query bank（§05 §5.1 quick wins）—— 单 IP 上 e/s 从 4.86 推到 ~8-10
2. **2-3 周**: 部署 1-3 台 Hetzner VPS + TREVORproxy（§08）—— 突破 30 e/s aggregate
3. **6 周+**: 如果还需要更多，考虑 cookie pool（§07）

---

## 通用文档约定

### 文档生命周期
所有文档都标注 `状态: Research v1`，预期持续迭代：
- v1: 初版调研（当前）
- v2: 增加实测数据 + 代码改动落地后的真实数字
- v3: 经验沉淀 + 反思 + 重新评估

### 更新流程
1. 实施后回来更新对应文档的 §X "迭代历史"
2. 修订核心数据（如真实 e/s 而非估算）
3. 新发现问题加到 §X "风险与开放问题"

### 跨文档引用
- 文件间相对路径引用：`[XX](XX_topic.md#section)`
- 引用本仓库代码：`production_v2.py:行号`
- 引用上层文档：`RATE_LIMIT_INVESTIGATION.md` 在父目录

---

## 4 文档的共同结构（便于查找）

每个调研文档都遵循：

```
1. TL;DR                — 5 行核心结论
2. 背景与问题陈述         — 为什么做这个调研
3. 调研发现 / 实测数据    — 具体数字 + 代码 + 引用
4. 量化预期收益          — 估算 ROI
5. 实施路线图（3 阶段）   — quick wins + mid-term + long-term
6. 风险与开放问题         — 不确定的部分
7. 参考资料              — 所有 URL 和 issue 编号
8. 迭代历史              — 版本变化日志
```

---

## 关联的上层文档

- **`../RATE_LIMIT_INVESTIGATION.md`** — 这次调研的"父文档"，记录了为什么走到现在这步的完整因果链（含 17 个章节，838 行）
- **`~/Desktop/YouTube InnerTube 429 限流深度调研与实战绕过方案.md`** — Manus AI 给的外部建议（已被本次调研验证 / 修正）
- **`../RATE_LIMIT_INVESTIGATION.md` §6** — 之前列的 6 个"后续可探索"，§05-§08 是其中 4 个的深化

---

## 调研工作量统计（生成时）

| 文档 | 行数 | 大小 | 主要工具用量 |
|---|---|---|---|
| 05_query_bank_diversity | 445 | 27 KB | WebSearch + 实测 YouTube suggest API |
| 06_bfs_discovery | 566 | 27 KB | 读 yt-dlp 源码 + 41 seed 实测 |
| 07_cookie_pool | 1015 | 45 KB | yt-dlp issues + Playwright PoC |
| 08_ipv6_vps_rotation | 682 | 29 KB | TREVORproxy/smart-ipv6 源码对比 |
| **Total** | **2,708** | **128 KB** | 4 agent × ~10 min 并行 |

---

*Index v1 — 2026-05-19。后续每次落地一项调研建议后回来更新此页 "调研→实施" 状态。*
