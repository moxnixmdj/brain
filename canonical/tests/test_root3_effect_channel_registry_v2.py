from __future__ import annotations

import json
from pathlib import Path

import pytest

from canonical.runtime.root3_effect_channel_registry_v2 import (
    RegistryError,
    compile_registry,
    git_blob_sha,
)


def _write(path: Path,text: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding="utf-8")


def _fixture(tmp_path: Path, *, helper_literal=True, native_impl=True):
    astra=tmp_path/"canonical/runtime/astra_runtime.py"
    reg=tmp_path/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    fixed=tmp_path/"canonical/runtime/fixed.py"
    helper=tmp_path/"canonical/runtime/helper.py"
    adapter=tmp_path/"canonical/runtime/bound_capabilities/demo.py"

    helper_call="_load_runtime_helper('helper')" if helper_literal else "_load_runtime_helper(name)"
    native_if="    if typ=='native_action': return {}\n" if native_impl else ""
    astra_text=(
        "import importlib.util\n"
        "def _load_runtime_helper(x):\n"
        "    importlib.util.spec_from_file_location('h','x')\n"
        "def _invoke_bound_capability(x):\n"
        "    importlib.util.spec_from_file_location('a','x')\n"
        "def _load_fixed():\n"
        "    path='fixed.py'\n"
        "    importlib.util.spec_from_file_location('f',path)\n"
        "def _goal_action(action):\n"
        "    typ=action.get('type')\n"
        +native_if+
        "def _run_model_independent_goal():\n"
        "    allowed_types={'native_action'}\n"
        "def caller():\n"
        f"    {helper_call}\n"
    )
    _write(astra,astra_text)
    _write(fixed,"x=1\n")
    _write(helper,"x=1\n")
    _write(adapter,"def run(*a): return {}\n")
    reg.parent.mkdir(parents=True,exist_ok=True)
    reg.write_text(json.dumps({
      "capabilities":{
        "NORMAL":{
          "adapter_module":"demo",
          "source":{"type":"python_stdlib"},
        },
        "NATIVE":{
          "adapter_module":"runtime_native_action",
          "action_template":{"type":"native_action","args":{}},
          "source":{
            "type":"runtime_native",
            "runtime_path":"canonical/runtime/astra_runtime.py",
            "action_type":"native_action",
          },
        },
      }
    }),encoding="utf-8")

    manifest={
      "schema":"PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2",
      "subject":{
        "astra_runtime":{
          "path":"canonical/runtime/astra_runtime.py",
          "git_blob_sha":git_blob_sha(astra.read_bytes()),
        },
        "bound_capability_registry":{
          "path":"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json",
          "git_blob_sha":git_blob_sha(reg.read_bytes()),
        },
      },
      "expected_repo_dynamic_universe":{
        "spec_loader_site_functions":[
          "_invoke_bound_capability","_load_fixed","_load_runtime_helper"
        ],
        "fixed_loader_sites":{"_load_fixed":"canonical/runtime/fixed.py"},
        "literal_runtime_helpers":["helper"],
        "ordinary_adapter_modules":["demo"],
        "runtime_native_actions":[{
          "capability_id":"NATIVE",
          "action_type":"native_action",
          "runtime_path":"canonical/runtime/astra_runtime.py",
          "execution_class":"DIRECT_GOAL_ACTION",
        }],
      },
    }
    mp=tmp_path/"canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json"
    mp.parent.mkdir(parents=True,exist_ok=True)
    mp.write_text(json.dumps(manifest),encoding="utf-8")
    return mp


def test_four_execution_classes_compile(tmp_path):
    _fixture(tmp_path)
    out=compile_registry(
        tmp_path,
        "canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json",
    )
    assert out["repo_local_dynamic_execution_universe_closed"] is True
    assert out["runtime_native_direct_action_universe_closed"] is True
    assert out["ordinary_adapter_module_count"]==1
    assert out["runtime_native_action_count"]==1
    assert out["registered_repo_module_count"]==3
    assert out["c1_channel_registry_scope_complete"] is False
    assert out["acceptance_credit_delta"]==0


def test_nonliteral_helper_fails_closed(tmp_path):
    _fixture(tmp_path,helper_literal=False)
    with pytest.raises(RegistryError,match="NONLITERAL_RUNTIME_HELPER_CALL"):
        compile_registry(
            tmp_path,
            "canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json",
        )


def test_missing_runtime_native_implementation_fails_closed(tmp_path):
    _fixture(tmp_path,native_impl=False)
    with pytest.raises(RegistryError,match="RUNTIME_NATIVE_GOAL_ACTION_MISSING"):
        compile_registry(
            tmp_path,
            "canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json",
        )


def test_blob_drift_fails_closed(tmp_path):
    _fixture(tmp_path)
    p=tmp_path/"canonical/runtime/astra_runtime.py"
    p.write_text(p.read_text()+"# drift\n",encoding="utf-8")
    with pytest.raises(RegistryError,match="ASTRA_RUNTIME_BLOB_DRIFT"):
        compile_registry(
            tmp_path,
            "canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json",
        )
