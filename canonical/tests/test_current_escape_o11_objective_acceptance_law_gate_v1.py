from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import current_escape_o11_objective_acceptance_law_gate_v1 as gate


SHA = "1" * 40
BIND = {"path": "canonical/governance/x.json", "git_blob_sha": SHA}
RECEIPT = {"path": "canonical/verification/x.json", "git_blob_sha": SHA}
CURSOR = "CODING_CURSORBENCH_GE_57_8"
MYSTERY = "MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER"
GDP = "PROWORK_GDPVAL_GE_1846"
AA = "PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT"
TB = "TB_SCIENCE_GE_58_7"


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def frontier(root: Path) -> None:
    rows = [
        CURSOR,
        MYSTERY,
        GDP,
        AA,
        "CODING_TB4_GE_66_4",
        "CODING_FRONTIERCODE_GE_54_4",
        "AUTOMATIONBENCH_GE_40",
        "HLE_TOOLS_GE_67_7",
        "TB_SCIENCE_GE_58_7",
        "CHARTOGRAPHY_TOOLS_GE_89",
        "OSWORLD_2_1_PARTIAL_GE_81_8",
        "FINANCE_ACCOUNTING_INDEX_GE_61",
        "FINANCE_AGENT_V2_GE_58_59",
    ]
    manifest_path = root / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
    _write(
        manifest_path,
        {
            "schema": gate.MANIFEST_SCHEMA,
            "rows": [{"obligation_id": x} for x in rows],
        },
    )
    _write(
        root / "canonical/governance/CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1.json",
        {
            "schema": gate.CUT_SCHEMA,
            "status": "CURRENT_ACTIVE_ESCAPE_COLLAPSED_TO_TWO_REUSE_ENGINES__O11_ACTIVE__Q1_ACTIVE__TB_PARKED",
            "source_bindings": {
                "manifest": [
                    "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json",
                    _blob(manifest_path),
                ]
            },
            "current_partition": {
                "total_escape_rows": 13,
                "active_rows": 12,
                "parked_rows": 1,
                "active_o_rows": 11,
                "active_q_rows": 1,
                "active_o_obligation_ids": [
                    CURSOR, MYSTERY, GDP,
                    "CODING_TB4_GE_66_4",
                    "CODING_FRONTIERCODE_GE_54_4",
                    "AUTOMATIONBENCH_GE_40",
                    "HLE_TOOLS_GE_67_7",
                    "CHARTOGRAPHY_TOOLS_GE_89",
                    "OSWORLD_2_1_PARTIAL_GE_81_8",
                    "FINANCE_ACCOUNTING_INDEX_GE_61",
                    "FINANCE_AGENT_V2_GE_58_59",
                ],
                "active_q_obligation_ids": [AA],
                "parked_obligation_ids": [TB],
            },
        },
    )


def proof(claim_id: str, scope: str, *, claim_value=None, target_value=None, proof_type="DETERMINISTIC_DERIVATION"):
    out = {
        "claim_id": claim_id,
        "status": "PROVED_SOUND_IMPLICATION" if proof_type == "SOUND_IMPLICATION" else "PROVED_EXACT",
        "proof_type": proof_type,
        "target_scope": scope,
        "evidence_class": "DETERMINISTIC_FORMAL_PROOF",
        "target_tuple_binding": dict(BIND),
        "receipts": [dict(RECEIPT)],
    }
    if claim_value is not None:
        out["claim_value"] = claim_value
    if target_value is not None:
        out["target_value"] = target_value
    return out


def threshold_cert(pid: str, lower=0.70, target=0.578):
    return {
        "predicate_id": pid,
        "exact_target_tuple_bound": True,
        "target_tuple_binding": dict(BIND),
        "certificate": {
            "type": "THRESHOLD_LOWER_BOUND",
            "receipts": [dict(RECEIPT)],
            "evaluator_relation": {
                "status": "PROVED_EXACT",
                "relation_type": "EXACT_IDENTITY",
                "target_scope": "FROZEN_TARGET_EVALUATOR_HARNESS_FALLBACK",
                "evidence_class": "EXACT_FROZEN_TARGET_HARNESS",
                "target_tuple_binding": dict(BIND),
                "receipts": [dict(RECEIPT)],
            },
            "proved_lower_bound": lower,
            "target_threshold": target,
            "premise_proofs": {
                "SCORE_DECOMPOSITION_EXACT": proof(
                    "SCORE_DECOMPOSITION_EXACT", "FROZEN_TARGET_SCORING_RULE"
                ),
                "LOWER_BOUND_GE_TARGET": proof(
                    "LOWER_BOUND_GE_TARGET",
                    "FROZEN_TARGET_SCORE_THRESHOLD",
                    claim_value=lower,
                    target_value=target,
                ),
            },
        },
    }


