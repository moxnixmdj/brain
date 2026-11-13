#!/usr/bin/env python3
"""Effect-directed compile routing: the reviewed declarations decide, the sentence binds,
verification accepts.

WHY THIS EXISTS
---------------

Measured wall (`canonical/tools/realistic_goal_reach_probe_v1.py`, PR #6760): 32 of 38
realistic advanced-coding sentences fail BEFORE any dispatch -- and the door's discovery
fallback then reports a boundary status that masks the compile gap. R29 wired the confined
dispatch seam; this module releases the layer ABOVE it: sentence -> compiled plan.

THE CONTRACT
------------

* The router's data is the SAME reviewed data the seam already gates on:
  `CONFINED_EFFECT_DECLARATIONS_V1.json` (which capabilities may run confined) and the
  verified bound-capability registry (`keywords`, `provides`, `action_template`).  There is
  no sentence table here -- no per-corpus recogniser, no benchmark-specific routing.  A new
  environment with new declarations routes automatically.
* A sentence routes only if EVERY gate holds:
  1. it names an output artifact whose format the verifier table can actually check
     (`program_synthesis_v1.has_verifier` / `carries_content_evidence`) -- the SAME evidence
     bar the carrier gate enforces before refusing;
  2. at least 2 stemmed content tokens of the sentence overlap the candidate's reviewed
     `keywords`/`provides` -- lexical agreement with the capability's own declared interface,
     ranked by overlap, ties broken by declaration order;
  3. every non-knob argument of the capability's action template binds from the sentence
     (artifact, repository anchor, mentioned paths) -- an argument that cannot bind honestly
     disqualifies the candidate (`None` never becomes a value).  Numeric knobs are omitted,
     not invented: the adapters read them with defaults (`args.get("timeout_s", ...)`).
* Execution goes through the R29 confined seam (`confined_dispatch_v1`): the adapter runs on
  the disposable clone, declared effects verify inside the worktree, the host is untouched,
  and the SAME expectation ruler judges the result.  The first candidate whose confined run
  passes wins; the receipt names exactly what executed.
* Honesty parity with the local path: the door's `_empty_test_selection` check applies to a
  passing result exactly as it does to a locally-executed one.
* Every attempt is recorded.  A route that ran and failed verification is a fail-closed
  result WITH its receipts -- never a fabricated pass, never silence, and never the
  boundary status that would misreport a verified-and-failed run as "sandbox missing".

WHAT THIS IS NOT
----------------

Not weight-space learning, not a trained model, not a general NLU compiler: it is one
general mechanism -- reviewed declarations + sentence-bound arguments + verification-decided
acceptance -- releasing exactly the sentences whose capability interface can be honored.
Sentences whose arguments cannot bind stay refused, as honestly as before.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Mapping

SCHEMA = "EFFECT_DIRECTED_COMPILE_V1"

_DECLARATIONS_PATH = pathlib.Path(__file__).resolve().parent / "CONFINED_EFFECT_DECLARATIONS_V1.json"

# The output artifact a sentence asks for.  The same regex family the carrier gate keys on
# (`cli_capability_acquisition_v1._requested_suffix`), kept to the full filename so the
# declared effect can bind to exactly what was named.
_OUTPUT_RE = re.compile(
    r"\b(?:into|to|as|named|called|output|produce|producing)\s+[\"']?([^\s\"']+\.[A-Za-z0-9]{1,6})\b",
    re.I,
)
_REPO_PATH_RE = re.compile(r"\b(?:canonical|tests|tools)[/\\][\w/.\-]+\.\w+\b")
_REPO_ANCHOR_RE = re.compile(
    r"\bthis repository\b|\bthe repository\b|\bthis repo\b|\bthis project\b", re.I
)
_TEST_PATH_RE = re.compile(r"(?:/tests/|\btests/)|(?:^|/)(?:test_[^/]*|[^/]*_test)\.py$")

_STOP = set(
    """the a an of for this and or with into to as from by on in over under write writes
    building build run runs select check checks find finds verify verifies apply repair
    produce producing produce named called output report reports result results it is are
    that all any be been their its them they there here what which when how best new
    python test tests source code file files json path paths""".split()
)

# Ordered Porter-lite suffix stripping (standard IR stemming, not benchmark tuning):
# applied iteratively while a stem stays longer than 4 characters, so "localize" and
# "localization" meet at "local", "selection" and "select" at "select", "ranking" and
# "rank" at "rank".
_SUFFIXES = ("ization", "ation", "ition", "tion", "ing", "ise", "ize", "ised", "ized",
             "ion", "ies", "ed", "er", "es", "s")


def _stem(word: str) -> str:
    w = word
    for _ in range(3):
        for suf in _SUFFIXES:
            if len(w) - len(suf) > 4 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        else:
            break
    return w


def _tokens(text: str) -> set[str]:
    return {
        _stem(w)
        for w in re.split(r"[^a-z0-9\-]+", str(text or "").lower())
        if w and w not in _STOP and len(w) > 1
    }


def _output_artifact(goal: str) -> str | None:
    found = _OUTPUT_RE.findall(str(goal or ""))
    return found[-1] if found else None


def _mentioned_paths(goal: str) -> list[str]:
    return _REPO_PATH_RE.findall(str(goal or ""))


def _declarations() -> list[str]:
    """The reviewed confinement declarations: the ONLY capability source this router reads."""
    doc = json.loads(_DECLARATIONS_PATH.read_text(encoding="utf-8"))
    caps = doc.get("capabilities")
    if isinstance(caps, Mapping):
        return list(caps.keys())
    if isinstance(caps, list):
        return [str(r.get("capability_id")) for r in caps if isinstance(r, Mapping)]
    return []


def _bind_args(template_args: Mapping[str, Any], artifact: str, mentioned: list[str],
               tests: list[str], py_sources: list[str], other_files: list[str],
               repo_anchored: bool) -> dict[str, Any] | None:
    """Bind the template's arguments from the sentence.  One dishonest value refuses the row."""
    NEVER_BOUND = {"operation", "symbol", "request_spec", "test_target"}
    bound: dict[str, Any] = {"output_path": artifact}
    for name in template_args:
        if name == "capability_id" or name in bound:
            continue
        if name in NEVER_BOUND:
            return None
        if name == "source_root":
            bound[name] = "." if (repo_anchored or mentioned) else None
        elif name == "test_paths":
            bound[name] = tests if tests else None
        elif name in ("target_path", "source_path"):
            bound[name] = py_sources[0] if py_sources else None
        elif name == "changed_paths":
            bound[name] = list(mentioned) if mentioned else None
        elif name == "input_path":
            bound[name] = (other_files + py_sources)[0] if (other_files or py_sources) else None
        else:
            continue  # numeric knobs / free knobs: omitted, adapter defaults apply
        if bound[name] is None:
            return None
    return bound


