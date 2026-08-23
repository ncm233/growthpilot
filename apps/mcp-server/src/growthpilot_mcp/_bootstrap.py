"""Puts apps/agent-service on sys.path so this package can `import app.*`
without a formal install step. This is a same-repo sibling package, not an
independently published library — a real pip dependency (editable install)
would be over-engineering for two folders that always ship together. Import
this module first, before anything that does `from app... import ...`."""

import os
import sys

_AGENT_SERVICE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "agent-service"))

if _AGENT_SERVICE_DIR not in sys.path:
    sys.path.insert(0, _AGENT_SERVICE_DIR)
