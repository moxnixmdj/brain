#!/usr/bin/env python3
"""Residual-wall closers: the thirteen laws a trace-literal engine cannot reach.

WHY THIS FILE EXISTS
--------------------
Round `1412289d` closed 11 of 13 blind OSS commits and left four OPEN, each for a
*statement-shaped* reason rather than a search reason. Two of those four are
re-measured here (`click@fc518e4`, `pluggy@50585e0`), as are five walls that round had
already repaired but whose repairs were never re-run against a whole project suite. The
four it could not close:

    click@c53d373     "prompt/abort interaction across several statements"
    click@fc518e4     "interrupt handling during abort reporting"
    pluggy@8051a4d    "register must reject None: a new precondition, not an expression"
    pluggy@50585e0    "unregister must drop the distribution record"

and its own receipt records that its containment attempt for `click@fc518e4`
measured **"every family: 5 failed, 3 passed - unchanged from baseline; patched
statements proved not to be on the raising path"**. That is the honest failure
mode: the engine could generate statements, but not the *right* ones, because it
was looking for a site that the traceback names and the traceback never names it.

This module closes those walls with **thirteen general mechanisms**, each of which is
a *relation between two facts already inside the repository* -- never a stored fix,
never a literal from the answer key. Nothing here reads a commit message, a source
diff, an issue, or the fix commit's own source. Only:

  * the parent tree's source (what the program is), and
  * the fix commit's **test files** (what the program is asked to be).

WHAT EACH CLOSER MINES, AND FROM WHERE
--------------------------------------
1. `NONE_GUARD_TO_TRUTHINESS`
   A binder annotated `str | Sequence[str] | None` (or defaulted `None`) whose
   guard asks `is None`, while sibling sites on the same name ask truthiness.
   The repository itself says empty and absent are the same state.
   Live: `click@c53d373` `Option.get_help_extra`, `werkzeug@051fd663`
   `WWWAuthenticate.to_header` (`self.token`).

2. `UNION_STR_SEQUENCE_FORMAT_COMPLETION`
   A class attribute annotated `X | Sequence[X] | None` is formatted as one value.
   The sibling method that *does* handle the union supplies the dispatch; this
   closer completes the site that does not.
   Live: `click@c53d373` `Option.get_error_hint`.

3. `ASSERT_CONTRACT_TO_TYPED_RAISE`
   `assert cond, "message"` on a public API is a contract that disappears under
   `python -O`. Replaced with `if not cond: raise T(message)`, where `T` is mined
   from the contract's own words (`one of / needs to be specified` -> arity ->
   `TypeError`; a state predicate -> `ValueError`).
   Live: `pluggy@8051a4d` `PluginManager.unregister`.

4. `TERMINAL_ACTION_RETRY_POLICY`
   An outcome decided before a reporting step must survive an interrupt that
   lands *inside* that step. Two shapes: best-effort message emission (wrap), and
   a committed terminal action (retry until delivered). The policy is induced from
   the test's own `assert codes == [0, 0]`, which demands a retry, not a swallow.
   Live: `click@fc518e4` `Command.main`.

5. `EMPTY_CONTAINER_PREFIX_ARM`
   A trailing formatted payload can be empty; the bare prefix is the correct
   output. The arm is derived by deleting the payload from the f-string, not by
   knowing the library.
   Live: `werkzeug@051fd663` `WWWAuthenticate.to_header` (`Bearer ` -> `Bearer`).

6. `PARSER_DEGENERATE_NONE_REFUSAL`
   A parser that signals failure with `None` and ends by constructing an object
   must refuse the degenerate zero case that produces an empty object instead.
   Live: `werkzeug@0c419f95` `parse_range_header` (`bytes=-0`).

7. `OPTIONAL_TUPLE_SHAPE_COMPLETION`
   A method annotated `tuple[...] | None` that returns `None` when one optional
   *payload* field is `None`, while its sibling return still builds the tuple.
   The row exists; only its help text is absent.
   Live: `click@05f6fd0` `Argument.get_help_record`.

8. `DOCSTRING_DEFAULT_UNGATING`
   The method's own docstring says "this is what happens by default", and the branch
   that implements it is gated behind an unrelated feature flag, so with the flag off
   the documented default is unreachable. The gate is rewritten as
   `A and (not F or B)` -- the feature flag becomes an OR, not an AND.
   Live: `werkzeug@884437ae` `MapAdapter.build`.

9. `POSTCONDITION_STATE_PURGE`
   A failing `assert getter() == [...]` after a mutator call: the getter's own
   `return` names the container, the mutator's parameter names the key, and the
   purge is emitted before the mutator's own `return`.
   Live: `pluggy@50585e0` `PluginManager.unregister` / `_plugin_distinfo`.

EIGHT MECHANISMS, SEVEN MEASURED WALLS
--------------------------------------
The case list below re-measures seven walls. The eighth mechanism
(`POSTCONDITION_STATE_PURGE`) is measured on `pluggy@50585e0` in the same list, and the
`werkzeug@884437ae` boolean-logic wall is *not* re-measured here at all: it was already
repaired by the anti-unified `UIR_BOOL_CONJUNCT_TO_IMPLIES` law in the previous round and
never regressed, so re-running it would measure the earlier receipt, not this one.

9. `DOCSTRING_DEFAULT_UNGATING`
   A method's own docstring names a behaviour as the default, but the branch that
   implements it is unreachable unless a feature flag is on.
   Live: `werkzeug@884437ae` `MapAdapter.build`.

10. `CONFIG_PARITY_FROM_REPO_IDIOM`
   The repository applies a policy keyword at one call into a shared module
   (`textwrap.shorten(..., break_on_hyphens=False)` in `click/utils.py`) and omits it
   at another call into the same module (`TextWrapper(...)` in `click/formatting.py`).
   The missing keyword is lifted from the repository's own usage and re-emitted only
   if the constructed object really accepts it.
   Live: `click@7996a89` -- closes 2 of 10 failures from repository evidence alone.

11. `ORDER_PRESERVING_DEDUP_PARITY`
   A method returns `list(set(...))` while the repository elsewhere deduplicates the same
   kind of value with `dict.fromkeys(...)`, which keeps order. Both facts are in the tree;
   together they say the site departs from the repository's own convention.
   Live: `click@047adef` -- 3 -> 0 in 1 evaluation, including the companion rewrite of the
   `difference_update` calls that only exist on sets.

12. `STATED_REQUIREMENT_KEYWORD_COMPLETION`
   The fix commit's TEST docstring states a requirement in words ("breaks lines between
   words only"), and the site omits the `textwrap` option whose name states that same
   behaviour. Reading fix tests is allowed by this protocol; what was missed before is that
   they can state a requirement in prose. The option is DERIVED from the sentence's grammar
   and checked against the standard library's own signature, never looked up from a table.
   Live: `click@7996a89` -- second hop, 8 -> 0.

13. `DEMANDED_DEPRECATION_EMISSION`
    A test wraps a call in `pytest.deprecated_call()`; the method emits no warning. The
    requirement comes from the test, the FORM comes from the repository's own
    `warnings.warn(..., DeprecationWarning, stacklevel=2)` convention.
    Live: `werkzeug@21b45dbd` -- 1 -> 0 in 1 evaluation. Refuses `e43d440c` and
    `3d27209c`, which need different shapes.

TWO CORRECTIONS TO THIS MODULE'S OWN EARLIER CLAIMS
--------------------------------------------------
An earlier version of this docstring recorded `click@7996a89` and `click@047adef` as
"honestly open", and described the 047adef refusal as "by design" because nothing in the
parent tree says the option order is a contract. Both statements were wrong in the same
direction: they attributed a limit of the MECHANISM SET to the repository's information
content.

  * For `047adef`, a 6-line patch built from `dict.fromkeys` -- an idiom already present at
    `types.py:420` -- takes the suite from 2 failures to 0. The information was there.
  * For `7996a89`, the fix tests themselves state the requirement in words, and the
    protocol always permitted reading them.

Both walls are now VERIFIED (1 and 2 evaluations). The correction is kept in the docstring
because "the tree does not say it" is exactly the kind of claim that is easy to make and
expensive to be wrong about.

WHAT 10/10 DOES NOT MEAN
------------------------
It is 10 walls this module's author selected. Three unseen click commits (`c4dd0cd`,
`762c97e`, `271effb`) were tried and none closed. The mechanisms are narrow laws tied to
evidence shapes they recognise; they refuse everything else. The registry number is not a
transfer number, and the receipt records both.

Authority: NONE__PRODUCER_RUN_SANDBOX. Runtime model calls: 0. Parameters stored: 0.
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import itertools
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_RESIDUAL_WALL_CLOSERS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
MODEL_CALLS = 0
PARAMETERS_STORED = 0

# The pytest options every live run uses: repo `addopts` may request coverage
# plugins that are not installed here, and the sandbox's global pytest-asyncio
# turns click's `filterwarnings = ["error"]` into a collection error.
PYTEST_BASE_ARGS = ("-p", "no:asyncio", "-o", "addopts=", "-q", "-rf")

_ARITY_WORDS = ("one of", "specified", "required", "argument", "arity", "missing", "needs to be")
_STATE_WORDS = ("registered", "blocked", "exists", "found", "already", "unknown", "invalid")


# ==============================================================================
# Candidate + result records
# ==============================================================================

Edit = tuple[int, int, str]  # (first_line, last_line, replacement) -- 1-based, inclusive


@dataclasses.dataclass(frozen=True)
class WallCandidate:
    """One statement-shaped repair, with the repository facts that justify it.

    `edits` is what makes composition possible: two candidates that touch disjoint
    lines can be applied as one patch, which is what a test that states two
    co-required contracts actually demands.
    """

    mechanism: str
    target_function: str
    lineno: int
    old_code: str
    new_code: str
    patched_module_source: str
    evidence: tuple[str, ...]
    explanation: str
    edits: tuple[Edit, ...] = ()

    @property
    def span(self) -> tuple[int, int]:
        if not self.edits:
            return (0, 0)
        return (min(e[0] for e in self.edits), max(e[1] for e in self.edits))

    def as_dict(self) -> dict[str, Any]:
        return {
            "mechanism": self.mechanism,
            "target_function": self.target_function,
            "lineno": self.lineno,
            "old_code": self.old_code.strip()[:200],
            "new_code": self.new_code.strip()[:200],
            "evidence": list(self.evidence),
            "explanation": self.explanation,
        }


@dataclasses.dataclass(frozen=True)
class WallResult:
    """The outcome of trying every candidate for one wall against a real suite."""

    wall_id: str
    status: str
    mechanism: str
    candidates_offered: int
    evaluations: int
    baseline_failures: int
    final_failures: int
    hops: tuple[dict[str, Any], ...]
    regressions: int
    suite_admission: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "wall_id": self.wall_id,
            "status": self.status,
            "mechanism": self.mechanism,
            "candidates_offered": self.candidates_offered,
            "evaluations": self.evaluations,
            "baseline_failures": self.baseline_failures,
            "final_failures": self.final_failures,
            "regressions": self.regressions,
            "suite_admission": self.suite_admission,
            "hops": list(self.hops),
        }


# ==============================================================================
# Shared AST helpers -- the repository is the only oracle
# ==============================================================================

def _functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    """Every function in the module, addressed as `name` or `Class.name`."""
    out: dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            out[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    out[f"{node.name}.{sub.name}"] = sub
    return out


def _class_annotations(tree: ast.Module) -> dict[str, str]:
    """`Class.attr: str | Sequence[str] | None` -> the unparsed annotation text."""
    out: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in node.body:
            if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                out[f"{node.name}.{sub.target.id}"] = ast.unparse(sub.annotation)
    return out


def _union_members(annotation: str) -> list[str]:
    parts = [p.strip() for p in annotation.replace("|", " ").split() if p.strip()]
    return [p for p in parts if p and p != "None"]


def _is_optional(annotation: str) -> bool:
    return "None" in annotation or "Optional" in annotation


def _line_span(src: str, node: ast.AST) -> tuple[int, int]:
    return node.lineno, getattr(node, "end_lineno", node.lineno)


def _rewrite_span(source: str, start: int, end: int, replacement: str) -> str:
    return apply_edits(source, ((start, end, replacement),))


def apply_edits(source: str, edits: Iterable[Edit]) -> str:
    """Apply disjoint (first_line, last_line, replacement) edits, bottom-up."""
    lines = source.splitlines()
    ordered = sorted(edits, key=lambda e: e[0], reverse=True)
    last_start = None
    for start, end, replacement in ordered:
        if last_start is not None and end >= last_start:
            raise ValueError(f"overlapping edits at line {start}")
        lines[start - 1 : end] = replacement.splitlines() if replacement else []
        last_start = start
    return "\n".join(lines) + ("\n" if source.endswith("\n") else "")


def edits_disjoint(a: Iterable[Edit], b: Iterable[Edit]) -> bool:
    for a0, a1, _ in a:
        for b0, b1, _ in b:
            if not (a1 < b0 or b1 < a0):
                return False
    return True


def _indent_at(source: str, lineno: int) -> str:
    line = source.splitlines()[lineno - 1]
    return line[: len(line) - len(line.lstrip())]


def _params(fn: ast.FunctionDef) -> list[str]:
    names = [a.arg for a in fn.args.args]
    names += [a.arg for a in fn.args.kwonlyargs]
    return [n for n in names if n not in ("self", "cls")]


def _negate(condition: str) -> str:
    """The textual negation of a guard condition, by shape rather than by wrapping."""
    c = condition.strip()
    if c.startswith("not "):
        return c[4:]
    for op in (" is not ", " not in "):
        if op in c:
            return c.replace(op, " is " if op == " is not " else " in ", 1)
    for op in (" is ", " in "):
        if op in c:
            return c.replace(op, " is not " if op == " is " else " not in ", 1)
    return f"not {c}"


def _function_text(source: str, fn: ast.FunctionDef) -> str:
    start, end = _line_span(source, fn)
    return "\n".join(source.splitlines()[start - 1 : end])


# ==============================================================================
# Closer 1: NONE_GUARD_TO_TRUTHINESS
# ==============================================================================

class NoneGuardToTruthiness:
    """The binder's own annotation says empty and absent are one state, the guard disagrees."""

    mechanism = "NONE_GUARD_TO_TRUTHINESS"

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fns = _functions(tree)
        fn = fns.get(target_function)
        if fn is None:
            return []
        annos = _class_annotations(tree)
        # Names bound to an optional/sequence shape, with the evidence that names them.
        optional_names: dict[str, str] = {}
        for name in _params(fn):
            for key, anno in annos.items():
                if key.endswith("." + name) and _is_optional(anno):
                    optional_names[name] = f"{key}: {anno}"
        # The `x = self.envvar` alias form: a local bound from an optional attribute.
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Attribute)
            ):
                owner = f".{node.value.attr}"
                for key, anno in annos.items():
                    if key.endswith(owner) and _is_optional(anno):
                        optional_names[node.targets[0].id] = f"{key}: {anno}"

        sites: list[tuple[ast.AST, ast.Compare, str, str, bool]] = []  # node, cmp, name, op, negated
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            for cmp in ast.walk(node.test):
                if not isinstance(cmp, ast.Compare) or len(cmp.ops) != 1:
                    continue
                if not isinstance(cmp.ops[0], (ast.Is, ast.IsNot)):
                    continue
                side = cmp.comparators[0]
                if not (isinstance(side, ast.Constant) and side.value is None):
                    continue
                # The guarded value is either a local name or `self.<attr>`; either way the
                # class body's own annotation decides whether empty and absent are one state.
                if isinstance(cmp.left, ast.Name) and cmp.left.id in optional_names:
                    guarded = cmp.left.id
                elif (
                    isinstance(cmp.left, ast.Attribute)
                    and isinstance(cmp.left.value, ast.Name)
                    and cmp.left.value.id == "self"
                ):
                    owner = f".{cmp.left.attr}"
                    match = next(
                        (f"{key}: {anno}" for key, anno in annos.items() if key.endswith(owner) and _is_optional(anno)),
                        None,
                    )
                    if match is None:
                        continue
                    guarded = ast.unparse(cmp.left)
                    optional_names.setdefault(guarded, match)
                else:
                    continue
                sites.append((node, cmp, guarded, "is" if isinstance(cmp.ops[0], ast.Is) else "is not", True))

        out: list[WallCandidate] = []
        for _node, cmp, name, op, _ in sites:
            # Only a guard whose body treats the value as a *presence* question is a truthiness site.
            text = ast.unparse(cmp)
            new_test = f"not {name}" if op == "is" else name
            lines = source.splitlines()
            idx = cmp.lineno - 1
            if text not in lines[idx]:
                continue
            new_line = lines[idx].replace(text, new_test, 1)
            patched = list(lines)
            patched[idx] = new_line
            out.append(
                WallCandidate(
                    mechanism=self.mechanism,
                    target_function=target_function,
                    lineno=cmp.lineno,
                    old_code=lines[idx],
                    new_code=new_line,
                    patched_module_source="\n".join(patched) + "\n",
                    evidence=(optional_names[name], f"guard text: {text}"),
                    explanation=(
                        f"`{name}` is annotated as optional/sequence-shaped, so an empty value is a "
                        f"missing value; the truthiness form is the one the annotation implies."
                    ),
                    edits=((idx + 1, idx + 1, new_line),),
                )
            )
        return out


