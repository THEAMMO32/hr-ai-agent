"""
Tests for HRRules module (src/agent/rules.py).
"""
import pytest
from src.agent.rules import HRRules


class TestCalculateRiskScore:
    """Tests for risk score calculation."""
    
    @pytest.mark.parametrize("text,expected_min", [
        # Risk keywords should raise score
        ("Company announces massive layoffs and restructuring", 0.7),
        ("Employee burnout reaches critical levels in tech sector", 0.7),
        ("Staff reduction and downsizing planned for Q3", 0.7),
        ("Workforce optimization leads to job cuts", 0.7),
    ])
    def test_calculate_risk_score_with_risk_keywords(self, text, expected_min):
        """Risk keywords (layoffs, burnout) should produce high risk scores."""
        score = HRRules.calculate_risk_score(text)
        assert score >= expected_min, f"Expected score >= {expected_min}, got {score}"
    
    @pytest.mark.parametrize("text,expected_max", [
        # Positive keywords should lower score
        ("Company announces massive hiring and growth plans", 0.3),
        ("New recruitment drive brings opportunities for talent", 0.3),
        ("Employee satisfaction reaches all-time high", 0.3),
        ("Company expands with new benefits and salary increases", 0.3),
    ])
    def test_calculate_risk_score_with_positive_keywords(self, text, expected_max):
        """Positive keywords (hiring, growth) should produce low risk scores."""
        score = HRRules.calculate_risk_score(text)
        assert score <= expected_max, f"Expected score <= {expected_max}, got {score}"
    
    @pytest.mark.parametrize("text", [
        "Regular quarterly report shows standard metrics",
        "Company updates office policy for hybrid work",
        "New coffee machine installed in break room",
        "Weekly team meeting scheduled for Friday",
    ])
    def test_calculate_risk_score_neutral(self, text):
        """Neutral text should score around 0.5."""
        score = HRRules.calculate_risk_score(text)
        assert 0.4 <= score <= 0.6, f"Expected score around 0.5, got {score}"


class TestDetectAnomaly:
    """Tests for anomaly detection."""
    
    def test_detect_anomaly_above_threshold(self):
        """Value 30%+ above average should be anomaly."""
        historical = [0.5, 0.5, 0.5, 0.5, 0.5]  # avg = 0.5
        current = 0.7  # 40% above avg
        result = HRRules.detect_anomaly(historical, current)
        assert result["is_anomaly"] is True
    
    def test_detect_anomaly_below_threshold(self):
        """Value within 30% of average should NOT be anomaly."""
        historical = [0.5, 0.5, 0.5, 0.5, 0.5]  # avg = 0.5
        current = 0.6  # 20% above avg
        result = HRRules.detect_anomaly(historical, current)
        assert result["is_anomaly"] is False
    
    def test_detect_anomaly_empty_history(self):
        """Empty history should not trigger anomaly."""
        result = HRRules.detect_anomaly([], 0.9)
        assert result["is_anomaly"] is False


class TestShouldGenerateAlert:
    """Tests for alert generation logic."""
    
    @pytest.mark.parametrize("sensitivity,threshold,risk_score,expected", [
        # Low sensitivity - only high risks
        ("low", 0.7, 0.8, True),
        ("low", 0.7, 0.6, False),
        ("low", 0.7, 0.3, False),
        # Medium sensitivity
        ("medium", 0.5, 0.8, True),
        ("medium", 0.5, 0.6, True),
        ("medium", 0.5, 0.4, False),
        # High sensitivity - catch everything
        ("high", 0.3, 0.8, True),
        ("high", 0.3, 0.6, True),
        ("high", 0.3, 0.4, True),
        ("high", 0.3, 0.2, False),
    ])
    def test_should_generate_alert_by_sensitivity(self, sensitivity, threshold, risk_score, expected):
        """Alert should trigger based on sensitivity threshold."""
        result = HRRules.should_generate_alert(
            risk_score=risk_score,
            sensitivity=sensitivity
        )
        assert result == expected, f"Sensitivity={sensitivity}, score={risk_score}: expected {expected}"
    
    def test_should_generate_alert_focus_topic_bonus(self):
        """Focus topic should lower threshold by 0.15."""
        # Without focus: 0.55 with medium sensitivity (threshold 0.5) -> True
        result_without_focus = HRRules.should_generate_alert(
            risk_score=0.55,
            sensitivity="medium",
            topic="culture",
            focus_topics=[]
        )
        assert result_without_focus is True
        
        # With focus: 0.55 - 0.15 = 0.40 < 0.5 -> still True
        result_with_focus = HRRules.should_generate_alert(
            risk_score=0.55,
            sensitivity="medium",
            topic="culture",
            focus_topics=["culture", "layoffs"]
        )
        assert result_with_focus is True


class TestPrioritizeInsight:
    """Tests for insight prioritization."""
    
    def test_prioritize_insight_critical(self):
        """Risk score 80+ should be critical priority."""
        insight = {
            "risk_score": 0.85,
            "what_changed": "Critical layoffs announced",
            "why_important": "Affects 5000 employees",
            "recommendation": "Immediate action required"
        }
        priority = HRRules.prioritize_insight(insight)
        assert priority >= 80
        assert priority <= 100
    
    def test_prioritize_insight_low(self):
        """Low risk score should have low priority."""
        insight = {
            "risk_score": 0.2,
            "what_changed": "Minor policy update",
            "why_important": "Routine change",
            "recommendation": "Note for review"
        }
        priority = HRRules.prioritize_insight(insight)
        assert priority < 30
    
    def test_prioritize_insight_with_anomaly_bonus(self):
        """Anomaly flag should increase priority."""
        insight_normal = {
            "risk_score": 0.6,
            "what_changed": "Change detected",
            "why_important": "Moderate impact",
            "recommendation": "Review needed"
        }
        insight_anomaly = {
            **insight_normal,
            "anomaly": {"is_anomaly": True}
        }
        
        priority_normal = HRRules.prioritize_insight(insight_normal)
        priority_anomaly = HRRules.prioritize_insight(insight_anomaly)
        
        assert priority_anomaly > priority_normal