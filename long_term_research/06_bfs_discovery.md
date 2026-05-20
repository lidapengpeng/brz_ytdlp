# BFS Discovery 专项调研

> 日期: 2026-05-19  
> 状态: Research v1（持续迭代中）  
> 关联问题: query-based discovery 的 81% dedup 重叠，需要开辟新 cid 池

## TL;DR

1. **YouTube 在 2024-2025 已经移除了独立 `/channels` tab**（yt-dlp `_tab.py:1944,1978` 自己的测试都标了 "channels tab removed"）。`params=EghjaGFubmVscw==` 现在被忽略，返回 = 默认 home tab。
2. **唯一有产出的 surface 是 home tab 的 `gridChannelRenderer`**（"Outros Canais"、"Collabs"、"Canal Principal" 等 shelf 里的关联频道）。
3. **实测**: 40 个真实 seeds (mid/huge/lang_rec/small)，每个 seed 平均产出 **0.25–3.25 个 new cid**（与 DB 105K eligible+79K rejected 去重后），但 BFS 输出的 **BR 转化率 = 63.2%**（vs query-based ~10-15%），明显更精准。
4. **Huge seeds (>=1M subs) 是最佳输入**：avg 5.62 cid / 3.25 new，且对 Brazil 高度聚类；mid (10K-1M) 平均 2.87/1.6；small 和 lang_rec 普遍 0–1 cid（这些频道根本没 collab shelf）。
5. **集成方案**：BFS 不替代 query disc，做**第三条 round-robin 策略**，专挑 105K eligible 中 subs>=100K 的 ~20K seed（按 RANDOM ORDER）轮询一遍 —— **理论新增上限 ~60K 新 cid**（实际可达 ~25-35K，受 BR 聚类 + DB 已知度影响）。代码改动只需在 `discovery_compare.py` 加一个新函数 + `production_v2.py` 加一个新 strategy entry + 一张 `bfs_visited` 小表，**~80 行**。

---

## 1. 背景与问题陈述

### 1.1 当前 query-based discovery 的瓶颈

- query_bank.txt: 36,138 个 pt-BR query
- 每 query 用 2 个策略（channel_filter + video_owners）round-robin
- 单 query 平均产出 ~30 个 candidate cid（discovery_compare.py:90, 134）
- 当前 DB: 105,941 eligible + 79,523 rejected = **184,981 known IDs**
- 在 production_v2 监控中观测到 dedup overlap ~81%（即 19% 的 cid 是新的）
- 越往后跑 overlap 越高，因为 query bank 在 cycle 里轮流抽，36K query 总共产出 1.8M cid 不到。最终瓶颈是 **query bank 的可达 cid 池有限**。

### 1.2 BFS 的角度

BFS 不依赖 query bank，而是从已有的 105K eligible 频道**自己的页面**抓 related/collab/channel-mention。即：

> "每个 BR 频道的首页可能链接到其它 BR 频道；这些 link 的 union 是 query-based 探不到的新 cid 池。"

理论上：105K eligible × 若干 related per seed = O(100K-1M) candidate，但实际去重 + 噪音后存量在 30-50K 量级。

---

## 2. YouTube channel 页面的 related-channel surfaces

### 2.1 `/channels` tab（已 deprecated）

**结论：基本死了。**

- params `EghjaGFubmVscw%3D%3D` 解码 = protobuf `\x12\x08channels`（字段标识 + 字符串 "channels"）。
- 历史上这个 tab 列 owner 关注的频道（"FEATURED CHANNELS"）。
- 2024-2025 YouTube 后台改版后：tab 在 UI 消失；API 调 params=EghjaGFubmVscw== 返回的 response **不再包含 `channels` tab title** —— YouTube 把这个 param 当 unknown，回的就是默认 home tab 的内容。
- 证据：
  - 实测 6 个 PDF cited 频道（10M Garena, ElectroBOOM, Olympics 16M, YouTube, 166K Cortes do Mylon, 215K IMPERA），tab list 全是 `[Início, Vídeos, Shorts, Ao vivo, Podcasts, Playlists, Posts]`，**无 "Canais"**。
  - yt-dlp source `_tab.py:1944` 注释: `# TODO: channels tab removed`
  - `_tab.py:1978`: `'skip': 'channels tab removed'`

- yield 估算：**0**（功能已废）

### 2.2 Home tab `gridChannelRenderer`（核心 surface）

**唯一实测有产出的 surface。**

Channel home tab（`browseId=UC…`，无 params 或 params=featured `EghmZWF0dXJlZA==`）的 response 里，`shelfRenderer.content.horizontalListRenderer.items[*].gridChannelRenderer` 包含关联频道。

中等 BR 频道实测 shelves 命名（葡语）：
- `"Outros Canais"`（其他频道）
- `"Canal Principal"`（主频道，常见于 cut/highlight 二号频道指向主号）
- `"Collabs"`（合作频道）
- `"Nossos canais"` / `"My favorite channels"`
- `"Our other channels!"`

- 实测每个频道返回的 channel id 数量：
  - **mid (10K-1M BR)**: avg 2.87 total, avg 1.60 new vs DB
  - **huge (>=1M BR)**: avg 5.62 total, avg 3.25 new vs DB
  - **lang_recovered (country=None,lang=pt)**: avg 0.25 — 几乎没有
  - **small (1K-10K BR)**: avg 0.60 — 几乎没有

- API 调用成本：1 次 browse call ≈ 0.5–0.6s wall clock，~50KB response
- 单 seed 整体 yield = 0.25 ~ 3.25 new cid

### 2.3 About panel 的 description 链接

**约等于 0 产出。**

- Stage 2（about panel token + continuation）拿到的 `aboutChannelViewModel.description` 里偶尔会有 `@handle` 文本，但 InnerTube 已经把 `@handle` 解析成 `browseEndpoint.browseId=UC...`。
- 实测一个 BR 频道（Filtr Kids Brasil 16 个 home channelRenderer 的 case），about panel 抓到的 UCxxx **只有 seed 自己**。
- 极少数频道（如教程类）会在描述里推荐多个频道；但要 stage2 额外一次 API call，成本高于收益。

- yield 估算：**< 0.1 / seed**，不值得专门开 surface。

### 2.4 Comments section（comment 挖矿）

**理论可行但风险高，本研究暂不实施。**

- yt-dlp 内部支持 comment extraction（`yt_dlp.extractor.youtube._video.YoutubeIE._extract_comment_entries`），调 InnerTube `next` endpoint with comment continuation。
- 每条 comment 的 `commentRenderer.authorEndpoint.browseEndpoint.browseId` 就是 commenter UC.
- 风险：
  - 评论区 commenter 绝大多数是消费者（subs<1k），noise ratio 估 80-95% 浪费。
  - 取 100 条 comment 大概拿 80 个唯一 cid，但 eligible（subs>=1K BR）大约只有 5-10 个 = 5-10% 转化（比 query-based 还差）。
  - comment fetch 比 channel browse 慢 2-3 倍。
- 结论：**不优先实施**。等 BFS + query 都耗尽后再考虑。

### 2.5 视频描述 @mentions

- 同样需要先抓视频列表 → 拿到 video id → 调 `/next` 拿 description → 抓 @handle
- 多一层 indirection，链路成本远高于 home tab。
- yield 估算：单 seed 平均 < 1 个新 cid（大部分视频描述只 promo 自家频道）

### 2.6 surface 汇总比较表

| Surface | API calls/seed | yield/seed | BR conv | 推荐 |
|---|---|---|---|---|
| `/channels` tab | 1 | **0**（已死） | n/a | ❌ |
| **Home tab `gridChannelRenderer`** | **1** | **0.25–3.25** | **63%** | ✅ **主力** |
| About description | +1 (stage2) | <0.1 | unknown | ❌ |
| Video description | 2-3+ | <1 | unknown | ❌ |
| Comments | 3+/page | 5-10/100 comment | ~5-10% | 推迟 |
| Featured Channels widget | n/a（YouTube 已合并进 home tab） | — | — | n/a |

---

## 3. 实测数据

### 3.1 Home tab 实测（41 个真实 BR seed × 4 个 cohort）

实验脚本: `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_experiment_v2.py`  
原始 dump: `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_experiment_v2_results.json`

**Aggregate**（41 seeds 跑完 = 123 次 surface call）：

| cohort | n_seeds | avg_total | avg_new | avg_eligible_hit | avg_dup% | avg_time |
|---|---|---|---|---|---|---|
| mid (10K-1M BR) | 15 | 2.87 | 1.60 | 1.27 | 44.2% | 0.55s |
| huge (>=1M BR) | 8 | 5.62 | 3.25 | 2.00 | 42.2% | 0.57s |
| lang_recovered pt | 8 | 0.25 | 0.25 | 0.00 | 0.0% | 0.51s |
| small (1K-10K BR) | 10 | 0.60 | 0.30 | 0.30 | 50.0% | 0.51s |

观察：
1. **huge 是 winner**：每 seed 3.25 个新 cid，44% 已经命中 DB eligible（说明 BR 同质性高）。
2. **mid 也可用**：1.6 new/seed，但要注意 1/3 的 mid seed 完全返回 0 cid（没 collab shelf 的频道）。
3. **lang_rec 和 small 没用**：这些频道没有 curated home，只有 video grid，调它们浪费 API call。
4. **每次调用 ~0.55s** — 比 query search 略快（query 通常 1.0-1.5s）。

