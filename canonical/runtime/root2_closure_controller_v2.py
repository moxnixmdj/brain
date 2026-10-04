from __future__ import annotations
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ROOT2_CLOSURE_CONTROLLER_V2"

class Root2ClosureError(ValueError):
    pass

PRIMARY_EVIDENCE_ORDER = (
    "OWNER_PRIMARY",
    "VERSIONED_REPO_RELEASE",
    "PAPER_DATASET_REGISTRY",
    "ARCHIVE",
    "GENERAL_WEB_DISCOVERY",
    "SOCIAL_DISCOVERY_POINTER",
)

ZERO_REALITY_CLASSES = {
    "TRUTH_REPAIR",
    "FORMAL_DOMINANCE",
    "DERIVED_NODE",
    "EXISTING_RECEIPT",
    "ACCOUNT_FACT",
    "OWNER_REPLY_BINDING",
    "PROTOCOL_EQUIVALENCE",
}

FRESH_REALITY_CLASSES = {"BRAIN_SCORE", "MATCHED_EMPIRICAL_COMPARISON"}

def validate_comparator(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    required = ("predicate_id","surface","target","model","population","harness","scorer","provenance")
    seen=set(); errors=[]
    for i,row in enumerate(rows):
        missing=[k for k in required if not str(row.get(k,"")).strip()]
        if missing:
            errors.append({"index":i,"type":"MISSING_FIELDS","fields":missing})
        pid=str(row.get("predicate_id","")).strip()
        if pid in seen:
            errors.append({"index":i,"type":"DUPLICATE_PREDICATE","predicate_id":pid})
        seen.add(pid)
        if row.get("name_only_equivalence") is True:
            errors.append({"index":i,"type":"NAME_ONLY_EQUIVALENCE_FORBIDDEN","predicate_id":pid})
    return {"schema":SCHEMA,"status":"PASS" if not errors else "FAIL_CLOSED","errors":errors}

def derive_nodes(*, open_predicates: Iterable[str], derivations: Sequence[Mapping[str, Any]], proved: Iterable[str]) -> dict[str, Any]:
    open_set=set(map(str,open_predicates)); proved_set=set(map(str,proved))
    closed=[]; blocked=[]
    for d in derivations:
        target=str(d.get("target","")).strip()
        premises={str(x) for x in d.get("premises",[])}
        if target not in open_set:
            continue
        if d.get("monotone_or_implication_verified") is not True:
            blocked.append({"target":target,"missing":["VERIFIED_IMPLICATION"]}); continue
        missing=sorted(premises-proved_set)
        if missing:
            blocked.append({"target":target,"missing":missing})
        else:
            closed.append(target); proved_set.add(target)
    return {"schema":SCHEMA,"status":"DERIVATION_COMPLETE","closed":sorted(closed),"blocked":blocked}

def compile_frontier(actions: Sequence[Mapping[str, Any]], *, open_predicates: Iterable[str], zero_reality_fixed_point: bool=False) -> dict[str, Any]:
    opens=set(map(str,open_predicates))
    zero=[]; fresh=[]; waiting=[]; deleted=[]; seen=set()
    for raw in actions:
        aid=str(raw.get("id","")).strip()
        if not aid or aid in seen:
            raise Root2ClosureError("ACTION_ID_INVALID_OR_DUPLICATE")
        seen.add(aid)
        closes=sorted(opens & {str(x) for x in raw.get("closes",[])})
        if not closes:
            deleted.append({"id":aid,"reason":"NO_OPEN_TARGET"}); continue
        if raw.get("incremental_spend_usd",0) != 0:
            deleted.append({"id":aid,"reason":"NONZERO_SPEND"}); continue
        if raw.get("saturated") is True and raw.get("wake_event") in (None,""):
            deleted.append({"id":aid,"reason":"SATURATED_NO_WAKE"}); continue
        cls=str(raw.get("class","")).strip()
        row={"id":aid,"class":cls,"closes":closes}
        if cls in ZERO_REALITY_CLASSES:
            zero.append(row)
        elif cls in FRESH_REALITY_CLASSES:
            if zero_reality_fixed_point:
                fresh.append(row)
            else:
                waiting.append({**row,"reason":"WAIT_ZERO_REALITY_FIXED_POINT"})
        else:
            waiting.append({**row,"reason":"EXTERNAL_OR_UNKNOWN_CLASS"})
    return {
        "schema":SCHEMA,
        "status":"FRONTIER_COMPILED",
        "zero_reality_parallel":[x["id"] for x in zero],
        "fresh_reality_authorized":[x["id"] for x in fresh],
        "waiting":[x["id"] for x in waiting],
        "deleted":[x["id"] for x in deleted],
        "fresh_reality_authority":bool(fresh),
    }

def next_phase(frontier: Mapping[str, Any]) -> str:
    if frontier.get("zero_reality_parallel"):
        return "ZERO_REALITY_MEGABATCH"
    if frontier.get("waiting") and not frontier.get("fresh_reality_authorized"):
        return "WAIT_OR_OBSERVE_WAKE_EVENTS"
    if frontier.get("fresh_reality_authorized"):
        return "MINIMUM_REALITY_TRANSACTION"
    return "RECOMPUTE_TERMINAL_FIXED_POINT"
