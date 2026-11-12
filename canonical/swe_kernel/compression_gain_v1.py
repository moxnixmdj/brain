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

#: A helper whose body looks a value up in a lifted table by a runtime key -- `table.get(key)`
#: with a None branch, or `table[key]` on a non-literal key. This is the world-model writer's
#: emitted shape (machinery identical across organs, one dict literal of per-organ data).
FAMILY_KEYED_TABLE = "keyed_table_lookup"

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

    def _is_literal(self, node: ast.AST) -> bool:
        """A literal, recursively: a constant, a signed constant, or a collection literal whose
        every element/key/value is itself a literal. The recursion is what lets a world-model's
        whole nested table dict lift as ONE parameter -- the same move the tuple rule makes for
        period blocks, generalised to every constant collection.

        `None`, `True` and `False` are EXCLUDED even though they parse as constants: they are
        singleton sentinels in control positions (`row is None`, `out['known'] = True`), and
        lifting them turns the machinery's own structure into a parameter -- measured: the
        world-model helper then renders with `if row is _p1:` and the abstraction stops being
        the shared machinery at all. Data tables so far carry numbers and strings; a table whose
        data genuinely contains booleans will refuse to lift wholesale, which is an honest
        refusal until a caller argues otherwise with a measured corpus."""
        if isinstance(node, ast.Constant):
            return node.value is not None and not isinstance(node.value, bool)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return isinstance(node.operand, ast.Constant) and not isinstance(
                node.operand.value, bool
            )
        if isinstance(node, ast.Tuple):
            return all(self._is_literal(e) for e in node.elts)
        if isinstance(node, (ast.List, ast.Set)):
            return all(self._is_literal(e) for e in node.elts)
        if isinstance(node, ast.Dict):
            return all(
                (k is None or self._is_literal(k)) and self._is_literal(v)
                for k, v in zip(node.keys, node.values)
            )
        return False

    def _take(self, src: str) -> ast.Name:
        name = f"_p{len(self.param_values)}"
        self.param_values.append(src)
        return ast.Name(id=name, ctx=ast.Load())

    def _visit_collection(self, node: ast.AST) -> ast.AST:
        if self._tuple_stack == 0 and node.elts and all(self._is_literal(e) for e in node.elts):
            return ast.copy_location(self._take(ast.unparse(node)), node)
        return self._descend(node)

    def _descend(self, node: ast.AST) -> ast.AST:
        self._tuple_stack += 1
        node = self.generic_visit(node)  # type: ignore[assignment]
        self._tuple_stack -= 1
        return node

    def visit_Tuple(self, node: ast.Tuple) -> ast.AST:
        if self._tuple_stack == 0 and node.elts and all(
            self._is_literal(e) for e in node.elts
        ):
            src = ast.unparse(node)
            return ast.copy_location(self._take(src), node)
        return self._descend(node)

    def visit_List(self, node: ast.List) -> ast.AST:
        return self._visit_collection(node)

    def visit_Set(self, node: ast.Set) -> ast.AST:
        return self._visit_collection(node)

    def visit_Dict(self, node: ast.Dict) -> ast.AST:
        if self._tuple_stack == 0 and node.values and all(
            (k is None or self._is_literal(k)) and self._is_literal(v)
            for k, v in zip(node.keys, node.values)
        ):
            return ast.copy_location(self._take(ast.unparse(node)), node)
        return self._descend(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        if self._tuple_stack == 0 and isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(
            node.operand, ast.Constant
        ):
            return ast.copy_location(self._take(ast.unparse(node)), node)
        return self.generic_visit(node)  # type: ignore[return-value]

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        # The same singleton exclusion as `_is_literal`, applied to bare constants: `None`,
        # `True` and `False` in control positions (`row is None`, `out['known'] = True`) are the
        # machinery's own structure. Lifting them measured out as self-defeating -- the
        # abstraction grew a parameter that every site passes as the same singleton, and the
        # schema dict shredded into per-key parameters.
        if node.value is None or isinstance(node.value, bool):
            return node
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
    # Indent EVERY line of each statement. Prefixing only the first line produced
    # `if row is None:` with its body at the same indentation -- a SyntaxError swallowed by the
    # try below and reported as "no shape". Multi-line statements have been liftable inputs
    # since the world-model lifter landed; only single-line corpora ever hid this.
    helper_src = (
        f"def {helper_name}({', '.join(param_names + arg_names)}):\n"
        + "\n".join(
            "\n".join(
                ("    " + ln) if ln.strip() else ln
                for ln in ast.unparse(ast.fix_missing_locations(s)).splitlines()
            )
            for s in new_body
        )
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
        # The lifted argument texts as a LIST. `call_args_src` cannot be split back apart --
        # a tuple parameter contains commas -- and a caller that reassembles call arguments from
        # a joined string will silently corrupt any constant that is itself a tuple.
        "param_values_src": list(lifter.param_values),
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
    # Keyed-table lookup: a `.get(...)` on a bare table name, with the None branch that
    # distinguishes a lookup-with-default from a plain indexing. Recognised from the call
    # structure, never from a name someone typed.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and any(isinstance(cmp, ast.Compare) for cmp in ast.walk(tree))
        ):
            return FAMILY_KEYED_TABLE
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
    probes: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Compress a corpus of solved programs into admissible abstractions.

    An abstraction is admissible only when ALL of these measured:
      * at least 2 corpus members share one lifted shape (1 site is a stored program, not one);
      * rewriting the members with the helper strictly reduces total `B_exec` description length
        (the repo's own metric, `executable_ast_bytes`) -- `gain_bytes > 0`, computed, never
        asserted;
      * every rewritten member reproduces its original program's outputs on the probe grid;
      * the probe grid DISCRIMINATES: the originals must produce at least two distinct outputs
        across the grid. A grid every input answers identically verifies nothing -- agreeing
        vacuously is how a forged abstraction would sail through, so a non-discriminating grid
        refuses admission instead of pretending to check. Domains that the default numeric grid
        cannot see (string-keyed tables, structural inputs) must be probed with caller-supplied
        `probes`; the bridge has no domain knowledge and correctly admits nothing it cannot
        probe.

    Everything else is returned under `refusals` with its reason, because a refusal that does not
    say why cannot be learned from.
    """
    grid = list(probes) if probes is not None else list(_PROBE_INPUTS)
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
        discriminating = False
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
            outputs = set()
            for x in grid:
                try:
                    a = orig_fn(x)
                    b = new_fn(x)
                except Exception:
                    preserved = False
                    break
                outputs.add(repr(a))
                if a != b:
                    preserved = False
                    break
            if not preserved:
                refusals.append({
                    "shape_key": g["shape_key"][:64],
                    "reason": "REWRITE_CHANGED_BEHAVIOUR_REFUSED",
                })
                break
            if len(outputs) >= 2:
                discriminating = True
        if not preserved:
            continue
        if not discriminating:
            # Every probe answered identically on the originals: the equality checks above were
            # vacuous, so nothing was verified. Admitting here would be passing a forged entry
            # through a gate that never looked.
            refusals.append({
                "shape_key": g["shape_key"][:64],
                "reason": "PROBE_GRID_NON_DISCRIMINATING",
                "sites": len(g["members"]),
                "grid_size": len(grid),
            })
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


def _library_abstractions(library: Any) -> list[dict[str, Any]]:
    """The library's admitted abstractions, re-derived into replayable form.

    A statement-function entry with a family is an admitted abstraction; its rendered helper IS
    the shared shape. The shape key is recomputed here from the rendered bytes rather than
    trusted from a stored field, because a library that cannot be re-read from its own persisted
    content is not content-addressed, it is rumoured.
    """
    out: list[dict[str, Any]] = []
    try:
        entries = list(library.concepts())
    except Exception:
        return out
    for e in entries:
        try:
            if not str(getattr(e, "family", "") or ""):
                continue
            if not getattr(e, "is_stmt_fn", False) or not str(getattr(e, "body_stmts", "") or "").strip():
                continue
            rendered = e.render_helper_def()
            lifted = lift_shape(rendered)
            if lifted is None:
                continue
            fn = _entry_fn(rendered, _helper_name_of(rendered))
            if fn is None:
                continue
            out.append({
                "concept_id": str(e.concept_id),
                "shape_key": lifted["shape_key"],
                "helper_src": rendered,
                "param_names": tuple(str(p) for p in (e.param_names or ())),
                "n_lifted": max(0, len(e.param_names or ()) - len(lifted["arg_names"])),
                "arity": int(getattr(e, "arity", 0) or 0),
            })
        except Exception:
            continue
    return out


def rewrite_source_with_abstractions(
    source: str,
    library: Any,
    *,
    probes: Sequence[Any] = _PROBE_INPUTS,
) -> dict[str, Any] | None:
    """Wake replay: rewrite a solved program to CALL an admitted abstraction.

    Round 24 closed the loop the round-23 note named: admission without replay is an append-only
    log. The wake pass in `concept_library_v1` handled single-expression concepts only and
    silently skipped statement-function abstractions -- which are the ONLY entries the library
    admits by compression, so the replay step could never fire on the library's real content.

    The rewrite is shape-matched and measured, never pattern-hoped:
      * the target function's lifted shape must EQUAL the abstraction's shape (argument names
        included -- unifying what cannot be verified is how a menu entry gets called a match);
      * the rewritten program is executed against the probe grid with the abstraction as its
        prelude -- the runtime condition the rewrite claims -- and ANY disagreement or exception
        refuses the whole rewrite (fail-closed, never partially rewritten);
      * the probe grid must DISCRIMINATE the original (>= 2 distinct outputs across the grid) --
        the same rule admission enforces. A string-keyed table probed with floats answers every
        input identically, so a vacuous grid refuses rather than shipping an unchecked rewrite;
        callers whose domain the numeric grid cannot see supply `probes`;
      * the rewrite must strictly reduce `description_bytes`. A replay that does not shrink the
        program is decoration, and decoration is not reuse.

    Returns a report dict on success, None on any refusal.
    """
    if library is None:
        return None
    abstractions = _library_abstractions(library)
    if not abstractions:
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not fns:
        return None
    concept_ids = {a["concept_id"] for a in abstractions}
    helpers: dict[str, str] = {}
    changes: list[dict[str, Any]] = []
    work = ast.parse(source)  # mutable copy
    for fn in [n for n in work.body if isinstance(n, ast.FunctionDef)]:
        if fn.name in concept_ids:
            continue
        lifted = lift_shape(source, fn.name)
        if lifted is None:
            continue
        match = next((a for a in abstractions if a["shape_key"] == lifted["shape_key"]), None)
        if match is None:
            continue
        if len(lifted["arg_names"]) != 1:
            continue  # the probe grid is single-argument; refusing beats pretending
        call_args = ", ".join(list(lifted["param_values_src"]) + list(lifted["arg_names"]))
        prelude = "\n".join(
            h for cid_, h in
            [(a["concept_id"], a["helper_src"]) for a in abstractions if a["concept_id"] == match["concept_id"]]
        )
        orig_fn_src = ast.get_source_segment(source, fn) or ast.unparse(fn)
        new_fn_src = f"def {fn.name}({', '.join(lifted['arg_names'])}):\n    return {match['concept_id']}({call_args})\n"
        orig_exec = _exec_fn(orig_fn_src, fn.name)
        new_exec = _exec_fn(new_fn_src, fn.name, prelude=prelude)
        if orig_exec is None or new_exec is None:
            return None
        seen_outputs: list[Any] = []
        for x in probes:
            try:
                a = orig_exec(x)
                b = new_exec(x)
            except Exception:
                return None
            if a != b:
                return None
            seen_outputs.append(a)
        # Discrimination, measured on the ORIGINAL: a grid the original answers identically
        # verified nothing, so the rewrite refuses rather than shipping unchecked. The equality
        # loop above stays fail-closed per probe; this is the vacuity gate.
        if len({repr(o) for o in seen_outputs}) < 2:
            return None
        before = description_bytes(orig_fn_src)
        after = description_bytes(new_fn_src)
        if after >= before:
            return None
        # The checked artifact IS the returned artifact: the function that lands is parsed from
        # the exact string whose behaviour and bytes were just measured. Round 24's first draft
        # built the AST separately with parameter NAME references instead of the inlined
        # constants, so it verified one program and returned another -- the same class of defect
        # as reporting a cost that omits the questions you asked.
        new_fn = ast.parse(new_fn_src).body[0]
        work.body[work.body.index(fn)] = ast.fix_missing_locations(new_fn)
        helpers[match["concept_id"]] = match["helper_src"]
        changes.append({
            "function": fn.name,
            "concept_id": match["concept_id"],
            "bytes_before": int(before),
            "bytes_after": int(after),
            "bytes_saved": int(before - after),
        })
    if not changes:
        return None
    try:
        final = ast.unparse(work) + "\n"
        # the full rewritten module must still compile with the helpers prepended
        exec(compile("\n".join(helpers.values()) + "\n" + final, "<replay>", "exec"), {"math": math})
    except Exception:
        return None
    return {
        "source": final,
        "helpers": helpers,
        "changes": changes,
        "bytes_before": sum(c["bytes_before"] for c in changes),
        "bytes_after": sum(c["bytes_after"] for c in changes),
    }
