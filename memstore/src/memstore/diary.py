"""Source adapter and compactor for the diary (`diary/architectural_decisions.md`, `diary/lessons_learned.md`).

An *entry* is one decision or lesson. Ingest stores each entry's exact text once (kind `diary-entry`, embedded from its
heading and opening) plus searchable chunks (kind `diary-chunk`). The store is the archive: ingest never deletes an
entry, so a file can later be compacted without losing anything. `compact` replaces entries in the file with one-line
digests ending in a `mem:` pointer, and refuses unless the store already holds the entry's exact text.

Compacted digests live in a marked region near the top of the file; the parser skips it, so a digest is never mistaken
for an entry. Full entries appended later are archived on the next ingest and compacted in turn.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from memstore.chunking import split_body
from memstore.store import Chunk, IngestReport, StoreError, recoverability

COMPONENT = "diary"
REGION_START = "<!-- memstore:digests:start -->"
REGION_END = "<!-- memstore:digests:end -->"
FILES = {"architectural_decisions": {2}, "lessons_learned": {2}}  # heading levels that start an entry; a deeper heading is a sub-section

_HEADING = re.compile(r"^(#{1,6}) +(.*\S)\s*$")
_FENCE = re.compile(r"^\s*```")
_DATE_PAREN = re.compile(r"\s*\(([^()]*\d{4}[^()]*)\)\s*$")
_MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                       "September", "October", "November", "December"], 1)}
EMBED_CHARS = 600


@dataclass
class Entry:
    heading: str
    level: int
    start: int  # first line (index into the file's lines)
    end: int    # one past the last line
    text: str   # exact text of the entry, without trailing blank lines or its closing `---`
    slug: str = ""
    date: str = ""  # ISO date or year-month when the heading or opening gives one

    @property
    def title(self):
        return clean_heading(self.heading)


@dataclass
class ParsedFile:
    lines: list
    entries: list
    dividers: list = field(default_factory=list)  # (line index, heading) of level-1 headings, which are not entries
    region: tuple = None  # (start, end) line indexes of the digest region markers, inclusive


def clean_heading(heading):
    return _DATE_PAREN.sub("", heading.replace("**", "")).strip()


def make_slug(heading):
    """The author's own kebab slug when the heading is one, else the title cut at a word boundary at 60 characters."""
    title = clean_heading(heading)
    pre = title.split(":")[0].strip()
    if re.fullmatch(r"[a-z0-9][a-z0-9-]{7,}", title):
        return title
    if re.fullmatch(r"[a-z0-9-]{20,}", pre):
        return pre
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().replace("`", "")).strip("-")
    return slug[:60].rsplit("-", 1)[0] if len(slug) > 60 else slug


def entry_date(heading, text):
    m = _DATE_PAREN.search(heading.replace("**", ""))
    if m:
        d = re.match(r"([A-Z][a-z]+)(?: (\d{1,2}))?(?:[-–]\d{1,2})?, (\d{4})", m.group(1)) or re.match(r"([A-Z][a-z]+)() (\d{4})", m.group(1))
        if d and d.group(1) in _MONTHS:
            month, day, year = _MONTHS[d.group(1)], d.group(2), d.group(3)
            return f"{year}-{month:02d}-{int(day):02d}" if day else f"{year}-{month:02d}"
    m = re.search(r"\*\*(\d{4}-\d{2}-\d{2})\.?\*\*", text[:400])
    return m.group(1) if m else ""


def parse(text, levels):
    lines = text.split("\n")
    region = None
    if REGION_START in lines:
        a = lines.index(REGION_START)
        if REGION_END not in lines[a:]:
            raise StoreError("The digest region has a start marker but no end marker; restore the end marker before anything else.")
        region = (a, lines.index(REGION_END, a))
    headings, in_fence = [], False
    for i, line in enumerate(lines):
        if region and region[0] <= i <= region[1]:
            continue
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        m = None if in_fence else _HEADING.match(line)
        if m:
            headings.append((i, len(m.group(1)), m.group(2)))
    entries, dividers, current = [], [], None

    def close(at):
        nonlocal current
        if current is not None:
            current.end = at
            body = lines[current.start:at]
            while body and not body[-1].strip():
                body.pop()
            if body and body[-1].strip() == "---":
                body.pop()
                while body and not body[-1].strip():
                    body.pop()
            current.text = "\n".join(body)
            current.slug = make_slug(current.heading)
            current.date = entry_date(current.heading, current.text)
            entries.append(current)
            current = None

    for i, level, heading in headings:
        if level == 1:
            close(i)
            dividers.append((i, heading))
        elif current is not None and level > current.level:
            continue  # a sub-section of the open entry
        else:
            close(i)
            if level in levels:
                current = Entry(heading, level, i, len(lines), "")
    close(len(lines))
    return ParsedFile(lines, entries, dividers, region)


