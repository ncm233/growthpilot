# GrowthPilot 面试讲解稿

> 用法：`一` 到 `三` 是主动输出的内容（背熟）；`四` 到 `六` 是被追问时的弹药（理解即可）；
> `七` 是短板与坦诚话术（**这部分决定你是"会做项目的人"还是"会做项目且知道边界的人"**）。

---

## 一、三个长度的自我介绍

### 30 秒版（HR / 简历初筛）

> GrowthPilot 是一个自主增长实验 Agent。你给它一个业务目标，比如"把注册转化率从 3.4% 提到 5%"，
> 它会从数据里定位流失最严重的环节、检索历史相似案例、生成 A/B 实验方案、做效果模拟排序，
> 然后**停下来**推一张审批卡片给人，人批准之后才写回原系统，并把结论沉淀进长期记忆。
> 全链路开源、已部署，也封装成了 MCP Server，你现在用 Claude Desktop 就能直接调用它。

### 90 秒版（技术面开场）

在 30 秒版基础上补三句：

> 技术上有三个我比较想讲的点。
> 第一是**可插拔的数据接入层**——企业微信、飞书、CRM、ERP、表单、埋点这六个外部系统，
> 每个都是 Mock/Real 双实现 + 工厂函数，没配密钥自动走 Mock，配了自动切真实实现，业务代码一行不改。
> 第二是**检索增强的假设生成**——实验方案不是让 LLM 凭空编，而是先从 200 多条增长案例库里混合检索 + 重排，
> 带引用注入 prompt，生成的每条假设都能点开看依据。
> 第三是**独立的 Critic 校验层**——专门检查两件事：预算有没有超限，以及方案里引用的数字跟原始漏斗数据对不对得上。
> 这两个检查点直接对应我评测集里的两个指标。

### 3 分钟版（深聊）

按 `二、架构主干` 的九层顺序讲一遍，每层一句话，重点停在 2 / 3 / 5 / 9 层。

---

## 二、架构主干：一次请求的完整生命周期

**这是整个面试的锚点。任何架构问题都可以拉回这条链回答。**

```
POST /runs { goal_text: "把创作者注册转化率从 3.4% 提到 5%", budget_limit: 50000 }
   │
   ├─① research_agent.extract_goal()
   │     自然语言 → {metric_name: "registration_conversion", target: 0.05}
   │
   ├─② data_agent.gather(metric_name, tools)
   │     并行调 analytics / form / crm / erp 四个工具 → 聚合成统一漏斗结构
   │     [每个工具都是 get_xxx_tool() 工厂返回，Mock 或 Real 取决于 .env]
   │
   ├─③ opportunity_agent.find_opportunity(raw_data, llm)
   │     扫描漏斗各环节流失率 → 定位最大流失点
   │     └─[RAG] retriever.search(场景+渠道+指标)
   │           BM25 + 向量混合检索 → bge-reranker 重排 → CRAG 分级
   │           → top-k 历史案例带引用注入 prompt
   │
   ├─④ experiment_agent.design_experiment(opportunity, raw_data, budget_limit, llm)
   │     产出 {hypothesis, type, variant_a, variant_b, proposed_budget, narrative}
   │
   ├─⑤ critic_agent.review(...)  ◄──── 独立校验，与生成方分离
   │     检查 1：proposed_budget > budget_limit ?
   │     检查 2：opportunity 声称的 from_users/to_users 是否等于原始漏斗真实值 ?
   │     检查 3：drop_rate 重算一遍是否对得上 ?
   │     └─ 不通过 → Reflect 回环（MAX_RETRIES=1），修正后重审
   │
   ├─⑥ simulator.run(run_id, opportunity, experiment, llm)
   │     Persona 模拟 → {summary, confidence}，用于多方案优先级排序
   │
   ├─⑦ feishu.create_approval() + feishu.send_message()
   │     生成审批卡片 → 推送给审批人
   │
   └─⑧ INSERT INTO runs (status = "pending_approval")

═══════════ 人工审批边界：Agent 到此为止，绝不自动执行 ═══════════

POST /runs/{id}/decide { decision: "approved" }
   │
   ├─ approved → form.update_fields() 或 crm.update_tag()   真实写回
   │             wecom.send_message()                        通知执行结果
   ├─ rejected → 仅记录，不执行
   │
   └─⑨ INSERT INTO memory (hypothesis, channel, result, confidence, lesson)
         结构化沉淀，供下一次 RAG 检索复用 ——闭环在这里合上
```

