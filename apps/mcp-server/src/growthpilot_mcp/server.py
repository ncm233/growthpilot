from . import _bootstrap  # noqa: F401  (side effect: puts agent-service's `app` package on sys.path)

from fastmcp import FastMCP

from app.db import init_db  # noqa: E402

# Idempotent (CREATE TABLE IF NOT EXISTS) — safe even if the FastAPI service
# already initialized the same growthpilot.db file, and necessary if this MCP
# server is the first process to touch it.
init_db()

mcp = FastMCP("GrowthPilot")

# Importing these registers their @mcp.tool-decorated functions onto `mcp`
# above. Must come after `mcp = FastMCP(...)` — each tool module does
# `from .server import mcp`, which only resolves once this module object
# already has the name bound.
from .tools import data, experiment, playbook  # noqa: E402,F401


def main():
    # HTTP transport, not stdio, and not a style preference: tested against a
    # real spawned subprocess (not just in-process calls) and any tool that
    # touches LanceDB — a Rust/tokio-backed library — hangs forever under
    # FastMCP's stdio transport on this machine. The exact same tool call
    # returns instantly under HTTP transport. This matches a known class of
    # issue in the MCP Python SDK (stdio + blocking-under-the-hood calls
    # hanging while SSE/HTTP works) rather than being specific to this code.
    # HTTP also happens to be what Phase 5's Zeabur deployment needs anyway.
    #
    # show_banner=False: FastMCP's ASCII banner prints to stdout, which would
    # corrupt a stdio JSON-RPC channel if this ever runs under stdio again.
    import os

    port = int(os.environ.get("GROWTHPILOT_MCP_PORT", "8210"))
    mcp.run(transport="http", host="127.0.0.1", port=port, show_banner=False)


if __name__ == "__main__":
    main()
