"""Finite affine grid operator inducer V1.

Infer a reusable spatial operator directly from grid demonstrations by searching
a bounded family of integer coordinate transforms. The operator is described by
a matrix + offset + output-shape rule, not by a benchmark/task label.

V1 supports exact copy-from-input spatial transforms only. It preserves every
equal-minimum exact operator and abstains when unseen prediction is ambiguous.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Mapping, Sequence

Grid = tuple[tuple[int, ...], ...]
SCHEMA = "PROJECT_BRAIN_FINITE_AFFINE_GRID_OPERATOR_INDUCER_V1"


class AffineGridOperatorError(ValueError):
    pass


def _grid(value: Sequence[Sequence[int]], label: str) -> Grid:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise AffineGridOperatorError(label.upper()+"_INVALID")
    rows=[]
    width=None
    for raw in value:
        if not isinstance(raw, Sequence) or isinstance(raw,(str,bytes)) or not raw:
            raise AffineGridOperatorError(label.upper()+"_ROW_INVALID")
        row=[]
        for v in raw:
            if not isinstance(v,int) or isinstance(v,bool) or not 0 <= v <= 9:
                raise AffineGridOperatorError(label.upper()+"_CELL_INVALID")
            row.append(v)
        if width is None: width=len(row)
        elif len(row)!=width: raise AffineGridOperatorError(label.upper()+"_NON_RECTANGULAR")
        rows.append(tuple(row))
    return tuple(rows)


def _shape(g: Grid) -> tuple[int,int]:
    return len(g),len(g[0])


def _nonzero_bbox(g:Grid)->tuple[int,int,int,int]|None:
    pts=[(r,c) for r,row in enumerate(g) for c,v in enumerate(row) if v!=0]
    if not pts:
        return None
    rs=[r for r,_ in pts]; cs=[c for _,c in pts]
    return min(rs),min(cs),max(rs),max(cs)


@dataclass(frozen=True)
class ShapeRule:
    rule_id: str

    def apply(self,g:Grid)->tuple[int,int]|None:
        h,w=_shape(g)
        if self.rule_id=="SAME": return h,w
        if self.rule_id=="SWAP": return w,h
        bbox=_nonzero_bbox(g)
        if bbox is None:
            return None
        r0,c0,r1,c1=bbox
        bh,bw=r1-r0+1,c1-c0+1
        if self.rule_id=="NONZERO_BBOX": return bh,bw
        if self.rule_id=="NONZERO_BBOX_SWAP": return bw,bh
        raise AffineGridOperatorError("SHAPE_RULE_UNSUPPORTED")


OFFSET_RULES=(
    "ZERO","H_MINUS_1","W_MINUS_1",
    "BBOX_R0","BBOX_C0","BBOX_R1","BBOX_C1",
    "CONST_-3","CONST_-2","CONST_-1","CONST_1","CONST_2","CONST_3"
)


def _offset_value(rule:str,g:Grid)->int|None:
    h,w=_shape(g)
    if rule=="ZERO": return 0
    if rule=="H_MINUS_1": return h-1
    if rule=="W_MINUS_1": return w-1
    if rule.startswith("BBOX_"):
        bbox=_nonzero_bbox(g)
        if bbox is None:
            return None
        r0,c0,r1,c1=bbox
        return {"BBOX_R0":r0,"BBOX_C0":c0,"BBOX_R1":r1,"BBOX_C1":c1}[rule]
    if rule.startswith("CONST_"): return int(rule.removeprefix("CONST_"))
    raise AffineGridOperatorError("OFFSET_RULE_UNSUPPORTED")


@dataclass(frozen=True)
class AffineOperator:
    a:int;b:int;c:int;d:int;e_rule:str;f_rule:str
    shape_rule:str

    def signature(self)->tuple[int,int,int,int,str,str,str]:
        return (self.a,self.b,self.c,self.d,self.e_rule,self.f_rule,self.shape_rule)


def _offset_description_cost(rule:str, shape_rule:str)->float:
    if rule=="ZERO":
        return 0.0
    if rule.startswith("BBOX_"):
        return 0.5 if shape_rule.startswith("NONZERO_BBOX") else 1.0
    if rule in ("H_MINUS_1","W_MINUS_1"):
        return 1.0
    if rule.startswith("CONST_"):
        return 1.5
    raise AffineGridOperatorError("OFFSET_RULE_UNSUPPORTED")


def _operator_cost(op:AffineOperator)->float:
    coeff_cost=sum(int(x!=0) for x in (op.a,op.b,op.c,op.d))
    shape_cost=0.0 if op.shape_rule=="SAME" else 0.5 if op.shape_rule=="SWAP" else 1.0
    return (
        float(coeff_cost)
        + shape_cost
        + _offset_description_cost(op.e_rule,op.shape_rule)
        + _offset_description_cost(op.f_rule,op.shape_rule)
    )


def _apply(g:Grid, op:AffineOperator)->Grid|None:
    ih,iw=_shape(g)
    shape=ShapeRule(op.shape_rule).apply(g)
    if shape is None:
        return None
    oh,ow=shape
    e=_offset_value(op.e_rule,g)
    f=_offset_value(op.f_rule,g)
    if e is None or f is None:
        return None
    out=[]
    for r in range(oh):
        row=[]
        for c in range(ow):
            sr=op.a*r+op.b*c+e
            sc=op.c*r+op.d*c+f
            if not (0<=sr<ih and 0<=sc<iw):
                return None
            row.append(g[sr][sc])
        out.append(tuple(row))
    return tuple(out)


def _offset_candidates(ih:int,iw:int,oh:int,ow:int)->range:
    # Every exact in-bounds affine map under coefficients {-1,0,1} needs no
    # offset magnitude larger than the largest involved dimension.
    m=max(ih,iw,oh,ow)
    return range(-m,m+1)


def induce(
    training_pairs: Sequence[Mapping[str,Sequence[Sequence[int]]]],
    *,
    coefficient_values: Sequence[int]=(-1,0,1),
    max_candidates:int=250000,
)->dict[str,Any]:
    try:
        if not isinstance(training_pairs,Sequence) or isinstance(training_pairs,(str,bytes)) or not training_pairs:
            raise AffineGridOperatorError("TRAINING_PAIRS_INVALID")
        pairs=[]
        for i,raw in enumerate(training_pairs):
            pairs.append((_grid(raw["input"],f"pair_{i}_input"),_grid(raw["output"],f"pair_{i}_output")))
    except (AffineGridOperatorError,KeyError,TypeError) as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc)}

    coeff=tuple(int(x) for x in coefficient_values)
    if not coeff or any(x not in (-1,0,1) for x in coeff):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"COEFFICIENT_DOMAIN_INVALID"}

    shape_rules=[]
    for rule in ("SAME","SWAP","NONZERO_BBOX","NONZERO_BBOX_SWAP"):
        if all(ShapeRule(rule).apply(i)==_shape(o) for i,o in pairs):
            shape_rules.append(rule)
    if not shape_rules:
        return {"schema":SCHEMA,"status":"NO_OPERATOR","reason":"NO_SUPPORTED_OUTPUT_SHAPE_RULE"}

    exact=[]
    evaluated=0
    for shape_rule in shape_rules:
        for a,b,c,d in product(coeff, repeat=4):
            # reject rank-zero maps and obvious coordinate collapse; V1 models
            # bijective orientation/translation style mappings.
            det=a*d-b*c
            if abs(det)!=1:
                continue
            for e_rule in OFFSET_RULES:
                for f_rule in OFFSET_RULES:
                    evaluated+=1
                    if evaluated>max_candidates:
                        return {
                            "schema":SCHEMA,"status":"SEARCH_BOUND_EXCEEDED",
                            "candidates_evaluated":evaluated,
                            "max_candidates":max_candidates,
                            "complete_within_declared_bound":False,
                            "terminal_authority":False,
                        }
                    op=AffineOperator(a,b,c,d,e_rule,f_rule,shape_rule)
                    if all(_apply(inp,op)==out for inp,out in pairs):
                        exact.append(op)

    if not exact:
        return {
            "schema":SCHEMA,"status":"NO_OPERATOR",
            "candidates_evaluated":evaluated,
            "complete_within_declared_bound":True,
            "completeness_scope":"UNIMODULAR_2D_INTEGER_AFFINE_MAPS_COEFF_NEG1_0_1_X_SYMBOLIC_CONTENT_RELATIVE_OFFSETS_X_DECLARED_SHAPE_RULES",
            "terminal_authority":False,
        }

    minimum_cost=min(_operator_cost(op) for op in exact)
    selected=[op for op in exact if _operator_cost(op)==minimum_cost]
    sigs=sorted({op.signature() for op in selected})
    return {
        "schema":SCHEMA,"status":"EXACT_OPERATORS",
        "operators":[{"a":a,"b":b,"c":c,"d":d,"e_rule":e,"f_rule":f,"shape_rule":s} for a,b,c,d,e,f,s in sigs],
        "operator_count":len(sigs),
        "minimum_description_cost":minimum_cost,
        "ambiguity_preserved":len(sigs)>1,
        "candidates_evaluated":evaluated,
        "complete_within_declared_bound":True,
        "completeness_scope":"UNIMODULAR_2D_INTEGER_AFFINE_MAPS_COEFF_NEG1_0_1_X_SYMBOLIC_CONTENT_RELATIVE_OFFSETS_X_DECLARED_SHAPE_RULES",
        "selection_rule":"MINIMUM_DESCRIPTION_COST__REUSE_ALREADY_INVOKED_CONTENT_RELATIVE_LATENTS_BEFORE_FREE_CONSTANTS",
        "terminal_authority":False,
        "promotion_authority":False,
    }


def predict(result:Mapping[str,Any], grid:Sequence[Sequence[int]])->dict[str,Any]:
    try:
        g=_grid(grid,"grid")
        outs=set()
        for raw in result["operators"]:
            op=AffineOperator(
                int(raw["a"]),int(raw["b"]),int(raw["c"]),int(raw["d"]),
                str(raw["e_rule"]),str(raw["f_rule"]),str(raw["shape_rule"])
            )
            out=_apply(g,op)
            if out is not None:
                outs.add(out)
    except (AffineGridOperatorError,KeyError,TypeError,ValueError) as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc)}
    if not outs:
        return {"schema":SCHEMA,"status":"UNDEFINED_FOR_INPUT","prediction":None}
    if len(outs)>1:
        return {"schema":SCHEMA,"status":"AMBIGUOUS_PREDICTION","prediction":None}
    out=next(iter(outs))
    return {"schema":SCHEMA,"status":"PREDICTED","prediction":[list(row) for row in out],"terminal_authority":False}
