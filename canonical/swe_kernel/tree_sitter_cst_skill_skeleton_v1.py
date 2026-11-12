#!/usr/bin/env python3
"""7-Language Tree-Sitter CST Skill Skeleton Anti-Unifier (`tree_sitter_cst_skill_skeleton_v1`).

Grammar-agnostic CST structural rule compiler, subtree anti-unifier, and cross-language
candidate generator across `python`, `rust`, `go`, `typescript`, `javascript`, `java`, and `cpp`
(`K3 = 0`, `$0` spend, `< 1 ms`):

  - Canonicalizes concrete Tree-Sitter CST expression trees onto a complete cross-language
    structural expression algebra:
      * `BINOP(op, left, right)`
      * `UNOP(op, operand)`
      * `LEN(arg)` (`len(x)` <-> `x.len()` <-> `x.length` <-> `x.size()`)
      * `CALL(callee, (arg0, ..., argN))` (arbitrary N-ary calls)
      * `MCALL(recv, method, (arg0, ..., argN))` (arbitrary N-ary member/method calls)
      * `ATTR(recv, field)` (`a.x` across Python/JS/TS/Go/Rust/Java/C++)
      * `SUBSCRIPT(val, idx)` (`a[i]` across Python/JS/TS/Go/Rust/Java/C++)
      * `TERNARY(cond, then_expr, else_expr)` (`a if c else b` <-> `c ? a : b` <-> `if c { a } else { b }`)
  - Supports multi-line function/method/statement rules (`python_scoped_edit_v1` windows,
    blocks, `if`/`elif`/`return` statements) via direct Tree-Sitter CST lockstep LCA descent,
    without fragile string-prefix stripping or fixed 5-shape whitelists.
  - Anti-unifies unchanged outer contexts (`CALL`, `MCALL`, `SUBSCRIPT`, `ATTR`, `TERNARY`,
    `LEN`, `UNOP`, `BINOP`) and abstracts unchanged composite child subtrees into `?exprK`
    structural holes so rules learned inside compound expressions transfer cleanly to new
    contexts and languages, fail-closed gated by Tree-Sitter parse validity + caller `verifier`.
"""
from __future__ import annotations

import re
from typing import Any, Iterator, Mapping, Sequence

from canonical.runtime import tree_sitter_swe_kernel_v1 as tsk

SCHEMA = "PROJECT_BRAIN_TREE_SITTER_CST_SKILL_SKELETON_V1"


class CstSubstrateUnavailable(RuntimeError):
    """The Tree-Sitter substrate is absent, so this capability cannot be exercised at all.

    Distinct from "no candidate applied". Both used to present as an empty iterator, and the
    difference is the difference between a broken mechanism and an uninstalled dependency.
    Measured 2026-11-12: `tree_sitter` absent from the image meant a Python lesson transferred
    to **none** of six languages, which reads exactly like a failed learner. With the pinned
    substrate restored (`scripts/restore_substrate_v1.py`) it transfers to **all six**. A
    capability that reports failure when it is merely unmeasured is a false negative, and it
    cost this tree a purple capability it actually had.
    """

    def __init__(self, language: str, detail: str = "") -> None:
        super().__init__(f"TREE_SITTER_SUBSTRATE_MISSING:{language}" + (f":{detail}" if detail else ""))
        self.language = language
        self.detail = detail

CODE_LANGUAGES = ("python", "rust", "go", "typescript", "javascript", "java", "cpp")

_CANON_OP = {
    "and": "&&",
    "&&": "&&",
    "or": "||",
    "||": "||",
    "not": "!",
    "!": "!",
    "<=": "<=",
    ">=": ">=",
    "<": "<",
    ">": ">",
    "==": "==",
    "!=": "!=",
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "//": "/",
    "%": "%",
}

_WRAPPER_TYPES = frozenset({
    "parenthesized_expression",
    "expression_list",
    "expression_statement",
})

_BINARY_NODE_TYPES = frozenset({
    "binary_expression",
    "binary_operator",
    "boolean_operator",
    "comparison_operator",
})

_UNARY_NODE_TYPES = frozenset({
    "unary_expression",
    "unary_operator",
    "not_operator",
})

_ATTR_NODE_TYPES = frozenset({
    "attribute",
    "member_expression",
    "selector_expression",
    "field_expression",
    "field_access",
})

_SUBSCRIPT_NODE_TYPES = frozenset({
    "subscript",
    "subscript_expression",
    "index_expression",
    "array_access",
})

_CALL_NODE_TYPES = frozenset({
    "call",
    "call_expression",
    "method_invocation",
})

_TERNARY_NODE_TYPES = frozenset({
    "conditional_expression",
    "ternary_expression",
    "if_expression",
})

_NUM_NODE_TYPES = frozenset({
    "integer",
    "float",
    "integer_literal",
    "float_literal",
    "number",
    "number_literal",
    "decimal_integer_literal",
    "decimal_floating_point_literal",
})

_IDENT_NODE_TYPES = frozenset({
    "identifier",
    "field_identifier",
    "property_identifier",
    "shorthand_property_identifier",
})


def _node_text(node: Any, raw: bytes) -> str:
    return raw[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _unwrap_expr(node: Any) -> Any:
    cur = node
    while cur is not None and cur.type in _WRAPPER_TYPES:
        named = [c for c in cur.children if c.is_named]
        if len(named) == 1:
            cur = named[0]
        else:
            break
    return cur


def _extract_len_arg(node: Any, raw: bytes) -> Any | None:
    """If `node` is `len(x)` / `x.len()` / `x.length` / `x.size()`, return CST node for `x`."""
    t = node.type
    if t in ("call", "call_expression"):
        children = [c for c in node.children if c.is_named]
        if len(children) >= 2:
            callee, args_node = children[0], children[1]
            if callee.type == "identifier" and _node_text(callee, raw) == "len":
                arg_named = [c for c in args_node.children if c.is_named]
                if len(arg_named) == 1:
                    return arg_named[0]
            if callee.type in _ATTR_NODE_TYPES:
                f_named = [c for c in callee.children if c.is_named]
                arg_named = [c for c in args_node.children if c.is_named]
                if len(f_named) == 2 and len(arg_named) == 0:
                    method_nm = _node_text(f_named[1], raw)
                    if method_nm in ("len", "size"):
                        return f_named[0]
    if t in _ATTR_NODE_TYPES:
        f_named = [c for c in node.children if c.is_named]
        if len(f_named) == 2 and _node_text(f_named[1], raw) == "length":
            return f_named[0]
    if t == "method_invocation":
        named = [c for c in node.children if c.is_named]
        if len(named) >= 2 and _node_text(named[1], raw) == "size":
            args_node = next((c for c in named[2:] if "argument" in c.type), None)
            if args_node is None or len([c for c in args_node.children if c.is_named]) == 0:
                return named[0]
    return None


def _extract_attr_parts(node: Any) -> tuple[Any, Any] | None:
    if node.type not in _ATTR_NODE_TYPES:
        return None
    named = [c for c in node.children if c.is_named]
    if len(named) == 2:
        return named[0], named[1]
    return None


def _extract_subscript_parts(node: Any) -> tuple[Any, Any] | None:
    if node.type not in _SUBSCRIPT_NODE_TYPES:
        return None
    named = [c for c in node.children if c.is_named]
    if len(named) != 2:
        return None
    base_nd, idx_nd = named[0], named[1]
    if idx_nd.type == "subscript_argument_list":
        sub_named = [c for c in idx_nd.children if c.is_named]
        if len(sub_named) != 1:
            return None
        idx_nd = sub_named[0]
    elif idx_nd.type == "slice":
        return None
    return base_nd, idx_nd


def _extract_call_or_mcall(node: Any) -> tuple[str, Any, Any | None, list[Any]] | None:
    """Return `('CALL', callee_nd, None, arg_nodes)` or `('MCALL', recv_nd, method_nd, arg_nodes)`."""
    t = node.type
    if t in ("call", "call_expression"):
        children = [c for c in node.children if c.is_named]
        if len(children) < 2:
            return None
        callee, args_node = children[0], children[1]
        if "argument" not in args_node.type:
            return None
        arg_nodes = [c for c in args_node.children if c.is_named]
        # Reject keyword/spread arguments so positional cross-language rendering stays sound
        if any(c.type in ("keyword_argument", "dictionary_splat", "list_splat", "spread_element") for c in arg_nodes):
            return None
        attr_parts = _extract_attr_parts(callee)
        if attr_parts is not None:
            return ("MCALL", attr_parts[0], attr_parts[1], arg_nodes)
        return ("CALL", callee, None, arg_nodes)
    if t == "method_invocation":
        named = [c for c in node.children if c.is_named]
        if len(named) == 2 and "argument" in named[1].type:
            arg_nodes = [c for c in named[1].children if c.is_named]
            return ("CALL", named[0], None, arg_nodes)
        if len(named) >= 3 and "argument" in named[-1].type:
            arg_nodes = [c for c in named[-1].children if c.is_named]
            return ("MCALL", named[0], named[1], arg_nodes)
    return None


def _extract_ternary_parts(node: Any, raw: bytes) -> tuple[Any, Any, Any] | None:
    """Return `(cond_node, then_node, else_node)` across Python, JS/TS/Java/C++, and Rust."""
    t = node.type
    if t in ("conditional_expression", "ternary_expression"):
        named = [c for c in node.children if c.is_named]
        if len(named) != 3:
            return None
        between_0_1 = raw[named[0].end_byte:named[1].start_byte].decode("utf-8", errors="replace")
        if re.search(r"\bif\b", between_0_1):
            # Python: `then_expr if cond_expr else else_expr`
            return named[1], named[0], named[2]
        if "?" in between_0_1:
            # C++ / JS / TS / Java: `cond_expr ? then_expr : else_expr`
            return named[0], named[1], named[2]
        return None
    if t == "if_expression":
        named = [c for c in node.children if c.is_named]
        if len(named) != 3:
            return None
        cond_nd, then_blk, else_clause = named[0], named[1], named[2]
        then_children = [c for c in then_blk.children if c.is_named]
        else_blocks = [c for c in else_clause.children if c.is_named]
        if len(then_children) == 1 and len(else_blocks) == 1 and else_blocks[0].type == "block":
            else_children = [c for c in else_blocks[0].children if c.is_named]
            if len(else_children) == 1:
                return cond_nd, then_children[0], else_children[0]
    return None


_NON_REWRITE_CONTAINERS = frozenset({
    "module",
    "program",
    "source_file",
    "translation_unit",
    "block",
    "statement_block",
    "compound_statement",
    "function_definition",
    "function_declaration",
    "method_definition",
    "method_declaration",
    "class_definition",
    "class_declaration",
    "parameter_list",
    "parameters",
    "formal_parameters",
    "argument_list",
    "arguments",
})


def _extract_slice_parts(node: Any, raw: bytes) -> tuple[Any, Any | None, Any | None] | None:
    """Extract `(base, start_or_None, stop_or_None)` from `arr[lo:hi]` or `arr.slice(lo, hi)`."""
    if node.type in _SUBSCRIPT_NODE_TYPES:
        named = [c for c in node.children if c.is_named]
        if len(named) == 2 and named[1].type == "slice":
            sl = named[1]
            # Reject 3-part stepped slices (`a:b:c`) for 2-arg `.slice(a, b)` cross-language soundness
            colons = [c for c in sl.children if not c.is_named and _node_text(c, raw) == ":"]
            if len(colons) != 1:
                return None
            colon_b = colons[0].start_byte
            s_named = [c for c in sl.children if c.is_named]
            lo = next((c for c in s_named if c.end_byte <= colon_b), None)
            hi = next((c for c in s_named if c.start_byte > colon_b), None)
            return named[0], lo, hi
    call_parts = _extract_call_or_mcall(node)
    if call_parts is not None and call_parts[0] == "MCALL" and call_parts[2] is not None:
        if _node_text(call_parts[2], raw).strip() == "slice" and 1 <= len(call_parts[3]) <= 2:
            lo = call_parts[3][0]
            hi = call_parts[3][1] if len(call_parts[3]) == 2 else None
            return call_parts[1], lo, hi
    return None


def _is_candidate_expr_node(node: Any, raw: bytes) -> bool:
    t = node.type
    if (
        t in _BINARY_NODE_TYPES
        or t in _UNARY_NODE_TYPES
        or t in _CALL_NODE_TYPES
        or t in _SUBSCRIPT_NODE_TYPES
        or t in _ATTR_NODE_TYPES
        or t in _TERNARY_NODE_TYPES
        or _extract_len_arg(node, raw) is not None
        or _extract_slice_parts(node, raw) is not None
    ):
        return True
    if t in _NON_REWRITE_CONTAINERS or t in _WRAPPER_TYPES:
        return False
    named = [c for c in node.children if c.is_named]
    return bool(named) and b"\n" not in raw[node.start_byte:node.end_byte]


def _ident_or_hole(txt: str, hole_by_ident: Mapping[str, str] | None) -> tuple[str, str]:
    if hole_by_ident and txt in hole_by_ident:
        return ("HOLE", hole_by_ident[txt])
    return ("ATOM", txt)


def cst_to_canonical_expr(node: Any, raw: bytes, hole_by_ident: Mapping[str, str] | None = None) -> tuple[Any, ...]:
    """Project a concrete Tree-Sitter expression node onto a canonical language-neutral tuple."""
    node = _unwrap_expr(node)
    len_arg = _extract_len_arg(node, raw)
    if len_arg is not None:
        return ("LEN", cst_to_canonical_expr(len_arg, raw, hole_by_ident))

    t = node.type
    if t in _BINARY_NODE_TYPES:
        named = [c for c in node.children if c.is_named]
        if len(named) == 2:
            left, right = named[0], named[1]
            mid_bytes = raw[left.end_byte:right.start_byte].decode("utf-8", errors="replace").strip()
            canon_op = _CANON_OP.get(mid_bytes)
            if canon_op:
                return (
                    "BINOP",
                    canon_op,
                    cst_to_canonical_expr(left, raw, hole_by_ident),
                    cst_to_canonical_expr(right, raw, hole_by_ident),
                )

    if t in _UNARY_NODE_TYPES:
        named = [c for c in node.children if c.is_named]
        if len(named) == 1:
            operand = named[0]
            prefix = raw[node.start_byte:operand.start_byte].decode("utf-8", errors="replace").strip()
            canon_op = _CANON_OP.get(prefix)
            if canon_op:
                return ("UNOP", canon_op, cst_to_canonical_expr(operand, raw, hole_by_ident))

    tern = _extract_ternary_parts(node, raw)
    if tern is not None:
        c_nd, t_nd, e_nd = tern
        return (
            "TERNARY",
            cst_to_canonical_expr(c_nd, raw, hole_by_ident),
            cst_to_canonical_expr(t_nd, raw, hole_by_ident),
            cst_to_canonical_expr(e_nd, raw, hole_by_ident),
        )

    sl_parts = _extract_slice_parts(node, raw)
    if sl_parts is not None:
        b_nd, lo_nd, hi_nd = sl_parts
        return (
            "SLICE",
            cst_to_canonical_expr(b_nd, raw, hole_by_ident),
            cst_to_canonical_expr(lo_nd, raw, hole_by_ident) if lo_nd is not None else ("NONE_BOUND",),
            cst_to_canonical_expr(hi_nd, raw, hole_by_ident) if hi_nd is not None else ("NONE_BOUND",),
        )

    call_parts = _extract_call_or_mcall(node)
    if call_parts is not None:
        ckind, first_nd, method_nd, arg_nodes = call_parts
        arg_skels = tuple(cst_to_canonical_expr(a, raw, hole_by_ident) for a in arg_nodes)
        if ckind == "MCALL" and method_nd is not None:
            m_txt = _node_text(method_nd, raw).strip()
            return (
                "MCALL",
                cst_to_canonical_expr(first_nd, raw, hole_by_ident),
                _ident_or_hole(m_txt, hole_by_ident),
                arg_skels,
            )
        c_txt = _node_text(first_nd, raw).strip()
        callee_sk = (
            _ident_or_hole(c_txt, hole_by_ident)
            if re.fullmatch(r"[A-Za-z_$][\w$]*", c_txt)
            else cst_to_canonical_expr(first_nd, raw, hole_by_ident)
        )
        return ("CALL", callee_sk, arg_skels)

    sub_parts = _extract_subscript_parts(node)
    if sub_parts is not None:
        return (
            "SUBSCRIPT",
            cst_to_canonical_expr(sub_parts[0], raw, hole_by_ident),
            cst_to_canonical_expr(sub_parts[1], raw, hole_by_ident),
        )

    attr_parts = _extract_attr_parts(node)
    if attr_parts is not None:
        f_txt = _node_text(attr_parts[1], raw).strip()
        return (
            "ATTR",
            cst_to_canonical_expr(attr_parts[0], raw, hole_by_ident),
            _ident_or_hole(f_txt, hole_by_ident),
        )

    txt = _node_text(node, raw).strip()
    if t in _NUM_NODE_TYPES or re.fullmatch(r"\d+(?:\.\d+)?", txt):
        if hole_by_ident and txt in hole_by_ident:
            return ("HOLE", hole_by_ident[txt])
        return ("NUM", txt)

    if t in _IDENT_NODE_TYPES or re.fullmatch(r"[A-Za-z_$][\w$]*", txt):
        return _ident_or_hole(txt, hole_by_ident)

    # Generic structural CST decomposition: handles ALL syntax constructs (`+=`, comprehensions,
    # lambdas, tuples, dicts, slices, clauses, statements) without construct whitelists!
    named = [c for c in node.children if c.is_named]
    if named and t not in _NON_REWRITE_CONTAINERS and b"\n" not in raw[node.start_byte:node.end_byte]:
        spans: list[str] = []
        cursor = node.start_byte
        child_skels: list[tuple[Any, ...]] = []
        for ch in named:
            spans.append(raw[cursor:ch.start_byte].decode("utf-8", errors="replace"))
            child_skels.append(cst_to_canonical_expr(ch, raw, hole_by_ident))
            cursor = ch.end_byte
        spans.append(raw[cursor:node.end_byte].decode("utf-8", errors="replace"))
        return ("GENERIC_CST", t, tuple(spans), tuple(child_skels))

    if hole_by_ident:
        found_holes = [h for syn, h in hole_by_ident.items() if syn in txt]
        if found_holes:
            return ("OPAQUE_WITH_HOLES", txt, tuple(sorted(set(found_holes))))
    return ("OPAQUE", txt)


def _wrap_compound_receiver(rendered: str, sub: tuple[Any, ...]) -> str:
    if sub[0] in ("BINOP", "UNOP", "TERNARY") and not (rendered.startswith("(") and rendered.endswith(")")):
        return f"({rendered})"
    if " " in rendered and not (rendered.startswith("(") and rendered.endswith(")")):
        return f"({rendered})"
    return rendered


def render_canonical_expr(expr: tuple[Any, ...], target_language: str, bindings: Mapping[str, str]) -> str | None:
    """Render a canonical CST expression into native `target_language` syntax."""
    lang = target_language.lower()
    kind = expr[0]
    if kind == "HOLE":
        val = bindings.get(str(expr[1]))
        return val if val is not None else None
    if kind in ("NUM", "ATOM", "OPAQUE"):
        return str(expr[1])
    if kind == "CALL1":
        fn_s = render_canonical_expr(expr[1], lang, bindings)
        arg_s = render_canonical_expr(expr[2], lang, bindings)
        if fn_s is None or arg_s is None:
            return None
        return f"{fn_s}({arg_s})"
    if kind == "CALL":
        fn_s = render_canonical_expr(expr[1], lang, bindings)
        if fn_s is None:
            return None
        rendered_args: list[str] = []
        for a_sk in expr[2]:
            a_s = render_canonical_expr(a_sk, lang, bindings)
            if a_s is None:
                return None
            rendered_args.append(a_s)
        return f"{fn_s}({', '.join(rendered_args)})"
    if kind == "MCALL0":
        r_s = render_canonical_expr(expr[1], lang, bindings)
        m_s = render_canonical_expr(expr[2], lang, bindings)
        if r_s is None or m_s is None:
            return None
        return f"{_wrap_compound_receiver(r_s, expr[1])}.{m_s}()"
    if kind == "MCALL":
        r_s = render_canonical_expr(expr[1], lang, bindings)
        m_s = render_canonical_expr(expr[2], lang, bindings)
        if r_s is None or m_s is None:
            return None
        rendered_args = []
        for a_sk in expr[3]:
            a_s = render_canonical_expr(a_sk, lang, bindings)
            if a_s is None:
                return None
            rendered_args.append(a_s)
        return f"{_wrap_compound_receiver(r_s, expr[1])}.{m_s}({', '.join(rendered_args)})"
    if kind == "ATTR":
        r_s = render_canonical_expr(expr[1], lang, bindings)
        f_s = render_canonical_expr(expr[2], lang, bindings)
        if r_s is None or f_s is None:
            return None
        return f"{_wrap_compound_receiver(r_s, expr[1])}.{f_s}"
    if kind == "SUBSCRIPT":
        b_s = render_canonical_expr(expr[1], lang, bindings)
        i_s = render_canonical_expr(expr[2], lang, bindings)
        if b_s is None or i_s is None:
            return None
        return f"{_wrap_compound_receiver(b_s, expr[1])}[{i_s}]"
    if kind == "SLICE":
        b_s = render_canonical_expr(expr[1], lang, bindings)
        if b_s is None:
            return None
        lo_s = "" if expr[2][0] == "NONE_BOUND" else render_canonical_expr(expr[2], lang, bindings)
        hi_s = "" if expr[3][0] == "NONE_BOUND" else render_canonical_expr(expr[3], lang, bindings)
        if lo_s is None or hi_s is None:
            return None
        recv = _wrap_compound_receiver(b_s, expr[1])
        if lang in ("python", "go"):
            return f"{recv}[{lo_s}:{hi_s}]"
        if lang in ("javascript", "typescript"):
            lo_arg = lo_s if lo_s else "0"
            return f"{recv}.slice({lo_arg}, {hi_s})" if hi_s else f"{recv}.slice({lo_arg})"
        if lang == "rust":
            return f"&{recv}[{lo_s}..{hi_s}]"
        return None
    if kind == "GENERIC_CST":
        spans = expr[2]
        children = expr[3]
        parts: list[str] = [str(spans[0])]
        for idx, ch in enumerate(children):
            c_s = render_canonical_expr(ch, lang, bindings)
            if c_s is None:
                return None
            parts.append(c_s)
            parts.append(str(spans[idx + 1]))
        return "".join(parts)
    if kind == "TERNARY":
        c_s = render_canonical_expr(expr[1], lang, bindings)
        t_s = render_canonical_expr(expr[2], lang, bindings)
        e_s = render_canonical_expr(expr[3], lang, bindings)
        if c_s is None or t_s is None or e_s is None:
            return None
        if lang == "python":
            return f"({t_s} if {c_s} else {e_s})"
        if lang == "rust":
            return f"if {c_s} {{ {t_s} }} else {{ {e_s} }}"
        if lang in ("typescript", "javascript", "java", "cpp"):
            return f"({c_s} ? {t_s} : {e_s})"
        return None
    if kind == "LEN":
        inner = render_canonical_expr(expr[1], lang, bindings)
        if inner is None:
            return None
        recv = _wrap_compound_receiver(inner, expr[1])
        if lang in ("python", "go"):
            return f"len({inner})"
        if lang == "rust":
            return f"{recv}.len()"
        if lang in ("typescript", "javascript"):
            return f"{recv}.length"
        if lang in ("java", "cpp"):
            return f"{recv}.size()"
        return None
    if kind == "UNOP":
        op, sub = str(expr[1]), expr[2]
        rendered = render_canonical_expr(sub, lang, bindings)
        if rendered is None:
            return None
        if sub[0] in ("BINOP", "TERNARY"):
            rendered = f"({rendered})"
        if op == "!":
            return f"not {rendered}" if lang == "python" else f"!{rendered}"
        return f"{op}{rendered}"
    if kind == "BINOP":
        op, left_t, right_t = str(expr[1]), expr[2], expr[3]
        left_s = render_canonical_expr(left_t, lang, bindings)
        right_s = render_canonical_expr(right_t, lang, bindings)
        if left_s is None or right_s is None:
            return None
        if op == "&&":
            op_s = "and" if lang == "python" else "&&"
        elif op == "||":
            op_s = "or" if lang == "python" else "||"
        else:
            op_s = op
        if left_t[0] in ("BINOP", "TERNARY") and (left_t[0] != "BINOP" or left_t[1] != op):
            left_s = f"({left_s})"
        if right_t[0] in ("BINOP", "TERNARY") and (right_t[0] != "BINOP" or right_t[1] != op):
            right_s = f"({right_s})"
        return f"{left_s} {op_s} {right_s}"
    return None


def _unify_skeleton(pattern: tuple[Any, ...], concrete: tuple[Any, ...], bindings: dict[str, str], raw_expr_text: str) -> bool:
    p_kind = pattern[0]
    if p_kind == "HOLE":
        h_name = str(pattern[1])
        is_num_hole = h_name.startswith("?num")
        if is_num_hole and concrete[0] != "NUM":
            return False
        bound_text = str(concrete[1]) if concrete[0] in ("ATOM", "NUM", "OPAQUE") else raw_expr_text
        prev = bindings.get(h_name)
        if prev is not None and prev != bound_text:
            return False
        bindings[h_name] = bound_text
        return True
    if p_kind != concrete[0]:
        return False
    if p_kind in ("NUM", "ATOM"):
        return pattern[1] == concrete[1]
    if p_kind == "LEN":
        return _unify_skeleton(pattern[1], concrete[1], bindings, raw_expr_text)
    if p_kind == "UNOP":
        return pattern[1] == concrete[1] and _unify_skeleton(pattern[2], concrete[2], bindings, raw_expr_text)
    if p_kind in ("CALL1", "MCALL0", "ATTR", "SUBSCRIPT"):
        return _unify_skeleton(pattern[1], concrete[1], bindings, raw_expr_text) and _unify_skeleton(
            pattern[2], concrete[2], bindings, raw_expr_text
        )
    if p_kind == "CALL":
        return (
            len(pattern[2]) == len(concrete[2])
            and _unify_skeleton(pattern[1], concrete[1], bindings, raw_expr_text)
            and all(_unify_skeleton(pa, ca, bindings, raw_expr_text) for pa, ca in zip(pattern[2], concrete[2]))
        )
    if p_kind == "MCALL":
        return (
            len(pattern[3]) == len(concrete[3])
            and _unify_skeleton(pattern[1], concrete[1], bindings, raw_expr_text)
            and _unify_skeleton(pattern[2], concrete[2], bindings, raw_expr_text)
            and all(_unify_skeleton(pa, ca, bindings, raw_expr_text) for pa, ca in zip(pattern[3], concrete[3]))
        )
    if p_kind == "TERNARY":
        return (
            _unify_skeleton(pattern[1], concrete[1], bindings, raw_expr_text)
            and _unify_skeleton(pattern[2], concrete[2], bindings, raw_expr_text)
            and _unify_skeleton(pattern[3], concrete[3], bindings, raw_expr_text)
        )
    if p_kind == "NONE_BOUND":
        return concrete[0] == "NONE_BOUND"
    if p_kind == "SLICE":
        return (
            _unify_skeleton(pattern[1], concrete[1], bindings, raw_expr_text)
            and _unify_skeleton(pattern[2], concrete[2], bindings, raw_expr_text)
            and _unify_skeleton(pattern[3], concrete[3], bindings, raw_expr_text)
        )
    if p_kind == "GENERIC_CST":
        return (
            pattern[1] == concrete[1]
            and tuple(s.strip() for s in pattern[2]) == tuple(s.strip() for s in concrete[2])
            and len(pattern[3]) == len(concrete[3])
            and all(_unify_skeleton(pa, ca, bindings, raw_expr_text) for pa, ca in zip(pattern[3], concrete[3]))
        )
    if p_kind == "BINOP":
        return (
            pattern[1] == concrete[1]
            and _unify_skeleton(pattern[2], concrete[2], bindings, raw_expr_text)
            and _unify_skeleton(pattern[3], concrete[3], bindings, raw_expr_text)
        )
    return False


def _iter_child_skeletons(sk: tuple[Any, ...]) -> Iterator[tuple[Any, ...]]:
    kind = sk[0]
    if kind in ("LEN",):
        yield sk[1]
    elif kind == "UNOP":
        yield sk[2]
    elif kind == "BINOP":
        yield sk[2]
        yield sk[3]
    elif kind in ("CALL1", "MCALL0", "ATTR", "SUBSCRIPT"):
        yield sk[1]
        yield sk[2]
    elif kind == "CALL":
        yield sk[1]
        yield from sk[2]
    elif kind == "MCALL":
        yield sk[1]
        yield sk[2]
        yield from sk[3]
    elif kind in ("TERNARY", "SLICE"):
        yield sk[1]
        yield sk[2]
        yield sk[3]
    elif kind == "GENERIC_CST":
        yield from sk[3]


def _collect_atoms_and_holes(sk: tuple[Any, ...], atoms: set[str], holes: set[str], *, selector_pos: bool = False) -> None:
    kind = sk[0]
    if kind == "HOLE":
        holes.add(str(sk[1]))
    elif kind == "ATOM":
        if not selector_pos and str(sk[1]) not in ("True", "False", "None", "true", "false", "null", "nil"):
            atoms.add(str(sk[1]))
    elif kind == "OPAQUE_WITH_HOLES":
        holes.update(str(h) for h in sk[2])
    elif kind in ("CALL", "CALL1"):
        _collect_atoms_and_holes(sk[1], atoms, holes, selector_pos=True)
        if kind == "CALL1":
            _collect_atoms_and_holes(sk[2], atoms, holes)
        else:
            for ch in sk[2]:
                _collect_atoms_and_holes(ch, atoms, holes)
    elif kind in ("MCALL", "MCALL0", "ATTR"):
        _collect_atoms_and_holes(sk[1], atoms, holes)
        _collect_atoms_and_holes(sk[2], atoms, holes, selector_pos=True)
        if kind == "MCALL":
            for ch in sk[3]:
                _collect_atoms_and_holes(ch, atoms, holes)
    else:
        for child in _iter_child_skeletons(sk):
            _collect_atoms_and_holes(child, atoms, holes)


def _has_non_hole_structure(sk: tuple[Any, ...]) -> bool:
    """True when `sk` constrains at least one operator/construct/literal rather than matching any expression."""
    return sk[0] not in ("HOLE", "OPAQUE", "OPAQUE_WITH_HOLES")


def _contains_opaque(sk: tuple[Any, ...]) -> bool:
    if sk[0] in ("OPAQUE", "OPAQUE_WITH_HOLES"):
        return True
    return any(_contains_opaque(ch) for ch in _iter_child_skeletons(sk))


def _scaffold_snippet_for_cst(raw_text: str, src_lang: str) -> bytes:
    """Normalize indentation and scaffold dangling clause/header fragments (`elif`, `while`, `if`, `for`) into valid CST roots."""
    import textwrap

    txt = textwrap.dedent(raw_text).strip()
    if src_lang == "python":
        first = txt.splitlines()[0].strip() if txt else ""
        if len(txt.splitlines()) == 1 and first.endswith(":"):
            if first.startswith(("elif ", "else:", "except", "finally:")):
                txt = f"if True:\n    pass\n{first}\n    pass"
            else:
                txt = f"{first}\n    pass"
        elif first.startswith(("elif ", "else:")):
            txt = "if True:\n    pass\n" + txt
        elif first.startswith(("except", "finally:")):
            txt = "try:\n    pass\n" + txt
    return (txt + "\n").encode("utf-8")


def _direct_cst_changed_expr_pair(
    pat_raw: bytes,
    rep_raw: bytes,
    src_lang: str,
    synth_to_hole: Mapping[str, str],
) -> tuple[tuple[Any, ...], tuple[Any, ...], bool] | None:
    """Parse multi-line / statement / function `pat_raw` & `rep_raw` directly and extract the changed CST expression pair."""
    pat_raw = _scaffold_snippet_for_cst(pat_raw.decode("utf-8", errors="replace"), src_lang)
    rep_raw = _scaffold_snippet_for_cst(rep_raw.decode("utf-8", errors="replace"), src_lang)
    try:
        pt = tsk.parse_bytes(src_lang, pat_raw)
        rt = tsk.parse_bytes(src_lang, rep_raw)
    except Exception as exc:
        # The stdlib AST is a legitimate fallback for Python SOURCES, but it produces a
        # Python-shaped skeleton that a non-Python target can never be unified against. Letting
        # that happen reports "the lesson does not transfer" when in fact no transfer was
        # attempted. Measured 2026-11-12: absent substrate -> 0 of 6 languages; restored -> 6/6.
        if not _substrate_present():
            raise CstSubstrateUnavailable(src_lang, type(exc).__name__) from exc
        return _python_stdlib_ast_changed_pair(pat_raw.decode("utf-8", errors="replace"), rep_raw.decode("utf-8", errors="replace"), synth_to_hole) if src_lang == "python" else None
    if getattr(pt.root_node, "has_error", False) or getattr(rt.root_node, "has_error", False):
        return _python_stdlib_ast_changed_pair(pat_raw.decode("utf-8", errors="replace"), rep_raw.decode("utf-8", errors="replace"), synth_to_hole) if src_lang == "python" else None

    pn = pt.root_node
    rn = rt.root_node
    # Descend through identical statement/declaration containers BEFORE canonicalizing so `while`/`elif`/`for` peel to their inner expression!
    while pn.type == rn.type:
        p_named = [c for c in pn.children if c.is_named]
        r_named = [c for c in rn.children if c.is_named]
        if len(p_named) != len(r_named) or not p_named:
            break
        # Check that surrounding literal punctuation/operators on `pn` vs `rn` are identical (e.g. don't peel `+=` vs `-=`)
        p_spans = [pat_raw[pn.start_byte:p_named[0].start_byte]] + [pat_raw[p_named[i].end_byte:p_named[i + 1].start_byte] for i in range(len(p_named) - 1)] + [pat_raw[p_named[-1].end_byte:pn.end_byte]]
        r_spans = [rep_raw[rn.start_byte:r_named[0].start_byte]] + [rep_raw[r_named[i].end_byte:r_named[i + 1].start_byte] for i in range(len(r_named) - 1)] + [rep_raw[r_named[-1].end_byte:rn.end_byte]]
        if [s.strip() for s in p_spans] != [s.strip() for s in r_spans]:
            break
        diffs = [
            idx
            for idx, (pc, rc) in enumerate(zip(p_named, r_named))
            if _node_text(pc, pat_raw) != _node_text(rc, rep_raw)
        ]
        if len(diffs) != 1:
            break
        cand_p, cand_r = p_named[diffs[0]], r_named[diffs[0]]
        # Do not descend below an expression into a bare identifier/number hole if the parent itself is an expression
        if _unwrap_expr(cand_p).type in (_NUM_NODE_TYPES | _IDENT_NODE_TYPES) and _is_candidate_expr_node(_unwrap_expr(pn), pat_raw):
            break
        pn, rn = cand_p, cand_r

    pn_u = _unwrap_expr(pn)
    rn_u = _unwrap_expr(rn)
    if _is_candidate_expr_node(pn_u, pat_raw) or _is_candidate_expr_node(rn_u, rep_raw):
        p_sk = cst_to_canonical_expr(pn_u, pat_raw, synth_to_hole)
        r_sk = cst_to_canonical_expr(rn_u, rep_raw, synth_to_hole)
        if p_sk != r_sk and not _contains_opaque(p_sk) and not _contains_opaque(r_sk):
            is_ret = _is_in_return_or_tail_position(pn_u, src_lang)
            return p_sk, r_sk, is_ret
    return None


def compile_rule_to_cst_skeleton(rule: Mapping[str, Any]) -> dict[str, Any] | None:
    """Lift a `VerifiedSkillStore` token rule into a `(pattern_skeleton, replacement_skeleton)` pair."""
    src_lang = str(rule.get("language") or "python").lower()
    if src_lang not in CODE_LANGUAGES:
        return None
    pat_toks = rule.get("pattern_tokens") or []
    rep_toks = rule.get("replacement_tokens") or []
    if not pat_toks or not rep_toks:
        return None

    hole_to_synth: dict[str, str] = {}
    synth_to_hole: dict[str, str] = {}
    counter = 0

    def _render_tokens(toks: Sequence[Any]) -> str:
        nonlocal counter
        parts: list[str] = []
        for item in toks:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            kind, val = str(item[0]), str(item[1])
            if kind in ("hole_id", "hole_num", "hole_str"):
                if kind == "hole_str":
                    return ""
                syn = hole_to_synth.get(val)
                if syn is None:
                    counter += 1
                    syn = f"__hnum{counter}__" if kind == "hole_num" else f"__hid{counter}__"
                    hole_to_synth[val] = syn
                    synth_to_hole[syn] = val
                parts.append(syn)
            else:
                parts.append(val)
        return "".join(parts)

    pat_raw_text = _render_tokens(pat_toks)
    rep_raw_text = _render_tokens(rep_toks)
    if not pat_raw_text.strip() or not rep_raw_text.strip():
        return None

    pat_skel: tuple[Any, ...] | None = None
    rep_skel: tuple[Any, ...] | None = None
    is_return_anchored = False

    # 1. Try direct CST parse + lockstep LCA descent (handles multi-line `def`/`fn`/`func` & statement blocks)
    direct = _direct_cst_changed_expr_pair(
        (pat_raw_text.rstrip() + "\n").encode("utf-8"),
        (rep_raw_text.rstrip() + "\n").encode("utf-8"),
        src_lang,
        synth_to_hole,
    )
    if direct is not None:
        pat_skel, rep_skel, is_return_anchored = direct

    # 2. Fallback for standalone expression / `return E` / `if E:` fragments
    if pat_skel is None or rep_skel is None:
        pat_src = pat_raw_text.strip()
        rep_src = rep_raw_text.strip()
        if re.match(r"^return\b", pat_src) and re.match(r"^return\b", rep_src):
            is_return_anchored = True
            pat_src = re.sub(r"^return\s+", "", pat_src).rstrip(";").strip()
            rep_src = re.sub(r"^return\s+", "", rep_src).rstrip(";").strip()
        elif re.match(r"^(?:elif|if)\b", pat_src) and re.match(r"^(?:elif|if)\b", rep_src) and pat_src.endswith(":") and rep_src.endswith(":"):
            pat_src = re.sub(r"^(?:elif|if)\s+", "", pat_src[:-1]).strip()
            rep_src = re.sub(r"^(?:elif|if)\s+", "", rep_src[:-1]).strip()
        else:
            pat_src = pat_src.rstrip(";").strip()
            rep_src = rep_src.rstrip(";").strip()

        def _parse_expr_in_lang(expr_str: str) -> tuple[Any, ...] | None:
            if "\n" in expr_str:
                return None
            if src_lang == "python":
                wrapped = f"def __f():\n    return {expr_str}\n".encode("utf-8")
            elif src_lang == "rust":
                wrapped = f"fn __f() -> bool {{ {expr_str} }}\n".encode("utf-8")
            elif src_lang == "go":
                wrapped = f"package p\nfunc __f() bool {{ return {expr_str} }}\n".encode("utf-8")
            elif src_lang in ("typescript", "javascript"):
                wrapped = f"function __f() {{ return {expr_str}; }}\n".encode("utf-8")
            elif src_lang == "java":
                wrapped = f"class __C {{ static Object __f() {{ return {expr_str}; }} }}\n".encode("utf-8")
            elif src_lang == "cpp":
                wrapped = f"auto __f() {{ return {expr_str}; }}\n".encode("utf-8")
            else:
                return None
            try:
                tree = tsk.parse_bytes(src_lang, wrapped)
            except Exception:
                return None
            if getattr(tree.root_node, "has_error", False):
                return None
            target_node = None
            stack = [tree.root_node]
            while stack:
                nd = stack.pop()
                if nd.type == "return_statement":
                    named = [c for c in nd.children if c.is_named and c.type != "return"]
                    if named:
                        target_node = named[-1]
                        break
                elif src_lang == "rust" and nd.type == "block":
                    named = [c for c in nd.children if c.is_named]
                    if named:
                        target_node = named[-1]
                        break
                stack.extend(reversed(nd.children))
            if target_node is None:
                return None
            skel = cst_to_canonical_expr(target_node, wrapped, synth_to_hole)
            if _contains_opaque(skel):
                return None
            return skel

        pat_skel = _parse_expr_in_lang(pat_src)
        rep_skel = _parse_expr_in_lang(rep_src)

    if pat_skel is None or rep_skel is None or pat_skel == rep_skel or not _has_non_hole_structure(pat_skel):
        return None

    pat_atoms: set[str] = set()
    pat_holes: set[str] = set()
    rep_atoms: set[str] = set()
    rep_holes: set[str] = set()
    _collect_atoms_and_holes(pat_skel, pat_atoms, pat_holes)
    _collect_atoms_and_holes(rep_skel, rep_atoms, rep_holes)
    if not rep_holes.issubset(pat_holes) or not rep_atoms.issubset(pat_atoms):
        return None

    return {
        "source_language": src_lang,
        "pattern_skeleton": pat_skel,
        "replacement_skeleton": rep_skel,
        "is_return_anchored": is_return_anchored,
    }


def _peel_single_diff_child(p: tuple[Any, ...], r: tuple[Any, ...]) -> tuple[tuple[Any, ...], tuple[Any, ...]] | None:
    """If `p` and `r` share an identical outer node and differ in exactly one child, return that child pair."""
    if p[0] != r[0]:
        return None
    kind = p[0]
    if kind == "LEN":
        return (p[1], r[1])
    if kind == "UNOP" and p[1] == r[1]:
        return (p[2], r[2])
    if kind == "BINOP" and p[1] == r[1]:
        if p[2] == r[2] and p[3] != r[3]:
            return (p[3], r[3])
        if p[3] == r[3] and p[2] != r[2]:
            return (p[2], r[2])
        return None
    if kind in ("CALL1", "ATTR", "SUBSCRIPT"):
        if p[1] == r[1] and p[2] != r[2]:
            return (p[2], r[2])
        if p[2] == r[2] and p[1] != r[1]:
            return (p[1], r[1])
        return None
    if kind == "CALL" and p[1] == r[1] and len(p[2]) == len(r[2]):
        diffs = [(pa, ra) for pa, ra in zip(p[2], r[2]) if pa != ra]
        return diffs[0] if len(diffs) == 1 else None
    if kind == "MCALL" and p[1] == r[1] and p[2] == r[2] and len(p[3]) == len(r[3]):
        diffs = [(pa, ra) for pa, ra in zip(p[3], r[3]) if pa != ra]
        return diffs[0] if len(diffs) == 1 else None
    if kind in ("TERNARY", "SLICE"):
        diffs = [(pa, ra) for pa, ra in zip(p[1:4], r[1:4]) if pa != ra]
        return diffs[0] if len(diffs) == 1 else None
    if kind == "GENERIC_CST" and p[1] == r[1] and tuple(s.strip() for s in p[2]) == tuple(s.strip() for s in r[2]) and len(p[3]) == len(r[3]):
        diffs = [(pa, ra) for pa, ra in zip(p[3], r[3]) if pa != ra]
        return diffs[0] if len(diffs) == 1 else None
    return None


def minimize_cst_skeleton_pair(
    pat_skel: tuple[Any, ...],
    rep_skel: tuple[Any, ...],
) -> tuple[tuple[Any, ...], tuple[Any, ...]] | None:
    """Peel unchanged outer CST wrappers and generalize unchanged composite child subtrees into `?exprK` holes."""
    p, r = pat_skel, rep_skel
    while p != r:
        nxt = _peel_single_diff_child(p, r)
        if nxt is None or not _has_non_hole_structure(nxt[0]):
            break
        p, r = nxt

    if p == r or not _has_non_hole_structure(p):
        return None

    expr_map: dict[tuple[Any, ...], tuple[str, str]] = {}

    def _has_any_hole(sk: tuple[Any, ...]) -> bool:
        if sk[0] == "HOLE":
            return True
        return any(_has_any_hole(ch) for ch in _iter_child_skeletons(sk))

    def _abstract_child(cp: tuple[Any, ...], cr: tuple[Any, ...]) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
        if cp == cr and cp[0] not in ("HOLE", "NUM", "ATOM") and _has_any_hole(cp):
            h = expr_map.get(cp)
            if h is None:
                h = ("HOLE", f"?expr{len(expr_map) + 1}")
                expr_map[cp] = h
            return h, h
        return cp, cr

    if p[0] == r[0]:
        kind = p[0]
        if kind == "BINOP":
            lp, lr = _abstract_child(p[2], r[2])
            rp, rr = _abstract_child(p[3], r[3])
            p = ("BINOP", p[1], lp, rp)
            r = ("BINOP", r[1], lr, rr)
        elif kind == "TERNARY":
            c1, c2 = _abstract_child(p[1], r[1])
            t1, t2 = _abstract_child(p[2], r[2])
            e1, e2 = _abstract_child(p[3], r[3])
            p = ("TERNARY", c1, t1, e1)
            r = ("TERNARY", c2, t2, e2)
        elif kind == "SUBSCRIPT":
            b1, b2 = _abstract_child(p[1], r[1])
            i1, i2 = _abstract_child(p[2], r[2])
            p = ("SUBSCRIPT", b1, i1)
            r = ("SUBSCRIPT", b2, i2)
        elif kind == "SLICE":
            b1, b2 = _abstract_child(p[1], r[1])
            l1, l2 = _abstract_child(p[2], r[2])
            h1, h2 = _abstract_child(p[3], r[3])
            p = ("SLICE", b1, l1, h1)
            r = ("SLICE", b2, l2, h2)
        elif kind == "GENERIC_CST" and p[1] == r[1] and len(p[3]) == len(r[3]):
            c_pairs = [_abstract_child(pa, ra) for pa, ra in zip(p[3], r[3])]
            p = ("GENERIC_CST", p[1], p[2], tuple(x[0] for x in c_pairs))
            r = ("GENERIC_CST", r[1], r[2], tuple(x[1] for x in c_pairs))
        elif kind == "CALL" and len(p[2]) == len(r[2]):
            c_pairs = [_abstract_child(pa, ra) for pa, ra in zip(p[2], r[2])]
            p = ("CALL", p[1], tuple(x[0] for x in c_pairs))
            r = ("CALL", r[1], tuple(x[1] for x in c_pairs))
        elif kind == "MCALL" and len(p[3]) == len(r[3]):
            r_recv1, r_recv2 = _abstract_child(p[1], r[1])
            c_pairs = [_abstract_child(pa, ra) for pa, ra in zip(p[3], r[3])]
            p = ("MCALL", r_recv1, p[2], tuple(x[0] for x in c_pairs))
            r = ("MCALL", r_recv2, r[2], tuple(x[1] for x in c_pairs))

    pa: set[str] = set()
    ph: set[str] = set()
    ra: set[str] = set()
    rh: set[str] = set()
    _collect_atoms_and_holes(p, pa, ph)
    _collect_atoms_and_holes(r, ra, rh)
    if not ph or not rh.issubset(ph) or not ra.issubset(pa):
        return None
    return p, r


def _is_in_return_or_tail_position(node: Any, target_language: str) -> bool:
    lang = target_language.lower()
    p = getattr(node, "parent", None)
    while p is not None and p.type in _WRAPPER_TYPES:
        p = getattr(p, "parent", None)
    if p is None:
        return False
    if p.type == "return_statement":
        return True
    if lang == "rust" and p.type == "block":
        after_bytes = [c.type for c in p.children if c.start_byte >= node.end_byte]
        if ";" not in after_bytes:
            return True
    if lang in ("typescript", "javascript") and p.type == "arrow_function":
        return True
    return False


def _iter_python_guard_statement_candidates(
    source_text: str,
    rule: Mapping[str, Any],
    *,
    max_candidates: int = 16,
) -> Iterator[str]:
    """General AST/CST multi-statement guard-insertion unification over compound operands & sibling operators."""
    import ast
    import textwrap

    pat_toks = rule.get("pattern_tokens")
    rep_toks = rule.get("replacement_tokens")
    if not isinstance(pat_toks, list) or not isinstance(rep_toks, list):
        return

    hole_map: dict[str, str] = {}
    rev_hole: dict[str, str] = {}
    idx_h = 0
    for kind, val in pat_toks + rep_toks:
        if str(kind).startswith("hole_") and str(val) not in hole_map:
            placeholder = f"__brain_h{idx_h}__"
            hole_map[str(val)] = placeholder
            rev_hole[placeholder] = str(val)
            idx_h += 1
    if not hole_map:
        return

    def _render_toks(toks: Sequence[Sequence[Any]], bind_map: Mapping[str, str], op_override: tuple[str, str] | None = None) -> str:
        parts: list[str] = []
        for kind, val in toks:
            sk, sv = str(kind), str(val)
            if sk.startswith("hole_") and sv in bind_map:
                parts.append(bind_map[sv])
            elif op_override is not None and sk == "op" and sv == op_override[0]:
                parts.append(op_override[1])
            else:
                parts.append(sv)
        return "".join(parts)

    pat_code = textwrap.dedent(_render_toks(pat_toks, hole_map)).strip()
    rep_code = textwrap.dedent(_render_toks(rep_toks, hole_map)).strip()
    try:
        pat_mod = ast.parse(pat_code)
        rep_mod = ast.parse(rep_code)
    except SyntaxError:
        return
    if len(pat_mod.body) != 1 or len(rep_mod.body) < 2:
        return
    pat_stmt = pat_mod.body[0]
    if not isinstance(pat_stmt, ast.Return) or pat_stmt.value is None:
        return

    import operator as _py_op

    _AST_BINOP_EVAL: dict[type[ast.operator], tuple[Any, str]] = {
        ast.Add: (_py_op.add, "+"),
        ast.Sub: (_py_op.sub, "-"),
        ast.Mult: (_py_op.mul, "*"),
        ast.Div: (_py_op.truediv, "/"),
        ast.FloorDiv: (_py_op.floordiv, "//"),
        ast.Mod: (_py_op.mod, "%"),
        ast.Pow: (_py_op.pow, "**"),
        ast.BitAnd: (_py_op.and_, "&"),
        ast.BitOr: (_py_op.or_, "|"),
        ast.BitXor: (_py_op.xor, "^"),
        ast.LShift: (_py_op.lshift, "<<"),
        ast.RShift: (_py_op.rshift, ">>"),
    }

    def _singularity_signature(op_cls: type[ast.operator]) -> tuple[type[BaseException] | None, type[BaseException] | None]:
        spec = _AST_BINOP_EVAL.get(op_cls)
        if spec is None:
            return (None, None)
        fn = spec[0]
        sig: list[type[BaseException] | None] = []
        for probe_rhs in (0, -1):
            try:
                fn(8, probe_rhs)
                sig.append(None)
            except Exception as exc:
                sig.append(type(exc))
        return (sig[0], sig[1])

    def _adapt_guard_zero_return_type(block_code: str, target_op_cls: type[ast.operator] | None) -> list[str]:
        if target_op_cls is None or target_op_cls not in _AST_BINOP_EVAL:
            return [block_code]
        try:
            sample_val = _AST_BINOP_EVAL[target_op_cls][0](8, 2)
        except Exception:
            return [block_code]
        target_zero = type(sample_val)(0)
        try:
            bmod = ast.parse(block_code)
        except SyntaxError:
            return [block_code]
        changed = False
        for sub in ast.walk(bmod):
            if (
                isinstance(sub, ast.Return)
                and isinstance(sub.value, ast.Constant)
                and isinstance(sub.value.value, (int, float))
                and not isinstance(sub.value.value, bool)
                and sub.value.value == 0
                and type(sub.value.value) is not type(target_zero)
            ):
                sub.value = ast.Constant(value=target_zero)
                changed = True
        if not changed:
            return [block_code]
        return [ast.unparse(bmod), block_code]

    def _match_ast_expr(
        p_nd: ast.AST,
        c_nd: ast.AST,
        binds: dict[str, str],
        op_pair: list[tuple[str, str, type[ast.operator]]],
    ) -> bool:
        if isinstance(p_nd, ast.Name) and p_nd.id in rev_hole:
            h_nm = rev_hole[p_nd.id]
            c_txt = ast.unparse(c_nd).strip()
            if isinstance(c_nd, (ast.BinOp, ast.BoolOp, ast.IfExp, ast.Compare)):
                c_txt = f"({c_txt})"
            prev = binds.get(h_nm)
            if prev is not None and prev.strip("() ") != c_txt.strip("() "):
                return False
            binds[h_nm] = c_txt
            return True
        if isinstance(p_nd, ast.BinOp) and isinstance(c_nd, ast.BinOp):
            p_op_t, c_op_t = type(p_nd.op), type(c_nd.op)
            if p_op_t is c_op_t:
                pass
            elif (
                p_op_t in _AST_BINOP_EVAL
                and c_op_t in _AST_BINOP_EVAL
                and _singularity_signature(p_op_t) != (None, None)
                and _singularity_signature(p_op_t) == _singularity_signature(c_op_t)
            ):
                op_pair.append((_AST_BINOP_EVAL[p_op_t][1], _AST_BINOP_EVAL[c_op_t][1], c_op_t))
            else:
                return False
            return _match_ast_expr(p_nd.left, c_nd.left, binds, op_pair) and _match_ast_expr(
                p_nd.right, c_nd.right, binds, op_pair
            )
        return ast.dump(p_nd) == ast.dump(c_nd)

    try:
        src_tree = ast.parse(source_text)
    except SyntaxError:
        return
    src_lines = source_text.splitlines(keepends=True)
    line_offs = [0]
    for ln in src_lines:
        line_offs.append(line_offs[-1] + len(ln))

    seen: set[str] = {source_text}
    yielded = 0
    for nd in ast.walk(src_tree):
        if not isinstance(nd, ast.Return) or nd.value is None or nd.lineno is None or nd.end_lineno is None:
            continue
        binds: dict[str, str] = {}
        op_swaps: list[tuple[str, str, type[ast.operator]]] = []
        if not _match_ast_expr(pat_stmt.value, nd.value, binds, op_swaps):
            continue
        op_ov = (op_swaps[0][0], op_swaps[0][1]) if op_swaps else None
        target_op_cls = op_swaps[0][2] if op_swaps else None
        rendered_block = textwrap.dedent(_render_toks(rep_toks, binds, op_override=op_ov)).strip()
        variants = _adapt_guard_zero_return_type(rendered_block, target_op_cls)

        line_start_idx = line_offs[nd.lineno - 1]
        stmt_start = line_start_idx + nd.col_offset
        stmt_end = line_offs[nd.end_lineno - 1] + nd.end_col_offset
        indent = " " * nd.col_offset

        for var_block in variants:
            indented_lines = [
                (indent + ln if i > 0 and ln.strip() else ln)
                for i, ln in enumerate(var_block.splitlines())
            ]
            cand = source_text[:stmt_start] + "\n".join(indented_lines) + source_text[stmt_end:]
            if cand in seen:
                continue
            try:
                ast.parse(cand)
            except SyntaxError:
                continue
            seen.add(cand)
            yielded += 1
            yield cand
            if yielded >= max_candidates:
                return


def _substrate_present() -> bool:
    """Is the Tree-Sitter substrate importable? Checked at call time, not import time."""
    try:
        from tree_sitter import Parser  # noqa: F401
        from tree_sitter_languages import get_language  # noqa: F401
    except Exception:
        return False
    return True


def iter_cst_skeleton_candidates(
    source_text: str,
    rule: Mapping[str, Any],
    *,
    target_language: str,
    max_candidates: int = 16,
    minimize: bool = False,
    suspect_lines: Sequence[int] | None = None,
) -> Iterator[str]:
    """Yield syntactically valid `target_language` rewrites via Tree-Sitter CST skeleton unification."""
    lang = target_language.lower()
    if lang not in CODE_LANGUAGES:
        return
    compiled = compile_rule_to_cst_skeleton(rule)
    if compiled is None:
        if lang == "python":
            yield from _iter_python_guard_statement_candidates(
                source_text, rule, max_candidates=max_candidates
            )
        return

    skeleton_pairs: list[tuple[tuple[Any, ...], tuple[Any, ...]]] = [
        (compiled["pattern_skeleton"], compiled["replacement_skeleton"])
    ]
    if minimize:
        minimized = minimize_cst_skeleton_pair(
            compiled["pattern_skeleton"],
            compiled["replacement_skeleton"],
        )
        if minimized is not None and minimized not in skeleton_pairs:
            skeleton_pairs.append(minimized)
    ret_only = bool(compiled["is_return_anchored"])

    raw = source_text.encode("utf-8")
    try:
        tree = tsk.parse_bytes(lang, raw)
    except Exception as exc:
        # A missing substrate is not "this rule does not apply". Propagate it so the caller can
        # say UNAVAILABLE instead of reporting a capability failure it never measured.
        if not _substrate_present():
            raise CstSubstrateUnavailable(lang, type(exc).__name__) from exc
        if lang == "python":
            yield from _iter_python_stdlib_ast_candidates(source_text, skeleton_pairs, max_candidates=max_candidates, suspect_lines=suspect_set if (suspect_set := [int(ln) for ln in (suspect_lines or ()) if isinstance(ln, int) and ln > 0]) else None)
        return
    if getattr(tree.root_node, "has_error", False):
        return

    expr_nodes: list[Any] = []
    stack = [tree.root_node]
    while stack:
        nd = stack.pop()
        if _is_candidate_expr_node(nd, raw):
            expr_nodes.append(nd)
        stack.extend(reversed(nd.children))

    yielded = 0
    seen: set[str] = {source_text}
    suspect_set = [int(ln) for ln in (suspect_lines or ()) if isinstance(ln, int) and ln > 0]
    if suspect_set:
        ordered_nodes = sorted(
            expr_nodes,
            key=lambda n: (
                min(abs((int(n.start_point[0]) + 1) - ln) for ln in suspect_set),
                0 if (ret_only and _is_in_return_or_tail_position(n, lang)) else 1,
                int(n.start_byte),
            ),
        )
    elif ret_only:
        ordered_nodes = (
            [n for n in expr_nodes if _is_in_return_or_tail_position(n, lang)]
            + [n for n in expr_nodes if not _is_in_return_or_tail_position(n, lang)]
        )
    else:
        ordered_nodes = expr_nodes

    for pat_skel, rep_skel in skeleton_pairs:
        for nd in ordered_nodes:
            bindings: dict[str, str] = {}
            if not _unify_cst_node_directly(pat_skel, nd, raw, bindings):
                continue
            repl_str = render_canonical_expr(rep_skel, lang, bindings)
            if not repl_str:
                continue
            cand_bytes = raw[:nd.start_byte] + repl_str.encode("utf-8") + raw[nd.end_byte:]
            try:
                cand_tree = tsk.parse_bytes(lang, cand_bytes)
                if getattr(cand_tree.root_node, "has_error", False):
                    continue
                cand_text = cand_bytes.decode("utf-8")
            except Exception:
                continue
            if cand_text not in seen:
                seen.add(cand_text)
                yielded += 1
                yield cand_text
                if yielded >= max_candidates:
                    return


def _unify_cst_node_directly(
    pat_skel: tuple[Any, ...],
    node: Any,
    raw: bytes,
    bindings: dict[str, str],
) -> bool:
    """Unify `pat_skel` directly against a concrete Tree-Sitter CST node, binding exact source slices."""
    orig_node = node
    node = _unwrap_expr(node)
    kind = pat_skel[0]
    if kind == "HOLE":
        h_name = str(pat_skel[1])
        unwrapped_txt = _node_text(node, raw).strip()
        raw_txt = _node_text(orig_node, raw).strip()
        if h_name.startswith("?num") and not (
            node.type in _NUM_NODE_TYPES or re.fullmatch(r"\d+(?:\.\d+)?", unwrapped_txt)
        ):
            return False
        need_wrap = (
            orig_node.type == "parenthesized_expression"
            or node.type in _BINARY_NODE_TYPES
            or node.type in _TERNARY_NODE_TYPES
        )
        bound_txt = (
            raw_txt
            if orig_node.type == "parenthesized_expression"
            else (f"({unwrapped_txt})" if need_wrap and not (unwrapped_txt.startswith("(") and unwrapped_txt.endswith(")")) else unwrapped_txt)
        )
        prev = bindings.get(h_name)
        if prev is not None and prev.strip("() ") != unwrapped_txt.strip("() "):
            return False
        if prev is None:
            bindings[h_name] = bound_txt
        return True

    if kind == "LEN":
        arg_nd = _extract_len_arg(node, raw)
        if arg_nd is None:
            return False
        return _unify_cst_node_directly(pat_skel[1], arg_nd, raw, bindings)

    if kind == "CALL1":
        call_parts = _extract_call_or_mcall(node)
        if call_parts is None or call_parts[0] != "CALL" or len(call_parts[3]) != 1:
            return False
        callee_txt = _node_text(call_parts[1], raw).strip()
        return _unify_skeleton(pat_skel[1], ("ATOM", callee_txt), bindings, callee_txt) and _unify_cst_node_directly(
            pat_skel[2], call_parts[3][0], raw, bindings
        )

    if kind == "CALL":
        call_parts = _extract_call_or_mcall(node)
        if call_parts is None or call_parts[0] != "CALL" or len(call_parts[3]) != len(pat_skel[2]):
            return False
        if not _unify_cst_node_directly(pat_skel[1], call_parts[1], raw, bindings):
            return False
        return all(_unify_cst_node_directly(pa, ca, raw, bindings) for pa, ca in zip(pat_skel[2], call_parts[3]))

    if kind == "MCALL0":
        call_parts = _extract_call_or_mcall(node)
        if call_parts is None or call_parts[0] != "MCALL" or call_parts[2] is None or len(call_parts[3]) != 0:
            return False
        m_txt = _node_text(call_parts[2], raw).strip()
        return _unify_cst_node_directly(pat_skel[1], call_parts[1], raw, bindings) and _unify_skeleton(
            pat_skel[2], ("ATOM", m_txt), bindings, m_txt
        )

    if kind == "MCALL":
        call_parts = _extract_call_or_mcall(node)
        if call_parts is None or call_parts[0] != "MCALL" or call_parts[2] is None or len(call_parts[3]) != len(pat_skel[3]):
            return False
        m_txt = _node_text(call_parts[2], raw).strip()
        if not _unify_cst_node_directly(pat_skel[1], call_parts[1], raw, bindings):
            return False
        if not _unify_skeleton(pat_skel[2], ("ATOM", m_txt), bindings, m_txt):
            return False
        return all(_unify_cst_node_directly(pa, ca, raw, bindings) for pa, ca in zip(pat_skel[3], call_parts[3]))

    if kind == "ATTR":
        attr_parts = _extract_attr_parts(node)
        if attr_parts is None or _extract_len_arg(node, raw) is not None:
            return False
        f_txt = _node_text(attr_parts[1], raw).strip()
        return _unify_cst_node_directly(pat_skel[1], attr_parts[0], raw, bindings) and _unify_skeleton(
            pat_skel[2], ("ATOM", f_txt), bindings, f_txt
        )

    if kind == "SUBSCRIPT":
        sub_parts = _extract_subscript_parts(node)
        if sub_parts is None:
            return False
        return _unify_cst_node_directly(pat_skel[1], sub_parts[0], raw, bindings) and _unify_cst_node_directly(
            pat_skel[2], sub_parts[1], raw, bindings
        )

    if kind == "TERNARY":
        tern = _extract_ternary_parts(node, raw)
        if tern is None:
            return False
        return (
            _unify_cst_node_directly(pat_skel[1], tern[0], raw, bindings)
            and _unify_cst_node_directly(pat_skel[2], tern[1], raw, bindings)
            and _unify_cst_node_directly(pat_skel[3], tern[2], raw, bindings)
        )

    if kind == "SLICE":
        sl_parts = _extract_slice_parts(node, raw)
        if sl_parts is None:
            return False
        b_nd, lo_nd, hi_nd = sl_parts
        if not _unify_cst_node_directly(pat_skel[1], b_nd, raw, bindings):
            return False
        if pat_skel[2][0] == "NONE_BOUND":
            if lo_nd is not None:
                return False
        elif lo_nd is None or not _unify_cst_node_directly(pat_skel[2], lo_nd, raw, bindings):
            return False
        if pat_skel[3][0] == "NONE_BOUND":
            if hi_nd is not None:
                return False
        elif hi_nd is None or not _unify_cst_node_directly(pat_skel[3], hi_nd, raw, bindings):
            return False
        return True

    if kind == "GENERIC_CST":
        if node.type != pat_skel[1]:
            return False
        named = [c for c in node.children if c.is_named]
        if len(named) != len(pat_skel[3]):
            return False
        spans: list[str] = []
        cursor = node.start_byte
        for ch in named:
            spans.append(raw[cursor:ch.start_byte].decode("utf-8", errors="replace").strip())
            cursor = ch.end_byte
        spans.append(raw[cursor:node.end_byte].decode("utf-8", errors="replace").strip())
        if tuple(spans) != tuple(str(s).strip() for s in pat_skel[2]):
            return False
        return all(_unify_cst_node_directly(pa, ca, raw, bindings) for pa, ca in zip(pat_skel[3], named))

    if kind == "NUM":
        return _node_text(node, raw).strip() == str(pat_skel[1])

    if kind == "ATOM":
        return _node_text(node, raw).strip() == str(pat_skel[1])

    if kind == "UNOP":
        if node.type not in _UNARY_NODE_TYPES:
            return False
        named = [c for c in node.children if c.is_named]
        if len(named) != 1:
            return False
        operand = named[0]
        prefix = raw[node.start_byte:operand.start_byte].decode("utf-8", errors="replace").strip()
        if _CANON_OP.get(prefix) != pat_skel[1]:
            return False
        return _unify_cst_node_directly(pat_skel[2], operand, raw, bindings)

    if kind == "BINOP":
        if node.type not in _BINARY_NODE_TYPES:
            return False
        named = [c for c in node.children if c.is_named]
        if len(named) != 2:
            return False
        left, right = named[0], named[1]
        mid = raw[left.end_byte:right.start_byte].decode("utf-8", errors="replace").strip()
        if _CANON_OP.get(mid) != pat_skel[1]:
            return False
        return (
            _unify_cst_node_directly(pat_skel[2], left, raw, bindings)
            and _unify_cst_node_directly(pat_skel[3], right, raw, bindings)
        )
    return False


def recall_across_languages_cst(
    store: Any,
    *,
    source_text: str,
    target_language: str,
    verifier: Any,
    error_class: str | None = None,
    source_languages: Sequence[str] | None = None,
    minimize: bool = False,
    suspect_lines: Sequence[int] | None = None,
    rule_filter: Any = None,
) -> dict[str, Any] | None:
    """Propose cross-language rewrites over Tree-Sitter CST skeletons (`7` code languages), gated by `verifier`."""
    if not callable(verifier):
        raise ValueError("CST_CROSS_LANGUAGE_RECALL_REQUIRES_VERIFIER")
    tgt = target_language.lower()
    if tgt not in CODE_LANGUAGES:
        return None
    langs = list(source_languages) if source_languages is not None else list(CODE_LANGUAGES)
    seen_skills: set[str] = set()
    for src_lang in langs:
        if src_lang.lower() == tgt:
            continue
        try:
            rules = store.lookup_rules(src_lang, error_class)
        except TypeError:
            rules = store.lookup_rules(src_lang)
        for rule in rules:
            if callable(rule_filter) and not rule_filter(rule):
                continue
            sid = str(rule.get("skill_id") or "")
            if sid and sid in seen_skills:
                continue
            seen_skills.add(sid)
            try:
                candidates = list(iter_cst_skeleton_candidates(
                    source_text,
                    rule,
                    target_language=tgt,
                    minimize=minimize,
                    suspect_lines=suspect_lines,
                ))
            except CstSubstrateUnavailable:
                # Nothing was measured. Reporting "no transfer" here is a false negative about a
                # capability the tree does have once its pinned substrate is restored.
                raise
            for cand in candidates:
                try:
                    ok = bool(verifier(cand))
                except Exception:
                    ok = False
                if ok:
                    return {
                        "schema": SCHEMA,
                        "skill_id": sid,
                        "from_language": src_lang,
                        "to_language": tgt,
                        "patched_source": cand,
                        "from_cross_language_memory": True,
                        "scope_tier": "CROSS_LANGUAGE_CST_SKELETON",
                        "verifier_passed": True,
                        "whole_task_correctness_proved": False,
                    }
    return None


def _py_ast_to_skel(node: Any, hole_by_ident: Mapping[str, str] | None = None) -> tuple[Any, ...]:
    import ast

    if isinstance(node, ast.Name):
        return _ident_or_hole(node.id, hole_by_ident)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        s = str(node.value)
        return ("HOLE", hole_by_ident[s]) if (hole_by_ident and s in hole_by_ident) else ("NUM", s)
    if isinstance(node, ast.BinOp):
        op_map = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "/", ast.Mod: "%"}
        op_s = op_map.get(type(node.op))
        if op_s:
            return ("BINOP", op_s, _py_ast_to_skel(node.left, hole_by_ident), _py_ast_to_skel(node.right, hole_by_ident))
    if isinstance(node, ast.BoolOp) and len(node.values) == 2:
        op_s = "&&" if isinstance(node.op, ast.And) else "||"
        return ("BINOP", op_s, _py_ast_to_skel(node.values[0], hole_by_ident), _py_ast_to_skel(node.values[1], hole_by_ident))
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        cmp_map = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!="}
        op_s = cmp_map.get(type(node.ops[0]))
        if op_s:
            return ("BINOP", op_s, _py_ast_to_skel(node.left, hole_by_ident), _py_ast_to_skel(node.comparators[0], hole_by_ident))
    if isinstance(node, ast.UnaryOp):
        u_map = {ast.Not: "!", ast.USub: "-", ast.UAdd: "+"}
        op_s = u_map.get(type(node.op))
        if op_s:
            return ("UNOP", op_s, _py_ast_to_skel(node.operand, hole_by_ident))
    if isinstance(node, ast.Call) and not node.keywords:
        if isinstance(node.func, ast.Name) and node.func.id == "len" and len(node.args) == 1:
            return ("LEN", _py_ast_to_skel(node.args[0], hole_by_ident))
        if isinstance(node.func, ast.Attribute):
            return (
                "MCALL",
                _py_ast_to_skel(node.func.value, hole_by_ident),
                _ident_or_hole(node.func.attr, hole_by_ident),
                tuple(_py_ast_to_skel(a, hole_by_ident) for a in node.args),
            )
        return ("CALL", _py_ast_to_skel(node.func, hole_by_ident), tuple(_py_ast_to_skel(a, hole_by_ident) for a in node.args))
    if isinstance(node, ast.Subscript):
        if isinstance(node.slice, ast.Slice) and node.slice.step is None:
            return (
                "SLICE",
                _py_ast_to_skel(node.value, hole_by_ident),
                _py_ast_to_skel(node.slice.lower, hole_by_ident) if node.slice.lower is not None else ("NONE_BOUND",),
                _py_ast_to_skel(node.slice.upper, hole_by_ident) if node.slice.upper is not None else ("NONE_BOUND",),
            )
        return ("SUBSCRIPT", _py_ast_to_skel(node.value, hole_by_ident), _py_ast_to_skel(node.slice, hole_by_ident))
    if isinstance(node, ast.Attribute):
        return ("ATTR", _py_ast_to_skel(node.value, hole_by_ident), _ident_or_hole(node.attr, hole_by_ident))
    if isinstance(node, ast.IfExp):
        return ("TERNARY", _py_ast_to_skel(node.test, hole_by_ident), _py_ast_to_skel(node.body, hole_by_ident), _py_ast_to_skel(node.orelse, hole_by_ident))
    if isinstance(node, ast.AugAssign):
        op_map = {ast.Add: "+=", ast.Sub: "-=", ast.Mult: "*=", ast.FloorDiv: "//=", ast.Mod: "%="}
        op_s = op_map.get(type(node.op))
        if op_s:
            return ("GENERIC_CST", "augmented_assignment", ("", f" {op_s} ", ""), (_py_ast_to_skel(node.target, hole_by_ident), _py_ast_to_skel(node.value, hole_by_ident)))
    return ("OPAQUE", ast.unparse(node))


