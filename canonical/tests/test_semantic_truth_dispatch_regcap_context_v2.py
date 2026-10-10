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

    def test_dispatch_uses_v2_for_positive_release(self):
        text = "the cushion is released when system-wide risk dissipates"
        out = evaluate(self.payload(text))
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["schema"],
            "PROJECT_BRAIN_REGCAP_CONTEXT_ATOM_TRUTH_CERTIFICATE_V2",
        )
        self.assertEqual(out["predicate_truth"], "TRUE")

    def test_dispatch_rejects_negated_positive_substring(self):
        text = "the cushion is not released when system-wide risk dissipates"
        out = evaluate(self.payload(text))
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["schema"],
            "PROJECT_BRAIN_REGCAP_CONTEXT_ATOM_TRUTH_CERTIFICATE_V2",
        )
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertFalse(out["truthful_precommitment_observation"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_dispatch_rejects_attributed_positive_substring(self):
        text = "analysts claim the cushion is released when system-wide risk dissipates"
        out = evaluate(self.payload(text))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
