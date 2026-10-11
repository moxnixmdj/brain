"""Generic schema-driven tool argument binder for Project Brain.

The binder turns one planned REST-like endpoint into concrete method/url/params/body
arguments using only:
- the user goal,
- the endpoint's declared schema/description,
- observed world records.

It is benchmark- and vendor-agnostic. Required values that cannot be grounded
cause a fail-closed result instead of guessing.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence
from urllib.parse import quote

SCHEMA = "PROJECT_BRAIN_GENERIC_TOOL_ARGUMENT_BINDER_V1"

_ID_KEYS = {"id","gid","key","record_id","recordid"}
_FIELD_GROUPS = {
    "name": {"name","title","subject","label"},
    "text": {"description","notes","body","text","message","content","comment"},
    "date": {"date","due","due_on","due_date","start","start_date","end","end_date","close_date","activitydate"},
    "status": {"status","stage","stage_name","stagename","state"},
    "priority": {"priority","severity"},
    "project": {"project","projects","project_id","projectid","project_gid"},
    "workspace": {"workspace","workspace_id","workspace_gid"},
    "section": {"section","section_id","section_gid"},
    "task": {"task","tasks","task_id","taskid","task_gid"},
    "tag": {"tag","tags","tag_id","tag_gid"},
    "person": {"assignee","owner","user","member","contact","employee"},
    "email": {"email","recipient","to"},
    "amount": {"amount","total","price","cost","value"},
    "id": _ID_KEYS,
}
_ALIAS_TO_GROUP = {
    alias: group
    for group, aliases in _FIELD_GROUPS.items()
    for alias in aliases
}
_ID_LITERAL = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:[_-][A-Za-z0-9_-]+)+\b")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")


def _norm_name(value: Any) -> str:
    raw = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "")).strip("_").lower()
    return raw


def canonical_field(name: Any) -> str:
    n = _norm_name(name)
    if n in _ALIAS_TO_GROUP:
        return _ALIAS_TO_GROUP[n]
    pieces = [x for x in n.split("_") if x]
    for piece in reversed(pieces):
        if piece in _ALIAS_TO_GROUP:
            return _ALIAS_TO_GROUP[piece]
    return n


def _record_id(record: Mapping[str, Any]) -> str | None:
    for key, value in record.items():
        if _norm_name(key) in _ID_KEYS and isinstance(value, (str, int)):
            text = str(value).strip()
            if text:
                return text
    return None


def _record_text(record: Mapping[str, Any]) -> str:
    pieces: list[str] = []
    for key, value in record.items():
        if isinstance(value, (str, int, float, bool)):
            pieces.append(str(key))
            pieces.append(str(value))
    return " ".join(pieces)


def extract_records(observations: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, str):
            try:
                walk(json.loads(value))
            except Exception:
                return
        elif isinstance(value, Mapping):
            row = dict(value)
            rid = _record_id(row)
            has_content = any(
                canonical_field(k) in {"name","text","status","date","project","section","task"}
                for k in row
            )
            if rid or has_content:
                sig = json.dumps(row, sort_keys=True, default=str)
                if sig not in seen:
                    seen.add(sig)
                    out.append(row)
            for child in row.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for observation in observations:
        walk(observation)
    return out


def _all_text(observations: Sequence[Any]) -> list[str]:
    texts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            texts.append(value)
            try:
                parsed = json.loads(value)
            except Exception:
                return
            walk(parsed)
        elif isinstance(value, Mapping):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for observation in observations:
        walk(observation)
    return texts


def _cue_facts(goal: str, observations: Sequence[Any]) -> dict[str, list[str]]:
    facts: dict[str, list[str]] = {}

    def add(group: str, value: str) -> None:
        value = str(value or "").strip(" \t\r\n.,;")
        if not value:
            return
        facts.setdefault(group, [])
        if value not in facts[group]:
            facts[group].append(value)

    sources = [goal, *_all_text(observations)]
    for text in sources:
        for m in re.finditer(r"\b([A-Za-z][A-Za-z _-]{1,30})\s*:\s*([^\n.]+)", text):
            raw_key = m.group(1).strip()
            value = m.group(2).strip()
            key_low = raw_key.lower()
            if key_low.startswith("create ") or key_low in {"task","item","record"}:
                add("name", value)
            add(canonical_field(raw_key), value)

        for email in _EMAIL.findall(text):
            add("email", email)
        for date in _DATE.findall(text):
            add("date", date)

    # Explicit field assignments in the goal.
    for m in re.finditer(
        r"\b(?:set|change|update|mark)\s+(?:the\s+)?(.{1,80}?)\s+(?:to|as)\s+([^,.;]+)",
        goal,
        flags=re.I,
    ):
        field_phrase = m.group(1).strip()
        value = m.group(2).strip()
        group = canonical_field(field_phrase)
        if group not in _FIELD_GROUPS:
            pieces = [_norm_name(x) for x in field_phrase.split()]
            for piece in reversed(pieces):
                candidate = canonical_field(piece)
                if candidate in _FIELD_GROUPS:
                    group = candidate
                    break
        if group in _FIELD_GROUPS:
            add(group, value)

    # Named section/project/etc. phrases and literal IDs.
    for group in ("project","workspace","section","task","tag"):
        for m in re.finditer(
            r"\b" + group + r"\s+['\"]?([A-Za-z0-9][A-Za-z0-9 _-]{1,60})['\"]?",
            goal,
            flags=re.I,
        ):
            add(group + "_name", m.group(1).strip())
        # Reverse-name form: "<name> section", "<name> project", etc.
        for m in re.finditer(
            r"['\"]?([A-Za-z0-9][A-Za-z0-9 _-]{1,60})['\"]?\s+" + group + r"\b",
            goal,
            flags=re.I,
        ):
            candidate = m.group(1).strip()
            parts = candidate.split()
            connectors = {"to","into","onto","in","under","within","the"}
            cut = -1
            for i, part in enumerate(parts):
                if part.lower() in connectors and i < len(parts) - 1:
                    cut = i
            if cut >= 0:
                parts = parts[cut + 1:]
            parts = parts[-4:]
            candidate = " ".join(parts).strip()
            if candidate:
                add(group + "_name", candidate)
    for literal in _ID_LITERAL.findall(goal):
        add("id_literal", literal)
    return facts


def extract_grounding_facts(goal: str, observations: Sequence[Any]) -> dict[str, list[str]]:
    """Public, read-only view of the binder's grounded semantic facts."""
    return _cue_facts(goal, observations)


