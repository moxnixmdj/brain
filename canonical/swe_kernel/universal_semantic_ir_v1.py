#!/usr/bin/env python3
"""Universal Semantic Meaning Graph (U-IR), Interprocedural Causal Lineage Graph,
and External Inspectable Semantic Causal Law Store.

Design laws:
1. Meaning, not spelling: lowers Python, C/C++, JavaScript/TypeScript, Rust, and Go
   concrete syntax trees into one canonical data/control-flow U-IR so semantically
   equivalent constructs (e.g. `for (int i=0; i<=n; i++)`, `while (ptr <= end)`,
   `for i in range(len(xs) + 1)`) map to the identical U-IR defect signature.
2. Interprocedural cause & effect: traces value/call/import lineage across files
   and computes transitive test impact cones so edits never fix one file by breaking
   its neighbors.
3. Zero world-fact weights, zero model calls: laws live in an inspectable, editable
   JSON store (`BRAIN_SEMANTIC_CAUSAL_LAWS_V1`), admitted only after sabotage and
   contrast verification, and surgically removable in O(1) without retraining.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import asdict, dataclass, field
import difflib
import hashlib
import json
import pathlib
import re
from typing import Any

from canonical.runtime.tree_sitter_swe_kernel_v1 import (
    IGNORED_DIRS,
    detect_language,
    parse_bytes,
    source_files,
)
from canonical.swe_kernel.effect_contract_composition_v1 import (
    EffectContract,
    PASS as CONTRACT_COMPATIBLE,
    UNDO as CONTRACT_EFFECT_UNDO,
    check_complete as check_effect_contract_complete,
    compose_contracts,
)

UIR_SCHEMA_VERSION = "BRAIN_UNIVERSAL_SEMANTIC_IR_V1"
LAW_STORE_SCHEMA = "BRAIN_SEMANTIC_CAUSAL_LAWS_V1"

DEFAULT_LAW_STORE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "astra_runtime"
    / "state"
    / "SEMANTIC_CAUSAL_LAWS_V1.json"
)


@dataclass(frozen=True)
class UIRNode:
    kind: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    roles: dict[str, Any] = field(default_factory=dict)


@dataclass
class UIRFunction:
    name: str
    rel_path: str
    language: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    params: list[str]
    return_hint: str
    calls: list[tuple[str, int]]
    nodes: list[UIRNode]
    semantic_fingerprint: str = ""


@dataclass(frozen=True)
class CausalCutSite:
    rel_path: str
    func_name: str
    language: str
    start_line: int
    end_line: int
    hop_distance: int
    causal_reason: str
    score: float


@dataclass
class SemanticCausalLaw:
    law_id: str
    defect_uir_kind: str
    transform_operator: str
    precondition_signature: dict[str, Any]
    learned_from_language: str
    sabotage_verified: bool
    contrast_verified: bool
    evidence_digest: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_effect_contract(self) -> EffectContract:
        """Build a declarative (P, O, A, V, F) EffectContract for static composition verification."""
        ec = self.precondition_signature.get("effect_contract")
        if isinstance(ec, dict):
            return EffectContract.of(
                self.law_id,
                preconditions=ec.get("P") or [f"{self.defect_uir_kind}:{self.transform_operator}:PRE"],
                observables=ec.get("O") or ["UIR_AST_SKELETON", "DATAFLOW_HOLES", "IMPACT_CONE_TESTS"],
                actions=ec.get("A") or [self.transform_operator],
                verdict=str(ec.get("V") or "PYTEST_IMPACT_CONE_AND_COW_BOUNDARY_FUZZ"),
                effects=[
                    *[("REMOVE", s) for s in (ec.get("F_remove") or [])],
                    *[("ESTABLISH", s) for s in (ec.get("F_establish") or [])],
                ]
                or [
                    ("REMOVE", f"DEFECT:{self.defect_uir_kind}:{json.dumps(self.precondition_signature, sort_keys=True)}"),
                    ("ESTABLISH", f"REPAIRED:{self.defect_uir_kind}:{self.transform_operator}"),
                ],
            )
        pre_key = f"DEFECT:{self.defect_uir_kind}:{json.dumps(self.precondition_signature, sort_keys=True)}"
        post_key = f"REPAIRED:{self.defect_uir_kind}:{self.transform_operator}"
        return EffectContract.of(
            self.law_id,
            preconditions=[pre_key],
            observables=[self.defect_uir_kind, "IMPACT_CONE_TESTS"],
            actions=[self.transform_operator],
            verdict="PYTEST_IMPACT_CONE_AND_COW_BOUNDARY_FUZZ",
            effects=[("REMOVE", pre_key), ("ESTABLISH", post_key)],
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SemanticCausalLaw:
        return cls(
            law_id=str(raw["law_id"]),
            defect_uir_kind=str(raw["defect_uir_kind"]),
            transform_operator=str(raw["transform_operator"]),
            precondition_signature=dict(raw.get("precondition_signature") or {}),
            learned_from_language=str(raw.get("learned_from_language") or "unknown"),
            sabotage_verified=bool(raw.get("sabotage_verified", False)),
            contrast_verified=bool(raw.get("contrast_verified", False)),
            evidence_digest=str(raw.get("evidence_digest") or ""),
            metadata=dict(raw.get("metadata") or {}),
        )


def _node_text(raw: bytes, node: Any) -> str:
    return raw[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _walk_ts(node: Any):
    stack = [node]
    while stack:
        cur = stack.pop()
        yield cur
        children = getattr(cur, "children", None) or []
        for ch in reversed(children):
            stack.append(ch)


def _extract_identifiers(raw: bytes, node: Any) -> list[str]:
    out: list[str] = []
    for sub in _walk_ts(node):
        if sub.type in {"identifier", "field_identifier", "property_identifier"}:
            txt = _node_text(raw, sub).strip()
            if txt:
                out.append(txt)
    return out


_NULL_CHECK_RE = re.compile(
    r"(?:\bNULL\b|\bnullptr\b|\bNone\b|\bnil\b|\bnull\b|\bundefined\b|\.is_none\(\)|\.is_some\(\))"
)


def _body_derefs_cursor(body_text: str, cursor_names: set[str], ptr_mode: bool = False) -> bool:
    if ptr_mode:
        for c in cursor_names:
            if re.search(rf"\*\s*{re.escape(c)}\b|\b{re.escape(c)}\s*\[|\b{re.escape(c)}\s*->", body_text):
                return True
    for c in cursor_names:
        if re.search(rf"\[\s*{re.escape(c)}(?:\s*[\+\-]\s*0)?\s*\]", body_text):
            return True
    return False


def _infer_default_return_expr(func_text: str, language: str, header_text: str) -> str:
    returns = re.findall(r"\breturn\s+([^;\n]+)", func_text)
    if language == "cpp":
        hdr = header_text.strip()
        if re.search(r"(?:\*\s*[A-Za-z_]\w*\s*\(|\(\s*[^)]*\*\s*\)\s*[A-Za-z_]\w*\s*\()", hdr):
            return "NULL"
        if re.search(r"(?:^(?:static\s+|inline\s+)*void\b|\(\s*void\s*\)\s*[A-Za-z_]\w*\s*\()", hdr):
            return ""
        if re.search(r"(?:^(?:static\s+|inline\s+)*(?:bool|cJSON_bool)\b|\(\s*(?:bool|cJSON_bool)\s*\)\s*[A-Za-z_]\w*\s*\()", hdr):
            return "false"
        if re.search(r"(?:^(?:static\s+|inline\s+)*double\b|\(\s*double\s*\)\s*[A-Za-z_]\w*\s*\()", hdr):
            return "(double)NAN" if "NAN" in func_text else '__builtin_nan("")'
        for r in returns:
            rs = r.strip()
            if rs in {"NULL", "nullptr", "-1", "0", "false", "(cJSON_bool)false", "0.0"}:
                return rs
        return "0"
    if language == "python":
        for r in returns:
            rs = r.strip()
            if rs in {"None", "False", "0", "[]", "()", '""', "''", "{}"}:
                return rs
        return "None"
    if language in {"javascript", "typescript"}:
        for r in returns:
            rs = r.strip()
            if rs in {"null", "undefined", "false", "0", "[]", '""', "''"}:
                return rs
        return "null"
    if language == "rust":
        if "Option<" in header_text:
            return "None"
        return "0"
    if language == "go":
        return "nil"
    return "None"


def _compute_uir_fingerprint(nodes: list[UIRNode]) -> str:
    canonical_seq = []
    for n in sorted(nodes, key=lambda x: (x.start_byte, x.kind)):
        filtered_roles = {
            k: v
            for k, v in sorted(n.roles.items())
            if k
            in {
                "bound_polarity",
                "body_derefs_cursor",
                "guard_kind",
                "dominated_by_null_guard",
                "dominated_by_nonzero_guard",
                "multipass_unmaterialized",
                "mutable_alias_escape",
            }
        }
        canonical_seq.append({"kind": n.kind, "roles": filtered_roles})
    payload = json.dumps(canonical_seq, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def lower_source_to_uir(
    source_bytes: bytes,
    language: str,
    rel_path: str = "<memory>",
) -> list[UIRFunction]:
    """Lower source bytes in Python, C/C++, JS/TS, Rust, or Go into canonical U-IR functions."""
    norm_lang = "cpp" if language in {"c", "cpp", "c++"} else language
    try:
        tree = parse_bytes(norm_lang, source_bytes)
        root = tree.root_node
    except Exception:
        if norm_lang != "python":
            return []
        src_str = source_bytes.decode("utf-8", errors="replace")
        py_lines = src_str.splitlines(keepends=True)
        py_offsets: list[int] = [0]
        for ln in py_lines:
            py_offsets.append(py_offsets[-1] + len(ln.encode("utf-8")))
        try:
            mod_ast = ast.parse(src_str)
        except SyntaxError:
            return []
        fallback_fns: list[UIRFunction] = []
        for a_node in ast.walk(mod_ast):
            if not isinstance(a_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            st_ln = a_node.lineno
            en_ln = getattr(a_node, "end_lineno", st_ln) or st_ln
            sb = py_offsets[st_ln - 1] if st_ln - 1 < len(py_offsets) else 0
            eb = py_offsets[min(en_ln, len(py_offsets) - 1)]
            params = [arg.arg for arg in a_node.args.args if arg.arg not in {"self", "cls"}]
            calls: list[tuple[str, int]] = []
            for sub in ast.walk(a_node):
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Name):
                        calls.append((sub.func.id, getattr(sub, "lineno", st_ln)))
                    elif isinstance(sub.func, ast.Attribute):
                        calls.append((sub.func.attr, getattr(sub, "lineno", st_ln)))
            uir_nodes: list[UIRNode] = []
            _augment_python_value_flow_uir(a_node, source_bytes, uir_nodes, py_lines, py_offsets)
            u_fn = UIRFunction(
                name=a_node.name,
                rel_path=rel_path,
                language="python",
                start_line=st_ln,
                end_line=en_ln,
                start_byte=sb,
                end_byte=eb,
                params=params,
                return_hint="None",
                calls=calls,
                nodes=uir_nodes,
            )
            u_fn.semantic_fingerprint = _compute_uir_fingerprint(uir_nodes)
            fallback_fns.append(u_fn)
        return fallback_fns

    func_node_types = {
        "function_definition",
        "method_definition",
        "function_declaration",
        "method_declaration",
        "function_item",
    }

    py_ast_by_name_line: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    py_line_offsets: list[int] = [0]
    py_lines: list[str] = []
    if norm_lang == "python":
        src_str = source_bytes.decode("utf-8", errors="replace")
        py_lines = src_str.splitlines(keepends=True)
        for ln in py_lines:
            py_line_offsets.append(py_line_offsets[-1] + len(ln.encode("utf-8")))
        try:
            mod_ast = ast.parse(src_str)
            for a_node in ast.walk(mod_ast):
                if isinstance(a_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    py_ast_by_name_line.setdefault(a_node.name, []).append(a_node)
        except SyntaxError:
            pass

    functions: list[UIRFunction] = []
    for fn_node in _walk_ts(root):
        if fn_node.type not in func_node_types:
            continue
        # Skip nested closures inside functions for top-level function extraction if desired,
        # except methods inside classes which we DO want.
        fn_text = _node_text(source_bytes, fn_node)
        fn_name = "<anonymous>"
        params: list[str] = []
        header_end = fn_node.end_byte
        body_node = None
        for ch in fn_node.children:
            if ch.type in {"identifier", "field_identifier", "property_identifier"} and fn_name == "<anonymous>":
                fn_name = _node_text(source_bytes, ch).strip()
            elif ch.type == "function_declarator":
                decl_name = ""
                decl_params: list[str] = []
                for sub in ch.children:
                    if sub.type in {"identifier", "field_identifier"} and not decl_name:
                        decl_name = _node_text(source_bytes, sub).strip()
                    elif sub.type == "parameter_list":
                        for p in sub.children:
                            pids = _extract_identifiers(source_bytes, p)
                            if pids:
                                decl_params.append(pids[-1])
                    elif sub.type == "pointer_declarator":
                        pids = _extract_identifiers(source_bytes, sub)
                        if pids and not decl_name:
                            decl_name = pids[0]
                if decl_name:
                    fn_name = decl_name
                    params = decl_params
            elif ch.type == "pointer_declarator":
                for sub in _walk_ts(ch):
                    if sub.type == "function_declarator":
                        decl_name = ""
                        decl_params = []
                        for s2 in sub.children:
                            if s2.type in {"identifier", "field_identifier"} and not decl_name:
                                decl_name = _node_text(source_bytes, s2).strip()
                            elif s2.type == "parameter_list":
                                for p in s2.children:
                                    pids = _extract_identifiers(source_bytes, p)
                                    if pids:
                                        decl_params.append(pids[-1])
                        if decl_name:
                            fn_name = decl_name
                            params = decl_params
            elif ch.type in {"parameters", "formal_parameters", "parameter_list"}:
                for p in ch.children:
                    pids = _extract_identifiers(source_bytes, p)
                    if pids:
                        params.append(pids[-1] if norm_lang == "cpp" else pids[0])
            elif ch.type in {"block", "compound_statement", "statement_block"}:
                body_node = ch
                header_end = ch.start_byte

        if body_node is None:
            continue

        hdr_start = max(0, fn_node.start_byte - 48) if norm_lang == "cpp" else fn_node.start_byte
        header_text = source_bytes[hdr_start : header_end].decode("utf-8", errors="replace")
        default_ret = _infer_default_return_expr(fn_text, norm_lang, header_text)

        uir_nodes: list[UIRNode] = []
        calls: list[tuple[str, int]] = []
        null_guarded_vars: set[str] = set()
        scoped_null_guards: list[tuple[str, int, int]] = []
        nonzero_guarded_vars: set[str] = set()

        def _is_null_dominated(expr: str, ln: int) -> bool:
            if expr in null_guarded_vars:
                return True
            return any(g_expr == expr and gs <= ln <= ge for g_expr, gs, ge in scoped_null_guards)

        # Pass 1: collect calls, guards, loops, exception boundaries
        for sub in _walk_ts(body_node):
            st_line = sub.start_point[0] + 1
            en_line = sub.end_point[0] + 1

            # Calls
            if sub.type in {"call", "call_expression"}:
                callee_node = sub.children[0] if sub.children else None
                if callee_node is not None:
                    callee_txt = _node_text(source_bytes, callee_node).strip()
                    short_callee = callee_txt.split(".")[-1].split("->")[-1].split("::")[-1]
                    if short_callee:
                        calls.append((short_callee, st_line))

            # Guards (if / conditional)
            if sub.type in {"if_statement", "if_expression", "conditional_expression"}:
                cond_node = sub.child_by_field_name("condition")
                if cond_node is None and len(sub.children) >= 2:
                    cond_node = sub.children[1] if sub.type == "if_statement" else sub.children[0]
                if cond_node is not None:
                    cond_txt = _node_text(source_bytes, cond_node).strip()
                    stripped_cond = cond_txt
                    if stripped_cond.startswith("(") and stripped_cond.endswith(")"):
                        stripped_cond = stripped_cond[1:-1].strip()
                    cond_ids = _extract_identifiers(source_bytes, cond_node)
                    sub_txt = _node_text(source_bytes, sub)
                    has_early_exit = bool(re.search(r"\b(?:return|break|continue|raise|throw|goto)\b", sub_txt))

                    if _NULL_CHECK_RE.search(stripped_cond) or (
                        norm_lang == "cpp" and re.match(r"^!\s*[A-Za-z_][\w\.\->]*$", stripped_cond)
                    ):
                        guard_kind = "EXISTENCE_CHECK"
                        null_exprs: list[str] = []
                        for m_ne in re.finditer(
                            r"(?:([A-Za-z_][\w\.\->]*)\s*(?:==|!=|===|!==|\bis\s+not\b|\bis\b)\s*(?:NULL|nullptr|None|null|undefined)\b"
                            r"|\b(?:NULL|nullptr|None|null|undefined)\s*(?:==|!=|===|!==)\s*([A-Za-z_][\w\.\->]*)"
                            r"|!\s*\(?\s*([A-Za-z_][\w\.\->]*)\s*\)?)",
                            stripped_cond,
                        ):
                            g_ex = (m_ne.group(1) or m_ne.group(2) or m_ne.group(3) or "").strip()
                            if g_ex and g_ex not in {"NULL", "nullptr", "None", "null", "undefined", "nil"}:
                                null_exprs.append(g_ex)
                        if not null_exprs:
                            null_exprs = [
                                cid for cid in cond_ids
                                if cid not in {"NULL", "nullptr", "None", "null", "undefined", "nil"}
                            ]
                        for g_ex in null_exprs:
                            if has_early_exit:
                                null_guarded_vars.add(g_ex)
                            else:
                                scoped_null_guards.append((g_ex, st_line, en_line))
                    elif re.match(r"^(?:not\s+|!\s*)?[A-Za-z_][\w\.]*$", stripped_cond):
                        guard_kind = "TRUTHINESS_CHECK"
                        if has_early_exit and norm_lang in {"cpp", "javascript", "typescript"}:
                            for cid in cond_ids:
                                null_guarded_vars.add(cid)
                    elif re.search(r"(?:!=|==)\s*0\b", stripped_cond):
                        guard_kind = "NONZERO_CHECK"
                        for cid in cond_ids:
                            nonzero_guarded_vars.add(cid)
                    else:
                        guard_kind = "RELATIONAL_OR_COMPOUND"
                        if re.search(r"!=|==|<|>=", stripped_cond):
                            for cid in cond_ids:
                                if "0" in stripped_cond:
                                    nonzero_guarded_vars.add(cid)

                    uir_nodes.append(
                        UIRNode(
                            kind="UIR_GUARD",
                            start_line=st_line,
                            end_line=en_line,
                            start_byte=cond_node.start_byte,
                            end_byte=cond_node.end_byte,
                            roles={
                                "guard_kind": guard_kind,
                                "subject_vars": cond_ids[:4],
                                "cond_text": stripped_cond,
                                "has_early_exit": has_early_exit,
                            },
                        )
                    )

            # Loops -> UIR_ITER_BOUNDED
            if sub.type in {
                "for_statement",
                "for_in_statement",
                "while_statement",
                "for_expression",
            }:
                loop_txt = _node_text(source_bytes, sub)
                bound_polarity = "UNKNOWN"
                cursor_vars: set[str] = set()
                cond_span = (sub.start_byte, sub.end_byte)
                ptr_mode = False
                loop_style = sub.type

                if norm_lang == "python" and sub.type == "for_statement":
                    # e.g. `for i in range(len(xs) + 1):` or `for i in range(n):`
                    m_rng = re.search(
                        r"for\s+([A-Za-z_]\w*)\s+in\s+(range\s*\(([^\n:]+)\))\s*:",
                        loop_txt,
                    )
                    if m_rng:
                        cursor_vars.add(m_rng.group(1))
                        rng_call = m_rng.group(2)
                        rng_arg = m_rng.group(3).strip()
                        rel_off = loop_txt.find(rng_call)
                        if rel_off >= 0:
                            cond_span = (sub.start_byte + rel_off, sub.start_byte + rel_off + len(rng_call))
                        loop_style = "PY_RANGE_FOR"
                        if re.search(r"\blen\s*\([^)]+\)\s*\+\s*1\b|\+\s*1\s*$", rng_arg):
                            bound_polarity = "INCLUSIVE_LE"
                        else:
                            bound_polarity = "STRICT_LT"
                elif norm_lang == "rust" and sub.type == "for_expression":
                    m_rs = re.search(r"for\s+([A-Za-z_]\w*)\s+in\s+([^\n\{]+)\{", loop_txt)
                    if m_rs:
                        cursor_vars.add(m_rs.group(1))
                        rng_expr = m_rs.group(2).strip()
                        rel_off = loop_txt.find(rng_expr)
                        if rel_off >= 0:
                            cond_span = (sub.start_byte + rel_off, sub.start_byte + rel_off + len(rng_expr))
                        loop_style = "RUST_RANGE_FOR"
                        bound_polarity = "INCLUSIVE_LE" if "..=" in rng_expr else "STRICT_LT"
                else:
                    # C / JS / Go / Python while or C-style for
                    cond_node = sub.child_by_field_name("condition")
                    if cond_node is None:
                        for ch in sub.children:
                            if ch.type in {"parenthesized_expression", "binary_expression", "comparison_operator"}:
                                cond_node = ch
                                break
                    if cond_node is not None:
                        cond_txt = _node_text(source_bytes, cond_node).strip()
                        cond_span = (cond_node.start_byte, cond_node.end_byte)
                        m_cmp = re.search(r"([A-Za-z_]\w*)\s*(<=|<)\s*([^;)\n]+)", cond_txt)
                        if m_cmp:
                            cursor_vars.add(m_cmp.group(1))
                            op = m_cmp.group(2)
                            bound_polarity = "INCLUSIVE_LE" if op == "<=" else "STRICT_LT"
                            cvar = re.escape(m_cmp.group(1))
                            if re.search(rf"\*\s*{cvar}\b|\b{cvar}\s*->", loop_txt):
                                ptr_mode = True
                            loop_style = "PTR_WHILE" if ptr_mode else ("C_FOR" if "for" in sub.type else "INDEX_WHILE")

                if bound_polarity != "UNKNOWN":
                    # Find loop body text
                    lbody = sub.children[-1] if sub.children else sub
                    lbody_txt = _node_text(source_bytes, lbody)
                    derefs = _body_derefs_cursor(lbody_txt, cursor_vars, ptr_mode=ptr_mode)
                    uir_nodes.append(
                        UIRNode(
                            kind="UIR_ITER_BOUNDED",
                            start_line=st_line,
                            end_line=en_line,
                            start_byte=cond_span[0],
                            end_byte=cond_span[1],
                            roles={
                                "loop_style": loop_style,
                                "bound_polarity": bound_polarity,
                                "body_derefs_cursor": derefs,
                                "cursor_vars": sorted(cursor_vars),
                                "cond_text": source_bytes[cond_span[0] : cond_span[1]].decode("utf-8", errors="replace"),
                            },
                        )
                    )

            # Dereferences / loads -> UIR_DEREF_LOAD
            if sub.type in {"subscript", "subscript_expression", "index_expression"}:
                txt = _node_text(source_bytes, sub).strip()
                base_var = txt.split("[", 1)[0].strip("()* ")
                if base_var and re.match(r"^[A-Za-z_]\w*$", base_var) and base_var not in {"self", "cls", "this"}:
                    uir_nodes.append(
                        UIRNode(
                            kind="UIR_DEREF_LOAD",
                            start_line=st_line,
                            end_line=en_line,
                            start_byte=sub.start_byte,
                            end_byte=sub.end_byte,
                            roles={
                                "base_var": base_var,
                                "deref_op": "INDEX",
                                "dominated_by_null_guard": _is_null_dominated(base_var, st_line),
                                "default_return": default_ret,
                            },
                        )
                    )
            elif norm_lang == "cpp" and sub.type in {"field_expression", "pointer_expression"}:
                txt = _node_text(source_bytes, sub).strip()
                if sub.type == "field_expression" and "->" in txt:
                    base_var = txt.split("->", 1)[0].strip("()* ")
                    if base_var and re.match(r"^[A-Za-z_]\w*$", base_var):
                        uir_nodes.append(
                            UIRNode(
                                kind="UIR_DEREF_LOAD",
                                start_line=st_line,
                                end_line=en_line,
                                start_byte=sub.start_byte,
                                end_byte=sub.end_byte,
                                roles={
                                    "base_var": base_var,
                                    "deref_op": "ARROW",
                                    "dominated_by_null_guard": _is_null_dominated(base_var, st_line),
                                    "default_return": default_ret,
                                },
                            )
                        )
                    prefix_expr = txt.rsplit("->", 1)[0].strip("()* ")
                    if "->" in prefix_expr and re.match(r"^[A-Za-z_]\w*(?:->[A-Za-z_]\w*)+$", prefix_expr):
                        uir_nodes.append(
                            UIRNode(
                                kind="UIR_DEREF_LOAD",
                                start_line=st_line,
                                end_line=en_line,
                                start_byte=sub.start_byte,
                                end_byte=sub.end_byte,
                                roles={
                                    "base_var": prefix_expr,
                                    "deref_op": "CHAINED_ARROW",
                                    "dominated_by_null_guard": _is_null_dominated(prefix_expr, st_line),
                                    "default_return": default_ret,
                                },
                            )
                        )
                elif sub.type == "pointer_expression" and txt.startswith("*"):
                    base_var = txt[1:].strip("() ")
                    if base_var and re.match(r"^[A-Za-z_]\w*$", base_var):
                        uir_nodes.append(
                            UIRNode(
                                kind="UIR_DEREF_LOAD",
                                start_line=st_line,
                                end_line=en_line,
                                start_byte=sub.start_byte,
                                end_byte=sub.end_byte,
                                roles={
                                    "base_var": base_var,
                                    "deref_op": "STAR",
                                    "dominated_by_null_guard": _is_null_dominated(base_var, st_line),
                                    "default_return": default_ret,
                                },
                            )
                        )
            elif norm_lang in {"python", "javascript", "typescript"} and sub.type in {"attribute", "member_expression"}:
                txt = _node_text(source_bytes, sub).strip()
                if "." in txt:
                    base_var, attr_name = txt.split(".", 1)
                    base_var = base_var.strip()
                    if (
                        base_var in params
                        and base_var not in {"self", "cls", "this"}
                        and attr_name.strip() not in {"length", "len"}
                    ):
                        uir_nodes.append(
                            UIRNode(
                                kind="UIR_DEREF_LOAD",
                                start_line=st_line,
                                end_line=en_line,
                                start_byte=sub.start_byte,
                                end_byte=sub.end_byte,
                                roles={
                                    "base_var": base_var,
                                    "deref_op": "ATTR",
                                    "dominated_by_null_guard": base_var in null_guarded_vars,
                                    "default_return": default_ret,
                                },
                            )
                        )

            # Division / modulo -> UIR_DIV_OP
            if sub.type in {"binary_operator", "binary_expression"} and len(sub.children) >= 3:
                op_txt = _node_text(source_bytes, sub.children[1]).strip()
                if op_txt in {"/", "//", "%"}:
                    rhs_txt = _node_text(source_bytes, sub.children[2]).strip("() ")
                    if re.match(r"^[A-Za-z_]\w*$", rhs_txt):
                        uir_nodes.append(
                            UIRNode(
                                kind="UIR_DIV_OP",
                                start_line=st_line,
                                end_line=en_line,
                                start_byte=sub.start_byte,
                                end_byte=sub.end_byte,
                                roles={
                                    "divisor_var": rhs_txt,
                                    "op": op_txt,
                                    "dominated_by_nonzero_guard": rhs_txt in nonzero_guarded_vars,
                                    "default_return": default_ret,
                                },
                            )
                        )

            # Exception boundary -> UIR_EXCEPT_BOUNDARY
            if norm_lang == "python" and sub.type == "except_clause":
                exc_txt = _node_text(source_bytes, sub)
                m_exc = re.match(r"except\s+(\([^)]+\)|[A-Za-z_][\w\.]*)", exc_txt)
                if m_exc:
                    spec_str = m_exc.group(1)
                    rel_off = exc_txt.find(spec_str)
                    uir_nodes.append(
                        UIRNode(
                            kind="UIR_EXCEPT_BOUNDARY",
                            start_line=st_line,
                            end_line=en_line,
                            start_byte=sub.start_byte + rel_off,
                            end_byte=sub.start_byte + rel_off + len(spec_str),
                            roles={"caught_spec": spec_str},
                        )
                    )

        # Python AST pass for deep value-flow semantics (multipass iterators & escaping mutable aliases)
        if norm_lang == "python":
            for a_node in py_ast_by_name_line.get(fn_name, ()):
                if abs(a_node.lineno - (fn_node.start_point[0] + 1)) <= 3:
                    _augment_python_value_flow_uir(a_node, source_bytes, uir_nodes, py_lines, py_line_offsets)

        u_fn = UIRFunction(
            name=fn_name,
            rel_path=rel_path,
            language=norm_lang,
            start_line=fn_node.start_point[0] + 1,
            end_line=fn_node.end_point[0] + 1,
            start_byte=fn_node.start_byte,
            end_byte=fn_node.end_byte,
            params=params,
            return_hint=default_ret,
            calls=calls,
            nodes=uir_nodes,
        )
        u_fn.semantic_fingerprint = _compute_uir_fingerprint(uir_nodes)
        functions.append(u_fn)

    return functions


def _augment_python_value_flow_uir(
    fn_ast: ast.FunctionDef | ast.AsyncFunctionDef,
    source_bytes: bytes,
    uir_nodes: list[UIRNode],
    precomputed_lines: list[str] | None = None,
    precomputed_offsets: list[int] | None = None,
) -> None:
    if precomputed_lines is not None and precomputed_offsets is not None:
        lines = precomputed_lines
        line_offsets = precomputed_offsets
    else:
        lines = source_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
        line_offsets = [0]
        for ln in lines:
            line_offsets.append(line_offsets[-1] + len(ln.encode("utf-8")))

    def _span_bytes(node: ast.AST) -> tuple[int, int]:
        sl = getattr(node, "lineno", 1) - 1
        sc = getattr(node, "col_offset", 0)
        el = getattr(node, "end_lineno", sl + 1) - 1
        ec = getattr(node, "end_col_offset", sc)
        sb = line_offsets[sl] + len(lines[sl][:sc].encode("utf-8")) if sl < len(lines) else 0
        eb = line_offsets[el] + len(lines[el][:ec].encode("utf-8")) if el < len(lines) else sb
        return sb, eb

    # Track local assignments `x = call(...)` and count downstream iterations/uses,
    # plus mutable list/dict/set locals returned alongside another reference to the same local.
    call_assigned: dict[str, ast.Assign] = {}
    mutable_locals: set[str] = set()
    for stmt in ast.walk(fn_ast):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            vname = stmt.targets[0].id
            if isinstance(stmt.value, ast.Call):
                cname = ast.unparse(stmt.value.func) if hasattr(ast, "unparse") else ""
                if cname not in {"list", "tuple", "set", "dict", "frozenset"}:
                    call_assigned[vname] = stmt
                if cname in {"list", "dict", "set"}:
                    mutable_locals.add(vname)
            elif isinstance(stmt.value, (ast.List, ast.Dict, ast.Set, ast.ListComp)):
                mutable_locals.add(vname)
        elif isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Attribute):
            if stmt.func.attr in {"append", "extend", "pop", "insert", "remove", "update", "add"}:
                if isinstance(stmt.func.value, ast.Name):
                    mutable_locals.add(stmt.func.value.id)

    for vname, assign_stmt in call_assigned.items():
        # Count distinct consumption sites (for-loop targets, comprehensions, unpacking, multi-call args)
        uses = 0
        for sub in ast.walk(fn_ast):
            if sub is assign_stmt or sub is assign_stmt.targets[0]:
                continue
            if isinstance(sub, ast.Name) and sub.id == vname and isinstance(sub.ctx, ast.Load):
                uses += 1
        if uses >= 2:
            sb, eb = _span_bytes(assign_stmt.value)
            uir_nodes.append(
                UIRNode(
                    kind="UIR_VALUE_FLOW",
                    start_line=assign_stmt.lineno,
                    end_line=getattr(assign_stmt, "end_lineno", assign_stmt.lineno),
                    start_byte=sb,
                    end_byte=eb,
                    roles={
                        "var_name": vname,
                        "multipass_unmaterialized": True,
                        "mutable_alias_escape": False,
                        "expr_text": source_bytes[sb:eb].decode("utf-8", errors="replace"),
                    },
                )
            )

    for sub in ast.walk(fn_ast):
        if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Tuple) and len(sub.value.elts) >= 2:
            elt_names_per_slot: list[set[str]] = []
            for elt in sub.value.elts:
                names = {n.id for n in ast.walk(elt) if isinstance(n, ast.Name)}
                elt_names_per_slot.append(names)
            for idx, elt in enumerate(sub.value.elts):
                if isinstance(elt, ast.Name) and elt.id in mutable_locals:
                    other_mentions = any(
                        elt.id in elt_names_per_slot[j]
                        for j in range(len(sub.value.elts))
                        if j != idx
                    )
                    if other_mentions:
                        sb, eb = _span_bytes(elt)
                        uir_nodes.append(
                            UIRNode(
                                kind="UIR_VALUE_FLOW",
                                start_line=sub.lineno,
                                end_line=getattr(sub, "end_lineno", sub.lineno),
                                start_byte=sb,
                                end_byte=eb,
                                roles={
                                    "var_name": elt.id,
                                    "multipass_unmaterialized": False,
                                    "mutable_alias_escape": True,
                                    "expr_text": source_bytes[sb:eb].decode("utf-8", errors="replace"),
                                },
                            )
                        )


class InterproceduralCausalGraph:
    """Fast multi-language cross-file call, import/include, and U-IR lineage graph."""

    def __init__(self, repo_root: pathlib.Path, *, max_files: int = 1200) -> None:
        self.repo_root = pathlib.Path(repo_root).resolve()
        self.functions_by_file: dict[str, list[UIRFunction]] = {}
        self.symbol_defs: dict[str, list[UIRFunction]] = {}
        self.call_edges: dict[tuple[str, str], list[tuple[str, str, int]]] = {}
        self.reverse_callers: dict[tuple[str, str], list[tuple[str, str, int]]] = {}
        self.file_imports: dict[str, set[str]] = {}
        self.reverse_importers: dict[str, set[str]] = {}
        self._build(max_files=max_files)

    def _build(self, *, max_files: int) -> None:
        try:
            files = source_files(self.repo_root, max_files=max_files)
        except Exception:
            files = []
            for p in sorted(self.repo_root.rglob("*")):
                if any(part in IGNORED_DIRS for part in p.parts):
                    continue
                if p.is_file() and not p.is_symlink() and detect_language(p):
                    files.append(p)
                    if len(files) >= max_files:
                        break

        rel_by_stem: dict[str, list[str]] = {}
        all_rels: set[str] = set()
        for fpath in files:
            rel = fpath.resolve().relative_to(self.repo_root).as_posix()
            all_rels.add(rel)
            rel_by_stem.setdefault(fpath.stem, []).append(rel)
            rel_by_stem.setdefault(fpath.name, []).append(rel)

        raw_cache: dict[str, tuple[str, bytes]] = {}
        for fpath in files:
            lang = detect_language(fpath)
            if not lang or lang == "yaml":
                continue
            rel = fpath.resolve().relative_to(self.repo_root).as_posix()
            if rel.startswith(("docs/", "doc/", "examples/", "benchmarks/")):
                continue
            try:
                raw = fpath.read_bytes()
            except OSError:
                continue
            if len(raw) > 800_000:
                continue
            raw_cache[rel] = (lang, raw)
            if _is_test_rel_path(rel):
                self.functions_by_file[rel] = []
                continue
            try:
                u_fns = lower_source_to_uir(raw, lang, rel_path=rel)
            except Exception:
                u_fns = []
            self.functions_by_file[rel] = u_fns
            for ufn in u_fns:
                self.symbol_defs.setdefault(ufn.name, []).append(ufn)

        # Resolve cross-file imports / #includes and call graph edges
        for rel, (lang, raw) in raw_cache.items():
            txt = raw.decode("utf-8", errors="replace")
            imports: set[str] = set()
            if lang == "python":
                for m in re.finditer(r"^\s*(?:from|import)\s+([.\w]+)", txt, re.M):
                    mod = m.group(1).lstrip(".")
                    parts = mod.split(".")
                    if parts and parts[-1] in rel_by_stem:
                        for cand in rel_by_stem[parts[-1]]:
                            if cand != rel:
                                imports.add(cand)
                    candidate_rel = "/".join(parts) + ".py"
                    for existing in all_rels:
                        if existing.endswith(candidate_rel) and existing != rel:
                            imports.add(existing)
            elif lang == "cpp":
                for m in re.finditer(r'#\s*include\s*["<]([^">]+)[">]', txt):
                    inc_name = pathlib.Path(m.group(1)).name
                    inc_stem = pathlib.Path(inc_name).stem
                    for cand in rel_by_stem.get(inc_name, []) + rel_by_stem.get(inc_stem, []):
                        if cand != rel:
                            imports.add(cand)
            elif lang in {"javascript", "typescript"}:
                for m in re.finditer(r"""(?:from|require\s*\()\s*['"]([^'"]+)['"]""", txt):
                    spec = pathlib.Path(m.group(1)).stem
                    for cand in rel_by_stem.get(spec, []):
                        if cand != rel:
                            imports.add(cand)

            self.file_imports[rel] = imports
            for target in imports:
                self.reverse_importers.setdefault(target, set()).add(rel)

        for rel, u_fns in self.functions_by_file.items():
            imported_files = self.file_imports.get(rel, set())
            for ufn in u_fns:
                caller_key = (rel, ufn.name)
                for callee_name, call_line in ufn.calls:
                    defs = self.symbol_defs.get(callee_name, [])
                    if not defs:
                        continue
                    # Prefer definitions in same file or imported/header-linked files
                    ranked_defs = sorted(
                        defs,
                        key=lambda d: (
                            0 if d.rel_path == rel else (1 if d.rel_path in imported_files else 2),
                            d.rel_path,
                        ),
                    )
                    for target_fn in ranked_defs[:3]:
                        callee_key = (target_fn.rel_path, target_fn.name)
                        self.call_edges.setdefault(caller_key, []).append(
                            (target_fn.rel_path, target_fn.name, call_line)
                        )
                        self.reverse_callers.setdefault(callee_key, []).append(
                            (rel, ufn.name, call_line)
                        )

    def find_enclosing_function(self, rel_path: str, line_no: int) -> UIRFunction | None:
        for ufn in self.functions_by_file.get(rel_path, []):
            if ufn.start_line <= line_no <= ufn.end_line:
                return ufn
        return None

    def trace_backward_causal_slice(
        self,
        anchors: list[tuple[str, int]],
        *,
        max_hops: int = 4,
    ) -> list[CausalCutSite]:
        """Walks both callees (producers of corrupted values) and callers (producers of
        bad arguments) across files starting from crash/failure anchors."""
        visited: dict[tuple[str, str], CausalCutSite] = {}
        frontier: list[tuple[str, str, int, str]] = []

        for rel_path, line_no in anchors:
            ufn = self.find_enclosing_function(rel_path, line_no)
            if ufn is not None:
                key = (rel_path, ufn.name)
                if key not in visited:
                    visited[key] = CausalCutSite(
                        rel_path=rel_path,
                        func_name=ufn.name,
                        language=ufn.language,
                        start_line=ufn.start_line,
                        end_line=ufn.end_line,
                        hop_distance=0,
                        causal_reason=f"anchor_line:{line_no}",
                        score=1.0,
                    )
                    frontier.append((rel_path, ufn.name, 0, "anchor"))
            else:
                # Top-level module / test script anchor: follow direct file_imports to imported source functions
                for imp_rel in sorted(self.file_imports.get(rel_path, set())):
                    if _is_test_rel_path(imp_rel):
                        continue
                    for imp_fn in self.functions_by_file.get(imp_rel, []):
                        ikey = (imp_rel, imp_fn.name)
                        if ikey not in visited:
                            visited[ikey] = CausalCutSite(
                                rel_path=imp_rel,
                                func_name=imp_fn.name,
                                language=imp_fn.language,
                                start_line=imp_fn.start_line,
                                end_line=imp_fn.end_line,
                                hop_distance=1,
                                causal_reason=f"imported_by_anchor:{rel_path}@{line_no}",
                                score=0.9,
                            )
                            frontier.append((imp_rel, imp_fn.name, 1, "import"))

        while frontier:
            cur_file, cur_fn, hop, _ = frontier.pop(0)
            if hop >= max_hops:
                continue
            # Producers called by current function (return-value lineage)
            for tgt_file, tgt_fn, call_ln in self.call_edges.get((cur_file, cur_fn), []):
                if _is_test_rel_path(tgt_file):
                    continue
                tkey = (tgt_file, tgt_fn)
                if tkey not in visited:
                    ufn = self._lookup_fn(tgt_file, tgt_fn)
                    if ufn is not None:
                        visited[tkey] = CausalCutSite(
                            rel_path=tgt_file,
                            func_name=tgt_fn,
                            language=ufn.language,
                            start_line=ufn.start_line,
                            end_line=ufn.end_line,
                            hop_distance=hop + 1,
                            causal_reason=f"callee_producer_of:{cur_fn}@{call_ln}",
                            score=round(1.0 / (1.0 + 0.45 * (hop + 1)), 4),
                        )
                        frontier.append((tgt_file, tgt_fn, hop + 1, "callee"))

            # Callers passing arguments into current function (argument lineage)
            for caller_file, caller_fn, call_ln in self.reverse_callers.get((cur_file, cur_fn), []):
                if _is_test_rel_path(caller_file):
                    continue
                ckey = (caller_file, caller_fn)
                if ckey not in visited:
                    ufn = self._lookup_fn(caller_file, caller_fn)
                    if ufn is not None:
                        visited[ckey] = CausalCutSite(
                            rel_path=caller_file,
                            func_name=caller_fn,
                            language=ufn.language,
                            start_line=ufn.start_line,
                            end_line=ufn.end_line,
                            hop_distance=hop + 1,
                            causal_reason=f"caller_arg_lineage_into:{cur_fn}@{call_ln}",
                            score=round(0.95 / (1.0 + 0.5 * (hop + 1)), 4),
                        )
                        frontier.append((caller_file, caller_fn, hop + 1, "caller"))

        return sorted(visited.values(), key=lambda c: (-c.score, c.hop_distance, c.rel_path, c.start_line))

    def compute_test_impact_cone(self, modified_rel_paths: list[str], *, max_tests: int = 8) -> list[str]:
        """Return transitive test files importing/including/calling modified source files."""
        seen: set[str] = set(modified_rel_paths)
        queue = list(modified_rel_paths)
        while queue:
            cur = queue.pop(0)
            for imp in self.reverse_importers.get(cur, set()):
                if imp not in seen:
                    seen.add(imp)
                    queue.append(imp)
            for ufn in self.functions_by_file.get(cur, []):
                for caller_file, _, _ in self.reverse_callers.get((cur, ufn.name), []):
                    if caller_file not in seen:
                        seen.add(caller_file)
                        queue.append(caller_file)

        impacted_tests = sorted(p for p in seen if _is_test_rel_path(p))
        return impacted_tests[:max_tests]

    def _lookup_fn(self, rel_path: str, fn_name: str) -> UIRFunction | None:
        for ufn in self.functions_by_file.get(rel_path, []):
            if ufn.name == fn_name:
                return ufn
        return None


def _is_test_rel_path(rel_path: str) -> bool:
    name = pathlib.Path(rel_path).name.lower()
    parts = {p.lower() for p in pathlib.Path(rel_path).parts}
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".spec.js")
        or "tests" in parts
        or "test" in parts
    )


class SemanticCausalLawStore:
    """External, inspectable, editable JSON store of cross-language Semantic Causal Laws."""

    def __init__(self, store_path: pathlib.Path | None = None) -> None:
        self.store_path = pathlib.Path(store_path or DEFAULT_LAW_STORE_PATH)
        self.laws: list[SemanticCausalLaw] = []
        self._load()

    def _load(self) -> None:
        if not self.store_path.exists():
            self.laws = []
            return
        raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.laws = [SemanticCausalLaw.from_dict(item) for item in (raw.get("laws") or [])]

    def save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": LAW_STORE_SCHEMA,
            "model_calls": 0,
            "memorized_world_weights": 0,
            "law_count": len(self.laws),
            "laws": [law.to_dict() for law in self.laws],
        }
        self.store_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def inspect_laws(self) -> list[dict[str, Any]]:
        return [law.to_dict() for law in self.laws]

    def check_contract_composition(
        self,
        first_law: SemanticCausalLaw,
        second_law: SemanticCausalLaw,
    ) -> dict[str, Any]:
        """Static EffectContract (P, O, A, V, F) composition check via effect_contract_composition_v1."""
        return compose_contracts(first_law.to_effect_contract(), second_law.to_effect_contract())

    def admit_law(self, law: SemanticCausalLaw) -> bool:
        """Fail-closed admission: requires sabotage + contrast verification AND a complete,
        non-inverting EffectContract (refuses EFFECT_UNDO against existing laws)."""
        if not law.sabotage_verified or not law.contrast_verified:
            return False
        contract = law.to_effect_contract()
        if check_effect_contract_complete(contract) is not None:
            return False
        for idx, existing in enumerate(self.laws):
            if (
                existing.defect_uir_kind == law.defect_uir_kind
                and existing.transform_operator == law.transform_operator
                and existing.precondition_signature == law.precondition_signature
            ):
                self.laws[idx] = law
                self.save()
                return True
            comp = compose_contracts(existing.to_effect_contract(), contract)
            if comp.get("verdict") == CONTRACT_EFFECT_UNDO:
                return False
        self.laws.append(law)
        self.save()
        return True

    def remove_law(self, law_id: str) -> bool:
        before = len(self.laws)
        self.laws = [l for l in self.laws if l.law_id != law_id]
        if len(self.laws) != before:
            self.save()
            return True
        return False

    def compact_laws(self) -> dict[str, int]:
        """Deduplicate alpha-equivalent laws and prune narrower TreeRewriteMorphisms
        strictly subsumed by more general verified morphisms in the store."""
        before_count = len(self.laws)
        kept: list[SemanticCausalLaw] = []

        def _subtree_subsumes(gen: SemanticCausalLaw, spec: SemanticCausalLaw) -> bool:
            if (
                gen.defect_uir_kind != "UIR_TREE_REWRITE_MORPHISM"
                or spec.defect_uir_kind != "UIR_TREE_REWRITE_MORPHISM"
            ):
                return (
                    gen.defect_uir_kind == spec.defect_uir_kind
                    and gen.transform_operator == spec.transform_operator
                    and gen.precondition_signature == spec.precondition_signature
                )
            gp = gen.precondition_signature
            sp = spec.precondition_signature
            if not (set(gp.get("required_domain_literals") or []) <= set(sp.get("required_domain_literals") or [])):
                return False
            try:
                g_lhs = ast.parse(str(gp.get("lhs_ast_pattern") or "")).body
                g_rhs = ast.parse(str(gp.get("rhs_ast_pattern") or "")).body
                s_lhs = ast.parse(str(sp.get("lhs_ast_pattern") or "")).body
                s_rhs = ast.parse(str(sp.get("rhs_ast_pattern") or "")).body
            except SyntaxError:
                return False
            if len(g_lhs) != len(s_lhs) or len(g_rhs) != len(s_rhs):
                return False
            bindings: dict[str, Any] = {}
            pure_only = set(gp.get("pure_only_holes") or [])
            for p_st, c_st in zip(g_lhs, s_lhs):
                if not _unify_ast_nodes(p_st, c_st, bindings, pure_only):
                    return False
            inst_rhs = _instantiate_ast_pattern(g_rhs, bindings)
            return [ast.dump(x) for x in inst_rhs] == [ast.dump(x) for x in s_rhs]

        for idx, cand in enumerate(self.laws):
            subsumed = False
            for jdx, other in enumerate(self.laws):
                if idx == jdx:
                    continue
                if _subtree_subsumes(other, cand):
                    # If mutually alpha-equivalent, keep the earlier index only
                    if _subtree_subsumes(cand, other) and idx < jdx:
                        continue
                    subsumed = True
                    break
            if not subsumed:
                kept.append(cand)

        self.laws = kept
        if len(self.laws) != before_count:
            self.save()
        return {
            "before": before_count,
            "after": len(self.laws),
            "pruned": before_count - len(self.laws),
        }

    def match_and_compile_candidates(
        self,
        source_bytes: bytes,
        language: str,
        rel_path: str = "<memory>",
        target_func_name: str | None = None,
        runtime_hint: dict[str, Any] | None = None,
    ) -> list[tuple[SemanticCausalLaw, bytes, str]]:
        """Diff target source's U-IR against stored Semantic Laws and compile candidate
        repairs into the target language's native syntax."""
        norm_lang = "cpp" if language in {"c", "cpp", "c++"} else language
        u_fns = lower_source_to_uir(source_bytes, norm_lang, rel_path=rel_path)
        results: list[tuple[SemanticCausalLaw, bytes, str]] = []

        for law in self.laws:
            if (
                target_func_name is None
                and law.precondition_signature.get("entry_anchored")
                and len(u_fns) > 12
            ):
                continue
            for ufn in u_fns:
                if target_func_name and ufn.name != target_func_name:
                    continue
                compiled = compile_law_to_function(
                    law=law,
                    ufn=ufn,
                    source_bytes=source_bytes,
                    language=norm_lang,
                    runtime_hint=runtime_hint,
                )
                for patched_bytes, desc in compiled:
                    if patched_bytes != source_bytes:
                        results.append((law, patched_bytes, desc))
        return results


def compile_law_to_function(
    *,
    law: SemanticCausalLaw,
    ufn: UIRFunction,
    source_bytes: bytes,
    language: str,
    runtime_hint: dict[str, Any] | None = None,
) -> list[tuple[bytes, str]]:
    """Lower a language-neutral SemanticCausalLaw into concrete target-language bytes."""
    out: list[tuple[bytes, str]] = []
    lines = source_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)

    # 1. Inclusive loop bound dereferencing bounded buffer/sequence -> strict bound
    if (
        law.defect_uir_kind == "UIR_ITER_BOUNDED"
        and law.transform_operator == "CLAMP_INCLUSIVE_BOUND_TO_STRICT"
    ):
        for node in ufn.nodes:
            if (
                node.kind == "UIR_ITER_BOUNDED"
                and node.roles.get("bound_polarity") == "INCLUSIVE_LE"
                and node.roles.get("body_derefs_cursor") is True
            ):
                old_span = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
                new_span = old_span
                if language == "python" and "range" in old_span:
                    new_span = re.sub(r"\+\s*1\b", "", old_span)
                    new_span = re.sub(r",\s*\)", ")", new_span)
                elif language == "rust" and "..=" in old_span:
                    new_span = old_span.replace("..=", "..", 1)
                elif "<=" in old_span:
                    new_span = old_span.replace("<=", "<", 1)
                if new_span != old_span:
                    patched = source_bytes[: node.start_byte] + new_span.encode("utf-8") + source_bytes[node.end_byte :]
                    out.append((patched, f"UIR[{law.law_id}]: clamp inclusive bound `{old_span}` -> `{new_span}`"))

    # 2. Unchecked nullable pointer/object dereference -> dominating existence guard
    elif (
        law.defect_uir_kind == "UIR_DEREF_LOAD"
        and law.transform_operator == "INSERT_DOMINATING_NULL_GUARD"
    ):
        body_entry_idx = max(0, ufn.start_line - 1)
        body_indent = "    "
        fn_body_txt = "".join(lines[max(0, ufn.start_line - 1) : min(len(lines), ufn.end_line)])
        cleanup_labels = list(dict.fromkeys(re.findall(r"\bgoto\s+([A-Za-z_]\w*)\s*;", fn_body_txt)))
        if language != "python":
            for scan_i in range(max(0, ufn.start_line - 1), min(len(lines), ufn.end_line)):
                if "{" in lines[scan_i]:
                    body_entry_idx = min(len(lines), scan_i + 1)
                    while body_entry_idx < min(len(lines), ufn.end_line):
                        dl = lines[body_entry_idx].strip()
                        if not dl or dl.startswith(("/*", "*", "//")):
                            body_entry_idx += 1
                            continue
                        if (
                            language == "cpp"
                            and dl.endswith(";")
                            and "->" not in dl
                            and not dl.startswith(("return", "if", "for", "while", "switch", "goto"))
                            and re.match(r"^(?:const\s+|unsigned\s+|signed\s+|struct\s+)*[A-Za-z_]\w*[\s\*]+[A-Za-z_]\w*\s*(?:=\s*[^;]+)?;$", dl)
                        ):
                            body_entry_idx += 1
                            continue
                        break
                    if body_entry_idx < len(lines):
                        m_ind = re.match(r"^\s*", lines[body_entry_idx])
                        if m_ind and m_ind.group(0).strip("\r\n"):
                            body_indent = m_ind.group(0)
                    break

        seen_sites: set[tuple[str, int]] = set()
        seen_params: set[str] = set()
        for node in ufn.nodes:
            if node.kind == "UIR_DEREF_LOAD" and not node.roles.get("dominated_by_null_guard"):
                base_var = str(node.roles.get("base_var") or "")
                deref_op = str(node.roles.get("deref_op") or "")
                is_param = base_var in ufn.params
                if not base_var:
                    continue
                if is_param:
                    if base_var in seen_params:
                        continue
                    seen_params.add(base_var)
                line_idx = body_entry_idx if (is_param and language != "python") else (node.start_line - 1)
                if (base_var, line_idx) in seen_sites or not (0 <= line_idx < len(lines)):
                    continue
                seen_sites.add((base_var, line_idx))
                indent = body_indent if (is_param and language != "python") else re.match(r"^\s*", lines[line_idx]).group(0)
                ret_expr = str(node.roles.get("default_return") or ufn.return_hint)
                if language == "cpp":
                    if deref_op == "CHAINED_ARROW" or ("->" in base_var and not lines[line_idx].lstrip().startswith("return")):
                        stmt_s = lines[line_idx].strip()
                        if stmt_s.endswith(";"):
                            wrapped = list(lines)
                            wrapped[line_idx] = f"{indent}if ({base_var} != NULL) {{ {stmt_s} }}\n"
                            out.append(("".join(wrapped).encode("utf-8"), f"UIR[{law.law_id}]: conditional null guard for `{base_var}`"))
                    for lbl in cleanup_labels[:1]:
                        if not is_param:
                            g_goto = list(lines)
                            g_goto.insert(line_idx, f"{indent}if ({base_var} == NULL) {{ goto {lbl}; }}\n")
                            out.append(("".join(g_goto).encode("utf-8"), f"UIR[{law.law_id}]: cleanup goto guard for `{base_var}`"))
                    ret_cands = [ret_expr]
                    if "nan" in ret_expr.lower() or "0.0" in ret_expr:
                        for extra_rc in ["(double)0", "0"] + [p for p in ufn.params if p != base_var][:1]:
                            if extra_rc not in ret_cands:
                                ret_cands.append(extra_rc)
                    for rc in ret_cands:
                        ret_stmt = f"return {rc};" if rc != "" else "return;"
                        new_lines = list(lines)
                        new_lines.insert(line_idx, f"{indent}if ({base_var} == NULL) {{ {ret_stmt} }}\n")
                        out.append(("".join(new_lines).encode("utf-8"), f"UIR[{law.law_id}]: insert null existence guard for `{base_var}`"))
                    continue
                elif language == "python":
                    guard_line = f"{indent}if {base_var} is None:\n{indent}    return {ret_expr}\n"
                elif language in {"javascript", "typescript"}:
                    guard_line = f"{indent}if ({base_var} === null || {base_var} === undefined) {{ return {ret_expr}; }}\n"
                elif language == "go":
                    guard_line = f"{indent}if {base_var} == nil {{ return {ret_expr} }}\n"
                else:
                    continue
                new_lines = list(lines)
                new_lines.insert(line_idx, guard_line)
                out.append(
                    (
                        "".join(new_lines).encode("utf-8"),
                        f"UIR[{law.law_id}]: insert null/None existence guard for `{base_var}`",
                    )
                )

    # 3. Truthiness vs Existence disambiguation (`if x:` -> `if x is not None:` / `x !== null && x !== undefined`)
    elif (
        law.defect_uir_kind == "UIR_GUARD"
        and law.transform_operator == "DISAMBIGUATE_TRUTHINESS_TO_EXISTENCE"
    ):
        hint_falsey_vars = set((runtime_hint or {}).get("falsey_non_none_vars") or [])
        for node in ufn.nodes:
            if node.kind == "UIR_GUARD" and node.roles.get("guard_kind") == "TRUTHINESS_CHECK":
                cond_txt = str(node.roles.get("cond_text") or "").strip()
                if cond_txt.startswith("not ") or cond_txt.startswith("!"):
                    continue
                if hint_falsey_vars and cond_txt not in hint_falsey_vars:
                    continue
                if language == "python":
                    new_cond = f"{cond_txt} is not None"
                elif language in {"javascript", "typescript"}:
                    new_cond = f"({cond_txt} !== null && {cond_txt} !== undefined)"
                elif language == "cpp":
                    new_cond = f"({cond_txt} != NULL)"
                else:
                    continue
                patched = source_bytes[: node.start_byte] + new_cond.encode("utf-8") + source_bytes[node.end_byte :]
                out.append((patched, f"UIR[{law.law_id}]: disambiguate truthiness `{cond_txt}` -> `{new_cond}`"))

    # 4. Unchecked zero divisor -> dominating non-zero guard
    elif (
        law.defect_uir_kind == "UIR_DIV_OP"
        and law.transform_operator == "INSERT_NONZERO_DIVISOR_GUARD"
    ):
        for node in ufn.nodes:
            if node.kind == "UIR_DIV_OP" and not node.roles.get("dominated_by_nonzero_guard"):
                div_var = str(node.roles.get("divisor_var") or "")
                ret_expr = str(node.roles.get("default_return") or ufn.return_hint)
                line_idx = node.start_line - 1
                if div_var and 0 <= line_idx < len(lines):
                    indent = re.match(r"^\s*", lines[line_idx]).group(0)
                    if language == "cpp":
                        ret_stmt = f"return {ret_expr};" if ret_expr != "" else "return;"
                        guard_line = f"{indent}if ({div_var} == 0) {{ {ret_stmt} }}\n"
                    elif language == "python":
                        guard_line = f"{indent}if {div_var} == 0:\n{indent}    return {ret_expr}\n"
                    elif language in {"javascript", "typescript"}:
                        guard_line = f"{indent}if ({div_var} === 0) {{ return {ret_expr}; }}\n"
                    else:
                        continue
                    new_lines = list(lines)
                    new_lines.insert(line_idx, guard_line)
                    out.append(("".join(new_lines).encode("utf-8"), f"UIR[{law.law_id}]: guard zero divisor `{div_var}`"))

    # 5. Multi-pass single-shot iterator -> materialize sequence
    elif (
        law.defect_uir_kind == "UIR_VALUE_FLOW"
        and law.transform_operator == "MATERIALIZE_MULTIPASS_ITERABLE"
    ):
        for node in ufn.nodes:
            if node.kind == "UIR_VALUE_FLOW" and node.roles.get("multipass_unmaterialized"):
                expr_txt = str(node.roles.get("expr_text") or "")
                if language == "python" and expr_txt:
                    for wrapper in ("tuple", "list"):
                        new_expr = f"{wrapper}({expr_txt})"
                        patched = (
                            source_bytes[: node.start_byte]
                            + new_expr.encode("utf-8")
                            + source_bytes[node.end_byte :]
                        )
                        out.append((patched, f"UIR[{law.law_id}]: materialize multipass iterable `{new_expr}`"))

    # 6. Mutable alias escape -> copy/clone
    elif (
        law.defect_uir_kind == "UIR_VALUE_FLOW"
        and law.transform_operator == "ISOLATE_ESCAPING_MUTABLE_ALIAS"
    ):
        for node in ufn.nodes:
            if node.kind == "UIR_VALUE_FLOW" and node.roles.get("mutable_alias_escape"):
                expr_txt = str(node.roles.get("expr_text") or "")
                if language == "python" and expr_txt:
                    new_expr = f"{expr_txt}.copy()"
                elif language in {"javascript", "typescript"} and expr_txt:
                    new_expr = f"[...{expr_txt}]"
                else:
                    continue
                patched = (
                    source_bytes[: node.start_byte]
                    + new_expr.encode("utf-8")
                    + source_bytes[node.end_byte :]
                )
                out.append((patched, f"UIR[{law.law_id}]: isolate escaping mutable alias `{new_expr}`"))

    # 7. Multi-statement / dataflow-bound AST subtree morphism (Plotkin/Refazer anti-unification)
    elif (
        language == "python"
        and law.defect_uir_kind == "UIR_TREE_REWRITE_MORPHISM"
        and law.transform_operator == "APPLY_BOUND_AST_SUBTREE_MORPHISM"
    ):
        for patched_bytes, desc in apply_ast_subtree_morphism(
            source_bytes=source_bytes,
            target_func_name=ufn.name,
            precond=law.precondition_signature,
            law_id=law.law_id,
            runtime_hint=runtime_hint,
        ):
            out.append((patched_bytes, desc))

    return out


