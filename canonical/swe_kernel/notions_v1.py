"""Tentative questions about source code, with explicit provenance and feedback.

A disagreement is an observation, not a specification.  In particular, similar
names do not establish that two functions should agree, and a failed equality does
not say which function is wrong.  This module proposes questions from source
structure; it does not give those questions authority to change the workspace.

The static numeric model is deliberately limited and never executes the source.
A reviewer may confirm or reject a question, identify a trusted reference, and
supply examples attributed to an external basis. Such feedback is scoped to the
exact source hash and can rank questions and support future structural proposals;
neither mechanism authorizes a new test or repair. A reference and its evidence
are caller-supplied claims, not authenticated independent verification.
"""
from __future__ import annotations

import contextlib
import functools
import hashlib
import json
import math
import os
import pathlib
import re
import tempfile
from typing import Any, Callable, Iterable, Mapping

from canonical.runtime.memory_policy_v1 import can_read_memory, can_write_memory
from canonical.swe_kernel.expression_hypotheses_v1 import (
    evaluate, function_models, observed_binary_operators, same_number, supported_binary_operator_names,
)

SCHEMA = "BRAIN_NOTIONS_V1"
MAX_FINDINGS = 512
MAX_EXPERIENCES = 256


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


def _serialized_update(method):
    """Serialize local read-modify-replace updates across processes.

    The lock is advisory and only coordinates writers that use this store. It
    does not authenticate data or guarantee correctness on every filesystem.
    """
    @functools.wraps(method)
    def guarded(self, *args, **kwargs):
        if not can_write_memory() or self.path is None:
            return method(self, *args, **kwargs)
        import fcntl
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_name("." + self.path.name + ".lock")
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                return method(self, *args, **kwargs)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return guarded