def superset_cert(pid: str):
    return {
        "predicate_id": pid,
        "exact_target_tuple_bound": True,
        "target_tuple_binding": dict(BIND),
        "certificate": {
            "type": "SCOPE_SUPERSET",
            "receipts": [dict(RECEIPT)],
            "evaluator_relation": {
                "status": "PROVED_SOUND_IMPLICATION",
                "relation_type": "SOUND_DOMINANCE_IMPLICATION",
                "target_scope": "FROZEN_TARGET_EVALUATOR_HARNESS_FALLBACK",
                "evidence_class": "SOUND_EVALUATOR_IMPLICATION",
                "target_tuple_binding": dict(BIND),
                "receipts": [dict(RECEIPT)],
            },
            "premise_proofs": {
                "HIDDEN_SCOPE_UPPER_BOUND": proof(
                    "HIDDEN_SCOPE_UPPER_BOUND",
                    "FROZEN_HIDDEN_TARGET_SCOPE",
                    proof_type="SOUND_IMPLICATION",
                ),
                "RESOURCE_SEMANTICS": proof(
                    "RESOURCE_SEMANTICS",
                    "FROZEN_TARGET_RESOURCE_SEMANTICS",
                    proof_type="SOUND_IMPLICATION",
                ),
                "UNIVERSAL_SUCCESS": proof(
                    "UNIVERSAL_SUCCESS",
                    "CERTIFICATE_CLAIM_DOMAIN",
                    proof_type="SOUND_IMPLICATION",
                ),
                "NO_TARGET_OUTCOME_LEAKAGE": proof(
                    "NO_TARGET_OUTCOME_LEAKAGE",
                    "CERTIFICATE_EVIDENCE_PROVENANCE",
                    proof_type="SOUND_IMPLICATION",
                ),
            },
        },
    }


def base_claim(pid: str, *, benchmark_id: str, cert: dict, superset=False):
    identity = {
        "benchmark_id": benchmark_id,
        "benchmark_version": "current",
        "target_id": "CURRENT_OWNER_TARGET",
        "harness_hash": "h1",
        "scoring_rule_hash": "s1",
        "resource_contract_hash": "r1",
    }
    policy = {
        "predicate_id": pid,
        "claim_scope": pid + "::CURRENT",
        "policy_binding": dict(BIND),
        "candidate_binding": dict(BIND),
        "candidate_frozen": True,
        "frozen_at": "2026-10-10T08:00:00+00:00",
        "frozen_identity": dict(identity),
        "identity_keys": list(identity),
        "freshness_keys": list(identity),
        "scope": (
            {"mode": "PROOF_CARRYING_SUPERSET"}
            if superset
            else {"mode": "EXACT_TASK_SET", "task_ids": ["a", "b"]}
        ),
        "require_clean_provenance": True,
        "evaluator": {"mode": "OBJECTIVE", "objective_validator": True},
    }
    evidence = {
        "observed_at": "2026-10-10T08:01:00+00:00",
        "observed_identity": dict(identity),
        "provenance": {
            "binding": dict(RECEIPT),
            "precommitment_frozen": True,
            "target_outcome_not_used": True,
            "status": "CLEAN",
        },
        "objective_evaluator": {
            "binding": dict(RECEIPT),
            "independent_verified": True,
            "relation": "BRAIN_GE_TARGET",
        },
        "failure_accounting_complete": True,
        "undisclosed_exclusion_count": 0,
        "reproducible": True,
        "evidence_capsule_binding": dict(RECEIPT),
        "v3_certificate": cert,
    }
    if superset:
        evidence["scope_cover"] = {
            "benchmark_id": benchmark_id,
            "predicate_id": pid,
            "scope_completeness": {
                "verified": True,
                "independent": True,
                "source_path": "canonical/verification/scope.json",
                "source_sha": SHA,
                "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
                "all_admissible_target_inputs_proved": True,
                "formal_completeness": True,
            },
            "cover_completeness": {
                "verified": True,
                "independent": True,
                "source_path": "canonical/verification/cover.json",
                "source_sha": SHA,
                "covers_entire_scope": True,
            },
            "cells": [
                {
                    "cell_id": "ALL",
                    "scope_relation": "PROVEN_STRONGER",
                    "policy_id": "BRAIN_POLICY",
                    "brain_owned_policy": True,
                    "deployable": True,
                    "resource_admissible": True,
                    "external_target_capability_provider": False,
                    "adequacy_certificate": {
                        "verified": True,
                        "independent": True,
                        "source_path": "canonical/verification/adequacy.json",
                        "source_sha": SHA,
                        "adequate_for_entire_cell": True,
                    },
                }
            ],
        }
    else:
        evidence["scope_records"] = [
            {"task_id": "a", "state": "VALID_RESULT"},
            {"task_id": "b", "state": "COUNTED_FAILURE"},
        ]
    return {"policy": policy, "evidence": evidence, "current_identity": dict(identity)}


