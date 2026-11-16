"""Where an edit comes from, and why that decides whether one experience can ever be enough.

THE DEFECT THIS FILE EXISTS TO REMOVE
-------------------------------------
The tree's repair machinery enumerates a hand-written list of edits: swap a comparison operator,
swap a binary operator, swap `min`/`max` or `any`/`all`, add a None-guard, substitute a literal mined
from the tests. Measured against a public corpus it did not choose, that list decides everything --
and it decides it BEFORE any search happens. `n ^= n - 1` printed for bit counting is repaired by
`&=`; there is no `ast.AugAssign` rule in the list, so no amount of budget, depth, or candidate
count can reach the repair. A capability bounded at 0 by vocabulary is not a search problem.

The mistake is architectural, not a missing entry. A hand-listed basis says: WE enumerate the ways
code can be wrong. That is a knowledge house of facts about bugs, written down by hand, and it can
never grow except by someone editing the list. It also cannot be what "show it once, it learns
permanently" means, because a demonstration adds an INSTANCE of a known edit type, never a new
type -- so the vocabulary is frozen at whatever the author imagined.

WHAT REPLACES IT
----------------
A demonstration is two artifacts: the defective source and the repaired source. Comparing their
ASTs yields a *structured edit*: the node type that changed, the role that changed, its immediate
context, and the substitution made there. That edit is then GENERALIZED -- its ancestry of node
types becomes an applicability condition, its operator pair becomes the content, and how many
independent demonstrations supported it becomes the template's support. The basis is therefore a
fold over experience, not a list in a file. Show it a fix, and the fix's SHAPE enters the space of
things it can try; show it the same shape twice and it ranks higher.

The honest consequence, stated up front: this makes one demonstration teach a *kind of edit*, not a
*fix*. Whether the kind applies to a new program is decided by whether the context matches and then
by the program's own oracle -- never by resemblance, and never by this file.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
- No semantic repair. Templates substitute one leaf for another inside an existing node. A fix that
  needs a new statement (a guard, an early return) has no context-preserving substitution and is
  reported NON_EXECUTABLE rather than approximated -- the same refusal `lesson_localization_v1`
  makes, for the same reason.
- No promotion. Candidates are verified against the caller's own test command; nothing is written
  back and nothing is credited.
- No model, no network, no spend.

Authority NONE. This module produces candidates and a count of what an oracle accepted.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import json
import pathlib
import sys
from typing import Any, Iterable, Iterator, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "BRAIN_INDUCED_EDIT_BASIS_V1"
AUTHORITY = "NONE__CANDIDATE_GENERATOR_PLUS_ORACLE_COUNT"

#: Operator classes a single-leaf substitution may install. Anything outside this set is not an
#: edit this module can express, and saying so is the point -- a silent skip would look like a
#: search that simply did not find it.
_OPERATORS = {name: getattr(ast, name) for name in (
    "Add", "Sub", "Mult", "Div", "FloorDiv", "Mod", "Pow", "MatMult", "LShift", "RShift",
    "BitOr", "BitXor", "BitAnd", "Lt", "LtE", "Gt", "GtE", "Eq", "NotEq", "Is", "IsNot",
    "In", "NotIn", "And", "Or", "Not", "UAdd", "USub", "Invert",
)}
_OP_BY_CLASS = {v: k for k, v in _OPERATORS.items()}

#: Roles this module will substitute. `ops` is a one-element list on Compare; `op` is a single node
#: on BinOp/AugAssign/UnaryOp; `id` and `value` are leaves on Name and Constant.
_SINGLE_LEAF_ROLES = ("op", "ops", "id", "value", "attr")

NON_EXECUTABLE_REASON = {
    "SUBTREE_REWRITE": "the fix changes the shape of the code, not a leaf inside it; a "
                       "context-preserving substitution cannot express it",
    "STATEMENT_INSERT": "the fix adds a statement; no existing context is preserved",
    "STATEMENT_DELETE": "the fix removes a statement; no existing context is preserved",
}


def _load_code(module_name: str) -> Any:
    """The repair loop loads its primitive by path; reuse that loader rather than a second copy."""
    return __import__(module_name, fromlist=["*"])


@dataclasses.dataclass(frozen=True)
class EditTemplate:
    """One generalized edit, with the experience that supports it.

    `context` is the ancestry of node types ending at the changed node's PARENT, deepest last. It is
    the applicability condition: the template may only be tried where the same ancestry occurs,
    trimmed to `context_depth` levels so that a fix seen inside a `for` can still apply inside a
    `while` when the depth is 1 -- which is a decision the caller makes explicitly, per run.
    """
    kind: str                 # OP_PAIR | NAME_PAIR | CONST_PAIR | NON_EXECUTABLE
    node_type: str            # the changed node's AST type, e.g. "AugAssign"
    role: str                 # which field changed
    context: tuple[str, ...]  # ancestry types, root -> parent
    old: Any = None           # op class name / identifier / literal
    new: Any = None
    reason: str = ""          # for NON_EXECUTABLE: which kind of shape change this was
    support: int = 0          # independent demonstrations that produced this same template
    taught_by: tuple[str, ...] = ()

    @property
    def context_depth(self) -> int:
        return len(self.context)

    @property
    def executable(self) -> bool:
        return self.kind != "NON_EXECUTABLE"

    def key(self, depth: int | None = None) -> tuple:
        ctx = self.context if depth is None else self.context[-depth:] if depth else ()
        return (self.kind, self.node_type, self.role, ctx, json.dumps(self.old, sort_keys=True, default=str),
                json.dumps(self.new, sort_keys=True, default=str))

    def template_id(self) -> str:
        return hashlib.sha256(json.dumps(list(self.key()), default=str).encode()).hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        payload = dataclasses.asdict(self)
        payload["context"] = list(self.context)
        payload["taught_by"] = list(self.taught_by)
        payload["template_id"] = self.template_id()
        return payload


# --------------------------------------------------------------------------------------------------
# induction: demonstration pair -> structured edit -> generalized template
# --------------------------------------------------------------------------------------------------

def _parse(source: str, where: str) -> ast.AST:
    try:
        return ast.parse(source)
    except SyntaxError as error:
        raise ValueError(f"UNPARSEABLE_{where}: {error.msg}") from error


def _leaf_name(value: Any) -> Any:
    if isinstance(value, type) and issubclass(value, ast.AST):
        return _OP_BY_CLASS.get(value, value.__name__)
    return value


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    """Remove inert string statements before comparing.

    QuixBugs' published "correct" programs append the DEFECTIVE source inside a trailing string
    literal (they document the bug that way), and its defective programs carry a descriptive
    docstring the fix omits. A bare string statement is semantically inert wherever it appears, so
    dropping all of them is behaviour-preserving -- and without it, induction reads documentation as
    edits, which is exactly the garbage the first run of this file produced.
    """
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if not isinstance(block, list):
                continue
            setattr(node, field, [statement for statement in block if not _is_inert_string(statement)])
    return tree


def _is_inert_string(statement: Any) -> bool:
    return (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str))


def _fingerprint(node: ast.AST) -> str:
    return ast.dump(node, annotate_fields=False, include_attributes=False)


def _diff_nodes(a: ast.AST, b: ast.AST, ancestry: tuple[str, ...],
                out: list[tuple[str, str, str, tuple[str, ...], Any, Any]], depth: int = 0) -> None:
    """Walk two trees in step and record every LEAF that differs, with the path that reaches it.

    Leaves are compared through `_leaf_name`, which turns an operator class into its name -- an
    operator is a leaf of the edit space, not a subtree to descend into. Getting that wrong is what
    made the first version of this file report `^=` -> `&=` as a SHAPE change and thus unreachable.
    """
    if depth > 200:
        raise ValueError("AST_TOO_DEEP")
    if type(a) is not type(b):
        out.append(("SHAPE", type(a).__name__, "", ancestry, _opaque(a), _opaque(b)))
        return
    if isinstance(a, (ast.Name, ast.Constant, ast.Attribute)):
        for role in ("id", "attr", "value"):
            if not hasattr(a, role) and not hasattr(b, role):
                continue
            va, vb = getattr(a, role, None), getattr(b, role, None)
            if role in ("id", "attr") and isinstance(va, str) and isinstance(vb, str) and va != vb:
                out.append(("LEAF", type(a).__name__, role, ancestry, va, vb))
            if role == "value" and type(va) in (int, float, str, bool, type(None)) and va != vb:
                out.append(("LEAF", type(a).__name__, role, ancestry, va, vb))
        return
    for field in a._fields:
        if field in ("ctx", "type_comment", "kind", "conversion", "format_spec"):
            continue
        va, vb = getattr(a, field, None), getattr(b, field, None)
        if field == "op" and isinstance(va, ast.AST) and isinstance(vb, ast.AST):
            if _leaf_name(type(va)) != _leaf_name(type(vb)):
                out.append(("LEAF", type(a).__name__, "op", ancestry,
                            _leaf_name(type(va)), _leaf_name(type(vb))))
            continue
        if field == "ops" and isinstance(va, list) and isinstance(vb, list):
            if len(va) != len(vb):
                out.append(("SHAPE", type(a).__name__, "ops", ancestry, _opaque(a), _opaque(b)))
                continue
            for left, right in zip(va, vb):
                if _leaf_name(type(left)) != _leaf_name(type(right)):
                    out.append(("LIST_LEAF", type(a).__name__, "ops", ancestry,
                                _leaf_name(type(left)), _leaf_name(type(right))))
            continue
        if isinstance(va, list) and isinstance(vb, list):
            if len(va) == len(vb):
                for left, right in zip(va, vb):
                    if isinstance(left, ast.AST) and isinstance(right, ast.AST):
                        _diff_nodes(left, right, ancestry + (type(a).__name__,), out, depth + 1)
                    elif type(left) in (int, float, str, bool, type(None)) and left != right:
                        out.append(("LIST_LEAF", type(a).__name__, field, ancestry, left, right))
                continue
            # Unequal statement counts: align first, so one inserted line is reported as an
            # insertion instead of erasing every difference below it.
            import difflib as _dl
            left_keys = [_fingerprint(x) if isinstance(x, ast.AST) else repr(x) for x in va]
            right_keys = [_fingerprint(x) if isinstance(x, ast.AST) else repr(x) for x in vb]
            for tag, i1, i2, j1, j2 in _dl.SequenceMatcher(a=left_keys, b=right_keys, autojunk=False).get_opcodes():
                if tag == "equal":
                    continue
                if tag == "replace" and (i2 - i1) == (j2 - j1):
                    for left, right in zip(va[i1:i2], vb[j1:j2]):
                        if isinstance(left, ast.AST) and isinstance(right, ast.AST):
                            _diff_nodes(left, right, ancestry + (type(a).__name__,), out, depth + 1)
                elif tag in ("insert", "replace") and (i2 == i1 or tag == "insert"):
                    out.append(("STATEMENT", type(a).__name__, field, ancestry, None, "INSERT"))
                elif tag in ("delete", "replace"):
                    out.append(("STATEMENT", type(a).__name__, field, ancestry, "DELETE", None))
            continue
        if isinstance(va, ast.AST) and isinstance(vb, ast.AST):
            _diff_nodes(va, vb, ancestry + (type(a).__name__,), out, depth + 1)


def type_field_name(node: ast.AST, field: str) -> str:  # pragma: no cover - naming helper
    return f"{type(node).__name__}.{field}"


def _opaque(node: ast.AST) -> str:
    """A stable, comparable fingerprint of a subtree, used only to detect that it changed."""
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def _classify(kind: str, node_type: str, role: str, old: Any, new: Any) -> tuple[str, Any, Any, str]:
    """Decide what an observed difference IS. Refuse rather than approximate."""
    if kind == "SHAPE":
        return "NON_EXECUTABLE", None, None, "SUBTREE_REWRITE"
    if kind == "STATEMENT":
        return "NON_EXECUTABLE", None, None, ("STATEMENT_INSERT" if new == "INSERT" else "STATEMENT_DELETE")
    if kind == "LIST_LEAF" and role == "ops":
        if old in _OPERATORS and new in _OPERATORS:
            return "OP_PAIR", old, new, ""
        return "NON_EXECUTABLE", None, None, "SUBTREE_REWRITE"
    if kind == "LEAF":
        if role in ("op", "ops"):
            if old in _OPERATORS and new in _OPERATORS:
                return "OP_PAIR", old, new, ""
            return "NON_EXECUTABLE", None, None, "SUBTREE_REWRITE"
        if role in ("id", "attr"):
            return "NAME_PAIR", old, new, ""
        if role == "value":
            return "CONST_PAIR", old, new, ""
    return "NON_EXECUTABLE", None, None, "SUBTREE_REWRITE"


def induce_templates(pairs: Iterable[tuple[str, str, str]], *, context_depth: int = 1,
                     max_templates_per_pair: int = 8) -> list[EditTemplate]:
    """Fold demonstrations into a basis.

    `pairs` is (name, defective_source, repaired_source). The name is carried into `taught_by` so a
    template can never be mistaken for something the system invented: every executable template
    names the demonstrations that produced it, and `support` counts distinct ones.

    The basis is deduplicated on (kind, node type, role, context trimmed to `context_depth`, old,
    new) -- so two bugs repaired the same way appear once with support 2, which is the only
    evidence a mechanism like this can honestly accumulate.
    """
    if context_depth < 0 or context_depth > 8:
        raise ValueError("CONTEXT_DEPTH_OUT_OF_RANGE")
    folded: dict[tuple, EditTemplate] = {}
    for name, defective, repaired in pairs:
        found: list[tuple[str, str, str, tuple[str, ...], Any, Any]] = []
        _diff_nodes(_strip_docstrings(_parse(defective, "DEFECTIVE")),
                    _strip_docstrings(_parse(repaired, "REPAIRED")), (), found)
        for kind, node_type, role, ancestry, old, new in found[:max_templates_per_pair]:
            template_kind, want_old, want_new, reason = _classify(kind, node_type, role, old, new)
            context = ancestry[-context_depth:] if context_depth else ()
            candidate = EditTemplate(kind=template_kind, node_type=node_type, role=role,
                                     context=tuple(context), old=want_old, new=want_new,
                                     reason=reason, support=1, taught_by=(name,))
            existing = folded.get(candidate.key())
            if existing is None:
                folded[candidate.key()] = candidate
            else:
                merged = dataclasses.replace(
                    existing, support=existing.support + 1,
                    taught_by=tuple(sorted(set(existing.taught_by) | {name})))
                folded[candidate.key()] = merged
    return sorted(folded.values(), key=lambda t: (not t.executable, -t.support, t.template_id()))


# --------------------------------------------------------------------------------------------------
# application: template x site -> candidate source
# --------------------------------------------------------------------------------------------------

def _sites(tree: ast.AST) -> Iterator[tuple[tuple[str, ...], tuple, ast.AST, ast.AST | None, str]]:
    """Every node, with a UNIQUE path to it as well as the type ancestry that reaches it.

    Two sibling `AugAssign`s in one function share the same type ancestry, so ancestry alone cannot
    say which one a template was induced from -- and mutating "the first node with the same ancestry"
    would silently repair a different statement than the one matched. The path is the identity; the
    ancestry is only the applicability condition.
    """
    stack: list[tuple[tuple[str, ...], tuple, ast.AST, ast.AST | None, str]] = [((), (), tree, None, "")]
    while stack:
        ancestry, path, node, parent, field = stack.pop()
        yield ancestry, path, node, parent, field
        for name, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                stack.append((ancestry + (type(node).__name__,), path + ((name, None),), value, node, name))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        stack.append((ancestry + (type(node).__name__,), path + ((name, index),), item, node, name))


def _resolve(tree: ast.AST, path: tuple) -> ast.AST | None:
    """Follow a site path. A path only exists in the tree it came from, so a miss is normal:
    the repaired program may have a different node at that position, or none at all."""
    node: Any = tree
    for field, index in path:
        try:
            node = getattr(node, field) if index is None else getattr(node, field)[index]
        except (AttributeError, IndexError, TypeError):
            return None
        if not isinstance(node, ast.AST):
            return None
    return node


def _install(parent: ast.AST, field: str, node: ast.AST, role: str, new: Any) -> bool:
    """Put `new` where the template says, in place. Returns False when this site cannot take it."""
    try:
        if role == "ops":
            current = getattr(node, "ops")
            if len(current) != 1:
                return False
            target = new if isinstance(new, type) else _OPERATORS.get(str(new))
            if target is None:
                return False
            node.ops = [target()]
            return True
        if role == "op":
            target = new if isinstance(new, type) else _OPERATORS.get(str(new))
            if target is None or not isinstance(getattr(node, "op", None), ast.AST):
                return False
            node.op = target()
            return True
        if role in ("id", "attr"):
            if not isinstance(getattr(node, role, None), str):
                return False
            setattr(node, role, str(new))
            return True
        if role == "value":
            if not isinstance(getattr(node, "value", None), (int, float, str, bool, type(None))):
                return False
            node.value = new
            return True
    except (AttributeError, TypeError, ValueError):
        return False
    return False


def _site_value(node: ast.AST, role: str) -> Any:
    if role == "ops":
        current = getattr(node, "ops", None)
        if not current or len(current) != 1:
            return None
        return _OP_BY_CLASS.get(type(current[0]), type(current[0]).__name__)
    if role == "op":
        op = getattr(node, "op", None)
        return _OP_BY_CLASS.get(type(op), type(op).__name__) if isinstance(op, ast.AST) else None
    if role in ("id", "attr"):
        return getattr(node, role, None)
    if role == "value":
        return getattr(node, "value", None)
    return None


def candidates_from_templates(source: str, templates: Sequence[EditTemplate], *,
                              max_candidates: int = 200) -> list[dict[str, Any]]:
    """Every (template, matching site) pair that produces a syntactically valid program.

    A template only fires where its context appears AND the site currently holds the template's OLD
    value -- i.e. where the demonstration's precondition is literally satisfied. That is what makes
    this transfer rather than analogy, and it is also why it fires rarely: the measured firing rate
    is the honest measure of how far one demonstration travels.
    """
    tree = _parse(source, "CANDIDATE_SOURCE")
    out: list[dict[str, Any]] = []
    for template in templates:
        if not template.executable:
            continue
        for ancestry, path, node, parent, field in _sites(tree):
            if parent is None or type(node).__name__ != template.node_type:
                continue
            if template.context and tuple(ancestry[-len(template.context):]) != template.context:
                continue
            if _site_value(node, template.role) != template.old:
                continue
            mutated = copy.deepcopy(tree)
            target = _resolve(mutated, path)
            if target is None or type(target).__name__ != template.node_type:
                continue
            if not _install(None, field, target, template.role, template.new):
                continue
            try:
                text = ast.unparse(ast.fix_missing_locations(mutated))
                ast.parse(text)
            except (SyntaxError, ValueError):
                continue
            out.append({"template_id": template.template_id(), "template": template.as_dict(),
                        "mutation": f"{template.node_type}.{template.role}:{template.old}->{template.new}",
                        "site_path": [list(step) for step in path], "site_context": list(ancestry),
                        "source": text, "source_sha256": hashlib.sha256(text.encode()).hexdigest()})
            if len(out) >= max_candidates:
                return out
    return out
    return out


# --------------------------------------------------------------------------------------------------
# rung two: one node replaced by another, generalized by anti-unification to holes
# --------------------------------------------------------------------------------------------------
#
# Measured on QuixBugs (40 real fixes, classified by the smallest subtree that differs):
#   leaf substitution inside an existing node        9/40
#   ONE node replaced at ONE position               18/40
#   several coordinated positions                    7/40
#   a statement inserted or deleted                  6/40
# So two thirds of real fixes live at rung two, and the leaf-only basis above cannot express most of
# them. The reason a node replacement can still travel between programs is anti-unification: what the
# two sides SHARE stays literal, what they differ in becomes a hole, and the holes are matched again
# at the next site. `mid` -> `mid + 1` is therefore not a fact about `mid`; it is `X -> X + 1`, whose
# only remaining commitment is the TYPE of the thing that changed (a Name) -- a constraint taken
# from the demonstration rather than invented, and the reason the search stays small.
#
# This is deliberately NOT the crystallizer's `anti_unify_code_rule`: that one unifies token
# snippets and cannot say "wrap these same holes in max(0, ...) at this position", and it has no
# notion of the site's context. The storage, admission and scope machinery is not duplicated here --
# this module only proposes candidates and counts what an oracle accepted.

HOLE_PREFIX = "__brain_hole_"


def _is_hole(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id.startswith(HOLE_PREFIX)


def _lgg(a: ast.AST, b: ast.AST, holes: dict[str, str], counter: list[int]) -> tuple[ast.AST, ast.AST, bool]:
    """Least general generalization of two subtrees, with shared holes for what differs.

    Returns (pattern_of_a, pattern_of_b, changed). `changed` is False when the two sides unify
    completely -- meaning the difference cannot be expressed relationally, and the caller must fall
    back to a literal replacement instead of silently emitting a rule that edits nothing.
    """
    if type(a) is not type(b):
        name = f"{HOLE_PREFIX}{counter[0]}__"
        counter[0] += 1
        holes[name] = _opaque(b)  # recorded for reporting only; matching binds at apply time
        return ast.Name(id=name, ctx=ast.Load()), ast.Name(id=name, ctx=ast.Load()), True
    if isinstance(a, (ast.Name, ast.Constant, ast.Attribute)):
        same = _opaque(a) == _opaque(b)
        if same:
            return copy.deepcopy(a), copy.deepcopy(b), False
        name = f"{HOLE_PREFIX}{counter[0]}__"
        counter[0] += 1
        holes[name] = _opaque(b)
        return ast.Name(id=name, ctx=ast.Load()), ast.Name(id=name, ctx=ast.Load()), True
    changed = False
    left, right = copy.deepcopy(a), copy.deepcopy(b)
    for field in a._fields:
        if field in ("ctx", "type_comment", "kind", "conversion", "format_spec"):
            continue
        va, vb = getattr(a, field, None), getattr(b, field, None)
        if isinstance(va, ast.AST) and isinstance(vb, ast.AST):
            pa, pb, ch = _lgg(va, vb, holes, counter)
            setattr(left, field, pa)
            setattr(right, field, pb)
            changed = changed or ch
        elif isinstance(va, list) and isinstance(vb, list):
            if len(va) != len(vb) or any(not isinstance(x, ast.AST) for x in va + vb):
                changed = True
                continue
            new_left, new_right = [], []
            for item_a, item_b in zip(va, vb):
                pa, pb, ch = _lgg(item_a, item_b, holes, counter)
                new_left.append(pa)
                new_right.append(pb)
                changed = changed or ch
            setattr(left, field, new_left)
            setattr(right, field, new_right)
        elif _leaf_name(va) != _leaf_name(vb):
            changed = True
    return left, right, changed


@dataclasses.dataclass(frozen=True)
class NodeTemplate:
    """One node-level edit, generalized: `old_pattern` matches, `new_pattern` replaces.

    `root_type` is the demonstration's own constraint -- the type of the node that was replaced --
    and is what keeps a relational rule from firing at every position in a file. `kind` is
    RELATIONAL when holes carry the transfer, LITERAL when the edit could not be generalized and may
    only be replayed where the exact subtree occurs.
    """
    kind: str                     # RELATIONAL | LITERAL
    mode: str                     # EXPR | STMT -- how the pattern text parses back
    root_type: str
    context: tuple[str, ...]
    old_pattern: str              # ast.dump of the matcher
    new_pattern: str
    support: int = 0
    taught_by: tuple[str, ...] = ()

    def template_id(self) -> str:
        payload = json.dumps([self.kind, self.root_type, list(self.context), self.old_pattern, self.new_pattern])
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "mode": self.mode, "root_type": self.root_type,
                "context": list(self.context),
                "old_pattern": self.old_pattern, "new_pattern": self.new_pattern,
                "support": self.support, "taught_by": list(self.taught_by),
                "template_id": self.template_id(), "rung": "NODE_SUBSTITUTION"}


def _occurrences(container: ast.AST, target_fingerprint: str) -> list[tuple]:
    """Every position inside `container` holding a subtree identical to the target."""
    return [path for _ancestry, path, node, _parent, _field in _sites(container)
            if _opaque(node) == target_fingerprint]


def _hole(name: str = HOLE_PREFIX + "0__") -> ast.Name:
    return ast.Name(id=name, ctx=ast.Load())


def induce_node_templates(pairs: Iterable[tuple[str, str, str]], *, context_depth: int = 1
                          ) -> list[NodeTemplate]:
    """Fold demonstrations into node-level templates: the second rung of the same ladder.

    Only the DEEPEST differing positions are kept. A fix to `binsearch(mid, end)` also differs at the
    enclosing call, but teaching both would put "rewrite the whole call" and "advance the index by
    one" in the same basis, and the coarser one travels nowhere. Taking the smallest subtree that
    differs is what makes the lesson `X -> X + 1` instead of a fact about one call site.
    """
    folded: dict[tuple, NodeTemplate] = {}
    for name, defective, repaired in pairs:
        old_tree = _strip_docstrings(_parse(defective, "DEFECTIVE"))
        new_tree = _strip_docstrings(_parse(repaired, "REPAIRED"))
        differed: dict[tuple, tuple[ast.AST, ast.AST]] = {}
        for ancestry, path, node, parent, field in _sites(old_tree):
            if parent is None:
                continue
            other = _resolve(new_tree, path)
            if other is None or _opaque(node) == _opaque(other):
                continue
            differed[path] = (node, other, ancestry)  # type: ignore[assignment]
        paths = list(differed)
        deepest = [p for p in paths
                   if not any(len(q) > len(p) and q[:len(p)] == p for q in paths)]
        for path in sorted(deepest):
            node, other, ancestry = differed[path]  # type: ignore[misc]
            mode = "EXPR" if isinstance(node, ast.expr) else "STMT"
            holes: dict[str, str] = {}
            pat_old, pat_new, changed = _lgg(node, other, holes, [0])
            if type(node) is not type(other):
                # The kind of node changed, so there is no common generalization of the two trees --
                # the fix is CONTAINMENT, and that is the shape most real repairs take: `mid` becomes
                # `mid + 1`, a sum becomes `max(0, sum)`, a value becomes a guarded version of itself.
                # Expressing it as "the old node, wrapped" is what makes the lesson travel: the
                # pattern says `H -> H + 1`, not "this call site is wrong".
                inside_new = _occurrences(other, _opaque(node))
                inside_old = _occurrences(node, _opaque(other))
                if len(inside_new) == 1:
                    kind = "RELATIONAL"
                    pat_old = _hole()
                    pat_new = copy.deepcopy(other)
                    parent_of_hole = _resolve(pat_new, inside_new[0][:-1])
                    leaf_field, index = inside_new[0][-1]
                    if parent_of_hole is None:
                        kind = "LITERAL"
                    elif index is None:
                        setattr(parent_of_hole, leaf_field, _hole())
                    else:
                        getattr(parent_of_hole, leaf_field)[index] = _hole()
                elif len(inside_old) == 1:
                    kind = "RELATIONAL"
                    pat_new = _hole()
                    pat_old = copy.deepcopy(node)
                    parent_of_hole = _resolve(pat_old, inside_old[0][:-1])
                    leaf_field, index = inside_old[0][-1]
                    if parent_of_hole is None:
                        kind = "LITERAL"
                    elif index is None:
                        setattr(parent_of_hole, leaf_field, _hole())
                    else:
                        getattr(parent_of_hole, leaf_field)[index] = _hole()
                else:
                    kind = "LITERAL"
                if kind == "RELATIONAL":
                    old_pattern, new_pattern = ast.unparse(pat_old), ast.unparse(pat_new)
                else:
                    old_pattern, new_pattern = ast.unparse(node), ast.unparse(other)
            elif not changed or _opaque(pat_old) == _opaque(pat_new):
                kind = "LITERAL"
                old_pattern, new_pattern = ast.unparse(node), ast.unparse(other)
            else:
                kind = "RELATIONAL"
                old_pattern, new_pattern = ast.unparse(pat_old), ast.unparse(pat_new)
            context = tuple(ancestry[-context_depth:]) if context_depth else ()
            candidate = NodeTemplate(kind=kind, mode=mode, root_type=type(node).__name__,
                                     context=context, old_pattern=old_pattern,
                                     new_pattern=new_pattern, support=1, taught_by=(name,))
            key = (candidate.kind, candidate.mode, candidate.root_type, candidate.context,
                   candidate.old_pattern, candidate.new_pattern)
            if key in folded:
                existing = folded[key]
                candidate = dataclasses.replace(
                    existing, support=existing.support + 1,
                    taught_by=tuple(sorted(set(existing.taught_by) | {name})))
            folded[key] = candidate
    return sorted(folded.values(), key=lambda t: (t.kind != "RELATIONAL", -t.support, t.template_id()))


def _parse_pattern(text: str, mode: str) -> ast.AST | None:
    try:
        if mode == "EXPR":
            return ast.parse(text, mode="eval").body
        body = ast.parse(text, mode="exec").body
        return body[0] if len(body) == 1 else None
    except SyntaxError:
        return None


def _unify(pattern: ast.AST, node: ast.AST, bindings: dict[str, ast.AST]) -> bool:
    if _is_hole(pattern):
        previous = bindings.get(pattern.id)
        if previous is None:
            bindings[pattern.id] = node
            return True
        return _opaque(previous) == _opaque(node)
    if type(pattern) is not type(node):
        return False
    for field in pattern._fields:
        if field in ("ctx", "type_comment"):
            continue
        va, vb = getattr(pattern, field, None), getattr(node, field, None)
        if isinstance(va, ast.AST):
            if not isinstance(vb, ast.AST) or not _unify(va, vb, bindings):
                return False
        elif isinstance(va, list):
            if not isinstance(vb, list) or len(va) != len(vb):
                return False
            for left, right in zip(va, vb):
                if isinstance(left, ast.AST):
                    if not isinstance(right, ast.AST) or not _unify(left, right, bindings):
                        return False
        elif _leaf_name(va) != _leaf_name(vb):
            return False
    return True


def _instantiate(pattern: ast.AST, bindings: dict[str, ast.AST]) -> ast.AST | None:
    if _is_hole(pattern):
        bound = bindings.get(pattern.id)
        return None if bound is None else copy.deepcopy(bound)
    clone = copy.deepcopy(pattern)
    for field in pattern._fields:
        if field in ("ctx", "type_comment"):
            continue
        value = getattr(pattern, field, None)
        if isinstance(value, ast.AST):
            made = _instantiate(value, bindings)
            if made is None:
                return None
            setattr(clone, field, made)
        elif isinstance(value, list):
            made_items = []
            for item in value:
                if isinstance(item, ast.AST):
                    made = _instantiate(item, bindings)
                    if made is None:
                        return None
                    made_items.append(made)
                else:
                    made_items.append(item)
            setattr(clone, field, made_items)
    return clone


def candidates_from_node_templates(source: str, templates: Sequence[NodeTemplate], *,
                                   max_candidates: int = 200) -> list[dict[str, Any]]:
    """Every place a node template matches and produces a syntactically valid program."""
    tree = _parse(source, "CANDIDATE_SOURCE")
    sites = list(_sites(tree))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for template in templates:
        pattern_old = _parse_pattern(template.old_pattern, template.mode)
        pattern_new = _parse_pattern(template.new_pattern, template.mode)
        if pattern_old is None or pattern_new is None:
            continue
        for ancestry, path, node, parent, field in sites:
            if parent is None or type(node).__name__ != template.root_type:
                continue
            if template.context and tuple(ancestry[-len(template.context):]) != template.context:
                continue
            bindings: dict[str, ast.AST] = {}
            if not _unify(pattern_old, node, bindings):
                continue
            replacement = _instantiate(pattern_new, bindings)
            if replacement is None:
                continue
            mutated = copy.deepcopy(tree)
            target_parent = _resolve(mutated, path[:-1]) if path else None
            if target_parent is None:
                continue
            leaf_field, index = path[-1]
            if index is None:
                setattr(target_parent, leaf_field, replacement)
            else:
                getattr(target_parent, leaf_field)[index] = replacement
            try:
                text = ast.unparse(ast.fix_missing_locations(mutated))
                ast.parse(text)
            except (SyntaxError, ValueError):
                continue
            digest = hashlib.sha256(text.encode()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            out.append({"template_id": template.template_id(), "template": template.as_dict(),
                        "mutation": f"{template.root_type}->{template.root_type}({template.kind})",
                        "site_path": [list(step) for step in path], "site_context": list(ancestry),
                        "source": text, "source_sha256": digest})
            if len(out) >= max_candidates:
                return out
    return out


# --------------------------------------------------------------------------------------------------
# what a fix IS: the rung it sits on
# --------------------------------------------------------------------------------------------------

#: The ladder, measured rather than assumed. A rung names the smallest edit space that can express a
#: fix, which is also the space a learner must have before ANY amount of search can find it.
RUNGS = ("NO_CHANGE", "RUNG_LEAF", "RUNG_NODE", "RUNG_MULTI", "RUNG_SHAPE")
_LEAF_TYPES = (ast.Name, ast.Constant, ast.Attribute, ast.operator, ast.cmpop, ast.unaryop, ast.boolop)


def differing_positions(old_tree: ast.AST, new_tree: ast.AST) -> list[dict[str, Any]]:
    """The smallest subtrees that differ, each with the path that reaches it.

    Descent stops at the first divergence, so a fix to `binsearch(mid, end)` reports ONE position
    (the argument that changed) rather than every ancestor that also differs. That is what makes the
    rung a property of the fix instead of an artefact of how deep the walk went.
    """
    out: list[dict[str, Any]] = []

    def walk(a: ast.AST, b: ast.AST, path: tuple) -> None:
        if type(a) is not type(b):
            out.append({"path": path, "old": a, "new": b, "change": "SUBSTITUTE"})
            return
        if isinstance(a, (ast.Name, ast.Constant, ast.Attribute)) or isinstance(a, (ast.operator, ast.cmpop,
                                                                                    ast.unaryop, ast.boolop)):
            if _opaque(a) != _opaque(b):
                out.append({"path": path, "old": a, "new": b, "change": "SUBSTITUTE"})
            return
        for field in a._fields:
            if field in ("ctx", "type_comment", "kind", "conversion", "format_spec"):
                continue
            va, vb = getattr(a, field, None), getattr(b, field, None)
            if isinstance(va, list) and isinstance(vb, list):
                keys_a = [_fingerprint(x) if isinstance(x, ast.AST) else repr(x) for x in va]
                keys_b = [_fingerprint(x) if isinstance(x, ast.AST) else repr(x) for x in vb]
                if len(va) == len(vb):
                    for index, (left, right) in enumerate(zip(va, vb)):
                        if isinstance(left, ast.AST) and isinstance(right, ast.AST):
                            walk(left, right, path + ((field, index),))
                        elif left != right:
                            out.append({"path": path + ((field, index),), "old": left, "new": right,
                                        "change": "SUBSTITUTE"})
                    continue
                import difflib as _dl
                for tag, i1, i2, j1, j2 in _dl.SequenceMatcher(a=keys_a, b=keys_b, autojunk=False).get_opcodes():
                    if tag == "equal":
                        continue
                    if tag == "replace" and (i2 - i1) == (j2 - j1):
                        for index, (left, right) in enumerate(zip(va[i1:i2], vb[j1:j2])):
                            if isinstance(left, ast.AST) and isinstance(right, ast.AST):
                                walk(left, right, path + ((field, i1 + index),))
                            else:
                                out.append({"path": path + ((field, i1 + index),), "old": left,
                                            "new": right, "change": "SUBSTITUTE"})
                    else:
                        out.append({"path": path + ((field, "OPAQUE"),), "old": None,
                                    "new": "INSERT" if tag == "insert" else "DELETE",
                                    "change": "INSERT" if tag == "insert" else "DELETE"})
            elif isinstance(va, ast.AST) and isinstance(vb, ast.AST):
                walk(va, vb, path + ((field, None),))
            elif _leaf_name(va) != _leaf_name(vb):
                out.append({"path": path + ((field, None),), "old": va, "new": vb, "change": "SUBSTITUTE"})

    walk(old_tree, new_tree, ())
    return out


def classify_fix_shape(defective: str, repaired: str) -> dict[str, Any]:
    """Name the rung a demonstrated fix sits on, and what it would cost to express it."""
    positions = differing_positions(_strip_docstrings(_parse(defective, "DEFECTIVE")),
                                    _strip_docstrings(_parse(repaired, "REPAIRED")))
    if not positions:
        rung = "NO_CHANGE"
    elif any(p["change"] != "SUBSTITUTE" for p in positions):
        rung = "RUNG_SHAPE"
    elif len(positions) > 1:
        rung = "RUNG_MULTI"
    elif len(positions) == 1 and isinstance(positions[0]["old"], _LEAF_TYPES) and isinstance(
            positions[0]["new"], _LEAF_TYPES):
        rung = "RUNG_LEAF"
    else:
        rung = "RUNG_NODE"
    return {"rung": rung, "position_count": len(positions),
            "positions": [{"path": str(p["path"]), "change": p["change"],
                           "old_type": type(p["old"]).__name__ if isinstance(p["old"], ast.AST) else repr(p["old"]),
                           "new_type": type(p["new"]).__name__ if isinstance(p["new"], ast.AST) else repr(p["new"])}
                          for p in positions]}
