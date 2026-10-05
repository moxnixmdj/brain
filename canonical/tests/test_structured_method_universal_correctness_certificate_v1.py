from __future__ import annotations

import unittest

from canonical.runtime.structured_method_universal_correctness_certificate_v1 import (
    REQUIRED_FACTS,
    ROOT,
    derive_source_facts,
    prove_from_facts,
    verify,
)


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class StructuredMethodUniversalCorrectnessCertificateV1Tests(unittest.TestCase):
    def setUp(self):
        self.candidate = text(
            "canonical/runtime/structured_method_normalized_rule_graph_v3.py"
        )
        self.oracle = text(
            "canonical/runtime/structured_method_normalized_rule_oracle_v3.py"
        )

    def test_live_sources_derive_universal_correctness_ceiling(self):
        out = verify()
        self.assertTrue(out["universal_correctness_proved"])
        self.assertTrue(out["theoretical_ceiling_proved"])
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_CORRECTNESS_PROOF")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        good = {name: True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(good)["universal_correctness_proved"])
        for name in REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = prove_from_facts(mutant)
            self.assertFalse(out["universal_correctness_proved"], name)
            self.assertIn(name, out["missing"])

    def test_removing_pending_deletion_kills_termination_premise(self):
        mutant = self.candidate.replace(
            "del pending[rid]; progressed=True",
            "progressed=True",
        )
        facts = derive_source_facts(mutant, self.oracle)
        self.assertFalse(facts["CANDIDATE_REMOVES_EACH_PROCESSED_RULE"])
        self.assertFalse(prove_from_facts(facts)["universal_correctness_proved"])

    def test_removing_no_progress_fail_closed_kills_topological_guard(self):
        mutant = self.candidate.replace(
            'raise GraphError("UNRESOLVED_DEPENDENCY_OR_CYCLE:"+",".join(sorted(pending)))',
            'return {"status":"COMPILED"}',
        )
        facts = derive_source_facts(mutant, self.oracle)
        self.assertFalse(facts["CANDIDATE_FAILS_CLOSED_IF_NO_RULE_IS_READY"])
        self.assertFalse(prove_from_facts(facts)["universal_correctness_proved"])

    def test_dynamic_operator_execution_kills_operator_data_premise(self):
        mutant = self.candidate + "\n# eval(operator)\n"
        facts = derive_source_facts(mutant, self.oracle)
        self.assertFalse(facts["CANDIDATE_OPERATOR_IDENTITY_IS_DATA_NOT_EXECUTED_CODE"])
        self.assertFalse(prove_from_facts(facts)["universal_correctness_proved"])

    def test_oracle_importing_candidate_kills_independence(self):
        mutant = (
            self.oracle
            + "\n# structured_method_normalized_rule_graph_v3\n"
        )
        facts = derive_source_facts(self.candidate, mutant)
        self.assertFalse(facts["ORACLE_IS_IMPLEMENTATION_INDEPENDENT"])
        self.assertFalse(prove_from_facts(facts)["universal_correctness_proved"])

    def test_removing_exact_oracle_field_comparison_kills_projection_premise(self):
        mutant = self.oracle.replace(
            "if candidate.get(key)!=value:",
            "if False:",
        )
        facts = derive_source_facts(self.candidate, mutant)
        self.assertFalse(
            facts["ORACLE_EXACTLY_COMPARES_EVERY_LOAD_BEARING_PROJECTION_FIELD"]
        )
        self.assertFalse(prove_from_facts(facts)["universal_correctness_proved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
