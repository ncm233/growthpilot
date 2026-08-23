# API 与物料清单

> 本文件回答两个问题：**要申请哪些 API（花多少钱、多难申请、什么时候申请）**，
> 以及 **要准备哪些物料（语料、数据、展示材料）**。
> 按 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) 的 Phase 组织，避免申请周期卡住开发。

---

## 一、API 清单

### 图例
- 💰 成本｜⏱ 申请周期｜🔑 个人能否申请（无公司）

### Phase 1 必需 — RAG 检索层

| API / 组件 | 用途 | 💰 | ⏱ | 🔑 | 建议 |
|---|---|---|---|---|---|
| **硅基流动 API**（BAAI/bge-m3 + bge-reranker-v2-m3） | embedding + rerank，托管，已实测 | 免费额度 | 注册即用 | ✅ | **已采用为默认真实模式**，见 `EMBEDDER_PROVIDER=siliconflow`。不用下载模型，`httpx` 直接调，跟 `OpenAICompatibleLLM` 同一套调用方式 |
| BAAI/bge-small-zh-v1.5（本地） | 中文向量嵌入，离线备选 | 免费 | 无需申请 | ✅ | 本地跑，~100MB，`pip install -r requirements-rag.txt`。断网/不想依赖第三方服务时用 |
| BAAI/bge-reranker-base（本地） | 检索结果重排，离线备选 | 免费 | 无需申请 | ✅ | 本地跑，~1.1GB |
| **LanceDB** | 嵌入式向量库 | 免费 | 无需申请 | ✅ | `pip install lancedb` + `tantivy`（FTS 索引依赖），**无需 Docker**（硬约束） |

> ⚠️ **不要选 Milvus / Qdrant server / Elasticsearch** —— 都要 Docker，你环境跑不起来，部署也复杂。
> 三档实现（Mock / SiliconFlow API / 本地 bge）的完整对比和真实检索质量数据见 [TECH_STACK.md](TECH_STACK.md)。

### Phase 1–5 必需 — LLM API

| API | 💰 | ⏱ | 🔑 | 建议 |
|---|---|---|---|---|
| **DeepSeek** | ~¥1/百万 token（最便宜） | 当天，充 ¥10 起 | ✅ | **主力**。OpenAI 兼容，直接填进 `LLM_BASE_URL` |
| **智谱 GLM-4-Flash** | 免费额度 | 当天 | ✅ | **备用/降级**。做 fallback 链路，成本优化的故事素材 |
| 通义千问 DashScope | 有免费额度 | 当天 | ✅ | 第三选择，多模态需求时用 |
| Moonshot Kimi | 按量 | 当天 | ✅ | 长上下文场景备用 |

> 代码里 `app/llm/openai_compatible.py` 已封装好 OpenAI 兼容层，**换模型只改 `.env` 两个变量**。
> 面试可讲：「我做了多供应商 fallback，主力 DeepSeek 控成本，超限降级到 GLM-4-Flash。」

### Phase 2 必需 — MCP 客户端（验证用，不是 API）

| 工具 | 💰 | 说明 |
|---|---|---|
| **Claude Desktop** | 免费 | 装好后改 `claude_desktop_config.json` 即可接你的 MCP Server。**面试现场演示就靠它** |
| Cursor / VS Code + Cline | 免费 | 备选 MCP 客户端 |

### Phase 3 必需 — 可观测性

| 服务 | 💰 | ⏱ | 🔑 | 建议 |
|---|---|---|---|---|
| **Langfuse Cloud** | 免费版够用（5 万 observations/月） | 注册即用 | ✅ | **首选**。无 Docker 就别自托管。SDK：`pip install langfuse` |
| Arize Phoenix | 免费开源 | 本地 pip | ✅ | 备选，偏评测打分 |

### Phase 5 可选（强烈建议做，"已部署"这三个字值钱）— IM / 审批

> **关键信息：飞书和企业微信都可以用个人身份注册一个"企业"**，不需要真实公司。
> 注册飞书 → 创建团队（填自己名字即可）→ 开发者后台 → 创建企业自建应用 → 拿 App ID / App Secret。
> 这是整个项目里最容易被误以为"做不了"的部分，实际上一小时能搞定。

| API | 用途 | 💰 | ⏱ | 🔑 | 优先级 |
|---|---|---|---|---|---|
| **飞书开放平台** | 机器人消息 + 审批实例 + 多维表格 | 免费 | 1–2 天审核 | ✅ 个人可注册团队 | **P0，只接这一家** |
| ↳ 多维表格 API | 当轻量 CRM 用，替代真实 CRM | 免费 | — | ✅ | P0 |
| ↳ 审批 API | 真实审批流，替代 Dashboard 按钮 | 免费 | — | ✅ | P0 |
| ↳ 机器人消息 API | 审批卡片 + 结果通知 | 免费 | — | ✅ | P0 |
| 企业微信 | 消息推送 + 审批单据 | 免费 | 1–2 天 | ✅ | P2，锦上添花 |

