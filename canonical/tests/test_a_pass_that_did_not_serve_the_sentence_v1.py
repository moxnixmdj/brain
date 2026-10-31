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
        base = _tree("needs_a_test")
        result = door.solve({
            "task_id": "PARTIAL_regression_test",
            "goal": ("The test in %s fails. Fix the bug in %s and add a regression test "
                     "that would have caught it, then make the whole suite pass."
                     % (_rel(base / "tests"), _rel(base / "app"))),
        })
        self.assertIsNot(result.get("pass"), True,
                         "a sentence asking for a regression test was certified without one")
        # The claim is withheld, and it says which effect was not served OR which
        # capability was refused -- never a bare PASS.
        named = list(result.get("unserved_effects") or [])
        named += [str(result.get("status") or "")]
        named += [str(result.get("failure_class") or "")]
        self.assertTrue(any("TEST_AUTHORING" in x or "STATED_" in x for x in named),
                        "the refusal does not name the effect that was not served: %r" % (named,))

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

    def test_the_effect_is_never_enforced_before_the_run(self):
        """It is an at-exit code, so a sentence that also asks for real work still runs."""
        self.assertIn("STATED_TEST_AUTHORING_NOT_PROVIDED_BY_CAPABILITY",
                      door._EFFECTS_AT_EXIT_CODES)
        goal = "Fix the bug in app and add a regression test that would have caught it."
        repair = {"provides": ["python.software.repair.apply"], "keywords": ["test"]}
        errors = door.stated_answer_errors(goal, repair, "python.software.repair.apply.verified.v1")
        self.assertTrue(any(e.split(":", 1)[0] == "STATED_TEST_AUTHORING_NOT_PROVIDED_BY_CAPABILITY"
                            for e in errors), errors)

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
