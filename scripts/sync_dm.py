#!/usr/bin/env python3
"""Sync Achieve data into Autochat dm schema."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "backend"))

from app.sync import run_dm_sync  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Achieve data into dm schema")
    parser.add_argument("--job", default="dm_sync", help="Job name for ops log")
    parser.add_argument(
        "--entities",
        default="",
        help="Comma-separated entities to sync (empty for all)",
    )
    parser.add_argument(
        "--terms",
        default="",
        help="Comma-separated term names to filter (optional)",
    )
    parser.add_argument(
        "--batch-size",
        default="",
        help="Batch size for upserts (optional)",
    )
    args = parser.parse_args()

    entities = [item.strip() for item in args.entities.split(",") if item.strip()] or None
    terms = [item.strip() for item in args.terms.split(",") if item.strip()] or None
    batch_size = int(args.batch_size) if args.batch_size else None

    result = run_dm_sync(
        job_name=args.job,
        entities=entities,
        term_window=terms,
        batch_size=batch_size,
    )
    print(result)


if __name__ == "__main__":
    main()
