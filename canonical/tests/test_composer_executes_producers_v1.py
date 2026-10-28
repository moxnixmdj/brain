# PROJECT_BRAIN
"""A composer is verified by work its producers did, never by registry metadata.

Pinned defect (2026-10-28): nineteen composer/gate adapters answered
``verified: True`` with no inputs at all, after checking that producer ids
existed in BOUND_CAPABILITY_REGISTRY_V1.json.  They now share one executor.
"""
from __future__ import annotations

import importlib
import json
import shutil
import uuid
from pathlib import Path

import pytest

from canonical.runtime import composer_execution_v1 as ce

ROOT = Path(__file__).resolve().parents[2]
BC = "canonical.runtime.bound_capabilities."
COMPOSERS = [
    "software_test_contract_supercomposer_v1", "software_review_synthesis_supercomposer_v1",
    "software_hardcore_swe_supercomposer_v1", "software_hardcore_final_supercomposer_v1",
    "software_hardcore_closing_supercomposer_v1", "software_evidence_synthesis_supercomposer_v1",
    "python_test_pipeline_verifier_v1", "python_refactor_test_scaffold_fusion_v1",
    "python_pr_land_composer_v1", "python_patch_review_supercomposer_v1",
    "python_provenance_coupling_supercomposer_v1", "python_fault_provenance_fusion_v1",
    "python_fault_patch_supercomposer_v1", "python_evidence_contract_supercomposer_v1",
    "python_contract_issue_orchestration_fusion_v1", "python_orchestration_symbol_supercomposer_v1",
    "python_pipeline_allowlist_gate_v1", "test_slice_never_miss_v1", "software_review_gate_composer_v1",
    "python_symbol_resolve_standalone_v1", "software_repair_crossfile_choreograph_v1",
    "software_repair_loop_cegis_hypothesis_v1",
]
# Non-composer adapters that used to verify a built-in demo when given no inputs.
DEMO_DEFAULTERS = {
    "software_patch_cegis_z3_v1": "MANIFEST_REQUIRED",
    "hardcore_software_engineering_orchestrator_v1": "CEGIS_MANIFEST_REQUIRED",
    "software_synthesis_grid_induction_v1": "TRAINING_PAIRS_REQUIRED",
    "execution_pipeline_8stage_v1": "STAGES_REQUIRED",
    "evidence_oracle_concrete_v1": "SOURCE_REQUIRED",
}


@pytest.fixture
def scratch():
    rel = Path("canonical/astra_runtime/tmp") / ("composer-" + uuid.uuid4().hex[:10])
    (ROOT / rel).mkdir(parents=True)
    yield rel
    shutil.rmtree(ROOT / rel, ignore_errors=True)


@pytest.mark.parametrize("name", COMPOSERS)
def test_no_inputs_is_never_verified(name, scratch):
    mod = importlib.import_module(BC + name)
    out = (scratch / "c.json").as_posix()
    result = mod.run({"output_path": out}, ROOT)
    assert result["verified"] is False and result["output_verified"] is False
    # directly, or through a nested composer that refused for the same reason
    assert "COMPOSER_INPUT_UNBOUND:" in result["reason"], result["reason"]
    artifact = json.loads((ROOT / out).read_text())
    assert artifact["verified"] is False
    assert "found" not in artifact  # the old metadata ledger is gone
    assert artifact["steps_run"] == 1 and artifact["steps"][0]["verified"] is False


