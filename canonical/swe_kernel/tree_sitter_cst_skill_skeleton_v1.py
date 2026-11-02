#!/usr/bin/env python3
"""8-Language Tree-Sitter CST Skill Skeleton Unifier (`tree_sitter_cst_skill_skeleton_v1`).

Removes the `return`-keyword and language-specific spelling barriers identified in
`WHERE_THE_SOLUTIONS_LIVE_20261101_V1.md` §5.1 & §7 (`K3 = 0`, `$0` spend, `< 1 ms`):
  - Uses `canonical/runtime/tree_sitter_swe_kernel_v1.parse_bytes` across `python`,
    `rust`, `go`, `typescript`, `javascript`, `java`, and `cpp`.
  - Canonicalizes concrete CST nodes onto a language-neutral structural AST/CST
    skeleton (`BINOP`, `UNOP`, `LEN`, `HOLE_ID`, `HOLE_NUM`, `LIT_NUM`, `EXPR`) so:
      * Python `return E` unifies seamlessly with Rust block tail-expressions `E`
        (no `return` token), JS/TS concise arrow bodies `=> E`, and `return E;`
        in Go/TS/JS/Java/C++.
      * Python/Go `len(x)` unifies seamlessly with Rust `x.len()`, TS/JS `x.length`,
        and Java/C++ `x.size()`, emitting native target-language syntax on rewrite.
      * Python `and` / `or` / `not` unifies seamlessly with `&&` / `||` / `!`.
  - Every proposed candidate is fail-closed gated by:
      (1) exact CST structural hole unification (no fresh unbound identifiers),
      (2) `tree_sitter_swe_kernel_v1.parse_bytes` `has_error == False`, and
      (3) the caller's mandatory semantic/test `verifier(candidate) == True`.
"""
from __future__ import annotations

import re
from typing import Any, Iterator, Mapping, Sequence

from canonical.runtime import tree_sitter_swe_kernel_v1 as tsk

SCHEMA = "PROJECT_BRAIN_TREE_SITTER_CST_SKILL_SKELETON_V1"

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
    # Python `call` or Go `call_expression`: `len(x)`
    if t in ("call", "call_expression"):
        children = [c for c in node.children if c.is_named]
        if len(children) >= 2:
            callee, args_node = children[0], children[1]
            # Python / Go: `len(x)`
            if callee.type == "identifier" and _node_text(callee, raw) == "len":
                arg_named = [c for c in args_node.children if c.is_named]
                if len(arg_named) == 1:
                    return arg_named[0]
            # Rust / C++: `x.len()` or `x.size()`
            if callee.type in ("field_expression", "member_expression"):
                f_named = [c for c in callee.children if c.is_named]
                arg_named = [c for c in args_node.children if c.is_named]
                if len(f_named) == 2 and len(arg_named) == 0:
                    method_nm = _node_text(f_named[1], raw)
                    if method_nm in ("len", "size"):
                        return f_named[0]
    # TS / JS: `x.length`
    if t in ("member_expression", "field_expression"):
        f_named = [c for c in node.children if c.is_named]
        if len(f_named) == 2 and _node_text(f_named[1], raw) == "length":
            return f_named[0]
    # Java: `x.size()`
    if t == "method_invocation":
        named = [c for c in node.children if c.is_named]
        if len(named) >= 2 and _node_text(named[1], raw) == "size":
            args_node = next((c for c in named[2:] if "argument" in c.type), None)
            if args_node is None or len([c for c in args_node.children if c.is_named]) == 0:
                return named[0]
    return None


