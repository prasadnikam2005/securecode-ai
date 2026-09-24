from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional


@dataclass
class AnalysisSummary:
    total_static_issues: int = 0
    bandit_issues: int = 0
    semgrep_findings: int = 0
    pylint_issues: int = 0
    pylint_score: Optional[float] = None
    pytest_passed: int = 0
    pytest_failed: int = 0
    pytest_skipped: int = 0
    dependency_missing_count: int = 0


@dataclass
class LLMBlock:
    ok: bool = False
    content: str = ""
    error: str = ""
    latency_ms: int = 0
    model: str = ""


@dataclass
class ReportSchema:
    input_mode: str
    original_input: str = ""
    generated_code: str = ""
    fixed_code: str = ""
    bug_explanation: str = ""
    generated_tests: str = ""
    llm_generation: LLMBlock = field(default_factory=LLMBlock)
    llm_debug: LLMBlock = field(default_factory=LLMBlock)
    analysis_summary: AnalysisSummary = field(default_factory=AnalysisSummary)
    bandit: Dict[str, Any] = field(default_factory=dict)
    pylint: Dict[str, Any] = field(default_factory=dict)
    semgrep: Dict[str, Any] = field(default_factory=dict)
    pytest: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, Any] = field(default_factory=dict)
    status: str = "draft"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_get(obj: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    if not isinstance(obj, dict):
        return default
    return obj.get(key, default)


def build_analysis_summary(
    analysis: Optional[Dict[str, Any]] = None,
    pytest_result: Optional[Dict[str, Any]] = None,
) -> AnalysisSummary:
    """
    Build a normalized summary from static analysis, dependency, and pytest output.
    """
    analysis = analysis or {}
    pytest_result = pytest_result or {}

    bandit_summary = _safe_get(analysis.get("bandit"), "summary", {}) or {}
    pylint_summary = _safe_get(analysis.get("pylint"), "summary", {}) or {}
    severity_counts = pylint_summary.get("severity_counts", {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    })
    semgrep_summary = _safe_get(analysis.get("semgrep"), "summary", {}) or {}
    dependency_report = analysis.get("dependencies", {}) or {}
    pytest_summary = _safe_get(pytest_result, "summary", {}) or {}

    bandit_issues = int(bandit_summary.get("issues_total", 0) or 0)
    semgrep_findings = int(semgrep_summary.get("findings_total", 0) or 0)
    pylint_code_issues = int(pylint_summary.get("code_message_count", 0) or 0)
    pylint_score = pylint_summary.get("score", None)
    missing_count = len(dependency_report.get("missing_modules", []) or [])

    passed = int(pytest_summary.get("passed", 0) or 0)
    failed = int(pytest_summary.get("failed", 0) or 0)
    skipped = int(pytest_summary.get("skipped", 0) or 0)

    return AnalysisSummary(
        total_static_issues=bandit_issues + semgrep_findings + pylint_code_issues,
        bandit_issues=bandit_issues,
        semgrep_findings=semgrep_findings,
        pylint_issues=pylint_code_issues,
        pylint_score=pylint_score,
        pytest_passed=passed,
        pytest_failed=failed,
        pytest_skipped=skipped,
        dependency_missing_count=missing_count,
    )


def build_report(
    *,
    input_mode: str,
    original_input: str = "",
    generated_code: str = "",
    fixed_code: str = "",
    bug_explanation: str = "",
    generated_tests: str = "",
    llm_generation: Optional[Dict[str, Any]] = None,
    llm_debug: Optional[Dict[str, Any]] = None,
    analysis: Optional[Dict[str, Any]] = None,
    pytest_result: Optional[Dict[str, Any]] = None,
    status: str = "draft",
    notes: Optional[List[str]] = None,
) -> ReportSchema:
    """
    Create one consistent report object for the whole pipeline.
    """
    llm_generation = llm_generation or {}
    llm_debug = llm_debug or {}
    analysis = analysis or {}
    pytest_result = pytest_result or {}

    report = ReportSchema(
        input_mode=input_mode,
        original_input=original_input,
        generated_code=generated_code,
        fixed_code=fixed_code,
        bug_explanation=bug_explanation,
        generated_tests=generated_tests,
        llm_generation=LLMBlock(
            ok=bool(llm_generation.get("ok", False)),
            content=str(llm_generation.get("content", "") or ""),
            error=str(llm_generation.get("error", "") or ""),
            latency_ms=int(llm_generation.get("latency_ms", 0) or 0),
            model=str(llm_generation.get("model", "") or ""),
        ),
        llm_debug=LLMBlock(
            ok=bool(llm_debug.get("ok", False)),
            content=str(llm_debug.get("content", "") or ""),
            error=str(llm_debug.get("error", "") or ""),
            latency_ms=int(llm_debug.get("latency_ms", 0) or 0),
            model=str(llm_debug.get("model", "") or ""),
        ),
        analysis_summary=build_analysis_summary(analysis, pytest_result),
        bandit=analysis.get("bandit", {}) if isinstance(analysis, dict) else {},
        pylint=analysis.get("pylint", {}) if isinstance(analysis, dict) else {},
        semgrep=analysis.get("semgrep", {}) if isinstance(analysis, dict) else {},
        dependencies=analysis.get("dependencies", {}) if isinstance(analysis, dict) else {},
        pytest=pytest_result if isinstance(pytest_result, dict) else {},
        status=status,
        notes=notes or [],
    )

    return report


def format_report_for_streamlit(report: ReportSchema) -> Dict[str, Any]:
    """
    Flatten the report into UI-friendly sections.
    """
    data = report.to_dict()

    bandit_output = _safe_get(data.get("bandit"), "output", "No Bandit output.")
    pylint_output = _safe_get(data.get("pylint"), "output", "No Pylint output.")
    semgrep_output = _safe_get(data.get("semgrep"), "output", "No Semgrep output.")
    pytest_output = _safe_get(data.get("pytest"), "output", "No pytest output.")
    pytest_errors = _safe_get(data.get("pytest"), "errors", None)

    dependencies = data.get("dependencies", {}) or {}
    missing_modules = dependencies.get("missing_modules", []) or []
    install_command = dependencies.get("install_command", "")

    return {
        "meta": {
            "input_mode": data.get("input_mode", ""),
            "status": data.get("status", ""),
            "notes": data.get("notes", []),
        },
        "code": {
            "original_input": data.get("original_input", ""),
            "generated_code": data.get("generated_code", ""),
            "fixed_code": data.get("fixed_code", ""),
            "generated_tests": data.get("generated_tests", ""),
        },
        "llm": {
            "generation": data.get("llm_generation", {}),
            "debug": data.get("llm_debug", {}),
            "bug_explanation": data.get("bug_explanation", ""),
        },
        "analysis": {
            "summary": data.get("analysis_summary", {}),
            "bandit": bandit_output,
            "pylint": pylint_output,
            "semgrep": semgrep_output,
            "dependencies": dependencies,
            "missing_modules": missing_modules,
            "install_command": install_command,
        },
        "pytest": {
            "output": pytest_output,
            "errors": pytest_errors,
            "details": data.get("pytest", {}),
        },
    }


def report_to_dict(report: ReportSchema) -> Dict[str, Any]:
    """
    Convenience helper for saving/exporting the report.
    """
    return report.to_dict()