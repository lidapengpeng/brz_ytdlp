# Instagram-Driven YouTube Channel Discovery for BR Creators

> 日期: 2026-05-20
> 状态: Research v1（规划）
> 关联问题: YouTube 算法图谱探完（DB 388K known, dedup 95%+，e/s 跌到 0.3-0.5），需开**算法外**的新数据源
> 预期增量: **30K-150K NEW BR eligibles**（视投入深度）

---

## TL;DR

YouTube 内部 discovery（search、watchEndpoint、related channels）已经触达 ~400K BR pt-BR 频道上限。剩下还在外面的频道，YouTube 算法图谱"看不见"——但**他们大概率出现在 Instagram 上**（巴西是 IG 全球第二大市场，500M+ 月活）。

策略：从 Instagram **bio link** 反向找到 YouTube channel。BR 创作者的 bio 里 70%+ 含 YouTube/Linktree/Beacons 链接。

预期产出：
- **Week 1 spike (零成本)**: Wikipedia + Linktree → **2-5K new eligibles**
- **Week 2-3 (单 IG 账号)**: bio scrape 1-3K BR creators → **10-30K new**
- **Week 4-8 (production)**: 多账号 BFS follower 网络 → **50-150K new**

成本范围：$0 - $300/月（取决于规模）

---

## 1. 背景与动机

### 1.1 为什么 Instagram 是最大未开发金矿

| 平台 | BR 月活 | 创作者倾向 |
|---|---|---|
| Instagram | 134M (Reels) + 113M (Stories 用户) | **几乎所有 BR 创作者必有** |
| YouTube | 150M（含被动观众）| 视频创作者主战场 |
| TikTok | 105M | 短视频偏 GenZ |
| X/Twitter | 24M | 文字+新闻偏多 |

**关键洞察**：BR 创作者的 IG follower count 通常 ≥ YouTube subscriber count。很多 IG influencer 同时有 YouTube 但 YouTube 频道**算法可见性极低**（没被 search/related 触达），导致我们的 YT-only discovery 找不到。

### 1.2 Bio link 经济

BR 创作者 bio 含外链概率：
- 直接 YouTube URL: ~35%
- Linktree / Beacons / Bio.link / Lnk.bio: ~40%
- 自建 landing page: ~10%
- 无链接: ~15%

→ **理论上 75%+ 的 BR IG 创作者可以从 bio 反向找到 YT channel**

### 1.3 当前阻塞

**YouTube discovery 已达 dedup 上限**：
- DB: 182K eligibles + 207K rejected = 389K known
- BFS watchnext yield: 2026-05-19 5.8/seed → 2026-05-20 已跌至 1.5-2/seed（cumulative dedup 60% 衰减）
- e/s sustained: 0.3-0.5（vs 历史峰值 6.96/s）

继续优化 YouTube path 收益递减。必须**开新源**。

---

## 2. 数据源景观

### 2.1 Instagram 官方/半官方 API

| 选项 | 可用性 | 限制 |
|---|---|---|
| Graph API | 需 Business 账号 + Meta 审核 | 只能查自己账号的 follower / insights，**不能爬别人** |
| Basic Display API | **已废弃 2024** | n/a |
| oEmbed | 不限 | 只返回单 post embed，**不含 user data** |

**结论**：官方 API 对我们用例**完全不可用**。

### 2.2 非官方 Python 库

