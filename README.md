# GrowthPilot

自主增长实验 Agent：给一个目标，它从数据里找机会点、生成实验假设、模拟排序、走人工审批，批准后写回原系统，并把结论存进长期记忆。

面向中国企业场景：企业微信 / 飞书 / CRM / ERP / 表单 / 官网埋点，而不是 HubSpot + GA4 那一套海外栈。

详细文档：
- [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) — 目录结构与分层职责
- [docs/API_AND_MATERIALS.md](docs/API_AND_MATERIALS.md) — API 清单与接入优先级
- [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) — 分阶段路线图（早期规划稿）

## 当前实现状态

这是一个**可本地运行的 MVP**，每一个外部系统都做成了可插拔接口（`app/tools/*`、`app/llm/*`）：
没有配置真实密钥时，自动用 Mock 实现（本地生成合成数据、审批走 Dashboard 按钮而不是真的飞书 UI）；
一旦在 `.env` 里填上真实密钥，`get_*_tool()` 工厂函数会自动切换到对应的 `Real*` 实现，Agent 代码本身不用改一行。

| 系统 | Mock（今天能跑） | Real（留好接口） |
|---|---|---|
| LLM | `MockLLM`：模板化中文叙述，零成本 | `OpenAICompatibleLLM`：接 DeepSeek / 通义千问 / GLM-4 等，只需 `LLM_BASE_URL` + `LLM_API_KEY` |
| 企业微信 | 通知落本地库 | `RealWecomTool`：真实 gettoken + message/send API |
| 飞书 | 审批状态就是本地 `runs.status`，Dashboard 按钮模拟人工审批 | `RealFeishuTool`：真实 tenant_access_token + 审批实例 API |
| CRM / ERP / 表单 / 埋点 | 合成数据（`app/tools/*.py` 里的 Mock 类） | 类已搭好骨架和 TODO，接入时新增一个 `Real*Tool` 类即可 |

## 快速开始

```bash
cd apps/agent-service
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

打开 http://127.0.0.1:8000 ，输入一个目标（比如"把创作者注册转化率从 3.4% 提到 5%"）点"开始分析"，
走一遍 Opportunity → Experiment → Critic 校验 → Simulation → 审批 → 写回 → Memory 的完整链路。

要接真实 LLM / 企业微信 / 飞书：复制 `apps/agent-service/.env.example` 为 `.env`，填入密钥即可，无需改代码。

## 跑 Eval

```bash
cd packages/eval
python generate_synthetic_data.py   # 生成合成的 Digital Marketing Performance 数据集
python benchmarks.py                # 跑 Critic / Simulation 的基准测试，输出 report.json
```

最新一次运行结果见 [packages/eval/report.json](packages/eval/report.json)。

## 目录

```
apps/agent-service/   FastAPI 后端：agents / tools / llm / simulation / planner / dashboard
packages/eval/         合成数据生成 + 基准测试
docs/                   架构、API 清单、开发计划、面试指南
```
