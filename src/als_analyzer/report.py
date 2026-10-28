"""Output: human-readable terminal report (rich) or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from itertools import groupby

from rich import box
from rich.console import Console
from rich.table import Table

from .model import Finding, Session

_STYLE = {"info": ("•", "cyan"), "warning": ("!", "yellow")}


def to_json(session: Session, findings: list[Finding]) -> str:
    payload = {
        "file": session.path.name,
        "creator": session.creator,
        "tempo": session.tempo,
        "parser_warnings": list(session.warnings),
        "findings": [asdict(f) for f in findings],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _table(spec: dict) -> Table:
    """Generic table: first column is the row label, empty/zero cells show as a dim dot."""
    table = Table(box=box.SIMPLE_HEAD, padding=(0, 1))
    for i, col in enumerate(spec["columns"]):
        if i == 0:  # long track names must not wrap into several lines
            table.add_column(col, justify="left", max_width=24, no_wrap=True, overflow="ellipsis")
        else:
            table.add_column(col, justify="center", overflow="fold")
    for row in spec["rows"]:
        table.add_row(*(str(c) if c or i == 0 else "[dim]·[/dim]" for i, c in enumerate(row)))
    return table


def render_text(session: Session, findings: list[Finding], console: Console | None = None) -> None:
    console = console or Console()
    console.print(f"[bold]{session.path.name}[/bold]")
    # Findings arrive grouped by analyzer (run order); keep that order.
    for analyzer, group in groupby(findings, key=lambda f: f.analyzer):
        console.print(f"\n[bold underline]{analyzer}[/bold underline]")
        for f in group:
            mark, color = _STYLE[f.severity]
            where = f"[dim]\\[{f.track}][/dim] " if f.track else ""
            console.print(f"  [{color}]{mark}[/{color}] {where}{f.message}", highlight=False)
            if f.data and "table" in f.data:
                console.print(_table(f.data["table"]))
    if session.warnings:
        console.print("\n[bold underline]parser warnings[/bold underline]")
        for w in session.warnings:
            console.print(f"  [yellow]![/yellow] {w}", highlight=False)
