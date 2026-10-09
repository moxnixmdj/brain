from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime import d_finality_execution_epoch_v1 as d
from canonical.runtime import live_capability_composition_v1 as composition


def _policy_and_cert(root: Path, allowed):
    material=root/"material.txt"
    material.write_text("sealed\n",encoding="utf-8")
    materials=[{"path":"material.txt","git_blob_sha":d.git_blob_sha_file(material)}]
    policy={
      "schema":d.POLICY_SCHEMA,
      "status":"ACTIVE_FAIL_CLOSED",
      "semantic_version":"composition-d-epoch-v1",
      "rule":"NO_UNCERTIFIED_AUTHORITY_WIDENING",
      "revoked_certificate_sha256":[],
    }
    policy["policy_sha256"]=d.policy_sha256(policy)
    cert={
      "schema":d.CERT_SCHEMA,
      "status":"VERIFIED_D_FINAL",
      "capability_id":allowed[0],
      "capability_contract_sha256":d.sha256_json({"scope":"composition-d-epoch"}),
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


def _manifest(second="bound:B", step_options=None):
    return {
      "composition_id":"d-epoch-composition",
      "inputs":{},
      "composition_steps":[
        {"step_id":"a","capability_id":"engine:A","payload":{}},
        {
          "step_id":"b",
          "capability_id":second,
          "depends_on":["a"],
          "payload":{},
          "options":step_options or {},
        },
      ],
      "outputs":{},
    }


class CompositionDEpochTests(unittest.TestCase):
    def test_no_epoch_preserves_experimental_composition(self):
        calls=[]
        out=composition.execute(
            _manifest(),
            invoke_capability=lambda cid,payload,opts: (
                calls.append(cid) or {"pass":True,"status":"OK"}
            ),
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(calls,["engine:A","bound:B"])

    def test_active_epoch_allows_only_members(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            policy,cert=_policy_and_cert(root,["engine:A","bound:B"])
            calls=[]
            with d.activate(cert,policy=policy,repo_root=root):
                out=composition.execute(
                    _manifest(),
                    invoke_capability=lambda cid,payload,opts: (
                        calls.append(cid) or {"pass":True,"status":"OK"}
                    ),
                )
            self.assertTrue(out["pass"],out)
            self.assertEqual(calls,["engine:A","bound:B"])

    def test_out_of_epoch_step_fails_before_callback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            policy,cert=_policy_and_cert(root,["engine:A"])
            calls=[]
            with d.activate(cert,policy=policy,repo_root=root):
                out=composition.execute(
                    _manifest(second="bound:UNAUTHORIZED"),
                    invoke_capability=lambda cid,payload,opts: (
                        calls.append(cid) or {"pass":True,"status":"OK"}
                    ),
                )
            self.assertFalse(out["pass"])
            self.assertIn("CAPABILITY_OUTSIDE_EPOCH:bound:UNAUTHORIZED",out["reason"])
            self.assertEqual(calls,["engine:A"])

    def test_step_options_cannot_smuggle_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            policy,cert=_policy_and_cert(root,["engine:A"])
            calls=[]
            with d.activate(cert,policy=policy,repo_root=root):
                out=composition.execute(
                    _manifest(
                        second="bound:UNAUTHORIZED",
                        step_options={
                          "allowed_capability_ids":["bound:UNAUTHORIZED"],
                          "d_finality_override":True,
                        },
                    ),
                    invoke_capability=lambda cid,payload,opts: (
                        calls.append((cid,dict(opts))) or {"pass":True,"status":"OK"}
                    ),
                )
            self.assertFalse(out["pass"])
            self.assertIn("CAPABILITY_OUTSIDE_EPOCH:bound:UNAUTHORIZED",out["reason"])
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0][0],"engine:A")


if __name__=="__main__":
    unittest.main(verbosity=2)