**讲这条链时要强调的三个"停顿点"**：
1. **⑤ Critic** —— 生成和校验必须分离，同一个 LLM 自己检查自己没有意义
2. **⑦⑧ 审批边界** —— 这是整个设计里最重要的一条线，见决策 #1
3. **⑨ 写回 memory** —— 闭环点。这次的结论会变成下次 RAG 的语料

---

## 三、九层分层与各层要点

| 层 | 一句话职责 | 面试要点 |
|---|---|---|
| 1 工具/数据接入 | 6 个外部系统统一成可调用工具 | Mock/Real 工厂模式，见决策 #2 |
| 2 检索增强 RAG | 为假设生成提供事实依据 | 混合检索 + 重排 + CRAG，见决策 #4 |
| 3 MCP 暴露 | 工具与检索暴露为标准 MCP 工具 | 让任意 MCP 客户端直连，见决策 #3 |
| 4 Agent 核心 | 5 个专职 Agent + Plan→Tool→Verify→Reflect | 角色分化，见决策 #5 |
| 5 记忆 | 结构化存实验历史 | 存结构化字段而非原文，见决策 #6 |
| 6 模拟 | 实验前预测方向做排序 | 便宜的预筛，不是替代真实实验，见决策 #7 |
| 7 审批与写回 | 人工确认后才动真实系统 | Human-in-the-loop，见决策 #1 |
| 8 评估 | 验证不编造指标、不违反预算 | 见 `五、数据与评估` |
| 9 可观测 | Langfuse 全链路 tracing | 检索命中率/工具成功率/延迟/成本 |

---

## 四、八个关键设计决策（被追问时的主要弹药）

每条都按 **决策 → 备选方案 → 为什么这么选 → 代价** 的格式讲。
**主动说出"代价"是最强的加分信号**——它证明你是权衡出来的，不是抄来的。

### 决策 #1：Agent 不自动执行，必须过人工审批

- **决策**：Agent 产出到"审批卡片"为止，人点批准后才写回业务系统
- **备选**：全自动执行 + 事后回滚
- **为什么**：增长实验会真实改动线上表单、CRM 标签、投放预算，是**不可逆的对外动作**。
  当前 LLM 在业务判断上的可靠性还不足以承担这个风险。而且中国企业的组织结构里，
  预算动用本来就必须走审批——这不是技术妥协，是业务现实。
  这也正好对应 *Code as Agent Harness* 综述里提出的开放问题之一：safety-critical actions 的 human oversight。
- **代价**：牺牲了端到端自动化的"炫技感"，链路里多了一个人工延迟。
  换来的是这套系统真的敢在企业里上线。

### 决策 #2：每个外部系统做 Mock/Real 双实现 + 工厂函数

- **决策**：`get_feishu_tool()` 读 `.env`，没密钥返回 `MockFeishuTool`，有密钥返回 `RealFeishuTool`
- **备选**：直接写死真实 API 调用 / 用 mock 库在测试里打桩
- **为什么**：三个收益。①**任何人 clone 下来立刻能跑**，不需要申请六家企业 API——这对开源项目的可用性是决定性的；
  ②评测可以完全离线跑，`packages/eval` 不依赖外部网络；
  ③接真实系统时业务代码零改动，降低集成风险。
- **代价**：多维护一套 Mock 实现，且 Mock 和 Real 的行为一致性需要人工保证（没有契约测试）。
  **如果被问"怎么保证 Mock 和 Real 行为一致"——诚实回答目前靠 `tools/base.py` 的抽象基类约束签名，
  但没有契约测试，这是我知道的一个短板。**

### 决策 #3：把工具层暴露为 MCP Server，而不是只做 HTTP API

- **决策**：用 FastMCP 把检索和数据工具封装成标准 MCP 工具（`search_growth_playbook` / `fetch_growth_data` /
  `propose_experiment` / `get_experiment_status`），独立 venv、HTTP transport
