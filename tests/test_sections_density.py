import json
from io import StringIO

from rich.console import Console

import factory
from als_analyzer import report
from als_analyzer.analyzers import density, sections
from als_analyzer.cli import main
from als_analyzer.parser import parse_als


def session_from(tmp_path, tracks, **kw):
    return parse_als(factory.write_als(tmp_path / "s.als", factory.als_xml(tracks, **kw)))


def test_sections_messages(als_path):
    s = parse_als(als_path)
    assert s.sections_source == "track 'ARRANGE'"
    messages = [f.message for f in sections.analyze(s)]
    assert messages == [
        "Sections from track 'ARRANGE' (bars assume 4/4)",
        "INTRO: bar 1, 8 bars",
        "DROP: bar 9, 16 bars",
    ]


def test_sections_source_locators(als_path, tmp_path):
    s = session_from(tmp_path, factory.sample_tracks(), locators=[("A", 0)])
    assert s.sections_source == "locators"


def test_sections_warns_when_none_found(tmp_path):
    s = session_from(tmp_path, factory.track("AudioTrack", 1, "Kick"))
    (finding,) = sections.analyze(s)
    assert finding.severity == "warning"


def test_empty_section_warns(tmp_path):
    s = session_from(tmp_path, "", locators=[("A", 8), ("B", 8)])
    # Second locator starts where the first one does not end: first is 0 long.
    assert any(f.severity == "warning" for f in sections.analyze(s))


def density_session(tmp_path):
    clips = factory.clip
    tracks = "".join(
        [
            factory.track("MidiTrack", 1, "ARRANGE", active=False,
                          clips=clips("midi", "INTRO", 0, 32) + clips("midi", "DROP", 32, 96)),
            factory.track("AudioTrack", 2, "Kick", clips=clips("audio", "k", 0, 16)),
            factory.track("AudioTrack", 3, "Pad", clips=clips("audio", "p", 40, 60)),
            factory.track("AudioTrack", 4, "Bass", clips=clips("audio", "b", 0, 96)),
            factory.track("AudioTrack", 5, "Muted", active=False, clips=clips("audio", "m", 0, 96)),
            factory.track("AudioTrack", 6, "Off", clips=clips("audio", "o", 0, 96, disabled=True)),
        ]
    )
    return session_from(tmp_path, tracks)


def test_density_table(tmp_path):
    findings = density.analyze(density_session(tmp_path))
    table = findings[-1].data["table"]
    assert table["columns"] == ["Track", "INTRO", "DROP"]
    # Switched-off tracks are left out; a clip spanning both sections counts in both.
    assert table["rows"] == [["Kick", 1, 0], ["Pad", 0, 1], ["Bass", 1, 1], ["Off", 0, 0]]
    assert [f.message for f in findings[:2]] == ["INTRO: 2 of 4 tracks playing", "DROP: 2 of 4 tracks playing"]


def test_density_without_sections_is_silent(tmp_path):
    assert density.analyze(session_from(tmp_path, factory.track("AudioTrack", 1, "Kick"))) == []


def test_table_in_terminal_and_json(tmp_path, capsys):
    s = density_session(tmp_path)
    findings = density.analyze(s)
    out = StringIO()
    report.render_text(s, findings, Console(file=out, width=100))
    assert "Bass" in out.getvalue() and "·" in out.getvalue()
    assert json.loads(report.to_json(s, findings))["findings"][-1]["data"]["table"]["rows"][0][0] == "Kick"


def test_cli_runs_all_analyzers_in_order(als_path, capsys):
    main([str(als_path), "--json"])
    names = [f["analyzer"] for f in json.loads(capsys.readouterr().out)["findings"]]
    assert list(dict.fromkeys(names))[:3] == ["inventory", "sections", "density"]
