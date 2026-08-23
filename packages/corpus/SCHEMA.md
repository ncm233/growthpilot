# 语料 Schema

`packages/corpus/curated/*.jsonl` 里每一行一条记录，字段如下（对应 [API_AND_MATERIALS.md](../../docs/API_AND_MATERIALS.md) 里定义的 schema）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | `exp-XXXX`，四位数字递增 |
| `scene` | string | 业务场景，如"SaaS 官网注册转化" |
| `channel` | string | 渠道/触点，如 `landing_page` / `checkout_form` / `referral` |
| `hypothesis` | string | 实验假设 |
| `intervention` | string | 具体改动 |
| `metric` | string | 被优化的指标名（snake_case） |
| `baseline` | number \| null | 基线值；不适用时为 `null` |
| `result` | number \| null | 实验后数值；不适用时为 `null` |
| `lift` | string | 效果描述，如 `"+21%"` 或 `"$12M/年"` |
| `outcome` | `"positive"` \| `"negative"` \| `"flat"` | 实验方向 |
| `confidence` | `"primary"` \| `"secondary"` | **结构化字段，不要塞进 lesson 文本里判断**——`secondary` 表示数字是行业广泛引用但找不到一手出处（早期版本靠在 `lesson` 里搜"二手"关键字来判断，会漏判措辞不同的条目，见 `app.js` 曾经的 bug） |
| `lesson` | string | 可复用的结论，人话解释，不承担"一手/二手"标记职责 |
| `source` | string | 出处名称 |
| `source_url` | string | 出处链接，必须是能打开的真实页面 |

## 语料来源分两类

1. **`curated/seed_cases.jsonl`** — 本仓库已收录的种子语料（8 条），全部经过 WebSearch 逐条核实链接和数字，可信度分层标注在 `lesson` 字段里。
2. **待扩充部分** — 目标 150–300 条，链接来源见 [docs/CORPUS_SOURCES.md](../../docs/CORPUS_SOURCES.md)。**不做自动爬虫**：GoodUI 等付费案例库有 ToS 限制，人工筛选、手动转录成本可控且更真实，也是面试时"语料怎么来的"这个问题最站得住脚的答案。
