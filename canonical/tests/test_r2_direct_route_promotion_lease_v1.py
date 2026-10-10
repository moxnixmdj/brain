from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import promote_r2_direct_route_v1 as promoter


def _hold_lease(pointer: str, ready, release) -> None:
    with promoter._promotion_lease(Path(pointer)):
        ready.set()
        release.wait(10)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _base_repo(root: Path) -> None:
    governance = root / "canonical/governance"
    verification = root / "canonical/verification"
    runtime = root / "canonical/runtime"
    governance.mkdir(parents=True)
    verification.mkdir(parents=True)
    runtime.mkdir(parents=True)

    admission = promoter.admission
    manifest_rel = "canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_BASE.json"
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
            "default": "NOT_LIVE_UNLESS_EXACT_INDEPENDENT_DEPLOYMENT_RECEIPT_VALIDATES",
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        },
    )
    _write_json(
        governance / "CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json",
        {
            "schema": admission.POINTER_SCHEMA,
            "date": "2026-10-10",
            "status": "ACTIVE_CURRENT_R2_DYNAMIC_ADMISSIONS_POINTER",
            "binding_semantics": (
                "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
            ),
            "target": {
                "path": manifest_rel,
                "git_blob_sha": admission.git_blob_sha(manifest_path),
                "schema": admission.MANIFEST_SCHEMA,
            },
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        },
    )


def _route_fixture(root: Path, suffix: str) -> tuple[str, str, str]:
    admission = promoter.admission
    route_id = f"DIRECT_ADEQUACY::CONCURRENT_TEST_{suffix}"
    capability_id = f"test.concurrent.{suffix.lower()}"

    runtime_rel = f"canonical/runtime/test_concurrent_route_{suffix.lower()}.py"
    runtime_path = root / runtime_rel
    runtime_path.write_text(
        "def preflight(request, **kwargs): return {'matched': True}\n"
        "def run(request, **kwargs): return {'pass': True}\n",
        encoding="utf-8",
    )

    verification_rel = f"canonical/verification/TEST_CONCURRENT_ROUTE_{suffix}_VERIFY.json"
    verification_path = root / verification_rel
    _write_json(
        verification_path,
        {"pass": True, "status": "INDEPENDENT_PASS", "terminal_authority": False},
    )

    candidate_rel = f"canonical/governance/TEST_CONCURRENT_ROUTE_{suffix}_CANDIDATE.json"
    candidate_path = root / candidate_rel
    _write_json(
        candidate_path,
        {
            "schema": admission.CANDIDATE_SCHEMA,
            "route_id": route_id,
            "capability_id": capability_id,
            "runtime_path": runtime_rel,
            "runtime_git_blob_sha": admission.git_blob_sha(runtime_path),
            "preflight_callable": "preflight",
            "run_callable": "run",
            "route_verification_path": verification_rel,
            "route_verification_git_blob_sha": admission.git_blob_sha(verification_path),
            "scope": f"TEST_CONCURRENT_SCOPE_{suffix}",
            "selection_class": admission.SELECTION_CLASS,
            "deployment_requested": True,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        },
    )

    receipt_rel = f"canonical/verification/TEST_CONCURRENT_ROUTE_{suffix}_RECEIPT.json"
    _write_json(
        root / receipt_rel,
        {
            "schema": admission.RECEIPT_SCHEMA,
            "status": "INDEPENDENT_PASS__R2_DIRECT_ROUTE_DEPLOYMENT",
            "candidate_path": candidate_rel,
            "candidate_git_blob_sha": admission.git_blob_sha(candidate_path),
            "route_id": route_id,
            "runtime_path": runtime_rel,
            "runtime_git_blob_sha": admission.git_blob_sha(runtime_path),
            "route_verification_path": verification_rel,
            "route_verification_git_blob_sha": admission.git_blob_sha(verification_path),
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
        },
    )
    return route_id, candidate_rel, receipt_rel


class R2DirectRoutePromotionLeaseV1Tests(unittest.TestCase):
    def test_concurrent_promotion_lease_fails_closed_without_waiting(self):
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("requires fork-capable verification host")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _base_repo(root)
            pointer = root / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"

            ctx = multiprocessing.get_context("fork")
            ready = ctx.Event()
            release = ctx.Event()
            process = ctx.Process(
                target=_hold_lease,
                args=(str(pointer), ready, release),
            )
            process.start()
            try:
                self.assertTrue(ready.wait(5), "child never acquired promotion lease")
                with self.assertRaisesRegex(
                    promoter.R2DirectRoutePromotionError,
                    "PROMOTION_LEASE_BUSY",
                ):
                    with promoter._promotion_lease(pointer):
                        self.fail("second promotion unexpectedly acquired live lease")
            finally:
                release.set()
                process.join(5)
                if process.is_alive():
                    process.terminate()
                    process.join(5)
            self.assertEqual(process.exitcode, 0)

    def test_two_verified_promotions_compose_without_lost_update(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _base_repo(root)
            route_a, candidate_a, receipt_a = _route_fixture(root, "A")
            route_b, candidate_b, receipt_b = _route_fixture(root, "B")

            first = promoter.promote(
                candidate_path=candidate_a,
                receipt_path=receipt_a,
                repo_root=root,
            )
            second = promoter.promote(
                candidate_path=candidate_b,
                receipt_path=receipt_b,
                repo_root=root,
            )

            self.assertTrue(first["pass"], first)
            self.assertTrue(second["pass"], second)
            self.assertTrue(first["frontier_changed"])
            self.assertTrue(second["frontier_changed"])
            self.assertEqual(
                first["promotion_lease_kind"],
                "LOCAL_PROCESS_FLOCK_NONBLOCKING",
            )
            self.assertEqual(
                second["promotion_lease_kind"],
                "LOCAL_PROCESS_FLOCK_NONBLOCKING",
            )

            current = promoter.admission.load_current_admissions(repo_root=root)
            ids = [row["route_id"] for row in current["admissions"]]
            self.assertEqual(current["manifest"]["admission_count"], 2)
            self.assertEqual(set(ids), {route_a, route_b})

    def test_exact_repromotion_remains_idempotent_under_lease(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _base_repo(root)
            route_id, candidate, receipt = _route_fixture(root, "IDEMPOTENT")

            first = promoter.promote(
                candidate_path=candidate,
                receipt_path=receipt,
                repo_root=root,
            )
            second = promoter.promote(
                candidate_path=candidate,
                receipt_path=receipt,
                repo_root=root,
            )

            self.assertTrue(first["frontier_changed"])
            self.assertFalse(second["frontier_changed"])
            self.assertEqual(second["status"], "ALREADY_LIVE_EXACT_BINDING")
            self.assertEqual(second["route_id"], route_id)
            self.assertEqual(
                second["promotion_lease"]["kind"],
                "LOCAL_PROCESS_FLOCK_NONBLOCKING",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