class NotionStore:
    """Persists questions and caller-supplied reviews, without self-authorization."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        self.seen: dict[str, dict[str, float]] = {}
        self.findings: dict[str, dict[str, Any]] = {}
        self.reviews: dict[str, dict[str, Any]] = {}
        self.examples: dict[str, list[dict[str, Any]]] = {}
        self.plans: dict[str, dict[str, Any]] = {}
        self.experiences: dict[str, dict[str, Any]] = {}
        self.authored_tests: dict[str, dict[str, Any]] = {}
        self.load()

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "seen": self.seen, "findings": self.findings,
                "reviews": self.reviews, "examples": self.examples, "plans": self.plans,
                "experiences": self.experiences, "authored_tests": self.authored_tests}

    def load(self) -> None:
        if not can_read_memory() or not self.path:
            return
        names = ("seen", "findings", "reviews", "examples", "plans", "experiences", "authored_tests")
        # Missing or corrupt files must not leave old in-process approvals live.
        for name in names:
            setattr(self, name, {})
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema") != SCHEMA:
                raise ValueError("notion memory schema mismatch")
            snapshot: dict[str, dict[str, Any]] = {}
            for name in names:
                value = data.get(name, {})  # older stores have no experiences
                if not isinstance(value, dict):
                    raise ValueError(f"notion memory field is invalid: {name}")
                if name == "examples":
                    if not all(isinstance(k, str) and isinstance(v, list) and
                               all(isinstance(row, dict) for row in v) for k, v in value.items()):
                        raise ValueError("notion examples are invalid")
                elif not all(isinstance(k, str) and isinstance(v, dict) for k, v in value.items()):
                    raise ValueError(f"notion memory entries are invalid: {name}")
                snapshot[name] = value
            for name, value in snapshot.items():
                setattr(self, name, value)
        except (ValueError, TypeError, UnicodeError) as exc:
            raise ValueError("notion memory is corrupt or incompatible") from exc

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

    @_serialized_update
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

    @_serialized_update
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

    @_serialized_update
    def record_plan(self, finding_id: str, plan: Mapping[str, Any], *,
                    expected_feedback_hash: str | None = None) -> bool:
        if not can_read_memory():
            return False
        self.load()
        if finding_id not in self.findings:
            return False
        if expected_feedback_hash is not None:
            current = self._feedback_hash(self.reviews.get(finding_id) or {}, self.examples.get(finding_id) or [])
            if current != expected_feedback_hash:
                return False  # the review/examples changed while planning
        value = dict(plan)
        if not can_write_memory():
            return self.plans.get(finding_id) == value
        if self.plans.get(finding_id) != value:
            self.plans[finding_id] = value
            self.save()
        return True

    @_serialized_update
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

    @staticmethod
    def _feedback_hash(review: Mapping[str, Any], examples: list[dict[str, Any]]) -> str:
        payload = json.dumps({"review": review, "examples": examples}, sort_keys=True,
                             separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _feedback_binding_valid(self, binding: Mapping[str, Any]) -> bool:
        """Whether this snapshot still contains the reviewed feedback in a marker."""
        fid = binding.get("finding_id")
        if not isinstance(fid, str):
            return False
        finding = self.findings.get(fid) or {}
        review = self.reviews.get(fid) or {}
        examples = self.examples.get(fid) or []
        plan = self.plans.get(fid) or {}
        target, reference = binding.get("target"), binding.get("reference")
        if not isinstance(target, str) or not isinstance(reference, str):
            return False
        if (not finding.get("fired") or finding.get("declined")
                or binding.get("module") != finding.get("module")
                or binding.get("source_sha256") != finding.get("source_sha256")
                or {target, reference} != {finding.get("left"), finding.get("right")}
                or review.get("decision") != "confirm" or review.get("trusted_function") != reference
                or len(examples) < 2 or plan.get("status") != "bounded_agreement"
                or plan.get("truncated") or plan.get("external_examples") != len(examples)):
            return False
        return binding.get("feedback_sha256") == self._feedback_hash(review, examples)

    @contextlib.contextmanager
    def hold_reviewed_feedback(self, binding: Mapping[str, Any]):
        """Hold a cooperative read lock while checking and using reviewed feedback.

        A concurrent store-method retraction waits until the current operation
        ends. This is local advisory synchronization, not authentication or a
        hostile-writer guarantee.
        """
        if not can_read_memory() or self.path is None:
            yield False
            return
        import fcntl
        lock_path = self.path.with_name("." + self.path.name + ".lock")
        try:
            # READ_ONLY may use an existing lock, but must not create one.
            mode = "a+b" if can_write_memory() else "rb"
            handle = lock_path.open(mode)
        except OSError:
            yield False
            return
        with handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
            try:
                try:
                    self.load()
                    valid = self._feedback_binding_valid(binding)
                except (OSError, ValueError, TypeError):
                    valid = False
                yield valid
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def render_reviewed_test(self, binding: Mapping[str, Any]) -> str:
        """Reconstruct the exact test from the currently locked feedback snapshot."""
        if not self._feedback_binding_valid(binding):
            raise ValueError("stale reviewed feedback")
        fid = str(binding["finding_id"])
        finding = self.findings[fid]
        examples = self.examples[fid]
        module = pathlib.PurePosixPath(str(binding["module"]))
        parts = module.with_suffix("").parts
        if module.suffix != ".py" or not parts or not all(part.isidentifier() for part in parts):
            raise ValueError("invalid reviewed module")
        target, reference = str(binding["target"]), str(binding["reference"])
        if not target.isidentifier() or not reference.isidentifier():
            raise ValueError("invalid reviewed function")
        arity = finding.get("arity")
        if type(arity) is not int or not 2 <= arity <= 4:
            raise ValueError("invalid reviewed arity")
        target_arity = arity if target == finding.get("right") else 1
        reference_arity = arity if reference == finding.get("right") else 1
        checks: list[tuple[list[Any], Any, list[Any] | None]] = []
        for observation in finding.get("observations") or []:
            x = observation["input"]
            expected = observation["left"] if reference == observation.get("left_name") else observation["right"]
            checks.append(([x] * target_arity, expected, [x] * reference_arity))
        for example in examples:
            checks.append((list(example["args"]), example["expected"], None))
        if not checks:
            raise ValueError("review has no observations")
        lines: list[str] = []
        for i, (args, expected, anchor_args) in enumerate(checks):
            call = f"{target}({', '.join(repr(x) for x in args)})"
            lines.extend([f"def test_notion_{fid[:12]}_{i}():", f"    assert {call} == {expected!r}"])
            if anchor_args is not None:
                anchor = f"{reference}({', '.join(repr(x) for x in anchor_args)})"
                lines.append(f"    assert {anchor} == {expected!r}")
            lines.append("")
        return ("# brain-notion-v1 " + json.dumps(dict(binding), sort_keys=True) + "\n"
                "# Based on explicitly supplied review and examples; not a proof.\n"
                f"from {'.'.join(parts)} import {', '.join(sorted((target, reference)))}\n\n"
                + "\n".join(lines))

    @staticmethod
    def _authored_test_key(workspace_root: pathlib.Path, rel_test: str) -> str:
        root = pathlib.Path(workspace_root).resolve()
        rel = pathlib.PurePosixPath(rel_test)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError("invalid authored test path")
        return hashlib.sha256(str(root).encode("utf-8")).hexdigest() + ":" + rel.as_posix()

    def authored_test_binding(self, workspace_root: pathlib.Path, rel_test: str) -> dict[str, Any] | None:
        if not can_read_memory():
            return None
        self.load()
        key = self._authored_test_key(workspace_root, rel_test)
        entry = self.authored_tests.get(key)
        if entry is None:
            return None
        # An existing but malformed origin is not the same as an unregistered
        # user test. Refuse publication rather than silently losing provenance.
        binding = entry.get("binding")
        required = ("module", "source_sha256", "target", "reference", "finding_id", "feedback_sha256")
        if (not isinstance(binding, dict)
                or not all(isinstance(binding.get(k), str) and binding[k] for k in required)
                or not isinstance(entry.get("test_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", entry["test_sha256"]) is None):
            raise ValueError("authored test origin is corrupt")
        return dict(binding)

    @_serialized_update
    def author_reviewed_test(self, binding: Mapping[str, Any], workspace_root: pathlib.Path,
                             test_file: pathlib.Path) -> bool:
        """Record origin before creating the reviewed test under one local lock.

        Origin stays recorded if creation fails, so an interrupted write fails
        closed rather than silently turning a generated test into a user test.
        """
        if not can_write_memory():
            return False
        self.load()
        if not self._feedback_binding_valid(binding):
            return False
        root = pathlib.Path(workspace_root).resolve()
        destination = pathlib.Path(test_file)
        if not destination.is_absolute():
            destination = root / destination
        try:
            rel_test = destination.relative_to(root).as_posix()
            module = (root / str(binding["module"])).resolve()
            if (not destination.resolve().is_relative_to(root) or destination.parent.resolve() != destination.parent
                    or destination.is_symlink() or not module.is_relative_to(root) or not module.is_file()
                    or destination.exists()
                    or hashlib.sha256(module.read_bytes()).hexdigest() != binding.get("source_sha256")):
                return False
            text = self.render_reviewed_test(binding)
            key = self._authored_test_key(root, rel_test)
        except (OSError, ValueError, TypeError, KeyError):
            return False
        if key not in self.authored_tests and len(self.authored_tests) >= MAX_FINDINGS:
            return False
        sidecar = destination.with_name("." + destination.name + ".brain-origin")
        if sidecar.exists() or sidecar.is_symlink():
            return False
        self.authored_tests[key] = {"binding": dict(binding),
                                    "test_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
        self.save()
        destination.parent.mkdir(parents=True, exist_ok=True)
        # This workspace integrity marker carries no learned semantic content.
        # It remains visible when learned-memory reads are OFF, so removing the
        # test header cannot silently reclassify the test as user-authored.
        with sidecar.open("x", encoding="utf-8") as stream:
            stream.write("brain-generated-test-v1\n")
            stream.flush()
            os.fsync(stream.fileno())
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        return True

    @_serialized_update
    def record_checked_repair(self, binding: Mapping[str, Any], candidate_source: str) -> dict[str, Any]:
        """Record syntax from a local reviewed repair, for proposals only.

        The caller must call this *after* the scoped candidate was published and
        checked; these checks are repeated here against stored attribution and
        every example. The evidence is unauthenticated and is not verification of
        intent. No future question is approved by remembering an operator.
        """
        if not can_write_memory():
            return {"status": "memory_policy_blocks_learning", "operators": []}
        self.load()
        fid = binding.get("finding_id")
        finding = self.findings.get(fid) if isinstance(fid, str) else None
        review = self.reviews.get(fid) if isinstance(fid, str) else None
        examples = self.examples.get(fid, []) if isinstance(fid, str) else []
        plan = self.plans.get(fid, {}) if isinstance(fid, str) else {}
        if not finding or not review or not isinstance(candidate_source, str):
            return {"status": "missing_attributed_feedback", "operators": []}
        target, reference = binding.get("target"), binding.get("reference")
        if (not isinstance(target, str) or not isinstance(reference, str)
                or review.get("decision") != "confirm" or review.get("trusted_function") != reference
                or {target, reference} != {finding.get("left"), finding.get("right")}
                or binding.get("source_sha256") != finding.get("source_sha256")
                or binding.get("module") != finding.get("module")
                or plan.get("status") != "bounded_agreement" or plan.get("truncated")
                or len(examples) < 2
                or binding.get("feedback_sha256") != self._feedback_hash(review, examples)):
            return {"status": "feedback_scope_mismatch", "operators": []}
        models = function_models(candidate_source)
        model, ref = models.get(target), models.get(reference)
        if not model or not ref:
            return {"status": "unsupported_candidate", "operators": []}
        seen_args: set[tuple[Any, ...]] = set()
        try:
            for example in examples:
                args = tuple(example.get("args", []))
                if args in seen_args or len(args) != len(model.params):
                    return {"status": "feedback_mismatch", "operators": []}
                seen_args.add(args)
                valid, value = evaluate(model, args)
                if not valid or not same_number(value, example.get("expected")):
                    return {"status": "feedback_mismatch", "operators": []}
            for observation in finding.get("observations", []):
                x = observation.get("input")
                expected = observation.get("left") if reference == observation.get("left_name") else observation.get("right")
                target_result = evaluate(model, (x,) * len(model.params))
                ref_result = evaluate(ref, (x,) * len(ref.params))
                if not (target_result[0] and ref_result[0] and same_number(target_result[1], expected)
                        and same_number(ref_result[1], expected)):
                    return {"status": "feedback_mismatch", "operators": []}
        except (TypeError, ValueError):
            return {"status": "feedback_mismatch", "operators": []}
        operators = observed_binary_operators(model.expression)
        if not operators:
            return {"status": "no_observed_operators", "operators": []}
        if fid not in self.experiences and len(self.experiences) >= MAX_EXPERIENCES:
            return {"status": "experience_capacity_reached", "operators": []}
        self.experiences[fid] = {
            "finding_id": fid, "module": finding["module"], "source_sha256": finding["source_sha256"],
            "candidate_sha256": hashlib.sha256(candidate_source.encode("utf-8")).hexdigest(),
            "target": target, "reference": reference, "operators": operators,
            "feedback_sha256": self._feedback_hash(review, examples),
            "observation": "locally_checked_reviewed_repair_not_independent_verification",
        }
        self.save()
        return {"status": "recorded_for_proposals", "operators": operators, "finding_id": fid}

    def learned_operators(self) -> list[str]:
        """Current evidence-supported primitives; retracted feedback contributes none."""
        if not can_read_memory():
            return []
        self.load()  # observe cross-process revocations rather than cached approval
        out: set[str] = set()
        for fid, experience in self.experiences.items():
            finding = self.findings.get(fid) or {}
            review = self.reviews.get(fid) or {}
            examples = self.examples.get(fid) or []
            if (review.get("decision") != "confirm" or len(examples) < 2
                    or review.get("trusted_function") != experience.get("reference")
                    or experience.get("source_sha256") != finding.get("source_sha256")):
                continue
            try:
                if self._feedback_hash(review, examples) != experience.get("feedback_sha256"):
                    continue
            except (TypeError, ValueError):
                continue
            ops = experience.get("operators")
            if isinstance(ops, list):
                out.update(op for op in ops if isinstance(op, str) and op in supported_binary_operator_names())
        return sorted(out)

    def score(self, finding: Mapping[str, Any]) -> float:
        """A learned review-priority score, not a probability or a permission.

        Each distinct reviewed question contributes once.  A feature's signed
        frequency is learned from feedback, not authored as an error-class table.
        Leave the current question out so its own label cannot score itself.
        """
        if not can_read_memory():
            return 0.0
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
        if not can_read_memory():
            return {"schema": SCHEMA, "tracked": 0, "reviewed": 0, "pending_examples": 0,
                    "learned_operators": [], "experiences": 0, "authored_tests": 0, "persisted_to": None}
        operators = self.learned_operators()  # reloads the same snapshot used by the counts
        return {"schema": SCHEMA, "tracked": len(self.findings), "reviewed": len(self.reviews),
                "pending_examples": sum(bool(p.get("next_query")) for p in self.plans.values()),
                "learned_operators": operators,
                "experiences": len(self.experiences), "authored_tests": len(self.authored_tests),
                "persisted_to": str(self.path) if self.path else None}


def live_notions(path: str | pathlib.Path | None = None) -> NotionStore:
    """Load current feedback; do not keep a stale process-wide cache after review."""
    return NotionStore(path if can_read_memory() else None)
