"""One file a sentence names must bind the two halves a capability declares.

The defect, measured on ``dac97dc``
-----------------------------------
"Extract the function helper from the python file <abs>/calc.py lines 6 to 7 into
a new function named helper_body and write the report to D/r.json" scored
``python.refactor.extract_function.v1`` at **33** -- highest of all 125
capabilities, 29 ahead of the next -- and was dropped as unbindable. The sentence
was then answered by ``document.convert.markdown_pdf.pandoc_weasyprint`` at score
**4**, which correctly refused a .py file with MARKDOWN_INPUT_REQUIRED and failed
the whole request closed.

The capability declares ``source_root`` (a directory) and ``module`` (a .py path
relative to it).  A sentence names ONE file.  Neither half can be bound alone, so
the owner was unreachable however well it matched -- and the failure named
``module:not_stated``, not the ``end_line`` the pinned binder reported first.

Three separate things had to be true before the sentence could work, and each was
measured:

1. The pair must be derived from the one stated path -- its directory is the
   root, its name is the module.  Nothing is invented; both come from the path
   the sentence gave.
2. The adapter's own verification law is "no tests => verified stays false
   loudly", and the registry template hardcodes ``run_tests`` to ``[]``, so the
   capability could never vouch for an edit it really had made.  The corpus is
   derived from the tree, through the module already shared with the eleven
   capabilities that refuse TEST_PATHS_REQUIRED.
3. That verification hardcoded ``python -m pytest``, which answered "No module
   named pytest" and rolled back a correct refactoring because its verifier could
   not start.  A derived corpus now runs through ``suite_argv``, which collects
   via unittest's loader and needs no third-party package.

These tests must be able to fail.  On ``dac97dc`` every test here fails except
the two that pin behaviour which must not change.
"""

import ast
import json
import pathlib
import shutil
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance  # noqa: E402

EXTRACT = "python.refactor.extract_function.v1"
REGISTRY = _ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

SOURCE = (
    "def add(a, b):\n"
    "    return a + b\n"
    "\n"
    "\n"
    "def helper(x):\n"
    "    a = x + 1\n"
    "    b = a * 2\n"
    "    return b\n"
)
TEST = (
    "import unittest, calc\n"
    "class T(unittest.TestCase):\n"
    "    def test_a(self):\n"
    "        self.assertEqual(calc.add(1, 2), 3)\n"
    "    def test_h(self):\n"
    "        self.assertEqual(calc.helper(1), 4)\n"
)


class _Tree(unittest.TestCase):
    """One tree per test, removed by addCleanup.

    The directory must not contain the word "test": path segments are BM25 query
    terms for the routing suites, so a scratch directory named test_something
    would leak into any ranking measured in the same process.
    """

    _NEXT = 0

    def setUp(self):
        import os

        type(self)._NEXT += 1
        self.base = (
            _ROOT / "canonical/astra_runtime/tmp"
            / ("extractfn_%d_%d" % (os.getpid(), type(self)._NEXT))
        )
        (self.base / "p" / "tests").mkdir(parents=True)
        (self.base / "p" / "calc.py").write_text(SOURCE)
        (self.base / "p" / "tests" / "test_calc.py").write_text(TEST)
        self.addCleanup(shutil.rmtree, self.base, True)
        self.src = self.base / "p"
        self.module = self.src / "calc.py"

    def sentence(self):
        return (
            "Extract the function helper from the python file %s lines 6 to 7 "
            "into a new function named helper_body and write the report to %s"
            % (self.module, self.base / "r.json")
        )

    def entry(self):
        return json.loads(REGISTRY.read_text())["capabilities"][EXTRACT]


class ThePairIsDerivedFromOneStatedFileTests(_Tree):
    def test_one_file_binds_both_halves(self):
        bound = front.bind_all_inputs(
            self.sentence(), self.entry(), _ROOT, cycle=0, spool=set()
        )
        self.assertEqual(bound["module"], "calc.py")
        self.assertTrue(
            str(bound["source_root"]).endswith("/p"),
            bound["source_root"],
        )

    def test_every_declared_input_binds(self):
        bound = front.bind_all_inputs(
            self.sentence(), self.entry(), _ROOT, cycle=0, spool=set()
        )
        self.assertEqual(bound["qualname"], "helper")
        self.assertEqual(bound["new_name"], "helper_body")
        self.assertEqual(int(bound["start_line"]), 6)
        self.assertEqual(int(bound["end_line"]), 7)

    def test_a_capability_that_declares_only_one_half_is_untouched(self):
        """The derivation is declaration-driven, never global."""
        entry = {
            "action_template": {"args": {"source_root": "${input.source_root}"}},
        }
        self.assertIsNone(front._module_pair_file(entry, [(
            str(self.module), self.module)]))

    def test_two_named_files_bind_nothing(self):
        """Exactly one file, or fail closed -- never pick one."""
        other = self.src / "other.py"
        other.write_text("y = 1\n")
        paths = [(str(self.module), self.module), (str(other), other)]
        self.assertIsNone(front._module_pair_file(self.entry(), paths))

    def test_a_named_directory_still_binds_the_directory(self):
        """A sentence that names a directory keeps the old answer."""
        entry = {"action_template": {"args": {"source_root": "${input.source_root}"}}}
        rel = str(self.src.relative_to(_ROOT))
        self.assertEqual(
            front.bind_typed_key(
                "audit the python source root %s" % rel, "source_root", _ROOT, entry
            ),
            rel,
        )