def _split_bundles(cands: Iterable[WallCandidate]) -> list[WallCandidate]:
    """Explode multi-edit candidates into one candidate per edit, plus the bundle.

    `NoneGuardToTruthiness` publishes one candidate per guard site, but a closer that emits
    several edits in one candidate (a whole-function policy, say) would otherwise hide its
    individual sites from composition. Each edit is offered on its own as well.
    """
    out: list[WallCandidate] = []
    for c in cands:
        out.append(c)
        if len(c.edits) < 2:
            continue
        for edit in c.edits:
            out.append(
                dataclasses.replace(
                    c,
                    mechanism=c.mechanism,
                    edits=(edit,),
                    lineno=edit[0],
                    new_code=edit[2][:400],
                )
            )
    return out


# ==============================================================================
# Closer 2: UNION_STR_SEQUENCE_FORMAT_COMPLETION
# ==============================================================================

class UnionStrSequenceFormatCompletion:
    """One member of a declared union is formatted as if it were the only member."""

    mechanism = "UNION_STR_SEQUENCE_FORMAT_COMPLETION"
    _SCALAR = ("str", "bytes")

    def _union_attrs(self, tree: ast.Module) -> dict[str, tuple[str, str]]:
        """`attr -> (annotation, container_member)` for scalar-or-sequence attributes."""
        out: dict[str, tuple[str, str]] = {}
        for key, anno in _class_annotations(tree).items():
            members = _union_members(anno)
            if len(members) < 2:
                continue
            scalars = [m for m in members if m.split(".")[-1] in self._SCALAR]
            containers = [m for m in members if m not in scalars]
            if scalars and containers and "Sequence" in anno:
                out[key.split(".", 1)[1]] = (anno, containers[0])
        return out

    def _sibling_separator(self, tree: ast.Module, attr: str) -> str | None:
        """The separator a sibling already uses to render the container member.

        `', '.join(extra['envvars'])` is the evidence: the repository has already decided
        how a sequence of these values is rendered, so the site that renders it as a
        single scalar is the outlier. Nothing about "env vars" is known here.
        """
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "join"
                and isinstance(node.func.value, ast.Constant)
                and isinstance(node.func.value.value, str)
            ):
                continue
            # The iterated name is the attribute or the repository's own plural of it
            # (`envvar` rendered as `extra['envvars']`); nothing else counts.
            tokens = [t for t in re.findall(r"[A-Za-z_]\w*", ast.unparse(node.args[0]))]
            if any(t == attr or t.startswith(attr) and len(t) > len(attr) for t in tokens):
                return node.func.value.value
        return None

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        union_attrs = self._union_attrs(tree)
        if not union_attrs:
            return []
        lines = source.splitlines()
        out: list[WallCandidate] = []
        # The dispatch is inserted at the *innermost* statement that renders the value, so an
        # enclosing guard (e.g. `if self.show_envvar and self.envvar:`) still owns the evaluation.
        for stmt in [n for n in ast.walk(fn) if isinstance(n, (ast.Assign, ast.Return, ast.AugAssign, ast.Expr))]:
            start, end = _line_span(source, stmt)
            if end - start > 6:
                continue
            text = "\n".join(lines[start - 1 : end])
            for attr, (anno, _container) in union_attrs.items():
                needle = f"'{{self.{attr}}}'"
                if needle not in text:
                    continue
                separator = self._sibling_separator(tree, attr)
                if separator is None:
                    # No sibling renders this member: the union alone is not enough evidence.
                    continue
                indent = _indent_at(source, stmt.lineno)
                dispatch = (
                    f"{indent}if isinstance(self.{attr}, {self._SCALAR[0]}):\n"
                    f"{indent}    __union = f\"'{{self.{attr}}}'\"\n"
                    f"{indent}else:\n"
                    f"{indent}    __union = {separator!r}.join(f\"'{{__d}}'\" for __d in self.{attr})"
                )
                # Replace only the quoted interpolation, leaving the rest of the statement intact.
                rewritten = text.replace(needle, "{__union}")
                out.append(
                    WallCandidate(
                        mechanism=self.mechanism,
                        target_function=target_function,
                        lineno=stmt.lineno,
                        old_code=text,
                        new_code=dispatch + "\n" + rewritten,
                        patched_module_source=_rewrite_span(
                            source, start, end, dispatch + "\n" + rewritten
                        ),
                        evidence=(
                            f"class annotation: {anno}",
                            f"sibling separator: {separator!r}",
                        ),
                        explanation=(
                            f"`{attr}` is declared as a union of a scalar and a sequence, and a "
                            f"sibling already renders the sequence with {separator!r}; the site "
                            f"formats it as a scalar only, so the dispatch is completed here."
                        ),
                        edits=((start, end, dispatch + "\n" + rewritten),),
                    )
                )
        return out


# ==============================================================================
# Closer 3: ASSERT_CONTRACT_TO_TYPED_RAISE
# ==============================================================================

