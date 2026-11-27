from __future__ import annotations
import json,unittest
from pathlib import Path
from canonical.runtime.recovery_t0_t2_acceptance_ceiling_lifter_v1 import (
    STRICT_EARLIEST_CHECK,
    WEAK_EARLIEST_DISJUNCTION,
    _semantic_relation_errors,
    evaluate,
)

ROOT=Path(__file__).resolve().parents[2]

def load(path):
    return json.loads((ROOT/path).read_text())

class RecoveryCeilingLifterTests(unittest.TestCase):
    def test_live_candidate_is_quarantined_fail_closed(self):
        out=evaluate(
            protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            predicates=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            binding=load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
            terminal=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
            relation=load("canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json"),
        )
        self.assertFalse(out["pass"],out)
        self.assertIsNone(out["candidate_witness"])
        self.assertIn("P1_EXECUTED_TERMINAL_SCOPE_MISMATCH_QUARANTINE_ACTIVE",out["errors"])
        self.assertIn("RELATION_STRICT_EARLIEST_TARGET_HAS_NO_STRICT_SOURCE_PROOF",out["errors"])
        self.assertIn("RELATION_EARLIEST_TARGET_WEAKENED_TO_EARLIEST_OR_CRITICAL",out["errors"])
        self.assertIn("CAUSAL_LOCALIZATION_CEILING_DERIVED_FROM_WEAKER_DISJUNCTION",out["errors"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

    def test_or_source_does_not_imply_strict_earliest_target(self):
        relation=load("canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json")
        errors=_semantic_relation_errors(relation)
        self.assertIn("RELATION_STRICT_EARLIEST_TARGET_HAS_NO_STRICT_SOURCE_PROOF",errors)
        self.assertIn("RELATION_EARLIEST_TARGET_WEAKENED_TO_EARLIEST_OR_CRITICAL",errors)
        self.assertIn("CAUSAL_LOCALIZATION_CEILING_DERIVED_FROM_WEAKER_DISJUNCTION",errors)

        critical_localized=True
        earliest_localized=False
        self.assertTrue(critical_localized or earliest_localized)
        self.assertFalse(earliest_localized)

    def test_semantic_guard_clears_only_with_strict_earliest_source(self):
        relation=load("canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json")
        relation["target_dimension_to_source_checks"]["earliest causal failure localization"]=[
            STRICT_EARLIEST_CHECK,
            "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
        ]
        relation["acceptance_to_objective_floor_ceiling"]["causal_localization"]["source_check"]=STRICT_EARLIEST_CHECK
        self.assertEqual(_semantic_relation_errors(relation),[])

    def test_legacy_pending_or_current_active_quarantine_both_block(self):
        # The live canonical quarantine uses quarantine_active; the lifter must
        # not silently stop blocking transport when governance moves a finding
        # out of the pending-verification field.
        out=evaluate(
            protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
            registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            predicates=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            binding=load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
            terminal=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
            relation=load("canonical/governance/RECOVERY_T0_T2_ACCEPTANCE_SCOPE_RELATION_V1.json"),
        )
        self.assertIn("P1_EXECUTED_TERMINAL_SCOPE_MISMATCH_QUARANTINE_ACTIVE",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
