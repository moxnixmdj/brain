from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import d_finality_execution_epoch_v1 as d
from canonical.runtime import d_finality_canonical_resolver_v1 as resolver
from canonical.runtime import d_finality_zero_ambient_frontdoor_v1 as frontdoor
from canonical.runtime import zero_ambient_namespace_launcher_v1 as zero_ambient


def write_json(path: Path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n",encoding="utf-8")


def stage(root: Path, *, physical_profile=frontdoor.PROFILE, effect_channels=()):
    runtime=root/"canonical/runtime"
    runtime.mkdir(parents=True,exist_ok=True)
    (root/"canonical/__init__.py").write_text("",encoding="utf-8")
    (runtime/"__init__.py").write_text("",encoding="utf-8")

    src=Path(__file__).resolve().parents[1]/"runtime"
    for name in (
        "d_finality_execution_epoch_v1.py",
        "d_finality_zero_ambient_child_v1.py",
    ):
        (runtime/name).write_bytes((src/name).read_bytes())

    # Tiny fabric is enough to prove the physical membrane + D epoch handoff.
    (runtime/"unified_cognitive_fabric_v1.py").write_text(
        "from canonical.runtime import d_finality_execution_epoch_v1 as d\n"
        "def run(request):\n"
        "    mode=str(request.get('mode') or '').strip().upper()\n"
        "    cid='engine:'+mode\n"
        "    d.require_capability(cid)\n"
        "    return {'pass':True,'status':'SYNTHETIC_FABRIC_PASS','mode':mode,"
        "'epoch':d.current_epoch().epoch_sha256,'current':d.current_epoch().current_capability_id}\n",
        encoding="utf-8",
    )

    materials=[]
    for rel in (
        "canonical/__init__.py",
        "canonical/runtime/__init__.py",
        "canonical/runtime/d_finality_execution_epoch_v1.py",
        "canonical/runtime/d_finality_zero_ambient_child_v1.py",
        "canonical/runtime/unified_cognitive_fabric_v1.py",
    ):
        p=root/rel
        materials.append({"path":rel,"git_blob_sha":d.git_blob_sha_file(p)})

    cid="engine:TEST"
    row_contract={
      "capability_id":cid,
      "physical_profile":physical_profile,
      "physical_dispatch_kind":"UNIFIED_FABRIC_V1",
      "dynamic_input_policy":{
        "schema":frontdoor.DYNAMIC_INPUT_SCHEMA,
        "allowed_prefixes":[],
        "allowed_extensions":[],
        "max_files":0,
        "max_total_bytes":0,
        "max_file_bytes":0,
      },
      "allowed_request_keys":["mode","payload"],
      "request_path_fields":[],
    }
    policy={
      "schema":d.POLICY_SCHEMA,"status":"ACTIVE_FAIL_CLOSED",
      "semantic_version":"physical-frontdoor-test-v1",
      "rule":"NO_UNCERTIFIED_AUTHORITY_WIDENING",
      "revoked_certificate_sha256":[],
    }
    policy["policy_sha256"]=d.policy_sha256(policy)
    cert={
      "schema":d.CERT_SCHEMA,"status":"VERIFIED_D_FINAL",
      "capability_id":cid,
      "capability_contract_sha256":d.sha256_json(
          frontdoor.capability_contract(cid,row_contract)
      ),
      "policy_sha256":policy["policy_sha256"],
      "registry_snapshot_root":d.sha256_json({"registry":"sealed"}),
      "state_snapshot_root":d.sha256_json({"state":"sealed"}),
      "materials":materials,
      "material_closure_root":d.material_closure_root(materials),
      "allowed_capability_ids":[cid],
      "allowed_knowledge_channels":[],
      "allowed_effect_channels":list(effect_channels),
      "donor_authority_zero":True,
      "fresh_replay_pass":True,
      "independent_replay_pass":True,
      "knowledge_capability_nonsmuggling_pass":True,
      "undeclared_dependency_count":0,
    }
    cert["certificate_sha256"]=d.certificate_sha256(cert)
    pp=root/"canonical/governance/d_policy.json"
    cp=root/"canonical/verification/d_cert.json"
    write_json(pp,policy); write_json(cp,cert)
    epoch=d.verify_certificate(cert,policy=policy,repo_root=root)

    child=root/frontdoor.CHILD_PATH
    row={
      **row_contract,
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
      "certificate_git_blob_sha":d.git_blob_sha_file(cp),
      "policy_git_blob_sha":d.git_blob_sha_file(pp),
      "zero_ambient_launcher_git_blob_sha":d.git_blob_sha_file(Path(zero_ambient.__file__)),
      "zero_ambient_child_git_blob_sha":d.git_blob_sha_file(child),
    }
    reg={
      "schema":resolver.REGISTRY_SCHEMA,
      "status":"ACTIVE_FAIL_CLOSED",
      "default":"NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW",
      "rows":[row],
    }
    write_json(root/resolver.DEFAULT_REGISTRY,reg)
    return cid,row,cert


class PhysicalFrontdoorTests(unittest.TestCase):
    def test_real_namespace_membrane_executes_certified_pure_request(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cid,row,cert=stage(root)
            out=frontdoor.run(
                {"mode":"TEST","payload":{"fresh":1}},
                capability_id=cid,
                repo_root=root,
            )
            self.assertTrue(out["pass"],out)
            self.assertTrue(out["physical_zero_ambient_enforced"])
            self.assertEqual(out["material_effects_committed"],0)
            self.assertEqual(out["result"]["status"],"SYNTHETIC_FABRIC_PASS")
            self.assertEqual(out["result"]["current"],cid)
            self.assertEqual(out["execution_epoch_sha256"],out["result"]["epoch"])

    def test_nonpure_profile_is_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cid,row,cert=stage(root,physical_profile="TYPED_BROKER_V1")
            with self.assertRaisesRegex(frontdoor.ZeroAmbientDFinalError,"PHYSICAL_PROFILE_NOT_PURE_ZERO_AMBIENT"):
                frontdoor.run({"mode":"TEST","payload":{}},capability_id=cid,repo_root=root)

    def test_effect_channel_is_rejected_by_pure_profile(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cid,row,cert=stage(root,effect_channels=["artifact:write"])
            with self.assertRaisesRegex(frontdoor.ZeroAmbientDFinalError,"PURE_PROFILE_EFFECT_CHANNEL_NOT_EMPTY"):
                frontdoor.run({"mode":"TEST","payload":{}},capability_id=cid,repo_root=root)

    def test_launcher_blob_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cid,row,cert=stage(root)
            reg_path=root/resolver.DEFAULT_REGISTRY
            reg=json.loads(reg_path.read_text())
            reg["rows"][0]["zero_ambient_launcher_git_blob_sha"]="0"*40
            write_json(reg_path,reg)
            with self.assertRaisesRegex(frontdoor.ZeroAmbientDFinalError,"ZERO_AMBIENT_LAUNCHER_BLOB_MISMATCH"):
                frontdoor.run({"mode":"TEST","payload":{}},capability_id=cid,repo_root=root)

    def test_child_blob_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cid,row,cert=stage(root)
            reg_path=root/resolver.DEFAULT_REGISTRY
            reg=json.loads(reg_path.read_text())
            reg["rows"][0]["zero_ambient_child_git_blob_sha"]="0"*40
            write_json(reg_path,reg)
            with self.assertRaisesRegex(frontdoor.ZeroAmbientDFinalError,"ZERO_AMBIENT_CHILD_BLOB_MISMATCH"):
                frontdoor.run({"mode":"TEST","payload":{}},capability_id=cid,repo_root=root)


    def test_request_shape_widening_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cid,row,cert=stage(root)
            with self.assertRaisesRegex(
                frontdoor.ZeroAmbientDFinalError,
                "REQUEST_KEYS_OUTSIDE_CERTIFIED_CONTRACT",
            ):
                frontdoor.run(
                    {"mode":"TEST","payload":{},"extra":"not-certified"},
                    capability_id=cid,
                    repo_root=root,
                )

    def test_registry_request_contract_mutation_invalidates_certificate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cid,row,cert=stage(root)
            reg_path=root/resolver.DEFAULT_REGISTRY
            reg=json.loads(reg_path.read_text())
            reg["rows"][0]["allowed_request_keys"]=["mode","payload","extra"]
            write_json(reg_path,reg)
            with self.assertRaisesRegex(
                frontdoor.ZeroAmbientDFinalError,
                "CAPABILITY_CONTRACT_HASH_MISMATCH",
            ):
                frontdoor.run(
                    {"mode":"TEST","payload":{},"extra":"x"},
                    capability_id=cid,
                    repo_root=root,
                )


if __name__=="__main__":
    unittest.main(verbosity=2)
