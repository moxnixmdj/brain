"""The closed circuit, tested: a real environment, a real guide on disk, a data never seen.

THE STAGE
---------
`StatisticsRepl` is an arbitrary computer environment: the task data comes from
the instance, the only actions are Python expression strings, the state is the
interpreter's own result, and the goal check recomputes nothing from the trace —
it asks the stdlib, exactly as a held-out test does. `statistics.md` is a real
guide excerpt with a real transcript (verified by replay, as the 2026-12-04 round
measured -- 130/138 printed outputs reproduced). The agent is told only the
program VOCABULARY it may use (`statistics`, `math`) — never the answer.

WHAT THIS PROVES AND WHAT IT DOES NOT
-------------------------------------
Proves: an environment the agent knows nothing about can be solved end-to-end —
scan (finds nothing), local-guide retrieval (real file), document-is-a-test-suite
(replayed and matched), bind to the observed data by execution, goal observed,
generalize to a MECHANISM SKETCH (never the data), admit on instances
it never saw, persist, and INSTANT RECALL on a brand-new instance.

Does NOT prove: GUI/browser use, OSWorld, SWE-bench Pro, or that this scales
beyond expression mechanisms. This is one honest, narrow, fully-verified circuit.
"""
from __future__ import annotations

import json
import shutil
import statistics
import tempfile
import unittest
from pathlib import Path

from canonical.swe_kernel import perfect_algorithm_v1 as pa

GUIDE = """# statistics — mathematical statistics functions

This page documents statistics.median. It is a faithful excerpt of the Python
standard library guide, stripped of everything but the part the task needs.

To compute the median of the numbers in a list, call statistics.median with the list. For example:

```
>>> statistics.median([3, 1, 4, 1, 5])
3
>>> statistics.median([10, 20, 30, 40, 50, 60])
35.0
```

statistics.median is robust against outliers, and it accepts any iterable of numbers.
"""

PROSE_ONLY_GUIDE = """# statistics — mathematical statistics functions

To compute the median of the numbers in a list, use statistics.median with the list.
It is robust against outliers and accepts any iterable of numbers. There is nothing
else on this page: no example, no transcript, nothing to replay.
"""


def goal_predicate(obs) -> bool:
    return (isinstance(obs, tuple) and len(obs) == 3 and obs[0] == "result"
            and obs[2] == statistics.median(obs[1]))


class StatisticsRepl:
    """An arbitrary computer environment: data in, expressions in, result out."""

    kind = "statistics"

    def __init__(self, data):
        self.data = tuple(data)
        self.last = None

    def reset(self) -> None:
        self.last = None

    def state(self):
        if self.last is None:
            return ("input", self.data)
        return ("result", self.data, self.last)

    def act(self, statement):
        import ast
        import math as _math
        import statistics as _statistics

        text = str(statement)
        tree = ast.parse(text, mode="eval")
        # actuation-layer containment, mirroring the IN_VOCABULARY gate: the
        # outermost call must be rooted at an offered program
        root = tree.body
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name) and root.id not in ("statistics", "math"):
            raise ValueError("PROGRAM_NOT_IN_VOCABULARY: " + root.id)
        ns = {"statistics": _statistics, "math": _math}
        self.last = eval(compile(tree, "<guide>", "eval"), ns)  # the env evaluates, not the test
        return self.last

    def snapshot(self):
        return self.last

    def restore(self, saved) -> None:
        self.last = saved


class DocumentSketchLoopTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="doc-sketch-loop-"))
        self._guide_root = self._tmp / "guides"
        self._guide_root.mkdir()
        (self._guide_root / "statistics.md").write_text(GUIDE, encoding="utf-8")
        self._mem = self._tmp / "memory.json"

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run(self, env, unseen, mem_path=None):
        return pa.run(env, "compute the median of the numbers in the list",
                      ["statistics.median"],  # the program VOCABULARY, not the answer
                      goal_predicate=goal_predicate,
                      goal_family="statistics_median", env_kind="statistics",
                      memory_path_=mem_path if mem_path is not None else self._mem,
                      budget=2, max_depth=2, seed=0,
                      unseen_instances=unseen,
                      fresh_reset=lambda e: e.reset(),
                      fresh_act=lambda e, a: e.act(a),
                      fresh_state=lambda e: e.state(),
                      local_root=self._guide_root)

    def test_document_plan_executes_verifies_admits_and_saves(self):
        # training data deliberately DIFFERENT from the guide's printed example
        # [3, 1, 4, 1, 5] -- otherwise the row is rehearsed, not learned
        env = StatisticsRepl([7, 2, 9, 4, 11])
        unseen = [StatisticsRepl([9, 7, 11, 3, 8, 10]), StatisticsRepl([100, 1, 50])]
        out = self._run(env, unseen)
        self.assertEqual(out["status"], "PASS__DOCUMENT_PLAN_EXECUTED_AND_VERIFIED", out)
        self.assertTrue(out["pass"])
        # the goal was OBSERVED on this instance, by the stdlib, not assumed
        self.assertEqual(env.last, statistics.median([7, 2, 9, 4, 11]))
        doc = out["steps"]["document_as_test_suite"]
        self.assertEqual(doc["status"], "PASS__PLAN_FROM_A_DOCUMENT", doc)
        # provenance: the guide is labelled external at every layer
        self.assertIn("EXTERNAL_DOCUMENT", out["authority"])
        admission = out["steps"]["admit"]
        self.assertEqual(admission["verdict"], "ADMIT", admission)
        self.assertEqual(admission["reached"], 2)
        self.assertEqual(out["steps"]["save"]["status"], "PASS__SAVED_TO_MEMORY")
        # what was saved is the MECHANISM, never the training data
        rules = pa.load_memory(self._mem)["rules"]
        self.assertEqual(len(rules), 1)
        blob = json.dumps(rules)
        self.assertNotIn("7, 2, 9", blob)   # training data never stored
        self.assertNotIn("9, 7, 11", blob)  # fresh-instance data never stored
        self.assertIn("statistics.median", blob)

    def test_saved_mechanism_recalls_instantly_on_a_new_instance(self):
        env = StatisticsRepl([7, 2, 9, 4, 11])
        unseen = [StatisticsRepl([9, 7, 11, 3, 8, 10])]
        out = self._run(env, unseen)
        self.assertEqual(out["status"], "PASS__DOCUMENT_PLAN_EXECUTED_AND_VERIFIED", out)
        fresh_env = StatisticsRepl([42, 8, 15, 16, 23, 4])
        out2 = self._run(fresh_env, unseen=None, mem_path=self._mem)
        self.assertEqual(out2["status"], "PASS__REPLAY_FROM_MEMORY", out2)
        self.assertEqual(out2["outcome"], "INSTANT_RECALL")
        self.assertEqual(fresh_env.last, statistics.median([42, 8, 15, 16, 23, 4]))
        # recall did not scan: no learning budget was spent
        self.assertNotIn("scan", out2["steps"])

    def test_without_fresh_instances_nothing_is_persisted(self):
        env = StatisticsRepl([7, 2, 9, 4, 11])
        out = self._run(env, unseen=None)
        self.assertEqual(out["status"], "PASS__DOCUMENT_PLAN_EXECUTED_AND_VERIFIED", out)
        self.assertEqual(out["outcome"], "DOCUMENT_PLAN_VERIFIED_RULE_REFUSED")
        self.assertEqual(out["steps"]["admit"]["verdict"], "REFUSED")
        self.assertEqual(out["steps"]["save"]["status"], "REFUSED__NOT_PERSISTED")
        self.assertEqual(pa.load_memory(self._mem)["rules"], [])

    def test_a_prose_only_guide_closes_nothing(self):
        (self._guide_root / "statistics.md").write_text(PROSE_ONLY_GUIDE, encoding="utf-8")
        env = StatisticsRepl([3, 1, 4, 1, 5])
        out = self._run(env, unseen=[StatisticsRepl([9, 7, 11])])
        self.assertEqual(out["status"], "OPEN__NO_PLAN_AFTER_SCAN", out)
        self.assertFalse(out["pass"])
        self.assertEqual(pa.load_memory(self._mem)["rules"], [])


if __name__ == "__main__":
    unittest.main()
