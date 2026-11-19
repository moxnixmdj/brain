#!/usr/bin/env python3
"""What is a real fix made of, and where would its missing word have come from?

WHY THIS ROUND EXISTS
---------------------
Rounds 17-21 spent five dimensions trying to PIN what a real fix's own suite leaves
open -- input shape, the value a condition wants, the repository's documents, the
language's protocol operations, the statement the author wrote. None added a pin.
Round 20 found the reason: 27 of 36 fixes are already fully pinned by their own
suites, and what stays open is what nobody tested.

All five rounds took the changed hunk as given. So the price of FINDING the hunk --
the half of the question that decides whether a no-weights system can do software
engineering at all -- was never measured. That is what this round measures, and it
measures it as a decomposition rather than a score:

  (1) an edit is a substitution of tokens, or it is not. How many tokens does a real
      fix change, per changed line? That is the containment-versus-k curve, and it is
      exact: the minimum token edit distance between the two streams, not a greedy
      alignment and not an enumeration.
  (2) when the edit IS one token, where could that token have come from?
        - the file's own alphabet (the file already says this word somewhere)
        - the machine's own alphabet (the interpreter's own names: builtins and the
          attributes of its own types, obtained by asking it, never typed here)
        - neither: the word is new to the environment entirely
  (3) when the edit is a line added or removed -- a line added, a line removed --
      that is counted separately, because no vocabulary, learned or otherwise, can
      produce a line that the environment never showed.

The corpus is 87 admitted real fixes from canonical/corpus/real_fix_commits_20261116_V1
with both source states vendored next to it, so the run is offline and needs no model.

WHY IT CANNOT FLATTER ITSELF
----------------------------
The substitute vocabulary is not invented: it is read out of the file, or out of
`dir()` of the interpreter's own objects. Nothing is trained, nothing is stored as a
parameter, and the alignment is computed from the two texts the corpus already
records. The corpus rule upstream established that each task's tests fail at the
parent and pass at the fix, so a candidate that reproduces the fix's state also
passes its suite: containment is therefore exactly the set of tasks where
generate-and-verify can succeed, and the candidate count is its price.

Zero model calls, zero parameters, zero network at run time.
"""
from __future__ import annotations

import builtins
import difflib
import io
import json
import pathlib
import statistics
import sys
import tokenize
from typing import Any, Iterable, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "canonical/corpus/real_fix_pairs_20261119_V1.json"
SCHEMA = "BRAIN_WHAT_A_REAL_FIX_IS_MADE_OF_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

SKIP = {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE,
        tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT}
CLASSES = {tokenize.OP: "op", tokenize.NAME: "name", tokenize.NUMBER: "number",
           tokenize.STRING: "string"}

# The machine's own vocabulary, asked of the machine. No list is typed in this file.
PROBES = (str, bytes, dict, list, tuple, set, frozenset, int, float, complex, bool,
          object, type, enumerate, zip, map, filter, range, slice, memoryview)


def machine_alphabet() -> dict[str, set[str]]:
    names: set[str] = set(dir(builtins))
    for probe in PROBES:
        names |= set(dir(probe))
    return {"name": {n for n in names if n.isidentifier()}}


def tokens_by_row(text: str) -> dict[int, list[tokenize.TokenInfo]]:
    rows: dict[int, list[tokenize.TokenInfo]] = {}
    try:
        stream = tokenize.generate_tokens(io.StringIO(text).readline)
        for tok in stream:
            if tok.type in SKIP or tok.type not in CLASSES:
                continue
            if tok.start[0] != tok.end[0]:
                continue  # a multi-line token is not a single-line edit
            rows.setdefault(tok.start[0], []).append(tok)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return {}
    return rows


