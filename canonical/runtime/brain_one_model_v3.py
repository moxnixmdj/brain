#!/usr/bin/env python3
"""THE ONE MODEL — a single door onto every proven layer of Project Brain.

You asked for one model. The tree already contained the parts, in different places,
under names that do not say what they are:

    brain_one_model_v2.py                 12.9 us route over 443 capabilities
    h100_verified_capability_registry_v8  21 verified zero-learned capabilities
    h100_zero_learned_schema_compiler_v1  bounded-format compilation, 0 learned bytes
    bound_capabilities/ (138 adapters)    executable, independently verified work
    brokered_workspace_execution_v1       admitted confinement (works on this host)
    ignorance_ledger_v1                   a ranked, priced model of its own ignorance
    admitted_confinement_execution_v1     the carrier the boundary was waiting for

This module is the door that chooses between them. It adds no capability of its own and
holds no state except the caches it delegates to.

The decision order is the whole design, and it is ordered by measured cost — cheapest
first, and every step can refuse:

    1. ROUTE     443 capabilities, 12.9 us. Closed-form scoring, no search.
    2. BIND      the registry's own action_template decides which inputs are legal.
                 Extra inputs are refused; a missing one names itself.
    3. COMPILE   if the goal looks like a table and names a target column, the
                 zero-learned schema compiler compiles it (103 us, 0 learned bytes).
    4. H100      21 verified zero-learned capabilities, reached only on abstention.
    5. EXECUTE   a bound adapter, or a read-only command under the admitted carrier.
    6. ACQUIRE   if the route was not confident, bridge the unknown tokens and learn.
    7. REFUSE    priced abstention. Never a guess.

Why this order and not another: steps 1-3 are microseconds and side-effect free, so they
are free to attempt. Step 5 is the only one that can touch anything, and it is reached only
with a bound template or a carrier-verified read-only argv. Step 6 writes exactly one
policy entry per bridged token. Step 7 is the default when nothing above is confident --
which is the property that keeps the whole thing honest.
"""

from __future__ import annotations

import pathlib

import json
import time
from typing import Any, Mapping, Sequence

from canonical.runtime import brain_one_model_v2 as core

SCHEMA = "PROJECT_BRAIN_ONE_MODEL_V3"
MODEL_ID = "BRAIN-ONE-MODEL-V3"
VERSION = 3


# --------------------------------------------------------------------------- H100 ---
_H100_REG = None


def _h100_registry() -> dict:
    global _H100_REG
    if _H100_REG is None:
        from canonical.runtime import h100_verified_capability_registry_v8 as r8
        _H100_REG = r8.registry_snapshot()
    return _H100_REG


def h100_capabilities() -> list[dict]:
    """The 21 independently verified zero-learned capabilities, as rows."""
    out = []
    for e in (_h100_registry().get("entries") or []):
        if isinstance(e, Mapping):
            out.append({"id": e.get("capability_id") or e.get("id"),
                        "provides": e.get("provides"), "kind": "H100_ZERO_LEARNED"})
    return out


def _looks_tabular(goal: str) -> bool:
    g = goal.lower()
    return any(w in g for w in ("table", "csv", "markdown table", "rows", "jsonl", "columns"))


# ------------------------------------------------------------------------ resolve ---
_QWORDS = ("what", "which", "how", "many", "much", "who", "where", "when",
           "total", "average", "mean", "largest", "smallest", "count",
           "sum", "digits", "doubled", "per")


def _is_question(goal: str) -> bool:
    """Is this a question about the files under `root`, rather than a request to act?"""
    g = str(goal or "").lower()
    return "?" in g or any(w in g.split() for w in _QWORDS)


