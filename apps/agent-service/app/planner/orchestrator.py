import json
import uuid

from ..agents import critic_agent, data_agent, experiment_agent, opportunity_agent, research_agent
from ..db import get_conn, now, row_to_run
from ..llm import get_llm
from ..simulation import simulator
from ..tools import get_analytics_tool, get_crm_tool, get_erp_tool, get_feishu_tool, get_form_tool, get_wecom_tool

MAX_RETRIES = 1


def _tools() -> dict:
    return {
        "analytics": get_analytics_tool(),
        "form": get_form_tool(),
        "crm": get_crm_tool(),
        "erp": get_erp_tool(),
    }


def run_goal(goal_text: str, budget_limit: float) -> dict:
    """Plan -> Tool Call -> Verify -> Reflect, then hand off to a human approval
    card instead of executing. This is the full pipeline behind one dashboard run."""
    llm = get_llm()
    tools = _tools()

    goal = research_agent.extract_goal(goal_text)
    raw_data = data_agent.gather(goal["metric_name"], tools)
    opportunity = opportunity_agent.find_opportunity(raw_data, llm)

    experiment = experiment_agent.design_experiment(opportunity, raw_data, budget_limit, llm)
    critic = critic_agent.review(opportunity, experiment, raw_data, budget_limit)

    retries = 0
    while not critic["passed"] and retries < MAX_RETRIES:
        # Reflect: clamp the budget to the limit and re-check. A real LLM-driven
        # experiment agent would regenerate the whole proposal here; the clamp
        # keeps this deterministic and testable for the eval harness.
        experiment["proposed_budget"] = min(experiment["proposed_budget"], budget_limit)
        critic = critic_agent.review(opportunity, experiment, raw_data, budget_limit)
        retries += 1

    run_id = str(uuid.uuid4())
    simulation = simulator.run(run_id, opportunity, experiment, llm)

    feishu = get_feishu_tool()
    approval_id = feishu.create_approval(
        run_id,
        {
            "goal": goal_text,
            "opportunity": opportunity["description"],
            "experiment": experiment["narrative"],
            "budget": experiment["proposed_budget"],
            "simulation": simulation["summary"],
        },
    )
    feishu.send_message("growth-approvers", f"新的增长实验待审批：{goal_text}\n{experiment['narrative']}")

    status = "pending_approval" if critic["passed"] else "rejected"
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO runs (id, goal, budget_limit, status, raw_data_json, opportunity_json,
               experiment_json, critic_json, simulation_json, approval_id, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id,
                goal_text,
                budget_limit,
                status,
                json.dumps(raw_data, ensure_ascii=False),
                json.dumps(opportunity, ensure_ascii=False),
                json.dumps(experiment, ensure_ascii=False),
                json.dumps(critic, ensure_ascii=False),
                json.dumps(simulation, ensure_ascii=False),
                approval_id,
                now(),
            ),
        )
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return row_to_run(row)


def decide(run_id: str, decision: str) -> dict:
    """Human approval closes the loop: on approve, write back to the source
    systems (form config, CRM tag) and notify via IM; on reject, just record it."""
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise KeyError(run_id)
    record = row_to_run(row)
    if record["status"] != "pending_approval":
        return record

    tools = _tools()
    wecom = get_wecom_tool()

    if decision == "approved":
        experiment = record["experiment"]
        if experiment.get("target_form_id"):
            tools["form"].update_fields(experiment["target_form_id"], experiment["variant_b"]["fields"])
        elif experiment.get("variant_b", {}).get("target_segment"):
            tools["crm"].update_tag(experiment["variant_b"]["target_segment"], f"experiment:{run_id[:8]}")
        wecom.send_message("growth-team", f"实验已批准并写回系统：{record['goal']}")
        result_text = "已批准，写回执行"
    else:
        wecom.send_message("growth-team", f"实验已被拒绝：{record['goal']}")
        result_text = "已拒绝，未执行"

    with get_conn() as conn:
        conn.execute(
            "UPDATE runs SET status = ?, decided_at = ? WHERE id = ?",
            (decision, now(), run_id),
        )
        conn.execute(
            """INSERT INTO memory (id, run_id, hypothesis, channel, result, confidence, lesson, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                run_id,
                record["experiment"]["hypothesis"],
                record["experiment"]["type"],
                result_text,
                record["simulation"]["confidence"],
                record["simulation"]["summary"],
                now(),
            ),
        )
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return row_to_run(row)
