"""End-to-End Tests for Epistemic Enterprise Multi-Page Web Agent v1 (WorkArena / WebArena-Pro Class).

Tests REAL live multi-server HTTP applications (isolated cookie sessions, CSRF tokens,
multi-page paginated HTML tables, destructive traps, detail drill-down, CRUD edits with
pre-filled field preservation, cross-application pipelines, Tier-0 single-experience
transfer across completely unseen app pairs, and instant unlearning) through ONE Front Door:
`open_model().solve(..., mode="EPISTEMIC")`.
"""
from __future__ import annotations

import http.server
import socketserver
import threading
import unittest
import urllib.parse
from typing import Any

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime import universal_epistemic_kernel_v1 as UEK


class _LiveAppServer:
    def __init__(self, handler_cls: type[http.server.BaseHTTPRequestHandler]) -> None:
        self._httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler_cls)
        self._httpd.daemon_threads = True
        self.port = int(self._httpd.server_address[1])
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def __enter__(self) -> "_LiveAppServer":
        self._thread.start()
        return self

    def __exit__(self, *_exc: Any) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


def _make_servicenow_portal_handler(state: dict[str, Any]) -> type[http.server.BaseHTTPRequestHandler]:
    """Realistic multi-page IT Incidents + Invoices portal with auth, CSRF, pagination, detail & CRUD edit."""
    csrf_tok = "csrf_sn_99182"
    session_cookie = "sn_sess=valid_session_abc"

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def _is_authed(self) -> bool:
            return session_cookie in (self.headers.get("Cookie") or "")

        def _send(self, code: int, html: str, cookie: str | None = None) -> None:
            body = html.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)

            if parsed.path in ("/", "/login"):
                if self._is_authed() and parsed.path == "/":
                    self._send(
                        200,
                        "<html><body><h1>Operations Portal</h1>"
                        "<nav><a href='/incidents?page=1'>Incidents Queue</a> | "
                        "<a href='/invoices?page=1'>Invoices Ledger</a> | "
                        "<a href='/admin/purge-all'>Purge All Records</a></nav>"
                        "<form method='POST' action='/admin/delete-all'><button>Delete Everything</button></form>"
                        "</body></html>",
                    )
                    return
                self._send(
                    200,
                    "<html><body><h1>Sign In</h1>"
                    f"<form method='POST' action='/login'>"
                    f"<input type='hidden' name='csrf_token' value='{csrf_tok}'>"
                    "<input name='username' required><input name='password' type='password' required>"
                    "<button type='submit'>Login</button></form></body></html>",
                )
                return

            if not self._is_authed():
                self._send(403, "<html><body>Forbidden: login required</body></html>")
                return

            if parsed.path == "/admin/purge-all":
                state["destructive_hits"] += 1
                self._send(200, "<html><body>WIPED!</body></html>")
                return

            if parsed.path == "/incidents":
                page = int((qs.get("page") or ["1"])[0])
                items = state["incidents"]
                per_page = 4
                chunk = items[(page - 1) * per_page : page * per_page]
                rows_html = []
                for it in chunk:
                    rows_html.append(
                        f"<tr><td>{it['id']}</td><td>{it['title']}</td><td>{it['status']}</td>"
                        f"<td>{it['priority']}</td><td>${it['cost']:,.2f}</td>"
                        f"<td><a href='/incidents/{it['id']}'>View</a> | "
                        f"<a href='/incidents/{it['id']}/edit'>Edit</a> | "
                        f"<a href='/incidents/{it['id']}/delete'>Delete</a></td></tr>"
                    )
                next_link = f"<a href='/incidents?page={page + 1}'>Next</a>" if page * per_page < len(items) else ""
                self._send(
                    200,
                    "<html><body><h1>Incidents Queue</h1>"
                    "<table><thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Priority</th><th>Cost</th><th>Actions</th></tr></thead>"
                    f"<tbody>{''.join(rows_html)}</tbody></table>"
                    f"<div class='pager'>{next_link}</div></body></html>",
                )
                return

            if parsed.path == "/invoices":
                page = int((qs.get("page") or ["1"])[0])
                items = state["invoices"]
                per_page = 3
                chunk = items[(page - 1) * per_page : page * per_page]
                rows_html = [
                    f"<tr><td>{iv['id']}</td><td>{iv['department']}</td><td>{iv['status']}</td><td>${iv['amount']:,.2f}</td></tr>"
                    for iv in chunk
                ]
                next_link = f"<a href='/invoices?page={page + 1}'>Next</a>" if page * per_page < len(items) else ""
                self._send(
                    200,
                    "<html><body><h1>Invoices Ledger</h1>"
                    "<table><thead><tr><th>Invoice</th><th>Department</th><th>Status</th><th>Amount</th></tr></thead>"
                    f"<tbody>{''.join(rows_html)}</tbody></table>"
                    f"<div class='pager'>{next_link}</div></body></html>",
                )
                return

            if parsed.path.startswith("/incidents/") and parsed.path.endswith("/delete"):
                state["destructive_hits"] += 1
                self._send(200, "<html><body>DELETED!</body></html>")
                return

            if parsed.path.startswith("/incidents/") and parsed.path.endswith("/edit"):
                inc_id = parsed.path.split("/")[2]
                rec = next((x for x in state["incidents"] if x["id"] == inc_id), None)
                if not rec:
                    self._send(404, "Not found")
                    return
                opts = "".join(
                    f"<option value='{s}'{' selected' if rec['status'] == s else ''}>{s}</option>"
                    for s in ("open", "in_progress", "resolved", "closed")
                )
                self._send(
                    200,
                    f"<html><body><h1>Edit {inc_id}</h1>"
                    f"<form method='POST' action='/incidents/{inc_id}/delete'><button>Delete Ticket</button></form>"
                    f"<form method='POST' action='/incidents/{inc_id}/edit'>"
                    f"<input type='hidden' name='csrf_token' value='{csrf_tok}'>"
                    f"<label for='f_title'>Title</label><input id='f_title' name='title' value='{rec['title']}' required>"
                    f"<label for='f_tier'>Customer Tier</label><input id='f_tier' name='customer_tier' value='{rec['customer_tier']}'>"
                    f"<label for='f_sla'>SLA Hours</label><input id='f_sla' name='sla_hours' value='{rec['sla_hours']}'>"
                    f"<label for='f_status'>Status</label><select id='f_status' name='status'>{opts}</select>"
                    f"<label for='f_assignee'>Assignee</label><input id='f_assignee' name='assignee' value='{rec['owner']}'>"
                    "<button type='submit'>Save Changes</button></form></body></html>",
                )
                return

            if parsed.path.startswith("/incidents/"):
                inc_id = parsed.path.split("/")[2]
                rec = next((x for x in state["incidents"] if x["id"] == inc_id), None)
                if not rec:
                    self._send(404, "Not found")
                    return
                self._send(
                    200,
                    f"<html><body><h1>Incident {inc_id}</h1>"
                    f"<dl><dt>Title</dt><dd>{rec['title']}</dd>"
                    f"<dt>Owner</dt><dd>{rec['owner']}</dd>"
                    f"<dt>Customer Tier</dt><dd>{rec['customer_tier']}</dd>"
                    f"<dt>Root Cause</dt><dd>{rec['root_cause']}</dd></dl>"
                    f"<a href='/incidents/{inc_id}/edit'>Edit Incident</a> | "
                    f"<a href='/incidents/{inc_id}/delete'>Delete Incident</a></body></html>",
                )
                return

            self._send(404, "Not found")

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            form = {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}

            if self.path == "/login":
                if form.get("csrf_token") != csrf_tok:
                    self._send(403, "Invalid CSRF token")
                    return
                if form.get("username") == "ops_admin" and form.get("password") == "s3cr3t!":
                    self._send(
                        200,
                        "<html><body><h1>Operations Portal</h1>"
                        "<nav><a href='/incidents?page=1'>Incidents Queue</a> | "
                        "<a href='/invoices?page=1'>Invoices Ledger</a> | "
                        "<a href='/admin/purge-all'>Purge All Records</a></nav></body></html>",
                        cookie=session_cookie,
                    )
                    return
                self._send(401, "Bad credentials")
                return

            if not self._is_authed():
                self._send(403, "Unauthorized")
                return

            if "delete" in self.path or "purge" in self.path:
                state["destructive_hits"] += 1
                self._send(200, "DELETED!")
                return

            if self.path.startswith("/incidents/") and self.path.endswith("/edit"):
                if form.get("csrf_token") != csrf_tok:
                    self._send(403, "Invalid CSRF token")
                    return
                inc_id = self.path.split("/")[2]
                rec = next((x for x in state["incidents"] if x["id"] == inc_id), None)
                if not rec:
                    self._send(404, "Not found")
                    return
                if form.get("status") == "resolved" and not form.get("resolution_code"):
                    self._send(400, "Error: missing required field: resolution_code")
                    return
                rec["title"] = form.get("title", rec["title"])
                rec["customer_tier"] = form.get("customer_tier", rec["customer_tier"])
                rec["sla_hours"] = form.get("sla_hours", rec["sla_hours"])
                rec["status"] = form.get("status", rec["status"])
                rec["owner"] = form.get("assignee", rec["owner"])
                rec["resolution_code"] = form.get("resolution_code", "")
                state["edits"].append(dict(rec))
                self._send(200, f"<html><body>Updated {inc_id} successfully!</body></html>")
                return

            self._send(404, "Not found")

    return Handler


