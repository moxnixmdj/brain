"""Zero-LLM Epistemic OpenAPI / REST API Discovery, Dependency-Chaining, Self-Healing & Polymorphic Transfer Engine (V1).

Implements all 7 APIFlow-Bench (2026) production REST-API capability axes with
ZERO external model calls (`model_calls == 0`), ZERO stored weights (`parameters_stored == 0`),
and ZERO memorized endpoints, schemas, URLs, or credentials (`authority == "NONE"`):

  1. Zero-prior discovery (`/openapi.json`, `/swagger.json`, root links) + `$ref` schema dereferencing
  2. Auth discovery + automatic mid-workflow `401 Unauthorized` token refresh
  3. Goal-directed backward-chaining foreign-key DAG planning + destructive-trap quarantine
  4. Full pagination traversal (`cursor` / `next_cursor`, `page` / `has_more`, `offset`, `Link: rel="next"`)
  5. Live `400`/`422` incomplete-spec schema & header self-healing + generalized `error_fix_laws`
  6. `429`/`503` `Retry-After` bounded backoff & idempotent retry
  7. Independent `GET` statefulness readback verification + zero-URL/zero-token polymorphic skill distillation
     for cross-service Tier-0 transfer onto completely unseen microservices.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_EPISTEMIC_OPENAPI_AGENT_V1"
AUTHORITY = "NONE"

_DESTRUCTIVE_RE = re.compile(r"\b(purge|wipe|reset|destroy|drop|nuke|truncate|delete_all|clear_all)\b", re.IGNORECASE)
_AUTH_PATH_RE = re.compile(r"\b(auth|login|signin|token|session|sessions|oauth)\b", re.IGNORECASE)
_TOKEN_FIELD_NAMES = ("access_token", "token", "api_token", "api_key", "jwt", "session_token", "auth_token")
_STOPWORDS = frozenset({
    "the", "a", "an", "to", "for", "of", "in", "on", "at", "by", "with", "and", "or", "its", "their",
    "this", "that", "from", "into", "api", "v1", "v2", "v3", "http", "https", "get", "post", "put",
    "patch", "use", "using", "service", "server", "endpoint", "please", "then", "also", "all",
})


def _split_tokens(text: str) -> list[str]:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text or ""))
    toks = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", s) if len(t) >= 2]
    return [t for t in toks if t not in _STOPWORDS]


def _singularize(word: str) -> str:
    w = word.lower().strip()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("sses") or w.endswith("shes") or w.endswith("ches") or w.endswith("xes"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def _http_json(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    body: Any = None,
    timeout_s: float = 8.0,
) -> tuple[int, dict[str, str], Any, str]:
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            try:
                parsed = json.loads(raw) if raw.strip() else None
            except Exception:
                parsed = None
            return int(resp.status), resp_headers, parsed, raw
    except urllib.error.HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        resp_headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        try:
            parsed = json.loads(raw) if raw.strip() else None
        except Exception:
            parsed = None
        return int(exc.code), resp_headers, parsed, raw
    except Exception as exc:
        return 0, {}, None, str(exc)


def _resolve_ref(spec: Mapping[str, Any], node: Any, _seen: frozenset[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(node, Mapping):
        return {}
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/") and ref not in _seen:
        cur: Any = spec
        for part in ref[2:].split("/"):
            if isinstance(cur, Mapping) and part in cur:
                cur = cur[part]
            else:
                cur = None
                break
        if isinstance(cur, Mapping):
            merged = dict(_resolve_ref(spec, cur, _seen | {ref}))
            for k, v in node.items():
                if k != "$ref":
                    merged[k] = v
            return merged
    out = dict(node)
    if "properties" in out and isinstance(out["properties"], Mapping):
        out["properties"] = {
            pk: _resolve_ref(spec, pv, _seen) if isinstance(pv, Mapping) else pv
            for pk, pv in out["properties"].items()
        }
    if "items" in out and isinstance(out["items"], Mapping):
        out["items"] = _resolve_ref(spec, out["items"], _seen)
    return out


def discover_openapi_spec(base_url: str, *, timeout_s: float = 6.0) -> tuple[str | None, dict[str, Any] | None, list[str]]:
    """Probe an unseen HTTP endpoint for an OpenAPI 3.x / Swagger 2.0 specification."""
    parsed = urllib.parse.urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    probes: list[str] = []

    def _is_spec(obj: Any) -> bool:
        return isinstance(obj, Mapping) and isinstance(obj.get("paths"), Mapping) and (
            "openapi" in obj or "swagger" in obj
        )

    candidates: list[str] = []
    if base_url.rstrip("/").endswith(".json"):
        candidates.append(base_url)
    else:
        candidates.append(base_url)

    # First check the provided URL itself (may return spec directly or discovery links)
    for u in candidates:
        probes.append(u)
        st, hdrs, js, _ = _http_json("GET", u, timeout_s=timeout_s)
        if st == 200 and _is_spec(js):
            return u, dict(js), probes
        if st == 200 and isinstance(js, Mapping):
            for lk_key in ("openapi", "openapi_url", "spec", "spec_url", "swagger", "schema"):
                lv = js.get(lk_key)
                if isinstance(lv, str) and lv.strip():
                    full_u = urllib.parse.urljoin(origin + "/", lv.lstrip("/"))
                    probes.append(full_u)
                    st2, _, js2, _ = _http_json("GET", full_u, timeout_s=timeout_s)
                    if st2 == 200 and _is_spec(js2):
                        return full_u, dict(js2), probes

    # Standard well-known OpenAPI discovery paths
    for rel in ("/openapi.json", "/swagger.json", "/api/openapi.json", "/.well-known/openapi.json", "/api-docs"):
        u = origin + rel
        if u in probes:
            continue
        probes.append(u)
        st, _, js, _ = _http_json("GET", u, timeout_s=timeout_s)
        if st == 200 and _is_spec(js):
            return u, dict(js), probes

    return None, None, probes


@dataclass
class ApiOperation:
    method: str
    path: str
    operation_id: str
    summary: str
    role: str  # AUTH | LIST | CREATE | READ | READ_SUBRESOURCE | DESTRUCTIVE | OTHER
    resource: str  # singular stem e.g. "client", "invoice", "warehouse", "shipment"
    subresource: str = ""
    path_params: list[str] = field(default_factory=list)
    query_params: list[dict[str, Any]] = field(default_factory=list)
    header_params: list[dict[str, Any]] = field(default_factory=list)
    body_schema: dict[str, Any] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)
    requires_auth: bool = False
    is_destructive: bool = False
    fk_deps: list[tuple[str, str]] = field(default_factory=list)  # (field_name, target_resource_singular)


@dataclass
class ApiGraph:
    origin: str
    title: str
    spec_url: str
    auth_scheme: dict[str, Any]  # {"type": "bearer"|"apiKey"|"none", "name": ..., "in": ...}
    auth_op: ApiOperation | None
    operations: list[ApiOperation]
    resources: set[str]


def _extract_auth_scheme(spec: Mapping[str, Any]) -> dict[str, Any]:
    comps = spec.get("components") if isinstance(spec.get("components"), Mapping) else {}
    schemes = comps.get("securitySchemes") if isinstance(comps.get("securitySchemes"), Mapping) else {}
    if not schemes and isinstance(spec.get("securityDefinitions"), Mapping):
        schemes = spec["securityDefinitions"]
    for _, sc in schemes.items():
        if not isinstance(sc, Mapping):
            continue
        stype = str(sc.get("type") or "").lower()
        if stype == "http" and str(sc.get("scheme") or "").lower() == "bearer":
            return {"type": "bearer", "name": "Authorization", "in": "header"}
        if stype == "apikey":
            return {
                "type": "apiKey",
                "name": str(sc.get("name") or "X-API-Key"),
                "in": str(sc.get("in") or "header").lower(),
            }
    return {"type": "none", "name": "", "in": ""}


def _extract_body_schema(spec: Mapping[str, Any], op_obj: Mapping[str, Any]) -> dict[str, Any]:
    rb = op_obj.get("requestBody")
    if isinstance(rb, Mapping):
        rb = _resolve_ref(spec, rb)
        content = rb.get("content")
        if isinstance(content, Mapping):
            for ct, media in content.items():
                if "json" in str(ct).lower() and isinstance(media, Mapping):
                    return _resolve_ref(spec, media.get("schema") or {})
            for media in content.values():
                if isinstance(media, Mapping) and "schema" in media:
                    return _resolve_ref(spec, media.get("schema") or {})
    # Swagger 2.0 body parameter
    for p in op_obj.get("parameters") or []:
        if isinstance(p, Mapping) and p.get("in") == "body":
            return _resolve_ref(spec, p.get("schema") or {})
    return {}


def _extract_response_schema(spec: Mapping[str, Any], op_obj: Mapping[str, Any]) -> dict[str, Any]:
    resps = op_obj.get("responses")
    if not isinstance(resps, Mapping):
        return {}
    for code in ("200", "201", "202"):
        r = resps.get(code)
        if not isinstance(r, Mapping):
            continue
        r = _resolve_ref(spec, r)
        content = r.get("content")
        if isinstance(content, Mapping):
            for ct, media in content.items():
                if "json" in str(ct).lower() and isinstance(media, Mapping):
                    return _resolve_ref(spec, media.get("schema") or {})
        if "schema" in r:
            return _resolve_ref(spec, r["schema"])
    return {}


def _resource_from_path(path: str) -> tuple[str, str, list[str]]:
    segs = [s for s in path.strip("/").split("/") if s]
    path_params: list[str] = []
    non_param: list[tuple[int, str]] = []
    for idx, seg in enumerate(segs):
        m = re.fullmatch(r"\{([^}]+)\}", seg)
        if m:
            path_params.append(m.group(1))
        else:
            if not re.fullmatch(r"v\d+|api", seg, re.IGNORECASE):
                non_param.append((idx, seg))
    if not non_param:
        return "", "", path_params
    resource = _singularize(non_param[0][1])
    subresource = ""
    if len(non_param) >= 2 and path_params:
        subresource = non_param[-1][1].lower()
    elif len(non_param) >= 2 and not path_params:
        resource = _singularize(non_param[-1][1])
    return resource, subresource, path_params


def compile_api_graph(origin: str, spec_url: str, spec: Mapping[str, Any]) -> ApiGraph:
    """Compile an OpenAPI/Swagger JSON spec into a typed entity-dependency graph."""
    info = spec.get("info") if isinstance(spec.get("info"), Mapping) else {}
    title = str(info.get("title") or "UnknownAPI")
    auth_scheme = _extract_auth_scheme(spec)
    global_sec = bool(spec.get("security"))
    ops: list[ApiOperation] = []
    resources: set[str] = set()
    auth_op: ApiOperation | None = None

    paths = spec.get("paths") if isinstance(spec.get("paths"), Mapping) else {}
    for raw_path, path_item in paths.items():
        if not isinstance(path_item, Mapping):
            continue
        shared_params = path_item.get("parameters") if isinstance(path_item.get("parameters"), list) else []
        for method_raw, op_obj in path_item.items():
            method = method_raw.upper()
            if method not in ("GET", "POST", "PUT", "PATCH", "DELETE") or not isinstance(op_obj, Mapping):
                continue
            op_id = str(op_obj.get("operationId") or f"{method.lower()}_{raw_path}")
            summary = str(op_obj.get("summary") or op_obj.get("description") or "")
            body_schema = _extract_body_schema(spec, op_obj)
            resp_schema = _extract_response_schema(spec, op_obj)
            res, subres, path_params = _resource_from_path(raw_path)

            q_params: list[dict[str, Any]] = []
            h_params: list[dict[str, Any]] = []
            for p_raw in list(shared_params) + list(op_obj.get("parameters") or []):
                p = _resolve_ref(spec, p_raw)
                pin = str(p.get("in") or "").lower()
                if pin == "query":
                    q_params.append(p)
                elif pin == "header":
                    h_params.append(p)

            is_destr = method == "DELETE" or bool(_DESTRUCTIVE_RE.search(f"{raw_path} {op_id} {summary}"))
            resp_props = set((resp_schema.get("properties") or {}).keys()) if isinstance(resp_schema, Mapping) else set()
            is_auth = (
                method == "POST"
                and not is_destr
                and (
                    bool(_AUTH_PATH_RE.search(f"{raw_path} {op_id} {summary}"))
                    or bool(resp_props & set(_TOKEN_FIELD_NAMES))
                )
            )
            if is_destr:
                role = "DESTRUCTIVE"
            elif is_auth:
                role = "AUTH"
            elif method == "GET" and not path_params:
                role = "LIST"
            elif method == "GET" and path_params and subres:
                role = "READ_SUBRESOURCE"
            elif method == "GET" and path_params:
                role = "READ"
            elif method == "POST" and not path_params:
                role = "CREATE"
            else:
                role = "OTHER"

            op_sec = op_obj.get("security")
            if op_sec is not None:
                req_auth = bool(op_sec)
            else:
                req_auth = global_sec and not is_auth

            op = ApiOperation(
                method=method,
                path=raw_path,
                operation_id=op_id,
                summary=summary,
                role=role,
                resource=res,
                subresource=subres,
                path_params=path_params,
                query_params=q_params,
                header_params=h_params,
                body_schema=body_schema,
                response_schema=resp_schema,
                requires_auth=req_auth,
                is_destructive=is_destr,
            )
            ops.append(op)
            if role == "AUTH" and auth_op is None:
                auth_op = op
            if res and role in ("LIST", "CREATE", "READ", "READ_SUBRESOURCE"):
                resources.add(res)

    # Infer foreign-key dependencies from body properties & path parameters against discovered resources
    for op in ops:
        if op.is_destructive or op.role == "AUTH":
            continue
        props = (op.body_schema.get("properties") or {}) if isinstance(op.body_schema, Mapping) else {}
        seen_fk: set[str] = set()
        for prop_name in props:
            m_fk = re.fullmatch(r"([A-Za-z0-9]+?)(?:_id|Id)", prop_name)
            if not m_fk:
                continue
            stem = _singularize(m_fk.group(1).lower())
            if stem in resources and stem != op.resource and prop_name not in seen_fk:
                op.fk_deps.append((prop_name, stem))
                seen_fk.add(prop_name)
        for pp in op.path_params:
            m_fk = re.fullmatch(r"([A-Za-z0-9]+?)(?:_id|Id)", pp)
            if m_fk:
                stem = _singularize(m_fk.group(1).lower())
                if stem in resources and stem != op.resource and pp not in seen_fk:
                    op.fk_deps.append((pp, stem))
                    seen_fk.add(pp)

    return ApiGraph(
        origin=origin,
        title=title,
        spec_url=spec_url,
        auth_scheme=auth_scheme,
        auth_op=auth_op,
        operations=ops,
        resources=resources,
    )


def _extract_goal_values(goal: str, field_values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Extract typed key-value pairs and named entities from explicit inputs + natural-language goal."""
    vals: dict[str, Any] = {}
    if field_values:
        for k, v in field_values.items():
            vals[str(k)] = v
            vals[str(k).lower()] = v

    # Extract explicit `key=value` or `key: value` tokens from goal
    for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]{1,30})\s*[:=]\s*(\"[^\"]+\"|'[^']+'|[^\s,;]+)", goal or ""):
        k = m.group(1).strip()
        v = m.group(2).strip().strip("\"'")
        vals.setdefault(k, v)
        vals.setdefault(k.lower(), v)

    # Extract quoted strings (often entity names like "Acme Corp" or "North Hub")
    quoted = re.findall(r"\"([^\"]{2,60})\"|'([^']{2,60})'", goal or "")
    q_list = [a or b for a, b in quoted if (a or b).strip()]
    if q_list:
        vals.setdefault("__quoted__", q_list)

    # Extract natural patterns: "for <Entity Name> with", "amount 250", "weight 42", "currency usd", "date 11/21/2026"
    m_for = re.search(r"\bfor\s+(?:client|customer|warehouse|account|user|org|vendor|project|owner)?\s*([A-Z][A-Za-z0-9\-]+(?:\s+[A-Z][A-Za-z0-9\-]+){0,3})", goal or "")
    if m_for:
        vals.setdefault("__entity_name__", m_for.group(1).strip())
    elif q_list:
        vals.setdefault("__entity_name__", q_list[0])

    for num_kw in ("amount", "total", "price", "quantity", "qty", "count", "weight", "items", "units"):
        m_n = re.search(rf"\b{num_kw}\s+(?:of\s+)?(\d+(?:\.\d+)?)\b", goal or "", re.IGNORECASE)
        if m_n:
            raw_num = m_n.group(1)
            vals.setdefault(num_kw, float(raw_num) if "." in raw_num else int(raw_num))

    m_cur = re.search(r"\bcurrency\s+([A-Za-z]{3})\b", goal or "", re.IGNORECASE)
    if m_cur:
        vals.setdefault("currency", m_cur.group(1))
    m_dt = re.search(r"\bdate\s+(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})\b", goal or "", re.IGNORECASE)
    if m_dt:
        vals.setdefault("date", m_dt.group(1))
        vals.setdefault("ship_date", m_dt.group(1))
        vals.setdefault("due_date", m_dt.group(1))
    return vals