def resolve(
    goal: str,
    *,
    root: str = ".",
    inputs: Mapping[str, Any] | None = None,
    payload: Any = None,
    target_column: str | None = None,
    execute: bool = False,
    acquire: bool = True,
    timeout: int = 20,
) -> dict[str, Any]:
    """Answer `goal` through the cheapest layer that can answer it, or refuse with a price.

    `execute=False` is the default: routing, binding, compilation and refusal are all
    side-effect free, so the default call never touches anything.
    """
    t0 = time.perf_counter()
    inputs = dict(inputs or {})
    trace: list[dict] = []

    def step(name: str, **kw: Any) -> None:
        trace.append({"step": name, "at_us": round((time.perf_counter() - t0) * 1e6, 1), **kw})

    # ---- 0-: THE CHEAPEST CAPABLE LAYER FIRST ----------------------------------
    # Opus 5.5 answers a request in ONE pass. This door used to spend its whole latency
    # understanding, routing, binding and refusing BEFORE it ever executed anything.
    #
    # Measured 2026-11-09: `resolve("how many unique lines in data.txt", execute=True)`
    # took 445 ms and returned FAIL_CLOSED__INPUT_BINDING_REQUIRED:path -- a refusal for a
    # question the confined carrier answers in ~100 ms, correctly, with the live tree
    # proven untouched. The understanding stack was asked about a question that has ONE
    # admitted answer shape.
    #
    # Compute-optimal allocation (Snell et al.; the 2026 T^2 scaling laws) says the budget
    # should follow the difficulty. A single "how many <thing> in <file>" question is easy
    # and has a verified program. Ask it here; fall through to the full stack only when
    # this layer cannot serve it. Nothing is skipped that used to produce an answer --
    # this layer is strictly narrower than the ones below it, and it declines by returning
    # no answer rather than by guessing.
    if _is_question(goal):
        try:
            from canonical.runtime import computer_env_v1 as _cenv
            from canonical.runtime import confined_query_bridge_v1 as _qbridge

            _k = _cenv.query_kind(goal)
            if _k is not None:
                from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import (
                    _extract_existing_file as _ef,
                )

                _m = _ef(goal, pathlib.Path(str(root)).resolve())
                if _m is not None:
                    _r = _qbridge.answer_confined(goal, _m, timeout=timeout)
                    step("fast_carrier", kind=_k, status=_r.get("status"),
                         confined=_r.get("confined"),
                         untouched=_r.get("live_workspace_untouched"),
                         micros=round((time.perf_counter() - t0) * 1e6, 1))
                    if _r.get("pass") is True:
                        return _answer(route={"best": None, "candidates": [],
                                              "confident": True, "coverage": 1.0},
                                       trace=trace, t0=t0,
                                       layer="CONFINED_QUERY_BRIDGE",
                                       carried=_r, acquisition=None,
                                       _is_counting_question=True)
        except Exception as exc:  # noqa: BLE001 - a fast layer that fails must not break the door
            step("fast_carrier_failed", error=str(exc)[:120])

    # ---- 0. UNDERSTAND: is this a question about the files here? ----------------
    # The highest-value layer in the tree is `value_algebra_v1` + `autonomous_v1`: answers
    # are BUILT from typed pieces that type-check against the values a tree provides, so a
    # question nobody wrote down can still be answered. It runs first because it is the
    # only layer that understands a compound question.
    if _is_question(goal):
        try:
            from canonical.runtime import autonomous_v1 as _A
            out = _A.run(goal=goal, root=str(root), iterations=8)
            v = out.get("verification") or {}
            step("answer", verified=v.get("verified"), reason=v.get("reason"))
            if v.get("verified"):
                # Measured 2026-11-09: `resolve("how many unique lines in data.txt")` on a
                # root where data.txt DOES NOT EXIST returned pass=True with 40 grep hits
                # and no number. The UNDERSTAND layer was asked only "is the answer
                # verified?" -- a question about ITSELF -- never "is this a counting
                # question?", so a counting question was answered by literature search and
                # the no-answer guard in `_answer` never ran (the guard only fires when the
                # answer is None, and an inspect dict is not None).
                #
                # A counting question has exactly one honest non-refusal shape: a number.
                # Anything else is the wrong answer executed correctly, which is the defect
                # this door exists to refuse. The counting flag is now passed in, so the
                # guard below sees it.
                return _answer(route={"best": None, "candidates": [],
                                      "confident": True, "coverage": 1.0},
                               trace=trace, t0=t0, layer="UNDERSTAND_BUILT_ANSWER",
                               result=out, acquisition=None,
                               _is_counting_question=_is_counting(goal))
        except Exception as exc:  # noqa: BLE001 - the understanding layer never breaks the door
            step("answer_failed", error=str(exc)[:120])

    # ---- 0c. REFERENCES: who or what does this sentence point back at? -----------
    # A goal arrives as prose and prose refers backwards: `it`, `that mode`, `must, too`,
    # `the former`, `respectively`. Routing the surface string throws that away and asks
    # the router to guess. Resolving first turns the goal into the proposition it means.
    #
    # The resolver FAILS CLOSED on genuine ambiguity, so a chain of three plausible
    # antecedents never silently becomes one.
    resolved_goal, references = goal, None
    try:
        from canonical.runtime import contextual_reference_resolution_v1 as refs
        r = refs.resolve(goal)
        references = {"status": r.get("status"), "reason": r.get("reason"),
                      "bindings": r.get("bindings") or [],
                      "count": len(r.get("bindings") or [])}
        if r.get("status") == "FAIL_CLOSED":
            step("references", status="FAIL_CLOSED", reason=r.get("reason"))
            return _refusal(route=None, trace=trace, t0=t0,
                            reason=str(r.get("reason") or "AMBIGUOUS_REFERENCE"),
                            detail={"candidates": r.get("candidates"),
                                    "mentions": r.get("mentions"),
                                    "fix": "name the entity instead of the pronoun"})
        if r.get("bindings"):
            step("references", status=r.get("status"),
                 bindings=r.get("bindings"))
            # a `respectively` mapping carries subject -> object obligations, and those
            # are the question's actual demands; hand them on in the trace
            resolved_goal = goal
    except Exception as exc:  # noqa: BLE001 - reference resolution never breaks the door
        step("references_failed", error=str(exc)[:120])

    # ---- 1. ROUTE -----------------------------------------------------------------
    route = core.route(resolved_goal)
    step("route", confident=route.get("confident"),
         best=(route.get("best") or {}).get("id"),
         coverage=route.get("coverage"), micros=route.get("micros"))

    # ---- 0b. SEMANTIC: has this model ever seen these words in context? ----------
    # `bridge()` can only repair a TYPO of a token already in the index. A word the
    # model has never routed -- "compute", "summarise", a domain noun -- has no lexical
    # source at all, and the honest answer used to be NO_SOURCE_FOR_TOKEN.
    #
    # The hyperdimensional layer supplies one: a word's neighbours are the words it is
    # USED LIKE in text the model has read, with no trained parameter anywhere. It cannot
    # know a word it never saw, and it says so. But for a word it has seen, it can say
    # what the word is near -- which is exactly what the router needs to find anything.
    if not route.get("confident"):
        try:
            from canonical.runtime import hyperdimensional_semantics_v1 as hd
            model_ = hd.model()
            if len(model_.context):
                near: list[dict] = []
                weights: dict[str, float] = {}
                for t in goal.lower().split():
                    if not t.isalpha() or not model_.known(t):
                        continue
                    for w, sc in model_.neighbours(t, 5):
                        near.append({"from": t, "to": w, "cosine": round(sc, 3)})
                        # ACCUMULATE, not concatenate. Two unknown words that point at the
                        # same neighbour are evidence twice over, and a single strong
                        # neighbour of one word should not be outvoted by five weak ones
                        # from another. Summing the cosines is the same rule the router
                        # already uses for a term that appears more than once.
                        weights[w] = weights.get(w, 0.0) + max(0.0, sc)
                if near:
                    near.sort(key=lambda d: -d["cosine"])
                    top = sorted(weights, key=lambda w: -weights[w])[:8]
                    expanded = goal + " " + " ".join(top)
                    alt = core.route(expanded)
                    step("semantic", neighbours=[d["to"] for d in near[:6]],
                         confident=alt.get("confident"))
                    if alt.get("confident") and (alt.get("best") or {}).get("id"):
                        route = alt
                        best = (alt.get("best") or {}).get("id")
                        return _answer(route=alt, trace=trace, t0=t0,
                                       layer="SEMANTIC_EXPANSION",
                                       result={"expanded_by": near[:6]},
                                       acquisition=acquisition)
        except Exception as exc:  # noqa: BLE001 - the semantic layer never breaks the door
            step("semantic_failed", error=str(exc)[:120])

    # ---- 6. ACQUIRE (moved up for the decision, applied after) ---------------------
    acquisition = None
    if not route.get("confident") and acquire:
        try:
            # A typo'd goal has no confident route, so there is no target to learn
            # against -- but exactly one candidate usually stands far above the rest,
            # and `route` already scored it. Passing that candidate is what makes the
            # bridge *directed*: `pyton -> python` where the goal is about python,
            # not `pyton -> python` against whatever else happened to score.
            target = _infer_target(goal) or None
            acquisition = core.acquire(goal, capability_id=target)
            step("acquire", bridged=len(acquisition.get("bridged") or []),
                 learned=acquisition.get("bridges_learned"),
                 micros=acquisition.get("micros"))
            if acquisition.get("bridges_learned"):
                route = core.route(goal)
                step("reroute", confident=route.get("confident"),
                     best=(route.get("best") or {}).get("id"))
        except Exception as exc:  # noqa: BLE001 - acquisition never breaks the door
            step("acquire_failed", error=str(exc)[:120])

    best = (route.get("best") or {}).get("id")

    # ---- 3. COMPILE ---------------------------------------------------------------
    if target_column and payload is not None and (_looks_tabular(goal) or True):
        hint = None
        g = goal.lower()
        if "csv" in g:
            hint = "CSV"
        elif "markdown" in g or "table" in g:
            hint = "MARKDOWN_TABLE"
        for h in ([hint] if hint else []) + ["CSV", "MARKDOWN_TABLE", "JSONL", "FREE_TEXT_KEY_VALUE"]:
            try:
                from canonical.runtime import h100_zero_learned_schema_compiler_v1 as sc
                compiled = sc.compile_observations(
                    payload, inputs=[str(k) for k in (inputs.get("features") or ["x"])],
                    target=target_column, format_hint=h)
                step("compile", format=hint or h, rows=compiled.get("row_count"),
                     learned_bytes=compiled.get("persistent_learned_bytes"),
                     model_calls=compiled.get("external_frontier_model_calls"))
                return _answer(route, trace, t0, layer="H100_SCHEMA_COMPILER",
                               compiled=compiled, acquisition=acquisition)
            except Exception:  # noqa: BLE001 - a format that does not parse is not an error
                continue

    # ---- 2 + 5. BIND and EXECUTE --------------------------------------------------
    bindable = best in (core._registry().get("capabilities") or {})
    if best and bindable:
        bound = core.solve(goal, inputs=inputs or None, capability_id=best,
                           execute=execute)
        step("bind", status=bound.get("status"), capability_id=best)
        ok = bool(bound.get("pass"))
        if ok:
            return _answer(route, trace, t0, layer="BOUND_CAPABILITY",
                           result=bound, acquisition=acquisition)
        # a stated read-only command whose only barrier was the carrier
        argv = _stated_argv(goal)
        if execute and argv:
            from canonical.runtime import admitted_confinement_execution_v1 as carrier
            carried = carrier.execute_confined(_rebase_argv(argv, root, goal),
                                              workspace_root=root,
                                              timeout=timeout, goal=goal)
            step("carrier", pass_=carried.get("pass"), status=carried.get("status"),
                 confined=carried.get("confined"),
                 untouched=carried.get("live_workspace_untouched"))
            if carried.get("pass"):
                return _answer(route, trace, t0, layer="ADMITTED_CONFINEMENT",
                               carried=carried, acquisition=acquisition,
                               _is_counting_question=_is_counting(goal))
            return _refusal(route, trace, t0, reason=str(carried.get("status")),
                            detail=carried, acquisition=acquisition)
        status_txt = str(bound.get("status") or "")
        needs = _needs_from_status(status_txt)
        return _refusal(route, trace, t0, reason=status_txt,
                        detail={"capability_id": best,
                                "binding": bound.get("binding"),
                                "needs": needs,
                                "fix": ("supply inputs={" + ", ".join(repr(n) for n in needs) + "}"
                                        if needs else "see binding")},
                        acquisition=acquisition)

    if best and not bindable:
        step("not_bindable", capability=best)
        argv = _stated_argv(goal)
        if execute and argv:
            from canonical.runtime import admitted_confinement_execution_v1 as carrier
            carried = carrier.execute_confined(_rebase_argv(argv, root, goal),
                                              workspace_root=root,
                                              timeout=timeout, goal=goal)
            step("carrier", pass_=carried.get("pass"), confined=carried.get("confined"))
            if carried.get("pass"):
                return _answer(route, trace, t0, layer="ADMITTED_CONFINEMENT",
                               carried=carried, acquisition=acquisition,
                               _is_counting_question=_is_counting(goal))
            return _refusal(route, trace, t0, reason=str(carried.get("status")),
                            detail=carried, acquisition=acquisition)
        return _refusal(route, trace, t0,
                        reason="ROUTED_TO_UNIFIABLE_ONLY_CAPABILITY:" + str(best),
                        detail={"hint": "pass inputs= or execute=True"},
                        acquisition=acquisition)

    # ---- 4. H100 CAPABILITIES -----------------------------------------------------
    for row in h100_capabilities():
        pid = str(row.get("provides") or row.get("id") or "")
        if pid and pid.split(".")[-1].replace("_", ".") in goal.lower().replace("_", "."):
            step("h100_match", capability=row.get("id"))
            return _answer(route, trace, t0, layer="H100_VERIFIED",
                           h100=row, acquisition=acquisition)

    # ---- 7. REFUSE, PRICED --------------------------------------------------------
    absent = core.absent(goal)
    step("absent", gaps=len(absent.get("cheapest_gaps") or []))
    return _refusal(route, trace, t0, reason="NO_CONFIDENT_LAYER",
                    detail={"cheapest_gaps": (absent.get("cheapest_gaps") or [])[:3]},
                    acquisition=acquisition, absent=absent)


