"""Finding names in a registry is not executing or validating a test pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.bound_capabilities import python_test_pipeline_verifier_v1 as pipeline
from canonical.runtime.bound_capabilities import test_slice_never_miss_v1 as slice_cap


def _registry(root: Path, capabilities: dict) -> None:
    path = root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"capabilities": capabilities}))


@pytest.mark.parametrize("selector_registered", [False, True])
def test_an_unrun_selector_cannot_verify_a_never_miss_slice(tmp_path, selector_registered):
    capabilities = {"python.source.change_impact.testselect.v1": {}} if selector_registered else {}
    _registry(tmp_path, capabilities)
    result = slice_cap.run({"output_path": "slice.json"}, tmp_path)
    artifact = json.loads((tmp_path / "slice.json").read_text())
    assert artifact["change_impact_exists"] is selector_registered
    assert artifact["never_miss"] is False
    assert artifact["speedup"] is None
    assert artifact["verified"] is False
    assert result["verified"] is False
    assert result["output_verified"] is False


def test_matching_registry_names_cannot_verify_an_unrun_pipeline(tmp_path):
    producers = [
        "test.slice.never_miss.v1", "python.source.change_impact.testselect.v1",
        "execution.pipeline.8stage.v1", "python.repository.acceptance.measure.v1",
        "python.tests.audit.unittest",
    ]
    capabilities = {name: {"provides": []} for name in producers}
    capabilities[producers[0]]["provides"] = list(pipeline.REQUIRES)
    _registry(tmp_path, capabilities)
    result = pipeline.run({"output_path": "pipeline.json"}, tmp_path)
    artifact = json.loads((tmp_path / "pipeline.json").read_text())
    assert all(artifact["found"].values()) and all(artifact["producers"].values())
    assert artifact["verified"] is False
    assert result["verified"] is False
    assert result["output_verified"] is False
