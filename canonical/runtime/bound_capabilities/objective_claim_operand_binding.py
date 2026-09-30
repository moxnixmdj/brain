#!/usr/bin/env python3
"""Bounded objective-to-claim-spec and semantic operand binding.

Verified candidate scope:
- exact quoted-claim support requests;
- explicit binary numeric comparisons using GT/LT/GTE/LTE/EQ/NE;
- explicit absolute-difference-at-most comparisons;
- unique lexical binding of left/right entity phrases to distinct generic V2
  evidence units;
- unique exact-unit-compatible numeric-literal binding;
- composition into the already-verified generic V2 claim/relation evaluator.

This module does not infer paraphrases, factual truth, causality, unit
conversion, evidence sufficiency, or latent semantic roles outside the bounded
explicit grammar. Ambiguity fails closed.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

SCHEMA="PROJECT_BRAIN_OBJECTIVE_CLAIM_SPEC_OPERAND_BINDING_V1"

_STOP={
 "a","an","and","are","as","at","be","by","check","compare","determine","does",
 "for","from","higher","greater","larger","lower","less","smaller","below",
 "exceed","exceeds","exceeded","equal","equals","same","different","differs",
 "differ","difference","least","most","more","no","find","in","is","it","of",
 "on","or","than","that","the","this","to","was","were","whether","which",
 "with","assess","investigate","verify","source","evidence","states","contains",
 "includes","says","exact","text","claim",
}
_WORD=re.compile(r"[a-z0-9][a-z0-9._+-]*")
_NUM_SURFACE=(
 r"[-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)"
 r"(?:\.\d+)?(?:[eE][-+]?\d+)?"
 r"(?:\s*[%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31})?"
)
_NUM=re.compile(
 r"(?<![A-Za-z0-9_.])"
 r"([-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)"
 r"(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?"
)

# Order matters: more specific forms precede more general comparison forms.
_RELATION_PATTERNS=[
 (re.compile(r"\b(?:determine|check|verify|assess|investigate|find)?\s*(?:whether\s+)?(.+?)\s+and\s+(.+?)\s+differ\s+by\s+(?:at\s+most|no\s+more\s+than)\s+("+_NUM_SURFACE+r")(?:[?.]|$)",re.I),"ABS_DIFF_LTE",3),
 (re.compile(r"\b(?:determine|check|verify|assess|investigate|find)?\s*(?:whether\s+)?(?:the\s+)?difference\s+between\s+(.+?)\s+and\s+(.+?)\s+(?:is|was)\s+(?:at\s+most|no\s+more\s+than)\s+("+_NUM_SURFACE+r")(?:[?.]|$)",re.I),"ABS_DIFF_LTE",3),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+(?:is|was|are|were)\s+(?:at\s+least|no\s+less\s+than)\s+(.+?)(?:[?.]|$)",re.I),"GTE",None),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+(?:is|was|are|were)\s+(?:at\s+most|no\s+more\s+than)\s+(.+?)(?:[?.]|$)",re.I),"LTE",None),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+(?:is|was|are|were)\s+(?:not\s+equal\s+to|different\s+from)\s+(.+?)(?:[?.]|$)",re.I),"NE",None),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+differs\s+from\s+(.+?)(?:[?.]|$)",re.I),"NE",None),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+(?:is|was|are|were)\s+(?:equal\s+to|the\s+same\s+as)\s+(.+?)(?:[?.]|$)",re.I),"EQ",None),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+(?:is|was|are|were)\s+(?:higher|greater|larger)\s+than\s+(.+?)(?:[?.]|$)",re.I),"GT",None),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+(?:is|was|are|were)\s+(?:lower|less|smaller)\s+than\s+(.+?)(?:[?.]|$)",re.I),"LT",None),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+(?:is|was|are|were)\s+below\s+(.+?)(?:[?.]|$)",re.I),"LT",None),
 (re.compile(r"\b(?:whether\s+)?(.+?)\s+(?:exceeds|exceeded)\s+(.+?)(?:[?.]|$)",re.I),"GT",None),
 (re.compile(r"\bdoes\s+(.+?)\s+exceed\s+(.+?)(?:[?.]|$)",re.I),"GT",None),
]
_QUOTED=[
 re.compile(r'\b(?:verify|check|determine)\s+(?:whether\s+)?(?:the\s+)?(?:source|evidence)\s+(?:states|contains|includes|says)\s+["“]([^"”]+)["”]',re.I),
 re.compile(r'\b(?:verify|check)\s+(?:the\s+)?exact\s+(?:text|claim)\s+["“]([^"”]+)["”]',re.I),
]

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _tokens(value):
    out=[]
    for raw in _WORD.findall(_canon(value).lower()):
        t=raw.strip("._+-")
        if len(t)<2 or t in _STOP:
            continue
        if t not in out:
            out.append(t)
    return out

def _clean_entity(value):
    text=_canon(value)
    text=re.sub(
      r"^(?:determine|check|assess|investigate|verify|find)\s+(?:whether\s+)?",
      "",text,flags=re.I,
    )
    return text.strip(" ,:;-")

def _parse_objective(objective):
    objective=_canon(objective)
    quoted=[]
    for rx in _QUOTED:
        m=rx.search(objective)
        if m:
            claim=_canon(m.group(1))
            if claim and claim not in quoted:
                quoted.append(claim)
    if quoted:
        if len(quoted)!=1:
            return None,"OBJECTIVE_CLAIM_AMBIGUOUS"
        return {"mode":"VERBATIM_SUPPORT","claim_text":quoted[0]},None

    matches=[]
    for rx,op,threshold_group in _RELATION_PATTERNS:
        m=rx.search(objective)
        if not m:
            continue
        left=_clean_entity(m.group(1)); right=_clean_entity(m.group(2))
        threshold=_canon(m.group(threshold_group)) if threshold_group else None
        row=(op,left,right,threshold)
        if left and right and row not in matches:
            matches.append(row)
    if len(matches)!=1:
        return None,"OBJECTIVE_RELATION_AMBIGUOUS_OR_UNSUPPORTED"
    op,left,right,threshold=matches[0]
    lt,rt=_tokens(left),_tokens(right)
    if not lt or not rt:
        return None,"OBJECTIVE_ENTITY_TOKENS_REQUIRED"
    if set(lt)==set(rt):
        return None,"OBJECTIVE_ENTITY_ROLES_NOT_DISTINCT"
    out={
      "mode":"NUMERIC_RELATION",
      "operator":op,
      "left_entity":left,
      "right_entity":right,
      "left_tokens":lt,
      "right_tokens":rt,
    }
    if threshold is not None:
        out["threshold"]=threshold
    return out,None

def _validated_units(extraction):
    if not isinstance(extraction,dict):
        raise ValueError("EXTRACTION_REQUIRED")
    if extraction.get("schema")!="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2":
        raise ValueError("EXTRACTION_SCHEMA_INVALID")
    if extraction.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED" or extraction.get("output_verified") is not True:
        raise ValueError("VERIFIED_GENERIC_EXTRACTION_REQUIRED")
    rows=extraction.get("evidence_units")
    if not isinstance(rows,list) or not rows:
        raise ValueError("EVIDENCE_UNITS_REQUIRED")
    out=[]; seen=set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("EVIDENCE_UNIT_INVALID")
        uid=str(row.get("evidence_unit_id") or "")
        text=_canon(row.get("text"))
        if not re.fullmatch(r"[0-9a-f]{64}",uid) or not text or uid in seen:
            raise ValueError("EVIDENCE_UNIT_ID_OR_TEXT_INVALID")
        seen.add(uid)
        out.append({"evidence_unit_id":uid,"text":text,"tokens":_tokens(text)})
    return out

def _bind_role(units,entity_tokens):
    target=set(entity_tokens)
    scored=[]
    for row in units:
        overlap=target & set(row["tokens"])
        if not overlap:
            continue
        coverage=len(overlap)/len(target)
        # Same scoring shape as Brain's prior scalar semantic binder:
        # exact token evidence dominates; shorter evidence units break weak
        # lexical ties only after overlap and coverage.
        scored.append((len(overlap),coverage,-len(row["tokens"]),row,sorted(overlap)))
    if not scored:
        return None,"NO_EVIDENCE_UNIT_FOR_ENTITY"
    scored.sort(key=lambda x:(-x[0],-x[1],-x[2],x[3]["evidence_unit_id"]))
    best=scored[0]
    tied=[x for x in scored if x[:3]==best[:3]]
    if len(tied)!=1:
        return None,"AMBIGUOUS_EVIDENCE_UNIT_FOR_ENTITY"
    if best[1] < 0.5 and best[0] < 2:
        return None,"INSUFFICIENT_ENTITY_ANCHOR_COVERAGE"
    return {
      "evidence_unit_id":best[3]["evidence_unit_id"],
      "text":best[3]["text"],
      "matched_entity_tokens":best[4],
      "entity_token_coverage":round(best[1],6),
    },None

def _numbers(text):
    rows=[]
    for index,m in enumerate(_NUM.finditer(text)):
        unit=_canon(m.group(2)).lower().rstrip(".,;:")
        rows.append({
          "numeric_literal_index":index,
          "surface":m.group(0).strip(),
          "number_surface":m.group(1),
          "unit":unit,
          "char_start":m.start(),
          "char_end":m.end(),
        })
    return rows

def _choose_pair(left_binding,right_binding):
    left=_numbers(left_binding["text"]); right=_numbers(right_binding["text"])
    if not left or not right:
        return None,"NUMERIC_LITERAL_REQUIRED_FOR_BOTH_ROLES"
    pairs=[]
    for a in left:
        for b in right:
            if a["unit"]==b["unit"]:
                pairs.append((a,b))
    if not pairs:
        return None,"NO_EXACT_UNIT_COMPATIBLE_OPERAND_PAIR"
    # Prefer an explicit shared unit surface over unitless decoys such as years.
    nonempty=[p for p in pairs if p[0]["unit"]]
    pool=nonempty if nonempty else pairs
    if len(pool)!=1:
        return None,"AMBIGUOUS_COMPATIBLE_OPERAND_PAIR"
    a,b=pool[0]
    return {
      "left":{"evidence_unit_id":left_binding["evidence_unit_id"],
              "numeric_literal_index":a["numeric_literal_index"]},
      "right":{"evidence_unit_id":right_binding["evidence_unit_id"],
               "numeric_literal_index":b["numeric_literal_index"]},
      "unit_surface":a["unit"] or None,
      "left_surface":a["surface"],"right_surface":b["surface"],
    },None

def _load_evaluator():
    path=pathlib.Path(__file__).resolve().with_name("generic_evidence_claim_relation.py")
    spec=importlib.util.spec_from_file_location("project_brain_verified_generic_claim_relation",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("VERIFIED_CLAIM_RELATION_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _bind_verbatim(parsed,units):
    claim=_canon(parsed.get("claim_text"))
    needle=claim.casefold()
    matches=[u for u in units if needle in u["text"].casefold()]
    if not matches:
        return None,"EXACT_QUOTED_CLAIM_NOT_FOUND"
    if len(matches)!=1:
        return None,"EXACT_QUOTED_CLAIM_EVIDENCE_AMBIGUOUS"
    spec={
      "mode":"VERBATIM_SUPPORT",
      "claim_text":claim,
      "evidence_unit_id":matches[0]["evidence_unit_id"],
    }
    return {
      "relation_spec":spec,
      "claim_binding":{
        "evidence_unit_id":matches[0]["evidence_unit_id"],
        "claim_text":claim,
        "binding_method":"EXACT_NORMALIZED_SUBSTRING",
      },
    },None

def bind(objective,extraction,evaluate_relation=True):
    objective=_canon(objective)
    base={
      "schema":SCHEMA,
      "objective":objective or None,
      "status":"UNBOUND",
      "binding_scope":"BOUNDED_EXPLICIT_COMPARISON_OR_EXACT_QUOTED_CLAIM_WITH_UNIQUE_EVIDENCE_BINDING",
      "semantic_entailment_status":"UNVERIFIED",
      "factual_correctness_status":"UNVERIFIED",
      "causality_status":"UNVERIFIED",
      "evidence_sufficiency_status":"UNVERIFIED",
      "unit_conversion_status":"NOT_PERFORMED",
      "model_dependency_count":0,
      "incremental_spend_usd":0,
    }
    if not objective:
        return {**base,"reason":"OBJECTIVE_REQUIRED"}
    parsed,reason=_parse_objective(objective)
    if reason:
        return {**base,"reason":reason}
    units=_validated_units(extraction)

    if parsed["mode"]=="VERBATIM_SUPPORT":
        bound,reason=_bind_verbatim(parsed,units)
        if reason:
            return {**base,"reason":reason,"parsed_objective":parsed}
        result={
          **base,
          "status":"CLAIM_SPEC_BOUND",
          "parsed_objective":parsed,
          **bound,
          "output_verified":True,
        }
    else:
        left,reason=_bind_role(units,parsed["left_tokens"])
        if reason:
            return {**base,"reason":"LEFT_"+reason,"parsed_objective":parsed}
        right,reason=_bind_role(units,parsed["right_tokens"])
        if reason:
            return {**base,"reason":"RIGHT_"+reason,"parsed_objective":parsed}
        if left["evidence_unit_id"]==right["evidence_unit_id"]:
            return {**base,"reason":"LEFT_RIGHT_ROLE_COLLISION","parsed_objective":parsed}
        pair,reason=_choose_pair(left,right)
        if reason:
            return {**base,"reason":reason,"parsed_objective":parsed,
                    "left_binding":left,"right_binding":right}
        relation_spec={
          "mode":"NUMERIC_RELATION",
          "operator":parsed["operator"],
          "left":pair["left"],
          "right":pair["right"],
        }
        if parsed.get("threshold") is not None:
            relation_spec["threshold"]=parsed["threshold"]
        result={
          **base,
          "status":"CLAIM_SPEC_AND_OPERANDS_BOUND",
          "parsed_objective":parsed,
          "left_binding":left,
          "right_binding":right,
          "operand_pair":pair,
          "relation_spec":relation_spec,
          "output_verified":True,
        }

    if evaluate_relation:
        evaluator=_load_evaluator()
        result["relation_result"]=evaluator.evaluate(extraction,result["relation_spec"])
        status=str(result["relation_result"].get("status") or "")
        if status not in {
          "NUMERIC_RELATION_VERIFIED",
          "EXACT_TEXT_SUPPORT_VERIFIED",
          "EXACT_TEXT_SUPPORT_NOT_VERIFIED",
        }:
            raise ValueError("VERIFIED_RELATION_EVALUATOR_DID_NOT_VERIFY")
    return result

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args,root):
    import json
    args=dict(args or {})
    inp=_safe_path(root,args.get("extraction_path"))
    out=_safe_path(root,args.get("output_path"))
    if not inp.is_file():
        raise ValueError("EXTRACTION_INPUT_MISSING")
    extraction=json.loads(inp.read_text(encoding="utf-8"))
    result=bind(args.get("objective"),extraction,evaluate_relation=True)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    return result