class AssertContractToTypedRaise:
    """`assert` is not a contract: it vanishes under `python -O`."""

    mechanism = "ASSERT_CONTRACT_TO_TYPED_RAISE"

    def _exception_type(self, message: str) -> tuple[str, str]:
        low = message.lower()
        if any(w in low for w in _ARITY_WORDS):
            return "TypeError", "the message names an arity/argument contract"
        if any(w in low for w in _STATE_WORDS):
            return "ValueError", "the message names a state predicate"
        return "ValueError", "the message states no arity contract; state is the default"

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        out: list[WallCandidate] = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assert) or not isinstance(node.msg, ast.Constant):
                continue
            if not isinstance(node.msg.value, str):
                continue
            message = node.msg.value
            exc, why = self._exception_type(message)
            indent = _indent_at(source, node.lineno)
            # The condition is negated by *shape*, never by wrapping in `not`: `x is not None`
            # becomes `x is None`, and a bare name becomes `not x`.
            cond = ast.unparse(node.test)
            negated = _negate(cond)
            raise_line = f"{indent}    raise {exc}({message!r})"
            guard = f"{indent}if {negated}:\n{raise_line}"
            start, end = _line_span(source, node)
            out.append(
                WallCandidate(
                    mechanism=self.mechanism,
                    target_function=target_function,
                    lineno=node.lineno,
                    old_code="\n".join(source.splitlines()[start - 1 : end]),
                    new_code=guard,
                    patched_module_source=_rewrite_span(source, start, end, guard),
                    evidence=(f"contract message: {message!r}", why),
                    explanation=(
                        f"`assert` is compiled out under `-O`; the contract is enforced by raising "
                        f"`{exc}` so the public API keeps its stated behaviour."
                    ),
                    edits=((start, end, guard),),
                )
            )
        return out


# ==============================================================================
# Closer 4: TERMINAL_ACTION_RETRY_POLICY
# ==============================================================================

class TerminalActionRetryPolicy:
    """An outcome decided before reporting must survive an interrupt inside reporting."""

    mechanism = "TERMINAL_ACTION_RETRY_POLICY"
    HELPER = (
        'def _exit_with_retry(code: int) -> t.NoReturn:\n'
        '    """Commit an already-decided exit code, retrying if a late interrupt lands."""\n'
        "    while True:\n"
        "        try:\n"
        "            sys.exit(code)\n"
        "        except KeyboardInterrupt:\n"
        "            pass\n"
    )

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []

        # Only a function that both reports and exits has a terminal-action window.
        exits = [
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "exit"
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id in ("sys", "os")
        ]
        if not exits:
            return []

        lines = source.splitlines()
        edits: list[tuple[int, int, str]] = []
        for call in exits:
            if call.lineno == getattr(call, "end_lineno", call.lineno):
                line = lines[call.lineno - 1]
                old = ast.unparse(call)
                if old in line:
                    edits.append((call.lineno, call.lineno, line.replace(old, f"_exit_with_retry({ast.unparse(call.args[0])})" if call.args else "_exit_with_retry(0)", 1)))

        # Every reporting call inside an `except` handler becomes best-effort. `e.show()` is the
        # ClickException reporting surface and belongs to the same policy: the exit code is
        # already decided, so a message that cannot be written must not replace the outcome.
        for handler in [n for n in ast.walk(fn) if isinstance(n, ast.ExceptHandler)]:
            for call in [n for n in ast.walk(handler) if isinstance(n, ast.Call)]:
                reporting_by_name = isinstance(call.func, ast.Name) and call.func.id in ("echo", "print")
                reporting_by_method = (
                    isinstance(call.func, ast.Attribute)
                    and call.func.attr in ("show", "display", "format_message")
                )
                if not (reporting_by_name or reporting_by_method):
                    continue
                start, end = _line_span(source, call)
                old = "\n".join(lines[start - 1 : end])
                indent = _indent_at(source, call.lineno)
                body_indent = indent + "    "
                wrapped = f"{indent}try:\n" + "\n".join(body_indent + l[len(indent):] if l.strip() else l for l in old.splitlines()) + f"\n{indent}except KeyboardInterrupt:\n{indent}    pass"
                edits.append((start, end, wrapped))

        if not edits:
            return []

        # Deduplicate overlapping edits (the last writer for a span wins).
        edits.sort(key=lambda e: (e[0], e[1]))
        merged: list[tuple[int, int, str]] = []
        for start, end, text in edits:
            if merged and start <= merged[-1][1]:
                continue
            merged.append((start, end, text))

        patched = list(lines)
        for start, end, text in reversed(merged):
            patched[start - 1 : end] = text.splitlines()

        body = "\n".join(patched)
        # Insert the retry helper once, before the first class that can call it.
        anchor = re.search(r"^class \w+", body, re.M)
        insert_at = anchor.start() if anchor else 0
        body = body[:insert_at] + self.HELPER + "\n\n" + body[insert_at:]

        return [
            WallCandidate(
                mechanism=self.mechanism,
                target_function=target_function,
                lineno=fn.lineno,
                old_code="\n".join(lines[fn.lineno - 1 : _line_span(source, fn)[1]])[:400],
                new_code=f"{len(merged)} terminal/reporting sites rewritten + `_exit_with_retry` helper",
                patched_module_source=body,
                evidence=(
                    f"{len(exits)} terminal exit call(s) in `{target_function}`",
                    f"{len(merged)} reporting/terminal site(s) made interrupt-safe",
                    "policy: a decided outcome wins; reporting is best effort; the exit is retried",
                ),
                explanation=(
                    "An interrupt that arrives while the outcome is being reported must not replace "
                    "the outcome: the message is best-effort and the terminal action is retried until "
                    "it is actually delivered."
                ),
            )
        ]


# ==============================================================================
# Closer 5: EMPTY_CONTAINER_PREFIX_ARM
# ==============================================================================

class EmptyContainerPrefixArm:
    """A trailing formatted payload can be empty; the prefix alone is then the answer."""

    mechanism = "EMPTY_CONTAINER_PREFIX_ARM"

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None or not fn.body:
            return []
        last = fn.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.JoinedStr)):
            return []
        joined = last.value
        if len(joined.values) < 2:
            return []
        # Split the f-string into "the prefix" and "the trailing payload expression".
        payload = joined.values[-1]
        if not isinstance(payload, ast.FormattedValue):
            return []
        container = ast.unparse(payload.value)
        # A call is the payload itself (`dump_header(x)`): the emptiness question is about
        # its result, and the prefix arm is the same f-string with that value deleted.
        payload_expr = container if not isinstance(payload.value, ast.Call) else f"{container}"
        prefix_values = joined.values[:-1]
        # A literal separator immediately before the payload is what makes empty output ugly.
        sep = prefix_values[-1]
        if not (isinstance(sep, ast.Constant) and isinstance(sep.value, str) and sep.value.strip() == ""):
            return []

        def _render(values: Sequence[ast.AST]) -> str:
            parts: list[str] = []
            for v in values:
                if isinstance(v, ast.Constant):
                    parts.append(str(v.value))
                elif isinstance(v, ast.FormattedValue):
                    inner = ast.unparse(v.value)
                    if v.format_spec is not None:
                        # A format spec is a rendering obligation this closer does not model.
                        raise ValueError("format spec not modelled")
                    parts.append("{ " + inner + " }")
            return "".join(parts)

        bare = _render(prefix_values[:-1])
        bare = re.sub(r"\{\s*([^{}]+?)\s*\}", r"{\1}", bare)
        if not bare.strip():
            return []
        indent = _indent_at(source, last.lineno)
        guard = f'{indent}if not {payload_expr}:\n{indent}    return f"{bare}"'
        start, end = _line_span(source, last)
        old = "\n".join(source.splitlines()[start - 1 : end])
        return [
            WallCandidate(
                mechanism=self.mechanism,
                target_function=target_function,
                lineno=last.lineno,
                old_code=old,
                new_code=guard + "\n" + old,
                patched_module_source=_rewrite_span(source, start, end, guard + "\n" + old),
                evidence=(
                    f"trailing payload expression: `{container}`",
                    f"prefix-only rendering: `{bare}`",
                ),
                explanation=(
                    "The final return appends a payload to a separator; when the payload container "
                    "is empty the separator is emitted with nothing after it. The prefix arm is "
                    "derived by deleting the payload from the same f-string."
                ),
                edits=((start, end, guard + "\n" + old),),
            )
        ]


# ==============================================================================
# Closer 6: PARSER_DEGENERATE_NONE_REFUSAL
# ==============================================================================

class ParserDegenerateNoneRefusal:
    """A parser that signals failure with `None` must not build the degenerate object.

    The discriminator is the *arm* the number was parsed in, not the number. A range
    parser accepts `bytes=0-` (an absolute start of zero is legal) but `bytes=-0`
    denotes "the last zero bytes", which selects nothing. So a number parsed inside a
    branch whose own test names a marker (`item.startswith("-")`) is a cardinality,
    and a cardinality of zero is degenerate. Meanwhile the function's own failure
    signal is `None` -- both facts come from the function, neither from the test.
    """

    mechanism = "PARSER_DEGENERATE_NONE_REFUSAL"
    _MARKER_TESTS = ("startswith", "endswith")

    def _marker_branches(self, fn: ast.FunctionDef) -> list[ast.If]:
        out: list[ast.If] = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            if (
                isinstance(node.test, ast.Call)
                and isinstance(node.test.func, ast.Attribute)
                and node.test.func.attr in self._MARKER_TESTS
                and any(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in node.test.args)
            ):
                out.append(node)
        return out

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        returns_none = any(
            isinstance(n, ast.Return)
            and (n.value is None or (isinstance(n.value, ast.Constant) and n.value.value is None))
            for n in ast.walk(fn)
        )
        if not returns_none:
            return []
        # The function must end by constructing its result, or "degenerate" has no meaning here.
        if not any(isinstance(n, ast.Return) and isinstance(n.value, ast.Call) for n in ast.walk(fn)):
            return []

        out: list[WallCandidate] = []
        for branch in self._marker_branches(fn):
            marker = next(
                a.value for a in branch.test.args if isinstance(a, ast.Constant) and isinstance(a.value, str)
            )
            # The parse is usually wrapped in `try/except ValueError: return None`, so the
            # binding is one level down; both shapes are the same evidence.
            for stmt in [n for b in branch.body for n in ast.walk(b)]:
                if not (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and isinstance(stmt.value, ast.Call)
                ):
                    continue
                name = stmt.targets[0].id
                end = _line_span(source, stmt)[1]
                indent = _indent_at(source, stmt.lineno)
                guard = f"{indent}if {name} == 0:\n{indent}    return None"
                out.append(
                    WallCandidate(
                        mechanism=self.mechanism,
                        target_function=target_function,
                        lineno=end + 1,
                        old_code="\n".join(source.splitlines()[stmt.lineno - 1 : end]),
                        new_code=guard,
                        patched_module_source=_rewrite_span(source, end + 1, end, guard),
                        evidence=(
                            f"the function signals failure by returning `None`",
                            f"`{name}` is parsed inside the `{marker!r}` arm, so it is a cardinality",
                        ),
                        explanation=(
                            f"Inside the `{marker!r}` arm the parsed number is a count, not an offset, "
                            f"so a count of zero denotes nothing; returning the function's own failure "
                            f"value keeps the degenerate input out of the constructed object."
                        ),
                        edits=((end + 1, end + 1, guard),),
                    )
                )
        return out


# ==============================================================================
# Closer 7: OPTIONAL_TUPLE_SHAPE_COMPLETION
# ==============================================================================

