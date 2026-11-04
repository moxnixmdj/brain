"""Bounded, non-executing models of simple numeric functions.

This module supplies a small *hypothesis space*, not a specification. It rebinds
source expressions and can compose supported operators observed in previous
locally checked repairs. An externally supplied example can eliminate models; a
query is chosen to separate survivors. Experience supplies proposals, not facts
or permission. Agreement in this bounded space is not a proof of correctness or
that two functions should agree.

No workspace module is imported or executed. Arithmetic is interpreted directly
from a restricted AST. Unsupported functions and arithmetic decline. The bounds
are deliberate: this is a limited static model, not a Python sandbox.
"""
from __future__ import annotations

import ast
from collections import Counter
import copy
import hashlib
import itertools
import math
import operator
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

MAX_SOURCE_BYTES = 400_000
MAX_AST_NODES = 12_000
MAX_EXPRESSION_NODES = 128
MAX_FUNCTIONS = 24
MAX_ARITY = 4
MAX_CANDIDATES = 256
MAX_QUERY_POINTS = 256
MAX_EXTERNAL_EXAMPLES = 256
INITIAL_LEARNED_BINARY_NODES = 2
MAX_LEARNED_BINARY_NODES = 6
MAX_SEMANTIC_COMBINATIONS = 4096
MIN_EXTERNAL_EXAMPLES = 2

# Python operator semantics, not a mapping from error classes to repairs.
_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


@dataclass(frozen=True)
class FunctionModel:
    name: str
    params: tuple[str, ...]
    expression: ast.expr


def _number(value: Any) -> bool:
    if type(value) is int:
        return value.bit_length() <= 80
    if type(value) is float:
        return math.isfinite(value) and abs(value) <= 1e20
    return False


def validate_external_examples(examples: Sequence[Mapping[str, Any]], arity: int, *,
                               require_attribution: bool = False) -> tuple[bool, str]:
    """Validate distinct, modelable answers; attribution fields are not authentication."""
    if not isinstance(examples, (list, tuple)) or len(examples) > MAX_EXTERNAL_EXAMPLES:
        return False, "invalid example collection or budget"
    seen: set[tuple[Any, ...]] = set()
    for example in examples:
        if not isinstance(example, Mapping):
            return False, "example is not a mapping"
        args, expected = example.get("args"), example.get("expected")
        if (not isinstance(args, (list, tuple)) or len(args) != arity
                or not all(_number(a) for a in args) or not _number(expected)):
            return False, "example is outside the numeric model"
        if require_attribution and any(not isinstance(example.get(field), str) or not example[field].strip()
                                       for field in ("reviewer", "basis")):
            return False, "example lacks attribution"
        key = tuple(args)
        if key in seen:
            return False, "duplicate example input"
        seen.add(key)
    return True, "valid"


def same_number(a: Any, b: Any) -> bool:
    """Compare supported numbers without converting large integers to floats."""
    if not _number(a) or not _number(b):
        return False
    if type(a) is int and type(b) is int:
        return a == b
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _expression_supported(expression: ast.AST, params: Sequence[str]) -> bool:
    nodes = list(ast.walk(expression))
    if len(nodes) > MAX_EXPRESSION_NODES:
        return False
    for node in nodes:
        if isinstance(node, ast.Constant):
            if not _number(node.value):
                return False
        elif isinstance(node, ast.Name):
            if node.id not in params or not isinstance(node.ctx, ast.Load):
                return False
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in _BINARY:
                return False
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in _UNARY:
                return False
        elif isinstance(node, (ast.Load, ast.operator, ast.unaryop)):
            continue
        else:
            return False
    return True


