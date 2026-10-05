from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.root3_effect_channel_registry_v1 import (
    RegistryError,
    compile_registry,
    git_blob_sha,
)


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8")


def _fixture(tmp_path: Path, *, nonliteral=False):
    astra=tmp_path/"canonical/runtime/astra_runtime.py"
    reg=tmp_path/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    fixed=tmp_path/"canonical/runtime/fixed.py"
    helper=tmp_path/"canonical/runtime/helper.py"
    adapter=tmp_path/"canonical/runtime/bound_capabilities/demo.py"
    call="_load_runtime_helper(name)" if nonliteral else "_load_runtime_helper('helper')"
    _write(astra,(
        "import importlib.util\n"
        "def _load_runtime_helper(x): pass\n"
        "def f():\n"
        f"    {call}\n"
        "    importlib.util.spec_from_file_location('x','y')\n"
    ))
    _write(fixed,"x=1\n")
    _write(helper,"x=1\n")
    _write(adapter,"def run(*a): return {}\n")
    reg.parent.mkdir(parents=True,exist_ok=True)
    reg.write_text(json.dumps({"capabilities":{"C":{"adapter_module":"demo","source":{"type":"python_stdlib"}}}}),encoding="utf-8")
    manifest={
        "schema":"PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V1",
        "subject":{
            "astra_runtime":{"path":"canonical/runtime/astra_runtime.py","git_blob_sha":git_blob_sha(astra.read_bytes())},
            "bound_capability_registry":{"path":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json","git_blob_sha":git_blob_sha(reg.read_bytes())},
        },
        "expected_repo_dynamic_universe":{
            "spec_from_file_location_call_count":1,
            "literal_runtime_helpers":["helper"],
            "bound_adapter_modules":["demo"],
            "fixed_repo_loader_paths":["canonical/runtime/fixed.py"],
        },
    }
    mp=tmp_path/"canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V1.json"
    mp.parent.mkdir(parents=True,exist_ok=True)
    mp.write_text(json.dumps(manifest),encoding="utf-8")
    return mp


def test_finite_repo_dynamic_universe_compiles(tmp_path):
    _fixture(tmp_path)
    out=compile_registry(tmp_path,"canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V1.json")
    assert out["repo_dynamic_module_universe_closed"] is True
    assert out["registered_repo_module_count"]==3
    assert out["c1_channel_registry_scope_complete"] is False
    assert out["acceptance_credit_delta"]==0


def test_nonliteral_runtime_helper_fails_closed(tmp_path):
    _fixture(tmp_path,nonliteral=True)
    with pytest.raises(RegistryError,match="NONLITERAL_RUNTIME_HELPER_CALL"):
        compile_registry(tmp_path,"canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V1.json")


def test_blob_drift_fails_closed(tmp_path):
    mp=_fixture(tmp_path)
    astra=tmp_path/"canonical/runtime/astra_runtime.py"
    astra.write_text(astra.read_text()+"# drift\n")
    with pytest.raises(RegistryError,match="ASTRA_RUNTIME_BLOB_DRIFT"):
        compile_registry(tmp_path,"canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V1.json")
