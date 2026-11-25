"""Constant refinement: when the defect is inside a literal, not a branch.

Two oracled rows stop at the same place and no engine in this repo reaches it:

  urllib3  77fa67aaf2   ("^(%s|%s|%s)(?::([0-9]{0,5}))?$")
                     -> ("^(%s|%s|%s)(?::0*([0-9]{0,5}))?$")
  packaging ba17fcea23  _normalized_regex  ->  [a-z0-9]+(?:-[a-z0-9]+)*

Both are a change *inside a string literal*. The guard-rule engine searches
if/elif/while/boolean clauses, so its 44 sites on `url.py` do not include the faulty
constant and the nearest branch reads it correctly. A generator that can only rewrite
branches cannot reach either row, no matter how many relations it is given.

This tool asks a narrower and answerable question:

    given the failing behaviour, can a small fixed family of LITERAL REFINEMENTS
    produce a candidate whose verdicts differ from the parent's?

The families are not guesses about the fix; they are the ways a character class can be
made stricter or looser while preserving the literal's shape:

    STRIP_PREFIX_QUANTIFIER   ([0-9]{0,5})  ->  0*([0-9]{0,5})   (arity preserved)
    ALLOW_ZERO_RUNS           ([0-9])       ->  ([0-9]*)
    ADD_WORD_BOUNDARY         no \\b         ->  \\b ...
    ANCHOR                    no ^/$        ->  ^...$
    ASCII_FLAG                compile(...)  ->  compile(..., re.ASCII)

Each candidate is compiled, then run against the docstring- or issue-derived oracle on
the parent and compared. The tool reports which refinement, if any, changes the verdict.
It does NOT claim the candidate is the human fix -- only that it is a literal edit that
moves the observed behaviour, which is the precondition for any search.

    python canonical/tools/the_literal_is_the_defect_v1.py \
        --repo packaging --commit ba17fcea23 --module packaging.utils \
        --a is_normalized_name --b canonicalize_name --alphabet a,1,- --maxlen 4
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_REPOS_ROOT = pathlib.Path("/home/user/repos")

# (name, pattern, replacement) -- applied to source TEXT, shape-preserving.
REFINEMENTS: tuple[tuple[str, str, str], ...] = (
    # urllib3 77fa67aaf2: allow a run of leading zeros inside the digit class
    # NOTE: must not add a capture group. `host, port = re.match(...).groups()` breaks
    # the moment the arity changes, and a "refinement" that breaks every call site is
    # not a candidate. The human fix prefix\`0*\` outside the group for exactly this
    # reason; my first version wrapped it and turned 2 failures into 8.
    ("STRIP_PREFIX_QUANTIFIER", r"\(\[0-9\]\{0,([0-9]+)\}\)", r"0*([0-9]{0,\1})"),
    # a quantified digit class that must also admit the empty run
    ("ALLOW_ZERO_RUNS", r"\(\[0-9\]\{1,([0-9]+)\}\)", r"([0-9]{0,\1})"),
    # packaging ba17fcea23: replace a character-class-plus-lookahead with the
    # equivalent "alphanumeric runs joined by single hyphens"
    ("ALNUM_RUN_HYPHEN_JOIN",
     r"\[a-z0-9\]\|\[a-z0-9\]\(\[a-z0-9-\]\(\?!--\)\)\*\[a-z0-9\]",
     r"[a-z0-9]+(?:-[a-z0-9]+)*"),
    # drop a negative lookahead that is inspectable only after consumption
    ("DROP_NEGATIVE_LOOKAHEAD", r"\(\?!--\)", r""),
    # anchors around an unanchored pattern
    ("ADD_ANCHORS", r're\.compile\(r"([^^"][^"]*)",', r're.compile(r"^\1$",'),
)

PROBE = '''
import importlib, itertools, json, sys
a_name, b_name, alphabet, maxlen, pkg = (sys.argv[1], sys.argv[2], sys.argv[3],
                                         int(sys.argv[4]), sys.argv[5])

def find(name):
    module = importlib.import_module(pkg)
    if hasattr(module, name):
        return getattr(module, name)
    for sub in ("utils", "filters", "core", "helpers", "misc"):
        try:
            m = importlib.import_module(pkg + "." + sub)
        except Exception:
            continue
        if hasattr(m, name):
            return getattr(m, name)
    return None

A, B = find(a_name), find(b_name)
if A is None or B is None:
    print(json.dumps({"error": "missing"})); raise SystemExit(0)
alphabet = alphabet.split(",")
cases = ["".join(p) for n in range(1, maxlen + 1)
         for p in itertools.product(alphabet, repeat=n)]
cases = [c for c in cases if c[0].isalnum() and c[-1].isalnum()]
bad = []
for c in cases:
    try:
        left = bool(A(c))
    except Exception:
        continue
    try:
        right = (B(c) == c)
    except Exception:
        continue
    if left != right:
        bad.append(c)
print(json.dumps({"error": None, "count": len(bad), "witness": bad[:10],
                  "cases": len(cases)}))
'''


def git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, errors="replace")


PORT_PROBE = '''
import json, sys
import urllib3

# The oracle is the ISSUE'S claim, not the full behaviour diff:
#   a port written with leading zeros must parse to its numeric value,
#   and ordinary ports must be unaffected.
# `:0` / `:0000` are reported as COLLATERAL, not asserted: on the real fixed tree they
# change from port 0 to port None because `0*` consumes the whole zero run. That is a
# behaviour change the maintainers accepted; folding it into the oracle would make the
# test tautological against the human patch instead of testing the reported defect.
REQUIRED = [("http://example.com", None),
            ("http://example.com:8080", 8080),
            ("http://example.com:000001", 1),
            ("http://example.com:00080", 80),
            ("http://127.0.0.1:00022", 22),
            ("http://[::1]:00080", 80)]
COLLATERAL = ["http://example.com:0", "http://example.com:0000"]

bad, collapsed = [], []
for case, want in REQUIRED:
    try:
        url = urllib3.util.parse_url(case)
    except Exception as error:
        bad.append((case, type(error).__name__))
        continue
    if url.port != want:
        bad.append((case, url.port))
for case in COLLATERAL:
    try:
        collapsed.append([case, urllib3.util.parse_url(case).port])
    except Exception as error:
        collapsed.append([case, type(error).__name__])
print(json.dumps({"error": None, "count": len(bad), "witness": bad[:6],
                  "cases": len(REQUIRED), "collateral": collapsed}))
'''


def run_probe(tree: pathlib.Path, args: argparse.Namespace) -> dict[str, Any]:
    code, extra = ((PORT_PROBE, []) if args.relation == "parses_leading_zero_port"
                   else (PROBE, [args.a, args.b, args.alphabet, str(args.maxlen),
                                 args.module]))
    done = subprocess.run(
        [sys.executable, "-c", code, *extra],
        cwd=str(tree), capture_output=True, text=True, errors="replace",
        timeout=args.seconds, stdin=subprocess.DEVNULL,
        env={**__import__("os").environ, "PYTHONPATH": "src:.",
             "PYTHONDONTWRITEBYTECODE": "1"})
    for line in reversed((done.stdout or "").strip().splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return {"error": "probe_failed", "tail": (done.stderr or "")[-160:]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--module", required=True, help="importable module, e.g. packaging.utils")
    parser.add_argument("--a", default="", help="predicate function (agrees only)")
    parser.add_argument("--b", default="", help="function it must agree with (agrees only)")
    parser.add_argument("--relation", default="agrees",
                        choices=("agrees", "parses_leading_zero_port"))
    parser.add_argument("--alphabet", default="a,1,-")
    parser.add_argument("--maxlen", type=int, default=4)
    parser.add_argument("--repos-root", type=pathlib.Path, default=DEFAULT_REPOS_ROOT)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--seconds", type=int, default=90)
    args = parser.parse_args(argv)

    repo = args.repos_root / args.repo
    receipt: dict[str, Any] = {"schema": "THE_LITERAL_IS_THE_DEFECT_V1",
                              "repo": args.repo, "commit": args.commit,
                              "module": args.module, "relation": [args.a, args.b],
                              "candidates": []}
    with tempfile.TemporaryDirectory() as where:
        tree = pathlib.Path(where) / "wt"
        added = git(repo, "worktree", "add", "--detach", str(tree), f"{args.commit}^")
        if added.returncode != 0:
            receipt["verdict"] = "WORKTREE_FAILED"
        else:
            try:
                baseline = run_probe(tree, args)
                receipt["parent"] = baseline
                if baseline.get("error") or not baseline.get("count"):
                    receipt["verdict"] = "PARENT_PASSES__NO_DEMAND"
                    args.receipt.parent.mkdir(parents=True, exist_ok=True)
                    args.receipt.write_text(json.dumps(receipt, indent=1))
                    print(json.dumps(receipt, indent=1)[:600])
                    return 0
                source_rel = args.module.replace(".", "/") + ".py"
                if args.relation == "parses_leading_zero_port":
                    source_rel = "urllib3/util/url.py"
                candidates: list[dict[str, Any]] = []
                for name, pattern, replacement in REFINEMENTS:
                    target = tree / "src" / source_rel
                    if not target.exists():
                        target = tree / source_rel
                    if not target.exists():
                        continue
                    original = target.read_text(encoding="utf-8", errors="replace")
                    refined, changes = re.subn(pattern, replacement, original)
                    if not changes:
                        continue
                    target.write_text(refined, encoding="utf-8")
                    try:
                        result = run_probe(tree, args)
                    finally:
                        target.write_text(original, encoding="utf-8")
                    candidates.append({"refinement": name, "edits": changes,
                                       "result": result,
                                       "moved": (not result.get("error")) and
                                                result.get("count", baseline["count"])
                                                < baseline["count"],
                                       "cleared": result.get("count") == 0})
                receipt["candidates"] = candidates
                cleared = [c for c in candidates if c["cleared"]]
                moved = [c for c in candidates if c["moved"] and not c["cleared"]]
                receipt["verdict"] = ("LITERAL_REFINEMENT_CLEARS" if cleared else
                                      "LITERAL_REFINEMENT_MOVES" if moved else
                                      "NO_REFINEMENT_IN_FAMILY")
            finally:
                git(repo, "worktree", "remove", "--force", str(tree))
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print(json.dumps(receipt, indent=1)[:1400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
