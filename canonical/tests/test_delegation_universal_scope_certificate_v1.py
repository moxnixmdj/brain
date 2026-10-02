from __future__ import annotations

import copy
import json
import unittest

from canonical.runtime.delegation_universal_scope_certificate_v1 import (
    EXPECTED_CONTRACT_ROW,
    REQUIRED_FACTS,
    ROOT,
    derive_source_facts,
    derive_transport_facts,
    prove_from_facts,
    verify,
)


def _j(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class DelegationUniversalScopeCertificateTests(unittest.TestCase):
    def test_live_exact_sources_and_transport_derive_universal_candidate(self):
        out = verify()
        self.assertTrue(out["universal_scope_proved"])
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["target_predicate"], "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        self.assertEqual(out["new_reality_units"], 0)
        self.assertEqual(out["terminal_cases_replayed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        baseline = {name: True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(baseline)["universal_scope_proved"])
        for name in REQUIRED_FACTS:
            facts = dict(baseline)
            facts[name] = False
            out = prove_from_facts(facts)
            self.assertFalse(out["universal_scope_proved"], name)
            self.assertIn(name, out["missing"])

    def test_all_live_transport_facts_hold(self):
        facts = derive_transport_facts(
            _j("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json"),
            _j("canonical/verification/DELEGATION_TEMPORAL_PROOF_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            _j("canonical/verification/DELEGATION_SCOPE_GATE_V2_V3_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            _j("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
        )
        self.assertTrue(all(facts.values()), facts)

    def test_scope_superset_mutation_fails_closed(self):
        relation = _j("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json")
        relation["candidate_population_relation"]["relation"] = "UNKNOWN"
        facts = derive_transport_facts(
            relation,
            _j("canonical/verification/DELEGATION_TEMPORAL_PROOF_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            _j("canonical/verification/DELEGATION_SCOPE_GATE_V2_V3_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            _j("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
        )
        self.assertFalse(facts["SCOPE_RELATION_CANDIDATE_SUPERSET"])

    def test_temporal_current_candidate_pin_mutation_fails_closed(self):
        transport = _j("canonical/verification/DELEGATION_TEMPORAL_PROOF_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        transport["exact_current_brain_blobs"]["canonical/runtime/delegation_whole_scope_candidate_v2.py"] = "0" * 40
        facts = derive_transport_facts(
            _j("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json"),
            transport,
            _j("canonical/verification/DELEGATION_SCOPE_GATE_V2_V3_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            _j("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
        )
        self.assertFalse(
            facts["INDEPENDENT_TEMPORAL_TRANSPORT_PINS_CURRENT_ALGORITHM_SCOPE_AND_PROTOCOL"]
        )

    def test_scope_admissibility_mutation_fails_closed(self):
        receipt = _j("canonical/verification/DELEGATION_SCOPE_GATE_V2_V3_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        receipt["verdict"]["admissible"] = False
        facts = derive_transport_facts(
            _j("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json"),
            _j("canonical/verification/DELEGATION_TEMPORAL_PROOF_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            receipt,
            _j("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
        )
        self.assertFalse(facts["INDEPENDENT_SCOPE_SUBSTITUTION_REMAINS_ADMISSIBLE"])

    def test_contract_semantic_drift_mutation_fails_closed(self):
        registry = _j("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
        rows = (
            registry.get("contracts")
            or registry.get("behaviors")
            or registry.get("rows")
            or registry.get("behavioral_contracts")
        )
        row = next(x for x in rows if x.get("behavior_id") == "TASK_TO_DELEGATION_GRAPH_001")
        row["scope"] = row["scope"] + "__MUTATED"
        facts = derive_transport_facts(
            _j("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json"),
            _j("canonical/verification/DELEGATION_TEMPORAL_PROOF_TRANSPORT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            _j("canonical/verification/DELEGATION_SCOPE_GATE_V2_V3_REPAIR_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
            registry,
        )
        self.assertFalse(facts["CURRENT_CONTRACT_SEMANTIC_SLICE_UNCHANGED"])

    def test_expected_contract_slice_is_exact_current_row(self):
        registry = _j("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
        rows = (
            registry.get("contracts")
            or registry.get("behaviors")
            or registry.get("rows")
            or registry.get("behavioral_contracts")
        )
        row = next(x for x in rows if x.get("behavior_id") == "TASK_TO_DELEGATION_GRAPH_001")
        self.assertEqual(row, EXPECTED_CONTRACT_ROW)

    def test_sequence_reuse_mutation_kills_finiteness_premise(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = candidate.replace("if sid in used:", "if False:")
        facts = derive_source_facts(mutant, oracle)
        self.assertFalse(facts["FINITE_SIMPLE_SEQUENCE_SEARCH"])

    def test_negative_cost_firewall_mutation_kills_optimality_premise(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = candidate.replace("float(cost)<0", "False")
        facts = derive_source_facts(mutant, oracle)
        self.assertFalse(facts["NONNEGATIVE_FINITE_STEP_COSTS_ENFORCED"])

    def test_schedulability_gate_mutation_kills_scope_proof(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = candidate.replace(
            "_schedule(list(seq),deps,steps,workers,caps)",
            "None",
        )
        facts = derive_source_facts(mutant, oracle)
        self.assertFalse(facts["GOAL_REQUIRES_SCHEDULABILITY_BEFORE_RETURN"])

    def test_oracle_exhaustiveness_mutation_kills_equivalence_premise(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = oracle.replace(
            "for order in permutations(subset):",
            "for order in [subset]:",
        )
        facts = derive_source_facts(candidate, mutant)
        self.assertFalse(
            facts["EXHAUSTIVE_ORACLE_ENUMERATES_ALL_SUBSETS_AND_PERMUTATIONS"]
        )

    def test_evidence_conflict_guard_mutation_kills_integrity_premise(self):
        candidate = (
            ROOT / "canonical/runtime/delegation_whole_scope_candidate_v2.py"
        ).read_text(encoding="utf-8")
        oracle = (
            ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py"
        ).read_text(encoding="utf-8")
        mutant = candidate.replace("EVIDENCE_OWNER_CONFLICT:", "IGNORED_EVIDENCE_CONFLICT:")
        facts = derive_source_facts(mutant, oracle)
        self.assertFalse(
            facts["EVIDENCE_OWNERSHIP_AND_TERMINAL_FANIN_ARE_TOTAL_FOR_SELECTED_WORK"]
        )

    def test_empirical_sample_is_not_a_premise(self):
        out = verify()
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertFalse(out["uses_new_acceptance_cases"])


if __name__ == "__main__":
    unittest.main()
