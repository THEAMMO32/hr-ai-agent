"""
Tests for data sources (RSS fetcher and mock data generator).
"""
import pytest
from unittest.mock import Mock, patch
from src.sources.rss_fetcher import RSSFetcher
from src.sources.mock_data import MockDataGenerator


class TestRSSFetcher:
    """Test suite for RSS feed fetching."""

    @patch('src.sources.rss_fetcher.feedparser')
    def test_fetch_all_aggregates_sources(self, mock_feedparser):
        # Configure mock to return two entries per source
        mock_feedparser.parse.return_value.entries = [
            Mock(link="http://example.com/1", title="News 1", summary="Summary 1"),
            Mock(link="http://example.com/2", title="News 2", summary="Summary 2")
        ]
        fetcher = RSSFetcher()
        # Override sources for predictable test
        fetcher.sources = [
            {"url": "http://feed1.com/rss", "name": "Feed1", "lang": "en"},
            {"url": "http://feed2.com/rss", "name": "Feed2", "lang": "ru"}
        ]
        items = fetcher.fetch_all()
        assert len(items) == 4  # 2 sources * 2 entries each

    @patch('src.sources.rss_fetcher.feedparser')
    def test_fetch_handles_parse_error(self, mock_feedparser):
        mock_feedparser.parse.side_effect = Exception("Parse error")
        fetcher = RSSFetcher()
        fetcher.sources = [{"url": "http://bad.com/rss", "name": "Bad", "lang": "en"}]
        items = fetcher.fetch_all()
        assert items == []  # graceful failure

    @patch('src.sources.rss_fetcher.feedparser')
    def test_fetch_limits_entries_per_source(self, mock_feedparser):
        entries = [Mock(link=f"http://ex.com/{i}", title=f"T{i}", summary=f"S{i}") for i in range(15)]
        mock_feedparser.parse.return_value.entries = entries
        fetcher = RSSFetcher()
        fetcher.sources = [{"url": "http://feed.com/rss", "name": "Feed", "lang": "en"}]
        items = fetcher.fetch_all()
        assert len(items) == 10  # max 10 per source

    @patch('src.sources.rss_fetcher.feedparser')
    def test_fetch_includes_metadata(self, mock_feedparser):
        mock_entry = Mock()
        mock_entry.link = "http://ex.com/1"
        mock_entry.title = "Test"
        mock_entry.summary = "Summary"
        mock_feedparser.parse.return_value.entries = [mock_entry]
        fetcher = RSSFetcher()
        fetcher.sources = [{"url": "http://feed.com/rss", "name": "TestFeed", "lang": "en"}]
        items = fetcher.fetch_all()
        assert items[0]["source"] == "TestFeed"
        assert items[0]["lang"] == "en"
        assert items[0]["type"] == "rss"


class TestMockDataGenerator:
    """Test suite for mock data generation."""

    def test_generate_batch_returns_requested_count(self):
        gen = MockDataGenerator()
        batch = gen.generate_batch(3)
        assert len(batch) == 3

    def test_all_items_marked_as_mock(self):
        gen = MockDataGenerator()
        batch = gen.generate_batch(5)
        for item in batch:
            assert item["type"] == "mock"
            assert item["is_mock"] is True

    def test_generated_items_have_ids_and_urls(self):
        gen = MockDataGenerator()
        batch = gen.generate_batch(1)
        assert "id" in batch[0]
        assert "url" in batch[0]

    def test_generate_batch_does_not_exceed_available_news(self):
        gen = MockDataGenerator()
        batch = gen.generate_batch(100)  # more than available
        assert len(batch) <= len(gen.MOCK_NEWS)

    def test_generate_batch_different_each_time(self):
        gen = MockDataGenerator()
        batch1 = gen.generate_batch(3)
        batch2 = gen.generate_batch(3)
        # IDs should differ because they use random UUIDs
        ids1 = {item["id"] for item in batch1}
        ids2 = {item["id"] for item in batch2}
        assert ids1.isdisjoint(ids2)  # likely, but not 100% guaranteed; acceptable for test

    def test_generated_content_is_string(self):
        gen = MockDataGenerator()
        batch = gen.generate_batch(1)
        assert isinstance(batch[0]["content"], str)
        assert len(batch[0]["content"]) > 0


# Дополнительные тесты для источников (source manager заглушка)
class TestSourceManager:
    """Tests for hypothetical source manager (if implemented)."""

    def test_sources_catalog_loads_all(self):
        from config.settings import RSS_SOURCES
        assert len(RSS_SOURCES) >= 2

    def test_get_active_sources_filters_correctly(self):
        # Placeholder: в реальном проекте можно протестировать фильтрацию
        # Здесь просто демонстрация структуры
        pass

    def test_source_manager_evaluate_valuable(self):
        # Placeholder
        pass

    def test_build_source_report_structure(self):
        # Placeholder
        pass