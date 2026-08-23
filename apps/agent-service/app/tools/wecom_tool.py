import httpx

from .. import config
from ..db import get_conn, now
from .base import IMTool


class MockWecomTool(IMTool):
    """No WECOM_CORP_ID/SECRET configured: writes notifications to the local DB
    instead of actually calling 企业微信, so the write-back step is still visible
    end-to-end in the dashboard."""

    def send_message(self, target: str, text: str) -> dict:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO notifications (run_id, channel, content, created_at) VALUES (?, ?, ?, ?)",
                (None, "wecom", f"[to:{target}] {text}", now()),
            )
        return {"ok": True, "mode": "mock"}

    def create_approval(self, run_id: str, payload: dict) -> str:
        # 企业微信 approval flow is not used in this demo — 飞书 carries the approval
        # story. Kept here only to satisfy the shared IMTool interface.
        return run_id

    def get_approval_status(self, approval_id: str) -> str:
        return "pending"


class RealWecomTool(IMTool):
    """Real 企业微信 API client. Activates automatically once WECOM_CORP_ID /
    WECOM_SECRET / WECOM_AGENT_ID are set. Endpoints are the documented
    self-built-app API: gettoken + message/send."""

    def __init__(self, corp_id: str, secret: str, agent_id: str):
        self.corp_id = corp_id
        self.secret = secret
        self.agent_id = agent_id

    def _access_token(self) -> str:
        resp = httpx.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={"corpid": self.corp_id, "corpsecret": self.secret},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode"):
            raise RuntimeError(f"企业微信 gettoken 失败: {data}")
        return data["access_token"]

    def send_message(self, target: str, text: str) -> dict:
        token = self._access_token()
        resp = httpx.post(
            f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}",
            json={
                "touser": target,
                "msgtype": "text",
                "agentid": int(self.agent_id),
                "text": {"content": text},
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()

    def create_approval(self, run_id: str, payload: dict) -> str:
        return run_id

    def get_approval_status(self, approval_id: str) -> str:
        return "pending"


def get_wecom_tool() -> IMTool:
    if config.WECOM_CORP_ID and config.WECOM_SECRET and config.WECOM_AGENT_ID:
        return RealWecomTool(config.WECOM_CORP_ID, config.WECOM_SECRET, config.WECOM_AGENT_ID)
    return MockWecomTool()
