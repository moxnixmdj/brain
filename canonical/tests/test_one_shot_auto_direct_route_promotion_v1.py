from __future__ import annotations

import sys
import types
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

fake_v1 = types.ModuleType("canonical.runtime.one_shot_verified_closure_v1")
fake_v1.run = lambda **kwargs: {}
sys.modules["canonical.runtime.one_shot_verified_closure_v1"] = fake_v1

from canonical.runtime import one_shot_reality_closure_v2 as v2


def closure(*, status, passed=False, internal=(), initial="i", final="f"):
    return {
        "schema": "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1",
        "status": status,
        "pass": passed,
        "fixed_point": True,
        "closure_class": "TEST",
        "initial_frontier_digest": initial,
        "final_frontier_digest": final,
        "final_state_sha256": "a" * 64,
        "irreducible_external_information_proved": False,
        "residual": {
            "internal_blockers": list(internal),
            "evidence_blockers": [],
            "irreducible_external_information_proved": False,
        },
    }


def provider_receipt(**extra):
    out = {
        "pass": True,
        "frontier_changed": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "d" * 64,
        "reuse_or_search_trace_complete": True,
        "new_code_written": False,
        "verifier_generated_or_reused": True,
        "verifier_passed": True,
    }
    out.update(extra)
    return out


