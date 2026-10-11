"""Successor generic app-policy overlay V3.

Adds high-confidence document/spreadsheet/presentation transformations already
present in the frozen typed app-operation registry. Unknown or underspecified
requests fall through to V2 without guessing.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_app_policy_overlay_v2 import (
    decide as base_decide,
    _active_app_name,
    _app,
    _app_op,
    _first_path,
    _latest_successful_app_operation,
    _candidate_action,
    _same_app_operation,
)

_FORMAT_TYPES={"general","number","currency","accounting","date","time","percentage","fraction","scientific","text"}
_POSITIONS={"left","right","center","top","bottom","top-left","top-right","bottom-left","bottom-right"}

def _finish_or_candidate(state:Mapping[str,Any],candidate:Mapping[str,Any]):
    action=_candidate_action(candidate)
    submitted,result=_latest_successful_app_operation(state)
    if action is not None and submitted is not None and result is not None and _same_app_operation(action,submitted):
        return {
            "response":"app operation postcondition receipted",
            "actions":[{"type":"DONE"}],
            "_policy_receipt":{
                "route":"GENERIC_APP_OPERATION_VERIFIED_V3",
                "app":action.get("app"),"operation":action.get("operation"),
                "task_specific_policy_data":False,"external_model_dependency":False,
            },
        }
    return candidate

def _writer(instruction:str):
    low=instruction.casefold()
    if "uppercase" in low or "lowercase" in low:
        case_type="uppercase" if "uppercase" in low else "lowercase"
        m=re.search(r'["“]([^"”]+)["”]|\'([^\']+)\'',instruction)
        if m:
            text=(m.group(1) or m.group(2)).strip()
            if text:
                return _app_op("libreoffice_writer","change_text_case",{
                    "case_type":case_type,"pattern":re.escape(text)
                })
    return None

def _calc(instruction:str):
    low=instruction.casefold()

    m=re.search(r"\bfreeze\s+(?:(\d+)\s+rows?)?(?:\s*(?:and|,)?\s*)?(?:(\d+)\s+columns?)?\b",instruction,re.I)
    if m and (m.group(1) or m.group(2)):
        args={}
        if m.group(1): args["rows"]=int(m.group(1))
        if m.group(2): args["columns"]=int(m.group(2))
        return _app_op("libreoffice_calc","freeze_panes",args)

    m=re.search(r"\bcopy\s+(?:the\s+)?sheet\s+[\x22\x27]?([^\x22\x27;]+?)[\x22\x27]?(?:\s+(?:to|as)\s+[\x22\x27]?([^\x22\x27;]+?)[\x22\x27]?)?(?:[.;]|$)",instruction,re.I)
    if m:
        args={"source_sheet":m.group(1).strip()}
        if m.group(2): args["new_sheet_name"]=m.group(2).strip()
        return _app_op("libreoffice_calc","copy_sheet",args)

    m=re.search(r"\b(?:set|format)\s+([A-Z]+\d+:[A-Z]+\d+)\s+(?:to|as|with)\s+(general|number|currency|accounting|date|time|percentage|fraction|scientific|text)(?:\s+format)?",instruction,re.I)
    if m:
        args={"range_str":m.group(1).upper(),"format_type":m.group(2).lower()}
        d=re.search(r"(\d+)\s+decimal\s+places?",instruction,re.I)
        if d: args["decimal_places"]=int(d.group(1))
        return _app_op("libreoffice_calc","set_number_format",args)

    m=re.search(r"\b(?:autofit|auto-fit)\s+columns?\s+([A-Z]+(?::[A-Z]+)?)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_calc","adjust_column_width",{"columns":m.group(1).upper(),"autofit":True})
    m=re.search(r"\b(?:set|adjust)\s+columns?\s+([A-Z]+(?::[A-Z]+)?)\s+(?:width\s+)?(?:to\s+)?(\d+(?:\.\d+)?)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_calc","adjust_column_width",{"columns":m.group(1).upper(),"width":float(m.group(2))})

    m=re.search(r"\b(?:autofit|auto-fit)\s+rows?\s+(\d+(?::\d+)?)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_calc","adjust_row_height",{"rows":m.group(1),"autofit":True})
    m=re.search(r"\b(?:set|adjust)\s+rows?\s+(\d+(?::\d+)?)\s+(?:height\s+)?(?:to\s+)?(\d+(?:\.\d+)?)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_calc","adjust_row_height",{"rows":m.group(1),"height":float(m.group(2))})

    m=re.search(r"\b(?:make|format)\s+([A-Z]+\d+:[A-Z]+\d+)\s+(.+?)(?:[.;]|$)",instruction,re.I)
    if m:
        args={"range_str":m.group(1).upper()}
        spec=m.group(2).casefold()
        if "bold" in spec: args["bold"]=True
        am=re.search(r"\b(left|center|right)\b",spec)
        if am: args["alignment"]=am.group(1)
        bg=re.search(r"background(?:\s+color)?\s+(#[0-9a-fA-F]{6})",m.group(2),re.I)
        if bg: args["background_color"]=bg.group(1)
        fc=re.search(r"(?:font|text)(?:\s+color)?\s+(#[0-9a-fA-F]{6})",m.group(2),re.I)
        if fc: args["font_color"]=fc.group(1)
        if len(args)>1:
            return _app_op("libreoffice_calc","format_range",args)

    # Highlight only when no color is requested, preserving the tool default.
    m=re.search(r"\bhighlight\s+([A-Z]+\d+:[A-Z]+\d+)\s*$",instruction.strip(),re.I)
    if m:
        return _app_op("libreoffice_calc","highlight_range",{"range_str":m.group(1).upper()})
    return None

def _impress(instruction:str):
    low=instruction.casefold()

    m=re.search(r"\bset\s+(?:the\s+)?font\s+(?:on|for)\s+slide\s+(\d+)\s+(?:to|as)\s+([^,.;]+)",instruction,re.I)
    if m:
        return _app_op("libreoffice_impress","set_slide_font",{"slide_index":int(m.group(1)),"font_name":m.group(2).strip()})

    m=re.search(r"\b(?:make|set)\s+(?:box|textbox)\s+(\d+)\s+(?:on|in)\s+slide\s+(\d+)\s+(.+?)(?:[.;]|$)",instruction,re.I)
    if m:
        spec=m.group(3).casefold()
        args={"slide_index":int(m.group(2)),"box_index":int(m.group(1))}
        if "bold" in spec: args["bold"]=True
        if "italic" in spec: args["italic"]=True
        if "underline" in spec: args["underline"]=True
        if len(args)>2:
            return _app_op("libreoffice_impress","set_style",args)

    m=re.search(r"\bset\s+(?:the\s+)?text\s+color\s+(?:of|for)\s+(?:box|textbox)\s+(\d+)\s+(?:on|in)\s+slide\s+(\d+)\s+(?:to|as)\s+([^,.;]+)",instruction,re.I)
    if m:
        return _app_op("libreoffice_impress","set_text_color",{"slide_index":int(m.group(2)),"box_index":int(m.group(1)),"color":m.group(3).strip()})

    m=re.search(r"\bset\s+(?:the\s+)?background\s+color\s+(?:of|for)\s+(?:box|textbox)\s+(\d+)\s+(?:on|in)\s+slide\s+(\d+)\s+(?:to|as)\s+([^,.;]+)",instruction,re.I)
    if m:
        return _app_op("libreoffice_impress","set_background_color",{"slide_index":int(m.group(2)),"box_index":int(m.group(1)),"color":m.group(3).strip()})

    m=re.search(r"\bdelete\s+(?:box|textbox)\s+(\d+)\s+(?:from|on|in)\s+slide\s+(\d+)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_impress","delete_content",{"slide_index":int(m.group(2)),"box_index":int(m.group(1))})

    m=re.search(r"\bposition\s+(?:box|textbox|image)\s+(\d+)\s+(?:on|in)\s+slide\s+(\d+)\s+(?:at|to)?\s*(top-left|top-right|bottom-left|bottom-right|left|right|center|top|bottom)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_impress","position_box",{"slide_index":int(m.group(2)),"box_index":int(m.group(1)),"position":m.group(3).lower()})

    m=re.search(r"\balign\s+(?:box|textbox)\s+(\d+)\s+(?:on|in)\s+slide\s+(\d+)\s+(?:to\s+)?(left|center|right|justify)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_impress","set_textbox_alignment",{"slide_index":int(m.group(2)),"box_index":int(m.group(1)),"alignment":m.group(3).lower()})

    m=re.search(r"\bset\s+slide\s+(\d+)\s+background\s+(?:to|as)\s+([^,.;]+)",instruction,re.I)
    if m:
        return _app_op("libreoffice_impress","set_slide_background",{"slide_index":int(m.group(1)),"color":m.group(2).strip()})

    if ("add slide numbers" in low or "insert slide numbers" in low):
        return _app_op("libreoffice_impress","set_slide_number",{})

    if "export" in low and ("png" in low or "jpeg" in low or "jpg" in low or "gif" in low or "bmp" in low or "tiff" in low):
        path=_first_path(instruction)
        if path:
            fm=re.search(r"\b(png|jpeg|jpg|gif|bmp|tiff)\b",instruction,re.I)
            if fm:
                args={"file_path":path,"format":fm.group(1).lower()}
                sm=re.search(r"slide\s+(\d+)",instruction,re.I)
                if sm: args["slide_index"]=int(sm.group(1))
                return _app_op("libreoffice_impress","export_to_image",args)
    return None

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    instruction=state.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip():
        return base_decide(state)
    active=_app(_active_app_name(state.get("a11y_tree")))
    candidate=None
    if active=="libreoffice_writer":
        candidate=_writer(instruction)
    elif active=="libreoffice_calc":
        candidate=_calc(instruction)
    elif active=="libreoffice_impress":
        candidate=_impress(instruction)
    if candidate is not None:
        return _finish_or_candidate(state,candidate)
    return base_decide(state)