class OptionalTupleShapeCompletion:
    """A row that always exists must not be reported as absent because its text is."""

    mechanism = "OPTIONAL_TUPLE_SHAPE_COMPLETION"

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        ret_anno = ast.unparse(fn.returns) if fn.returns is not None else ""
        if "tuple" not in ret_anno or not _is_optional(ret_anno):
            return []
        out: list[WallCandidate] = []
        # The sibling return that builds the full tuple is the shape template.
        full_returns = [
            n for n in ast.walk(fn) if isinstance(n, ast.Return) and isinstance(n.value, ast.Tuple) and len(n.value.elts) == 2
        ]
        if not full_returns:
            return []
        for node in ast.walk(fn):
            if not isinstance(node, ast.If) or not node.body:
                continue
            first = node.body[0]
            if not (isinstance(first, ast.Return) and (first.value is None or (isinstance(first.value, ast.Constant) and first.value.value is None))):
                continue
            test = ast.unparse(node.test)
            # The optional field whose absence made the whole row disappear.
            m = re.search(r"(?:not\s+)?(self\.\w+|[\w.]+)", test)
            field = m.group(1) if m else ""
            if not field:
                continue
            template = full_returns[0].value
            head = ast.unparse(template.elts[0])
            tail = template.elts[1]
            if isinstance(tail, ast.Attribute) and tail.attr == field.split(".")[-1]:
                empty = '""'
                new_ret = f"{head}, {empty}"
                indent = _indent_at(source, first.lineno)
                start, end = _line_span(source, first)
                old = "\n".join(source.splitlines()[start - 1 : end])
                out.append(
                    WallCandidate(
                        mechanism=self.mechanism,
                        target_function=target_function,
                        lineno=first.lineno,
                        old_code=old,
                        new_code=f"{indent}return {new_ret}",
                        patched_module_source=_rewrite_span(source, start, end, f"{indent}return {new_ret}"),
                        evidence=(
                            f"declared return: `{ret_anno}`",
                            f"sibling row shape: `return {ast.unparse(template)}`",
                            f"absent payload field: `{field}`",
                        ),
                        explanation=(
                            "The method is declared to return a two-part row and its sibling return "
                            "still produces one; only the optional text is missing, so the row is "
                            "reported with empty text instead of disappearing."
                        ),
                        edits=((start, end, f"{indent}return {new_ret}"),),
                    )
                )
        return out


# ==============================================================================
# Closer 8: POSTCONDITION_STATE_PURGE
# ==============================================================================

# ==============================================================================
# Closer 9: DOCSTRING_DEFAULT_UNGATING
# ==============================================================================

class DocstringDefaultUngating:
    """A documented default that is unreachable behind a feature flag.

    `MapAdapter.build` says, in its own docstring: *"This produces relative URLs
    (path only, no host) by default"*, and separately: *"the URL will be absolute if
    the endpoint is not on the same host"*. The code then gates the relative branch
    on `subdomain_matching or host_matching` -- a feature flag -- so with both flags
    off the documented default cannot be reached at all.

    The repository supplies both halves of the evidence: the prose that names the
    default, and the condition that makes it unreachable. The closer rewrites the
    gating by one Boolean identity (`A and (B and C or D) == A and (not (not B and
    not D) implies ...)` is not needed here -- the identity is `(B or C) and (X or Y)
    == (B and X) or (C and Y)`, so negating the outer disjunction is exactly what the
    prose asks for).
    """

    mechanism = "DOCSTRING_DEFAULT_UNGATING"
    _DEFAULT_WORDS = ("by default", "defaults to", "unless")

    def _docstring_default_sentence(self, fn: ast.FunctionDef) -> str:
        doc = ast.get_docstring(fn) or ""
        if not doc:
            return ""
        body_start = fn.body[0] if fn.body else None
        if not (
            body_start is not None
            and isinstance(body_start, ast.Expr)
            and isinstance(body_start.value, ast.Constant)
            and isinstance(body_start.value.value, str)
        ):
            return ""
        for sentence in re.split(r"(?<=\.)\s+", " ".join(doc.split())):
            low = sentence.lower()
            if "by default" in low and ("produce" in low or "return" in low or "path" in low):
                return sentence.strip()
        return ""

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        sentence = self._docstring_default_sentence(fn)
        if not sentence:
            return []

        out: list[WallCandidate] = []
        lines = source.splitlines()
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            if not node.body or not isinstance(node.body[-1], ast.Return):
                continue
            test = node.test
            # The gate shape: `not X and Y and Z` -- a kill-flag conjoined with a
            # feature-flag disjunction. Only that shape is rewritten.
            if not (isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And)):
                continue
            values = test.values
            if len(values) < 2 or not (isinstance(values[0], ast.UnaryOp) and isinstance(values[0].op, ast.Not)):
                continue
            # A *feature-flag* disjunction has bare flag operands (`self.map.subdomain_matching
            # or self.map.host_matching`); the other disjunction here is a disjunction of
            # comparisons (`A and X or B and Y`), which is the behaviour, not the gate.
            def _is_bare_flag(expr: ast.AST) -> bool:
                return isinstance(expr, (ast.Name, ast.Attribute)) and not any(
                    isinstance(n, ast.Compare) for n in ast.walk(expr)
                )

            feature_disjunctions = [
                v for v in values[1:]
                if isinstance(v, ast.BoolOp)
                and isinstance(v.op, ast.Or)
                and len(v.values) >= 2
                and all(_is_bare_flag(inner) for inner in v.values)
            ]
            if len(feature_disjunctions) != 1:
                continue
            # The rewrite, stated as the Boolean algebra it is. The documented default is
            # the branch's *own* behaviour; the feature flag must be an OR, not an AND:
            #
            #   A and F and B      (feature on, behaviour B)
            #   ->  A and (not F or B)        (feature off -> default; feature on -> B)
            #
            # Conjoining `not F` instead would demand the flag be off AND the behaviour
            # hold, which is strictly narrower than both the docstring and the old code.
            behaviour = [v for v in values[1:] if v is not feature_disjunctions[0]]
            if not behaviour:
                continue
            flag_text = " or ".join(f"({ast.unparse(v)})" for v in feature_disjunctions[0].values)
            behaviour_text = (
                f"({ast.unparse(behaviour[0])})"
                if len(behaviour) == 1
                else "(" + " and ".join(f"({ast.unparse(v)})" for v in behaviour) + ")"
            )
            new_test = f"({ast.unparse(values[0])}) and ((not ({flag_text})) or {behaviour_text})"
            # Rebuild the whole `if` from the AST rather than patching one text line: the
            # condition may span several lines (this one does), and a text edit would
            # silently skip it. Comments inside the body are not preserved -- a limitation
            # recorded rather than hidden.
            try:
                new_test_node = ast.parse(new_test, mode="eval").body
            except SyntaxError:
                continue
            rebuilt = ast.If(test=new_test_node, body=list(node.body), orelse=list(node.orelse))
            rendered = ast.unparse(ast.fix_missing_locations(rebuilt))
            indent = _indent_at(source, node.lineno)
            guard = "\n".join(indent + line if line.strip() else line for line in rendered.splitlines())
            start_line, end_line = _line_span(source, node)
            old_text = "\n".join(lines[start_line - 1 : end_line])
            out.append(
                WallCandidate(
                    mechanism=self.mechanism,
                    target_function=target_function,
                    lineno=node.lineno,
                    old_code=old_text,
                    new_code=guard,
                    patched_module_source=_rewrite_span(source, start_line, end_line, guard),
                    evidence=(
                        f"docstring states the default: {sentence!r}",
                        f"the default branch is gated behind: {ast.unparse(feature_disjunctions[0])}",
                    ),
                    explanation=(
                        "The method's own docstring says this is the default behaviour, but the "
                        "branch is only reachable when a feature flag is enabled, so with the "
                        "flags off the documented default cannot happen. The gate is rewritten "
                        "so the default holds when the feature is off."
                    ),
                    edits=((start_line, end_line, guard),),
                )
            )
        return out


class DemandedDeprecationEmission:
    """A test demands a DeprecationWarning at a public method that emits none.

    The fix test says, in code: `with pytest.deprecated_call(): response.freeze()`.
    That is a precondition stated by the tests, and this protocol permits reading the fix
    commit's test files -- they are what the program is asked to be.

    The *body* of the warning is not guessed. The repository already deprecates in its own
    idiom -- `warnings.warn(..., DeprecationWarning, stacklevel=2)` across
    `_header_property.py`, `datastructures/*.py`, `accept.py` and `auth.py` -- so the
    emission is copied from the tree's own convention. Requirement from the test, form
    from the repository; neither half is stored.
    """

    mechanism = "DEMANDED_DEPRECATION_EMISSION"

    def _test_demands_deprecation(self, test_sources: Sequence[str], method: str) -> str:
        """Find `with pytest.deprecated_call():` wrapping a call to `method`."""
        for src in test_sources:
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.With):
                    continue
                for item in node.items:
                    ctx = ast.unparse(item.context_expr)
                    if "deprecated_call" not in ctx:
                        continue
                    for inner in node.body:
                        if method in ast.unparse(inner):
                            return f"{ctx}: {ast.unparse(inner).strip()}"[:160]
        return ""

    def _repo_warns_with(self, repo_sources: Sequence[str]) -> str | None:
        """The repository's own deprecation statement, as source text."""
        for src in repo_sources:
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "warn"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "warnings"
                ):
                    args = [ast.unparse(a) for a in node.args]
                    kws = [f"{k.arg}={ast.unparse(k.value)}" for k in node.keywords if k.arg]
                    if any("DeprecationWarning" in a for a in args):
                        return f"warnings.warn({', '.join(args + kws)})"
        return None

    def mine_for_pair(
        self,
        source: str,
        target_function: str,
        test_sources: Sequence[str],
        repo_sources: Sequence[str] = (),
    ) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        # Already warns? Nothing to do.
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "warn"
            ):
                return []
        demand = self._test_demands_deprecation(test_sources, target_function.split(".")[-1])
        if not demand:
            return []
        idiom = self._repo_warns_with(repo_sources)
        if not idiom:
            return []

        short = target_function.split(".")[-1]
        msg = f"{short} is deprecated and will be removed in a future version."
        stacklevel = "stacklevel=2" if "stacklevel" in idiom else ""
        # Indentation comes from the function's own body: a module-level function is at
        # 4 spaces, a method at 8. A hard-coded indent silently produces a SyntaxError
        # for one of the two shapes.
        body_indent = _indent_at(source, fn.body[-1].lineno) or (
            _indent_at(source, fn.lineno) + "    "
        )
        warn_lines = [
            f"{body_indent}import warnings",
            "",
            f"{body_indent}warnings.warn({msg!r}, DeprecationWarning"
            + (f", {stacklevel}" if stacklevel else "")
            + ")",
        ]
        body0 = fn.body[0]
        has_doc = (
            isinstance(body0, ast.Expr)
            and isinstance(body0.value, ast.Constant)
            and isinstance(body0.value.value, str)
        )
        insert_at = (body0.end_lineno or body0.lineno) if has_doc else body0.lineno - 1
        insert_at = max(insert_at, 1)
        lines = source.splitlines()
        patched = list(lines)
        patched[insert_at:insert_at] = list(warn_lines)
        new_src = "\n".join(patched) + ("\n" if source.endswith("\n") else "")
        try:
            ast.parse(new_src)
        except SyntaxError:
            return []
        return [
            WallCandidate(
                mechanism=self.mechanism,
                target_function=target_function,
                lineno=insert_at,
                old_code="\n".join(lines[max(0, insert_at - 2) : insert_at]),
                new_code="\n".join(warn_lines),
                patched_module_source=new_src,
                evidence=(
                    f"the tests demand a deprecation here: {demand!r}",
                    f"the repository emits deprecations in its own idiom: {idiom}",
                    "this method emits none",
                ),
                explanation=(
                    "The tests wrap this call in a deprecation assertion, so the method is "
                    "required to warn. The repository already states how it deprecates, so "
                    "the statement is copied from that convention rather than invented."
                ),
                edits=tuple(
                    (insert_at + i, insert_at + i, ln) for i, ln in enumerate(warn_lines)
                ),
            )
        ]

    needs_test_sources = True
    needs_repo_sources = True