def _make_source_tracker_handler(
    state: dict[str, Any],
    *,
    variant: str,
) -> type[http.server.BaseHTTPRequestHandler]:
    """Two completely structurally distinct Source Web Apps (Peppermint Tickets vs PipeCRM Deals)."""
    csrf_tok = f"csrf_src_{variant}"
    cookie_val = f"src_{variant}_sid=ok_{variant}"
    login_path = "/login" if variant == "peppermint" else "/signin"
    list_path = "/tickets" if variant == "peppermint" else "/deals"
    user_ok = "alice" if variant == "peppermint" else "crm_user"
    pass_ok = "passA" if variant == "peppermint" else "passC"

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def _authed(self) -> bool:
            return cookie_val in (self.headers.get("Cookie") or "")

        def _send(self, code: int, html: str, cookie: str | None = None) -> None:
            b = html.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self) -> None:
            p = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(p.query)
            if p.path in ("/", login_path):
                if self._authed() and p.path == "/":
                    lbl = "Support Tickets" if variant == "peppermint" else "Active Deals"
                    self._send(200, f"<html><body><h1>{variant.upper()}</h1><a href='{list_path}?page=1'>{lbl}</a></body></html>")
                    return
                uname = "username" if variant == "peppermint" else "email"
                self._send(
                    200,
                    f"<html><body><form method='POST' action='{login_path}'>"
                    f"<input type='hidden' name='csrf_token' value='{csrf_tok}'>"
                    f"<input name='{uname}' required><input name='password' type='password' required>"
                    "<button>Sign In</button></form></body></html>",
                )
                return
            if not self._authed():
                self._send(403, "Login required")
                return
            if p.path == list_path:
                page = int((qs.get("page") or ["1"])[0])
                rows = state["records"]
                chunk = rows[(page - 1) * 2 : page * 2]
                nxt = f"<a href='{list_path}?page={page + 1}'>Next</a>" if page * 2 < len(rows) else ""
                if variant == "peppermint":
                    trs = "".join(
                        f"<tr><td>{r['id']}</td><td>{r['title']}</td><td>{r['status']}</td><td>{r['priority']}</td>"
                        f"<td><a href='/tickets/{r['id']}'>View</a> | <a href='/tickets/{r['id']}/delete'>Delete</a></td></tr>"
                        for r in chunk
                    )
                    self._send(
                        200,
                        "<html><body><table><thead><tr><th>Ticket ID</th><th>Title</th><th>Status</th><th>Priority</th><th>Action</th></tr></thead>"
                        f"<tbody>{trs}</tbody></table>{nxt}</body></html>",
                    )
                else:
                    trs = "".join(
                        f"<tr><td>{r['id']}</td><td>{r['title']}</td><td>{r['status']}</td><td>${r['value']:,.0f}</td>"
                        f"<td><a href='/deals/{r['id']}'>Inspect</a> | <a href='/deals/{r['id']}/remove'>Remove</a></td></tr>"
                        for r in chunk
                    )
                    self._send(
                        200,
                        "<html><body><table><thead><tr><th>Deal Code</th><th>Account</th><th>Stage</th><th>Value</th><th>Action</th></tr></thead>"
                        f"<tbody>{trs}</tbody></table>{nxt}</body></html>",
                    )
                return
            if p.path.startswith(f"{list_path}/"):
                rid = p.path.split("/")[2]
                rec = next((r for r in state["records"] if r["id"] == rid), None)
                if not rec:
                    self._send(404, "Not found")
                    return
                if variant == "peppermint":
                    self._send(
                        200,
                        f"<html><body><h1>{rec['id']}</h1><dl><dt>Owner</dt><dd>{rec['owner']}</dd>"
                        f"<dt>Impact</dt><dd>{rec['detail']}</dd></dl></body></html>",
                    )
                else:
                    self._send(
                        200,
                        f"<html><body><h1>{rec['id']}</h1>"
                        f"<p>Lead: {rec['owner']}</p><p>Notes: {rec['detail']}</p></body></html>",
                    )
                return
            self._send(404, "Not found")

        def do_POST(self) -> None:
            ln = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(ln).decode("utf-8", errors="replace")
            form = {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}
            if self.path == login_path:
                u = form.get("username") or form.get("email")
                if form.get("csrf_token") == csrf_tok and u == user_ok and form.get("password") == pass_ok:
                    lbl = "Support Tickets" if variant == "peppermint" else "Active Deals"
                    self._send(
                        200,
                        f"<html><body><h1>{variant.upper()}</h1><a href='{list_path}?page=1'>{lbl}</a></body></html>",
                        cookie=cookie_val,
                    )
                    return
                self._send(401, "Bad login")
                return
            self._send(404, "Not found")

    return Handler


