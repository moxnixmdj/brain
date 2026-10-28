"""Registry metadata and architecture search do not prove project work occurred."""
from __future__ import annotations

import json
from pathlib import Path
import importlib
import shutil
import tempfile
import unittest

from canonical.runtime import astra_runtime, capability_proposal_generators, goal_compiler
from canonical.runtime import compile_brain_unified_model_v1 as model_compiler
from canonical.runtime.bound_capabilities import hardcore_software_engineering_orchestrator_v1 as kernel
from canonical.runtime.bound_capabilities import software_hardcore_swe_supercomposer_v1 as supercomposer
from canonical.runtime.bound_capabilities import software_patch_cegis_z3_v1 as cegis
from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as choreography
from canonical.runtime.bound_capabilities import software_repair_loop_cegis_hypothesis_v1 as repair_loop
from canonical.runtime.bound_capabilities import software_review_gate_composer_v1 as review
from canonical.runtime.bound_capabilities import grounded_executable_composition as composition

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
DIAGNOSTICS = (
    "software_hardcore_final_supercomposer_v1", "software_hardcore_closing_supercomposer_v1",
    "software_review_synthesis_supercomposer_v1", "software_test_contract_supercomposer_v1",
    "software_evidence_synthesis_supercomposer_v1", "python_provenance_coupling_supercomposer_v1",
    "python_patch_review_supercomposer_v1", "python_orchestration_symbol_supercomposer_v1",
    "python_fault_patch_supercomposer_v1", "python_evidence_contract_supercomposer_v1",
    "python_contract_issue_orchestration_fusion_v1", "python_fault_provenance_fusion_v1",
    "python_pipeline_allowlist_gate_v1", "python_pr_land_composer_v1",
    "python_refactor_test_scaffold_fusion_v1", "python_symbol_resolve_standalone_v1",
    "python_test_pipeline_verifier_v1",
)


class CompositionClaimControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="brain-composition-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        registry_copy = self.root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        registry_copy.parent.mkdir(parents=True)
        shutil.copyfile(REGISTRY, registry_copy)
        self.capabilities = json.loads(REGISTRY.read_text())["capabilities"]

    def test_no_project_operation_cannot_verify_swe_effects(self):
        cases = [
            (kernel, "software.hardcore.kernel.orchestrate.v1", {}),
            (cegis, "software.patch.synthesize.cegis.z3.v1", {}),
            (choreography, "software.repair.choreograph.crossfile.v1", {"source_root": "missing"}),
            (repair_loop, "software.repair.loop.cegis_hypothesis.v1", {"budget": 0}),
            (supercomposer, "software.hardcore.swe.supercomposer.v1", {}),
            (review, "software.review.gate.composer.v1", {}),
        ]
        for engine, capability, extra in cases:
            with self.subTest(capability=capability):
                result = engine.run({**extra, "output_path": "result.json"}, self.root)
                self.assertTrue(result["output_verified"])
                self.assertFalse(result["verified"])
                action = self.capabilities[capability]["action_template"]
                with self.assertRaisesRegex(astra_runtime.Blocker, "ACTION_EXPECTATION_FAILED"):
                    astra_runtime._verify_action_expectation(action, result)

    def test_remaining_registry_only_supercomposers_do_not_claim_project_work(self):
        for name in DIAGNOSTICS:
            with self.subTest(module=name):
                engine = importlib.import_module("canonical.runtime.bound_capabilities." + name)
                result = engine.run({"output_path": "result.json"}, self.root)
                self.assertTrue(result["output_verified"])
                self.assertFalse(result["verified"])
                self.assertFalse(json.loads((self.root / "result.json").read_text())["verified"])
                action = self.capabilities[engine.CAPABILITY_ID]["action_template"]
                with self.assertRaisesRegex(astra_runtime.Blocker, "ACTION_EXPECTATION_FAILED"):
                    astra_runtime._verify_action_expectation(action, result)

    def test_registry_diagnostics_are_not_executable_task_candidates(self):
        diagnostic = {cid: entry for cid, entry in self.capabilities.items()
                      if entry.get("diagnostic_only") is True}
        self.assertGreaterEqual(len(diagnostic), 20)
        for cid, entry in diagnostic.items():
            with self.subTest(capability=cid):
                self.assertEqual(goal_compiler._score(cid, cid, entry)[0], 0)
                self.assertFalse(capability_proposal_generators._zero_spend_verified(entry))
        providers = goal_compiler._effect_providers(self.capabilities)
        self.assertFalse([cid for cid, entry in providers.values() if entry.get("diagnostic_only") is True])
        rows = [model_compiler._capability_row(cid, entry, ROOT) for cid, entry in diagnostic.items()]
        grammar = model_compiler._build_grammar(rows, [])
        self.assertFalse(grammar["index"])
        self.assertTrue(all(not row["verification"]["independent_verification_evident"] for row in rows))
        cid, entry = next(iter(diagnostic.items()))
        grounding = {"schema": "PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1",
                     "input_contract_bindability_enforced": True,
                     "clauses": [{"index": 0, "status": "GROUNDED", "text": cid,
                                  "candidates": [{"capability_id": cid}]}]}
        with self.assertRaisesRegex(composition.CompositionError, "CANDIDATE_DIAGNOSTIC_ONLY"):
            composition.compose(cid, grounding, {cid: entry}, goal_compiler, ROOT)

    def test_changed_capabilities_do_not_inherit_independent_verification(self):
        ids = ["code.multilanguage.parse.tree_sitter.v1", "python.contract.check.crosshair.v1",
               "evidence.oracle.concrete_execution.v1", "evidence.oracle.hypothesis_property.v1",
               "python.software.repair.loop.test_guided.ast.v1", "python.review.diff_perf_gate.v1",
               "software.review.gate.composer.v1"]
        for cid in ids:
            with self.subTest(capability_id=cid):
                entry = self.capabilities[cid]
                self.assertIs(entry["verification"]["current_implementation_independently_verified"], False)
                row = model_compiler._capability_row(cid, entry, ROOT)
                self.assertFalse(row["verification"]["independent_verification_evident"])
                self.assertEqual(row["verification"]["evidence_scope"], "HISTORICAL_IMPLEMENTATION_ONLY")

    def test_remaining_composers_cannot_overwrite_source_or_registry(self):
        source = self.root / "program.py"
        source.write_text("def f(): return 1\n")
        registry = self.root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        for name in DIAGNOSTICS:
            engine = importlib.import_module("canonical.runtime.bound_capabilities." + name)
            for output in (source, registry):
                with self.subTest(module=name, output=output.name):
                    original = output.read_bytes()
                    with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
                        engine.run({"output_path": str(output.relative_to(self.root))}, self.root)
                    self.assertEqual(output.read_bytes(), original)

    def test_positive_budget_does_not_mistake_unbound_demo_for_repair(self):
        result = repair_loop.run({"budget": 1, "output_path": "result.json"}, self.root)
        self.assertFalse(result["verified"])
        self.assertEqual(result["iterations"], 0)
        self.assertFalse(list(self.root.rglob("tmp_loop_*.json")))

    def test_diagnostics_do_not_overwrite_a_python_source(self):
        source = self.root / "program.py"
        source.write_text("def f(): return 1\n")
        for engine in (kernel, cegis, choreography, repair_loop, supercomposer, review):
            with self.subTest(engine=engine.__name__):
                before = source.read_bytes()
                with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
                    engine.run({"budget": 0, "output_path": "program.py"}, self.root)
                self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
