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

    # Quotient predicates by identical truth vectors over the complete observed
    # population. This is behavior-preserving for the current synthesis problem.
    # Within each class retain every equal-minimum-cost expression as an alias so
    # representational ambiguity is not silently erased.
    classes_by_signature={}
    for p in informative:
        signature=tuple(_predicate_truth(p,row.features) for row in population)
        classes_by_signature.setdefault(signature,[]).append(p)

    behavior_classes=[]
    for idx,(signature,members) in enumerate(sorted(classes_by_signature.items(),key=lambda kv:kv[0])):
        min_cost=min(float(p["cost"]) for p in members)
        aliases=sorted(
            [p for p in members if float(p["cost"])==min_cost],
            key=lambda p:p["predicate_id"],
        )
        behavior_classes.append({
            "class_id":f"BC_{idx:03d}",
            "signature":signature,
            "cost":min_cost,
            "aliases":aliases,
        })

    if len(behavior_classes)>MAX_PREDICATES:
        return {
            "schema":SCHEMA,
            "status":"SEARCH_BOUND_EXCEEDED",
            "reason":"BEHAVIOR_CLASS_FRONTIER_TOO_LARGE",
            "predicate_behavior_class_count":len(behavior_classes),
            "raw_informative_predicate_count":len(informative),
            "max_predicates":MAX_PREDICATES,
            "terminal_authority":False,
        }
    frontier_complete=True

    specs=[
        PredicateSpec(
            c["class_id"],
            "derived_numeric_predicate_behavior_class",
            {"path":"canonical/runtime/finite_feature_expression_inventor_v1.py","span":[0,1]},
            float(c["cost"]),
        )
        for c in behavior_classes
    ]
    class_by_id={c["class_id"]:c for c in behavior_classes}
    examples=[]
    for row_index,row in enumerate(population):
        facts=frozenset(
            c["class_id"]
            for c in behavior_classes
            if c["signature"][row_index]
        )
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
            "predicate_behavior_class_count":len(behavior_classes),
            "terminal_authority":False,
        }

    accepted=[]
    for rule in result["rules"]:
        class_ids=tuple(x["predicate_id"] for x in rule["preconditions"])
        replay=[
            all(class_by_id[cid]["signature"][row_index] for cid in class_ids)
            for row_index,_row in enumerate(population)
        ]
        labels=[row.positive for row in population]
        if replay!=labels:
            continue

        # Expand equal-minimum representational aliases. Keep a hard explicit
        # bound rather than silently dropping alternatives.
        alias_products=[class_by_id[cid]["aliases"] for cid in class_ids]
        combinations_out=[([],0)]
        for aliases in alias_products:
            next_out=[]
            for prefix,_ in combinations_out:
                for alias in aliases:
                    next_out.append((prefix+[alias],0))
                    if len(next_out)>256:
                        return {
                            "schema":SCHEMA,
                            "status":"SEARCH_BOUND_EXCEEDED",
                            "reason":"ALIAS_EXPANSION_LIMIT",
                            "limit":256,
                            "terminal_authority":False,
                        }
            combinations_out=next_out
        for aliases,_ in combinations_out:
            accepted.append({
                "predicate_ids":[p["predicate_id"] for p in aliases],
                "predicates":aliases,
                "behavior_class_ids":list(class_ids),
                "cost":rule["cost"],
            })

    if not accepted:
        return {"schema":SCHEMA,"status":"INTERNAL_REPLAY_FAILURE","terminal_authority":False}

    min_cost=min(float(x["cost"]) for x in accepted)
    best=sorted(
        [x for x in accepted if float(x["cost"])==min_cost],
        key=lambda x:(x["behavior_class_ids"],x["predicate_ids"]),
    )
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
