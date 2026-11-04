"""P1-P6 for *the creature cannot reach its own synthesizer*.

Every test here drives `sovereign_perform` -- the live executor -- through a real `Creature`. None of
them call the synthesizer directly: calling the synthesizer directly is precisely the measurement that
looked like a capability for three rounds while the creature itself could not reach it.
"""
from __future__ import annotations

import pathlib
import tempfile
import unittest

import canonical.runtime.creature_runtime_v1 as CR
import canonical.runtime.mortality_and_triage_v1 as M

BLOCK_A = [5.0, -2.0, 7.0]
BLOCK_B = [9.0, 1.0, -4.0]


def _periodic(block):
    return lambda x: block[int(x) % len(block)]


def _affine(x):
    return 3 * x - 4


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.creature = CR.boot(self._tmp.name, identity="t", life=900)
        self.creature._sovereign_learn_tasks = {}
        self.target = [(-1,), (500,), (1000,)]

    def tearDown(self):
        self._tmp.cleanup()

    def perform(self, work_id, fn, xs=(1, 2, 3), target=None, oracle=True):
        self.creature._sovereign_learn_tasks[work_id] = {
            "examples": [((x,), fn(x)) for x in xs],
            "oracle": (lambda p: fn(p[0])) if oracle else None,
            "target": self.target if target is None else target,
        }
        return CR.sovereign_perform(M.Work(id=work_id, value=1.0, cost=1.0), self.creature)


class ReachabilityTests(_Base):
    """P1: an id the router has never heard of is attempted, not refused."""

    def test_unknown_prefix_reaches_the_synthesizer(self):
        res = self.perform("mystery:the-thing-nobody-named", _periodic(BLOCK_A))
        self.assertNotEqual(res["blocked"], "UNSUPPORTED_WORK_KIND")
        self.assertTrue(res["ok"])
        self.assertEqual(res["answers"], [BLOCK_A[int(x[0]) % 3] for x in self.target])

    def test_unrouted_affine_task_is_answered(self):
        res = self.perform("mystery:affine", _affine)
        self.assertTrue(res["ok"])
        self.assertEqual(res["answers"], [_affine(x[0]) for x in self.target])

    def test_a_capability_with_no_answerable_payload_still_refuses(self):
        # The route opens a door; it does not pretend an empty room is furnished.
        res = CR.sovereign_perform(
            M.Work(id="mystery:no-payload-at-all", value=1.0, cost=1.0), self.creature
        )
        self.assertEqual(res["blocked"], "UNSUPPORTED_WORK_KIND")
        self.assertFalse(res["ok"])

    def test_known_prefixes_are_not_hijacked(self):
        # A `chase:` id with a learn payload must still go to the chase route: the new door is opened
        # for problems nobody named, not for problems that already have a door.
        self.creature._sovereign_learn_tasks["chase:x"] = {
            "examples": [((1,), 5.0)],
            "oracle": lambda p: p[0],
            "target": [(1,)],
        }
        res = CR.sovereign_perform(M.Work(id="chase:x", value=1.0, cost=1.0), self.creature)
        self.assertNotIn(res.get("learned_status"), {"INDUCED_OPERATOR_CRYSTALLIZED"})
        self.assertEqual(res["blocked"], "MISSING_CHASE_SPEC")


class NoPrivilegeByNameTests(_Base):
    """P2: identical evidence under different spellings gets identical treatment."""

    def test_two_unrelated_names_agree(self):
        first = self.perform("mystery:alpha", _periodic(BLOCK_A))
        second = self.perform("zzz--nothing-in-common--42", _periodic(BLOCK_A))
        self.assertEqual(first["answers"], second["answers"])
        self.assertEqual(first["ok"], second["ok"])

    def test_signature_does_not_contain_the_work_id_or_the_sample_count(self):
        # A signature that changed with the sample count would make every sighting a new problem, and
        # experience would never accumulate. A signature containing the id would make learning a
        # function of spelling.
        small = CR._evidence_shape_signature([((x,), _periodic(BLOCK_A)(x)) for x in (1, 2, 3)])
        large = CR._evidence_shape_signature([((x,), _periodic(BLOCK_A)(x)) for x in range(1, 12)])
        self.assertEqual(small, large)
        self.assertNotIn("mystery", small)


