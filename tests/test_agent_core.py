"""
Tests for agent core logic.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.agent.core import HRAgent
from src.agent.state import AgentState

RECENT = (datetime.now() - timedelta(hours=1)).isoformat()


@pytest.fixture
def fresh_state(tmp_path):
    """Чистое состояние с временным файлом для каждого теста."""
    state = AgentState()
    state.state_file = tmp_path / "state.json"
    state.reset()
    return state


@pytest.fixture
def mock_external_services():
    """Mock all external calls: translator, classifier, GigaChat."""
    with patch('src.agent.core.translate_if_needed', side_effect=lambda text, lang=None: text), \
         patch('src.agent.core.classify_content', return_value={
             "topic": "culture", "confidence": 0.7, "keywords": ["test"]
         }), \
         patch('src.insights.generator.gigachat_client') as mock_gc:
        mock_gc.generate_insight.return_value = {
            "what_changed": "Mock insight",
            "risk_level": "medium",
            "urgency": "week"
        }
        yield


@pytest.fixture
def mock_rss_fetcher():
    with patch('src.agent.core.RSSFetcher') as mock:
        instance = mock.return_value
        instance.fetch_all.return_value = []
        yield instance


@pytest.fixture
def mock_mock_data():
    with patch('src.agent.core.MockDataGenerator') as mock:
        instance = mock.return_value
        instance.generate_batch.return_value = []
        yield instance


@pytest.fixture
def agent(mock_external_services, mock_rss_fetcher, mock_mock_data, fresh_state):
    """Агент с полностью изолированным состоянием."""
    with patch('src.agent.state.agent_state', fresh_state), \
         patch('src.agent.core.agent_state', fresh_state):
        agent = HRAgent()
        yield agent


class TestHRAgent:
    def test_agent_initialization(self):
        agent = HRAgent()
        assert agent.user_config["role"] == "analyst"
        assert "hiring" in agent.user_config["focus_topics"]

    def test_agent_configure(self, agent):
        agent.configure(role="manager", sensitivity="high")
        assert agent.user_config["role"] == "manager"
        assert agent.user_config["sensitivity"] == "high"
        assert "diversity" in agent.user_config["focus_topics"]

    def test_run_cycle_processes_news(self, agent, mock_rss_fetcher, mock_mock_data, fresh_state):
        url = "http://example.com/1"
        mock_rss_fetcher.fetch_all.return_value = [{
            "url": url,
            "title": "Test news",
            "content": "Some content",
            "source": "TestSource",
            "lang": "en",
            "published": RECENT
        }]
        mock_mock_data.generate_batch.return_value = []
        result = agent.run_cycle()
        assert result["new_items"] == 1
        assert fresh_state.is_url_processed(url)

    def test_run_cycle_skips_duplicates(self, agent, mock_rss_fetcher, mock_mock_data, fresh_state):
        url = "http://dup.com"
        mock_rss_fetcher.fetch_all.return_value = [{
            "url": url,
            "title": "Dup",
            "content": "Content",
            "lang": "en",
            "published": RECENT
        }]
        mock_mock_data.generate_batch.return_value = []
        agent.run_cycle()
        result = agent.run_cycle()
        assert result["new_items"] == 0

    def test_run_cycle_updates_state(self, agent, mock_rss_fetcher, mock_mock_data, fresh_state):
        url = "http://state.com"
        mock_rss_fetcher.fetch_all.return_value = [{
            "url": url,
            "title": "State",
            "content": "Content",
            "lang": "en",
            "published": RECENT
        }]
        mock_mock_data.generate_batch.return_value = []
        agent.run_cycle()
        assert fresh_state.is_url_processed(url)
        assert len(fresh_state.get_trend_data("culture")) > 0

    def test_alert_generated_for_high_risk(self, agent, mock_rss_fetcher, mock_mock_data, fresh_state):
        url = "http://highrisk.com"
        mock_rss_fetcher.fetch_all.return_value = [{
            "url": url,
            "title": "Massive layoffs and downsizing",
            "content": "Company announces massive layoffs and restructuring affecting thousands",
            "lang": "en",
            "published": RECENT
        }]
        mock_mock_data.generate_batch.return_value = []
        result = agent.run_cycle()
        assert len(result["alerts_created"]) == 1

    def test_insight_generation_threshold(self, agent, mock_rss_fetcher, mock_mock_data, fresh_state):
        url = "http://insight.com"
        mock_rss_fetcher.fetch_all.return_value = [{
            "url": url,
            "title": "Burnout reaches critical levels",
            "content": "Employee burnout and overwork are at all-time high",
            "lang": "en",
            "published": RECENT
        }]
        mock_mock_data.generate_batch.return_value = []
        # Классифицируем как "burnout", чтобы triggered _should_generate_insight
        with patch('src.agent.core.classify_content', return_value={
            "topic": "burnout", "confidence": 0.9, "keywords": ["burnout"]
        }):
            result = agent.run_cycle()
        assert len(result["insights_generated"]) == 1

    def test_state_persistence(self, agent, fresh_state, tmp_path):
        fresh_state.save()
        new_state = AgentState()
        new_state.state_file = tmp_path / "state.json"
        loaded = new_state._load_state()
        assert "observations" in loaded

    def test_get_dashboard_data(self, agent):
        data = agent.get_dashboard_data()
        assert "insights" in data
        assert "trends" in data
        assert "metrics" in data

    def test_get_status(self, agent):
        status = agent.get_status()
        assert "total_observations" in status
        assert status["config"] == agent.user_config