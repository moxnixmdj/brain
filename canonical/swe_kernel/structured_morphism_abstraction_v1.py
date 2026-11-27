#!/usr/bin/env python3
"""Structured morphism abstraction: the smallest change that makes a learned repair transfer.

WHY THIS EXISTS
---------------
The tree's own ablation receipt (`AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2`)
records two facts in the same breath:

  * the skill store contributes **nothing** to any repair in its catalogue -- store and no-store
    runs are identical; and
  * the learned pattern is *"a single hole over the whole body (pattern has no 'T' and no 'F')"*,
    so its constraint is "match this exact body": **0 proposals on its own witness, 0 on a
    held-out same-family body, 0 in the file text**.

A store whose entries are whole-body holes cannot transfer. Not because retrieval is slow, not
because the index is missing, but because the abstraction is degenerate: what was learned is the
identity function on one string. This module is the non-degenerate operator.

WHAT IT DOES
------------
Given one concrete repair (a before-snippet and an after-snippet), anti-unify the pair into a
two-sided rewrite rule:

    lhs := the before side, with holes exactly where the two sides differ
    rhs := the after side, using the SAME hole names

so `apply(rule, new_before)` binds the holes by matching the lhs and instantiates the rhs. A rule
is admitted only if it survives three fail-closed gates:

  1. FIDELITY        -- applying it to its own witness reproduces the witness's after side exactly;
  2. TRANSFER        -- applying it to the same snippet under renamed identifiers and shifted
                        literals reproduces that variant's after side exactly;
  3. NON-DEGENERACY  -- the after side must carry structure outside its holes. This is the gate
                        the old store failed and the one that matters: a degenerate rule passes
                        1 and 2 trivially and can never transfer, because its lhs is the identity.

Rejected rules are returned with the failing gate named. Nothing is persisted here; this is the
admission test a store must run before it writes.

SCOPE: Python expressions and simple statements, structurally. It is not a program synthesizer and
it does not decide whether a repair is correct -- the caller's verifier does that.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA = "BRAIN_STRUCTURED_MORPHISM_ABSTRACTION_V1"

ADMITTED = "ADMITTED"
REFUSED_DEGENERATE = "REFUSED_DEGENERATE"
REFUSED_FIDELITY = "REFUSED_FIDELITY"
REFUSED_TRANSFER = "REFUSED_TRANSFER"
REFUSED_SHAPE = "REFUSED_SHAPE"
VERDICTS = (ADMITTED, REFUSED_DEGENERATE, REFUSED_FIDELITY, REFUSED_TRANSFER, REFUSED_SHAPE)

# Fields that carry a name. Two nodes differing only here differ in naming, not in shape.
_NAME_FIELDS = {"id", "arg", "name", "attr", "asname", "module"}


@dataclass(frozen=True)
class PHole:
    """A position where the witness and its repair differed. `role` decides what may bind."""

    name: str
    role: str  # 'name' | 'const' | 'expr' | 'value'


@dataclass
class PNode:
    """A concrete AST shape with holes in the places that changed."""

    kind: str
    fields: Dict[str, Any] = field(default_factory=dict)

def _parse(source: str) -> ast.AST:
    """Parse an expression, or a single statement -- both are first-class witnesses here."""
    text = source.strip()
    if not text:
        raise SyntaxError("empty snippet")
    try:
        return ast.parse(text, mode="eval").body
    except SyntaxError:
        tree = ast.parse(text, mode="exec")
        if len(tree.body) != 1:
            raise SyntaxError("expected exactly one statement")
        return tree.body[0]


@dataclass(frozen=True)
class PRef:
    """The after side reads a subterm of whatever the before side bound: `?h0.left`."""

    hole: str
    path: Tuple[Union[str, int], ...]

    def render(self) -> str:
        suffix = "".join(f"[{step}]" if isinstance(step, int) else f".{step}" for step in self.path)
        return f"{self.hole}{suffix}"


@dataclass(frozen=True)
class PValue:
    """A scalar field (a constant's value, a flag) the after side pins to what the witness had."""

    value: Any


@dataclass(frozen=True)
class PLiteral:
    """The after side carries a value the before side cannot derive: pinned, so it cannot transfer."""

    node: ast.AST


def _dump(node: Any) -> str:
    return ast.dump(node, include_attributes=False) if isinstance(node, ast.AST) else repr(node)


def _role(node: Any) -> str:
    if isinstance(node, ast.Name):
        return "name"
    if isinstance(node, ast.Constant):
        return "const"
    if isinstance(node, ast.AST):
        return "expr"
    return "value"


@dataclass
class Rule:
    """A two-sided rewrite rule: match `lhs` against code, bind holes, instantiate `rhs`."""

    lhs: Any
    rhs: Any
    holes: Dict[str, str]
    before: str
    after: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA,
            "lhs": render(self.lhs),
            "rhs": render(self.rhs),
            "holes": dict(sorted(self.holes.items())),
            "before": self.before,
            "after": self.after,
            "structured_nodes": structured_nodes(self.rhs),
            "hole_share": round(hole_share(self.rhs), 4),
        }


