"""Sections: the arrangement structure, from locators or a guide track."""

from __future__ import annotations

from ..model import Finding, Session

NAME = "sections"
ORDER = 10

BEATS_PER_BAR = 4  # ponytail: time signature is not parsed, 4/4 assumed; read it from the master track if needed


def analyze(session: Session) -> list[Finding]:
    if not session.sections:
        return [
            Finding(
                NAME,
                "warning",
                "No sections found: no locators and no MIDI track matching --sections-track",
            )
        ]
    findings = [Finding(NAME, "info", f"Sections from {session.sections_source} (bars assume 4/4)")]
    for s in session.sections:
        bars = (s.end - s.start) / BEATS_PER_BAR
        first = s.start / BEATS_PER_BAR + 1
        if bars <= 0:
            findings.append(Finding(NAME, "warning", f"{s.name or '(unnamed)'}: empty section at bar {first:g}"))
        else:
            findings.append(
                Finding(NAME, "info", f"{s.name or '(unnamed)'}: bar {first:g}, {bars:g} bars")
            )
    return findings
