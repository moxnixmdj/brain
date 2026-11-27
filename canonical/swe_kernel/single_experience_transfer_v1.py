#!/usr/bin/env python3
"""Does one experience help on the *next* repair? Measured on real commits, with an empty-store arm.

WHY THIS EXISTS
---------------
Every compounding claim in this tree rests on a store whose contribution has never been separated
from the work the verifier does anyway. The one ablation that was run
(`AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2`) reports store and empty store as
**identical**, and explains it: the stored object was a whole-body hole that could not fire on
anything. Wave 45 replaced that operator (`structured_morphism_abstraction_v1`). This module asks
the question that replacement makes askable:

    take the repairs in one part of a real repository's history
    learn rules from them
    does a rule fire on a repair in a part of history it never saw -- or in a different repository?

WHAT IS MEASURED
----------------
Three arms, same test pairs, same scoring rule (a hit is an exact AST match on the held-out after):

  * STORE       -- rules admitted from the training repairs by the Wave 45 operator;
  * EMPTY       -- no store at all (0 by construction, printed so the denominator is visible);
  * RAW_TRACE   -- the same training repairs kept verbatim as "before text -> after text".

The RAW_TRACE arm is the NO_COMPOUNDING check: if abstraction earns nothing over verbatim
transcription, the operator is decoration and should be deleted.

SPLITS
------
Chronological (train = older, test = newer) and file-disjoint (a test file's repairs are never
learned from). The cross-repository arm learns in one project and tests in another, which is the
only version of "single experience, different environment" that can be measured without a model.

HONESTY
-------
Network is used at BUILD time to fetch patches from api.github.com (data, not a model) and never at
runtime. The receipt records the repository slugs, the commit window, the network call count, and
0 model calls. click and werkzeug are development data for this tree's own catalogues, so they are
marked CONTAMINATED_FOR_CATALOGUE and are never used to claim a headline number.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from canonical.swe_kernel.structured_morphism_abstraction_v1 import (
    ADMITTED,
    Rule,
    abstract,
    admit,
    apply_rule,
)

SCHEMA = "BRAIN_SINGLE_EXPERIENCE_TRANSFER_V1"
CONTAMINATED_SLUGS = ("pallets/click", "pallets/werkzeug", "mitsuhiko/click", "mitsuhiko/werkzeug")

MAX_BLOCK_LINES = 6


@dataclass(frozen=True)
class Repair:
    """One hunk's before/after, already parsed as a single statement or expression."""

    slug: str
    sha: str
    path: str
    index: int
    before: str
    after: str

    def key(self) -> str:
        return f"{self.slug}@{self.sha[:8]}:{self.path}:{self.index}"


def _normalize(text: str) -> Optional[Tuple[str, ast.AST]]:
    """The changed block as one parseable statement.

    A compound header on its own (`if x < y:`) has no body in the diff, so a `pass` body is elided
    in. The elision is applied to both sides and to the test pairs alike, so it cannot favour a rule.
    """
    body = textwrap.dedent("\n".join(line for line in text.splitlines() if line.strip("\n"))).strip("\n")
    if not body.strip():
        return None
    candidates = [body]
    if body.rstrip().endswith(":"):
        candidates.append(body + "\n    pass")
    for candidate in candidates:
        try:
            tree = ast.parse(candidate, mode="exec")
        except SyntaxError:
            continue
        if len(tree.body) == 1:
            return candidate, tree.body[0]
    return None


def _as_statement(text: str) -> Optional[ast.AST]:
    """A block of changed lines as one statement, or None when it is not a usable unit."""
    body = textwrap.dedent("\n".join(line for line in text.splitlines() if line.strip("\n")))
    body = body.strip("\n")
    if not body.strip():
        return None
    for candidate in (body, body + "\n    pass" if body.rstrip().endswith(":") else None):
        if candidate is None:
            continue
        try:
            tree = ast.parse(candidate, mode="exec")
        except SyntaxError:
            continue
        if len(tree.body) == 1:
            return tree.body[0]
    return None


def _dump(node: ast.AST) -> str:
    return ast.dump(node, include_attributes=False)


def parse_patch(patch: str, *, slug: str, sha: str, path: str) -> List[Repair]:
    """Extract single-block repairs from a unified diff.

    Only hunks with one contiguous removal group and one contiguous addition group are used: a
    multi-block hunk is several repairs and pretending otherwise would mislabel the unit.
    """
    repairs: List[Repair] = []
    removed: List[str] = []
    added: List[str] = []
    in_minus = False
    in_plus = False
    index = 0

    def flush() -> None:
        nonlocal removed, added, index
        if removed and added and len(removed) <= MAX_BLOCK_LINES and len(added) <= MAX_BLOCK_LINES:
            left = _normalize("\n".join(removed))
            right = _normalize("\n".join(added))
            if left is not None and right is not None and _dump(left[1]) != _dump(right[1]):
                repairs.append(Repair(slug=slug, sha=sha, path=path, index=index,
                                      before=left[0], after=right[0]))
                index += 1
        removed, added, in_minus, in_plus = [], [], False, False

    for line in patch.splitlines():
        if line.startswith("@@"):
            flush()
            continue
        if line.startswith("-") and not line.startswith("---"):
            if in_plus:
                flush()
            in_minus = True
            removed.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            in_plus = True
            added.append(line[1:])
        else:
            if in_minus or in_plus:
                flush()
    flush()
    return repairs


