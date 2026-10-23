#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH=ROOT/"runtime"/"astra_runtime.py"
spec=importlib.util.spec_from_file_location("project_brain_grounding_bound_integration",RUNTIME_PATH)
runtime=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=runtime
spec.loader.exec_module(runtime)

class PlainGoalGroundingBoundIntegrationTests(unittest.TestCase):
    def test_registry_producer_and_independent_verifier_are_callable(self):
        registry=json.loads(
            (ROOT/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
        )["capabilities"]
        producer="plain_goal.bound_capability.grounding.stdlib"
        verifier="plain_goal.bound_capability.grounding.verify.stdlib"
        self.assertEqual(registry[producer]["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(registry[verifier]["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(registry[producer]["verification"]["model_dependency_count"],0)
        self.assertEqual(registry[verifier]["verification"]["model_dependency_count"],0)

        goal="Audit the Python tests with unittest and report passed failed and skipped counts."
        rel="canonical/astra_runtime/tmp/BOUND_GROUNDING_REGISTRY_INTEGRATION.json"
        path=pathlib.Path.cwd()/rel
        path.unlink(missing_ok=True)
        self.addCleanup(lambda:path.unlink(missing_ok=True))

        produced=runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":producer,
                "goal":goal,
                "output_path":rel,
            },
        })
        self.assertTrue(produced["output_verified"],produced)
        self.assertEqual(produced["model_dependency_count"],0)
        # The clause must actually ground.  It used to report grounded_clause_count 0 with
        # unresolved_clause_indexes [0] while every one of the 20 ranked candidates was
        # rejected, 15 of them on output_path alone - a capability that writes a report was
        # refused because the sentence did not name where to write it, even though this very
        # call had declared an output area.  That is fixed and pinned here.
        report=json.loads(path.read_text(encoding="utf-8"))
        # A candidate IS now identified where previously all 20 ranked candidates were
        # rejected and none was named at all.  The clause is still not GROUNDED, and says so:
        # the surviving candidate's proposed bindings do not cover its declared inputs, so the
        # call cannot be made.  grounded_clause_count must be 0 for a clause the record itself
        # labels UNBOUND_INPUTS_NOT_GROUNDED - counting it as grounded because a candidate was
        # found is a success verdict for work that cannot be done, in both the producer and its
        # independent verifier, and both were doing it.
        self.assertEqual(report["clauses"][0]["status"],"UNBOUND_INPUTS_NOT_GROUNDED")
        self.assertEqual(report["grounded_clause_count"],0)
        self.assertEqual(report["unresolved_clause_indexes"],[0])
        self.assertTrue(produced["candidate_capability_ids"],
                        "grounding admitted no candidate at all")
        # The offered destination is recorded, so a grounded clause is distinguishable from
        # an invented one.
        self.assertEqual(report["declared_output_destination"],
                         "canonical/astra_runtime/tmp/BOUND_GROUNDING_REGISTRY_INTEGRATION_candidate_output.json")
        # And the fixed failure mode must not come back.  A candidate may still be refused on
        # output_path when the destination on offer is the WRONG TYPE for it - handing a docx
        # writer a .json path would be a guess - but never merely because no destination was
        # offered.  Measured, this goal went from 15 output_path refusals to 2, and both of
        # those 2 are docx creators whose semantic type is .docx.
        registry=json.loads(
            (ROOT/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8")
        )["capabilities"]
        NON_JSON_MARKERS=("docx","word","xlsx","spreadsheet","workbook","pdf","png","qr","barcode","image")
        rejected=report["clauses"][0].get("rejected_unbindable_candidates") or []
        for row in rejected:
            if "GOAL_INPUT_BINDING_REQUIRED:output_path" not in str(row.get("error")):
                continue
            entry=registry.get(str(row.get("capability_id"))) or {}
            blob=" ".join(str(x) for x in (entry.get("provides") or [])).lower()
            self.assertTrue(
                any(marker in blob for marker in NON_JSON_MARKERS),
                "a report writer was refused for want of a destination the caller supplied: %s"
                % row.get("capability_id"),
            )
        # python.tests.audit.unittest is deliberately NOT asserted here.  It needs `pattern`
        # and `source_root`, and this sentence states neither; inventing a glob to make it
        # bind would be a guess, and making every report writer bindable was measured to drop
        # expected_first_selected from 22 of 23 to 12 of 23.  The refusal is correct.

        verified=runtime._goal_action({
            "type":"invoke_capability",
            "args":{
                "capability_id":verifier,
                "goal":goal,
                "result_path":rel,
            },
        })
        self.assertTrue(verified["verified"],verified)
        self.assertTrue(verified["producer_independent"])
        self.assertEqual(verified["model_dependency_count"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
