import os
import time
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
DEFAULT_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "2048"))


@dataclass
class LLMResponse:
    ok: bool
    content: str = ""
    error: str = ""
    model: str = ""
    latency_ms: int = 0


def _get_api_key() -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is missing. Add it to your .env file before running the app."
        )
    return api_key


def _build_client() -> Groq:
    return Groq(api_key=_get_api_key())


def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.3,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
) -> LLMResponse:
    """
    Core Groq LLM wrapper.

    Returns a structured response so downstream modules can handle success/failure cleanly.
    """
    start_time = time.perf_counter()
    chosen_model = model or DEFAULT_MODEL

    try:
        client = _build_client()

        response = client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_message.strip()},
            ],
            temperature=temperature,
            max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
        )

        content = ""
        if response and response.choices:
            content = response.choices[0].message.content or ""

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        if not content.strip():
            return LLMResponse(
                ok=False,
                error="LLM returned an empty response.",
                model=chosen_model,
                latency_ms=elapsed_ms,
            )

        return LLMResponse(
            ok=True,
            content=content.strip(),
            model=chosen_model,
            latency_ms=elapsed_ms,
        )

    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return LLMResponse(
            ok=False,
            error=str(e),
            model=chosen_model,
            latency_ms=elapsed_ms,
        )


def test_connection() -> LLMResponse:
    return call_llm(
        system_prompt="You are a helpful assistant.",
        user_message="Say exactly: API connection successful",
        temperature=0.0,
        max_tokens=32,
    )