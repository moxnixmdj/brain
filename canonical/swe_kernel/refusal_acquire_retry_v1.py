"""Wave 41 — a refusal names the term to acquire: `REFUSAL_ACQUIRE_RETRY_V1`.

What was measured, and what was missing
--------------------------------------
Wave 40's bench scored the creature on unseen instances and, in
`CROSS_LANGUAGE_RULE_TRANSFER`, produced a number nobody had: the Meaning-IR ratchet
either applies a learned rule **verbatim, as a token pattern inside its original
context**, or it produces nothing. `x <= hi -> x < hi` crosses from Python to Go only
because the Go line happens to contain `return <hole> <= <hole>`; change the identifier
names, drop the `return`, or write the comparison with its operands the other way round
and the bridge declines — even though the *rule* is one operator swap and the target line
still contains the comparison it is about.

That is the shape of the defect the roadmap calls **abstain -> acquire -> retry**: the gate
abstains and stops. The refusal is not silent — `REFUSED__CROSS_LANGUAGE_TRANSFER_NOT_PRODUCED`
names exactly what is missing (a context-free application procedure for the rule) — but
nothing was done with the name.

What this module does
---------------------
1. **Reads the refusal as a specification.** `OperatorRewrite.from_tokens` derives the
   *meaning* of a crystallised rule: the single operator token that changed, with every
   other non-hole token required to be identical. A rule whose change is anything else is
   refused by name rather than approximated.
2. **Acquires the missing procedure by trying them, cheapest first.** `apply_direct` rewrites
   occurrences of the old operator; `apply_inverted` also handles the same predicate written
   with its operands exchanged (`bound >= x` for `x <= bound`). Each candidate is admitted
   only by the caller's verifier **and** a syntax check — a candidate that cannot be verified
   is not a candidate.
3. **Retries and admits.** When a procedure verifies, the pair
   `(target_language, before_op, after_op)` is admitted to a store, so the *next* refusal of
   the same kind starts with that procedure instead of rediscovering it. `search_steps`
   counts what it actually cost; a reused acquisition costs one step, not two.
4. **Never claims more than it did.** The returned verdict carries `refusals` (what was
   named), `acquisition` (what was tried, how many steps, whether it was reused), `retry`
   (the verifier's word, not ours) and `model_calls: 0`. If nothing verifies, `pass` is
   False and the status says so.

Honest limits
-------------
The procedures here cover comparison operators in expressions. Everything else — an
acquired helper, a renamed symbol, a different statement shape at the level of the edit —
still declines, and declines by name. The store is in-memory and per-process, so "reuse" is
measured inside one run, not across restarts. And the verifier is whatever the caller
supplies: this module can be *wrong* only by admitting a candidate the caller's verifier
accepted.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_REFUSAL_ACQUIRE_RETRY_V1"

#: Operators whose rewrite is a change of comparison, in the languages this bridge carries.
COMPARISON_OPERATORS: tuple[str, ...] = ("<=", ">=", "==", "!=", "<", ">")

#: What each comparison means when the operands are exchanged. `x < y` is `y > x`.
INVERTED: dict[str, str] = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!="}

#: Two-character operators must be matched before their one-character prefixes.
_OPERATOR_RE = re.compile(r"(<=|>=|==|!=|<<|>>|<|>)")

#: A comparison with *something* on both sides. The left character must be part of an
#: operand, which is what keeps `->`, `=>`, `<<` and `>>` out of the rewrite.
_COMPARISON_RE = re.compile(r"(?<=[\w\)\]])(\s*)(<=|>=|==|!=|<|>)(\s*)(?=[\w\(\[])")


@dataclass(frozen=True)
class Refusal:
    """A refusal read as a specification: what was attempted, and what it asks for."""

    code: str
    attempted: str
    asked_for: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "attempted": self.attempted, "asked_for": list(self.asked_for)}


@dataclass(frozen=True)
class OperatorRewrite:
    """The meaning of a lexical rule: one operator token swapped, nothing else changed."""

    before: str
    after: str

    @classmethod
    def from_tokens(
        cls,
        pattern_tokens: Sequence[Sequence[str]],
        replacement_tokens: Sequence[Sequence[str]],
    ) -> "OperatorRewrite | None":
        """Derive the operand rewrite from a crystallised rule's token pair.

        Returns `None` unless exactly one `op` token changed and every other non-hole token is
        identical — a rule that also moves an identifier, a keyword or a literal is a different
        edit and must not be reconstructed from an operator pair.
        """
        pattern = [(str(t[0]), str(t[1])) for t in pattern_tokens if len(tuple(t)) >= 2]
        replacement = [(str(t[0]), str(t[1])) for t in replacement_tokens if len(tuple(t)) >= 2]
        # Whitespace is layout; everything else — including the hole identities — is the edit's
        # meaning. A rule that also renumbers its holes is not one operator swap.
        shape_p = [(k, v) for k, v in pattern if k != "ws"]
        shape_r = [(k, v) for k, v in replacement if k != "ws"]
        if len(shape_p) != len(shape_r) or not shape_p:
            return None
        changed = [(a, b) for a, b in zip(shape_p, shape_r) if a != b]
        if len(changed) != 1:
            return None
        (kind_a, before), (kind_b, after) = changed[0]
        if kind_a != "op" or kind_b != "op":
            return None
        if before not in COMPARISON_OPERATORS or after not in COMPARISON_OPERATORS:
            return None
        return cls(before=before, after=after)

    @property
    def key(self) -> tuple[str, str, str]:
        return ("OPERATOR", self.before, self.after)


@dataclass
class AcquisitionStore:
    """What a refusal bought, kept so the next refusal of the same kind costs less."""

    admitted: dict[tuple[str, str, str, str], dict[str, Any]] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def _key(self, target_language: str, rewrite: OperatorRewrite) -> tuple[str, str, str, str]:
        return (str(target_language).lower(), *rewrite.key)

    def lookup(self, target_language: str, rewrite: OperatorRewrite) -> dict[str, Any] | None:
        found = self.admitted.get(self._key(target_language, rewrite))
        if found is None:
            self.misses += 1
            return None
        self.hits += 1
        return dict(found)

    def admit(self, target_language: str, rewrite: OperatorRewrite, procedure: str) -> None:
        self.admitted[self._key(target_language, rewrite)] = {"procedure": procedure}

    def as_dict(self) -> dict[str, Any]:
        return {"admitted": len(self.admitted), "hits": self.hits, "misses": self.misses}


# --------------------------------------------------------------------------- procedures
def _applications(text: str, operator: str) -> list[tuple[int, int]]:
    """Character spans of `text`'s comparison operators, in order."""
    return [(m.start(2), m.end(2)) for m in _COMPARISON_RE.finditer(text) if m.group(2) == operator]


