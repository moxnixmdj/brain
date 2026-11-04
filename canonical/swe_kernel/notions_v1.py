"""Tentative questions about source code, with explicit provenance and feedback.

A disagreement is an observation, not a specification.  In particular, similar
names do not establish that two functions should agree, and a failed equality does
not say which function is wrong.  This module proposes questions from source
structure; it does not give those questions authority to change the workspace.

The static numeric model is deliberately limited and never executes the source.
A reviewer may confirm or reject a question, identify a trusted reference, and
supply independent examples.  Such feedback is scoped to the exact source hash
and is used to rank future questions; the ranking itself never authorizes a test
or repair.  A feedback reference is a caller-supplied claim, not authenticated
proof of independent verification.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import re
import tempfile
from typing import Any, Callable, Iterable, Mapping

from canonical.runtime.memory_policy_v1 import can_read_memory, can_write_memory
from canonical.swe_kernel.expression_hypotheses_v1 import evaluate, function_models, same_number

SCHEMA = "BRAIN_NOTIONS_V1"
MAX_FINDINGS = 512


def _identifier(kind: str, module: str, digest: str, left: str, right: str, arity: int) -> str:
    payload = json.dumps([kind, module, digest, left, right, arity], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Notion:
    """A refutable question; ``fired`` means disagreement, not an identified bug."""

    __slots__ = ("kind", "subject", "claim", "check", "fired", "declined", "value", "arity",
                 "module", "source_sha256", "left", "right", "id")

    def __init__(self, kind: str, subject: str, claim: str, check: Callable[[], Any],
                 value: float = 1.0, arity: int = 0, *, module: str = "",
                 source_sha256: str = "", left: str = "", right: str = "") -> None:
        self.kind, self.subject, self.claim, self.check = kind, subject, claim, check
        self.fired: bool | None = None
        self.declined = False
        self.value, self.arity = value, arity
        self.module, self.source_sha256 = module, source_sha256
        self.left, self.right = left, right
        self.id = _identifier(kind, module, source_sha256, left, right, arity)

    def evaluate(self) -> dict[str, Any]:
        base = {"id": self.id, "kind": self.kind, "subject": self.subject, "claim": self.claim,
                "module": self.module, "source_sha256": self.source_sha256,
                "left": self.left, "right": self.right, "arity": self.arity,
                "provenance": "bounded_static_model", "authority": "hypothesis"}
        try:
            result = self.check()
            if isinstance(result, Mapping):
                held = bool(result.get("held"))
                declined = bool(result.get("declined"))
                detail = str(result.get("detail", ""))
                observations = list(result.get("observations") or [])
            elif isinstance(result, (tuple, list)) and len(result) >= 2:
                held, detail = bool(result[0]), str(result[1])
                declined = bool(result[2]) if len(result) > 2 else False
                observations = []
            else:
                raise ValueError("invalid check result")
        except Exception as exc:  # a failed model is not a violated expectation
            self.fired, self.declined = False, True
            return {**base, "fired": False, "declined": True,
                    "detail": f"declined: {type(exc).__name__}", "observations": []}
        self.fired, self.declined = not held and not declined, declined
        return {**base, "fired": self.fired, "declined": declined,
                "detail": detail, "observations": observations}

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "subject": self.subject, "claim": self.claim}


def notions_for_source(source: str, module_name: str = "mod") -> list[Notion]:
    """Suggest equal-input relations without assuming their semantic validity.

    Only single-return numeric functions in a small statically interpretable subset
    are considered.  The four probe inputs are exploration choices, not source
    specifications.  Every eligible narrow/wide pair is considered regardless of
    its name; names may later be learned as *ranking features*, never as proof.
    """
    models = function_models(source)
    if not models:
        return []
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    out: list[Notion] = []
    for left in models.values():
        if len(left.params) != 1:
            continue
        for right in models.values():
            if len(right.params) <= 1:
                continue
            if len(out) >= 128:
                return out

            def check(left=left, right=right) -> dict[str, Any]:
                observations: list[dict[str, Any]] = []
                for value in (2, 3, 4, 5):
                    left_ok, a = evaluate(left, (value,))
                    right_ok, b = evaluate(right, (value,) * len(right.params))
                    if left_ok and right_ok:
                        observations.append({"input": value, "left": a, "right": b,
                                             "left_name": left.name, "right_name": right.name})
                if len(observations) < 2:
                    return {"declined": True, "detail": "fewer than two safely modelled inputs",
                            "observations": observations}
                disagreements = [o for o in observations if not same_number(o["left"], o["right"])]
                return {"held": not disagreements, "observations": observations,
                        "detail": (f"{len(disagreements)} disagreement(s) among {len(observations)} "
                                   "statically modelled inputs; relation and blame are unconfirmed")}

            out.append(Notion(
                kind="IDENTITY", subject=f"{left.name} vs {right.name}(equal args)",
                claim=f"Could {left.name}(x) equal {right.name}(x, ... , x)?",
                check=check, value=1.0, arity=len(right.params), module=module_name,
                source_sha256=digest, left=left.name, right=right.name,
            ))
    return out


def _features(finding: Mapping[str, Any]) -> set[str]:
    """Generic, data-derived lexical/structural features, not a list of meanings."""
    left = set(re.findall(r"[a-z]+|[0-9]+", str(finding.get("left", "")).lower()))
    right = set(re.findall(r"[a-z]+|[0-9]+", str(finding.get("right", "")).lower()))
    return ({f"left:{x}" for x in left} | {f"right:{x}" for x in right} |
            {f"shared:{x}" for x in left & right} |
            {f"kind:{finding.get('kind')}", f"arity:{finding.get('arity')}"})


class NotionStore:
    """Persists questions and caller-supplied reviews, without self-authorization."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        self.seen: dict[str, dict[str, float]] = {}
        self.findings: dict[str, dict[str, Any]] = {}
        self.reviews: dict[str, dict[str, Any]] = {}
        self.examples: dict[str, list[dict[str, Any]]] = {}
        self.plans: dict[str, dict[str, Any]] = {}
        self.load()

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "seen": self.seen, "findings": self.findings,
                "reviews": self.reviews, "examples": self.examples, "plans": self.plans}

    def load(self) -> None:
        if not can_read_memory() or not self.path or not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema") != SCHEMA:
                return
            for name in ("seen", "findings", "reviews", "examples", "plans"):
                value = data.get(name)
                if not isinstance(value, dict):
                    continue
                if name == "examples":
                    clean = {k: [row for row in v if isinstance(row, dict)]
                             for k, v in value.items() if isinstance(k, str) and isinstance(v, list)}
                else:
                    clean = {k: v for k, v in value.items() if isinstance(k, str) and isinstance(v, dict)}
                setattr(self, name, clean)
        except (ValueError, OSError, TypeError):
            return

    def save(self) -> None:
        if not can_write_memory() or not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp: str | None = None
        try:
            # A unique temporary file prevents concurrent writers from sharing
            # the same scratch path. Explicit write failures must reach callers;
            # otherwise a review could appear saved when it was discarded.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".notions-", delete=False) as handle:
                tmp = handle.name
                json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
            tmp = None
        finally:
            if tmp is not None:
                pathlib.Path(tmp).unlink(missing_ok=True)

    @staticmethod
    def key(n: Notion) -> str:
        return f"{n.kind}::{n.subject}"

    def record(self, results: Iterable[Mapping[str, Any]]) -> None:
        """Remember each exact source/question once; repeated sensing is not new evidence."""
        if not can_write_memory():
            return
        self.load()
        changed = False
        for raw in results:
            r = dict(raw)
            key = str(r.get("id") or "")
            if not key:
                continue
            if key not in self.findings and len(self.findings) >= MAX_FINDINGS:
                continue
            first_observation = key not in self.findings
            if self.findings.get(key) != r:
                self.findings[key] = r
                changed = True
            # Count distinct source/question pairs, not repeated reads. These
            # are diagnostics, not labels or authorization.
            if first_observation:
                skey = f"{r.get('kind')}::{r.get('subject')}"
                slot = self.seen.setdefault(skey, {"evaluated": 0.0, "fired": 0.0, "declined": 0.0})
                slot["evaluated"] += 1
                slot["fired"] += float(bool(r.get("fired")))
                slot["declined"] += float(bool(r.get("declined")))
                changed = True
        if changed:
            self.save()

    def review(self, finding_id: str, *, decision: str, reviewer: str, basis: str,
               trusted_function: str | None = None) -> dict[str, Any]:
        """Record a caller's explicit relation decision, not a self-generated label.

        ``basis`` identifies the outside evidence or human decision. This API does
        not authenticate it. A confirmed relation alone does not identify blame;
        the caller may additionally identify a reference they choose to trust.
        """
        if not can_write_memory():
            raise PermissionError("memory policy forbids feedback")
        self.load()
        finding = self.findings.get(finding_id)
        if not finding or not finding.get("fired") or finding.get("declined"):
            raise ValueError("unknown or non-firing question")
        if (decision not in ("confirm", "reject") or not isinstance(reviewer, str) or not reviewer.strip()
                or not isinstance(basis, str) or not basis.strip()):
            raise ValueError("an explicit decision, reviewer and basis are required")
        if trusted_function is not None and trusted_function not in {finding.get("left"), finding.get("right")}:
            raise ValueError("reference must be one of the two functions")
        if decision == "reject" and trusted_function is not None:
            raise ValueError("a rejected relation cannot have a trusted reference")
        review = {"decision": decision, "reviewer": reviewer[:200], "basis": basis[:500],
                  "trusted_function": trusted_function}
        previous = self.reviews.get(finding_id)
        if previous != review:
            self.reviews[finding_id] = review
            # Old examples and plans cannot be reused after a change in authority.
            self.examples.pop(finding_id, None)
            self.plans.pop(finding_id, None)
            self.save()
        return dict(review)

    def record_plan(self, finding_id: str, plan: Mapping[str, Any]) -> None:
        if not can_write_memory():
            return
        self.load()
        if finding_id not in self.findings:
            return
        value = dict(plan)
        if self.plans.get(finding_id) != value:
            self.plans[finding_id] = value
            self.save()

    def answer(self, finding_id: str, *, args: list[int | float], expected: int | float,
               reviewer: str, basis: str) -> dict[str, Any]:
        """Record an external answer to the currently proposed input, once."""
        if not can_write_memory():
            raise PermissionError("memory policy forbids feedback")
        self.load()
        review = self.reviews.get(finding_id) or {}
        plan = self.plans.get(finding_id) or {}
        query = plan.get("next_query") or {}
        if (review.get("decision") != "confirm" or not review.get("trusted_function")
                or not isinstance(args, list) or query.get("args") != args
                or any(type(a) not in (int, float) or (isinstance(a, float) and not math.isfinite(a)) for a in args)):
            raise ValueError("answer does not match an active, reviewed query")
        if (not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(basis, str)
                or not basis.strip() or type(expected) not in (int, float)):
            raise ValueError("an independent numeric answer and its provenance are required")
        if isinstance(expected, int) and expected.bit_length() > 80:
            raise ValueError("answer exceeds numeric budget")
        if isinstance(expected, float) and (not math.isfinite(expected) or abs(expected) > 1e20):
            raise ValueError("answer exceeds numeric budget")
        prior = self.examples.setdefault(finding_id, [])
        if any(e.get("args") == args for e in prior):
            raise ValueError("query was already answered")
        example = {"args": list(args), "expected": expected, "reviewer": reviewer[:200], "basis": basis[:500]}
        prior.append(example)
        # Require a new plan before accepting another answer; the model must actually update.
        self.plans.pop(finding_id, None)
        self.save()
        return dict(example)

    def score(self, finding: Mapping[str, Any]) -> float:
        """A learned review-priority score, not a probability or a permission.

        Each distinct reviewed question contributes once.  A feature's signed
        frequency is learned from feedback, not authored as an error-class table.
        Leave the current question out so its own label cannot score itself.
        """
        wanted = _features(finding)
        if not wanted:
            return 0.0
        counts: dict[str, list[int]] = {f: [0, 0] for f in wanted}
        current_signature = (finding.get("source_sha256"), finding.get("left"),
                             finding.get("right"), finding.get("arity"))
        grouped: dict[tuple[Any, ...], tuple[Mapping[str, Any], set[str]]] = {}
        for fid, review in self.reviews.items():
            old = self.findings.get(fid)
            if not old or review.get("decision") not in {"confirm", "reject"}:
                continue
            signature = (old.get("source_sha256"), old.get("left"), old.get("right"), old.get("arity"))
            if signature == current_signature:
                continue  # no self-evidence, including copies in a different path
            if signature not in grouped:
                grouped[signature] = (old, set())
            grouped[signature][1].add(str(review["decision"]))
        for old, decisions in grouped.values():
            if len(decisions) != 1:
                continue  # conflicting reviews of identical evidence are not a label
            label = 0 if "confirm" in decisions else 1
            for feature in wanted & _features(old):
                counts[feature][label] += 1
        return round(sum((p - n) / (p + n + 2) for p, n in counts.values()) / len(wanted), 6)

    def is_noise(self, n: Notion, **_: Any) -> bool:
        """Fire frequency cannot establish semantic validity; retained for compatibility."""
        return False

    def informativeness(self, n: Notion) -> float:
        return self.score(n.evaluate())

    def summary(self) -> Mapping[str, Any]:
        return {"schema": SCHEMA, "tracked": len(self.findings), "reviewed": len(self.reviews),
                "pending_examples": sum(bool(p.get("next_query")) for p in self.plans.values()),
                "persisted_to": str(self.path) if self.path else None}


def live_notions(path: str | pathlib.Path | None = None) -> NotionStore:
    """Load current feedback; do not keep a stale process-wide cache after review."""
    return NotionStore(path if can_read_memory() else None)
