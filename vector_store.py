"""Vector search over logged attacker commands ("similar attacks").

Every command is turned into an embedding (Gemini embeddings, or a built-in
offline fallback) and stored in a vector database (ChromaDB, or a small
NumPy index if ChromaDB is not installed). Searching finds earlier commands
that look like a new one.
"""
import json
import math
import os
import re
import zlib

import db
from config import API_KEY, LOG_DIR

EMBED_MODEL = os.getenv("PHANTOMNET_EMBED_MODEL", "gemini-embedding-001")
EMBED_PREF = os.getenv("PHANTOMNET_EMBED", "auto")            # auto | local
BACKEND_PREF = os.getenv("PHANTOMNET_VECTOR_BACKEND", "auto")  # auto | chroma | numpy
STORE_DIR = os.path.join(LOG_DIR, "vector_db")
LOCAL_DIMS = 512
MODES = ("gemini", "local")


# ------------------------------------------------------------- embeddings
def _local_embed(text):
    """Offline embedding: hashed word and character n-gram counts."""
    t = text.lower()
    vec = [0.0] * LOCAL_DIMS
    for word in re.findall(r"[a-z0-9_.:/\-]+", t):
        vec[zlib.crc32(f"w:{word}".encode()) % LOCAL_DIMS] += 2.0
    padded = f"  {t}  "
    for n in (2, 3, 4):
        for i in range(len(padded) - n + 1):
            vec[zlib.crc32(f"c:{padded[i:i + n]}".encode()) % LOCAL_DIMS] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _gemini_embed(texts):
    from google import genai

    client = genai.Client(api_key=API_KEY)
    out = []
    for i in range(0, len(texts), 50):
        resp = client.models.embed_content(model=EMBED_MODEL, contents=texts[i:i + 50])
        out += [list(e.values) for e in resp.embeddings]
    return out


def embed(texts, mode):
    if mode == "gemini":
        return _gemini_embed(texts)
    return [_local_embed(t) for t in texts]


def pick_mode():
    """Use Gemini embeddings if they work, otherwise the offline fallback."""
    if EMBED_PREF == "local":
        return "local"
    try:
        _gemini_embed(["probe"])
        return "gemini"
    except Exception as exc:
        print(f"[Gemini embeddings not available ({type(exc).__name__}); using offline embeddings]")
        return "local"


# ----------------------------------------------------------------- stores
class _NumpyStore:
    backend = "built-in NumPy index"

    def __init__(self, name):
        os.makedirs(STORE_DIR, exist_ok=True)
        self.path = os.path.join(STORE_DIR, f"{name}.json")
        self.data = {"ids": [], "vectors": [], "metas": []}
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)

    def existing(self, ids):
        return set(ids) & set(self.data["ids"])

    def upsert(self, ids, vectors, metas, docs):
        pos = {i: n for n, i in enumerate(self.data["ids"])}
        for i, v, m in zip(ids, vectors, metas):
            if i in pos:
                self.data["vectors"][pos[i]], self.data["metas"][pos[i]] = v, m
            else:
                self.data["ids"].append(i)
                self.data["vectors"].append(v)
                self.data["metas"].append(m)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f)

    def count(self):
        return len(self.data["ids"])

    def query(self, vec, n):
        import numpy as np

        mat = np.array(self.data["vectors"], dtype=float)
        q = np.array(vec, dtype=float)
        sims = (mat @ q) / ((np.linalg.norm(mat, axis=1) * np.linalg.norm(q)) + 1e-12)
        order = np.argsort(-sims)[:n]
        return [(float(sims[i]), self.data["metas"][i]) for i in order]


class _ChromaStore:
    backend = "ChromaDB"

    def __init__(self, name):
        import chromadb

        os.makedirs(STORE_DIR, exist_ok=True)
        client = chromadb.PersistentClient(path=STORE_DIR)
        self.col = client.get_or_create_collection(
            name, metadata={"hnsw:space": "cosine"}
        )

    def existing(self, ids):
        return set(self.col.get(ids=ids)["ids"]) if ids else set()

    def upsert(self, ids, vectors, metas, docs):
        self.col.upsert(ids=ids, embeddings=vectors, metadatas=metas, documents=docs)

    def count(self):
        return self.col.count()

    def query(self, vec, n):
        res = self.col.query(query_embeddings=[vec], n_results=n)
        return [(1.0 - d, m) for d, m in zip(res["distances"][0], res["metadatas"][0])]


def get_store(mode):
    name = f"commands_{mode}"
    if BACKEND_PREF != "numpy":
        try:
            return _ChromaStore(name)
        except Exception as exc:
            if BACKEND_PREF == "chroma":
                raise
            print(f"[ChromaDB not available ({type(exc).__name__}); using built-in index]")
    return _NumpyStore(name)


# ------------------------------------------------------------- public API
def index_events(limit=1000):
    """Embed and store logged commands that are not indexed yet."""
    events = [e for e in db.fetch_logs(limit=limit) if e["command"].strip()]
    mode = pick_mode()
    while True:
        store = get_store(mode)
        ids = [str(e["id"]) for e in events]
        have = store.existing(ids)
        new = [e for e in events if str(e["id"]) not in have]
        if not new:
            return {"mode": mode, "new": 0, "total": store.count(), "backend": store.backend}
        texts = [e["command"] for e in new]
        unique = list(dict.fromkeys(texts))
        try:
            vecs = dict(zip(unique, embed(unique, mode)))
        except Exception as exc:
            if mode == "gemini":
                print(f"[Gemini embeddings failed ({type(exc).__name__}); using offline embeddings]")
                mode = "local"
                continue
            raise
        metas = [
            {
                "event_id": int(e["id"]),
                "session_id": e["session_id"],
                "category": e["category"],
                "severity": e["severity"],
                "timestamp": e["timestamp"],
                "command": e["command"],
            }
            for e in new
        ]
        store.upsert([str(e["id"]) for e in new], [vecs[t] for t in texts], metas, texts)
        return {"mode": mode, "new": len(new), "total": store.count(), "backend": store.backend}


def search_similar(text, k=5, hide_exact=True):
    """Return the k most similar earlier commands (one row per distinct command)."""
    for mode in MODES:
        store = get_store(mode)
        if store.count() == 0:
            continue
        try:
            qvec = embed([text], mode)[0]
        except Exception:
            continue
        hits = store.query(qvec, min(store.count(), k * 10))
        best = {}
        for sim, meta in hits:
            cmd = meta["command"]
            if hide_exact and cmd.strip().lower() == text.strip().lower():
                continue
            if cmd not in best:
                best[cmd] = {
                    "command": cmd,
                    "similarity": round(sim, 3),
                    "category": meta["category"],
                    "severity": meta["severity"],
                    "session_id": meta["session_id"],
                    "timestamp": meta["timestamp"],
                }
        rows = sorted(best.values(), key=lambda r: -r["similarity"])[:k]
        return {"mode": mode, "backend": store.backend, "results": rows}
    return {"mode": None, "backend": None, "results": []}


def status():
    out = {}
    for mode in MODES:
        store = get_store(mode)
        out["backend"] = store.backend
        out[mode] = store.count()
    return out