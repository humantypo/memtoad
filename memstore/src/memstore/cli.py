"""Command line: `python -m memstore <command>`; run with no arguments for the list."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from memstore import check, diary
from memstore.store import Store, StoreError, git_toplevel, resolve_store_path


def load_sources():
    """The diary, plus any source a project registers under the `memstore.sources` entry-point group: a module with
    `resolve(root, path=None)` (the folder to read, raising FileNotFoundError) and `ingest(store, root, folder,
    dry_run=False)` returning an `IngestReport`. Each chunk such a source writes starts with a one-line label."""
    from importlib.metadata import entry_points
    sources = {"diary": diary}
    for ep in entry_points(group="memstore.sources"):
        if ep.name in sources:
            raise StoreError(f"memstore source '{ep.name}' is registered twice")
        sources[ep.name] = ep.load()
    return sources


def _coerce(text):
    try:
        return json.loads(text)
    except ValueError:
        return text


def _labels(root):
    try:
        return diary.labels(Path(root) / "diary")
    except (FileNotFoundError, StoreError):
        return {}


def describe(m, labels=None):
    if m["component"] == "diary":
        label = (labels or {}).get(m["pointer"])
        flag = f" · NOT IN FORCE: {label}" if label else ""
        return f"diary · {m['file']} · {m.get('date', 'undated')} · {m['heading'][:90]}{flag}"
    return f"{m['component']} · {m['kind']} · {m.get('date', 'undated')}" + (f" · §{m['section']}" if "section" in m else "")


def build_where(args):
    clauses = [] if args.kind else [{"kind": {"$ne": "diary-entry"}}]  # exact entries are fetched with `get`, not searched
    for key, value in (("component", args.component), ("kind", args.kind)):
        if value is not None:
            clauses.append({key: value})
    if args.since:
        clauses.append({"date_int": {"$gte": int(args.since.replace("-", ""))}})
    for item in args.where or []:
        key, sep, value = item.partition("=")
        if not sep:
            raise StoreError(f"--where expects key=value, got '{item}'")
        clauses.append({key: _coerce(value)})
    return None if not clauses else clauses[0] if len(clauses) == 1 else {"$and": clauses}


def cmd_ingest(args, store, root):
    sources = load_sources()
    if args.source not in sources:
        raise StoreError(f"No source '{args.source}'; known: {', '.join(sorted(sources))}")
    source = sources[args.source]
    folder = source.resolve(root, args.path)
    if args.rebuild:
        store.drop()
    report = source.ingest(store, root, folder, dry_run=args.dry_run)
    for source_id, result in report.sources.items():
        print(f"{source_id}: +{result.added} ~{result.updated} retag {result.retagged} ={result.unchanged} -{result.deleted}")
    t = report.totals
    verb = "Would change" if args.dry_run else "Changed"
    print(f"\n{verb}: {t.added} added, {t.updated} updated (re-embedded), {t.retagged} retagged, "
          f"{t.deleted} deleted; {t.unchanged} unchanged, "
          f"across {len(report.sources)} sources. Originals untouched.")
    for problem in report.problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    return 1 if report.problems else 0


def cmd_search(args, store, root):
    hits = store.search(args.query, n=args.n, where=build_where(args))
    labels = _labels(root)  # read from the files at display time: status lives in the markdown, never in the store
    if not hits:
        print("No matches.")
    for rank, hit in enumerate(hits, 1):
        m = hit.metadata
        print(f"{rank}. {hit.distance:.3f}  {m['pointer']}")
        print(f"   {describe(m, labels)}")
        body = hit.document.split("\n", 1)[1] if "\n" in hit.document else hit.document
        print("   " + (body if args.full else body[:240].replace("\n", " ") + ("…" if len(body) > 240 else "")))
    return 0


def cmd_get(args, store, root):
    hits = store.get_pointer(args.pointer)
    m = hits[0].metadata
    print(f"{m['pointer']}   {describe(m, _labels(root))} · {m['recoverable']}\nOriginal: {m['source_path']}\n")
    exact = m["kind"] == "diary-entry"  # every other record starts with a label line
    print("\n".join(h.document if exact else h.document.split("\n", 1)[1] for h in hits))
    return 0


def cmd_export(args, store, root):
    n = store.export(args.out)
    print(f"Wrote {n} chunks to {args.out} (text, no vectors; not for tracking).")
    return 0


def _embed_text(metadata, document):
    return diary.embed_text(metadata, document) if metadata.get("kind") == "diary-entry" else document


def cmd_index(args, store, root):
    """The landscape read for session start: both Indexes, and the full entries that are not yet compacted."""
    folder = Path(root) / "diary"
    chars = 0
    for stem, levels in diary.FILES.items():
        text = (folder / f"{stem}.md").read_text(encoding="utf-8")
        index, bullets = diary.split_region(text)
        full = diary.parse(text, levels).entries
        gone = sum(1 for b in bullets if diary._labelled(b))
        print(f"## {stem}: {len(bullets)} digests ({len(bullets) - gone} in force, {gone} no longer in force; newest first), "
              f"{len(full)} full entries not yet compacted")
        live = diary.index_lines([b for b in bullets if not diary._labelled(b)])
        print("\n".join(live))
        if gone:
            print("No longer in force (superseded or retired):")
            print("\n".join(diary.index_lines([b for b in bullets if diary._labelled(b)])))
        for e in full:
            try:
                label = diary.label_of(e.heading)
            except diary.LabelError:
                label = "MALFORMED LABEL, run check-pointers"
            flag = f" NOT IN FORCE: {label};" if label else ""
            print(f"- [FULL, read in diary/{stem}.md]{flag} {e.title} ({len(e.text):,} chars)")
        chars += sum(len(line) for line in index)
        print()
    tokens = chars // 4
    if args.budget and tokens > args.budget:
        print(f"NOTICE: the Indexes are about {tokens:,} tokens, over the {args.budget:,}-token budget. "
              "Consider a /tidy review pass to label entries that are no longer in force.\n")
    print("Drill down: python -m memstore get mem:diary/<file>#<slug>   |   python -m memstore search \"query\"")
    return 0


def cmd_set_label(args, store, root):
    stem, slug = _pointer_parts(args.pointer)
    label = None if args.clear else (f"superseded by {args.superseded_by}" if args.superseded_by else f"retired {args.retired}")
    folder = Path(root) / "diary"
    new = diary.set_label(folder / f"{stem}.md", slug, label, dry_run=args.dry_run)
    print(f"{'Would label' if args.dry_run else 'Labelled'} {args.pointer}: {new}")
    if args.superseded_by and args.superseded_by not in diary.known_slugs(folder):
        print(f"WARNING: no entry '{args.superseded_by}' in either diary file", file=sys.stderr)
    return 0


def cmd_restore(args, store, root):
    stem, slug = _pointer_parts(args.pointer)
    entry = diary.restore(store, Path(root) / "diary" / f"{stem}.md", slug, dry_run=args.dry_run)
    print(f"{'Would restore' if args.dry_run else 'Restored'} {args.pointer} below the digest region ({len(entry):,} chars). "
          f"Next: `compact {stem} --digests FILE` with a digest for '{slug}' (label it if it is no longer in force).")
    return 0


def _pointer_parts(pointer):
    import re
    m = re.fullmatch(r"mem:diary/([a-z_]+)#([A-Za-z0-9_.-]+)", pointer)
    if not m or m.group(1) not in diary.FILES:
        raise StoreError(f"expected mem:diary/<{'|'.join(sorted(diary.FILES))}>#<slug>, got '{pointer}'")
    return m.groups()


def cmd_check_pointers(args, store, root):
    rep = check.check_diary(store, Path(root) / "diary", provenance=not args.no_provenance)
    if not args.no_docs:
        check.check_docs(store, root, rep)
    for line in rep.errors:
        print(f"ERROR   {line}")
    for line in rep.warnings:
        print(f"WARNING {line}")
    for line in rep.info:
        print(f"info    {line}")
    print(f"\nChecked {rep.checked} digests and pointers: {len(rep.errors)} errors, {len(rep.warnings)} warnings, {len(rep.info)} notes.")
    return 0 if rep.ok else 1


def cmd_reindex(args, store, root):
    n = store.reindex(embed_text_fn=_embed_text)
    print(f"Re-embedded {n} records from their stored text with '{store.ef.name()}'. Source files were not read.")
    return 0


def cmd_import(args, store, root):
    rows = [json.loads(line) for line in open(args.file, encoding="utf-8") if line.strip()]
    n = store.load_rows(rows, embed_text_fn=_embed_text)
    print(f"Imported {n} records from {args.file} into {store.path}.")
    return 0


def cmd_compact(args, store, root):
    digests = json.load(open(args.digests, encoding="utf-8")) if args.digests else {}
    path = Path(root) / "diary" / f"{args.file}.md"
    before, after, slugs = diary.compact(store, path, digests, dry_run=args.dry_run)
    verb = "Would compact" if args.dry_run else "Compacted"
    print(f"{verb} {len(slugs)} entries in {path.name}: {before:,} -> {after:,} bytes ({100 * after // before}%).")
    return 0


def cmd_status(args, store, root):
    import chromadb
    metas = store.all_metadata()
    print(f"Store: {store.path}\nEmbedding: {store.ef.name()}   chromadb {chromadb.__version__}")
    print(f"Chunks: {len(metas)} across {len({m['source_id'] for m in metas})} sources")
    for (component, kind), n in sorted(Counter((m["component"], m["kind"]) for m in metas).items()):
        print(f"  {component:10s} {kind:8s} {n}")
    local = sorted({m["source_path"] for m in metas if m.get("recoverable") == "local-only"})
    if local:
        print(f"\nNot in git ({len(local)} files; the store may be their only copy):")
        for rel in local:
            gone = "" if (Path(root) / rel).exists() else "   MISSING ON DISK: the store is the only copy"
            print(f"  {rel}{gone}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="memstore", description=__doc__)
    parser.add_argument("--store", help="store directory (default: $MEMSTORE_PATH, else <git root>/diary/memstore/chroma)")
    parser.add_argument("--root", help="repository root that source paths are relative to (default: git root of cwd)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="what the store holds, and what is not recoverable from git")

    ing = sub.add_parser("ingest", help="add or refresh a source; idempotent, never touches the originals")
    ing.add_argument("source", help="diary, or a source a project registers (`memstore.sources` entry points)")
    ing.add_argument("--path", help="folder to read instead of the source's default")
    ing.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    ing.add_argument("--rebuild", action="store_true", help="drop the store's collection first (needed after an embedding change)")

    exp = sub.add_parser("export", help="dump every chunk to a JSONL file: a safety copy before a chromadb upgrade")
    exp.add_argument("--out", required=True, help="file to write (outside diary/memstore/)")

    cmp_ = sub.add_parser("compact", help="replace archived diary entries with one-line digests (JSON {slug: text})")
    cmp_.add_argument("file", choices=sorted(diary.FILES))
    cmp_.add_argument("--digests", help="JSON file; omit to only rebuild the index from the digests already in the file")
    cmp_.add_argument("--dry-run", action="store_true")

    idx = sub.add_parser("index", help="print both diary Indexes and list full entries not yet compacted (the session-start read)")
    idx.add_argument("--budget", type=int, default=8000, help="print a notice when the Indexes exceed about this many tokens (0: never)")

    lab = sub.add_parser("set-label", help="mark an entry as no longer in force (or clear that), in the markdown only")
    lab.add_argument("pointer", help="mem:diary/<file>#<slug>")
    which = lab.add_mutually_exclusive_group(required=True)
    which.add_argument("--superseded-by", metavar="SLUG", help="the entry that replaces it (in either file)")
    which.add_argument("--retired", metavar="'Mon YYYY: reason'", help="when and why it stopped applying; no parentheses")
    which.add_argument("--clear", action="store_true", help="back in force")
    lab.add_argument("--dry-run", action="store_true")

    rst = sub.add_parser("restore", help="put an archived entry that lost its digest back into its file as a full entry")
    rst.add_argument("pointer", help="mem:diary/<file>#<slug>")
    rst.add_argument("--dry-run", action="store_true")

    chk = sub.add_parser("check-pointers", help="verify every digest pointer resolves to its exact entry, the Index is current, and digests are well formed")
    chk.add_argument("--no-provenance", action="store_true", help="skip the check that names and numbers in a digest appear in its source entry")
    chk.add_argument("--no-docs", action="store_true", help="skip the scan of every markdown file for mem: pointers")

    sub.add_parser("reindex", help="re-embed every record from its stored text (after an embedding change); keeps archived entries")

    imp = sub.add_parser("import", help="fill a fresh store from an `export` file (after a chromadb change or on a new machine)")
    imp.add_argument("file")

    get = sub.add_parser("get", help="print the exact entry a pointer names (mem:diary/<file>#<slug>)")
    get.add_argument("pointer")

    srch = sub.add_parser("search", help="semantic search, optionally filtered by metadata")
    srch.add_argument("query")
    srch.add_argument("-n", type=int, default=5)
    srch.add_argument("--component")
    srch.add_argument("--kind", help="diary-chunk (the default search), diary-entry, or a registered source's kind")
    srch.add_argument("--since", help="YYYY-MM-DD: entries dated on or after")
    srch.add_argument("--where", action="append", metavar="KEY=VALUE", help="any metadata field, e.g. file=lessons_learned.md")
    srch.add_argument("--full", action="store_true", help="print whole chunks")

    args = parser.parse_args(argv)
    if args.command == "ingest" and args.rebuild and args.dry_run:
        parser.error("--rebuild and --dry-run cannot be combined")
    try:
        root = Path(args.root) if args.root else git_toplevel()
        store = Store(resolve_store_path(args.store), create=args.command in ("ingest", "compact", "import"))
        return {"status": cmd_status, "ingest": cmd_ingest, "search": cmd_search, "get": cmd_get, "export": cmd_export, "compact": cmd_compact,
                "reindex": cmd_reindex, "import": cmd_import, "index": cmd_index, "set-label": cmd_set_label, "restore": cmd_restore,
                "check-pointers": cmd_check_pointers}[args.command](args, store, root)
    except (StoreError, FileNotFoundError) as exc:
        print(f"memstore: {exc}", file=sys.stderr)
        return 2
