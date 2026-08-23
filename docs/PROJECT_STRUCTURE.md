# GrowthPilot 项目结构

> 标注约定：`[已实现]` = 当前代码库里真实存在且能跑；`[Phase N]` = 计划新增，见 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)。
> 面试时只讲 `[已实现]`，被问到规划再讲 `[Phase N]`。**不要把规划当成果讲。**

## 一、当前真实结构（截至 Phase 0）

```
GrowthOps Agent/
├── apps/
│   └── agent-service/                    # FastAPI 单体后端 + 内置 Dashboard
│       ├── requirements.txt              # fastapi / uvicorn / jinja2 / httpx / dotenv
│       ├── .env.example                  # 所有外部系统密钥占位
│       ├── growthpilot.db                # SQLite（.gitignore，不入库）
│       └── app/
│           ├── main.py                   # FastAPI 入口：Dashboard 路由 + REST API
│           ├── config.py                 # 环境变量读取、DB 路径
│           ├── db.py                     # SQLite schema：runs / memory / notifications
│           ├── agents/                   # 5 个专职 Agent（无状态纯函数）
│           │   ├── research_agent.py     # 自然语言目标 → 结构化 goal
│           │   ├── data_agent.py         # 调工具取数、聚合成漏斗
│           │   ├── opportunity_agent.py  # 漏斗 → 最大流失环节
│           │   ├── experiment_agent.py   # 机会点 → A/B 实验方案
│           │   └── critic_agent.py       # 独立校验：预算约束 + 数字幻觉
│           ├── planner/
│           │   └── orchestrator.py       # 主循环：Plan→Tool→Verify→Reflect→审批→写回
│           ├── simulation/
│           │   └── simulator.py          # Persona 模拟，实验前预测方向与置信度
│           ├── llm/                      # 双实现：MockLLM / OpenAICompatibleLLM
│           │   ├── base.py               # 抽象接口
│           │   └── __init__.py           # get_llm() 工厂，按 .env 自动切换
│           ├── rag/                      # ✅ 检索增强层（Phase 1 已完成）
│           │   ├── embedder.py           #   三档：MockEmbedder / SiliconFlowEmbedder(bge-m3 API) / BgeEmbedder(本地)
│           │   ├── reranker.py           #   三档：MockReranker / SiliconFlowReranker / BgeReranker(本地交叉编码器)
│           │   ├── store.py              #   LanceDB 封装：建表/重建/混合检索(向量+FTS, RRF融合)
│           │   ├── ingest.py             #   CLI：读 corpus jsonl → embed → 分词 → 建索引
│           │   ├── retriever.py          #   编排：混合检索→重排→CRAG分级(correct/ambiguous/wrong)→降级兜底，@observe(as_type="retriever")
│           │   └── citations.py          #   格式化成 prompt 文本块 + 结构化引用列表
│           ├── obs/                      # ✅ 可观测层（Phase 3 已完成）
│           │   └── tracing.py            #   flush() 封装；@observe 直接在各 agents/tools/llm/rag 文件里用
│           ├── tools/                    # 6 个外部系统工具，Mock/Real 双实现
│           │   ├── base.py               # 工具抽象基类
│           │   ├── analytics_tool.py     # 埋点行为数据
│           │   ├── form_tool.py          # 表单 Lead 采集 + 字段写回
│           │   ├── crm_tool.py           # 商机/客户/标签读写
│           │   ├── erp_tool.py           # 订单/库存
│           │   ├── feishu_tool.py        # 审批实例 + 机器人消息
│           │   └── wecom_tool.py         # 企业微信消息推送
│           ├── templates/index.html      # Dashboard 页面
│           └── static/                   # app.js / style.css
│
├── packages/
│   ├── eval/
│   │   ├── generate_synthetic_data.py    # 合成 Digital Marketing Performance 风格数据（装饰性，当前评测未消费它，见下方说明）
│   │   ├── benchmarks.py                 # ✅ Critic Baseline(60) + Adversarial(28) 双套件，输出 report.json
│   │   ├── retrieval_eval.py             # ✅ Phase 3：RAG 检索质量消融（Mock/真实embed/真实embed+rerank），输出 retrieval_report.json
│   │   ├── datasets/
│   │   ├── report.json                   # 最近一次 Critic 评测结果
│   │   └── retrieval_report.json         # 最近一次检索消融结果
│   └── corpus/                           # 增长案例语料（RAG 的原始素材）
│       ├── SCHEMA.md                     #   语料字段定义
│       ├── curated/seed_cases.jsonl      #   8 条已核实种子语料（HubSpot/Bing/Google/Obama/Airbnb/Dropbox/Netflix/Expedia）
│       └── raw/                          #   待转录的原始案例草稿（空，按需追加）
│
├── docs/
│   ├── PROJECT_STRUCTURE.md              # 本文件
│   ├── CORPUS_SOURCES.md                 # 语料/数据集来源链接清单（全部已核实）
│   ├── TECH_STACK.md                     # 技术选型记录，含真实 A/B 测试数据和踩坑记录
│   ├── EVALUATION.md                     # ✅ Phase 3：评测方法论、结果、发现并修复的真实 bug
│   ├── HARNESS_DESIGN.md                 # ✅ Phase 4：三层 harness 架构对齐论文 + Reflect 结构性不可达的发现
│   ├── DEVELOPMENT_PLAN.md               # 分阶段路线图
│   ├── API_AND_MATERIALS.md              # API 申请清单 + 物料清单
│   └── INTERVIEW_GUIDE.md                # 面试讲解稿
│
├── apps/mcp-server/                      # ✅ MCP 暴露层（Phase 2 已完成）
│   ├── README.md                         #   工具清单、设计边界、独立venv/HTTP transport的原因
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── run.bat                           #   本地启动（HTTP，默认端口 8210）
│   └── src/growthpilot_mcp/
│       ├── __main__.py                   #   python -m growthpilot_mcp 的入口（见下方踩坑记录）
│       ├── _bootstrap.py                 #   sys.path 注入，import agent-service 的 app 包
│       ├── server.py                     #   FastMCP 实例 + HTTP transport 启动
│       └── tools/
│           ├── playbook.py               #   search_growth_playbook
│           ├── data.py                   #   fetch_growth_data
│           └── experiment.py             #   propose_experiment / get_experiment_status（无 decide）
│
└── README.md
```

