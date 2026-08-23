import random
import statistics
import zlib


def run(run_id: str, opportunity: dict, experiment: dict, llm, n_personas: int = 500) -> dict:
    """AgentA/B-style pre-flight simulation: NOT a prediction of the real effect
    size, only a direction + confidence signal used to rank experiment ideas before
    spending real budget/traffic on them. Seeded per run_id for reproducibility."""
    seed = zlib.crc32(run_id.encode())
    rng = random.Random(seed)

    baseline_rate = opportunity["to_users"] / opportunity["from_users"]
    effect_size = min(opportunity["drop_rate"] * 0.35, 0.25)

    lifts = [effect_size + rng.gauss(0, 0.05) for _ in range(n_personas)]
    lifts.sort()
    lift_low = lifts[int(0.1 * n_personas)]
    lift_high = lifts[int(0.9 * n_personas)]
    mean_lift = statistics.mean(lifts)
    std_lift = statistics.pstdev(lifts)
    confidence = max(0.0, min(1.0, 1 - (std_lift / (abs(mean_lift) + 1e-6)) * 0.3))

    result = {
        "n_personas": n_personas,
        "baseline_rate": round(baseline_rate, 4),
        "lift_low": round(lift_low, 4),
        "lift_high": round(lift_high, 4),
        "mean_lift": round(mean_lift, 4),
        "confidence": round(confidence, 3),
        "direction": "positive" if mean_lift > 0 else "negative",
    }
    result["summary"] = llm.narrate("simulation_summary", result)
    return result
