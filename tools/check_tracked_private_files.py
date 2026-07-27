"""Fail when Git tracks a local runtime or private-data artifact."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path, PurePosixPath


FORBIDDEN_DIRECTORIES = {"data", "attachments", "imports", "backups", "logs"}
FORBIDDEN_NAMES = {".env", ".private_terms"}
FORBIDDEN_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".posbackup", ".db-wal", ".db-shm", ".sqlite-wal", ".sqlite-shm")


def tracked_private_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"], check=True, capture_output=True, text=True
    )
    findings: list[str] = []
    for raw_name in result.stdout.splitlines():
        path = PurePosixPath(raw_name)
        lowered_name = path.name.lower()
        if any(part.lower() in FORBIDDEN_DIRECTORIES for part in path.parts):
            findings.append(raw_name)
        elif lowered_name in FORBIDDEN_NAMES or (
            lowered_name.startswith(".env.") and lowered_name != ".env.example"
        ):
            findings.append(raw_name)
        elif lowered_name.endswith(FORBIDDEN_SUFFIXES):
            findings.append(raw_name)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    findings = tracked_private_files(args.root.resolve())
    if findings:
        print("Forbidden tracked files:")
        print("\n".join(findings))
        return 1
    print("Tracked private-file scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