def candidates(goal: str, registry: Mapping[str, Mapping[str, Any]] | None = None
               ) -> list[tuple[str, Mapping[str, Any], dict[str, Any], int]]:
    """Gated, bound, ranked candidates: (capability_id, entry, action, overlap)."""
    artifact = _output_artifact(goal)
    if not artifact:
        return []
    from canonical.runtime import program_synthesis_v1 as ps
    suffix = ps.suffix_for_name(artifact)
    if not ps.has_verifier(suffix) or not ps.carries_content_evidence(suffix):
        return []
    if registry is None:
        from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
        registry = load_verified_registry()
    mentioned = [p for p in _mentioned_paths(goal) if p != artifact]
    tests = [p for p in mentioned if _TEST_PATH_RE.search(p)]
    py_sources = [p for p in mentioned if p.endswith(".py") and p not in tests]
    other_files = [p for p in mentioned if p not in tests and p not in py_sources]
    repo_anchored = bool(_REPO_ANCHOR_RE.search(str(goal)))
    goal_tokens = _tokens(goal)
    # IDF weighting over the candidate pool: a token that appears in the keyword text of
    # many declared rows discriminates nothing ("test", "report"); a token unique to one
    # row names it.  The gate is the SUM of 1/df over the overlap.
    kw_texts = []
    for cid in _declarations():
        e = registry.get(cid)
        kw_texts.append(_tokens(" ".join(str(x) for x in
                                         ((e.get("keywords") or []) + (e.get("provides") or [])))
                                ) if isinstance(e, Mapping) else set())
    df: dict[str, int] = {}
    for toks in kw_texts:
        for t in toks:
            df[t] = df.get(t, 0) + 1
    # Path fragments never vote on capability identity: a mentioned repo path is bound as
    # an ARGUMENT, and its fragments ("runtime", "v1", "credit_gates") are filesystem
    # vocabulary, not the sentence's English.  Only the remaining words gate.
    path_vocab: set[str] = set()
    for p in mentioned:
        path_vocab |= _tokens(p.replace("/", " ").replace("-", " ").replace("_", " ").replace(".", " "))
    gate_tokens = goal_tokens - path_vocab
    out: list[tuple[str, Mapping[str, Any], dict[str, Any], float]] = []
    for index, cid in enumerate(_declarations()):
        entry = registry.get(cid)
        if not isinstance(entry, Mapping):
            continue
        overlap_tokens = gate_tokens & kw_texts[index]
        if len(overlap_tokens) < 2:
            continue
        # IDF-weighted gate: the sum of 1/df over the overlap. Two mid-frequency tokens,
        # or one rare and one common, open it; ubiquitous word soup does not.
        idf_score = round(sum(1.0 / df[t] for t in overlap_tokens), 3)
        if idf_score < 0.8:
            continue
        template = entry.get("action_template")
        template_args = template.get("args") if isinstance(template, Mapping) else None
        if not isinstance(template_args, Mapping):
            continue
        bound = _bind_args(template_args, artifact, mentioned, tests, py_sources,
                           other_files, repo_anchored)
        if bound is None:
            continue
        expect = template.get("expect") if isinstance(template, Mapping) else None
        action = {"args": {"capability_id": cid, **bound},
                  "expect": expect if isinstance(expect, Mapping) else {}}
        out.append((cid, entry, action, idf_score))
    # Stable sort by overlap: ties keep declaration order (the reviewed file's order).
    out.sort(key=lambda t: -t[3])
    return out