- **备选**：只提供 REST API / 只做 LangChain Tool
- **为什么**：MCP 在 2026 年已经是事实标准（Anthropic 捐给 Linux Foundation 的 Agentic AI Foundation 三大支柱之一）。
  做成 MCP 意味着 Claude Desktop、Cursor、任何 MCP 客户端都能直接接入，
  而不是只有我自己的前端能用。**对企业客户来说，这意味着他们现有的 AI 工具链能直接复用我的能力。**
- **代价（都是实测出来的，不是纸上谈兵）**：
  1. **独立 venv**：`fastmcp` 需要的 `starlette`/`uvicorn` 版本区间跟 agent-service 锁定的
     `fastapi==0.115.0` 直接冲突，装进同一个 venv 会当场把 FastAPI 服务弄坏（实测复现过）。
     两个 venv 是唯一干净的解法，代价是要多维护一套依赖。
  2. **HTTP transport 而非更常见的 STDIO**：真实子进程 + 真实协议测试发现，任何调用
     LanceDB（Rust/tokio 后端）的工具在 STDIO transport 下会**永久挂死**，换成 HTTP 瞬间返回。
     这跟 MCP Python SDK 仓库报告过的一类已知问题吻合。没有深挖 Rust/Python 双运行时冲突的根因，
     直接换 transport——HTTP 本来也是 Phase 5 部署需要的东西。
  3. 顺带踩到一个更隐蔽的坑：`python -m pkg.server` + 跨文件 `@mcp.tool`（`from ..server import mcp`）
     会导致 Python 把 `server.py` 导入两次（一次绑定成 `__main__`，一次通过相对导入正常导入），
     工具注册到了"空气"那份 `mcp` 对象上，`mcp.run()` 却跑在另一份空的实例上——**客户端连得上，
     工具列表永远是空的，不报任何错误**。改成 `python -m pkg`（走 `__main__.py`）才解决。
  完整排查过程见 [docs/TECH_STACK.md](TECH_STACK.md)。
- **面试话术**：「我一开始按最常见的教程用 STDIO transport，写完在 in-process 单元测试里全部通过，
  但我特意又用真实子进程 + 真实 JSON-RPC 协议测了一遍——这才发现 STDIO 下 LanceDB 调用会挂死。
  只测函数调用，不测真实协议，这个坑我不会发现。」

### 决策 #4：混合检索 + 交叉编码器重排，而不是纯向量检索

- **决策**：BM25 全文 + 稠密向量并行召回 → RRF 融合 → bge-reranker 重排 → CRAG 分级
- **备选**：纯向量 top-k
- **为什么**：增长案例语料有大量**专有名词和精确指标**（"漏斗""留存率""RRF""cold start"），
  纯语义向量对这类精确匹配不敏感，BM25 正好补上。
  重排用 cross-encoder 而不是让 LLM 逐条打分，是因为 **1 亿参数级的重排模型比多次 LLM 调用便宜两个数量级，延迟也低得多**。
  CRAG 分级（Correct / Ambiguous / Wrong）用来决定：检索质量差的时候要不要触发查询重写或者干脆声明"没有可参考案例"。
- **代价**：多了一个模型要加载（~1.1GB 显存/内存），冷启动变慢；
  混合检索的融合权重目前是拍脑袋定的，没做超参搜索。

### 决策 #5：五个专职 Agent，而不是一个大 Agent 带一堆工具

- **决策**：research / data / opportunity / experiment / critic 五个角色分化
- **备选**：单 Agent + ReAct 循环调所有工具
- **为什么**：三个原因。①**每个 Agent 的 prompt 可以窄而深**，不用在一个 prompt 里塞五种任务的指令；
  ②**Critic 必须独立**——生成方和校验方共享上下文的话，校验会被生成时的错误假设污染；
  ③每个环节可以单独评测（`packages/eval` 里 opportunity 检出率和幻觉捕获率是分开算的）。
  这对应 *Code as Agent Harness* 里 Scaling 层的"角色分化"模式。
- **代价**：链路是固定顺序的流水线，缺少动态重规划能力。
  遇到需要反复横跳的复杂任务（比如需要先看 CRM 再回头补埋点数据），当前架构处理不了。
  **这是我下一步想改成图式编排的原因。**

### 决策 #6：Memory 存结构化字段，不存对话原文

