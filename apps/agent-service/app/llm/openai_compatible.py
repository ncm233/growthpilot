import json

import httpx

from .base import BaseLLM

TASK_PROMPTS = {
    "opportunity": (
        "你是增长分析师。根据以下结构化漏斗数据，用一句中文说明流失最严重的环节，"
        "不要编造数据中没有的数字。如果 reference_cases 里有历史案例，可以简要引用作为参考，"
        "但不要虚构 reference_cases 之外的案例或数字：\n{context}"
    ),
    "experiment": (
        "你是增长实验设计师。根据以下结构化实验参数，用中文写一段简短的实验说明，"
        "不要编造数据中没有的数字。如果 reference_cases 里有历史案例，可以简要引用作为参考，"
        "但不要虚构 reference_cases 之外的案例或数字：\n{context}"
    ),
    "simulation_summary": "你是数据分析师。根据以下模拟结果，用中文总结预期效果和置信度，并提醒这只是排序参考不是真实结果：\n{context}",
}


class OpenAICompatibleLLM(BaseLLM):
    """Real HTTP client against any OpenAI-compatible /chat/completions endpoint —
    DeepSeek, DashScope (Qwen), Moonshot, Zhipu GLM all support this shape.
    Activated automatically once LLM_BASE_URL + LLM_API_KEY are set."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def narrate(self, task: str, context: dict) -> str:
        prompt_template = TASK_PROMPTS.get(task, "请描述以下数据：\n{context}")
        prompt = prompt_template.format(context=json.dumps(context, ensure_ascii=False))
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
