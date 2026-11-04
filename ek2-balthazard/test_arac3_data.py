import json
import re
from pathlib import Path
import unittest


HTML = Path(__file__).parent / "arac3" / "arac3.html"


class Arac3DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = HTML.read_text(encoding="utf-8")
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


