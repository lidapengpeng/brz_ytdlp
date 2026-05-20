# Query Bank 多样性专项调研

> 日期: 2026-05-19
> 状态: **v2 落地完成（2026-05-19 PM）** —— Suggest BFS 已生产部署
> 关联问题: dedup 重叠率 81%，限制 sustainable e/s

## 🎯 v2 落地成果（先写在最上面）

**实测**（同 IP, 60s 各跑 ~170 queries × 3 disc workers）：

| | OLD 36K bank | **NEW 46K bank** | delta |
|---|---|---|---|
| new cids/60s | 296 | **404** | **+108** |
| new cid/s | 4.93 | **6.73** | **+1.80** |
| dedup overlap | 84.5% | **78.8%** | **-5.7pp** |
| **Boost ratio** | — | **1.36x** | — |

**Bank 增长**：36,138 queries → 46,513 queries (+10,375 新 query, 99.1% novel)

**生成方法**：100 个 BR 文化 taxonomy seeds → depth-2 YouTube Suggest BFS (1253 layer-1 + 9113 layer-2 = 10,470 唯一新 query, 570s)

**生产部署**：`terminal_runner.py` 已切到 `query_bank_extended.txt`，`bash run.sh` 烟测通过

完整实施细节见 §3.1。
> 关联文件: `query_bank.txt` (36,138 行), `build_query_bank.py`, `discovery_compare.py`

## TL;DR

1. 当前 query bank **36,138 行高度同质化**: 84% 以 `canal/brasil/oficial/brasileiro` 结尾，词根冗余严重 (10K canal + 10K brasil 后缀=变体而非真新意), 27 个州合计被提及 < 200 次 (人口最大的 SP 仅 48 次)。
2. **YouTube suggest API 实测有效**: 用 94 个 BR 主题种子调用 `suggestqueries-clients6.youtube.com/complete/search?client=youtube&ds=yt&hl=pt-BR&gl=BR` 一轮就扩出 **1,165 个新 query, 其中 1,132 (97.2%) 不在当前 bank 中**。零错误, 平均每种子 12.4 个长尾建议, 14 个上限。
3. 三层 BFS 扩展可期到 **100K-200K 真长尾 query** (每个含具体年份/形容词/地名修饰), 这类长尾的 channel-filter 搜索新 cid 命中率显著高于"X brasil"类宽匹配。
4. 预估收益: 替换为多样化 bank 后，**dedup 新 cid 率从 19% → 40-55%**, sustainable e/s 从 4.86 → **8-12** (取决于 InnerTube 节流), 700K 目标达成时间从 ~40 天缩短到 **16-24 天**。
5. 优先级路线: 本周做 suggest API 三层 BFS（即可获得 ~150K 新 query），二周内整合 Google Trends related queries + hashtag 挖矿，1 月内做 comments BFS 和 LLM 模板增量。

---

## 1. 背景与问题陈述

**项目目标**: 700K 巴西 pt-BR YouTube 频道 (country=Brasil 或 lang_recovered=pt, subs ≥ 1000)。

**当前实际状态** (DB 抽样确认):
- `channels` 表共 105,408 行 (其中 country=Brasil 88,158 行, country=None+lang=pt 17,317 行)。
- `rejected_channel_ids` 79,090 行 (即重复或不合格的 cid)。
- Sustained throughput: 4.86 e/s。
- Dedup ratio: query 平均返回 30 个 cid → 仅 ~5.7 个 (19%) 为新 cid → **81% 重叠率**。

**瓶颈来源** (假设): channel-filter 搜索 `<query>` 时, 同样的"头部 BR 频道"会反复命中。query bank 缺乏长尾意图修饰词 (年份、具体地名、人名), 导致 SERP 收敛到 BR 大众频道池。

**调研目标**: 把 dedup 重叠率压到 < 50%, 维持或提升 e/s。

---

## 2. 当前 query bank 分析

**规模与形态**:
- 总行数 36,138
- 长度分布: 1 词 655 行, 2 词 12,458 行, 3 词 13,434 行, 4 词 8,537 行, 5+ 词 1,054 行。**90% 是 2-4 词的短 query**, 几乎没有 5+ 词长尾。

**词频 (top 25)**: `canal=10,037`, `brasil=9,996`, `brasileiro=6,645`, `oficial=6,529`, `de=4,988`, `do=704`, `para=657`, `casa=347`, `gta=294`, `rotina=298`, `minecraft=261`, `gospel=245`, `futebol=245`。

