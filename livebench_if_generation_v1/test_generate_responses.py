"""Tests for the fail-closed LiveBench-IF response generator (mock endpoint only; no real network)."""
from __future__ import annotations

import datetime as dt
import json
import tempfile
import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from livebench_if_generation_v1 import generate_responses as gr

HERE = Path(__file__).resolve().parent
SECRET = "sk-test-SECRET-never-in-outputs"
MODEL = "@cf/qwen/qwen3.8-27b"
PRICES = json.loads((HERE / "prices_workers_ai_v1.json").read_text())["models"]


class Mock:
    """Tiny endpoint speaking the three supported styles. Records every request."""

    def __init__(self, style: str, fail_first: int = 0, fail_status: int = 500, usage: bool = True):
        self.style, self.fail_first, self.fail_status, self.usage = style, fail_first, fail_status, usage
        self.requests: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                if len(outer.requests) <= outer.fail_first:
                    self.send_response(outer.fail_status)
                    self.end_headers()
                    self.wfile.write(b"{}")
                    return
                user = [m for m in body["messages"] if m["role"] == "user"][-1]["content"]
                text = "RESPONSE::" + user
                use = {"prompt_tokens": 100, "completion_tokens": 50}
                if outer.style == "plain":
                    payload, ctype = text.encode(), "text/plain"
                elif outer.style == "cf-run-response-shape":
                    payload, ctype = json.dumps({"result": {"response": text, **({"usage": use} if outer.usage else {})}, "success": True}).encode(), "application/json"
                elif outer.style == "cf-run-choices-shape":
                    payload, ctype = json.dumps({"result": {"choices": [{"message": {"content": text}}], **({"usage": use} if outer.usage else {}), "model": "mock-returned"}, "success": True}).encode(), "application/json"
                else:
                    payload, ctype = json.dumps({"choices": [{"message": {"content": text}}], **({"usage": use} if outer.usage else {}), "model": "mock-returned"}).encode(), "application/json"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.mocks: list[Mock] = []

    def tearDown(self):
        for m in self.mocks:
            m.close()
        self.tmp.cleanup()

    def mock(self, *a, **k) -> Mock:
        m = Mock(*a, **k)
        self.mocks.append(m)
        return m

    def questions(self, rows, name="q.jsonl") -> Path:
        p = self.dir / name
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        return p

    def config(self, system=True, max_out=200, cid="TEST_CFG") -> Path:
        p = self.dir / f"cfg_{cid}.json"
        p.write_text(json.dumps({"config_id": cid, "system_prompt": "be exact" if system else None, "max_completion_tokens": max_out}))
        return p

    def run_gen(self, mock: Mock, qpath: Path, cpath: Path, out=None, style="openai", **kw):
        if style == "openai":
            tr = gr.OpenAITransport(mock.url, SECRET)
        elif style == "cf-run":
            tr = gr.CfRunTransport("ACCT", SECRET, base_url=mock.url)
        else:
            tr = gr.PlainTransport(mock.url + "/")
        if not any(k in kw for k in ("frozen_release", "frozen_release_min", "assert_no_frozen_questions")):
            kw["assert_no_frozen_questions"] = True  # tests that are not about the frozen policy state it explicitly
        return gr.run(questions_path=qpath, config_path=cpath, out_dir=out or self.dir / "out", model_id=kw.pop("model_id", MODEL),
                      transport=tr, sleep=lambda s: None, **kw)


ROWS3 = [{"question_id": f"q{i}", "prompt": f"prompt-{i}"} for i in (1, 2, 3)]


