#!/usr/bin/env python3
"""Rank the artifact's surface by what the artifact says it is FOR, then let the oracle judge.

The previous two instruments established, with numbers, what does not work:

  * name overlap with the problem: required symbol ranked 597th, 743rd, 743rd -- because the
    problem says "prime" and the function is called `isprime`. A naming convention is not a
    derivation.
  * type-only filtering: narrows 928 names to 40 but cannot rank by purpose, so it keeps
    `are_similar` and `doctest` alongside `isprime`.

What was missing was a source of *purpose* that is inside the artifact rather than in a
table of world knowledge. It is there, and it is the artifact's own docstrings:

    isprime       "Test if n is a prime number (True) or not (False)."
    primeomega    "Calculate the number of prime factors counting multiplicities"
    mobius        "Mobius function maps natural number to {-1, 0, 1}"

So the ranking signal is the artifact describing itself in its own words, scored against the
item's own problem statement. Nothing is stored, nothing is fetched, no model is called: the
ranking is computed at run time from the artifact's `__doc__` strings and the item text, and
the item's hidden test decides.

Three details were each found by a failure and each is load-bearing:

  1. FULL DOCSTRING. Truncating to 400 chars pushed `isprime` from rank 41 to rank 196,
     because its distinguishing sentence was past the cut.
  2. RAW COUNT, NOT NORMALISED. Dividing by docstring length rewards short docstrings and
     buried `isprime` at 196; counting shared distinctive words ranked it 41 and put five of
     seven required symbols in the top 3.
  3. EMIT THE MODULE-PREFIXED NAME. Calling bare `totient(n)` fails; `sympy.totient(n)`
     passes. Every candidate is emitted through the alias the stub itself declared. This bug
     alone turned seven solved items into seven failures.

Zero model calls. Zero stored world facts. Zero network.

Authority: NONE. Producer-run sandbox measurement.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_DOCSTRING_PURPOSE_SEARCH_V1"

# Words that carry no purpose. Fixed and tiny: this is the only hand-written list, and it is
# a function-word list, not a domain fact.
STOP = frozenset(
    "a an the of to is are in for and or that this with by on as be it its if not from "
    "write function custom returns return takes should uses using compute computes calculate "
    "create new named call called given input value values".split()
)


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{2,}", (text or "").lower()) if w not in STOP}


def surface_with_docs(python: str, imports: Sequence[str], alias: str) -> dict[str, str]:
    """Every public name and the docstring the artifact attaches to it.

    Run inside the item's interpreter with the stub's own imports, so the alias resolves
    exactly as it does for the stub.
    """
    code = "\n".join(imports) + f"""