### 3.2 BR 转化率实测（38 个 BFS-discovered new id 全跑 extract_v4）

实验脚本: `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_validate_new.py`  
原始 dump: `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_validate_new_results.json`

```
Total validated: 38
  errors: 0
  short-circuited (subs<1k): 4   (10.5%)
  BR confirmed (country=Brasil/Brazil): 23  (60.5%)
  Non-BR with confirmed country: 7  (18.4%)
  country=None (no lang_rec): 4  (10.5%)
  is_target=True (eligible): 24  (63.2%)
```

**对比 query-based**（discovery_compare.py 历史数据）：
- channel_filter strategy: ~10-13% 转化率
- video_owners strategy: ~13-17% 转化率

**BFS 转化率 63.2% 是 query-based 的 4-5 倍**。

噪音来源（7 个 non-BR）：全部来自 1 个 seed `Filtr Kids Brasil` —— 这个频道收录全球 Kids Tv 系列（Romania, Thailand, India, Sweden, USA, Arabic, Argentina）作为 collab，是个**国际 IP 频道**。提示 BFS 应当过滤 seed 类型，对国际 IP 系列号要谨慎。

Sample BR targets 命中（看名字明显是 BR）：
- `UC616AjTPQBY1MMbpEuUoO9A` Tubal do Vale 508K
- `UCurtF2FbeqdbK7VTHTWGHXA` Woods 593K
- `UCAYWcsIdvkXoM6_azdVirlA` A Turma do Balão Mágico 727K (lang_recovered)

### 3.3 调用 surface params 的实测对比

把同一个 seed（Filtr Kids Brasil）调三个 endpoints：
- `params=EghjaGFubmVscw==`（/channels）→ 16 个 channel id
- 无 params（home tab） → 16 个 channel id (相同！)
- `params=EgVhYm91dPIGBAoCEgA=`（about tab） → 16 个 channel id (相同！)

**YouTube 把 unknown/legacy params 当成 home tab 处理。** 这意味着我们应该用最简单的 `{"browseId": cid}`（不传 params），少传一个字段。

---

## 4. Seed 优先级策略

### 4.1 实测推荐：huge + 部分 mid，跳过 small/lang_rec

| 层级 | 描述 | SQL | 数量 | 期望 new/seed | 期望总收益 |
|---|---|---|---|---|---|
| L1 huge | subs>=1M BR | `WHERE is_target=1 AND subscribers>=1000000 AND country IN ('Brazil','Brasil')` | ~3,730 | 3.25 | ~12K new cid |
| L2 large | subs 100K-1M BR | `WHERE is_target=1 AND subscribers BETWEEN 100000 AND 999999 AND country IN ('Brazil','Brasil')` | ~17K | ~2.5 (插值) | ~42K new cid |
| L3 mid | subs 10K-100K BR | `WHERE is_target=1 AND subscribers BETWEEN 10000 AND 99999 AND country IN ('Brazil','Brasil')` | ~37K | 1.0 (部分有 collab) | ~37K new cid |
| L4 skip | subs<10K, lang_rec | — | ~48K | <0.3 | ~14K，但浪费 48K API call —— **不值** |

**优先级顺序 L1 → L2 → L3**。L4 跳过。

实际可去重收益（一次 pass，**理论上限**）：
- L1 + L2 + L3 全跑一次 = ~57K seeds × ~1.5 new/seed avg = **~85K candidate**
- 经过 BR 转化（63%）+ subs>=1k 过滤（90%）= **~48K eligible candidate**
- 再扣除 DB 已知去重（粗估 30-40% 重叠，因为 BFS 是网络结构走，命中已有 cluster）= **~30-35K 真正新增 eligible**

### 4.2 推荐执行 SQL

```sql
-- 选 BFS seeds，按 subs 降序、再 RANDOM tiebreak 避免反复跑同一 cluster
CREATE TABLE IF NOT EXISTS bfs_visited (
    seed_cid    TEXT PRIMARY KEY,
    visited_at  INTEGER NOT NULL,
    n_yielded   INTEGER,
    n_new       INTEGER
);

-- 从 channels 里选下一批 seeds
SELECT c.channel_id, c.subscribers
FROM channels c
LEFT JOIN bfs_visited v ON c.channel_id = v.seed_cid
WHERE c.is_target = 1
  AND c.subscribers >= 10000
  AND c.country IN ('Brazil', 'Brasil')
  AND v.seed_cid IS NULL          -- 未访问过
ORDER BY c.subscribers DESC, c.discovered_at ASC
LIMIT 100;
```

### 4.3 不同 cohort 应分批处理

- **Phase 1**: subs>=1M (huge) —— ~3700 seeds，预计 12-15K new
- **Phase 2**: subs 100K-1M (large) —— ~17K seeds，预计 30-40K new
- **Phase 3**: subs 10K-100K (mid) —— ~37K seeds，预计 30-40K new（衰减后实际更少）

每个 phase 跑完 → 评估 yield curve → 决定是否进 next phase。

---

## 5. 去重 + 防环设计

### 5.1 Schema 增量

```sql
-- BFS 已访问过的 seed（防止反复 browse 同一频道）
CREATE TABLE IF NOT EXISTS bfs_visited (
    seed_cid    TEXT PRIMARY KEY,
    visited_at  INTEGER NOT NULL,
    n_yielded   INTEGER,           -- 这次返回多少 cid
    n_new       INTEGER,           -- 其中新的多少（未在 channels/rejected 里）
    depth       INTEGER DEFAULT 1  -- 留作多层 BFS 的扩展
);
CREATE INDEX IF NOT EXISTS idx_bfs_visited_at ON bfs_visited(visited_at);
```

无需 in-memory 状态，每次 worker 起来 SELECT 一批未访问的 seed 即可。

### 5.2 防环算法

BFS 本身就是 set-based（已 visited 不再访问），但单 worker 多并发场景下要：

1. **claim 阶段**: worker 用 `INSERT OR IGNORE INTO bfs_visited(seed_cid, visited_at, n_yielded, n_new) VALUES (?, ?, NULL, NULL)` 占位，主键冲突就 retry next seed
2. **disco 阶段**: 调 home tab → 抓 cid list
3. **dedup**: 与 `channels.channel_id` ∪ `rejected_channel_ids.channel_id` ∪ session `seen_channels` 去重
4. **enqueue**: 新 cid 放入 validator queue
5. **update**: `UPDATE bfs_visited SET n_yielded=?, n_new=? WHERE seed_cid=?`

并发安全：claim 阶段的 INSERT OR IGNORE 是 SQLite 原子的，多 worker 同时跑也只一个能 claim。

### 5.3 深度限制

| 深度 | 描述 | 期望收益 | 风险 |
|---|---|---|---|
| 1 | 只用现有 105K eligible 当 seed | 30-40K new | 低 |
| 2 | 把 depth-1 找到的新 cid 当 seed 再跑一轮 | 衰减厉害（已知 cluster 命中率高），增量可能 5-10K | 中（被 YouTube 视为爬虫） |
| 3+ | 几乎无收益 | — | 高 |

**建议 depth=1 起步**，跑完一轮看数据再决定是否进 depth=2。

---

## 6. 整合到 production_v2.py

### 6.1 改动概览

| 文件 | 改动 | 行数 |
|---|---|---|
| `discovery_compare.py` | 修复 `discover_via_bfs` —— 改为不传 params，直接调 home tab | 改 5 行 |
| `production_v2.py` | 加 `discover_via_bfs_seeded` worker，启动时建 `bfs_visited` 表 | +50 行 |
| **schema 增量**（init_db） | 加 CREATE TABLE bfs_visited | +8 行 |
| Run script (terminal_runner.py) | 加 `--bfs-workers` 参数 | +5 行 |

合计 **~70-80 行**。

### 6.2 discovery_compare.py 修复

把现有 `discover_via_bfs` 改为不传死的 channels params（YouTube 已忽略），改用更稳定的 home tab，并扩大 ID 抓取（用前面验证过的 harvest 逻辑）：

```python
# discovery_compare.py:159 - 替换现有 discover_via_bfs
def discover_via_bfs(seed_channel_id: str, limit: int = 30) -> Tuple[List[str], dict]:
    """Strategy C: visit seed's home tab and harvest collab/featured channels.

    NOTE: /channels tab is removed by YouTube post-2024 (yt-dlp _tab.py:1944, 1978).
    The home tab response (no params) contains gridChannelRenderer in
    shelfRenderer items — these are the "Outros Canais" / "Collabs" / "Canal
    Principal" shelves. Average yield: 0.6 (small) / 1.6 (mid) / 3.25 (huge BR).
    BR conversion rate ~63%, vs ~12% for query-based.
    """
    ydl = _make_ydl_for_search()
    ie = ydl.get_info_extractor("YoutubeTab")
    t0 = time.time()
    # NO params — pre-2024 EghjaGFubmVscw== returns same as home now
    resp = ie._call_api(
        ep="browse", video_id=seed_channel_id,
        query={"browseId": seed_channel_id},
    )
    elapsed = time.time() - t0
    ids: List[str] = []
    seen: Set[str] = set([seed_channel_id])
    # Two complementary renderers
    for r in _find_all(resp, "gridChannelRenderer"):
        if isinstance(r, dict):
            cid = r.get("channelId")
            if cid and cid not in seen and cid.startswith("UC"):
                seen.add(cid); ids.append(cid)
                if len(ids) >= limit: break
    for r in _find_all(resp, "channelRenderer"):
        if isinstance(r, dict):
            cid = r.get("channelId")
            if cid and cid not in seen and cid.startswith("UC"):
                seen.add(cid); ids.append(cid)
                if len(ids) >= limit: break
    return ids, {"elapsed_s": elapsed, "response_bytes": len(json.dumps(resp))}
```

