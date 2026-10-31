"""Registry declarations do not prove engineering workflows executed."""
import ast
import hashlib
import importlib
import json
from pathlib import Path

import pytest

MODULES = [
    "python_contract_issue_orchestration_fusion_v1",
    "python_evidence_contract_supercomposer_v1",
    "python_fault_patch_supercomposer_v1",
    "python_orchestration_symbol_supercomposer_v1",
    "python_patch_review_supercomposer_v1",
    "python_pr_land_composer_v1",
    "python_provenance_coupling_supercomposer_v1",
    "python_refactor_test_scaffold_fusion_v1",
    "software_evidence_synthesis_supercomposer_v1",
    "software_hardcore_closing_supercomposer_v1",
    "software_hardcore_final_supercomposer_v1",
    "software_hardcore_swe_supercomposer_v1",
    "software_review_synthesis_supercomposer_v1",
    "software_test_contract_supercomposer_v1",
]


@pytest.mark.parametrize("name", MODULES)
@pytest.mark.parametrize("all_present", [False, True], ids=["empty", "all-declarations-present"])
def test_registry_presence_is_not_a_verified_workflow(tmp_path, name, all_present):
    mod = importlib.import_module("canonical.runtime.bound_capabilities." + name)
    registry = {"capabilities": {}}
    if all_present:
        # Construct a maximally favorable registry without executing any producer.
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        assignment = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "producers" for t in node.targets))
        for producer in ast.literal_eval(assignment.value):
            registry["capabilities"][producer] = {"provides": []}
        registry["capabilities"]["fixture.effects"] = {"provides": mod.REQUIRES}
        audit = tmp_path / "canonical/runtime/bound_capabilities/python_source_audit.py"
        audit.parent.mkdir(parents=True)
        audit.write_text("# presence is not execution\n", encoding="utf-8")
    path = tmp_path / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry), encoding="utf-8")
    result = mod.run({"output_path": "out/result.json"}, tmp_path)
    raw = (tmp_path / result["output_path"]).read_bytes()
    artifact = json.loads(raw)
    assert result["output_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["verified"] is False
    assert result["output_verified"] is False
    assert artifact["verified"] is False
    assert result["reason"] == artifact["reason"] == "DEPENDENCIES_NOT_EXECUTED"
    assert artifact["registry_ready"] is all_present
