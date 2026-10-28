"""Parse an .als file into the typed model.

This is the only module that knows the XML layout. It never writes anything,
and it tolerates missing tags (other Live versions): problems are collected in
``Session.warnings`` instead of raising.
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Callable
from xml.etree.ElementTree import Element, ParseError

from defusedxml import ElementTree as safe_et
from defusedxml.common import DefusedXmlException

from .model import Clip, Device, Section, Session, Track, TrackKind

GZIP_MAGIC = b"\x1f\x8b"
DEFAULT_SECTIONS_TRACK = "ARRANGE"

_TRACK_TAGS: dict[str, TrackKind] = {
    "AudioTrack": "audio",
    "MidiTrack": "midi",
    "GroupTrack": "group",
    "ReturnTrack": "return",
}
# (plugin format, path of the plugin name under PluginDevice)
_PLUGIN_NAMES = (
    ("VST2", "PluginDesc/VstPluginInfo/PlugName"),
    ("VST3", "PluginDesc/Vst3PluginInfo/Name"),
    ("AU", "PluginDesc/AuPluginInfo/Name"),
)
_CLIP_EVENTS = {
    "audio": "DeviceChain/MainSequencer/Sample/ArrangerAutomation/Events",
    "midi": "DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events",
}
_CLIP_TAGS = {"audio": "AudioClip", "midi": "MidiClip"}

Warn = Callable[[str], None]


class AlsParseError(Exception):
    """The file is not a readable Live set."""


def parse_als(path: str | Path, sections_track: str = DEFAULT_SECTIONS_TRACK) -> Session:
    """Parse a gzip-compressed .als or an already-decompressed XML file."""
    path = Path(path)
    data = path.read_bytes()
    if data.startswith(GZIP_MAGIC):
        try:
            data = gzip.decompress(data)
        except (OSError, EOFError) as exc:
            raise AlsParseError(f"{path.name}: corrupt gzip data ({exc})") from exc
    try:
        root = safe_et.fromstring(data)
    except (ParseError, DefusedXmlException) as exc:
        raise AlsParseError(f"{path.name}: not valid Live XML ({exc})") from exc
    if root.tag != "Ableton" or root.find("LiveSet") is None:
        raise AlsParseError(f"{path.name}: no <Ableton>/<LiveSet> root found")

    warnings: list[str] = []
    warn = warnings.append
    live_set = root.find("LiveSet")

    tracks_node = live_set.find("Tracks")
    if tracks_node is None:
        warn("LiveSet/Tracks is missing")
        tracks_node = Element("Tracks")
    tracks = tuple(
        _parse_track(node, _TRACK_TAGS[node.tag], warn)
        for node in tracks_node
        if node.tag in _TRACK_TAGS
    )

    # Live 12 calls it MainTrack, earlier versions MasterTrack.
    master_node = live_set.find("MainTrack")
    if master_node is None:
        master_node = live_set.find("MasterTrack")
    if master_node is None:
        warn("master track (MainTrack/MasterTrack) is missing")
    # The master has no color/group/clips, so its missing tags are not worth a warning.
    master = _parse_track(master_node, "master", lambda _: None) if master_node is not None else None

    tempo = None
    if master_node is not None:
        tempo = _float(_val(master_node, "DeviceChain/Mixer/Tempo/Manual", warn=warn, ctx="master"))

    sections, sections_source = _build_sections(live_set, tracks, sections_track)
    return Session(
        path=path,
        creator=root.get("Creator", ""),
        minor_version=root.get("MinorVersion", ""),
        tempo=tempo,
        tracks=tracks,
        master=master,
        sections=sections,
        sections_source=sections_source,
        warnings=tuple(warnings),
    )


def _val(node: Element, path: str, default: str | None = None, *, warn: Warn | None = None, ctx: str = "") -> str | None:
    """Value attribute of the tag at ``path``; falls back to a plain attribute of ``node``."""
    el = node.find(path)
    if el is not None and "Value" in el.attrib:
        return el.get("Value")
    if "/" not in path and path in node.attrib:
        return node.get(path)
    if warn:
        warn(f"{ctx}: missing <{path}>")
    return default


def _float(raw: str | None, default: float | None = None) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _int(raw: str | None, default: int = 0) -> int:
    value = _float(raw)
    return default if value is None else int(value)


def _bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() == "true"


def _parse_track(node: Element, kind: TrackKind, warn: Warn) -> Track:
    track_id = _int(node.get("Id"), -1)
    ctx = f"{kind} track Id={track_id}"
    user_name = _val(node, "Name/UserName", "") or ""
    name = _val(node, "Name/EffectiveName", warn=warn, ctx=ctx) or user_name or f"{kind} {track_id}"
    ctx = f"track '{name}'"
    return Track(
        id=track_id,
        kind=kind,
        name=name,
        user_name=user_name,
        color=_int(_val(node, "Color", warn=warn, ctx=ctx), -1),
        group_id=_int(_val(node, "TrackGroupId"), -1),
        output_target=_val(node, "DeviceChain/AudioOutputRouting/Target", "", warn=warn, ctx=ctx) or "",
        active=_bool(_val(node, "DeviceChain/Mixer/Speaker/Manual", warn=warn, ctx=ctx), True),
        devices=_parse_devices(node),
        clips=_parse_clips(node, kind, warn, ctx) if kind in _CLIP_EVENTS else (),
    )


def _parse_devices(node: Element) -> tuple[Device, ...]:
    devices_node = node.find("DeviceChain/DeviceChain/Devices")
    if devices_node is None:
        return ()
    devices = []
    for dev in devices_node:
        if dev.tag == "PluginDevice":
            devices.append(_parse_plugin(dev))
        else:
            devices.append(Device(name=dev.tag))
    return tuple(devices)


def _parse_plugin(dev: Element) -> Device:
    for fmt, path in _PLUGIN_NAMES:
        name = _val(dev, path)
        if name:
            return Device(name=name, plugin_format=fmt)
    return Device(name="(unknown plugin)", plugin_format="unknown")


def _parse_clips(node: Element, kind: str, warn: Warn, ctx: str) -> tuple[Clip, ...]:
    events = node.find(_CLIP_EVENTS[kind])
    if events is None:
        warn(f"{ctx}: arrangement events not found")
        return ()
    clips = []
    for c in events.findall(_CLIP_TAGS[kind]):
        clips.append(
            Clip(
                kind=kind,  # type: ignore[arg-type]
                name=_val(c, "Name", "") or "",
                start=_float(_val(c, "Time", warn=warn, ctx=ctx), 0.0),
                end=_float(_val(c, "CurrentEnd", warn=warn, ctx=ctx), 0.0),
                disabled=_bool(_val(c, "Disabled"), False),
                pitch_coarse=_int(_val(c, "PitchCoarse")),
                is_warped=_bool(_val(c, "IsWarped"), False),
                # Only SampleRef of clips: FileRef also appears in device presets.
                sample_path=_val(c, "SampleRef/FileRef/Path") if kind == "audio" else None,
            )
        )
    return tuple(clips)


def _build_sections(
    live_set: Element, tracks: tuple[Track, ...], guide_name: str
) -> tuple[tuple[Section, ...], str]:
    """Sections from locators; if there are none, from the guide track's MIDI clips.

    Returns the sections and a description of where they came from.
    """
    locators = sorted(
        (
            (_float(_val(loc, "Time"), 0.0), _val(loc, "Name", "") or "")
            for loc in live_set.findall("Locators/Locators/Locator")
        ),
        key=lambda t: t[0],
    )
    if locators:
        song_end = max((c.end for t in tracks for c in t.clips), default=0.0)
        ends = [start for start, _ in locators[1:]] + [max(song_end, locators[-1][0])]
        sections = tuple(Section(name, start, end) for (start, name), end in zip(locators, ends))
        return sections, "locators"

    guide = next((t for t in tracks if t.name.casefold() == guide_name.casefold() and t.kind == "midi"), None)
    if guide is None:
        return (), ""
    clips = sorted((c for c in guide.clips if not c.disabled), key=lambda c: c.start)
    return tuple(Section(c.name, c.start, c.end) for c in clips), f"track '{guide.name}'"
