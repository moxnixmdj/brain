"""Conditional program-side proof kernel for Tool Discovery V4.

This is deliberately stronger than the superseded V3 refinement checker:
- exact blob binding;
- structural ordering checks over the decision procedure;
- exhaustive abstract end-to-end episodes in which identities are initially
  hidden behind authoritative discovery sources;
- truthful safe probes over every Boolean capability world in the abstraction;
- comparison against a global (not currently-visible-only) least-cost oracle.

It proves only the Brain-owned program side *conditional on* the V2 interface
contract. It does not assert that any real interface satisfies that contract.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import itertools
import json
from pathlib import Path
from typing import Any

from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_V4_CONDITIONAL_PROGRAM_PROOF_V1"
V4="canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
CONTRACT="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2.json"
EXPECTED={
    V4:"9572b25f7bdaee0f35e00cf3a1f25bc0dbd69096",
    CONTRACT:"066ae03f40769abf3ce29cbd4e8bbfcb3fdbba92",
}
REQUIRED_PROPERTIES={
"PUBLIC_INPUT_SCHEMA_IS_TOTAL_TYPED_AND_VALIDATED_BEFORE_POLICY_CALL",
"DISCOVERY_SOURCE_IDS_AND_TOOL_IDS_ARE_NONEMPTY_AND_UNIQUE_WITHIN_THEIR_CURRENT_SCOPE",
"EVERY_DISCOVERY_SOURCE_AND_TOOL_COST_USED_FOR_ORDERING_IS_FINITE_NONNEGATIVE_NUMERIC",
"ACTIVE_CONSTRAINT_USES_DECLARED_V4_PREDICATE_LANGUAGE_WITH_TYPED_OPERANDS",
"FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
"DECISION_EPOCH_EXPLICIT_AND_DISCOVERY_RECEIPTS_EPOCH_BOUND",
"DECISION_EPOCH_ADVANCES_ON_REQUIRED_CAPABILITY_CONSTRAINT_OR_DISCOVERY_SOURCE_SEMANTIC_CHANGE",
"EVERY_LISTED_DISCOVERY_SOURCE_HAS_EXPLICIT_AVAILABILITY_AND_AUTHORIZATION_STATE",
"DISCOVERY_RECEIPTS_TRUTHFUL_SOURCE_AND_DECISION_EPOCH_BOUND",
"AUTHORIZED_DISCOVERY_ACTION_RETURNS_RECEIPT_AND_RESULT_OR_RESTARTS_EPISODE",
"DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
"UNION_OF_AVAILABLE_AUTHORIZED_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
"DISCOVERY_SOURCE_COMPLETENESS_HOLDS_FOR_POLICY_REQUIRED_CAPABILITY_QUERY",
"DISCOVERED_TOOL_ID_METADATA_UNIQUE_AND_CONSISTENT_WITHIN_EPOCH",
"DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_CONSTRAINT_AND_SAFE_PROBE_PERMISSION_FIELDS",
"EVERY_REQUIRED_CAPABILITY_FOR_EACH_ADMISSIBLE_CANDIDATE_IS_ALREADY_EVIDENCED_OR_EXPLICITLY_SAFE_PROBE_DECIDABLE",
"SAFE_PROBE_PERMISSION_EXPLICIT_PER_TOOL_CAPABILITY",
"SAFE_PROBE_ACTION_FOR_EXPLICIT_PERMISSION_RETURNS_TRUTHFUL_CURRENT_TOOL_EPOCH_RECEIPT_OR_RESTARTS_EPISODE",
"SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_TOOL_EPOCH_BOUND",
"VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}

def _blob_sha(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _load(path:str)->dict[str,Any]:
    x=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise ValueError(path+":NOT_OBJECT")
    return x

def _structural_invariants()->dict[str,bool]:
    source=(ROOT/V4).read_text(encoding="utf-8")
    tree=ast.parse(source)
    fn=next(
        n for n in tree.body
        if isinstance(n,ast.FunctionDef) and n.name=="next_action"
    )
    fn_source=ast.get_source_segment(source,fn) or inspect.getsource(v4.next_action)
    q=fn_source.find("queried=_queried_sources(public)")
    srcs=fn_source.find("sources=[")
    discover_if=fn_source.find("if sources:")
    discover_ret=fn_source.find('"action":"DISCOVER"')
    tool_list=fn_source.find("tools=[")
    tool_sort=fn_source.find("tools.sort(")
    tool_loop=fn_source.find("for tool in tools:")
    probe_gate=fn_source.find("if not all(_probe_allowed(tool,cap) for cap in unknown):")
    probe_ret=fn_source.find('"action":"PROBE"')
    select_ret=fn_source.find('"action":"SELECT"')
    final_esc=fn_source.rfind('"action":"ESCALATE"')

    queried_source=inspect.getsource(v4._queried_sources)
    probe_source=inspect.getsource(v4._probe_allowed)
    return {
        "DISCOVERY_GATE_PRECEDES_TOOL_EVALUATION":
            -1 not in (q,srcs,discover_if,discover_ret,tool_list)
            and q<srcs<discover_if<discover_ret<tool_list,
        "TOOL_COST_SORT_PRECEDES_TOOL_LOOP":
            -1 not in (tool_sort,tool_loop) and tool_sort<tool_loop,
        "SAFE_PROBE_GATE_PRECEDES_PROBE":
            -1 not in (probe_gate,probe_ret) and probe_gate<probe_ret,
        "PROBE_BRANCH_PRECEDES_SELECT":
            -1 not in (probe_ret,select_ret) and probe_ret<select_ret,
        "FINAL_ESCALATE_AFTER_TOOL_LOOP":
            -1 not in (tool_loop,final_esc) and tool_loop<final_esc,
        "DISCOVERY_RECEIPTS_CURRENT_DECISION_EPOCH_ONLY":
            'int(x.get("decision_epoch",-1))==epoch' in queried_source,
        "DISCOVERY_SOURCE_REQUIRES_AUTHORIZATION":
            's.get("authorized") is True' in fn_source,
        "SAFE_PROBE_PERMISSION_EXPLICIT":
            'safe_probe_capabilities' in probe_source,
        "GENERIC_LOOP_STRUCTURE":
            all(
                token not in fn_source
                for token in ("T0","T1","S0","S1","CAP_A")
            ),
    }

def _tool(i:int, required:list[str])->dict[str,Any]:
    return {
        "tool_id":f"T{i}",
        "cost":float(i+1),
        "available":True,
        "authorized":True,
        "epoch":0,
        "safe_probe_capabilities":list(required),
    }

def _base(required:list[str],tools:list[dict[str,Any]],sources:list[dict[str,Any]])->dict[str,Any]:
    return {
        "required_capabilities":list(required),
        "constraint":None,
        "visible_tools":list(tools),
        "prior_probe_receipts":[],
        "discovery_sources":[
            {"source_id":s["source_id"],"cost":s["cost"],"available":True,"authorized":True}
            for s in sources
        ],
        "discovery_receipts":[],
        "version_events":[],
        "decision_epoch":0,
    }

def _global_best(all_tools:list[dict[str,Any]], required:list[str], oracle:dict[tuple[str,str],bool])->str|None:
    candidates=[]
    for t in all_tools:
        tid=str(t["tool_id"])
        if all(oracle[(tid,c)] for c in required):
            candidates.append(t)
    if not candidates:
        return None
    candidates.sort(key=lambda t:(float(t["cost"]),str(t["tool_id"])))
    return str(candidates[0]["tool_id"])

def _drive_episode(
    all_tools:list[dict[str,Any]],
    required:list[str],
    initial_ids:set[str],
    source_members:dict[str,set[str]],
    oracle:dict[tuple[str,str],bool],
)->dict[str,Any]:
    byid={str(t["tool_id"]):t for t in all_tools}
    sources=[
        {"source_id":sid,"cost":float(i+1)/10.0,"tool_ids":sorted(ids)}
        for i,(sid,ids) in enumerate(sorted(source_members.items()))
    ]
    visible=set(initial_ids)
    public=_base(required,[byid[x] for x in sorted(visible)],sources)
    actions=[]
    max_steps=len(sources)+len(all_tools)*len(required)+len(all_tools)+5

    for _ in range(max_steps):
        action=v4.next_action(public)
        actions.append(action)
        kind=action.get("action")
        if kind=="DISCOVER":
            sid=str(action.get("source_id") or "")
            source=next(s for s in sources if s["source_id"]==sid)
            visible.update(source["tool_ids"])
            public["visible_tools"]=[byid[x] for x in sorted(visible)]
            public["discovery_receipts"].append({
                "kind":"DISCOVERY_RESULT",
                "source_id":sid,
                "decision_epoch":public["decision_epoch"],
            })
            continue
        if kind=="PROBE":
            tid=str(action["tool_id"]); cap=str(action["capability"])
            public["prior_probe_receipts"].append({
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":tid,
                "capability":cap,
                "epoch":0,
                "supported":bool(oracle[(tid,cap)]),
            })
            continue
        if kind=="SELECT":
            return {"terminal":"SELECT","tool_id":str(action["tool_id"]),"actions":actions}
        if kind=="ESCALATE":
            return {"terminal":"ESCALATE","tool_id":None,"actions":actions}
        return {"terminal":"INVALID","tool_id":None,"actions":actions}
    return {"terminal":"BUDGET_EXHAUSTED","tool_id":None,"actions":actions}

def _exhaustive_dynamic_abstraction()->dict[str,Any]:
    required=["CAP_A","CAP_B"]
    all_tools=[_tool(i,required) for i in range(3)]
    tool_ids=[str(t["tool_id"]) for t in all_tools]
    checked=0
    failures=[]

    # Initial visibility choices. Every initially hidden identity is assigned to
    # exactly one of two authoritative sources; querying both sources therefore
    # makes the environment complete.
    for visible_bits in itertools.product((False,True), repeat=len(tool_ids)):
        initial={tid for tid,b in zip(tool_ids,visible_bits) if b}
        hidden=[tid for tid in tool_ids if tid not in initial]
        assignments=list(itertools.product((0,1), repeat=len(hidden))) or [()]
        for assignment in assignments:
            members={"S0":set(),"S1":set()}
            for tid,which in zip(hidden,assignment):
                members[f"S{which}"].add(tid)
            for caps in itertools.product((False,True), repeat=len(tool_ids)*len(required)):
                oracle={}
                k=0
                for tid in tool_ids:
                    for cap in required:
                        oracle[(tid,cap)]=bool(caps[k]); k+=1
                got=_drive_episode(all_tools,required,initial,members,oracle)
                expected=_global_best(all_tools,required,oracle)
                checked+=1
                if expected is None:
                    ok=got["terminal"]=="ESCALATE"
                else:
                    ok=got["terminal"]=="SELECT" and got["tool_id"]==expected
                if not ok:
                    failures.append({
                        "initial":sorted(initial),
                        "members":{k:sorted(v) for k,v in members.items()},
                        "oracle":{f"{k[0]}::{k[1]}":v for k,v in oracle.items()},
                        "expected":expected,
                        "got":got,
                    })
                    if len(failures)>=5:
                        return {"pass":False,"checked":checked,"failures":failures}
    return {"pass":True,"checked":checked,"failures":[]}


def _ref_get(obj:dict[str,Any],path:str):
    cur:Any=obj
    for part in str(path).split("."):
        if not isinstance(cur,dict) or part not in cur:
            return None
        cur=cur[part]
    return cur

def _ref_pred(expr:Any,tool:dict[str,Any])->bool:
    if expr in (None,{},[]):
        return True
    if not isinstance(expr,dict):
        return False
    op=str(expr.get("op") or "")
    if op=="and":
        xs=expr.get("args")
        return isinstance(xs,list) and all(_ref_pred(x,tool) for x in xs)
    if op=="or":
        xs=expr.get("args")
        return isinstance(xs,list) and bool(xs) and any(_ref_pred(x,tool) for x in xs)
    if op=="not":
        return not _ref_pred(expr.get("arg"),tool)
    value=_ref_get(tool,str(expr.get("path") or ""))
    target=expr.get("value")
    if op=="exists":
        return (value is not None) is bool(target)
    if op=="eq": return value==target
    if op=="neq": return value!=target
    if op=="in": return isinstance(target,list) and value in target
    if op=="not_in": return isinstance(target,list) and value not in target
    if op=="contains": return isinstance(value,(str,list,tuple,set)) and target in value
    if isinstance(value,bool) or isinstance(target,bool):
        return False
    if not isinstance(value,(int,float)) or not isinstance(target,(int,float)):
        return False
    if op=="lt": return value<target
    if op=="le": return value<=target
    if op=="gt": return value>target
    if op=="ge": return value>=target
    return False

def _predicate_semantics_checks()->dict[str,Any]:
    tools=[
        {"meta":{"region":"EU","risk":1,"tags":["prod","safe"],"provider":"P1"},"n":2,"flag":True},
        {"meta":{"region":"US","risk":3,"tags":["prod"],"provider":"P2"},"n":0,"flag":False},
        {"meta":{"region":"EU","risk":2,"tags":[],"provider":"P3"},"n":-1},
    ]
    atoms=[
        {"op":"eq","path":"meta.region","value":"EU"},
        {"op":"neq","path":"meta.provider","value":"P2"},
        {"op":"in","path":"meta.region","value":["EU","APAC"]},
        {"op":"not_in","path":"meta.region","value":["US"]},
        {"op":"contains","path":"meta.tags","value":"safe"},
        {"op":"exists","path":"meta.region","value":True},
        {"op":"exists","path":"missing","value":False},
        {"op":"lt","path":"meta.risk","value":2},
        {"op":"le","path":"meta.risk","value":2},
        {"op":"gt","path":"n","value":0},
        {"op":"ge","path":"n","value":0},
    ]
    exprs=list(atoms)
    exprs.extend([
        {"op":"and","args":[atoms[0],atoms[7]]},
        {"op":"or","args":[atoms[4],atoms[10]]},
        {"op":"not","arg":atoms[1]},
        {"op":"and","args":[atoms[0],{"op":"or","args":[atoms[4],atoms[8]]}]},
    ])
    checked=0
    failures=[]
    for tool in tools:
        for expr in exprs:
            got=v4._pred(expr,tool)
            expected=_ref_pred(expr,tool)
            checked+=1
            if got!=expected:
                failures.append({"tool":tool,"expr":expr,"expected":expected,"got":got})
    malformed=[
        "bad",
        {"op":"unknown","path":"n","value":1},
        {"op":"or","args":[]},
        {"op":"lt","path":"flag","value":1},
    ]
    for expr in malformed:
        got=v4._pred(expr,tools[0])
        expected=_ref_pred(expr,tools[0])
        checked+=1
        if got!=expected:
            failures.append({"tool":tools[0],"expr":expr,"expected":expected,"got":got})
    return {"pass":not failures,"checked":checked,"failures":failures}

def _route_filter_checks()->dict[str,bool]:
    required=["CAP_A"]
    cheap=_tool(0,required)
    expensive=_tool(1,required)
    cheap["meta"]={"region":"US"}
    expensive["meta"]={"region":"EU"}
    public=_base(required,[cheap,expensive],[])
    public["constraint"]={"op":"eq","path":"meta.region","value":"EU"}
    public["prior_probe_receipts"]=[
        {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True},
        {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T1","capability":"CAP_A","epoch":0,"supported":True},
    ]
    constrained=v4.next_action(public)

    cheap2=dict(cheap); cheap2["authorized"]=False
    public2=_base(required,[cheap2,expensive],[])
    public2["prior_probe_receipts"]=list(public["prior_probe_receipts"])
    unauthorized=v4.next_action(public2)
    return {
        "CONSTRAINT_FILTERS_CHEAPER_INADMISSIBLE_ROUTE":
            constrained=={"action":"SELECT","tool_id":"T1"},
        "TOOL_AUTHORIZATION_FILTERS_CHEAPER_INADMISSIBLE_ROUTE":
            unauthorized=={"action":"SELECT","tool_id":"T1"},
    }

def _epoch_and_authority_checks()->dict[str,bool]:
    required=["CAP_A"]
    t=_tool(0,required)

    stale=_base(required,[],[{"source_id":"S0","cost":0.1}])
    stale["decision_epoch"]=2
    stale["discovery_receipts"]=[{
        "kind":"DISCOVERY_RESULT","source_id":"S0","decision_epoch":1
    }]
    stale_action=v4.next_action(stale)

    unauth=_base(required,[t],[])
    unauth["prior_probe_receipts"]=[{
        "kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0",
        "capability":"CAP_A","epoch":0,"supported":True,
    }]
    unauth["discovery_sources"]=[{
        "source_id":"BAD","cost":0.0,"available":True,"authorized":False
    }]
    unauth_action=v4.next_action(unauth)

    return {
        "STALE_DISCOVERY_RECEIPT_REOPENS_DISCOVERY":
            stale_action=={"action":"DISCOVER","source_id":"S0","query":"CAP_A"},
        "UNAUTHORIZED_SOURCE_NEVER_QUERIED":
            unauth_action=={"action":"SELECT","tool_id":"T0"},
    }

def evaluate()->dict[str,Any]:
    drift=[p for p,sha in EXPECTED.items() if _blob_sha(p)!=sha]
    contract=_load(CONTRACT)
    props=contract.get("required_properties")
    property_exact=(
        isinstance(props,list)
        and all(isinstance(x,str) and x for x in props)
        and set(props)==REQUIRED_PROPERTIES
        and contract.get("instance_verified") is False
    )
    structural=_structural_invariants()
    abstraction=_exhaustive_dynamic_abstraction()
    edge=_epoch_and_authority_checks()
    predicate=_predicate_semantics_checks()
    route_filters=_route_filter_checks()
    program_pass=(
        not drift
        and property_exact
        and all(structural.values())
        and abstraction["pass"]
        and all(edge.values())
        and predicate["pass"]
        and all(route_filters.values())
    )
    return {
        "schema":SCHEMA,
        "status":(
            "PASS__V4_CONDITIONAL_PROGRAM_SIDE_PROOF__GLOBAL_ORACLE_ABSTRACTION__EXTERNAL_INTERFACE_INSTANCE_OPEN__ZERO_CREDIT"
            if program_pass else
            "FAIL_CLOSED__V4_CONDITIONAL_PROGRAM_PROOF_FAILED"
        ),
        "source_blob_drift":drift,
        "interface_contract_property_set_exact":property_exact,
        "structural_induction_obligations":structural,
        "exhaustive_dynamic_abstraction":abstraction,
        "epoch_and_authority_checks":edge,
        "predicate_language_semantics":predicate,
        "route_filter_checks":route_filters,
        "conditional_program_sound_under_v2_contract":program_pass,
        "global_oracle_is_over_complete_tool_set_not_current_visible_subset":True,
        "universal_target_proved":False,
        "external_interface_instance_verified":False,
        "minimum_missing_fact":(
            "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
            "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2"
            if program_pass else
            "V4_PROGRAM_SIDE_PROOF_NOT_CLOSED"
        ),
        "hard_nonclaims":[
            "FINITE_ABSTRACT_MODEL_CHECK_IS_PAIRED_WITH_HASH_PINNED_GENERIC_CONTROL_FLOW_INVARIANTS_NOT_USED_ALONE_AS_UNIVERSAL_PROOF",
            "NO_REAL_DISCOVERY_INTERFACE_INSTANCE_IS_ASSERTED",
            "NO_TOOL_DISCOVERY_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT",
            "NO_TERMINAL_REPLAY",
        ],
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["status"].startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
