from abc import ABC, abstractmethod


class AnalyticsTool(ABC):
    @abstractmethod
    def get_funnel(self, metric_name: str) -> list[dict]:
        """Returns ordered funnel steps: [{step, users}, ...]"""


class FormTool(ABC):
    @abstractmethod
    def get_fields(self, form_id: str) -> list[dict]:
        """Returns [{field_id, label, required, abandonment_rate}, ...]"""

    @abstractmethod
    def update_fields(self, form_id: str, field_ids: list[str]) -> dict:
        """Writes back the approved field set. Returns {ok, form_id, fields}"""


class CRMTool(ABC):
    @abstractmethod
    def get_segments(self) -> list[dict]:
        """Returns [{segment, size, conversion_rate}, ...]"""

    @abstractmethod
    def update_tag(self, segment: str, tag: str) -> dict:
        """Writes an experiment tag back onto a CRM segment."""


class ERPTool(ABC):
    @abstractmethod
    def get_order_stats(self) -> dict:
        """Returns {orders_30d, revenue_30d, avg_order_value}"""


class IMTool(ABC):
    """Shared contract for 企业微信 / 飞书: notify + approval round-trip."""

    @abstractmethod
    def send_message(self, target: str, text: str) -> dict:
        ...

    @abstractmethod
    def create_approval(self, run_id: str, payload: dict) -> str:
        """Returns an approval_id."""

    @abstractmethod
    def get_approval_status(self, approval_id: str) -> str:
        """Returns pending | approved | rejected"""