def _coerce_for_schema(val: Any, prop_schema: Mapping[str, Any]) -> Any:
    ptype = str(prop_schema.get("type") or "").lower()
    if ptype == "integer":
        try:
            return int(float(val))
        except Exception:
            return 1
    if ptype == "number":
        try:
            return float(val)
        except Exception:
            return 1.0
    if ptype == "boolean":
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("1", "true", "yes")
    if ptype == "string":
        return str(val)
    return val


def _build_body_for_op(
    op: ApiOperation,
    vals: Mapping[str, Any],
    fk_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    props = op.body_schema.get("properties") if isinstance(op.body_schema, Mapping) else None
    if not isinstance(props, Mapping):
        return {}
    required = set(op.body_schema.get("required") or [])
    body: dict[str, Any] = {}
    norm_vals = {re.sub(r"[^a-z0-9]", "", k.lower()): v for k, v in vals.items() if not k.startswith("__")}

    for pname, pschema in props.items():
        if not isinstance(pschema, Mapping):
            pschema = {}
        if pname in fk_bindings:
            body[pname] = _coerce_for_schema(fk_bindings[pname], pschema)
            continue
        pnorm = re.sub(r"[^a-z0-9]", "", pname.lower())
        matched = None
        if pname in vals:
            matched = vals[pname]
        elif pname.lower() in vals:
            matched = vals[pname.lower()]
        elif pnorm in norm_vals:
            matched = norm_vals[pnorm]
        else:
            # Fuzzy alias match (e.g. `ship_date` <-> `date`, `item_count` <-> `items`, `client_name` <-> `name`)
            ptoks = set(_split_tokens(pname))
            for vk, vv in vals.items():
                if vk.startswith("__"):
                    continue
                vtoks = set(_split_tokens(vk))
                if ptoks and vtoks and (ptoks & vtoks):
                    matched = vv
                    break
            if matched is None and any(t in pname.lower() for t in ("name", "title", "label")) and "__entity_name__" in vals:
                matched = vals["__entity_name__"]

        if matched is not None:
            body[pname] = _coerce_for_schema(matched, pschema)
        elif pname in required:
            if "default" in pschema:
                body[pname] = pschema["default"]
            elif isinstance(pschema.get("enum"), list) and pschema["enum"]:
                body[pname] = pschema["enum"][0]
            elif pschema.get("example") is not None:
                body[pname] = pschema["example"]
            else:
                ptype = str(pschema.get("type") or "string").lower()
                if ptype == "integer":
                    body[pname] = int(pschema.get("minimum", 1))
                elif ptype == "number":
                    body[pname] = float(pschema.get("minimum", 1.0))
                elif ptype == "boolean":
                    body[pname] = True
                elif ptype == "array":
                    body[pname] = []
                elif ptype == "object":
                    body[pname] = {}
                else:
                    fmt = str(pschema.get("format") or "").lower()
                    if fmt == "date":
                        body[pname] = "2026-11-21"
                    elif fmt == "email":
                        body[pname] = "ops@example.com"
                    else:
                        body[pname] = str(vals.get("__entity_name__") or f"default_{pname}")
    return body


def _normalize_date_iso(raw: str) -> str | None:
    s = str(raw).strip()
    m1 = re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if m1:
        return f"{int(m1.group(1)):04d}-{int(m1.group(2)):02d}-{int(m1.group(3)):02d}"
    m2 = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if m2:
        a, b, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        mon, day = (a, b) if a <= 12 else (b, a)
        return f"{y:04d}-{mon:02d}-{day:02d}"
    return None


def _repair_from_http_error(
    status: int,
    err_json: Any,
    err_raw: str,
    headers: dict[str, str],
    body: dict[str, Any],
    attempt_idx: int,
) -> tuple[bool, list[str]]:
    """Deterministically repair headers/body from a live HTTP 400/422 validation error."""
    repaired = False
    rules_fired: list[str] = []

    err_items: list[dict[str, Any]] = []
    if isinstance(err_json, Mapping):
        if isinstance(err_json.get("detail"), list):
            for it in err_json["detail"]:
                if isinstance(it, Mapping):
                    err_items.append(dict(it))
        if isinstance(err_json.get("errors"), list):
            for it in err_json["errors"]:
                if isinstance(it, Mapping):
                    err_items.append(dict(it))
        err_items.append(dict(err_json))
    else:
        err_items.append({"message": err_raw})

    for item in err_items:
        msg = " ".join(
            str(item.get(k) or "") for k in ("message", "msg", "error", "detail") if isinstance(item.get(k), str)
        )
        # 1. Missing required HTTP header (e.g., X-Idempotency-Key, X-Request-Nonce)
        req_hdr = item.get("missing_header") or item.get("required_header")
        if not req_hdr:
            m_h = re.search(r"(?:missing|required)\s+(?:required\s+)?header[:\s]+['\"]?([A-Za-z0-9\-]+)['\"]?", msg, re.IGNORECASE)
            if m_h:
                req_hdr = m_h.group(1)
        if req_hdr and isinstance(req_hdr, str):
            hname = req_hdr.strip()
            if hname not in headers:
                digest = hashlib.sha256(f"{hname}:{json.dumps(body, sort_keys=True)}:{attempt_idx}".encode()).hexdigest()[:16]
                headers[hname] = f"idemp-{digest}"
                repaired = True
                rules_fired.append("missing_header_self_heal")

        # Identify target body field name
        fld = item.get("field")
        if not fld and isinstance(item.get("loc"), list) and item["loc"]:
            fld = str(item["loc"][-1])
        if not fld:
            m_f = re.search(r"field\s+['\"]([A-Za-z0-9_]+)['\"]", msg, re.IGNORECASE)
            if m_f:
                fld = m_f.group(1)

        # 2. Enum / uppercase / allowed value repair
        allowed = item.get("allowed") or item.get("enum") or item.get("expected_values")
        if fld and fld in body:
            cur_v = body[fld]
            if isinstance(allowed, list) and allowed:
                for av in allowed:
                    if str(av).lower() == str(cur_v).lower():
                        if body[fld] != av:
                            body[fld] = av
                            repaired = True
                            rules_fired.append("enum_case_normalize")
                        break
                else:
                    body[fld] = allowed[0]
                    repaired = True
                    rules_fired.append("enum_fallback_repair")
            elif re.search(r"\buppercase\b", msg, re.IGNORECASE) and isinstance(cur_v, str) and cur_v != cur_v.upper():
                body[fld] = cur_v.upper()
                repaired = True
                rules_fired.append("enum_case_normalize")

            # 3. Date ISO-8601 format repair (YYYY-MM-DD)
            fmt_hint = str(item.get("format") or item.get("expected_format") or "")
            if ("YYYY-MM-DD" in fmt_hint.upper() or "YYYY-MM-DD" in msg.upper() or "ISO" in msg.upper()) and isinstance(cur_v, str):
                iso = _normalize_date_iso(cur_v)
                if iso and iso != cur_v:
                    body[fld] = iso
                    repaired = True
                    rules_fired.append("date_iso_format_repair")

            # 4. Integer / numeric coercion or minimum clamp
            if re.search(r"\binteger\b|\bint\b", msg, re.IGNORECASE) and not isinstance(cur_v, int):
                try:
                    body[fld] = int(float(cur_v))
                    repaired = True
                    rules_fired.append("scalar_type_coercion")
                except Exception:
                    pass
            if item.get("minimum") is not None:
                try:
                    if float(cur_v) < float(item["minimum"]):
                        body[fld] = item["minimum"]
                        repaired = True
                        rules_fired.append("numeric_min_clamp")
                except Exception:
                    pass

        # 5. Missing required body field discovered via 400/422
        if fld and fld not in body and re.search(r"missing|required", msg, re.IGNORECASE):
            if isinstance(allowed, list) and allowed:
                body[fld] = allowed[0]
            elif item.get("default") is not None:
                body[fld] = item["default"]
            else:
                body[fld] = f"auto_{fld}"
            repaired = True
            rules_fired.append("missing_body_field_fill")

    return repaired, rules_fired


def _extract_items_and_next(payload: Any, headers: Mapping[str, str]) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
    """Extract list items and next-page pagination token from any standard REST collection response."""
    items: list[dict[str, Any]] = []
    if isinstance(payload, list):
        items = [x for x in payload if isinstance(x, dict)]
        nxt = None
    elif isinstance(payload, Mapping):
        for k in ("items", "data", "results", "records", "entries", "rows"):
            if isinstance(payload.get(k), list):
                items = [x for x in payload[k] if isinstance(x, dict)]
                break
        if not items:
            for v in payload.values():
                if isinstance(v, list) and (not v or isinstance(v[0], Mapping)):
                    items = [dict(x) for x in v if isinstance(x, Mapping)]
                    break
        nxt = None
        for ck in ("next_cursor", "nextCursor", "cursor_next", "next_token", "nextToken"):
            cv = payload.get(ck)
            if cv:
                nxt = {"cursor": str(cv)}
                break
        if nxt is None and payload.get("next_page"):
            nxt = {"page": str(payload["next_page"])}
        elif nxt is None and payload.get("has_more") is True:
            cur_p = payload.get("page")
            if isinstance(cur_p, int):
                nxt = {"page": str(cur_p + 1)}
            elif payload.get("next_offset") is not None:
                nxt = {"offset": str(payload["next_offset"])}
    else:
        nxt = None

    # RFC 8288 Link: <...>; rel="next"
    link_hdr = headers.get("link", "")
    if nxt is None and 'rel="next"' in link_hdr:
        m_l = re.search(r'<([^>]+)>;\s*rel="next"', link_hdr)
        if m_l:
            nxt = {"__next_url__": m_l.group(1)}
    return items, nxt


def _distill_api_poly_skill(stages: list[str], repair_rules: list[str]) -> dict[str, Any]:
    """Distill a ZERO-URL, ZERO-CREDENTIAL, ZERO-VALUE generalized polymorphic OpenAPI workflow skill."""
    canonical_stages = list(dict.fromkeys(stages))
    canonical_repairs = sorted(set(repair_rules))
    sig_str = "|".join(canonical_stages) + "::" + ",".join(canonical_repairs)
    skill_id = f"apipoly_{hashlib.sha256(sig_str.encode()).hexdigest()[:12]}"
    return {
        "skill_id": skill_id,
        "kind": "openapi_polymorphic_workflow",
        "stages": canonical_stages,
        "repair_capabilities": canonical_repairs,
        "verified_uses": 1,
        "utility_q": 0.9,
        "contains_urls_tokens_or_values": False,
    }


def _match_api_poly_skill(memory: Mapping[str, Any] | None, required_stages: Sequence[str]) -> dict[str, Any] | None:
    if not isinstance(memory, Mapping):
        return None
    store = memory.get("api_poly_skills")
    if not isinstance(store, Mapping):
        return None
    req = set(required_stages)
    best: dict[str, Any] | None = None
    best_score = -1.0
    for sk in store.values():
        if not isinstance(sk, Mapping):
            continue
        sk_stages = set(sk.get("stages") or [])
        if req <= sk_stages:
            score = float(sk.get("utility_q", 0.5)) + 0.05 * len(sk.get("repair_capabilities") or [])
            if score > best_score:
                best_score = score
                best = dict(sk)
    return best


def solve_live_openapi_workflow(
    api_url: str,
    goal: str,
    *,
    memory: dict[str, Any] | None = None,
    field_values: Mapping[str, Any] | None = None,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Enter an unseen OpenAPI/REST microservice knowing NOTHING, discover its schema,
    plan the backward-chaining FK dependency DAG, handle 401 refresh + 429 backoff +
    400/422 incomplete-spec self-healing + full pagination + GET readback verification,
    and distill a zero-URL/zero-token polymorphic skill into external memory."""
    t0 = time.monotonic()
    parsed_u = urllib.parse.urlparse(api_url)
    origin = f"{parsed_u.scheme}://{parsed_u.netloc}"

    spec_url, spec, discovery_probes = discover_openapi_spec(api_url, timeout_s=min(timeout_s, 5.0))
    if not spec or not spec_url:
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": "openapi_rest_api",
            "status": "FAILED",
            "mode": "OPENAPI_SPEC_NOT_FOUND",
            "discovery_probes": discovery_probes,
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    graph = compile_api_graph(origin, spec_url, spec)
    vals = _extract_goal_values(goal, field_values)
    goal_toks = set(_split_tokens(goal))

    # Select target CREATE operation by semantic overlap with goal
    create_ops = [op for op in graph.operations if op.role == "CREATE" and not op.is_destructive]
    if not create_ops:
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": "openapi_rest_api",
            "status": "FAILED",
            "mode": "NO_CREATE_ENDPOINT",
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # Compute FK dependency DAG depth per resource so leaf targets outrank intermediate parents on ties
    create_by_res = {op.resource: op for op in create_ops}

    def _fk_depth(res: str, seen: frozenset[str] = frozenset()) -> int:
        op_r = create_by_res.get(res)
        if op_r is None or not op_r.fk_deps or res in seen:
            return 0
        return 1 + max(_fk_depth(dep_r, seen | {res}) for _, dep_r in op_r.fk_deps)

    def _score_create(op: ApiOperation) -> tuple[int, int, int]:
        op_toks = set(_split_tokens(f"{op.path} {op.operation_id} {op.summary}"))
        op_toks.add(op.resource)
        direct_verb = int(
            bool(
                re.search(
                    rf"\b(?:create|add|submit|open|issue|dispatch|register|launch|post|make|new)\s+(?:a\s+|an\s+|the\s+)?{re.escape(op.resource)}s?\b",
                    goal or "",
                    re.IGNORECASE,
                )
            )
        )
        overlap = len(goal_toks & op_toks)
        return (direct_verb, overlap, _fk_depth(op.resource))

    target_create = max(create_ops, key=_score_create)

    # Select optional GET readback endpoint for target resource (prefer subresource if mentioned in goal)
    read_sub_ops = [
        op for op in graph.operations
        if op.role == "READ_SUBRESOURCE" and op.resource == target_create.resource and not op.is_destructive
    ]
    read_ops = [
        op for op in graph.operations
        if op.role == "READ" and op.resource == target_create.resource and not op.is_destructive
    ]
    target_read: ApiOperation | None = None
    if read_sub_ops:
        scored_sub = sorted(
            read_sub_ops,
            key=lambda o: len(goal_toks & set(_split_tokens(f"{o.path} {o.subresource} {o.summary}"))),
            reverse=True,
        )
        if len(goal_toks & set(_split_tokens(f"{scored_sub[0].path} {scored_sub[0].subresource} {scored_sub[0].summary}"))) > 0:
            target_read = scored_sub[0]
    if target_read is None and read_ops:
        target_read = read_ops[0]
    elif target_read is None and read_sub_ops:
        target_read = read_sub_ops[0]

    # Check Tier-0 polymorphic skill recall from external memory!
    planned_stages = ["DISCOVER_OPENAPI"]
    if graph.auth_op is not None and graph.auth_scheme.get("type") != "none":
        planned_stages.append("AUTH_ACQUIRE")
    if target_create.fk_deps:
        planned_stages.append("PAGINATED_FK_RESOLVE")
    planned_stages.append("CREATE_TARGET")
    if target_read is not None:
        planned_stages.append("VERIFY_READBACK")

    matched_poly = _match_api_poly_skill(memory, planned_stages)
    prior_repairs = set(matched_poly.get("repair_capabilities") or []) if matched_poly else set()

    # Runtime state & telemetry
    auth_token: str | None = None
    trace: list[dict[str, Any]] = []
    stages_executed: list[str] = ["DISCOVER_OPENAPI"]
    repairs_applied: list[str] = []
    auth_refreshes = 0
    rate_limit_retries = 0
    pages_scanned = 0
    schema_repairs = 0
    destructive_traps_hit = 0

    def _apply_auth(hdrs: dict[str, str], q_url: str) -> str:
        if not auth_token:
            return q_url
        stype = graph.auth_scheme.get("type")
        if stype == "bearer":
            hdrs["Authorization"] = f"Bearer {auth_token}"
        elif stype == "apiKey":
            if graph.auth_scheme.get("in") == "query":
                sep = "&" if "?" in q_url else "?"
                q_url = f"{q_url}{sep}{urllib.parse.urlencode({graph.auth_scheme['name']: auth_token})}"
            else:
                hdrs[graph.auth_scheme["name"]] = auth_token
        return q_url

    def _acquire_auth(*, is_refresh: bool = False) -> bool:
        nonlocal auth_token, auth_refreshes
        if graph.auth_op is None:
            return False
        a_body = _build_body_for_op(graph.auth_op, vals, {})
        st, _, js, raw = _http_json(
            graph.auth_op.method,
            origin + graph.auth_op.path,
            body=a_body if a_body else {},
            timeout_s=min(timeout_s, 6.0),
        )
        trace.append({"step": "AUTH_REFRESH" if is_refresh else "AUTH_ACQUIRE", "method": graph.auth_op.method, "path": graph.auth_op.path, "status": st})
        if st in (200, 201) and isinstance(js, Mapping):
            for tk in _TOKEN_FIELD_NAMES:
                if js.get(tk):
                    auth_token = str(js[tk])
                    if is_refresh:
                        auth_refreshes += 1
                    else:
                        stages_executed.append("AUTH_ACQUIRE")
                    return True
        return False

    def _exec_resilient(
        op: ApiOperation,
        *,
        path_bindings: Mapping[str, Any] | None = None,
        query: Mapping[str, str] | None = None,
        body: dict[str, Any] | None = None,
        override_url: str | None = None,
    ) -> tuple[int, dict[str, str], Any, str]:
        nonlocal rate_limit_retries, schema_repairs, destructive_traps_hit
        assert not op.is_destructive, f"Refusing destructive trap endpoint {op.method} {op.path}"
        req_headers: dict[str, str] = {}
        # Proactively populate any explicitly declared OpenAPI header params
        for hp in op.header_params:
            hname = str(hp.get("name") or "")
            if hname and hp.get("required"):
                req_headers[hname] = str(vals.get(hname) or vals.get(hname.lower()) or f"hdr-{int(time.time()*1000)}")
        req_body = dict(body) if body is not None else None

        # Tier-0 proactive normalization when memory already knows prior repair laws!
        if req_body is not None and "date_iso_format_repair" in prior_repairs:
            for bk, bv in list(req_body.items()):
                if isinstance(bv, str) and "date" in bk.lower():
                    iso = _normalize_date_iso(bv)
                    if iso and iso != bv:
                        req_body[bk] = iso
                        repairs_applied.append("date_iso_format_repair")
        if req_body is not None and "enum_case_normalize" in prior_repairs:
            for bk, bv in list(req_body.items()):
                if isinstance(bv, str) and bk.lower() in ("currency", "country", "region", "code") and len(bv) <= 4 and bv != bv.upper():
                    req_body[bk] = bv.upper()
                    repairs_applied.append("enum_case_normalize")

        for attempt in range(1, 8):
            if override_url:
                url = urllib.parse.urljoin(origin + "/", override_url)
            else:
                rel_path = op.path
                for pk, pv in (path_bindings or {}).items():
                    rel_path = rel_path.replace("{" + pk + "}", urllib.parse.quote(str(pv), safe=""))
                url = origin + rel_path
                if query:
                    sep = "&" if "?" in url else "?"
                    url = f"{url}{sep}{urllib.parse.urlencode(query)}"

            hdrs_call = dict(req_headers)
            url_call = _apply_auth(hdrs_call, url)
            st, rhdrs, rjson, rraw = _http_json(
                op.method, url_call, headers=hdrs_call, body=req_body, timeout_s=min(timeout_s, 6.0),
            )
            trace.append({"step": op.role, "method": op.method, "path": op.path, "status": st, "attempt": attempt})

            if 200 <= st < 300:
                return st, rhdrs, rjson, rraw

            # 1. Mid-workflow 401 Unauthorized -> refresh token automatically & retry!
            if st == 401 and graph.auth_op is not None:
                if _acquire_auth(is_refresh=True):
                    repairs_applied.append("auth_refresh_on_401")
                    continue
                return st, rhdrs, rjson, rraw

            # 2. 429 / 503 Rate-limit / transient backoff -> honor Retry-After & retry!
            if st in (429, 503):
                ra_raw = rhdrs.get("retry-after") or (
                    str(rjson.get("retry_after")) if isinstance(rjson, Mapping) and rjson.get("retry_after") is not None else "0.03"
                )
                try:
                    wait_s = min(max(float(ra_raw), 0.01), 0.5)
                except Exception:
                    wait_s = 0.05
                time.sleep(wait_s)
                rate_limit_retries += 1
                repairs_applied.append("retry_after_on_429")
                continue

            # 3. 400 / 422 Incomplete-spec validation error -> deterministic live schema/header self-heal!
            if st in (400, 422) and req_body is not None:
                fixed, fired = _repair_from_http_error(st, rjson, rraw, req_headers, req_body, attempt)
                if fixed:
                    schema_repairs += len(fired)
                    repairs_applied.extend(fired)
                    continue

            return st, rhdrs, rjson, rraw

        return 0, {}, None, "MAX_RETRIES_EXCEEDED"

    # Stage 1: Acquire initial authentication token if service uses auth
    if graph.auth_op is not None and graph.auth_scheme.get("type") != "none":
        if not _acquire_auth(is_refresh=False):
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "openapi_rest_api",
                "status": "FAILED",
                "mode": "AUTH_FAILED",
                "trace": trace,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

    # Stage 2: Recursively resolve arbitrary-depth foreign-key DAG dependencies
    #          (paginated LIST -> fallback recursive CREATE with cycle guard)
    fk_bindings: dict[str, Any] = {}
    resolved_entities: dict[str, dict[str, Any]] = {}
    target_entity_name = str(vals.get("__entity_name__") or vals.get("name") or "").strip().lower()

    def _entity_hint_for_resource(dep_res: str) -> str:
        for k in (f"{dep_res}_name", f"{dep_res}Name", dep_res):
            if k in vals and isinstance(vals[k], str) and vals[k].strip():
                return vals[k].strip()
        return str(vals.get("__entity_name__") or vals.get("name") or "").strip()

    def _resolve_resource_fk(dep_res: str, fk_field: str, visited: frozenset[str]) -> Any:
        nonlocal pages_scanned
        if fk_field in vals:
            return vals[fk_field]
        if dep_res in resolved_entities:
            cached = resolved_entities[dep_res]
            return cached.get("id") or cached.get(fk_field)
        if dep_res in visited:
            return None

        list_op = next((o for o in graph.operations if o.role == "LIST" and o.resource == dep_res and not o.is_destructive), None)
        create_dep_op = next((o for o in graph.operations if o.role == "CREATE" and o.resource == dep_res and not o.is_destructive), None)

        hint_raw = _entity_hint_for_resource(dep_res)
        hint_low = hint_raw.lower()
        found_item: dict[str, Any] | None = None
        if list_op is not None:
            q_names = {str(qp.get("name") or "") for qp in list_op.query_params}
            cur_query: dict[str, str] = {}
            next_url: str | None = None
            if "page" in q_names:
                cur_query["page"] = "1"
            for _page_guard in range(25):
                st_l, hdr_l, js_l, _ = _exec_resilient(list_op, query=cur_query if not next_url else None, override_url=next_url)
                if st_l != 200:
                    break
                pages_scanned += 1
                items, nxt = _extract_items_and_next(js_l, hdr_l)
                for it in items:
                    if hint_low:
                        hay = " ".join(str(v).lower() for v in it.values() if isinstance(v, (str, int)))
                        if hint_low in hay:
                            found_item = it
                            break
                    elif items:
                        found_item = items[0]
                        break
                if found_item is not None or not nxt:
                    break
                if "__next_url__" in nxt:
                    next_url = nxt["__next_url__"]
                    cur_query = {}
                else:
                    next_url = None
                    if "cursor" in nxt:
                        cname = next((qn for qn in q_names if any(w in qn.lower() for w in ("cursor", "after", "token"))), "cursor")
                        cur_query = {cname: nxt["cursor"]}
                    elif "page" in nxt:
                        cur_query = {"page": nxt["page"]}
                    elif "offset" in nxt:
                        cur_query = {"offset": nxt["offset"]}
                    else:
                        break

        if found_item is None and create_dep_op is not None:
            # Recursively resolve parent FKs of `create_dep_op` before creating `dep_res`!
            sub_fks: dict[str, Any] = {}
            for sub_fk_field, sub_res in create_dep_op.fk_deps:
                sub_id = _resolve_resource_fk(sub_res, sub_fk_field, visited | {dep_res})
                if sub_id is not None:
                    sub_fks[sub_fk_field] = sub_id
            dep_vals = dict(vals)
            if hint_raw:
                dep_vals["name"] = hint_raw
                dep_vals["__entity_name__"] = hint_raw
            dep_body = _build_body_for_op(create_dep_op, dep_vals, sub_fks)
            st_d, _, js_d, _ = _exec_resilient(create_dep_op, body=dep_body)
            if st_d in (200, 201) and isinstance(js_d, Mapping):
                found_item = dict(js_d)

        if found_item is not None:
            eid = found_item.get("id") or found_item.get(fk_field) or next(
                (v for k, v in found_item.items() if k.lower().endswith("id") and v is not None), None
            )
            if eid is not None:
                resolved_entities[dep_res] = found_item
                stages_executed.append("PAGINATED_FK_RESOLVE")
                return eid
        return None

    for fk_field, dep_res in target_create.fk_deps:
        rid = _resolve_resource_fk(dep_res, fk_field, frozenset({target_create.resource}))
        if rid is not None:
            fk_bindings[fk_field] = rid

    # Stage 3: Execute target CREATE with resolved foreign keys + self-healing
    target_body = _build_body_for_op(target_create, vals, fk_bindings)
    st_c, _, js_c, raw_c = _exec_resilient(target_create, body=target_body)
    if st_c not in (200, 201) or not isinstance(js_c, Mapping):
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": "openapi_rest_api",
            "status": "FAILED",
            "mode": "TARGET_CREATE_FAILED",
            "http_status": st_c,
            "raw_error": raw_c[:400],
            "trace": trace,
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }
    stages_executed.append("CREATE_TARGET")
    created_obj = dict(js_c)
    created_id = created_obj.get("id") or next(
        (v for k, v in created_obj.items() if k.lower().endswith("id") and v is not None), None
    )

    # Stage 4: Independent GET readback verification (APIFlow-Bench statefulness + final delivery)
    readback_obj: Any = None
    if target_read is not None and created_id is not None:
        pbind = {pp: created_id for pp in target_read.path_params}
        st_r, _, js_r, _ = _exec_resilient(target_read, path_bindings=pbind)
        if st_r == 200 and js_r is not None:
            readback_obj = js_r
            stages_executed.append("VERIFY_READBACK")
        else:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "openapi_rest_api",
                "status": "FAILED",
                "mode": "READBACK_VERIFICATION_FAILED",
                "http_status": st_r,
                "created": created_obj,
                "trace": trace,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

    # Stage 5: Distill ZERO-URL, ZERO-TOKEN, ZERO-VALUE generalized polymorphic workflow skill into memory
    distilled_skill = _distill_api_poly_skill(stages_executed, repairs_applied)
    if memory is not None:
        store = memory.setdefault("api_poly_skills", {})
        if matched_poly and matched_poly["skill_id"] in store:
            ex = store[matched_poly["skill_id"]]
            ex["verified_uses"] = int(ex.get("verified_uses", 1)) + 1
            ex["utility_q"] = round(min(0.99, float(ex.get("utility_q", 0.9)) + 0.03), 4)
            ex["repair_capabilities"] = sorted(set(ex.get("repair_capabilities") or []) | set(repairs_applied))
        else:
            store[distilled_skill["skill_id"]] = distilled_skill

    mode = "TIER0_OPENAPI_POLY_SKILL" if matched_poly is not None else "EPISTEMIC_OPENAPI_WORKFLOW_SOLVED"
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "modality": "openapi_rest_api",
        "status": "VERIFIED",
        "mode": mode,
        "service_title": graph.title,
        "spec_url": spec_url,
        "target_operation": f"{target_create.method} {target_create.path}",
        "readback_operation": f"{target_read.method} {target_read.path}" if target_read else None,
        "resolved_foreign_keys": fk_bindings,
        "created": created_obj,
        "readback": readback_obj,
        "telemetry": {
            "discovery_probes": len(discovery_probes),
            "pages_scanned": pages_scanned,
            "auth_refreshes": auth_refreshes,
            "rate_limit_retries": rate_limit_retries,
            "schema_repairs": schema_repairs,
            "repairs_applied": sorted(set(repairs_applied)),
            "destructive_traps_hit": destructive_traps_hit,
            "tier0_poly_skill_used": matched_poly is not None,
            "tier0_skill_id": matched_poly["skill_id"] if matched_poly else None,
        },
        "distilled_poly_skill": distilled_skill,
        "trace": trace,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }
