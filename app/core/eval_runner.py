"""Eval runner for Clay Webhook OS skills.

Loads golden sets from `evals/{skill_name}/golden-set.json`, executes each case
through the skill execution pipeline (without HTTP), scores outputs against
expected fields and quality criteria, and stores results for regression tracking.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.core.claude_executor import ClaudeExecutor
from app.core.context_assembler import build_prompt
from app.core.model_router import resolve_model
from app.core.skill_loader import load_context_files, load_skill, load_skill_config

logger = logging.getLogger("clay-webhook-os")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CaseScore:
    """Score for a single eval case."""
    case_index: int
    passed: bool
    field_presence: dict[str, bool] = field(default_factory=dict)
    json_valid: bool = True
    confidence_in_range: bool | None = None
    field_length_ok: dict[str, bool] = field(default_factory=dict)
    custom_assertions: dict[str, bool] = field(default_factory=dict)
    error: str | None = None
    output: dict | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "case_index": self.case_index,
            "passed": self.passed,
            "field_presence": self.field_presence,
            "json_valid": self.json_valid,
            "confidence_in_range": self.confidence_in_range,
            "field_length_ok": self.field_length_ok,
            "custom_assertions": self.custom_assertions,
            "error": self.error,
            "output": self.output,
            "duration_ms": self.duration_ms,
        }


@dataclass
class EvalResult:
    """Aggregate result for an eval run."""
    skill: str
    timestamp: str
    total_cases: int
    passed: int
    failed: int
    scores: list[CaseScore] = field(default_factory=list)
    regressions: list[dict] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "timestamp": self.timestamp,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.passed / self.total_cases, 3) if self.total_cases > 0 else 0.0,
            "scores": [s.to_dict() for s in self.scores],
            "regressions": self.regressions,
            "duration_ms": self.duration_ms,
        }


# ---------------------------------------------------------------------------
# Golden set loader
# ---------------------------------------------------------------------------

def _evals_dir() -> Path:
    return settings.base_dir / "evals"


def load_golden_set(skill: str) -> list[dict] | None:
    """Load golden-set.json for a skill. Returns None if not found."""
    golden_file = _evals_dir() / skill / "golden-set.json"
    if not golden_file.exists():
        return None
    try:
        return json.loads(golden_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.error("[eval] Failed to load golden set for %s: %s", skill, e)
        return None


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_case(case_index: int, output: dict, case_def: dict, duration_ms: int = 0) -> CaseScore:
    """Score a single eval case output against its definition."""
    score = CaseScore(case_index=case_index, passed=True, duration_ms=duration_ms)

    # Check JSON validity — if we got here, the output is already a dict
    score.json_valid = isinstance(output, dict)
    if not score.json_valid:
        score.passed = False
        score.error = "Output is not a valid JSON object"
        return score

    # Store output for inspection
    score.output = output

    # Field presence
    expected_fields = case_def.get("expected_fields", [])
    for field_name in expected_fields:
        present = field_name in output and output[field_name] is not None
        score.field_presence[field_name] = present
        if not present:
            score.passed = False

    # Quality criteria
    criteria = case_def.get("quality_criteria", {})

    # confidence_score_min
    if "confidence_score_min" in criteria:
        conf = output.get("confidence_score")
        if conf is not None:
            try:
                conf_val = float(conf)
                score.confidence_in_range = conf_val >= criteria["confidence_score_min"]
                if not score.confidence_in_range:
                    score.passed = False
            except (TypeError, ValueError):
                score.confidence_in_range = False
                score.passed = False
        else:
            # confidence_score not present — already caught by field_presence
            score.confidence_in_range = False

    # max_field_lengths
    max_lengths = criteria.get("max_field_lengths", {})
    for field_name, max_len in max_lengths.items():
        value = output.get(field_name, "")
        if isinstance(value, str):
            ok = len(value) <= max_len
            score.field_length_ok[field_name] = ok
            if not ok:
                score.passed = False
        else:
            # Non-string field — skip length check
            score.field_length_ok[field_name] = True

    return score


# ---------------------------------------------------------------------------
# Regression detection
# ---------------------------------------------------------------------------

def compare_runs(skill: str, run_a_ts: str, run_b_ts: str) -> list[dict]:
    """Compare two eval runs and return regressions (cases that passed in A but fail in B).

    Args:
        skill: Skill name.
        run_a_ts: Timestamp of the baseline run (older).
        run_b_ts: Timestamp of the new run (newer).

    Returns:
        List of regression dicts with case_index and details.
    """
    results_dir = _evals_dir() / skill / "results"
    file_a = results_dir / f"{run_a_ts}.json"
    file_b = results_dir / f"{run_b_ts}.json"

    if not file_a.exists() or not file_b.exists():
        return []

    try:
        data_a = json.loads(file_a.read_text())
        data_b = json.loads(file_b.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    scores_a = {s["case_index"]: s for s in data_a.get("scores", [])}
    scores_b = {s["case_index"]: s for s in data_b.get("scores", [])}

    regressions = []
    for idx, score_a in scores_a.items():
        score_b = scores_b.get(idx)
        if score_a.get("passed") and score_b and not score_b.get("passed"):
            regressions.append({
                "case_index": idx,
                "was_passing": True,
                "now_failing": True,
                "baseline_run": run_a_ts,
                "current_run": run_b_ts,
                "failed_checks": _diff_checks(score_a, score_b),
            })

    return regressions


def _diff_checks(score_a: dict, score_b: dict) -> list[str]:
    """Find which checks regressed between two case scores."""
    diffs = []
    # Field presence regressions
    for field_name, was_present in score_a.get("field_presence", {}).items():
        now_present = score_b.get("field_presence", {}).get(field_name, False)
        if was_present and not now_present:
            diffs.append(f"field_missing:{field_name}")
    # Confidence regression
    if score_a.get("confidence_in_range") and not score_b.get("confidence_in_range"):
        diffs.append("confidence_below_min")
    # Field length regression
    for field_name, was_ok in score_a.get("field_length_ok", {}).items():
        now_ok = score_b.get("field_length_ok", {}).get(field_name, True)
        if was_ok and not now_ok:
            diffs.append(f"field_too_long:{field_name}")
    # JSON validity regression
    if score_a.get("json_valid") and not score_b.get("json_valid"):
        diffs.append("json_invalid")
    return diffs


# ---------------------------------------------------------------------------
# Results storage
# ---------------------------------------------------------------------------

def save_result(skill: str, result: EvalResult) -> Path:
    """Save eval result to evals/{skill}/results/{timestamp}.json. Returns path."""
    results_dir = _evals_dir() / skill / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    result_file = results_dir / f"{result.timestamp}.json"
    result_file.write_text(json.dumps(result.to_dict(), indent=2))
    return result_file


def load_result(skill: str, timestamp: str) -> dict | None:
    """Load a specific eval result by timestamp."""
    result_file = _evals_dir() / skill / "results" / f"{timestamp}.json"
    if not result_file.exists():
        return None
    try:
        return json.loads(result_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def list_results(skill: str) -> list[str]:
    """List all result timestamps for a skill, newest first."""
    results_dir = _evals_dir() / skill / "results"
    if not results_dir.exists():
        return []
    timestamps = []
    for f in results_dir.iterdir():
        if f.suffix == ".json":
            timestamps.append(f.stem)
    return sorted(timestamps, reverse=True)


def get_latest_result(skill: str) -> dict | None:
    """Get the most recent eval result for a skill."""
    timestamps = list_results(skill)
    if not timestamps:
        return None
    return load_result(skill, timestamps[0])


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_eval(
    skill: str,
    *,
    model: str | None = None,
    timeout: int | None = None,
) -> EvalResult:
    """Run the full eval suite for a skill.

    Loads the golden set, executes each case through the skill pipeline
    (prompt assembly + ClaudeExecutor, bypassing HTTP layer), scores results,
    detects regressions against the previous run, and saves to disk.

    Args:
        skill: Skill name (must have a golden set in evals/).
        model: Optional model override. Defaults to skill config.
        timeout: Optional timeout override. Defaults to settings.request_timeout.

    Returns:
        EvalResult with all scores and regressions.
    """
    run_start = time.monotonic()
    timestamp = time.strftime("%Y%m%d-%H%M%S")

    golden_set = load_golden_set(skill)
    if golden_set is None:
        raise FileNotFoundError(f"No golden set found for skill '{skill}' at evals/{skill}/golden-set.json")

    # Load skill content
    skill_content = load_skill(skill)
    if skill_content is None:
        raise ValueError(f"Skill '{skill}' not found")

    config = load_skill_config(skill)
    resolved_model = model or resolve_model(skill_config=config)
    resolved_timeout = timeout or settings.request_timeout

    executor = ClaudeExecutor()
    scores: list[CaseScore] = []
    passed = 0
    failed = 0

    logger.info("[eval] Starting eval for skill=%s, cases=%d, model=%s", skill, len(golden_set), resolved_model)

    for i, case_def in enumerate(golden_set):
        case_data = case_def.get("input", {}).get("data", {})

        case_start = time.monotonic()
        try:
            # Build prompt (same pipeline as webhook, without HTTP)
            context_files = load_context_files(skill_content, case_data, skill_name=skill)
            prompt = build_prompt(skill_content, context_files, case_data)

            # Execute
            result = await executor.execute(prompt, model=resolved_model, timeout=resolved_timeout)
            case_duration = int((time.monotonic() - case_start) * 1000)

            output = result.get("result", {})
            if not isinstance(output, dict):
                score = CaseScore(
                    case_index=i,
                    passed=False,
                    json_valid=False,
                    error=f"Non-dict output: {type(output).__name__}",
                    duration_ms=case_duration,
                )
            else:
                score = score_case(i, output, case_def, duration_ms=case_duration)

        except Exception as e:
            case_duration = int((time.monotonic() - case_start) * 1000)
            score = CaseScore(
                case_index=i,
                passed=False,
                json_valid=False,
                error=str(e),
                duration_ms=case_duration,
            )
            logger.error("[eval] Case %d failed with error: %s", i, e)

        scores.append(score)
        if score.passed:
            passed += 1
        else:
            failed += 1

        logger.info(
            "[eval] Case %d/%d: %s (duration=%dms)",
            i + 1, len(golden_set),
            "PASS" if score.passed else "FAIL",
            score.duration_ms,
        )

    total_duration = int((time.monotonic() - run_start) * 1000)

    # Regression detection: compare against previous run
    previous_timestamps = list_results(skill)
    regressions = []
    if previous_timestamps:
        regressions = compare_runs(skill, previous_timestamps[0], timestamp)

    eval_result = EvalResult(
        skill=skill,
        timestamp=timestamp,
        total_cases=len(golden_set),
        passed=passed,
        failed=failed,
        scores=scores,
        regressions=regressions,
        duration_ms=total_duration,
    )

    # Save result
    result_path = save_result(skill, eval_result)
    logger.info(
        "[eval] Completed: skill=%s, passed=%d/%d, duration=%dms, saved=%s",
        skill, passed, len(golden_set), total_duration, result_path,
    )

    return eval_result
