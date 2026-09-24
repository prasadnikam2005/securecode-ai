from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional


def run_in_sandbox(
    code: str = "",
    command: Optional[list[str]] = None,
    timeout: int = 10,
    working_dir: Optional[str] = None,
) -> Dict[str, object]:
    """
    Central sandbox execution engine.

    Supports:
    - Running raw Python code
    - Running custom commands (e.g., pytest)
    - Using an existing working directory OR an isolated temp dir
    """

    if not working_dir and (not code or not code.strip()) and not command:
        return {
            "status": "error",
            "output": None,
            "errors": "No code, working directory, or command provided.",
            "returncode": -1,
        }

    if timeout <= 0:
        return {
            "status": "error",
            "output": None,
            "errors": "Invalid timeout value.",
            "returncode": -1,
        }

    temp_dir = None
    exec_dir = None
    main_file = None

    try:
        if working_dir:
            exec_dir = Path(working_dir).resolve()
            if not exec_dir.exists() or not exec_dir.is_dir():
                return {
                    "status": "error",
                    "output": None,
                    "errors": f"Working directory does not exist: {exec_dir}",
                    "returncode": -1,
                }
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix="securecode_sandbox_")
            exec_dir = Path(temp_dir.name)

            if code and code.strip():
                main_file = exec_dir / "main.py"
                main_file.write_text(code, encoding="utf-8", newline="\n")
            elif command is None:
                return {
                    "status": "error",
                    "output": None,
                    "errors": "No code provided for sandbox execution.",
                    "returncode": -1,
                }

        if command:
            exec_command = command
        else:
            if main_file is None:
                return {
                    "status": "error",
                    "output": None,
                    "errors": "No executable file was created for default execution.",
                    "returncode": -1,
                }
            exec_command = [sys.executable, str(main_file)]

        result = subprocess.run(
            exec_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(exec_dir),
        )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        return {
            "status": "success" if result.returncode == 0 else "failed",
            "output": stdout if stdout else "No output.",
            "errors": stderr if stderr else None,
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "output": None,
            "errors": f"Execution timed out after {timeout} seconds.",
            "returncode": -1,
        }

    except Exception as e:
        return {
            "status": "error",
            "output": None,
            "errors": str(e),
            "returncode": -1,
        }

    finally:
        if temp_dir:
            try:
                temp_dir.cleanup()
            except Exception:
                pass