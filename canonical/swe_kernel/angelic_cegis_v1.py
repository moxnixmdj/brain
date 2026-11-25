#!/usr/bin/env python3
"""Angelic spec abduction + observational-equivalence STUN/CEGIS.

THE PROBLEM.  When a synthesizer meets a name it cannot resolve it emits
``FOREIGN_IDENT_UNBOUND`` and gives up.  Measured on the real corpora
(`real_fix_pairs_20261119_V1.json`, `single_line_fix_commits_20261123_V1.json`),
the fixes that a single-expression grammar cannot reach are:

  * **multi-statement / helper** bodies -- 72 of 87 commits need more than one
    expression (``_eval_extra_set`` / ``_splice_operand`` style helpers);
  * **local data-flow normalisation** -- ``item.include_group`` becomes a local
    ``include_group`` before use;
  * **relational guards across frames** -- ``if name not in ("__version__",
    "__version_info__")``, ``if self.show_envvar and self.envvar is not None``,
    ``if frozen is True and a.on_setattr is not setters.NO_OP``.

THE METHOD.  Instead of refusing, *abduce a specification* from the scope and
search for an expression that satisfies it:

  1. **Harvest** the vocabulary: live locals, module globals, imports, enclosing
     class ``__dict__`` attributes, names mined from sibling call sites, and the
     repo's own helper schemas.  Nothing outside the harvested vocabulary is ever
     emitted -- an invented name is a refusal, not a guess.
  2. **Enumerate** candidates from a typed grammar over that vocabulary,
     including multi-step bodies (intermediate locals) and freshly synthesised
     helper functions.
  3. **Deduplicate modulo the e-graph**: two candidates that lower to the same
     Meaning-IR e-class are the same candidate.  This is what stops the search
     from re-testing ``a + b`` and ``b + a`` as if they were different ideas.
  4. **CEGIS**: execute each survivor against a caller-supplied oracle on a
     witness set.  A mismatch is a counterexample, not a failure -- it is added
     to the witness set and the next candidate must also satisfy it.
  5. **Admit only what ran.**  ``admitted=True`` is emitted iff the candidate was
     executed and matched on *every* witness.  No execution, no admission.

Everything runs under ``fresh_bytecode`` semantics (``PYTHONDONTWRITEBYTECODE=1``):
candidates are ``exec``'d from source strings, never imported from a stale
``.pyc``, and the restricted executor exposes only an allowlisted builtin set.

Authority: NONE.  The oracle is the caller's; this module never certifies its own
output.
"""
from __future__ import annotations

import ast
import itertools
import os
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Mapping, Sequence

from canonical.swe_kernel import guarded_meaning_ir_v1 as mir

SCHEMA = "PROJECT_BRAIN_ANGELIC_CEGIS_V1"

#: The only builtins a synthesised expression may use.  Anything else is a
#: refusal -- an invented capability is not a synthesised one.
SAFE_BUILTINS: dict[str, Any] = {
    "len": len, "isinstance": isinstance, "issubclass": issubclass,
    "getattr": getattr, "hasattr": hasattr, "setattr": setattr,
    "list": list, "tuple": tuple, "dict": dict, "set": set, "frozenset": frozenset,
    "sorted": sorted, "reversed": lambda v: list(reversed(v)),
    "min": min, "max": max, "sum": sum, "abs": abs, "any": any, "all": all,
    "range": range, "enumerate": enumerate, "zip": zip,
    "int": int, "float": float, "str": str, "bool": bool, "repr": repr,
    "True": True, "False": False, "None": None,
    "NotImplementedError": NotImplementedError, "TypeError": TypeError,
    "ValueError": ValueError, "KeyError": KeyError, "IndexError": IndexError,
    "AttributeError": AttributeError, "ZeroDivisionError": ZeroDivisionError,
}

_CONST_literals = [
    "0", "1", "-1", "2", "''", "' '", "None", "True", "False", "()", "[]", "{}",
]


# --------------------------------------------------------------------------- #
# 1. Scope harvesting
# --------------------------------------------------------------------------- #


