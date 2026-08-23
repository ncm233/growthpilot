import math
from abc import ABC, abstractmethod


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        """candidates come from store.hybrid_search(); each must carry a
        'search_text' field. Returns the top_k candidates, each annotated with
        '_rerank_score' (higher = more relevant), sorted descending."""


class MockReranker(BaseReranker):
    """No-op: keeps the LanceDB RRF fusion order as-is, copies the RRF score
    into _rerank_score. Zero dependencies. Not a quality stand-in — like
    MockLLM, it exists so the pipeline runs offline, not to approximate real
    reranking. retriever.py's CRAG-style grading treats Mock-mode results as
    always 'correct' (see retriever.py) rather than trying to calibrate
    thresholds against a meaningless score."""

    def rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        out = []
        for c in candidates:
            c = dict(c)
            c["_rerank_score"] = c.get("_relevance_score", 1.0)
            out.append(c)
        return out[:top_k]


class SiliconFlowReranker(BaseReranker):
    """BAAI/bge-reranker-v2-m3 via SiliconFlow's hosted /v1/rerank API.
    No local model download. See SiliconFlowEmbedder for the same tradeoff:
    zero-download convenience against depending on a third-party service."""

    # Same caching rationale as SiliconFlowEmbedder._query_cache — module-
    # level because a fresh instance is built per retriever.search() call.
    # Keyed by (model, query, candidate id set): the reranker's output is a
    # pure function of the query and which documents it's scoring against,
    # not their input order — the LanceDB hybrid_search order upstream can
    # vary run to run without changing what a cache hit should return.
    _cache: dict[tuple, list[dict]] = {}
    cache_hits = 0
    cache_misses = 0

    def __init__(self, api_key: str, model: str = "BAAI/bge-reranker-v2-m3"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.siliconflow.cn/v1"

    def rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        if not candidates:
            return []

        cache_key = (self.model, query, top_k, tuple(sorted(c["id"] for c in candidates)))
        cached = SiliconFlowReranker._cache.get(cache_key)
        if cached is not None:
            SiliconFlowReranker.cache_hits += 1
            return cached
        SiliconFlowReranker.cache_misses += 1

        import httpx

        docs = [c["search_text"] for c in candidates]
        resp = httpx.post(
            f"{self.base_url}/rerank",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "query": query, "documents": docs, "top_n": top_k},
            timeout=30.0,
        )
        resp.raise_for_status()
        results = resp.json()["results"]  # already sorted by relevance_score desc
        out = []
        for r in results:
            c = dict(candidates[r["index"]])
            c["_rerank_score"] = r["relevance_score"]
            out.append(c)
        SiliconFlowReranker._cache[cache_key] = out
        return out


class BgeReranker(BaseReranker):
    """BAAI/bge-reranker-base cross-encoder, local CPU inference, ~1.1GB model
    pulled from HuggingFace on first use. Cross-encoders score a (query,
    document) pair jointly instead of comparing independent embeddings, which
    is why this step catches relevance that vector similarity alone misses —
    and why it's used to rerank a shortlist rather than search the whole
    corpus (it's O(n) forward passes, not an index lookup)."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        from sentence_transformers import CrossEncoder  # heavy import, deferred

        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        if not candidates:
            return []
        pairs = [(query, c["search_text"]) for c in candidates]
        raw_scores = self._model.predict(pairs)
        out = []
        for c, raw in zip(candidates, raw_scores):
            c = dict(c)
            c["_rerank_score"] = 1 / (1 + math.exp(-float(raw)))  # sigmoid -> comparable [0,1] range
            out.append(c)
        out.sort(key=lambda c: c["_rerank_score"], reverse=True)
        return out[:top_k]


def get_reranker() -> BaseReranker:
    from .. import config

    if config.RERANKER_PROVIDER == "siliconflow" and config.SILICONFLOW_API_KEY:
        return SiliconFlowReranker(config.SILICONFLOW_API_KEY, config.SILICONFLOW_RERANK_MODEL)
    if config.RERANKER_PROVIDER == "bge":
        return BgeReranker()
    return MockReranker()
