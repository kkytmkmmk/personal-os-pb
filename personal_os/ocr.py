"""Optional local OCR boundary.

The Personal OS remains dependency-light: OCR is used when Pillow,
pytesseract and the local Tesseract executable are available. Failure never
blocks preservation of the original image or the later vision fallback.
"""

from __future__ import annotations

from io import BytesIO


def extract_text(image_bytes: bytes, languages: str = "jpn+eng") -> dict[str, object]:
    try:
        from PIL import Image
        import pytesseract
        from pytesseract import Output
    except ImportError:
        return {"available": False, "text": "", "confidence": 0.0, "engine": "none"}
    try:
        image = Image.open(BytesIO(image_bytes))
        data = pytesseract.image_to_data(image, lang=languages, output_type=Output.DICT)
        words = []
        confidences = []
        for text, confidence in zip(data.get("text", []), data.get("conf", [])):
            cleaned = str(text or "").strip()
            try:
                score = float(confidence)
            except (TypeError, ValueError):
                score = -1
            if cleaned:
                words.append(cleaned)
                if score >= 0:
                    confidences.append(score / 100.0)
        return {
            "available": True,
            "text": " ".join(words),
            "confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            "engine": "tesseract",
        }
    except Exception as error:  # optional native executable and image codecs
        return {
            "available": False,
            "text": "",
            "confidence": 0.0,
            "engine": "tesseract",
            "error": str(error)[:500],
        }


def is_sufficient(result: dict[str, object], minimum_characters: int = 40) -> bool:
    text = "".join(str(result.get("text") or "").split())
    readable = sum(character.isalnum() or "\u3040" <= character <= "\u9fff" for character in text)
    return (
        bool(result.get("available"))
        and readable >= minimum_characters
        and float(result.get("confidence") or 0.0) >= 0.45
    )

