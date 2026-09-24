from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional

from utils.image_processor import image_to_code_candidate


class InputType(str, Enum):
    TEXT_PROMPT = "text_prompt"
    CODE_INPUT = "code_input"
    IMAGE_UPLOAD = "image_upload"
    EMPTY = "empty"
    UNKNOWN = "unknown"


@dataclass
class RoutedInput:
    input_type: InputType
    raw_text: str = ""
    normalized_text: str = ""
    confidence: float = 0.0
    notes: str = ""
    image_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["input_type"] = self.input_type.value
        return data


def _clean_text(text: str) -> str:
    if not text:
        return ""
    return text.strip()


def _looks_like_code(text: str) -> bool:
    if not text:
        return False

    stripped = text.strip()
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if not lines:
        return False

    code_markers = [
        "def ",
        "class ",
        "import ",
        "from ",
        "return ",
        "print(",
        "if __name__",
        "try:",
        "except:",
        "{",
        "}",
        ";",
        "=>",
        "console.log(",
        "public static void main",
    ]

    score = 0
    lower = stripped.lower()

    for marker in code_markers:
        if marker.lower() in lower:
            score += 1

    # Extra signal: multiple indented lines or code-like punctuation
    if any(line.startswith(("    ", "\t")) for line in lines):
        score += 1
    if stripped.count("(") + stripped.count(")") >= 4:
        score += 1
    if stripped.count("=") >= 2:
        score += 1

    return score >= 3


def _looks_like_natural_language(text: str) -> bool:
    if not text:
        return False

    stripped = text.strip()
    if len(stripped) < 10:
        return False

    # If it has a sentence-like structure and not many code markers, treat as prompt.
    return not _looks_like_code(stripped)


def route_input(
    text_prompt: str = "",
    code_input: str = "",
    image_input: Any = None,
) -> RoutedInput:
    """
    Route the user input into one of the supported modes:
    - text prompt
    - pasted code
    - image upload

    Priority:
    1. code_input if clearly code
    2. image_input if provided
    3. text_prompt
    """
    text_prompt = _clean_text(text_prompt)
    code_input = _clean_text(code_input)

    # 1) Prefer explicit code input if present
    if code_input:
        if _looks_like_code(code_input):
            return RoutedInput(
                input_type=InputType.CODE_INPUT,
                raw_text=code_input,
                normalized_text=code_input,
                confidence=0.95,
                notes="Detected pasted code input.",
            )
        # If user pasted text into code box but it does not look like code,
        # still treat it as code input because UI intent matters.
        return RoutedInput(
            input_type=InputType.CODE_INPUT,
            raw_text=code_input,
            normalized_text=code_input,
            confidence=0.75,
            notes="Received text in code input area; treated as code input by UI intent.",
        )

    # 2) Image input
    if image_input is not None:
        image_result = image_to_code_candidate(image_input)

        if image_result.get("ok"):
            extracted = _clean_text(image_result.get("text", ""))
            return RoutedInput(
                input_type=InputType.IMAGE_UPLOAD,
                raw_text="",
                normalized_text=extracted,
                confidence=0.85 if extracted else 0.5,
                notes=image_result.get("notes", "Image processed successfully."),
                image_result=image_result,
            )

        return RoutedInput(
            input_type=InputType.IMAGE_UPLOAD,
            raw_text="",
            normalized_text="",
            confidence=0.0,
            notes=image_result.get("error", "Image extraction failed."),
            image_result=image_result,
        )

    # 3) Text prompt
    if text_prompt:
        if _looks_like_natural_language(text_prompt):
            return RoutedInput(
                input_type=InputType.TEXT_PROMPT,
                raw_text=text_prompt,
                normalized_text=text_prompt,
                confidence=0.90,
                notes="Detected natural language prompt.",
            )

        return RoutedInput(
            input_type=InputType.UNKNOWN,
            raw_text=text_prompt,
            normalized_text=text_prompt,
            confidence=0.55,
            notes="Input is ambiguous; treat carefully in pipeline.",
        )

    # 4) Empty
    return RoutedInput(
        input_type=InputType.EMPTY,
        raw_text="",
        normalized_text="",
        confidence=1.0,
        notes="No input provided.",
    )


def route_input_dict(
    text_prompt: str = "",
    code_input: str = "",
    image_input: Any = None,
) -> Dict[str, Any]:
    """
    Dict-friendly wrapper for Streamlit and pipeline usage.
    """
    return route_input(
        text_prompt=text_prompt,
        code_input=code_input,
        image_input=image_input,
    ).to_dict()