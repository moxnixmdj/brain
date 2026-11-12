#!/usr/bin/env python3
"""A taught edit may not touch a new target until its one open question is settled.

Why this exists
---------------
Measured 2026-11-12 on this tree (`canonical/tools/one_try_state_probe_20261112_v1.py`,
measurement 6): a demonstration `a <= hi` -> `a < hi` taught on `inside` is applied to a
same-shaped target `is_last_index` where `<=` is *semantically required*, silently making it
wrong at the boundary. `edit_by_example_v1` consults shape, names and imports -- but never the
target's meaning. One demonstration is a point, not a quantifier.

`INSTANT_LEARNING_AUDIT_20261112_V1.md` (ranked plan item 2) names the missing edge: connect
`settlement_v1` question selection to rule admission where multiple hypotheses survive.

What this module does
---------------------
Given a demonstration (`before_text` -> `after_text`) and a new target, there are exactly two
hypotheses about the target's correct form:

* `apply_teach` -- the demonstration's transformation transfers to this target;
* `keep_target` -- it does not; the target's current form is already what is wanted.

The module makes both candidate forms runnable, finds the inputs where they *disagree*
(those are the only questions worth asking), and:

1. no disagreement on the probe grid -> the demonstration decides; admit, and say so
   honestly (`ADMIT_GRID_NON_DISCRIMINATING`: the grid is finite, boundaries beyond it are
   not covered by this instrument);
2. disagreement and no oracle -> refuse, fail closed, and record the disagreement points as
   *the questions the creature should ask* (`REFUSE_NO_ORACLE_UNSETTLED`);
3. disagreement and an oracle -> ask the disagreement points through `settlement_v1`
   (version-space bookkeeping, `select_probe` order) under an asymmetric rule:
   **refuse at the first contradiction; admit only when every disagreement point has been
   asked and agreed.** A refusal is settled by one answer; an admission must cover the whole
   disagreement set, because a coarse two-form hypothesis space settles its posterior after a
   single agreeing answer -- measured here on the first draft (2026-11-12): one question at
   `(-1, -1)` "settled" the wrong rule onto `is_last_index`, reproducing in miniature the
   audit's 0/200 one-success result. Refusal typically costs 1-2 questions; admission costs
   one question per boundary the edit could change. Budget exhausted with points unasked ->
   fail closed;
4. target not probeable at all (does not exec, wrong parameter count, every probe raises
   for both candidates) -> refuse, fail closed (`REFUSE_UNPROBEABLE_TARGET`).

The oracle is the minimum question interface: one call per chosen probe. It is whatever can
answer "what *should* this return here" -- a test, a teacher, a spec. This module never
widens its own claim: admission is a statement about this target, this demonstration and the
probe grid used, with `terminal_authority` false throughout.
"""
from __future__ import annotations

import ast
import itertools
import inspect
from typing import Any, Callable, Sequence

from canonical.runtime.settlement_v1 import (
    SETTLED,
    UNDERDETERMINED,
    Hypothesis,
    Settlement,
    VersionSpace,
)
from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe

GRID_VALUES: tuple[int, ...] = (-1, 0, 1, 2, 3)
MAX_PARAMS = 3
DEFAULT_BUDGET = 8

APPLY_KEY = "apply_teach"
KEEP_KEY = "keep_target"

# Actions
ADMIT_SETTLED = "ADMIT_SETTLED"
ADMIT_GRID_NON_DISCRIMINATING = "ADMIT_GRID_NON_DISCRIMINATING"
REFUSED_DEMO = "REFUSED_DEMO"
REFUSED_SHAPE = "REFUSED_SHAPE"
REFUSE_NO_ORACLE_UNSETTLED = "REFUSE_NO_ORACLE_UNSETTLED"
REFUSE_UNPROBEABLE_TARGET = "REFUSE_UNPROBEABLE_TARGET"
REFUSE_UNSETTLED_BY_INSTRUMENT = "REFUSE_UNSETTLED_BY_INSTRUMENT"
REFUSE_ORACLE_SAYS_KEEP = "REFUSE_ORACLE_SAYS_KEEP"

Oracle = Callable[..., Any]

_RAISE = "raise"


def _raise_sentinel(exc: BaseException) -> tuple[str, str]:
    return (_RAISE, type(exc).__name__)


def _candidate_outcome(fn: Callable[..., Any], args: tuple[Any, ...]) -> Any:
    """Run one candidate on one probe; a raise is an honest outcome, not a crash."""
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 - the exception *class* is the outcome
        return _raise_sentinel(exc)