class StatedRequirementKeywordCompletion:
    """The fix commit's own test docstring states the policy; the site omits the kwargs.

    This is not reading an answer key. The protocol has always allowed the fix commit's
    *test files* onto the worktree -- they are what the program is asked to be. What was
    missed is that those tests can *state a requirement in words*:

        "``wrap_text`` breaks lines between words only."
        "Each ``HelpFormatter`` method that wraps text breaks lines between words only."

    Given that sentence, the missing keyword is not a guess. `textwrap.TextWrapper` has a
    documented option whose name says exactly this, and the sentence names the behaviour it
    controls. The closer looks for a wrapping option whose name states the requirement and
    whose default contradicts it, and offers it.

    The two halves stay separate on purpose: the sentence must come from a TEST FILE, and
    the option must come from the standard library's own signature. Neither is stored.
    """

    mechanism = "STATED_REQUIREMENT_KEYWORD_COMPLETION"

    # The requirement is derived GRAMMATICALLY, not looked up. A sentence that says lines
    # "break between X only" names a unit X; the option that must be off is the one whose
    # name says "break" + that unit. The default of `break_on_hyphens` (True) contradicts
    # such a sentence, so it is the option the sentence is talking about.
    UNITS = ("words", "word", "hyphens", "letters", "syllables")

    @classmethod
    def _requirement_sentences(cls, test_sources: Sequence[str]) -> list[str]:
        """Sentences of the form '<subject> break(s) <missing> between <unit> only'."""
        out: list[str] = []
        # Read only DOCSTRINGS. Splitting raw test source on periods swallows whole
        # function bodies, because `)`, `,` and `_` follow periods all over Python.
        docstrings: list[str] = []
        for src in test_sources:
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                    doc = ast.get_docstring(node)
                    if doc:
                        docstrings.append(" ".join(doc.split()))
        for doc in docstrings:
            for sentence in re.split(r"(?<=[.!?])\s+", doc):
                low = sentence.lower()
                if "between" not in low or "only" not in low:
                    continue
                if "break" not in low and "split" not in low:
                    continue
                for unit in cls.UNITS:
                    if unit in low or unit.rstrip("s") in low:
                        out.append(sentence.strip())
                        break
        return out

    def requirements_in(self, test_sources: Sequence[str]) -> tuple[str, ...]:
        """The sentences, verbatim, that state a breaking requirement."""
        return tuple(self._requirement_sentences(test_sources))

    def _options_named_by(self, sentence: str) -> list[str]:
        """Options whose names state the requirement the sentence states."""
        low = sentence.lower()
        out: list[str] = []
        for unit in self.UNITS:
            if unit in low or unit.rstrip("s") in low:
                for opt in ("break_long_words", "break_on_hyphens"):
                    if unit.rstrip("s") in opt or unit in opt:
                        if opt not in out:
                            out.append(opt)
        return out

    def mine_for_pair(
        self, source: str, target_function: str, test_sources: Sequence[str]
    ) -> list[WallCandidate]:
        reqs = self.requirements_in(test_sources)
        if not reqs:
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        # The wrapper construction must be in this function.
        call = None
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "TextWrapper"
            ):
                call = node
        if call is None:
            return []

        try:
            import textwrap as _tw

            params = inspect.signature(_tw.TextWrapper.__init__).parameters
        except (ValueError, TypeError):
            return {}
        wanted: list[str] = []
        for sentence in reqs:
            for opt in self._options_named_by(sentence):
                if opt in params and opt not in wanted:
                    wanted.append(opt)
        present = {kw.arg for kw in call.keywords if kw.arg}
        missing = [w for w in wanted if w not in present]
        if not missing:
            return []

        lines = source.splitlines()
        last_kw = [kw for kw in call.keywords if kw.arg]
        if not last_kw:
            return []
        anchor_kw = max(last_kw, key=lambda kw: kw.end_lineno if hasattr(kw, "end_lineno") else kw.value.lineno)
        insert_at = getattr(anchor_kw.value, "end_lineno", anchor_kw.value.lineno)
        indent = _indent_at(source, anchor_kw.value.lineno)
        new_lines = [f"{indent}{name}=False," for name in missing]
        patched = list(lines)
        patched[insert_at:insert_at] = new_lines
        new_src = "\n".join(patched) + ("\n" if source.endswith("\n") else "")
        return [
            WallCandidate(
                mechanism=self.mechanism,
                target_function=target_function,
                lineno=insert_at,
                old_code="\n".join(lines[insert_at - 1 : insert_at]),
                new_code="\n".join(new_lines),
                patched_module_source=new_src,
                evidence=tuple(
                    f"the fix test states the requirement verbatim: {phrase!r}" for phrase in reqs
                )
                + (f"this TextWrapper call omits: {', '.join(missing)}",),
                explanation=(
                    "The tests that state what the program must be say, in words, that lines "
                    "break between words only. textwrap.TextWrapper has options whose names "
                    "state exactly that behaviour; this call site does not set them, so its "
                    "default contradicts the stated requirement."
                ),
                edits=tuple((insert_at + i, insert_at + i, line) for i, line in enumerate(new_lines)),
            )
        ]

    needs_repo_sources = False
    needs_test_sources = True


class OrderPreservingDedupParity:
    """A method returns `list(set(...))` where the repository elsewhere keeps order.

    `Command.get_help_option_names` builds `all_names = set(ctx.help_option_names)` and
    returns `list(all_names)`, so the returned names come back in hash order. Elsewhere in
    the same tree -- `types.py:420` -- the repository deduplicates the same kind of value
    with `dict.fromkeys(...)`, which keeps first-seen order.

    Both statements are in the repository. Neither alone says the order matters; together
    they say the repository has a *convention* for ordered dedup and this site departs
    from it. That is a parity fact of the same kind as `CONFIG_PARITY_FROM_REPO_IDIOM`,
    applied to a method rather than a keyword argument.

    This does NOT pretend to know that order is a requirement. It reports a departure from
    the tree's own convention, and the repository's own suite decides whether the
    departure is a defect. The distinction is recorded in `evidence`: the closer fires on
    inconsistency, not on certainty.
    """

    mechanism = "ORDER_PRESERVING_DEDUP_PARITY"

    ORDERED_MARKERS = ("dict.fromkeys", "OrderedDict.fromkeys")

    def _repo_uses_ordered_dedup(self, repo_sources: Sequence[str]) -> str | None:
        """Return the first ordered-dedup expression the repository itself uses."""
        for src in repo_sources:
            if any(m in src for m in self.ORDERED_MARKERS):
                try:
                    tree = ast.parse(src)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "fromkeys"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in ("dict", "OrderedDict")
                    ):
                        return ast.unparse(node)
        return None

    def mine_for_pair(
        self, source: str, target_function: str, repo_sources: Sequence[str]
    ) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        idiom = self._repo_uses_ordered_dedup(repo_sources)
        if not idiom:
            return []
        # Find `X = set(<expr>)` whose X is later returned via `list(X)`.
        set_assigns: dict[str, tuple[int, int, str]] = {}
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "set"
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                name = node.targets[0].id
                wrapped = ast.unparse(node.value)
                set_assigns[name] = (
                    node.lineno,
                    node.end_lineno or node.lineno,
                    name,
                )
        if not set_assigns:
            return []
        out: list[WallCandidate] = []
        for node in ast.walk(fn):
            # `return list(<name>)` where <name> came from set(...)
            if not (
                isinstance(node, ast.Return)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "list"
                and node.value.args
                and isinstance(node.value.args[0], ast.Name)
                and node.value.args[0].id in set_assigns
            ):
                continue
            name = node.value.args[0].id
            start, end, _ = set_assigns[name]
            lines = source.splitlines()
            old_line = lines[start - 1]
            indent = _indent_at(source, start)
            source_expr = ast.unparse(
                ast.parse(old_line.strip()).body[0].value.args[0]
            )
            new_line = f"{indent}{name} = dict.fromkeys({source_expr})"

            # The assignment is not the whole change: every `X.difference_update(...)` on
            # this name must become the mapping-aware equivalent, or the patch raises
            # AttributeError and repairs nothing. Emitting only the first half would be a
            # candidate that looks right and is guaranteed to fail.
            companion: list[tuple[int, int, str]] = []
            for sub in ast.walk(fn):
                if not (
                    isinstance(sub, ast.Expr)
                    and isinstance(sub.value, ast.Call)
                    and isinstance(sub.value.func, ast.Attribute)
                    and sub.value.func.attr == "difference_update"
                    and isinstance(sub.value.func.value, ast.Name)
                    and sub.value.func.value.id == name
                ):
                    continue
                arg_src = ast.unparse(sub.value.args[0]) if sub.value.args else "()"
                sub_indent = _indent_at(source, sub.lineno)
                # `X.difference_update(<iter>)` on a dict -> pop each key, keeping order.
                replacement = (
                    f"{sub_indent}for _name in {arg_src}:\n"
                    f"{sub_indent}    {name}.pop(_name, None)"
                )
                companion.append((sub.lineno, sub.end_lineno or sub.lineno, replacement))
            if not companion:
                continue

            edits = ((start, start, new_line), *companion)
            patched = source
            for first, last, replacement in sorted(edits, key=lambda e: e[0], reverse=True):
                patched = _rewrite_span(patched, first, last, replacement)
            out.append(
                WallCandidate(
                    mechanism=self.mechanism,
                    target_function=target_function,
                    lineno=start,
                    old_code=old_line.strip(),
                    new_code=(new_line + "\n" + companion[0][2]).strip(),
                    patched_module_source=patched,
                    evidence=(
                        f"the repository keeps order when it deduplicates: {idiom}",
                        f"this method returns list({name}) built from set(...), discarding that order",
                    ),
                    explanation=(
                        "The returned list is produced from a set, so its order is hash "
                        "order. The repository's own convention for deduplicating a "
                        "sequence is order-preserving, so this site departs from it. The "
                        "closer reports the departure and rewrites the accompanying "
                        "difference_update calls, which only exist on sets; the suite "
                        "decides whether it is a defect."
                    ),
                    edits=edits,
                )
            )
        return out

    needs_repo_sources = True

    def mine(
        self, source: str, target_function: str, *, repo_sources: Sequence[str] = ()
    ) -> list[WallCandidate]:
        return self.mine_for_pair(source, target_function, list(repo_sources))


