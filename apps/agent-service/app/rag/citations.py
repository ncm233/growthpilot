def format_citations(hits: list[dict]) -> dict:
    """Turns reranked LanceDB rows into (a) a prompt-ready numbered block for
    LLM narration and (b) a structured list for the API/UI, so citations
    survive as clickable sources instead of dissolving into prose."""
    citation_list = []
    lines = []
    for i, h in enumerate(hits, start=1):
        citation_list.append(
            {
                "n": i,
                "id": h.get("id"),
                "scene": h.get("scene"),
                "lift": h.get("lift"),
                "outcome": h.get("outcome"),
                "confidence": h.get("confidence"),
                "lesson": h.get("lesson"),
                "source": h.get("source"),
                "source_url": h.get("source_url"),
                "score": round(h.get("_rerank_score", 0.0), 4),
            }
        )
        secondary_note = "（二手数据）" if h.get("confidence") == "secondary" else ""
        lines.append(f"[{i}] {h.get('scene')}：{h.get('lesson')}（效果：{h.get('lift')}{secondary_note}）")

    prompt_block = "\n".join(lines) if lines else "（未找到可参考的历史案例）"
    return {"list": citation_list, "prompt_block": prompt_block}
