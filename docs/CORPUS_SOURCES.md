# 语料来源与链接清单

回答三个问题：**去哪找增长/A-B 测试案例**、**去哪找可直接跑的数据集**、**评测该参照哪些基准**。全部链接均已用 WebSearch 逐条核实（截至 2026-08-23），不是凭记忆猜的。

| 节 | 内容 | 用在哪 |
|---|---|---|
| 一 | 已收录的 8 条种子语料 | 现状 |
| 二 | 英文案例库（GoodUI 等） | RAG 语料主力 |
| 三 | 中文案例源 + 中英检索鸿沟的解法 | RAG 语料 |
| 四 | Kaggle 结构化数据集 | Eval / 建模 |
| 五 | 天池中文真实数据集 | **Demo 漏斗换真实数据** |
| 六 | RAG / Agent 评测基准 | Phase 3 评测方法论 |
| 七 | 扩充流程与优先级 | 执行顺序 |

## 一、已收录：8 条种子语料

见 [packages/corpus/curated/seed_cases.jsonl](../packages/corpus/curated/seed_cases.jsonl)，每条都标了可信度（是否为一手数据 vs 行业广泛引用的二手数字）：

| id | 案例 | 效果 | 一手/二手 |
|---|---|---|---|
| exp-0001 | HubSpot CTA 红/绿按钮 | 点击率 +21% | 一手（HubSpot 官方博客） |
| exp-0002 | Bing 搜索结果链接颜色 | 年收入 +$80M | 一手（Bing 官方博客） |
| exp-0003 | Google 41 种蓝色链接测试 | 年收入 +$200M | 二手（广泛引用，非 Google 一手） |
| exp-0004 | Obama 2008 竞选官网多变量测试 | 注册 +40%，$60M 额外捐款 | 一手（Optimizely 案例研究） |
| exp-0005 | Airbnb 专业摄影 | 预订频次 +7% | 一手（CMU 学术论文 + Airbnb 工程博客） |
| exp-0006 | Dropbox 双边邀请奖励 | 注册永久 +60%，15个月 +3900% | 一手（广泛报道，数字一致性高） |
| exp-0007 | Netflix 个性化缩略图 | 点击率 +20% | 二手（广泛引用，非 Netflix 一手论文） |
| exp-0008 | Expedia 删除易混淆表单字段 | 年利润 +$12M | 一手（多家 UX 媒体独立报道，数字一致） |

exp-0008 和我们自己 Demo 里的"精简注册表单字段"实验类型直接对应，面试时可以直接类比引用。

## 二、案例库（继续扩充到 150–300 条时用）

