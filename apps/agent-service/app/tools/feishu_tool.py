import httpx
from langfuse import observe

from .. import config
from ..db import get_conn, now
from .base import IMTool


class MockFeishuTool(IMTool):
    """No FEISHU_APP_ID/SECRET configured: approval instances live entirely in the
    local `runs` table (status column), and a human approves/rejects from the
    dashboard instead of the real 飞书 approval UI. Same contract either way —
    the orchestrator never knows which one it's talking to."""

    @observe(as_type="tool", name="FeishuTool.send_message")
    def send_message(self, target: str, text: str) -> dict:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO notifications (run_id, channel, content, created_at) VALUES (?, ?, ?, ?)",
                (None, "feishu", f"[to:{target}] {text}", now()),
            )
        return {"ok": True, "mode": "mock"}

    @observe(as_type="tool", name="FeishuTool.create_approval")
    def create_approval(self, run_id: str, payload: dict) -> str:
        # run_id doubles as approval_id: the `runs.status` column IS the approval state.
        return run_id

    @observe(as_type="tool", name="FeishuTool.get_approval_status")
    def get_approval_status(self, approval_id: str) -> str:
        with get_conn() as conn:
            row = conn.execute("SELECT status FROM runs WHERE id = ?", (approval_id,)).fetchone()
        return row["status"] if row else "pending"


class RealFeishuTool(IMTool):
    """Real 飞书开放平台 API client. Activates once FEISHU_APP_ID / FEISHU_APP_SECRET
    are set. create_approval additionally needs FEISHU_APPROVAL_CODE — an approval
    definition must already exist in the 飞书管理后台 (approval flows can't be
    created ad hoc via API, only instances of a predefined flow)."""

    def __init__(self, app_id: str, app_secret: str, approval_code: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.approval_code = approval_code

    @observe(as_type="tool", name="FeishuTool._tenant_access_token")
    def _tenant_access_token(self) -> str:
        resp = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code"):
            raise RuntimeError(f"飞书 tenant_access_token 获取失败: {data}")
        return data["tenant_access_token"]

    @observe(as_type="tool", name="RealFeishuTool.send_message")
    def send_message(self, target: str, text: str) -> dict:
        token = self._tenant_access_token()
        resp = httpx.post(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
            headers={"Authorization": f"Bearer {token}"},
            json={"receive_id": target, "msg_type": "text", "content": f'{{"text":"{text}"}}'},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()

    @observe(as_type="tool", name="RealFeishuTool.create_approval")
    def create_approval(self, run_id: str, payload: dict) -> str:
        if not self.approval_code:
            raise RuntimeError("FEISHU_APPROVAL_CODE 未配置：需先在飞书管理后台创建审批定义")
        token = self._tenant_access_token()
        resp = httpx.post(
            "https://open.feishu.cn/open-apis/approval/v4/instances",
            headers={"Authorization": f"Bearer {token}"},
            json={"approval_code": self.approval_code, "form": payload},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("instance_code", run_id)

    @observe(as_type="tool", name="RealFeishuTool.get_approval_status")
    def get_approval_status(self, approval_id: str) -> str:
        token = self._tenant_access_token()
        resp = httpx.get(
            f"https://open.feishu.cn/open-apis/approval/v4/instances/{approval_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        status = resp.json().get("data", {}).get("status", "PENDING")
        return {"PENDING": "pending", "APPROVED": "approved", "REJECTED": "rejected"}.get(status, "pending")


def get_feishu_tool() -> IMTool:
    if config.FEISHU_APP_ID and config.FEISHU_APP_SECRET:
        return RealFeishuTool(config.FEISHU_APP_ID, config.FEISHU_APP_SECRET, config.FEISHU_APPROVAL_CODE)
    return MockFeishuTool()