def _children(node: ast.AST) -> List[Tuple[Tuple[Union[str, int], ...], ast.AST]]:
    out: List[Tuple[Tuple[Union[str, int], ...], ast.AST]] = []
    for name in node._fields:
        value = getattr(node, name, None)
        if isinstance(value, ast.AST):
            out.append(((name,), value))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, ast.AST):
                    out.append(((name, index), item))
    return out


def _descendant_path(before: ast.AST, after: ast.AST) -> Optional[Tuple[Union[str, int], ...]]:
    """Shortest path from `before` to a subtree structurally equal to `after`, or None."""
    target = _dump(after)
    frontier: List[Tuple[Tuple[Union[str, int], ...], ast.AST]] = [((), before)]
    seen = 0
    while frontier and seen < 512:
        path, node = frontier.pop(0)
        seen += 1
        if _dump(node) == target:
            return path
        frontier.extend((path + step, child) for step, child in _children(node))
    return None


def _unify_pair(before: Any, after: Any, holes: Dict[str, str],
                memo: Dict[Tuple[str, str], PHole],
                names: Dict[str, PHole], *, parameterize_names: bool) -> Tuple[Any, Any]:
    """Anti-unify (before, after) into (lhs_pattern, rhs_pattern) sharing hole names."""
    if isinstance(before, ast.Name) and isinstance(after, ast.Name) and parameterize_names:
        # A name that is unchanged on both sides is still a parameter: the rule must fire on the
        # same shape under different identifiers, which is the whole point of storing it.
        if before.id == after.id:
            hole = names.get(before.id)
            if hole is None:
                hole = PHole(f"?n{len(names)}", "name")
                names[before.id] = hole
                holes[hole.name] = "name"
            return hole, hole
        return _hole_pair(before, after, holes, memo)

    if not isinstance(before, ast.AST) or not isinstance(after, ast.AST):
        return _hole_pair(before, after, holes, memo)
    if type(before) is not type(after):
        return _hole_pair(before, after, holes, memo)

    lhs_fields: Dict[str, Any] = {}
    rhs_fields: Dict[str, Any] = {}
    for name in before._fields:
        left, right = getattr(before, name, None), getattr(after, name, None)
        if isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                return _hole_pair(before, after, holes, memo)
            lhs_items, rhs_items = [], []
            for l_item, r_item in zip(left, right):
                l_pat, r_pat = _unify_pair(l_item, r_item, holes, memo, names,
                                           parameterize_names=parameterize_names)
                lhs_items.append(l_pat)
                rhs_items.append(r_pat)
            lhs_fields[name], rhs_fields[name] = lhs_items, rhs_items
        elif isinstance(left, ast.AST) and isinstance(right, ast.AST):
            l_pat, r_pat = _unify_pair(left, right, holes, memo, names,
                                       parameterize_names=parameterize_names)
            lhs_fields[name], rhs_fields[name] = l_pat, r_pat
        elif left == right:
            lhs_fields[name] = rhs_fields[name] = left
        else:
            # A scalar leaf that differs (a literal's value, a flag) is pinned: the after side
            # carries the witness's value, so the rule cannot silently generalise it.
            hole = _new_hole(before, after, "value", holes, memo)
            lhs_fields[name] = hole
            rhs_fields[name] = PValue(right)
    kind = type(before).__name__
    if lhs_fields == rhs_fields:
        return PNode(kind, lhs_fields), PNode(kind, rhs_fields)
    return PNode(kind, lhs_fields), PNode(kind, rhs_fields)


