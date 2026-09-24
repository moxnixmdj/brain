#!/usr/bin/env python3
"""Deterministic plain-goal compiler for Project Brain.

Purpose: remove hand-authored target_effects/initial_facts for goals that
clearly map to already verified bound capabilities. It intentionally fails
closed on unknown or ambiguous goals so the next missing mechanism remains
observable instead of being guessed.
"""
from __future__ import annotations

import json
import pathlib
import re


class GoalCompilationFailure(RuntimeError):
    def __init__(self, code, detail=None):
        self.code=code
        self.detail=detail
        super().__init__(code if detail is None else f"{code}:{detail}")


STOPWORDS={
    "the","a","an","to","from","of","and","or","with","using","use","do","for",
    "which","is","are","be","this","that","into","on","in","visible"
}

GENERIC_MATCH_TOKENS={
    "generate","image","text","extract","create","save","output","input",
    "file","read","write","convert","process","data"
}


def _tokens(value):
    return {
        t.lower() for t in re.findall(r"[A-Za-z0-9]+", str(value or ""))
        if len(t) >= 2 and t.lower() not in STOPWORDS
    }


def _flatten(value):
    if isinstance(value,dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value,list):
        return " ".join(_flatten(v) for v in value)
    return str(value or "")


def _placeholders(value):
    text=_flatten(value)
    return sorted(set(re.findall(r"\$\{input\.([A-Za-z0-9_]+)\}",text)))


def _repo_paths(goal, root):
    candidates=[]
    for raw in re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",goal):
        raw=raw.rstrip(".,;:!?)]}")
        p=(pathlib.Path(root)/raw).resolve()
        rr=pathlib.Path(root).resolve()
        if p==rr or rr in p.parents:
            candidates.append((raw,p))
    return candidates


