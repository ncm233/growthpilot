# 开发计划（分阶段路线图）

面向中国企业的架构调整：不依赖 HubSpot / GA4 / Vercel，改用企业微信 / 飞书 / CRM / ERP / 表单 / 官网埋点，
LLM 默认接国产模型（数据不出境），部署走阿里云/腾讯云。

```
企业微信 / 飞书          →  身份认证 + IM 通知 + 审批流
CRM (纷享销客/销售易/自建) →  客户与商机数据
ERP (用友/金蝶/自建)      →  订单/库存/财务数据
表单 (金数据/自建埋点)     →  Lead 采集
官网行为数据 (神策/GrowingIO/自建埋点+ClickHouse) →  用户行为
         ↓
    统一数据接入层 (MCP Tools)
         ↓
    GrowthOps Agent 分析与实验层
         ↓
    人工审批 (飞书审批 / 企业微信审批)
         ↓
    写回原系统 (CRM/ERP/表单 API)
```

## 阶段

**Phase 0：需求与架构定稿（1周）** — 确定 MVP 数据源优先级、审批卡片字段、LLM 供应商。

**Phase 1：数据接入层（2-3周）** — 自建 MCP Server：`fetch_form_leads` / `fetch_website_events` / `fetch_crm_pipeline` / `fetch_erp_orders`。

**Phase 2：Agent 核心引擎（3-4周）** — Plan → Tool Call → Verify → Reflect 主循环；结构化 Experiment Memory；先做 5 个 Agent（Research / Data / Opportunity / Experiment / Critic）。

**Phase 3：Growth 业务逻辑（3-4周）** — Opportunity Agent 发现问题点，Hypothesis Engine 生成假设，Experiment Generator 生成 A/B 方案。

**Phase 4：模拟与评估层（2-3周）** — AgentA/B 风格 Persona 模拟做实验优先级排序；用公开数据集搭建 Eval Dashboard，验证不瞎编指标、不违反预算约束。

**Phase 5：审批与写回闭环（2周）** — 飞书/企业微信审批卡片 → 人工确认 → 自动写回 CRM/表单 → IM 通知执行结果。

**Phase 6：Dashboard/Demo 打磨（2周）** — Goal → Opportunity → Hypothesis → Experiment → Simulation → Approval → Result 全链路可视化。

**Phase 7：上线与迭代** — 部署到阿里云/腾讯云，接入监控，用真实数据回收反馈。

## 当前进度

MVP（Phase 1–6 的最小可跑版本）已在 [apps/agent-service](../apps/agent-service) 实现：5 个 Agent、Plan/Verify 循环、结构化 Memory、模拟层、审批与写回闭环、Eval 基准测试全部跑通，细节见根目录 [README.md](../README.md)。尚未做的：真实 CRM/ERP/埋点对接（当前为 Mock）、Phase 0 里更细的数据源优先级访谈、云端部署。
