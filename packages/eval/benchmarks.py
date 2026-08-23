"""Eval harness for the four metrics named in the interview guide:
  1. opportunity detection accuracy
  2. budget constraint adherence (critic catch rate on injected violations)
  3. metric-hallucination catch rate (critic catch rate on tampered claims)
  4. simulation direction accuracy

These test the Critic Agent and Simulation layer against ADVERSARIAL synthetic
inputs (deliberately-violating / deliberately-tampered proposals), not just the
normal pipeline — the normal pipeline is constructed to never violate its own
constraints, so testing only the happy path would be a tautology.

Run from this directory: python benchmarks.py
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "agent-service"))

from app.agents import critic_agent, opportunity_agent  # noqa: E402
from app.llm.mock_llm import MockLLM  # noqa: E402
from app.simulation import simulator  # noqa: E402

N_CASES = 60
LLM = MockLLM()


def make_funnel(rng: random.Random) -> list[dict]:
    landing = rng.randint(6000, 14000)
    step2 = int(landing * rng.uniform(0.30, 0.55))
    step3 = int(step2 * rng.uniform(0.75, 0.95))
    step4 = int(step3 * rng.uniform(0.25, 0.60))
    step5 = int(step4 * rng.uniform(0.5, 0.75))
    return [
        {"step": "落地页浏览", "users": landing},
        {"step": "点击注册按钮", "users": step2},
        {"step": "开始填写表单", "users": step3},
        {"step": "提交表单", "users": step4},
        {"step": "完成首次激活", "users": step5},
    ]


def independent_ground_truth(funnel: list[dict]) -> tuple[str, str]:
    """Recomputes the max-drop step with a deliberately different code path
    (manual max-tracking loop vs opportunity_agent's own loop) so the check
    isn't just re-running the same line of code against itself."""
    rates = []
    for i in range(len(funnel) - 1):
        a, b = funnel[i], funnel[i + 1]
        rates.append((a["step"], b["step"], 1 - b["users"] / a["users"]))
    best = rates[0]
    for r in rates[1:]:
        if r[2] > best[2]:
            best = r
    return best[0], best[1]


def run():
    rng = random.Random(1234)

    opp_correct = 0
    budget_violations_caught = 0
    budget_violations_total = 0
    budget_false_positives = 0
    budget_valid_total = 0
    hallucinations_caught = 0
    hallucinations_total = 0
    sim_direction_correct = 0
    sim_direction_total = 0

    for i in range(N_CASES):
        raw_data = {"funnel": make_funnel(rng), "form_fields": [], "segments": [], "erp": {}}

        # --- 1. opportunity detection accuracy ---
        opp = opportunity_agent.find_opportunity(raw_data, LLM)
        gt_from, gt_to = independent_ground_truth(raw_data["funnel"])
        if opp["from_step"] == gt_from and opp["to_step"] == gt_to:
            opp_correct += 1

        budget_limit = rng.uniform(4000, 12000)

        # --- 2. budget constraint adherence: valid case ---
        valid_experiment = {
            "type": "form_simplification",
            "proposed_budget": budget_limit * rng.uniform(0.5, 0.95),
        }
        result = critic_agent.review(opp, valid_experiment, raw_data, budget_limit)
        budget_valid_total += 1
        if not result["passed"]:
            budget_false_positives += 1

        # --- 2b. budget constraint adherence: deliberately-violating case ---
        bad_experiment = {
            "type": "form_simplification",
            "proposed_budget": budget_limit * rng.uniform(1.1, 1.8),
        }
        result = critic_agent.review(opp, bad_experiment, raw_data, budget_limit)
        budget_violations_total += 1
        if not result["passed"]:
            budget_violations_caught += 1

        # --- 3. hallucination catch rate: tamper the opportunity's numbers ---
        tampered_opp = dict(opp)
        tampered_opp["from_users"] = opp["from_users"] + rng.randint(50, 500)
        result = critic_agent.review(tampered_opp, valid_experiment, raw_data, budget_limit)
        hallucinations_total += 1
        if not result["passed"]:
            hallucinations_caught += 1

        # --- 4. simulation direction accuracy ---
        # Ground truth: our synthetic funnels always have a real drop (drop_rate > 0),
        # and the proposed fix always targets that drop, so the expected direction
        # is always positive by construction.
        sim = simulator.run(f"bench-{i}", opp, valid_experiment, LLM, n_personas=200)
        sim_direction_total += 1
        if sim["direction"] == "positive":
            sim_direction_correct += 1

    report = {
        "n_cases": N_CASES,
        "opportunity_detection_accuracy": round(opp_correct / N_CASES, 4),
        "budget_constraint_catch_rate": round(budget_violations_caught / budget_violations_total, 4),
        "budget_constraint_false_positive_rate": round(budget_false_positives / budget_valid_total, 4),
        "hallucination_catch_rate": round(hallucinations_caught / hallucinations_total, 4),
        "simulation_direction_accuracy": round(sim_direction_correct / sim_direction_total, 4),
    }

    out_path = os.path.join(os.path.dirname(__file__), "report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    run()
