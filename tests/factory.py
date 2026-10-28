"""Builds minimal synthetic .als files for tests (no real session data in the repo)."""

from __future__ import annotations

import gzip
from pathlib import Path


def clip(kind: str, name: str, start: float, end: float, *, disabled=False, pitch=0, warped=True, path=None) -> str:
    if kind == "audio":
        body = (
            f'<IsWarped Value="{str(warped).lower()}"/><PitchCoarse Value="{pitch}"/>'
            f'<SampleRef><FileRef><Path Value="{path or ""}"/></FileRef></SampleRef>'
        )
        tag = "AudioClip"
    else:
        body, tag = "", "MidiClip"
    return (
        f'<{tag} Id="0" Time="{start}"><Disabled Value="{str(disabled).lower()}"/>'
        f'<CurrentEnd Value="{end}"/><Name Value="{name}"/>{body}</{tag}>'
    )


def plugin(kind: str, name: str) -> str:
    info = {
        "VST2": f'<VstPluginInfo><PlugName Value="{name}"/></VstPluginInfo>',
        "VST3": f'<Vst3PluginInfo><Name Value="{name}"/></Vst3PluginInfo>',
    }[kind]
    return f"<PluginDevice><PluginDesc>{info}</PluginDesc></PluginDevice>"


def track(
    tag: str,
    id: int,
    name: str,
    *,
    user_name: str | None = None,
    color=0,
    group_id=-1,
    target="AudioOut/Main",
    active=True,
    devices="",
    clips="",
) -> str:
    user_name = name if user_name is None else user_name
    seq = {
        "AudioTrack": f"<Sample><ArrangerAutomation><Events>{clips}</Events></ArrangerAutomation></Sample>",
        "MidiTrack": f"<ClipTimeable><ArrangerAutomation><Events>{clips}</Events></ArrangerAutomation></ClipTimeable>",
    }.get(tag, "")
    return (
        f'<{tag} Id="{id}"><Name><EffectiveName Value="{name}"/><UserName Value="{user_name}"/></Name>'
        f'<Color Value="{color}"/><TrackGroupId Value="{group_id}"/>'
        f"<DeviceChain><Mixer><Speaker><Manual Value=\"{str(active).lower()}\"/></Speaker></Mixer>"
        f'<AudioOutputRouting><Target Value="{target}"/></AudioOutputRouting>'
        f"<MainSequencer>{seq}</MainSequencer>"
        f"<DeviceChain><Devices>{devices}</Devices></DeviceChain></DeviceChain></{tag}>"
    )


def als_xml(tracks="", *, locators=(), tempo=133, master_tag="MainTrack", creator="Ableton Live 12.4.3") -> str:
    locs = "".join(f'<Locator><Name Value="{n}"/><Time Value="{t}"/></Locator>' for n, t in locators)
    return (
        f'<?xml version="1.0" encoding="UTF-8"?><Ableton Creator="{creator}" MinorVersion="12.0_12300"><LiveSet>'
        f"<Tracks>{tracks}</Tracks>"
        f'<{master_tag} Id="0"><Name><EffectiveName Value="Main"/><UserName Value=""/></Name>'
        f'<DeviceChain><Mixer><Tempo><Manual Value="{tempo}"/></Tempo></Mixer></DeviceChain></{master_tag}>'
        f"<Locators><Locators>{locs}</Locators></Locators></LiveSet></Ableton>"
    )


def sample_tracks() -> str:
    """ARRANGE guide, a kick with a disabled clip and a plugin, a group with a child, a return."""
    return "".join(
        [
            track(
                "MidiTrack", 1, "ARRANGE", active=False,
                clips=clip("midi", "INTRO", 0, 32) + clip("midi", "DROP", 32, 96),
            ),
            track(
                "AudioTrack", 2, "Kick", color=5, group_id=10,
                devices=plugin("VST3", "Serum") + "<Eq8/>",
                clips=clip("audio", "kick_Amin", 0, 16, path="C:/Samples/kick_Amin.wav", pitch=2)
                + clip("audio", "kick2", 16, 32, disabled=True, warped=False),
            ),
            track("GroupTrack", 10, "Drums", user_name="Drums"),
            track(
                "AudioTrack", 3, "Hat", user_name="", group_id=10, target="AudioOut/Track.10/TrackIn",
                devices=plugin("VST2", "Sylenth1"),
            ),
            track("ReturnTrack", 20, "A-Reverb"),
        ]
    )


def write_als(path: Path, xml: str, *, compress: bool = True) -> Path:
    path.write_bytes(gzip.compress(xml.encode()) if compress else xml.encode())
    return path
