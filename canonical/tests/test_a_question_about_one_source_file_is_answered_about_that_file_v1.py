#!/usr/bin/env python3
"""A question about one source file must be answered about that one file.

Measured on ``origin/main`` through the live admission entry, nine ordinary
software-engineering sentences produced three answers::

    count the functions in the python file F      FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
    list the imports of the python file F         FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
    which classes are defined in the python file F  -> python.contract.check.crosshair.v1, FAIL
    the call graph of the python file F           -> python.contract.check.crosshair.v1, FAIL
    who calls the function leaf in the root D     PASS
    the symbols defined in the root D             PASS
    resolve the symbol top in the root D          FAIL, JSONDecodeError
    run the python tests in the root D            PASS

Three causes, all mechanical, none of them about understanding the request.

1. **The machine had no file scope at all.** ``source_root`` is a directory key,
   so a sentence naming one ``.py`` file bound nothing and was refused before any
   adapter ran. Both ``python_source_audit`` and ``python_source_symbol_index``
   also raised ``*_ROOT_MISSING`` on anything but a directory.

2. **A precondition was paid as if it were a request.** ``goal_compiler._score``
   awards 3 points per matched ``requires`` token and counts every one as
   specificity. ``python.contract.check.crosshair.v1`` declares
   ``requires: ["python.source.file.available"]``, and on "Count the functions
   defined in the python file F ..." it collected 6 points and specificity 2 for
   requiring that a python file exist -- finishing at 22 against 15 for
   ``python.source.audit.ast``, whose matched keywords were ``functions`` and
   ``python``, the two words that ARE the question. A capability was chosen
   because both of them need a python file to be there.

   The set of such tokens is derived from the registry, never written by hand:
   among the 56 entries that declare any precondition, ``available`` appears in
   82.1%, ``file`` 55.4%, ``source`` 35.7%, ``python`` 28.6% -- then a clear gap
   to ``test``/``corpus`` at 19.6%. A precondition most of the registry shares
   discriminates nothing, so it neither scores nor counts as specificity.

3. **``python.source.symbols.resolve.v1`` demanded a JSON array.** The binder
   hands an adapter what the sentence said; "resolve the symbol top" binds the
   name ``top``, and the adapter died on ``json.loads("top")``.

All nine sentences now answer, and the answers are asserted against the bytes of
the files they describe -- including the two that matter most: a file-scoped
audit reports that file only, and a name defined in two places is reported as
MULTI_HOME with both, never as the first hit.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as ra  # noqa: E402

SCRATCH = "canonical/astra_runtime/tmp/file_scope_is_a_scope_v1"

CALC = (
    "import os\n"
    "import sys\n"
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
# A second file that defines the SAME bare name, so a resolver that stops at the
# first hit cannot pass, and an audit that walks the parent directory cannot pass.
OTHER = "def leaf():\n    return 99\n"
TESTFILE = "from calc import top\n\n\ndef test_top():\n    assert top() == 2\n"


class _Workspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = ROOT / SCRATCH / cls.__name__.lower()
        shutil.rmtree(cls.dir, ignore_errors=True)
        cls.dir.mkdir(parents=True)
        (cls.dir / "calc.py").write_text(CALC, encoding="utf-8")
        (cls.dir / "other.py").write_text(OTHER, encoding="utf-8")
        (cls.dir / "test_calc.py").write_text(TESTFILE, encoding="utf-8")

    def _ask(self, name, goal):
        return ra.solve({"task_id": "%s-%s" % (name, self.__class__.__name__), "goal": goal})


class AQuestionAboutOneFileIsAnsweredAboutThatFileTests(_Workspace):
    def test_the_audit_reports_that_file_and_not_its_siblings(self):
        """The pin that makes file scope a scope rather than a convenience.

        `other.py` sits in the same directory and also defines `leaf`. An
        implementation that widened the scope to the parent directory would
        report two files and a second `leaf`, and would look like it worked.
        """
        out = self.dir / "a.json"
        result = self._ask(
            "AUDIT",
            "Count the functions defined in the python file "
            + str(self.dir / "calc.py")
            + " and write the report to "
            + str(out),
        )
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertEqual(result.get("compiled_capability_id"), "python.source.audit.ast")
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["totals"]["files"], 1)
        self.assertEqual([p["path"].rsplit("/", 1)[-1] for p in report["files"]], ["calc.py"])
        self.assertEqual(report["files"][0]["functions"], ["leaf", "orphan", "top"])
        self.assertEqual(report["files"][0]["classes"], ["W"])
        self.assertEqual(report["files"][0]["imports"], ["os", "sys"])

    def test_the_index_answers_a_call_graph_question_about_one_file(self):
        out = self.dir / "d.json"
        result = self._ask(
            "GRAPH",
            "Report the call graph of the functions in the python file "
            + str(self.dir / "calc.py")
            + " writing the report to "
            + str(out),
        )
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertEqual(result.get("compiled_capability_id"), "python.source.symbols.index.ast")
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["totals"]["files"], 1)
        self.assertEqual(report["callers_of"]["leaf"], ["top"])

    def test_naming_a_directory_still_indexes_the_whole_tree(self):
        """The negative control for the file-scope change.

        Teaching the adapter to accept a file must not narrow what a directory
        means. Naming the directory has to reach every file in it.
        """
        out = self.dir / "dir.json"
        result = self._ask(
            "DIR",
            "Report the symbols defined in the python source root "
            + str(self.dir)
            + " writing the report to "
            + str(out),
        )
        self.assertIs(result.get("pass"), True, result.get("status"))
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["totals"]["files"], 3)
        self.assertEqual(
            sorted(m["path"].rsplit("/", 1)[-1] for m in report["modules"]),
            ["calc.py", "other.py", "test_calc.py"],
        )


class APreconditionIsNotARequestTests(unittest.TestCase):
    def test_the_nondiscriminating_set_is_derived_from_the_registry(self):
        """Recompute the set independently and require the scorer to agree.

        A hand-written word list goes stale the moment the registry changes. This
        pins the rule, not the four words it happens to produce today.
        """
        reg = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
        )["capabilities"]
        declaring = [gc._tokens(e.get("requires", [])) for e in reg.values() if e.get("requires")]
        counts = {}
        for toks in declaring:
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
        n = float(len(declaring))
        expected = frozenset(t for t, c in counts.items() if c / n > gc._REQUIRES_SHARE_CEILING)
        self.assertEqual(gc._nondiscriminating_requires_tokens(), expected)
        # The gap that makes the threshold meaningful rather than arbitrary:
        # measured, 28.6% then 19.6%, nothing in between.
        shares = sorted((c / n for c in counts.values()), reverse=True)
        just_below = max(s for s in shares if s <= gc._REQUIRES_SHARE_CEILING)
        just_above = min(s for s in shares if s > gc._REQUIRES_SHARE_CEILING)
        self.assertLess(just_below, 0.20)
        self.assertGreater(just_above, 0.28)

    def test_requiring_a_python_file_does_not_outscore_the_capability_asked_for(self):
        goal = (
            "Count the functions defined in the python file canonical/runtime/goal_compiler.py"
        )
        registry = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
        )["capabilities"]
        audit = gc._score(goal, "python.source.audit.ast", registry["python.source.audit.ast"])
        crosshair = gc._score(
            goal, "python.contract.check.crosshair.v1", registry["python.contract.check.crosshair.v1"]
        )
        self.assertGreater(audit[0], crosshair[0], (audit, crosshair))
        # The mechanism, not just the outcome: `file` and `python` are matched but
        # carry no information, so they are neither scored nor counted.
        self.assertEqual(crosshair[2]["nondiscriminating_requires"], ["file", "python"])
        self.assertEqual(crosshair[2]["informative_requires"], [])
        self.assertEqual(crosshair[1], 0)


class ANameResolvesToEveryPlaceItIsDefinedTests(_Workspace):
    def test_a_bare_name_resolves_and_an_ambiguous_name_lists_every_home(self):
        out = self.dir / "g.json"
        result = self._ask(
            "RESOLVE",
            "Resolve the symbols in the python source root "
            + str(self.dir)
            + " for the queries top, leaf, orphan writing the report to "
            + str(out),
        )
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertEqual(result.get("compiled_capability_id"), "python.source.symbols.resolve.v1")
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["query_count"], 3)
        by_name = {r["query"]["name"]: r for r in report["results"]}
        # `leaf` is defined in BOTH files. The first hit is not the answer.
        self.assertEqual(by_name["leaf"]["status"], "MULTI_HOME")
        self.assertEqual(
            sorted(d["module"].rsplit("/", 1)[-1] for d in by_name["leaf"]["definitions"]),
            ["calc.py", "other.py"],
        )
        self.assertEqual(by_name["top"]["status"], "RESOLVED")
        self.assertEqual(by_name["orphan"]["status"], "RESOLVED")

    def test_a_name_nothing_defines_is_reported_unresolved_not_invented(self):
        out = self.dir / "g2.json"
        result = self._ask(
            "MISSING",
            "Resolve the symbols in the python source root "
            + str(self.dir)
            + " for the queries top, nonexistent_symbol_xyz writing the report to "
            + str(out),
        )
        self.assertIs(result.get("pass"), True, result.get("status"))
        report = json.loads(out.read_text(encoding="utf-8"))
        by_name = {r["query"]["name"]: r for r in report["results"]}
        self.assertEqual(by_name["nonexistent_symbol_xyz"]["status"], "UNRESOLVED")
        self.assertEqual(by_name["nonexistent_symbol_xyz"]["definitions"], [])
        self.assertEqual(report["unresolved_count"], 1)


class HowAListOfNamesIsStatedTests(unittest.TestCase):
    def test_a_delimited_list_binds_every_name(self):
        from canonical.runtime import goal_front_compiler_v1 as front

        self.assertEqual(
            front._parse_typed_value("queries", " top, leaf, orphan writing the report to /tmp/r.json"),
            ["top", "leaf", "orphan"],
        )
        self.assertEqual(front._parse_typed_value("queries", " top; leaf"), ["top", "leaf"])
        self.assertEqual(front._parse_typed_value("queries", " top"), ["top"])

    def test_an_undelimited_list_binds_one_name_rather_than_guessing(self):
        """The honest limit, pinned so it cannot silently become a guess.

        `writing` is as valid an identifier as `leaf`, so an undelimited run of
        words cannot be split into names and prose by shape. Binding all of them
        would put `writing`, `report` and `to` into the artifact as UNRESOLVED
        names and report a lie about the source.
        """
        from canonical.runtime import goal_front_compiler_v1 as front

        self.assertEqual(
            front._parse_typed_value("queries", " top leaf orphan writing the report to R"),
            ["top"],
        )
        self.assertIsNone(front._parse_typed_value("queries", ""))
        self.assertIsNone(front._parse_typed_value("queries", " 7, 8"))


if __name__ == "__main__":
    unittest.main()
