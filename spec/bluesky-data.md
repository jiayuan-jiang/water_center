
# Spec: Bluesky 数据爬取

_Updated: 2026-06-24（基于官方 API 实测结果）_

---

## 目标

爬取 Bluesky 上与五大湖相关的帖子，时间范围与 Reddit 语料对齐（2023-01-01 至今），合并进 `data/corpus.jsonl` 供 BERTopic 分析。

---

## 背景：leobalduf vs 官方 API

| 方案 | 状态 | 优先级 |
|------|------|--------|
| leobalduf Firehose 日志申请 | 邮件已发（2026-06-24），等回复 | 备用 |
| 官方 `searchPosts` API | **实测可用，覆盖 2023 年至今** | **当前执行方案** |

---

## 数据结构（重要：与 Reddit 不同）

Bluesky 没有 post / comment 之分，**一切都是 post**。回复是带 `reply` 字段的 post。

```
Reddit：Post → [Comment, Comment → [Reply...]]
Bluesky：Post_A（root）
         Post_B（reply → parent=A）
         Post_C（reply → parent=B）
```

`searchPosts` 返回扁平列表，root post 和 reply 混在一起，**都带完整文本，直接可用**，不需要像 Reddit 那样单独抓评论。

### 每条 post 的关键字段

```python
post.uri              # 唯一 ID: at://did:plc:.../app.bsky.feed.post/rkey
post.record.text      # 正文（最长 300 字）
post.record.created_at  # ISO 8601 时间戳
post.record.reply     # None = 原帖；有值 = 回复（含 parent.uri, root.uri）
post.author.handle    # 用户名 xxx.bsky.social
post.author.did       # 用户唯一 ID
post.like_count
post.reply_count
post.repost_count
```

---

## 爬取策略

### 认证
`searchPosts` **必须登录**（未登录返回 401）。使用账号密码登录，凭证从环境变量读取，不硬编码。

```python
client = Client()
client.login(os.environ["BSKY_USER"], os.environ["BSKY_PASS"])
```

### 关键词与查询语法

**Bluesky 搜索行为（实测 2026-06-24）：**

| 写法 | 行为 |
|------|------|
| `"Great Lakes"`（加引号）| 精确短语匹配，必须连续出现 |
| `Great Lakes`（不加引号）| AND 逻辑，两词不要求相邻，易产生噪声 |
| `#GreatLakes` | 匹配 hashtag，与加引号的短语结果**不完全重叠** |
| 大小写 | 完全不敏感 |



因此每个湖名需要拆成**两条独立查询**：加引号的精确短语 + hashtag，才能同时覆盖正文提及和标签标注两种表达方式。

```python
QUERIES = [
    # 精确短语（匹配正文）
    '"Great Lakes"',
    '"Lake Michigan"',
    '"Lake Erie"',
    '"Lake Superior"',
    '"Lake Huron"',
    '"Lake Ontario"',
    # Hashtag（与短语结果不完全重叠，需单独查）
    '#GreatLakes',
    '#LakeMichigan',
    '#LakeErie',
    '#LakeSuperior',
    '#LakeHuron',
    '#LakeOntario',
]
```

**注意：** 不使用 `OR` 合并（如 `"Great Lakes" OR #GreatLakes`），因为合并后无法通过 cursor 拿到完整结果，且两条独立查询在去重逻辑中会通过 `uri` 自动合并。

### 时间范围
```
开始：2023-01-01
结束：当前日期
```

### 分页策略（关键）

`sort=oldest` 不生效（实测返回最新帖），必须用 **月度时间窗口 + cursor 分页** 组合：

```
for keyword in KEYWORDS:
    for month in [2023-01, 2023-02, ..., 2026-06]:
        cursor = None
        while True:
            resp = searchPosts(q=keyword, since=month_start, until=month_end,
                               limit=100, cursor=cursor)
            保存结果
            if resp.cursor is None: break
            cursor = resp.cursor
```

**为什么要切月？**
- 每次最多返回 100 条
- cursor 分页才能取完某个时间窗口内的全部结果
- 时间窗口太大（如整年）时，100 条可能只覆盖窗口末尾几天

