"""Self-contained HTML report (one file, inline CSS, no JavaScript, no network).

Colors live in the CSS variables at the top of ``_CSS``: change them there.
"""

from __future__ import annotations

import re
from html import escape
from itertools import groupby

from .model import Finding, Session

_CSS = """
:root{color-scheme:dark light;--bg:#0f0f11;--card:#17171a;--raised:#1d1d21;--line:#2a2a30;--fg:#ececee;
--muted:#8d8d97;--accent:#5eead4;--warn:#f5b84b;--warn-bg:#3a2d12}
@media (prefers-color-scheme:light){:root{--bg:#f6f5f3;--card:#fff;--raised:#f1efec;--line:#e4e1dc;
--fg:#1b1b1f;--muted:#6b6b73;--accent:#0d9488;--warn:#b45309;--warn-bg:#fdf0d5}}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:64px}
body{margin:0;background:var(--bg);color:var(--fg);font:14.5px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;
font-variant-numeric:tabular-nums}
main{max-width:1120px;margin:0 auto;padding:28px 16px 56px}
h1{font-size:1.6rem;letter-spacing:-.01em;margin:0 0 2px;overflow-wrap:anywhere}
.meta{color:var(--muted);margin:0 0 20px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:20px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat .n{font-size:1.9rem;font-weight:650;line-height:1.1;letter-spacing:-.02em}
.stat .l{color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;margin-top:4px}
.stat .s{color:var(--muted);font-size:.82rem;margin-top:6px}
.stat.warn .n{color:var(--warn)}
nav{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0;margin-bottom:12px;
display:flex;flex-wrap:wrap;gap:6px;border-bottom:1px solid var(--line)}
nav a{color:var(--muted);text-decoration:none;border:1px solid var(--line);border-radius:999px;
padding:2px 12px;font-size:.82rem;background:var(--card)}
nav a:hover,nav a:focus-visible{color:var(--fg);border-color:var(--accent);outline:none}
nav a.has-warn::after{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;
background:var(--warn);margin-left:7px;vertical-align:middle}
details{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:12px}
summary{cursor:pointer;padding:12px 16px;font-weight:600;display:flex;gap:8px;align-items:center;
text-transform:capitalize;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸";color:var(--muted);transition:transform .15s}
details[open]>summary::before{transform:rotate(90deg)}
.badge{margin-left:auto;font-size:.75rem;font-weight:600;text-transform:none;color:var(--warn);
background:var(--warn-bg);border-radius:999px;padding:1px 10px}
ul{list-style:none;margin:0;padding:0 16px 12px}
li{display:flex;gap:8px;padding:3px 0;align-items:baseline}
.sev{flex:none;width:1.2em;text-align:center;color:var(--muted)}
.warning .sev{color:var(--warn);font-weight:700}
.track{flex:none;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.78rem;
background:var(--raised);border-radius:6px;padding:0 7px;color:var(--muted)}
.msg{overflow-wrap:anywhere}
.tablewrap{overflow:auto;max-height:70vh;margin:4px 16px 16px;border:1px solid var(--line);border-radius:10px}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:.82rem}
th,td{padding:4px 8px;text-align:center;border-bottom:1px solid var(--line)}
thead th{position:sticky;top:0;z-index:1;background:var(--raised);font-weight:600;min-width:72px;
vertical-align:bottom;line-height:1.25}
thead th small{display:block;color:var(--muted);font-weight:400;font-size:.72rem}
tbody th,tfoot th{position:sticky;left:0;background:var(--card);text-align:left;font-weight:400;
max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
thead th:first-child{left:0;z-index:2;text-align:left}
tr.grp th{background:var(--raised);color:var(--muted);font-size:.72rem;text-transform:uppercase;
letter-spacing:.08em;font-weight:600;position:static}
tr.idle th{color:var(--muted)}
td{background:color-mix(in srgb,var(--accent) calc(var(--v,0)*65%),transparent)}
td.zero{color:var(--muted);opacity:.5}
tfoot th,tfoot td{font-weight:650;background:var(--raised);border-bottom:0;position:sticky;bottom:0}
footer{color:var(--muted);font-size:.8rem;margin-top:28px}
@media (max-width:600px){main{padding:16px 12px 40px}.stat .n{font-size:1.6rem}}
"""


def _esc(value: object) -> str:
    # Track and clip names come from an untrusted file: always escape.
    return escape(str(value), quote=True)


def _slug(name: str) -> str:
    return "a-" + re.sub(r"\W+", "-", name).strip("-").lower()


