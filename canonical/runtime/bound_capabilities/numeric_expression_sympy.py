#!/usr/bin/env python3
"""Strict typed scalar arithmetic using programmatic SymPy objects only."""
from __future__ import annotations
import ast, math, re

_NUMERIC_TEXT=re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_MAX_EXPR_CHARS=1000
_MAX_AST_NODES=64
_MAX_VARIABLES=16
_MAX_ABS_EXPONENT=100.0

def _scalar(sp, value, label):
    if isinstance(value,bool):
        raise RuntimeError("NUMERIC_EXPRESSION_BOOL_REJECTED:"+label)
    if isinstance(value,int):
        return sp.Integer(value)
    if isinstance(value,float):
        if not math.isfinite(value):
            raise RuntimeError("NUMERIC_EXPRESSION_NONFINITE_INPUT:"+label)
        return sp.Rational(repr(value))
    if isinstance(value,str):
        text=value.strip()
        if not _NUMERIC_TEXT.fullmatch(text):
            raise RuntimeError("NUMERIC_EXPRESSION_INPUT_NOT_NUMERIC:"+label)
        try:
            return sp.Rational(text)
        except Exception as exc:
            raise RuntimeError("NUMERIC_EXPRESSION_INPUT_PARSE_FAILED:"+label) from exc
    raise RuntimeError("NUMERIC_EXPRESSION_INPUT_TYPE_REJECTED:"+label)

def _build(sp, node, variables):
    if isinstance(node,ast.Expression):
        return _build(sp,node.body,variables)
    if isinstance(node,ast.Constant):
        if isinstance(node.value,bool) or not isinstance(node.value,(int,float)):
            raise RuntimeError("NUMERIC_EXPRESSION_LITERAL_REJECTED")
        return _scalar(sp,node.value,"literal")
    if isinstance(node,ast.Name):
        if node.id not in variables:
            raise RuntimeError("NUMERIC_EXPRESSION_UNKNOWN_VARIABLE:"+node.id)
        return variables[node.id]
    if isinstance(node,ast.UnaryOp):
        value=_build(sp,node.operand,variables)
        if isinstance(node.op,ast.UAdd):
            return value
        if isinstance(node.op,ast.USub):
            return -value
        raise RuntimeError("NUMERIC_EXPRESSION_UNARY_OPERATOR_REJECTED")
    if isinstance(node,ast.BinOp):
        left=_build(sp,node.left,variables)
        right=_build(sp,node.right,variables)
        if isinstance(node.op,ast.Add):
            return left+right
        if isinstance(node.op,ast.Sub):
            return left-right
        if isinstance(node.op,ast.Mult):
            return left*right
        if isinstance(node.op,ast.Div):
            if bool(sp.simplify(right)==0):
                raise RuntimeError("NUMERIC_EXPRESSION_DIVISION_BY_ZERO")
            return left/right
        if isinstance(node.op,ast.Pow):
            try:
                exp=float(sp.N(right,20))
            except Exception as exc:
                raise RuntimeError("NUMERIC_EXPRESSION_EXPONENT_NOT_SCALAR") from exc
            if not math.isfinite(exp) or abs(exp)>_MAX_ABS_EXPONENT:
                raise RuntimeError("NUMERIC_EXPRESSION_EXPONENT_OUT_OF_BOUNDS")
            return sp.Pow(left,right)
        raise RuntimeError("NUMERIC_EXPRESSION_BINARY_OPERATOR_REJECTED")
    raise RuntimeError("NUMERIC_EXPRESSION_SYNTAX_REJECTED:"+type(node).__name__)

def run(args, root):
    del root
    expression=str(args.get("expression") or "").strip()
    raw_variables=args.get("variables")
    if not expression or len(expression)>_MAX_EXPR_CHARS:
        raise RuntimeError("NUMERIC_EXPRESSION_TEXT_INVALID")
    if not isinstance(raw_variables,dict) or len(raw_variables)>_MAX_VARIABLES:
        raise RuntimeError("NUMERIC_EXPRESSION_VARIABLES_INVALID")
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",str(k)) for k in raw_variables):
        raise RuntimeError("NUMERIC_EXPRESSION_VARIABLE_NAME_INVALID")
    try:
        tree=ast.parse(expression,mode="eval")
    except SyntaxError as exc:
        raise RuntimeError("NUMERIC_EXPRESSION_PARSE_FAILED") from exc
    if sum(1 for _ in ast.walk(tree))>_MAX_AST_NODES:
        raise RuntimeError("NUMERIC_EXPRESSION_TOO_COMPLEX")

    import sympy as sp
    variables={str(k):_scalar(sp,v,str(k)) for k,v in raw_variables.items()}
    result=sp.simplify(_build(sp,tree,variables))
    if result.is_real is not True or result.is_finite is not True:
        raise RuntimeError("NUMERIC_EXPRESSION_RESULT_NOT_FINITE_REAL")
    numeric=sp.N(result,17)
    value=float(numeric)
    if not math.isfinite(value):
        raise RuntimeError("NUMERIC_EXPRESSION_RESULT_NOT_FINITE_REAL")
    return {
      "adapter":"numeric_expression_sympy",
      "expression":expression,
      "variable_names":sorted(variables),
      "exact_result":str(result),
      "value":value,
      "sympy_version":sp.__version__,
      "verified":True,
      "model_dependency_count":0,
    }