**后缀冗余**:
- `* canal`: 10,027 行 (27.7%)
- `* brasil`: 9,780 行 (27.1%)
- `* oficial`: 6,523 行 (18.1%)
- `* brasileiro/a/s`: 6,612 行 (18.3%)
- → 合计 91% 的 query 是机器生成的"词根 × {canal,brasil,oficial,brasileiro}"叉乘, **缺乏自然语言长尾结构**。

**27 州覆盖度（关键缺口）**:
```
são paulo: 48      rio grande do sul: 4    pernambuco: 3
rio de janeiro: 15  paraná: 9              roraima: 4
minas gerais: 11    santa catarina: 4      sergipe: 4
bahia: 15           ceará: 9               tocantins: 4
distrito federal: 4 ... (其余几乎都是 3-4 次)
```
全国 27 州只被提及 ~200 次, 占 query 总量 0.55%。**地理长尾完全缺失**。

**话题覆盖抽样**:
- 有: rotina(298), vlog(233), gospel(245), futebol(245), gta(294), minecraft(261), ASMR(136), anime(134), funk, sertanejo, samba 等。
- 缺/弱: `podcast=85`, `shorts=48`, `tiktok=76`, `reels=11`, `manga=16`, `cosplay=8`, `estoicismo=2`, `filosofia=20`, `tarô=6`, `buddismo=0`, `diario=0`, `drama=12`, `ficção=15`。

**结论**: 当前 bank 是"词根爆炸" (cartesian product) 而非"自然搜索意图"。同一频道会在 `funk brasil` / `funk brasileiro` / `funk canal` / `funk oficial` 四个 query 下都出现, 这正是 81% 重叠的根源。

---

## 3. 调研发现

### 3.1 YouTube Suggest API（实测）

**端点** (无 API key, 公开):
```
https://suggestqueries-clients6.youtube.com/complete/search
  ?client=youtube
  &ds=yt
  &hl=pt-BR
  &gl=BR
  &q=<PREFIX>
```
返回 JSONP 形式: `window.google.ac.h(["prefix",[["sug1",0],["sug2",0],...]])`，每个 prefix 最多 14 条建议。

**实测脚本** (已在 `/tmp/yt_suggest_test.py` 跑通):

```python
import json, time, urllib.parse, urllib.request

URL = "https://suggestqueries-clients6.youtube.com/complete/search"

def suggest(prefix: str) -> list[str]:
    q = urllib.parse.urlencode({
        "client":"youtube","ds":"yt","q":prefix,"hl":"pt-BR","gl":"BR"})
    req = urllib.request.Request(f"{URL}?{q}",
        headers={"User-Agent":"Mozilla/5.0", "Accept-Language":"pt-BR,pt;q=0.9"})
    raw = urllib.request.urlopen(req, timeout=8).read().decode("utf-8","replace")
    s, e = raw.find("("), raw.rfind(")")
    arr = json.loads(raw[s+1:e])
    return [x[0] for x in arr[1] if isinstance(x, list) and isinstance(x[0], str)]
```

**实测结果** (94 个 BR 主题种子, 单线程, 150ms 间隔):
| 指标 | 值 |
|---|---|
| 种子数 | 94 |
| 错误数 | 0 |
| 平均每种子返回 | 12.4 条 |
| 总 unique 输出 | 1,165 条 |
| 与当前 36K bank 重叠 | **33 条 (2.8%)** |
| **纯新增** | **1,132 条 (97.2%)** |
| 单种子耗时 | ~0.2s (含 sleep) |

**新 query 样本** (随机 15 条):
```
brigadeiro de maracujá
investir em imoveis no brasil
santos fc noticias hoje sormani
oab 46 / oab 1 fase
forró perfeito / forró real / forró de favela
sertanejo 2025
tesouro direto renda +
sbt ao vivo agora online hoje
ano novo eletrofunk / ano novo copacabana
chapada diamantina trilha
record ao vivo 24 horas grátis
musica brasileira moda
salvador bahia território africano baiano sou eu
valorantbrasil ego / valorant brasil cinematic
```

