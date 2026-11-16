#!/usr/bin/env python3
"""Scope for the shipped skill store: bought with executed observations, enforced at recall.

THE GAP THIS CLOSES, MEASURED FIRST
-----------------------------------
`skill_scope_ledger_v1` ran the shipped `VERIFIED_SKILLS_BUNDLE_V1` through its own probes and
reported `5/5 EXACT_MATCH_ONLY` -- every rule fired exactly where it was taught and its
`applicability_state` was `UNDETERMINED__NO_CONTRASTING_OUTCOME`. Counts were shipped; states
were not. `macro_v1` documents the call-time half of the same hole: withholding on an
undetermined scope is described in a docstring and nowhere executed.

`skill_scope_acquisition_v1` already buys scope from executed observations, and
`contrast_selection_v1` already chooses the next question by exact information gain over states
the remaining victims would actually produce. Nothing wired either into the shipped store. This
module is that wiring, in both directions:

1. BUY. `paired_victims` constructs, from the rule's own token streams, paired worlds -- the
   same program under two different own-specifications, so the defective world is repaired and
   the already-correct world is broken by the unscoped skill. `attach_scopes` runs
   `skill_scope_acquisition_v1.buy_scope` over them and writes the resulting `scope` block into
   the rule payload. Rules whose lesson is not a single operator swap, or whose language has no
   fact extractor, get an honest `SCOPE_NOT_BOUGHT__...` status rather than a silent absence --
   a state, not a count.

2. WITHHOLD. `admit` is the law from `applicability_v1` applied at call time: a caller may
   withhold a plan ONLY on an `IDENTIFIED` requirement this target's observed facts do not
   meet. A rule with no identified scope is admitted with a named basis
   (`NOTHING_TO_WITHHOLD_ON`) -- never a pretended check. An identified scope whose facts
   cannot be computed (no oracle, extractor failure) is refused with the reason named, because
   an unexecuted baseline is not a fact.

`verified_skill_crystallizer_v1.recall_and_apply_verified` calls `admit` before proposing from
any rule that carries an identified scope. Rules without scope behave byte-for-byte as before.

WHY THE PAIRED WORLDS LOOK LIKE THIS
------------------------------------
A scope is only identified when the facts every success share are facts no failure has. Three
rename sets x three code shapes per rule keep the structural facts varying across successes so
the intersection collapses to `baseline.violates_own_spec` -- the one fact that separates the
defective worlds from the already-correct ones. With a single shape the shared
`operator.none_present` fact survives alongside it and the learner correctly answers
`AMBIGUOUS` instead of guessing. Both numbers must move or the scope is decoration: repairs
kept, breakages refused.

Authority: NONE. Producer-run measurement on constructed paired fixtures -- the same standard
`skill_scope_acquisition_probe_v1` is judged by. `whole_task_correctness_proved` stays False.
Zero model dependency at recall time.
"""
from __future__ import annotations

import copy
import json
import pathlib
import re
from typing import Any, Callable, Mapping, Sequence

from canonical.swe_kernel import operator_generalization_v1 as _gen
from canonical.swe_kernel import skill_scope_acquisition_v1 as _acq

SCHEMA = "PROJECT_BRAIN_SKILL_SCOPE_BUNDLE_V1"
SCOPE_NOT_BOUGHT = "SCOPE_NOT_BOUGHT"
AUTHORITY = "NONE__PRODUCER_RUN"

# Renames for instantiated hole ids. Three sets so successes and failures of different shapes
# never share accidental identifier facts.
_RENAMES: tuple[tuple[str, ...], ...] = (
    ("a", "b", "c", "d"),
    ("p", "q", "r", "s"),
    ("i", "j", "k", "m"),
)

# Grid of inputs searched for one where the original and swapped expressions differ, so the
# paired specs are separating by construction rather than by hand-written intent.
_GRID_2 = ((2, 3), (3, 2), (1, 4), (5, 1), (2, 2), (0, 3))
_GRID_3 = ((1, 2, 3), (3, 2, 1), (2, 1, 4), (1, 1, 1), (4, 3, 2))


