from .. import config
from .mock_llm import MockLLM
from .openai_compatible import OpenAICompatibleLLM


def get_llm():
    """Interface boundary: swap providers with LLM_PROVIDER, no agent code changes."""
    if config.LLM_PROVIDER == "openai_compatible" and config.LLM_BASE_URL and config.LLM_API_KEY:
        return OpenAICompatibleLLM(
            base_url=config.LLM_BASE_URL,
            api_key=config.LLM_API_KEY,
            model=config.LLM_MODEL,
        )
    return MockLLM()
