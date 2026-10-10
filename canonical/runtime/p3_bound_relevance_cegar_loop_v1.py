"""P3 bound relevance CEGAR loop v1.

Executable composition of already-owned P3 mechanisms:
- robust policy-adequacy CEGAR,
- selected semantic TRUE/FALSE/UNKNOWN certificate,
- source-positive exact selected-policy realization.

Critical binding rule: a truth certificate may refine the CEGAR state only when
its authoritative source-derived predicate_id exactly equals the atom used by
the selected discriminator formula. Caller labels never authorize refinement.

V1 binds only ATOM(id) and NOT(ATOM(id)) discriminator formulas. Composite
formula truth requires a separate sound composition proof and remains open.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p3_robust_policy_adequacy_cegar_v1 import solve as solve_cegar
from canonical.runtime.semantic_truth_dispatch_v1 import evaluate as evaluate_truth
from canonical.runtime.p3_source_positive_selection_cell_v1 import evaluate as evaluate_selection

SCHEMA="PROJECT_BRAIN_P3_BOUND_RELEVANCE_CEGAR_LOOP_V1"
MAX_REFINEMENT_STEPS=16


def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "relevance_control_loop_authorized":False,
        "p3_contract_cell_authorized":False,
        "source_authorization_verified":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
    if detail:
        out["detail"]=detail
    return out


def _open(status:str, *, reason:str, trace:list[dict[str,Any]], **detail:Any)->dict[str,Any]:
    control={}
    for key in (
        "next_information_request",
        "next_required_edge",
        "next_information_request_candidates",
        "checker_materialization_template",
        "checker_materialization_template_candidates",
    ):
        if key in detail:
            control[key]=deepcopy(detail.pop(key))
    out={
        "schema":SCHEMA,
        "pass":False,
        "status":status,
        "reason":reason,
        "trace":trace,
        "relevance_control_loop_authorized":True,
        "p3_contract_cell_authorized":False,
        "source_authorization_verified":False,
        "db_admission_authority":False,
        "u_subtraction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **control,
    }
    if detail:
        out["detail"]=detail
    return out


def _formula_atom(formula:Any)->tuple[str,bool]|None:
    """Return (authoritative_atom_id, positive_polarity) for bindable formulas."""
    if not isinstance(formula,Mapping):
        return None
    if set(formula)=={"op","id"} and formula.get("op")=="ATOM":
        atom=formula.get("id")
        if isinstance(atom,str) and atom:
            return atom,True
        return None
    if set(formula)=={"op","arg"} and formula.get("op")=="NOT":
        arg=formula.get("arg")
        if isinstance(arg,Mapping) and set(arg)=={"op","id"} and arg.get("op")=="ATOM":
            atom=arg.get("id")
            if isinstance(atom,str) and atom:
                return atom,False
    return None


def _truth_constraint(atom_id:str, truth:bool)->dict[str,Any]:
    atom={"op":"ATOM","id":atom_id}
    return atom if truth else {"op":"NOT","arg":atom}


def evaluate(payload:Mapping[str,Any], *, repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    allowed={
        "context_id","v3_input","cegar_problem",
        "truth_payloads_by_discriminator_id","truth_payloads_by_predicate_id",
        "source_positive_selection_contracts",
        "max_refinement_steps",
    }
    extra=set(payload)-allowed
    if extra:
        return _fail("UNMODELED_LOOP_FIELDS",extra=sorted(extra))

    public=payload.get("v3_input")
    problem=payload.get("cegar_problem")
    truth_payloads=payload.get("truth_payloads_by_discriminator_id")
    predicate_truth_payloads=payload.get("truth_payloads_by_predicate_id",{})
    selection_contracts=payload.get("source_positive_selection_contracts")
    if not isinstance(public,Mapping):
        return _fail("V3_INPUT_REQUIRED")
    if not isinstance(problem,Mapping):
        return _fail("CEGAR_PROBLEM_REQUIRED")
    if not isinstance(truth_payloads,Mapping):
        return _fail("TRUTH_PAYLOADS_BY_DISCRIMINATOR_ID_REQUIRED")
    if not isinstance(predicate_truth_payloads,Mapping):
        return _fail("TRUTH_PAYLOADS_BY_PREDICATE_ID_INVALID")
    if not isinstance(selection_contracts,Mapping):
        return _fail("SOURCE_POSITIVE_SELECTION_CONTRACTS_REQUIRED")

    max_steps=payload.get("max_refinement_steps",MAX_REFINEMENT_STEPS)
    if isinstance(max_steps,bool) or not isinstance(max_steps,int) or max_steps<0 or max_steps>MAX_REFINEMENT_STEPS:
        return _fail("MAX_REFINEMENT_STEPS_INVALID")

    working=deepcopy(dict(problem))
    formal=working.get("formal_source_constraints",[])
    if not isinstance(formal,list):
        return _fail("FORMAL_SOURCE_CONSTRAINTS_MUST_BE_LIST")
    working["formal_source_constraints"]=deepcopy(formal)

    trace:list[dict[str,Any]]=[]
    used_observations:set[tuple[str,bool]] = set()
    known_truths:dict[str,bool] = {}
    root=Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]

    for step in range(max_steps+1):
        cegar=solve_cegar(working)
        trace.append({
            "step":step,
            "kind":"CEGAR",
            "status":cegar.get("status"),
            "reason":cegar.get("reason"),
            "selected_policy_id":cegar.get("selected_policy_id"),
            "selected_discriminator":cegar.get("selected_discriminator"),
        })

        if cegar.get("pass") is True and cegar.get("common_policy_certified") is True:
            policy_id=cegar.get("selected_policy_id")
            if not isinstance(policy_id,str) or not policy_id:
                return _fail("CEGAR_COMMON_POLICY_ID_INVALID",trace=trace)
            contract=selection_contracts.get(policy_id)
            if not isinstance(contract,Mapping):
                return _open(
                    "OPEN__COMMON_POLICY_SELECTION_BINDING_REQUIRED",
                    reason="COMMON_POLICY_HAS_NO_EXACT_SOURCE_POSITIVE_SELECTION_CONTRACT",
                    trace=trace,
                    selected_policy_id=policy_id,
                )
            if contract.get("selected_policy_id")!=policy_id:
                return _fail(
                    "COMMON_POLICY_SELECTION_CONTRACT_POLICY_MISMATCH",
                    selected_policy_id=policy_id,
                    contract_policy_id=contract.get("selected_policy_id"),
                    trace=trace,
                )
            realized=evaluate_selection(
                {
                    "v3_input":public,
                    "source_positive_selection_contract":contract,
                },
                repo_root=root,
            )
            trace.append({
                "step":step,
                "kind":"SOURCE_POSITIVE_SELECTION",
                "status":realized.get("status"),
                "reason":realized.get("reason"),
                "selected_policy_id":realized.get("selected_policy_id"),
            })
            if realized.get("pass") is not True:
                return _open(
                    "OPEN__COMMON_POLICY_EXACT_REALIZATION_BINDING_UNSATISFIED",
                    reason="CEGAR_COMMON_POLICY_CERTIFIED_BUT_EXACT_P3_SELECTION_REALIZATION_DID_NOT_CERTIFY",
                    trace=trace,
                    selected_policy_id=policy_id,
                    realization=realized,
                )
            if realized.get("selected_policy_id")!=policy_id:
                return _fail("REALIZED_POLICY_ID_DRIFT",trace=trace,realization=realized)
            return {
                "schema":SCHEMA,
                "pass":True,
                "status":"PASS__P3_BOUND_RELEVANCE_CEGAR_LOOP_REALIZED",
                "context_id":payload.get("context_id"),
                "selected_policy_id":policy_id,
                "selected_claim_ids":list(realized.get("selected_claim_ids") or []),
                "rendered_text":realized.get("rendered_text"),
                "render_trace":list(realized.get("render_trace") or []),
                "refinement_steps":step,
                "trace":trace,
                "relevance_control_loop_authorized":True,
                "p3_contract_cell_authorized":True,
                "source_authorization_verified":False,
                "db_admission_authority":False,
                "u_subtraction_authority":False,
                "terminal_authority":False,
                "terminal_credit_delta":0,
                "boundary":"FINITE_DECLARED_CEGAR_REGION__SOURCE_BOUND_BOOLEAN_FORMULA_TRUTH_COMPOSED_FROM_AUTHORITATIVE_ATOM_CERTIFICATES__NO_GLOBAL_P3_CLOSURE",
            }

        reason=cegar.get("reason")
        status=cegar.get("status")
        if reason=="NO_AUTHENTICATED_POLICY_ADEQUACY":
            return _open(
                "OPEN__POSITIVE_POLICY_ADEQUACY_CERTIFICATE_REQUIRED",
                reason="NO_AUTHENTICATED_POLICY_ADEQUACY",
                trace=trace,
                cegar=cegar,
            )
        if reason=="AUTHENTICATED_POLICY_COVER_INCOMPLETE":
            return _open(
                "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
                reason="AUTHENTICATED_POLICY_COVER_INCOMPLETE",
                trace=trace,
                cegar=cegar,
            )
        if status=="UNRESOLVED__NO_DECLARED_ONE_STEP_DISCRIMINATOR_CLOSES_POLICY_REGIONS":
            return _open(
                "OPEN__POLICY_CHANGING_DISCRIMINATOR_OR_STRONGER_ADEQUACY_REQUIRED",
                reason="NO_DECLARED_ONE_STEP_DISCRIMINATOR_CLOSES_POLICY_REGIONS",
                trace=trace,
                cegar=cegar,
            )
        if status!="UNRESOLVED__MINIMUM_ONE_STEP_POLICY_CHANGING_DISCRIMINATOR_SELECTED":
            return _fail("CEGAR_UNEXPECTED_FAILURE",trace=trace,cegar=cegar)

        selected=cegar.get("selected_discriminator")
        if not isinstance(selected,Mapping):
            return _fail("CEGAR_SELECTED_DISCRIMINATOR_INVALID",trace=trace)
        discriminator_id=selected.get("discriminator_id")
        formula=selected.get("formula")
        if not isinstance(discriminator_id,str) or not discriminator_id:
            return _fail("CEGAR_SELECTED_DISCRIMINATOR_ID_INVALID",trace=trace)
        if not isinstance(formula,Mapping):
            return _fail("CEGAR_SELECTED_DISCRIMINATOR_FORMULA_INVALID",trace=trace)

        new_observations=0

        def candidates_for(atom_id:str):
            raw=predicate_truth_payloads.get(atom_id)
            if raw is None:
                raw=truth_payloads.get(discriminator_id)
            if isinstance(raw,Mapping):
                return [raw]
            if isinstance(raw,list) and raw and all(isinstance(x,Mapping) for x in raw):
                return list(raw)
            return []

        def prove_atom(atom_id:str):
            nonlocal new_observations
            if atom_id in known_truths:
                return known_truths[atom_id],None
            candidates=candidates_for(atom_id)
            if not candidates:
                return None,_open(
                    "OPEN__SELECTED_PREDICATE_PROOF_PAYLOAD_REQUIRED",
                    reason="SELECTED_FORMULA_ATOM_HAS_NO_TRUTH_CERTIFICATE_PAYLOAD",
                    trace=trace,
                    selected_discriminator=selected,
                    predicate_id=atom_id,
                )
            successes=[]
            attempts=[]
            actionable_requests=[]
            actionable_edges=[]
            materialization_templates=[]
            for candidate_payload in candidates:
                truth=evaluate_truth(candidate_payload)
                request=truth.get("next_information_request")
                edge=truth.get("next_required_edge")
                template=truth.get("checker_materialization_template")
                if isinstance(template,Mapping):
                    template_copy=deepcopy(dict(template))
                    if not any(existing==template_copy for existing in materialization_templates):
                        materialization_templates.append(template_copy)
                if isinstance(request,Mapping):
                    request_copy=deepcopy(dict(request))
                    if not any(existing==request_copy for existing in actionable_requests):
                        actionable_requests.append(request_copy)
                if isinstance(edge,str) and edge and edge not in actionable_edges:
                    actionable_edges.append(edge)
                attempts.append({
                    "status":truth.get("status"),
                    "reason":truth.get("reason"),
                    "predicate_id":truth.get("predicate_id"),
                    "predicate_truth":truth.get("predicate_truth"),
                    "actionable_information_request":isinstance(request,Mapping),
                    "checker_materialization_template":isinstance(template,Mapping),
                })
                if truth.get("pass") is not True or truth.get("truthful_precommitment_observation") is not True:
                    continue
                if truth.get("predicate_id")!=atom_id:
                    return None,_fail(
                        "SELECTED_DISCRIMINATOR_TRUTH_IDENTITY_MISMATCH",
                        trace=trace,
                        selected_formula_atom_id=atom_id,
                        truth_certificate_predicate_id=truth.get("predicate_id"),
                        requested_predicate_id=truth.get("requested_predicate_id"),
                    )
                if truth.get("predicate_truth") not in {"TRUE","FALSE"}:
                    return None,_fail("SELECTED_DISCRIMINATOR_TRUTH_VALUE_INVALID",trace=trace,truth_result=truth)
                successes.append(truth)
            if not successes:
                trace.append({
                    "step":step,
                    "kind":"SELECTED_SEMANTIC_TRUTH",
                    "predicate_id":atom_id,
                    "selected_discriminator_id":discriminator_id,
                    "attempts":attempts,
                    "result":"UNKNOWN",
                    "actionable_information_request_count":len(actionable_requests),
                    "checker_materialization_template_count":len(materialization_templates),
                })
                control={}
                if len(actionable_requests)==1:
                    control["next_information_request"]=actionable_requests[0]
                    control["next_required_edge"]=(
                        actionable_edges[0]
                        if len(actionable_edges)==1
                        else "SELECTED_PREDICATE_MINIMUM_INFORMATION"
                    )
                elif len(actionable_requests)>1:
                    control["next_information_request_candidates"]=actionable_requests
                    control["next_required_edge"]=(
                        "DISAMBIGUATE_SELECTED_PREDICATE_INFORMATION_REQUEST"
                    )
                if len(materialization_templates)==1:
                    control["checker_materialization_template"]=materialization_templates[0]
                elif len(materialization_templates)>1:
                    control["checker_materialization_template_candidates"]=materialization_templates
                return None,_open(
                    "OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
                    reason="SELECTED_SEMANTIC_TRUTH_CERTIFICATE_RETURNED_UNKNOWN_OR_FAILED",
                    trace=trace,
                    selected_discriminator=selected,
                    predicate_id=atom_id,
                    attempts=attempts,
                    **control,
                )
            values={x["predicate_truth"] for x in successes}
            if len(values)!=1:
                return None,_fail(
                    "CONFLICTING_AUTHORITATIVE_TRUTH_CERTIFICATES",
                    trace=trace,predicate_id=atom_id,truth_values=sorted(values),
                )
            atom_truth=next(iter(values))=="TRUE"
            observation=(atom_id,atom_truth)
            opposite=(atom_id,not atom_truth)
            if opposite in used_observations:
                return None,_fail(
                    "CONTRADICTORY_REFINEMENT_OBSERVATION",
                    trace=trace,predicate_id=atom_id,
                )
            if observation not in used_observations:
                used_observations.add(observation)
                known_truths[atom_id]=atom_truth
                constraint=_truth_constraint(atom_id,atom_truth)
                working["formal_source_constraints"].append(constraint)
                new_observations+=1
                trace.append({
                    "step":step,
                    "kind":"REFINEMENT",
                    "authoritative_predicate_id":atom_id,
                    "predicate_truth":"TRUE" if atom_truth else "FALSE",
                    "formal_source_constraint":constraint,
                    "selected_discriminator_id":discriminator_id,
                })
            return atom_truth,None

        def prove_formula(node:Mapping[str,Any]):
            op=node.get("op")
            if op=="TRUE":
                return True,None
            if op=="FALSE":
                return False,None
            if op=="ATOM":
                atom=node.get("id")
                if not isinstance(atom,str) or not atom:
                    return None,_fail("SELECTED_FORMULA_ATOM_ID_INVALID",trace=trace)
                return prove_atom(atom)
            if op=="NOT":
                value,error=prove_formula(node.get("arg"))
                return (None,error) if error is not None else (not value,None)
            if op=="AND":
                args=node.get("args")
                if not isinstance(args,list) or len(args)<2:
                    return None,_fail("SELECTED_FORMULA_AND_ARGS_INVALID",trace=trace)
                for child in args:
                    value,error=prove_formula(child)
                    if error is not None: return None,error
                    if value is False: return False,None
                return True,None
            if op=="OR":
                args=node.get("args")
                if not isinstance(args,list) or len(args)<2:
                    return None,_fail("SELECTED_FORMULA_OR_ARGS_INVALID",trace=trace)
                for child in args:
                    value,error=prove_formula(child)
                    if error is not None: return None,error
                    if value is True: return True,None
                return False,None
            if op=="XOR":
                args=node.get("args")
                if not isinstance(args,list) or len(args)<2:
                    return None,_fail("SELECTED_FORMULA_XOR_ARGS_INVALID",trace=trace)
                values=[]
                for child in args:
                    value,error=prove_formula(child)
                    if error is not None: return None,error
                    values.append(value)
                return sum(1 for value in values if value)==1,None
            if op=="IMPLIES":
                left,error=prove_formula(node.get("if"))
                if error is not None: return None,error
                if left is False: return True,None
                right,error=prove_formula(node.get("then"))
                return (None,error) if error is not None else (bool(right),None)
            return None,_fail("SELECTED_FORMULA_OPERATOR_UNSUPPORTED",trace=trace,operator=op)

        formula_truth,error=prove_formula(formula)
        if error is not None:
            return error
        trace.append({
            "step":step,
            "kind":"SELECTED_DISCRIMINATOR_FORMULA_TRUTH",
            "selected_discriminator_id":discriminator_id,
            "formula":formula,
            "formula_truth":formula_truth,
            "new_authoritative_atom_observations":new_observations,
        })
        if new_observations==0:
            return _fail(
                "CEGAR_REFINEMENT_NO_PROGRESS_REPEAT_OBSERVATION",
                trace=trace,
                selected_discriminator_id=discriminator_id,
            )

    return _open(
        "OPEN__REFINEMENT_STEP_BOUND_EXHAUSTED",
        reason="MAX_REFINEMENT_STEPS_EXHAUSTED_WITHOUT_COMMON_POLICY",
        trace=trace,
        max_refinement_steps=max_steps,
    )


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {},repo_root=root)