def cst_to_canonical_expr(node: Any, raw: bytes, hole_by_ident: Mapping[str, str] | None = None) -> tuple[Any, ...]:
    """Project a concrete Tree-Sitter expression node onto a canonical language-neutral tuple."""
    node = _unwrap_expr(node)
    len_arg = _extract_len_arg(node, raw)
    if len_arg is not None:
        return ("LEN", cst_to_canonical_expr(len_arg, raw, hole_by_ident))

    t = node.type
    if t in _BINARY_NODE_TYPES:
        # Children: left, op_token(s), right
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

    txt = _node_text(node, raw).strip()
    if t in _NUM_NODE_TYPES or re.fullmatch(r"\d+(?:\.\d+)?", txt):
        if hole_by_ident and txt in hole_by_ident:
            return ("HOLE", hole_by_ident[txt])
        return ("NUM", txt)

    if t in _IDENT_NODE_TYPES or re.fullmatch(r"[A-Za-z_$][\w$]*", txt):
        if hole_by_ident and txt in hole_by_ident:
            return ("HOLE", hole_by_ident[txt])
        return ("ATOM", txt)

    # Zero-arg member method call `recv.method()` (e.g. `hook.has_spec()`, `spec.hasSpec()`)
    m_call0 = re.fullmatch(r"([A-Za-z_$][\w$]*)\s*\.\s*([A-Za-z_$][\w$]*)\s*\(\s*\)", txt)
    if m_call0:
        r_tok, m_tok = m_call0.group(1), m_call0.group(2)
        r_sk = ("HOLE", hole_by_ident[r_tok]) if (hole_by_ident and r_tok in hole_by_ident) else ("ATOM", r_tok)
        m_sk = ("HOLE", hole_by_ident[m_tok]) if (hole_by_ident and m_tok in hole_by_ident) else ("ATOM", m_tok)
        return ("MCALL0", r_sk, m_sk)

    # Opaque sub-expression (e.g., `a[i]`, `obj.field`, `foo(bar)`): binds against a `?id` hole!
    return ("OPAQUE", txt)


def render_canonical_expr(expr: tuple[Any, ...], target_language: str, bindings: Mapping[str, str]) -> str | None:
    """Render a canonical CST expression into native `target_language` syntax."""
    lang = target_language.lower()
    kind = expr[0]
    if kind == "HOLE":
        val = bindings.get(str(expr[1]))
        return val if val is not None else None
    if kind in ("NUM", "ATOM", "OPAQUE"):
        return str(expr[1])
    if kind == "MCALL0":
        r_s = render_canonical_expr(expr[1], lang, bindings)
        m_s = render_canonical_expr(expr[2], lang, bindings)
        if r_s is None or m_s is None:
            return None
        return f"{r_s}.{m_s}()"
    if kind == "LEN":
        inner = render_canonical_expr(expr[1], lang, bindings)
        if inner is None:
            return None
        need_parens = " " in inner and not (inner.startswith("(") and inner.endswith(")"))
        recv = f"({inner})" if need_parens else inner
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
        if sub[0] == "BINOP":
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
        if left_t[0] == "BINOP" and left_t[1] != op:
            left_s = f"({left_s})"
        if right_t[0] == "BINOP" and right_t[1] != op:
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
    if p_kind == "MCALL0":
        return _unify_skeleton(pattern[1], concrete[1], bindings, raw_expr_text) and _unify_skeleton(
            pattern[2], concrete[2], bindings, raw_expr_text
        )
    if p_kind == "BINOP":
        return (
            pattern[1] == concrete[1]
            and _unify_skeleton(pattern[2], concrete[2], bindings, raw_expr_text)
            and _unify_skeleton(pattern[3], concrete[3], bindings, raw_expr_text)
        )
    return False


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
        return "".join(parts).strip()

    pat_src = _render_tokens(pat_toks)
    rep_src = _render_tokens(rep_toks)
    if not pat_src or not rep_src:
        return None

    # Strip leading `return ` / `if ` / `elif ` and trailing `;` or `:` so expression skeleton is pure
    is_return_anchored = False
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
        # Find the return expression or block tail expression
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
        if skel[0] == "OPAQUE":
            return None
        return skel

    pat_skel = _parse_expr_in_lang(pat_src)
    rep_skel = _parse_expr_in_lang(rep_src)
    if pat_skel is None or rep_skel is None or pat_skel == rep_skel:
        return None

    # Refuse if replacement introduces an unbound identifier atom not present in pattern
    def _collect_atoms_and_holes(sk: tuple[Any, ...], atoms: set[str], holes: set[str]) -> None:
        if sk[0] == "HOLE":
            holes.add(str(sk[1]))
        elif sk[0] == "ATOM":
            atoms.add(str(sk[1]))
        elif sk[0] in ("LEN", "UNOP"):
            _collect_atoms_and_holes(sk[-1], atoms, holes)
        elif sk[0] in ("BINOP", "MCALL0"):
            _collect_atoms_and_holes(sk[-2], atoms, holes)
            _collect_atoms_and_holes(sk[-1], atoms, holes)

    pat_atoms, pat_holes = set(), set()
    rep_atoms, rep_holes = set(), set()
    _collect_atoms_and_holes(pat_skel, pat_atoms, pat_holes)
    _collect_atoms_and_holes(rep_skel, rep_atoms, rep_holes)
    if (rep_atoms - pat_atoms) or (rep_holes - pat_holes):
        return None

    return {
        "schema": SCHEMA,
        "pattern_skeleton": pat_skel,
        "replacement_skeleton": rep_skel,
        "is_return_anchored": is_return_anchored,
    }


