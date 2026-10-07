"""Fail-closed dynamic extension basis gate.

Purpose:
Preserve load-bearing requirements that are not representable by the canonical
behavioral-contract base fields. Each such requirement becomes an opaque,
content-addressed extension atom. A selected policy must either include the atom
in its adequacy basis/condition or bind an independent unconditional discharge.

This gate closes structural omission only. It does not interpret the extension,
prove its truth, or prove policy adequacy.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_DYNAMIC_ADEQUACY_EXTENSION_BASIS_GATE_V1"

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _atom_id(requirement_id:str, source_unit_ids:Sequence[str])->str:
    body={"requirement_id":requirement_id,"source_unit_ids":sorted(source_unit_ids)}
    return "EXT::"+sha256(_canon(body).encode("utf-8")).hexdigest()

def _string_set(value:Any,label:str,errors:list[str])->set[str]:
    if not isinstance(value,list) or any(not isinstance(x,str) or not x for x in value):
        errors.append(label+"_INVALID")
        return set()
    if len(value)!=len(set(value)):
        errors.append(label+"_DUPLICATE")
    return set(value)

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["PAYLOAD_MAPPING_REQUIRED"],"terminal_authority":False}

    errors:list[str]=[]

    units=payload.get("operative_semantic_units")
    if not isinstance(units,Sequence) or isinstance(units,(str,bytes)):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["OPERATIVE_SEMANTIC_UNITS_INVALID"],"terminal_authority":False}

    unit_ids:set[str]=set()
    for i,row in enumerate(units):
        if not isinstance(row,Mapping):
            errors.append(f"SEMANTIC_UNIT_INVALID:{i}")
            continue
        sid=row.get("semantic_unit_id")
        if not isinstance(sid,str) or not sid or sid in unit_ids:
            errors.append(f"SEMANTIC_UNIT_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        unit_ids.add(sid)

    requirements=payload.get("requirements")
    if not isinstance(requirements,Sequence) or isinstance(requirements,(str,bytes)) or not requirements:
        errors.append("REQUIREMENTS_INVALID_OR_EMPTY")
        requirements=[]

    req_units:dict[str,set[str]]={}
    for i,row in enumerate(requirements):
        if not isinstance(row,Mapping):
            errors.append(f"REQUIREMENT_INVALID:{i}")
            continue
        rid=row.get("requirement_id")
        if not isinstance(rid,str) or not rid or rid in req_units:
            errors.append(f"REQUIREMENT_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        refs=_string_set(row.get("source_semantic_unit_ids"),f"REQUIREMENT_SOURCE_UNITS:{rid}",errors)
        for sid in sorted(refs-unit_ids):
            errors.append(f"REQUIREMENT_UNKNOWN_SEMANTIC_UNIT:{rid}:{sid}")
        req_units[rid]=refs

    mapped_units=set().union(*req_units.values()) if req_units else set()
    for sid in sorted(unit_ids-mapped_units):
        errors.append("OPERATIVE_SEMANTIC_UNIT_WITHOUT_REQUIREMENT:"+sid)

    canonical=_string_set(payload.get("canonical_requirement_ids"),"CANONICAL_REQUIREMENT_IDS",errors)
    unknown_canonical=canonical-set(req_units)
    for rid in sorted(unknown_canonical):
        errors.append("CANONICAL_REQUIREMENT_UNKNOWN:"+rid)

    extensions=set(req_units)-canonical

    declared=payload.get("extension_bindings")
    if not isinstance(declared,Sequence) or isinstance(declared,(str,bytes)):
        errors.append("EXTENSION_BINDINGS_INVALID")
        declared=[]

    ext_by_req:dict[str,Mapping[str,Any]]={}
    for i,row in enumerate(declared):
        if not isinstance(row,Mapping):
            errors.append(f"EXTENSION_BINDING_INVALID:{i}")
            continue
        rid=row.get("requirement_id")
        if not isinstance(rid,str) or rid not in extensions or rid in ext_by_req:
            errors.append(f"EXTENSION_REQUIREMENT_INVALID_OR_DUPLICATE:{i}:{rid}")
            continue
        refs=_string_set(row.get("source_semantic_unit_ids"),f"EXTENSION_SOURCE_UNITS:{rid}",errors)
        if refs!=req_units[rid]:
            errors.append(f"EXTENSION_SOURCE_UNIT_BINDING_MISMATCH:{rid}")
        expected=_atom_id(rid,sorted(refs))
        if row.get("extension_atom_id")!=expected:
            errors.append(f"EXTENSION_ATOM_ID_MISMATCH:{rid}")
        ext_by_req[rid]=row

    for rid in sorted(extensions-set(ext_by_req)):
        errors.append("LOAD_BEARING_EXTENSION_UNBOUND:"+rid)

    policies=payload.get("policies")
    if not isinstance(policies,Sequence) or isinstance(policies,(str,bytes)) or not policies:
        errors.append("POLICIES_INVALID_OR_EMPTY")
        policies=[]

    expected_atoms={rid:_atom_id(rid,sorted(req_units[rid])) for rid in extensions}
    seen_policies:set[str]=set()
    policy_rows=[]
    for i,row in enumerate(policies):
        if not isinstance(row,Mapping):
            errors.append(f"POLICY_INVALID:{i}")
            continue
        pid=row.get("policy_id")
        if not isinstance(pid,str) or not pid or pid in seen_policies:
            errors.append(f"POLICY_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        seen_policies.add(pid)
        basis=_string_set(row.get("extension_basis_atom_ids"),f"POLICY_EXTENSION_BASIS:{pid}",errors)
        condition=_string_set(row.get("extension_condition_atom_ids"),f"POLICY_EXTENSION_CONDITION:{pid}",errors)

        raw_dis=row.get("unconditional_extension_discharges",[])
        if not isinstance(raw_dis,Sequence) or isinstance(raw_dis,(str,bytes)):
            errors.append(f"POLICY_EXTENSION_DISCHARGES_INVALID:{pid}")
            raw_dis=[]
        discharged:set[str]=set()
        for j,d in enumerate(raw_dis):
            if not isinstance(d,Mapping):
                errors.append(f"POLICY_EXTENSION_DISCHARGE_INVALID:{pid}:{j}")
                continue
            atom=d.get("extension_atom_id")
            cert=d.get("certificate_id")
            if atom not in set(expected_atoms.values()):
                errors.append(f"POLICY_EXTENSION_DISCHARGE_UNKNOWN_ATOM:{pid}:{atom}")
                continue
            if not isinstance(cert,str) or not cert.strip():
                errors.append(f"POLICY_EXTENSION_DISCHARGE_CERTIFICATE_MISSING:{pid}:{atom}")
                continue
            discharged.add(atom)

        required=set(expected_atoms.values())-discharged
        for atom in sorted(required-basis):
            errors.append(f"POLICY_EXTENSION_REQUIRED_NOT_IN_BASIS:{pid}:{atom}")
        for atom in sorted(required-condition):
            errors.append(f"POLICY_EXTENSION_REQUIRED_NOT_IN_CONDITION:{pid}:{atom}")
        for atom in sorted(condition-basis):
            errors.append(f"POLICY_EXTENSION_CONDITION_OUTSIDE_BASIS:{pid}:{atom}")
        for atom in sorted((basis|condition)-set(expected_atoms.values())):
            errors.append(f"POLICY_EXTENSION_UNKNOWN_ATOM:{pid}:{atom}")
        policy_rows.append({
            "policy_id":pid,
            "extension_required_count":len(expected_atoms),
            "extension_basis_count":len(basis),
            "extension_condition_count":len(condition),
            "extension_discharge_count":len(discharged),
        })

    return {
        "schema":SCHEMA,
        "pass":not errors,
        "status":"PASS__DYNAMIC_EXTENSION_STRUCTURAL_OMISSION_CLOSED" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "operative_semantic_unit_count":len(unit_ids),
        "requirement_count":len(req_units),
        "canonical_requirement_count":len(canonical & set(req_units)),
        "extension_requirement_count":len(extensions),
        "extension_atoms":{rid:expected_atoms[rid] for rid in sorted(expected_atoms)},
        "policy_results":policy_rows,
        "structural_extension_omission_closed":not errors,
        "semantic_truth_self_verified":False,
        "certificate_truth_self_verified":False,
        "policy_adequacy_self_verified":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
