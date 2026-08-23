"""Eval harness for GrowthPilot's deterministic guardrails: Critic Agent and
the Simulation layer's direction signal.

Two suites, reported separately (see docs/EVALUATION.md for why they must
stay separate rather than being blended into one score):

  BASELINE  — synthetic funnels + obviously-wrong injected violations
              (budget 10-80% over limit, numbers off by 50-500 users).
              Tests: does Critic catch OBVIOUS problems at all.

  ADVERSARIAL — edge cases chosen by reading critic_agent.py's actual logic
              and asking "what would slip through a check phrased exactly
              like this". Tests: does Critic catch SUBTLE problems, and does
              it avoid false-positiving on legitimate boundary cases.
              One of these (growth-framed-as-a-drop) found a real bug in
              critic_agent.py, since fixed — see git log.

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

N_BASELINE_CASES = 60
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


def run_baseline(rng: random.Random) -> dict:
    opp_correct = 0
    budget_violations_caught = 0
    budget_violations_total = 0
    budget_false_positives = 0
    budget_valid_total = 0
    hallucinations_caught = 0
    hallucinations_total = 0
    sim_direction_correct = 0
    sim_direction_total = 0

    for i in range(N_BASELINE_CASES):
        raw_data = {"funnel": make_funnel(rng), "form_fields": [], "segments": [], "erp": {}}

        opp = opportunity_agent.find_opportunity(raw_data, LLM)
        gt_from, gt_to = independent_ground_truth(raw_data["funnel"])
        if opp["from_step"] == gt_from and opp["to_step"] == gt_to:
            opp_correct += 1

        budget_limit = rng.uniform(4000, 12000)

        valid_experiment = {"type": "form_simplification", "proposed_budget": budget_limit * rng.uniform(0.5, 0.95)}
        result = critic_agent.review(opp, valid_experiment, raw_data, budget_limit)
        budget_valid_total += 1
        if not result["passed"]:
            budget_false_positives += 1

        bad_experiment = {"type": "form_simplification", "proposed_budget": budget_limit * rng.uniform(1.1, 1.8)}
        result = critic_agent.review(opp, bad_experiment, raw_data, budget_limit)
        budget_violations_total += 1
        if not result["passed"]:
            budget_violations_caught += 1

        tampered_opp = dict(opp)
        tampered_opp["from_users"] = opp["from_users"] + rng.randint(50, 500)
        result = critic_agent.review(tampered_opp, valid_experiment, raw_data, budget_limit)
        hallucinations_total += 1
        if not result["passed"]:
            hallucinations_caught += 1

        # Ground truth: our synthetic funnels always have a real drop (drop_rate > 0),
        # and the proposed fix always targets that drop, so the expected direction
        # is always positive by construction — see docs/EVALUATION.md for why this
        # particular metric is closer to a regression sanity-check than a
        # discriminative eval, and shouldn't be read as "93% accurate simulation".
        sim = simulator.run(f"bench-{i}", opp, valid_experiment, LLM, n_personas=200)
        sim_direction_total += 1
        if sim["direction"] == "positive":
            sim_direction_correct += 1

    return {
        "n_cases": N_BASELINE_CASES,
        "opportunity_detection_accuracy": round(opp_correct / N_BASELINE_CASES, 4),
        "budget_constraint_catch_rate": round(budget_violations_caught / budget_violations_total, 4),
        "budget_constraint_false_positive_rate": round(budget_false_positives / budget_valid_total, 4),
        "hallucination_catch_rate": round(hallucinations_caught / hallucinations_total, 4),
        "simulation_direction_accuracy": round(sim_direction_correct / sim_direction_total, 4),
    }


# ============================================================
# Adversarial suite — each case is (name, expect_pass, build_fn)
# build_fn(rng) -> (opportunity, experiment, raw_data, budget_limit)
# expect_pass tells us what critic_agent.review()["passed"] SHOULD be.
# ============================================================


def _case_budget_exact_limit(rng):
    """Boundary: proposed_budget == budget_limit exactly. Should PASS —
    the check is `>`, not `>=`. Verifies no off-by-one on the boundary."""
    limit = round(rng.uniform(4000, 12000), 2)
    raw_data = {"funnel": [{"step": "A", "users": 1000}, {"step": "B", "users": 400}]}
    opp = {"from_step": "A", "to_step": "B", "from_users": 1000, "to_users": 400, "drop_rate": 0.6}
    exp = {"proposed_budget": limit}
    return opp, exp, raw_data, limit


def _case_budget_one_cent_over(rng):
    """Boundary: proposed_budget == budget_limit + 0.01. Should be CAUGHT —
    tests the tolerance (1e-6) is tight enough to catch a real cent-level
    overage rather than being so loose it masks small violations."""
    limit = round(rng.uniform(4000, 12000), 2)
    raw_data = {"funnel": [{"step": "A", "users": 1000}, {"step": "B", "users": 400}]}
    opp = {"from_step": "A", "to_step": "B", "from_users": 1000, "to_users": 400, "drop_rate": 0.6}
    exp = {"proposed_budget": limit + 0.01}
    return opp, exp, raw_data, limit


def _case_budget_one_cent_under(rng):
    """Boundary: proposed_budget == budget_limit - 0.01. Should PASS —
    the mirror of the above, checking no false-positive right below the line."""
    limit = round(rng.uniform(4000, 12000), 2)
    raw_data = {"funnel": [{"step": "A", "users": 1000}, {"step": "B", "users": 400}]}
    opp = {"from_step": "A", "to_step": "B", "from_users": 1000, "to_users": 400, "drop_rate": 0.6}
    exp = {"proposed_budget": limit - 0.01}
    return opp, exp, raw_data, limit


def _case_growth_framed_as_drop(rng):
    """The bug this eval suite found: to_users > from_users (a net GAIN)
    packaged as if it were the worst drop, with self-consistent numbers.
    Should be CAUGHT — see the drop_rate<=0 check added to critic_agent.py."""
    from_u = rng.randint(500, 2000)
    to_u = from_u + rng.randint(100, 800)
    raw_data = {"funnel": [{"step": "A", "users": from_u}, {"step": "B", "users": to_u}]}
    drop_rate = round(1 - (to_u / from_u), 4)
    opp = {"from_step": "A", "to_step": "B", "from_users": from_u, "to_users": to_u, "drop_rate": drop_rate}
    exp = {"proposed_budget": 5000.0}
    return opp, exp, raw_data, 10000.0


def _case_flat_step_zero_drop(rng):
    """Edge case: from_users == to_users, drop_rate == 0 exactly. Not a
    violation (0 <= 0 boundary on the new check uses <=, so this SHOULD be
    caught too — a flat step is not a meaningful 'opportunity' either).
    Verifies the <= 0 boundary (not < 0) behaves as intended."""
    n = rng.randint(500, 2000)
    raw_data = {"funnel": [{"step": "A", "users": n}, {"step": "B", "users": n}]}
    opp = {"from_step": "A", "to_step": "B", "from_users": n, "to_users": n, "drop_rate": 0.0}
    exp = {"proposed_budget": 5000.0}
    return opp, exp, raw_data, 10000.0


def _case_phantom_step_reference(rng):
    """opportunity references a step name that doesn't exist in raw_data's
    funnel at all (e.g. a stale reference after the funnel was regenerated).
    Should be CAUGHT via the from_users/to_users mismatch check."""
    raw_data = {"funnel": [{"step": "A", "users": 1000}, {"step": "B", "users": 400}]}
    opp = {"from_step": "A", "to_step": "C_不存在", "from_users": 1000, "to_users": 400, "drop_rate": 0.6}
    exp = {"proposed_budget": 5000.0}
    return opp, exp, raw_data, 10000.0


def _case_subtle_one_percent_drift(rng):
    """Numeric drift small enough to plausibly be 'rounding', not the
    original test's 50-500 absolute drift (easy to catch). Tests whether the
    1e-6/1e-4 tolerances are tight enough to still catch a ~1% relative
    drift rather than treating it as noise. Should be CAUGHT."""
    from_u = rng.randint(2000, 5000)
    to_u = int(from_u * rng.uniform(0.3, 0.6))
    raw_data = {"funnel": [{"step": "A", "users": from_u}, {"step": "B", "users": to_u}]}
    true_drop = round(1 - (to_u / from_u), 4)
    drifted_from = int(from_u * 1.01)  # 1% drift — not huge, but not float noise either
    opp = {"from_step": "A", "to_step": "B", "from_users": drifted_from, "to_users": to_u, "drop_rate": true_drop}
    exp = {"proposed_budget": 5000.0}
    return opp, exp, raw_data, 10000.0


ADVERSARIAL_CASES = [
    ("budget_exact_limit", True, _case_budget_exact_limit),
    ("budget_one_cent_over", False, _case_budget_one_cent_over),
    ("budget_one_cent_under", True, _case_budget_one_cent_under),
    ("growth_framed_as_drop", False, _case_growth_framed_as_drop),
    ("flat_step_zero_drop", False, _case_flat_step_zero_drop),
    ("phantom_step_reference", False, _case_phantom_step_reference),
    ("subtle_one_percent_drift", False, _case_subtle_one_percent_drift),
]
N_ADVERSARIAL_REPEATS = 4  # each case re-run with different random numbers


def run_adversarial(rng: random.Random) -> dict:
    per_case = {}
    total = 0
    correct = 0
    failures = []

    for name, expect_pass, build_fn in ADVERSARIAL_CASES:
        case_correct = 0
        for _ in range(N_ADVERSARIAL_REPEATS):
            opp, exp, raw_data, budget_limit = build_fn(rng)
            result = critic_agent.review(opp, exp, raw_data, budget_limit)
            ok = result["passed"] == expect_pass
            total += 1
            if ok:
                correct += 1
                case_correct += 1
            else:
                failures.append(
                    {
                        "case": name,
                        "expected_pass": expect_pass,
                        "actual_pass": result["passed"],
                        "issues": result["issues"],
                    }
                )
        per_case[name] = round(case_correct / N_ADVERSARIAL_REPEATS, 4)

    return {
        "n_cases": total,
        "accuracy": round(correct / total, 4),
        "per_case_accuracy": per_case,
        "failures": failures,
    }


def run():
    rng = random.Random(1234)
    baseline = run_baseline(rng)

    rng2 = random.Random(5678)
    adversarial = run_adversarial(rng2)

    report = {"baseline": baseline, "adversarial": adversarial}

    out_path = os.path.join(os.path.dirname(__file__), "report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    run()
