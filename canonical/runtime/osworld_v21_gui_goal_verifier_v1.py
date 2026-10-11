"""Deterministic current-state GUI goal verifier for high-confidence predicates.

The verifier accepts only simple instruction forms whose truth can be read
directly from the current accessibility tree. It never infers task IDs, hidden
evaluator state, or semantic intent beyond the explicit predicate.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_GUI_GOAL_EVIDENCE_V1"


def _norm(value:Any)->str:
    return re.sub(r"\s+"," ",unicodedata.normalize("NFKC",str(value or "")).casefold()).strip()


def _local(name:str)->str:
    return name.rsplit("}",1)[-1] if "}" in name else name


def _attrs(node:ET.Element)->dict[str,str]:
    return {_local(str(k)).casefold():str(v) for k,v in node.attrib.items()}


def _label(node:ET.Element)->str:
    name=str(node.get("name") or "").strip()
    text=str(node.text or "").strip()
    if name and text and _norm(name)!=_norm(text):
        return name+" "+text
    return name or text


def _visible(node:ET.Element)->bool:
    a=_attrs(node)
    return a.get("visible","true").casefold()!="false" and a.get("showing","true").casefold()!="false"


def _parse(xml_text:Any)->list[dict[str,Any]]:
    if not isinstance(xml_text,str) or not xml_text.strip():
        return []
    try:
        root=ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out=[]
    for node in root.iter():
        if not _visible(node):
            continue
        label=_label(node)
        if not label:
            continue
        out.append({
            "tag":_local(str(node.tag)).casefold(),
            "label":label,
            "attrs":_attrs(node),
        })
    return out


def _strip_target(value:str)->str:
    return value.strip().strip(" .,:;").strip('"\'“”').strip()


def _predicate(instruction:str)->dict[str,Any]|None:
    s=instruction.strip()

    m=re.fullmatch(
        r"(check|select|enable|uncheck|deselect|disable)\s+(?:the\s+)?(.+?)[.!]?",
        s,
        re.I,
    )
    if m:
        verb=m.group(1).casefold()
        target=_strip_target(m.group(2))
        if not target:
            return None
        if verb in {"check","uncheck"}:
            attr="checked"
        elif verb in {"select","deselect"}:
            attr="selected"
        else:
            attr="enabled"
        expected=verb in {"check","select","enable"}
        return {"kind":"BOOL_ATTR","target":target,"attr":attr,"expected":expected}

    m=re.fullmatch(r"turn\s+(on|off)\s+(?:the\s+)?(.+?)[.!]?",s,re.I)
    if m:
        target=_strip_target(m.group(2))
        if not target:
            return None
        return {
            "kind":"BOOL_ATTR","target":target,"attr":"checked",
            "expected":m.group(1).casefold()=="on",
        }

    m=re.fullmatch(
        r"(?:set|change)\s+(?:the\s+)?(.+?)\s+(?:to|as)\s+[\"“](.+?)[\"”][.!]?",
        s,
        re.I,
    )
    if m:
        field=_strip_target(m.group(1)); value=m.group(2)
        if field and value:
            return {"kind":"VALUE","target":field,"expected":value}

    m=re.fullmatch(
        r"(?:type|enter|input)\s+[\"“](.+?)[\"”]\s+(?:in|into)\s+(?:the\s+)?(.+?)[.!]?",
        s,
        re.I,
    )
    if m:
        value=m.group(1); field=_strip_target(m.group(2))
        if field and value:
            return {"kind":"VALUE","target":field,"expected":value}

    if "http://" not in s.casefold() and "https://" not in s.casefold():
        m=re.fullmatch(r"open\s+(?:the\s+)?(.+?)[.!]?",s,re.I)
        if m:
            target=_strip_target(m.group(1))
            if target:
                return {"kind":"ACTIVE_WINDOW","target":target}

    return None


def _bool(value:Any)->bool|None:
    v=_norm(value)
    if v in {"true","1","yes","on","checked","selected","enabled"}:
        return True
    if v in {"false","0","no","off","unchecked","unselected","disabled"}:
        return False
    return None


def verify_gui_goal(state:Mapping[str,Any])->dict[str,Any]|None:
    if not isinstance(state,Mapping):
        return None
    instruction=state.get("instruction")
    current_sha=state.get("screenshot_sha256")
    if not isinstance(instruction,str) or not instruction.strip():
        return None
    if not isinstance(current_sha,str) or len(current_sha)!=64:
        return None
    pred=_predicate(instruction)
    if pred is None:
        return None

    nodes=_parse(state.get("a11y_tree"))
    target=_norm(pred["target"])
    matches=[n for n in nodes if _norm(n["label"])==target]
    if len(matches)!=1:
        return None
    node=matches[0]

    observed=None
    passed=False
    if pred["kind"]=="BOOL_ATTR":
        observed=_bool(node["attrs"].get(pred["attr"]))
        passed=observed is pred["expected"]
    elif pred["kind"]=="VALUE":
        observed=node["attrs"].get("value")
        passed=isinstance(observed,str) and observed==pred["expected"]
    elif pred["kind"]=="ACTIVE_WINDOW":
        active=_bool(node["attrs"].get("active"))
        observed=active
        passed=active is True
    else:
        return None

    if not passed:
        return None

    predicate_sha=hashlib.sha256(
        repr((pred,node["tag"],node["label"],observed)).encode("utf-8")
    ).hexdigest()
    return {
        "schema":SCHEMA,
        "pass":True,
        "basis":"EXPLICIT_CURRENT_A11Y_PREDICATE",
        "current_screenshot_sha256":current_sha,
        "predicate":pred,
        "observed":observed,
        "predicate_sha256":predicate_sha,
        "task_specific_policy_data":False,
        "external_model_dependency":False,
    }
