import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.dependency_manager import dependency_summary


def _run_command(
    command: list[str],
    timeout: int = 30,
    cwd: Optional[str] = None,
    input_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a command safely and return structured output.
    """
    try:
        result = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return {
            "ok": True,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds.",
        }
    except FileNotFoundError as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command not found: {str(e)}",
        }
    except Exception as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def _write_temp_code(temp_dir: str, code: str) -> Path:
    """
    Write code to a temporary file inside an isolated temp directory.
    """
    file_path = Path(temp_dir) / "target.py"
    file_path.write_text(code, encoding="utf-8", newline="\n")
    return file_path


def _safe_module_command(module_name: str) -> list[str]:
    return [sys.executable, "-m", module_name]


def run_bandit(code: str) -> dict:
    """
    Run Bandit security scanner on a Python code string.
    """
    if not code or not code.strip():
        return {"status": "error", "output": "No code provided.", "issues": [], "summary": {}}

    with tempfile.TemporaryDirectory(prefix="securecode_bandit_") as temp_dir:
        temp_file = _write_temp_code(temp_dir, code)

        command = _safe_module_command("bandit") + ["-f", "json", "-q", str(temp_file)]
        result = _run_command(command, timeout=30, cwd=temp_dir)

        if not result["ok"] and "Command not found" in result["stderr"]:
            return {
                "status": "error",
                "output": "Bandit is not installed or not available in this environment.",
                "issues": [],
                "summary": {},
            }

        raw_output = result["stdout"] or result["stderr"]

        if not result["ok"]:
            return {
                "status": "error",
                "output": raw_output,
                "issues": [],
                "summary": {},
            }

        try:
            payload = json.loads(result["stdout"]) if result["stdout"] else {}
            results = payload.get("results", [])
            metrics = payload.get("metrics", {})
            issues = []

            for item in results:
                issues.append(
                    {
                        "test_id": item.get("test_id", ""),
                        "issue_text": item.get("issue_text", ""),
                        "severity": item.get("issue_severity", ""),
                        "confidence": item.get("issue_confidence", ""),
                        "line_number": item.get("line_number", None),
                        "more_info": item.get("more_info", ""),
                    }
                )

            summary = {
                "issues_total": len(issues),
                "high": metrics.get("_totals", {}).get("SEVERITY.HIGH", 0),
                "medium": metrics.get("_totals", {}).get("SEVERITY.MEDIUM", 0),
                "low": metrics.get("_totals", {}).get("SEVERITY.LOW", 0),
            }

            return {
                "status": "success",
                "output": raw_output if raw_output.strip() else "No issues found.",
                "issues": issues,
                "summary": summary,
            }
        except Exception:
            return {
                "status": "success",
                "output": raw_output if raw_output.strip() else "No issues found.",
                "issues": [],
                "summary": {"issues_total": 0},
            }

def _map_pylint_severity(rule: str) -> str:
    if not rule:
        return "UNKNOWN"

    first = rule[0]

    if first in ("C", "R"):
        return "LOW"
    elif first == "W":
        return "MEDIUM"
    elif first == "E":
        return "HIGH"
    elif first == "F":
        return "CRITICAL"
    else:
        return "UNKNOWN"
    
    
def _classify_pylint_lines(raw_output: str, missing_modules: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse and classify pylint output into structured, deduplicated issues.
    """

    missing_modules = [m.lower() for m in (missing_modules or [])]

    code_issues: Dict[str, Dict[str, Any]] = {}
    environment_issues: List[str] = []

    # Regex for pylint message
    pattern = re.compile(r":(\d+):\d+:\s([A-Z]\d+):\s(.+)")

    for line in (raw_output or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        lowered = stripped.lower()

        # --- Detect dependency issues ---
        is_dependency_related = False
        if (
            "unable to import" in lowered
            or "import-error" in lowered
            or "modulenotfounderror" in lowered
        ):
            is_dependency_related = True

        for module in missing_modules:
            if module and module in lowered:
                is_dependency_related = True
                break

        if is_dependency_related:
            environment_issues.append(stripped)
            continue

        # --- Skip score line ---
        if stripped.startswith("Your code has been rated at"):
            continue

        # --- Structured parsing ---
        match = pattern.search(stripped)
        if match:
            line_no = int(match.group(1))
            rule = match.group(2)
            message = match.group(3)

            key = f"{line_no}:{rule}"

            if key not in code_issues:
                severity = _map_pylint_severity(rule)

                code_issues[key] = {
                    "line": line_no,
                    "rule": rule,
                    "severity": severity,
                    "message": message,
                    "raw": stripped,
                }

    return {
        "code_messages": list(code_issues.values()),
        "environment_messages": environment_issues,
    }


def run_pylint(code: str, missing_modules: Optional[List[str]] = None) -> dict:
    """
    Run Pylint on a Python code string.
    Returns structured results including score and separated message categories.
    """
    if not code or not code.strip():
        return {
            "status": "error",
            "output": "No code provided.",
            "messages": [],
            "environment_messages": [],
            "summary": {},
        }

    missing_modules = missing_modules or []

    with tempfile.TemporaryDirectory(prefix="securecode_pylint_") as temp_dir:
        temp_file = _write_temp_code(temp_dir, code)

        command = _safe_module_command("pylint") + [
            str(temp_file),
            "--score=y",
            "--reports=n",
            "--output-format=text",
            "--disable=C0114,C0115,C0116",
        ]
        result = _run_command(command, timeout=30, cwd=temp_dir)

        if not result["ok"] and "Command not found" in result["stderr"]:
            return {
                "status": "error",
                "output": "Pylint is not installed or not available in this environment.",
                "messages": [],
                "environment_messages": [],
                "summary": {},
            }

        raw_output = (result["stdout"] or "") + ("\n" + result["stderr"] if result["stderr"] else "")
        raw_output = raw_output.strip()

        if not result["ok"] and not raw_output:
            return {
                "status": "error",
                "output": "Pylint failed without producing output.",
                "messages": [],
                "environment_messages": [],
                "summary": {},
            }

        score_match = re.search(r"rated at (-?\d+(\.\d+)?)/10", raw_output)
        score = float(score_match.group(1)) if score_match else None

        classified = _classify_pylint_lines(raw_output, missing_modules)
        code_messages = classified["code_messages"]
        environment_messages = classified["environment_messages"]

        filtered_output = "\n".join([msg["raw"] for msg in code_messages]).strip()
        if not filtered_output:
            filtered_output = "No code-quality issues found."

        severity_counts = {
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0,
            "CRITICAL": 0,
        }

        for msg in code_messages:
            sev = msg.get("severity", "UNKNOWN")
            if sev in severity_counts:
                severity_counts[sev] += 1

        summary = {
            "score": score,
            "message_count": len(code_messages) + len(environment_messages),
            "code_message_count": len(code_messages),
            "environment_message_count": len(environment_messages),

            # 🔥 NEW
            "severity_counts": severity_counts,
        }

        return {
            "status": "success",
            "output": filtered_output,
            "messages": code_messages,
            "environment_messages": environment_messages,
            "summary": summary,
        }


def run_semgrep(code: str) -> dict:
    """
    Run Semgrep with a local security scan if available.
    """
    if not code or not code.strip():
        return {"status": "error", "output": "No code provided.", "findings": [], "summary": {}}

    if shutil.which("semgrep") is None:
        return {
            "status": "skipped",
            "output": "Semgrep is not installed or not available in this environment.",
            "findings": [],
            "summary": {},
        }

    result = _run_command(
        ["semgrep", "--config=auto", "--json", "-"],
        timeout=30,
        input_text=code,
    )

    if not result["ok"]:
        return {
            "status": "error",
            "output": result["stderr"] or "Semgrep failed.",
            "findings": [],
            "summary": {},
        }

    try:
        payload = json.loads(result["stdout"]) if result["stdout"] else {}
        findings = payload.get("results", [])
        return {
            "status": "success",
            "output": result["stdout"] if result["stdout"].strip() else "No issues found.",
            "findings": findings,
            "summary": {"findings_total": len(findings)},
        }
    except Exception:
        return {
            "status": "success",
            "output": result["stdout"] if result["stdout"].strip() else "No issues found.",
            "findings": [],
            "summary": {"findings_total": 0},
        }


def run_full_analysis(code: str) -> dict:
    """
    Run static analysis safely with dependency awareness.
    """
    dep_report = dependency_summary(code)
    missing_modules = dep_report.get("missing_modules", []) or []

    analysis_result = {
        "dependencies": dep_report,
    }

    try:
        analysis_result["bandit"] = run_bandit(code)
    except Exception as e:
        analysis_result["bandit"] = {
            "status": "error",
            "output": str(e),
            "issues": [],
            "summary": {},
        }

    try:
        analysis_result["pylint"] = run_pylint(code, missing_modules=missing_modules)
    except Exception as e:
        analysis_result["pylint"] = {
            "status": "error",
            "output": str(e),
            "messages": [],
            "environment_messages": [],
            "summary": {},
        }

    try:
        analysis_result["semgrep"] = run_semgrep(code)
    except Exception as e:
        analysis_result["semgrep"] = {
            "status": "error",
            "output": str(e),
            "findings": [],
            "summary": {},
        }

    bandit_issues = analysis_result.get("bandit", {}).get("summary", {}).get("issues_total", 0) or 0
    semgrep_findings = analysis_result.get("semgrep", {}).get("summary", {}).get("findings_total", 0) or 0
    pylint_score = analysis_result.get("pylint", {}).get("summary", {}).get("score", None)
    dependency_missing_count = len(dep_report.get("missing_modules", []) or [])

    pylint_code_issues = analysis_result.get("pylint", {}).get("summary", {}).get("code_message_count", 0)

    analysis_result["summary"] = {
        # 🔐 Security
        "bandit_issues": int(bandit_issues),
        "semgrep_findings": int(semgrep_findings),

        # 🧹 Code quality
        "pylint_issues": int(pylint_code_issues),
        "pylint_score": pylint_score,

        # ⚠️ Environment
        "dependency_missing_count": dependency_missing_count,

        # 📊 Total (only meaningful issues)
        "total_static_issues": int(bandit_issues) + int(semgrep_findings) + int(pylint_code_issues),
}

    return analysis_result