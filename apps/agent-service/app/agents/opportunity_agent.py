from langfuse import observe

from ..rag import retriever


@observe(as_type="agent")
def find_opportunity(raw_data: dict, llm) -> dict:
    """Deterministic: scans the funnel for the single largest step-to-step drop.
    The LLM is only asked to narrate this after the fact — it never picks the step.
    RAG only grounds that narration with precedent cases; retrieval never influences
    which step gets picked, so a bad retrieval degrades the explanation, not the decision."""
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

    # Query construction was A/B tested against the real reranker, not guessed:
    # a full natural-language question scored WORSE than short keyword phrases
    # (0.0 wrong), because the corpus's own search_text (scene+hypothesis+
    # intervention+lesson) is itself short and content-word-dense, not
    # conversational — matching the corpus's register beats "sounding natural"
    # as a heuristic. Dropping from_step and using to_step alone scored best
    # (0.89 vs 0.29 for "A 到 B 转化流失", 0.0 for a full question) — see
    # docs/TECH_STACK.md for the full comparison table.
    rag_result = retriever.search(f"{worst['to_step']}转化流失", top_k=3)
    worst["citations"] = rag_result["citations"]
    worst["description"] = llm.narrate("opportunity", {**worst, "reference_cases": rag_result["prompt_block"]})
    return worst