### 关键设计：Mock / Real 双实现工厂

每个外部系统都是 `get_xxx_tool()` 工厂函数，读 `.env` 决定返回 `MockXxxTool` 还是 `RealXxxTool`。
Agent 代码永远只面向抽象接口编程，**接不接真实系统，业务代码一行都不用改**。
这是整个项目最值得讲的工程决策之一，详见 [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) 决策 #2。

---

## 二、Phase 0–4 完成情况 vs. 最初规划

Phase 1–4 基本都做完了，但**不是每一项都完全按最初写的样子实现**——这本身就是诚实记录的一部分：

| 最初计划 | 实际情况 |
|---|---|
| `packages/eval/retrieval_testset.jsonl` + `ablation.py` | 实现为 `retrieval_eval.py` 里内联的 `TESTSET` 常量 + 输出 `retrieval_report.json`，没有拆成独立文件——20 题规模下拆文件是过度设计 |
| `app/skills/`（Markdown 增长打法） | **没做**。`experiment_agent` 现在是规则驱动，没有任何代码会读取 skill 文件，加了也是没人用的装饰性文件。见 [HARNESS_DESIGN.md](HARNESS_DESIGN.md) 第五节 |
| `HARNESS_DESIGN.md` | ✅ 已完成，但结论跟最初设想不同——文档核心发现是"Reflect 循环在当前确定性链路里结构性不可达"，而不是简单地把代码映射到论文框架 |

## Phase 5 进度

| 项 | 状态 |
|---|---|
| 架构图 | ✅ Mermaid，直接内嵌 README（GitHub 原生渲染，不用维护单独的 svg 文件） |
| Demo GIF | ✅ `assets/demo.gif`，Playwright 驱动真实浏览器录制（不是截图拼接），10 帧完整走一遍目标输入→RAG 检索引用→Critic→模拟→审批→案例库 |
| 一个顺带修复的 UI 缺口 | 录 GIF 时发现 `app.js` 从来没渲染过 `opportunity.citations`/`experiment.citations`——RAG 检索结果一直只在叙述文本里带一句摘要，没有结构化展示。加了 `citationsBlock()`，现在能看到可点击跳转真实来源的引用卡片 |
| 部署配置 | ✅ `Procfile` / `.python-version` / `docs/DEPLOYMENT.md`；自动在 startup 建 LanceDB 索引（`app/main.py`，容器重启不需要手动 ingest） |
| Zeabur 实际部署 | 🔨 进行中 |

---

## 三、分层职责一览

