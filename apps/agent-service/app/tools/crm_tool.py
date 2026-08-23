import random

from langfuse import observe

from .base import CRMTool


class MockCRMTool(CRMTool):
    """Stands in for 纷享销客 / 销售易 OpenAPI, or 飞书多维表格 used as a lightweight CRM."""

    @observe(as_type="tool", name="CRMTool.get_segments")
    def get_segments(self) -> list[dict]:
        rng = random.Random(7)
        names = ["新注册创作者", "试用未转化", "高活跃创作者", "流失风险"]
        return [
            {
                "segment": n,
                "size": rng.randint(400, 3000),
                "conversion_rate": round(rng.uniform(0.02, 0.18), 3),
            }
            for n in names
        ]

    @observe(as_type="tool", name="CRMTool.update_tag")
    def update_tag(self, segment: str, tag: str) -> dict:
        # Real impl: POST to CRM vendor's segment/customer tagging endpoint
        return {"ok": True, "segment": segment, "tag": tag}


class RealCRMTool(CRMTool):
    """TODO: implement against your CRM vendor's OpenAPI. Needs CRM_API_BASE / CRM_API_KEY."""

    def __init__(self, base_url: str, api_key: str):
        raise NotImplementedError("Set CRM_API_BASE / CRM_API_KEY and implement the REST calls.")

    def get_segments(self) -> list[dict]:
        raise NotImplementedError

    def update_tag(self, segment: str, tag: str) -> dict:
        raise NotImplementedError


def get_crm_tool() -> CRMTool:
    return MockCRMTool()
