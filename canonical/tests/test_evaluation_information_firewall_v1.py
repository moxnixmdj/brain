from __future__ import annotations
import unittest
from canonical.runtime.evaluation_information_firewall_v1 import evaluate, transition


class Tests(unittest.TestCase):
    def test_post_exposure_repo_search_denied(self):
        state = {
            "lane_id": "x",
            "task_identity_exposed": True,
            "clean_qualification_active": True,
            "revoked_capabilities": [],
        }
        out = evaluate(state, "REPO_SEARCH")
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["request_allowed"])

    def test_post_exposure_exact_blob_allowed(self):
        state = {
            "lane_id": "x",
            "task_identity_exposed": True,
            "clean_qualification_active": True,
            "revoked_capabilities": [],
        }
        out = evaluate(state, "EXACT_FROZEN_BLOB_READ")
        self.assertTrue(out["request_allowed"])

    def test_exposure_cannot_reverse(self):
        prev = {
            "lane_id": "x",
            "task_identity_exposed": True,
            "clean_qualification_active": True,
            "revoked_capabilities": ["REPO_SEARCH"],
        }
        nxt = {
            "lane_id": "x",
            "task_identity_exposed": False,
            "clean_qualification_active": True,
            "revoked_capabilities": ["REPO_SEARCH"],
        }
        out = transition(prev, nxt)
        self.assertFalse(out["pass"])
        self.assertIn("IDENTITY_EXPOSURE_CANNOT_BE_REVERSED", out["errors"])

    def test_revocation_cannot_restore(self):
        prev = {
            "lane_id": "x",
            "task_identity_exposed": True,
            "clean_qualification_active": True,
            "revoked_capabilities": [],
        }
        nxt = {
            "lane_id": "x",
            "task_identity_exposed": True,
            "clean_qualification_active": True,
            "revoked_capabilities": [],
        }
        out = transition(prev, nxt)
        self.assertTrue(out["pass"], out)
        self.assertIn("REPO_SEARCH", out["state"]["revoked_capabilities"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
