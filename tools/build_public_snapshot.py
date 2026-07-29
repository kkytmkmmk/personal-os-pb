"""Build a sanitized, source-only public snapshot without touching user data."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".js", ".html", ".css", ".md", ".json", ".toml", ".yaml", ".yml", ".ps1", ".txt"}
ALLOWED_ROOTS = {"app.py", "personal_os", "static", "tools", "tests", "benchmarks", "requirements", "docs", "README.md", "ARCHITECTURE.md", "USER_GUIDE.md", "CONTRIBUTING.md", ".gitignore", ".env.example", "requirements-dev.txt"}
ALLOWED_BINARY_PREFIXES = ("docs/screenshots/ux-phase5/",)
PUBLIC_REVIEW_TEXT_PATHS = (Path("docs/ux_phase5_visual_review.md"),)


def is_allowed_binary(relative: Path) -> bool:
    return relative.as_posix().startswith(ALLOWED_BINARY_PREFIXES) and relative.suffix.lower() == ".png"


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(["git", "-C", str(root), "ls-files"], check=True, capture_output=True, text=True)
    return [root / name for name in result.stdout.splitlines() if name]


def is_allowed(relative: Path) -> bool:
    return bool(relative.parts) and relative.parts[0] in ALLOWED_ROOTS


def local_replacements(root: Path) -> dict[str, str]:
    """Read local-only redaction rules in ``term=replacement`` format."""
    path = root / ".private_terms"
    if not path.is_file():
        return {}
    rules: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        source, separator, replacement = line.strip().partition("=")
        if source and separator and replacement:
            rules[_decode_rule_value(source)] = _decode_rule_value(replacement)
    return rules


def _decode_rule_value(value: str) -> str:
    """Allow the ignored local rule file to contain only ASCII escape syntax."""
    if "\\u" not in value and "\\U" not in value:
        return value
    try:
        return value.encode("ascii").decode("unicode_escape")
    except UnicodeError:
        return value


def redact(text: str, replacements: dict[str, str]) -> str:
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)
    text = re.sub(r"C:[\\/]+Users[\\/]+[^\\/\s'`\"<>]+", "<user-home>", text, flags=re.IGNORECASE)
    return re.sub(r"/(?:Users|home)/[^/\s'`\"<>]+", "<user-home>", text, flags=re.IGNORECASE)


def public_readme(text: str) -> str:
    banner = (
        "> This repository is a generated, sanitized public mirror. "
        "No user runtime database, private history, attachments, or personal "
        "context are intentionally included. Direct changes may be overwritten.\n\n"
    )
    return banner + text


def build_snapshot(output: Path) -> int:
    output = output.resolve()
    if output == ROOT:
        raise ValueError("The public snapshot output cannot be the repository root")
    if output.exists():
        shutil.rmtree(output)
    screenshot_dir = ROOT / "docs" / "screenshots" / "ux-phase5"
    if screenshot_dir.exists():
        try:
            from tools.check_public_screenshots import find_screenshot_issues
        except ModuleNotFoundError:  # Direct execution from tools/ on Windows.
            from check_public_screenshots import find_screenshot_issues
        issues = find_screenshot_issues(ROOT)
        if issues:
            raise ValueError("Public screenshot safety check failed: " + "; ".join(issues))
    copied = 0
    replacements = local_replacements(ROOT)
    copied_relative: set[Path] = set()
    for source in tracked_files(ROOT):
        relative = source.relative_to(ROOT)
        if not is_allowed(relative) or not source.is_file():
            continue
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() in TEXT_SUFFIXES or source.name in {".gitignore", ".env.example"}:
            content = redact(source.read_text(encoding="utf-8"), replacements)
            if relative.as_posix() == "README.md":
                content = public_readme(content)
            target.write_text(content, encoding="utf-8", newline="\n")
        elif is_allowed_binary(relative):
            shutil.copy2(source, target)
        else:
            continue
        copied += 1
        copied_relative.add(relative)
    # Review screenshots are generated assets rather than source text. They
    # are admitted only from this safety-validated path, so a local pre-commit
    # snapshot exercises the same public contract as CI.
    if screenshot_dir.exists():
        for source in [screenshot_dir / "manifest.json", *sorted(screenshot_dir.glob("*.png"))]:
            if not source.is_file():
                continue
            relative = source.relative_to(ROOT)
            if relative in copied_relative:
                continue
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix.lower() == ".png":
                shutil.copy2(source, target)
            else:
                target.write_text(redact(source.read_text(encoding="utf-8"), replacements), encoding="utf-8", newline="\n")
            copied += 1
    for relative in PUBLIC_REVIEW_TEXT_PATHS:
        if relative in copied_relative:
            continue
        source = ROOT / relative
        if not source.is_file():
            continue
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(redact(source.read_text(encoding="utf-8"), replacements), encoding="utf-8", newline="\n")
        copied += 1
    info = output / "PUBLIC_SNAPSHOT_INFO.md"
    info.write_text(
        "# Public snapshot\n\n"
        "This repository is a generated, sanitized public mirror of Personal OS.\n\n"
        "No runtime database, private history, attachments, or local configuration "
        "is intentionally included. Direct changes may be overwritten by the next "
        "validated snapshot.\n\n"
        f"Generated at: {datetime.now(UTC).isoformat()}\n",
        encoding="utf-8",
        newline="\n",
    )
    copied += 1
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT.parent / "personal-os-public")
    args = parser.parse_args()
    copied = build_snapshot(args.output)
    print(f"Public snapshot created: {args.output.resolve()} ({copied} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
