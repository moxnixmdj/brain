"""An executable binding may not silently omit another stated input file.

These are current-tree routing regressions, not capability promotion evidence.
The public registry's pending-promotion gate remains unchanged.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import goal_compiler as gc
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import live_integrated_brain_v1 as live

ROOT = Path(__file__).resolve().parents[2]
INDEX = "python.source.symbols.index.ast"
INVOKER = "brain.module.function.invoke"
MODULE = "canonical/runtime/bounded_claim_support.py"


class StatedInputCoverageTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "canonical/astra_runtime/tmp"
        parent.mkdir(parents=True, exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(prefix="input_coverage_", dir=parent)
        self.addCleanup(self.scratch.cleanup)
        self.directory = Path(self.scratch.name)
        self.payload = self.directory / "payload.json"
        self.payload.write_text(json.dumps({"claim_text": "Orion budget is 40.",
                                            "evidence_text": "Orion budget is 40."}))
        self.output = self.directory / "result.json"
        self.registry = gc._platform_admissible_registry(live.load_verified_registry())

    def rel(self, path):
        return Path(path).relative_to(ROOT).as_posix()

    def sentence(self, payload=None):
        return (f"Call the function classify_support in {MODULE} with the payload "
                f"{self.rel(payload or self.payload)} and save the result to {self.rel(self.output)}")

    def test_complete_typed_invocation_displaces_only_the_incomplete_binding(self):
        result = front.compile_goal(self.sentence(), self.registry, ROOT)
        self.assertEqual(result["selected_capability"], INVOKER)
        self.assertEqual(result["inputs"]["json_path"], self.rel(self.payload))
        self.assertEqual(result["match_evidence"]["displaced_pinned_selection"], INDEX)
        self.assertEqual(result["match_evidence"]["displaced_unserved_files"], [self.rel(self.payload)])
        self.assertFalse(self.output.exists(), "selection must not execute the callable")

    def test_selected_contract_runs_the_existing_adapter_with_a_direct_call_oracle(self):
        from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as invoker
        from canonical.runtime.bounded_claim_support import classify_support

        compiled = front.compile_goal(self.sentence(), self.registry, ROOT)
        result = invoker.run(compiled["inputs"], ROOT)
        self.assertEqual(result["status"], "MODULE_FUNCTION_INVOKED")
        record = json.loads(self.output.read_text())
        payload = json.loads(self.payload.read_text())
        self.assertEqual(record["result"], classify_support(**payload))
        self.assertEqual(record["result"]["relation"], "SUPPORTS")
        self.assertEqual(record["tier"], "TEST_EVIDENCED")

    def test_bound_repository_scope_owns_its_relative_test_file(self):
        repo = self.directory / "repo"
        (repo / "tests").mkdir(parents=True)
        test = repo / "tests/test_math.py"
        test.write_text("def test_ok():\n    assert 1 == 1\n")
        goal = (f"Find the commit in {self.rel(repo)} that broke tests/test_math.py "
                f"and write its commit id to {self.rel(self.output)}")
        self.assertEqual(front._unserved_stated_file_paths(
            goal, {"source_root": self.rel(repo), "output_path": self.rel(self.output)}, ROOT), [])

    def test_file_outside_the_bound_directory_is_not_owned(self):
        scope = self.directory / "scope"
        scope.mkdir()
        outside = self.rel(scope) + "/../payload.json"
        goal = f"Read {outside} in {self.rel(scope)} and save to {self.rel(self.output)}"
        self.assertEqual(front._unserved_stated_file_paths(
            goal, {"source_root": self.rel(scope), "output_path": self.rel(self.output)}, ROOT), [outside])

    def test_no_complete_candidate_refuses_instead_of_running_the_indexer(self):
        with self.assertRaises(gc.GoalCompilationFailure) as raised:
            front.compile_goal(self.sentence(), {INDEX: self.registry[INDEX]}, ROOT)
        self.assertEqual(raised.exception.code, "GOAL_INPUT_BINDING_REQUIRED")
        self.assertIn(self.rel(self.payload), raised.exception.detail)
        self.assertFalse(self.output.exists())

    def test_nonexistent_input_cannot_be_silently_dropped_either(self):
        missing = self.directory / "absent.json"
        with self.assertRaises(gc.GoalCompilationFailure) as raised:
            front.compile_goal(self.sentence(missing), self.registry, ROOT)
        self.assertIn(self.rel(missing), raised.exception.detail)
        self.assertFalse(self.output.exists())

    def test_complete_specific_source_analysis_keeps_its_route(self):
        goal = f"Index the functions in the python source {MODULE} and save the result to {self.rel(self.output)}"
        result = front.compile_goal(goal, {INDEX: self.registry[INDEX]}, ROOT)
        self.assertEqual(result["selected_capability"], INDEX)
        self.assertEqual(result["inputs"]["source_root"], MODULE)
        self.assertNotIn("F17_RETRIEVAL_FIRST_TYPED_ADMISSION", result["front_compiler"]["rules_applied"])

    def test_selection_uses_contracts_not_the_invoker_id(self):
        alternate = "typed.payload.execute.alternative"
        entry = copy.deepcopy(self.registry[INVOKER])
        entry["capability_id"] = alternate
        entry["action_template"]["args"]["capability_id"] = alternate
        entry["declared_action_template"]["args"]["capability_id"] = alternate
        registry = {INDEX: self.registry[INDEX], alternate: entry}
        result = front.compile_goal(self.sentence(), registry, ROOT)
        self.assertEqual(result["selected_capability"], alternate)
        self.assertEqual(result["inputs"]["function"], "classify_support")
        self.assertFalse(self.output.exists())

    def test_ambiguous_complete_contracts_do_not_rescue_an_incomplete_winner(self):
        registry = {INDEX: self.registry[INDEX]}
        for cid in ("typed.payload.execute.alpha", "typed.payload.execute.beta"):
            entry = copy.deepcopy(self.registry[INVOKER])
            entry["capability_id"] = cid
            entry["action_template"]["args"]["capability_id"] = cid
            entry["declared_action_template"]["args"]["capability_id"] = cid
            registry[cid] = entry
        with self.assertRaises(gc.GoalCompilationFailure):
            front.compile_goal(self.sentence(), registry, ROOT)
        self.assertFalse(self.output.exists())

    def test_absolute_and_relative_bindings_cover_the_same_file(self):
        inputs = {"source_path": str(ROOT / MODULE), "json_path": str(self.payload),
                  "output_path": str(self.output)}
        self.assertEqual(front._unserved_stated_file_paths(self.sentence(), inputs, ROOT), [])

    def test_list_and_whole_goal_arguments_retain_their_file_evidence(self):
        paths = [MODULE, self.rel(self.payload), self.rel(self.output)]
        self.assertEqual(front._unserved_stated_file_paths(self.sentence(), {"argv": paths}, ROOT), [])
        self.assertEqual(front._unserved_stated_file_paths(self.sentence(), {"goal": self.sentence()}, ROOT), [])

    def test_directory_context_and_urls_are_not_additional_input_files(self):
        goal = (f"Index {MODULE} under canonical/runtime using https://example.org/context.json "
                f"and save the result to {self.rel(self.output)}")
        self.assertEqual(front._unserved_stated_file_paths(
            goal, {"source_root": MODULE, "output_path": self.rel(self.output)}, ROOT), [])


if __name__ == "__main__":
    unittest.main()
