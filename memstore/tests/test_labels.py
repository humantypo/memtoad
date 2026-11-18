"""Labels: an entry stays in force unless its date parenthetical says `superseded by <slug>` or `retired <Mon YYYY>: <why>`."""
import pytest

from memstore import check, cli, diary
from memstore.store import StoreError
from test_check import compacted
from test_cli import stub_embedder  # noqa: F401  (fixture)
from test_diary import diary_repo  # noqa: F401  (fixture)

DEC = "architectural_decisions"
FIRST = f"mem:diary/{DEC}#first-decision"
SECOND = f"mem:diary/{DEC}#second-decision-with-a-long-title-that-is-not-a-slug"


@pytest.mark.parametrize("heading", ["install-script-is-the-last (June 2026)", "optional-memstore-archive (November 17, 2026)",
                                     "A long title that is not a slug at all (Aug 4, 2026)"])
@pytest.mark.parametrize("label", ["superseded by committer-diary-prep-only", "retired Nov 2026: the install scripts were removed"])
def test_a_label_never_changes_the_slug_or_the_date(heading, label):
    labelled = diary.with_label(heading, label)
    assert diary.make_slug(labelled) == diary.make_slug(heading)
    assert diary.entry_date(labelled, "") == diary.entry_date(heading, "")
    assert diary.label_of(labelled) == label


@pytest.mark.parametrize("text,expected", [
    ("slug (June 2026)", None),
    ("First (Aug 1, 2026), active.", None),
    ("committer-diary-prep-only (August 2026, supersedes committer-owns-commit-discipline)", None),  # tidy's fold form
    ("x (June 2026; superseded by y)", "superseded by y"),
    ("**X (Jun 3, 2026; retired Nov 2026: gone in 1.2.0).**", "retired Nov 2026: gone in 1.2.0"),
])
def test_label_grammar(text, expected):
    assert diary.label_of(text) == expected


@pytest.mark.parametrize("text", ["x (June 2026, superseded by y)", "x (June 2026; retired Nov 2026: reason (with parens))",
                                  "x (June 2026; retired: no date)", "x (June 2026; retired Nov 2026: " + "r" * 130 + ")"])
def test_a_near_miss_label_is_an_error_not_silently_in_force(text):
    with pytest.raises(diary.LabelError):
        diary.label_of(text)


@pytest.mark.parametrize("label", ["retired Nov 2026: has (parens)", "retired November: no year", "superseded by Not_A_Slug",
                                   "retired Nov 2026: " + "r" * 130])
def test_set_label_refuses_a_bad_label(label):
    with pytest.raises(StoreError):
        diary.check_label(label)


def test_sorting_uses_the_entry_date_not_the_retirement_date():
    old = "- **Old (Jun 3, 2026; retired Mar 5, 2027: gone).** a → `mem:diary/x#old`"
    new = "- **New (Dec 1, 2026).** b → `mem:diary/x#new`"
    assert diary._sorted_digests([old, new]) == [new, old]


def test_an_unlabelled_diary_rebuilds_byte_identically_and_has_no_sublist(diary_repo, store):
    path = compacted(diary_repo, store) / f"{DEC}.md"
    before = path.read_text()
    diary.compact(None, path, {})
    assert path.read_text() == before and "No longer in force" not in before


def test_labelling_a_digest_moves_it_below_the_entries_in_force_and_clearing_restores_it(diary_repo, store):
    folder = compacted(diary_repo, store)
    path = folder / f"{DEC}.md"
    original = path.read_text()
    new = diary.set_label(path, "first-decision", "superseded by second-decision-with-a-long-title-that-is-not-a-slug")
    assert new.startswith("First (Aug 1, 2026; superseded by second-") and ", active" not in new
    index, bullets = diary.split_region(path.read_text())
    assert index[0].startswith("- Second") and index[1].startswith("- First (Aug 1, 2026; superseded by")
    assert "**No longer in force**" in path.read_text()
    rep = check.check_diary(store, folder)
    assert rep.ok, rep.errors
    assert diary.labels(folder) == {FIRST: "superseded by second-decision-with-a-long-title-that-is-not-a-slug"}
    diary.set_label(path, "first-decision", None)
    assert path.read_text() == original.replace("(Aug 1, 2026), active", "(Aug 1, 2026)")


def test_labelling_a_full_entry_edits_its_heading_only_and_keeps_its_pointer(diary_repo, store):
    path = diary_repo / "diary" / f"{DEC}.md"
    diary.set_label(path, "first-decision", "retired Nov 2026: replaced by the hook")
    text = path.read_text()
    assert "## first-decision (August 1, 2026; retired Nov 2026: replaced by the hook)" in text
    assert [e.slug for e in diary.parse(text, diary.FILES[DEC]).entries][0] == "first-decision"
    diary.ingest(store, diary_repo)
    assert store.get_pointer(FIRST)
    assert check.check_diary(store, diary_repo / "diary").ok


def test_dry_run_writes_nothing(diary_repo, store):
    path = compacted(diary_repo, store) / f"{DEC}.md"
    before = path.read_text()
    diary.set_label(path, "first-decision", "retired Nov 2026: x", dry_run=True)
    assert path.read_text() == before