def _new_hole(before: Any, after: Any, role: str, holes: Dict[str, str],
              memo: Dict[Tuple[str, str], PHole]) -> PHole:
    key = (_dump(before), _dump(after))
    existing = memo.get(key)
    if existing is not None:
        return existing
    if role != "value" and _role(before) != _role(after):
        role = "expr" if isinstance(before, ast.AST) and isinstance(after, ast.AST) else "value"
    hole = PHole(f"?h{len(holes)}", role)
    holes[hole.name] = role
    memo[key] = hole
    return hole


def _hole_pair(before: Any, after: Any, holes: Dict[str, str],
               memo: Dict[Tuple[str, str], PHole]) -> Tuple[Any, Any]:
    """A position that differs: bind it on the lhs, and read it back on the rhs.

    If the after side is a subterm of the before side (the common repair: drop an off-by-one, peel
    a wrapper, reuse an argument) the rule can *project* it and stays transferable. Otherwise the
    after side is pinned to what the witness had, and the transfer gate will refuse it.
    """
    hole = _new_hole(before, after, _role(before), holes, memo)
    if isinstance(before, ast.AST) and isinstance(after, ast.AST):
        path = _descendant_path(before, after)
        if path is not None:
            return hole, PRef(hole.name, path)
    return hole, PLiteral(after)


def abstract(before_source: str, after_source: str, *, parameterize_names: bool = True) -> Rule:
    """Anti-unify one concrete repair into a two-sided rule."""
    before_node = _parse(before_source)
    after_node = _parse(after_source)
    holes: Dict[str, str] = {}
    lhs, rhs = _unify_pair(before_node, after_node, holes, {}, {},
                           parameterize_names=parameterize_names)
    return Rule(lhs=lhs, rhs=rhs, holes=holes,
                before=before_source.strip(), after=after_source.strip())


def _walk(pattern: Any):
    yield pattern
    if isinstance(pattern, (PRef, PLiteral, PValue)):
        return
    if isinstance(pattern, PNode):
        for value in pattern.fields.values():
            if isinstance(value, list):
                for item in value:
                    yield from _walk(item)
            else:
                yield from _walk(value)


def structured_nodes(pattern: Any) -> int:
    return sum(1 for p in _walk(pattern) if isinstance(p, PNode))


def hole_share(pattern: Any) -> float:
    """Fraction of the pattern that is a hole. 1.0 means 'this exact body' -- the degenerate case."""
    nodes = list(_walk(pattern))
    holes = sum(1 for p in nodes if isinstance(p, PHole))
    total = len(nodes)
    return 1.0 if total == 0 else holes / total


def render(pattern: Any) -> str:
    if isinstance(pattern, PHole):
        return pattern.name
    if isinstance(pattern, PRef):
        return pattern.render()
    if isinstance(pattern, PLiteral):
        return f"<{_dump(pattern.node)}>"
    if isinstance(pattern, PValue):
        return f"<{pattern.value!r}>"
    if isinstance(pattern, PNode):
        parts = []
        for key, value in pattern.fields.items():
            if value is None or value == []:
                continue
            if isinstance(value, list):
                parts.append(f"{key}=[{', '.join(render(v) for v in value)}]")
            else:
                parts.append(f"{key}={render(value)}")
        return f"{pattern.kind}({', '.join(parts)})"
    return repr(pattern)


def match(pattern: Any, node: Any, bindings: Dict[str, Any]) -> bool:
    if isinstance(pattern, PHole):
        if pattern.name in bindings:
            bound = bindings[pattern.name]
            if pattern.role == "name":
                return isinstance(node, ast.Name) and node.id == getattr(bound, "id", None)
            if pattern.role == "const":
                return (isinstance(node, ast.Constant)
                        and node.value == getattr(bound, "value", object()))
            return _dump(bound) == _dump(node)
        if pattern.role == "name" and not isinstance(node, ast.Name):
            return False
        if pattern.role == "const" and not isinstance(node, ast.Constant):
            return False
        if pattern.role == "expr" and not isinstance(node, ast.AST):
            return False
        if pattern.role == "value" and isinstance(node, ast.AST):
            return False
        bindings[pattern.name] = node
        return True
    if isinstance(pattern, PRef):
        raise TypeError("a projection belongs to the after side only")
    if isinstance(pattern, (PLiteral, PValue)):
        raise TypeError("a pinned value belongs to the after side only")
    if isinstance(pattern, PNode):
        if not isinstance(node, ast.AST) or type(node).__name__ != pattern.kind:
            return False
        for key, sub in pattern.fields.items():
            value = getattr(node, key, None)
            if isinstance(sub, list):
                if not isinstance(value, list) or len(value) != len(sub):
                    return False
                if not all(match(p, v, bindings) for p, v in zip(sub, value)):
                    return False
            elif not match(sub, value, bindings):
                return False
        return True
    return pattern == node


