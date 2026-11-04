import json
import re
from pathlib import Path
import unittest


HTML = Path(__file__).with_name("arac3.html")


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
