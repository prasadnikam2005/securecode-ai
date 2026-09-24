from __future__ import annotations

from typing import Any, Dict, List, Optional

from modules.code_synthesis import fix_code, generate_code
from modules.debugger import explain_bug
from modules.dynamic_analysis import run_code_safely
from modules.static_analysis import run_full_analysis
from modules.test_generator import generate_tests, run_tests
from utils.dependency_manager import dependency_summary
from utils.dependency_policy import DependencyMode, decide_dependency_action
from utils.input_router import InputType, RoutedInput, route_input
from utils.report_builder import ReportSchema, build_report, format_report_for_streamlit


DEFAULT_EXECUTION_TIMEOUT = 10
DEFAULT_PYTEST_TIMEOUT = 30
DEFAULT_DEPENDENCY_MODE = DependencyMode.FALLBACK


def _llm_block(
    ok: bool = True,
    content: str = "",
    error: str = "",
    latency_ms: int = 0,
    model: str = "",
) -> Dict[str, Any]:
    return {
        "ok": ok,
        "content": content,
        "error": error,
        "latency_ms": latency_ms,
        "model": model,
    }


def _safe_notes(notes: Optional[List[str]] = None) -> List[str]:
    if not notes:
        return []
    return [str(note) for note in notes if str(note).strip()]


def _build_dependency_notes(dep_report: Dict[str, Any]) -> List[str]:
    notes: List[str] = []

    missing = dep_report.get("missing_modules", []) or []
    install_command = dep_report.get("install_command", "")

    if missing:
        notes.append(f"Missing dependencies detected: {', '.join(missing)}")
        if install_command:
            notes.append(f"Suggested install command: {install_command}")
    else:
        notes.extend(dep_report.get("notes", []) or [])

    return notes

def _build_bandit_feedback(bandit_result: Dict[str, Any]) -> str:
    issues = bandit_result.get("issues", []) or []
    if not issues:
        return ""

    lines = []
    for item in issues:
        test_id = item.get("test_id", "UNKNOWN")
        issue_text = item.get("issue_text", "")
        severity = item.get("severity", "")
        lines.append(f"- {test_id} [{severity}]: {issue_text}")

    return (
        "You are fixing security vulnerabilities in Python code.\n\n"
        "Bandit detected the following issues:\n"
        + "\n".join(lines)
        + "\n\n"
        "STRICT RULES:\n"
        "- NEVER use hardcoded passwords, secrets, or credentials\n"
        "- Replace hardcoded values with secure input (e.g., input() or getpass.getpass())\n"
        "- Ensure the fix actually removes the vulnerability\n"
        "- Do NOT reintroduce the same issue\n"
        "- Return ONLY corrected Python code\n\n"
        "Fix the code now."
    )

