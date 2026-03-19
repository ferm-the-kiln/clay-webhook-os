"""Tests for skill chain DSL parser."""
from app.core.chain_parser import chain_to_skill_list, evaluate_condition, parse_chain


class TestParseChain:
    def test_single_skill(self):
        steps = parse_chain("email-gen")
        assert len(steps) == 1
        assert steps[0]["skill"] == "email-gen"
        assert steps[0]["condition"] is None
        assert steps[0]["params"] == {}

    def test_two_skills_arrow(self):
        steps = parse_chain("email-gen → quality-gate")
        assert len(steps) == 2
        assert steps[0]["skill"] == "email-gen"
        assert steps[1]["skill"] == "quality-gate"

    def test_ascii_arrow(self):
        steps = parse_chain("email-gen -> quality-gate")
        assert len(steps) == 2
        assert steps[0]["skill"] == "email-gen"
        assert steps[1]["skill"] == "quality-gate"

    def test_three_skills(self):
        steps = parse_chain("classify → email-gen → quality-gate")
        assert len(steps) == 3
        assert [s["skill"] for s in steps] == ["classify", "email-gen", "quality-gate"]

    def test_params(self):
        steps = parse_chain("email-gen(model=sonnet) → quality-gate")
        assert steps[0]["params"] == {"model": "sonnet"}
        assert steps[1]["params"] == {}

    def test_multiple_params(self):
        steps = parse_chain("email-gen(model=sonnet, retry=true)")
        assert steps[0]["params"] == {"model": "sonnet", "retry": "true"}

    def test_condition(self):
        steps = parse_chain("email-gen → quality-gate | if confidence_score < 0.7")
        assert steps[1]["condition"] is not None
        assert steps[1]["condition"]["field"] == "confidence_score"
        assert steps[1]["condition"]["op"] == "<"
        assert steps[1]["condition"]["value"] == 0.7

    def test_empty_string(self):
        assert parse_chain("") == []
        assert parse_chain("   ") == []

    def test_none_input(self):
        assert parse_chain(None) == []


class TestEvaluateCondition:
    def test_less_than_true(self):
        cond = {"field": "score", "op": "<", "value": 0.7}
        assert evaluate_condition(cond, {"score": 0.5}) is True

    def test_less_than_false(self):
        cond = {"field": "score", "op": "<", "value": 0.7}
        assert evaluate_condition(cond, {"score": 0.9}) is False

    def test_equals_string(self):
        cond = {"field": "status", "op": "==", "value": "approved"}
        assert evaluate_condition(cond, {"status": "approved"}) is True
        assert evaluate_condition(cond, {"status": "rejected"}) is False

    def test_not_equals(self):
        cond = {"field": "status", "op": "!=", "value": "rejected"}
        assert evaluate_condition(cond, {"status": "approved"}) is True

    def test_greater_than(self):
        cond = {"field": "score", "op": ">", "value": 0.5}
        assert evaluate_condition(cond, {"score": 0.8}) is True

    def test_missing_field(self):
        cond = {"field": "score", "op": "<", "value": 0.7}
        assert evaluate_condition(cond, {}) is False

    def test_none_condition(self):
        assert evaluate_condition(None, {"any": "data"}) is True

    def test_gte(self):
        cond = {"field": "n", "op": ">=", "value": 5}
        assert evaluate_condition(cond, {"n": 5}) is True
        assert evaluate_condition(cond, {"n": 4}) is False

    def test_lte(self):
        cond = {"field": "n", "op": "<=", "value": 5}
        assert evaluate_condition(cond, {"n": 5}) is True
        assert evaluate_condition(cond, {"n": 6}) is False


class TestChainToSkillList:
    def test_extracts_skill_names(self):
        skills = chain_to_skill_list("email-gen → quality-gate → follow-up")
        assert skills == ["email-gen", "quality-gate", "follow-up"]

    def test_with_params(self):
        skills = chain_to_skill_list("email-gen(model=sonnet) → quality-gate")
        assert skills == ["email-gen", "quality-gate"]

    def test_empty(self):
        assert chain_to_skill_list("") == []
