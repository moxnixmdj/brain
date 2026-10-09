from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/"canonical/runtime"


def _fake(name, **attrs):
    mod=types.ModuleType(name)
    for k,v in attrs.items():
        setattr(mod,k,v)
    sys.modules[name]=mod
    return mod


def _load():
    dspec=importlib.util.spec_from_file_location(
        "canonical.runtime.d_finality_execution_epoch_v1",
        RUNTIME/"d_finality_execution_epoch_v1.py",
    )
    d=importlib.util.module_from_spec(dspec)
    sys.modules[dspec.name]=d
    dspec.loader.exec_module(d)

    _fake(
        "canonical.runtime.autonomous_verified_self_improvement_v1",
        DEFAULT_STATE_PATH=Path("/nonexistent"),
    )
    _fake("canonical.runtime.certificate_gated_selected_route_runtime_entrypoint_v2")
    _fake("canonical.runtime.h100_verified_capability_registry_v8")
    _fake(
        "canonical.runtime.verified_bound_capability_execution_adapter_v1",
        execute=lambda local_id,inputs: {
            "pass":True,
            "status":"FAKE_BOUND_PASS",
            "local_id":local_id,
            "inputs":dict(inputs),
        },
    )

    spec=importlib.util.spec_from_file_location(
        "invoker_under_test",
        RUNTIME/"live_capability_invoker_v1.py",
    )
    inv=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inv)
    return d,inv


def _policy_and_cert(d, root: Path, allowed):
    material=root/"material.txt"
    material.write_text("sealed\n",encoding="utf-8")
    materials=[{"path":"material.txt","git_blob_sha":d.git_blob_sha_file(material)}]
    policy={
      "schema":d.POLICY_SCHEMA,
      "status":"ACTIVE_FAIL_CLOSED",
      "semantic_version":"invoker-independent-v1",
      "rule":"NO_UNCERTIFIED_AUTHORITY_WIDENING",
      "revoked_certificate_sha256":[],
    }
    policy["policy_sha256"]=d.policy_sha256(policy)
    cert={
      "schema":d.CERT_SCHEMA,
      "status":"VERIFIED_D_FINAL",
      "capability_id":allowed[0],
      "capability_contract_sha256":d.sha256_json({"scope":"invoker-independent"}),
      "policy_sha256":policy["policy_sha256"],
      "registry_snapshot_root":d.sha256_json({"registry":"frozen"}),
      "state_snapshot_root":d.sha256_json({"state":"frozen"}),
      "materials":materials,
      "material_closure_root":d.material_closure_root(materials),
      "allowed_capability_ids":list(allowed),
      "allowed_knowledge_channels":[],
      "allowed_effect_channels":[],
      "donor_authority_zero":True,
      "fresh_replay_pass":True,
      "independent_replay_pass":True,
      "knowledge_capability_nonsmuggling_pass":True,
      "undeclared_dependency_count":0,
    }
    cert["certificate_sha256"]=d.certificate_sha256(cert)
    return policy,cert


class InvokerDEpochTests(unittest.TestCase):
    def test_no_epoch_preserves_experimental_execution(self):
        d,inv=_load()
        calls=[]
        out=inv.invoke(
            "engine:TEST",
            {"x":1},
            engine_runner=lambda mode,payload,opts: (
                calls.append((mode,dict(payload))) or {"pass":True,"status":"OK"}
            ),
        )
        self.assertTrue(out["pass"])
        self.assertEqual(calls,[("TEST",{"x":1})])
        self.assertFalse(d.has_active_epoch())

    def test_active_epoch_sets_child_identity_and_allows_member(self):
        d,inv=_load()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            policy,cert=_policy_and_cert(d,root,["engine:TEST"])
            seen=[]
            def runner(mode,payload,opts):
                epoch=d.current_epoch()
                seen.append((mode,epoch.root_capability_id,epoch.current_capability_id))
                return {"pass":True,"status":"OK"}
            with d.activate(cert,policy=policy,repo_root=root):
                out=inv.invoke("engine:TEST",{},engine_runner=runner)
                self.assertTrue(out["pass"])
                self.assertEqual(d.current_epoch().current_capability_id,"engine:TEST")
            self.assertEqual(seen,[("TEST","engine:TEST","engine:TEST")])
            self.assertFalse(d.has_active_epoch())

    def test_out_of_epoch_capability_is_denied_before_dispatch(self):
        d,inv=_load()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            policy,cert=_policy_and_cert(d,root,["engine:TEST"])
            calls=[]
            with d.activate(cert,policy=policy,repo_root=root):
                with self.assertRaisesRegex(d.DFinalityError,"CAPABILITY_OUTSIDE_EPOCH"):
                    inv.invoke(
                        "engine:OTHER",
                        {},
                        engine_runner=lambda *args: calls.append(args) or {"pass":True},
                    )
            self.assertEqual(calls,[])

    def test_bound_member_uses_same_epoch_gate(self):
        d,inv=_load()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            policy,cert=_policy_and_cert(d,root,["bound:B"])
            with d.activate(cert,policy=policy,repo_root=root):
                out=inv.invoke("bound:B",{"v":7},engine_runner=lambda *_: {"pass":True})
                self.assertTrue(out["pass"])
                self.assertEqual(out["result"]["local_id"],"B")
                with self.assertRaisesRegex(d.DFinalityError,"CAPABILITY_OUTSIDE_EPOCH"):
                    inv.invoke("bound:C",{},engine_runner=lambda *_: {"pass":True})


if __name__=="__main__":
    unittest.main(verbosity=2)
