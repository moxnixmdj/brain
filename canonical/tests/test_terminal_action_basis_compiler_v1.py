import unittest
from canonical.runtime.terminal_action_basis_compiler_v1 import evaluate

class Tests(unittest.TestCase):
    def fixture(self):
        reg={"predicates":[{"id":"A"},{"id":"B"},{"id":"C"}]}
        ev={"claims":[{"predicate_id":"A","state":"PROVED"}]}
        hg={"actions":[
            {"id":"X","target_predicates":["B"]},
            {"id":"Y","target_predicates":["C"]},
            {"id":"Z","target_predicates":["B","C"]},
        ]}
        return reg,ev,hg

    def test_complete_and_minimal(self):
        out=evaluate(*self.fixture())
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["unresolved_predicate_count"],2)
        self.assertEqual(out["minimum_declared_action_basis"],["Z"])

    def test_uncovered_fails_closed(self):
        reg,ev,hg=self.fixture()
        hg["actions"]=[{"id":"X","target_predicates":["B"]}]
        out=evaluate(reg,ev,hg)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["uncovered_unresolved_predicates"],["C"])

    def test_unknown_target_fails_closed(self):
        reg,ev,hg=self.fixture()
        hg["actions"].append({"id":"BAD","target_predicates":["NOPE"]})
        out=evaluate(reg,ev,hg)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any(x.startswith("UNKNOWN_TARGET:BAD") for x in out["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
