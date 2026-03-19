"""Tests for synthetic demo CSV data quality and structure."""

import csv
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "data" / "demo" / "synthetic-50.csv"

REQUIRED_COLUMNS = [
    "first_name",
    "last_name",
    "title",
    "company_name",
    "company_domain",
    "company_description",
    "industry",
    "employee_count",
]

# 14 named verticals from the classify skill + Other
KNOWN_VERTICALS = [
    "Media/Entertainment",
    "Cybersecurity",
    "EdTech",
    "AdTech",
    "Sports Tech",
    "SaaS",
    "FinTech",
    "HealthTech",
    "E-Commerce",
    "Real Estate Tech",
    "HR Tech",
    "LegalTech",
    "CleanTech",
    "AgriTech",
    "Other",
]


def _load_rows() -> list[dict]:
    """Load CSV rows via DictReader."""
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestDemoCsvStructure:
    """Validate CSV file existence, shape, and columns."""

    def test_csv_file_exists_and_parseable(self):
        """Test 1: CSV file exists and is parseable."""
        assert CSV_PATH.exists(), f"CSV not found at {CSV_PATH}"
        rows = _load_rows()
        assert len(rows) > 0, "CSV has no data rows"

    def test_csv_has_exactly_50_rows(self):
        """Test 2: CSV has exactly 50 data rows."""
        rows = _load_rows()
        assert len(rows) == 50, f"Expected 50 rows, got {len(rows)}"

    def test_csv_has_required_columns(self):
        """Test 3: CSV has all required columns."""
        rows = _load_rows()
        actual_columns = set(rows[0].keys())
        for col in REQUIRED_COLUMNS:
            assert col in actual_columns, f"Missing required column: {col}"


class TestDemoCsvQualityDistribution:
    """Validate data quality variance across tiers."""

    def test_industry_diversity(self):
        """Test 4: At least 8 of 14 industry verticals represented."""
        rows = _load_rows()
        industries = {
            row["industry"].strip()
            for row in rows
            if row.get("industry", "").strip()
        }
        # Count how many known verticals appear
        matched = industries & set(KNOWN_VERTICALS)
        assert len(matched) >= 8, (
            f"Only {len(matched)} verticals found: {matched}. Need at least 8."
        )

    def test_real_company_domains(self):
        """Test 5: At least 20 rows have real company domains."""
        rows = _load_rows()
        real_domains = [
            row
            for row in rows
            if row.get("company_domain", "").strip()
            and "." in row["company_domain"]
            and "fake" not in row["company_domain"].lower()
            and "example" not in row["company_domain"].lower()
        ]
        assert len(real_domains) >= 20, (
            f"Only {len(real_domains)} rows with real domains. Need at least 20."
        )

    def test_messy_or_missing_titles(self):
        """Test 6: At least 10 rows have messy/abbreviated/missing titles."""
        rows = _load_rows()
        messy_indicators = [
            ".",  # abbreviations like "sr."
            "/",  # compound titles like "cto / co-founder"
            "&",  # compound titles like "cto & co-founder"
            "mgr",
            "mktg",
            "eng",
            "assoc",
            "sr ",
            "sr.",
            "jr ",
            "jr.",
        ]
        messy_count = 0
        for row in rows:
            title = row.get("title", "").strip()
            if not title:
                messy_count += 1
                continue
            title_lower = title.lower()
            if any(ind in title_lower for ind in messy_indicators):
                messy_count += 1
                continue
            # Very short/generic titles
            if len(title) <= 12 and title.lower() in (
                "associate",
                "consultant",
                "analyst",
                "lead",
                "manager",
                "intern",
                "contractor",
            ):
                messy_count += 1

        assert messy_count >= 10, (
            f"Only {messy_count} messy/abbreviated/missing titles. Need at least 10."
        )

    def test_rows_with_missing_fields(self):
        """Test 7: At least 10 rows have missing fields."""
        rows = _load_rows()
        sparse_count = 0
        check_fields = ["company_description", "industry", "company_domain"]
        for row in rows:
            if any(not row.get(f, "").strip() for f in check_fields):
                sparse_count += 1

        assert sparse_count >= 10, (
            f"Only {sparse_count} rows with missing fields. Need at least 10."
        )

    def test_no_duplicate_domains(self):
        """Test 8: No duplicate company_domain values (except empty strings)."""
        rows = _load_rows()
        domains = [
            row["company_domain"].strip()
            for row in rows
            if row.get("company_domain", "").strip()
        ]
        duplicates = [d for d in domains if domains.count(d) > 1]
        assert len(duplicates) == 0, (
            f"Duplicate domains found: {set(duplicates)}"
        )
