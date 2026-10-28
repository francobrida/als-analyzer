"""Routing: which tracks are buses, and which tracks skip the bus the rest use."""

from __future__ import annotations

from ..model import Finding, Session, Track

NAME = "routing"

_MAIN = "AudioOut/Main"


def analyze(session: Session) -> list[Finding]:
    by_id = {t.id: t for t in session.tracks}
    findings: list[Finding] = []
    feeds: dict[int, list[Track]] = {}
    for t in session.tracks:
        dest = t.destination_id
        if dest is None:
            continue
        if dest in by_id:
            feeds.setdefault(dest, []).append(t)
        else:
            findings.append(
                Finding(NAME, "warning", f"Routes to unknown track Id={dest}", t.name, t.id)
            )

    for bus_id, sources in feeds.items():
        bus = by_id[bus_id]
        names = ", ".join(s.name for s in sources)
        findings.append(Finding(NAME, "info", f"Bus receiving {len(sources)} track(s): {names}", bus.name, bus.id))
    if not feeds:
        findings.append(Finding(NAME, "info", "No buses detected"))
        return findings

    # Sources that actually make sound: active, with clips, and not buses themselves.
    sources = [t for t in session.tracks if t.kind in ("audio", "midi") and t.active and t.clips and t.id not in feeds]
    via_bus = [t for t in sources if t.destination_id in feeds]
    direct = [t for t in sources if t.output_target == _MAIN]
    if len(via_bus) > len(direct):
        for t in direct:
            findings.append(
                Finding(
                    NAME,
                    "warning",
                    f"Goes straight to Main while {len(via_bus)} of {len(sources)} tracks go through a bus",
                    t.name,
                    t.id,
                )
            )
    return findings