### 6.3 production_v2.py: 新 BFS worker

加到 SCHEMA：

```python
SCHEMA = """
...
CREATE TABLE IF NOT EXISTS bfs_visited (
    seed_cid    TEXT PRIMARY KEY,
    visited_at  INTEGER NOT NULL,
    n_yielded   INTEGER,
    n_new       INTEGER,
    depth       INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_bfs_visited_at ON bfs_visited(visited_at);
"""
```

在 `run_pipeline` 里加：

```python
# BFS seed queue —— 从 DB 拉未访问的 huge/large/mid BR seed
bfs_seed_queue: asyncio.Queue = asyncio.Queue(maxsize=500)

async def bfs_seed_loader():
    """Periodically refills BFS seed queue from DB."""
    while not stop_event.is_set():
        # Refill when queue is low
        if bfs_seed_queue.qsize() < 50:
            async with db_lock:
                rows = list(db_conn.execute("""
                    SELECT c.channel_id, c.subscribers
                    FROM channels c
                    LEFT JOIN bfs_visited v ON c.channel_id = v.seed_cid
                    WHERE c.is_target=1
                      AND c.subscribers >= 10000
                      AND c.country IN ('Brazil','Brasil')
                      AND v.seed_cid IS NULL
                    ORDER BY c.subscribers DESC
                    LIMIT 200
                """).fetchall())
            for cid, _subs in rows:
                # claim it now via INSERT OR IGNORE
                async with db_lock:
                    cur = db_conn.execute(
                        "INSERT OR IGNORE INTO bfs_visited (seed_cid, visited_at) VALUES (?, ?)",
                        (cid, int(time.time())))
                    if cur.rowcount == 0:
                        continue   # someone else claimed it
                await bfs_seed_queue.put(cid)
            if not rows:
                # DB exhausted — sleep before retry
                await asyncio.sleep(60)
        await asyncio.sleep(5)

async def bfs_worker(worker_id: int):
    """Pulls seed cid from bfs_seed_queue, harvests related, queues into ch_queue."""
    wid = ("bfs", worker_id)
    _set_state(wid, "spawned", "")
    while not stop_event.is_set():
        try:
            seed = await asyncio.wait_for(bfs_seed_queue.get(), timeout=10.0)
        except asyncio.TimeoutError:
            continue
        _set_state(wid, "bfs_browse", seed)
        try:
            ids, _meta = await loop.run_in_executor(disc_pool, discover_via_bfs, seed, 30)
        except Exception:
            continue
        async with seen_lock:
            new_ids = [c for c in ids if c not in seen_channels and c not in known_ids]
            for c in new_ids: seen_channels.add(c)
        # Update bfs_visited with yield stats
        async with db_lock:
            db_conn.execute(
                "UPDATE bfs_visited SET n_yielded=?, n_new=? WHERE seed_cid=?",
                (len(ids), len(new_ids), seed))
        counters.discovered += len(new_ids)
        for cid in new_ids:
            if stop_event.is_set(): return
            try:
                await asyncio.wait_for(ch_queue.put(cid), timeout=10.0)
            except asyncio.TimeoutError:
                break
```

并 spawn：

```python
# 在 disc_tasks + val_tasks 之外，加 BFS pool
bfs_seed_task = asyncio.create_task(bfs_seed_loader())
bfs_workers = 3   # 比 disc workers 少 —— BFS API call 快但 yield 不同
bfs_tasks = [asyncio.create_task(bfs_worker(i)) for i in range(bfs_workers)]
```

记得 finally 块 cancel + gather。

### 6.4 添加新 import

```python
from discovery_compare import discover_via_bfs   # 现有就是 line 24 那块加一个 entry
```

### 6.5 频率/比例建议

- **disc_workers=10**（query-based）
- **bfs_workers=3** （BFS）
- validation pool 共用一个 80-worker pool（不变）
- 预期 BFS 贡献 disc rate 的 20-30%，但贡献 eligible rate 的 30-40%（因为转化率高 4-5 倍）

### 6.6 监控指标增量

在 `monitor()` 里加：

```python
async with db_lock:
    n_visited = db_conn.execute("SELECT COUNT(*) FROM bfs_visited").fetchone()[0]
    n_with_yield = db_conn.execute("SELECT COUNT(*) FROM bfs_visited WHERE n_yielded IS NOT NULL").fetchone()[0]
print(f"  bfs: visited={n_visited} yielded={n_with_yield}")
```

---

## 7. 预期收益

### 7.1 单 pass 理论上限

| Phase | Seeds | avg new/seed | 单 pass new candidates | BR 转化 (63%) | 真正新增 eligible |
|---|---|---|---|---|---|
| 1 (huge, ≥1M) | 3,730 | 3.25 | 12,120 | 7,640 | ~6,500（部分重复） |
| 2 (large, 100K-1M) | 17,000 | 2.5 | 42,500 | 26,775 | ~18,000 |
| 3 (mid, 10K-100K) | 37,000 | 1.0 | 37,000 | 23,310 | ~12,000 |
| **Total** | **57,730** | **avg 1.59** | **91,620** | **57,725** | **~36,500** |

实际数字会受 BR cluster 同质性（已知频率高）拖累，**保守估计 25K–35K new eligible 增量**。这是 query-based 当前 ~5K/天 速率的额外 ~一周量。

### 7.2 API call 成本

- 57,730 seeds × 1 home tab call = **57,730 API calls** (BFS 部分)
- 当前 production 已经在 ~50K-100K calls/day，BFS 一次 pass 一两天就跑完
- 显著比 query-based 经济：query-based 一次 search 平均产出 1.6 个 eligible，BFS 一次 browse 平均产出 ~0.6 eligible —— 但 BFS API call 时间更短（0.55s vs 1.2s），且不需要 query 输入

### 7.3 是否突破 700K 终极目标

700K 总目标的 path：
- 已有 105K
- query-based 还能加 ~50-80K（query bank 总池子估 ~300K eligible 上限）
- **BFS 一次 pass 加 ~30K**
- BFS depth-2 再加 ~10-15K
- 长尾：sitemap、recommended、playlists 还可挖 ~10-20K

**BFS 是这条路上 single biggest 单一增量 source**。

---

## 8. 风险 & 开放问题

### 8.1 YouTube 端风险

1. **BFS 是否会被 YouTube 视为爬虫并触发 captcha？**
   - 大量短时间访问相同 channel home tab 的 fingerprint 与正常用户不同
   - 当前 production 已经有 IP rotation + visitor_data 随机化 + 5 个 client UA，BFS 沿用就行
   - **缓解**: BFS rate 控制 ≤ 6 req/s/IP，且与 query-based 工作流交错（disc + bfs 不在同一时间段集中）

2. **Related channels 是否长期稳定？**
   - 同一个 seed 多次访问，YouTube 返回内容**理论上是 owner-curated**（owner 在 YouTube Studio 设置），所以稳定。
   - 但首页的"Collabs"shelf 可能含 YouTube 算法推荐成分（带 personalization）
   - **建议**: 同一 seed 跑过一次后不重跑（visited set 永久），depth=2 可以晚一两周再跑

3. **shelf 命名是国际化的**
   - 葡语: "Outros Canais", "Canal Principal", "Collabs", "Nossos Canais"
   - 英文: "Featured Channels", "Other Channels"
   - 我们 harvest 是基于 `gridChannelRenderer` / `channelRenderer` 的 channelId 字段，**与 shelf 标题无关** —— 不会破

### 8.2 数据质量风险

1. **BR cluster 同质性**: huge BR 频道的 collab 大概率也是 BR（实测 60.5% 直接 country=Brasil 命中），但有 outlier（如 Filtr Kids Brasil 引出全球 Kids Tv），需 country 过滤。
2. **Lang_recovered 命中可能性**：BFS 引出 country=None 频道少（38 个里只有 1 个 lang_recovered=pt），所以 BFS 主要扩大 country=Brasil cohort 而非 lang_recovered cohort。要扩 lang_recovered 还得靠 query 或专门的 description scan。

### 8.3 开放问题

- **Q1**: depth-2 BFS 的真实收益是否值得 API call？需要先跑完 depth-1 再实测。
- **Q2**: 不同语言 user-agent / accept-language 跑 BFS 会不会拿到不同 collab 列表？（YouTube 可能本地化推荐）—— 这个是优化方向 v2。
- **Q3**: 同一 seed 用不同 client（tv vs mweb vs ios）跑会不会有差异？—— 待 A/B。
- **Q4**: 把 BFS 与 video_owners 组合：从 huge seed 抓 video 列表 → 抓视频 description 的 @mention —— 链路长但可能补 missing。

