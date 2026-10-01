"""Bounded dependency-free GD&T feature-control-frame parser.

White-box design donor:
  clay-good/anvilate@c29daa0832bc0f1cf66bfa6549bfa626a87b34a8
  src/anvilate/gdt.py (MIT)

This is a clean Brain-local rewrite of the small typed grammar/legality slice
needed by M1A. It is not a standards conformance engine and never verifies that
a manufactured feature satisfies the parsed tolerance.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA="BRAIN_GDT_FEATURE_CONTROL_FRAME_V1"

CHARACTERISTICS={
    "—":("straightness","form"),
    "STRAIGHTNESS":("straightness","form"),
    "▱":("flatness","form"),
    "FLATNESS":("flatness","form"),
    "○":("circularity","form"),
    "CIRCULARITY":("circularity","form"),
    "⌭":("cylindricity","form"),
    "CYLINDRICITY":("cylindricity","form"),
    "⌒":("profile_of_a_line","profile"),
    "PROFILE OF A LINE":("profile_of_a_line","profile"),
    "⌓":("profile_of_a_surface","profile"),
    "PROFILE OF A SURFACE":("profile_of_a_surface","profile"),
    "∠":("angularity","orientation"),
    "ANGULARITY":("angularity","orientation"),
    "⊥":("perpendicularity","orientation"),
    "⟂":("perpendicularity","orientation"),
    "PERPENDICULARITY":("perpendicularity","orientation"),
    "∥":("parallelism","orientation"),
    "PARALLELISM":("parallelism","orientation"),
    "⌖":("position","location"),
    "POSITION":("position","location"),
    "◎":("concentricity","location"),
    "CONCENTRICITY":("concentricity","location"),
    "⌯":("symmetry","location"),
    "SYMMETRY":("symmetry","location"),
    "↗":("circular_runout","runout"),
    "CIRCULAR RUNOUT":("circular_runout","runout"),
    "⌰":("total_runout","runout"),
    "TOTAL RUNOUT":("total_runout","runout"),
}
REMOVED_IN_2018={"concentricity","symmetry"}
DATUM_RULE={"form":"forbidden","profile":"optional","orientation":"required","location":"required","runout":"required"}
EDITION_ALIASES={
    "2009":"ASME Y14.5-2009",
    "ASME Y14.5-2009":"ASME Y14.5-2009",
    "2018":"ASME Y14.5-2018",
    "ASME Y14.5-2018":"ASME Y14.5-2018",
}
FEATURE_TYPES={"surface","feature_of_size"}
NUM=r"(?:\d+(?:\.\d+)?|\.\d+)"
TOL_RE=re.compile(rf"^(?P<diam>[Ø⌀∅])?\s*(?P<value>{NUM})\s*(?P<unit>MM|IN)?(?P<tail>.*)$",re.I)
DATUM_RE=re.compile(r"^(?P<letter>[A-Z]{1,3})(?:\s*(?P<boundary>Ⓜ|MMC|MMB|Ⓛ|LMC|LMB))?$")
MODIFIER_MAP={"Ⓜ":"MMC","MMC":"MMC","Ⓛ":"LMC","LMC":"LMC","Ⓟ":"PROJECTED","PROJECTED":"PROJECTED"}
DATUM_BOUNDARY={"Ⓜ":"MMB","MMC":"MMB","MMB":"MMB","Ⓛ":"LMB","LMC":"LMB","LMB":"LMB"}


def _fail(error: str, raw: str | None=None, **extra: Any) -> dict[str,Any]:
    out={"schema":SCHEMA,"status":"FAIL_CLOSED","error":error,"terminal_authority":False}
    if raw is not None:
        out["raw"]=raw
    out.update(extra)
    return out


def _characteristic(cell: str):
    key=" ".join(cell.strip().upper().split())
    return CHARACTERISTICS.get(key)


def _tolerance(cell: str):
    s=" ".join(cell.strip().upper().replace("⌀","Ø").replace("∅","Ø").split())
    m=TOL_RE.fullmatch(s)
    if not m:
        return None
    value=float(m.group("value"))
    if not (value>0.0):
        return None
    tail=m.group("tail").strip()
    mods=[]
    if tail:
        # Modifiers are explicit whitespace-separated tokens; compact ambiguous
        # strings fail closed rather than being guessed apart.
        for token in tail.split():
            mapped=MODIFIER_MAP.get(token)
            if mapped is None or mapped in mods:
                return None
            mods.append(mapped)
    return {
        "value":value,
        "units":m.group("unit").lower() if m.group("unit") else None,
        "diametral":bool(m.group("diam")),
        "modifiers":mods,
    }


def _datum(cell: str):
    s=" ".join(cell.strip().upper().split())
    m=DATUM_RE.fullmatch(s)
    if not m:
        return None
    boundary=DATUM_BOUNDARY.get(m.group("boundary") or "","RMB")
    return {"letter":m.group("letter"),"boundary":boundary}


def parse_feature_control_frame(
    text: str,
    *,
    edition: str,
    feature_type: str,
) -> dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return _fail("EMPTY")
    ed=EDITION_ALIASES.get(str(edition).strip())
    if ed is None:
        return _fail("EDITION_REQUIRED_OR_UNSUPPORTED",text)
    ft=str(feature_type).strip().lower().replace(" ","_")
    if ft not in FEATURE_TYPES:
        return _fail("FEATURE_TYPE_REQUIRED_OR_UNSUPPORTED",text)

    cells=[c.strip() for c in text.split("|")]
    if len(cells)<2 or any(not c for c in cells):
        return _fail("FRAME_GRAMMAR_INVALID",text)

    char=_characteristic(cells[0])
    if char is None:
        return _fail("CHARACTERISTIC_UNSUPPORTED",text)
    characteristic,family=char
    if ed=="ASME Y14.5-2018" and characteristic in REMOVED_IN_2018:
        return _fail("CHARACTERISTIC_NOT_IN_DECLARED_EDITION",text,characteristic=characteristic)

    tol=_tolerance(cells[1])
    if tol is None:
        return _fail("TOLERANCE_CELL_INVALID",text)

    datums=[]
    for cell in cells[2:]:
        d=_datum(cell)
        if d is None:
            return _fail("DATUM_CELL_INVALID",text,cell=cell)
        if d["letter"] in {x["letter"] for x in datums}:
            return _fail("DUPLICATE_DATUM",text,datum=d["letter"])
        datums.append(d)
    if len(datums)>3:
        return _fail("TOO_MANY_DATUM_REFERENCES",text)

    rule=DATUM_RULE[family]
    if rule=="forbidden" and datums:
        return _fail("DATUM_FORBIDDEN_FOR_FORM_CONTROL",text)
    if rule=="required" and not datums:
        return _fail("DATUM_REQUIRED",text)

    material=[m for m in tol["modifiers"] if m in {"MMC","LMC"}]
    if material and ft!="feature_of_size":
        return _fail("MATERIAL_CONDITION_REQUIRES_FEATURE_OF_SIZE",text)
    if tol["diametral"] and ft!="feature_of_size":
        return _fail("DIAMETRAL_ZONE_REQUIRES_FEATURE_OF_SIZE",text)
    if "PROJECTED" in tol["modifiers"]:
        if ft!="feature_of_size" or family not in {"location","orientation"}:
            return _fail("PROJECTED_ZONE_SCOPE_INVALID",text)

    if any(d["boundary"]!="RMB" for d in datums):
        # A datum material-boundary modifier only makes sense when the datum
        # itself is known to be a feature of size. That metadata is not encoded
        # in this text-only bounded parser, so preserve it as unresolved rather
        # than silently authorizing the frame.
        return _fail("DATUM_MATERIAL_BOUNDARY_REQUIRES_EXTERNAL_FEATURE_METADATA",text)

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "characteristic":characteristic,
        "characteristic_class":family,
        "edition":ed,
        "feature_type":ft,
        "tolerance":tol,
        "datums":datums,
        "terminal_authority":False,
        "scope":"BOUNDED_TEXTUAL_FEATURE_CONTROL_FRAME_GRAMMAR_AND_DECLARED_INPUT_LEGALITY_ONLY",
        "donor_runtime_required":False,
    }
