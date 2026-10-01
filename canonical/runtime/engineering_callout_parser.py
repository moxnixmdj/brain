"""Parse explicit engineering dimension callouts. Unsupported syntax fails closed."""
from __future__ import annotations
import re

SCHEMA="BRAIN_ENGINEERING_CALLOUT_PARSE_V1"

def _clean(text):
    return " ".join(text.strip().replace("\u00d8","DIA ").replace("\u2300","DIA ").replace("\u00b1","+/-").replace("\u00d7","x").split())

def parse_callout(text):
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"EMPTY"}
    s=_clean(text)
    m=re.fullmatch(r"M([0-9]+(?:\.[0-9]+)?)(?:[xX]([0-9]+(?:\.[0-9]+)?))?",s,re.I)
    if m:
        return {"schema":SCHEMA,"status":"PARSED","kind":"thread","standard":"ISO_METRIC","major_diameter":float(m.group(1)),"pitch":float(m.group(2)) if m.group(2) else None,"units":"mm","terminal_authority":False}
    m=re.fullmatch(r"DIA\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|in)?",s,re.I)
    if m:
        v=float(m.group(1)); return {"schema":SCHEMA,"status":"PARSED","kind":"diameter","value":v,"radius":v/2.0,"units":m.group(2).lower() if m.group(2) else None,"terminal_authority":False}
    m=re.fullmatch(r"R\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|in)?",s,re.I)
    if m:
        return {"schema":SCHEMA,"status":"PARSED","kind":"radius","value":float(m.group(1)),"units":m.group(2).lower() if m.group(2) else None,"terminal_authority":False}
    m=re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*\+/-\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|in)?",s,re.I)
    if m:
        v=float(m.group(1)); t=float(m.group(2)); return {"schema":SCHEMA,"status":"PARSED","kind":"symmetric_tolerance","value":v,"upper_deviation":t,"lower_deviation":-t,"units":m.group(3).lower() if m.group(3) else None,"terminal_authority":False}
    m=re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*\+([0-9]+(?:\.[0-9]+)?)\s*/\s*-([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|in)?",s,re.I)
    if m:
        return {"schema":SCHEMA,"status":"PARSED","kind":"asymmetric_tolerance","value":float(m.group(1)),"upper_deviation":float(m.group(2)),"lower_deviation":-float(m.group(3)),"units":m.group(4).lower() if m.group(4) else None,"terminal_authority":False}
    m=re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|m|in)",s,re.I)
    if m:
        return {"schema":SCHEMA,"status":"PARSED","kind":"linear","value":float(m.group(1)),"units":m.group(2).lower(),"terminal_authority":False}
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","error":"UNSUPPORTED_OR_AMBIGUOUS","raw":s}
