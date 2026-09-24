from modules.llm_core import call_llm

SYSTEM_PROMPT = """You are a senior Python security engineer generating production-grade code.

STRICT REQUIREMENTS (must follow):
- Follow PEP8 strictly
- Max line length: 100 characters
- Add a final newline at end of file
- Use correct import order:
  1. Standard library
  2. Third-party
  3. Local imports
- No unused imports
- No wildcard imports
- Keep functions small and modular
- Use clear variable names
- Include basic input validation where appropriate

SECURITY RULES:
- Never use eval() or exec()
- Prefer safe standard-library implementations
- Avoid insecure patterns

OUTPUT RULES:
- Return ONLY raw Python code
- No markdown
- No explanations
"""


def strip_markdown(code: str) -> str:
    """
    Remove markdown code fences and surrounding noise from LLM output.
    """
    if not code:
        return ""

    text = code.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if text.startswith("python\n"):
        text = text[len("python\n"):].lstrip()

    return text.strip()


def enforce_basic_formatting(code: str) -> str:
    """
    Deterministically clean code after LLM output.

    This does NOT try to be a full formatter.
    It only guarantees:
    - trailing spaces removed
    - extra blank lines at the end removed
    - file ends with exactly one newline
    """
    if not code:
        return ""

    lines = [line.rstrip() for line in code.splitlines()]
    formatted = "\n".join(lines).rstrip()

    if formatted:
        return formatted + "\n"

    return ""


def _build_generation_message(user_prompt: str) -> str:
    return (
        "Generate production-ready Python code.\n\n"
        "Requirements:\n"
        "- Follow all rules strictly\n"
        "- Ensure code passes linting (PEP8)\n"
        "- Ensure no line exceeds 100 characters\n"
        "- Ensure file ends with a newline\n\n"
        f"Task:\n{user_prompt.strip()}\n"
    )


def _build_fix_message(buggy_code: str, error_message: str) -> str:
    return (
        "Fix the following Python code.\n\n"
        "STRICT REQUIREMENTS:\n"
        "- Fix ALL errors\n"
        "- Ensure PEP8 compliance\n"
        "- Max line length: 100\n"
        "- Proper import order\n"
        "- Add final newline\n"
        "- Remove unused imports\n\n"
        f"Code:\n{buggy_code.strip()}\n\n"
        f"Error:\n{error_message.strip() or 'No error provided'}\n\n"
        "Return ONLY corrected Python code."
    )


def generate_code(user_prompt: str) -> str:
    """
    Generate secure Python code from a natural language prompt.
    Raises RuntimeError if the LLM call fails.
    """
    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt cannot be empty.")

    response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=_build_generation_message(user_prompt),
        temperature=0.2,
    )

    if not response.ok:
        raise RuntimeError(f"Code generation failed: {response.error}")

    code = strip_markdown(response.content)
    return enforce_basic_formatting(code)


def fix_code(buggy_code: str, error_message: str) -> str:
    """
    Fix buggy code given the error message.
    Raises RuntimeError if the LLM call fails.
    """
    if not buggy_code or not buggy_code.strip():
        raise ValueError("buggy_code cannot be empty.")

    response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=_build_fix_message(buggy_code, error_message),
        temperature=0.2,
    )

    if not response.ok:
        raise RuntimeError(f"Code fixing failed: {response.error}")

    code = strip_markdown(response.content)
    return enforce_basic_formatting(code)