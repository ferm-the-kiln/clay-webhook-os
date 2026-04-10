"""Tests for app/core/context_index.py — TF-IDF semantic index over markdown files."""

import math

import pytest

from app.core.context_index import _STOP_WORDS, ContextIndex, _tokenize

# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = _tokenize("Hello World Example")
        assert "hello" in tokens
        assert "world" in tokens
        assert "example" in tokens

    def test_removes_stop_words(self):
        tokens = _tokenize("the quick brown fox and the lazy dog")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens

    def test_removes_short_tokens(self):
        tokens = _tokenize("I am ok at it")
        # All are <=2 chars or stop words
        assert tokens == []

    def test_lowercases(self):
        tokens = _tokenize("UPPERCASE Words HERE")
        assert all(t == t.lower() for t in tokens)

    def test_splits_on_non_alphanumeric(self):
        tokens = _tokenize("hello-world foo_bar baz.qux")
        assert "hello" in tokens
        assert "world" in tokens
        assert "foo" in tokens
        assert "bar" in tokens
        assert "baz" in tokens
        assert "qux" in tokens

    def test_preserves_numbers(self):
        tokens = _tokenize("revenue 500 million employees 200")
        assert "500" in tokens
        assert "million" in tokens
        assert "200" in tokens
        assert "revenue" in tokens
        assert "employees" in tokens

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_only_stop_words(self):
        assert _tokenize("the and or but is are was") == []

    def test_mixed_content(self):
        tokens = _tokenize("# Sales Framework\n\nUse **BANT** methodology for qualifying leads.")
        assert "sales" in tokens
        assert "framework" in tokens
        assert "bant" in tokens
        assert "methodology" in tokens
        assert "qualifying" in tokens
        assert "leads" in tokens


# ---------------------------------------------------------------------------
# ContextIndex — build
# ---------------------------------------------------------------------------


