"""The repository is the seed corpus: harvest the artifact's own valid inputs, distil them by coverage, search.

THE QUESTION THIS ROUND ASKS FIRST
----------------------------------
Rounds 17 and 18 spent two mechanisms on the same 8 unpinned behavioural parts and pinned 2. Both engines were
fed the SAME seeds: the literal arguments of the ONE test file the fix touches -- for `tomli`, five one-character
strings such as `"v"` and `"."`. A parser cannot be entered through five characters. So before building a third
reachability mechanism, the cheapest possible explanation had to be tested:

    was the wall the mechanism, or the SEED?

The field says seeds dominate. OSS-Fuzz's own guidance is "start with existing test inputs: unit test inputs,
integration test data, or real-world examples ... verify coverage ... keep it minimal", and its 1.12-million-session
study found developer-provided seed corpora retain long-term effectiveness. FuzzWise (Dec 2025) measures a better
initial corpus finding 8 errors where a random one finds 1 at equal coverage. MoonLight (2019) shows distillation
by coverage is the right selection rule and that weighting by size usually wins.

WHAT THIS DOES
--------------
    harvest    string literals from the repository's own test files, and text data files under test/data/fixture
               directories -- the artifact's own valid documents, written by the project's authors
    distil     GREEDY SET COVER over lines of the target file: a candidate is kept only if it executes a line no
               kept seed executes. No model, no heuristic weight, no hand-picked rule -- the coverage is measured
    search     the distilled seeds are handed to BOTH existing engines unchanged (round 17's mutation search and
               round 18's operand walk) and the result is compared against the same engines fed the tiny seeds

WHAT IS DELIBERATELY NOT CLAIMED
--------------------------------
Harvesting is bounded: files over 64 KB, binary content, `.py` data files and vcs directories are skipped, and the
distilled corpus is capped. A part that no harvested document reaches is reported with both verdicts and with the
coverage the corpus achieved, so a failure names whether the seeds never entered the file or entered it and still
could not reach the part.
"""

from __future__ import annotations

import ast
import json
import subprocess
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import reach_the_changed_site_v1 as R  # noqa: E402
from canonical.swe_kernel import what_the_condition_wants_v1 as W  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

SCHEMA = "BRAIN_THE_REPOSITORY_IS_THE_SEED_CORPUS_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
MAX_SEEDS = 40
EXECUTIONS_PER_SEED = 20
EXECUTION_CAP = 600
CANDIDATE_CAP = 400
BATCH = 40
MAX_PARTS = 3
MAX_FILE_BYTES = 64 * 1024
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "build", "dist", ".tox", ".mypy_cache"}
TEXT_SUFFIXES = {".toml", ".txt", ".json", ".ini", ".cfg", ".conf", ".csv", ".yaml", ".yml", ".in", ".out",
                 ".md", ".rst", ".xml", ".html", ".sql", ".sh", ".dat", ".expected"}