def check_slugs(entries, stem):
    seen, dupes = {}, []
    for e in entries:
        if e.slug in seen:
            dupes.append(f"{e.slug!r} (lines {seen[e.slug] + 1} and {e.start + 1})")
        seen.setdefault(e.slug, e.start)
    if dupes:
        raise StoreError(f"{stem}: duplicate entry slugs, so pointers would collide: {'; '.join(dupes)}")


def _label(stem, entry):
    return _label_for(stem, entry.title, entry.date)


def _label_for(stem, title, date):
    return f"[diary · {stem} · {title[:90]}" + (f" · {date}" if date else "") + "]"


def embed_text(metadata, document):
    """What a stored `diary-entry` record is embedded from (label plus opening), recomputed for `reindex`."""
    return f"{_label_for(metadata['file'].removesuffix('.md'), metadata['heading'], metadata.get('date', ''))}\n{document[:EMBED_CHARS]}"


def entry_chunks(stem, entry, source_path, recoverable):
    base = {"component": COMPONENT, "file": f"{stem}.md", "heading": entry.title, "slug": entry.slug,
            "pointer": f"mem:diary/{stem}#{entry.slug}", "source_path": source_path, "recoverable": recoverable,
            "entry_chars": len(entry.text)}
    if entry.date:
        base["date"] = entry.date
        base["date_int"] = int(entry.date.replace("-", "").ljust(8, "0")[:8])
    label = _label(stem, entry)
    opening = entry.text[:EMBED_CHARS]
    chunks = [Chunk(f"diary/{stem}#{entry.slug}", entry.text, {**base, "kind": "diary-entry"},
                    embed_text=f"{label}\n{opening}")]
    for part, piece in enumerate(split_body(entry.text)):
        chunks.append(Chunk(f"diary/{stem}#{entry.slug}.{part}", f"{label}\n{piece}", {**base, "kind": "diary-chunk", "part": part}))
    return chunks


def _slug_of(chunk_id):
    return chunk_id.split("#", 1)[1].rsplit(".", 1)[0] if "." in chunk_id.split("#", 1)[1] else chunk_id.split("#", 1)[1]


def resolve(root, path=None):
    folder = Path(path) if path else Path(root) / "diary"
    missing = [f for f in FILES if not (folder / f"{f}.md").is_file()]
    if missing:
        raise FileNotFoundError(f"No diary files {missing} in {folder}")
    return folder


def ingest(store, root, folder=None, dry_run=False):
    """Archive every entry still present in full in the diary files. Never deletes: compacted entries stay in the store."""
    folder, report = resolve(root, folder), IngestReport()
    for stem, levels in FILES.items():
        path = folder / f"{stem}.md"
        parsed = parse(path.read_text(encoding="utf-8"), levels)
        check_slugs(parsed.entries, stem)
        try:
            rel = path.resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            rel = str(path.resolve())
        rec = recoverability(root, path)
        chunks = [c for e in parsed.entries for c in entry_chunks(stem, e, rel, rec)]
        present = {e.slug for e in parsed.entries}
        report.sources[f"diary/{stem}"] = store.sync_source(
            f"diary/{stem}", chunks, dry_run=dry_run, delete_stale=lambda cid: _slug_of(cid) in present)
    return report


# ---------------------------------------------------------------------------------------------------- compaction

def _bullet(stem, slug, text):
    return f"- {text} → `mem:diary/{stem}#{slug}`"


_DIGEST_LINE = re.compile(r"^- .* → `mem:diary/[^`]+`$")
_MON = {m[:3]: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                         "September", "October", "November", "December"], 1)}


def _lead(bullet):
    """The bold opening of a digest bullet: its title, date and status."""
    m = re.match(r"^- \*\*(.+?)\*\*", bullet)
    return m.group(1) if m else bullet[2:80]


