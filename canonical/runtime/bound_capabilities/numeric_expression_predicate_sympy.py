#!/usr/bin/env python3
"""Restricted model-independent numeric expression and predicate evaluation via SymPy.

The adapter never evals Python and never sympifies user text. It parses a tiny
Python-expression AST, constructs SymPy objects node-by-node, and rejects every
syntax form outside the promoted numeric envelope.
"""
from __future__ import annotations
import ast
import math
import re

MAX_EXPRESSION_CHARS=512
MAX_AST_NODES=96
MAX_VARIABLES=16
MAX_ABS_EXPONENT=64.0
MAX_ABS_INPUT=1e100
ALLOWED_FUNCTIONS={"abs","min","max"}


def _number(value, sp):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise RuntimeError("NUMERIC_INPUT_REQUIRED")
    if isinstance(value,float):
        if not math.isfinite(value):
            raise RuntimeError("NUMERIC_INPUT_NONFINITE")
        if abs(value)>MAX_ABS_INPUT:
            raise RuntimeError("NUMERIC_INPUT_MAGNITUDE_LIMIT")
        return sp.Float(repr(value),50)
    if abs(value)>10**300:
        raise RuntimeError("NUMERIC_INPUT_MAGNITUDE_LIMIT")
    return sp.Integer(value)


def _truth(value):
    if isinstance(value,bool):
        return value
    try:
        return bool(value)
    except Exception as exc:
        raise RuntimeError("NUMERIC_PREDICATE_NOT_DECIDABLE") from exc


def _real_float(value, sp):
    evaluated=sp.N(value,40)
    if evaluated.is_real is not True or evaluated.is_finite is not True:
        raise RuntimeError("NUMERIC_RESULT_NOT_FINITE_REAL")
    out=float(evaluated)
    if not math.isfinite(out):
        raise RuntimeError("NUMERIC_RESULT_NOT_FINITE_FLOAT")
    return out


def _eval(node, env, sp):
    if isinstance(node,ast.Constant):
        return _number(node.value,sp)
    if isinstance(node,ast.Name):
        if node.id not in env:
            raise RuntimeError("NUMERIC_VARIABLE_UNBOUND:"+node.id)
        return env[node.id]
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
        value=_eval(node.operand,env,sp)
        return value if isinstance(node.op,ast.UAdd) else -value
    if isinstance(node,ast.BinOp):
        left=_eval(node.left,env,sp)
        right=_eval(node.right,env,sp)
        if isinstance(node.op,ast.Add):
            return left+right
        if isinstance(node.op,ast.Sub):
            return left-right
        if isinstance(node.op,ast.Mult):
            return left*right
        if isinstance(node.op,ast.Div):
            if sp.simplify(right)==0:
                raise RuntimeError("NUMERIC_DIVISION_BY_ZERO")
            return left/right
        if isinstance(node.op,ast.Mod):
            if sp.simplify(right)==0:
                raise RuntimeError("NUMERIC_MODULO_BY_ZERO")
            return sp.Mod(left,right)
        if isinstance(node.op,ast.Pow):
            exponent=_real_float(right,sp)
            if abs(exponent)>MAX_ABS_EXPONENT:
                raise RuntimeError("NUMERIC_EXPONENT_LIMIT")
            return sp.Pow(left,right)
        raise RuntimeError("NUMERIC_OPERATOR_REJECTED:"+type(node.op).__name__)
    if isinstance(node,ast.Call):
        if not isinstance(node.func,ast.Name) or node.func.id not in ALLOWED_FUNCTIONS:
            raise RuntimeError("NUMERIC_CALL_REJECTED")
        if node.keywords:
            raise RuntimeError("NUMERIC_KEYWORDS_REJECTED")
        values=[_eval(x,env,sp) for x in node.args]
        if not values:
            raise RuntimeError("NUMERIC_CALL_ARGUMENT_REQUIRED")
        if node.func.id=="abs" and len(values)==1:
            return sp.Abs(values[0])
        if node.func.id=="min":
            return sp.Min(*values)
        if node.func.id=="max":
            return sp.Max(*values)
        raise RuntimeError("NUMERIC_CALL_ARITY_INVALID")
    if isinstance(node,ast.Compare):
        left=_eval(node.left,env,sp)
        if len(node.ops)!=len(node.comparators) or not node.ops:
            raise RuntimeError("NUMERIC_COMPARE_INVALID")
        results=[]
        for op,rhs_node in zip(node.ops,node.comparators):
            right=_eval(rhs_node,env,sp)
            if isinstance(op,ast.Lt):
                rel=sp.Lt(left,right)
            elif isinstance(op,ast.LtE):
                rel=sp.Le(left,right)
            elif isinstance(op,ast.Gt):
                rel=sp.Gt(left,right)
            elif isinstance(op,ast.GtE):
                rel=sp.Ge(left,right)
            elif isinstance(op,ast.Eq):
                rel=sp.Eq(left,right)
            elif isinstance(op,ast.NotEq):
                rel=sp.Ne(left,right)
            else:
                raise RuntimeError("NUMERIC_COMPARE_OPERATOR_REJECTED")
            results.append(_truth(rel))
            left=right
        return all(results)
    raise RuntimeError("NUMERIC_AST_NODE_REJECTED:"+type(node).__name__)