def instantiate(pattern: Any, bindings: Mapping[str, Any]) -> Any:
    if isinstance(pattern, PRef):
        if pattern.hole not in bindings:
            raise KeyError(f"unbound hole {pattern.hole}")
        node: Any = bindings[pattern.hole]
        for step in pattern.path:
            node = node[step] if isinstance(step, int) else getattr(node, step)
        return node
    if isinstance(pattern, PLiteral):
        return _clone(pattern.node)
    if isinstance(pattern, PValue):
        return pattern.value
    if isinstance(pattern, PHole):
        if pattern.name not in bindings:
            raise KeyError(f"unbound hole {pattern.name}")
        return bindings[pattern.name]
    if isinstance(pattern, PNode):
        node = _new_node(pattern.kind)
        for key, sub in pattern.fields.items():
            if isinstance(sub, list):
                setattr(node, key, [instantiate(item, bindings) for item in sub])
            else:
                setattr(node, key, instantiate(sub, bindings))
        return ast.fix_missing_locations(node)
    return pattern


def _clone(node: Any) -> Any:
    if isinstance(node, ast.AST):
        out = type(node)()
        for name in node._fields:
            value = getattr(node, name, None)
            if isinstance(value, list):
                setattr(out, name, [_clone(v) for v in value])
            else:
                setattr(out, name, _clone(value))
        return ast.fix_missing_locations(out)
    return node


_NODE_TYPES = {name: obj for name, obj in vars(ast).items()
               if isinstance(obj, type) and issubclass(obj, ast.AST)}


def _new_node(kind: str) -> ast.AST:
    cls = _NODE_TYPES.get(kind)
    if cls is None:
        raise KeyError(f"unknown AST node {kind}")
    return cls()


def apply_rule(rule: Rule, source: str) -> Optional[str]:
    """Rewrite `source` with `rule`, or None when the lhs does not match."""
    try:
        node = _parse(source)
    except SyntaxError:
        return None
    bindings: Dict[str, Any] = {}
    if not match(rule.lhs, node, bindings):
        return None
    try:
        return ast.unparse(ast.fix_missing_locations(instantiate(rule.rhs, bindings)))
    except (KeyError, AttributeError, IndexError, TypeError):
        # A projection is defined against the pattern's own bound subtree; a different match may
        # bind a node that has no such field. That is a non-match, not an error.
        return None


def _same(rendered: Optional[str], expected: str) -> bool:
    if rendered is None:
        return False
    try:
        return _dump(_parse(rendered)) == _dump(_parse(expected))
    except SyntaxError:
        return False


def admit(before: str, after: str, held_out: Optional[Tuple[str, str]] = None) -> Dict[str, Any]:
    """Run the three gates and return a fail-closed verdict."""
    try:
        rule = abstract(before, after)
    except (SyntaxError, TypeError, KeyError, ValueError) as exc:
        return {"schema": SCHEMA, "verdict": REFUSED_SHAPE,
                "reason": f"{type(exc).__name__}: {exc}"}

    if render(rule.lhs) == render(rule.rhs):
        return {"schema": SCHEMA, "verdict": REFUSED_DEGENERATE, "rule": rule.to_dict(),
                "reason": "the two sides abstract to the same pattern: this records no change"}

    share = hole_share(rule.rhs)
    structured = structured_nodes(rule.rhs)
    if structured <= 1 or share >= 1.0:
        return {"schema": SCHEMA, "verdict": REFUSED_DEGENERATE, "rule": rule.to_dict(),
                "reason": "after side has no structure outside its holes: the rule matches one exact "
                          "body and cannot transfer -- the degenerate case the old store shipped"}

    produced = apply_rule(rule, before)
    if not _same(produced, after):
        return {"schema": SCHEMA, "verdict": REFUSED_FIDELITY, "rule": rule.to_dict(),
                "produced": produced}

    transfer: Optional[bool] = None
    if held_out is not None:
        variant_before, variant_after = held_out
        transfer = _same(apply_rule(rule, variant_before), variant_after)
        if not transfer:
            return {"schema": SCHEMA, "verdict": REFUSED_TRANSFER, "rule": rule.to_dict(),
                    "produced": apply_rule(rule, variant_before)}

    return {"schema": SCHEMA, "verdict": ADMITTED, "rule": rule.to_dict(),
            "fidelity": produced, "transfer": transfer}


