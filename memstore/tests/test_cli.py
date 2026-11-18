import json
import re
from pathlib import Path

import pytest

from memstore import cli, diary
from memstore.store import Store, StoreError, resolve_store_path
from memstore_testkit import tree_hashes
from test_diary import DECISIONS, LESSONS, diary_repo  # noqa: F401  (fixture)

# What /memtoad:bootstrap writes when the store is enabled: an empty digest region, new full entries below it.
FRESH = """# Architectural Decisions

Read the Index first.

---

<!-- memstore:digests:start -->

**Index** (newest first; the digests below follow the same order)


**Digests**


<!-- memstore:digests:end -->
"""


@pytest.fixture
def stub_embedder(monkeypatch, ef):
    monkeypatch.setattr("memstore.store.default_embedding_function", lambda: ef)


def test_store_path_precedence_explicit_then_env_then_git_root(repo, monkeypatch, tmp_path):
    monkeypatch.delenv("MEMSTORE_PATH", raising=False)
    assert resolve_store_path(cwd=repo) == repo.resolve() / "diary/memstore/chroma"
    monkeypatch.setenv("MEMSTORE_PATH", str(tmp_path / "env"))
    assert resolve_store_path(cwd=repo) == tmp_path / "env"
    assert resolve_store_path(str(tmp_path / "flag"), cwd=repo) == tmp_path / "flag"


def test_outside_git_without_a_path_is_an_error(tmp_path, monkeypatch):
    monkeypatch.delenv("MEMSTORE_PATH", raising=False)
    with pytest.raises(StoreError, match="--store"):
        resolve_store_path(cwd=tmp_path)


def test_ingest_dry_run_writes_nothing_and_a_second_ingest_embeds_nothing(diary_repo, tmp_path, ef, stub_embedder, capsys):
    base = ["--store", str(tmp_path / "s"), "--root", str(diary_repo)]
    before = tree_hashes(diary_repo / "diary")
    assert cli.main(base + ["ingest", "diary", "--dry-run"]) == 0
    assert "Would change" in capsys.readouterr().out and not (tmp_path / "s").exists()
    assert cli.main(base + ["ingest", "diary"]) == 0
    assert "Originals untouched" in capsys.readouterr().out
    embedded = ef.embedded
    assert cli.main(base + ["ingest", "diary"]) == 0
    assert ef.embedded == embedded and " 0 added, 0 updated" in capsys.readouterr().out
    assert tree_hashes(diary_repo / "diary") == before


def test_search_status_and_get(diary_repo, tmp_path, stub_embedder, capsys):
    base = ["--store", str(tmp_path / "s"), "--root", str(diary_repo)]
    cli.main(base + ["ingest", "diary"])
    capsys.readouterr()
    assert cli.main(base + ["search", "sub-section stays inside", "--where", "file=architectural_decisions.md", "-n", "2"]) == 0
    out = capsys.readouterr().out
    assert "mem:diary/architectural_decisions#first-decision" in out and "lessons_learned" not in out
    assert cli.main(base + ["status"]) == 0
    out = capsys.readouterr().out
    assert "diary-entry" in out and "Not in git" not in out  # the fixture's files are staged, so recoverable from git
    assert cli.main(base + ["get", "diary/architectural_decisions#first-decision"]) == 0  # "mem:" is optional
    out = capsys.readouterr().out
    assert out.rstrip().endswith("```\n## not a heading\n```") and "### A sub-section" in out
    assert cli.main(base + ["get", "mem:diary/architectural_decisions#nope"]) == 2
    assert "No chunk has pointer" in capsys.readouterr().err


def test_an_unknown_source_and_a_bad_where_are_reported(diary_repo, tmp_path, stub_embedder, capsys):
    base = ["--store", str(tmp_path / "s"), "--root", str(diary_repo)]
    assert cli.main(base + ["ingest", "no_such_source"]) == 2
    assert "known: diary" in capsys.readouterr().err
    cli.main(base + ["ingest", "diary"])
    assert cli.main(base + ["search", "x", "--where", "oops"]) == 2


def test_search_without_a_store_says_so(repo, tmp_path, stub_embedder, capsys):
    code = cli.main(["--store", str(tmp_path / "none"), "--root", str(repo), "search", "x"])
    assert code == 2 and "run `ingest` first" in capsys.readouterr().err


def test_a_fresh_bootstrapped_file_takes_new_entries_below_the_empty_region(repo, tmp_path, ef, stub_embedder, capsys):
    d = repo / "diary"
    d.mkdir()
    (d / "architectural_decisions.md").write_text(FRESH + "\n## brand-new-decision (November 17, 2026)\n\nBody.\n")
    (d / "lessons_learned.md").write_text(FRESH.replace("Architectural Decisions", "Lessons Learned"))
    base = ["--store", str(tmp_path / "s"), "--root", str(repo)]
    assert cli.main(base + ["ingest", "diary"]) == 0
    digests = tmp_path / "d.json"
    digests.write_text(json.dumps({"brand-new-decision": "**Brand new (Nov 17, 2026), active.** The rule."}))
    assert cli.main(base + ["compact", "architectural_decisions", "--digests", str(digests)]) == 0
    text = (d / "architectural_decisions.md").read_text()
    assert "## brand-new-decision" not in text and "- Brand new (Nov 17, 2026), active\n" in text
    assert "→ `mem:diary/architectural_decisions#brand-new-decision`" in text
    capsys.readouterr()
    assert cli.main(base + ["check-pointers"]) == 0
    assert cli.main(base + ["compact", "architectural_decisions"]) == 0  # an index-only rebuild changes nothing
    assert (d / "architectural_decisions.md").read_text() == text


def _package_files():
    return list(Path(cli.__file__).parent.glob("*.py"))


def test_memstore_imports_no_host_application():
    allowed = {"memstore", "argparse", "json", "sys", "collections", "pathlib", "re", "subprocess", "dataclasses",
               "hashlib", "os", "importlib", "chromadb"}
    imported = {m.group(2).split(".")[0] for p in _package_files()
                for m in re.finditer(r"^\s*(from|import)\s+([\w.]+)", p.read_text(), re.M)}
    assert imported <= allowed, f"memstore must import only the standard library and chromadb: {imported - allowed}"


def test_chromadb_is_imported_only_when_a_store_is_opened():
    top_level = [p.name for p in _package_files() if re.search(r"^(import|from)\s+chromadb", p.read_text(), re.M)]
    assert not top_level


def test_store_written_by_another_chromadb_version_is_refused(diary_repo, tmp_path, ef, monkeypatch):
    diary.ingest(Store(tmp_path / "s", embedding_function=ef), diary_repo)
    monkeypatch.setattr("memstore.store.chromadb_version", lambda: "9.9.9")
    with pytest.raises(StoreError, match="written by chromadb"):
        diary.ingest(Store(tmp_path / "s", embedding_function=ef), diary_repo)


def test_export_writes_sorted_verbatim_jsonl(diary_repo, tmp_path, stub_embedder, capsys):
    base = ["--store", str(tmp_path / "s"), "--root", str(diary_repo)]
    cli.main(base + ["ingest", "diary"])
    out = tmp_path / "dump.jsonl"
    assert cli.main(base + ["export", "--out", str(out)]) == 0
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert [r["id"] for r in rows] == sorted(r["id"] for r in rows) and len(rows) == 8  # 4 entries: an exact record and one chunk each
    assert any(r["document"].startswith("## first-decision (August 1, 2026)") for r in rows) and "\r" not in out.read_text()
