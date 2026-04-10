"""Semantic Context Index for knowledge_base/ and clients/.

Primary backend: sqlite-vec + FastEmbed (embedded vector search, CPU-only,
no separate server). Falls back to pure-stdlib TF-IDF if those packages
aren't installed, keeping the same public API (`search`, `search_by_data`,
`doc_count`).

Public API is stable: callers don't need to know which backend is active.
"""

import logging
import math
import re
import sqlite3
import struct
from collections import Counter
from pathlib import Path

logger = logging.getLogger("clay-webhook-os")

# Optional vector-search dependencies. If missing, we transparently fall
# back to the legacy TF-IDF implementation.
try:
    import sqlite_vec  # type: ignore
    from fastembed import TextEmbedding  # type: ignore
    _VECTOR_DEPS_AVAILABLE = True
except ImportError:
    _VECTOR_DEPS_AVAILABLE = False

# Default embedding model — ~33MB, 384-dim, MIT-licensed, strong on retrieval.
_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
_DEFAULT_DIM = 384

# Stop words for TF-IDF fallback.
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "shall",
    "this", "that", "these", "those", "not", "no", "as", "if", "then",
    "than", "so", "up", "out", "about", "into", "through", "during",
    "before", "after", "above", "below", "between", "each", "all", "any",
    "both", "few", "more", "most", "other", "some", "such", "only", "own",
    "same", "too", "very", "just", "also", "how", "what", "which", "who",
    "when", "where", "why", "their", "they", "them", "your", "you", "we",
    "our", "us", "he", "she", "him", "her", "his", "my", "me", "i",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric, filter stop words and short tokens."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in _STOP_WORDS]


def _pack_f32(vec) -> bytes:
    """Serialize a 1-D float32 array/list into sqlite-vec's expected bytes layout."""
    # Works for numpy arrays (via .astype/.tobytes) and plain sequences.
    if hasattr(vec, "astype") and hasattr(vec, "tobytes"):
        return vec.astype("float32").tobytes()
    return struct.pack(f"{len(vec)}f", *vec)