def _parse(expression):
    if not isinstance(expression,str) or not expression.strip():
        raise RuntimeError("NUMERIC_EXPRESSION_REQUIRED")
    expression=expression.strip()
    if len(expression)>MAX_EXPRESSION_CHARS:
        raise RuntimeError("NUMERIC_EXPRESSION_TOO_LONG")
    try:
        tree=ast.parse(expression,mode="eval")
    except SyntaxError as exc:
        raise RuntimeError("NUMERIC_EXPRESSION_SYNTAX_INVALID") from exc
    nodes=list(ast.walk(tree))
    if len(nodes)>MAX_AST_NODES:
        raise RuntimeError("NUMERIC_EXPRESSION_AST_LIMIT")
    forbidden=(
        ast.Attribute,ast.Subscript,ast.Lambda,ast.Dict,ast.List,ast.Set,ast.Tuple,
        ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp,ast.NamedExpr,
        ast.IfExp,ast.BoolOp,
    )
    if any(isinstance(node,forbidden) for node in nodes):
        raise RuntimeError("NUMERIC_EXPRESSION_SURFACE_REJECTED")
    return tree


def run(args, root):
    try:
        import sympy as sp
    except Exception as exc:
        raise RuntimeError("SYMPY_IMPORT_FAILED") from exc
    if sp.__version__!="1.14.0":
        raise RuntimeError("SYMPY_VERSION_MISMATCH:"+str(sp.__version__))

    expression=str(args.get("expression") or "").strip()
    raw_vars=args.get("variables")
    if not isinstance(raw_vars,dict) or len(raw_vars)>MAX_VARIABLES:
        raise RuntimeError("NUMERIC_VARIABLES_INVALID")
    env={}
    observed={}
    for name,value in raw_vars.items():
        name=str(name)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,31}",name):
            raise RuntimeError("NUMERIC_VARIABLE_NAME_INVALID")
        env[name]=_number(value,sp)
        observed[name]=value

    guard=args.get("guard",True)
    if not isinstance(guard,bool):
        raise RuntimeError("NUMERIC_GUARD_BOOLEAN_REQUIRED")
    if not guard:
        label=args.get("guard_failure_label")
        if label is not None and (
            not isinstance(label,str)
            or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}",label)
        ):
            raise RuntimeError("NUMERIC_GUARD_LABEL_INVALID")
        return {
            "adapter":"numeric_expression_predicate_sympy",
            "verified":True,
            "status":"GUARD_FALSE",
            "operation":"SKIPPED_BY_GUARD",
            "expression":expression,
            "input_values":observed,
            "value":None,
            "predicate":False,
            "label":label,
            "sympy_version":sp.__version__,
            "model_dependency_count":0,
        }

    tree=_parse(expression)
    result=_eval(tree.body,env,sp)
    predicate=result if isinstance(result,bool) else None
    if isinstance(result,bool):
        value=result
    else:
        value=_real_float(result,sp)

    true_label=args.get("true_label")
    false_label=args.get("false_label")
    label=None
    if true_label is not None or false_label is not None:
        if not isinstance(result,bool):
            raise RuntimeError("NUMERIC_LABEL_REQUIRES_PREDICATE")
        for candidate in (true_label,false_label):
            if not isinstance(candidate,str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}",candidate):
                raise RuntimeError("NUMERIC_LABEL_INVALID")
        label=true_label if result else false_label

    return {
        "adapter":"numeric_expression_predicate_sympy",
        "verified":True,
        "status":"EVALUATED",
        "expression":expression,
        "input_values":observed,
        "value":value,
        "predicate":predicate,
        "label":label,
        "sympy_version":sp.__version__,
        "model_dependency_count":0,
    }
