"""Langfuse wiring.

`@observe` is imported directly from `langfuse` at each call site (agents,
tools, rag, llm) rather than re-exported from here — it's already the public
API, wrapping it would just be indirection. It degrades to a harmless no-op
when LANGFUSE_PUBLIC_KEY/SECRET_KEY aren't set (logs a warning, doesn't
raise) — the same graceful-degradation shape as every Mock/Real integration
elsewhere in this codebase, just without needing a MockXxx class since the
SDK already does it.

This module's only real job is `flush()`. Langfuse's background exporter
thread batches and flushes on an interval, which is fine for the long-running
FastAPI process but not for short request-scoped units of work that need
their trace to actually land before the caller exits — an eval script run,
an MCP tool call, a single orchestrator entrypoint. Call flush() at the end
of those, not inside every decorated function (that would defeat batching).
"""

from langfuse import get_client


def flush() -> None:
    try:
        get_client().flush()
    except Exception:
        # Never let observability plumbing take down a real request — same
        # rule this codebase applies to RAG/LLM failures (see retriever.py).
        pass
