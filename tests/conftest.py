import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # lets tests `import factory`

import factory  # noqa: E402


@pytest.fixture
def als_path(tmp_path):
    """Gzipped synthetic session inside a 'Demo Project' folder."""
    folder = tmp_path / "Demo Project"
    folder.mkdir()
    return factory.write_als(folder / "demo.als", factory.als_xml(factory.sample_tracks()))
