"""Dependencies: samples that live outside the project folder."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from ..model import Finding, Session

NAME = "dependencies"
ORDER = 70

# "<anything> Project/" as a path prefix, e.g. ".../666 Project/".
_PROJECT_PREFIX = re.compile(r"^(.*?[^/]+ Project)/", re.IGNORECASE)


def _norm(path: str) -> str:
    # Sample paths may be Windows or POSIX style, so compare as lowercase forward-slash strings.
    # ponytail: case-insensitive on every OS; wrong only for paths differing by case on Linux.
    return path.replace("\\", "/").rstrip("/").casefold()


def _project_from_als_location(als_path: Path) -> str | None:
    """Nearest ancestor folder named '... Project' (Live's project folder)."""
    for folder in als_path.resolve().parents:
        if folder.name.casefold().endswith(" project"):
            return str(folder)
    return None


def _project_from_samples(paths: list[str]) -> str | None:
    """Most common '... Project' prefix among sample paths (for a .als copied out of its project)."""
    prefixes = Counter(m.group(1) for p in paths if (m := _PROJECT_PREFIX.match(p.replace("\\", "/"))))
    return prefixes.most_common(1)[0][0] if prefixes else None


def analyze(session: Session) -> list[Finding]:
    findings: list[Finding] = []
    sample_paths = [c.sample_path for t in session.tracks for c in t.clips if c.sample_path]

    project = _project_from_als_location(session.path)
    if project is None:
        project = _project_from_samples(sample_paths)
        if project:
            findings.append(
                Finding(NAME, "info", f"The .als is not inside a '... Project' folder; project inferred from sample paths: {project}")
            )
        else:
            project = str(session.path.resolve().parent)
            findings.append(
                Finding(NAME, "warning", f"No '... Project' folder found; using the .als folder ({project})")
            )
    root = _norm(project) + "/"

    for t in session.tracks:
        outside = sorted({c.sample_path for c in t.clips if c.sample_path and not _norm(c.sample_path).startswith(root)})
        if outside:
            findings.append(
                Finding(
                    NAME, "warning",
                    f"{len(outside)} sample(s) outside the project folder: {', '.join(outside)}",
                    t.name, t.id, data={"paths": outside},
                )
            )
    if not any(f.severity == "warning" and f.track for f in findings):
        findings.append(Finding(NAME, "info", f"All {len(set(sample_paths))} sample(s) are inside the project folder"))
    return findings
