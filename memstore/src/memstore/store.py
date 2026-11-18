"""The chroma-backed store: open, sync a source's chunks idempotently, search, report status.

chromadb is imported only here and only when a store is opened, so nothing else needs it installed.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

COLLECTION = "memstore"
STORE_ENV = "MEMSTORE_PATH"
DEFAULT_STORE = Path("diary") / "memstore" / "chroma"  # tracked in git: the diary's long-form half


class StoreError(RuntimeError):
    pass


@dataclass
class Chunk:
    id: str
    document: str
    metadata: dict
    embed_text: str = None  # what is embedded when that is not the document itself (a long verbatim entry)

    def doc_hash(self):
        """Hash of the text alone: a change to it means the chunk must be embedded again."""
        return hashlib.sha256(self.document.encode("utf-8")).hexdigest()

    def fingerprint(self):
        """Hash of everything stored: a change to the text or to any metadata field makes the chunk update."""
        payload = json.dumps([self.document, self.metadata], sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class SyncResult:
    added: int = 0
    updated: int = 0  # text changed, embedded again
    retagged: int = 0  # only metadata changed, stored vector reused
    unchanged: int = 0
    deleted: int = 0

    def __iadd__(self, other):
        self.added += other.added
        self.updated += other.updated
        self.retagged += other.retagged
        self.unchanged += other.unchanged
        self.deleted += other.deleted
        return self


@dataclass
class IngestReport:
    """What one `ingest` of a source did: a SyncResult per source id, and the problems that were skipped."""
    sources: dict = field(default_factory=dict)  # source id -> SyncResult
    problems: list = field(default_factory=list)  # human-readable, one per skipped or incomplete thing

    @property
    def totals(self):
        total = SyncResult()
        for result in self.sources.values():
            total += result
        return total


def recoverability(root, path):
    """"git" when the file is tracked (recover with `git show <sha>:<path>`), else "local-only"."""
    done = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=root, capture_output=True)
    return "git" if done.returncode == 0 else "local-only"


@dataclass
class Hit:
    id: str
    distance: float
    document: str
    metadata: dict = field(default_factory=dict)


def git_toplevel(cwd=None):
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise StoreError("Not inside a git repository, so there is no default store location; pass --store or set "
                         f"{STORE_ENV}.") from exc
    return Path(out.stdout.strip())


def resolve_store_path(explicit=None, cwd=None):
    """--store, then $MEMSTORE_PATH, then <git toplevel of cwd>/diary/memstore/chroma."""
    chosen = explicit or os.environ.get(STORE_ENV)
    return Path(chosen).expanduser() if chosen else git_toplevel(cwd) / DEFAULT_STORE


def chromadb_version():
    import chromadb
    return chromadb.__version__


# ---------------------------------------------------------------------------------------------------- format compatibility
#
# chromadb migrates a store's on-disk format when it opens it, one way, and records each step in the `migrations` table of
# `chroma.sqlite3`. A store is tracked in git and shared, so a teammate whose chromadb migrates it would lock out everyone
# on an older version. The version string is a poor proxy (most releases change nothing on disk), so compatibility is
# decided from the migrations themselves, read with sqlite3 *before* chromadb touches the store.

_KNOWN = None


def store_migrations(path):
    """{(dir, version)} of the format migrations applied to the store at `path`; empty when there is none."""
    db = Path(path) / "chroma.sqlite3"
    if not db.is_file():
        return set()
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            return {(d, int(v)) for d, v in con.execute("SELECT dir, version FROM migrations")}
        finally:
            con.close()
    except sqlite3.DatabaseError as exc:  # locked, corrupt, or not a chroma store: say so, never guess a format
        raise StoreError(f"Cannot read the format of the store at {path} ({db.name}: {exc}).") from exc


def recorded_chromadb(path):
    """The chromadb version recorded when the store's collection was created, or None."""
    db = Path(path) / "chroma.sqlite3"
    if not db.is_file():
        return None
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = con.execute("SELECT m.str_value FROM collection_metadata m JOIN collections c ON c.id = m.collection_id "
                          "WHERE c.name = ? AND m.key = 'memstore_chromadb'", (COLLECTION,)).fetchone()
        return row[0] if row else None
    except sqlite3.DatabaseError:
        return None
    finally:
        con.close()


def _cache_file():
    base = Path(os.environ.get("MEMSTORE_CACHE") or Path.home() / ".cache" / "memstore")
    return base / f"known-migrations-chromadb-{chromadb_version()}.json"


