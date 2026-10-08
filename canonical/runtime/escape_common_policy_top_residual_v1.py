"""Authenticated TOP common-policy residual for the live escape-policy root.

For one content-addressed Brain-owned policy adequacy condition Phi_p over a
finite load-bearing decision basis B, this module asks the strongest zero-new-
information question:

    does TOP_B entail Phi_p ?

Equivalently it compiles the residual:

    R_p = TOP_B AND NOT(Phi_p) = NOT(Phi_p)

to deterministic DIMACS by exact truth-table maxterms. If R_p is UNSAT on the
declared basis, Phi_p is valid for every valuation of B. If SAT, one exact
counterexample valuation is returned.

The result never grants U-empty, ABC, deployment, scope-completeness, or
terminal authority by itself.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes

SCHEMA="PROJECT_BRAIN_ESCAPE_COMMON_POLICY_TOP_RESIDUAL_V1"
SPEC_SCHEMA="PROJECT_BRAIN_ESCAPE_COMMON_POLICY_TOP_RESIDUAL_SPEC_V1"
ADEQUACY_SCHEMA="PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA="PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"
MAX_ATOMS=12
MAX_FORMULA_NODES=4096
TOP_LEVEL_FIELDS=frozenset({
    "schema","scope_id","decision_basis","policy_id","policy_condition","adequacy_binding"
})
BINDING_FIELDS=frozenset({
    "adequacy_certificate_path","adequacy_certificate_blob_sha",
    "independent_verification_path","independent_verification_blob_sha"
})
OPS={"TRUE","FALSE","ATOM","NOT","AND","OR","IMPLIES","XOR"}


def _fail(reason:str, **more:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "authenticated_policy_adequacy":False,
        "top_common_policy_candidate":False,
        "global_scope_complete":False,
        "u_empty_authorized":False,
        "abc_closed_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **more,
    }


def _canon(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _condition_sha(condition:Mapping[str,Any])->str:
    return hashlib.sha256(_canon(condition).encode("utf-8")).hexdigest()


def _validate_formula(formula:Any,basis:set[str],budget:list[int])->None:
    budget[0]+=1
    if budget[0]>MAX_FORMULA_NODES:
        raise ValueError("FORMULA_NODE_BUDGET_EXCEEDED")
    if not isinstance(formula,Mapping):
        raise ValueError("FORMULA_NOT_OBJECT")
    op=formula.get("op")
    if op not in OPS:
        raise ValueError("FORMULA_OP_INVALID")
    if op in {"TRUE","FALSE"}:
        if set(formula)!={"op"}:
            raise ValueError("FORMULA_FIELDS_INVALID")
        return
    if op=="ATOM":
        if set(formula)!={"op","id"}:
            raise ValueError("FORMULA_FIELDS_INVALID")
        atom=formula.get("id")
        if not isinstance(atom,str) or not atom or atom not in basis:
            raise ValueError("ATOM_OUTSIDE_DECISION_BASIS")
        return
    if op=="NOT":
        if set(formula)!={"op","arg"}:
            raise ValueError("FORMULA_FIELDS_INVALID")
        _validate_formula(formula.get("arg"),basis,budget)
        return
    if op in {"AND","OR","XOR"}:
        if set(formula)!={"op","args"}:
            raise ValueError("FORMULA_FIELDS_INVALID")
        args=formula.get("args")
        if not isinstance(args,Sequence) or isinstance(args,(str,bytes)) or len(args)<2:
            raise ValueError("FORMULA_ARGS_INVALID")
        for arg in args:
            _validate_formula(arg,basis,budget)
        return
    if op=="IMPLIES":
        if set(formula)!={"op","if","then"}:
            raise ValueError("FORMULA_FIELDS_INVALID")
        _validate_formula(formula.get("if"),basis,budget)
        _validate_formula(formula.get("then"),basis,budget)
        return
    raise ValueError("FORMULA_INVALID")


def _eval(formula:Mapping[str,Any],valuation:Mapping[str,bool])->bool:
    op=formula["op"]
    if op=="TRUE": return True
    if op=="FALSE": return False
    if op=="ATOM": return bool(valuation[formula["id"]])
    if op=="NOT": return not _eval(formula["arg"],valuation)
    if op=="AND": return all(_eval(x,valuation) for x in formula["args"])
    if op=="OR": return any(_eval(x,valuation) for x in formula["args"])
    if op=="XOR": return sum(1 for x in formula["args"] if _eval(x,valuation))==1
    if op=="IMPLIES": return (not _eval(formula["if"],valuation)) or _eval(formula["then"],valuation)
    raise AssertionError(op)


def _authenticate(
    policy_id:str,
    condition:Mapping[str,Any],
    binding:Mapping[str,Any],
    *,
    repo_root:str|Path,
)->dict[str,Any]:
    if not isinstance(binding,Mapping) or set(binding)!=BINDING_FIELDS:
        raise ValueError("ADEQUACY_BINDING_FIELDS_INVALID")
    adequacy=resolve_receipt_bytes({
        "path":binding.get("adequacy_certificate_path"),
        "git_blob_sha":binding.get("adequacy_certificate_blob_sha"),
    },repo_root=repo_root)
    verification=resolve_receipt_bytes({
        "path":binding.get("independent_verification_path"),
        "git_blob_sha":binding.get("independent_verification_blob_sha"),
    },repo_root=repo_root)
    a=adequacy["document"]
    v=verification["document"]
    csha=_condition_sha(condition)
    if a.get("schema")!=ADEQUACY_SCHEMA: raise ValueError("ADEQUACY_CERTIFICATE_SCHEMA_INVALID")
    if a.get("policy_id")!=policy_id: raise ValueError("ADEQUACY_POLICY_ID_MISMATCH")
    if a.get("policy_condition_sha256")!=csha: raise ValueError("ADEQUACY_CONDITION_MISMATCH")
    if a.get("adequacy_proved") is not True: raise ValueError("ADEQUACY_NOT_PROVED")
    if a.get("brain_owned") is not True: raise ValueError("POLICY_NOT_BRAIN_OWNED")
    if a.get("load_bearing_constraints_preserved") is not True:
        raise ValueError("LOAD_BEARING_CONSTRAINTS_NOT_PRESERVED")
    if v.get("schema")!=VERIFY_SCHEMA: raise ValueError("ADEQUACY_VERIFICATION_SCHEMA_INVALID")
    if v.get("policy_id")!=policy_id: raise ValueError("ADEQUACY_VERIFICATION_POLICY_ID_MISMATCH")
    if v.get("subject_git_blob_sha")!=adequacy["git_blob_sha"]:
        raise ValueError("ADEQUACY_VERIFICATION_SUBJECT_MISMATCH")
    if v.get("pass") is not True: raise ValueError("ADEQUACY_INDEPENDENT_VERIFICATION_NOT_PASS")
    return {
        "policy_id":policy_id,
        "condition_sha256":csha,
        "adequacy_certificate_blob_sha":adequacy["git_blob_sha"],
        "adequacy_certificate_byte_sha256":adequacy["byte_sha256"],
        "independent_verification_blob_sha":verification["git_blob_sha"],
        "independent_verification_byte_sha256":verification["byte_sha256"],
    }


def _residual_dimacs(
    basis:list[str],
    condition:Mapping[str,Any],
)->tuple[str,dict[str,bool]|None,int]:
    # CNF for NOT(condition): exclude every valuation satisfying condition.
    clauses:list[list[int]]=[]
    witness=None
    for bits in itertools.product((False,True),repeat=len(basis)):
        valuation=dict(zip(basis,bits))
        phi=_eval(condition,valuation)
        if not phi and witness is None:
            witness=valuation
        if phi:
            clause=[]
            for index,name in enumerate(basis,1):
                clause.append(-index if valuation[name] else index)
            clauses.append(clause)
    lines=[f"p cnf {len(basis)} {len(clauses)}"]
    lines.extend(" ".join(map(str,c))+" 0" for c in clauses)
    return "\n".join(lines)+"\n",witness,len(clauses)


def evaluate(
    spec_reference:Mapping[str,Any],
    *,
    repo_root:str|Path,
    expected_scope_id:str,
)->dict[str,Any]:
    try:
        if not isinstance(expected_scope_id,str) or not expected_scope_id:
            return _fail("EXPECTED_SCOPE_REQUIRED")
        bound=resolve_receipt_bytes(spec_reference,repo_root=repo_root)
        spec=bound["document"]
        if spec.get("schema")!=SPEC_SCHEMA:
            return _fail("SPEC_SCHEMA_INVALID")
        if spec.get("scope_id")!=expected_scope_id:
            return _fail("SPEC_SCOPE_MISMATCH")
        if set(spec)!=TOP_LEVEL_FIELDS:
            return _fail("SPEC_FIELDS_INVALID")
        basis=spec.get("decision_basis")
        if (
            not isinstance(basis,list) or not basis or len(basis)>MAX_ATOMS
            or len(set(basis))!=len(basis)
            or any(not isinstance(x,str) or not x for x in basis)
        ):
            return _fail("DECISION_BASIS_INVALID")
        policy_id=spec.get("policy_id")
        if not isinstance(policy_id,str) or not policy_id:
            return _fail("POLICY_ID_INVALID")
        condition=spec.get("policy_condition")
        try:
            _validate_formula(condition,set(basis),[0])
        except Exception as exc:
            return _fail("POLICY_CONDITION_INVALID",detail=str(exc)[:200])
        try:
            auth=_authenticate(
                policy_id,condition,spec.get("adequacy_binding"),
                repo_root=repo_root,
            )
        except Exception as exc:
            return _fail("ADEQUACY_AUTHENTICATION_FAILED",detail=str(exc)[:200])

        dimacs,witness,clause_count=_residual_dimacs(list(basis),condition)
        residual_sha=hashlib.sha256(dimacs.encode("utf-8")).hexdigest()
        semantic_status=(
            "SAT_ON_TOP_DECLARED_BASIS"
            if witness is not None
            else "UNSAT_ON_TOP_DECLARED_BASIS"
        )
        return {
            "schema":SCHEMA,
            "pass":True,
            "status":"PASS__AUTHENTICATED_TOP_COMMON_POLICY_RESIDUAL_COMPILED",
            "scope_id":expected_scope_id,
            "spec_git_blob_sha":bound["git_blob_sha"],
            "spec_byte_sha256":bound["byte_sha256"],
            "policy_id":policy_id,
            "decision_basis":list(basis),
            "decision_basis_count":len(basis),
            "policy_condition_sha256":auth["condition_sha256"],
            "authenticated_policy_adequacy":True,
            "adequacy_binding":auth,
            "semantic_status":semantic_status,
            "residual_model":witness,
            "dimacs":dimacs,
            "dimacs_variable_count":len(basis),
            "dimacs_clause_count":clause_count,
            "residual_sha256":residual_sha,
            "top_common_policy_candidate":witness is None,
            "independent_unsat_certificate_replay_performed":False,
            "deployment_resource_binding_verified":False,
            "basis_completeness_verified":False,
            "global_scope_complete":False,
            "u_empty_authorized":False,
            "abc_closed_authorized":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
            "boundary":(
                "AUTHENTICATED_POLICY_ADEQUACY_PLUS_TOP_ENTAILMENT_OVER_DECLARED_BASIS_ONLY;"
                "NO_BASIS_COMPLETENESS_NO_DEPLOYMENT_RESOURCE_BINDING_NO_GLOBAL_SCOPE_PROMOTION"
            ),
        }
    except Exception as exc:
        return _fail("SPEC_BINDING_OR_REPLAY_INVALID",detail=str(exc)[:200])