@dataclass
class Scope:
    """Everything a candidate expression is allowed to mention."""

    locals: tuple[str, ...] = ()
    globals: tuple[str, ...] = ()
    params: tuple[str, ...] = ()
    attributes: dict[str, tuple[str, ...]] = field(default_factory=dict)
    helpers: tuple[str, ...] = ()
    types: tuple[str, ...] = ()
    literals: tuple[str, ...] = ()
    binds: tuple[str, ...] = ()
    #: call expressions that occur at the target, verbatim -- the raw material
    #: for the call-shape family (wrap, rename a method, append an argument)
    calls: tuple[str, ...] = ()

    def names(self) -> tuple[str, ...]:
        # An attribute owner is a first-class name: without ``self`` in the
        # vocabulary, ``self.show_envvar`` is unreachable and the synthesiser
        # would refuse exactly the relational guards real fixes need.
        return tuple(dict.fromkeys(self.locals + self.params + self.globals
                                   + tuple(self.attributes)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "locals": list(self.locals), "globals": list(self.globals),
            "params": list(self.params),
            "attributes": {k: list(v) for k, v in self.attributes.items()},
            "helpers": list(self.helpers), "types": list(self.types),
            "literals": list(self.literals), "binds": list(self.binds),
            "calls": list(self.calls), "name_count": len(self.names()),
        }


def harvest_scope(source: str, *, target: str | None = None,
                  extra_sources: Mapping[str, str] | None = None,
                  env: Mapping[str, Any] | None = None,
                  method_vocabulary: Mapping[str, Sequence[str]] | None = None) -> Scope:
    """Harvest the vocabulary visible at ``target`` from the sources.

    ``target`` is a function name (or ``Class.method``).  The enclosing class
    body and module top level are both harvested, so a guard may relate a live
    local to an enclosing-frame attribute -- the ``Metadata.__dict__`` case.
    """
    tree = ast.parse(source)
    fn_node: ast.AST | None = None
    class_stack: list[ast.ClassDef] = []
    globals_: set[str] = set()
    attributes: dict[str, set[str]] = {}
    helpers: set[str] = set()
    types: set[str] = set()
    literals: set[str] = set()

    def visit_class(cls: ast.ClassDef) -> None:
        for st in cls.body:
            if isinstance(st, ast.Assign):
                for t in st.targets:
                    if isinstance(t, ast.Name):
                        globals_.add(t.id)
            elif isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
                globals_.add(st.target.id)
            elif isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                helpers.add(f"{cls.name}.{st.name}")
                helpers.add(st.name)
        types.add(cls.name)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            helpers.add(node.name)
            if node.name == target:
                fn_node = node
            for a in node.args.args:
                globals_.add(a.arg)
        elif isinstance(node, ast.ClassDef):
            class_stack.append(node)
            visit_class(node)
            for st in node.body:
                if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if f"{node.name}.{st.name}" == target:
                        fn_node = st
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    globals_.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            globals_.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                globals_.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.If):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    helpers.add(sub.name)

    local_names: set[str] = set()
    params: set[str] = set()
    calls: set[str] = set()
    if fn_node is not None:
        args = fn_node.args
        for a in list(args.args) + list(args.kwonlyargs):
            if a.arg not in {"self", "cls"}:
                params.add(a.arg)
        for st in ast.walk(fn_node):
            if isinstance(st, ast.Name) and isinstance(st.ctx, ast.Store):
                local_names.add(st.id)
            elif isinstance(st, ast.Attribute) and isinstance(st.value, ast.Name):
                attributes.setdefault(st.value.id, set()).add(st.attr)
            elif isinstance(st, ast.Constant) and isinstance(st.value, (str, int, float, bool)):
                literals.add(repr(st.value))
            elif isinstance(st, ast.Call):
                try:
                    calls.add(ast.unparse(st))
                except Exception:
                    pass
    # attributes of any name we know about (harvested from every source)
    for src in [source] + list((extra_sources or {}).values()):
        try:
            for st in ast.walk(ast.parse(src)):
                if isinstance(st, ast.Attribute) and isinstance(st.value, ast.Name):
                    attributes.setdefault(st.value.id, set()).add(st.attr)
                elif isinstance(st, ast.Constant) and isinstance(st.value, str):
                    literals.add(repr(st.value))
        except SyntaxError:
            continue
    for k in (env or {}):
        globals_.add(str(k))
    # ``method_vocabulary`` is EXPLICIT angelic foreknowledge: which method names
    # a receiver is allowed to be given.  Without it a ``split`` -> ``rsplit``
    # rename is unreachable BY CONSTRUCTION -- the grammar will not invent a
    # method name, because an invented name is a fabricated repair.  A caller
    # that supplies it is recorded as having supplied it.
    for recv, names in (method_vocabulary or {}).items():
        attributes.setdefault(str(recv), set()).update(str(n) for n in names)
    # A module that *defines* ``__version__`` and ``__version_info__`` is telling
    # us those two strings are meaningful, so they enter the literal vocabulary.
    # Harvested, never invented -- the set-membership guard fix needs both.
    for g in sorted(globals_):
        if (g.startswith("__") and g.endswith("__")) or g.isupper():
            literals.add(repr(g))
    # helper names mined from sibling call sites, if extra sources were given
    for src in (extra_sources or {}).values():
        try:
            for st in ast.walk(ast.parse(src)):
                if isinstance(st, ast.Call) and isinstance(st.func, ast.Name):
                    helpers.add(st.func.id)
        except SyntaxError:
            continue
    return Scope(
        locals=tuple(sorted(local_names - params)),
        globals=tuple(sorted(globals_ - local_names)),
        params=tuple(sorted(params)),
        attributes={k: tuple(sorted(v)) for k, v in sorted(attributes.items())},
        helpers=tuple(sorted(helpers)),
        types=tuple(sorted(types)),
        literals=tuple(sorted(literals))[:64],
        calls=tuple(sorted(calls))[:24],
    )


# --------------------------------------------------------------------------- #
# 2. Candidate enumeration (angelic grammar)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Candidate:
    expr: str
    schema: str
    binds: tuple[tuple[str, str], ...] = ()      # (local_name, expr_source)
    helpers: tuple[tuple[str, str], ...] = ()    # (helper_name, def_source)
    term: Any = None

    def source(self) -> str:
        parts = [f"{n} = {e}" for n, e in self.binds]
        parts += [h for _n, h in self.helpers]
        return "\n".join(parts + [f"return {self.expr}"])


