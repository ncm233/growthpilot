from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """Agents call narrate() for wording only. All decision logic (which step is the
    opportunity, what the proposed budget is, whether it violates a constraint) is
    computed deterministically upstream and passed in as `context` — the LLM never
    invents numbers, it only explains ones that already exist. This is what the
    Critic Agent's hallucination check verifies against."""

    @abstractmethod
    def narrate(self, task: str, context: dict) -> str:
        ...
