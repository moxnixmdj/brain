from __future__ import annotations

from typing import Any, Callable, Mapping

try:
    import trusted_terminal_progress_delta_gate as progress_gate
except ImportError:
    from canonical.runtime import terminal_progress_delta_gate_v1 as progress_gate

POINTER_PATH = "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
ROOT_STATE_PATH = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
TOURNAMENT_PATH = "canonical/governance/TERMINAL_FALSIFICATION_TOURNAMENT_CURRENT_INPUT_V1.json"
CONTROL_LOOP_PATH = "canonical/governance/TERMINAL_FALSIFICATION_CONTROL_LOOP_V2.json"

RESULT_BEARING_WORK_CLASSES = {"PROGRESS_CANDIDATE", "TRUTH_REPAIR"}
ALL_WORK_CLASSES = RESULT_BEARING_WORK_CLASSES | {"FALSIFICATION_PROBE", "CONTROL_PLANE"}

class TerminalProgressEnforcementError(ValueError):
    pass

def _strings(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise TerminalProgressEnforcementError(name + "_INVALID")
    out=[x.strip() for x in value]
    if len(out)!=len(set(out)):
        raise TerminalProgressEnforcementError(name + "_DUPLICATE")
    return out

def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TerminalProgressEnforcementError(name + "_INVALID")
    return value

def compile_canonical_state(
    *,
    pointer: Mapping[str, Any],
    root_state: Mapping[str, Any],
    tournament: Mapping[str, Any],
    control_loop: Mapping[str, Any],
) -> dict[str, Any]:
    exact=_mapping(pointer.get("exact_state"),"POINTER_EXACT_STATE")
    partition=_mapping(root_state.get("current_residual_root_partition"),"ROOT_PARTITION")
    atomic=[]
    for key in ("root1_only","root2_only","root3_only","root2_and_root3"):
        atomic.extend(_strings(partition.get(key,[]),"ROOT_PARTITION_"+key.upper()))
    if len(atomic)!=len(set(atomic)):
        raise TerminalProgressEnforcementError("ATOMIC_PARTITION_OVERLAP")
    if len(atomic)!=partition.get("unresolved_total") or len(atomic)!=exact.get("unresolved_atomic"):
        raise TerminalProgressEnforcementError("ATOMIC_OPEN_COUNT_MISMATCH")

    meta=[]
    for proposal in tournament.get("proposals") or []:
        if isinstance(proposal,Mapping) and proposal.get("interface")=="BEHAVIORAL_QUOTIENT_AND_TRANSFER":
            meta.extend(_strings(proposal.get("target_obligations",[]),"META_ACTIVE_TARGETS"))
    meta.extend(_strings(pointer.get("meta_dormant_wake_only",[]),"META_DORMANT_TARGETS"))
    meta=sorted(set(meta))
    if len(meta)!=exact.get("meta_envelope_open_count"):
        raise TerminalProgressEnforcementError("META_OPEN_COUNT_MISMATCH")

    open_truth=sorted(set(atomic)|set(meta))
    if len(open_truth)!=exact.get("total_open_truth_obligations"):
        raise TerminalProgressEnforcementError("GLOBAL_OPEN_TRUTH_COUNT_MISMATCH")

    interfaces=sorted(_strings(pointer.get("current_shared_causal_interfaces",[]),"ACTIVE_INTERFACES"))

    claims={}
    for row in control_loop.get("claims") or []:
        if not isinstance(row,Mapping):
            raise TerminalProgressEnforcementError("CONTROL_LOOP_CLAIM_INVALID")
        cid=row.get("id")
        if not isinstance(cid,str) or not cid:
            raise TerminalProgressEnforcementError("CONTROL_LOOP_CLAIM_ID_INVALID")
        if cid in claims:
            raise TerminalProgressEnforcementError("CONTROL_LOOP_CLAIM_DUPLICATE")
        claims[cid]=row
    active={cid for cid,row in claims.items() if row.get("status")=="ACTIVE"}
    if not active:
        raise TerminalProgressEnforcementError("NO_ACTIVE_CONTROL_LOOP_CLAIMS")

    open_prereqs=set()
    edges={cid:[] for cid in active}
    for cid in active:
        deps=_strings(claims[cid].get("depends_on",[]),"CLAIM_DEPENDENCIES")
        for dep in deps:
            dep_row=claims.get(dep)
            if dep_row is None:
                raise TerminalProgressEnforcementError("CLAIM_DEPENDENCY_UNKNOWN:"+dep)
            if dep_row.get("status")!="PROVED":
                open_prereqs.add(dep)
                if dep in active:
                    edges[cid].append(dep)

    visiting=set()
    cache={}
    def depth(cid: str) -> int:
        if cid in cache:
            return cache[cid]
        if cid in visiting:
            raise TerminalProgressEnforcementError("ACTIVE_CLAIM_DEPENDENCY_CYCLE")
        visiting.add(cid)
        value=1+max((depth(dep) for dep in edges[cid]),default=0)
        visiting.remove(cid)
        cache[cid]=value
        return value
    max_depth=max(depth(cid) for cid in active)

    state={
        "schema": progress_gate.STATE_SCHEMA,
        "open_truth_obligations": open_truth,
        "active_causal_interfaces": interfaces,
        "open_prerequisites": sorted(open_prereqs),
        "max_open_causal_depth": max_depth,
        "open_proof_node_count": len(active),
    }
    state["state_sha256"]=progress_gate.sha256_json(state)
    return state

def evaluate_postchange(
    *,
    work_class: str,
    target_truth_obligations: list[str],
    before_documents: Mapping[str, Mapping[str, Any]],
    after_documents: Mapping[str, Mapping[str, Any]],
    evidence_record: Mapping[str, Any],
    resolve_receipt: Callable[[str], tuple[Mapping[str, Any], str]],
) -> dict[str, Any]:
    if work_class not in RESULT_BEARING_WORK_CLASSES:
        raise TerminalProgressEnforcementError("WORK_CLASS_NOT_RESULT_BEARING")
    before=compile_canonical_state(
        pointer=before_documents[POINTER_PATH],
        root_state=before_documents[ROOT_STATE_PATH],
        tournament=before_documents[TOURNAMENT_PATH],
        control_loop=before_documents[CONTROL_LOOP_PATH],
    )
    after=compile_canonical_state(
        pointer=after_documents[POINTER_PATH],
        root_state=after_documents[ROOT_STATE_PATH],
        tournament=after_documents[TOURNAMENT_PATH],
        control_loop=after_documents[CONTROL_LOOP_PATH],
    )
    targets=_strings(target_truth_obligations,"TARGET_TRUTH_OBLIGATIONS")
    record=_mapping(evidence_record,"TERMINAL_PROGRESS_EVIDENCE")
    rows_key="evidence_receipts" if work_class=="PROGRESS_CANDIDATE" else "countermodel_receipts"
    rows=record.get(rows_key)
    if not isinstance(rows,list) or not rows:
        raise TerminalProgressEnforcementError(rows_key.upper()+"_MISSING")
    for index,row in enumerate(rows):
        if not isinstance(row,Mapping):
            raise TerminalProgressEnforcementError(f"{rows_key.upper()}_INVALID:{index}")
        path=row.get("path")
        if not isinstance(path,str) or not path:
            raise TerminalProgressEnforcementError(f"{rows_key.upper()}_PATH_INVALID:{index}")
        actual_doc,actual_blob=resolve_receipt(path)
        if row.get("git_blob_sha")!=actual_blob:
            raise TerminalProgressEnforcementError(f"{rows_key.upper()}_BLOB_MISMATCH:{index}")
        for field in (
            "before_state_sha256",
            "after_state_sha256",
            "target_truth_obligations_sha256",
            "effect_kind",
        ):
            if actual_doc.get(field)!=row.get(field):
                raise TerminalProgressEnforcementError(f"{rows_key.upper()}_CONTENT_BINDING_MISMATCH:{index}:{field}")

    gate_input={
        "schema": progress_gate.INPUT_SCHEMA,
        "kind": "PROGRESS" if work_class=="PROGRESS_CANDIDATE" else "TRUTH_REPAIR",
        "before": before,
        "after": after,
        "target_truth_obligations": targets,
        rows_key: rows,
    }
    result=progress_gate.compile_result(gate_input)
    expected=(
        "ADMIT_TERMINAL_CONTRACTING_PROGRESS"
        if work_class=="PROGRESS_CANDIDATE"
        else "ADMIT_TRUTH_REPAIR_NOT_PROGRESS"
    )
    if result.get("status")!=expected:
        raise TerminalProgressEnforcementError("TERMINAL_PROGRESS_GATE_DENIED:"+str(result.get("status")))
    return {
        "status":"PASS",
        "work_class":work_class,
        "before_state_sha256":before["state_sha256"],
        "after_state_sha256":after["state_sha256"],
        "gate_result":result,
    }