def _request_fields(endpoint: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = endpoint.get("requestBody")
    if raw is None:
        raw = endpoint.get("request_body")
    if raw is None:
        raw = endpoint.get("request")

    fields: dict[str, dict[str, Any]] = {}

    def put(name: str, *, required: bool, is_array: bool, raw_spec: Any) -> None:
        name = str(name or "").strip()
        if not name or name in {"data","properties","body"}:
            return
        prev = fields.get(name)
        row = {
            "name": name,
            "required": bool(required),
            "array": bool(is_array),
            "canonical": canonical_field(name),
            "raw": raw_spec,
        }
        if prev is None or (row["required"] and not prev["required"]):
            fields[name] = row

    def from_mapping(value: Any, inherited_required: set[str] | None = None) -> None:
        if not isinstance(value, Mapping):
            return
        required_set = set(str(x) for x in (value.get("required") or [])) if isinstance(value.get("required"), list) else set()
        required_set |= set(inherited_required or set())
        props = value.get("properties")
        if isinstance(props, Mapping):
            for name, spec in props.items():
                is_array = isinstance(spec, Mapping) and str(spec.get("type")) == "array"
                put(str(name), required=str(name) in required_set, is_array=is_array, raw_spec=spec)
                if isinstance(spec, Mapping):
                    from_mapping(spec)
        schema = value.get("schema")
        if isinstance(schema, Mapping):
            from_mapping(schema, required_set)
        content = value.get("content")
        if isinstance(content, Mapping):
            for spec in content.values():
                if isinstance(spec, Mapping):
                    from_mapping(spec, required_set)

    if isinstance(raw, Mapping):
        from_mapping(raw)
    elif isinstance(raw, str):
        text = raw
        for m in re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\((required|optional)[^)]*\)",
            text,
            flags=re.I,
        ):
            desc = m.group(0).lower()
            put(
                m.group(1),
                required=m.group(2).lower() == "required",
                is_array="array" in desc or "list" in desc,
                raw_spec=m.group(0),
            )
        for m in re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_]*)(\?)?\s*:\s*([^,}\]]+)",
            text,
        ):
            desc = m.group(3).lower()
            put(
                m.group(1),
                required=m.group(2) != "?",
                is_array="array" in desc or "list" in desc or desc.strip().startswith("["),
                raw_spec=m.group(0),
            )
    return list(fields.values())


