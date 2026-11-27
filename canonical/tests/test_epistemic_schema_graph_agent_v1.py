"""Live Spider 2.0 / BIRD SchemaGraphSQL + GraphQL Introspection test suite (V1).

Tests BOTH modalities end-to-end through ONE Front Door (`open_model().solve(..., mode="EPISTEMIC")`)
with ZERO external model calls (`model_calls == 0`), ZERO stored weights (`parameters_stored == 0`),
and ZERO memorized schemas, table names, URLs, or credentials (`authority == "NONE"`):
  1. Spider 2.0 implicit-FK 4-table Steiner-BFS join + BIRD cell-value grounding + cross-DB Tier-0 transfer
  2. Live HTTP GraphQL `__schema` introspection + nested OBJECT expansion + INPUT_OBJECT mutation +
     live `Did you mean` error self-healing + cross-service Tier-0 transfer + inspectable memory deletion.
"""

from __future__ import annotations

import http.server
import json
import pathlib
import re
import sqlite3
import tempfile
import threading
import unittest
from typing import Any

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime import universal_epistemic_kernel_v1 as UEK


def _build_commerce_db_no_declared_fks(path: pathlib.Path) -> None:
    """4-table commerce DB with ZERO declared FOREIGN KEY constraints (Spider 2.0 Lite stress test)."""
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, region TEXT);
        CREATE TABLE products (id INTEGER PRIMARY KEY, title TEXT, category TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT);
        CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL);

        INSERT INTO customers VALUES (1, 'Alice', 'NA'), (2, 'Bob', 'EU'), (3, 'Cara', 'APAC');
        INSERT INTO products VALUES (10, 'Laptop', 'Electronics'), (11, 'Phone', 'Electronics'), (12, 'Desk', 'Furniture');
        INSERT INTO orders VALUES (100, 1, 'paid'), (101, 2, 'paid'), (102, 2, 'cancelled'), (103, 3, 'paid');
        INSERT INTO order_items VALUES
          (1, 100, 10, 2, 500.0),   -- Alice Electronics paid: 1000
          (2, 100, 12, 3, 200.0),   -- Alice Furniture (filtered out!)
          (3, 101, 11, 3, 400.0),   -- Bob Electronics paid: 1200
          (4, 102, 10, 5, 500.0),   -- Bob cancelled (filtered out!)
          (5, 103, 11, 1, 400.0);   -- Cara Electronics paid: 400
        """
    )
    con.commit()
    con.close()


def _build_hospital_db_beta(path: pathlib.Path) -> None:
    """Completely distinct 3-table hospital DB with declared FKs and totally different column/PK names."""
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE departments (dept_id INTEGER PRIMARY KEY, title TEXT);
        CREATE TABLE doctors (doc_id INTEGER PRIMARY KEY, dept_id INTEGER REFERENCES departments(dept_id), full_name TEXT);
        CREATE TABLE visits (visit_id INTEGER PRIMARY KEY, doc_id INTEGER REFERENCES doctors(doc_id), outcome TEXT, fee REAL);

        INSERT INTO departments VALUES (1, 'Cardiology'), (2, 'Neurology');
        INSERT INTO doctors VALUES (10, 1, 'Dr. Heart'), (11, 2, 'Dr. Brain');
        INSERT INTO visits VALUES
          (1, 10, 'completed', 300.0),
          (2, 10, 'completed', 200.0),
          (3, 10, 'cancelled', 999.0),
          (4, 11, 'completed', 750.0);
        """
    )
    con.commit()
    con.close()