def _lead_date(lead):
    m = re.search(r"\b([A-Z][a-z]{2})[a-z]* (\d{1,2})(?:[–-]\d{1,2})?, (\d{4})", lead) or \
        re.search(r"\b([A-Z][a-z]{2})[a-z]* ()(\d{4})", lead)
    if not m or m.group(1) not in _MON:
        return (0, 0, 0)
    return (int(m.group(3)), _MON[m.group(1)], int(m.group(2) or 0))


def _sorted_digests(bullets):
    """Newest first; entries with no readable date last; equal dates keep their order."""
    return [b for _, b in sorted(enumerate(bullets), key=lambda ib: (tuple(-x for x in _lead_date(_lead(ib[1]))), ib[0]))]


def split_region(text):
    """(index lines, digest bullets) of a diary file's region, or ([], []) when it has none."""
    lines = text.split("\n")
    if REGION_START not in lines or REGION_END not in lines[lines.index(REGION_START):]:
        return [], []
    a = lines.index(REGION_START)
    b = lines.index(REGION_END, a)
    inside = lines[a + 1:b]
    digests_at = next((i for i, l in enumerate(inside) if l.startswith("**Digests**")), len(inside))
    index_at = next((i for i, l in enumerate(inside) if l.startswith("**Index**")), 0)
    index = [l for l in inside[index_at:digests_at] if l.startswith("- ")]
    return index, [l for l in inside if _DIGEST_LINE.match(l)]


def region_lines(bullets):
    """The digest region: a one-line-per-entry index, then the digests in the same order."""
    ordered = _sorted_digests(bullets)
    index = [f"- {_lead(b).rstrip('.')}" for b in ordered]
    return [REGION_START, "", "**Index** (newest first; the digests below follow the same order)", "", *index, "",
            "**Digests**", "", *ordered, "", REGION_END, ""]


def compact(store, path, digests, dry_run=False):
    """Replace the named entries in `path` with digests. {slug: digest text}. Returns (bytes before, bytes after, slugs)."""
    path = Path(path)
    stem = path.stem
    original = path.read_text(encoding="utf-8")
    parsed = parse(original, FILES[stem])
    check_slugs(parsed.entries, stem)
    by_slug = {e.slug: e for e in parsed.entries}
    unknown = sorted(set(digests) - set(by_slug))
    if unknown:
        raise StoreError(f"{stem}: no full entry with slug(s) {unknown}; already compacted, or the slug is wrong")
    for slug, text in digests.items():
        if "\n" in text.strip() or "mem:" in text:
            raise StoreError(f"{slug}: a digest is one paragraph and does not carry its own pointer")
        got = store.collection.get(ids=[f"diary/{stem}#{slug}"], include=["documents"])
        if not got["ids"]:
            raise StoreError(f"{slug}: not archived in the store; run `ingest diary` first")
        if got["documents"][0] != by_slug[slug].text:
            raise StoreError(f"{slug}: the store's archived text differs from the file's; run `ingest diary` first and review")
    chosen = sorted((by_slug[s] for s in digests), key=lambda e: e.start)
    lines, drop = parsed.lines, set()
    for e in chosen:
        drop.update(range(e.start, e.end))
    bullets = [_bullet(stem, e.slug, digests[e.slug].strip()) for e in chosen]
    if not parsed.region and not bullets:
        return len(original.encode()), len(original.encode()), []
    if parsed.region:
        a, b = parsed.region
        existing = [l for l in lines[a + 1:b] if _DIGEST_LINE.match(l)]
        before = [l for i, l in enumerate(lines) if i < a and i not in drop]
        after = [l for i, l in enumerate(lines) if i > b and i not in drop]
    else:
        existing = []
        first = min([e.start for e in parsed.entries] + [len(lines)])
        before = [l for i, l in enumerate(lines) if i < first and i not in drop]
        after = [l for i, l in enumerate(lines) if i >= first and i not in drop]
    if before and before[-1].strip():
        before.append("")
    while after and not after[0].strip():
        after = after[1:]
    result = "\n".join(before + region_lines(existing + bullets) + after)
    result = re.sub(r"\n{4,}", "\n\n\n", result).rstrip("\n") + "\n"  # stable under repeated runs
    if not dry_run:
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(result, encoding="utf-8", newline="\n")
        tmp.replace(path)
    return len(original.encode()), len(result.encode()), [e.slug for e in chosen]
