#!/usr/bin/env python3
"""Fail-closed inversion of frozen public IFBench description templates."""
from __future__ import annotations
import ast, json, re
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_LIVEBENCH_PUBLIC_DESCRIPTION_INVERTER_V1"
PINNED_COMMIT="8f8e5c381a16e3f24257776edd53471fe86f8091"
_NUMERIC={"N","percentage","small_n","min_words","max_words","n","m","n_start","n_end"}
_FIELD=re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

def _registry()->dict[str,Any]:
    path=Path(__file__).with_name("livebench_public_description_templates_v1.json")
    return json.loads(path.read_text(encoding="utf-8"))

def _pattern(template:str)->re.Pattern[str]:
    out=[]; pos=0
    fields=list(_FIELD.finditer(template))
    for i,m in enumerate(fields):
        out.append(re.escape(template[pos:m.start()]))
        name=m.group(1)
        body=r"-?\d+(?:\.\d+)?" if name in _NUMERIC else (r".+?" if i < len(fields)-1 or template[m.end():] else r".+")
        out.append(f"(?P<{name}>{body})")
        pos=m.end()
    out.append(re.escape(template[pos:]))
    return re.compile("".join(out),re.DOTALL)

def _coerce(name:str,raw:str)->Any:
    v=raw.strip()
    if name in _NUMERIC:
        x=float(v); return int(x) if x.is_integer() else x
    if name=="options":
        try:
            x=ast.literal_eval(v)
            if isinstance(x,(list,tuple)): return list(x)
        except Exception: pass
    return v

def recover(prompt:str)->dict[str,Any]:
    text=str(prompt or "")
    if not text:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"PROMPT_REQUIRED","matches":[]}
    found=[]
    for iid,item in _registry()["instructions"].items():
        for template in item["templates"]:
            for m in _pattern(template).finditer(text):
                kwargs={k:_coerce(k,v) for k,v in m.groupdict().items()}
                unresolved=list(item.get("unresolved_kwargs") or [])
                for k in unresolved: kwargs.pop(k,None)
                found.append({"instruction_id":iid,"checker_class":item["checker_class"],"template":template,
                              "description":m.group(0),"kwargs":kwargs,"unresolved_kwargs":unresolved,
                              "span_start":m.start(),"span_end":m.end()})
    found.sort(key=lambda x:(x["span_start"],x["span_end"],x["instruction_id"]))
    status="NO_PUBLIC_DESCRIPTION_MATCH" if not found else ("PARTIAL__EXPLICIT_RESIDUALS" if any(x["unresolved_kwargs"] for x in found) else "PASS__VISIBLE_KWARGS_RECOVERED")
    return {"schema":SCHEMA,"status":status,"pinned_commit":PINNED_COMMIT,"model_dependency_count":0,
            "network_used":False,"terminal_data_used":False,"row_lookup_used":False,"matches":found,
            "hard_nonclaim":"DESCRIPTION_INVERSION_ONLY__NO_WITNESS_OR_SCORE_CLAIM"}

def run(args:dict[str,Any],root=None)->dict[str,Any]:
    return recover(str((args or {}).get("prompt") or ""))
