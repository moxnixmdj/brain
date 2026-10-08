import hashlib, json, pathlib, tempfile
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.adequacy_basis_structural_completeness_gate_v1 import compile_contract_basis
from canonical.runtime.behavioral_contract_extension_gate_v1 import compile_extensions
from canonical.runtime.terminal_policy_basis_authenticator_v1 import evaluate

SCHEMA={"required_behavior_fields":["behavior_id","inputs","environment_state","allowed_information","required_output_or_action","success_condition","failure_condition","terminal_consequence","verification_route","dependency_boundary","scope"]}

def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"))
def condition_sha(x): return hashlib.sha256(canon(x).encode()).hexdigest()

def contract(bid="B1", extension=False):
    x={"behavior_id":bid,"source":"test","inputs":"i","environment_state":"e","allowed_information":"a","required_output_or_action":"o","success_condition":"s","failure_condition":"f","terminal_consequence":"t","verification_route":"v","dependency_boundary":"d","scope":"scope"}
    if extension:x["remaining_scope"]=["x"]
    return x

def write(root,name,obj):
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
    raw=canon(obj).encode();p.write_bytes(raw)
    return {"path":name,"git_blob_sha":git_blob_id(raw,object_format="sha1")}

def manifest(c):
    compiled=compile_contract_basis(c,SCHEMA); by={r["field"]:r["atom_id"] for r in compiled["obligations"]}
    policy_fields={"allowed_information","required_output_or_action","success_condition","failure_condition","dependency_boundary"}
    return {"schema":"PROJECT_BRAIN_POLICY_ADEQUACY_BASIS_MANIFEST_V1","behavior_id":c["behavior_id"],"candidate_policy_set_complete_certificate_id":"","admission_atom_ids":[by[x] for x in ("inputs","environment_state","scope")],"promotion_atom_ids":[by["verification_route"]],"terminal_accounting_atom_ids":[by["terminal_consequence"]],"policies":[{"policy_id":"P","basis_atom_ids":[by[x] for x in sorted(policy_fields)],"policy_condition_atom_ids":[by[x] for x in sorted(policy_fields)],"unconditional_discharges":[]}]}

def build(root, contracts):
    registry={"schema":"TEST_REGISTRY","active_contracted_residuals":contracts}
    rr=write(root,"registry.json",registry); sr=write(root,"schema.json",SCHEMA)
    rows=[]
    for c in contracts:
        m=manifest(c); mr=write(root,f"manifest-{c['behavior_id']}.json",m)
        condition={"op":"ATOM","id":"COND_"+c["behavior_id"]}
        cert={"schema":"PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1","policy_id":"P","policy_condition":condition,"policy_condition_sha256":condition_sha(condition),"adequacy_proved":True,"brain_owned":True,"load_bearing_constraints_preserved":True,"status":"TEST"}
        cr=write(root,f"cert-{c['behavior_id']}.json",cert)
        verification={"schema":"PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1","policy_id":"P","subject_git_blob_sha":cr["git_blob_sha"],"pass":True,"status":"TEST"}
        vr=write(root,f"verify-{c['behavior_id']}.json",verification)
        ext=compile_extensions(c)
        rows.append({"behavior_id":c["behavior_id"],"selected_policy_id":"P","policy_manifest_ref":mr,"policy_condition":condition,"adequacy_certificate_ref":cr,"adequacy_verification_ref":vr,"abc_extension_atom_ids":ext["abc_extension_atom_ids"]})
    return {"registry_ref":rr,"contract_schema_ref":sr,"closures":rows}

def run(mutator=None, contracts=None):
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td); p=build(root,contracts or [contract("B1"),contract("B2",True)])
        if mutator:mutator(root,p)
        return evaluate(p,repo_root=root)

def test_complete_authenticated_positive_basis_passes_without_terminal_credit():
    out=run()
    assert out["pass"] is True
    assert out["authenticated_behavior_count"]==2
    assert out["all_current_registry_behavior_edges_authenticated"] is True
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False

def test_missing_contract_closure_fails_closed():
    out=run(lambda root,p:p["closures"].pop())
    assert out["pass"] is False
    assert out["reason"]=="CONTRACT_CLOSURE_DOMAIN_MISMATCH"
    assert out["open_behavior_ids"]==["B2"]

def test_stale_adequacy_certificate_blob_fails_closed():
    def mutate(root,p):p["closures"][0]["adequacy_certificate_ref"]["git_blob_sha"]="0"*40
    out=run(mutate)
    assert out["pass"] is False
    assert "ADEQUACY_CERTIFICATE_BINDING_INVALID:B1" in out["errors"]

def test_independent_verification_subject_mismatch_fails_closed():
    def mutate(root,p):
        row=p["closures"][0]; v=json.loads((root/row["adequacy_verification_ref"]["path"]).read_text());v["subject_git_blob_sha"]="0"*40;row["adequacy_verification_ref"]=write(root,"badverify.json",v)
    out=run(mutate)
    assert out["pass"] is False
    assert "ADEQUACY_VERIFICATION_SUBJECT_MISMATCH:B1" in out["errors"]

def test_policy_condition_mismatch_fails_closed():
    def mutate(root,p):p["closures"][0]["policy_condition"]={"op":"TRUE"}
    out=run(mutate)
    assert out["pass"] is False
    assert "ADEQUACY_CONDITION_MISMATCH:B1" in out["errors"]

def test_policy_manifest_omission_fails_closed():
    def mutate(root,p):
        row=p["closures"][0]; m=json.loads((root/row["policy_manifest_ref"]["path"]).read_text());m["policies"][0]["basis_atom_ids"]=m["policies"][0]["basis_atom_ids"][:-1];m["policies"][0]["policy_condition_atom_ids"]=m["policies"][0]["policy_condition_atom_ids"][:-1]
        row["policy_manifest_ref"]=write(root,"badmanifest.json",m)
    out=run(mutate)
    assert out["pass"] is False
    assert "POLICY_MANIFEST_STRUCTURAL_INCOMPLETE:B1" in out["errors"]

def test_required_extension_membership_cannot_disappear():
    def mutate(root,p):p["closures"][1]["abc_extension_atom_ids"]=[]
    out=run(mutate)
    assert out["pass"] is False
    assert "ABC_EXTENSION_ADMISSION_INCOMPLETE:B2" in out["errors"]

def test_self_asserted_certificate_without_independent_pass_fails():
    def mutate(root,p):
        row=p["closures"][0]; v=json.loads((root/row["adequacy_verification_ref"]["path"]).read_text());v["pass"]=False;row["adequacy_verification_ref"]=write(root,"failedverify.json",v)
    out=run(mutate)
    assert out["pass"] is False
    assert "ADEQUACY_INDEPENDENT_VERIFICATION_NOT_PASS:B1" in out["errors"]
