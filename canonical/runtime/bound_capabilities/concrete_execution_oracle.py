"""Bounded, concrete contract witnesses for a safe pure-Python numeric subset.

Source is parsed and interpreted by the same restricted expression engine used
by the Hypothesis adapter. It is never imported or executed, and a finite clean
sample does not prove correctness. This oracle is not independent of that
Hypothesis adapter because they share the expression interpreter.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Any

SCHEMA = "CONTRACT_VIOLATION_ORACLE_CONCRETE_V1"
PROVIDES = ["evidence.concrete_contract_violation"]
INPUTS = ["source.python_function_with_docstring_contract"]
MODEL_DEPENDENCY_COUNT = 0
_SAMPLE = (-8, -3, -1, 0, 1, 2, 3, 5, 7, 11, 16, 100, -100)


def _load_safe_contract():
    path = pathlib.Path(__file__).with_name("evidence_oracle_hypothesis_v1.py")
    spec = importlib.util.spec_from_file_location("_brain_safe_contract_expressions", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("SAFE_CONTRACT_INTERPRETER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CONTRACT = _load_safe_contract()


def _result(status: str, checked: int, violations: list[dict[str, Any]],
            posts: list[str], sample_size: int, reason: str = "") -> dict[str, Any]:
    result = {"status": status, "violations": violations, "checked": checked,
              "posts": posts, "sample_size": sample_size, "proves_absence": False,
              "engine": "RESTRICTED_NUMERIC_AST_INTERPRETER",
              "independent_of_hypothesis_adapter": False}
    if reason:
        result["reason"] = reason
    return result


def check_source(source: str, sample: tuple | list = _SAMPLE) -> dict[str, Any]:
    """Return concrete witnesses, or an explicit unsupported/indeterminate result."""
    if type(sample) not in (list, tuple) or len(sample) > 10000:
        raise ValueError("INVALID_SAMPLE")
    if not isinstance(source, str):
        return _result("UNSUPPORTED_SOURCE", 0, [], [], len(sample), "SOURCE_NOT_TEXT")
    try:
        arg, expression, pre, post = _CONTRACT._parse(source)
    except (_CONTRACT._Unsupported, RecursionError, UnicodeError) as exc:
        return _result("UNSUPPORTED_SOURCE", 0, [], [], len(sample), str(exc))
    posts = [text for text, _ in post]
    checked = 0
    violations: list[dict[str, Any]] = []
    for value in sample:
        try:
            value = _CONTRACT._number(value)
            env = {arg: value}
            if not all(bool(_CONTRACT._interpret(cond, env)) for cond in pre):
                continue
        except (_CONTRACT._Unsupported, ArithmeticError, TypeError, RecursionError) as exc:
            return _result("UNSUPPORTED_EVALUATION", checked, [], posts, len(sample), str(exc))
        checked += 1
        try:
            returned = _CONTRACT._interpret(expression, env)
        except _CONTRACT._Unsupported as exc:
            return _result("UNSUPPORTED_EVALUATION", checked, [], posts, len(sample), str(exc))
        except (ArithmeticError, TypeError, ValueError) as exc:
            # A postcondition describes returned values. Without an explicit
            # supported exception contract, raising is not itself a witness.
            return _result("UNSUPPORTED_EVALUATION", checked, [], posts, len(sample),
                           "FUNCTION_EXPRESSION_RAISED:" + type(exc).__name__)
        env.update({"_": returned, "result": returned, "__return__": returned})
        for text, condition in post:
            try:
                holds = bool(_CONTRACT._interpret(condition, env))
            except (_CONTRACT._Unsupported, ArithmeticError, TypeError, ValueError, RecursionError) as exc:
                return _result("UNSUPPORTED_EVALUATION", checked, [], posts, len(sample), str(exc))
            if not holds:
                violations.append({"input": value, "post": text, "returned": returned})
    status = ("CONTRACT_VIOLATION_FOUND" if violations else
              "NO_COUNTEREXAMPLE_IN_SAMPLE" if checked else
              "NO_INPUTS_SATISFY_PRECONDITIONS" if sample else "NO_INPUTS_CHECKED")
    return _result(status, checked, violations, posts, len(sample))


def run(args: dict, root: str) -> dict:
    args = dict(args or {})
    source = args.get("source")
    if source is None:
        repo = pathlib.Path(root).resolve()
        target = (repo / str(args.get("target_path") or "")).resolve()
        if target == repo or repo not in target.parents:
            raise ValueError("PATH_OUTSIDE_ROOT")
        if not target.is_file():
            raise ValueError("ORACLE_TARGET_MISSING")
        source = target.read_text(encoding="utf-8")
    sample = _SAMPLE if args.get("sample") is None else args["sample"]
    out = check_source(source, sample)
    out.update({"schema": SCHEMA, "provides": PROVIDES,
                "model_dependency_count": MODEL_DEPENDENCY_COUNT})
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(run({"target_path": sys.argv[1]}, "."), indent=2))
