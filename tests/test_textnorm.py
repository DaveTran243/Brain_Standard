"""M0 gate: Vietnamese text matches whether typed with diacritics, without them, or in decomposed (NFD) form."""
from __future__ import annotations

import sys
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_brain import BrainTestCase  # noqa: E402

from brain import drive, kgcore, textnorm  # noqa: E402

WITH = "Thư viện Johnny Decimal của Đức"
WITHOUT = "thu vien johnny decimal cua duc"
NFD = unicodedata.normalize("NFD", WITH)


class FoldTest(unittest.TestCase):
    def test_three_spellings_fold_alike(self):
        self.assertNotEqual(WITH, NFD)                       # the input really is decomposed
        self.assertEqual(textnorm.fold(WITH), WITHOUT)
        self.assertEqual(textnorm.fold(NFD), WITHOUT)
        self.assertEqual(textnorm.fold(WITHOUT), WITHOUT)

    def test_d_with_stroke_and_case(self):
        self.assertEqual(textnorm.fold("ĐƯỜNG đi"), "duong di")
        self.assertEqual(textnorm.fold("PARA"), "para")

    def test_every_vietnamese_vowel_folds_to_ascii(self):
        vowels = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ"
        for v in vowels + vowels.upper():
            self.assertTrue(textnorm.fold(v).isascii(), v)

    def test_nfc_composes(self):
        self.assertEqual(textnorm.nfc(NFD), WITH)

    def test_words_drop_stop_words_given_with_diacritics(self):
        self.assertEqual(textnorm.words(WITH, stop=["của"]), ["thu", "vien", "johnny", "decimal", "duc"])
        self.assertEqual(textnorm.words(NFD, stop=["cua"]), textnorm.words(WITH, stop=["của"]))

    def test_drive_uses_the_shared_fold(self):
        self.assertIs(drive.fold, textnorm.fold)


class GraphMatchTest(unittest.TestCase):
    def setUp(self):
        self.index = kgcore.GraphIndex([
            {"s": "thư viện", "p": "links to", "o": "johnny decimal"},
            {"s": "đường đi", "p": "links to", "o": "thư viện"},
        ])

    def test_entity_found_with_without_and_nfd(self):
        for q in ("thư viện ở đâu", "thu vien o dau", unicodedata.normalize("NFD", "Thư viện ở đâu")):
            self.assertIn("thư viện", kgcore.match_entities(self.index, q), q)

    def test_d_with_stroke_matches(self):
        self.assertIn("đường đi", kgcore.match_entities(self.index, "duong di nao"))

    def test_names_are_not_changed(self):
        self.assertTrue(all(not n.isascii() or n == "johnny decimal" for n in self.index.adjacency))


class WhereTest(BrainTestCase):
    def test_where_ignores_diacritics_and_nfd(self):
        want = ["vien", "nghien", "cuu", "duc"]                  # "thu" is a stop word of brain where
        self.assertEqual(drive.tokens("Thư viện nghiên cứu Đức"), want)
        self.assertEqual(drive.tokens("thu vien nghien cuu duc"), want)
        self.assertEqual(drive.tokens(unicodedata.normalize("NFD", "Thư viện nghiên cứu Đức")), want)


if __name__ == "__main__":
    unittest.main()
