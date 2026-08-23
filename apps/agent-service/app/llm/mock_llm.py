from .base import BaseLLM


class MockLLM(BaseLLM):
    """Deterministic template-based narration. No network calls, no API key.
    Exists so the whole pipeline runs today; swap LLM_PROVIDER=openai_compatible
    (with LLM_BASE_URL / LLM_API_KEY) to route the same calls through a real model."""

    def narrate(self, task: str, context: dict) -> str:
        method = getattr(self, f"_{task}", None)
        if method is None:
            return f"[mock-llm] 未知任务类型 {task}，原始数据：{context}"
        return method(context)

    def _opportunity(self, c: dict) -> str:
        base = (
            f"在漏斗「{c['from_step']} → {c['to_step']}」环节发现明显流失："
            f"{c['from_users']} 个用户中只有 {c['to_users']} 个进入下一步，"
            f"流失率 {c['drop_rate']*100:.1f}%，是当前漏斗里流失最严重的一环。"
        )
        return base + self._citation_suffix(c)

    def _experiment(self, c: dict) -> str:
        base = (
            f"假设：{c['hypothesis']}。"
            f"实验设计为 A/B 对照——A 组保持现状，B 组{c['variant_b_desc']}，"
            f"预计投入 ¥{c['proposed_budget']:.0f}（预算上限 ¥{c['budget_limit']:.0f}）。"
        )
        return base + self._citation_suffix(c)

    def _citation_suffix(self, c: dict) -> str:
        ref = c.get("reference_cases")
        if not ref or ref.startswith("（"):
            return ""
        return f" 参考历史案例：\n{ref}"

    def _simulation_summary(self, c: dict) -> str:
        return (
            f"基于 {c['n_personas']} 个模拟用户画像的预测：预期提升区间 "
            f"{c['lift_low']*100:.1f}% ~ {c['lift_high']*100:.1f}%，置信度 {c['confidence']*100:.0f}%。"
            f"该结果仅用于实验优先级排序，不替代真实 A/B 测试结果。"
        )