def _extract_text_argument(goal):
    quoted=re.findall(r'["\']([^"\']+)["\']',goal)
    if len(quoted)==1 and quoted[0].strip():
        return quoted[0].strip()
    patterns=[
        r"\b(?:for|from)\s+the\s+text\s+(.+?)(?=\s+and\s+(?:save|write|store)\b|\s+(?:save|write|store)\b|$)",
        r"\btext\s+(.+?)(?=\s+and\s+(?:save|write|store)\b|\s+(?:save|write|store)\b|$)",
    ]
    for pattern in patterns:
        m=re.search(pattern,goal,flags=re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip(" .,:;")
    raise GoalCompilationFailure("GOAL_TEXT_INPUT_BINDING_REQUIRED")


def _bind_inputs(goal, root, entry):
    template=entry.get("action_template") or {}
    keys=_placeholders(template)
    if not keys:
        return {}
    paths=_repo_paths(goal,root)
    result={}
    for key in keys:
        if key=="text":
            result[key]=_extract_text_argument(goal)
            continue
        if key.endswith("_path"):
            stem=key[:-5].lower()
            if key.startswith("output_"):
                # Output paths are expected not to exist yet. Bind only a
                # repository-safe path explicitly present in the goal.
                matching=[raw for raw,p in paths if (not stem or stem in raw.lower() or p.suffix.lower() in {".png",".jpg",".jpeg",".pdf",".txt",".json",".csv",".md"})]
                if len(matching)==1:
                    result[key]=matching[0]
                    continue
                if len(paths)==1:
                    result[key]=paths[0][0]
                    continue
            else:
                existing=[(raw,p) for raw,p in paths if p.is_file()]
                matching=[raw for raw,p in existing if (not stem or stem in p.suffix.lower() or stem in raw.lower())]
                if len(matching)==1:
                    result[key]=matching[0]
                    continue
                if len(existing)==1:
                    result[key]=existing[0][0]
                    continue
        raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED",key)
    return result


def _score(goal, cid, entry):
    gt=_tokens(goal)
    provides=_tokens(entry.get("provides",[]))
    requires=_tokens(entry.get("requires",[]))
    identity=_tokens(cid)
    keywords=_tokens(entry.get("keywords",[]))
    # Requirements are highly informative for environment qualifiers such as
    # image-only/scanned/local/etc. Provides represent the requested effect.
    effect_matches=(gt & provides) | (gt & identity) | (gt & keywords)
    distinctive={x for x in effect_matches if x not in GENERIC_MATCH_TOKENS}
    # Preconditions and generic verbs/nouns may refine a match but may never
    # create one. A barcode-image goal must not become a QR-image action merely
    # because both say "generate" and "image".
    if not effect_matches or not distinctive:
        return 0,0,{
            "goal_tokens":sorted(gt),
            "matched_provides":[],
            "matched_requires":sorted(gt & requires),
            "matched_identity":[],
            "matched_keywords":sorted(gt & keywords),
        }
    score=5*len(gt & provides)+4*len(gt & keywords)+3*len(gt & requires)+2*len(gt & identity)
    # Prefer more-specific matched preconditions when base scores tie.
    specificity=len(gt & requires)
    return score,specificity,{
        "goal_tokens":sorted(gt),
        "matched_provides":sorted(gt & provides),
        "matched_requires":sorted(gt & requires),
        "matched_identity":sorted(gt & identity),
        "matched_keywords":sorted(gt & keywords),
    }


def _render_template(value, inputs):
    if isinstance(value,dict):
        return {k:_render_template(v,inputs) for k,v in value.items()}
    if isinstance(value,list):
        return [_render_template(v,inputs) for v in value]
    if isinstance(value,str):
        out=value
        for key,val in inputs.items():
            out=out.replace("${input."+str(key)+"}",str(val))
        if "${input." in out:
            raise GoalCompilationFailure("GOAL_INPUT_BINDING_REQUIRED","unresolved template input")
        return out
    return value


def decompose_goal(goal):
    """Return ordered action clauses for an explicitly compound plain goal.

    This is intentionally conservative: sentence boundaries, explicit "then",
    and action-bearing "and" connectors only. It does not invent hidden steps.
    """
    text=" ".join(str(goal or "").strip().split())
    if not text:
        return []
    parts=re.split(r"(?<=[.!?])\s+(?=[A-Z])|\b[Tt]hen\b",text)
    clauses=[]
    action_connector=re.compile(
        r"\s+and\s+(?=(?:read|inspect|create|generate|convert|extract|verify|check|render|analy[sz]e)\b)",
        re.IGNORECASE,
    )
    for part in parts:
        part=part.strip(" .")
        if not part:
            continue
        for sub in action_connector.split(part):
            sub=sub.strip(" .")
            if sub:
                clauses.append(sub)
    return clauses


def _compile_single_goal(goal, registry, root):
    ranked=[]
    for cid,entry in sorted((registry or {}).items()):
        if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        if not isinstance(entry.get("action_template"),dict):
            continue
        score,specificity,evidence=_score(goal,cid,entry)
        if score<=0:
            continue
        try:
            inputs=_bind_inputs(goal,root,entry)
        except GoalCompilationFailure:
            continue
        ranked.append((score,specificity,cid,entry,inputs,evidence))
    ranked.sort(key=lambda x:(-x[0],-x[1],x[2]))
    if not ranked:
        raise GoalCompilationFailure("GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH")
    best=ranked[0]
    if len(ranked)>1 and ranked[1][0]==best[0] and ranked[1][1]==best[1]:
        raise GoalCompilationFailure(
            "GOAL_COMPILATION_AMBIGUOUS",
            json.dumps({"candidates":[best[2],ranked[1][2]],"score":best[0]},sort_keys=True)
        )
    score,specificity,cid,entry,inputs,evidence=best
    return {
        "schema":"PROJECT_BRAIN_COMPILED_CAPABILITY_PROBLEM_V1",
        "compiler_mode":"DETERMINISTIC_VERIFIED_CAPABILITY_MATCH",
        "selected_capability":cid,
        "score":score,
        "match_evidence":evidence,
        "inputs":inputs,
        "initial_facts":list(entry.get("requires") or []),
        "target_effects":list(entry.get("provides") or []),
        "capabilities":[],
        "finish_summary":"PLAIN_GOAL_COMPLETE",
    }


def _compile_compound_goal(goal, clauses, registry, root):
    actions=[]
    compiled_parts=[]
    for index,clause in enumerate(clauses):
        lower=clause.lower()
        # Evidence-only repository reads are native runtime actions and should
        # not require a separately acquired capability.
        if re.match(r"^(?:read|inspect|open)\b",lower):
            paths=_repo_paths(clause,root)
            existing=[(raw,p) for raw,p in paths if p.is_file()]
            if len(existing)==1:
                action={
                    "type":"read_file",
                    "args":{"path":existing[0][0]},
                    "expect":{"type":"field_nonempty","field":"content"},
                }
                actions.append(action)
                compiled_parts.append({
                    "index":index,"subgoal":clause,"mode":"NATIVE_READ",
                    "path":existing[0][0],
                })
                continue
        try:
            part=_compile_single_goal(clause,registry,root)
        except GoalCompilationFailure as exc:
            raise GoalCompilationFailure(
                "GOAL_COMPILATION_SUBGOAL_UNRESOLVED",
                json.dumps({
                    "index":index,
                    "subgoal":clause,
                    "cause":exc.code,
                    "cause_detail":exc.detail,
                    "clauses":clauses,
                },sort_keys=True)
            ) from exc
        cid=part["selected_capability"]
        entry=registry[cid]
        action=_render_template(entry["action_template"],part["inputs"])
        actions.append(action)
        compiled_parts.append({
            "index":index,
            "subgoal":clause,
            "mode":"VERIFIED_CAPABILITY",
            "selected_capability":cid,
            "inputs":part["inputs"],
            "target_effects":part["target_effects"],
            "score":part["score"],
        })
    actions.append({
        "type":"finish",
        "args":{"summary":"COMPOUND_GOAL_COMPLETE"},
    })
    return {
        "schema":"PROJECT_BRAIN_COMPILED_COMPOUND_GOAL_V1",
        "compiler_mode":"DETERMINISTIC_COMPOUND_ACTION_PLAN",
        "clauses":clauses,
        "compiled_parts":compiled_parts,
        "controller_actions":actions,
        "finish_summary":"COMPOUND_GOAL_COMPLETE",
    }


def compile_goal(goal, registry, root):
    goal=str(goal or "").strip()
    if not goal:
        raise GoalCompilationFailure("GOAL_REQUIRED")
    clauses=decompose_goal(goal)
    if len(clauses)>1:
        return _compile_compound_goal(goal,clauses,registry,root)
    return _compile_single_goal(goal,registry,root)