- **决策**：`memory` 表存 `{hypothesis, channel, result, confidence, lesson}` 五个结构化字段
- **备选**：把每次 run 的完整上下文序列化存下来
- **为什么**：结构化字段可以直接做条件检索（"找同渠道、结果为正、置信度 > 0.7 的历史实验"），
  而对话原文只能做语义检索。而且原文塞进 prompt 会迅速吃满上下文窗口——
  这正是"Remember, Don't Re-read"那类工作的核心主张。
- **代价**：丢失了推理过程的细节。如果想复盘"当时为什么会得出这个结论"，现在查不到。
  **Phase 3 接了 Langfuse 之后，这部分由 trace 补上。**

### 决策 #7：加一层 Persona 模拟层

- **决策**：实验方案生成后，先跑 Persona 模拟预测方向和置信度，再进入审批
- **备选**：直接把所有方案推给人审批
- **为什么**：真实 A/B 实验的成本是"两周时间 + 一半流量"，极其昂贵。
  模拟层的作用不是**替代**真实实验，而是做**便宜的预筛和优先级排序**——
  当有 5 个候选方案时，先跑模拟排个序，人只需要重点看排前 2 的。
- **代价**：模拟结果的绝对数值不可信，只有相对排序有参考价值。
  **这一点我在 UI 上明确标注了，避免使用者误读。** 评测里我也只测"方向准确率"，不测数值误差。

### 决策 #8：SQLite + LanceDB，不上 Postgres + 独立向量库

- **决策**：SQLite 存业务数据，LanceDB 嵌入式存向量
- **备选**：Postgres + pgvector / Milvus / Qdrant
- **为什么**：**零运维依赖，`pip install` 就能跑，不需要 Docker。**
  对一个要让别人 clone 下来五分钟跑通的开源项目，这个优先级高于性能。
  LanceDB 还原生支持混合检索的 RRF 融合，省了自己实现的功夫。
- **代价**：单机、无并发写、数据量上万条以后检索延迟会涨。
  **生产化要换 Postgres + pgvector，但换的成本很低，因为 `app/rag/store.py` 是接口隔离的。**

### 决策 #9：用 Langfuse 的语义化 `as_type`，不是所有 span 都叫 "span"

- **决策**：`@observe(as_type=...)` 按角色打类型——Agent 用 `agent`、Critic 用 `guardrail`、
  RAG 检索用 `retriever`、LLM 叙述用 `generation`、外部系统调用用 `tool`
- **备选**：所有装饰都用默认的 `span`，靠 name 字段区分
- **为什么**：Langfuse 后台按类型渲染不同图标和统计维度（比如 `generation` 会单独统计 token/成本，
  `guardrail` 会在 UI 上高亮成校验节点），打对类型让 trace 树一眼能看出"这是谁在做什么"，
  不用逐条点开看 name。这也逼着我在写代码时明确想清楚"这个函数到底是 Agent 决策、工具调用、
  还是纯校验"，是一次有价值的架构复盘。
- **代价**：几乎没有——多打一个参数的事。**唯一的代价是接上的第一天就看到了一个自己没意识到的
  性能问题**（见下面这条），不算代价，算意外收获。
- **接上当天就看到的真实发现**：跑一次真实 `/api/run`，Langfuse trace 显示单次请求 7.96 秒，
  其中两次 RAG 检索（`opportunity_agent` 和 `experiment_agent` 各查一次真实 SiliconFlow API）
  加起来占了 85% 以上（4.54s + 2.25s）。**这不是靠猜的优化方向，是数据直接指出来的**——
  Phase 4 已经把这个问题修掉，见决策 #10。

### 决策 #10：给 embedding/rerank 加进程级缓存，不是把两次检索并行化

- **决策**：`SiliconFlowEmbedder.embed_query()` 和 `SiliconFlowReranker.rerank()` 各自加一个
  模块级缓存 dict，key 分别是 `(model, text)` 和 `(model, query, top_k, 候选id集合)`
- **备选（一开始以为该这么做，后来发现不成立）**：用 `asyncio.gather` 把两次检索并行化
- **为什么不是并行化**：`experiment_agent` 的检索 query 是从 `opportunity_agent` 的输出里构造出来的
  （`experiment["hypothesis"]` 引用了 `opportunity['from_step']`/`to_step`），两次检索之间是真正的
  **数据依赖**，不是两个独立任务，`asyncio.gather` 用不上。这是先分析依赖关系、发现最初设想的方案
  站不住脚，然后换了真正可行的方案——不是「加了并行就当作优化交差」。
