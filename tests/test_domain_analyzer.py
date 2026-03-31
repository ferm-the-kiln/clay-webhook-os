"""Tests for app.core.domain_analyzer — pure keyword/exclusion analysis."""

from app.core.domain_analyzer import DomainSignals, analyze_domain_signals


class TestAnalyzeDomainSignals:
    def test_gps_company_name(self):
        result = analyze_domain_signals("SolidGPS", "solidgps.com")
        assert result.keyword_matches
        assert "gps" in result.keyword_matches
        assert result.suggested_archetype == "GPS / Fleet Tracking"
        assert result.confidence_boost > 0

    def test_iot_domain_keywords(self):
        result = analyze_domain_signals("Acme IoT Sensors", "acme-sensors.com")
        assert "sensor" in result.keyword_matches
        assert result.confidence_boost >= 0.1

    def test_hard_exclusion_bank(self):
        result = analyze_domain_signals("Goldman Sachs Banking", "goldmansachs.com")
        assert result.is_hard_exclusion is True
        assert result.confidence_boost == 0.0
        assert not result.keyword_matches

    def test_hard_exclusion_fashion(self):
        result = analyze_domain_signals("Zara Fashion Group", "zara.com")
        assert result.is_hard_exclusion is True

    def test_hard_exclusion_insurance(self):
        result = analyze_domain_signals("Hartford Insurance", "thehartford.com")
        assert result.is_hard_exclusion is True

    def test_no_signals(self):
        result = analyze_domain_signals("Acme Corp", "acme.com")
        assert not result.keyword_matches
        assert result.confidence_boost == 0.0
        assert result.suggested_archetype == ""
        assert result.is_hard_exclusion is False

    def test_boost_three_plus_keywords(self):
        result = analyze_domain_signals("GPS Fleet Tracker Telematics", "gpsfleet.com")
        assert result.confidence_boost == 0.3

    def test_boost_two_keywords(self):
        result = analyze_domain_signals("DroneBot Autonomous", "dronebot.com")
        assert result.confidence_boost >= 0.2

    def test_boost_one_keyword(self):
        result = analyze_domain_signals("FarmTech", "farmtech.io")
        assert result.confidence_boost == 0.1

    def test_robotics_archetype(self):
        result = analyze_domain_signals("Voliro Airborne Robotics", "voliro.com")
        assert result.suggested_archetype == "Robotics / Autonomous"

    def test_agriculture_archetype(self):
        result = analyze_domain_signals("HerdDogg Livestock", "herddogg.com")
        assert "livestock" in result.keyword_matches or "herd" in result.keyword_matches
        assert result.suggested_archetype == "Agriculture / Livestock"

    def test_cellular_keywords_boost_without_archetype(self):
        result = analyze_domain_signals("Acme SIM Card Manager", "acme-sim.com")
        assert "sim card" in result.keyword_matches
        assert result.confidence_boost >= 0.1
