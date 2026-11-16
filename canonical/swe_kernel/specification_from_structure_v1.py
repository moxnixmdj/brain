#!/usr/bin/env python3
"""A specification is read off the code's own structure, confirmed on the program as it
stands, and only then allowed to judge a candidate.

WHY THIS EXISTS
---------------
Every learning loop in this tree ends at the same missing object: a verifier. The lesson
admission gate can admit a rule only if something outside the rule says which outcome was
right. A test supplies that where a test exists -- and in real work the test is the
expensive part. The 2026 field says the same thing from both sides: OSWorld 2.0
(arXiv:2606.29537) finds verification skipping is the central failure mode of long-horizon
computer use; Veritas (arXiv:2611.13336) finds test-time self-improvement "gated by the same
bottleneck: the verifier"; and this tree's own measurement found its shipped test generator's
assertions had a mutation score of 0.000 -- `assertNotIsInstance(result, BaseException)` is
true of every function that returns, the local instance of *All Smoke, No Alarm*
(arXiv:2606.18168: weak or absent oracle signals in 80.2% of 86,156 agent-authored test-file
patches).

So the question this module answers is not "how do we get more tests". It is:

    what can be known about correctness with no specification, no test file and no model,
    from the program's own structure plus its own execution?

A function's name and shape constrain what it must do. A `normalize` must reach a fixed point
or the name is wrong. `encode`/`decode` must round-trip or one of them is wrong. A `lines`
that reorders must not lose an element. A `isabs` that disagrees with `posixpath.isabs` on an
input is wrong on that input, and the standard library is on every machine. None of these
needs a human, a model or a test.

THE TWO LAYERS, AND WHY BOTH ARE NEEDED
---------------------------------------
1. **Proposal** is structural and cheap: names, arities, annotations, inverse pairs. Its job
   is to order the hypotheses, not to decide anything.
2. **Confirmation** is execution against the program as it stands: a proposed law is usable
   only if it held on the baseline for every input where it was defined. The law is a
   hypothesis; the baseline is its first victim. This is the lesson admission gate's
   discipline, moved one level up.

Two refusal conditions matter more than the confirmation, because they are the two ways a
verifier lies:

    REFUTED   the relation does not hold on the program as it stands, so it is not a law of
              this program and may judge nothing. (It may be a defect report about the
              baseline; it is recorded and NOT used.)
    VACUOUS   the relation holds but no input in the grid could have broken it: a constant
              function is trivially idempotent; a function returning its input trivially
              round-trips. A check whose success case is "I didn't look" is the exact failure
              this tree keeps naming, so a vacuous law is counted and never used.

WHAT IT DOES NOT CLAIM
----------------------
A kill is not a proof of wrongness and a survivor is not a proof of rightness. Killing a
behaviourally perturbed variant means *this law, confirmed on this program, distinguishes that
variant from the program*. Confirmation is over a bounded grid, so a confirmed law is a
hypothesis about the program, not a theorem. The residual (survivors) is the honest blind
spot and is reported as such.

Authority: NONE. Stdlib only. Every execution happens in one time-bounded child process in a
temporary directory; a function whose own body mentions a filesystem, network, process or
interpreter primitive is declined by static name and never called.
"""
from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SPECIFICATION_FROM_STRUCTURE_V1"

CONFIRMED = "CONFIRMED"
VACUOUS = "VACUOUS"
REFUTED = "REFUTED_ON_THE_BASELINE"
NOT_APPLICABLE = "NOT_APPLICABLE"

# --------------------------------------------------------------------------- #
# Layer 1: what structure proposes. Nothing here decides anything.
# --------------------------------------------------------------------------- #
#: A name that says "canonical form" raises the prior that a fixed point exists.
IDEMPOTENT_TOKENS: tuple[str, ...] = (
    "normalize", "normalise", "canonical", "canonicalize", "canonicalise", "sanitize",
    "sanitise", "clean", "dedupe", "dedup", "unique", "sort", "sorted", "strip", "trim",
    "squash", "compact", "stabilize", "stabilise",
)

#: A name that says "reorder a sequence" raises the prior that no element is lost.
MULTISET_TOKENS: tuple[str, ...] = (
    "sort", "sorted", "unique", "dedupe", "dedup", "shuffle", "reorder", "order", "reverse",
    "rank", "lines",
)

#: A name that says "deduplicate" preserves the set of elements, and legitimately drops the
#: duplicates, so it is a different law from multiset preservation. Both are proposed and
#: execution decides which one this program actually obeys.
SET_TOKENS: tuple[str, ...] = ("unique", "dedupe", "dedup", "set")