### 去重
用 `post.uri` 做唯一键，跨关键词查询会有重叠（如一条帖子同时提到 "Lake Michigan" 和 "Great Lakes"）。

### 速率控制
- 官方限制：3000 次请求 / 5 分钟（极宽松）
- 每次请求后 sleep 0.5s，礼貌性延迟即可
- 遇到 429 则 sleep 30s 后重试

### 断点续传
维护 `data/bluesky_checkpoint.json`，记录已完成的 `(keyword, month)` 组合，支持中断后继续。

checkpoint 文件格式：

```json
{
  "done": [
    ["Great Lakes", "2023-01"],
    ["Great Lakes", "2023-02"],
    ["Lake Michigan", "2023-01"]
  ]
}
```

每完成一个 `(keyword, month)` 的全量分页后追加写入，不要等全部完成才写。

### 月份窗口生成

```python
from datetime import date, timezone
from dateutil.relativedelta import relativedelta

def month_windows(start: date, end: date):
    """Yield (since_str, until_str) for each calendar month in [start, end)."""
    cur = start.replace(day=1)
    while cur <= end:
        nxt = cur + relativedelta(months=1)
        yield (
            cur.strftime("%Y-%m-%dT00:00:00Z"),
            (nxt - relativedelta(days=1)).strftime("%Y-%m-%dT23:59:59Z"),
        )
        cur = nxt
```

调用示例：

```python
for since, until in month_windows(date(2023, 1, 1), date.today()):
    ...
```

---

## 注意事项

1. **文本极短**：Bluesky 帖子最长 300 字（约 50–60 词），远短于 Reddit 评论。`MIN_WORDS` 阈值应降低到 5–8 词，否则大量数据会被过滤掉。

2. **数量预期要低**：Bluesky 用户体量远小于 Reddit，且五大湖相关讨论更少。预计几百到几千条，不要期望 Reddit 量级。

3. **语言过滤**：`post.record.langs` 字段可用，但并非所有帖子都填写，建议不强过滤，让预处理阶段处理。

4. **reply vs root 无需区分**：两者都含完整文本，统一处理即可。如需分析讨论结构（哪些话题引发了更多回复），可用 `reply_count` 字段。

5. **`since`/`until` bug 状态**：GitHub issue #3258 报告的 bug（加日期参数报错）在 2026-06-24 实测中**已不复现**，参数可正常使用。

6. **凭证安全**：不得将账号密码写入代码或提交到 git。始终从环境变量读取：
   ```bash
   export BSKY_USER=jiayuanj@umich.edu
   export BSKY_PASS=<password>
   ```

---

## 输出格式

文件：`data/bluesky_raw.jsonl`，每行一个 JSON 对象：

```json
{
  "uri": "at://did:plc:xxx/app.bsky.feed.post/yyy",
  "author_handle": "user.bsky.social",
  "author_did": "did:plc:xxx",
  "created_at": "2024-03-15T12:34:56.789Z",
  "text": "原始帖子文本",
  "like_count": 3,
  "reply_count": 1,
  "repost_count": 0,
  "is_reply": false,
  "parent_uri": null,
  "root_uri": null,
  "keyword": "Great Lakes"
}
```

---

## 预处理注意（preprocess 阶段）

输出到 `data/corpus_bluesky.jsonl`，**不合并进** `data/corpus.jsonl`。两个平台独立保存、独立建模。

Schema 映射：

```python
{
  "id":          post["uri"].split("/")[-1],   # rkey 作为 ID
  "post_id":     post["root_uri"],             # 原始 thread root（root post 时与 id 相同）
  "source":      "bluesky",
  "author":      post["author_handle"],
  "score":       post["like_count"],
  "created_utc": int(datetime.fromisoformat(post["created_at"]).timestamp()),
  "text":        cleaned_text,
}
```

`MIN_WORDS` 建议改为 **8**（而非 Reddit 的 15），因为 Bluesky 帖子天然更短。

---

## `scrape_bluesky.py` 算法（伪代码）