def apply_direct(text: str, rewrite: OperatorRewrite) -> tuple[str, int]:
    """Rewrite occurrences of the learned operator. Returns (text, edits)."""
    spans = _applications(text, rewrite.before)
    if not spans:
        return text, 0
    out, cursor = [], 0
    for start, end in spans:
        out.append(text[cursor:start])
        out.append(rewrite.after)
        cursor = end
    out.append(text[cursor:])
    return "".join(out), len(spans)


def apply_inverted(text: str, rewrite: OperatorRewrite) -> tuple[str, int]:
    """Rewrite the same predicate written with its operands exchanged (`y >= x` for `x <= y`)."""
    mirror_before = INVERTED.get(rewrite.before)
    mirror_after = INVERTED.get(rewrite.after)
    if mirror_before is None or mirror_after is None or mirror_before == mirror_after:
        return text, 0
    spans = _applications(text, mirror_before)
    if not spans:
        return text, 0
    out, cursor = [], 0
    for start, end in spans:
        out.append(text[cursor:start])
        out.append(mirror_after)
        cursor = end
    out.append(text[cursor:])
    return "".join(out), len(spans)


PROCEDURES: dict[str, Callable[[str, OperatorRewrite], tuple[str, int]]] = {
    "DIRECT_OPERATOR_REWRITE": apply_direct,
    "INVERTED_OPERAND_REWRITE": apply_inverted,
}


