from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import escape_gap_a_policy_cover_adapter_v1 as adapter
from canonical.runtime.escape_progress_shared_gap_audit_v3 import _audit_gap_a
from canonical.runtime.observable_policy_cover_executor_v1 import _digest


OID = "FINANCE_ACCOUNTING_INDEX_GE_61"


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def write_json(root: Path, rel: str, doc: dict) -> dict:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {"path": rel, "git_blob_sha": git_blob(path)}


def auth_receipt(**extra):
    return {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        **extra,
    }


def direct_problem():
    return {
        "state_id": OID,
        "worlds": [{"world_id": "w0"}, {"world_id": "w1"}],
        "world_set_completeness_receipt": auth_receipt(
            policy_relevant_world_set_complete=True,
            state_id=OID,
        ),
        "policies": [
            {
                "policy_id": "p_all",
                "adequate_world_ids": ["w0", "w1"],
                "cost_units": 1,
                "adequacy_receipt": auth_receipt(
                    policy_id="p_all",
                    policy_adequate_on_every_listed_world=True,
                    policy_safe_on_every_listed_world=True,
                    hard_constraint_scope_complete=True,
                    brain_owned=True,
                    deployed_exact=True,
                    resource_bound_proved=True,
                ),
            }
        ],
        "discriminators": [],
    }


def strict_problem():
    return {
        "state_id": OID,
        "worlds": [{"world_id": "w0"}, {"world_id": "w1"}],
        "world_set_completeness_receipt": auth_receipt(
            policy_relevant_world_set_complete=True,
            state_id=OID,
        ),
        "policies": [
            {
                "policy_id": "p0",
                "adequate_world_ids": ["w0"],
                "cost_units": 1,
                "adequacy_receipt": auth_receipt(
                    policy_id="p0",
                    policy_adequate_on_every_listed_world=True,
                    policy_safe_on_every_listed_world=True,
                    hard_constraint_scope_complete=True,
                    brain_owned=True,
                    deployed_exact=True,
                    resource_bound_proved=True,
                ),
            },
            {
                "policy_id": "p1",
                "adequate_world_ids": ["w1"],
                "cost_units": 1,
                "adequacy_receipt": auth_receipt(
                    policy_id="p1",
                    policy_adequate_on_every_listed_world=True,
                    policy_safe_on_every_listed_world=True,
                    hard_constraint_scope_complete=True,
                    brain_owned=True,
                    deployed_exact=True,
                    resource_bound_proved=True,
                ),
            },
        ],
        "discriminators": [
            {
                "discriminator_id": "d",
                "outcomes": {"w0": "left", "w1": "right"},
                "cost_units": 0,
                "truth_safety_receipt": auth_receipt(
                    discriminator_id="d",
                    outcome_map_complete=True,
                    truth_preserving=True,
                    safe_on_entire_state=True,
                    resource_bound_proved=True,
                ),
            }
        ],
    }