def _start_graphql_service_alpha() -> tuple[http.server.ThreadingHTTPServer, str, dict[str, Any]]:
    state: dict[str, Any] = {
        "tickets": [
            {"id": "t1", "title": "Auth timeout", "status": "OPEN", "priority": "HIGH", "assignee": {"id": "u1", "handle": "maya"}},
            {"id": "t2", "title": "Old CSS bug", "status": "CLOSED", "priority": "LOW", "assignee": {"id": "u2", "handle": "liam"}},
        ],
        "purge_hits": 0,
    }
    schema_resp = {
        "data": {
            "__schema": {
                "queryType": {"name": "Query"},
                "mutationType": {"name": "Mutation"},
                "types": [
                    {
                        "kind": "OBJECT",
                        "name": "Query",
                        "fields": [
                            {
                                "name": "tickets",
                                "description": "List support tickets by status",
                                "args": [{"name": "status", "type": {"kind": "NON_NULL", "name": None, "ofType": {"kind": "ENUM", "name": "TicketStatus", "ofType": None}}}],
                                "type": {"kind": "LIST", "name": None, "ofType": {"kind": "OBJECT", "name": "Ticket", "ofType": None}},
                            }
                        ],
                    },
                    {
                        "kind": "OBJECT",
                        "name": "Mutation",
                        "fields": [
                            {
                                "name": "createTicket",
                                "description": "Create a new support ticket",
                                "args": [{"name": "input", "type": {"kind": "NON_NULL", "name": None, "ofType": {"kind": "INPUT_OBJECT", "name": "TicketInput", "ofType": None}}}],
                                "type": {"kind": "OBJECT", "name": "Ticket", "ofType": None},
                            },
                            {
                                "name": "purgeAllTickets",
                                "description": "Destructive trap: purge all tickets",
                                "args": [],
                                "type": {"kind": "SCALAR", "name": "Boolean", "ofType": None},
                            },
                        ],
                    },
                    {
                        "kind": "OBJECT",
                        "name": "Ticket",
                        "fields": [
                            {"name": "id", "args": [], "type": {"kind": "SCALAR", "name": "ID", "ofType": None}},
                            {"name": "title", "args": [], "type": {"kind": "SCALAR", "name": "String", "ofType": None}},
                            {"name": "status", "args": [], "type": {"kind": "ENUM", "name": "TicketStatus", "ofType": None}},
                            {"name": "priority", "args": [], "type": {"kind": "SCALAR", "name": "String", "ofType": None}},
                            {"name": "assignee", "args": [], "type": {"kind": "OBJECT", "name": "User", "ofType": None}},
                        ],
                    },
                    {
                        "kind": "OBJECT",
                        "name": "User",
                        "fields": [
                            {"name": "id", "args": [], "type": {"kind": "SCALAR", "name": "ID", "ofType": None}},
                            {"name": "handle", "args": [], "type": {"kind": "SCALAR", "name": "String", "ofType": None}},
                        ],
                    },
                    {
                        "kind": "INPUT_OBJECT",
                        "name": "TicketInput",
                        "inputFields": [
                            {"name": "title", "type": {"kind": "NON_NULL", "name": None, "ofType": {"kind": "SCALAR", "name": "String", "ofType": None}}},
                            {"name": "priority", "type": {"kind": "NON_NULL", "name": None, "ofType": {"kind": "SCALAR", "name": "String", "ofType": None}}},
                        ],
                    },
                    {
                        "kind": "ENUM",
                        "name": "TicketStatus",
                        "enumValues": [{"name": "OPEN"}, {"name": "CLOSED"}],
                    },
                ],
            }
        }
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send(self, code: int, obj: Any) -> None:
            raw = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self) -> None:
            clen = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(clen).decode("utf-8")) if clen else {}
            q = str(body.get("query") or "")
            if "__schema" in q:
                self._send(200, schema_resp)
                return
            if "purgeAllTickets" in q:
                state["purge_hits"] += 1
                self._send(200, {"data": {"purgeAllTickets": True}})
                return
            if "tickets(" in q:
                if "assignee {" not in q:
                    self._send(200, {"errors": [{"message": "Field 'assignee' of type 'User' must have a selection of subfields"}]})
                    return
                m_st = re.search(r"status:\s*([A-Z_]+)", q)
                st_val = m_st.group(1) if m_st else "OPEN"
                matched = [t for t in state["tickets"] if t["status"] == st_val]
                self._send(200, {"data": {"tickets": matched}})
                return
            if "createTicket(" in q:
                m_t = re.search(r'title:\s*"([^"]+)"', q)
                m_p = re.search(r'priority:\s*"([^"]+)"', q)
                title = m_t.group(1) if m_t else "Untitled"
                prio = m_p.group(1) if m_p else "LOW"
                # Deliberately reject "urgent" with GraphQL Did-You-Mean hint to verify live error self-healing!
                if prio.upper() not in ("LOW", "MEDIUM", "HIGH"):
                    self._send(200, {"errors": [{"message": f"Invalid priority value '{prio}'; expected 'HIGH'"}]})
                    return
                rec = {"id": f"t{len(state['tickets']) + 1}", "title": title, "status": "OPEN", "priority": prio, "assignee": {"id": "u1", "handle": "maya"}}
                state["tickets"].append(rec)
                self._send(200, {"data": {"createTicket": rec}})
                return
            self._send(400, {"errors": [{"message": "Unknown GraphQL operation"}]})

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{port}/graphql", state