class HappyPathAndSecrets(Base):
    def test_openai_style_end_to_end_with_adapter_preflight(self):
        m = self.mock("openai")
        s = self.run_gen(m, self.questions(ROWS3), self.config(), max_total_tokens=100_000)
        self.assertEqual((s["status"], s["answered"], s["calls_made_this_run"]), ("COMPLETE", 3, 3))
        self.assertEqual(len(m.requests), 3)
        for r in m.requests:
            self.assertEqual(r["path"], "/chat/completions")
            self.assertEqual(r["auth"], f"Bearer {SECRET}")
            self.assertEqual(r["body"]["messages"][0], {"role": "system", "content": "be exact"})
            self.assertEqual(r["body"]["max_completion_tokens"], 200)
        out = self.dir / "out"
        recs = [json.loads(x) for x in (out / "responses.jsonl").read_text().splitlines()]
        self.assertEqual([r["question_id"] for r in recs], ["q1", "q2", "q3"])
        self.assertEqual(recs[0]["response"], "RESPONSE::prompt-1")
        self.assertTrue(s["provenance_chain_ok"])
        self.assertEqual(s["adapter_preflight"]["status"], "PASS")
        self.assertEqual(s["adapter_preflight"]["content_inspected"], False)
        answers = json.loads((out / "model_answers.json").read_text())
        self.assertEqual(answers["brain"]["q2"]["choices"][0]["turns"], ["RESPONSE::prompt-2"])
        self.assertIs(s["execution_authority"], False)
        self.assertEqual((s["capability_credit_delta"], s["incremental_spend_usd"]), (0, 0))

    def test_secret_is_never_written_anywhere(self):
        m = self.mock("openai")
        self.run_gen(m, self.questions(ROWS3), self.config(), max_total_tokens=100_000)
        for p in (self.dir / "out").rglob("*"):
            if p.is_file():
                self.assertNotIn(SECRET, p.read_text(), p.name)

    def test_no_system_message_when_policy_absent_and_hash_binds_config(self):
        m = self.mock("openai")
        c_raw, c_pol = self.config(system=False, cid="RAW"), self.config(system=True, cid="POL")
        self.run_gen(m, self.questions(ROWS3[:1]), c_raw, out=self.dir / "a", max_total_tokens=10_000)
        self.run_gen(m, self.questions(ROWS3[:1]), c_pol, out=self.dir / "b", max_total_tokens=10_000)
        self.assertEqual([x["role"] for x in m.requests[0]["body"]["messages"]], ["user"])
        self.assertEqual([x["role"] for x in m.requests[1]["body"]["messages"]], ["system", "user"])
        pa = json.loads((self.dir / "a" / "provenance.jsonl").read_text().splitlines()[0])
        pb = json.loads((self.dir / "b" / "provenance.jsonl").read_text().splitlines()[0])
        self.assertNotEqual(pa["config_sha256"], pb["config_sha256"])
        self.assertNotEqual(pa["request_sha256"], pb["request_sha256"])
        self.assertEqual((pa["config_id"], pb["config_id"]), ("RAW", "POL"))