# --------------------------------------------------------------------------- the loop
class RefusalAcquisitionLoop:
    """Attempt -> named refusal -> acquire the missing term -> retry -> verify -> admit.

    The loop is only allowed to do one thing on its own authority: try candidate procedures.
    Admission of a candidate is the caller's verifier's decision, and a candidate that changes
    nothing is never admitted (`edits == 0`).
    """

    def __init__(self, store: AcquisitionStore | None = None) -> None:
        self.store = store if store is not None else AcquisitionStore()
        self._lock = threading.Lock()

    # -- generic shape ------------------------------------------------------
    def attempt_verified(
        self,
        *,
        attempt: Callable[[], Mapping[str, Any]],
        verifier: Callable[[Mapping[str, Any]], bool],
    ) -> dict[str, Any]:
        """Run an attempt and let the verifier, not the attempt, decide whether it succeeded."""
        t0 = time.perf_counter()
        try:
            result = dict(attempt())
        except Exception as exc:  # noqa: BLE001 - a refusal is data, not a crash
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "REFUSED__ATTEMPT_RAISED",
                "error": f"{type(exc).__name__}: {exc}",
                "model_calls": 0,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }
        verified = bool(verifier(result))
        return {
            "schema": SCHEMA,
            "pass": verified,
            "status": "PASS__ATTEMPT_VERIFIED" if verified else "REFUSED__ATTEMPT_DID_NOT_VERIFY",
            "verified": verified,
            "attempt": result,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    # -- the concrete acquisition this wave needed --------------------------
    def acquire_cross_language_patch(
        self,
        *,
        rule: Mapping[str, Any],
        source_text: str,
        target_language: str,
        verifier: Callable[[str], bool],
        parse_check: Callable[[str, str], tuple[bool, str]] | None = None,
        procedures: Iterable[str] = ("DIRECT_OPERATOR_REWRITE", "INVERTED_OPERAND_REWRITE"),
    ) -> dict[str, Any]:
        """Turn a bridge refusal into a verified cross-language patch, or say why not."""
        t0 = time.perf_counter()
        refusal = Refusal(
            code="CROSS_LANGUAGE_BRIDGE_PRODUCED_NOTHING",
            attempted="apply the crystallised rule's token pattern inside the target's own context",
            asked_for=("a context-free application procedure for the rule's operator change",),
        )
        rewrite = OperatorRewrite.from_tokens(
            rule.get("pattern_tokens") or (), rule.get("replacement_tokens") or ()
        )
        base: dict[str, Any] = {
            "schema": SCHEMA,
            "pass": False,
            "refusals": [refusal.as_dict()],
            "target_language": str(target_language),
            "model_calls": 0,
        }
        if rewrite is None:
            return {
                **base,
                "status": "REFUSED__RULE_CHANGE_IS_NOT_A_SINGLE_OPERATOR",
                "acquisition": {"kind": "NONE", "reason": "the rule changes more than one operator"},
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }
        if not callable(verifier):
            return {
                **base,
                "status": "REFUSED__ACQUISITION_REQUIRES_A_VERIFIER",
                "acquisition": {"kind": "NONE", "reason": "no verifier supplied"},
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        declared = self.store.lookup(target_language, rewrite)
        order = list(procedures)
        reused = declared is not None
        if declared is not None and declared.get("procedure") in order:
            order = [declared["procedure"]] + [p for p in order if p != declared["procedure"]]

        tried: list[dict[str, Any]] = []
        for steps, name in enumerate(order, start=1):
            procedure = PROCEDURES.get(name)
            if procedure is None:
                continue
            candidate, edits = procedure(source_text, rewrite)
            if edits == 0 or candidate == source_text:
                tried.append({"procedure": name, "edits": 0, "admitted": False, "why": "CHANGED_NOTHING"})
                continue
            if parse_check is not None:
                ok, why = parse_check(target_language, candidate)
                if not ok:
                    tried.append({"procedure": name, "edits": edits, "admitted": False, "why": why})
                    continue
            try:
                verified = bool(verifier(candidate))
            except Exception as exc:  # noqa: BLE001 - a raising verifier is a refusal
                tried.append(
                    {"procedure": name, "edits": edits, "admitted": False,
                     "why": f"VERIFIER_RAISED:{type(exc).__name__}"}
                )
                continue
            if not verified:
                tried.append({"procedure": name, "edits": edits, "admitted": False, "why": "VERIFIER_REJECTED"})
                continue
            with self._lock:
                self.store.admit(target_language, rewrite, name)
            return {
                **base,
                "pass": True,
                "status": "PASS__ACQUIRED_AFTER_REFUSAL",
                "patched_source": candidate,
                "acquisition": {
                    "kind": "CONTEXT_FREE_OPERATOR_REWRITE",
                    "before": rewrite.before,
                    "after": rewrite.after,
                    "procedure": name,
                    "edits": edits,
                    "search_steps": steps,
                    "reused": reused,
                    "procedures_tried": tried,
                },
                "retry": {"verified": True, "verified_by": "caller_verifier"},
                "store": self.store.as_dict(),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        return {
            **base,
            "status": "REFUSED__ACQUISITION_FAILED",
            "acquisition": {
                "kind": "CONTEXT_FREE_OPERATOR_REWRITE",
                "before": rewrite.before,
                "after": rewrite.after,
                "procedure": None,
                "edits": 0,
                "search_steps": len(order),
                "reused": reused,
                "procedures_tried": tried,
            },
            "retry": {"verified": False, "verified_by": "caller_verifier"},
            "store": self.store.as_dict(),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    # -- what the loop bought, stated as a measurement ----------------------
    def summary(self) -> dict[str, Any]:
        return {"schema": SCHEMA, **self.store.as_dict()}


_SHARED: RefusalAcquisitionLoop | None = None


def shared_refusal_loop() -> RefusalAcquisitionLoop:
    """Process-wide loop, so a declared acquisition is remembered by the next caller."""
    global _SHARED
    if _SHARED is None:
        _SHARED = RefusalAcquisitionLoop()
    return _SHARED


def acquire_and_retry(**kwargs: Any) -> dict[str, Any]:
    """Federation/UnifiedModel entry point: acquire a verified patch after a named refusal."""
    return shared_refusal_loop().acquire_cross_language_patch(**kwargs)
