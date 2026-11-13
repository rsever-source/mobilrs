import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import requests
from bs4 import BeautifulSoup

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

    def test_date_failure_diagnostic_reports_dom_location_without_guessing(self):
        html = (
            "<html><body><div class='story-title'>Haber başlığı</div>"
            "<section class='article-meta'><span class='publish-date'>15.10.2026</span></section>"
            "</body></html>"
        )
        response = FakeResponse(
            html,
            url="https://www.aa.com.tr/tr/ayrimcilikhatti/engelsiz-yasam/test/125",
        )
        diagnostics = []
        with patch.object(ns._SESSION, "get", return_value=response):
            published = ns._article_published_at(response.url, diagnostics=diagnostics)
        self.assertIsNone(published)
        self.assertTrue(diagnostics)
        self.assertIn('"h1_found":false', diagnostics[0])
        self.assertIn('"class":"publish-date"', diagnostics[0])
        self.assertIn('"dates":["15.10.2026"]', diagnostics[0])
        self.assertIn('"contains_heading":false', diagnostics[0])

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
        diagnostic = ns._SOURCE_DIAGNOSTICS[source["name"]]
        self.assertFalse(diagnostic["validated"])
        self.assertTrue(any("Detay sayfası doğrulanamadı" in error for error in diagnostic["errors"]))

    def test_aa_byline_date_is_parsed_without_h1(self):
        # Gerçek AA DOM yapısı: başlık h1 değil; tarih div.news-writeby içinde
        # düz metin, gövdede ise haberde anılan geçmiş bir tarih var.
        html = (
            "<html><body><div class='news-maindiv'><div class='news-detail'>"
            "<h3 class='spot'>10 yaşındaki otizmli şampiyon yüzücü Kaan, Manş Denizi'ni geçmeyi hedefliyor.</h3>"
            "<div class='news-writeby'><div class='author'>Fatih Gökbulut</div>"
            "<div>15.10.2026</div></div>"
            "<div class='contentBodyDiv'><p>Fırsat verilmesi halinde ABD'li Dan Parker'ın "
            "31 Mart 2022'de kırdığı rekoru geliştirebilir.</p></div>"
            "</div></div></body></html>"
        )
        response = FakeResponse(
            html,
            url="https://www.aa.com.tr/tr/ayrimcilikhatti/engelsiz-yasam/otizmli-yuzucu/3456",
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            published = ns._article_published_at(response.url)
        self.assertEqual(published, "2026-10-15T00:00:00+00:00")

    def test_aa_maindiv_date_is_parsed_when_writeby_absent(self):
        html = (
            "<html><body><div class='news-maindiv'><h3>Spot metni başlık</h3>"
            "<div>16.10.2026</div>"
            "<div class='contentBodyDiv'><p>Metin 01.01.2020'de başladı.</p></div>"
            "</div></body></html>"
        )
        response = FakeResponse(
            html,
            url="https://www.aa.com.tr/tr/ayrimcilikhatti/engelsiz-yasam/test/3457",
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            published = ns._article_published_at(response.url)
        self.assertEqual(published, "2026-10-16T00:00:00+00:00")

    def test_aa_page_without_reliable_date_returns_none(self):
        # Yazar-tarih bloğunda tarih yok; gövdedeki tarih yayın tarihi sanılmamalı.
        html = (
            "<html><body><div class='news-maindiv'>"
            "<div class='news-writeby'><div class='author'>Muhabir</div></div>"
            "<div class='contentBodyDiv'><p>Etkinlik 15.10.2026 tarihinde düzenlendi.</p></div>"
            "</div></body></html>"
        )
        response = FakeResponse(
            html,
            url="https://www.aa.com.tr/tr/ayrimcilikhatti/engelsiz-yasam/test/3458",
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            published = ns._article_published_at(response.url)
        self.assertIsNone(published)

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
            "<html><head><title>Engelli yönetmelik duyurusu</title></head><body>"
            "<h1>Engelli yönetmelik duyurusu</h1><main><article>"
            "Bu TBB duyurusu, engelli bireylere ilişkin yönetmelik değişikliğini "
            "ve belediyelerin uygulaması gereken esasları açıklamaktadır."
            "</article></main></body></html>",
            url="https://www.tbb.gov.tr/tr/mevzuat-duyurulari/engelli-duyurusu",
        )
        with patch.object(ns._SESSION, "get", side_effect=[listing, detail]):
            items = ns._tbb_mevzuat_items(source)
        self.assertEqual(items, [])
        diagnostic = ns._SOURCE_DIAGNOSTICS[source["name"]]
        self.assertFalse(diagnostic["validated"])
        self.assertTrue(any("yayın tarihi bulunamadı" in error for error in diagnostic["errors"]))



    def test_tbb_validates_tls_list_title_date_content_and_keeps_tbb_link(self):
        source = {
            "name": ns.TBB_SOURCE_NAME,
            "url": "https://www.tbb.gov.tr/tr/mevzuat-duyurulari",
            "keywords": ["engelli"],
        }
        tbb_url = "https://www.tbb.gov.tr/tr/mevzuat-duyurulari/engelli-duyurusu"
        gazette_url = "https://www.resmigazete.gov.tr/eskiler/2026/11/20261109.htm"
        listing = FakeResponse(
            "<html><body><a href='/tr/mevzuat-duyurulari/engelli-duyurusu'>"
            "Engelli yönetmelik duyurusu</a></body></html>",
            url=source["url"],
        )
        detail = FakeResponse(
            "<html><head><meta property='article:published_time' "
            "content='2026-11-09T10:00:00+03:00'></head><body>"
            "<h1>Engelli yönetmelik duyurusu</h1><main><article>"
            "Bu TBB duyurusu, engelli bireylere ilişkin yönetmelik değişikliğini "
            "ve belediyelerin uygulaması gereken esasları açıklamaktadır. "
            "Ayrıntılı açıklama ve uygulama hükümleri bu sayfada yer almaktadır."
            "</article></main>"
            f"<a href='{gazette_url}'>Resmî Gazete</a></body></html>",
            url=tbb_url,
        )
        with patch.object(ns._SESSION, "get", side_effect=[listing, detail]) as get:
            items = ns._tbb_mevzuat_items(source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], tbb_url)
        self.assertEqual(items[0]["content_url"], gazette_url)
        self.assertEqual(items[0]["content_origin"], "Resmî Gazete mevzuat belgesi")
        self.assertIn("TBB duyurusu", items[0]["content"])
        self.assertEqual(items[0]["published_at"], "2026-11-09T07:00:00+00:00")
        diagnostic = ns._SOURCE_DIAGNOSTICS[source["name"]]
        self.assertTrue(diagnostic["tls_verified"])
        self.assertTrue(diagnostic["list_read"])
        self.assertTrue(diagnostic["validated"])
        self.assertEqual(get.call_count, 2)
        self.assertTrue(all(call.kwargs.get("verify") is True for call in get.call_args_list))

    def test_tbb_no_keyword_match_uses_detail_probe_for_source_health(self):
        source = {
            "name": ns.TBB_SOURCE_NAME,
            "url": "https://www.tbb.gov.tr/tr/mevzuat-duyurulari",
            "keywords": ["engelli"],
        }
        listing = FakeResponse(
            "<html><body><a href='/tr/mevzuat-duyurulari/personel-duyurusu'>"
            "Belediyelere yönelik personel mevzuatı duyurusu</a></body></html>",
            url=source["url"],
        )
        detail = FakeResponse(
            "<html><head><meta property='article:published_time' "
            "content='2026-11-09T10:00:00+03:00'></head><body>"
            "<h1>Belediyelere yönelik personel mevzuatı duyurusu</h1><main><article>"
            "Bu TBB duyurusu belediyelerin personel mevzuatı uygulamalarına ilişkin "
            "bilgilendirme içerir. Ayrıntılar ve uygulama esasları açıklanmıştır."
            "</article></main></body></html>",
            url="https://www.tbb.gov.tr/tr/mevzuat-duyurulari/personel-duyurusu",
        )
        with patch.object(ns._SESSION, "get", side_effect=[listing, detail]):
            items = ns._tbb_mevzuat_items(source)

        self.assertEqual(items, [])
        diagnostic = ns._SOURCE_DIAGNOSTICS[source["name"]]
        self.assertTrue(diagnostic["health_probe"])
        self.assertTrue(diagnostic["validated"])
        self.assertEqual(diagnostic["detail_successes"], 1)

    def test_tbb_redirect_to_non_tbb_page_cannot_validate_source(self):
        source = {
            "name": ns.TBB_SOURCE_NAME,
            "url": "https://www.tbb.gov.tr/tr/mevzuat-duyurulari",
            "keywords": ["engelli"],
        }
        listing = FakeResponse(
            "<html><body><a href='/tr/mevzuat-duyurulari/engelli-duyurusu'>"
            "Engelli yönetmelik duyurusu</a></body></html>",
            url=source["url"],
        )
        wrong_page = FakeResponse(
            "<html><body><h1>Engelli yönetmelik duyurusu</h1><main>"
            "Bu sayfa yanlış hedefe yönlendirilmiştir ve duyuru kaynağı değildir."
            "</main></body></html>",
            url="https://example.com/fake",
        )
        with patch.object(ns._SESSION, "get", side_effect=[listing, wrong_page]):
            ns._tbb_mevzuat_items(source)

        diagnostic = ns._SOURCE_DIAGNOSTICS[source["name"]]
        self.assertFalse(diagnostic["validated"])
        self.assertTrue(any("beklenmeyen adrese yönlendi" in error for error in diagnostic["errors"]))


class TbbPublishedAtFieldTests(unittest.TestCase):
    """TBB detay sayfasindaki gercek duyuru yayin tarihi alaninin okunmasi.

    Gercek TBB sayfalarinda yayin tarihi, duyurunun kendi govdesindeki
    "field--name-published-at" alaninda <time datetime="..."> olarak durur.
    Sayfanin geri kalanindaki <time> etiketleri "diger duyurular" listesine
    aittir ve duyuru metnindeki tarihler mevzuat icinde gecebilir.
    """

    def setUp(self):
        ns._SOURCE_DIAGNOSTICS.clear()

    @staticmethod
    def _detail_html(published_datetime, published_text, extra_time_tags="", body=""):
        return (
            "<html><head><title>Engelli yönetmelik duyurusu</title></head><body>"
            "<h1>Engelli yönetmelik duyurusu</h1>"
            "<article class='node node--type-announcement node--view-mode-full clearfix'>"
            "<div class='block block-layout-builder block-field-blocknodeannouncementpublished-at'>"
            "<div class='field field--name-published-at field--type-published-at field__item'>"
            f"<time datetime='{published_datetime}' class='datetime'>{published_text}</time>"
            "</div></div>"
            f"<div class='field field--name-body field--type-text-with-summary'>{body}</div>"
            "</article>"
            f"{extra_time_tags}"
            "</body></html>"
        )

    def test_announcement_published_at_field_is_preferred_over_sidebar_dates(self):
        # Sidebar'da 8 farkli "diger duyuru" tarihi var; genel tarama bunlari
        # toplayip "tek aday" kuralini bozuyordu ve tarih None donuyordu.
        sidebar = (
            "<div class='view view-announcements view-id-announcements'>"
            "<div class='views-row'><div class='views-field views-field-title'>"
            "<span class='field-content'>"
            "<time datetime='2026-11-04T12:12:27+03:00' class='datetime'>04/11/2026</time>"
            "</span></div></div>"
            "<div class='views-row'><div class='views-field views-field-title'>"
            "<span class='field-content'>"
            "<time datetime='2026-10-27T17:33:59+03:00' class='datetime'>27/10/2026</time>"
            "</span></div></div>"
            "</div>"
        )
        soup = BeautifulSoup(
            self._detail_html("2026-11-10T11:15:08+03:00", "10 Kasım 2026", sidebar),
            "html.parser",
        )
        published = ns._tbb_detail_published_at(soup)
        self.assertEqual(published, "2026-11-10T08:15:08+00:00")

    def test_datetime_attribute_is_preferred_over_visible_text(self):
        # datetime oznitelligi ISO ve saat iceriyor; gorunen metin gun seviyesinde.
        soup = BeautifulSoup(
            self._detail_html("2026-11-10T11:15:08+03:00", "10 Kasım 2026"),
            "html.parser",
        )
        self.assertEqual(ns._tbb_detail_published_at(soup), "2026-11-10T08:15:08+00:00")

    def test_visible_text_is_used_when_datetime_attribute_is_missing(self):
        html = (
            "<html><body><h1>Engelli yönetmelik duyurusu</h1>"
            "<article class='node node--type-announcement'>"
            "<div class='field field--name-published-at field__item'>"
            "<time class='datetime'>04/11/2026</time>"
            "</div></article></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(ns._tbb_detail_published_at(soup), "2026-11-04T00:00:00+00:00")

    def test_legal_text_dates_do_not_override_announcement_date(self):
        # Mevzuat metni icinde gecerli tarihler var; duyuru tarihi onlardan farkli
        # olmali ve mevzuat metnindeki tarih secilmemeli.
        body = (
            "<p>Bu duyuru 15.10.2026 tarihli kararname uyarinca yayimlanmistir. "
            "Yayin tarihi 01.11.2026 olarak belirlenmistir.</p>"
        )
        soup = BeautifulSoup(
            self._detail_html("2026-11-10T11:15:08+03:00", "10 Kasım 2026", body=body),
            "html.parser",
        )
        published = ns._tbb_detail_published_at(soup)
        self.assertEqual(published, "2026-11-10T08:15:08+00:00")
        self.assertNotIn("2026-10-15", published)
        self.assertNotIn("2026-11-01", published)

    def test_many_time_tags_outside_announcement_do_not_block_the_date(self):
        # Cok sayida <time> etiketi (farkli yillarda) duyuru tarihi bulunmasini engellememeli.
        extra = "".join(
            f"<div class='views-row'><time datetime='2026-0{month}-01T08:00:00+03:00'>01/0{month}/2026</time></div>"
            for month in range(1, 9)
        )
        soup = BeautifulSoup(
            self._detail_html("2026-11-10T11:15:08+03:00", "10 Kasım 2026", extra),
            "html.parser",
        )
        self.assertEqual(ns._tbb_detail_published_at(soup), "2026-11-10T08:15:08+00:00")

    def test_meta_published_time_path_is_preserved(self):
        # Mevcut meta yolu degistirilmedi; oncelikli calismaya devam etmeli.
        html = (
            "<html><head><meta property='article:published_time' "
            "content='2026-11-09T10:00:00+03:00'></head><body>"
            "<h1>Engelli yönetmelik duyurusu</h1>"
            "<article class='node node--type-announcement'>"
            "<div class='field field--name-published-at field__item'>"
            "<time datetime='2026-01-01T00:00:00+03:00'>01/01/2026</time>"
            "</div></article></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(ns._tbb_detail_published_at(soup), "2026-11-09T07:00:00+00:00")

    def test_json_ld_published_date_path_is_preserved(self):
        html = (
            "<html><head><script type='application/ld+json'>"
            '{"@type":"Article","datePublished":"2026-11-08T09:30:00+03:00"}'
            "</script></head><body>"
            "<h1>Engelli yönetmelik duyurusu</h1>"
            "<article class='node node--type-announcement'>"
            "<div class='field field--name-published-at field__item'>"
            "<time datetime='2026-01-01T00:00:00+03:00'>01/01/2026</time>"
            "</div></article></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(ns._tbb_detail_published_at(soup), "2026-11-08T06:30:00+00:00")

    def test_page_without_announcement_field_falls_back_to_existing_behaviour(self):
        # published-at alani olmayan bir sayfada mevcut genel yol calismaya devam eder.
        html = (
            "<html><body><h1>Engelli yönetmelik duyurusu</h1>"
            "<time datetime='2026-11-05T10:00:00+03:00'>05/11/2026</time>"
            "</body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(ns._tbb_detail_published_at(soup), "2026-11-05T07:00:00+00:00")

    def test_announcement_without_any_published_date_still_returns_none(self):
        # published-at alani bos ve sayfada baska hicbir tarih yok: sonuc None.
        html = (
            "<html><body><h1>Engelli yönetmelik duyurusu</h1>"
            "<article class='node node--type-announcement'>"
            "<div class='field field--name-published-at field__item'></div>"
            "<div class='field field--name-body'>Duyuru metni</div>"
            "</article></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        self.assertIsNone(ns._tbb_detail_published_at(soup))

    def test_empty_announcement_field_keeps_existing_fallback_behaviour(self):
        # published-at alani bos sayfada mevcut genel tarama yolu devreye girer.
        # Bu, duzeltmeden once de gecerli olan davranistir ve degistirilmemistir.
        html = (
            "<html><body><h1>Engelli yönetmelik duyurusu</h1>"
            "<article class='node node--type-announcement'>"
            "<div class='field field--name-published-at field__item'></div>"
            "<div class='field field--name-body'><time>01/01/2026</time></div>"
            "</article></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(ns._tbb_detail_published_at(soup), "2026-01-01T00:00:00+00:00")

    def test_end_to_end_tbb_item_is_published_with_announcement_date(self):
        # Uctan uca: liste + detay sayfasi ile gercek duyuru haber olarak uretilmeli.
        source = {
            "name": ns.TBB_SOURCE_NAME,
            "url": "https://www.tbb.gov.tr/tr/mevzuat-duyurulari",
            "keywords": ["engelli"],
        }
        tbb_url = "https://www.tbb.gov.tr/tr/mevzuat-duyurulari/engelli-duyurusu"
        listing = FakeResponse(
            "<html><body><a href='/tr/mevzuat-duyurulari/engelli-duyurusu'>"
            "Engelli yönetmelik duyurusu</a></body></html>",
            url=source["url"],
        )
        sidebar = (
            "<div class='view view-announcements'><div class='views-row'>"
            "<time datetime='2026-11-04T12:12:27+03:00' class='datetime'>04/11/2026</time>"
            "</div></div>"
        )
        detail = FakeResponse(
            self._detail_html(
                "2026-11-10T11:15:08+03:00",
                "10 Kasım 2026",
                sidebar,
                body=(
                    "<p>Bu TBB duyurusu, engelli bireylere ilişkin yönetmelik "
                    "değişikliğini ve belediyelerin uygulaması gereken esasları "
                    "açıklamaktadır. Ayrıntılı açıklama ve uygulama hükümleri "
                    "bu sayfada yer almaktadır.</p>"
                ),
            ),
            url=tbb_url,
        )
        with patch.object(ns._SESSION, "get", side_effect=[listing, detail]):
            items = ns._tbb_mevzuat_items(source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], tbb_url)
        self.assertEqual(items[0]["published_at"], "2026-11-10T08:15:08+00:00")
        diagnostic = ns._SOURCE_DIAGNOSTICS[source["name"]]
        self.assertTrue(diagnostic["validated"])
        self.assertEqual(diagnostic["detail_successes"], 1)
        self.assertEqual(diagnostic["errors"], [])


class TbbPrimarySourcePolicyTests(unittest.TestCase):
    def setUp(self):
        ns._SOURCE_DIAGNOSTICS.clear()

    def test_resmigazete_fallback_is_skipped_in_normal_news_flow(self):
        source = {
            "name": "Resmî Gazete – TBB Mevzuat Yedeği",
            "kind": "resmigazete",
            "enabled": False,
            "disabled_reason": "manual fallback only",
        }
        with patch.object(ns, "_resmigazete_items") as fallback_parser:
            items = ns._source_items(source)

        self.assertEqual(items, [])
        fallback_parser.assert_not_called()
        diagnostic = ns._SOURCE_DIAGNOSTICS[source["name"]]
        self.assertEqual(diagnostic["stage"], "skipped")
        self.assertEqual(diagnostic["reason"], "manual fallback only")
        self.assertEqual(diagnostic["errors"], [])

    def test_tbb_primary_source_remains_enabled_and_is_called(self):
        source = {
            "name": "Türkiye Belediyeler Birliği – Mevzuat Duyuruları",
            "kind": "tbb_mevzuat",
            "enabled": True,
        }
        expected = [{"source": source["name"], "title": "Test", "url": "https://www.tbb.gov.tr/tr/mevzuat-duyurulari/test"}]
        with patch.object(ns, "_tbb_mevzuat_items", return_value=expected) as tbb_parser:
            items = ns._source_items(source)

        self.assertEqual(items, expected)
        tbb_parser.assert_called_once_with(source)


class FakeGibResponse:
    def __init__(self, status_code=200, payload=None, json_error=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"resultContainer": {"content": []}}
        self._json_error = json_error
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


class GibApiRetryTests(unittest.TestCase):
    def setUp(self):
        ns._GIB_SOURCE_DIAGNOSTICS.clear()
        self.source = {
            "name": "Test GIB",
            "url": "https://gib.gov.tr/api/list",
            "kind": "gib_api",
            "body": {},
            "size": 10,
            "pages": 1,
            "keywords": ["engelli"],
            "detail_url": "https://www.gib.gov.tr/duyuru-arsivi/guncel",
            "file_url": "https://cdn.gib.gov.tr/file/",
        }

    def _run(self, outcomes):
        with patch.object(ns, "_load_json", return_value={"items": [], "seen_urls": {}}), \
             patch.object(ns.time, "sleep"), \
             patch.object(ns._SESSION, "post", side_effect=outcomes) as post:
            items = ns._gib_api_items(self.source)
        return items, post.call_count, ns._GIB_SOURCE_DIAGNOSTICS["Test GIB"]

    def test_timeout_then_success_retries_once(self):
        response = FakeGibResponse()
        _, calls, diagnostic = self._run([
            requests.exceptions.ReadTimeout("first timeout"), response
        ])
        self.assertEqual(calls, 2)
        self.assertIsNone(diagnostic["error"])

    def test_three_timeouts_stop_after_three_attempts(self):
        _, calls, diagnostic = self._run([
            requests.exceptions.ReadTimeout("timeout 1"),
            requests.exceptions.ReadTimeout("timeout 2"),
            requests.exceptions.ReadTimeout("timeout 3"),
        ])
        self.assertEqual(calls, 3)
        self.assertIn("ReadTimeout", diagnostic["error"])

    def test_client_error_is_not_retried(self):
        _, calls, diagnostic = self._run([
            FakeGibResponse(status_code=400, text="bad request")
        ])
        self.assertEqual(calls, 1)
        self.assertIn("HTTP 400", diagnostic["error"])

    def test_invalid_json_is_not_retried(self):
        _, calls, diagnostic = self._run([
            FakeGibResponse(json_error=ValueError("invalid JSON"))
        ])
        self.assertEqual(calls, 1)
        self.assertIn("JSON parse", diagnostic["error"])


class ResmiGazeteFallbackTests(unittest.TestCase):
    def setUp(self):
        ns._SOURCE_DIAGNOSTICS.clear()
        ns._GIB_SOURCE_DIAGNOSTICS.clear()
        self.source = {
            "name": "Resmî Gazete – TBB Mevzuat Yedeği",
            "kind": "resmigazete",
            "url": "https://www.resmigazete.gov.tr",
            "lookback_days": 1,
            "max_items": 10,
            "keywords": ["engelli", "ötv", "erişilebilirlik"],
        }
        self.detail_url = "https://www.resmigazete.gov.tr/eskiler/2026/11/20261110-2.htm"
        self.listing = FakeResponse(
            "<html><body><a href='/eskiler/2026/11/20261110-2.htm'>"
            "Engelli Bireylere Yönelik Özel Bakım Merkezleri Yönetmeliği"
            "</a></body></html>",
            url="https://www.resmigazete.gov.tr/10.11.2026",
        )
        self.detail = FakeResponse(
            "<html><body><main><h1>Engelli Bireylere Yönelik Özel Bakım Merkezleri Yönetmeliği</h1>"
            "<p>Bu Yönetmeliğin amacı engelli bireylere sunulan özel bakım hizmetlerinin "
            "usul ve esaslarını, başvuru ve değerlendirme işlemlerini ve hizmet sunumunu "
            "düzenlemektir. Kuruluşlar Bakanlık tarafından denetlenir.</p></main></body></html>",
            url=self.detail_url,
        )

    def test_official_gazette_keyword_item_is_parsed_from_official_document(self):
        with patch.object(
            ns._SESSION, "get", side_effect=[self.listing, self.detail]
        ) as get, patch.object(ns.time, "sleep"):
            items = ns._resmigazete_items(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], self.source["name"])
        self.assertEqual(items[0]["url"], self.detail_url)
        self.assertIn("engelli bireylere", items[0]["title"].casefold())
        self.assertIn("özel bakım hizmetlerinin", items[0]["content"].casefold())
        expected_day = datetime.now(timezone(timedelta(hours=3))).date()
        self.assertEqual(
            ns._date(items[0]["published_at"]).date(),
            expected_day,
        )
        self.assertEqual(get.call_count, 2)
        diagnostic = ns._SOURCE_DIAGNOSTICS[self.source["name"]]
        self.assertEqual(diagnostic["keyword_matches"], 1)
        self.assertEqual(diagnostic["parsed_items"], 1)
        self.assertEqual(diagnostic["errors"], [])

    def test_official_gazette_index_timeout_retries_then_parses(self):
        with patch.object(
            ns._SESSION,
            "get",
            side_effect=[
                requests.exceptions.ReadTimeout("temporary timeout"),
                self.listing,
                self.detail,
            ],
        ) as get, patch.object(ns.time, "sleep"):
            items = ns._resmigazete_items(self.source)

        self.assertEqual(len(items), 1)
        self.assertEqual(get.call_count, 3)

    def test_official_gazette_unrelated_notice_is_not_selected(self):
        unrelated = FakeResponse(
            "<html><body><a href='/eskiler/2026/11/20261110-3.htm'>"
            "Gençlik ve Spor Bakanlığı Yurt Hizmetleri Yönetmeliği"
            "</a></body></html>",
            url="https://www.resmigazete.gov.tr/10.11.2026",
        )
        with patch.object(ns._SESSION, "get", return_value=unrelated):
            items = ns._resmigazete_items(self.source)

        self.assertEqual(items, [])
        diagnostic = ns._SOURCE_DIAGNOSTICS[self.source["name"]]
        self.assertEqual(diagnostic["keyword_matches"], 0)
        self.assertEqual(diagnostic["errors"], [])

    def test_official_gazette_legacy_turkish_html_decodes_from_original_bytes(self):
        html = (
            "<html><head><title>Resmî Gazete</title></head><body>"
            "<h1>7 Ekim 2026 ÇARŞAMBA</h1>"
            "<p>ENGELLİ BİREYLERE YÖNELİK ÖZEL BAKIM MERKEZLERİ YÖNETMELİĞİ</p>"
            "<p>Bu Yönetmeliğin amacı ve kapsamı engelli bireylere yönelik hizmetlerdir.</p>"
            "</body></html>"
        )
        class LegacyResponse:
            content = html.encode("cp1254")
            headers = {"Content-Type": "text/html; charset=ISO-8859-1"}
            url = "https://www.resmigazete.gov.tr/eskiler/2026/10/20261007-4.htm"
            text = content.decode("iso-8859-1")

            def raise_for_status(self):
                return None

        with patch.object(ns._SESSION, "get", return_value=LegacyResponse()):
            article = ns._resmigazete_document_text(
                "https://www.resmigazete.gov.tr/eskiler/2026/10/20261007-4.htm"
            )

        self.assertIn("ÇARŞAMBA", article)
        self.assertIn("YÖNETMELİĞİ", article)
        self.assertIn("Yönetmeliğin amacı", article)


    def test_official_gazette_utf8_html_keeps_turkish_characters(self):
        html = (
            "<html><body><h1>7 Ekim 2026 ÇARŞAMBA</h1>"
            "<p>ENGELLİ BİREYLERE YÖNELİK YÖNETMELİĞİ</p>"
            "<p>Yönetmeliğin amacı ve kapsamı.</p></body></html>"
        )
        response = FakeResponse(
            html,
            url="https://www.resmigazete.gov.tr/eskiler/2026/11/20261110-2.htm",
        )
        with patch.object(ns._SESSION, "get", return_value=response):
            article = ns._resmigazete_document_text(response.url)

        self.assertIn("ÇARŞAMBA", article)
        self.assertIn("ENGELLİ BİREYLERE", article)
        self.assertIn("YÖNETMELİĞİ", article)
        self.assertNotIn("ÇARÞAMBA", article)


if __name__ == "__main__":
    unittest.main()
