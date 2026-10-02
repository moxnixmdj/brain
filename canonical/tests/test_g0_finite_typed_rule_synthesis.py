import unittest

from canonical.runtime.g0_finite_typed_rule_synthesis import (
    PredicateSpec,
    RuleExample,
    synthesize_minimal_conjunctive_rule,
)


def p(pid, cost=1.0):
    return PredicateSpec(pid, "bool", {"path": "schema.json", "span": [0, 1]}, cost)


def e(eid, facts, positive):
    return RuleExample(eid, frozenset(facts), positive, {"observation_id": eid})


class Tests(unittest.TestCase):
    def test_unique_minimum_rule(self):
        out = synthesize_minimal_conjunctive_rule(
            predicates=[p("authenticated"), p("admin"), p("online")],
            examples=[
                e("p1", {"authenticated", "admin", "online"}, True),
                e("p2", {"authenticated", "admin"}, True),
                e("n1", {"authenticated", "online"}, False),
                e("n2", {"admin", "online"}, False),
            ],
            emit={"action": "allow"},
        )
        self.assertEqual(out["status"], "SYNTHESIZED_UNIQUE", out)
        ids = [x["predicate_id"] for x in out["rules"][0]["preconditions"]]
        self.assertEqual(ids, ["admin", "authenticated"])
        self.assertFalse(out["donor_runtime_required"])

    def test_equal_minimum_rules_preserve_ambiguity(self):
        out = synthesize_minimal_conjunctive_rule(
            predicates=[p("a"), p("b")],
            examples=[
                e("p", {"a", "b"}, True),
                e("n", set(), False),
            ],
            emit={"outcome": "x"},
        )
        self.assertEqual(out["status"], "SYNTHESIZED_AMBIGUOUS", out)
        self.assertEqual(len(out["rules"]), 2)
        self.assertTrue(out["ambiguity_preserved"])

    def test_cost_breaks_cardinality_tie(self):
        out = synthesize_minimal_conjunctive_rule(
            predicates=[p("a", 3), p("b", 1)],
            examples=[e("p", {"a", "b"}, True), e("n", set(), False)],
            emit={"outcome": "x"},
        )
        self.assertEqual(out["status"], "SYNTHESIZED_UNIQUE", out)
        self.assertEqual(out["rules"][0]["preconditions"][0]["predicate_id"], "b")

    def test_negative_counterexample_falsifies_rule_class(self):
        out = synthesize_minimal_conjunctive_rule(
            predicates=[p("a"), p("b")],
            examples=[
                e("p", {"a", "b"}, True),
                e("n", {"a", "b"}, False),
            ],
            emit={"outcome": "x"},
        )
        self.assertEqual(out["status"], "MODEL_FALSIFIED", out)

    def test_no_negative_examples_escalates(self):
        out = synthesize_minimal_conjunctive_rule(
            predicates=[p("a")],
            examples=[e("p", {"a"}, True)],
            emit={"outcome": "x"},
        )
        self.assertEqual(out["status"], "ESCALATE", out)

    def test_unknown_predicate_fails_closed(self):
        out = synthesize_minimal_conjunctive_rule(
            predicates=[p("a")],
            examples=[e("p", {"a", "unknown"}, True), e("n", set(), False)],
            emit={"outcome": "x"},
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_missing_provenance_fails_closed(self):
        bad = PredicateSpec("a", "bool", {})
        out = synthesize_minimal_conjunctive_rule(
            predicates=[bad],
            examples=[e("p", {"a"}, True), e("n", set(), False)],
            emit={"outcome": "x"},
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_empty_emit_fails_closed(self):
        out = synthesize_minimal_conjunctive_rule(
            predicates=[p("a")],
            examples=[e("p", {"a"}, True), e("n", set(), False)],
            emit={},
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
