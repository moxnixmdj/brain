#!/usr/bin/env python3
"""Fail-closed response generator for LiveBench-IF-shaped questions.

PROVISIONAL tooling: zero progress credit, no scoring, no capability claim.

What it does
------------
Reads a local questions file, asks an OpenAI-compatible / Cloudflare Workers AI /
plain-text endpoint for one response per question, and writes
``{question_id, response}`` records that the already independently verified
adapter ``canonical/runtime/livebench_if_response_adapter.py`` turns into the
LiveBench ``model_answers`` structure. Scoring is done elsewhere by the pinned,
independently verified scorer.

Safety properties enforced in code, before any network call where applicable
-----------------------------------------------------------------------------
* Budget cap, fail closed: a worst-case cost check runs BEFORE each call and the
  run stops (exit 4) instead of exceeding a token cap or a per-UTC-day neuron cap.
  The Cloudflare ``cf-run`` style refuses to start without a neuron cap and a price
  table, so zero spend is the default by construction.
* Frozen-set protection, explicit and fail closed: a frozen policy MUST be chosen
  (``--frozen-release`` exact dates, ``--frozen-release-min`` a minimum date, or
  ``--assert-no-frozen-questions``). A question is frozen if its release matches a rule
  or if its release date is unknown. Frozen questions are refused (exit 3) unless a
  content-addressed authorization file matches the exact questions file, config file,
  model id and rule. Nothing is sent before this check.
* Provenance: every call appends a hash-chained line (request/response digests,
  usage, neurons). API keys are read from the environment and never written.
* Resume: answered question ids are skipped; the provenance chain is verified first.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SUMMARY_SCHEMA = "PROJECT_BRAIN_LIVEBENCH_IF_GENERATION_SUMMARY_V1"
AUTH_SCHEMA = "PROJECT_BRAIN_LIVEBENCH_IF_FROZEN_ONE_SHOT_AUTHORIZATION_V1"
GENESIS = "0" * 64


class Blocked(Exception):
    code = 2


class FrozenBlocked(Blocked):
    code = 3


class BudgetStop(Exception):
    code = 4


class TransportFailed(Exception):
    code = 5


# --------------------------------------------------------------------------- helpers
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def est_tokens(text: str) -> int:
    """Conservative token estimate (3 characters per token)."""
    return max(1, math.ceil(len(text) / 3))


def utc_day(now: dt.datetime) -> str:
    return now.astimezone(dt.timezone.utc).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- questions
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def normalize_release(value: Any) -> str | None:
    """ISO date (YYYY-MM-DD) from a date, datetime or string; None when absent or unparseable."""
    if value is None:
        return None
    m = _DATE.match(str(value).strip())
    return m.group(1) if m else None


def load_questions(path: Path, id_field: str = "question_id", prompt_field: str = "prompt",
                   release_field: str = "livebench_release_date") -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not isinstance(rows, list) or not rows:
        raise Blocked("QUESTIONS_EMPTY_OR_NOT_A_LIST")
    out: list[dict[str, Any]] = []
    seen: set[Any] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise Blocked(f"QUESTION_ROW_NOT_AN_OBJECT:{i}")
        if id_field not in row:
            raise Blocked(f"QUESTION_ID_MISSING:{i}")
        qid = row[id_field]
        if isinstance(qid, bool) or not isinstance(qid, (int, str)) or (isinstance(qid, str) and not qid.strip()):
            raise Blocked(f"QUESTION_ID_INVALID:{i}")
        if qid in seen:
            raise Blocked(f"QUESTION_ID_DUPLICATE:{qid!r}")
        seen.add(qid)
        prompt = row.get(prompt_field)
        if not isinstance(prompt, str):
            turns = row.get("turns")
            prompt = turns[0] if isinstance(turns, list) and turns and isinstance(turns[0], str) else None
        if not isinstance(prompt, str) or not prompt.strip():
            raise Blocked(f"QUESTION_PROMPT_MISSING:{qid!r}")
        out.append({"question_id": qid, "prompt": prompt, "release": normalize_release(row.get(release_field))})
    return out


# --------------------------------------------------------------------------- config / frozen guard
def load_config(path: Path) -> dict[str, Any]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cfg, dict) or not isinstance(cfg.get("config_id"), str) or not cfg["config_id"]:
        raise Blocked("CONFIG_ID_MISSING")
    if cfg.get("system_prompt") is not None and not isinstance(cfg["system_prompt"], str):
        raise Blocked("CONFIG_SYSTEM_PROMPT_NOT_A_STRING")
    mct = cfg.get("max_completion_tokens")
    if isinstance(mct, bool) or not isinstance(mct, int) or mct <= 0:
        raise Blocked("CONFIG_MAX_COMPLETION_TOKENS_REQUIRED_POSITIVE_INT")
    return cfg


def frozen_rule_label(exact: Sequence[str], minimum: str | None) -> str:
    parts = []
    if exact:
        parts.append(",".join(sorted(exact)))
    if minimum:
        parts.append(">=" + minimum)
    return ";".join(parts)


def enforce_frozen_protection(questions: Sequence[Mapping[str, Any]], exact: Sequence[str], minimum: str | None,
                              assert_none: bool, authorization_path: Path | None, questions_path: Path,
                              config_path: Path, model_id: str) -> dict[str, Any]:
    exact = [normalize_release(x) or "" for x in exact]
    if any(not x for x in exact):
        raise Blocked("FROZEN_RELEASE_NOT_AN_ISO_DATE")
    minimum = normalize_release(minimum) if minimum else None
    if not exact and not minimum and not assert_none:
        raise Blocked("FROZEN_POLICY_REQUIRED__PASS_--frozen-release_OR_--frozen-release-min_OR_--assert-no-frozen-questions")
    if assert_none and (exact or minimum):
        raise Blocked("FROZEN_POLICY_CONFLICT__ASSERT_NONE_CANNOT_BE_COMBINED_WITH_A_FROZEN_RULE")
    if assert_none:
        return {"frozen_questions": 0, "authorized": False, "policy": "ASSERTED_NO_FROZEN_QUESTIONS"}

    def is_frozen(q: Mapping[str, Any]) -> bool:
        rel = q["release"]
        if rel is None:
            return True  # unknown release is treated as frozen (fail closed)
        return rel in exact or (minimum is not None and rel >= minimum)

    rule = frozen_rule_label(exact, minimum)
    frozen_ids = [q["question_id"] for q in questions if is_frozen(q)]
    if not frozen_ids:
        return {"frozen_questions": 0, "authorized": False, "policy": "RULE", "rule": rule}
    if authorization_path is None:
        raise FrozenBlocked("FROZEN_QUESTIONS_PRESENT_AND_NO_AUTHORIZATION")
    try:
        auth = json.loads(Path(authorization_path).read_text(encoding="utf-8"))
    except Exception as exc:  # unreadable or invalid JSON
        raise FrozenBlocked(f"AUTHORIZATION_UNREADABLE:{type(exc).__name__}")
    checks = {
        "schema": auth.get("schema") == AUTH_SCHEMA,
        "execution_authority": auth.get("execution_authority") is True,
        "frozen_rule": auth.get("frozen_rule") == rule,
        "model_id": auth.get("model_id") == model_id,
        "questions_sha256": auth.get("questions_sha256") == sha256_file(questions_path),
        "config_sha256": auth.get("config_sha256") == sha256_file(config_path),
    }
    bad = sorted(k for k, ok in checks.items() if not ok)
    if bad:
        raise FrozenBlocked("AUTHORIZATION_MISMATCH:" + ",".join(bad))
    return {"frozen_questions": len(frozen_ids), "authorized": True, "policy": "RULE", "rule": rule}


# --------------------------------------------------------------------------- budget
class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict[str, Any] = {"days": {}, "total_tokens": 0, "calls": 0}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.path)


class Budget:
    """Worst-case pre-check plus post-call accounting. Fails closed."""

    def __init__(self, ledger: Ledger, model_id: str, max_total_tokens: int | None,
                 max_neurons_per_day: float | None, prices: Mapping[str, Any] | None,
                 clock: Callable[[], dt.datetime]):
        self.ledger, self.model_id, self.clock = ledger, model_id, clock
        self.max_total_tokens, self.max_neurons_per_day = max_total_tokens, max_neurons_per_day
        self.price = None
        if prices is not None:
            entry = prices.get(model_id)
            if not isinstance(entry, Mapping) or "input" not in entry or "output" not in entry:
                raise Blocked("PRICE_TABLE_HAS_NO_ENTRY_FOR_MODEL")
            self.price = (float(entry["input"]), float(entry["output"]))  # neurons per million tokens
        if max_neurons_per_day is not None and self.price is None:
            raise Blocked("NEURON_CAP_REQUIRES_PRICE_TABLE")

    def neurons(self, tokens_in: int, tokens_out: int) -> float | None:
        if self.price is None:
            return None
        return (tokens_in * self.price[0] + tokens_out * self.price[1]) / 1e6

    def precheck(self, est_in: int, max_out: int) -> None:
        if self.max_total_tokens is not None and self.ledger.data["total_tokens"] + est_in + max_out > self.max_total_tokens:
            raise BudgetStop("TOKEN_CAP_WOULD_BE_EXCEEDED")
        if self.max_neurons_per_day is not None:
            day = utc_day(self.clock())
            used = self.ledger.data["days"].get(day, {}).get("neurons", 0.0)
            worst = self.neurons(est_in, max_out)
            if used + worst > self.max_neurons_per_day:
                raise BudgetStop("NEURON_CAP_WOULD_BE_EXCEEDED_TODAY")

    def commit(self, tokens_in: int, tokens_out: int) -> float | None:
        n = self.neurons(tokens_in, tokens_out)
        day = utc_day(self.clock())
        d = self.ledger.data["days"].setdefault(day, {"neurons": 0.0, "calls": 0})
        d["calls"] += 1
        if n is not None:
            d["neurons"] = round(d["neurons"] + n, 6)
        self.ledger.data["total_tokens"] += tokens_in + tokens_out
        self.ledger.data["calls"] += 1
        self.ledger.save()
        return n


# --------------------------------------------------------------------------- transports
class Transport:
    style = "abstract"

    def call(self, messages: list[dict[str, str]], model_id: str, cfg: Mapping[str, Any], timeout: float) -> dict[str, Any]:
        raise NotImplementedError

    def request_body(self, messages: list[dict[str, str]], model_id: str, cfg: Mapping[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _post(url: str, body: dict[str, Any], headers: Mapping[str, str], timeout: float) -> bytes:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "ProjectBrain-LiveBenchIF-Gen/1", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(4_000_000)


def _extract(obj: Mapping[str, Any]) -> tuple[str, int | None, int | None, str | None]:
    node = obj.get("result") if isinstance(obj.get("result"), Mapping) else obj
    text = None
    choices = node.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], Mapping):
        msg = choices[0].get("message")
        if isinstance(msg, Mapping) and isinstance(msg.get("content"), str):
            text = msg["content"]
    if text is None and isinstance(node.get("response"), str):
        text = node["response"]
    if not isinstance(text, str):
        raise TransportFailed("RESPONSE_HAS_NO_TEXT")
    usage = node.get("usage") if isinstance(node.get("usage"), Mapping) else {}
    tin, tout = usage.get("prompt_tokens"), usage.get("completion_tokens")
    tin = tin if isinstance(tin, int) and not isinstance(tin, bool) else None
    tout = tout if isinstance(tout, int) and not isinstance(tout, bool) else None
    model = node.get("model") if isinstance(node.get("model"), str) else None
    return text, tin, tout, model


class OpenAITransport(Transport):
    style = "openai"

    def __init__(self, base_url: str, api_key: str):
        self.base_url, self.api_key = base_url.rstrip("/"), api_key

    def request_body(self, messages, model_id, cfg):
        body = {"model": model_id, "messages": messages, "max_completion_tokens": cfg["max_completion_tokens"]}
        for k in ("temperature", "top_p", "seed", "reasoning_effort"):
            if cfg.get(k) is not None:
                body[k] = cfg[k]
        return body

    def call(self, messages, model_id, cfg, timeout):
        raw = _post(self.base_url + "/chat/completions", self.request_body(messages, model_id, cfg),
                    {"Authorization": f"Bearer {self.api_key}"}, timeout)
        text, tin, tout, model = _extract(json.loads(raw))
        return {"text": text, "tokens_in": tin, "tokens_out": tout, "returned_model": model}


class CfRunTransport(OpenAITransport):
    style = "cf-run"

    def __init__(self, account_id: str, api_key: str, base_url: str = "https://api.cloudflare.com/client/v4"):
        super().__init__(base_url, api_key)
        self.account_id = account_id

    def call(self, messages, model_id, cfg, timeout):
        url = f"{self.base_url}/accounts/{self.account_id}/ai/run/{model_id}"
        body = self.request_body(messages, model_id, cfg)
        body.pop("model", None)
        raw = _post(url, body, {"Authorization": f"Bearer {self.api_key}"}, timeout)
        text, tin, tout, model = _extract(json.loads(raw))
        return {"text": text, "tokens_in": tin, "tokens_out": tout, "returned_model": model}


class PlainTransport(Transport):
    """Verified Pollinations-style transport: POST {messages, model} -> plain text, no usage."""
    style = "plain"

    def __init__(self, url: str):
        self.url = url

    def request_body(self, messages, model_id, cfg):
        return {"messages": messages, "model": model_id}

    def call(self, messages, model_id, cfg, timeout):
        raw = _post(self.url, self.request_body(messages, model_id, cfg), {}, timeout).decode("utf-8", "replace")
        return {"text": raw, "tokens_in": None, "tokens_out": None, "returned_model": None}


# --------------------------------------------------------------------------- provenance
class Provenance:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.prev = GENESIS
        self.seq = 0
        if self.path.exists() and self.path.stat().st_size:
            ok, prev, seq = verify_chain(self.path)
            if not ok:
                raise Blocked("PROVENANCE_CHAIN_BROKEN__REFUSING_TO_RESUME")
            self.prev, self.seq = prev, seq

    def append(self, record: dict[str, Any]) -> None:
        self.seq += 1
        rec = {"seq": self.seq, **record, "prev_hash": self.prev}
        rec["line_hash"] = sha256_bytes((self.prev + canonical(rec)).encode("utf-8"))
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(canonical(rec) + "\n")
            fh.flush()
        self.prev = rec["line_hash"]


def verify_chain(path: Path) -> tuple[bool, str, int]:
    prev, seq = GENESIS, 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        claimed = rec.pop("line_hash", None)
        if rec.get("prev_hash") != prev or rec.get("seq") != seq + 1:
            return False, prev, seq
        if sha256_bytes((prev + canonical(rec)).encode("utf-8")) != claimed:
            return False, prev, seq
        prev, seq = claimed, seq + 1
    return True, prev, seq


# --------------------------------------------------------------------------- core run
def run(*, questions_path: Path, config_path: Path, out_dir: Path, model_id: str, transport: Transport,
        max_total_tokens: int | None = None, max_neurons_per_day: float | None = None,
        prices: Mapping[str, Any] | None = None, frozen_release: str | None = None,
        frozen_release_min: str | None = None, assert_no_frozen_questions: bool = False,
        authorization_path: Path | None = None, id_field: str = "question_id", prompt_field: str = "prompt",
        release_field: str = "livebench_release_date", max_attempts: int = 3, timeout: float = 120.0,
        clock: Callable[[], dt.datetime] | None = None, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
    cfg = load_config(config_path)
    questions = load_questions(questions_path, id_field, prompt_field, release_field)
    exact = [x.strip() for x in (frozen_release or "").split(",") if x.strip()]
    frozen = enforce_frozen_protection(questions, exact, frozen_release_min, assert_no_frozen_questions,
                                       authorization_path, questions_path, config_path, model_id)
    if isinstance(transport, CfRunTransport) and (max_neurons_per_day is None or prices is None):
        raise Blocked("CF_RUN_REQUIRES_NEURON_CAP_AND_PRICE_TABLE__ZERO_SPEND_BY_CONSTRUCTION")
    if max_total_tokens is None and max_neurons_per_day is None:
        raise Blocked("A_BUDGET_CAP_IS_REQUIRED")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    resp_path, prov_path = out_dir / "responses.jsonl", out_dir / "provenance.jsonl"
    done: set[Any] = set()
    if resp_path.exists():
        for line in resp_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["question_id"])
    prov = Provenance(prov_path)
    ledger = Ledger(out_dir / "ledger.json")
    budget = Budget(ledger, model_id, max_total_tokens, max_neurons_per_day, prices, clock)
    config_sha, questions_sha = sha256_file(config_path), sha256_file(questions_path)
    status, stop_reason, calls_made = "COMPLETE", None, 0

    for q in questions:
        if q["question_id"] in done:
            continue
        messages = ([{"role": "system", "content": cfg["system_prompt"]}] if cfg.get("system_prompt") else []) + \
                   [{"role": "user", "content": q["prompt"]}]
        est_in = sum(est_tokens(m["content"]) for m in messages)
        try:
            budget.precheck(est_in, cfg["max_completion_tokens"])
        except BudgetStop as exc:
            status, stop_reason = "STOPPED_AT_BUDGET_CAP", str(exc)
            break
        request_sha = sha256_bytes(canonical(transport.request_body(messages, model_id, cfg)).encode("utf-8"))
        result, attempt = None, 0
        while attempt < max_attempts:
            attempt += 1
            try:
                result = transport.call(messages, model_id, cfg, timeout)
                break
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or exc.code >= 500
                if not retryable or attempt >= max_attempts:
                    status, stop_reason = "STOPPED_TRANSPORT_FAILURE", f"HTTP_{exc.code}"
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt >= max_attempts:
                    status, stop_reason = "STOPPED_TRANSPORT_FAILURE", type(exc).__name__
                    break
            sleep(min(2 ** attempt, 30))
        if result is None:
            status = "STOPPED_TRANSPORT_FAILURE"
            stop_reason = stop_reason or "NO_RESULT"
            break
        reported = result["tokens_in"] is not None and result["tokens_out"] is not None
        tin = result["tokens_in"] if reported else est_in
        tout = result["tokens_out"] if reported else est_tokens(result["text"])
        neurons = budget.commit(tin, tout)
        calls_made += 1
        prov.append({"ts_utc": clock().astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "question_id": q["question_id"], "attempt": attempt, "model_id": model_id,
                     "returned_model": result["returned_model"], "config_id": cfg["config_id"], "config_sha256": config_sha,
                     "request_sha256": request_sha, "response_sha256": sha256_bytes(result["text"].encode("utf-8")),
                     "usage": {"prompt": tin, "completion": tout, "reported_by_endpoint": reported}, "neurons": neurons})
        with resp_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"question_id": q["question_id"], "response": result["text"]}, ensure_ascii=False) + "\n")
            fh.flush()
        done.add(q["question_id"])

    summary: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA, "status": status, "stop_reason": stop_reason,
        "questions_total": len(questions), "answered": len(done), "calls_made_this_run": calls_made,
        "model_id": model_id, "config_id": cfg["config_id"], "config_sha256": config_sha, "questions_sha256": questions_sha,
        "transport_style": transport.style, "frozen": frozen,
        "ledger": ledger.data, "provenance_chain_ok": verify_chain(prov_path)[0] if prov_path.exists() else True,
        "adapter_preflight": None,
        "execution_authority": False, "promotion_authority": False,
        "capability_credit_delta": 0, "family_credit_delta": 0, "incremental_spend_usd": 0,
        "note": "PROVISIONAL tooling output; zero progress credit; scoring happens elsewhere",
    }
    if status == "COMPLETE":
        summary["adapter_preflight"] = _adapter_preflight(resp_path, questions, out_dir, model_id="brain")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _adapter_preflight(resp_path: Path, questions: Sequence[Mapping[str, Any]], out_dir: Path, model_id: str) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        from canonical.runtime.livebench_if_response_adapter import adapt_responses, validate_against_questions
    except Exception as exc:  # adapter not importable outside the repo checkout
        return {"status": "SKIPPED_ADAPTER_NOT_IMPORTABLE", "detail": type(exc).__name__}
    records = [json.loads(line) for line in resp_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    answers = adapt_responses(records, model_id=model_id)
    verdict = validate_against_questions(answers, [{"question_id": q["question_id"]} for q in questions], model_id=model_id)
    if verdict.get("status") == "PASS":
        (out_dir / "model_answers.json").write_text(json.dumps(answers, ensure_ascii=False) + "\n", encoding="utf-8")
    return verdict


# --------------------------------------------------------------------------- CLI
def build_transport(args: argparse.Namespace) -> Transport:
    if args.api_style == "plain":
        return PlainTransport(args.base_url)
    key = os.environ.get(args.api_key_env, "")
    if not key:
        raise Blocked(f"API_KEY_ENV_VAR_EMPTY:{args.api_key_env}")
    if args.api_style == "cf-run":
        acct = os.environ.get(args.account_id_env, "")
        if not acct:
            raise Blocked(f"ACCOUNT_ID_ENV_VAR_EMPTY:{args.account_id_env}")
        return CfRunTransport(acct, key, args.base_url or "https://api.cloudflare.com/client/v4")
    return OpenAITransport(args.base_url, key)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-style", choices=("openai", "cf-run", "plain"), required=True)
    ap.add_argument("--base-url", default="")
    ap.add_argument("--api-key-env", default="BRAIN_GEN_API_KEY")
    ap.add_argument("--account-id-env", default="CLOUDFLARE_ACCOUNT_ID")
    ap.add_argument("--max-total-tokens", type=int, default=None)
    ap.add_argument("--max-neurons-per-utc-day", type=float, default=None)
    ap.add_argument("--prices", type=Path, default=None)
    ap.add_argument("--frozen-release", default=None, help="comma-separated exact release dates treated as frozen")
    ap.add_argument("--frozen-release-min", default=None, help="releases on or after this date are frozen")
    ap.add_argument("--assert-no-frozen-questions", action="store_true", help="explicitly assert the file holds only non-frozen questions")
    ap.add_argument("--authorization", type=Path, default=None)
    ap.add_argument("--id-field", default="question_id")
    ap.add_argument("--prompt-field", default="prompt")
    ap.add_argument("--release-field", default="livebench_release_date")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args(argv)
    try:
        prices = json.loads(args.prices.read_text(encoding="utf-8")) if args.prices else None
        if isinstance(prices, Mapping) and "models" in prices:
            prices = prices["models"]
        summary = run(
            questions_path=args.questions, config_path=args.config, out_dir=args.out, model_id=args.model,
            transport=build_transport(args), max_total_tokens=args.max_total_tokens,
            max_neurons_per_day=args.max_neurons_per_utc_day, prices=prices, frozen_release=args.frozen_release,
            frozen_release_min=args.frozen_release_min, assert_no_frozen_questions=args.assert_no_frozen_questions,
            authorization_path=args.authorization, id_field=args.id_field, prompt_field=args.prompt_field,
            release_field=args.release_field, max_attempts=args.max_attempts, timeout=args.timeout)
    except Blocked as exc:
        print(f"BLOCKED {exc}", file=sys.stderr)
        return exc.code
    print(json.dumps({k: summary[k] for k in ("status", "stop_reason", "questions_total", "answered", "calls_made_this_run")}))
    return {"COMPLETE": 0, "STOPPED_AT_BUDGET_CAP": 4, "STOPPED_TRANSPORT_FAILURE": 5}[summary["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
