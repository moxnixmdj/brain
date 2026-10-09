from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


def _mod(name, **attrs):
    m=types.ModuleType(name)
    for k,v in attrs.items():
        setattr(m,k,v)
    sys.modules[name]=m
    return m


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n",encoding="utf-8")


def _load_runtime(root: Path):
    runtime=root/"canonical/runtime"
    # Real D primitives first.
    ds=importlib.util.spec_from_file_location(
        "canonical.runtime.d_finality_execution_epoch_v1",
        runtime/"d_finality_execution_epoch_v1.py",
    )
    d=importlib.util.module_from_spec(ds); sys.modules[ds.name]=d; ds.loader.exec_module(d)
    rs=importlib.util.spec_from_file_location(
        "canonical.runtime.d_finality_canonical_resolver_v1",
        runtime/"d_finality_canonical_resolver_v1.py",
    )
    resolver=importlib.util.module_from_spec(rs); sys.modules[rs.name]=resolver; rs.loader.exec_module(resolver)

    state={"p3_calls":0,"p3_epoch_seen":False,"drain_calls":0}
    def p3_eval(payload,repo_root=None):
        state["p3_calls"]+=1
        state["p3_epoch_seen"]=d.has_active_epoch()
        return {"pass":True,"status":"P3_OK","payload":dict(payload)}

    _mod("canonical.runtime.live_integrated_brain_v1",load_verified_registry=lambda:{})
    _mod("canonical.runtime.p3_real_context_v3_admission_v12",evaluate=p3_eval)
    _mod("canonical.runtime.autonomous_verified_self_improvement_v1",DEFAULT_STATE_PATH=root/"state.json")
    _mod("canonical.runtime.r3_improvement_queue_driver_v1",drain=lambda **kw:(state.__setitem__("drain_calls",state["drain_calls"]+1) or {"pass":True}))
    _mod("canonical.runtime.live_brain_runtime_v1",SURFACES=(),observe_runtime_outcome=lambda *a,**k:{"pass":True})
    _mod("canonical.runtime.h100_verified_capability_registry_v8")
    _mod("canonical.runtime.exact_linear_parameter_polytope_v1")
    _mod("canonical.runtime.interval_information_frontier_v1")
    _mod("canonical.runtime.capability_first_scheduler_v1")
    _mod("canonical.runtime.brain_owned_python_closure_census_v1",census=lambda *a,**k:{"brain_owned_file_count":0,"brain_owned_transitive_source_bytes":0,"brain_owned_transitive_files":[]})
    _mod("canonical.runtime.current_authority_runtime_census_v1",run=lambda *a,**k:{"pass":True,"authority_pointer_reference_missing_count":0,"authority_pointer_reference_missing_paths":[]})
    _mod("canonical.runtime.live_capability_ownership_v1",evaluate=lambda *a,**k:{"live_owned_capability_ids":[],"live_owned_capability_count":0,"pass":False,"r1_structural_closure":False})
    _mod("canonical.runtime.live_capability_invoker_v1")
    _mod("canonical.runtime.live_capability_composition_v1")
    _mod("canonical.runtime.r1_live_architecture_closure_gate_v1",evaluate=lambda *a,**k:{"pass":False,"errors":["TEST"]})
    _mod("canonical.runtime.universal_escape_resolver_v1")
    _mod("canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2")
    _mod("canonical.runtime.terminal_autopilot_v1")
    _mod("canonical.runtime.terminal_root_decision_gate_v1")
    _mod("canonical.runtime.terminal_closure_reducer")
    _mod("canonical.runtime.verified_bound_capability_execution_adapter_v1",execute=lambda *a,**k:{"pass":True})
    _mod("canonical.runtime.semantic_ambiguity_control_v1")
    _mod("canonical.runtime.semantic_relation_control_v1")
    _mod("canonical.runtime.oewn_decision_sense_control_v1")
    physical_calls=[]
    def physical_run(request,*,capability_id,repo_root):
        physical_calls.append({
            "request":dict(request),
            "capability_id":capability_id,
            "repo_root":str(repo_root),
        })
        return {
          "pass":True,
          "status":"PASS__PHYSICAL_D_FINAL_ZERO_AMBIENT",
          "certificate_sha256":"1"*64,
          "policy_sha256":"2"*64,
          "execution_epoch_sha256":"3"*64,
          "material_closure_root":"4"*64,
          "launcher_git_blob_sha":"5"*40,
          "child_git_blob_sha":"6"*40,
          "launcher_policy_sha256":"7"*64,
          "broker_sha256":"8"*64,
          "material_effects_committed":0,
          "result":{
            "schema":"PROJECT_BRAIN_UNIFIED_COGNITIVE_FABRIC_V1",
            "status":"FABRIC_DISPATCH_COMPLETE",
            "mode":"P3",
            "requested_mode":"P3",
            "auto_routed":False,
            "engine":"p3_real_context_v3_admission_v12.evaluate",
            "inner_pass":True,
            "inner_status":"P3_OK",
            "result":{"pass":True,"status":"P3_OK"},
            "single_front_door":True,
            "terminal_authority":False,
            "terminal_credit_delta":0,
          },
        }
    _mod("canonical.runtime.d_finality_zero_ambient_frontdoor_v1",run=physical_run)

    us=importlib.util.spec_from_file_location(
        "fabric_under_test",
        runtime/"unified_cognitive_fabric_v1.py",
    )
    fabric=importlib.util.module_from_spec(us); us.loader.exec_module(fabric)
    state["physical_calls"]=physical_calls
    return d,resolver,fabric,state