class Budget(Base):
    def test_token_cap_stops_before_exceeding(self):
        m = self.mock("openai")
        s = self.run_gen(m, self.questions(ROWS3), self.config(max_out=200), max_total_tokens=400)
        self.assertEqual(s["status"], "STOPPED_AT_BUDGET_CAP")
        self.assertEqual(s["stop_reason"], "TOKEN_CAP_WOULD_BE_EXCEEDED")
        self.assertEqual((s["answered"], len(m.requests)), (2, 2))
        self.assertLessEqual(s["ledger"]["total_tokens"], 400)
        self.assertIsNone(s["adapter_preflight"])

    def test_neuron_cap_per_utc_day_then_resume_next_day_without_duplicates(self):
        m = self.mock("openai")
        rows = [{"question_id": f"q{i}", "prompt": f"prompt-{i}"} for i in range(1, 6)]
        q, c = self.questions(rows), self.config(max_out=200)
        day1 = lambda: dt.datetime(2026, 10, 2, 12, tzinfo=dt.timezone.utc)
        day2 = lambda: dt.datetime(2026, 10, 3, 1, tzinfo=dt.timezone.utc)
        s1 = self.run_gen(m, q, c, max_neurons_per_day=100, prices=PRICES, clock=day1)
        self.assertEqual((s1["status"], s1["stop_reason"], s1["answered"]), ("STOPPED_AT_BUDGET_CAP", "NEURON_CAP_WOULD_BE_EXCEEDED_TODAY", 3))
        self.assertLessEqual(s1["ledger"]["days"]["2026-10-02"]["neurons"], 100)
        s2 = self.run_gen(m, q, c, max_neurons_per_day=100, prices=PRICES, clock=day2)
        self.assertEqual((s2["status"], s2["answered"], s2["calls_made_this_run"]), ("COMPLETE", 5, 2))
        self.assertEqual(len(m.requests), 5, "resume must not repeat answered questions")
        self.assertEqual(sorted(s2["ledger"]["days"]), ["2026-10-02", "2026-10-03"])
        self.assertTrue(s2["provenance_chain_ok"])

    def test_neurons_are_computed_from_reported_usage(self):
        m = self.mock("openai")
        s = self.run_gen(m, self.questions(ROWS3[:1]), self.config(), max_neurons_per_day=1000, prices=PRICES,
                         clock=lambda: dt.datetime(2026, 10, 2, tzinfo=dt.timezone.utc))
        expected = (100 * PRICES[MODEL]["input"] + 50 * PRICES[MODEL]["output"]) / 1e6
        self.assertAlmostEqual(s["ledger"]["days"]["2026-10-02"]["neurons"], expected, places=4)
        prov = json.loads((self.dir / "out" / "provenance.jsonl").read_text().splitlines()[0])
        self.assertAlmostEqual(prov["neurons"], expected, places=4)
        self.assertEqual(prov["usage"], {"prompt": 100, "completion": 50, "reported_by_endpoint": True})
        self.assertEqual(prov["returned_model"], "mock-returned")

    def test_a_budget_cap_is_mandatory(self):
        m = self.mock("openai")
        with self.assertRaises(gr.Blocked) as cm:
            self.run_gen(m, self.questions(ROWS3), self.config())
        self.assertIn("BUDGET_CAP_IS_REQUIRED", str(cm.exception))
        self.assertEqual(len(m.requests), 0)

    def test_cf_run_refuses_without_neuron_cap_and_prices_zero_spend_by_construction(self):
        m = self.mock("cf-run-response-shape")
        for kw in ({}, {"max_total_tokens": 10_000}, {"max_neurons_per_day": 100}):
            with self.subTest(kw=kw), self.assertRaises(gr.Blocked):
                self.run_gen(m, self.questions(ROWS3), self.config(), style="cf-run", **kw)
        self.assertEqual(len(m.requests), 0)

    def test_neuron_cap_needs_a_price_entry_for_the_model(self):
        m = self.mock("openai")
        with self.assertRaises(gr.Blocked):
            self.run_gen(m, self.questions(ROWS3), self.config(), max_neurons_per_day=50, prices=PRICES, model_id="@cf/unknown/model")
        self.assertEqual(len(m.requests), 0)


