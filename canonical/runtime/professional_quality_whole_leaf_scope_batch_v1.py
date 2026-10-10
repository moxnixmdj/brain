"""Batch professional whole-leaf scope closure V1.

Replays exact whole-domain equivalence for every frozen professional leaf and
checks the same universal scope-certificate semantics already used by the R10
execution exemplar. Scope only. Property truth remains separate.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as domain
from canonical.runtime import professional_quality_whole_leaf_scope_certificate_v1 as scope

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_V1"
EPOCH="2026-10-10T18:05:00+02:00"
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "domain_runtime":("canonical/runtime/professional_quality_whole_leaf_domain_equivalence_v1.py","76bf7e1a6f26ff3664ed8c355dff8a688b074159"),
 "domain_tests":("canonical/tests/test_professional_quality_whole_leaf_domain_equivalence_v1.py","38678fcf59ee3fa87b223156748a1b29660764e1"),
 "domain_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json","b6b826d1658d8a2c88ea80260ee667e86ae99394"),
 "scope_runtime":("canonical/runtime/professional_quality_whole_leaf_scope_certificate_v1.py","3c2630a63aa90f7b4667ef57f73f75b1c6b3c828"),
 "scope_tests":("canonical/tests/test_professional_quality_whole_leaf_scope_certificate_v1.py","0ab58e1a703a6c9a2af3cc1b6307287d49f6404c"),
 "universal_scope":("canonical/runtime/universal_scope_closure_compiler_v1.py","b208255789b14e44e86c82c196e06b5c41b3d039"),
}

def _blob_bytes(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _blob(path:Path)->str:
    return _blob_bytes(path.read_bytes())

def _doc_blob(doc:Mapping[str,Any])->str:
    raw=(json.dumps(doc,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode("utf-8")
    return _blob_bytes(raw)

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "leaf_count":0,"domain_equivalence_pass_count":0,"scope_complete_count":0,
      "property_truth_count":0,"quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,**extra}

def _leaf_ids(manifest:Mapping[str,Any])->list[str]:
    out=[]
    for row in manifest.get("roots") or []:
        if not isinstance(row,Mapping): continue
        for field in ("semantic_leaf","execution_leaf"):
            leaf=row.get(field)
            if isinstance(leaf,Mapping) and isinstance(leaf.get("id"),str):
                out.append(leaf["id"])
    return sorted(out)

def project_documents(manifest:Mapping[str,Any], global_domain_verify:Mapping[str,Any], *, epoch:str=EPOCH)->dict[str,Any]:
    if global_domain_verify.get("status","").startswith("PASS__") is not True:
        return _fail("GLOBAL_DOMAIN_VERIFY_NOT_PASS")
    replay=global_domain_verify.get("independent_replay")
    if not isinstance(replay,Mapping) or replay.get("real_manifest_leaf_count")!=24 or replay.get("real_manifest_passed")!=24 or replay.get("unit_tests_passed")!=8:
        return _fail("GLOBAL_DOMAIN_VERIFY_INDEPENDENT_REPLAY_INVALID")
    if (global_domain_verify.get("subject") or {}).get("runtime_git_blob_sha")!=PINS["domain_runtime"][1]:
        return _fail("GLOBAL_DOMAIN_VERIFY_RUNTIME_BINDING_STALE")
    if (global_domain_verify.get("subject") or {}).get("leaf_manifest_git_blob_sha")!=PINS["manifest"][1]:
        return _fail("GLOBAL_DOMAIN_VERIFY_MANIFEST_BINDING_STALE")

    leaf_ids=_leaf_ids(manifest)
    if len(leaf_ids)!=24 or len(set(leaf_ids))!=24:
        return _fail("MANIFEST_LEAF_SET_INVALID",observed_count=len(leaf_ids))

    rows=[]
    for leaf_id in leaf_ids:
        claim_scope=domain.build_claim_scope(manifest,leaf_id,epoch=epoch)
        dv=domain.evaluate(manifest,claim_scope)
        if dv.get("pass") is not True:
            return _fail("DOMAIN_EQUIVALENCE_REPLAY_FAILED",leaf_id=leaf_id,verdict=dv)
        claim_scope_blob=_doc_blob(claim_scope)
        claim_verify={
          "schema":scope.CLAIM_VERIFY_SCHEMA,
          "status":"PASS__BATCH_REPLAY_WHOLE_LEAF_DOMAIN_EQUIVALENCE",
          "leaf_id":leaf_id,
          "claim_id":dv["claim_id"],
          "claim_scope_git_blob_sha":claim_scope_blob,
          "whole_leaf_domain_equivalence_proved":True,
        }
        claim_verify_blob=_doc_blob(claim_verify)
        verify_path="canonical/verification/batch/"+dv["claim_id"]+".json"
        cert={
          "schema":scope.CERT_SCHEMA,
          "leaf_id":leaf_id,
          "claim_id":dv["claim_id"],
          "claim_scope_git_blob_sha":claim_scope_blob,
          "scope_certificate":{
            "id":leaf_id+"::WHOLE_LEAF_SCOPE_BATCH_V1",
            "target_scope_id":"scope://professional-quality/whole-leaf/"+dv["claim_id"],
            "claim_id":dv["claim_id"],
            "basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
            "verified":True,
            "independent":True,
            "scope_relation":"EXACT",
            "formal_completeness":True,
            "all_admissible_target_inputs_proved":True,
            "premise_set_id":"claim-verification:"+claim_verify_blob,
          },
          "evidence_refs":[{"path":verify_path,"git_blob_sha":claim_verify_blob}],
          "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
          "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
          "terminal_credit_delta":0,"incremental_spend_usd":0,
        }
        sv=scope.evaluate(
          claim_scope,claim_verify,cert,
          claim_scope_blob=claim_scope_blob,
          claim_verification_blob=claim_verify_blob,
          claim_verification_path=verify_path,
        )
        if sv.get("pass") is not True or sv.get("whole_leaf_scope_complete") is not True:
            return _fail("SCOPE_CERTIFICATE_REPLAY_FAILED",leaf_id=leaf_id,verdict=sv)
        rows.append({
          "leaf_id":leaf_id,"claim_id":dv["claim_id"],
          "claim_scope_git_blob_sha":claim_scope_blob,
          "claim_verification_git_blob_sha":claim_verify_blob,
          "scope_definition_sha256":dv["scope_definition_sha256"],
          "whole_leaf_domain_equivalence_proved":True,
          "whole_leaf_scope_complete":True,
          "leaf_property_truth_authority":False,
        })

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__24_OF_24_WHOLE_LEAF_DOMAIN_EQUIVALENCE_AND_UNIVERSAL_SCOPE_COVER_REPLAY__PROPERTY_TRUTH_SEPARATE",
      "epoch":epoch,"leaf_count":24,
      "domain_equivalence_pass_count":24,"scope_complete_count":24,
      "property_truth_count":0,
      "unique_claim_id_count":len({r["claim_id"] for r in rows}),
      "rows":rows,
      "next":"RUN_LEAF_PROPERTY_TRUTH_VERIFICATION_ON_SCOPE_COMPLETE_CLAIMS__DO_NOT_REOPEN_SCOPE_CONSTRUCTION_UNLESS_CONTENT_DRIFT_INVALIDATES_THIS_BATCH",
      "new_primitive_required":False,
      "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
      "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,
    }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root else ROOT
    docs={}
    for key,(rel,expected) in PINS.items():
        path=root/rel
        if not path.is_file() or path.is_symlink(): return _fail(key.upper()+"_MISSING")
        if _blob(path)!=expected: return _fail(key.upper()+"_BLOB_STALE")
        if key in ("manifest","domain_verify"):
            try: docs[key]=json.loads(path.read_text(encoding="utf-8"))
            except Exception: return _fail(key.upper()+"_JSON_INVALID")
    return project_documents(docs["manifest"],docs["domain_verify"])

if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
