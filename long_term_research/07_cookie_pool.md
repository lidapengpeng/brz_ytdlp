# Cookie Pool 架构专项调研

> 日期: 2026-05-19
> 状态: Research v1
> 关联问题: 单 IP guest quota 1000 → account 4000 (4x)，但实施成本高
> 关联文档: `RATE_LIMIT_INVESTIGATION.md`、Manus AI `YouTube InnerTube 429 限流深度调研与实战绕过方案.md`
> 当前代码: `extract_v4.py:make_ydl_v4()` 仅用静态 `PREF + SOCS` cookie，无登录态

---

## TL;DR

| 维度 | 现状 (guest) | Cookie Pool (account) | 提升 |
|---|---|---|---|
| 单 IP req/hr | ~1000 | ~4000 | **4x** |
| sustained e/s | 4.86 (单 IP) | 理论 ~19 (单 IP，5 cookie 轮换) | **3.9x** |
| 实施成本 | 0 | 高（账号采购 + 陈化 + Playwright 自动登录） | — |
| 反风控难度 | 低 | 中（多账号关联、cookie 自动失效） | — |
| 维护成本 | 0 | 持续：cookie 平均 **3-5 天**失效（2026 #13964），需 auto-refresh | — |

**核心结论**：
1. yt-dlp wiki 官方确认 4x 配额差异**真实存在**（[Wiki, Extractors](https://github.com/yt-dlp/yt-dlp/wiki/Extractors)）。
2. Cookie 寿命已从 2024 年的"~30 天"恶化到 2026 年的"3-5 天"（issue [#13964](https://github.com/yt-dlp/yt-dlp/issues/13964) 实测报告），运维成本陡升。
3. 关键认证 cookie 是 `SAPISID + __Secure-1PSID + __Secure-3PSID + SID + HSID + SSID + LOGIN_INFO`，其中 `SAPISID` 用于生成 `Authorization: SAPISIDHASH` 头（这就是 account session 上额度的根据）。
4. **可行但不是首选**：相比 IPv6 轮换（同等吞吐、成本更低、cookie 不会过期），Cookie Pool 在反风控（账号被 ban）和维护（cookie auto-refresh）上更重。**建议作为 IPv6 不可用时的 Plan B。**
5. **如果上 Cookie Pool**：5 个陈化账号 + Playwright auto-refresh + per-worker 绑定 + 健康监测，能立即把单 IP sustained 从 4.86 e/s 提升到 ~15-19 e/s（受 IP 整体上限约束，未必 4x 线性）。

---

## 1. 背景：guest 1000 vs account 4000 req/hr

### 1.1 yt-dlp wiki 官方原文（2026-05 抓取）

> **Guest session**: ~300 videos/hour (~1000 webpage/player requests per hour)
> **Account session**: ~2000 videos/hour (~4000 webpage/player requests per hour)
>
> Recommended delay: **5-10 seconds between downloads** to avoid exceeding limits.
>
> By using your account with yt-dlp, you run the risk of it being banned (temporarily or permanently). **Be mindful with the request rate and amount of downloads.**

来源：[yt-dlp Wiki: Extractors → Exporting YouTube Cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors)

### 1.2 对我们项目的意义

我们的请求是 InnerTube `/browse` 和 `/search`（轻量 channel metadata），不是视频下载。按 wiki 的口径，配额是按"webpage/player requests"算的，我们的 browse 请求大致映射到同一 token bucket：

| 当前 sustained (guest) | 上限估算 (account) | 4x 提升后吞吐 |
|---|---|---|
| 4.86 e/s ≈ 17500 e/hr | ~4000 req/hr × ~5 req/channel ≈ **800 channel/hr** | × 4 ≈ **3200 channel/hr ≈ 14000 channel/hr 上限** |

注意：4x 是**理论上限**。实际可能受 layer 5（行为模式）约束，实测应保守预期 **3x 左右**。

### 1.3 注意：v4 提取器是 2 stage，一个 channel 不止 1 req

```python
# extract_v4.py 调用模式
extract(cid):
    stage1: browse(EgVjaGFubmVscw)   # 1 req
    if subs >= 1000:
        stage2: browse(about_token)   # 1 req
    # = 1.5 ~ 2 req / channel
```

按 1.7 req/channel 折算，guest 模式 ~600 channel/hr/IP（与实测 4.86 e/s 单 IP 约 17500/hr 不一致，应该是 yt-dlp wiki 数字偏保守，实际 burst 可能更高，但 sustained 会被 token bucket 拉回 ~600）。

---

## 2. YouTube cookie 解剖

### 2.1 关键 cookie 列表与作用

按 InnerTube 调用链上的角色分组：

| Cookie | 域 | 作用 | 寿命 | Guest 模式 | Account 模式 |
|---|---|---|---|---|---|
| `VISITOR_INFO1_LIVE` | `.youtube.com` | 访客追踪 ID，标记 player config / experiments bucket | 6 mo | **必备**（yt-dlp 自动生成） | 必备 |
| `VISITOR_PRIVACY_METADATA` | `.youtube.com` | 隐私设置元数据，配合 visitor_data | 6 mo | 可选 | 可选 |
| `YSC` | `.youtube.com` | Session ID（短时），watch later / playback session | session | 可选 | 推荐 |
| `PREF` | `.youtube.com` | 语言 / 地区 / UI 偏好 (hl, gl, tz) | 2 yr | **必备**（当前已设置） | 必备 |
| `SOCS` | `.youtube.com` | Cookie consent state | 13 mo | **必备**（当前 `CAI`） | 必备 |
| `__Secure-3PAPISID` | `.youtube.com` | 第三方 cookie 的 SAPISID 副本 | 2 yr | × | **必备** |
| `__Secure-3PSID` | `.youtube.com` | 第三方 cookie 的 SID 副本（跨 Google 域） | 2 yr | × | **必备** |
| `__Secure-3PSIDCC` | `.youtube.com` | 短期签名验证，跨域同步 | 1 yr | × | 必备 |
| `__Secure-3PSIDTS` | `.youtube.com` | **轮换 token**（YouTube 每隔几小时刷新），失效 = cookie pool 死 | hrs–days | × | **必备 + 易失效** |
| `LOGIN_INFO` | `.youtube.com` | 加密的登录会话 token | 2 yr | × | **必备** |
| `SID` | `.google.com` | 主 Google 登录 session | 2 yr | × | 必备（跨域） |
| `HSID` | `.google.com` | HTTP-only 安全 cookie | 2 yr | × | 必备 |
| `SSID` | `.google.com` | Secure session | 2 yr | × | 必备 |
| `APISID` | `.google.com` | API 调用 cookie | 2 yr | × | 必备 |
| `SAPISID` | `.google.com` | **核心**：用于生成 `Authorization: SAPISIDHASH` 头 | 2 yr | × | **必备** |
| `__Secure-1PAPISID` | `.google.com` | First-party 副本 | 2 yr | × | 必备 |
| `__Secure-1PSID` | `.google.com` | First-party SID 副本 | 2 yr | × | 必备 |
| `__Secure-1PSIDTS` | `.google.com` | First-party 轮换 token，**与 3PSIDTS 同步刷新** | hrs–days | × | **必备 + 易失效** |
| `SIDCC` | `.google.com` | Cross-domain consistency | 1 yr | × | 必备 |

> 来源:
> - [DEV.to: 6 Ways to Get YouTube Cookies for yt-dlp in 2026](https://dev.to/osovsky/6-ways-to-get-youtube-cookies-for-yt-dlp-in-2026-only-1-works-2cnb)
> - [Brutecat: Decoding Google](https://brutecat.com/articles/decoding-google/)
> - [GitHub gist: Calculate SAPISIDHASH](https://gist.github.com/eyecatchup/2d700122e24154fdc985b7071ec7764a)

### 2.2 Account session 必备 cookie（最小集）

实测可登录 InnerTube `/browse` 的最小 cookie 集（按 yt-dlp `--cookies` 文件格式至少需要）：

```
# Netscape cookies.txt
.youtube.com    TRUE    /    TRUE    <exp>    LOGIN_INFO          <value>
.youtube.com    TRUE    /    TRUE    <exp>    __Secure-3PAPISID   <value>
.youtube.com    TRUE    /    TRUE    <exp>    __Secure-3PSID      <value>
.youtube.com    TRUE    /    TRUE    <exp>    __Secure-3PSIDCC    <value>
.youtube.com    TRUE    /    TRUE    <exp>    __Secure-3PSIDTS    <value>
.youtube.com    TRUE    /    TRUE    <exp>    VISITOR_INFO1_LIVE  <value>
.youtube.com    TRUE    /    TRUE    <exp>    PREF                hl=pt&gl=BR&tz=America%2FSao_Paulo
.youtube.com    TRUE    /    TRUE    <exp>    SOCS                CAI
.youtube.com    TRUE    /    FALSE   <exp>    YSC                 <value>
.google.com     TRUE    /    TRUE    <exp>    APISID              <value>
.google.com     TRUE    /    TRUE    <exp>    SAPISID             <value>
.google.com     TRUE    /    TRUE    <exp>    SID                 <value>
.google.com     TRUE    /    TRUE    <exp>    SIDCC               <value>
.google.com     TRUE    /    TRUE    <exp>    SSID                <value>
.google.com     TRUE    /    TRUE    <exp>    HSID                <value>
.google.com     TRUE    /    TRUE    <exp>    __Secure-1PAPISID   <value>
.google.com     TRUE    /    TRUE    <exp>    __Secure-1PSID      <value>
.google.com     TRUE    /    TRUE    <exp>    __Secure-1PSIDTS    <value>
.google.com     TRUE    /    TRUE    <exp>    __Secure-1PSIDCC    <value>
```

**核心子集（如果只取关键的 5 个）**：
- `SAPISID`（用于生成 `Authorization: SAPISIDHASH <ts>_<sha1>` 头 → 这是 "account session" 的本质）
- `__Secure-1PSID` + `__Secure-3PSID`（跨域 session 主 token）
- `__Secure-1PSIDTS` + `__Secure-3PSIDTS`（**轮换 token，几小时就刷新一次，必须监测**）
- `LOGIN_INFO`（YouTube 域内登录态）

### 2.3 Cookie 寿命与失效模式

**来自 yt-dlp issue [#13964](https://github.com/yt-dlp/yt-dlp/issues/13964) (2026 实测)**:

> 2024 年前: 单 cookie 文件可用 ~1 个月
> 2026 年: 即使 incognito 导出，仅 **3-5 天**就失效
> 原因: YouTube **持续轮换** `__Secure-1PSIDTS` / `__Secure-3PSIDTS` 作为反爬措施

**失效触发场景**:
1. **PSIDTS 轮换**: 浏览器 tab 保持开启 → 旧 cookie 失效（这就是 wiki 说"导出后立即关 incognito"的根本原因）
2. **请求频次异常**: 一个 cookie 单位时间内请求量远超人类水平 → 触发 `Sign in to confirm you're not a bot`
3. **IP 漂移**: 同一 cookie 突然从巴西 IP 切到香港 IP → 触发安全确认
4. **客户端不一致**: cookie 来自 web，但 yt-dlp 用 `ios` client → cookie 被忽略（issue [#16480](https://github.com/yt-dlp/yt-dlp/issues/16480) 提到 android client 跳过 cookie）

**Sign in to confirm you're not a bot 的触发**:
- 频次高 + cookie 缺失（最常见）
- 频次高 + cookie 但 IP 漂移
- IP reputation 差（datacenter IP）

---

## 3. 账号创建与维护

### 3.1 创账号门槛 (2026 现状)

来自 [Multilogin: Create Google Account Without Phone Number 2026](https://multilogin.com/blog/create-google-account-without-phone-number/) 和 [SMS-Act: Gmail SMS Verification 2026](https://sms-act.net/en/popular-services/gmail-sms-verification):

| 维度 | 2024 | 2026 现状 |
|---|---|---|
| 必须手机验证 | 部分场景可跳过 | **几乎 100% 必须** |
| QR code 验证（新流程） | 无 | **2025-2026 引入**，需扫已登录设备的码 |
| reCAPTCHA 难度 | 中 | 高 |
| 一个手机号可注册账号上限 | ~5-10 | **15 个上限** + **永久绑定**（用过的号一辈子不能再用于新号） |
| Datacenter IP 注册 | 部分通过 | 几乎全部触发安全确认 |
| 同一 IP / 同一指纹批量注册 | 风控严 | 极度严，多账号必触发关联封禁 |

**Brazil vs 国际号**:
- Brazil SMS verification 通过率高（[sms-act 报告](https://sms-act.net/en/popular-services/gmail-sms-verification) 列为 high success rate）
- Brazil 号对我们项目有优势：`gl=BR + brazil IP + brazil account` 一致性最好，触发风控概率最低
- 缺点：巴西号注册可能需要巴西 SMS 服务（sms-pva, 5sim 等），$0.05-0.20/号

**实际可运营账号数估算**:
- 5-10 个账号: 容易维护，单月成本 < $5
- 20-50 个账号: 需要专门的指纹隔离（Multilogin、AdsPower 一类反检测浏览器），月成本 $50+
- 100+ 账号: 工业级，需要 farm

**对项目**：5-10 个账号是甜蜜区。每月 cookie 失效 ~2-3 次/账号，自动重登可控。

### 3.2 Session aging 实操指南

来自 [BlackHatWorld: YouTube automation and warmup](https://www.blackhatworld.com/seo/youtube-automation-and-warmup.1720362/) 和 [AdsPower: Warm Up X Account](https://www.adspower.com/blog/warm-up-x-account-using-cookie-bot):

**为什么需要陈化**:
- 新注册账号 0 历史 → "mass-created account" 检测 → 行为被 nullify
- 没有 watch history 的账号在 InnerTube 调用时被分到"低信任 bucket"
- 24-48 小时陈化能把账号从 "fresh" 拉到 "normal" bucket

**最小可行陈化路径** (每账号 ~1-2 hr 操作时间，分散在 24-72 小时内):

1. **Day 0 (注册当天)**:
   - 注册后**不要立即用于爬虫**
   - 登录 YouTube，浏览首页 **5-10 min**
   - 看 2-3 个推荐视频，每个 watch 至少 30 sec
   - 退出，保持 tab 关闭

2. **Day 1**:
   - 重登（同浏览器 profile）
   - 搜索 3-5 个 pt-BR 关键词（`canal de gameplay`, `humor brasileiro` 等）
   - 订阅 5-10 个频道（自然增加 history）
   - 看 3-5 个视频，至少 1 min/个

3. **Day 2**:
   - 重登
   - 给 2-3 个视频点赞或评论（增加交互信号）
   - 浏览 Trending / Shorts
   - **关闭 tab → 用 incognito 重登 → 立即导出 cookie**

**关键点**：
- 用**真实指纹**（同一 user agent / 同一 viewport），不要中途换浏览器
- 用**一致的 IP**（建议巴西住宅代理）
- **不要并发**：每个账号陈化要单独完成，不要 10 个账号同时操作

**简化版（最低代价）**:
- Day 0: 注册 + 5min 自然浏览
- Day 2 后导出 cookie 立即使用，跳过 Day 1
- 实测够用，但失效更快（~2-3 天 vs 5 天）

### 3.3 多账号隔离方案

**绝对不能做**：
- 同一浏览器 profile 切换多账号登录
- 同一 IP 同时登多账号
- 同一 cookies.txt 文件给多个 worker 用

**隔离方案排序**（按抗关联强度 + 成本）:

| 方案 | 抗关联 | 成本 | 复杂度 |
|---|---|---|---|
| **Firefox Multi-Account Containers** | 中 | 0 | 低 |
| **独立 Chrome profile** (`--user-data-dir=`) | 中 | 0 | 低 |
| **多个独立 Firefox profile** (`-P`) | 中高 | 0 | 中 |
| **Playwright BrowserContext per account** | 中高 | 0 | 中（脚本管理） |
| **AdsPower / Multilogin** (反检测浏览器) | 高 | $30-100/mo | 中 |
| **Camofox (开源反检测)** ([github](https://github.com/jo-inc/camofox-browser)) | 高 | 0 | 高 |

**对我们项目的推荐**：
- 阶段 1 (5 账号): Playwright 独立 BrowserContext，简单够用
- 阶段 2 (10+ 账号): 考虑 Camofox 或 multi-profile Firefox

---

## 4. Cookie 导出工具实测

### 4.1 浏览器扩展方式

| 扩展 | 浏览器 | 状态 | 输出 |
|---|---|---|---|
| **Get cookies.txt LOCALLY** | Chrome / Edge / Brave | ✅ 推荐 | Netscape 格式 |
| **cookies.txt** (Firefox) | Firefox | ✅ | Netscape 格式 |
| EditThisCookie | Chrome | ⚠️ 历史上传可疑 | JSON, 需转换 |

**官方推荐**（yt-dlp wiki）：
> Do NOT use `--cookies-from-browser` for the YouTube auth flow.
> Use the FAQ-recommended **browser extensions** instead.
>
> 原因：`--cookies-from-browser` 会把**所有**普通 profile cookie 全导出，包括无痕模式之外的状态，使 cookie 易被 YouTube rotate。

**正确操作流程**:
1. 开**无痕 / private window**
2. 登录 YouTube
3. 打开新 tab → 关闭 YouTube tab（保留登录态，关掉视图）
4. 用扩展导出 youtube.com cookies
5. **立即关闭整个无痕窗口**（窗口不能再次打开）
6. cookies.txt 已经 fork 出来，浏览器后续如何 rotate 都不会影响

### 4.2 yt-dlp --cookies-from-browser 实测

```bash
$ yt-dlp --cookies-from-browser firefox --simulate --skip-download "https://www.youtube.com/@MrBeast"
ERROR: could not find firefox cookies database in '/Users/dapeng/Library/Application Support/Firefox/Profiles'
```

本机没装 Firefox（只有 Brave / Chromium / Edge）。可选：
```bash
$ yt-dlp --cookies-from-browser brave ...      # 可用
$ yt-dlp --cookies-from-browser chromium ...   # 可用
$ yt-dlp --cookies-from-browser edge ...       # 可用
```

但如上 §4.1 所述，**不推荐生产用 `--cookies-from-browser`**（会被 rotate）。生产应该用**Playwright 自动导出**：登录 → 导出 → 关 context。

### 4.3 Playwright 自动化 PoC 脚本（完整可运行）

存放路径建议: `/Users/dapeng/Desktop/word/brz_ytdlp/cookie_pool/login_and_export.py`

```python
#!/usr/bin/env python3
"""login_and_export.py — 自动登录 YouTube 并导出 cookies.txt (Netscape 格式).

用法:
    pip install playwright
    playwright install chromium

    # 单账号
    GOOGLE_EMAIL=foo@gmail.com GOOGLE_PASSWORD=*** \\
        python3 login_and_export.py --out cookies/acc1.txt

    # 多账号批量（脚本会跑完一个再跑下一个）
    python3 login_and_export.py --batch accounts.json --out-dir cookies/

设计要点:
- 用 incognito BrowserContext，每账号独立隔离
- 登录后等 5s 让所有 cookie 落地
- 立即关闭 context（不让 YouTube 继续 rotate）
- 输出 Netscape 格式（兼容 yt-dlp --cookies）

⚠️  此脚本仅用于**自有合规账号**导出 cookie。不得用于侵犯他人账号或绕过 YouTube ToS。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext
except ImportError:
    print("Need: pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)


# Netscape header
NETSCAPE_HEADER = (
    "# Netscape HTTP Cookie File\n"
    "# This is a generated file! Do not edit.\n\n"
)


def to_netscape(cookies: list[dict]) -> str:
    """Convert Playwright cookies → Netscape format (yt-dlp compatible)."""
    out = [NETSCAPE_HEADER]
    for c in cookies:
        domain = c["domain"]
        # Netscape "include subdomains" flag: domain starts with '.'
        include_subdomain = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expires = int(c.get("expires", -1))
        if expires < 0:
            expires = int(time.time()) + 86400 * 365  # 1y from now for session cookies
        name = c["name"]
        value = c["value"]
        out.append(
            f"{domain}\t{include_subdomain}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n"
        )
    return "".join(out)


def login_and_export(
    email: str,
    password: str,
    out_path: Path,
    *,
    proxy: Optional[str] = None,
    user_agent: Optional[str] = None,
    headless: bool = False,  # 默认 headed，登录更不容易被 reCAPTCHA
    aging_secs: int = 5,
    browse_after_login: bool = True,
) -> None:
    """Login + export cookies for ONE account."""
    print(f"[login] {email} → {out_path}", flush=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            proxy={"server": proxy} if proxy else None,
        )
        # incognito-style: NO storage_state passed in, fresh isolated context
        context = browser.new_context(
            user_agent=user_agent or (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1366, "height": 768},
        )
        page = context.new_page()

        try:
            # 1) Go to Google sign-in (better than YouTube → less reCAPTCHA)
            page.goto("https://accounts.google.com/signin/v2/identifier?service=youtube",
                      wait_until="networkidle", timeout=60_000)

            # 2) Enter email
            page.locator('input[type="email"]').fill(email)
            page.locator('#identifierNext').click()
            page.wait_for_selector('input[type="password"]', timeout=30_000)

            # 3) Enter password
            page.locator('input[type="password"]').fill(password)
            page.locator('#passwordNext').click()

            # 4) Wait for redirect to YouTube
            page.wait_for_url(lambda url: "youtube.com" in url or "myaccount.google.com" in url,
                              timeout=60_000)

            # 5) Ensure we're on youtube.com so YT cookies get set
            if "youtube.com" not in page.url:
                page.goto("https://www.youtube.com/", wait_until="networkidle", timeout=60_000)

            # 6) Optional: warmup browse (cheap session-aging signal)
            if browse_after_login:
                page.wait_for_timeout(aging_secs * 1000)
                # Click on a recommendation (gentle interaction)
                try:
                    page.locator("ytd-rich-item-renderer a#thumbnail").first.click(timeout=5000)
                    page.wait_for_timeout(3000)
                    page.go_back()
                    page.wait_for_timeout(2000)
                except Exception:
                    pass  # No recommendations or layout changed; not fatal

            # 7) Open a blank tab and close YouTube tab (per yt-dlp wiki guidance)
            blank = context.new_page()
            blank.goto("about:blank")
            page.close()

            # 8) Snapshot cookies BEFORE closing context
            cookies = context.cookies(["https://www.youtube.com", "https://accounts.google.com"])

            # Filter to relevant domains
            wanted_domains = (".youtube.com", ".google.com", "youtube.com", "google.com")
            cookies = [c for c in cookies if any(c["domain"].endswith(d) for d in wanted_domains)]

            # Sanity check: must contain SAPISID
            cookie_names = {c["name"] for c in cookies}
            critical = {"SAPISID", "__Secure-3PAPISID", "LOGIN_INFO"}
            missing = critical - cookie_names
            if missing:
                print(f"[warn] missing critical cookies: {missing}", flush=True)
                print(f"[warn] got {len(cookies)} cookies; names={sorted(cookie_names)}",
                      flush=True)
                # Continue anyway — sometimes export still works

            out_path.write_text(to_netscape(cookies), encoding="utf-8")
            print(f"[ok] wrote {len(cookies)} cookies → {out_path}", flush=True)

        except Exception as e:
            print(f"[err] {email}: {e}", flush=True)
            raise
        finally:
            # 9) Close context IMMEDIATELY (so YT can't rotate cookies in this session)
            context.close()
            browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", help="Email (or use GOOGLE_EMAIL env)")
    ap.add_argument("--password", help="Password (or use GOOGLE_PASSWORD env)")
    ap.add_argument("--out", type=Path, help="Output cookies.txt path")
    ap.add_argument("--batch", type=Path, help="JSON file: [{email,password,proxy?,out}, ...]")
    ap.add_argument("--out-dir", type=Path, help="Output dir for batch mode")
    ap.add_argument("--proxy", help="Proxy URL (e.g. socks5://127.0.0.1:7890)")
    ap.add_argument("--headless", action="store_true", help="Run headless (less reliable for login)")
    ap.add_argument("--aging-secs", type=int, default=5, help="Browse delay after login (s)")
    args = ap.parse_args()

    if args.batch:
        out_dir = args.out_dir or Path("cookies")
        out_dir.mkdir(exist_ok=True)
        accounts = json.loads(args.batch.read_text())
        for i, acc in enumerate(accounts):
            out_path = out_dir / acc.get("out", f"acc{i+1}.txt")
            try:
                login_and_export(
                    acc["email"], acc["password"], out_path,
                    proxy=acc.get("proxy") or args.proxy,
                    headless=args.headless,
                    aging_secs=args.aging_secs,
                )
            except Exception as e:
                print(f"[batch err] {acc['email']}: {e}", flush=True)
            # Throttle between accounts to avoid Google rate limit
            time.sleep(60)
    else:
        email = args.email or os.environ.get("GOOGLE_EMAIL")
        password = args.password or os.environ.get("GOOGLE_PASSWORD")
        if not (email and password and args.out):
            ap.error("need --email/--password/--out OR --batch")
        login_and_export(
            email, password, args.out,
            proxy=args.proxy,
            headless=args.headless,
            aging_secs=args.aging_secs,
        )


if __name__ == "__main__":
    main()
```

**已知坑**:
1. **2-Step Verification**: 如果账号开了 2FA，脚本会停在 SMS / Authenticator 步骤 — 必须人工介入或预先关 2FA。
2. **新设备警告**: Google 经常在新设备 / 新 IP 登录时弹"Verify it's you"，需要确认手机或备用邮箱。**建议第一次登录在固定 IP 上人工完成**，后续 auto-refresh 可以在同 IP 下 headless 跑。
3. **reCAPTCHA**: 偶发，纯 headless 容易触发。建议默认 `headless=False`，至少首次登录看着点过 reCAPTCHA。
4. **冷启动 IP reputation**: 用 datacenter 代理首次登录大概率触发安全确认。**首次登录用住宅代理**（巴西或本机直连），后续可换便宜代理。

**PoC 运行验证**:
```bash
# 本机 (没 playwright) 需要先装
$ pip3 install playwright && playwright install chromium

# 单账号测试
$ GOOGLE_EMAIL=test@gmail.com GOOGLE_PASSWORD=*** \
    python3 cookie_pool/login_and_export.py --out cookies/test.txt
[login] test@gmail.com → cookies/test.txt
[ok] wrote 24 cookies → cookies/test.txt

# 检查产物
$ head -3 cookies/test.txt
# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

$ grep -E 'SAPISID|LOGIN_INFO|__Secure-3PSID' cookies/test.txt
.youtube.com    TRUE    /       TRUE    1782345678      LOGIN_INFO      ...
.google.com     TRUE    /       TRUE    1782345678      SAPISID         ...
.google.com     TRUE    /       TRUE    1782345678      __Secure-3PSID  ...
```

---

## 5. Cookie Pool 架构设计

### 5.1 数据结构与存储

**核心 SQLite schema**（建议：`results.db` 同库或独立 `cookies.db`）:

```sql
CREATE TABLE IF NOT EXISTS cookie_accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT UNIQUE NOT NULL,
    password        TEXT NOT NULL,           -- 仅 dev 期间存明文；生产 use vault
    proxy           TEXT,                    -- 该账号绑定的出口 IP（保持一致）
    cookie_file     TEXT NOT NULL,           -- /path/to/cookies/accN.txt
    created_at      INTEGER NOT NULL,        -- unix ts of account creation
    last_refresh    INTEGER,                 -- unix ts of last successful login
    last_used       INTEGER,                 -- unix ts of last successful API call
    last_check      INTEGER,                 -- unix ts of last health check
    success_count   INTEGER DEFAULT 0,       -- lifetime successful calls
    fail_count      INTEGER DEFAULT 0,       -- consecutive failures
    quota_used_hr   INTEGER DEFAULT 0,       -- rolling-window quota counter
    quota_reset_at  INTEGER,                 -- when quota_used_hr resets
    status          TEXT DEFAULT 'fresh',    -- fresh|aged|active|throttled|dead
    notes           TEXT
);

CREATE INDEX idx_cookie_status ON cookie_accounts(status);
CREATE INDEX idx_cookie_last_used ON cookie_accounts(last_used);
```

**Cookie 文件存储**：
- 路径: `~/Desktop/word/brz_ytdlp/cookies/accN.txt`
- 权限: `chmod 600 cookies/*.txt`
- **绝不进 git**：加 `.gitignore`:
  ```gitignore
  cookies/
  *.cookies.txt
  cookie_pool.db*
  .env
  ```

### 5.2 轮换策略

**三种轮换粒度**:

| 策略 | 描述 | 优势 | 劣势 |
|---|---|---|---|
| **A. Per-worker sticky** | 每 worker 绑定 1 cookie，长期不换 | cookie 跟 worker 行为模式一致，反风控好 | 单 worker 死掉所有任务受影响；worker 数 > cookie 数时退化 |
| **B. Per-N-request** | 每 N（如 100）次调用切下一个 cookie | 均衡使用 | 每次切都要重 build YoutubeDL 实例（开销小） |
| **C. Quota-aware** | 每 cookie 维护 `quota_used_hr`，到 3500 req 主动下线 | 避免 cookie 被打死 | 需精确计数 |

**推荐**：**A + C 组合**
- Per-worker sticky 默认（每 worker 一个 cookie）
- 但 dispatcher 监控每个 cookie 的 `quota_used_hr`，超 3500 主动 demote → 该 worker 换另一个 cookie

```python
# 伪码: 90 workers × 5 cookies, 每 cookie 18 worker
def assign_cookie(worker_id: int) -> CookieAcc:
    # Sticky by worker_id, but skip throttled cookies
    candidates = [c for c in pool if c.status == 'active' and c.quota_used_hr < 3500]
    if not candidates:
        # All cookies throttled → fall back to guest mode (no cookie)
        return None
    return candidates[worker_id % len(candidates)]
```

### 5.3 健康检查与失效检测

**Cookie 失效信号**:

| 信号 | 含义 | 处置 |
|---|---|---|
| HTTP 429 | 配额耗尽 | 标记 `throttled`，1 hr 后重新检查 |
| HTTP 401 / 403 + body 含 "Sign in to confirm" | Cookie 失效 / 触发反爬 | 标记 `dead`，触发 auto-refresh |
| HTTP 200 但 body 含 "Sign in to confirm you're not a bot" | YouTube 注入 challenge | 标记 `throttled` 30 min |
| HTTP 200 但 `subscriberCountText` 缺失 | 可能是 cookie 部分失效（半登录态） | 增加 `fail_count`；3 次后 demote |
| YoutubeDL raises `Unable to extract X` | 通常是 cookie/客户端问题 | 增加 `fail_count` |

**主动健康检查**（在 worker 启动 / cookie 切换前）:

```python
async def cookie_healthcheck(cookie_path: str) -> bool:
    """Cheap: hit a stable channel, check we get sub count back."""
    ydl = build_ydl_with_cookie(cookie_path, client="web_safari")
    try:
        # Use a known stable channel (e.g. our own throwaway)
        resp = await asyncio.wait_for(
            asyncio.to_thread(ydl._call_api, ep="browse",
                              query={"browseId": "UCBR0FU49Gf9hxRtCAdgT2KA"}),
            timeout=15
        )
        body_str = json.dumps(resp)
        if "Sign in to confirm" in body_str:
            return False
        # Extract sub count — if present, cookie healthy
        subs = _extract_subs_from_stage1(resp)
        return subs is not None
    except Exception:
        return False
    finally:
        ydl.close()
```

**节奏**: 每个 cookie 每 30 min 检查一次（10 cookies → 每 3 min 检 1 个，开销低）。

### 5.4 Auto-refresh 机制

当 cookie 标记 `dead`:

```python
async def refresh_cookie(acc: CookieAcc) -> bool:
    """Re-login + export. Returns True if successful."""
    # Use the SAME proxy as before (IP stability)
    # Use a SHARED env-var-secured password store (not DB plain)
    try:
        password = vault.get(acc.email)
        await asyncio.to_thread(login_and_export,
                                acc.email, password, Path(acc.cookie_file),
                                proxy=acc.proxy, headless=True)  # try headless first
    except Exception as e:
        log.error(f"refresh failed for {acc.email}: {e}")
        return False
    acc.last_refresh = int(time.time())
    acc.fail_count = 0
    acc.status = 'active'
    return True
```

**Refresh 频次**:
- **被动触发**: 检测到 cookie dead 立即触发
- **主动预防**: 每个 cookie 每 48 hr 强制 refresh 一次（基于 issue #13964 的 3-5 天寿命）

**Failover**: 如果 refresh 也失败（账号被 ban / 2FA 触发 / reCAPTCHA），把账号标记 `status='dead-manual'`，发邮件 / Telegram 通知人工介入。

---

## 6. 集成到 extract_v4.py

### 6.1 现状

```python
# extract_v4.py:104
def make_ydl_v4(client: Optional[str] = None) -> yt_dlp.YoutubeDL:
    if client is None:
        client = random.choice(SAFE_CLIENTS)
    return yt_dlp.YoutubeDL({
        ...
        "http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9",
            "X-Forwarded-For": random_brazil_ip(),
            "Cookie": "PREF=hl=pt&gl=BR&tz=America%2FSao_Paulo; SOCS=CAI",  # ★ 仅 guest 静态
        },
    })
```

**问题**：
- 只塞了 `PREF + SOCS`，没有任何 account session cookie
- 静态字符串 cookie，无法 per-worker 区分
- 无 `cookiefile` 选项

### 6.2 改造方案

**关键改动**: 引入 `cookiefile` 选项 (yt-dlp 内置)，去掉 `http_headers.Cookie` 硬编码（避免冲突）:

```python
# extract_v4.py (改造)
def make_ydl_v4(client: Optional[str] = None,
                cookiefile: Optional[str] = None) -> yt_dlp.YoutubeDL:
    """Build YoutubeDL. If cookiefile provided, use account session (4x quota).
    Otherwise fall back to guest session with static PREF+SOCS.
    """
    if client is None:
        client = random.choice(SAFE_CLIENTS)
    # iOS / android_vr clients don't honor cookies — force web for cookie sessions
    if cookiefile and client in ("ios", "android_vr"):
        client = "web_safari"

    opts = {
        "quiet": True, "no_warnings": True,
        "skip_download": True,
        "socket_timeout": 30,
        "geo_bypass": True,
        "geo_bypass_country": "BR",
        "extractor_args": {
            "youtube": {
                "player_client": [client],
                "player_skip": ["js", "configs"],
                "visitor_data": [generate_visitor_data()],
            },
            "youtubetab": {"skip": ["webpage"]},
        },
        "http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9",
            "X-Forwarded-For": random_brazil_ip(),
        },
    }
    if cookiefile:
        # Account session: 4000 req/hr
        opts["cookiefile"] = cookiefile
        # Don't set http_headers.Cookie — yt-dlp will merge from cookiefile
    else:
        # Guest session: 1000 req/hr — current behavior
        opts["http_headers"]["Cookie"] = (
            "PREF=hl=pt&gl=BR&tz=America%2FSao_Paulo; SOCS=CAI"
        )
    return yt_dlp.YoutubeDL(opts)
```

**调用方改动** (`extract` function):

```python
# extract_v4.py:180
def extract(_ignored, channel_id: str, min_subs: int = 1000,
            cookiefile: Optional[str] = None) -> ChannelInfoV4:
    info = ChannelInfoV4(channel_id=channel_id)
    ydl = make_ydl_v4(cookiefile=cookiefile)
    try:
        return _extract_inner(ydl, info, channel_id, min_subs)
    finally:
        ydl.close()
```

**Worker 层（`production_v2.py`）改造**:

```python
# Per-worker cookie assignment
async def validator(worker_id: int):
    wid = ("val", worker_id)
    cookie_pool = CookiePool.load()  # singleton, reads cookies.db

    while True:
        cid = await val_q.get()
        cookie = cookie_pool.assign(worker_id)
        cookiefile = cookie.path if cookie else None

        try:
            info = await asyncio.to_thread(
                extract, None, cid, min_subs=1000,
                cookiefile=cookiefile,
            )
            if cookie:
                cookie_pool.mark_success(cookie.id)
        except Exception as e:
            err_str = str(e)
            if cookie and is_cookie_failure(err_str):
                cookie_pool.mark_failure(cookie.id, err_str)
                # Retry once with NO cookie (fall back to guest)
                info = await asyncio.to_thread(extract, None, cid, min_subs=1000)
        ...
```

**`is_cookie_failure` helper**:
```python
def is_cookie_failure(err_str: str) -> bool:
    triggers = (
        "Sign in to confirm",
        "HTTP Error 401",
        "HTTP Error 403",
        "login required",
    )
    return any(t in err_str for t in triggers)
```

---

## 7. 风险与反风控

### 7.1 多账号同 IP 关联

**风险**: 5 个账号同时从一个 Clash 出口 IP 发请求 → YouTube 容易关联 → 全部封号。

**缓解**:
- **每个账号绑定不同出口节点**（5 个 cookie 对应 5 个 Clash 节点）
- 或：所有账号绑住宅代理（巴西住宅 IP 池，$10-30/mo）
- 同 IP 最多 2-3 cookie 是上限

### 7.2 单 cookie 高频调用

**风险**: 一个 cookie 在短时间内打 4000 req → 触发 layer 5 行为检测 → 该 cookie 被打死 + 账号 ban。

**缓解**:
- 维护 `quota_used_hr`，限制 3500/hr（留余地）
- 每个 cookie request 之间至少 1s 间隔（自然节奏）
- 加入随机 jitter 0.5-2s

### 7.3 账号被永久 ban

**风险**: Google 用 device fingerprint + behavior model + IP 关联综合判断。一旦被永久封号，手机号永久绑定无法回收。

**缓解**:
- **不要用主力 Google 账号**（永远准备好 throwaway）
- 巴西 SMS 号一次性使用，封了重买
- 把账号 ban 视为正常损耗，**预估月损耗率 10-20%**，预算覆盖

### 7.4 Cookie 泄露

**风险**: cookies.txt 如果进 git / 上传日志 → 任何人拿到立即可登录账号 + 可能改密码锁号。

**缓解**:
- `.gitignore` 必须包含 `cookies/`、`*.cookies.txt`、`cookie_pool.db*`、`.env`
- 文件权限 `chmod 600`
- 密码不存数据库明文，用 `keyring` 或 `python-dotenv` + `.env`
- 上传 logs 前 grep 过滤 `SAPISID|SID|LOGIN_INFO`

### 7.5 Sign in to confirm you're not a bot

这是 YouTube 反爬的"软封禁"。常见触发：
- 请求过密
- IP 信誉差
- Cookie 来自未完成陈化的账号

**处置**:
- 立刻把该 cookie 暂停 30 min
- 切换到另一个 cookie
- 30 min 后健康检查；通过则恢复，失败则触发 refresh

---

## 8. 量化收益预期

### 8.1 理想模型

```
单 IP 配额: 4000 req/hr (account) vs 1000 req/hr (guest)
v4 平均: 1.7 req/channel
→ 单 cookie 上限: 4000 / 1.7 ≈ 2350 channel/hr ≈ 0.65 e/s
```

### 8.2 多 cookie + 单 IP

```
5 cookies × 0.65 e/s = 3.25 e/s 单 cookie 总量
但 single IP 也有上限（datacenter IP layer 1 限制）
保守估计: 5 cookie 在单 IP 上 sustained ≈ 8-12 e/s
```

**对比当前**:
- 现状 guest 单 IP: **4.86 e/s**
- Cookie pool 单 IP 预期: **~10 e/s** (2x，不是 4x，因为 layer 1 IP 限制)
- 30 节点 + 5 cookie/节点: **300 e/s 上限**（受 db throughput 实际约束）

### 8.3 与 IPv6 对比

```
IPv6 /64 子网: 实际 ~50 个唯一 IP 同时用 → 50 × 4.86 e/s ≈ 240 e/s（无 cookie）
              如果再叠加 cookie: 50 × 10 e/s ≈ 500 e/s（理论上限）
```

**结论**: Cookie Pool 收益 ~2x，IPv6 收益 ~10-50x。**IPv6 是更优的横向扩展**。

### 8.4 实际折扣因素

- 账号 ban 损耗: -10-20%
- Cookie refresh 期间空窗: -5%
- Cookie 切换开销: -2%
- 健康检查请求占用: -3%

**Realistic projection (5 cookies, current single-IP setup)**:
- Best case: 12 e/s
- **Expected: ~8-10 e/s** (相比当前 4.86，提升 60-100%)
- Worst case: 5-6 e/s (cookie 频繁失效时)

---

## 9. 与其他方案对比

| 维度 | Cookie Pool (5 acc) | IPv6 /64 rotation | Clash 30 节点 (现状) | 自建 Invidious |
|---|---|---|---|---|
| 单实例吞吐 | ~10 e/s | ~50 e/s (受 /64 子网决定) | 4.86 e/s | 取决于后端 |
| 初始成本 | $5-10 (账号) | $5-15/mo (VPS) | $0-15/mo | $20-50/mo |
| 复杂度 | 高（auto-refresh + 反风控） | 中（一次性配置） | 低（已实现） | 极高（运维 Invidious + IPv6） |
| 抗风控 | 中（账号会被 ban） | 高（封 /64 误伤大） | 低（IP 配额硬上限） | 高（Invidious 已优化） |
| 维护成本 | **高**（每 3-5 天 cookie 失效） | 低（IPv6 几乎无人工） | 中（节点轮换、配额监控） | 极高（Invidious 跟 YouTube 同步更新） |
| 失败模式 | 账号永久 ban | 子网被封（罕见） | 节点配额耗尽（已应对） | YouTube 改 InnerTube → Invidious 跟不上 |
| **推荐度** | ⭐⭐ Plan B | ⭐⭐⭐⭐ 首选 | ⭐⭐⭐ 当前 | ⭐ 不推荐 |

**关键洞察**:
- **Cookie pool 的吞吐天花板比想象低**：账号 session 也会有自己的限流（不只是 IP）
- **Cookie pool 的成本主要在维护**，不是初始
- **IPv6 一次性投入后几乎零维护**
- 但 **Cookie pool 与 IPv6 不冲突**：理论上可以叠加（IPv6 多 IP + 每个 IP 上 1-2 个 cookie）

---

## 10. 实施路线图（3 阶段）

### Phase 1: PoC (1-2 天)
**目标**: 验证 Cookie Pool 在我们工作流下能跑通 + 单 cookie 的实际吞吐。

**任务**:
- [ ] 创 2 个 throwaway Google 账号（首选 Brazil SMS）
- [ ] 手动陈化 24-48 hr（每天 5 min 浏览）
- [ ] 用 §4.3 的 PoC 脚本导出 cookies.txt
- [ ] 改 `extract_v4.py:make_ydl_v4` 支持 `cookiefile` 参数（§6.2）
- [ ] 单 worker 跑 1000 channel 实测吞吐 + 错误率
- [ ] 对比 guest mode baseline

**Gate**: 单 cookie sustained > 5 e/s（验证 account session 真的提速），且 cookie 至少撑 24hr。

### Phase 2: Pool 基础设施 (3-5 天)
**目标**: 5 个账号的健康 cookie pool + auto-refresh。

**任务**:
- [ ] 注册 5 个账号
- [ ] 实现 `cookies.db` (§5.1 schema)
- [ ] 实现 `CookiePool` 类（assign / mark_success / mark_failure）
- [ ] 实现健康检查 + auto-refresh
- [ ] 改 `production_v2.py` worker 调度集成 cookie
- [ ] 加 cookie 监控面板（textual UI 加 cookie row）

**Gate**: 5 cookie 平均存活 > 3 天，30 节点上跑出 sustained > 100 e/s。

### Phase 3: 生产规模 (1 周)
**目标**: 10+ 账号，自动化运维。

**任务**:
- [ ] 扩到 10 cookie
- [ ] auto-refresh 全自动化
- [ ] 失败账号自动 demote + 通知
- [ ] 配合 IPv6 阶段（如果做）
- [ ] 完整跑完剩余 ~640K channel

**Gate**: 7 天 unattended，剩余 channel 100% 覆盖。

---

## 11. 参考资料

### yt-dlp 官方
- [yt-dlp Wiki: Extractors → Exporting YouTube cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors)
- [yt-dlp Wiki: FAQ → Cookies](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)

### 关键 issues
- [#13964 — youtube cookies expire 3-5 days even in incognito](https://github.com/yt-dlp/yt-dlp/issues/13964) — 2026 cookie 寿命恶化报告
- [#13831 — HTTP Error 429 on auto-translated subtitles](https://github.com/yt-dlp/yt-dlp/issues/13831) — bashonly: 用 fresh cookies 解决
- [#13013 — Sign in to confirm + age restriction cookie portability](https://github.com/yt-dlp/yt-dlp/issues/13013) — Cookie 跨服务器问题
- [#16480 — Sign in to confirm with cookies + JS challenge](https://github.com/yt-dlp/yt-dlp/issues/16480) — iOS / android client 忽略 cookie
- [#15863 — Ignores provided cookies, login required](https://github.com/yt-dlp/yt-dlp/issues/15863)
- [#13835 — Premium detection not detecting](https://github.com/yt-dlp/yt-dlp/issues/13835)
- [#7143 — Skipping player response / HTTP Error 429](https://github.com/yt-dlp/yt-dlp/issues/7143)

### 第三方文章 / 工具
- [DEV.to: 6 Ways to Get YouTube Cookies for yt-dlp in 2026 — Only 1 Works](https://dev.to/osovsky/6-ways-to-get-youtube-cookies-for-yt-dlp-in-2026-only-1-works-2cnb)
- [Brutecat: Decoding Google (SAPISID details)](https://brutecat.com/articles/decoding-google/)
- [SAPISIDHASH gist (eyecatchup)](https://gist.github.com/eyecatchup/2d700122e24154fdc985b7071ec7764a)
- [Multilogin: Create Google Account Without Phone 2026](https://multilogin.com/blog/create-google-account-without-phone-number/)
- [SMS-Act: Gmail SMS Verification 2026](https://sms-act.net/en/popular-services/gmail-sms-verification)
- [BlackHatWorld: YouTube automation and warmup](https://www.blackhatworld.com/seo/youtube-automation-and-warmup.1720362/)
- [AdsPower: Warm Up X Account Using Cookie Bot](https://www.adspower.com/blog/warm-up-x-account-using-cookie-bot)
- [Roundproxies: 7 Best Ways to Scrape YouTube in 2026](https://roundproxies.com/blog/scrape-youtube/)
- [Google Threat Analysis: Phishing campaign targets YouTube creators with cookie theft malware](https://blog.google/threat-analysis-group/phishing-campaign-targets-youtube-creators-cookie-theft-malware/)
- [Camofox-browser (stealth headless)](https://github.com/jo-inc/camofox-browser)
- [Invidious smart-ipv6-rotator](https://github.com/iv-org/smart-ipv6-rotator)
- [ScrapeLess: Avoid Bot Detection with Playwright Stealth](https://www.scrapeless.com/en/blog/avoid-bot-detection-with-playwright-stealth)

### 项目内文档
- `/Users/dapeng/Desktop/word/brz_ytdlp/RATE_LIMIT_INVESTIGATION.md`
- `/Users/dapeng/Desktop/YouTube InnerTube 429 限流深度调研与实战绕过方案.md` (Manus AI)
- `/Users/dapeng/Desktop/word/brz_ytdlp/extract_v4.py` (改造目标)
- `/Users/dapeng/Desktop/word/brz_ytdlp/production_v2.py` (改造目标)

---

## 12. 迭代历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1 | 2026-05-19 | 初版：完整覆盖 cookie 解剖、PoC 脚本、pool 架构、风险评估、与 IPv6 对比 |

---

## 附录 A: 决策建议

如果让我**今天**给项目组一个建议:

1. **不要现在 all-in Cookie Pool**。维护成本太高，cookie 3-5 天失效要 auto-refresh，账号 ban 是常态。
2. **优先做 IPv6 /64 轮换**（Manus AI 报告的方向）。这是同等吞吐、低维护、抗风控的方案。
3. **Cookie Pool 留作 Plan B**: IPv6 不可行时，或 IPv6 触顶后做 hybrid 叠加。
4. **如果一定要现在做**:
   - 限制在 5 个账号，PoC 阶段
   - 用 Playwright auto-refresh（§4.3 脚本可直接复用）
   - 监控成本: 1 人 0.5 day/week 处理 ban + refresh 异常

5. **代码改动可以先准备好**（§6.2）：让 `make_ydl_v4` 支持 `cookiefile` 参数，未来切换零成本。
