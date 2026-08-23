import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    budget_limit REAL NOT NULL,
    status TEXT NOT NULL,              -- pending_approval | approved | rejected
    raw_data_json TEXT NOT NULL,
    opportunity_json TEXT NOT NULL,
    experiment_json TEXT NOT NULL,
    critic_json TEXT NOT NULL,
    simulation_json TEXT NOT NULL,
    approval_id TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS memory (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    channel TEXT NOT NULL,
    result TEXT NOT NULL,
    confidence REAL NOT NULL,
    lesson TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    channel TEXT NOT NULL,             -- wecom | feishu
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def row_to_run(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "goal": row["goal"],
        "budget_limit": row["budget_limit"],
        "status": row["status"],
        "raw_data": json.loads(row["raw_data_json"]),
        "opportunity": json.loads(row["opportunity_json"]),
        "experiment": json.loads(row["experiment_json"]),
        "critic": json.loads(row["critic_json"]),
        "simulation": json.loads(row["simulation_json"]),
        "approval_id": row["approval_id"],
        "created_at": row["created_at"],
        "decided_at": row["decided_at"],
    }