def _build_authority(root: Path, d, resolver, cid="engine:P3", status="VERIFIED_D_FINAL_CURRENT"):
    material=root/"canonical/runtime/material.txt"
    material.parent.mkdir(parents=True,exist_ok=True)
    material.write_text("sealed\n",encoding="utf-8")
    mats=[{"path":"canonical/runtime/material.txt","git_blob_sha":d.git_blob_sha_file(material)}]
    policy={
      "schema":d.POLICY_SCHEMA,"status":"ACTIVE_FAIL_CLOSED",
      "semantic_version":"fabric-frontdoor-v1",
      "rule":"NO_UNCERTIFIED_AUTHORITY_WIDENING",
      "revoked_certificate_sha256":[],
    }
    policy["policy_sha256"]=d.policy_sha256(policy)
    cert={
      "schema":d.CERT_SCHEMA,"status":"VERIFIED_D_FINAL",
      "capability_id":cid,
      "capability_contract_sha256":d.sha256_json({"capability_id":cid}),
      "policy_sha256":policy["policy_sha256"],
      "registry_snapshot_root":d.sha256_json({"registry":"frozen"}),
      "state_snapshot_root":d.sha256_json({"state":"frozen"}),
      "materials":mats,
      "material_closure_root":d.material_closure_root(mats),
      "allowed_capability_ids":[cid],
      "allowed_knowledge_channels":[],
      "allowed_effect_channels":[],
      "donor_authority_zero":True,"fresh_replay_pass":True,
      "independent_replay_pass":True,
      "knowledge_capability_nonsmuggling_pass":True,
      "undeclared_dependency_count":0,
    }
    cert["certificate_sha256"]=d.certificate_sha256(cert)
    pp=root/"canonical/governance/d_policy.json"
    cp=root/"canonical/verification/d_cert.json"
    _write_json(pp,policy); _write_json(cp,cert)
    epoch=d.verify_certificate(cert,policy=policy,repo_root=root)
    row={
      "capability_id":cid,"status":status,
      "d_certificate_sha256":cert["certificate_sha256"],
      "material_certificate_sha256":"a"*64,
      "provider_theorem_sha256":"b"*64,
      "policy_sha256":policy["policy_sha256"],
      "execution_epoch_sha256":epoch.epoch_sha256,
      "material_closure_root":epoch.material_closure_root,
      "fresh_replay_pass":True,"independent_replay_pass":True,
      "donor_authority_zero":True,"undeclared_dependency_count":0,
      "certificate_path":"canonical/verification/d_cert.json",
      "policy_path":"canonical/governance/d_policy.json",
      "certificate_git_blob_sha":d.git_blob_sha_file(cp),
      "policy_git_blob_sha":d.git_blob_sha_file(pp),
    }
    reg={"schema":resolver.REGISTRY_SCHEMA,"status":"ACTIVE_FAIL_CLOSED","default":"NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW","rows":[row]}
    _write_json(root/resolver.DEFAULT_REGISTRY,reg)


