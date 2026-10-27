#!/usr/bin/env python3
"""Two vetoes that stopped ordinary software-engineering sentences being answered.

Measured on this tree, thirteen everyday sentences a software engineer would
type -- "count the functions defined in <file>", "list the imports of <file>",
"report the cyclomatic complexity of <file>", "run the tests in <root>" --
produced **zero** answers. Two separate gates were responsible, and neither had
anything to do with understanding the request.

1. ``route()`` charged the tokens of a *stated path* to the coverage budget.
   ``/home/user/brain/canonical/astra_runtime/tmp/x/calc.py`` contributes eleven
   tokens no capability can ever claim, so "Count the functions defined in the
   python file <that path>" measured coverage 0.240 against the 0.34 floor and
   was refused as ``GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED`` before a single
   capability was considered. The same request with the paths written as bare
   filenames measured 0.556 and routed. The verdict was a lottery on how long
   the caller's paths were.

2. A capability whose declared substrate is absent was still selected.
   ``python.contract.check.crosshair.v1`` runs ``sys.executable -m crosshair``;
   crosshair is not installed here and never can be at $0 spend. Nothing
   declared that dependency -- the registry records the PyPI *project* name
   ``crosshair-tool``, which is not the name Python imports -- so the capability
   looked satisfied and was chosen for eight of the thirteen sentences, then
   failed every one with ``BOUND_PYPI_SOURCE_INCOMPLETE``.

Both fixes are declarations, not permissions: nothing here widens what may run.
A path is still bound by the binder, an unstated input still fails closed
(``missing_inputs_fail_closed``), and an out-of-domain sentence still fails
closed whether or not it names real files.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as model_runtime  # noqa: E402
from canonical.runtime import compile_brain_unified_model_v1 as compiler  # noqa: E402

ARTIFACT = ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"


def _module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


class StatedPathIsNotAWordOfTheAskTests(unittest.TestCase):
    """A path the caller typed is data to be bound, not a word to be covered."""

    def test_a_real_path_is_found_and_its_tokens_leave_the_ask(self):
        real = "canonical/runtime/brain_unified_model_v1.py"
        goal = "count the functions defined in the python file " + real
        self.assertEqual(model_runtime.path_literals(goal), [real])
        ask = model_runtime.ask_tokens(goal)
        self.assertNotIn("brain", ask)
        self.assertNotIn("canonical", ask)
        self.assertIn("count", ask)
        self.assertIn("functions", ask)

    def test_prose_that_has_the_shape_of_a_path_is_still_a_word_of_the_ask(self):
        """The negative control for the rule above.

        "and/or", "read/write" and "input/output" all match the path grammar. If
        the rule blanked anything with a slash in it, a sentence could be made
        to look understood by typing slashes. They resolve to no existing parent
        directory, so they stay question words and still count against the
        budget.
        """
        goal = "read/write the and/or of input/output"
        self.assertEqual(model_runtime.path_literals(goal), [])
        self.assertEqual(
            model_runtime.ask_tokens(goal), ["read", "write", "input", "output"]
        )

    def test_a_path_under_no_existing_directory_is_not_blanked(self):
        """Fail closed: a path that is nowhere is not a located artifact."""
        goal = "count the functions in canonical/runtime/zz_no_such_dir_zz/mod.py"
        self.assertEqual(model_runtime.path_literals(goal), [])
        self.assertIn("zz_no_such_dir_zz", model_runtime.ask_tokens(goal))


class CoverageBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()

    def test_naming_a_real_artifact_is_not_a_reason_to_refuse_the_request(self):
        real = "canonical/runtime/brain_unified_model_v1.py"
        out = "canonical/astra_runtime/tmp/route_ask.json"
        goal = (
            "count the functions defined in the python file "
            + real
            + " and write the report to "
            + out
        )
        routed = self.model.route(goal)
        self.assertTrue(
            routed["confident"],
            "a sentence that names two real files was refused; the paths were "
            "charged to the coverage budget: coverage=" + str(routed["coverage"]),
        )
        # The claim in one line: how long the caller's paths are makes no
        # difference to the verdict. The same sentence with the paths deleted
        # must measure exactly the same coverage.
        bare = self.model.route(
            "count the functions defined in the python file and write the report to"
        )
        self.assertEqual(routed["coverage"], bare["coverage"])
        self.assertGreaterEqual(routed["coverage"], self.model.min_coverage)
        # And the capability chosen is the one the bare sentence chooses.
        self.assertEqual((routed["best"] or {}).get("id"), (bare["best"] or {}).get("id"))

    def test_an_out_of_domain_sentence_naming_real_paths_still_fails_closed(self):
        """The negative control for the rule above.

        Removing the paths must not become a way to smuggle an unknown request
        past the gate. The ask is still measured, and an ask the model does not
        represent is still refused.
        """
        real = "canonical/runtime/brain_unified_model_v1.py"
        routed = self.model.route(
            "launch a weather satellite into low earth orbit from " + real
        )
        self.assertFalse(routed["confident"])
        self.assertEqual(
            routed["reason"], "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED"
        )


class DeclaredDependencyTests(unittest.TestCase):
    """The compiler declares what the adapter will import or exec."""

    def _declare(self, adapter_source: str, source: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "canonical/runtime/bound_capabilities").mkdir(parents=True)
            (root / "canonical/runtime/bound_capabilities/ad.py").write_text(
                adapter_source, encoding="utf-8"
            )
            entry = {"adapter_module": "ad", "source": source}
            return compiler._dependency_declaration(entry, root)

    def test_the_module_an_adapter_runs_with_dash_m_is_declared(self):
        decl = self._declare(
            "import subprocess, sys\n"
            "def run(a, r):\n"
            "    return subprocess.run([sys.executable, '-m', 'crosshair', 'check'])\n",
            {"type": "pypi", "project": "crosshair-tool", "version": "0.0.109"},
        )
        self.assertIn("crosshair", decl["declared_dependencies_checked"])
        self.assertNotIn(
            "crosshair-tool",
            decl["declared_dependencies_checked"],
            "a distribution name is not an import name and must not be declared "
            "as one",
        )

    def test_the_program_an_adapter_execs_is_declared_as_an_executable(self):
        decl = self._declare(
            "import subprocess\n"
            "def run(a, r):\n"
            "    argv = ['pandoc', 'in.md', '-o', 'out.pdf']\n"
            "    return subprocess.run(argv, capture_output=True)\n",
            {"type": "apt", "packages": [{"name": "pandoc", "version": "3.1.3"}]},
        )
        self.assertIn("pandoc", decl["declared_dependencies_checked"])
        self.assertIn("pandoc", decl["declared_dependency_executables"])

    def test_a_program_name_that_is_not_a_literal_is_not_declared(self):
        """The negative control: only what the source states is declared.

        A first element computed at run time is not a fact about the tree, and
        ``[sys.executable, '-m', 'x']`` names no program at all.
        """
        decl = self._declare(
            "import subprocess, sys\n"
            "def run(a, r, exe):\n"
            "    return subprocess.run([exe, '--version'])\n",
            {"type": "apt", "packages": [{"name": "something", "version": "1"}]},
        )
        self.assertEqual(decl["declared_dependency_executables"], [])

    def test_the_declaration_does_not_depend_on_the_host(self):
        """Recompiling on a different machine must not change the artifact."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "canonical/runtime/bound_capabilities").mkdir(parents=True)
            (root / "canonical/runtime/bound_capabilities/ad.py").write_text(
                "import subprocess\n"
                "def run(a, r):\n"
                "    return subprocess.run(['definitely-not-installed-xyz'])\n",
                encoding="utf-8",
            )
            entry = {"adapter_module": "ad", "source": {"type": "apt", "packages": []}}
            first = compiler._dependency_declaration(entry, root)
            with mock.patch.object(shutil, "which", lambda _n: None):
                second = compiler._dependency_declaration(entry, root)
            with mock.patch.object(shutil, "which", lambda _n: "/usr/bin/true"):
                third = compiler._dependency_declaration(entry, root)
        self.assertEqual(first, second)
        self.assertEqual(first, third)
        self.assertIn("definitely-not-installed-xyz", first["declared_dependencies_checked"])