class TestBuild:
    def test_build_empty_dirs(self, tmp_path):
        idx = ContextIndex(dirs=[tmp_path / "nonexistent"], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 0

    def test_build_indexes_md_files(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        kb.mkdir()
        (kb / "sales.md").write_text("Enterprise sales methodology for SaaS companies")
        (kb / "marketing.md").write_text("Content marketing strategy for B2B companies")

        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 2

    def test_build_skips_non_md_files(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        kb.mkdir()
        (kb / "readme.txt").write_text("This should be ignored")
        (kb / "data.json").write_text('{"key": "value"}')
        (kb / "actual.md").write_text("This should be indexed with content")

        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 1

    def test_build_skips_defaults_dir(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        defaults = kb / "_defaults"
        defaults.mkdir(parents=True)
        (defaults / "default.md").write_text("Default content should be skipped")
        (kb / "normal.md").write_text("Normal content should be indexed here")

        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 1

    def test_build_skips_empty_files(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        kb.mkdir()
        (kb / "empty.md").write_text("")
        (kb / "whitespace.md").write_text("   \n\n  ")  # Only short tokens/stop words
        (kb / "real.md").write_text("Substantial content about enterprise software sales")

        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        # empty and whitespace-only produce no tokens
        assert idx.doc_count == 1

    def test_build_multiple_dirs(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        clients = tmp_path / "clients"
        kb.mkdir()
        clients.mkdir()
        (kb / "framework.md").write_text("Sales framework methodology for qualifying prospects")
        (clients / "acme.md").write_text("Acme Corp is a technology company building AI products")

        idx = ContextIndex(dirs=[kb, clients], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 2

    def test_build_recursive(self, tmp_path):
        kb = tmp_path / "knowledge_base" / "industries"
        kb.mkdir(parents=True)
        (kb / "saas.md").write_text("SaaS companies subscription revenue recurring model")
        parent = tmp_path / "knowledge_base"
        (parent / "general.md").write_text("General knowledge content about business strategy")

        idx = ContextIndex(dirs=[parent], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 2

    def test_build_relative_paths(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        kb.mkdir()
        (kb / "voice.md").write_text("Professional tone and communication style guidelines")
        (kb / "other.md").write_text("Engineering practices for scalable distributed systems")

        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        results = idx.search("professional tone", top_k=1)
        assert len(results) >= 1
        assert results[0][0] == "knowledge_base/voice.md"

    def test_build_clears_previous(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        kb.mkdir()
        (kb / "old.md").write_text("Old content about legacy systems and migration")

        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 1

        # Remove old, add new
        (kb / "old.md").unlink()
        (kb / "new.md").write_text("New content about modern cloud architecture")
        (kb / "other.md").write_text("Unrelated document about sales pipeline management")
        idx.build()
        assert idx.doc_count == 2
        results = idx.search("cloud architecture", top_k=1)
        assert results[0][0] == "knowledge_base/new.md"

    def test_build_idf_computed(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        kb.mkdir()
        (kb / "a.md").write_text("sales pipeline qualification methodology")
        (kb / "b.md").write_text("marketing pipeline content strategy")

        idx = ContextIndex(dirs=[kb], base_dir=tmp_path, force_backend="tfidf")
        idx.build()
        # "pipeline" appears in both docs, IDF = log(2/2) = 0
        assert idx._idf["pipeline"] == 0.0
        # "sales" appears in 1 doc, IDF = log(2/1) = log(2)
        assert idx._idf["sales"] == pytest.approx(math.log(2))

    def test_build_tf_normalized(self, tmp_path):
        kb = tmp_path / "knowledge_base"
        kb.mkdir()
        (kb / "doc.md").write_text("sales sales sales marketing")

        idx = ContextIndex(dirs=[kb], base_dir=tmp_path, force_backend="tfidf")
        idx.build()
        tf = idx._tf["knowledge_base/doc.md"]
        # "sales" appears 3 times in 4-token doc (after filtering)
        assert tf["sales"] == pytest.approx(3 / 4)
        assert tf["marketing"] == pytest.approx(1 / 4)


# ---------------------------------------------------------------------------
# ContextIndex — search
# ---------------------------------------------------------------------------


class TestSearch:
    def _build_index(self, tmp_path, files: dict[str, str]):
        """Helper: create files and build index."""
        kb = tmp_path / "knowledge_base"
        kb.mkdir(exist_ok=True)
        for name, content in files.items():
            (kb / name).write_text(content)
        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        return idx

    def test_basic_search(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "sales.md": "Enterprise sales methodology for qualifying leads and prospects",
            "marketing.md": "Content marketing strategy for generating awareness and leads",
            "engineering.md": "Software engineering practices for building scalable systems",
        })
        results = idx.search("sales methodology")
        assert len(results) > 0
        assert results[0][0] == "knowledge_base/sales.md"

    def test_search_returns_scores(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "doc.md": "Sales pipeline management and optimization strategies",
            "other.md": "Unrelated content about cloud infrastructure deployment",
        })
        results = idx.search("sales pipeline")
        assert len(results) >= 1
        path, score = results[0]
        assert isinstance(score, float)
        assert score > 0

    def test_search_top_k(self, tmp_path):
        idx = self._build_index(tmp_path, {
            f"doc{i}.md": f"Technology document number {i} about software engineering"
            for i in range(10)
        })
        results = idx.search("technology software engineering", top_k=3)
        assert len(results) <= 3

    def test_search_empty_index(self, tmp_path):
        idx = ContextIndex(dirs=[tmp_path / "empty"], base_dir=tmp_path)
        idx.build()
        assert idx.search("anything") == []

    def test_search_empty_query(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "doc.md": "Content about enterprise software sales methodology",
        })
        assert idx.search("") == []

    def test_search_stop_words_only_query(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "doc.md": "Content about enterprise software sales methodology",
        })
        assert idx.search("the and or is") == []

    def test_search_no_match(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "doc.md": "Sales methodology for qualifying leads and prospects",
        })
        results = idx.search("kubernetes containerization docker")
        assert results == []

    def test_search_sorted_by_relevance(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "saas.md": "SaaS subscription revenue recurring revenue model pricing",
            "general.md": "General business knowledge strategy planning overview",
            "saas_deep.md": "SaaS companies subscription model recurring revenue pricing tiers enterprise SaaS",
        })
        results = idx.search("SaaS subscription revenue", top_k=3)
        # saas_deep.md should score higher (more relevant terms)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_default_top_k_is_3(self, tmp_path):
        idx = self._build_index(tmp_path, {
            f"doc{i}.md": f"Sales pipeline qualification document number {i}"
            for i in range(10)
        })
        results = idx.search("sales pipeline qualification")
        assert len(results) <= 3


# ---------------------------------------------------------------------------
# ContextIndex — search_by_data
# ---------------------------------------------------------------------------


class TestSearchByData:
    def _build_index(self, tmp_path, files: dict[str, str]):
        kb = tmp_path / "knowledge_base"
        kb.mkdir(exist_ok=True)
        for name, content in files.items():
            (kb / name).write_text(content)
        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        return idx

    def test_extracts_company_name(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "saas.md": "SaaS technology companies building subscription software",
            "finance.md": "Financial services banking investment portfolio management",
        })
        results = idx.search_by_data({"company_name": "SaaS Technology Corp"})
        assert len(results) > 0
        assert results[0][0] == "knowledge_base/saas.md"

    def test_extracts_industry(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "finance.md": "Financial services banking investment management portfolio",
            "other.md": "Engineering practices for scalable distributed systems",
        })
        results = idx.search_by_data({"industry": "financial services"})
        assert len(results) > 0

    def test_extracts_multiple_fields(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "saas.md": "SaaS engineering software development technology",
            "other.md": "Financial services banking investment management portfolio",
        })
        results = idx.search_by_data({
            "company_name": "Acme",
            "industry": "SaaS",
            "title": "Software Engineer",
        })
        assert len(results) > 0

    def test_empty_data_returns_empty(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "doc.md": "Content about enterprise software systems",
        })
        assert idx.search_by_data({}) == []

    def test_no_relevant_fields_returns_empty(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "doc.md": "Content about enterprise software systems",
        })
        assert idx.search_by_data({"email": "test@test.com", "phone": "123"}) == []

    def test_non_string_fields_skipped(self, tmp_path):
        idx = self._build_index(tmp_path, {
            "doc.md": "Technology company building software products",
            "other.md": "Financial services banking investment management portfolio",
        })
        results = idx.search_by_data({"company_name": 123, "industry": "technology"})
        assert len(results) > 0

    def test_top_k_passed_through(self, tmp_path):
        idx = self._build_index(tmp_path, {
            f"doc{i}.md": f"Technology software engineering document {i}"
            for i in range(10)
        })
        results = idx.search_by_data({"industry": "technology software"}, top_k=2)
        assert len(results) <= 2

    def test_all_query_fields(self, tmp_path):
        """All supported data fields are extracted."""
        idx = self._build_index(tmp_path, {
            "doc.md": "company industry title role department description persona product bio summary",
            "other.md": "completely unrelated content about underwater basket weaving techniques",
        })
        data = {
            "company_name": "company",
            "company": "company",
            "industry": "industry",
            "title": "title",
            "role": "role",
            "department": "department",
            "description": "description",
            "bio": "bio",
            "summary": "summary",
            "company_description": "description",
            "persona": "persona",
            "product": "product",
        }
        results = idx.search_by_data(data)
        assert len(results) > 0


