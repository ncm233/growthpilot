# 技术选型记录

> 本文件是最终决策的唯一来源。写代码、写文档、面试讲解如果有出入，以本文件为准。
> 每条选型都标了「为什么」和「什么情况下会重新评估」——这两点是面试被追问选型时的直接答案。

| 层 | 选型 | 为什么 | 什么时候重新评估 |
|---|---|---|---|
| 主力 LLM | **DeepSeek**（`deepseek-chat`） | OpenAI 兼容，价格最低（~¥1/百万 token），`app/llm/openai_compatible.py` 已封装好 | 效果不够时换更强模型，只改 `.env` |
| 降级 LLM | **智谱 GLM-4-Flash** | 免费额度，主力超限/失败时的 fallback | — |
| Embedding | **三档可插拔**：Mock（哈希伪向量）/ **SiliconFlow API**（BAAI/bge-m3，托管，免费）/ BgeEmbedder（bge-small-zh-v1.5，本地） | 见下方「Embedding/Reranker 三档对比」 | 语料涨到数千条以上、或某一档不可用时切换 |
| Reranker | **三档可插拔**：Mock（直通）/ **SiliconFlow API**（BAAI/bge-reranker-v2-m3，托管，免费）/ BgeReranker（bge-reranker-base，本地） | 同上，交叉编码器重排比多次 LLM 调用便宜两个数量级 | 同上 |
| 向量库 | **LanceDB**（嵌入式） | `pip install` 直接用，硬约束：本机无 Docker；原生支持混合检索 RRF 融合 | 数据量上万条、需要多机并发写时换 Postgres+pgvector |
| 全文检索 | LanceDB 内置 FTS | 配合向量检索做混合召回（BM25 + dense） | — |
| 业务数据库 | **SQLite**（保持不变） | 已有实现，单用户 Demo 场景够用 | 生产化 / 需要并发写时换 Postgres，`db.py` 是标准 SQL，迁移成本低 |
| MCP 框架 | **FastMCP (Python)** | 官方推荐的高层封装，`@mcp.tool` 装饰器几行代码定义工具 | — |
| 可观测性 | **Langfuse Cloud**（免费版） | 硬约束：无 Docker，不自托管；免费额度（5 万 observations/月）够用 | — |
| 部署 | **Zeabur** | 中国网络友好、支持 Python、支持持久化卷放 LanceDB；先把一个做扎实，比两个都做但都潦草强 | 如果 Zeabur 免费额度不够用，再加 HF Spaces 做备份 |

## Embedding / Reranker 三档对比

`EMBEDDER_PROVIDER` / `RERANKER_PROVIDER` 各自独立可切换，跟 `LLM_PROVIDER` 是同一套工厂模式（`app/rag/embedder.py::get_embedder()`、`reranker.py::get_reranker()`）：

| 档位 | 依赖 | 网络 | 检索质量 | 什么时候用 |
|---|---|---|---|---|
| `mock` | 零依赖 | 不需要 | 仅字符哈希，只用于验证管线逻辑跑没跑通 | 默认值，clone 下来直接跑 |
| `siliconflow` | 仅 `httpx`（已有） | 需要，调硅基流动托管 API | 真实语义质量（BAAI/bge-m3 + bge-reranker-v2-m3） | **推荐**：不用下载模型，注册即用，免费额度够 Demo 用 |
| `bge` | `sentence-transformers` + torch（`requirements-rag.txt`） | 仅首次下载模型需要，之后完全离线 | 真实语义质量，本地可控 | 网络不稳定、要离线跑、或不想依赖第三方服务时 |

**为什么加 siliconflow 这一档**：本地 bge 方案要装 torch（几百 MB）+ 下载模型（~1.1GB reranker），装到一半才发现拖慢开发节奏不划算。SiliconFlow 直接托管了同系列的 bge 模型（embedding 用 bge-m3，rerank 用 bge-reranker-v2-m3），走 OpenAI 兼容 HTTP 接口，跟项目里 `OpenAICompatibleLLM` 是完全一样的调用模式，零新增重型依赖。**代价是接入了第三方服务的可用性和限流风险**——这也是为什么本地 `bge` 档位没有删掉，留作断网/限流时的退路，三档同一套接口可以随时切换，不改一行 Agent 代码。

面试话术：「Embedding 我做了三档实现，跟 LLM 那层是同一套 Provider 工厂模式。日常开发用 SiliconFlow 托管的 bge-m3，不用下载模型，接入成本最低；如果考虑生产环境对第三方服务的依赖风险，可以随时切到本地 bge 模型，代码不用改，只是 `.env` 里的一个开关。」

### 真实数据验证：Mock vs 真实语义检索

用同一批查询在 Mock（哈希伪向量）和真实模式（SiliconFlow bge-m3 + bge-reranker-v2-m3）下对比：

