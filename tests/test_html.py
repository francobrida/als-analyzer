from xml.sax.saxutils import escape

import pytest

import factory
from als_analyzer import cli
from als_analyzer.analyzers import run_all
from als_analyzer.parser import parse_als
from als_analyzer.report_html import to_html


def html_for(path):
    s = parse_als(path)
    return to_html(s, run_all(s))


def test_html_has_sections_heatmap_and_warning_count(als_path):
    html = html_for(als_path)
    assert html.startswith("<!doctype html>")
    for name in ("inventory", "sections", "density", "plugins"):
        assert f"<summary>{name}" in html
    assert "<td style='--v:1.000'>1</td>" in html  # Kick in INTRO is the busiest cell
    assert "warning(s)" in html


def test_html_summary_nav_and_table_extras(als_path):
    html = html_for(als_path)
    assert "<nav" in html and "href='#a-density'" in html and "id='a-density'" in html
    assert "<div class='l'>Third-party plugins</div>" in html and "<div class='l'>Sections</div>" in html
    # Section notes under the column names, group header rows and the totals row of the density table.
    assert "<small>bar 9</small>" in html
    assert "<tr class='grp'><th colspan='3'>Drums</th></tr>" in html
    assert "<tfoot>" in html and "Tracks playing" in html


def test_html_escapes_untrusted_names(tmp_path):
    # XML-escaped in the file; the parser hands back a real "<script>" name.
    evil = escape("<script>alert(1)</script>")
    xml = factory.als_xml(factory.track("AudioTrack", 1, evil, devices=factory.plugin("VST3", "Comp")))
    html = html_for(factory.write_als(tmp_path / "e.als", xml))
    assert parse_als(tmp_path / "e.als").tracks[0].name == "<script>alert(1)</script>"
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_html_is_self_contained(als_path):
    html = html_for(als_path)
    assert "<script" not in html and "http://" not in html and "https://" not in html


def test_cli_html_writes_file(als_path, tmp_path, capsys):
    out = tmp_path / "report.html"
    assert cli.main([str(als_path), "--html", str(out)]) == 0
    assert "demo.als" in out.read_text(encoding="utf-8")
    assert str(out) in capsys.readouterr().out


def test_cli_open_uses_temp_file_and_browser(als_path, monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(cli.webbrowser, "open", opened.append)
    assert cli.main([str(als_path), "--open"]) == 0
    assert len(opened) == 1 and opened[0].startswith("file:///") and opened[0].endswith("als-analyzer-demo.html")


def test_cli_rejects_json_with_html(als_path):
    with pytest.raises(SystemExit) as exc:
        cli.main([str(als_path), "--json", "--open"])
    assert exc.value.code == 2


def test_cli_html_unwritable_path(als_path, tmp_path, capsys):
    assert cli.main([str(als_path), "--html", str(tmp_path / "missing" / "r.html")]) == 1
