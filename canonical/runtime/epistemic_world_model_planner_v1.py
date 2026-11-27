"""Epistemic Causal World-Model & Belief-State Planner v1 (Arbitrary Computer Use).

Zero-LLM (`model_calls=0`), zero-weight (`parameters_stored=0`), environment-agnostic
belief-state planner that replaces rigid fixed-stage pipelines with:
  1. Online Symbolic Transition World Model `G = (V, E)` recording `(s, a) -> (s', delta)`
     for cycle prevention, stagnation detection, and exact BFS shortest-path backtracking
     out of dead-end screens/branches.
  2. Dynamic Causal Precondition Discovery & Goal-Stack Decomposition: detects disabled
     target actions or live precondition rejection errors (`400`/`403`/`409` or A11y alert),
     extracts missing prerequisite concepts/artifacts, pushes a dynamic subgoal, explores
     safe unvisited branches by (Subgoal Alignment + Epistemic Information Gain), harvests
     runtime-generated tokens/codes/unlocked states, routes back along `G`, and completes
     the previously blocked target action (including 2-step confirmation modals).
  3. Pre-Execution Safety Simulation (CUWM / WebDreamer zero-LLM principle): predicts and
     blocks destructive/irreversible traps before execution (`traps_hit == 0`).
  4. Unified Environment Adapters:
       - `InteractiveA11yWorldAdapter` (arbitrary multi-screen interactive GUI A11y trees)
       - `LiveHTTPWorldAdapter` (arbitrary stateful multi-page HTTP/HTML apps with cookies,
         CSRF tokens, error banners, multi-hop prerequisites, dead-ends, and modals)
  5. Single-Experience Compositional Transfer (`memory["world_model_plans"]`) with zero
     URLs / screen IDs / widget IDs / weights and instant unlearning (`delete_memory_entry`).
"""
from __future__ import annotations

import hashlib
import html as html_lib
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Mapping, Sequence

from canonical.runtime import compose_v1 as COMPOSE_ERR
from canonical.runtime import htmlform_read_v1 as HTMLFORM

SCHEMA = "brain.epistemic_world_model_planner.v1"
AUTHORITY = "NONE"

_DESTRUCTIVE_RE = re.compile(
    r"\b(?:delete|destroy|purge|wipe|revoke|drop|terminate|erase|nuke|reset[-_\s]?all|remove[-_\s]?all|deactivate|factory[-_\s]?reset|format[-_\s]?disk)\b",
    flags=re.IGNORECASE,
)

_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "at", "for", "from", "with",
    "by", "is", "are", "be", "was", "were", "it", "this", "that", "as", "into", "before",
    "after", "must", "need", "needs", "required", "require", "requires", "first", "please",
    "cannot", "cant", "blocked", "missing", "error", "failed", "http", "https", "page",
    "screen", "button", "click", "open", "go", "navigate", "then", "now", "your", "app",
})

_ARTIFACT_PATTERNS = (
    # Key: VALUE or Key = VALUE (e.g. "Approval Code: APR-9042", "Signing Token = TOK_8812")
    re.compile(
        r"\b([A-Za-z][A-Za-z0-9_ \-]{1,28}?(?:code|token|key|secret|pin|otp|id|ticket|nonce|hash|signature|voucher|badge))\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{4,48})['\"]?",
        flags=re.IGNORECASE,
    ),
    # Standalone uppercase prefixed runtime artifact like APR-9042, TOK-771A, KEY-4421, OTP-8831
    re.compile(r"\b((?:APR|TOK|KEY|OTP|SIG|AUTH|VCH|PIN|SEC|REL|CHG)[-_][A-Z0-9]{3,16})\b"),
)

_ROLE_CANON: dict[str, tuple[str, ...]] = {
    "security": ("security", "auth", "keys", "key", "token", "signing", "certificate", "cert", "credentials", "vault", "2fa", "mfa", "permissions", "access"),
    "compliance": ("compliance", "approval", "approve", "audit", "review", "policy", "governance", "verify", "verification", "attest", "signoff"),
    "settings": ("settings", "config", "configuration", "preferences", "options", "admin", "flags", "features", "toggle", "enable", "activate"),
    "deploy": ("deploy", "release", "publish", "ship", "launch", "promote", "rollout", "activate", "execute", "run", "dispatch", "transfer", "submit", "confirm", "finalize", "complete"),
    "back": ("back", "home", "dashboard", "main", "overview", "return", "cancel", "close", "menu", "hub"),
}


def _toks(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9]+", str(text or "").lower())
    return {t for t in raw if len(t) >= 2 and t not in _STOP_WORDS}


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").strip().lower()).strip("_")


def _abstract_role(text: str) -> str:
    ts = _toks(text)
    for role, kws in _ROLE_CANON.items():
        if ts & set(kws):
            return role
    if ts:
        return sorted(ts)[0]
    return "generic"


def _is_destructive(text: str) -> bool:
    return bool(_DESTRUCTIVE_RE.search(str(text or "")))


def _extract_artifacts(text: str) -> dict[str, str]:
    """Harvest runtime-generated tokens/codes/keys from visible UI text or banners."""
    found: dict[str, str] = {}
    s = str(text or "")
    for pat in _ARTIFACT_PATTERNS:
        for m in pat.finditer(s):
            if m.lastindex and m.lastindex >= 2:
                k = _norm_key(m.group(1))
                v = m.group(2).strip()
                if k and v and v.lower() not in ("required", "missing", "invalid", "none", "null", "false", "true"):
                    found[k] = v
                    # Also bind generic tail word (e.g. "token", "code", "key")
                    tail = k.split("_")[-1]
                    if tail in ("code", "token", "key", "pin", "otp", "secret", "voucher", "signature"):
                        found.setdefault(tail, v)
            else:
                v = m.group(1).strip()
                if v:
                    found.setdefault("artifact_token", v)
                    found.setdefault("token", v)
                    found.setdefault("code", v)
    return found


def _extract_precondition_signal(errors: Sequence[str], disabled_labels: Sequence[str]) -> dict[str, Any]:
    """Extract missing prerequisite terms and artifact field hints from live errors or disabled buttons."""
    terms: set[str] = set()
    artifact_keys: list[str] = []
    raw_msgs = [
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(e))).strip()
        for e in errors
        if str(e).strip()
    ] + [str(d).strip() for d in disabled_labels if str(d).strip()]
    for msg in raw_msgs:
        for mk in COMPOSE_ERR.missing_from_error(msg):
            nmk = _norm_key(mk)
            if nmk and nmk not in artifact_keys:
                artifact_keys.append(nmk)
                terms |= _toks(nmk.replace("_", " "))
        for m in re.finditer(
            r"(?:missing|required|requires|need|needs|prerequisite|must\s+(?:first\s+)?(?:enable|generate|request|obtain|verify|approve|activate|unlock))\s*[:\-]?\s*([^.;!\n]{3,80})",
            msg,
            flags=re.IGNORECASE,
        ):
            frag = m.group(1).strip()
            terms |= _toks(frag)
            # Detect explicit field-like token `foo_bar`
            for m_f in re.finditer(r"\b([a-z][a-z0-9]*_[a-z0-9_]+)\b", frag.lower()):
                fk = m_f.group(1)
                if fk not in artifact_keys:
                    artifact_keys.append(fk)
        # Also include tokens from full error if structured pattern missed
        if not terms:
            terms |= _toks(msg)
    return {"terms": terms, "artifact_keys": artifact_keys, "messages": raw_msgs}


# ---------------------------------------------------------------------------
# 1. Unified Observable State & Affordance Representation
# ---------------------------------------------------------------------------

