"""Decide a program's runtime faults from the SOURCE, by following the literal values it already contains.

WHY THIS AND NOT A SYMBOLIC EXECUTOR. §A116 left the system unable to decide, before running, whether a program
is correct -- and for the faults that actually break programs (the ones that exist only at runtime) that was the
only thing that would have helped. The obvious answer, and the one the literature gives, is symbolic or concolic
execution. Its own surveys say what it costs: path explosion, an SMT solver in the inner loop, and "usually
reveal shallow bugs only". That is a large machine with a known wall.

FIRST PRINCIPLES SAYS LOOK AT WHAT THE FAILURES ACTUALLY DEPEND ON. Measured 2026-11-23, the five runtime-state
faults §A116 could not predict:

    a = 10; b = 0; print(a / b)          ZeroDivisionError
    xs = [1, 2]; print(xs[5])            IndexError
    d = {"a": 1}; print(d["b"])          KeyError
    for n in [1, 2, 3]: total / (n - 2)  ZeroDivisionError on the third iteration
    def f(n): ...; f(3)                  fails only for large n

**Every value involved is a literal in the source.** No input is symbolic. Nothing needs solving. What is
needed is to follow the literals: bind `a` to 10 and `b` to 0, and `a / b` is decided. This is constant
propagation, and for this class of fault it answers the question that symbolic execution would answer far more
expensively -- with no solver, no path forking beyond what the loops already force, and no wall.

WHAT IT REFUSES, AND WHY THAT IS THE DESIGN. The moment a value is not a known constant -- an input, a file, a
function argument, something computed from an unknown -- this module says UNKNOWN and stops. UNKNOWN is not a
failure; it is the honest answer, and it is what keeps the module from accusing correct programs. A predictor
that cries wolf is worse than none, because its "repair" changes something that was never broken (§A113, §A115
both learned this the hard way).

WHAT IS DELIBERATELY NOT HERE. No symbolic variables, no constraint solver, no path merging, no heap model, no
side-effect analysis. Each of those is a real technique for a real problem this module does not have. Following
literal values through straight-line code, assignment, and `for` loops over literal sequences covers the fault
classes measured above and nothing more; everything beyond that is reported UNKNOWN rather than guessed.

Authority NONE. Pure function of the program text. Zero model calls, $0.
"""
from __future__ import annotations

import ast
import builtins
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_EVALUATE_LITERALS_V1"

#: A sentinel for "not a known constant". Deliberately distinct from `None`, which IS a known constant that
#: programs index and divide by -- conflating them would make `print(None)` look like an unknown.
class _Unknown:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNKNOWN"


UNKNOWN = _Unknown()

#: Loop bodies are executed at most this many times. A `for` over a literal sequence is unrolled exactly; a
#: `while` loop, whose trip count is not in the source, is refused rather than guessed.
MAX_UNROLL = 64
MAX_STEPS = 20000


class _Stop(Exception):
    """Raised when the walk cannot continue honestly."""


#: Functions whose value this module decides AND which change nothing. A name outside this set is assumed able
#: to rebind anything, because assuming otherwise is how a stale value becomes a false accusation.
_PURE = frozenset({"len", "str", "int", "float", "list", "tuple", "sorted", "sum", "min", "max", "abs",
                   "range", "print", "dict", "set", "bool", "repr", "ord", "chr", "round"})

#: Methods that read without changing. `append`, `pop`, `update`, `clear`, `sort` are deliberately NOT here:
#: they mutate, so they must invalidate.
_PURE_METHODS = frozenset({"lower", "upper", "strip", "split", "keys", "values", "items", "get", "copy",
                           "index", "count", "startswith", "endswith", "join", "format"})


def _literal(node: ast.AST | None) -> Any:
    """The constant a node denotes, or UNKNOWN. `ast.literal_eval` covers tuples/lists/dicts and nothing else."""
    if node is None:
        return UNKNOWN
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return UNKNOWN


