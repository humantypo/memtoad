import subprocess

import pytest

from memstore.store import Store
from memstore_testkit import StubEmbedding


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