def _atoms(scope: Scope, *, guard: bool) -> list[str]:
    out: list[str] = []
    for n in scope.names():
        out.append(n)
        if guard:
            out += [f"not {n}", f"{n} is None", f"{n} is not None"]
    for obj, attrs in scope.attributes.items():
        if obj in scope.names():
            for a in attrs:
                out.append(f"{obj}.{a}")
                if guard:
                    out += [f"{obj}.{a} is None", f"{obj}.{a} is not None"]
    return out


def _predicates(scope: Scope) -> list[str]:
    """Atomic predicates, including the *relational* ones real fixes need."""
    preds: list[str] = []
    names = scope.names()
    lits = [x for x in scope.literals if len(x) <= 24][:24]
    for n in names:
        preds += [f"{n} is None", f"{n} is not None"]
        for lit in lits[:6]:
            preds += [f"{n} == {lit}", f"{n} != {lit}"]
        preds.append(f"len({n}) > 0")
    for obj, attrs in scope.attributes.items():
        if obj not in names:
            continue
        for a in attrs[:24]:
            preds += [f"{obj}.{a} is None", f"{obj}.{a} is not None",
                      f"{obj}.{a} is True", f"{obj}.{a} is False",
                      f"hasattr({obj}, {a!r})"]
            for lit in lits[:4]:
                preds.append(f"{obj}.{a} == {lit}")
            if len(lits) >= 2:
                str_lits = [x for x in lits if x.startswith(("'", '"'))][:4]
                for x, y in itertools.combinations(str_lits, 2):
                    preds.append(f"{obj}.{a} in ({x}, {y})")
                    preds.append(f"{obj}.{a} not in ({x}, {y})")
    for t in scope.types[:12]:
        for n in names[:8]:
            preds.append(f"isinstance({n}, {t})")
    # set membership: the ``name not in ("__version__", "__version_info__")`` shape
    if lits:
        small = [x for x in lits if x.startswith(("'", '"'))][:4]
        if len(small) >= 2:
            for n in names[:12]:
                # pairs, not the whole set: the measured fix is a 2-tuple, and a
                # 3-tuple that happens to agree on the witnesses is over-general
                for x, y in itertools.combinations(small, 2):
                    preds.append(f"{n} in ({x}, {y})")
                    preds.append(f"{n} not in ({x}, {y})")
    return preds


def _multistep_grammar(scope: Scope, *, max_atoms: int = 32) -> Iterable[Candidate]:
    """``_v = expr; return _v.attr`` -- normalise before you use.

    This is the shape behind ``item.include_group`` -> ``include_group`` and the
    ``Metadata.__dict__`` guards: bind the intermediate, then relate to it.
    """
    atoms = _atoms(scope, guard=False)[:max_atoms]
    for a in atoms:
        for obj, attrs in scope.attributes.items():
            for at in attrs[:8]:
                yield Candidate(f"_v.{at}", "bind_attr", binds=(("_v", a),))
        yield Candidate(f"_v[0]", "bind_index", binds=(("_v", a),))
        yield Candidate(f"len(_v)", "bind_len", binds=(("_v", a),))
    for h in scope.helpers[:12]:
        yield Candidate(f"_v", "bind_call", binds=(("_v", f"{h}()"),))


def _helper_grammar(scope: Scope, *, max_atoms: int = 32) -> Iterable[Candidate]:
    """Synthesise a *helper function* and call it (the ``_eval_extra_set`` shape)."""
    atoms = _atoms(scope, guard=False)[:max_atoms]
    for h in scope.helpers[:8]:
        for a in atoms[:8]:
            yield Candidate(f"{h}({a})", "helper_wrap")
    for a in atoms[:max_atoms]:
        for b in atoms[:8]:
            if a == b:
                continue
            body = f"return {a} if {a} is not None else {b}"
            yield Candidate("_brain_h(x)", "helper_new",
                            helpers=(("_brain_h",
                                      f"def _brain_h(x):\n    {body}\n"
                                      f"    return {b}"),))
            break


# --------------------------------------------------------------------------- #
# 3. Restricted execution + observational equivalence
# --------------------------------------------------------------------------- #


