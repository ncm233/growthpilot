"""Entry point for `python -m growthpilot_mcp`.

This indirection is not boilerplate — it's the fix for a real bug found while
testing against a genuine stdio subprocess (not just in-process calls):
running `python -m growthpilot_mcp.server` directly binds that module as
`__main__`, and tools/*.py's relative import (`from ..server import mcp`)
then imports a SECOND, separate copy of server.py as `growthpilot_mcp.server`
to satisfy the relative import — so `@mcp.tool` registers tools onto that
second copy's `mcp` object, while `mcp.run()` executes on the first (empty)
one. Claude Desktop would connect successfully and see zero tools, silently.
Routing through a trivial __main__.py means server.py is always imported
normally exactly once, never duplicated.
"""

from .server import main

main()
