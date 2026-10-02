import unittest

from canonical.runtime.typed_hypothesis_compiler import Atom, Entity, Template, compile_hypotheses


class Tests(unittest.TestCase):
    def test_instantiates_all_well_typed_supported_candidates(self):
        out = compile_hypotheses(
            entities=[
                Entity("report", frozenset({"artifact"})),
                Entity("deck", frozenset({"artifact"})),
                Entity("exec", frozenset({"audience"})),
            ],
            facts=[
                Atom("requested_for", ("report", "exec")),
                Atom("requested_for", ("deck", "exec")),
            ],
            templates=[
                Template(
                    "candidate_plan",
                    (("a", "artifact"), ("u", "audience")),
                    (Atom("requested_for", ("$a", "$u")),),
                    (Atom("plan_candidate", ("$a", "$u")),),
                )
            ],
        )
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["candidate_count"], 2)
        self.assertEqual(
            [c["binding"]["a"] for c in out["candidates"]],
            ["deck", "report"],
        )

    def test_required_facts_filter_cartesian_assignments(self):
        out = compile_hypotheses(
            entities=[
                Entity("tool_a", frozenset({"tool"})),
                Entity("tool_b", frozenset({"tool"})),
                Entity("pdf", frozenset({"format"})),
            ],
            facts=[Atom("supports", ("tool_b", "pdf"))],
            templates=[
                Template(
                    "route",
                    (("t", "tool"), ("f", "format")),
                    (Atom("supports", ("$t", "$f")),),
                    (Atom("route_candidate", ("$t", "$f")),),
                )
            ],
        )
        self.assertEqual(out["candidate_count"], 1)
        self.assertEqual(out["candidates"][0]["binding"], {"f": "pdf", "t": "tool_b"})

    def test_ambiguity_is_preserved_not_ranked_away(self):
        out = compile_hypotheses(
            entities=[
                Entity("cause_a", frozenset({"cause"})),
                Entity("cause_b", frozenset({"cause"})),
            ],
            facts=[
                Atom("supported", ("cause_a",)),
                Atom("supported", ("cause_b",)),
            ],
            templates=[
                Template(
                    "cause",
                    (("c", "cause"),),
                    (Atom("supported", ("$c",)),),
                    (Atom("cause_candidate", ("$c",)),),
                )
            ],
        )
        self.assertEqual(out["candidate_count"], 2)

    def test_wrong_type_does_not_bind(self):
        out = compile_hypotheses(
            entities=[
                Entity("x", frozenset({"artifact"})),
                Entity("y", frozenset({"tool"})),
            ],
            facts=[Atom("eligible", ("x",)), Atom("eligible", ("y",))],
            templates=[
                Template(
                    "artifact_only",
                    (("v", "artifact"),),
                    (Atom("eligible", ("$v",)),),
                    (Atom("candidate", ("$v",)),),
                )
            ],
        )
        self.assertEqual(out["candidate_count"], 1)
        self.assertEqual(out["candidates"][0]["binding"]["v"], "x")

    def test_literal_arguments_are_supported(self):
        out = compile_hypotheses(
            entities=[Entity("source", frozenset({"source"}))],
            facts=[Atom("authority", ("source", "primary"))],
            templates=[
                Template(
                    "primary_source",
                    (("s", "source"),),
                    (Atom("authority", ("$s", "primary")),),
                    (Atom("source_candidate", ("$s",)),),
                )
            ],
        )
        self.assertEqual(out["candidate_count"], 1)

    def test_unknown_template_variable_fails_closed(self):
        out = compile_hypotheses(
            entities=[Entity("x", frozenset({"thing"}))],
            facts=[],
            templates=[
                Template(
                    "bad",
                    (("x", "thing"),),
                    (),
                    (Atom("candidate", ("$missing",)),),
                )
            ],
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_duplicate_entity_ids_fail_closed(self):
        out = compile_hypotheses(
            entities=[
                Entity("x", frozenset({"thing"})),
                Entity("x", frozenset({"thing"})),
            ],
            facts=[],
            templates=[],
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_candidate_bound_escalates_without_truncation(self):
        out = compile_hypotheses(
            entities=[
                Entity("a", frozenset({"thing"})),
                Entity("b", frozenset({"thing"})),
            ],
            facts=[],
            templates=[
                Template(
                    "all",
                    (("x", "thing"),),
                    (),
                    (Atom("candidate", ("$x",)),),
                )
            ],
            max_candidates=1,
        )
        self.assertEqual(out["status"], "ESCALATE", out)
        self.assertEqual(out["reason"], "CANDIDATE_BOUND_EXCEEDED")

    def test_no_supported_candidate_is_explicit_empty_pass(self):
        out = compile_hypotheses(
            entities=[Entity("x", frozenset({"thing"}))],
            facts=[],
            templates=[
                Template(
                    "needs_fact",
                    (("x", "thing"),),
                    (Atom("known", ("$x",)),),
                    (Atom("candidate", ("$x",)),),
                )
            ],
        )
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["candidate_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