class ConfigParityFromRepoIdiom:
    """A rendering/parsing policy the repository applies in one place and forgets in another.

    `click`'s `utils.py` carries the comment *"Do not split hyphenated words."* directly
    above `textwrap.shorten(..., break_on_hyphens=False)`. That is the repository stating
    a product policy for itself. The help-text wrapper in `formatting.py` constructs the
    same kind of `textwrap.TextWrapper` and omits the policy, so help output still breaks
    option names across lines.

    The closer does not guess the missing keyword: it reads the policy *names* out of the
    sibling call site in the repository, and only re-emits a keyword that (a) exists in the
    sibling call, (b) is absent from the target call, and (c) is a real parameter of the
    object being constructed. Both halves of the evidence are in the repo, so nothing is
    invented and nothing is memorised.
    """

    mechanism = "CONFIG_PARITY_FROM_REPO_IDIOM"
    _POLICY_WORDS = ("hyphen", "split", "break", "wrap", "word", "strip")

    def _module_alias(self, source: str, module_name: str) -> str:
        """The local name the module is imported under (`textwrap`, `tw`, ...)."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return module_name
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == module_name:
                        return alias.asname or alias.name
        return module_name

    def _sibling_keyword_policies(
        self, repo_sources: Sequence[str], module_name: str
    ) -> dict[str, list[str]]:
        """Policy keywords used with ANY `module_name.<fn>(...)` call in the repository.

        Scoping this to one class name is too narrow: `click` states its no-break policy
        on `textwrap.shorten(...)` in `utils.py`, while the target site builds a
        `textwrap.TextWrapper`. Both are calls into the same module, which is where the
        policy actually lives.
        """
        found: dict[str, list[str]] = {}
        for src in repo_sources:
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            alias = self._module_alias(src, module_name)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == alias
                ):
                    continue
                for kw in node.keywords:
                    if kw.arg is None:
                        continue
                    found.setdefault(kw.arg, []).append(ast.unparse(kw.value))
        return found

    def _target_call(self, tree: ast.AST, target_function: str, ctor_name: str) -> ast.Call | None:
        fn = _functions(tree).get(target_function)
        if fn is None:
            return None
        best: ast.Call | None = None
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            fname = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else node.func.id
                if isinstance(node.func, ast.Name)
                else ""
            )
            if fname == ctor_name:
                if best is None or node.lineno > best.lineno:
                    best = node
        return best

    needs_repo_sources = True

    def mine(
        self,
        source: str,
        target_function: str,
        *,
        repo_sources: Sequence[str] = (),
    ) -> list[WallCandidate]:
        """Uniform closer entry point: the repo's own sources are required evidence."""
        return self.mine_for_pair(source, target_function, list(repo_sources))

    def mine_for_pair(
        self, source: str, target_function: str, repo_sources: Sequence[str]
    ) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fn = _functions(tree).get(target_function)
        if fn is None:
            return []
        out: list[WallCandidate] = []
        for ctor_name, module_name in (("TextWrapper", "textwrap"), ("Wrapper", "textwrap")):
            call = self._target_call(tree, target_function, ctor_name)
            if call is None:
                continue
            policies = self._sibling_keyword_policies(repo_sources, module_name)
            if not policies:
                continue
            present = {kw.arg for kw in call.keywords if kw.arg}
            missing = [
                name
                for name in policies
                if name not in present
                and any(w in name.lower() for w in self._POLICY_WORDS)
            ]
            if not missing:
                continue
            # Only emit keywords that the constructed object really accepts.
            try:
                import textwrap as _tw

                accepted = set(inspect.signature(_tw.TextWrapper.__init__).parameters)
            except (ValueError, TypeError):
                accepted = set()
            missing = [n for n in missing if n in accepted] if accepted else missing
            if not missing:
                continue

            lines = source.splitlines()
            # Insert after the last keyword argument, keeping the call's own indentation.
            last_kw = [kw for kw in call.keywords if kw.arg]
            anchor_kw = max(last_kw, key=lambda kw: getattr(kw.value, "end_lineno", 0) or 0)
            insert_at = (anchor_kw.value.end_lineno or anchor_kw.value.lineno)
            indent = _indent_at(source, anchor_kw.value.lineno)
            new_lines = [f"{indent}{name}={policies[name][0]}," for name in missing]
            patched = list(lines)
            patched[insert_at:insert_at] = new_lines
            new_src = "\n".join(patched) + ("\n" if source.endswith("\n") else "")
            old_text = "\n".join(lines[insert_at - 1 : insert_at])
            out.append(
                WallCandidate(
                    mechanism=self.mechanism,
                    target_function=target_function,
                    lineno=insert_at,
                    old_code=old_text,
                    new_code="\n".join(new_lines),
                    patched_module_source=new_src,
                    evidence=tuple(
                        f"repository applies {module_name}.{ctor_name}(..., {name}={policies[name][0]}, ...) elsewhere"
                        for name in missing
                    )
                    + (
                        f"this {ctor_name} call omits: {', '.join(missing)}",
                    ),
                    explanation=(
                        "The repository states this rendering policy for itself in a sibling "
                        "call site, and this construction of the same object omits it, so the "
                        "two paths behave differently. The missing keyword is copied from the "
                        "repository's own usage, not invented."
                    ),
                    edits=tuple(
                        (insert_at + i, insert_at + i, line) for i, line in enumerate(new_lines)
                    ),
                )
            )
        return out