# --------------------------------------------------------------------------- construction
def _instantiate(rule: Mapping[str, Any], key: str, names: Sequence[str]) -> str:
    """The rule's token stream with hole ids filled by concrete identifiers, in order."""
    out: list[str] = []
    holes: dict[str, str] = {}
    for kind, value in rule.get(key) or ():
        if kind == "hole_id":
            if value not in holes:
                if len(holes) >= len(names):
                    raise ValueError("MORE_HOLES_THAN_NAMES")
                holes[value] = names[len(holes)]
            out.append(holes[value])
        else:
            out.append(str(value))
    return "".join(out)


def _exec_ok(source: str, spec: str) -> bool:
    """Execute `source` then `spec`; the spec is assertions, so passing means they held."""
    ns: dict[str, Any] = {}
    try:
        exec(compile(source, "<scope-pair>", "exec"), ns)
        exec(compile(spec, "<scope-pair-spec>", "exec"), ns)
    except Exception:
        return False
    return True


def _run(source: str, fn: str, args: tuple[int, ...]) -> Any:
    ns: dict[str, Any] = {}
    exec(compile(source, "<scope-pair>", "exec"), ns)  # noqa: S102 -- fixture execution by design
    return ns[fn](*args)


def _pair_for_shape(rule: Mapping[str, Any], shape: str, names: tuple[str, ...]) -> dict[str, Any] | None:
    """One paired world: the same source under a defective spec and an already-correct spec.

    Returns None when no input separates the original from the swap for this shape -- recorded
    by the caller as `NO_CONTRASTING_INPUT_FOUND` rather than faked.
    """
    pattern_expr = _instantiate(rule, "pattern_tokens", names)[len("return ") :]
    replacement_expr = _instantiate(rule, "replacement_tokens", names)[len("return ") :]
    if not pattern_expr or not replacement_expr:
        return None

    callee_match = re.match(r"return (\w+)\(", _instantiate(rule, "pattern_tokens", names))
    if callee_match:
        callee = names[0]
        params = list(names[1:4])
        prelude = f"def {callee}(x, y):\n    return x + y\n"
    else:
        callee = None
        params = list(names[:2])
        prelude = ""

    p0, p1 = params[0], params[1]
    if shape == "bare":
        body = lambda expr: f"def f({', '.join(params)}):\n    return {expr}\n"  # noqa: E731
    elif shape == "ternary":
        # Adds a comparison so this shape's structural facts (operator.Gt, site.return)
        # differ from the bare shape's -- the diversity that collapses the survivor set.
        body = lambda expr: (  # noqa: E731
            f"def f({', '.join(params)}):\n"
            f"    return {expr} if {p0} > {p1} else 0\n"
        )
    elif shape == "if_preface":
        body = lambda expr: (  # noqa: E731
            f"def f({', '.join(params)}):\n"
            f"    if {p0} < {p1}:\n"
            f"        pass\n"
            f"    return {expr}\n"
        )
    else:  # pragma: no cover - internal shape table
        return None

    original = prelude + body(pattern_expr)
    swapped = prelude + body(replacement_expr)

    grid = _GRID_3 if len(params) == 3 else _GRID_2
    for args in grid:
        try:
            original_value = _run(original, "f", args)
            swapped_value = _run(swapped, "f", args)
        except Exception:
            continue
        if original_value == swapped_value:
            continue
        rendered = ", ".join(str(x) for x in args)
        label_prefix = callee or params[0]
        return {
            "defective": {
                "label": f"{label_prefix}_{shape}_defect",
                "source": original,
                # The defective world's OWN specification: it demands the swap's behaviour,
                # which the original program does not provide. Nothing here is told which
                # world is defective -- executing the spec decides that.
                "spec": f"assert f({rendered}) == {swapped_value}\n",
            },
            "already_correct": {
                "label": f"{label_prefix}_{shape}_already_correct",
                "source": original,
                "spec": f"assert f({rendered}) == {original_value}\n",
            },
        }
    return None