**飞书一家就能覆盖「数据源 + 审批 + 写回」三个环节**，`app/tools/feishu_tool.py`（4070 字节）里 `RealFeishuTool` 的骨架已经写好了，填密钥即可。

### 部署

| 平台 | 💰 | 适配度 | 说明 |
|---|---|---|---|
| **Zeabur** | 有免费额度 | ⭐⭐⭐⭐⭐ | 中国网络友好、支持 Python、支持持久化卷放 LanceDB。**首选** |
| Hugging Face Spaces | 免费 | ⭐⭐⭐⭐ | 免费无限期，适合放 Demo；但国内访问需梯子 |
| Railway | 有免费额度 | ⭐⭐⭐ | 稳定，国内访问一般 |
| 阿里云/腾讯云 ECS | ¥100/月起 | ⭐⭐⭐ | 秋招期间没必要花这钱 |

> 建议：**Zeabur 部主站 + HF Spaces 部一份备份**。面试官在哪都能打开。

### 暂不接入（讲清楚为什么不接，比硬接更专业）

| API | 不接的理由 |
|---|---|
| CRM（纷享销客/销售易） | 需企业授权，个人拿不到。**用飞书多维表格模拟，架构上可插拔** |
| ERP（用友/金蝶） | 授权周期以月计，投入产出比极低 |
| 神策 / GrowingIO | 企业版付费。用合成埋点数据代替 |

---

## 二、物料清单

### A. 语料物料 —— Phase 1 的命脉，最容易卡死，**Day 1 就开工**

**目标：150–300 条结构化增长实验记录。** 没有语料，RAG 就是空壳，整个项目最大的亮点会变成最大的破绽。

**进度**：8 条种子语料已核实入库，见 [packages/corpus/curated/seed_cases.jsonl](../packages/corpus/curated/seed_cases.jsonl)；全部来源链接（案例库 + Kaggle 数据集）已核实并整理成清单，见 [docs/CORPUS_SOURCES.md](CORPUS_SOURCES.md)。

**统一 Schema**（写进 `packages/corpus/SCHEMA.md`）：

```jsonc
{
  "id": "exp-0042",
  "scene": "SaaS 官网注册转化",        // 场景
  "channel": "landing_page",           // 渠道
  "hypothesis": "把注册表单从 7 字段减到 3 字段可提升完成率",
  "intervention": "移除公司规模/行业/职位/电话 4 个非必填字段",
  "metric": "form_completion_rate",
  "baseline": 0.034,
  "result": 0.051,                     // 结果
  "lift": "+50%",
  "outcome": "positive",               // positive | negative | flat
  "lesson": "字段每减少 1 个，完成率约提升 6–8%，但线索质量下降需配合后置补全",
  "source": "GoodUI / 案例编号 xx",
  "source_url": "https://..."
}
```

**来源与配额建议：**

| 来源 | 目标条数 | 获取方式 | 备注 |
|---|---|---|---|
| **GoodUI** goodui.org | 60–80 | 公开 A/B 测试案例库，结构化程度最高 | 有明确的 lift 数字，最适合做语料 |
| **ABtestguide** | 30–40 | 公开案例 + 统计显著性数据 | 可用来做「置信度」字段 |
| **GrowthHackers** 案例 | 30–40 | 社区案例复盘 | 质量参差，需人工筛 |
| **你自己三段实习的脱敏记录** | **20–40** | 自己写 | ⭐ **最有价值的部分，别人抄不走** |
| Kaggle Marketing A/B Testing Dataset | 20–30 | CC0 协议可直接入库 | 补数值型案例 |

**你自己的语料怎么写**（这几条面试官一定会追问，写扎实）：
- 易娱：SEO 站群「泛休闲内容走主站 / 具体游戏内容走分站」的分流假设 → 25 个分站单批次发布 → 长尾词承接效果
- Ancher.ai：Reddit 冷启动 2 周 0→8k 粉的账号权重养成假设；125 封个性化冷启动邮件的分组承接策略 → 重复/无效/跳过均为 0
- 中文在线：AI 漫剧上架流程提效，100+ 人工作组的高频场景拆解 → 哪些环节适合自动化、哪些不适合

> ⚠️ **脱敏红线**：不能出现真实公司内部数据、客户名、未公开的业务指标绝对值。
> 写成「某短视频平台」「转化率提升约 X%」这种相对表述，或直接把绝对值换成比例。

