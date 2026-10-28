import pytest

import factory
from als_analyzer.analyzers import key
from als_analyzer.analyzers.key import Key, compatible, parse_key
from als_analyzer.parser import parse_als


@pytest.mark.parametrize(
    "name, expected",
    [
        ("G#min", Key(8, "minor")),
        ("Amin", Key(9, "minor")),
        ("kick_A", Key(9, None)),
        ("BPhrygian", Key(11, "phrygian")),
        ("loop_B_Phrygian_140", Key(11, "phrygian")),
        ("pad_F#m_120", Key(6, "minor")),
        ("Dm", Key(2, "minor")),
        ("Ebmaj", Key(3, "major")),
        ("Bb", Key(10, None)),
        ("Bbmin", Key(10, "minor")),
        ("amin", Key(9, "minor")),
        ("C major lead", Key(0, "major")),
        ("a_Amin", Key(9, "minor")),  # a lone lowercase letter is skipped, the real key is found
        # not keys
        ("D#2", None),
        ("C3", None),
        ("Bass", None),
        ("Dmitri", None),
        ("Abstract", None),
        ("Amen_break", None),
        ("a", None),
        ("kick", None),
        ("Am7", None),
    ],
)
def test_parse_key(name, expected):
    assert parse_key(name) == expected


def test_compatibility_is_by_diatonic_collection():
    assert compatible(Key(9, "minor"), Key(0, "major"))  # A minor ~ C major
    assert compatible(Key(2, "dorian"), Key(0, "major"))
    assert compatible(Key(9, None), Key(9, "minor"))
    assert not compatible(Key(9, "minor"), Key(1, "minor"))


def session_with(tmp_path, **tracks):
    xml = "".join(
        factory.track("AudioTrack", i, name, clips=clips)
        for i, (name, clips) in enumerate(tracks.items(), start=1)
    )
    return parse_als(factory.write_als(tmp_path / "k.als", factory.als_xml(xml)))


def c(sample, **kw):
    return factory.clip("audio", "clip", 0, 8, path=f"C:/Samples/{sample}.wav", **kw)


def test_transposition_applies_only_to_warped_clips(tmp_path):
    s = session_with(tmp_path, Pad=c("pad_Amin", pitch=2) + c("pad2_Amin", pitch=2, warped=False))
    keys = [key.clip_key(cl) for cl in s.tracks[0].clips]
    assert keys == [Key(11, "minor"), Key(9, "minor")]


def test_multiple_keys_in_one_track(tmp_path):
    findings = key.analyze(session_with(tmp_path, Pad=c("a_Amin") + c("b_Emin")))
    (warn,) = [f for f in findings if f.severity == "warning"]
    assert warn.track == "Pad" and "estimated" in warn.message and "A minor" in warn.message


def test_mismatching_track_is_flagged_but_relative_keys_are_not(tmp_path):
    s = session_with(tmp_path, Bass=c("bass_Amin"), Lead=c("lead_Cmaj"), Pad=c("pad_Amin"), Vox=c("vox_C#min"))
    findings = key.analyze(s)
    assert findings[0].message == "Session key (estimated): A minor, 3 of 4 keyed clips"
    assert [f.track for f in findings if f.severity == "warning"] == ["Vox"]


def test_bare_note_mismatch_is_only_info(tmp_path):
    s = session_with(tmp_path, Bass=c("bass_Amin"), Pad=c("pad_Amin"), Riser=c("riser 128 BPM F#"))
    (mismatch,) = [f for f in key.analyze(s) if f.track == "Riser"]
    assert mismatch.severity == "info"


def test_disabled_clips_and_unkeyed_samples_are_ignored(tmp_path):
    s = session_with(tmp_path, Kick=c("kick") + c("x_Gmin", disabled=True))
    assert [f.message for f in key.analyze(s)] == ["No key information found in sample names"]


def test_all_key_messages_say_estimated(tmp_path):
    findings = key.analyze(session_with(tmp_path, A=c("a_Amin"), B=c("b_C#min")))
    assert all("estimated" in f.message for f in findings)
