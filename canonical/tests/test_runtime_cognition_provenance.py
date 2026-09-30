#!/usr/bin/env python3
import importlib.util
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical" / "runtime" / "astra_runtime.py"

spec = importlib.util.spec_from_file_location("astra_runtime_provenance_test", RUNTIME)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

def test_model_independent_result_is_runtime_stamped():
    result = runtime._stamp_cognition_provenance({
        "adapter": "goal",
        "returncode": 0,
        "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN",
        "planner_model_last": None,
    })
    assert result["model_dependency_count"] == 0
    assert result["cognition_dependency_class"] == "MODEL_INDEPENDENT"
    assert result["cognition_provenance_authority"] == "ASTRA_RUNTIME_DERIVED_V1"

def test_advisory_model_result_cannot_claim_zero_dependency():
    result = runtime._stamp_cognition_provenance({
        "adapter": "goal",
        "returncode": 0,
        "controller_mode": "OPTIONAL_MODEL_ADVISORY",
        "planner_model_last": "example-model",
        "model_dependency_count": 0,
    })
    assert result["model_dependency_count"] == 1
    assert result["cognition_dependency_class"] == "MODEL_ASSISTED"

def test_provenance_scan_fails_closed_on_excessive_nesting():
    value = {"controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN"}
    for _ in range(26):
        value = {"nested": value}
    with pytest.raises(runtime.Blocker, match="COGNITION_PROVENANCE_MAX_DEPTH_EXCEEDED"):
        runtime._collect_model_dependency_count(value)
