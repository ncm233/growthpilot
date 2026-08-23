"""CLI: python -m app.rag.ingest
Reads packages/corpus/curated/*.jsonl, embeds each case, and rebuilds the
LanceDB table from scratch. Re-run this any time the corpus changes or the
embedder provider (EMBEDDER_PROVIDER) is switched.
"""

import json
import os

from . import store
from .embedder import get_embedder

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CORPUS_DIR = os.path.join(BASE_DIR, "..", "..", "packages", "corpus", "curated")


def _search_text(rec: dict) -> str:
    # scene + hypothesis + intervention + lesson is the field mix that best
    # matches how experiment_agent/opportunity_agent phrase their queries
    # (see retriever.py callers) — outcome/lift/source are structured data,
    # not prose worth embedding.
    parts = [rec.get("scene"), rec.get("hypothesis"), rec.get("intervention"), rec.get("lesson")]
    return " ".join(p for p in parts if p)


def load_corpus() -> list[dict]:
    records = []
    if not os.path.isdir(CORPUS_DIR):
        return records
    for fname in sorted(os.listdir(CORPUS_DIR)):
        if not fname.endswith(".jsonl"):
            continue
        with open(os.path.join(CORPUS_DIR, fname), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def main():
    import jieba

    records = load_corpus()
    if not records:
        print(f"语料为空：{os.path.abspath(CORPUS_DIR)} 下没有 .jsonl 文件，先往 packages/corpus/curated/ 里加案例")
        return

    embedder = get_embedder()
    texts = [_search_text(r) for r in records]
    vectors = embedder.embed(texts)

    rows = []
    for rec, text, vec in zip(records, texts, vectors):
        row = dict(rec)
        row["search_text"] = text
        row["search_text_tokenized"] = " ".join(jieba.lcut(text))
        row["vector"] = vec
        rows.append(row)

    store.rebuild_table(rows)
    print(
        f"已索引 {len(rows)} 条案例 -> {store.STORE_DIR}"
        f"（embedder={embedder.__class__.__name__}, dim={embedder.dim}）"
    )


if __name__ == "__main__":
    main()
