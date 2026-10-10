from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

fake_v1 = types.ModuleType("canonical.runtime.one_shot_verified_closure_v1")
fake_v1.run = lambda **kwargs: {}
sys.modules.setdefault("canonical.runtime.one_shot_verified_closure_v1", fake_v1)

from canonical.runtime import one_shot_reality_closure_v2 as v2


def _closure(*, status: str, passed: bool = False, initial: str, final: str):
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
            "internal_blockers": [] if passed else ["ROOT1_GAP"],
            "evidence_blockers": [],
            "irreducible_external_information_proved": False,
        },
    }


def _provider_receipt():
    return {
        "pass": True,
        "frontier_changed": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "d" * 64,
        "reuse_or_search_trace_complete": True,
        "new_code_written": False,
        "verifier_generated_or_reused": True,
        "verifier_passed": True,
    }


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fixture(root: Path, *, tag: str = "A") -> tuple[str, str]:
    admission = v2.r2_direct_route_promoter.admission
    governance = root / "canonical/governance"
    runtime = root / "canonical/runtime"
    governance.mkdir(parents=True, exist_ok=True)
    runtime.mkdir(parents=True, exist_ok=True)

    wrapper = runtime / "r2_direct_live_admission_v1.py"
    wrapper.write_text(
        "# synthetic exact live wrapper\n",
        encoding="utf-8",
    )

    manifest_rel = (
        "canonical/governance/"
        f"R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_SYNTHETIC_{tag}.json"
    )
    manifest_path = root / manifest_rel
    _write_json(
        manifest_path,
        {
            "schema": admission.MANIFEST_SCHEMA,
            "date": "2026-10-10",
            "status": "ACTIVE_DYNAMIC_ADMISSIONS__EMPTY_BASELINE",
            "selection_class": admission.SELECTION_CLASS,
            "collision_policy": "FAIL_CLOSED_ON_ANY_OTHER_DYNAMIC_OR_LEGACY_MATCH",
            "admissions": [],
            "admission_count": 0,
            "fixture_tag": tag,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        },
    )
    manifest_sha = admission.git_blob_sha(manifest_path)
    _write_json(
        governance / "CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json",
        {
            "schema": admission.POINTER_SCHEMA,
            "date": "2026-10-10",
            "status": "ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
            "binding_semantics": (
                "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__"
                "IMMUTABLE_TARGET_GIT_BLOB_BOUND"
            ),
            "target": {
                "path": manifest_rel,
                "git_blob_sha": manifest_sha,
                "schema": admission.MANIFEST_SCHEMA,
            },
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        },
    )
    return manifest_sha, admission.git_blob_sha(wrapper)


class OneShotR2RouteDeploymentContractV1Tests(unittest.TestCase):
    def test_synthesis_provider_receives_exact_current_noninterference_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_sha, wrapper_sha = _fixture(root)
            observed = {}

            def provider(request):
                observed.update(request)
                return _provider_receipt()

            first = _closure(status="OPEN", initial="i0", final="f0")
            second = _closure(
                status="PASS", passed=True, initial="i1", final="f1"
            )
            with patch.object(v2.v1, "run", side_effect=[first, second]):
                out = v2.run(
                    repo_root=root,
                    capability_synthesis_provider=provider,
                )

            self.assertTrue(out["pass"], out)
            contract = observed["r2_direct_route_deployment_contract"]
            self.assertEqual(
                contract["schema"],
                "PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_PROVIDER_CONTRACT_V2",
            )
            self.assertTrue(contract["optional_direct_route_proposal"])
            self.assertFalse(contract["provider_deployment_authority"])
            self.assertTrue(contract["new_route_noninterference_required"])
            self.assertTrue(contract["existing_exact_binding_repromotion_exempt"])

            ni = contract["noninterference"]
            self.assertEqual(
                ni["proof_schema"],
                v2.r2_direct_route_promoter.admission.NONINTERFERENCE_SCHEMA,
            )
            self.assertEqual(
                ni["proof_class"],
                v2.r2_direct_route_promoter.admission.NONINTERFERENCE_PROOF_CLASS,
            )
            self.assertEqual(
                ni["baseline_dynamic_manifest_git_blob_sha"],
                manifest_sha,
            )
            self.assertEqual(ni["baseline_dynamic_route_ids"], [])
            self.assertEqual(
                ni["baseline_live_wrapper_git_blob_sha"],
                wrapper_sha,
            )
            self.assertIn(
                "noninterference_verification_path",
                ni["deployment_receipt_required_fields"],
            )
            self.assertIn(
                "noninterference_verification_git_blob_sha",
                ni["deployment_receipt_required_fields"],
            )
            self.assertFalse(contract["verification_authority_mutation_allowed"])
            self.assertFalse(contract["terminal_authority"])

    def test_contract_re_resolves_pointer_at_each_provider_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first_sha, _ = _fixture(root, tag="A")
            first = v2._r2_direct_route_deployment_contract(repo_root=root)
            second_sha, _ = _fixture(root, tag="B")
            second = v2._r2_direct_route_deployment_contract(repo_root=root)

            self.assertEqual(
                first["noninterference"][
                    "baseline_dynamic_manifest_git_blob_sha"
                ],
                first_sha,
            )
            self.assertEqual(
                second["noninterference"][
                    "baseline_dynamic_manifest_git_blob_sha"
                ],
                second_sha,
            )
            self.assertNotEqual(first_sha, second_sha)


if __name__ == "__main__":
    unittest.main(verbosity=2)