_PY_SAFE_GLOBALS: frozenset[str] = frozenset(
    {
        "None", "True", "False", "len", "str", "int", "float", "bool", "bytes",
        "list", "tuple", "dict", "set", "frozenset", "isinstance", "issubclass",
        "type", "getattr", "hasattr", "setattr", "any", "all", "min", "max", "sum",
        "sorted", "reversed", "enumerate", "zip", "range", "repr", "abs",
        "iter", "next", "map", "filter", "round",
        "ValueError", "TypeError", "KeyError", "AttributeError", "IndexError",
        "RuntimeError", "OSError", "Exception", "StopIteration",
    }
)
_UNIVERSAL_IDENTITY_LITERALS: frozenset[Any] = frozenset({"", b"", 0, 1, -1, True, False, None})


def _index_python_functions(tree: ast.AST) -> dict[tuple[str, str], ast.FunctionDef | ast.AsyncFunctionDef]:
    out: dict[tuple[str, str], ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[("", node.name)] = node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[(node.name, item.name)] = item
    return out


def _minimal_changed_stmt_slice(
    b_body: list[ast.stmt],
    a_body: list[ast.stmt],
) -> tuple[list[ast.stmt], list[ast.stmt]] | None:
    b_dumps = [ast.dump(s) for s in b_body]
    a_dumps = [ast.dump(s) for s in a_body]
    if b_dumps == a_dumps:
        return None
    sm = difflib.SequenceMatcher(a=b_dumps, b=a_dumps, autojunk=False)
    changed = [op for op in sm.get_opcodes() if op[0] != "equal"]
    if not changed:
        return None
    i1 = changed[0][1]
    i2 = changed[-1][2]
    j1 = changed[0][3]
    j2 = changed[-1][4]
    if i1 == i2:
        prev_is_doc = (
            i1 == 1
            and isinstance(b_body[0], ast.Expr)
            and isinstance(b_body[0].value, ast.Constant)
            and isinstance(b_body[0].value.value, str)
        )
        if not prev_is_doc and i1 > 0 and j1 > 0:
            i1 -= 1
            j1 -= 1
        elif i2 < len(b_body) and j2 < len(a_body):
            i2 += 1
            j2 += 1
    b_slice = b_body[i1:i2]
    a_slice = a_body[j1:j2]
    # Descend if a single compound statement holds the entire interior diff
    if len(b_slice) == 1 and len(a_slice) == 1 and type(b_slice[0]) is type(a_slice[0]):
        bs0, as0 = b_slice[0], a_slice[0]
        if isinstance(bs0, (ast.If, ast.For, ast.While, ast.With)):
            b_hdr = ast.dump(getattr(bs0, "test", getattr(bs0, "iter", ast.Constant(None))))
            a_hdr = ast.dump(getattr(as0, "test", getattr(as0, "iter", ast.Constant(None))))
            if b_hdr == a_hdr:
                b_or = [ast.dump(x) for x in getattr(bs0, "orelse", [])]
                a_or = [ast.dump(x) for x in getattr(as0, "orelse", [])]
                if b_or == a_or:
                    sub = _minimal_changed_stmt_slice(bs0.body, as0.body)
                    if sub is not None:
                        return sub
                elif [ast.dump(x) for x in bs0.body] == [ast.dump(x) for x in as0.body]:
                    sub = _minimal_changed_stmt_slice(getattr(bs0, "orelse", []), getattr(as0, "orelse", []))
                    if sub is not None:
                        return sub
    if not b_slice or not a_slice or len(b_slice) > 6 or len(a_slice) > 6:
        return None
    # Include 1 preceding dataflow-feeding `Assign` when a 1-line leaf rewrite (`return a == b`)
    # needs its producer statement for structural specificity and variable binding!
    if (
        len(b_slice) == 1
        and len(a_slice) == 1
        and i1 > 0
        and j1 > 0
        and isinstance(b_body[i1 - 1], ast.Assign)
        and ast.dump(b_body[i1 - 1]) == ast.dump(a_body[j1 - 1])
    ):
        assigned_prev = {
            t.id for t in b_body[i1 - 1].targets if isinstance(t, ast.Name)
        }
        read_cur = {
            n.id for n in ast.walk(b_slice[0]) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
        }
        if assigned_prev & read_cur:
            b_slice = b_body[i1 - 1 : i2]
            a_slice = a_body[j1 - 1 : j2]
    return b_slice, a_slice


def _is_liftable_load_expr(node: ast.AST) -> bool:
    if isinstance(node, (ast.Call, ast.BinOp, ast.UnaryOp)):
        return True
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        return isinstance(getattr(node, "ctx", None), ast.Load)
    return False


def _is_pure_access_expr(node: ast.AST) -> bool:
    if isinstance(node, (ast.Name, ast.Constant)):
        return True
    if isinstance(node, ast.Attribute):
        return _is_pure_access_expr(node.value)
    if isinstance(node, ast.Subscript):
        return _is_pure_access_expr(node.value) and _is_pure_access_expr(node.slice)
    return False


def extract_ast_subtree_morphism(
    before_bytes: bytes,
    after_bytes: bytes,
) -> dict[str, Any] | None:
    """Anti-unify a concrete multi-statement or compound AST repair into a reusable,
    dataflow-bound TreeRewriteMorphism with non-linear hole constraints."""
    try:
        b_tree = ast.parse(before_bytes.decode("utf-8", errors="replace"))
        a_tree = ast.parse(after_bytes.decode("utf-8", errors="replace"))
    except SyntaxError:
        return None

    b_fns = _index_python_functions(b_tree)
    a_fns = _index_python_functions(a_tree)
    slice_pair: tuple[list[ast.stmt], list[ast.stmt]] | None = None
    matched_bfn: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    entry_anchored = False
    for key, bfn in b_fns.items():
        afn = a_fns.get(key)
        if afn is not None and ast.dump(bfn) != ast.dump(afn):
            slice_pair = _minimal_changed_stmt_slice(bfn.body, afn.body)
            if slice_pair is not None:
                matched_bfn = bfn
                first_exec_idx = (
                    1
                    if bfn.body
                    and isinstance(bfn.body[0], ast.Expr)
                    and isinstance(bfn.body[0].value, ast.Constant)
                    and isinstance(bfn.body[0].value.value, str)
                    else 0
                )
                if first_exec_idx < len(bfn.body) and slice_pair[0][0] is bfn.body[first_exec_idx]:
                    entry_anchored = len(slice_pair[1]) > len(slice_pair[0])
                break
    if slice_pair is None or matched_bfn is None:
        return None

    all_bfn_args = list(getattr(matched_bfn.args, "posonlyargs", [])) + list(matched_bfn.args.args)
    fn_params = [a.arg for a in all_bfn_args if a.arg not in {"self", "cls"}]
    param_hole_map = {p: f"__HPARAM_{idx}__" for idx, p in enumerate(fn_params)}

    b_slice, a_slice = slice_pair
    b_expr_dumps: set[str] = {
        ast.dump(sub)
        for stmt in b_slice
        for sub in ast.walk(stmt)
        if _is_liftable_load_expr(sub)
    }
    a_expr_dumps: set[str] = {
        ast.dump(sub)
        for stmt in a_slice
        for sub in ast.walk(stmt)
        if _is_liftable_load_expr(sub)
    }
    shared_expr_dumps = b_expr_dumps & a_expr_dumps

    expr_hole_map: dict[str, str] = {}
    hole_purity_required: dict[str, bool] = {}

    class _SharedExprLifter(ast.NodeTransformer):
        def visit(self, node: ast.AST) -> Any:
            if _is_liftable_load_expr(node):
                d = ast.dump(node)
                if d in shared_expr_dumps:
                    h = expr_hole_map.get(d)
                    if h is None:
                        h = f"__HEXPR_{len(expr_hole_map)}__"
                        expr_hole_map[d] = h
                        hole_purity_required[h] = False
                    return ast.Name(id=h, ctx=ast.Load())
            return super().visit(node)

    b_stage1 = [_SharedExprLifter().visit(copy.deepcopy(s)) for s in b_slice]
    a_stage1 = [_SharedExprLifter().visit(copy.deepcopy(s)) for s in a_slice]

    var_map: dict[str, str] = {}
    attr_map: dict[str, str] = {}

    class _RecordBinder(ast.NodeTransformer):
        def __init__(self, allow_new: bool) -> None:
            self.allow_new = allow_new

        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id.startswith("__HEXPR_") or node.id in _PY_SAFE_GLOBALS:
                return node
            if node.id in var_map:
                return ast.Name(id=var_map[node.id], ctx=node.ctx)
            if self.allow_new:
                h = f"__HVAR_{len(var_map)}__"
                var_map[node.id] = h
                return ast.Name(id=h, ctx=node.ctx)
            if node.id in param_hole_map:
                return ast.Name(id=param_hole_map[node.id], ctx=node.ctx)
            return node

        def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
            new_val = self.visit(node.value)
            if node.attr in attr_map:
                new_attr = attr_map[node.attr]
            elif self.allow_new:
                new_attr = f"__HATTR_{len(attr_map)}__"
                attr_map[node.attr] = new_attr
            else:
                new_attr = node.attr
            return ast.Attribute(value=new_val, attr=new_attr, ctx=node.ctx)

    b_lifted = [_RecordBinder(allow_new=True).visit(s) for s in b_stage1]
    a_lifted = [_RecordBinder(allow_new=False).visit(s) for s in a_stage1]

    # Count hole occurrences to enforce side-effect purity on non-linear holes
    lhs_counts: dict[str, int] = {}
    rhs_counts: dict[str, int] = {}
    for s in b_lifted:
        for n in ast.walk(s):
            if isinstance(n, ast.Name) and n.id.startswith("__HEXPR_"):
                lhs_counts[n.id] = lhs_counts.get(n.id, 0) + 1
    for s in a_lifted:
        for n in ast.walk(s):
            if isinstance(n, ast.Name) and n.id.startswith("__HEXPR_"):
                rhs_counts[n.id] = rhs_counts.get(n.id, 0) + 1

    pure_only_holes = sorted(
        h
        for h in set(lhs_counts) | set(rhs_counts)
        if lhs_counts.get(h, 0) != 1 or rhs_counts.get(h, 0) != 1
    )

    used_param_holes = sorted(
        {
            n.id
            for s in a_lifted
            for n in ast.walk(s)
            if isinstance(n, ast.Name) and n.id.startswith("__HPARAM_")
        }
    )
    min_param_arity = (
        max(int(ph.split("_")[3]) + 1 for ph in used_param_holes)
        if used_param_holes
        else 0
    )

    # Closedness check (FOREIGN_IDENT_UNBOUND guard)
    assigned_in_rhs = {
        n.id
        for s in a_lifted
        for n in ast.walk(s)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
    }
    bound_holes = set(lhs_counts) | set(var_map.values()) | set(used_param_holes)
    for s in a_lifted:
        for n in ast.walk(s):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if (
                    n.id not in bound_holes
                    and n.id not in assigned_in_rhs
                    and n.id not in _PY_SAFE_GLOBALS
                ):
                    return None

    # Specificity guard: disallow degenerate single-hole wildcards (e.g. `return __HEXPR_0__`)
    structural_scope = (b_lifted + a_lifted) if entry_anchored else b_lifted
    structural_nodes = sum(
        1
        for s in structural_scope
        for n in ast.walk(s)
        if isinstance(
            n,
            (
                ast.If, ast.Compare, ast.BoolOp, ast.Tuple, ast.List, ast.Dict,
                ast.For, ast.While, ast.Try, ast.With, ast.Raise, ast.BinOp, ast.Subscript,
            ),
        )
    )
    if len(b_lifted) < 2 and structural_nodes < 2:
        return None

    b_consts = {
        n.value
        for s in b_lifted
        for n in ast.walk(s)
        if isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes, int, float))
    }
    raise_msg_ids = {
        id(sub)
        for s in a_lifted
        for r in ast.walk(s)
        if isinstance(r, ast.Raise)
        for sub in ast.walk(r)
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str)
    }
    domain_lits = sorted(
        {
            repr(n.value)
            for s in a_lifted
            for n in ast.walk(s)
            if isinstance(n, ast.Constant)
            and id(n) not in raise_msg_ids
            and isinstance(n.value, (str, bytes, int, float))
            and n.value not in _UNIVERSAL_IDENTITY_LITERALS
            and n.value not in b_consts
        }
    )

    lhs_src = ast.unparse(ast.Module(body=b_lifted, type_ignores=[])).strip()
    rhs_src = ast.unparse(ast.Module(body=a_lifted, type_ignores=[])).strip()
    if not lhs_src or not rhs_src or lhs_src == rhs_src:
        return None

    def _alpha_canonicalize(pattern_src: str) -> str:
        mapping: dict[str, str] = {}

        def _repl(m: re.Match[str]) -> str:
            tok = m.group(0)
            if tok not in mapping:
                mapping[tok] = f"__H_{len(mapping)}__"
            return mapping[tok]

        return re.sub(r"__H(?:EXPR|VAR|ATTR|PARAM)_\d+__", _repl, pattern_src)

    lhs_canon = _alpha_canonicalize(lhs_src)
    rhs_canon = _alpha_canonicalize(rhs_src)

    return {
        "lhs_ast_pattern": lhs_src,
        "rhs_ast_pattern": rhs_src,
        "lhs_stmt_count": len(b_lifted),
        "rhs_stmt_count": len(a_lifted),
        "entry_anchored": entry_anchored,
        "min_param_arity": min_param_arity,
        "pure_only_holes": pure_only_holes,
        "required_domain_literals": domain_lits,
        "effect_contract": {
            "P": [f"AST_SLICE:{lhs_canon}"],
            "O": ["AST_SUBTREE_STRUCTURE", "DATAFLOW_HOLE_BINDINGS", "IMPACT_CONE_TESTS"],
            "A": [f"REWRITE_AST_SLICE:{lhs_canon}=>{rhs_canon}"],
            "V": "PYTEST_IMPACT_CONE_AND_COW_BOUNDARY_FUZZ",
            "F_remove": [f"AST_SLICE:{lhs_canon}"],
            "F_establish": [f"AST_SLICE:{rhs_canon}"],
        },
    }


def _unify_ast_nodes(
    pat: ast.AST,
    conc: ast.AST,
    bindings: dict[str, Any],
    pure_only_holes: set[str],
) -> bool:
    if isinstance(pat, ast.Name) and pat.id.startswith("__HEXPR_"):
        if not isinstance(conc, ast.expr):
            return False
        if pat.id in pure_only_holes and not _is_pure_access_expr(conc):
            return False
        prev = bindings.get(pat.id)
        if prev is not None:
            return ast.dump(prev) == ast.dump(conc)
        bindings[pat.id] = copy.deepcopy(conc)
        return True

    if isinstance(pat, ast.Name) and (pat.id.startswith("__HVAR_") or pat.id.startswith("__HPARAM_")):
        if not isinstance(conc, ast.Name):
            return False
        prev = bindings.get(pat.id)
        if prev is not None:
            return prev == conc.id
        if pat.id.startswith("__HVAR_") and conc.id in {
            v for k, v in bindings.items() if k.startswith("__HVAR_")
        }:
            return False
        bindings[pat.id] = conc.id
        return True

    if type(pat) is not type(conc):
        return False

    if isinstance(pat, ast.Attribute):
        if not _unify_ast_nodes(pat.value, conc.value, bindings, pure_only_holes):
            return False
        if pat.attr.startswith("__HATTR_"):
            prev = bindings.get(pat.attr)
            if prev is not None:
                return prev == conc.attr
            if conc.attr in {v for k, v in bindings.items() if k.startswith("__HATTR_")}:
                return False
            bindings[pat.attr] = conc.attr
            return True
        return pat.attr == conc.attr

    for field_name in pat._fields:
        if field_name in {"ctx", "type_comment"}:
            continue
        pv = getattr(pat, field_name)
        cv = getattr(conc, field_name)
        if isinstance(pv, list):
            if not isinstance(cv, list) or len(pv) != len(cv):
                return False
            for p_item, c_item in zip(pv, cv):
                if isinstance(p_item, ast.AST):
                    if not isinstance(c_item, ast.AST) or not _unify_ast_nodes(
                        p_item, c_item, bindings, pure_only_holes
                    ):
                        return False
                elif p_item != c_item:
                    return False
        elif isinstance(pv, ast.AST):
            if not isinstance(cv, ast.AST) or not _unify_ast_nodes(pv, cv, bindings, pure_only_holes):
                return False
        elif pv != cv:
            return False
    return True


def _instantiate_ast_pattern(rhs_stmts: list[ast.stmt], bindings: dict[str, Any]) -> list[ast.stmt]:
    class _Substituter(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id.startswith("__HEXPR_") and node.id in bindings:
                return copy.deepcopy(bindings[node.id])
            if (node.id.startswith("__HVAR_") or node.id.startswith("__HPARAM_")) and node.id in bindings:
                return ast.Name(id=str(bindings[node.id]), ctx=node.ctx)
            return node

        def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
            new_val = self.visit(node.value)
            new_attr = str(bindings.get(node.attr, node.attr))
            return ast.Attribute(value=new_val, attr=new_attr, ctx=node.ctx)

    return [_Substituter().visit(copy.deepcopy(s)) for s in rhs_stmts]


def _iter_stmt_lists(fn_node: ast.AST) -> list[list[ast.stmt]]:
    lists: list[list[ast.stmt]] = []
    for sub in ast.walk(fn_node):
        for attr in ("body", "orelse", "finalbody"):
            val = getattr(sub, attr, None)
            if isinstance(val, list) and val and all(isinstance(x, ast.stmt) for x in val):
                lists.append(val)
    return lists


def apply_ast_subtree_morphism(
    *,
    source_bytes: bytes,
    target_func_name: str,
    precond: dict[str, Any],
    law_id: str,
    runtime_hint: dict[str, Any] | None = None,
) -> list[tuple[bytes, str]]:
    lhs_src = str(precond.get("lhs_ast_pattern") or "")
    rhs_src = str(precond.get("rhs_ast_pattern") or "")
    if not lhs_src or not rhs_src:
        return []

    req_lits = list(precond.get("required_domain_literals") or [])
    if req_lits:
        hint_lits = {repr(x) for x in ((runtime_hint or {}).get("assertion_literals") or [])}
        src_text = source_bytes.decode("utf-8", errors="replace")
        if not all((lit in hint_lits or lit in src_text) for lit in req_lits):
            return []

    try:
        lhs_stmts = ast.parse(lhs_src).body
        rhs_stmts = ast.parse(rhs_src).body
        src_text = source_bytes.decode("utf-8", errors="replace")
        tree = ast.parse(src_text)
    except SyntaxError:
        return []

    pure_only = set(precond.get("pure_only_holes") or [])
    entry_anchored = bool(precond.get("entry_anchored"))
    min_arity = int(precond.get("min_param_arity") or 0)
    lines = src_text.splitlines(keepends=True)
    results: list[tuple[bytes, str]] = []
    k_len = len(lhs_stmts)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != target_func_name:
            continue
        all_tgt_args = list(getattr(node.args, "posonlyargs", [])) + list(node.args.args)
        tgt_params = [a.arg for a in all_tgt_args if a.arg not in {"self", "cls"}]
        if min_arity and len(tgt_params) < min_arity:
            continue
        param_seed_bindings = {f"__HPARAM_{p_i}__": p_nm for p_i, p_nm in enumerate(tgt_params)}
        first_exec_idx = (
            1
            if node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
            else 0
        )
        candidate_bodies = [node.body] if entry_anchored else _iter_stmt_lists(node)
        for body in candidate_bodies:
            if len(body) < k_len:
                continue
            idx_range = [first_exec_idx] if entry_anchored else list(range(len(body) - k_len + 1))
            for idx in idx_range:
                if idx + k_len > len(body):
                    continue
                if entry_anchored and isinstance(body[idx], ast.If):
                    continue
                window = body[idx : idx + k_len]
                bindings: dict[str, Any] = dict(param_seed_bindings)
                ok = True
                for p_stmt, c_stmt in zip(lhs_stmts, window):
                    if not _unify_ast_nodes(p_stmt, c_stmt, bindings, pure_only):
                        ok = False
                        break
                if not ok:
                    continue
                inst_stmts = _instantiate_ast_pattern(rhs_stmts, bindings)
                start_ln = window[0].lineno - 1
                end_ln = getattr(window[-1], "end_lineno", window[-1].lineno)
                if not (0 <= start_ln < end_ln <= len(lines)):
                    continue
                indent_match = re.match(r"^[ \t]*", lines[start_ln])
                indent = indent_match.group(0) if indent_match else ""
                rendered_lines: list[str] = []
                for istmt in inst_stmts:
                    for rln in ast.unparse(istmt).splitlines():
                        rendered_lines.append(f"{indent}{rln}\n")
                new_lines = lines[:start_ln] + rendered_lines + lines[end_ln:]
                patched_src = "".join(new_lines)
                try:
                    ast.parse(patched_src)
                except SyntaxError:
                    continue
                patched_bytes = patched_src.encode("utf-8")
                if patched_bytes != source_bytes:
                    results.append(
                        (
                            patched_bytes,
                            f"UIR_SUBTREE[{law_id}]: rewrite {k_len}-stmt AST slice -> `{rhs_src}`",
                        )
                    )
    return results


def lift_verified_diff_to_semantic_law(
    *,
    before_bytes: bytes,
    after_bytes: bytes,
    language: str,
    rel_path: str = "<memory>",
    sabotage_verified: bool = False,
    contrast_verified: bool = False,
) -> SemanticCausalLaw | None:
    """Lift a newly invented, verified concrete repair into a language-neutral SemanticCausalLaw."""
    norm_lang = "cpp" if language in {"c", "cpp", "c++"} else language
    before_fns = {f.name: f for f in lower_source_to_uir(before_bytes, norm_lang, rel_path=rel_path)}
    after_fns = {f.name: f for f in lower_source_to_uir(after_bytes, norm_lang, rel_path=rel_path)}

    defect_kind = ""
    transform_op = ""
    precond: dict[str, Any] = {}

    for fname, bfn in before_fns.items():
        afn = after_fns.get(fname)
        if afn is None:
            continue
        b_iters = [n for n in bfn.nodes if n.kind == "UIR_ITER_BOUNDED"]
        a_iters = [n for n in afn.nodes if n.kind == "UIR_ITER_BOUNDED"]
        if len(b_iters) == len(a_iters):
            for bi, ai in zip(b_iters, a_iters):
                if (
                    bi.roles.get("bound_polarity") == "INCLUSIVE_LE"
                    and ai.roles.get("bound_polarity") == "STRICT_LT"
                    and bi.roles.get("body_derefs_cursor") is True
                ):
                    defect_kind = "UIR_ITER_BOUNDED"
                    transform_op = "CLAMP_INCLUSIVE_BOUND_TO_STRICT"
                    precond = {"bound_polarity": "INCLUSIVE_LE", "body_derefs_cursor": True}
                    break

        if not transform_op:
            b_unchecked = [n for n in bfn.nodes if n.kind == "UIR_DEREF_LOAD" and not n.roles.get("dominated_by_null_guard")]
            a_unchecked = [n for n in afn.nodes if n.kind == "UIR_DEREF_LOAD" and not n.roles.get("dominated_by_null_guard")]
            b_ex_cnt = sum(1 for n in bfn.nodes if n.kind == "UIR_GUARD" and n.roles.get("guard_kind") == "EXISTENCE_CHECK")
            a_ex_cnt = sum(1 for n in afn.nodes if n.kind == "UIR_GUARD" and n.roles.get("guard_kind") == "EXISTENCE_CHECK")
            if len(b_unchecked) > len(a_unchecked) and a_ex_cnt > b_ex_cnt:
                defect_kind = "UIR_DEREF_LOAD"
                transform_op = "INSERT_DOMINATING_NULL_GUARD"
                precond = {"dominated_by_null_guard": False}

        if not transform_op:
            b_truth = [n for n in bfn.nodes if n.kind == "UIR_GUARD" and n.roles.get("guard_kind") == "TRUTHINESS_CHECK"]
            a_exist = [n for n in afn.nodes if n.kind == "UIR_GUARD" and n.roles.get("guard_kind") == "EXISTENCE_GUARD" or n.roles.get("guard_kind") == "EXISTENCE_CHECK"]
            if len(b_truth) > 0 and len(a_exist) > len([n for n in bfn.nodes if n.kind == "UIR_GUARD" and n.roles.get("guard_kind") == "EXISTENCE_CHECK"]):
                defect_kind = "UIR_GUARD"
                transform_op = "DISAMBIGUATE_TRUTHINESS_TO_EXISTENCE"
                precond = {"guard_kind": "TRUTHINESS_CHECK"}

        if not transform_op:
            b_div = [n for n in bfn.nodes if n.kind == "UIR_DIV_OP" and not n.roles.get("dominated_by_nonzero_guard")]
            a_div = [n for n in afn.nodes if n.kind == "UIR_DIV_OP" and not n.roles.get("dominated_by_nonzero_guard")]
            if len(b_div) > len(a_div):
                defect_kind = "UIR_DIV_OP"
                transform_op = "INSERT_NONZERO_DIVISOR_GUARD"
                precond = {"dominated_by_nonzero_guard": False}

        if not transform_op:
            b_mp = [n for n in bfn.nodes if n.kind == "UIR_VALUE_FLOW" and n.roles.get("multipass_unmaterialized")]
            a_mp = [n for n in afn.nodes if n.kind == "UIR_VALUE_FLOW" and n.roles.get("multipass_unmaterialized")]
            if len(b_mp) > len(a_mp):
                defect_kind = "UIR_VALUE_FLOW"
                transform_op = "MATERIALIZE_MULTIPASS_ITERABLE"
                precond = {"multipass_unmaterialized": True}

        if not transform_op:
            b_al = [n for n in bfn.nodes if n.kind == "UIR_VALUE_FLOW" and n.roles.get("mutable_alias_escape")]
            a_al = [n for n in afn.nodes if n.kind == "UIR_VALUE_FLOW" and n.roles.get("mutable_alias_escape")]
            if len(b_al) > len(a_al):
                defect_kind = "UIR_VALUE_FLOW"
                transform_op = "ISOLATE_ESCAPING_MUTABLE_ALIAS"
                precond = {"mutable_alias_escape": True}

    if (not defect_kind or not transform_op) and norm_lang == "python":
        morphism = extract_ast_subtree_morphism(before_bytes, after_bytes)
        if morphism is not None:
            defect_kind = "UIR_TREE_REWRITE_MORPHISM"
            transform_op = "APPLY_BOUND_AST_SUBTREE_MORPHISM"
            precond = morphism

    if not defect_kind or not transform_op:
        return None

    ev_hash = hashlib.sha256(before_bytes + b"\x00->\x00" + after_bytes).hexdigest()[:16]
    law_key = json.dumps(
        {"k": defect_kind, "op": transform_op, "p": precond},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    law_id = f"uir_law_{hashlib.sha256(law_key).hexdigest()[:12]}"
    return SemanticCausalLaw(
        law_id=law_id,
        defect_uir_kind=defect_kind,
        transform_operator=transform_op,
        precondition_signature=precond,
        learned_from_language=norm_lang,
        sabotage_verified=sabotage_verified,
        contrast_verified=contrast_verified,
        evidence_digest=ev_hash,
    )