class CurrentEscapeO11ObjectiveAcceptanceLawGateTests(unittest.TestCase):
    def test_current_frontier_is_exactly_o11_q1_plus_one_parked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            o, q, parked, _ = gate._frontier(root)
            self.assertEqual(len(o), 11)
            self.assertEqual(q, {AA})
            self.assertEqual(parked, {TB})
            self.assertIn(GDP, o)
            self.assertNotIn(TB, o)

    def test_current_threshold_claim_routes_through_existing_kernel(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            claim = base_claim(
                CURSOR,
                benchmark_id="CURSORBENCH_4_0",
                cert=threshold_cert(CURSOR),
            )
            out = gate.evaluate(
                {"obligation_id": CURSOR, "claim_spec": claim},
                repo_root=root,
            )
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["proof_mode"], "THRESHOLD_LOWER_BOUND")
            self.assertEqual(out["kernel_verdict"]["status"], "PROVEN")
            self.assertFalse(out["acceptance_authority"])

    def test_current_identity_drift_is_stale_not_proven(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            claim = base_claim(
                CURSOR,
                benchmark_id="CURSORBENCH_4_0",
                cert=threshold_cert(CURSOR),
            )
            claim["current_identity"]["target_id"] = "NEW_OWNER_TARGET"
            out = gate.evaluate(
                {"obligation_id": CURSOR, "claim_spec": claim},
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertEqual(out["status"], "STALE__CURRENT_O_OBJECTIVE_ACCEPTANCE")
            self.assertIn("CURRENT_IDENTITY_DRIFT", out["reason"])

    def test_strengthened_mystery_predicate_uses_scope_superset_without_old_bar_alias(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            claim = base_claim(
                MYSTERY,
                benchmark_id="MYSTERYMECHANISM_CURRENT_SCOPE",
                cert=superset_cert(MYSTERY),
                superset=True,
            )
            out = gate.evaluate(
                {"obligation_id": MYSTERY, "claim_spec": claim},
                repo_root=root,
            )
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["proof_mode"], "SCOPE_SUPERSET")
            self.assertEqual(out["kernel_verdict"]["predicate_id"], MYSTERY)
            self.assertNotEqual(out["kernel_verdict"]["predicate_id"], "MYSTERYMECHANISM_GE_49_55")

    def test_only_aa_is_rejected_to_q_law_and_gdpval_is_current_o(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            aa_claim = base_claim(
                AA,
                benchmark_id="AA_BRIEFCASE",
                cert=threshold_cert(AA, lower=1900, target=1822),
            )
            aa_out = gate.evaluate(
                {"obligation_id": AA, "claim_spec": aa_claim},
                repo_root=root,
            )
            self.assertFalse(aa_out["pass"])
            self.assertEqual(aa_out["status"], "NOT_APPLICABLE__CURRENT_Q_ROW")

            gdp_claim = base_claim(
                GDP,
                benchmark_id="GDPVAL",
                cert=threshold_cert(GDP, lower=1900, target=1846),
            )
            gdp_out = gate.evaluate(
                {"obligation_id": GDP, "claim_spec": gdp_claim},
                repo_root=root,
            )
            self.assertTrue(gdp_out["pass"], gdp_out)

    def test_parked_tb_cannot_enter_o_gate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            claim = base_claim(
                TB,
                benchmark_id="TB_SCIENCE",
                cert=threshold_cert(TB),
            )
            out = gate.evaluate(
                {"obligation_id": TB, "claim_spec": claim},
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertEqual(out["status"], "NOT_APPLICABLE__CURRENT_PARKED_ROW")

    def test_claim_predicate_must_equal_obligation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            claim = base_claim(
                CURSOR,
                benchmark_id="CURSORBENCH_4_0",
                cert=threshold_cert(CURSOR),
            )
            claim["policy"]["predicate_id"] = MYSTERY
            out = gate.evaluate(
                {"obligation_id": CURSOR, "claim_spec": claim},
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "CLAIM_PREDICATE_ID_MISMATCH")

    def test_incomplete_scope_stays_open(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            claim = base_claim(
                CURSOR,
                benchmark_id="CURSORBENCH_4_0",
                cert=threshold_cert(CURSOR),
            )
            claim["evidence"]["scope_records"].pop()
            out = gate.evaluate(
                {"obligation_id": CURSOR, "claim_spec": claim},
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertEqual(out["status"], "OPEN__CURRENT_O_OBJECTIVE_ACCEPTANCE")

    def test_kernel_proven_never_grants_acceptance_or_terminal_credit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            frontier(root)
            claim = base_claim(
                CURSOR,
                benchmark_id="CURSORBENCH_4_0",
                cert=threshold_cert(CURSOR),
            )
            out = gate.evaluate(
                {"obligation_id": CURSOR, "claim_spec": claim},
                repo_root=root,
            )
            self.assertTrue(out["pass"], out)
            self.assertFalse(out["acceptance_authority"])
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["acceptance_credit_delta"], 0)
            self.assertEqual(out["capability_credit_delta"], 0)
            self.assertEqual(out["ownership_credit_delta"], 0)
            self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