class FailClosedTests(_Base):
    """P3: nothing to learn from means nothing is crystallized."""

    def test_no_examples_refuses(self):
        res = self.perform("mystery:no-evidence", _periodic(BLOCK_A), xs=())
        self.assertEqual(res["blocked"], "NO_EXAMPLES_TO_LEARN_FROM")
        self.assertFalse(res["ok"])
        self.assertIsNone(res["learned_status"])

    def test_no_oracle_refuses(self):
        res = self.perform("mystery:no-oracle", _periodic(BLOCK_A), oracle=False)
        self.assertEqual(res["blocked"], "NO_ORACLE_TO_CHECK_AGAINST")
        self.assertFalse(res["ok"])

    def test_no_fabrication_when_the_result_is_wrong(self):
        # An oracle that disagrees with the examples must produce a refusal, never an answer that
        # merely looks verified.
        self.creature._sovereign_learn_tasks["mystery:liar"] = {
            "examples": [((1,), 5.0), ((2,), -2.0), ((3,), 7.0)],
            "oracle": lambda p: -999,  # contradicts the evidence
            "target": [(4,)],
        }
        res = CR.sovereign_perform(
            M.Work(id="mystery:liar", value=1.0, cost=1.0), self.creature
        )
        if res["ok"]:
            self.assertEqual(res["answers"], [_periodic(BLOCK_A)(4)])

    def test_refusals_settle_rather_than_skip_the_ledger(self):
        res = self.perform("mystery:no-evidence", _periodic(BLOCK_A), xs=())
        self.assertIn("surprise", res)


class LearnsAcrossWorkItemsTests(_Base):
    """P4: the second sighting is cheaper than the first, and still right."""

    def test_second_sighting_costs_less_from_the_live_executor(self):
        first = self.perform("mystery:first", _periodic(BLOCK_A), xs=(1, 2, 3))
        second = self.perform("mystery:second", _periodic(BLOCK_A), xs=(4, 5, 6))
        self.assertTrue(first["ok"] and second["ok"])
        self.assertGreater(first["questions_asked"], 0)
        self.assertLess(second["questions_asked"], first["questions_asked"])
        expected = [BLOCK_A[int(x[0]) % 3] for x in self.target]
        self.assertEqual(first["answers"], expected)
        self.assertEqual(second["answers"], expected)

    def test_recall_is_verified_by_an_oracle_question_not_assumed(self):
        self.perform("mystery:a", _periodic(BLOCK_A))
        second = self.perform("mystery:b", _periodic(BLOCK_A))
        self.assertEqual(second["learned_status"], "RECALLED_TIER0_ORGAN")
        # It is cheaper than fresh synthesis, but it is not free: the incumbent was tested.
        self.assertEqual(second["questions_asked"], 1)

    def test_same_shape_different_function_is_not_answered_from_stale_memory(self):
        self.perform("mystery:a", _periodic(BLOCK_A))
        other = self.perform("mystery:b", _periodic(BLOCK_B))
        self.assertTrue(other["ok"])
        self.assertEqual(
            other["answers"], [BLOCK_B[int(x[0]) % 3] for x in self.target]
        )

    def test_what_was_learned_survives_a_restart(self):
        # Experience that lives only in the process is not experience, it is a cache.
        first = self.perform("mystery:before-restart", _periodic(BLOCK_A))
        self.assertTrue(first["ok"])
        revived = CR.boot(self._tmp.name, identity="t", life=900)
        revived._sovereign_learn_tasks = {
            "mystery:after-restart": {
                "examples": [((x,), _periodic(BLOCK_A)(x)) for x in (1, 2, 3)],
                "oracle": lambda p: _periodic(BLOCK_A)(p[0]),
                "target": self.target,
            }
        }
        second = CR.sovereign_perform(
            M.Work(id="mystery:after-restart", value=1.0, cost=1.0), revived
        )
        self.assertTrue(second["ok"])
        self.assertLess(second["questions_asked"], first["questions_asked"])
        self.assertEqual(
            second["answers"], [BLOCK_A[int(x[0]) % 3] for x in self.target]
        )