---

## 9. 参考资料

### 代码源

- `discovery_compare.py:124-185` — 现有 `discover_via_bfs` 雏形（用过期的 channels params）
- `production_v2.py:218-254` — 现有 disc 策略 round-robin 结构（要扩成 3 策略）
- `extract_v4.py:180-227` — 验证 extract pipeline，BFS-found cid 会进这里
- `.venv/.../yt_dlp/extractor/youtube/_tab.py:1944,1978` — yt-dlp 自己注明 channels tab 已废
- `.venv/.../yt_dlp/extractor/youtube/_tab.py:565` — `gridChannelRenderer` map to `self._grid_entries`

### 实验脚本（本研究产出）

- `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_experiment.py` — v1 实验（用错的 country='Brazil' filter，已废弃）
- `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_experiment_v2.py` — **主实验**，3 surface × 4 cohort × 41 seed
- `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_probe.py` — surface response 结构 probe（看 tab list / shelf 名）
- `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_validate_new.py` — 验证 BFS-found 新 cid 的 BR 转化率

### 数据 dump（本研究产出）

- `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_experiment_v2_results.json` — 41 seed × 3 surface 完整结果
- `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_validate_new_results.json` — 38 新 cid 的 extract_v4 验证结果

### 外部参考

- yt-dlp GitHub issues #10804, #2117（关于 channel tab 变更，未深挖，与本研究结论 "channels tab removed" 一致）
- InnerTube API 文档（unofficial）: tab params 是 protobuf-encoded，详见 `params=` decoder
- 现有 `discovery_compare.py:159` 注释 `# The /channels tab uses browse with params=EghjaGFubmVscw==` 现需更新为反映 deprecated 状态

---

## 10. 迭代历史

### v1（2026-05-19，本次）

- ✅ 实测 6 个 PDF cited seed 的 tab list，确认 /channels tab 已 deprecated
- ✅ 实测 41 个真实 BR seed × 4 cohort × 3 surface，得出 cohort-wise yield 表
- ✅ 验证 38 个 BFS-found cid，确认 63.2% BR 转化率（vs query-based 10-15%）
- ✅ 设计 bfs_visited schema + production_v2 集成方案
- ✅ 输出 phase 1/2/3 执行计划与预期收益（25K–35K new eligible）

### v2（待跑，本研究下一步）

- [ ] 在 production_v2.py 实施 BFS worker (~70 行)，跑 24h 实测 yield curve
- [ ] phase 1 (huge ≥1M, 3.7K seeds) 跑完，对比预测/实际新增 eligible
- [ ] 评估是否进 phase 2 (large 100K-1M)
- [ ] depth-2 实验：从 phase 1 new cids 里挑 100 个再 BFS 一轮

### v3（potential）

- [ ] 多语言 BFS（en-US accept-language → 看是否 surface 不同 collab）
- [ ] 与 video_owners 组合（video description @mention 链路）
- [ ] sitemap.xml 扫 + recommended 视频频道作为辅助 BFS source
- [ ] Comments 挖矿（受 5% 转化率限制，最低优先级）

---

# 11. v2 调研扩展（2026-05-19 PM 第二轮）

> 本轮聚焦：调研 yt-dlp / Hacker News / scrapfly / dev.to / scrapecreators / dermasmid / tombulled 等社区最新讨论，找隐藏 InnerTube surface，构建下一步可执行测试方案。

## 11.1 新参考资料（实测 + 引用核实）

### 11.1.1 [`anvaka/allytrelated`](https://github.com/anvaka/allytrelated) — 关键先行项目（2015-2016）

历史最具规模的 YouTube 关联频道 BFS crawler，从 TotalBiscuit 起点 BFS **覆盖了 ~3M channels**。GitHub 10 stars（不流行但成功了）。

**关键设计（README + index.js 实读）**：
- 用 AWS Lambda 做 fetch（绕本机 IP 限流）
- `maxWorkerCount: 2, channelsPerWorker: 30` → 极低并发（60 channels in-flight max）
- 输出格式 `{id, title, related[], subscribers, relatedTitle}` —— 注意保留了 `relatedTitle`（shelf 名）
- README 原话：**"YouTube has couple `related` sections. By default this crawler will take only the first one (most of the time the first section is generated by users)."** —— 直接证实 BFS 主要 surface 是 owner-curated 部分
- **last commit 2016-10-08** —— 用的是 pre-2023 时代的 `/channels` tab（已 deprecated），如今只剩 home tab gridChannelRenderer 可用
- **对我们的启发**：
  1. 低并发 + 慢爬可以做到百万规模（说明 surface 本身能产出）
  2. 保留 shelfTitle 用于 QA（spam shelf vs 真 collab shelf）
  3. AWS Lambda 类的分布式 fetch 是已知方案（参考 §08 IPv6 VPS）

### 11.1.2 yt-dlp 内部 browse_id 常量梳理（源码 grep 实测）

```bash
$ grep -rh "FE[a-z_]*" yt_dlp/extractor/youtube/ -o | sort -u
FE
FEwhat_to_watch
```

**只有一个 FE* 常量被 yt-dlp 显式 reference**: `FEwhat_to_watch` = 首页推荐 (`/feed/recommended`)

`yt_dlp/extractor/youtube/_redirect.py:140` 定义了 `YoutubeRecommendedIE(YoutubeFeedsInfoExtractor)`，URL 是 `https://www.youtube.com/feed/recommended` 直接走 InnerTube。

实测 (`browseId=FEwhat_to_watch` + 新 visitor_data + tv client + gl=BR):
- HTTP 200 ✓
- response 63KB
- renderer 类型：`richGridRenderer, richSectionRenderer, feedTabbedHeaderRenderer, consentBumpV2Renderer` 等
- **videoRenderer count: 0** ❌
- **richItemRenderer count: 0** ❌
- **extracted channel IDs: 0** ❌

**结论**：guest session 的 /feed/recommended **不返回任何视频**——只返回页面 chrome（toolbar、tabs、consent bump、empty grid）。需要 watch history / cookies 才能拿到推荐。**对我们 anon 模式无用。**

### 11.1.3 其它 FE* browse_id 实测

| browseId | 期望 | HTTP 实测 |
|---|---|---|
| `FEwhat_to_watch` | 首页推荐 | 200（但空 grid） |
| `FEtrending` | 趋势 | **400** ❌ |
| `FEexplore` | 探索 | **400** ❌ |
| `FEtopics` | 话题 | **400** ❌ |
| `FEhashtag` + 字符串 params | 标签 | **400** ❌ |

**全军覆没**——这些 surface 要么已被 YouTube 移除 InnerTube 暴露（July 2025 trending 被废 [Dash Social 引用]），要么需要复杂的 protobuf-encoded params。

### 11.1.4 [YouTube Channels Tab Removed Nov 2023 — piunikaweb](https://piunikaweb.com/2023/11/28/youtube-about-channels-tabs-missing-heres-what-we-know/)

第三方独立确认：YouTube 在 **2023 年 11 月**移除了 `/channels` 和 `/about` tab。creator 的 secondary channel 现在只能通过 home tab 的 channel shelf 暴露。

> "The loss of the 'Channels' tab makes it more difficult to discover secondary channels from creators..."

**对应我们 §2.1 已经实测的结论**：所有 channels params 都被当 home tab 处理。

### 11.1.5 [scrapfly 2026 — How to Scrape YouTube](https://scrapfly.io/blog/posts/how-to-scrape-youtube) & [dev.to 2026](https://dev.to/agenthustler/how-to-scrape-youtube-in-2026-videos-channels-comments-and-metadata-27pn)

两篇 2026 商业 scraping 总结：
- 都**没提 channel-discovery 专门 endpoint**
- 推荐的都是 search-based + 已知 URL 直抓
- 完全没提 BFS 或 graph traversal
- 推荐 PO token + visitor data warming（→ 与我们 §07 cookie pool 调研一致）

**对我们的启发**：**业界没有更好的 channel discovery 方案**。BFS 仍然是单 IP scraper 能做的最好选择。商业服务（Apify、ScrapeCreators）也是用一样的 surface。

### 11.1.6 yt-dlp issue [#13879 — `/feed/recommended` --flat-playlist 缺 channel 信息](https://github.com/yt-dlp/yt-dlp/issues/13879)（2025-08+ 提出，仍 open）

reporter 用 `yt-dlp --flat-playlist https://www.youtube.com/feed/recommended` 想拿首页推荐视频列表，但 `%(channel)s` 都返回 "NA"。

**等于实证了 §11.1.2**：anon /feed/recommended 返回的是 page chrome，没真实视频，所以 channel field 都 NA。

### 11.1.7 [tombulled/innertube](https://github.com/tombulled/innertube) Python InnerTube client

通用 InnerTube wrapper，覆盖 YouTube + YouTube Music + Kids + Studio。**没有提供 channel-discovery 专用方法**——只提供原始 endpoint wrapper。