class FrozenProtection(Base):
    FROZEN = "2026-06-25"

    def rows(self):
        return [{"question_id": "d1", "prompt": "dev-1", "livebench_release_date": "2026-05-01"},
                {"question_id": "f1", "prompt": "frozen-1", "livebench_release_date": self.FROZEN}]

    def auth(self, q: Path, c: Path, **override) -> Path:
        body = {"schema": gr.AUTH_SCHEMA, "execution_authority": True, "frozen_rule": self.FROZEN, "model_id": MODEL,
                "questions_sha256": gr.sha256_file(q), "config_sha256": gr.sha256_file(c)}
        body.update(override)
        p = self.dir / "auth.json"
        p.write_text(json.dumps(body))
        return p

    def test_frozen_rows_without_authorization_send_nothing(self):
        m = self.mock("openai")
        with self.assertRaises(gr.FrozenBlocked) as cm:
            self.run_gen(m, self.questions(self.rows()), self.config(), max_total_tokens=10_000, frozen_release=self.FROZEN)
        self.assertEqual(cm.exception.code, 3)
        self.assertEqual(len(m.requests), 0)
        self.assertFalse((self.dir / "out" / "responses.jsonl").exists())

    def test_dev_only_questions_do_not_need_authorization(self):
        m = self.mock("openai")
        rows = [r for r in self.rows() if r["question_id"] == "d1"]
        s = self.run_gen(m, self.questions(rows), self.config(), max_total_tokens=10_000, frozen_release=self.FROZEN)
        self.assertEqual((s["status"], s["frozen"]["frozen_questions"]), ("COMPLETE", 0))

    def test_each_authorization_field_is_checked_before_any_request(self):
        q, c = self.questions(self.rows()), self.config()
        for field, bad in (("execution_authority", False), ("model_id", "other"), ("questions_sha256", "0" * 64),
                           ("config_sha256", "0" * 64), ("frozen_rule", "2025-01-01"), ("schema", "WRONG")):
            m = self.mock("openai")
            a = self.auth(q, c, **{field: bad})
            with self.subTest(field=field), self.assertRaises(gr.FrozenBlocked) as cm:
                self.run_gen(m, q, c, max_total_tokens=10_000, frozen_release=self.FROZEN, authorization_path=a, out=self.dir / f"o_{field}")
            self.assertIn(field, str(cm.exception))
            self.assertEqual(len(m.requests), 0)

    def test_changing_the_questions_file_invalidates_the_authorization(self):
        q, c = self.questions(self.rows()), self.config()
        a = self.auth(q, c)
        q.write_text(q.read_text() + json.dumps({"question_id": "x", "prompt": "p", "livebench_release_date": "2026-05-01"}) + "\n")
        m = self.mock("openai")
        with self.assertRaises(gr.FrozenBlocked):
            self.run_gen(m, q, c, max_total_tokens=10_000, frozen_release=self.FROZEN, authorization_path=a)
        self.assertEqual(len(m.requests), 0)

    def test_exact_authorization_allows_the_run(self):
        q, c = self.questions(self.rows()), self.config()
        m = self.mock("openai")
        s = self.run_gen(m, q, c, max_total_tokens=10_000, frozen_release=self.FROZEN, authorization_path=self.auth(q, c))
        self.assertEqual((s["status"], s["answered"]), ("COMPLETE", 2))
        self.assertEqual(s["frozen"], {"frozen_questions": 1, "authorized": True, "policy": "RULE", "rule": self.FROZEN})

    def test_a_frozen_policy_must_be_chosen_explicitly(self):
        m = self.mock("openai")
        with self.assertRaises(gr.Blocked) as cm:
            gr.run(questions_path=self.questions(self.rows()), config_path=self.config(), out_dir=self.dir / "o",
                   model_id=MODEL, transport=gr.OpenAITransport(m.url, SECRET), max_total_tokens=10_000, sleep=lambda s: None)
        self.assertIn("FROZEN_POLICY_REQUIRED", str(cm.exception))
        self.assertEqual(len(m.requests), 0)

    def test_assert_none_cannot_be_combined_with_a_rule(self):
        m = self.mock("openai")
        for kw in ({"frozen_release": self.FROZEN}, {"frozen_release_min": "2025-11-25"}):
            with self.subTest(kw=kw), self.assertRaises(gr.Blocked) as cm:
                self.run_gen(m, self.questions(self.rows()), self.config(), max_total_tokens=10_000, assert_no_frozen_questions=True, **kw)
            self.assertIn("FROZEN_POLICY_CONFLICT", str(cm.exception))
        self.assertEqual(len(m.requests), 0)

    def test_minimum_date_rule_covers_every_later_release(self):
        rows = [{"question_id": "old", "prompt": "o", "livebench_release_date": "2025-11-24"},
                {"question_id": "edge", "prompt": "e", "livebench_release_date": "2025-11-25"},
                {"question_id": "new", "prompt": "n", "livebench_release_date": "2026-01-08"}]
        m = self.mock("openai")
        with self.assertRaises(gr.FrozenBlocked):
            self.run_gen(m, self.questions(rows), self.config(), max_total_tokens=10_000, frozen_release_min="2025-11-25")
        self.assertEqual(len(m.requests), 0)
        s = self.run_gen(m, self.questions(rows[:1], name="old.jsonl"), self.config(), max_total_tokens=10_000,
                         frozen_release_min="2025-11-25", out=self.dir / "dev")
        self.assertEqual((s["status"], s["frozen"]["frozen_questions"], s["frozen"]["rule"]), ("COMPLETE", 0, ">=2025-11-25"))

    def test_unknown_release_date_is_treated_as_frozen(self):
        rows = [{"question_id": "u", "prompt": "no release field"}]
        m = self.mock("openai")
        with self.assertRaises(gr.FrozenBlocked):
            self.run_gen(m, self.questions(rows), self.config(), max_total_tokens=10_000, frozen_release="2025-11-25")
        self.assertEqual(len(m.requests), 0)

    def test_release_dates_are_normalized_and_exact_lists_work(self):
        self.assertEqual(gr.normalize_release("2025-11-25T00:00:00"), "2025-11-25")
        self.assertEqual(gr.normalize_release("2025-11-25 00:00:00+00:00"), "2025-11-25")
        self.assertIsNone(gr.normalize_release("R"))
        self.assertIsNone(gr.normalize_release(None))
        rows = [{"question_id": "a", "prompt": "a", "livebench_release_date": "2025-11-25T00:00:00"}]
        m = self.mock("openai")
        with self.assertRaises(gr.FrozenBlocked):
            self.run_gen(m, self.questions(rows), self.config(), max_total_tokens=10_000, frozen_release="2026-01-08, 2025-11-25")
        self.assertEqual(len(m.requests), 0)
        with self.assertRaises(gr.Blocked) as cm:
            self.run_gen(m, self.questions(rows), self.config(), max_total_tokens=10_000, frozen_release="not-a-date")
        self.assertIn("NOT_AN_ISO_DATE", str(cm.exception))


