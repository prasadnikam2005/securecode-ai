from __future__ import annotations

import ast
import importlib.util
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Set


@dataclass
class DependencyReport:
    imported_modules: List[str]
    stdlib_modules: List[str]
    third_party_modules: List[str]
    missing_modules: List[str]
    install_command: str = ""
    notes: List[str] = None

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        if data["notes"] is None:
            data["notes"] = []
        return data


def _normalize_module_name(module_name: str) -> str:
    return module_name.split(".")[0].strip()


def extract_imports(code: str) -> Set[str]:
    """
    Extract top-level imported module names from Python code.
    """
    if not code or not code.strip():
        return set()

    imported: Set[str] = set()

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(_normalize_module_name(alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(_normalize_module_name(node.module))

    return imported


def is_stdlib_module(module_name: str) -> bool:
    """
    Best-effort check for standard library modules.
    """
    module_name = _normalize_module_name(module_name)

    if module_name in sys.builtin_module_names:
        return True

    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        return False

    # Standard library modules are usually inside the Python install path,
    # not site-packages. This is a best-effort heuristic.
    origin = spec.origin.lower()
    return "site-packages" not in origin and "dist-packages" not in origin


def is_module_available(module_name: str) -> bool:
    module_name = _normalize_module_name(module_name)
    return importlib.util.find_spec(module_name) is not None


def build_install_command(missing_modules: List[str]) -> str:
    if not missing_modules:
        return ""
    return f"{sys.executable} -m pip install " + " ".join(sorted(set(missing_modules)))


def analyze_dependencies(code: str) -> DependencyReport:
    """
    Analyze code imports and detect missing external dependencies.
    """
    imported_modules = sorted(extract_imports(code))

    stdlib_modules: List[str] = []
    third_party_modules: List[str] = []
    missing_modules: List[str] = []

    for module in imported_modules:
        if is_stdlib_module(module):
            stdlib_modules.append(module)
        else:
            third_party_modules.append(module)
            if not is_module_available(module):
                missing_modules.append(module)

    notes: List[str] = []
    if missing_modules:
        notes.append("Some external dependencies are missing in the current environment.")
    if third_party_modules and not missing_modules:
        notes.append("All detected third-party imports appear to be available.")

    return DependencyReport(
        imported_modules=imported_modules,
        stdlib_modules=sorted(stdlib_modules),
        third_party_modules=sorted(third_party_modules),
        missing_modules=sorted(set(missing_modules)),
        install_command=build_install_command(missing_modules),
        notes=notes,
    )


def dependency_summary(code: str) -> Dict[str, object]:
    """
    Dict-friendly wrapper for UI/pipeline usage.
    """
    return analyze_dependencies(code).to_dict()