from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch
import zipfile
from hashlib import sha256

from canonical.runtime import oewn_release_sense_universe_v1 as oewn


def build_zip(*, missing_synset=False, unsafe=False, duplicate_sense=False):
    entries = {
        "margin": {
            "n": {
                "sense": [
                    {"id": "margin%1:21:01::", "synset": "10000001-n"},
                    {"id": "margin%1:21:02::", "synset": "10000002-n"},
                ]
            }
        },
        "run": {
            "v": {"sense": [{"id": "run%2:38:00::", "synset": "20000001-v"}]}
        },
    }
    if duplicate_sense:
        entries["margin"]["n"]["sense"].append(
            {"id": "margin%1:21:01::", "synset": "10000003-n"}
        )

    noun = {
        "10000001-n": {
            "definition": ["profit sense"],
            "members": ["margin", "gross profit margin"],
            "partOfSpeech": "n",
        },
        "10000002-n": {
            "definition": ["collateral sense"],
            "members": ["margin", "security deposit"],
            "partOfSpeech": "n",
        },
    }
    if duplicate_sense:
        noun["10000003-n"] = {
            "definition": ["duplicate sense id target"],
            "members": ["margin"],
            "partOfSpeech": "n",
        }
    if missing_synset:
        del noun["10000002-n"]

    verb = {
        "20000001-v": {
            "definition": ["move quickly"],
            "members": ["run"],
            "partOfSpeech": "v",
        }
    }
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("entries-m.json", json.dumps(entries))
        z.writestr("entries-a.json", json.dumps({}))
        z.writestr("noun.possession.json", json.dumps(noun))
        z.writestr("verb.motion.json", json.dumps(verb))
        z.writestr("frames.json", json.dumps({}))
        if unsafe:
            z.writestr("../escape.json", "{}")
    return bio.getvalue()


def run_with_fixture(raw, lemma, pos=None):
    with patch.object(oewn, "RELEASE_SHA256", sha256(raw).hexdigest()):
        return oewn.enumerate_senses(raw, lemma, part_of_speech=pos)


class Tests(unittest.TestCase):
    def test_wrong_archive_hash_fails_closed(self):
        out = oewn.enumerate_senses(build_zip(), "margin", part_of_speech="n")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__OEWN_2025_RELEASE_HASH_MISMATCH",
        )
        self.assertFalse(out["candidate_set_complete_relative_to_release"])

    def test_exact_lemma_enumerates_every_sense_without_selecting_one(self):
        raw = build_zip()
        out = run_with_fixture(raw, " Margin ", "n")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["sense_count"], 2)
        self.assertEqual(
            {x["synset_id"] for x in out["senses"]},
            {"10000001-n", "10000002-n"},
        )
        self.assertTrue(out["candidate_set_complete_relative_to_release"])
        self.assertFalse(out["intended_sense_identified"])
        self.assertFalse(out["open_world_english_sense_completeness_claimed"])

    def test_pos_filter_is_exact(self):
        raw = build_zip()
        out = run_with_fixture(raw, "run", "v")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["sense_count"], 1)
        self.assertEqual(out["senses"][0]["part_of_speech"], "v")

    def test_absent_lemma_is_release_relative_absence_only(self):
        raw = build_zip()
        out = run_with_fixture(raw, "not-in-release", "n")
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["release_relative_absence"])
        self.assertEqual(out["sense_count"], 0)
        self.assertTrue(out["candidate_set_complete_relative_to_release"])
        self.assertFalse(out["open_world_english_sense_completeness_claimed"])

    def test_missing_referenced_synset_fails_closed(self):
        raw = build_zip(missing_synset=True)
        out = run_with_fixture(raw, "margin", "n")
        self.assertFalse(out["pass"])
        self.assertIn("REFERENCED_SYNSET_MISSING", out["reason"])

    def test_duplicate_sense_id_fails_closed(self):
        raw = build_zip(duplicate_sense=True)
        out = run_with_fixture(raw, "margin", "n")
        self.assertFalse(out["pass"])
        self.assertIn("DUPLICATE_SENSE_ID", out["reason"])

    def test_unsafe_zip_member_fails_closed(self):
        raw = build_zip(unsafe=True)
        out = run_with_fixture(raw, "margin", "n")
        self.assertFalse(out["pass"])
        self.assertIn("ZIP_UNSAFE_MEMBER", out["reason"])

    def test_synset_must_actually_contain_lemma(self):
        raw = build_zip()
        src = io.BytesIO(raw)
        outbuf = io.BytesIO()
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(outbuf, "w") as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "noun.possession.json":
                    obj = json.loads(data)
                    obj["10000002-n"]["members"] = ["security deposit"]
                    data = json.dumps(obj).encode()
                zout.writestr(info.filename, data)
        bad = outbuf.getvalue()
        out = run_with_fixture(bad, "margin", "n")
        self.assertFalse(out["pass"])
        self.assertIn("SYNSET_DOES_NOT_CONTAIN_LEMMA", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
