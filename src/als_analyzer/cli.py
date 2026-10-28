"""Command line entry point: ``als-analyzer session.als [--json]``."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import webbrowser
from pathlib import Path

from . import report, report_html
from .analyzers import run_all
from .parser import DEFAULT_SECTIONS_TRACK, AlsParseError, parse_als


def _temp_report_path(als_path: Path) -> Path:
    stem = re.sub(r"\W+", "_", als_path.stem)
    return Path(tempfile.gettempdir()) / f"als-analyzer-{stem}.html"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="als-analyzer", description="Read-only analysis of an Ableton Live .als session.")
    ap.add_argument("path", help="path to the .als file (gzip or plain XML)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the terminal report")
    ap.add_argument(
        "--sections-track",
        default=DEFAULT_SECTIONS_TRACK,
        metavar="NAME",
        help=f"MIDI track whose clips define the sections when there are no locators (default: {DEFAULT_SECTIONS_TRACK})",
    )
    ap.add_argument("--html", metavar="FILE", help="write a self-contained HTML report to FILE")
    ap.add_argument(
        "--open", action="store_true", help="open the HTML report in the browser (a temp file if --html is not given)"
    )
    args = ap.parse_args(argv)
    if args.json and (args.html or args.open):
        ap.error("--json cannot be combined with --html/--open")

    try:
        session = parse_als(args.path, sections_track=args.sections_track)
    except (OSError, AlsParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    findings = run_all(session)
    if args.html or args.open:
        out = Path(args.html) if args.html else _temp_report_path(session.path)
        try:
            out.write_text(report_html.to_html(session, findings), encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot write report: {exc}", file=sys.stderr)
            return 1
        print(f"Report written to {out}")
        if args.open:
            webbrowser.open(out.resolve().as_uri())
    elif args.json:
        sys.stdout.reconfigure(encoding="utf-8")  # JSON keeps non-ASCII track names
        print(report.to_json(session, findings))
    else:
        report.render_text(session, findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