class FabricDActivationTests(unittest.TestCase):
    def stage(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        src=Path(__file__).resolve().parents[1]/"runtime"
        dst=root/"canonical/runtime"; dst.mkdir(parents=True)
        for name in (
            "d_finality_execution_epoch_v1.py",
            "d_finality_canonical_resolver_v1.py",
            "unified_cognitive_fabric_v1.py",
        ):
            (dst/name).write_bytes((src/name).read_bytes())
        return td,root,_load_runtime(root)

    def test_experimental_mode_runs_without_d_authority(self):
        td,root,(d,resolver,fabric,state)=self.stage()
        self.addCleanup(td.cleanup)
        out=fabric.run({"mode":"P3","payload":{"x":1},"options":{"learn":False}})
        self.assertEqual(out["status"],"FABRIC_DISPATCH_COMPLETE")
        self.assertTrue(out["inner_pass"])
        self.assertFalse(state["p3_epoch_seen"])
        self.assertEqual(state["p3_calls"],1)

    def test_d_final_routes_only_through_physical_membrane(self):
        td,root,(d,resolver,fabric,state)=self.stage()
        self.addCleanup(td.cleanup)
        out=fabric.run({
          "mode":"P3",
          "payload":{"fresh":1},
          "options":{"learn":True},
          "ownership_mode":"D_FINAL",
        })
        self.assertEqual(out["status"],"FABRIC_DISPATCH_COMPLETE")
        self.assertTrue(out["inner_pass"])
        self.assertEqual(state["p3_calls"],0)
        self.assertEqual(len(state["physical_calls"]),1)
        call=state["physical_calls"][0]
        self.assertEqual(call["capability_id"],"engine:P3")
        self.assertNotIn("ownership_mode",call["request"])
        self.assertFalse(call["request"]["options"]["learn"])
        self.assertEqual(out["d_finality"]["mode"],"D_FINAL")
        self.assertTrue(out["d_finality"]["physical_zero_ambient_enforced"])
        self.assertEqual(out["d_finality"]["material_effects_committed"],0)

    def test_d_certified_context_uses_only_canonical_authority(self):
        td,root,(d,resolver,fabric,state)=self.stage()
        self.addCleanup(td.cleanup)
        _build_authority(root,d,resolver)
        out=fabric.run({"mode":"P3","payload":{"fresh":1},"ownership_mode":"D_CERTIFIED_CONTEXT"})
        self.assertEqual(out["status"],"FABRIC_DISPATCH_COMPLETE")
        self.assertTrue(out["inner_pass"])
        self.assertTrue(state["p3_epoch_seen"])
        self.assertEqual(state["drain_calls"],0)
        self.assertEqual(out["d_finality"]["mode"],"D_CERTIFIED_CONTEXT")
        self.assertFalse(out["d_finality"]["physical_zero_ambient_enforced"])
        self.assertFalse(d.has_active_epoch())

    def test_pending_canonical_row_cannot_activate_context(self):
        td,root,(d,resolver,fabric,state)=self.stage()
        self.addCleanup(td.cleanup)
        _build_authority(root,d,resolver,status="PENDING_D_FINAL_CERTIFICATE")
        out=fabric.run({"mode":"P3","payload":{},"ownership_mode":"D_CERTIFIED_CONTEXT"})
        self.assertFalse(out["pass"])
        self.assertIn("CAPABILITY_NOT_CURRENT_D_FINAL",out["reason"])
        self.assertEqual(state["p3_calls"],0)

    def test_caller_supplied_certificate_is_rejected_before_dispatch(self):
        td,root,(d,resolver,fabric,state)=self.stage()
        self.addCleanup(td.cleanup)
        out=fabric.run({
          "mode":"P3","payload":{},
          "d_finality_certificate":{"forged":True},
        })
        self.assertFalse(out["pass"])
        self.assertIn("CALLER_SUPPLIED_D_AUTHORITY_FORBIDDEN",out["reason"])
        self.assertEqual(state["p3_calls"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
