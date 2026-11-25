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
import itertools
from dataclasses import dataclass
import pathlib
import re
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
    arg_texts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "exc_name": self.exc_name,
            "match_pattern": self.match_pattern,
            "callee": self.callee,
            "arg_literals": [repr(a) for a in self.arg_literals],
            "keyword_literals": [[k, repr(v)] for k, v in self.keyword_literals],
            "call_text": self.call_text[:200],
            "node_id": self.node_id,
            "arg_texts": list(self.arg_texts),
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
    """Extract every `pytest.raises(...)` contract from one test module's source.

    Each contract is attributed to the test function that states it, because contracts stated by the
    *same* test are co-required: one test failing on two `pytest.raises` blocks needs both guards.
    """
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return []
    scopes: list[tuple[str, ast.AST]] = []
    for top in tree.body:
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scopes.append((top.name, top))
        elif isinstance(top, ast.ClassDef):
            for sub in top.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    scopes.append((f"{top.name}.{sub.name}", sub))
    if not scopes:
        scopes = [(node_id, tree)]
    out: list[ExceptionContract] = []
    for scope_name, scope_node in scopes:
        for node in ast.walk(scope_node):
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
                        arg_texts=tuple(ast.unparse(a)[:80] for a in call.args),
                        keyword_literals=kw_lits,
                        call_text=ast.unparse(call)[:200],
                        node_id=scope_name,
                    )
                )
    return out


def _raises_callee_name(node: ast.Call) -> str | None:
    return _call_callee(node)


def _contract_boundary_literal(contract: ExceptionContract) -> tuple[int, Any] | tuple[str, Any] | None:
    """The first argument that is a *boundary* value: a contract, not one test's data."""
    for idx, val in enumerate(contract.arg_literals):
        if val is nexus._REFUSED:  # noqa: SLF001
            continue
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


def _same_class_predicates(fn: "scm.FunctionCPG", cpg: "scm.ProjectCPG") -> list[str]:
    """Methods of the same class that take exactly one argument: the repo's own guard vocabulary.

    This is repo-native component mining applied to *guards*: `unregister(plugin)` already has a
    sibling method that answers "is this plugin registered", and a contract that says "this call must
    raise" is enforced by negating that sibling. Nothing is looked up in a table of known libraries;
    the candidates are the class's own methods and the suite decides which one is right.
    """
    out: list[str] = []
    owner = None
    for cls_name, methods in cpg.class_methods.items():
        if any(m_name == fn.name for m_name, _ in methods):
            owner = cls_name
            break
    if owner is not None:
        for m_name, m_params in cpg.class_methods.get(owner, []):
            if m_name == fn.name or m_name.startswith("_"):
                continue
            names = [_param_name(p) for p in m_params] if m_params and isinstance(m_params[0], (tuple, list)) else list(m_params)
            if len([n for n in names if n not in ("self", "cls")]) == 1:
                out.append(f"self.{m_name}")
    if not out:
        # The class-method index only covers query-style methods, so the fallback is the file's own
        # one-argument functions, addressed as `self.<name>`. A wrong pick is refuted by the suite.
        for m_name, defs in cpg.functions.items():
            if m_name == fn.name or m_name.startswith("_"):
                continue
            for d in defs:
                if d.rel_path != fn.rel_path or d.language != "python":
                    continue
                if not d.params or _param_name(d.params[0]) not in ("self", "cls"):
                    continue
                if len(_param_names(d)) == 1:
                    out.append(f"self.{m_name}")
                    break
    return out[:6]


_PRED_STOP = frozenset({"self", "cls", "is", "get", "has", "not", "the", "of", "or", "and", "to", "a"})


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 2 and t not in _PRED_STOP}


def _predicate_score(pred: str, message: str, negated: bool) -> int:
    """How well a sibling method answers the contract's own words: pure token overlap, no table.

    `not self.is_registered(plugin)` scores against the message `"not registered"` because the
    method name and the message share the word *registered*. This is the only signal used, so an
    unrelated sibling (`self.add_hookspecs`) scores zero and is pushed out of the candidate budget.
    """
    score = len(_tokens(pred.split(".", 1)[1]) & _tokens(message))
    if negated and "not" in message.lower():
        score += 1
    return score


def guard_candidates(
    fn: "scm.FunctionCPG",
    contract: ExceptionContract,
    body_text: str,
    cpg: "scm.ProjectCPG | None" = None,
) -> list[tuple[str, str]]:
    """One-line guard-and-raise statements that enforce `contract` inside `fn`."""
    indent = _indent_of(body_text)
    message = contract.match_pattern.replace('"', "'") if contract.match_pattern else ""
    raise_stmt = f'raise {contract.exc_name}("{message}")' if message else f"raise {contract.exc_name}()"
    params = _param_names(fn)
    if not params:
        return []
    out: list[tuple[str, str]] = []

    def _emit(cond: str, tag: str) -> None:
        guard = f"{indent}if {cond}:\n{indent}    {raise_stmt}\n"
        out.append((tag, guard + body_text))

    # Family 1: a boundary literal argument -> `if param is None`, `not param`, ...
    bound = _contract_boundary_literal(contract)
    if bound is not None:
        if isinstance(bound[0], int):
            idx = bound[0]
            param = params[idx] if idx < len(params) else params[-1]
            literal = bound[1]
        else:
            key = bound[0]
            param = key if key in params else params[0]
            literal = bound[1]
        for cond in _guard_conditions(param, literal):
            _emit(cond, f"SPEC_CONTRACT_GUARD[{cond}]")

    # Family 2: a call with no arguments at all -> every parameter must be absent.
    if not contract.arg_literals and not contract.keyword_literals and not contract.arg_texts:
        conj = " and ".join(f"{p} is None" for p in params)
        if conj:
            _emit(conj, f"SPEC_CONTRACT_GUARD[{conj}]")

    # Family 3: an argument the test supplied as an object -> the repository's own predicate on it.
    # Predicates are ranked by whether their name answers the contract's expected message, and each
    # one is offered both bare and conditioned on another parameter being absent: a method with an
    # optional selector (`unregister(plugin=None, name=None)`) only means "must be registered" on
    # the path where the selector was not used, which is exactly the `name is None and` conjunct.
    if cpg is not None and contract.arg_texts:
        target = params[0]
        others = [p for p in params[1:] if p != target]
        ranked = sorted(
            ((_predicate_score(pred, contract.match_pattern, True), pred)
             for pred in _same_class_predicates(fn, cpg)),
            key=lambda it: -it[0],
        )
        if ranked and ranked[0][0] > 0:
            ranked = [it for it in ranked if it[0] > 0]
        for _score, pred in ranked:
            for other in others:
                cond = f"{other} is None and not {pred}({target})"
                _emit(cond, f"SPEC_CONTRACT_GUARD[{cond}]")
            _emit(f"not {pred}({target})", f"SPEC_CONTRACT_GUARD[not {pred}]")
            _emit(f"{pred}({target})", f"SPEC_CONTRACT_GUARD[{pred}]")
    return out


