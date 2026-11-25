"""The project already states its own oracle in the docstring.

My Wall 1 experiment failed (0/19) because it *invented* metamorphic relations
(idempotence, round-trip, aliasing) and checked them against a green suite. The suite's
behaviour is already correct, so the relation fired on intentional mutation: 400
violations on click `d340b0c1` and 213 on attrs `a572c3a4`, identical at the fix.

This is a different source and it was hiding in plain sight. A docstring frequently
states a relation between two functions in the same module:

    "`is_normalized_name()` is documented to return `True` iff `canonicalize_name`
     would roundtrip the name unchanged."

That sentence IS a metamorphic oracle, written by a human, shipped in the source. It
needs no invention and no guessing: parse the claim, run it on the parent, run it at the
fix, keep it if it discriminates.

Measured on `packaging ba17fcea23` by hand before writing this: violations
`['a--b', '1--1']` on the parent, `[]` at the fix. A clean fail-to-pass oracle for a row
that every engine refused, from a docstring.

Claims recognised (conservative; an unrecognised sentence is skipped, not guessed):

    A(x) <-> B(x) == x            "returns True iff <other> roundtrips"
    A(x) <-> B(x) is A(x)         "is equivalent to", "agrees with"
    A(f(x)) == g(A(x))            stated commutation

The tool never writes a candidate patch. It produces the DEMAND only -- which is the
half that was missing, and which every generator in this repo must have before it can
act.

    python canonical/tools/the_docstring_states_the_oracle_v1.py \
        --receipt canonical/verification/THE_DOCSTRING_STATES_THE_ORACLE_20261124_V1.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

CORPUS = REPO / "canonical" / "corpus" / "single_line_fix_commits_20261123_V1.json"
DEFAULT_REPOS_ROOT = pathlib.Path("/home/user/repos")

# Names must look like identifiers so prose words ("the", "this") never qualify.
IDENT = r"[a-z_][a-z0-9_]{3,}"
# "A returns True iff B ... roundtrip[s]" -- the packaging case.
# The shipped docstring is:
#     Check if a name is already normalized (i.e. canonicalize_name would
#     roundtrip to the same value).
# The word "iff" is absent and the relation spans a line break. What is actually
# stated is: the predicate agrees with "B would roundtrip to the same value".
# So the pattern keys on the ROUNDTRIP PHRASE and takes the nearest preceding
# identifier as B, not on any particular conjunction. My first version required
# a literal "iff" on one line and found nothing in the very function it was built
# for.
IFF_ROUNDTRIP = re.compile(
    rf"^(?P<doc>\s*)[^\n]*?\b(?P<b>{IDENT})\b[^.\n]{{0,80}}?"
    rf"(?:roundtrip|round-trip|the same value|unchanged)", re.I | re.S)
# "A is equivalent to B" / "A agrees with B"
EQUIVALENT = re.compile(
    rf"({IDENT})\s*\(?\)?[^.\n]{{0,60}}?\b(?:is equivalent to|agrees with|"
    rf"is consistent with)\b[^.\n]{{0,40}}?({IDENT})", re.I)


def git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, errors="replace")


def docstrings(text: str) -> list[tuple[str, str]]:
    """(owning function name, docstring) for every def in the file.

    Parsed, not regexed. My first attempt used a regex over the source and found ZERO
    docstrings in the file it was written for -- a regex spanning triple quotes and
    newlines is exactly the kind of thing that silently returns nothing.
    """
    import ast as _ast
    try:
        tree = _ast.parse(text)
    except SyntaxError:
        return []
    out: list[tuple[str, str]] = []
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            doc = _ast.get_docstring(node)
            if doc:
                out.append((node.name, doc))
    return out


def claims_in(text: str) -> list[dict[str, str]]:
    """Every mechanically-checkable relation the prose states between two identifiers.

    Docstrings are scanned first, because the subject of the sentence is usually the
    function that owns the docstring (`is_normalized_name`), not a name repeated inside
    it.
    """
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    STOP = {"roundtrip", "round", "trip", "same", "value", "unchanged", "return",
            "returns", "returned", "check", "already", "normalized", "would", "name",
            "param", "type", "args", "none", "bool", "true", "false"}
    ROUNDTRIP = re.compile(r"\b(?:roundtrip|round-trip|the same value|unchanged|"
                           r"unchanged)\b", re.I)
    for owner, body in docstrings(text or ""):
        # strip Sphinx/reST roles so :func:`canonicalize_name` reads as an identifier
        clean = re.sub(r":[a-z]+:`~?([^`]+)`", r"\1", body).replace("`", " ")
        phrase = ROUNDTRIP.search(clean)
        if not phrase:
            continue
        # take identifiers ADJACENT to the phrase, nearest first, not a greedy span
        before = re.findall(r"\b([a-z_][a-z0-9_]{3,})\b", clean[:phrase.start()])
        order = [w for w in reversed(before) if w.lower() not in STOP]
        if not order:
            continue
        other = order[0]
        if other == owner or "test" in owner:
            continue
        key = ("iff_roundtrip", owner, other)
        if key in seen:
            continue
        seen.add(key)
        out.append({"kind": "iff_roundtrip", "a": owner, "b": other,
                    "quote": clean.strip()[:200]})

    for kind, pattern in (("iff_roundtrip", IFF_ROUNDTRIP), ("equivalent", EQUIVALENT)):
        for match in pattern.finditer(text or ""):
            a, b = match.group(1), match.group(2)
            if a == b or "test" in a or "test" in b:
                continue
            key = (kind, a, b)
            if key in seen:
                continue
            seen.add(key)
            out.append({"kind": kind, "a": a, "b": b,
                        "quote": match.group(0)[:200]})
    return out


# The probe imports the project, finds both callables, and reports disagreements.
# It deliberately does NOT know which tree it is in; the caller compares.
PROBE = '''
import importlib, itertools, json, sys
a_name, b_name, alphabet, maxlen = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
pkg = sys.argv[5]

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
    print(json.dumps({"error": "missing", "a": A is not None, "b": B is not None}))
    raise SystemExit(0)

alphabet = alphabet.split(",")
cases = ["".join(p) for n in range(1, maxlen + 1) for p in itertools.product(alphabet, repeat=n)]
# Only inputs the function's own domain admits. A bare "-" or "a-" is not a package
# name under PEP 503, so a disagreement there is noise, not a defect -- and it buried
# the real witness ("a--b") under 45 irrelevant ones on the first run.
cases = [c for c in cases if c[0].isalnum() and c[-1].isalnum()]
violations = []
for case in cases:
    try:
        left = bool(A(case))
    except Exception:
        continue
    try:
        right = (B(case) == case)
    except Exception:
        continue
    if left != right:
        violations.append(case)
print(json.dumps({"error": None, "cases": len(cases), "violations": violations[:12],
                  "count": len(violations)}))
'''


def run_probe(tree: pathlib.Path, claim: dict[str, str], pkg: str,
              seconds: int) -> dict[str, Any]:
    flag = git(tree, "rev-parse", "--is-inside-work-tree")
    if flag.returncode != 0:
        return {"error": "no_worktree"}
    alphabet = "a,1,-"
    done = subprocess.run(
        [sys.executable, "-c", PROBE, claim["a"], claim["b"], alphabet, "4", pkg],
        cwd=str(tree), capture_output=True, text=True, errors="replace",
        timeout=seconds, stdin=subprocess.DEVNULL,
        env={**__import__("os").environ, "PYTHONPATH": "src:.",
             "PYTHONDONTWRITEBYTECODE": "1"})
    for line in reversed((done.stdout or "").strip().splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return {"error": "probe_failed", "tail": (done.stderr or "")[-200:]}


def package_for(repo: str, tree: pathlib.Path) -> str | None:
    """The importable package name, read from the tree rather than assumed."""
    for candidate in ("src", "."):
        base = tree / candidate if candidate != "." else tree
        if not base.is_dir():
            continue
        for entry in base.iterdir():
            if entry.is_dir() and (entry / "__init__.py").exists():
                return entry.name
    return None


def one(repo_path: pathlib.Path, entry: dict[str, Any], seconds: int) -> dict[str, Any]:
    row: dict[str, Any] = {"repo": entry["repo"], "commit": entry["commit"][:10]}
    with tempfile.TemporaryDirectory() as where:
        parent = pathlib.Path(where) / "parent"
        fix = pathlib.Path(where) / "fix"
        for tree, rev in ((parent, f"{entry['commit']}^"), (fix, entry["commit"])):
            added = git(repo_path, "worktree", "add", "--detach", str(tree), rev)
            if added.returncode != 0:
                return {**row, "verdict": "WORKTREE_FAILED",
                        "note": added.stderr[:140]}
        try:
            sources = entry.get("sources") or []
            text = ""
            for source in sources:
                target = parent / source
                if target.exists():
                    text += target.read_text(encoding="utf-8", errors="replace")
            claims = claims_in(text)
            row["claims"] = claims
            if not claims:
                row["verdict"] = "NO_STATED_RELATION"
                return row
            pkg = package_for(entry["repo"], parent)
            row["package"] = pkg
            if not pkg:
                row["verdict"] = "NO_IMPORTABLE_PACKAGE"
                return row
            tested = []
            for claim in claims:
                before = run_probe(parent, claim, pkg, seconds)
                after = run_probe(fix, claim, pkg, seconds)
                if before.get("error") or after.get("error"):
                    continue
                tested.append({"claim": claim, "parent_violations": before["count"],
                               "fix_violations": after["count"],
                               "witness": (before.get("violations") or [])[:4],
                               "discriminates": before["count"] > 0
                                                and after["count"] == 0})
            row["tested"] = tested
            winning = [t for t in tested if t["discriminates"]]
            if winning:
                row["verdict"] = "DOCSTRING_ORACLE_DISCRIMINATES"
                row["witness"] = winning[0]["witness"]
                row["quote"] = winning[0]["claim"]["quote"]
            elif tested:
                row["verdict"] = "RELATION_DOES_NOT_DISCRIMINATE"
            else:
                row["verdict"] = "RELATION_UNRUNNABLE"
            return row
        finally:
            for tree in (parent, fix):
                git(repo_path, "worktree", "remove", "--force", str(tree))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--repos-root", type=pathlib.Path, default=DEFAULT_REPOS_ROOT)
    parser.add_argument("--only", default="")
    parser.add_argument("--seconds", type=int, default=120)
    args = parser.parse_args(argv)

    tasks = json.loads(CORPUS.read_text(encoding="utf-8"))["tasks"]
    wanted = {p.strip() for p in args.only.split(",") if p.strip()}
    if wanted:
        tasks = [t for t in tasks if any(t["commit"].startswith(w) for w in wanted)]

    rows = []
    for index, entry in enumerate(tasks, 1):
        repo_path = args.repos_root / entry["repo"]
        if not (repo_path / ".git").exists():
            rows.append({"repo": entry["repo"], "commit": entry["commit"][:10],
                         "verdict": "REPO_MISSING"})
            continue
        row = one(repo_path, entry, args.seconds)
        rows.append(row)
        print(f"[{index}/{len(tasks)}] {row['repo']:14s} {row['commit']} "
              f"{row['verdict']:32s} claims={len(row.get('claims') or [])} "
              f"{str(row.get('witness',''))[:40]}", flush=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    receipt = {"schema": "THE_DOCSTRING_STATES_THE_ORACLE_V1",
               "method": "harvest a relation the docstring already states between two "
                         "identifiers, run it on parent and fix, keep if it discriminates",
               "counts": dict(sorted(counts.items())), "rows": rows}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print("\n== counts")
    for name, count in receipt["counts"].items():
        print(f"  {name:34s} {count}")
    print(f"\nreceipt -> {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
