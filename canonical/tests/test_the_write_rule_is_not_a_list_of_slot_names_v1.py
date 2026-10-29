#!/usr/bin/env python3
"""The write-authority rule must not depend on a list of slot names it can enumerate.

Measured on `main` 88bb18bb, 2026-10-29, one day after the write-authority rule
merged: the rule read "what is this capability being asked to read" from a fixed
tuple of eighteen slot names.  ``code.impact.tree_sitter.testselect.v1`` states
the files it analyses in ``changed_paths``, which the tuple does not name, so the
rule ran (one invocation, verified) and returned None.  The adapter then wrote a
1076-byte JSON impact report over a 272-byte Python module:

    "Generate the tests for app/models.py in <repo>."
      -> FAIL__LIVE_CONTROLLER_EXECUTION
      -> app/models.py is now a tree-sitter impact report

The same sentence destroyed a source file in three separate requests (scaffold,
regression_test, reproduce) -- deterministic, 3/3.

Across all 125 registry rows there are 122 argument names the tuple cannot name
in advance (``diff_path`` x9, ``anchor_path`` x4, ``index_path`` x3,
``worktree_path`` x4, ``json_path`` x11, ...).  A rule that enumerates the names
it defends is a rule that always loses the race, so the fix is not a longer list:
it is the observation that the role of an argument is decided by whether it is
WRITTEN, not by what it is called.  Every argument that is not a destination is
an input.  That is strictly fewer conditions than the tuple it replaces.

Two things are asserted here, in this order:

  1. the slot-name race is closed -- an argument the rule has never heard of
     still protects the file it names, and a legitimate transformer still writes;
  2. the refusal is TYPED.  Measured: the caller was told
     FAIL__LIVE_CONTROLLER_EXECUTION ("execution or verification failure") about
     a deliberate refusal, which blames the controller and invites a retry of the
     action that was just refused.

The oracle is the filesystem and the returned status, never this module's own
opinion of itself.
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

WORK = ROOT / "canonical/astra_runtime/tmp/test_write_authority_slot_race_v1"

MODELS = '"""Models."""\n\n\nclass Item:\n    def __init__(self, price_cents):\n        self.price_cents = price_cents\n'
UTILS = '"""Helpers."""\n\n\ndef pct(v, whole):\n    return v / whole\n'


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "app").mkdir(parents=True)
    (base / "app/models.py").write_text(MODELS, encoding="utf-8")
    (base / "app/utils.py").write_text(UTILS, encoding="utf-8")
    (base / "app/__init__.py").write_text("", encoding="utf-8")
    return base


def _rel(p: pathlib.Path) -> str:
    return str(p.relative_to(ROOT))


class TheSlotNameIsNotTheRule(unittest.TestCase):
    def test_a_slot_the_rule_never_heard_of_still_protects_its_file(self):
        """The measured shape: changed_paths, which is not in any slot list."""
        base = _fresh("changed_paths")
        target = _rel(base / "app/models.py")
        reason = wa.violation(
            ROOT,
            {"capability_id": "code.impact.tree_sitter.testselect.v1",
             "output_path": target, "changed_paths": [target]},
            "code.impact.tree_sitter.testselect.v1")
        self.assertIsNotNone(reason, "a report was bound over the file it analyses")
        self.assertIn("OUTPUT_OVERWRITES_A_STATED_SOURCE", reason)
        self.assertIn("read_as=changed_paths", reason)

    def test_every_unlisted_argument_shape_is_read_as_an_input(self):
        """One case per spelling the registry actually uses, none of which the
        previous tuple named.  A list is a list of inputs, not one path."""
        base = _fresh("spellings")
        target = _rel(base / "app/utils.py")
        for slot in ("changed_paths", "diff_path", "anchor_path", "index_path",
                     "worktree_path", "json_path", "analyze_paths"):
            args = {"output_path": target, slot: [target]}
            reason = wa.violation(ROOT, args, "python.source.symbols.index.ast")
            self.assertIsNotNone(reason, f"{slot} did not protect the file it names")
            self.assertIn(f"read_as={slot}", reason)

    def test_a_destination_slot_is_never_read_as_an_input(self):
        """The complement of the rule: the value being written cannot also be
        the reason it may not be written, or nothing could ever be written."""
        base = _fresh("dest_not_input")
        target = _rel(base / "app/utils.py")
        self.assertIsNone(wa.violation(ROOT, {"output_path": target},
                                       "python.source.symbols.index.ast"))

    def test_a_source_transformer_still_replaces_the_file_it_names(self):
        """The rule must not cost the capabilities that exist to change code."""
        base = _fresh("transformer")
        target = _rel(base / "app/utils.py")
        args = {"module": target, "output_path": target, "changed_paths": [target]}
        for cap in ("python.refactor.rename_parameter.v1",
                    "python.refactor.rename_symbol.v1",
                    "python.refactor.extract_function.v1",
                    "python.software.repair.loop.test_guided.ast.v1"):
            self.assertIsNone(wa.violation(ROOT, args, cap), cap)

    def test_a_new_report_beside_the_source_is_still_allowed(self):
        base = _fresh("new_report")
        args = {"changed_paths": [_rel(base / "app/models.py")],
                "output_path": _rel(base / "app/impact.json")}
        self.assertIsNone(wa.violation(ROOT, args, "code.impact.tree_sitter.testselect.v1"))

    def test_the_rule_is_not_merely_the_suffix_check(self):
        """Mutation control.  With no input argument at all the same destination
        is permitted, so a test asserting only 'a source suffix is refused' would
        pass for the wrong reason."""
        base = _fresh("mutation")
        target = _rel(base / "app/utils.py")
        self.assertIsNotNone(wa.violation(ROOT, {"output_path": target,
                                                 "changed_paths": [target]},
                                          "python.source.audit.ast"))
        self.assertIsNone(wa.violation(ROOT, {"output_path": target},
                                       "python.source.audit.ast"))


class TheDoorSaysWhatHappened(unittest.TestCase):
    """End to end.  The filesystem is the judge of the file; the status is the
    judge of the report."""

    def _solve(self, case: str, goal: str):
        from canonical.runtime import live_brain_route_admission_v1 as door
        base = _fresh(case)
        return door.solve({"task_id": "WAS_" + case,
                           "goal": goal.format(b=_rel(base))}), base

    def test_the_module_survives_the_test_generation_request(self):
        result, base = self._solve(
            "door_scaffold", "Generate the tests for {b}/app/models.py.")
        self.assertEqual((base / "app/models.py").read_text(encoding="utf-8"), MODELS,
                         "the module the request named was replaced by a report")
        self.assertIs(result.get("pass"), False)

    def test_a_refusal_is_reported_as_a_refusal_not_as_a_controller_fault(self):
        result, base = self._solve(
            "door_typed", "Generate the tests for {b}/app/models.py.")
        status = str(result.get("status") or "")
        if "WRITE_AUTHORITY" in status:
            self.assertEqual(status, "FAIL_CLOSED__WRITE_AUTHORITY_REFUSED")
            self.assertEqual(result.get("failure_class"),
                             "AN_ACTION_WOULD_OVERWRITE_A_FILE_IT_READS")
        else:
            # The binder may legitimately route this sentence elsewhere; what it
            # may never do is claim a controller fault for a deliberate refusal.
            self.assertNotIn("OUTPUT_OVERWRITES_A_STATED_SOURCE", str(result.get("reason") or ""))

    def test_a_route_that_states_its_report_still_passes(self):
        """The rule must not cost a working route."""
        result, base = self._solve(
            "door_ok", "Index the symbols in {b}/app and save the index to {b}/symbols.json.")
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertTrue((base / "symbols.json").is_file())
        self.assertEqual((base / "app/models.py").read_text(encoding="utf-8"), MODELS)
        self.assertEqual((base / "app/utils.py").read_text(encoding="utf-8"), UTILS)


if __name__ == "__main__":
    unittest.main()