# ---------------------------------------------------------------------------
# ContextIndex — doc_count property
# ---------------------------------------------------------------------------


class TestDocCount:
    def test_doc_count_before_build(self, tmp_path):
        idx = ContextIndex(dirs=[tmp_path], base_dir=tmp_path)
        assert idx.doc_count == 0

    def test_doc_count_after_build(self, tmp_path):
        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "a.md").write_text("Content about enterprise sales methodology")
        (kb / "b.md").write_text("Content about marketing strategy planning")
        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 2

    def test_doc_count_after_rebuild(self, tmp_path):
        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "a.md").write_text("Content about enterprise sales methodology")
        idx = ContextIndex(dirs=[kb], base_dir=tmp_path)
        idx.build()
        assert idx.doc_count == 1
        (kb / "b.md").write_text("Content about marketing strategy planning")
        idx.build()
        assert idx.doc_count == 2


# ---------------------------------------------------------------------------
# _STOP_WORDS coverage
# ---------------------------------------------------------------------------


class TestStopWords:
    def test_stop_words_is_frozenset(self):
        assert isinstance(_STOP_WORDS, frozenset)

    def test_common_words_included(self):
        for word in ("the", "and", "or", "is", "are", "was", "not", "for"):
            assert word in _STOP_WORDS

    def test_pronouns_included(self):
        for word in ("you", "they", "them", "your", "his", "her", "we"):
            assert word in _STOP_WORDS