class UnrunnableCapabilityIsNotTheAnswerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()
        cls.cid = "python.contract.check.crosshair.v1"

    def test_a_capability_that_cannot_resolve_its_own_dependency_is_reported(self):
        row = self.model.capabilities[self.cid]
        missing = model_runtime._missing_declared_dependencies(row)
        # Host-independent, like the chromedriver claim it mirrors: the report
        # must agree with a live probe rather than assert one host's contents.
        self.assertEqual(
            "crosshair" in missing,
            not (_module_present("crosshair") or shutil.which("crosshair")),
            "the crosshair dependency is declared but the report disagrees with "
            "a live probe of this machine",
        )
        if _module_present("crosshair") or shutil.which("crosshair"):
            self.skipTest("crosshair is installed on this host")
        self.assertIn(self.cid, self.model.unrunnable_capabilities())

    def test_route_reports_an_unrunnable_capability_without_hiding_it(self):
        """`route()` answers what the model contains, which is not a host fact.

        The ranking must not move with what this machine has installed: this
        sandbox has pypdf and the CI runner does not, and the pinned route for
        "extract text from a pdf document" has to be the same on both. So the
        capability is reported, not removed.
        """
        if self.cid not in self.model.unrunnable_capabilities():
            self.skipTest("crosshair is installed on this host")
        goal = "python symbolic contract verification oracle counterexample crosshair"
        routed = self.model.route(goal)
        self.assertIn(self.cid, routed["unrunnable_on_this_host"])
        ids = [row["id"] for row in routed["candidates"]]
        self.assertIn(
            self.cid,
            ids,
            "the capability was hidden from the ranking, which makes routing "
            "depend on the host that answered",
        )

    def test_the_dependency_is_declared_so_that_any_host_can_report_it(self):
        """The real defect was that nothing declared it, not that nothing refused.

        A refusal placed in `solve()` was tried and rejected: five pinned
        DeclaredContextBindingTests drive pdf.extract.text.pypdf end to end and
        assert on the refusal *reason* and on `binding_provenance`, and a
        dependency refusal in front of the binder replaced
        CAPABILITY_INPUTS_MISSING with another string and short-circuited the
        provenance they read. What the artifact must carry is the declaration;
        `status()` and `unrunnable_capabilities()` already turn that into an
        answer about the machine that is asking.
        """
        row = self.model.capabilities[self.cid]
        declared = (row.get("declared_dependencies") or {}).get(
            "declared_dependencies_checked"
        )
        self.assertIn("crosshair", declared or [])
        # And the declaration is a fact about the tree, so it is the same on
        # every host even though the ANSWER about presence is not.
        status = self.model.status()
        self.assertEqual(
            status["declared_dependencies_present"]
            + status["declared_dependencies_missing"],
            len(self.model.capabilities),
        )

    def test_an_unrunnable_capability_is_still_addressable_by_its_own_id(self):
        """The negative control for the rule above.

        Excluding a capability from keyword selection must not make it
        unreachable: naming it is the caller taking responsibility for the
        choice, not a keyword match the model made on their behalf.
        """
        routed = self.model.route(self.cid)
        self.assertTrue(routed["confident"], routed["reason"])
        self.assertEqual(routed["best"]["id"], self.cid)

    def test_the_ranking_is_the_same_on_a_host_that_has_nothing_installed(self):
        """The regression this design decision exists to prevent.

        Filtering the ranking by presence made "extract text from a pdf
        document" stop routing to pdf.extract.text.pypdf on the CI runner,
        which does not have pypdf, while it kept routing here, which does. A
        routing assertion that holds in one sandbox and fails in another is not
        an assertion about the model. With every declared dependency on the
        machine reported missing -- 367 of 374 capabilities -- all four pinned
        routes must still be confident and still land where the model says.
        """
        cases = {
            "extract text from a pdf document": "pdf.extract.text.pypdf",
            "create a sqlite table from json records": (
                "sqlite.table.create_from_json_records"
            ),
            "rank sources by relevance to an objective": (
                "source.objective_relevance.rank.bm25"
            ),
            "audit python source structure and imports": "python.source.audit.ast",
        }
        with mock.patch.object(shutil, "which", lambda _name: None), mock.patch.object(
            importlib.util, "find_spec", lambda _name: None
        ):
            self.model._unrunnable = None
            try:
                self.assertGreater(len(self.model.unrunnable_capabilities()), 300)
                for goal, expected in cases.items():
                    with self.subTest(goal=goal):
                        routed = self.model.route(goal)
                        self.assertTrue(routed["confident"], routed["reason"])
                        self.assertEqual(routed["best"]["id"], expected)
            finally:
                self.model._unrunnable = None

    def test_every_capability_that_can_run_here_is_still_selectable(self):
        """The gate must not empty the model."""
        unrunnable = self.model.unrunnable_capabilities()
        self.assertLess(len(unrunnable), len(self.model.capabilities))
        for cid, missing in unrunnable.items():
            with self.subTest(cid=cid):
                self.assertTrue(missing)


if __name__ == "__main__":
    unittest.main()
