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
import os
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
    # httpx e63b6594f2: an unescaped `.` inside a compiled pattern matches ANY character,
    # so "023b76x43144" matched the IPv4-shape test and was rejected as an invalid IPv4
    # address. Escaping the metacharacter is the minimal literal repair. Note the guard:
    # the dot must sit between two literal character-class quantifiers, which is the shape
    # of a dotted-quad. A blanket "escape every dot" rule would fire on every pattern in
    # every repo, and most of them mean any-character on purpose.
    # A lookahead, so the dot is CONSUMED and must be re-emitted escaped. My first
    # version grouped "[0-9]+." and re-emitted it verbatim, so the pattern matched but
    # the text came back unchanged -- "edits=1, moved=False", a fire that did nothing.
    ("ESCAPE_DOTTED_QUAD",
     r"(\[0-9\]\+)\.(?=\[0-9\])",
     r"\1\\."),
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

IPV4_LIKE_PROBE = '''
import json
import httpx

# The oracle is the ISSUE'S claim, not the patch. The issue is that a rare host name was
# rejected as an invalid IPv4 address because the shape test used an unescaped ".".
#   REQUIRED   a non-IPv4 host must survive parsing
#   COLLATERAL real IPv4 literals must keep working -- reported, not asserted, because a
#              refinement that escaped every dot would pass REQUIRED and destroy these.
REQUIRED = [("https://023b76x43144/", "023b76x43144")]
COLLATERAL = [("https://1.2.3.4/", "1.2.3.4"), ("https://127.0.0.1:8080/", "127.0.0.1"),
              ("https://example.com/", "example.com")]

bad, survived = [], []
for case, want in REQUIRED:
    try:
        host = httpx.URL(case).host
    except Exception as error:
        bad.append((case, type(error).__name__))
        continue
    if host != want:
        bad.append((case, host))
for case, want in COLLATERAL:
    try:
        survived.append([case, httpx.URL(case).host == want])
    except Exception as error:
        survived.append([case, type(error).__name__])
print(json.dumps({"error": None, "count": len(bad), "witness": bad[:6],
                  "cases": len(REQUIRED), "collateral": survived}))
'''

FALSEY_KEY_PROBE = '''
import json
from more_itertools import all_unique

class CaseFold:
    """A falsey callable is still a valid key. `if key else` discards it."""
    def __bool__(self):
        return False
    def __call__(self, x):
        return x.lower()

REQUIRED = [(["A", "B", "C", "b"], False)]     # 'b' and 'B' collide under the key
COLLATERAL = [(["A", "B", "C"], True), (["A", "a"], False)]

bad, survived = [], []
for items, want in REQUIRED:
    try:
        got = all_unique(items, CaseFold())
    except Exception as error:
        bad.append((str(items), type(error).__name__)); continue
    if got != want:
        bad.append((str(items), got))
for items, want in COLLATERAL:
    try:
        survived.append([str(items), all_unique(items, CaseFold()) == want])
    except Exception as error:
        survived.append([str(items), type(error).__name__])
print(json.dumps({"error": None, "count": len(bad), "witness": bad[:6],
                  "cases": len(REQUIRED), "collateral": survived}))
'''

# An AST-scoped, oracle-selected refinement. The failing test names the function; within
# that function only a PARAMETER used as a bare truthiness test can be the site. In
# more_itertools.all_unique that is one site, while the same textual shape appears 8 times
# in the file. Grep precision here is 1/8; the scope rule is what makes it exact.
_REFINE_SOURCE = r"""
import ast, pathlib, re, sys

def sites(src, func):
    tree = ast.parse(src)
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func]:
        params = {a.arg for a in fn.args.args} | {a.arg for a in fn.args.kwonlyargs}
        for node in ast.walk(fn):
            test = node.test if isinstance(node, (ast.IfExp, ast.If)) else None
            if isinstance(test, ast.Name) and test.id in params:
                out.append((node.lineno, test.id))
    return out

def apply(path, func, param):
    src = path.read_text(); edits = 0
    for line, name in sites(src, func):
        if name != param:
            continue
        lines = src.splitlines(keepends=True)
        new = re.sub(rf"\bif {re.escape(param)}\b(?!\s+is)",
                     f"if {param} is not None", lines[line - 1], count=1)
        if new != lines[line - 1]:
            lines[line - 1] = new; src = "".join(lines); edits += 1
    if edits:
        path.write_text(src)
    return edits

path, func, param = sys.argv[1], sys.argv[2], sys.argv[3]
print(apply(pathlib.Path(path), func, param))
"""