#: Ordered stems whose names say one inverts the other.
ROUND_TRIP_STEMS: tuple[tuple[str, str], ...] = (
    ("encode", "decode"), ("enc", "dec"), ("dumps", "loads"), ("dump", "load"),
    ("serialize", "deserialize"), ("serialise", "deserialise"), ("quote", "unquote"),
    ("compress", "decompress"), ("pack", "unpack"), ("marshal", "unmarshal"),
    ("escape", "unescape"),
)

#: A reimplementation that disagrees with the standard library on an input is wrong on that
#: input. The reference is resolved through `importlib`, so no import happens at module load.
STDLIB_REFERENCES: dict[str, tuple[str, str]] = {
    "isabs": ("posixpath", "isabs"),
    "isabsolute": ("posixpath", "isabs"),
    "basename": ("posixpath", "basename"),
    "dirname": ("posixpath", "dirname"),
    "splitext": ("posixpath", "splitext"),
    "normpath": ("posixpath", "normpath"),
    "floor": ("math", "floor"),
    "ceil": ("math", "ceil"),
    "sqrt": ("math", "sqrt"),
    "fabs": ("math", "fabs"),
    "gcd": ("math", "gcd"),
    "isqrt": ("math", "isqrt"),
    "hex": ("builtins", "hex"),
    "bin": ("builtins", "bin"),
    "abs": ("builtins", "abs"),
    "round": ("builtins", "round"),
    "strip": ("builtins", "strip"),
    "lstrip": ("builtins", "lstrip"),
    "rstrip": ("builtins", "rstrip"),
    "lower": ("builtins", "lower"),
    "upper": ("builtins", "upper"),
    "casefold": ("builtins", "casefold"),
    "swapcase": ("builtins", "swapcase"),
    "isdigit": ("builtins", "isdigit"),
    "isalpha": ("builtins", "isalpha"),
    "isalnum": ("builtins", "isalnum"),
    "isspace": ("builtins", "isspace"),
    "startswith": ("builtins", "startswith"),
    "endswith": ("builtins", "endswith"),
    "split": ("builtins", "split"),
    "splitlines": ("builtins", "splitlines"),
    "replace": ("builtins", "replace"),
    "zfill": ("builtins", "zfill"),
    "capitalize": ("builtins", "capitalize"),
    "center": ("builtins", "center"),
    "expandtabs": ("builtins", "expandtabs"),
}

#: Names whose mention in a function body means this instrument will not call it. The list is
#: about what the body *names*, because that is the only static fact available pre-call.
DANGEROUS_NAMES: frozenset[str] = frozenset({
    "open", "exec", "eval", "compile", "__import__", "input", "system", "popen", "fork",
    "kill", "unlink", "remove", "removedirs", "rmdir", "rmtree", "chmod", "chown", "rename",
    "write_text", "write_bytes", "mkdir", "makedirs", "run", "call", "check_call",
    "check_output", "Popen", "socket", "connect", "urlopen", "urlretrieve", "getenv",
    "environ", "exit", "_exit", "abort", "sqlite3",
})

#: The only values this instrument will pass to real code. Small on purpose: a bigger grid
#: buys a smaller blind spot and a longer wall clock, and the measurement is about the
#: mechanism, not about maximising one number.
POOLS: dict[str, tuple[Any, ...]] = {
    "int": (-3, -1, 0, 1, 2, 3, 10, 100),
    "float": (-1.5, 0.0, 2.5, 10.0),
    "str": ("", "a", "A", " a ", "a b", "12", "3.5", "a/b/c", "x\ny", "ab",
            "/", "/a/b", "/a/../b"),
    "bool": (True, False),
    "list": ([], [1], [3, 1, 2], [1, 1, 2], [0, -1], ["b"], ["b", "a", "b"], ["a", "b"]),
    "dict": ({}, {"a": 1}, {"a": 1, "b": 2}),
}

#: What to try when nothing in the signature says what the parameter is.
UNKNOWN_POOL: tuple[Any, ...] = (
    0, 1, 2, -1, "", "a", " a ", "a b", "12", "a/b/c", "x\ny", [1], [3, 1, 2],
    ["b", "a", "b"], {}, True, None,
)

#: A module is not imported to be judged. Only these imports and the selected function
#: definitions are put in front of the interpreter, so no top-level statement of the real
#: module ever runs. A function whose body needs a global built by a call at import time will
#: fail with NameError and be recorded as excluded -- that is the price of never executing a
#: module's import side effects, and it is paid in coverage, not in truth.
STDLIB_TOP_LEVEL: frozenset[str] = frozenset({
    "__future__", "abc", "ast", "base64", "binascii", "bisect", "collections", "contextlib",
    "copy", "csv", "dataclasses", "decimal", "difflib", "enum", "fractions", "functools",
    "gzip", "hashlib", "heapq", "io", "itertools", "json", "math", "numbers", "operator",
    "os", "pathlib", "posixpath", "random", "re", "statistics", "string", "struct", "sys",
    "textwrap", "time", "typing", "unicodedata", "urllib", "uuid", "xml", "zlib",
})

