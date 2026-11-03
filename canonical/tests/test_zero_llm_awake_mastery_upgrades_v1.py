#!/usr/bin/env python3
"""End-to-end + sabotage falsification suite for the 4 Zero-LLM (`K3 = 0`) Awake Mastery Upgrades."""
from __future__ import annotations

import os
import pathlib
import sqlite3
import tempfile
import time
import uuid

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import ignorance_ledger_v1 as ledger
from canonical.runtime import live_brain_route_admission_v1 as ra
from canonical.swe_kernel import operator_generalization_v1 as op_gen
from canonical.swe_kernel import rule_expiry_v1 as rule_exp
from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
    compile_and_qualify_skill,
    recall_and_execute_workflow,
)
from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn
from canonical.swe_kernel.predicate_world_abstraction_v1 import (
    explore_and_elevate_computer_env,
    project_computer_observation,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore


def test_move1_single_trace_auto_twin_qualification_and_sabotage_rejection() -> None:
    with tempfile.TemporaryDirectory() as td:
        td_p = pathlib.Path(td)
        wf_db = td_p / "wf.sqlite"
        ep1 = td_p / "ep1"
        ep1.mkdir()
        db1 = ep1 / "ops.db"
        with sqlite3.connect(db1) as c:
            c.execute("CREATE TABLE services(name TEXT PRIMARY KEY, tier TEXT)")
            c.execute("INSERT INTO services VALUES('payments', 'canary')")
            c.commit()

        # Unconfined automatic controller fails closed per #6592
        r_unconf = solve_or_learn(
            {
                "goal": 'promote service "payments" in ops.db',
                "acquisition_trace": [
                    {"layer": "pixel_ui", "x": 40, "y": 50, "label": "click_row"},
                    {
                        "layer": "sqlite_exec",
                        "db_path": "ops.db",
                        "sql": "UPDATE services SET tier='prod' WHERE name='payments'",
                    },
                ],
                "postcondition": {
                    "kind": "sqlite_query_equals",
                    "db_path": "ops.db",
                    "sql": "SELECT tier FROM services WHERE name='payments'",
                    "equals": "prod",
                },
                "cwd": str(ep1),
            },
            db_path=wf_db,
        )
        assert r_unconf["pass"] is False
        assert r_unconf["status"] == "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"

        # Single trace (N=1, no heldout_goal!) -> auto-twin synthesizes perturbed DB & qualifies!
        r1 = compile_and_qualify_skill(
            goal='promote service "payments" in ops.db',
            trace=[
                {"layer": "pixel_ui", "x": 40, "y": 50, "label": "click_row"},
                {
                    "layer": "sqlite_exec",
                    "db_path": "ops.db",
                    "sql": "UPDATE services SET tier='prod' WHERE name='payments'",
                },
            ],
            postcondition={
                "kind": "sqlite_query_equals",
                "db_path": "ops.db",
                "sql": "SELECT tier FROM services WHERE name='payments'",
                "equals": "prod",
            },
            auto_synthesize_twin=True,
            source_cwd=ep1,
            db_path=wf_db,
        )
        assert r1["pass"] is True, r1

        # Unseen target replays from compiled Tier-0 memory in milliseconds!
        ep2 = td_p / "ep2"
        ep2.mkdir()
        db2 = ep2 / "ops.db"
        with sqlite3.connect(db2) as c:
            c.execute("CREATE TABLE services(name TEXT PRIMARY KEY, tier TEXT)")
            c.execute("INSERT INTO services VALUES('analytics', 'canary')")
            c.commit()

        t0 = time.perf_counter()
        r2 = recall_and_execute_workflow(
            'promote service "analytics" in ops.db',
            cwd=ep2,
            db_path=wf_db,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert r2 is not None and r2["pass"] is True
        assert elapsed_ms < 50.0

        # Negative falsifier: parameter-free / ungeneralizable trace MUST fail closed on auto-twin!
        bad = compile_and_qualify_skill(
            goal="run fixed static task",
            trace=[{"layer": "python_file_op", "op": "write_text", "path": "fixed.txt", "content": "ok"}],
            postcondition={"kind": "file_contains", "path": "fixed.txt", "needle": "ok"},
            auto_synthesize_twin=True,
            source_cwd=ep1,
            db_path=wf_db,
        )
        assert bad["pass"] is False


def test_move2a_constructor_table_free_metamorphic_cli_signatures() -> None:
    saved_kinds = dict(cenv._PROBE_KINDS)
    saved_bytes = cenv.probe_bytes
    try:
        cenv._PROBE_KINDS.clear()
        cenv.probe_bytes = None  # Force zero constructor-table fallback!
        with tempfile.TemporaryDirectory() as td:
            f = pathlib.Path(td) / "data.txt"
            f.write_text("alpha beta\n\nalpha beta\ngamma\n\nlongest_line_in_file_xyz\n", encoding="utf-8")

            r_total = cenv.answer_query(f"count the lines in {f}", f)
            r_nonempty = cenv.answer_query(f"count the non-empty lines in {f}", f)
            r_blank = cenv.answer_query(f"count the blank lines in {f}", f)
            r_uniq = cenv.answer_query(f"count the unique lines in {f}", f)
            r_maxlen = cenv.answer_query(f"what is the length of the longest line in {f}", f)
            r_cached = cenv.answer_query(f"count the non-empty lines in {f}", f)

            assert r_total["pass"] and int(r_total["answer"]) == 6
            assert r_nonempty["pass"] and int(r_nonempty["answer"]) == 4
            assert r_blank["pass"] and int(r_blank["answer"]) == 2
            assert r_uniq["pass"] and int(r_uniq["answer"]) == 4
            assert r_maxlen["pass"] and int(r_maxlen["answer"]) == 24
            assert r_cached["pass"] and r_cached.get("from_memory") is True
    finally:
        cenv._PROBE_KINDS.clear()
        cenv._PROBE_KINDS.update(saved_kinds)
        cenv.probe_bytes = saved_bytes


def test_move2b_egraph_congruence_closed_algebraic_rule_generalization() -> None:
    def _twin_oracle(cand: str) -> bool:
        ns: dict[str, object] = {}
        try:
            exec(compile(cand, "<twin>", "exec"), ns)
            fn = next(
                v for k, v in ns.items()
                if k != "__builtins__" and callable(v) and not isinstance(v, type)
            )
            return abs(fn(100.0, 0.2) - 80.0) < 1e-6 and abs(fn(50.0, 0.1) - 45.0) < 1e-6
        except Exception:
            return False

    def _exec_check(cand: str, assertion: str) -> bool:
        ns: dict[str, object] = {}
        try:
            exec(compile(cand, "<cand>", "exec"), ns)
            exec(compile(assertion, "<assert>", "exec"), ns)
            return True
        except Exception:
            return False

    with tempfile.TemporaryDirectory() as td:
        from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle

        base = pathlib.Path(td)
        scope_id = "test/arithmetic-egraph/v1"
        contract = {
            "schema_version": 1,
            "scope_id": scope_id,
            "verification_kind": "TEST_SUITE",
            "dependencies": {},
            "preconditions": {},
        }
        train_dir = base / "train"
        train_dir.mkdir(parents=True, exist_ok=True)
        (train_dir / "subject.py").write_text("def total(p, t):\n    return p + p * t\n", encoding="utf-8")
        (train_dir / "test_subject.py").write_text(
            "import unittest\nfrom subject import total\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertAlmostEqual(total(100, 0.2), 80.0)\n"
            "        self.assertAlmostEqual(total(50, 0.1), 45.0)\n",
            encoding="utf-8",
        )
        store = VerifiedSkillStore(base / "skills.sqlite", seed=False)
        # Multi-token structural lesson (`p + p * t` -> `p * (1 - t)`): beyond 1-token operator swap!
        cryst = store.crystallize_code_fix(
            before_snippet="def total(p, t):\n    return p + p * t\n",
            after_snippet="def total(p, t):\n    return p * (1 - t)\n",
            language="python",
            error_class="ARITHMETIC",
            contract=contract,
            training_verifier=ProjectTestOracle(train_dir, "subject.py", ["test_subject.py"], scope_id),
        )
        assert cryst["crystallized"] is True
        rule = store.lookup_rules("python", "ARITHMETIC")[0]
        assert op_gen.derive_operator_swap(rule) is None

        shapes = [
            ("s1", "def target(price, disc):\n    return price * (1 + disc)\n", "self.assertAlmostEqual(target(200, 0.25), 150.0)"),
            ("s2", "def target(base, rate):\n    return (1.0 + rate) * base\n", "self.assertAlmostEqual(target(80, 0.1), 72.0)"),
            ("s3", "def target(sub, fee):\n    out = fee * sub + sub\n    return round(out, 4)\n", "self.assertEqual(target(100, 0.15), 85.0)"),
            (
                "s4",
                "class Quote:\n    def __init__(self, v):\n        self.v = v\n    def due(self, r):\n        return self.v * (1 + r)\n"
                "def target(v, r):\n    return Quote(v).due(r)\n",
                "self.assertAlmostEqual(target(50, 0.2), 40.0)",
            ),
        ]
        for label, src, check_stmt in shapes:
            sdir = base / f"case_{label}"
            sdir.mkdir(parents=True, exist_ok=True)
            (sdir / "subject.py").write_text(src, encoding="utf-8")
            (sdir / "test_subject.py").write_text(
                "import unittest\nfrom subject import target\n"
                "class T(unittest.TestCase):\n"
                f"    def test_a(self):\n        {check_stmt}\n",
                encoding="utf-8",
            )
            hit = store.recall_and_apply_verified(
                source_text=src,
                language="python",
                error_class="ARITHMETIC",
                verifier=ProjectTestOracle(sdir, "subject.py", ["test_subject.py"], scope_id),
                required_verification_kind="TEST_SUITE",
                scope_id=scope_id,
                context={"dependencies": {}, "preconditions": {}},
                allow_scope_escalation=True,
            )
            assert hit is not None and hit["scope_tier"] == "SCOPE_ALGEBRAIC"

        # Negative falsifier: opposite-spec ProjectTestOracle never admits an algebraic rewrite
        neg_dir = base / "neg_case"
        neg_dir.mkdir(parents=True, exist_ok=True)
        (neg_dir / "subject.py").write_text("def target(price, disc):\n    return price * (1 + disc)\n", encoding="utf-8")
        (neg_dir / "test_subject.py").write_text(
            "import unittest\nfrom subject import target\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n"
            "        self.assertAlmostEqual(target(200, 0.25), 250.0)\n",
            encoding="utf-8",
        )
        rejected = store.recall_and_apply_verified(
            source_text="def target(price, disc):\n    return price * (1 + disc)\n",
            language="python",
            error_class="ARITHMETIC",
            verifier=ProjectTestOracle(neg_dir, "subject.py", ["test_subject.py"], scope_id),
            required_verification_kind="TEST_SUITE",
            scope_id=scope_id,
            context={"dependencies": {}, "preconditions": {}},
            allow_scope_escalation=True,
        )
        assert rejected is None


def test_move3_predicate_world_abstraction_and_ui_elevation() -> None:
    # Verify CNF predicate projection + volatile key stripping
    proj = project_computer_observation(
        {"authed": True, "ready": False, "timestamp": 123456789, "csrf_token": "abc"},
        cnf_predicates=[
            {"name": "can_submit", "definition_cnf": [["authed"], ["!ready"]]}
        ],
    )
    assert proj == {"can_submit": True}

    class NoisySurface:
        def __init__(self, db_path: pathlib.Path, svc: str) -> None:
            self.db_path = db_path
            self.svc = svc
            self.screen = "landing"
            self.logged_in = False
            with sqlite3.connect(self.db_path) as c:
                c.execute("CREATE TABLE IF NOT EXISTS rel(svc TEXT PRIMARY KEY, st TEXT)")
                c.execute("INSERT OR REPLACE INTO rel VALUES(?, 'pending')", (self.svc,))
                c.commit()

        def reset(self) -> None:
            self.screen = "landing"
            self.logged_in = False
            with sqlite3.connect(self.db_path) as c:
                c.execute("UPDATE rel SET st='pending' WHERE svc=?", (self.svc,))
                c.commit()

        def act(self, action: str) -> None:
            if action == "goto_auth":
                self.screen = "auth"
            elif action == "login" and self.screen == "auth":
                self.logged_in = True
                self.screen = "panel"
            elif action == "ship" and self.logged_in and self.screen == "panel":
                with sqlite3.connect(self.db_path) as c:
                    c.execute("UPDATE rel SET st='shipped' WHERE svc=?", (self.svc,))
                    c.commit()
                self.screen = "done"

        def shipped(self) -> bool:
            with sqlite3.connect(self.db_path) as c:
                r = c.execute("SELECT st FROM rel WHERE svc=?", (self.svc,)).fetchone()
                return bool(r and r[0] == "shipped")

        def state(self) -> dict[str, object]:
            return {
                "request_id": str(uuid.uuid4()),
                "timestamp": time.time_ns(),
                "latency_ms": (time.time_ns() % 53) * 0.1,
                "html": (
                    f"<html><title>{self.screen}</title>"
                    f"<body data-state='{self.screen}:{'shipped' if self.shipped() else 'pending'}'>"
                    f"<form action='/{self.screen}' method='post'>"
                    f"<input type='hidden' name='csrf_token' value='{uuid.uuid4().hex}'>"
                    f"</form></body></html>"
                ),
            }

    def is_shipped(obs: object) -> bool:
        return "done:shipped" in str(obs)

    with tempfile.TemporaryDirectory() as td:
        td_p = pathlib.Path(td)
        old_exp = os.environ.get("BRAIN_EXPERIENCE_FILE")
        os.environ["BRAIN_EXPERIENCE_FILE"] = str(td_p / "exp.json")
        try:
            s1_dir = td_p / "s1"
            s1_dir.mkdir()
            s1 = NoisySurface(s1_dir / "rel.db", "core_api")
            r1 = explore_and_elevate_computer_env(
                s1,
                ["goto_auth", "login", "ship", "noop"],
                is_goal=is_shipped,
                goal_text='ship release "core_api" in rel.db',
                postcondition={
                    "kind": "sqlite_query_equals",
                    "db_path": "rel.db",
                    "sql": "SELECT st FROM rel WHERE svc='core_api'",
                    "equals": "shipped",
                },
                extract_trace=lambda _e, _p: (
                    _e.reset()
                    or [
                        {"kind": "pixel_click", "x": 10, "y": 10, "label": "goto_auth"},
                        {"kind": "sql_exec", "db_path": "rel.db", "sql": "UPDATE rel SET st='shipped' WHERE svc='core_api'"},
                    ]
                ),
                budget=32,
                max_depth=5,
                skill_db=td_p / "wf.sqlite",
                source_cwd=s1_dir,
            )
            assert r1["pass"] and r1["plan"] == ["goto_auth", "login", "ship"]
            assert r1["elevated_skill"]["pass"] is True

            # 1-trial transfer on second noisy surface
            s2_dir = td_p / "s2"
            s2_dir.mkdir()
            s2 = NoisySurface(s2_dir / "rel.db", "edge_proxy")
            r2 = explore_and_elevate_computer_env(
                s2, ["goto_auth", "login", "ship", "noop"], is_goal=is_shipped, budget=32
            )
            assert r2["pass"] and r2.get("transferred") is True and r2["trials_spent"] == 1

            # Direct <50 ms protocol replay on third surface (+ #6592 unconfined controller check)
            s3_dir = td_p / "s3"
            s3_dir.mkdir()
            s3 = NoisySurface(s3_dir / "rel.db", "worker_bus")
            r3_unconf = solve_or_learn(
                {
                    "goal": 'ship release "worker_bus" in rel.db',
                    "postcondition": {
                        "kind": "sqlite_query_equals",
                        "db_path": "rel.db",
                        "sql": "SELECT st FROM rel WHERE svc='worker_bus'",
                        "equals": "shipped",
                    },
                    "cwd": str(s3_dir),
                },
                db_path=td_p / "wf.sqlite",
            )
            assert r3_unconf["pass"] is False
            assert r3_unconf["status"] == "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"
            r3 = recall_and_execute_workflow(
                'ship release "worker_bus" in rel.db',
                cwd=s3_dir,
                db_path=td_p / "wf.sqlite",
            )
            assert r3 is not None and r3["pass"] and s3.shipped()
        finally:
            if old_exp is None:
                os.environ.pop("BRAIN_EXPERIENCE_FILE", None)
            else:
                os.environ["BRAIN_EXPERIENCE_FILE"] = old_exp


def test_move4_continuous_zero_llm_awake_agency_daemon_and_rule_expiry() -> None:
    with tempfile.TemporaryDirectory() as td:
        td_p = pathlib.Path(td)
        ledger_p = td_p / "ledger.json"
        skills_p = td_p / "skills.sqlite"
        wf_p = td_p / "wf.sqlite"

        ws1 = td_p / "ws1"
        ws1.mkdir()
        (ws1 / "Makefile").write_text("verify:\n\tabsent_verifier_cli_777 --all\n", encoding="utf-8")
        (ws1 / "billing.py").write_text("def apply_discount(p, t):\n    return p + p * t\n", encoding="utf-8")
        (ws1 / "test_billing.py").write_text(
            "from billing import apply_discount\n"
            "def test_disc():\n"
            "    assert abs(apply_discount(100.0, 0.2) - 80.0) < 1e-6\n"
            "    assert abs(apply_discount(50.0, 0.1) - 45.0) < 1e-6\n"
            "if __name__ == '__main__':\n"
            "    test_disc()\n",
            encoding="utf-8",
        )

        daemon = AwakeAgencyDaemon(
            ws1,
            ledger_path=ledger_p,
            skill_store_path=skills_p,
            workflow_db_path=wf_p,
            apply_verified_repairs=True,
        )
        p1 = daemon.pulse(channels=("solve",))
        assert p1["k3_external_llm_calls"] == 0
        assert p1["sensed"]["missing_commands"] >= 1
        assert p1["cow_experimentation"]["repaired"] == 1
        sid = p1["cow_experimentation"]["repairs"][0]["skill_id"]
        assert sid and rule_exp.usable(skills_p, sid) is True

        # Transfer autonomously to unseen workspace via live_brain_route_admission_v1.awake_pulse
        ws2 = td_p / "ws2"
        ws2.mkdir()
        (ws2 / "invoice.py").write_text("def net_due(amt, r):\n    return amt * (1.0 + r)\n", encoding="utf-8")
        (ws2 / "test_invoice.py").write_text(
            "from invoice import net_due\n"
            "def test_net():\n"
            "    assert abs(net_due(200.0, 0.25) - 150.0) < 1e-6\n"
            "if __name__ == '__main__':\n"
            "    test_net()\n",
            encoding="utf-8",
        )
        p2 = ra.awake_pulse(
            ws2,
            ledger_path=ledger_p,
            skill_store_path=skills_p,
            workflow_db_path=wf_p,
            apply_verified_repairs=True,
            channels=("solve",),
        )
        assert p2["cow_experimentation"]["repaired"] == 1
        assert p2["cow_experimentation"]["repairs"][0]["mode"] == "VERIFIED_SKILL_RECALL"

        # Simulate platform drift in rule_expiry_v1 -> rule transitions to STALE!
        drifted_world = rule_exp.world_fingerprint()
        drifted_world["platform"] = "SimulatedAlienOS"
        audit_rep = rule_exp.audit(skills_p, now=drifted_world)
        assert audit_rep["counts"][rule_exp.STALE] == 1
        assert ledger.open_gaps(path=str(ledger_p)) >= 1
