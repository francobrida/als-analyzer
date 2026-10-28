"""Typed data model of a parsed session.

Pure data: nothing here knows about XML. Positions and lengths are in beats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

TrackKind = Literal["audio", "midi", "group", "return", "master"]
Severity = Literal["info", "warning"]


@dataclass(frozen=True)
class Device:
    name: str
    # "VST2" / "VST3" / "AU" for third-party plugins, None for Live's own devices.
    plugin_format: str | None = None

    @property
    def is_plugin(self) -> bool:
        return self.plugin_format is not None


@dataclass(frozen=True)
class Clip:
    kind: Literal["audio", "midi"]
    name: str
    start: float
    end: float
    disabled: bool = False
    pitch_coarse: int = 0
    is_warped: bool = False
    # Absolute path of the sample; only set for audio clips (from SampleRef).
    sample_path: str | None = None


@dataclass(frozen=True)
class Track:
    id: int
    kind: TrackKind
    name: str  # visible name (EffectiveName)
    user_name: str  # empty if the track was never renamed
    color: int  # palette index, not RGB
    group_id: int  # -1 = not in a group
    output_target: str  # e.g. "AudioOut/Main" or "AudioOut/Track.157/TrackIn"
    active: bool
    devices: tuple[Device, ...] = ()
    clips: tuple[Clip, ...] = ()

    @property
    def destination_id(self) -> int | None:
        """Id of the track this one feeds, or None if it goes to Main / elsewhere."""
        m = re.match(r"^AudioOut/Track\.(\d+)(/|$)", self.output_target)
        if m:
            return int(m.group(1))
        # Tracks inside a group send to the group (seen in real Live 12 sessions).
        if self.output_target == "AudioOut/GroupTrack" and self.group_id != -1:
            return self.group_id
        return None


@dataclass(frozen=True)
class Section:
    name: str
    start: float
    end: float


@dataclass(frozen=True)
class Session:
    path: Path
    creator: str
    minor_version: str
    tempo: float | None
    tracks: tuple[Track, ...]  # audio, midi, group and return tracks, in file order
    master: Track | None
    sections: tuple[Section, ...] = ()
    # Where the sections came from: "locators", "track 'NAME'" or "" if none were found.
    sections_source: str = ""
    # Problems found while parsing (missing tags, other Live versions...).
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    analyzer: str
    severity: Severity
    message: str
    track: str | None = None  # visible track name
    track_id: int | None = None
    # Optional structured payload (e.g. a table) for the report to render.
    data: dict[str, Any] | None = field(default=None, compare=False)
