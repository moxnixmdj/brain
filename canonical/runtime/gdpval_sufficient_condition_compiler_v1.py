"""Fail-closed sufficient-condition compiler for bounded GDPval criterion forms.

A compiled program is intentionally allowed to be STRONGER than the natural-language
criterion. Passing the program is therefore evidence for the criterion only when the
compiler rule has been independently proved sound. Unsupported language remains UNKNOWN.

The runtime operates over a typed artifact-unit IR rather than parsing Office/PDF bytes.
Artifact extraction is a separate capability and must preserve the unit types used here.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping, Sequence


SCHEMA="PROJECT_BRAIN_GDPVAL_SUFFICIENT_CONDITION_COMPILER_V1"
PROGRAM_SCHEMA="PROJECT_BRAIN_ARTIFACT_PREDICATE_PROGRAM_V1"


class CriterionCompileError(ValueError):
    pass


def _norm_text(value: Any, *, punctuation_insensitive: bool=False) -> str:
    s=" ".join(str(value or "").split()).casefold()
    if punctuation_insensitive:
        s=re.sub(r"[^\w\s]+"," ",s,flags=re.UNICODE)
        s=" ".join(s.split())
    return s


def _dec(value: str) -> str:
    x=value.replace(",","").replace("$","").replace("%","").strip()
    try:
        d=Decimal(x)
    except InvalidOperation as exc:
        raise CriterionCompileError("NUMERIC_LITERAL_INVALID") from exc
    if not d.is_finite():
        raise CriterionCompileError("NUMERIC_LITERAL_NONFINITE")
    return str(d)


def _program(rule_id: str, predicate: Mapping[str,Any], criterion: str) -> dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"COMPILED_SUFFICIENT_CONDITION",
        "rule_id":rule_id,
        "criterion":" ".join(str(criterion or "").split()),
        "program":{"schema":PROGRAM_SCHEMA,"predicate":dict(predicate)},
        "semantic_relation":"PROGRAM_PASS_IMPLIES_CRITERION_TRUE__CONVERSE_NOT_CLAIMED",
        "terminal_authority":False,
    }


_Q=r"""["'“”‘’]([^"'“”‘’]+)["'“”‘’]"""


def compile_criterion(criterion: str) -> dict[str,Any]:
    text=" ".join(str(criterion or "").split())
    base={"schema":SCHEMA,"criterion":text,"terminal_authority":False}
    if not text:
        return {**base,"status":"FAIL_CLOSED","reason":"CRITERION_MISSING"}

    # Native document/report top-level heading. Requiring a real level-1 heading is
    # stronger than mere visual resemblance and therefore safe as a one-way witness.
    pats=[
        rf"The report includes a top-level section titled {_Q}\.?\s*(?:\(case/punctuation variations acceptable\)\.)?",
        rf"The report includes a top-level section titled {_Q}\s*\(case/punctuation variations acceptable\)\.?",
    ]
    for pat in pats:
        m=re.fullmatch(pat,text,re.I)
        if m:
            return _program("TOP_LEVEL_HEADING_EQUALS_QUOTED",{
                "op":"HEADING_EQUALS","text":m.group(1),"level":1,
                "case_insensitive":True,"punctuation_insensitive":True,
            },text)

    m=re.fullmatch(rf"The document contains a (?:distinct )?section (?:titled|headed) {_Q}\.?",text,re.I)
    if m:
        return _program("SECTION_HEADING_EQUALS_QUOTED",{
            "op":"HEADING_EQUALS","text":m.group(1),"level":None,
            "case_insensitive":True,"punctuation_insensitive":False,
        },text)

    m=re.fullmatch(rf"Includes a top-level section whose heading contains the phrase {_Q} \(case.?insensitive\)\.?",text,re.I)
    if m:
        return _program("TOP_LEVEL_HEADING_CONTAINS_QUOTED",{
            "op":"HEADING_CONTAINS","text":m.group(1),"level":1,
            "case_insensitive":True,"punctuation_insensitive":False,
        },text)

    m=re.fullmatch(rf"The document includes a heading that equals \(case-insensitive; optional trailing colon\) {_Q}",text,re.I)
    if m:
        return _program("HEADING_EQUALS_QUOTED_OPTIONAL_COLON",{
            "op":"HEADING_EQUALS","text":m.group(1),"level":None,
            "case_insensitive":True,"strip_trailing_colon":True,
            "punctuation_insensitive":False,
        },text)

    # Exact worksheet-name semantics are native and unambiguous.
    m=re.fullmatch(rf"(?:Workbook \(deliverable\)|The workbook) contains a worksheet named exactly {_Q} \(case-insensitive(?:, ignoring surrounding spaces)?\)\.?",text,re.I)
    if m:
        return _program("WORKSHEET_NAME_EQUALS_QUOTED",{
            "op":"SHEET_NAME_EQUALS","text":m.group(1),
            "case_insensitive":True,"trim":True,
        },text)

    # Exact line-value criteria. Same-unit anchoring is stronger than the original
    # criterion, so it may false-negative but cannot pass from an unrelated value.
    m=re.fullmatch(r"(Form|Schedule)\s+(\d+)\s+line\s+(\d+)\s+is\s+\$([\d,]+(?:\.\d+)?)\.?",text,re.I)
    if m:
        return _program("ANCHORED_FORM_OR_SCHEDULE_LINE_VALUE",{
            "op":"UNIT_ANCHORED_NUMERIC_EQ",
            "anchors":[f"{m.group(1)} {m.group(2)}",f"line {m.group(3)}"],
            "value":_dec(m.group(4)),"unit":"USD",
            "case_insensitive":True,
        },text)

    # Repeated carrier-rate family.
    m=re.fullmatch(
        r"States the (\d{4}) annual rate increase for ([A-Za-z0-9 .&/-]+?) as a number between "
        r"([\d.]+)% and ([\d.]+)%",
        text,re.I,
    )
    if m:
        return _program("ANCHORED_ANNUAL_RATE_RANGE",{
            "op":"UNIT_ANCHORED_NUMERIC_RANGE",
            "anchors":[m.group(1),m.group(2),"annual rate increase"],
            "lower":_dec(m.group(3)),"upper":_dec(m.group(4)),"unit":"percent",
            "inclusive":True,"case_insensitive":True,
        },text)

    # Repeated scenario-default scalar families.
    m=re.fullmatch(r"Scenario\s+(\d+) default primary term equals ([\d.]+) years?\.?",text,re.I)
    if m:
        return _program("ANCHORED_SCENARIO_PRIMARY_TERM",{
            "op":"UNIT_ANCHORED_NUMERIC_EQ",
            "anchors":[f"scenario {m.group(1)}","primary term"],
            "value":_dec(m.group(2)),"unit":"years","case_insensitive":True,
        },text)

    m=re.fullmatch(r"Scenario\s+(\d+) default base rent equals \$([\d,.]+) per SF per month\.?",text,re.I)
    if m:
        return _program("ANCHORED_SCENARIO_BASE_RENT",{
            "op":"UNIT_ANCHORED_NUMERIC_EQ",
            "anchors":[f"scenario {m.group(1)}","base rent"],
            "value":_dec(m.group(2)),"unit":"USD_PER_SF_PER_MONTH","case_insensitive":True,
        },text)

    m=re.fullmatch(r"Scenario\s+(\d+) default annual escalator equals ([\d.]+)%\.?",text,re.I)
    if m:
        return _program("ANCHORED_SCENARIO_ESCALATOR",{
            "op":"UNIT_ANCHORED_NUMERIC_EQ",
            "anchors":[f"scenario {m.group(1)}","annual escalator"],
            "value":_dec(m.group(2)),"unit":"percent","case_insensitive":True,
        },text)

    return {**base,"status":"UNRESOLVED","reason":"OUTSIDE_VERIFIED_SUFFICIENT_GRAMMAR"}


def _unit_text(unit: Mapping[str,Any]) -> str:
    return str(unit.get("text") or "")


def _numbers(text: str) -> list[tuple[Decimal,str]]:
    rx=re.compile(r"(?<![\w.])\$?([-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(\s*%|\s*years?\b|\s*USD\b)?",re.I)
    out=[]
    for m in rx.finditer(text):
        try: value=Decimal(m.group(1).replace(",",""))
        except InvalidOperation: continue
        raw_unit=(m.group(2) or "").strip().casefold()
        if m.group(0).lstrip().startswith("$"): unit="USD"
        elif raw_unit=="%": unit="percent"
        elif raw_unit.startswith("year"): unit="years"
        else: unit=""
        out.append((value,unit))
    return out


def evaluate(program: Mapping[str,Any], units: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    if not isinstance(program,Mapping) or program.get("schema")!=PROGRAM_SCHEMA:
        raise CriterionCompileError("PROGRAM_SCHEMA_INVALID")
    if not isinstance(units,Sequence) or isinstance(units,(str,bytes)):
        raise CriterionCompileError("UNITS_INVALID")
    p=program.get("predicate")
    if not isinstance(p,Mapping): raise CriterionCompileError("PREDICATE_INVALID")
    op=str(p.get("op") or "")

    if op in {"HEADING_EQUALS","HEADING_CONTAINS"}:
        target=str(p.get("text") or "")
        target_norm=_norm_text(target,punctuation_insensitive=bool(p.get("punctuation_insensitive")))
        for u in units:
            if str(u.get("kind") or "")!="HEADING": continue
            if p.get("level") is not None and u.get("level")!=p.get("level"): continue
            value=_unit_text(u)
            if p.get("strip_trailing_colon"): value=value.rstrip().rstrip(":").rstrip()
            vn=_norm_text(value,punctuation_insensitive=bool(p.get("punctuation_insensitive")))
            ok=(vn==target_norm) if op=="HEADING_EQUALS" else (target_norm in vn)
            if ok:
                return {"status":"PASS","witness":dict(u),"terminal_authority":False}
        return {"status":"NOT_PROVED","terminal_authority":False}

    if op=="SHEET_NAME_EQUALS":
        target=_norm_text(p.get("text"))
        for u in units:
            if str(u.get("kind") or "")=="SHEET" and _norm_text(u.get("name"))==target:
                return {"status":"PASS","witness":dict(u),"terminal_authority":False}
        return {"status":"NOT_PROVED","terminal_authority":False}

    if op in {"UNIT_ANCHORED_NUMERIC_EQ","UNIT_ANCHORED_NUMERIC_RANGE"}:
        anchors=[_norm_text(x) for x in p.get("anchors") or []]
        for u in units:
            text=_unit_text(u); nt=_norm_text(text)
            if not anchors or not all(a in nt for a in anchors): continue
            nums=_numbers(text)
            if op=="UNIT_ANCHORED_NUMERIC_EQ":
                want=Decimal(str(p["value"]))
                wanted_unit=str(p.get("unit") or "")
                for val,unit in nums:
                    # Compound business units may be expressed textually outside the
                    # numeric token. Require their anchor words in the same unit.
                    if wanted_unit=="USD_PER_SF_PER_MONTH":
                        unit_ok=("$" in text and "sf" in nt and "month" in nt)
                    else:
                        unit_ok=(not wanted_unit or unit==wanted_unit)
                    if val==want and unit_ok:
                        return {"status":"PASS","witness":dict(u),"value":str(val),"terminal_authority":False}
            else:
                lo=Decimal(str(p["lower"])); hi=Decimal(str(p["upper"]))
                wanted_unit=str(p.get("unit") or "")
                for val,unit in nums:
                    if (not wanted_unit or unit==wanted_unit) and lo<=val<=hi:
                        return {"status":"PASS","witness":dict(u),"value":str(val),"terminal_authority":False}
        return {"status":"NOT_PROVED","terminal_authority":False}

    raise CriterionCompileError("UNKNOWN_PREDICATE_OP:"+op)
