import hashlib,json,pathlib,tempfile
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.source_contract_compiler import atomize_source,semantic_unit_id
from canonical.runtime.synthesis_certified_visible_support_policy_v2 import INPUT_SCHEMA
from canonical.runtime import p3_bound_binary_real_context_membership_v1 as m

def public():
    return {
      "schema":INPUT_SCHEMA,
      "task":{
        "claims":[
          {"claim_id":"left","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","required":False},
          {"claim_id":"right","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","required":False},
        ],
        "evidence":[
          {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,"provenance":[{"source_id":"S1","locator":"p1"}]},
          {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,"provenance":[{"source_id":"S2","locator":"p2"}]},
        ],
        "audience_profile":{
          "profile_id":"EXPLICIT",
          "constraints":{
            "output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED",
            "required_sections":[],"allowed_sections":None,"max_items":3,"max_chars":3000,
            "heading_level":2,"require_title":False,
          },
        },
      },
    }

OBJECTIVE="Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum."
SOURCE=(
 "Output whether the declared objective is true.\n"
 "Use the two declared claims.\n"
 "Use the verified evidence with provenance.\n"
 "Use the declared audience constraints.\n"
)
FIELDS=["OBJECTIVE","CLAIMS","EVIDENCE","AUDIENCE_PROFILE"]

def build(root:pathlib.Path):
    p=public()
    projections=m._projections(OBJECTIVE,p)
    hashes={k:m._sha_obj(v) for k,v in projections.items()}
    atoms=atomize_source(SOURCE,"TASK")
    reqs=[]; dispositions=[]; units=[]
    for i,(atom,field) in enumerate(zip(atoms,FIELDS)):
        rid=f"R{i}"
        sid=semantic_unit_id(atom.atom_id,0,len(atom.text))
        reqs.append({
          "id":rid,
          "source_atom_ids":[atom.atom_id],
          "source_semantic_unit_ids":[sid],
          "p3_binding":{"field":field,"value_sha256":hashes[field]},
        })
        dispositions.append({
          "atom_id":atom.atom_id,"kind":"BEHAVIOR","rationale":"load bearing",
          "requirement_ids":[rid],
        })
        units.append({
          "atom_id":atom.atom_id,"start":0,"end":len(atom.text),
          "text_sha256":hashlib.sha256(atom.text.encode()).hexdigest(),
          "kind":"BEHAVIOR",
          "semantic_fingerprint":"P3_BINDING:"+field+":"+hashes[field],
          "rationale":"independent semantic binding",
        })
    structured=m._sha_obj({"behavior_id":m.BEHAVIOR_ID,"objective":OBJECTIVE,"v2_input":p})
    receipt={
      "schema":m.AUTH_SCHEMA,"independent_verified":True,"exact_byte_bound":True,
      "conclusion":"success","context_id":"ctx","behavior_id":m.BEHAVIOR_ID,
      "source_name":"TASK","source_sha256":m._sha_text(SOURCE),
      "structured_contract_sha256":structured,
      "authoritative_source_set_complete":True,
      "no_external_load_bearing_authority":True,
    }
    rp=root/"canonical/verification/auth.json";rp.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(receipt,sort_keys=True,separators=(",",":")).encode();rp.write_bytes(raw)
    return {
      "context_id":"ctx","objective":OBJECTIVE,"v2_input":p,
      "source_name":"TASK","source_text":SOURCE,
      "dispositions":dispositions,
      "requirements":reqs,
      "extractor_units":{"A":[dict(x) for x in units],"B":[dict(x) for x in units]},
      "authority_scope_ref":{"path":"canonical/verification/auth.json","git_blob_sha":git_blob_id(raw,object_format="sha1")},
    }

def run(mut=None,stale=False):
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); x=build(root)
        if mut: mut(x,root)
        if stale: x["authority_scope_ref"]["git_blob_sha"]="0"*40
        return m.evaluate(x,repo_root=root)

def test_pass_authenticates_membership_only():
    out=run()
    assert out["pass"] is True,out
    assert out["selected_class_membership_authenticated"] is True
    assert out["real_context_semantic_scope_complete"] is True
    assert out["source_authorization_verified"] is True
    assert out["top_law_eligible"] is True
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["terminal_authority"] is False

