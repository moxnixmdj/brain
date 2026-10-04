#!/usr/bin/env python3
import unittest

from canonical.runtime.capability_evidence_observability_v1 import (
    FORMAL_INSTRUCTION_ADHERENCE,
    LIVEBENCH_IF_2026,
    SEMANTIC_PARAPHRASE,
    SEMANTIC_SIMPLIFICATION,
    SEMANTIC_STORY_GENERATION,
    SEMANTIC_SUMMARIZATION,
    UnsupportedCapabilityCredit,
    observable_capabilities,
    require_support,
    semantic_credit_from_livebench_if_only,
    supports,
)


class CapabilityEvidenceObservabilityTests(unittest.TestCase):
    def test_livebench_if_supports_formal_adherence(self):
        self.assertTrue(supports(LIVEBENCH_IF_2026, FORMAL_INSTRUCTION_ADHERENCE))
        require_support(LIVEBENCH_IF_2026, FORMAL_INSTRUCTION_ADHERENCE)

    def test_livebench_if_cannot_mint_semantic_credit(self):
        for capability in (
            SEMANTIC_PARAPHRASE,
            SEMANTIC_SIMPLIFICATION,
            SEMANTIC_SUMMARIZATION,
            SEMANTIC_STORY_GENERATION,
        ):
            self.assertFalse(supports(LIVEBENCH_IF_2026, capability))
            self.assertFalse(semantic_credit_from_livebench_if_only(capability))
            with self.assertRaises(UnsupportedCapabilityCredit):
                require_support(LIVEBENCH_IF_2026, capability)

    def test_unknown_benchmark_fails_closed(self):
        self.assertEqual(observable_capabilities(["UNKNOWN"]), frozenset())
        self.assertFalse(supports("UNKNOWN", FORMAL_INSTRUCTION_ADHERENCE))

    def test_union_exposes_only_declared_observables(self):
        self.assertEqual(
            observable_capabilities([LIVEBENCH_IF_2026]),
            frozenset({FORMAL_INSTRUCTION_ADHERENCE}),
        )


if __name__ == "__main__":
    unittest.main()
