"""
Shared pytest fixtures for HR AI Agent tests.
"""
import json
import pytest
from pathlib import Path

@pytest.fixture
def sample_news_ru():
    return {
        "title": "Массовые сокращения в IT-секторе: 5000 сотрудников под увольнение",
        "content": "Крупная технологическая компания объявила о масштабной реструктуризации. Планируется сократить 5000 рабочих мест в связи с оптимизацией расходов. Сотрудники жалуются на выгорание и повышенный уровень стресса.",
        "source": "VC.ru",
        "language": "ru",
        "timestamp": "2026-04-24T10:00:00"
    }

@pytest.fixture
def sample_news_en():
    return {
        "title": "Tech Giant Announces Massive Hiring Spree: 10,000 New Positions",
        "content": "The company revealed plans for unprecedented growth with new hiring initiatives across all departments. Focus on diversity and inclusion with competitive salary packages.",
        "source": "TechCrunch",
        "language": "en",
        "timestamp": "2026-04-24T10:00:00"
    }

@pytest.fixture
def mock_agent_state(tmp_path):
    from src.agent.state import AgentState
    state = AgentState()
    state.data_dir = tmp_path
    state._observations = []
    state._insights = []
    state._alerts = []
    state._config = {"role": "hr_director", "topics": ["layoffs","hiring","salaries","burnout"], "sensitivity": "medium", "time_range": "24h"}
    return state

@pytest.fixture
def tmp_state_file(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"observations": [], "insights": [], "alerts": [], "config": {}}))
    return state_file
