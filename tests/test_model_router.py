from unittest.mock import patch

from app.core.model_router import resolve_model


class TestLayer1RequestOverride:
    def test_request_model_takes_priority(self):
        result = resolve_model(
            request_model="haiku",
            skill_config={"model": "opus", "model_tier": "heavy"},
            prompt="short prompt",
        )
        assert result == "haiku"


class TestLayer2SkillModel:
    def test_explicit_model_from_skill(self):
        result = resolve_model(
            skill_config={"model": "sonnet"},
        )
        assert result == "sonnet"


class TestLayer3SkillTier:
    @patch("app.core.model_router.settings")
    def test_tier_maps_to_model(self, mock_settings):
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.enable_smart_routing = False
        mock_settings.default_model = "opus"
        result = resolve_model(skill_config={"model_tier": "light"})
        assert result == "haiku"

    @patch("app.core.model_router.settings")
    def test_tier_standard(self, mock_settings):
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.enable_smart_routing = False
        mock_settings.default_model = "opus"
        result = resolve_model(skill_config={"model_tier": "standard"})
        assert result == "sonnet"

    @patch("app.core.model_router.settings")
    def test_tier_heavy(self, mock_settings):
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.enable_smart_routing = False
        mock_settings.default_model = "opus"
        result = resolve_model(skill_config={"model_tier": "heavy"})
        assert result == "opus"

    @patch("app.core.model_router.settings")
    def test_unknown_tier_falls_through(self, mock_settings):
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.enable_smart_routing = False
        mock_settings.default_model = "opus"
        result = resolve_model(skill_config={"model_tier": "unknown"})
        assert result == "opus"