**对我们的启发**：如果未来要做更深 BFS（如 watchEndpoint 系列），可以参考它的 endpoint 集合，但目前不是必要。

### 11.1.8 [dermasmid/scrapetube](https://github.com/dermasmid/scrapetube)

Python YouTube scraper，主要做 channel video listing + search。**README 不涉及 channel-to-channel discovery**。

## 11.2 总结：什么 surface 真的能用

经过两轮调研，**单 IP 可用的 channel discovery surfaces 已经清楚**：

| Surface | InnerTube Endpoint | guest 可用 | 实测 yield/seed | 我们的状态 |
|---|---|---|---|---|
| **Home tab gridChannelRenderer** | `browse` + `browseId=UC...` | ✅ | 0.6–3.25 | **已验证** ⭐ |
| /channels tab | `browse` + `params=Egh...` | ❌ deprecated 2023-11 | 0 | 已排除 |
| /feed/recommended (FEwhat_to_watch) | `browse` + `browseId=FE...` | ❌ 返回空 | 0 | 已排除 |
| /feed/trending, /feed/explore, /feed/topics | `browse` + `browseId=FE...` | ❌ HTTP 400 | n/a | 已排除 |
| Hashtag pages | `browse` + protobuf params | 复杂 | unknown | 推迟 |
| Video watchEndpoint "up next" | `next` endpoint | ✅ | unknown | **待测** |
| Music browse | music.youtube.com endpoint | ✅ | unknown | **待测** |
| Search `sp=channel filter` | `search` + `EgIQAg==` | ✅ | 30/query | 已用 |
| About description @mentions | extract_v4 stage 2 | ✅ | <0.1 | 已排除 |
| Comments | `next` + comment continuation | ✅ | 5-10 / 100 | 推迟 |

## 11.3 下一步实验方案矩阵

按预期 ROI 排序，每个 scenario 都给**可执行假设 + 测试方法 + 成功标准**：

### 测试方案 A：watchEndpoint "Up Next" 挖矿 ⭐⭐⭐⭐

**核心假设**：
每个视频的 "up next / watch next" 推荐列表是**算法-curated**（不是 owner-curated），所以与 home tab gridChannelRenderer 互补。一个 BR seed 的高播放视频，其 watch-next 列表大概率推荐其它 BR 频道（语言+地理聚类）。

**为什么可能比 BFS gridChannel 强**：
- BFS gridChannel 只覆盖 owner 主动列的 ~3-6 个 channel
- watchEndpoint 一个视频出 ~20-30 个 up-next videos = ~15-25 个 unique channels
- 一个 seed 的 top 10 视频 → ~100-200 个 candidate channels（多倍 yield）

**测试方法**：
1. 从 channels 抽 10 个 huge BR seed（subs>=1M, BR）
2. 对每个 seed，先用 `browse browseId=UC... params=EgZ2aWRlb3M=` 拿 videos tab 取 top 10 video IDs
3. 对每个 videoId 调 `next` endpoint with `videoId` + `playbackContext`
4. 解析 response 的 `contents.twoColumnWatchNextResults.secondaryResults.results[*].compactVideoRenderer.shortBylineText.runs[0].navigationEndpoint.browseEndpoint.browseId`
5. 统计：unique channel count / seed; BR 转化率（spot check 20 个）
6. 对比 §3.1 home tab gridChannel 数据

**预期产出**: 50-100 unique channels per seed × BR 转化 40-60%（推测略低于 gridChannel 因为算法推荐多元化）。

**实验脚本目标位置**: `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_v2_watchnext_experiment.py`

**成功标准**：
- ✅ 每 seed 平均 ≥10 个不在 DB 的 new cid（vs gridChannel 3.25）
- ✅ BR 转化 ≥40%（vs gridChannel 63%）
- ✅ 单次 next-endpoint call ≤2.5s wall clock

如果通过 → 加为第四 discovery 策略 `discover_via_watchnext(seed_cid)`。

### 测试方案 B：YouTube Music BR 探索 ⭐⭐⭐

**核心假设**：
`music.youtube.com` 是 YouTube 内的独立产品（虽然底层 InnerTube），它的浏览结构（"Trending in Brazil"、"Top Hits Brasil"、"Sertanejo"、"Funk"、"MPB"）与主站不同。Music 的 channelRenderer 可能曝光主站搜索难触达的频道（特别是 artist channel auto-generated）。

**测试方法**：
1. 用 InnerTube client `WEB_REMIX`（yt-dlp 内置）调 music.youtube.com browse
2. 试 browse_id `FEmusic_home`, `FEmusic_charts`, `FEmusic_explore`
3. 解析 musicResponsiveListItemRenderer / musicCardShelfRenderer 中的 channelId
4. 用 gl=BR + hl=pt-BR locale lock
5. 跑 5 个不同 music browse_id × 10 page × 30 cid

**预期产出**：100-500 unique BR music channels，部分可能是 topic channel (UC*HOME 格式) 与正常频道不同。

**实验脚本目标位置**: `/Users/dapeng/Desktop/word/brz_ytdlp/bfs_v2_music_experiment.py`

**成功标准**：
- ✅ 至少 1 个 FEmusic_* browse_id 返回 200 + 含 channel
- ✅ 拿到 ≥100 个不在主 DB 的 cid
- ✅ 50%+ 是真 BR (gl=BR locale 应该自然过滤)

**风险**：很多 auto-gen topic channel (UC*HOME) subs 极低或全是 music video re-uploads，extract_v4 可能 short-circuit 全部。先 spot-check 10 个验证再大规模跑。

### 测试方案 C：BFS depth-2 衰减曲线 ⭐⭐

**核心假设**：
v1 §5.3 留的开放问题：depth-2 BFS（用 depth-1 找到的 30K 新 cid 当 seed 再 BFS）的真实 yield。

**测试方法**：
1. 等 v1 BFS 实施后，DB 里多出 ~30K depth-1 new cid
2. 从中抽 100 个（按 subs>=100K BR 过滤）当 depth-2 seed
3. 跑 BFS gridChannel + watchEndpoint（如果方案 A 已通过）
4. 统计：depth-2 新增的 cid 中**不在 depth-1 已发现**的有多少
5. 比较 depth-1 vs depth-2 yield/seed 衰减率

**成功标准**：
- ✅ depth-2 衰减率 ≤70%（即 depth-1 3.25 → depth-2 ≥1.0）
- ❌ 若 ≤20%，说明 BR 关联频道是闭合 cluster，depth-2 浪费 API

**结论指导**：决定 BFS 要不要做 ≥3 层。

### 测试方案 D：多 client / 多 locale BFS A/B ⭐

**核心假设**：
v1 §8.3 留的开放问题。YouTube 推荐算法对不同 device profile 有差异化，所以同一 seed 用 `tv` / `mweb` / `ios` / `android_vr` 跑 BFS 可能拿到不同的"Outros Canais" shelf。

**测试方法**：
1. 选 5 个 huge BR seed
2. 对每个 seed 用 5 个 client × 3 个 locale（pt-BR, en-US, es-419）= 15 个组合
3. 计算 75 次 call 之间的 cid 并集 vs 单 client 单 locale
4. 看 union/single 比值是否 ≥1.5（即多策略提升至少 50%）

**预期**：提升应该 ≤1.5x（gridChannelRenderer 是 owner-curated，对推荐算法不敏感）。如果 ≥1.5x，说明 locale 也影响 owner-curated shelf 展示（可能性较低但值得验证）。

**成本**：极低（75 个 call ≈ 1 分钟），但**收益预期较低**。优先级低。

### 测试方案 E：Subscribe-Now widget / 频道页面 sidebar  ⭐

**核心假设**：
yt-dlp 源码 search 中看到 `subscribeButton` 字段（discovery_compare 实测 channelRenderer 含 subscribeButton）。这意味着 InnerTube 知道某个 visitor 是否订阅某 channel——也许有一个 sidebar widget 推荐"你订阅这个就会喜欢的频道"（类似 Spotify 推荐）。

**测试方法**：
1. 调 channel home browse，detailed walk all renderers
2. 找 `subscribeChannelRendererProperty` / `subscriptionWidgetRenderer` / 类似 widget
3. 如果存在，提取其中 channelId

**预期**：可能不存在（YouTube 把推荐塞在算法里而不是 widget），但 cost 极低（看 response）。

**优先级**：低，但可顺便做（实验脚本里加 5 行 grep）。

### 测试方案 F：Sitemap / channel-list URLs 暴力扫 ⭐⭐

**核心假设**：
`https://www.youtube.com/sitemaps/sitemap.xml` 列出公开 channel URL 索引。该 sitemap 可能包含 BR-specific 子 sitemap。

**测试方法**：
1. `curl https://www.youtube.com/sitemaps/sitemap.xml` 看 root
2. 找 BR-related / pt-related sitemap entry
3. 下载这些 sitemap 抽 channel URL (`/channel/UC...` 或 `/@handle`)
4. 估算 yield + BR 比例

**风险**：sitemap 可能只有 video 没 channel；或全是 indexed 已知频道。

**优先级**：中（cost 极低，一次性 ~5 分钟），如果 sitemap 有 ≥1K BR 新 cid 就值得。

