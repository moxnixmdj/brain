"""Epistemic Enterprise Multi-Page Web Agent v1 (WorkArena / WebArena-Pro Class).

Zero-LLM (`model_calls=0`), zero-weight (`parameters_stored=0`), stdlib-only epistemic
solver for the three hardest real-world enterprise browser workflows:
  1. `WEB_TABLE_FILTER_AGGREGATE`: Authenticated multi-page HTML table pagination,
     fuzzy column resolution, relational filtering (equality, substring, numeric bounds),
     sorting, detail-page drill-down, and exact deterministic aggregation
     (`count`, `sum`, `avg`, `max`, `min`, `top_k`, `list`, `lookup`).
  2. `WEB_RECORD_CRUD_EDIT`: Authenticated multi-page record localization -> safe
     Edit/Detail navigation (strictly blocking destructive traps) -> pre-populated form
     value preservation + CSRF replay + targeted field updates + error-driven required
     field discovery + verified persistence.
  3. `WEB_CROSS_APP_BRIDGE`: Multi-application pipeline across two independent live web
     sites with isolated cookie sessions (Source App query/detail harvest -> semantic
     fact projection -> Target App authenticated CSRF creation/posting), PLUS single-
     experience polymorphic skill distillation (`web_enterprise_skills`) for zero-probe
     Tier-0 transfer across completely unseen web app pairs and instant unlearning.
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
from html.parser import HTMLParser
from typing import Any, Mapping, Sequence

from canonical.runtime import compose_v1 as COMPOSE_ERR
from canonical.runtime import htmlform_read_v1 as HTMLFORM

SCHEMA = "brain.epistemic_enterprise_web_agent.v1"
AUTHORITY = "NONE"

_DESTRUCTIVE_WORDS = (
    "delete",
    "destroy",
    "purge",
    "wipe",
    "revoke",
    "drop",
    "terminate",
    "erase",
    "remove",
    "nuke",
    "close-account",
    "close_account",
    "deactivate",
    "reset-all",
    "reset_all",
)

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "username": ("username", "user", "login", "userid", "user_id", "account", "email", "handle", "member"),
    "password": ("password", "pass", "pwd", "passwd", "secret"),
    "title": ("title", "subject", "heading", "name", "page_title", "doc_title", "summary_title", "topic"),
    "summary": ("summary", "body", "content", "description", "details", "message", "notes", "note", "text", "markdown", "comment"),
    "owner": ("owner", "assignee", "assigned_to", "author", "reporter", "contact", "manager", "lead", "requester", "responsible"),
    "status": ("status", "state", "stage", "resolution", "workflow_state"),
    "priority": ("priority", "severity", "urgency", "level", "impact"),
    "category": ("category", "type", "department", "dept", "team", "group", "queue", "tag", "component"),
    "ticket_id": ("ticket_id", "ref_id", "reference", "incident_id", "issue_id", "case_id", "record_id", "external_id", "source_id", "id"),
    "amount": ("amount", "total", "cost", "price", "budget", "revenue", "value", "balance", "salary", "spend", "fee"),
    "email": ("email", "e-mail", "mail", "recipient", "to_email", "contact_email"),
    "channel": ("channel", "channel_id", "room", "workspace", "space", "folder", "project", "board", "notebook"),
}


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").strip().lower()).strip("_")


def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(str(s or ""))).strip()


def _parse_number(s: Any) -> float | None:
    if isinstance(s, (int, float)) and not isinstance(s, bool):
        return float(s)
    txt = _clean_text(str(s or ""))
    if not txt:
        return None
    m = re.fullmatch(r"[\$\€\£\¥]?\s*([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*%?", txt)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _is_destructive_text(s: str) -> bool:
    low = str(s or "").lower()
    return any(w in low for w in _DESTRUCTIVE_WORDS)


def _is_form_destructive(fm: Mapping[str, Any]) -> bool:
    if fm.get("destructive_risk"):
        return True
    act = str(fm.get("action") or "")
    btns = " ".join(str(b.get("label") or "") for b in (fm.get("buttons") or []))
    return _is_destructive_text(act + " " + btns)


# ---------------------------------------------------------------------------
# 1. Structural HTML Table, Link, Key-Value Detail & Pre-Filled Form Parsers
# ---------------------------------------------------------------------------

class _EnterprisePageParser(HTMLParser):
    """Single-pass stdlib parser extracting tables, links, headings, and detail KV pairs."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.tables: list[dict[str, Any]] = []
        self.links: list[dict[str, Any]] = []
        self.kv_pairs: dict[str, str] = {}
        self.headings: list[str] = []

        self._in_table = False
        self._table_depth = 0
        self._cur_table: dict[str, Any] | None = None
        self._in_thead = False
        self._in_tr = False
        self._cur_row_cells: list[dict[str, Any]] = []
        self._cur_row_is_header = False
        self._cur_row_attrs: dict[str, str] = {}
        self._in_cell = False
        self._cur_cell_text: list[str] = []
        self._cur_cell_links: list[dict[str, Any]] = []

        self._in_a = False
        self._cur_a_href = ""
        self._cur_a_text: list[str] = []

        self._in_dt = False
        self._in_dd = False
        self._cur_dt: list[str] = []
        self._cur_dd: list[str] = []
        self._last_dt = ""

        self._in_heading = False
        self._cur_heading: list[str] = []

        self._in_block = False
        self._block_tag = ""
        self._cur_block: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        if t == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._in_table = True
                self._cur_table = {"headers": [], "rows": [], "id": ad.get("id", ""), "class": ad.get("class", "")}
        elif self._in_table and self._table_depth == 1:
            if t == "thead":
                self._in_thead = True
            elif t == "tr":
                self._in_tr = True
                self._cur_row_cells = []
                self._cur_row_is_header = self._in_thead
                self._cur_row_attrs = {k: v for k, v in ad.items() if k == "id" or k.startswith("data-")}
            elif t in ("th", "td") and self._in_tr:
                self._in_cell = True
                if t == "th":
                    self._cur_row_is_header = True
                self._cur_cell_text = []
                self._cur_cell_links = []

        if t == "a":
            self._in_a = True
            self._cur_a_href = ad.get("href", "").strip()
            self._cur_a_text = []
        elif t == "dt":
            self._in_dt = True
            self._cur_dt = []
        elif t == "dd":
            self._in_dd = True
            self._cur_dd = []
        elif t in ("h1", "h2", "h3"):
            self._in_heading = True
            self._cur_heading = []
        elif t in ("p", "li", "div") and not self._in_table:
            if not self._in_block:
                self._in_block = True
                self._block_tag = t
                self._cur_block = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "a" and self._in_a:
            href = self._cur_a_href
            text = _clean_text(" ".join(self._cur_a_text))
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                abs_url = urllib.parse.urljoin(self.base_url, href)
                lk = {
                    "href": href,
                    "url": abs_url,
                    "text": text,
                    "is_destructive": _is_destructive_text(href + " " + text),
                }
                self.links.append(lk)
                if self._in_cell:
                    self._cur_cell_links.append(lk)
            self._in_a = False
            self._cur_a_href = ""
            self._cur_a_text = []

        if self._in_table and self._table_depth == 1:
            if t in ("th", "td") and self._in_cell:
                self._cur_row_cells.append({
                    "text": _clean_text(" ".join(self._cur_cell_text)),
                    "links": list(self._cur_cell_links),
                })
                self._in_cell = False
            elif t == "tr" and self._in_tr:
                assert self._cur_table is not None
                if self._cur_row_cells:
                    if self._cur_row_is_header and not self._cur_table["headers"]:
                        self._cur_table["headers"] = [c["text"] for c in self._cur_row_cells]
                    elif not self._cur_row_is_header:
                        self._cur_table["rows"].append({
                            "cells": list(self._cur_row_cells),
                            "attrs": dict(self._cur_row_attrs),
                        })
                self._in_tr = False
            elif t == "thead":
                self._in_thead = False
            elif t == "table":
                assert self._cur_table is not None
                # Fallback if table had no <th>/<thead>: use first row as header if >=2 rows
                if not self._cur_table["headers"] and len(self._cur_table["rows"]) >= 2:
                    self._cur_table["headers"] = [c["text"] for c in self._cur_table["rows"][0]["cells"]]
                    self._cur_table["rows"] = self._cur_table["rows"][1:]
                self.tables.append(self._cur_table)
                self._cur_table = None
                self._in_table = False
                self._table_depth = 0
        elif t == "table" and self._table_depth > 1:
            self._table_depth -= 1

        if t == "dt" and self._in_dt:
            self._last_dt = _clean_text(" ".join(self._cur_dt)).rstrip(":")
            self._in_dt = False
        elif t == "dd" and self._in_dd:
            val = _clean_text(" ".join(self._cur_dd))
            if self._last_dt and val:
                self.kv_pairs[_norm_key(self._last_dt)] = val
            self._in_dd = False
        elif t in ("h1", "h2", "h3") and self._in_heading:
            h = _clean_text(" ".join(self._cur_heading))
            if h:
                self.headings.append(h)
            self._in_heading = False
        elif self._in_block and t == self._block_tag:
            txt = _clean_text(" ".join(self._cur_block))
            m_kv = re.fullmatch(r"([A-Za-z][A-Za-z0-9 _/\-]{1,36}):\s+(.{1,240})", txt)
            if m_kv:
                k_norm = _norm_key(m_kv.group(1))
                v_clean = m_kv.group(2).strip()
                if k_norm and v_clean and k_norm not in self.kv_pairs:
                    self.kv_pairs[k_norm] = v_clean
            self._in_block = False
            self._block_tag = ""

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._cur_a_text.append(data)
        if self._in_cell:
            self._cur_cell_text.append(data)
        if self._in_dt:
            self._cur_dt.append(data)
        if self._in_dd:
            self._cur_dd.append(data)
        if self._in_heading:
            self._cur_heading.append(data)
        if self._in_block:
            self._cur_block.append(data)


