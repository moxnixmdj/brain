#!/usr/bin/env python3
"""Brain-owned deterministic symbolic surface solver for bounded HLE numeric forms.

This V1 deliberately covers only mechanically compilable forms. It never calls a
model or reads gold. Unsupported semantics fail closed rather than guessing.
"""
from __future__ import annotations

import ast, hashlib, math, operator, re
from typing import Any

SCHEMA='PROJECT_BRAIN_HLE_SYMBOLIC_SURFACE_SOLVER_V1'
_INLINE=[re.compile(r'\\\((.*?)\\\)',re.S),re.compile(r'\$(.*?)\$',re.S),re.compile(r'\\\[(.*?)\\\]',re.S)]
_NUM=r'[-+]?(?:\d+(?:\.\d+)?)'

class Unsupported(ValueError): pass

def _frac_repl(m): return f'(({m.group(1)})/({m.group(2)}))'
def _sqrt_repl(m): return f'sqrt({m.group(1)})'

def normalize_latex(x:str)->str:
    s=x.strip()
    for _ in range(4):
        ns=re.sub(r'\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}',_frac_repl,s)
        ns=re.sub(r'\\sqrt\s*\{([^{}]+)\}',_sqrt_repl,ns)
        if ns==s: break
        s=ns
    s=s.replace('\\cdot','*').replace('\\times','*').replace('\\div','/').replace('\\pi','pi')
    s=s.replace('−','-').replace('–','-').replace('^','**')
    s=re.sub(r'\\left|\\right','',s)
    s=s.replace('{','(').replace('}',')')
    s=re.sub(r'\\,|\\!|\\;|\\:',' ',s)
    s=re.sub(r'\s+','',s)
    return s

_BIN={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Pow:operator.pow,ast.Mod:operator.mod}
_UN={ast.UAdd:operator.pos,ast.USub:operator.neg}
_FUN={'sqrt':math.sqrt,'abs':abs,'factorial':math.factorial,'gcd':math.gcd,'lcm':math.lcm,'floor':math.floor,'ceil':math.ceil}
_CONST={'pi':math.pi,'e':math.e}

def safe_eval(expr:str)->float|int:
    if len(expr)>600: raise Unsupported('EXPR_TOO_LONG')
    tree=ast.parse(expr,mode='eval')
    def ev(n):
        if isinstance(n,ast.Expression): return ev(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)): return n.value
        if isinstance(n,ast.Name) and n.id in _CONST:return _CONST[n.id]
        if isinstance(n,ast.BinOp) and type(n.op) in _BIN:
            a,b=ev(n.left),ev(n.right)
            if isinstance(n.op,ast.Pow) and abs(b)>10000: raise Unsupported('POWER_TOO_LARGE')
            return _BIN[type(n.op)](a,b)
        if isinstance(n,ast.UnaryOp) and type(n.op) in _UN:return _UN[type(n.op)](ev(n.operand))
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in _FUN and not n.keywords:
            args=[ev(a) for a in n.args];return _FUN[n.func.id](*args)
        raise Unsupported('AST_OUTSIDE_SAFE_SURFACE')
    v=ev(tree)
    if isinstance(v,complex) or not math.isfinite(float(v)):raise Unsupported('NONFINITE_OR_COMPLEX')
    return v

def _format(v:float|int)->str:
    if isinstance(v,int): return str(v)
    x=float(v)
    if abs(x-round(x))<1e-12:return str(int(round(x)))
    return format(x,'.12g')

def _math_segments(q:str)->list[str]:
    out=[]
    for r in _INLINE:
        for m in r.finditer(q):
            s=m.group(1).strip()
            if s and s not in out:out.append(s)
    return out

def _solve_monomial_equation(question:str):
    q=normalize_latex(question)
    m=re.search(r'\b([A-Za-z])\*\*(\d+)=' + f'({_NUM})',q)
    if not m:return None
    var,n,c=m.group(1),int(m.group(2)),float(m.group(3))
    if n<2 or n>8:return None
    low=question.casefold()
    selector='positive' if re.search(r'\bpositive\b|\bgreater than zero\b',low) else 'negative' if re.search(r'\bnegative\b|\bless than zero\b',low) else 'nonnegative' if re.search(r'\bnonnegative\b',low) else None
    if selector is None:return None
    if c<0 and n%2==0:return None
    root=abs(c)**(1.0/n)
    if selector=='negative':root=-root
    if selector=='nonnegative':root=abs(root)
    return _format(root)

def _solve_linear_equation(question:str):
    low=question.casefold()
    if not re.search(r'\b(?:solve|find|determine)\b',low):return None
    norm=normalize_latex(question)
    m=re.search(r'(?<![A-Za-z0-9])(?:(%s)\*)?([A-Za-z])([+-]%s)?=(%s)'%(_NUM,_NUM,_NUM),norm)
    if not m:return None
    a=float(m.group(1)) if m.group(1) is not None else 1.0
    b=float(m.group(3)) if m.group(3) else 0.0
    c=float(m.group(4))
    if a==0:return None
    return _format((c-b)/a)

def propose(*,task_id:str,question:str,has_nonempty_image_payload:bool=False)->dict[str,Any]:
    base={'schema':SCHEMA,'task_id':task_id,'question_sha256':hashlib.sha256(question.encode()).hexdigest(),'candidate_answer_authority':False,'gold_accessed':False,'external_model_calls':0,'model_dependency_count':0,'incremental_spend_usd':0,'terminal_authority':False}
    if has_nonempty_image_payload:return {**base,'status':'FAIL_CLOSED__IMAGE_SEMANTICS_UNSUPPORTED','candidate_answer':None}
    for mode,fn in [('MONOMIAL_EQUATION',_solve_monomial_equation),('LINEAR_EQUATION',_solve_linear_equation)]:
        try:a=fn(question)
        except Exception:a=None
        if a is not None:return {**base,'status':'CANDIDATE_GENERATED','candidate_answer':a,'compile_mode':mode,'hard_nonclaim':'BOUNDED_SYMBOLIC_SURFACE_PROPOSAL_NOT_GENERAL_MATH_CORRECTNESS'}
    if re.search(r'\b(?:compute|calculate|evaluate)\b',question,re.I):
        for raw in reversed(_math_segments(question)):
            expr=normalize_latex(raw)
            if any(x in expr for x in ['=','<','>']) or '\\' in expr:continue
            names=set(re.findall(r'\b[A-Za-z]+\b',expr))
            if any(n not in set(_FUN)|set(_CONST) for n in names):continue
            try:v=safe_eval(expr)
            except Exception:continue
            return {**base,'status':'CANDIDATE_GENERATED','candidate_answer':_format(v),'compile_mode':'EXPLICIT_ARITHMETIC_EXPRESSION','expression_sha256':hashlib.sha256(expr.encode()).hexdigest(),'hard_nonclaim':'BOUNDED_SYMBOLIC_SURFACE_PROPOSAL_NOT_GENERAL_MATH_CORRECTNESS'}
    return {**base,'status':'FAIL_CLOSED__UNSUPPORTED_SYMBOLIC_FORM','candidate_answer':None}
