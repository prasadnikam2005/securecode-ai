from modules.llm_core import call_llm

SYSTEM_PROMPT = """You are an expert Python debugger and code explainer.

Your job:
- Identify the root cause of the bug
- Explain it in simple, beginner-friendly English
- Mention the likely fix clearly
- Keep the response concise and practical

Rules:
- Do not write code unless it is needed for a tiny fix example
- Do not over-explain
- If the error message is missing, infer from the code carefully and say so
"""


def _build_explain_message(code: str, error: str) -> str:
    error_text = error.strip() if error and error.strip() else "No error message provided."

    return (
        "Analyze the following Python code and explain the bug.\n\n"
        f"Code:\n{code.strip()}\n\n"
        f"Error:\n{error_text}\n\n"
        "Return a short explanation with:\n"
        "1. Root cause\n"
        "2. Why it happened\n"
        "3. How to fix it"
    )


def explain_bug(code: str, error: str = "") -> str:
    """
    Explain a bug in plain English.
    Raises RuntimeError if the LLM call fails.
    """
    if not code or not code.strip():
        raise ValueError("code cannot be empty.")

    response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=_build_explain_message(code, error),
        temperature=0.2,
    )

    if not response.ok:
        raise RuntimeError(f"Bug explanation failed: {response.error}")

    return response.content.strip()