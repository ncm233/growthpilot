from langfuse import observe

from .base import FormTool

_FIELDS = [
    {"field_id": "name", "label": "姓名", "required": True, "abandonment_rate": 0.02},
    {"field_id": "email", "label": "邮箱", "required": True, "abandonment_rate": 0.05},
    {"field_id": "phone", "label": "手机号", "required": True, "abandonment_rate": 0.09},
    {"field_id": "company", "label": "公司名称", "required": False, "abandonment_rate": 0.22},
    {"field_id": "role", "label": "职位", "required": False, "abandonment_rate": 0.18},
    {"field_id": "referral", "label": "了解渠道", "required": False, "abandonment_rate": 0.15},
    {"field_id": "agree_terms", "label": "同意服务条款", "required": True, "abandonment_rate": 0.03},
]


class MockFormTool(FormTool):
    """Stands in for 金数据 / 腾讯问卷 / 自建表单系统."""

    @observe(as_type="tool", name="FormTool.get_fields")
    def get_fields(self, form_id: str) -> list[dict]:
        return [dict(f) for f in _FIELDS]

    @observe(as_type="tool", name="FormTool.update_fields")
    def update_fields(self, form_id: str, field_ids: list[str]) -> dict:
        # Real impl: PUT https://jinshuju.net/api/v1/forms/{form_id}/fields with API token
        return {"ok": True, "form_id": form_id, "fields": field_ids}


class RealFormTool(FormTool):
    """TODO: implement against 金数据 API (or your form vendor). Needs FORM_API_TOKEN."""

    def __init__(self, api_token: str):
        raise NotImplementedError("Set FORM_API_TOKEN and implement the 金数据 REST calls.")

    def get_fields(self, form_id: str) -> list[dict]:
        raise NotImplementedError

    def update_fields(self, form_id: str, field_ids: list[str]) -> dict:
        raise NotImplementedError


def get_form_tool() -> FormTool:
    return MockFormTool()
