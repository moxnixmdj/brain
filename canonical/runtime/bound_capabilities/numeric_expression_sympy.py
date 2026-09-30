#!/usr/bin/env python3
"""Restricted typed scalar numeric expression evaluation backed by SymPy.

No eval, exec, arbitrary sympify strings, calls, attributes, subscripts, or
container syntax are accepted. The expression is parsed with Python AST and
translated node-by-node to programmatic SymPy objects.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import pathlib
import re

import sympy as sp

_NUMERIC_TEXT=re.compile(r"^[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?$")


def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p!=root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def _number(value):
    if isinstance(value,bool):
        raise RuntimeError("NUMERIC_EXPRESSION_BOOLEAN_REJECTED")
    if isinstance(value,int):
        return sp.Integer(value)
    if isinstance(value,float):
        if not math.isfinite(value):
            raise RuntimeError("NUMERIC_EXPRESSION_NONFINITE_INPUT")
        return sp.Float(repr(value),17)
    if isinstance(value,str):
        text=value.strip()
        if len(text)>96 or not _NUMERIC_TEXT.fullmatch(text):
            raise RuntimeError("NUMERIC_EXPRESSION_INPUT_NOT_NUMERIC")
        try:
            f=float(text)
        except Exception as exc:
            raise RuntimeError("NUMERIC_EXPRESSION_INPUT_NOT_NUMERIC") from exc
        if not math.isfinite(f):
            raise RuntimeError("NUMERIC_EXPRESSION_NONFINITE_INPUT")
        if re.fullmatch(r"[+-]?\d+",text):
            return sp.Integer(text)
        return sp.Float(text,17)
    raise RuntimeError("NUMERIC_EXPRESSION_INPUT_NOT_NUMERIC")


def _build(node, variables, depth=0):
    if depth>16:
        raise RuntimeError("NUMERIC_EXPRESSION_DEPTH_LIMIT")
    if isinstance(node,ast.Expression):
        return _build(node.body,variables,depth+1)
    if isinstance(node,ast.Constant):
        if isinstance(node.value,(int,float)) and not isinstance(node.value,bool):
            if isinstance(node.value,float) and not math.isfinite(node.value):
                raise RuntimeError("NUMERIC_EXPRESSION_LITERAL_NONFINITE")
            if abs(float(node.value))>1e100:
                raise RuntimeError("NUMERIC_EXPRESSION_LITERAL_LIMIT")
            return _number(node.value)
        raise RuntimeError("NUMERIC_EXPRESSION_LITERAL_TYPE_REJECTED")
    if isinstance(node,ast.Name):
        if node.id not in variables:
            raise RuntimeError("NUMERIC_EXPRESSION_VARIABLE_UNBOUND:"+node.id)
        return variables[node.id]
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
        value=_build(node.operand,variables,depth+1)
        return value if isinstance(node.op,ast.UAdd) else -value
    if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
        left=_build(node.left,variables,depth+1)
        right=_build(node.right,variables,depth+1)
        if isinstance(node.op,ast.Add): return left+right
        if isinstance(node.op,ast.Sub): return left-right
        if isinstance(node.op,ast.Mult): return left*right
        if isinstance(node.op,ast.Div): return left/right
        try:
            exponent=float(sp.N(right,17))
        except Exception as exc:
            raise RuntimeError("NUMERIC_EXPRESSION_EXPONENT_INVALID") from exc
        if not math.isfinite(exponent) or abs(exponent)>32:
            raise RuntimeError("NUMERIC_EXPRESSION_EXPONENT_LIMIT")
        return left**right
    raise RuntimeError("NUMERIC_EXPRESSION_AST_NODE_REJECTED:"+type(node).__name__)


def run(args, root):
    expression=str(args.get("expression") or "").strip()
    raw_variables=args.get("variables")
    if not expression or len(expression)>512:
        raise RuntimeError("NUMERIC_EXPRESSION_REQUIRED")
    if not isinstance(raw_variables,dict) or len(raw_variables)>16:
        raise RuntimeError("NUMERIC_EXPRESSION_VARIABLES_INVALID")
    variables={}
    for name,value in raw_variables.items():
        name=str(name or "")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}",name):
            raise RuntimeError("NUMERIC_EXPRESSION_VARIABLE_NAME_INVALID")
        variables[name]=_number(value)
    try:
        tree=ast.parse(expression,mode="eval")
    except SyntaxError as exc:
        raise RuntimeError("NUMERIC_EXPRESSION_SYNTAX_INVALID") from exc
    nodes=list(ast.walk(tree))
    if len(nodes)>64:
        raise RuntimeError("NUMERIC_EXPRESSION_NODE_LIMIT")
    result=_build(tree,variables)
    if result.has(sp.zoo,sp.oo,-sp.oo,sp.nan):
        raise RuntimeError("NUMERIC_EXPRESSION_NONFINITE_RESULT")
    if result.is_real is not True:
        raise RuntimeError("NUMERIC_EXPRESSION_RESULT_NOT_REAL")
    numeric=sp.N(result,17)
    try:
        value=float(numeric)
    except Exception as exc:
        raise RuntimeError("NUMERIC_EXPRESSION_RESULT_NOT_SCALAR") from exc
    if not math.isfinite(value):
        raise RuntimeError("NUMERIC_EXPRESSION_NONFINITE_RESULT")
    output=_safe_path(root,args.get("output_path"))
    output.parent.mkdir(parents=True,exist_ok=True)
    payload={
      "schema":"PROJECT_BRAIN_TYPED_SCALAR_NUMERIC_EXPRESSION_RESULT_V1",
      "expression":expression,
      "variables":{k:str(v) for k,v in variables.items()},
      "symbolic_result":str(result),
      "value":value,
      "model_dependency_count":0,
      "output_verified":True,
    }
    output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    return {
      "adapter":"numeric_expression_sympy",
      "expression":expression,
      "value":value,
      "symbolic_result":str(result),
      "variable_names":sorted(variables),
      "output_path":str(output.relative_to(pathlib.Path(root).resolve())),
      "output_sha256":hashlib.sha256(raw).hexdigest(),
      "model_dependency_count":0,
      "output_verified":True,
    }
