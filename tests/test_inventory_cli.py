import json
import types

import factory
from als_analyzer import analyzers
from als_analyzer.analyzers import inventory
from als_analyzer.cli import main
from als_analyzer.parser import parse_als


def test_inventory_counts(als_path):
    messages = [f.message for f in inventory.analyze(parse_als(als_path))]
    assert "Tempo: 133 BPM" in messages
    assert "Tracks: 2 audio, 1 MIDI, 1 groups" in messages
    assert "Return tracks: 1" in messages
    assert "Sections: 2 (INTRO, DROP)" in messages


def test_inventory_warns_without_tempo(tmp_path):
    xml = '<Ableton Creator="Live 9"><LiveSet><Tracks/></LiveSet></Ableton>'
    findings = inventory.analyze(parse_als(factory.write_als(tmp_path / "a.als", xml)))
    assert [f.severity for f in findings if "Tempo" in f.message] == ["warning"]


def test_inventory_is_discovered_first():
    assert analyzers.discover()[0] is inventory


def test_failing_analyzer_does_not_stop_the_others(als_path, monkeypatch):
    def boom(session):
        raise RuntimeError("x")

    bad = types.SimpleNamespace(NAME="bad", analyze=boom)
    monkeypatch.setattr(analyzers, "discover", lambda: [bad, inventory])
    findings = analyzers.run_all(parse_als(als_path))
    assert findings[0].analyzer == "bad" and findings[0].severity == "warning"
    assert any(f.analyzer == "inventory" for f in findings)


def test_cli_json(als_path, capsys):
    assert main([str(als_path), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["file"] == "demo.als" and out["tempo"] == 133
    assert out["findings"][0]["analyzer"] == "inventory"


def test_cli_text(als_path, capsys):
    assert main([str(als_path)]) == 0
    assert "Tempo: 133 BPM" in capsys.readouterr().out


def test_cli_sections_track_option(als_path, capsys):
    main([str(als_path), "--json", "--sections-track", "nope"])
    messages = [f["message"] for f in json.loads(capsys.readouterr().out)["findings"]]
    assert "Sections: 0" in messages


def test_cli_missing_file_and_bad_file(tmp_path, capsys):
    assert main([str(tmp_path / "nope.als")]) == 1
    bad = factory.write_als(tmp_path / "bad.als", "<html/>")
    assert main([str(bad)]) == 1
    assert "error:" in capsys.readouterr().err
