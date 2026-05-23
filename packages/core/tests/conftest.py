from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_vault_path() -> Path:
    """The committed read-only sample vault."""
    return FIXTURES / "sample-vault"


@pytest.fixture
def temp_vault(tmp_path: Path, sample_vault_path: Path) -> Path:
    """A writable copy of the sample vault in a temp dir."""
    dest = tmp_path / "vault"
    shutil.copytree(sample_vault_path, dest)
    return dest
