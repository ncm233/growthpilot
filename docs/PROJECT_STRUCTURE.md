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
│           │   ├── retriever.py          #   编排：混合检索→重排→CRAG分级(correct/ambiguous/wrong)→降级兜底
│           │   └── citations.py          #   格式化成 prompt 文本块 + 结构化引用列表
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
│   │   ├── generate_synthetic_data.py    # 合成 Digital Marketing Performance 风格数据
│   │   ├── benchmarks.py                 # 基准测试，输出 report.json
│   │   ├── datasets/
│   │   └── report.json                   # 最近一次评测结果
│   └── corpus/                           # 增长案例语料（RAG 的原始素材，检索管线本身仍是 Phase 1）
│       ├── SCHEMA.md                     #   语料字段定义
│       ├── curated/seed_cases.jsonl      #   8 条已核实种子语料（HubSpot/Bing/Google/Obama/Airbnb/Dropbox/Netflix/Expedia）
│       └── raw/                          #   待转录的原始案例草稿（空，按需追加）
│
├── docs/
│   ├── PROJECT_STRUCTURE.md              # 本文件
│   ├── CORPUS_SOURCES.md                 # 语料/数据集来源链接清单（全部已核实）
│   ├── DEVELOPMENT_PLAN.md               # 分阶段路线图
│   ├── API_AND_MATERIALS.md              # API 申请清单 + 物料清单
│   └── INTERVIEW_GUIDE.md                # 面试讲解稿
│
└── README.md
```

### 关键设计：Mock / Real 双实现工厂

每个外部系统都是 `get_xxx_tool()` 工厂函数，读 `.env` 决定返回 `MockXxxTool` 还是 `RealXxxTool`。
Agent 代码永远只面向抽象接口编程，**接不接真实系统，业务代码一行都不用改**。
这是整个项目最值得讲的工程决策之一，详见 [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) 决策 #2。

---

## 二、目标结构（Phase 1–5 完成后）

```
GrowthOps Agent/
├── apps/
│   ├── agent-service/
│   │   └── app/
│   │       ├── （以上全部保留，含 ✅ rag/，见上方「一」）
│   │       ├── obs/                      # [Phase 3] 可观测性
│   │       │   └── tracing.py            #   Langfuse 装饰器与 span 封装
│   │       └── skills/                   # [Phase 4] Markdown 定义的可复用增长打法
│   │           ├── seo-longtail.md
│   │           └── cold-start-community.md
│   │
│   └── mcp-server/                       # [Phase 2] MCP 暴露层
│       ├── pyproject.toml                #   fastmcp>=2.0.0
│       └── src/growthpilot_mcp/
│           ├── server.py
│           └── tools/
│               ├── playbook.py           #   search_growth_playbook（复用 app/rag）
│               ├── data.py               #   fetch_form_leads / fetch_crm_pipeline
│               └── experiment.py         #   propose_experiment / simulate_experiment
│
├── packages/
│   ├── corpus/                           # 语料原始素材 ✅ 已有 8 条种子；检索管线仍是 [Phase 1]
│   │   ├── raw/                          #   待转录草稿
│   │   ├── curated/                      #   ✅ seed_cases.jsonl（8 条已核实案例）
│   │   └── SCHEMA.md                     #   ✅ 语料字段定义
│   └── eval/
│       ├── （以上保留）
│       ├── retrieval_testset.jsonl       # [Phase 3] 50 题检索标注集
│       └── ablation.py                   # [Phase 3] 四组消融对比
│
├── docs/
│   ├── （以上全部保留）
│   ├── HARNESS_DESIGN.md                 # [Phase 4] 三层 harness 设计，对齐论文
│   └── EVALUATION.md                     # [Phase 3] 评测方法与消融结果
│
└── assets/                               # [Phase 5] 展示物料
    ├── architecture.svg
    ├── demo.gif
    └── langfuse-trace.png
```

---

## 三、分层职责一览

| # | 层 | 目录 | 职责 | 状态 |
|---|---|---|---|---|
| 1 | 工具/数据接入层 | `app/tools/` | 6 个外部系统统一封装成可调用工具，Mock/Real 可插拔 | ✅ 已实现 |
| 2 | 检索增强层 | `app/rag/`（管线）/ `packages/corpus/`（语料） | 历史实验与公开增长案例的混合检索，为假设生成提供事实依据 | ✅ **已实现**（语料 8 条种子，管线 Mock/SiliconFlow/本地 bge 三档，已接入 opportunity_agent + experiment_agent） |
| 3 | MCP 暴露层 | `apps/mcp-server/` | 把工具层与检索层暴露为标准 MCP 工具，任意 MCP 客户端可直连 | 🔨 Phase 2 |
| 4 | Agent 核心层 | `app/agents/`, `app/planner/` | 5 个专职 Agent + Plan→Tool→Verify→Reflect 主循环 | ✅ 已实现 |
| 5 | 记忆层 | `db.py` 的 `memory` 表 | 结构化存 hypothesis/channel/result/confidence/lesson，避免全上下文塞 Prompt | ✅ 已实现（SQLite） |
| 6 | 模拟层 | `app/simulation/` | Persona 模拟预测实验方向与置信度，做优先级排序 | ✅ 已实现 |
| 7 | 审批与写回层 | `orchestrator.decide()` + `feishu_tool` / `wecom_tool` | 审批卡片 → 人工确认 → 写回表单/CRM → IM 通知 | ✅ 已实现 |
| 8 | 评估层 | `packages/eval/` | 验证不编造指标、不违反预算约束；Phase 3 增加检索评测与消融 | ✅ 已实现，🔨 Phase 3 强化 |
| 9 | 可观测层 | `app/obs/` | Langfuse 全链路 tracing：检索命中、工具成功率、延迟、成本 | 🔨 Phase 3 |

---

## 四、一次完整请求的调用链

```
POST /runs  { goal_text, budget_limit }
      │
      ▼
orchestrator.run_goal()
      │
      ├─ research_agent.extract_goal(goal_text)        自然语言 → {metric_name, target}
      ├─ data_agent.gather(metric_name, tools)         并行调 analytics/form/crm/erp → 漏斗
      ├─ opportunity_agent.find_opportunity(raw, llm)  定位最大流失环节
      │      └─[Phase 1] rag.retriever.search()        检索相似历史案例，带引用注入 prompt
      ├─ experiment_agent.design_experiment(...)       生成 A/B 方案 + 预算
      ├─ critic_agent.review(...)                      ◄── 独立校验：预算 / 数字幻觉
      │      └─ 不通过 → Reflect 回环重试（MAX_RETRIES=1）
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