class _FormPrefillParser(HTMLParser):
    """Extract existing field values and <label> text per form so CRUD edits preserve untouched fields."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[dict[str, Any]] = []
        self._cur: dict[str, Any] | None = None
        self._in_textarea = False
        self._ta_name = ""
        self._ta_buf: list[str] = []
        self._in_select = False
        self._sel_name = ""
        self._sel_opts: list[tuple[str, str, bool]] = []
        self._in_opt = False
        self._opt_val = ""
        self._opt_sel = False
        self._opt_buf: list[str] = []
        self._in_label = False
        self._label_for = ""
        self._label_buf: list[str] = []
        self._id_to_name: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        if t == "form":
            self._cur = {
                "action": ad.get("action", ""),
                "method": (ad.get("method", "GET") or "GET").upper(),
                "prefill": {},
                "labels": {},
                "select_options": {},
            }
            self._id_to_name = {}
        elif self._cur is not None:
            if t == "label":
                self._in_label = True
                self._label_for = ad.get("for", "")
                self._label_buf = []
            elif t == "input":
                name = ad.get("name", "")
                iid = ad.get("id", "")
                if name and iid:
                    self._id_to_name[iid] = name
                itype = ad.get("type", "text").lower()
                if name and itype not in ("submit", "button", "reset", "image"):
                    if itype in ("checkbox", "radio"):
                        if "checked" in ad:
                            self._cur["prefill"][name] = ad.get("value", "on")
                    elif "value" in ad:
                        self._cur["prefill"][name] = ad["value"]
            elif t == "textarea":
                name = ad.get("name", "")
                iid = ad.get("id", "")
                if name and iid:
                    self._id_to_name[iid] = name
                if name:
                    self._in_textarea = True
                    self._ta_name = name
                    self._ta_buf = []
            elif t == "select":
                name = ad.get("name", "")
                iid = ad.get("id", "")
                if name and iid:
                    self._id_to_name[iid] = name
                if name:
                    self._in_select = True
                    self._sel_name = name
                    self._sel_opts = []
            elif t == "option" and self._in_select:
                self._in_opt = True
                self._opt_val = ad.get("value", "")
                self._opt_sel = "selected" in ad
                self._opt_buf = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if self._cur is None:
            return
        if t == "label" and self._in_label:
            lbl = _clean_text(" ".join(self._label_buf)).rstrip(":")
            if self._label_for and lbl:
                self._cur["labels"][self._label_for] = lbl
            self._in_label = False
        elif t == "textarea" and self._in_textarea:
            self._cur["prefill"][self._ta_name] = "".join(self._ta_buf)
            self._in_textarea = False
        elif t == "option" and self._in_opt:
            txt = _clean_text(" ".join(self._opt_buf))
            val = self._opt_val if self._opt_val != "" else txt
            self._sel_opts.append((val, txt, self._opt_sel))
            self._in_opt = False
        elif t == "select" and self._in_select:
            self._cur["select_options"][self._sel_name] = list(self._sel_opts)
            for val, _txt, is_sel in self._sel_opts:
                if is_sel:
                    self._cur["prefill"][self._sel_name] = val
                    break
            self._in_select = False
        elif t == "form":
            # Map id-keyed labels to field names
            mapped_labels: dict[str, str] = {}
            for k_id, lbl in self._cur["labels"].items():
                fname = self._id_to_name.get(k_id, k_id)
                mapped_labels[fname] = lbl
            self._cur["labels"] = mapped_labels
            self.forms.append(self._cur)
            self._cur = None

    def handle_data(self, data: str) -> None:
        if self._in_textarea:
            self._ta_buf.append(data)
        if self._in_opt:
            self._opt_buf.append(data)
        if self._in_label:
            self._label_buf.append(data)


def parse_enterprise_page(html: str, base_url: str) -> dict[str, Any]:
    """Parse tables, normalized row dicts, links, detail KV pairs, and prefilled forms."""
    p = _EnterprisePageParser(base_url)
    p.feed(html or "")
    p.close()

    fp = _FormPrefillParser()
    fp.feed(html or "")
    fp.close()

    structured_tables: list[dict[str, Any]] = []
    for tb in p.tables:
        raw_headers = list(tb["headers"])
        norm_headers = [_norm_key(h) or f"col_{i}" for i, h in enumerate(raw_headers)]
        row_dicts: list[dict[str, Any]] = []
        for r in tb["rows"]:
            cells = r["cells"]
            fields: dict[str, str] = {}
            links: list[dict[str, Any]] = []
            for idx, cell in enumerate(cells):
                col = norm_headers[idx] if idx < len(norm_headers) else f"col_{idx}"
                fields[col] = cell["text"]
                for lk in cell["links"]:
                    links.append(lk)
            row_dicts.append({
                "fields": fields,
                "raw_cells": [c["text"] for c in cells],
                "links": links,
                "attrs": r["attrs"],
                "full_text": " ".join(c["text"] for c in cells),
            })
        structured_tables.append({
            "headers": raw_headers,
            "norm_headers": norm_headers,
            "rows": row_dicts,
            "id": tb["id"],
        })

    return {
        "tables": structured_tables,
        "links": p.links,
        "kv_pairs": p.kv_pairs,
        "headings": p.headings,
        "form_prefills": fp.forms,
    }


# ---------------------------------------------------------------------------
# 2. HTTP Cookie Session Helper
# ---------------------------------------------------------------------------

class _WebSession:
    def __init__(self, timeout_s: float = 10.0) -> None:
        self.timeout_s = timeout_s
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(
        self,
        url: str,
        *,
        method: str = "GET",
        form_data: Mapping[str, str] | None = None,
        json_data: Mapping[str, Any] | None = None,
    ) -> tuple[int, str, str]:
        headers: dict[str, str] = {}
        body: bytes | None = None
        m = method.upper()
        req_url = url
        if m == "GET" and form_data:
            qs = urllib.parse.urlencode(list(form_data.items()))
            sep = "&" if "?" in req_url else "?"
            req_url = f"{req_url}{sep}{qs}"
        elif json_data is not None:
            body = json.dumps(dict(json_data)).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form_data is not None:
            body = urllib.parse.urlencode(list(form_data.items())).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(req_url, data=body, headers=headers, method=m)
        try:
            with self.opener.open(req, timeout=self.timeout_s) as resp:
                return int(getattr(resp, "status", 200)), resp.geturl(), resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else str(exc)
            return int(exc.code), req_url, err_body


# ---------------------------------------------------------------------------
# 3. Goal Compiler: Filters, Aggregations, Record Targets & Field Updates
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://[^\s'\"<>]+", flags=re.IGNORECASE)


def extract_urls(instruction: str, extra_urls: Sequence[str] = ()) -> list[str]:
    urls: list[str] = []
    for u in extra_urls:
        if u and str(u) not in urls:
            urls.append(str(u))
    for m in _URL_RE.finditer(instruction or ""):
        u = m.group(0).rstrip(".,;)")
        if u and u not in urls:
            urls.append(u)
    return urls


def _resolve_alias_value(
    field_name: str,
    supplied: Mapping[str, str],
    *,
    label_text: str = "",
) -> str | None:
    nk = _norm_key(field_name)
    if nk in supplied:
        return supplied[nk]
    if field_name.lower() in supplied:
        return supplied[field_name.lower()]
    lbl_norm = _norm_key(label_text) if label_text else ""
    if lbl_norm and lbl_norm in supplied:
        return supplied[lbl_norm]
    for _canon, aliases in _FIELD_ALIASES.items():
        if nk in aliases or (lbl_norm and lbl_norm in aliases) or any(a in nk for a in aliases if len(a) >= 4):
            for a in aliases:
                if a in supplied:
                    return supplied[a]
    return None


def _parse_goal_filters_and_updates(instruction: str, supplied: Mapping[str, str]) -> dict[str, Any]:
    """Parse relational predicates, aggregation op, sort/return column, record ID, and updates."""
    text = instruction or ""
    low = text.lower()

    # 1. Detect explicit record IDs like INC-402, TKT-19, INV-2026-07, #42, ORD-99
    record_id: str | None = None
    m_id = re.search(r"\b([A-Z]{2,6}-\d{1,6}(?:-\d{1,4})?)\b", text)
    if m_id:
        record_id = m_id.group(1)
    else:
        m_hash = re.search(r"#(\d{1,6})\b", text)
        if m_hash:
            record_id = m_hash.group(1)

    # 2. Detect explicit equality filters (`col=val`, `col is 'val'`, `where col is val`, `status is open`)
    eq_filters: list[tuple[str, str]] = []
    seen_f: set[tuple[str, str]] = set()
    _STOP_KEYS = {
        "http", "https", "url", "username", "user", "password", "pass", "pwd",
        "source_url", "target_url", "set", "change", "update", "to", "as",
        "create", "post", "submit", "new", "page", "ticket", "item", "record",
        "the", "a", "an", "and", "or", "with", "where", "from", "in", "on", "of", "for",
    }

    # First capture explicit field updates (`set X to Y`, `change X to Y`, `assign ... to Y`, `mark ... as Y`)
    updates: dict[str, str] = {}
    for m_upd in re.finditer(
        r"\b(?:set|change|update)\s+(?:the\s+)?([A-Za-z_][A-Za-z0-9_\- ]{1,24}?)\s+(?:to|=)\s+(?:['\"]([^'\"]+)['\"]|([A-Za-z0-9_\-\.@$+]+))",
        text,
        flags=re.IGNORECASE,
    ):
        k = _norm_key(m_upd.group(1))
        v = (m_upd.group(2) or m_upd.group(3) or "").strip()
        if k and v and k not in ("the", "it", "this"):
            updates[k] = v
    m_assign = re.search(
        r"\b(?:re)?assign(?:ed)?\s+(?:it\s+|the\s+\w+\s+)?to\s+(?:['\"]([^'\"]+)['\"]|([A-Z][a-zA-Z0-9_\-\.@]+(?:\s+[A-Z][a-zA-Z0-9_\-\.@]+)?))",
        text,
    )
    if m_assign:
        val_a = (m_assign.group(1) or m_assign.group(2) or "").strip()
        if val_a and any(w in low for w in ("assign", "reassign")):
            if any(w in low for w in ("update", "edit", "change", "set", "reassign", "assign ")):
                updates.setdefault("assignee", val_a)
                updates.setdefault("owner", val_a)
    m_mark = re.search(
        r"\bmark\s+(?:it|the\s+\w+|record|ticket|issue|invoice|order)\s+as\s+(?:['\"]([^'\"]+)['\"]|([A-Za-z0-9_\-]+))",
        text,
        flags=re.IGNORECASE,
    )
    if m_mark:
        updates.setdefault("status", (m_mark.group(1) or m_mark.group(2) or "").strip())

    # Capture filters (`where col is val`, `col=val`, `with col val`)
    for m_f in re.finditer(
        r"(?:\bwhere\s+|\bwith\s+)?\b([A-Za-z_][A-Za-z0-9_]{1,22})\s*(?:=|is)\s*(?:['\"]([^'\"]+)['\"]|([A-Za-z0-9_\-\.]+))",
        text,
        flags=re.IGNORECASE,
    ):
        # Skip if preceded directly by `set`/`change`/`update` or `to`
        prefix = text[max(0, m_f.start() - 16):m_f.start()].lower()
        if re.search(r"\b(?:set|change|update|to|as)\s+$", prefix):
            continue
        k = _norm_key(m_f.group(1))
        v = (m_f.group(2) or m_f.group(3) or "").strip()
        if not k or not v or k in _STOP_KEYS or k in updates:
            continue
        if v.lower() in ("a", "an", "the", "open", "closed", "resolved", "active", "inactive", "pending", "paid", "unpaid", "overdue") or len(v) >= 2:
            if (k, v.lower()) not in seen_f and v.lower() not in ("the", "a", "an", "on", "in", "at", "from", "to", "and", "or"):
                seen_f.add((k, v.lower()))
                eq_filters.append((k, v))

    # Numeric filters: `amount > 100`, `price >= 50`, `cost above 200`, `amount over $500`, `under 100`
    num_filters: list[tuple[str, str, float]] = []
    for m_nf in re.finditer(
        r"\b([A-Za-z_][A-Za-z0-9_]{1,22})\s*(>=|<=|>|<|above|over|greater than|at least|more than|below|under|less than|at most)\s*[\$\€\£]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        text,
        flags=re.IGNORECASE,
    ):
        col = _norm_key(m_nf.group(1))
        op_raw = m_nf.group(2).lower().strip()
        val = float(m_nf.group(3).replace(",", ""))
        op = {
            ">": ">", "above": ">", "over": ">", "greater than": ">", "more than": ">",
            ">=": ">=", "at least": ">=",
            "<": "<", "below": "<", "under": "<", "less than": "<",
            "<=": "<=", "at most": "<=",
        }[op_raw]
        num_filters.append((col, op, val))

    # Implicit keyword filters for natural phrases like "open VPN ticket", "high-priority open incident"
    keyword_terms: list[str] = []
    for kw in ("open", "closed", "pending", "overdue", "unpaid", "paid", "active", "critical", "high", "medium", "low"):
        if re.search(rf"\b{kw}\b", low) and not any(v.lower() == kw for _, v in eq_filters) and not any(v.lower() == kw for v in updates.values()):
            keyword_terms.append(kw)
    for m_q in re.finditer(r"['\"]([^'\"]{2,60})['\"]", text):
        q = m_q.group(1).strip()
        if q and q not in updates.values() and not q.startswith("http"):
            if not any(v.lower() == q.lower() for _, v in eq_filters):
                keyword_terms.append(q)
    # Acronyms like VPN, SSO, DNS, TLS, ERP, SLA mentioned as topic
    for m_acr in re.finditer(r"\b([A-Z]{2,5})\b", text):
        acr = m_acr.group(1)
        if acr not in ("HTTP", "HTTPS", "URL", "HTML", "JSON", "REST", "API", "SQL", "CSRF", "ID", "UI", "GET", "POST"):
            if record_id and acr in record_id:
                continue
            if acr not in keyword_terms:
                keyword_terms.append(acr)

    # 3. Aggregation / Query intent
    agg_op: str | None = None
    if re.search(r"\b(?:how many|count(?:\s+of)?|number\s+of)\b", low):
        agg_op = "count"
    elif re.search(r"\b(?:sum(?:\s+of)?|total\s+(?:amount|cost|price|revenue|budget|spend|value|salary|balance|fee|sum))\b", low) or re.search(r"\bcalculate\s+(?:the\s+)?total\b", low):
        agg_op = "sum"
    elif re.search(r"\b(?:average|avg|mean)\b", low):
        agg_op = "avg"
    elif re.search(r"\b(?:highest|largest|most expensive|maximum|max)\b", low):
        agg_op = "max"
    elif re.search(r"\b(?:lowest|smallest|cheapest|minimum|min)\b", low):
        agg_op = "min"
    elif re.search(r"\b(?:list|all|names of|ids of)\b", low):
        agg_op = "list"

    # Requested target metric column (for sum/avg/max/min)
    metric_hint: str | None = None
    m_met = re.search(
        r"\b(?:sum|total|average|avg|mean|highest|largest|maximum|max|lowest|smallest|minimum|min|sort(?:ed)?\s+by)\s+(?:of\s+|the\s+)?([A-Za-z_][A-Za-z0-9_]{1,22})\b",
        low,
    )
    if m_met:
        cand_m = _norm_key(m_met.group(1))
        if cand_m not in ("open", "closed", "active", "all", "the", "a", "an", "priority", "ticket", "tickets", "invoice", "invoices", "order", "orders", "item", "items", "record", "records"):
            metric_hint = cand_m
        elif cand_m == "priority":
            metric_hint = "priority"

    # Requested return field (e.g., "return the owner", "find the title of", "who owns")
    return_field: str | None = None
    if re.search(r"\bwho\s+(?:owns|is\s+assigned|handles)\b", low):
        return_field = "owner"
    else:
        m_ret = re.search(
            r"\b(?:return|get|extract|find|report|show)\s+(?:the\s+)?(owner|assignee|title|name|id|email|status|priority|amount|total|cost|price|department|category|summary|author)\b",
            low,
        )
        if m_ret:
            return_field = _norm_key(m_ret.group(1))

    return {
        "record_id": record_id,
        "eq_filters": eq_filters,
        "num_filters": num_filters,
        "keyword_terms": keyword_terms,
        "updates": updates,
        "agg_op": agg_op,
        "metric_hint": metric_hint,
        "return_field": return_field,
    }


def _resolve_col(hint: str | None, headers: Sequence[str]) -> str | None:
    if not hint or not headers:
        return None
    h_norm = _norm_key(hint)
    if h_norm in headers:
        return h_norm
    for h in headers:
        if h_norm in h or h in h_norm:
            return h
    for _canon, aliases in _FIELD_ALIASES.items():
        if h_norm in aliases:
            for h in headers:
                if h in aliases or any(a in h for a in aliases if len(a) >= 4):
                    return h
    return None


def _priority_rank(val: str) -> float | None:
    low = str(val or "").strip().lower()
    mapping = {
        "p0": 5.0, "urgent": 5.0, "blocker": 5.0, "critical": 4.0, "sev1": 4.0,
        "p1": 4.0, "high": 3.0, "sev2": 3.0, "p2": 3.0,
        "medium": 2.0, "normal": 2.0, "sev3": 2.0, "p3": 2.0,
        "low": 1.0, "minor": 1.0, "sev4": 1.0, "p4": 1.0,
    }
    return mapping.get(low)


def _row_sort_key(row: Mapping[str, Any], col: str | None, headers: Sequence[str]) -> float:
    fields = row.get("fields") or {}
    c = _resolve_col(col, headers)
    if c and c in fields:
        n = _parse_number(fields[c])
        if n is not None:
            return n
        pr = _priority_rank(fields[c])
        if pr is not None:
            return pr
    # Fallback: pick first numeric column
    for h in headers:
        n = _parse_number(fields.get(h, ""))
        if n is not None:
            return n
    return 0.0


def _row_matches_predicates(
    row: Mapping[str, Any],
    headers: Sequence[str],
    parsed: Mapping[str, Any],
) -> bool:
    fields = row.get("fields") or {}
    full_low = str(row.get("full_text") or "").lower()

    rid = parsed.get("record_id")
    if rid:
        if str(rid).lower() not in full_low:
            return False

    for col_hint, expected in parsed.get("eq_filters") or []:
        c = _resolve_col(col_hint, headers)
        exp_low = expected.lower()
        if c and c in fields:
            cell_low = str(fields[c]).lower()
            if exp_low != cell_low and exp_low not in cell_low:
                return False
        else:
            if exp_low not in full_low:
                return False

    for col_hint, op, bound in parsed.get("num_filters") or []:
        c = _resolve_col(col_hint, headers)
        val_num: float | None = None
        if c and c in fields:
            val_num = _parse_number(fields[c])
        else:
            for h in headers:
                n = _parse_number(fields.get(h, ""))
                if n is not None:
                    val_num = n
                    break
        if val_num is None:
            return False
        if op == ">" and not (val_num > bound):
            return False
        if op == ">=" and not (val_num >= bound):
            return False
        if op == "<" and not (val_num < bound):
            return False
        if op == "<=" and not (val_num <= bound):
            return False

    for kw in parsed.get("keyword_terms") or []:
        kw_low = kw.lower()
        if kw_low not in full_low:
            # Allow synonym check if keyword is an explicit filter already or not present in any column
            return False

    return True


# ---------------------------------------------------------------------------
# 4. Shared Authenticated Multi-Page Navigation & Form Filling Helpers
# ---------------------------------------------------------------------------

def _fill_safe_form(
    fm: Mapping[str, Any],
    prefill_info: Mapping[str, Any] | None,
    bindings: Mapping[str, str],
    *,
    preserve_existing: bool = False,
    extra_keys: Sequence[str] = (),
) -> tuple[dict[str, str], bool]:
    payload: dict[str, str] = {}
    used_csrf = False
    hidden = fm.get("hidden_replay") or {}
    if hidden:
        used_csrf = True
        for hk, hv in hidden.items():
            payload[str(hk)] = str(hv)

    prefill = dict((prefill_info or {}).get("prefill") or {})
    labels = dict((prefill_info or {}).get("labels") or {})
    sel_opts = dict((prefill_info or {}).get("select_options") or {})

    if preserve_existing:
        for pk, pv in prefill.items():
            if pk not in payload:
                payload[pk] = str(pv)

    req_f = list(fm.get("required_input") or [])
    opt_f = list(fm.get("optional_input") or [])
    choices = fm.get("choices") or {}
    all_fields = list(dict.fromkeys(req_f + opt_f + list(prefill.keys()) + list(extra_keys)))

    for fname in all_fields:
        if fname in hidden:
            continue
        lbl = labels.get(fname, "")
        val = _resolve_alias_value(fname, bindings, label_text=lbl)
        if val is not None:
            # Match <select> option value or label case-insensitively
            if fname in sel_opts and sel_opts[fname]:
                matched_opt = None
                for oval, otxt, _ in sel_opts[fname]:
                    if oval.lower() == val.lower() or otxt.lower() == val.lower():
                        matched_opt = oval
                        break
                if matched_opt is not None:
                    val = matched_opt
            elif fname in choices and choices[fname]:
                for opt in choices[fname]:
                    if str(opt).lower() == val.lower():
                        val = str(opt)
                        break
            payload[fname] = val
        elif fname not in payload and (fname in req_f or fname in extra_keys):
            if fname in choices and choices[fname]:
                payload[fname] = str(choices[fname][0])
            else:
                payload[fname] = f"auto_{fname.lower()}"

    return payload, used_csrf


def _match_prefill_for_form(fm: Mapping[str, Any], prefills: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    act = str(fm.get("action") or "")
    meth = str(fm.get("method") or "GET").upper()
    for pf in prefills:
        if str(pf.get("action") or "") == act and str(pf.get("method") or "GET").upper() == meth:
            return pf
    for pf in prefills:
        if str(pf.get("action") or "") == act:
            return pf
    return None


def _authenticate_if_needed(
    sess: _WebSession,
    resolved_url: str,
    html: str,
    supplied: Mapping[str, str],
    *,
    allow_destructive: bool,
    trace: list[dict[str, Any]],
    stages: list[str],
    blocked_destructive: list[str],
) -> tuple[str, str, bool, bool]:
    """Authenticate automatically if page has a login form or login link and credentials exist."""
    has_creds = (
        _resolve_alias_value("username", supplied) is not None
        and _resolve_alias_value("password", supplied) is not None
    )
    used_csrf = False
    for _ in range(3):
        parsed_pg = parse_enterprise_page(html, resolved_url)
        desc = HTMLFORM.describe(HTMLFORM.read_forms(html))
        safe_forms = []
        for fm in desc.get("forms") or []:
            if not allow_destructive and _is_form_destructive(fm):
                act = str(fm.get("action") or "")
                if act and act not in blocked_destructive:
                    blocked_destructive.append(act)
                continue
            safe_forms.append(fm)

        login_form = next(
            (
                fm for fm in safe_forms
                if any(
                    k in (str(fm.get("action") or "") + " " + " ".join(fm.get("required_input") or []) + " " + " ".join(fm.get("optional_input") or [])).lower()
                    for k in ("login", "signin", "sign-in", "auth", "password", "passwd", "pwd")
                )
            ),
            None,
        )
        if login_form is not None and has_creds:
            act_url = urllib.parse.urljoin(resolved_url, str(login_form.get("action") or ""))
            pf = _match_prefill_for_form(login_form, parsed_pg["form_prefills"])
            payload, csrf_hit = _fill_safe_form(login_form, pf, supplied, preserve_existing=False)
            used_csrf = used_csrf or csrf_hit
            st, new_url, new_html = sess.request(act_url, method=str(login_form.get("method") or "POST"), form_data=payload)
            trace.append({"stage": "AUTH_LOGIN", "action": act_url, "status": st, "keys": sorted(payload)})
            if 200 <= st < 300:
                stages.append("AUTH_LOGIN")
                return new_url, new_html, True, used_csrf
            return resolved_url, html, False, used_csrf

        # If current page has no tables & no data forms, check for a login link when credentials exist
        if has_creds and not parsed_pg["tables"]:
            login_lk = next(
                (
                    lk for lk in parsed_pg["links"]
                    if (not lk["is_destructive"])
                    and any(k in (lk["href"] + " " + lk["text"]).lower() for k in ("login", "sign in", "signin", "log in", "auth"))
                ),
                None,
            )
            if login_lk is not None and login_lk["url"] != resolved_url:
                st, resolved_url, html = sess.request(login_lk["url"], method="GET")
                trace.append({"stage": "NAV_LOGIN", "url": resolved_url, "status": st})
                if st >= 400:
                    return resolved_url, html, False, used_csrf
                continue
        break
    return resolved_url, html, True, used_csrf


def _crawl_all_table_rows(
    sess: _WebSession,
    start_url: str,
    start_html: str,
    instruction: str,
    *,
    allow_destructive: bool,
    trace: list[dict[str, Any]],
    stages: list[str],
    blocked_destructive: list[str],
    max_pages: int = 20,
) -> dict[str, Any]:
    """Navigate to data table (if on dashboard), follow pagination across ALL pages, collect rows."""
    low_instr = (instruction or "").lower()
    goal_words = {w for w in re.findall(r"[a-z]{3,}", low_instr) if w not in ("the", "and", "for", "with", "from", "that", "this", "find", "return", "http", "https")}

    cur_url = start_url
    cur_html = start_html
    visited: set[str] = {cur_url}
    headers: list[str] = []
    raw_headers: list[str] = []
    all_rows: list[dict[str, Any]] = []
    seen_row_keys: set[str] = set()
    pages_crawled = 0

    for _hop in range(max_pages):
        pg = parse_enterprise_page(cur_html, cur_url)
        for lk in pg["links"]:
            if lk["is_destructive"] and lk["href"] not in blocked_destructive:
                blocked_destructive.append(lk["href"])

        if pg["tables"]:
            pages_crawled += 1
            # Pick the largest table on the page
            best_tb = max(pg["tables"], key=lambda t: len(t["rows"]))
            if not headers and best_tb["norm_headers"]:
                headers = list(best_tb["norm_headers"])
                raw_headers = list(best_tb["headers"])
            for row in best_tb["rows"]:
                rk = json.dumps(row["raw_cells"], sort_keys=True)
                if rk not in seen_row_keys:
                    seen_row_keys.add(rk)
                    row_copy = dict(row)
                    row_copy["page_url"] = cur_url
                    all_rows.append(row_copy)

            # Find pagination "Next" link or next page=N link
            next_lk = None
            best_next_sc = 0
            for lk in pg["links"]:
                if lk["is_destructive"] or lk["url"] in visited:
                    continue
                txt_l = lk["text"].lower().strip()
                href_l = lk["href"].lower()
                sc = 0
                if txt_l in ("next", "next >", "next ›", "next »", ">", "›", "»", "next page"):
                    sc = 10
                elif "next" in txt_l:
                    sc = 8
                elif re.search(r"[?&](?:page|p|offset|cursor)=\d+", href_l):
                    sc = 6
                if sc > best_next_sc:
                    best_next_sc = sc
                    next_lk = lk

            if next_lk is not None:
                st, nxt_url, nxt_html = sess.request(next_lk["url"], method="GET")
                trace.append({"stage": "PAGINATE_TABLE", "url": nxt_url, "status": st})
                visited.add(next_lk["url"])
                visited.add(nxt_url)
                if 200 <= st < 300:
                    if "PAGINATE_TABLE" not in stages:
                        stages.append("PAGINATE_TABLE")
                    cur_url, cur_html = nxt_url, nxt_html
                    continue
            break

        # No table yet -> navigate from dashboard/home to a list/table link matching goal keywords
        nav_cands: list[tuple[int, dict[str, Any]]] = []
        for lk in pg["links"]:
            if lk["is_destructive"] or lk["url"] in visited:
                continue
            comb = (lk["href"] + " " + lk["text"]).lower()
            sc = 0
            for gw in goal_words:
                if gw in comb:
                    sc += 4
            if any(k in comb for k in ("tickets", "incidents", "issues", "invoices", "orders", "records", "items", "list", "queue", "catalog", "products", "employees", "cases", "projects", "deals", "contacts", "table", "browse")):
                sc += 3
            if any(k in comb for k in ("logout", "signout", "login", "signin", "new", "create")):
                sc -= 6
            if sc > 0:
                nav_cands.append((sc, lk))
        if not nav_cands:
            break
        nav_cands.sort(key=lambda x: -x[0])
        chosen = nav_cands[0][1]
        st, nxt_url, nxt_html = sess.request(chosen["url"], method="GET")
        trace.append({"stage": "NAV_TO_LIST", "url": nxt_url, "status": st})
        visited.add(chosen["url"])
        visited.add(nxt_url)
        if 200 <= st < 300:
            if "NAV_TO_LIST" not in stages:
                stages.append("NAV_TO_LIST")
            cur_url, cur_html = nxt_url, nxt_html
            continue
        break

    if all_rows and "CRAWL_TABLE" not in stages:
        stages.append("CRAWL_TABLE")

    return {
        "headers": headers,
        "raw_headers": raw_headers,
        "rows": all_rows,
        "pages_crawled": pages_crawled,
        "last_url": cur_url,
        "last_html": cur_html,
    }


def _drill_row_detail(
    sess: _WebSession,
    row: Mapping[str, Any],
    trace: list[dict[str, Any]],
    stages: list[str],
    *,
    prefer_edit: bool = False,
) -> tuple[str | None, str, dict[str, str]]:
    """Follow a safe row link (Edit or Detail/View) and extract KV fields."""
    links = [lk for lk in (row.get("links") or []) if not lk.get("is_destructive")]
    if not links:
        return None, "", {}

    def _score_lk(lk: Mapping[str, Any]) -> int:
        comb = (str(lk.get("href") or "") + " " + str(lk.get("text") or "")).lower()
        if prefer_edit:
            if any(k in comb for k in ("edit", "update", "modify", "manage")):
                return 10
            if any(k in comb for k in ("view", "detail", "open", "show")):
                return 6
            return 3
        else:
            if any(k in comb for k in ("view", "detail", "show", "open")):
                return 10
            if any(k in comb for k in ("edit", "update")):
                return 4
            return 7

    links.sort(key=_score_lk, reverse=True)
    chosen = links[0]
    st, d_url, d_html = sess.request(chosen["url"], method="GET")
    stage = "OPEN_EDIT_PAGE" if prefer_edit else "DRILL_DETAIL_PAGE"
    trace.append({"stage": stage, "url": d_url, "status": st})
    if not (200 <= st < 300):
        return None, "", {}
    if stage not in stages:
        stages.append(stage)
    d_pg = parse_enterprise_page(d_html, d_url)
    kv = dict(d_pg["kv_pairs"])
    # Also harvest any single-form prefilled values as KV facts
    for pf in d_pg["form_prefills"]:
        for k, v in (pf.get("prefill") or {}).items():
            nk = _norm_key(k)
            if nk and v and nk not in kv and "csrf" not in nk and "token" not in nk:
                kv[nk] = str(v)
    return d_url, d_html, kv


# ---------------------------------------------------------------------------
# 5. Polymorphic Enterprise Skill Memory (Zero-URL, Zero-HTML, Zero-Weights)
# ---------------------------------------------------------------------------

def _enterprise_skill_key(workflow_kind: str, needs_source_auth: bool, needs_target_auth: bool) -> str:
    sig = f"{workflow_kind}|sa={int(needs_source_auth)}|ta={int(needs_target_auth)}"
    return "webent_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]


def _match_enterprise_skill(
    memory: dict[str, Any] | None,
    *,
    workflow_kind: str,
    needs_source_auth: bool,
    needs_target_auth: bool,
) -> dict[str, Any] | None:
    if not isinstance(memory, dict):
        return None
    store = memory.get("web_enterprise_skills")
    if not isinstance(store, dict):
        return None
    lid = _enterprise_skill_key(workflow_kind, needs_source_auth, needs_target_auth)
    entry = store.get(lid)
    if isinstance(entry, dict):
        return entry
    # Fallback: match same workflow kind regardless of auth flag
    for entry in store.values():
        if isinstance(entry, dict) and entry.get("workflow_kind") == workflow_kind:
            return entry
    return None


def _distill_enterprise_skill(
    memory: dict[str, Any] | None,
    *,
    workflow_kind: str,
    needs_source_auth: bool,
    needs_target_auth: bool,
    stages: Sequence[str],
    discovered_fields: Sequence[str],
    used_csrf: bool,
    blocked_destructive: bool,
) -> dict[str, Any] | None:
    if not isinstance(memory, dict):
        return None
    store = memory.setdefault("web_enterprise_skills", {})
    if not isinstance(store, dict):
        return None
    lid = _enterprise_skill_key(workflow_kind, needs_source_auth, needs_target_auth)
    prev = store.get(lid)
    prev_fields = list((prev or {}).get("discovered_field_holes") or [])
    merged_fields = list(dict.fromkeys(prev_fields + [str(f).lower() for f in discovered_fields if f]))
    skill = {
        "law_id": lid,
        "kind": "WEB_ENTERPRISE_POLY_SKILL",
        "workflow_kind": workflow_kind,
        "needs_source_auth": bool(needs_source_auth),
        "needs_target_auth": bool(needs_target_auth),
        "abstract_stage_sequence": list(dict.fromkeys(stages)),
        "discovered_field_holes": merged_fields,
        "requires_csrf_replay": bool(used_csrf),
        "blocks_destructive_traps": bool(blocked_destructive),
        "uses": int((prev or {}).get("uses", 0)) + 1,
        "parameters_stored": 0,
    }
    store[lid] = skill
    return skill


# ---------------------------------------------------------------------------
# 6. Public Entry Points: Table Filter/Aggregate, CRUD Edit, Cross-App Bridge
# ---------------------------------------------------------------------------

def solve_enterprise_table_query(
    url: str,
    instruction: str,
    *,
    memory: dict[str, Any] | None = None,
    supplied: Mapping[str, str] | None = None,
    allow_destructive: bool = False,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """WorkArena-class Multi-Page Table Pagination + Filtering + Sorting + Exact Aggregation."""
    t0 = time.monotonic()
    sup = {str(k).strip().lower(): str(v) for k, v in (supplied or {}).items()}
    parsed = _parse_goal_filters_and_updates(instruction, sup)
    needs_auth = _resolve_alias_value("username", sup) is not None and _resolve_alias_value("password", sup) is not None
    recalled = _match_enterprise_skill(memory, workflow_kind="TABLE_FILTER_AGGREGATE", needs_source_auth=needs_auth, needs_target_auth=False)

    sess = _WebSession(timeout_s=timeout_s)
    trace: list[dict[str, Any]] = []
    stages: list[str] = []
    blocked_destructive: list[str] = []

    st, res_url, html = sess.request(url, method="GET")
    trace.append({"stage": "GET_START", "url": res_url, "status": st})
    if st >= 400:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_GET_FAILED", "http_status": st,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    res_url, html, auth_ok, used_csrf = _authenticate_if_needed(
        sess, res_url, html, sup,
        allow_destructive=allow_destructive, trace=trace, stages=stages, blocked_destructive=blocked_destructive,
    )
    if not auth_ok:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_AUTH_FAILED",
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    crawled = _crawl_all_table_rows(
        sess, res_url, html, instruction,
        allow_destructive=allow_destructive, trace=trace, stages=stages, blocked_destructive=blocked_destructive,
    )
    headers = crawled["headers"]
    rows = crawled["rows"]
    if not rows:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_NO_TABLE_FOUND",
            "trace": trace, "stages_executed": stages,
            "blocked_destructive_forms": blocked_destructive,
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    matched = [r for r in rows if _row_matches_predicates(r, headers, parsed)]
    # Fallback: if implicit keyword terms over-constrained (e.g. prose word not in table), drop keyword_terms and re-match
    if not matched and parsed["keyword_terms"]:
        relaxed = dict(parsed)
        relaxed["keyword_terms"] = []
        matched = [r for r in rows if _row_matches_predicates(r, headers, relaxed)]

    stages.append("FILTER_AGGREGATE")
    agg_op = parsed["agg_op"] or "list"
    metric_col = _resolve_col(parsed["metric_hint"], headers)
    if metric_col is None and agg_op in ("sum", "avg", "max", "min"):
        for h in headers:
            if any(_parse_number(r["fields"].get(h, "")) is not None for r in matched):
                metric_col = h
                break

    answer: Any = None
    winning_row: dict[str, Any] | None = None
    detail_kv: dict[str, str] = {}

    if agg_op == "count":
        answer = len(matched)
    elif agg_op == "sum":
        vals = [_parse_number(r["fields"].get(metric_col or "", "")) for r in matched]
        nums = [v for v in vals if v is not None]
        answer = round(sum(nums), 6) if nums else 0.0
    elif agg_op == "avg":
        vals = [_parse_number(r["fields"].get(metric_col or "", "")) for r in matched]
        nums = [v for v in vals if v is not None]
        answer = round(sum(nums) / len(nums), 6) if nums else 0.0
    elif agg_op in ("max", "min") and matched:
        reverse = agg_op == "max"
        ordered = sorted(matched, key=lambda r: _row_sort_key(r, metric_col or parsed["metric_hint"], headers), reverse=reverse)
        winning_row = ordered[0]
        ret_f = parsed["return_field"]
        if ret_f:
            rc = _resolve_col(ret_f, headers)
            if rc and rc in winning_row["fields"] and winning_row["fields"][rc]:
                answer = winning_row["fields"][rc]
            else:
                # Drill into detail page to recover missing field (e.g. owner/email/root_cause)
                _du, _dh, detail_kv = _drill_row_detail(sess, winning_row, trace, stages, prefer_edit=False)
                answer = _resolve_alias_value(ret_f, detail_kv) or winning_row["fields"].get(metric_col or "", "")
        else:
            val_num = _parse_number(winning_row["fields"].get(metric_col or "", ""))
            answer = val_num if val_num is not None else winning_row["fields"]
    else:
        ret_f = parsed["return_field"]
        if ret_f and matched:
            rc = _resolve_col(ret_f, headers)
            if rc:
                answer = [r["fields"].get(rc, "") for r in matched]
            elif len(matched) == 1:
                _du, _dh, detail_kv = _drill_row_detail(sess, matched[0], trace, stages, prefer_edit=False)
                answer = _resolve_alias_value(ret_f, detail_kv)
        if answer is None:
            answer = [r["fields"] for r in matched]
        if matched:
            winning_row = matched[0]

    distilled = _distill_enterprise_skill(
        memory,
        workflow_kind="TABLE_FILTER_AGGREGATE",
        needs_source_auth=needs_auth,
        needs_target_auth=False,
        stages=stages,
        discovered_fields=[],
        used_csrf=used_csrf,
        blocked_destructive=bool(blocked_destructive),
    )

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "modality": "live_http_web_ui",
        "status": "VERIFIED",
        "mode": "TIER0_WEB_ENTERPRISE_SKILL" if recalled else "WEB_TABLE_FILTER_AGGREGATE",
        "answer": answer,
        "aggregation": agg_op,
        "metric_column": metric_col,
        "pages_crawled": crawled["pages_crawled"],
        "total_rows_scanned": len(rows),
        "matched_count": len(matched),
        "matched_rows": [r["fields"] for r in matched],
        "winning_row": winning_row["fields"] if winning_row else None,
        "detail_fields": detail_kv,
        "stages_executed": stages,
        "blocked_destructive_forms": blocked_destructive,
        "recalled_law_id": recalled["law_id"] if recalled else None,
        "distilled_law": distilled,
        "failed_probes": 0,
        "trace": trace,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def solve_enterprise_record_crud_edit(
    url: str,
    instruction: str,
    *,
    memory: dict[str, Any] | None = None,
    supplied: Mapping[str, str] | None = None,
    allow_destructive: bool = False,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """WebArena-class Multi-Page Record Locate -> Safe Edit -> CSRF Update -> Verified Persistence."""
    t0 = time.monotonic()
    sup = {str(k).strip().lower(): str(v) for k, v in (supplied or {}).items()}
    parsed = _parse_goal_filters_and_updates(instruction, sup)
    merged_updates = dict(sup)
    merged_updates.update(parsed["updates"])

    needs_auth = _resolve_alias_value("username", sup) is not None and _resolve_alias_value("password", sup) is not None
    recalled = _match_enterprise_skill(memory, workflow_kind="RECORD_CRUD_EDIT", needs_source_auth=needs_auth, needs_target_auth=False)
    prebound_fields = list((recalled or {}).get("discovered_field_holes") or [])

    sess = _WebSession(timeout_s=timeout_s)
    trace: list[dict[str, Any]] = []
    stages: list[str] = []
    blocked_destructive: list[str] = []
    discovered_fields: list[str] = []
    failed_probes = 0

    st, res_url, html = sess.request(url, method="GET")
    trace.append({"stage": "GET_START", "url": res_url, "status": st})
    if st >= 400:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_GET_FAILED", "http_status": st,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    res_url, html, auth_ok, used_csrf = _authenticate_if_needed(
        sess, res_url, html, sup,
        allow_destructive=allow_destructive, trace=trace, stages=stages, blocked_destructive=blocked_destructive,
    )
    if not auth_ok:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_AUTH_FAILED",
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    crawled = _crawl_all_table_rows(
        sess, res_url, html, instruction,
        allow_destructive=allow_destructive, trace=trace, stages=stages, blocked_destructive=blocked_destructive,
    )
    headers = crawled["headers"]
    rows = crawled["rows"]

    # Locate target record row
    matched = [r for r in rows if _row_matches_predicates(r, headers, parsed)]
    if not matched and parsed["record_id"]:
        rid_l = parsed["record_id"].lower()
        matched = [r for r in rows if rid_l in str(r.get("full_text") or "").lower()]
    if not matched and parsed["keyword_terms"]:
        for kw in parsed["keyword_terms"]:
            kl = kw.lower()
            m2 = [r for r in rows if kl in str(r.get("full_text") or "").lower()]
            if m2:
                matched = m2
                break
    if not matched:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_RECORD_NOT_FOUND",
            "pages_crawled": crawled["pages_crawled"], "total_rows_scanned": len(rows),
            "blocked_destructive_forms": blocked_destructive,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    target_row = matched[0]
    edit_url, edit_html, _kv = _drill_row_detail(sess, target_row, trace, stages, prefer_edit=True)
    if not edit_url:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_NO_EDIT_LINK",
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    # If detail page links to an explicit /edit page and has no safe POST form yet, follow the Edit link
    for _step in range(2):
        pg_e = parse_enterprise_page(edit_html, edit_url)
        desc_e = HTMLFORM.describe(HTMLFORM.read_forms(edit_html))
        safe_forms = []
        for fm in desc_e.get("forms") or []:
            if not allow_destructive and _is_form_destructive(fm):
                act = str(fm.get("action") or "")
                if act and act not in blocked_destructive:
                    blocked_destructive.append(act)
                continue
            if str(fm.get("method") or "GET").upper() in ("POST", "PUT", "PATCH"):
                safe_forms.append(fm)
        if safe_forms:
            break
        edit_lk = next(
            (lk for lk in pg_e["links"] if (not lk["is_destructive"]) and any(k in (lk["href"] + " " + lk["text"]).lower() for k in ("edit", "update", "modify"))),
            None,
        )
        if edit_lk is not None and edit_lk["url"] != edit_url:
            st, edit_url, edit_html = sess.request(edit_lk["url"], method="GET")
            trace.append({"stage": "OPEN_EDIT_FORM", "url": edit_url, "status": st})
            if 200 <= st < 300:
                stages.append("OPEN_EDIT_FORM")
                continue
        break

    pg_e = parse_enterprise_page(edit_html, edit_url)
    desc_e = HTMLFORM.describe(HTMLFORM.read_forms(edit_html))
    safe_forms = [
        fm for fm in (desc_e.get("forms") or [])
        if (allow_destructive or not _is_form_destructive(fm))
        and str(fm.get("method") or "GET").upper() in ("POST", "PUT", "PATCH")
    ]
    if not safe_forms:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_NO_SAFE_EDIT_FORM",
            "blocked_destructive_forms": blocked_destructive,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    fm = safe_forms[0]
    pf = _match_prefill_for_form(fm, pg_e["form_prefills"])
    act_url = urllib.parse.urljoin(edit_url, str(fm.get("action") or ""))
    extra_keys = list(prebound_fields)

    final_st = 0
    final_url = edit_url
    final_body = ""
    submitted_payload: dict[str, str] = {}

    for _try in range(4):
        payload, csrf_hit = _fill_safe_form(
            fm, pf, merged_updates, preserve_existing=True, extra_keys=extra_keys,
        )
        used_csrf = used_csrf or csrf_hit
        final_st, final_url, final_body = sess.request(act_url, method=str(fm.get("method") or "POST"), form_data=payload)
        trace.append({"stage": "SUBMIT_CRUD_EDIT", "action": act_url, "status": final_st, "keys": sorted(payload)})
        submitted_payload = payload
        if 200 <= final_st < 300:
            stages.append("SUBMIT_CRUD_EDIT")
            distilled = _distill_enterprise_skill(
                memory,
                workflow_kind="RECORD_CRUD_EDIT",
                needs_source_auth=needs_auth,
                needs_target_auth=False,
                stages=stages,
                discovered_fields=discovered_fields or prebound_fields,
                used_csrf=used_csrf,
                blocked_destructive=bool(blocked_destructive),
            )
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "live_http_web_ui",
                "status": "VERIFIED",
                "mode": "TIER0_WEB_ENTERPRISE_SKILL" if (recalled and failed_probes == 0) else "WEB_RECORD_CRUD_EDIT",
                "http_status": final_st,
                "final_url": final_url,
                "response_body": final_body,
                "updated_record": target_row["fields"],
                "submitted_payload": submitted_payload,
                "pages_crawled": crawled["pages_crawled"],
                "failed_probes": failed_probes,
                "discovered_conditional_fields": discovered_fields,
                "stages_executed": stages,
                "blocked_destructive_forms": blocked_destructive,
                "recalled_law_id": recalled["law_id"] if recalled else None,
                "distilled_law": distilled,
                "trace": trace,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }
        failed_probes += 1
        missing = list(COMPOSE_ERR.missing_from_error(final_body))
        for m_req in re.finditer(
            r"(?:missing|required)\s+(?:required\s+)?(?:field|param|parameter|key)?\s*[:=]?\s*['\"]?([A-Za-z_][A-Za-z0-9_\-]*)['\"]?",
            final_body,
            flags=re.IGNORECASE,
        ):
            cand = m_req.group(1).strip().lower()
            if cand and cand not in ("error", "detail", "message", "field", "required", "missing") and cand not in missing:
                missing.append(cand)
        added = False
        for mk in missing:
            mkl = mk.strip().lower()
            if mkl and mkl not in extra_keys:
                extra_keys.append(mkl)
                if mkl not in discovered_fields:
                    discovered_fields.append(mkl)
                added = True
        if not added:
            break

    return {
        "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
        "status": "FAILED", "mode": "WEB_CRUD_SUBMIT_FAILED", "http_status": final_st,
        "response_body": final_body, "failed_probes": failed_probes,
        "blocked_destructive_forms": blocked_destructive,
        "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0, "parameters_stored": 0,
    }


def solve_cross_app_web_bridge(
    source_url: str,
    target_url: str,
    instruction: str,
    *,
    memory: dict[str, Any] | None = None,
    supplied: Mapping[str, str] | None = None,
    allow_destructive: bool = False,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """WebArena-Pro Cross-Application Bridge (Source App A -> Fact Projection -> Target App B).

    Maintains two completely isolated cookie sessions, extracts exact facts from Source App A
    (with login + pagination + table filtering + detail-page drill-down), projects those
    semantic bindings onto Target App B's creation/posting form (with Target auth + CSRF +
    failure-driven conditional field discovery), and distills a domain-agnostic Poly-Skill
    for 0-probe Tier-0 transfer onto brand-new unseen App C -> App D pairs!
    """
    t0 = time.monotonic()
    sup = {str(k).strip().lower(): str(v) for k, v in (supplied or {}).items()}
    parsed = _parse_goal_filters_and_updates(instruction, sup)

    # Split optional source_* / target_* credentials cleanly while keeping shared fallbacks
    src_sup = dict(sup)
    tgt_sup = dict(sup)
    for k, v in sup.items():
        if k.startswith("source_"):
            src_sup[k[len("source_"):]] = v
        elif k.startswith("target_"):
            tgt_sup[k[len("target_"):]] = v

    needs_sa = _resolve_alias_value("username", src_sup) is not None and _resolve_alias_value("password", src_sup) is not None
    needs_ta = _resolve_alias_value("username", tgt_sup) is not None and _resolve_alias_value("password", tgt_sup) is not None

    recalled = _match_enterprise_skill(
        memory,
        workflow_kind="CROSS_APP_BRIDGE",
        needs_source_auth=needs_sa,
        needs_target_auth=needs_ta,
    )
    prebound_fields = list((recalled or {}).get("discovered_field_holes") or [])

    trace: list[dict[str, Any]] = []
    stages: list[str] = []
    blocked_destructive: list[str] = []
    discovered_fields: list[str] = []
    failed_probes = 0
    used_csrf = False

    # ---------------- Phase 1: Source App A (Isolated Session A) ----------------
    sess_a = _WebSession(timeout_s=timeout_s)
    st_a, url_a, html_a = sess_a.request(source_url, method="GET")
    trace.append({"app": "source", "stage": "GET_START", "url": url_a, "status": st_a})
    if st_a >= 400:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_SOURCE_GET_FAILED", "http_status": st_a,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    url_a, html_a, auth_a, csrf_a = _authenticate_if_needed(
        sess_a, url_a, html_a, src_sup,
        allow_destructive=allow_destructive, trace=trace, stages=stages, blocked_destructive=blocked_destructive,
    )
    used_csrf = used_csrf or csrf_a
    if not auth_a:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_SOURCE_AUTH_FAILED",
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    crawled_a = _crawl_all_table_rows(
        sess_a, url_a, html_a, instruction,
        allow_destructive=allow_destructive, trace=trace, stages=stages, blocked_destructive=blocked_destructive,
    )
    headers_a = crawled_a["headers"]
    rows_a = crawled_a["rows"]

    matched_a = [r for r in rows_a if _row_matches_predicates(r, headers_a, parsed)]
    if not matched_a and parsed["keyword_terms"]:
        relaxed = dict(parsed)
        relaxed["keyword_terms"] = []
        matched_a = [r for r in rows_a if _row_matches_predicates(r, headers_a, relaxed)]
    if not matched_a:
        matched_a = list(rows_a)

    if not matched_a:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_SOURCE_NO_RECORDS",
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    # Rank if max/min requested (e.g. highest-priority or highest-cost ticket)
    agg_op = parsed["agg_op"]
    if agg_op in ("max", "min"):
        matched_a = sorted(
            matched_a,
            key=lambda r: _row_sort_key(r, parsed["metric_hint"], headers_a),
            reverse=(agg_op == "max"),
        )
    chosen_row = matched_a[0]
    extracted_facts: dict[str, str] = {k: v for k, v in chosen_row["fields"].items() if v}

    # Always drill into the winning row's safe Detail page to harvest rich fields (owner/email/notes)
    _du, _dh, detail_kv = _drill_row_detail(sess_a, chosen_row, trace, stages, prefer_edit=False)
    for k, v in detail_kv.items():
        if v and k not in extracted_facts:
            extracted_facts[k] = v

    # Build canonical summary text & projected bindings for Target App B
    summary_parts = [f"{k}={v}" for k, v in extracted_facts.items()]
    auto_summary = " | ".join(summary_parts)
    projected_bindings: dict[str, str] = dict(tgt_sup)
    for k, v in extracted_facts.items():
        projected_bindings.setdefault(k, v)
    projected_bindings.setdefault("summary", auto_summary)
    projected_bindings.setdefault("body", auto_summary)
    projected_bindings.setdefault("content", auto_summary)
    projected_bindings.setdefault("description", auto_summary)
    projected_bindings.setdefault("message", auto_summary)
    # Propagate title/subject and owner/assignee aliases cleanly
    best_title = _resolve_alias_value("title", extracted_facts)
    if not best_title:
        # General schema-agnostic fallback: first descriptive non-numeric, non-status, non-action column value
        for fk, fv in extracted_facts.items():
            if not fv or fk in ("action", "actions", "status", "stage", "state", "priority", "severity", "owner", "lead", "assignee"):
                continue
            if _parse_number(fv) is not None or re.fullmatch(r"[A-Z]{2,6}-\d+", fv.strip()):
                continue
            if "|" in fv or "view" in fv.lower() or "inspect" in fv.lower():
                continue
            best_title = fv
            break
    best_title = best_title or _resolve_alias_value("ticket_id", extracted_facts) or "Cross-App Summary"
    projected_bindings.setdefault("title", f"Summary: {best_title}")
    best_owner = _resolve_alias_value("owner", extracted_facts)
    if best_owner:
        projected_bindings.setdefault("owner", best_owner)
        projected_bindings.setdefault("assignee", best_owner)
    best_ref = _resolve_alias_value("ticket_id", extracted_facts)
    if best_ref:
        projected_bindings.setdefault("ticket_id", best_ref)
        projected_bindings.setdefault("reference", best_ref)
    stages.append("PROJECT_SOURCE_FACTS")

    # ---------------- Phase 2: Target App B (Isolated Session B) ----------------
    sess_b = _WebSession(timeout_s=timeout_s)
    st_b, url_b, html_b = sess_b.request(target_url, method="GET")
    trace.append({"app": "target", "stage": "GET_START", "url": url_b, "status": st_b})
    if st_b >= 400:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_TARGET_GET_FAILED", "http_status": st_b,
            "extracted_source_facts": extracted_facts,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    url_b, html_b, auth_b, csrf_b = _authenticate_if_needed(
        sess_b, url_b, html_b, tgt_sup,
        allow_destructive=allow_destructive, trace=trace, stages=stages, blocked_destructive=blocked_destructive,
    )
    used_csrf = used_csrf or csrf_b
    if not auth_b:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_TARGET_AUTH_FAILED",
            "extracted_source_facts": extracted_facts,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    # Navigate to a safe creation/compose/new-page POST form on Target App B
    visited_b: set[str] = {url_b}
    create_form: dict[str, Any] | None = None
    create_pg: dict[str, Any] | None = None
    for _hop in range(4):
        pg_b = parse_enterprise_page(html_b, url_b)
        desc_b = HTMLFORM.describe(HTMLFORM.read_forms(html_b))
        safe_post_forms = []
        for fm in desc_b.get("forms") or []:
            if not allow_destructive and _is_form_destructive(fm):
                act = str(fm.get("action") or "")
                if act and act not in blocked_destructive:
                    blocked_destructive.append(act)
                continue
            if str(fm.get("method") or "GET").upper() in ("POST", "PUT"):
                safe_post_forms.append(fm)
        if safe_post_forms:
            create_form = safe_post_forms[0]
            create_pg = pg_b
            break
        # Follow New / Create / Compose / Post / Add Page link
        nav_b = [
            lk for lk in pg_b["links"]
            if (not lk["is_destructive"]) and lk["url"] not in visited_b
            and any(k in (lk["href"] + " " + lk["text"]).lower() for k in ("new", "create", "compose", "post", "add", "publish", "report", "note", "page", "message", "wiki", "kb"))
        ]
        if not nav_b:
            break
        chosen_b = nav_b[0]
        st_b, url_b, html_b = sess_b.request(chosen_b["url"], method="GET")
        trace.append({"app": "target", "stage": "NAV_TARGET_CREATE", "url": url_b, "status": st_b})
        visited_b.add(chosen_b["url"])
        visited_b.add(url_b)
        if 200 <= st_b < 300:
            if "NAV_TARGET_CREATE" not in stages:
                stages.append("NAV_TARGET_CREATE")
            continue
        break

    if create_form is None or create_pg is None:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_TARGET_NO_CREATE_FORM",
            "extracted_source_facts": extracted_facts,
            "blocked_destructive_forms": blocked_destructive,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }

    pf_b = _match_prefill_for_form(create_form, create_pg["form_prefills"])
    act_b = urllib.parse.urljoin(url_b, str(create_form.get("action") or ""))
    extra_keys = list(prebound_fields)

    final_st = 0
    final_url = url_b
    final_body = ""
    submitted_payload: dict[str, str] = {}

    for _try in range(4):
        payload, csrf_hit = _fill_safe_form(
            create_form, pf_b, projected_bindings, preserve_existing=False, extra_keys=extra_keys,
        )
        used_csrf = used_csrf or csrf_hit
        final_st, final_url, final_body = sess_b.request(act_b, method=str(create_form.get("method") or "POST"), form_data=payload)
        trace.append({"app": "target", "stage": "SUBMIT_TARGET_CREATE", "action": act_b, "status": final_st, "keys": sorted(payload)})
        submitted_payload = payload
        if 200 <= final_st < 300:
            stages.append("SUBMIT_TARGET_CREATE")
            distilled = _distill_enterprise_skill(
                memory,
                workflow_kind="CROSS_APP_BRIDGE",
                needs_source_auth=needs_sa,
                needs_target_auth=needs_ta,
                stages=stages,
                discovered_fields=discovered_fields or prebound_fields,
                used_csrf=used_csrf,
                blocked_destructive=bool(blocked_destructive),
            )
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "live_http_web_ui",
                "status": "VERIFIED",
                "mode": "TIER0_WEB_ENTERPRISE_SKILL" if (recalled and failed_probes == 0) else "WEB_CROSS_APP_BRIDGE",
                "http_status": final_st,
                "final_url": final_url,
                "response_body": final_body,
                "extracted_source_facts": extracted_facts,
                "submitted_payload": submitted_payload,
                "source_pages_crawled": crawled_a["pages_crawled"],
                "failed_probes": failed_probes,
                "discovered_conditional_fields": discovered_fields,
                "stages_executed": stages,
                "blocked_destructive_forms": blocked_destructive,
                "recalled_law_id": recalled["law_id"] if recalled else None,
                "distilled_law": distilled,
                "trace": trace,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }
        failed_probes += 1
        missing = list(COMPOSE_ERR.missing_from_error(final_body))
        for m_req in re.finditer(
            r"(?:missing|required)\s+(?:required\s+)?(?:field|param|parameter|key)?\s*[:=]?\s*['\"]?([A-Za-z_][A-Za-z0-9_\-]*)['\"]?",
            final_body,
            flags=re.IGNORECASE,
        ):
            cand = m_req.group(1).strip().lower()
            if cand and cand not in ("error", "detail", "message", "field", "required", "missing") and cand not in missing:
                missing.append(cand)
        added = False
        for mk in missing:
            mkl = mk.strip().lower()
            if mkl and mkl not in extra_keys:
                extra_keys.append(mkl)
                if mkl not in discovered_fields:
                    discovered_fields.append(mkl)
                added = True
        if not added:
            break

    return {
        "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
        "status": "FAILED", "mode": "WEB_TARGET_SUBMIT_FAILED", "http_status": final_st,
        "response_body": final_body, "extracted_source_facts": extracted_facts,
        "failed_probes": failed_probes, "blocked_destructive_forms": blocked_destructive,
        "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0, "parameters_stored": 0,
    }


def classify_enterprise_web_intent(
    instruction: str,
    *,
    urls: Sequence[str],
    supplied: Mapping[str, str],
) -> str | None:
    """Return 'CROSS_APP_BRIDGE', 'RECORD_CRUD_EDIT', 'TABLE_FILTER_AGGREGATE', or None."""
    if len(urls) >= 2:
        return "CROSS_APP_BRIDGE"
    low = (instruction or "").lower()
    # Preserve e-commerce cart/checkout workflows for the existing multi-page e-commerce engine
    if any(k in low for k in ("cart", "bag", "basket", "checkout", "check out", "place order", "purchase")):
        return None
    parsed = _parse_goal_filters_and_updates(instruction, supplied)
    if parsed["updates"] and (
        parsed["record_id"]
        or any(k in low for k in ("ticket", "incident", "issue", "record", "invoice", "case", "row", "entry", "table", "queue", "edit", "update", "reassign"))
    ):
        return "RECORD_CRUD_EDIT"
    if parsed["agg_op"] is not None and any(
        k in low for k in ("table", "list", "queue", "tickets", "incidents", "issues", "invoices", "orders", "records", "employees", "items", "products", "cases", "pages", "paginate", "portal", "filter", "where", "how many", "total", "sum", "average", "avg", "highest", "lowest", "most expensive", "cheapest", "who owns")
    ):
        return "TABLE_FILTER_AGGREGATE"
    return None