- **为什么缓存能生效**：Demo 数据是按 `metric_name` 确定性播种生成的，同一个目标反复跑，
  检索 query 文本完全一样。缓存对这个场景是精准命中，不是碰运气的优化。
- **实测效果**：冷启动 5.416s → 缓存命中 0.032s，**降低 99.4%**。用 Langfuse 自己接的 tracing
  基础设施验证了自己的优化——发现问题靠 trace，验证修复也靠 trace，是个完整闭环。
- **代价 / 边界**：只对 SiliconFlow 这两个走真实网络的实现加了缓存，Mock/本地 bge 没加
  （本来就够快，加缓存没有意义）。缓存是进程内存，没有过期策略——query embedding 缓存本身没有
  失效风险（同一个 query 文本的向量在同一个模型下永远不变，跟语料库内容无关）；但 rerank 缓存的
  key 包含候选案例的 id 集合，如果**语料库里某条已有 id 的内容被编辑过**（而不是新增新 id），
  重排缓存会返回基于旧内容算出的分数，这是一个已知但目前不影响 Demo 的边界情况——
  语料扩充的工作流是追加新 id，不是原地编辑，实际触发概率很低。

---

## 五、数据与评估（最容易被问穿的一块，必须准备扎实）

### 语料

- 200+ 条结构化增长实验案例，字段见 `packages/corpus/SCHEMA.md`
- 来源：GoodUI 公开 A/B 案例库、ABtestguide、GrowthHackers 社区复盘、Kaggle Marketing A/B Testing 数据集（CC0），
  以及**我自己三段实习的脱敏实验记录**
- **主动说这一句**：「其中有 20~40 条是我自己在做 SEO 站群和海外冷启动时的真实实验记录，脱敏后结构化进来的。
  这部分是这个语料库跟网上抄一份最不一样的地方。」

### 评测设计

| 指标 | 怎么测 | 说明 |
|---|---|---|
| opportunity 检出准确率 | 合成漏斗，已知最大流失点，看是否命中 | ✅ Baseline 套件 |
| 预算约束捕获率 / 误报率 | 故意生成超预算方案 + 精确到分的边界用例 | ✅ Baseline + Adversarial 套件 |
| 数字幻觉捕获率 | 篡改 opportunity 引用的漏斗数字，看是否被识破 | ✅ Baseline 套件 |
| **对抗性边界用例（7类28例）** | 精确预算边界、增长包装成流失、幽灵环节引用、1%级数字漂移等 | ✅ Adversarial 套件，见 [EVALUATION.md](EVALUATION.md) |
| 模拟方向准确率 | 只看方向对不对，不看数值 | ✅ 已有，但要诚实说明这个指标接近重言式（见 EVALUATION.md） |
| **检索 recall@k / MRR** | 20 题标注集（8 条语料，规模会随语料增长） | ✅ 已完成，见 [EVALUATION.md](EVALUATION.md) |
| **工具调用成功率 / P95 延迟 / 单次成本** | Langfuse trace 统计 | ✅ 已完成，18 个 observation/请求，见下方 |

### 检索质量消融实验（真实数据，已完成）

| 配置 | MRR | recall@1 | recall@3 | recall@5 |
|---|---|---|---|---|
| Mock embed + Mock rerank | 0.863 | 0.75 | 0.95 | 1.00 |
| 真实 embed + Mock rerank | 0.942 | 0.90 | 1.00 | 1.00 |
| 真实 embed + 真实 rerank | 0.900 | 0.90 | 0.90 | 0.90 |

**这张表最有价值的不是数字，是"加了重排反而更低"这个反直觉结果背后的诊断**——查了每条掉分记录后
发现重排器其实把正确答案排到了第一名，真正的问题是 CRAG 置信度分级阈值对"排对了但用词抽象/带行话"
的 query 过于保守，直接判成 wrong 就不返回任何 citation 了。完整排查过程见 EVALUATION.md。

### report.json 从"全 1.0 无信息量"到"全 1.0 但含金量不一样"

