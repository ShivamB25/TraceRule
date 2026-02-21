from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile


PROFILES: dict[str, list[str]] = {
    "tiny": [
        "HI-Small_Trans.csv",
        "HI-Small_accounts.csv",
        "HI-Small_Patterns.txt",
    ],
    "small": [
        "HI-Small_Trans.csv",
        "LI-Small_Trans.csv",
        "HI-Small_accounts.csv",
        "LI-Small_accounts.csv",
        "HI-Small_Patterns.txt",
        "LI-Small_Patterns.txt",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--zip-path",
        default="ibm-transactions-for-anti-money-laundering-aml.zip",
    )
    parser.add_argument("--output-dir", default="data/aml_demo")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="small")
    parser.add_argument("--budget-gb", type=float, default=1.5)
    return parser.parse_args()


def format_gb(size_bytes: int) -> str:
    return f"{size_bytes / (1024**3):.3f} GB"


def main() -> None:
    args = parse_args()
    zip_path = Path(args.zip_path)
    output_dir = Path(args.output_dir)
    budget_bytes = int(args.budget_gb * (1024**3))

    if not zip_path.exists():
        raise SystemExit(f"Zip not found: {zip_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path) as zf:
        infos = {info.filename: info for info in zf.infolist()}
        requested = PROFILES[args.profile]
        selected: list[str] = []
        total_size = 0

        for name in requested:
            if name not in infos:
                raise SystemExit(f"Missing file in zip: {name}")
            size = infos[name].file_size
            if total_size + size > budget_bytes:
                continue
            selected.append(name)
            total_size += size

        if not selected:
            raise SystemExit(
                f"Nothing selected within budget {args.budget_gb} GB. Increase --budget-gb."
            )

        print(f"Profile: {args.profile}")
        print(f"Budget: {format_gb(budget_bytes)}")
        print(f"Selected total: {format_gb(total_size)}")
        print("Files:")
        for name in selected:
            print(f"- {name} ({format_gb(infos[name].file_size)})")

        zf.extractall(path=output_dir, members=selected)

    manifest = {
        "zip_path": str(zip_path),
        "profile": args.profile,
        "budget_gb": args.budget_gb,
        "selected_total_bytes": total_size,
        "selected_files": selected,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Extracted to: {output_dir}")
    print(f"Manifest: {output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
