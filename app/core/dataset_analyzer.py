import json
import logging
import statistics
from collections import Counter

logger = logging.getLogger("clay-webhook-os")

# Analysis types
ANALYSIS_TYPES = {"icp", "win-loss", "churn", "usage", "sequence-performance", "expansion"}

ANALYSIS_LABELS = {
    "icp": "ICP Pattern Detection",
    "win-loss": "Win/Loss Analysis",
    "churn": "Churn Pattern Identification",
    "usage": "Feature Adoption Analysis",
    "sequence-performance": "Sequence Performance Analysis",
    "expansion": "Expansion Trigger Identification",
}


class DatasetAnalyzer:
    """Pre-processes dataset rows in Python, then builds a prompt for claude."""

    def preprocess(self, rows: list[dict], analysis_type: str, outcome_column: str | None = None, segment_columns: list[str] | None = None) -> dict:
        """Compute Python-side stats across all rows."""
        if not rows:
            return {"row_count": 0, "columns": {}, "sample_rows": [], "cross_tabs": {}}

        # Detect columns and types
        all_keys = set()
        for row in rows:
            all_keys.update(k for k in row.keys() if not k.startswith("_"))

        columns: dict[str, dict] = {}
        for key in sorted(all_keys):
            values = [row.get(key) for row in rows if row.get(key) is not None and str(row.get(key)).strip() != ""]
            if not values:
                columns[key] = {"type": "empty", "non_null": 0, "missing_rate": 1.0}
                continue

            # Try numeric
            numeric_vals = []
            for v in values:
                try:
                    numeric_vals.append(float(v))
                except (ValueError, TypeError):
                    break

            if len(numeric_vals) == len(values) and numeric_vals:
                columns[key] = {
                    "type": "numeric",
                    "non_null": len(values),
                    "missing_rate": round(1 - len(values) / len(rows), 3),
                    "min": round(min(numeric_vals), 2),
                    "max": round(max(numeric_vals), 2),
                    "mean": round(statistics.mean(numeric_vals), 2),
                    "median": round(statistics.median(numeric_vals), 2),
                }
                if len(numeric_vals) > 1:
                    columns[key]["stdev"] = round(statistics.stdev(numeric_vals), 2)
            else:
                # Categorical
                str_values = [str(v) for v in values]
                counter = Counter(str_values)
                top_values = counter.most_common(15)
                columns[key] = {
                    "type": "categorical",
                    "non_null": len(values),
                    "missing_rate": round(1 - len(values) / len(rows), 3),
                    "unique_count": len(counter),
                    "top_values": {k: v for k, v in top_values},
                }

        # Cross-tabulations (outcome vs segment columns)
        cross_tabs: dict[str, dict] = {}
        if outcome_column and outcome_column in all_keys:
            seg_cols = segment_columns or []
            # Auto-detect good segment columns if none specified
            if not seg_cols:
                for key, info in columns.items():
                    if key == outcome_column:
                        continue
                    if info.get("type") == "categorical" and 2 <= info.get("unique_count", 0) <= 20:
                        seg_cols.append(key)
                    if len(seg_cols) >= 6:
                        break

            for seg_col in seg_cols:
                tab: dict[str, dict] = {}
                for row in rows:
                    outcome = str(row.get(outcome_column, "")).strip()
                    segment = str(row.get(seg_col, "")).strip()
                    if not outcome or not segment:
                        continue
                    if segment not in tab:
                        tab[segment] = {}
                    tab[segment][outcome] = tab[segment].get(outcome, 0) + 1
                if tab:
                    cross_tabs[f"{seg_col} × {outcome_column}"] = tab

        # Sample rows (stratified by outcome if available)
        sample_rows = self._stratified_sample(rows, outcome_column, max_rows=30)

        return {
            "row_count": len(rows),
            "columns": columns,
            "sample_rows": sample_rows,
            "cross_tabs": cross_tabs,
        }

    def _stratified_sample(self, rows: list[dict], outcome_column: str | None, max_rows: int = 30) -> list[dict]:
        """Pick representative sample rows, stratified by outcome."""
        if len(rows) <= max_rows:
            return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]

        if outcome_column:
            groups: dict[str, list[dict]] = {}
            for row in rows:
                key = str(row.get(outcome_column, "unknown"))
                groups.setdefault(key, []).append(row)

            sample = []
            per_group = max(1, max_rows // max(len(groups), 1))
            for group_rows in groups.values():
                step = max(1, len(group_rows) // per_group)
                for i in range(0, len(group_rows), step):
                    if len(sample) >= max_rows:
                        break
                    sample.append(group_rows[i])
            return [{k: v for k, v in r.items() if not k.startswith("_")} for r in sample[:max_rows]]

        # Uniform sampling
        step = max(1, len(rows) // max_rows)
        sample = [rows[i] for i in range(0, len(rows), step)]
        return [{k: v for k, v in r.items() if not k.startswith("_")} for r in sample[:max_rows]]

    def build_analysis_prompt(self, preprocessed: dict, analysis_type: str, business_context: str = "") -> str:
        """Compose the prompt for claude --print."""
        label = ANALYSIS_LABELS.get(analysis_type, analysis_type)

        prompt_parts = [
            f"# First-Party Data Analysis: {label}\n",
            "You are an expert data analyst specializing in B2B sales and marketing analytics.",
            "Analyze the following dataset summary and sample rows to identify actionable patterns.\n",
        ]

        if business_context:
            prompt_parts.append(f"## Business Context\n{business_context}\n")

        # Dataset overview
        prompt_parts.append(f"## Dataset Overview\n- Total rows: {preprocessed['row_count']}")
        prompt_parts.append(f"- Columns: {len(preprocessed['columns'])}\n")

        # Column summaries
        prompt_parts.append("## Column Distributions\n")
        for col_name, info in preprocessed["columns"].items():
            if info["type"] == "empty":
                continue
            prompt_parts.append(f"### {col_name}")
            prompt_parts.append(f"- Type: {info['type']}, Non-null: {info['non_null']}, Missing: {info['missing_rate']:.1%}")
            if info["type"] == "numeric":
                prompt_parts.append(f"- Range: {info['min']} — {info['max']}, Mean: {info['mean']}, Median: {info['median']}")
            elif info["type"] == "categorical":
                prompt_parts.append(f"- Unique values: {info['unique_count']}")
                top = info.get("top_values", {})
                if top:
                    top_str = ", ".join(f"{k} ({v})" for k, v in list(top.items())[:10])
                    prompt_parts.append(f"- Top: {top_str}")
            prompt_parts.append("")

        # Cross-tabulations
        if preprocessed.get("cross_tabs"):
            prompt_parts.append("## Cross-Tabulations\n")
            for tab_name, tab_data in preprocessed["cross_tabs"].items():
                prompt_parts.append(f"### {tab_name}")
                for segment, outcomes in sorted(tab_data.items()):
                    outcome_str = ", ".join(f"{k}: {v}" for k, v in outcomes.items())
                    prompt_parts.append(f"- {segment}: {outcome_str}")
                prompt_parts.append("")

        # Sample rows
        if preprocessed.get("sample_rows"):
            prompt_parts.append(f"## Sample Rows ({len(preprocessed['sample_rows'])} of {preprocessed['row_count']})\n")
            prompt_parts.append("```json")
            prompt_parts.append(json.dumps(preprocessed["sample_rows"][:15], indent=2, default=str))
            prompt_parts.append("```\n")

        # Analysis-specific output instructions
        prompt_parts.append(self._get_output_instructions(analysis_type))

        return "\n".join(prompt_parts)

    def _get_output_instructions(self, analysis_type: str) -> str:
        """Return the output schema instructions for each analysis type."""
        schemas = {
            "icp": """## Output Format

Return ONLY valid JSON with this exact structure:
{
  "analysis_type": "icp",
  "icp_definition": "string — 2-3 sentence summary of the ideal customer profile based on the data",
  "strongest_predictors": [
    {"factor": "string", "direction": "positive|negative", "impact": "high|medium|low", "evidence": "string"}
  ],
  "anti_patterns": [
    {"factor": "string", "description": "string — what makes a bad-fit customer"}
  ],
  "recommended_filters": [
    {"column": "string", "operator": "equals|contains|greater_than|less_than", "value": "string", "rationale": "string"}
  ],
  "segment_insights": [
    {"segment": "string", "finding": "string", "win_rate": "string or null"}
  ],
  "confidence_score": 0.0-1.0,
  "key_takeaways": ["string — 3-5 actionable insights"]
}""",
            "win-loss": """## Output Format

Return ONLY valid JSON with this exact structure:
{
  "analysis_type": "win-loss",
  "win_themes": [
    {"theme": "string", "frequency": "high|medium|low", "description": "string", "examples": ["string"]}
  ],
  "loss_themes": [
    {"theme": "string", "frequency": "high|medium|low", "description": "string", "examples": ["string"]}
  ],
  "objection_angles": [
    {"objection": "string", "frequency": "high|medium|low", "suggested_response": "string"}
  ],
  "qualification_questions": [
    {"question": "string", "why": "string — what this question helps identify"}
  ],
  "confidence_score": 0.0-1.0,
  "key_takeaways": ["string — 3-5 actionable insights"]
}""",
            "churn": """## Output Format

Return ONLY valid JSON with this exact structure:
{
  "analysis_type": "churn",
  "churn_predictors": [
    {"factor": "string", "risk_level": "high|medium|low", "lead_time": "string — how early this signal appears", "evidence": "string"}
  ],
  "retention_signals": [
    {"factor": "string", "strength": "strong|moderate|weak", "description": "string"}
  ],
  "aha_features": [
    {"feature": "string", "impact": "string — correlation with retention"}
  ],
  "risk_indicators": [
    {"indicator": "string", "threshold": "string", "action": "string — what to do when triggered"}
  ],
  "confidence_score": 0.0-1.0,
  "key_takeaways": ["string — 3-5 actionable insights"]
}""",
            "usage": """## Output Format

Return ONLY valid JSON with this exact structure:
{
  "analysis_type": "usage",
  "adoption_patterns": [
    {"feature": "string", "adoption_rate": "string", "correlation_with_retention": "positive|neutral|negative", "insight": "string"}
  ],
  "power_user_profile": {
    "description": "string",
    "key_behaviors": ["string"],
    "percentage_of_users": "string"
  },
  "underused_features": [
    {"feature": "string", "adoption_rate": "string", "potential_impact": "string"}
  ],
  "engagement_tiers": [
    {"tier": "string", "criteria": "string", "size": "string", "retention_rate": "string or null"}
  ],
  "confidence_score": 0.0-1.0,
  "key_takeaways": ["string — 3-5 actionable insights"]
}""",
            "sequence-performance": """## Output Format

Return ONLY valid JSON with this exact structure:
{
  "analysis_type": "sequence-performance",
  "top_performing_patterns": [
    {"pattern": "string", "metric": "string", "value": "string", "sample_size": "string"}
  ],
  "underperforming_patterns": [
    {"pattern": "string", "issue": "string", "suggestion": "string"}
  ],
  "timing_insights": [
    {"finding": "string", "recommendation": "string"}
  ],
  "subject_line_analysis": [
    {"pattern": "string", "performance": "above_average|average|below_average", "example": "string"}
  ],
  "personalization_impact": {
    "finding": "string",
    "top_variables": ["string"],
    "recommendation": "string"
  },
  "confidence_score": 0.0-1.0,
  "key_takeaways": ["string — 3-5 actionable insights"]
}""",
            "expansion": """## Output Format

Return ONLY valid JSON with this exact structure:
{
  "analysis_type": "expansion",
  "expansion_triggers": [
    {"trigger": "string", "frequency": "high|medium|low", "avg_time_to_expand": "string or null", "evidence": "string"}
  ],
  "upsell_segments": [
    {"segment": "string", "expansion_rate": "string", "avg_expansion_value": "string or null", "key_signals": ["string"]}
  ],
  "timing_patterns": [
    {"pattern": "string", "optimal_window": "string", "evidence": "string"}
  ],
  "risk_factors": [
    {"factor": "string", "impact": "string — how it blocks expansion"}
  ],
  "confidence_score": 0.0-1.0,
  "key_takeaways": ["string — 3-5 actionable insights"]
}""",
        }
        return schemas.get(analysis_type, schemas["icp"])