**之前的问题不是分数低不低，是测试用例和被测代码来自同一个合成脚本，自己考自己。** 重做评测时没有
简单地"加几条用例把分数打下来"，而是**逐行读 `critic_agent.py` 的判断逻辑，针对每一处边界条件设计
用例**（预算恰好等于上限、超 1 分钱、增长包装成流失、幽灵环节引用……），这个过程里：

- **真的找到并修复了两个 bug**：Critic 不验证"流失"是否真的是流失（净增长可以被包装成机会点通过审核）；
  引用不存在环节名时会直接抛 `TypeError` 崩溃，而不是报告一个问题
- 修复之后 Adversarial 套件确实是 1.0——但这个 1.0 是"28 个边界用例，包括故意在边界两侧各设一个的
  精确对照组，全部按预期通过"，跟"自己造数据自己测"的 1.0 不是一回事

**面试话术**：「这五个指标现在还是 1.0，但含金量不一样了。之前的问题不是分数，是测试设计——用例和
被测代码同源。我这次重做时不是加几条用例把分数打低看起来更真实，而是去读 Critic 的判断逻辑，
针对每一处边界条件构造用例，这个过程真的抓到了两个 bug：一个是它不验证流失是不是真的在流失，
一个是遇到幽灵环节引用会直接崩溃而不是报错。修完之后再测，1.0 才是有意义的。」

---

## 六、高频追问与应答

### 关于 RAG

**Q：为什么不直接把所有案例塞进 prompt？200 条也不多。**
A：三个原因。①上下文成本——200 条案例约 8 万 token，每次调用成本和延迟都不可接受；
②「大海捞针」问题——长上下文里模型对中间部分的注意力会显著衰减；
③可扩展性——语料是要持续增长的，`memory` 表每次实验都会写入新记录，塞不下。
不过你说得对，在语料只有几十条的早期，全塞进去确实是更简单且效果更好的方案，RAG 是为了规模化。

**Q：CRAG 分级判定为 Wrong 的时候你怎么处理？**
A：分三档。Correct 直接用；Ambiguous 触发查询重写再检索一轮；
Wrong 则**明确降级——不注入任何案例，并在输出里标注"本次未找到可参考的历史案例，以下方案基于通用增长框架生成"**。
我认为宁可承认没有依据，也不能拿不相关的案例误导使用者。

**Q：中文 embedding 你怎么选的？**
A：用的 bge-small-zh-v1.5，本地跑。选它有两个考虑：一是零成本且数据不出境，
这对企业客户是刚需；二是小模型（~100MB）冷启动快，部署在免费额度的云平台上跑得动。
我也测过 DashScope 的 text-embedding-v3，效果略好但引入了 API 依赖和成本，
在我这个量级上不值得。**如果语料涨到万级，我会重新评估。**

**Q：chunking 策略？**
A：我的语料是结构化 JSONL，每条案例本身就是一个天然的语义单元，所以**不做二次切分，一条案例一个 chunk**。
这是结构化语料相比非结构化文档的优势。如果后面要接入非结构化的行业报告 PDF，才需要引入递归或语义分块。

### 关于 Agent 架构

**Q：为什么不用 LangGraph / AutoGen / CrewAI？**
A：早期我评估过。不用的原因是这个项目的编排逻辑是**固定顺序的流水线加一个 Reflect 回环**，
用框架反而多一层抽象，调试时要穿透框架看状态。自己写 orchestrator 只有 130 行，完全可控。
**但我知道这个选择的边界在哪**——一旦需要动态重规划、并行子 Agent、或者复杂的条件分支，
手写会迅速失控，那时候我会迁移到 LangGraph。我看过 ByteDance DeerFlow 2.0 的实现，
它就是基于 LangGraph 做的 sandbox + memory + skills + 子 Agent 编排，是我下一步的参考。

**Q：Reflect 只重试一次（MAX_RETRIES=1），为什么？**
A：因为当前的 Reflect 实现是确定性的预算 clamp，重试第二次不会有新信息，纯属浪费。
**这其实是一个我知道的简化**——真正的 Reflect 应该把 Critic 的 issues 反馈给 experiment_agent 让它重新生成，
那种情况下多轮重试才有意义。改成 LLM 驱动的重生成之后，我会把上限提到 3 并加一个收敛判断。

