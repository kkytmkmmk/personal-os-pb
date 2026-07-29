"""Record an explicit human approval for generated synthetic screenshots."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

try:  # Direct script execution and package import are both supported.
    from tools.check_public_screenshots import SCREENSHOT_DIR, find_screenshot_issues, sha256_file
except ModuleNotFoundError:  # pragma: no cover - exercised by the CLI path
    from check_public_screenshots import SCREENSHOT_DIR, find_screenshot_issues, sha256_file


CONFIRMATION = "I visually reviewed every screenshot"


def approve(root: Path, reviewer: str, confirmation: str, approve_all: bool) -> int:
    if not reviewer.strip():
        raise ValueError("--reviewer is required")
    if not approve_all:
        raise ValueError("--approve-all is required for the complete reviewed set")
    if confirmation != CONFIRMATION:
        raise ValueError("confirmation phrase does not match")
    issues = find_screenshot_issues(root, require_approval=False)
    if issues:
        raise ValueError("cannot approve unsafe screenshots: " + "; ".join(issues))
    directory = root.resolve() / SCREENSHOT_DIR
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    timestamp = datetime.now(UTC).isoformat()
    for item in manifest["screenshots"]:
        image = directory / item["file"]
        item.update({"reviewed": True, "reviewed_at": timestamp, "reviewed_by": reviewer.strip(), "sha256": sha256_file(image)})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(manifest["screenshots"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--approve-all", action="store_true")
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    try:
        count = approve(args.root, args.reviewer, args.confirm, args.approve_all)
    except ValueError as error:
        parser.error(str(error))
    print(f"Approved {count} reviewed synthetic screenshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
