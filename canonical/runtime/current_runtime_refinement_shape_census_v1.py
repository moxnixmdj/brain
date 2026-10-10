"""Conservative AST census for prioritizing current runtime refinement work.

This is scheduling evidence only. It grants no semantic-refinement credit.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CURRENT_RUNTIME_REFINEMENT_SHAPE_CENSUS_V1"
DANGEROUS_IMPORT_ROOTS={"subprocess","requests","urllib","socket","httpx","aiohttp","shutil"}
DANGEROUS_CALL_NAMES={"exec","eval","open","__import__"}
DANGEROUS_ATTRS={"write_text","write_bytes","replace","unlink","mkdir","rmdir","remove","rename"}
AUTHORITY_KEYS={"terminal_authority","execution_authority","capability_promotion_authority","acceptance_authority"}


def _scan(path:Path)->dict[str,Any]:
    tree=ast.parse(path.read_text(encoding="utf-8"))
    dynamic_or_effect=False
    canonical_dependency=False
    authority_true=False
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[]
            if isinstance(node,ast.Import):
                names=[x.name for x in node.names]
            else:
                names=[node.module or ""]
            for name in names:
                root=name.split(".")[0]
                if root in DANGEROUS_IMPORT_ROOTS:
                    dynamic_or_effect=True
                if name=="canonical.runtime" or name.startswith("canonical.runtime."):
                    canonical_dependency=True
                if name=="importlib" or name.startswith("importlib."):
                    dynamic_or_effect=True
        elif isinstance(node,ast.Call):
            if isinstance(node.func,ast.Name) and node.func.id in DANGEROUS_CALL_NAMES:
                dynamic_or_effect=True
            if isinstance(node.func,ast.Attribute) and node.func.attr in DANGEROUS_ATTRS:
                dynamic_or_effect=True
        elif isinstance(node,ast.Dict):
            for key,value in zip(node.keys,node.values):
                if isinstance(key,ast.Constant) and key.value in AUTHORITY_KEYS:
                    if isinstance(value,ast.Constant) and value.value is True:
                        authority_true=True
    if authority_true or dynamic_or_effect:
        category="AUTHORITY_EFFECT_OR_DYNAMIC"
    elif canonical_dependency:
        category="TRANSITIVE_RUNTIME_DEPENDENT"
    else:
        category="SELF_CONTAINED_NO_DIRECT_EFFECT"
    return {
        "category":category,
        "direct_dynamic_or_effect_surface":dynamic_or_effect,
        "literal_authority_true_surface":authority_true,
        "canonical_runtime_dependency":canonical_dependency,
    }


def run(
    repo_root:str|Path,
    *,
    snapshot_path:str="canonical/governance/CURRENT_AUTHORITY_RUNTIME_REFINEMENT_OBLIGATION_SNAPSHOT_20261010_V1.json",
)->dict[str,Any]:
    root=Path(repo_root).resolve()
    p=(root/snapshot_path).resolve()
    if root not in p.parents or not p.is_file():
        raise ValueError("OBLIGATION_SNAPSHOT_MISSING_OR_OUTSIDE_REPO")
    raw=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw,Mapping) or raw.get("coverage_complete") is not True:
        raise ValueError("OBLIGATION_SNAPSHOT_NOT_COMPLETE")
    obligations=raw.get("obligations")
    if not isinstance(obligations,list) or not obligations:
        raise ValueError("OBLIGATIONS_REQUIRED")
    rows=[]
    for item in obligations:
        if not isinstance(item,Mapping):
            raise ValueError("OBLIGATION_NOT_OBJECT")
        rel=str(item.get("path") or "")
        full=(root/rel).resolve()
        if root not in full.parents or not full.is_file():
            raise ValueError("RUNTIME_PATH_INVALID:"+rel)
        row={"path":rel,"git_blob_sha":str(item.get("git_blob_sha") or ""),**_scan(full)}
        rows.append(row)
    counts={}
    for row in rows:
        counts[row["category"]]=counts.get(row["category"],0)+1
    return {
        "schema":SCHEMA,
        "status":"PASS__CONSERVATIVE_REFINEMENT_SHAPE_CENSUS",
        "pass":True,
        "obligation_count":len(rows),
        "category_counts":counts,
        "rows":rows,
        "semantic_refinement_proved":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
