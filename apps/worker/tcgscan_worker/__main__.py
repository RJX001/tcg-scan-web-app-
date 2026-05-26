"""CLI entrypoint: `python -m tcgscan_worker <command> ...`.

Supported commands:
- worker              run the Temporal worker
- ingest:catalog      --game <slug> [--limit N]
- embed:catalog       --game <slug> [--limit N]
- rollup:daily        [--card-id UUID]
- ingest:pricing      --card-id UUID | --game <slug> [--source ...]
- schedules:register  register Temporal schedules (Week 4–5)
"""

from __future__ import annotations

import asyncio
import sys

import structlog

log = structlog.get_logger()


def _cmd_worker(_argv: list[str]) -> int:
    from tcgscan_worker.worker import run_worker

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        log.info("worker.stop")
    return 0


def _cmd_ingest_catalog(argv: list[str]) -> int:
    from tcgscan_worker.catalog.runner import main

    return main(argv)


def _cmd_embed_catalog(argv: list[str]) -> int:
    from tcgscan_worker.embedding import main

    return main(argv)


def _cmd_rollup(argv: list[str]) -> int:
    from tcgscan_worker.rollup import main

    return main(argv)


def _cmd_ingest_pricing(argv: list[str]) -> int:
    from tcgscan_worker.pricing.ingest import main

    return main(argv)


def _cmd_schedules(_argv: list[str]) -> int:
    from tcgscan_worker.schedules import main

    return main()


COMMANDS = {
    "worker": _cmd_worker,
    "ingest:catalog": _cmd_ingest_catalog,
    "embed:catalog": _cmd_embed_catalog,
    "rollup:daily": _cmd_rollup,
    "ingest:pricing": _cmd_ingest_pricing,
    "schedules:register": _cmd_schedules,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(f"usage: python -m tcgscan_worker <{'|'.join(COMMANDS)}> [args...]")
        return 0
    cmd, *rest = sys.argv[1:]
    fn = COMMANDS.get(cmd)
    if fn is None:
        print(f"unknown command: {cmd}")
        return 2
    return fn(rest)


if __name__ == "__main__":
    raise SystemExit(main())
