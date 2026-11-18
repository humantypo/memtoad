import subprocess

import pytest

from memstore.store import Store
from memstore_testkit import StubEmbedding


@pytest.fixture(autouse=True)
def _private_cache(tmp_path_factory, monkeypatch):
    """Keep the per-version migrations cache out of the user's home directory."""
    monkeypatch.setenv("MEMSTORE_CACHE", str(tmp_path_factory.getbasetemp() / "memstore-cache"))


@pytest.fixture
def ef():
    return StubEmbedding()


@pytest.fixture
def repo(tmp_path):
    """A throwaway git repo."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


@pytest.fixture
def store(tmp_path, ef):
    return Store(tmp_path / "store", embedding_function=ef)