def _run_code_pipeline(
    *,
    input_mode: str,
    original_input: str,
    code: str,
    notes: Optional[List[str]] = None,
) -> ReportSchema:
    """
    Shared pipeline for code-like inputs:
    - static analysis
    - dependency check
    - dependency policy decision
    - dynamic execution
    - test generation + pytest
    - debugger + fixer on execution failure
    """
    notes = _safe_notes(notes)

    
    working_code = code
    auto_fixed_code = ""
    auto_fix_applied = False

    analysis = run_full_analysis(working_code)
    dep_report = dependency_summary(working_code)
    analysis["dependencies"] = dep_report

    notes.extend(_build_dependency_notes(dep_report))

    # Keep the original code for UI/reporting
    original_generated_code = code

    # ---------------------------
    # SECURITY-FIRST AUTO-FIX PASS
    # ---------------------------
    bandit_summary = analysis.get("bandit", {}).get("summary", {}) or {}
    bandit_issues = int(bandit_summary.get("issues_total", 0) or 0)

    if bandit_issues > 0:
        try:
            bandit_feedback = _build_bandit_feedback(analysis.get("bandit", {}))
            security_fixed_code = fix_code(working_code, bandit_feedback)

            if security_fixed_code.strip() and security_fixed_code.strip() != working_code.strip():
                working_code = security_fixed_code
                auto_fixed_code = security_fixed_code
                auto_fix_applied = True
                notes.append(f"Security auto-fix applied based on Bandit issues: {bandit_issues}")

                # Re-run analysis after security fix
                analysis = run_full_analysis(working_code)
                dep_report = dependency_summary(working_code)
                analysis["dependencies"] = dep_report
        except Exception as e:
            notes.append(f"Security auto-fix failed: {str(e)}")

    # ---------------------------
    # CODE-QUALITY AUTO-FIX PASS
    # ---------------------------
    pylint_summary = analysis.get("pylint", {}).get("summary", {}) or {}
    pylint_issues = int(pylint_summary.get("code_message_count", 0) or 0)

    if pylint_issues > 0:
        try:
            pylint_feedback = analysis.get("pylint", {}).get("output", "") or ""
            style_fixed_code = fix_code(working_code, pylint_feedback)

            if style_fixed_code.strip() and style_fixed_code.strip() != working_code.strip():
                working_code = style_fixed_code
                auto_fixed_code = style_fixed_code
                auto_fix_applied = True
                notes.append(f"Style auto-fix applied based on Pylint issues: {pylint_issues}")

                # Re-run analysis after style fix
                analysis = run_full_analysis(working_code)
                dep_report = dependency_summary(working_code)
                analysis["dependencies"] = dep_report
        except Exception as e:
            notes.append(f"Style auto-fix failed: {str(e)}")

    

    dep_decision = decide_dependency_action(
        dep_report.get("missing_modules", []) or [],
        mode=DEFAULT_DEPENDENCY_MODE,
    )
    notes.append(dep_decision.reason)
    
    if dep_report.get("missing_modules"):
        pytest_result = {
            "status": "skipped",
            "output": None,
            "errors": "Execution skipped due to missing dependencies.",
            "summary": {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "generated_tests": 0,
            },
        }
    else:
        generated_tests = generate_tests(working_code)
        pytest_result = run_tests(working_code, generated_tests, timeout=DEFAULT_PYTEST_TIMEOUT) 
    
    # Improve status classification
    if dep_decision.should_stop:
        status = "dependency_blocked"
    elif dep_report.get("missing_modules"):
        status = "partial_success"
    else:
        status = "success"
        

    if dep_decision.should_stop:
        return build_report(
            input_mode=input_mode,
            original_input=original_input,
            generated_code=original_generated_code,
            fixed_code=auto_fixed_code if auto_fix_applied else "",
            bug_explanation="",
            generated_tests="",
            llm_generation=_llm_block(ok=True, content=original_generated_code),
            llm_debug=_llm_block(
                ok=False,
                content="",
                error="Execution stopped due to missing dependencies in strict mode.",
            ),
            analysis=analysis,
            pytest_result={
                "status": "skipped",
                "output": None,
                "errors": "Execution skipped because required dependencies are missing.",
                "summary": {
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "generated_tests": 0,
                },
            },
            status="partial_success",
            notes=notes,
        )

    execution = run_code_safely(working_code, timeout=DEFAULT_EXECUTION_TIMEOUT)

    bug_explanation = ""
    fixed_code = ""
    generated_tests = ""
    pytest_result: Dict[str, Any] = {}

    execution_failed = execution.get("status") in {"failed", "error", "timeout"} or execution.get("returncode", 0) != 0
    execution_error_text = execution.get("errors") or execution.get("output") or ""

    if execution_failed and execution_error_text.strip():
        notes.append("Dynamic execution failed; debugger was invoked.")
        try:
            bug_explanation = explain_bug(working_code, execution_error_text)
        except Exception as e:
            bug_explanation = f"Debugger failed: {str(e)}"

        try:
            fixed_code = fix_code(working_code, execution_error_text)
        except Exception as e:
            fixed_code = ""
            notes.append(f"Auto-fix failed: {str(e)}")

    try:
        generated_tests = generate_tests(working_code)
        pytest_result = run_tests(working_code, generated_tests, timeout=DEFAULT_PYTEST_TIMEOUT)
    except Exception as e:
        pytest_result = {
            "status": "error",
            "errors": str(e),
            "output": None,
            "summary": {},
        }
        notes.append(f"Test generation/execution failed: {str(e)}")

    status = "completed"
    if execution_failed:
        status = "completed_with_issues"
    if pytest_result.get("status") in {"failed", "error", "timeout"}:
        status = "completed_with_issues"

    return build_report(
        input_mode=input_mode,
        original_input=original_input,
        generated_code=original_generated_code,
        fixed_code=auto_fixed_code if auto_fix_applied else fixed_code,
        bug_explanation=bug_explanation,
        generated_tests=generated_tests,
        llm_generation=_llm_block(ok=True, content=original_generated_code),
        llm_debug=_llm_block(ok=bool(bug_explanation.strip()), content=bug_explanation),
        analysis=analysis,
        pytest_result=pytest_result,
        status=status,
        notes=notes,
    )