def known_migrations():
    """The format migrations the installed chromadb applies: those of a fresh, empty store it creates in a temp dir.
    Fixed per chromadb version, so cached on disk per version (best effort: a bad cache only costs the probe again)."""
    global _KNOWN
    if _KNOWN is None:
        cache = _cache_file()
        try:
            _KNOWN = {(d, int(v)) for d, v in json.loads(cache.read_text())}
        except (OSError, ValueError, TypeError):
            import chromadb
            from chromadb.config import Settings
            tmp = tempfile.mkdtemp(prefix="memstore-probe-")
            try:
                chromadb.PersistentClient(path=tmp, settings=Settings(anonymized_telemetry=False))
                _KNOWN = store_migrations(tmp)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            if not _KNOWN:
                _KNOWN = None
                raise StoreError(f"chromadb {chromadb_version()} records no format migrations where memstore looks for "
                                 "them, so store compatibility cannot be decided; memstore needs updating for it.")
            if _KNOWN:
                try:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text(json.dumps(sorted(_KNOWN)))
                except OSError:
                    pass
    return _KNOWN


def _names_of(migrations):
    return ", ".join(f"{d} {v}" for d, v in sorted(migrations))


def read_probe(path):
    """Open a throwaway copy of the store with the installed chromadb and read from it; raises on any failure."""
    import chromadb
    from chromadb.config import Settings
    tmp = Path(tempfile.mkdtemp(prefix="memstore-probe-"))
    try:
        shutil.copytree(path, tmp / "store")
        client = chromadb.PersistentClient(path=str(tmp / "store"), settings=Settings(anonymized_telemetry=False))
        if COLLECTION in [c if isinstance(c, str) else c.name for c in client.list_collections()]:
            col = client.get_collection(COLLECTION, embedding_function=None)
            if col.count():
                col.get(limit=1, include=["documents", "metadatas"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def compatibility(path):
    """("same" | "migrate" | "newer", detail) for the store at `path` and the installed chromadb, without opening it."""
    applied, known = store_migrations(path), known_migrations()
    if applied - known:
        return "newer", _names_of(applied - known)
    if known - applied:
        return "migrate", _names_of(known - applied)
    return "same", ""


def check_format(path, allow_upgrade=False):
    """Refuse, before chromadb opens the real store, any open that would migrate it or that it cannot read."""
    state, detail = compatibility(path)
    built_with = recorded_chromadb(path) or "an unknown version"
    if state == "newer":
        raise StoreError(f"The store at {path} uses format migrations ({detail}) that chromadb {chromadb_version()} does "
                         f"not know; it was last migrated by a newer chromadb (created with {built_with}). Upgrade "
                         "chromadb to the version the project's requirements name.")
    if state == "migrate" and not allow_upgrade:
        raise StoreError(f"chromadb {chromadb_version()} would migrate the store at {path} to a newer format ({detail}), "
                         "one way: teammates on the older chromadb could no longer read it once it is committed. "
                         "Nothing was changed. Either install the chromadb the project's requirements name, or run "
                         "`upgrade-store` and raise the project's chromadb floor in the same commit.")
    if state == "same" and recorded_chromadb(path) not in (None, chromadb_version()):
        try:
            read_probe(path)  # same format; still prove this version can read it before touching the real store
        except Exception as exc:
            raise StoreError(f"chromadb {chromadb_version()} cannot read the store at {path} (created with {built_with}), "
                             f"although its format migrations match: {exc}. Install the chromadb the project's "
                             "requirements name.") from exc
    return state


def default_embedding_function():
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    return ONNXMiniLM_L6_V2()


class Store:
    """One chroma collection. `embedding_function` is injectable so tests need no model download."""

    def __init__(self, path, embedding_function=None, create=True, allow_upgrade=False):
        self.path = Path(path)
        self._ef = embedding_function
        self._create = create
        self._allow_upgrade = allow_upgrade  # only `upgrade-store` lets the installed chromadb migrate the format
        self._checked = False
        self._collection = None

    @property
    def exists(self):
        return self.path.is_dir() and any(self.path.iterdir())

    @property
    def ef(self):
        if self._ef is None:
            self._ef = default_embedding_function()
        return self._ef

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._open()
        return self._collection

    def _client(self):
        import chromadb
        from chromadb.config import Settings
        if not self._checked and (self.path / "chroma.sqlite3").is_file():
            check_format(self.path, self._allow_upgrade)  # before chromadb opens it: opening is what migrates
            self._checked = True
        return chromadb.PersistentClient(path=str(self.path), settings=Settings(anonymized_telemetry=False))

    @staticmethod
    def _names(client):
        return [c if isinstance(c, str) else c.name for c in client.list_collections()]

    def _open(self):
        if not self._create and not self.exists:
            raise StoreError(f"No store at {self.path}; run `ingest` first.")
        client = self._client()
        if COLLECTION in self._names(client):
            try:
                col = client.get_collection(COLLECTION, embedding_function=self.ef)
            except ValueError as exc:  # chromadb itself refuses an embedding other than the one the collection records
                if "embedding function" not in str(exc).lower():
                    raise
                raise StoreError(f"The store at {self.path} was built with another embedding than '{self.ef.name()}'. "
                                 "Re-embed it from its stored text: `reindex`.") from exc
            meta = col.metadata or {}
            recorded = meta.get("memstore_embedding")
            if recorded != self.ef.name():
                raise StoreError(f"The store at {self.path} was built with embedding '{recorded}', not '{self.ef.name()}'. "
                                 "Re-embed it from its stored text: `reindex`.")
            return col
        return client.create_collection(COLLECTION, embedding_function=self.ef,
                                        metadata={"hnsw:space": "cosine", "memstore_embedding": self.ef.name(),
                                                 "memstore_chromadb": chromadb_version()})

    def drop(self):
        """Delete the collection (the files it was derived from are untouched). Refused while the store holds archived diary
        entries: once a diary file is compacted, the store is the only place their full text is kept."""
        if self.exists:
            client = self._client()
            if COLLECTION in self._names(client):
                archived = client.get_collection(COLLECTION, embedding_function=self.ef).get(
                    where={"kind": "diary-entry"}, limit=1)["ids"]
                if archived:
                    raise StoreError("The store holds archived diary entries that may exist nowhere else in full, so it is "
                                     "not rebuilt from the source files. To change the embedding use `reindex` (re-embeds "
                                     "from the stored text); to move to another chromadb version use `export --out FILE` "
                                     "then `import FILE`.")
                client.delete_collection(COLLECTION)
        self._collection = None

    def stored_state(self, source_id):
        """{chunk id: (doc_hash, fingerprint)} for one source; empty when there is no store yet."""
        if not self.exists:
            return {}
        got = self.collection.get(where={"source_id": source_id}, include=["metadatas"])
        return {i: (m["doc_hash"], m["fingerprint"]) for i, m in zip(got["ids"], got["metadatas"])}

    def plan(self, source_id, chunks, delete_stale=True):
        """What a sync would do: (ids to embed, ids to retag, ids to delete, SyncResult), changing nothing.
        delete_stale: True deletes every stored chunk of the source that is no longer produced; False deletes none; a
        function of the chunk id deletes only those it accepts (an entry's own leftover chunks, never a whole entry)."""
        stored = self.stored_state(source_id)
        new = {c.id: c for c in chunks}
        result = SyncResult()
        embed, retag = [], []
        for cid, chunk in new.items():
            if cid not in stored:
                result.added += 1
                embed.append(cid)
            elif stored[cid][0] != chunk.doc_hash():
                result.updated += 1
                embed.append(cid)
            elif stored[cid][1] != chunk.fingerprint():
                result.retagged += 1
                retag.append(cid)
            else:
                result.unchanged += 1
        stale = [cid for cid in stored if cid not in new and (delete_stale(cid) if callable(delete_stale) else delete_stale)]
        result.deleted = len(stale)
        return embed, retag, stale, result

    def sync_source(self, source_id, chunks, dry_run=False, delete_stale=True):
        """Make the store's chunks for source_id equal `chunks`: upsert the new and changed, delete the vanished."""
        ids = [c.id for c in chunks]
        if len(set(ids)) != len(ids):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise StoreError(f"Duplicate chunk ids for {source_id}: {dupes}")
        embed, retag, stale, result = self.plan(source_id, chunks, delete_stale)
        if dry_run:
            return result
        by_id = {c.id: c for c in chunks}

        def stored_metadata(chunk):
            return {**chunk.metadata, "source_id": source_id, "doc_hash": chunk.doc_hash(),
                    "fingerprint": chunk.fingerprint()}

        if embed:
            batch = [by_id[i] for i in embed]
            self.collection.upsert(ids=embed, documents=[c.document for c in batch],
                                   embeddings=self.ef([c.embed_text or c.document for c in batch]),
                                   metadatas=[stored_metadata(c) for c in batch])
        if retag:
            batch = [by_id[i] for i in retag]
            vectors = self.collection.get(ids=retag, include=["embeddings"])
            by_vector = dict(zip(vectors["ids"], vectors["embeddings"]))
            self.collection.upsert(ids=retag, documents=[c.document for c in batch],
                                   embeddings=[by_vector[i] for i in retag],
                                   metadatas=[stored_metadata(c) for c in batch])
        if stale:
            self.collection.delete(ids=stale)
        return result

    def search(self, query, n=5, where=None):
        if not self.exists:
            raise StoreError(f"No store at {self.path}; run `ingest` first.")
        res = self.collection.query(query_embeddings=self.ef([query]), n_results=n, where=where or None,
                                    include=["documents", "metadatas", "distances"])
        return [Hit(i, d, doc, m) for i, d, doc, m in zip(res["ids"][0], res["distances"][0], res["documents"][0],
                                                          res["metadatas"][0])]

    def get_pointer(self, pointer):
        """Records a pointer names, in reading order; for a diary entry, its exact archived text only."""
        if not self.exists:
            raise StoreError(f"No store at {self.path}; run `ingest` first.")
        pointer = pointer if pointer.startswith("mem:") else f"mem:{pointer}"
        got = self.collection.get(where={"pointer": pointer}, include=["documents", "metadatas"])
        if got["ids"]:
            if any(m["kind"] == "diary-entry" for m in got["metadatas"]):  # the exact entry, not its search chunks
                keep = [i for i, m in enumerate(got["metadatas"]) if m["kind"] == "diary-entry"]
                got = {k: [got[k][i] for i in keep] for k in ("ids", "metadatas", "documents")}
            rows = sorted(zip(got["metadatas"], got["documents"]), key=lambda r: r[0].get("part", 0))
            return [Hit(m["pointer"], 0.0, d, m) for m, d in rows]
        raise StoreError(f"No chunk has pointer {pointer}. Pointers are printed by `search`; if a section was renamed in "
                         "the source, re-run `ingest`.")

    def export(self, out):
        """Write every chunk (id, text, metadata; no vectors) to a JSONL file, sorted by id. A safety copy before a
        chromadb upgrade, not a tracked artefact."""
        if not self.exists:
            raise StoreError(f"No store at {self.path}; run `ingest` first.")
        got = self.collection.get(include=["documents", "metadatas"])
        rows = sorted(zip(got["ids"], got["documents"], got["metadatas"]))
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            for cid, doc, meta in rows:
                fh.write(json.dumps({"id": cid, "document": doc, "metadata": meta}, ensure_ascii=False, sort_keys=True) + "\n")
        return len(rows)

    def reindex(self, embed_text_fn=None, batch=200):
        """Re-embed every stored record from its stored text with the current embedding function. Never reads the source
        files, so archived diary entries survive. A new collection is built beside the old one and swapped in only when
        the copy is complete; a failure leaves the old collection as it was."""
        if not self.exists:
            raise StoreError(f"No store at {self.path}; run `ingest` first.")
        client = self._client()
        names = self._names(client)
        if COLLECTION not in names and "memstore_old" in names:  # an earlier swap was interrupted: put the old one back
            client.get_collection("memstore_old", embedding_function=None).modify(name=COLLECTION)
            names = self._names(client)
        if COLLECTION not in names:
            raise StoreError(f"The store at {self.path} has no '{COLLECTION}' collection.")
        old = client.get_collection(COLLECTION, embedding_function=None)  # format compatibility was checked in _client
        for leftover in ("memstore_new", "memstore_old"):
            if leftover in names:
                client.delete_collection(leftover)
        rows = old.get(include=["documents", "metadatas"])
        ids, docs, metas = rows["ids"], rows["documents"], rows["metadatas"]
        new = client.create_collection("memstore_new", embedding_function=self.ef, metadata={
            "hnsw:space": "cosine", "memstore_embedding": self.ef.name(), "memstore_chromadb": chromadb_version()})
        try:
            self._copy_in(new, ids, docs, metas, embed_text_fn, batch)
            if new.count() != len(ids):
                raise StoreError(f"Re-embedding wrote {new.count()} of {len(ids)} records; the old collection is untouched.")
        except Exception:
            client.delete_collection("memstore_new")
            raise
        old.modify(name="memstore_old")
        new.modify(name=COLLECTION)
        client.delete_collection("memstore_old")
        self._collection = None
        return len(ids)

    def load_rows(self, rows, embed_text_fn=None, batch=200):
        """Fill a store that has no data yet from `export` rows [{id, document, metadata}], embedding with the current
        function. For a move to another chromadb version or a second machine."""
        if self.exists and COLLECTION in self._names(self._client()):
            raise StoreError(f"The store at {self.path} already exists; import needs a fresh location.")
        col = self.collection  # creates it
        self._copy_in(col, [r["id"] for r in rows], [r["document"] for r in rows], [r["metadata"] for r in rows],
                      embed_text_fn, batch)
        return len(rows)

    def _copy_in(self, col, ids, docs, metas, embed_text_fn, batch):
        for i in range(0, len(ids), batch):
            d, m = docs[i:i + batch], metas[i:i + batch]
            texts = [embed_text_fn(mm, dd) if embed_text_fn else dd for mm, dd in zip(m, d)]
            col.upsert(ids=ids[i:i + batch], documents=d, embeddings=self.ef(texts), metadatas=m)

    def all_metadata(self):
        if not self.exists:
            raise StoreError(f"No store at {self.path}; run `ingest` first.")
        return self.collection.get(include=["metadatas"])["metadatas"]