class Provenance(Base):
    def test_chain_detects_tampering_and_resume_refuses(self):
        m = self.mock("openai")
        q, c = self.questions(ROWS3), self.config()
        self.run_gen(m, q, c, max_total_tokens=100_000)
        p = self.dir / "out" / "provenance.jsonl"
        self.assertTrue(gr.verify_chain(p)[0])
        lines = p.read_text().splitlines()
        rec = json.loads(lines[1])
        rec["usage"]["completion"] = 1  # falsify usage
        lines[1] = gr.canonical(rec)
        p.write_text("\n".join(lines) + "\n")
        self.assertFalse(gr.verify_chain(p)[0])
        with self.assertRaises(gr.Blocked) as cm:
            self.run_gen(m, q, c, max_total_tokens=100_000)
        self.assertIn("PROVENANCE_CHAIN_BROKEN", str(cm.exception))

    def test_deleted_or_reordered_lines_break_the_chain(self):
        m = self.mock("openai")
        self.run_gen(m, self.questions(ROWS3), self.config(), max_total_tokens=100_000)
        p = self.dir / "out" / "provenance.jsonl"
        lines = p.read_text().splitlines()
        p.write_text("\n".join([lines[0], lines[2]]) + "\n")
        self.assertFalse(gr.verify_chain(p)[0])


