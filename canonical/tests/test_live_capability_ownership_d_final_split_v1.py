from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


HERE=Path(__file__).resolve()
ROOT=HERE.parents[2]
RUNTIME=ROOT/"canonical/runtime"


def _install_fake_module(name, **attrs):
    mod=types.ModuleType(name)
    for key,value in attrs.items():
        setattr(mod,key,value)
    sys.modules[name]=mod
    return mod


def _load_ownership():
    # Build only the provider surfaces live_capability_ownership_v1 imports.
    fake_live=_install_fake_module(
        "canonical.runtime.live_integrated_brain_v1",
        load_verified_registry=lambda: {"b1":{},"b2":{}},
    )
    fake_self=_install_fake_module(
        "canonical.runtime.autonomous_verified_self_improvement_v1",
        DEFAULT_STATE_PATH=Path("/nonexistent/state.json"),
        load_state=lambda _p=None: {"skills":{}},
    )
    fake_h100=_install_fake_module(
        "canonical.runtime.h100_verified_capability_registry_v8",
        REGISTRY=({"capability_id":"H1","route":"R1"},),
    )
    class Receipt:
        def __init__(self,route_id,admitted=True):
            self.route_id=route_id
            self.admitted=admitted
    fake_cert=_install_fake_module(
        "canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2",
        load_registry=lambda: {},
        _verified_rows=lambda _r: ([Receipt("R1",True)],[]),
    )

    # Load the real D coverage reducer.
    d_spec=importlib.util.spec_from_file_location(
        "canonical.runtime.d_finality_coverage_gate_v1",
        RUNTIME/"d_finality_coverage_gate_v1.py",
    )
    d_mod=importlib.util.module_from_spec(d_spec)
    sys.modules[d_spec.name]=d_mod
    d_spec.loader.exec_module(d_mod)

    spec=importlib.util.spec_from_file_location(
        "ownership_under_test",
        RUNTIME/"live_capability_ownership_v1.py",
    )
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _manifest(path: Path):
    doc={
      "schema":"PROJECT_BRAIN_LIVE_CAPABILITY_OWNERSHIP_MANIFEST_V1",
      "status":"ACTIVE_AUTHORITATIVE_LIVE_ADMISSION_AND_D_FINAL_OWNERSHIP_ONTOLOGY",
      "default":"NOT_LIVE_OWNED_UNLESS_D_FINAL_CERTIFIED",
      "providers":{
        "FABRIC_ENGINES":{"fabric_carrier":"DIRECT_ENGINE_MODE"},
        "VERIFIED_BOUND_CAPABILITIES":{"fabric_carrier":"BOUND_CAPABILITY"},
        "ACTIVE_VERIFIED_LEARNED_SKILLS":{"fabric_carrier":"LEARNING_EPISODE"},
        "H100_VERIFIED_CAPABILITIES":{"fabric_carrier":"H100_INFERENCE"},
        "CERTIFICATE_GATED_SELECTED_ROUTES":{"fabric_carrier":"CERTIFIED_ROUTE"},
      },
    }
    path.write_text(json.dumps(doc),encoding="utf-8")


def _pending_registry(path: Path, ids):
    doc={
      "schema":"PROJECT_BRAIN_D_FINALITY_CERTIFICATE_REGISTRY_V1",
      "status":"ACTIVE_FAIL_CLOSED",
      "default":"NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW",
      "rows":[
        {"capability_id":cid,"status":"PENDING_D_FINAL_CERTIFICATE"}
        for cid in ids
      ],
    }
    path.write_text(json.dumps(doc),encoding="utf-8")


def _verified_registry(path: Path, ids):
    rows=[]
    for i,cid in enumerate(ids):
        h=(f"{i+1:064x}")[-64:]
        rows.append({
          "capability_id":cid,
          "status":"VERIFIED_D_FINAL_CURRENT",
          "d_certificate_sha256":h,
          "material_certificate_sha256":("a"*63)+hex((i%15)+1)[2:],
          "provider_theorem_sha256":"b"*64,
          "policy_sha256":"c"*64,
          "execution_epoch_sha256":"d"*64,
          "material_closure_root":"e"*64,
          "fresh_replay_pass":True,
          "independent_replay_pass":True,
          "donor_authority_zero":True,
          "undeclared_dependency_count":0,
        })
    doc={
      "schema":"PROJECT_BRAIN_D_FINALITY_CERTIFICATE_REGISTRY_V1",
      "status":"ACTIVE_FAIL_CLOSED",
      "default":"NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW",
      "rows":rows,
    }
    path.write_text(json.dumps(doc),encoding="utf-8")


class OwnershipDSplitTests(unittest.TestCase):
    ENGINES={
      "RAW_GOAL":"x",
      "BOUND_CAPABILITY":"x",
      "LEARNING_EPISODE":"x",
      "H100_INFERENCE":"x",
      "CERTIFIED_ROUTE":"x",
    }

    def test_pending_registry_preserves_admission_but_grants_zero_ownership(self):
        o=_load_ownership()
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            manifest=td/"manifest.json"
            dreg=td/"d.json"
            _manifest(manifest)

            # First derive the exact synthetic admitted set with a pending registry
            # containing the deterministic expected identities.
            expected=[
              "bound:b1","bound:b2","certified_route:R1","h100:H1",
              "engine:BOUND_CAPABILITY","engine:CERTIFIED_ROUTE",
              "engine:H100_INFERENCE","engine:LEARNING_EPISODE","engine:RAW_GOAL",
            ]
            _pending_registry(dreg,expected)
            out=o.evaluate(
                self.ENGINES,
                manifest_path=manifest,
                d_finality_registry_path=dreg,
                self_improvement_state_path=td/"state.json",
            )
            self.assertEqual(out["live_admitted_capability_ids"],sorted(expected))
            self.assertEqual(out["live_admitted_capability_count"],9)
            self.assertEqual(out["live_owned_capability_count"],0)
            self.assertEqual(out["d_final_missing_capability_count"],9)
            self.assertTrue(out["structurally_admitted_equals_fabric_reachable"])
            self.assertTrue(out["experimental_execution_without_ownership_permitted"])
            self.assertFalse(out["pass"])
            self.assertFalse(out["r1_structural_closure"])

    def test_full_current_d_registry_reopens_ownership_without_changing_admission(self):
        o=_load_ownership()
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            manifest=td/"manifest.json"
            dreg=td/"d.json"
            _manifest(manifest)
            ids=[
              "bound:b1","bound:b2","certified_route:R1","h100:H1",
              "engine:BOUND_CAPABILITY","engine:CERTIFIED_ROUTE",
              "engine:H100_INFERENCE","engine:LEARNING_EPISODE","engine:RAW_GOAL",
            ]
            _verified_registry(dreg,ids)
            out=o.evaluate(
                self.ENGINES,
                manifest_path=manifest,
                d_finality_registry_path=dreg,
                self_improvement_state_path=td/"state.json",
            )
            self.assertEqual(out["live_admitted_capability_ids"],sorted(ids))
            self.assertEqual(out["live_owned_capability_ids"],sorted(ids))
            self.assertEqual(out["live_owned_capability_count"],9)
            self.assertEqual(out["d_final_missing_capability_count"],0)
            self.assertTrue(out["d_final_coverage_complete"])
            self.assertTrue(out["live_owned_equals_fabric_reachable"])
            self.assertTrue(out["pass"])
            self.assertTrue(out["r1_structural_closure"])


if __name__=="__main__":
    unittest.main(verbosity=2)
