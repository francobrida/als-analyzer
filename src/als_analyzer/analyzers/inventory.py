"""Inventory: Live version, tempo and what the session is made of."""

from __future__ import annotations

from ..model import Finding, Session

NAME = "inventory"
ORDER = 0


def analyze(session: Session) -> list[Finding]:
    def info(message: str) -> Finding:
        return Finding(NAME, "info", message)

    kinds = [t.kind for t in session.tracks]
    findings = [info(f"Created with {session.creator or 'unknown Live version'}")]
    if session.tempo is None:
        findings.append(Finding(NAME, "warning", "Tempo not found"))
    else:
        findings.append(info(f"Tempo: {session.tempo:g} BPM"))
    findings += [
        info(f"Tracks: {kinds.count('audio')} audio, {kinds.count('midi')} MIDI, {kinds.count('group')} groups"),
        info(f"Return tracks: {kinds.count('return')}"),
        info(f"Sections: {len(session.sections)}"
             + (f" ({', '.join(s.name for s in session.sections)})" if session.sections else "")),
    ]
    return findings
