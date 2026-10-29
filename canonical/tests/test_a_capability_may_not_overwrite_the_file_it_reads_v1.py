#!/usr/bin/env python3
"""A capability may not write its report over the file it was asked to read.

Measured on `main` e2d7981, 2026-10-29, before this rule existed:

  * "Fix the ZeroDivisionError in <repo>/app/utils.py." replaced 14 lines of
    source with a tree-sitter parse report (3/3, deterministic);
  * "Who last changed the function line_total in <repo>/app/service.py?" -- a
    READ-ONLY question -- replaced 358 lines of source with a JSON symbol index.

Both arrive the same way: every software-engineering row declares
`output_path: "${input.output_path}"` and `source_root: "${input.source_root}"`,
so a goal that names no destination leaves the binder exactly one stated path --
the source -- and the report is bound onto it.  Two different invocation
kernels were involved, which is why the rule is checked at both.

The oracle is the filesystem: the stated source must be byte-identical after the
request.  Nothing here asserts that a refusal is *correct* in the abstract; it
asserts that the file the user named still says what it said.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import write_authority_v1 as wa  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_write_authority_v1"

UTILS = '"""Helpers."""\n\n\ndef clamp(v, low, high):\n    return max(low, min(high, v))\n'
SERVICE = '"""Logic."""\n\n\ndef line_total(item):\n    return item.price_cents\n'


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "app").mkdir(parents=True)
    (base / "app/utils.py").write_text(UTILS, encoding="utf-8")
    (base / "app/service.py").write_text(SERVICE, encoding="utf-8")
    (base / "app/__init__.py").write_text("", encoding="utf-8")
    return base


def _rel(p: pathlib.Path) -> str:
    return str(p.relative_to(ROOT))


class TheRule(unittest.TestCase):
    def test_an_output_over_the_stated_source_is_refused(self):
        """The measured shape: source_root is a directory, output_path is a file
        inside it that the capability will parse."""
        base = _fresh("dir_root")
        args = {"source_root": _rel(base / "app"),
                "output_path": _rel(base / "app/service.py")}
        reason = wa.violation(ROOT, args, "python.source.symbols.index.ast")
        self.assertIsNotNone(reason)
        self.assertIn("OUTPUT_OVERWRITES_A_STATED_SOURCE", reason)
        self.assertIn("read_as=source_root", reason)

    def test_the_same_shape_with_an_equal_source_path_is_refused(self):
        base = _fresh("equal")
        args = {"source_path": _rel(base / "app/utils.py"),
                "output_path": _rel(base / "app/utils.py")}
        self.assertIsNotNone(wa.violation(ROOT, args, "code.multilanguage.parse.tree_sitter.v1"))

    def test_a_report_beside_the_source_is_allowed(self):
        """A NEW file cannot destroy anything, wherever it is written."""
        base = _fresh("report_beside")
        args = {"source_root": _rel(base / "app"),
                "output_path": _rel(base / "app/report.json")}
        self.assertIsNone(wa.violation(ROOT, args, "python.source.symbols.index.ast"))

    def test_a_report_outside_the_source_root_is_allowed(self):
        base = _fresh("report_outside")
        args = {"source_root": _rel(base / "app"),
                "output_path": _rel(base / "index.json")}
        self.assertIsNone(wa.violation(ROOT, args, "python.source.symbols.index.ast"))

    def test_no_destination_stated_is_not_the_rule(self):
        """With no output slot there is nothing for this rule to say.  The
        adapter's own default path applies, and that is a different defect."""
        base = _fresh("no_dest")
        self.assertIsNone(wa.violation(ROOT, {"source_root": _rel(base / "app")},
                                       "python.source.symbols.index.ast"))

    def test_a_source_transformer_may_replace_the_file_it_names(self):
        """python.refactor.rename_parameter.v1 exists to change the file it
        names; the rule reads that from the capability's own id."""
        base = _fresh("transformer")
        args = {"module": _rel(base / "app/utils.py"),
                "output_path": _rel(base / "app/utils.py")}
        self.assertIsNone(wa.violation(ROOT, args, "python.refactor.rename_parameter.v1"))
        self.assertIsNone(wa.violation(ROOT, args, "python.software.repair.loop.test_guided.ast.v1"))
        self.assertTrue(wa.is_source_transformer("python.patch.search.test_guided.ast.v1"))

    def test_a_non_source_file_is_not_protected_by_this_rule(self):
        base = _fresh("nonsource")
        (base / "app/data.json").write_text("{}\n", encoding="utf-8")
        args = {"source_root": _rel(base / "app"),
                "output_path": _rel(base / "app/data.json")}
        self.assertIsNone(wa.violation(ROOT, args, "python.source.symbols.index.ast"))

    def test_check_raises_and_carries_the_reason(self):
        base = _fresh("raises")
        args = {"source_root": _rel(base / "app"),
                "output_path": _rel(base / "app/utils.py")}
        with self.assertRaises(wa.WriteAuthorityViolation) as ctx:
            wa.check(ROOT, args, "python.source.audit.ast")
        self.assertIn("capability=python.source.audit.ast", str(ctx.exception))

    def test_a_mutation_that_drops_the_source_slots_lets_it_through(self):
        """Mutation control: the refusal is carried by the READ, not by the
        suffix.  With no source slot the same destination is permitted, so a
        test asserting only "source suffix is refused" would pass for the wrong
        reason."""
        base = _fresh("mutation")
        args = {"source_root": _rel(base / "app"),
                "output_path": _rel(base / "app/utils.py")}
        self.assertIsNotNone(wa.violation(ROOT, args, "python.source.audit.ast"))
        self.assertIsNone(wa.violation(ROOT, {"output_path": _rel(base / "app/utils.py")},
                                       "python.source.audit.ast"))


class TheDoorKeepsTheSource(unittest.TestCase):
    """End to end through the live front door, filesystem as the judge."""

    def _solve(self, case: str, goal: str) -> tuple[dict, pathlib.Path]:
        from canonical.runtime import live_brain_route_admission_v1 as door
        base = _fresh(case)
        return door.solve({"task_id": "WA_" + case, "goal": goal.format(b=_rel(base))}), base

    def test_a_repair_sentence_does_not_replace_the_source_with_a_report(self):
        result, base = self._solve("door_fix", "Fix the ZeroDivisionError in {b}/app/utils.py.")
        self.assertEqual((base / "app/utils.py").read_text(encoding="utf-8"), UTILS)
        self.assertIs(result.get("pass"), False)

    def test_a_read_only_question_does_not_replace_the_source_with_a_report(self):
        result, base = self._solve(
            "door_blame", "Who last changed the function line_total in {b}/app/service.py?")
        self.assertEqual((base / "app/service.py").read_text(encoding="utf-8"), SERVICE)
        self.assertIs(result.get("pass"), False)

    def test_an_index_request_that_states_its_report_still_passes(self):
        """The rule must not cost a working route."""
        result, base = self._solve(
            "door_ok", "Index the symbols in {b}/app and save the index to {b}/symbols.json.")
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertTrue((base / "symbols.json").is_file())
        self.assertEqual((base / "app/utils.py").read_text(encoding="utf-8"), UTILS)
        self.assertEqual((base / "app/service.py").read_text(encoding="utf-8"), SERVICE)


if __name__ == "__main__":
    unittest.main()
