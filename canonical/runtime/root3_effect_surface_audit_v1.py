"""Fail-closed source audit for Root3 host-effect mediation."""
from __future__ import annotations
import ast, hashlib
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_EFFECT_SURFACE_AUDIT_V1"\n# Sound use: a detected site is constructive evidence of an effect surface.\n# Absence is not yet a whole-program completeness proof; dynamic Python and\n# receiver typing require a stronger closed-world registry/confinement proof.
_SUBPROCESS={"run","Popen","call","check_call","check_output"}
_FS={"write_text","write_bytes","mkdir","unlink","rename","rmdir","touch"}
_SHUTIL={"copy","copy2","copyfile","copytree","move","rmtree"}
_DYNAMIC={"exec_module"}

def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _chain(node:ast.AST)->list[str]:
    out=[]
    while isinstance(node,ast.Attribute):
        out.append(node.attr); node=node.value
    if isinstance(node,ast.Name): out.append(node.id)
    return list(reversed(out))

def _parents(tree:ast.AST)->dict[ast.AST,ast.AST]:
    out={}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p): out[c]=p
    return out

def _owner(node:ast.AST, parents:dict[ast.AST,ast.AST])->str:
    cur=node
    while cur in parents:
        cur=parents[cur]
        if isinstance(cur,(ast.FunctionDef,ast.AsyncFunctionDef)): return cur.name
    return "<module>"

def audit_source(source:str, expected_git_blob_sha:str|None=None)->dict[str,Any]:
    raw=source.encode("utf-8"); sha=git_blob_sha(raw)
    if expected_git_blob_sha and sha!=expected_git_blob_sha:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_BLOB_DRIFT",
                "expected_git_blob_sha":expected_git_blob_sha,"actual_git_blob_sha":sha,
                "no_bypass_proven":False,"terminal_authority":False,"acceptance_credit_delta":0}
    tree=ast.parse(source); parents=_parents(tree); lines=source.splitlines(); sites=[]
    def add(kind,node):
        n=int(getattr(node,"lineno",0) or 0)
        sites.append({"kind":kind,"function":_owner(node,parents),"line":n,
                      "source":lines[n-1].strip() if n else ""})
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call): continue
        chain=_chain(node.func); leaf=chain[-1] if chain else (node.func.id if isinstance(node.func,ast.Name) else "")
        if len(chain)>=2 and chain[0]=="subprocess" and leaf in _SUBPROCESS:
            add("PROCESS_SPAWN",node); continue
        if isinstance(node.func,ast.Name) and node.func.id=="_ORIGINAL_URLOPEN":
            add("RAW_NETWORK_FALLBACK",node); continue
        if len(chain)>=2 and chain[0]=="shutil" and leaf in _SHUTIL:
            add("FILESYSTEM_MUTATION",node); continue
        if leaf in _FS:
            add("FILESYSTEM_MUTATION",node); continue
        if leaf=="open":
            mode=None
            if node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str): mode=node.args[0].value
            for kw in node.keywords:
                if kw.arg=="mode" and isinstance(kw.value,ast.Constant) and isinstance(kw.value.value,str): mode=kw.value.value
            if mode and any(c in mode for c in "awx+"): add("FILESYSTEM_MUTATION",node)
            continue
        if leaf in _DYNAMIC or (isinstance(node.func,ast.Name) and node.func.id in {"exec","eval","compile"}):
            add("DYNAMIC_CODE_EXECUTION",node); continue
    bridge_optional=('PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR' in source and "if not raw_dir:" in source and "return None" in source)
    if bridge_optional:
        line=next((i for i,x in enumerate(lines,1) if "PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR" in x),0)
        sites.append({"kind":"OPTIONAL_BROKER_BOUNDARY","function":"_external_tool_bridge","line":line,
                      "source":"bridge may return None when no broker is configured"})
    grouped={}
    for row in sites: grouped.setdefault(row["kind"],[]).append(row)
    for rows in grouped.values(): rows.sort(key=lambda r:(r["line"],r["function"]))
    kinds=sorted(grouped)
    repair=[]
    if kinds: repair.append("MANDATORY_MATERIAL_EFFECT_BROKER_OR_VERIFIED_CONFINEMENT")
    if "PROCESS_SPAWN" in grouped: repair.append("NO_DIRECT_PROCESS_SPAWN_OUTSIDE_MEDIATED_BOUNDARY")
    if "RAW_NETWORK_FALLBACK" in grouped: repair.append("NO_RAW_NETWORK_FALLBACK")
    if "FILESYSTEM_MUTATION" in grouped: repair.append("NO_UNBROKERED_DURABLE_FILESYSTEM_MUTATION")
    if "DYNAMIC_CODE_EXECUTION" in grouped: repair.append("NO_UNREGISTERED_DYNAMIC_CODE_EXECUTION")
    if "OPTIONAL_BROKER_BOUNDARY" in grouped: repair.append("BROKER_MUST_BE_MANDATORY_NOT_OPTIONAL")
    return {"schema":SCHEMA,
            "status":"FAIL_CLOSED_UNMEDIATED_EFFECT_SURFACE" if kinds else "PASS",
            "reason":"UNMEDIATED_OR_DYNAMIC_EFFECT_CLASSES_PRESENT" if kinds else "NO_UNMEDIATED_EFFECT_CLASS_FOUND",
            "actual_git_blob_sha":sha,"effect_class_count":len(kinds),
            "effect_site_count":sum(map(len,grouped.values())),"blocking_effect_classes":kinds,
            "effect_sites":grouped,"no_bypass_proven":not kinds,"required_repair_classes":repair,
            "terminal_authority":False,"acceptance_credit_delta":0}

def audit_file(path:Path, expected_git_blob_sha:str|None=None)->dict[str,Any]:
    return audit_source(path.read_text(encoding="utf-8"),expected_git_blob_sha)