def _python_stdlib_ast_changed_pair(
    pat_src: str,
    rep_src: str,
    synth_to_hole: Mapping[str, str],
) -> tuple[tuple[Any, ...], tuple[Any, ...], bool] | None:
    import ast

    try:
        pm = ast.parse(pat_src)
        rm = ast.parse(rep_src)
    except SyntaxError:
        return None
    pn: Any = pm
    rn: Any = rm
    is_ret = False
    while type(pn) is type(rn):
        if isinstance(pn, ast.Return):
            is_ret = True
        p_ch = list(ast.iter_child_nodes(pn))
        r_ch = list(ast.iter_child_nodes(rn))
        if len(p_ch) != len(r_ch) or not p_ch:
            break
        diffs = [i for i, (a, b) in enumerate(zip(p_ch, r_ch)) if ast.dump(a) != ast.dump(b)]
        if len(diffs) != 1:
            break
        nxt_p, nxt_r = p_ch[diffs[0]], r_ch[diffs[0]]
        if isinstance(nxt_p, ast.operator):
            break
        if isinstance(nxt_p, (ast.Name, ast.Constant)) and isinstance(pn, (ast.expr, ast.AugAssign)):
            break
        pn, rn = nxt_p, nxt_r
    p_sk = _py_ast_to_skel(pn, synth_to_hole)
    r_sk = _py_ast_to_skel(rn, synth_to_hole)
    if p_sk != r_sk and not _contains_opaque(p_sk) and not _contains_opaque(r_sk):
        return p_sk, r_sk, is_ret
    return None