class _State:
    """Name -> value. Only literals are ever bound; everything else is UNKNOWN and never overwritten with a
    guess, so one unknown never silently poisons a name that was previously known."""

    def __init__(self) -> None:
        self.names: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        if name in self.names:
            return self.names[name]
        # builtins are known constants when they are: `True`, `False`, `None`, and small named functions are
        # NOT values that can be indexed or divided, so they are UNKNOWN for this module's purposes.
        return UNKNOWN

    def set(self, name: str, value: Any) -> None:
        self.names[name] = value

    def copy(self) -> "_State":
        clone = _State()
        clone.names = dict(self.names)
        return clone


def _binary(op: ast.operator, left: Any, right: Any) -> Any:
    """Apply an operator to two known constants, or UNKNOWN. The fault classes are decided HERE.

    A division by a known zero is a ZeroDivisionError the program will raise; every other arithmetic result is
    worth following because it may become an index or a divisor later. Exceptions are caught and turned into
    UNKNOWN: an operation this module cannot evaluate is not evidence of a fault.
    """
    if left is UNKNOWN or right is UNKNOWN:
        return UNKNOWN
    try:
        if isinstance(op, ast.Div) or isinstance(op, ast.FloorDiv) or isinstance(op, ast.Mod):
            if right == 0:
                raise _Stop("DIVIDE_BY_KNOWN_ZERO")
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.FloorDiv):
            return left // right
        if isinstance(op, ast.Mod):
            return left % right
        if isinstance(op, ast.Pow):
            if right > 64:
                return UNKNOWN
            return left ** right
        if isinstance(op, ast.USub):
            return -left
    except _Stop:
        raise
    except Exception:
        return UNKNOWN
    return UNKNOWN


