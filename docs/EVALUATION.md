# 评估方法与结果

> 面试用一句话总结：**这份评测不是为了拿满分，是为了找真 bug。** 重做评测的过程里
> 实际发现并修复了 `critic_agent.py` 的两个真实缺陷（见下方「找到的真实 bug」），
> 这比任何分数本身都更能说明评测设计得有没有用。

## 一、Critic Agent 评测：`packages/eval/benchmarks.py`

### 为什么拆成两套体系，不合并成一个分数

| 套件 | 测什么 | 用例来源 |
|---|---|---|
| **Baseline**（60 例） | Critic 能不能拦住**明显**的违规（预算超 10-80%、数字偏差 50-500） | `generate_synthetic_data.py` 风格的随机合成漏斗 |
| **Adversarial**（28 例，7 类 × 4 次重复） | Critic 能不能拦住**边界/隐蔽**的问题，以及会不会误伤合法边界情况 | 直接读 `critic_agent.py` 源码，针对每一行判断逻辑设计"刚好卡在判断边界上"的用例 |

之前只有 Baseline 一套，五项指标全 1.0——问题不在于分数本身，而在于"明显违规"这个门槛太低，
且测试数据和被测代码来自同一个合成脚本，本质是自己考自己。Adversarial 套件不测"够不够明显"，
测"判断逻辑本身有没有漏洞"。

### Adversarial 套件的 7 类用例

| 用例 | 预期结果 | 测的是什么 |
|---|---|---|
| `budget_exact_limit` | 通过 | 预算恰好等于上限（边界是 `>` 不是 `>=`） |
| `budget_one_cent_over` | 拦截 | 超出上限仅 1 分钱，容差（1e-6）是否真的够紧 |
| `budget_one_cent_under` | 通过 | 边界另一侧，确认没有误伤 |
| `growth_framed_as_drop` | 拦截 | **见下方「找到的真实 bug 1」** |
| `flat_step_zero_drop` | 拦截 | 流失率恰好为 0（不是"流失"，也不该被当机会点） |
| `phantom_step_reference` | 拦截 | 引用了漏斗里不存在的环节名 —— **见下方「找到的真实 bug 2」** |
| `subtle_one_percent_drift` | 拦截 | 数字偏差从"明显错"（50-500 绝对值）改成"看着像四舍五入"的 1% 相对偏差，阈值是否还扛得住 |

### 找到的真实 bug（不是设计出来演示的，是测出来的）

**Bug 1：`critic_agent` 不验证"流失"真的是流失。** 原逻辑只检查机会点引用的数字跟原始漏斗
是否自洽——如果 `to_users > from_users`（用户其实在增长），但 opportunity 声称的
`drop_rate` 是按这两个数字算出来的负数（内部自洽），两条已有检查全部通过。也就是说，
一个被包装成"最严重流失"的净增长环节可以直接通过审核。修复：新增 `recomputed_drop <= 0`
检查（[app/agents/critic_agent.py](../apps/agent-service/app/agents/critic_agent.py)）。

**Bug 2：`phantom_step_reference` 用例直接把 Critic 崩了。** 当 `to_step` 引用一个漏斗里
不存在的环节名时，`actual_to` 是 `None`，但原代码只用 `if actual_from` 做除零保护，
没检查 `actual_to`，导致 `None / int` 抛 `TypeError`——**Critic 直接崩溃，而不是报告一个
"发现问题"**。一个会崩溃的 Critic 比一个会误判的 Critic 更危险：误判至少还挡了一次审批，
崩溃是直接让整条 pipeline 挂掉。修复：把守卫条件改成 `actual_from and actual_to is not None`。

### 当前结果

```json
{
  "baseline": {
    "n_cases": 60,
    "opportunity_detection_accuracy": 1.0,
    "budget_constraint_catch_rate": 1.0,
    "budget_constraint_false_positive_rate": 0.0,
    "hallucination_catch_rate": 1.0,
    "simulation_direction_accuracy": 1.0
  },
  "adversarial": {
    "n_cases": 28,
    "accuracy": 1.0,
    "per_case_accuracy": {
      "budget_exact_limit": 1.0,
      "budget_one_cent_over": 1.0,
      "budget_one_cent_under": 1.0,
      "growth_framed_as_drop": 1.0,
      "flat_step_zero_drop": 1.0,
      "phantom_step_reference": 1.0,
      "subtle_one_percent_drift": 1.0
    },
    "failures": []
  }
}
```