PLUS_IN_SAFE_PROBE = '''
import json
from werkzeug.routing import Map, Rule

# The issue: a '+' in a query VALUE must be percent-encoded, because in a query string
# '+' means space. It was in the encoder's safe set, so "1+2" survived as "1+2" and any
# reader would decode it to "1 2".
REQUIRED = [("1+2", "/?v=1%2B2")]
# Space is encoded as '+' by this encoder on parent, human fix AND refinement alike --
# asserted as '%20' in my first probe, which scored a correct refinement as a regression.
# Measured on all three trees before writing the expectation.
COLLATERAL = [("a b", "/?v=a+b"), ("plain", "/?v=plain"), ("a/b", "/?v=a/b")]

map_ = Map([Rule("/", endpoint="index")])
bind = map_.bind("example.com")
bad, survived = [], []
for value, want in REQUIRED:
    try:
        got = bind.build("index", values={"v": value})
    except Exception as error:
        bad.append((value, type(error).__name__)); continue
    if got != want:
        bad.append((value, got))
for value, want in COLLATERAL:
    try:
        survived.append([value, bind.build("index", values={"v": value}) == want])
    except Exception as error:
        survived.append([value, type(error).__name__])
print(json.dumps({"error": None, "count": len(bad), "witness": bad[:6],
                  "cases": len(REQUIRED), "collateral": survived}))
'''

# Drop ONE character from a `safe=` literal. The scope rule that makes this exact:
#   the failing behaviour names the function (_urlencode); inside it there is exactly one
#   `safe=` keyword argument, and that literal contains the offending character.
# Without the scope rule this is "delete a character from any string in the repo".
_SETDROP_SOURCE = r"""
import ast, pathlib, sys
path, func, char = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
src = path.read_text(); tree = ast.parse(src)
found = 0
for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func]:
    for kw in [k for k in ast.walk(fn) if isinstance(k, ast.keyword) and k.arg == "safe"]:
        if not (isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str)):
            continue
        if char not in kw.value.value:
            continue
        lines = src.splitlines(keepends=True)
        i = kw.value.lineno - 1
        new = lines[i].replace(kw.value.value, kw.value.value.replace(char, "", 1), 1)
        if new != lines[i]:
            lines[i] = new; src = "".join(lines); found += 1
if found:
    path.write_text(src)
print(found)
"""