| # | 层 | 目录 | 职责 | 状态 |
|---|---|---|---|---|
| 1 | 工具/数据接入层 | `app/tools/` | 6 个外部系统统一封装成可调用工具，Mock/Real 可插拔 | ✅ 已实现 |
| 2 | 检索增强层 | `app/rag/`（管线）/ `packages/corpus/`（语料） | 历史实验与公开增长案例的混合检索，为假设生成提供事实依据 | ✅ **已实现**（语料 8 条种子，管线 Mock/SiliconFlow/本地 bge 三档，已接入 opportunity_agent + experiment_agent） |
| 3 | MCP 暴露层 | `apps/mcp-server/` | 把工具层与检索层暴露为标准 MCP 工具，任意 MCP 客户端可直连；决策层动作（审批/写回）刻意不暴露 | ✅ 已实现（HTTP transport，独立 venv，见其 README） |
| 4 | Agent 核心层 | `app/agents/`, `app/planner/` | 5 个专职 Agent + Plan→Tool→Verify→Reflect 主循环 | ✅ 已实现，但 Verify→Reflect 在当前确定性生成逻辑下结构性不可达，见 [HARNESS_DESIGN.md](HARNESS_DESIGN.md) |
| 5 | 记忆层 | `db.py` 的 `memory` 表 | 结构化存 hypothesis/channel/result/confidence/lesson，避免全上下文塞 Prompt | ✅ 已实现（SQLite） |
| 6 | 模拟层 | `app/simulation/` | Persona 模拟预测实验方向与置信度，做优先级排序 | ✅ 已实现 |
| 7 | 审批与写回层 | `orchestrator.decide()` + `feishu_tool` / `wecom_tool` | 审批卡片 → 人工确认 → 写回表单/CRM → IM 通知 | ✅ 已实现 |
| 8 | 评估层 | `packages/eval/` | Critic Baseline+Adversarial 双套件（找到并修复 2 个真实 bug）+ 检索质量消融 | ✅ 已实现，见 [EVALUATION.md](EVALUATION.md) |
| 9 | 可观测层 | `app/obs/` | Langfuse 全链路 tracing：18 个 observation/请求，语义化类型(agent/tool/retriever/generation/guardrail) | ✅ 已实现，见 [TECH_STACK.md](TECH_STACK.md) 里接上当天发现的真实延迟问题 |
| 10 | Harness 架构文档 | `docs/HARNESS_DESIGN.md` | 三层框架（Interface/Mechanism/Scaling）对齐 *Code as Agent Harness* 论文，含 Reflect 结构性不可达的诚实发现 | ✅ 已实现（Phase 4） |

---

## 四、一次完整请求的调用链

```
POST /runs  { goal_text, budget_limit }
      │
      ▼
orchestrator.run_goal()
      │
      ├─ research_agent.extract_goal(goal_text)        自然语言 → {metric_name, target}
      ├─ data_agent.gather(metric_name, tools)         串行调 analytics/form/crm/erp → 漏斗（已知待优化项，见 INTERVIEW_GUIDE.md 短板清单）
      ├─ opportunity_agent.find_opportunity(raw, llm)  定位最大流失环节
      │      └─ rag.retriever.search()                 检索相似历史案例，带引用注入 prompt（embed/rerank 带进程级缓存，命中时 <0.05s）
      ├─ experiment_agent.design_experiment(...)       生成 A/B 方案 + 预算（proposed_budget 生成时已 clamp 到上限）
      │      └─ rag.retriever.search()                 同上，检索命中同一个进程级缓存
      ├─ critic_agent.review(...)                      ◄── 独立校验：预算 / 数字幻觉 / 流失方向
      │      └─ 不通过 → Reflect 回环重试（MAX_RETRIES=1，当前确定性链路下结构性不可达，见 HARNESS_DESIGN.md）
      ├─ simulator.run(run_id, ...)                    Persona 模拟 → summary + confidence
      ├─ feishu.create_approval() + send_message()     生成审批卡片，推送给审批人
      └─ INSERT INTO runs (status = pending_approval)
      │
      ▼  ——————— 人工审批边界（Agent 到此为止，绝不自动执行）———————
      │
POST /runs/{id}/decide  { decision }
      │
      ▼
orchestrator.decide()
      ├─ approved → form.update_fields() 或 crm.update_tag()   写回原系统
      │             wecom.send_message()                        通知执行结果
      ├─ rejected → 仅记录
      └─ INSERT INTO memory (hypothesis, channel, result, confidence, lesson)
```

**这条链路是面试讲解的主干**，把它背熟，任何架构问题都可以拉回到这条链上回答。