def test_an_archived_entry_with_no_digest_is_an_error(diary_repo, store):
    folder = compacted(diary_repo, store)
    path = folder / f"{DEC}.md"
    path.write_text("\n".join(l for l in path.read_text().split("\n") if not l.endswith("#first-decision`")))
    diary.compact(None, path, {})
    rep = check.check_diary(store, folder)
    assert any("'first-decision' has neither a digest nor a full entry" in e for e in rep.errors)


def test_a_malformed_label_is_an_error_and_a_missing_successor_a_warning(diary_repo, store):
    folder = compacted(diary_repo, store)
    path = folder / f"{DEC}.md"
    diary.set_label(path, "first-decision", "superseded by no-such-entry")
    rep = check.check_diary(store, folder)
    assert rep.ok and any("names no entry" in w for w in rep.warnings)
    path.write_text(path.read_text().replace("; superseded by no-such-entry", ", superseded by no-such-entry"))
    assert any("looks labelled" in e for e in check.check_diary(store, folder).errors)


def test_a_reason_is_not_reported_as_an_unsupported_digest_name(diary_repo, store):
    folder = compacted(diary_repo, store)
    diary.set_label(folder / f"{DEC}.md", "second-decision-with-a-long-title-that-is-not-a-slug", "retired Nov 2026: gone in 1.2.0")
    assert not check.check_diary(store, folder, provenance=True).warnings[1:]  # only the fixture's own first_rule/300 warning
    assert not any("1.2" in w for w in check.check_diary(store, folder).warnings)


def test_cli_set_label_then_search_get_and_index_show_it(diary_repo, tmp_path, stub_embedder, capsys):
    base = ["--store", str(tmp_path / "s"), "--root", str(diary_repo)]
    assert cli.main(base + ["ingest", "diary"]) == 0
    assert cli.main(base + ["set-label", FIRST, "--retired", "Nov 2026: replaced by the hook"]) == 0
    assert "Labelled" in capsys.readouterr().out
    assert cli.main(base + ["search", "first decision body", "-n", "10"]) == 0
    assert "NOT IN FORCE: retired Nov 2026: replaced by the hook" in capsys.readouterr().out
    assert cli.main(base + ["get", FIRST]) == 0
    assert "NOT IN FORCE" in capsys.readouterr().out
    assert cli.main(base + ["index", "--budget", "1"]) == 0
    assert "NOT IN FORCE: retired Nov 2026" in (out := capsys.readouterr().out) and "NOTICE" not in out  # full entries: no Index yet
    assert cli.main(base + ["set-label", FIRST, "--clear"]) == 0
    assert cli.main(base + ["set-label", "mem:diary/nope#x", "--clear"]) == 2


def test_cli_index_counts_and_budget_notice(diary_repo, tmp_path, stub_embedder, capsys, store):
    compacted(diary_repo, store)
    base = ["--store", str(store.path), "--root", str(diary_repo)]
    assert cli.main(base + ["set-label", FIRST, "--superseded-by", "second-decision-with-a-long-title-that-is-not-a-slug"]) == 0
    capsys.readouterr()
    assert cli.main(base + ["index", "--budget", "1"]) == 0
    out = capsys.readouterr().out
    assert "1 in force, 1 no longer in force" in out and "No longer in force (superseded or retired):" in out
    assert "NOTICE: the Indexes are about" in out
    assert cli.main(base + ["index"]) == 0
    assert "NOTICE" not in capsys.readouterr().out


def test_a_digest_without_a_slug_is_reported_not_a_crash(diary_repo, tmp_path, stub_embedder, capsys, store):
    folder = compacted(diary_repo, store)
    path = folder / f"{DEC}.md"
    path.write_text(path.read_text().replace(f"`{FIRST}`", f"`mem:diary/{DEC}`"))
    rep = check.check_diary(store, folder)
    assert any("no trailing pointer" in e or "does not resolve" in e for e in rep.errors)
    base = ["--store", str(store.path), "--root", str(diary_repo)]
    assert cli.main(base + ["search", "rule two"]) == 0
    assert cli.main(base + ["get", SECOND]) == 0


def test_an_entry_renamed_after_ingest_is_caught_and_restore_fixes_it(diary_repo, tmp_path, stub_embedder, capsys, store):
    folder = compacted(diary_repo, store)
    path = folder / f"{DEC}.md"
    path.write_text(path.read_text() + "\n## third-decision-typo (Sep 1, 2026)\n\nBody three.\n")
    diary.ingest(store, diary_repo)
    path.write_text(path.read_text().replace("third-decision-typo", "third-decision-fixed"))  # renamed after ingest
    diary.ingest(store, diary_repo)
    errors = check.check_diary(store, folder).errors
    assert any("'third-decision-typo' has neither" in e and "restore" in e for e in errors)
    base = ["--store", str(store.path), "--root", str(diary_repo)]
    assert cli.main(base + ["restore", f"mem:diary/{DEC}#third-decision-typo"]) == 0
    assert "Restored" in capsys.readouterr().out
    assert cli.main(base + ["restore", f"mem:diary/{DEC}#third-decision-typo"]) == 2  # already back
    diary.compact(store, path, {"third-decision-typo": "**Third (Sep 1, 2026; superseded by third-decision-fixed).** Typo.",
                                "third-decision-fixed": "**Third (Sep 1, 2026).** Body three."})
    rep = check.check_diary(store, folder)
    assert rep.ok, rep.errors
    index, _ = diary.split_region(path.read_text())
    assert index[-1] == "- Third (Sep 1, 2026; superseded by third-decision-fixed)"