def _is_test_path(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return name.startswith("test_") or name.endswith("_test.py") or "/tests/" in rel or "/test/" in rel


TRACED_SUITE = r"""
import os, sys
target = os.path.abspath(sys.argv[1]); testRel = sys.argv[2]
seen = set()
def trace(frame, event, arg):
    if event == "line" and os.path.abspath(frame.f_code.co_filename) == target:
        seen.add(frame.f_lineno)
    return trace
sys.settrace(trace)
import pytest
code = pytest.main([testRel, "-q", "--no-header", "-p", "no:cacheprovider"])
sys.settrace(None)
print("EXECUTED_LINES", sorted(seen))
"""


def executed_lines_by_the_suite(tree: pathlib.Path, source_rel: str, fixed: str, test_rel: str,
                               timeout_s: int = 600) -> set[int]:
    """Which lines of the fixed file the ORIGINAL test executes.

    This is the boundary of the input space, not a heuristic. Both engines feed arguments into the call sites the
    test already contains; a line the test never executes is reachable by no argument at all. Measuring it says
    which parts are an input problem and which are an ACTION problem -- a code path no test operation performs.
    """
    target = tree / source_rel
    original = target.read_bytes()
    try:
        target.write_text(fixed, encoding="utf-8")
        try:
            proc = subprocess.run([sys.executable, "-c", TRACED_SUITE, str(target), test_rel], cwd=str(tree),
                                  env=G._env_for(tree), capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return set()
    finally:
        target.write_bytes(original)
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith("EXECUTED_LINES"):
            try:
                return set(json.loads(line.split(" ", 1)[1]))
            except (ValueError, IndexError):
                return set()
    return set()


def harvest_documents(tree: pathlib.Path) -> list[dict[str, Any]]:
    """Every string the repository itself already uses as an input, with where it came from."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def offer(text: str, origin: str, prefer: int = 0) -> None:
        """Validity first, brevity second. The first version of this ranked `prefer - length`, which put one-line
        test fragments ahead of the project's real documents and cut the documents off at the candidate cap; the
        kept samples were `"v=['"` and `"a={"`. A parser is entered through documents, not fragments."""
        if not isinstance(text, str) or not (2 <= len(text) <= 2000) or text in seen:
            return
        if "\x00" in text:
            return
        seen.add(text)
        found.append({"text": text, "origin": origin, "rank": (prefer, -min(len(text), 400))})

    for path in sorted(tree.rglob("*")):
        if len(found) >= CANDIDATE_CAP * 3:
            break
        rel = str(path.relative_to(tree))
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        if path.suffix == ".py":
            if not _is_test_path(rel):
                continue
            try:
                module = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(module):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    offer(node.value, rel, prefer=3 if "\n" in node.value else 1)
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if not ("/tests/" in f"/{rel}" or "/test/" in f"/{rel}" or path.suffix == ".toml"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        offer(text, rel, prefer=5)                       # a whole data file: the project says it is an input
    found.sort(key=lambda item: (-item["rank"][0], item["rank"][1]))
    return found[:CANDIDATE_CAP]


def distil(tree: pathlib.Path, source_rel: str, call: Mapping[str, Any],
           documents: Sequence[Mapping[str, Any]], cap: int = MAX_SEEDS) -> tuple[list[str], dict[str, Any]]:
    """Greedy set cover over lines of the TARGET FILE: keep a document only if it executes a line none does."""
    target = str(tree / source_rel)
    covered: set[int] = set()
    kept: list[str] = []
    spent = 0
    candidates = [document["text"] for document in documents]
    for start in range(0, len(candidates), BATCH):
        if len(kept) >= cap:
            break
        chunk = candidates[start:start + BATCH]
        cases = [{"module": call["module"], "function": call["function"], "args": [text],
                  "kinds": ["raw"]} for text in chunk]
        results = W._batch(tree, target, 0, cases)
        spent += len(cases)
        for text, result in zip(chunk, results):
            lines = set(result.get("lines") or [])
            if lines - covered:
                kept.append(text)
                covered |= lines
                if len(kept) >= cap:
                    break
    return kept, {"candidates": len(candidates), "kept": len(kept), "executions": spent,
                  "lines_covered": len(covered)}


def calls_from(documents: Sequence[str], call: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The distilled documents as calls in the shape both engines already take."""
    out = []
    for text in documents:
        rest = [argument for argument in call["args"][1:]
                if isinstance(argument, (str, int, float, bool, list, dict, type(None)))]
        out.append({"module": call["module"], "function": call["function"], "args": [text] + rest})
    return out


def judge(tree: pathlib.Path, source_rel: str, test_rel: str, fixed: str, mutant: str, part: Mapping[str, Any],
          calls: Sequence[Mapping[str, Any]], budget: int | None = None) -> dict[str, Any]:
    """Both engines, unchanged, on one seed set. A budget is passed only when the seed set implies spending more:
    seeds are only cheap if the search is allowed to execute them."""
    extra = {} if budget is None else {"budget": budget}
    by_mutation = R.reach_part(tree, source_rel, test_rel, fixed, mutant, part, calls, **extra)
    by_operand = W.what_the_condition_wants(tree, source_rel, test_rel, fixed, mutant, part, calls, **extra)
    winner = by_operand if by_operand["state"] == W.PINNED else by_mutation
    return {"state": winner["state"], "by_mutation": by_mutation["state"], "by_operand": by_operand["state"],
            "assertion": winner.get("assertion")}


def audit_task(task: Mapping[str, Any], grammar: Sequence[Mapping[str, Any]], cap: int = MAX_PARTS) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    entry = next((g for g in grammar if g["sha"] == task["sha"] and g["source"] == source_rel), None)
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel}
    if entry is None:
        return {**row, "state": PINS.REFUSED_NO_GRAMMAR}
    fixed, defective = entry["repaired"], entry["defective"]
    if G.try_candidate(tree, source_rel, test_rel, defective)["passed"] or \
            not G.try_candidate(tree, source_rel, test_rel, fixed)["passed"]:
        return {**row, "state": R.REFUSED_CONTROL}
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") \
        if (tree / test_rel).is_file() else ""
    tiny = SYN.calls_from_the_test(test_source)
    row["tiny_seeds"] = len(tiny)
    executed = executed_lines_by_the_suite(tree, source_rel, fixed, test_rel)
    row["lines_the_suite_executes"] = len(executed)
    judged: list[dict[str, Any]] = []
    documents = harvest_documents(tree)
    row["documents"] = len(documents)
    distilled: list[str] = []
    distilled_once = False
    for part in PINS.hunks(defective, fixed):
        if len(judged) >= cap:
            break
        if not PINS.is_behavioural(fixed, part) or PINS.typing_only(fixed, part):
            continue
        mutant = PINS.revert(fixed, defective, part)
        if G.try_candidate(tree, source_rel, test_rel, mutant)["passed"] is False:
            continue                       # the suite already pins this part: nothing to search
        if not distilled_once and tiny:
            distilled, stats = distil(tree, source_rel, tiny[0], documents)
            distilled_once = True
        else:
            stats = {}
        # The proven seeds are never thrown away: distillation ADDS documents to the tests' own literals, because a
        # coverage-greedy corpus measured worse on its own (it dropped the small seeds that reach one error branch).
        enriched = (list(tiny) + (calls_from(distilled, tiny[0]) if distilled else [])) if tiny else []
        seen_args: set[str] = set()
        enriched = [call for call in enriched
                    if not (str(call["args"][0]) in seen_args or seen_args.add(str(call["args"][0])))]
        same = judge(tree, source_rel, test_rel, fixed, mutant, part, enriched) if enriched else \
            {"state": R.REFUSED_NO_SEED, "by_mutation": None, "by_operand": None}
        wide = judge(tree, source_rel, test_rel, fixed, mutant, part, enriched,
                     budget=min(EXECUTION_CAP, EXECUTIONS_PER_SEED * len(enriched))) if enriched else same
        baseline = judge(tree, source_rel, test_rel, fixed, mutant, part, tiny)
        changed = set(range(part["new"][0], part["new"][1] + 1))
        judged.append({"tiny": baseline, "seeded": same, "seeded_wide": wide, "corpus": stats,
                       "seeds": len(enriched), "documents": len(documents),
                       "the_suite_executes_the_change": bool(changed & executed),
                       "part_head": str(part.get("added") or "").strip()[:120] or "(removal)"})
    def pins(key: str) -> int:
        return sum(1 for item in judged if item[key]["state"] == R.PINNED)
    pinned_tiny, pinned_same, pinned_wide = pins("tiny"), pins("seeded"), pins("seeded_wide")
    return {**row, "parts": judged, "unpinned_parts": len(judged), "pinned_tiny": pinned_tiny,
            "pinned_same_budget": pinned_same, "pinned_wide_budget": pinned_wide,
            "state": R.PINNED if pinned_wide else (PINS.FULLY_PINNED if not judged else R.NOT_REACHED)}


def measure(tasks: Sequence[Mapping[str, Any]], grammar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [audit_task(task, grammar) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    parts = [item for row in rows for item in (row.get("parts") or [])]
    tiny = sum(1 for item in parts if item["tiny"]["state"] == R.PINNED)
    same = sum(1 for item in parts if item["seeded"]["state"] == R.PINNED)
    wide = sum(1 for item in parts if item["seeded_wide"]["state"] == R.PINNED)
    gained = sum(1 for item in parts if item["seeded_wide"]["state"] == R.PINNED and item["tiny"]["state"] != R.PINNED)
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {
            "tasks": len(rows), "states": states, "parts_audited": len(parts),
            "pinned_with_tiny_seeds": tiny, "pinned_with_the_corpus_same_budget": same,
            "pinned_with_the_corpus_wide_budget": wide, "gained_by_seeds": gained,
            "documents_harvested": sum((row.get("documents") or 0) for row in rows),
            "seeds_kept": sum((item.get("corpus") or {}).get("kept") or 0 for item in parts),
            "lines_covered_by_the_corpus": sum((item.get("corpus") or {}).get("lines_covered") or 0 for item in parts),
            "certified_share_before": 0.762,
            "parts_the_suite_never_executes": sum(1 for item in parts
                                                  if not item.get("the_suite_executes_the_change")),
            "unpinned_because_the_suite_never_executes": sum(1 for item in parts
                                                             if not item.get("the_suite_executes_the_change")
                                                             and item["tiny"]["state"] != R.PINNED),
            "reached_by_the_corpus": sum(1 for item in parts
                                         if item["seeded_wide"]["state"] == R.REACHED_NO_DIFF
                                         and item["tiny"]["state"] == R.NOT_REACHED),
            "certified_share_after": round((32 + gained) / 42, 3) if parts else None,
            "seeds_per_part": sum(item.get("seeds") or 0 for item in parts),
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [(row, item) for row in report["rows"] for item in (row.get("parts") or [])
           if item["seeded_wide"]["state"] == R.PINNED and item["tiny"]["state"] != R.PINNED]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} {row['sha'][:8]}: "
                       + str(item["seeded_wide"].get("assertion") or "").replace("\n", " ")[:150]
                       for row, item in won)
    return (f"{totals['tasks']} real fixes: {totals['parts_audited']} parts the suite accepts without. "
            f"Tests' own literals: {totals['pinned_with_tiny_seeds']} pinned. Repository corpus, same budget: "
            f"{totals['pinned_with_the_corpus_same_budget']}. Repository corpus, budget scaled to the seeds: "
            f"{totals['pinned_with_the_corpus_wide_budget']}, {totals['gained_by_seeds']} gained. Harvested "
            f"{totals['documents_harvested']} documents, kept {totals['seeds_kept']} seeds covering "
            f"{totals['lines_covered_by_the_corpus']} lines. Of the {totals['parts_audited']} parts, "
            f"{totals['parts_the_suite_never_executes']} are lines the ORIGINAL suite never executes in the fixed "
            f"code -- no argument to its call sites can reach them. Certified share {totals['certified_share_before']} -> "
            f"{totals['certified_share_after']}." + (f" {detail}" if detail else ""))


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--hist", type=pathlib.Path, default=pathlib.Path("/tmp/hist"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/histwork"))
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args(argv)
    from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE
    tasks = SHAPE.prepare_corpus(args.manifest, args.hist, args.work, limit=args.limit)
    grammar = json.loads(args.manifest.read_text(encoding="utf-8"))["grammar"]
    report = measure(tasks, grammar)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
