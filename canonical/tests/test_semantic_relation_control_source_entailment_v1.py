import hashlib
import unittest

from canonical.runtime.bounded_semantic_relation_proof_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
)
from canonical.runtime.semantic_relation_control_v1 import resolve


SCOPE = "finance:policy:2026"


def span(source_id, text, scope=SCOPE):
    return {
        "source_id": source_id,
        "scope_id": scope,
        "span_text": text,
        "span_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def bounded(left_members, right_members, universe=("a", "b", "c")):
    e = {
        "schema": EVIDENCE_SCHEMA,
        "scope_id": SCOPE,
        "left_id": "L",
        "right_id": "R",
        "universe_complete": True,
        "left_extension_complete": True,
        "right_extension_complete": True,
        "universe": list(universe),
        "left_members": list(left_members),
        "right_members": list(right_members),
    }
    return e, evidence_sha256(e)


class Tests(unittest.TestCase):
    def test_source_chain_proves_direction_without_complete_denotation_universe(self):
        out = resolve({
            "left_id": "L",
            "right_id": "R",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_entailment_spans": [
                span("doc:A", "Every reserve buffer is a liquidity reserve."),
                span("doc:B", "Every liquidity reserve is a liquidity cushion."),
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertFalse(out["bounded_extension_proof"]["available"])

    def test_mutual_source_paths_prove_scoped_logical_equivalence_not_identity(self):
        out = resolve({
            "left_id": "L",
            "right_id": "R",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "source_entailment_spans": [
                span("doc:A", "Every reserve buffer is a liquidity reserve."),
                span("doc:B", "Every liquidity reserve is a liquidity cushion."),
                span("doc:C", "Every liquidity cushion is a reserve buffer."),
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["proved_facts"]["logical_equivalence_in_scope"])
        self.assertFalse(out["proved_facts"]["semantic_identity"])

    def test_source_counterexample_can_prove_required_direction_false(self):
        out = resolve({
            "left_id": "L",
            "right_id": "R",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "source_entailment_spans": [
                span("doc:A", "Some reserve buffer is not a liquidity cushion."),
            ],
        })
        self.assertFalse(out["pass"])
        self.assertTrue(out["required_relation_disproved"])
        self.assertEqual(
            out["status"],
            "PROVED__REQUIRED_SEMANTIC_RELATION_FALSE_IN_BOUND_SCOPE",
        )

    def test_bounded_positive_and_source_counterexample_conflict_fail_closed(self):
        e, digest = bounded(("a",), ("a", "b"))
        out = resolve({
            "left_id": "L",
            "right_id": "R",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "bounded_extension_evidence": e,
            "expected_bounded_extension_sha256": digest,
            "source_entailment_spans": [
                span("doc:A", "Some reserve buffer is not a liquidity cushion."),
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SEMANTIC_EVIDENCE_CHANNEL_CONFLICT",
        )

    def test_source_positive_and_bounded_counterexample_conflict_fail_closed(self):
        e, digest = bounded(("a", "b"), ("a",))
        out = resolve({
            "left_id": "L",
            "right_id": "R",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "LEFT_ENTAILS_RIGHT",
            "bounded_extension_evidence": e,
            "expected_bounded_extension_sha256": digest,
            "source_entailment_spans": [
                span("doc:A", "Every reserve buffer is a liquidity cushion."),
            ],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SEMANTIC_EVIDENCE_CHANNEL_CONFLICT",
        )

    def test_semantic_nonidentity_can_still_be_current_decision_substitution(self):
        out = resolve({
            "left_id": "L",
            "right_id": "R",
            "left_surface": "reserve buffer",
            "right_surface": "liquidity cushion",
            "scope_id": SCOPE,
            "required_relation": "CURRENT_DECISION_SUBSTITUTION",
            "source_entailment_spans": [
                span("doc:A", "Some reserve buffer is not a liquidity cushion."),
            ],
            "terminal_signature_rows": [
                {
                    "raw_id": "L",
                    "signature_complete": True,
                    "terminal_signature": {"action": "REDUCE"},
                },
                {
                    "raw_id": "R",
                    "signature_complete": True,
                    "terminal_signature": {"action": "REDUCE"},
                },
            ],
        })
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["proved_facts"]["current_decision_substitution"])
        self.assertFalse(out["proved_facts"]["left_entails_right"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
