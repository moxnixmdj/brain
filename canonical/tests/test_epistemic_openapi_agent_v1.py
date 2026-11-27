"""Live adversarial APIFlow-Bench-grade test suite for Epistemic OpenAPI Agent V1.

Verifies ALL 7 APIFlow-Bench (2026) production REST-API capability axes across TWO
completely distinct live HTTP OpenAPI 3.0 microservices (Service Alpha: Billing/Invoicing;
Service Beta: Logistics/Shipments with zero shared endpoints, auth schemes, pagination styles,
or field names), through ONE Front Door (`open_model().solve(..., mode="EPISTEMIC")`), with:
  - model_calls == 0, parameters_stored == 0, authority == "NONE"
  - Zero-URL / zero-token / zero-value polymorphic skill distillation & cross-service Tier-0 transfer
  - 5/5 deterministic reliability & inspectable memory save/load/delete without retraining.
"""

from __future__ import annotations

import http.server
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.parse
from typing import Any

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime import universal_epistemic_kernel_v1 as UEK


# ---------------------------------------------------------------------------
# Live Service Alpha: Billing & Invoicing (Bearer + cursor pagination + 401 expiry + 429 + incomplete-spec 422)
# ---------------------------------------------------------------------------

def _start_billing_service_alpha() -> tuple[http.server.ThreadingHTTPServer, str, dict[str, Any]]:
    state: dict[str, Any] = {
        "token_counter": 0,
        "active_token": None,
        "token_uses": 0,
        "clients": [
            {"id": "cli_101", "name": "Beta Labs"},
            {"id": "cli_102", "name": "Gamma Studio"},
            {"id": "cli_103", "name": "Orion Works"},
            {"id": "cli_104", "name": "Vega Systems"},
            {"id": "cli_105", "name": "Acme Corp"},  # Hidden on Page 3!
        ],
        "invoices": {},
        "rate_limited_once": False,
        "purge_hits": 0,
        "auth_calls": 0,
    }

    openapi_spec = {
        "openapi": "3.0.3",
        "info": {"title": "AlphaBillingAPI", "version": "1.0.0"},
        "security": [{"BearerAuth": []}],
        "components": {
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer"},
            },
            "schemas": {
                "InvoiceCreate": {
                    "type": "object",
                    "required": ["client_id", "amount", "currency"],
                    "properties": {
                        "client_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},  # Deliberately omits uppercase enum constraint!
                    },
                },
                "LoginBody": {
                    "type": "object",
                    "required": ["username", "password"],
                    "properties": {
                        "username": {"type": "string", "default": "billing_bot"},
                        "password": {"type": "string", "default": "secret"},
                    },
                },
            },
        },
        "paths": {
            "/v1/auth/login": {
                "post": {
                    "operationId": "loginUser",
                    "summary": "Acquire bearer access token",
                    "security": [],
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/LoginBody"}}}},
                    "responses": {
                        "200": {
                            "description": "Token",
                            "content": {"application/json": {"schema": {"type": "object", "properties": {"access_token": {"type": "string"}}}}},
                        }
                    },
                }
            },
            "/v1/clients": {
                "get": {
                    "operationId": "listClients",
                    "summary": "List paginated clients",
                    "parameters": [{"name": "cursor", "in": "query", "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "createClient",
                    "summary": "Create a new client",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {"name": {"type": "string"}},
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/v1/invoices": {
                "post": {
                    "operationId": "createInvoice",
                    "summary": "Create a billing invoice for a client",
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/InvoiceCreate"}}}},
                    "responses": {"201": {"description": "Created"}},
                }
            },
            "/v1/invoices/{invoice_id}/receipt": {
                "get": {
                    "operationId": "getInvoiceReceipt",
                    "summary": "Fetch verified billing receipt for an invoice",
                    "parameters": [{"name": "invoice_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/v1/admin/purge": {
                "delete": {
                    "operationId": "purgeAllBilling",
                    "summary": "Destructive trap: wipe all billing records",
                    "responses": {"200": {"description": "Wiped"}},
                }
            },
        },
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send_json(self, code: int, obj: Any, extra_headers: dict[str, str] | None = None) -> None:
            raw = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            for hk, hv in (extra_headers or {}).items():
                self.send_header(hk, hv)
            self.end_headers()
            self.wfile.write(raw)

        def _check_auth(self) -> bool:
            auth = self.headers.get("Authorization", "")
            if not state["active_token"] or auth != f"Bearer {state['active_token']}":
                self._send_json(401, {"error": "unauthorized", "message": "Invalid or missing bearer token"})
                return False
            state["token_uses"] += 1
            # Deliberately expire token after 2 uses to force live mid-workflow 401 refresh!
            if state["token_uses"] == 3:
                state["active_token"] = None
                self._send_json(401, {"error": "token_expired", "message": "Bearer token expired; re-authenticate"})
                return False
            return True

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/openapi.json":
                self._send_json(200, openapi_spec)
                return
            if parsed.path == "/":
                self._send_json(200, {"service": "AlphaBillingAPI", "openapi": "/openapi.json"})
                return
            if not self._check_auth():
                return
            if parsed.path == "/v1/clients":
                qs = urllib.parse.parse_qs(parsed.query)
                cur = qs.get("cursor", ["0"])[0]
                idx = int(cur) if cur.isdigit() else 0
                page_items = state["clients"][idx : idx + 2]
                nxt = str(idx + 2) if (idx + 2) < len(state["clients"]) else None
                self._send_json(200, {"items": page_items, "next_cursor": nxt})
                return
            if parsed.path.startswith("/v1/invoices/") and parsed.path.endswith("/receipt"):
                inv_id = parsed.path.split("/")[3]
                inv = state["invoices"].get(inv_id)
                if not inv:
                    self._send_json(404, {"error": "not_found"})
                    return
                self._send_json(200, {"invoice_id": inv_id, "verified": True, "total": inv["amount"], "currency": inv["currency"], "client_id": inv["client_id"]})
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            clen = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(clen).decode("utf-8", errors="replace") if clen > 0 else "{}"
            body = json.loads(raw) if raw.strip() else {}

            if parsed.path == "/v1/auth/login":
                state["token_counter"] += 1
                state["auth_calls"] += 1
                state["active_token"] = f"alpha_tok_{state['token_counter']}"
                state["token_uses"] = 0
                self._send_json(200, {"access_token": state["active_token"]})
                return

            if not self._check_auth():
                return

            if parsed.path == "/v1/invoices":
                # Simulate transient 429 rate-limit burst once!
                if not state["rate_limited_once"]:
                    state["rate_limited_once"] = True
                    self._send_json(429, {"error": "rate_limited", "retry_after": 0.02}, {"Retry-After": "0.02"})
                    return
                # Incomplete-spec hidden constraints: X-Idempotency-Key header + uppercase USD/EUR currency!
                errs = []
                if not self.headers.get("X-Idempotency-Key"):
                    errs.append({"missing_header": "X-Idempotency-Key", "message": "Missing required header 'X-Idempotency-Key'"})
                if body.get("currency") not in ("USD", "EUR", "GBP"):
                    errs.append({"field": "currency", "allowed": ["USD", "EUR", "GBP"], "message": "currency must be uppercase ISO code"})
                if errs:
                    self._send_json(422, {"detail": errs})
                    return
                inv_id = f"inv_{len(state['invoices']) + 1}"
                rec = {"id": inv_id, **body, "idempotency_key": self.headers.get("X-Idempotency-Key")}
                state["invoices"][inv_id] = rec
                self._send_json(201, rec)
                return

            self._send_json(404, {"error": "not_found"})

        def do_DELETE(self) -> None:
            state["purge_hits"] += 1
            self._send_json(200, {"purged": True})

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{port}", state


# ---------------------------------------------------------------------------
# Live Service Beta: Completely Distinct Logistics & Shipments Microservice
#   (apiKey X-API-Token + page/has_more pagination + missing FK creation + camelCase warehouseId
#    + 401 mid-chain expiry + 429 burst + incomplete-spec X-Request-Nonce & ISO date 422!)
# ---------------------------------------------------------------------------

def _start_logistics_service_beta() -> tuple[http.server.ThreadingHTTPServer, str, dict[str, Any]]:
    state: dict[str, Any] = {
        "token_counter": 0,
        "active_token": None,
        "token_uses": 0,
        "warehouses": [
            {"id": "wh_01", "name": "East Dock"},
            {"id": "wh_02", "name": "South Terminal"},
            {"id": "wh_03", "name": "West Depot"},
        ],
        "shipments": {},
        "rate_limited_once": False,
        "reset_hits": 0,
    }

    openapi_spec = {
        "openapi": "3.0.3",
        "info": {"title": "BetaLogisticsAPI", "version": "2.1.0"},
        "security": [{"ApiToken": []}],
        "components": {
            "securitySchemes": {
                "ApiToken": {"type": "apiKey", "in": "header", "name": "X-API-Token"},
            },
            "schemas": {
                "WarehouseCreate": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {"name": {"type": "string"}},
                },
                "ShipmentCreate": {
                    "type": "object",
                    "required": ["warehouseId", "weight", "ship_date"],
                    "properties": {
                        "warehouseId": {"type": "string"},
                        "weight": {"type": "integer"},
                        "ship_date": {"type": "string"},  # Deliberately omits YYYY-MM-DD format!
                    },
                },
            },
        },
        "paths": {
            "/api/v2/sessions": {
                "post": {
                    "operationId": "createSession",
                    "summary": "Create API session token",
                    "security": [],
                    "responses": {
                        "201": {
                            "description": "Session",
                            "content": {"application/json": {"schema": {"type": "object", "properties": {"api_token": {"type": "string"}}}}},
                        }
                    },
                }
            },
            "/api/v2/warehouses": {
                "get": {
                    "operationId": "listWarehouses",
                    "summary": "List warehouses with page pagination",
                    "parameters": [{"name": "page", "in": "query", "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "createWarehouse",
                    "summary": "Register a new warehouse",
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/WarehouseCreate"}}}},
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/api/v2/shipments": {
                "post": {
                    "operationId": "createShipment",
                    "summary": "Create outbound logistics shipment",
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ShipmentCreate"}}}},
                    "responses": {"201": {"description": "Created"}},
                }
            },
            "/api/v2/shipments/{shipment_id}/manifest": {
                "get": {
                    "operationId": "getShipmentManifest",
                    "summary": "Fetch final shipment manifest",
                    "parameters": [{"name": "shipment_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/v2/reset-all": {
                "post": {
                    "operationId": "resetAllLogistics",
                    "summary": "Destructive trap: reset all warehouses and shipments",
                    "responses": {"200": {"description": "Reset"}},
                }
            },
        },
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send_json(self, code: int, obj: Any, extra_headers: dict[str, str] | None = None) -> None:
            raw = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            for hk, hv in (extra_headers or {}).items():
                self.send_header(hk, hv)
            self.end_headers()
            self.wfile.write(raw)

        def _check_auth(self) -> bool:
            tok = self.headers.get("X-API-Token", "")
            if not state["active_token"] or tok != state["active_token"]:
                self._send_json(401, {"error": "invalid_session"})
                return False
            state["token_uses"] += 1
            if state["token_uses"] == 3:
                state["active_token"] = None
                self._send_json(401, {"error": "session_expired"})
                return False
            return True

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/openapi.json":
                self._send_json(200, openapi_spec)
                return
            if not self._check_auth():
                return
            if parsed.path == "/api/v2/warehouses":
                qs = urllib.parse.parse_qs(parsed.query)
                page = int(qs.get("page", ["1"])[0])
                start = (page - 1) * 2
                chunk = state["warehouses"][start : start + 2]
                self._send_json(200, {"data": chunk, "page": page, "has_more": (start + 2) < len(state["warehouses"])})
                return
            if parsed.path.startswith("/api/v2/shipments/") and parsed.path.endswith("/manifest"):
                sid = parsed.path.split("/")[4]
                sh = state["shipments"].get(sid)
                if not sh:
                    self._send_json(404, {"error": "not_found"})
                    return
                self._send_json(200, {"shipment_id": sid, "status": "DISPATCHED", **sh})
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            clen = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(clen).decode("utf-8", errors="replace") if clen > 0 else "{}"
            body = json.loads(raw) if raw.strip() else {}

            if parsed.path == "/api/v2/sessions":
                state["token_counter"] += 1
                state["active_token"] = f"beta_sess_{state['token_counter']}"
                state["token_uses"] = 0
                self._send_json(201, {"api_token": state["active_token"]})
                return

            if parsed.path == "/api/v2/reset-all":
                state["reset_hits"] += 1
                self._send_json(200, {"reset": True})
                return

            if not self._check_auth():
                return

            if parsed.path == "/api/v2/warehouses":
                wid = f"wh_{len(state['warehouses']) + 1:02d}"
                rec = {"id": wid, "name": body.get("name", "unnamed")}
                state["warehouses"].append(rec)
                self._send_json(201, rec)
                return

            if parsed.path == "/api/v2/shipments":
                if not state["rate_limited_once"]:
                    state["rate_limited_once"] = True
                    self._send_json(429, {"error": "throttled"}, {"Retry-After": "0.02"})
                    return
                errs = []
                if not self.headers.get("X-Request-Nonce"):
                    errs.append({"required_header": "X-Request-Nonce", "message": "Required header 'X-Request-Nonce' missing"})
                sd = str(body.get("ship_date") or "")
                if not (len(sd) == 10 and sd[4] == "-" and sd[7] == "-"):
                    errs.append({"field": "ship_date", "expected_format": "YYYY-MM-DD", "message": "ship_date must be ISO YYYY-MM-DD"})
                if errs:
                    self._send_json(422, {"errors": errs})
                    return
                sid = f"shp_{len(state['shipments']) + 1}"
                rec = {"id": sid, **body, "nonce": self.headers.get("X-Request-Nonce")}
                state["shipments"][sid] = rec
                self._send_json(201, rec)
                return

            self._send_json(404, {"error": "not_found"})

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{port}", state


class EpistemicOpenAPIAgentV1Tests(unittest.TestCase):
    def test_01_apiflow_7axes_and_cross_service_tier0_transfer_via_one_front_door(self) -> None:
        """Full 7-axis APIFlow-Bench live workflow on Service Alpha -> distill zero-URL/zero-token
        polymorphic skill -> persist to JSON -> zero-shot Tier-0 transfer onto unseen Service Beta ->
        5/5 reliability + inspectable memory deletion without retraining."""
        srv_a, url_a, state_a = _start_billing_service_alpha()
        srv_b, url_b, state_b = _start_logistics_service_beta()
        try:
            model = open_model()
            mem = UEK.new_universal_memory()

            # 1. Cold run on Service Alpha through ONE Front Door
            out_a = model.solve(
                "Create invoice for client Acme Corp with amount 250 currency usd and fetch its receipt",
                mode="EPISTEMIC",
                inputs={"api_url": url_a, "memory": mem},
            )
            er_a = out_a["epistemic_result"]
            self.assertEqual(er_a["status"], "VERIFIED", er_a)
            self.assertEqual(er_a["mode"], "EPISTEMIC_OPENAPI_WORKFLOW_SOLVED")
            self.assertEqual(er_a["model_calls"], 0)
            self.assertEqual(er_a["parameters_stored"], 0)
            self.assertEqual(er_a["authority"], "NONE")
            self.assertEqual(er_a["resolved_foreign_keys"], {"client_id": "cli_105"})
            self.assertEqual(er_a["readback"]["verified"], True)
            self.assertEqual(er_a["readback"]["currency"], "USD")
            self.assertEqual(er_a["readback"]["total"], 250)
            tel_a = er_a["telemetry"]
            self.assertEqual(tel_a["pages_scanned"], 3)  # Scanned all 3 cursor pages to find Acme Corp!
            self.assertGreaterEqual(tel_a["auth_refreshes"], 1)  # Survived mid-chain 401 expiry!
            self.assertGreaterEqual(tel_a["rate_limit_retries"], 1)  # Survived 429 burst!
            self.assertGreaterEqual(tel_a["schema_repairs"], 2)  # Repaired missing header + lowercase usd!
            self.assertEqual(state_a["purge_hits"], 0)  # Never touched destructive DELETE trap!

            # Verify zero-URL / zero-token / zero-value memory hygiene!
            skill_a = er_a["distilled_poly_skill"]
            skill_blob = json.dumps(skill_a)
            for forbidden in ("127.0.0.1", "alpha_tok", "Acme", "/v1/invoices", "cli_105", "X-Idempotency-Key"):
                self.assertNotIn(forbidden, skill_blob)
            self.assertFalse(skill_a["contains_urls_tokens_or_values"])

            # 2. Save memory to disk JSON, reload fresh, and zero-shot transfer onto COMPLETELY UNSEEN Service Beta!
            with tempfile.TemporaryDirectory(prefix="openapi_mem_") as td:
                mpath = pathlib.Path(td) / "epistemic_mem.json"
                UEK.save_universal_memory(mem, mpath)
                mem2 = UEK.load_universal_memory(mpath)

                out_b = model.solve(
                    "Create shipment for warehouse Delta Hub with weight 42 date 11/21/2026 and fetch its manifest",
                    mode="EPISTEMIC",
                    inputs={"api_url": url_b, "memory": mem2},
                )
                er_b = out_b["epistemic_result"]
                self.assertEqual(er_b["status"], "VERIFIED", er_b)
                self.assertEqual(er_b["mode"], "TIER0_OPENAPI_POLY_SKILL")
                self.assertEqual(er_b["model_calls"], 0)
                self.assertEqual(er_b["parameters_stored"], 0)
                self.assertEqual(er_b["authority"], "NONE")
                self.assertTrue(er_b["telemetry"]["tier0_poly_skill_used"])
                self.assertEqual(er_b["telemetry"]["tier0_skill_id"], skill_a["skill_id"])
                # Delta Hub was NOT on pages 1-2 -> agent created it via POST /api/v2/warehouses & bound camelCase warehouseId!
                self.assertEqual(er_b["resolved_foreign_keys"], {"warehouseId": "wh_04"})
                self.assertEqual(er_b["readback"]["status"], "DISPATCHED")
                self.assertEqual(er_b["readback"]["ship_date"], "2026-11-21")
                self.assertEqual(er_b["readback"]["weight"], 42)
                self.assertEqual(er_b["telemetry"]["pages_scanned"], 2)
                self.assertGreaterEqual(er_b["telemetry"]["auth_refreshes"], 1)
                self.assertGreaterEqual(er_b["telemetry"]["rate_limit_retries"], 1)
                self.assertEqual(state_b["reset_hits"], 0)

                # 3. Inspectable deletion removes the skill cleanly without retraining
                self.assertTrue(UEK.delete_memory_entry(mem2, skill_a["skill_id"]))
                self.assertNotIn(skill_a["skill_id"], mem2["api_poly_skills"])

            # 4. APIFlow-Bench 5/5 reliability gate: 5 consecutive runs on Service Beta must ALL pass 100%!
            for run_i in range(5):
                out_r = model.solve(
                    f"Create shipment for warehouse Delta Hub with weight {10 + run_i} date 11/21/2026 and fetch its manifest",
                    mode="EPISTEMIC",
                    inputs={"api_url": url_b, "memory": mem},
                )
                er_r = out_r["epistemic_result"]
                self.assertEqual(er_r["status"], "VERIFIED", f"Run {run_i} failed: {er_r}")
                self.assertEqual(er_r["readback"]["weight"], 10 + run_i)
                self.assertEqual(er_r["readback"]["ship_date"], "2026-11-21")
        finally:
            srv_a.shutdown()
            srv_a.server_close()
            srv_b.shutdown()
            srv_b.server_close()

    def test_02_recursive_multihop_fk_dag_and_rfc8288_link_pagination(self) -> None:
        """Service Gamma: 3-tier recursive FK DAG (organization -> project -> deployment -> status),
        query-param apiKey auth (?key=...), RFC 8288 Link: rel=\"next\" pagination, and URL embedded
        directly in plain-text goal via ONE Front Door."""
        state: dict[str, Any] = {
            "tok": "gamma_qkey_99",
            "organizations": [
                {"id": "org_1", "name": "AlphaOrg"},
                {"id": "org_2", "name": "NebulaCorp"},  # Page 2 via RFC 8288 Link header!
            ],
            "projects": [],  # Empty -> must recursively find NebulaCorp -> create project -> create deployment!
            "deployments": {},
        }
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "GammaCloudDeployAPI", "version": "3.0.0"},
            "security": [{"QueryKey": []}],
            "components": {
                "securitySchemes": {
                    "QueryKey": {"type": "apiKey", "in": "query", "name": "key"},
                }
            },
            "paths": {
                "/auth/token": {
                    "post": {
                        "operationId": "issueKey",
                        "security": [],
                        "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object", "properties": {"api_key": {"type": "string"}}}}}}},
                    }
                },
                "/organizations": {
                    "get": {"operationId": "listOrgs", "responses": {"200": {"description": "OK"}}},
                },
                "/projects": {
                    "get": {"operationId": "listProjects", "responses": {"200": {"description": "OK"}}},
                    "post": {
                        "operationId": "createProject",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["organization_id", "name"],
                                        "properties": {
                                            "organization_id": {"type": "string"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    },
                },
                "/deployments": {
                    "post": {
                        "operationId": "createDeployment",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["project_id", "version"],
                                        "properties": {
                                            "project_id": {"type": "string"},
                                            "version": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    }
                },
                "/deployments/{deployment_id}/status": {
                    "get": {
                        "operationId": "getDeploymentStatus",
                        "parameters": [{"name": "deployment_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {"200": {"description": "OK"}},
                    }
                },
            },
        }

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:
                return

            def _send(self, code: int, obj: Any, extra_h: dict[str, str] | None = None) -> None:
                raw = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for hk, hv in (extra_h or {}).items():
                    self.send_header(hk, hv)
                self.end_headers()
                self.wfile.write(raw)

            def _auth_ok(self, qs: dict[str, list[str]]) -> bool:
                if qs.get("key", [""])[0] != state["tok"]:
                    self._send(401, {"error": "bad_key"})
                    return False
                return True

            def do_GET(self) -> None:
                p = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(p.query)
                if p.path == "/openapi.json":
                    self._send(200, spec)
                    return
                if not self._auth_ok(qs):
                    return
                if p.path == "/organizations":
                    pg = int(qs.get("pg", ["1"])[0])
                    if pg == 1:
                        self._send(200, [state["organizations"][0]], {"Link": '</organizations?pg=2>; rel="next"'})
                    else:
                        self._send(200, [state["organizations"][1]])
                    return
                if p.path == "/projects":
                    self._send(200, state["projects"])
                    return
                if p.path.startswith("/deployments/") and p.path.endswith("/status"):
                    did = p.path.split("/")[2]
                    dep = state["deployments"].get(did)
                    if not dep:
                        self._send(404, {"error": "missing"})
                        return
                    self._send(200, {"deployment_id": did, "state": "LIVE", **dep})
                    return
                self._send(404, {"error": "not_found"})

            def do_POST(self) -> None:
                p = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(p.query)
                clen = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(clen).decode("utf-8")) if clen else {}
                if p.path == "/auth/token":
                    self._send(200, {"api_key": state["tok"]})
                    return
                if not self._auth_ok(qs):
                    return
                if p.path == "/projects":
                    rec = {"id": f"prj_{len(state['projects']) + 1}", **body}
                    state["projects"].append(rec)
                    self._send(201, rec)
                    return
                if p.path == "/deployments":
                    did = f"dep_{len(state['deployments']) + 1}"
                    rec = {"id": did, **body}
                    state["deployments"][did] = rec
                    self._send(201, rec)
                    return
                self._send(404, {"error": "not_found"})

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            model = open_model()
            # Notice: URL embedded directly in goal, NO `api_url` arg passed!
            out = model.solve(
                f"Use the OpenAPI microservice at http://127.0.0.1:{port} to create deployment version=v4.2 "
                f"with project_name=CoreEngine organization_name=NebulaCorp and check its status",
                mode="EPISTEMIC",
                inputs={"workspace": "."},
            )
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED", er)
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)
            self.assertEqual(er["authority"], "NONE")
            self.assertEqual(er["resolved_foreign_keys"], {"project_id": "prj_1"})
            self.assertEqual(state["projects"][0]["organization_id"], "org_2")
            self.assertEqual(state["projects"][0]["name"], "CoreEngine")
            self.assertEqual(er["readback"]["state"], "LIVE")
            self.assertEqual(er["readback"]["version"], "v4.2")
            # Followed RFC 8288 Link: rel="next" to page 2 of /organizations + scanned /projects!
            self.assertGreaterEqual(er["telemetry"]["pages_scanned"], 3)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
