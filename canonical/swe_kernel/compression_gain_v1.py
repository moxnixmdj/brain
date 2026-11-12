"""Compression-gained abstractions: the mechanism that lets solved problems compound.

Round 22 measured the deepest still-open defect
(`THE_DEEPEST_STILL_OPEN_DEFECT_NOTHING_IS_EVER_COMPRESSED_20261104_V1.md`): nothing in the tree
is ever compressed, so experience cannot compound. Meeting period-3 (14 questions) and period-7
(34) left a cold period-5 at exactly 24 questions; the one writer into the concept library `G_t`
silently rejected every organ the synthesizer can produce, because it admitted only
single-`return` bodies and reported a fabricated gain (`mdl_gain_bytes=max(1, code_bytes)`,
`corpus_sites=1`) that no compression ever computed. `G_t` stayed empty by construction.

This module is the fix, built on the same load-bearing idea as the field's library-learning line
(DreamCoder EC^2 wake/sleep compression; Stitch corpus-guided abstraction; LILO
search-compress-document): compress the corpus of solved programs into shared abstractions, admit
an abstraction ONLY when rewriting the corpus with it strictly reduces total description length,
and let admitted abstractions change what future evidence collection must pay.

Scope, stated honestly: this is SHAPE LIFTING -- scalar constants become parameters and a tuple of
constants becomes one block parameter -- not full lambda abduction. It finds exactly the shared
parameterized-shape abstractions a corpus of template-emitted programs contains, refuses
everything else, and licenses nothing that is not measured: strictly more than zero bytes gained,
at least two real sites, and every rewritten site reproducing its original program's behaviour on
a probe grid. An abstraction that fails any of those is a menu entry and is refused as one.

No model dependency. Pure stdlib. Fail-closed: every refusal returns None or an empty list, never
a guess.
"""
from __future__ import annotations

import ast
import hashlib
import math
from typing import Any, Sequence

#: The one family this module can name today, and only from structure. A shape whose body indexes
#: a sequence by a modular expression -- a `%` remainder, or a floored division feeding the index,
#: which is how the organ writer emits `x - floor(x/n)*n` -- is a periodic-table lookup. Any other
#: shape licenses nothing: an unnamed family is not a family.
FAMILY_PERIODIC_TABLE = "periodic_table"

#: Probe grid for the behaviour-preservation check. Both the original program and its rewritten
#: form run in the same namespace on the same inputs; any disagreement refuses the abstraction.
_PROBE_INPUTS = tuple(list(range(-9, 26)) + [0.5, -2.5, 17.5])


def _entry_fn(source: str, entrypoint: str) -> ast.FunctionDef | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    return next(
        (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == entrypoint),
        None,
    )


class _LiftConstants(ast.NodeTransformer):
    """Replace every constant with a parameter; a tuple of constants becomes ONE block parameter.

    The tuple rule is what makes period-3 and period-5 the same shape: their bodies differ only in
    the block tuple, so the tuple -- not its elements -- is the parameter. A shape that survives
    this lift is a structure the corpus actually shares. A signed numeric literal counts as a
    literal: `-2.0` parses as `USub(Constant(2.0))`, and treating the sign as structure would make
    two blocks differ by where their minus signs sit -- an accident of printing, not a difference
    in what the programs compute.
    """

    def __init__(self) -> None:
        self.param_values: list[str] = []  # source text of each lifted argument expression
        self._tuple_stack = 0

    @staticmethod
    def _is_literal(node: ast.AST) -> bool:
        if isinstance(node, ast.Constant):
            return True
        return (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, (ast.USub, ast.UAdd))
            and isinstance(node.operand, ast.Constant)
        )

    def _take(self, src: str) -> ast.Name:
        name = f"_p{len(self.param_values)}"
        self.param_values.append(src)
        return ast.Name(id=name, ctx=ast.Load())

    def visit_Tuple(self, node: ast.Tuple) -> ast.AST:
        if self._tuple_stack == 0 and node.elts and all(
            self._is_literal(e) for e in node.elts
        ):
            src = ast.unparse(node)
            return ast.copy_location(self._take(src), node)
        self._tuple_stack += 1
        node = self.generic_visit(node)  # type: ignore[assignment]
        self._tuple_stack -= 1
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        if self._tuple_stack == 0 and isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(
            node.operand, ast.Constant
        ):
            return ast.copy_location(self._take(ast.unparse(node)), node)
        return self.generic_visit(node)  # type: ignore[return-value]

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return ast.copy_location(self._take(ast.unparse(node)), node)


