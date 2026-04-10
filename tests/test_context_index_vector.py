"""Tests for the vector backend of app/core/context_index.py.

These tests only run when sqlite-vec + fastembed are installed. Without
those packages, the module transparently falls back to TF-IDF (covered
by test_context_index.py).
"""

import pytest

from app.core.context_index import _VECTOR_DEPS_AVAILABLE, ContextIndex

pytestmark = pytest.mark.skipif(
    not _VECTOR_DEPS_AVAILABLE,
    reason="sqlite-vec + fastembed not installed (pip install -e '.[vector]')",
)


class TestVectorBackend:
    def _build_index(self, tmp_path, files: dict[str, str]):
        kb = tmp_path / "knowledge_base"
        kb.mkdir(exist_ok=True)
        for name, content in files.items():
            (kb / name).write_text(content)
        idx = ContextIndex(
            dirs=[kb],
            base_dir=tmp_path,
            db_path=tmp_path / "context_index.db",
            force_backend="vector",
        )
        idx.build()
        return idx

    def test_backend_is_vector(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "sales.md": "Enterprise sales methodology for SaaS companies",
        })
        assert idx.backend == "vector"
        assert idx.doc_count == 1

    def test_persists_to_sqlite_file(self, tmp_path):
        db_path = tmp_path / "context_index.db"
        idx = self._build_index(tmp_path, {
            "doc.md": "Content about enterprise software sales",
        })
        assert db_path.exists()
        assert db_path.stat().st_size > 0
        idx.close()

    def test_semantic_match_beats_keyword(self, tmp_path):
        """A true semantic match should find a relevant doc even without
        exact keyword overlap — this is the whole point of vectors."""
        idx = self._build_index(tmp_path, {
            "saas.md": "Software as a Service subscription pricing for B2B customers",
            "hardware.md": "Physical servers and data center infrastructure equipment",
        })
        # Query uses different words than the doc but same meaning.
        results = idx.search("recurring revenue model for enterprise software", top_k=2)
        assert len(results) >= 1
        top_path, _ = results[0]
        assert top_path == "knowledge_base/saas.md"

    def test_search_returns_scores(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "doc.md": "Enterprise sales methodology for qualifying leads",
        })
        results = idx.search("sales methodology")
        assert len(results) == 1
        path, score = results[0]
        assert isinstance(score, float)
        # Our similarity conversion: 1 / (1 + distance) ∈ (0, 1]
        assert 0.0 < score <= 1.0

    def test_empty_index_returns_empty(self, tmp_path):
        kb = tmp_path / "empty"
        kb.mkdir()
        idx = ContextIndex(
            dirs=[kb],
            base_dir=tmp_path,
            db_path=tmp_path / "context_index.db",
            force_backend="vector",
        )
        idx.build()
        assert idx.doc_count == 0
        assert idx.search("anything") == []

    def test_rebuild_overwrites_db(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        kb.mkdir()
        (kb / "a.md").write_text("Content about enterprise sales")
        idx = ContextIndex(
            dirs=[kb],
            base_dir=tmp_path,
            db_path=tmp_path / "context_index.db",
            force_backend="vector",
        )
        idx.build()
        assert idx.doc_count == 1

        (kb / "a.md").unlink()
        (kb / "b.md").write_text("Content about marketing strategy")
        (kb / "c.md").write_text("Content about engineering practices")
        idx.build()
        assert idx.doc_count == 2

    def test_search_by_data(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "finance.md": "Financial services banking investment portfolio management",
            "saas.md": "Software as a Service subscription recurring revenue",
        })
        results = idx.search_by_data({
            "industry": "banking",
            "title": "Investment Advisor",
        })
        assert len(results) > 0
        assert results[0][0] == "knowledge_base/finance.md"

    def test_force_backend_vector_requires_deps(self, tmp_path):
        """Sanity: force_backend='vector' works when deps present (this test suite)."""
        kb = tmp_path / "kb"
        kb.mkdir()
        idx = ContextIndex(
            dirs=[kb],
            base_dir=tmp_path,
            db_path=tmp_path / "ix.db",
            force_backend="vector",
        )
        assert idx.backend == "vector"


class TestPublicAPIStability:
    """Verify the public API matches the TF-IDF backend contract."""

    def test_has_same_public_methods(self, tmp_path):
        idx = ContextIndex(
            dirs=[tmp_path],
            base_dir=tmp_path,
            force_backend="vector",
        )
        assert hasattr(idx, "build")
        assert hasattr(idx, "search")
        assert hasattr(idx, "search_by_data")
        assert hasattr(idx, "doc_count")
        assert hasattr(idx, "backend")
        assert hasattr(idx, "close")
