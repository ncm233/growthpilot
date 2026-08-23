import hashlib
from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Document-side embedding, used at ingest time."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Query-side embedding. Kept separate from embed() because bge models
        are asymmetric: queries need an instruction prefix, documents don't."""


class MockEmbedder(BaseEmbedder):
    """Deterministic character-n-gram hashing, zero ML dependencies, runs
    instantly offline. Retrieval quality is real-but-crude (shared substrings
    score higher, no actual semantics) — this exists so the ingest/store/
    retrieve pipeline is testable and the app boots with no extra installs,
    same role MockLLM plays for the LLM layer. Swap EMBEDDER_PROVIDER=bge for
    real semantic search."""

    dim = 64

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._hash_vector(text)

    def _hash_vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = text.split() or [text]
        for tok in tokens:
            for n in (2, 3):
                for i in range(max(len(tok) - n + 1, 1)):
                    gram = tok[i : i + n]
                    h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
                    vec[h % self.dim] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


class SiliconFlowEmbedder(BaseEmbedder):
    """BAAI/bge-m3 via SiliconFlow's hosted API (OpenAI-compatible /v1/embeddings).
    No local model download, no torch — just an HTTP call, same dependency
    footprint as OpenAICompatibleLLM. Trades "no download" for "depends on a
    third-party service being up and rate limits" — the honest tradeoff
    against BgeEmbedder, see docs/TECH_STACK.md."""

    dim = 1024  # bge-m3 output dim; informational only, not schema-enforced

    def __init__(self, api_key: str, model: str = "BAAI/bge-m3"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.siliconflow.cn/v1"

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        resp = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": texts, "encoding_format": "float"},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        data.sort(key=lambda d: d["index"])  # API doesn't guarantee input order in response
        return [d["embedding"] for d in data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class BgeEmbedder(BaseEmbedder):
    """BAAI/bge-small-zh-v1.5 via sentence-transformers, local CPU inference,
    ~100MB model pulled from HuggingFace on first use. See docs/TECH_STACK.md
    for why this size was chosen over bge-m3."""

    dim = 512
    QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        from sentence_transformers import SentenceTransformer  # heavy import, deferred

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(list(texts), normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(self.QUERY_INSTRUCTION + text, normalize_embeddings=True).tolist()


def get_embedder() -> BaseEmbedder:
    from .. import config

    if config.EMBEDDER_PROVIDER == "siliconflow" and config.SILICONFLOW_API_KEY:
        return SiliconFlowEmbedder(config.SILICONFLOW_API_KEY, config.SILICONFLOW_EMBEDDING_MODEL)
    if config.EMBEDDER_PROVIDER == "bge":
        return BgeEmbedder()
    return MockEmbedder()