def _is_in_return_or_tail_position(node: Any, target_language: str) -> bool:
    lang = target_language.lower()
    p = getattr(node, "parent", None)
    while p is not None and p.type in _WRAPPER_TYPES:
        p = getattr(p, "parent", None)
    if p is None:
        return False
    if p.type == "return_statement":
        return True
    # Rust block tail expression (`fn f(...) -> T { expr }` or `if c { expr } else { expr }`)
    if lang == "rust" and p.type == "block":
        # A Rust tail expression has no trailing `;` child after it in the block
        after_bytes = [c.type for c in p.children if c.start_byte >= node.end_byte]
        if ";" not in after_bytes:
            return True
    # JS / TS concise arrow body (`(x, hi) => x <= hi`)
    if lang in ("typescript", "javascript") and p.type == "arrow_function":
        return True
    return False


def iter_cst_skeleton_candidates(
    source_text: str,
    rule: Mapping[str, Any],
    *,
    target_language: str,
    max_candidates: int = 16,
) -> Iterator[str]:
    """Yield syntactically valid `target_language` rewrites via Tree-Sitter CST skeleton unification."""
    lang = target_language.lower()
    if lang not in CODE_LANGUAGES:
        return
    compiled = compile_rule_to_cst_skeleton(rule)
    if compiled is None:
        return

    pat_skel = compiled["pattern_skeleton"]
    rep_skel = compiled["replacement_skeleton"]
    ret_only = bool(compiled["is_return_anchored"])

    raw = source_text.encode("utf-8")
    try:
        tree = tsk.parse_bytes(lang, raw)
    except Exception:
        return
    if getattr(tree.root_node, "has_error", False):
        return

    # Collect candidate expression nodes in source order
    expr_nodes: list[Any] = []
    stack = [tree.root_node]
    while stack:
        nd = stack.pop()
        if nd.type in _BINARY_NODE_TYPES or nd.type in _UNARY_NODE_TYPES or _extract_len_arg(nd, raw) is not None:
            expr_nodes.append(nd)
        stack.extend(reversed(nd.children))

    yielded = 0
    seen: set[str] = {source_text}
    # Prefer return/tail-anchored matches first when the taught rule was a return expression,
    # then offer general expression sites if needed (verifier always decides!).
    ordered_nodes = (
        [n for n in expr_nodes if _is_in_return_or_tail_position(n, lang)]
        + [n for n in expr_nodes if not _is_in_return_or_tail_position(n, lang)]
        if ret_only
        else expr_nodes
    )

    for nd in ordered_nodes:
        bindings: dict[str, str] = {}
        conc = cst_to_canonical_expr(nd, raw, None)
        # Re-walk concrete sub-nodes so `HOLE` binds exact concrete sub-expression source text
        if not _unify_cst_node_directly(pat_skel, nd, raw, bindings):
            continue
        _ = conc
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
    node = _unwrap_expr(node)
    kind = pat_skel[0]
    if kind == "HOLE":
        h_name = str(pat_skel[1])
        txt = _node_text(node, raw).strip()
        if h_name.startswith("?num") and not (node.type in _NUM_NODE_TYPES or re.fullmatch(r"\d+(?:\.\d+)?", txt)):
            return False
        prev = bindings.get(h_name)
        if prev is not None and prev != txt:
            return False
        bindings[h_name] = txt
        return True

    if kind == "LEN":
        arg_nd = _extract_len_arg(node, raw)
        if arg_nd is None:
            return False
        return _unify_cst_node_directly(pat_skel[1], arg_nd, raw, bindings)

    if kind == "NUM":
        return _node_text(node, raw).strip() == str(pat_skel[1])

    if kind == "ATOM":
        return _node_text(node, raw).strip() == str(pat_skel[1])

    if kind == "MCALL0":
        txt = _node_text(node, raw).strip()
        m = re.fullmatch(r"([A-Za-z_$][\w$]*)\s*\.\s*([A-Za-z_$][\w$]*)\s*\(\s*\)", txt)
        if not m:
            return False
        return _unify_skeleton(pat_skel[1], ("ATOM", m.group(1)), bindings, m.group(1)) and _unify_skeleton(
            pat_skel[2], ("ATOM", m.group(2)), bindings, m.group(2)
        )

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
            sid = str(rule.get("skill_id") or "")
            if sid and sid in seen_skills:
                continue
            seen_skills.add(sid)
            for cand in iter_cst_skeleton_candidates(source_text, rule, target_language=tgt):
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
