"""Canonical AST program-length measurement for non-synthetic H100 capabilities.

The coding convention is frozen in
H100_NON_SYNTHETIC_DESCRIPTION_LENGTH_PRECOMMIT_V1.json before outcomes.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_NON_SYNTHETIC_DESCRIPTION_LENGTH_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_NON_SYNTHETIC_DESCRIPTION_LENGTH_RESULT_V1"
COMPILED_REFERENCE_BITS=6

class DescriptionCodeError(ValueError):
    pass

def _drop_docstring(body:list[ast.stmt])->list[ast.stmt]:
    if body and isinstance(body[0],ast.Expr):
        v=body[0].value
        if isinstance(v,ast.Constant) and isinstance(v.value,str):
            return body[1:]
    return body

class _DocstringStripper(ast.NodeTransformer):
    def visit_Module(self,node:ast.Module):
        self.generic_visit(node)
        node.body=_drop_docstring(node.body)
        return node
    def visit_FunctionDef(self,node:ast.FunctionDef):
        self.generic_visit(node)
        node.body=_drop_docstring(node.body)
        return node
    def visit_AsyncFunctionDef(self,node:ast.AsyncFunctionDef):
        self.generic_visit(node)
        node.body=_drop_docstring(node.body)
        return node
    def visit_ClassDef(self,node:ast.ClassDef):
        self.generic_visit(node)
        node.body=_drop_docstring(node.body)
        return node

def canonical_ast_text(source:str)->str:
    if not isinstance(source,str):
        raise DescriptionCodeError("SOURCE_NOT_TEXT")
    try:
        tree=ast.parse(source)
    except SyntaxError as exc:
        raise DescriptionCodeError("SOURCE_SYNTAX_INVALID") from exc
    tree=_DocstringStripper().visit(tree)
    return ast.dump(tree,annotate_fields=True,include_attributes=False)

def gamma_length_bits_for_byte_count(n:int)->int:
    if not isinstance(n,int) or isinstance(n,bool) or n<0:
        raise DescriptionCodeError("BYTE_COUNT_INVALID")
    positive=n+1
    return 2*int(math.floor(math.log2(positive)))+1

def raw_program_bits_from_canonical_bytes(n:int)->int:
    return gamma_length_bits_for_byte_count(n)+8*n

def measure_path(path:Path)->dict[str,Any]:
    src=path.read_text(encoding="utf-8")
    text=canonical_ast_text(src)
    blob=text.encode("utf-8")
    raw_bits=raw_program_bits_from_canonical_bytes(len(blob))
    delta=raw_bits-COMPILED_REFERENCE_BITS
    if delta<=0:
        raise DescriptionCodeError("NONPOSITIVE_DESCRIPTION_REDUCTION")
    return {
        "path":str(path.relative_to(ROOT)),
        "canonical_ast_utf8_bytes":len(blob),
        "canonical_ast_sha256":hashlib.sha256(blob).hexdigest(),
        "raw_self_delimiting_program_bits":raw_bits,
        "compiled_registry_reference_bits":COMPILED_REFERENCE_BITS,
        "description_bit_reduction":delta,
        "generic_prefix_search_bound_ratio_log2":delta,
        "generic_prefix_search_bound_ratio":"2^"+str(delta),
    }

def run()->dict[str,Any]:
    if sys.version_info[:2]!=(3,11):
        raise DescriptionCodeError("PYTHON_3_11_REQUIRED_FOR_FROZEN_AST_CODE")
    pre=json.loads(PRE.read_text())
    if pre.get("status")!="FROZEN_BEFORE_AST_CODE_LENGTH_OUTCOMES__FOUR_PRIOR_VERIFIED_NON_SYNTHETIC_CAPABILITIES__ZERO_CREDIT":
        raise DescriptionCodeError("PRECOMMIT_NOT_FROZEN")
    rows=[]
    for item in pre["cohort"]:
        row=measure_path(ROOT/item["runtime"])
        row["id"]=item["id"]
        row["registry_id"]=item["registry_id"]
        rows.append(row)
    deltas=[x["description_bit_reduction"] for x in rows]
    raw=[x["raw_self_delimiting_program_bits"] for x in rows]
    return {
        "schema":SCHEMA,
        "status":"NON_SYNTHETIC_CANONICAL_AST_DESCRIPTION_LENGTH_MEASURED__FOUR_CAPABILITY_CLASSES__ZERO_CREDIT",
        "python_version":".".join(map(str,sys.version_info[:3])),
        "subjects":rows,
        "summary":{
            "subject_count":len(rows),
            "raw_program_bits_min":min(raw),
            "raw_program_bits_median":sorted(raw)[len(raw)//2-1:len(raw)//2+1] if len(raw)%2==0 else sorted(raw)[len(raw)//2],
            "raw_program_bits_max":max(raw),
            "description_bit_reduction_min":min(deltas),
            "description_bit_reduction_max":max(deltas),
            "compiled_reference_bits":COMPILED_REFERENCE_BITS,
        },
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "CANONICAL_AST_CODE_LENGTH_IS_NOT_KOLMOGOROV_COMPLEXITY",
            "PYTHON_AST_CODE_IS_IMPLEMENTATION_LEVEL",
            "2^DELTA_IS_NOT_A_MEASURED_WALL_CLOCK_SPEEDUP",
            "COMPILED_REFERENCE_ASSUMES_CAPABILITY_ALREADY_EXISTS_IN_VERIFIED_REGISTRY",
            "NO_H100_TERMINAL_CREDIT"
        ],
        "h100_terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
