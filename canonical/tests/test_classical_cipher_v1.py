"""Admission tests for the classical-cipher capability.

Victims are REAL English prose from this repository's docs (not synthetic
letter soup, not benchmark data), encrypted with fresh keys. A capability
that cannot recover unseen Vigenere-family specimens is NOT admitted.
"""
from __future__ import annotations

import random
import re
import unittest
import pathlib
from collections import Counter

from canonical.runtime import classical_cipher_v1 as cc

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _prose_slices(n_slices: int, min_len: int = 700):
    blobs = []
    seen = set()
    for p in sorted(ROOT.rglob("*.md")):
        if len(blobs) >= n_slices:
            break
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        letters = re.sub(r"[^A-Za-z]", "", t).upper()
        for start in (0, len(letters) // 2):
            blob = letters[start:start + min_len]
            if len(blob) >= min_len and blob not in seen:
                seen.add(blob)
                blobs.append(blob)
                break
    return blobs


class ClassicalCipherTests(unittest.TestCase):
    def test_ioc_separates_english_from_vigenere(self):
        text = "A" * 100
        self.assertAlmostEqual(cc.ioc(""), 0.0)
        eng = re.sub(r"[^A-Za-z]", "", (ROOT / "README.md").read_text(errors="ignore")).upper()[:3000] \
            if (ROOT / "README.md").exists() else "THEQUICKBROWNFOX" * 100
        self.assertGreater(cc.ioc(eng), 0.055)
        rng = random.Random(7)
        rnd = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(2000))
        self.assertLess(cc.ioc(rnd), 0.045)

    def test_stats_file_is_inspectable_and_provenanced(self):
        stats = cc.load_stats()
        self.assertIn("provenance", stats)
        self.assertEqual(len(stats["monogram"]), 26)
        self.assertGreater(len(stats["bigram"]), 100)

    def test_unseen_standard_vigenere_recovered(self):
        victims = []
        rng = random.Random(20261124)
        for i, blob in enumerate(_prose_slices(6)):
            key = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(rng.choice([4, 6, 9])))
            victims.append({"name": f"prose-{i}", "plaintext": blob, "variant": "vigenere", "key": key})
        out = cc.admission(victims)
        self.assertGreaterEqual(int(out["plaintext_recovery"].split("/")[0]), 4, msg=str(out))

    def test_unseen_interleaved_vigenere_recovered(self):
        victims = []
        rng = random.Random(90210)
        for i, blob in enumerate(_prose_slices(4, min_len=800)):
            key = ("KINGDOM|QUEST" if i % 2 == 0 else "CIPHER|SHADOW")
            victims.append({"name": f"interp-{i}", "plaintext": blob,
                            "variant": "interleaved2", "key": key})
        out = cc.admission(victims)
        self.assertGreaterEqual(int(out["plaintext_recovery"].split("/")[0]), 2, msg=str(out))


if __name__ == "__main__":
    unittest.main()