def run_pipeline(
    text_prompt: str = "",
    code_input: str = "",
    image_input: Any = None,
) -> ReportSchema:
    """
    Main end-to-end pipeline.

    Routes input first, then dispatches to the appropriate processing path.
    """
    routed: RoutedInput = route_input(
        text_prompt=text_prompt,
        code_input=code_input,
        image_input=image_input,
    )

    notes = _safe_notes([routed.notes] if routed.notes else [])

    if routed.input_type == InputType.EMPTY:
        return build_report(
            input_mode=InputType.EMPTY.value,
            original_input="",
            status="empty",
            notes=notes or ["No input provided."],
        )

    if routed.input_type == InputType.CODE_INPUT:
        code = routed.normalized_text.strip()
        if not code:
            return build_report(
                input_mode=InputType.CODE_INPUT.value,
                original_input=routed.raw_text,
                status="error",
                notes=notes or ["Code input was empty after normalization."],
            )
        return _run_code_pipeline(
            input_mode=InputType.CODE_INPUT.value,
            original_input=routed.raw_text,
            code=code,
            notes=notes,
        )

    if routed.input_type == InputType.IMAGE_UPLOAD:
        code = routed.normalized_text.strip()
        if not code:
            return build_report(
                input_mode=InputType.IMAGE_UPLOAD.value,
                original_input="",
                status="error",
                notes=notes or ["Image extraction produced no usable text."],
            )
        return _run_code_pipeline(
            input_mode=InputType.IMAGE_UPLOAD.value,
            original_input=code,
            code=code,
            notes=notes,
        )

    if routed.input_type == InputType.TEXT_PROMPT:
        prompt = routed.normalized_text.strip()
        if not prompt:
            return build_report(
                input_mode=InputType.TEXT_PROMPT.value,
                original_input=routed.raw_text,
                status="error",
                notes=notes or ["Text prompt was empty after normalization."],
            )

        try:
            generated_code = generate_code(prompt)
        except Exception as e:
            return build_report(
                input_mode=InputType.TEXT_PROMPT.value,
                original_input=prompt,
                status="error",
                notes=notes + [f"Code generation failed: {str(e)}"],
            )

        return _run_code_pipeline(
            input_mode=InputType.TEXT_PROMPT.value,
            original_input=prompt,
            code=generated_code,
            notes=notes,
        )

    return build_report(
        input_mode=InputType.UNKNOWN.value,
        original_input=routed.raw_text,
        status="error",
        notes=notes or ["Input type could not be determined."],
    )


def run_pipeline_as_dict(
    text_prompt: str = "",
    code_input: str = "",
    image_input: Any = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper for Streamlit/UI usage.
    """
    report = run_pipeline(
        text_prompt=text_prompt,
        code_input=code_input,
        image_input=image_input,
    )
    return format_report_for_streamlit(report)