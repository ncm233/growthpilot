import os

# store.py -> rag -> app -> agent-service -> apps -> repo root (5 levels)
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
STORE_DIR = os.path.join(_REPO_ROOT, "data", "lancedb")
TABLE_NAME = "growth_cases"
FTS_COLUMN = "search_text_tokenized"


def _connect():
    # Lazy import: lancedb is only required once someone actually uses RAG.
    # Keeps `pip install -r requirements.txt` (base) + `python -m uvicorn ...`
    # working even before anyone runs `pip install -r requirements-rag.txt`.
    import lancedb

    os.makedirs(STORE_DIR, exist_ok=True)
    return lancedb.connect(STORE_DIR)


def rebuild_table(records: list[dict]):
    """Drops and recreates the table from scratch. Called by ingest.py.
    The corpus is small (hundreds of rows, not millions) so a full rebuild on
    every ingest run is simpler and safer than incremental upsert logic, and
    it avoids stale-vector bugs when the embedder provider changes (a table
    built with MockEmbedder's 64-dim vectors is silently wrong once you
    switch to BgeEmbedder's 512-dim ones — rebuilding from scratch sidesteps
    that instead of trying to detect and migrate it)."""
    db = _connect()
    if TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)

    table = db.create_table(TABLE_NAME, data=records)
    table.create_fts_index(FTS_COLUMN, replace=True)
    return table


def get_table():
    db = _connect()
    if TABLE_NAME not in db.table_names():
        raise RuntimeError(
            f"LanceDB 表 '{TABLE_NAME}' 不存在，请先在 apps/agent-service 目录下运行 "
            "`python -m app.rag.ingest` 建索引"
        )
    return db.open_table(TABLE_NAME)


def hybrid_search(query_text_tokenized: str, query_vector: list[float], limit: int) -> list[dict]:
    """Vector + FTS hybrid search, fused with LanceDB's built-in RRFReranker.
    Returns raw candidates (not yet cross-encoder reranked — that's
    reranker.py's job on this shortlist)."""
    table = get_table()
    results = (
        table.search(query_type="hybrid", vector_column_name="vector")
        .text(query_text_tokenized)
        .vector(query_vector)
        .limit(limit)
        .to_list()
    )
    return results
