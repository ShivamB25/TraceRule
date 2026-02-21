from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TRANSACTION_FILES = ("HI-Small_Trans.csv", "LI-Small_Trans.csv")
ACCOUNT_FILES = ("HI-Small_accounts.csv", "LI-Small_accounts.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/aml_demo")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument(
        "--max-trans-rows",
        type=int,
        default=250000,
        help="Total transaction rows to ingest across files; 0 means all",
    )
    parser.add_argument(
        "--max-account-rows",
        type=int,
        default=0,
        help="Total account rows to ingest across files; 0 means all",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Append data instead of truncating transactions/accounts first",
    )
    return parser.parse_args()


def parse_event_ts(value: str) -> datetime:
    return datetime.strptime(value, "%Y/%m/%d %H:%M")


async def create_tables(conn) -> None:
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS transactions ("
            "id BIGSERIAL PRIMARY KEY,"
            "source_file TEXT NOT NULL,"
            "source_row_number BIGINT NOT NULL,"
            "event_ts TIMESTAMP NOT NULL,"
            "from_bank TEXT NOT NULL,"
            "from_account TEXT NOT NULL,"
            "to_bank TEXT NOT NULL,"
            "to_account TEXT NOT NULL,"
            "amount_received NUMERIC(18,2) NOT NULL,"
            "receiving_currency TEXT NOT NULL,"
            "amount_paid NUMERIC(18,2) NOT NULL,"
            "payment_currency TEXT NOT NULL,"
            "payment_format TEXT NOT NULL,"
            "is_laundering BOOLEAN NOT NULL,"
            "created_at TIMESTAMP DEFAULT NOW(),"
            "UNIQUE(source_file, source_row_number)"
            ")"
        )
    )
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS accounts ("
            "id BIGSERIAL PRIMARY KEY,"
            "source_file TEXT NOT NULL,"
            "source_row_number BIGINT NOT NULL,"
            "bank_name TEXT NOT NULL,"
            "bank_id TEXT NOT NULL,"
            "account_number TEXT NOT NULL,"
            "entity_id TEXT NOT NULL,"
            "entity_name TEXT NOT NULL,"
            "created_at TIMESTAMP DEFAULT NOW(),"
            "UNIQUE(source_file, source_row_number)"
            ")"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_transactions_event_ts ON transactions(event_ts)"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_transactions_is_laundering ON transactions(is_laundering)"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_transactions_from_account ON transactions(from_account)"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_transactions_to_account ON transactions(to_account)"
        )
    )


async def load_transactions(
    conn, data_dir: Path, batch_size: int, max_rows: int
) -> int:
    insert_stmt = text(
        "INSERT INTO transactions ("
        "source_file, source_row_number, event_ts, from_bank, from_account, to_bank, to_account,"
        "amount_received, receiving_currency, amount_paid, payment_currency, payment_format, is_laundering"
        ") VALUES ("
        ":source_file, :source_row_number, :event_ts, :from_bank, :from_account, :to_bank, :to_account,"
        ":amount_received, :receiving_currency, :amount_paid, :payment_currency, :payment_format, :is_laundering"
        ") ON CONFLICT (source_file, source_row_number) DO NOTHING"
    )

    loaded = 0
    batch: list[dict] = []

    for filename in TRANSACTION_FILES:
        csv_path = data_dir / filename
        if not csv_path.exists():
            continue

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)

            for row_index, row in enumerate(reader, start=1):
                if max_rows and loaded >= max_rows:
                    break
                if len(row) < 11:
                    continue

                batch.append(
                    {
                        "source_file": filename,
                        "source_row_number": row_index,
                        "event_ts": parse_event_ts(row[0].strip()),
                        "from_bank": row[1].strip(),
                        "from_account": row[2].strip(),
                        "to_bank": row[3].strip(),
                        "to_account": row[4].strip(),
                        "amount_received": Decimal(row[5].strip()),
                        "receiving_currency": row[6].strip(),
                        "amount_paid": Decimal(row[7].strip()),
                        "payment_currency": row[8].strip(),
                        "payment_format": row[9].strip(),
                        "is_laundering": row[10].strip() == "1",
                    }
                )
                loaded += 1

                if len(batch) >= batch_size:
                    await conn.execute(insert_stmt, batch)
                    batch = []
                    if loaded % 100000 == 0:
                        print(f"Loaded transactions: {loaded}")

        if max_rows and loaded >= max_rows:
            break

    if batch:
        await conn.execute(insert_stmt, batch)

    return loaded


async def load_accounts(conn, data_dir: Path, batch_size: int, max_rows: int) -> int:
    insert_stmt = text(
        "INSERT INTO accounts ("
        "source_file, source_row_number, bank_name, bank_id, account_number, entity_id, entity_name"
        ") VALUES ("
        ":source_file, :source_row_number, :bank_name, :bank_id, :account_number, :entity_id, :entity_name"
        ") ON CONFLICT (source_file, source_row_number) DO NOTHING"
    )

    loaded = 0
    batch: list[dict] = []

    for filename in ACCOUNT_FILES:
        csv_path = data_dir / filename
        if not csv_path.exists():
            continue

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)

            for row_index, row in enumerate(reader, start=1):
                if max_rows and loaded >= max_rows:
                    break
                if len(row) < 5:
                    continue

                batch.append(
                    {
                        "source_file": filename,
                        "source_row_number": row_index,
                        "bank_name": row[0].strip(),
                        "bank_id": row[1].strip(),
                        "account_number": row[2].strip(),
                        "entity_id": row[3].strip(),
                        "entity_name": row[4].strip(),
                    }
                )
                loaded += 1

                if len(batch) >= batch_size:
                    await conn.execute(insert_stmt, batch)
                    batch = []

        if max_rows and loaded >= max_rows:
            break

    if batch:
        await conn.execute(insert_stmt, batch)

    return loaded


async def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"Data directory not found: {data_dir}")

    from app.database import engine

    async with engine.begin() as conn:
        await create_tables(conn)

        if not args.no_truncate:
            await conn.execute(text("TRUNCATE TABLE transactions RESTART IDENTITY"))
            await conn.execute(text("TRUNCATE TABLE accounts RESTART IDENTITY"))

        loaded_transactions = await load_transactions(
            conn,
            data_dir,
            args.batch_size,
            args.max_trans_rows,
        )
        loaded_accounts = await load_accounts(
            conn,
            data_dir,
            args.batch_size,
            args.max_account_rows,
        )

        tx_total = await conn.execute(text("SELECT COUNT(*) FROM transactions"))
        acc_total = await conn.execute(text("SELECT COUNT(*) FROM accounts"))
        laundering_total = await conn.execute(
            text("SELECT COUNT(*) FROM transactions WHERE is_laundering = TRUE")
        )

        print(f"Loaded transaction rows this run: {loaded_transactions}")
        print(f"Loaded account rows this run: {loaded_accounts}")
        print(f"transactions total: {tx_total.scalar_one()}")
        print(f"accounts total: {acc_total.scalar_one()}")
        print(f"transactions marked laundering: {laundering_total.scalar_one()}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
