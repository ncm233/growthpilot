"""Retrieval quality eval: recall@k / MRR against a hand-labeled testset,
compared across embedder/reranker provider combinations.

Testset scale is honest about where it stands: 20 queries against an 8-case
corpus (packages/corpus/curated/seed_cases.jsonl), not the 50-question /
150-300-case target from docs/CORPUS_SOURCES.md — this script and its
metrics are exactly what should keep running as the corpus grows toward
that target, not a one-off. See docs/EVALUATION.md for the numbers this
produced and what to do as the corpus scales up.

Run from apps/agent-service (needs its venv + the `app` package on path):
    cd apps/agent-service
    set PYTHONPATH=.
    .venv\\Scripts\\python -m ..\\..\\packages\\eval\\retrieval_eval    (won't work as -m across dirs)
or simply:
    cd apps/agent-service
    set PYTHONPATH=.
    .venv\\Scripts\\python ..\\..\\packages\\eval\\retrieval_eval.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "agent-service"))

from app.obs import tracing  # noqa: E402
from app.rag import retriever, store  # noqa: E402
from app.rag.embedder import MockEmbedder, SiliconFlowEmbedder  # noqa: E402
from app.rag.ingest import _search_text, load_corpus  # noqa: E402
from app.rag.reranker import MockReranker, SiliconFlowReranker  # noqa: E402

# (query, [relevant_ids]) — a case can have more than one acceptable relevant
# id when two corpus cases are genuinely close (e.g. exp-0002 vs exp-0003 are
# both about link-color testing; a query that doesn't specify "search results
# page" vs "product UI" can't be blamed for surfacing either).
TESTSET = [
    ("落地页按钮颜色测试", ["exp-0001"]),
    ("红色按钮点击率", ["exp-0001"]),
    ("搜索结果链接颜色", ["exp-0002"]),
    ("很多种蓝色色调测试", ["exp-0003"]),
    ("链接颜色对收入的影响", ["exp-0002", "exp-0003"]),
    ("多变量测试组合优化", ["exp-0004"]),
    ("竞选官网注册转化", ["exp-0004"]),
    ("房源图片质量对预订的影响", ["exp-0005"]),
    ("专业摄影提升预订率", ["exp-0005"]),
    ("邀请好友奖励机制", ["exp-0006"]),
    ("双边推荐奖励存储空间", ["exp-0006"]),
    ("个性化封面缩略图", ["exp-0007"]),
    ("视频推荐点击率优化", ["exp-0007"]),
    ("结账表单字段精简", ["exp-0008"]),
    ("表单字段语义模糊导致流失", ["exp-0008"]),
    ("旅游预订转化率优化", ["exp-0008"]),
    ("CTA文案与素材组合测试", ["exp-0004"]),
    ("增长黑客邀请裂变", ["exp-0006"]),
    ("UGC照片对比专业摄影", ["exp-0005"]),
    ("内容个性化提升参与度", ["exp-0007"]),
]

TOP_K = 5

CONFIGS = {
    "mock_embed+mock_rerank": (MockEmbedder(), MockReranker()),
}


def _reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / rank
    return 0.0


def _recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    return 1.0 if any(rid in relevant_ids for rid in retrieved_ids[:k]) else 0.0


def ingest_with(embedder) -> None:
    records = load_corpus()
    texts = [_search_text(r) for r in records]
    vectors = embedder.embed(texts)
    import jieba

    rows = []
    for rec, text, vec in zip(records, texts, vectors):
        row = dict(rec)
        row["search_text"] = text
        row["search_text_tokenized"] = " ".join(jieba.lcut(text))
        row["vector"] = vec
        rows.append(row)
    store.rebuild_table(rows)


def run_config(name: str, embedder, reranker) -> dict:
    print(f"\n=== {name} ===")
    ingest_with(embedder)

    rr_sum = 0.0
    recall_1_sum = 0.0
    recall_3_sum = 0.0
    recall_5_sum = 0.0
    status_counts = {"correct": 0, "ambiguous": 0, "wrong": 0, "unavailable": 0}

    for query, relevant_ids in TESTSET:
        result = retriever.search(query, top_k=TOP_K, embedder=embedder, reranker=reranker)
        status_counts[result["status"]] = status_counts.get(result["status"], 0) + 1
        retrieved_ids = [c["id"] for c in result["citations"]]

        rr_sum += _reciprocal_rank(retrieved_ids, relevant_ids)
        recall_1_sum += _recall_at_k(retrieved_ids, relevant_ids, 1)
        recall_3_sum += _recall_at_k(retrieved_ids, relevant_ids, 3)
        recall_5_sum += _recall_at_k(retrieved_ids, relevant_ids, 5)

    n = len(TESTSET)
    metrics = {
        "n_queries": n,
        "mrr": round(rr_sum / n, 4),
        "recall@1": round(recall_1_sum / n, 4),
        "recall@3": round(recall_3_sum / n, 4),
        "recall@5": round(recall_5_sum / n, 4),
        "status_counts": status_counts,
    }
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


def main():
    results = {"mock_embed+mock_rerank": run_config("mock_embed+mock_rerank", MockEmbedder(), MockReranker())}

    from app import config

    if config.SILICONFLOW_API_KEY:
        real_embedder = SiliconFlowEmbedder(config.SILICONFLOW_API_KEY, config.SILICONFLOW_EMBEDDING_MODEL)
        results["real_embed+mock_rerank"] = run_config(
            "real_embed+mock_rerank", real_embedder, MockReranker()
        )
        real_reranker = SiliconFlowReranker(config.SILICONFLOW_API_KEY, config.SILICONFLOW_RERANK_MODEL)
        results["real_embed+real_rerank"] = run_config(
            "real_embed+real_rerank", real_embedder, real_reranker
        )
    else:
        print("\nSILICONFLOW_API_KEY 未配置，跳过真实 embedding 消融组")

    out_path = os.path.join(os.path.dirname(__file__), "retrieval_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nwrote {out_path}")

    # Leave the index in its best configuration for the running app rather
    # than stranding it on whichever ablation config ran last.
    if config.SILICONFLOW_API_KEY:
        ingest_with(SiliconFlowEmbedder(config.SILICONFLOW_API_KEY, config.SILICONFLOW_EMBEDDING_MODEL))
        print("re-ingested with real embedder (leaving index in production config)")

    tracing.flush()


if __name__ == "__main__":
    main()