class RepoFixture:
    def __init__(self, root: Path, problem: dict):
        self.root = root
        manifest_ref = write_json(
            root,
            "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json",
            {
                "schema": adapter.MANIFEST_SCHEMA,
                "rows": [{"obligation_id": OID, "route_group": "GAP_A_ACQUISITION_TOTALITY"}],
            },
        )
        binding_path = (
            "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json"
        )
        write_json(
            root,
            binding_path,
            {
                "current_successor_manifest": manifest_ref,
                "current_effective_projection": {
                    "route_group_overrides": {},
                    "parked_rows": [],
                },
            },
        )
        write_json(
            root,
            "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json",
            {
                "classifications": [
                    {
                        "residual_id": "ESCAPE_GAP_A_ACQUISITION_TOTALITY",
                        "existing_binding": binding_path,
                    },
                    {
                        "residual_id": "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS",
                        "existing_binding": binding_path,
                    },
                ]
            },
        )
        problem_sha = _digest(problem)
        cover = {
            "schema": "PROJECT_BRAIN_OBSERVABLE_POLICY_COVER_INPUT_BINDING_V1",
            "state_id": OID,
            "problem_sha256": problem_sha,
            "cover_inputs_authenticated": True,
            "policy_relevant_world_set_completeness_authenticated": True,
            "all_policy_adequacy_receipts_authenticated": True,
            "all_discriminator_truth_safety_receipts_authenticated": True,
            "brain_owned_and_resource_bounds_authenticated": True,
        }
        cover_ref = write_json(
            root, "canonical/governance/test-cover-binding.json", cover
        )
        cover_verify = {
            "schema": "PROJECT_BRAIN_OBSERVABLE_POLICY_COVER_INPUT_BINDING_INDEPENDENT_VERIFICATION_V1",
            "subject_git_blob_sha": cover_ref["git_blob_sha"],
            "state_id": OID,
            "problem_sha256": problem_sha,
            "pass": True,
            "independent_verified": True,
            "input_authentication_verified": True,
            "policy_adequacy_authentication_verified": True,
            "discriminator_semantics_authentication_verified": True,
            "independent_verifier_id": "independent-cover-verifier",
        }
        cover_verify_ref = write_json(
            root, "canonical/verification/test-cover-binding-verify.json", cover_verify
        )
        self.cover_binding = {
            "receipt": cover_ref,
            "verification": cover_verify_ref,
        }

    def policy_availability(self, *, resource_admissible=True):
        receipt = {
            "schema": adapter.POLICY_AVAILABILITY_SCHEMA,
            "state_id": OID,
            "obligation_id": OID,
            "common_policy_id": "p_all",
            "currently_available": True,
            "resource_admissible": resource_admissible,
        }
        ref = write_json(
            self.root, "canonical/governance/test-policy-availability.json", receipt
        )
        verify = {
            "schema": adapter.POLICY_AVAILABILITY_VERIFY_SCHEMA,
            "subject_git_blob_sha": ref["git_blob_sha"],
            "state_id": OID,
            "obligation_id": OID,
            "common_policy_id": "p_all",
            "pass": True,
            "independent_verified": True,
            "current_availability_verified": True,
            "resource_admissibility_verified": True,
            "independent_verifier_id": "independent-availability-verifier",
        }
        vref = write_json(
            self.root, "canonical/verification/test-policy-availability-verify.json", verify
        )
        return {"receipt": ref, "verification": vref}

    def discriminator_acquirability(self):
        receipt = {
            "schema": adapter.DISCRIMINATOR_ACQUIRABILITY_SCHEMA,
            "state_id": OID,
            "obligation_id": OID,
            "discriminator_id": "d",
            "currently_acquirable": True,
        }
        ref = write_json(
            self.root, "canonical/governance/test-discriminator-acquirability.json", receipt
        )
        verify = {
            "schema": adapter.DISCRIMINATOR_ACQUIRABILITY_VERIFY_SCHEMA,
            "subject_git_blob_sha": ref["git_blob_sha"],
            "state_id": OID,
            "obligation_id": OID,
            "discriminator_id": "d",
            "pass": True,
            "independent_verified": True,
            "current_acquirability_verified": True,
            "independent_verifier_id": "independent-acquirability-verifier",
        }
        vref = write_json(
            self.root,
            "canonical/verification/test-discriminator-acquirability-verify.json",
            verify,
        )
        return {"receipt": ref, "verification": vref}


