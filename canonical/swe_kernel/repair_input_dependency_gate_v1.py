"""Refuse a repair that stops reading an input the original function read.

WHY THIS EXISTS
---------------
Measured 2026-11-01: `solve_repository_closed_loop` "repaired" a two-file coupled billing bug by
replacing the function with

    def compute_invoice(items, disc):
        if disc % 2 == 0:
            return 110.0
        return 85.0

which passes the two visible tests, reports `PASS__CLOSED_LOOP_MULTISTEP_REPO_REPAIRED_AND_VERIFIED`,
and is wrong on every input the tests do not contain (`[100.0], 0.0` returns 110.0; the correct
answer is 100.0). 0/5 runs produced an honest repair.

The existing sabotage control did not catch it, and could not: it checks that the patched code is
*load-bearing* for the tests, which a lookup table is. It does not check that the patched code is
still a function of its inputs.

THE RULE
--------
A patch may not reduce a function's input dependency set. If `compute_invoice` read `items`
before the patch and does not read it after, the patch is refused, regardless of whether the
tests are green.

This is deliberately narrow and syntactic. It does not prove an edit correct; it refuses one
specific failure -- solving the tests by discarding the data. It can reject a legitimate patch
that removes a genuinely unused parameter read, which is why the refusal is a named status with
the offending parameter listed, and why `terminal_authority` is false: a caller may override with
knowledge this module does not have.

INPUTS ARE IDENTIFIED BY POSITION, NOT BY NAME
----------------------------------------------
Measured 2026-11-01 on the first version of this module: it compared parameter *names*, so a patch
that only renamed `def area(w, h)` to `def area(width, height)` was refused as
`PATCH_STOPPED_READING_ITS_INPUTS: area(h), area(w)`. Renaming a parameter is the most benign
honest edit there is, and refusing it would have made the gate an obstacle to correct work. The
first audit missed this because none of the seven real diffs it was run over happened to rename
anything -- a small sample that agreed with the gate for an uninteresting reason.

Inputs are therefore keyed by their position in the signature: the second positional parameter
before the patch is the second positional parameter after it, whatever it is called. A patch that
stops reading that slot is still refused; a patch that renames it now passes. Removing a parameter
outright still reduces the set, and is still refused -- conservatively, since a signature change
is a different question from a repair.

WHAT IT IS NOT
--------------
Not a verifier, not a held-out test generator, and not a correctness proof. A patch can lose no
dependencies and still be wrong. It closes exactly one hole and says so.
"""
from __future__ import annotations

import ast
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_REPAIR_INPUT_DEPENDENCY_GATE_V1"

PASS = "PASS"
REFUSED = "REFUSED"

_STDLIB_ROOTS = frozenset(getattr(sys, "stdlib_module_names", ())) | {
    "builtins",
    "__future__",
    "typing_extensions",
}


class GateError(RuntimeError):
    """Raised when the gate cannot decide honestly."""


def _slots(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, str]]:
    """(slot key, parameter name) for every parameter, in signature order.

    The slot key is positional so that renaming a parameter does not read as discarding it.
    """
    args = node.args
    slots: list[tuple[str, str]] = []
    for idx, a in enumerate(list(args.posonlyargs) + list(args.args)):
        slots.append((f"pos#{idx}", a.arg))
    for idx, a in enumerate(args.kwonlyargs):
        slots.append((f"kwonly#{idx}", a.arg))
    if args.vararg:
        slots.append(("vararg", args.vararg.arg))
    if args.kwarg:
        slots.append(("kwargs", args.kwarg.arg))
    return slots


def _body_loads(node: ast.AST) -> set[str]:
    """Names loaded in a function's own body, not in functions nested inside it."""
    out: set[str] = set()
    stack: list[ast.AST] = list(ast.iter_child_nodes(node))
    while stack:
        current = stack.pop()
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue  # a nested function has its own parameters
        if isinstance(current, ast.Name) and isinstance(current.ctx, ast.Load):
            out.add(current.id)
        stack.extend(ast.iter_child_nodes(current))
    return out