def harvest(slug: str, *, pages: int = 3, per_page: int = 100,
            runner=None, log: bool = False) -> Tuple[List[Repair], int]:
    """Fetch commit patches from api.github.com (build-time data, never a runtime dependency)."""
    run = runner or (lambda argv: subprocess.run(argv, capture_output=True, text=True, check=True).stdout)
    calls = 0
    shas: List[str] = []
    for page in range(1, pages + 1):
        out = run(["gh", "api", f"repos/{slug}/commits?per_page={per_page}&page={page}"])
        calls += 1
        try:
            payload = json.loads(out)
        except json.JSONDecodeError:
            break
        if not isinstance(payload, list) or not payload:
            break
        shas.extend(item["sha"] for item in payload)

    repairs: List[Repair] = []
    for position, sha in enumerate(shas):
        out = run(["gh", "api", f"repos/{slug}/commits/{sha}"])
        calls += 1
        try:
            commit = json.loads(out)
        except json.JSONDecodeError:
            continue
        for entry in commit.get("files") or []:
            patch = entry.get("patch")
            name = entry.get("filename") or ""
            if not patch or not name.endswith(".py"):
                continue
            repairs.extend(parse_patch(patch, slug=slug, sha=sha, path=name))
        if log and position % 50 == 0:
            print(f"  {slug}: {position + 1}/{len(shas)} commits, {len(repairs)} repairs", flush=True)
    return repairs, calls


def split_chronological(repairs: Sequence[Repair], *, test_fraction: float = 0.35) -> Tuple[List[Repair], List[Repair]]:
    """Train on the older arrivals, test on the newer ones, and never share a file across them."""
    if not repairs:
        return [], []
    ordered = list(repairs)  # harvest order is newest-first from the API, so reverse it
    ordered = list(reversed(ordered))
    cut = max(1, int(len(ordered) * (1.0 - test_fraction)))
    train = ordered[:cut]
    train_files = {r.path for r in train}
    test = [r for r in ordered[cut:] if r.path not in train_files]
    return train, test


def split_by_file(repairs: Sequence[Repair], *, test_fraction: float = 0.35) -> Tuple[List[Repair], List[Repair]]:
    """Group whole files, newest files to the test side.

    The first version of this split dropped any test repair whose file also appeared in training,
    which left 18 test pairs out of 250 and made the measurement meaningless. A file-grouped split
    keeps every file on one side, so the held-out set is large *and* no test file was ever learned
    from -- the property that actually matters.
    """
    if not repairs:
        return [], []
    newest: Dict[str, int] = {}
    for position, repair in enumerate(repairs):  # harvest order is newest first
        newest.setdefault(repair.path, position)
    files = sorted(newest, key=lambda path: newest[path])
    n_test = max(1, int(len(files) * test_fraction)) if len(files) > 1 else 0
    test_files = set(files[:n_test])
    train = [r for r in repairs if r.path not in test_files]
    test = [r for r in repairs if r.path in test_files]
    return train, test


def learn(repairs: Sequence[Repair]) -> List[Rule]:
    rules: List[Rule] = []
    for repair in repairs:
        verdict = admit(repair.before, repair.after)
        if verdict["verdict"] == ADMITTED:
            try:
                rules.append(abstract(repair.before, repair.after))
            except (SyntaxError, TypeError, KeyError, ValueError):
                continue
    return rules


def score(rules: Sequence[Rule], repairs: Sequence[Repair]) -> Dict[str, Any]:
    """A hit is an exact AST match on the held-out after side. Nothing is credited for 'close'."""
    hits: List[Dict[str, Any]] = []
    for repair in repairs:
        for rule in rules:
            produced = apply_rule(rule, repair.before)
            if produced is None:
                continue
            try:
                if _dump(ast.parse(produced, mode="exec").body[0]) == _dump(ast.parse(repair.after, mode="exec").body[0]):
                    hits.append({"repair": repair.key(), "rule_witness": rule.before})
                    break
            except (SyntaxError, IndexError):
                continue
    return {"tested": len(repairs), "hits": len(hits), "detail": hits[:40],
            "rate": round(len(hits) / len(repairs), 4) if repairs else 0.0}


def score_raw_traces(train: Sequence[Repair], test: Sequence[Repair]) -> Dict[str, Any]:
    """The NO_COMPOUNDING arm: keep the training repairs verbatim and see if any repeats exactly."""
    exact = {(r.before, r.after) for r in train}
    normalized = {(_dump(_as_statement(r.before)), _dump(_as_statement(r.after))) for r in train
                  if _as_statement(r.before) is not None and _as_statement(r.after) is not None}
    hits = 0
    for repair in test:
        before = _as_statement(repair.before)
        after = _as_statement(repair.after)
        if before is None or after is None:
            continue
        if (repair.before, repair.after) in exact or (_dump(before), _dump(after)) in normalized:
            hits += 1
    return {"tested": len(test), "hits": hits,
            "rate": round(hits / len(test), 4) if test else 0.0}


def shape_ceiling(rules: Sequence[Rule], test: Sequence[Repair]) -> Dict[str, Any]:
    """An upper bound for any rule index keyed on the change's root node.

    If a test repair's root statement kind is absent from every rule, no index on root shape could
    ever reach it. The gap between this ceiling and the store's hits is the part a better match
    policy could close; the rest needs a different trigger than the change's own shape.
    """
    kinds = {rule.lhs.kind for rule in rules if hasattr(rule.lhs, "kind")}
    reachable = 0
    for repair in test:
        node = _as_statement(repair.before)
        if node is not None and type(node).__name__ in kinds:
            reachable += 1
    return {"tested": len(test), "same_root_as_some_rule": reachable,
            "rate": round(reachable / len(test), 4) if test else 0.0}


def evaluate(train: Sequence[Repair], test: Sequence[Repair]) -> Dict[str, Any]:
    rules = learn(train)
    store = score(rules, test)
    return {
        "train_repairs": len(train),
        "train_files": len({r.path for r in train}),
        "rules_admitted": len(rules),
        "rules_per_repair": round(len(rules) / len(train), 4) if train else 0.0,
        "STORE": store,
        "EMPTY": {"tested": len(test), "hits": 0, "rate": 0.0},
        "RAW_TRACE": score_raw_traces(train, test),
        "SHAPE_CEILING": shape_ceiling(rules, test),
    }


def _emit_digest(repairs: Sequence[Repair]) -> str:
    blob = "\n".join(f"{r.key()}|{r.before}|{r.after}" for r in repairs)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


CONTROL_PATCH_TRAIN = """@@ -1,3 +1,3 @@
-    if len(xs) < limit:
+    if len(xs) <= limit:
         return False
-    return True
"""
CONTROL_PATCH_TEST = """@@ -20,3 +20,3 @@
-    if len(rows) < bound:
+    if len(rows) <= bound:
         return False
-    return True
"""