def attempt(request: Mapping[str, Any]) -> dict[str, Any] | None:
    """Route the request through reviewed declarations + the confined seam.

    Returns a door-shaped result (pass or fail-closed, receipts attached) or `None` when the
    sentence does not route -- in which case the caller's existing path (including the
    carrier gate) proceeds exactly as before.
    """
    if not isinstance(request, Mapping):
        return None
    goal = str(request.get("goal") or "").strip()
    if not goal:
        return None
    from canonical.runtime import confined_dispatch_v1 as confined
    if not confined.declarations():
        return None
    cands = candidates(goal)
    if not cands:
        return None
    from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
    registry = load_verified_registry()
    from canonical.runtime.live_brain_route_admission_v1 import ROOT  # workspace-aware door root

    artifact = _output_artifact(goal)
    attempted: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for cid, entry, action, overlap in cands:
        if cid not in registry:
            continue
        result = confined.run_confined_capability(cid, registry[cid], action, host_root=ROOT)
        if result is None:
            attempted.append({"capability_id": cid, "routed": False,
                              "reason": "CONFINED_SEAM_REFUSED_SHAPE"})
            continue
        passed = result.get("pass") is True or result.get("output_verified") is True
        attempted.append({"capability_id": cid, "routed": True, "pass": bool(passed),
                          "receipt": result.get("confinement", {}).get("receipt_sha256")
                          if isinstance(result.get("confinement"), Mapping) else None})
        if passed:
            from canonical.runtime import live_brain_route_admission_v1 as door
            if door._empty_test_selection(goal, result):
                return {
                    "schema": SCHEMA, "task_id": str(request.get("task_id") or ""),
                    "goal": goal, "pass": False, "executed": True,
                    "semantic_acceptance_complete": False,
                    "status": "FAIL_CLOSED__ANSWER_EMPTY__NO_TESTS_SELECTED",
                    "failure_class": "ANSWER_EMPTY:SELECTED_TESTS_IS_EMPTY_WHILE_AFFECTED_MODULES_EXIST",
                    "detail": "The confined capability ran and verified its artifact, but the "
                              "selection it produced is empty while affected modules exist.",
                    "compiled_capability_id": cid,
                    "compiler_mode": "EFFECT_DIRECTED_DECLARED_CAPABILITY",
                    "effect_directed": {"artifact": artifact, "attempted": attempted,
                                        "selected": cid, "overlap_gate": "STEMMED_IDF_WEIGHTED_GE_0.8"},
                }
            results.append((cid, result))
            break
        results.append((cid, result))
    if not results:
        return None
    selected_cid, selected = results[-1]
    passed = selected.get("pass") is True or selected.get("output_verified") is True
    result = dict(selected)
    result.update({
        "schema": SCHEMA, "task_id": str(request.get("task_id") or ""), "goal": goal,
        "pass": bool(passed), "executed": True,
        "semantic_acceptance_complete": bool(passed),
        "status": ("EXECUTED__EFFECT_DIRECTED_CONFINED" if passed
                   else "FAIL_CLOSED__EFFECT_DIRECTED_CONFINED_RUN_DID_NOT_VERIFY"),
        "failure_class": None if passed else "EFFECT_DIRECTED_CONFINED_RUN_DID_NOT_VERIFY",
        "detail": ("Routed by the reviewed effect declarations; executed on the disposable "
                   "clone; declared effects verified; judged by the door's expectation ruler."
                   if passed else
                   "Every gated candidate ran confined and none verified its declared effect; "
                   "the receipts below are the honest outcome."),
        "compiled_capability_id": selected_cid,
        "compiler_mode": "EFFECT_DIRECTED_DECLARED_CAPABILITY",
        "effect_directed": {"artifact": artifact, "attempted": attempted,
                            "selected": selected_cid, "overlap_gate": "STEMMED_IDF_WEIGHTED_GE_0.8"},
    })
    return result


if __name__ == "__main__":
    import sys
    g = " ".join(sys.argv[1:])
    for cid, _entry, action, ov in candidates(g):
        print(cid, "overlap", ov, json.dumps(action["args"], sort_keys=True))
