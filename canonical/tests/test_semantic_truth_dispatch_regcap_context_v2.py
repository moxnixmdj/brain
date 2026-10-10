import unittest

from canonical.runtime.semantic_truth_dispatch_v1 import evaluate


class Tests(unittest.TestCase):
    def payload(self, text):
        return {
            "truth_kind": "REGCAP_CONTEXT_ATOM",
            "predicate_id": "caller-label",
            "source_text": text,
            "source_id": "doc:A",
            "start": 0,
            "end": len(text),
            "context_kind": "CERTIFIED_REGCAP_CCYB_RELEASE_CONTEXT",
            "target_atom_id": "RELEASE::SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
        }

    def test_dispatch_uses_v2_for_canonical_positive_release(self):
        text = "This cushion is released when system-wide risk crystallizes or dissipates."
        out = evaluate(self.payload(text))
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["schema"],
            "PROJECT_BRAIN_REGCAP_CONTEXT_ATOM_TRUTH_CERTIFICATE_V2",
        )
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_dispatch_rejects_weaker_negated_and_attributed_forms(self):
        cases = [
            "The cushion is released when system-wide risk dissipates.",
            "The cushion is not released when system-wide risk crystallises or dissipates.",
            "Analysts claim the cushion is released when system-wide risk crystallises or dissipates.",
        ]
        for text in cases:
            with self.subTest(text=text):
                out = evaluate(self.payload(text))
                self.assertFalse(out["pass"], out)
                self.assertEqual(out["predicate_truth"], "UNKNOWN")
                self.assertFalse(out["truthful_precommitment_observation"])
                self.assertFalse(out["semantic_truth_authority"])
                self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
