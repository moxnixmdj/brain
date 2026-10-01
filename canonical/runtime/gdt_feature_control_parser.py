"""Typed parser for a bounded textual/OCR GD&T feature-control-frame subset.

Accepts explicit textual names and common OCR-friendly symbols/tokens. Unsupported or
ambiguous notation fails closed. This is notation parsing only, not geometric compliance.
"""
from __future__ import annotations
import re
from typing import Any

SCHEMA="BRAIN_GDT_FCF_PARSER_V1"

CHAR_MAP={
    "POSITION":"POSITION","TRUE POSITION":"POSITION","⌖":"POSITION",
    "PERPENDICULARITY":"PERPENDICULARITY","PERP":"PERPENDICULARITY","⊥":"PERPENDICULARITY",
    "PARALLELISM":"PARALLELISM","PARALLEL":"PARALLELISM","∥":"PARALLELISM",
    "FLATNESS":"FLATNESS",
    "STRAIGHTNESS":"STRAIGHTNESS",
    "CIRCULARITY":"CIRCULARITY","ROUNDNESS":"CIRCULARITY",
    "CYLINDRICITY":"CYLINDRICITY",
    "PROFILE OF A LINE":"PROFILE_LINE","PROFILE LINE":"PROFILE_LINE",
    "PROFILE OF A SURFACE":"PROFILE_SURFACE","PROFILE SURFACE":"PROFILE_SURFACE",
    "CIRCULAR RUNOUT":"CIRCULAR_RUNOUT","RUNOUT":"CIRCULAR_RUNOUT",
    "TOTAL RUNOUT":"TOTAL_RUNOUT",
}
MATERIAL={"M":"MMC","MMC":"MMC","L":"LMC","LMC":"LMC","S":"RFS","RFS":"RFS"}

def _norm(s:str)->str:
    s=s.replace("⌀","DIA ").replace("Ø","DIA ").replace("⌀","DIA ")
    s=re.sub(r"[\[\]{}]","|",s)
    s=re.sub(r"\s+"," ",s.strip().upper())
    return s

def parse_feature_control_frame(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"EMPTY"}
    s=_norm(text)
    parts=[p.strip() for p in re.split(r"[|;]",s) if p.strip()]
    if len(parts)<2:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"FCF_FIELDS_INSUFFICIENT","raw":s}
    characteristic=CHAR_MAP.get(parts[0])
    if characteristic is None:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"UNSUPPORTED_CHARACTERISTIC","raw":s}
    tol=parts[1]
    dia=False
    if tol.startswith("DIA "):
        dia=True; tol=tol[4:].strip()
    m=re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(?:\s*(MM|CM|M|IN))?(?:\s+(MMC|LMC|RFS|M|L|S))?",tol)
    if not m:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"TOLERANCE_FIELD_UNSUPPORTED","raw":s}
    value=float(m.group(1)); units=m.group(2).lower() if m.group(2) else None
    material=MATERIAL.get(m.group(3)) if m.group(3) else None
    datums=[]
    for field in parts[2:]:
        dm=re.fullmatch(r"([A-Z][A-Z0-9]*)(?:\s+(MMC|LMC|RFS|M|L|S))?",field)
        if not dm:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"DATUM_FIELD_UNSUPPORTED","field":field,"raw":s}
        datums.append({"datum":dm.group(1),"material_condition":MATERIAL.get(dm.group(2)) if dm.group(2) else None})
    return {"schema":SCHEMA,"status":"PARSED","characteristic":characteristic,
            "tolerance":{"value":value,"diametrical_zone":dia,"units":units,"material_condition":material},
            "datums":datums,"terminal_authority":False,
            "scope":"BOUNDED_TEXTUAL_OR_OCR_FEATURE_CONTROL_FRAME_NOTATION_ONLY"}

def parse_datum(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"EMPTY"}
    s=_norm(text)
    m=re.fullmatch(r"(?:DATUM\s+)?([A-Z][A-Z0-9]*)",s)
    if not m:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"UNSUPPORTED_DATUM","raw":s}
    return {"schema":SCHEMA,"status":"PARSED","kind":"datum","datum":m.group(1),"terminal_authority":False}