| 库 | 维护活跃 | 关键功能 | 风险 |
|---|---|---|---|
| **[instagrapi](https://github.com/subzeroid/instagrapi)** | ⭐ Active 2026 | 模拟移动端 API，支持 login / bio / followers / hashtag | 账号 7-14 天会 flagged |
| [instaloader](https://github.com/instaloader/instaloader) | Active | 下载导向，能取 user bio | 同上 |
| [aiograpi](https://github.com/subzeroid/aiograpi) | Active | async 版 instagrapi | 同上 |
| [playwright](https://playwright.dev/) | Robust | 真浏览器，最难封但慢 | 100 req/h/账号 |

**推荐**: 主用 `instagrapi`（速度快、API 稳定），关键操作（账号注册、bio 编辑）用 playwright 备用。

### 2.3 商业 scraping 服务

| 服务 | 价格 | 数据质量 | 一次性 vs 持续 |
|---|---|---|---|
| **[Apify Instagram Scraper](https://apify.com/apify/instagram-scraper)** | $0.30 / 1000 profiles | 含 bio + external_url | ✓ pay-per-use |
| [Bright Data Instagram Dataset](https://brightdata.com/products/datasets/instagram) | $1 / 1000 records | 含 follower lists | ✓ |
| [SmartProxy Instagram API](https://smartproxy.com/) | $50/mo 基础 | bio + post + follower | ✗ subscription |
| [SocialBlade API](https://socialblade.com/api) | $0.0025 / call | YouTube + IG ranking lists | ✓ |

**推荐**: Apify 对一次性大批量最划算（如扫 10K profiles 只要 $3）。

### 2.4 邻近数据源（IG 之外的辅助）

| 源 | 价值 | 工程 |
|---|---|---|
| **Wikipedia "Lista de YouTubers brasileiros"** | 几百到 ~2K seed creators | 半天 |
| Forbes BR 30 under 30 / Influencer ranking | 数百 high-tier creators | 1 天 |
| **Linktree public pages (无需 IG 登录)** | 任意已知 BR IG 账号 → 直接获取 Linktree → YouTube URL | 1 天 |
| Twitter/X bio mentioning IG | 跨平台 bridge | 中等 |
| Apple Podcast BR ranking → 主播 IG → YT | 边角金矿 | 中等 |

---

## 3. 总体架构

```
                        ┌──────────────────────────────────┐
                        │  Phase 1: SEED Bootstrap         │
                        │  - Wikipedia BR YouTubers list   │
                        │  - SocialBlade BR top 1000       │
                        │  - 手动 curated ~50 mega-names  │
                        │  → ~1-3K seed IG handles         │
                        └────────────┬─────────────────────┘
                                     │
                        ┌────────────▼─────────────────────┐
                        │  Phase 2: BIO MINING             │
                        │  For each IG handle:             │
                        │  - instagrapi.user_info(handle)  │
                        │  - extract bio + external_url    │
                        │  - resolve Linktree if linked    │
                        │  - parse YouTube channel URL     │
                        │  → ~700-2000 YT URLs found       │
                        └────────────┬─────────────────────┘
                                     │
                        ┌────────────▼─────────────────────┐
                        │  Phase 3: FOLLOWER BFS           │
                        │  For each seed creator's followers│
                        │  - filter: followers_count > 10K │
                        │  - get their bio + repeat        │
                        │  → 10K-100K candidate IG accounts│
                        └────────────┬─────────────────────┘
                                     │
                        ┌────────────▼─────────────────────┐
                        │  Phase 4: YT VALIDATION BRIDGE   │
                        │  - Extract YT channel_id from URL│
                        │  - INSERT INTO ig_discovered_yt  │
                        │  - Push into ch_queue            │
                        │  - extract_v4 验证 country/subs  │
                        │  → DB merge                       │
                        └──────────────────────────────────┘
```

### 3.1 数据流

```
Instagram username  →  bio_data{external_url, biography}
                  ↓
            extract_youtube_url(bio + linktree if linked)
                  ↓
            youtube.com/@handle OR /channel/UC...
                  ↓
            resolve handle → channel_id (yt-dlp 或 fetch HTML)
                  ↓
            INSERT INTO ig_discovered_yt(ig_username, yt_channel_id, source, discovered_at)
                  ↓
            如果 yt_channel_id NOT IN known_ids → push to ch_queue
                  ↓
            extract_v4 → channels OR rejected_channel_ids
```

### 3.2 新增 DB schema

```sql
CREATE TABLE IF NOT EXISTS ig_users (
    ig_username     TEXT PRIMARY KEY,
    full_name       TEXT,
    biography       TEXT,
    external_url    TEXT,                  -- 原 IG external_url (常是 Linktree)
    followers_count INTEGER,
    following_count INTEGER,
    media_count     INTEGER,
    is_private      INTEGER DEFAULT 0,
    is_verified     INTEGER DEFAULT 0,
    country_guess   TEXT,                  -- 'BR' / 'PT' / 'unknown'
    yt_url_extracted TEXT,                 -- 解析出的 YouTube URL
    yt_channel_id   TEXT,                  -- 解析出的 UC* channel_id
    fetched_at      INTEGER NOT NULL,
    source          TEXT                   -- 'seed' / 'follower_of:<handle>' / 'wikipedia' / etc
);
CREATE INDEX idx_ig_yt_channel ON ig_users(yt_channel_id);
CREATE INDEX idx_ig_followers ON ig_users(followers_count);

CREATE TABLE IF NOT EXISTS ig_follower_visited (
    seed_ig         TEXT PRIMARY KEY,
    visited_at      INTEGER,
    n_followers_fetched INTEGER,
    n_yt_extracted  INTEGER
);
```

---

## 4. 阶段执行计划

### Phase 0 — Spike 验证（本周，0 成本）

**目标**: 不用 IG 账号，证明数据源可挖。

**步骤**:

1. **Wikipedia 抓取**（半天）
   ```python
   # Scrape "Lista de YouTubers brasileiros" + 类似页面
   url = "https://pt.wikipedia.org/wiki/Lista_de_YouTubers_brasileiros"
   # 解析 table 提取每行的 名字 + YouTube 链接 + IG 链接
   # 预期 200-500 条记录
   ```

2. **Linktree 直接抓**（半天）
   ```python
   # Linktree 是 public，不需要 IG 登录！
   # 给定 username:
   r = requests.get(f'https://linktr.ee/{username}')
   # parse HTML 中所有 YouTube 链接
   ```

3. **SocialBlade BR top YouTube list**（半天）
   ```python
   # https://socialblade.com/youtube/top/country/br/mostsubscribed
   # 已知 top 1000 BR YouTubers — 但他们大概率已经在我们 DB
   # 价值：取每个的 IG handle（如果 SB 显示）→ 反向用
   ```

4. **手动 seed 列表**（1-2 小时）
   ```python
   # GPT / Claude 给出 100 个最知名 BR creators 名字 + IG handle
   # 包括各 niche:
   # - mega: Anitta, Whindersson, Felipe Neto
   # - 美妆: Boca Rosa, Bianca Andrade
   # - 健身: Renato Cariani
   # - 游戏: Cellbit, Castro brothers
   # ...
   ```

**Phase 0 Verdict**:
- 拿到 ~1-3K **可解析的 IG → YT 映射**
- 其中 cross-check 已有 DB，**估 30-60% 是新 channel = 300-1800 new eligibles**
- 这个数字 OK 但小，验证流程 work 即可

**决策门**: 如果 Phase 0 产出 >500 new eligibles → 进 Phase 1。否则放弃。

---

### Phase 1 — 单账号 IG 直接 scrape（1 周）

**目标**: 用 1 个 IG 账号，扫 1-3K BR creators 的 bio。

**资源**:
- 1 个 IG 账号（手动注册，需要 BR 手机号或国际手机号）
- 1 个住宅代理（巴西 IP 首选，否则美国/欧洲）
- 24-48h "session aging"（账号注册后正常浏览几天，避免立刻 scrape）

**代码**:
```python
from instagrapi import Client
cl = Client()
cl.login(username='your_burner', password='...')

# Bio scrape
for handle in seed_list:
    info = cl.user_info_by_username(handle)
    save_ig_user(info.dict())
    
    # Rate limit: 150/h max
    time.sleep(random.uniform(20, 30))
```

**风险**: 账号 7-14 天会 flagged。准备 backup 账号。

**预期产出**: 1500-3000 bio scraped → 70% 含 external_url → 60% 含 YT → 30% NEW → **300-1300 new eligibles**

**Phase 1 决策门**: 
- ≥ 1000 new eligible → 进 Phase 2 (BFS)
- < 1000 → 重新评估，可能 Apify 一次性买更划算

---

### Phase 2 — Follower BFS（2 周）

**目标**: 在每个 seed 的 followers 里挖更多创作者。

**核心算法**:
```python
def bfs_followers(seed_handle, max_followers=5000, min_followers_count=10000):
    """For a seed, get their followers, filter to creators (>=10K followers)."""
    followers = cl.user_followers(user_id=seed_user_id, amount=max_followers)
    # IG 返回的 followers 是 short user objects, need follow-up call for bio
    creator_candidates = [f for f in followers if f.follower_count > min_followers_count]
    for candidate in creator_candidates:
        info = cl.user_info(candidate.pk)
        if info.external_url:  # has bio link
            yt_url = parse_youtube(info.biography, info.external_url)
            if yt_url:
                save_discovered(handle=candidate.username, yt_url=yt_url)
```

**Scale 估算**:
- 100 mega-seeds × 5000 followers each = 500K candidate followers
- Filter to >10K followers themselves = ~50K creator candidates
- 其中 ~60% 有 bio link → 30K profiles
- ~50% 含 YouTube → 15K YouTube URLs
- ~30% NEW vs our DB → **4-5K NEW eligibles**

**资源升级**: 此时单账号不够，**3-5 个 IG 账号轮换**

**Phase 2 决策门**: ≥ 3K new eligibles → 进 Phase 3 (production)

---

### Phase 3 — Production 多账号 farm（2-4 周）

**目标**: 持续运行的 IG → YouTube 发现 pipeline。

**架构**:
```
IG account pool (10-20 accounts)
  ├─ each runs ~100 req/h (safe)
  ├─ rotate through residential proxies (Brazil mix)
  └─ checkpoint state in DB for resume after ban

Crawler:
  ├─ priority queue: high-follower seeds first
  ├─ BFS depth limit: 2 (seeds → followers → their followers)
  └─ dedup: skip already-visited IG handles

Bridge to YouTube:
  ├─ extract_youtube_url() — handle Linktree/Beacons/etc.
  ├─ resolve handle → channel_id (cached)
  └─ push to brz_ytdlp ch_queue
```

**预期产出**: 持续 10-30 days, total **50K-150K new YT channels mined**
**Conversion to NEW eligibles**: 30-50K（after dedup vs current 388K)

**资源**:
- 10 IG 账号: 注册成本 ~$50（含临时手机号 SMS）
- Residential proxy: Bright Data / SmartProxy ~$100-200/mo
- 服务器（本机够，但建议租 1 VPS 防干扰）: $5/mo
- **Total monthly: $200-300**

---

## 5. 工具/库选型

### 5.1 IG scraping 核心

```python
# requirements
instagrapi>=2.0
requests>=2.32
beautifulsoup4>=4.12     # Linktree HTML parsing
yt-dlp                    # bridge to existing pipeline
```

### 5.2 关键代码模块

```
brz_ytdlp/
├── ig_discovery/                  # NEW module
│   ├── __init__.py
│   ├── account_pool.py            # rotate IG accounts + cooldown
│   ├── bio_extractor.py           # bio → external_url → YT URL
│   ├── linktree_parser.py         # Linktree HTML → all links
│   ├── follower_bfs.py            # BFS algorithm
│   ├── bridge_to_yt.py            # IG-discovered YT URLs → ch_queue
│   ├── seed_loader.py             # bootstrap from Wikipedia/SocialBlade/manual
│   └── rate_limiter.py            # token bucket per account
├── ig_users.db                    # separate SQLite for IG data (don't pollute results.db)
└── (existing files)
```

### 5.3 关键函数（伪代码）

```python
# bio_extractor.py
def extract_youtube_from_bio(biography: str, external_url: str) -> Optional[str]:
    """Extract YouTube URL from IG profile data."""
    YT_PATTERNS = [
        r'(?:youtube\.com/(?:channel/|c/|user/|@))([A-Za-z0-9_-]+)',
        r'(?:youtu\.be/)([A-Za-z0-9_-]+)',
    ]
    # 1. Check bio text directly
    for pattern in YT_PATTERNS:
        if m := re.search(pattern, biography):
            return canonicalize_youtube_url(m.group(0))
    # 2. Check external_url (often Linktree)
    if external_url and 'linktr.ee' in external_url:
        return resolve_linktree(external_url)
    # 3. Direct YouTube external_url
    for pattern in YT_PATTERNS:
        if m := re.search(pattern, external_url or ''):
            return canonicalize_youtube_url(m.group(0))
    return None
```

```python
# linktree_parser.py
def resolve_linktree(linktree_url: str) -> Optional[str]:
    """Linktree public pages don't require login. Parse HTML for YT links."""
    r = requests.get(linktree_url, timeout=10, headers={
        'User-Agent': 'Mozilla/5.0 ...'
    })
    soup = BeautifulSoup(r.text, 'html.parser')
    for a in soup.find_all('a', href=True):
        url = a['href']
        if 'youtube.com' in url or 'youtu.be' in url:
            return url
    return None
```

```python
# account_pool.py
class IGAccountPool:
    """Manages multiple IG accounts with rotation + cooldown."""
    def __init__(self, accounts_config: list[dict]):
        self.accounts = accounts_config  # [{'username': ..., 'password': ..., 'last_used': 0, 'fails': 0}]
        self.cooldown = 30 * 60  # 30 min between uses of same account
        self.max_per_hour = 100
    
    def get_client(self) -> Optional[Client]:
        # Pick least-recently-used account with no recent fails
        candidates = [a for a in self.accounts 
                      if time.time() - a['last_used'] > self.cooldown
                      and a['fails'] < 3]
        if not candidates: return None
        chosen = min(candidates, key=lambda a: a['last_used'])
        chosen['last_used'] = time.time()
        return self._login(chosen)
```

---

## 6. 成本-收益矩阵

### 6.1 各 Phase 投入/产出

| Phase | 工程时间 | 月成本 | 预期 NEW eligibles | $/eligible |
|---|---|---|---|---|
| Phase 0 (Wikipedia + Linktree) | 1 周 | $0 | 1-2K | **$0** ⭐ |
| Phase 1 (单 IG 账号) | 1 周 | $20（proxy） | 5-15K | $1-4 |
| Phase 2 (BFS) | 2 周 | $50 | 30-60K | $0.8-1.6 |
| Phase 3 (Production) | 4 周 | $200-300 | 100K+ | $2-3 |

### 6.2 一次性 vs 持续

**一次性方案**（Apify Instagram Scraper $0.30/1000 profiles）:
- 扫 50K BR creator IG profiles: ~$15
- 加 cross-check 工程: 1 周
- 产出: ~15-25K NEW eligibles
- **$/eligible: $0.001 (比自建便宜)** ⭐⭐⭐
- **缺点**: 一次性，无后续累积

**持续方案**（自建 IG account pool）:
- 月开销 $200-300
- 持续产出 ~10K NEW/month
- 6 个月累计 60K NEW

**建议路径**: Phase 0 (free) → 若 yield 好 → **直接买 Apify 50K profiles $15** → 跳过 Phase 1/2 → 评估是否进 Phase 3 production。

---

## 7. 风险与缓解

### 7.1 IG 账号封禁

**风险**: scraping detection → 账号永封 → 数据中断

**缓解**:
- 账号 7-14 天注定要换。备 backup 池
- 单账号 100 req/h 极限，超了就 rest 1-2h
- 用 residential proxy（巴西 IP 最匹配，否则美国/欧洲）
- 偶尔做"人类操作": 点赞、评论几个 post，让 session 看似真人

### 7.2 Linktree/外链解析失败

**风险**: bio link 跳转链 多变（Linktree → Bio.link → 自建 →...）

**缓解**:
- 优先 Linktree（公开 HTML 易解析）
- 5 个最常见 bio link 平台都实现 parser
- 解析失败的归到"unknown bio source"待人工查（人工核个 1K 不到 2 小时）

### 7.3 法律 / TOS

**Instagram TOS** 禁止自动化 scraping。**风险**:
- 个人账号 ban（已 covered above）
- 极端情况：Meta 起诉（**对小规模个人项目极不可能**，hiQ Labs v LinkedIn 判决支持 public data scraping，IG 公开 bio 属于 public data）

**缓解**:
- 只爬 public profile（不爬 private）
- 不重新发布 IG 内容（仅提取 outgoing links）
- 不用爬到的数据做营销 / 商业模型（仅作为 YT 频道发现 seed）

### 7.4 数据质量

**风险**: 拿到的 YT URLs 大量是 outdated/失效（很多用户 bio 几年没改）

**缓解**:
- 拿到 YT URL 后立刻 extract_v4 验证
- 失效的直接进 rejected_channel_ids
- 跟踪 hit rate（valid YT URLs / bio scraped）

---

## 8. 集成现有 brz_ytdlp pipeline

### 8.1 双 DB 设计

```
ig_users.db          (新, ~100MB)
  ├── ig_users
  ├── ig_follower_visited
  ├── ig_seed_queue
  └── events

results.db (现有)
  ├── channels        ← extract_v4 写入 (existing flow)
  ├── rejected_channel_ids
  └── bfs_visited
```

**bridge 步骤**: ig_users.yt_channel_id 不在 results.db 的 known_ids → push 到 results.db 的 ch_queue → existing pipeline 验证。

### 8.2 命令行接口

```bash
# Phase 0 一次性运行
./.venv/bin/python -m ig_discovery.bootstrap --source wikipedia --output ig_users.db

# Phase 1+ 启动持续 scraping
./.venv/bin/python -m ig_discovery.run --accounts accounts.json --depth 2

# Bridge to YT pipeline (run periodically, e.g. cron every 1h)
./.venv/bin/python -m ig_discovery.bridge --push-to ch_queue
```

### 8.3 与现有 production_v2.py 共存

无需修改 production_v2.py。ig_discovery 独立运行，**只**通过 `INSERT OR IGNORE` 给 results.db 写入新 cid（让 production_v2 的 validator 后续 extract）。

---

## 9. MVP / Quick wins（本周可做）

按时间从小到大排：

### 9.1 1 小时 — 手动 mega-seeds 测试
```python
# 给定 30 个最知名 BR creators，手动找 IG → bio → YT
# 99% 都已经在 DB，但作为 sanity check
# 这一步验证 extract_youtube_from_bio 函数 work
```

### 9.2 半天 — Wikipedia BR YouTubers list
```python
# Scrape pt.wikipedia.org "Lista de YouTubers brasileiros"
# 250 known names, 50-80% has YT link directly in wiki
# Direct path, no IG needed
```

### 9.3 1 天 — Linktree exploration
```python
# 给定已有 DB 中 5K 个 BR channels (subs>=10K)，
# 反查每个的 about page 是否有 IG/Linktree link
# 如果有 → 拉 Linktree → 看是否有 OTHER YouTube links (collab 频道 etc.)
# 完全不需要 IG 账号
```

### 9.4 1 周 — 单 IG 账号 spike
```python
# 注册 1 个临时 IG 账号
# 用 instagrapi 爬 1000 个 mega-creator 的 bio
# 测试 hit rate + conversion
```

---

## 10. 决策树

```
NOW: 388K known_ids, e/s 0.5, dedup 95%
  │
  ▼
Phase 0 spike (Wikipedia + Linktree, this week, $0)
  │
  ├── Yields > 1K new eligibles?
  │   ├── YES → invest in MVP Phase 1
  │   └── NO → consider Apify $15 one-shot
  │
  ▼
Phase 1 (1 IG account, 1 week, $20)
  │
  ├── Yields > 5K new eligibles?
  │   ├── YES → Phase 2 (BFS, $50/mo)
  │   └── NO → revert to YT-only, accept 400K ceiling
  │
  ▼
Phase 2 (multi-account, 2 weeks, $50-100/mo)
  │
  ├── Yields > 30K new?
  │   ├── YES → Phase 3 production farm ($200-300/mo)
  │   └── NO → keep at Phase 2 scale
  │
  ▼
Phase 3 (production, 1+ month, $200-300/mo)
  │
  → Sustain 700K target
```

---

## 11. 关键开放问题

1. **YouTube handle 唯一性**: IG bio 里写 "youtube.com/@xyz" 时，@xyz 可能是 channel handle 也可能 video ID（罕见）。需要 fetch + resolve 到 UC*。
   - 解决方法：用 yt-dlp 的 `youtube:handle` 提取器，或直接 fetch `youtube.com/@handle` 看 HTML 含 channel_id。

2. **Linktree 之外的 bio link 服务**: 至少 10 个常见（Beacons, Bio.link, Lnk.bio, Allmylinks, Linkin.bio, Carrd, etc.）。要不要全做，还是只 Linktree（占 65%+ 份额）？
   - 推荐：Linktree + Beacons + Bio.link 三个覆盖 80%+。其他 10% 单独存"unknown bio_source"，**累积到 500 个后人工 review**。

3. **BR 判定**: IG profile 不直接说 country。怎么判断 IG user 是 BR？
   - bio 文字 pt-BR + 经典 BR 关键词（brasil/sao paulo/rio/etc.）
   - external_url 域名（.com.br）
   - **最简单**: 一开始只爬 seed 的 followers（seed 都 BR → followers 大概率 BR）

4. **Follower lists access**: IG 严格限制 follower API. 单账号每天上限 ~500 follower list calls.
   - 解决方法：账号池 + 缓存 follower lists（每个 seed 只爬一次）

5. **Apify 数据更新频率**: 商业服务有 cache，可能数据是 1-3 月旧的。新晋创作者会漏掉。
   - 推荐：核心做自建 fresh scrape；Apify 仅一次性补底（buy known top 50K）

---

## 12. 时间线建议

### Sprint 1（本周，1 周）— Phase 0 spike
- 周一: bootstrap module 设计 + Wikipedia scraper
- 周二: Linktree parser + 现有 5K BR channels 反查
- 周三-周四: 手动 mega seeds 测试 + 写 extract_youtube_from_bio
- 周五: 评估产出，决定是否买 Apify 或自建 IG

### Sprint 2-3（下周开始，2 周）— Phase 1 + 决策
- 注册第 1 个 IG 账号 + 24h aging
- 写 ig_discovery 模块基础架构
- 跑 1000 BR creator bio scrape
- 评估 yield，决定是否进 Phase 2/3

### Sprint 4+（看情况）— Phase 2/3 长期
- 账号池
- BFS
- 持续运行 + monitoring

---

## 13. 备选方案 — 如果 IG 路径整体不通

如果 Phase 0 spike 显示 Wikipedia + Linktree 也产出 < 1K new eligibles，说明：
- 我们的 DB 已经包含**所有公开可发现的 BR creators**
- 剩下的 BR YouTube channels 是"地下"的（不上 Wikipedia 也不上 IG）
- 700K target 可能本身不现实

那时考虑：
- **降低 BR 判定阈值**：lang_recovered cohort 扩展，subs>=500，包含 Portugal/PT-Africa
- **接受 ~400K ceiling**
- **改攻方向**: 不抓更多频道，对现有 200K 频道做更深的 metadata（视频数、发布频率、最近活跃度等），提供更丰富的下游分析价值

---

## 14. 参考资料

### Instagram scraping libraries
- [instagrapi](https://github.com/subzeroid/instagrapi) — Python mobile API client
- [instagrapi docs](https://subzeroid.github.io/instagrapi/) — comprehensive API ref
- [instaloader](https://github.com/instaloader/instaloader) — alt library, download-focused

### Aggregator services
- [Apify Instagram Scraper](https://apify.com/apify/instagram-scraper)
- [Bright Data Instagram Datasets](https://brightdata.com/products/datasets/instagram)
- [SocialBlade API](https://socialblade.com/api)

### Legal precedent
- hiQ Labs v LinkedIn (2019, 2022) — US 9th Circuit, public data scraping permitted
- Meta v Bright Data (2024) — Meta lost, public IG data scraping permitted

### BR creator landscape
- [Forbes Brasil Influencers list](https://forbes.com.br/forbes-lifestyle/influenciadores)
- [Wikipedia: Lista de YouTubers brasileiros](https://pt.wikipedia.org/wiki/Lista_de_YouTubers_brasileiros)
- [SocialBlade BR top YouTube](https://socialblade.com/youtube/top/country/br)

---

## 15. Iteration history

### v1 (2026-05-20, this doc)
- Initial planning after YouTube discovery wall hit (388K known, e/s dropped to 0.5)
- 4-phase plan defined: spike → single account → BFS → production
- Cost-benefit matrix shows Phase 0 (free) is correct first step
- Apify $15 one-shot identified as potential shortcut

### Future
- v2 (after Phase 0 spike): actual yield numbers, decide Phase 1 / Apify / abandon
- v3 (after Phase 1): Phase 2 BFS feasibility
- v4 (after Phase 2): production farm architecture finalized
