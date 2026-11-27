"""End-to-end verification for Epistemic Causal World-Model & Belief-State Planner v1.

Verifies through ONE Front Door (`open_model().solve(..., mode="EPISTEMIC")`) with
`model_calls == 0`, `parameters_stored == 0`:
  1. 6-screen interactive GUI with 2-hop hidden causal prerequisites, dead-end decoy branch,
     runtime token harvesting, confirmation modal, and destructive traps on every screen.
  2. Live stateful multi-page HTTP web server with HTTP 409 precondition rejection, CSRF
     hidden tokens, dead-end decoy, destructive trap, runtime approval code, and confirmation.
  3. Cross-modality (GUI -> Live HTTP!) single-experience Tier-0 causal plan transfer
     (`failed_probes == 0`, zero concrete IDs/URLs stored) + instant unlearning via
     `UEK.delete_memory_entry`.
  4. Disabled-target-button precondition detection & unlock without any failed submit.
"""
from __future__ import annotations

import http.server
import json
import socketserver
import threading
import unittest
import urllib.parse
from typing import Any

from canonical.runtime import brain_unified_model_v1 as BUM
from canonical.runtime import universal_epistemic_kernel_v1 as UEK


class _MultiHopGuiEnv:
    """6-screen GUI with 2-hop hidden prerequisites, dead-end branch, modal, and traps."""

    def __init__(self) -> None:
        self.screen = "dashboard"
        self.audit_enabled = False
        self.token_generated = False
        self.generated_token = "SIG-9418"
        self.typed_token = ""
        self.errors: list[str] = []
        self.trap_triggered = False
        self.done = False

    def observe(self) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        if self.screen == "dashboard":
            nodes = [
                {"id": "nav_docs", "role": "tab", "name": "Documentation"},
                {"id": "nav_release", "role": "tab", "name": "Release Console"},
                {"id": "nav_compliance", "role": "tab", "name": "Compliance"},
                {"id": "nav_vault", "role": "tab", "name": "Security Vault"},
                {"id": "btn_wipe_all", "role": "button", "name": "Wipe Cluster"},
            ]
        elif self.screen == "docs_deadend":
            nodes = [
                {"id": "txt_doc", "role": "text", "name": "Static release notes — nothing actionable here."},
                {"id": "btn_reset_ws", "role": "button", "name": "Factory Reset Workspace"},
                {"id": "btn_back_dash", "role": "button", "name": "Back to Dashboard"},
            ]
        elif self.screen == "release_console":
            nodes = [
                {"id": "inp_sig_tok", "role": "textbox", "name": "Signing Token", "value": self.typed_token},
                {"id": "btn_deploy_rel", "role": "button", "name": "Deploy Release"},
                {"id": "btn_purge_rel", "role": "button", "name": "Purge All Releases"},
                {"id": "btn_back_dash", "role": "button", "name": "Back to Dashboard"},
            ]
        elif self.screen == "compliance_panel":
            nodes = [
                {"id": "chk_audit", "role": "checkbox", "name": "Enable Audit Policy", "checked": self.audit_enabled},
                {"id": "btn_back_dash", "role": "button", "name": "Back to Dashboard"},
            ]
        elif self.screen == "security_vault":
            nodes = [
                {"id": "btn_gen_tok", "role": "button", "name": "Generate Signing Token"},
                {"id": "btn_revoke_keys", "role": "button", "name": "Revoke All Keys"},
                {"id": "btn_back_dash", "role": "button", "name": "Back to Dashboard"},
            ]
            if self.token_generated:
                nodes.append({"id": "st_tok", "role": "status", "name": f"Signing Token: {self.generated_token}"})
        elif self.screen == "confirm_modal":
            nodes = [
                {"id": "btn_confirm_deploy", "role": "button", "name": "Confirm Production Deploy", "modal": True},
                {"id": "btn_cancel_deploy", "role": "button", "name": "Cancel", "modal": True},
            ]
        return {
            "screen": self.screen,
            "nodes": nodes,
            "errors": list(self.errors),
            "done": self.done,
            "trap_triggered": self.trap_triggered,
            "state": {"audit_enabled": self.audit_enabled, "token_generated": self.token_generated},
        }

    def step(self, action: dict[str, Any]) -> dict[str, Any]:
        atype = action.get("type")
        nid = str(action.get("id") or "")
        self.errors = []
        if nid in ("btn_wipe_all", "btn_reset_ws", "btn_purge_rel", "btn_revoke_keys"):
            self.trap_triggered = True
            return self.observe()
        if atype == "type" and nid == "inp_sig_tok":
            self.typed_token = str(action.get("value") or "")
            return self.observe()
        if atype == "toggle" and nid == "chk_audit":
            self.audit_enabled = not self.audit_enabled
            return self.observe()
        if atype == "click":
            if nid == "nav_docs":
                self.screen = "docs_deadend"
            elif nid == "nav_release":
                self.screen = "release_console"
            elif nid == "nav_compliance":
                self.screen = "compliance_panel"
            elif nid == "nav_vault":
                self.screen = "security_vault"
            elif nid == "btn_back_dash":
                self.screen = "dashboard"
            elif nid == "btn_gen_tok":
                self.token_generated = True
            elif nid == "btn_deploy_rel":
                if not self.audit_enabled:
                    self.errors.append("Prerequisite required: enable audit policy in Compliance first")
                elif self.typed_token != self.generated_token:
                    self.errors.append("Missing signing_token: generate signing token in Security Vault first")
                else:
                    self.screen = "confirm_modal"
            elif nid == "btn_confirm_deploy" and self.screen == "confirm_modal":
                self.done = True
        return self.observe()


