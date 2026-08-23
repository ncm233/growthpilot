def find_opportunity(raw_data: dict, llm) -> dict:
    """Deterministic: scans the funnel for the single largest step-to-step drop.
    The LLM is only asked to narrate this after the fact — it never picks the step."""
    funnel = raw_data["funnel"]
    worst = None
    for i in range(len(funnel) - 1):
        a, b = funnel[i], funnel[i + 1]
        drop_rate = 1 - (b["users"] / a["users"]) if a["users"] else 0
        if worst is None or drop_rate > worst["drop_rate"]:
            worst = {
                "from_step": a["step"],
                "to_step": b["step"],
                "from_users": a["users"],
                "to_users": b["users"],
                "drop_rate": round(drop_rate, 4),
            }
    worst["description"] = llm.narrate("opportunity", worst)
    return worst
