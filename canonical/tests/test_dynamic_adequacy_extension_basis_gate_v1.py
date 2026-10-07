from canonical.runtime.dynamic_adequacy_extension_basis_gate_v1 import evaluate

def base():
    unit="SEM-u1"
    req="R-extra"
    import hashlib,json
    body=json.dumps({"requirement_id":req,"source_unit_ids":[unit]},sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    atom="EXT::"+hashlib.sha256(body).hexdigest()
    return {
        "operative_semantic_units":[{"semantic_unit_id":unit}],
        "requirements":[{"requirement_id":"R-base","source_semantic_unit_ids":[unit]},{"requirement_id":req,"source_semantic_unit_ids":[unit]}],
        "canonical_requirement_ids":["R-base"],
        "extension_bindings":[{"requirement_id":req,"source_semantic_unit_ids":[unit],"extension_atom_id":atom}],
        "policies":[{"policy_id":"p","extension_basis_atom_ids":[atom],"extension_condition_atom_ids":[atom],"unconditional_extension_discharges":[]}],
    }

def test_extension_preserved_as_opaque_atom():
    out=evaluate(base())
    assert out["pass"] is True
    assert out["extension_requirement_count"]==1
    assert out["structural_extension_omission_closed"] is True
    assert out["semantic_truth_self_verified"] is False

def test_unbound_extension_fails_closed():
    p=base()
    p["extension_bindings"]=[]
    out=evaluate(p)
    assert out["pass"] is False
    assert "LOAD_BEARING_EXTENSION_UNBOUND:R-extra" in out["errors"]

def test_policy_cannot_ignore_extension():
    p=base()
    p["policies"][0]["extension_basis_atom_ids"]=[]
    p["policies"][0]["extension_condition_atom_ids"]=[]
    out=evaluate(p)
    assert out["pass"] is False
    assert any(x.startswith("POLICY_EXTENSION_REQUIRED_NOT_IN_BASIS:p:EXT::") for x in out["errors"])
    assert any(x.startswith("POLICY_EXTENSION_REQUIRED_NOT_IN_CONDITION:p:EXT::") for x in out["errors"])

def test_independent_discharge_can_replace_contingent_extension_atom():
    p=base()
    atom=p["extension_bindings"][0]["extension_atom_id"]
    p["policies"][0]["extension_basis_atom_ids"]=[]
    p["policies"][0]["extension_condition_atom_ids"]=[]
    p["policies"][0]["unconditional_extension_discharges"]=[{"extension_atom_id":atom,"certificate_id":"cert-1"}]
    out=evaluate(p)
    assert out["pass"] is True

def test_operative_unit_without_requirement_fails_closed():
    p=base()
    p["operative_semantic_units"].append({"semantic_unit_id":"SEM-orphan"})
    out=evaluate(p)
    assert out["pass"] is False
    assert "OPERATIVE_SEMANTIC_UNIT_WITHOUT_REQUIREMENT:SEM-orphan" in out["errors"]

def test_tampered_extension_atom_id_fails_closed():
    p=base()
    p["extension_bindings"][0]["extension_atom_id"]="EXT::bad"
    out=evaluate(p)
    assert out["pass"] is False
    assert "EXTENSION_ATOM_ID_MISMATCH:R-extra" in out["errors"]
