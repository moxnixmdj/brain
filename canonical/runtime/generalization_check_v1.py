"""Does the synthesizer return a function or an interpolation? Check on points it never saw.

WHY THIS EXISTS
---------------
The 2026-11-04 semantic-join benchmark counted a held-out problem as "solved" when
`synthesize_python_function_body` returned a non-None body. Re-reading that body revealed it was:

    if not lo2:
        return ((s + 2) / hi2)
    return ((s - lo2) / 1)

which reproduces the three teaching examples and is not the target function. The counter could not
tell an interpolation from a formula, so every reach number this project has reported from that
counter is an upper bound, not a measurement.

This module supplies the missing check: hold points back, synthesize on the rest, and require the
returned body to agree at the withheld points. A body that only fits its examples is reported as
OVERFIT, not as a solve.

Authority: NONE. Pure Python `eval` over a closed builtin namespace, small numeric tuples, $0.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_GENERALIZATION_CHECK_V1"

SOLVED = "SOLVED"
OVERFIT = "OVERFIT"
UNREACHED = "UNREACHED"


def _split_body(body: str) -> tuple[list[str], list[str]]:
    """Separate leading helper `def` blocks from the final function body.

    This split is the whole bug fixed on 2026-11-04. `synthesize_python_function_body` returns
    concept-helpers already materialised, so a body using a learned concept looks like:

        def concept_640d4492(_v0, _v1, _v2):
            return (...)
        return (concept_640d4492(v, l, h) + 0.5)

    The first compiler wrapped EVERY line in the outer function, producing a nested `def` whose
    `return` belonged to the helper -- so a correct body was compiled into nonsense and reported
    as OVERFIT. That made a real reach gain look like a null result for one full round.
    """
    lines = body.splitlines()
    helpers: list[str] = []
    idx = 0
    while idx < len(lines):
        if not lines[idx].startswith("def "):
            break
        helpers.append(lines[idx])
        idx += 1
        while idx < len(lines) and (lines[idx].startswith((" ", "\t")) or not lines[idx].strip()):
            if not lines[idx].strip() and idx + 1 < len(lines) and not lines[idx + 1].startswith((" ", "\t")):
                break
            helpers.append(lines[idx])
            idx += 1
    return helpers, lines[idx:]


def _compile_body(body: str, param_names: Sequence[str]) -> Any:
    """Compile a synthesized body (helpers + final statements) into a callable."""
    helpers, outer = _split_body(body)
    if not outer:
        raise ValueError("NO_FUNCTION_BODY")
    src = "\n".join(helpers) + ("\n\n" if helpers else "")
    src += f"def _f({', '.join(param_names)}):\n" + "".join(
        "    " + line + "\n" for line in outer)
    import builtins as _bi

    safe = {k: getattr(_bi, k) for k in ("abs", "min", "max", "round", "int", "float", "len")
            if hasattr(_bi, k)}
    # ONE namespace, used as globals. Passing separate globals/locals put the helper `def` in
    # locals while `_f` resolved names in globals, so the concept call raised NameError and a
    # correct body was scored OVERFIT -- the same class of bug as the line-splitting one.
    ns: dict[str, Any] = {"__builtins__": safe}
    exec(compile(src, "<synth>", "exec"), ns)  # noqa: S102
    return ns["_f"]


def _agrees(got: Any, want: Any, tol: float = 1e-9) -> bool:
    if isinstance(got, bool) or isinstance(want, bool):
        return got == want
    if isinstance(got, (int, float)) and isinstance(want, (int, float)):
        return abs(float(got) - float(want)) <= tol * max(1.0, abs(float(want)))
    return got == want


def classify(body: str | None, param_names: Sequence[str],
             withheld: Sequence[tuple[tuple[Any, ...], Any]]) -> tuple[str, list[Any]]:
    """SOLVED only if the body agrees on every withheld point."""
    if not body:
        return UNREACHED, []
    try:
        fn = _compile_body(body, param_names)
    except Exception:  # noqa: BLE001 - a body that will not compile cannot generalise
        return OVERFIT, []
    observed: list[Any] = []
    for args, want in withheld:
        try:
            got = fn(*args)
        except Exception:  # noqa: BLE001
            return OVERFIT, observed
        observed.append(got)
        if not _agrees(got, want):
            return OVERFIT, observed
    return SOLVED, observed


def measure(problems: Sequence[dict[str, Any]],
            synth: Callable[..., str | None],
            *, max_weight: int = 4, extra_constants: Sequence[Any] = (),
            concept_library: Any | None = None) -> dict[str, Any]:
    """Run every problem with a train/withhold split and report the honest verdict."""
    rows: list[dict[str, Any]] = []
    for prob in problems:
        name = str(prob.get("name", "?"))
        params = list(prob["params"])
        train = list(prob["train"])
        withheld = list(prob["withheld"])
        body = synth(params, train, extra_constants=extra_constants,
                     max_weight=max_weight, concept_library=concept_library)
        verdict, observed = classify(body, params, withheld)
        rows.append({
            "problem": name,
            "verdict": verdict,
            "body": body,
            "withheld_expected": [w for _, w in withheld],
            "withheld_observed": observed,
        })
    return {
        "schema": SCHEMA,
        "rows": rows,
        "solved": sum(1 for r in rows if r["verdict"] == SOLVED),
        "overfit": sum(1 for r in rows if r["verdict"] == OVERFIT),
        "unreached": sum(1 for r in rows if r["verdict"] == UNREACHED),
        "total": len(rows),
        "authority": "NONE",
        "not_claimed": [
            "that a SOLVED verdict proves the target function -- it is agreement on the withheld "
            "points, and two structurally different formulas can agree there",
            "that OVERFIT means the search is weak -- it means this body does not generalise",
        ],
    }
