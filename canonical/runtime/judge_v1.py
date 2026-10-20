"""A bounded adviser, never an authority.

This is the System One contract -- Choice / Score / Noul against a
/v1/systemone endpoint -- as the Brain already understands it
(cognitive_decision_kernel.py is "Jev-compatible", admits a decision
only above a configured confidence, and ESCALATES otherwise).

Why a classifier here and not somewhere else: it CANNOT GENERATE. It
returns typed probabilities and no prose. That single property is what
makes it admissible under the ownership law, where a text-generating
model would not be. It cannot invent a claim, because it cannot emit
one. It can still be WRONG -- "cannot hallucinate does not mean cannot
be wrong" -- so its verdict is an ADVICE, and code decides.

THE SLOT IT FILLS. Not the mind. A classifier cannot write a program
or decide what to do, so it does not fill proposal packets and it
never will. What it is good at is the thing code is worst at: naming
something it has never seen before. That is precisely where this
system is still brittle -- classify() is a hand-written table of error
strings, which is training data wearing a general name. It handles the
failures someone anticipated and files everything else as
"unclassified". A calibrated classifier can name a failure nobody
anticipated, and say how sure it is.

THE GATE. A verdict is admitted only above a threshold; below it, the
judge ESCALATES and the caller falls back rather than acting on a
guess. Low confidence is not a weak yes. It is a refusal, and it must
be treated as one.

HOSTED OR SELF-HOSTED -- the contract is the same either way, and the
endpoint comes from the environment, never from this file:

    BRAIN_JUDGE_URL   https://api.typesafe.ai/v1/systemone   (hosted)
                      http://127.0.0.1:8919/v1/systemone     (local)

Open-weight compatible servers (jev-style, Vev) speak this same
shape, so running the classifier locally is a configuration change
and not a rewrite. Running it locally matters: a classifier you host
yourself is a component, while one you call is a dependency.

WHEN NOTHING IS CONFIGURED, this says so. It does not approximate a
judgment, and it does not return a confident-looking middle value
that the caller cannot distinguish from a real verdict.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_JUDGE_V1"

ENV_URL = "BRAIN_JUDGE_URL"
ENV_KEY = "BRAIN_JUDGE_KEY"
ENV_MODEL = "BRAIN_JUDGE_MODEL"

# Research-reported behaviour: high confidence acts, medium asks, low
# escalates. Chosen before seeing any verdict, so it is a policy and
# not a fitting exercise.
DEFAULT_THRESHOLD = 0.80
ESCALATE = "ESCALATE"


def configured() -> bool:
    return bool(os.environ.get(ENV_URL, "").strip())


def _post(payload: Mapping[str, Any], timeout: float) -> dict:
    url = os.environ[ENV_URL].strip()
    key = os.environ.get(ENV_KEY, "").strip()
    model = os.environ.get(ENV_MODEL, "").strip() or "jev-latest"
    body = json.dumps({**payload, "model": payload.get("model") or model})
    req = urllib.request.Request(
        url, data=body.encode("utf-8"),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {key}"} if key else {})},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise JudgeUnavailable(f"HTTP {exc.code}") from exc
    except Exception as exc:
        raise JudgeUnavailable(f"{type(exc).__name__}: {exc}") from exc


class JudgeUnavailable(RuntimeError):
    """No classifier reachable. Not the same as a verdict."""


def ask(state: Any, questions: Mapping[str, Any],
        timeout: float = 10.0) -> dict:
    """One call to /v1/systemone. Raises if nothing is reachable."""
    if not configured():
        raise JudgeUnavailable(f"{ENV_URL} is not set")
    return _post({"state": state, "questions": dict(questions)}, timeout)


def noul(state: Any, instruction: str, threshold: float = DEFAULT_THRESHOLD,
         timeout: float = 10.0) -> dict:
    """A bounded yes/no, admitted only above the threshold.

    Returns `admitted` False and verdict ESCALATE both when the
    classifier declines and when it is unreachable, because from the
    caller's side those are the same instruction: do not act on this.
    """
    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must be in (0, 1]")
    try:
        out = ask(state, {"q": {"type": "noul", "instructions": instruction}},
                  timeout)
    except JudgeUnavailable as exc:
        return {"schema": SCHEMA, "admitted": False, "verdict": ESCALATE,
                "probability": None, "threshold": threshold,
                "reason": f"unavailable: {exc}"}
    q = (out.get("questions") or out.get("results") or {}).get("q") or {}
    p = q.get("noul", q.get("probability"))
    if not isinstance(p, (int, float)):
        return {"schema": SCHEMA, "admitted": False, "verdict": ESCALATE,
                "probability": None, "threshold": threshold,
                "reason": "no probability in the response"}
    p = float(p)
    yes = p >= threshold
    no = (1.0 - p) >= threshold
    verdict = "YES" if yes else ("NO" if no else ESCALATE)
    return {"schema": SCHEMA, "admitted": verdict != ESCALATE,
            "verdict": verdict, "probability": p, "threshold": threshold,
            "reason": ("above threshold" if verdict != ESCALATE
                       else "confidence below threshold; not a weak yes")}


def choose(state: Any, instruction: str, options: Mapping[str, str],
           threshold: float = DEFAULT_THRESHOLD,
           timeout: float = 10.0) -> dict:
    """Pick one of a closed set, gated the same way.

    The set is CLOSED deliberately. A classifier asked an open
    question can be confidently wrong; asked to choose among options
    it can still be wrong, but it cannot invent a new category the
    rest of the system has never heard of.
    """
    try:
        out = ask(state, {"q": {"type": "choice",
                                "instructions": instruction,
                                "criteria": dict(options)}}, timeout)
    except JudgeUnavailable as exc:
        return {"schema": SCHEMA, "admitted": False, "choice": None,
                "confidence": None, "threshold": threshold,
                "reason": f"unavailable: {exc}"}
    q = (out.get("questions") or out.get("results") or {}).get("q") or {}
    choice = q.get("choice")
    conf = q.get("confidence", q.get("probability"))
    if choice not in options:
        return {"schema": SCHEMA, "admitted": False, "choice": None,
                "confidence": None, "threshold": threshold,
                "reason": "choice outside the closed set"}
    if not isinstance(conf, (int, float)) or float(conf) < threshold:
        return {"schema": SCHEMA, "admitted": False, "choice": choice,
                "confidence": conf, "threshold": threshold,
                "reason": "confidence below threshold"}
    return {"schema": SCHEMA, "admitted": True, "choice": choice,
            "confidence": float(conf), "threshold": threshold}
