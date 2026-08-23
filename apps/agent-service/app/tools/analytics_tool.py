import hashlib
import random

from langfuse import observe

from .base import AnalyticsTool


class MockAnalyticsTool(AnalyticsTool):
    """Stands in for 神策数据 / GrowingIO / 自建埋点+ClickHouse.
    Generates a seeded (reproducible per metric_name), plausible signup funnel."""

    @observe(as_type="tool", name="AnalyticsTool.get_funnel")
    def get_funnel(self, metric_name: str) -> list[dict]:
        seed = int(hashlib.sha256(metric_name.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        landing = rng.randint(9000, 12000)
        cta_click = int(landing * rng.uniform(0.38, 0.48))
        form_start = int(cta_click * rng.uniform(0.85, 0.95))
        form_submit = int(form_start * rng.uniform(0.30, 0.42))  # the real drop-off
        activated = int(form_submit * rng.uniform(0.55, 0.7))

        return [
            {"step": "落地页浏览", "users": landing},
            {"step": "点击注册按钮", "users": cta_click},
            {"step": "开始填写表单", "users": form_start},
            {"step": "提交表单", "users": form_submit},
            {"step": "完成首次激活", "users": activated},
        ]


class RealAnalyticsTool(AnalyticsTool):
    """TODO: wire to 神策数据 / GrowingIO query API. Interface (get_funnel) is
    already what OpportunityAgent expects — only this class needs to change."""

    def __init__(self, base_url: str, api_key: str):
        raise NotImplementedError(
            "Configure ANALYTICS_API_BASE / ANALYTICS_API_KEY and implement the "
            "query call for your analytics vendor's event API."
        )

    def get_funnel(self, metric_name: str) -> list[dict]:
        raise NotImplementedError


def get_analytics_tool() -> AnalyticsTool:
    return MockAnalyticsTool()