def _param_specs(endpoint: Mapping[str, Any]) -> list[dict[str, Any]]:
    params = endpoint.get("parameters") or {}
    out: list[dict[str, Any]] = []
    if isinstance(params, Mapping):
        for name, spec0 in params.items():
            spec = dict(spec0) if isinstance(spec0, Mapping) else {}
            out.append({
                "name": str(name),
                "required": spec.get("required") is True,
                "default": spec.get("default"),
                "location": str(spec.get("location") or ""),
                "array": str(spec.get("type") or "") == "array",
                "canonical": canonical_field(name),
                "raw": spec,
            })
    elif isinstance(params, list):
        for spec0 in params:
            if not isinstance(spec0, Mapping) or not spec0.get("name"):
                continue
            spec = dict(spec0)
            out.append({
                "name": str(spec["name"]),
                "required": spec.get("required") is True,
                "default": spec.get("default"),
                "location": str(spec.get("location") or spec.get("in") or ""),
                "array": str(spec.get("type") or "") == "array",
                "canonical": canonical_field(spec["name"]),
                "raw": spec,
            })
    return out


def _goal_words(goal: str) -> set[str]:
    return {
        x.lower()
        for x in re.findall(r"[A-Za-z0-9_-]+", goal)
        if len(x) > 2
    }


def _named_record_id(
    semantic: str,
    goal: str,
    facts: Mapping[str, list[str]],
    records: Sequence[Mapping[str, Any]],
) -> str | None:
    desired_names = [x.lower() for x in facts.get(semantic + "_name", [])]
    if semantic == "task":
        desired_names.extend(x.lower() for x in facts.get("name", []))
    goal_words = _goal_words(goal)
    ranked: list[tuple[int, str]] = []
    for record in records:
        rid = _record_id(record)
        if not rid:
            continue
        text = _record_text(record).lower()
        score = 0
        name_values = [
            str(value).strip().lower()
            for key, value in record.items()
            if canonical_field(key) == "name"
            and isinstance(value, (str, int, float))
            and str(value).strip()
        ]
        name_match = False
        for name in desired_names:
            if name and any(name == value for value in name_values):
                score += 30
                name_match = True
        if desired_names and semantic in {"project","workspace","section","task","tag","person"} and not name_match:
            continue
        score += min(20, 2 * len(goal_words & set(re.findall(r"[a-z0-9_-]+", text))))
        keys = {canonical_field(k) for k in record}
        if semantic in keys:
            score += 10
        if score > 0:
            ranked.append((score, rid))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    if not ranked:
        return None
    top_score = ranked[0][0]
    top_ids = sorted({rid for score, rid in ranked if score == top_score})
    if len(top_ids) != 1:
        return None
    return top_ids[0]


def _literal_id_for_semantic(semantic: str, goal: str, facts: Mapping[str, list[str]]) -> str | None:
    aliases = sorted(_FIELD_GROUPS.get(semantic, {semantic}), key=len, reverse=True)
    for alias in aliases:
        m = re.search(
            r"\b" + re.escape(alias.replace("_", " ")) + r"\s+([A-Za-z][A-Za-z0-9_-]{2,})\b",
            goal,
            flags=re.I,
        )
        if m and ("_" in m.group(1) or "-" in m.group(1) or any(ch.isdigit() for ch in m.group(1))):
            return m.group(1)
    for value in facts.get("id_literal", []):
        low = value.lower()
        if low.startswith(semantic[:4]) or low.startswith(semantic):
            return value
    return None


