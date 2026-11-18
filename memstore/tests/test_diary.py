import json
import subprocess

import pytest

from memstore import cli, diary
from memstore.store import Store, StoreError

DECISIONS = """# Architectural Decisions

Intro line.

---

## first-decision (August 1, 2026)

Body of the first decision.

### A sub-section

Stays inside the first decision.

```
## not a heading
```

---

## Second decision: with a long title that is not a slug (July 2, 2026)

Body two.

---
"""

LESSONS = """# Lessons Learned

Intro.

---

## a-lesson-with-a-sub-section (October 3, 2026)

**Rule**: Body of the lesson.

### A sub-section

Stays inside the lesson.

---

## another-lesson-with-detail (September 1, 2026)

Body.
"""


@pytest.fixture
def diary_repo(repo):
    d = repo / "diary"
    d.mkdir()
    (d / "architectural_decisions.md").write_text(DECISIONS)
    (d / "lessons_learned.md").write_text(LESSONS)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return repo


def parsed(text, stem="architectural_decisions"):
    return diary.parse(text, diary.FILES[stem])


def test_decisions_subsections_and_fenced_headings_stay_inside_their_entry():
    p = parsed(DECISIONS)
    assert [e.slug for e in p.entries] == ["first-decision", "second-decision-with-a-long-title-that-is-not-a-slug"]
    assert "### A sub-section" in p.entries[0].text and "## not a heading" in p.entries[0].text
    assert p.entries[0].text.endswith("```") and not p.entries[0].text.endswith("---")  # exact text, closing rule dropped
    assert p.entries[0].date == "2026-08-01" and p.entries[1].date == "2026-07-02"


def test_lessons_sub_sections_stay_inside_their_entry():
    p = parsed(LESSONS, "lessons_learned")
    assert [e.slug for e in p.entries] == ["a-lesson-with-a-sub-section", "another-lesson-with-detail"]
    assert "### A sub-section" in p.entries[0].text and "Stays inside the lesson." in p.entries[0].text
    assert len(p.dividers) == 1 and p.entries[0].date == "2026-10-03"  # only the level-1 title


def test_duplicate_slugs_fail_the_ingest(diary_repo, store):
    (diary_repo / "diary/architectural_decisions.md").write_text(DECISIONS + "\n## first-decision (August 1, 2026)\n\nAgain.\n")
    with pytest.raises(StoreError, match="duplicate entry slugs"):
        diary.ingest(store, diary_repo)


def test_ingest_stores_exact_text_and_get_returns_it(diary_repo, store, capsys):
    diary.ingest(store, diary_repo)
    exact = parsed(DECISIONS).entries[0].text
    hits = store.get_pointer("mem:diary/architectural_decisions#first-decision")
    assert [h.document for h in hits] == [exact]
    assert {m["kind"] for m in store.collection.get(where={"slug": "first-decision"})["metadatas"]} == {"diary-entry", "diary-chunk"}


def test_search_returns_chunks_not_the_duplicate_exact_entry(diary_repo, tmp_path, ef, monkeypatch, capsys):
    monkeypatch.setattr("memstore.store.default_embedding_function", lambda: ef)
    base = ["--store", str(tmp_path / "s"), "--root", str(diary_repo)]
    cli.main(base + ["ingest", "diary"])
    capsys.readouterr()
    cli.main(base + ["search", "body of the first decision", "-n", "6"])
    out = capsys.readouterr().out
    assert "mem:diary/architectural_decisions#first-decision" in out
    assert cli.main(base + ["search", "body", "--kind", "diary-entry"]) == 0


def digest_file(tmp_path, **d):
    p = tmp_path / "d.json"
    p.write_text(json.dumps(d))
    return p


def test_compact_replaces_entries_with_a_pointer_and_keeps_the_archive(diary_repo, store):
    diary.ingest(store, diary_repo)
    path = diary_repo / "diary/architectural_decisions.md"
    before, after, slugs = diary.compact(store, path, {"first-decision": "**First (Aug 1, 2026).** The rule."})
    text = path.read_text()
    assert slugs == ["first-decision"] and after == len(text.encode())  # a toy entry is too small to shrink net of the markers
    assert diary.REGION_START in text and "- **First (Aug 1, 2026).** The rule. → `mem:diary/architectural_decisions#first-decision`" in text
    assert "Body of the first decision" not in text and "## Second decision" in text and text.index(diary.REGION_START) < text.index("## Second")
    assert text.index("# Architectural Decisions") < text.index("Intro line.") < text.index(diary.REGION_START)  # after the title and intro
    # a re-ingest sees the digest as no entry, deletes nothing, and the exact text is still retrievable
    again = diary.ingest(store, diary_repo).sources["diary/architectural_decisions"]
    assert again.deleted == 0
    assert "Body of the first decision" in store.get_pointer("mem:diary/architectural_decisions#first-decision")[0].document
    # a second compaction extends the same region
    diary.compact(store, path, {"second-decision-with-a-long-title-that-is-not-a-slug": "**Second.** Rule two."})
    text = path.read_text()
    assert text.count(diary.REGION_START) == 1 and text.index("**First") < text.index("**Second") < text.index(diary.REGION_END)
    assert "## " not in text.replace("<!--", "")  # no full entry is left


def test_compacting_a_lesson_keeps_its_sub_section_out_of_the_file_and_in_the_archive(diary_repo, store):
    diary.ingest(store, diary_repo)
    path = diary_repo / "diary/lessons_learned.md"
    diary.compact(store, path, {"a-lesson-with-a-sub-section": "**A lesson (Oct 3, 2026).** Rule."})
    text = path.read_text()
    assert "Stays inside the lesson." not in text and "## another-lesson-with-detail" in text
    assert "Stays inside the lesson." in store.get_pointer("mem:diary/lessons_learned#a-lesson-with-a-sub-section")[0].document


def test_compact_refuses_unarchived_changed_or_malformed(diary_repo, store):
    path = diary_repo / "diary/architectural_decisions.md"
    with pytest.raises(StoreError, match="not archived"):
        diary.compact(store, path, {"first-decision": "x"})
    diary.ingest(store, diary_repo)
    path.write_text(path.read_text().replace("Body of the first decision.", "Edited since the ingest."))
    with pytest.raises(StoreError, match="differs from the file's"):
        diary.compact(store, path, {"first-decision": "x"})
    diary.ingest(store, diary_repo)
    with pytest.raises(StoreError, match="no full entry"):
        diary.compact(store, path, {"nope": "x"})
    with pytest.raises(StoreError, match="one paragraph"):
        diary.compact(store, path, {"first-decision": "two\n\nparagraphs"})
    with pytest.raises(StoreError, match="one paragraph"):
        diary.compact(store, path, {"first-decision": "carries mem:diary/x itself"})


def test_editing_a_full_entry_updates_it_and_prunes_only_its_own_leftover_chunks(diary_repo, store):
    path = diary_repo / "diary/architectural_decisions.md"
    long_body = "\n\n".join(f"Paragraph {i} " + "word " * 120 for i in range(6))
    path.write_text(DECISIONS.replace("Body of the first decision.", long_body))
    diary.ingest(store, diary_repo)
    n_before = len(store.collection.get(where={"slug": "first-decision"})["ids"])
    path.write_text(DECISIONS)
    result = diary.ingest(store, diary_repo).sources["diary/architectural_decisions"]
    assert result.deleted > 0 and len(store.collection.get(where={"slug": "first-decision"})["ids"]) < n_before
    assert store.collection.get(where={"slug": "second-decision-with-a-long-title-that-is-not-a-slug"})["ids"]


def test_the_store_cannot_be_dropped_while_it_holds_archived_entries(diary_repo, store):
    diary.ingest(store, diary_repo)
    with pytest.raises(StoreError, match="export --out"):
        store.drop()


def test_the_region_holds_a_newest_first_index_and_digests_in_the_same_order(diary_repo, store):
    diary.ingest(store, diary_repo)
    path = diary_repo / "diary/architectural_decisions.md"
    diary.compact(store, path, {"first-decision": "**First (Aug 1, 2026), active.** The rule.",
                                "second-decision-with-a-long-title-that-is-not-a-slug": "**Second (Jul 2, 2026).** Rule two."})
    text = path.read_text()
    index = text.split("**Index**")[1].split("**Digests**")[0]
    digests = text.split("**Digests**")[1]
    assert [l for l in index.splitlines() if l.startswith("- ")] == ["- First (Aug 1, 2026), active", "- Second (Jul 2, 2026)"]
    assert digests.index("**First") < digests.index("**Second")
    # a later, older-dated digest slots into place and the index is rebuilt, not appended
    (diary_repo / "diary/architectural_decisions.md").write_text(text + "\n## third-decision (June 1, 2026)\n\nBody three.\n")
    diary.ingest(store, diary_repo)
    diary.compact(store, path, {"third-decision": "**Third (Jun 1, 2026).** Rule three."})
    text = path.read_text()
    idx = [l for l in text.split("**Index**")[1].split("**Digests**")[0].splitlines() if l.startswith("- ")]
    assert [l.split(",")[0] for l in idx] == ["- First (Aug 1", "- Second (Jul 2", "- Third (Jun 1"] and text.count(diary.REGION_START) == 1
    # compacting nothing only rebuilds the index and leaves the file unchanged
    before = path.read_text()
    diary.compact(store, path, {})
    assert path.read_text() == before