**Q：五个 Agent 之间怎么传状态？**
A：纯函数式——每个 Agent 是无状态函数，接收上一步的输出作为参数，返回结构化 dict，
由 orchestrator 串联，全部状态最终落到 `runs` 表的各个 json 字段里。
好处是每一步的中间产物都可以单独回放和评测；代价是没有共享的可变工作区，
Agent 之间无法协商——这也是 *Code as Agent Harness* 里提到的多 Agent 状态一致性问题。

**Q：这个 harness 和 Claude Code / OpenCode 这类 coding agent harness 有什么区别？**
A：coding agent 的 harness 核心是**代码执行环境**——文件系统、终端、沙箱、测试反馈回环，
它的 verification 是"跑一下测试就知道对不对"，反馈信号强且免费。
我这个业务 Agent 的 verification 信号是稀疏且昂贵的——一个增长实验要两周才能知道结果。
所以我的设计重心不在执行环境，而在**执行前的多重把关**：Critic 规则校验 + 模拟预筛 + 人工审批三道闸。
这是 *Code as Agent Harness* 综述里明确提出的开放问题之一：incomplete feedback 下的 verification。

### 关于工程

**Q：并发怎么处理？SQLite 顶得住吗？**
A：顶不住，这是明确的短板。SQLite 单写锁，当前是单用户 Demo 场景所以没问题。
生产化第一件事就是换 Postgres——`db.py` 里所有查询都是标准 SQL，迁移成本很低。
另外 `data_agent.gather()` 现在是串行调四个工具，改成 `asyncio.gather` 能省一半延迟，这个我还没做。

**Q：LLM 调用失败怎么办？**
A：`app/llm/` 里做了多供应商抽象，主力 DeepSeek、降级 GLM-4-Flash。
**但说实话，当前的 fallback 还只是配置层面可切换，没有做自动重试和熔断，这是待补的。**

**Q：成本大概多少？**
A：单次完整 run 大约 3–5 次 LLM 调用，DeepSeek 价格下约 ¥0.01–0.03。
Embedding/rerank 走 SiliconFlow 免费模型零成本。这不是估算，Langfuse trace 里能直接看到——
接上之后发现单次请求 7.96 秒里，两次 RAG 检索占了 85% 以上，这个数字比"成本大概多少"更早被我注意到。

**Q：为什么两次检索是串行的，不并行？**
A：这是 Langfuse trace 帮我发现的问题，还没优化——`opportunity_agent` 和 `experiment_agent`
各自独立调用 `retriever.search()`，目前是顺序执行。下一步会改成 `asyncio.gather` 并行发起，
或者给 embedding 结果按 query 文本加缓存（同一批 Demo 数据里 `to_step` 只有几种取值，缓存命中率会很高）。
我现在的判断优先级是先把这个改掉，因为它是 trace 数据显示的最大单项耗时来源。

### 关于你本人

**Q：你不是计算机专业的，这个项目是你自己写的吗？**
A：是我自己设计和实现的，AI 编码工具帮了很多忙——**这恰恰是我想强调的能力**。
我的三段实习都在做同一件事：把重复的运营流程变成自动化系统。
在中文在线我用 Coze 给 100 多人的团队搭工作流和 RAG，在 Ancher.ai 用 Codex 搭邮件外联流水线，
在易娱做 SEO 站群自动化。这些都是无代码/低代码方案，**能跑但不可控、不可测、不可交付给别人**。
GrowthPilot 是我把同一套业务理解重新用工程方式实现一遍：有分层、有抽象、有评测、有可观测性。
**我的差异化不是算法，是我真的知道运营团队在什么环节会痛、什么方案会被业务方拒绝。**

**Q：这个项目最难的部分是什么？**
A：不是代码，是**决定哪些事不让 Agent 做**。
一开始我想做全自动——Agent 发现机会、生成实验、直接改线上配置。
写到一半我意识到这在真实企业里根本不可能被接受：没有哪个增长负责人敢让 AI 直接动预算和线上表单。
所以我把整个架构从"自动执行"改成了"生成 + 校验 + 模拟 + 人工审批"，
这个改动砍掉了项目最炫的部分，但让它变成了一个真的可能上线的东西。

---

## 七、已知短板清单（主动说出来，不要等被挖出来）

准备一句开场：**「这个项目有几个我明确知道的短板，我先说一下。」** 然后挑 2–3 条讲。

