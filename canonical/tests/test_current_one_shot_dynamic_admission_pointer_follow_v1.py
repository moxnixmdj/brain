from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import current_one_shot_projection_v1 as projection


ROOT = Path(__file__).resolve().parents[2]


class CurrentOneShotDynamicAdmissionPointerFollowV1Tests(unittest.TestCase):
    def test_evaluate_follows_current_content_addressed_pointer_target(self):
        out = projection.evaluate(ROOT)
        self.assertTrue(out["pass"], out)

        pointer = projection._load(
            ROOT / projection.PATHS["dynamic_admissions_pointer"]
        )
        target = pointer["target"]
        manifest_path = ROOT / target["path"]
        manifest = projection._load(manifest_path)
        live = out["default_runtime_integration"]["dynamic_admission"]

        self.assertEqual(live["manifest_path"], target["path"])
        self.assertEqual(live["manifest_git_blob_sha"], projection._blob(manifest_path))
        self.assertEqual(target["git_blob_sha"], projection._blob(manifest_path))
        self.assertEqual(live["dynamic_route_count"], manifest["admission_count"])
        self.assertEqual(manifest["admission_count"], len(manifest["admissions"]))

    def test_stale_default_runtime_snapshot_is_observable_not_failure(self):
        out = projection.evaluate(ROOT)
        self.assertTrue(out["pass"], out)

        default_runtime = projection._load(
            ROOT / projection.PATHS["default_runtime"]
        )
        pointer = projection._load(
            ROOT / projection.PATHS["dynamic_admissions_pointer"]
        )
        target = pointer["target"]
        dynamic = default_runtime["r2_default_route_runtime"]["dynamic_admission"]
        drift = out["default_runtime_integration"]["dynamic_admission"]["snapshot_drift"]

        self.assertEqual(
            drift["manifest_path_differs_from_current"],
            bool(dynamic.get("current_manifest_path"))
            and dynamic.get("current_manifest_path") != target["path"],
        )
        self.assertEqual(
            drift["manifest_blob_differs_from_current"],
            bool(dynamic.get("current_manifest_git_blob_sha"))
            and dynamic.get("current_manifest_git_blob_sha") != target["git_blob_sha"],
        )
        self.assertFalse(drift["snapshot_is_authoritative"])
        self.assertNotIn(
            "DEFAULT_RUNTIME_DYNAMIC_MANIFEST_PATH_MISMATCH", out["errors"]
        )
        self.assertNotIn(
            "DEFAULT_RUNTIME_DYNAMIC_MANIFEST_BLOB_MISMATCH", out["errors"]
        )
        self.assertNotIn(
            "DEFAULT_RUNTIME_DYNAMIC_ROUTE_COUNT_MISMATCH", out["errors"]
        )

    def test_pointer_target_blob_mismatch_still_fails_closed(self):
        default_runtime = projection._load(
            ROOT / projection.PATHS["default_runtime"]
        )
        pointer = projection._load(
            ROOT / projection.PATHS["pointer"]
        )
        admissions_pointer = projection._load(
            ROOT / projection.PATHS["dynamic_admissions_pointer"]
        )
        target_path, target = projection._resolve_dynamic_admissions_manifest(
            ROOT, admissions_pointer
        )
        admissions_manifest = projection._load(target)

        static_targets = {
            name: (ROOT / rel)
            for name, rel in projection.PATHS.items()
            if name != "dynamic_admissions_manifest"
        }
        actual = {name: projection._blob(path) for name, path in static_targets.items()}
        actual["dynamic_admissions_manifest"] = projection._blob(target)

        tampered = deepcopy(admissions_pointer)
        tampered["target"]["git_blob_sha"] = "0" * 40
        _, errors = projection._default_runtime_projection(
            pointer,
            default_runtime,
            tampered,
            admissions_manifest,
            actual,
            target_path,
        )
        self.assertIn("DYNAMIC_ADMISSIONS_TARGET_BLOB_MISMATCH", errors)

    def test_out_of_namespace_target_is_rejected_before_file_access(self):
        pointer = {
            "target": {
                "path": "../../etc/passwd",
                "schema": "PROJECT_BRAIN_R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_V1",
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(
                ValueError,
                "DYNAMIC_ADMISSIONS_TARGET_PATH_OUTSIDE_ALLOWED_NAMESPACE",
            ):
                projection._resolve_dynamic_admissions_manifest(Path(tmp), pointer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
