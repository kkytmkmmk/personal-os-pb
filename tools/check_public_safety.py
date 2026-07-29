"""Detect likely personal data before publishing a Personal OS snapshot.

The scanner intentionally reports locations only; it never prints matching
content.  A local, git-ignored `.private_terms` file can extend the checks.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


TEXT_SUFFIXES = {".py", ".js", ".html", ".css", ".md", ".json", ".toml", ".yaml", ".yml", ".ps1", ".txt"}
IGNORED_PARTS = {".git", "data", "dist", "__pycache__", ".venv", "venv", ".pytest_cache"}


def _tracked_files(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"], check=True, capture_output=True, text=True
        )
        return [root / item for item in result.stdout.splitlines() if item]
    except (OSError, subprocess.CalledProcessError):
        return [path for path in root.rglob("*") if path.is_file()]


def _decode_rule_value(value: str) -> str:
    """Allow local rules to stay ASCII-only via ``\\uXXXX`` escapes."""
    if "\\u" not in value and "\\U" not in value:
        return value
    try:
        return value.encode("ascii").decode("unicode_escape")
    except UnicodeError:
        return value


def _private_terms(root: Path) -> list[str]:
    local_file = root / ".private_terms"
    if not local_file.is_file():
        return []
    try:
        terms = []
        for line in local_file.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            term, _, _replacement = value.partition("=")
            if term:
                terms.append(_decode_rule_value(term))
        return terms
    except OSError:
        return []


def _patterns(root: Path) -> dict[str, re.Pattern[str]]:
    # Build the user-directory pattern from fragments so the scanner does not
    # itself contain a concrete machine path example.
    windows_home = "C:" + r"[\\/]" + "Users" + r"[\\/]" + r"[^\\/\s]+"
    terms = _private_terms(root)
    result = {
        "absolute Windows user path": re.compile(windows_home, re.IGNORECASE),
        "absolute macOS user path": re.compile(r"/(?:Users|home)/[^/\s]+", re.IGNORECASE),
        "email address": re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
        # A SHA-256 value can contain a coincidental 10--11 digit run.  Do
        # not classify such a run as a phone number when it is embedded in a
        # hexadecimal token (for example a reviewed screenshot hash).
        "phone number": re.compile(r"(?<![0-9a-fA-F])(?:0\d{1,4}-\d{1,4}-\d{3,4}|0\d{9,10})(?![0-9a-fA-F])"),
    }
    for term in terms:
        result[f"private term ({term[:24]})"] = re.compile(re.escape(term), re.IGNORECASE)
    return result


def find_public_safety_issues(root: Path) -> list[dict[str, object]]:
    root = root.resolve()
    patterns = _patterns(root)
    findings: list[dict[str, object]] = []
    for path in _tracked_files(root):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".gitignore", ".env.example"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            for kind, pattern in patterns.items():
                if pattern.search(line):
                    findings.append({"kind": kind, "file": relative, "line": line_number})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    findings = find_public_safety_issues(args.root)
    if findings:
        for item in findings:
            print(f"{item['kind']}: {item['file']}:{item['line']}")
        return 1
    print("Public safety scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
