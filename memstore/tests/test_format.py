"""Store format compatibility: decided from chromadb's own migrations table, checked before chromadb opens the store."""
import sqlite3

import pytest

from memstore import cli, diary, store as store_mod
from memstore.store import Store, StoreError
from memstore_testkit import tree_hashes
from test_cli import stub_embedder  # noqa: F401  (fixture)
from test_diary import diary_repo  # noqa: F401  (fixture)


@pytest.fixture
def built(diary_repo, tmp_path, ef):
    path = tmp_path / "s"
    diary.ingest(Store(path, embedding_function=ef), diary_repo)
    return path


def _sql(path, statement):
    con = sqlite3.connect(path / "chroma.sqlite3")
    con.execute(statement)
    con.commit()
    con.close()


def test_the_installed_chromadb_writes_exactly_the_migrations_it_knows(built):
    assert store_mod.store_migrations(built) == store_mod.known_migrations() != set()
    assert store_mod.compatibility(built) == ("same", "")
    assert store_mod.recorded_chromadb(built) == store_mod.chromadb_version()


def test_a_store_from_a_newer_chromadb_is_refused_untouched(built, diary_repo, ef):
    _sql(built, "INSERT INTO migrations VALUES ('sysdb', 999, '00999-future.sqlite.sql', 'select 1', 'h')")
    before = tree_hashes(built)
    with pytest.raises(StoreError, match="sysdb 999.*does not know"):
        diary.ingest(Store(built, embedding_function=ef), diary_repo)
    assert tree_hashes(built) == before  # chromadb itself would have opened it without complaint


def test_an_open_that_would_migrate_is_refused_before_chromadb_touches_the_store(built, diary_repo, ef, monkeypatch):
    known = store_mod.known_migrations() | {("sysdb", 999)}  # as if the installed chromadb were one format step ahead
    monkeypatch.setattr("memstore.store.known_migrations", lambda: known)
    before = tree_hashes(built)
    with pytest.raises(StoreError, match="would migrate.*sysdb 999.*upgrade-store"):
        diary.ingest(Store(built, embedding_function=ef), diary_repo)
    assert tree_hashes(built) == before
    assert Store(built, embedding_function=ef, allow_upgrade=True).collection.count()  # the deliberate path opens it


def test_a_version_that_cannot_read_the_copy_is_refused(built, diary_repo, ef, monkeypatch):
    monkeypatch.setattr("memstore.store.chromadb_version", lambda: "1.6.0")
    monkeypatch.setattr("memstore.store.read_probe", lambda p: (_ for _ in ()).throw(RuntimeError("bad segment")))
    with pytest.raises(StoreError, match="cannot read.*bad segment"):
        diary.ingest(Store(built, embedding_function=ef), diary_repo)


def test_cli_status_and_upgrade_store(built, diary_repo, stub_embedder, capsys, monkeypatch):
    base = ["--store", str(built), "--root", str(diary_repo)]
    assert cli.main(base + ["status"]) == 0
    assert "compatible" in capsys.readouterr().out
    assert cli.main(base + ["upgrade-store"]) == 0
    assert "Nothing to do" in capsys.readouterr().out
    known = store_mod.known_migrations() | {("sysdb", 999)}
    monkeypatch.setattr("memstore.store.known_migrations", lambda: known)
    monkeypatch.setattr("memstore.cli.compatibility", store_mod.compatibility)
    assert cli.main(base + ["status"]) == 1
    assert "refused until `upgrade-store`" in capsys.readouterr().out
    assert cli.main(base + ["search", "decision"]) == 2
    assert "would migrate" in capsys.readouterr().err
    assert cli.main(base + ["upgrade-store", "--dry-run"]) == 0
    assert "Would migrate" in capsys.readouterr().out
    assert cli.main(base + ["upgrade-store"]) == 0
    assert "raise the project's chromadb floor" in capsys.readouterr().out


def test_the_known_migrations_are_cached_per_chromadb_version(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMSTORE_CACHE", str(tmp_path / "c"))
    monkeypatch.setattr("memstore.store._KNOWN", None)
    fresh = store_mod.known_migrations()
    cache = store_mod._cache_file()
    assert cache.is_file() and cache.name == f"known-migrations-chromadb-{store_mod.chromadb_version()}.json"
    monkeypatch.setattr("memstore.store._KNOWN", None)
    cache.write_text("not json")
    assert store_mod.known_migrations() == fresh  # a corrupt cache is rebuilt, never trusted


def test_reindex_and_drop_are_refused_too_when_they_would_migrate(built, ef, monkeypatch):
    known = store_mod.known_migrations() | {("sysdb", 999)}
    monkeypatch.setattr("memstore.store.known_migrations", lambda: known)
    before = tree_hashes(built)
    with pytest.raises(StoreError, match="would migrate"):
        Store(built, embedding_function=ef).reindex()
    with pytest.raises(StoreError, match="would migrate"):
        Store(built, embedding_function=ef).drop()
    assert tree_hashes(built) == before


def test_an_unreadable_store_database_is_reported_not_read_as_a_format(built, ef):
    (built / "chroma.sqlite3").write_bytes(b"not a database at all" * 100)
    with pytest.raises(StoreError, match="Cannot read the format"):
        store_mod.compatibility(built)


def test_a_chromadb_that_records_no_migrations_is_not_treated_as_older(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMSTORE_CACHE", str(tmp_path / "c"))
    monkeypatch.setattr("memstore.store._KNOWN", None)
    monkeypatch.setattr("memstore.store.store_migrations", lambda p: set())
    with pytest.raises(StoreError, match="memstore needs updating"):
        store_mod.known_migrations()
    assert store_mod._KNOWN is None  # not cached as an empty format
