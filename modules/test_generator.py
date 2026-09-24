from __future__ import annotations

import sys
import re
import tempfile
from pathlib import Path
from typing import Dict

from modules.llm_core import call_llm
from utils.sandbox import run_in_sandbox


SYSTEM_PROMPT = """You are an expert Python testing engineer.

Your job is to generate high-quality pytest test cases for the given Python code.

Rules:
- Return only raw pytest code
- Do not wrap in markdown fences
- Do not include explanations
- Use clear test names
- Prefer deterministic tests
- Focus on correctness, edge cases, and basic error handling
- Do not invent unavailable imports
"""


def strip_markdown(code: str) -> str:
    if not code:
        return ""

    text = code.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:-1] if len(lines) >= 2 else lines
        text = "\n".join(lines).strip()

    if text.startswith("python\n"):
        text = text[len("python\n"):].lstrip()

    return text.strip()


def _build_prompt(code: str, target_name: str = "target") -> str:
    return (
        "Generate pytest test cases for the following Python code.\n\n"
        f"The code will be available as `{target_name}.py` and should be imported using `import {target_name}`.\n\n"
        f"Code:\n{code.strip()}\n\n"
        "Return only raw pytest code."
    )


def generate_tests(code: str, target_name: str = "target") -> str:
    if not code or not code.strip():
        raise ValueError("code cannot be empty.")

    response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=_build_prompt(code, target_name),
        temperature=0.2,
    )

    if not response.ok:
        raise RuntimeError(f"Test generation failed: {response.error}")

    return strip_markdown(response.content)


def _count_tests(test_code: str) -> int:
    return len(re.findall(r"^\s*def\s+test_", test_code, re.MULTILINE))


def _prepare_project(code: str, tests: str) -> Path:
    """
    Minimal project setup only (no execution logic here).
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="securecode_tests_"))

    (temp_dir / "target.py").write_text(code, encoding="utf-8")
    (temp_dir / "test_target.py").write_text(tests, encoding="utf-8")

    return temp_dir


def run_tests(code: str, tests: str, timeout: int = 30) -> Dict[str, object]:
    """
    Run pytest using the centralized sandbox.
    """

    if not code.strip():
        return {"status": "error", "errors": "No code provided."}

    if not tests.strip():
        return {"status": "error", "errors": "No tests provided."}

    temp_dir = None

    try:
        temp_dir = _prepare_project(code, tests)

        result = run_in_sandbox(
            command=[sys.executable, "-m", "pytest", "-q"],
            timeout=timeout,
            working_dir=str(temp_dir),
        )

        summary_text = (result.get("output") or "") + (result.get("errors") or "")

        passed = int(re.search(r"(\d+)\s+passed", summary_text).group(1)) if re.search(r"(\d+)\s+passed", summary_text) else 0
        failed = int(re.search(r"(\d+)\s+failed", summary_text).group(1)) if re.search(r"(\d+)\s+failed", summary_text) else 0
        skipped = int(re.search(r"(\d+)\s+skipped", summary_text).group(1)) if re.search(r"(\d+)\s+skipped", summary_text) else 0

        return {
            "status": result.get("status"),
            "output": result.get("output"),
            "errors": result.get("errors"),
            "summary": {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "generated_tests": _count_tests(tests),
            },
        }

    finally:
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def generate_and_run_tests(code: str, timeout: int = 30) -> Dict[str, object]:
    """
    Full pipeline: generate + execute tests
    """
    tests = generate_tests(code)
    execution = run_tests(code, tests, timeout)

    return {
        "tests": tests,
        "execution": execution,
    }