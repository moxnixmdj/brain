from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from canonical.runtime import escape_progress_shared_gap_audit_v3 as v3
from canonical.runtime import escape_progress_shared_gap_audit_v4 as v4

ROOT=Path(__file__).resolve().parents[2]
M=json.loads((ROOT/"canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json").read_text())
B=json.loads((ROOT/"canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V5.json").read_text())

def _blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+bytes([0])+data).hexdigest()

def _write(root,rel,obj):
    p=root/rel; p.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
    p.write_bytes(data)
    return {"path":rel,"git_blob_sha":_blob(data)},data

def _proof(row):
    oid=row["obligation_id"]; g=row["route_group"]
    if g==v3.GAP_A:
        x={"schema":v4.ROW_PROOF_SCHEMA,"producer_id":"producer:"+oid,"obligation_id":oid,"route_group":g,"currently_acquirable":True,"finite_outcome_ids":["yes","no"],"outcome_map_complete":True,"decision_region_size_before":2,"max_nonterminal_decision_region_size_after":1,"authenticated_truth_preserving":True,"safe":True}
    else:
        x={"schema":v4.ROW_PROOF_SCHEMA,"producer_id":"producer:"+oid,"obligation_id":oid,"route_group":g,"verified_action_id":"verified:"+oid,"action_executable_now":True,"progress_measure":{"kind":"FINITE_NATURAL_RANK","current_rank":2,"minimum_rank":0,"well_founded":True},"allowed_outcomes":[{"outcome_id":"done","terminal":True,"strictly_decreases_measure":False},{"outcome_id":"progress","terminal":False,"strictly_decreases_measure":True}],"safe":True}
    for k in ("truth_authority","execution_authority","promotion_authority","acceptance_authority","terminal_authority"): x[k]=False
    x["proof_sha256"]=v3._sha(x)
    return x

def _bindings(root):
    out={}
    for row in M["rows"]:
        oid=row["obligation_id"]; proof=_proof(row)
        pref,pbytes=_write(root,"canonical/proofs/"+oid+".json",proof)
        verify={"schema":v4.ROW_VERIFY_SCHEMA,"pass":True,"independent_verified":True,"semantic_proof_verified":True,"evidence_bindings_verified":True,"obligation_id":oid,"route_group":row["route_group"],"independent_verifier_id":"verifier:"+oid,"subject":{"path":pref["path"],"git_blob_sha":pref["git_blob_sha"],"byte_sha256":hashlib.sha256(pbytes).hexdigest()},"truth_authority":False,"execution_authority":False,"promotion_authority":False,"acceptance_authority":False,"terminal_authority":False}
        vref,_=_write(root,"canonical/verification/"+oid+".json",verify)
        out[oid]={"proof":pref,"independent_verification":vref}
    return out

def test_raw_or_missing_proofs_have_zero_cc_r3_authority():
    out=v4.audit(M,B,{},repo_root=ROOT)
    assert out["pass"] is True
    assert out["cc_r3_proved"] is False
    assert out["authenticated_row_proof_count"]==0

def test_exact_independently_verified_proofs_can_reach_v3_structural_gate():
    with tempfile.TemporaryDirectory() as td:
        out=v4.audit(M,B,_bindings(Path(td)),repo_root=td)
        assert out["pass"] is True,out
        assert out["cc_r3_proved"] is True,out
        assert out["authenticated_row_proof_count"]==13

def test_same_producer_and_verifier_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); binds=_bindings(root)
        oid=M["rows"][0]["obligation_id"]
        ref=binds[oid]["independent_verification"]
        doc=json.loads((root/ref["path"]).read_text())
        doc["independent_verifier_id"]="producer:"+oid
        new,_=_write(root,ref["path"],doc)
        binds[oid]["independent_verification"]=new
        out=v4.audit(M,B,binds,repo_root=root)
        assert out["cc_r3_proved"] is False
        assert oid+":ROW_PROOF_SELF_VERIFICATION_REJECTED" in out["authentication_errors"]

def test_post_verification_proof_byte_drift_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); binds=_bindings(root)
        oid=M["rows"][0]["obligation_id"]
        p=root/binds[oid]["proof"]["path"]
        doc=json.loads(p.read_text()); doc["safe"]=False
        p.write_text(json.dumps(doc))
        out=v4.audit(M,B,binds,repo_root=root)
        assert out["cc_r3_proved"] is False
        assert any(x.startswith(oid+":ROW_PROOF_BYTE_BINDING_INVALID:") for x in out["authentication_errors"])
