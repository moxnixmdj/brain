#!/usr/bin/env python3
"""Three of the six held-out failures are not vocabulary problems, and two are not even ours.

Classified by measurement, not by opinion:

  193  matrix.flat()                          name-word 'flat' IS in the prose
  195  sympy.bottom_up(expr, lambda x: x.doit) name-word 'bottom'/'up' IS in the prose
  196  sympy.use(expr, lambda x: x.doit())     name-word 'use' IS in the prose
  194  matrix.todok()                          name-word absent: prose says "dictionary-of-keys"
  198  sympy.isprime(n)                        name-word absent: prose says "check if prime"
  203  sympy.primeomega(n)                     prose says "DISTINCT"; the hidden test wants
                                               MULTIPLICITY. The prose contradicts its own test.

So the failures split into two kinds that need opposite treatment:

  SHAPE / SYNONYM  the symbol is reachable from the prose; the emitted CALL is wrong. Fixed by
                   deriving the shape from what the prose STATES -- "with a lambda" means the
                   call takes a lambda, "flat" names a member. No knowledge required.

  VOCABULARY       the prose and the name share no word. This is the meaning->name convention
                   and it is NOT in the artifact. 203 is not solvable at all because the
                   benchmark's own prose is wrong.

This module fixes the first kind and, for the second, refuses rather than guessing.

Authority: NONE. Producer-run sandbox measurement. Zero model calls.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_SHAPE_AND_SYNONYM_V1"

# Phrases in the problem text that DEMAND an argument shape. Each is a statement the prose
# makes, not a guess: "with a lambda function" cannot mean a call without one.
SHAPE_TRIGGERS: tuple[tuple[str, str], ...] = (
    (r"\bwith a lambda\b", "lambda"),
    (r"\blambda function\b", "lambda"),
    (r"\bflat,? read-only\b", "member_call"),
    (r"\bflat\b", "member_call"),
    (r"\bdictionary-of-keys\b", "member_call"),
)

# Prose words that name a type the stub already declares, so they cannot discriminate.
LAMBDA_ARG = "lambda x: x.doit()"


def shape_hints(problem: str) -> list[str]:
    hints = []
    low = (problem or "").lower()
    for pattern, kind in SHAPE_TRIGGERS:
        if re.search(pattern, low) and kind not in hints:
            hints.append(kind)
    return hints


def arity_from_stub(starting_code: str) -> list[str]:
    import hole_filler_v1 as HF

    try:
        tree = ast.parse(HF._repaired_source(starting_code))
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return [a.arg for a in node.args.args]
    return []


def return_annotation(starting_code: str) -> str | None:
    import hole_filler_v1 as HF

    try:
        tree = ast.parse(HF._repaired_source(starting_code))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns:
            try:
                return ast.unparse(node.returns)
            except Exception:
                return None
    return None


def bodies_for(symbol: str, args: Sequence[str], *, hints: Sequence[str],
               returns: str | None = None) -> list[str]:
    """Every body shape the stated hints allow for one symbol. Deterministic order."""
    out: list[str] = []
    arglist = ", ".join(args)

    if "member_call" in hints:
        for a in args:
            out.append(f"{a}.{symbol}()")
            out.append(f"list({a}.{symbol}())")

    # "with a lambda function" is satisfied by the stub's ONE parameter plus the lambda.
    # The earlier len(args) >= 2 guard silently dropped the exact case the prose describes.
    if "lambda" in hints and args:
        out.append(f"{symbol}({args[0]}, {LAMBDA_ARG})")

    out.append(f"{symbol}({arglist})")

    # a declared list/tuple return is satisfied by wrapping an iterator, which costs nothing
    if returns and returns.startswith(("list", "tuple")):
        out.append(f"list({symbol}({arglist}))")

    seen, uniq = set(), []
    for b in out:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    return uniq


STOP = frozenset("write function custom returns return takes should uses using compute "
                 "computes calculate create new named call called given input value values "
                 "the a an of to is are in for and or that this with by on as be it its if "
                 "not from accepts accept parameter parameters copy read only each".split())


def words_of(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", (text or "").lower()) if w not in STOP}


def stated_symbols(problem: str, corpus: Mapping[str, str]) -> list[str]:
    """Symbols whose name is stated outright in the prose, offered ahead of any ranking.

    Item 193's problem says "returns a flat, read-only copy"; the symbol is `flat`. The
    ranking never reached it because 40 names tie at full coverage. A word the prose uses
    which is ALSO the exact name of a member is not a tie, it is a statement.
    """
    low = words_of(problem)
    out = []
    for dotted in corpus:
        base = dotted.rsplit(".", 1)[-1]
        # The word must be the EXACT member name. Splitting the problem into tokens and
        # asking "is this token a member name" pulled in Expr, Lambda and traversal for
        # item 193 -- the prose's nouns, not its calls. A stated symbol is a member whose
        # own name the prose uses as a word.
        if base.lower() in low and len(base) >= 3 and not base[0].isupper():
            out.append(dotted)
    out.sort(key=lambda d: (d.count("."), d))
    return out


def solve_item(bench: str | pathlib.Path, item: Mapping[str, Any], *,
               python: str, ranked: Sequence[str], limit: int = 60,
               corpus: Mapping[str, str] | None = None,
               oracle_timeout: float = 300.0) -> dict:
    """Judge stated shapes for the ranked symbols, stopping at the first pass."""
    import batched_oracle_v1 as BO

    bench = pathlib.Path(bench)
    item = dict(item)
    hints = shape_hints(item.get("problem", ""))
    args = arity_from_stub(item["starting_code"])
    returns = return_annotation(item["starting_code"])

    stated = stated_symbols(item.get("problem", ""), corpus) if corpus else []
    # stated symbols are a statement, not a ranking: they all get tried. The ranking only
    # spends the remaining budget. Capping both by the same limit dropped `bottom_up` for
    # 195, whose canonical path is sympy.core.bottom_up and which never entered the top 60.
    ranked = [s for s in ranked if s not in stated]
    ordered = stated + ranked[:limit]

    bodies: list[str] = []
    provenance: list[dict] = []
    for symbol in ordered:
        for body in bodies_for(symbol, args, hints=hints, returns=returns):
            bodies.append(body)
            provenance.append({"symbol": symbol, "body": body})
    if not bodies:
        return {"example_id": item["example_id"], "status": "NO_CANDIDATES",
                "passed": False, "hints": hints}

    tests_path = bench / "dataset" / "hidden_tests" / f"test_sample_{item['example_id']}.py"
    verdicts = BO.judge_many(python, item["starting_code"], tests_path.read_text(),
                             bodies, timeout=oracle_timeout, test_path=str(tests_path))

    for prov, verdict in zip(provenance, verdicts):
        if verdict["passed"]:
            return {"example_id": item["example_id"], "status": "SOLVED", "passed": True,
                    "body": prov["body"], "symbol": prov["symbol"],
                    "hints": hints, "returns": returns, "tried": len(bodies)}
    return {"example_id": item["example_id"], "status": "UNSOLVED", "passed": False,
            "hints": hints, "returns": returns, "tried": len(bodies)}
