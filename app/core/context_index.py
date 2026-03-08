"""Phase 4: Semantic Context Loading — TF-IDF index for knowledge_base and clients.

At startup, indexes all .md files. Exposes search(query, top_k) to find
relevant context files without hardcoded paths in skill frontmatter.

Pure stdlib implementation — no numpy/sklearn required.
"""

import logging
import math
import re
from collections import Counter
from pathlib import Path

logger = logging.getLogger("clay-webhook-os")

# Stop words to filter out common English words
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


class ContextIndex:
    """TF-IDF index over markdown files in knowledge_base/ and clients/."""

    def __init__(self, dirs: list[Path], base_dir: Path):
        self._dirs = dirs
        self._base_dir = base_dir
        # Indexed data
        self._docs: dict[str, list[str]] = {}  # rel_path → tokens
        self._tf: dict[str, Counter] = {}       # rel_path → term frequencies
        self._idf: dict[str, float] = {}        # term → IDF score
        self._doc_count = 0

    def build(self) -> None:
        """Scan directories and build the TF-IDF index."""
        self._docs.clear()
        self._tf.clear()

        for directory in self._dirs:
            if not directory.exists():
                continue
            for md_file in directory.rglob("*.md"):
                # Skip defaults (already auto-loaded)
                if "_defaults" in md_file.parts:
                    continue
                rel_path = str(md_file.relative_to(self._base_dir))
                try:
                    content = md_file.read_text()
                except (OSError, UnicodeDecodeError):
                    continue
                tokens = _tokenize(content)
                if not tokens:
                    continue
                self._docs[rel_path] = tokens
                # Term frequency: normalized by doc length
                counter = Counter(tokens)
                doc_len = len(tokens)
                self._tf[rel_path] = Counter({t: c / doc_len for t, c in counter.items()})

        self._doc_count = len(self._docs)
        if self._doc_count == 0:
            logger.info("[context-index] No documents to index")
            return

        # Build IDF: log(N / df) for each term
        df: Counter = Counter()
        for tokens in self._docs.values():
            unique_terms = set(tokens)
            for term in unique_terms:
                df[term] += 1

        self._idf = {
            term: math.log(self._doc_count / count)
            for term, count in df.items()
        }

        logger.info(
            "[context-index] Indexed %d documents, %d unique terms",
            self._doc_count, len(self._idf),
        )

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Search for documents matching the query.

        Returns list of (rel_path, score) sorted by relevance, descending.
        """
        if not self._docs:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores: dict[str, float] = {}
        for path, tf in self._tf.items():
            score = 0.0
            for token in query_tokens:
                if token in tf:
                    tfidf = tf[token] * self._idf.get(token, 0)
                    score += tfidf
            if score > 0:
                scores[path] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def search_by_data(self, data: dict, top_k: int = 3) -> list[tuple[str, float]]:
        """Build a query from data fields and search the index.

        Extracts relevant text fields from the data payload to form a query.
        """
        query_parts = []
        # Use common enrichment fields for query
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

        query = " ".join(query_parts)
        return self.search(query, top_k)

    @property
    def doc_count(self) -> int:
        return self._doc_count
