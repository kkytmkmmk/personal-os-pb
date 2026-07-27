"""Fail when source-controlled files appear to contain a concrete API secret."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


IGNORED_PARTS = {".git", "data", "__pycache__", ".venv", "venv", ".pytest_cache"}
TEXT_SUFFIXES = {
    ".py", ".js", ".html", ".css", ".md", ".json", ".toml", ".yaml", ".yml",
    ".ps1", ".txt", ".env", ".example",
}
PATTERNS = {
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[0-9A-Za-z_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgithub_pat_[0-9A-Za-z_]{20,}\b|\bgh[opsu]_[0-9A-Za-z]{20,}\b"),
}


def find_secrets(root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".gitignore":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(lines, 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append({
                        "kind": label,
                        "file": str(path.relative_to(root)),
                        "line": line_number,
                    })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    findings = find_secrets(args.root.resolve())
    if findings:
        for item in findings:
            print(f"{item['kind']}: {item['file']}:{item['line']}")
        return 1
    print("No concrete API-key patterns found in source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