def test_a_digest_without_a_readable_date_sorts_last(diary_repo, store):
    diary.ingest(store, diary_repo)
    path = diary_repo / "diary/architectural_decisions.md"
    diary.compact(store, path, {"first-decision": "**No date here.** Rule.",
                                "second-decision-with-a-long-title-that-is-not-a-slug": "**Second (Jul 2, 2026).** Rule two."})
    idx = [l for l in path.read_text().split("**Index**")[1].split("**Digests**")[0].splitlines() if l.startswith("- ")]
    assert idx == ["- Second (Jul 2, 2026)", "- No date here"]


def test_reindex_changes_the_embedding_and_keeps_every_archived_entry(diary_repo, tmp_path):
    from memstore_testkit import StubEmbedding
    path = tmp_path / "s"
    one = Store(path, embedding_function=StubEmbedding(label="one"))
    diary.ingest(one, diary_repo)
    diary.compact(one, diary_repo / "diary/architectural_decisions.md", {"first-decision": "**First (Aug 1, 2026).** Rule."})
    exact = one.get_pointer("mem:diary/architectural_decisions#first-decision")[0].document
    before = one.collection.count()
    two = Store(path, embedding_function=StubEmbedding(label="two"))
    with pytest.raises(StoreError, match="reindex"):
        two.collection
    from memstore.cli import _embed_text
    assert Store(path, embedding_function=StubEmbedding(label="two")).reindex(embed_text_fn=_embed_text) == before
    again = Store(path, embedding_function=StubEmbedding(label="two"))
    assert again.collection.count() == before and (again.collection.metadata or {})["memstore_embedding"] == "two"
    assert again.get_pointer("mem:diary/architectural_decisions#first-decision")[0].document == exact
    assert again.search("first decision body", n=2)  # searchable under the new embedding


def test_a_failed_reindex_leaves_the_old_collection_untouched(diary_repo, tmp_path):
    from memstore_testkit import StubEmbedding

    class Failing(StubEmbedding):
        def __call__(self, input):
            raise RuntimeError("embedding service down")

    path = tmp_path / "s"
    one = Store(path, embedding_function=StubEmbedding(label="one"))
    diary.ingest(one, diary_repo)
    n = one.collection.count()
    with pytest.raises(RuntimeError, match="down"):
        Store(path, embedding_function=Failing(label="two")).reindex()
    still = Store(path, embedding_function=StubEmbedding(label="one"))
    assert still.collection.count() == n and (still.collection.metadata or {})["memstore_embedding"] == "one"


def test_export_then_import_rebuilds_a_fresh_store_with_the_same_text(diary_repo, tmp_path, ef):
    import json
    src = Store(tmp_path / "a", embedding_function=ef)
    diary.ingest(src, diary_repo)
    out = tmp_path / "dump.jsonl"
    src.export(out)
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    dst = Store(tmp_path / "b", embedding_function=ef)
    assert dst.load_rows(rows, embed_text_fn=None) == len(rows)
    a, b = src.collection.get(include=["documents", "metadatas"]), dst.collection.get(include=["documents", "metadatas"])
    assert sorted(zip(a["ids"], a["documents"])) == sorted(zip(b["ids"], b["documents"]))
    with pytest.raises(StoreError, match="fresh location"):
        Store(tmp_path / "b", embedding_function=ef).load_rows(rows)


def test_opening_with_another_embedding_names_reindex(diary_repo, tmp_path, ef):
    from memstore_testkit import StubEmbedding
    diary.ingest(Store(tmp_path / "s", embedding_function=ef), diary_repo)
    with pytest.raises(StoreError, match="reindex"):
        Store(tmp_path / "s", embedding_function=StubEmbedding(label="other-embedding")).collection