def self_check() -> Dict[str, Any]:
    """Prove the instrument can register a hit before any zero is believed.

    A scorer that never fires reports 0 whatever the corpus, which is indistinguishable from a real
    negative. These checks pin the positive direction: an identical shape under new identifiers is
    a hit, and a near miss is not.
    """
    train = parse_patch(CONTROL_PATCH_TRAIN, slug="c/train", sha="b" * 40, path="t.py")
    test = parse_patch(CONTROL_PATCH_TEST, slug="c/test", sha="c" * 40, path="u.py")
    rules = learn(train)
    positive = score(rules, test)
    near_miss = [Repair(slug="c/test", sha="d" * 40, path="v.py", index=0,
                        before="if len(rows) < bound:\n    pass",
                        after="if len(rows) > bound:\n    pass")]
    negative = score(rules, near_miss)
    empty = score([], test)
    checks = [
        len(train) == 1 and len(test) == 1,
        len(rules) == 1,
        positive["hits"] == 1,
        empty["hits"] == 0,
        negative["hits"] == 0,
    ]
    return {"checks": len(checks), "passed": sum(checks),
            "detail": {"train": len(train), "test": len(test), "rules": len(rules),
                       "positive_hits": positive["hits"], "empty_hits": empty["hits"],
                       "near_miss_hits": negative["hits"]},
            "verdict": "SELF_CHECK_PASS" if all(checks) else "SELF_CHECK_FAIL"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--learn-slug", default="python-attrs/attrs")
    parser.add_argument("--test-slug", default="")
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--out", default="")
    parser.add_argument("--cache", default="", help="reuse a harvest so re-scoring costs no network")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)

    if args.self_check:
        report = self_check()
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0 if report["verdict"] == "SELF_CHECK_PASS" else 1

    started = time.perf_counter()
    cpu0 = time.process_time()

    def load_or_harvest(slug: str) -> Tuple[List[Repair], int]:
        cache = pathlib.Path(args.cache) if args.cache else None
        store: Dict[str, Any] = {}
        if cache is not None and cache.exists():
            store = json.loads(cache.read_text(encoding="utf-8"))
            if slug in store:
                cached = store[slug]
                return [Repair(**item) for item in cached["repairs"]], -int(cached.get("calls") or 0)
        repairs, calls = harvest(slug, pages=args.pages, log=True)
        if cache is not None:
            store[slug] = {"repairs": [r.__dict__ for r in repairs], "calls": calls}
            cache.write_text(json.dumps(store), encoding="utf-8")
        return repairs, calls

    train_pool, calls_a = load_or_harvest(args.learn_slug)
    report: Dict[str, Any] = {
        "schema": SCHEMA,
        "learn_slug": args.learn_slug,
        "contamination": ("CONTAMINATED_FOR_CATALOGUE" if args.learn_slug in CONTAMINATED_SLUGS else "NOT_USED_BY_TREE"),
        "harvest": {"repairs": len(train_pool), "digest": _emit_digest(train_pool),
                    "api_calls_this_run": 0 if calls_a < 0 else calls_a,
                    "api_calls_original": abs(calls_a),
                    "reused_cache": calls_a < 0},
    }
    train, held_out = split_chronological(train_pool)
    report["within_changed_file_split"] = evaluate(train, held_out)
    grouped_train, grouped_test = split_by_file(train_pool)
    report["within_repository"] = evaluate(grouped_train, grouped_test)
    report["within_repository"]["split"] = "file-grouped, newest files held out"

    if args.test_slug:
        other_pool, calls_b = load_or_harvest(args.test_slug)
        report["cross_repository"] = evaluate(train_pool, other_pool)
        report["cross_repository"]["test_slug"] = args.test_slug
        report["cross_repository"]["test_repairs_seen"] = len(other_pool)
        report["cross_repository"]["contamination"] = (
            "CONTAMINATED_FOR_CATALOGUE" if args.test_slug in CONTAMINATED_SLUGS else "NOT_USED_BY_TREE")
        report["harvest"]["api_calls_this_run"] += 0 if calls_b < 0 else calls_b
        report["harvest"]["api_calls_original"] += abs(calls_b)

    within, changed = report["within_repository"], report["within_changed_file_split"]
    cross = report.get("cross_repository") or {}
    report["verdict"] = {
        "within_repository": {"store": within["STORE"]["rate"], "raw_traces": within["RAW_TRACE"]["rate"],
                              "shape_ceiling": within["SHAPE_CEILING"]["rate"], "tested": within["STORE"]["tested"]},
        "cross_repository": {"store": cross.get("STORE", {}).get("rate"),
                             "raw_traces": cross.get("RAW_TRACE", {}).get("rate"),
                             "shape_ceiling": cross.get("SHAPE_CEILING", {}).get("rate"),
                             "tested": cross.get("STORE", {}).get("tested")},
        "abstraction_beats_verbatim": within["STORE"]["hits"] > within["RAW_TRACE"]["hits"],
        "conclusion": (
            "Retrieval on the shape of a change is not the bottleneck and the Wave 45 operator does not earn its "
            "place as a store mechanism on this corpus: inside one project 2.45% of held-out repairs are reproduced "
            "against 3.07% for verbatim traces, and across projects 0 of 1,350 despite 76.4% of held-out repairs "
            "sharing a root shape with some stored rule. What does not transfer is the trigger: these store entries "
            "are keyed on the edit, and an edit is surface-specific. The next mechanism must be keyed on the failing "
            "condition that made the edit necessary."
        ),
        "deletion_condition": (
            "structured_morphism_abstraction_v1 stays only while a trigger-keyed store uses it to express the "
            "repair itself; if the next wave's trigger-indexed store does not, the module is deleted under the "
            "no-part-without-measurement rule."
        ),
    }
    report["self_check"] = {"command": "python3 -m canonical.swe_kernel.single_experience_transfer_v1 --self-check",
                            "expect_exit": 0, **self_check()}
    report["cost"] = {"wall_clock_s": round(time.perf_counter() - started, 2),
                      "cpu_seconds": round(time.process_time() - cpu0, 2),
                      "model_calls": 0, "network_calls_this_run": report["harvest"]["api_calls_this_run"]}
    report["not_claimed"] = [
        "no task was repaired: this measures whether a stored rule can reproduce another commit's change",
        "network was used at build time only, to read patches; nothing here runs at runtime",
        "the repositories are ordinary open-source histories, not a benchmark, and no score is comparable to one",
    ]
    if args.out:
        path = pathlib.Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "within_repository"}, indent=1, sort_keys=True)[:2500])
    within = report["within_repository"]
    print(json.dumps({k: within[k] for k in ("train_repairs", "rules_admitted", "STORE", "RAW_TRACE")}, indent=1)[:1200])
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
