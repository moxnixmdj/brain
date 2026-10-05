from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime.root3_child_process_census_v1 import (
    PROCESS_APIS,
    compile_census,
    git_blob_sha,
)


def test_current_registered_process_surface_is_finite():
    root=Path(__file__).resolve().parents[2]
    out=compile_census(
        root,
        "canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json",
    )
    assert out["registered_execution_universe_fully_parsed"] is True
    assert out["registered_execution_module_count"] > 0
    assert out["spawn_site_count"] > 0
    assert set(out["spawn_apis"]).issubset(PROCESS_APIS)
    assert out["child_process_internal_effect_totality_proved"] is False
    assert out["acceptance_credit_delta"]==0


def test_alias_detection_fixture(tmp_path):
    root=tmp_path
    (root/"canonical/runtime/bound_capabilities").mkdir(parents=True)
    astra=root/"canonical/runtime/astra_runtime.py"
    astra.write_text(
        "import subprocess as sp\n"
        "def f():\n"
        "    return sp.run(['echo','x'])\n",
        encoding="utf-8",
    )
    adapter=root/"canonical/runtime/bound_capabilities/demo.py"
    adapter.write_text(
        "from subprocess import Popen as P\n"
        "def run():\n"
        "    return P(['echo','y'])\n",
        encoding="utf-8",
    )
    manifest={
      "schema":"PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2",
      "expected_repo_dynamic_universe":{
        "fixed_loader_sites":{},
        "literal_runtime_helpers":[],
        "ordinary_adapter_modules":["demo"],
      },
    }
    p=root/"canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(manifest),encoding="utf-8")
    out=compile_census(root,p.relative_to(root))
    assert out["spawn_site_count"]==2
    assert {x["api"] for x in out["spawn_sites"]}=={"subprocess.run","subprocess.Popen"}