@dataclass
class Affordance:
    action_id: str
    kind: str  # "click" | "toggle" | "submit_form" | "nav_link" | "input"
    label: str
    enabled: bool = True
    destructive: bool = False
    is_back_nav: bool = False
    is_modal_confirm: bool = False
    value: str = ""
    checked: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateObs:
    state_id: str
    screen_name: str
    visible_text: str
    affordances: list[Affordance]
    errors: list[str]
    done: bool
    facts: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def _compute_state_hash(obs: StateObs) -> str:
    sig_parts = [
        obs.screen_name,
        "|".join(
            sorted(
                f"{a.kind}:{a.action_id}:{int(a.enabled)}:{int(a.checked)}:{a.label[:40]}"
                for a in obs.affordances
            )
        ),
        "|".join(sorted(f"{k}={v}" for k, v in obs.facts.items())),
    ]
    return hashlib.sha256("\n".join(sig_parts).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 2. Adapter 1: Interactive GUI / Accessibility-Tree Environment Adapter
# ---------------------------------------------------------------------------

class InteractiveA11yWorldAdapter:
    """Wraps any `gui_env` (`observe()` + `step(action)`) for the belief-state planner."""

    def __init__(self, gui_env: Any) -> None:
        self.gui_env = gui_env
        self._last_raw: dict[str, Any] = {}

    def _to_obs(self, raw: Mapping[str, Any]) -> StateObs:
        self._last_raw = dict(raw)
        screen = str(raw.get("screen") or "root")
        nodes = list(raw.get("nodes") or ())
        errors = [str(e) for e in (raw.get("errors") or ()) if str(e).strip()]
        text_chunks: list[str] = [screen]
        affs: list[Affordance] = []
        facts: dict[str, str] = {}

        for nd in nodes:
            role = str(nd.get("role") or "").lower()
            nid = str(nd.get("id") or nd.get("target_id") or "")
            name = str(nd.get("name") or nd.get("label") or "")
            val = str(nd.get("value") or "")
            enabled = not bool(nd.get("disabled", False))
            checked = bool(nd.get("checked", False))
            in_modal = bool(nd.get("modal", False)) or ("modal" in screen.lower()) or ("confirm" in screen.lower())

            if name:
                text_chunks.append(name)
            if val:
                text_chunks.append(val)

            if role in ("alert", "error"):
                et = (name or val).strip()
                if et and et not in errors:
                    errors.append(et)
                continue

            if role in ("status", "text", "heading", "banner", "code", "note", "badge"):
                continue

            if not nid:
                continue

            destr = _is_destructive(name + " " + nid)
            is_back = any(w in (name + " " + nid).lower() for w in ("back", "home", "dashboard", "overview", "return", "main menu", "hub"))
            if role in ("textbox", "input", "textarea", "searchbox", "combobox", "select"):
                affs.append(Affordance(
                    action_id=nid, kind="input", label=name or nid, enabled=enabled,
                    destructive=False, value=val, meta={"role": role, "required": bool(nd.get("required", False)), "options": list(nd.get("options") or ())},
                ))
            elif role in ("checkbox", "switch", "toggle"):
                affs.append(Affordance(
                    action_id=nid, kind="toggle", label=name or nid, enabled=enabled,
                    destructive=destr, checked=checked, meta={"role": role},
                ))
                if checked:
                    facts[_norm_key(name or nid)] = "enabled"
            elif role in ("button", "link", "tab", "menuitem", "option"):
                is_confirm = in_modal and any(w in name.lower() for w in ("confirm", "yes", "proceed", "ok", "approve", "accept", "continue"))
                affs.append(Affordance(
                    action_id=nid, kind="click", label=name or nid, enabled=enabled,
                    destructive=destr, is_back_nav=is_back, is_modal_confirm=is_confirm,
                    meta={"role": role},
                ))

        vis_text = "\n".join(text_chunks)
        facts.update(_extract_artifacts(vis_text))
        for k, v in (raw.get("state") or {}).items():
            if isinstance(v, (str, int, float, bool)):
                facts[f"env_{_norm_key(k)}"] = str(v)

        obs = StateObs(
            state_id="",
            screen_name=screen,
            visible_text=vis_text,
            affordances=affs,
            errors=errors,
            done=bool(raw.get("done", False)),
            facts=facts,
            raw=dict(raw),
        )
        obs.state_id = _compute_state_hash(obs)
        return obs

    def observe(self) -> StateObs:
        return self._to_obs(self.gui_env.observe())

    def execute(self, aff: Affordance, bindings: Mapping[str, str]) -> tuple[StateObs, dict[str, Any]]:
        if aff.kind == "input":
            val = bindings.get(aff.action_id) or bindings.get(_norm_key(aff.label)) or ""
            if not val:
                nk = _norm_key(aff.label)
                for tail in ("token", "code", "key", "pin", "otp", "username", "password", "email", "name"):
                    if tail in nk and tail in bindings:
                        val = bindings[tail]
                        break
            act = {"type": "type", "id": aff.action_id, "value": val}
        elif aff.kind == "toggle":
            act = {"type": "toggle", "id": aff.action_id}
        else:
            act = {"type": "click", "id": aff.action_id}
        nxt = self.gui_env.step(act)
        return self._to_obs(nxt), act

    def can_jump_url(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# 3. Adapter 2: Live Stateful Multi-Page HTTP / HTML Web World Adapter
# ---------------------------------------------------------------------------

class _HTTPPageScanner(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[dict[str, Any]] = []
        self.alerts: list[str] = []
        self.disabled_buttons: list[str] = []
        self.text_parts: list[str] = []
        self._in_a = False
        self._a_href = ""
        self._a_buf: list[str] = []
        self._in_alert = False
        self._alert_buf: list[str] = []
        self._in_btn = False
        self._btn_disabled = False
        self._btn_buf: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        if t in ("script", "style"):
            self._skip_depth += 1
            return
        if t == "a":
            self._in_a = True
            self._a_href = ad.get("href", "").strip()
            self._a_buf = []
        if ad.get("role", "").lower() in ("alert", "error") or any(c in ad.get("class", "").lower() for c in ("error", "alert", "danger")):
            self._in_alert = True
            self._alert_buf = []
        if t == "button":
            self._in_btn = True
            self._btn_disabled = "disabled" in ad
            self._btn_buf = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("script", "style"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if t == "a" and self._in_a:
            txt = re.sub(r"\s+", " ", html_lib.unescape(" ".join(self._a_buf))).strip()
            if self._a_href and not self._a_href.startswith(("#", "javascript:")):
                self.links.append({
                    "href": self._a_href,
                    "url": urllib.parse.urljoin(self.base_url, self._a_href),
                    "text": txt or self._a_href,
                })
            self._in_a = False
        if self._in_alert and t in ("div", "p", "span", "section", "aside"):
            atxt = re.sub(r"\s+", " ", html_lib.unescape(" ".join(self._alert_buf))).strip()
            if atxt:
                self.alerts.append(atxt)
            self._in_alert = False
        if t == "button" and self._in_btn:
            btxt = re.sub(r"\s+", " ", html_lib.unescape(" ".join(self._btn_buf))).strip()
            if self._btn_disabled and btxt:
                self.disabled_buttons.append(btxt)
            self._in_btn = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_a:
            self._a_buf.append(data)
        if self._in_alert:
            self._alert_buf.append(data)
        if self._in_btn:
            self._btn_buf.append(data)
        txt = data.strip()
        if txt:
            self.text_parts.append(txt)


class LiveHTTPWorldAdapter:
    """Wraps any live multi-page stateful HTTP/HTML web app with isolated cookie session."""

    def __init__(
        self,
        start_url: str,
        *,
        goal_done_markers: Sequence[str] = (),
        timeout_s: float = 10.0,
    ) -> None:
        self.start_url = start_url
        self.timeout_s = timeout_s
        self.goal_done_markers = tuple(m.lower() for m in goal_done_markers if m)
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.current_url = start_url
        self.current_html = ""
        self.last_status = 200
        self.last_headers: dict[str, str] = {}
        self.last_errors: list[str] = []
        self.done_reached = False
        self.url_by_state: dict[str, str] = {}
        # Enterprise HTTP protocol state (RFC 9110 OCC, Async 202 polling, Mid-session 401 refresh,
        # RFC 9110 429/503 Retry-After backoff, IETF Idempotency-Key transfer/drift, RFC 8288 pagination)
        self.etag_by_url: dict[str, str] = {}
        self.latest_etag: str | None = None
        self.session_headers: dict[str, str] = {}
        self.proactive_occ_header: str | None = None
        self.discovered_occ_header: str | None = None
        self.proactive_idempotency_header: str | None = None
        self.discovered_idempotency_header: str | None = None
        self.occ_recoveries: int = 0
        self.async_polls: int = 0
        self.auth_refreshes: int = 0
        self.rate_limit_retries: int = 0
        self.idempotency_recoveries: int = 0
        self.pages_traversed: int = 0
        self.policy_drift_quarantines: int = 0
        self.protocol_events: list[dict[str, Any]] = []
        self._paginated_extra_facts: dict[str, str] = {}
        self._mutation_seq: int = 0

    def _req(
        self,
        url: str,
        *,
        method: str = "GET",
        form_data: Mapping[str, str] | None = None,
        extra_headers: Mapping[str, str] | None = None,
        max_rate_retries: int = 4,
    ) -> tuple[int, str, str, dict[str, str]]:
        body = urllib.parse.urlencode(list(form_data.items())).encode("utf-8") if form_data is not None else None
        headers: dict[str, str] = dict(self.session_headers)
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if extra_headers:
            headers.update({str(k): str(v) for k, v in extra_headers.items()})

        for attempt in range(max_rate_retries + 1):
            req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
            try:
                with self.opener.open(req, timeout=self.timeout_s) as resp:
                    hdrs = {k.lower(): v for k, v in resp.headers.items()}
                    final_u = resp.geturl()
                    txt = resp.read().decode("utf-8", errors="replace")
                    if "etag" in hdrs and hdrs["etag"].strip():
                        self.etag_by_url[final_u] = hdrs["etag"].strip()
                        self.etag_by_url[url] = hdrs["etag"].strip()
                        self.latest_etag = hdrs["etag"].strip()
                    self.last_headers = hdrs
                    return int(getattr(resp, "status", 200)), final_u, txt, hdrs
            except urllib.error.HTTPError as exc:
                hdrs = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else ())}
                eb = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else str(exc)
                if "etag" in hdrs and hdrs["etag"].strip():
                    self.etag_by_url[url] = hdrs["etag"].strip()
                    self.latest_etag = hdrs["etag"].strip()
                self.last_headers = hdrs
                st_code = int(exc.code)
                # RFC 9110 `429 Too Many Requests` / transient `502`/`503`/`504` backoff honoring `Retry-After`
                if st_code in (429, 502, 503, 504) and attempt < max_rate_retries:
                    delay_s = 0.02 * (2 ** attempt)
                    if hdrs.get("retry-after"):
                        try:
                            delay_s = min(max(float(hdrs["retry-after"]), 0.005), 0.25)
                        except ValueError:
                            pass
                    time.sleep(delay_s)
                    self.rate_limit_retries += 1
                    self.protocol_events.append({
                        "event": "RATE_LIMIT_RETRY",
                        "status": st_code,
                        "url": url,
                        "method": method.upper(),
                        "retry_after_s": round(delay_s, 4),
                        "attempt": attempt + 1,
                    })
                    continue
                return st_code, url, eb, hdrs
        return 503, url, "rate limit retries exhausted", {}

    def _extract_idempotency_header_hint(self, status: int, body: str, hdrs: Mapping[str, str]) -> str | None:
        """Detect required Idempotency-Key / custom deduplication header from 400/409/422/428 rejection."""
        if status not in (400, 409, 422, 428):
            return None
        if hdrs.get("x-required-idempotency-header"):
            return hdrs["x-required-idempotency-header"].strip()
        low = body.lower()
        if not any(k in low for k in ("idempotency", "idempotent", "dedup", "duplicate-safe", "request-key")):
            return None
        m_cust = re.search(r"\b(X-[A-Za-z][A-Za-z0-9-]{2,40}|Idempotency-Key)\b", body)
        if m_cust:
            return m_cust.group(1)
        return "Idempotency-Key"

    def _extract_next_page_url(self, base_url: str, body: str, hdrs: Mapping[str, str]) -> str | None:
        """Detect RFC 8288 `Link: <url>; rel="next"`, JSON `next_url`/`next_page`, or HTML `rel="next"` / Next Page link."""
        link_hdr = hdrs.get("link") or ""
        if link_hdr:
            m_lk = re.search(r'<([^>]+)>\s*;\s*[^,]*\brel\s*=\s*"?next"?', link_hdr, re.I)
            if m_lk:
                return urllib.parse.urljoin(base_url, m_lk.group(1).strip())
        # JSON pagination fields
        if body.lstrip().startswith("{"):
            try:
                jb = json.loads(body)
                if isinstance(jb, dict):
                    for jk in ("next_url", "next_page", "next"):
                        v = jb.get(jk)
                        if isinstance(v, str) and v.strip():
                            return urllib.parse.urljoin(base_url, v.strip())
            except Exception:
                pass
        # HTML `<a rel="next" href="...">` or `<a href="..." rel="next">`
        m_a_rel = re.search(
            r"""<a\b[^>]*\brel\s*=\s*['"]next['"][^>]*\bhref\s*=\s*['"]([^'"]+)['"]|"""
            r"""<a\b[^>]*\bhref\s*=\s*['"]([^'"]+)['"][^>]*\brel\s*=\s*['"]next['"]""",
            body,
            re.I,
        )
        if m_a_rel:
            href = m_a_rel.group(1) or m_a_rel.group(2)
            if href:
                return urllib.parse.urljoin(base_url, href.strip())
        return None

    def _harvest_paginated_artifacts(
        self,
        start_url: str,
        start_body: str,
        start_hdrs: Mapping[str, str],
        *,
        bindings: Mapping[str, str] = (),
        max_pages: int = 5,
    ) -> dict[str, str]:
        """Follow bounded `rel="next"` pagination links to harvest cross-page facts/artifacts."""
        extra: dict[str, str] = {}
        visited: set[str] = {start_url}
        cur_u, cur_b, cur_h = start_url, start_body, start_hdrs
        for _ in range(max_pages):
            nxt_u = self._extract_next_page_url(cur_u, cur_b, cur_h)
            if not nxt_u or nxt_u in visited:
                break
            visited.add(nxt_u)
            st_p, ru_p, body_p, hdrs_p = self._req(nxt_u, method="GET")
            if st_p == 401 and self._try_refresh_auth(body_p, hdrs_p, bindings if isinstance(bindings, Mapping) else {}):
                st_p, ru_p, body_p, hdrs_p = self._req(nxt_u, method="GET")
            if not (200 <= st_p < 300):
                break
            self.pages_traversed += 1
            self.protocol_events.append({"event": "PAGINATION_NEXT_PAGE", "url": ru_p, "page_index": self.pages_traversed + 1})
            sc_p = _HTTPPageScanner(ru_p)
            sc_p.feed(body_p or "")
            sc_p.close()
            extra.update(_extract_artifacts("\n".join(sc_p.text_parts) + "\n" + body_p))
            cur_u, cur_b, cur_h = ru_p, body_p, hdrs_p
        return extra

    def _extract_occ_header_hint(self, status: int, body: str, hdrs: Mapping[str, str]) -> str | None:
        """Detect required Optimistic Concurrency Control header from 412/409/400 rejection."""
        if status not in (400, 409, 412):
            return None
        low = body.lower()
        # Explicit header hint from server response header (`X-Required-Header`)
        if hdrs.get("x-required-header"):
            return hdrs["x-required-header"].strip()
        # Explicit custom header mentioned in body (e.g. "Missing required header: X-Concurrency-Version")
        m_cust = re.search(r"\b(X-[A-Za-z][A-Za-z0-9-]{2,40}|If-Match)\b", body)
        if m_cust and any(k in low for k in ("header", "missing", "require", "match", "etag", "version", "lock", "stale", "conflict", "precondition")):
            return m_cust.group(1)
        if status == 412 or any(k in low for k in ("if-match", "etag", "precondition failed", "stale version", "optimistic lock", "concurrent modification")):
            return "If-Match"
        return None

    def _try_refresh_auth(self, body: str, hdrs: Mapping[str, str], bindings: Mapping[str, str]) -> bool:
        """Recover from mid-session 401 Unauthorized by refreshing token/session without losing belief state."""
        refresh_url: str | None = None
        for hk in ("x-refresh-url", "x-auth-url", "location"):
            if hdrs.get(hk):
                refresh_url = urllib.parse.urljoin(self.current_url, hdrs[hk].strip())
                break
        if not refresh_url:
            try:
                j = json.loads(body)
                if isinstance(j, dict):
                    for jk in ("refresh_url", "auth_url", "login_url", "token_url"):
                        if isinstance(j.get(jk), str) and j[jk].strip():
                            refresh_url = urllib.parse.urljoin(self.current_url, j[jk].strip())
                            break
            except Exception:
                pass
        if not refresh_url:
            m_href = re.search(r"""(?:href|action)\s*=\s*['"]([^'"]*(?:refresh|auth|login|token|session)[^'"]*)['"]""", body, re.I)
            if m_href:
                refresh_url = urllib.parse.urljoin(self.current_url, m_href.group(1))
        if not refresh_url:
            return False
        form_auth: dict[str, str] = {}
        for k in ("refresh_token", "username", "password", "api_key"):
            if k in bindings:
                form_auth[k] = str(bindings[k])
        st_r, ru_r, body_r, hdrs_r = self._req(refresh_url, method="POST", form_data=form_auth or {"refresh": "1"})
        if not (200 <= st_r < 300):
            return False
        # Extract refreshed bearer token if returned in JSON or header
        tok: str | None = hdrs_r.get("x-access-token") or hdrs_r.get("x-auth-token")
        if not tok:
            try:
                jr = json.loads(body_r)
                if isinstance(jr, dict):
                    for tk in ("access_token", "token", "bearer_token", "session_token"):
                        if isinstance(jr.get(tk), str) and jr[tk].strip():
                            tok = jr[tk].strip()
                            break
            except Exception:
                pass
        if tok:
            self.session_headers["Authorization"] = f"Bearer {tok}"
        self.auth_refreshes += 1
        self.protocol_events.append({"event": "AUTH_401_REFRESH", "refresh_url": refresh_url, "status": st_r})
        return True

    def _poll_async_job(
        self,
        init_status: int,
        init_url: str,
        init_body: str,
        init_hdrs: Mapping[str, str],
        *,
        max_polls: int = 16,
    ) -> tuple[int, str, str, dict[str, str]]:
        """Handle RFC 9110 `202 Accepted` async jobs by polling Location / status_url until terminal state."""
        poll_url: str | None = None
        if init_hdrs.get("location"):
            poll_url = urllib.parse.urljoin(init_url, init_hdrs["location"].strip())
        if not poll_url:
            try:
                j0 = json.loads(init_body)
                if isinstance(j0, dict):
                    for jk in ("status_url", "poll_url", "job_url", "href", "location"):
                        if isinstance(j0.get(jk), str) and j0[jk].strip():
                            poll_url = urllib.parse.urljoin(init_url, j0[jk].strip())
                            break
            except Exception:
                pass
        if not poll_url:
            m_lk = re.search(r"""href\s*=\s*['"]([^'"]*(?:job|status|poll|task|operation)[^'"]*)['"]""", init_body, re.I)
            if m_lk:
                poll_url = urllib.parse.urljoin(init_url, m_lk.group(1))
        if not poll_url:
            return init_status, init_url, init_body, dict(init_hdrs)

        st_p, ru_p, body_p, hdrs_p = init_status, init_url, init_body, dict(init_hdrs)
        for _ in range(max_polls):
            ra_raw = hdrs_p.get("retry-after", "")
            try:
                delay_s = min(max(float(ra_raw), 0.0), 0.15)
            except Exception:
                delay_s = 0.02
            if delay_s > 0:
                time.sleep(delay_s)
            st_p, ru_p, body_p, hdrs_p = self._req(poll_url, method="GET")
            self.async_polls += 1
            if st_p == 202:
                continue
            if st_p >= 400:
                self.protocol_events.append({"event": "ASYNC_202_FAILED", "poll_url": poll_url, "status": st_p})
                return st_p, ru_p, body_p, hdrs_p
            # Check JSON or HTML terminal status
            is_pending = False
            result_url: str | None = None
            try:
                jp = json.loads(body_p)
                if isinstance(jp, dict):
                    st_val = str(jp.get("status") or jp.get("state") or "").strip().lower()
                    if st_val in ("pending", "queued", "running", "in_progress", "processing", "accepted"):
                        is_pending = True
                    elif st_val in ("failed", "error", "cancelled", "aborted"):
                        self.protocol_events.append({"event": "ASYNC_202_FAILED", "poll_url": poll_url, "state": st_val})
                        return 400, ru_p, body_p, hdrs_p
                    else:
                        for rk in ("result_url", "artifact_url", "redirect_url"):
                            if isinstance(jp.get(rk), str) and jp[rk].strip():
                                result_url = urllib.parse.urljoin(ru_p, jp[rk].strip())
                                break
            except Exception:
                low_p = body_p.lower()
                if any(k in low_p for k in ('data-job-status="pending"', 'data-job-status="running"', "status: pending", "status: running", "job still running")):
                    is_pending = True
            if is_pending:
                continue
            if result_url:
                st_r, ru_r, body_r, hdrs_r = self._req(result_url, method="GET")
                self.protocol_events.append({"event": "ASYNC_202_COMPLETED", "poll_url": poll_url, "result_url": result_url, "polls": self.async_polls})
                return st_r, ru_r, body_r, hdrs_r
            self.protocol_events.append({"event": "ASYNC_202_COMPLETED", "poll_url": poll_url, "polls": self.async_polls})
            return st_p, ru_p, body_p, hdrs_p
        return st_p, ru_p, body_p, hdrs_p

    def _build_obs(self, *, post_ok_body: str = "") -> StateObs:
        sc = _HTTPPageScanner(self.current_url)
        sc.feed(self.current_html or "")
        sc.close()

        desc = HTMLFORM.describe(HTMLFORM.read_forms(self.current_html or ""))
        affs: list[Affordance] = []

        for idx, fm in enumerate(desc.get("forms") or ()):
            act = str(fm.get("action") or "")
            abs_act = urllib.parse.urljoin(self.current_url, act)
            btns = [str(b.get("label") or "") for b in (fm.get("buttons") or ())]
            label = " ".join(b for b in btns if b).strip() or act or f"form_{idx}"
            destr = bool(fm.get("destructive_risk")) or _is_destructive(act + " " + label)
            is_dis = any(b in sc.disabled_buttons for b in btns) if btns else False
            is_conf = any(w in (act + " " + label).lower() for w in ("confirm", "finalize", "proceed", "yes"))
            affs.append(Affordance(
                action_id=f"form:{idx}:{abs_act}",
                kind="submit_form",
                label=label,
                enabled=not is_dis,
                destructive=destr,
                is_modal_confirm=is_conf,
                meta={"form": fm, "action_url": abs_act},
            ))

        for db in sc.disabled_buttons:
            if not any(a.label == db and not a.enabled for a in affs):
                affs.append(Affordance(
                    action_id=f"disabled:{_norm_key(db)}",
                    kind="click",
                    label=db,
                    enabled=False,
                    destructive=_is_destructive(db),
                ))

        seen_u: set[str] = set()
        for lk in sc.links:
            u = lk["url"]
            if u in seen_u:
                continue
            seen_u.add(u)
            is_back = any(w in (lk["href"] + " " + lk["text"]).lower() for w in ("back", "home", "dashboard", "overview", "hub"))
            affs.append(Affordance(
                action_id=f"link:{u}",
                kind="nav_link",
                label=lk["text"],
                enabled=True,
                destructive=_is_destructive(lk["href"] + " " + lk["text"]),
                is_back_nav=is_back,
                meta={"url": u},
            ))

        vis_text = "\n".join(sc.text_parts)
        errors = list(self.last_errors)
        for al in sc.alerts:
            if al not in errors:
                errors.append(al)
        facts = _extract_artifacts(vis_text + "\n" + post_ok_body)
        if self._paginated_extra_facts:
            for pk, pv in self._paginated_extra_facts.items():
                facts.setdefault(pk, pv)

        low_v = (vis_text + " " + post_ok_body).lower()
        if self.goal_done_markers and any(m in low_v for m in self.goal_done_markers):
            self.done_reached = True
        elif any(m in low_v for m in ("data-goal-complete", "workflow completed", "deployed successfully", "published successfully", "transfer completed", "order confirmed")):
            self.done_reached = True

        path_name = urllib.parse.urlparse(self.current_url).path or "/"
        obs = StateObs(
            state_id="",
            screen_name=path_name,
            visible_text=vis_text,
            affordances=affs,
            errors=errors,
            done=self.done_reached,
            facts=facts,
            raw={"url": self.current_url, "http_status": self.last_status, "html": self.current_html},
        )
        obs.state_id = _compute_state_hash(obs)
        self.url_by_state[obs.state_id] = self.current_url
        return obs

    def observe(self) -> StateObs:
        if not self.current_html:
            st, ru, body, hdrs = self._req(self.start_url, method="GET")
            self.last_status, self.current_url, self.current_html = st, ru, body
            self.last_errors = [body] if st >= 400 else []
            self._paginated_extra_facts = (
                self._harvest_paginated_artifacts(ru, body, hdrs) if 200 <= st < 300 else {}
            )
        return self._build_obs()

    def jump_to_url(self, url: str) -> StateObs:
        st, ru, body, hdrs = self._req(url, method="GET")
        self.last_status, self.current_url, self.current_html = st, ru, body
        self.last_errors = [body] if st >= 400 else []
        self._paginated_extra_facts = (
            self._harvest_paginated_artifacts(ru, body, hdrs) if 200 <= st < 300 else {}
        )
        return self._build_obs()

    def execute(self, aff: Affordance, bindings: Mapping[str, str]) -> tuple[StateObs, dict[str, Any]]:
        if aff.kind == "nav_link":
            u = str(aff.meta["url"])
            st, ru, body, hdrs = self._req(u, method="GET")
            if st == 401 and self._try_refresh_auth(body, hdrs, bindings):
                st, ru, body, hdrs = self._req(u, method="GET")
            self.last_status, self.current_url, self.current_html = st, ru, body
            self.last_errors = [body] if st >= 400 else []
            self._paginated_extra_facts = (
                self._harvest_paginated_artifacts(ru, body, hdrs, bindings=bindings) if 200 <= st < 300 else {}
            )
            return self._build_obs(), {"action": "nav_link", "url": u, "status": st}

        if aff.kind == "submit_form":
            fm = aff.meta["form"]
            act_url = str(aff.meta["action_url"])
            method = str(fm.get("method") or "POST").upper()

            def _build_payload(form_dict: Mapping[str, Any]) -> dict[str, str]:
                pl: dict[str, str] = {}
                for hk, hv in (form_dict.get("hidden_replay") or {}).items():
                    pl[str(hk)] = str(hv)
                req_f = list(form_dict.get("required_input") or ())
                opt_f = list(form_dict.get("optional_input") or ())
                choices = form_dict.get("choices") or {}
                extra_f = list(bindings.get("__extra_fields__", "").split(",")) if bindings.get("__extra_fields__") else []
                for fname in list(dict.fromkeys(req_f + opt_f + [f for f in extra_f if f])):
                    nk = _norm_key(fname)
                    val = bindings.get(fname) or bindings.get(nk)
                    if val is None:
                        for tail in ("token", "code", "key", "pin", "otp", "username", "password", "email", "name"):
                            if tail in nk and tail in bindings:
                                val = bindings[tail]
                                break
                    if val is not None:
                        pl[fname] = str(val)
                    elif fname in req_f:
                        pl[fname] = str(choices[fname][0]) if (fname in choices and choices[fname]) else f"auto_{nk}"
                return pl

            payload = _build_payload(fm)
            self._mutation_seq += 1
            idem_key = "wm-" + hashlib.sha256(
                f"{act_url}|{sorted(payload.items())}|{self._mutation_seq}".encode("utf-8")
            ).hexdigest()[:16]
            req_hdrs: dict[str, str] = {}
            active_occ_hdr = self.discovered_occ_header or self.proactive_occ_header
            if active_occ_hdr:
                cur_etag = self.etag_by_url.get(self.current_url) or self.etag_by_url.get(act_url) or self.latest_etag
                if cur_etag:
                    req_hdrs[active_occ_hdr] = cur_etag
            active_idem_hdr = self.discovered_idempotency_header or self.proactive_idempotency_header
            if active_idem_hdr:
                req_hdrs[active_idem_hdr] = idem_key

            st, ru, body, hdrs = self._req(act_url, method=method, form_data=payload, extra_headers=req_hdrs)

            # 1. Mid-Session 401 Unauthorized -> transparent auth/token refresh + replay (preserves belief state!)
            if st == 401 and self._try_refresh_auth(body, hdrs, bindings):
                st, ru, body, hdrs = self._req(act_url, method=method, form_data=payload, extra_headers=req_hdrs)

            # 1b. IETF Idempotency-Key / Custom Deduplication Header Discovery & Policy-Drift Quarantine
            idem_hdr_hint = self._extract_idempotency_header_hint(st, body, hdrs)
            if idem_hdr_hint:
                if active_idem_hdr and idem_hdr_hint.lower() != active_idem_hdr.lower():
                    self.policy_drift_quarantines += 1
                    self.protocol_events.append({
                        "event": "IDEMPOTENCY_POLICY_DRIFT_QUARANTINE",
                        "stale_header": active_idem_hdr,
                        "new_header": idem_hdr_hint,
                    })
                retry_idem_hdrs = {k: v for k, v in req_hdrs.items() if k.lower() != (active_idem_hdr or "").lower()}
                retry_idem_hdrs[idem_hdr_hint] = idem_key
                st_i, ru_i, body_i, hdrs_i = self._req(act_url, method=method, form_data=payload, extra_headers=retry_idem_hdrs)
                if st_i == 401 and self._try_refresh_auth(body_i, hdrs_i, bindings):
                    st_i, ru_i, body_i, hdrs_i = self._req(act_url, method=method, form_data=payload, extra_headers=retry_idem_hdrs)
                if 200 <= st_i < 300 or st_i in (409, 412):
                    self.discovered_idempotency_header = idem_hdr_hint
                    self.idempotency_recoveries += 1
                    req_hdrs = retry_idem_hdrs
                    self.protocol_events.append({
                        "event": "IDEMPOTENCY_HEADER_RECOVERY",
                        "header": idem_hdr_hint,
                        "idempotency_key": idem_key,
                        "initial_status": st,
                        "retry_status": st_i,
                    })
                st, ru, body, hdrs = st_i, ru_i, body_i, hdrs_i

            # 2. RFC 9110 Optimistic Concurrency Control (`412 Precondition Failed` / `409 Conflict` / policy-drifted header):
            #    Re-read fresh ETag + hidden fields via GET, detect policy drift if recalled header was rejected, and replay!
            occ_hdr_hint = self._extract_occ_header_hint(st, body, hdrs)
            if occ_hdr_hint:
                if active_occ_hdr and occ_hdr_hint.lower() != active_occ_hdr.lower():
                    self.policy_drift_quarantines += 1
                    self.protocol_events.append({
                        "event": "POLICY_DRIFT_QUARANTINE",
                        "stale_header": active_occ_hdr,
                        "new_header": occ_hdr_hint,
                    })
                # Re-read current page to obtain fresh ETag + refreshed hidden form version/csrf tokens
                st_g, ru_g, body_g, _ = self._req(self.current_url, method="GET")
                if 200 <= st_g < 300:
                    self.current_html = body_g
                    # Refresh hidden fields from latest HTML if matching form action exists
                    desc_g = HTMLFORM.describe(HTMLFORM.read_forms(body_g or ""))
                    for fm_g in (desc_g.get("forms") or ()):
                        if urllib.parse.urljoin(ru_g, str(fm_g.get("action") or "")) == act_url:
                            payload = _build_payload(fm_g)
                            break
                fresh_etag = self.etag_by_url.get(self.current_url) or self.etag_by_url.get(act_url) or self.latest_etag
                retry_hdrs = {k: v for k, v in req_hdrs.items() if k.lower() != (active_occ_hdr or "").lower()}
                if fresh_etag:
                    retry_hdrs[occ_hdr_hint] = fresh_etag
                st2, ru2, body2, hdrs2 = self._req(act_url, method=method, form_data=payload, extra_headers=retry_hdrs)
                if st2 == 401 and self._try_refresh_auth(body2, hdrs2, bindings):
                    st2, ru2, body2, hdrs2 = self._req(act_url, method=method, form_data=payload, extra_headers=retry_hdrs)
                if 200 <= st2 < 300:
                    self.discovered_occ_header = occ_hdr_hint
                    self.occ_recoveries += 1
                    self.protocol_events.append({
                        "event": "OCC_ETAG_RECOVERY",
                        "header": occ_hdr_hint,
                        "etag": fresh_etag,
                        "initial_status": st,
                        "retry_status": st2,
                    })
                    st, ru, body, hdrs = st2, ru2, body2, hdrs2
                else:
                    st, ru, body, hdrs = st2, ru2, body2, hdrs2

            # 3. RFC 9110 Async Long-Running Job (`202 Accepted` + `Location` / `status_url` polling)
            if st == 202:
                st, ru, body, hdrs = self._poll_async_job(st, ru, body, hdrs)

            self.last_status = st
            if 200 <= st < 300:
                self.current_url, self.current_html = ru, body
                self.last_errors = []
                return self._build_obs(post_ok_body=body), {"action": "submit_form", "url": act_url, "status": st, "keys": sorted(payload)}
            else:
                # Keep current page HTML intact so we stay grounded on the form, record server rejection error!
                self.last_errors = [body]
                return self._build_obs(), {"action": "submit_form", "url": act_url, "status": st, "keys": sorted(payload), "error": body[:200]}

        return self.observe(), {"action": "noop"}

    def can_jump_url(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# 4. External Memory: Compositional World-Model Plan Distillation & Recall
# ---------------------------------------------------------------------------

def _plan_key(goal_role: str) -> str:
    return "wmplan_" + hashlib.sha256(f"wm_plan|{goal_role}".encode("utf-8")).hexdigest()[:12]


def _recall_world_model_plan(memory: dict[str, Any] | None, goal_role: str) -> dict[str, Any] | None:
    if not isinstance(memory, dict):
        return None
    store = memory.get("world_model_plans")
    if not isinstance(store, dict):
        return None
    pid = _plan_key(goal_role)
    rec = store.get(pid)
    return rec if isinstance(rec, dict) else None


def _distill_world_model_plan(
    memory: dict[str, Any] | None,
    *,
    goal_role: str,
    precondition_roles: Sequence[str],
    unlock_action_role: str | None,
    artifact_roles: Sequence[str],
    uses_confirmation: bool,
    blocked_traps: bool,
    protocol_laws: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(memory, dict):
        return None
    store = memory.setdefault("world_model_plans", {})
    if not isinstance(store, dict):
        return None
    pid = _plan_key(goal_role)
    prev = store.get(pid)
    merged_pre = list(dict.fromkeys(list((prev or {}).get("precondition_roles") or []) + list(precondition_roles)))
    merged_art = list(dict.fromkeys(list((prev or {}).get("artifact_roles") or []) + list(artifact_roles)))
    merged_proto = dict((prev or {}).get("protocol_laws") or {})
    if protocol_laws:
        for pk, pv in protocol_laws.items():
            if pv is not None:
                merged_proto[str(pk)] = pv
    plan = {
        "law_id": pid,
        "kind": "CAUSAL_WORLD_MODEL_PLAN",
        "goal_role": goal_role,
        "precondition_roles": merged_pre,
        "unlock_action_role": unlock_action_role or (prev or {}).get("unlock_action_role"),
        "artifact_roles": merged_art,
        "uses_confirmation": bool(uses_confirmation or (prev or {}).get("uses_confirmation")),
        "blocks_destructive_traps": bool(blocked_traps or (prev or {}).get("blocks_destructive_traps")),
        "protocol_laws": merged_proto,
        "uses": int((prev or {}).get("uses", 0)) + 1,
        "parameters_stored": 0,
    }
    store[pid] = plan
    return plan


# ---------------------------------------------------------------------------
# 5. Core Epistemic Belief-State Planner (World Model + Backtracking + Subgoals)
# ---------------------------------------------------------------------------

def solve_with_epistemic_world_model(
    adapter: InteractiveA11yWorldAdapter | LiveHTTPWorldAdapter,
    instruction: str,
    *,
    field_values: Mapping[str, Any] | None = None,
    memory: dict[str, Any] | None = None,
    max_steps: int = 32,
) -> dict[str, Any]:
    """Run the unified Belief-State World-Model Planner over ANY supported adapter."""
    t0 = time.monotonic()
    goal_toks = _toks(instruction)
    goal_role = _abstract_role(instruction)
    allow_destructive = _is_destructive(instruction)

    bindings: dict[str, str] = {}
    for k, v in (field_values or {}).items():
        bindings[str(k)] = str(v)
        bindings[_norm_key(str(k))] = str(v)

    # Tier-0 Compositional World-Model Plan Recall!
    recalled_plan = _recall_world_model_plan(memory, goal_role)
    if isinstance(adapter, LiveHTTPWorldAdapter) and isinstance(recalled_plan, dict):
        proto_rec = recalled_plan.get("protocol_laws")
        if isinstance(proto_rec, dict):
            if proto_rec.get("occ_header"):
                adapter.proactive_occ_header = str(proto_rec["occ_header"])
            if proto_rec.get("idempotency_header"):
                adapter.proactive_idempotency_header = str(proto_rec["idempotency_header"])

    # Dynamic Goal Stack: top of stack is active subgoal; base is main goal.
    subgoal_stack: list[dict[str, Any]] = []
    if recalled_plan and recalled_plan.get("precondition_roles"):
        pre_terms: set[str] = set()
        for pr in recalled_plan["precondition_roles"]:
            pre_terms.add(pr)
            pre_terms |= set(_ROLE_CANON.get(pr, ()))
        if recalled_plan.get("unlock_action_role"):
            ur = str(recalled_plan["unlock_action_role"])
            pre_terms.add(ur)
            pre_terms |= set(_ROLE_CANON.get(ur, ()))
        subgoal_stack.append({
            "kind": "PROACTIVE_PRECONDITION",
            "terms": pre_terms,
            "roles": list(recalled_plan["precondition_roles"]),
            "source": "tier0_world_model_plan",
        })

    # Factored Symbolic Transition World Model (CUWM principle):
    #   1. Exact belief-state signatures (`world_nodes`, `state_tried`) detect stagnation &
    #      re-enable target actions once prerequisites change screen state.
    #   2. Topological Screen Graph (`screen_edges`, `screen_obs`, `visited_nav_actions`)
    #      stays invariant under global belief-state deltas so BFS backtracking & target
    #      return ALWAYS work across multi-hop prerequisite unlocks!
    world_nodes: dict[str, StateObs] = {}
    screen_obs: dict[str, StateObs] = {}
    screen_edges: dict[str, list[tuple[str, str]]] = {}  # screen_name -> [(action_id, next_screen)]
    screen_url: dict[str, str] = {}
    tried_actions: dict[str, set[str]] = {}  # state_id -> set[action_id]
    explored_nav_by_screen: dict[str, set[str]] = {}  # screen_name -> set[action_id] already navigated
    blocked_until_unlock: set[str] = set()  # action_ids blocked by active precondition subgoal
    causal_preconditions: list[dict[str, Any]] = []
    discovered_precondition_roles: list[str] = []
    discovered_artifact_roles: list[str] = []
    unlock_action_role: str | None = None

    blocked_traps: list[str] = []
    traps_hit = 0
    failed_probes = 0
    backtracks = 0
    uses_confirmation = False
    trace: list[dict[str, Any]] = []
    target_screen_name: str | None = None

    def _bfs_next_action_to_screen(start_screen: str, goal_screens: set[str]) -> str | None:
        if start_screen in goal_screens:
            return None
        q: deque[tuple[str, str | None]] = deque([(start_screen, None)])
        seen: set[str] = {start_screen}
        while q:
            cur_sc, first_act = q.popleft()
            for act_id, nxt_sc in screen_edges.get(cur_sc, ()):
                fa = act_id if first_act is None else first_act
                if nxt_sc in goal_screens:
                    return fa
                if nxt_sc not in seen:
                    seen.add(nxt_sc)
                    q.append((nxt_sc, fa))
        return None

    obs = adapter.observe()
    world_nodes[obs.state_id] = obs
    screen_obs[obs.screen_name] = obs
    if isinstance(adapter, LiveHTTPWorldAdapter):
        screen_url[obs.screen_name] = adapter.current_url
    for k, v in obs.facts.items():
        bindings.setdefault(k, v)

    for step_idx in range(1, max_steps + 1):
        if obs.done:
            break

        cur_sid = obs.state_id
        cur_screen = obs.screen_name
        world_nodes[cur_sid] = obs
        screen_obs[cur_screen] = obs
        if isinstance(adapter, LiveHTTPWorldAdapter):
            screen_url[cur_screen] = adapter.current_url
        tried = tried_actions.setdefault(cur_sid, set())
        nav_tried = explored_nav_by_screen.setdefault(cur_screen, set())

        # Harvest any newly visible facts/artifacts into active belief state
        for k, v in obs.facts.items():
            if not k.startswith("env_") and k not in bindings:
                bindings[k] = v
                if k not in discovered_artifact_roles:
                    discovered_artifact_roles.append(k)

        # Record any destructive traps present on this screen & NEVER execute them
        safe_affs: list[Affordance] = []
        disabled_goal_labels: list[str] = []
        for a in obs.affordances:
            if a.destructive and not allow_destructive:
                if a.label not in blocked_traps:
                    blocked_traps.append(a.label)
                continue
            if not a.enabled:
                if _toks(a.label) & goal_toks or _abstract_role(a.label) == goal_role:
                    disabled_goal_labels.append(a.label)
                    target_screen_name = cur_screen
                continue
            safe_affs.append(a)

        # Check for disabled target button / live precondition error -> dynamically push precondition subgoal!
        if (obs.errors or disabled_goal_labels) and not any(sg.get("kind") == "DISCOVERED_PRECONDITION" for sg in subgoal_stack):
            sig = _extract_precondition_signal(obs.errors, disabled_goal_labels)
            if sig["terms"] or sig["artifact_keys"]:
                if target_screen_name is None:
                    target_screen_name = cur_screen
                pre_roles = list(dict.fromkeys(_abstract_role(t) for t in sig["terms"] if _abstract_role(t) in _ROLE_CANON))
                for pr in pre_roles:
                    if pr not in discovered_precondition_roles:
                        discovered_precondition_roles.append(pr)
                for ak in sig["artifact_keys"]:
                    if ak not in discovered_artifact_roles:
                        discovered_artifact_roles.append(ak)
                subgoal_stack.append({
                    "kind": "DISCOVERED_PRECONDITION",
                    "terms": set(sig["terms"]),
                    "artifact_keys": list(sig["artifact_keys"]),
                    "roles": pre_roles,
                    "source": "live_precondition_error",
                })
                causal_preconditions.append({
                    "step": step_idx,
                    "screen": cur_screen,
                    "terms": sorted(sig["terms"]),
                    "artifact_keys": sig["artifact_keys"],
                })

        # 1. Modal confirmation takes immediate top priority (post-target safety dialog)
        modal_conf = next((a for a in safe_affs if a.is_modal_confirm and a.action_id not in tried), None)
        if modal_conf is not None:
            uses_confirmation = True
            tried.add(modal_conf.action_id)
            nxt_obs, act_log = adapter.execute(modal_conf, bindings)
            if nxt_obs.raw.get("trap_triggered"):
                traps_hit += 1
            if nxt_obs.screen_name != cur_screen:
                screen_edges.setdefault(cur_screen, []).append((modal_conf.action_id, nxt_obs.screen_name))
            trace.append({"step": step_idx, "phase": "MODAL_CONFIRM", "screen": cur_screen, "action": act_log, "next_screen": nxt_obs.screen_name})
            obs = nxt_obs
            continue

        # 2. Fill any unfilled input fields on the current screen whose bindings we already hold
        unfilled_input = None
        for a in safe_affs:
            if a.kind == "input" and a.action_id not in tried:
                nk = _norm_key(a.label)
                val = bindings.get(a.action_id) or bindings.get(nk)
                if val is None:
                    for tail in ("token", "code", "key", "pin", "otp", "username", "password", "email", "name"):
                        if tail in nk and tail in bindings:
                            val = bindings[tail]
                            break
                if val is not None and str(val) != a.value:
                    unfilled_input = a
                    break
        if unfilled_input is not None:
            tried.add(unfilled_input.action_id)
            nxt_obs, act_log = adapter.execute(unfilled_input, bindings)
            trace.append({"step": step_idx, "phase": "FILL_INPUT", "screen": cur_screen, "action": act_log})
            obs = nxt_obs
            continue

        # 3. Score candidate actions using Active Subgoal Alignment + Epistemic Information Gain!
        active_sg = subgoal_stack[-1] if subgoal_stack else None
        active_terms = set(active_sg["terms"]) if active_sg else set(goal_toks)

        # If we have NO active precondition subgoal AND we previously discovered `target_screen_name`
        # AND we are NOT currently on `target_screen_name`, route straight back via Screen Graph!
        if active_sg is None and target_screen_name is not None and cur_screen != target_screen_name:
            if adapter.can_jump_url() and target_screen_name in screen_url:
                backtracks += 1
                nxt_obs = adapter.jump_to_url(screen_url[target_screen_name])
                trace.append({"step": step_idx, "phase": "WORLD_MODEL_RETURN_TO_TARGET", "from": cur_screen, "to": nxt_obs.screen_name})
                obs = nxt_obs
                continue
            route_act = _bfs_next_action_to_screen(cur_screen, {target_screen_name})
            aff_r = next((a for a in safe_affs if a.action_id == route_act), None) if route_act else None
            if aff_r is None:
                # Reverse-hop via Back/Home link to reach the hub that knows `target_screen_name`
                aff_r = next((a for a in safe_affs if a.is_back_nav), None)
            if aff_r is not None:
                backtracks += 1
                nxt_obs, act_log = adapter.execute(aff_r, bindings)
                if nxt_obs.screen_name != cur_screen:
                    screen_edges.setdefault(cur_screen, []).append((aff_r.action_id, nxt_obs.screen_name))
                trace.append({"step": step_idx, "phase": "WORLD_MODEL_RETURN_TO_TARGET", "screen": cur_screen, "action": act_log, "next_screen": nxt_obs.screen_name})
                obs = nxt_obs
                continue

        scored: list[tuple[float, Affordance]] = []
        for a in safe_affs:
            if a.kind == "input":
                continue
            if a.kind == "toggle" and a.checked:
                continue
            if active_sg is not None and a.action_id in blocked_until_unlock:
                continue
            if a.action_id in tried or a.action_id in nav_tried:
                continue
            a_toks = _toks(a.label + " " + a.action_id)
            a_role = _abstract_role(a.label)
            sc = 0.0

            if active_sg is not None:
                pre_ov = len(a_toks & active_terms)
                sc += pre_ov * 12.0
                if a_role in (active_sg.get("roles") or ()):
                    sc += 10.0
                if a.kind == "toggle" and not a.checked:
                    sc += 6.0 if pre_ov > 0 else 2.5
                if a.kind == "submit_form" and pre_ov > 0:
                    sc += 8.0
                if a_role == goal_role and pre_ov == 0 and (a.kind == "submit_form" or a_toks & goal_toks):
                    sc -= 15.0
                if not a.is_back_nav:
                    sc += 3.0
                else:
                    sc -= 2.0
            else:
                g_ov = len(a_toks & goal_toks)
                sc += g_ov * 12.0
                if a_role == goal_role:
                    sc += 10.0
                if a.kind == "submit_form":
                    sc += 5.0
                if not a.is_back_nav:
                    sc += 2.0
                else:
                    sc -= 2.5

            scored.append((sc, a))

        chosen: Affordance | None = None
        if scored:
            scored.sort(key=lambda x: (-x[0], x[1].action_id))
            if scored[0][0] > -5.0:
                chosen = scored[0][1]

        # 4. Automatic World-Model Backtracking when on a Dead End (all local actions exhausted!)
        if chosen is None:
            frontier_screens: set[str] = set()
            for sc_name, st_obs in screen_obs.items():
                if sc_name == cur_screen:
                    continue
                t_st = tried_actions.get(st_obs.state_id, set())
                t_nv = explored_nav_by_screen.get(sc_name, set())
                if any(
                    (not x.destructive or allow_destructive)
                    and x.enabled
                    and x.kind != "input"
                    and (not x.is_back_nav)
                    and x.action_id not in t_st
                    and x.action_id not in t_nv
                    for x in st_obs.affordances
                ):
                    frontier_screens.add(sc_name)

            if adapter.can_jump_url() and frontier_screens:
                # Prefer frontier screens whose affordances best match active_terms
                def _f_score(sn: str) -> float:
                    st_o = screen_obs[sn]
                    t_nv = explored_nav_by_screen.get(sn, set())
                    best = 0.0
                    for x in st_o.affordances:
                        if x.action_id not in t_nv and not x.is_back_nav and x.enabled and not x.destructive:
                            best = max(best, float(len(_toks(x.label) & active_terms)))
                    return best
                target_f = max(sorted(frontier_screens), key=_f_score)
                if target_f in screen_url:
                    backtracks += 1
                    nxt_obs = adapter.jump_to_url(screen_url[target_f])
                    trace.append({"step": step_idx, "phase": "BACKTRACK_JUMP", "from": cur_screen, "to": nxt_obs.screen_name})
                    obs = nxt_obs
                    continue

            if frontier_screens:
                bt_act_id = _bfs_next_action_to_screen(cur_screen, frontier_screens)
                if bt_act_id:
                    aff_bt = next((a for a in safe_affs if a.action_id == bt_act_id), None)
                    if aff_bt is not None:
                        backtracks += 1
                        nxt_obs, act_log = adapter.execute(aff_bt, bindings)
                        if nxt_obs.screen_name != cur_screen:
                            screen_edges.setdefault(cur_screen, []).append((aff_bt.action_id, nxt_obs.screen_name))
                        trace.append({"step": step_idx, "phase": "BACKTRACK_BFS", "screen": cur_screen, "action": act_log, "next_screen": nxt_obs.screen_name})
                        obs = nxt_obs
                        continue

            back_aff = next((a for a in safe_affs if a.is_back_nav), None)
            if back_aff is not None:
                backtracks += 1
                nxt_obs, act_log = adapter.execute(back_aff, bindings)
                if nxt_obs.screen_name != cur_screen:
                    screen_edges.setdefault(cur_screen, []).append((back_aff.action_id, nxt_obs.screen_name))
                trace.append({"step": step_idx, "phase": "BACKTRACK_NAV", "screen": cur_screen, "action": act_log, "next_screen": nxt_obs.screen_name})
                if nxt_obs.state_id == cur_sid and nxt_obs.screen_name == cur_screen:
                    break
                obs = nxt_obs
                continue

            if subgoal_stack:
                subgoal_stack.pop()
                continue
            break

        # 5. Execute chosen action & update Factored World Model!
        tried.add(chosen.action_id)
        pre_facts = dict(obs.facts)
        nxt_obs, act_log = adapter.execute(chosen, bindings)
        if nxt_obs.raw.get("trap_triggered"):
            traps_hit += 1
        if nxt_obs.screen_name != cur_screen:
            screen_edges.setdefault(cur_screen, []).append((chosen.action_id, nxt_obs.screen_name))
            # Mark navigation action explored on cur_screen (except returning to target screen)
            if not chosen.is_back_nav and nxt_obs.screen_name != target_screen_name:
                nav_tried.add(chosen.action_id)

        added_facts = {k: v for k, v in nxt_obs.facts.items() if pre_facts.get(k) != v}
        new_artifacts = {k: v for k, v in added_facts.items() if not k.startswith("env_")}
        for k, v in new_artifacts.items():
            bindings[k] = v
            if k not in discovered_artifact_roles:
                discovered_artifact_roles.append(k)

        action_failed = bool(nxt_obs.errors) and (not nxt_obs.done) and (nxt_obs.state_id == cur_sid or act_log.get("status", 200) >= 400)
        if action_failed:
            failed_probes += 1
            blocked_until_unlock.add(chosen.action_id)
            if _abstract_role(chosen.label) == goal_role or (_toks(chosen.label) & goal_toks):
                target_screen_name = cur_screen
                tried.discard(chosen.action_id)
            sig = _extract_precondition_signal(nxt_obs.errors, [])
            if sig["artifact_keys"]:
                existing_ex = [x for x in bindings.get("__extra_fields__", "").split(",") if x]
                for ak in sig["artifact_keys"]:
                    if ak not in existing_ex:
                        existing_ex.append(ak)
                bindings["__extra_fields__"] = ",".join(existing_ex)
            if (sig["terms"] or sig["artifact_keys"]) and not any(sg.get("kind") == "DISCOVERED_PRECONDITION" for sg in subgoal_stack):
                pre_roles = list(dict.fromkeys(_abstract_role(t) for t in sig["terms"] if _abstract_role(t) in _ROLE_CANON))
                for pr in pre_roles:
                    if pr not in discovered_precondition_roles:
                        discovered_precondition_roles.append(pr)
                subgoal_stack.append({
                    "kind": "DISCOVERED_PRECONDITION",
                    "terms": set(sig["terms"]),
                    "artifact_keys": list(sig["artifact_keys"]),
                    "roles": pre_roles,
                    "source": "action_rejection_error",
                })
                causal_preconditions.append({
                    "step": step_idx,
                    "screen": cur_screen,
                    "terms": sorted(sig["terms"]),
                    "artifact_keys": sig["artifact_keys"],
                })
        elif active_sg is not None:
            a_toks = _toks(chosen.label)
            satisfied = False
            if new_artifacts:
                satisfied = True
            elif chosen.kind == "toggle" and (a_toks & active_sg["terms"] or added_facts):
                satisfied = True
            elif chosen.kind in ("click", "submit_form") and (not chosen.is_back_nav) and (added_facts or nxt_obs.state_id != cur_sid and nxt_obs.screen_name == cur_screen) and (a_toks & active_sg["terms"] or _abstract_role(chosen.label) in (active_sg.get("roles") or ())):
                satisfied = True
            if satisfied:
                nav_tried.add(chosen.action_id)
                unlock_action_role = _abstract_role(chosen.label)
                for pr in (active_sg.get("roles") or ()):
                    if pr not in discovered_precondition_roles:
                        discovered_precondition_roles.append(pr)
                # Clear tried & blocked on target screen so previously blocked target can execute now!
                blocked_until_unlock.clear()
                if target_screen_name and target_screen_name in screen_obs:
                    tried_actions.pop(screen_obs[target_screen_name].state_id, None)
                subgoal_stack.pop()

        trace.append({
            "step": step_idx,
            "phase": "SUBGOAL_STEP" if active_sg else "GOAL_STEP",
            "screen": cur_screen,
            "action": act_log,
            "next_screen": nxt_obs.screen_name,
            "delta_facts": sorted(added_facts.keys()),
            "failed": action_failed,
        })
        obs = nxt_obs

    verified = bool(obs.done)
    proto_laws: dict[str, Any] = {}
    proto_events: list[dict[str, Any]] = []
    occ_recoveries = 0
    async_polls = 0
    auth_refreshes = 0
    rate_limit_retries = 0
    idempotency_recoveries = 0
    pages_traversed = 0
    policy_drift_quarantines = 0
    if isinstance(adapter, LiveHTTPWorldAdapter):
        occ_recoveries = adapter.occ_recoveries
        async_polls = adapter.async_polls
        auth_refreshes = adapter.auth_refreshes
        rate_limit_retries = adapter.rate_limit_retries
        idempotency_recoveries = adapter.idempotency_recoveries
        pages_traversed = adapter.pages_traversed
        policy_drift_quarantines = adapter.policy_drift_quarantines
        proto_events = list(adapter.protocol_events)
        if adapter.discovered_occ_header:
            proto_laws["occ_header"] = adapter.discovered_occ_header
        elif adapter.proactive_occ_header:
            proto_laws["occ_header"] = adapter.proactive_occ_header
        if adapter.discovered_idempotency_header:
            proto_laws["idempotency_header"] = adapter.discovered_idempotency_header
        elif adapter.proactive_idempotency_header:
            proto_laws["idempotency_header"] = adapter.proactive_idempotency_header
        if async_polls > 0:
            proto_laws["async_202_polling"] = True
        if auth_refreshes > 0:
            proto_laws["auth_401_refresh"] = True
        if rate_limit_retries > 0:
            proto_laws["rate_limit_429_503_backoff"] = True
        if pages_traversed > 0:
            proto_laws["pagination_next_traversal"] = True

    distilled_plan: dict[str, Any] | None = None
    if verified and (discovered_precondition_roles or causal_preconditions or unlock_action_role or recalled_plan or proto_laws):
        distilled_plan = _distill_world_model_plan(
            memory,
            goal_role=goal_role,
            precondition_roles=discovered_precondition_roles or ([unlock_action_role] if unlock_action_role else []),
            unlock_action_role=unlock_action_role,
            artifact_roles=discovered_artifact_roles,
            uses_confirmation=uses_confirmation,
            blocked_traps=bool(blocked_traps),
            protocol_laws=proto_laws or None,
        )

    mode_tag = (
        "TIER0_WORLD_MODEL_PLAN"
        if (
            verified
            and recalled_plan is not None
            and failed_probes == 0
            and occ_recoveries == 0
            and idempotency_recoveries == 0
            and policy_drift_quarantines == 0
        )
        else ("EPISTEMIC_WORLD_MODEL_PLANNER" if verified else "WORLD_MODEL_PLAN_EXHAUSTED")
    )
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "status": "VERIFIED" if verified else "FAILED",
        "mode": mode_tag,
        "steps_taken": len(trace),
        "states_discovered": len(world_nodes),
        "backtracks": backtracks,
        "failed_probes": failed_probes,
        "traps_avoided": blocked_traps,
        "traps_hit": traps_hit,
        "occ_recoveries": occ_recoveries,
        "async_polls": async_polls,
        "auth_refreshes": auth_refreshes,
        "rate_limit_retries": rate_limit_retries,
        "idempotency_recoveries": idempotency_recoveries,
        "pages_traversed": pages_traversed,
        "policy_drift_quarantines": policy_drift_quarantines,
        "protocol_events": proto_events,
        "causal_preconditions": causal_preconditions,
        "harvested_artifacts": {k: v for k, v in bindings.items() if k in discovered_artifact_roles},
        "recalled_plan_id": recalled_plan["law_id"] if recalled_plan else None,
        "distilled_plan": distilled_plan,
        "final_screen": obs.screen_name,
        "trace": trace,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }
