"""A PASS that served some of the sentence is not a PASS, and the work still stands.

Measured on main `b68f7c7`, 2026-10-31, with the filesystem as the oracle:

    "The test in <D>/tests fails.  Fix the bug in <D>/app and add a regression test
     that would have caught it, then make the whole suite pass."
      -> python.software.repair.apply.verified.v1
      -> PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED__…
      -> tree: app fixed, suite green, and NO test file anywhere

Two effects were asked for, one was delivered, and the door stamped the whole thing
VERIFIED.  The composed branch already refused to do that -- it reads its verifier's
verdict and demotes itself (`FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED`) -- so the one
route that could lie was the single-capability route.

The law pinned here:

  * a stated effect the row cannot supply is a reason NOT to refuse the whole sentence
    when the sentence asks for other work the row can do (`_EFFECTS_AT_EXIT_CODES`);
  * it is enforced at the EXIT instead: `pass` is withheld, the effect is named, and
    `work_performed_anyway` says the change really landed;
  * the check reads what a row PRODUCES (id, `provides`, `target_effects`,
    `result_fields`) and never the whole row text -- a test-GUIDED repair mentions tests
    everywhere, and grepping the row let it certify "add a regression test".
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import unittest

from canonical.runtime import live_brain_route_admission_v1 as door

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = ROOT / "canonical/astra_runtime/tmp/test_a_pass_that_did_not_serve_the_sentence"

# The fixture the measurement used (`advanced_swe_probe_20261030.py:_fresh`), copied
# rather than paraphrased: a dataclass-free model with the fields the sentence names, and a
# service whose total ignores quantity.
MODELS = (
    '"""Models."""\n\n\n'
    "class Item:\n"
    "    def __init__(self, name, price_cents, qty=1):\n"
    "        self.name = name\n"
    "        self.price_cents = price_cents\n"
    "        self.qty = qty\n\n"
    "    def subtotal(self):\n"
    "        return self.price_cents * self.qty\n\n\n"
    "def line_total(item):\n"
    "    return item.price_cents * item.qty\n"
)
SERVICE = (
    '"""Logic."""\n'
    "from app.models import Item, line_total\n\n\n"
    "def cart_total(items):\n"
    "    return sum(i.price_cents for i in items)\n"
)
TEST_SERVICE = (
    "import unittest\n\n"
    "from app.models import Item\n"
    "from app.service import cart_total\n\n\n"
    "class CartTotals(unittest.TestCase):\n"
    "    def test_quantity_counts(self):\n"
    "        items = [Item('a', 450, 2)]\n"
    "        self.assertEqual(cart_total(items), 900)\n\n\n"
    "if __name__ == '__main__':\n"
    "    unittest.main()\n"
)


def _tree(tag: str) -> pathlib.Path:
    d = BASE / tag
    if d.exists():
        shutil.rmtree(d)
    for sub in ("app", "tests"):
        (d / sub).mkdir(parents=True)
    (d / "app/__init__.py").write_text("", encoding="utf-8")
    (d / "app/models.py").write_text(MODELS, encoding="utf-8")
    (d / "app/service.py").write_text(SERVICE, encoding="utf-8")
    (d / "tests/__init__.py").write_text("", encoding="utf-8")
    (d / "tests/test_service.py").write_text(TEST_SERVICE, encoding="utf-8")
    # The measured fixture is a repository: several lanes read history to prove a change.
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q"], cwd=str(d), check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(d), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=str(d), check=True,
                   capture_output=True, env={**os.environ, **env})
    return d


def _rel(p: pathlib.Path) -> str:
    return p.relative_to(ROOT).as_posix()


class APartialAnswerIsNotAPassTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(BASE, ignore_errors=True)

    def test_a_second_effect_the_row_cannot_supply_withholds_the_pass(self):
        """End to end through the one exit every route passes.

        The reproduction is the ladder job ``fix_then_regression_test``
        (``hardcore_swe_surface_probe_20261030.py``): on ``b68f7c7`` that sentence reached
        ``python.software.repair.apply.verified.v1``, fixed the tree, left the suite green
        and reported PASS with no test file anywhere.  A hand-built tree does not reach
        that row (it stops at ``CAPABILITY_RETURNED_A_VERDICT``, measured), so the
        reproduction lives in the probe; this pins the law it exercises, at the exit.
        """
        goal = ("Fix the bug in app and add a regression test that would have caught it, "
                "then make the whole suite pass.")
        result = {"pass": True,
                  "status": "PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED",
                  "capability_id": "python.software.repair.apply.verified.v1",
                  "execution": {"steps": [
                      {"capability_id": "python.software.repair.apply.verified.v1"}]}}
        closed = door._close_observations(result, goal, None)
        self.assertIsNot(closed.get("pass"), True,
                         "a sentence that asked for a regression test passed without one")
        self.assertEqual(closed.get("status"), "FAIL_CLOSED__STATED_EFFECT_NOT_PROVIDED_BY_THE_RUN")
        self.assertEqual(list(closed.get("unserved_effects") or []),
                         ["STATED_TEST_AUTHORING_NOT_PROVIDED_BY_CAPABILITY"])
        self.assertTrue(closed.get("work_performed_anyway"),
                        "work that landed must not be denied")
        self.assertTrue(str(closed.get("runtime_status_before_effect_check") or "").startswith("PASS__"),
                        "what the runtime did must stay in the record")

    def test_the_check_reads_what_a_row_produces_not_what_it_is_tagged_with(self):
        """The seam: a test-GUIDED repair mentions tests everywhere and supplies none."""
        goal = ("Fix the bug in app and add a regression test that would have caught it, "
                "then make the whole suite pass.")
        repair = {"capability_id": "python.software.repair.apply.verified.v1",
                  "provides": ["python.software.repair.apply", "test_guided_repair"],
                  "keywords": ["test", "tests", "repair", "fix", "suite"],
                  "result_fields": ["tests_run", "passed"]}
        generated = {"capability_id": "python.tests.generate.scaffold.v1",
                     "provides": ["python.tests.generate.scaffold"],
                     "keywords": ["test"], "result_fields": ["tests_written"]}
        self.assertEqual(
            door._enforced_at_exit(goal, [repair], [repair["capability_id"]]),
            ["STATED_TEST_AUTHORING_NOT_PROVIDED_BY_CAPABILITY"],
            "a repair row that merely mentions tests was read as authoring one")
        self.assertEqual(
            door._enforced_at_exit(goal, [generated], [generated["capability_id"]]), [],
            "the row that does generate tests was refused")

    def test_a_test_file_that_appeared_is_the_effect_however_silent_the_row_is(self):
        """Measured false negative: the feature row wrote test_total.py and declared nothing."""
        base = _tree("wrote_a_test")
        before = {"files": {"%s/app/models.py" % _rel(base): [1, 1]}}
        (base / "tests/test_total.py").write_text("def test_it():\n    assert True\n", encoding="utf-8")
        goal = ("Add a function total_cents(item) to %s/app/models.py and add a test for it "
                "in %s/tests/test_total.py." % (_rel(base), _rel(base)))
        self.assertEqual(
            door._enforced_at_exit(goal, [{"provides": ["python.feature.implement_function_spec"]}],
                                   ["python.feature.implement_function_spec.v1"], before), [],
            "a test file the run actually wrote was not read as the effect")

    def test_a_row_that_declares_it_synthesizes_the_test_is_not_demoted(self):
        """The registry declaration outranks every token; a capable row keeps its pass."""
        goal = "Fix the bug in app and add a regression test that would have caught it."
        capable = {"provides": ["software.repair.crossfile.choreograph"],
                   "action_template": {"args": {"synthesize_regression_test": True}}}
        self.assertEqual(
            door._enforced_at_exit(goal, [capable],
                                   ["software.repair.crossfile.choreograph.v1"]), [],
            "a row that declares synthesize_regression_test was demoted anyway")

    def test_the_effect_is_never_enforced_before_the_run(self):
        """It is an at-exit code: the answer gate may not judge it, the exit must."""
        self.assertIn("STATED_TEST_AUTHORING_NOT_PROVIDED_BY_CAPABILITY",
                      door._EFFECTS_AT_EXIT_CODES)
        goal = "Fix the bug in app and add a regression test that would have caught it."
        repair = {"provides": ["python.software.repair.apply"], "keywords": ["test"]}
        self.assertEqual(
            door.stated_answer_errors(goal, repair, "python.software.repair.apply.verified.v1"), [],
            "the answer gate judged an effect only the exit can see")

    def test_the_plan_is_not_refused_before_the_run_for_the_unserved_effect(self):
        """Refusal costs the work the sentence also asked for -- measured 27/28 vs 28/28."""
        from canonical.runtime import swe_typed_plan_v1 as plan
        goal = ("Fix the bug in app and add a regression test that would have caught it, "
                "then make the whole suite pass.")
        self.assertIsNone(
            plan.implementation_effect_error(goal, ["python.software.repair.apply.verified.v1"], {}),
            "the plan was refused before the run for an effect the exit now withholds")
        # The sibling rule in the same block still fires: a query nothing serves is a gap.
        self.assertEqual(
            plan.implementation_effect_error(
                "Find every caller of the function parse in app", ["python.code.index.v1"], {}),
            "R10_CALLER_QUERY_EFFECT_UNSERVED")

    def test_a_sentence_that_asks_for_a_name_is_not_a_request_to_author_a_test(self):
        """Negative control: 'write the test name' asks for a NAME."""
        base = _tree("a_name")
        result = door.solve({
            "task_id": "PARTIAL_name_is_not_a_test",
            "goal": ("One test in %s fails intermittently. Find it and write the test name to %s."
                     % (_rel(base / "tests"), _rel(base / "answer.json"))),
        })
        self.assertNotIn("STATED_TEST_AUTHORING_NOT_PROVIDED_BY_CAPABILITY",
                         list(result.get("unserved_effects") or []),
                         "a request for a test's NAME was read as a request to author one")


if __name__ == "__main__":
    unittest.main()
