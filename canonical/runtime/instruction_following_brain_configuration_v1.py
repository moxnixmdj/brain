"""Generic Brain-owned instruction-following configuration.

This module is benchmark-agnostic. It accepts only the user-visible task prompt,
reuses existing Brain deterministic requirement parsers when they apply, and
constructs a configuration for an approved general cognition substrate.
It never consumes evaluator annotations, expected outputs, checker identities,
or hidden acceptance metadata.
"""
from __future__ import annotations
import json, re
from typing import Any
from canonical.runtime import explicit_compound_requirement_decomposer as compound
from canonical.runtime import bounded_predicate_argument_semantics as pas

SCHEMA="BRAIN_INSTRUCTION_FOLLOWING_CONFIGURATION_V1"

def _bounded_clauses(prompt:str)->list[dict[str,Any]]:
    pieces=[]
    for line in prompt.splitlines():
        line=line.strip()
        if not line or len(line)>800:
            continue
        for part in re.split(r"(?<=[.!?])\s+", line):
            part=part.strip()
            if not part or len(part)>500:
                continue
            parsed=pas.parse_clause(part)
            if parsed.get("status")=="RESOLVED":
                g=parsed["semantic_graph"]
                pieces.append({
                    "subject":g["subject"],
                    "predicate":g["predicate"],
                    "object":g["object"],
                    "modality":g["modality"],
                    "polarity":g["polarity"],
                })
            if len(pieces)>=24:
                return pieces
    return pieces

def compile_instruction_configuration(prompt:str)->dict[str,Any]:
    if not isinstance(prompt,str) or not prompt.strip():
        raise ValueError("PROMPT_REQUIRED")
    if len(prompt)>100000:
        raise ValueError("PROMPT_TOO_LARGE")

    dec=compound.decompose_explicit_compound(prompt)
    obligations=list(dec.get("obligations") or []) if dec.get("status")=="DECOMPOSED" else []
    bounded=_bounded_clauses(prompt)

    extracted={
        "explicit_compound_obligations":obligations[:32],
        "bounded_modal_clauses":bounded,
    }
    system=(
        "You are the general cognition substrate executing a durable Project Brain "
        "instruction-following configuration. The user-visible prompt is the sole task "
        "authority. Satisfy every explicit requirement simultaneously. Preserve exact "
        "requested output structure and do not add meta-commentary, disclaimers, headings, "
        "or explanations unless the user asks for them. Before emitting the answer, silently "
        "check the draft against all explicit lexical, structural, quantitative, ordering, "
        "formatting, inclusion, exclusion, start/end, and transformation constraints. "
        "When requirements conflict, obey the most explicit local constraint and do not "
        "invent unstated requirements. The deterministic Brain extraction below is only a "
        "source-bound aid; it never overrides the original prompt.\n"
        "BRAIN_DETERMINISTIC_EXTRACTION="
        +json.dumps(extracted,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    )
    return {
        "schema":SCHEMA,
        "system":system,
        "user":prompt,
        "deterministic_extraction":extracted,
        "hidden_evaluator_information_consumed":False,
        "terminal_authority":False,
    }

def messages_for_prompt(prompt:str)->list[dict[str,str]]:
    cfg=compile_instruction_configuration(prompt)
    return [
        {"role":"system","content":cfg["system"]},
        {"role":"user","content":cfg["user"]},
    ]