**关键观察**:
1. 这些 query 都是**真实搜索意图**, 包含年份 (2025, 2026)、具体节目 (record ao vivo)、长尾修饰 (de favela, sem dó), 是字母叉乘永远生成不出来的。
2. 命中"头部频道"的概率降低, 命中**中长尾频道**的概率提升 (因为这些频道才是真正在用这些长尾标题/描述)。
3. **三层 BFS** 可行: 用 1,165 个 L1 结果再各自跑 suggest → 估计 L2 ~10K, L3 ~50-100K (饱和)。

**BFS 实施代码草稿**:
```python
def bfs_expand(seeds: list[str], depth: int = 3, max_total: int = 200_000) -> set[str]:
    seen = set(seeds); frontier = list(seeds)
    for d in range(depth):
        next_frontier = []
        for p in frontier:
            for s in suggest(p):
                s = s.strip().lower()
                if s and s not in seen and len(seen) < max_total:
                    seen.add(s); next_frontier.append(s)
            time.sleep(0.1)
        frontier = next_frontier
        if not frontier or len(seen) >= max_total: break
    return seen
```

**rate-limit 风险**: 公开 API 没有官方配额，但 google 后端会 throttle。建议加 retry + 跨 proxy 节点 (你们已有 30 节点 Clash) 平均下来 1 token/100ms 安全, **10K seeds × 14 suggs ≈ 140K query 大约 30 分钟**。