class OneShotAutoDirectRoutePromotionV1Tests(unittest.TestCase):
    def test_provider_without_route_proposal_preserves_existing_behavior(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",), initial="i0", final="f0")
        second = closure(status="PASS", passed=True, initial="i1", final="f1")
        with patch.object(v2.v1, "run", side_effect=[first, second]), patch.object(
            v2.r2_direct_route_promoter, "promote"
        ) as promote:
            out = v2.run(
                repo_root=".",
                capability_synthesis_provider=lambda contract: provider_receipt(),
            )
        self.assertTrue(out["pass"], out)
        promote.assert_not_called()
        row = out["transcript"][0]["r2_direct_route_promotion"]
        self.assertFalse(row["attempted"])

    def test_verified_candidate_and_receipt_are_promoted_before_retry(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",), initial="i0", final="f0")
        second = closure(status="PASS", passed=True, initial="i1", final="f1")
        receipt = provider_receipt(
            r2_direct_route_candidate_path="canonical/governance/CANDIDATE.json",
            r2_direct_route_independent_receipt_path="canonical/verification/RECEIPT.json",
        )
        promoted = {
            "pass": True,
            "status": "PASS__R2_DIRECT_ROUTE_PROMOTED_AND_CURRENT_POINTER_REPLAYED",
            "route_id": "DIRECT_ADEQUACY::TEST_V1",
            "frontier_changed": True,
            "new_manifest_git_blob_sha": "1" * 40,
            "receipt_sha256": "2" * 64,
            "verification_authority_mutated": False,
            "terminal_authority": False,
        }
        with patch.object(v2.v1, "run", side_effect=[first, second]), patch.object(
            v2.r2_direct_route_promoter, "promote", return_value=promoted
        ) as promote:
            out = v2.run(
                repo_root=".",
                capability_synthesis_provider=lambda contract: receipt,
            )
        self.assertTrue(out["pass"], out)
        promote.assert_called_once_with(
            candidate_path="canonical/governance/CANDIDATE.json",
            receipt_path="canonical/verification/RECEIPT.json",
            repo_root=".",
        )
        row = out["transcript"][0]["r2_direct_route_promotion"]
        self.assertTrue(row["attempted"])
        self.assertTrue(row["frontier_changed"])
        self.assertEqual(row["route_id"], "DIRECT_ADEQUACY::TEST_V1")

    def test_incomplete_route_binding_fails_closed(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",))
        receipt = provider_receipt(
            r2_direct_route_candidate_path="canonical/governance/CANDIDATE.json",
        )
        with patch.object(v2.v1, "run", return_value=first):
            out = v2.run(
                repo_root=".",
                capability_synthesis_provider=lambda contract: receipt,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__INFRASTRUCTURE_OR_PROVIDER_FAILURE",
        )
        self.assertIn(
            "R2_DIRECT_ROUTE_PROMOTION_BINDING_INCOMPLETE",
            out["failure"]["reason"],
        )

    def test_promoter_rejection_cannot_be_laundered_into_provider_success(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",))
        receipt = provider_receipt(
            r2_direct_route_candidate_path="canonical/governance/CANDIDATE.json",
            r2_direct_route_independent_receipt_path="canonical/verification/RECEIPT.json",
        )
        with patch.object(v2.v1, "run", return_value=first), patch.object(
            v2.r2_direct_route_promoter,
            "promote",
            return_value={
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "BAD_RECEIPT",
                "verification_authority_mutated": False,
            },
        ):
            out = v2.run(
                repo_root=".",
                capability_synthesis_provider=lambda contract: receipt,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__INFRASTRUCTURE_OR_PROVIDER_FAILURE",
        )
        self.assertIn("R2_DIRECT_ROUTE_PROMOTION_FAILED", out["failure"]["reason"])


    def test_real_promoter_transaction_updates_dynamic_pointer_before_retry(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",), initial="i0", final="f0")
        second = closure(status="PASS", passed=True, initial="i1", final="f1")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            governance = root / "canonical/governance"
            verification = root / "canonical/verification"
            runtime = root / "canonical/runtime"
            governance.mkdir(parents=True)
            verification.mkdir(parents=True)
            runtime.mkdir(parents=True)
            (runtime / "r2_direct_live_admission_v1.py").write_text(
                "# synthetic live wrapper for exact noninterference binding\n",
                encoding="utf-8",
            )

            route_runtime_rel = "canonical/runtime/test_direct_route_v1.py"
            route_runtime = root / route_runtime_rel
            route_runtime.write_text(
                "def preflight(request, **kwargs): return {'matched': True}\n"
                "def run(request, **kwargs): return {'pass': True}\n",
                encoding="utf-8",
            )
            route_verify_rel = "canonical/verification/TEST_ROUTE_VERIFY.json"
            route_verify = root / route_verify_rel
            route_verify.write_text(
                json.dumps({"pass": True, "status": "INDEPENDENT_PASS"}) + "\n",
                encoding="utf-8",
            )

            admission = v2.r2_direct_route_promoter.admission
            manifest_rel = "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_TEST_BASE.json"
            manifest = {
                "schema": admission.MANIFEST_SCHEMA,
                "date": "2026-10-09",
                "status": "ACTIVE_DYNAMIC_ADMISSIONS__EMPTY_BASELINE",
                "selection_class": admission.SELECTION_CLASS,
                "collision_policy": "FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
                "admissions": [],
                "admission_count": 0,
                "default": "NOT_LIVE_UNLESS_EXACT_INDEPENDENT_DEPLOYMENT_RECEIPT_VALIDATES",
                "incremental_spend_usd": 0,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
            manifest_path = root / manifest_rel
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            pointer = {
                "schema": admission.POINTER_SCHEMA,
                "date": "2026-10-09",
                "status": "ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
                "binding_semantics": "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND",
                "target": {
                    "path": manifest_rel,
                    "git_blob_sha": admission.git_blob_sha(manifest_path),
                    "schema": admission.MANIFEST_SCHEMA,
                },
                "incremental_spend_usd": 0,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
            (governance / "CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json").write_text(
                json.dumps(pointer, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            candidate_rel = "canonical/governance/TEST_DIRECT_ROUTE_CANDIDATE.json"
            candidate = {
                "schema": admission.CANDIDATE_SCHEMA,
                "route_id": "DIRECT_ADEQUACY::TEST_AUTO_PROMOTION_V1",
                "capability_id": "test.auto.promotion",
                "runtime_path": route_runtime_rel,
                "runtime_git_blob_sha": admission.git_blob_sha(route_runtime),
                "preflight_callable": "preflight",
                "run_callable": "run",
                "route_verification_path": route_verify_rel,
                "route_verification_git_blob_sha": admission.git_blob_sha(route_verify),
                "scope": "TEST_EXACT_SCOPE",
                "selection_class": admission.SELECTION_CLASS,
                "deployment_requested": True,
                "incremental_spend_usd": 0,
                "terminal_authority": False,
            }
            candidate_path = root / candidate_rel
            candidate_path.write_text(
                json.dumps(candidate, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            candidate_sha = admission.git_blob_sha(candidate_path)

            current = admission.load_current_admissions(repo_root=root)
            noninterference_rel = (
                "canonical/verification/TEST_DIRECT_ROUTE_NONINTERFERENCE.json"
            )
            noninterference_path = root / noninterference_rel
            noninterference = {
                "schema": admission.NONINTERFERENCE_SCHEMA,
                "status": "INDEPENDENT_PASS__R2_DIRECT_ROUTE_NONINTERFERENCE",
                "candidate_path": candidate_rel,
                "candidate_git_blob_sha": candidate_sha,
                "route_id": candidate["route_id"],
                "runtime_path": candidate["runtime_path"],
                "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
                "baseline_live_wrapper_path": admission.LIVE_WRAPPER_PATH,
                "baseline_live_wrapper_git_blob_sha": admission.git_blob_sha(
                    root / admission.LIVE_WRAPPER_PATH
                ),
                "baseline_dynamic_manifest_git_blob_sha": current[
                    "target_git_blob_sha"
                ],
                "baseline_dynamic_route_ids": [],
                "proof_class": admission.NONINTERFERENCE_PROOF_CLASS,
                "legacy_overlap_absent_verified": True,
                "dynamic_overlap_absent_verified": True,
                "scope_complete_for_candidate_match_domain": True,
                "independent_verified": True,
                "verification_authority_mutated": False,
                "promotion_authority": False,
                "terminal_authority": False,
                "incremental_spend_usd": 0,
            }
            noninterference_path.write_text(
                json.dumps(noninterference, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            independent_rel = "canonical/verification/TEST_DIRECT_ROUTE_DEPLOYMENT_RECEIPT.json"
            independent = {
                "schema": admission.RECEIPT_SCHEMA,
                "status": "INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT",
                "candidate_path": candidate_rel,
                "candidate_git_blob_sha": candidate_sha,
                "route_id": candidate["route_id"],
                "runtime_path": candidate["runtime_path"],
                "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
                "route_verification_path": candidate["route_verification_path"],
                "route_verification_git_blob_sha": candidate["route_verification_git_blob_sha"],
                "selection_class": admission.SELECTION_CLASS,
                "independent_verified": True,
                "preflight_pure_no_effect": True,
                "matched_route_failure_no_fallthrough": True,
                "producer_independent_acceptance": True,
                "exact_raw_obligation_acceptance": True,
                "deployment_eligible": True,
                "verification_authority_mutated": False,
                "promotion_authority": False,
                "terminal_authority": False,
                "incremental_spend_usd": 0,
                "noninterference_verification_path": noninterference_rel,
                "noninterference_verification_git_blob_sha": admission.git_blob_sha(
                    noninterference_path
                ),
            }
            independent_path = root / independent_rel
            independent_path.write_text(
                json.dumps(independent, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            provider = lambda contract: provider_receipt(
                r2_direct_route_candidate_path=candidate_rel,
                r2_direct_route_independent_receipt_path=independent_rel,
            )
            with patch.object(v2.v1, "run", side_effect=[first, second]):
                out = v2.run(
                    repo_root=root,
                    capability_synthesis_provider=provider,
                )

            self.assertTrue(out["pass"], out)
            promotion = out["transcript"][0]["r2_direct_route_promotion"]
            self.assertTrue(promotion["attempted"])
            self.assertTrue(promotion["frontier_changed"])
            self.assertEqual(promotion["route_id"], candidate["route_id"])

            current = json.loads(
                (governance / "CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotEqual(current["target"]["path"], manifest_rel)
            promoted_manifest = json.loads(
                (root / current["target"]["path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(promoted_manifest["admission_count"], 1)
            self.assertEqual(
                promoted_manifest["admissions"][0]["route_id"],
                candidate["route_id"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
