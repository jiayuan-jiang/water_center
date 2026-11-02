
# Spec: Mastodon 数据爬取与分析

_Updated: 2026-08-19（第三个平台，与 Reddit/Bluesky 并行、不合并）_

---

## 目标

爬取 mastodon.social 上与五大湖相关的帖子，时间范围与 Reddit/Bluesky 语料对齐（2023-01-01 至今），独立建模，接入同一套 topic browser。

---

## 背景：为什么不能像 Bluesky 一样按关键词全文搜索

Bluesky 的 `searchPosts` 之所以能做到近似全网关键词搜索，是因为 Bluesky PBC 事实上运营着一个中心化的 Relay + AppView，索引了整个网络的绝大部分公开内容。Mastodon 架构上刻意没有等价物——它是 ~10,000+ 个互相独立的实例，没有任何一方索引全网内容（反监控设计原则）。

- `GET /api/v2/search?type=statuses` 只搜索**本实例的本地索引**，且需要认证 + 该实例装了 ElasticSearch；未认证请求返回空结果（已实测确认）。
- 唯一可行的公开无认证抓取方式是 **hashtag 时间线** `GET /api/v1/timelines/tag/:hashtag`，能拿到本实例 + 联邦同步进来的相关内容，但只覆盖"发帖时用了这个 hashtag"的子集。
- 意外优点：hashtag 时间线是 ID 分页（`max_id`），没有 Bluesky search 那种 30–90 天的实际可用窗口限制，理论上可以一直往回翻到该 hashtag 的最早使用记录。

---

## 数据结构

Mastodon 没有 post / comment 之分，一切都是 status（可能是 reply）。`content` 字段是 **HTML**（`<p>`、`<a class="hashtag">`、`<br>`），不同于 Bluesky 的纯文本 `text`。

### 每条 status 的关键字段

```python
status["id"]                    # 本实例（mastodon.social）本地 ID，唯一
status["created_at"]            # ISO 8601
status["content"]               # HTML，需要 strip
status["language"]              # 可能为 None
status["url"]                   # 完整 permalink——注意可能指向任意联邦实例域名
status["account"]["acct"]       # 本地用户是 "username"，远程用户是 "username@instance.tld"
status["favourites_count"]      # 作为 score
status["in_reply_to_id"]        # 回复目标，无则为 None
```

---

## 爬取策略（`scrapers/scrape_mastodon.py`）

### Hashtag 列表

```python
HASHTAGS = [
    "greatlakes", "lakemichigan", "lakeerie", "lakesuperior",
    "lakehuron", "lakeontario",
    "greatlakeswater", "greatlakesecho",
    "greatlakeswatercompact", "greatlakeswatershedcleanup",
    "michigan", "wisconsin", "ohio", "ontario",
    "chicago", "minnesota", "illinois", "indiana",
]
```

湖名 + `greatlakes*` 前缀标签地域限定明确。后 8 个地名标签（`michigan`/`ohio` 等）用量很大但混杂大量无关内容（体育、政治、日常生活）——刻意保留，靠 `preprocessing/preprocess_mastodon.py` 的关键词相关性过滤器挡掉，而不是从源头排除（按用户决定：先拿全量数据，后续过滤）。

被明确排除、未采用的通用词标签：`pfas`、`algae`、`waterquality`、`invasivespecies` 等——这些是全球通用词，会抓到欧洲/澳洲等无关地区的同名话题，与"五大湖"这个地域限定不匹配。

### 分页与断点续传

- ID 分页：`max_id` 从上一页最后一条 status 的 id 取值，逐页往回翻。
- Checkpoint 文件 `data/mastodon_checkpoint.json`：`{hashtag: {"max_id": ..., "done": bool}}`，每页写盘，支持中断后精确续跑（不像 Bluesky 的 (keyword, month) 粒度，是每页级别）。
- 截止条件：当某页任意一条帖子的 `created_at` 早于 2023-01-01（`THREE_YEARS_AGO`），标记该 hashtag 完成，停止。
- 速率：1.5s/请求；遇到 429 sleep 30s 重试。实测 `#michigan` 这类高流量标签会触发密集限流。

### 已知踩坑

首次不带 checkpoint 跑的版本中途被环境杀掉（可能是工具链的隐藏超时），此后加了 checkpoint 机制，改用 `nohup` 分离出对话轮次生命周期，避免依赖工具自身的后台任务追踪。

---

## 预处理（`preprocessing/preprocess_mastodon.py`）

输入 `data/mastodon_raw.jsonl` → 输出 `data/corpus_mastodon.jsonl`（不合并进 `corpus.jsonl`）。

步骤（对照 `preprocessing/preprocess_bluesky.py`）：
1. 按 `id` 去重
2. 语言过滤：`language` 字段为 `None` 或 `"en"` 则保留
3. **HTML 转纯文本**（Mastodon 特有步骤）：`<br>`/`</p>` → 空格，剩余标签整体去掉，`html.unescape()` 解码实体
4. URL / @mention / #hashtag 清除
5. `MIN_WORDS = 8`（同 Bluesky）
6. 关键词相关性过滤：复用 Bluesky 的 `KEEP_KEYWORDS` 列表——这是过滤掉 `#ohio`/`#michigan` 里无关内容的主力（43,006 条原始 → 39,749 过长度 → 6,219 过相关性 → 5,593 去重后最终语料）
7. 精确文本去重

