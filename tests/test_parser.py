import pytest

import factory
from als_analyzer.parser import AlsParseError, parse_als


def by_name(session, name):
    return next(t for t in session.tracks if t.name == name)


def test_gzip_and_plain_xml_give_same_result(tmp_path):
    xml = factory.als_xml(factory.sample_tracks())
    gz = parse_als(factory.write_als(tmp_path / "a.als", xml))
    plain = parse_als(factory.write_als(tmp_path / "b.als", xml, compress=False))
    assert gz.tracks == plain.tracks and gz.tempo == plain.tempo


def test_session_metadata(als_path):
    s = parse_als(als_path)
    assert s.creator == "Ableton Live 12.4.3"
    assert s.tempo == 133
    assert s.master is not None and s.master.kind == "master"
    assert s.warnings == ()


def test_track_kinds_and_order(als_path):
    s = parse_als(als_path)
    assert [(t.id, t.kind) for t in s.tracks] == [
        (1, "midi"), (2, "audio"), (10, "group"), (3, "audio"), (20, "return"),
    ]


def test_track_fields(als_path):
    s = parse_als(als_path)
    kick, hat, arrange = by_name(s, "Kick"), by_name(s, "Hat"), by_name(s, "ARRANGE")
    assert (kick.color, kick.group_id, kick.output_target) == (5, 10, "AudioOut/Main")
    assert hat.user_name == "" and hat.output_target == "AudioOut/Track.10/TrackIn"
    assert arrange.active is False and kick.active is True


def test_audio_clips(als_path):
    kick = by_name(parse_als(als_path), "Kick")
    first, second = kick.clips
    assert (first.start, first.end, first.pitch_coarse, first.disabled) == (0, 16, 2, False)
    assert first.sample_path == "C:/Samples/kick_Amin.wav" and first.is_warped
    assert second.disabled and not second.is_warped


def test_devices_native_vs_plugins(als_path):
    s = parse_als(als_path)
    kick_devices = by_name(s, "Kick").devices
    assert [(d.name, d.plugin_format) for d in kick_devices] == [("Serum", "VST3"), ("Eq8", None)]
    assert [(d.name, d.plugin_format) for d in by_name(s, "Hat").devices] == [("Sylenth1", "VST2")]


def test_sections_from_guide_track(als_path):
    s = parse_als(als_path)
    assert [(x.name, x.start, x.end) for x in s.sections] == [("INTRO", 0, 32), ("DROP", 32, 96)]


def test_guide_track_name_is_configurable(als_path):
    assert parse_als(als_path, sections_track="Other").sections == ()


def test_locators_take_priority_over_guide_track(tmp_path):
    xml = factory.als_xml(factory.sample_tracks(), locators=[("Break", 64), ("Intro", 0)])
    s = parse_als(factory.write_als(tmp_path / "l.als", xml))
    # Sorted by time; the last locator ends at the end of the last clip (96, the DROP guide clip).
    assert [(x.name, x.start, x.end) for x in s.sections] == [("Intro", 0, 64), ("Break", 64, 96)]


def test_legacy_master_track_name(tmp_path):
    xml = factory.als_xml(factory.sample_tracks(), master_tag="MasterTrack", tempo=120)
    s = parse_als(factory.write_als(tmp_path / "old.als", xml))
    assert s.tempo == 120


def test_missing_tags_warn_instead_of_crashing(tmp_path):
    xml = (
        '<Ableton Creator="Ableton Live 9"><LiveSet><Tracks>'
        '<AudioTrack Id="7"><Name><UserName Value="Lonely"/></Name></AudioTrack>'
        "</Tracks></LiveSet></Ableton>"
    )
    s = parse_als(factory.write_als(tmp_path / "bare.als", xml))
    assert s.tracks[0].name == "Lonely" and s.tempo is None and s.master is None
    assert any("master track" in w for w in s.warnings)
    assert any("Lonely" in w for w in s.warnings)


def test_entity_expansion_is_rejected(tmp_path):
    xml = '<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "boom">]><Ableton><LiveSet>&x;</LiveSet></Ableton>'
    with pytest.raises(AlsParseError):
        parse_als(factory.write_als(tmp_path / "evil.als", xml))


def test_not_an_als_raises(tmp_path):
    with pytest.raises(AlsParseError):
        parse_als(factory.write_als(tmp_path / "x.als", "<html/>"))


def test_parsing_never_modifies_the_file(als_path):
    before = als_path.read_bytes()
    parse_als(als_path)
    assert als_path.read_bytes() == before
