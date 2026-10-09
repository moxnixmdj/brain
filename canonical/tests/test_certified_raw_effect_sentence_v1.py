from __future__ import annotations
import unittest

from canonical.runtime import certified_raw_effect_sentence_v1 as c


class CertifiedRawEffectSentenceV1Tests(unittest.TestCase):
    def test_define(self):
        out=c.compile_sentence(
            "Effect A.t defines threshold as 10.",
            document_id="A",
            slot_id="A.effect",
        )
        self.assertTrue(out["pass"],out)
        effect=out["slot"]["hypotheses"][0]["effect"]
        self.assertEqual(effect["effect_class"],"DEFINE")
        self.assertEqual(effect["target_id"],"threshold")
        self.assertEqual(effect["value"],10)
        self.assertEqual(effect["supersedes"],[])
        self.assertIsNone(effect["valid_from"])

    def test_replace_with_effective_date(self):
        out=c.compile_sentence(
            "Effect B.t replaces A.t on threshold with 12 effective 2026-07-01.",
            document_id="B",
            slot_id="B.effect",
        )
        self.assertTrue(out["pass"],out)
        effect=out["slot"]["hypotheses"][0]["effect"]
        self.assertEqual(effect["effect_class"],"REPLACE")
        self.assertEqual(effect["supersedes"],["A.t"])
        self.assertEqual(effect["valid_from"],"2026-07-01")

    def test_exception_with_typed_condition(self):
        out=c.compile_sentence(
            "Effect C.t excepts B.t on threshold with 8 when small = true effective 2026-07-01.",
            document_id="C",
            slot_id="C.effect",
        )
        self.assertTrue(out["pass"],out)
        effect=out["slot"]["hypotheses"][0]["effect"]
        self.assertEqual(effect["effect_class"],"EXCEPTION")
        self.assertEqual(effect["conditions"],{"small":True})
        self.assertEqual(effect["value"],8)

    def test_override_string_value(self):
        out=c.compile_sentence(
            'Effect D.t overrides C.t on tier with "gold".',
            document_id="D",
            slot_id="D.effect",
        )
        self.assertTrue(out["pass"],out)
        effect=out["slot"]["hypotheses"][0]["effect"]
        self.assertEqual(effect["effect_class"],"OVERRIDE")
        self.assertEqual(effect["value"],"gold")

    def test_unrecognized_sentence_remains_top(self):
        out=c.compile_sentence(
            "The threshold should probably become twelve next summer.",
            document_id="B",
            slot_id="B.effect",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRECOGNIZED__RETAIN_SOURCE_TOP")

    def test_near_miss_wording_is_not_silently_normalized(self):
        out=c.compile_sentence(
            "Effect B.t changes A.t on threshold to 12 effective 2026-07-01.",
            document_id="B",
            slot_id="B.effect",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRECOGNIZED__RETAIN_SOURCE_TOP")

    def test_invalid_calendar_date_fails_closed(self):
        out=c.compile_sentence(
            "Effect B.t replaces A.t on threshold with 12 effective 2026-02-30.",
            document_id="B",
            slot_id="B.effect",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("ValueError:",out["reason"])
        self.assertIn("2026",out["reason"])

    def test_non_scalar_json_is_not_accepted(self):
        out=c.compile_sentence(
            "Effect A.t defines threshold as [10].",
            document_id="A",
            slot_id="A.effect",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"UNRECOGNIZED__RETAIN_SOURCE_TOP")

    def test_multiline_region_fails_closed(self):
        out=c.compile_sentence(
            "Effect A.t defines threshold as 10.\nEffect X.t defines x as 1.",
            document_id="A",
            slot_id="A.effect",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("SINGLE_LINE",out["reason"])


if __name__=="__main__":
    unittest.main()
