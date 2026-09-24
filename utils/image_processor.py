from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


try:
    import pytesseract
except Exception:
    pytesseract = None


SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


@dataclass
class ImageExtractionResult:
    ok: bool
    text: str = ""
    error: str = ""
    notes: str = ""
    image_size: str = ""
    detected_language: str = "unknown"
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "text": self.text,
            "error": self.error,
            "notes": self.notes,
            "image_size": self.image_size,
            "detected_language": self.detected_language,
            "confidence": self.confidence,
        }


def is_supported_image_filename(filename: str) -> bool:
    if not filename:
        return False
    _, ext = os.path.splitext(filename.lower())
    return ext in SUPPORTED_IMAGE_EXTENSIONS


def load_image(source: Union[str, bytes, bytearray, io.BytesIO, Any]) -> Image.Image:
    """
    Load an image from a path, bytes, BytesIO, or Streamlit UploadedFile-like object.
    """
    if isinstance(source, Image.Image):
        return source.copy()

    if isinstance(source, str):
        return Image.open(source)

    if isinstance(source, (bytes, bytearray)):
        return Image.open(io.BytesIO(source))

    if hasattr(source, "read"):
        data = source.read()
        return Image.open(io.BytesIO(data))

    raise TypeError(f"Unsupported image source type: {type(source)}")


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Basic preprocessing for OCR:
    - convert to grayscale
    - autocontrast
    - sharpen slightly
    """
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.SHARPEN)
    gray = ImageEnhance.Contrast(gray).enhance(1.6)
    return gray


def clean_extracted_text(text: str) -> str:
    """
    Normalize OCR text a bit so code becomes more usable.
    """
    if not text:
        return ""

    text = text.replace("\x0c", "")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()


def looks_like_code(text: str) -> bool:
    """
    Simple heuristic to detect whether OCR output is probably code.
    """
    if not text:
        return False

    indicators = [
        "def ",
        "class ",
        "import ",
        "from ",
        "if __name__",
        "return ",
        "{",
        "}",
        "(",
        ")",
        "=",
        "print(",
    ]

    lower = text.lower()
    score = sum(1 for item in indicators if item in lower)
    return score >= 4


def extract_text_from_image(source: Union[str, bytes, bytearray, io.BytesIO, Any]) -> Dict[str, Any]:
    """
    Extract text from an image using OCR.

    Returns a structured dict so the app can display errors cleanly.
    """
    if pytesseract is None:
        return {
            "ok": False,
            "text": "",
            "error": (
                "pytesseract is not installed. Install pytesseract and Tesseract OCR "
                "to enable image extraction."
            ),
            "notes": "OCR unavailable.",
            "image_size": "",
            "detected_language": "unknown",
            "confidence": None,
        }

    try:
        image = load_image(source)
        image_size = f"{image.width}x{image.height}"

        processed = preprocess_image(image)

        # OCR config tuned for code-like screenshots and dense text.
        ocr_config = "--oem 3 --psm 6"
        raw_text = pytesseract.image_to_string(processed, config=ocr_config)

        cleaned_text = clean_extracted_text(raw_text)

        notes = []
        if not cleaned_text:
            notes.append("OCR returned empty text.")
        elif looks_like_code(cleaned_text):
            notes.append("Extracted text looks code-like.")
        else:
            notes.append("Extracted text looks more like prose than code.")

        return {
            "ok": True,
            "text": cleaned_text,
            "error": "",
            "notes": " ".join(notes),
            "image_size": image_size,
            "detected_language": "unknown",
            "confidence": None,
        }

    except Exception as e:
        return {
            "ok": False,
            "text": "",
            "error": str(e),
            "notes": "Image extraction failed.",
            "image_size": "",
            "detected_language": "unknown",
            "confidence": None,
        }


def image_to_code_candidate(source: Union[str, bytes, bytearray, io.BytesIO, Any]) -> Dict[str, Any]:
    """
    Extract text and return a code-focused payload for the input router.
    """
    result = extract_text_from_image(source)

    if not result.get("ok"):
        return result

    text = result.get("text", "")
    if not text.strip():
        result["notes"] = (result.get("notes", "") + " No usable text found.").strip()
        return result

    return result