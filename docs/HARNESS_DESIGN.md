# Harness 设计：对齐 Code as Agent Harness 框架

> 这份文档做两件事：把 GrowthPilot 已有的架构映射到 *Code as Agent Harness*
> （arXiv 2605.18747）提出的三层框架（Interface / Mechanism / Scaling），
> 并诚实地写清楚映射里站不住脚的部分——**不是把现有代码换个名字包装成论文架构**，
> 是先验证哪些地方真的有三层 harness 的实质，哪些只是线性流水线，再决定要不要动代码。

## 一、三层映射

| 论文层次 | GrowthPilot 对应 | 代码位置 |
|---|---|---|
| **Interface**（代码/工具接口） | 工具抽象基类统一了 6 个外部系统的调用契约；MCP Server 把检索与生成能力暴露成标准 schema | `app/tools/base.py`（`AnalyticsTool`/`FormTool`/`CRMTool`/`ERPTool`/`IMTool`），`apps/mcp-server/` |
| **Mechanism**（规划/记忆/工具使用/迭代调试） | 见下方逐项展开 | `app/planner/orchestrator.py`, `app/db.py`, `app/rag/`, `app/agents/critic_agent.py` |
| **Scaling**（多智能体角色分化 + human oversight） | 5 个专职 Agent 角色分化 + 人工审批作为强制边界 | `app/agents/*.py`, `orchestrator.decide()` |

### Mechanism 层逐项对照

| 论文概念 | GrowthPilot 实现 | 成熟度 |
|---|---|---|
| Planning | `orchestrator.run_goal()` 的固定顺序流水线：Plan(research)→Tool Call(data)→Act(opportunity/experiment)→Verify(critic)→Reflect | 有，但是**静态**编排（无动态重规划能力），见下方决策 |
| Memory | `memory` 表存结构化字段（hypothesis/channel/result/confidence/lesson），供未来检索复用 | 有，结构化字段而非对话原文 |
| Tool use | `app/tools/*` 六个外部系统 + RAG 检索作为"知识工具" | 有 |
| Iterative debugging（验证驱动的迭代修复） | Critic 校验 + Reflect 重试循环（`MAX_RETRIES=1`） | **有实现，但在当前确定性链路里结构性不可达——见下方「诚实的发现」** |

## 二、诚实的发现：Reflect 循环在真实链路里永远不会触发

写这份文档时重新读了一遍 `orchestrator.py` 和 `experiment_agent.py` 的实际逻辑，发现一个此前没意识到的事实：

```python
# experiment_agent.py
proposed_budget = min(budget_limit, 8000.0)   # 表单精简分支
proposed_budget = min(budget_limit, 5000.0)   # 预算倾斜分支
```

**`proposed_budget` 在生成的那一刻就已经是 `min(budget_limit, 常数)`**——预算永远不可能超过上限。
而 `orchestrator.run_goal()` 里的 Reflect 循环：

```python
while not critic["passed"] and retries < MAX_RETRIES:
    experiment["proposed_budget"] = min(experiment["proposed_budget"], budget_limit)
    critic = critic_agent.review(opportunity, experiment, raw_data, budget_limit)
    retries += 1
```

这段代码要生效，前提是 Critic 第一次校验就没通过——但 Critic 唯一会因为预算而拦截的场景
（`proposed_budget > budget_limit`），在 `experiment_agent` 已经提前 clamp 的情况下**根本不会发生**。
同理，`opportunity_agent` 只从真实漏斗数据里算最大流失点，永远不会声称一个不存在的环节，
也永远不会把净增长包装成流失——Phase 3 对抗测试里能测出 `growth_framed_as_drop`、
`phantom_step_reference` 这些场景，靠的是**手工构造违反规则的 dict 直接喂给 `critic_agent.review()`**，
绕过了 `opportunity_agent`/`experiment_agent` 的正常生成路径。

**结论**：在当前全确定性的生成逻辑下，Critic 和 Reflect 是**防御性架构**，不是**当前必经路径**——
它们防的是一个还不存在的风险：**如果未来 `experiment_agent` 变成 LLM 驱动的生成（而不是规则计算)，
这些校验才会在真实流量里被触发**。这跟论文里"迭代调试"设想的"生成→验证→修复"循环有本质区别：
论文假设生成本身有不确定性，GrowthPilot 现在的生成没有不确定性，所以循环有名无实。

### 面试话术

> 「我重新读代码的时候发现，Critic 和 Reflect 在我现在的确定性生成逻辑下其实永远不会真的触发——
> `experiment_agent` 生成预算的时候已经提前 clamp 到上限了。我没有把这个模块删掉，因为它是给未来
> `experiment_agent` 变成 LLM 驱动生成之后留的安全网，而且 Phase 3 的对抗测试已经覆盖了它——
> 但我会诚实地说，这是防御性设计，不是当前真的在生效的机制。这也是我读了 Code as Agent Harness
> 这篇论文之后回头看自己代码才想清楚的一点：迭代调试这个机制的价值取决于生成本身有没有不确定性。」

## 三、Scaling 层：多 Agent 角色分化 + human oversight