def synthesize_spec_guards(
    project_root: pathlib.Path | str,
    cpg: "scm.ProjectCPG",
    test_sources: Sequence[str],
    *,
    max_candidates: int = 16,
    prioritize: Sequence[str] = (),
) -> list[tuple[str, str, "scm.FunctionCPG", bytes]]:
    """Bind every mined contract to a project function and return ready-to-apply guard patches.

    Contracts stated by the *same* test function are enforced **together** first: that is the
    difference between "the engine can write one guard" and "the engine can write the set of guards a
    single test demands", which is what `pluggy@8051a4d` needs.
    """
    root = pathlib.Path(project_root).resolve()
    # (rel, fname, node) -> list of (fn, body_site, [(tag, guard_text), ...]) one entry per contract
    by_scope: dict[tuple[str, str, str], list[tuple[scm.FunctionCPG, Any, list[tuple[str, str]]]]] = {}
    for src in test_sources:
        for contract in mine_exception_contracts(src):
            arity = len(contract.arg_literals)
            candidates = [
                fn for fn in cpg.functions.get(contract.callee, [])
                if fn.language == "python" and len(_param_names(fn)) >= arity
            ]
            if len(candidates) != 1:
                continue  # ambiguity is refused, not guessed
            fn = candidates[0]
            body_site = next((st for st in fn.sites if st.kind == "func_body"), None)
            if body_site is None:
                continue
            guards: list[tuple[str, str]] = []
            for tag, new_body in guard_candidates(fn, contract, body_site.source_text, cpg):
                if not new_body.endswith(body_site.source_text):
                    continue
                guards.append((tag, new_body[: len(new_body) - len(body_site.source_text)]))
            if guards:
                by_scope.setdefault((fn.rel_path, fn.name, contract.node_id), []).append((fn, body_site, guards))

    def _splice(fn: "scm.FunctionCPG", site: Any, texts: Sequence[str]) -> bytes | None:
        raw = (root / fn.rel_path).read_bytes()
        patched = scm._apply_site_patch(raw, site, "".join(texts) + site.source_text)  # noqa: SLF001
        if not scm._syntactically_valid(patched, "python", raw):  # noqa: SLF001
            return None
        return patched

    wanted = {n.split("::")[-1].split("[")[0] for n in prioritize}

    def _rank(item: tuple[tuple[str, str, str], Any]) -> tuple[int, int]:
        node = item[0][2]
        focused = 0 if (node.split(".")[-1] in wanted or node in wanted) else 1
        return (focused, len(item[1]))

    proposals: list[tuple[str, str, scm.FunctionCPG, bytes]] = []
    # 1. The guards a single test states, enforced together. Scopes from tests that are actually
    # failing come first, so a 16-candidate budget is never spent on a test that already passes.
    for (rel, fname, node), entries in sorted(by_scope.items(), key=_rank):
        fn, site = entries[0][0], entries[0][1]
        for guard_choice in itertools.product(*(entry[2] for entry in entries)):
            texts = [g for _tag, g in guard_choice]
            if any("is None" in t for t in texts):
                # Calling nothing first: a bare nullity conjunction must precede a guard that
                # *calls* a sibling predicate, or `unregister()` answers the predicate's error
                # ("not registered") instead of the contract's arity error ("one of name or plugin").
                texts = sorted(texts, key=lambda t: (1 if "self." in t else 0, t.count(" and ")))
            patched = _splice(fn, site, texts)
            if patched is None:
                continue
            tag = "+".join(_tag for _tag, _g in guard_choice)
            proposals.append((f"SPEC_CONTRACT_SET[{node or rel}]:{tag}", fn.name, fn, patched))
            if len(proposals) >= max_candidates:
                return proposals
            cap = 4 if (node.split(".")[-1] in wanted or node in wanted) else 1
            if len([p for p in proposals if (node or rel) in p[0]]) >= cap:
                break
    # 2. Singles, for contracts no other contract shares a test with.
    for (rel, fname, node), entries in sorted(by_scope.items(), key=_rank):
        for fn, site, guards in entries:
            for tag, text in guards:
                patched = _splice(fn, site, [text])
                if patched is None:
                    continue
                proposals.append((tag, fn.name, fn, patched))
                if len(proposals) >= max_candidates:
                    return proposals
    return proposals


__all__ = [
    "ExceptionContract",
    "guard_candidates",
    "mine_exception_contracts",
    "synthesize_spec_guards",
]
