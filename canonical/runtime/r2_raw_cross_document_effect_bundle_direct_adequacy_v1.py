"""R2 direct adequacy for raw cross-document effect bundles V1."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import raw_cross_document_effect_bundle_v1 as compiler
from canonical.runtime import cross_document_source_residual_frontier_v1 as combined
from canonical.runtime import cross_document_source_residual_frontier_verify_v1 as verifier

SCHEMA="PROJECT_BRAIN_R2_RAW_CROSS_DOCUMENT_EFFECT_BUNDLE_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::RAW_CROSS_DOCUMENT_EFFECT_BUNDLE_V1"
CAPABILITY_ID="cross_document.raw_effect_bundle.certified_sentences.stdlib"
VERIFIER_CAPABILITY_ID="cross_document.source_residual_frontier.verify.stdlib"
ROOT=Path(__file__).resolve().parents[2]

GRAMMAR=re.compile(
    r"Using the raw cross-document effect bundle at "
    r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), compute and independently "
    r"verify the effective value and save it to "
    r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
    re.I,
)


def _base(status:str,passed:bool=False)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "matched":False,
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "direct_adequacy_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _safe(root:Path,rel:Any,file:bool=False)->Path:
    root=Path(root).resolve()
    p=Path(str(rel or "").strip())
    if p.is_absolute() or ".." in p.parts or not p.as_posix().startswith("canonical/"):
        raise ValueError("PATH_INVALID")
    q=(root/p).resolve()
    if q==root or root not in q.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    if file and (not q.is_file() or q.is_symlink()):
        raise ValueError("FILE_REQUIRED")
    return q


def _load(path:Path)->tuple[bytes,dict[str,Any]]:
    raw=path.read_bytes()
    try:
        obj=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("JSON_INPUT_INVALID") from exc
    if not isinstance(obj,dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return raw,obj


def _contract(goal:str)->dict[str,Any]:
    out=compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["cross_document.raw_effect_bundle"],
    )
    if out.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return out


def _open_from_compiler(result:Mapping[str,Any])->dict[str,Any]:
    did=result.get("document_id")
    regions=[
        deepcopy(dict(x))
        for x in result.get("coverage_regions") or []
        if isinstance(x,Mapping) and x.get("mode")=="OPEN_UNKNOWN_EFFECT"
    ]
    obligation={
        "kind":"CERTIFY_RAW_EFFECT_SENTENCE_OR_PROVE_QUERY_IRRELEVANCE",
        "document_id":did,
        "open_unknown_region_ids":[str(x.get("region_id")) for x in regions],
    }
    return {
        "blocking_document_ids":[did] if isinstance(did,str) and did else [],
        "blocking_unknown_regions":regions,
        "next_proof_obligations":[obligation],
    }


def _material(bundle:Mapping[str,Any])->tuple[dict[str,Any],dict[str,Any]|None,dict[str,Any]|None]:
    compiled=compiler.compile_bundle(bundle)
    if compiled.get("status")=="FAIL_CLOSED":
        raise ValueError(
            "RAW_BUNDLE_COMPILER_FAIL_CLOSED:"+str(compiled.get("reason"))
        )
    case=compiled.get("v12_case")
    if not isinstance(case,Mapping):
        return compiled,None,None
    result=combined.evaluate(case)
    if str(result.get("status") or "").startswith("FAIL_CLOSED"):
        raise ValueError(
            "COMBINED_FRONTIER_FAIL_CLOSED:"
            + str(result.get("reason") or result.get("status"))
        )
    checked=verifier.verify(case,result)
    if checked.get("verified") is not True:
        raise ValueError(
            "INDEPENDENT_COMBINED_FRONTIER_RECOMPUTATION_FAILED:"
            + ",".join(checked.get("errors") or [])
        )
    return compiled,result,checked


def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request,Mapping):
        return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
    goal=str(request.get("goal") or "").strip()
    task=str(request.get("task_id") or "").strip()
    if not goal or not task:
        return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
    m=GRAMMAR.fullmatch(goal)
    if not m:
        return {**_base("NOT_APPLICABLE"),"matched":False}
    try:
        inp,out=m.group("input"),m.group("output")
        ip=_safe(root,inp,True)
        op=_safe(root,out)
        if ip==op:
            raise ValueError("INPUT_OUTPUT_COLLISION")
        raw,bundle=_load(ip)
        compiled,result,checked=_material(bundle)

        if result is None:
            opened=_open_from_compiler(compiled)
            return {
                **_base("NOT_APPLICABLE__RAW_SOURCE_SEMANTICS_OPEN"),
                "matched":False,
                "route_id":ROUTE_ID,
                "direct_route_semantic_open":True,
                "effect_status":compiled.get("status"),
                **opened,
                "minimum_discriminator_slots":[],
                "possible_outcomes":[],
                "world_count":None,
                "query_relative_source_completeness_proved":False,
                "compiler_status":compiled.get("status"),
            }

        if result.get("pass") is not True:
            return {
                **_base("NOT_APPLICABLE__RAW_SOURCE_SEMANTICS_OPEN"),
                "matched":False,
                "route_id":ROUTE_ID,
                "direct_route_semantic_open":True,
                "effect_status":result.get("status"),
                "blocking_document_ids":deepcopy(
                    result.get("blocking_document_ids") or []
                ),
                "blocking_unknown_regions":deepcopy(
                    result.get("blocking_unknown_regions") or []
                ),
                "next_proof_obligations":deepcopy(
                    result.get("next_proof_obligations") or []
                ),
                "minimum_discriminator_slots":deepcopy(
                    result.get("minimum_discriminator_slots") or []
                ),
                "possible_outcomes":deepcopy(
                    result.get("possible_outcomes") or []
                ),
                "world_count":result.get("world_count"),
                "query_relative_source_completeness_proved":result.get(
                    "query_relative_source_completeness_proved"
                ),
                "compiler_status":compiled.get("status"),
                "preflight_verification":deepcopy(checked),
            }

        contract=_contract(goal)
        ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
        if not ids:
            raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
        gsha=sha256(goal.encode("utf-8")).hexdigest()
        bsha=sha256(raw).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "verifier_capability_id":VERIFIER_CAPABILITY_ID,
            "goal_sha256":gsha,
            "policy_id":"R2_RAW_CROSS_DOCUMENT_BUNDLE::"+gsha+"::"+bsha,
            "input_path":inp,
            "input_sha256":bsha,
            "output_path":out,
            "effective_value":deepcopy(result.get("effective_value")),
            "world_count":result.get("world_count"),
            "query_relative_source_completeness_proved":True,
            "certified_effect_sentence_count":compiled.get(
                "certified_effect_sentence_count"
            ),
            "raw_acceptance_obligation_ids":ids,
            "semantic_scope":(
                "RAW_DOCUMENT_LINES__ONLY_EXACT_CERTIFIED_EFFECT_SENTENCES_REMOVE_"
                "SOURCE_TOP__V12_REVERIFIES_EXACT_SOURCE_BYTES_AND_EFFECT_WORLDS"
            ),
            "preflight_execution_authority":False,
            "preflight_verification":deepcopy(checked),
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "reason":type(exc).__name__+":"+str(exc),
        }


def _restore(path:Path,existed:bool,raw:bytes|None)->None:
    if existed:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw or b"")
    else:
        try:path.unlink()
        except FileNotFoundError:pass


def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf
    ip=_safe(root,pf["input_path"],True)
    op=_safe(root,pf["output_path"])
    existed=op.is_file()
    old=op.read_bytes() if existed else None
    try:
        before=ip.read_bytes()
        if sha256(before).hexdigest()!=pf["input_sha256"]:
            raise RuntimeError("BUNDLE_DRIFT_BEFORE_EXECUTION")
        bundle=json.loads(before.decode("utf-8"))
        compiled,result,checked=_material(bundle)
        if (
            compiled.get("pass") is not True
            or result is None
            or result.get("pass") is not True
            or checked is None
            or checked.get("verified") is not True
        ):
            raise RuntimeError("RAW_BUNDLE_NO_LONGER_PROVES_COMMON_EFFECTIVE_VALUE")
        if ip.read_bytes()!=before:
            raise RuntimeError("BUNDLE_MUTATION_DETECTED")

        output={
            "schema":"PROJECT_BRAIN_RAW_CROSS_DOCUMENT_EFFECT_BUNDLE_RESULT_V1",
            "compiler_status":compiled.get("status"),
            "certified_effect_sentence_count":compiled.get(
                "certified_effect_sentence_count"
            ),
            "effective_value":deepcopy(result.get("effective_value")),
            "world_count":result.get("world_count"),
            "query_relative_source_completeness_proved":True,
            "combined_result":result,
            "combined_verification":checked,
        }
        op.parent.mkdir(parents=True,exist_ok=True)
        op.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        reread=json.loads(op.read_text(encoding="utf-8"))
        check2=verifier.verify(compiled["v12_case"],reread.get("combined_result") or {})
        if check2.get("verified") is not True:
            raise RuntimeError("OUTPUT_READBACK_VERIFICATION_FAILED")
        if reread.get("effective_value")!=result.get("effective_value"):
            raise RuntimeError("OUTPUT_EFFECTIVE_VALUE_MISMATCH")

        contract=_contract(str(request["goal"]))
        ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
        if ids!=pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "verifier_capability_id":VERIFIER_CAPABILITY_ID,
            "selected_policy_id":pf["policy_id"],
            "goal_sha256":pf["goal_sha256"],
            "input_path":pf["input_path"],
            "input_sha256":pf["input_sha256"],
            "output_path":pf["output_path"],
            "output_sha256":sha256(op.read_bytes()).hexdigest(),
            "effective_value":deepcopy(result["effective_value"]),
            "world_count":result["world_count"],
            "query_relative_source_completeness_proved":True,
            "certified_effect_sentence_count":compiled[
                "certified_effect_sentence_count"
            ],
            "semantic_scope":pf["semantic_scope"],
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":ids,
            "raw_acceptance_obligation_count":len(ids),
            "acceptance_receipt":deepcopy(check2),
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "source_immutability_verified":True,
            "authority_boundary":(
                "DIRECT_ROUTE_CLAIMS_ONLY_EXACT_CERTIFIED_EFFECT_SENTENCE_GRAMMAR;"
                "UNRECOGNIZED_NONWHITESPACE_SOURCE_BYTES_REMAIN_TOP"
            ),
        }
    except Exception as exc:
        _restore(op,existed,old)
        rollback=(op.is_file() and existed and op.read_bytes()==(old or b"")) if existed else not op.exists()
        return {
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "goal_sha256":pf.get("goal_sha256"),
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "rollback_complete":rollback,
            "reason":type(exc).__name__+":"+str(exc),
        }