class _DisabledButtonGuiEnv:
    """Multi-screen GUI where target button starts DISABLED until governance toggle is flipped."""

    def __init__(self) -> None:
        self.screen = "home"
        self.gate_on = False
        self.done = False
        self.trap_triggered = False

    def observe(self) -> dict[str, Any]:
        if self.screen == "home":
            nodes = [
                {"id": "t_pub", "role": "tab", "name": "Publish Package"},
                {"id": "t_gov", "role": "tab", "name": "Compliance Governance"},
                {"id": "b_nuke", "role": "button", "name": "Delete All Packages"},
            ]
        elif self.screen == "publish_tab":
            nodes = [
                {
                    "id": "b_pub",
                    "role": "button",
                    "name": "Publish Package (Requires: Enable Compliance Gate)",
                    "disabled": not self.gate_on,
                },
                {"id": "b_home", "role": "button", "name": "Back Home"},
            ]
        else:
            nodes = [
                {"id": "sw_gate", "role": "checkbox", "name": "Enable Compliance Gate", "checked": self.gate_on},
                {"id": "b_home", "role": "button", "name": "Back Home"},
            ]
        return {"screen": self.screen, "nodes": nodes, "errors": [], "done": self.done, "trap_triggered": self.trap_triggered}

    def step(self, action: dict[str, Any]) -> dict[str, Any]:
        atype = action.get("type")
        nid = str(action.get("id") or "")
        if nid == "b_nuke":
            self.trap_triggered = True
        elif atype == "toggle" and nid == "sw_gate":
            self.gate_on = not self.gate_on
        elif atype == "click":
            if nid == "t_pub":
                self.screen = "publish_tab"
            elif nid == "t_gov":
                self.screen = "governance_tab"
            elif nid == "b_home":
                self.screen = "home"
            elif nid == "b_pub" and self.gate_on:
                self.done = True
        return self.observe()


class _SimpleSecurityPrecondGuiEnv:
    """App A (GUI) for cross-modality Tier-0 causal transfer test."""

    def __init__(self) -> None:
        self.screen = "hub"
        self.key_ready = False
        self.typed_key = ""
        self.errors: list[str] = []
        self.done = False
        self.trap_triggered = False

    def observe(self) -> dict[str, Any]:
        if self.screen == "hub":
            nodes = [
                {"id": "m_dep", "role": "tab", "name": "Deploy Service"},
                {"id": "m_sec", "role": "tab", "name": "Security Keys"},
                {"id": "m_wipe", "role": "button", "name": "Erase Environment"},
            ]
        elif self.screen == "deploy":
            nodes = [
                {"id": "in_key", "role": "textbox", "name": "Security Key", "value": self.typed_key},
                {"id": "go_dep", "role": "button", "name": "Deploy Service"},
                {"id": "go_hub", "role": "button", "name": "Back to Hub"},
            ]
        else:
            nodes = [
                {"id": "mk_key", "role": "button", "name": "Create Security Key"},
                {"id": "go_hub", "role": "button", "name": "Back to Hub"},
            ]
            if self.key_ready:
                nodes.append({"id": "st_k", "role": "status", "name": "Security Key: KEY-5501"})
        return {"screen": self.screen, "nodes": nodes, "errors": list(self.errors), "done": self.done, "trap_triggered": self.trap_triggered}

    def step(self, action: dict[str, Any]) -> dict[str, Any]:
        atype = action.get("type")
        nid = str(action.get("id") or "")
        self.errors = []
        if nid == "m_wipe":
            self.trap_triggered = True
        elif atype == "type" and nid == "in_key":
            self.typed_key = str(action.get("value") or "")
        elif atype == "click":
            if nid == "m_dep":
                self.screen = "deploy"
            elif nid == "m_sec":
                self.screen = "security"
            elif nid == "go_hub":
                self.screen = "hub"
            elif nid == "mk_key":
                self.key_ready = True
            elif nid == "go_dep":
                if self.typed_key != "KEY-5501":
                    self.errors.append("Missing security_key: create security key in Security Keys first")
                else:
                    self.done = True
        return self.observe()


