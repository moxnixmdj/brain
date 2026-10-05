"""Fail-closed closed-world TCB reducer for composition P1/P2.

A PASS is only a sufficient-condition certificate: one implementation-bound,
independently verified state-ledger certificate plus one such certificate for
every distinct action type. No terminal/acceptance/execution credit is granted.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA="PROJECT_BRAIN_COMPOSITION_CLOSED_WORLD_TCB_REDUCER_V1"
LEDGER_TRUE=(
 "verified","independent","implementation_bound","append_only_state_root",
 "content_addressed_values","verified_initials_only_bootstrap",
 "declared_input_lookup_requires_state_root_membership",
 "declared_output_registration_mandatory","producer_receipt_bound_to_every_output",
 "rollback_restores_exact_prior_state_root","state_root_chain_content_bound",
)
ACTION_TRUE=(
 "verified","independent","implementation_bound","declared_inputs_complete",
 "declared_outputs_complete","ambient_reads_forbidden",
 "ambient_writes_forbidden_except_declared_outputs",
 "declared_file_reads_routed_through_state_root",
 "declared_file_writes_registered_in_state_root",
 "nondeterministic_external_observations_declared_as_inputs",
)

def _sha40(x:Any)->bool:
    return isinstance(x,str) and len(x)==40 and all(c in "0123456789abcdef" for c in x.lower())

def _refs(x:Any):
    out=[]
    if isinstance(x,Mapping):
        if set(x)=={"$effect_result"}:
            v=x.get("$effect_result")
            out.append(("", "") if not isinstance(v,Mapping) else
                       (str(v.get("effect") or ""),str(v.get("field") or "")))
        else:
            for v in x.values(): out.extend(_refs(v))
    elif isinstance(x,Sequence) and not isinstance(x,(str,bytes,bytearray)):
        for v in x: out.extend(_refs(v))
    return out

def _bind_errors(row:Mapping[str,Any],prefix:str):
    e=[]
    if not isinstance(row.get("implementation_path"),str) or not row["implementation_path"].startswith("canonical/"):
        e.append(prefix+":IMPLEMENTATION_PATH_INVALID")
    if not isinstance(row.get("verifier_path"),str) or not row["verifier_path"].startswith("canonical/"):
        e.append(prefix+":VERIFIER_PATH_INVALID")
    if not _sha40(row.get("implementation_git_blob_sha")):
        e.append(prefix+":IMPLEMENTATION_BLOB_INVALID")
    if not _sha40(row.get("verifier_git_blob_sha")):
        e.append(prefix+":VERIFIER_BLOB_INVALID")
    return e

def evaluate(composition:Mapping[str,Any],ledger:Mapping[str,Any],certs:Sequence[Mapping[str,Any]]):
    errors=[]
    problem=composition.get("problem") if isinstance(composition,Mapping) else None
    caps=problem.get("capabilities") if isinstance(problem,Mapping) else None
    if not isinstance(caps,list) or not caps:
        errors.append("CAPABILITIES_MISSING"); caps=[]
    if composition.get("composition_ready") is not True: errors.append("COMPOSITION_NOT_READY")
    if not isinstance(problem,Mapping) or problem.get("restrict_inherited_bound_capabilities") is not True:
        errors.append("GROUNDING_SCOPE_NOT_RESTRICTED")
    vi=composition.get("verified_initial_facts")
    re=composition.get("required_external_initials")
    if not isinstance(vi,list) or any(not isinstance(x,str) or not x for x in vi):
        errors.append("VERIFIED_INITIAL_FACTS_INVALID"); vi=[]
    if not isinstance(re,list) or any(not isinstance(x,str) or not x for x in re):
        errors.append("REQUIRED_EXTERNAL_INITIALS_INVALID"); re=[]
    if not set(re).issubset(set(vi)): errors.append("UNVERIFIED_EXTERNAL_INITIAL_PRESENT")

    if not isinstance(ledger,Mapping):
        errors.append("LEDGER_CERTIFICATE_INVALID")
    else:
        missing=[k for k in LEDGER_TRUE if ledger.get(k) is not True]
        if missing: errors.append("LEDGER_CERTIFICATE_NOT_CLOSED_WORLD:"+",".join(sorted(missing)))
        errors.extend(_bind_errors(ledger,"LEDGER"))

    by_type={}
    ids=set()
    if not isinstance(certs,Sequence) or isinstance(certs,(str,bytes,bytearray)):
        errors.append("ACTION_CERTIFICATES_INVALID"); certs=[]
    for i,c in enumerate(certs):
        if not isinstance(c,Mapping): errors.append(f"ACTION_CERTIFICATE_INVALID:{i}"); continue
        cid=str(c.get("certificate_id") or ""); typ=str(c.get("action_type") or "")
        if not cid or cid in ids: errors.append(f"ACTION_CERTIFICATE_ID_INVALID:{i}"); continue
        ids.add(cid)
        if not typ or typ in by_type: errors.append("ACTION_TYPE_CERTIFICATE_INVALID:"+typ); continue
        missing=[k for k in ACTION_TRUE if c.get(k) is not True]
        if missing: errors.append("ACTION_CERTIFICATE_NOT_CLOSED_WORLD:"+typ+":"+",".join(sorted(missing)))
        errors.extend(_bind_errors(c,"ACTION:"+typ)); by_type[typ]=c

    providers={}
    action_types=set()
    for i,cap in enumerate(caps):
        if not isinstance(cap,Mapping): errors.append(f"CAPABILITY_INVALID:{i}"); continue
        cid=str(cap.get("id") or "")
        action=cap.get("action")
        typ=str(action.get("type") or "") if isinstance(action,Mapping) else ""
        if not typ: errors.append("ACTION_TYPE_MISSING:"+cid)
        else:
            action_types.add(typ)
            if typ not in by_type: errors.append("ACTION_TYPE_CERTIFICATE_MISSING:"+typ)
        try: clause=int(cap.get("clause_index"))
        except Exception: clause=-1; errors.append("CLAUSE_INDEX_INVALID:"+cid)
        fields=cap.get("result_fields"); provides=cap.get("provides")
        if not isinstance(fields,list): fields=[]; errors.append("RESULT_FIELDS_INVALID:"+cid)
        if not isinstance(provides,list): provides=[]; errors.append("PROVIDES_INVALID:"+cid)
        for effect in provides:
            if isinstance(effect,str) and effect:
                providers.setdefault(effect,[]).append((cid,clause,set(str(x) for x in fields)))

    ref_count=0
    for cap in caps:
        if not isinstance(cap,Mapping): continue
        cid=str(cap.get("id") or "")
        req=set(str(x) for x in (cap.get("requires") or []))
        inputs=cap.get("inputs")
        if not isinstance(inputs,Mapping): errors.append("INPUTS_INVALID:"+cid); continue
        for effect,field in _refs(inputs):
            ref_count+=1
            if not effect or not field: errors.append("EFFECT_RESULT_REF_INVALID:"+cid); continue
            if effect not in req: errors.append("EFFECT_RESULT_NOT_REQUIRED:"+cid+":"+effect); continue
            rows=[r for r in providers.get(effect,[]) if r[0]!=cid]
            if not rows: errors.append("EFFECT_RESULT_PROVIDER_MISSING:"+cid+":"+effect); continue
            if len({r[1] for r in rows})!=1:
                errors.append("EFFECT_RESULT_PROVIDER_AMBIGUOUS_ACROSS_CLAUSES:"+cid+":"+effect); continue
            if any(field not in r[2] for r in rows):
                errors.append("EFFECT_RESULT_FIELD_UNDECLARED_ON_SOME_ALTERNATIVE:"+cid+":"+effect+":"+field)

    passed=not errors
    return {
      "schema":SCHEMA,
      "status":"PASS__FINITE_CLOSED_WORLD_TCB_ESTABLISHED__P1_P2_REDUCED_BY_CONSTRUCTION__ZERO_CREDIT" if passed else "FAIL_CLOSED",
      "pass":passed,"errors":sorted(set(errors)),
      "action_types":sorted(action_types),"action_type_count":len(action_types),
      "cross_step_effect_result_refs":ref_count,
      "tcb_closed":passed,
      "p1_state_preservation_reduced":passed,
      "p2_provenance_completeness_reduced":passed,
      "p3_zero_failure_aggregation_ready":passed,
      "proof_boundary":"PROOF_SIZE_DEPENDS_ON_ONE_LEDGER_CERTIFICATE_PLUS_DISTINCT_ACTION_TYPE_CERTIFICATES_NOT_TRAJECTORY_OR_COMBINATION_COUNT",
      "hard_nonclaim":"CERTIFICATES_ARE_NOT_SELF_PROVED_AND_PARENT_COMPOSITION_ACCEPTANCE_IS_NOT_GRANTED",
      "execution_authority":False,"promotion_authority":False,
      "capability_credit_delta":0,"family_credit_delta":0,"ownership_credit_delta":0,
      "new_reality_units_consumed":0,
    }
