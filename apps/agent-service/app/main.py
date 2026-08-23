import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from .db import get_conn, init_db, row_to_run
from .planner import orchestrator

BASE_DIR = os.path.dirname(__file__)
CORPUS_DIR = os.path.join(BASE_DIR, "..", "..", "..", "packages", "corpus", "curated")

app = FastAPI(title="GrowthPilot")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.on_event("startup")
def _startup():
    init_db()


class RunRequest(BaseModel):
    goal: str
    budget_limit: float = 10000.0


class DecisionRequest(BaseModel):
    decision: str  # approved | rejected


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/run")
def api_run(req: RunRequest):
    if not req.goal.strip():
        raise HTTPException(400, "goal is required")
    return orchestrator.run_goal(req.goal, req.budget_limit)


@app.get("/api/runs")
def api_runs():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
    return [row_to_run(r) for r in rows]


@app.get("/api/runs/{run_id}")
def api_run_detail(run_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "run not found")
    return row_to_run(row)


@app.post("/api/runs/{run_id}/decision")
def api_decide(run_id: str, req: DecisionRequest):
    try:
        return orchestrator.decide(run_id, req.decision)
    except KeyError:
        raise HTTPException(404, "run not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/memory")
def api_memory():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM memory ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/corpus")
def api_corpus():
    """Serves packages/corpus/curated/*.jsonl — the verified growth/CRO case
    studies used as RAG source material. Reading straight off disk (not a DB
    table) keeps the corpus editable as plain JSONL files that get reviewed
    like code, not hidden behind a write API."""
    records = []
    if os.path.isdir(CORPUS_DIR):
        for fname in sorted(os.listdir(CORPUS_DIR)):
            if not fname.endswith(".jsonl"):
                continue
            path = os.path.join(CORPUS_DIR, fname)
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
    return records


@app.get("/api/notifications")
def api_notifications():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50").fetchall()
    return [dict(r) for r in rows]
