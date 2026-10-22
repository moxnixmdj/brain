#!/usr/bin/env python3
"""A verifier step must be handed the same goal string its producer was handed.

Every clause of a compound goal is compiled with its own clause text bound to the
`goal` input. That is right for a step doing independent work and wrong for a step
whose contract is to re-check an earlier one: an independent verifier recomputes a
digest of the goal it is given and compares it against the digest the producer
recorded, so the two must receive the same string.

Measured on BENCH_GROUNDING_AND_VERIFY -- "Compile a plain goal into a bound
capability and verify the grounding." The clause split handed the producer
'Compile a plain goal into a bound capability' (sha256 8999f288...) and the
verifier 'verify the grounding' (sha256 4c9ae405...), so the verifier failed with
GOAL_HASH_MISMATCH even though the producer had succeeded.
"""
import importlib.util
import pathlib
import unittest

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPILER_PATH = CANONICAL_ROOT / "runtime" / "goal_compiler.py"

spec = importlib.util.spec_from_file_location("goal_compiler_goal_parity", COMPILER_PATH)
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)

PRODUCER = "test.grounding.produce"
VERIFIER = "test.grounding.verify"
PRODUCED_EFFECT = "test.grounding.available"
AMBIENT_EFFECT = "test.ambient.available"


def _registry():
    """Producer/verifier pair plus a verifier whose requirement is ambient.

    The second verifier mirrors archive.verify.tar_gz.gnu, which requires facts
    that no step in the plan provides. The inheritance rule must not fire on it:
    those goals currently pass and learn, and rewriting their goal string would
    change what their verifier checks.
    """
    return {
        PRODUCER: {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "requires": [],
            "provides": [PRODUCED_EFFECT],
            "cost": 1,
            "incremental_spend_usd": 0,
            "action_template": {"type": "invoke_capability",
                                "args": {"capability_id": PRODUCER, "goal": "${input.goal}"}},
        },
        VERIFIER: {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "requires": [PRODUCED_EFFECT],
            "provides": ["test.grounding.verified"],
            "cost": 1,
            "incremental_spend_usd": 0,
            "action_template": {"type": "invoke_capability",
                                "args": {"capability_id": VERIFIER, "goal": "${input.goal}"}},
        },
    }


def _goals(actions):
    out = []
    for action in actions:
        args = action.get("args") or {}
        inputs = args.get("inputs")
        out.append((args.get("capability_id"),
                    (inputs or args).get("goal") if isinstance(inputs, dict) or inputs is None
                    else args.get("goal")))
    return out


class VerifierGoalParityTests(unittest.TestCase):
    def _steps(self, clauses):
        actions = [
            {"type": "invoke_capability",
             "args": {"capability_id": PRODUCER,
                      "goal": "Compile a plain goal into a bound capability"}},
            {"type": "invoke_capability",
             "args": {"capability_id": VERIFIER, "goal": "verify the grounding"}},
        ]
        if clauses == "ambient":
            actions[1]["args"]["capability_id"] = "test.ambient.verify"
        return compiler._inherit_producer_goal_for_verifier_steps(actions, _registry())

    def test_verifier_receives_the_producers_goal_string(self):
        actions = self._steps("plan")
        self.assertEqual(
            [a["args"]["goal"] for a in actions],
            ["Compile a plain goal into a bound capability",
             "Compile a plain goal into a bound capability"],
            "the verifier must hash the same string the producer hashed",
        )

    def test_inheritance_requires_a_proved_requires_provides_relation(self):
        """Negative control: unrelated steps keep their own clause."""
        registry = _registry()
        registry[VERIFIER]["requires"] = [AMBIENT_EFFECT]
        actions = [
            {"type": "invoke_capability",
             "args": {"capability_id": PRODUCER,
                      "goal": "Compile a plain goal into a bound capability"}},
            {"type": "invoke_capability",
             "args": {"capability_id": VERIFIER, "goal": "verify the grounding"}},
        ]
        compiler._inherit_producer_goal_for_verifier_steps(actions, registry)
        self.assertEqual(actions[1]["args"]["goal"], "verify the grounding",
                         "a step that does not consume this plan's output must not be rewritten")

    def test_verifier_of_an_ambient_fact_is_untouched(self):
        """The archive verifier's requirements are ambient, so tar goals must not change."""
        registry = _registry()
        registry["test.ambient.verify"] = dict(registry[VERIFIER], requires=[AMBIENT_EFFECT])
        actions = [
            {"type": "invoke_capability",
             "args": {"capability_id": PRODUCER, "goal": "Create an archive from a manifest"}},
            {"type": "invoke_capability",
             "args": {"capability_id": "test.ambient.verify", "goal": "verify the archive"}},
        ]
        compiler._inherit_producer_goal_for_verifier_steps(actions, registry)
        self.assertEqual(actions[1]["args"]["goal"], "verify the archive")

    def test_single_step_goal_is_unchanged(self):
        actions = [{"type": "invoke_capability",
                    "args": {"capability_id": PRODUCER, "goal": "do one thing"}},
                   {"type": "finish", "args": {"summary": "DONE"}}]
        before = [dict(a["args"]) for a in actions]
        compiler._inherit_producer_goal_for_verifier_steps(actions, _registry())
        self.assertEqual([dict(a["args"]) for a in actions], before)

    def test_finish_step_without_a_capability_is_not_rewritten(self):
        actions = self._steps("plan")
        actions.append({"type": "finish", "args": {"summary": "DONE"}})
        compiler._inherit_producer_goal_for_verifier_steps(actions, _registry())
        self.assertNotIn("goal", actions[-1]["args"])

    def test_inherited_goal_never_comes_from_the_producer_output(self):
        """The string must still originate in the request, or independence is lost."""
        actions = self._steps("plan")
        self.assertEqual(actions[1]["args"]["goal"], actions[0]["args"]["goal"])
        self.assertNotIn("$result", str(actions[1]["args"]["goal"]))

    def test_real_benchmark_goal_compiles_both_steps_with_one_goal(self):
        """End-to-end against the real registry and the real goal that failed."""
        import sys
        if str(CANONICAL_ROOT.parent) not in sys.path:
            sys.path.insert(0, str(CANONICAL_ROOT.parent))
        from canonical.runtime import goal_compiler as package_compiler
        from canonical.runtime.availability_v1 import load_registry
        registry = load_registry()
        goal = "Compile a plain goal into a bound capability and verify the grounding."
        compiled = package_compiler.compile_goal(goal, registry, str(CANONICAL_ROOT.parent))
        steps = [(a.get("args") or {}).get("capability_id")
                 for a in compiled["controller_actions"]]
        self.assertIn("plain_goal.bound_capability.grounding.stdlib", steps)
        self.assertIn("plain_goal.bound_capability.grounding.verify.stdlib", steps)
        goals = []
        for action in compiled["controller_actions"]:
            args = action.get("args") or {}
            if args.get("capability_id"):
                inputs = args.get("inputs") or args
                goals.append(inputs.get("goal"))
        self.assertEqual(len(set(goals)), 1,
                         f"every capability step must carry one goal string, got {goals}")


if __name__ == "__main__":
    unittest.main()
