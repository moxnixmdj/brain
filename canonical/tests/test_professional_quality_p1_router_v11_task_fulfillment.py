from __future__ import annotations
import json
from hashlib import sha256
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_p1_router_v11_task_fulfillment as v11


class V11FocusedTests(unittest.TestCase):
    def test_target_hash_is_canonical_and_exact(self):
        t={
          "objective":"o","audience":"a","source_evidence":{"x":1},
          "artifact_type":"PDF","constraints":{"n":2},
          "current_draft_or_render":{"sha256":"f"*64},
        }
        expected=sha256(json.dumps(
          t,sort_keys=True,separators=(",",":"),ensure_ascii=False
        ).encode()).hexdigest()
        self.assertEqual(v11._target_sha256(
          {"professional_target_instance":t}
        ),expected)

    def test_single_artifact_rejects_ambiguity(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"EXACTLY_ONE_ARTIFACT_PATH_REQUIRED"):
                v11._single_artifact(Path(td),["a","b"])

    def test_reject_revokes_prior_positive(self):
        out=v11._reject({
          "positive_certification_authorized":True,
          "quality_authority":False,
        },"X")
        self.assertFalse(out["positive_certification_authorized"])
        self.assertFalse(out["task_fulfillment_verified"])
        self.assertFalse(out["quality_authority"])

    def test_nonpositive_path_does_not_need_bundle(self):
        with patch.object(v11.base,"route",return_value={
          "status":"ABSTAIN",
          "positive_certification_authorized":False,
        }):
            out=v11.route({},repo_root=".")
        self.assertFalse(out["task_fulfillment_verified"])
        self.assertFalse(out["task_fulfillment_gate_required_for_nonpositive"])


if __name__=="__main__":
    unittest.main(verbosity=2)
