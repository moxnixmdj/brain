from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.escape_progress_13_route_manifest_v2 import validate_repo

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"


def _copy_subject(root: Path) -> None:
    overlay = json.loads((ROOT / OVERLAY).read_text(encoding="utf-8"))
    base_path = overlay["base_manifest"]["path"]
    base = json.loads((ROOT / base_path).read_text(encoding="utf-8"))
    paths = {
        OVERLAY,
        base_path,
        overlay["frozen_claim"]["path"],
        overlay["shared_progress_reduction"]["path"],
        overlay["currentness"]["tb_pointer_path"],
        overlay["currentness"]["required_rank19_authority_path"],
    }
    for row in base["rows"]:
        paths.add(row["evidence"][0])
    for rel in sorted(paths):
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)


class EscapeProgress13RouteManifestV2Tests(unittest.TestCase):
    def test_current_overlay_reconstructs_all_13_rows_and_keeps_global_gap_open(self):
        out = validate_repo(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["row_count"], 13)
        self.assertEqual(out["gap_a_count"], 9)
        self.assertEqual(out["gap_b_count"], 4)
        self.assertTrue(out["shared_well_founded_progress_measure_bound"])
        self.assertEqual(out["specific_internal_action_bindings_proved"], 0)
        self.assertFalse(out["global_repair_acquirability_proved"])
        self.assertFalse(out["global_escape_progress_totality_proved"])
        self.assertFalse(out["cc_r3_proved"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_stale_shared_progress_blob_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _copy_subject(root)
            rel = json.loads((root / OVERLAY).read_text())["shared_progress_reduction"]["path"]
            (root / rel).write_text((root / rel).read_text() + "\n", encoding="utf-8")
            out = validate_repo(root)
            self.assertFalse(out["pass"])
            self.assertIn("PROGRESS_BLOB_STALE", out["errors"])

    def test_overlay_cannot_self_promote_global_repair_acquirability(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _copy_subject(root)
            path = root / OVERLAY
            doc = json.loads(path.read_text())
            doc["shared_progress_reduction"]["global_repair_acquirability_proved"] = True
            path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            out = validate_repo(root)
            self.assertFalse(out["pass"])
            self.assertIn("REPAIR_ACQUIRABILITY_MUST_REMAIN_OPEN", out["errors"])

    def test_tb_pointer_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _copy_subject(root)
            overlay = json.loads((root / OVERLAY).read_text())
            rel = overlay["currentness"]["tb_pointer_path"]
            doc = json.loads((root / rel).read_text())
            doc["staged_rank19"]["authority_git_blob_sha"] = "0" * 40
            (root / rel).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            out = validate_repo(root)
            self.assertFalse(out["pass"])
            self.assertTrue(
                "TB_POINTER_BLOB_STALE" in out["errors"]
                or "TB_POINTER_AUTHORITY_BLOB_DRIFT" in out["errors"]
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