def _make_target_wiki_handler(
    state: dict[str, Any],
    *,
    variant: str,
) -> type[http.server.BaseHTTPRequestHandler]:
    """Two completely structurally distinct Target Web Apps (Notion Wiki vs OpsBoard Reports)."""
    csrf_tok = f"csrf_tgt_{variant}"
    cookie_val = f"tgt_{variant}_sid=ok_{variant}"
    login_path = "/login" if variant == "notion" else "/auth"
    new_path = "/pages/new" if variant == "notion" else "/reports/compose"
    post_path = "/pages/create" if variant == "notion" else "/reports/publish"
    user_ok = "wiki_bot" if variant == "notion" else "ops_bot"
    pass_ok = "passB" if variant == "notion" else "passD"

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def _authed(self) -> bool:
            return cookie_val in (self.headers.get("Cookie") or "")

        def _send(self, code: int, html: str, cookie: str | None = None) -> None:
            b = html.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self) -> None:
            p = urllib.parse.urlparse(self.path).path
            if p in ("/", login_path):
                if self._authed() and p == "/":
                    lbl = "New Wiki Page" if variant == "notion" else "Compose Report"
                    self._send(
                        200,
                        f"<html><body><h1>{variant.upper()}</h1>"
                        f"<a href='{new_path}'>{lbl}</a> | <a href='/workspace/wipe'>Wipe Workspace</a></body></html>",
                    )
                    return
                self._send(
                    200,
                    f"<html><body><form method='POST' action='{login_path}'>"
                    f"<input type='hidden' name='csrf_token' value='{csrf_tok}'>"
                    "<input name='username' required><input name='password' type='password' required>"
                    "<button>Login</button></form></body></html>",
                )
                return
            if not self._authed():
                self._send(403, "Login required")
                return
            if p == "/workspace/wipe":
                state["destructive_hits"] += 1
                self._send(200, "WIPED")
                return
            if p == new_path:
                if variant == "notion":
                    self._send(
                        200,
                        f"<html><body><h1>New Wiki Page</h1>"
                        f"<form method='POST' action='/pages/destroy-all'><button>Destroy All Pages</button></form>"
                        f"<form method='POST' action='{post_path}'>"
                        f"<input type='hidden' name='csrf_token' value='{csrf_tok}'>"
                        "<label for='pt'>Title</label><input id='pt' name='page_title' required>"
                        "<label for='au'>Owner</label><input id='au' name='author_name' required>"
                        "<label for='mb'>Summary</label><textarea id='mb' name='markdown_body' required></textarea>"
                        "<button type='submit'>Create Page</button></form></body></html>",
                    )
                else:
                    self._send(
                        200,
                        f"<html><body><h1>Compose Dispatch Report</h1>"
                        f"<form method='POST' action='{post_path}'>"
                        f"<input type='hidden' name='csrf_token' value='{csrf_tok}'>"
                        "<label for='hd'>Heading</label><input id='hd' name='heading' required>"
                        "<label for='ct'>Lead</label><input id='ct' name='contact' required>"
                        "<label for='dt'>Details</label><textarea id='dt' name='details' required></textarea>"
                        "<button type='submit'>Publish Report</button></form></body></html>",
                    )
                return
            self._send(404, "Not found")

        def do_POST(self) -> None:
            ln = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(ln).decode("utf-8", errors="replace")
            form = {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}
            if self.path == login_path:
                if form.get("csrf_token") == csrf_tok and form.get("username") == user_ok and form.get("password") == pass_ok:
                    lbl = "New Wiki Page" if variant == "notion" else "Compose Report"
                    self._send(
                        200,
                        f"<html><body><h1>{variant.upper()}</h1>"
                        f"<a href='{new_path}'>{lbl}</a> | <a href='/workspace/wipe'>Wipe Workspace</a></body></html>",
                        cookie=cookie_val,
                    )
                    return
                self._send(401, "Bad auth")
                return
            if not self._authed():
                self._send(403, "Login required")
                return
            if "destroy" in self.path or "wipe" in self.path:
                state["destructive_hits"] += 1
                self._send(200, "DESTROYED")
                return
            if self.path == post_path:
                if form.get("csrf_token") != csrf_tok:
                    self._send(403, "Invalid CSRF token")
                    return
                if not form.get("space_code"):
                    self._send(400, "Error: missing required field: space_code")
                    return
                state["created"].append(dict(form))
                self._send(200, "<html><body>Created successfully!</body></html>")
                return
            self._send(404, "Not found")

    return Handler