（原始文件：[packages/eval/report.json](../packages/eval/report.json)）

**两套都是 1.0，但含金量不一样了**：Baseline 的 1.0 一直没什么信息量（本来就该 100% 拦住明显
违规）；Adversarial 的 1.0 是在**修复了两个真实 bug 之后**才达到的——过程本身（构造边界用例 →
发现问题 → 修代码 → 重新验证）才是这次重做评测的核心产出，不是分数。

### 已知局限（不回避）

- Adversarial 的 7 类用例不是穷举，只覆盖了读代码时能想到的边界；`from_step` 缺失、
  `drop_rate` 本身的浮点精度边界等还没专门测
- `simulation_direction_accuracy` 这个指标接近重言式：`simulator.py` 里 `effect_size` 恒为正、
  1000 次高斯采样的均值几乎不可能翻负，所以这个指标测的是"代码没写错"，不是"模拟准不准"，
  不该被读成"93% 模拟准确率"这种强结论

---

## 二、RAG 检索质量评测：`packages/eval/retrieval_eval.py`

### 规模的诚实说明

20 个查询，对应语料库现有的 8 条种子案例——**不是**文档里定的 50 题 / 150-300 条语料的目标规模。
这个脚本和它的指标就是留着跟语料库一起长大的，不是一次性任务，见 [CORPUS_SOURCES.md](CORPUS_SOURCES.md)。

### 三组消融（比最初计划的"有无 RAG"更精确）

最初规划里说要测"无 RAG / 纯向量 / 混合 / 混合+重排"四组，实际做的时候发现更有信息量的切法是
**分别隔离 embedding 质量和重排的边际贡献**：

| 配置 | MRR | recall@1 | recall@3 | recall@5 | 状态分布 |
|---|---|---|---|---|---|
| Mock embed + Mock rerank | 0.863 | 0.75 | 0.95 | 1.00 | 20 correct |
| **真实 embed + Mock rerank** | 0.942 | 0.90 | 1.00 | 1.00 | 20 correct |
| 真实 embed + 真实 rerank | 0.900 | 0.90 | 0.90 | 0.90 | 16 correct / 2 ambiguous / 2 wrong |

### 一个反直觉但查清楚了原因的发现：加了真实重排，recall 反而更低

表面看"真实 rerank"比"直通"分数更差，容易得出"重排帮倒忙"的错误结论。逐条查了这 4 个
掉分的 query 之后发现：**重排器把正确答案排到了第 1 名**（4 个案例里 top1 全部是期望的
案例 ID），真正拉低分数的是 **CRAG 置信度分级阈值**（`correct≥0.5 / ambiguous≥0.2 / 否则wrong`）
太保守——遇到用词抽象或带行话的 query（比如"增长黑客邀请裂变"对应"双边邀请奖励"这个案例），
即使排对了名次，置信度分数也压不到 0.2 以上，被判成 `wrong` 后**直接不返回任何 citation**，
recall 记为 0。

**结论**：这不是检索能力的问题，是分级阈值和当前 20 题小样本不匹配。0.5/0.2 这两个数字是上一轮
A/B 测试里凭 8 条语料的经验定的，样本一大就暴露出对"排对了但不够自信"这类情况过于保守。
**下一步**：语料补到 80-100 条、测试集补到 50 题之后，应该用这批数据重新扫一遍阈值，而不是
继续沿用两个只在小样本上验证过的数字。

### 两个真正的 top-1 miss（非阈值问题，是真实检索误差）

| Query | 期望 | 实际 top1 | 解读 |
|---|---|---|---|
| "搜索结果链接颜色" | exp-0002（Bing） | exp-0003（Google 41种蓝色） | 这两条本来就是近义案例（都是链接颜色测试），测试集设计时就该预料到这种模糊性，不算检索缺陷 |
| "视频推荐点击率优化" | exp-0007（Netflix缩略图） | exp-0001（CTA按钮颜色） | 真实的语义检索误差，但 top-3 能找回来（recall@3 仍是 1.0） |

---

## 三、下一步（跟 Phase 3 之后的计划一致）

1. Langfuse 接入后，把这两个评测脚本的运行也接进 tracing，能直接看到每次检索的 span 而不只是最终统计数字
2. 语料补到 80-100 条时，重新生成检索测试集（至少 50 题），并用那批数据重新校准 CRAG 分级阈值
3. Adversarial 套件可以继续加类别，比如专门测 `from_step` 缺失（目前只测了 `to_step` 缺失）