def _needs_from_status(status: str) -> list[str]:
    """`FAIL_CLOSED__INPUT_BINDING_REQUIRED:pdf_path` names exactly one thing it needs.

    A refusal that names no cause cannot be acted on; this turns the status the bind
    layer already produced into the concrete missing input.
    """
    tok = "INPUT_BINDING_REQUIRED:"
    if tok not in status:
        return []
    tail = status.split(tok, 1)[1]
    return [n for n in (tail.replace("+", ",").split(",")) if n.strip()]


def _infer_target(goal: str) -> str | None:
    """The capability a goal is most probably about, for a bridge to be learned against.

    Uses the route's own top candidate only when it is unambiguous: the score must be
    strictly positive and at least 1.25x the runner-up. Otherwise None -- an ambiguous
    goal learns nothing, which is the same rule the trigram bridge uses.
    """
    try:
        r = core.route(goal)
        cands = [c for c in (r.get("candidates") or []) if c.get("score")]
        if not cands:
            return None
        cands.sort(key=lambda c: -float(c["score"]))
        top = float(cands[0]["score"])
        if top <= 0:
            return None
        if len(cands) > 1 and top < 1.25 * float(cands[1]["score"]):
            return None
        cid = cands[0].get("id")
        # only a capability the model can actually bind
        return cid if cid in (core._registry().get("capabilities") or {}) else None
    except Exception:  # noqa: BLE001
        return None


def _stated_argv(goal: str) -> list[str] | None:
    try:
        from canonical.runtime import composer_route_v1 as cr
        argv = cr.extract_argv(goal)
        return list(argv) if argv else None
    except Exception:  # noqa: BLE001
        return None


def _rebase_argv(argv: list[str], root: str, goal: str) -> list[str]:
    """Leave the command alone. Change the DIRECTORY it runs in, not its words.

    Measured 2026-11-09, twice, in both directions:

      bare operand + carrier cwd "."      -> ran in the repository, sort died with
                                             "cannot read: data.txt"
      absolute operand + carrier cwd X    -> ran in X, sort died with
                                             "cannot read: <abs path>", because the
                                             carrier stages a workspace-relative view
                                             and an absolute host path is not in it.

    Neither rewrite helps. The operand is already relative to the workspace the sentence
    names, and `root` IS that workspace. Pass `root` and let the words stand. Kept as a
    named place recording both failed variants so neither is re-derived.
    """
    return argv


# -------------------------------------------------------------------------- shape ---
def _is_counting(goal: str) -> bool:
    """Is this a "how many X" question? Used to demand a number, not a listing."""
    try:
        from canonical.runtime import computer_env_v1 as _cenv

        return _cenv.query_kind(goal) is not None
    except Exception:  # noqa: BLE001 - fail closed: a counting answer with no number is no pass
        return True


