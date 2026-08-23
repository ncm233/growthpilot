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

    # Found via adversarial testing: a phantom to_step (not in raw_data's
    # funnel at all) leaves actual_to as None while actual_from is still a
    # real number — `actual_from else None` alone doesn't guard that,
    # None / int crashes with TypeError instead of degrading to "issue found".
    # A crashed Critic is worse than a wrong one: the run fails open with no
    # verdict at all instead of blocking on a real issue.
    recomputed_drop = round(1 - (actual_to / actual_from), 4) if actual_from and actual_to is not None else None
    if recomputed_drop is not None and abs(recomputed_drop - opportunity["drop_rate"]) > 1e-4:
        issues.append(
            f"流失率计算不一致：声称 {opportunity['drop_rate']}，重算得 {recomputed_drop}"
        )

    # Found via adversarial testing, not hypothetical: the two checks above only
    # verify internal self-consistency (claimed numbers match the source data and
    # each other) — a step where users INCREASED (to_users > from_users, negative
    # drop_rate) sails through both if the numbers are self-consistent, even
    # though "the largest drop" being a net gain is nonsensical on its face.
    if recomputed_drop is not None and recomputed_drop <= 0:
        issues.append(
            f"「{opportunity['from_step']} → {opportunity['to_step']}」不是流失，是净增长"
            f"（{actual_from} → {actual_to}），不能作为流失机会点"
        )

    return {"passed": len(issues) == 0, "issues": issues}