MAX_INPUTS_PER_FUNCTION = 24


# --------------------------------------------------------------------------- #
# Layer 1 implementation
# --------------------------------------------------------------------------- #
def _annotation_kind(node: ast.AST | None) -> str | None:
    """Map an annotation to a value-pool name when it is one of the simple ones."""
    if node is None:
        return None
    if isinstance(node, ast.Name):
        text = node.id
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value
    elif isinstance(node, ast.Attribute):
        text = node.attr
    else:
        text = ast.unparse(node)
    text = text.strip().strip("'\"").lower()
    if text in ("int", "integer"):
        return "int"
    if text in ("float", "double"):
        return "float"
    if text in ("str", "string", "text"):
        return "str"
    if text in ("bool", "boolean"):
        return "bool"
    if text.startswith(("list", "sequence", "tuple")):
        return "list"
    if text.startswith(("dict", "mapping")):
        return "dict"
    return None


def _name_tokens(name: str) -> list[str]:
    """Split a function name into lowercase tokens on underscores and camel humps."""
    spaced: list[str] = []
    for index, char in enumerate(name):
        if char == "_":
            spaced.append(" ")
        elif char.isupper() and index and not name[index - 1].isupper():
            spaced.append(" " + char.lower())
        else:
            spaced.append(char.lower())
    return [token for token in "".join(spaced).split() if token]


