import json
import subprocess

import pytest

from memstore import check, cli, diary
from memstore.store import Store
from test_diary import DECISIONS, LESSONS, diary_repo  # noqa: F401  (fixture)


def compacted(diary_repo, store):
    diary.ingest(store, diary_repo)
    diary.compact(store, diary_repo / "diary/architectural_decisions.md", {
        "first-decision": "**First (Aug 1, 2026), active.** The `first_rule()` applies to 300 files.",
        "second-decision-with-a-long-title-that-is-not-a-slug": "**Second (Jul 2, 2026).** Rule two."})
    return diary_repo / "diary"


def test_a_clean_diary_passes(diary_repo, store):
    folder = compacted(diary_repo, store)
    rep = check.check_diary(store, folder)
    assert rep.ok and rep.checked == 2


def test_names_and_numbers_the_source_lacks_are_warnings_not_errors(diary_repo, store):
    folder = compacted(diary_repo, store)
    rep = check.check_diary(store, folder)
    assert rep.ok and any("first_rule" in w and "300" in w for w in rep.warnings)
    assert not check.check_diary(store, folder, provenance=False).warnings


def test_a_dangling_or_wrong_pointer_is_an_error(diary_repo, store):
    folder = compacted(diary_repo, store)
    p = folder / "architectural_decisions.md"
    p.write_text(p.read_text().replace("#first-decision`", "#no-such-entry`"))
    rep = check.check_diary(store, folder)
    assert any("does not resolve" in e and "no-such-entry" in e for e in rep.errors)
    p.write_text(p.read_text().replace("mem:diary/architectural_decisions#no-such", "mem:diary/lessons_learned#no-such"))
    assert any("another file" in e for e in check.check_diary(store, folder).errors)


def test_malformed_digests_and_a_stale_index_are_errors(diary_repo, store):
    folder = compacted(diary_repo, store)
    p = folder / "architectural_decisions.md"
    good = p.read_text()
    p.write_text(good.replace("**Second (Jul 2, 2026).** Rule two.", "Rule two with a stray `tick."))
    errs = check.check_diary(store, folder).errors
    assert any("bold title" in e for e in errs) and any("unbalanced backticks" in e for e in errs)
    p.write_text(good.replace("- Second (Jul 2, 2026)\n", ""))
    assert any("Index is stale" in e for e in check.check_diary(store, folder).errors)
    p.write_text(good.replace(diary.REGION_END, ""))
    assert any("only one of its two markers" in e for e in check.check_diary(store, folder).errors)


def test_full_entries_not_yet_compacted_are_reported_as_notes(diary_repo, store):
    folder = compacted(diary_repo, store)
    p = folder / "architectural_decisions.md"
    p.write_text(p.read_text() + "\n## fresh-decision (October 30, 2026)\n\nBody.\n")
    rep = check.check_diary(store, folder)
    assert rep.ok and any("fresh-decision" in i and "NOT archived" in i for i in rep.info)
    diary.ingest(store, diary_repo)
    assert any("fresh-decision" in i and "archived" in i and "NOT" not in i for i in check.check_diary(store, folder).info)


def test_pointers_in_other_markdown_must_resolve_but_templates_are_ignored(diary_repo, store):
    folder = compacted(diary_repo, store)
    (diary_repo / "NOTES.md").write_text("See `mem:diary/architectural_decisions#first-decision`, and the template "
                                         "mem:diary/<file>#<slug> and mem:other/<source>/x. Bad: mem:diary/lessons_learned#ghost.")
    subprocess.run(["git", "add", "-A"], cwd=diary_repo, check=True)
    rep = check.check_docs(store, diary_repo)
    assert [e for e in rep.errors] == ["NOTES.md: pointer does not resolve: mem:diary/lessons_learned#ghost"]


def test_cli_index_and_check_pointers(diary_repo, tmp_path, ef, monkeypatch, capsys):
    monkeypatch.setattr("memstore.store.default_embedding_function", lambda: ef)
    base = ["--store", str(tmp_path / "s"), "--root", str(diary_repo)]
    cli.main(base + ["ingest", "diary"])
    store = Store(tmp_path / "s", embedding_function=ef)
    diary.compact(store, diary_repo / "diary/architectural_decisions.md", {"first-decision": "**First (Aug 1, 2026).** Rule."})
    capsys.readouterr()
    assert cli.main(base + ["index"]) == 0
    out = capsys.readouterr().out
    assert "architectural_decisions: 1 digests" in out and "- First (Aug 1, 2026)" in out and "[FULL" in out and "Drill down" in out
    assert cli.main(base + ["check-pointers"]) == 0
    assert "0 errors" in capsys.readouterr().out
    p = diary_repo / "diary/architectural_decisions.md"
    p.write_text(p.read_text().replace("#first-decision`", "#gone`"))
    assert cli.main(base + ["check-pointers"]) == 1
    assert "ERROR" in capsys.readouterr().out
