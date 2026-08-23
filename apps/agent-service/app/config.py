import os
from dotenv import load_dotenv

load_dotenv()


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


LLM_PROVIDER = env("LLM_PROVIDER", "mock")
LLM_BASE_URL = env("LLM_BASE_URL")
LLM_API_KEY = env("LLM_API_KEY")
LLM_MODEL = env("LLM_MODEL", "deepseek-chat")

EMBEDDER_PROVIDER = env("EMBEDDER_PROVIDER", "mock")  # mock | siliconflow | bge
RERANKER_PROVIDER = env("RERANKER_PROVIDER", "mock")  # mock | siliconflow | bge

SILICONFLOW_API_KEY = env("SILICONFLOW_API_KEY")
SILICONFLOW_EMBEDDING_MODEL = env("SILICONFLOW_EMBEDDING_MODEL", "BAAI/bge-m3")
SILICONFLOW_RERANK_MODEL = env("SILICONFLOW_RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

WECOM_CORP_ID = env("WECOM_CORP_ID")
WECOM_SECRET = env("WECOM_SECRET")
WECOM_AGENT_ID = env("WECOM_AGENT_ID")

FEISHU_APP_ID = env("FEISHU_APP_ID")
FEISHU_APP_SECRET = env("FEISHU_APP_SECRET")
FEISHU_APPROVAL_CODE = env("FEISHU_APPROVAL_CODE")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "growthpilot.db")
