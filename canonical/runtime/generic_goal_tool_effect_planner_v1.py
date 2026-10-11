"""Generic goal-to-tool-effect planner for Project Brain.

This module is benchmark-agnostic. It converts:
  plain-language goals -> action intents
  arbitrary REST-like tool schemas -> coarse effect capabilities
and reuses Brain's existing capability_planner for minimum-cost composition.

It does not execute tools, inspect hidden benchmark assertions, or contain
application/task-specific literals. Unknown or ambiguous routes fail closed.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities

SCHEMA = "PROJECT_BRAIN_GENERIC_GOAL_TOOL_EFFECT_PLANNER_V1"

_STOP = {
    "a","an","the","to","of","for","from","with","in","on","at","by","as",
    "it","its","this","that","these","those","and","or","then","please","our",
    "my","your","their","all","any","each","into","onto","using","use","before",
    "after","once","when","where","which","who","what","is","are","be","been",
}
_ACTION_WORDS = {
    "observe": ("find","get","lookup","search","list","read","review","inspect","check","verify","confirm"),
    "notify": ("send","notify","message","reply","alert"),
    "delete": ("delete","remove","void","cancel","archive","unsubscribe"),
    "update": ("mark","update","change","set","edit","correct","close","flag"),
    "associate": ("attach","assign","move","route","link","apply"),
    "create": ("create","add","log","record","post","schedule","open","make","submit","append","insert"),
}
_ALL_ACTION_TERMS = {x for xs in _ACTION_WORDS.values() for x in xs}
_GENERIC_RESOURCE = {
    "data","record","records","item","items","thing","things","field","fields",
    "value","values","api","endpoint","endpoints","tool","tools","workspace",
}
_NEGATION = re.compile(r"(?:do\s+not|don't|dont|must\s+not|never)\s+$", re.I)


def _singular(token: str) -> str:
    t = token.lower().strip("_-.")
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    # Preserve common singular nouns whose lexical form ends in s.
    if t.endswith(("status", "analysis", "basis", "crisis", "thesis", "diagnosis")):
        return t
    if len(t) > 4 and t.endswith(("sses", "ss")):
        return t
    if len(t) > 4 and t.endswith("s"):
        return t[:-1]
    return t


def _tokens(value: Any) -> list[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", str(value or ""))
    out: list[str] = []
    for token in raw:
        t = _singular(token)
        if len(t) < 2 or t in _STOP:
            continue
        out.append(t)
    return out


def _resource_terms(value: Any) -> list[str]:
    out: list[str] = []
    for t in _tokens(value):
        if t in _ALL_ACTION_TERMS or t in _GENERIC_RESOURCE:
            continue
        if t not in out:
            out.append(t)
    return out


def _split_clauses(goal: str) -> list[str]:
    parts = re.split(r"\s*(?:[.;]\s+|\bthen\b|\band\s+then\b)\s*", str(goal or ""), flags=re.I)
    return [x.strip(" ,") for x in parts if x and x.strip(" ,")]


def _action_hits(clause: str) -> list[tuple[int, str, str, bool]]:
    low = clause.lower()
    hits: list[tuple[int, str, str, bool]] = []
    for action, words in _ACTION_WORDS.items():
        for word in words:
            for m in re.finditer(r"\b" + re.escape(word) + r"\b", low):
                resolved = action
                if word == "add":
                    tail = low[m.end():]
                    if re.search(r"\b(?:to|into|onto)\b", tail):
                        resolved = "associate"
                prefix = low[max(0, m.start() - 24):m.start()]
                forbidden = _NEGATION.search(prefix) is not None
                hits.append((m.start(), resolved, word, forbidden))
    hits.sort(key=lambda x: (x[0], x[1], x[2]))
    dedup: list[tuple[int, str, str, bool]] = []
    seen: set[tuple[str, bool]] = set()
    for row in hits:
        key = (row[1], row[3])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(row)
    return dedup


def compile_goal_contract(goal: str) -> dict[str, Any]:
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("GOAL_REQUIRED")
    intents: list[dict[str, Any]] = []
    for clause_index, clause in enumerate(_split_clauses(goal)):
        terms = _resource_terms(clause)
        for _, action, trigger, forbidden in _action_hits(clause):
            intent_id = "intent_" + str(len(intents))
            intents.append({
                "id": intent_id,
                "clause_index": clause_index,
                "clause": clause,
                "action_class": action,
                "trigger": trigger,
                "resource_terms": terms,
                "forbidden": forbidden,
            })
    if not intents:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "goal": goal,
            "intents": [],
            "reason": "NO_ACTION_INTENT_COMPILED",
        }
    positive = [x for x in intents if not x["forbidden"]]
    return {
        "schema": SCHEMA,
        "status": "COMPILED" if positive else "NO_POSITIVE_ACTION_REQUIRED",
        "goal": goal,
        "intents": intents,
        "positive_intent_ids": [x["id"] for x in positive],
        "forbidden_intent_ids": [x["id"] for x in intents if x["forbidden"]],
    }


def _flatten_schema_text(endpoint: Mapping[str, Any]) -> str:
    pieces = [
        endpoint.get("id"),
        endpoint.get("method"),
        endpoint.get("url"),
        endpoint.get("path"),
        endpoint.get("description"),
        json.dumps(endpoint.get("parameters") or {}, sort_keys=True),
        endpoint.get("request"),
        endpoint.get("requestBody"),
        endpoint.get("request_body"),
        endpoint.get("response"),
    ]
    return " ".join(str(x or "") for x in pieces)


def _endpoint_action(method: str, text: str) -> str:
    method = method.upper()
    low = text.lower()
    if method == "GET":
        return "observe"
    if method == "DELETE":
        return "delete"
    if method in {"PATCH", "PUT"}:
        return "update"
    if method == "POST":
        if any(x in low for x in ("send", "deliver", "notify", "message", "reply")):
            return "notify"
        if any(x in low for x in (
            "addtask","addtag","add task","add tag","attach","assign","move ",
            "link ","apply ","associate","membership","copyto","copy to",
        )):
            return "associate"
        return "create"
    return "mutate"


def profile_endpoint(endpoint: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(endpoint, Mapping):
        raise ValueError("ENDPOINT_OBJECT_REQUIRED")
    eid = str(endpoint.get("id") or endpoint.get("name") or "").strip()
    method = str(endpoint.get("method") or "").upper().strip()
    url = str(endpoint.get("url") or endpoint.get("path") or "").strip()
    if not eid or not method or not url:
        raise ValueError("ENDPOINT_ID_METHOD_URL_REQUIRED")
    text = _flatten_schema_text(endpoint)
    return {
        "id": eid,
        "method": method,
        "url": url,
        "action_class": _endpoint_action(method, text),
        "resource_terms": _resource_terms(text),
        "raw": dict(endpoint),
    }


def _overlap(intent: Mapping[str, Any], profile: Mapping[str, Any]) -> list[str]:
    a = set(str(x) for x in intent.get("resource_terms") or [])
    b = set(str(x) for x in profile.get("resource_terms") or [])
    return sorted(a & b)


def _compatibility(intent: Mapping[str, Any], profile: Mapping[str, Any]) -> tuple[int, list[str]] | None:
    action = str(intent.get("action_class") or "")
    endpoint_action = str(profile.get("action_class") or "")
    overlap = _overlap(intent, profile)
    if not overlap:
        return None
    if action == "observe":
        if endpoint_action != "observe":
            return None
        base = 24
    elif action != endpoint_action:
        return None
    else:
        base = 30
    return base + min(20, 4 * len(overlap)), overlap


def _done(intent_id: str) -> str:
    return "goal." + intent_id + ".satisfied"


def _grounded(intent_id: str) -> str:
    return "goal." + intent_id + ".grounded"


def build_planning_problem(goal: str, endpoints: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    contract = compile_goal_contract(goal)
    positive = [x for x in contract.get("intents") or [] if not x.get("forbidden")]
    if not positive:
        return {
            "schema": SCHEMA,
            "status": contract.get("status"),
            "contract": contract,
            "problem": None,
            "capability_meta": {},
            "endpoint_profiles": [],
        }

    profiles: list[dict[str, Any]] = []
    for endpoint in endpoints:
        try:
            profiles.append(profile_endpoint(endpoint))
        except ValueError:
            continue

    capability_meta: dict[str, dict[str, Any]] = {}
    capabilities: list[dict[str, Any]] = []
    route_ambiguities: list[dict[str, Any]] = []

    # One observation endpoint can ground multiple later state-changing intents.
    for profile in profiles:
        if profile["action_class"] != "observe":
            continue
        provides: set[str] = set()
        scores: list[int] = []
        matched_intents: list[str] = []
        for intent in positive:
            comp = _compatibility(intent, profile)
            overlap = _overlap(intent, profile)
            if intent["action_class"] == "observe" and comp is not None:
                provides.add(_done(intent["id"]))
                scores.append(comp[0])
                matched_intents.append(intent["id"])
            elif intent["action_class"] != "observe" and overlap:
                provides.add(_grounded(intent["id"]))
                scores.append(12 + min(16, 3 * len(overlap)))
                matched_intents.append(intent["id"])
        if not provides:
            continue
        cid = "observe::" + profile["id"]
        cost = max(0.2, 1.2 - (max(scores) / 100.0))
        capabilities.append({
            "id": cid,
            "requires": [],
            "provides": sorted(provides),
            "cost": cost,
            "action": {
                "type": "dynamic_tool_endpoint",
                "args": {"endpoint_id": profile["id"]},
            },
            "result_fields": [],
        })
        capability_meta[cid] = {
            "role": "observation",
            "endpoint_id": profile["id"],
            "method": profile["method"],
            "url": profile["url"],
            "matched_intents": matched_intents,
            "score": max(scores),
        }

    for intent in positive:
        if intent["action_class"] == "observe":
            continue
        compatible: list[tuple[int, list[str], dict[str, Any]]] = []
        for profile in profiles:
            comp = _compatibility(intent, profile)
            if comp is None:
                continue
            score, overlap = comp
            compatible.append((score, overlap, profile))
        if compatible:
            best_score = max(row[0] for row in compatible)
            top = [row for row in compatible if row[0] == best_score]
            top_ids = sorted({row[2]["id"] for row in top})
            if len(top_ids) > 1:
                route_ambiguities.append({
                    "intent_id": intent["id"],
                    "action_class": intent["action_class"],
                    "score": best_score,
                    "endpoint_ids": top_ids,
                })
                continue
        for score, overlap, profile in compatible:
            cid = "act::" + intent["id"] + "::" + profile["id"]
            capabilities.append({
                "id": cid,
                "requires": [_grounded(intent["id"])],
                "provides": [_done(intent["id"])],
                "cost": max(0.25, 1.5 - (score / 100.0)),
                "action": {
                    "type": "dynamic_tool_endpoint",
                    "args": {"endpoint_id": profile["id"]},
                },
                "result_fields": [],
            })
            capability_meta[cid] = {
                "role": "mutation",
                "endpoint_id": profile["id"],
                "method": profile["method"],
                "url": profile["url"],
                "intent_id": intent["id"],
                "action_class": intent["action_class"],
                "overlap": overlap,
                "score": score,
            }

    problem = {
        "initial_facts": [],
        "target_effects": [_done(x["id"]) for x in positive],
        "capabilities": capabilities,
        "max_expansions": 10000,
    }
    return {
        "schema": SCHEMA,
        "status": "READY",
        "contract": contract,
        "problem": problem,
        "capability_meta": capability_meta,
        "endpoint_profiles": profiles,
        "route_ambiguities": route_ambiguities,
    }


def plan_goal_over_tool_schemas(goal: str, endpoints: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    built = build_planning_problem(goal, endpoints)
    if built.get("problem") is None:
        return {
            **built,
            "pass": built.get("status") == "NO_POSITIVE_ACTION_REQUIRED",
            "plan": [],
            "steps": [],
        }
    if built.get("route_ambiguities"):
        return {
            **built,
            "status": "UNRESOLVED",
            "pass": False,
            "reason": "AMBIGUOUS_TOP_TOOL_EFFECT_ROUTE",
            "plan": [],
            "steps": [],
        }
    problem = built["problem"]
    if not problem.get("capabilities"):
        return {
            **built,
            "status": "UNRESOLVED",
            "pass": False,
            "reason": "NO_COMPATIBLE_TOOL_EFFECTS",
            "plan": [],
            "steps": [],
        }
    try:
        planned = plan_capabilities(problem)
    except PlanningFailure as exc:
        return {
            **built,
            "status": "UNRESOLVED",
            "pass": False,
            "reason": exc.code + ((":" + str(exc.detail)) if exc.detail else ""),
            "plan": [],
            "steps": [],
        }

    steps: list[dict[str, Any]] = []
    meta = built["capability_meta"]
    for cid in planned["plan"]:
        row = dict(meta.get(cid) or {})
        row["capability_id"] = cid
        steps.append(row)
    return {
        **built,
        "status": "PLANNED",
        "pass": True,
        "planning": planned,
        "plan": list(planned["plan"]),
        "steps": steps,
        "observation_endpoint_ids": [
            x["endpoint_id"] for x in steps if x.get("role") == "observation"
        ],
        "mutation_endpoint_ids": [
            x["endpoint_id"] for x in steps if x.get("role") == "mutation"
        ],
    }


def endpoint_rows_from_search_payloads(payloads: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for payload in payloads:
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                continue
        if not isinstance(payload, Mapping):
            continue
        rows = payload.get("results")
        if not isinstance(rows, list):
            continue
        for raw in rows:
            if not isinstance(raw, Mapping):
                continue
            row = dict(raw)
            key = (
                str(row.get("id") or row.get("name") or ""),
                str(row.get("method") or ""),
                str(row.get("url") or row.get("path") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
    return out
