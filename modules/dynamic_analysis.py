from __future__ import annotations

from typing import Dict

from utils.sandbox import run_in_sandbox


def run_code_safely(code: str, timeout: int = 10) -> Dict[str, object]:
    """
    Execute Python code safely using the centralized sandbox.

    This is now a thin wrapper over the sandbox layer.
    """

    result = run_in_sandbox(code=code, timeout=timeout)

    return {
        "status": result.get("status"),
        "output": result.get("output"),
        "errors": result.get("errors"),
        "returncode": result.get("returncode"),
    }