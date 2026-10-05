from __future__ import annotations

import json
import unittest

from canonical.runtime import structured_method_universal_correctness_certificate_v1 as cert


def _text(rel: str) -> str:
    return (cert.ROOT / rel).read_text(encoding="utf-8")


def _data(rel: str):
    return json.loads(_text(rel))


def _facts(compiler=None, oracle=None, scope_audit=None, scope_gate=None, oracle_verification=None):
    return cert.derive_source_facts(
        _text("canonical/runtime/structured_method_normalized_rule_graph_v3.py")
        if compiler is None else compiler,
        _text("canonical/runtime/structured_method_normalized_rule_oracle_v3.py")
        if oracle is None else oracle,
        _data("canonical/governance/STRUCTURED_METHOD_SCOPE_AUDIT_V3.json")
        if scope_audit is None else scope_audit,
        _data("canonical/verification/STRUCTURED_METHOD_SCOPE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        if scope_gate is None else scope_gate,
        _data("canonical/verification/STRUCTURED_METHOD_NORMALIZED_RULE_V3_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        if oracle_verification is None else oracle_verification,
    )


class StructuredMethodUniversalCorrectnessCertificateV1Tests(unittest.TestCase):
    def test_fail_closed_if_any_universal_premise_is_missing(self):
        good = {name: True for name in cert.REQUIRED_FACTS}
        self.assertTrue(cert.prove_from_facts(good)["universal_correctness_proved_candidate"])
        for name in cert.REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = cert.prove_from_facts(mutant)
            self.assertFalse(out["universal_correctness_proved_candidate"], name)
            self.assertFalse(out["objective_ceiling_candidate"], name)
            self.assertIn(name, out["missing"])
            self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_removing_ready_rule_predicate_kills_induction(self):
        compiler = _text("canonical/runtime/structured_method_normalized_rule_graph_v3.py")
        mutant = compiler.replace(
            "if any(x not in nodes for x in ins):\n                    continue",
            "if False:\n                    continue",
        )
        facts = _facts(compiler=mutant)
        self.assertFalse(facts["READY_PREDICATE_IDENTICAL"])
        self.assertFalse(cert.prove_from_facts(facts)["universal_correctness_proved_candidate"])

    def test_changing_compiler_edge_transition_kills_state_bisimulation(self):
        compiler = _text("canonical/runtime/structured_method_normalized_rule_graph_v3.py")
        mutant = compiler.replace(
            'edges.append({"source":src,"target":out,"rule_id":rid})',
            'edges.append({"source":out,"target":src,"rule_id":rid})',
        )
        facts = _facts(compiler=mutant)
        self.assertFalse(facts["DERIVED_NODE_RULE_EDGE_TRANSITION_CORRESPONDS"])
        self.assertFalse(cert.prove_from_facts(facts)["universal_correctness_proved_candidate"])

    def test_reopening_scope_dimension_kills_ceiling_candidate(self):
        scope = _data("canonical/governance/STRUCTURED_METHOD_SCOPE_AUDIT_V3.json")
        scope["unresolved_scope_dimensions"] = ["MUTANT_UNRESOLVED_DIMENSION"]
        facts = _facts(scope_audit=scope)
        self.assertFalse(facts["SCOPE_ALREADY_CLOSED"])
        self.assertFalse(cert.prove_from_facts(facts)["universal_correctness_proved_candidate"])

    def test_removing_oracle_field_comparison_kills_score_implication(self):
        oracle = _text("canonical/runtime/structured_method_normalized_rule_oracle_v3.py")
        mutant = oracle.replace(
            "for key,value in exp.items():",
            "for key,value in {}.items():",
        )
        facts = _facts(oracle=mutant)
        self.assertFalse(facts["ORACLE_SCORE_CHECKS_EVERY_EXPECTED_FIELD"])
        self.assertFalse(cert.prove_from_facts(facts)["universal_correctness_proved_candidate"])

    def test_exact_current_sources_satisfy_the_bound_theorem(self):
        out = cert.verify()
        self.assertTrue(out["universal_correctness_proved_candidate"], out)
        self.assertTrue(out["scope_complete"])
        self.assertTrue(out["objective_ceiling_candidate"])
        self.assertEqual(
            out["basis_kind"],
            "ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS",
        )
        self.assertEqual(out["brain_value"], 1)
        self.assertEqual(out["theoretical_upper_bound"], 1)
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertFalse(out["terminal_wave_load_bearing"])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["terminal_cases_consumed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