| 短板 | 现状 | 我的计划 |
|---|---|---|
| **对抗用例非穷举** | 已加 28 例边界测试并修了 2 个真 bug，但只覆盖读代码时能想到的边界（如只测了 `to_step` 缺失，没测 `from_step` 缺失） | 继续按同样方法论补类别，见 EVALUATION.md |
| **检索测试集规模小** | 20 题对 8 条语料，CRAG 分级阈值只在小样本上验证过 | 语料补到 80-100 条时重新生成 50 题测试集，重新校准阈值 |
| **Reflect 在当前确定性链路里结构性不可达** | `experiment_agent` 生成时预算已 clamp，Critic 唯一能拦的场景永远不会真的发生（Phase 4 读代码才发现，见 HARNESS_DESIGN.md） | 保留作防御性设计，未来 experiment_agent 变 LLM 驱动时才会真正生效 |
| **Mock 与 Real 无契约测试** | 仅靠抽象基类约束签名 | 加一组接口契约测试 |
| **SQLite 单机** | 无并发写 | 迁 Postgres，接口已隔离 |
| **串行工具调用** | `data_agent.gather()` 四个工具串行 | 改 asyncio 并发（当前量级下影响很小，见下一条的教训——先分析依赖关系再决定要不要做） |
| ~~两次 RAG 检索串行，占单次请求 85%+ 耗时~~ | **✅ Phase 4 已修复**——原计划的 `asyncio.gather` 并行化经分析后发现两次检索是真数据依赖，行不通；改用 embedding/rerank 进程级缓存，实测 6.359s→0.056s（检索部分，-99.1%） | — |
| **无 LLM 熔断重试** | 只有配置层 fallback | 加指数退避 + 熔断 |
| **固定流水线编排** | 无法动态重规划 | 复杂场景迁 LangGraph |
| **真实 CRM/ERP 未接** | 个人拿不到企业授权 | 用飞书多维表格模拟，架构可插拔 |

---

## 八、和简历三段实习的呼应（面试官一定会串起来问）

把 GrowthPilot 讲成**你实习经历的技术化收敛**，而不是一个孤立的课程作业：

| 实习 | 做了什么 | 在 GrowthPilot 里对应什么 |
|---|---|---|
| **中文在线** | Coze 搭爆款前贴视频 Agent + 口播视频 RAG（原片解析 / 风格检索 / 提示词拼装） | **第 2 层 RAG 检索层**——同一套"检索相似案例 → 带引用组装 prompt"的思路，从 Coze 无代码重写成了可测可控的工程实现 |
| **Ancher.ai** | 微信公众号 5 账号自动运营 Agent；Codex 搭 125 封个性化冷启动邮件流水线，重复/无效/跳过均为 0 | **第 1 层工具接入 + 第 8 层评估**——"重复/无效/跳过均为 0"就是最朴素的评测意识，GrowthPilot 把它系统化成了 eval harness |
| **易娱** | SEO 站群自动化，25 个分站单批次发布，主站/分站内容分流策略 | **第 5 层 Memory + 第 6 层模拟**——分流策略本质就是"基于历史效果做优先级排序" |
| **丰疆智能** | FieldFusion V3.0 PRD、官网重构 | **第 7 层审批与写回**——知道 B 端产品必须有人工确认环节，是产品经历给的直觉 |

**收口话术**：
> 我前面做的都是"能跑但只有我能维护"的自动化。GrowthPilot 是我把同样的业务理解，
> 用有分层、有抽象、有评测、有可观测性的方式重做一遍。
> 我的目标不是证明我算法多强，而是证明我能把一个真实的业务流程，工程化成一个别人也能接手、能扩展、能上线的系统。

---

## 九、面试前 10 分钟检查清单

- [ ] Zeabur Demo 链接能打开
- [ ] Claude Desktop 里 MCP Server 连接正常，随手调一次 `search_growth_playbook`
- [ ] Langfuse 面板登录着，能展开一条完整 trace
- [ ] GitHub 仓库 README 顶部 GIF 能正常播放
- [ ] `docs/EVALUATION.md` 的消融表打开备用
- [ ] Dashboard 左侧三个预置目标按钮试点一遍（创作者注册转化率 / 落地页注册率 / 邀请好友转化率），现场不用现打字
- [ ] 短板清单挑好今天要主动讲的 2 条