def rename(source: str, names: Mapping[str, str],
           literals: Optional[Mapping[Any, Any]] = None) -> str:
    """Build the held-out variant the transfer gate uses: same shape, new names and literals."""
    literals = dict(literals or {})

    class _Rename(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
            node.id = names.get(node.id, node.id)
            return node

        def visit_arg(self, node: ast.arg) -> ast.AST:  # noqa: N802
            node.arg = names.get(node.arg, node.arg)
            return node

        def visit_Constant(self, node: ast.Constant) -> ast.AST:  # noqa: N802
            if node.value in literals:
                node.value = literals[node.value]
            return node

    tree = ast.parse(source)
    _Rename().visit(tree)
    return ast.unparse(ast.fix_missing_locations(tree)).strip()


# --------------------------------------------------------------------------- #
# Self-check: the gates must separate, and the degenerate control must be refused
# --------------------------------------------------------------------------- #

WITNESS = ("for i in range(len(xs) - 1):\n    total += xs[i]",
           "for i in range(len(xs)):\n    total += xs[i]")
VARIANT = ("for j in range(len(ys) - 1):\n    acc += ys[j]",
           "for j in range(len(ys)):\n    acc += ys[j]")
DECOY = ("x + 1", "n * k")


def _self_check() -> Dict[str, Any]:
    checks: List[bool] = []
    detail: Dict[str, Any] = {}

    admitted = admit(WITNESS[0], WITNESS[1], VARIANT)
    detail["witness"] = admitted
    checks.append(admitted["verdict"] == ADMITTED)
    checks.append(admitted.get("transfer") is True)
    checks.append(admitted["rule"]["structured_nodes"] > 3)

    decoy = admit(DECOY[0], DECOY[1])
    detail["decoy"] = decoy
    checks.append(decoy["verdict"] == REFUSED_DEGENERATE)

    no_transfer = admit(WITNESS[0], "for i in range(len(xs) - 1):\n    total += 0",
                        ("for j in range(len(ys) - 1):\n    acc += ys[j]",
                         "for j in range(len(ys) - 1):\n    acc += 1"))
    detail["transfer_control"] = no_transfer
    checks.append(no_transfer["verdict"] == REFUSED_TRANSFER)

    renamed = rename(WITNESS[0], {"i": "j", "xs": "ys", "total": "acc"})
    checks.append(_same(renamed, VARIANT[0]))

    # A rule admitted on its witness must fire on a *third*, unseen surface of the same family.
    third = "for k in range(len(rows) - 1):\n    seen += rows[k]"
    third_expected = "for k in range(len(rows)):\n    seen += rows[k]"
    rule = abstract(WITNESS[0], WITNESS[1])
    produced = apply_rule(rule, third)
    detail["third_surface"] = {"source": third, "produced": produced}
    checks.append(_same(produced, third_expected))

    # Ablation: without name parameterization the rule is pinned to its witness's identifiers and
    # cannot fire on an unseen surface. This is the measured contribution of that one part.
    no_param = abstract(WITNESS[0], WITNESS[1], parameterize_names=False)
    ablated = apply_rule(no_param, third)
    detail["name_parameterization_ablation"] = {
        "without": ablated,
        "shares": no_param.to_dict()["holes"],
    }
    checks.append(not _same(ablated, third_expected))

    return {
        "schema": f"{SCHEMA}_SELF_CHECK",
        "checks": len(checks),
        "passed": sum(1 for c in checks if c),
        "detail": detail,
        "verdict": "SELF_CHECK_PASS" if all(checks) else "SELF_CHECK_FAIL",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--before", default="")
    parser.add_argument("--after", default="")
    parser.add_argument("--held-out-before", default="")
    parser.add_argument("--held-out-after", default="")
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)

    if args.self_check or not (args.before and args.after):
        report = _self_check()
        print(json.dumps(report, indent=2, sort_keys=True)[:4000])
        return 0 if report["verdict"] == "SELF_CHECK_PASS" else 1

    held = (args.held_out_before, args.held_out_after) if args.held_out_before else None
    result = admit(args.before, args.after, held)
    if args.json:
        path = pathlib.Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True)[:4000])
    return 0 if result["verdict"] == ADMITTED else 1


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
