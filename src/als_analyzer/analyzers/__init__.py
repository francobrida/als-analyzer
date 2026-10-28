"""Analyzer discovery.

Every module in this package that defines ``NAME`` and ``analyze(session)`` is
picked up automatically, so adding an analyzer means adding a file and nothing else.
An optional ``ORDER`` int controls report order (default 50, lower goes first).
"""

from __future__ import annotations

import importlib
import pkgutil

from ..model import Finding, Session

DEFAULT_ORDER = 50


def discover():
    modules = [
        importlib.import_module(f"{__name__}.{info.name}")
        for info in pkgutil.iter_modules(__path__)
    ]
    modules = [m for m in modules if hasattr(m, "NAME") and hasattr(m, "analyze")]
    return sorted(modules, key=lambda m: (getattr(m, "ORDER", DEFAULT_ORDER), m.NAME))


def run_all(session: Session) -> list[Finding]:
    """Run every analyzer; one failing analyzer is reported, not fatal."""
    findings: list[Finding] = []
    for module in discover():
        try:
            findings.extend(module.analyze(session))
        except Exception as exc:  # noqa: BLE001 - isolate analyzers from each other
            findings.append(Finding(module.NAME, "warning", f"analyzer failed: {exc!r}"))
    return findings
