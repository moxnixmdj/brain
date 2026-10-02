import copy
import unittest
from canonical.runtime.delegation_contract_proof_suite import preflight_case, score

class DelegationContractProofTests(unittest.TestCase):
    def setUp(self):
        self.hidden,self.good=preflight_case()

    def test_good(self):
        r=score(self.hidden,self.good)
        self.assertTrue(r["pass"],r)
        self.assertEqual(r["oracle_min_waves"],3)

    def test_drop_required_task(self):
        bad=copy.deepcopy(self.good)
        bad["task_ids"].remove("C"); bad["dependencies"].pop("C"); bad["assignment"].pop("C")
        bad["dependencies"]["D"]=["B"]; bad["waves"]=[["A"],["B"],["D"]]
        self.assertFalse(score(self.hidden,bad)["pass"])

    def test_spurious_dependency(self):
        bad=copy.deepcopy(self.good); bad["dependencies"]["C"]=["A","B"]
        self.assertFalse(score(self.hidden,bad)["pass"])

    def test_wrong_worker_capability(self):
        bad=copy.deepcopy(self.good); bad["assignment"]["C"]="W1"
        self.assertFalse(score(self.hidden,bad)["pass"])

    def test_serialized_schedule_rejected(self):
        bad=copy.deepcopy(self.good); bad["waves"]=[["A"],["B"],["C"],["D"]]
        self.assertFalse(score(self.hidden,bad)["pass"])

    def test_worker_double_booking_rejected(self):
        bad=copy.deepcopy(self.good)
        bad["assignment"]["C"]="W1"
        bad["waves"]=[["A"],["B","C"],["D"]]
        self.assertFalse(score(self.hidden,bad)["pass"])

    def test_expensive_distractor_rejected(self):
        bad=copy.deepcopy(self.good)
        bad["task_ids"]=["A","B","DISTRACTOR","D"]
        bad["dependencies"]={"A":[],"B":["A"],"DISTRACTOR":[],"D":["B","DISTRACTOR"]}
        bad["assignment"]={"A":"W1","B":"W1","DISTRACTOR":"W2","D":"W2"}
        bad["waves"]=[["A","DISTRACTOR"],["B"],["D"]]
        self.assertFalse(score(self.hidden,bad)["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