### 输出 schema（比标准 7 字段多一个 `url`）

```python
{
    "id":          str,   # status 本地 id
    "post_id":     str,   # in_reply_to_id or id
    "source":      "mastodon",
    "author":      str,   # account.acct，如 "user@instance.tld"
    "score":       int,   # favourites_count
    "created_utc": int,
    "text":        str,   # 清洗后纯文本
    "url":         str,   # 原始 permalink，域名因联邦实例而异，无法像 Reddit/Bluesky 那样公式化重建
}
```

未做 bot 黑名单预处理——沿用 Bluesky 的先例（先跑一遍看 outlier 残留噪声，需要再补），实测 outlier 残余噪声率 40%，与 Reddit(41%)/Bluesky 相当，暂不需要。

---

## 话题标注

25 个 BERTopic 话题中人工标注保留 16 个（其余为交通事故、道路施工、餐厅开业、俄亥俄州政治、天气机器人乱码、政治集会通知、Buckeyes 体育等明显无关内容）：

```python
MASTODON_TOPIC_LABELS = {
    0:  "General Great Lakes Discussion",
    1:  "Flooding & Flood Warnings",
    2:  "Great Lakes Restoration & Policy",
    4:  "Lake Rescues & Boating Incidents",
    5:  "Ice Cover & Winter Weather",
    6:  "Beach Safety & Swim Advisories",
    8:  "Environmental Policy & Regulation",
    10: "PFAS & Chemical Contamination",
    11: "Invasive Species & Wildlife",
    12: "Wildfire Smoke & Air Quality",
    14: "Fishing & Fish Populations",
    15: "Algal Blooms",
    17: "Data Centers & Water Consumption",
    21: "Line 5 Pipeline & Litigation",
    22: "Muskegon Waterfront Development",
    24: "Grand River & Riverfront Projects",
}
```

（此 dict 按现有代码库惯例独立复制进了 `build/build_docs_data.py` / `build/build_trend_data.py` / `llm/controversy_llm.py` / `llm/steep_tag.py` / `analysis/subtopic_model.py`（作为 `VALID_TOPICS` 集合）——不是共享模块，是有意保持与 Reddit/Bluesky 现状一致的重复。）

---

## 执行顺序

```bash
python scrapers/scrape_mastodon.py                          # → data/mastodon_raw.jsonl
python preprocessing/preprocess_mastodon.py                       # → data/corpus_mastodon.jsonl
python analysis/topic_model.py --corpus data/corpus_mastodon.jsonl --out-dir data/topics_mastodon
python build/build_docs_data.py --platform mastodon --corpus data/corpus_mastodon.jsonl \
    --topics-dir data/topics_mastodon --out-dir frontend/public/data/mastodon
python build/build_trend_data.py --platform mastodon
python analysis/subtopic_model.py --platform mastodon
python llm/grounded_summary.py --platform mastodon       # 需要 GEMINI_API_KEY
python build/build_subtopic_data.py --platform mastodon
python analysis/sentiment_analysis.py --platform mastodon      # RoBERTa，接入前端 mood 徽章
python analysis/outlier_analysis.py --platform mastodon
python analysis/outlier_emotion.py --platform mastodon
python build/build_outlier_data.py --platform mastodon
python analysis/topic_similarity_network.py --platform mastodon --set topics
python analysis/topic_similarity_network.py --platform mastodon --set outliers

# 以下步骤因 OpenAI 账号日请求配额耗尽（10000/10000）中断，待配额恢复后续跑：
python llm/controversy_llm.py --platform mastodon         # 16/16 topics，仅完成 1 个
python llm/steep_tag.py --target topics --platform mastodon
python llm/steep_tag.py --target outliers --platform mastodon
python llm/outlier_candidates.py --platform mastodon
python build/build_steep_trend.py --platform mastodon       # 依赖上面两步的 CSV
```

---

## 前端接入

数据契约与 Bluesky 完全一致（`data/{platform}/topics.json`、`data/{platform}_topic_trends.json`、`data/subtopics/{platform}/...`、`data/outliers/{platform}/...`、`data/network/{platform}/...`），唯一区别是 comment card 展示真实 `@handle@instance`（而不是 Bluesky 那种扁平化的固定 "Bluesky" 标签），因为 Mastodon 内容横跨几十个不同实例，作者信息比 Bluesky 更有信息量。CSS 用 Mastodon 品牌紫 `#6364FF`（`.source-mastodon`）。

`App.jsx` / `ModeSelect.jsx` / `DetailPanel.jsx` 里原本 `platform === 'bluesky' ? A : B` 的二元三元表达式，在加入第三个平台后全部改成了「reddit 是特例，其余走 `data/${platform}/...` 统一模板」的写法。
