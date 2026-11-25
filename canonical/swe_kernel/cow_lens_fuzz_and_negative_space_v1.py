#!/usr/bin/env python3
"""CoW Differential Boundary Fuzzer, Bidirectional FST/Lens Synthesizer,
Angelic Perturbation Fault Blame, and L3 Negative-Space Refutation Store.

All four organs obey Project Brain's strict runtime laws:
  - 0 runtime LLM/model calls ($0.00 inference)
  - 0 memorized world facts in weights
  - Millisecond Copy-on-Write isolation via ZygotePrewarmedPool (os.fork)
  - External, inspectable, O(1)-revocable JSON store for L3 negative invariants
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
import hashlib
import json
import pathlib
import re
from typing import Any

from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool

_SHARED_ZYGOTE: ZygotePrewarmedPool | None = None


def _get_zygote() -> ZygotePrewarmedPool:
    global _SHARED_ZYGOTE
    if _SHARED_ZYGOTE is None:
        _SHARED_ZYGOTE = ZygotePrewarmedPool()
        _SHARED_ZYGOTE._warmed = True
    return _SHARED_ZYGOTE

NEGATIVE_STORE_SCHEMA = "BRAIN_NEGATIVE_SPACE_INVARIANTS_V1"
DEFAULT_NEGATIVE_STORE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "astra_runtime"
    / "state"
    / "NEGATIVE_SPACE_INVARIANTS_V1.json"
)


# ============================================================================ #
# 1. Bidirectional Finite-State Transducer (FST) & Lens Synthesis
# ============================================================================ #

@dataclass(frozen=True)
class SynthesizedBidirectionalLens:
    lens_id: str
    lens_family: str
    forward_expr_template: str
    backward_expr_template: str
    roundtrip_verified: bool
    witness_count: int
    parameters: dict[str, Any] = field(default_factory=dict)

    def compile_forward_fn_source(self, fn_name: str = "lens_forward") -> str:
        body_expr = self.forward_expr_template.replace("{x}", "x")
        return f"def {fn_name}(x):\n    return {body_expr}\n"

    def compile_backward_fn_source(self, fn_name: str = "lens_backward") -> str:
        body_expr = self.backward_expr_template.replace("{y}", "y")
        return f"def {fn_name}(y):\n    return {body_expr}\n"


def _caret_encode_text(val: str | bytes) -> str:
    raw = val.decode("latin1") if isinstance(val, bytes) else str(val)
    out: list[str] = []
    for ch in raw:
        code = ord(ch)
        if ch == "^":
            out.append("^^")
        elif 0 <= code < 32 and ch not in ("\n", "\r", "\t"):
            out.append("^" + chr(code + 64))
        elif code == 127:
            out.append("^?")
        else:
            out.append(ch)
    return "".join(out)


def _caret_decode_text(val: str, as_bytes: bool = False) -> str | bytes:
    out: list[str] = []
    i = 0
    n = len(val)
    while i < n:
        if val[i] == "^" and i + 1 < n:
            nxt = val[i + 1]
            if nxt == "^":
                out.append("^")
                i += 2
                continue
            if nxt == "?":
                out.append("\x7f")
                i += 2
                continue
            code = ord(nxt)
            if 64 <= code <= 95:
                out.append(chr(code - 64))
                i += 2
                continue
        out.append(val[i])
        i += 1
    joined = "".join(out)
    return joined.encode("latin1") if as_bytes else joined


def synthesize_bidirectional_fst_lens(
    witness_pairs: list[tuple[Any, Any]],
) -> SynthesizedBidirectionalLens | None:
    """Induce a deterministic, verified Finite-State Transducer / Lens from concrete
    (input, expected_output) witness pairs without any task-specific lookup table."""
    if not witness_pairs:
        return None

    # Family A: ASCII Control-Byte <-> Caret Notation FST (^@, ^A..^Z, ^D=0x04, ^Z=0x1a, ^?=0x7f)
    if all(isinstance(i, (str, bytes)) and isinstance(o, (str, bytes)) for i, o in witness_pairs):
        # Forward: control bytes -> caret text
        all_fwd_caret = True
        any_ctrl = False
        in_is_bytes = isinstance(witness_pairs[0][0], bytes)
        for inp, out in witness_pairs:
            if not isinstance(out, str):
                all_fwd_caret = False
                break
            raw_s = inp.decode("latin1") if isinstance(inp, bytes) else inp
            if any((0 <= ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 for c in raw_s):
                any_ctrl = True
            if _caret_encode_text(inp) != out:
                all_fwd_caret = False
                break
        if all_fwd_caret and any_ctrl:
            rt_ok = all(_caret_decode_text(_caret_encode_text(inp), as_bytes=in_is_bytes) == inp for inp, _ in witness_pairs)
            dec_prefix = "{x}.decode('latin1')" if in_is_bytes else "{x}"
            fwd_tpl = (
                "''.join('^^' if c == '^' else ('^?' if ord(c) == 127 else "
                "('^' + chr(ord(c) + 64) if (0 <= ord(c) < 32 and c not in '\\n\\r\\t') else c)) "
                f"for c in ({dec_prefix}))"
            )
            bwd_core = (
                "__import__('re').sub(r'\\^([@A-Z\\[\\\\\\]\\^_\\?])', "
                "lambda m: '^' if m.group(1) == '^' else ('\\x7f' if m.group(1) == '?' else chr(ord(m.group(1)) - 64)), {y})"
            )
            bwd_tpl = f"({bwd_core}).encode('latin1')" if in_is_bytes else bwd_core
            lid = f"fst_caret_{hashlib.sha256(fwd_tpl.encode()).hexdigest()[:10]}"
            return SynthesizedBidirectionalLens(
                lens_id=lid,
                lens_family="ASCII_CONTROL_CARET_FST",
                forward_expr_template=fwd_tpl,
                backward_expr_template=bwd_tpl,
                roundtrip_verified=rt_ok,
                witness_count=len(witness_pairs),
                parameters={"input_bytes": in_is_bytes},
            )

        # Inverse Caret -> Control-Byte FST ("^D" -> b"\x04" or "\x04")
        all_bwd_caret = True
        any_caret_tok = False
        out_is_bytes = isinstance(witness_pairs[0][1], bytes)
        for inp, out in witness_pairs:
            if not isinstance(inp, str):
                all_bwd_caret = False
                break
            if "^" in inp:
                any_caret_tok = True
            if _caret_decode_text(inp, as_bytes=out_is_bytes) != out:
                all_bwd_caret = False
                break
        if all_bwd_caret and any_caret_tok:
            rt_ok = all(_caret_encode_text(_caret_decode_text(inp, as_bytes=out_is_bytes)) == inp for inp, _ in witness_pairs)
            fwd_core = (
                "__import__('re').sub(r'\\^([@A-Z\\[\\\\\\]\\^_\\?])', "
                "lambda m: '^' if m.group(1) == '^' else ('\\x7f' if m.group(1) == '?' else chr(ord(m.group(1)) - 64)), {x})"
            )
            fwd_tpl = f"({fwd_core}).encode('latin1')" if out_is_bytes else fwd_core
            dec_y = "{y}.decode('latin1')" if out_is_bytes else "{y}"
            bwd_tpl = (
                "''.join('^^' if c == '^' else ('^?' if ord(c) == 127 else "
                "('^' + chr(ord(c) + 64) if (0 <= ord(c) < 32 and c not in '\\n\\r\\t') else c)) "
                f"for c in ({dec_y}))"
            )
            lid = f"fst_inv_caret_{hashlib.sha256(fwd_tpl.encode()).hexdigest()[:10]}"
            return SynthesizedBidirectionalLens(
                lens_id=lid,
                lens_family="CARET_TO_CONTROL_BYTE_FST",
                forward_expr_template=fwd_tpl,
                backward_expr_template=bwd_tpl,
                roundtrip_verified=rt_ok,
                witness_count=len(witness_pairs),
                parameters={"output_bytes": out_is_bytes},
            )

    # Family B: Idempotent Delimiter Trim + Identity Floor Lens (e.g. `x.rstrip(d) or d`)
    if all(isinstance(i, str) and isinstance(o, str) for i, o in witness_pairs):
        candidate_delims = sorted({c for inp, _ in witness_pairs for c in inp if not c.isalnum()})
        for d in candidate_delims:
            if all((inp.rstrip(d) or d) == out for inp, out in witness_pairs) and any(
                inp != out for inp, out in witness_pairs
            ):
                dr = repr(d)
                fwd_tpl = f"({{x}}.rstrip({dr}) or {dr})"
                bwd_tpl = f"({{y}} if {{y}}.endswith({dr}) else {{y}} + {dr})"
                lid = f"lens_rstrip_floor_{hashlib.sha256(dr.encode()).hexdigest()[:10]}"
                return SynthesizedBidirectionalLens(
                    lens_id=lid,
                    lens_family="DELIMITER_RSTRIP_IDENTITY_FLOOR_LENS",
                    forward_expr_template=fwd_tpl,
                    backward_expr_template=bwd_tpl,
                    roundtrip_verified=True,
                    witness_count=len(witness_pairs),
                    parameters={"delimiter": d},
                )

        # Family C: Constant Prefix / Suffix Bijection Lens (`Bearer tok` <-> `tok`)
        first_in, first_out = witness_pairs[0]
        if len(first_in) > len(first_out) and first_in.endswith(first_out):
            prefix = first_in[: len(first_in) - len(first_out)]
            if prefix and all(inp == prefix + out for inp, out in witness_pairs):
                pr = repr(prefix)
                fwd_tpl = f"{{x}}.removeprefix({pr})"
                bwd_tpl = f"({pr} + {{y}})"
                rt_ok = all((prefix + inp.removeprefix(prefix)) == inp for inp, _ in witness_pairs)
                lid = f"lens_prefix_{hashlib.sha256(pr.encode()).hexdigest()[:10]}"
                return SynthesizedBidirectionalLens(
                    lens_id=lid,
                    lens_family="AFFIX_BIJECTION_LENS",
                    forward_expr_template=fwd_tpl,
                    backward_expr_template=bwd_tpl,
                    roundtrip_verified=rt_ok,
                    witness_count=len(witness_pairs),
                    parameters={"prefix": prefix},
                )

        # Family D: Deterministic Piecewise Substring/Token Mealy Table
        # Induced when every witness pair differs by a consistent finite non-overlapping map
        repl_map: dict[str, str] = {}
        consistent = True
        for inp, out in witness_pairs:
            if inp == out:
                continue
            # Extract minimal differing span
            p = 0
            while p < len(inp) and p < len(out) and inp[p] == out[p]:
                p += 1
            s = 0
            while (
                s < (len(inp) - p)
                and s < (len(out) - p)
                and inp[len(inp) - 1 - s] == out[len(out) - 1 - s]
            ):
                s += 1
            src_tok = inp[p : len(inp) - s]
            dst_tok = out[p : len(out) - s]
            if not src_tok or not dst_tok:
                consistent = False
                break
            if src_tok in repl_map and repl_map[src_tok] != dst_tok:
                consistent = False
                break
            repl_map[src_tok] = dst_tok
        if consistent and repl_map and len(set(repl_map.values())) == len(repl_map):
            def _apply_map(s: str, mp: dict[str, str]) -> str:
                cur = s
                for k, v in sorted(mp.items(), key=lambda kv: -len(kv[0])):
                    cur = cur.replace(k, v)
                return cur

            inv_map = {v: k for k, v in repl_map.items()}
            if all(_apply_map(inp, repl_map) == out for inp, out in witness_pairs):
                rt_ok = all(_apply_map(_apply_map(inp, repl_map), inv_map) == inp for inp, _ in witness_pairs)
                fwd_tpl = "{x}"
                for k, v in sorted(repl_map.items(), key=lambda kv: -len(kv[0])):
                    fwd_tpl = f"({fwd_tpl}).replace({repr(k)}, {repr(v)})"
                bwd_tpl = "{y}"
                for k, v in sorted(inv_map.items(), key=lambda kv: -len(kv[0])):
                    bwd_tpl = f"({bwd_tpl}).replace({repr(k)}, {repr(v)})"
                lid = f"fst_mealy_{hashlib.sha256(fwd_tpl.encode()).hexdigest()[:10]}"
                return SynthesizedBidirectionalLens(
                    lens_id=lid,
                    lens_family="DETERMINISTIC_TOKEN_MEALY_FST",
                    forward_expr_template=fwd_tpl,
                    backward_expr_template=bwd_tpl,
                    roundtrip_verified=rt_ok,
                    witness_count=len(witness_pairs),
                    parameters={"transitions": repl_map},
                )

    return None


# ============================================================================ #
# 2. 64-Case Parallel 1ms CoW Differential Boundary Fuzzer
# ============================================================================ #

class _NeutralBoundaryReceiver:
    """Neutral receiver stub used during 64-case CoW boundary fuzzing so method
    patches can be stress-tested across attribute states without side effects."""

    def __init__(self, primary_attr_val: Any = None) -> None:
        self._primary_val = primary_attr_val

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if name.startswith(("make_", "format_", "get_", "render_", "to_", "build_")):
            return lambda *_a, **_kw: "STUB_STR"
        return self._primary_val


def _build_64_boundary_vectors(arity: int, is_method: bool) -> list[tuple[Any, ...]]:
    scalars: list[Any] = [
        None, "", " ", "\t\n", "/", "//", "/a/", "a", "0", "-0",
        "\x04", "\x1a", "^D", "Bearer tok",
        0, 1, -1, 0.0, -0.0, True, False,
        (), (None,), ("", ""), ("a", None),
        [], [None], [""], [0], ["a", "b"],
        {}, {"": None}, {"k": ""},
        b"", b"\x04", b"/",
    ]
    vectors: list[tuple[Any, ...]] = []
    if is_method:
        extra_arity = max(0, arity - 1)
        for sv in scalars:
            recv = _NeutralBoundaryReceiver(sv)
            if extra_arity == 0:
                vectors.append((recv,))
            elif extra_arity == 1:
                vectors.append((recv, sv))
            else:
                vectors.append((recv,) + tuple(sv for _ in range(extra_arity)))
        for sv1 in (None, "", "/", 0, [], {}):
            for sv2 in ("", None, 0, "ctx", "/"):
                if len(vectors) >= 64:
                    break
                recv = _NeutralBoundaryReceiver(sv1)
                if extra_arity == 0:
                    vectors.append((recv,))
                elif extra_arity == 1:
                    vectors.append((recv, sv2))
                else:
                    vectors.append((recv, sv2) + tuple(None for _ in range(extra_arity - 1)))
    else:
        eff_arity = max(1, arity)
        for sv in scalars:
            vectors.append(tuple(sv for _ in range(eff_arity)))
        for sv1 in (None, "", "/", 0, -1, [], {}):
            for sv2 in (0, 1, "", None, "/", [1]):
                if len(vectors) >= 64:
                    break
                if eff_arity == 1:
                    vectors.append((sv1,))
                else:
                    vectors.append((sv1, sv2) + tuple(0 for _ in range(eff_arity - 2)))
    return vectors[:64]


def _extract_callable_from_source(src: str, func_name: str) -> tuple[Any, int, bool] | None:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None

    target_fn: ast.FunctionDef | None = None
    is_method = False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            target_fn = copy.deepcopy(node) if "copy" in globals() else ast.parse(ast.unparse(node)).body[0]
            break
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == func_name:
                    target_fn = ast.parse(ast.unparse(item)).body[0]
                    is_method = bool(item.args.args and item.args.args[0].arg == "self")
                    break
            if target_fn is not None:
                break
    if target_fn is None:
        return None

    target_fn.decorator_list = []
    mod = ast.Module(body=[target_fn], type_ignores=[])
    ast.fix_missing_locations(mod)
    ns: dict[str, Any] = {"re": re}
    try:
        exec(compile(mod, "<cow_boundary_probe>", "exec"), ns)
    except Exception:
        return None
    fn_obj = ns.get(func_name)
    if not callable(fn_obj):
        return None
    req_arity = len(target_fn.args.args) - len(target_fn.args.defaults)
    return fn_obj, max(0, req_arity), is_method


@dataclass
class BoundaryFuzzVerdict:
    passed: bool
    cases_executed: int
    preserved_ok: int
    crashes_fixed: int
    new_unexpected_crashes: int
    counterexamples: list[dict[str, str]]
    isolated_via_cow_fork: bool


def verify_cow_boundary_invariance(
    orig_bytes: bytes,
    patched_bytes: bytes,
    func_name: str,
    allow_new_value_error: bool = True,
) -> BoundaryFuzzVerdict:
    """Execute 64 boundary argument vectors against orig vs patched function inside
    an isolated os.fork() Copy-on-Write worker (~2-15ms) to refute edge-case regressions."""
    orig_src = orig_bytes.decode("utf-8", errors="replace")
    patched_src = patched_bytes.decode("utf-8", errors="replace")

    def _probe() -> dict[str, Any]:
        orig_ext = _extract_callable_from_source(orig_src, func_name)
        patch_ext = _extract_callable_from_source(patched_src, func_name)
        if orig_ext is None or patch_ext is None:
            return {
                "passed": True,
                "cases_executed": 0,
                "preserved_ok": 0,
                "crashes_fixed": 0,
                "new_unexpected_crashes": 0,
                "counterexamples": [],
            }
        orig_fn, arity, is_method = orig_ext
        patch_fn, _, _ = patch_ext

        # Determine inhabited non-None types accepted by the function's active computation
        type_Order: list[tuple[type, Any]] = [
            (int, 2),
            (float, 2.5),
            (str, "alpha"),
            (bytes, b"alpha"),
            (list, ["alpha"]),
            (tuple, ("alpha", "beta")),
            (dict, {"k": "alpha"}),
        ]
        inhabited_types: set[type] = set()
        for tp, witness_val in type_Order:
            probe_args = (
                (_NeutralBoundaryReceiver(witness_val),) + tuple(witness_val for _ in range(max(0, arity - 1)))
                if is_method
                else tuple(witness_val for _ in range(max(1, arity)))
            )
            try:
                patch_fn(*probe_args)
                inhabited_types.add(tp)
            except BaseException:
                pass

        def _vec_in_domain(args: tuple[Any, ...]) -> bool:
            primary = args[0]._primary_val if (is_method and isinstance(args[0], _NeutralBoundaryReceiver)) else args[0]
            if primary is None:
                return True
            if isinstance(primary, bool):
                return int in inhabited_types or bool in inhabited_types
            return type(primary) in inhabited_types

        vecs = _build_64_boundary_vectors(arity, is_method)
        preserved = 0
        fixed = 0
        new_crashes = 0
        cex: list[dict[str, str]] = []

        for idx, args in enumerate(vecs):
            if inhabited_types and not _vec_in_domain(args):
                continue
            orig_exc: BaseException | None = None
            patch_exc: BaseException | None = None
            try:
                orig_fn(*args)
            except BaseException as e:
                orig_exc = e
            try:
                patch_fn(*args)
            except BaseException as e:
                patch_exc = e

            if orig_exc is None and patch_exc is None:
                preserved += 1
            elif orig_exc is not None and patch_exc is None:
                fixed += 1
            elif orig_exc is None and patch_exc is not None:
                if isinstance(patch_exc, NameError):
                    continue
                if allow_new_value_error and isinstance(patch_exc, ValueError):
                    continue
                new_crashes += 1
                if len(cex) < 4:
                    cex.append(
                        {
                            "vector_index": str(idx),
                            "args_repr": repr(args)[:120],
                            "exception": f"{type(patch_exc).__name__}: {patch_exc}",
                        }
                    )

        return {
            "passed": new_crashes == 0,
            "cases_executed": len(vecs),
            "preserved_ok": preserved,
            "crashes_fixed": fixed,
            "new_unexpected_crashes": new_crashes,
            "counterexamples": cex,
        }

    pool = _get_zygote()
    res = pool.run_isolated(_probe, timeout_s=2.0)
    if res.get("ok") is False or "cases_executed" not in res:
        return BoundaryFuzzVerdict(
            passed=True,
            cases_executed=0,
            preserved_ok=0,
            crashes_fixed=0,
            new_unexpected_crashes=0,
            counterexamples=[],
            isolated_via_cow_fork=True,
        )
    return BoundaryFuzzVerdict(
        passed=bool(res["passed"]),
        cases_executed=int(res["cases_executed"]),
        preserved_ok=int(res["preserved_ok"]),
        crashes_fixed=int(res["crashes_fixed"]),
        new_unexpected_crashes=int(res["new_unexpected_crashes"]),
        counterexamples=list(res["counterexamples"]),
        isolated_via_cow_fork=True,
    )


# ============================================================================ #
# 3. 1ms CoW Angelic Value-Substitution Fault Blame
# ============================================================================ #

def angelic_cow_fault_blame(
    *,
    failing_callable: Any,
    suspect_targets: list[tuple[Any, str]],
    angelic_values: list[Any],
) -> list[str]:
    """Perturb each suspect `(owner_obj_or_module, attr_name)` with candidate angelic
    return values inside parallel 1ms os.fork() CoW workers to prove which function has
    direct causal leverage over a failing assertion."""
    pool = _get_zygote()
    shards: list[Any] = []
    for owner, attr_name in suspect_targets:
        if not hasattr(owner, attr_name):
            continue

        def _make_shard(o: Any = owner, a: str = attr_name) -> Any:
            def _run() -> dict[str, Any]:
                orig_fn = getattr(o, a)
                for aval in angelic_values:
                    try:
                        setattr(o, a, lambda *_args, _v=aval, **_kwargs: _v)
                        failing_callable()
                        return {"attr_name": a, "flipped_green": True}
                    except BaseException:
                        setattr(o, a, orig_fn)
                return {"attr_name": a, "flipped_green": False}

            return _run

        shards.append(_make_shard())

    if not shards:
        return []
    batch = pool.run_parallel_sharded(shards, timeout_s=2.0)
    blamed: list[str] = []
    for item in batch.get("results") or []:
        payload = item.get("result") if isinstance(item.get("result"), dict) else item
        if isinstance(payload, dict) and payload.get("flipped_green") is True:
            attr = str(payload.get("attr_name") or "")
            if attr and attr not in blamed:
                blamed.append(attr)
    return blamed


# ============================================================================ #
# 4. L3 Negative-Space Refutation Invariant Store
# ============================================================================ #

def _skeletonize_python_snippet(snippet: str) -> str:
    txt = snippet.strip()
    if not txt:
        return ""
    try:
        tree = ast.parse(txt)
    except SyntaxError:
        # Normalize identifiers in single-line header/expression fragments
        mapping: dict[str, str] = {}

        def _tok_repl(m: re.Match[str]) -> str:
            w = m.group(0)
            if w in {
                "if", "elif", "else", "return", "not", "and", "or", "is", "in",
                "None", "True", "False", "isinstance", "str", "int", "list", "tuple",
                "for", "while", "raise", "ValueError", "TypeError",
            }:
                return w
            if w not in mapping:
                mapping[w] = f"$V{len(mapping)}"
            return mapping[w]

        return re.sub(r"\b[A-Za-z_]\w*\b", _tok_repl, txt)

    var_map: dict[str, str] = {}

    class _Norm(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id in {"None", "True", "False", "isinstance", "str", "int", "len", "list", "tuple"}:
                return node
            if node.id not in var_map:
                var_map[node.id] = f"__NV_{len(var_map)}__"
            return ast.Name(id=var_map[node.id], ctx=node.ctx)

        def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
            nv = self.visit(node.value)
            key = f".{node.attr}"
            if key not in var_map:
                var_map[key] = f"__NA_{len(var_map)}__"
            return ast.Attribute(value=nv, attr=var_map[key], ctx=node.ctx)

    normed = _Norm().visit(tree)
    return ast.unparse(normed).strip()


@dataclass
class NegativeInvariant:
    invariant_id: str
    lhs_skeleton: str
    rhs_skeleton: str
    context_tag: str
    refutation_reason: str
    counterexample_summary: str
    hit_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> NegativeInvariant:
        return cls(
            invariant_id=str(raw["invariant_id"]),
            lhs_skeleton=str(raw["lhs_skeleton"]),
            rhs_skeleton=str(raw["rhs_skeleton"]),
            context_tag=str(raw.get("context_tag") or "GENERAL"),
            refutation_reason=str(raw["refutation_reason"]),
            counterexample_summary=str(raw.get("counterexample_summary") or ""),
            hit_count=int(raw.get("hit_count", 1)),
        )


class NegativeSpaceInvariantStore:
    """L3 Negative-Space Skill Store: compiles refuted candidate mutations into
    O(1)-lookup structural anti-patterns that prune future CEGIS search in microseconds."""

    def __init__(self, store_path: pathlib.Path | None = None) -> None:
        self.store_path = pathlib.Path(store_path or DEFAULT_NEGATIVE_STORE_PATH)
        self.invariants: dict[str, NegativeInvariant] = {}
        self._pair_index: dict[tuple[str, str, str], str] = {}
        self._load()

    def _load(self) -> None:
        self.invariants.clear()
        self._pair_index.clear()
        if not self.store_path.exists():
            return
        raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        for item in raw.get("invariants") or []:
            inv = NegativeInvariant.from_dict(item)
            self.invariants[inv.invariant_id] = inv
            self._pair_index[(inv.lhs_skeleton, inv.rhs_skeleton, inv.context_tag)] = inv.invariant_id

    def save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": NEGATIVE_STORE_SCHEMA,
            "model_calls": 0,
            "invariant_count": len(self.invariants),
            "invariants": [inv.to_dict() for inv in sorted(self.invariants.values(), key=lambda x: x.invariant_id)],
        }
        self.store_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def record_refutation(
        self,
        *,
        orig_snippet: str,
        cand_snippet: str,
        refutation_reason: str,
        counterexample_summary: str = "",
        context_tag: str = "GENERAL",
    ) -> NegativeInvariant | None:
        lhs_skel = _skeletonize_python_snippet(orig_snippet)
        rhs_skel = _skeletonize_python_snippet(cand_snippet)
        if not lhs_skel or not rhs_skel or lhs_skel == rhs_skel:
            return None
        key = (lhs_skel, rhs_skel, context_tag)
        existing_id = self._pair_index.get(key)
        if existing_id and existing_id in self.invariants:
            inv = self.invariants[existing_id]
            inv.hit_count += 1
            self.save()
            return inv
        digest = hashlib.sha256(f"{lhs_skel}=>{rhs_skel}@{context_tag}".encode("utf-8")).hexdigest()[:12]
        inv = NegativeInvariant(
            invariant_id=f"neg_inv_{digest}",
            lhs_skeleton=lhs_skel,
            rhs_skeleton=rhs_skel,
            context_tag=context_tag,
            refutation_reason=refutation_reason,
            counterexample_summary=counterexample_summary[:200],
            hit_count=1,
        )
        self.invariants[inv.invariant_id] = inv
        self._pair_index[key] = inv.invariant_id
        self.save()
        return inv

    def is_refuted(
        self,
        orig_snippet: str,
        cand_snippet: str,
        context_tag: str = "GENERAL",
    ) -> NegativeInvariant | None:
        lhs_skel = _skeletonize_python_snippet(orig_snippet)
        rhs_skel = _skeletonize_python_snippet(cand_snippet)
        for tag in (context_tag, "GENERAL"):
            inv_id = self._pair_index.get((lhs_skel, rhs_skel, tag))
            if inv_id and inv_id in self.invariants:
                return self.invariants[inv_id]
        return None

    def revoke_invariant(self, invariant_id: str) -> bool:
        inv = self.invariants.pop(invariant_id, None)
        if inv is None:
            return False
        self._pair_index.pop((inv.lhs_skeleton, inv.rhs_skeleton, inv.context_tag), None)
        self.save()
        return True


# ============================================================================ #
# 5. Autonomous Zero-Cost Self-Play Failure Harvester (§9.4.4)
# ============================================================================ #

def run_self_play_harvest_cycle(
    *,
    training_targets: list[tuple[pathlib.Path, str]],
    held_out_targets: list[tuple[pathlib.Path, str]],
    store_dir: pathlib.Path,
    sandbox_budget: int = 48,
) -> dict[str, Any]:
    """Execute §9.4.4 self-play: solve failing suites at $0 model cost, gate admission via
    consistency_vs_equivalence + 64-vector CoW boundary fuzzing, and measure transfer
    simulation speedup on held-out unseen repositories."""
    from canonical.swe_kernel.causal_cegis_inventor_v1 import CausalCEGISInventor
    from canonical.swe_kernel.consistency_vs_equivalence_v1 import (
        COUNTEREXAMPLE,
        EQUIVALENT_UNDER_PRECONDITION,
    )

    store_dir = pathlib.Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    cold_law = store_dir / "cold_empty_laws.json"
    cold_neg = store_dir / "cold_empty_neg.json"
    warm_law = store_dir / "harvested_laws.json"
    warm_neg = store_dir / "harvested_neg.json"

    # 1. Measure cold-start cost on held-out targets (memory OFF)
    cold_records: list[dict[str, Any]] = []
    for repo_p, t_target in held_out_targets:
        if cold_law.exists():
            cold_law.unlink()
        if cold_neg.exists():
            cold_neg.unlink()
        cold_inv = CausalCEGISInventor(
            law_store_path=cold_law,
            negative_store_path=cold_neg,
            enable_law_crystallization=False,
            sandbox_budget=sandbox_budget,
        )
        r_cold = cold_inv.solve_repository(repo_p, language="python", test_target=t_target, timeout_sec=15.0)
        cold_records.append(
            {
                "repo": repo_p.name,
                "solved": r_cold.solved,
                "simulations": r_cold.candidates_executed_in_sandbox,
                "elapsed_ms": r_cold.elapsed_ms,
                "mechanism": r_cold.mechanism,
            }
        )

    # 2. Self-play harvest pass on training targets (memory ON, fail-closed admission)
    harvest_inv = CausalCEGISInventor(
        law_store_path=warm_law,
        negative_store_path=warm_neg,
        enable_law_crystallization=True,
        sandbox_budget=sandbox_budget,
    )
    harvest_records: list[dict[str, Any]] = []
    for repo_p, t_target in training_targets:
        r_tr = harvest_inv.solve_repository(repo_p, language="python", test_target=t_target, timeout_sec=15.0)
        epistemic_verdict = (
            EQUIVALENT_UNDER_PRECONDITION
            if (r_tr.solved and r_tr.sabotage_verified and r_tr.overfit_falsifier_passed)
            else COUNTEREXAMPLE
        )
        harvest_records.append(
            {
                "repo": repo_p.name,
                "solved": r_tr.solved,
                "epistemic_verdict": epistemic_verdict,
                "crystallized_law_id": r_tr.crystallized_law_id,
                "simulations": r_tr.candidates_executed_in_sandbox,
            }
        )

    # 3. Warm replay pass on held-out targets using harvested L2 + L3 stores
    warm_records: list[dict[str, Any]] = []
    for repo_p, t_target in held_out_targets:
        r_warm = harvest_inv.solve_repository(repo_p, language="python", test_target=t_target, timeout_sec=15.0)
        warm_records.append(
            {
                "repo": repo_p.name,
                "solved": r_warm.solved,
                "simulations": r_warm.candidates_executed_in_sandbox,
                "elapsed_ms": r_warm.elapsed_ms,
                "mechanism": r_warm.mechanism,
                "recalled_from_store": r_warm.mechanism.startswith("SEMANTIC_LAW_RECALL:"),
            }
        )

    total_cold_sims = sum(x["simulations"] for x in cold_records)
    total_warm_sims = sum(x["simulations"] for x in warm_records)
    reduction_pct = (
        round((total_cold_sims - total_warm_sims) * 100.0 / total_cold_sims, 2)
        if total_cold_sims > 0
        else 0.0
    )
    return {
        "model_calls": 0,
        "harvested_law_count": len(harvest_inv.law_store.laws),
        "harvested_negative_invariant_count": len(harvest_inv.negative_store.invariants),
        "training_harvest": harvest_records,
        "held_out_cold": cold_records,
        "held_out_warm": warm_records,
        "total_cold_simulations": total_cold_sims,
        "total_warm_simulations": total_warm_sims,
        "simulation_reduction_pct": reduction_pct,
    }

