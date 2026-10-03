from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.root2_owner_fanout_and_capsule_verifier_v1 import verify

ROOT=Path(__file__).resolve().parents[2]
def load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

class TestRoot2OwnerFanoutCapsuleVerifierV1(unittest.TestCase):
    def setUp(self):
        self.cap=load("canonical/governance/ROOT2_UNIVERSAL_COMPARATOR_CAPSULE_V1.json")
        self.fan=load("canonical/governance/ROOT2_OWNER_CHANNEL_FANOUT_V1.json")

    def test_live_pass(self):
        out=verify(self.cap,self.fan)
        self.assertTrue(out["pass"])
        self.assertEqual(out["owner_channel_count"],5)
        self.assertEqual(out["directly_targeted_root2_fixed_bar_predicates"],9)
        self.assertFalse(out["generic_external_task_entrypoint_bound"])

    def test_missing_owner_fails(self):
        fan=copy.deepcopy(self.fan)
        fan["channels"]=fan["channels"][:-1]
        self.assertFalse(verify(self.cap,fan)["pass"])

    def test_nonzero_spend_fails(self):
        fan=copy.deepcopy(self.fan)
        fan["incremental_spend_usd"]=1
        self.assertFalse(verify(self.cap,fan)["pass"])

    def test_fake_entrypoint_claim_fails(self):
        cap=copy.deepcopy(self.cap)
        cap["current_brain_execution_seams"]["generic_external_task_entrypoint"]="fake.py"
        self.assertFalse(verify(cap,self.fan)["pass"])

    def test_unstarted_channel_fails(self):
        fan=copy.deepcopy(self.fan)
        fan["channels"][0]["state"]="PLANNED"
        self.assertFalse(verify(self.cap,fan)["pass"])

if __name__=="__main__":
    unittest.main()
