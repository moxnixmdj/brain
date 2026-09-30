#!/usr/bin/env python3
"""Deterministic open-ended research-intent decomposition.

This module is deliberately small and model-independent. It does not answer a
research question and it does not select a domain-specific supplier. It turns a
broad research objective into typed causal roles and role-specific semantic
queries so downstream verified capability discovery receives the right unit of
work instead of the entire prose objective.

No task-specific names, domains, package names, URLs, or answers belong here.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_RESEARCH_INTENT_DECOMPOSITION_V1"

ROLE_QUESTION = "QUESTION_RESOLUTION"
ROLE_EVIDENCE = "PRIMARY_EVIDENCE_DISCOVERY"
ROLE_METHOD = "METHOD_SELECTION"
ROLE_TOOL = "TOOL_DISCOVERY"
ROLE_EXPERIMENT = "EXECUTABLE_EXPERIMENT"
ROLE_QUANT = "QUANTITATIVE_ANALYSIS"
ROLE_LIMITS = "LIMITATION_ANALYSIS"
ROLE_VERIFY = "INDEPENDENT_VERIFICATION"
ROLE_SYNTHESIS = "SYNTHESIS_AND_PROVENANCE"

_GENERIC = {
    "a","an","and","are","as","at","be","been","being","by","can","could","do",
    "does","for","from","how","if","in","into","is","it","its","may","of","on",
    "or","should","than","that","the","their","then","there","these","this","to",
    "use","using","was","were","what","when","where","whether","which","while",
    "will","with","would",
}
_RESEARCH_CUES = {
    "determine","evaluate","assess","investigate","analyze","analyse","compare",
    "estimate","measure","establish","test","verify","validate","quantify",
    "characterize","characterise","explain","decide",
}
_PROCESS_CUES = {
    "authoritative","primary","technical","evidence","source","sources","method",
    "methods","research","discover","discovery","tool","tools","route","routes",
    "experiment","experiments","executable","independent","independently",
    "verification","verify","limitations","limitation","uncertainty","provenance",
    "answer","report","decision","quality","consequential","result","results",
    "justify","choose","select","synthesize","synthesise",
}

_CUE_MAP = {
    ROLE_EVIDENCE: (
        "authoritative", "primary source", "primary technical evidence",
        "evidence", "documentation", "source", "sources", "literature",
    ),
    ROLE_METHOD: (
        "choose", "justify the research method", "research method", "method",
        "methodology", "decide what evidence", "design",
    ),
    ROLE_TOOL: (
        "discover", "tool", "tools", "route", "select an executable",
        "select a tool", "necessary source and tool",
    ),
    ROLE_EXPERIMENT: (
        "experiment", "real executable", "execute", "run a real", "test the claim",
        "reproduce", "reproduction", "measurement",
    ),
    ROLE_QUANT: (
        "quantify", "calculate", "compute", "estimate", "measure", "compare",
        "rate", "ratio", "difference", "trend", "uncertainty",
    ),
    ROLE_LIMITS: (
        "limitation", "limitations", "uncertainty", "failure mode", "scope",
        "boundary", "caveat",
    ),
    ROLE_VERIFY: (
        "independently verify", "independent verification", "cross-check",
        "crosscheck", "reproduce", "verify the consequential", "validate",
    ),
    ROLE_SYNTHESIS: (
        "decision-quality", "decision quality", "answer", "report", "synthesize",
        "synthesise", "conclusion", "provenance",
    ),
}

@dataclass(frozen=True)
class Role:
    role: str
    required: bool
    basis: tuple[str, ...]
    objective: str
    semantic_query: str

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()

def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9_.+/-]*", text.lower())

def _content_tokens(text: str) -> list[str]:
    out: list[str] = []
    for token in _tokens(text):
        base=token.strip("._/+\-")
        if len(base) < 2:
            continue
        if base in _GENERIC or base in _RESEARCH_CUES or base in _PROCESS_CUES:
            continue
        if base not in out:
            out.append(base)
    return out

def _question_span(goal: str) -> str:
    # The first sentence/clause normally carries the proposition being resolved.
    first=re.split(r"(?<=[.!?])\s+|;\s*", goal, maxsplit=1)[0].strip()
    if not first:
        return goal
    # Remove only generic leading research operators, never domain content.
    first=re.sub(
        r"^(?:please\s+)?(?:determine|evaluate|assess|investigate|analy[sz]e|"
        r"compare|estimate|measure|establish|test|verify|quantify)\s+",
        "",
        first,
        flags=re.IGNORECASE,
    ).strip()
    return first or goal

def _query(subject_tokens: Iterable[str], purpose: str) -> str:
    tokens=list(subject_tokens)
    # Purpose terms are semantic role descriptors, not package names.
    return " ".join(tokens[:18] + purpose.split())

def _hits(goal_lower: str, phrases: Iterable[str]) -> tuple[str, ...]:
    return tuple(p for p in phrases if p in goal_lower)

def decompose(goal: str) -> dict:
    goal=_norm(goal)
    if not goal:
        raise ValueError("GOAL_REQUIRED")
    lower=goal.lower()
    question=_question_span(goal)
    subject=_content_tokens(question)
    if not subject:
        subject=_content_tokens(goal)
    if not subject:
        raise ValueError("NO_DOMAIN_CONTENT_TOKENS")

    roles: list[Role] = [
        Role(
            ROLE_QUESTION,
            True,
            ("research_objective",),
            question,
            _query(subject, "claim resolution"),
        )
    ]

    # Evidence and synthesis are mandatory for an open-ended research result.
    evidence_hits=_hits(lower,_CUE_MAP[ROLE_EVIDENCE])
    roles.append(Role(
        ROLE_EVIDENCE,
        True,
        evidence_hits or ("open_ended_research_default",),
        "Discover and evaluate authoritative evidence relevant to the question.",
        _query(subject, "authoritative primary evidence documentation"),
    ))

    for role in (ROLE_METHOD,ROLE_TOOL,ROLE_EXPERIMENT,ROLE_QUANT,ROLE_LIMITS,ROLE_VERIFY):
        found=_hits(lower,_CUE_MAP[role])
        required=bool(found)
        if role==ROLE_VERIFY:
            # Decision-quality open-ended research always needs an independent
            # verification obligation even when the wording omits the adjective.
            required=True
            found=found or ("open_ended_research_default",)
        if role==ROLE_LIMITS and any(x in lower for x in ("decision-quality","decision quality")):
            required=True
            found=found or ("decision_quality_scope",)
        if not required:
            continue
        purpose={
            ROLE_METHOD:"research method selection",
            ROLE_TOOL:"tool capability supplier discovery",
            ROLE_EXPERIMENT:"executable experiment measurement",
            ROLE_QUANT:"quantitative analysis calculation",
            ROLE_LIMITS:"limitations uncertainty scope",
            ROLE_VERIFY:"independent verification alternative method",
        }[role]
        objective={
            ROLE_METHOD:"Choose a sufficient research method before execution.",
            ROLE_TOOL:"Discover and verify the least-friction tool or capability route.",
            ROLE_EXPERIMENT:"Execute a real experiment or measurement sufficient to test the claim.",
            ROLE_QUANT:"Perform the quantitative analysis required by the question.",
            ROLE_LIMITS:"Identify material limitations, uncertainty, and scope boundaries.",
            ROLE_VERIFY:"Independently verify the consequential result using a distinct route where practical.",
        }[role]
        roles.append(Role(role,True,found,objective,_query(subject,purpose)))

    synthesis_hits=_hits(lower,_CUE_MAP[ROLE_SYNTHESIS])
    roles.append(Role(
        ROLE_SYNTHESIS,
        True,
        synthesis_hits or ("open_ended_research_default",),
        "Synthesize the verified evidence into a scoped decision-quality conclusion with provenance.",
        _query(subject, "evidence synthesis conclusion provenance"),
    ))

    # Stable causal ordering. Downstream code may execute or route one role at a
    # time; this module itself never invents a supplier or domain-specific recipe.
    order=[
        ROLE_QUESTION,ROLE_EVIDENCE,ROLE_METHOD,ROLE_TOOL,ROLE_EXPERIMENT,
        ROLE_QUANT,ROLE_LIMITS,ROLE_VERIFY,ROLE_SYNTHESIS,
    ]
    roles.sort(key=lambda r: order.index(r.role))
    role_payload=[
        {
            "role":r.role,
            "required":r.required,
            "basis":list(r.basis),
            "objective":r.objective,
            "semantic_query":r.semantic_query,
        }
        for r in roles
    ]
    return {
        "schema":SCHEMA,
        "goal":goal,
        "goal_sha256":hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        "question":question,
        "subject_terms":subject,
        "roles":role_payload,
        "role_order":[x["role"] for x in role_payload],
        "model_dependency_count":0,
        "cognition_dependency_class":"MODEL_INDEPENDENT",
        "cognition_provenance_authority":"ASTRA_RUNTIME_DERIVED_V1",
        "supplier_selected":False,
        "task_specific_recipe_embedded":False,
    }

def main() -> int:
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--output")
    args=ap.parse_args()
    value=decompose(args.goal)
    raw=json.dumps(value,indent=2,sort_keys=True)+"\n"
    if args.output:
        from pathlib import Path
        p=Path(args.output)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(raw,encoding="utf-8")
    print(raw,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