class _Evaluator:
    """Walks a program's statements, carrying literal values, and records the faults it can PROVE.

    The output is always a list of `certain` faults and a list of `unknown` reasons. Nothing is ever reported as
    a fault unless the value that causes it was a literal the walk actually followed.
    """

    def __init__(self) -> None:
        self.faults: list[dict[str, Any]] = []
        self.unknowns: list[str] = []
        self.steps = 0
        # A FAULT INSIDE A `try` THAT CATCHES IT IS NOT A FAULT -- the program handles it and runs.
        # Measured 2026-11-23: `a=10; b=0; try: print(a/b) except ZeroDivisionError: print(0)` was reported as
        # THE_PROGRAM_WILL_RAISE, which is a false accusation against a correct program. That is the cry-wolf
        # error §A113 and §A115 each hit in a different place, so it is guarded here rather than remembered.
        self.guarded: int = 0

    def _tick(self) -> None:
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise _Stop("STEP_LIMIT")

    def _certain(self, kind: str, node: ast.AST, detail: str) -> None:
        # ALWAYS RECORDED. Whether the fault actually kills the program is decided by the enclosing `try`,
        # which is the only place that knows which handlers are in scope. Filtering here would need this
        # function to know the enclosing context, and the first version of this guard did exactly that --
        # suppressing a ZeroDivisionError inside `try/except KeyError`, which does NOT catch it, so a program
        # that crashes was reported as fine. Wrong in the direction that matters most.
        entry = {"class": kind, "line": getattr(node, "lineno", None), "detail": detail}
        if entry not in self.faults:
            self.faults.append(entry)

    def _catches(self, handler: ast.ExceptHandler, kind: str) -> bool:
        """Does this handler catch the fault class the walk proved?

        A bare `except:` catches everything. An `except T:` catches by exception NAME, and the classes this
        module proves map to exactly four: ZeroDivisionError, IndexError, KeyError, and (via _Stop) nothing else.
        A handler naming a different class does not save the program, so the fault still counts.
        """
        target = {"zero_division": "ZeroDivisionError",
                  "index_out_of_range": "IndexError",
                  "key_not_found": "KeyError"}.get(kind, "")
        if handler.type is None:
            return True
        names = []
        for node in ast.walk(handler.type):
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
        return target in names or "BaseException" in names or "Exception" in names

    # -- expressions: return a value, recording faults on the way -------------------------------------
    def value(self, node: ast.AST | None, state: _State) -> Any:
        self._tick()
        if node is None:
            return UNKNOWN
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            items = [self.value(item, state) for item in node.elts]
            if any(item is UNKNOWN for item in items):
                return UNKNOWN
            return items if isinstance(node, ast.List) else tuple(items)
        if isinstance(node, ast.Dict):
            pairs = {}
            for key_node, value_node in zip(node.keys, node.values):
                if key_node is None:      # `{**other}` -- contents unknown
                    return UNKNOWN
                key = self.value(key_node, state)
                val = self.value(value_node, state)
                if key is UNKNOWN or val is UNKNOWN:
                    return UNKNOWN
                pairs[key] = val
            return pairs
        if isinstance(node, ast.Name):
            return state.get(node.id)
        if isinstance(node, ast.BinOp):
            left = self.value(node.left, state)
            right = self.value(node.right, state)
            try:
                return _binary(node.op, left, right)
            except _Stop as stop:
                detail = "%s / %s" % (left, right)
                self._certain("zero_division", node, str(stop) + ": " + detail)
                raise
        if isinstance(node, ast.UnaryOp):
            return _binary(node.op, self.value(node.operand, state), 0)
        if isinstance(node, ast.Subscript):
            container = self.value(node.value, state)
            index = self.value(node.slice, state)
            if container is UNKNOWN:
                return UNKNOWN
            if index is UNKNOWN:
                self.unknowns.append("SUBSCRIPT_WITH_UNKNOWN_INDEX line %s" % getattr(node, "lineno", "?"))
                return UNKNOWN
            try:
                return container[index]
            except IndexError:
                self._certain("index_out_of_range", node, "%r[%r] does not exist" % (container, index))
                raise _Stop("INDEX_OUT_OF_RANGE")
            except KeyError:
                self._certain("key_not_found", node, "%r[%r] does not exist" % (container, index))
                raise _Stop("KEY_NOT_FOUND")
            except TypeError:
                return UNKNOWN
        if isinstance(node, ast.Attribute):
            return UNKNOWN
        if isinstance(node, ast.Call):
            return self._call(node, state)
        if isinstance(node, ast.Compare):
            left = self.value(node.left, state)
            for op, comparator in zip(node.ops, node.comparators):
                right = self.value(comparator, state)
                if left is UNKNOWN or right is UNKNOWN:
                    return UNKNOWN
                try:
                    if isinstance(op, ast.Eq):
                        left = left == right
                    elif isinstance(op, ast.NotEq):
                        left = left != right
                    elif isinstance(op, ast.Lt):
                        left = left < right
                    elif isinstance(op, ast.LtE):
                        left = left <= right
                    elif isinstance(op, ast.Gt):
                        left = left > right
                    elif isinstance(op, ast.GtE):
                        left = left >= right
                    elif isinstance(op, ast.In):
                        left = left in right
                    elif isinstance(op, ast.NotIn):
                        left = left not in right
                    else:
                        return UNKNOWN
                except TypeError:
                    return UNKNOWN
            return left
        if isinstance(node, ast.BoolOp):
            for operand in node.values:
                current = self.value(operand, state)
                if current is UNKNOWN:
                    return UNKNOWN
                if isinstance(node.op, ast.And) and not current:
                    return current
                if isinstance(node.op, ast.Or) and current:
                    return current
            return current
        if isinstance(node, ast.IfExp):
            test = self.value(node.test, state)
            if test is UNKNOWN:
                return UNKNOWN
            return self.value(node.body if test else node.orelse, state)
        if isinstance(node, ast.JoinedStr):
            parts = []
            for piece in node.values:
                if isinstance(piece, ast.Constant):
                    parts.append(str(piece.value))
                elif isinstance(piece, ast.FormattedValue):
                    inner = self.value(piece.value, state)
                    if inner is UNKNOWN:
                        return UNKNOWN
                    parts.append(str(inner))
                else:
                    return UNKNOWN
            return "".join(parts)
        if isinstance(node, ast.Call) or isinstance(node, ast.Lambda):
            return UNKNOWN
        # anything else (comprehensions, awaits, yields) is not followed
        return UNKNOWN

    def _invalidate(self, node: ast.Call, state: _State) -> None:
        """A MUTATING OR UNMODELLED CALL MAKES PREVIOUSLY-KNOWN VALUES UNKNOWN.

        THE FAILURE THIS FIXES IS A FALSE ACCUSATION, the worst kind. Measured 2026-11-23, adversarial pass:
        `xs=[]; xs.append(1); print(xs[0])` was reported as an IndexError -- and the program is CORRECT. The walk
        knew `xs == []`, `append` did not update that knowledge, and so it indexed an empty list that was not
        empty. Two more of the same shape: `d={}; d["k"]=1; print(d["k"])` and a `while` loop that counts down.

        An evaluator that cannot follow an effect must DROP what it believed, not keep believing it. Keeping a
        stale value is how this module would tell someone to "repair" a program that already works, which is the
        cry-wolf error §A113 and §A115 each met in a different place.
        """
        func = node.func
        # a method call may mutate whatever it is called on
        if isinstance(func, ast.Attribute):
            target = func.value
            if isinstance(target, ast.Name):
                state.set(target.id, UNKNOWN)
            else:
                # `d["a"].append(...)` -- the container is reachable only through an expression; drop every name
                # to be safe rather than keep a value the call may have changed
                state.names = {name: UNKNOWN for name in state.names}
        # a bare call may rebind anything it can see; only a known-pure builtin is exempt
        if isinstance(func, ast.Name) and func.id not in _PURE:
            state.names = {name: UNKNOWN for name in state.names}

    def _call(self, node: ast.Call, state: _State) -> Any:
        """Evaluate a call's ARGUMENTS first, then decide the call itself only if it is a known-pure builtin.

        THE ARGUMENTS ARE THE POINT, and skipping them was a real defect. Measured 2026-11-23: `a=10; b=0;
        print(a/b)` was NOT reported, because `print` is not a pure builtin whose value is decidable -- so the
        whole call returned UNKNOWN without ever looking at `a/b`, which is exactly where the program dies. A
        function whose RESULT this module cannot predict can still have a SIDE EFFECT that is certain: its
        arguments are evaluated before it is called, so a fault inside them happens whatever the function does.

        Only calls whose value is decidable from literals: `len`, `str`, `int`, `range`, `list`, `sorted`.

        Every other call returns UNKNOWN. This is deliberately a short list of PURE builtins whose behaviour is
        fixed by the language -- not a table of library functions, which would need an entry per library and
        would be the patch this project keeps replacing.
        """
        func = node.func
        # ARGUMENTS ARE EVALUATED BEFORE THE CALL, whatever the call is -- so they are walked unconditionally.
        # `print(a/0)` dies in `a/0`, not in `print`.
        for argument in list(node.args) + [keyword.value for keyword in node.keywords or []
                                          if keyword.arg is not None]:
            self.value(argument, state)
        name = func.id if isinstance(func, ast.Name) else None
        # the invalidation happens BEFORE the value is decided: the call's effects are what make old values
        # untrustworthy, and that is true whether or not its RETURN value is decidable
        if isinstance(func, ast.Name) and name not in _PURE:
            self._invalidate(node, state)
        elif isinstance(func, ast.Attribute) and func.attr not in _PURE_METHODS:
            self._invalidate(node, state)
        if name in ("len", "str", "int", "float", "list", "tuple", "sorted", "sum", "min", "max", "abs"):
            args = [self.value(item, state) for item in node.args]
            if any(arg is UNKNOWN for arg in args):
                return UNKNOWN
            try:
                if name == "len":
                    return len(args[0])
                if name == "str":
                    return str(args[0])
                if name == "int":
                    return int(args[0])
                if name == "float":
                    return float(args[0])
                if name == "list":
                    return list(args[0])
                if name == "tuple":
                    return tuple(args[0])
                if name == "sorted":
                    return sorted(args[0])
                if name == "sum":
                    return sum(args[0])
                if name == "min":
                    return min(args) if len(args) > 1 else min(args[0])
                if name == "max":
                    return max(args) if len(args) > 1 else max(args[0])
                if name == "abs":
                    return abs(args[0])
            except Exception:
                return UNKNOWN
            return UNKNOWN
        if name == "range":
            args = [self.value(item, state) for item in node.args]
            if any(arg is UNKNOWN for arg in args):
                return UNKNOWN
            # THE LENGTH IS CHECKED BEFORE THE LIST IS BUILT. `range(10**9)` was reaching `list(...)`, which
            # allocates a billion entries to discover it is too long -- a hang dressed as an analysis. The trip
            # count is arithmetic on the arguments, so it is known before anything is materialised.
            try:
                span = len(range(*args))
            except Exception:
                return UNKNOWN
            if span > MAX_UNROLL:
                self.unknowns.append("LOOP_TOO_LONG line %s (%d trips)" % (getattr(node, "lineno", "?"), span))
                return UNKNOWN
            try:
                return list(range(*args))
            except Exception:
                return UNKNOWN
        # A LIBRARY CALL WHOSE FAILURE DEPENDS ON MATHEMATICS IS NOT DECIDED HERE, AND SAYING SO IS THE ANSWER.
        # `math.sqrt(-1)` raises ValueError. Modelling every library's domain would be a table of libraries --
        # the knowledge house in miniature -- so it is refused by name, which is honest, rather than reported as
        # "no fault found", which is not: this walk not seeing a fault is not the same as the program being safe.
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "math":
            self.unknowns.append("MATHEMATICAL_DOMAIN_NOT_MODELLED line %s" % getattr(node, "lineno", "?"))
            return UNKNOWN
        if isinstance(func, ast.Attribute) and func.attr in ("lower", "upper", "strip", "split", "keys",
                                                             "values", "items", "replace"):
            target = self.value(func.value, state)
            if target is UNKNOWN:
                return UNKNOWN
            args = [self.value(item, state) for item in node.args]
            if any(arg is UNKNOWN for arg in args):
                return UNKNOWN
            try:
                return getattr(target, func.attr)(*args)
            except Exception:
                return UNKNOWN
        return UNKNOWN

    # -- statements -----------------------------------------------------------------------------------
    def block(self, statements: list[ast.stmt], state: _State) -> None:
        for statement in statements:
            self._tick()
            self.statement(statement, state)

    def statement(self, node: ast.stmt, state: _State) -> None:
        if isinstance(node, ast.Assign):
            value = self.value(node.value, state)
            for target in node.targets:
                self._apply(target, value, state)
            return
        if isinstance(node, ast.AnnAssign):
            if node.value is not None:
                self._apply(node.target, self.value(node.value, state), state)
            return
        if isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                current = state.get(node.target.id)
                right = self.value(node.value, state)
                try:
                    state.set(node.target.id, _binary(node.op, current, right))
                except _Stop as stop:
                    self._certain("zero_division", node, str(stop))
                    raise
            else:
                self.value(node.target, state)
                self.value(node.value, state)
            return
        if isinstance(node, ast.Expr):
            self.value(node.value, state)
            return
        if isinstance(node, ast.For):
            iterable = self.value(node.iter, state)
            if iterable is UNKNOWN or not hasattr(iterable, "__iter__"):
                if not any("LOOP_TOO_LONG" in reason for reason in self.unknowns[-2:]):
                    self.unknowns.append("FOR_OVER_UNKNOWN line %s" % getattr(node, "lineno", "?"))
                # the body still may hold a fault that does not depend on the loop variable; walking it once
                # with UNKNOWN bindings is honest because nothing in it can then be decided from a guess
                self.block(node.body, state)
                return
            items = list(iterable)
            if len(items) > MAX_UNROLL:
                self.unknowns.append("LOOP_TOO_LONG line %s" % getattr(node, "lineno", "?"))
                return
            for item in items:
                iteration = state.copy()
                self._bind(node.target, item, iteration)
                self.block(node.body, iteration)
                state.names.update(iteration.names)
            self.block(node.orelse, state)
            return
        if isinstance(node, ast.While):
            # A `while` WHOSE CONDITION IS DECIDABLE IS JUST A LOOP WITH A KNOWN TRIP COUNT. Measured 2026-11-23:
            # `x=5; while x>0: x=x-1; print(10/x)` raises ZeroDivisionError and was reported UNKNOWN. Unrolling
            # the condition the same way `for` over a literal is unrolled costs nothing new -- the state walk
            # already carries the values. A condition that goes UNKNOWN stops the unroll and says so, which is
            # the same refusal as before rather than a guess.
            for _ in range(MAX_UNROLL):
                condition = self.value(node.test, state)
                if condition is UNKNOWN:
                    self.unknowns.append("WHILE_CONDITION_UNKNOWN line %s" % getattr(node, "lineno", "?"))
                    return
                if not condition:
                    self.block(node.orelse, state)
                    return
                self.block(node.body, state)
            self.unknowns.append("WHILE_LOOP_TOO_LONG line %s" % getattr(node, "lineno", "?"))
            return
        if isinstance(node, ast.If):
            test = self.value(node.test, state)
            if test is UNKNOWN:
                self.unknowns.append("BRANCH_ON_UNKNOWN line %s" % getattr(node, "lineno", "?"))
                # both arms are walked, but nothing decided in them is reported as certain, because we do not
                # know which runs. The faults recorded there are still facts about the arm that WOULD run.
                self.block(node.body, state.copy())
                self.block(node.orelse, state.copy())
                return
            self.block(node.body if test else node.orelse, state)
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # a function body is not analysed until it is called, and calls are not followed (see `_call`)
            return
        if isinstance(node, ast.Return):
            self.value(node.value, state)
            return
        if isinstance(node, ast.Try):
            # THE BODY IS RUN WITH THE GUARD ON, then the faults it recorded are checked against the handlers.
            # Guarding by "does any handler catch anything" would be too generous in the other direction: a
            # handler for `KeyError` does not save a program from `ZeroDivisionError`. So the body is walked
            # unguarded into a scratch list, and each recorded fault is kept only if NO handler catches it.
            before = len(self.faults)
            self.guarded += 1
            try:
                self.block(node.body, state)
            except _Stop:
                # a fault was proved inside the guarded body. That is exactly the case the handlers exist for,
                # so the walk continues to the handler check below rather than unwinding out of the program.
                pass
            finally:
                self.guarded -= 1
            caught = [f for f in self.faults[before:] if not any(self._catches(h, f["class"])
                                                                for h in node.handlers)]
            del self.faults[before:]
            self.faults.extend(caught)
            for handler in node.handlers:
                self.block(handler.body, state.copy())
            self.block(node.orelse, state)
            self.block(node.finalbody, state)
            return
        if isinstance(node, ast.With):
            self.block(node.body, state)
            return
        if isinstance(node, ast.Assert):
            self.value(node.test, state)
            return
        if isinstance(node, ast.Raise):
            self.value(node.exc, state)
            return
        # imports, deletes, global declarations and everything else have no value to follow

    def _apply(self, target: ast.AST, value: Any, state: _State) -> None:
        """Assignment, including the two forms that CHANGE an existing container rather than rebind a name.

        `d["k"] = 1` and `xs[0] = 9` are the ordinary way a program builds the very structures it later indexes,
        and ignoring them means the module keeps believing the empty literal. Measured 2026-11-23: `d={};
        d["k"]=1; print(d["k"])` was reported as a KeyError -- a false accusation against a correct program.
        Where the container is a known literal it is UPDATED; where it is not, the base name becomes UNKNOWN,
        because the effect happened whatever it was.
        """
        if isinstance(target, ast.Subscript):
            container = self.value(target.value, state)
            index = self.value(target.slice, state)
            if isinstance(target.value, ast.Name):
                if container is UNKNOWN or index is UNKNOWN:
                    state.set(target.value.id, UNKNOWN)
                else:
                    try:
                        container[index] = value
                        state.set(target.value.id, container)
                    except Exception:
                        state.set(target.value.id, UNKNOWN)
            else:
                # `d["a"]["b"] = 1` -- the outer container is not a name; drop every belief
                state.names = {name: UNKNOWN for name in state.names}
            return
        if isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name):
                state.set(target.value.id, UNKNOWN)
            else:
                state.names = {name: UNKNOWN for name in state.names}
            return
        self._bind(target, value, state)

    def _bind(self, target: ast.AST, value: Any, state: _State) -> None:
        if isinstance(target, ast.Name):
            state.set(target.id, value)
        elif isinstance(target, (ast.Tuple, ast.List)):
            items = value if isinstance(value, (list, tuple)) else UNKNOWN
            for position, element in enumerate(target.elts):
                if items is UNKNOWN:
                    self._bind(element, UNKNOWN, state)
                else:
                    try:
                        self._bind(element, items[position], state)
                    except IndexError:
                        self._bind(element, UNKNOWN, state)
        # attributes and subscripts are not tracked


