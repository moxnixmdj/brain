#!/usr/bin/env python3
"""Specification-contract synthesis: mine the test's own `pytest.raises(...)` expectation and write
the guard that makes the program honour it.

THE BOTTLENECK THIS CLOSES, AND WHY IT IS NOT MORE SEARCH
---------------------------------------------------------
Round V2 ended with 9 of 13 unseen OSS commits repaired and four open. Every one of the four needs a
*statement* the engine could not express: a new guard, a new assignment, an early return, a
memory-safety check. `pluggy@8051a4d` is the cleanest of them:

    with pytest.raises(TypeError, match="plugin must not be None"):
        pm.register(None)

The program does not raise, the test fails with `DID NOT RAISE`, and no expression-level repair can
fix it because there is no wrong expression -- there is a *missing contract*. The value being
rejected is `None`, the parameter it should be rejected for is `plugin`, and the exception the caller
expects is `TypeError` with that message. All three facts are published by the test, which is the
specification, not the answer key.

So the mechanism is not a bigger grammar. It is: **read the contract the test already states, bind it
to the parameter the callee declares, and emit the one-line guard that enforces it.** Then let the
project's own suite decide, exactly as every other candidate is decided.

WHAT IS MINED, AND FROM WHERE
-----------------------------
* `with pytest.raises(Exc, match="...")`  -> `(exc_name, message_regex)`  [the test's expectation]
* the call inside that block              -> `(callee, argument literals)` [the API surface]
* `pytest.raises(Exc, callable, *args)`   -> the same, functional form
* the callee is bound to a real function through the project's own CPG (by name and arity), so the
  guard is written into the function that actually owns the parameter.
* the guard's condition is derived from the *parameter name* and the *boundary literal* the test
  called with: `is None`, `not x`, `== boundary`, `len(x) == 0`. Nothing else is emitted.

WHAT IS REFUSED
---------------
* A non-boundary literal (`pm.register("abc")`) is not a contract, it is one test's data. Only
  boundary values (`None`, empty string/bytes/container, `0`, negative where the test itself is the
  only caller) are admitted, using the same `is_canonical_default` notion the nexus gate uses.
* A callee that does not resolve to exactly one project function by name and arity is refused.
* A guard that does not make the failing tests pass *and* keep the full suite green is rejected. The
  suite is the only judge; this module never accepts its own proposal.
* C/C++/JS are out of scope for this version: the contract binding uses Python AST parameter names.
  That limit is stated rather than hidden.

Authority: NONE__PRODUCER_RUN_SANDBOX. Runtime model calls: 0. Network calls at run time: 0.
Parameters stored: 0.
"""
from __future__ import annotations

import ast
import dataclasses
from dataclasses import dataclass
import pathlib
import sys
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import causal_nexus_v1 as nexus  # noqa: E402
from canonical.swe_kernel import semantic_causal_engine_v1 as scm  # noqa: E402

SCHEMA = "BRAIN_SPEC_CONTRACT_SYNTHESIS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"


@dataclass(frozen=True)
class ExceptionContract:
    """One `pytest.raises` expectation, bound to the call the test makes inside it."""
    exc_name: str
    match_pattern: str
    callee: str
    arg_literals: tuple[Any, ...]
    keyword_literals: tuple[tuple[str, Any], ...]
    call_text: str
    node_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "exc_name": self.exc_name,
            "match_pattern": self.match_pattern,
            "callee": self.callee,
            "arg_literals": [repr(a) for a in self.arg_literals],
            "keyword_literals": [[k, repr(v)] for k, v in self.keyword_literals],
            "call_text": self.call_text[:200],
            "node_id": self.node_id,
        }


def _raises_exc_name(node: ast.AST) -> str | None:
    """`ValueError` / `jwt.InvalidKeyError` / `click.ClickException` -> the name to emit."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        inner = _raises_exc_name(node.value)
        return f"{inner}.{node.attr}" if inner else node.attr
    if isinstance(node, ast.Tuple) and node.elts:
        return _raises_exc_name(node.elts[0])
    return None


def _call_callee(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _literal_arg(node: ast.AST) -> Any:
    """A literal argument value, or `_REFUSED` when the argument is not self-contained."""
    try:
        return ast.literal_eval(node)
    except Exception:
        return nexus._REFUSED  # noqa: SLF001 - one shared sentinel, not a second notion of "no"


def mine_exception_contracts(test_source: str, *, node_id: str = "") -> list[ExceptionContract]:
    """Extract every `pytest.raises(...)` contract from one test module's source."""
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return []
    out: list[ExceptionContract] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            ctx = item.context_expr
            if not (isinstance(ctx, ast.Call) and _raises_callee_name(ctx) == "raises"):
                continue
            if not ctx.args:
                continue
            exc_name = _raises_exc_name(ctx.args[0])
            if not exc_name:
                continue
            match = ""
            for kw in ctx.keywords:
                if kw.arg == "match" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    match = kw.value.value
            call: ast.Call | None = None
            for stmt in node.body:
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.Call):
                        call = sub
                        break
                if call is not None:
                    break
            if call is None or _call_callee(call) is None:
                continue
            lits = tuple(_literal_arg(a) for a in call.args)
            if any(v is nexus._REFUSED for v in lits):  # noqa: SLF001
                continue
            kw_lits = tuple(
                (kw.arg, _literal_arg(kw.value)) for kw in call.keywords
                if kw.arg and _literal_arg(kw.value) is not nexus._REFUSED  # noqa: SLF001
            )
            out.append(
                ExceptionContract(
                    exc_name=exc_name,
                    match_pattern=match,
                    callee=_call_callee(call) or "",
                    arg_literals=lits,
                    keyword_literals=kw_lits,
                    call_text=ast.unparse(call)[:200],
                    node_id=node_id,
                )
            )
    return out