class TheVerificationRunsTheDiscoveredCorpusTests(_Tree):
    def test_the_derived_corpus_is_absolute_so_the_runner_can_find_it(self):
        """Repo-relative paths do not resolve from cwd=source_root."""
        from canonical.runtime.bound_capabilities import (
            python_test_corpus_discovery_v1 as discovery,
        )

        found = discovery.discover_test_files(self.src)
        self.assertTrue(found)
        for path in found:
            self.assertTrue(pathlib.Path(path).is_absolute(), path)

    def test_the_verifier_does_not_require_pytest_for_a_derived_corpus(self):
        source = (
            _ROOT / "canonical/runtime/bound_capabilities/python_refactor_extract_function.py"
        ).read_text(encoding="utf-8")
        self.assertIn("suite_argv", source)
        # The hardcoded pytest call may remain for a caller that names pytest
        # args, but it must not be the only way the derived corpus is run.
        self.assertIn("verify_argv", source)


class TheExtractionIsReinspectedTests(_Tree):
    def _produce(self):
        import importlib

        module = importlib.import_module(
            "canonical.runtime.bound_capabilities.python_refactor_extract_function"
        )
        rel = str(self.src.relative_to(_ROOT))
        args = {
            "source_root": rel,
            "module": "calc.py",
            "qualname": "helper",
            "new_name": "helper_body",
            "start_line": 6,
            "end_line": 7,
            "output_path": str((self.base / "r.json").relative_to(_ROOT)),
            "run_tests": [],
        }
        result = module.run(args, _ROOT)
        return args, result, self.base / "r.json"

    def test_a_genuine_extraction_is_accepted(self):
        args, result, _ = self._produce()
        ok, code, info = acceptance.INSPECTORS[EXTRACT](args, result, _ROOT)
        self.assertTrue(ok, code)
        self.assertEqual(info["owner_now_calls"], "helper_body")

    def test_an_extraction_that_never_happened_is_refused(self):
        args, result, report = self._produce()

        def rename(data):
            data["extracted_name"] = "never_created"

        data = json.loads(report.read_text())
        rename(data)
        report.write_text(json.dumps(data))
        ok, code, _ = acceptance.INSPECTORS[EXTRACT](args, result, _ROOT)
        self.assertFalse(ok)
        self.assertEqual(
            code, "EXTRACT_NEW_FUNCTION_IS_NOT_DEFINED_IN_THE_MODULE"
        )

    def test_a_copy_that_left_the_caller_untouched_is_refused(self):
        """An extraction the caller does not use is a copy, not an extraction."""
        args, result, _ = self._produce()
        text = self.module.read_text()
        self.module.write_text(text.replace("b = helper_body(x)", "b = a * 2"))
        ok, code, _ = acceptance.INSPECTORS[EXTRACT](args, result, _ROOT)
        self.assertFalse(ok)
        self.assertEqual(code, "EXTRACT_ORIGINAL_FUNCTION_DOES_NOT_CALL_THE_NEW_ONE")

    def test_a_claimed_signature_the_function_does_not_have_is_refused(self):
        args, result, report = self._produce()
        data = json.loads(report.read_text())
        data["inputs"] = ["x", "y", "z"]
        report.write_text(json.dumps(data))
        ok, code, _ = acceptance.INSPECTORS[EXTRACT](args, result, _ROOT)
        self.assertFalse(ok)
        self.assertEqual(code, "EXTRACT_INFERRED_INPUTS_ARE_NOT_THE_NEW_SIGNATURE")

    def test_a_module_left_unparseable_is_refused(self):
        args, result, _ = self._produce()
        self.module.write_text("def broken(:\n")
        ok, code, _ = acceptance.INSPECTORS[EXTRACT](args, result, _ROOT)
        self.assertFalse(ok)
        self.assertEqual(code, "EXTRACT_MODULE_DOES_NOT_PARSE_AFTER_THE_EDIT")

    def test_a_missing_report_is_refused(self):
        args, result, report = self._produce()
        report.unlink()
        ok, code, _ = acceptance.INSPECTORS[EXTRACT](args, result, _ROOT)
        self.assertFalse(ok)
        self.assertEqual(code, "EXTRACT_REPORT_ABSENT_FROM_DISK")

    def test_the_inspector_is_registered(self):
        self.assertIn(EXTRACT, acceptance.INSPECTORS)
        self.assertGreaterEqual(len(acceptance.INSPECTORS), 19)


class EndToEndTests(_Tree):
    def test_the_front_door_refactors_and_is_accepted(self):
        from canonical.runtime import live_brain_route_admission_v1 as adm

        out = adm.solve({"task_id": "extract_e2e", "goal": self.sentence()})
        rg = out.get("raw_goal_acceptance") or {}
        self.assertIs(rg.get("pass"), True, rg.get("reason"))
        self.assertEqual(
            out.get("status"),
            "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
        )
        self.assertTrue((self.base / "r.json").is_file())

    def test_the_source_is_actually_refactored(self):
        from canonical.runtime import live_brain_route_admission_v1 as adm

        adm.solve({"task_id": "extract_e2e2", "goal": self.sentence()})
        text = self.module.read_text()
        self.assertIn("def helper_body(x):", text)
        self.assertIn("helper_body(x)", text)
        self.assertIsNotNone(ast.parse(text))

    def test_the_pandoc_converter_is_not_selected(self):
        from canonical.runtime import live_integrated_brain_v1 as live

        _r, _a, compiled = live.compile_against_live_registry(
            self.sentence(), str(_ROOT)
        )
        self.assertEqual(compiled.get("selected_capability"), EXTRACT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
