"""A registry row nobody can reach is not a capability, and a range nobody stated is not a range.

Measured 2026-10-30: ``python.refactor.extract_function.v1`` had been in the
registry since the refactor round and **no sentence could bind it**.  Its
adapter lifts a STATEMENT BLOCK and needs nine declared inputs, four of which
describe one region of one file:

    module, qualname, start_line, end_line, new_name

A human states that region as a quoted statement plus the file plus the new
name:

    "Extract the statement `total = a + b` into a new function
     named sum2 in .../pkg/calc.py."

so the honest answer was ``BINDING_REFUSED:end_line:not_stated`` -- correct,
permanent, and completely silent about the fact that every earlier slot had
been bound and that the last four are a function of bytes the sentence already
states.  The capability was dead code wearing a registry row.

This module pins the whole reachability chain, because each link failed on its
own and each one alone looked like a refusal with no defect behind it:

  1. the SENTENCE was not a SWE request at all (``extract`` was not an SWE verb,
     so derivation never ran and the binder kept demanding ``end_line``);
  2. the typed plan had no family for extraction, so it answered
     ``NO_DECISIVE_TYPED_PLAN`` and the door refused before admission;
  3. the derivation guard required the FULL contracted slot set, so a shadow
     contract that still carried one of them derived nothing.

The boundary is as important as the reachability: the adapter lifts STATEMENTS,
so a quoted sub-EXPRESSION must bind nothing.  ``Extract the expression `a + b`''
names text the capability would silently not be extracting, and a machine that
edits something adjacent to what was asked is worse than one that refuses.  Every
refusal below is held to the same invariant: the tree is byte-identical after it.
"""

import shutil
import unittest
from time import perf_counter_ns

from canonical.runtime import declared_input_derivation_v1 as dd
from canonical.runtime import live_brain_route_admission_v1 as ra
from canonical.runtime import swe_typed_plan_v1 as plan

ROOT = ra.ROOT
SCRATCH = "canonical/astra_runtime/tmp/extract1"

CALC = (
    "def add(a, b):\n"
    "    total = a + b\n"
    "    return total\n"
    "\n"
    "\n"
    "def mul(a, b):\n"
    "    return a * b\n"
)
TESTS = (
    "import unittest\n"
    "\n"
    "import calc\n"
    "\n"
    "\n"
    "class T(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(calc.add(2, 3), 5)\n"
    "\n"
    "    def test_mul(self):\n"
    "        self.assertEqual(calc.mul(2, 3), 6)\n"
)


def _fresh(name):
    d = ROOT / ("%s/%s" % (SCRATCH, name))
    shutil.rmtree(d, ignore_errors=True)
    (d / "pkg").mkdir(parents=True)
    (d / "pkg" / "calc.py").write_text(CALC, encoding="utf-8")
    (d / "pkg" / "test_calc.py").write_text(TESTS, encoding="utf-8")
    return "%s/%s/pkg" % (SCRATCH, name)


def _solve(goal):
    return ra.solve({"task_id": "EX%d" % perf_counter_ns(), "goal": goal})


def _row():
    reg = dict(ra.load_verified_registry())
    return reg["python.refactor.extract_function.v1"]


class TestTheStatedStatementIsTheStatementExtracted(unittest.TestCase):

    def test_the_sentence_reaches_the_row_and_the_row_does_the_work(self):
        """End to end: stated statement, stated name, stated file -> rewritten source."""
        base = _fresh("reach")
        calc = "%s/calc.py" % base
        goal = ("Extract the statement `total = a + b` into a new function "
                "named sum2 in %s." % calc)
        result = _solve(goal)
        self.assertTrue(
            result.get("pass"),
            "the extract row was not reached: %s / %s"
            % (result.get("status"), result.get("compiled_capability_id")),
        )
        self.assertEqual(
            result.get("compiled_capability_id"),
            "python.refactor.extract_function.v1",
            "some other capability answered an extraction",
        )
        after = (ROOT / calc).read_text(encoding="utf-8")
        self.assertIn("def sum2(a, b):", after, "the new function was never defined")
        self.assertIn("total = sum2(a, b)", after, "the site was never rewritten")
        self.assertIn("def mul(a, b):", after, "an unrelated function was destroyed")

    def test_the_whole_coordinate_comes_from_the_sentence(self):
        """Every slot the sentence determines is derived, not guessed.

        ``end_line`` was the slot that refused this row for days.  It is the end
        of the statement the sentence QUOTED -- read from the tree's own AST,
        matched on normalized source -- so the derivation cannot pick a different
        statement than the one that was stated.
        """
        base = _fresh("derive")
        calc = "%s/calc.py" % base
        goal = ("Extract the statement `total = a + b` into a new function "
                "named sum2 in %s." % calc)
        _shadow, derived, _report = dd.binding_view(goal, _row(), ROOT)
        self.assertEqual(derived.get("qualname"), "add",
                         "the enclosing function was not the one that holds the statement")
        self.assertEqual(derived.get("start_line"), 2)
        self.assertEqual(derived.get("end_line"), 2,
                         "a single-line statement has a one-line range")
        self.assertEqual(derived.get("new_name"), "sum2")
        self.assertEqual(derived.get("source_root"), base)
        self.assertTrue(str(derived.get("module")).endswith("calc.py"))

    def test_the_family_is_decisive_so_admission_is_not_skipped(self):
        """``NO_DECISIVE_TYPED_PLAN`` refused the request before ``admit`` saw it."""
        base = _fresh("family")
        goal = ("Extract the statement `total = a + b` into a new function "
                "named sum2 in %s/calc.py." % base)
        terms = plan._family_terms(goal)
        self.assertIsNotNone(terms, "no typed-plan family answers an extraction")
        self.assertEqual(terms[1], "extract",
                         "the family that answers extraction is %r" % (terms,))

    def test_a_pdf_extraction_is_not_this(self):
        """"Extract the text from the PDF" must not enter the code-transform lane."""
        self.assertFalse(dd.is_swe_request("Extract the text from the PDF report.pdf."))
        self.assertFalse(dd.is_swe_request("Summarize the spreadsheet into a report."))