def _start_graphql_service_beta() -> tuple[http.server.ThreadingHTTPServer, str]:
    schema_resp = {
        "data": {
            "__schema": {
                "queryType": {"name": "Query"},
                "mutationType": None,
                "types": [
                    {
                        "kind": "OBJECT",
                        "name": "Query",
                        "fields": [
                            {
                                "name": "clusters",
                                "description": "List cloud clusters in a region",
                                "args": [{"name": "region", "type": {"kind": "NON_NULL", "name": None, "ofType": {"kind": "ENUM", "name": "RegionCode", "ofType": None}}}],
                                "type": {"kind": "LIST", "name": None, "ofType": {"kind": "OBJECT", "name": "Cluster", "ofType": None}},
                            }
                        ],
                    },
                    {
                        "kind": "OBJECT",
                        "name": "Cluster",
                        "fields": [
                            {"name": "id", "args": [], "type": {"kind": "SCALAR", "name": "ID", "ofType": None}},
                            {"name": "name", "args": [], "type": {"kind": "SCALAR", "name": "String", "ofType": None}},
                            {"name": "nodes", "args": [], "type": {"kind": "OBJECT", "name": "NodeInfo", "ofType": None}},
                        ],
                    },
                    {
                        "kind": "OBJECT",
                        "name": "NodeInfo",
                        "fields": [
                            {"name": "id", "args": [], "type": {"kind": "SCALAR", "name": "ID", "ofType": None}},
                            {"name": "zone", "args": [], "type": {"kind": "SCALAR", "name": "String", "ofType": None}},
                        ],
                    },
                    {
                        "kind": "ENUM",
                        "name": "RegionCode",
                        "enumValues": [{"name": "US_EAST"}, {"name": "EU_WEST"}],
                    },
                ],
            }
        }
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def do_POST(self) -> None:
            clen = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(clen).decode("utf-8")) if clen else {}
            q = str(body.get("query") or "")
            resp = (
                schema_resp
                if "__schema" in q
                else {"data": {"clusters": [{"id": "c1", "name": "prod-eu", "nodes": {"id": "n1", "zone": "eu-west-1a"}}]}}
            )
            raw = json.dumps(resp).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{port}/graphql"