def _oracle_outcome(oracle: Oracle, args: tuple[Any, ...]) -> Any:
    try:
        return oracle(*args)
    except Exception as exc:  # noqa: BLE001
        return _raise_sentinel(exc)


def _first_function(text: str) -> str | None:
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef):
            return node.name
    return None


def _load_function(text: str) -> Callable[..., Any]:
    namespace: dict[str, Any] = {"__name__": "settled_admission_target"}
    exec(compile(text, "<settled-admission-target>", "exec"), namespace)  # noqa: S102
    name = _first_function(text)
    if name is None or name not in namespace:
        raise ValueError("target defines no function")
    return namespace[name]


def _param_count(fn: Callable[..., Any]) -> int:
    return len(inspect.signature(fn).parameters)


def _probe_grid(n: int, grid_values: Sequence[int]) -> list[tuple[Any, ...]]:
    return list(itertools.product(sorted(grid_values), repeat=n))


def _is_raise(outcome: Any) -> bool:
    return isinstance(outcome, tuple) and len(outcome) == 2 and outcome[0] == _RAISE


def _row(
    space: VersionSpace,
    queries_used: int,
    information_bits: float,
    domain: Sequence[tuple[Any, ...]],
    confidence: float,
    status: str,
    *,
    winner_key: str | None = None,
) -> Settlement:
    """Build the honest settlement row for the asymmetry protocol.

    The posterior and the domain disagreement come from the live VersionSpace; the winner is
    named only when the protocol's own rule (contradiction, or full coverage) settled it.
    """
    post = space.posterior()
    winner = None
    if winner_key is not None:
        winner = space._by_key[winner_key]  # noqa: SLF001 - same module family, single ruler
    return Settlement(
        status=status,
        reason="asymmetric protocol: refuse on first contradiction, admit on full coverage",
        winner=winner,
        posterior=post,
        queries_used=queries_used,
        information_bits=round(information_bits, 6),
        domain_disagreement=space.domain_disagreement(domain),
        confidence=post.get(winner_key, 0.0) if winner_key else 0.0,
        threshold=confidence,
        probe_space_size=len(domain),
    )


def _result(
    action: str,
    why: str,
    *,
    rules: Sequence[Any] = (),
    edited_text: str | None = None,
    probes_asked: Sequence[Any] = (),
    disagreement_points: Sequence[Any] = (),
    grid_size: int = 0,
    settlement: Settlement | None = None,
    evidence: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "action": action,
        "why": why,
        "rule_descriptions": [str(rule) for rule in rules],
        "edited_text": edited_text,
        "probes_asked": [list(p) for p in probes_asked],
        "disagreement_points": [list(p) for p in disagreement_points],
        "grid_size": grid_size,
        "settlement": None if settlement is None else settlement.as_row(),
        "evidence": list(evidence),
        "terminal_authority": False,
    }