class TestWhatWasNotStatedIsNotInvented(unittest.TestCase):

    def test_a_quoted_expression_binds_nothing(self):
        """The adapter lifts statements; a sub-expression is a different edit."""
        base = _fresh("expr")
        calc = "%s/calc.py" % base
        before = (ROOT / calc).read_bytes()
        goal = ("Extract the expression `a + b` into a new function "
                "named sum2 in %s." % calc)
        _shadow, derived, _report = dd.binding_view(goal, _row(), ROOT)
        self.assertNotIn("start_line", derived,
                         "an expression was bound as a statement range")
        self.assertNotIn("end_line", derived)
        result = _solve(goal)
        self.assertFalse(result.get("pass"), "a sub-expression was reported as extracted")
        self.assertEqual((ROOT / calc).read_bytes(), before,
                         "a refused extraction edited the source anyway")

    def test_a_statement_that_is_not_in_the_file_binds_nothing(self):
        base = _fresh("absent")
        calc = "%s/calc.py" % base
        before = (ROOT / calc).read_bytes()
        goal = ("Extract the statement `zzz = qqq + 1` into a new function "
                "named s2 in %s." % calc)
        _shadow, derived, _report = dd.binding_view(goal, _row(), ROOT)
        self.assertNotIn("start_line", derived)
        self.assertFalse(_solve(goal).get("pass"))
        self.assertEqual((ROOT / calc).read_bytes(), before)

    def test_no_stated_name_is_not_a_name(self):
        """"sum2" is the sentence's; the machine does not name functions for people."""
        base = _fresh("noname")
        calc = "%s/calc.py" % base
        before = (ROOT / calc).read_bytes()
        goal = ("Extract the statement `total = a + b` into a new function in %s." % calc)
        _shadow, derived, _report = dd.binding_view(goal, _row(), ROOT)
        self.assertNotIn("new_name", derived, "a name nobody stated was invented")
        result = _solve(goal)
        self.assertFalse(result.get("pass"))
        self.assertEqual((ROOT / calc).read_bytes(), before)

    def test_a_refusal_names_the_capability_it_refused(self):
        """Not anonymous: a refusal the caller cannot read is one they cannot close (P11)."""
        base = _fresh("reason")
        calc = "%s/calc.py" % base
        result = _solve("Extract the statement `total = a + b` into a new function in %s." % calc)
        self.assertIn(str(result.get("compiled_capability_id") or ""),
                      str(result.get("compiler_detail") or ""),
                      "the refusal named no capability: %s" % result.get("compiler_detail"))

    def test_a_refusal_names_the_slot_the_binder_named(self):
        """The machine held the missing slot by name and used to say only "weak evidence".

        Measured 2026-10-30: ``Refactor <path>/calc.py.`` selected
        ``crossfile_edit.choreograph``, whose own binder said
        ``BINDING_REFUSED:edits_path:0_type_compatible_existing_files_named``, and the
        refusal reached the caller as ``:not_admitted:R3_WEAK_EVIDENCE``.  Naming the
        slot changes no verdict -- it is still refused -- but it is the difference
        between "try again with more words" and "this capability wants an edits file".
        """
        base = _fresh("slot")
        calc = "%s/calc.py" % base
        result = _solve("Refactor %s." % calc)
        self.assertFalse(result.get("pass"), "an unstated refactor was reported as done")
        detail = str(result.get("compiler_detail") or "")
        binding = str((result.get("route_admission") or {}).get("typed_binding_reason") or "")
        if not binding.startswith("BINDING_REFUSED:"):
            self.skipTest("this sentence did not reach a capability that named a slot")
        slot = binding[len("BINDING_REFUSED:"):].split(":")[0]
        self.assertIn(slot, detail,
                      "the refusal did not name %r, which its own binder named: %s"
                      % (slot, detail))
        self.assertNotIn("not_admitted:", detail,
                         "the specific reason was replaced by a generic rule")


if __name__ == "__main__":
    unittest.main()
