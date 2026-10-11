"""Structured spreadsheet/presentation policy overlay V4.

Adds high-confidence observation and advanced Calc/Impress operations already
present in the typed registry. Unknown requests fall through to V3.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_app_policy_overlay_v3 import (
    decide as base_decide,
    _finish_or_candidate,
)
from canonical.runtime.osworld_v21_app_policy_overlay_v2 import (
    _active_app_name,
    _app,
    _app_op,
)

_CHART_TYPES={"bar","column","line","pie","scatter","area"}
_LEGEND_POSITIONS={"top","bottom","left","right","none"}

def _quoted(text:str)->list[str]:
    vals=re.findall(r'["“]([^"”]+)["”]',text)
    vals.extend(re.findall(r"'([^']+)'",text))
    return [x.strip() for x in vals if x.strip()]

def _letters_csv(value:str)->list[str]:
    out=[]
    for item in re.split(r"\s*,\s*|\s+",value.strip()):
        if not item:
            continue
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9 _.-]*",item):
            out.append(item)
        else:
            return []
    return out

def _calc(instruction:str):
    low=instruction.casefold()

    if re.search(r"\b(check|show|get|inspect|review)\b.*\b(workbook|sheets?|active sheet)\b",low):
        return _app_op("libreoffice_calc","get_workbook_info",{})

    m=re.search(r"\b(?:get|read|show|inspect)\s+(?:the\s+)?(?:data\s+in\s+)?column\s+([A-Z]+)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_calc","get_column_data",{"column_name":m.group(1).upper()})

    m=re.search(r"\bset\s+column\s+([A-Z]+)\s+values?\s+to\s+(\[[^\n]+\])",instruction,re.I)
    if m:
        try:
            values=json.loads(m.group(2))
        except Exception:
            values=None
        if isinstance(values,list) and len(values)<=256:
            args={"column_name":m.group(1).upper(),"data":values}
            start=re.search(r"\bstarting\s+(?:at\s+)?row\s+(\d+)\b",instruction,re.I)
            if start: args["start_index"]=int(start.group(1))
            return _app_op("libreoffice_calc","set_column_values",args)

    m=re.search(r"\bset\s+(?:a\s+)?validation\s+list\s+(?:for\s+)?column\s+([A-Z]+)\s+to\s+(.+?)(?:[.;]|$)",instruction,re.I)
    if m:
        values=_quoted(m.group(2))
        if len(values)>=1:
            return _app_op("libreoffice_calc","set_validation_list",{"column_name":m.group(1).upper(),"values":values})

    m=re.search(r"\breorder\s+columns?\s+(?:to\s+)?(.+?)(?:[.;]|$)",instruction,re.I)
    if m:
        cols=[x.upper() for x in _letters_csv(m.group(1)) if re.fullmatch(r"[A-Za-z]+",x)]
        if len(cols)>=2:
            return _app_op("libreoffice_calc","reorder_columns",{"column_order":cols})

    m=re.search(r"\bcreate\s+(?:a\s+)?(bar|column|line|pie|scatter|area)\s+chart\s+(?:from|using)\s+([A-Z]+\d+:[A-Z]+\d+)",instruction,re.I)
    if m:
        args={"chart_type":m.group(1).lower(),"data_range":m.group(2).upper()}
        title=re.search(r"\b(?:titled|title)\s+[\x22\x27]([^\x22\x27]+)[\x22\x27]",instruction,re.I)
        if title: args["title"]=title.group(1)
        xaxis=re.search(r"\bx[- ]axis\s+(?:title\s+)?[\x22\x27]([^\x22\x27]+)[\x22\x27]",instruction,re.I)
        yaxis=re.search(r"\by[- ]axis\s+(?:title\s+)?[\x22\x27]([^\x22\x27]+)[\x22\x27]",instruction,re.I)
        if xaxis: args["x_axis_title"]=xaxis.group(1)
        if yaxis: args["y_axis_title"]=yaxis.group(1)
        return _app_op("libreoffice_calc","create_chart",args)

    m=re.search(
        r"\bcreate\s+(?:a\s+)?pivot\s+table\s+[\x22\x27]([^\x22\x27]+)[\x22\x27]\s+"
        r"(?:from|using)\s+sheet\s+[\x22\x27]([^\x22\x27]+)[\x22\x27].*?"
        r"value\s+fields?\s+([A-Za-z0-9_, .-]+?)(?:\s+(?:at|using|with)\b|[.;]|$)",
        instruction,re.I,
    )
    if m:
        values=_letters_csv(m.group(3))
        if values:
            args={"source_sheet":m.group(2),"table_name":m.group(1),"value_fields":values}
            target=re.search(r"\bat\s+([A-Z]+\d+)\b",instruction,re.I)
            if target: args["target_cell"]=target.group(1).upper()
            agg=re.search(r"\b(sum|count|average|min|max)\b",instruction,re.I)
            if agg: args["aggregation_function"]=agg.group(1).lower()
            rows=re.search(r"\brow\s+fields?\s+([A-Za-z0-9_, .-]+?)(?:\s+(?:column|value|at|using|with)\b|[.;]|$)",instruction,re.I)
            cols=re.search(r"\bcolumn\s+fields?\s+([A-Za-z0-9_, .-]+?)(?:\s+(?:row|value|at|using|with)\b|[.;]|$)",instruction,re.I)
            if rows:
                parsed=_letters_csv(rows.group(1))
                if parsed: args["row_fields"]=parsed
            if cols:
                parsed=_letters_csv(cols.group(1))
                if parsed: args["col_fields"]=parsed
            return _app_op("libreoffice_calc","create_pivot_table",args)

    m=re.search(r"\bset\s+(?:the\s+)?chart\s+legend\s+(?:position\s+)?(?:to|at)\s+(top|bottom|left|right|none)\b",instruction,re.I)
    if m:
        return _app_op("libreoffice_calc","set_chart_legend_position",{"position":m.group(1).lower()})
    return None

def _impress(instruction:str):
    low=instruction.casefold()
    if re.search(r"\b(how many|count|number of|get|show)\b.*\bslides?\b",low):
        return _app_op("libreoffice_impress","get_slide_count",{})
    return None

def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    instruction=state.get("instruction")
    if not isinstance(instruction,str) or not instruction.strip():
        return base_decide(state)
    active=_app(_active_app_name(state.get("a11y_tree")))
    candidate=None
    if active=="libreoffice_calc":
        candidate=_calc(instruction)
    elif active=="libreoffice_impress":
        candidate=_impress(instruction)
    if candidate is not None:
        return _finish_or_candidate(state,candidate)
    return base_decide(state)
