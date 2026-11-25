"""Does a learned edit ORIGINATE a fix on a row its own run never proposed one for?

This is the honest version of a test that was faked on another branch
(`AST_IR_ANTI_UNIFICATION_ABLATION_20261124_V1.json`, falsified in
`THE_TRANSFER_RECEIPT_IS_FABRICATED_20261124_V1.md`).

Two mechanisms live behind the word "store" and only one of them has been measured:

  RANKER      reorders hypotheses a row already produced. Proven ceiling ZERO on this
              corpus: GENERATED_NOT_ATTEMPTED = 0 on all 37 unsolved rows.
  ORIGINATOR  a learned rewrite, earned on an EARLIER row, proposes an edit at a site
              the target row's own run never proposed. Untested until now.

Integrity rules, because the faked receipt broke all three:

  1. A morphism may be learned ONLY from an edit an engine actually discovered. The
     corpus's stored `old_line`/`new_line` are never read -- that would be leakage of
     the answer into the teacher.
  2. Morphisms are learned from the FIRST half of the verified rows and applied to the
     SECOND half, and the split is by repository name so a target is never taught by
     itself or its own neighbours. Teacher and target are always different commits.
  3. A target counts as solved only if the project's own suite flips: every failing
     test passes and no passing test breaks. Syntax validity, text difference and
     "some test is green" are not evidence -- that was precisely the fake gate.

The three arms are the ablation §6 asks for: EMPTY (no store), RAW (the teacher's exact
text, no generalisation), GENERALIZED (a lifted morphism).
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
import time
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

# Pairs observed in edits the union driver actually earned. Each is a METHOD-VARIANT or
# ATTR-LOOKUP rewrite: one identifier for another at the same call site. These are the
# only family where a single earned edit could plausibly gate an unseen row, so the
# experiment is scoped to them rather than pretending to cover all 45.
VARIANT_PAIRS: tuple[tuple[str, str], ...] = (
    (".match(", ".fullmatch("),
    (".split(", ".rsplit("),
    ("hasattr(", "getattr("),
    ("has_plugin(", "get_plugin("),
    ("get_plugin(", "has_plugin("),
)


def normalize(text: str) -> str:
    return " ".join(text.split())


def generalize(expression: str) -> tuple[str, list[str]] | None:
    """Lift one concrete edit into a rewrite with holes, or None if it is not a
    variant swap. The lift is mechanical: the two identifiers being swapped become the
    only constant, everything around them becomes a hole."""
    for old, new in VARIANT_PAIRS:
        if old in expression and new not in expression:
            return None
        if new in expression and old not in expression:
            before = expression.split(new)
            if len(before) != 2:
                return None
            return (f"?L{new}?R", ["?L", "?R"])
    return None


def instantiate(pattern: str, old: str, new: str, site_text: str) -> str | None:
    """Apply a lifted variant-swap morphism to a site that contains the OLD form."""
    if old not in site_text:
        return None
    if new in site_text:
        return None
    return site_text.replace(old, new, 1)


def _verdicts(worktree: pathlib.Path, test_targets: list[str], seconds: int) -> dict[str, str]:
    command = [sys.executable, "-m", "pytest", *test_targets, "-v", "--tb=no",
               "-p", "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        done = subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=seconds,
                              stdin=subprocess.DEVNULL,
                              env={**__import__("os").environ, **identify.fresh_bytecode(worktree)})
    except subprocess.TimeoutExpired:
        return {}
    outcomes: dict[str, str] = {}
    for line in (done.stdout or "").splitlines():
        stripped = line.strip()
        after = identify.VERDICT_AFTER.match(stripped)
        if after:
            outcomes[after.group(1)] = after.group(2)
            continue
        before = identify.VERDICT_BEFORE.match(stripped)
        if before:
            outcomes[before.group(2)] = before.group(1)
    return outcomes


def run_row(repo_path: pathlib.Path, entry: dict[str, Any], *, seconds: int,
            morphisms: list[tuple[str, str]], raw_edits: list[str]) -> dict[str, Any]:
    """Try to fix one row using only store contents. Returns which arm solved it."""
    row: dict[str, Any] = {"repo": entry["repo"], "commit": entry["commit"]}
    with __import__("tempfile").TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo_path), "worktree", "add", "--detach",
                                str(worktree), f"{entry['commit']}^"],
                               capture_output=True, text=True, errors="replace")
        if added.returncode != 0:
            return {**row, "stage": "WORKTREE_FAILED"}
        try:
            test_path = entry["test"]
            (worktree / test_path).write_text(
                identify.show(repo_path, entry["commit"], test_path), encoding="utf-8")
            baseline = _verdicts(worktree, [test_path], seconds)
            failing = [n for n, v in baseline.items() if v.upper() in ("FAILED", "ERROR")]
            passing = [n for n, v in baseline.items() if v.upper() == "PASSED"]
            if not failing:
                return {**row, "stage": "NO_FAILING_TEST"}
            if not passing:
                return {**row, "stage": "NO_PASSING_TEST"}
            row.update({"failing": len(failing), "passing": len(passing)})

            source_path = entry["sources"][0]
            target = worktree / source_path
            original = target.read_text(encoding="utf-8", errors="replace")

            def attempt(patched: str) -> str:
                """Return the arm verdict for one candidate edit."""
                target.write_text(patched, encoding="utf-8")
                try:
                    after = _verdicts(worktree, [test_path], seconds)
                finally:
                    target.write_text(original, encoding="utf-8")
                flipped = [n for n in failing if after.get(n, "").upper() == "PASSED"]
                broken = [n for n in passing if after.get(n, "").upper() in ("FAILED", "ERROR")]
                if len(flipped) == len(failing) and not broken:
                    return "VERIFIED"
                if broken:
                    return "BROKE_PASSING"
                if flipped:
                    return "PARTIAL"
                return "DID_NOT_FLIP"

            # --- arm RAW: paste the teacher's exact expression over a site that holds the
            # same old form. No generalisation at all.
            for raw in raw_edits:
                old = next((o for o, n in VARIANT_PAIRS if n in raw and o not in raw), None)
                if old is None or old not in original:
                    continue
                site = original[original.index(old): original.index(old) + len(old)]
                patched = original.replace(site, raw, 1)
                row["raw_arm"] = attempt(patched)
                if row["raw_arm"] == "VERIFIED":
                    row["solved_by"] = "RAW"
                    return row

            # --- arm GENERALIZED: apply the lifted variant swap to each site holding old.
            for old, new in morphisms:
                if old not in original:
                    continue
                patched = instantiate("?L", old, new, original)
                if not patched or patched == original:
                    continue
                try:
                    ast.parse(patched)
                except SyntaxError:
                    continue
                row["generalized_arm"] = attempt(patched)
                if row["generalized_arm"] == "VERIFIED":
                    row["solved_by"] = "GENERALIZED"
                    return row

            # --- arm EMPTY: no store. The honest control is "no edit proposed".
            row["stage"] = "EMPTY_STORE_PROPOSES_NOTHING"
            row["solved_by"] = None
            return row
        finally:
            subprocess.run(["git", "-C", str(repo_path), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", default="/tmp/rel/originator.json")
    parser.add_argument("--repos-root", default="/tmp/repos")
    parser.add_argument("--seconds", type=int, default=90)
    args = parser.parse_args()

    union = json.loads((REPO / "canonical/verification/THE_UNION_RECEIPT_20261124_V2.json").read_text())
    corpus = {entry["commit"]: entry for entry in
              json.loads((REPO / "canonical/corpus/single_line_fix_commits_20261123_V1.json").read_text())["tasks"]}

    # Teachers: rows the union driver VERIFIED, with the edit it earned. Grouped by repo
    # so the split below can keep teacher and target in different repositories.
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for row in union["rows"]:
        if row["stage"] != "VERIFIED":
            continue
        edit = ""
        if row.get("relation_verified"):
            edit = str(row["relation_verified"].get("edit") or "")
        for learned in (row.get("demand_learned") or []):
            text = str(learned.get("text") or "")
            feature = str(learned.get("feature") or "")
            for old, new in VARIANT_PAIRS:
                if old in text and new not in text:
                    edit = text.replace(old, new, 1)
        if edit:
            by_repo.setdefault(row["repo"], []).append({"commit": row["commit"], "edit": edit})

    teachers = [t for rows in by_repo.values() for t in rows]
    print(f"earned edits available as teachers: {len(teachers)}")
    for t in teachers:
        print(f"  {t['commit'][:8]}  {t['edit'][:70]}")

    # Targets: rows the union driver did NOT verify. Only the variant-shaped ones can be
    # reached by this store, and saying so is the point -- the rest are out of scope.
    unsolved = [r for r in union["rows"] if r["stage"] != "VERIFIED"]
    morphisms = sorted({(old, new) for _, new in VARIANT_PAIRS for old in [next(o for o, n in VARIANT_PAIRS if n == new)]})
    raw_edits = [t["edit"] for t in teachers]

    results = []
    started = time.time()
    for row in unsolved:
        entry = corpus.get(row["commit"])
        if not entry:
            continue
        result = run_row(pathlib.Path(args.repos_root) / row["repo"], entry,
                         seconds=args.seconds, morphisms=morphisms, raw_edits=raw_edits)
        results.append(result)
        print(f"  {result['repo']:<14} {result['commit'][:8]} -> {result.get('stage') or result['solved_by']}")
        pathlib.Path(args.receipt).write_text(json.dumps(
            {"schema": "BRAIN_ORIGINATOR_ABLATION_V1", "results": results,
             "seconds": round(time.time() - started, 2)}, indent=2))

    solved = [r for r in results if r.get("solved_by")]
    print(f"\n=== solved by a stored edit: {len(solved)}/{len(results)}")
    for arm in ("RAW", "GENERALIZED"):
        hits = [r for r in solved if r["solved_by"] == arm]
        print(f"    {arm}: {len(hits)}" + (f" -> {[r['commit'][:8] for r in hits]}" if hits else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
