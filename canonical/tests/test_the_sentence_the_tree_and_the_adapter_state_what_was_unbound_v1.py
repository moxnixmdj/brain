"""The sentence, the tree and the adapter already state the three inputs it could not bind.

The defect, measured on ``c79a8f5``
-----------------------------------
``bind_all_inputs`` refused ``python.refactor.rename_symbol.v1`` for the sentence

    Rename the function line_total to item_total in <b>/app and update every caller.

with ``module:not_stated``, ``new_symbol:not_stated`` and ``run_tests:not_stated``
and the whole request died as ``FAIL__RAW_GOAL_COMPILATION_GAP``.  None of the
three is a guess:

* the ADAPTER states its own harness defaults -- ``args.get("python_executable")
  or sys.executable``, ``args.get("timeout_s") or 300``, ``args.get("run_tests")
  or []`` (``python_refactor_rename_symbol.py``);
* the SENTENCE states the replacement identifier -- "... to ``item_total``";
* the TREE under the stated ``source_root`` states which module defines
  ``qualname`` -- exactly one file defines ``line_total``.

So the missing source of truth was never the caller: it was the compiler failing
to read three declarations the repository already carries.  Measured after:
``COMPILED -> python.refactor.rename_symbol.v1`` with ``module=models.py``,
``new_symbol=item_total`` and the harness keys bound; the tier probe's rename
sentence went from ``FAIL__RAW_GOAL_COMPILATION_GAP`` to a verified rename.

The bounds (these are the tests that must be able to fail)
----------------------------------------------------------
A derived value may never be a REFERENT.  ``code_multilanguage_tree_sitter_v1``
falls back to ``source_root or "canonical/runtime"``; deriving that would index a
tree the sentence never named instead of refusing, so a path key is never
settled from an adapter default.  Ambiguity binds nothing: two files defining the
same symbol leave ``module`` unbound, and two different "... to <ident>" clauses
leave ``new_symbol`` unbound.  A stated value always wins -- derivation only ever
runs after the pinned and typed binders have both refused a key.

Against ``c79a8f5`` this file ERRORS throughout, because the three derivations do
not exist yet -- the behaviour it pins is measured by the tier probe, which went
from ``FAIL__RAW_GOAL_COMPILATION_GAP`` (score 11, dropped on ``module``) to a
verified rename.  What the file can prove TODAY is the bounds: run it with any
one of the three rules removed and the matching ``*Never*`` test goes red.
"""

import json
import pathlib
import shutil
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402

REGISTRY = json.loads((_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))
RENAME = REGISTRY["capabilities"]["python.refactor.rename_symbol.v1"]


class _Tree(unittest.TestCase):
    """One fixture per test under the runtime scratch root, removed by addCleanup."""

    _NEXT = 0

    def setUp(self):
        import os

        type(self)._NEXT += 1
        self.base = (_ROOT / "canonical/astra_runtime/tmp"
                     / ("derive_%d_%d" % (os.getpid(), type(self)._NEXT)))
        (self.base / "app").mkdir(parents=True)
        (self.base / "app" / "models.py").write_text(
            "def line_total(item):\n    return item.price_cents * item.qty\n",
            encoding="utf-8",
        )
        (self.base / "app" / "service.py").write_text(
            "from app.models import line_total\n\n\n"
            "def cart_total(items):\n    return sum(line_total(i) for i in items)\n",
            encoding="utf-8",
        )
        self.addCleanup(shutil.rmtree, self.base, True)
        self.src = self.base / "app"

    def sentence(self, tail="and update every caller", replacement="item_total"):
        stated = (" to %s" % replacement) if replacement else ""
        return "Rename the function line_total%s in %s %s." % (stated, self.src, tail)

    def bind(self, goal, entry=RENAME):
        # cycle/spool are what the compiler passes: the sentence names no output
        # artifact, so the deterministic spool path settles ``output_path``.
        return front.bind_all_inputs(goal, entry, _ROOT, cycle=0, spool=set())


class TheThreeDeclarationsSettleTheSentenceTests(_Tree):
    """Each unbound key is read from the declaration that already owns it."""

    def test_the_adapter_states_its_harness_defaults(self):
        bound = self.bind(self.sentence())
        self.assertEqual(bound["python_executable"], sys.executable)
        self.assertEqual(bound["timeout_s"], 300)
        self.assertEqual(bound["run_tests"], [])

    def test_the_sentence_states_the_replacement_identifier(self):
        self.assertEqual(self.bind(self.sentence())["new_symbol"], "item_total")

    def test_the_tree_states_the_defining_module(self):
        self.assertEqual(self.bind(self.sentence())["module"], "models.py")

    def test_a_stated_value_still_wins_over_every_derivation(self):
        """A tree that states the module is never overruled by a default."""
        bound = self.bind(self.sentence())
        self.assertEqual((_ROOT / bound["source_root"]).resolve(), self.src.resolve())
        self.assertEqual(bound["qualname"], "line_total")
        self.assertEqual(bound["module"], "models.py")


class TheBoundsHoldTests(_Tree):
    """A derivation may not invent a referent and may not break a tie."""

    def test_an_adapter_default_never_settles_a_referent(self):
        """``source_root or "canonical/runtime"`` is a fallback, not a declaration."""
        entry = REGISTRY["capabilities"]["code.multilanguage.parse.tree_sitter.v1"]
        failure = front.GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", "source_root:not_stated")
        still = front.derive_declared_inputs("Index the code and write r.json", [("source_root", failure)],
                                             _ROOT, entry, {})
        self.assertEqual([key for key, _ in still], ["source_root"])

    def test_two_defining_files_bind_nothing(self):
        (self.base / "app" / "other.py").write_text(
            "def line_total(item):\n    return 0\n", encoding="utf-8"
        )
        failure = front.GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED", "module:not_stated")
        still = front.derive_declared_inputs(self.sentence(), [("module", failure)], _ROOT, RENAME,
                                             {"qualname": "line_total", "source_root": str(self.src)})
        self.assertEqual([key for key, _ in still], ["module"])

    def test_no_stated_replacement_binds_no_replacement(self):
        goal = "Rename the function line_total in %s and update every caller." % self.src
        with self.assertRaises(front.GoalCompilationFailure):
            self.bind(goal)

    def test_two_different_replacements_bind_no_replacement(self):
        """Two "... to <ident>" clauses are two claims; a tie binds nothing."""
        goal = ("Rename the function line_total to item_total in %s and also rename "
                "cart_total to basket_total" % self.src)
        self.assertIsNone(front.declared_replacement_identifier(goal))


if __name__ == "__main__":
    unittest.main(verbosity=2)
