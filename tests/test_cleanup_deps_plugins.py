import factory
from als_analyzer.analyzers import cleanup, dependencies, plugins
from als_analyzer.parser import parse_als


def test_cleanup_on_sample_session(als_path):
    findings = cleanup.analyze(parse_als(als_path))
    by_sev = {(f.severity, f.track): f.message for f in findings}
    assert by_sev[("info", "Kick")] == "1 disabled clip(s): kick2"
    # Hat has a plugin but no clips; the group and the guide track are not "empty with devices".
    assert by_sev[("warning", "Hat")] == "Empty track with 1 device(s) loaded"
    assert ("warning", "Drums") not in by_sev
    unnamed = by_sev[("info", None)]
    assert "Hat" in unnamed and "A-Reverb" not in unnamed and "Kick" not in unnamed


def test_cleanup_bus_with_devices_is_not_empty_and_repeated_clips_are_counted(tmp_path):
    clip = factory.clip
    xml = factory.als_xml(
        factory.track("AudioTrack", 1, "Src", target="AudioOut/Track.2/TrackIn",
                      clips=clip("audio", "take", 0, 4, disabled=True) + clip("audio", "take", 4, 8, disabled=True))
        + factory.track("AudioTrack", 2, "Bus", devices=factory.plugin("VST3", "Comp"))
    )
    s = parse_als(factory.write_als(tmp_path / "b.als", xml))
    messages = [f.message for f in cleanup.analyze(s)]
    assert "2 disabled clip(s): take x2" in messages
    assert not any("Empty track" in m for m in messages)


def test_cleanup_nothing_to_report(tmp_path):
    xml = factory.als_xml(factory.track("AudioTrack", 1, "Kick", clips=factory.clip("audio", "k", 0, 4)))
    s = parse_als(factory.write_als(tmp_path / "c.als", xml))
    assert [f.message for f in cleanup.analyze(s)] == ["Nothing to clean up"]


def test_dependencies_flags_samples_outside_project(als_path):
    findings = dependencies.analyze(parse_als(als_path))
    (warn,) = [f for f in findings if f.severity == "warning"]
    assert warn.track == "Kick" and warn.data == {"paths": ["C:/Samples/kick_Amin.wav"]}


def test_dependencies_samples_inside_project_are_fine(als_path):
    inside = (als_path.parent / "Samples" / "Imported" / "a.wav").as_posix()
    other_case = inside.upper()  # same file, different case/style
    xml = factory.als_xml(
        factory.track("AudioTrack", 1, "A", clips=factory.clip("audio", "a", 0, 4, path=inside))
        + factory.track("AudioTrack", 2, "B", clips=factory.clip("audio", "b", 0, 4, path=other_case.replace("/", "\\")))
    )
    s = parse_als(factory.write_als(als_path, xml))
    assert [f.message for f in dependencies.analyze(s)] == ["All 2 sample(s) are inside the project folder"]


def test_dependencies_infers_project_from_sample_paths_when_als_was_copied(tmp_path):
    clip = factory.clip
    xml = factory.als_xml(
        factory.track("AudioTrack", 1, "A", clips=clip("audio", "a", 0, 4, path="C:/Music/My Project/Samples/a.wav"))
        + factory.track("AudioTrack", 2, "B", clips=clip("audio", "b", 0, 4, path="C:/Lib/Splice/b.wav"))
    )
    folder = tmp_path / "copies"
    folder.mkdir()
    findings = dependencies.analyze(parse_als(factory.write_als(folder / "x.als", xml)))
    assert findings[0].severity == "info" and "inferred" in findings[0].message
    assert [(f.track, f.severity) for f in findings[1:]] == [("B", "warning")]


def test_dependencies_without_project_folder_warns(tmp_path):
    folder = tmp_path / "loose"
    folder.mkdir()
    s = parse_als(factory.write_als(folder / "x.als", factory.als_xml()))
    assert dependencies.analyze(s)[0].severity == "warning"


def test_plugins_listed_per_track_and_summarized(als_path):
    findings = plugins.analyze(parse_als(als_path))
    assert findings[0].message == "2 third-party plugin(s) needed: Serum (VST3), Sylenth1 (VST2)"
    assert [(f.track, f.message) for f in findings[1:]] == [
        ("Kick", "Serum (VST3)"),
        ("Hat", "Sylenth1 (VST2)"),
    ]


def test_plugins_none(tmp_path):
    s = parse_als(factory.write_als(tmp_path / "p.als", factory.als_xml()))
    assert [f.message for f in plugins.analyze(s)] == ["No third-party plugins"]