class Transports(Base):
    def test_retry_then_success_records_the_attempt(self):
        m = self.mock("openai", fail_first=1, fail_status=500)
        s = self.run_gen(m, self.questions(ROWS3[:1]), self.config(), max_total_tokens=10_000)
        self.assertEqual(s["status"], "COMPLETE")
        self.assertEqual(len(m.requests), 2)
        self.assertEqual(json.loads((self.dir / "out" / "provenance.jsonl").read_text().splitlines()[0])["attempt"], 2)
        self.assertEqual(s["ledger"]["calls"], 1, "a failed attempt must not be counted as spend")

    def test_rate_limit_is_retryable_but_client_errors_are_not(self):
        m = self.mock("openai", fail_first=1, fail_status=429)
        self.assertEqual(self.run_gen(m, self.questions(ROWS3[:1]), self.config(), max_total_tokens=10_000)["status"], "COMPLETE")
        m2 = self.mock("openai", fail_first=99, fail_status=400)
        s = self.run_gen(m2, self.questions(ROWS3[:1]), self.config(), max_total_tokens=10_000, out=self.dir / "o2")
        self.assertEqual((s["status"], s["stop_reason"], len(m2.requests)), ("STOPPED_TRANSPORT_FAILURE", "HTTP_400", 1))

    def test_persistent_server_error_stops_after_max_attempts_leaving_partial_state_resumable(self):
        m = self.mock("openai", fail_first=99, fail_status=503)
        s = self.run_gen(m, self.questions(ROWS3), self.config(), max_total_tokens=10_000, max_attempts=3)
        self.assertEqual((s["status"], s["answered"], len(m.requests)), ("STOPPED_TRANSPORT_FAILURE", 0, 3))
        self.assertEqual(s["ledger"]["calls"], 0)

    def test_plain_style_has_no_usage_so_tokens_are_estimated_and_still_capped(self):
        m = self.mock("plain")
        # estimated usage per call is 12 tokens (6 in + 6 out); worst-case pre-check is est_in + max_out = 206.
        # cap 215 allows the first call (206 <= 215) and forbids the second (12 + 206 = 218 > 215).
        s = self.run_gen(m, self.questions(ROWS3), self.config(max_out=200), style="plain", max_total_tokens=215)
        self.assertEqual((s["status"], s["answered"], len(m.requests)), ("STOPPED_AT_BUDGET_CAP", 1, 1))
        self.assertEqual(s["ledger"]["total_tokens"], 12)
        prov = json.loads((self.dir / "out" / "provenance.jsonl").read_text().splitlines()[0])
        self.assertFalse(prov["usage"]["reported_by_endpoint"])
        self.assertEqual(m.requests[0]["body"].keys(), {"messages", "model"})

    def test_cf_run_parses_both_response_shapes_and_sends_no_model_in_body(self):
        for shape in ("cf-run-response-shape", "cf-run-choices-shape"):
            m = self.mock(shape)
            s = self.run_gen(m, self.questions(ROWS3[:1]), self.config(), style="cf-run", out=self.dir / shape,
                             max_neurons_per_day=500, prices=PRICES, clock=lambda: dt.datetime(2026, 10, 2, tzinfo=dt.timezone.utc))
            with self.subTest(shape=shape):
                self.assertEqual(s["status"], "COMPLETE")
                self.assertEqual(m.requests[0]["path"], f"/accounts/ACCT/ai/run/{MODEL}")
                self.assertNotIn("model", m.requests[0]["body"])
                self.assertEqual(m.requests[0]["auth"], f"Bearer {SECRET}")

    def test_missing_usage_falls_back_to_estimate_and_flags_it(self):
        m = self.mock("openai", usage=False)
        s = self.run_gen(m, self.questions(ROWS3[:1]), self.config(), max_total_tokens=10_000)
        prov = json.loads((self.dir / "out" / "provenance.jsonl").read_text().splitlines()[0])
        self.assertFalse(prov["usage"]["reported_by_endpoint"])
        self.assertGreater(s["ledger"]["total_tokens"], 0)


