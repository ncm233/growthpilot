def review(opportunity: dict, experiment: dict, raw_data: dict, budget_limit: float) -> dict:
    """Independent verification pass, separate from the agents that generated the
    proposal. Two checks map directly to the two eval metrics in packages/eval:
    budget constraint adherence, and numeric-claim hallucination."""
    issues = []

    if experiment["proposed_budget"] > budget_limit + 1e-6:
        issues.append(
            f"预算超出上限：提议 ¥{experiment['proposed_budget']:.0f} > 上限 ¥{budget_limit:.0f}"
        )

    funnel_by_step = {s["step"]: s["users"] for s in raw_data["funnel"]}
    claimed_from = opportunity["from_users"]
    claimed_to = opportunity["to_users"]
    actual_from = funnel_by_step.get(opportunity["from_step"])
    actual_to = funnel_by_step.get(opportunity["to_step"])
    if claimed_from != actual_from or claimed_to != actual_to:
        issues.append(
            f"机会点引用的数字与原始漏斗数据不符："
            f"声称 {claimed_from}->{claimed_to}，实际 {actual_from}->{actual_to}"
        )

    recomputed_drop = round(1 - (actual_to / actual_from), 4) if actual_from else None
    if recomputed_drop is not None and abs(recomputed_drop - opportunity["drop_rate"]) > 1e-4:
        issues.append(
            f"流失率计算不一致：声称 {opportunity['drop_rate']}，重算得 {recomputed_drop}"
        )

    return {"passed": len(issues) == 0, "issues": issues}