def test_every_composer_lists_only_registered_producers_and_its_registry_entry():
    reg = json.loads((ROOT / ce.REGISTRY_REL).read_text())["capabilities"]
    for name in COMPOSERS:
        mod = importlib.import_module(BC + name)
        assert mod.PRODUCERS, name
        assert all(p in reg for p in mod.PRODUCERS), (name, mod.PRODUCERS)
        assert reg[mod.CAPABILITY_ID]["adapter_module"] == name
        # Composers are internal composition nodes: their registry templates
        # carry no producer-input placeholders, so the plain-goal ranker does
        # not let their broad vocabulary steal a sentence (measured 2026-10-28:
        # with placeholders, test.slice.never_miss.v1 tied a translation goal
        # through world binding).  Inputs reach them from explicit callers.
        template_inputs = {
            v[8:-1] for v in reg[mod.CAPABILITY_ID]["action_template"]["args"].values()
            if isinstance(v, str) and v.startswith("${input.")} - {"output_path"}
        declared = set(ce.declared_inputs(ROOT, mod.PRODUCERS))
        assert declared, name  # they do need real inputs
        own = set(getattr(mod, "OWN_INPUTS", ()))  # e.g. the repair loop's budget
        assert template_inputs <= declared | own, (name, template_inputs - declared - own)


def test_real_inputs_run_the_producer_and_verify(scratch):
    fx = scratch / "fx"
    (ROOT / fx / "pkg").mkdir(parents=True)
    (ROOT / fx / "pkg" / "__init__.py").write_text("")
    (ROOT / fx / "pkg" / "core.py").write_text("def add(a, b):\n    return a + b\n")
    (ROOT / fx / "tests").mkdir()
    (ROOT / fx / "tests" / "test_core.py").write_text(
        "from pkg.core import add\ndef test_add():\n    assert add(1, 2) == 3\n")
    mod = importlib.import_module(BC + "test_slice_never_miss_v1")
    out = (scratch / "slice.json").as_posix()
    result = mod.run({"source_root": fx.as_posix(), "changed_paths": [(fx / "pkg/core.py").as_posix()],
                      "output_path": out}, ROOT)
    artifact = json.loads((ROOT / out).read_text())
    step = artifact["steps"][0]
    assert step["status"] == "VERIFIED" and step["verified"] is True, step
    assert (ROOT / step["output_path"]).is_file()
    step_artifact = json.loads((ROOT / step["output_path"]).read_text())
    assert "tests/test_core.py" in json.dumps(step_artifact)
    assert result["verified"] is True and result["steps_run"] == 1


def test_a_failing_producer_fails_the_composition(scratch):
    fx = scratch / "fx"
    (ROOT / fx).mkdir(parents=True)
    (ROOT / fx / "mod.py").write_text("x = 1\n")
    mod = importlib.import_module(BC + "test_slice_never_miss_v1")
    out = (scratch / "slice.json").as_posix()
    result = mod.run({"source_root": fx.as_posix(), "changed_paths": ["does_not_exist.py"],
                      "output_path": out}, ROOT)
    assert result["verified"] is False
    assert result["reason"] not in ("", "VERIFIED")
    artifact = json.loads((ROOT / out).read_text())
    assert artifact["steps"][0]["verified"] is False


def test_cycle_is_refused(scratch):
    out = (scratch / "cycle.json").as_posix()
    ce._ACTIVE.append("test.slice.never_miss.v1")
    try:
        mod = importlib.import_module(BC + "test_slice_never_miss_v1")
        result = mod.run({"source_root": "canonical", "changed_paths": ["x.py"], "output_path": out}, ROOT)
    finally:
        ce._ACTIVE.remove("test.slice.never_miss.v1")
    assert result["verified"] is False and result["reason"].startswith("COMPOSER_CYCLE:")
    assert result["steps_run"] == 0


def test_output_outside_repository_is_refused():
    mod = importlib.import_module(BC + "test_slice_never_miss_v1")
    with pytest.raises(RuntimeError, match="PATH_OUTSIDE_REPOSITORY"):
        mod.run({"output_path": "../escape.json"}, ROOT)


@pytest.mark.parametrize("name,reason", sorted(DEMO_DEFAULTERS.items()))
def test_no_inputs_means_no_demo_verdict(name, reason, scratch):
    mod = importlib.import_module(BC + name)
    out = (scratch / "d.json").as_posix()
    result = mod.run({"output_path": out}, ROOT)
    assert result["verified"] is False and result["output_verified"] is False, result
    assert reason in (str(result.get("reason")) + str(result.get("status"))), result
    assert json.loads((ROOT / out).read_text())["verified"] is False