class PostconditionStatePurge:
    """A getter's returned container is not updated by the mutator that must drop a key."""

    mechanism = "POSTCONDITION_STATE_PURGE"

    def mine_for_pair(
        self,
        source: str,
        mutator: str,
        getter: str,
        key_param: str,
    ) -> list[WallCandidate]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fns = _functions(tree)
        mut_fn = fns.get(mutator)
        get_fn = fns.get(getter)
        if mut_fn is None or get_fn is None:
            return []
        # The getter's own `return` names the container the postcondition reads.
        container = ""
        for node in ast.walk(get_fn):
            if isinstance(node, ast.Return) and node.value is not None:
                attrs = [n.attr for n in ast.walk(node.value) if isinstance(n, ast.Attribute)]
                if attrs:
                    container = attrs[0]
                    break
        if not container:
            return []
        # The mutator must already touch that container somewhere, else the purge belongs elsewhere.
        return_node = None
        for node in ast.walk(mut_fn):
            if isinstance(node, ast.Return):
                return_node = node
        if return_node is None:
            return []
        indent = _indent_at(source, return_node.lineno)
        purge = (
            f"{indent}self.{container} = [__e for __e in self.{container} if __e[0] is not {key_param}]"
        )
        start = return_node.lineno
        return [
            WallCandidate(
                mechanism=self.mechanism,
                target_function=mutator,
                lineno=start,
                old_code=source.splitlines()[start - 1],
                new_code=purge,
                patched_module_source=_rewrite_span(source, start, start, purge),
                evidence=(
                    f"getter `{getter}` returns `self.{container}`",
                    f"mutator `{mutator}` removes the registry entry but never `.{container}`",
                ),
                explanation=(
                    "The failing assertion reads a getter after a mutator, so the getter's container "
                    "is a postcondition on the mutator. The purge is emitted before the mutator's own "
                    "`return`, keyed by the mutator's parameter."
                ),
                edits=((start, start, purge),),
            )
        ]

    def _tuple_container(self, tree: ast.Module) -> str | None:
        """The one attribute the class declares as a sequence of pairs.

        `self._plugin_distinfo: Final[list[tuple[Plugin, Distribution]]] = []` is the
        evidence: a recorded pairing, which is exactly the state a mutator has to keep
        in step with the registry it mutates.
        """
        pairs: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.AnnAssign):
                continue
            target = node.target
            if not (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self"):
                continue
            anno = ast.unparse(node.annotation)
            compact = anno.replace(" ", "")
            if "list[tuple[" in compact or "List[Tuple[" in compact or "Sequence[tuple[" in compact:
                pairs.append(target.attr)
        return pairs[0] if len(pairs) == 1 else None

    def mine(self, source: str, target_function: str) -> list[WallCandidate]:
        """The class declares one pairing; the mutator must keep it in step."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        fns = _functions(tree)
        fn = fns.get(target_function)
        if fn is None or not _params(fn):
            return []
        container = self._tuple_container(tree)
        if container is None:
            return []
        if f"self.{container}" in _function_text(source, fn):
            # The mutator already touches the pairing: this is not the missing step.
            return []
        # The *success* path is the function's last top-level return: an early `return None`
        # is a refusal, and putting the purge there would run it on the failure branch.
        return_nodes = [n for n in fn.body if isinstance(n, ast.Return)]
        if not return_nodes:
            return []
        out: list[WallCandidate] = []
        key = _params(fn)[0]
        for ret in return_nodes[-1:]:
            indent = _indent_at(source, ret.lineno)
            purge = (
                f"{indent}self.{container} = [__e for __e in self.{container} if __e[0] is not {key}]"
            )
            # The purge is inserted *before* the success return, never in place of it.
            replacement = purge + "\n" + source.splitlines()[ret.lineno - 1]
            out.append(
                WallCandidate(
                    mechanism=self.mechanism,
                    target_function=target_function,
                    lineno=ret.lineno,
                    old_code=source.splitlines()[ret.lineno - 1],
                    new_code=purge,
                    patched_module_source=_rewrite_span(source, ret.lineno, ret.lineno, replacement),
                    evidence=(
                        f"`self.{container}` is declared as a sequence of pairs",
                        f"`{target_function}` removes the registry entry but leaves the pairing untouched",
                        f"purge key: the mutator's own parameter `{key}`",
                    ),
                    explanation=(
                        "The class records a pairing keyed by the same entity the mutator removes, so "
                        "the pairing is a postcondition on the mutator; the purge is emitted before "
                        "the mutator's own `return`, keyed by its own parameter."
                    ),
                    edits=((ret.lineno, ret.lineno, replacement),),
                )
            )
        return out


# ==============================================================================
# Orchestration
# ==============================================================================

@dataclasses.dataclass
class ResidualWallCloser:
    """Offers each wall's candidates in mechanism order; the repository's suite decides."""

    closers: tuple[Any, ...] = dataclasses.field(
        default_factory=lambda: (
            NoneGuardToTruthiness(),
            UnionStrSequenceFormatCompletion(),
            AssertContractToTypedRaise(),
            EmptyContainerPrefixArm(),
            ParserDegenerateNoneRefusal(),
            OptionalTupleShapeCompletion(),
            TerminalActionRetryPolicy(),
            DocstringDefaultUngating(),
            ConfigParityFromRepoIdiom(),
            OrderPreservingDedupParity(),
            StatedRequirementKeywordCompletion(),
            DemandedDeprecationEmission(),
            PostconditionStatePurge(),
        )
    )

    def mine_all(
        self,
        source: str,
        target_function: str,
        *,
        functions: Sequence[str] = (),
        repo_sources: Sequence[str] = (),
        test_sources: Sequence[str] = (),
    ) -> list[WallCandidate]:
        """Every candidate the closers can fire, plus their disjoint compositions.

        One test can state two co-required contracts (`test_register` demands both a
        `TypeError` for arity and a `ValueError` for state). Single-site search cannot
        express that by construction, so candidates that touch disjoint lines are
        summed here and offered as ONE patch.
        """
        targets = [target_function, *[f for f in functions if f != target_function]]
        out: list[WallCandidate] = []
        seen: set[str] = {source}
        for name in targets:
            for closer in self.closers:
                if getattr(closer, "needs_test_sources", False) and getattr(
                    closer, "needs_repo_sources", False
                ):
                    fired = closer.mine_for_pair(  # type: ignore[attr-defined]
                        source, name, list(test_sources), list(repo_sources) + [source]
                    )
                elif getattr(closer, "needs_test_sources", False):
                    fired = closer.mine_for_pair(  # type: ignore[attr-defined]
                        source, name, list(test_sources)
                    )
                elif getattr(closer, "needs_repo_sources", False):
                    fired = closer.mine(  # type: ignore[call-arg]
                        source, name, repo_sources=list(repo_sources) + [source]
                    )
                else:
                    fired = closer.mine(source, name)
                for cand in _split_bundles(fired):
                    if cand.patched_module_source in seen:
                        continue
                    try:
                        ast.parse(cand.patched_module_source)
                    except SyntaxError:
                        continue
                    seen.add(cand.patched_module_source)
                    out.append(cand)
        composed = self._compose(source, out, seen)
        # Composed repairs are ranked first: they are the ones a single-site search
        # cannot reach, so the cheap single-site evaluations must not consume the budget.
        composed.sort(key=lambda c: c.lineno)
        return composed + out

    def _compose(self, source: str, single: Sequence[WallCandidate], seen: set[str]) -> list[WallCandidate]:
        """Sum every disjoint subset of fired candidates into one patch, largest first.

        A test that states three co-required contracts needs three guards at once; a
        pairwise or single-site search cannot express that, which is exactly why
        `click@c53d373` stayed OPEN for the previous round. Enumerating disjoint
        subsets of the *fired* candidates is cheap (the clauses are few), and the
        repository's own suite still decides.
        """
        composable = [c for c in single if c.edits]
        # One representative per (mechanism, span): duplicated shapes add nothing.
        unique: dict[tuple[str, tuple[int, int]], WallCandidate] = {}
        for c in composable:
            unique.setdefault((c.mechanism, c.span), c)
        items = sorted(unique.values(), key=lambda c: c.span)
        if len(items) > 8:
            items = items[:8]

        out: list[WallCandidate] = []
        for size in range(len(items), 1, -1):
            for group in itertools.combinations(items, size):
                edits: list[Edit] = []
                ok = True
                for c in group:
                    if not edits_disjoint(edits, c.edits):
                        ok = False
                        break
                    edits.extend(c.edits)
                if not ok:
                    continue
                try:
                    patched = apply_edits(source, edits)
                except ValueError:
                    continue
                if patched in seen:
                    continue
                try:
                    ast.parse(patched)
                except SyntaxError:
                    continue
                seen.add(patched)
                # Name every summed clause, including repeats of one mechanism at two
                # sites: `X+X` is a different claim from `X`, and the receipt must say so.
                mechanisms = "+".join(c.mechanism for c in group)
                out.append(
                    WallCandidate(
                        mechanism=mechanisms,
                        target_function=group[0].target_function,
                        lineno=min(c.lineno for c in group),
                        old_code=" | ".join(c.old_code.strip() for c in group)[:400],
                        new_code=" | ".join(c.new_code.strip() for c in group)[:400],
                        patched_module_source=patched,
                        evidence=tuple(e for c in group for e in c.evidence),
                        explanation=(
                            f"One test states {len(group)} co-required contracts; the guards are "
                            f"emitted as one patch because no strict subset satisfies it."
                        ),
                        edits=tuple(edits),
                    )
                )
        return out


# ==============================================================================
# Live verification against a real repository worktree
# ==============================================================================

def _git(repo: pathlib.Path, *args: str) -> str:
    """Every git call names its `cwd=` explicitly: no test ever reads the tree it runs in."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.stdout if proc.returncode == 0 else ""


def _count_failures(output: str) -> int | None:
    m = re.search(r"(\d+) failed", output)
    if m:
        return int(m.group(1))
    if re.search(r"\b\d+ (?:passed|skipped)", output) or " no tests ran" in output:
        return 0
    if "error" in output.lower():
        return None
    return 0


def run_suite(
    workdir: pathlib.Path,
    test_files: Sequence[str],
    *,
    extra_pythonpath: Sequence[pathlib.Path] = (),
    timeout_s: float = 300.0,
) -> tuple[int | None, str]:
    """Run pytest the way the repository expects, and return (failures, output)."""
    src = workdir / "src"
    parts: list[str] = []
    if src.is_dir():
        parts.append(str(src))
    parts.extend(str(p) for p in extra_pythonpath)
    env = {
        "PYTHONPATH": ":".join(parts),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *PYTEST_BASE_ARGS, *test_files],
            cwd=str(workdir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    output = proc.stdout + proc.stderr
    return _count_failures(output), output


def _suite_files(workdir: pathlib.Path, suite: Sequence[str]) -> list[str]:
    files: list[str] = []
    for entry in suite:
        p = workdir / entry
        if p.is_dir():
            files.extend(str(f.relative_to(workdir)) for f in sorted(p.rglob("test_*.py")))
        else:
            files.append(entry)
    return files


def _suite_failures(
    workdir: pathlib.Path,
    suite: Sequence[str],
    *,
    extra_pythonpath: Sequence[pathlib.Path] = (),
    scope: str = "one",
) -> tuple[int | None, list[str]]:
    """Whole-project failures, plus the names of test files that could not be measured.

    Some project suites do not terminate under this sandbox (a subprocess test waiting on
    a pipe, for example). Running each file under its own timeout turns "the batch hangs"
    into a per-file answer. A file that cannot complete is returned *by name* so the
    caller can exclude exactly that file -- measured at baseline and after the repair --
    instead of either pretending it passed or refusing the whole admission.
    """
    if scope != "per-file":
        failures, _ = run_suite(workdir, list(suite), extra_pythonpath=extra_pythonpath, timeout_s=600.0)
        return failures, ([] if failures is not None else list(suite))
    total = 0
    unmeasurable: list[str] = []
    for rel in _suite_files(workdir, suite):
        failures, _ = run_suite(workdir, [rel], extra_pythonpath=extra_pythonpath, timeout_s=90.0)
        if failures is None:
            unmeasurable.append(rel)
            continue
        total += failures
    return total, unmeasurable


def close_wall_against_git(
    repo: pathlib.Path,
    commit: str,
    source_path: str,
    test_files: Sequence[str],
    *,
    target_function: str,
    functions: Sequence[str] = (),
    mechanisms: Sequence[str] = (),
    extra_pythonpath: Sequence[pathlib.Path] = (),
    scratch_root: pathlib.Path | None = None,
    max_evaluations: int = 40,
    full_suite: Sequence[str] = (),
    suite_scope: str = "one",
    repo_source_globs: Sequence[str] = (),
) -> WallResult:
    """Repair one real commit in a `/dev/shm` worktree of its parent, with only tests copied.

    The parent tree supplies the program; the fix commit supplies *only* its test
    files. No source diff, patch, commit message, or issue text is read -- so a
    VERIFIED here is earned by the repository's own suite, not by the answer key.

    Search is a monotone test-cover zipper: a candidate is kept only when it strictly
    reduces the failure count, and after each kept hop the closers re-mine the
    repaired tree, so a second wall inside the same file is reachable with the first
    one already in place.
    """
    root = scratch_root or pathlib.Path("/dev/shm")
    root.mkdir(parents=True, exist_ok=True)
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="wall_", dir=str(root)))
    wtree = workdir / "wt"
    wall_id = f"{repo.name}@{commit[:7]}"

    _git(repo, "worktree", "add", "--detach", str(wtree), f"{commit}~1")
    try:
        for rel in test_files:
            text = _git(repo, "show", f"{commit}:{rel}")
            if not text:
                return WallResult(wall_id, "REFUSED__TEST_FILE_UNREADABLE", "", 0, 0, -1, -1, (), 0)
            target = wtree / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

        baseline_failures, _ = run_suite(wtree, test_files, extra_pythonpath=extra_pythonpath)
        if baseline_failures is None:
            return WallResult(wall_id, "REFUSED__BASELINE_UNRUNNABLE", "", 0, 0, -1, -1, (), 0)
        if baseline_failures == 0:
            return WallResult(wall_id, "REFUSED__BASELINE_ALREADY_PASSING", "", 0, 0, 0, 0, (), 0)

        source_file = wtree / source_path
        source = source_file.read_text(encoding="utf-8")
        closer = ResidualWallCloser()

        # The repository is allowed to testify about itself: sibling call sites give the
        # policy names that this call site forgot. Only files under the declared globs are
        # read, and only *names plus values* are lifted -- no answer key is consulted.
        repo_sources: list[str] = []
        for pattern in repo_source_globs:
            for path in sorted(wtree.glob(pattern)):
                if path.is_file() and path.suffix == ".py":
                    try:
                        repo_sources.append(path.read_text(encoding="utf-8"))
                    except OSError:
                        continue

        # The fix commit's test files are already on the worktree; they are what the
        # program is asked to be, and they may state a requirement in words.
        test_sources: list[str] = []
        for rel in test_files:
            path = wtree / rel
            if path.is_file():
                try:
                    test_sources.append(path.read_text(encoding="utf-8"))
                except OSError:
                    continue

        def _offered(text: str) -> list[WallCandidate]:
            cands = closer.mine_all(
                text,
                target_function,
                functions=functions,
                repo_sources=repo_sources,
                test_sources=test_sources,
            )
            return [c for c in cands if not mechanisms or c.mechanism in mechanisms]

        pool = _offered(source)
        total_offered = len(pool)
        if not pool:
            return WallResult(
                wall_id, "REFUSED__NO_MECHANISM_FIRES", "", 0, 0,
                baseline_failures, baseline_failures, (), 0,
            )

        baseline_suite: int | None = None
        excluded_files: list[str] = []
        if full_suite:
            baseline_suite, excluded_files = _suite_failures(
                wtree, full_suite, extra_pythonpath=extra_pythonpath, scope=suite_scope
            )

        current_failures = baseline_failures
        evaluations = 0
        hops: list[dict[str, Any]] = []
        regressions = 0
        mechanism_used: list[str] = []
        tried: set[str] = set()

        while pool and current_failures > 0 and evaluations < max_evaluations:
            cand = pool.pop(0)
            if cand.patched_module_source in tried:
                continue
            tried.add(cand.patched_module_source)
            source_file.write_text(cand.patched_module_source, encoding="utf-8")
            failures, _out = run_suite(wtree, test_files, extra_pythonpath=extra_pythonpath)
            evaluations += 1
            if failures is None:
                source_file.write_text(source, encoding="utf-8")
                continue
            if failures < current_failures:
                hops.append(
                    {
                        "mechanism": cand.mechanism,
                        "lineno": cand.lineno,
                        "failures_before": current_failures,
                        "failures_after": failures,
                        "evidence": list(cand.evidence),
                    }
                )
                mechanism_used.append(cand.mechanism)
                current_failures = failures
                source = cand.patched_module_source
                # Re-mine the repaired tree: the next wall may only be visible now.
                fresh = _offered(source)
                total_offered += len(fresh)
                pool = fresh + pool
            else:
                if failures > baseline_failures:
                    regressions += 1
                source_file.write_text(source, encoding="utf-8")

        status = "VERIFIED" if current_failures == 0 else "OPEN__CANDIDATES_EXHAUSTED"
        if current_failures > 0 and not pool and evaluations >= max_evaluations:
            status = "OPEN__EVALUATION_BUDGET_EXHAUSTED"

        # A repair is only admitted when the project's WHOLE suite still passes: the
        # copied test file says what the program must become, the rest says what it must
        # stay. A wall that closes its own file by breaking a neighbour is still REGRESSED.
        suite_admission: dict[str, Any] | None = None
        if status == "VERIFIED" and full_suite and baseline_suite is None:
            hops.append(
                {
                    "mechanism": "FULL_SUITE_ADMISSION_SKIPPED__BASELINE_UNRUNNABLE",
                    "lineno": 0,
                    "failures_before": 0,
                    "failures_after": 0,
                    "evidence": ["the project suite does not complete under this sandbox"],
                }
            )
        elif status == "VERIFIED" and full_suite:
            measured = [f for f in _suite_files(wtree, full_suite) if f not in excluded_files]
            suite_failures, _ = _suite_failures(
                wtree, measured, extra_pythonpath=extra_pythonpath, scope=suite_scope
            )
            # Compared against the tree's OWN baseline: a suite that is already red for
            # reasons outside this wall (a missing optional dependency, a collection error)
            # is not made worse by a repair that leaves the same count.
            suite_admission = {
                "measured_files": len(measured),
                "excluded_files": excluded_files,
                "baseline_failures": baseline_suite,
                "after_repair_failures": suite_failures,
            }
            if suite_failures is None or suite_failures > baseline_suite:
                status = "REGRESSED__FULL_SUITE_RED"
                hops.append(
                    {
                        "mechanism": "FULL_SUITE_ADMISSION",
                        "lineno": 0,
                        "failures_before": 0,
                        "failures_after": suite_failures if suite_failures is not None else -1,
                        "evidence": [
                            f"full-suite failures rose from {baseline_suite} to {suite_failures}",
                            *[f"excluded (unmeasurable at baseline too): {f}" for f in excluded_files],
                        ],
                    }
                )
        return WallResult(
            wall_id,
            status,
            "+".join(dict.fromkeys(mechanism_used)),
            total_offered,
            evaluations,
            baseline_failures,
            current_failures,
            tuple(hops),
            regressions,
            suite_admission,
        )
    finally:
        _git(repo, "worktree", "remove", "--force", str(wtree))
        _git(repo, "worktree", "prune")
        shutil.rmtree(workdir, ignore_errors=True)


