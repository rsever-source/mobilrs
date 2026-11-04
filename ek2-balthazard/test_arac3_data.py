import json
import re
from pathlib import Path
import unittest


HTML = Path(__file__).parent / "arac3" / "arac3.html"


class Arac3DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = HTML.read_text(encoding="utf-8")
        cls.html = source
        match = re.search(r"const diseases=(\[.*?\]);\nlet category", source)
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

    def test_fas_guide_contains_all_user_selectable_levels(self):
        for level in range(6):
            self.assertIn(f"{level}:{{description:", self.html)
        self.assertIn("otomatik atama yapılmaz", self.html)

    def test_fas_guide_indicators_match_source(self):
        expected = {
            0: ("Yürüyemez veya iki kişinin yardımına ihtiyaç duyar.", "Ağır"),
            1: ("Sürekli fiziksel desteğe ihtiyaç duyar.", "Ağır"),
            2: ("Aralıklı veya hafif dokunarak yardıma ihtiyaç duyar.", "Ağır"),
            3: ("Gözetim veya sözel yönlendirme gerekir.", "Orta"),
            4: ("Eğim/merdivende yardım gerekir.", "Hafif"),
            5: ("Her zeminde bağımsız yürür.", "Etkilemez"),
        }
        for level, (description, indicator) in expected.items():
            self.assertIn(f"{level}:{{description:'{description}',indicator:'{indicator}'", self.html)

    def test_fas_state_is_per_record_and_removed_with_record(self):
        self.assertIn("const fasLevels={};", self.html)
        self.assertIn("fasLevels[input.closest('.fas-picker').dataset.fasId]=Number(input.value)", self.html)
        self.assertIn("delete fasLevels[id]", self.html)

    def test_non_fas_records_do_not_render_fas_picker(self):
        self.assertIn("if(!d.hasFas)return ''", self.html)
        self.assertIn("(d.hasFas?fasPicker(d,'selected'):'')", self.html)

    def test_fas_display_is_informational_not_a_percentage_or_balthazard_result(self):
        self.assertIn("FAS seçimi kullanıcı tarafından bilgi amaçlı yapılır", self.html)
        self.assertIn("Seçilen maddeler için Balthazard hesabı yapılmaz", self.html)
        self.assertNotIn("fasLevels[input.closest('.fas-picker').dataset.fasId]=Number(input.value)*", self.html)

    def test_kds_marker_remains_independent(self):
        self.assertIn("d.calculator?'<span class=\"tag\">KDS hesaplayıcısı</span>'", self.html)
        self.assertIn("d.calculator?'<span class=\"tag\">KDS bağlantısı</span>'", self.html)

    def test_official_source_and_fas_indicator_labels_are_visible(self):
        self.assertIn("Resmî kaynak: 28.09.2021 tarihli Resmî Gazete", self.html)
        self.assertIn("FAS '+input.value+' · '+fasGuide[input.value].indicator", self.html)

    def test_ek1_levels_are_rendered_for_search_results_and_selected_diseases(self):
        self.assertIn("function ek1DuzeyHTML(d)", self.html)
        self.assertIn("'+ek1DuzeyHTML(d)", self.html)
        self.assertIn("EK-1 çalışma gücü kaybı düzeyi", self.html)

    def test_neurogenic_bladder_has_only_medium_level_and_reevaluation_note(self):
        start = self.html.index("'Nörojenik mesane':{")
        end = self.html.index("},\n  'Lepra':", start)
        record = self.html[start:end]
        self.assertIn("ad:'Orta Düzey'", record)
        self.assertNotIn("Ağır Düzey", record)
        self.assertNotIn("Hafif Düzey", record)
        self.assertIn("2 yıl sonra yeniden değerlendirilir.", record)
        self.assertIn("devamlı sonda ya da TAK", record)

    def test_single_level_and_multi_level_diseases_are_not_filled_with_missing_levels(self):
        lepra_start = self.html.index("'Lepra':{")
        lepra_end = self.html.index("},\n  'Polimiyozit", lepra_start)
        lepra = self.html[lepra_start:lepra_end]
        self.assertIn("ad:'Ağır Düzey'", lepra)
        self.assertNotIn("Orta Düzey", lepra)
        self.assertNotIn("Hafif Düzey", lepra)
        polymyositis_start = self.html.index("'Polimiyozit ve Dermatomiyozit':{")
        polymyositis_end = self.html.index("\n};\nfunction ek1DuzeyHTML", polymyositis_start)
        polymyositis = self.html[polymyositis_start:polymyositis_end]
        for level in ("Ağır Düzey", "Orta Düzey", "Hafif Düzey"):
            self.assertIn(level, polymyositis)

    def test_all_tool_pages_link_to_arac3(self):
        for path in ("arac1", "arac2"):
            source = (HTML.parent.parent / path / f"{path}.html").read_text(encoding="utf-8")
            self.assertIn('href="/arac3">Çalışma Gücü Kaybı</a>', source)


if __name__ == "__main__":
    unittest.main()