def evaluate(source: str) -> dict[str, Any]:
    """Faults this program will certainly raise, decided from the literals it contains.

    Returns `certain` (faults the walk proved), `unknowns` (why parts could not be decided), and `covers`. An
    empty `certain` with a non-empty `unknowns` means NOT "the program is fine" -- it means this module could not
    see, which is a different statement and is reported as one.
    """
    try:
        tree = ast.parse(str(source))
    except SyntaxError as broken:
        return {"schema": SCHEMA, "certain": [], "unknowns": ["SYNTAX_ERROR"],
                "detail": str(broken)[:200], "verdict": "CANNOT_READ"}
    evaluator = _Evaluator()
    try:
        evaluator.block(tree.body, _State())
    except _Stop as stop:
        if str(stop) not in ("DIVIDE_BY_KNOWN_ZERO",):
            evaluator.unknowns.append("STOPPED: " + str(stop))
    except RecursionError:
        evaluator.unknowns.append("RECURSION_LIMIT")

    certain = evaluator.faults
    if certain:
        verdict = "THE_PROGRAM_WILL_RAISE"
    elif evaluator.unknowns:
        verdict = "THIS_WALK_COULD_NOT_DECIDE"
    else:
        # THIS WORDING IS DELIBERATE. "No fault found" is not "no fault exists": this walk follows literals
        # through straight-line code and known loops, and a program that passes it may still fail. Saying so in
        # the verdict itself is cheaper than a caveat nobody reads.
        verdict = "NO_FAULT_FOUND_IN_WHAT_COULD_BE_FOLLOWED"
    return {"schema": SCHEMA, "certain": certain, "unknowns": evaluator.unknowns,
            "steps": evaluator.steps, "verdict": verdict}


def main(argv: list[str] | None = None) -> int:
    import json
    import pathlib
    import sys

    arguments = list(argv if argv is not None else sys.argv[1:])
    if not arguments:
        print(json.dumps({"schema": SCHEMA, "usage": "evaluate_literals_v1 <program.py>"}))
        return 0
    path = pathlib.Path(arguments[0])
    print(json.dumps(evaluate(path.read_text()), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