def function_models(source: str) -> dict[str, FunctionModel]:
    """Read simple top-level functions as ASTs.  Nothing in ``source`` is run."""
    if not isinstance(source, str) or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return {}
    try:
        tree = ast.parse(source)
        if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
            return {}
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return {}
    # Do not model a module whose top-level statements could rebind a function.
    # Even an import or assignment is outside this small static model's scope.
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            args = node.args
            annotated_args = (*args.posonlyargs, *args.args, *args.kwonlyargs,
                              *([args.vararg] if args.vararg else []),
                              *([args.kwarg] if args.kwarg else []))
            # These expressions run while Python defines a function, including
            # on unrelated definitions. Decline the whole module rather than
            # model it as inert when importing it could change the program.
            if (node.decorator_list or args.defaults or any(x is not None for x in args.kw_defaults)
                    or node.returns is not None or any(a.annotation is not None for a in annotated_args)):
                return {}
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        return {}
    definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    counts = Counter(n.name for n in definitions)
    models: dict[str, FunctionModel] = {}
    for fn in definitions[:MAX_FUNCTIONS]:
        if counts[fn.name] != 1 or fn.decorator_list:
            continue
        args = fn.args
        if args.vararg or args.kwarg or args.kwonlyargs or args.defaults:
            continue
        params = tuple(a.arg for a in (*args.posonlyargs, *args.args))
        if not 1 <= len(params) <= MAX_ARITY:
            continue
        body = list(fn.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body.pop(0)
        if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
            continue
        expression = body[0].value
        if _expression_supported(expression, params):
            models[fn.name] = FunctionModel(fn.name, params, expression)
    return models


def _apply_binary(op: type[ast.operator], left: int | float, right: int | float) -> int | float:
    """One numeric operation under the same limits used by all static models."""
    if op is ast.Pow and (abs(right) > 12 or abs(left) > 1e6):
        raise ValueError("power exceeds model budget")
    result = _BINARY[op](left, right)
    if not _number(result):
        raise ValueError("value exceeds model budget")
    return result


def evaluate_expression(expression: ast.AST, bindings: Mapping[str, Any]) -> tuple[bool, int | float | None]:
    """Interpret a whitelisted numeric AST with bounded intermediate results."""
    if not _expression_supported(expression, tuple(bindings)) or not all(_number(v) for v in bindings.values()):
        return False, None

    def visit(node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant):
            result = node.value
        elif isinstance(node, ast.Name):
            result = bindings[node.id]
        elif isinstance(node, ast.UnaryOp):
            result = _UNARY[type(node.op)](visit(node.operand))
        elif isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            result = _apply_binary(type(node.op), left, right)
        else:
            raise ValueError("unsupported expression")
        if not _number(result):
            raise ValueError("value exceeds model budget")
        return result

    try:
        return True, visit(expression)
    except (ArithmeticError, KeyError, TypeError, ValueError, OverflowError, RecursionError):
        return False, None


def evaluate(model: FunctionModel, args: Sequence[Any]) -> tuple[bool, int | float | None]:
    if len(args) != len(model.params):
        return False, None
    return evaluate_expression(model.expression, dict(zip(model.params, args)))


def supported_binary_operator_names() -> frozenset[str]:
    return frozenset(cls.__name__ for cls in _BINARY)


def observed_binary_operators(expression: ast.AST) -> list[str]:
    """Describe supported primitives actually present in a restricted expression."""
    return sorted({type(node.op).__name__ for node in ast.walk(expression)
                   if isinstance(node, ast.BinOp) and type(node.op) in _BINARY})


def _learned_compositions(params: Sequence[str], operator_names: Sequence[str], *, max_nodes: int):
    """Enumerate small programs from observed operators, not a failure/repair table.

    Only parameters are leaves; no value is copied from a previous task. Each
    binary-node count is enumerated bottom-up. The caller applies the budget and
    tests every resulting model against this task's own observations.
    """
    supported = {cls.__name__: cls for cls in _BINARY}
    operators = [supported[name] for name in sorted({n for n in operator_names if isinstance(n, str)})
                 if name in supported]
    if not operators:
        return
    levels: list[list[ast.expr]] = [[ast.Name(id=p, ctx=ast.Load()) for p in params]]
    for count in range(1, max_nodes + 1):
        level: list[ast.expr] = []
        for left_count in range(count):
            right_count = count - left_count - 1
            for op in operators:
                for left in levels[left_count]:
                    for right in levels[right_count]:
                        expr = ast.fix_missing_locations(ast.BinOp(
                            left=copy.deepcopy(left), op=op(), right=copy.deepcopy(right)))
                        level.append(expr)
                        yield expr
        levels.append(level)


def expression_candidates(target: FunctionModel, templates: Sequence[FunctionModel], *,
                          learned_operators: Sequence[str] = (),
                          max_learned_binary_nodes: int = INITIAL_LEARNED_BINARY_NODES,
                          limit: int = MAX_CANDIDATES) -> tuple[list[ast.expr], bool]:
    """Rebind each parameter occurrence in source expressions to a target parameter.

    Bindings are not chosen by a table: all combinations within the budget are
    considered.  For example, a two-occurrence expression can bind its occurrences
    to the same target parameter or to two different ones.  Constants and operator
    nodes come from the source templates or previously observed primitives,
    not a catalogue of failure classes. Learned compositions are proposals only.
    """
    limit = max(1, min(int(limit), MAX_CANDIDATES))
    out: list[ast.expr] = []
    seen: set[str] = set()
    truncated = False

    def add(expr: ast.expr) -> None:
        if not _expression_supported(expr, target.params):
            return
        key = ast.dump(expr, include_attributes=False)
        if key not in seen:
            seen.add(key)
            out.append(expr)

    add(copy.deepcopy(target.expression))
    for template in templates:
        # NodeTransformer visits Name nodes in this same deterministic order.
        occurrences = [n for n in ast.walk(template.expression)
                       if isinstance(n, ast.Name) and n.id in template.params]
        # ast.walk is breadth-first, while NodeTransformer is depth-first; only the
        # count matters because every combination of target names is enumerated.
        n = len(occurrences)
        if n == 0:
            continue  # never introduce a constant-only candidate
        combinations = len(target.params) ** n
        remaining = max(0, limit - len(out))
        if not remaining:
            truncated = True
            break
        # Bound attempted combinations too, even when many deduplicate.
        budget = min(combinations, MAX_CANDIDATES)
        if combinations > budget:
            truncated = True
        for names in itertools.islice(itertools.product(target.params, repeat=n), budget):
            iterator = iter(names)

            class Bind(ast.NodeTransformer):
                def visit_Name(self, node: ast.Name) -> ast.AST:
                    if node.id in template.params:
                        return ast.copy_location(ast.Name(id=next(iterator), ctx=ast.Load()), node)
                    return node

            expr = ast.fix_missing_locations(Bind().visit(copy.deepcopy(template.expression)))
            add(expr)
            if len(out) >= limit:
                if combinations > 1:
                    truncated = True
                break
    if learned_operators and not truncated:
        # Parameters are the leaves of the learned grammar. Include them as
        # zero-node candidates before considering compositions.
        for name in target.params:
            add(ast.Name(id=name, ctx=ast.Load()))
            if len(out) > limit:
                return out[:limit], True
        # Bound attempts as well as distinct candidates. Encountering a budget
        # makes incomplete search explicit; it cannot become agreement evidence.
        attempts = 0
        depth = max(0, min(int(max_learned_binary_nodes), MAX_LEARNED_BINARY_NODES))
        for expr in _learned_compositions(target.params, learned_operators, max_nodes=depth):
            attempts += 1
            if attempts > MAX_CANDIDATES * 4:
                truncated = True
                break
            before = len(out)
            add(expr)
            if len(out) > limit:
                truncated = True
                break
            if before < limit and len(out) == limit:
                # Continue until a further distinct candidate, if any, shows
                # that this exact-sized space was actually truncated.
                continue
    return out[:limit], truncated


def _number_key(value: int | float) -> tuple[str, Any]:
    # Python considers 0, 0.0 and -0.0 equal; numeric operations can still
    # distinguish their types or signed zero. Do not merge those behaviors.
    return ("int", value) if type(value) is int else ("float", value.hex())


def _semantic_points(arity: int, constraints: Sequence[tuple[Sequence[Any], Any]]
                     ) -> tuple[list[tuple[Any, ...]], dict[tuple[Any, ...], int]] | None:
    if 6 ** arity + 3 ** arity > MAX_QUERY_POINTS:
        return None
    points: list[tuple[Any, ...]] = []
    index: dict[tuple[Any, ...], int] = {}
    domains = (itertools.product((2, 3, 4, 5, 6, 7), repeat=arity),
               itertools.product((-3, 0, 11), repeat=arity),
               (tuple(args) for args, _ in constraints))
    for point in itertools.chain.from_iterable(domains):
        if len(point) != arity or not all(_number(v) for v in point):
            return None
        key = tuple(_number_key(v) for v in point)
        if key not in index:
            if len(points) >= MAX_QUERY_POINTS:
                return None
            index[key] = len(points)
            points.append(tuple(point))
    return points, index


def _signature(values: Sequence[int | float | None]) -> tuple[Any, ...]:
    return tuple(None if v is None else _number_key(v) for v in values)


def _semantic_compositions(
    target: FunctionModel, constraints: Sequence[tuple[Sequence[Any], Any]],
    operators: Sequence[str], *, limit: int,
) -> tuple[list[ast.expr], bool, dict[str, Any]]:
    """Compose one minimal representative per exact finite-domain behavior.

    All operator inputs are bounded built-in numbers, so equal typed subexpression
    vectors give equal parent vectors on these points. This preserves distinctions
    *on this domain*, not on unobserved inputs. Every level must complete within
    both caps before it can support bounded agreement or justify deeper search.
    """
    domain = _semantic_points(len(target.params), constraints)
    base = {"method": "finite_domain_signature", "learned_binary_node_budget": MAX_LEARNED_BINARY_NODES,
            "more_complex_learned_models_unexamined": True}
    if domain is None:
        return [], True, {**base, "learned_binary_nodes_explored": INITIAL_LEARNED_BINARY_NODES,
                          "expansion_rounds": 0, "candidates_examined": 0,
                          "semantic_combinations": 0, "domain_points": 0,
                          "complete_through_depth": False, "reason": "semantic_domain_budget"}
    points, point_index = domain
    required = [(point_index[tuple(_number_key(v) for v in args)], expected)
                for args, expected in constraints]
    # key -> (typed values at all points, representative AST)
    levels: list[dict[tuple[Any, ...], tuple[tuple[int | float | None, ...], ast.expr]]] = []
    seen: dict[tuple[Any, ...], tuple[tuple[int | float | None, ...], ast.expr]] = {}
    leaves: dict[tuple[Any, ...], tuple[tuple[int | float | None, ...], ast.expr]] = {}
    for i, name in enumerate(target.params):
        values = tuple(point[i] for point in points)
        key = _signature(values)
        leaves.setdefault(key, (values, ast.Name(id=name, ctx=ast.Load())))
    seen.update(leaves)
    levels.append(leaves)
    supported = {cls.__name__: cls for cls in _BINARY}
    attempts = 0

    def finish(depth: int, current: Mapping[tuple[Any, ...], tuple[tuple[int | float | None, ...], ast.expr]],
               truncated: bool) -> tuple[list[ast.expr], bool, dict[str, Any]]:
        survivors = [expr for values, expr in current.values()
                     if all(values[i] is not None and same_number(values[i], expected)
                            for i, expected in required)] if depth > INITIAL_LEARNED_BINARY_NODES else []
        info = {**base, "learned_binary_nodes_explored": depth,
                "expansion_rounds": max(0, depth - INITIAL_LEARNED_BINARY_NODES),
                "candidates_examined": len(seen) + len(current), "semantic_combinations": attempts,
                "domain_points": len(points), "complete_through_depth": not truncated}
        return survivors, truncated, info

    for depth in range(1, MAX_LEARNED_BINARY_NODES + 1):
        current: dict[tuple[Any, ...], tuple[tuple[int | float | None, ...], ast.expr]] = {}
        for left_depth in range(depth):
            for name in operators:
                op = supported[name]
                for left_values, left_expr in levels[left_depth].values():
                    for right_values, right_expr in levels[depth - left_depth - 1].values():
                        attempts += 1
                        if attempts > MAX_SEMANTIC_COMBINATIONS:
                            return finish(depth, current, True)
                        values_list: list[int | float | None] = []
                        for left, right in zip(left_values, right_values):
                            if left is None or right is None:
                                values_list.append(None)
                                continue
                            try:
                                values_list.append(_apply_binary(op, left, right))
                            except (ArithmeticError, KeyError, TypeError, ValueError, OverflowError, RecursionError):
                                values_list.append(None)
                        values = tuple(values_list)
                        key = _signature(values)
                        if key in seen or key in current:
                            continue
                        if len(seen) + len(current) >= limit:
                            return finish(depth, current, True)
                        expr = ast.fix_missing_locations(ast.BinOp(
                            left=copy.deepcopy(left_expr), op=op(), right=copy.deepcopy(right_expr)))
                        current[key] = (values, expr)
        if depth > INITIAL_LEARNED_BINARY_NODES:
            survivors, truncated, info = finish(depth, current, False)
            if survivors:
                return survivors, truncated, info
        seen.update(current)
        levels.append(current)
    return finish(MAX_LEARNED_BINARY_NODES, {}, False)


def fitting_expression_candidates(
    target: FunctionModel, templates: Sequence[FunctionModel],
    constraints: Sequence[tuple[Sequence[Any], Any]], *,
    learned_operators: Sequence[str] = (), limit: int = MAX_CANDIDATES,
) -> tuple[list[ast.expr], bool, dict[str, Any]]:
    """Fit, then deepen only after a complete shallower search is refuted.

    A larger grammar supplies hypotheses, not evidence. We stop at the first
    depth with survivors, explicitly bounded by a finite semantic domain and
    resource caps; larger programs and behaviors outside that domain remain open.
    """
    operators = sorted({name for name in learned_operators
                        if isinstance(name, str) and name in supported_binary_operator_names()})
    limit = max(1, min(int(limit), MAX_CANDIDATES))
    depth = INITIAL_LEARNED_BINARY_NODES if operators else 0
    info = {"method": "syntactic", "learned_binary_nodes_explored": depth,
            "learned_binary_node_budget": MAX_LEARNED_BINARY_NODES if operators else 0,
            "expansion_rounds": 0, "candidates_examined": 0, "semantic_combinations": 0,
            "complete_through_depth": False, "more_complex_learned_models_unexamined": bool(operators)}
    if (not constraints or any(not isinstance(args, (list, tuple)) or len(args) != len(target.params)
                               or not all(_number(v) for v in args) or not _number(expected)
                               for args, expected in constraints)):
        return [], False, {**info, "reason": "missing_or_unsupported_constraints"}
    candidates, truncated = expression_candidates(
        target, templates, learned_operators=operators, max_learned_binary_nodes=depth, limit=limit)
    survivors = [expr for expr in candidates if all(
        (lambda result: result[0] and same_number(result[1], expected))(
            evaluate_expression(expr, dict(zip(target.params, args))))
        for args, expected in constraints)]
    info["candidates_examined"], info["complete_through_depth"] = len(candidates), not truncated
    if survivors or truncated or not operators:
        return survivors, truncated, info
    # Only complete refutation licenses additional search, not publication.
    return _semantic_compositions(target, constraints, operators, limit=limit)


def replace_return_expression(source: str, model: FunctionModel, replacement: ast.expr) -> str | None:
    """Replace precisely this return expression, preserving all other source bytes."""
    node = model.expression
    if not all(hasattr(node, field) for field in ("lineno", "col_offset", "end_lineno", "end_col_offset")):
        return None
    # AST columns are UTF-8 byte offsets, not Python string character offsets.
    lines = source.encode("utf-8").splitlines(keepends=True)
    if not (1 <= node.lineno <= node.end_lineno <= len(lines)):
        return None
    start = sum(len(x) for x in lines[:node.lineno - 1]) + node.col_offset
    end = sum(len(x) for x in lines[:node.end_lineno - 1]) + node.end_col_offset
    raw = source.encode("utf-8")
    try:
        candidate = (raw[:start] + ast.unparse(replacement).encode("utf-8") + raw[end:]).decode("utf-8")
        ast.parse(candidate)
    except (SyntaxError, ValueError, RecursionError, UnicodeError):
        return None
    return candidate if candidate != source else None


def _masked_target_expression(source: str, expression: ast.expr) -> bytes | None:
    if not all(hasattr(expression, f) for f in ("lineno", "col_offset", "end_lineno", "end_col_offset")):
        return None
    lines = source.encode("utf-8").splitlines(keepends=True)
    if not (1 <= expression.lineno <= expression.end_lineno <= len(lines)):
        return None
    start = sum(len(x) for x in lines[:expression.lineno - 1]) + expression.col_offset
    end = sum(len(x) for x in lines[:expression.end_lineno - 1]) + expression.end_col_offset
    raw = source.encode("utf-8")
    return raw[:start] + b"<EXPRESSION>" + raw[end:]


def target_expression_scope_sha256(source: str, target_name: str) -> str | None:
    """Fingerprint all source bytes except the modeled target return expression."""
    model = function_models(source).get(target_name)
    masked = _masked_target_expression(source, model.expression) if model else None
    return hashlib.sha256(masked).hexdigest() if masked is not None else None


def only_target_expression_changed(before: str, after: str, target_name: str) -> bool:
    """Require every source byte outside the named return expression to be unchanged."""
    old_model = function_models(before).get(target_name)
    new_model = function_models(after).get(target_name)
    if not old_model or not new_model or old_model.params != new_model.params or before == after:
        return False
    old_mask = _masked_target_expression(before, old_model.expression)
    new_mask = _masked_target_expression(after, new_model.expression)
    return old_mask is not None and old_mask == new_mask


def investigate(source: str, *, target_name: str, reference_name: str,
                observations: Sequence[Mapping[str, Any]],
                examples: Sequence[Mapping[str, Any]],
                learned_operators: Sequence[str] = ()) -> dict[str, Any]:
    """Filter source-derived models and ask a discriminating, externally answered query.

    The caller must supply observations from an explicitly trusted reference and
    separately supplied examples; neither source-derived predictions nor a model's
    own output may be fed back as an external answer.
    """
    learned_operators = tuple(sorted({n for n in learned_operators
                                      if isinstance(n, str) and n in supported_binary_operator_names()}))
    models = function_models(source)
    target, reference = models.get(target_name), models.get(reference_name)
    if not target or not reference or target_name == reference_name:
        return {"status": "unsupported", "candidates": 0, "next_query": None,
                "reason": "target/reference unavailable in restricted static model"}
    constraints: list[tuple[tuple[Any, ...], Any]] = []
    for observation in observations:
        x = observation.get("input")
        expected = observation.get("left") if reference_name == observation.get("left_name") else observation.get("right")
        if not _number(x) or not _number(expected):
            continue
        # The relation under review is the diagonal relation; a reference with
        # one parameter sees x once, a wider reference sees it in every slot.
        constraints.append(((x,) * len(target.params), expected))
    examples_valid, reason = validate_external_examples(examples, len(target.params))
    if not examples_valid:
        return {"status": "invalid_external_examples", "candidates": 0, "next_query": None, "reason": reason}
    for example in examples:
        constraints.append((tuple(example["args"]), example["expected"]))
    if not constraints:
        return {"status": "no_reference_observations", "candidates": 0, "next_query": None,
                "reason": "no supported, attributed constraints"}
    survivors, candidate_truncated, search = fitting_expression_candidates(
        target, [reference], constraints, learned_operators=learned_operators)
    # The main grid and the out-of-range stress grid are separately bounded.
    # A partial exploration must not count as agreement across either grid.
    truncated = candidate_truncated or (6 ** len(target.params) + 3 ** len(target.params) > MAX_QUERY_POINTS)
    if not survivors:
        return {"status": "truncated_search" if truncated else "no_candidates",
                "candidates": 0, "truncated": truncated, "next_query": None, "search": search,
                "external_examples": len(examples), "learned_operators_considered": list(learned_operators),
                "reason": "no explored model fits the supplied evidence"}

    asked = {args for args, _ in constraints}
    best: tuple[float, tuple[int, ...], list[int | float]] | None = None
    fallback: tuple[tuple[int, ...], list[int | float]] | None = None
    checked = {"primary": 0, "stress": 0, "undefined": 0}

    def examine(args: tuple[int, ...], domain: str) -> tuple[float, list[int | float]] | None:
        if args in asked:
            return None
        results = [evaluate_expression(expr, dict(zip(target.params, args))) for expr in survivors]
        if not all(ok for ok, _ in results):
            checked["undefined"] += 1
            return None
        checked[domain] += 1
        buckets: list[tuple[int | float, int]] = []
        for _, value in results:
            for i, (known, count) in enumerate(buckets):
                if same_number(value, known):
                    buckets[i] = (known, count + 1)
                    break
            else:
                buckets.append((value, 1))
        entropy = -sum((count / len(results)) * math.log2(count / len(results)) for _, count in buckets)
        return entropy, [value for value, _ in buckets]

    # Discriminate on the original finite grid first. If models agree there,
    # challenge that agreement on a small second grid with negative, zero and
    # larger inputs. These values are generic stress choices, not an oracle.
    for args in itertools.islice(itertools.product((2, 3, 4, 5, 6, 7), repeat=len(target.params)), MAX_QUERY_POINTS):
        result = examine(args, "primary")
        if result is None:
            continue
        entropy, predictions = result
        if fallback is None:
            fallback = (args, predictions)
        if len(predictions) >= 2 and (best is None or entropy > best[0] + 1e-12):
            best = (entropy, args, predictions)

    stress_complete = best is None
    stress_fallback: tuple[tuple[int, ...], list[int | float]] | None = None
    if stress_complete:
        stress = list(itertools.product((-3, 0, 11), repeat=len(target.params)))
        # Prioritize varied inputs at opposite ends of the domain; diagonal
        # points have already been proposed by the source relationship.
        stress.sort(key=lambda a: (-(max(a) - min(a)), -max(abs(x) for x in a), a))
        for args in stress:
            result = examine(args, "stress")
            if result is None:
                continue
            entropy, predictions = result
            if stress_fallback is None:
                stress_fallback = (args, predictions)
            if len(predictions) >= 2 and (best is None or entropy > best[0] + 1e-12):
                best = (entropy, args, predictions)

    query = None
    if best:
        entropy, args, predictions = best
        query = {"args": list(args), "predictions": predictions, "reason": "models_disagree", "entropy_bits": round(entropy, 6)}
    elif len(examples) < MIN_EXTERNAL_EXAMPLES and (stress_fallback or fallback):
        args, predictions = stress_fallback or fallback
        query = {"args": list(args), "predictions": predictions, "reason": "independent_validation", "entropy_bits": 0.0}
    status = "needs_example" if query else (
        "insufficient_external_examples" if len(examples) < MIN_EXTERNAL_EXAMPLES else
        "truncated_search" if truncated else "bounded_agreement"
    )
    return {
        "status": status,
        "candidates": len(survivors),
        "candidate_expressions": [ast.unparse(expr) for expr in survivors[:12]],
        "truncated": truncated,
        "external_examples": len(examples),
        "learned_operators_considered": sorted(set(learned_operators)),
        "search": search,
        "coverage": {**checked, "stress_grid_completed": stress_complete},
        "next_query": query,
        "scope": ("bounded source and learned models at the first surviving depth on jointly defined points "
                  "in two finite grids; deeper models may be unexamined; not proof of intent"),
    }