### 测试方案 G：Playlist collaborators 链路 ⭐

**核心假设**：
某些 BR 大频道有 "Curated by us" / "Tag along" 类协作 playlist，playlist owner 是其它频道。

**测试方法**：
1. 从 channel home 找 playlistRenderer，抽 playlistId
2. 调 playlist browse 拿 playlist info + videos
3. 抽 video owner channel = potential new cid

**预期**：yield 中等（playlist 在 BR creator 圈不主流），但**新 surface**。

**优先级**：中。等 v1 BFS + 方案 A 跑完再考虑。

## 11.4 测试方案优先级矩阵 + 时间线

| 方案 | 期望 yield | 工程量 | 风险 | 优先级 | 何时做 |
|---|---|---|---|---|---|
| **A: watchEndpoint up-next** | **+10-25 cid/seed** | 中 (~150 行) | 中（算法 noise） | **高** | **v1 BFS 跑完后立即** |
| **B: YouTube Music BR** | +100-500 全新 cid | 中 (~100 行) | 高（quality 差） | 高 | 与 A 并行 |
| C: depth-2 BFS | 衰减后 ~15K | 低（脚本改 1 行） | 低 | 中 | v1 数据出来后 |
| D: client/locale A/B | 边际改善 | 极低 | 低 | 低 | 周末顺便跑 |
| E: subscribe widget | 探索性 | 极低 | 低 | 低 | A 实验时顺便 |
| F: sitemap 扫 | 可能 +0 或 +5K | 极低 | 低 | 中 | 周末顺便跑 |
| G: playlist collab | 探索性 | 中 | 中 | 低 | 等 A/B 数据出来 |

## 11.5 v1 BFS 与 v2 扩展的关系

v1 已经验证: gridChannelRenderer 是**有产出**的主力 (63% BR, 3.25 new/huge seed)。  
v2 要回答的是: **能否在 v1 之外开辟 1-2 个新 surface 把单 seed 总 new cid 推到 10+?**

实施顺序建议：
1. **本周**: 把 v1 BFS 上线（参考 §6 实施方案，~70 行代码）—— 解锁 25-35K 新 eligible
2. **下周**: 跑测试方案 A (watchEndpoint up-next) —— 实测 yield
3. **下下周**: 测试方案 B (YouTube Music) + 方案 F (sitemap)
4. **第四周**: 整合所有有效 surface，跑 depth-2 BFS

## 11.6 风险预警：新发现

### 11.6.1 watchEndpoint 流量特征不同

调 `next` endpoint 跟调 `browse` endpoint 在 YouTube 看来是不同行为模式：
- `browse` = 用户翻 channel 主页（低频）
- `next` = 用户看视频时 fetch 推荐（极高频）

短时间大量 `next` call 可能触发**视频限流**，会影响我们 extract_v4 的两阶段 InnerTube call（也是 browse）。**测试方案 A 实施时需要分摊到不同 visitor_data / IP**。

### 11.6.2 Topic Channels（UC*HOME）的低质量

YouTube Music 的 artist 频道很多是 auto-generated（命名格式如 `UCxxx_x_HOME`），它们：
- 没有 owner（无 home tab 内容）
- subs 极少或没显示
- 视频全是 audio-track re-uploads

我们的 extract_v4 会 short-circuit 这些（subs<1000 + country=None + 没有 description），但**会浪费 API call**。测试方案 B 实施时应**先用 channelId 正则过滤** UC*HOME 格式（如果存在）。

### 11.6.3 anvaka/allytrelated 用的 AWS Lambda 启示

allytrelated 在 2015-2016 用了 AWS Lambda 做分布式 fetch（每个 Lambda 一个临时 IP）。这其实是当时的 IPv6 rotation 替代品。**等价于我们 §08 IPv6 VPS 方案**，但 AWS Lambda 现在已经被广泛限流（YouTube 知道 AWS IP 段）。教训：**云上 IP 池 ≠ 真住宅 IP**，YouTube 区别对待。

---

## 11.7 v2 调研产出文件清单

本轮调研未新增脚本（基本是源码 grep + 实测 + web fetch）。下一步实验方案要写的脚本（v3 阶段）：

| 文件 | 用途 |
|---|---|
| `bfs_v2_watchnext_experiment.py` | 测试方案 A 主脚本 |
| `bfs_v2_music_experiment.py` | 测试方案 B |
| `bfs_v2_depth2_experiment.py` | 测试方案 C |
| `bfs_v2_client_locale_ab.py` | 测试方案 D |
| `bfs_v2_widget_probe.py` | 测试方案 E（小脚本） |
| `bfs_v2_sitemap_scan.py` | 测试方案 F |
| `bfs_v2_playlist_collab.py` | 测试方案 G |

每个脚本设计为独立 standalone，dump 输出到 `bfs_v2_<name>_results.json`，主程序 import `extract_v3` 复用 helpers。

---

## 11.8 本轮新增参考资料

