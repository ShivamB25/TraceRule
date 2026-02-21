from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INTERNAL_TABLES = ("policies", "rules", "violations")


def _get_engine():
    from app.database import engine

    return engine


async def _list_public_tables(engine) -> list[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname='public' ORDER BY tablename"
            )
        )
        return [row[0] for row in result]


async def _truncate_tables(engine, table_names: list[str]) -> None:
    if not table_names:
        return

    quoted = ", ".join(f'"{name}"' for name in table_names)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


async def _print_counts(engine, table_names: list[str]) -> None:
    async with engine.connect() as conn:
        for table_name in table_names:
            result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            count = result.scalar_one()
            print(f"{table_name}: {count}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset TraceRule database tables for clean demos"
    )
    parser.add_argument(
        "--all-public",
        action="store_true",
        help="Truncate every table in public schema (including business tables)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation",
    )
    args = parser.parse_args()

    engine = _get_engine()
    public_tables = await _list_public_tables(engine)
    if args.all_public:
        target_tables = public_tables
        mode_label = "ALL public tables"
    else:
        target_tables = [t for t in INTERNAL_TABLES if t in public_tables]
        mode_label = "internal TraceRule tables only"

    if not target_tables:
        print("No matching tables found. Nothing to reset.")
        await engine.dispose()
        return

    print(f"Reset mode: {mode_label}")
    print("Tables:")
    for table_name in target_tables:
        print(f"- {table_name}")

    if not args.yes:
        answer = input("Proceed with TRUNCATE? Type 'yes' to continue: ").strip()
        if answer != "yes":
            print("Cancelled.")
            await engine.dispose()
            return

    await _truncate_tables(engine, target_tables)
    print("Reset complete. Current row counts:")
    await _print_counts(engine, target_tables)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
