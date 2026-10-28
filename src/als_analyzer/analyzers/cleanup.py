"""Cleanup: disabled clips, empty tracks that still load devices, tracks never renamed."""

from __future__ import annotations

from collections import Counter

from ..model import Finding, Session

NAME = "cleanup"
ORDER = 60


def analyze(session: Session) -> list[Finding]:
    findings: list[Finding] = []
    # A track that receives other tracks is a bus: no clips of its own is expected.
    buses = {t.destination_id for t in session.tracks}
    for t in session.tracks:
        disabled = Counter(c.name or "(unnamed)" for c in t.clips if c.disabled)
        if disabled:
            names = ", ".join(n if k == 1 else f"{n} x{k}" for n, k in disabled.items())
            findings.append(
                Finding(NAME, "info", f"{sum(disabled.values())} disabled clip(s): {names}", t.name, t.id)
            )
        if t.kind in ("audio", "midi") and not t.clips and t.devices and t.id not in buses:
            findings.append(
                Finding(NAME, "warning", f"Empty track with {len(t.devices)} device(s) loaded", t.name, t.id)
            )

    # Returns and the main track have meaningful default names, so they are not listed.
    unnamed = [t.name for t in session.tracks if t.kind != "return" and not t.user_name]
    if unnamed:
        findings.append(Finding(NAME, "info", f"{len(unnamed)} track(s) never renamed: {', '.join(unnamed)}"))
    if not findings:
        findings.append(Finding(NAME, "info", "Nothing to clean up"))
    return findings