| 查询 | Mock top1 分数 | 真实模式 top1 分数 | 差距说明 |
|---|---|---|---|
| "提交表单 到 结账 转化流失" | 0.0323 | 0.8891 | Mock 模式所有候选分数挤在 0.03 附近，区分度极弱 |
| "落地页 CTA 按钮 颜色" | 0.0325 | 0.997 | 同上 |
| "个性化推荐 提升点击率"（语料里无原词） | 未测试 | 0.8473 命中 Netflix 缩略图案例 | 真正的语义泛化，不是关键词命中 |
| 无关查询"今天北京天气怎么样" | — | status=`wrong`，未采用 | CRAG 降级正确触发，不会把不相关内容硬塞进 prompt |

**结论**：Mock 模式下重排分数几乎没有区分度（top1 和 top2 只差 0.001），这也是为什么 `retriever.py` 里 `_grade()` 对 `MockReranker` 直接跳过分级——阈值化一个没有意义的分数只是自欺欺人，这个设计判断在真实数据出来后被验证是对的。

### 真实数据验证：query 措辞对检索质量的影响（一个推翻了自己假设的发现）

最初假设"bge 类模型偏好自然语言问句"，把 `opportunity_agent` 的检索 query 从电报体拼接改成完整问句，结果**反而更差**（从 ambiguous 掉到 wrong）。用同一份语料做了系统 A/B：

| Query 写法 | 示例 | top1 分数 | 分级 |
|---|---|---|---|
| 电报体拼接 | "开始填写表单 到 提交表单 转化流失" | 0.288 | ambiguous |
| 完整自然语言问句 | "用户从「开始填写表单」到「提交表单」之间大量流失，可能是什么原因导致的，怎么改善？" | — | **wrong**（反而更差） |
| 核心概念极简 | "表单填写流失" | 0.725 | correct |
| 场景风格短语 | "注册表单转化流失" | 0.963 | correct |
| **仅 to_step + 转化流失（最终采用）** | "提交表单转化流失" | **0.887** | **correct** |

**真正的原因不是"自然语言更好"，而是 query 和语料的文本风格要匹配。** 本项目语料的 `search_text` 字段本身是 `scene+hypothesis+intervention+lesson` 拼接的短句、关键词密集，不是对话式问句；query 越像语料自己的写法，检索分数越高，跟"是否像自然语言"关系不大。最终 `opportunity_agent.py` 采用 `f"{to_step}转化流失"`——短、不依赖硬编码业务假设、且是系统测试里除了手工挑选的"场景风格"外分数最高的通用写法。

**这个发现比"选对了"更值钱**：它证明了技术选型不是查文档定下来的，是自己用真实数据测出来的，第一次假设错了，测出来之后改了判断——这正是面试官想看到的工程判断过程，而不是背答案。

## 数据相关（明确的分阶段安排，不是待定）

| 数据 | 当前 Phase 1 | Phase 3 |
|---|---|---|
| Demo 用的转化漏斗 | `generate_synthetic_data.py` 造的合成数据（先跑通 RAG 管线代码逻辑，不被数据接入卡住主线） | 换成 [天池 UserBehavior](https://tianchi.aliyun.com/dataset/649) 抽样数据，`pv→cart→fav→buy` 天然对应真实漏斗 |
| Eval 用的实验数据 | 保持现有合成用例（当前 `report.json` 满分的问题根源是评测设计缺对抗性用例，不是数据来源，见 [API_AND_MATERIALS.md](API_AND_MATERIALS.md)） | 接入 [Kaggle marketing-ab-testing](https://www.kaggle.com/datasets/faviovaz/marketing-ab-testing)（58.8 万行真实数据）+ 20 条对抗性用例，一次性解决 |
| RAG 语料 | 8 条种子案例（已入库） + 持续补充见 [CORPUS_SOURCES.md](CORPUS_SOURCES.md) | 补到 80–300 条 |

**为什么不现在就换真实数据**：Phase 1 的目标是把 RAG 管线代码（embedder → store → retriever → citations）跑通，数据源是可替换的输入，不是这一阶段的瓶颈。先用合成数据验证逻辑，再换真实数据源，两件事解耦，互不阻塞。**面试可以直接讲这个顺序安排的理由**——工程上"先让链路跑通，再换更真实的输入"是标准做法。

## 面试话术模板

> 「Embedding 选 bge-small-zh 是权衡过的：我的语料量级在几百条，小模型的检索质量已经够用，
> 换大模型对效果提升有限，但会明显拖慢冷启动和部署成本。如果语料涨到几千条以上，
> 我会重新评估换 bge-m3。」

> 「Demo 数据我是分两步接的：先用合成数据把 RAG 管线本身的逻辑跑通，
> 确认 embedder、检索、重排、citation 拼装都没问题，再单独接入天池真实数据替换数据源。
> 这样两件事解耦，管线开发不会被数据清洗卡住进度。」