class ContextIndex:
    """Semantic index over markdown files in knowledge_base/ and clients/.

    If sqlite-vec + FastEmbed are installed, uses vector search over
    embeddings persisted to a SQLite file. Otherwise falls back to an
    in-memory TF-IDF index built in :meth:`build`.
    """

    def __init__(
        self,
        dirs: list[Path],
        base_dir: Path,
        db_path: Path | None = None,
        model_name: str = _DEFAULT_MODEL,
        embedding_dim: int = _DEFAULT_DIM,
        force_backend: str | None = None,
    ):
        self._dirs = dirs
        self._base_dir = base_dir
        self._db_path = db_path or (base_dir / "data" / "context_index.db")
        self._model_name = model_name
        self._embedding_dim = embedding_dim

        # Backend selection — may downgrade at build() time if init fails.
        # Pass force_backend="tfidf" to pin the legacy backend (used by tests
        # that exercise TF-IDF internals directly).
        if force_backend == "tfidf":
            self._backend = "tfidf"
        elif force_backend == "vector":
            if not _VECTOR_DEPS_AVAILABLE:
                raise ImportError(
                    "force_backend='vector' requires sqlite-vec + fastembed"
                )
            self._backend = "vector"
        else:
            self._backend = "vector" if _VECTOR_DEPS_AVAILABLE else "tfidf"

        # TF-IDF state
        self._docs: dict[str, list[str]] = {}
        self._tf: dict[str, Counter] = {}
        self._idf: dict[str, float] = {}
        self._doc_count = 0

        # Vector state
        self._conn: sqlite3.Connection | None = None
        self._paths: list[str] = []  # rowid index → rel_path
        self._embedder = None  # type: ignore[assignment]

    # ------------------------------------------------------------------ build

    def build(self) -> None:
        """Scan directories and build the index for the active backend."""
        if self._backend == "vector":
            try:
                self._build_vector()
                return
            except Exception as e:
                logger.warning(
                    "[context-index] Vector build failed (%s) — falling back to TF-IDF",
                    e,
                )
                self._backend = "tfidf"
                # Fall through to TF-IDF build.

        self._build_tfidf()

    def _iter_md_files(self):
        """Yield (rel_path, content) for every indexable markdown file."""
        for directory in self._dirs:
            if not directory.exists():
                continue
            for md_file in directory.rglob("*.md"):
                if "_defaults" in md_file.parts:
                    continue
                rel_path = str(md_file.relative_to(self._base_dir))
                try:
                    content = md_file.read_text()
                except (OSError, UnicodeDecodeError):
                    continue
                if not content.strip():
                    continue
                yield rel_path, content

    def _build_vector(self) -> None:
        """Build the sqlite-vec + FastEmbed index, persisting to disk."""
        assert _VECTOR_DEPS_AVAILABLE, "vector deps should be available here"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Fresh DB each build — file-based KB changes need re-embedding anyway.
        if self._db_path.exists():
            try:
                self._db_path.unlink()
            except OSError:
                pass

        conn = sqlite3.connect(str(self._db_path))
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        conn.execute(
            f"CREATE VIRTUAL TABLE vec_items USING vec0(embedding float[{self._embedding_dim}])"
        )
        conn.execute(
            "CREATE TABLE items (rowid INTEGER PRIMARY KEY, rel_path TEXT NOT NULL)"
        )

        paths: list[str] = []
        texts: list[str] = []
        for rel_path, content in self._iter_md_files():
            # Truncate long docs to the model's effective window (~512 tokens ≈ 2k chars).
            paths.append(rel_path)
            texts.append(content[:4000])

        if not paths:
            conn.commit()
            self._conn = conn
            self._paths = []
            self._doc_count = 0
            logger.info("[context-index] No documents to index (vector backend)")
            return

        logger.info(
            "[context-index] Embedding %d documents with %s...",
            len(paths), self._model_name,
        )
        embedder = TextEmbedding(model_name=self._model_name)
        self._embedder = embedder
        # FastEmbed yields one numpy array per text.
        vectors = list(embedder.embed(texts))

        for idx, (rel_path, vec) in enumerate(zip(paths, vectors)):
            conn.execute(
                "INSERT INTO items(rowid, rel_path) VALUES (?, ?)", (idx, rel_path)
            )
            conn.execute(
                "INSERT INTO vec_items(rowid, embedding) VALUES (?, ?)",
                (idx, _pack_f32(vec)),
            )

        conn.commit()
        self._conn = conn
        self._paths = paths
        self._doc_count = len(paths)
        logger.info(
            "[context-index] Indexed %d documents (vector, %d-dim, %s)",
            self._doc_count, self._embedding_dim, self._model_name,
        )

    def _build_tfidf(self) -> None:
        """Legacy pure-stdlib TF-IDF build."""
        self._docs.clear()
        self._tf.clear()
        self._idf = {}

        for rel_path, content in self._iter_md_files():
            tokens = _tokenize(content)
            if not tokens:
                continue
            self._docs[rel_path] = tokens
            counter = Counter(tokens)
            doc_len = len(tokens)
            self._tf[rel_path] = Counter(
                {t: c / doc_len for t, c in counter.items()}
            )

        self._doc_count = len(self._docs)
        if self._doc_count == 0:
            logger.info("[context-index] No documents to index (tfidf backend)")
            return

        df: Counter = Counter()
        for tokens in self._docs.values():
            for term in set(tokens):
                df[term] += 1
        self._idf = {
            term: math.log(self._doc_count / count) for term, count in df.items()
        }

        # Free raw token lists — only needed during build() for IDF computation.
        self._docs.clear()
        logger.info(
            "[context-index] Indexed %d documents (tfidf, %d unique terms)",
            self._doc_count, len(self._idf),
        )

    # ----------------------------------------------------------------- search

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Search for documents matching the query.

        Returns a list of ``(rel_path, score)`` sorted by relevance descending.
        Higher score = more relevant regardless of backend (vector converts
        cosine distance to similarity for a consistent API).
        """
        if self._doc_count == 0:
            return []
        if self._backend == "vector" and self._conn is not None and self._embedder is not None:
            return self._search_vector(query, top_k)
        return self._search_tfidf(query, top_k)

    def _search_vector(self, query: str, top_k: int) -> list[tuple[str, float]]:
        assert self._conn is not None and self._embedder is not None
        query_text = query.strip()
        if not query_text:
            return []
        try:
            query_vec = next(iter(self._embedder.embed([query_text[:4000]])))
        except Exception as e:
            logger.warning("[context-index] query embed failed: %s — empty result", e)
            return []

        rows = self._conn.execute(
            """
            SELECT items.rel_path, vec_items.distance
            FROM vec_items
            JOIN items ON items.rowid = vec_items.rowid
            WHERE vec_items.embedding MATCH ?
              AND k = ?
            ORDER BY vec_items.distance
            """,
            (_pack_f32(query_vec), top_k),
        ).fetchall()

        # vec0 returns L2 distance for float[] by default; convert to a
        # bounded similarity score so higher = better, matching TF-IDF semantics.
        return [(rel_path, 1.0 / (1.0 + float(dist))) for rel_path, dist in rows]

    def _search_tfidf(self, query: str, top_k: int) -> list[tuple[str, float]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores: dict[str, float] = {}
        for path, tf in self._tf.items():
            score = 0.0
            for token in query_tokens:
                if token in tf:
                    score += tf[token] * self._idf.get(token, 0.0)
            if score > 0:
                scores[path] = score

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def search_by_data(self, data: dict, top_k: int = 3) -> list[tuple[str, float]]:
        """Build a query from common enrichment fields and search the index."""
        query_parts: list[str] = []
        for key in (
            "company_name", "company", "industry", "title", "role",
            "department", "description", "bio", "summary",
            "company_description", "persona", "product",
        ):
            val = data.get(key)
            if val and isinstance(val, str):
                query_parts.append(val)

        if not query_parts:
            return []
        return self.search(" ".join(query_parts), top_k)

    # --------------------------------------------------------------- metadata

    @property
    def doc_count(self) -> int:
        return self._doc_count

    @property
    def backend(self) -> str:
        """Returns 'vector' or 'tfidf' — which backend is actually in use."""
        return self._backend

    def close(self) -> None:
        """Release the SQLite connection (vector backend only)."""
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            self._conn = None