| 来源 | 规模 | 访问方式 | 备注 |
|---|---|---|---|
| [GoodUI Data Stories](https://goodui.org/datastories/) | 26 篇详细案例 + 会员区 600+ 测试 | 免费预览 + 付费会员看全部 | 结构化程度最高，胜负结果都公开（不只报喜不报忧） |
| [GoodUI Patterns](https://goodui.org/patterns/) | 141 个模式，基于 635 次测试 | 免费浏览 | 按模式索引，适合反查"这个改动有没有人测过" |
| [GrowthHackers Growth Studies](https://growthhackers.com/category/growth-studies/) | 持续更新 | 免费 | WhatsApp/IBM 等大厂案例 |
| [Optimizely Insights Blog](https://www.optimizely.com/insights/) | 持续更新 | 免费 | Obama 案例出处，企业级 A/B 案例质量较高 |
| [Unbounce A/B Testing Examples](https://unbounce.com/a-b-testing/examples/) | 10 个案例 | 免费 | 落地页场景为主 |
| [HubSpot 11 A/B Testing Examples](https://blog.hubspot.com/marketing/a-b-testing-experiments-examples) | 11 个案例 | 免费 | 含红绿按钮案例原文 |
| [CXL: Which CTA Button Color Converts Best](https://cxl.com/blog/which-color-converts-the-best/) | 综述型 | 免费 | 汇总多个颜色类测试，附方法论批判（很多"颜色测试"结论其实站不住脚，这篇文章本身就是很好的"如何识破伪案例"素材） |
| [人人都是产品经理：18个用户增长案例](https://www.yunyingpai.com/data/460331.html) | 18 个案例 | 免费 | 中文，含 Dropbox 等案例的本地化解读 |

## 三、中文案例源（补 bge-small-zh 的中文语料缺口）

项目定位是"面向中国企业场景"，嵌入模型也选了 `bge-small-zh`，但语料如果全是英文案例，检索时的中英语义鸿沟会实打实拉低命中率。这几个是中文来源：

| 来源 | 规模 | 链接 | 质量判断 |
|---|---|---|---|
| 运营派：18 个用户增长案例 | 18 | [yunyingpai.com/data/460331.html](https://www.yunyingpai.com/data/460331.html) | ⚠️ 主要是 Dropbox/LinkedIn 等西方案例的中文转述，**和英文源重复**，价值在于提供中文表述方式而非新增案例 |
| 人人都是产品经理：载入史册的 18 个国外增长黑客案例 | 18 | [woshipm.com/operate/3192604.html](https://www.woshipm.com/operate/3192604.html) | ⚠️ 同上，与运营派高度重叠 |
| 人人都是产品经理：增长黑客 AB-Testing 系统设计 | 方法论 | [woshipm.com/pd/4171327.html](https://www.woshipm.com/pd/4171327.html) | ✅ **不是案例是方法论**，但对写 `lesson` 字段的中文表述很有参考价值 |
| CSDN：10 个 A/B 测试实例 | 10 | [blog.csdn.net/2401_86759994/article/details/141672636](https://blog.csdn.net/2401_86759994/article/details/141672636) | ✅ 含 Going「免费注册→免费试用」+104%、Campaign Monitor 动态文本替换 +31.4% 等**带明确数字**的案例 |

> ⚠️ **诚实结论：中文公开案例库的信息密度远低于英文源，而且绝大多数是同一批西方案例的转述。**
> 与其硬凑中文案例条数，**真正能补上中文缺口的是两件事**：
> ① 把英文案例转录成 schema 时，`hypothesis` / `intervention` / `lesson` **三个字段用中文写**（`source` 保留英文原链接）——
> 这样检索侧的中文 query 能对上中文字段，语义鸿沟问题直接消解；
> ② 你自己三段实习的脱敏记录天然就是中文的真实中国场景语料，这是唯一无可替代的部分。

## 四、结构化数据集（Kaggle，可直接下载建模）

| 数据集 | 规模 | 链接 |
|---|---|---|
| Digital Marketing Performance Dataset | 合成数据，Multi-Platform | [kaggle.com/datasets/alinaboulsi/digital-marketing-performance-dataset](https://www.kaggle.com/datasets/alinaboulsi/digital-marketing-performance-dataset) |
| Marketing A/B Testing | **58.8万行真实实验数据**（ad vs psa 分组，含 converted/total_ads/时段字段） | [kaggle.com/datasets/faviovaz/marketing-ab-testing](https://www.kaggle.com/datasets/faviovaz/marketing-ab-testing) |
| Facebook Ad Campaign | 3 个真实campaign，含年龄/性别/兴趣定向 + 花费/点击/转化 | [kaggle.com/datasets/madislemsalu/facebook-ad-campaign](https://www.kaggle.com/datasets/madislemsalu/facebook-ad-campaign) |
| Sales Conversion Optimization (Clicks Conversion Tracking) | 广告点击转化，适合做 CAC/CPA 分析 | [kaggle.com/datasets/loveall/clicks-conversion-tracking](https://www.kaggle.com/datasets/loveall/clicks-conversion-tracking) |
| Marketing Campaign Dataset | 客户画像 + 营销响应 | [kaggle.com/datasets/rahulchavan99/marketing-campaign-dataset](https://www.kaggle.com/datasets/rahulchavan99/marketing-campaign-dataset) |

`faviovaz/marketing-ab-testing` 是这里面**最值得优先接入**的：真实实验数据、58.8万行、字段干净，可以直接喂给 `packages/eval` 做比 60 条合成用例更有说服力的基准测试。

## 五、中文真实数据集（天池，做中国场景 Demo 用）

Kaggle 那批数据是海外营销场景。要让 Demo 的"漏斗"看起来像中国互联网业务，用天池：

| 数据集 | 规模 | 链接 | 用途 |
|---|---|---|---|
| **淘宝用户购物行为数据集（UserBehavior）** | ~100 万用户、约 1 亿条行为记录（2017-11-25 ~ 12-03）；字段：user_id / item_id / category_id / behavior_type / timestamp，behavior_type 含 pv / cart / fav / buy | [tianchi.aliyun.com/dataset/649](https://tianchi.aliyun.com/dataset/649) | ⭐ **首选**。`pv → cart → fav → buy` 四个 behavior_type 天然就是一个**真实转化漏斗**，直接对上 `data_agent.gather()` 的输出结构 |
| 电商用户行为分析数据集 | 中等 | [tianchi.aliyun.com/dataset/216886](https://tianchi.aliyun.com/dataset/216886) | 备选 |
| 电商购物用户行为分析数据 | 中等 | [tianchi.aliyun.com/dataset/203653](https://tianchi.aliyun.com/dataset/203653) | 备选 |
| 天池数据集总入口 | — | [tianchi.aliyun.com/dataset/](https://tianchi.aliyun.com/dataset/) | 自行检索 |

**为什么 UserBehavior 值得优先接**：现在 `generate_synthetic_data.py` 造的漏斗是合成的，面试官一问"这数据哪来的"就只能答"我自己造的"。
换成淘宝真实行为数据算出来的漏斗，`opportunity_agent` 定位的"最大流失环节"就是**真实存在的业务问题**，说服力完全不同。
注意 1 亿行不用全用，抽样 100 万行就够 Demo，避免仓库体积失控（**原始数据不要提交进 git**，写个下载脚本）。

## 六、评测基准数据集（Phase 3 用，直接对应 harness 关键词）

这一节和语料无关，是**给评测层用的**。面试时能说出"我参照 X 基准的方法设计了自己的评测集"，比自己拍脑袋定指标专业得多。

### 检索质量

| 基准 | 说明 | 链接 |
|---|---|---|
| **C-MTEB** | 中文文本嵌入基准，35 个数据集 / 6 类任务（含 retrieval、reranking）。**bge 系列模型就是在这套基准上评的**，你用 bge 就该知道它的评测口径 | [huggingface.co/C-MTEB](https://huggingface.co/C-MTEB) ｜ [排行榜](https://huggingface.co/spaces/mteb/leaderboard) ｜ [C-Pack 论文](https://arxiv.org/html/2309.07597v3) |
| T2Retrieval | C-MTEB 里的中文检索子集，可直接下载 | [huggingface.co/datasets/mteb/T2Retrieval](https://huggingface.co/datasets/mteb/T2Retrieval) |

### RAG 幻觉与忠实度

| 基准 | 说明 | 链接 |
|---|---|---|
| **RAGTruth** | 1.8 万条**词级标注**的幻觉语料，覆盖 QA / data2text / 摘要三类任务，把幻觉分成 Evident Conflict / Subtle Conflict / Baseless Information 等类型。**你的 `critic_agent` 做的"数字幻觉检测"，正好可以对齐它的分类体系** | [github.com/ParticleMedia/RAGTruth](https://github.com/ParticleMedia/RAGTruth) |
| **CRAG** | Meta 出的综合 RAG 基准，4409 组 QA，5 个领域 8 类问题，带模拟检索 API。**你 `retriever.py` 里的 CRAG 分级（Correct/Ambiguous/Wrong）概念就来自这条线** | [github.com/facebookresearch/CRAG](https://github.com/facebookresearch/CRAG/) ｜ [论文](https://arxiv.org/abs/2406.04744) |
| RAGBench / RAGEval | 可解释 RAG 基准 / 场景化评测集生成框架，做自己的领域评测集时可参考方法 | [RAGBench](https://arxiv.org/pdf/2407.11005) ｜ [RAGEval](https://arxiv.org/pdf/2408.01262) |

### Agent 工具调用

| 基准 | 说明 | 链接 |
|---|---|---|
| **τ²-bench** | Sierra 出的工具-Agent-用户交互基准，**核心考点是"Agent 能不能在遵守领域规则的前提下完成任务"——和你的 `critic_agent` 校验预算约束是同一类问题** | [github.com/sierra-research/tau2-bench](https://github.com/sierra-research/tau2-bench) ｜ [论文](https://arxiv.org/pdf/2406.12045) |
| τ²-bench-Verified | Amazon 修正版，订正了原版里任务定义与评判标准不一致的问题 | [github.com/amazon-agi/tau2-bench-verified](https://github.com/amazon-agi/tau2-bench-verified) |
| ScaleAI MCP-Atlas | 单轮自然语言请求 + 多工具调用的 ground truth 轨迹，**Phase 2 做完 MCP Server 后可以拿它的格式做自测** | [huggingface.co/datasets/ScaleAI/MCP-Atlas](https://huggingface.co/datasets/ScaleAI/MCP-Atlas) |
| mcp-agent-trajectory-benchmark | 49 条 MCP agent 轨迹（ATIF v1.2 格式），体量小、适合参考轨迹记录格式 | [huggingface.co/datasets/obaydata/mcp-agent-trajectory-benchmark](https://huggingface.co/datasets/obaydata/mcp-agent-trajectory-benchmark) |

> ⚠️ **不要真去跑这些基准。** 它们体量大、跑一遍成本高，而且和你的业务场景不匹配——
> 强行贴一个 τ²-bench 分数反而暴露你不理解基准的适用范围。
> **正确用法是借鉴方法论**：借 RAGTruth 的幻觉分类体系设计你 `critic_agent` 的检查项，
> 借 C-MTEB 的 recall@k / nDCG@k 口径定义你 50 题标注集的指标，
> 借 τ²-bench 的"规则遵守"视角解释你为什么要做预算约束校验。
> 面试话术：**「我没跑这些基准，因为我的场景和它们不重合。但我参照 RAGTruth 的幻觉分类设计了自己的校验项，具体是……」**

## 七、继续扩充语料的建议流程

**不做自动爬虫**——GoodUI 等付费案例库有 ToS 限制，而且案例这种非结构化叙事内容本来就需要人工判断才能提炼成 [SCHEMA.md](../packages/corpus/SCHEMA.md) 里的结构化字段。建议流程：

1. 每周从上面的免费来源里挑 5–10 个案例，人工按 schema 转录成一行 JSONL，追加到 `packages/corpus/curated/`
2. **转录时 `hypothesis` / `intervention` / `lesson` 三个字段一律写中文**，`source` / `source_url` 保留英文原文出处——这是解决中英检索鸿沟最省力的办法（见第三节）
3. 数字有二手来源分歧的（比如 exp-0003 的 $200M），在 `lesson` 字段里明确写"广泛引用，非一手数据"，不要含糊带过
4. 自己三段实习的脱敏经历权重最高——见 [API_AND_MATERIALS.md](API_AND_MATERIALS.md) 里"你自己的语料怎么写"那节，这部分是别人抄不走的差异化内容

### 优先级排序（时间紧的话按这个顺序做）

| 优先级 | 动作 | 理由 |
|---|---|---|
| **P0** | 接 [天池 UserBehavior](https://tianchi.aliyun.com/dataset/649)，把 Demo 漏斗换成真实数据 | 一次性解决"数据是你自己造的"这个最致命的质疑 |
| **P0** | 写 20–40 条自己实习的脱敏案例 | 唯一不可替代的差异化语料 |
| **P1** | 接 [faviovaz/marketing-ab-testing](https://www.kaggle.com/datasets/faviovaz/marketing-ab-testing)（58.8 万行真实实验数据）替换 eval 的合成用例 | 比继续攒案例条数更能提升可信度 |
| **P1** | 案例库补到 80–100 条（英文源为主，字段写中文） | RAG 检索需要的最低语料密度 |
| **P2** | 参照 RAGTruth 分类体系细化 `critic_agent` 检查项 | 面试深度加分，非必需 |
| **P3** | 案例补到 200–300 条 | 边际收益递减，有时间再说 |

> **一句话判断标准**：面试官不会数你有多少条语料，但一定会问"你这数据哪来的"。
> **P0 两项解决的是"来源可信"，比 P3 的"数量好看"重要得多。**
