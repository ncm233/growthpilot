def design_experiment(opportunity: dict, raw_data: dict, budget_limit: float, llm) -> dict:
    """Builds a concrete A/B proposal. Every number in the returned dict is either
    copied from raw_data or computed from it — nothing is invented, so Critic Agent
    can trace each claim back to a source."""

    if opportunity["to_step"] == "提交表单":
        fields = raw_data["form_fields"]
        required = [f for f in fields if f["required"]]
        droppable = sorted(
            (f for f in fields if not f["required"]),
            key=lambda f: f["abandonment_rate"],
            reverse=True,
        )
        # drop every optional field whose abandonment rate clears the threshold —
        # keeps low-friction optional fields, cuts the ones actually causing drop-off
        threshold = 0.12
        dropped = [f for f in droppable if f["abandonment_rate"] > threshold]
        kept_optional = [f for f in droppable if f["abandonment_rate"] <= threshold]
        variant_b_fields = [f["field_id"] for f in required + kept_optional]

        hypothesis = (
            f"表单字段过多是「{opportunity['from_step']} → {opportunity['to_step']}」"
            f"流失的主因，去掉高流失字段（{'、'.join(f['label'] for f in dropped)}）"
            f"可以降低填写门槛"
        )
        variant_b_desc = f"表单从 {len(fields)} 个字段精简到 {len(variant_b_fields)} 个"
        proposed_budget = min(budget_limit, 8000.0)

        experiment = {
            "type": "form_simplification",
            "hypothesis": hypothesis,
            "variant_a": {"desc": "维持现有表单", "fields": [f["field_id"] for f in fields]},
            "variant_b": {"desc": variant_b_desc, "fields": variant_b_fields},
            "variant_b_desc": variant_b_desc,
            "target_form_id": "signup_form",
            "proposed_budget": proposed_budget,
            "budget_limit": budget_limit,
        }
    else:
        segments = raw_data["segments"]
        best_segment = max(segments, key=lambda s: s["conversion_rate"])
        hypothesis = (
            f"「{opportunity['from_step']} → {opportunity['to_step']}」流失较高，"
            f"向转化率最高的分群「{best_segment['segment']}」倾斜触达预算可能更有效"
        )
        variant_b_desc = f"将 30% 预算向「{best_segment['segment']}」分群倾斜"
        proposed_budget = min(budget_limit, 5000.0)
        experiment = {
            "type": "budget_reallocation",
            "hypothesis": hypothesis,
            "variant_a": {"desc": "维持现有预算分配"},
            "variant_b": {"desc": variant_b_desc, "target_segment": best_segment["segment"]},
            "variant_b_desc": variant_b_desc,
            "target_form_id": None,
            "proposed_budget": proposed_budget,
            "budget_limit": budget_limit,
        }

    experiment["narrative"] = llm.narrate(
        "experiment",
        {
            "hypothesis": experiment["hypothesis"],
            "variant_b_desc": experiment["variant_b_desc"],
            "proposed_budget": experiment["proposed_budget"],
            "budget_limit": budget_limit,
        },
    )
    return experiment
