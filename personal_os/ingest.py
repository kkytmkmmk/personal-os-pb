"""Pure upload parsing and image validation helpers.

Persistence and fact extraction stay in the application layer so this module
can be tested without opening the Personal OS database or contacting an LLM.
"""

from __future__ import annotations

import re


def multipart_file(body: bytes, content_type: str) -> bytes:
    match = re.search(r"boundary=([^;]+)", content_type)
    if not match:
        raise ValueError("A multipart form boundary is required")
    boundary = match.group(1).strip('"').encode()
    for part in body.split(b"--" + boundary):
        header, separator, payload = part.partition(b"\r\n\r\n")
        if separator and b"filename=" in header:
            return payload.rsplit(b"\r\n", 1)[0]
    raise ValueError("No uploaded file was found")


def multipart_form_file(body: bytes, content_type: str) -> tuple[bytes, str, str, dict[str, str]]:
    """Read one uploaded file and ordinary UTF-8 multipart fields."""
    match = re.search(r"boundary=([^;]+)", content_type)
    if not match:
        raise ValueError("A multipart form is required")
    boundary = match.group(1).strip('"').encode()
    uploaded: tuple[bytes, str, str] | None = None
    fields: dict[str, str] = {}
    for part in body.split(b"--" + boundary):
        header, separator, payload = part.partition(b"\r\n\r\n")
        if not separator:
            continue
        payload = payload.rsplit(b"\r\n", 1)[0]
        disposition = header.decode("utf-8", "replace")
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        if filename_match:
            content_type_match = re.search(
                r"Content-Type:\s*([^\r\n;]+)", disposition, re.IGNORECASE
            )
            uploaded = (
                payload,
                filename_match.group(1) or "screenshot",
                content_type_match.group(1) if content_type_match else "",
            )
        else:
            fields[name_match.group(1)] = payload.decode("utf-8", "replace").strip()
    if not uploaded:
        raise ValueError("No image file was supplied")
    return (*uploaded, fields)


def detect_image_mime(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None