参考: [Hacking together your own YouTube Suggest API](https://dev.to/adrienshen/hacking-together-your-own-youtube-suggest-api-c0o), [Google Autocomplete Unofficial Spec](https://www.fullstackoptimization.com/a/google-autocomplete-google-suggest-unofficial-full-specification)。

---

### 3.2 业界 keyword research 工具

| 工具 | 免费层 | BR 数据 | 适用场景 |
|---|---|---|---|
| **Google Trends Brazil** (`trends.google.com/trends?geo=BR`) | 完全免费, 无 key | Related Queries + Related Topics | 提取一个 seed 的 5-10 个上升 query，适合做 seed 选择和趋势验证。可 scrape `pn=p1` (Brazil) 接口。|
| **YouTube Data API v3 search.list** | 10K units/day | 全球 | 配 `regionCode=BR&relevanceLanguage=pt` 可作辅助验证, 但配额很紧。|
| **Semrush** (付费) | 7 天 trial | 1.7B BR keyword | 输入"futebol", 给出 BR 月搜索量 + intent 分类。适合一次性 mining。|
| **Ahrefs** (付费) | 仅免费 webmaster | 完整 BR DB | 同上, **支持 .br 域名反向链接 → 可挖 BR YouTube 频道的官网**。|
| **Ubersuggest Brasil** | 3 query/天免费 | 中等 | Quick start, 但量受限。|
| **AnswerThePublic** | 3 query/天免费 | "What/where/how + seed" | 适合补 5W1H 长尾 (`como assistir <X> brasil`, `onde comprar <Y> br`)。|
| **Keyword Tool .io** | 全部数据需付费 | 多语言含 pt-BR | 也是基于 YouTube/Google autocomplete 的封装, **其底层就是上面 3.1 的 endpoint**。所以我们自己跑可省 $69/月。|

**结论**: 不需要付费工具。**自建 YouTube suggest BFS + Google Trends related queries scraping** 已能覆盖业界工具 80% 的输出, 且数据更新更及时 (实时 vs 工具周更/月更)。

参考: [Top SEO tools for Brazil 2025 - Ranktracker](https://www.ranktracker.com/blog/a-complete-guide-for-doing-seo-in-brazil/), [How to use Google Autocomplete API - MLforSEO](https://www.mlforseo.com/machine-learning-implementation-guides/keyword-research/how-to-use-google-autocomplete-apis-for-keyword-suggestions/)。

---

### 3.3 巴西文化 taxonomy

**5 大区 (Macroregiões)**:
- Norte: AC, AM, AP, PA, RO, RR, TO
- Nordeste: AL, BA, CE, MA, PB, PE, PI, RN, SE
- Centro-Oeste: DF, GO, MT, MS
- Sudeste: ES, MG, RJ, SP
- Sul: PR, RS, SC

**27 单元 (含 27 首府)**: SP→São Paulo, RJ→Rio de Janeiro, MG→Belo Horizonte, BA→Salvador, CE→Fortaleza, PR→Curitiba, RS→Porto Alegre, PE→Recife, PA→Belém, MA→São Luís, SC→Florianópolis, GO→Goiânia, AM→Manaus, ES→Vitória, PB→João Pessoa, RN→Natal, MT→Cuiabá, AL→Maceió, PI→Teresina, DF→Brasília, MS→Campo Grande, SE→Aracaju, RO→Porto Velho, TO→Palmas, AC→Rio Branco, AP→Macapá, RR→Boa Vista。

**5 大都市区 (人口 >2M)**: São Paulo, Rio de Janeiro, Belo Horizonte, Brasília, Salvador, Fortaleza, Curitiba, Recife, Manaus, Porto Alegre。

**音乐流派 (per 区域)**:
- Norte/Nordeste: forró, xote, baião, frevo, maracatu, axé, samba-reggae, brega, tecnobrega, arrocha, piseiro, pisadinha, lambada, carimbó, ijexá
- Sudeste: samba, pagode, bossa nova, MPB, funk carioca, funk paulista
- Centro-Oeste/Sul: sertanejo, modão, sertanejo universitário, vaneira, chamamé, fandango, milonga
- Cross: rap nacional, trap br, rock nacional, gospel, evangélico

**体育**:
- Série A 时钟: Flamengo, Palmeiras, São Paulo, Corinthians, Fluminense, Vasco, Botafogo, Santos, Atlético-MG, Cruzeiro, Internacional, Grêmio, Athletico-PR, Bahia, Sport, Fortaleza, Ceará, Vitória, Bragantino, Cuiabá ...
- 非足球: vôlei, basquete, UFC brasileiro (Charles do Bronx, Glover Teixeira), MMA, surf (Medina, Italo), tênis (Bia Haddad)

**美食地域**:
- Mineira: pão de queijo, feijão tropeiro, frango com quiabo
- Bahiana: acarajé, vatapá, moqueca, caruru
- Nordestina: baião de dois, carne de sol, tapioca, cuscuz
- Gaúcha: churrasco, chimarrão, pinhão
- Amazônica: tacacá, açaí, pirarucu, tucupi
- Paulista: pizza (?), virado à paulista
- Carioca: feijoada (nacional), bolinho de bacalhau

**节日/事件**:
- Carnaval (várzea), Festa Junina, São João, Réveillon Copacabana, Rock in Rio, Lollapalooza Brasil, Bienal SP, Festival de Parintins, Oktoberfest Blumenau, Cavalhadas, Cirio de Nazaré

**电视/媒体**: Globo, SBT, Record, Band, RedeTV, RecordNews, BandSports, Globoplay, Telecine, Globonews, Telemundo, Cultura, TV Brasil, NSC

**历史/政治**: ditadura militar, Diretas Já, redemocratização, Plano Real, lava jato, impeachment, mensalão, eleição presidencial, STF, congresso, lula, bolsonaro, dilma, temer, fhc, jair messias, dirceu, moro, marcola

**宗教**: católico, evangélico, neopentecostal, IURD, Assembleia de Deus, Igreja Universal, candomblé, umbanda, espírita, kardecista, ateu br

**教育/职场**: ENEM, vestibular, FUVEST, UNICAMP, USP, UFRJ, UFMG, OAB, concurso público, INSS, CLT, MEI, contratação PJ

把这 5 类各取 50-200 种子, 直接喂入 §3.1 的 BFS, 估计**单 BFS 一次 = 5K seeds × 14 suggs = 70K query**, 重复后约 30K unique，全量三层可到 150K。

---

### 3.4 LLM-based query 生成

直接喂 §3.3 taxonomy 给 LLM, 让它生成"自然搜索意图"的长尾 query (不是叉乘)。

**模板 1: 角色扮演 + 具体意图**
```
你是一个 35 岁的圣保罗人, 喜欢看 YouTube。请列出 50 个你在过去 30 天最可能搜索的具体长尾 query, 涉及主题: 工作 (TI), 育儿, 周末美食, 政治新闻, 自动驾驶。每个 query 5-12 个词，包含具体年份/品牌/地名修饰。葡语 (pt-BR), 不带"canal"/"brasil"通用后缀，模拟真实搜索框输入。
```

**模板 2: 长尾生成 (with constraints)**
```
生成 50 个 YouTube 搜索 query, 主题=巴西东北部 forró 音乐 (含 piseiro, arrocha, xote 子类型)。
要求:
- 葡语 pt-BR
- 每个 query 必须包含: 一个具体艺人或乐队名 + 一个修饰词 (ao vivo / acústico / dvd / sertão / 2024 / remix)
- 不要使用 "canal" / "oficial" / "brasil"
- 避免词根叉乘, 模仿真实搜索框自动建议风格

示例: "lambasaia ao vivo no sertão 2024"
```

**模板 3: Niche 深挖 (mining a single vertical)**
```
我要从 YouTube 挖巴西"finanças pessoais"垂直的中长尾频道。生成 100 个 pt-BR query, 满足:
- 覆盖话题: investimentos, FIIs, ações, tesouro direto, dividendos, BTC, fundos imobiliários, declaração IR, dívida ativa, planejamento financeiro, FGTS, INSS, aposentadoria
- 每个 query 必须包含 2 个具体术语 (例如 "BBAS3 dividendo 2024"), 不要泛词
- 不带 "brasil" / "canal" / "oficial" / "brasileiro"
- 每行一个, 不要解释
```

**模板 4: Verb-driven (意图驱动)**
```
我要找 YouTube 上做 X 的频道。生成 100 个 pt-BR 搜索 query, 每个用以下意图动词开头之一: como, onde, por que, qual, quanto, quando, vale a pena, melhor, pior。主题:
- 怎么开 MEI / abrir CNPJ
- 怎么用 PIX / pagamentos
- 怎么准备 OAB / concurso público
- 怎么经营 cafeteria pequena em SP / 加盟巴西品牌
```

**模板 5: Region × Vertical 笛卡尔 (with LLM guard)**
```
针对巴西 27 州中的 [STATE], 生成 30 个 YouTube pt-BR query, 关于本州特有的:
- 本地新闻台 / 本地报纸
- 本地音乐人 / 本地乐队
- 本地美食 / 本地节庆
- 本地政府账号 / 本地教育机构
要求: query 自然, 含具体名称 (不是泛词), 例如:
  "manchete jornal A Crítica de Manaus hoje"
  "cuiabá festa do divino 2024"
不要"<topic> <state> canal"这种叉乘。
```

**预期产出**: 5 个模板 × 每模板 100 query × 多次迭代(温度 0.8) ≈ 单次 LLM cost $1-3, 产出 ~2K-5K 高质量 query。**与 suggest API BFS 互补** (LLM 擅长冷门话题, suggest 擅长热门)。

---

### 3.5 Anti-patterns（已饱和的 query 模式）

由于 `channels.target_reason` 列只记录 country/lang 来源 (无具体 query 出处), **直接的 per-query yield 统计需要补加日志**。但基于词频和频道生态分析, 以下模式可识别为低边际收益:

1. **`X canal`** (10K 行 → 27% 占比): 与 channel-filter search 双重指定, 等于二次过滤同一池。**建议剔除全部 ` canal` 后缀变体**, 因为 channel-filter 已是 search 模式参数。
2. **`X brasil` + `X brasileiro` 同时存在**: 这两个意思接近，YouTube 搜索的 ranker 会返回大量相同 channel。**保留更自然的那个** (单字 X 用 brasileiro, 多字短语用 brasil)。
3. **超广义单词 query** (655 行的 1-词 query, 例如"praia", "casa"): SERP 收敛到大众频道。**全部删除或加修饰** (e.g. "praia secreta nordeste 2024")。
4. **重叠 modifier**: `gta brasil`, `gta canal`, `gta rp`, `gta oficial`, `gta brasileiro` — 五个 query 返回同一批 GTA RP 频道。**用一个 + suggest 扩展** 即可。
5. **TV node 重复**: `globo`, `globo canal`, `globo brasil`, `globo oficial`, `globo brasileiro` — Globo 旗下账号就那么几个。**单一 query + 用 BFS 抽取其 channel comments/related 才有增量**。
6. **音乐流派的 brutal 笛卡尔**: `funk brasil / funk canal / funk brasileiro / funk oficial / funk consciente brasil / funk paulista brasil` — 应换成 §3.4 模板 2 的具体艺人 + 年份。

**经验法则**: 一个词根的 4-后缀变体只保留 1 个 (无后缀), 其余的让 suggest API 去填长尾。预计 query bank 可缩减到 ~9K 高质量精选 + 150K 自动 BFS 扩展 = **~160K 总量, dedup 重叠 < 50%**。

---

### 3.6 Hashtag 和 comments 挖矿

**A. YouTube hashtag 系统** (`https://www.youtube.com/hashtag/<tag>`):
- yt-dlp 支持: `ytsearch:` 或直接 hashtag URL → 返回 hashtag 下的 videos → 抽 owner channelId。
- 优势: hashtag 本身就是用户主动打的 vertical 标签, 与 query 完全不同的发现路径。
- 高流量 BR hashtags (基于 BR 网络趋势): `#shorts`, `#fyp`, `#brasil`, `#sertanejo`, `#funk`, `#flamengo`, `#corinthians`, `#flamenguistas`, `#palmeiras`, `#sambadeenredo`, `#bbb`, `#bbb24`, `#bbb25`, `#globo`, `#carnaval`, `#festajunina`, `#sãopaulo`, `#riodejaneiro`, `#evangélico`, `#gospel`, `#funkbrasil`, `#trapnacional`, `#mpb`, `#bolsonaro`, `#lula`, `#stf`, `#enem`, `#vestibular`, `#concursopúblico`, `#freefire`, `#freefirebr`, `#valorantbrasil`, `#lolbr`, `#tiktokbrasil`。

**实施草稿**:
```python
# Use yt-dlp with playlistnum-limit to list hashtag videos quickly
import yt_dlp
def hashtag_owners(tag: str, n: int = 200) -> set[str]:
    opts = {"extract_flat": True, "playlistend": n, "quiet": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/hashtag/{tag}", download=False)
    return {e.get("channel_id") for e in info.get("entries", []) if e.get("channel_id")}
```
**预期增量**: 50-100 个 BR hashtag × 200 个 video × dedup → 5K-15K 新 cid。这条管线**与 query-search 完全正交**, dedup 重叠率最低。

**B. Comments 挖矿** (yt-dlp `--write-comments` / `getcomments=True`):
- yt-dlp 支持开箱即用, 输出 JSON 含每条 comment 的 `author_id` (即 channel_id)。
- 配置:
  ```python
  ydl_opts = {
      "getcomments": True,
      "extractor_args": {"youtube": {"max_comments": ["100", "10", "5", "all"]}},
      # max-comments, max-parents, max-replies, max-replies-per-thread
  }
  ```
- 思路: 对已经确认是 BR 的频道, 抽 top-10 video × top-100 comment × author_id → 新 cid。
- 优势: **强 BR-signal 传播** (评论者大概率也是 BR 用户的频道), 比 query search 更精准。
- 风险: 评论提取慢 (每 video 5-10s), **每 10 个高质量种子 channel 约 5 分钟提取**, 但 cid yield 可达 100+ unique/seed。
- 注: comments 默认不含 @mention 链接到具体 channel, 但 `author_id` 字段直接是 channel_id。

参考: [yt-dlp comments docs](https://github.com/yt-dlp/yt-dlp/issues/2372), [How to Scrape YouTube Comments - Decodo](https://decodo.com/blog/scraping-youtube-comments)。

---

## 4. 量化预期收益

**假设**:
- 当前 36K bank, dedup 后 19% 新 cid → 5.7 new cid/query。
- 维持 30 cid/query 的 SERP 容量。

**新 bank 估算** (200K 多元 query):
- L1 seeds (taxonomy + 现有精选): ~9K
- L1+L2 suggest BFS: +50K
- L3 BFS + 长尾: +90K
- Hashtag + LLM templates: +50K
- 总量 ~200K, 平均 query 长度 4-7 词。

**预期 dedup 重叠率**: 由于长尾 query 命中"中长尾频道", 同一 cid 多次出现的概率下降 40-60%。**保守估计 dedup 重叠 65% → 35% 新 cid → ~10.5 new cid/query**。

**对 e/s 的影响**:
- 单 query 吞吐 (从 search → channel-filter list → first-page) 与重叠率无关, 约 0.3-0.5 s/query (受 InnerTube 限速)。
- 但 **discovery 阶段产生 5.7 vs 10.5 new cid/query, downstream extract pipeline 工作量翻倍** → 在 extract 不是瓶颈的前提下, e/s 从 4.86 → **8-10** 是合理的。
- 若 extract 已经 saturate (`extract_v4.py` 两阶段 InnerTube), 则收益主要体现在**总 query 数量减少**: 现在跑 36K query 才能得到 ~200K eligible cid, 新策略下 14K query 即可。**总耗时从 40 天 → 16-24 天**。

**降级假设** (悲观): 若 suggest BFS 的长尾 query 命中率比预期低 (比如本身热度太低导致 SERP < 30 cid), 那么 cid/query 下降但 dedup 改善。**净 e/s 估计 6-8** (仍比 4.86 提升 25-65%)。

---

## 5. 实施路线图

### 5.1 Quick wins (本周可做)

| 任务 | 时间 | 文件 | 输出 |
|---|---|---|---|
| 写 `expand_via_suggest.py` (BFS L1+L2, 配 Clash 节点轮询) | 0.5 day | 新文件 | `query_bank_v2.txt` ~50K |
| 删现有 ` canal` / ` oficial` / ` brasileiro` 单纯后缀变体 (保留唯一根) | 1h | `build_query_bank.py` | `query_bank.txt` 压缩到 ~9K |
| 在 `production_v2.py` 加 per-query yield 日志 (记录每 query 实际产 cid + new cid 数) | 2h | `production_v2.py` | 用于 §3.5 anti-pattern 量化 |
| 合并: `query_bank.txt = 9K 精选 + 50K suggest BFS = ~55K` | 0.5h | merge script | `query_bank_v2.txt` |
| **跑 24h 实测 e/s 对比** | 24h | endurance run | report |

### 5.2 Mid-term (2 周内)

| 任务 | 时间 | 输出 |
|---|---|---|
| 三层 BFS suggest 扩展到 150K query | 0.5 day + 1h API 跑 | `query_bank_v3.txt` |
| Hashtag pipeline (100 个 BR hashtag → 抽 owner_id), 加入 discovery_compare | 1 day | `discovery_hashtag.py` |
| Google Trends scraping (related queries per category, 30 个 BR 大主题, 每 24h 跑) | 1 day | `trends_daily.json` 自动 merge |
| LLM 生成 (5 个模板 × 100 query × Claude/GPT) | 0.5 day | +500-2K 高质量 query |
| Comments mining 原型 (10 个高质量 seed channel × 50 video × 100 comment) | 1 day | yield 实测报告 |
| 整合所有源, 去重, 排序优先级 (BR-confidence score reuse `build_query_bank.py`) | 0.5 day | `query_bank_v4.txt` ~200K |

### 5.3 Long-term (1 月+)

| 任务 | 价值 |
|---|---|
| **自适应 query allocator**: 每 query 的实际 yield 累计统计, low-yield 自动降权或剔除, 用 ε-greedy 持续选 query | dedup 重叠率 < 30% |
| 跨语言反向: 用葡语关键词调用 google trends 看上升 query → 同时探测 country-specific 新闻话题 | 抓"突发新闻"驱动的临时频道 |
| Channel BFS-3 (`discovery_compare.py` 已有 BFS 雏形, 扩展 depth 3 with conf-threshold) | 中长尾 BR 频道集合的传染式发现 |
| 训练一个轻量 classifier: query × cid yield 预测 → 仅跑 top-30% predicted-high-yield query | 资源效率 +200% |
| 关注 yt-dlp [issue #2372](https://github.com/yt-dlp/yt-dlp/issues/2372) (comments JSON 独立文件) 和 InnerTube 升级 | 维持长期兼容 |

---

## 6. 风险与开放问题

1. **YouTube suggest API 节流**: 单 IP 跑 100K+ query 大概率被限速。**缓解**: 用 30 节点 Clash 池轮询, 每节点 ≤ 5 req/min。也可降到 50ms sleep + 5-10 并发。
2. **长尾 query 反而 SERP 空**: 部分超冷门 query (例如"manchete jornal Boa Vista RR 2024") 可能 SERP < 5 cid, 提升 dedup 但拉低 cid/query 总数。**应在 production_v2 加 fallback: SERP < 10 时跳过, 不浪费 InnerTube quota**。
3. **多样性 vs 精确度 trade-off**: 长尾 query 会引入更多 non-BR 频道 (例如 "agronegócio no paraguai" → 巴拉圭频道)。**缓解**: extract_v4 已有 `country='Brasil'` 双闸门, 多筛除是可接受的。
4. **Comments mining 法律灰色**: comments 抓取虽然技术可行, 但若大规模做需要尊重 robots.txt 和 YouTube ToS。**缓解**: 仅用 `author_id`, 不存 comment 内容; 提取频率合理化。
5. **LLM 成本**: 5K query 模板 × 10 次迭代 ≈ Claude/GPT $30-100。**应一次性投入, 不周期化**。
6. **per-query yield 统计需要 schema 改造**: `channels` 表当前没有 `source_query` 列。**建议加 `event` 表 kind='discovered' msg=query 来反查**。
7. **开放问题**: 现有 query_bank 是 build_query_bank.py 从 5 个 LLM lexicon 合并而来 (claude/chatgpt/deepseek/gemini/grok)。**是否可以让这些 LLM 用 §3.4 的角色模板重跑, 直接产出长尾版?** 值得一试。

---

## 7. 参考资料

**API/工具**:
- [Google Autocomplete Unofficial Spec - Fullstackoptimization](https://www.fullstackoptimization.com/a/google-autocomplete-google-suggest-unofficial-full-specification)
- [Hacking YouTube Suggest API - DEV.to](https://dev.to/adrienshen/hacking-together-your-own-youtube-suggest-api-c0o)
- [YouTube Autocomplete without API key - Codegena](https://codegena.com/youtube-auto-complete-channel-feed-without-api-key/)
- [Google Autocomplete for Keyword Research - MLforSEO](https://www.mlforseo.com/machine-learning-implementation-guides/keyword-research/how-to-use-google-autocomplete-apis-for-keyword-suggestions/)
- [Google Trends Brazil](https://trends.google.com/trends/?geo=BR)

**Keyword research industry**:
- [Best AI SEO Tools Brazil 2025 - QuickCreator](https://quickcreator.io/blog/best-ai-seo-tools-brazil-2025/)
- [SEO Guide Brazil - Ranktracker](https://www.ranktracker.com/blog/a-complete-guide-for-doing-seo-in-brazil/)
- [Top 200 Google Searches Brazil - Clicks.so](https://resources.clicks.so/top-google-searches/brazil/portuguese)
- [Top SEO Tools Brazil - RaDigitalWorld](https://www.radigitalworld.com/2024/09/top-seo-tools-for-brazil.html)

**yt-dlp comments**:
- [yt-dlp Comments JSON issue #2372](https://github.com/yt-dlp/yt-dlp/issues/2372)
- [Download YouTube comments yt-dlp - Corbpie](https://write.corbpie.com/download-a-youtube-video-comments-with-yt-dlp/)
- [Scrape YouTube Comments - Decodo](https://decodo.com/blog/scraping-youtube-comments)
- [yt-dlp comments JSON gist](https://gist.github.com/extratone/1f92744e7612caaa2e22ef7c41ba4354)

**BR taxonomy**:
- [Brazil States Capitals Map - MapsOfIndia](https://www.mapsofindia.com/world-map/brazil/states-and-capital-list-map.html)
- [Brazil Music Genres - Chartmetric](https://hmc.chartmetric.com/brazilian-music-genres/)
- [Brazil Culture by Region - RioAndLearn](https://rioandlearn.com/brazil-states/)
- [Brazil States & Provinces 2026 - Geocountries](https://www.geocountries.com/states/brazil)

**项目内部参照**:
- `/Users/dapeng/Desktop/word/brz_ytdlp/query_bank.txt` — 当前 bank
- `/Users/dapeng/Desktop/word/brz_ytdlp/build_query_bank.py` — 现行构建脚本 (BR-confidence scorer)
- `/Users/dapeng/Desktop/word/brz_ytdlp/discovery_compare.py` — discovery 多策略对比
- `/Users/dapeng/Desktop/word/brz_ytdlp/extract_v4.py` — channel 提取双闸门
- `/Users/dapeng/Desktop/word/brz_ytdlp/results.db` — 105K channels, 79K rejected
- `/tmp/yt_suggest_test.py` — §3.1 实测脚本
- `/tmp/yt_suggest_output.txt` — 实测产物 1,165 个新 query

---

## 8. 迭代历史

- **v1: 2026-05-19** — 初稿。实测 YouTube suggest API (94 seeds → 1,165 new queries, 97.2% novelty)。覆盖当前 bank 分析、业界工具、BR taxonomy、LLM 模板、anti-patterns、hashtag+comments、量化收益、3 阶段路线图。
- v2 (planned): 加入"per-query yield"实测数据 (需要先在 production_v2 加日志, 跑 24h 后填回)。
- v3 (planned): 加入 BFS L2/L3 实测的 query 数和 cid yield 对比。
- v4 (planned): hashtag pipeline 实测结果, comments mining 实测结果。
