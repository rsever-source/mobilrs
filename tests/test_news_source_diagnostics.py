import unittest
from unittest.mock import patch

import requests
import news_service as ns


class FakeResponse:
    def __init__(self, text, url="https://example.com/feed"):
        self.text = text
        self.content = text.encode("utf-8")
        self.url = url
        self.status_code = 200
        self.headers = {"Content-Type": "text/html; charset=utf-8"}

    def raise_for_status(self):
        return None


class NewsSourceDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        ns._SOURCE_DIAGNOSTICS.clear()
        ns._GIB_SOURCE_DIAGNOSTICS.clear()

    def test_valid_empty_rss_is_not_a_source_error(self):
        source = {"name": "Test RSS", "url": "https://example.com/feed"}
        response = FakeResponse(
            "<rss version='2.0'><channel><title>Test</title></channel></rss>"
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            items = ns._feed_items(source)
        self.assertEqual(items, [])
        self.assertEqual(ns._SOURCE_DIAGNOSTICS["Test RSS"]["errors"], [])

    def test_changed_rss_root_is_reported_as_parse_error(self):
        source = {"name": "Test RSS", "url": "https://example.com/feed"}
        response = FakeResponse("<html><body>Site changed</body></html>")
        with patch.object(ns._SESSION, "get", return_value=response):
            with self.assertRaises(ValueError):
                ns._feed_items(source)
        self.assertTrue(ns._SOURCE_DIAGNOSTICS["Test RSS"]["errors"])

    def test_rss_items_without_parseable_title_and_link_are_reported(self):
        source = {"name": "Test RSS", "url": "https://example.com/feed"}
        response = FakeResponse(
            "<rss version='2.0'><channel><title>Test</title>"
            "<item><description>Missing title and link</description></item>"
            "</channel></rss>"
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            items = ns._feed_items(source)
        self.assertEqual(items, [])
        self.assertTrue(ns._SOURCE_DIAGNOSTICS["Test RSS"]["errors"])

    def test_html_path_change_is_reported(self):
        source = {
            "name": "Test HTML",
            "url": "https://example.com/news",
            "include_path": "/news/",
            "allowed_prefix": "https://example.com/",
        }
        response = FakeResponse(
            "<html><body><a href='/about'>About this organization</a></body></html>",
            url=source["url"],
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            with self.assertRaises(RuntimeError):
                ns._html_items(source)
        self.assertTrue(ns._SOURCE_DIAGNOSTICS["Test HTML"]["errors"])

    def test_valid_html_with_old_news_is_not_a_source_error(self):
        source = {
            "name": "Test HTML",
            "url": "https://example.com/news",
            "include_path": "/news/",
            "allowed_prefix": "https://example.com/",
        }
        response = FakeResponse(
            "<html><body><a href='/news/old'>Engelli destek duyurusu 01.10.2026</a></body></html>",
            url=source["url"],
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            items = ns._html_items(source)
        self.assertEqual(len(items), 1)
        self.assertEqual(ns._SOURCE_DIAGNOSTICS["Test HTML"]["errors"], [])

    def test_aa_visible_header_date_is_parsed_when_no_metadata_exists(self):
        html = (
            "<html><body><main><div class='article-header'>"
            "<h1>Bakan Göktaş'tan engelli bireylere ilişkin paylaşım</h1>"
            "<div class='author'>Fatih Gökbulut</div><div class='date'>07.10.2026</div>"
            "</div><div class='article-body'>Haber metni.</div></main></body></html>"
        )
        response = FakeResponse(
            html,
            url="https://www.aa.com.tr/tr/ayrimcilikhatti/engelsiz-yasam/test/123",
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            published = ns._article_published_at(response.url)
        self.assertEqual(published, "2026-10-07T00:00:00+00:00")

    def test_visible_date_outside_article_header_is_not_guessed(self):
        html = (
            "<html><body><h1>Haber başlığı</h1><div class='related'>"
            "Başka haber 01.10.2026</div><div class='related'>"
            "Diğer haber 02.10.2026</div></body></html>"
        )
        response = FakeResponse(
            html,
            url="https://www.aa.com.tr/tr/ayrimcilikhatti/engelsiz-yasam/test/124",
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            published = ns._article_published_at(response.url)
        self.assertIsNone(published)

    def test_tbb_detail_failure_is_recorded(self):
        source = {
            "name": "Türkiye Belediyeler Birliği – Mevzuat Duyuruları",
            "url": "https://www.tbb.gov.tr/tr/mevzuat-duyurulari",
            "keywords": ["engelli"],
        }
        listing = FakeResponse(
            "<html><body><a href='/tr/mevzuat-duyurulari/engelli-duyurusu'>"
            "Engelli yönetmelik duyurusu</a></body></html>",
            url=source["url"],
        )
        with patch.object(
            ns._SESSION,
            "get",
            side_effect=[listing, requests.exceptions.Timeout("detail timed out")],
        ):
            items = ns._tbb_mevzuat_items(source)
        self.assertEqual(items, [])
        errors = ns._SOURCE_DIAGNOSTICS[source["name"]]["errors"]
        self.assertTrue(any("Detay sayfası okunamadı" in error for error in errors))

    def test_tbb_unparseable_publication_date_is_recorded(self):
        source = {
            "name": "Türkiye Belediyeler Birliği – Mevzuat Duyuruları",
            "url": "https://www.tbb.gov.tr/tr/mevzuat-duyurulari",
            "keywords": ["engelli"],
        }
        listing = FakeResponse(
            "<html><body><a href='/tr/mevzuat-duyurulari/engelli-duyurusu'>"
            "Engelli yönetmelik duyurusu</a></body></html>",
            url=source["url"],
        )
        detail = FakeResponse(
            "<html><body>Bu duyuru metninde beklenen yayın tarihi bulunmuyor.</body></html>",
            url="https://www.tbb.gov.tr/tr/mevzuat-duyurulari/engelli-duyurusu",
        )
        with patch.object(ns._SESSION, "get", side_effect=[listing, detail]):
            items = ns._tbb_mevzuat_items(source)
        self.assertEqual(items, [])
        errors = ns._SOURCE_DIAGNOSTICS[source["name"]]["errors"]
        self.assertTrue(any("Yayın tarihi çözümlenemedi" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
