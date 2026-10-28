import factory
from als_analyzer.analyzers import routing
from als_analyzer.parser import parse_als

CLIP = factory.clip("audio", "x", 0, 8)


def run(tmp_path, *tracks):
    s = parse_als(factory.write_als(tmp_path / "r.als", factory.als_xml("".join(tracks))))
    return routing.analyze(s)


def audio(id, name, target="AudioOut/Main", **kw):
    return factory.track("AudioTrack", id, name, target=target, clips=kw.pop("clips", CLIP), **kw)


def test_bus_detected_and_majority_warns_direct_tracks(tmp_path):
    findings = run(
        tmp_path,
        audio(1, "Kick", "AudioOut/Track.10/TrackIn"),
        audio(2, "Snare", "AudioOut/Track.10/TrackIn"),
        audio(3, "Vox"),  # straight to Main
        factory.track("AudioTrack", 10, "Drums Bus"),
    )
    assert findings[0].message == "Bus receiving 2 track(s): Kick, Snare" and findings[0].track == "Drums Bus"
    (warn,) = [f for f in findings if f.severity == "warning"]
    assert warn.track == "Vox" and "2 of 3" in warn.message


def test_no_warning_when_direct_tracks_are_the_majority(tmp_path):
    findings = run(
        tmp_path,
        audio(1, "Kick", "AudioOut/Track.10/TrackIn"),
        audio(2, "Vox"),
        audio(3, "Pad"),
        factory.track("AudioTrack", 10, "Bus"),
    )
    assert not [f for f in findings if f.severity == "warning"]


def test_group_children_count_as_bus_members(tmp_path):
    findings = run(
        tmp_path,
        audio(1, "Kick", "AudioOut/GroupTrack", group_id=10),
        audio(2, "Snare", "AudioOut/GroupTrack", group_id=10),
        audio(3, "Vox"),
        factory.track("GroupTrack", 10, "Drums"),
    )
    assert "Bus receiving 2 track(s)" in findings[0].message
    assert [f.track for f in findings if f.severity == "warning"] == ["Vox"]


def test_inactive_and_empty_tracks_are_not_flagged(tmp_path):
    findings = run(
        tmp_path,
        audio(1, "Kick", "AudioOut/Track.10/TrackIn"),
        audio(2, "Muted", active=False),
        factory.track("AudioTrack", 3, "Empty"),
        factory.track("AudioTrack", 10, "Bus"),
    )
    assert not [f for f in findings if f.severity == "warning"]


def test_unknown_destination_warns(tmp_path):
    findings = run(tmp_path, audio(1, "Lost", "AudioOut/Track.99/TrackIn"))
    assert findings[0].severity == "warning" and "Id=99" in findings[0].message


def test_no_buses(tmp_path):
    assert [f.message for f in run(tmp_path, audio(1, "Kick"))] == ["No buses detected"]
