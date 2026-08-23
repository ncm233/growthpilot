import random

from .base import ERPTool


class MockERPTool(ERPTool):
    """Stands in for 用友 / 金蝶开放平台. Not on the critical path of the signup-funnel
    demo yet, but wired into the architecture for when Opportunity Agent needs
    order/revenue context (e.g. paid-plan conversion experiments)."""

    def get_order_stats(self) -> dict:
        rng = random.Random(3)
        return {
            "orders_30d": rng.randint(800, 1500),
            "revenue_30d": round(rng.uniform(300000, 600000), 2),
            "avg_order_value": round(rng.uniform(280, 420), 2),
        }


class RealERPTool(ERPTool):
    """TODO: implement against 用友/金蝶开放平台. Needs ERP_API_BASE / ERP_API_KEY."""

    def __init__(self, base_url: str, api_key: str):
        raise NotImplementedError("Set ERP_API_BASE / ERP_API_KEY and implement the REST calls.")

    def get_order_stats(self) -> dict:
        raise NotImplementedError


def get_erp_tool() -> ERPTool:
    return MockERPTool()
