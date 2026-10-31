"""A lexical match cannot override a typed input-binding refusal."""
from pathlib import Path

import pytest

from canonical.runtime import capability_selection_retrieval_v1 as selection
from canonical.runtime import goal_compiler
from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def registry():
    return goal_compiler._platform_admissible_registry(dict(load_verified_registry()))


@pytest.mark.parametrize("cid,goal", [
    ("python.source.symbols.index.ast", "Index python source symbols from directory nowhere and save to report.json."),
    ("python.repo.diff_apply_full_testgate.v1", "Apply the diff to the repository and run full tests save the output to report.json."),
    ("python.software.issue_to_pr.orchestrate.v1", "Orchestrate issue to PR for the repository and save to report.json."),
    ("archive.tar_gz.create_from_manifest", "Create a tar.gz archive from the manifest and save it to output.tar.gz."),
])
def test_unbound_contract_cannot_be_admitted(registry, cid, goal):
    typed = selection.admit(goal, cid, registry[cid], ROOT)
    assert typed["admitted"] is False
    assert typed["reason"].startswith("BINDING_REFUSED:")
    result = admission.route_admission(goal, {"selected_capability": cid}, registry)
    assert result["admitted"] is False
    assert result["typed_binding_refused"] is True
    assert result["typed_binding_reason"] == typed["reason"]
    assert result["rule"] == "R15_TYPED_INPUT_BINDING_REFUSED"


@pytest.mark.parametrize("cid,goal", [
    ("python.source.symbols.index.ast", "Index python source symbols from directory canonical/runtime and save to canonical/tmp_symbols_report.json."),
    ("archive.tar_gz.create_from_manifest", "Create a tar.gz archive from the manifest canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json and save it to canonical/tmp_b9.tar.gz."),
])
def test_fully_bound_contract_still_admitted(registry, cid, goal):
    # Routing only: the archive input is used to test binding, not archive execution.
    typed = selection.admit(goal, cid, registry[cid], ROOT)
    assert typed["admitted"] is True
    result = admission.route_admission(goal, {"selected_capability": cid}, registry)
    assert result["admitted"] is True
    assert result["admission_basis"] == "DECLARED_INPUT_CONTRACT_FULLY_STATED_IN_GOAL"
