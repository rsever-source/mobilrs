# -*- coding: utf-8 -*-
"""Araç 3 arama testleri.

Kapsam:
- 182 kaydın tamamı için alias verisi bütünlüğü (resmî ad/kimlik değişmezliği dâhil).
- Her alias'ın kendi kaydını bulması (182 kayıt × alias sayısı).
- Her resmî adın ve ayırt edici kelimesinin kaydı bulması.
- Kelime içinden eşleşme yasağı: kelimenin ilk harfi atılmış parçalar kaydı getirmemeli.
- Türkçe karakter, büyük/küçük harf, boşluk ve tire toleransı.
- Bilinen yanlış eşleşme tuzakları ("inme", "MS", "as", "kol" vb.).
- Sayfadaki JavaScript aramasının bu Python referansıyla birebir aynı sonucu vermesi.
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


HTML = Path(__file__).parent / "arac3" / "arac3.html"
MAPPING = Path(__file__).parent / "arac3" / "arac3_182_ek1_eslestirme.json"

DISEASES_PATTERN = re.compile(r"const diseases=(\[.*?\]);\nconst ARAC3_MAPPING_DATA=", re.S)

_TR_FOLD = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "â": "a", "î": "i", "û": "u",
    "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u",
})


def fold(value):
    """Sayfadaki arac3Fold ile aynı normalizasyon."""
    value = str(value).replace("İ", "i").replace("I", "ı").lower().translate(_TR_FOLD)
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    return re.sub(r"\s+", " ", value)


def query_tokens(value):
    folded = fold(value)
    return folded.split(" ") if folded else []


def record_tokens(record):
    parts = [record["name"]] + list(record.get("aliases") or [])
    return set(query_tokens(" ".join(parts)))


def matches(record, query):
    tokens = query_tokens(query)
    if not tokens:
        return True
    record_token_set = record_tokens(record)
    return all(token in record_token_set for token in tokens)


def search(records, query):
    return [record for record in records if matches(record, query)]


class Arac3SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = HTML.read_text(encoding="utf-8")
        match = DISEASES_PATTERN.search(cls.source)
        if not match:
            raise AssertionError("Araç 3 veri dizisi bulunamadı")
        cls.records = json.loads(match.group(1))
        cls.by_id = {record["id"]: record for record in cls.records}
        cls.mapping = json.loads(MAPPING.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ veri

    def test_all_182_records_have_alias_data(self):
        self.assertEqual(len(self.records), 182)
        self.assertEqual([record["id"] for record in self.records],
                         ["d%03d" % number for number in range(1, 183)])
        total = 0
        for record in self.records:
            aliases = record.get("aliases")
            self.assertIsInstance(aliases, list, record["id"])
            self.assertTrue(aliases, record["id"])
            name_fold = fold(record["name"])
            seen = set()
            for alias in aliases:
                self.assertIsInstance(alias, str, record["id"])
                self.assertEqual(alias, alias.strip(), (record["id"], alias))
                folded = fold(alias)
                self.assertTrue(folded, (record["id"], alias))
                self.assertNotEqual(folded, name_fold, (record["id"], alias))
                self.assertGreaterEqual(len(folded), 2, (record["id"], alias))
                self.assertNotIn(folded, seen, (record["id"], alias))
                seen.add(folded)
            total += len(aliases)
        self.assertGreaterEqual(total, 700)

    def test_official_ids_names_and_fields_are_unchanged(self):
        mapping_names = {row["mevcut_kayit_id"]: row["mevcut_hastalik_adi"]
                         for row in self.mapping["kayitlar"]}
        for number, record in enumerate(self.records, start=1):
            self.assertEqual(record["id"], "d%03d" % number)
            self.assertEqual(record["mevcut_kayit_id"] if "mevcut_kayit_id" in record else
                             "MEVCUT-%03d" % number, "MEVCUT-%03d" % number)
            self.assertEqual(record["name"], mapping_names["MEVCUT-%03d" % number])
            self.assertEqual(
                set(record),
                {"id", "name", "category", "aliases", "hasFas", "calculator", "source"},
                record["id"],
            )

    # -------------------------------------------------------------- pozitif

    def test_every_alias_finds_its_own_record(self):
        for record in self.records:
            for alias in record["aliases"]:
                with self.subTest(record=record["id"], alias=alias):
                    ids = [item["id"] for item in search(self.records, alias)]
                    self.assertIn(record["id"], ids)

    def test_every_official_name_finds_its_own_record(self):
        for record in self.records:
            with self.subTest(record=record["id"], query=record["name"]):
                ids = [item["id"] for item in search(self.records, record["name"])]
                self.assertIn(record["id"], ids)

    def test_distinctive_name_word_finds_its_own_record(self):
        for record in self.records:
            tokens = [token for token in query_tokens(record["name"])
                      if len(token) >= 5 and token.isalnum()]
            if not tokens:
                continue
            token = max(tokens, key=len)
            with self.subTest(record=record["id"], token=token):
                ids = [item["id"] for item in search(self.records, token)]
                self.assertIn(record["id"], ids)

    def test_known_synonyms_return_expected_exact_sets(self):
        exact = {
            "sara": {"d001"},
            "grand mal": {"d001"},
            "çocuk felci": {"d013"},
            "ms": {"d011"},
            "as": {"d110"},
            "epilepsi": {"d001", "d002", "d003"},
            "sedef": {"d132"},
            "verem": {"d178"},
            "şeker": {"d173"},
            "diyabet": {"d173"},
            "cüzzam": {"d147"},
            "kelebek": {"d136"},
            "alzheimer": {"d004"},
            "demans": {"d004"},
            "otizm": {"d029"},
            "felç": {"d005", "d009"},
            "kalp krizi": {"d155"},
            "tansiyon": {"d156"},
            "koah": {"d175"},
            "astım": {"d176"},
            "uyku apnesi": {"d177"},
            "hemofili": {"d081"},
            "talasemi": {"d072"},
            "orak": {"d071"},
            "lösemi": {"d078", "d079", "d084"},
            "lenfoma": {"d083", "d128", "d129", "d130"},
            "skleroderma": {"d104", "d146"},
            "behçet": {"d108"},
            "lupus": {"d107"},
            "pku": {"d174"},
            "hiv": {"d182"},
            "çölyak": {"d116"},
            "meme": {"d045"},
            "prostat": {"d059"},
            "testis": {"d060"},
            "nefrotik": {"d163"},
            "gvhd": {"d143"},
            "morfea": {"d146"},
            "glossektomi": {"d035"},
            "larenjektomi": {"d036"},
            "mds": {"d073", "d079"},
            "mpn": {"d078", "d079"},
            "kml": {"d078", "d084"},
        }
        for query, expected in exact.items():
            with self.subTest(query=query):
                actual = {record["id"] for record in search(self.records, query)}
                self.assertEqual(actual, expected)

    def test_generic_terms_cover_the_right_sections(self):
        oncology = {"d%03d" % number for number in range(40, 64)}
        amputations = {"d%03d" % number for number in range(87, 102)}
        transplants = {"d085", "d086", "d113", "d121", "d181"}

        self.assertEqual({record["id"] for record in search(self.records, "kanser")}, oncology)
        self.assertEqual({record["id"] for record in search(self.records, "amputasyon")}, amputations)
        self.assertEqual({record["id"] for record in search(self.records, "transplantasyon")}, transplants)

        tumors = {record["id"] for record in search(self.records, "tümör")}
        self.assertTrue(oncology <= tumors)
        self.assertIn("d008", tumors)
        self.assertIn("d172", tumors)

    # -------------------------------------------------------------- negatif

    def test_no_match_inside_a_word(self):
        """Bir kelimenin ilk harfi atılarak elde edilen parça o kaydı getirmemeli."""
        checked = 0
        for record in self.records:
            candidates = [token for token in query_tokens(record["name"])
                          if len(token) >= 5 and token.isalnum()]
            if not candidates:
                continue
            longest = max(candidates, key=len)
            fragment = longest[1:]
            if len(fragment) < 3 or fragment in record_tokens(record):
                continue
            with self.subTest(record=record["id"], fragment=fragment):
                ids = [item["id"] for item in search(self.records, fragment)]
                self.assertNotIn(record["id"], ids)
            checked += 1
        self.assertGreater(checked, 150)

    def test_known_false_positive_traps(self):
        traps = {
            "inme": set(),
            "epile": set(),
            "kans": set(),
            "tansiyo": set(),
            "şekerli": set(),
            "kalp": {"d156"},
            "beyin": {"d011"},
            "kol": {"d120"},
            "kan": {"d173"},
            "as": {"d001", "d011", "d084"},
            "ms": {"d021", "d084", "d132"},
        }
        for query, forbidden in traps.items():
            with self.subTest(query=query):
                actual = {record["id"] for record in search(self.records, query)}
                self.assertEqual(actual & forbidden, set(), (query, sorted(actual & forbidden)))

        # "inme" hiçbir kaydı getirmemeli; "MS" yalnızca multiple skleroz olmalı.
        self.assertEqual(search(self.records, "inme"), [])
        self.assertEqual([record["id"] for record in search(self.records, "ms")], ["d011"])

    def test_multi_word_queries_require_all_words(self):
        self.assertEqual([record["id"] for record in search(self.records, "kalp krizi")], ["d155"])
        self.assertEqual(search(self.records, "kalp epilepsi"), [])
        self.assertEqual(search(self.records, "verem astım"), [])
        self.assertEqual([record["id"] for record in search(self.records, "kronik böbrek")], ["d162"])

    def test_empty_query_matches_everything(self):
        self.assertEqual(len(search(self.records, "")), 182)
        self.assertEqual(len(search(self.records, "   ")), 182)

    # ------------------------------------------------------------ tolerans

    def test_turkish_case_character_space_and_hyphen_tolerance(self):
        variants = [
            ("EPİLEPSİ", "epilepsi"),
            ("Epilepsi", "epilepsi"),
            ("sizofreni", "şizofreni"),
            ("ŞİZOFRENİ", "şizofreni"),
            ("tuberkuloz", "tüberküloz"),
            ("VEREM", "verem"),
            ("colyak", "çölyak"),
            ("grand-mal", "grand mal"),
            ("GRAND   MAL", "grand mal"),
            ("  grand\tmal  ", "grand mal"),
            ("Tip 1 Diyabet", "tip 1 diyabet"),
            ("astim", "astım"),
            ("şeker hastalığı", "şeker hastalığı"),
            ("şeker-hastalığı", "şeker hastalığı"),
        ]
        for variant, canonical in variants:
            with self.subTest(variant=variant):
                self.assertEqual(
                    [record["id"] for record in search(self.records, variant)],
                    [record["id"] for record in search(self.records, canonical)],
                )

    # --------------------------------------------------------------- sayfa

    def test_search_input_is_wired_to_token_matcher(self):
        for snippet in (
            "function arac3Fold(value)",
            "function arac3SearchTokens(value)",
            "function arac3RecordTokens(d)",
            "function arac3MatchesQuery(d, query)",
            "diseases.filter(d=>matchesCategory(d,category)&&arac3MatchesQuery(d,q))",
            'id="search"',
        ):
            self.assertIn(snippet, self.source)
        # Eski alt dize araması kalmamalı.
        self.assertNotIn(".includes(q)", self.source)
        self.assertNotIn('toLocaleLowerCase(\'tr-TR\').includes', self.source)

    # ---------------------------------------------------------------- JS

    @unittest.skipUnless(shutil.which("node"), "node bulunamadı; JS eşdeğerlik testi atlandı")
    def test_javascript_matcher_agrees_with_python_reference(self):
        block = re.search(
            r"const ARAC3_TR_FOLD = \{.*?return queryTokens\.every\(token=>recordTokens\.has\(token\)\);\n\}",
            self.source,
            re.S,
        )
        self.assertIsNotNone(block, "arama fonksiyonları sayfada bulunamadı")

        queries = set()
        for record in self.records:
            queries.add(record["name"])
            queries.update(record["aliases"])
        queries.update({
            "", "inme", "ms", "MS", "as", "epile", "kans", "tansiyo", "kalp", "beyin",
            "kol", "kan", "grand-mal", "GRAND   MAL", "EPİLEPSİ", "sizofreni", "colyak",
            "kanser", "tümör", "amputasyon", "transplantasyon", "nakil", "  boşluk  ",
        })
        queries = sorted(queries)

        script = block.group(0) + """
const fs = require('fs');
const records = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const queries = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = {};
for (const q of queries) out[q] = records.filter(r=>arac3MatchesQuery(r,q)).map(r=>r.id);
process.stdout.write(JSON.stringify(out));
"""
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "matcher.js").write_text(script, encoding="utf-8")
            (directory / "records.json").write_text(
                json.dumps(self.records, ensure_ascii=False), encoding="utf-8")
            (directory / "queries.json").write_text(
                json.dumps(queries, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                ["node", str(directory / "matcher.js"),
                 str(directory / "records.json"), str(directory / "queries.json")],
                capture_output=True, text=True, encoding="utf-8",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        js_results = json.loads(result.stdout)

        mismatches = []
        for query in queries:
            expected = [record["id"] for record in search(self.records, query)]
            if js_results.get(query) != expected:
                mismatches.append((query, expected[:5], (js_results.get(query) or [])[:5]))
        self.assertEqual(mismatches, [], "JS ve Python arama sonuçları farklı")


if __name__ == "__main__":
    unittest.main()
