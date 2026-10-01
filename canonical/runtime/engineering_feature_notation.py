"""Bounded deterministic parser for compound engineering feature callouts and GD&T text.

This extends the narrow scalar callout parser into explicit, machine-checkable
feature semantics. It intentionally accepts only a frozen grammar. Unsupported
notation fails closed.

Examples:
  2X DIA 10 THRU
  DIA 20 CBORE 30 DEPTH 5
  DIA 10 CSK 20 X 90 DEG
  M8x1.25 DEPTH 12
  POSITION | DIA 0.10 | A | B | C
  FLATNESS | 0.05
  PERPENDICULARITY | 0.10 | A
  DATUM | A
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA="BRAIN_ENGINEERING_FEATURE_NOTATION_V1"

_NUM=r"(?:\d+(?:\.\d+)?|\.\d+)"
_UNIT=r"(?:mm|cm|m|in)"
_GDT={
    "POSITION":"position",
    "TRUE POSITION":"position",
    "FLATNESS":"flatness",
    "STRAIGHTNESS":"straightness",
    "PERPENDICULARITY":"perpendicularity",
    "PARALLELISM":"parallelism",
    "CIRCULARITY":"circularity",
    "ROUNDNESS":"circularity",
    "CYLINDRICITY":"cylindricity",
    "PROFILE OF A LINE":"profile_line",
    "PROFILE LINE":"profile_line",
    "PROFILE OF A SURFACE":"profile_surface",
    "PROFILE SURFACE":"profile_surface",
    "CIRCULAR RUNOUT":"circular_runout",
    "TOTAL RUNOUT":"total_runout",
}

def _clean(text:str)->str:
    s=text.strip().upper()
    s=s.replace("Ø","DIA ").replace("⌀","DIA ")
    s=s.replace("⌴"," CBORE ").replace("⌵"," CSK ")
    s=s.replace("°"," DEG ")
    s=re.sub(r"\s+"," ",s)
    return s.strip()

def _num(s:str)->float:
    return float(s)

def _split_unit(s:str)->tuple[float,str|None]|None:
    m=re.fullmatch(rf"({_NUM})\s*({_UNIT})?",s,re.I)
    if not m:
        return None
    return float(m.group(1)), (m.group(2).lower() if m.group(2) else None)

def parse_feature_notation(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"EMPTY"}
    s=_clean(text)

    # Datum declaration.
    m=re.fullmatch(r"DATUM\s*(?:\|\s*)?([A-Z][A-Z0-9]?)",s)
    if m:
        return {
            "schema":SCHEMA,"status":"PARSED","kind":"datum",
            "datum":m.group(1),"terminal_authority":False
        }

    # GD&T feature control frame expressed in OCR-friendly text with | separators.
    if "|" in s:
        cells=[c.strip() for c in s.split("|") if c.strip()]
        if not cells:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"EMPTY_FRAME"}
        op=_GDT.get(cells[0])
        if op:
            if len(cells)<2:
                return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"GDT_TOLERANCE_MISSING"}
            tolcell=cells[1]
            diam=False
            if tolcell.startswith("DIA "):
                diam=True
                tolcell=tolcell[4:].strip()
            val=_split_unit(tolcell)
            if val is None:
                return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"GDT_TOLERANCE_INVALID"}
            tol,unit=val
            datums=cells[2:]
            if any(not re.fullmatch(r"[A-Z][A-Z0-9]?",d) for d in datums):
                return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"GDT_DATUM_INVALID"}
            if op in {"flatness","straightness","circularity","cylindricity"} and datums:
                return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"DATUM_NOT_ALLOWED_FOR_FORM_CONTROL"}
            if op in {"perpendicularity","parallelism","circular_runout","total_runout"} and not datums:
                return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"DATUM_REQUIRED"}
            return {
                "schema":SCHEMA,"status":"PARSED","kind":"gdt",
                "characteristic":op,"tolerance":tol,"diametrical_zone":diam,
                "units":unit,"datums":datums,"terminal_authority":False
            }

    # Optional quantity prefix.
    quantity=1
    qm=re.match(r"^(\d+)\s*X\s+",s)
    if qm:
        quantity=int(qm.group(1))
        if quantity<=0:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"QUANTITY_INVALID"}
        s=s[qm.end():].strip()

    # Metric thread with optional depth.
    m=re.fullmatch(rf"M({_NUM})(?:X({_NUM}))?(?:\s+DEPTH\s+({_NUM})\s*({_UNIT})?)?",s)
    if m:
        return {
            "schema":SCHEMA,"status":"PARSED","kind":"thread","standard":"ISO_METRIC",
            "quantity":quantity,"major_diameter":_num(m.group(1)),
            "pitch":(_num(m.group(2)) if m.group(2) else None),
            "depth":(_num(m.group(3)) if m.group(3) else None),
            "units":(m.group(4).lower() if m.group(4) else "mm"),
            "terminal_authority":False
        }

    # Diameter feature with optional THRU/DEPTH/CBORE/CSK.
    m=re.fullmatch(
        rf"DIA\s*({_NUM})\s*({_UNIT})?"
        rf"(?:\s+(THRU)|\s+DEPTH\s+({_NUM})\s*({_UNIT})?)?"
        rf"(?:\s+CBORE\s+({_NUM})\s*({_UNIT})?(?:\s+DEPTH\s+({_NUM})\s*({_UNIT})?)?)?"
        rf"(?:\s+CSK\s+({_NUM})\s*({_UNIT})?\s+X\s+({_NUM})\s*DEG)?",
        s,
    )
    if m:
        base=float(m.group(1)); base_unit=(m.group(2).lower() if m.group(2) else None)
        through=bool(m.group(3))
        depth=float(m.group(4)) if m.group(4) else None
        depth_unit=m.group(5).lower() if m.group(5) else base_unit
        cbore_d=float(m.group(6)) if m.group(6) else None
        cbore_unit=m.group(7).lower() if m.group(7) else base_unit
        cbore_depth=float(m.group(8)) if m.group(8) else None
        cbore_depth_unit=m.group(9).lower() if m.group(9) else base_unit
        csk_d=float(m.group(10)) if m.group(10) else None
        csk_unit=m.group(11).lower() if m.group(11) else base_unit
        csk_angle=float(m.group(12)) if m.group(12) else None
        if through and depth is not None:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"THRU_AND_DEPTH_CONFLICT"}
        return {
            "schema":SCHEMA,"status":"PARSED","kind":"hole_or_cylindrical_feature",
            "quantity":quantity,"diameter":base,"units":base_unit,
            "through":through,"depth":depth,"depth_units":depth_unit,
            "counterbore":(
                {"diameter":cbore_d,"units":cbore_unit,"depth":cbore_depth,"depth_units":cbore_depth_unit}
                if cbore_d is not None else None
            ),
            "countersink":(
                {"diameter":csk_d,"units":csk_unit,"angle_deg":csk_angle}
                if csk_d is not None else None
            ),
            "terminal_authority":False
        }

    # Radius with optional quantity.
    m=re.fullmatch(rf"R\s*({_NUM})\s*({_UNIT})?",s)
    if m:
        return {
            "schema":SCHEMA,"status":"PARSED","kind":"radius_feature",
            "quantity":quantity,"radius":float(m.group(1)),
            "units":m.group(2).lower() if m.group(2) else None,
            "terminal_authority":False
        }

    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED",
        "error":"UNSUPPORTED_OR_AMBIGUOUS_NOTATION","raw":s
    }
