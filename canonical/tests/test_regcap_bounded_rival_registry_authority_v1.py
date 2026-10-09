from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import bounded_authenticated_concept_universe_v1 as universe
from canonical.runtime import regcap_bounded_rival_registry_authority_v1 as auth
from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix


ROOT = Path(__file__).resolve().parents[2]


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(row["fragment_id"])
                for row in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


def request():
    return {
        "schema": auth.REQUEST_SCHEMA,
        "registry_id": auth.REGISTRY_ID,
        "scope_id": auth.SCOPE_ID,
    }


class Tests(unittest.TestCase):
    def test_authority_receipt_authenticates_only_bounded_registry_scope(self):
        out = auth.verify_authority_request(
            request(),
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["schema"], universe.AUTHORITY_SCHEMA)
        self.assertTrue(out["scope_completeness_authenticated"])
        self.assertTrue(out["concept_semantics_authenticated"])
        self.assertEqual(set(out["bounded_scope_complete_for"]), set(matrix.DOMAIN))
        self.assertFalse(out["open_world_ontology_complete"])
        self.assertFalse(out["terminal_authority"])

    def test_generic_universe_bridge_accepts_the_independent_authority(self):
        out = auth.resolve_authenticated_registry(
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["authenticated_scope_completeness"], out)
        self.assertTrue(out["hypothesis_set_complete"], out)
        self.assertTrue(out["candidate_set_complete_relative_to_registry"], out)
        self.assertEqual(set(out["candidate_concept_ids"]), set(matrix.DOMAIN))
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_registry_observation_tables_match_source_backed_matrix(self):
        checked = auth.load_registry(repo_root=ROOT)
        with patch.object(
            matrix,
            "verify_matrix",
            return_value={
                "pass": True,
                "candidate_domain": list(matrix.DOMAIN),
                "observations": [
                    {
                        "observation_id": oid,
                        "outcomes": dict(outcomes),
                    }
                    for oid, outcomes in matrix.OBSERVATIONS.items()
                ],
                "matrix_sha256": "b" * 64,
            },
        ):
            out = auth.verify_authority_request(
                request(),
                repo_root=ROOT,
                projection_verifier=fake_projection,
            )
        self.assertTrue(out["pass"], out)

    def test_matrix_outcome_mismatch_fails_closed(self):
        bad = {
            "pass": True,
            "candidate_domain": list(matrix.DOMAIN),
            "observations": [
                {
                    "observation_id": oid,
                    "outcomes": dict(outcomes),
                }
                for oid, outcomes in matrix.OBSERVATIONS.items()
            ],
            "matrix_sha256": "c" * 64,
        }
        bad["observations"][0]["outcomes"][matrix.DOMAIN[0]] = "TAMPERED"
        with patch.object(matrix, "verify_matrix", return_value=bad):
            out = auth.verify_authority_request(
                request(),
                repo_root=ROOT,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OBSERVATION_OUTCOME_MISMATCH", out["reason"])

    def test_wrong_scope_fails_closed(self):
        row = request()
        row["scope_id"] = "OPEN_WORLD"
        out = auth.verify_authority_request(
            row,
            repo_root=ROOT,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SCOPE_ID_MISMATCH")

    def test_registry_blob_drift_fails_closed(self):
        source = ROOT / auth.REGISTRY_PATH
        doc = json.loads(source.read_text(encoding="utf-8"))
        doc["scope_id"] = doc["scope_id"] + "-tampered"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / auth.REGISTRY_PATH
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(doc, sort_keys=True),
                encoding="utf-8",
            )
            out = auth.verify_authority_request(
                request(),
                repo_root=root,
                projection_verifier=fake_projection,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("REGISTRY_GIT_BLOB_DRIFT", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
