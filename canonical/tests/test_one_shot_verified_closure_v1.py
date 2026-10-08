from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import one_shot_verified_closure_v1 as one


class OneShotVerifiedClosureV1Tests(unittest.TestCase):
    def test_r2_edge_classification_separates_external_reality(self):
        external = one._classify_r2_edge(
            "FRESH_EXTERNAL_REALITY_WHEN_THE_SELECTED_FACT_IS_NOT_PRESENT"
        )
        internal = one._classify_r2_edge(
            "GENUINELY_NEW_R3_PRIMITIVE_MUST_BE_FOUND_OR_BUILT"
        )
        self.assertEqual(external["class"], "EXTERNAL_INFORMATION")
        self.assertEqual(internal["class"], "INTERNAL_ACTIONABLE")

    def test_binding_status_is_exact_git_blob_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "x.json"
            raw = b'{"x":1}\n'
            p.write_bytes(raw)
            git_sha = hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest()
            ok = one._binding_status(
                root, {"path": "x.json", "git_blob_sha": git_sha}
            )
            self.assertTrue(ok["pass"], ok)
            bad = one._binding_status(
                root, {"path": "x.json", "git_blob_sha": "0" * 40}
            )
            self.assertFalse(bad["pass"])
            self.assertEqual(bad["reason"], "CONTENT_ADDRESS_DRIFT")

    def test_latest_r3_receipt_detects_exact_byte_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical/runtime").mkdir(parents=True)
            verify = root / "canonical/verification"
            verify.mkdir(parents=True)
            target = root / "canonical/runtime/a.py"
            target.write_text("x=1\n", encoding="utf-8")
            expected = one._git_blob_sha(target)
            receipt = {
                "status": "PASS",
                "exact_live_blobs": {
                    "canonical/runtime/a.py": expected,
                },
            }
            (verify / "R3_AUTONOMOUS_VERIFIED_COMPOUNDING_LOOP_IMPLEMENTATION_20261008_V9.json").write_text(
                json.dumps(receipt), encoding="utf-8"
            )
            fresh = one._r3_receipt_freshness(root)
            self.assertTrue(fresh["pass"], fresh)
            target.write_text("x=2\n", encoding="utf-8")
            stale = one._r3_receipt_freshness(root)
            self.assertFalse(stale["pass"])
            self.assertEqual(
                stale["reason"], "R3_RECEIPT_NOT_EXACT_CURRENT_BYTES"
            )

    def test_result_digest_is_stable_for_same_value(self):
        value = {"b": [2, 1], "a": {"x": True}}
        self.assertEqual(one._sha256_obj(value), one._sha256_obj(value))


if __name__ == "__main__":
    unittest.main(verbosity=2)
