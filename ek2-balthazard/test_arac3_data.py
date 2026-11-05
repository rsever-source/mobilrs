import json
import re
from pathlib import Path
import unittest


HTML = Path(__file__).parent / "arac3" / "arac3.html"


class Arac3DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = HTML.read_text(encoding="utf-8")
        match = re.search(r"const diseases=(\[.*?\]);\nconst ARAC3_MAPPING_DATA=", source)
        if not match:
            raise AssertionError("Araç 3 veri dizisi bulunamadı")
        cls.records = json.loads(match.group(1))

    def test_complete_source_counts(self):
        self.assertEqual(len(self.records), 182)
        self.assertEqual(len({record["category"] for record in self.records}), 16)
        self.assertEqual(sum(record["hasFas"] for record in self.records), 18)
        self.assertEqual(sum(record["calculator"] == "KDS" for record in self.records), 1)

    def test_source_markers_are_not_standalone_records(self):
        names = {record["name"] for record in self.records}
        self.assertNotIn("FAS", names)
        self.assertNotIn("hesaplayıcı", names)
        self.assertEqual(
            next(record["name"] for record in self.records if record["calculator"] == "KDS"),
            "Kognitif bozukluklar",
        )

    def test_source_traceability_is_present(self):
        for record in self.records:
            source = record["source"]
            self.assertEqual(source["textFile"], "Yeni Metin Belgesi (2).txt")
            self.assertEqual(source["pdf"], "20210928-4-1.pdf")
            self.assertGreater(source["textLine"], 0)
            self.assertEqual(source["pdfSection"], record["category"])
            self.assertTrue(source["pdfPages"])


    def test_ek1_mapping_dataset_integrity(self):
        mapping_path = Path(__file__).parent / "arac3" / "arac3_182_ek1_eslestirme.json"
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        records = data["kayitlar"]
        self.assertEqual(len(records), 182)
        self.assertEqual(len({row["mevcut_kayit_id"] for row in records}), 182)
        self.assertEqual(data["ozet"]["duzey_basligi_bulunan_mevcut_kayit"], 177)
        self.assertEqual(data["ozet"]["en_az_bir_kriter_metni_dolu_mevcut_kayit"], 166)
        self.assertEqual(data["ozet"]["duzey_basligi_var_kriter_metni_bos_mevcut_kayit"], 11)
        self.assertEqual(data["ozet"]["eslesme_yok_kayitlar"], [])
        for row in records:
            self.assertIsInstance(row.get("duzeyler"), list)
            if not row.get("duzey_gosterimi_izinli"):
                self.assertFalse(row.get("duzeyler"), row["mevcut_kayit_id"])


    def test_shared_accessibility_toolbar_footer_and_mobile_layout(self):
        source = HTML.read_text(encoding="utf-8")
        for control_id in (
            "siteAccessibilityToggle",
            "siteAccessibilityPanel",
            "siteAccessibilityReset",
            "siteContrastToggle",
            "siteDarkToggle",
        ):
            self.assertIn(f'id="{control_id}"', source)

        self.assertIn('data-site-font="1.12"', source)
        self.assertIn('data-site-font="1.25"', source)
        self.assertIn('localStorage.setItem("engellime-font-size"', source)
        self.assertIn('localStorage.setItem("engellime-high-contrast"', source)
        self.assertIn('localStorage.setItem("engellime-dark-mode"', source)
        self.assertIn('body.font-large .sayfa{zoom:1.12}', source)
        self.assertIn('body.font-xlarge .sayfa{zoom:1.25}', source)
        self.assertIn("@media(max-width:760px)", source)
        self.assertIn(".site-accessibility-panel.open{display:flex;flex-direction:column}", source)
        self.assertIn('<footer class="alt-bilgi">', source)
        self.assertIn('href="#main-content"', source)
        self.assertEqual(len(re.findall(r"<main\b", source)), 1)

    def test_mapping_notice_count_and_mobile_header_match_arac1(self):
        source = HTML.read_text(encoding="utf-8")
        mapping_path = Path(__file__).parent / "arac3" / "arac3_182_ek1_eslestirme.json"
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        self.assertEqual(data["ozet"]["duzey_basligi_var_kriter_metni_bos_mevcut_kayit"], 11)
        self.assertIn("duzey_basligi_var_kriter_metni_bos_mevcut_kayit", source)
        self.assertNotIn("duzey_basligi_var_kriter_metni_bos_duzeyler", source)
        self.assertRegex(
            source,
            r"@media\(max-width:760px\)\{[^}]*body\{padding-top:0!important\}[^}]*\.site-header\{display:none!important;min-height:0\}[^}]*\.app\{padding-top:0!important\}"
        )

    def test_arac3_initializes_embedded_data_and_mobile_controls(self):
        source = HTML.read_text(encoding="utf-8")
        self.assertIn("const mappingReady=Array.isArray(ARAC3_MAPPING_DATA.kayitlar)", source)
        self.assertIn("new Map(mappingReady?ARAC3_MAPPING_DATA.kayitlar.map", source)
        self.assertNotIn("apply();loadMapping();", source)
        self.assertNotIn("Ek-1 kriter verisi yükleniyor", source)
        self.assertIn("182 hastalık kaydı ve Ek-1 düzeyleri bu sayfanın içinde sabit veridir", source)
        self.assertNotIn('class="back"', source)
        self.assertIn('id="siteAccessibilityToggle"', source)
        self.assertIn('id="siteAccessibilityPanel"', source)
        self.assertIn('grid-template-areas:"brand home" "tools tools"', source)
        self.assertIn(".site-accessibility-panel.open{display:flex;flex-direction:column}", source)

    def test_mapping_is_embedded_and_does_not_depend_on_api(self):
        source = HTML.read_text(encoding="utf-8")
        self.assertIn("const ARAC3_MAPPING_DATA=", source)
        self.assertNotIn("fetch('/api/arac3/eslestirme'", source)
        self.assertIn("182 hastalık kaydı ve Ek-1 düzeyleri bu sayfanın içinde sabit veridir", source)
        self.assertIn("mappingLoadError", source)
        embedded = re.search(r"const ARAC3_MAPPING_DATA=(\{.*?\});\nconst mappingReady", source)
        self.assertIsNotNone(embedded, "Araç 3 gömülü eşleştirme verisi bulunamadı")
        data = json.loads(embedded.group(1))
        self.assertEqual(len(data["kayitlar"]), 182)
        self.assertEqual(data["ozet"]["mevcut_kayit_sayisi"], 182)

    def test_disease_specific_level_selection_ui(self):
        source = HTML.read_text(encoding="utf-8")
        self.assertIn("function orderedLevels(m)", source)
        self.assertIn("function renderLevelPicker(d,m)", source)
        self.assertIn("data-level=", source)
        self.assertIn("Seçilen düzey:", source)
        self.assertIn("entry.levelKey", source)
        self.assertIn("Her hastalık için yalnızca seçilen düzeyin kriteri gösterilir", source)
        self.assertIn("Bu düzey başlığı kaynak veride bulunuyor ancak kriter metni boş", source)
        self.assertIn("function levelIsSelectable(level)", source)
        self.assertIn("level.secim_izinli===true", source)

        mapping_path = Path(__file__).parent / "arac3" / "arac3_182_ek1_eslestirme.json"
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        by_name = {row["mevcut_hastalik_adi"]: row for row in data["kayitlar"]}

        new_bladder = by_name["Yeni mesane yapılması"]["duzeyler"]
        self.assertEqual([level["anahtar"] for level in new_bladder], ["agir", "orta"])
        self.assertNotEqual(new_bladder[0]["kriter"], new_bladder[1]["kriter"])

        neurogenic_bladder = by_name["Nörojenik mesane"]["duzeyler"]
        self.assertEqual([level["anahtar"] for level in neurogenic_bladder], ["orta"])

        copd = by_name["Kronik pulmoner yetmezlik"]["duzeyler"]
        self.assertEqual([level["anahtar"] for level in copd], ["agir", "orta", "hafif"])
        self.assertEqual(len({level["kriter"] for level in copd}), 3)

    def test_cognitive_mild_criterion_excludes_kds_table(self):
        mapping_path = Path(__file__).parent / "arac3" / "arac3_182_ek1_eslestirme.json"
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        row = next(item for item in data["kayitlar"] if item["mevcut_kayit_id"] == "MEVCUT-004")
        mild = next(level for level in row["duzeyler"] if level["anahtar"] == "hafif")
        self.assertEqual(
            mild["kriter"],
            "Hafif düzey bilişsel bozukluk; klinik kognitif değerlendirme skoru 4-5 ve minimental test skoru 22 ila 25 arası olmalıdır."
        )
        self.assertNotIn("Klinik Kognitif Değerlendirme Skoru (KDS)", mild["kriter"])
        self.assertNotIn("Günlük aktivite:", mild["kriter"])

    def test_empty_criteria_amputation_levels_are_selectable(self):
        mapping_path = Path(__file__).parent / "arac3" / "arac3_182_ek1_eslestirme.json"
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        expected_ids = {
            "MEVCUT-088", "MEVCUT-089", "MEVCUT-090", "MEVCUT-091",
            "MEVCUT-096", "MEVCUT-097",
        }
        flagged = {
            row["mevcut_kayit_id"]
            for row in data["kayitlar"]
            for level in (row.get("duzeyler") or [])
            if level.get("secim_izinli") is True
        }
        self.assertEqual(flagged, expected_ids)

        by_id = {row["mevcut_kayit_id"]: row for row in data["kayitlar"]}
        for record_id in expected_ids:
            row = by_id[record_id]
            self.assertFalse(row["kriter_metni_var"], record_id)
            self.assertEqual(row["kriter_metni_bos_duzeyler"], ["Ağır"], record_id)
            self.assertEqual(len(row["duzeyler"]), 1, record_id)
            level = row["duzeyler"][0]
            self.assertEqual(level["anahtar"], "agir", record_id)
            self.assertEqual(level["kriter"], "", record_id)
            self.assertEqual(level["kriter_durumu"], "baslik_var_metin_yok", record_id)

        # Bu 6 kayit disinda secim izni verilmemis olmali.
        self.assertEqual(
            len([level for row in data["kayitlar"] for level in (row.get("duzeyler") or [])
                 if "secim_izinli" in level]),
            6,
        )

    def test_amputation_category_filters_exact_six_diseases(self):
        source = HTML.read_text(encoding="utf-8")
        ids_match = re.search(
            r"const AMPUTASYON_DISEASE_IDS = new Set\(\[(.*?)\]\);",
            source,
            re.S,
        )
        self.assertIsNotNone(ids_match, "Amputasyon kategori kimlik kümesi bulunamadı")
        actual_ids = set(re.findall(r"""['"]([^'"]+)['"]""", ids_match.group(1)))
        expected_ids = {"d088", "d089", "d090", "d091", "d096", "d097"}
        self.assertEqual(actual_ids, expected_ids)
        self.assertIn("function matchesCategory(d, selectedCategory)", source)
        self.assertIn("selectedCategory === 'Amputasyonlar'", source)
        self.assertIn("AMPUTASYON_DISEASE_IDS.has(d.id)", source)
        self.assertIn("diseases.filter(d=>matchesCategory(d,category)", source)

        records_by_id = {record["id"]: record for record in self.records}
        self.assertEqual(set(records_by_id) & expected_ids, expected_ids)
        self.assertTrue(all(
            records_by_id[record_id]["category"] == "Ortopedi ve Travmatolojik Hastalıklar"
            for record_id in expected_ids
        ))
        self.assertEqual(
            [records_by_id[record_id]["name"] for record_id in sorted(expected_ids)],
            [
                "Skapulotorasik (tek taraflı)",
                "Omuz dezartikülasyonu (tek taraflı)",
                "Kol (omuz ile dirsek arası) (tek taraflı)",
                "Dirsek dezartikülasyonu (tek taraflı)",
                "Hemipelvektomi",
                "Kalça dezartikülasyonu (tek taraflı)",
            ],
        )

    def test_arac3_category_pills_match_arac1_and_hide_desktop_home_shortcut(self):
        source = HTML.read_text(encoding="utf-8")
        arac1_path = Path(__file__).parent / "arac1" / "arac1.html"
        arac1 = arac1_path.read_text(encoding="utf-8")

        # Araç 1'deki branş/kategori kapsüllerinin temel ölçü ve renkleri.
        for rule in (
            ".cipler{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;padding:4px 0 14px;overflow:visible}",
            ".cip{min-width:0;width:100%;border:1px solid #d5e2f2;background:#fff;color:#172642;padding:8px 8px;border-radius:999px;font-size:13px;line-height:1.25;font-family:inherit;cursor:pointer;white-space:normal;overflow-wrap:anywhere}",
            '.cip[aria-pressed="true"]{background:#dceeff;border-color:#78baff;color:#064eb5;font-weight:700}',
        ):
            self.assertIn(rule, arac1)

        self.assertIn(
            ".chips{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;padding:4px 0 14px;overflow:visible}",
            source,
        )
        self.assertIn(
            ".chip{min-width:0;width:100%;border:1px solid #d5e2f2;background:#fff;color:#172642;padding:8px 8px;border-radius:999px;font-size:13px;line-height:1.25;font-family:inherit;cursor:pointer;white-space:normal;overflow-wrap:anywhere}",
            source,
        )
        self.assertIn(
            '.chip[aria-pressed="true"],.chip.on{background:#dceeff;border-color:#78baff;color:#064eb5;font-weight:700}',
            source,
        )

        categories_line = next(line for line in source.splitlines() if line.startswith("const categories="))

        categories = re.findall(r"'([^']+)'", categories_line)
        self.assertEqual(len(categories), 17)
        self.assertIn("Kalp Hastalıkları", categories)
        self.assertIn("Amputasyonlar", categories)

        # Yalnızca scroll ile açılan masaüstü kısayolu kaldırılmalı;
        # dar ekranda kullanılan başlık bağlantısı korunmalı.
        self.assertNotIn('<a class="site-scroll-home"', source)
        self.assertNotIn('document.querySelector(".site-scroll-home")', source)
        self.assertIn('<a class="site-mobile-home"', source)
        self.assertIn('grid-template-areas:"brand home" "tools tools"', source)

    def test_expected_fas_connections(self):
        expected = {
            "Parapleji/Paraparezi, Monopleji/Monoparezi, Hemipleji/Hemiparezi, Kuadripleji/Kuadriparezi vb. motor kaybı olanlar",
            "Parkinson sendromu",
            "Benign beyin tümörleri",
            "Serebral palsi",
            "Spinal kord; sinir kökü lezyonları, dejeneratif nörolojik hastalıklar veya herhangi bir nedene bağlı",
            "Multiple skleroz",
            "Poliomyelit",
            "Müsküler distrofi ile birlikte",
            "Periferal nöropatiler ile birlikte",
            "Tedaviye rağmen anlamlı düzelme göstermeyen subakut kombine kord dejenerasyonu (Pernisiyöz anemi vb ile birlikte)",
            "Serebral travma",
            "Huntington Koresi, Syringomyeli, Friedrich ataksisi, Wilson hastalığı, Jeneralize distoni gibi dejeneratif ve akkiz/herediter hastalıklar, Spino-serebellar dejenerasyon veya Serebellar hastalıklar",
            "Eklemlerin majör disfonksiyonları",
            "Sistemik skleroz (skleroderma)",
            "Raynaud fenomeni",
            "Polimiyozit ve Dermatomiyozit",
            "İnflamatuar artritler",
            "Ankilozan spondilit veya diğer spondiloartropatilerde (omurga tutulumunda)",
        }
        actual = {record["name"] for record in self.records if record["hasFas"]}
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()


