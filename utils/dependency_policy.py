from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List


class DependencyMode(str, Enum):
    STRICT = "strict"
    FALLBACK = "fallback"
    INSTALL = "install"


@dataclass
class DependencyDecision:
    mode: DependencyMode
    missing_modules: List[str]
    should_stop: bool
    should_rewrite: bool
    should_install: bool
    reason: str

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["mode"] = self.mode.value
        return data


def decide_dependency_action(
    missing_modules: List[str],
    mode: DependencyMode = DependencyMode.STRICT,
) -> DependencyDecision:
    """
    Decide what the pipeline should do when dependencies are missing.

    STRICT   -> stop and report
    FALLBACK -> allow an explicit rewrite step later
    INSTALL  -> allow controlled installation later
    """
    missing_modules = sorted(set(missing_modules or []))

    if not missing_modules:
        return DependencyDecision(
            mode=mode,
            missing_modules=[],
            should_stop=False,
            should_rewrite=False,
            should_install=False,
            reason="No missing dependencies detected.",
        )

    if mode == DependencyMode.STRICT:
        return DependencyDecision(
            mode=mode,
            missing_modules=missing_modules,
            should_stop=True,
            should_rewrite=False,
            should_install=False,
            reason="Missing dependencies detected. Strict mode requires stopping and reporting.",
        )

    if mode == DependencyMode.FALLBACK:
        return DependencyDecision(
            mode=mode,
            missing_modules=missing_modules,
            should_stop=False,
            should_rewrite=True,
            should_install=False,
            reason="Missing dependencies detected. Fallback mode allows an explicit rewrite step.",
        )

    return DependencyDecision(
        mode=mode,
        missing_modules=missing_modules,
        should_stop=False,
        should_rewrite=False,
        should_install=True,
        reason="Missing dependencies detected. Install mode allows controlled installation.",
    )