### B. 评测标注集 —— Phase 3

| 物料 | 规模 | 说明 |
|---|---|---|
| `packages/eval/retrieval_testset.jsonl` | **50 题** | `{query, relevant_ids[]}`，人工标注哪几条语料应该被检索到。这是 recall@k / nDCG 的唯一依据 |
| 对抗性实验方案用例 | 20 条 | **专门用来打破当前 report.json 全 1.0 的困境**：故意造预算超限、数字微小偏差（1% 以内）、引用不存在的漏斗环节、逻辑自洽但违背常识的方案 |
| 消融配置 | 4 组 | 无 RAG / 纯向量 / 混合检索 / 混合+重排 |

> ⚠️ **当前 `report.json` 五项全 1.0 是重大可信度风险。** 原因是 `critic_agent` 是规则判断，
> 而测试用例来自同一个 `generate_synthetic_data.py`，等于自己考自己。
> 解法：(1) 加对抗性用例把分数打下来；(2) 让 experiment_agent 用真实 LLM 生成方案而非确定性 clamp；
> (3) 报告里明确写清「规则可捕获 vs LLM 生成的边界情况」的分界。
> **一个 0.82 的诚实数字，远比 1.0 有说服力。**

### C. 演示数据

| 物料 | 说明 |
|---|---|
| 合成漏斗数据 | 已有 `generate_synthetic_data.py`，保持 |
| 飞书多维表格 Demo 表 | Phase 5 接真实飞书时，造一张 50 行的假 CRM 表 |
| 3 个预置 Demo 目标 | Dashboard 上放快捷按钮，面试时不用现场打字：<br>「把创作者注册转化率从 3.4% 提到 5%」<br>「降低 Puzzle 站群的跳出率」<br>「提升冷启动邮件的回复率」 |

### D. 账号与密钥清单（建一个 `.env` 检查表）

```
LLM_BASE_URL / LLM_API_KEY          DeepSeek        Phase 1
LLM_FALLBACK_BASE_URL / KEY         智谱 GLM-4-Flash Phase 1
LANGFUSE_PUBLIC_KEY / SECRET_KEY    Langfuse Cloud  Phase 3
LANGFUSE_HOST                       Langfuse Cloud  Phase 3
FEISHU_APP_ID / FEISHU_APP_SECRET   飞书开放平台     Phase 5
FEISHU_APPROVAL_CODE                飞书审批定义     Phase 5
WECOM_CORP_ID / SECRET / AGENT_ID   企业微信        Phase 5（可选）
```

> 🔒 `.env` 必须在 `.gitignore` 里。提交前用 `git diff --cached` 确认没有密钥泄漏。

### E. 展示物料 —— Phase 5

| 物料 | 用途 | 制作要点 |
|---|---|---|
| **README 顶部 Demo GIF** | 3 秒内抓住注意力 | 录 MCP 在 Claude Desktop 里被调用的过程，比录 Dashboard 更惊艳 |
| **架构图**（Mermaid，内嵌 README） | 讲解主视觉 | 九层分层 + 数据流向 + 标注人工审批边界 |
| **Langfuse trace 截图** | 证明可观测性真的接了 | 展开一次完整 run 的嵌套 span |
| **消融对比表** | 证明数字是测出来的不是编的 | 四行表格，放 README 和 `docs/EVALUATION.md` |
| **90 秒 Demo 视频** | 投递时附链接 | 目标输入 → 检索引用 → 实验方案 → 模拟 → 审批 → 写回，一镜到底 |
| **`claude_desktop_config.json` 片段** | 面试官 30 秒自己接上 | 放 README 显眼位置，复制即用 |
| **[INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md)** | 面试自查背稿 | 已单独成文 |

---

## 三、申请时间线（避免卡进度）

| 时间 | 动作 |
|---|---|
| **今天** | 注册 DeepSeek 充 ¥20；注册 Langfuse Cloud；开始搜集语料 |
| **Phase 1 第 1 天** | 下载 bge 模型（首次跑会自动拉，提前跑一次避免演示时等下载） |
| **Phase 2 前** | 装 Claude Desktop |
| **Phase 4 期间** | 注册飞书团队 + 建自建应用（审核 1–2 天，提前申请） |
| **Phase 5 第 1 天** | 注册 Zeabur，绑 GitHub 仓库 |

**面试坦诚话术**：「当前 Demo 用飞书多维表格模拟 CRM。架构上数据接入层是可插拔的 MCP 工具，
接真实纷享销客只需要新增一个实现类，业务代码不动。个人身份拿不到企业 CRM 授权，
所以我选择把可插拔性做扎实，而不是硬造一个没打磨过的假集成。」