class EpistemicSchemaGraphAgentV1Tests(unittest.TestCase):
    def test_01_spider2_implicit_fk_4table_join_and_cross_db_tier0_transfer(self) -> None:
        """Spider 2.0 / BIRD zero-prior SQLite SchemaGraphSQL via ONE Front Door:
        4-table implicit-FK join (ZERO declared FKs) + BIRD cell-value grounding +
        persisted cross-DB Tier-0 polymorphic skill transfer + destructive-SQL guard + deletion."""
        model = open_model()
        mem = UEK.new_universal_memory()

        with tempfile.TemporaryDirectory(prefix="epistemic_sql_") as td:
            base = pathlib.Path(td)
            db_a = base / "commerce_alpha.db"
            db_b = base / "hospital_beta.db"
            _build_commerce_db_no_declared_fks(db_a)
            _build_hospital_db_beta(db_b)

            # 1. Cold run on DB Alpha (ZERO declared FKs -> Spider 2.0 implicit joinability discovery!)
            out_a = model.solve(
                "Find the top 2 customers by total revenue for Electronics orders with status 'paid'",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_a), "memory": mem},
            )
            er_a = out_a["epistemic_result"]
            self.assertEqual(er_a["status"], "VERIFIED", er_a)
            self.assertEqual(er_a["mode"], "EPISTEMIC_SCHEMA_GRAPH_SQL_SOLVED")
            self.assertEqual(er_a["model_calls"], 0)
            self.assertEqual(er_a["parameters_stored"], 0)
            self.assertEqual(er_a["authority"], "NONE")
            self.assertEqual(er_a["telemetry"]["edges_declared"], 0)
            self.assertGreaterEqual(er_a["telemetry"]["edges_inferred_implicit_fk"], 3)
            self.assertEqual(er_a["telemetry"]["join_hops"], 3)
            self.assertTrue(er_a["telemetry"]["used_implicit_fk"])
            self.assertEqual(
                er_a["rows"],
                [
                    {"group_key": "Bob", "metric_value": 1200.0},
                    {"group_key": "Alice", "metric_value": 1000.0},
                ],
            )
            # Verify zero-table/zero-column/zero-value memory hygiene!
            sk_a = er_a["distilled_poly_skill"]
            sk_blob = json.dumps(sk_a)
            for forbidden in ("customers", "orders", "Electronics", "Bob", "Alice", "unit_price"):
                self.assertNotIn(forbidden, sk_blob)
            self.assertFalse(sk_a["contains_tables_columns_or_values"])

            # 2. Save memory to JSON -> reload -> Tier-0 transfer onto COMPLETELY UNSEEN Hospital DB Beta!
            mpath = base / "mem.json"
            UEK.save_universal_memory(mem, mpath)
            mem2 = UEK.load_universal_memory(mpath)

            out_b = model.solve(
                "Compute total fee per department for visits with outcome 'completed'",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_b), "memory": mem2},
            )
            er_b = out_b["epistemic_result"]
            self.assertEqual(er_b["status"], "VERIFIED", er_b)
            self.assertEqual(er_b["mode"], "TIER0_SQL_POLY_SKILL")
            self.assertTrue(er_b["telemetry"]["tier0_poly_skill_used"])
            self.assertEqual(er_b["telemetry"]["tier0_skill_id"], sk_a["skill_id"])
            self.assertEqual(
                er_b["rows"],
                [
                    {"group_key": "Neurology", "metric_value": 750.0},
                    {"group_key": "Cardiology", "metric_value": 500.0},
                ],
            )

            # 3. Destructive SQL safety guard blocks DROP TABLE
            out_bad = model.solve("DROP TABLE visits", mode="EPISTEMIC", inputs={"db_path": str(db_b)})
            self.assertEqual(out_bad["epistemic_result"]["mode"], "DESTRUCTIVE_SQL_BLOCKED")

            # 4. Inspectable deletion removes the SQL poly skill cleanly
            self.assertTrue(UEK.delete_memory_entry(mem2, sk_a["skill_id"]))
            self.assertNotIn(sk_a["skill_id"], mem2["sql_poly_skills"])

    def test_02_live_graphql_introspection_nested_query_mutation_selfheal_and_transfer(self) -> None:
        """Live HTTP GraphQL `__schema` introspection -> 100% schema-valid nested Query +
        INPUT_OBJECT Mutation with live error self-healing -> cross-endpoint Tier-0 transfer."""
        srv_a, url_a, state_a = _start_graphql_service_alpha()
        srv_b, url_b = _start_graphql_service_beta()
        try:
            model = open_model()
            mem = UEK.new_universal_memory()

            # 1. Nested Query on Service Alpha (URL auto-detected right out of plain goal!)
            out_q = model.solve(
                f"Query GraphQL at {url_a} for open tickets including assignee details",
                mode="EPISTEMIC",
                inputs={"workspace": ".", "memory": mem},
            )
            er_q = out_q["epistemic_result"]
            self.assertEqual(er_q["status"], "VERIFIED", er_q)
            self.assertEqual(er_q["mode"], "EPISTEMIC_GRAPHQL_INTROSPECTION_SOLVED")
            self.assertEqual(er_q["model_calls"], 0)
            self.assertEqual(er_q["parameters_stored"], 0)
            self.assertEqual(er_q["authority"], "NONE")
            self.assertTrue(er_q["telemetry"]["schema_compliant_by_construction"])
            self.assertEqual(len(er_q["data"]["tickets"]), 1)
            self.assertEqual(er_q["data"]["tickets"][0]["assignee"]["handle"], "maya")

            # 2. INPUT_OBJECT Mutation + live error self-healing (`urgent` -> `HIGH`), zero destructive hits!
            out_m = model.solve(
                'Create ticket title="Router down" priority=urgent',
                mode="EPISTEMIC",
                inputs={"graphql_url": url_a, "memory": mem},
            )
            er_m = out_m["epistemic_result"]
            self.assertEqual(er_m["status"], "VERIFIED", er_m)
            self.assertEqual(er_m["operation_kind"], "mutation")
            self.assertGreaterEqual(er_m["telemetry"]["self_heals"], 1)
            self.assertEqual(er_m["data"]["createTicket"]["priority"], "HIGH")
            self.assertEqual(er_m["data"]["createTicket"]["title"], "Router down")
            self.assertEqual(state_a["purge_hits"], 0)

            # Verify zero-URL / zero-field / zero-value memory hygiene!
            sk_q = er_q["distilled_poly_skill"]
            sk_blob = json.dumps(sk_q)
            for forbidden in ("127.0.0.1", "tickets", "assignee", "maya", "Router"):
                self.assertNotIn(forbidden, sk_blob)
            self.assertFalse(sk_q["contains_urls_fields_or_values"])

            # 3. Cross-endpoint Tier-0 transfer onto COMPLETELY UNSEEN GraphQL Service Beta!
            out_b = model.solve(
                "List eu_west clusters and their nodes",
                mode="EPISTEMIC",
                inputs={"graphql_url": url_b, "memory": mem},
            )
            er_b = out_b["epistemic_result"]
            self.assertEqual(er_b["status"], "VERIFIED", er_b)
            self.assertEqual(er_b["mode"], "TIER0_GRAPHQL_POLY_SKILL")
            self.assertTrue(er_b["telemetry"]["tier0_poly_skill_used"])
            self.assertEqual(er_b["data"]["clusters"][0]["nodes"]["zone"], "eu-west-1a")

            # 4. Inspectable deletion removes GraphQL skill cleanly without retraining
            self.assertTrue(UEK.delete_memory_entry(mem, sk_q["skill_id"]))
            self.assertNotIn(sk_q["skill_id"], mem["graphql_poly_skills"])
        finally:
            srv_a.shutdown()
            srv_a.server_close()
            srv_b.shutdown()
            srv_b.server_close()

    def test_03_sql_5table_chain_avg_numeric_filter_and_graphql_5of5_reliability(self) -> None:
        """5-table 4-hop SchemaGraphSQL chain (`orgs->workspaces->projects->runs->metrics`) with
        AVG + numeric `>` predicate + COUNT, plus 5/5 (100%) deterministic GraphQL reliability."""
        model = open_model()
        with tempfile.TemporaryDirectory(prefix="epistemic_sql5_") as td:
            db_c = pathlib.Path(td) / "saas_5table.db"
            con = sqlite3.connect(str(db_c))
            con.executescript(
                """
                CREATE TABLE orgs (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE workspaces (id INTEGER PRIMARY KEY, org_id INTEGER, title TEXT);
                CREATE TABLE projects (id INTEGER PRIMARY KEY, workspace_id INTEGER, slug TEXT);
                CREATE TABLE runs (id INTEGER PRIMARY KEY, project_id INTEGER, env TEXT);
                CREATE TABLE metrics (id INTEGER PRIMARY KEY, run_id INTEGER, latency REAL);

                INSERT INTO orgs VALUES (1, 'Acme'), (2, 'Globex');
                INSERT INTO workspaces VALUES (10, 1, 'Core'), (20, 2, 'Lab');
                INSERT INTO projects VALUES (100, 10, 'api'), (200, 20, 'ml');
                INSERT INTO runs VALUES (1000, 100, 'prod'), (2000, 200, 'prod');
                INSERT INTO metrics VALUES
                  (1, 1000, 20.0),   -- filtered out (<= 50)
                  (2, 1000, 100.0),  -- Acme prod > 50
                  (3, 1000, 200.0),  -- Acme prod > 50 -> AVG = 150.0
                  (4, 2000, 80.0);   -- Globex prod > 50 -> AVG = 80.0
                """
            )
            con.commit()
            con.close()

            out_avg = model.solve(
                "Find average latency per org for prod runs with latency > 50",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_c)},
            )
            er_avg = out_avg["epistemic_result"]
            self.assertEqual(er_avg["status"], "VERIFIED", er_avg)
            self.assertEqual(er_avg["telemetry"]["join_hops"], 4)
            self.assertEqual(er_avg["telemetry"]["edges_declared"], 0)
            self.assertEqual(
                er_avg["rows"],
                [
                    {"group_key": "Acme", "metric_value": 150.0},
                    {"group_key": "Globex", "metric_value": 80.0},
                ],
            )

        # GraphQL 5/5 reliability across 5 consecutive fresh invocations (0% variance)
        srv_b, url_b = _start_graphql_service_beta()
        try:
            passes = 0
            for _ in range(5):
                r = model.solve(
                    "List eu_west clusters and their nodes",
                    mode="EPISTEMIC",
                    inputs={"graphql_url": url_b},
                )
                er = r["epistemic_result"]
                if er["status"] == "VERIFIED" and er["data"]["clusters"][0]["nodes"]["zone"] == "eu-west-1a":
                    passes += 1
            self.assertEqual(passes, 5)
        finally:
            srv_b.shutdown()
            srv_b.server_close()

    def test_04_clbench_latent_conventions_zero_probe_reuse_drift_and_unlearning(self) -> None:
        """CL-BENCH (2606.05661) + AgentCL (2606.02461) Continual DB Learning:
        1. Joint single-experience counterexample abduction of hidden cents scale (0.01) +
           hidden excluded status ('voided') + automatic soft-delete filtering (`is_deleted = 0`).
        2. Tier-0 zero-exploration (`exploratory_queries == 0`) transfer to unseen GROUP BY query.
        3. Zero negative transfer (AgentCL Generalization Gain >= 0) on independent unseen DB B.
        4. Live schema-version drift (`ALTER TABLE`) + live convention drift (cents -> dollars) quarantine.
        5. Zero-weight instant unlearning via `UEK.delete_memory_entry`.
        """
        from canonical.runtime import universal_epistemic_kernel_v1 as uek

        model = open_model()
        mem = uek.new_universal_memory()

        with tempfile.TemporaryDirectory() as td:
            tdp = pathlib.Path(td)
            db_a = tdp / "clbench_ledger_a.sqlite"
            con_a = sqlite3.connect(str(db_a))
            con_a.executescript(
                """
                CREATE TABLE customers (
                    customer_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    region TEXT NOT NULL
                );
                CREATE TABLE invoices (
                    invoice_id INTEGER PRIMARY KEY,
                    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
                    subtotal REAL NOT NULL,
                    state TEXT NOT NULL,
                    is_deleted INTEGER NOT NULL DEFAULT 0
                );
                INSERT INTO customers VALUES
                    (1, 'Northstar', 'EMEA'),
                    (2, 'Sunbelt', 'AMER');
                INSERT INTO invoices VALUES
                    (10, 1, 12500, 'settled', 0),
                    (11, 1, 25000, 'settled', 0),
                    (12, 1, 99900, 'voided', 0),
                    (13, 1, 50000, 'settled', 1),
                    (14, 2, 10000, 'settled', 0),
                    (15, 2, 40000, 'voided', 0);
                """
            )
            con_a.commit()
            con_a.close()

            # Episode 1: Cold start on unseen DB A with BOTH hidden cents (0.01) AND hidden 'voided' exclusion!
            # Expected EMEA settled non-deleted subtotal = (12500 + 25000) * 0.01 = 375.00
            def _ver_ep1(rows: list[dict[str, object]]) -> dict[str, object]:
                val = rows[0].get("metric_value") if rows else None
                ok = isinstance(val, (int, float)) and abs(float(val) - 375.0) < 1e-6
                return {"pass": ok, "expected_value": 375.0}

            out1 = model.solve(
                "What is the total subtotal of invoices for EMEA?",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_a), "memory": mem, "verifier": _ver_ep1},
            )
            er1 = out1["epistemic_result"]
            self.assertEqual(er1["status"], "VERIFIED", er1)
            self.assertEqual(er1["model_calls"], 0)
            self.assertEqual(er1["parameters_stored"], 0)
            self.assertGreater(er1["telemetry"]["exploratory_queries"], 0)
            self.assertAlmostEqual(float(er1["rows"][0]["metric_value"]), 375.0, places=6)
            ab_kinds = {a["kind"] for a in er1["telemetry"]["abduced_conventions"]}
            self.assertEqual(ab_kinds, {"STATUS_EXCLUSION_CONVENTION", "SCALE_CONVENTION"})
            db_law_id = er1["telemetry"]["db_law_id"]
            self.assertIn(db_law_id, mem["db_schema_laws"])

            # Episode 2: Unseen GROUP BY query across customers -> invoices on DB A!
            # Must use 0 exploratory queries and apply BOTH learned conventions on attempt 1 (NO verifier!).
            out2 = model.solve(
                "What is the total subtotal per region?",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_a), "memory": mem},
            )
            er2 = out2["epistemic_result"]
            self.assertEqual(er2["status"], "VERIFIED", er2)
            self.assertEqual(er2["telemetry"]["exploratory_queries"], 0)
            self.assertTrue(er2["telemetry"]["schema_cache_hit"])
            self.assertEqual(er2["telemetry"]["answer_queries"], 1)
            self.assertEqual(er2["telemetry"]["drift_quarantines"], 0)
            by_region = {r["group_key"]: round(float(r["metric_value"]), 2) for r in er2["rows"]}
            self.assertEqual(by_region, {"EMEA": 375.0, "AMER": 100.0})

            # Episode 3: AgentCL Generalization / Stability — independent unseen DB B in whole dollars!
            # Must NOT suffer negative transfer from DB A's 0.01 scale or 'voided' exclusion.
            db_b = tdp / "clbench_ledger_b.sqlite"
            con_b = sqlite3.connect(str(db_b))
            con_b.executescript(
                """
                CREATE TABLE payments (
                    payment_id INTEGER PRIMARY KEY,
                    amount REAL NOT NULL,
                    state TEXT NOT NULL
                );
                INSERT INTO payments VALUES
                    (1, 200.0, 'settled'),
                    (2, 50.0, 'voided');
                """
            )
            con_b.commit()
            con_b.close()

            out3 = model.solve(
                "What is the total amount of payments?",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_b), "memory": mem},
            )
            er3 = out3["epistemic_result"]
            self.assertEqual(er3["status"], "VERIFIED", er3)
            self.assertAlmostEqual(float(er3["rows"][0]["metric_value"]), 250.0, places=6)

            # Episode 4a: Live schema-version drift on DB A (`ALTER TABLE`) -> schema drift quarantine + re-introspect
            con_a2 = sqlite3.connect(str(db_a))
            con_a2.execute("ALTER TABLE customers ADD COLUMN tier TEXT DEFAULT 'enterprise'")
            con_a2.commit()
            con_a2.close()

            out4a = model.solve(
                "What is the total subtotal per region?",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_a), "memory": mem},
            )
            er4a = out4a["epistemic_result"]
            self.assertEqual(er4a["status"], "VERIFIED", er4a)
            self.assertEqual(er4a["telemetry"]["drift_quarantines"], 1)
            self.assertFalse(er4a["telemetry"]["schema_cache_hit"])
            self.assertGreater(er4a["telemetry"]["exploratory_queries"], 0)
            # Compatible conventions preserved across additive schema migration!
            by_region_4a = {r["group_key"]: round(float(r["metric_value"]), 2) for r in er4a["rows"]}
            self.assertEqual(by_region_4a, {"EMEA": 375.0, "AMER": 100.0})

            # Episode 4b: Live convention drift on DB A (subtotal migrated from cents -> whole dollars!)
            con_a3 = sqlite3.connect(str(db_a))
            con_a3.execute("UPDATE invoices SET subtotal = subtotal / 100.0")
            con_a3.commit()
            con_a3.close()

            out4b = model.solve(
                "What is the total subtotal of invoices for EMEA?",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_a), "memory": mem, "verifier": _ver_ep1},
            )
            er4b = out4b["epistemic_result"]
            self.assertEqual(er4b["status"], "VERIFIED", er4b)
            self.assertEqual(er4b["telemetry"]["drift_quarantines"], 1)
            self.assertAlmostEqual(float(er4b["rows"][0]["metric_value"]), 375.0, places=6)
            self.assertAlmostEqual(float(mem["db_schema_laws"][db_law_id]["scale_laws"]["invoices.subtotal"]), 1.0, places=6)

            # Episode 5: Post-drift Tier-0 reuse (`exploratory_queries == 0`, new scale 1.0 active!)
            out5 = model.solve(
                "What is the total subtotal per region?",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_a), "memory": mem},
            )
            er5 = out5["epistemic_result"]
            self.assertEqual(er5["status"], "VERIFIED", er5)
            self.assertEqual(er5["telemetry"]["exploratory_queries"], 0)
            self.assertTrue(er5["telemetry"]["schema_cache_hit"])
            by_region_5 = {r["group_key"]: round(float(r["metric_value"]), 2) for r in er5["rows"]}
            self.assertEqual(by_region_5, {"EMEA": 375.0, "AMER": 100.0})

            # Episode 6: Zero-weight instant unlearning via UEK.delete_memory_entry
            deleted = uek.delete_memory_entry(mem, db_law_id)
            self.assertTrue(deleted)
            self.assertNotIn(db_law_id, mem["db_schema_laws"])
            out6 = model.solve(
                "What is the total subtotal per region?",
                mode="EPISTEMIC",
                inputs={"db_path": str(db_a), "memory": mem},
            )
            er6 = out6["epistemic_result"]
            self.assertEqual(er6["status"], "VERIFIED", er6)
            self.assertFalse(er6["telemetry"]["schema_cache_hit"])
            self.assertGreater(er6["telemetry"]["exploratory_queries"], 0)


if __name__ == "__main__":
    unittest.main()
