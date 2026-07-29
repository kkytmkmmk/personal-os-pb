"""Validate reviewed synthetic screenshots before a public snapshot is built.

The check is intentionally structural.  It rejects unregistered PNG files,
metadata chunks, unsupported dimensions and any manifest entry that is not
explicitly synthetic and reviewed.  A human visual review remains required.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path


SCREENSHOT_DIR = Path("docs/screenshots/ux-phase5")
MAX_BYTES = 2 * 1024 * 1024
MAX_COUNT = 80
ALLOWED_VIEWPORTS = {(1280, 720), (1440, 900), (390, 844), (375, 667)}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TEXT_CHUNKS = {b"tEXt", b"zTXt", b"iTXt"}
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.png$")


def png_dimensions_and_metadata(path: Path) -> tuple[tuple[int, int] | None, list[str]]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        return None, ["not a PNG"]
    cursor = len(PNG_SIGNATURE)
    dimensions: tuple[int, int] | None = None
    issues: list[str] = []
    while cursor < len(data):
        if cursor + 12 > len(data):
            return dimensions, [*issues, "truncated PNG chunk"]
        length = struct.unpack(">I", data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        payload_end = cursor + 8 + length
        if payload_end + 4 > len(data):
            return dimensions, [*issues, "invalid PNG chunk length"]
        payload = data[cursor + 8:payload_end]
        if kind == b"IHDR":
            if length != 13:
                issues.append("invalid IHDR")
            else:
                dimensions = struct.unpack(">II", payload[:8])
        if kind in TEXT_CHUNKS:
            issues.append(f"metadata chunk {kind.decode('ascii')}")
        cursor = payload_end + 4
        if kind == b"IEND":
            break
    return dimensions, issues


def find_screenshot_issues(root: Path) -> list[str]:
    directory = root.resolve() / SCREENSHOT_DIR
    if not directory.exists():
        return []
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return ["manifest.json is missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"invalid manifest: {error}"]
    entries = manifest.get("screenshots") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        return ["manifest screenshots must be a non-empty list"]
    if len(entries) > MAX_COUNT:
        return [f"screenshot count exceeds {MAX_COUNT}"]
    registered: set[str] = set()
    issues: list[str] = []
    for item in entries:
        if not isinstance(item, dict):
            issues.append("manifest contains a non-object entry")
            continue
        name = item.get("file")
        viewport = item.get("viewport")
        if not isinstance(name, str) or not NAME.fullmatch(name):
            issues.append(f"invalid screenshot file name: {name!r}")
            continue
        registered.add(name)
        if item.get("data_type") != "synthetic":
            issues.append(f"{name}: data_type must be synthetic")
        if item.get("contains_sensitive_data") is not False:
            issues.append(f"{name}: contains_sensitive_data must be false")
        if item.get("reviewed") is not True:
            issues.append(f"{name}: reviewed must be true")
        if not isinstance(item.get("route"), str) or not item["route"].startswith("#"):
            issues.append(f"{name}: route must be a hash route")
        if not isinstance(viewport, dict):
            issues.append(f"{name}: viewport is missing")
            continue
        dimensions = (viewport.get("width"), viewport.get("height"))
        if dimensions not in ALLOWED_VIEWPORTS:
            issues.append(f"{name}: unsupported viewport {dimensions}")
            continue
        image = directory / name
        if not image.is_file():
            issues.append(f"{name}: registered PNG is missing")
            continue
        if image.stat().st_size > MAX_BYTES:
            issues.append(f"{name}: exceeds {MAX_BYTES} bytes")
        actual, png_issues = png_dimensions_and_metadata(image)
        if actual != dimensions:
            issues.append(f"{name}: PNG dimensions {actual} do not match {dimensions}")
        issues.extend(f"{name}: {issue}" for issue in png_issues)
    actual_names = {path.name for path in directory.glob("*.png")}
    for name in sorted(actual_names - registered):
        issues.append(f"unregistered screenshot: {name}")
    for name in sorted(registered - actual_names):
        issues.append(f"registered screenshot missing: {name}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    issues = find_screenshot_issues(args.root)
    if issues:
        print("Public screenshot safety: FAIL")
        print("\n".join(issues))
        return 1
    print("Public screenshot safety: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
