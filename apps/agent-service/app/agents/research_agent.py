import re

GOAL_PATTERN = re.compile(r"(?P<metric>.+?)从\s*([\d.]+)%\s*(?:提到|提升到|到)\s*(?P<target>[\d.]+)%")


def extract_goal(goal_text: str) -> dict:
    """Turns free-text goals like '把创作者注册转化率从 3.4% 提到 5%' into structured
    parameters the rest of the pipeline can act on. Falls back to a generic metric
    name when the text doesn't match the pattern, rather than guessing numbers."""
    match = GOAL_PATTERN.search(goal_text.replace(" ", ""))
    if match:
        return {
            "metric_name": match.group("metric").strip("把 "),
            "target_pct": float(match.group("target")),
            "raw_goal": goal_text,
        }
    return {"metric_name": "注册转化率", "target_pct": None, "raw_goal": goal_text}
