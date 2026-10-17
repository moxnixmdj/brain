"""Second independent oracle: concrete execution.

The CrossHair oracle answers "does a satisfying assignment exist?" by
symbolic execution over Z3.  This one answers "does it break when I run it?"
by actually calling the function on enumerated concrete inputs.

The two share no machinery, no solver and no assumptions.  That independence
is the entire point: an oracle that agrees with itself proves nothing.

Model dependency: 0.  This evaluates Python and arithmetic.  No network, no
model, no solver.
"""
from __future__ import annotations

import pathlib
import re
import sys

SCHEMA = "CONTRACT_VIOLATION_ORACLE_CONCRETE_V1"
PROVIDES = ["evidence.concrete_contract_violation"]
INPUTS = ["source.python_function_with_docstring_contract"]
MODEL_DEPENDENCY_COUNT = 0

_POST_RE = re.compile(r"^\s*(?:-\s*)?post(?:condition)?\s*:\s*(.+)$", re.I)

# Deliberately small.  A concrete oracle may only ever witness a violation, so
# a clean run is "no counterexample found in this sample", never "proven".
_SAMPLE = (-8, -3, -1, 0, 1, 2, 3, 5, 7, 11, 16, 100, -100)

_SAFE = {
    "abs": abs, "min": min, "max": max, "len": len,
    "sum": sum, "int": int, "float": float, "bool": bool,
}


def _posts(docstring: str) -> list[str]:
    out = []
    for line in (docstring or "").splitlines():
        m = _POST_RE.match(line)
        if m:
            out.append(m.group(1).strip())
    return out


def check_source(source: str, sample=_SAMPLE) -> dict:
    """Execute the function on concrete inputs.  Report the first witness."""
    ns: dict = {}
    exec(compile(source, "<instance>", "exec"), ns)  # noqa: S102
    fn = ns.get("f")
    if fn is None:
        raise ValueError("NO_FUNCTION_F")

    posts = _posts(fn.__doc__ or "")
    if not posts:
        return {
            "status": "NO_POSTCONDITION_PARSED",
            "violations": [],
            "checked": 0,
            "posts": [],
        }

    violations = []
    checked = 0
    for x in sample:
        try:
            result = fn(x)
        except Exception as exc:  # raising IS a contract failure
            violations.append({"input": x, "reason": f"raised {type(exc).__name__}"})
            checked += 1
            continue
        checked += 1
        env = dict(_SAFE)
        env.update({"x": x, "_": result, "__return__": result, "result": result})
        for post in posts:
            try:
                ok = bool(eval(post, {"__builtins__": {}}, env))  # noqa: S307
            except Exception as exc:
                violations.append({"input": x, "post": post,
                                   "reason": f"unevaluable: {type(exc).__name__}"})
                continue
            if not ok:
                violations.append({"input": x, "post": post, "returned": result})

    return {
        "status": "CONTRACT_VIOLATION_FOUND" if violations else "NO_COUNTEREXAMPLE_IN_SAMPLE",
        "violations": violations,
        "checked": checked,
        "posts": posts,
        "sample_size": len(sample),
    }


def run(args: dict, root: str) -> dict:
    args = dict(args or {})
    raw = args.get("source")
    if raw is None:
        target = pathlib.Path(str(args.get("target_path")))
        if not target.is_file():
            raise ValueError("ORACLE_TARGET_MISSING")
        raw = target.read_text()
    sample = tuple(args.get("sample") or _SAMPLE)
    out = check_source(raw, sample)
    out.update({
        "schema": SCHEMA,
        "provides": PROVIDES,
        "model_dependency_count": MODEL_DEPENDENCY_COUNT,
        # Honesty clause: absence of a witness is not proof.
        "proves_absence": False,
    })
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(run({"target_path": sys.argv[1]}, "."), indent=2))
