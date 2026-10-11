"""Fresh synthetic generalization suite for grid representation invention V1.

Frozen families:
  in-scope: upper triangle, lower triangle, off-diagonal band,
            square-component selection, single-component color selection,
            row/column occupancy comparison.
  boundary probes: anti-diagonal across changing component size,
                   exact center across changing odd component size.

The solver receives only each task's training pairs. Test outputs remain evaluator-only.
"""
from __future__ import annotations
import json
from copy import deepcopy
from typing import Callable

from canonical.runtime.grid_delta_rule_inducer_v3 import induce,predict

SCHEMA="PROJECT_BRAIN_GRID_REPRESENTATION_INVENTION_FRESH_SUITE_V1"


def blank(h,w): return [[0 for _ in range(w)] for _ in range(h)]


def rect(grid,top,left,h,w,color):
    for r in range(top,top+h):
        for c in range(left,left+w):
            grid[r][c]=color
    return grid


def recolor_rect_relation(grid,top,left,h,w,target,pred:Callable[[int,int,int,int],bool]):
    out=deepcopy(grid)
    for rr in range(h):
        for cc in range(w):
            if pred(rr,cc,h,w):
                out[top+rr][left+cc]=target
    return out


def task_rect_relation(family,pred,target,train_specs,test_spec):
    train=[]
    for H,W,top,left,h,w,color in train_specs:
        g=rect(blank(H,W),top,left,h,w,color)
        train.append({"input":g,"output":recolor_rect_relation(g,top,left,h,w,target,pred)})
    H,W,top,left,h,w,color=test_spec
    g=rect(blank(H,W),top,left,h,w,color)
    return {
        "family":family,
        "expected_in_scope":True,
        "train":train,
        "test_input":g,
        "test_output":recolor_rect_relation(g,top,left,h,w,target,pred),
    }


def task_square_component_selector():
    def make(H,W,specs):
        g=blank(H,W)
        for top,left,h,w,color in specs: rect(g,top,left,h,w,color)
        out=deepcopy(g)
        for top,left,h,w,color in specs:
            if h==w:
                for r in range(top,top+h):
                    for c in range(left,left+w): out[r][c]=4
        return g,out
    train=[]
    for H,W,specs in [
        (7,10,[(1,1,2,2,1),(1,5,2,3,1)]),
        (9,12,[(2,1,3,3,2),(1,7,2,4,2)]),
    ]:
        g,o=make(H,W,specs);train.append({"input":g,"output":o})
    g,o=make(10,13,[(1,1,4,4,3),(3,8,3,2,3)])
    return {"family":"SQUARE_COMPONENT","expected_in_scope":True,"train":train,"test_input":g,"test_output":o}


def task_single_component_color_selector():
    def make(H,W,specs):
        g=blank(H,W)
        for top,left,h,w,color in specs: rect(g,top,left,h,w,color)
        totals={}
        for _t,_l,h,w,color in specs: totals[color]=totals.get(color,0)+h*w
        out=deepcopy(g)
        for top,left,h,w,color in specs:
            if h*w==totals[color]:
                for r in range(top,top+h):
                    for c in range(left,left+w): out[r][c]=9
        return g,out
    train=[]
    for H,W,specs in [
        (8,12,[(1,1,2,2,1),(1,6,1,2,3),(4,6,1,2,3)]),
        (9,13,[(1,1,2,3,5),(1,8,1,2,6),(5,8,2,1,6)]),
    ]:
        g,o=make(H,W,specs);train.append({"input":g,"output":o})
    g,o=make(10,14,[(1,1,3,2,7),(1,9,2,2,8),(6,8,1,4,8)])
    return {"family":"SINGLE_COMPONENT_COLOR","expected_in_scope":True,"train":train,"test_input":g,"test_output":o}


def cross_grid(n,vertical_cols,horizontal_row,color,target):
    g=blank(n,n)
    for c in vertical_cols:
        for r in range(n): g[r][c]=color
    for c in range(n): g[horizontal_row][c]=color
    row_nz=[sum(v!=0 for v in row) for row in g]
    col_nz=[sum(g[r][c]!=0 for r in range(n)) for c in range(n)]
    o=deepcopy(g)
    for r in range(n):
        for c in range(n):
            if row_nz[r]<col_nz[c]: o[r][c]=target
    return g,o


def task_row_col_comparison():
    train=[]
    for args in [(5,[2],2,1,6),(6,[1,4],3,3,6)]:
        g,o=cross_grid(*args);train.append({"input":g,"output":o})
    g,o=cross_grid(7,[1,3,5],2,4,6)
    return {"family":"ROW_NZ_LT_COL_NZ","expected_in_scope":True,"train":train,"test_input":g,"test_output":o}


def boundary_anti_diagonal():
    return task_rect_relation(
        "ANTI_DIAGONAL_SIZE_RELATION",
        lambda r,c,h,w:r+c==w-1,
        8,
        [(5,5,0,0,3,3,1),(7,7,1,1,4,4,2)],
        (8,8,1,2,5,5,3),
    ) | {"expected_in_scope":False}


def boundary_exact_center():
    return task_rect_relation(
        "EXACT_CENTER_SIZE_RELATION",
        lambda r,c,h,w:r==h//2 and c==w//2,
        7,
        [(5,5,0,0,3,3,1),(7,7,1,1,5,5,2)],
        (9,9,1,1,7,7,3),
    ) | {"expected_in_scope":False}


def build_suite():
    return [
        task_rect_relation(
            "UPPER_TRIANGLE",
            lambda r,c,h,w:r<c,
            2,
            [(5,5,0,0,3,3,1),(7,7,1,2,4,4,3)],
            (8,8,2,1,5,5,4),
        ),
        task_rect_relation(
            "LOWER_TRIANGLE",
            lambda r,c,h,w:r>c,
            5,
            [(5,6,1,1,3,3,2),(7,8,1,2,4,4,6)],
            (8,9,2,2,5,5,7),
        ),
        task_rect_relation(
            "OFF_DIAGONAL_BAND",
            lambda r,c,h,w:abs(r-c)==1,
            9,
            [(5,5,0,1,3,3,1),(7,7,1,1,4,4,3)],
            (8,8,1,2,5,5,4),
        ),
        task_square_component_selector(),
        task_single_component_color_selector(),
        task_row_col_comparison(),
        boundary_anti_diagonal(),
        boundary_exact_center(),
    ]


def run():
    rows=[]
    for task in build_suite():
        result=induce(task["train"])
        pred=predict(result,task["test_input"]) if result.get("status")=="VERIFIED_RULE_OPTIONS" else {"status":"NO_PREDICTION","prediction":None}
        exact=pred.get("prediction")==task["test_output"]
        rows.append({
            "family":task["family"],
            "expected_in_scope":task["expected_in_scope"],
            "induce_status":result.get("status"),
            "route":result.get("route"),
            "predict_status":pred.get("status"),
            "exact":exact,
        })
    in_scope=[x for x in rows if x["expected_in_scope"]]
    boundary=[x for x in rows if not x["expected_in_scope"]]
    return {
        "schema":SCHEMA,
        "task_count":len(rows),
        "in_scope_task_count":len(in_scope),
        "in_scope_exact":sum(x["exact"] for x in in_scope),
        "in_scope_pass":all(x["exact"] for x in in_scope),
        "boundary_task_count":len(boundary),
        "boundary_exact":sum(x["exact"] for x in boundary),
        "rows":rows,
        "terminal_authority":False,
        "promotion_authority":False,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
