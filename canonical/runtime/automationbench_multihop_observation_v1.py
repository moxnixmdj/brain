"""Bounded multi-hop read planner for AutomationBench API mode.

This module adds no mutation capability and no external model cognition.
It expands public api_search endpoint descriptions into deterministic GET calls,
grounds later path parameters from prior GET results, and deduplicates calls.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import quote

from canonical.runtime.automationbench_owned_policy_kernel_v1 import (
    classify,
    parse_search_payload,
    rank_endpoints,
)

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_MULTIHOP_OBSERVATION_V1"


def discovery_search_queries(prompt: str, *, max_queries: int = 6) -> list[str]:
    apps = set(classify(prompt)["apps"])
    if "google_sheets" in apps:
        apps.add("google_drive")

    priority: list[str] = []
    if "salesforce" in apps:
        priority.append("salesforce SOQL query records")
    if "google_drive" in apps:
        priority.append("google drive list files")
    if "google_sheets" in apps:
        priority.append("google sheets get spreadsheet metadata by id")
        priority.append("google sheets batch get cell values ranges")
    if "gmail" in apps:
        priority.append("gmail list mailbox messages")
        priority.append("gmail get message by id")
    if "asana" in apps:
        priority.append("asana projects sections tasks get list")

    prompt_words = [
        w.lower()
        for w in re.findall(r"[A-Za-z0-9_.@:/-]+", prompt)
        if len(w) > 2
    ]
    for app in sorted(apps):
        q = " ".join([app.replace("_", " "), "search", "get", *prompt_words[:5]])
        if q not in priority:
            priority.append(q)
    return priority[:max_queries]


def _flatten_mappings(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, Mapping):
            d = dict(x)
            out.append(d)
            for v in d.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            try:
                walk(json.loads(x))
            except Exception:
                return

    walk(value)
    return out


def _required_parameters(ep: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    params = ep.get("parameters") or {}
    out: list[tuple[str, dict[str, Any]]] = []
    if isinstance(params, Mapping):
        for name, spec0 in params.items():
            if isinstance(spec0, Mapping) and spec0.get("required") is True:
                out.append((str(name), dict(spec0)))
    elif isinstance(params, list):
        for spec0 in params:
            if (
                isinstance(spec0, Mapping)
                and spec0.get("required") is True
                and spec0.get("name")
            ):
                out.append((str(spec0["name"]), dict(spec0)))
    return out


def _prompt_ids(prompt: str) -> list[str]:
    return list(
        dict.fromkeys(
            re.findall(r"\b(?:[A-Za-z]{1,12}[_-])?[A-Za-z0-9]{6,}\b", prompt)
        )
    )


def _ground_from_prompt(name: str, prompt: str) -> str | None:
    low = name.lower().replace("-", "_")
    ids = _prompt_ids(prompt)
    if low in {"userid", "user_id"}:
        return "me"
    if low.endswith(("_id", "_gid")) or low in {
        "id",
        "gid",
        "key",
        "workspace",
        "project",
        "board",
        "base",
        "table",
        "channel",
    }:
        for value in ids:
            if "_" in value or "-" in value or any(ch.isdigit() for ch in value):
                return value
    return None


def _quoted_phrases(prompt: str) -> list[str]:
    return [
        x.strip()
        for x in re.findall(r"['\"]([^'\"]{2,100})['\"]", prompt)
        if x.strip()
    ]


def _observed_values(
    name: str,
    prompt: str,
    observations: Sequence[Any],
    *,
    endpoint_id: str = "",
) -> list[str]:
    low = name.lower().replace("-", "_")
    quoted = [q.lower() for q in _quoted_phrases(prompt)]
    scored: list[tuple[int, str]] = []

    for rec in _flatten_mappings(list(observations)):
        ep = endpoint_id.lower()
        if ep.startswith("gmail.") and low in {"id", "message_id", "messageid"}:
            if not any(k in rec for k in ("threadId", "thread_id", "labelIds", "label_ids")):
                continue
        if ep.startswith("google_drive.") and low in {"id", "file_id", "fileid"}:
            if not any(k in rec for k in ("mimeType", "mime_type", "parents")):
                continue
        if ep.startswith("sheets.") and low in {"spreadsheetid", "spreadsheet_id"}:
            mime = str(rec.get("mimeType") or rec.get("mime_type") or "").lower()
            if (
                "spreadsheetId" not in rec
                and "spreadsheet_id" not in rec
                and "spreadsheet" not in mime
            ):
                continue

        label_parts: list[str] = []
        for key in ("name", "title", "subject"):
            value = rec.get(key)
            if isinstance(value, str):
                label_parts.append(value)
        props = rec.get("properties")
        if isinstance(props, Mapping) and isinstance(props.get("title"), str):
            label_parts.append(str(props["title"]))
        label = " ".join(label_parts).lower()

        values: list[str] = []
        for key, value in rec.items():
            nk = str(key).lower().replace("-", "_")
            if value is None or isinstance(value, (dict, list)):
                continue
            if nk == low:
                values.append(str(value))

        if not values and (
            low.endswith(("_id", "_gid"))
            or low in {
                "id",
                "gid",
                "spreadsheetid",
                "spreadsheet_id",
                "fileid",
                "file_id",
            }
        ):
            for key in (
                "spreadsheetId",
                "spreadsheet_id",
                "fileId",
                "file_id",
                "gid",
                "id",
                "Id",
            ):
                value = rec.get(key)
                if value is not None and not isinstance(value, (dict, list)):
                    values.append(str(value))

        score = 0
        if quoted and any(q in label for q in quoted):
            score += 20
        mime = str(rec.get("mimeType") or rec.get("mime_type") or "").lower()
        if "spreadsheet" in low and "spreadsheet" in mime:
            score += 10
        for value in values:
            if value:
                scored.append((score, value))

    scored.sort(key=lambda item: (-item[0], item[1]))
    if not scored:
        return []
    top_score = scored[0][0]
    if top_score > 0:
        scored = [item for item in scored if item[0] == top_score]
    return list(dict.fromkeys(value for _, value in scored))


def _salesforce_queries(prompt: str) -> list[str]:
    low = prompt.lower()
    objects: list[str] = []
    if any(x in low for x in ("opportunity", "deal", "won", "salesforce")):
        objects.append("Opportunity")
    if any(x in low for x in ("account", "tier", "parent")):
        objects.append("Account")
    if any(x in low for x in ("case", "support", "escalation")):
        objects.append("Case")
    return [f"SELECT * FROM {obj}" for obj in dict.fromkeys(objects)]


def _sheet_targets(observations: Sequence[Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for obs in observations:
        value = obs
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                continue
        if not isinstance(value, Mapping):
            continue
        spreadsheet_id = value.get("spreadsheetId") or value.get("spreadsheet_id")
        sheets = value.get("sheets")
        if not spreadsheet_id or not isinstance(sheets, list):
            continue
        for sheet in sheets:
            if not isinstance(sheet, Mapping):
                continue
            props = sheet.get("properties")
            if isinstance(props, Mapping) and props.get("title"):
                out.append((str(spreadsheet_id), str(props["title"])))
    return list(dict.fromkeys(out))


def call_fingerprint(tool: str, arguments: Mapping[str, Any]) -> str:
    return json.dumps(
        {"tool": tool, "arguments": dict(arguments)},
        sort_keys=True,
        separators=(",", ":"),
    )


def _endpoint_allowed(endpoint_id: str, prompt: str) -> bool:
    low_id = endpoint_id.lower()
    low_prompt = prompt.lower()
    if low_id.startswith("salesforce."):
        return endpoint_id == "salesforce.query"
    if low_id.startswith("google_drive."):
        return endpoint_id == "google_drive.files.list"
    if low_id.startswith("sheets."):
        return endpoint_id in {
            "sheets.spreadsheets.get",
            "sheets.spreadsheets.values.get",
            "sheets.spreadsheets.values.batchGet",
        }
    if low_id.startswith("gmail."):
        if "draft" in low_prompt:
            return "draft" in low_id or low_id in {
                "gmail.users.messages.list",
                "gmail.users.messages.get",
            }
        if "label" in low_prompt:
            return "label" in low_id or low_id in {
                "gmail.users.messages.list",
                "gmail.users.messages.get",
            }
        return endpoint_id in {
            "gmail.users.messages.list",
            "gmail.users.messages.get",
        }
    return True


def observation_expansion_plan(
    prompt: str,
    search_payloads: Iterable[str | Mapping[str, Any]],
    *,
    observations: Sequence[Any] = (),
    already_called: set[str] | None = None,
    max_calls: int = 6,
) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for payload in search_payloads:
        for ep in parse_search_payload(payload):
            key = (str(ep.get("method") or ""), str(ep.get("url") or ""))
            if key in seen:
                continue
            seen.add(key)
            endpoints.append(ep)

    done = already_called or set()
    out: list[dict[str, Any]] = []

    def add(ep: Mapping[str, Any], args: dict[str, Any]) -> None:
        if len(out) >= max_calls:
            return
        fp = call_fingerprint("api_fetch", args)
        if fp in done:
            return
        out.append(
            {
                "tool": "api_fetch",
                "arguments": args,
                "endpoint_id": ep.get("id"),
            }
        )

    for ep in rank_endpoints(prompt, endpoints):
        if len(out) >= max_calls:
            break
        if str(ep.get("method") or "").upper() != "GET":
            continue
        endpoint_id = str(ep.get("id") or "")
        if not _endpoint_allowed(endpoint_id, prompt):
            continue
        base_url = str(ep.get("url") or "")
        if not base_url:
            continue

        if endpoint_id == "salesforce.query":
            for query in _salesforce_queries(prompt):
                add(
                    ep,
                    {
                        "method": "GET",
                        "url": base_url,
                        "params": json.dumps({"q": query}, sort_keys=True),
                    },
                )
            continue

        if endpoint_id == "sheets.spreadsheets.values.batchGet":
            for spreadsheet_id, title in _sheet_targets(observations):
                add(
                    ep,
                    {
                        "method": "GET",
                        "url": base_url.replace(
                            "{spreadsheetId}", quote(spreadsheet_id, safe="")
                        ),
                        "params": json.dumps(
                            {"ranges": [f"{title}!A1:Z1000"]},
                            sort_keys=True,
                        ),
                    },
                )
            continue

        choices: list[tuple[str, dict[str, Any], list[str]]] = []
        valid = True
        for name, spec in _required_parameters(ep):
            default = spec.get("default")
            if default is not None:
                values = [str(default)]
            else:
                low_name = name.lower().replace("-", "_")
                observed_first = low_name in {
                    "id",
                    "gid",
                    "message_id",
                    "messageid",
                    "file_id",
                    "fileid",
                    "spreadsheet_id",
                    "spreadsheetid",
                }
                observed = _observed_values(
                    name,
                    prompt,
                    observations,
                    endpoint_id=endpoint_id,
                )
                prompt_value = _ground_from_prompt(name, prompt)
                if observed_first:
                    values = observed or ([prompt_value] if prompt_value is not None else [])
                else:
                    values = ([prompt_value] if prompt_value is not None else []) or observed
            if not values:
                valid = False
                break
            choices.append((name, spec, values[:max_calls]))
        if not valid:
            continue

        variants: list[tuple[str, dict[str, str]]] = [(base_url, {})]
        for name, spec, values in choices:
            expanded: list[tuple[str, dict[str, str]]] = []
            for current_url, params in variants:
                for value in values:
                    next_url = current_url
                    next_params = dict(params)
                    placeholder = "{" + name + "}"
                    if (
                        str(spec.get("location") or "").lower() == "path"
                        or placeholder in next_url
                    ):
                        if placeholder not in next_url:
                            continue
                        next_url = next_url.replace(
                            placeholder, quote(str(value), safe="")
                        )
                    else:
                        next_params[name] = str(value)
                    expanded.append((next_url, next_params))
                    if len(expanded) >= max_calls:
                        break
                if len(expanded) >= max_calls:
                    break
            variants = expanded
            if not variants:
                break

        for url, params in variants:
            if "{" in url or "}" in url:
                continue
            args: dict[str, Any] = {"method": "GET", "url": url}
            if params:
                args["params"] = json.dumps(params, sort_keys=True)
            add(ep, args)

    return out