def _iter_python_stdlib_ast_candidates(
    source_text: str,
    skeleton_pairs: Sequence[tuple[tuple[Any, ...], tuple[Any, ...]]],
    *,
    max_candidates: int = 16,
    suspect_lines: Sequence[int] | None = None,
) -> Iterator[str]:
    import ast

    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return
    lines = source_text.splitlines(keepends=True)
    line_offsets = [0]
    for ln in lines:
        line_offsets.append(line_offsets[-1] + len(ln))

    nodes = [
        nd for nd in ast.walk(tree)
        if isinstance(nd, (ast.expr, ast.AugAssign))
        and getattr(nd, "lineno", None) is not None
        and getattr(nd, "end_lineno", None) is not None
    ]
    if suspect_lines:
        nodes.sort(key=lambda n: (min(abs(int(n.lineno) - s) for s in suspect_lines), int(n.lineno), int(n.col_offset)))

    seen: set[str] = {source_text}
    yielded = 0
    for pat_skel, rep_skel in skeleton_pairs:
        for nd in nodes:
            start = line_offsets[nd.lineno - 1] + nd.col_offset
            end = line_offsets[nd.end_lineno - 1] + nd.end_col_offset
            raw_slice = source_text[start:end]
            c_skel = _py_ast_to_skel(nd)
            bindings: dict[str, str] = {}
            if not _unify_skeleton(pat_skel, c_skel, bindings, raw_slice):
                continue
            repl = render_canonical_expr(rep_skel, "python", bindings)
            if not repl:
                continue
            cand = source_text[:start] + repl + source_text[end:]
            if cand in seen:
                continue
            try:
                ast.parse(cand)
            except SyntaxError:
                continue
            seen.add(cand)
            yielded += 1
            yield cand
            if yielded >= max_candidates:
                return