def test_stale_authority_blob_fails():
    out=run(stale=True)
    assert out["pass"] is False
    assert out["reason"].startswith("AUTHORITY_SCOPE_RECEIPT_BINDING_INVALID")

def test_external_authority_not_closed_fails():
    def mut(x,root):
        ref=x["authority_scope_ref"]
        doc=json.loads((root/ref["path"]).read_text())
        doc["no_external_load_bearing_authority"]=False
        raw=json.dumps(doc,sort_keys=True,separators=(",",":")).encode()
        (root/ref["path"]).write_bytes(raw);ref["git_blob_sha"]=git_blob_id(raw,object_format="sha1")
    out=run(mut)
    assert out["reason"]=="AUTHORITY_SCOPE_RECEIPT_INVALID:no_external_load_bearing_authority"

def test_omitted_source_atom_fails():
    def mut(x,root): x["dispositions"].pop()
    out=run(mut)
    assert out["reason"]=="SOURCE_CONTRACT_NOT_SCOPE_COMPLETE"

def test_extractor_disagreement_fails():
    def mut(x,root):
        x["extractor_units"]["B"][0]["semantic_fingerprint"]="DIFFERENT"
    out=run(mut)
    assert out["reason"]=="SOURCE_CONTRACT_NOT_SCOPE_COMPLETE"

def test_wrong_structured_binding_hash_fails():
    def mut(x,root):
        x["requirements"][0]["p3_binding"]["value_sha256"]="sha256:"+"0"*64
    out=run(mut)
    assert out["reason"]=="P3_BINDING_VALUE_HASH_MISMATCH"

def test_semantic_fingerprint_must_bind_same_structured_field():
    def mut(x,root):
        good=x["requirements"][0]["p3_binding"]["value_sha256"]
        for ex in x["extractor_units"].values():
            ex[0]["semantic_fingerprint"]="P3_BINDING:CLAIMS:"+good
    out=run(mut)
    assert out["reason"]=="P3_SEMANTIC_FINGERPRINT_BINDING_MISMATCH"

def test_unknown_contract_field_fails():
    def mut(x,root):
        x["requirements"][0]["p3_binding"]["field"]="HIDDEN_SEMANTICS"
    out=run(mut)
    assert out["reason"]=="P3_BINDING_FIELD_OUTSIDE_BINARY_CELL"

def test_hidden_task_field_fails():
    def mut(x,root):
        x["v2_input"]["task"]["secret_requirement"]="do something else"
    out=run(mut)
    assert out["reason"]=="STRUCTURED_CONTRACT_INVALID"

def test_binary_cell_shape_still_enforced():
    def mut(x,root):
        x["v2_input"]["task"]["claims"][0]["required"]=True
        # Rebind authority receipt to the changed structured bytes so failure
        # must come from the binary cell, not stale authority metadata.
        ref=x["authority_scope_ref"];doc=json.loads((root/ref["path"]).read_text())
        doc["structured_contract_sha256"]=m._sha_obj({"behavior_id":m.BEHAVIOR_ID,"objective":x["objective"],"v2_input":x["v2_input"]})
        raw=json.dumps(doc,sort_keys=True,separators=(",",":")).encode();(root/ref["path"]).write_bytes(raw);ref["git_blob_sha"]=git_blob_id(raw,object_format="sha1")
        # Claims projection hash and source fingerprints must also follow the changed structure.
        h=m._sha_obj(x["v2_input"]["task"]["claims"])
        x["requirements"][1]["p3_binding"]["value_sha256"]=h
        for ex in x["extractor_units"].values():
            ex[1]["semantic_fingerprint"]="P3_BINDING:CLAIMS:"+h
    out=run(mut)
    assert out["reason"]=="BOUND_BINARY_EXPRESSION_CELL_REJECTED"

def test_objective_drift_without_new_authority_receipt_fails():
    def mut(x,root): x["objective"]="Determine whether 6061 aluminum is higher than AISI type 304 stainless steel."
    out=run(mut)
    assert out["reason"]=="AUTHORITY_SCOPE_RECEIPT_INVALID:structured_contract_sha256"
