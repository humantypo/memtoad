"""Consistency checks for the diary and for `mem:` pointers written anywhere in the repository's markdown.

Errors (exit 1): a digest whose pointer does not resolve to the exact archived entry, a pointer naming another file or a
duplicate slug, a malformed digest, a stale Index, unbalanced region markers, a malformed label, an archived entry with
neither a digest nor a full entry in its file (reachable only by luck of search), a `mem:` pointer in a document that does
not resolve. Warnings (reported, exit 0): backticked names or numbers in a digest that its source entry does not contain
(legitimate when the writer verified code locations, so they are to be read, not blindly fixed); a `superseded by` slug
that names no entry in either file. Info: full entries not yet
compacted or archived.
"""
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from memstore import diary
from memstore.store import StoreError

POINTER = re.compile(r"mem:[a-z0-9_-]+/[A-Za-z0-9_./-]+(?:#[A-Za-z0-9_.-]+)?")
_DATE = re.compile(r"[A-Z][a-z]{2,8} \d{1,2}(?:[–-]\d{1,2})?, \d{4}|\d{4}-\d{2}-\d{2}|\b[A-Z][a-z]{2,8} \d{4}\b")


@dataclass
class CheckReport:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    info: list = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self):
        return not self.errors


def _norm(text):
    return re.sub(r"\s+", " ", text).replace(",", "")


def _unsupported(digest, source):
    """Backticked names and numbers in a digest that its source entry does not contain."""
    src = _norm(source)
    body = digest.rsplit(" → `mem:", 1)[0]
    names = [n for n in set(re.findall(r"`([^`]{2,60})`", body)) if _norm(n) not in src]
    plain = _DATE.sub(" ", body.replace("`", " "))
    nums = [n for n in set(re.findall(r"(?<![\w.])\d[\d,]*\.?\d*%?", plain)) if len(n.strip(",.")) >= 3 and _norm(n.strip(",.")) not in src]
    return sorted(names), sorted(nums)


def _check_label(rep, stem, text, slugs_everywhere):
    try:
        label = diary.label_of(text)
    except diary.LabelError as exc:
        rep.errors.append(f"{stem}: {exc}")
        return
    if label and label.startswith("superseded by ") and label.removeprefix("superseded by ") not in slugs_everywhere:
        rep.warnings.append(f"{stem}: '{label}' names no entry in either diary file: {text[:70]}")


def check_diary(store, folder, provenance=True):
    rep = CheckReport()
    try:
        everywhere = diary.known_slugs(folder)
    except (FileNotFoundError, StoreError):
        everywhere = set()
    for stem, levels in diary.FILES.items():
        path = Path(folder) / f"{stem}.md"
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        if (diary.REGION_START in lines) != (diary.REGION_END in lines):
            rep.errors.append(f"{stem}: the digest region has only one of its two markers")
            continue
        parsed = diary.parse(text, levels)
        index, bullets = diary.split_region(text)
        slugs = {}
        for b in bullets:
            rep.checked += 1
            m = re.search(r"→ `(mem:diary/([a-z_]+)#([^`]+))`$", b)
            label = _lead_label(b)
            if not m:
                rep.errors.append(f"{stem}: digest has no trailing pointer: {label}")
                continue
            ptr, ptr_stem, slug = m.groups()
            if ptr_stem != stem:
                rep.errors.append(f"{stem}: pointer names another file ({ptr_stem}): {label}")
            if slug in slugs:
                rep.errors.append(f"{stem}: two digests share the slug '{slug}'")
            slugs[slug] = b
            body = b[2:m.start()].strip()
            if not body.startswith("**") or body.count("**") < 2:
                rep.errors.append(f"{stem}: digest does not open with a bold title: {label}")
            if body.count("`") % 2:
                rep.errors.append(f"{stem}: unbalanced backticks: {label}")
            if "mem:" in body:
                rep.errors.append(f"{stem}: a digest carries a pointer inside its text: {label}")
            _check_label(rep, stem, diary._lead(b), everywhere)
            try:
                hit = store.get_pointer(ptr)
            except StoreError:
                rep.errors.append(f"{stem}: pointer does not resolve: {ptr}")
                continue
            if len(hit) != 1 or hit[0].metadata.get("kind") != "diary-entry":
                rep.errors.append(f"{stem}: pointer does not name one archived entry: {ptr}")
                continue
            if provenance:
                lead = diary._lead(b)
                unlabelled = b.replace(f"**{lead}**", f"**{diary._LABEL_TAIL.sub('', lead.rstrip('.').rstrip(')'))}**", 1)
                names, nums = _unsupported(unlabelled, hit[0].document)  # a label's reason is not from the entry
                if names or nums:
                    rep.warnings.append(f"{stem}: {label[:70]}: not in the source entry: names {names[:5]} numbers {nums[:5]}")
        if index != diary.index_lines(bullets):
            rep.errors.append(f"{stem}: the Index is stale ({len(index)} lines for {len(bullets)} digests); run `compact {stem}`")
        if diary.ordered_digests(bullets) != bullets:
            rep.errors.append(f"{stem}: digests are not in Index order; run `compact {stem}`")
        present = set(slugs) | {e.slug for e in parsed.entries}
        if store.exists:
            rows = store.collection.get(where={"$and": [{"kind": "diary-entry"}, {"file": f"{stem}.md"}]}, include=["metadatas"])
            for meta in rows["metadatas"]:
                if meta["slug"] not in present:
                    rep.errors.append(f"{stem}: archived entry '{meta['slug']}' has neither a digest nor a full entry in the "
                                      f"file, so only a lucky search reaches it (renamed or deleted after ingest?). Fix: "
                                      f"`restore {meta['pointer']}`, then `compact {stem}` it with a digest labelled "
                                      f"`superseded by <new-slug>` (a rename) or `retired <Mon YYYY>: <why>`")
        for e in parsed.entries:
            _check_label(rep, stem, e.heading, everywhere)
            archived = store.collection.get(ids=[f"diary/{stem}#{e.slug}"], include=["documents"])
            state = "archived" if archived["ids"] and archived["documents"][0] == e.text else "NOT archived (or changed): run `ingest diary`"
            rep.info.append(f"{stem}: full entry '{e.slug}' ({len(e.text):,} chars) not yet compacted, {state}")
    return rep


def _lead_label(bullet):
    return diary._lead(bullet)[:80]


def check_docs(store, root, rep=None):
    """Every `mem:` pointer written in the repository's markdown must resolve."""
    rep = rep or CheckReport()
    root = Path(root)
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "*.md"], cwd=root, capture_output=True, text=True)
    seen = set()
    for rel in sorted(out.stdout.split()):
        for ptr in POINTER.findall((root / rel).read_text(encoding="utf-8", errors="replace")):
            ptr = ptr.rstrip(".")
            if ptr.endswith("/") or (rel, ptr) in seen:
                continue
            seen.add((rel, ptr))
            rep.checked += 1
            try:
                store.get_pointer(ptr)
            except StoreError:
                rep.errors.append(f"{rel}: pointer does not resolve: {ptr}")
    return rep
