from langfuse import observe

from . import citations as citations_mod
from . import store
from .embedder import get_embedder
from .reranker import BaseReranker, MockReranker, get_reranker

CANDIDATE_K = 20

# CRAG-style grading (Correct / Ambiguous / Wrong) on the top reranked score.
# Calibrated for a real cross-encoder's [0,1] relevance score (BgeReranker's
# sigmoid output or SiliconFlowReranker's API relevance_score — same
# bge-reranker family, comparable range). MockReranker skips grading entirely
# (see _grade below) because its score is just the RRF fusion rank, not a
# relevance judgment — thresholding a meaningless number would just be
# theater. These thresholds are a starting point, not a validated constant:
# Phase 3's 50-question retrieval testset is what should actually tune them.
CORRECT_THRESHOLD = 0.5
AMBIGUOUS_THRESHOLD = 0.2


def _grade(reranker: BaseReranker, top_score: float) -> str:
    if isinstance(reranker, MockReranker):
        return "correct"
    if top_score >= CORRECT_THRESHOLD:
        return "correct"
    if top_score >= AMBIGUOUS_THRESHOLD:
        return "ambiguous"
    return "wrong"


def _empty_result(reason: str) -> dict:
    return {"status": "unavailable", "reason": reason, "citations": [], "prompt_block": "（未找到可参考的历史案例）"}


@observe(as_type="retriever")
def search(query: str, top_k: int = 3, embedder=None, reranker=None) -> dict:
    """Hybrid search -> cross-encoder rerank -> CRAG-style grade -> citations.
    Never raises: any failure (RAG deps not installed, corpus not ingested
    yet, empty corpus) degrades to an empty-but-valid result so callers
    (opportunity_agent / experiment_agent) can always proceed without RAG
    rather than crashing the whole run.

    embedder/reranker default to the .env-configured provider (get_embedder()
    / get_reranker()) but can be passed explicitly — used by
    packages/eval/retrieval_eval.py to run several provider combinations in
    one process without touching .env between runs."""
    import jieba

    try:
        embedder = embedder or get_embedder()
        reranker = reranker or get_reranker()
        query_vec = embedder.embed_query(query)
        query_tokens = " ".join(jieba.lcut(query))
        hits = store.hybrid_search(query_tokens, query_vec, limit=CANDIDATE_K)
    except ImportError as e:
        return _empty_result(f"RAG 依赖未安装：{e}（运行 pip install -r requirements-rag.txt 启用真实检索）")
    except RuntimeError as e:
        return _empty_result(str(e))

    if not hits:
        return _empty_result("语料库为空或未匹配到任何案例")

    reranked = reranker.rerank(query, hits, top_k=top_k)
    top_score = reranked[0]["_rerank_score"] if reranked else 0.0
    status = _grade(reranker, top_score)

    if status == "wrong":
        return {"status": "wrong", "citations": [], "prompt_block": "（检索到的案例相关性过低，未采用）"}

    formatted = citations_mod.format_citations(reranked)
    return {"status": status, "citations": formatted["list"], "prompt_block": formatted["prompt_block"]}