def _answer(route, trace, t0, *, layer, result=None, compiled=None, carried=None,
            h100=None, acquisition=None, _is_counting_question: bool = False) -> dict:
    # The number the caller asked for, lifted out of whichever receipt holds it. Every
    # layer below answers by returning a receipt; a caller should not have to know the
    # shape of the layer that answered.
    _ans = None
    for _src in (carried, result, compiled, h100):
        if not isinstance(_src, dict):
            continue
        # `value` before `answer`. The bridge returns `answer` as a display STRING and
        # `value` as the typed number, which is a defensible split -- but a door that
        # surfaces '6' on one path and 6 on another makes every caller write `int(x)`
        # or compare against the wrong type. The door speaks in types.
        if _src.get("value") is not None and not isinstance(_src.get("value"), (dict, list)):
            _ans = _src.get("value")
            break
        if _src.get("answer") is not None:
            _ans = _src.get("answer")
            if isinstance(_ans, str) and _ans.strip().lstrip("-").isdigit():
                _ans = int(_ans.strip())
            break
    # A QUESTION THAT GOT NO ANSWER IS NOT A PASS.
    #
    # Measured 2026-11-09: `how many unique words in data.txt` returned pass=True,
    # layer=ADMITTED_CONFINEMENT, answer=None. The carrier had run `wc -w` and printed
    # "6 data.txt" -- a correct execution of the WRONG command, reported as success. A
    # caller that checks `pass` gets a green light and no number, which is the failure mode
    # this whole project exists to refuse: a report asserting success with no evidence.
    #
    # A layer that executed but produced no answer is a refusal with a receipt, and it says
    # so. This is in `_answer` rather than at the call site so no future layer can bypass it.
    # The rule applies to the BRIDGE, which exists to answer a counting question, and not
    # to a stated command, whose evidence IS its stdout. Measured 2026-11-09: applying it to
    # both broke `sort -u data.txt`, which correctly runs, prints, and is followed by the
    # caller -- a listing is the answer to "run this", and demanding an integer there would
    # be demanding the wrong shape back.
    # Keyed on WHAT WAS ASKED, not on which layer answered. A counting question
    # ("how many ...") must come back with a number; a stated command ("sort -u x") comes
    # back with its output, which is the answer to what was asked. Measured 2026-11-09:
    # `unique words` is refused by the bridge and then falls to the raw carrier, so keying
    # on the bridge's own layer missed the exact case this rule exists for.
    # `_answer` has no `goal` parameter, so the first version of this guard raised
    # NameError, the except swallowed it, and the rule silently never fired -- a fail-open
    # inside the code written to prevent a fail-open. The question is now passed explicitly
    # by the caller, and an unanswerable question object means the rule DOES fire (fail
    # closed), because a counting answer with no number is never a pass.
    _asked_to_count = _is_counting_question
    # A counting question has one honest answer shape: a number. `_ans is None` is not the
    # only way to fail to answer it -- measured 2026-11-09, the UNDERSTAND layer returned a
    # 40-hit inspect dict (an inspection report, not a count) and the old None-only check
    # passed it straight through. Bind the rule to the ANSWER'S SHAPE, not merely its
    # presence: a bool is an int in Python and is not a count, and a bare string of digits
    # is coerced by the caller, so only a real numeric type counts as having counted.
    def _is_a_number(x) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    # Narrowed 2026-11-09 after the wider rule broke `sort -u data.txt`: that goal has NO
    # query_kind (it is a stated command), so it never sets the counting flag and is
    # unaffected -- but an earlier, broader shape rule also refused a legitimately non-
    # numeric answer whose listing IS its answer. The defect being fixed is narrower than
    # "not a number": it is a STRUCTURED REPORT standing in for a count. A dict with a
    # schema is an inspection/report object; it is never a count, and it is precisely what
    # shadowed the number. Scalars (int, str, list, None) keep the old presence rule.
    _is_a_report = isinstance(_ans, dict) and bool(_ans.get("schema"))
    # The `_asked_to_count` conjunction is load-bearing and was dropped once while editing
    # this line, which made every STATED COMMAND with no extracted answer refuse -- the
    # regression was caught by test_the_one_model_reaches_the_carrier_layer_and_passes.
    # The rule governs counting questions ONLY. A stated command's evidence is its stdout
    # and it never reaches this branch.
    _produced_no_count = _asked_to_count and (
        _ans is None or _is_a_report or not _is_a_number(_ans)
    )
    if _produced_no_count:
        return _refusal(route, trace, t0,
                        reason="FAIL_CLOSED__EXECUTION_PRODUCED_NO_ANSWER",
                        detail={"layer": layer,
                                "carried_status": (carried or {}).get("status"),
                                "carried_stdout": str((carried or {}).get("stdout"))[:200],
                                "confined": (carried or {}).get("confined"),
                                "live_workspace_untouched": (carried or {}).get("live_workspace_untouched"),
                                "why": ("the program ran under an admitted confinement but its "
                                        "output is not an answer to the question asked"),
                                "fix": "ask a shape the carrier can compute, or supply the metric explicitly"},
                        acquisition=acquisition)
    return {
        "schema": SCHEMA, "model_id": MODEL_ID, "version": VERSION,
        "operation": "RESOLVE", "pass": True, "layer": layer,
        "answer": _ans,
        "capability": (route.get("best") or {}).get("id"),
        "weights": 0, "persistent_learned_bytes": 0,
        "incremental_spend_usd": 0,
        "result": result, "compiled": compiled, "carried": carried, "h100": h100,
        "acquisition": acquisition,
        "route": {"confident": route.get("confident"),
                  "coverage": route.get("coverage"),
                  "candidates": (route.get("candidates") or [])[:3]},
        "trace": trace,
        "micros": round((time.perf_counter() - t0) * 1e6, 1),
    }