def _table(spec: dict) -> str:
    cols, rows = spec["columns"], spec["rows"]
    notes = spec.get("column_notes") or [""] * (len(cols) - 1)
    row_groups = spec.get("row_groups") or [""] * len(rows)
    top = max((c for r in rows for c in r[1:] if isinstance(c, (int, float))), default=0) or 1

    head = f"<th scope='col'>{_esc(cols[0])}</th>" + "".join(
        f"<th scope='col'>{_esc(c)}" + (f"<small>{_esc(n)}</small>" if n else "") + "</th>"
        for c, n in zip(cols[1:], notes)
    )
    body, last_group = [], ""
    for row, group in zip(rows, row_groups):
        if group != last_group:
            if group:
                body.append(f"<tr class='grp'><th colspan='{len(cols)}'>{_esc(group)}</th></tr>")
            last_group = group
        cells = []
        for c in row[1:]:
            if isinstance(c, (int, float)) and c:
                cells.append(f"<td style='--v:{c / top:.3f}'>{_esc(c)}</td>")
            else:
                cells.append("<td class='zero'>·</td>")
        idle = "" if any(row[1:]) else " class='idle'"
        body.append(f"<tr{idle}><th scope='row' title='{_esc(row[0])}'>{_esc(row[0])}</th>{''.join(cells)}</tr>")

    foot = ""
    if spec.get("footer"):
        f = spec["footer"]
        foot = (
            f"<tfoot><tr><th scope='row'>{_esc(f[0])}</th>"
            + "".join(f"<td>{_esc(c)}</td>" for c in f[1:])
            + "</tr></tfoot>"
        )
    return (
        f"<div class='tablewrap'><table><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>{foot}</table></div>"
    )


def _finding(f: Finding) -> str:
    mark = "!" if f.severity == "warning" else "•"
    track = f"<span class='track' title='{_esc(f.track)}'>{_esc(f.track)}</span>" if f.track else ""
    return (
        f"<li class='{f.severity}'><span class='sev' role='img' aria-label='{f.severity}'>{mark}</span>"
        f"{track}<span class='msg'>{_esc(f.message)}</span></li>"
    )


def _group(name: str, findings: list[Finding]) -> str:
    warnings = sum(f.severity == "warning" for f in findings)
    badge = f"<span class='badge'>{warnings} warning(s)</span>" if warnings else ""
    items, tables = [], []
    for f in findings:
        items.append(_finding(f))
        if f.data and "table" in f.data:
            tables.append(_table(f.data["table"]))
    return (
        f"<details open id='{_slug(name)}'><summary>{_esc(name)}{badge}</summary>"
        f"<ul>{''.join(items)}</ul>{''.join(tables)}</details>"
    )


def _stat(number: object, label: str, sub: str = "", warn: bool = False) -> str:
    sub_html = f"<div class='s'>{_esc(sub)}</div>" if sub else ""
    return f"<div class='stat{' warn' if warn else ''}'><div class='n'>{_esc(number)}</div><div class='l'>{_esc(label)}</div>{sub_html}</div>"


def _summary(session: Session, total_warnings: int, analyzers_with_warnings: int) -> str:
    kinds = [t.kind for t in session.tracks]
    tracks_sub = f"{kinds.count('audio')} audio · {kinds.count('midi')} MIDI · {kinds.count('group')} groups · {kinds.count('return')} returns"
    sections = session.sections
    bars = (max(s.end for s in sections) - min(s.start for s in sections)) / 4 if sections else 0
    sections_sub = f"{bars:g} bars (assuming 4/4)" if sections else "none found"
    devices = [d for t in session.tracks + ((session.master,) if session.master else ()) for d in t.devices if d.is_plugin]
    unique_plugins = {(d.name, d.plugin_format) for d in devices}
    tempo = f"{session.tempo:g}" if session.tempo is not None else "?"
    warn_sub = f"in {analyzers_with_warnings} section(s)" if total_warnings else "nothing to flag"
    return (
        "<div class='stats'>"
        + _stat(tempo, "BPM", session.creator or "unknown Live version")
        + _stat(len(session.tracks), "Tracks", tracks_sub)
        + _stat(len(sections), "Sections", sections_sub)
        + _stat(len(unique_plugins), "Third-party plugins")
        + _stat(total_warnings, "Warnings", warn_sub, warn=bool(total_warnings))
        + "</div>"
    )


def to_html(session: Session, findings: list[Finding]) -> str:
    groups = [(name, list(g)) for name, g in groupby(findings, key=lambda f: f.analyzer)]
    if session.warnings:
        groups.append(("parser warnings", [Finding("parser warnings", "warning", w) for w in session.warnings]))
    warn_counts = {name: sum(f.severity == "warning" for f in g) for name, g in groups}
    total = sum(warn_counts.values())
    nav = "".join(
        "<a href='#{}'{}>{}</a>".format(_slug(n), " class='has-warn'" if warn_counts[n] else "", _esc(n))
        for n, _ in groups
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{_esc(session.path.name)} — als-analyzer</title><style>{_CSS}</style></head><body><main>"
        f"<h1>{_esc(session.path.name)}</h1><p class='meta'>Session analysis · read-only</p>"
        f"{_summary(session, total, sum(1 for c in warn_counts.values() if c))}"
        f"<nav aria-label='Analyzers'>{nav}</nav>"
        f"{''.join(_group(n, g) for n, g in groups)}"
        "<footer>Generated by als-analyzer. Key detection is an estimate from sample names.</footer>"
        "</main></body></html>"
    )
