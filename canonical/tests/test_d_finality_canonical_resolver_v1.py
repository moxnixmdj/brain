from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import d_finality_execution_epoch_v1 as d
from canonical.runtime import d_finality_canonical_resolver_v1 as r


def write_json(path: Path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n",encoding="utf-8")


def build(root: Path, capability_id="engine:TEST"):
    material=root/"canonical/runtime/material.txt"
    material.parent.mkdir(parents=True,exist_ok=True)
    material.write_text("sealed\n",encoding="utf-8")
    materials=[{
      "path":"canonical/runtime/material.txt",
      "git_blob_sha":d.git_blob_sha_file(material),
    }]
    policy={
      "schema":d.POLICY_SCHEMA,
      "status":"ACTIVE_FAIL_CLOSED",
      "semantic_version":"resolver-test-v1",
      "rule":"NO_UNCERTIFIED_AUTHORITY_WIDENING",
      "revoked_certificate_sha256":[],
    }
    policy["policy_sha256"]=d.policy_sha256(policy)
    cert={
      "schema":d.CERT_SCHEMA,
      "status":"VERIFIED_D_FINAL",
      "capability_id":capability_id,
      "capability_contract_sha256":d.sha256_json({"capability_id":capability_id}),
      "policy_sha256":policy["policy_sha256"],
      "registry_snapshot_root":d.sha256_json({"registry":"sealed"}),
      "state_snapshot_root":d.sha256_json({"state":"sealed"}),
      "materials":materials,
      "material_closure_root":d.material_closure_root(materials),
      "allowed_capability_ids":[capability_id],
      "allowed_knowledge_channels":[],
      "allowed_effect_channels":[],
      "donor_authority_zero":True,
      "fresh_replay_pass":True,
      "independent_replay_pass":True,
      "knowledge_capability_nonsmuggling_pass":True,
      "undeclared_dependency_count":0,
    }
    cert["certificate_sha256"]=d.certificate_sha256(cert)
    policy_path=root/"canonical/governance/d_policy.json"
    cert_path=root/"canonical/verification/d_cert.json"
    write_json(policy_path,policy)
    write_json(cert_path,cert)
    epoch=d.verify_certificate(cert,policy=policy,repo_root=root)
    row={
      "capability_id":capability_id,
      "status":"VERIFIED_D_FINAL_CURRENT",
      "d_certificate_sha256":cert["certificate_sha256"],
      "material_certificate_sha256":"a"*64,
      "provider_theorem_sha256":"b"*64,
      "policy_sha256":policy["policy_sha256"],
      "execution_epoch_sha256":epoch.epoch_sha256,
      "material_closure_root":epoch.material_closure_root,
      "fresh_replay_pass":True,
      "independent_replay_pass":True,
      "donor_authority_zero":True,
      "undeclared_dependency_count":0,
      "certificate_path":"canonical/verification/d_cert.json",
      "policy_path":"canonical/governance/d_policy.json",
      "certificate_git_blob_sha":d.git_blob_sha_file(cert_path),
      "policy_git_blob_sha":d.git_blob_sha_file(policy_path),
    }
    registry={
      "schema":r.REGISTRY_SCHEMA,
      "status":"ACTIVE_FAIL_CLOSED",
      "default":"NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW",
      "rows":[row],
    }
    registry_path=root/r.DEFAULT_REGISTRY
    write_json(registry_path,registry)
    return {
      "material":material,"policy":policy,"cert":cert,
      "policy_path":policy_path,"cert_path":cert_path,
      "row":row,"registry":registry,"registry_path":registry_path,
      "epoch":epoch,
    }


class ResolverTests(unittest.TestCase):
    def test_verified_current_row_resolves_exact_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            x=build(root)
            out=r.resolve_for_capability("engine:TEST",repo_root=root)
            self.assertTrue(out["pass"])
            self.assertEqual(out["execution_epoch_sha256"],x["epoch"].epoch_sha256)
            self.assertEqual(out["certificate_sha256"],x["cert"]["certificate_sha256"])

    def test_pending_row_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            x=build(root)
            x["registry"]["rows"][0]["status"]="PENDING_D_FINAL_CERTIFICATE"
            write_json(x["registry_path"],x["registry"])
            with self.assertRaisesRegex(r.DFinalityResolutionError,"CAPABILITY_NOT_CURRENT_D_FINAL"):
                r.resolve_for_capability("engine:TEST",repo_root=root)

    def test_certificate_byte_drift_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            x=build(root)
            x["cert_path"].write_text(x["cert_path"].read_text()+"\n",encoding="utf-8")
            with self.assertRaisesRegex(r.DFinalityResolutionError,"CERTIFICATE_BLOB_DRIFT"):
                r.resolve_for_capability("engine:TEST",repo_root=root)

    def test_policy_byte_drift_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            x=build(root)
            x["policy_path"].write_text(x["policy_path"].read_text()+"\n",encoding="utf-8")
            with self.assertRaisesRegex(r.DFinalityResolutionError,"POLICY_BLOB_DRIFT"):
                r.resolve_for_capability("engine:TEST",repo_root=root)

    def test_material_drift_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            x=build(root)
            x["material"].write_text("mutated\n",encoding="utf-8")
            with self.assertRaisesRegex(d.DFinalityError,"MATERIAL_BLOB_DRIFT"):
                r.resolve_for_capability("engine:TEST",repo_root=root)

    def test_registry_epoch_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            x=build(root)
            x["registry"]["rows"][0]["execution_epoch_sha256"]="0"*64
            write_json(x["registry_path"],x["registry"])
            with self.assertRaisesRegex(r.DFinalityResolutionError,"REGISTRY_EXECUTION_EPOCH_MISMATCH"):
                r.resolve_for_capability("engine:TEST",repo_root=root)


if __name__=="__main__":
    unittest.main(verbosity=2)