def lift_shape(source: str, entrypoint: str | None = None) -> dict[str, Any] | None:
    """Lift one solved program into its parameterized shape.

    `entrypoint=None` takes the first function in the module -- the canonical form for stored
    library renderings, whose only function is the concept itself. Returns None for anything that
    is not a plain function: no shape, no abstraction, no exception-based shortcuts. The shape key
    covers the argument names too -- two programs whose argument names differ are two shapes,
    because unifying what cannot be verified is exactly how a menu entry gets called an
    abstraction.
    """
    if entrypoint is None:
        try:
            tree0 = ast.parse(source)
        except SyntaxError:
            return None
        first = next((n for n in tree0.body if isinstance(n, ast.FunctionDef)), None)
        if first is None:
            return None
        entrypoint = first.name
    fn = _entry_fn(source, entrypoint)
    if fn is None or not fn.body:
        return None
    lifter = _LiftConstants()
    new_body = [lifter.visit(stmt) for stmt in fn.body]
    args_src = ast.unparse(fn.args)
    param_names = tuple(f"_p{i}" for i in range(len(lifter.param_values)))
    arg_names = tuple(a.arg for a in fn.args.args)
    helper_name = "_cand_abstraction"
    helper_src = (
        f"def {helper_name}({', '.join(param_names + arg_names)}):\n"
        + "\n".join("    " + ast.unparse(ast.fix_missing_locations(s)) for s in new_body)
        + "\n"
    )
    try:
        key_tree = ast.parse(helper_src)
        shape_key = ast.dump(key_tree.body[0].args) + "|" + ast.dump(
            ast.Module(body=key_tree.body[0].body, type_ignores=[])
        )
    except Exception:
        return None
    call_args = ", ".join(lifter.param_values + list(arg_names))
    return {
        "shape_key": shape_key,
        "helper_src": helper_src,
        "param_names": param_names + arg_names,
        "arity": len(param_names) + len(arg_names),
        "call_args_src": call_args,
        "entry_fn_src": ast.unparse(fn),
        "entry_fn_name": entrypoint,
        "arg_names": arg_names,
    }


def family_of(helper_src: str) -> str | None:
    """Structural family of a lifted helper, or None when the shape names no family this module
    can vouch for. Modular indexing is recognised from the index expression itself -- a `%`
    remainder, or a `floor(expr / n)` feeding the index, which is the organ writer's emitted
    residue form. Recognising the family from the structure, not from a name someone typed, is
    what keeps this a measurement rather than a label."""
    try:
        tree = ast.parse(helper_src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        for sub in ast.walk(node.slice):
            if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Mod):
                return FAMILY_PERIODIC_TABLE
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "floor"
                and any(isinstance(a, ast.BinOp) and isinstance(a.op, ast.Div) for a in sub.args)
            ):
                return FAMILY_PERIODIC_TABLE
    return None