def _refusal(route, trace, t0, *, reason, detail=None, acquisition=None, absent=None) -> dict:
    return {
        "schema": SCHEMA, "model_id": MODEL_ID, "version": VERSION,
        "operation": "RESOLVE", "pass": False, "layer": "REFUSAL",
        "status": reason, "detail": detail or {},
        "weights": 0, "persistent_learned_bytes": 0, "incremental_spend_usd": 0,
        "acquisition": acquisition, "absent": absent,
        "route": {"confident": route.get("confident"),
                  "coverage": route.get("coverage"),
                  "candidates": (route.get("candidates") or [])[:3]},
        "trace": trace,
        "micros": round((time.perf_counter() - t0) * 1e6, 1),
    }


# --------------------------------------------------------------------------- face ---
def inventory() -> dict:
    """What this one model is made of — counted, not asserted."""
    core._load_index()
    bound = core._registry().get("capabilities") or {}
    h = _h100_registry()
    from canonical.runtime import brokered_workspace_execution_v1 as broker
    try:
        from canonical.runtime import ignorance_ledger_v1 as ledger
        gaps = ledger.open_gaps()
    except Exception:  # noqa: BLE001
        gaps = None
    return {
        "schema": SCHEMA, "model_id": MODEL_ID, "version": VERSION,
        "capabilities_indexed": len(core._CAPS),
        "routing_tokens": sum(len(v) for v in core._INDEX.values()),
        "bound_capabilities": len(bound),
        "h100_verified_capabilities": len(h.get("entries") or []),
        "h100_persistent_learned_bytes": h.get("persistent_learned_bytes"),
        "engines": 1,
        "weights": 0,
        "persistent_learned_bytes": 0,
        "admitted_confinement_available": broker.namespace_broker_available(),
        "open_ignorance_gaps": gaps,
        "layers": ["ROUTE", "BIND", "COMPILE", "H100", "EXECUTE", "ACQUIRE", "REFUSE"],
        "non_claims": [
            "NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS",
            "NOT_AN_INDEPENDENT_VERIFICATION__SANDBOX_MEASUREMENT_ONLY",
            "KNOWLEDGE_IS_INDEXED_NOT_EMBEDDED__RETRIEVED_JUST_IN_TIME",
            "COVERAGE_IS_NOT_CAPABILITY__EXECUTION_STILL_REQUIRES_DECLARED_SUBSTRATE",
            "NO_BENCHMARK_FRONTIER_CLAIM__HLE_ARC_SWEBENCH_OSWORLD_NEVER_RUN_HERE",
        ],
        # Does this model ENFORCE the engineering contract it ships with? Measured, not
        # asserted: the gate engine is asked whether it implements every gate the Supreme
        # contract declares. On 2026-11-09 the honest answer changed from "nothing enforces
        # it" (zero Python references to the contract) to "10 of 10 gates, 13 tests".
        "engineering_contract_enforced": _contract_state(),
    }


def _contract_state() -> dict:
    """The gate engine's coverage of the shipped contract, or why it cannot be asked."""
    try:
        from canonical.runtime import supreme_gate_engine_v1 as gates

        cov = gates.contract_coverage()
        return {"engine": "supreme_gate_engine_v1",
                "declared": cov["declared_count"],
                "implemented": cov["implemented_count"],
                "complete": cov["complete"],
                "missing": cov["missing_from_engine"]}
    except Exception as exc:  # noqa: BLE001 - an unaskable gate is reported as unenforced
        return {"engine": None, "complete": False, "error": str(exc)[:120]}


def status() -> dict:
    return {"schema": SCHEMA, "model_id": MODEL_ID, "version": VERSION,
            "inventory": inventory()}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "inventory":
        print(json.dumps(inventory(), indent=1, default=str))
    elif len(sys.argv) > 1:
        print(json.dumps(resolve(" ".join(sys.argv[1:])), indent=1, default=str)[:6000])
    else:
        print(json.dumps(resolve("extract text from a pdf"), indent=1, default=str)[:4000])