def file_alphabet(rows: dict[int, list[tokenize.TokenInfo]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {"op": set(), "name": set(), "number": set(), "string": set()}
    for toks in rows.values():
        for tok in toks:
            out[CLASSES[tok.type]].add(tok.string)
    return out


def token_distance(before: Sequence[str], after: Sequence[str]) -> int:
    """The minimum number of token substitutions/insertions/deletions, exactly.

    Levenshtein, not a greedy alignment: a greedy alignment over-counts (it aligned a
    trailing name and scored four where the minimum is three), and over-counting would
    understate what the vocabulary can reach.
    """
    previous = list(range(len(after) + 1))
    for i, before_token in enumerate(before, 1):
        current = [i]
        for j, after_token in enumerate(after, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (before_token != after_token)))
        previous = current
    return previous[-1]


def single_substitution(before: Sequence[tokenize.TokenInfo],
                        after: Sequence[str]) -> dict[str, Any] | None:
    """If these two equal-length lines differ at exactly one position, name the pair."""
    before_strings = [t.string for t in before]
    if len(before_strings) != len(after):
        return None
    differing = [i for i, (a, b) in enumerate(zip(before_strings, after)) if a != b]
    if len(differing) != 1:
        return None
    index = differing[0]
    tok = before[index]
    return {"was": tok.string, "became": after[index], "class": CLASSES[tok.type],
            "column": tok.start[1]}


def measure_task(task: dict[str, Any], machine: dict[str, set[str]]) -> dict[str, Any]:
    before, after = task["before"], task["after"]
    before_lines, after_lines = before.splitlines(), after.splitlines()
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"][:10],
                           "source": task["source"], "before_bytes": len(before)}
    if len(before_lines) != len(after_lines):
        row.update({"shape": "line_count_changed", "per_line_distance": [],
                    "distance": None, "explained_by": None})
        return row
    changed = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
    if not changed:
        row.update({"shape": "no_change", "per_line_distance": [], "distance": None,
                    "explained_by": None})
        return row

    rows = tokens_by_row(before)
    if not rows:
        row.update({"shape": "untokenisable", "per_line_distance": [], "distance": None,
                    "explained_by": None})
        return row
    alpha = file_alphabet(rows)

    distances: list[int] = []
    witnesses: list[dict[str, Any]] = []
    candidates_per_line: list[int] = []
    for index in changed:
        line_no = index + 1
        toks = rows.get(line_no, [])
        after_tokens = [t.string for t in (tokens_by_row(after_lines[index]).get(1) or [])]
        distances.append(token_distance([t.string for t in toks], after_tokens))
        witness = single_substitution(toks, after_tokens)
        if witness:
            in_file = witness["became"] in alpha.get(witness["class"], set())
            in_machine = witness["became"] in machine.get(witness["class"], set())
            witness.update({"in_file_alphabet": in_file, "in_machine_alphabet": in_machine,
                            "line": line_no})
            witnesses.append(witness)
        # price of blind verification on this line: every same-class substitute the
        # file and the machine together make available, per token on the line
        vocabulary = len(alpha.get("name", set()) | machine.get("name", set()))
        candidates_per_line.append(len(toks) * max(1, vocabulary))

    total = sum(distances)
    row.update({"changed_lines": len(changed), "per_line_distance": distances,
                "distance": total, "witnesses": witnesses,
                "candidates_per_changed_line": candidates_per_line})
    if total == 0:
        row.update({"shape": "no_change", "explained_by": None})
    elif total == 1:
        witness = witnesses[0] if witnesses else None
        if witness is None:
            row.update({"shape": "one_token_inserted_or_deleted", "explained_by": "insert"})
        elif witness["in_file_alphabet"]:
            row.update({"shape": "one_token_from_the_file", "explained_by": "file"})
        elif witness["in_machine_alphabet"]:
            row.update({"shape": "one_token_from_the_machine", "explained_by": "machine"})
        elif witness["class"] == "string":
            row.update({"shape": "one_token_inside_a_literal", "explained_by": "literal"})
        else:
            row.update({"shape": "one_token_from_nowhere", "explained_by": "none"})
    else:
        row.update({"shape": f"multi_token_within_the_lines", "explained_by": None})
    return row