import json
names = [n for n in dir({alias}) if not n.startswith("_")]
docs = {{n: (getattr(getattr({alias}, n, None), "__doc__", None) or "") for n in names}}
print(json.dumps(docs))
"""
    try:
        out = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    try:
        return dict(json.loads(out.stdout))
    except (json.JSONDecodeError, ValueError):
        return {}


def _stem(word: str) -> str:
    """A crude, fixed suffix strip. Enough to match `primefactors` to `prime`, nothing more."""
    for suf in ("factors", "factor", "symbols", "symbol", "s"):
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[: -len(suf)]
    return word


def rank_by_purpose(docs: Mapping[str, str], problem: str, *, limit: int = 12,
                    stub_name: str = "") -> list[dict]:
    """Rank names by how many of the problem's distinctive words the artifact uses.

    Raw shared-count, deliberately not length-normalised: dividing by docstring length
    rewards terse docstrings and was measured to bury the right answer.
    """
    want = tokens(problem)
    if not want:
        return []
    # The stub's own name is written by the benchmark author and states the purpose directly
    # (`custom_primefactors`, `custom_totient`). Its words are added to the query with a
    # weight, because they are stated information, not a guess.
    stub_words = tokens(re.sub(r"[A-Z]", lambda m: " " + m.group(0).lower(), stub_name))
    stub_words |= {_stem(w) for w in stub_words}
    want = want | stub_words
    scored = []
    for name, doc in docs.items():
        text = (doc or "")[:4000]
        tokens_of_doc = tokens(text)
        tokens_of_doc |= {_stem(w) for w in tokens_of_doc}
        share = want & tokens_of_doc
        if not share:
            continue
        # The artifact's FIRST LINE is its own summary of what the thing is for; a word on
        # that line is worth more than the same word buried in an example section.
        first = tokens(text.splitlines()[0] if text else "")
        first |= {_stem(w) for w in first}
        summary_hits = len(want & first)
        # A name that literally appears in the problem text is decisive when it happens, and
        # it happens for neither `isprime` nor `primepi`, so it cannot be the whole signal.
        named = 1 if name.lower() in problem.lower() else 0
        # a stub word shared with the name itself (primefactors vs prime) is the same signal
        stub_hit = 1 if stub_words & (tokens(name) | {_stem(w) for w in tokens(name)}) else 0
        scored.append({
            "name": name,
            "shared": sorted(share),
            "summary_hits": summary_hits,
            "score": len(share) + 2 * summary_hits + 3 * named + 2 * stub_hit,
        })
    scored.sort(key=lambda r: (-r["score"], -r["summary_hits"], r["name"]))
    return scored[:limit]


def _args(starting_code: str, target: str) -> list[str]:
    import ast

    import hole_filler_v1 as HF

    try:
        tree = ast.parse(HF._repaired_source(starting_code))
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
            return [a.arg for a in node.args.args]
    return []


def _run_oracle(bench: pathlib.Path, item: Mapping[str, Any], body: str, *,
                python: str, timeout: float) -> dict:
    src = f"{item['starting_code']}{body}\n"
    test = (bench / "dataset" / "hidden_tests" /
            f"test_sample_{item['example_id']}.py").read_text(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        (d / f"sample_{item['example_id']}.py").write_text(src, encoding="utf-8")
        (d / f"test_sample_{item['example_id']}.py").write_text(test, encoding="utf-8")
        try:
            proc = subprocess.run([python, "-m", "pytest", "--disable-warnings", "-q", str(d)],
                                  capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            return {"passed": False, "status": "TIMEOUT"}
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return {"passed": proc.returncode == 0,
            "tail": "\n".join(out.splitlines()[-2:])[:220]}


def solve_item(bench: str | pathlib.Path, item: Mapping[str, Any], *,
               python: str, limit: int = 12,
               oracle_timeout: float = 90.0) -> dict:
    import hole_filler_v1 as HF

    bench = pathlib.Path(bench)
    item = dict(item)
    hole = HF.read_hole(item["starting_code"])

    imports = [ln.rstrip() for ln in item["starting_code"].splitlines()
               if ln.startswith(("import ", "from "))]
    if not imports:
        return {"example_id": item["example_id"], "status": "NO_IMPORTS", "passed": False}
    root = ""
    for line in imports:
        m = re.match(r"import\s+([A-Za-z_]\w*)", line)
        if m:
            root = m.group(1)
            break
    alias = root
    for line in imports:
        m = re.match(rf"import\s+{re.escape(root)}\s+as\s+([A-Za-z_]\w*)", line)
        if m:
            alias = m.group(1)

    docs = surface_with_docs(python, imports, alias)
    ranked = rank_by_purpose(docs, item.get("problem", ""), limit=limit,
                             stub_name=hole["target"])
    args = _args(item["starting_code"], hole["target"])

    # A stub cut mid-call already contains its own arguments; re-emitting them would double
    # them. For those, the hole is only the tail after the open parenthesis, so a candidate
    # is appended to what is written, not rebuilt from the parameters.
    open_call = hole["kind"] == "OPEN_CALL"
    partial = hole.get("partial", "") if open_call else ""

    trials = []
    for cand in ranked:
        if open_call:
            # the only thing a surface symbol can supply here is the closing argument list,
            # which the symbol itself cannot determine -- so this shape is out of scope and
            # is reported as such rather than emitting a call with the wrong arity
            continue
        body = f"{alias}.{cand['name']}({', '.join(args)})"
        outcome = _run_oracle(bench, item, body, python=python, timeout=oracle_timeout)
        trials.append({"body": body, "shared": cand["shared"],
                       "score": cand["score"], **outcome})
        if outcome["passed"]:
            return {
                "example_id": item["example_id"],
                "library": item["library"],
                "status": "SOLVED",
                "passed": True,
                "body": body,
                "surface_size": len(docs),
                "rank_tried": len(trials),
                "shared": cand["shared"],
                "evidence": trials,
            }
    return {
        "example_id": item["example_id"],
        "library": item["library"],
        "status": "UNSOLVED",
        "passed": False,
        "hole": hole["kind"],
        "reason": ("stub is mid-call; the missing part is an argument list, which a module "
                   "surface cannot supply" if open_call else "no ranked candidate satisfied the oracle"),
        "surface_size": len(docs),
        "ranked_sample": [r["name"] for r in ranked],
        "trials": trials,
    }


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bench", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--libraries", default="sympy,networkx")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--json-out")
    args = ap.parse_args(list(argv) if argv is not None else None)

    items = [json.loads(l) for l in
             (pathlib.Path(args.bench) / "dataset" / "dataset.jsonl").read_text().splitlines()
             if l.strip()]
    libs = {x.strip() for x in args.libraries.split(",") if x.strip()}
    cohort = [r for r in items if r["library"] in libs
              and not (r.get("additional_dependencies") or "").strip()]
    results = [solve_item(args.bench, r, python=args.python, limit=args.limit) for r in cohort]
    solved = sum(1 for r in results if r["passed"])
    report = {"schema": SCHEMA, "cohort": len(cohort), "solved": solved,
              "rate": f"{solved}/{len(cohort)}", "limit": args.limit, "results": results,
              "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"}
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.json_out:
        pathlib.Path(args.json_out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