def _signature(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    args = fn.args
    positional = list(args.posonlyargs) + list(args.args)
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    required: list[dict[str, Any]] = []
    for arg, default in zip(positional, defaults):
        if default is not None:
            continue
        required.append({"name": arg.arg, "kind": _annotation_kind(arg.annotation)})
    return {
        "required": required,
        "varargs": args.vararg is not None,
        "kwargs": args.kwarg is not None,
        "kwonly_required": [
            arg.arg
            for arg, default in zip(args.kwonlyargs, args.kw_defaults)
            if default is None
        ],
        "returns": _annotation_kind(fn.returns),
    }


def _declined_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and node.id in DANGEROUS_NAMES:
            hits.append(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in DANGEROUS_NAMES:
            hits.append(node.attr)
    ordered: list[str] = []
    for hit in hits:
        if hit not in ordered:
            ordered.append(hit)
    return ordered


def public_functions(module_source: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The functions this instrument is willing to call, and the ones it refuses to call."""
    tree = ast.parse(module_source)
    accepted: list[dict[str, Any]] = []
    declined: list[dict[str, Any]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("__") and node.name.endswith("__"):
            continue
        signature = _signature(node)
        reason = None
        if isinstance(node, ast.AsyncFunctionDef):
            reason = "ASYNC_FUNCTION_NOT_CALLED_HERE"
        elif signature["varargs"] or signature["kwargs"]:
            reason = "VARIADIC_SIGNATURE_HAS_NO_FINITE_CALL_GRID"
        elif signature["kwonly_required"]:
            reason = "REQUIRED_KEYWORD_ONLY_ARGUMENT"
        elif len(signature["required"]) > 2:
            reason = "ARITY_ABOVE_TWO"
        else:
            dangerous = _declined_names(node)
            if dangerous:
                reason = "REACHES_A_SIDE_EFFECTING_NAME:" + ",".join(sorted(dangerous))
        entry = {
            "name": node.name,
            "lineno": node.lineno,
            "required": signature["required"],
            "returns": signature["returns"],
            "tokens": _name_tokens(node.name),
        }
        if reason is None:
            accepted.append(entry)
        else:
            entry["reason"] = reason
            declined.append(entry)
    return accepted, declined


def _has_a_call(node: ast.AST) -> bool:
    return any(isinstance(sub, (ast.Call, ast.Await, ast.Yield, ast.YieldFrom)) for sub in ast.walk(node))


def reduce_module(module_source: str, function_names: Sequence[str]) -> str:
    """The smallest module that still lets the selected functions be called.

    Imports that are not standard library are dropped, module-level assignments whose value
    could execute something are dropped, and every other top-level statement -- including the
    `sys.path.insert(...)` and the `if __name__ == "__main__"` block that real modules carry --
    is dropped. Nothing at module scope can then have an effect.
    """
    tree = ast.parse(module_source)
    wanted = set(function_names)
    body: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            if all(alias.name.split(".")[0] in STDLIB_TOP_LEVEL for alias in node.names):
                body.append(node)
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if node.level == 0 and (module in STDLIB_TOP_LEVEL or module == "__future__"):
                body.append(node)
        elif isinstance(node, ast.Assign):
            if not _has_a_call(node.value):
                body.append(node)
        elif isinstance(node, ast.AnnAssign):
            if node.value is None or not _has_a_call(node.value):
                body.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
            body.append(node)
    reduced = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(reduced)
    return ast.unparse(reduced) + "\n"


def _round_trip_pairs(names: Sequence[str]) -> list[tuple[str, str]]:
    """(encoder, decoder) pairs whose names say one inverts the other."""
    pairs: list[tuple[str, str]] = []
    lowered = {name.lower(): name for name in names}
    for first, second in ROUND_TRIP_STEMS:
        for name in names:
            low = name.lower()
            index = low.find(first)
            if index < 0:
                continue
            partner = lowered.get(low[:index] + second + low[index + len(first):])
            if partner and partner != name:
                pairs.append((name, partner))
    return pairs


def derive(module_source: str, module_name: str) -> dict[str, Any]:
    """Every law this module's structure proposes, before anything has been executed."""
    accepted, declined = public_functions(module_source)
    by_name = {entry["name"]: entry for entry in accepted}
    invariants: list[dict[str, Any]] = []

    def add(kind: str, function: str, derivation: str, **extra: Any) -> None:
        invariant = {
            "invariant_id": f"{kind}:{function}" + (":" + str(extra["partner"]) if extra.get("partner") else ""),
            "kind": kind,
            "function": function,
            "module": module_name,
            "derivation": derivation,
        }
        invariant.update(extra)
        invariants.append(invariant)

    for entry in accepted:
        name = entry["name"]
        tokens = set(entry["tokens"])
        arity = len(entry["required"])
        add("TOTALITY", name,
            "a function that returned on this input returns on this input; every other law is "
            "only meaningful on a defined input")
        if arity == 1:
            if tokens & set(IDEMPOTENT_TOKENS):
                why = ",".join(sorted(tokens & set(IDEMPOTENT_TOKENS)))
                add("IDEMPOTENCE", name, f"the name says 'canonical form': {why}")
            else:
                add("IDEMPOTENCE", name,
                    "unary and therefore testable for a fixed point; the name does not claim one, "
                    "so this is a hypothesis execution must confirm")
            add("INVOLUTION", name,
                "unary and therefore testable for being its own inverse")
            if tokens & set(MULTISET_TOKENS) and entry["required"][0]["kind"] in (None, "list"):
                why = ",".join(sorted(tokens & set(MULTISET_TOKENS)))
                add("MULTISET_PRESERVED", name, f"the name says 'reorder a sequence': {why}")
            if tokens & set(SET_TOKENS) and entry["required"][0]["kind"] in (None, "list"):
                why = ",".join(sorted(tokens & set(SET_TOKENS)))
                add("SET_PRESERVED", name, f"the name says 'deduplicate a sequence': {why}")
            reference = sorted(tokens & set(STDLIB_REFERENCES))
            if reference:
                module_ref, attr = STDLIB_REFERENCES[reference[0]]
                add("STDLIB_DIFFERENTIAL", name,
                    f"the name says `{reference[0]}`, which the standard library defines",
                    reference_module=module_ref, reference_attr=attr)
            elif name.lower() in STDLIB_REFERENCES:
                module_ref, attr = STDLIB_REFERENCES[name.lower()]
                add("STDLIB_DIFFERENTIAL", name,
                    f"the name `{name}` is the standard library's `{attr}`",
                    reference_module=module_ref, reference_attr=attr)
        if arity == 1:
            add("PERMUTATION_INVARIANT", name,
                "unary, so if this program folds a sequence the answer may not depend on the "
                "order it was handed; execution decides")
        if arity == 2:
            add("ASSOCIATIVITY", name,
                "binary and therefore testable for regrouping; a name that does not claim it "
                "makes this a hypothesis execution must confirm")
            add("COMMUTATIVITY", name,
                "binary and therefore testable for symmetry; a name that does not claim it "
                "makes this a hypothesis execution must confirm")

    for encoder, decoder in _round_trip_pairs(list(by_name)):
        add("ROUND_TRIP", encoder, f"`{decoder}` is named as the inverse of `{encoder}`",
            partner=decoder)

    return {
        "schema": SCHEMA,
        "module": module_name,
        "functions": accepted,
        "declined": declined,
        "invariants": invariants,
    }


# --------------------------------------------------------------------------- #
# Layer 2: input grids. Deterministic, JSON-safe, derived from the signature.
# --------------------------------------------------------------------------- #
def _pool_for(param: Mapping[str, Any]) -> tuple[Any, ...]:
    kind = param.get("kind")
    return POOLS[kind] if kind in POOLS else UNKNOWN_POOL


def build_grid(
    required: Sequence[Mapping[str, Any]],
    limit: int = MAX_INPUTS_PER_FUNCTION,
    extra_pools: Mapping[str, Sequence[Any]] | None = None,
) -> list[dict[str, Any]]:
    """`[{'args': [...]}]` -- the inputs this instrument will call a function with.

    `extra_pools` is how real geometry enters. A toy pool asks a function about `"a/b/c"`; a
    pool drawn from the tree asks it about the paths and lines this repository actually
    contains. Every instrument this project has built has come out weaker on invented inputs
    than on the real ones, so the caller may supply them and they are tried first.
    """
    extra = extra_pools or {}
    arity = len(required)
    if arity == 0:
        return [{"args": []}]

    def pool_for(param: Mapping[str, Any]) -> tuple[Any, ...]:
        kind = param.get("kind")
        supplied = tuple(extra.get(kind or "any") or ())
        toy = _pool_for(param)
        if not supplied:
            return toy
        merged: list[Any] = []
        for index in range(max(len(supplied), len(toy))):
            if index < len(supplied):
                merged.append(supplied[index])
            if index < len(toy):
                merged.append(toy[index])
        return tuple(merged)

    first = pool_for(required[0])
    if arity == 1:
        return [{"args": [value]} for value in first[:limit]]
    second = pool_for(required[1])
    return [
        {"args": [first[index % len(first)], second[(index * 3) % len(second)]]}
        for index in range(min(limit, len(first) * 2))
    ]


# --------------------------------------------------------------------------- #
# Layer 2 implementation: one bounded child, one temporary directory
# --------------------------------------------------------------------------- #
class _ExecutionTimeout(BaseException):
    """Raised inside the child to escape a call that will not return."""


_RAISED = "__RAISED__:"


def _call(fn: Any, args: Sequence[Any], timeout: float) -> tuple[str, Any]:
    """Call, and record a raise or a hang as an observation rather than a crash."""
    signal = __import__("signal")
    previous = None
    if hasattr(signal, "setitimer"):
        def _alarm(_signum: int, _frame: Any) -> None:
            raise _ExecutionTimeout()

        previous = signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return "OK", fn(*args)
    except _ExecutionTimeout:
        return "TIMEOUT", None
    except BaseException as exc:  # noqa: BLE001 - a raise is an observation, not a crash
        return _RAISED + type(exc).__name__, None
    finally:
        if hasattr(signal, "setitimer"):
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return "<" + type(value).__name__ + ">"


def _same(left: Any, right: Any) -> bool:
    if isinstance(left, float) and isinstance(right, float):
        import math

        if math.isnan(left) and math.isnan(right):
            return True
        return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-12)
    return left == right


class _NoThird:
    pass


_NO_THIRD = _NoThird()


def _third_value(second: Any) -> Any:
    """A third operand of the same kind, so `(a.b).c` and `a.(b.c)` are both meaningful."""
    if isinstance(second, bool):
        return not second
    if isinstance(second, int):
        return second + 1
    if isinstance(second, float):
        return second + 1.0
    if isinstance(second, str):
        return second + "c"
    if isinstance(second, list):
        return list(second) + [1]
    if isinstance(second, tuple):
        return tuple(second) + (1,)
    return _NO_THIRD


def _load_module(source: str, name: str, directory: pathlib.Path) -> Any:
    import importlib.util

    path = directory / (name + ".py")
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_subject_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reference(module_ref: str, attr: str) -> Any:
    import importlib

    return getattr(importlib.import_module(module_ref), attr)


def _precondition(kind: str, args: Sequence[Any]) -> str | None:
    """Why this law is not even defined on these arguments -- decided before calling.

    Calling first would record a `TypeError` from Python's own type rules as a violation of a
    law about the function, which is exactly the confusion `COMMUTATIVITY` had on
    `"a" + 12`.
    """
    if kind in ("COMMUTATIVITY", "ASSOCIATIVITY"):
        if len(args) != 2:
            return "NOT_BINARY"
        if type(args[0]) is not type(args[1]):
            return "NOT_A_HOMOGENEOUS_PAIR"
        if kind == "COMMUTATIVITY" and args[0] == args[1]:
            return "NOT_A_HOMOGENEOUS_DISTINCT_PAIR"
        return None
    if kind == "PERMUTATION_INVARIANT":
        items = args[0] if args else None
        if not isinstance(items, (list, tuple)) or len(items) < 2:
            return "NOT_A_SEQUENCE_OF_TWO"
        return None
    if kind in ("MULTISET_PRESERVED", "SET_PRESERVED"):
        items = args[0] if args else None
        if not isinstance(items, (list, tuple)):
            return "NOT_A_SEQUENCE"
        return None
    return None


def _evaluate(invariant: Mapping[str, Any], functions: Mapping[str, Any],
              args: Sequence[Any], timeout: float) -> dict[str, Any]:
    """Run one law on one input. `holds` is None when the law is undefined on that input."""
    kind = invariant["kind"]
    function = functions.get(invariant["function"])
    if function is None:
        return {"holds": None, "why": "FUNCTION_ABSENT"}
    undefined = _precondition(kind, args)
    if undefined is not None:
        return {"holds": None, "why": undefined}

    status, value = _call(function, args, timeout)
    if status != "OK":
        return {"holds": None, "why": status, "status": status}

    if kind == "TOTALITY":
        return {"holds": True, "value": _jsonable(value)}

    if kind == "IDEMPOTENCE":
        status_two, value_two = _call(function, (value,), timeout)
        if status_two != "OK":
            return {"holds": None, "why": "SECOND_APPLICATION_" + status_two}
        return {"holds": _same(value, value_two),
                "first": _jsonable(value), "second": _jsonable(value_two)}

    if kind == "INVOLUTION":
        status_two, value_two = _call(function, (value,), timeout)
        if status_two != "OK":
            return {"holds": None, "why": "SECOND_APPLICATION_" + status_two}
        return {"holds": _same(value_two, list(args)[0]),
                "once": _jsonable(value), "twice": _jsonable(value_two)}

    if kind == "ROUND_TRIP":
        decoder = functions.get(invariant["partner"])
        if decoder is None:
            return {"holds": None, "why": "PARTNER_ABSENT"}
        status_two, value_two = _call(decoder, (value,), timeout)
        if status_two != "OK":
            return {"holds": None, "why": "DECODER_" + status_two}
        return {"holds": _same(value_two, list(args)[0]),
                "encoded": _jsonable(value), "decoded": _jsonable(value_two)}

    if kind == "MULTISET_PRESERVED":
        source_items = list(args)[0] if args else None
        if not isinstance(source_items, (list, tuple)) or not isinstance(value, (list, tuple)):
            return {"holds": None, "why": "NOT_A_SEQUENCE"}
        return {"holds": sorted(map(repr, value)) == sorted(map(repr, source_items)),
                "output": _jsonable(value)}

    if kind == "SET_PRESERVED":
        source_items = list(args)[0] if args else None
        if not isinstance(source_items, (list, tuple)) or not isinstance(value, (list, tuple)):
            return {"holds": None, "why": "NOT_A_SEQUENCE"}
        return {"holds": set(map(repr, value)) == set(map(repr, source_items)),
                "output": _jsonable(value)}

    if kind == "PERMUTATION_INVARIANT":
        items = list(args)[0] if args else None
        if not isinstance(items, (list, tuple)) or len(items) < 2:
            return {"holds": None, "why": "NOT_A_SEQUENCE_OF_TWO"}
        rotated = list(items)[1:] + list(items)[:1]
        reversed_items = list(reversed(list(items)))
        status_two, value_two = _call(function, (rotated,), timeout)
        status_three, value_three = _call(function, (reversed_items,), timeout)
        if status_two != "OK" or status_three != "OK":
            return {"holds": None, "why": "PERMUTED_" + status_two + "/" + status_three}
        return {"holds": _same(value, value_two) and _same(value, value_three),
                "original": _jsonable(value), "rotated": _jsonable(value_two),
                "reversed": _jsonable(value_three)}

    if kind == "ASSOCIATIVITY":
        if len(args) != 2:
            return {"holds": None, "why": "NOT_BINARY"}
        first, second = args[0], args[1]
        third = _third_value(second)
        if third is _NO_THIRD:
            return {"holds": None, "why": "NO_THIRD_OPERAND"}
        status_left_inner, left_inner = _call(function, (first, second), timeout)
        status_right_inner, right_inner = _call(function, (second, third), timeout)
        if status_left_inner != "OK" or status_right_inner != "OK":
            return {"holds": None, "why": "INNER_APPLICATION_" + status_left_inner}
        status_left, left_grouped = _call(function, (left_inner, third), timeout)
        status_right, right_grouped = _call(function, (first, right_inner), timeout)
        if status_left != "OK" or status_right != "OK":
            return {"holds": None, "why": "OUTER_APPLICATION_" + status_left + "/" + status_right}
        return {"holds": _same(left_grouped, right_grouped),
                "left_grouped": _jsonable(left_grouped), "right_grouped": _jsonable(right_grouped)}

    if kind == "PERMUTATION_INVARIANT":
        if _distinct("original", defined) < 2:
            return 0
        return len(defined)
    if kind == "ASSOCIATIVITY":
        if _distinct("left_grouped", defined) < 2:
            return 0
        homogeneous = [row for row in defined if len(row["args"]) == 2
                       and type(row["args"][0]) is type(row["args"][1])]
        return len(homogeneous)
    if kind == "COMMUTATIVITY":
        if len(args) != 2:
            return {"holds": None, "why": "NOT_BINARY"}
        # Symmetry is not implied for a heterogeneous operator: `a + b` is symmetric on
        # numbers and not on `"a" + 12`. Claiming it there would be a law about Python's
        # type rules, not about this function.
        if type(args[0]) is not type(args[1]) or args[0] == args[1]:
            return {"holds": None, "why": "NOT_A_HOMOGENEOUS_DISTINCT_PAIR"}
        status_two, value_two = _call(function, (args[1], args[0]), timeout)
        if status_two != "OK":
            return {"holds": None, "why": "SWAPPED_" + status_two}
        return {"holds": _same(value, value_two),
                "forward": _jsonable(value), "swapped": _jsonable(value_two)}

    if kind == "STDLIB_DIFFERENTIAL":
        reference = _reference(invariant["reference_module"], invariant["reference_attr"])
        status_two, value_two = _call(reference, args, timeout)
        if status_two != "OK":
            return {"holds": None, "why": "REFERENCE_" + status_two}
        return {"holds": _same(value_two, value),
                "reference": _jsonable(value_two), "observed": _jsonable(value)}

    return {"holds": None, "why": "UNKNOWN_LAW"}


def _distinct(field: str, defined: list[dict[str, Any]]) -> int:
    return len({json.dumps(row.get(field), sort_keys=True, default=repr) for row in defined})


def _discriminating(kind: str, defined: list[dict[str, Any]]) -> int:
    """How many inputs could have broken this law. Zero means the law proves nothing.

    A function that returns the same value on every input makes almost every law vacuously
    true: `isabs` over a grid with no absolute path is a constant `False`, so it is trivially
    its own fixed point and trivially round-trips. Requiring at least two distinct results is
    what stops the instrument from counting a tautology as knowledge.
    """
    if kind == "TOTALITY":
        return len(defined)
    if kind == "IDEMPOTENCE":
        if _distinct("first", defined) < 2:
            return 0
        return sum(1 for row in defined if not _same(row.get("first"), row["args"][0]))
    if kind == "INVOLUTION":
        if _distinct("once", defined) < 2:
            return 0
        return sum(1 for row in defined if not _same(row.get("once"), row["args"][0]))
    if kind == "ROUND_TRIP":
        if _distinct("encoded", defined) < 2:
            return 0
        return sum(1 for row in defined if not _same(row.get("encoded"), row["args"][0]))
    if kind in ("MULTISET_PRESERVED", "SET_PRESERVED"):
        if _distinct("output", defined) < 1:
            return 0
        return sum(1 for row in defined
                   if row.get("output") is not None and row["args"][0] is not None
                   and row.get("output") != row["args"][0])
    if kind == "PERMUTATION_INVARIANT":
        if _distinct("original", defined) < 2:
            return 0
        return len(defined)
    if kind == "ASSOCIATIVITY":
        if _distinct("left_grouped", defined) < 2:
            return 0
        homogeneous = [row for row in defined if len(row["args"]) == 2
                       and type(row["args"][0]) is type(row["args"][1])]
        return len(homogeneous)
    if kind == "COMMUTATIVITY":
        distinct = {json.dumps(row.get("forward"), sort_keys=True) for row in defined}
        swapped_pairs = [row for row in defined if len(row["args"]) == 2 and row["args"][0] != row["args"][1]]
        return len(swapped_pairs) if len(distinct) >= 2 else 0
    if kind == "STDLIB_DIFFERENTIAL":
        distinct = {json.dumps(row.get("reference"), sort_keys=True) for row in defined}
        return len(defined) if len(distinct) >= 2 else 0
    return 0


def confirm_and_judge(kernel: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Confirm every law on the baseline, then let only the confirmed ones judge variants."""
    timeout = float(payload.get("call_timeout_s") or 0.5)
    directory = pathlib.Path(payload["workdir"])
    baseline = kernel._load_module(payload["baseline_source"], "baseline", directory)
    base_functions = {name: getattr(baseline, name) for name in payload["function_names"]
                      if hasattr(baseline, name)}

    confirmations: list[dict[str, Any]] = []
    witnesses: dict[str, list[dict[str, Any]]] = {}
    for invariant in payload["invariants"]:
        grid = payload["grids"].get(invariant["function"]) or []
        defined: list[dict[str, Any]] = []
        failing: list[dict[str, Any]] = []
        for entry in grid:
            outcome = kernel._evaluate(invariant, base_functions, entry["args"], timeout)
            outcome["args"] = entry["args"]
            if outcome.get("holds") is None:
                continue
            defined.append(outcome)
            if outcome.get("holds") is False:
                failing.append(outcome)
        row: dict[str, Any] = {
            "invariant_id": invariant["invariant_id"],
            "kind": invariant["kind"],
            "function": invariant["function"],
            "derivation": invariant["derivation"],
            "inputs_defined": len(defined),
        }
        if not defined:
            row["verdict"] = kernel.NOT_APPLICABLE
            row["discriminating_inputs"] = 0
            confirmations.append(row)
            continue
        if failing:
            row["verdict"] = kernel.REFUTED
            row["discriminating_inputs"] = 0
            row["first_disagreement"] = failing[0]
            confirmations.append(row)
            continue
        row["discriminating_inputs"] = kernel._discriminating(invariant["kind"], defined)
        row["verdict"] = kernel.CONFIRMED if row["discriminating_inputs"] else kernel.VACUOUS
        confirmations.append(row)
        if row["verdict"] == kernel.CONFIRMED:
            witnesses[invariant["invariant_id"]] = [{"args": item["args"]} for item in defined]

    confirmed = {row["invariant_id"] for row in confirmations if row["verdict"] == kernel.CONFIRMED}
    by_id = {invariant["invariant_id"]: invariant for invariant in payload["invariants"]}
    judged: list[dict[str, Any]] = []

    for variant in payload.get("variants") or []:
        record: dict[str, Any] = {
            "variant_id": variant["variant_id"],
            "operator": variant.get("operator"),
            "function": variant.get("function"),
            "killed_by": [],
            "counterexample": None,
        }
        try:
            module = kernel._load_module(variant["source"], "variant_" + str(variant["variant_id"]),
                                         directory)
        except BaseException as exc:  # noqa: BLE001 - an unimportable variant is a difference
            record["killed_by"] = ["IMPORT_FAILED"]
            record["counterexample"] = {"law": "IMPORT_FAILED", "why": type(exc).__name__}
            judged.append(record)
            continue
        functions = {name: getattr(module, name) for name in payload["function_names"]
                     if hasattr(module, name)}
        changed = variant.get("function")
        relevant = [
            invariant_id
            for invariant_id in sorted(confirmed)
            if changed in (by_id[invariant_id]["function"], by_id[invariant_id].get("partner"))
        ]
        record["laws_brought_to_bear"] = len(relevant)
        for invariant_id in relevant:
            invariant = by_id[invariant_id]
            kill = None
            for entry in witnesses.get(invariant_id, []):
                outcome = kernel._evaluate(invariant, functions, entry["args"], timeout)
                broken = outcome.get("holds") is False
                if invariant["kind"] == "TOTALITY" and str(outcome.get("why", "")).startswith(_RAISED):
                    broken = True
                if not broken:
                    continue
                kill = {
                    "law": invariant["kind"],
                    "invariant_id": invariant_id,
                    "derivation": invariant["derivation"],
                    "args": entry["args"],
                    "observed": outcome,
                }
                break
            if kill is not None:
                record["killed_by"].append(invariant_id)
                if record["counterexample"] is None:
                    record["counterexample"] = kill
        judged.append(record)

    return {"confirmations": confirmations, "judgements": judged}


_ACTIONS = {"confirm_and_judge": confirm_and_judge}


# --------------------------------------------------------------------------- #
# Parent side: one child, one temporary directory, no writes to the tree
# --------------------------------------------------------------------------- #
_CHILD_SOURCE = r'''
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("_brain_specification_from_structure", sys.argv[1])
kernel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kernel)
payload = json.loads(sys.stdin.read())
sys.stdout.write(json.dumps(kernel._ACTIONS[payload["action_name"]](kernel, payload)))
'''


def child_payload(
    *,
    module_name: str,
    baseline_source: str,
    derived: Mapping[str, Any],
    variants: Sequence[Mapping[str, Any]],
    call_timeout_s: float = 0.5,
    extra_pools: Mapping[str, Sequence[Any]] | None = None,
) -> dict[str, Any]:
    """Assemble the JSON the child executes. Kept public so a caller can inspect it."""
    functions = derived["functions"]
    return {
        "action_name": "confirm_and_judge",
        "module_name": module_name,
        "baseline_source": baseline_source,
        "function_names": [entry["name"] for entry in functions],
        "grids": {
            entry["name"]: build_grid(entry["required"], extra_pools=extra_pools)
            for entry in functions
        },
        "invariants": list(derived["invariants"]),
        "variants": list(variants),
        "call_timeout_s": call_timeout_s,
    }


def run_child(payload: Mapping[str, Any], timeout_s: float = 900.0) -> Any:
    """Execute the confirmation and the judgements in the bounded child."""
    with tempfile.TemporaryDirectory(prefix="brain_spec_structure_") as workdir:
        body = dict(payload)
        body["workdir"] = workdir
        process = subprocess.run(
            [sys.executable, "-B", "-c", _CHILD_SOURCE, str(pathlib.Path(__file__).resolve())],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=workdir,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
        )
    if process.returncode != 0 or not process.stdout.strip():
        raise RuntimeError(
            "SPECIFICATION_CHILD_FAILED:" + (process.stderr or process.stdout)[:400]
        )
    return json.loads(process.stdout)
