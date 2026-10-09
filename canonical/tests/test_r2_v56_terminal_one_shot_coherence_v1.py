import hashlib
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
R2=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ONE=ROOT/"canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json"
SCHED=ROOT/"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V54.json"

def git_blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

class TestR2V56TerminalOneShotCoherence(unittest.TestCase):
    def test_exact_pointer_chain_and_zero_credit(self):
        r2=json.loads(R2.read_text())
        term=json.loads(TERM.read_text())
        one=json.loads(ONE.read_text())

        self.assertIn("V56",r2["status"])
        self.assertEqual(r2["scheduler_cut"]["path"],"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V54.json")
        self.assertEqual(r2["scheduler_cut"]["git_blob_sha"],git_blob(SCHED))

        self.assertEqual(term["pointer_revision"],95)
        self.assertIn("CURRENT_R2_V56",term["status"])
        src=term["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(src["path"],"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
        self.assertEqual(src["scheduler_cut"]["path"],r2["scheduler_cut"]["path"])
        self.assertEqual(src["scheduler_cut"]["git_blob_sha"],r2["scheduler_cut"]["git_blob_sha"])
        self.assertEqual(src["status"],r2["status"])
        self.assertEqual(term["live_truth"]["current_r2_scheduler_cut"],"ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V54")
        self.assertFalse(term["live_truth"]["terminal"])

        self.assertIn("CURRENT_R2_V56",one["status"])
        self.assertEqual(one["authority"]["current_r2_pointer_git_blob_sha"],git_blob(R2))
        self.assertEqual(one["authority"]["current_terminal_authority_git_blob_sha"],git_blob(TERM))
        self.assertEqual(one["authority"]["current_terminal_authority_pointer_revision"],95)
        self.assertEqual(one["authority"]["current_r2_scheduler_cut_path"],r2["scheduler_cut"]["path"])
        self.assertEqual(one["authority"]["current_r2_scheduler_cut_git_blob_sha"],r2["scheduler_cut"]["git_blob_sha"])
        self.assertTrue(one["authority"]["dynamic_current_projection"]["authoritative_for_moving_r2_and_terminal"])
        self.assertFalse(one["authority"]["static_projection_snapshots_authoritative"])
        self.assertFalse(one["current_projection_refresh_20261009"]["snapshot_authoritative"])
        self.assertTrue(one["current_main_v56_projection_reconciliation"]["terminal_remains_false"])
        self.assertEqual(one["accounting"]["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main()