class TestEpistemicEnterpriseWebAgentV1(unittest.TestCase):
    def _build_portal_state(self) -> dict[str, Any]:
        return {
            "destructive_hits": 0,
            "edits": [],
            "incidents": [
                {"id": "INC-401", "title": "Email sync delay", "status": "closed", "priority": "low", "cost": 120.0, "owner": "Sam Lee", "customer_tier": "Standard", "sla_hours": "24", "root_cause": "Queue spike"},
                {"id": "INC-402", "title": "VPN gateway flap", "status": "open", "priority": "high", "cost": 850.0, "owner": "Diego Park", "customer_tier": "Enterprise", "sla_hours": "4", "root_cause": "BGP flap"},
                {"id": "INC-403", "title": "Printer offline", "status": "open", "priority": "low", "cost": 90.0, "owner": "Lin Chen", "customer_tier": "Standard", "sla_hours": "48", "root_cause": "Paper jam"},
                {"id": "INC-404", "title": "SSO token expiry", "status": "open", "priority": "high", "cost": 1400.0, "owner": "Maya Patel", "customer_tier": "Enterprise", "sla_hours": "2", "root_cause": "Clock skew"},
                {"id": "INC-405", "title": "VPN tunnel outage EU", "status": "open", "priority": "high", "cost": 3250.0, "owner": "Elena Rostova", "customer_tier": "Enterprise", "sla_hours": "1", "root_cause": "Expired cert"},
                {"id": "INC-406", "title": "Billing export CSV", "status": "resolved", "priority": "medium", "cost": 300.0, "owner": "Omar Haddad", "customer_tier": "Pro", "sla_hours": "12", "root_cause": "UTF-8 BOM"},
                {"id": "INC-407", "title": "DNS cache stale", "status": "open", "priority": "medium", "cost": 410.0, "owner": "Nora Vance", "customer_tier": "Pro", "sla_hours": "8", "root_cause": "TTL mismatch"},
                {"id": "INC-408", "title": "TLS handshake timeout", "status": "open", "priority": "medium", "cost": 620.0, "owner": "Alex Kim", "customer_tier": "Enterprise", "sla_hours": "4", "root_cause": "Cipher mismatch"},
                {"id": "INC-409", "title": "Dashboard chart lag", "status": "closed", "priority": "low", "cost": 150.0, "owner": "Sam Lee", "customer_tier": "Standard", "sla_hours": "24", "root_cause": "Missing index"},
                {"id": "INC-410", "title": "VPN split-tunnel drop", "status": "closed", "priority": "high", "cost": 4900.0, "owner": "Fake Closed", "customer_tier": "Enterprise", "sla_hours": "1", "root_cause": "Old closed"},
            ],
            "invoices": [
                {"id": "INV-01", "department": "Engineering", "status": "unpaid", "amount": 1250.50},
                {"id": "INV-02", "department": "Engineering", "status": "unpaid", "amount": 250.00},
                {"id": "INV-03", "department": "Marketing", "status": "unpaid", "amount": 1800.00},
                {"id": "INV-04", "department": "Engineering", "status": "paid", "amount": 4000.00},
                {"id": "INV-05", "department": "Engineering", "status": "unpaid", "amount": 2400.00},
                {"id": "INV-06", "department": "Sales", "status": "unpaid", "amount": 950.00},
            ],
        }

    def test_01_workarena_multipage_table_filter_aggregate_and_detail_drilldown(self) -> None:
        state = self._build_portal_state()
        model = open_model()
        creds = {"username": "ops_admin", "password": "s3cr3t!"}

        with _LiveAppServer(_make_servicenow_portal_handler(state)) as srv:
            # 1a. Paginated multi-page COUNT with compound filters (3 pages, 10 incidents -> 3 high-priority open)
            out_cnt = model.solve(
                "How many open incidents where priority is high in the incidents queue?",
                mode="EPISTEMIC",
                inputs={"web_url": srv.base_url + "/", "field_values": creds},
            )
            er_cnt = out_cnt["epistemic_result"]
            self.assertEqual(er_cnt["status"], "VERIFIED", er_cnt)
            self.assertEqual(er_cnt["mode"], "WEB_TABLE_FILTER_AGGREGATE")
            self.assertEqual(er_cnt["answer"], 3)
            self.assertEqual(er_cnt["pages_crawled"], 3)
            self.assertEqual(er_cnt["total_rows_scanned"], 10)
            self.assertEqual(er_cnt["model_calls"], 0)
            self.assertEqual(er_cnt["parameters_stored"], 0)
            self.assertTrue(er_cnt["blocked_destructive_forms"])

            # 1b. Paginated SUM with string equality + numeric inequality filter + currency parsing
            out_sum = model.solve(
                "Calculate the total amount of unpaid invoices where department is Engineering and amount > 500",
                mode="EPISTEMIC",
                inputs={"web_url": srv.base_url + "/", "field_values": creds},
            )
            er_sum = out_sum["epistemic_result"]
            self.assertEqual(er_sum["status"], "VERIFIED", er_sum)
            self.assertEqual(er_sum["pages_crawled"], 2)
            self.assertAlmostEqual(float(er_sum["answer"]), 3650.5, places=2)

            # 1c. Paginated MAX + Detail-page drill-down (owner is NOT in summary table!)
            out_max = model.solve(
                "Find the owner of the highest cost open VPN incident in the incidents queue",
                mode="EPISTEMIC",
                inputs={"web_url": srv.base_url + "/", "field_values": creds},
            )
            er_max = out_max["epistemic_result"]
            self.assertEqual(er_max["status"], "VERIFIED", er_max)
            self.assertEqual(er_max["answer"], "Elena Rostova")
            self.assertEqual(er_max["winning_row"]["id"], "INC-405")
            self.assertIn("DRILL_DETAIL_PAGE", er_max["stages_executed"])
            self.assertEqual(state["destructive_hits"], 0)

    def test_02_webarena_authenticated_crud_edit_preserves_fields_and_discovers_conditional_field(self) -> None:
        state = self._build_portal_state()
        model = open_model()
        mem = UEK.new_universal_memory()

        with _LiveAppServer(_make_servicenow_portal_handler(state)) as srv:
            out = model.solve(
                "Update incident INC-408 in the incidents queue: set status to resolved and assign to Priya Nair",
                mode="EPISTEMIC",
                inputs={
                    "web_url": srv.base_url + "/",
                    "memory": mem,
                    "field_values": {
                        "username": "ops_admin",
                        "password": "s3cr3t!",
                        "resolution_code": "PATCHED_TLS_CIPHER",
                    },
                },
            )
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["mode"], "WEB_RECORD_CRUD_EDIT")
            self.assertEqual(er["pages_crawled"], 3)
            self.assertIn("resolution_code", er["discovered_conditional_fields"])
            self.assertEqual(state["destructive_hits"], 0)
            self.assertEqual(len(state["edits"]), 1)
            rec = state["edits"][0]
            self.assertEqual(rec["id"], "INC-408")
            self.assertEqual(rec["status"], "resolved")
            self.assertEqual(rec["owner"], "Priya Nair")
            self.assertEqual(rec["resolution_code"], "PATCHED_TLS_CIPHER")
            # Crucial: untouched pre-filled fields MUST be preserved!
            self.assertEqual(rec["title"], "TLS handshake timeout")
            self.assertEqual(rec["customer_tier"], "Enterprise")
            self.assertEqual(rec["sla_hours"], "4")

    def test_03_webarena_pro_cross_app_bridge_tier0_transfer_and_instant_unlearning(self) -> None:
        model = open_model()
        mem = UEK.new_universal_memory()

        # Pair 1: Peppermint Ticket Tracker -> Notion Knowledge Wiki
        src1_state = {
            "records": [
                {"id": "TKT-221", "title": "Laptop battery swap", "status": "open", "priority": "low", "owner": "Dana Wu", "detail": "Battery degraded"},
                {"id": "TKT-222", "title": "VPN routing closed", "status": "closed", "priority": "critical", "owner": "Old Owner", "detail": "Already resolved"},
                {"id": "TKT-225", "title": "VPN gateway outage EU", "status": "open", "priority": "critical", "owner": "Marcus Vance", "detail": "EU-West gateway timeout"},
            ]
        }
        tgt1_state = {"destructive_hits": 0, "created": []}

        with _LiveAppServer(_make_source_tracker_handler(src1_state, variant="peppermint")) as src1, \
             _LiveAppServer(_make_target_wiki_handler(tgt1_state, variant="notion")) as tgt1:
            out1 = model.solve(
                f"From {src1.base_url}/ find the highest priority open VPN ticket and create a summary wiki page on {tgt1.base_url}/",
                mode="EPISTEMIC",
                inputs={
                    "memory": mem,
                    "field_values": {
                        "source_username": "alice",
                        "source_password": "passA",
                        "target_username": "wiki_bot",
                        "target_password": "passB",
                        "space_code": "OPS-KB",
                    },
                },
            )
            er1 = out1["epistemic_result"]
            self.assertEqual(er1["status"], "VERIFIED", er1)
            self.assertEqual(er1["mode"], "WEB_CROSS_APP_BRIDGE")
            self.assertEqual(er1["model_calls"], 0)
            self.assertEqual(er1["parameters_stored"], 0)
            self.assertEqual(tgt1_state["destructive_hits"], 0)
            self.assertEqual(er1["failed_probes"], 1)
            self.assertIn("space_code", er1["discovered_conditional_fields"])
            self.assertEqual(len(tgt1_state["created"]), 1)
            created1 = tgt1_state["created"][0]
            self.assertIn("VPN gateway outage EU", created1["page_title"])
            self.assertEqual(created1["author_name"], "Marcus Vance")
            self.assertIn("EU-West gateway timeout", created1["markdown_body"])
            self.assertEqual(created1["space_code"], "OPS-KB")

            # Inspect distilled skill: ZERO URLs, ZERO HTML, ZERO concrete IDs, ZERO weights!
            law = er1["distilled_law"]
            self.assertIsNotNone(law)
            law_id = law["law_id"]
            law_blob = str(law)
            self.assertNotIn("127.0.0.1", law_blob)
            self.assertNotIn("TKT-225", law_blob)
            self.assertNotIn("Marcus Vance", law_blob)
            self.assertEqual(law["parameters_stored"], 0)

        # Pair 2: COMPLETELY UNSEEN PipeCRM -> OpsBoard (different ports, routes, columns, form field names!)
        src2_state = {
            "records": [
                {"id": "DL-901", "title": "Acme Retail", "status": "lost", "value": 95000, "owner": "Ignored", "detail": "Closed lost"},
                {"id": "DL-902", "title": "Helios Bio", "status": "active", "value": 42000, "owner": "Tariq Z", "detail": "Pilot phase"},
                {"id": "DL-903", "title": "Orion Cloud", "status": "active", "value": 185000, "owner": "Sora Takahashi", "detail": "Annual enterprise expansion"},
            ]
        }
        tgt2_state = {"destructive_hits": 0, "created": []}

        with _LiveAppServer(_make_source_tracker_handler(src2_state, variant="pipecrm")) as src2, \
             _LiveAppServer(_make_target_wiki_handler(tgt2_state, variant="opsboard")) as tgt2:
            # 2a. Tier-0 single-experience transfer: 0 failed probes on completely unseen app pair!
            out2 = model.solve(
                "Find the highest value active deal and publish a dispatch report",
                mode="EPISTEMIC",
                inputs={
                    "source_url": src2.base_url + "/",
                    "target_url": tgt2.base_url + "/",
                    "memory": mem,
                    "field_values": {
                        "source_username": "crm_user",
                        "source_password": "passC",
                        "target_username": "ops_bot",
                        "target_password": "passD",
                        "space_code": "REV-OPS",
                    },
                },
            )
            er2 = out2["epistemic_result"]
            self.assertEqual(er2["status"], "VERIFIED", er2)
            self.assertEqual(er2["mode"], "TIER0_WEB_ENTERPRISE_SKILL")
            self.assertEqual(er2["recalled_law_id"], law_id)
            self.assertEqual(er2["failed_probes"], 0)
            self.assertEqual(len(tgt2_state["created"]), 1)
            created2 = tgt2_state["created"][0]
            self.assertIn("Orion Cloud", created2["heading"])
            self.assertEqual(created2["contact"], "Sora Takahashi")
            self.assertIn("Annual enterprise expansion", created2["details"])
            self.assertEqual(created2["space_code"], "REV-OPS")

            # 2b. Instant Unlearning: delete law_id from external memory -> skill is immediately gone!
            self.assertTrue(UEK.delete_memory_entry(mem, law_id))
            self.assertEqual(mem["web_enterprise_skills"], {})
            out3 = model.solve(
                "Find the highest value active deal and publish a dispatch report",
                mode="EPISTEMIC",
                inputs={
                    "source_url": src2.base_url + "/",
                    "target_url": tgt2.base_url + "/",
                    "memory": mem,
                    "field_values": {
                        "source_username": "crm_user",
                        "source_password": "passC",
                        "target_username": "ops_bot",
                        "target_password": "passD",
                        "space_code": "REV-OPS",
                    },
                },
            )
            er3 = out3["epistemic_result"]
            self.assertEqual(er3["status"], "VERIFIED", er3)
            self.assertIsNone(er3["recalled_law_id"])
            self.assertEqual(er3["failed_probes"], 1)

    def test_04_multitable_avg_min_and_select_label_value_crud(self) -> None:
        """Multi-table page (KPI header table + paginated main table), AVG & MIN currency queries,
        and CRUD edit matching <select><option value='3'>Resolved</option> text->code mapping."""
        state: dict[str, Any] = {
            "destructive_hits": 0,
            "saved": [],
            "items": [
                {"id": "ASSET-10", "name": "Rack Switch A", "category": "Network", "status": "1", "price": 1200.0},
                {"id": "ASSET-11", "name": "Rack Switch B", "category": "Network", "status": "1", "price": 800.0},
                {"id": "ASSET-12", "name": "Fiber Patch", "category": "Network", "status": "1", "price": 400.0},
                {"id": "ASSET-13", "name": "Office Chair", "category": "Furniture", "status": "1", "price": 250.0},
            ],
        }

        class MultiTableHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def _send(self, code: int, html: str) -> None:
                b = html.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self) -> None:
                p = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(p.query)
                if p.path in ("/", "/assets"):
                    page = int((qs.get("p") or ["1"])[0])
                    rows = state["items"][(page - 1) * 2 : page * 2]
                    trs = "".join(
                        f"<tr><td>{r['id']}</td><td>{r['name']}</td><td>{r['category']}</td><td>${r['price']:,.2f}</td>"
                        f"<td><a href='/assets/{r['id']}/edit'>Edit</a> | <a href='/assets/{r['id']}/destroy'>Destroy</a></td></tr>"
                        for r in rows
                    )
                    nxt = f"<a href='/assets?p={page + 1}'>›</a>" if page * 2 < len(state["items"]) else ""
                    # Decoy 1-row KPI summary table BEFORE the real data table
                    self._send(
                        200,
                        "<html><body>"
                        "<table><thead><tr><th>Metric</th><th>Count</th></tr></thead><tbody><tr><td>Total</td><td>4</td></tr></tbody></table>"
                        "<table><thead><tr><th>Asset</th><th>Name</th><th>Category</th><th>Price</th><th>Actions</th></tr></thead>"
                        f"<tbody>{trs}</tbody></table>{nxt}</body></html>",
                    )
                    return
                if p.path.startswith("/assets/") and p.path.endswith("/edit"):
                    aid = p.path.split("/")[2]
                    rec = next((r for r in state["items"] if r["id"] == aid), None)
                    if not rec:
                        self._send(404, "Not found")
                        return
                    self._send(
                        200,
                        f"<html><body>"
                        f"<form method='POST' action='/assets/{aid}/destroy'><button>Destroy Asset</button></form>"
                        f"<form method='POST' action='/assets/{aid}/save'>"
                        f"<input type='hidden' name='csrf' value='tok_asset'>"
                        f"<input name='name' value='{rec['name']}'>"
                        "<select name='status'><option value='1' selected>Active</option><option value='2'>Maintenance</option><option value='3'>Retired</option></select>"
                        "<button type='submit'>Save</button></form></body></html>",
                    )
                    return
                if "destroy" in p.path:
                    state["destructive_hits"] += 1
                    self._send(200, "DESTROYED")
                    return
                self._send(404, "Not found")

            def do_POST(self) -> None:
                ln = int(self.headers.get("Content-Length") or "0")
                raw = self.rfile.read(ln).decode("utf-8", errors="replace")
                form = {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}
                if "destroy" in self.path:
                    state["destructive_hits"] += 1
                    self._send(200, "DESTROYED")
                    return
                if self.path.endswith("/save") and form.get("csrf") == "tok_asset":
                    state["saved"].append(dict(form))
                    self._send(200, "<html><body>Saved</body></html>")
                    return
                self._send(400, "Bad request")

        model = open_model()
        with _LiveAppServer(MultiTableHandler) as srv:
            # AVG over filtered Network items across 2 pages: (1200 + 800 + 400) / 3 = 800.0
            out_avg = model.solve(
                "What is the average price of items where category is Network in the table?",
                mode="EPISTEMIC",
                inputs={"web_url": srv.base_url + "/"},
            )
            er_avg = out_avg["epistemic_result"]
            self.assertEqual(er_avg["status"], "VERIFIED", er_avg)
            self.assertAlmostEqual(float(er_avg["answer"]), 800.0, places=2)
            self.assertEqual(er_avg["pages_crawled"], 2)

            # MIN over filtered Network items -> return name of cheapest Network item ("Fiber Patch")
            out_min = model.solve(
                "Find the name of the cheapest item where category is Network in the table",
                mode="EPISTEMIC",
                inputs={"web_url": srv.base_url + "/"},
            )
            er_min = out_min["epistemic_result"]
            self.assertEqual(er_min["status"], "VERIFIED", er_min)
            self.assertEqual(er_min["answer"], "Fiber Patch")

            # CRUD edit mapping <option value='3'>Retired</option> via display label while preserving name!
            out_ed = model.solve(
                "Update record ASSET-11 in the table: set status to Retired",
                mode="EPISTEMIC",
                inputs={"web_url": srv.base_url + "/"},
            )
            er_ed = out_ed["epistemic_result"]
            self.assertEqual(er_ed["status"], "VERIFIED", er_ed)
            self.assertEqual(state["destructive_hits"], 0)
            self.assertEqual(len(state["saved"]), 1)
            self.assertEqual(state["saved"][0]["status"], "3")
            self.assertEqual(state["saved"][0]["name"], "Rack Switch B")


if __name__ == "__main__":
    unittest.main()
