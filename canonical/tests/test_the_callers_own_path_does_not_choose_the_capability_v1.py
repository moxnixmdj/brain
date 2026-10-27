#!/usr/bin/env python3
"""Two properties of the sentence must not choose the capability.

Measured on ``origin/main``, "Report the call graph of the functions in the
python file /home/user/brain/canonical/astra_runtime/tmp/x/calc.py writing the
report to .../r.json" was answered by
``document.convert.markdown_pdf.pandoc_weasyprint`` -- a Markdown-to-PDF
converter -- ahead of the four python capabilities that own the question, and
"Report who calls the function top in the python source root /home/user/brain/..."
was answered by ``brain.module.function.invoke``. Neither capability was asked
for. Both causes are mechanical.

1. **The caller's own path was voting.** The token breakdown of the second
   sentence::

       brain.module.function.invoke      674.3 = function 269.3 + brain 202.5 x2
       python.source.symbols.index.ast   483.6 = calls 403.0 + source 46.6 + python 34.1
       terminal.kstar.root.assess.stdlib 449.2 = root 44.2  + brain 202.5 x2

   ``brain`` is in ``/home/user/brain/...``, it appears twice, and it is a token
   in 100+ capability ids: 405.0 of every winner's score was the directory the
   file happens to live in. A path is data the binder binds, not a word about
   the operation -- the line ``ask_tokens`` already drew for the coverage budget,
   while the scoring loop still read the raw sentence.

2. **Saying a word twice counted as two votes.** In the first sentence
   ``report`` appears twice, at 269.3 a hit. That alone measured 538.6 -- more
   than the 505.9 scored by the capability that owns `call` and `graph` -- for a
   capability whose only match was that destination noun. Repetition is how a
   sentence is phrased, not extra evidence about what is being asked.

``route()`` now scores over ``ask_tokens(goal)`` plus the tokens of a capability
id the goal names, with each distinct token voting once. ``query_tokens`` still
reports the raw tokens, so nothing about what the model saw is hidden.

Note for the next reader who reaches for the keyword list: deleting ``report``
from ``document.convert.markdown_pdf.pandoc_weasyprint`` also fixes both
sentences, and it breaks
``test_goal_compiler.py::test_compound_goal_compiles_full_verified_audit_pipeline``.
That clause -- "create .../CAPABILITY_AUDIT.pdf from that report" -- carries no
word for markdown or convert at all; ``report`` is the only token pointing at the
source document, it lifts the converter into a 15-15 tie with the docx writer,
and ``_resolve_tie_by_executability`` then decides correctly on the ``.md`` in
context. Two scorers read the same registry and weight it 4 points versus 269.3.
The registry is right; the scorer was wrong.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest
from time import perf_counter_ns

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as model_runtime  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as ra  # noqa: E402

SCRATCH = "canonical/astra_runtime/tmp/path_does_not_choose_v1"

SOURCE = (
    "import os\n"
    "\n"
    "\n"
    "class W:\n"
    "    def spin(self):\n"
    "        return 1\n"
    "\n"
    "\n"
    "def leaf():\n"
    "    return 1\n"
    "\n"
    "\n"
    "def orphan():\n"
    "    return 2\n"
    "\n"
    "\n"
    "def top():\n"
    "    return leaf() + W().spin()\n"
)


def _fresh(name: str) -> pathlib.Path:
    d = ROOT / SCRATCH / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return d


class PathDoesNotChooseTheCapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()
        cls.dir = _fresh("route")
        (cls.dir / "calc.py").write_text(SOURCE, encoding="utf-8")

    def test_the_destination_word_does_not_let_a_converter_answer(self):
        goal = (
            "Report the call graph of the functions in the python file "
            + str(self.dir / "calc.py")
            + " writing the report to "
            + str(self.dir / "r.json")
        )
        routed = self.model.route(goal)
        self.assertTrue(routed["confident"], routed["reason"])
        self.assertEqual(routed["best"]["id"], "python.source.symbols.index.ast")
        # The converter is allowed to be a passenger -- the sentence does say
        # "report" and it is one of the words that capability indexes -- but one
        # word must not outvote the words that name the operation. Measured
        # before this change it scored 538.6 (the same word counted twice)
        # against 505.9 for the capability that owns `call` and `graph`, and won.
        scores = {row["id"]: row["score"] for row in routed["candidates"]}
        converter = "document.convert.markdown_pdf.pandoc_weasyprint"
        if converter in scores:
            self.assertLess(
                scores[converter],
                scores["python.source.symbols.index.ast"],
                "a destination noun outranked the operation the sentence asked for",
            )

    def test_where_the_file_lives_cannot_change_which_capability_answers(self):
        """The pin that would have caught both defects at once.

        The same question about two copies of the same file, in two different
        directories, must route identically. Before this change the answer
        depended on the directory name: one path contained `brain`, which is a
        token in 100+ capability ids, and that alone decided the ranking.
        """
        other = _fresh("elsewhere")
        (other / "calc.py").write_text(SOURCE, encoding="utf-8")
        template = (
            "Report who calls the function leaf in the python source root {} "
            "writing the report to " + "r.json"
        )
        first = self.model.route(template.format(self.dir))
        second = self.model.route(template.format(other))
        self.assertTrue(first["confident"], first["reason"])
        self.assertEqual(first["best"]["id"], "python.source.symbols.index.ast")
        self.assertEqual(
            first["best"]["id"],
            second["best"]["id"],
            "the same question about the same file routed differently because "
            "the file lived in a different directory",
        )

    def test_a_converter_still_owns_its_own_sentence(self):
        """The negative control for dropping the word `report`.

        Removing a keyword is only safe if the capability still answers the
        sentences that are actually about it.
        """
        cases = {
            "Convert the markdown file notes.md to a pdf document": (
                "document.convert.markdown_pdf.pandoc_weasyprint"
            ),
            "Create a docx report from the json records in data.json": (
                "docx.document.create_from_json_record"
            ),
        }
        for goal, expected in cases.items():
            with self.subTest(goal=goal):
                routed = self.model.route(goal)
                self.assertTrue(routed["confident"], routed["reason"])
                self.assertEqual(routed["best"]["id"], expected)


class TheAnswerIsAskedOfTheBytesTests(unittest.TestCase):
    """Routing is not an answer. These run the sentence and read the report.

    Stated plainly so they are not over-claimed: all three of these pass on
    ``origin/main`` too, because the live admission path already routed
    directory-scoped sentences correctly. They are pins on the *content* of the
    answer -- that "who calls leaf" is answered from the call edges and not
    invented, and that a function nothing calls is not given a caller. The two
    tests above are the ones that fail on baseline and measure this change.
    """

    @classmethod
    def setUpClass(cls):
        cls.dir = _fresh("execute")
        (cls.dir / "calc.py").write_text(SOURCE, encoding="utf-8")

    def _solve(self, name: str, goal: str) -> dict:
        return ra.solve({"task_id": "%s-%d" % (name, perf_counter_ns()), "goal": goal})

    def test_who_calls_a_function_is_answered_with_the_callers(self):
        out_path = self.dir / "wc.json"
        result = self._solve(
            "WC",
            "Report who calls the function leaf in the python source root "
            + str(self.dir)
            + " writing the report to "
            + str(out_path),
        )
        self.assertIs(result.get("pass"), True, result.get("reason"))
        self.assertEqual(result.get("compiled_capability_id"), "python.source.symbols.index.ast")
        report = json.loads(out_path.read_text(encoding="utf-8"))
        # top() is `return leaf() + W().spin()` and nothing else calls leaf.
        self.assertEqual(report["callers_of"]["leaf"], ["top"])

    def test_a_function_nothing_calls_is_not_given_a_caller(self):
        """The negative control for the test above.

        `orphan` is defined and never called. A report that invented a caller
        for it would look exactly as plausible as the right one.
        """
        out_path = self.dir / "orph.json"
        result = self._solve(
            "OR",
            "Report the symbols defined in the python source root "
            + str(self.dir)
            + " writing the report to "
            + str(out_path),
        )
        self.assertIs(result.get("pass"), True, result.get("reason"))
        report = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertNotIn("orphan", report["callers_of"])
        self.assertEqual(report["callers_of"]["leaf"], ["top"])
        self.assertEqual(report["totals"]["symbols"], 5)

    def test_the_audit_names_what_the_file_actually_contains(self):
        out_path = self.dir / "au.json"
        result = self._solve(
            "AU",
            "Audit the python source structure and imports in the source root "
            + str(self.dir)
            + " writing the report to "
            + str(out_path),
        )
        self.assertIs(result.get("pass"), True, result.get("reason"))
        report = json.loads(out_path.read_text(encoding="utf-8"))
        row = report["files"][0]
        self.assertEqual(row["imports"], ["os"])
        self.assertEqual(row["functions"], ["leaf", "orphan", "top"])
        self.assertEqual(row["classes"], ["W"])
        self.assertEqual(report["totals"]["functions"], 3)

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
