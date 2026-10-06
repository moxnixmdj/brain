"""Deterministic representation minifier for the frozen numeric-kernel campaign.

This transforms Python source under a deliberately narrow observational contract:
the frozen V2 capability campaign. It is NOT claimed as general Python semantic
equivalence. It removes annotations/docstrings, shortens internal global names,
and keeps only runtime typing names proven necessary by falsification.
"""
from __future__ import annotations
import ast, hashlib, bz2
from pathlib import Path

RENAMES={
"_EPS":"A","_UNARY":"B","_BINARY":"C","_COMMUTATIVE":"D",
"ExpressionTreeError":"E","_finite":"F","_normalize_rows":"G","_nrmse":"H",
"_solve_linear_system":"I","_fit_linear_features":"J","_apply_unary":"K",
"_apply_binary":"L","evaluate_tree":"M","_structural_signature":"N",
"_tree_complexity":"O","_feature_record":"P","_vector_key":"Q","_predict_combo":"R",
}

class _T(ast.NodeTransformer):
    def visit_Module(self,node):
        kept=[]
        for x in node.body:
            if isinstance(x,ast.ImportFrom) and x.module=="__future__":
                continue
            if isinstance(x,ast.ImportFrom) and x.module=="typing":
                x.names=[a for a in x.names if a.name in {"Mapping","Sequence"}]
                if not x.names:
                    continue
            kept.append(x)
        node.body=kept
        self.generic_visit(node)
        if node.body and _is_docstring(node.body[0]):
            node.body.pop(0)
        return node

    def visit_FunctionDef(self,node):
        if node.name in RENAMES:
            node.name=RENAMES[node.name]
        for a in list(node.args.args)+list(node.args.kwonlyargs):
            a.annotation=None
        if node.args.vararg:
            node.args.vararg.annotation=None
        if node.args.kwarg:
            node.args.kwarg.annotation=None
        node.returns=None
        self.generic_visit(node)
        if node.body and _is_docstring(node.body[0]):
            node.body.pop(0)
        return node

    def visit_ClassDef(self,node):
        if node.name in RENAMES:
            node.name=RENAMES[node.name]
        self.generic_visit(node)
        if node.body and _is_docstring(node.body[0]):
            node.body.pop(0)
        return node

    def visit_Name(self,node):
        if node.id in RENAMES:
            node.id=RENAMES[node.id]
        return node

    def visit_AnnAssign(self,node):
        if node.value is None:
            return None
        return ast.copy_location(
            ast.Assign(targets=[self.visit(node.target)],value=self.visit(node.value)),
            node,
        )

def _is_docstring(node):
    return (
        isinstance(node,ast.Expr)
        and isinstance(node.value,ast.Constant)
        and isinstance(node.value.value,str)
    )

def transform_source(source:str)->str:
    tree=ast.parse(source)
    tree=_T().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+"\n"

def transform_file(path:str|Path)->dict[str,object]:
    source=Path(path).read_text(encoding="utf-8")
    out=transform_source(source)
    raw=out.encode("utf-8")
    return {
        "source":out,
        "raw_bytes":len(raw),
        "sha256":hashlib.sha256(raw).hexdigest(),
        "bz2_9_bytes":len(bz2.compress(raw,compresslevel=9)),
    }