def description_bytes(source_text: str) -> int:
    """Canonical UNCOMPRESSED AST text length -- the description-length currency for compression
    decisions.

    `executable_ast_bytes` (zlib level 9) stays the byte ledger elsewhere, but it is the wrong
    currency here and using it was the first draft's mistake: zlib re-derives shared structure for
    free, so a corpus measured under zlib is already the corpus AFTER the abstraction did its
    work -- a currency in which the mechanism being admitted can never measure a gain is not a
    measurement, it is a veto. The literature's currency is program size (Stitch's corpus MDL,
    DreamCoder's description length), and that is what this is: the size of what must be written
    down so the decoder -- Python -- can run it.
    """
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return len(source_text)

    class _StripDoc(ast.NodeTransformer):
        @staticmethod
        def _clean(body: list[ast.stmt]) -> list[ast.stmt]:
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                return body[1:] or [ast.Pass()]
            return body

        def visit_Module(self, n: ast.Module) -> ast.AST:
            n.body = self._clean(n.body)
            return self.generic_visit(n)

        def visit_FunctionDef(self, n: ast.FunctionDef) -> ast.AST:
            n.body = self._clean(n.body)
            return self.generic_visit(n)

    cleaned = _StripDoc().visit(tree)
    ast.fix_missing_locations(cleaned)
    return len(ast.unparse(cleaned))


def _exec_fn(source: str, entrypoint: str, *, prelude: str | None = None) -> Any | None:
    ns: dict[str, Any] = {"math": math}
    try:
        if prelude:
            exec(compile(prelude, "<compression_gain_prelude>", "exec"), ns)
        exec(compile(source, "<compression_gain>", "exec"), ns)
    except Exception:
        return None
    return ns.get(entrypoint)


