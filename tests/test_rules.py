"""
Tests for HRRules module (src/agent/rules.py).
"""
import pytest
from src.agent.rules import HRRules


class TestCalculateRiskScore:
    """Tests for risk score calculation."""

    @pytest.mark.parametrize("text,topic,expected_min", [
        ("Company announces massive layoffs and restructuring", "layoffs", 0.7),
        ("Employee burnout reaches critical levels in tech sector", "burnout", 0.65),
        ("Staff reduction and downsizing planned for Q3", "layoffs", 0.65),
        ("Workforce optimization leads to job cuts", "layoffs", 0.65),
    ])
    def test_calculate_risk_score_with_risk_keywords(self, text, topic, expected_min):
        score = HRRules.calculate_risk_score(text, topic)
        assert score >= expected_min, f"Expected >= {expected_min}, got {score}"

    @pytest.mark.parametrize("text,topic,expected_max", [
        ("Company launches new hiring surge and upskilling program, employee well-being improved", "hiring", 0.3),
        ("New talent acquisition and training program drives career growth", "hiring", 0.3),
        ("Employee satisfaction and well-being at all-time high", "culture", 0.35),
        ("Company expands with new benefits and salary increases, employee engagement up", "salaries", 0.4),
    ])
    def test_calculate_risk_score_with_positive_keywords(self, text, topic, expected_max):
        score = HRRules.calculate_risk_score(text, topic)
        assert score <= expected_max, f"Expected <= {expected_max}, got {score}"

    @pytest.mark.parametrize("text,topic", [
        ("Regular quarterly report shows standard metrics", "culture"),
        ("Company updates office policy for hybrid work", "culture"),
        ("New coffee machine installed in break room", "culture"),
        ("Weekly team meeting scheduled for Friday", "culture"),
    ])
    def test_calculate_risk_score_neutral(self, text, topic):
        score = HRRules.calculate_risk_score(text, topic)
        assert 0.4 <= score <= 0.6, f"Expected ~0.5, got {score}"


class TestDetectAnomaly:
    """Tests for anomaly detection."""

    def test_detect_anomaly_above_threshold(self):
        historical = [{"value": 0.5} for _ in range(5)]
        current = 0.7
        result = HRRules.detect_anomaly(current, historical)
        assert result["is_anomaly"] is True

    def test_detect_anomaly_below_threshold(self):
        historical = [{"value": 0.5} for _ in range(5)]
        current = 0.6
        result = HRRules.detect_anomaly(current, historical)
        assert result["is_anomaly"] is False

    def test_detect_anomaly_empty_history(self):
        result = HRRules.detect_anomaly(0.9, [])
        assert result["is_anomaly"] is False

    def test_anomaly_insufficient_history(self):
        historical = [{"value": 0.5} for _ in range(4)]
        result = HRRules.detect_anomaly(0.9, historical)
        assert result["is_anomaly"] is False


class TestShouldGenerateAlert:
    """Tests for alert generation logic."""

    @pytest.mark.parametrize("sensitivity,risk_score,expected", [
        ("low", 0.8, True),
        ("low", 0.6, False),
        ("low", 0.3, False),
        ("medium", 0.8, True),
        ("medium", 0.6, True),
        ("medium", 0.4, False),
        ("high", 0.8, True),
        ("high", 0.6, True),
        ("high", 0.4, True),
        ("high", 0.2, False),
    ])
    def test_should_generate_alert_by_sensitivity(self, sensitivity, risk_score, expected):
        user_config = {"sensitivity": sensitivity, "focus_topics": []}
        result = HRRules.should_generate_alert(risk_score, "layoffs", user_config)
        assert result == expected, f"sensitivity={sensitivity}, score={risk_score}: expected {expected}"

    def test_should_generate_alert_focus_topic_bonus(self):
        user_config_no_focus = {"sensitivity": "medium", "focus_topics": []}
        assert HRRules.should_generate_alert(0.55, "culture", user_config_no_focus) is True

        user_config_focus = {"sensitivity": "medium", "focus_topics": ["culture"]}
        assert HRRules.should_generate_alert(0.55, "culture", user_config_focus) is True
        assert HRRules.should_generate_alert(0.4, "culture", user_config_focus) is True
        assert HRRules.should_generate_alert(0.4, "culture", user_config_no_focus) is False


class TestPrioritizeInsight:
    """Tests for insight prioritization."""

    def test_prioritize_insight_critical(self):
        insight = {
            "risk_score": 0.85,
            "risk_level": "critical",
            "urgency": "immediate",
            "what_changed": "Critical layoffs announced",
            "why_important": "Affects 5000 employees",
            "recommendation": "Immediate action required"
        }
        priority = HRRules.prioritize_insight(insight, "hr_director")
        assert priority == 100

    def test_prioritize_insight_low(self):
        insight = {
            "risk_score": 0.2,
            "risk_level": "low",
            "urgency": "month",
            "what_changed": "Minor policy update",
            "why_important": "Routine change",
            "recommendation": "Note for review"
        }
        priority = HRRules.prioritize_insight(insight, "hr_director")
        assert priority == 55

    def test_prioritize_insight_medium(self):
        insight = {
            "risk_score": 0.5,
            "risk_level": "medium",
            "urgency": "week",
            "what_changed": "Some change",
            "why_important": "Moderate impact",
            "recommendation": "Review"
        }
        priority = HRRules.prioritize_insight(insight, "hr_director")
        assert priority == 75

    def test_prioritize_insight_with_anomaly_bonus(self):
        insight_normal = {
            "risk_score": 0.6,
            "risk_level": "high",
            "urgency": "week",
            "what_changed": "Change detected",
            "why_important": "Moderate impact",
            "recommendation": "Review needed"
        }
        insight_anomaly = {
            **insight_normal,
            "anomaly": {"is_anomaly": True}
        }
        priority_normal = HRRules.prioritize_insight(insight_normal, "hr_director")
        priority_anomaly = HRRules.prioritize_insight(insight_anomaly, "hr_director")
        assert priority_normal == 90
        assert priority_anomaly == 90