- [anvaka/allytrelated](https://github.com/anvaka/allytrelated) — pre-2023 BFS crawler，覆盖 ~3M channel（先行项目）
- [piunikaweb — YouTube Channels Tab Removed Nov 2023](https://piunikaweb.com/2023/11/28/youtube-about-channels-tabs-missing-heres-what-we-know/)
- [scrapfly — How to Scrape YouTube 2026](https://scrapfly.io/blog/posts/how-to-scrape-youtube)
- [dev.to — How to Scrape YouTube 2026](https://dev.to/agenthustler/how-to-scrape-youtube-in-2026-videos-channels-comments-and-metadata-27pn)
- [scrapecreators — Unofficial YouTube API](https://scrapecreators.com/blog/youtube-api)（商业 wrapper，无 BFS 角度）
- [tombulled/innertube](https://github.com/tombulled/innertube) — Python InnerTube client (通用 wrapper)
- [dermasmid/scrapetube](https://github.com/dermasmid/scrapetube)
- yt-dlp [#13879](https://github.com/yt-dlp/yt-dlp/issues/13879) — /feed/recommended missing channel
- yt-dlp [#10530](https://github.com/yt-dlp/yt-dlp/issues/10530) — Topic channels playlist parsing
- yt-dlp 源码 `_tab.py:939, 1485-1486, 1627-1628`
- yt-dlp 源码 `_redirect.py:140-160`（YoutubeRecommendedIE / YoutubeSubscriptionsIE）
- [YouTube Topic Insights — Google Gemini 工具 2026](https://ppc.land/youtube-topic-insights-googles-open-source-gemini-tool-that-finds-trends-for-you/)（用 Data API v3，对我们无关）

## 11.9 v2 迭代历史

### 2026-05-19 PM（本轮）

- ✅ 调研 anvaka/allytrelated（pre-2023 3M channel BFS）实读 index.js & README
- ✅ 源码 grep yt-dlp 所有 FE* browse_id 常量（只有 `FEwhat_to_watch`）
- ✅ 实测 4 个 InnerTube browse_id：`FEwhat_to_watch` 200 但空、`FEtrending`/`FEexplore`/`FEtopics` 全 400
- ✅ 第三方验证：YouTube 2023-11 移除 /channels + /about tab（piunikaweb 报道）
- ✅ 业界扫描：scrapfly/dev.to/scrapecreators 都没专门 channel discovery 方案
- ✅ 输出 **7 个测试方案矩阵**（方案 A-G），按 ROI 排序
- ✅ 标识新风险：watchEndpoint 流量特征、Topic Channels 低质量、AWS IP 被识别

### 2026-05-26（计划）

- [ ] 实施测试方案 A (`bfs_v2_watchnext_experiment.py`)，跑 10 个 huge seed
- [ ] 与 v1 gridChannel 数据对比，计算合并 yield
- [ ] 决定是否引入第四 discovery 策略

### 2026-06-02（计划）

- [ ] 实施测试方案 B (`bfs_v2_music_experiment.py`)
- [ ] 测试方案 F (sitemap 扫)
- [ ] 测试方案 D (client/locale A/B)

### 2026-06-09（计划）

- [ ] depth-2 BFS 实测（方案 C）
- [ ] 整合所有 v1+v2 surface 出最终 BFS module

---

# 12. v3 调研：全部 7 个测试方案实测落地（2026-05-19 晚）

> 在 v2 §11 提的 7 个测试方案（A-G），全部在本次会话内逐个实测。所有脚本 + 数据 dump 保存在 `long_term_research/v2_experiments/`。

## 12.1 测试方案 A — watchEndpoint Up-Next 挖矿 ⭐⭐⭐⭐⭐

**结论**：**EXCELLENT，强烈建议加为第二 BFS 策略**。

### Bug 修复：v1 用错的 renderer

v1 实验脚本（`test_A_watchnext.py`）按 v2 §11.3 的设计假设找 `compactVideoRenderer` —— **HTTP 200 但 0 cids**。

源码深探发现：**YouTube 在 2024 已废弃 `compactVideoRenderer`**，up-next sidebar 现在用：

```
contents.twoColumnWatchNextResults.secondaryResults.secondaryResults.results[*].lockupViewModel
```

owner channelId 在：
```
lockupViewModel.metadata.lockupMetadataViewModel.image.decoratedAvatarViewModel
.rendererContext.commandContext.onTap.innertubeCommand.browseEndpoint.browseId
```

修复后的脚本 `test_A_watchnext_v2.py` 用了"显式路径 + 兜底 extract_all_cids" 双策略，鲁棒。

### 实测数据

5 huge BR seed × 每 seed 取 top 5 video × 调 `/next` ：
- 总 API call: 30（5 videos browse + 25 next）
- 每个 video 的 sidebar `secondaryResults.results` 长度: **21-22 个 entry**（稳定）
- 每个 video 的 owner channel union: **10-19 个**（含 reelShelf 等噪音 renderer 里的 cid）
- 每个 video 的 new cid: **0-8 个**（与 DB 195K 已知去重后）

| Seed | new cids 总和 |
|---|---|
| UCMQGjL7ft6aNLKPp5xN-P3A | **29** ⭐ (最佳) |
| UCmF5w6pmvYfnMOqjQowgraA | 13 |
| UCpY-MyNXZx0sYhTH9qunY5A | 7 |
| UCMxxxx (UCfnkMKk7oyukXjkWNBuTflQ) | 3 |
| (5th seed) | 2 |
| **Total** | **54 new cids** |

### 关键指标

- **avg 10.8 new cid / huge seed**（v1 BFS gridChannel: 3.25）
- **boost: 3.32x**
- yield per API call: 1.80 new cid / call

### 集成建议（已写入 06 §6 plan，v3 更新）

加为第四 round-robin 策略 `discover_via_watchnext(seed_cid)`:
1. 调 home tab 拿 videos tab 的 top N video IDs（建议 N=3, 兼顾 yield 和 cost）
2. 对每个 video 调 `/next` endpoint（web_safari client）
3. 解析 secondaryResults 的 lockupViewModel → owner channelId

**API 成本**: 4 calls per seed (1 home + 3 next)，每 call ~700-900ms = ~3s/seed

### Trade-off：noise 比 gridChannel 高

up-next 是**算法-curated 而非 owner-curated**，意味着包含：
- 完全无关 channel（YouTube 推热门）
- 即使 BR 占比应该高（because we set hl=pt-BR）
- BR 转化率估 ~40-55%（vs gridChannel 63%），需在生产单独验证

### Risk 关注

watchEndpoint = 视频高频 fetch 行为。多个 IP 上同时 sustained 调可能触发 video-side throttle。**部署时建议 disc_workers 用 token bucket**，watchEndpoint call ≤ 2 req/s/IP。

实验脚本：`v2_experiments/test_A_watchnext_v2.py`  
数据 dump：`v2_experiments/test_A_watchnext_v2_results.json`

## 12.2 测试方案 B — YouTube Music BR 探索 ⭐⭐⭐

**结论**：**WORTH 单独 strategy**（产出 ~100 cid / 整套 endpoint 扫一遍）。

### Endpoint 试探结果

跑 10 个 `FEmusic_*` browse_id，过 yt-dlp 的 `web_music` client：

| Endpoint | HTTP | cids 新 | 时间 |
|---|---|---|---|
| `FEmusic_home` | 200 | **0** | 486ms（应该有但抽不出，结构未深探） |
| **`FEmusic_charts`** | **200** | **40 new** ✅ | 335ms |
| **`FEmusic_explore`** | **200** | **63 new** ✅ | 520ms |
| **`FEmusic_new_releases`** | **200** | **63 new** ✅ | 490ms |
| `FEmusic_moods_and_genres` | 200 | 0 | 294ms |
| `FEmusic_trending` | **400** | n/a | — |
| `FEmusic_listen_again` | **500** | n/a | — |
| `FEmusic_library_landing` | 200 | 0 | 281ms |
| `FEmusic_top_charts` | **400** | n/a | — |
| `FEmusic_hotlist` | **400** | n/a | — |

**3 个 endpoint 产出**：charts (40) + explore (63) + new_releases (63) = **98 unique new cids** (合并去重后)

### Music search test

用 `web_music` client + 自构 music search filter params 试 4 个 BR genre query → 全部 0 cids。说明 music search 需要更复杂的 protobuf params（暂未深挖）。

### 集成建议

Music discovery 是**周期性扫描**（不是 BFS）—— 一次扫 3 个 endpoint × 3 个 visitor_data 变体 = 9 个 call → 期望 ~200-300 new cids per scan window。
- 频率：每天 1-2 次（结果不会日变化很大）
- 成本：极低（10 个 call）
- 数据存到独立 surface

⚠️ **Topic Channels 噪音预警**：music charts 里大量是 `UC*HOME` 自动生成 artist 频道（subs 极少或全是音乐 re-upload）。validation 阶段需要：
- 检测 channelId 是否匹配 topic pattern
- 或允许它们进 DB 但 short-circuit by extract_v4

实验脚本：`v2_experiments/test_B_youtube_music.py`  
数据 dump：`v2_experiments/test_B_youtube_music_results.json`

## 12.3 测试方案 C v2 — depth-2 BFS 衰减 🟡

**结论**：**MARGINAL，huge cohort 不值，mid cohort 可考虑**。

用 v1 BFS 已验证的 38 个 new cid 中，筛 >=10K BR 的 15 个做 depth-2 seed，跑 BFS gridChannel：

- avg cids returned/seed: 1.73
- **avg new/seed: 0.93**
- 总 14 个 unique new cid

vs v1 baseline 衰减率：
- vs depth-1 huge (3.25/seed): **28.7% retention** —— 大幅衰减，不值
- vs depth-1 mid (1.60/seed): **58.3% retention** —— 中等衰减，部分值

### 解释

v1 depth-1 找的 38 个 cid 多数是中型频道（subs 10K-500K）。这些频道的 home tab `gridChannelRenderer` 含较少 "Outros Canais" shelf（小频道运营更随意），所以衰减明显。

### 建议

- **depth=1 already saturate huge cohort** ——多跑只是命中已 known cid
- **mid 可考虑 depth=2 但低优先级**
- 长期可能反复 depth=1 跑 + 新增 seed（如果 query 跑出新 seed）

实验脚本：`v2_experiments/test_C_depth2_v2.py`  
数据 dump：`v2_experiments/test_C_depth2_v2_results.json`

## 12.4 测试方案 D — client/locale A/B ❌

**结论**：**NOT WORTH，gridChannelRenderer 完全是 owner-curated**。

5 huge BR seed × 3 clients (tv, web_safari, android_vr) × 3 locales (pt-BR/en-US/es-419) = 45 calls

**所有 (client, locale) 组合返回完全相同的 cid 集合** —— union vs single 都一样。

```
boost ratio: 1.00x (45 个组合 vs 1 个 baseline)
```

这证实了 v1 §8.3 的开放问题：**owner-curated shelf 对 device profile 和 locale 完全不敏感**。

实验脚本：`v2_experiments/test_D_client_locale_ab.py`  
数据 dump：`v2_experiments/test_D_client_locale_ab_results.json`

## 12.5 测试方案 E — Subscribe widget probe ❌

**结论**：**NOT WORTH，没有隐藏的 recommendation widget**。

5 huge BR seed 各调 home browse，dump 所有 renderer 类型 + 找 `subscrib*` / `recommend*` / `widget*` / `similar*` 关键字段：

- 51 个 unique renderer 类型 across 5 seeds
- subscribe-related 字段: `["subscribeButton", "subscriberCountText"]` —— 都是已知 channel-info 字段，不是 recommendation widget
- widget-related: `["suggestedPosition"]` —— 是 ad 相关，不含 channel 链接

仅 1 个 seed 在 `subscribeButton` 内部含 3 个 cid（其它频道的 sub button 嵌入），都是已知 cid。

实验脚本：`v2_experiments/test_E_widget_probe.py`  
数据 dump：`v2_experiments/test_E_widget_probe_results.json`

## 12.6 测试方案 F — Sitemap brute scan ❌

**结论**：**YouTube sitemap 不含 channel URL**。

从 `https://www.youtube.com/sitemaps/sitemap.xml` 拿到 20 个 sub-sitemap，扫了前 5 个：
- 总 3MB+ 内容
- **channel URL 0 个**
- @handle URL 0 个
- video URL 0 个

YouTube 的 sitemap 索引的不是 watch/channel 页，而是 about / creators / kids 等**静态运营页**。对 discovery 完全无用。

实验脚本：`v2_experiments/test_F_sitemap.py`  
数据 dump：`v2_experiments/test_F_sitemap_results.json`

## 12.7 测试方案 G — Playlist collaborators ❌

**结论**：**NOT WORTH，BR 频道 home tab 没主流 playlist 暴露**。

5 huge BR seed × 取 home tab 找 playlistRenderer：
- 4/5 seed 的 playlistRenderer count = 0
- 1/5 seed 有 12 个 lockupViewModel（新版 playlist 容器），但 contentId 不是 PL* 格式（应该是 video 或 mix）
- 唯一 1 个 seed 拿到 10 个真正的 playlist ID，跑了 3 个：
  - 平均 ~5 video / playlist
  - **owners 全部 = seed 本人**（不是第三方合作）

结论：YouTube 主流 BR 频道**没有公开协作 playlist**，要么个人 playlist 全 self-uploaded，要么 collab 全私密。

实验脚本：`v2_experiments/test_G_playlist_collab.py`  
数据 dump：`v2_experiments/test_G_playlist_collab_results.json`

## 12.8 v3 综合优先级矩阵（更新）

| 方案 | v2 预测 | **v3 实测** | 工程量 | 决策 |
|---|---|---|---|---|
| **A: watchEndpoint** | +10-25/seed | **+10.8/seed @ 3.32x v1** ⭐ | 中 | **🏆 上线** |
| **B: YouTube Music** | +100-500/scan | **+98/scan** ⭐ | 中 | **✓ 上线（独立 scanner）** |
| C: depth-2 BFS | 50%/decay | 28-58% 衰减 | 极低 | 推迟（mid 才考虑）|
| D: client/locale | 边际 | **1.00x** | n/a | **🗑 放弃** |
| E: widget probe | 探索 | **0 widget** | n/a | **🗑 放弃** |
| F: sitemap | 0/5K | **0 channel** | n/a | **🗑 放弃** |
| G: playlist | 探索 | **0 new** | n/a | **🗑 放弃** |

**4/7 方案可砍**（D/E/F/G），节省后续约 1 周的探索时间。

## 12.9 综合 v1 + v2 BFS 落地路线图（重要：取代 v2 §11.4）

### 阶段 1：基础 BFS 上线（本周，v1 §6 plan）
- 代码改动：~70 行
- 单一 strategy：home tab `gridChannelRenderer`
- 阶段产出：跑完一遍 ~57K BR seeds → 预期 **+25-35K eligibles**

### 阶段 2：加 watchEndpoint 策略（v3 测试 A）
- 代码改动：~120 行（新策略函数 + production_v2 round-robin 扩展）
- 双 BFS 并行：gridChannel + watchnext
- **基于实测 10.8/seed 推算**：57K huge/large seed × ~10 new (打 5 折考虑 sustained throttle) = **+250K candidate**
- 即使 BR 转化降到 40%，eligible 增量 = **+100K** ⭐
- ⚠️ 注意 watchEndpoint 流量特征（需要 token bucket per IP）

### 阶段 3：Music scanner（v3 测试 B）
- 代码改动：~80 行（一个 standalone music_scanner.py，定时运行）
- 周期：每天 1-2 次扫 3 个 endpoint
- 阶段产出：每次 +98 new cid，月均 +3000 cid（多次扫去重后）

### 阶段 4：mid cohort depth-2 BFS（v3 测试 C）
- 仅对 v1 BFS depth-1 新发现的 mid (10K-100K subs) cohort 跑 depth-2
- 衰减约 58% → +几千 cid，**最后再做**

## 12.10 实施代码模板（直接可贴）

### discover_via_watchnext (新增)

```python
# discovery_compare.py
def discover_via_watchnext(seed_channel_id: str, n_videos: int = 3, limit: int = 50) -> Tuple[List[str], dict]:
    """Strategy D: fetch top N videos of seed, then call /next on each video,
    harvest owner channels from secondaryResults.lockupViewModel.

    Key API path:
    contents.twoColumnWatchNextResults.secondaryResults.secondaryResults.results[*]
    .lockupViewModel.metadata.lockupMetadataViewModel.image.decoratedAvatarViewModel
    .rendererContext.commandContext.onTap.innertubeCommand.browseEndpoint.browseId

    Average yield: ~10.8 new cid/huge_seed (3.32x vs grid_channel BFS).
    """
    ydl = _make_ydl_for_search()
    ie = ydl.get_info_extractor("YoutubeTab")
    t0 = time.time()
    # Step 1: get top N video ids from videos tab
    resp = ie._call_api(
        ep="browse", video_id=seed_channel_id,
        query={"browseId": seed_channel_id, "params": "EgZ2aWRlb3M%3D"},  # videos tab
        default_client="web_safari",
    )
    video_ids = []
    for renderer_key in ("videoRenderer", "gridVideoRenderer"):
        for r in _find_all(resp, renderer_key):
            if isinstance(r, dict):
                vid = r.get("videoId")
                if vid and vid not in video_ids:
                    video_ids.append(vid)
                    if len(video_ids) >= n_videos: break
        if len(video_ids) >= n_videos: break
    # Fallback: lockupViewModel for new layout
    if len(video_ids) < n_videos:
        for lvm in _find_all(resp, "lockupViewModel"):
            if isinstance(lvm, dict):
                content_id = lvm.get("contentId")
                if content_id and len(content_id) == 11 and content_id not in video_ids:
                    video_ids.append(content_id)
                    if len(video_ids) >= n_videos: break

    # Step 2: call /next on each video, harvest owner cids
    all_owners: Set[str] = set([seed_channel_id])
    for vid in video_ids:
        ydl2 = _make_ydl_for_search()
        try:
            ie2 = ydl2.get_info_extractor("YoutubeTab")
            n_resp = ie2._call_api(ep="next", video_id=vid,
                                  query={"videoId": vid},
                                  default_client="web_safari")
            try:
                sec = n_resp["contents"]["twoColumnWatchNextResults"]["secondaryResults"]["secondaryResults"]["results"]
            except (KeyError, TypeError):
                sec = []
            for entry in sec:
                lvm = entry.get("lockupViewModel") if isinstance(entry, dict) else None
                if not lvm: continue
                try:
                    cid = (lvm["metadata"]["lockupMetadataViewModel"]["image"]
                          ["decoratedAvatarViewModel"]["rendererContext"]
                          ["commandContext"]["onTap"]["innertubeCommand"]
                          ["browseEndpoint"]["browseId"])
                    if cid and cid.startswith("UC"):
                        all_owners.add(cid)
                except (KeyError, TypeError):
                    pass
        except Exception:
            continue  # one video failure shouldn't kill the seed
        finally:
            try: ydl2.close()
            except: pass

    all_owners.discard(seed_channel_id)
    ids = list(all_owners)[:limit]
    return ids, {"elapsed_s": time.time() - t0, "n_videos": len(video_ids)}
```

### production_v2.py 扩 DISC_STRATEGIES（v1 §6.3 基础上）

```python
DISC_STRATEGIES = [
    ("video_owners",     discover_via_video_owners),
    ("channel_filter",   discover_via_channel_filter),
    ("bfs_grid_channel", discover_via_bfs),         # v1 §6.2
    ("bfs_watchnext",    discover_via_watchnext),   # NEW (v3)
]
```

production_v2 的 disc workers 现在 round-robin 4 个策略，watchnext 那一支的 API call 是其它的 3-4 倍（1 home + 3 next）—— 把 watchnext 工人数减半（如 2 个 worker 跑 3 个其它 + 1 个跑 watchnext 比例 3:1）。

## 12.11 v3 迭代历史

### 2026-05-19 PM2（本次）

- ✅ 7 个 v2 §11 测试方案**全部跑完**
- ✅ Bug 修复：Test A 从 `compactVideoRenderer` 换成 `lockupViewModel`（YouTube 2024 layout 变化）
- ✅ Bug 修复：Test C 修正 v1 dump 读取 (`results.[*]`)
- ✅ 实测验证 4 个方案可砍（D/E/F/G）—— 节省路线图时间
- ✅ Test A v2 拿到 **10.8 new/seed (3.32x baseline)** —— v2 最佳新发现
- ✅ Test B 拿到 **98 cid per scan** —— 独立 surface
- ✅ Test C 确认 depth-2 衰减 28-58%，huge 不值 mid 可考虑
- ✅ 输出完整 production-ready 代码模板 (discover_via_watchnext)
- ✅ 所有脚本 + JSON dump 持久化在 `v2_experiments/`

### 2026-05-26（计划）

- [ ] **本周必做**：上线 v1 BFS gridChannel（v1 §6 plan，~70 行）
- [ ] 加 v3 watchnext 策略到 production_v2 (~120 行)
- [ ] 跑 24h 实测 sustained eligible rate 提升

### 2026-06-02（计划）

- [ ] 写 music_scanner.py（v3 测试 B 落地，独立 cron 脚本）
- [ ] 监控 watchnext 是否触发 YouTube 视频限流

### 2026-06-09（计划）

- [ ] 评估是否对 mid cohort 跑 depth-2 BFS
- [ ] 长期：整合 BFS + Music + query-based 出最终 master discovery module

## 12.12 v3 数据产出文件清单

```
long_term_research/v2_experiments/
├── _bfs_v2_helpers.py             (shared utilities)
├── test_A_watchnext.py            (v1, buggy with compactVideoRenderer)
├── test_A_watchnext_v2.py         (v2, FIXED with lockupViewModel) ⭐
├── test_A_watchnext_v2_results.json
├── test_B_youtube_music.py
├── test_B_youtube_music_results.json
├── test_C_depth2.py               (v1, buggy v1 dump read)
├── test_C_depth2_v2.py            (v2, FIXED) 
├── test_C_depth2_v2_results.json
├── test_D_client_locale_ab.py
├── test_D_client_locale_ab_results.json
├── test_E_widget_probe.py
├── test_E_widget_probe_results.json
├── test_F_sitemap.py
├── test_F_sitemap_results.json
├── test_G_playlist_collab.py
└── test_G_playlist_collab_results.json
```