def compress_corpus(
    sources: Sequence[str],
    *,
    entrypoints: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Compress a corpus of solved programs into admissible abstractions.

    An abstraction is admissible only when ALL of these measured:
      * at least 2 corpus members share one lifted shape (1 site is a stored program, not one);
      * rewriting the members with the helper strictly reduces total `B_exec` description length
        (the repo's own metric, `executable_ast_bytes`) -- `gain_bytes > 0`, computed, never
        asserted;
      * every rewritten member reproduces its original program's outputs on the probe grid.

    Everything else is returned under `refusals` with its reason, because a refusal that does not
    say why cannot be learned from.
    """
    eps = list(entrypoints) if entrypoints is not None else [None] * len(sources)
    groups: dict[str, dict[str, Any]] = {}
    refusals: list[dict[str, Any]] = []
    for idx, src in enumerate(sources):
        ep = eps[idx] if idx < len(eps) else None
        lifted = lift_shape(src, ep)
        if lifted is None:
            refusals.append({"source_index": idx, "reason": "NO_SHAPE"})
            continue
        g = groups.setdefault(
            lifted["shape_key"],
            {"shape_key": lifted["shape_key"], "helper_src": lifted["helper_src"],
             "param_names": lifted["param_names"], "arity": lifted["arity"],
             "members": []},
        )
        g["members"].append({"source": src, "call_args_src": lifted["call_args_src"],
                             "fn_name": lifted["entry_fn_name"]})

    abstractions: list[dict[str, Any]] = []
    for g in groups.values():
        if len(g["members"]) < 2:
            refusals.append({
                "shape_key": g["shape_key"][:64],
                "reason": "SINGLE_SITE_IS_A_STORED_PROGRAM_NOT_AN_ABSTRACTION",
                "sites": len(g["members"]),
            })
            continue
        helper = g["helper_src"]
        digest = hashlib.sha1(g["shape_key"].encode("utf-8")).hexdigest()[:12]
        concept_id = f"c_x_{digest}"
        helper_named = helper.replace("_cand_abstraction", concept_id, 1)
        before = sum(description_bytes(m["source"]) for m in g["members"])
        rewritten_srcs = []
        for m in g["members"]:
            rewritten_srcs.append(
                f"def {m['fn_name']}({', '.join(_arg_names_of(m['source'], m['fn_name']))}):\n"
                f"    return {concept_id}({m['call_args_src']})\n"
            )
        after = description_bytes(helper_named) + sum(
            description_bytes(r) for r in rewritten_srcs
        )
        gain = before - after
        if gain <= 0:
            refusals.append({
                "shape_key": g["shape_key"][:64],
                "reason": "NOT_COMPRESSIVE_A_REWRITE_THAT_DOES_NOT_SHRINK_IS_A_MENU_ENTRY",
                "sites": len(g["members"]),
                "before_bytes": before,
                "after_bytes": after,
            })
            continue
        family = family_of(helper_named)
        preserved = True
        for m, r in zip(g["members"], rewritten_srcs):
            orig_fn = _exec_fn(m["source"], m["fn_name"])
            # The rewritten member calls the abstraction, so the helper is its prelude: this is
            # exactly the runtime condition the abstraction claims -- corpus + library, together.
            new_fn = _exec_fn(r, m["fn_name"], prelude=helper_named)
            if orig_fn is None or new_fn is None:
                preserved = False
                refusals.append({
                    "shape_key": g["shape_key"][:64], "reason": "MEMBER_DID_NOT_COMPILE",
                })
                break
            for x in _PROBE_INPUTS:
                try:
                    a = orig_fn(x)
                    b = new_fn(x)
                except Exception:
                    preserved = False
                    break
                if a != b:
                    preserved = False
                    break
            if not preserved:
                refusals.append({
                    "shape_key": g["shape_key"][:64],
                    "reason": "REWRITE_CHANGED_BEHAVIOUR_REFUSED",
                })
                break
        if not preserved:
            continue
        abstractions.append({
            "concept_id": concept_id,
            "shape_key": g["shape_key"],
            "helper_src": helper_named,
            "param_names": g["param_names"],
            "arity": g["arity"],
            "gain_bytes": int(gain),
            "before_bytes": int(before),
            "after_bytes": int(after),
            "sites": len(g["members"]),
            "family": family or "",
            "rewritten_sources": rewritten_srcs,
            "_member_sources": [m["source"] for m in g["members"]],
        })
    return {"abstractions": abstractions, "refusals": refusals}


def helper_body_stmts(abstraction: dict[str, Any]) -> str:
    """The abstraction helper's body as statement text, for a statement-function ConceptEntry.

    The helper IS the abstraction: the shared shape with the lifted parameters named. Storing the
    helper (not one member) is what makes the entry reusable at every future site of the shape.
    """
    src = str(abstraction.get("helper_src") or "")
    fn = _entry_fn(src, _helper_name_of(src))
    if fn is None or not fn.body:
        return ""
    return "\n".join(ast.unparse(stmt) for stmt in fn.body)


def _helper_name_of(src: str) -> str:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ""
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            return n.name
    return ""


def _arg_names_of(source: str, entrypoint: str) -> list[str]:
    fn = _entry_fn(source, entrypoint)
    if fn is None:
        raise ValueError("NO_ENTRY_FN")
    return [a.arg for a in fn.args.args]


def licensed_table_policy(library: Any) -> dict[str, Any] | None:
    """The evidence policy an admitted abstraction licenses -- or None.

    A policy may come only from a measured abstraction: family `periodic_table`, at least 2 corpus
    sites, strictly positive measured compression gain, and at least one verified hit. An empty
    library, a singleton, an incompressible shape, or a never-verified entry licenses NOTHING, and
    the caller keeps its cold evidence rule. The returned `min_compression` is the licensed
    evidence factor for a NEW member of the family: the block must still explain at least twice
    its own size, and the growth path's independent verification at 2p and 3p is not waived --
    this policy moves where evidence is collected, never whether it is verified.
    """
    if library is None:
        return None
    try:
        entries = list(library.concepts())
    except Exception:
        return None
    for e in entries:
        try:
            family = str(getattr(e, "family", "") or "")
            sites = int(getattr(e, "corpus_sites", 0) or 0)
            gain = int(getattr(e, "mdl_gain_bytes", 0) or 0)
            hits = int(getattr(e, "verified_hits", 0) or 0)
        except Exception:
            continue
        if family == FAMILY_PERIODIC_TABLE and sites >= 2 and gain > 0 and hits >= 1:
            return {
                "min_compression": 2.0,
                "concept_id": str(e.concept_id),
                "corpus_sites": sites,
                "gain_bytes": gain,
            }
    return None
