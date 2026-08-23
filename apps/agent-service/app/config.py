import os
from dotenv import load_dotenv

load_dotenv()


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


LLM_PROVIDER = env("LLM_PROVIDER", "mock")
LLM_BASE_URL = env("LLM_BASE_URL")
LLM_API_KEY = env("LLM_API_KEY")
LLM_MODEL = env("LLM_MODEL", "deepseek-chat")

WECOM_CORP_ID = env("WECOM_CORP_ID")
WECOM_SECRET = env("WECOM_SECRET")
WECOM_AGENT_ID = env("WECOM_AGENT_ID")

FEISHU_APP_ID = env("FEISHU_APP_ID")
FEISHU_APP_SECRET = env("FEISHU_APP_SECRET")
FEISHU_APPROVAL_CODE = env("FEISHU_APPROVAL_CODE")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "growthpilot.db")