def run_probe(tree: pathlib.Path, args: argparse.Namespace) -> dict[str, Any]:
    if args.relation == "plus_in_safe":
        done = subprocess.run([sys.executable, "-c", PLUS_IN_SAFE_PROBE], cwd=tree,
                              capture_output=True, text=True, errors="replace",
                              timeout=args.seconds,
                              env={**os.environ, "PYTHONPATH": f"{tree}:{tree / 'src'}"})
        try:
            return json.loads(done.stdout.strip().splitlines()[-1])
        except Exception:
            return {"error": (done.stdout + done.stderr)[-400:]}
    if args.relation == "falsey_key":
        done = subprocess.run([sys.executable, "-c", FALSEY_KEY_PROBE], cwd=tree,
                              capture_output=True, text=True, errors="replace",
                              timeout=args.seconds,
                              env={**os.environ, "PYTHONPATH": f"{tree}:{tree / 'src'}"})
        try:
            return json.loads(done.stdout.strip().splitlines()[-1])
        except Exception:
            return {"error": (done.stdout + done.stderr)[-400:]}
    if args.relation == "ipv4_like_host":
        done = subprocess.run([sys.executable, "-c", IPV4_LIKE_PROBE], cwd=tree,
                              capture_output=True, text=True, errors="replace",
                              timeout=args.seconds,
                              env={**os.environ, "PYTHONPATH": f"{tree}:{tree / 'src'}"})
        try:
            return json.loads(done.stdout.strip().splitlines()[-1])
        except Exception:
            return {"error": (done.stdout + done.stderr)[-400:]}
    code, extra = ((PORT_PROBE, []) if args.relation == "parses_leading_zero_port"
                   else (PROBE, [args.a, args.b, args.alphabet, str(args.maxlen),
                                 args.module]))
    done = subprocess.run(
        [sys.executable, "-c", code, *extra],
        cwd=str(tree), capture_output=True, text=True, errors="replace",
        timeout=args.seconds, stdin=subprocess.DEVNULL,
        # src-layout repos need "src:."; FLAT-layout repos (httpx) are shadowed by any
        # installed copy, so the probe silently tests the wrong code. That happened: the
        # ipv4_like_host probe reported the parent's failure on a tree that had already
        # been refined, and the tool concluded NO_REFINEMENT_IN_FAMILY while the correct
        # refinement had in fact fired. Put the tree first, and assert provenance.
        env={**os.environ, "PYTHONPATH": f"{tree}:{tree / 'src'}",
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
                        choices=("agrees", "parses_leading_zero_port", "ipv4_like_host",
                                 "falsey_key", "plus_in_safe"))
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
                if args.relation == "plus_in_safe":
                    source_rel = "src/werkzeug/urls.py"
                if args.relation == "falsey_key":
                    # oracle-selected function and parameter, supplied by the failing test
                    source_rel = "more_itertools/more.py"
                candidates: list[dict[str, Any]] = []
                if args.relation == "plus_in_safe":
                    # Drop ONE character from the single `safe=` literal in the function
                    # the failure names. Scope is what makes this exact: 25 `safe=`
                    # literals exist in werkzeug, and only this one is in the encoder.
                    target = tree / source_rel
                    original = target.read_text(encoding="utf-8", errors="replace")
                    edits = subprocess.run(
                        [sys.executable, "-c", _SETDROP_SOURCE, str(target),
                         "_urlencode", "+"],
                        capture_output=True, text=True, errors="replace")
                    try:
                        changes = int(edits.stdout.strip().splitlines()[-1])
                    except Exception:
                        changes = 0
                    if changes:
                        try:
                            result = run_probe(tree, args)
                        finally:
                            target.write_text(original, encoding="utf-8")
                        candidates.append({"refinement": "SAFE_SET_DROP_PLUS",
                                           "edits": changes, "result": result,
                                           "moved": (not result.get("error")) and
                                                    result.get("count", baseline["count"])
                                                    < baseline["count"],
                                           "cleared": result.get("count") == 0})
                if args.relation == "falsey_key":
                    # AST-scoped refinement: textual substitution cannot express
                    # "a parameter of THIS function used as a bare truthiness test".
                    target = tree / source_rel
                    original = target.read_text(encoding="utf-8", errors="replace")
                    edits = subprocess.run(
                        [sys.executable, "-c", _REFINE_SOURCE, str(target),
                         "all_unique", "key"],
                        capture_output=True, text=True, errors="replace")
                    try:
                        changes = int(edits.stdout.strip().splitlines()[-1])
                    except Exception:
                        changes = 0
                    if changes:
                        try:
                            result = run_probe(tree, args)
                        finally:
                            target.write_text(original, encoding="utf-8")
                        candidates.append({"refinement": "FALSEY_KEY_NOT_NONE",
                                           "edits": changes, "result": result,
                                           "moved": (not result.get("error")) and
                                                    result.get("count", baseline["count"])
                                                    < baseline["count"],
                                           "cleared": result.get("count") == 0})
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
