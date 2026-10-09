from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import r2_direct_route_dynamic_admission_v1 as admission
from canonical.runtime import promote_r2_direct_route_v1 as promoter


class R2DirectRouteDynamicAdmissionV1Tests(unittest.TestCase):
    def _fixture(self, root: Path):
        runtime = root / "canonical/runtime/new_direct_route_v1.py"
        verification = root / "canonical/verification/NEW_DIRECT_ROUTE_VERIFY_V1.json"
        candidate = root / "canonical/governance/NEW_DIRECT_ROUTE_DEPLOYMENT_CANDIDATE_V1.json"
        receipt = root / "canonical/verification/NEW_DIRECT_ROUTE_DEPLOYMENT_RECEIPT_V1.json"
        baseline = root / "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_20261009_V1.json"
        pointer = root / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"
        for path in (runtime, verification, candidate, receipt, baseline, pointer):
            path.parent.mkdir(parents=True, exist_ok=True)

        runtime.write_text(
            "def preflight(request, *, repo_root=None):\n"
            "    return {'matched': False}\n"
            "def run(request, *, repo_root=None):\n"
            "    return {'pass': True, 'route_id': 'DIRECT_ADEQUACY::NEW_TEST_V1'}\n",
            encoding="utf-8",
        )
        verification.write_text(
            json.dumps({"schema":"TEST","status":"PASS"},indent=2)+"\n",
            encoding="utf-8",
        )
        runtime_sha = admission.git_blob_sha(runtime)
        verification_sha = admission.git_blob_sha(verification)
        candidate_doc = {
            "schema": admission.CANDIDATE_SCHEMA,
            "route_id": "DIRECT_ADEQUACY::NEW_TEST_V1",
            "capability_id": "test.new.route",
            "runtime_path": "canonical/runtime/new_direct_route_v1.py",
            "runtime_git_blob_sha": runtime_sha,
            "preflight_callable": "preflight",
            "run_callable": "run",
            "route_verification_path": "canonical/verification/NEW_DIRECT_ROUTE_VERIFY_V1.json",
            "route_verification_git_blob_sha": verification_sha,
            "scope": "EXACT_TEST_SCOPE",
            "selection_class": admission.SELECTION_CLASS,
            "deployment_requested": True,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }
        candidate.write_text(
            json.dumps(candidate_doc,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
        candidate_sha = admission.git_blob_sha(candidate)
        receipt_doc = {
            "schema": admission.RECEIPT_SCHEMA,
            "status": "INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT",
            "candidate_path": "canonical/governance/NEW_DIRECT_ROUTE_DEPLOYMENT_CANDIDATE_V1.json",
            "candidate_git_blob_sha": candidate_sha,
            "route_id": candidate_doc["route_id"],
            "runtime_path": candidate_doc["runtime_path"],
            "runtime_git_blob_sha": runtime_sha,
            "route_verification_path": candidate_doc["route_verification_path"],
            "route_verification_git_blob_sha": verification_sha,
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
        }
        receipt.write_text(
            json.dumps(receipt_doc,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
        baseline_doc = {
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
        baseline.write_text(
            json.dumps(baseline_doc,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
        baseline_sha = admission.git_blob_sha(baseline)
        pointer_doc = {
            "schema": admission.POINTER_SCHEMA,
            "date": "2026-10-09",
            "status": "ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
            "binding_semantics": (
                "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
            ),
            "target": {
                "path": "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_20261009_V1.json",
                "git_blob_sha": baseline_sha,
                "schema": admission.MANIFEST_SCHEMA,
            },
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        pointer.write_text(
            json.dumps(pointer_doc,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
        return candidate, receipt, pointer

    def test_compile_and_atomic_promote(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate, receipt, pointer = self._fixture(root)
            current = admission.load_current_admissions(repo_root=root)
            compiled = admission.compile_admission(
                repo_root=root,
                current_manifest=current["manifest"],
                candidate_path=str(candidate.relative_to(root)),
                receipt_path=str(receipt.relative_to(root)),
            )
            self.assertTrue(compiled["pass"])
            self.assertTrue(compiled["frontier_changed"])
            self.assertEqual(compiled["manifest"]["admission_count"],1)

            out = promoter.promote(
                candidate_path=str(candidate.relative_to(root)),
                receipt_path=str(receipt.relative_to(root)),
                repo_root=root,
                pointer_path=pointer,
            )
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["frontier_changed"])
            self.assertTrue(out["promotion_executed"])
            observed = admission.load_current_admissions(
                repo_root=root,
                pointer_path=pointer,
            )
            self.assertEqual(observed["manifest"]["admission_count"],1)
            self.assertEqual(
                observed["admissions"][0]["route_id"],
                "DIRECT_ADEQUACY::NEW_TEST_V1",
            )

            duplicate = promoter.promote(
                candidate_path=str(candidate.relative_to(root)),
                receipt_path=str(receipt.relative_to(root)),
                repo_root=root,
                pointer_path=pointer,
            )
            self.assertTrue(duplicate["pass"])
            self.assertFalse(duplicate["frontier_changed"])
            self.assertEqual(duplicate["status"],"ALREADY_LIVE_EXACT_BINDING")

    def test_tampered_independent_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate, receipt, _pointer = self._fixture(root)
            doc=json.loads(receipt.read_text(encoding="utf-8"))
            doc["exact_raw_obligation_acceptance"]=False
            receipt.write_text(
                json.dumps(doc,indent=2,sort_keys=True)+"\n",
                encoding="utf-8",
            )
            current = admission.load_current_admissions(repo_root=root)
            with self.assertRaises(admission.DynamicAdmissionError):
                admission.compile_admission(
                    repo_root=root,
                    current_manifest=current["manifest"],
                    candidate_path=str(candidate.relative_to(root)),
                    receipt_path=str(receipt.relative_to(root)),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
