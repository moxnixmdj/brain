#!/usr/bin/env python3
"""Fail-closed, zero-model bridge from typed instruction slots to a goal packet.

This module is deliberately not a natural-language interpreter. It compiles an
explicit finite *binding request* into the packet consumed by
``goal_directed_sufficient_knowing_v1.evaluate``. Operands and transformation
families come from an external, inspectable, editable template store; raw prose
is retained as provenance only. Arbitrary or unbounded purpose words fail
closed. It uses only the Python standard library, writes no parameters, opens no
network, and makes no model call.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import pathlib
import re
from typing import Any, Mapping

SCHEMA = "BRAIN_RAW_INSTRUCTION_PURPOSE_BINDER_V1"
GDSK_PACKET_SCHEMA = "PROJECT_BRAIN_GOAL_DIRECTED_SUFFICIENT_KNOWING_PACKET_V1"
GDSK_STORE_SCHEMA = "PROJECT_BRAIN_GOAL_DIRECTED_SUFFICIENT_KNOWLEDGE_STORE_V1"
SOURCE_CLASS_BY_ORIGIN = {
    "DISTINCT_VERIFIER": "independent_verifier",
    "BOUNDED_ENVIRONMENT_SCAN": "authenticated_observation",
    "INSTRUCTION_QUOTED_OPERANDS": "local_guide",
}
ALLOWED_GOAL_FAMILIES = frozenset({
    "CREATE_FILE",
    "REMOVE_LITERAL_LINES",
    "COPY_FILE",
    "MOVE_OR_RENAME_FILE",
    "CHMOD_FILE",
})
ALLOWED_UNIVERSE_SOURCES = frozenset({
    "INSTRUCTION_QUOTED_OPERANDS",
    "BOUNDED_ENVIRONMENT_SCAN",
    "EXTERNAL_TYPED_TEMPLATE",
})
ALLOWED_EVIDENCE_SOURCES = frozenset({
    "INSTRUCTION_QUOTED_OPERANDS",
    "BOUNDED_ENVIRONMENT_SCAN",
    "DISTINCT_VERIFIER",
})
ALLOWED_LABELS = frozenset({"K1_SCOPED_FACT", "K2_UNVERIFIED", "K3_MODEL_DEPENDENT"})
_SAFE_SLOT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_SAFE_TEMPLATE_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SAFE_DOMAIN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9._/ @:+=,()\-]{1,512}$")
_UNBOUNDED_PURPOSE_WORDS = frozenset({
    "anything", "arbitrary", "best", "general", "intelligent", "meaning",
    "understand", "whatever",
})


class BindingRefused(ValueError):
    """A typed, fail-closed refusal; no packet and no environment action."""


def _refuse(code: str, detail: str = "") -> None:
    raise BindingRefused(code + (":" + detail if detail else ""))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _string(value: Any, name: str, *, max_len: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_len:
        _refuse("INVALID_STRING", name)
    if any(ord(ch) < 32 for ch in value):
        _refuse("CONTROL_CHARACTER", name)
    return value


def _typed_dict(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        _refuse("INVALID_OBJECT", name)
    return value


def _typed_list(value: Any, name: str) -> list[Any]:
    if type(value) is not list:
        _refuse("INVALID_ARRAY", name)
    return value


def _bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        _refuse("INVALID_BOOLEAN", name)
    return value


def _unique(values: list[str], name: str) -> None:
    if len(values) != len(set(values)):
        _refuse("DUPLICATE_VALUE", name)


def _validate_identifier(value: Any, regex: re.Pattern[str], name: str) -> str:
    text = _string(value, name, max_len=64)
    if not regex.fullmatch(text):
        _refuse("INVALID_IDENTIFIER", name)
    return text


def _validate_external_store(store: Any, name: str) -> dict[str, Any]:
    obj = _typed_dict(store, name)
    if obj.get("schema") != "BRAIN_EXTERNAL_PURPOSE_TEMPLATE_STORE_V1":
        _refuse("INVALID_EXTERNAL_STORE_SCHEMA", name)
    if obj.get("external_editable") is not True:
        _refuse("EXTERNAL_EDITABLE_NOT_ASSERTED", name)
    if obj.get("facts_or_skills_in_parameters") is not False:
        _refuse("PARAMETER_WAREHOUSE_ASSERTION", name)
    templates = _typed_list(obj.get("templates"), name + ".templates")
    if not templates:
        _refuse("EMPTY_TEMPLATE_STORE", name)
    normalized: list[dict[str, Any]] = []
    seen: list[str] = []
    for i, row in enumerate(templates):
        t = _typed_dict(row, f"template[{i}]")
        tid = _validate_identifier(t.get("template_id"), _SAFE_TEMPLATE_ID, f"template[{i}].template_id")
        seen.append(tid)
        family = _string(t.get("goal_family"), f"template[{i}].goal_family", max_len=64)
        if family not in ALLOWED_GOAL_FAMILIES:
            _refuse("UNSUPPORTED_GOAL_FAMILY", family)
        slots = _typed_list(t.get("required_slots"), f"template[{i}].required_slots")
        slot_names = [_validate_identifier(s, _SAFE_SLOT, f"template[{i}].slot") for s in slots]
        _unique(slot_names, f"template[{i}].required_slots")
        if "path" not in slot_names or "literal" not in slot_names:
            _refuse("TEMPLATE_LACKS_PATH_OR_LITERAL", tid)
        out_actions = _typed_list(t.get("output_actions"), f"template[{i}].output_actions")
        if len(out_actions) < 2:
            _refuse("TEMPLATE_LACKS_DECISION_CONTRAST", tid)
        ids = [_validate_identifier(a.get("id"), _SAFE_SLOT, f"template[{i}].action.id") for a in map(lambda x: _typed_dict(x, f"template[{i}].action"), out_actions)]
        _unique(ids, f"template[{i}].output_actions")
        for a in out_actions:
            _string(a.get("command_template"), f"template[{i}].action.command_template", max_len=4096)
            for field in ("requires_unknown", "requires_value"):
                if field in a:
                    _validate_identifier(a[field], _SAFE_SLOT, f"template[{i}].action.{field}")
        predicate = _typed_dict(t.get("success_predicate"), f"template[{i}].success_predicate")
        if predicate.get("kind") != "BOUNDED_EXACT_STATE":
            _refuse("UNBOUNDED_SUCCESS_PREDICATE", tid)
        _typed_list(predicate.get("checks"), f"template[{i}].predicate.checks")
        normalized.append(copy.deepcopy(row))
    _unique(seen, name + ".template_ids")
    validated = copy.deepcopy(obj)
    validated["templates"] = normalized
    return validated


def load_external_store(path: str | pathlib.Path) -> dict[str, Any]:
    """Load and validate an external editable store; never synthesize templates."""
    p = pathlib.Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _refuse("EXTERNAL_STORE_UNREADABLE", type(exc).__name__)
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        _refuse("EXTERNAL_STORE_INVALID_JSON", type(exc).__name__)
    return _validate_external_store(obj, "external_store")


def _render(template: str, slots: Mapping[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in slots:
            _refuse("MISSING_TEMPLATE_SLOT", key)
        return slots[key]
    return re.sub(r"\{\{([A-Za-z][A-Za-z0-9_]{0,63})\}\}", repl, template)


def _validate_scoped_source(row: Any, name: str, allowed: frozenset[str]) -> dict[str, Any]:
    d = _typed_dict(row, name)
    source = _string(d.get("source"), name + ".source", max_len=128)
    if source not in allowed:
        _refuse("UNSCOPED_OR_FORBIDDEN_SOURCE", source)
    scope = _typed_dict(d.get("scope"), name + ".scope")
    if scope.get("closed_world") is not True:
        _refuse("OPEN_WORLD_SCOPE", name)
    if scope.get("bounded_enumerated") is not True:
        _refuse("UNBOUNDED_ENUMERATION", name)
    evidence = _string(d.get("evidence_ref"), name + ".evidence_ref", max_len=256)
    falsifier = _string(d.get("falsifier"), name + ".falsifier", max_len=256)
    return {"source": source, "scope": dict(scope), "evidence_ref": evidence, "falsifier": falsifier}


def _validate_hypotheses(raw: Any, name: str) -> list[dict[str, Any]]:
    rows = _typed_list(raw, name)
    if len(rows) != 2:
        _refuse("HYPOTHESIS_MODEL_NOT_BINARY", name)
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        d = _typed_dict(row, f"{name}[{i}]")
        hid = _validate_identifier(d.get("id"), _SAFE_SLOT, f"{name}[{i}].id")
        p = d.get("probability")
        if type(p) not in (int, float) or isinstance(p, bool) or not math.isfinite(float(p)) or not 0.0 <= float(p) <= 1.0:
            _refuse("INVALID_PROBABILITY", f"{name}[{i}]")
        utilities = _typed_dict(d.get("utilities"), f"{name}[{i}].utilities")
        normalized_u: dict[str, float] = {}
        for action, utility in utilities.items():
            aid = _validate_identifier(action, _SAFE_SLOT, f"{name}[{i}].utility")
            if type(utility) not in (int, float) or isinstance(utility, bool) or not math.isfinite(float(utility)):
                _refuse("INVALID_UTILITY", aid)
            normalized_u[aid] = float(utility)
        out.append({"id": hid, "probability": float(p), "utilities": normalized_u})
    total = sum(row["probability"] for row in out)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        _refuse("HYPOTHESIS_PROBABILITIES_NOT_NORMALIZED", name)
    return out


def _validate_unknown_evidence(row: Any, name: str) -> dict[str, Any]:
    d = _typed_dict(row, name)
    label = _string(d.get("label"), name + ".label", max_len=64)
    if label not in ALLOWED_LABELS:
        _refuse("INVALID_KNOWLEDGE_LABEL", label)
    if label != "K1_SCOPED_FACT":
        _refuse("NON_K1_UNCERTAINTY", label)
    _bool(d.get("decision_relevant"), name + ".decision_relevant")
    source = _validate_scoped_source(d.get("source"), name + ".source", ALLOWED_EVIDENCE_SOURCES)
    if source["source"] == "DISTINCT_VERIFIER":
        _bool(d.get("distinct_from_producer"), name + ".distinct_from_producer")
    return {
        "label": label,
        "decision_relevant": d["decision_relevant"],
        "source": source,
        "evidence_ref": _string(d.get("evidence_ref"), name + ".evidence_ref", max_len=256),
        "falsifier": _string(d.get("falsifier"), name + ".falsifier", max_len=256),
        "distinct_from_producer": d.get("distinct_from_producer"),
    }


def _validate_binding_request(request: Any) -> dict[str, Any]:
    r = _typed_dict(request, "binding_request")
    if r.get("schema") != "BRAIN_TYPED_PURPOSE_BINDING_REQUEST_V1":
        _refuse("INVALID_REQUEST_SCHEMA")
    raw = _string(r.get("raw_instruction"), "raw_instruction", max_len=8192)
    if any(word in raw.casefold() for word in _UNBOUNDED_PURPOSE_WORDS):
        _refuse("UNBOUNDED_PURPOSE_WORD")
    tid = _validate_identifier(r.get("template_id"), _SAFE_TEMPLATE_ID, "template_id")
    slots_obj = _typed_dict(r.get("quoted_slots"), "quoted_slots")
    slots: dict[str, str] = {}
    for key, value in slots_obj.items():
        slot = _validate_identifier(key, _SAFE_SLOT, "quoted_slots.key")
        text = _string(value, "quoted_slots." + slot, max_len=512)
        if not _SAFE_VALUE.fullmatch(text):
            _refuse("UNSAFE_QUOTED_VALUE", slot)
        slots[slot] = text
    evidence = _validate_scoped_source(r.get("environment_evidence"), "environment_evidence", ALLOWED_UNIVERSE_SOURCES)
    distinct = _validate_scoped_source(r.get("distinct_verifier"), "distinct_verifier", {"DISTINCT_VERIFIER"})
    if _bool(r.get("distinct_from_producer"), "distinct_from_producer") is not True:
        _refuse("DISTINCT_VERIFIER_NOT_ASSERTED")
    seen = _typed_list(r.get("visible_scan_atoms"), "visible_scan_atoms")
    if not seen:
        _refuse("EMPTY_BOUNDED_SCAN")
    atoms = [_string(x, "visible_scan_atoms", max_len=256) for x in seen]
    _unique(atoms, "visible_scan_atoms")
    domain = _validate_identifier(r.get("domain"), _SAFE_DOMAIN, "domain")
    complete = _bool(r.get("action_universe_complete"), "action_universe_complete")
    if not complete:
        _refuse("ACTION_UNIVERSE_INCOMPLETE")
    return {
        "schema": r["schema"],
        "raw_instruction": raw,
        "template_id": tid,
        "quoted_slots": slots,
        "environment_evidence": evidence,
        "distinct_verifier": distinct,
        "distinct_from_producer": True,
        "visible_scan_atoms": atoms,
        "domain": domain,
        "action_universe_complete": complete,
        "hypothesis_model": _validate_hypotheses(r.get("hypothesis_model"), "hypothesis_model"),
        "unknown_evidence": _validate_unknown_evidence(r.get("unknown_evidence"), "unknown_evidence"),
        "query_cost": _validate_query_cost(r.get("query_cost"), "query_cost"),
    }


def _validate_query_cost(value: Any, name: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)) or float(value) < 0.0:
        _refuse("INVALID_QUERY_COST", name)
    return float(value)


def _find_template(store: Mapping[str, Any], template_id: str) -> dict[str, Any]:
    for row in store["templates"]:
        if row["template_id"] == template_id:
            return copy.deepcopy(row)
    _refuse("TEMPLATE_NOT_IN_EXTERNAL_STORE", template_id)


def _assert_slot_closure(template: Mapping[str, Any], slots: Mapping[str, str], raw: str) -> None:
    required = set(template["required_slots"])
    supplied = set(slots)
    if required != supplied:
        _refuse("SLOT_CLOSURE_MISMATCH", ",".join(sorted(required ^ supplied)))
    for slot, value in slots.items():
        # Every typed slot must be explicitly present in quoted source text.
        if not any(value in span for span in re.findall(r"`([^`]{1,4096})`", raw)):
            _refuse("SLOT_NOT_QUOTED_IN_RAW_INSTRUCTION", slot)
        if slot == "path":
            if value.startswith("~") or ".." in pathlib.PurePosixPath(value).parts:
                _refuse("UNSAFE_PATH_SLOT", value)
            if value.startswith("/") and not value.startswith(("/app/", "/workspace/", "/root/")):
                _refuse("UNSAFE_PATH_SLOT", value)
            if any(marker in value.casefold() for marker in ("tests/", "test/", "solution/", "verifier/", ".git/")):
                _refuse("HIDDEN_OR_FORBIDDEN_PATH_SLOT", value)


def build_packet(request: Any, external_store: Any) -> dict[str, Any]:
    """Compile a typed request and an external template into a GDSK packet.

    On any ambiguity, missing scoped evidence, unsupported transformation,
    open-world claim or hidden source, raise ``BindingRefused``. This function
    never asks a user/model and never interprets prose into semantics. The
    output is the exact packet shape consumed by
    ``goal_directed_sufficient_knowing_v1.evaluate``.
    """
    r = _validate_binding_request(request)
    store = _validate_external_store(external_store, "external_store")
    t = _find_template(store, r["template_id"])
    _assert_slot_closure(t, r["quoted_slots"], r["raw_instruction"])

    uncertainty = _typed_dict(t.get("uncertainty", {}), "template.uncertainty")
    unknown = _validate_identifier(uncertainty.get("unknown"), _SAFE_SLOT, "template.uncertainty.unknown")
    values = [
        _validate_identifier(v, _SAFE_SLOT, "template.uncertainty.value")
        for v in _typed_list(uncertainty.get("values"), "template.uncertainty.values")
    ]
    _unique(values, "template.uncertainty.values")
    if len(values) != len(r["hypothesis_model"]):
        _refuse("UNCERTAINTY_HYPOTHESIS_MISMATCH")
    if sorted(h["id"] for h in r["hypothesis_model"]) != sorted(values):
        _refuse("HYPOTHESIS_VALUE_MISMATCH")

    u = r["unknown_evidence"]
    if u["decision_relevant"] is not True:
        _refuse("UNKNOWN_NOT_DECISION_RELEVANT")
    source_class = SOURCE_CLASS_BY_ORIGIN.get(u["source"]["source"])
    if not source_class:
        _refuse("UNKNOWN_SOURCE_CLASS_NOT_K1")
    predicate = _typed_dict(t.get("success_predicate"), "template.success_predicate")
    checks = [_string(x, "template.predicate.check", max_len=256) for x in _typed_list(predicate.get("checks"), "template.predicate.checks")]
    if not checks:
        _refuse("EMPTY_SUCCESS_PREDICATE")

    actions: list[dict[str, Any]] = []
    for row in t["output_actions"]:
        command = _render(row["command_template"], r["quoted_slots"])
        action: dict[str, Any] = {
            "id": row["id"],
            "requires": [unknown],
            "effect": t["goal_family"].casefold().replace("_", " ") + ":" + row["id"],
            "command": command,
        }
        for field in ("requires_unknown", "requires_value"):
            if field in row:
                action[field] = row[field]
        if action.get("requires_unknown") != unknown:
            _refuse("ACTION_UNKNOWN_MISMATCH", row["id"])
        if action.get("requires_value") not in values:
            _refuse("ACTION_VALUE_NOT_IN_BOUNDED_ENUMERATION", row["id"])
        actions.append(action)
    action_ids = [a["id"] for a in actions]
    for h in r["hypothesis_model"]:
        if set(h["utilities"]) != set(action_ids):
            _refuse("UTILITY_MODEL_ACTION_MISMATCH", h["id"])

    scan = [
        {
            "id": "scan_" + str(i),
            "content": atom,
            "decision_terms": [r["domain"], unknown, t["goal_family"].casefold().replace("_", " "), "path", "literal"],
        }
        for i, atom in enumerate(r["visible_scan_atoms"])
    ]
    template_sha = canonical_sha256(t)
    store_sha = canonical_sha256(store)
    packet: dict[str, Any] = {
        "schema": GDSK_PACKET_SCHEMA,
        "goal": {
            "id": "BOUNDED_" + t["goal_family"],
            "effect": t["goal_family"].casefold().replace("_", " "),
            "success_predicate": "BOUNDED_EXACT_STATE:" + ";".join(checks),
            "value": 1.0,
            "risk": 1.0,
            "source": "EXTERNAL_TYPED_TEMPLATE_PLUS_QUOTED_INSTRUCTION_SLOTS",
            "source_sha256": canonical_sha256({"template": t, "raw_instruction": r["raw_instruction"]}),
            "falsifier": r["distinct_verifier"]["falsifier"],
        },
        "environment": {
            "id": "bounded-scan-" + canonical_sha256({"atoms": r["visible_scan_atoms"], "domain": r["domain"]})[:16],
            "environment_class": r["domain"],
            "recompute_terms": list(r["visible_scan_atoms"]),
        },
        "store": {
            "schema": GDSK_STORE_SCHEMA,
            "facts": [],
            "relations": [],
            "template_store_sha256": store_sha,
        },
        "actions": actions,
        "unknowns": [
            {
                "id": unknown,
                "source_class": source_class,
                "falsifier": u["falsifier"],
                "bounded_enumeration": True,
                "completeness_required": True,
                "cost": r["query_cost"],
                "hypotheses": r["hypothesis_model"],
                "action_values": dict(r["hypothesis_model"][0]["utilities"]),
                "ready_made_plan": False,
                "ready_made_answer": False,
                "model_call_required": False,
            }
        ],
        "scan": scan,
        "independent_verifier_present": True,
        "producer_id": "arena-agent:raw-instruction-purpose-binder-v1",
        "verifier_id": "distinct-verifier:" + r["distinct_verifier"]["evidence_ref"],
        "max_queries": 1,
        "binding_provenance": {
            "binder_schema": SCHEMA,
            "raw_instruction_sha256": sha256_text(r["raw_instruction"]),
            "quoted_slots_sha256": canonical_sha256(r["quoted_slots"]),
            "external_store_sha256": store_sha,
            "template_id": t["template_id"],
            "template_sha256": template_sha,
            "typed_action_quotient": {
                "complete": r["action_universe_complete"],
                "source": r["environment_evidence"]["source"],
                "closed_world": True,
                "bounded_enumerated": True,
                "atoms": list(r["visible_scan_atoms"]),
                "actions": [dict(a) for a in actions],
                "unknown": {"id": unknown, "values": values, "evidence": u},
            },
            "distinct_verifier": r["distinct_verifier"],
            "producer_is_verifier": False,
            "model_calls": 0,
            "runtime_network_calls": 0,
            "parameters_written": 0,
            "trajectory_saved": False,
            "world_fact_warehouse": False,
        },
    }
    return packet

def build_refusal(request: Any, external_store: Any, error: BindingRefused) -> dict[str, Any]:
    """Return a provenance-only refusal that cannot be mistaken for a packet."""
    raw = request.get("raw_instruction", "") if isinstance(request, dict) else ""
    store_sha = canonical_sha256(external_store) if isinstance(external_store, (dict, list)) else ""
    return {
        "schema": "BRAIN_TYPED_PURPOSE_BINDING_REFUSAL_V1",
        "status": "REFUSED__NO_ACTION_QUOTIENT",
        "reason": str(error),
        "raw_instruction_sha256": sha256_text(raw if isinstance(raw, str) else ""),
        "external_store_sha256": store_sha,
        "packet": None,
        "model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
    }


def compile_request(request: Any, external_store: Any) -> dict[str, Any]:
    """Compile or fail closed; callers must not execute on a refusal."""
    try:
        packet = build_packet(request, external_store)
    except BindingRefused as exc:
        return build_refusal(request, external_store, exc)
    return {
        "schema": "BRAIN_TYPED_PURPOSE_BINDING_RESULT_V1",
        "status": "BOUND__TYPED_ACTION_QUOTIENT",
        "binder_schema": SCHEMA,
        "packet": packet,
        "raw_instruction_sha256": sha256_text(request["raw_instruction"]),
        "external_store_sha256": canonical_sha256(external_store),
        "model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "trajectory_saved": False,
        "world_fact_warehouse": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="Path to a typed binding request JSON")
    parser.add_argument("--store", required=True, help="Path to the external editable template store JSON")
    parser.add_argument("--out", required=True, help="Path for the result or refusal JSON")
    args = parser.parse_args(argv)
    try:
        request = json.loads(pathlib.Path(args.request).read_text(encoding="utf-8"))
        store = load_external_store(args.store)
    except (OSError, UnicodeError, json.JSONDecodeError, BindingRefused) as exc:
        result = build_refusal({}, {}, BindingRefused("INPUT_UNREADABLE:" + type(exc).__name__ + ":" + str(exc)[:160]))
    else:
        result = compile_request(request, store)
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "reason": result.get("reason", ""), "out": args.out}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
