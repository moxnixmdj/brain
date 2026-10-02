import unittest
from canonical.runtime.terminal_action_coverage_guard_v1 import evaluate

class Tests(unittest.TestCase):
    def fixture(self):
        reg={"predicates":[{"id":"A"},{"id":"B"},{"id":"C"}]}
        ev={"claims":[{"predicate_id":"A","state":"PROVED"}]}
        hg={"actions":[
            {"id":"X","target_predicates":["B"]},
            {"id":"Y","target_predicates":["C"]},
        ]}
        return reg,ev,hg

    def test_complete(self):
        out=evaluate(*self.fixture())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["unresolved_predicate_count"],2)
        self.assertEqual(out["represented_unresolved_predicate_count"],2)

    def test_uncovered_fails_closed(self):
        reg,ev,hg=self.fixture()
        hg["actions"]=[{"id":"X","target_predicates":["B"]}]
        out=evaluate(reg,ev,hg)
        self.assertFalse(out["pass"])
        self.assertEqual(out["uncovered_unresolved_predicates"],["C"])

    def test_unknown_target_fails_closed(self):
        reg,ev,hg=self.fixture()
        hg["actions"].append({"id":"BAD","target_predicates":["NOPE"]})
        out=evaluate(reg,ev,hg)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("UNKNOWN_TARGET:BAD") for x in out["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
