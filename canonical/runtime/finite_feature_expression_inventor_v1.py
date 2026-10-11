"""Finite feature-expression inventor V1.

Given labeled rows of bounded numeric features, enumerate a finite grammar of
derived boolean predicates and use Brain's verified G0 conjunctive-rule
synthesizer to find every minimum-cost discriminator.

This is representation invention over a declared grammar, not open-world
semantic invention. Equal-minimum ambiguity is preserved and every accepted
predicate conjunction is replayed over the complete labeled population.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import isfinite
from typing import Any, Mapping, Sequence

from canonical.runtime.g0_finite_typed_rule_synthesis import (
    PredicateSpec,
    RuleExample,
    synthesize_minimal_conjunctive_rule,
)

SCHEMA="PROJECT_BRAIN_FINITE_FEATURE_EXPRESSION_INVENTOR_V1"
MAX_FEATURES=16
MAX_ROWS=4096
MAX_PREDICATES=20


@dataclass(frozen=True)
class LabeledRow:
    row_id:str
    features:Mapping[str,int|float]
    positive:bool


def _valid_number(v:Any)->bool:
    return not isinstance(v,bool) and isinstance(v,(int,float)) and isfinite(float(v))


def _normalize(rows:Sequence[LabeledRow])->tuple[list[LabeledRow],tuple[str,...]]|dict[str,Any]:
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows or len(rows)>MAX_ROWS:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"ROWS_INVALID"}
    ids=[]; keys=None; out=[]
    for row in rows:
        if not isinstance(row,LabeledRow) or not isinstance(row.row_id,str) or not row.row_id:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"ROW_INVALID"}
        ids.append(row.row_id)
        if not isinstance(row.positive,bool) or not isinstance(row.features,Mapping) or not row.features:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"ROW_FIELDS_INVALID"}
        rk=tuple(sorted(row.features))
        if keys is None: keys=rk
        elif rk!=keys:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"FEATURE_SCHEMA_MISMATCH"}
        if any(not isinstance(k,str) or not k or not _valid_number(row.features[k]) for k in rk):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"FEATURE_VALUE_INVALID"}
        out.append(row)
    if len(ids)!=len(set(ids)):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"ROW_ID_DUPLICATE"}
    assert keys is not None
    if len(keys)>MAX_FEATURES:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"TOO_MANY_BASE_FEATURES"}
    return out,keys


def _expr_value(expr:tuple[str,...], features:Mapping[str,int|float])->float:
    op=expr[0]
    if op=="RAW": return float(features[expr[1]])
    a=float(features[expr[1]])
    b=float(features[expr[2]])
    if op=="DIFF": return a-b
    if op=="ABS_DIFF": return abs(a-b)
    if op=="SUM": return a+b
    if op=="MIN": return min(a,b)
    if op=="MAX": return max(a,b)
    if op=="EQ": return 1.0 if a==b else 0.0
    if op=="LT": return 1.0 if a<b else 0.0
    if op=="GT": return 1.0 if a>b else 0.0
    raise ValueError("EXPR_OP_UNSUPPORTED")


def _expr_id(expr:tuple[str,...])->str:
    return "__".join(expr)


def _candidate_exprs(keys:Sequence[str])->list[tuple[str,...]]:
    out=[("RAW",k) for k in keys]
    for a,b in combinations(keys,2):
        out.extend([
            ("DIFF",a,b),("DIFF",b,a),("ABS_DIFF",a,b),
            ("SUM",a,b),("MIN",a,b),("MAX",a,b),
            ("EQ",a,b),("LT",a,b),("GT",a,b),
            ("LT",b,a),("GT",b,a),
        ])
    # Deterministic complexity-first ordering.
    out.sort(key=lambda e:(0 if e[0]=="RAW" else 1,e))
    return out


def _predicate_candidates(rows:Sequence[LabeledRow], keys:Sequence[str])->list[dict[str,Any]]:
    positives=[r for r in rows if r.positive]
    negatives=[r for r in rows if not r.positive]
    candidates=[]
    seen=set()

    for expr in _candidate_exprs(keys):
        pvals=sorted({_expr_value(expr,r.features) for r in positives})
        nvals=sorted({_expr_value(expr,r.features) for r in negatives})
        if not pvals: continue

        # Equality predicates are generated only for values seen in positives.
        for value in pvals:
            pid=f"{_expr_id(expr)}__EQVAL__{value:g}"
            if pid not in seen:
                seen.add(pid)
                candidates.append({
                    "predicate_id":pid,
                    "kind":"EQ_VALUE",
                    "expr":list(expr),
                    "value":value,
                    "cost":1.0 if expr[0]=="RAW" else 2.0,
                })

        # Boolean relational expressions can be represented directly as ==1.
        if expr[0] in {"EQ","LT","GT"} and 1.0 in pvals:
            pid=f"{_expr_id(expr)}__TRUE"
            if pid not in seen:
                seen.add(pid)
                candidates.append({
                    "predicate_id":pid,
                    "kind":"TRUE",
                    "expr":list(expr),
                    "cost":2.0,
                })

        # Thresholds are induced only at observed positive/negative boundaries.
        values=sorted(set(pvals+nvals))
        for lo,hi in zip(values,values[1:]):
            threshold=(lo+hi)/2.0
            # Keep only thresholds that are nontrivial on the observed population.
            for kind in ("LE","GE"):
                truth=[(_expr_value(expr,r.features)<=threshold) if kind=="LE" else (_expr_value(expr,r.features)>=threshold) for r in rows]
                if all(truth) or not any(truth):
                    continue
                pid=f"{_expr_id(expr)}__{kind}__{threshold:g}"
                if pid in seen: continue
                seen.add(pid)
                candidates.append({
                    "predicate_id":pid,
                    "kind":kind,
                    "expr":list(expr),
                    "threshold":threshold,
                    "cost":1.5 if expr[0]=="RAW" else 2.5,
                })

    # Rank by discrimination and description cost, but do not select truth here.
    def discrimination(c):
        vals=[_predicate_truth(c,r.features) for r in rows]
        pos=sum(v for v,r in zip(vals,rows) if r.positive)
        neg=sum(v for v,r in zip(vals,rows) if not r.positive)
        return (-(pos-neg),float(c["cost"]),c["predicate_id"])
    candidates.sort(key=discrimination)
    return candidates


def _predicate_truth(p:Mapping[str,Any], features:Mapping[str,int|float])->bool:
    value=_expr_value(tuple(p["expr"]),features)
    kind=p["kind"]
    if kind=="EQ_VALUE": return value==float(p["value"])
    if kind=="TRUE": return value==1.0
    if kind=="LE": return value<=float(p["threshold"])
    if kind=="GE": return value>=float(p["threshold"])
    raise ValueError("PREDICATE_KIND_UNSUPPORTED")


def invent(rows:Sequence[LabeledRow])->dict[str,Any]:
    norm=_normalize(rows)
    if isinstance(norm,dict): return norm
    population,keys=norm
    if not any(r.positive for r in population) or not any(not r.positive for r in population):
        return {"schema":SCHEMA,"status":"UNSUPPORTED","reason":"BOTH_CLASSES_REQUIRED"}

    all_candidates=_predicate_candidates(population,keys)
    if not all_candidates:
        return {"schema":SCHEMA,"status":"NO_DERIVED_PREDICATES"}

    # Exact logical reduction for conjunctive synthesis:
    # every predicate appearing in a valid conjunction must be true in every
    # positive example. Predicates failing that condition can be removed without
    # excluding any valid conjunctive rule. Also remove predicates true in every
    # negative, because they cannot discriminate any negative.
    positives=[r for r in population if r.positive]
    negatives=[r for r in population if not r.positive]
    informative=[]
    for p in all_candidates:
        if not all(_predicate_truth(p,r.features) for r in positives):
            continue
        if all(_predicate_truth(p,r.features) for r in negatives):
            continue
        informative.append(p)

    if len(informative)>MAX_PREDICATES:
        # The proof-preserving common-positive reduction was insufficient to fit
        # the verified G0 predicate bound. Do not silently heuristic-prune a
        # possibly necessary atom: report the bound explicitly.
        return {
            "schema":SCHEMA,
            "status":"SEARCH_BOUND_EXCEEDED",
            "reason":"COMMON_POSITIVE_PREDICATE_FRONTIER_TOO_LARGE",
            "predicate_count":len(informative),
            "max_predicates":MAX_PREDICATES,
            "terminal_authority":False,
        }
    frontier_complete=True

    specs=[
        PredicateSpec(
            p["predicate_id"],
            "derived_numeric_predicate",
            {"path":"canonical/runtime/finite_feature_expression_inventor_v1.py","span":[0,1]},
            float(p["cost"]),
        )
        for p in informative
    ]
    by_id={p["predicate_id"]:p for p in informative}
    examples=[]
    for row in population:
        facts=frozenset(p["predicate_id"] for p in informative if _predicate_truth(p,row.features))
        examples.append(RuleExample(row.row_id,facts,row.positive,{"observation_id":row.row_id}))

    result=synthesize_minimal_conjunctive_rule(
        predicates=specs,
        examples=examples,
        emit={"classification":"positive"},
    )
    if result.get("status") not in ("SYNTHESIZED_UNIQUE","SYNTHESIZED_AMBIGUOUS"):
        return {
            "schema":SCHEMA,
            "status":"NO_SYNTHESIZED_DISCRIMINATOR",
            "g0_status":result.get("status"),
            "predicate_frontier_complete":frontier_complete,
            "predicate_count":len(informative),
            "terminal_authority":False,
        }

    accepted=[]
    for rule in result["rules"]:
        ids=tuple(x["predicate_id"] for x in rule["preconditions"])
        replay=[
            all(_predicate_truth(by_id[pid],row.features) for pid in ids)
            for row in population
        ]
        labels=[row.positive for row in population]
        if replay==labels:
            accepted.append({
                "predicate_ids":list(ids),
                "predicates":[by_id[pid] for pid in ids],
                "cost":rule["cost"],
            })

    if not accepted:
        return {"schema":SCHEMA,"status":"INTERNAL_REPLAY_FAILURE","terminal_authority":False}

    min_cost=min(float(x["cost"]) for x in accepted)
    best=sorted([x for x in accepted if float(x["cost"])==min_cost],key=lambda x:x["predicate_ids"])
    return {
        "schema":SCHEMA,
        "status":"INVENTED_DISCRIMINATORS",
        "base_features":list(keys),
        "discriminators":best,
        "discriminator_count":len(best),
        "minimum_cost":min_cost,
        "ambiguity_preserved":len(best)>1,
        "population_full_replay_verified":True,
        "predicate_frontier_complete":frontier_complete,
        "predicate_count":len(informative),
        "grammar_scope":"RAW_PAIRWISE_DIFF_ABS_DIFF_SUM_MIN_MAX_EQ_LT_GT_PLUS_OBSERVED_THRESHOLDS",
        "open_world_representation_invention_claimed":False,
        "terminal_authority":False,
        "promotion_authority":False,
    }


def evaluate(discriminator:Mapping[str,Any],features:Mapping[str,int|float])->bool:
    return all(_predicate_truth(p,features) for p in discriminator["predicates"])