def paired_victims(rule: Mapping[str, Any]) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Paired defective/already-correct victims for this rule, or (None, honest_not_bought_reason).

    The reason is the exact `SCOPE_NOT_BOUGHT__...` suffix the scope block will carry. No
    exception, no silent empty list: a rule this constructor cannot build evidence for says so.
    """
    if not _gen.derive_operator_swap(rule):
        # Not a single-operator lesson (multi-token edits, declarations, optional chaining):
        # the paired-world constructor derives both sides from one operator difference.
        # Checked before language: for a rule this shape no extractor could help either.
        return None, "NOT_A_SINGLE_OPERATOR_LESSON"
    language = str(rule.get("language") or "").lower()
    if language != "python":
        # `observable_facts` is an AST walker for Python and refuses any other language; a fact
        # computed by the wrong parser is worse than no fact.
        return None, "NO_FACT_EXTRACTOR_FOR_LANGUAGE"

    victims: list[dict[str, Any]] = []
    for names in _RENAMES:
        for shape in ("bare", "ternary", "if_preface"):
            try:
                pair = _pair_for_shape(rule, shape, names)
            except ValueError:
                pair = None
            if pair is None:
                continue
            victims.append(pair["defective"])
            victims.append(pair["already_correct"])
    if not victims:
        return None, "NO_CONTRASTING_INPUT_FOUND"
    return victims, None


# --------------------------------------------------------------------------- buying
def buy_scope_for_rule(rule: Mapping[str, Any], *, budget: int | None = None) -> dict[str, Any]:
    """Run the acquisition protocol for one rule and return its scope block (never raises)."""
    victims, not_bought = paired_victims(rule)
    if not_bought is not None:
        return {
            "schema": SCHEMA,
            "status": f"{SCOPE_NOT_BOUGHT}__{not_bought}",
            "required": None,
            "reason": not_bought,
            "observations_spent": 0,
            "evidence_rows": 0,
            "victims_offered": 0,
            "authority": AUTHORITY,
        }

    assert victims is not None  # paired_victims: reason None implies victims
    report = _acq.buy_scope(
        rule,
        victims,
        budget=(len(victims) if budget is None else budget),
        language=str(rule.get("language") or "python").lower(),
    )
    boundary = report.pop("boundary", None)
    if boundary is not None and not report.get("status"):
        report["status"] = str(getattr(boundary, "status", "UNDETERMINED__NO_EVIDENCE"))
    return {
        "schema": SCHEMA,
        "status": str(report.get("status") or "UNDETERMINED__NO_EVIDENCE"),
        "required": (list(report["required"]) if report.get("required") else None),
        "reason": report.get("reason"),
        "observations_spent": int(report.get("observations_spent") or 0),
        "evidence_rows": int(report.get("evidence_rows") or 0),
        "victims_offered": len(victims),
        "authority": AUTHORITY,
    }


def attach_scopes(bundle: Mapping[str, Any], *, budget: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """A copy of `bundle` with a `scope` block inside every rule payload, plus a report.

    The block lives inside the inner rule payload, which `skill_identity` does not hash -- the
    content address of every shipped rule survives attachment unchanged.
    """
    out = copy.deepcopy(bundle)
    entries: list[dict[str, Any]] = []
    identified = 0
    not_bought = 0
    for entry in out.get("rules") or ():
        rule = entry.get("rule") if isinstance(entry, Mapping) else None
        if not isinstance(rule, Mapping):
            entries.append({"skill_id": entry.get("skill_id") if isinstance(entry, Mapping) else None,
                            "status": "SCOPE_NOT_BOUGHT__NO_RULE_PAYLOAD"})
            not_bought += 1
            continue
        scope = buy_scope_for_rule(rule, budget=budget)
        rule["scope"] = scope
        status = str(scope["status"])
        if status.startswith("IDENTIFIED"):
            identified += 1
        elif status.startswith(SCOPE_NOT_BOUGHT):
            not_bought += 1
        entries.append({
            "skill_id": entry.get("skill_id"),
            "language": rule.get("language"),
            "status": status,
            "required": scope.get("required"),
            "observations_spent": scope.get("observations_spent"),
            "evidence_rows": scope.get("evidence_rows"),
            "victims_offered": scope.get("victims_offered"),
        })
    report = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "rule_count": len(entries),
        "identified": identified,
        "not_bought": not_bought,
        "entries": entries,
    }
    return out, report


# --------------------------------------------------------------------------- the law at call time
def observed_facts(source_text: str, *, verifier: Callable[[str], bool] | None,
                   language: str = "python") -> dict[str, Any]:
    """Facts this target actually has, computed from executing its own specification.

    `{"ok": True, "facts": [...]}` or `{"ok": False, "reason": ...}`. A verifier that raises is
    undecided, not False: `skill_scope_acquisition_v1._default_executor` maps an exception to a
    failed specification, and that convention is the tree's own.
    """
    if verifier is None:
        return {"ok": False, "reason": "NO_ORACLE__BASELINE_NOT_EXECUTED"}
    try:
        baseline_ok = bool(verifier(source_text))
    except Exception:
        baseline_ok = False
    try:
        facts = _acq.observable_facts(source_text, baseline_ok=baseline_ok, language=language)
    except Exception as exc:  # e.g. NO_FACT_EXTRACTOR_FOR_LANGUAGE
        return {"ok": False, "reason": f"FACT_EXTRACTOR_FAILED__{type(exc).__name__}"}
    return {"ok": True, "facts": sorted(facts)}


def has_identified_scope(rule: Mapping[str, Any]) -> bool:
    scope = rule.get("scope")
    return isinstance(scope, Mapping) and str(scope.get("status") or "").startswith("IDENTIFIED")


def admit(rule: Mapping[str, Any], source_text: str, *, language: str = "python",
          verifier: Callable[[str], bool] | None = None,
          observed: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """May this rule be PROPOSED against this target? Withhold only on IDENTIFIED, per the law.

    * no scope block / scope not identified -> admitted, named `NOTHING_TO_WITHHOLD_ON` basis
    * identified, facts observed, requirement met -> admitted, `REQUIREMENT_SATISFIED`
    * identified, requirement absent from the facts -> refused, `missing` named
    * identified, facts unobservable (no oracle / extractor failure) -> refused, reason named
    """
    scope = rule.get("scope")
    if not isinstance(scope, Mapping):
        return {"admitted": True, "basis": "NO_IDENTIFIED_SCOPE__NOTHING_TO_WITHHOLD_ON",
                "scope_status": None, "missing": []}
    status = str(scope.get("status") or "")
    if not status.startswith("IDENTIFIED"):
        return {"admitted": True, "basis": f"SCOPE_{status}__NOTHING_TO_WITHHOLD_ON",
                "scope_status": status, "missing": []}

    required = list(scope.get("required") or ())
    obs = dict(observed) if observed is not None else observed_facts(
        source_text, verifier=verifier, language=language)
    if not obs.get("ok"):
        return {"admitted": False,
                "basis": f"IDENTIFIED_REQUIREMENT_UNOBSERVABLE__{obs.get('reason')}",
                "scope_status": status, "missing": required}
    check = _acq.admits(required, obs.get("facts") or ())
    return {"admitted": bool(check["admitted"]), "basis": str(check["basis"]),
            "scope_status": status, "missing": list(check.get("missing") or []),
            "facts": list(obs.get("facts") or ())}


# --------------------------------------------------------------------------- serialisation
def load_bundle(path: str | pathlib.Path) -> dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def save_bundle(bundle: Mapping[str, Any], path: str | pathlib.Path) -> None:
    target = pathlib.Path(path)
    target.write_text(json.dumps(bundle, indent=1, sort_keys=True), encoding="utf-8")


__all__ = [
    "SCHEMA",
    "SCOPE_NOT_BOUGHT",
    "AUTHORITY",
    "admit",
    "attach_scopes",
    "buy_scope_for_rule",
    "has_identified_scope",
    "load_bundle",
    "observed_facts",
    "paired_victims",
    "save_bundle",
]
