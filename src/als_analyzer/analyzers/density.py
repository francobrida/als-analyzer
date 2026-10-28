"""Density: how many tracks have active clips sounding in each section."""

from __future__ import annotations

from ..model import Clip, Finding, Section, Session

NAME = "density"
ORDER = 20

BEATS_PER_BAR = 4  # same 4/4 assumption as the sections analyzer


def _sounds_in(clip: Clip, section: Section) -> bool:
    return not clip.disabled and clip.start < section.end and clip.end > section.start


def analyze(session: Session) -> list[Finding]:
    if not session.sections:
        return []  # the sections analyzer already reports this
    # Switched-off tracks (e.g. the guide track) make no sound.
    tracks = [t for t in session.tracks if t.kind in ("audio", "midi") and t.active]
    rows = [
        [t.name] + [sum(_sounds_in(c, s) for c in t.clips) for s in session.sections]
        for t in tracks
    ]
    findings = []
    playing = []
    for i, s in enumerate(session.sections, start=1):
        playing.append(sum(1 for r in rows if r[i]))
        findings.append(Finding(NAME, "info", f"{s.name or '(unnamed)'}: {playing[-1]} of {len(rows)} tracks playing"))
    by_id = {t.id: t for t in session.tracks}
    # Optional extras used by richer renderers (the terminal table ignores them).
    table = {
        "columns": ["Track"] + [s.name for s in session.sections],
        "rows": rows,
        "column_notes": [f"bar {s.start / BEATS_PER_BAR + 1:g}" for s in session.sections],
        "row_groups": [by_id[t.group_id].name if t.group_id in by_id else "" for t in tracks],
        "footer": ["Tracks playing"] + playing,
    }
    findings.append(Finding(NAME, "info", "Active clips per track and section", data={"table": table}))
    return findings