def parameter_use(source_text: str) -> dict[str, frozenset[str]]:
    """For every function in `source_text`, the parameters its body actually reads."""
    if not isinstance(source_text, str) or not source_text.strip():
        raise GateError("SOURCE_REQUIRED")
    try:
        tree = ast.parse(source_text)
    except SyntaxError as exc:
        raise GateError("SOURCE_NOT_PARSEABLE") from exc

    uses: dict[str, frozenset[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            loaded = _body_loads(node)
            uses[node.name] = frozenset(slot for slot, name in _slots(node) if name in loaded)
    return uses


def lost_dependencies(before_source: str, after_source: str) -> list[dict[str, str]]:
    """Parameters that a function read before the patch and no longer reads after it."""
    before = parameter_use(before_source)
    after = parameter_use(after_source)
    lost: list[dict[str, str]] = []
    for name, used_before in before.items():
        if name not in after:
            continue  # a deleted function is a different question, decided elsewhere
        for slot in sorted(used_before - after[name]):
            lost.append({
                "function": name,
                "slot": slot,
                "parameter": _names_by_slot(before_source, name).get(slot, slot),
            })
    return lost


def _names_by_slot(source_text: str, function_name: str) -> dict[str, str]:
    """Slot key -> parameter name, for reporting a refusal in the caller's own vocabulary."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return {slot: param for slot, param in _slots(node)}
    return {}


def _collect_non_stdlib_imports(node: ast.AST) -> tuple[dict[str, str], dict[str, str]]:
    """Return `(symbol_to_module, alias_to_module)` for non-stdlib imports in `node`'s scope."""
    sym_to_mod: dict[str, str] = {}
    alias_to_mod: dict[str, str] = {}
    stack: list[ast.AST] = list(ast.iter_child_nodes(node))
    while stack:
        cur = stack.pop()
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(cur, ast.ImportFrom):
            if cur.level and cur.level >= 1:
                mod_key = "." * cur.level + (cur.module or "")
            else:
                mod_name = cur.module or ""
                root_pkg = mod_name.split(".", 1)[0]
                if not root_pkg or root_pkg in _STDLIB_ROOTS:
                    continue
                mod_key = mod_name
            for al in cur.names:
                if al.name == "*":
                    continue
                sym_to_mod[al.asname or al.name] = mod_key
        elif isinstance(cur, ast.Import):
            for al in cur.names:
                root_pkg = al.name.split(".", 1)[0]
                if not root_pkg or root_pkg in _STDLIB_ROOTS:
                    continue
                local = al.asname if al.asname else root_pkg
                alias_to_mod[local] = al.name if al.asname else root_pkg
        else:
            stack.extend(ast.iter_child_nodes(cur))
    return sym_to_mod, alias_to_mod


def _local_shadows(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Names bound locally as parameters, assignments, or nested defs in `fn_node`."""
    shadows = {name for _, name in _slots(fn_node)}
    stack: list[ast.AST] = list(ast.iter_child_nodes(fn_node))
    while stack:
        cur = stack.pop()
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            shadows.add(cur.name)
            continue
        if isinstance(cur, ast.Lambda):
            continue
        if isinstance(cur, ast.Name) and isinstance(cur.ctx, ast.Store):
            shadows.add(cur.id)
        stack.extend(ast.iter_child_nodes(cur))
    return shadows


def _attr_root_name(node: ast.AST) -> str | None:
    cur = node
    while isinstance(cur, ast.Attribute):
        cur = cur.value
    if isinstance(cur, ast.Name):
        return cur.id
    return None


def imported_callee_use(
    source_text: str,
    *,
    inherited_symbols: dict[str, str] | None = None,
    inherited_aliases: dict[str, str] | None = None,
    require_call: bool = True,
) -> dict[str, dict[str, str]]:
    """For every function in `source_text`, map non-stdlib imported module -> witness callee.

    When `require_call=True` (used on `before_source`), only actual `ast.Call` invocations of
    non-stdlib imported symbols/modules register an obligation, so unused imports or imported
    constants never create obligations. When `require_call=False` (used on `after_source`),
    higher-order callback references (`map(apply_discount, ...)`) also satisfy the obligation.
    """
    if not isinstance(source_text, str) or not source_text.strip():
        raise GateError("SOURCE_REQUIRED")
    try:
        tree = ast.parse(source_text)
    except SyntaxError as exc:
        raise GateError("SOURCE_NOT_PARSEABLE") from exc

    mod_syms = dict(inherited_symbols or {})
    mod_aliases = dict(inherited_aliases or {})
    top_syms, top_aliases = _collect_non_stdlib_imports(tree)
    mod_syms.update(top_syms)
    mod_aliases.update(top_aliases)

    out: dict[str, dict[str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        fn_syms = dict(mod_syms)
        fn_aliases = dict(mod_aliases)
        local_syms, local_aliases = _collect_non_stdlib_imports(node)
        fn_syms.update(local_syms)
        fn_aliases.update(local_aliases)
        shadows = _local_shadows(node)

        used_modules: dict[str, str] = {}
        stack: list[ast.AST] = list(ast.iter_child_nodes(node))
        while stack:
            cur = stack.pop()
            if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(cur, ast.Call):
                func = cur.func
                if isinstance(func, ast.Name) and func.id not in shadows and func.id in fn_syms:
                    used_modules.setdefault(fn_syms[func.id], func.id)
                elif isinstance(func, ast.Attribute):
                    root_nm = _attr_root_name(func.value)
                    if root_nm and root_nm not in shadows and (root_nm in fn_aliases or root_nm in fn_syms):
                        mod_origin = fn_aliases.get(root_nm) or fn_syms[root_nm]
                        used_modules.setdefault(mod_origin, f"{root_nm}.{func.attr}")
            elif not require_call:
                if isinstance(cur, ast.Name) and isinstance(cur.ctx, ast.Load):
                    if cur.id not in shadows and cur.id in fn_syms:
                        used_modules.setdefault(fn_syms[cur.id], cur.id)
                elif isinstance(cur, ast.Attribute) and isinstance(cur.ctx, ast.Load):
                    root_nm = _attr_root_name(cur.value)
                    if root_nm and root_nm not in shadows and (root_nm in fn_aliases or root_nm in fn_syms):
                        mod_origin = fn_aliases.get(root_nm) or fn_syms[root_nm]
                        used_modules.setdefault(mod_origin, f"{root_nm}.{cur.attr}")
            stack.extend(ast.iter_child_nodes(cur))
        out[node.name] = used_modules
    return out


def lost_imported_callees(before_source: str, after_source: str) -> list[dict[str, str]]:
    """Non-stdlib imported callees a function invoked before the patch and severed after it.

    Measured 2026-11-13 on the coupled two-file billing defect (`billing/invoice.py` +
    `billing/discounts.py`): bottom-up observational synthesis replaced `compute_invoice` with
    `return (sum(items) - disc)`, reading both formal parameters (`items`, `disc`) while
    deleting the call to `from billing.discounts import apply_discount` and leaving
    `billing/discounts.py` (`return price + disc`) broken. Keying by origin module allows
    swapping sibling helpers from the same module (`encode` -> `decode`) and never restricts
    stdlib helpers (`math`, `itertools`), while refusing cross-module call-graph amputation.
    """
    if not isinstance(before_source, str) or not before_source.strip():
        raise GateError("SOURCE_REQUIRED")
    if not isinstance(after_source, str) or not after_source.strip():
        raise GateError("SOURCE_REQUIRED")
    try:
        before_tree = ast.parse(before_source)
    except SyntaxError as exc:
        raise GateError("SOURCE_NOT_PARSEABLE") from exc
    inh_syms, inh_aliases = _collect_non_stdlib_imports(before_tree)

    before_calls = imported_callee_use(before_source, require_call=True)
    after_uses = imported_callee_use(
        after_source,
        inherited_symbols=inh_syms,
        inherited_aliases=inh_aliases,
        require_call=False,
    )
    lost: list[dict[str, str]] = []
    for fn_name, before_mods in before_calls.items():
        if fn_name not in after_uses:
            continue
        after_mods = after_uses[fn_name]
        for mod_key in sorted(set(before_mods) - set(after_mods)):
            lost.append({
                "function": fn_name,
                "module": mod_key,
                "callee": before_mods[mod_key],
            })
    return lost


def gate(before_source: str, after_source: str) -> dict[str, Any]:
    """Decide whether the patch keeps every input and non-stdlib callee dependency."""
    try:
        lost = lost_dependencies(before_source, after_source)
        lost_callees = lost_imported_callees(before_source, after_source)
    except GateError as exc:
        return {
            "schema": SCHEMA,
            "status": REFUSED,
            "reason": str(exc),
            "lost": [],
            "lost_callees": [],
            "terminal_authority": False,
        }
    if lost:
        listed = ", ".join(f"{item['function']}({item['parameter']})" for item in lost)
        return {
            "schema": SCHEMA,
            "status": REFUSED,
            "reason": "PATCH_STOPPED_READING_ITS_INPUTS: " + listed,
            "lost": lost,
            "lost_callees": lost_callees,
            "terminal_authority": False,
        }
    if lost_callees:
        listed_callees = ", ".join(f"{item['function']}({item['callee']})" for item in lost_callees)
        return {
            "schema": SCHEMA,
            "status": REFUSED,
            "reason": "PATCH_STOPPED_CALLING_IMPORTED_DEPENDENCY: " + listed_callees,
            "lost": [],
            "lost_callees": lost_callees,
            "terminal_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": PASS,
        "reason": "INPUT_DEPENDENCIES_PRESERVED",
        "lost": [],
        "lost_callees": [],
        "terminal_authority": False,
    }


def semantic_sensitivity_gate(
    before_source: str,
    after_source: str,
    *,
    function_name: str,
    probe_pairs: list[tuple[tuple[Any, ...], tuple[Any, ...]]],
    expected_direction_by_pair: list[str] | None = None,
) -> dict[str, Any]:
    """Behavioral input-sensitivity & directional monotonicity gate beyond syntactic parameter reads.

    Directly closes `REPAIR_ADMISSION_KNOWN_COUNTEREXAMPLE_20261101_V1`:
    catches wrong-operator patches that syntactically read every parameter (such as
    `total * 100.0 / disc`, which crashes on `disc=0` or increases instead of decreasing
    as discount increases) by verifying finite evaluation and directional sensitivity
    across paired perturbations `(x_low, x_high)`.
    """
    from canonical.swe_kernel.meta_circular_organ_graph_v1 import compile_organ_namespace

    base_verdict = gate(before_source, after_source)
    if base_verdict["status"] != PASS:
        return base_verdict
    try:
        _, ns = compile_organ_namespace(after_source)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": REFUSED,
            "reason": f"PATCH_NOT_PURE_EXECUTABLE:{exc}",
            "lost": [],
            "terminal_authority": False,
        }
    fn = ns.get(function_name)
    if not callable(fn):
        return {
            "schema": SCHEMA,
            "status": REFUSED,
            "reason": f"FUNCTION_MISSING:{function_name}",
            "lost": [],
            "terminal_authority": False,
        }
    for idx, (inp_a, inp_b) in enumerate(probe_pairs):
        try:
            out_a = fn(*inp_a)
            out_b = fn(*inp_b)
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "status": REFUSED,
                "reason": f"PATCH_CRASHED_ON_PERTURBATION_PROBE:{type(exc).__name__}",
                "probe_index": idx,
                "terminal_authority": False,
            }
        if out_a == out_b:
            return {
                "schema": SCHEMA,
                "status": REFUSED,
                "reason": "PATCH_INSENSITIVE_TO_INPUT_PERTURBATION",
                "probe_index": idx,
                "terminal_authority": False,
            }
        if expected_direction_by_pair and idx < len(expected_direction_by_pair):
            direction = expected_direction_by_pair[idx]
            if direction == "decreasing" and not (out_b < out_a):
                return {
                    "schema": SCHEMA,
                    "status": REFUSED,
                    "reason": "PATCH_VIOLATES_MONOTONIC_DIRECTION:expected_decreasing",
                    "probe_index": idx,
                    "terminal_authority": False,
                }
            if direction == "increasing" and not (out_b > out_a):
                return {
                    "schema": SCHEMA,
                    "status": REFUSED,
                    "reason": "PATCH_VIOLATES_MONOTONIC_DIRECTION:expected_increasing",
                    "probe_index": idx,
                    "terminal_authority": False,
                }
    return {
        "schema": SCHEMA,
        "status": PASS,
        "reason": "INPUT_DEPENDENCIES_AND_SEMANTIC_SENSITIVITY_VERIFIED",
        "lost": [],
        "terminal_authority": False,
    }