def test_tree_sitter_index_refuses_without_a_source_root(scratch):
    mod = importlib.import_module(BC + "code_multilanguage_tree_sitter_v1")
    with pytest.raises(RuntimeError, match="SOURCE_ROOT_REQUIRED"):
        mod.run({"output_path": (scratch / "ts.json").as_posix()}, ROOT)


def test_repair_loop_runs_the_oracles_on_the_callers_source(scratch):
    src = scratch / "fx"
    (ROOT / src).mkdir(parents=True)
    (ROOT / src / "m.py").write_text('def f(x):\n    """post: _ == x + 1"""\n    return abs(x)\n')
    (ROOT / src / "edits.json").write_text(json.dumps({"edits": []}))
    (ROOT / scratch / "manifest.json").write_text(json.dumps({
        "components": [{"id": "k", "kind": "MECHANISM", "requires": [], "provides": ["e"],
                        "verified": True, "brain_owned": True, "donor_independent": True,
                        "cost": {"wall_clock": 0.1, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}}],
        "counterexamples": [], "initial_facts": [],
        "target": {"required_effects": ["e"], "forbidden_effects": [], "max_components": 2, "top_k": 1},
        "allow_candidate_components": False}))
    mod = importlib.import_module(BC + "software_repair_loop_cegis_hypothesis_v1")
    out = (scratch / "loop.json").as_posix()
    result = mod.run({"budget": 2, "manifest": (scratch / "manifest.json").as_posix(),
                      "source_path": (src / "m.py").as_posix(), "source": None, "source_root": src.as_posix(),
                      "edits_path": (src / "edits.json").as_posix(), "changed_paths": [(src / "m.py").as_posix()],
                      "output_path": out}, ROOT)
    artifact = json.loads((ROOT / out).read_text())
    assert result["iterations"] == 1
    by = {s["producer"]: s for s in artifact["steps"]}
    assert by["software.patch.synthesize.cegis.z3.v1"]["verified"] is True
    # the property oracle ran on the caller's source and found the real violation (x = 0)
    hyp = by["evidence.oracle.hypothesis_property.v1"]
    assert hyp["status"] == "VERIFIED", hyp
    hyp_artifact = json.loads((ROOT / hyp["output_path"]).read_text())
    assert hyp_artifact["status"] == "CONTRACT_VIOLATION_FOUND", hyp_artifact.get("status")
    assert result["verified"] in (True, False)  # the verdict is whatever the ledger says, never a default


def test_repair_loop_zero_budget_runs_nothing(scratch):
    mod = importlib.import_module(BC + "software_repair_loop_cegis_hypothesis_v1")
    out = (scratch / "loop0.json").as_posix()
    result = mod.run({"budget": 0, "manifest": {}, "output_path": out}, ROOT)
    assert result["iterations"] == 0 and result["verified"] is False
    assert result["reason"] == "REPAIR_BUDGET_ZERO"


def test_deadline_is_an_end_to_end_budget(scratch):
    mod = importlib.import_module(BC + "test_slice_never_miss_v1")
    out = (scratch / "deadline.json").as_posix()
    result = mod.run({"source_root": "canonical", "changed_paths": ["x.py"], "deadline_s": 0,
                      "output_path": out}, ROOT)
    assert result["verified"] is False and result["steps_run"] == 1
    assert result["reason"].startswith("COMPOSER_DEADLINE_EXCEEDED:")
    assert json.loads((ROOT / out).read_text())["deadline_s"] == 0


def test_unbound_timeout_inherits_the_remaining_budget(tmp_path):
    bound, unbound = ce._bind("p", {"timeout_s": "${input.timeout_s}", "x": "${input.x}"},
                              {"x": 1}, "o.json", remaining_s=7.9)
    assert unbound == [] and bound == {"timeout_s": 7, "x": 1, "output_path": "o.json"}
    bound, unbound = ce._bind("p", {"timeout_s": "${input.timeout_s}"}, {}, "o.json", remaining_s=None)
    assert unbound == ["timeout_s"]
