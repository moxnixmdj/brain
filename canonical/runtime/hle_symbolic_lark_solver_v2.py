#!/usr/bin/env python3
"""Brain-owned HLE symbolic solver using local SymPy/Lark as a code tool.

No external reasoning model, web access, or gold is used. The solver is bounded
and fail-closed: it parses only explicit LaTeX math spans, evaluates closed
expressions, and solves small explicit equation systems when the requested
symbol/expression can be identified structurally.
"""
from __future__ import annotations

import hashlib
import re
import signal
import threading
from contextlib import contextmanager
from typing import Any

import sympy as sp
from sympy.parsing.latex import parse_latex

SCHEMA="PROJECT_BRAIN_HLE_SYMBOLIC_LARK_SOLVER_V2"
_INLINE=[
    re.compile(r'\\\((.*?)\\\)',re.S),
    re.compile(r'\\\[(.*?)\\\]',re.S),
    re.compile(r'(?<!\\)\$(?!\$)(.*?)(?<!\\)\$',re.S),
]
_ASK=re.compile(r'\b(?:compute|calculate|evaluate|find|determine|solve|what is|what are|value of|values of)\b',re.I)
_POS=re.compile(r'\b(?:positive|greater than zero|largest|greatest|maximum|maximal)\b',re.I)
_NEG=re.compile(r'\b(?:negative|less than zero|smallest|least|minimum|minimal)\b',re.I)
_NONNEG=re.compile(r'\bnonnegative\b',re.I)

class Timeout(RuntimeError):pass

@contextmanager
def _deadline(seconds:int=2):
    if not hasattr(signal,'SIGALRM') or threading.current_thread() is not threading.main_thread():
        yield;return
    def handler(signum,frame):raise Timeout('SYMBOLIC_TIMEOUT')
    old=signal.signal(signal.SIGALRM,handler)
    signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old)

def _segments(q:str)->list[tuple[int,int,str]]:
    out=[]
    for r in _INLINE:
        for m in r.finditer(q):
            raw=m.group(1).strip()
            if raw and len(raw)<=1800:out.append((m.start(),m.end(),raw))
    out.sort(key=lambda x:(x[0],x[1]))
    ded=[];seen=set()
    for row in out:
        k=(row[0],row[1],row[2])
        if k not in seen:seen.add(k);ded.append(row)
    return ded

def _parse(raw:str):
    if len(raw)>1800:return None
    try:
        with _deadline(2):
            return parse_latex(raw,backend='lark')
    except Exception:
        return None

def _node_count(x:sp.Basic)->int:
    try:return sum(1 for _ in sp.preorder_traversal(x))
    except Exception:return 10**9

def _safe_doit(x:Any):
    if not isinstance(x,sp.Basic) or _node_count(x)>1200:return None
    try:
        with _deadline(2):
            y=x.doit(deep=True)
            y=sp.simplify(y)
    except Exception:return None
    if not isinstance(y,sp.Basic) or _node_count(y)>1500:return None
    return y

def _render(x:Any)->str|None:
    if x is None:return None
    try:
        if isinstance(x,sp.Float):
            if abs(float(x)-round(float(x)))<1e-12:return str(int(round(float(x))))
            return sp.sstr(x.evalf(12))
        if isinstance(x,(sp.Integer,sp.Rational)):
            return sp.sstr(x)
        if isinstance(x,sp.Basic):
            if x.has(sp.zoo,sp.oo,-sp.oo,sp.nan):return None
            return sp.sstr(x)
    except Exception:return None
    return None

def _tail(q:str)->str:
    q=' '.join(q.split())
    parts=[x.strip() for x in re.split(r'(?<=[.!?])\s+',q) if x.strip()]
    return parts[-1] if parts else q[-1600:]

def _target_from_tail(q:str,segs:list[tuple[int,int,str]],parsed:list[Any]):
    tail=_tail(q)
    if not _ASK.search(tail):return None
    tail_start=max(0,len(q)-max(len(tail)+200,1800))
    candidates=[]
    for row,obj in zip(segs,parsed):
        if row[0]>=tail_start and obj is not None:
            candidates.append(obj)
    return candidates[-1] if candidates else None

def _select_solution(values:list[Any],question:str):
    vals=[]
    for v in values:
        y=_safe_doit(v) if isinstance(v,sp.Basic) else v
        if y is not None:vals.append(y)
    if len(vals)==1:return vals[0]
    if not vals:return None
    real=[]
    for v in vals:
        try:
            if v.is_real is True:real.append(v)
        except Exception:pass
    pool=real or vals
    try:
        if _NONNEG.search(question):
            p=[v for v in pool if sp.N(v)>=0]
            return p[0] if len(p)==1 else None
        if _POS.search(question):
            p=[v for v in pool if sp.N(v)>0]
            if len(p)==1:return p[0]
            if p and re.search(r'\b(?:largest|greatest|maximum|maximal)\b',question,re.I):return max(p,key=lambda z:float(sp.N(z)))
        if _NEG.search(question):
            p=[v for v in pool if sp.N(v)<0]
            if len(p)==1:return p[0]
            if p and re.search(r'\b(?:smallest|least|minimum|minimal)\b',question,re.I):return min(p,key=lambda z:float(sp.N(z)))
    except Exception:return None
    return None