class Validation(Base):
    def test_question_file_validation(self):
        bad = {
            "duplicate": [{"question_id": "a", "prompt": "x"}, {"question_id": "a", "prompt": "y"}],
            "missing_prompt": [{"question_id": "a"}],
            "bool_id": [{"question_id": True, "prompt": "x"}],
            "empty_id": [{"question_id": " ", "prompt": "x"}],
        }
        for name, rows in bad.items():
            with self.subTest(case=name), self.assertRaises(gr.Blocked):
                gr.load_questions(self.questions(rows, name=f"{name}.jsonl"))
        ok = gr.load_questions(self.questions([{"question_id": 7, "turns": ["from turns"]}], name="turns.jsonl"))
        self.assertEqual(ok[0]["prompt"], "from turns")

    def test_config_validation(self):
        for body in ({"system_prompt": "x", "max_completion_tokens": 10},
                     {"config_id": "A", "max_completion_tokens": 0},
                     {"config_id": "A", "max_completion_tokens": True},
                     {"config_id": "A", "system_prompt": 5, "max_completion_tokens": 10}):
            p = self.dir / "bad_cfg.json"
            p.write_text(json.dumps(body))
            with self.subTest(body=body), self.assertRaises(gr.Blocked):
                gr.load_config(p)

    def test_shipped_configs_are_valid_and_differ_only_by_policy(self):
        raw = gr.load_config(HERE / "brain_if_config_raw_v1.json")
        pol = gr.load_config(HERE / "brain_if_config_policy_v1.json")
        self.assertIsNone(raw["system_prompt"])
        self.assertTrue(pol["system_prompt"])
        self.assertEqual({k: v for k, v in raw.items() if k not in ("config_id", "purpose", "system_prompt")},
                         {k: v for k, v in pol.items() if k not in ("config_id", "purpose", "system_prompt")})
        self.assertNotIn("livebench", pol["system_prompt"].lower())  # benchmark-agnostic policy

    def test_shipped_price_table_matches_the_census_constants(self):
        census = json.loads((HERE.parent / "canonical/reasoning/2026-10-02_ZERO_COST_SUBSTRATE_ROUTE_CENSUS_V1.json").read_text())
        consts = {p["id"]: p for p in census["material_premises"]}["P6_COMPUTED_FREE_TIER_VS_ONE_PASS"]["evidence"]["constants"]
        for model, price in consts["models_neurons_per_million_tokens"].items():
            self.assertEqual(PRICES[model], {"input": price["input"], "output": price["output"]}, model)

    def test_cli_exit_codes(self):
        m = self.mock("plain")
        q, c = self.questions(ROWS3), self.config(max_out=200)
        base = ["--questions", str(q), "--config", str(c), "--model", "mock", "--api-style", "plain", "--base-url", m.url + "/",
                "--assert-no-frozen-questions"]
        self.assertEqual(gr.main(base + ["--out", str(self.dir / "o1"), "--max-total-tokens", "100000"]), 0)
        # plain style estimates 12 tokens per call; 215 allows only the first call (see the plain-style test)
        self.assertEqual(gr.main(base + ["--out", str(self.dir / "o2"), "--max-total-tokens", "215"]), 4)
        self.assertEqual(gr.main(base + ["--out", str(self.dir / "o3")]), 2)  # no cap
        no_policy = [a for a in base if a != "--assert-no-frozen-questions"] + ["--out", str(self.dir / "o5"), "--max-total-tokens", "100000"]
        self.assertEqual(gr.main(no_policy), 2)  # no frozen policy chosen
        fq = self.questions([{"question_id": "f", "prompt": "p", "livebench_release_date": "2025-11-25"}], name="f.jsonl")
        n_before = len(m.requests)
        code = gr.main(["--questions", str(fq), "--config", str(c), "--model", "mock", "--api-style", "plain", "--base-url", m.url + "/",
                        "--out", str(self.dir / "o4"), "--max-total-tokens", "1000", "--frozen-release-min", "2025-11-25"])
        self.assertEqual(code, 3)
        self.assertEqual(len(m.requests), n_before, "frozen refusal must precede any request")

    def test_estimate_is_conservative(self):
        self.assertEqual(gr.est_tokens("x" * 300), 100)
        self.assertEqual(gr.est_tokens(""), 1)


if __name__ == "__main__":
    unittest.main()