已经在 [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) 决策 #5 和 #1 里详细写过，这里不重复。
核心结论没变：5 个 Agent 各自窄而深，Critic 独立于生成方，审批是唯一不能被任何接口
（包括 MCP）绕过的边界。

## 四、Phase 4 真正做的代码改动：把 Phase 3 发现的性能问题修掉

Phase 3 接上 Langfuse 后发现单次请求 7.96 秒里，两次 RAG 检索占了 85%+。分析后发现
`opportunity_agent` 和 `experiment_agent` 的两次检索**不能并行**——experiment 的检索
依赖 opportunity 的输出，是真正的串行依赖，`asyncio.gather` 用不上。

真正能优化的地方：这批 Demo 数据是按 `metric_name` 确定性播种生成的，同一个目标反复跑，
检索 query 文本完全一致。给 `SiliconFlowEmbedder.embed_query()` 和 `SiliconFlowReranker.rerank()`
加了进程级缓存（模块级 dict，key 分别是 `(model, text)` 和 `(model, query, top_k, 候选id集合)`）。

### 实测效果

| | 耗时 | 说明 |
|---|---|---|
| 冷启动（首次查询） | 5.416s | 走真实 embed + rerank API |
| 缓存命中（重复查询） | 0.032s | **降低 99.4%** |

拆解缓存命中后的 0.032s 花在哪：

| 步骤 | 耗时 |
|---|---|
| `embed_query`（缓存命中） | 0.0000s |
| jieba 分词 | 0.0000s |
| LanceDB 混合检索 | 0.0299s |
| `rerank`（缓存命中） | 0.0000s |

### 端到端验证（不只是孤立测试单个函数）

上面这组数字是直接调 `retriever.search()` 测出来的，为了排除"孤立测试不代表真实请求"的疑虑，
又把同一个目标通过真实 `/api/run` 连续调了两次，然后用 Langfuse REST API 拉取这两次请求的
真实 trace 做对比（不是本地掐表）：

| | HTTP 请求总耗时 | Trace 里两次 RETRIEVER span 总和 |
|---|---|---|
| 第一次（冷启动） | 9.370s | 6.359s |
| 第二次（缓存命中） | 1.515s | **0.056s** |

请求总耗时降了 84%，RAG 检索部分单独看降了 **99.1%**——跟孤立测试的 99.4% 基本吻合，
证明这不是测试环境的假象。

**一个附带发现**：第一次测的时候直接写脚本调 `retriever.search()`，没有先 `import app.config`
触发 `.env` 加载，Langfuse 客户端在无密钥的降级状态下跑出了 1.36 秒的"缓存命中但还是慢"的假象——
排查后发现是 Langfuse 未认证客户端本身的开销，跟检索缓存无关。补上 `import app.config` 之后
缓存命中直接降到 0.032s。**这也是一个值得记的教训**：任何要单独调用 `@observe` 装饰过的函数做
基准测试的脚本，都要确保 `.env` 先被加载，否则测出来的数字包含了一段跟被测逻辑无关的噪音。

### 为什么不缓存 Mock/本地 bge

`MockEmbedder`/`MockReranker` 本来就是纯内存计算，零网络开销，加缓存没有意义；`BgeEmbedder`/
`BgeReranker` 是本地推理，延迟来自 CPU 前向计算而不是网络往返，缓存能省的时间有限，
且模型常驻内存后重复调用本身已经很快。只给 SiliconFlow 这两个真实走网络的实现加缓存，
是刻意的取舍，不是漏掉。

## 五、Phase 4 明确没做的两件事（及原因）

**没有重构 `orchestrator.py` 的内部结构。** 最初计划是把它拆成显式的 `_plan()`/`_verify_reflect()`
等具名函数来"更像 harness"。写这份文档时发现没必要：每个真正的处理步骤已经是 `app/agents/*.py`
里独立的、被 `@observe` 单独打点的函数，`orchestrator.run_goal()` 本身只是把它们按顺序串起来。
再拆一层只是把同一段逻辑挪个位置、换个函数名，不会让架构变得更清晰，反而是"为了看起来像论文
架构而重构"的反面教材。**结构本来就在，这次只是第一次把它跟论文的词汇对应着讲清楚。**

**没有加 `app/skills/` 目录。** 最初计划参考 DeerFlow 2.0 的 skill 设计，加几个 Markdown 定义的
"可复用增长打法"（如 `seo-longtail.md`）。评估后决定不做：现在没有任何代码会读取这些文件——
`experiment_agent` 是规则驱动的，只认两种硬编码的实验类型，Markdown skill 文件加进去只会是
没人用的装饰性文件，违反"不做没有消费者的功能"这条我在整个项目里一直在坚持的原则。
**如果之后要做，前提是先有一个真正会读取 skill 内容的调用点**（比如让 RAG 检索层把 skill
和案例语料一起检索），不是先加文件再找用途。

## 六、参考

- *Code as Agent Harness*（arXiv 2605.18747）——三层框架的来源
- [TECH_STACK.md](TECH_STACK.md) — Phase 1-3 的技术选型与真实 A/B 数据
- [EVALUATION.md](EVALUATION.md) — Critic 对抗测试与检索质量消融
- [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) 决策 #1/#5/#9 — 审批边界、多 Agent 分化、可观测性
