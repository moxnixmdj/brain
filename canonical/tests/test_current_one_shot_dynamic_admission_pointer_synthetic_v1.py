from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from canonical.runtime import current_one_shot_projection_v1 as projection


def _write_text(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(root: Path, rel: str, value: dict) -> Path:
    return _write_text(root, rel, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _build_fixture(root: Path) -> tuple[str, Path]:
    for key in ("v1", "v2", "live_wrapper", "fixed_point", "v19", "v21"):
        _write_text(root, projection.PATHS[key], f"# fixture {key}\n")

    self_target = root / projection.PATHS["self"]
    self_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(projection.__file__), self_target)

    _write_json(
        root,
        projection.PATHS["r2"],
        {
            "status": "ACTIVE_CURRENT_R2_AUTHORITY__V66__FIXTURE",
            "current_cell_classifications": {},
        },
    )
    _write_json(
        root,
        projection.PATHS["terminal"],
        {"status": "TERMINAL_FALSE__FIXTURE", "pointer_revision": 1},
    )

    current_manifest_rel = (
        "canonical/governance/"
        "R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_feedfacecafebeef.json"
    )
    manifest = {
        "schema": "PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1",
        "status": "ACTIVE_DYNAMIC_ADMISSIONS__NONEMPTY",
        "admission_count": 1,
        "admissions": [{"route_id": "DIRECT_ADEQUACY::FIXTURE_DYNAMIC_V1"}],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    manifest_path = _write_json(root, current_manifest_rel, manifest)
    manifest_blob = projection._blob(manifest_path)

    admissions_pointer = {
        "schema": "PROJECT_BRAIN_CURRENT_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_POINTER_V1",
        "binding_semantics": (
            "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__IMMUTABLE_TARGET_GIT_BLOB_BOUND"
        ),
        "target": {
            "path": current_manifest_rel,
            "git_blob_sha": manifest_blob,
            "schema": "PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1",
        },
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    admissions_pointer_path = _write_json(
        root,
        projection.PATHS["dynamic_admissions_pointer"],
        admissions_pointer,
    )

    actual = {
        key: projection._blob(root / projection.PATHS[key])
        for key in ("v1", "v2", "live_wrapper", "fixed_point", "v19", "v21", "self")
    }

    default_runtime = {
        "schema": "PROJECT_BRAIN_CURRENT_DEFAULT_RUNTIME_INTEGRATION_V1",
        "binding_semantics": (
            "MUTABLE_CURRENT_PATH_IDENTITY__IMMUTABLE_LOAD_BEARING_DESCENDANTS_GIT_BLOB_BOUND"
        ),
        "status": "ACTIVE__FIXTURE",
        "r2_default_route_runtime": {
            "stable_wrapper_path": projection.PATHS["live_wrapper"],
            "stable_wrapper_git_blob_sha": actual["live_wrapper"],
            "fixed_point_controller_path": projection.PATHS["fixed_point"],
            "fixed_point_controller_git_blob_sha": actual["fixed_point"],
            "current_r2_activation_baseline": {
                "authority_pointer_path": projection.PATHS["r2"],
                "pointer_path_identity_authoritative": True,
                "runtime_path": projection.PATHS["v19"],
                "runtime_git_blob_sha": actual["v19"],
                "activation_route_count": 39,
                "role": (
                    "CURRENT_R2_SCHEDULER_AND_ACTIVATION_SNAPSHOT__"
                    "NOT_DEFAULT_RUNTIME_SOURCE_SELECTOR"
                ),
            },
            "verified_static_backend": {
                "runtime_path": projection.PATHS["v21"],
                "runtime_git_blob_sha": actual["v21"],
                "lineage": ["V21", "V20", "V19"],
                "static_default_route_count_before_dynamic": 41,
            },
            "dynamic_admission": {
                "current_pointer_path": projection.PATHS["dynamic_admissions_pointer"],
                "pointer_path_identity_authoritative": True,
                "current_pointer_git_blob_sha": "1" * 40,
                "current_manifest_path": (
                    "canonical/governance/"
                    "R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_stale0000000000.json"
                ),
                "current_manifest_git_blob_sha": "2" * 40,
                "current_dynamic_route_count": 0,
                "future_verified_route_requires_new_vN_source": False,
            },
        },
        "terminal_authority": False,
        "accounting": {"terminal_credit_delta": 0},
    }
    _write_json(root, projection.PATHS["default_runtime"], default_runtime)

    one_shot_pointer = {
        "runtime": {
            "path": projection.PATHS["v2"],
            "git_blob_sha": actual["v2"],
        },
        "predecessor": {
            "path": projection.PATHS["v1"],
            "git_blob_sha": actual["v1"],
        },
        "authority": {
            "dynamic_current_projection": {
                "path": projection.PATHS["self"],
                "git_blob_sha": actual["self"],
                "authoritative_for_moving_r2_and_terminal": True,
            },
            "static_projection_snapshots_authoritative": False,
        },
        "default_runtime_integration": {
            "path": projection.PATHS["default_runtime"],
            "pointer_semantics": "MUTABLE_CURRENT_PATH_IDENTITY_AUTHORITATIVE",
        },
        "current_projection_refresh_20261009": {},
    }
    _write_json(root, projection.PATHS["pointer"], one_shot_pointer)

    return current_manifest_rel, admissions_pointer_path


class CurrentOneShotDynamicAdmissionPointerSyntheticV1Tests(unittest.TestCase):
    def test_moving_pointer_target_is_authoritative_and_snapshot_drift_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target_rel, _ = _build_fixture(root)

            out = projection.evaluate(root)
            self.assertTrue(out["pass"], out)

            live = out["default_runtime_integration"]["dynamic_admission"]
            self.assertEqual(live["manifest_path"], target_rel)
            self.assertEqual(live["dynamic_route_count"], 1)
            self.assertEqual(out["default_runtime_integration"]["effective_known_direct_route_count"], 42)
            self.assertTrue(live["snapshot_drift"]["pointer_blob_differs_from_current"])
            self.assertTrue(live["snapshot_drift"]["manifest_path_differs_from_current"])
            self.assertTrue(live["snapshot_drift"]["manifest_blob_differs_from_current"])
            self.assertTrue(live["snapshot_drift"]["route_count_differs_from_current"])
            self.assertFalse(live["snapshot_drift"]["snapshot_is_authoritative"])

    def test_tampered_target_blob_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_fixture(root)
            pointer_path = root / projection.PATHS["dynamic_admissions_pointer"]
            pointer = projection._load(pointer_path)
            pointer["target"]["git_blob_sha"] = "0" * 40
            _write_json(
                root,
                projection.PATHS["dynamic_admissions_pointer"],
                pointer,
            )

            out = projection.evaluate(root)
            self.assertFalse(out["pass"])
            self.assertIn("DYNAMIC_ADMISSIONS_TARGET_BLOB_MISMATCH", out["errors"])

    def test_pointer_cannot_escape_dynamic_admission_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_fixture(root)
            pointer = projection._load(
                root / projection.PATHS["dynamic_admissions_pointer"]
            )
            pointer["target"]["path"] = "../../etc/passwd"
            _write_json(
                root,
                projection.PATHS["dynamic_admissions_pointer"],
                pointer,
            )

            with self.assertRaisesRegex(
                ValueError,
                "DYNAMIC_ADMISSIONS_TARGET_PATH_OUTSIDE_ALLOWED_NAMESPACE",
            ):
                projection.evaluate(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