def fresh_bytecode_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """An environment that cannot reuse a stale ``.pyc`` (``fresh_bytecode``)."""
    env = dict(base or os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONPATH", None)
    return env


class CandidateRefused(Exception):
    """The candidate could not be executed in the restricted environment."""


def _restricted_eval(expr: str, names: Mapping[str, Any], *,
                     filename: str = "<angelic>") -> Any:
    env = dict(names)
    env["__builtins__"] = dict(SAFE_BUILTINS)
    try:
        code = compile(expr, filename, "eval")
    except SyntaxError as exc:
        raise CandidateRefused(f"SNTAX:{exc.msg}") from exc
    return eval(code, env)  # noqa: S307 - restricted env, caller-supplied names


def _restricted_exec(src: str, names: Mapping[str, Any], *,
                     filename: str = "<angelic>") -> dict[str, Any]:
    env = dict(names)
    env["__builtins__"] = dict(SAFE_BUILTINS)
    code = compile(src, filename, "exec")
    exec(code, env)  # noqa: S102 - restricted env, caller-supplied names
    return env


def observe(fn: Any, env: Mapping[str, Any]) -> tuple[str, Any]:
    """``('value', v)`` or ``('error', ExceptionType)`` -- never a crash."""
    try:
        return ("value", fn(dict(env)))
    except Exception as exc:  # noqa: BLE001 - an observed error is a result
        return ("error", type(exc).__name__)


def observational_equivalence(a: Any, b: Any, inputs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Two expressions are equivalent iff they agree on every witness input.

    SOUNDNESS.  An expression that raises on every witness has NOT been shown
    equivalent to anything -- "both crashed" is the absence of a specification,
    not a match.  So the oracle must produce at least one real value before any
    equivalence claim is possible; otherwise the verdict is
    ``NO_SPECIFICATION`` and ``equivalent`` is False.  This is what stops a
    candidate that merely raises the same ``NameError`` as an underspecified
    oracle from being admitted.
    """
    rows: list[dict[str, Any]] = []
    a_values = 0
    b_values = 0
    for i, env in enumerate(inputs):
        oa, ob = observe(a, env), observe(b, env)
        if oa[0] == "value":
            a_values += 1
        if ob[0] == "value":
            b_values += 1
        rows.append({"i": i, "a": list(oa), "b": list(ob), "equal": oa == ob})
        if oa != ob:
            return {"schema": SCHEMA, "equivalent": False, "counterexample": rows[-1],
                    "witnesses": len(inputs)}
    if a_values == 0 or b_values == 0:
        return {"schema": SCHEMA, "equivalent": False, "counterexample": None,
                "witnesses": len(inputs), "rows": rows,
                "reason": "NO_SPECIFICATION",
                "note": ("neither side ever produced a value on these witnesses, so "
                         "there is no behaviour to be equivalent to")}
    return {"schema": SCHEMA, "equivalent": True, "counterexample": None,
            "witnesses": len(inputs), "rows": rows}


# --------------------------------------------------------------------------- #
# 4. CEGIS
# --------------------------------------------------------------------------- #


def _is_constant_expr(expr: str) -> bool:
    """True for a candidate that mentions no name at all (a bare literal)."""
    body = expr.strip()
    if body in {"True", "False", "None"}:
        return True
    if body[:1] in {"'", '"'} and body[-1:] == body[:1]:
        return True
    try:
        float(body)
        return True
    except ValueError:
        return False


def _best(matches: Sequence[str]) -> str:
    """Prefer a candidate that USES the inputs over one that ignores them.

    ``2`` and ``price - disc`` agree on a one-witness set, but only one of them
    is a repair; the other is a coincidence wearing a repair's clothes.  So a
    bare literal may only be chosen when nothing that names an input matched.
    """
    named = [m for m in matches if not _is_constant_expr(m)]
    return min(named or list(matches), key=len)


def candidate_space(scope: Scope, *, kind: str = "value",
                    budget: int = 4096) -> Iterator[tuple[str, str]]:
    """Yield ``(expr, schema)`` in the same order the search would try them.

    Public so that "is this expression even REACHABLE?" is a question the
    grammar can answer without pretending to have witnesses.  A fix shape that
    is absent from this stream is a grammar gap, and reporting it as one is
    more useful than a silent refusal.
    """
    n = 0
    atoms = _atomic_expressions(scope, guard=(kind == "guard"))
    for expr in atoms:
        yield expr, "atom"
        n += 1
        if n >= budget:
            return
    scored = list(atoms)
    if kind == "guard":
        for op in ("and", "or"):
            for a, b in itertools.combinations(scored[:20], 2):
                yield f"{a} {op} {b}", f"{op}2"
                n += 1
                if n >= budget:
                    return
        for a, b, c in itertools.islice(itertools.combinations(scored[:14], 3), 256):
            yield f"{a} and {b} and {c}", "and3"
            n += 1
            if n >= budget:
                return
        return
    for opn in ("-", "+", "*", "//", "%", "/"):
        for a, b in itertools.permutations(scored[:16], 2):
            yield f"{a} {opn} {b}", "binop"
            n += 1
            if n >= budget:
                return
    pred_pool = [pr for pr in itertools.islice(_predicates(scope), 96)][:12]
    name_set = set(scope.names())
    vals = ([e for e in scored if e in name_set]
            + [e for e in scored if e.startswith("[") and e.endswith("]")
               and e[1:-1] in name_set]
            + [e for e in scored if e.startswith("list(") and e.endswith(")")
               and e[5:-1] in name_set])[:12]
    for pr in pred_pool:
        for a, b in itertools.permutations(vals, 2):
            yield f"{a} if {pr} else {b}", "select"
            n += 1
            if n >= budget:
                return


def _atomic_expressions(scope: Scope, *, guard: bool) -> list[str]:
    """The atomic vocabulary a composite may be built from (order-preserving)."""
    out: list[str] = []
    names = scope.names()
    for n in names:
        out.append(n)
        out.append(f"len({n})")
        if guard:
            out += [f"not {n}", f"{n} is None", f"{n} is not None"]
    for obj, attrs in scope.attributes.items():
        if obj not in names:
            continue
        for a in attrs[:24]:
            out.append(f"{obj}.{a}")
            if guard:
                out += [f"{obj}.{a} is None", f"{obj}.{a} is not None",
                        f"{obj}.{a} is True", f"{obj}.{a} is False",
                        f"hasattr({obj}, {a!r})"]
    if guard:
        out += _predicates(scope)
    else:
        for h in scope.helpers[:16]:
            out.append(f"{h}()")
        # ---- call-shape family -------------------------------------------
        # The measured corpus is dominated by edits to an EXISTING call: wrap it
        # (``tuple(f(x))``), rename the method (``split`` -> ``rsplit``), or
        # append an argument.  A grammar that only composes fresh expressions
        # from names cannot reach any of those, so the calls already present at
        # the target are first-class atoms and are varied in place.
        for call in scope.calls[:8]:
            if len(call) > 90:
                continue
            out.append(call)
            for wrap in ("tuple", "list", "set", "sorted", "frozenset", "dict"):
                out.append(f"{wrap}({call})")
            out.append(f"{call}[0]")
            out.append(f"{call}[:1]")
            # method rename: ``recv.m(...)`` -> ``recv.<other attr>(...)``
            head, dot, meth = call.partition(".")
            meth_name = meth.split("(", 1)[0]
            if dot and meth_name and head in scope.attributes:
                for other in scope.attributes[head][:8]:
                    if other != meth_name:
                        out.append(f"{head}.{other}{meth[len(meth_name):]}")
        for n in names[:8]:
            # Common single-line fix shapes.  Deliberately bounded: an atom that
            # is not here is a refusal, never an invented name.
            out += [f"[{n}]", f"list({n})", f"sorted({n})", f"{n}.copy()",
                    f"{n}[::-1]", f"list(reversed({n}))", f"set({n})", f"tuple({n})"]
        out += [x for x in _CONST_literals if x not in ("{}",)]
    return list(dict.fromkeys(out))


class AngelicCEGIS:
    """Counterexample-guided search over the harvested vocabulary.

    ``oracle(env) -> value`` is the specification.  A candidate is admitted only
    when it has been *executed* and matched the oracle on every witness, so a
    candidate that merely parses is never reported as a repair.

    The search is **witness-directed**: every atom is first evaluated on the
    whole witness set in memory, and an atom whose observation vector is
    constant (for a guard) or already covered (for a value) is dropped before a
    single composite is built.  That is what keeps a 2 000-shape grammar inside a
    256-attempt budget -- pruning happens before execution, not after.
    """

    def __init__(self, *, budget: int = 256, max_witnesses: int = 32) -> None:
        self.budget = int(budget)
        self.max_witnesses = int(max_witnesses)
        self._seen_classes: set[int] = set()
        self._graph = mir.SemiPersistentEGraph()

    # -- canonical dedup -------------------------------------------------- #
    def _class_of(self, expr: str, params: Sequence[str]) -> int | None:
        """Canonical e-class of a candidate expression, or None if unparsable."""
        try:
            src = f"def _probe({', '.join(params)}):\n    return ({expr})\n"
            mod = mir.lower_python(src)
            term = mir.function_term(mod, "_probe")
            if term is None:
                return None
            return self._graph.class_of(term)
        except Exception:  # noqa: BLE001 - an unparsable candidate is simply skipped
            return None

    def _novel(self, expr: str, params: Sequence[str]) -> bool:
        """False when an equivalent candidate was already tried (modulo rewrites).

        Saturation runs *before* the comparison: without it ``a + b`` and ``b + a``
        land in different e-classes and the search re-tests the same idea twice.
        """
        cls = self._class_of(expr, params)
        if cls is None:
            return True
        self._graph.saturate(rounds=2, budget=4000)
        root = self._graph.find(cls)
        if root in self._seen_classes:
            return False
        self._seen_classes.add(root)
        return True

    # -- in-memory observation -------------------------------------------- #
    def _namespace(self, scope: Scope, env: Mapping[str, Any]) -> dict[str, Any]:
        ns = {n: None for n in scope.names()}
        ns.update({n: None for n in scope.helpers})
        ns.update(env)
        ns["__builtins__"] = dict(SAFE_BUILTINS)
        return ns

    def _vector(self, expr: str, scope: Scope, inputs: Sequence[Mapping[str, Any]],
                *, binds: Sequence[tuple[str, str]] = (),
                helpers: Sequence[tuple[str, str]] = ()) -> tuple | None:
        """Observe ``expr`` on every witness.  ``None`` means "refused"."""
        base = {n: None for n in scope.names()}
        base.update({n: None for n in scope.helpers})
        base["__builtins__"] = dict(SAFE_BUILTINS)
        for _name, hsrc in helpers:
            try:
                base.update(_restricted_exec(hsrc, base, filename="<angelic_helper>"))
            except Exception:  # noqa: BLE001
                return None
        rows: list[tuple[str, Any]] = []
        for env in inputs:
            ns = dict(base)
            ns.update(env)
            try:
                for name, bexpr in binds:
                    ns[name] = _restricted_eval(bexpr, ns)
                value = _restricted_eval(expr, ns)
            except CandidateRefused:
                # an unparsable candidate is a refusal, not an observation
                return None
            except Exception as exc:  # noqa: BLE001 - an observed error is a result
                rows.append(("error", type(exc).__name__))
            else:
                rows.append(("value", value))
        return tuple(rows)

    # -- search ------------------------------------------------------------ #
    def invent(self, scope: Scope, oracle: Any, inputs: Sequence[Mapping[str, Any]], *,
               kind: str = "value", budget: int | None = None) -> dict[str, Any]:
        """Search for an expression satisfying ``oracle`` on every witness."""
        limit = int(budget if budget is not None else self.budget)
        inputs = list(inputs)[: self.max_witnesses]
        if not inputs:
            return {"schema": SCHEMA, "admitted": False, "reason": "NO_WITNESSES",
                    "attempts": 0, "verified_by_execution": False, "kind": kind}
        spec = tuple(observe(oracle, dict(e)) for e in inputs)
        if not any(row[0] == "value" for row in spec):
            # The oracle never produced a value on these witnesses.  That is not a
            # specification, it is a missing one: any candidate that also raises
            # would "match" it, which is how a search turns into a forgery.
            return {"schema": SCHEMA, "kind": kind, "admitted": False,
                    "reason": "NO_SPECIFICATION",
                    "note": ("the oracle raised on every witness, so there is no "
                             "behaviour to be equivalent to"),
                    "attempts": 0, "verified_by_execution": False,
                    "witnesses_checked": len(inputs), "scope": scope.as_dict(),
                    "fresh_bytecode": True}
        # A single shared budget lets one grammar family (boolean composites are
        # the worst offender) eat everything before the ternary family is even
        # reached.  Each family gets its own slice, so `a if p else b` is always
        # reachable no matter how many `x and y` shapes precede it.
        quarter = max(4, limit // 4)
        cap_atoms = quarter
        cap_bool = cap_atoms + max(4, limit // 8)
        cap_binop = cap_bool + quarter
        cap_ternary = cap_binop + quarter
        attempts = 0
        duplicates = 0
        observational = 0
        refusals = 0
        counterexamples: list[dict[str, Any]] = []
        pruned_constant = 0

        def admit(expr: str, schema: str, *, binds=(), helpers=()) -> dict[str, Any]:
            return {
                "schema": SCHEMA, "kind": kind, "admitted": True,
                "reason": "ADMITTED__EXECUTION_VERIFIED",
                "attempts": attempts,
                "duplicates_modulo_egraph": duplicates,
                "duplicates_observational": observational,
                "atoms_pruned_nondiscriminating": pruned_constant,
                "refusals": refusals,
                "counterexamples": counterexamples[:8],
                "counterexample_count": len(counterexamples),
                "scope": scope.as_dict(),
                "verified_by_execution": True, "fresh_bytecode": True,
                "witnesses_checked": len(inputs),
                "candidate": {"expr": expr, "schema": schema,
                              "binds": [list(b) for b in binds],
                              "helpers": [list(h) for h in helpers]},
            }

        def refuse_all(reason: str) -> dict[str, Any]:
            return {
                "schema": SCHEMA, "kind": kind, "admitted": False, "reason": reason,
                "attempts": attempts, "duplicates_modulo_egraph": duplicates,
                "duplicates_observational": observational,
                "atoms_pruned_nondiscriminating": pruned_constant,
                "refusals": refusals, "counterexamples": counterexamples[:8],
                "counterexample_count": len(counterexamples),
                "scope": scope.as_dict(), "verified_by_execution": False,
                "fresh_bytecode": True, "witnesses_checked": len(inputs),
            }

        # ---- 1. score every atom on the witness set, in memory ----
        atoms = _atomic_expressions(scope, guard=(kind == "guard"))
        scored: list[tuple[str, tuple]] = []
        matches: list[str] = []
        for expr in atoms:
            if not self._novel(expr, scope.params):
                duplicates += 1
                continue
            vec = self._vector(expr, scope, inputs)
            if vec is None:
                refusals += 1
                continue
            if kind == "guard" and len(set(vec)) == 1:
                pruned_constant += 1        # cannot discriminate: never a guard
                continue
            if kind == "value":
                if any(vec == v for _e, v in scored):
                    observational += 1   # same meaning: not a new idea
                    continue
            scored.append((expr, vec))
            attempts += 1
            if vec == spec:
                # keep scanning (a few more atoms only) so an equally-correct but
                # SHORTER expression wins: over-general fixes are still bugs
                matches.append(expr)
                if len(matches) >= 4:
                    return admit(_best(matches), "atom")
                continue
            if len(counterexamples) < 8:
                idx = next(i for i in range(len(vec)) if vec[i] != spec[i])
                counterexamples.append({"i": idx, "got": list(vec[idx]),
                                        "want": list(spec[idx]), "expr": expr})
            if attempts >= cap_atoms:
                break

        # A bare literal that happens to agree is NOT a repair -- it is a
        # coincidence.  Hold it as a fallback and keep searching for something
        # that actually uses the inputs; only return it if nothing better exists.
        fallback = _best(matches) if matches else None
        if fallback is not None and not _is_constant_expr(fallback):
            return admit(fallback, "atom")

        # ---- 2. boolean composites (guards only) ----
        pool = [e for e, _v in scored][:20]
        for op in (("and", "or") if kind == "guard" else ()):
            for a, b in itertools.combinations(pool, 2):
                if attempts >= cap_bool:
                    break
                expr = f"{a} {op} {b}"
                if not self._novel(expr, scope.params):
                    duplicates += 1
                    continue
                vec = self._vector(expr, scope, inputs)
                attempts += 1
                if vec is None:
                    refusals += 1
                    continue
                if vec == spec:
                    return admit(expr, f"{op}2")
                if len(counterexamples) < 8:
                    idx = next((i for i in range(len(vec)) if vec[i] != spec[i]), 0)
                    counterexamples.append({"i": idx, "got": list(vec[idx]),
                                            "want": list(spec[idx]), "expr": expr})
            if attempts >= limit:
                break

        # ---- 2b. value composites: binary operators over the atom pool ----
        if kind != "guard":
            for opn in ("-", "+", "*", "//", "%", "/"):
                # permutations, not combinations: ``price - disc`` and
                # ``disc - price`` are different meanings for every operator
                # except ``+``/``*`` (which the e-graph collapses anyway).
                for a, b in itertools.permutations(pool[:16], 2):
                    if attempts >= cap_binop:
                        break
                    expr = f"{a} {opn} {b}"
                    if not self._novel(expr, scope.params):
                        duplicates += 1
                        continue
                    vec = self._vector(expr, scope, inputs)
                    attempts += 1
                    if vec is None:
                        refusals += 1
                        continue
                    if vec == spec:
                        return admit(expr, "binop")
                    if len(counterexamples) < 8:
                        idx = next((i for i in range(len(vec)) if vec[i] != spec[i]), 0)
                        counterexamples.append({"i": idx, "got": list(vec[idx]),
                                                "want": list(spec[idx]), "expr": expr})
                if attempts >= limit:
                    break

        # ---- 2c. ternaries: ``a if <discriminating pred> else b`` ----
        if kind != "guard":
            pred_pool: list[str] = []
            for pr in itertools.islice(_predicates(scope), 96):
                pvec = self._vector(pr, scope, inputs)
                if pvec is not None and len(set(pvec)) > 1:
                    pred_pool.append(pr)
                if len(pred_pool) >= 12:
                    break
            # Names and their list-wraps first, constants last.  A length sort
            # puts ``'x'`` and ``'0'`` ahead of ``'[key]'`` and starves the
            # ternary family of the very atoms the fix needs.
            name_set = set(scope.names())
            pool_names = [e for e, _v in scored if e in name_set]
            wraps = [e for e, _v in scored
                     if e.startswith("[") and e.endswith("]") and e[1:-1] in name_set]
            lists = [e for e, _v in scored
                     if e.startswith("list(") and e.endswith(")") and e[5:-1] in name_set]
            vals = (pool_names + wraps + lists)[:12]
            for pr in pred_pool:
                for a, b in itertools.permutations(vals, 2):
                    if attempts >= cap_ternary:
                        break
                    expr = f"{a} if {pr} else {b}"
                    if not self._novel(expr, scope.params):
                        duplicates += 1
                        continue
                    vec = self._vector(expr, scope, inputs)
                    attempts += 1
                    if vec is None:
                        refusals += 1
                        continue
                    if vec == spec:
                        return admit(expr, "select")
                    if len(counterexamples) < 8:
                        idx = next((i for i in range(len(vec)) if vec[i] != spec[i]), 0)
                        counterexamples.append({"i": idx, "got": list(vec[idx]),
                                                "want": list(spec[idx]), "expr": expr})

        # ---- 3. three-way conjunctions (the `frozen is True and ...` shape) ----
        for a, b, c in itertools.islice(itertools.combinations(pool[:14], 3), 256):
            if attempts >= limit:
                break
            expr = f"{a} and {b} and {c}"
            if not self._novel(expr, scope.params):
                duplicates += 1
                continue
            vec = self._vector(expr, scope, inputs)
            attempts += 1
            if vec is None:
                refusals += 1
                continue
            if vec == spec:
                return admit(expr, "and3")
            if len(counterexamples) < 8:
                idx = next((i for i in range(len(vec)) if vec[i] != spec[i]), 0)
                counterexamples.append({"i": idx, "got": list(vec[idx]),
                                        "want": list(spec[idx]), "expr": expr})

        # ---- 4. multi-step binds and freshly synthesised helpers ----
        if kind != "guard":
            for cand in itertools.islice(_multistep_grammar(scope), 128):
                if attempts >= limit:
                    break
                if not self._novel(cand.expr, scope.params):
                    duplicates += 1
                    continue
                vec = self._vector(cand.expr, scope, inputs, binds=cand.binds,
                                   helpers=cand.helpers)
                attempts += 1
                if vec is None:
                    refusals += 1
                    continue
                if vec == spec:
                    return admit(cand.expr, cand.schema, binds=cand.binds,
                                 helpers=cand.helpers)
            for cand in itertools.islice(_helper_grammar(scope), 128):
                if attempts >= limit:
                    break
                vec = self._vector(cand.expr, scope, inputs, binds=cand.binds,
                                   helpers=cand.helpers)
                attempts += 1
                if vec is None:
                    refusals += 1
                    continue
                if vec == spec:
                    return admit(cand.expr, cand.schema, binds=cand.binds,
                                 helpers=cand.helpers)

        if fallback is not None:
            # nothing that used the inputs matched; a bare literal did.  Admit it
            # only as a last resort, and say so.
            out = admit(fallback, "atom")
            out["degraded"] = "BARE_LITERAL_FALLBACK"
            out["note"] = ("only a constant matched the witnesses; this is a "
                           "coincidence, not a repair, unless more witnesses agree")
            return out
        return refuse_all("NO_ADMITTED_CANDIDATE" if attempts else "NO_CANDIDATES")

    # -- guard-specific entry ---------------------------------------------- #
    def invent_guard(self, scope: Scope, oracle: Any,
                     inputs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        """Guard search: the oracle yields the boolean the guard must produce."""
        return self.invent(scope, oracle, inputs, kind="guard")


def guard_oracle(desired: Any, true_body: Any) -> Any:
    """Build a boolean guard oracle from the two branch bodies.

    The guard must be ``True`` exactly where taking the true branch yields the
    desired outcome, so ``observe(true_body, env) == observe(desired, env)``.
    """
    def oracle(env: Mapping[str, Any]) -> bool:
        return observe(true_body, dict(env)) == observe(desired, dict(env))
    return oracle


# --------------------------------------------------------------------------- #
# 5. One-call synthesis
# --------------------------------------------------------------------------- #


def synthesize_hole(source: str, *, target: str, oracle: Any,
                    inputs: Sequence[Mapping[str, Any]], kind: str = "value",
                    extra_sources: Mapping[str, str] | None = None,
                    env: Mapping[str, Any] | None = None,
                    budget: int = 256) -> dict[str, Any]:
    """Harvest, enumerate and CEGIS-verify a replacement for one hole."""
    scope = harvest_scope(source, target=target, extra_sources=extra_sources, env=env)
    cegis = AngelicCEGIS(budget=budget)
    out = cegis.invent(scope, oracle, inputs, kind=kind)
    out["target"] = target
    out["hole_kind"] = kind
    return out


def verify_candidate(expr: str, oracle: Any, inputs: Sequence[Mapping[str, Any]],
                     *, names: Sequence[str] = ()) -> dict[str, Any]:
    """Observational equivalence between an expression and an oracle."""
    def cand(env: Mapping[str, Any]) -> Any:
        ns = {n: env.get(n) for n in names}
        return _restricted_eval(expr, ns)

    eq = observational_equivalence(cand, oracle, list(inputs))
    return {"schema": SCHEMA, "expr": expr, "verified_by_execution": True,
            "witnesses": len(inputs), **eq}


def synthesize_guard(source: str, *, target: str, oracle: Any,
                     inputs: Sequence[Mapping[str, Any]],
                     extra_sources: Mapping[str, str] | None = None,
                     budget: int = 256) -> dict[str, Any]:
    """Alias for :func:`synthesize_hole` with ``kind="guard"``."""
    return synthesize_hole(source, target=target, oracle=oracle, inputs=inputs,
                           kind="guard", extra_sources=extra_sources, budget=budget)


def cross_frame_guard(source: str, *, target: str, oracle: Any,
                      inputs: Sequence[Mapping[str, Any]],
                      enclosing: Mapping[str, str] | None = None,
                      budget: int = 512) -> dict[str, Any]:
    """Relational guard across an enclosing class/module frame.

    ``enclosing`` maps a *name visible in the target* to source text of the
    frame that defines it, so attributes such as ``Metadata.__dict__`` entries
    enter the vocabulary instead of producing ``FOREIGN_IDENT_UNBOUND``.
    """
    merged = dict(enclosing or {})
    scope = harvest_scope(source, target=target, extra_sources=merged)
    # widen the attribute vocabulary with everything the enclosing frames expose
    attrs: dict[str, set[str]] = {k: set(v) for k, v in scope.attributes.items()}
    for name, src in merged.items():
        try:
            for st in ast.walk(ast.parse(src)):
                if isinstance(st, ast.Attribute) and isinstance(st.value, ast.Name):
                    attrs.setdefault(st.value.id, set()).add(st.attr)
                    attrs.setdefault(name, set()).add(st.attr)
        except SyntaxError:
            continue
    scope.attributes = {k: tuple(sorted(v)) for k, v in attrs.items()}
    cegis = AngelicCEGIS(budget=budget)
    out = cegis.invent(scope, oracle, inputs, kind="guard")
    out["enclosing_frames"] = sorted(merged)
    return out


__all__ = [
    "SCHEMA", "SAFE_BUILTINS", "Scope", "harvest_scope", "Candidate",
    "CandidateRefused", "AngelicCEGIS", "guard_oracle",
    "candidate_space", "observational_equivalence", "observe",
    "fresh_bytecode_env", "synthesize_hole", "synthesize_guard", "cross_frame_guard",
    "verify_candidate",
]