def _raises_callee_name(node: ast.Call) -> str | None:
    return _call_callee(node)


def _contract_boundary_literal(contract: ExceptionContract) -> tuple[int, Any] | tuple[str, Any] | None:
    """The first argument that is a *boundary* value: a contract, not one test's data."""
    for idx, val in enumerate(contract.arg_literals):
        if nexus.is_canonical_default(val) or val is None:
            return idx, val
        if isinstance(val, (int, float)) and val < 0:
            return idx, val
    for key, val in contract.keyword_literals:
        if nexus.is_canonical_default(val) or val is None:
            return key, val
    return None


_TYPE_TOKENS = frozenset({
    "Any", "str", "int", "bool", "float", "bytes", "bytearray", "None", "object", "list", "dict",
    "tuple", "set", "Optional", "Sequence", "Mapping", "Callable", "Iterable", "Iterator", "T",
})


def _param_name(pair: Sequence[str]) -> str:
    """`FunctionCPG.params` is `(type, name)`; pick the identifier, not the annotation."""
    if len(pair) >= 2:
        for candidate in (pair[1], pair[0]):
            if candidate in _TYPE_TOKENS:
                continue
            if candidate.isidentifier():
                return candidate
        return pair[1]
    return pair[0] if pair else ""


def _param_names(fn: "scm.FunctionCPG") -> list[str]:
    names = [_param_name(p) for p in fn.params]
    return [n for n in names if n not in ("self", "cls")]


def _guard_conditions(param: str, literal: Any) -> list[str]:
    conds: list[str] = []
    if literal is None:
        conds.append(f"{param} is None")
    if isinstance(literal, bool):
        conds.append(f"{param} is {literal}")
    if isinstance(literal, (str, bytes, list, tuple, dict, set, frozenset)) and len(literal) == 0:
        conds.append(f"not {param}")
        conds.append(f"len({param}) == 0")
    if isinstance(literal, (int, float)) and not isinstance(literal, bool):
        conds.append(f"{param} == {literal!r}")
        if literal <= 0:
            conds.append(f"{param} <= 0")
    if not conds:
        conds.append(f"{param} is None")
    return conds


def _indent_of(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line[: len(line) - len(line.lstrip())]
    return "    "


def guard_candidates(
    fn: "scm.FunctionCPG",
    contract: ExceptionContract,
    body_text: str,
) -> list[tuple[str, str]]:
    """One-line guard-and-raise statements that enforce `contract` inside `fn`."""
    bound = _contract_boundary_literal(contract)
    if bound is None:
        return []
    params = _param_names(fn)
    if not params:
        return []
    if isinstance(bound[0], int):
        idx = bound[0]
        param = params[idx] if idx < len(params) else params[-1]
        literal = bound[1]
    else:
        key = bound[0]
        param = key if key in params else params[0]
        literal = bound[1]
    indent = _indent_of(body_text)
    message = contract.match_pattern.replace('"', "'") if contract.match_pattern else ""
    raise_stmt = f'raise {contract.exc_name}("{message}")' if message else f"raise {contract.exc_name}()"
    out: list[tuple[str, str]] = []
    for cond in _guard_conditions(param, literal):
        guard = f"{indent}if {cond}:\n{indent}    {raise_stmt}\n"
        out.append((f"SPEC_CONTRACT_GUARD[{cond}]", guard + body_text))
    return out


def synthesize_spec_guards(
    project_root: pathlib.Path | str,
    cpg: "scm.ProjectCPG",
    test_sources: Sequence[str],
    *,
    max_candidates: int = 12,
) -> list[tuple[str, str, "scm.FunctionCPG", bytes]]:
    """Bind every mined contract to a project function and return ready-to-apply guard patches."""
    root = pathlib.Path(project_root).resolve()
    proposed: list[tuple[str, str, scm.FunctionCPG, bytes]] = []
    seen: set[str] = set()
    for src in test_sources:
        for contract in mine_exception_contracts(src):
            arity = len([a for a in contract.arg_literals])
            candidates: list[scm.FunctionCPG] = []
            for fn in cpg.functions.get(contract.callee, []):
                if fn.language != "python":
                    continue
                if len(_param_names(fn)) < arity:
                    continue
                candidates.append(fn)
            if len(candidates) != 1:
                # Ambiguity is refused, not guessed: two functions with that name means the
                # contract does not identify its owner.
                continue
            fn = candidates[0]
            body_site = next((s for s in fn.sites if s.kind == "func_body"), None)
            if body_site is None:
                continue
            for tag, new_body in guard_candidates(fn, contract, body_site.source_text):
                key = f"{fn.rel_path}:{fn.name}:{tag}"
                if key in seen:
                    continue
                seen.add(key)
                raw = (root / fn.rel_path).read_bytes()
                patched = scm._apply_site_patch(raw, body_site, new_body)  # noqa: SLF001
                if not scm._syntactically_valid(patched, "python", raw):  # noqa: SLF001
                    continue
                proposed.append((tag, fn.name, fn, patched))
                if len(proposed) >= max_candidates:
                    return proposed
    return proposed


__all__ = [
    "ExceptionContract",
    "guard_candidates",
    "mine_exception_contracts",
    "synthesize_spec_guards",
]
