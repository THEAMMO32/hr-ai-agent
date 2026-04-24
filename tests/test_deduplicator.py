"""
Tests for content deduplication module.
"""
import pytest
from src.deduplicator import Deduplicator, SimHash


class TestSimHash:
    def test_exact_duplicate_detected(self):
        d = Deduplicator()
        text = "Company announces massive layoffs in tech sector, affecting thousands of employees."
        assert not d.is_duplicate(text, url="url1")[0]
        assert d.is_duplicate(text, url="url2")[0]

    def test_near_duplicate_with_typos(self):
        d = Deduplicator(short_text_threshold=200, short_distance=3, long_distance=5)
        # длинный текст (>200 символов), чтобы использовать порог 5 бит
        base = "The company announced massive layoffs in the technology sector, affecting thousands of employees. "
        long_text = base * 6  # ~180*6 = 1080 символов
        assert not d.is_duplicate(long_text, url="url1")[0]
        # одна опечатка
        long_text2 = long_text.replace("layoffs", "layofs")
        assert d.is_duplicate(long_text2, url="url2")[0]

    def test_short_text_threshold(self):
        d = Deduplicator(short_text_threshold=200, short_distance=3)
        short = "Short text."
        assert not d.is_duplicate(short, url="s1")[0]
        short2 = "Short text.."
        assert d.is_duplicate(short2, url="s2")[0]

    def test_different_languages_same_news(self):
        d = Deduplicator()
        en = "Company announces massive layoffs, thousands of jobs cut."
        ru = "Компания объявляет о массовых увольнениях, тысячи рабочих мест сокращены."
        assert not d.is_duplicate(en, url="en1")[0]
        assert not d.is_duplicate(ru, url="ru1")[0]

    def test_empty_content_handled_gracefully(self):
        d = Deduplicator()
        assert not d.is_duplicate("", url="empty")[0]
        # None не должно вызывать исключений (наша реализация его не принимает, но тест проверяет)
        try:
            d.is_duplicate(None, url="none")
        except Exception:
            pytest.fail("is_duplicate raised exception on None input")

    def test_html_tags_stripped(self):
        d = Deduplicator()
        text1 = "<p>Hello world</p>"
        text2 = "Hello world"
        assert not d.is_duplicate(text1, url="html")[0]
        assert d.is_duplicate(text2, url="plain")[0]

    def test_fifo_buffer_evicts_old(self):
        d = Deduplicator(max_items=3)
        d.is_duplicate("First", url="1")
        d.is_duplicate("Second", url="2")
        d.is_duplicate("Third", url="3")
        d.is_duplicate("Fourth", url="4")
        assert not d.is_duplicate("First", url="5")[0]

    def test_stats_counts_correctly(self):
        d = Deduplicator()
        for i in range(10):
            d.is_duplicate(f"Unique text {i}", url=f"u{i}")
        d.is_duplicate("Unique text 0", url="dup1")
        d.is_duplicate("Unique text 1", url="dup2")
        d.is_duplicate("Unique text 2", url="dup3")
        stats = d.get_stats()
        assert stats["total_processed"] == 10
        assert stats["duplicates_found"] == 3
        assert abs(stats["duplicate_ratio"] - 3/10) < 0.001

    def test_is_url_processed_prefilter(self):
        d = Deduplicator()
        d.mark_url_processed("http://example.com", "Some content")
        assert d.is_url_processed("http://example.com")
        assert not d.is_url_processed("http://other.com")

    def test_different_casing(self):
        d = Deduplicator()
        text = "Breaking News: HR Trends in 2025"
        d.is_duplicate(text, url="1")
        assert d.is_duplicate(text.lower(), url="2")[0]
        assert d.is_duplicate(text.upper(), url="3")[0]

    def test_punctuation_normalized(self):
        d = Deduplicator()
        text1 = "Hello, world! How are you?"
        d.is_duplicate(text1, url="1")
        text2 = "Hello world How are you"
        assert d.is_duplicate(text2, url="2")[0]

    def test_reset_clears_all(self):
        d = Deduplicator()
        d.is_duplicate("Some text", url="1")
        d.reset()
        assert d.get_stats()["total_processed"] == 0
        assert not d.is_duplicate("Some text", url="1")[0]