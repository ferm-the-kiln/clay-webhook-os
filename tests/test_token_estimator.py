from app.core.token_estimator import MODEL_PRICING, estimate_cost, estimate_tokens


class TestEstimateTokens:
    def test_basic_estimate(self):
        assert estimate_tokens(400) == 100

    def test_small_input(self):
        assert estimate_tokens(1) == 1

    def test_zero_returns_one(self):
        assert estimate_tokens(0) == 1

    def test_rounding(self):
        assert estimate_tokens(5) == 1
        assert estimate_tokens(6) == 2


class TestEstimateCost:
    def test_opus_cost(self):
        cost = estimate_cost("opus", 1000, 500)
        expected = (1000 / 1_000_000) * 15.0 + (500 / 1_000_000) * 75.0
        assert cost == round(expected, 6)

    def test_sonnet_cost(self):
        cost = estimate_cost("sonnet", 1000, 500)
        expected = (1000 / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0
        assert cost == round(expected, 6)

    def test_haiku_cost(self):
        cost = estimate_cost("haiku", 1000, 500)
        expected = (1000 / 1_000_000) * 0.25 + (500 / 1_000_000) * 1.25
        assert cost == round(expected, 6)

    def test_unknown_model_falls_back_to_opus(self):
        cost_unknown = estimate_cost("gpt-5", 1000, 500)
        cost_opus = estimate_cost("opus", 1000, 500)
        assert cost_unknown == cost_opus

    def test_zero_tokens(self):
        assert estimate_cost("opus", 0, 0) == 0.0

    def test_large_token_count(self):
        cost = estimate_cost("opus", 1_000_000, 1_000_000)
        expected = 15.0 + 75.0
        assert cost == expected


class TestModelPricing:
    def test_all_models_have_input_output(self):
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing
            assert pricing["input"] > 0
            assert pricing["output"] > 0