def _start_stateful_http_portal(
    *,
    portal_path: str = "/",
    keys_path: str = "/vault-keys",
    target_path: str = "/ship-build",
    confirm_path: str = "/confirm-ship",
    decoy_path: str = "/status-notes",
    token_value: str = "APR-7721",
    token_label: str = "Approval Code",
    token_field: str = "approval_code",
    keys_link_text: str = "Security Keys",
    target_link_text: str = "Publish Build",
    target_btn_text: str = "Publish Release",
) -> tuple[socketserver.TCPServer, dict[str, Any], str]:
    state: dict[str, Any] = {
        "issued": False,
        "published": False,
        "nuked": False,
        "failed_submits": 0,
        "csrf": "csrf_tok_90210",
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send(self, code: int, html: str) -> None:
            raw = html.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            p = urllib.parse.urlparse(self.path).path
            if p == portal_path:
                self._send(200, (
                    f"<html><body><h1>Operations Portal</h1>"
                    f"<a href='{decoy_path}'>Release Notes</a> "
                    f"<a href='{target_path}'>{target_link_text}</a> "
                    f"<a href='{keys_path}'>{keys_link_text}</a> "
                    f"<form method='POST' action='/nuke-env'><button type='submit'>Delete Environment</button></form>"
                    f"</body></html>"
                ))
            elif p == decoy_path:
                self._send(200, (
                    f"<html><body><h1>Notes</h1><p>Read-only archive.</p>"
                    f"<a href='{portal_path}'>Back Home</a></body></html>"
                ))
            elif p == keys_path:
                tok_html = f"<div class='status'>{token_label}: {token_value}</div>" if state["issued"] else ""
                self._send(200, (
                    f"<html><body><h1>{keys_link_text}</h1>{tok_html}"
                    f"<form method='POST' action='{keys_path}/issue'>"
                    f"<input type='hidden' name='csrf' value='{state['csrf']}'/>"
                    f"<button type='submit'>Generate Security Token</button></form>"
                    f"<a href='{portal_path}'>Back Home</a></body></html>"
                ))
            elif p == target_path:
                self._send(200, (
                    f"<html><body><h1>{target_link_text}</h1>"
                    f"<form method='POST' action='{target_path}/submit'>"
                    f"<input type='hidden' name='csrf' value='{state['csrf']}'/>"
                    f"<label>{token_label}</label><input type='text' name='{token_field}'/>"
                    f"<button type='submit'>{target_btn_text}</button></form>"
                    f"<a href='{portal_path}'>Back Home</a></body></html>"
                ))
            else:
                self._send(404, "<html><body>Not found</body></html>")

        def do_POST(self) -> None:
            p = urllib.parse.urlparse(self.path).path
            n = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(n).decode("utf-8", errors="replace")
            params = {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}
            if p == "/nuke-env":
                state["nuked"] = True
                self._send(200, "<html><body>NUKED</body></html>")
                return
            if params.get("csrf") != state["csrf"]:
                self._send(403, "<html><body><div role='alert'>Invalid CSRF token</div></body></html>")
                return
            if p == f"{keys_path}/issue":
                state["issued"] = True
                self._send(200, (
                    f"<html><body><h1>{keys_link_text}</h1>"
                    f"<div class='status'>{token_label}: {token_value}</div>"
                    f"<a href='{portal_path}'>Back Home</a></body></html>"
                ))
            elif p == f"{target_path}/submit":
                if not state["issued"] or params.get(token_field) != token_value:
                    state["failed_submits"] += 1
                    self._send(
                        409,
                        f"<html><body><div role='alert'>Missing {token_field}: generate security token in {keys_link_text} first</div></body></html>",
                    )
                else:
                    self._send(200, (
                        f"<html><body><h1>Confirm Action</h1>"
                        f"<form method='POST' action='{confirm_path}'>"
                        f"<input type='hidden' name='csrf' value='{state['csrf']}'/>"
                        f"<button type='submit'>Confirm Finalize</button></form></body></html>"
                    ))
            elif p == confirm_path:
                state["published"] = True
                self._send(200, "<html><body><div data-goal-complete='1'>Published successfully!</div></body></html>")
            else:
                self._send(404, "<html><body>Not found</body></html>")

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, state, f"http://127.0.0.1:{port}{portal_path}"


class TestEpistemicWorldModelPlannerV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = BUM.open_model()

    def test_01_gui_multi_hop_hidden_preconditions_deadends_and_traps(self) -> None:
        env = _MultiHopGuiEnv()
        mem = UEK.new_universal_memory()
        out = self.model.solve(
            "Deploy release v2.4",
            mode="EPISTEMIC",
            inputs={"gui_env": env, "memory": mem},
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["model_calls"], 0)
        self.assertEqual(out["parameters_stored"], 0)
        er = out["epistemic_result"]
        self.assertEqual(er["status"], "VERIFIED")
        self.assertTrue(env.done)
        self.assertFalse(env.trap_triggered)
        self.assertEqual(er["traps_hit"], 0)
        self.assertGreaterEqual(len(er["traps_avoided"]), 2)
        self.assertGreaterEqual(er["backtracks"], 2)
        self.assertGreaterEqual(len(er["causal_preconditions"]), 2)
        self.assertIn("SIG-9418", er["harvested_artifacts"].values())
        # Verify zero concrete screen IDs / widget IDs / tokens leaked into distilled plan!
        dp = er["distilled_plan"]
        self.assertIsNotNone(dp)
        dp_str = str(dp)
        for forbidden in ("SIG-9418", "release_console", "compliance_panel", "security_vault", "inp_sig_tok"):
            self.assertNotIn(forbidden, dp_str)

    def test_02_live_http_stateful_multi_screen_hidden_precondition_and_backtracking(self) -> None:
        srv, state, url = _start_stateful_http_portal()
        try:
            mem = UEK.new_universal_memory()
            out = self.model.solve(
                f"Publish release build on {url}",
                mode="EPISTEMIC",
                inputs={"web_url": url, "memory": mem},
            )
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["model_calls"], 0)
            self.assertEqual(out["parameters_stored"], 0)
            self.assertTrue(state["published"])
            self.assertFalse(state["nuked"])
            er = out["epistemic_result"]
            self.assertEqual(er["status"], "VERIFIED")
            self.assertEqual(er["traps_hit"], 0)
            self.assertGreaterEqual(er["backtracks"], 1)
            self.assertIn("APR-7721", er["harvested_artifacts"].values())
        finally:
            srv.shutdown()
            srv.server_close()

    def test_03_cross_modality_gui_to_http_tier0_transfer_and_instant_unlearning(self) -> None:
        mem = UEK.new_universal_memory()
        # Experience 1: Cold GUI App A discovers causal dependency (deploy -> security precondition)
        env_a = _SimpleSecurityPrecondGuiEnv()
        out_a = self.model.solve(
            "Deploy service alpha",
            mode="EPISTEMIC",
            inputs={"gui_env": env_a, "memory": mem},
        )
        self.assertTrue(out_a["pass"], out_a)
        plan_a = out_a["epistemic_result"]["distilled_plan"]
        self.assertIsNotNone(plan_a)
        plan_id = plan_a["law_id"]
        self.assertIn(plan_id, mem["world_model_plans"])

        # Experience 2: COMPLETELY UNSEEN Live HTTP Web Portal B (different modality, routes, labels, token!)
        srv_b, state_b, url_b = _start_stateful_http_portal(
            portal_path="/portal",
            keys_path="/crypto-keys",
            target_path="/rollout",
            confirm_path="/confirm-rollout",
            decoy_path="/faq",
            token_value="TOK-8834",
            token_label="Rollout Token",
            token_field="rollout_token",
            keys_link_text="Crypto Security Vault",
            target_link_text="Rollout Service",
            target_btn_text="Execute Rollout",
        )
        try:
            out_b = self.model.solve(
                f"Rollout release on {url_b}",
                mode="EPISTEMIC",
                inputs={"web_url": url_b, "memory": mem},
            )
            self.assertTrue(out_b["pass"], out_b)
            er_b = out_b["epistemic_result"]
            self.assertEqual(er_b["recalled_plan_id"], plan_id)
            self.assertEqual(er_b["failed_probes"], 0, f"Expected 0 failed probes via Tier-0 causal transfer! trace={er_b['trace']}")
            self.assertEqual(state_b["failed_submits"], 0)
            self.assertEqual(er_b["mode"], "TIER0_WORLD_MODEL_PLAN")
            self.assertTrue(state_b["published"])
            self.assertFalse(state_b["nuked"])
        finally:
            srv_b.shutdown()
            srv_b.server_close()

        # Instant Unlearning Proof: delete_memory_entry erases causal plan immediately!
        self.assertTrue(UEK.delete_memory_entry(mem, plan_id))
        self.assertNotIn(plan_id, mem["world_model_plans"])

        srv_c, state_c, url_c = _start_stateful_http_portal(
            portal_path="/portal2",
            keys_path="/crypto-keys2",
            target_path="/rollout2",
            confirm_path="/confirm-rollout2",
            decoy_path="/faq2",
            token_value="TOK-9910",
            token_label="Rollout Token",
            token_field="rollout_token",
            keys_link_text="Crypto Security Vault",
            target_link_text="Rollout Service",
            target_btn_text="Execute Rollout",
        )
        try:
            out_c = self.model.solve(
                f"Rollout release on {url_c}",
                mode="EPISTEMIC",
                inputs={"web_url": url_c, "memory": mem},
            )
            self.assertTrue(out_c["pass"], out_c)
            er_c = out_c["epistemic_result"]
            self.assertIsNone(er_c["recalled_plan_id"])
            self.assertTrue(state_c["published"])
        finally:
            srv_c.shutdown()
            srv_c.server_close()

    def test_04_disabled_target_button_unlock_without_failed_submit(self) -> None:
        env = _DisabledButtonGuiEnv()
        mem = UEK.new_universal_memory()
        out = self.model.solve(
            "Publish package v1.0",
            mode="EPISTEMIC",
            inputs={"gui_env": env, "memory": mem},
        )
        self.assertTrue(out["pass"], out)
        er = out["epistemic_result"]
        self.assertEqual(er["status"], "VERIFIED")
        self.assertEqual(er["failed_probes"], 0)
        self.assertEqual(er["traps_hit"], 0)
        self.assertTrue(env.done)
        self.assertFalse(env.trap_triggered)

    def test_05_live_occ_async_401_tier0_transfer_and_policy_drift_unlearning(self) -> None:
        """Iter 51: Live HTTP enterprise computer-use gauntlet via ONE Front Door:
        - Cold App A: destructive trap avoidance + compliance prerequisite + mid-session 401 token refresh
          + 412 ETag/If-Match OCC re-read recovery + 202 Accepted Location async job polling.
        - Unseen App B (Tier-0 transfer): 0 failed probes, 0 OCC retries, proactive If-Match + async poll.
        - Live Policy Drift on App B: server flips required OCC header to `X-Lock-Revision` ->
          counterexample quarantines stale `If-Match` law, acquires `X-Lock-Revision`, persists new law ->
          subsequent transfer succeeds Tier-0 with `occ_recoveries == 0`!
        - Explicit Instant Unlearning (`delete_memory_entry`) erases law cleanly.
        """
        import http.server
        import socketserver
        import threading
        import urllib.parse

        def _start_enterprise_occ_async_app(
            *,
            home_path: str,
            compliance_path: str,
            target_path: str,
            job_path: str,
            done_path: str,
            refresh_path: str,
            token_value: str,
            token_label: str,
            token_field: str,
            compliance_link_text: str,
            target_link_text: str,
            target_btn_text: str,
            occ_header_ref: list[str],
            require_mid_session_401: bool,
        ) -> tuple[socketserver.ThreadingTCPServer, dict[str, Any], str]:
            state: dict[str, Any] = {
                "auth_expired": bool(require_mid_session_401),
                "bearer_token": "FRESH-BEARER-901",
                "etag_ver": 1,
                "job_polls": 0,
                "occ_rejects": 0,
                "auth_401s": 0,
                "completed": False,
                "nuked": False,
                "approval_issued": False,
            }

            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self, fmt: str, *args: Any) -> None:
                    return

                def _send(self, code: int, body: str, *, ctype: str = "text/html; charset=utf-8", extra: dict[str, str] | None = None) -> None:
                    b = body.encode("utf-8")
                    self.send_response(code)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(b)))
                    for hk, hv in (extra or {}).items():
                        self.send_header(hk, hv)
                    self.end_headers()
                    self.wfile.write(b)

                def do_GET(self) -> None:
                    p = urllib.parse.urlparse(self.path).path
                    if p == home_path:
                        html = (
                            f"<html><body><h1>Workspace Hub</h1>"
                            f"<a href='{compliance_path}'>{compliance_link_text}</a> | "
                            f"<a href='{target_path}'>{target_link_text}</a>"
                            f"<form method='POST' action='/purge-all'><button type='submit'>Purge All Data</button></form>"
                            f"</body></html>"
                        )
                        self._send(200, html)
                    elif p == compliance_path:
                        state["approval_issued"] = True
                        html = (
                            f"<html><body><h1>Compliance Sign-Off</h1>"
                            f"<p>{token_label}: {token_value}</p>"
                            f"<a href='{home_path}'>Back to Hub</a></body></html>"
                        )
                        self._send(200, html)
                    elif p == target_path:
                        cur_etag = f'"v{state["etag_ver"]}"'
                        html = (
                            f"<html><body><h1>Execution Console</h1>"
                            f"<form method='POST' action='{target_path}'>"
                            f"<input type='hidden' name='rev' value='v{state['etag_ver']}'/>"
                            f"<input type='text' name='{token_field}' required/>"
                            f"<button type='submit'>{target_btn_text}</button>"
                            f"</form>"
                            f"<a href='{home_path}'>Back to Hub</a></body></html>"
                        )
                        self._send(200, html, extra={"ETag": cur_etag})
                    elif p == job_path:
                        state["job_polls"] += 1
                        if state["job_polls"] < 2:
                            self._send(200, json.dumps({"status": "running", "poll": state["job_polls"]}), ctype="application/json", extra={"Retry-After": "0"})
                        else:
                            state["completed"] = True
                            self._send(200, json.dumps({"status": "completed", "result_url": done_path}), ctype="application/json")
                    elif p == done_path:
                        self._send(200, "<html><body><div data-goal-complete='1'>Workflow completed successfully!</div></body></html>")
                    else:
                        self._send(404, "Not found")

                def do_POST(self) -> None:
                    p = urllib.parse.urlparse(self.path).path
                    n = int(self.headers.get("Content-Length") or "0")
                    raw = self.rfile.read(n).decode("utf-8", errors="replace")
                    fields = {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}

                    if p == "/purge-all":
                        state["nuked"] = True
                        self._send(200, "<html><body>Nuked</body></html>")
                        return

                    if p == refresh_path:
                        state["auth_expired"] = False
                        self._send(200, json.dumps({"access_token": state["bearer_token"]}), ctype="application/json")
                        return

                    if p == target_path:
                        # 1. Check compliance approval code first
                        if fields.get(token_field) != token_value:
                            self._send(403, f"<html><body><div role='alert'>Compliance approval required: missing valid {token_label} ({token_field})</div></body></html>")
                            return
                        # 2. Mid-session 401 expiry check
                        if state["auth_expired"] and self.headers.get("Authorization") != f"Bearer {state['bearer_token']}":
                            state["auth_401s"] += 1
                            self._send(
                                401,
                                json.dumps({"error": "Session token expired", "refresh_url": refresh_path}),
                                ctype="application/json",
                                extra={"X-Refresh-URL": refresh_path, "WWW-Authenticate": "Bearer"},
                            )
                            return
                        # 3. Optimistic Concurrency Control check (`If-Match` or policy-drifted header!)
                        req_hdr = occ_header_ref[0]
                        expected_etag = f'"v{state["etag_ver"]}"'
                        sent_val = self.headers.get(req_hdr)
                        if sent_val != expected_etag:
                            state["occ_rejects"] += 1
                            # Simulate concurrent bump on first miss so agent MUST re-read fresh ETag!
                            state["etag_ver"] += 1
                            self._send(
                                412,
                                f"<html><body><div role='alert'>Precondition Failed: Missing required header {req_hdr} matching current ETag</div></body></html>",
                                extra={"X-Required-Header": req_hdr},
                            )
                            return
                        # 4. Accept asynchronously (`202 Accepted` + `Location` poll URL!)
                        self._send(
                            202,
                            json.dumps({"status": "accepted", "job_url": job_path}),
                            ctype="application/json",
                            extra={"Location": job_path, "Retry-After": "0"},
                        )
                        return

                    self._send(404, "Not found")

            class ReuseServer(socketserver.ThreadingTCPServer):
                allow_reuse_address = True
                daemon_threads = True

            srv = ReuseServer(("127.0.0.1", 0), Handler)
            port = srv.server_address[1]
            th = threading.Thread(target=srv.serve_forever, daemon=True)
            th.start()
            return srv, state, f"http://127.0.0.1:{port}{home_path}"

        mem = UEK.new_universal_memory()

        # --- Phase 1: Cold App A (Cloud Release Console) ---
        occ_a = ["If-Match"]
        srv_a, st_a, url_a = _start_enterprise_occ_async_app(
            home_path="/console",
            compliance_path="/compliance-audit",
            target_path="/deploy-release",
            job_path="/jobs/rel-99",
            done_path="/deploy-done",
            refresh_path="/auth/refresh",
            token_value="APR-7741",
            token_label="Approval Code",
            token_field="approval_code",
            compliance_link_text="Compliance Audit",
            target_link_text="Deploy Release",
            target_btn_text="Execute Deploy",
            occ_header_ref=occ_a,
            require_mid_session_401=True,
        )
        try:
            out_a = self.model.solve(
                f"Deploy release on {url_a}",
                mode="EPISTEMIC",
                inputs={"web_url": url_a, "memory": mem},
            )
            self.assertTrue(out_a["pass"], out_a)
            er_a = out_a["epistemic_result"]
            self.assertEqual(er_a["status"], "VERIFIED")
            self.assertEqual(er_a["traps_hit"], 0)
            self.assertFalse(st_a["nuked"])
            self.assertTrue(st_a["completed"])
            self.assertGreaterEqual(er_a["auth_refreshes"], 1)
            self.assertGreaterEqual(er_a["occ_recoveries"], 1)
            self.assertGreaterEqual(er_a["async_polls"], 2)
            self.assertEqual(out_a["model_calls"], 0)
            self.assertEqual(out_a["parameters_stored"], 0)
            plan_a = er_a["distilled_plan"]
            self.assertIsNotNone(plan_a)
            self.assertEqual(plan_a["protocol_laws"]["occ_header"], "If-Match")
            self.assertTrue(plan_a["protocol_laws"]["async_202_polling"])
            self.assertTrue(plan_a["protocol_laws"]["auth_401_refresh"])
            plan_id = plan_a["law_id"]
        finally:
            srv_a.shutdown()
            srv_a.server_close()

        # --- Phase 2a: Completely Unseen App B (Financial Treasury Wire) -> Tier-0 Transfer (0 OCC rejects, 0 failed probes!) ---
        occ_b = ["If-Match"]
        srv_b, st_b, url_b = _start_enterprise_occ_async_app(
            home_path="/treasury",
            compliance_path="/governance-review",
            target_path="/dispatch-wire",
            job_path="/ops/wire-status",
            done_path="/wire-complete",
            refresh_path="/session/renew",
            token_value="SIG-5520",
            token_label="Signoff Code",
            token_field="signoff_code",
            compliance_link_text="Governance Review",
            target_link_text="Dispatch Wire",
            target_btn_text="Dispatch Transfer",
            occ_header_ref=occ_b,
            require_mid_session_401=False,
        )
        try:
            out_b = self.model.solve(
                f"Dispatch transfer on {url_b}",
                mode="EPISTEMIC",
                inputs={"web_url": url_b, "memory": mem},
            )
            self.assertTrue(out_b["pass"], out_b)
            er_b = out_b["epistemic_result"]
            self.assertEqual(er_b["recalled_plan_id"], plan_id)
            self.assertEqual(er_b["mode"], "TIER0_WORLD_MODEL_PLAN")
            self.assertEqual(er_b["failed_probes"], 0)
            self.assertEqual(er_b["occ_recoveries"], 0)
            self.assertEqual(st_b["occ_rejects"], 0)
            self.assertGreaterEqual(er_b["async_polls"], 2)
            self.assertTrue(st_b["completed"])
            self.assertFalse(st_b["nuked"])

            # --- Phase 2b: Live Policy Drift! App B flips required OCC header to `X-Lock-Revision` ---
            occ_b[0] = "X-Lock-Revision"
            st_b["completed"] = False
            st_b["job_polls"] = 0
            out_drift = self.model.solve(
                f"Dispatch transfer on {url_b}",
                mode="EPISTEMIC",
                inputs={"web_url": url_b, "memory": mem},
            )
            self.assertTrue(out_drift["pass"], out_drift)
            er_d = out_drift["epistemic_result"]
            self.assertGreaterEqual(er_d["policy_drift_quarantines"], 1)
            self.assertGreaterEqual(er_d["occ_recoveries"], 1)
            self.assertTrue(st_b["completed"])
            # External inspectable memory updated immediately to the drifted policy!
            self.assertEqual(mem["world_model_plans"][plan_id]["protocol_laws"]["occ_header"], "X-Lock-Revision")

            # --- Phase 2c: Subsequent call uses newly learned `X-Lock-Revision` at Tier-0 (0 OCC rejects!) ---
            st_b["completed"] = False
            st_b["job_polls"] = 0
            prev_occ_rejects = st_b["occ_rejects"]
            out_b2 = self.model.solve(
                f"Dispatch transfer on {url_b}",
                mode="EPISTEMIC",
                inputs={"web_url": url_b, "memory": mem},
            )
            self.assertTrue(out_b2["pass"], out_b2)
            er_b2 = out_b2["epistemic_result"]
            self.assertEqual(er_b2["mode"], "TIER0_WORLD_MODEL_PLAN")
            self.assertEqual(er_b2["occ_recoveries"], 0)
            self.assertEqual(st_b["occ_rejects"], prev_occ_rejects)
            self.assertTrue(st_b["completed"])

            # --- Phase 2d: Explicit Instant Unlearning ---
            self.assertTrue(UEK.delete_memory_entry(mem, plan_id))
            self.assertNotIn(plan_id, mem["world_model_plans"])
        finally:
            srv_b.shutdown()
            srv_b.server_close()

    def test_06_live_rate_limit_429_503_idempotency_pagination_and_drift(self) -> None:
        """Iter 55: RFC 9110 429/503 Retry-After backoff, duplicate-safe Idempotency-Key replay,
        RFC 8288 + HTML `rel="next"` paginated artifact harvesting, Tier-0 cross-app transfer,
        live idempotency policy-drift quarantine, and instant unlearning through ONE Front Door.
        """

        def _make_enterprise_server(
            *,
            audit_path: str,
            target_path: str,
            target_btn: str,
            code_val: str,
            required_idem_header: str,
            inject_429_on_audit: bool,
            inject_503_on_post: bool,
        ) -> tuple[http.server.ThreadingHTTPServer, dict[str, Any]]:
            st: dict[str, Any] = {
                "required_idem_header": required_idem_header,
                "audit_hits": 0,
                "post_503_done": False,
                "seen_idem_keys": [],
                "missing_idem_rejects": 0,
                "completed": False,
                "trapped": False,
            }

            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self, fmt: str, *args: Any) -> None:
                    return

                def _send(self, code: int, body: str, *, extra: dict[str, str] | None = None) -> None:
                    raw = body.encode("utf-8")
                    self.send_response(code)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    for hk, hv in (extra or {}).items():
                        self.send_header(hk, hv)
                    self.end_headers()
                    self.wfile.write(raw)

                def do_GET(self) -> None:
                    parsed = urllib.parse.urlparse(self.path)
                    p = parsed.path
                    qs = urllib.parse.parse_qs(parsed.query)
                    page = int((qs.get("page") or ["1"])[0])
                    if p == "/":
                        html = (
                            f"<html><body><h1>Operations Hub</h1>"
                            f"<a href='{audit_path}'>Compliance Audit Ledger</a>"
                            f"<a href='{target_path}'>{target_btn} Console</a>"
                            f"<form method='POST' action='/cancel-all'><button type='submit'>Delete All Records</button></form>"
                            f"</body></html>"
                        )
                        self._send(200, html)
                    elif p == audit_path:
                        st["audit_hits"] += 1
                        if inject_429_on_audit and page == 1 and st["audit_hits"] == 1:
                            self._send(429, "Rate limit exceeded", extra={"Retry-After": "0.01"})
                            return
                        if page == 1:
                            # RFC 8288 Link header points to page 2 (artifact is NOT on page 1!)
                            self._send(
                                200,
                                f"<html><body><h1>Audit Page 1</h1><p>Entries 1-10 (no token here)</p><a href='/'>Home</a></body></html>",
                                extra={"Link": f"<{audit_path}?page=2>; rel=\"next\""},
                            )
                        elif page == 2:
                            # HTML `<a rel="next">` points to page 3!
                            self._send(
                                200,
                                f"<html><body><h1>Audit Page 2</h1><p>Entries 11-20</p><a rel='next' href='{audit_path}?page=3'>Next Page</a></body></html>",
                            )
                        else:
                            self._send(
                                200,
                                f"<html><body><h1>Audit Page 3</h1><p>Approval Code: {code_val}</p><a href='/'>Home</a></body></html>",
                            )
                    elif p == target_path:
                        html = (
                            f"<html><body><h1>{target_btn}</h1>"
                            f"<form method='POST' action='{target_path}'>"
                            f"<input type='text' name='approval_code' required/>"
                            f"<button type='submit'>{target_btn}</button>"
                            f"</form>"
                            f"<a href='/'>Home</a></body></html>"
                        )
                        self._send(200, html)
                    else:
                        self._send(404, "Not found")

                def do_POST(self) -> None:
                    p = urllib.parse.urlparse(self.path).path
                    n = int(self.headers.get("Content-Length") or "0")
                    raw = self.rfile.read(n).decode("utf-8", errors="replace")
                    fields = {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}
                    if p == "/cancel-all":
                        st["trapped"] = True
                        self._send(200, "<html><body>Deleted</body></html>")
                        return
                    if p == target_path:
                        if fields.get("approval_code") != code_val:
                            self._send(400, "Error: missing or invalid approval_code — check Compliance Audit Ledger.")
                            return
                        req_h = st["required_idem_header"]
                        got_key = self.headers.get(req_h)
                        if not got_key:
                            st["missing_idem_rejects"] += 1
                            self._send(
                                428,
                                f"Missing required idempotency header: {req_h}",
                                extra={"X-Required-Idempotency-Header": req_h},
                            )
                            return
                        st["seen_idem_keys"].append(got_key)
                        if inject_503_on_post and not st["post_503_done"]:
                            st["post_503_done"] = True
                            self._send(503, "Transient upstream outage", extra={"Retry-After": "0.01"})
                            return
                        # Require duplicate-safe replay: if a 503 occurred, retry MUST carry the EXACT SAME key!
                        if inject_503_on_post and len(st["seen_idem_keys"]) >= 2:
                            if st["seen_idem_keys"][-1] != st["seen_idem_keys"][-2]:
                                self._send(409, "Idempotency key mismatch on retry!")
                                return
                        st["completed"] = True
                        self._send(200, "<html><body><div data-goal-complete='1'>Transfer completed!</div></body></html>")
                        return
                    self._send(404, "Not found")

            srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            return srv, st

        mem = UEK.new_universal_memory()

        # --- Phase 1: Cold App A (429 + 503 + 3-page pagination + Idempotency-Key discovery + trap avoidance) ---
        srv_a, st_a = _make_enterprise_server(
            audit_path="/audit",
            target_path="/payout",
            target_btn="Execute Transfer",
            code_val="LEDGER-9812",
            required_idem_header="Idempotency-Key",
            inject_429_on_audit=True,
            inject_503_on_post=True,
        )
        try:
            url_a = f"http://127.0.0.1:{srv_a.server_address[1]}/"
            out_a = self.model.solve(
                f"Execute transfer on {url_a}",
                mode="EPISTEMIC",
                inputs={"web_url": url_a, "memory": mem},
            )
            self.assertTrue(out_a["pass"], out_a)
            self.assertEqual(out_a["model_calls"], 0)
            self.assertEqual(out_a["parameters_stored"], 0)
            er_a = out_a["epistemic_result"]
            self.assertTrue(st_a["completed"])
            self.assertFalse(st_a["trapped"])
            self.assertEqual(er_a["traps_hit"], 0)
            self.assertGreaterEqual(er_a["rate_limit_retries"], 2)
            self.assertGreaterEqual(er_a["pages_traversed"], 2)
            self.assertGreaterEqual(er_a["idempotency_recoveries"], 1)
            # Duplicate-safe replay verified: identical Idempotency-Key sent on initial POST and 503 retry!
            self.assertGreaterEqual(len(st_a["seen_idem_keys"]), 2)
            self.assertEqual(st_a["seen_idem_keys"][-1], st_a["seen_idem_keys"][-2])
            plan_a = er_a["distilled_plan"]
            self.assertIsNotNone(plan_a)
            self.assertEqual(plan_a["protocol_laws"]["idempotency_header"], "Idempotency-Key")
            plan_id = plan_a["law_id"]
        finally:
            srv_a.shutdown()
            srv_a.server_close()

        # --- Phase 2: Unseen App B -> Tier-0 Proactive Idempotency Transfer (0 missing-header rejects!) ---
        srv_b, st_b = _make_enterprise_server(
            audit_path="/compliance",
            target_path="/settle",
            target_btn="Dispatch Transfer",
            code_val="TREASURY-4401",
            required_idem_header="Idempotency-Key",
            inject_429_on_audit=False,
            inject_503_on_post=False,
        )
        try:
            url_b = f"http://127.0.0.1:{srv_b.server_address[1]}/"
            out_b = self.model.solve(
                f"Dispatch transfer on {url_b}",
                mode="EPISTEMIC",
                inputs={"web_url": url_b, "memory": mem},
            )
            self.assertTrue(out_b["pass"], out_b)
            er_b = out_b["epistemic_result"]
            self.assertEqual(er_b["mode"], "TIER0_WORLD_MODEL_PLAN")
            self.assertEqual(er_b["failed_probes"], 0)
            self.assertEqual(er_b["idempotency_recoveries"], 0)
            self.assertEqual(st_b["missing_idem_rejects"], 0)
            self.assertGreaterEqual(er_b["pages_traversed"], 2)
            self.assertTrue(st_b["completed"])

            # --- Phase 3: Live Idempotency Policy Drift (`Idempotency-Key` -> `X-Request-Idempotency`) ---
            st_b["required_idem_header"] = "X-Request-Idempotency"
            st_b["completed"] = False
            out_drift = self.model.solve(
                f"Dispatch transfer on {url_b}",
                mode="EPISTEMIC",
                inputs={"web_url": url_b, "memory": mem},
            )
            self.assertTrue(out_drift["pass"], out_drift)
            er_d = out_drift["epistemic_result"]
            self.assertGreaterEqual(er_d["policy_drift_quarantines"], 1)
            self.assertGreaterEqual(er_d["idempotency_recoveries"], 1)
            self.assertEqual(mem["world_model_plans"][plan_id]["protocol_laws"]["idempotency_header"], "X-Request-Idempotency")

            # Subsequent call transfers newly learned `X-Request-Idempotency` at Tier-0 (0 rejects!)
            st_b["completed"] = False
            prev_rej = st_b["missing_idem_rejects"]
            out_b2 = self.model.solve(
                f"Dispatch transfer on {url_b}",
                mode="EPISTEMIC",
                inputs={"web_url": url_b, "memory": mem},
            )
            self.assertTrue(out_b2["pass"], out_b2)
            er_b2 = out_b2["epistemic_result"]
            self.assertEqual(er_b2["mode"], "TIER0_WORLD_MODEL_PLAN")
            self.assertEqual(er_b2["idempotency_recoveries"], 0)
            self.assertEqual(st_b["missing_idem_rejects"], prev_rej)

            # Explicit Instant Unlearning
            self.assertTrue(UEK.delete_memory_entry(mem, plan_id))
            self.assertNotIn(plan_id, mem["world_model_plans"])
        finally:
            srv_b.shutdown()
            srv_b.server_close()


if __name__ == "__main__":
    unittest.main()