```python
CHECKPOINT_FILE = "data/bluesky_checkpoint.json"
OUT_FILE        = "data/bluesky_raw.jsonl"
START_DATE      = date(2023, 1, 1)

# 加载 checkpoint
done = set(map(tuple, checkpoint.get("done", [])))
seen_uris = set(line["uri"] for line in read_existing_raw())  # 去重

client = Client(); client.login(BSKY_USER, BSKY_PASS)

for keyword in KEYWORDS:
    for since, until in month_windows(START_DATE, date.today()):
        month = since[:7]           # "2023-01"
        if (keyword, month) in done:
            continue

        cursor = None
        while True:
            resp = client.app.bsky.feed.search_posts(
                params={"q": keyword, "since": since, "until": until,
                        "limit": 100, "cursor": cursor}
            )
            for post in resp.posts or []:
                if post.uri in seen_uris:
                    continue
                seen_uris.add(post.uri)
                write_jsonl(OUT_FILE, to_record(post, keyword))

            if not resp.cursor:
                break
            cursor = resp.cursor
            time.sleep(0.5)

        done.add((keyword, month))
        save_checkpoint(done)
```

`to_record(post, keyword)` 按照「输出格式」一节定义的字段提取即可。

---

## `preprocess_bluesky.py` 规格

文件：`preprocess_bluesky.py`（独立于 `preprocess.py`，不修改现有 Reddit 预处理逻辑）

**输入**：`data/bluesky_raw.jsonl`
**输出**：`data/corpus_bluesky.jsonl`（独立语料库，**不合并进** `corpus.jsonl`）

> 设计原则：Reddit 和 Bluesky 是两个独立平台，用户群体、话语风格、帖子长度差异显著。分开保存、分开建模，便于平台间结果对比，避免一个平台的噪声污染另一个平台的 topic。

### 清洗步骤

1. **去重**：按 `uri` 字段去重（scraper 侧已处理，这里二次保险）
2. **语言过滤**：跳过 `langs` 字段明确非英语的帖子（如 `["fr"]`、`["de"]`）；`langs` 缺失或包含 `"en"` 则保留
3. **文本清洗**：
   - 去除 URL（`https?://\S+`）
   - 去除 @mention（`@\w+`）
   - 去除前导/尾随空白
4. **最小词数过滤**：`MIN_WORDS = 8`（低于 Reddit 的 15，因为 Bluesky 帖子天然更短）
5. **Schema 映射**（见预处理注意一节）

### 输出 schema（与 corpus.jsonl 字段一致）

```python
{
    "id":          str,   # uri 的 rkey 部分
    "post_id":     str,   # root_uri（原帖；若为 root 则与 id 相同）
    "source":      "bluesky",
    "author":      str,   # author_handle
    "score":       int,   # like_count
    "created_utc": int,   # Unix 时间戳
    "text":        str,   # 清洗后文本
}
```

---

## 分析流程（与 Reddit 流程平行，不合并）

Bluesky 使用与 Reddit **完全相同的分析方法**，但在独立的数据文件和输出目录下运行：

| 步骤 | Reddit | Bluesky |
|------|--------|---------|
| 语料 | `data/corpus.jsonl` | `data/corpus_bluesky.jsonl` |
| 主题建模输出 | `data/topics/` | `data/topics_bluesky/` |
| 词云 | `data/wordclouds/` | `data/wordclouds_bluesky/` |
| Topic browser | `docs/` | `docs/bluesky/`（或同一 browser 加 platform 切换） |

`topic_model.py` 和 `build_docs_data.py` 需支持 `--corpus` / `--out-dir` 参数（或通过环境变量），以便复用同一套代码跑两个平台。

---

## 执行顺序

```bash
export BSKY_USER=jiayuanj@umich.edu
export BSKY_PASS=<password>

# 1. 爬取
python scrape_bluesky.py                          # → data/bluesky_raw.jsonl

# 2. 预处理
python preprocess_bluesky.py                      # → data/corpus_bluesky.jsonl

# 3. 建模（独立于 Reddit，不合并）
python topic_model.py \
    --corpus data/corpus_bluesky.jsonl \
    --out-dir data/topics_bluesky

# 4. 构建 topic browser 数据
python build_docs_data.py \
    --topics-dir data/topics_bluesky \
    --out-dir docs/bluesky
```