def propose(*,task_id:str,question:str,has_nonempty_image_payload:bool=False)->dict[str,Any]:
    base={
        'schema':SCHEMA,'task_id':task_id,'question_sha256':hashlib.sha256(question.encode()).hexdigest(),
        'candidate_answer_authority':False,'gold_accessed':False,'external_model_calls':0,
        'external_reasoning_model_calls':0,'model_dependency_count':0,'incremental_spend_usd':0,
        'terminal_authority':False,
    }
    if has_nonempty_image_payload:
        return {**base,'status':'FAIL_CLOSED__IMAGE_SEMANTICS_UNSUPPORTED','candidate_answer':None}
    segs=_segments(question)
    if not segs:return {**base,'status':'FAIL_CLOSED__NO_LATEX_SEGMENTS','candidate_answer':None}
    parsed=[_parse(r[2]) for r in segs]
    good=[x for x in parsed if isinstance(x,sp.Basic)]
    if not good:return {**base,'status':'FAIL_CLOSED__NO_PARSEABLE_LATEX','candidate_answer':None}

    target=_target_from_tail(question,segs,parsed)
    equations=[x for x in good if isinstance(x,sp.Equality)]

    if isinstance(target,sp.Basic) and not isinstance(target,sp.Equality) and not target.free_symbols:
        y=_safe_doit(target); ans=_render(y)
        if ans is not None:
            return {**base,'status':'CANDIDATE_GENERATED','candidate_answer':ans,'compile_mode':'LARK_DIRECT_CLOSED_TARGET','parseable_segment_count':len(good),'hard_nonclaim':'SYMPY_LARK_PROPOSAL_NOT_GENERAL_MATH_CORRECTNESS'}

    target_expr=None
    target_symbol=None
    if isinstance(target,sp.Symbol):target_symbol=target;target_expr=target
    elif isinstance(target,sp.Basic) and not isinstance(target,sp.Equality):target_expr=target

    symbols=sorted(set().union(*(e.free_symbols for e in equations)),key=lambda s:s.name) if equations else []
    if len(equations)<=8 and 1<=len(symbols)<=5:
        if target_symbol is None and len(symbols)==1:target_symbol=symbols[0];target_expr=target_symbol
        try:
            with _deadline(3):
                sols=sp.solve(equations,symbols,dict=True,simplify=True)
        except Exception:sols=[]
        if isinstance(sols,dict):sols=[sols]
        if sols and target_expr is not None:
            vals=[]
            for sol in sols[:32]:
                try:
                    v=sp.simplify(target_expr.subs(sol))
                    if not v.free_symbols:vals.append(v)
                except Exception:pass
            sel=_select_solution(vals,question);ans=_render(sel)
            if ans is not None:
                return {**base,'status':'CANDIDATE_GENERATED','candidate_answer':ans,'compile_mode':'LARK_SMALL_EQUATION_SYSTEM','equation_count':len(equations),'symbol_count':len(symbols),'parseable_segment_count':len(good),'hard_nonclaim':'SYMPY_LARK_PROPOSAL_NOT_GENERAL_MATH_CORRECTNESS'}

    if len(equations)==1 and len(equations[0].free_symbols)==1:
        s=next(iter(equations[0].free_symbols))
        try:
            with _deadline(2):vals=sp.solve(equations[0],s)
        except Exception:vals=[]
        sel=_select_solution(list(vals) if isinstance(vals,(list,tuple,set)) else [vals],question);ans=_render(sel)
        if ans is not None:
            return {**base,'status':'CANDIDATE_GENERATED','candidate_answer':ans,'compile_mode':'LARK_SINGLE_EQUATION','equation_count':1,'symbol_count':1,'parseable_segment_count':len(good),'hard_nonclaim':'SYMPY_LARK_PROPOSAL_NOT_GENERAL_MATH_CORRECTNESS'}

    if _ASK.search(_tail(question)):
        for obj in reversed(good):
            if isinstance(obj,sp.Equality) or obj.free_symbols:continue
            y=_safe_doit(obj);ans=_render(y)
            if ans is not None:
                return {**base,'status':'CANDIDATE_GENERATED','candidate_answer':ans,'compile_mode':'LARK_LAST_CLOSED_EXPRESSION','parseable_segment_count':len(good),'hard_nonclaim':'SYMPY_LARK_PROPOSAL_NOT_GENERAL_MATH_CORRECTNESS'}

    return {**base,'status':'FAIL_CLOSED__PARSED_BUT_UNRESOLVED','candidate_answer':None,'parseable_segment_count':len(good),'equation_count':len(equations)}