class GapAPolicyCoverAdapterTests(unittest.TestCase):
    def test_current_projection_promotes_reclassified_historical_gap_b_row(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            oid = "PROWORK_GDPVAL_GE_1846"
            manifest_ref = write_json(
                root,
                "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json",
                {
                    "schema": adapter.MANIFEST_SCHEMA,
                    "rows": [{"obligation_id": oid, "route_group": "GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"}],
                },
            )
            binding_path = "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json"
            write_json(
                root,
                binding_path,
                {
                    "current_successor_manifest": manifest_ref,
                    "current_effective_projection": {
                        "route_group_overrides": {oid: "GAP_A_ACQUISITION_TOTALITY"},
                        "parked_rows": [],
                    },
                },
            )
            write_json(
                root,
                "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json",
                {
                    "classifications": [
                        {"residual_id": "ESCAPE_GAP_A_ACQUISITION_TOTALITY", "existing_binding": binding_path},
                        {"residual_id": "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS", "existing_binding": binding_path},
                    ]
                },
            )
            row = adapter._manifest_row(oid, root)
            self.assertEqual(row["route_group"], "GAP_A_ACQUISITION_TOTALITY")

    def test_current_projection_keeps_parked_tb_out_of_gap_a(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            oid = "TB_SCIENCE_GE_58_7"
            manifest_ref = write_json(
                root,
                "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json",
                {
                    "schema": adapter.MANIFEST_SCHEMA,
                    "rows": [{"obligation_id": oid, "route_group": "GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"}],
                },
            )
            binding_path = "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json"
            write_json(
                root,
                binding_path,
                {
                    "current_successor_manifest": manifest_ref,
                    "current_effective_projection": {
                        "route_group_overrides": {},
                        "parked_rows": [oid],
                    },
                },
            )
            write_json(
                root,
                "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json",
                {
                    "classifications": [
                        {"residual_id": "ESCAPE_GAP_A_ACQUISITION_TOTALITY", "existing_binding": binding_path},
                        {"residual_id": "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS", "existing_binding": binding_path},
                    ]
                },
            )
            with self.assertRaisesRegex(ValueError, "PARKED"):
                adapter._manifest_row(oid, root)

    def test_direct_common_policy_emits_audit_valid_terminal_proof(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            fx = RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                    "policy_availability_binding": fx.policy_availability(),
                },
                repo_root=root,
            )
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["row_proof_emitted"])
            self.assertEqual(
                out["row_proof"]["resolution_mode"], "TERMINAL_COMMON_POLICY"
            )
            self.assertEqual(_audit_gap_a({"obligation_id": OID}, out["row_proof"]), [])

    def test_missing_policy_availability_emits_no_proof(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            fx = RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                },
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertFalse(out["row_proof_emitted"])
            self.assertIn("AVAILABILITY", out["status"])

    def test_resource_bound_does_not_imply_resource_admissible(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            fx = RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                    "policy_availability_binding": fx.policy_availability(
                        resource_admissible=False
                    ),
                },
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertFalse(out["row_proof_emitted"])
            self.assertIn("RESOURCE_ADMISSIBILITY", out["policy_availability"]["reason"])

    def test_root_discriminator_emits_audit_valid_strict_proof(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = strict_problem()
            fx = RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                    "discriminator_acquirability_binding": fx.discriminator_acquirability(),
                },
                repo_root=root,
            )
            self.assertTrue(out["pass"], out)
            proof = out["row_proof"]
            self.assertEqual(proof["resolution_mode"], "STRICT_DISCRIMINATOR")
            self.assertEqual(proof["decision_region_size_before"], 2)
            self.assertEqual(proof["max_nonterminal_decision_region_size_after"], 1)
            self.assertEqual(len(proof["finite_outcome_ids"]), 2)
            self.assertEqual(_audit_gap_a({"obligation_id": OID}, proof), [])

    def test_missing_acquirability_does_not_turn_totality_tree_into_row_proof(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = strict_problem()
            fx = RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                },
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertFalse(out["row_proof_emitted"])
            self.assertIn("ACQUIRABILITY", out["status"])

    def test_forged_inline_cover_flags_without_bound_cover_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": {
                        "pass": True,
                        "independent_verified": True,
                        "all_policy_adequacy_receipts_authenticated": True,
                    },
                },
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertFalse(out["row_proof_emitted"])

    def test_adequate_but_unsafe_policy_cannot_be_adapted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            problem["policies"][0]["adequacy_receipt"][
                "policy_safe_on_every_listed_world"
            ] = False
            fx = RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                    "policy_availability_binding": fx.policy_availability(),
                },
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertFalse(out["row_proof_emitted"])

    def test_stale_availability_blob_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            fx = RepoFixture(root, problem)
            binding = fx.policy_availability()
            binding["receipt"]["git_blob_sha"] = "0" * 40
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                    "policy_availability_binding": binding,
                },
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertIn("BOUND_BLOB_DRIFT", out["policy_availability"]["reason"])

    def test_state_must_equal_obligation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            problem["state_id"] = "OTHER"
            RepoFixture(root, problem)
            out = adapter.adapt(
                {"obligation_id": OID, "problem": problem},
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "STATE_ID_MUST_EQUAL_OBLIGATION_ID")

    def test_proof_digest_tamper_is_killed_by_existing_audit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            fx = RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                    "policy_availability_binding": fx.policy_availability(),
                },
                repo_root=root,
            )
            proof = dict(out["row_proof"])
            proof["common_policy_id"] = "tampered"
            missing = _audit_gap_a({"obligation_id": OID}, proof)
            self.assertIn(f"{OID}:CONTENT_ADDRESS_PROOF_INVALID", missing)

    def test_adapter_never_grants_terminal_or_cc_r3_credit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            problem = direct_problem()
            fx = RepoFixture(root, problem)
            out = adapter.adapt(
                {
                    "obligation_id": OID,
                    "problem": problem,
                    "cover_binding": fx.cover_binding,
                    "policy_availability_binding": fx.policy_availability(),
                },
                repo_root=root,
            )
            self.assertTrue(out["pass"], out)
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["row_credit_delta"], 0)
            self.assertEqual(out["cc_r3_credit_delta"], 0)
            self.assertEqual(out["capability_credit_delta"], 0)
            self.assertEqual(out["acceptance_credit_delta"], 0)
            self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
