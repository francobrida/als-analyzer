import subprocess
import sys

from als_analyzer import context_menu


def test_command_quotes_path_and_opens_report():
    cmd = context_menu._command()
    assert cmd.endswith('-m als_analyzer "%1" --open') and cmd.startswith('"')


def test_python_dash_m_runs_cli(als_path):
    out = subprocess.run([sys.executable, "-m", "als_analyzer", str(als_path), "--json"], capture_output=True, text=True)
    assert out.returncode == 0 and '"inventory"' in out.stdout
