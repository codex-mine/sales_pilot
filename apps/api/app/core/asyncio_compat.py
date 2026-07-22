"""
Windows runs `asyncio.ProactorEventLoop` by default; `psycopg`'s async mode
(used by `langgraph-checkpoint-postgres`'s `AsyncPostgresSaver` — see
`app/agents/base.py`) only supports a selector-based loop. Linux (every real
deployment target — see `docker-compose.yml`) is unaffected, since its
default loop is already selector-based; this only matters for local Windows
dev/test runs, where it must be set before any event loop is created, so
every process entry point that might construct a checkpointer (the API
process, Celery workers, pytest) calls this at import time.
"""

import asyncio
import sys


def ensure_selector_event_loop_policy() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
