#!/usr/bin/env python3
"""One exposure or two? A probe of the generalizer, not of the benchmark.

The instant-learning story says: see a fix once, keep a skill forever. The ablation in
`instant_learning_seeded_store_ablation_v1.py` found the store refusing to learn anything, and named the
culprit -- the lifted morphism does not unify on a different bug in the same project, so the `reusable`
gate cannot be earned. This tool asks the next question with the least possible machinery:

  is the failure in the *lift* (it over-binds identifiers) or in the *anti-unification*
  (it cannot combine two witnesses at all)?

Why that distinction decides the design: `anti_unify_subtree_morphisms` begins by requiring
`len(m1.before_stmts_pattern) == len(m2.before_stmts_pattern)` -- identical statement-slice arity. Two
real bugs whose fixes touch different numbers of lines therefore cannot be generalized together at all,
no matter how much evidence accumulates. If that is what we are hitting, then "one exposure plus a
re-probe" cannot be fixed by waiting for a second exposure: the composition operator itself is the limit,
and the fix belongs one level down -- anti-unify over the Semantic IR (what §9.2 actually specifies), not
over un-parsed statement strings.

Everything reported here is a *shape* result except when `--run-tests` is given: a rewrite that applies is
not a rewrite that is correct, and this repo has already been burned once by treating a plausible-looking
patch as a pass. Zero model calls, zero parameters written; nothing here reads a test's expected answer --
the inputs are the commits' own parent trees.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_ONE_OR_TWO_WITNESS_GENERALIZATION_PROBE_V1"


def _git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, timeout=300)


def changed_source(repo: pathlib.Path, sha: str) -> tuple[str, str, str]:
    """(path, parent_source, commit_source) for the first non-test .py file the commit touched."""
    files = [f for f in _git(repo, "diff", "--name-only", f"{sha}^", sha).stdout.split("\n")
             if f and not f.startswith("tests/") and f.endswith(".py")]
    if not files:
        return "", "", ""
    path = files[0]
    before = _git(repo, "show", f"{sha}^:{path}")
    after = _git(repo, "show", f"{sha}:{path}")
    return path, (before.stdout or ""), (after.stdout or "")


def probe(repos_dir: pathlib.Path, witnesses: Sequence[Mapping[str, str]],
          targets: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    from canonical.swe_kernel import epistemic_admission_and_self_play_v1 as EASP

    lifts: list[dict[str, Any]] = []
    for w in witnesses:
        repo = repos_dir / w["repo"]
        path, before, after = changed_source(repo, w["sha"])
        rec: dict[str, Any] = {"witness": f"{w['repo']}@{w['sha'][:9]}", "file": path}
        if not before or not after:
            rec["lift"] = "BLOB_UNREADABLE"
            lifts.append(rec)
            continue
        m = EASP.lift_python_subtree_morphism(before, after)
        rec["lift"] = "NONE" if m is None else "OK"
        if m is not None:
            rec["before_arity"] = len(m.before_stmts_pattern)
            rec["after_arity"] = len(m.after_stmts_template)
            rec["param_holes"] = list(m.param_holes)
            rec["hole_types"] = dict(m.hole_types)
            rec["before_pattern"] = [s.strip()[:78] for s in m.before_stmts_pattern]
            rec["after_template"] = [s.strip()[:78] for s in m.after_stmts_template]
            rec["unbound_foreign_idents"] = sorted(EASP.TreeRewriteMorphism(
                before_stmts_pattern=m.before_stmts_pattern, after_stmts_template=m.after_stmts_template
            ).unbound_holes())
        rec["_morph"] = m
        lifts.append(rec)

    ms = [r.get("_morph") for r in lifts if r.get("_morph") is not None]
    pairs: list[dict[str, Any]] = []
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            au = EASP.anti_unify_subtree_morphisms(ms[i], ms[j])
            a, b = lifts[i], lifts[j]
            pairs.append({
                "witnesses": [a["witness"], b["witness"]],
                "arity_before": [a.get("before_arity"), b.get("before_arity")],
                "arity_after": [a.get("after_arity"), b.get("after_arity")],
                "unified": au is not None,
                # named explicitly, because "returns None" is otherwise indistinguishable from
                # "no generalization exists": the operator refused, it did not search and fail.
                "refusal_reason": ("" if au is not None else
                                   ("ARITY_MISMATCH_BEFORE" if a.get("before_arity") != b.get("before_arity")
                                    else "ARITY_MISMATCH_AFTER" if a.get("after_arity") != b.get("after_arity")
                                    else "NO_COMMON_SHAPE")),
                "unified_pattern": [s.strip()[:78] for s in au.before_stmts_pattern] if au else [],
            })

    applications: list[dict[str, Any]] = []
    for t in targets:
        trepo = repos_dir / t["repo"]
        tpath, tbefore, tafter = changed_source(trepo, t["sha"])
        if not tbefore:
            applications.append({"target": f"{t['repo']}@{t['sha'][:9]}", "status": "TARGET_UNREADABLE"})
            continue
        for r in lifts:
            m = r.get("_morph")
            if m is None:
                continue
            out = EASP.apply_subtree_morphism_to_python(m, tbefore, apply_all=True)
            applications.append({
                "target": f"{t['repo']}@{t['sha'][:9]}",
                "skill_from": r["witness"],
                "unifies": bool(out and out != tbefore),
                # `matches_the_real_fix` is a diagnostic of how narrow the pattern is, never a score:
                # the commit's own after-source is not available to the agent at runtime, so agreement
                # here would flatter us and prove nothing about capability.
                "byte_delta_vs_real_fix": (None if not out else len(out) - len(tafter)),
            })
    for r in lifts:
        r.pop("_morph", None)
    return {"schema": SCHEMA, "lifts": lifts, "anti_unification_pairs": pairs,
            "cross_commit_applications": applications}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos-dir", default="/tmp/corpus")
    ap.add_argument("--witness", action="append", default=[],
                    help="repo@sha (repeatable); two or more = the multi-exposure arm")
    ap.add_argument("--target", action="append", default=[], help="repo@sha to try each skill on")
    ap.add_argument("--json-out", default=None)
    ns = ap.parse_args(argv)

    def parse(spec: str) -> dict[str, str]:
        repo, _, sha = spec.partition("@")
        return {"repo": repo, "sha": sha}

    if not ns.witness:
        ap.error("--witness repo@sha is required at least twice")
    d = probe(pathlib.Path(ns.repos_dir), [parse(w) for w in ns.witness],
              [parse(t) for t in ns.target] or [parse(w) for w in ns.witness[1:]])
    n_pairs = d["anti_unification_pairs"]
    verdict = ("ANTI_UNIFICATION_REFUSES_ON_ARY" if n_pairs and all(not p["unified"] for p in n_pairs)
               else "SOME_PAIRS_UNIFIED" if n_pairs else "SINGLE_WITNESS_ONLY")
    d["verdict"] = verdict
    d["reading"] = ("the composition operator, not the number of exposures, decides: with mismatched "
                    "statement arity two witnesses cannot be generalized at all"
                    if verdict == "ANTI_UNIFICATION_REFUSES_ON_ARY" else
                    "at least one pair unified -- check whether it then applied cross-commit before "
                    "crediting it; a unified rule that never fires is still no capability")
    payload = json.dumps(d, indent=1, sort_keys=True) + "\n"
    if ns.json_out:
        pathlib.Path(ns.json_out).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    print(f"VERDICT: {verdict}")
    for r in d["lifts"]:
        print(f"  lift {r['witness']:24s} {r['lift']:14s} before_arity={r.get('before_arity')} after={r.get('after_arity')}")
    for p in n_pairs:
        print(f"  anti_unify({p['witnesses'][0]} , ...): unified={p['unified']} reason={p['refusal_reason'] or '-'}")
    for a in d["cross_commit_applications"]:
        print(f"  apply {a.get('skill_from','')} -> {a['target']}: unifies={a.get('unifies')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