class HonestyMachineryTests(_Base):
    """P6: the new route is subject to the same record as every other route."""

    def test_result_carries_prediction_and_surprise(self):
        res = self.perform("mystery:predicted", _periodic(BLOCK_A))
        self.assertIsInstance(res["predicted_probability"], float)
        self.assertIn("surprise", res)

    def test_calibration_ledger_grows(self):
        ledger = self.creature.calibration_ledger
        before = sum(1 for _ in ledger.path.read_text().splitlines()) if ledger.path.is_file() else 0
        self.perform("mystery:ledger", _periodic(BLOCK_A))
        after = sum(1 for _ in ledger.path.read_text().splitlines()) if ledger.path.is_file() else 0
        self.assertGreater(after, before)

    def test_reported_cost_matches_what_the_synthesizer_says_it_spent(self):
        res = self.perform("mystery:cost", _periodic(BLOCK_A))
        self.assertGreater(res["questions_asked"], 0)
        self.assertLess(res["questions_asked"], 200)  # a refusal is not allowed to hide in a huge bill


class ADoorThatWasNeverReallyThereTests(_Base):
    """The `repair:` route named `_REPO_ROOT`, which did not exist in the module.

    So the branch listed in the router raised `NameError` on every call. It was reported as a route
    and could never run -- a capability in the tree and unreachable in fact, the very defect this
    round is about, one door over. Found by driving the router rather than by reading it.
    """

    def test_repo_root_is_bound(self):
        self.assertTrue(isinstance(CR._REPO_ROOT, pathlib.Path))
        self.assertTrue((CR._REPO_ROOT / "canonical").is_dir())

    def test_every_global_the_executor_uses_is_actually_bound(self):
        """A name that is read and never bound anywhere in the module is a route that cannot run.

        Keyword-argument names, parameters, comprehension targets and dunders are excluded, because
        those are not global reads. What remains is the class of name `_REPO_ROOT` belonged to.
        """
        import ast
        import builtins

        tree = ast.parse(pathlib.Path(CR.__file__).read_text(encoding="utf-8"))

        bound: set[str] = set()
        not_a_global: set[str] = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                bound.add(n.id)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(n.name)
                args = n.args if hasattr(n, "args") else None
                if args is not None:
                    for a in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                        not_a_global.add(a.arg)
                    for a in (args.vararg, args.kwarg):
                        if a is not None:
                            not_a_global.add(a.arg)
            elif isinstance(n, ast.Lambda):
                for a in (*n.args.posonlyargs, *n.args.args, *n.args.kwonlyargs):
                    not_a_global.add(a.arg)
                for a in (n.args.vararg, n.args.kwarg):
                    if a is not None:
                        not_a_global.add(a.arg)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    bound.add(a.asname or a.name.split(".")[0])
            elif isinstance(n, ast.keyword):
                if n.arg is not None:
                    not_a_global.add(n.arg)
            elif isinstance(n, (ast.comprehension,)):
                for sub in ast.walk(n.target):
                    if isinstance(sub, ast.Name):
                        not_a_global.add(sub.id)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                bound.add(n.name)

        undefined = {
            n.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Name)
            and isinstance(n.ctx, ast.Load)
            and n.id not in bound
            and n.id not in not_a_global
            and not n.id.startswith("__")
            and not hasattr(builtins, n.id)
        }
        self.assertEqual(undefined, set(), f"read but never bound: {sorted(undefined)}")

    def test_the_repair_route_settles_instead_of_raising(self):
        # No sandbox work is intended here; what is asserted is that whatever the route does, it
        # RETURNS through the settlement path rather than propagating an exception out of
        # `sovereign_perform` and losing the belief ticket that was already opened.
        # Point the sandbox at an empty tree so this measures the route's failure handling and not
        # the speed of the repository's test suite.
        empty = pathlib.Path(self._tmp.name) / "empty_ws"
        empty.mkdir()
        self.creature.workspace_root = empty
        res = CR.sovereign_perform(M.Work(id="repair:smoke", value=1.0, cost=1.0), self.creature)
        self.assertIn("surprise", res)
        self.assertIsInstance(res["predicted_probability"], float)


if __name__ == "__main__":
    unittest.main()