def _bind_semantic_value(
    semantic: str,
    *,
    goal: str,
    facts: Mapping[str, list[str]],
    records: Sequence[Mapping[str, Any]],
) -> Any:
    relation_semantics = {"project","workspace","section","task","tag","person","id"}
    if semantic in relation_semantics:
        literal = _literal_id_for_semantic(semantic, goal, facts)
        if literal is not None:
            return literal
        rid = _named_record_id(semantic, goal, facts, records)
        if rid is not None:
            return rid
        # Human-readable relation names are not valid substitutes for IDs.
        return None

    if facts.get(semantic):
        return facts[semantic][0]

    if semantic == "name":
        if facts.get("name"):
            return facts["name"][0]
        quoted = re.findall(r"['\"]([^'\"]{2,120})['\"]", goal)
        if len(quoted) == 1:
            return quoted[0]

    if semantic == "date":
        dates = _DATE.findall(goal)
        if dates:
            return dates[0]

    if semantic == "email":
        emails = _EMAIL.findall(goal)
        if emails:
            return emails[0]

    return None


def resolve_semantic_reference(
    *,
    semantic: str,
    goal: str,
    observations: Sequence[Any],
) -> Any:
    """Resolve one semantic value using the same fail-closed grounding rules as execution."""
    facts = _cue_facts(goal, observations)
    records = extract_records(observations)
    return _bind_semantic_value(
        semantic,
        goal=goal,
        facts=facts,
        records=records,
    )


def bind_endpoint_call(
    *,
    goal: str,
    endpoint: Mapping[str, Any],
    observations: Sequence[Any],
) -> dict[str, Any]:
    method = str(endpoint.get("method") or "").upper().strip()
    url = str(endpoint.get("url") or endpoint.get("path") or "").strip()
    endpoint_id = str(endpoint.get("id") or endpoint.get("name") or "").strip()
    if not method or not url or not endpoint_id:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "ENDPOINT_ID_METHOD_URL_REQUIRED",
        }

    records = extract_records(observations)
    facts = _cue_facts(goal, observations)
    params: dict[str, Any] = {}
    bindings: dict[str, Any] = {}

    for spec in _param_specs(endpoint):
        name = spec["name"]
        value = spec.get("default")
        source = "default" if value is not None else None
        if value is None:
            value = _bind_semantic_value(
                spec["canonical"],
                goal=goal,
                facts=facts,
                records=records,
            )
            if value is not None:
                source = "grounded"
        if value is None:
            if spec["required"]:
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "status": "UNRESOLVED",
                    "reason": "REQUIRED_PARAMETER_UNGROUNDED:" + name,
                    "endpoint_id": endpoint_id,
                }
            continue
        if spec["array"] and not isinstance(value, list):
            value = [value]
        placeholder = "{" + name + "}"
        is_path = spec["location"].lower() == "path" or placeholder in url
        if is_path:
            if placeholder not in url:
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "status": "FAIL_CLOSED",
                    "reason": "PATH_PLACEHOLDER_MISSING:" + name,
                    "endpoint_id": endpoint_id,
                }
            rendered = ",".join(str(x) for x in value) if isinstance(value, list) else str(value)
            url = url.replace(placeholder, quote(rendered, safe=""))
        else:
            params[name] = value
        bindings["parameter." + name] = {"value": value, "source": source}

    if "{" in url or "}" in url:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNRESOLVED",
            "reason": "UNRESOLVED_PATH_PLACEHOLDER",
            "endpoint_id": endpoint_id,
        }

    body: dict[str, Any] = {}
    for spec in _request_fields(endpoint):
        value = _bind_semantic_value(
            spec["canonical"],
            goal=goal,
            facts=facts,
            records=records,
        )
        if value is None:
            if spec["required"]:
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "status": "UNRESOLVED",
                    "reason": "REQUIRED_BODY_FIELD_UNGROUNDED:" + spec["name"],
                    "endpoint_id": endpoint_id,
                }
            continue
        if spec["array"] and not isinstance(value, list):
            value = [value]
        body[spec["name"]] = value
        bindings["body." + spec["name"]] = {"value": value, "source": "grounded"}

    arguments: dict[str, Any] = {"method": method, "url": url}
    if params:
        arguments["params"] = json.dumps(params, sort_keys=True)
    if body:
        arguments["body"] = json.dumps(body, sort_keys=True)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "BOUND",
        "endpoint_id": endpoint_id,
        "arguments": arguments,
        "bindings": bindings,
        "record_count_considered": len(records),
    }