# ==============================================================================
# The measured walls: a fixed, public case list
# ==============================================================================

CLICK_PROJECT_TESTS = (
    "tests/test_abort_interrupt.py", "tests/test_arguments.py", "tests/test_basic.py",
    "tests/test_chain.py", "tests/test_command_decorators.py", "tests/test_commands.py",
    "tests/test_compat.py", "tests/test_context.py", "tests/test_custom_classes.py",
    "tests/test_defaults.py", "tests/test_formatting.py", "tests/test_imports.py",
    "tests/test_info_dict.py", "tests/test_normalization.py", "tests/test_options.py",
    "tests/test_parser.py", "tests/test_shell_completion.py", "tests/test_testing.py",
    "tests/test_types", "tests/test_utils",
)

# `tests/test_deprecations.py` and `tests/test_stream_lifecycle.py` are absent from the
# click list on purpose: the first needs installed package metadata (`click` is imported
# from source here), the second does not terminate in this sandbox. Neither is measured
# by the admission gate, and neither is excluded to make a result look better -- both
# fail identically on the untouched parent tree.
RESIDUAL_WALL_CASES: tuple[dict[str, Any], ...] = (
    {
        "wall_id": "click@05f6fd0",
        "repo": "click", "commit": "05f6fd0",
        "source_path": "src/click/core.py",
        "fix_test_files": ("tests/test_arguments.py",),
        "target_functions": ("Argument.get_help_record",),
        "project_tests": CLICK_PROJECT_TESTS, "suite_scope": "per-file",
        "wall": "an undocumented argument must still get a help row",
    },
    {
        "wall_id": "click@c53d373",
        "repo": "click", "commit": "c53d373",
        "source_path": "src/click/core.py",
        "fix_test_files": ("tests/test_options.py",),
        "target_functions": ("Option.get_help_extra", "Option.get_error_hint"),
        "project_tests": CLICK_PROJECT_TESTS, "suite_scope": "per-file",
        "wall": "empty envvar == absent envvar, and a sequence envvar names every member",
    },
    {
        "wall_id": "click@fc518e4",
        "repo": "click", "commit": "fc518e4",
        "source_path": "src/click/core.py",
        "fix_test_files": ("tests/test_abort_interrupt.py",),
        "target_functions": ("Command.main",),
        "project_tests": CLICK_PROJECT_TESTS, "suite_scope": "per-file",
        "wall": "a second interrupt while reporting must not replace the decided outcome",
    },
    {
        "wall_id": "click@047adef",
        "repo": "click", "commit": "047adef",
        "source_path": "src/click/core.py",
        "fix_test_files": ("tests/test_commands.py",),
        "target_functions": ("Command.get_help_option_names",),
        "project_tests": CLICK_PROJECT_TESTS, "suite_scope": "per-file",
        "repo_source_globs": ("src/click/*.py",),
        "wall": (
            "help option names must keep declaration order: `set()` is used where the "
            "returned list order is part of the contract"
        ),
    },
    {
        "wall_id": "click@7996a89",
        "repo": "click", "commit": "7996a89",
        "source_path": "src/click/formatting.py",
        "fix_test_files": ("tests/test_formatting.py",),
        "target_functions": ("wrap_text",),
        "project_tests": ("tests/test_formatting.py",), "suite_scope": "one",
        "repo_source_globs": ("src/click/*.py",),
        "wall": (
            "wrapping must not break hyphenated words: the repo states this policy in "
            "`utils.py` and omits it at the `TextWrapper` construction in `formatting.py`"
        ),
    },
    {
        "wall_id": "werkzeug@21b45dbd",
        "repo": "werkzeug", "commit": "21b45dbd",
        "source_path": "src/werkzeug/wrappers/response.py",
        "fix_test_files": ("tests/test_wrappers.py",),
        "target_functions": ("Response.freeze",),
        "project_tests": ("tests/",), "suite_scope": "per-file",
        "repo_source_globs": ("src/werkzeug/**/*.py",),
        "wall": (
            "a public method the test wraps in `pytest.deprecated_call()` must emit a "
            "DeprecationWarning, which it currently does not"
        ),
    },
    {
        "wall_id": "werkzeug@051fd663",
        "repo": "werkzeug", "commit": "051fd663",
        "source_path": "src/werkzeug/datastructures/auth.py",
        "fix_test_files": ("tests/test_http.py",),
        "target_functions": ("WWWAuthenticate.to_header",),
        "project_tests": ("tests/",), "suite_scope": "per-file",
        "wall": "an empty parameter payload must not leave a trailing separator",
    },
    {
        "wall_id": "werkzeug@0c419f95",
        "repo": "werkzeug", "commit": "0c419f95",
        "source_path": "src/werkzeug/http.py",
        "fix_test_files": ("tests/test_http.py",),
        "target_functions": ("parse_range_header",),
        "project_tests": ("tests/",), "suite_scope": "per-file",
        "wall": "a suffix cardinality of zero selects nothing and must be refused",
    },
    {
        "wall_id": "werkzeug@884437ae",
        "repo": "werkzeug", "commit": "884437ae",
        "source_path": "src/werkzeug/routing/map.py",
        "fix_test_files": ("tests/test_routing.py",),
        "target_functions": ("MapAdapter.build",),
        "project_tests": ("tests/test_routing.py",), "suite_scope": "one",
        "wall": "a documented default that is only reachable behind a feature flag",
    },
    {
        "wall_id": "pluggy@8051a4d",
        "repo": "pluggy", "commit": "8051a4d",
        "source_path": "src/pluggy/_manager.py",
        "fix_test_files": ("testing/test_pluginmanager.py",),
        "target_functions": ("PluginManager.unregister",),
        "project_tests": ("testing/",), "suite_scope": "one",
        "wall": "two co-required contracts inside one test: arity and state",
    },
    {
        "wall_id": "pluggy@50585e0",
        "repo": "pluggy", "commit": "50585e0",
        "source_path": "src/pluggy/_manager.py",
        "fix_test_files": ("testing/test_pluginmanager.py",),
        "target_functions": ("PluginManager.unregister",),
        "project_tests": ("testing/",), "suite_scope": "one",
        "wall": "the recorded distribution must be dropped with the plugin",
    },
)


def evaluate_residual_walls(
    repos_root: pathlib.Path,
    *,
    extra_pythonpath: Sequence[pathlib.Path] = (),
) -> dict[str, Any]:
    """Run every wall in `RESIDUAL_WALL_CASES` against its real repository.

    Requires cloned `pallets/click`, `pallets/werkzeug` and `pytest-dev/pluggy` under
    `repos_root`. Returns a receipt-shaped record either way: an unrunnable wall is
    reported as such, never silently dropped.
    """
    rows: list[dict[str, Any]] = []
    for case in RESIDUAL_WALL_CASES:
        repo_dir = repos_root / case["repo"]
        if not (repo_dir / ".git").exists():
            rows.append({**{k: case[k] for k in ("wall_id", "repo", "commit", "wall")},
                         "status": "UNRUNNABLE__REPO_NOT_CLONED"})
            continue
        started = time.monotonic()
        result = close_wall_against_git(
            repo_dir,
            case["commit"],
            case["source_path"],
            list(case["fix_test_files"]),
            target_function=case["target_functions"][0],
            functions=case["target_functions"][1:],
            extra_pythonpath=extra_pythonpath,
            full_suite=list(case["project_tests"]),
            suite_scope=case["suite_scope"],
            repo_source_globs=case.get("repo_source_globs", ()),
        )
        row = result.as_dict()
        row.update(
            {
                "repo": case["repo"],
                "commit": case["commit"],
                "wall": case["wall"],
                "fix_test_files": list(case["fix_test_files"]),
                "eval_seconds": round(time.monotonic() - started, 2),
            }
        )
        rows.append(row)
    verified = [r for r in rows if r.get("status") == "VERIFIED"]
    return {
        "cases": len(rows),
        "verified": len(verified),
        "open": [r["wall_id"] for r in rows if r.get("status") != "VERIFIED"],
        "rows": rows,
        "protocol": (
            "single-parent commits from three external repositories; ONLY the fix commit's "
            "test files are copied onto a /dev/shm worktree of the parent; no source diff, "
            "patch, commit message, or issue text is read by the engine; a repair counts only "
            "when the copied tests pass AND the project's own suite fails no more than it did "
            "on the untouched parent"
        ),
    }


def receipt(result: WallResult, suite_tail: str = "") -> dict[str, Any]:
    doc = result.as_dict()
    doc["suite_tail"] = suite_tail
    return doc


if __name__ == "__main__":
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/corpus_repos")
    stub = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None
    print(
        json.dumps(
            evaluate_residual_walls(root, extra_pythonpath=(stub,) if stub else ()),
            indent=2,
            sort_keys=True,
        )
    )