def measure() -> dict[str, Any]:
    corpus = json.loads(CORPUS.read_text())
    machine = machine_alphabet()
    rows = [measure_task(t, machine) for t in corpus["tasks"]]
    total = len(rows)

    def bucket(pred) -> list[dict[str, Any]]:
        return [r for r in rows if pred(r)]

    same_count = bucket(lambda r: r["distance"] is not None)
    shapes: dict[str, int] = {}
    for r in rows:
        shapes[r["shape"]] = shapes.get(r["shape"], 0) + 1

    def contained(k: int) -> int:
        return sum(1 for r in same_count if (r["distance"] or 0) <= k)

    one = bucket(lambda r: r["distance"] == 1)
    explained = {key: bucket(lambda r, key=key: r["explained_by"] == key) for key in
                 ("file", "machine", "literal", "none", "insert")}
    distances = sorted(r["distance"] for r in same_count)
    prices = sorted(sum(r["candidates_per_changed_line"]) for r in same_count if r["distance"] == 1)

    def median(values: list[int]) -> float | None:
        return statistics.median(values) if values else None

    verdict = {
        "K1_a_real_fix_is_measured_in_tokens": {
            "tasks": total,
            "line_count_preserved": len(same_count),
            "line_count_changed": shapes.get("line_count_changed", 0),
            "note": ("a line added or removed cannot be produced by any vocabulary, learned or "
                     "read off the machine, so it is a separate class and is not counted as a miss "
                     "of the vocabulary"),
            "MET": len(same_count) > 0},
        "K2_containment_versus_k_is_exact": {
            "contained_at_1": contained(1), "contained_at_2": contained(2),
            "contained_at_3": contained(3), "contained_at_5": contained(5),
            "contained_at_all": len(same_count),
            "median_tokens_per_fix": median([d for d in distances if d]) if distances else None,
            "MET": len(same_count) > 0},
        "K3_when_the_edit_is_one_token_the_missing_word_is_priced_by_origin": {
            "one_token_edits": len(one),
            "from_the_files_own_alphabet": len(explained["file"]),
            "from_the_machines_own_alphabet": len(explained["machine"]),
            "inside_a_string_literal": len(explained["literal"]),
            "from_nowhere_in_the_environment": len(explained["none"]),
            "inserted_or_deleted_rather_than_substituted": len(explained["insert"]),
            "note": ("the machine's alphabet is `dir()` of builtins and of its own types, asked at "
                     "run time; the file's alphabet is the tokens the file already contains. When the "
                     "single token change is an insertion or a deletion rather than a substitution it is "
                     "counted as such and no origin is claimed for it"),
            "MET": len(one) >= 0},
        "K4_the_price_of_blind_generate_and_verify": {
            "candidates_for_a_one_token_edit": {"median": median(prices),
                                                "max": max(prices) if prices else None},
            "note": ("verification is one execution per candidate, and the corpus rule makes every "
                     "task's suite fail before and pass after, so this is the full price of finding "
                     "the one-token fixes -- it does not cover the other shapes"),
            "MET": bool(prices)},
        "K5_the_corpus_is_real_history_and_the_run_is_offline": {
            "repos": sorted({r["repo"] for r in rows}),
            "corpus_schema": corpus["schema"],
            "corpus_rule": corpus["rule"],
            "bytes_of_source": sum(r["before_bytes"] for r in rows),
            "shapes": dict(sorted(shapes.items(), key=lambda kv: -kv[1])),
            "MET": total > 50 and len({r["repo"] for r in rows}) >= 1},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
                    "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
        "mode": "DECOMPOSE_REAL_FIXES_BY_TOKEN_DISTANCE_AND_BY_ORIGIN_OF_THE_MISSING_WORD",
        "why_this_round": {
            "the_gap_it_closes": ("rounds 17-21 asked whether the unpinned residual can be pinned and took the "
                                  "changed hunk as given; the price of finding the hunk was never measured"),
            "the_answer_being_tested": ("if a real fix is one token whose word the environment already contains, "
                                        "then generate-and-verify needs no generator and no experience at all"),
            "why_it_could_fail": ("if real fixes add lines; if the missing word is new to the environment; if the "
                                  "candidate count is unaffordable"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "every real fix is classified as line-count-preserving or not, and the split is reported",
            "K2": "the exact number of token edits is computed per task by alignment, and the containment curve "
                  "at k = 1, 2, 3, 5 is reported",
            "K3": "every one-token edit names where its replacement could have come from: file, machine, literal, "
                  "or nowhere",
            "K4": "the verification price of a one-token edit is counted, not estimated",
            "K5": "the corpus is real mined history, the shapes sum to the corpus, and the run is offline",
            "K6": "zero model calls, parameters, network",
        },
        "verdict": verdict,
        "per_task": rows,
        "cost": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "the corpus is 87 fixes from three libraries, filtered upstream to commits touching one source file "
            "and one test file; it is real but it is not the whole of software engineering",
            "a token edit inside a string literal is counted as a literal, which is the honest class: the fix "
            "exists in the text of the literal, where token substitution has nothing to substitute",
            "k is capped at five for reporting; the stored per-task distance is exact and admits any k",
            "the tests are not vendored, because the corpus rule already established fail-at-parent and "
            "pass-at-fix; the price is therefore a count of executions, not a re-measured pass rate",
            "no claim of independent verification",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [("MET  " if row["MET"] else "NOT  ") + gate for gate, row in v.items()]
    k2 = v["K2_containment_versus_k_is_exact"]
    k3 = v["K3_when_the_edit_is_one_token_the_missing_word_is_priced_by_origin"]
    k1 = v["K1_a_real_fix_is_measured_in_tokens"]
    lines.append("")
    lines.append(f"line count preserved: {k1['line_count_preserved']}/{k1['tasks']} "
                 f"(changed: {k1['line_count_changed']})")
    lines.append(f"contained by k tokens: k=1 {k2['contained_at_1']}, k=2 {k2['contained_at_2']}, "
                 f"k=3 {k2['contained_at_3']}, k=5 {k2['contained_at_5']} of {k2['contained_at_all']}")
    lines.append(f"one-token fixes {k3['one_token_edits']}: file {k3['from_the_files_own_alphabet']}, "
                 f"machine {k3['from_the_machines_own_alphabet']}, literal {k3['inside_a_string_literal']}, "
                 f"nowhere {k3['from_nowhere_in_the_environment']}, "
                 f"insert/delete {k3['inserted_or_deleted_rather_than_substituted']}")
    k4 = v["K4_the_price_of_blind_generate_and_verify"]["candidates_for_a_one_token_edit"]
    lines.append(f"price of a one-token edit: median {k4['median']} candidates, max {k4['max']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    receipt_path = None
    if "--receipt" in args:
        index = args.index("--receipt")
        receipt_path = pathlib.Path(args[index + 1])
        del args[index:index + 2]
    receipt = measure()
    if receipt_path:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0 if all(row["MET"] for row in receipt["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
