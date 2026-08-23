from ..server import mcp


@mcp.tool
def search_growth_playbook(query: str, top_k: int = 3) -> dict:
    """检索增长案例知识库（RAG）。

    输入一个业务场景或流失环节的简短描述（例如"注册表单转化流失"、"落地页 CTA 优化"），
    返回相关的历史 A/B 测试案例，每条都附带效果数据和来源链接。适合在设计增长实验前
    先查一下有没有类似的历史经验可以参考，避免凭空猜测。

    Args:
        query: 简短的场景描述，用词越贴近"渠道/环节+问题类型"越准（例如"表单转化流失"
            比"为什么用户不填表单呢"这种完整问句效果更好——检索模型对关键词密集的
            短语打分明显更高，见 docs/TECH_STACK.md 的 A/B 测试记录）。
        top_k: 返回案例数量，默认 3。

    Returns:
        {"status": "correct"|"ambiguous"|"wrong"|"unavailable", "citations": [...], "prompt_block": "..."}
        status 为 "wrong" 或 "unavailable" 时 citations 为空，代表没有找到足够相关的案例，
        不代表报错。
    """
    from app.obs import tracing
    from app.rag import retriever

    result = retriever.search(query, top_k=top_k)
    tracing.flush()  # MCP tool calls are their own request-scoped unit of work, same as orchestrator entrypoints
    return result
