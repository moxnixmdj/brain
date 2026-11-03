"""Noticing that your own answer is suspect -- without being told.

THE GAP THIS CLOSES
-------------------
Every earlier organ in this project required an outsider to say "that was wrong". The creature
could revise a concept, attribute a failure, and retire a part, but only once told. This module
supplies the trigger, and it is careful about one thing:

**It does not read the answer.** It sees the body the synthesizer produced, the parameter names it
was asked for, and a domain grid built from the arity. It never sees withheld points or expected
values. That is the difference between noticing a failure and being told about one.

WHAT IT CAN SEE
---------------
1. `partiality` -- the body raises, or returns non-finite, somewhere in its own domain.
2. `branch_imbalance` -- a conditional whose arm fires on a tiny slice of the domain. Measured
   example: `if not (min(v, l)): return ((v / h) + 0.5)` puts the entire real computation in a branch
   that fires on 1 of 30 probes; the other arm returns `abs(l - 0.5)`, which ignores `v` and `h`.
3. `dead_branch` -- an arm that never fires at all.

WHAT IT CANNOT SEE, AND THIS IS THE POINT
-----------------------------------------
A body can be confidently wrong with none of these defects. Every signal here is a *symptom of
desperation*: a search that cannot find the real structure produces special cases, crashes, or
ignores its inputs. A search that finds a clean wrong answer -- well-formed, total, balanced, and
false -- produces nothing this audit can see. I expect that miss and say so in advance.

Authority: NONE. Pure Python. The AST is rewritten for tracing, never `eval`'d with a global hook.
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.concept_library_v1 import _generate_probe_grids

SCHEMA = "PROJECT_BRAIN_SELF_AUDIT_V1"

# A branch that fires on less than this fraction of the domain is treated as a special case rather
# than a rule. Chosen from the measured case (1 of 30 = 0.033) with headroom; not derived.
IMBALANCE_THRESHOLD = 0.15

SAFE_BUILTINS = {k: getattr(__builtins__, k) if not isinstance(__builtins__, dict)
                 else __builtins__[k]
                 for k in ("abs", "min", "max", "round", "int", "float", "len")}


def _split(body: str) -> tuple[list[str], list[str]]:
    """Separate helper `def` blocks from the function body (same rule as generalization_check)."""
    from canonical.runtime.generalization_check_v1 import _split_body

    return _split_body(body)


def _parse_returns(outer: list[str]) -> list[ast.Return]:
    """Return the `Return` nodes in the outer function body, in source order."""
    src = "if True:\n" + "\n".join("    " + line for line in outer)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    found: list[ast.Return] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            found.append(node)
    found.sort(key=lambda n: getattr(n, "lineno", 0))
    return found


def _instrumented_source(helpers: list[str], outer: list[str], n_returns: int,
                         params: Sequence[str]) -> str:
    """Rewrite the body so every `return X` records which branch fired, without a trace hook.

    A global `sys.settrace` was used to explore this and is deliberately not used here: installing a
    process-wide hook from inside a creature's runtime is a side effect that can break unrelated
    tracing (test runners, profilers) and is not worth the coupling.
    """
    counter_index = 0

    class _Rewriter(ast.NodeTransformer):
        def __init__(self) -> None:
            self.index = 0

        def visit_Return(self, node: ast.Return) -> ast.AST:
            if node.value is None:
                return node
            idx = self.index
            self.index += 1
            call = ast.Call(func=ast.Name(id="__audit_hit", ctx=ast.Load()),
                            args=[ast.Constant(value=idx)], keywords=[])
            new_value = ast.Call(func=ast.Name(id="__audit_wrap", ctx=ast.Load()),
                                 args=[ast.Constant(value=idx), node.value], keywords=[])
            node.value = new_value
            ast.copy_location(node, node.value)
            _ = call
            return node

    src = "if True:\n" + "\n".join("    " + line for line in outer)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ""
    rewriter = _Rewriter()
    rewriter.visit(tree)
    ast.fix_missing_locations(tree)
    body_src = ast.unparse(tree)
    # Strip ONLY the synthetic `if True:` header and its single indent level. The first version
    # dedented every line starting with four spaces, which also stripped the indent inside the real
    # `if not min(v, l):` -- so the nested `return` came back to top level, the wrapper failed to
    # compile, and every branch count read 0. Found by printing the rewritten source, not by
    # trusting the flag: the flag looked right for the wrong reason.
    lines = body_src.splitlines()
    if lines and lines[0].strip() == "if True:":
        lines = [lines[0]] + [
            (line[4:] if line.startswith("    ") else line) for line in lines[1:]
        ]
    dedented = lines[1:] if lines and lines[0].strip() == "if True:" else lines
    _ = (counter_index, n_returns)
    return "\n".join(helpers) + ("\n\n" if helpers else "") + "\n".join(dedented)


def audit_body(body: str | None, params: Sequence[str], *, domain: str = "numeric") -> dict[str, Any]:
    """Structural self-audit. Returns signals and a verdict. Reads no expected values."""
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "params": list(params),
        "signals": {},
        "flag": False,
        "reasons": [],
        "saw_expected_values": False,
        "authority": "NONE",
    }
    if not body:
        report["signals"] = {"emitted": False}
        return report

    helpers, outer = _split(body)
    grid_entry = _generate_probe_grids(len(params))
    points = grid_entry[0][1] if grid_entry else []

    # ---- partiality ------------------------------------------------------------------ #
    try:
        from canonical.runtime.generalization_check_v1 import _compile_body

        fn = _compile_body(body, list(params))
    except Exception as exc:  # noqa: BLE001
        report["signals"] = {"compiles": False, "error": type(exc).__name__}
        report["flag"] = True
        report["reasons"].append("DOES_NOT_COMPILE")
        return report

    raises = 0
    nonfinite = 0
    for row in points:
        try:
            out = fn(*row)
        except Exception:  # noqa: BLE001
            raises += 1
            continue
        if isinstance(out, float) and (math.isnan(out) or math.isinf(out)):
            nonfinite += 1

    # ---- branch coverage ------------------------------------------------------------- #
    returns = _parse_returns(outer)
    reached: dict[int, int] = {i: 0 for i in range(len(returns))}
    traced_ok = False
    if len(returns) > 1 and points:
        src = _instrumented_source(helpers, outer, len(returns), params)
        if src:
            hits = [0] * len(returns)

            def _wrap(idx: int, value: Any) -> Any:
                hits[idx] += 1
                return value

            ns: dict[str, Any] = {"__builtins__": SAFE_BUILTINS, "__audit_wrap": _wrap}
            wrapper = ("def _audit_fn(" + ", ".join(params) + "):\n"
                       + "\n".join("    " + line for line in src.splitlines()))
            try:
                exec(compile(wrapper, "<audit>", "exec"), ns)  # noqa: S102
                audit_fn = ns["_audit_fn"]
                for row in points:
                    try:
                        audit_fn(*row)
                    except Exception:  # noqa: BLE001 - a raise here is already counted above
                        pass
                reached = {i: hits[i] for i in range(len(returns))}
                traced_ok = True
            except Exception:  # noqa: BLE001
                traced_ok = False
    _ = traced_ok

    total_hits = sum(reached.values())
    dead = [i for i, n in reached.items() if n == 0] if len(returns) > 1 else []
    fractions = {i: (n / total_hits) for i, n in reached.items() if total_hits} if total_hits else {}
    imbalanced = [i for i, frac in fractions.items()
                  if 0 < frac < IMBALANCE_THRESHOLD and len(returns) > 1]

    # ---- triviality ------------------------------------------------------------------ #
    ignored: list[str] = []
    if points:
        for i, name in enumerate(params):
            outcomes = set()
            for row in points:
                probe = list(row)
                probe[i] = (probe[i] + 7) if isinstance(probe[i], (int, float)) else probe[i]
                try:
                    outcomes.add(repr(fn(*probe)))
                except Exception:  # noqa: BLE001
                    outcomes.add("<raise>")
            if len(outcomes) == 1:
                ignored.append(str(name))

    report["signals"] = {
        "emitted": True,
        "compiles": True,
        "probes": len(points),
        "raises": raises,
        "nonfinite": nonfinite,
        "returns": len(returns),
        "branch_hits": reached,
        "branch_dead": dead,
        "branch_imbalanced": imbalanced,
        "ignored_params": ignored,
    }

    if raises or nonfinite:
        report["flag"] = True
        report["reasons"].append("PARTIAL_ON_OWN_DOMAIN")
    if dead:
        report["flag"] = True
        report["reasons"].append("DEAD_BRANCH")
    if imbalanced:
        report["flag"] = True
        report["reasons"].append("BRANCH_IMBALANCE")
    if ignored and len(ignored) < len(params):
        report["flag"] = True
        report["reasons"].append("IGNORES_PARAMETER")

    report["concludes"] = (
        "SUSPECT -- structural defect visible without reading the answer"
        if report["flag"] else
        "NO_STRUCTURAL_DEFECT_VISIBLE -- which is NOT a clean bill of health: a well-formed, total, "
        "balanced body that is simply false looks exactly like this"
    )
    return report