def settle_taught_edit(
    target_text: str,
    before_text: str,
    after_text: str,
    *,
    oracle: Oracle | None = None,
    budget: int = DEFAULT_BUDGET,
    grid_values: Sequence[int] = GRID_VALUES,
    confidence: float = 0.99,
) -> dict[str, Any]:
    """Admit (or refuse) the demonstration's edit onto `target_text`, settled by questions.

    Returns a JSON-safe dict; `action` is one of the module's action constants and
    `edited_text` is the admitted text (present only when the edit is admitted).
    `edit_by_example_v1.Refused` from the *demonstration* itself is re-raised unchanged:
    a lesson that cannot be learned at all is the caller's error, not an admission decision.
    """
    rules = ebe.learn(before_text, after_text)
    try:
        edited = ebe.repeated(rules, target_text, "the example")
    except ebe.Refused as exc:
        return _result(
            REFUSED_SHAPE,
            "the demonstration's change has no same-shaped place in the target: %s" % exc,
            rules=rules,
        )

    try:
        fn_apply = _load_function(edited)
        fn_keep = _load_function(target_text)
    except Exception as exc:  # noqa: BLE001
        return _result(
            REFUSE_UNPROBEABLE_TARGET,
            "the target or its edited form does not load as a callable: %s" % exc,
            rules=rules,
        )

    n = _param_count(fn_keep)
    if _param_count(fn_apply) != n or n == 0 or n > MAX_PARAMS:
        return _result(
            REFUSE_UNPROBEABLE_TARGET,
            "target takes %d parameters; this instrument probes 1..%d integer parameters"
            % (n, MAX_PARAMS),
            rules=rules,
        )

    grid = _probe_grid(n, grid_values)
    outcomes_apply = [_candidate_outcome(fn_apply, t) for t in grid]
    outcomes_keep = [_candidate_outcome(fn_keep, t) for t in grid]
    disagreement = [t for t, a, k in zip(grid, outcomes_apply, outcomes_keep) if a != k]

    if all(_is_raise(a) for a in outcomes_apply) and all(_is_raise(k) for k in outcomes_keep):
        return _result(
            REFUSE_UNPROBEABLE_TARGET,
            "every probe raises for both candidate forms; the target cannot be probed here",
            rules=rules,
            grid_size=len(grid),
        )

    if not disagreement:
        return _result(
            ADMIT_GRID_NON_DISCRIMINATING,
            "the taught change cannot alter this target's behaviour on any of the %d probed "
            "inputs; the demonstration decides. The grid is finite: behaviour beyond it is "
            "not covered by this instrument." % len(grid),
            rules=rules,
            edited_text=edited,
            grid_size=len(grid),
            evidence=["GRID_NON_DISCRIMINATING"],
        )

    space = VersionSpace(
        [
            Hypothesis(
                key=APPLY_KEY,
                predict=lambda t: _candidate_outcome(fn_apply, t),
                description="the demonstration's edit transfers to this target",
            ),
            Hypothesis(
                key=KEEP_KEY,
                predict=lambda t: _candidate_outcome(fn_keep, t),
                description="the target already has the form the demonstration was reaching for",
            ),
        ]
    )

    if oracle is None:
        return _result(
            REFUSE_NO_ORACLE_UNSETTLED,
            "the two candidate forms disagree on %d probed input(s) and no oracle was given "
            "to settle them; admitting would bank a guess. Fail closed. The disagreement "
            "points are the questions to ask." % len(disagreement),
            rules=rules,
            disagreement_points=disagreement,
            grid_size=len(grid),
            evidence=["UNSETTLED_NO_ORACLE", "QUESTIONS_WORTH_ASKING"],
        )

    # Asymmetric settlement. Refusing needs one contradiction; admitting must cover the
    # whole disagreement set. The first draft asked one question and let the posterior
    # settle: at (-1, -1) the oracle legitimately answers False, `apply_teach` also says
    # False, and the ruler declared the WRONG rule settled -- the audit's 0/200 one-success
    # result, reproduced in miniature. The loop below is the fix, and its cost is honest.
    remaining = list(disagreement)
    asked: list[tuple[Any, ...]] = []
    information_bits = 0.0
    while remaining:
        if len(asked) >= max(0, budget):
            return _result(
                REFUSE_UNSETTLED_BY_INSTRUMENT,
                "verified %d of %d disagreement point(s) within the question budget and all "
                "asked agreed; the unasked points are open questions. Admitting on partial "
                "coverage would bank a guess. Fail closed."
                % (len(asked), len(disagreement)),
                rules=rules,
                probes_asked=asked,
                disagreement_points=disagreement,
                grid_size=len(grid),
                settlement=_row(space, len(asked), information_bits, disagreement,
                                confidence, UNDERDETERMINED),
                evidence=["PARTIAL_COVERAGE"],
            )
        probe, gain = space.select_probe(remaining)
        if probe is None:  # pragma: no cover - candidates differ on every remaining point
            break
        outcome = _oracle_outcome(oracle, probe)
        information_bits += gain
        space.observe(probe, outcome)
        asked.append(probe)
        remaining.remove(probe)
        if outcome != _candidate_outcome(fn_apply, probe):
            # The oracle contradicts the taught form here: the target already has the form
            # the demonstration was reaching for. One contradiction settles the refusal.
            return _result(
                REFUSE_ORACLE_SAYS_KEEP,
                "the oracle contradicts the taught edit at the disagreement point %r; the "
                "target's boundary semantics keep their current form" % (probe,),
                rules=rules,
                probes_asked=asked,
                disagreement_points=disagreement,
                grid_size=len(grid),
                settlement=_row(space, len(asked), information_bits, disagreement,
                                confidence, SETTLED, winner_key=KEEP_KEY),
                evidence=["ORACLE_CONTRADICTS_APPLY"],
            )

    return _result(
        ADMIT_SETTLED,
        "the oracle agreed with the taught edit on every one of the %d disagreement "
        "point(s); the edit transfers to this target" % len(asked),
        rules=rules,
        edited_text=edited,
        probes_asked=asked,
        disagreement_points=disagreement,
        grid_size=len(grid),
        settlement=_row(space, len(asked), information_bits, disagreement,
                        confidence, SETTLED, winner_key=APPLY_KEY),
    )
