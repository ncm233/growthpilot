from ..server import mcp


@mcp.tool
def propose_experiment(goal: str, budget_limit: float = 10000.0) -> dict:
    """给定一个增长目标，跑完整的 Opportunity -> RAG 检索 -> Experiment -> Critic ->
    Simulation 流程，生成一份带历史案例引用的 A/B 实验方案。

    生成的方案会写入待审批队列（status="pending_approval"）并推送一条审批通知，
    但【不会】自动执行或写回任何业务系统——这个工具只负责"生成方案"，没有能力
    批准、拒绝或让方案生效。批准/拒绝只能由人类在 GrowthPilot Dashboard 上完成，
    这是刻意的设计边界：不把写回动作暴露给任何 MCP 客户端，即使调用方是 LLM
    也无法绕过人工审批这一步。

    Args:
        goal: 自然语言描述的增长目标，例如"把创作者注册转化率从 3.4% 提到 5%"。
        budget_limit: 本次实验的预算上限（人民币）。

    Returns:
        完整的 run 记录：{id, status, opportunity, experiment, critic, simulation, ...}。
        用返回的 id 调用 get_experiment_status 可以跟进后续审批进展。
    """
    from app.planner import orchestrator

    return orchestrator.run_goal(goal, budget_limit)


@mcp.tool
def get_experiment_status(run_id: str) -> dict:
    """查询某次实验提案（由 propose_experiment 生成）的当前状态。

    只读工具，用来确认一份方案是还在等待审批（pending_approval）、已批准
    （approved，代表已经写回系统执行）、还是被拒绝（rejected）。

    Args:
        run_id: propose_experiment 返回结果里的 "id" 字段。

    Returns:
        run 记录；run_id 不存在时返回 {"error": "..."}。
    """
    from app.db import get_conn, row_to_run

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return {"error": f"run_id 不存在：{run_id}"}
    return row_to_run(row)