class TestLayer4SmartRouting:
    @patch("app.core.model_router.settings")
    def test_short_prompt_routes_to_haiku(self, mock_settings):
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        mock_settings.default_model = "opus"

        result = resolve_model(prompt="x" * 100, context_file_count=0)
        assert result == "haiku"

    @patch("app.core.model_router.settings")
    def test_medium_prompt_routes_to_sonnet(self, mock_settings):
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        mock_settings.default_model = "opus"

        # 20000 chars -> ~5000 tokens -> sonnet range
        result = resolve_model(prompt="x" * 20000, context_file_count=0)
        assert result == "sonnet"

    @patch("app.core.model_router.settings")
    def test_long_prompt_routes_to_opus(self, mock_settings):
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        mock_settings.default_model = "opus"

        # 80000 chars -> ~20000 tokens -> opus range
        result = resolve_model(prompt="x" * 80000, context_file_count=0)
        assert result == "opus"

    @patch("app.core.model_router.settings")
    def test_short_prompt_with_many_files_skips_haiku(self, mock_settings):
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        mock_settings.default_model = "opus"

        # Short prompt but >1 context file -> should skip haiku
        result = resolve_model(prompt="x" * 100, context_file_count=3)
        assert result == "sonnet"

    @patch("app.core.model_router.settings")
    def test_smart_routing_disabled_skips_to_default(self, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.default_model = "opus"

        result = resolve_model(prompt="short")
        assert result == "opus"


class TestLayer5Default:
    @patch("app.core.model_router.settings")
    def test_no_config_returns_default(self, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.default_model = "opus"
        result = resolve_model()
        assert result == "opus"

    @patch("app.core.model_router.settings")
    def test_empty_skill_config_returns_default(self, mock_settings):
        mock_settings.enable_smart_routing = False
        mock_settings.default_model = "opus"
        result = resolve_model(skill_config={})
        assert result == "opus"


class TestLayerPriority:
    def test_request_beats_skill_model(self):
        result = resolve_model(request_model="haiku", skill_config={"model": "opus"})
        assert result == "haiku"

    def test_skill_model_beats_tier(self):
        result = resolve_model(skill_config={"model": "sonnet", "model_tier": "heavy"})
        assert result == "sonnet"

    def test_tier_beats_smart_routing(self):
        with patch("app.core.model_router.settings") as mock_settings:
            mock_settings.enable_smart_routing = True
            mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
            mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
            mock_settings.default_model = "opus"

            result = resolve_model(
                skill_config={"model_tier": "light"},
                prompt="x" * 80000,  # would be opus via smart routing
            )
            assert result == "haiku"


# ---------------------------------------------------------------------------
# _estimate_tokens
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_basic_estimate(self):
        from app.core.model_router import _estimate_tokens
        assert _estimate_tokens("x" * 400) == 100

    def test_empty_string(self):
        from app.core.model_router import _estimate_tokens
        assert _estimate_tokens("") == 0

    def test_short_string(self):
        from app.core.model_router import _estimate_tokens
        # 3 chars // 4 = 0
        assert _estimate_tokens("abc") == 0

    def test_exact_multiple(self):
        from app.core.model_router import _estimate_tokens
        assert _estimate_tokens("x" * 8000) == 2000


# ---------------------------------------------------------------------------
# PromptStats dataclass
# ---------------------------------------------------------------------------


class TestPromptStats:
    def test_creation(self):
        from app.core.model_router import PromptStats
        ps = PromptStats(token_estimate=500, context_file_count=3)
        assert ps.token_estimate == 500
        assert ps.context_file_count == 3


# ---------------------------------------------------------------------------
# Smart routing boundary cases
# ---------------------------------------------------------------------------


class TestSmartRoutingBoundaries:
    @patch("app.core.model_router.settings")
    def test_exactly_at_light_threshold(self, mock_settings):
        """Exactly 2000 tokens (8000 chars) with <=1 file → haiku."""
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        result = resolve_model(prompt="x" * 8000, context_file_count=1)
        assert result == "haiku"

    @patch("app.core.model_router.settings")
    def test_one_above_light_threshold(self, mock_settings):
        """2001 tokens (8004 chars) → sonnet."""
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        result = resolve_model(prompt="x" * 8004, context_file_count=0)
        assert result == "sonnet"

    @patch("app.core.model_router.settings")
    def test_exactly_at_standard_threshold(self, mock_settings):
        """Exactly 10000 tokens (40000 chars) → sonnet."""
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        result = resolve_model(prompt="x" * 40000, context_file_count=0)
        assert result == "sonnet"

    @patch("app.core.model_router.settings")
    def test_one_above_standard_threshold(self, mock_settings):
        """10001 tokens (40004 chars) → opus."""
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        result = resolve_model(prompt="x" * 40004, context_file_count=0)
        assert result == "opus"

    @patch("app.core.model_router.settings")
    def test_exactly_one_context_file_still_haiku(self, mock_settings):
        """context_file_count=1 is still eligible for haiku (<=1 check)."""
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        result = resolve_model(prompt="x" * 100, context_file_count=1)
        assert result == "haiku"

    @patch("app.core.model_router.settings")
    def test_two_context_files_skips_haiku(self, mock_settings):
        """context_file_count=2 prevents haiku even for short prompts."""
        mock_settings.enable_smart_routing = True
        mock_settings.model_tier_map = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        mock_settings.auto_route_thresholds = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        result = resolve_model(prompt="x" * 100, context_file_count=2)
        assert result == "sonnet"

    @patch("app.core.model_router.settings")
    def test_prompt_none_with_smart_routing_enabled(self, mock_settings):
        """Smart routing enabled but prompt=None → falls through to default."""
        mock_settings.enable_smart_routing = True
        mock_settings.default_model = "opus"
        result = resolve_model(prompt=None)
        assert result == "opus"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_string_model_in_skill_falls_through(self):
        """Skill config with model='' (falsy) falls through to next layer."""
        with patch("app.core.model_router.settings") as mock_settings:
            mock_settings.enable_smart_routing = False
            mock_settings.default_model = "opus"
            result = resolve_model(skill_config={"model": ""})
            assert result == "opus"

    def test_none_skill_config(self):
        """skill_config=None treated same as empty dict."""
        with patch("app.core.model_router.settings") as mock_settings:
            mock_settings.enable_smart_routing = False
            mock_settings.default_model = "sonnet"
            result = resolve_model(skill_config=None)
            assert result == "sonnet"

    def test_empty_string_request_model_falls_through(self):
        """request_model='' (falsy) falls through to next layer."""
        with patch("app.core.model_router.settings") as mock_settings:
            mock_settings.enable_smart_routing = False
            mock_settings.default_model = "opus"
            result = resolve_model(request_model="", skill_config={"model": "sonnet"})
            assert result == "sonnet"
