"""Plugins: third-party plugins per track, i.e. what someone else needs to open the session."""

from __future__ import annotations

from ..model import Finding, Session

NAME = "plugins"
ORDER = 80


def analyze(session: Session) -> list[Finding]:
    tracks = session.tracks + ((session.master,) if session.master else ())
    per_track = [(t, [d for d in t.devices if d.is_plugin]) for t in tracks]
    per_track = [(t, plugins) for t, plugins in per_track if plugins]
    if not per_track:
        return [Finding(NAME, "info", "No third-party plugins")]

    unique = sorted({f"{d.name} ({d.plugin_format})" for _, plugins in per_track for d in plugins})
    findings = [Finding(NAME, "info", f"{len(unique)} third-party plugin(s) needed: {', '.join(unique)}")]
    for t, plugins in per_track:
        listed = ", ".join(f"{d.name} ({d.plugin_format})" for d in plugins)
        findings.append(Finding(NAME, "info", listed, t.name, t.id))
    return findings
