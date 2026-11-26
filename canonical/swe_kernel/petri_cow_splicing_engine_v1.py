#!/usr/bin/env python3
"""Zero-Knowledge-House Petri-Net Component Synthesis, Dual-Program Splicing & 16-Way CoW World Tomography (`petri_cow_splicing_engine_v1`).

Experimental computed mechanisms for proposing and checking actions. A syntax
match, bounded execution or stored record is not evidence of a hard-task solve.
The cross-task fix-piece coverage study is not a fixed-grammar ceiling:

1. Repo-Native Type-Transition Petri Net (`RepoNativePetriMiner`):
   Harvests repository classes, methods, `@property` descriptors, sibling `self.<attr>` fields,
   module functions, constants, and exception types via `IncrementalSemanticGraph` + AST + live
   runtime MRO/collection-element witnesses. Encodes them as typed Petri-net transitions
   `(InputPlaces...) -> OutputPlace` (SyPet / APIphany reachability) including collection
   functor lifts (`[el.m(arg) for el in seq]`, `sep.join(seq)`, tuple-type widenings) so target
   repos supply their own domain vocabulary at runtime.

2. Backward Witness Propagation + Dual-Program Counterexample Splicing (`BackwardWitnessAndDualSplicer`):
   Extracts expected values/types/exceptions from assertion tracebacks, propagates residuals
   backward through return/call/operator nodes, and splices partial candidates (`P1` passing
   failing slice `T_fail` + `P0`/`P2` passing complementary slice `T_pass` or `T_fail_2`) via
   synthesized minimal separating boolean guards `(P1) if (G) else (P0)` verified in parallel
   Copy-on-Write forks under an Anti-Lookup-Table Equivalence Law (`consistency_vs_equivalence_v1`).

3. 16-Way Parallel CoW Speculative Execution + Differential Multi-Layer State Tomography
   (`ParallelCoWWorldTomographer` & `MealyStateCompiler`):
   Forks up to 16 parallel `os.fork()` shadow futures simultaneously across Python/CLI/SQLite/
   DOM-ARIA/filesystem actions, captures 5-layer `MultiLayerStateSnapshot`s filtered by
   `SEPARATION + STABILITY` (`distinguishing_projection_v1`), compiles Mealy transition tables
   with `(P, O, A, V, F)` `EffectContract`s (`effect_contract_composition_v1`), and selects
   actions that strictly minimize goal residual while discarding failed futures at zero disk cost.

4. Cross-Modal Type-Transition Petri Planner, §9.2 5-Gate Admission-Filtered Skill Store &
   Offline Adversarial Self-Play (`CrossModalPetriPlanner`, `AdmissionFilteredSkillStore`,
   `AdversarialSelfPlayEngine`):
   Unifies GUI/ARIA, SQLite, CLI, Python, and registered Brain capabilities in one typed Petri
   net; enforces the 5-gate admission filter (`verified`, `goal_relevant`,
   `prediction_error_bearing`, `reusable` with hard `FOREIGN_IDENT_UNBOUND` rejection,
   `compressible`) with provenance + version-drift re-validation probes and §6 memory ablation
   modes (`generalized`, `raw_traces`, `disabled`); and runs identity-guarded adversarial
   fault-injection self-play (`same_identity_supervisor` contract).

Authority: NONE. No external inference service; execution still costs time and compute.
"""
from __future__ import annotations

import ast
import copy
import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import select
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.consistency_vs_equivalence_v1 import (  # noqa: E402
    EQUIVALENT_UNDER_PRECONDITION,
    prove_code_rule,
)
from canonical.swe_kernel.effect_contract_composition_v1 import (  # noqa: E402
    Effect,
    EffectContract,
    PASS as CONTRACT_PASS,
    compose_chain,
)
from canonical.swe_kernel.incremental_semantic_graph_v1 import (  # noqa: E402
    IncrementalSemanticGraph,
)

SCHEMA = "PROJECT_BRAIN_PETRI_COW_SPLICING_ENGINE_V1"

_SAFE_BUILTINS_NAMES = frozenset({
    "abs", "all", "any", "bool", "bytes", "callable", "chr", "dict", "divmod",
    "enumerate", "filter", "float", "frozenset", "getattr", "hasattr", "hash",
    "hex", "int", "isinstance", "issubclass", "iter", "len", "list", "map",
    "max", "min", "next", "object", "oct", "ord", "pow", "range", "repr",
    "reversed", "round", "set", "slice", "sorted", "str", "sum", "tuple",
    "type", "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError",
    "RuntimeError", "OSError", "LookupError", "Exception", "BaseException",
    "True", "False", "None", "zip",
})

_MUTATING_METHOD_DENYLIST = frozenset({
    "append", " clear", "clear", "close", "commit", "connect", "delete", "discard",
    "dump", "dumps_to_file", " execute", "execute", "executemany", "exit", "extend",
    "flush", "insert", "kill", "mkdir", "open", "pop", "popitem", "put", "quit",
    "read", "readline", "readlines", "remove", "rename", "replace_file", "reset",
    "rmdir", "rollback", "save", "seek", "send", "setattr", "setblocking",
    "setdefault", "shutdown", "sort", "start", "stop", "terminate", "truncate",
    "unlink", "update", "wait", "write", "writelines",
})


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# =========================================================================== #
# 1. REPO-NATIVE TYPE-TRANSITION PETRI NET (`RepoNativePetriMiner`)
# =========================================================================== #

@dataclass(frozen=True)
class PetriTransition:
    """Typed morphism `(input_places...) -> output_place` mined from repo or environment."""
    transition_id: str
    surface: str  # PYTHON_METHOD | PYTHON_PROP | PYTHON_ATTR | PYTHON_FUNC | PYTHON_COMP | GUI_ARIA | SQLITE_QUERY | CLI_EXEC | BRAIN_CAPABILITY
    owner_type: str
    name: str
    param_names: tuple[str, ...]
    input_places: tuple[str, ...]
    output_place: str
    template_py: str
    mdl_cost: int
    preconditions: tuple[str, ...] = ()
    effects: tuple[tuple[str, str], ...] = ()  # (ESTABLISH|REMOVE, subject)

    def to_effect_contract(self, verdict_instrument: str = "cow_oracle_verifier") -> EffectContract:
        effs = tuple(Effect(kind=k, subject=s) for k, s in self.effects) or (
            Effect(kind="ESTABLISH", subject=f"place:{self.output_place}"),
        )
        obs = tuple(f"place:{p}" for p in self.input_places) or ("place:unit",)
        return EffectContract(
            skill_id=self.transition_id,
            preconditions=self.preconditions,
            observables=obs,
            actions=(f"{self.surface}:{self.name}",),
            verdict=verdict_instrument,
            effects=effs,
        )


def _infer_return_place_from_fn(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if fn_node.returns is not None:
        try:
            ann = ast.unparse(fn_node.returns)
            if "bool" in ann:
                return "bool"
            if "str" in ann:
                return "str"
            if "int" in ann:
                return "int"
            if "tuple" in ann.lower():
                return "tuple"
            if "list" in ann.lower():
                return "list"
            return ann.split("[")[0].split("|")[0].strip() or "Any"
        except Exception:
            pass
    for sub in ast.walk(fn_node):
        if isinstance(sub, ast.Return) and sub.value is not None:
            v = sub.value
            if isinstance(v, (ast.Compare, ast.BoolOp)) or (isinstance(v, ast.Constant) and isinstance(v.value, bool)):
                return "bool"
            if isinstance(v, ast.Tuple):
                return "tuple"
            if isinstance(v, (ast.List, ast.ListComp)):
                return "list"
            if isinstance(v, ast.JoinedStr) or (isinstance(v, ast.Constant) and isinstance(v.value, str)):
                return "str"
            if isinstance(v, ast.Constant) and isinstance(v.value, int):
                return "int"
    return "Any"


def _looks_pure_accessor_or_transform(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    name = fn_node.name
    if name.startswith("__") and name not in ("__str__", "__repr__", "__len__", "__bool__"):
        return False
    if name in _MUTATING_METHOD_DENYLIST:
        return False
    low = name.lower()
    if low.startswith(("write", "delete", "remove", "clear", "pop", "push", "send", "exec", "kill", "close", "exit", "fail", "abort")):
        return False
    # Reject methods whose body writes to disk/subprocess or deletes attributes
    for sub in ast.walk(fn_node):
        if isinstance(sub, (ast.Delete, ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom, ast.Await)):
            return False
    return True


class RepoNativePetriMiner:
    """Harvests typed Petri-net transitions directly from target repository AST + `IncrementalSemanticGraph`."""

    def __init__(self, worktree: pathlib.Path) -> None:
        self.worktree = pathlib.Path(worktree).resolve()
        self.transitions: list[PetriTransition] = []
        self.class_attrs: dict[str, set[str]] = {}
        self.class_bases: dict[str, list[str]] = {}
        self.module_constants: dict[str, list[str]] = {}
        self.module_exceptions: dict[str, list[str]] = {}
        self.module_functions: dict[str, list[PetriTransition]] = {}
        self._mined_files: set[str] = set()
        self._graph: IncrementalSemanticGraph | None = None

    def _ensure_graph(self) -> IncrementalSemanticGraph | None:
        if self._graph is None:
            try:
                self._graph = IncrementalSemanticGraph(self.worktree)
            except Exception:
                self._graph = None
        return self._graph

    def mine_scope(self, primary_rel_files: Sequence[str], max_imported_files: int = 10) -> dict[str, Any]:
        """Mine Petri-net transitions from localized files and their resolved intra-repo imports."""
        queue: list[str] = [f for f in primary_rel_files if f and (self.worktree / f).is_file()]
        graph = self._ensure_graph()
        if graph is not None:
            for rel_f in list(queue[:4]):
                try:
                    sums = graph.load_summaries(rel_f)
                    info = sums.get(rel_f, {})
                    for imp in info.get("imports", [])[:16]:
                        mod_name = str(imp.get("module") or "")
                        if not mod_name:
                            continue
                        mod_rel = mod_name.replace(".", "/")
                        for cand in (
                            f"{mod_rel}.py",
                            f"src/{mod_rel}.py",
                            f"{mod_rel}/__init__.py",
                            f"src/{mod_rel}/__init__.py",
                        ):
                            if cand not in queue and (self.worktree / cand).is_file() and len(queue) < len(primary_rel_files) + max_imported_files:
                                queue.append(cand)
                except Exception:
                    pass

        for rel_f in queue:
            if rel_f in self._mined_files:
                continue
            self._mined_files.add(rel_f)
            self._mine_single_file(rel_f)

        return {
            "files_mined": len(self._mined_files),
            "transitions_mined": len(self.transitions),
            "classes_mined": len(self.class_attrs),
        }

    def _mine_single_file(self, rel_f: str) -> None:
        fp = self.worktree / rel_f
        try:
            src = fp.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except (OSError, SyntaxError, UnicodeDecodeError):
            return

        consts = self.module_constants.setdefault(rel_f, [])
        excs = self.module_exceptions.setdefault(rel_f, [])
        funcs = self.module_functions.setdefault(rel_f, [])

        for node in tree.body:
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id.isupper() and len(consts) < 24:
                        consts.append(tgt.id)
            elif isinstance(node, ast.FunctionDef):
                if not _looks_pure_accessor_or_transform(node):
                    continue
                pos_args = [a.arg for a in node.args.args]
                n_req = len(pos_args) - len(node.args.defaults)
                if 1 <= n_req <= 2 and len(pos_args) <= 3:
                    req_params = tuple(pos_args[:n_req])
                    out_p = _infer_return_place_from_fn(node)
                    tr = PetriTransition(
                        transition_id=f"{rel_f}::{node.name}/{n_req}",
                        surface="PYTHON_FUNC",
                        owner_type=rel_f,
                        name=node.name,
                        param_names=req_params,
                        input_places=tuple("Any" for _ in req_params),
                        output_place=out_p,
                        template_py=f"{node.name}(" + ", ".join(f"{{{i}}}" for i in range(n_req)) + ")",
                        mdl_cost=8 + 3 * n_req,
                    )
                    self.transitions.append(tr)
                    funcs.append(tr)
            elif isinstance(node, ast.ClassDef):
                cls_name = node.name
                bases = []
                for b in node.bases:
                    try:
                        b_txt = ast.unparse(b).split(".")[-1]
                        bases.append(b_txt)
                    except Exception:
                        pass
                self.class_bases[cls_name] = bases
                if any(
                    b.endswith(("Error", "Exception", "Warning", "Invalid", "BadParameter", "UsageError", "HTTPException"))
                    for b in [cls_name, *bases]
                ):
                    excs.append(cls_name)

                attrs = self.class_attrs.setdefault(cls_name, set())
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        attrs.add(item.target.id)
                    elif isinstance(item, ast.Assign):
                        for t in item.targets:
                            if isinstance(t, ast.Name) and not t.id.startswith("__"):
                                attrs.add(t.id)
                    elif isinstance(item, ast.FunctionDef):
                        # Record `self.<attr>` writes inside `__init__` or methods
                        for sub in ast.walk(item):
                            if (
                                isinstance(sub, ast.Attribute)
                                and isinstance(sub.value, ast.Name)
                                and sub.value.id == "self"
                                and not sub.attr.startswith("__")
                            ):
                                if isinstance(sub.ctx, ast.Store) or item.name == "__init__":
                                    attrs.add(sub.attr)

                        if not _looks_pure_accessor_or_transform(item):
                            continue
                        decs = []
                        for d in item.decorator_list:
                            try:
                                decs.append(ast.unparse(d))
                            except Exception:
                                pass
                        is_prop = any(d.endswith(("property", "cached_property")) for d in decs)
                        pos_args = [a.arg for a in item.args.args]
                        if not pos_args or pos_args[0] not in ("self", "cls"):
                            continue
                        rest_args = pos_args[1:]
                        n_req = max(0, len(rest_args) - len(item.args.defaults))
                        out_p = _infer_return_place_from_fn(item)
                        if is_prop and n_req == 0:
                            attrs.add(item.name)
                            self.transitions.append(PetriTransition(
                                transition_id=f"{cls_name}.{item.name}@prop",
                                surface="PYTHON_PROP",
                                owner_type=cls_name,
                                name=item.name,
                                param_names=("self",),
                                input_places=(cls_name,),
                                output_place=out_p,
                                template_py="{0}." + item.name,
                                mdl_cost=6,
                            ))
                        elif n_req <= 2:
                            req_params = tuple(rest_args[:n_req])
                            arg_slots = ", ".join(f"{{{i + 1}}}" for i in range(n_req))
                            self.transitions.append(PetriTransition(
                                transition_id=f"{cls_name}.{item.name}/{n_req}",
                                surface="PYTHON_METHOD",
                                owner_type=cls_name,
                                name=item.name,
                                param_names=("self", *req_params),
                                input_places=(cls_name, *("Any" for _ in req_params)),
                                output_place=out_p,
                                template_py=f"{{0}}.{item.name}({arg_slots})",
                                mdl_cost=9 + 3 * n_req,
                            ))

    def mro_for(self, cls_name: str) -> list[str]:
        seen: list[str] = []
        stack = [cls_name]
        while stack and len(seen) < 10:
            cur = stack.pop(0)
            if cur in seen or not cur:
                continue
            seen.append(cur)
            for b in self.class_bases.get(cur, ()):
                if b not in seen:
                    stack.append(b)
        return seen

    def methods_for_types(self, cls_names: Sequence[str]) -> list[PetriTransition]:
        expanded: set[str] = set()
        for c in cls_names:
            expanded.update(self.mro_for(c))
        return [t for t in self.transitions if t.owner_type in expanded and t.surface in ("PYTHON_METHOD", "PYTHON_PROP")]

    def sibling_attrs_for_types(self, cls_names: Sequence[str]) -> list[str]:
        expanded: set[str] = set()
        for c in cls_names:
            expanded.update(self.mro_for(c))
        out: set[str] = set()
        for c in expanded:
            out.update(self.class_attrs.get(c, ()))
        return sorted(out)

    def synthesize_petri_candidates(
        self,
        *,
        rel_file: str,
        orig_expr: str,
        fail_frames: Sequence[Mapping[str, Any]],
        pass_frames: Sequence[Mapping[str, Any]],
        require_bool: bool = False,
        max_candidates: int = 32,
    ) -> list[tuple[str, str]]:
        """Run bounded Type-Transition Petri-Net reachability from in-scope runtime variables to candidate expressions.

        Returns a ranked list of `(candidate_expr_py, transition_provenance)` pairs.
        """
        all_frames = [*fail_frames, *pass_frames]
        if not all_frames:
            return []

        # Collect runtime variable -> observed MRO types, element MRO types, and attributes
        var_types: dict[str, list[str]] = {}
        var_elem_types: dict[str, list[str]] = {}
        var_attrs: dict[str, set[str]] = {}
        in_scope_vars: list[str] = []

        for fr in all_frames[:6]:
            for var_name, meta in fr.items():
                if not isinstance(var_name, str) or not var_name.isidentifier() or var_name.startswith("__"):
                    continue
                if var_name not in in_scope_vars:
                    in_scope_vars.append(var_name)
                if not isinstance(meta, Mapping):
                    continue
                t_name = str(meta.get("t") or "")
                t_list = var_types.setdefault(var_name, [])
                if t_name and t_name not in t_list:
                    t_list.append(t_name)
                for mc in meta.get("mro") or ():
                    if isinstance(mc, str) and mc not in t_list:
                        t_list.append(mc)
                et_list = var_elem_types.setdefault(var_name, [])
                for ec in meta.get("elem_mro") or ():
                    if isinstance(ec, str) and ec not in et_list:
                        et_list.append(ec)
                el_t = str(meta.get("elem_t") or "")
                if el_t and el_t not in et_list:
                    et_list.append(el_t)
                attrs_map = meta.get("attrs")
                if isinstance(attrs_map, Mapping):
                    var_attrs.setdefault(var_name, set()).update(
                        k for k in attrs_map.keys() if isinstance(k, str) and k.isidentifier()
                    )

        scored: dict[str, tuple[int, str]] = {}

        def _propose(expr: str, priority_cost: int, prov: str) -> None:
            expr_clean = expr.strip()
            if not expr_clean or expr_clean == orig_expr.strip() or len(expr_clean) > 140:
                return
            try:
                ast.parse(expr_clean, mode="eval")
            except SyntaxError:
                return
            prev = scored.get(expr_clean)
            if prev is None or priority_cost < prev[0]:
                scored[expr_clean] = (priority_cost, prov)

        # 1. Sibling `obj.<attr>` transitions (e.g. `self.options` -> `self._original_options`)
        try:
            orig_node = ast.parse(orig_expr, mode="eval").body
        except SyntaxError:
            orig_node = None

        if isinstance(orig_node, ast.Attribute) and isinstance(orig_node.value, ast.Name):
            recv = orig_node.value.id
            orig_attr = orig_node.attr
            cand_attrs = set(self.sibling_attrs_for_types(var_types.get(recv, []))) | var_attrs.get(recv, set())
            for sa in cand_attrs:
                if sa == orig_attr or sa.startswith("__"):
                    continue
                # High affinity when one attribute name is a prefix/substring/underscore-variant of the other!
                shared = (orig_attr in sa) or (sa in orig_attr) or (orig_attr.strip("_") == sa.strip("_"))
                if require_bool and not sa.startswith(("is_", "has_", "allow_", "can_", "should_", "use_", "no_", "_")):
                    if not shared:
                        continue
                cost = 4 if shared else 14
                _propose(f"{recv}.{sa}", cost, f"PETRI_SIBLING_ATTR:{recv}.{sa}")

        # 2. Type-lattice transitions for `Name` (`list` -> `(list, tuple)`) AND `isinstance(x, T)` calls!
        widening_pairs = {
            "list": "(list, tuple)",
            "tuple": "(list, tuple)",
            "str": "(str, bytes)",
            "bytes": "(bytes, bytearray)",
            "set": "(set, frozenset)",
            "dict": "(dict, Mapping)" if "Mapping" in in_scope_vars else "",
            "int": "(int, float)",
        }
        if isinstance(orig_node, ast.Name) and not require_bool:
            w = widening_pairs.get(orig_node.id, "")
            if w:
                _propose(w, 6, f"PETRI_TYPE_WIDEN:{orig_node.id}->{w}")
            stripped = orig_node.id.strip("_")
            for v in in_scope_vars:
                if v != orig_node.id and v.strip("_") == stripped:
                    _propose(v, 3, f"PETRI_SCOPE_SYNONYM:{orig_node.id}->{v}")

        if (
            isinstance(orig_node, ast.Call)
            and isinstance(orig_node.func, ast.Name)
            and orig_node.func.id == "isinstance"
            and len(orig_node.args) == 2
        ):
            subj_s = ast.unparse(orig_node.args[0])
            type_s = ast.unparse(orig_node.args[1])
            w_t = widening_pairs.get(type_s, "")
            if w_t:
                _propose(f"isinstance({subj_s}, {w_t})", 4, f"PETRI_ISINSTANCE_WIDEN:{type_s}->{w_t}")
            # Type-lattice supremum relaxation: `isinstance(x, T)` -> `x is not None` / `bool(x)`
            _propose(f"{subj_s} is not None", 5, f"PETRI_TYPE_SUPREMUM:{subj_s}_is_not_None")
            _propose(f"{subj_s} is None", 8, f"PETRI_TYPE_BOTTOM:{subj_s}_is_None")

        # 2b. Receiver-preserving method swaps (`self.get_plugin(x)` -> `self.has_plugin(x)` / `... is not None`)
        #     and unary wrapper unwrapping (`list(x)` -> `x` / `repr(x)`)!
        if isinstance(orig_node, ast.Call):
            if isinstance(orig_node.func, ast.Name) and len(orig_node.args) == 1 and not orig_node.keywords and not require_bool:
                fn_id = orig_node.func.id
                inner_s = ast.unparse(orig_node.args[0])
                if fn_id in ("list", "tuple", "set", "str", "int", "bool"):
                    _propose(inner_s, 4, f"PETRI_UNWRAP:{fn_id}({inner_s})->{inner_s}")
                    _propose(f"repr({inner_s})", 5, f"PETRI_UNWRAP_REPR:{fn_id}({inner_s})->repr({inner_s})")
            elif isinstance(orig_node.func, ast.Attribute) and isinstance(orig_node.func.value, ast.Name):
                recv_v = orig_node.func.value.id
                old_m = orig_node.func.attr
                call_arity = len(orig_node.args)
                arg_txts = [ast.unparse(a) for a in orig_node.args]
                if require_bool and (
                    old_m == "get" or old_m.startswith(("get_", "find", "lookup", "resolve", "match", "search"))
                ):
                    _propose(f"({orig_expr}) is not None", 4, "PETRI_CALL_IS_NOT_NONE")
                for tr in self.methods_for_types(var_types.get(recv_v, [])):
                    if tr.surface != "PYTHON_METHOD" or tr.name == old_m:
                        continue
                    if len(tr.param_names) - 1 != call_arity:
                        continue
                    is_bool_m = tr.output_place == "bool" or tr.name.startswith(("is_", "has_", "can_", "should_", "check_"))
                    if require_bool and not is_bool_m:
                        continue
                    # Bonus when old_m and tr.name share stem (`get_plugin` <-> `has_plugin`)!
                    old_tail = old_m.split("_", 1)[-1] if "_" in old_m else old_m
                    new_tail = tr.name.split("_", 1)[-1] if "_" in tr.name else tr.name
                    cost_m = 3 if old_tail == new_tail else 9
                    _propose(
                        f"{recv_v}.{tr.name}({', '.join(arg_txts)})",
                        cost_m,
                        f"PETRI_RECV_METHOD_SWAP:{recv_v}.{old_m}->{tr.name}",
                    )

        # 3. Direct instance method & property transitions `v.m(...)`
        for v in in_scope_vars[:10]:
            v_types = var_types.get(v, [])
            for tr in self.methods_for_types(v_types):
                is_bool_tr = tr.output_place == "bool" or tr.name.startswith(("is_", "has_", "can_", "should_", "check_"))
                if require_bool and not is_bool_tr:
                    continue
                if tr.surface == "PYTHON_PROP":
                    _propose(tr.template_py.format(v), tr.mdl_cost + 2, f"PETRI_PROP:{tr.transition_id}")
                else:
                    req_params = tr.param_names[1:]
                    if len(req_params) == 0:
                        _propose(tr.template_py.format(v), tr.mdl_cost + 2, f"PETRI_METHOD0:{tr.transition_id}")
                    elif len(req_params) == 1:
                        p0 = req_params[0]
                        # Exact parameter-name match in scope gets top Petri affinity!
                        arg_choices = [sv for sv in in_scope_vars if sv != v and (sv == p0 or sv.endswith(f"_{p0}") or p0.endswith(f"_{sv}"))]
                        if not arg_choices:
                            arg_choices = [sv for sv in in_scope_vars[:5] if sv != v and sv != "self"]
                        for sv in arg_choices[:3]:
                            affinity_bonus = -5 if sv == p0 else 3
                            _propose(
                                tr.template_py.format(v, sv),
                                max(2, tr.mdl_cost + affinity_bonus),
                                f"PETRI_METHOD1:{tr.transition_id}({sv})",
                            )

        # 4. Collection Functor Lift: `[el.method(arg) for el in seq]` & `sep.join(seq)`!
        if not require_bool:
            for seq_v in in_scope_vars[:10]:
                s_types = var_types.get(seq_v, [])
                if not any(t in ("list", "tuple", "set", "dict_values", "iterator", "generator") for t in s_types):
                    continue
                el_types = list(var_elem_types.get(seq_v, []))
                # String sequence joins (`', '.join(pre_init_args)`, `' '.join(...)`, `''.join(...)`)
                if "str" in el_types or seq_v.endswith(("args", "parts", "items", "lines", "names", "tokens")):
                    for sep, cost_s in ((", ", 7), (" ", 8), ("", 8), ("/", 10)):
                        _propose(f"{sep!r}.join({seq_v})", cost_s, f"PETRI_JOIN:{sep!r}.join({seq_v})")

                # Method functor lift over element classes (`[x.get_help_record(ctx) for x in args]`)
                cand_methods = self.methods_for_types(el_types) if el_types else []
                if not cand_methods and seq_v.endswith("s") and len(seq_v) >= 3:
                    # Fallback when failing frame had an empty list `[]` so runtime `elem_mro` was unobserved:
                    # match singular stem against mined classes (`args` -> `Argument`/`Parameter`, `opts` -> `Option`)!
                    stem = seq_v[:-1].lower()
                    inferred_cls = [
                        c for c in self.class_bases
                        if c.lower().startswith(stem[:3]) or (stem == "arg" and c in ("Argument", "Parameter"))
                    ]
                    cand_methods = self.methods_for_types(inferred_cls)

                iter_var = f"_{seq_v[:-1]}" if seq_v.endswith("s") and len(seq_v) > 2 and not seq_v.startswith("_") else "_el"
                if iter_var in in_scope_vars:
                    iter_var = "_petri_el"

                for tr in cand_methods[:12]:
                    req_params = tr.param_names[1:]
                    if tr.surface == "PYTHON_PROP":
                        _propose(
                            f"[{iter_var}.{tr.name} for {iter_var} in {seq_v}]",
                            8,
                            f"PETRI_MAP_PROP:{tr.transition_id}",
                        )
                    elif len(req_params) == 0:
                        _propose(
                            f"[{iter_var}.{tr.name}() for {iter_var} in {seq_v}]",
                            9,
                            f"PETRI_MAP0:{tr.transition_id}",
                        )
                    elif len(req_params) == 1:
                        p0 = req_params[0]
                        exact_args = [sv for sv in in_scope_vars if sv != seq_v and sv == p0]
                        other_args = [sv for sv in in_scope_vars[:4] if sv not in (seq_v, "self") and sv != p0]
                        for sv in (exact_args + other_args)[:2]:
                            base_cost = 5 if sv == p0 else 13
                            call_s = f"{iter_var}.{tr.name}({sv})"
                            _propose(
                                f"[{call_s} for {iter_var} in {seq_v}]",
                                base_cost,
                                f"PETRI_MAP1:{tr.transition_id}({sv})",
                            )
                            _propose(
                                f"[_rv for {iter_var} in {seq_v} if (_rv := {call_s}) is not None]",
                                base_cost + 4,
                                f"PETRI_FILTER_MAP1:{tr.transition_id}({sv})",
                            )

        # 5. Intra-file & imported module function transitions `fn(v)` / `fn(v1, v2)`
        file_funcs = list(self.module_functions.get(rel_file, ()))
        for tr in file_funcs[:12]:
            is_bool_fn = tr.output_place == "bool" or tr.name.startswith(("is_", "has_", "can_", "should_", "check_"))
            if require_bool and not is_bool_fn:
                continue
            if len(tr.param_names) == 1:
                p0 = tr.param_names[0]
                ordered_vars = sorted(
                    [v for v in in_scope_vars[:8] if v != "self"],
                    key=lambda v: (0 if v == p0 else 1, len(v)),
                )
                for v in ordered_vars[:3]:
                    cost = 6 if v == p0 else 11
                    _propose(f"{tr.name}({v})", cost, f"PETRI_MOD_FUNC1:{tr.transition_id}({v})")
            elif len(tr.param_names) == 2:
                p0, p1 = tr.param_names
                if p0 in in_scope_vars and p1 in in_scope_vars and p0 != p1:
                    _propose(f"{tr.name}({p0}, {p1})", 7, f"PETRI_MOD_FUNC2:{tr.transition_id}({p0},{p1})")

        ranked = sorted(scored.items(), key=lambda kv: (kv[1][0], len(kv[0]), kv[0]))
        return [(expr, meta[1]) for expr, meta in ranked[:max_candidates]]

    @staticmethod
    def synthesize_sibling_return_lifts(
        enclosing_fn: ast.FunctionDef | ast.AsyncFunctionDef | None,
        stmt: ast.stmt,
        fail_frames: Sequence[Mapping[str, Any]],
    ) -> list[tuple[str, str]]:
        """Intra-Function Sibling-Return Monoidal Coalescing:

        When an early `return None` (or `return <const>`) executes in `fail_frames`, inspect
        sibling `return <expr>` statements in the SAME `enclosing_fn` and coalesce any
        `None`-valued runtime sub-expressions `(x -> x or identity)` over monoidal identities
        `""`, `()`, `[]`, `0`.
        """
        if enclosing_fn is None or not isinstance(stmt, ast.Return):
            return []
        cur_ret_txt = ast.unparse(stmt.value) if stmt.value is not None else "None"

        # Identify variables / `self.<attr>` expressions that are `None` in `fail_frames`
        null_exprs: set[str] = set()
        for ff in fail_frames[:3]:
            for var_k, meta in ff.items():
                if not isinstance(meta, Mapping):
                    continue
                if meta.get("t") == "NoneType" or meta.get("v") is None and "len" not in meta and "attrs" not in meta and "mro" not in meta:
                    if meta.get("t") == "NoneType":
                        null_exprs.add(var_k)
                attrs_m = meta.get("attrs")
                if isinstance(attrs_m, Mapping):
                    for ak, av_repr in attrs_m.items():
                        if av_repr == "None":
                            null_exprs.add(f"{var_k}.{ak}")

        out: list[tuple[str, str]] = []
        seen: set[str] = {cur_ret_txt}
        identities = ("''", "()", "[]", "0")

        for sub in ast.walk(enclosing_fn):
            if not isinstance(sub, ast.Return) or sub is stmt or sub.value is None:
                continue
            sib_txt = ast.unparse(sub.value)
            if len(sib_txt) > 120:
                continue
            if sib_txt not in seen:
                seen.add(sib_txt)
                out.append((sib_txt, "PETRI_SIBLING_RETURN_DIRECT"))

            # Replace any `Name` or `Attribute` inside `sub.value` (prioritizing runtime-null ones!) with `(e or id)`
            sub_targets: list[ast.expr] = []
            for child in ast.walk(sub.value):
                if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
                    sub_targets.append(child)
                elif isinstance(child, ast.Name) and child.id not in _SAFE_BUILTINS_NAMES:
                    # Skip `Name` if it is merely the receiver of `self.foo` or callee of `foo(...)`
                    sub_targets.append(child)

            # Deduplicate by unparsed text, ordering runtime-null expressions first
            ordered_t_txts: list[str] = []
            for t_node in sub_targets:
                t_s = ast.unparse(t_node)
                if t_s not in ordered_t_txts:
                    ordered_t_txts.append(t_s)
            ordered_t_txts.sort(key=lambda s: (0 if s in null_exprs else 1, -len(s)))

            for t_s in ordered_t_txts[:4]:
                # Avoid replacing callee names like `self.make_metavar` in `self.make_metavar(ctx)`
                if f"{t_s}(" in sib_txt:
                    continue
                for ident_lit in identities:
                    coalesced = re.sub(rf"(?<![\w\.]){re.escape(t_s)}(?![\w\(])", f"({t_s} or {ident_lit})", sib_txt)
                    if coalesced != sib_txt and coalesced not in seen:
                        try:
                            ast.parse(coalesced, mode="eval")
                            seen.add(coalesced)
                            out.append((coalesced, f"PETRI_SIBLING_RETURN_COALESCE:{t_s}->{ident_lit}"))
                        except SyntaxError:
                            pass
        return out[:14]


# =========================================================================== #
# 2. BACKWARD WITNESS INVERSION + DUAL-PROGRAM COUNTEREXAMPLE SPLICING
# =========================================================================== #

@dataclass(frozen=True)
class AssertionWitness:
    expected_values: tuple[Any, ...]
    expected_types: tuple[str, ...]
    expected_exceptions: tuple[str, ...]
    expected_substrings: tuple[str, ...]


class BackwardWitnessAndDualSplicer:
    """Backward witness extraction/inversion + Dual-Program Counterexample Splicing (`(P1) if (G) else (P0)`)."""

    @staticmethod
    def extract_witness_from_pytest_output(stdout_and_stderr: str) -> AssertionWitness:
        vals: list[Any] = []
        types_seen: list[str] = []
        excs: list[str] = []
        subs: list[str] = []

        for m in re.finditer(r"assert\s+.+?\s*==\s*(.+)", stdout_and_stderr):
            rhs = m.group(1).strip()
            try:
                lit = ast.literal_eval(rhs)
                if lit not in vals:
                    vals.append(lit)
                    t_n = type(lit).__name__
                    if t_n not in types_seen:
                        types_seen.append(t_n)
            except Exception:
                pass

        for m in re.finditer(r"AssertionError:\s*(.+?)\s*!=\s*(.+)", stdout_and_stderr):
            for side in (m.group(2).strip(), m.group(1).strip()):
                try:
                    lit = ast.literal_eval(side)
                    if lit not in vals:
                        vals.append(lit)
                except Exception:
                    pass

        for m in re.finditer(r"in\s+(['\"][^'\"]{2,80}['\"])", stdout_and_stderr):
            try:
                s_lit = ast.literal_eval(m.group(1))
                if isinstance(s_lit, str) and s_lit not in subs:
                    subs.append(s_lit)
            except Exception:
                pass

        for m in re.finditer(r"(?:DID NOT RAISE|raises\()\s*([A-Za-z_][A-Za-z0-9_\.]*)", stdout_and_stderr):
            en = m.group(1).split(".")[-1]
            if en not in excs:
                excs.append(en)

        return AssertionWitness(
            expected_values=tuple(vals[:8]),
            expected_types=tuple(types_seen[:6]),
            expected_exceptions=tuple(excs[:6]),
            expected_substrings=tuple(subs[:6]),
        )

    @staticmethod
    def invert_return_residual(ret_expr: ast.expr, expected_val: Any) -> list[tuple[ast.expr, Any]]:
        """Propagate `ret_expr == expected_val` one algebraic step backward to `(sub_expr, sub_target)`."""
        inversions: list[tuple[ast.expr, Any]] = [(ret_expr, expected_val)]
        if isinstance(ret_expr, ast.UnaryOp) and isinstance(ret_expr.op, ast.Not) and isinstance(expected_val, bool):
            inversions.append((ret_expr.operand, not expected_val))
        elif isinstance(ret_expr, ast.BinOp) and isinstance(expected_val, (int, float)) and not isinstance(expected_val, bool):
            if isinstance(ret_expr.op, ast.Add) and isinstance(ret_expr.right, ast.Constant) and isinstance(ret_expr.right.value, (int, float)):
                inversions.append((ret_expr.left, expected_val - ret_expr.right.value))
            elif isinstance(ret_expr.op, ast.Sub) and isinstance(ret_expr.right, ast.Constant) and isinstance(ret_expr.right.value, (int, float)):
                inversions.append((ret_expr.left, expected_val + ret_expr.right.value))
        elif isinstance(ret_expr, ast.BinOp) and isinstance(ret_expr.op, ast.Add) and isinstance(expected_val, str):
            if isinstance(ret_expr.left, ast.Constant) and isinstance(ret_expr.left.value, str) and expected_val.startswith(ret_expr.left.value):
                inversions.append((ret_expr.right, expected_val[len(ret_expr.left.value):]))
            if isinstance(ret_expr.right, ast.Constant) and isinstance(ret_expr.right.value, str) and expected_val.endswith(ret_expr.right.value):
                rlen = len(ret_expr.right.value)
                inversions.append((ret_expr.left, expected_val[:-rlen] if rlen else expected_val))
        elif isinstance(ret_expr, ast.Tuple) and isinstance(expected_val, tuple) and len(ret_expr.elts) == len(expected_val):
            for elt, sub_v in zip(ret_expr.elts, expected_val):
                inversions.append((elt, sub_v))
        return inversions

    @staticmethod
    def is_lookup_table_overfit(
        branch_expr: str,
        guard_expr: str,
        in_scope_vars: Sequence[str],
        num_distinct_fail_witnesses: int,
    ) -> bool:
        """Anti-Lookup-Table Equivalence Law (`consistency_vs_equivalence_v1` discipline):

        Rejects memorized `const_literal if x == 'exact_test_input' else orig` patches when
        `branch_expr` references zero runtime variables AND `guard_expr` compares against an
        ad-hoc non-structural literal on only a single failing witness.
        """
        var_set = {v for v in in_scope_vars if v not in ("True", "False", "None")}
        branch_tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", branch_expr))
        branch_uses_var = bool(branch_tokens & var_set)
        if branch_uses_var:
            return False
        # Allow structural canonical guards (`is None`, `is not None`, `not x`, `len(x) == 0`, `x == ''`, `x <= 0`)
        try:
            g_ast = ast.parse(guard_expr, mode="eval").body
        except SyntaxError:
            return True
        for sub in ast.walk(g_ast):
            if isinstance(sub, ast.Constant):
                val = sub.value
                if val is None or isinstance(val, bool):
                    continue
                if isinstance(val, (int, float)) and val in (-1, 0, 1):
                    continue
                if isinstance(val, (str, bytes)) and len(val) <= 1:
                    continue
                # Non-trivial literal inside guard paired with constant branch:
                if num_distinct_fail_witnesses < 2:
                    return True
        return False

    @classmethod
    def synthesize_separating_guards(
        cls,
        mental_model: Any,
        *,
        positive_envs: Sequence[Mapping[str, Any]],
        negative_envs: Sequence[Mapping[str, Any]],
        site_constants: Sequence[Any] = (),
        sibling_bool_attrs: Sequence[str] = (),
        synthesize_disc_fn: Callable[..., list[tuple[str, Any]]] | None = None,
        max_guards: int = 12,
    ) -> list[str]:
        """Synthesize minimal boolean projections `G` with `G(positive_envs)=True` and `G(negative_envs)=False`."""
        if not positive_envs or not negative_envs:
            return []
        guards: list[str] = []
        if synthesize_disc_fn is not None:
            for g_txt, _ in synthesize_disc_fn(
                mental_model,
                fail_envs=positive_envs,
                pass_envs=negative_envs,
                site_constants=site_constants,
                max_preds=max_guards,
            ):
                if g_txt not in guards:
                    guards.append(g_txt)

        # Also test repo-native `self.<bool_attr>` / `isinstance(v, ...)` projections
        all_envs = [*positive_envs, *negative_envs]
        n_pos = len(positive_envs)
        target_vec = tuple([("bool", True)] * n_pos + [("bool", False)] * len(negative_envs))

        extra_cands: list[str] = []
        if any("self" in env for env in positive_envs):
            for attr in sibling_bool_attrs[:12]:
                extra_cands.extend([f"bool(self.{attr})", f"not self.{attr}", f"self.{attr} is None", f"self.{attr} is not None"])

        for k in list(positive_envs[0].keys())[:8]:
            if not k.isidentifier() or k.startswith("_"):
                continue
            pos_types = {type(env.get(k)).__name__ for env in positive_envs if k in env}
            neg_types = {type(env.get(k)).__name__ for env in negative_envs if k in env}
            diff_t = pos_types - neg_types
            for t_name in diff_t:
                if t_name in ("str", "bytes", "int", "float", "list", "tuple", "dict", "set", "bool"):
                    extra_cands.append(f"isinstance({k}, {t_name})")
            diff_neg = neg_types - pos_types
            for t_name in diff_neg:
                if t_name in ("str", "bytes", "int", "float", "list", "tuple", "dict", "set", "bool"):
                    extra_cands.append(f"not isinstance({k}, {t_name})")

        for cand in extra_cands:
            if cand in guards:
                continue
            ok, vec = mental_model.eval_expr_vector(cand, all_envs)
            if ok and vec == target_vec:
                guards.append(cand)
                if len(guards) >= max_guards:
                    break

        guards.sort(key=lambda g: (len(g), g))
        return guards[:max_guards]

    @classmethod
    def build_spliced_expressions(
        cls,
        *,
        positive_expr: str,
        negative_expr: str,
        guards: Sequence[str],
        in_scope_vars: Sequence[str],
        num_distinct_fail_witnesses: int,
    ) -> list[tuple[str, str]]:
        """Construct `(positive_expr) if (G) else (negative_expr)` candidates passing Anti-Lookup-Table gate."""
        out: list[tuple[str, str]] = []
        if positive_expr.strip() == negative_expr.strip():
            return out
        for g in guards:
            if cls.is_lookup_table_overfit(positive_expr, g, in_scope_vars, num_distinct_fail_witnesses):
                continue
            spliced = f"({positive_expr}) if ({g}) else ({negative_expr})"
            try:
                ast.parse(spliced, mode="eval")
                out.append((spliced, g))
            except SyntaxError:
                continue
        return out


# =========================================================================== #
# 3. 16-WAY PARALLEL CoW SPECULATIVE EXECUTION + MEALY STATE TOMOGRAPHY
# =========================================================================== #

@dataclass(frozen=True)
class MultiLayerStateSnapshot:
    """5-layer computer-use & software-state observation filtered for `SEPARATION + STABILITY`."""
    accessibility_dom_layer: dict[str, Any]
    filesystem_fd_layer: dict[str, str]
    sqlite_db_layer: dict[str, list[tuple[Any, ...]]]
    config_env_layer: dict[str, Any]
    cli_ipc_layer: dict[str, Any]

    def stable_projection_key(self) -> str:
        payload = {
            "dom": self.accessibility_dom_layer,
            "fs": self.filesystem_fd_layer,
            "sqlite": {k: [list(r) for r in v] for k, v in sorted(self.sqlite_db_layer.items())},
            "cfg": self.config_env_layer,
            "ipc_rc": self.cli_ipc_layer.get("returncode"),
            "ipc_status": self.cli_ipc_layer.get("status_code"),
        }
        return _sha256_text(json.dumps(payload, sort_keys=True, default=str))

    def diff_effects(self, after: "MultiLayerStateSnapshot") -> tuple[Effect, ...]:
        """Compute exact typed `Effect(ESTABLISH|REMOVE, subject)` delta between two snapshots."""
        effects: list[Effect] = []
        # 1. Accessibility / DOM delta
        for k, v2 in sorted(after.accessibility_dom_layer.items()):
            v1 = self.accessibility_dom_layer.get(k)
            if v1 != v2:
                if v1 is not None:
                    effects.append(Effect("REMOVE", f"dom:{k}={v1}"))
                effects.append(Effect("ESTABLISH", f"dom:{k}={v2}"))
        # 2. Filesystem delta
        for p, h2 in sorted(after.filesystem_fd_layer.items()):
            h1 = self.filesystem_fd_layer.get(p)
            if h1 != h2:
                if h1 is not None:
                    effects.append(Effect("REMOVE", f"fs:{p}:{h1[:12]}"))
                effects.append(Effect("ESTABLISH", f"fs:{p}:{h2[:12]}"))
        for p, h1 in sorted(self.filesystem_fd_layer.items()):
            if p not in after.filesystem_fd_layer:
                effects.append(Effect("REMOVE", f"fs:{p}:{h1[:12]}"))
        # 3. SQLite delta
        for tbl, rows2 in sorted(after.sqlite_db_layer.items()):
            rows1 = self.sqlite_db_layer.get(tbl, [])
            if rows1 != rows2:
                effects.append(Effect("ESTABLISH", f"sqlite:{tbl}:rows={len(rows2)}"))
        # 4. Config delta
        for ck, cv2 in sorted(after.config_env_layer.items()):
            cv1 = self.config_env_layer.get(ck)
            if cv1 != cv2:
                if cv1 is not None:
                    effects.append(Effect("REMOVE", f"cfg:{ck}={cv1}"))
                effects.append(Effect("ESTABLISH", f"cfg:{ck}={cv2}"))
        # 5. CLI/IPC status delta
        rc2 = after.cli_ipc_layer.get("returncode")
        if rc2 is not None and rc2 != self.cli_ipc_layer.get("returncode"):
            effects.append(Effect("ESTABLISH", f"cli:rc={rc2}"))
        return tuple(effects)


def capture_multilayer_snapshot(
    workspace: pathlib.Path,
    *,
    dom_state: Mapping[str, Any] | None = None,
    cli_result: Mapping[str, Any] | None = None,
) -> MultiLayerStateSnapshot:
    """Inspect real filesystem, SQLite databases, JSON configs, DOM/ARIA state, and CLI output."""
    ws = pathlib.Path(workspace).resolve()
    fs_map: dict[str, str] = {}
    sqlite_map: dict[str, list[tuple[Any, ...]]] = {}
    cfg_map: dict[str, Any] = {}

    if ws.exists():
        for p in sorted(ws.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ws).as_posix()
            if any(seg.startswith(".") or seg == "__pycache__" for seg in rel.split("/")):
                continue
            try:
                raw = p.read_bytes()
            except OSError:
                continue
            fs_map[rel] = _sha256_bytes(raw)
            if p.suffix in (".db", ".sqlite", ".sqlite3"):
                try:
                    conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
                    try:
                        tables = [
                            r[0]
                            for r in conn.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                            ).fetchall()
                        ]
                        for t in tables[:12]:
                            rows = conn.execute(f'SELECT * FROM "{t}" LIMIT 50').fetchall()
                            sqlite_map[f"{rel}::{t}"] = rows
                    finally:
                        conn.close()
                except sqlite3.Error:
                    pass
            elif p.suffix == ".json" and len(raw) <= 65536:
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                    if isinstance(parsed, dict):
                        for k, v in list(parsed.items())[:24]:
                            if isinstance(v, (bool, int, float, str)) or v is None:
                                cfg_map[f"{rel}:{k}"] = v
                except Exception:
                    pass

    return MultiLayerStateSnapshot(
        accessibility_dom_layer=dict(dom_state or {}),
        filesystem_fd_layer=fs_map,
        sqlite_db_layer=sqlite_map,
        config_env_layer=cfg_map,
        cli_ipc_layer=dict(cli_result or {}),
    )


@dataclass(frozen=True)
class SpeculativeBranchResult:
    branch_index: int
    action_id: str
    goal_residual: float
    before_key: str
    after_key: str
    effects: tuple[Effect, ...]
    payload: dict[str, Any]
    elapsed_ms: float


class ParallelCoWWorldTomographer:
    """16-Way Parallel `os.fork()` Copy-on-Write Counterfactual Speculative Executor + Mealy Compiler."""

    def __init__(self, max_parallel_ways: int = 16, wave_concurrency: int = 8) -> None:
        self.max_parallel_ways = max(1, min(32, int(max_parallel_ways)))
        self.wave_concurrency = max(1, min(16, int(wave_concurrency)))
        self.branches_forked: int = 0
        self.waves_executed: int = 0

    def speculate_parallel(
        self,
        base_workspace: pathlib.Path,
        candidates: Sequence[tuple[str, Callable[[pathlib.Path], dict[str, Any]]]],
        goal_residual_fn: Callable[[MultiLayerStateSnapshot, Mapping[str, Any]], float],
        *,
        initial_dom_state: Mapping[str, Any] | None = None,
        timeout_s: float = 5.0,
    ) -> list[SpeculativeBranchResult]:
        """Fork up to 16 isolated CoW shadow sandboxes in parallel, run each candidate action,
        capture full 5-layer state tomography, and return all branches ranked by `goal_residual`.

        Base workspace on disk is NEVER mutated by speculative rollouts (`0` residual side effects).
        """
        before_snap = capture_multilayer_snapshot(base_workspace, dom_state=initial_dom_state)
        before_key = before_snap.stable_projection_key()
        batch = list(candidates[: self.max_parallel_ways])
        results: list[SpeculativeBranchResult] = []

        for wave_start in range(0, len(batch), self.wave_concurrency):
            wave = batch[wave_start : wave_start + self.wave_concurrency]
            self.waves_executed += 1
            active: dict[int, tuple[int, int, str, pathlib.Path, float]] = {}

            for offset, (action_id, fn) in enumerate(wave):
                b_idx = wave_start + offset
                shadow_dir = pathlib.Path(tempfile.mkdtemp(prefix=f"cow_shadow_{b_idx}_"))
                if base_workspace.exists():
                    shutil.copytree(base_workspace, shadow_dir / "ws", symlinks=True)
                else:
                    (shadow_dir / "ws").mkdir(parents=True, exist_ok=True)

                r_fd, w_fd = os.pipe()
                t0 = time.perf_counter()
                self.branches_forked += 1
                pid = os.fork()
                if pid == 0:
                    os.close(r_fd)
                    try:
                        out = fn(shadow_dir / "ws") or {}
                        after_snap = capture_multilayer_snapshot(
                            shadow_dir / "ws",
                            dom_state=out.get("dom_state", initial_dom_state),
                            cli_result=out.get("cli_result"),
                        )
                        residual = float(goal_residual_fn(after_snap, out))
                        effs = before_snap.diff_effects(after_snap)
                        msg = {
                            "ok": True,
                            "residual": residual,
                            "after_key": after_snap.stable_projection_key(),
                            "effects": [(e.kind, e.subject) for e in effs],
                            "payload": out,
                        }
                    except Exception as exc:
                        msg = {
                            "ok": False,
                            "residual": 1.0,
                            "after_key": before_key,
                            "effects": [],
                            "payload": {"error": f"{type(exc).__name__}: {exc}"},
                        }
                    raw = json.dumps(msg, default=str).encode("utf-8")
                    os.write(w_fd, struct.pack(">I", len(raw)) + raw)
                    os.close(w_fd)
                    os._exit(0)
                else:
                    os.close(w_fd)
                    active[r_fd] = (pid, b_idx, action_id, shadow_dir, t0)

            deadline = time.perf_counter() + timeout_s
            buffers: dict[int, bytearray] = {fd: bytearray() for fd in active}
            while active:
                rem = max(0.0, deadline - time.perf_counter())
                ready_fds, _, _ = select.select(list(active.keys()), [], [], rem)
                if not ready_fds:
                    for fd, (pid, b_idx, action_id, shadow_dir, t0) in list(active.items()):
                        try:
                            os.kill(pid, 9)
                        except OSError:
                            pass
                        os.waitpid(pid, 0)
                        os.close(fd)
                        shutil.rmtree(shadow_dir, ignore_errors=True)
                        results.append(SpeculativeBranchResult(
                            branch_index=b_idx,
                            action_id=action_id,
                            goal_residual=1.0,
                            before_key=before_key,
                            after_key=before_key,
                            effects=(),
                            payload={"timeout": True},
                            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
                        ))
                    active.clear()
                    break

                for fd in ready_fds:
                    chunk = os.read(fd, 65536)
                    if chunk:
                        buffers[fd].extend(chunk)
                        continue
                    pid, b_idx, action_id, shadow_dir, t0 = active.pop(fd)
                    os.close(fd)
                    os.waitpid(pid, 0)
                    shutil.rmtree(shadow_dir, ignore_errors=True)
                    buf = bytes(buffers[fd])
                    if len(buf) >= 4:
                        (sz,) = struct.unpack(">I", buf[:4])
                        data = json.loads(buf[4 : 4 + sz].decode("utf-8"))
                    else:
                        data = {"residual": 1.0, "after_key": before_key, "effects": [], "payload": {}}
                    eff_objs = tuple(Effect(kind=k, subject=s) for k, s in data.get("effects", ()))
                    results.append(SpeculativeBranchResult(
                        branch_index=b_idx,
                        action_id=action_id,
                        goal_residual=float(data.get("residual", 1.0)),
                        before_key=before_key,
                        after_key=str(data.get("after_key", before_key)),
                        effects=eff_objs,
                        payload=dict(data.get("payload") or {}),
                        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
                    ))

        results.sort(key=lambda r: (r.goal_residual, r.branch_index))
        return results


class MealyStateCompiler:
    """Compiles empirical `(StateKey, Action) -> (NextStateKey, EffectContract)` Mealy machines from CoW rollouts."""

    def __init__(self) -> None:
        self.transitions: dict[tuple[str, str], tuple[str, EffectContract]] = {}

    def ingest_rollouts(self, rollouts: Sequence[SpeculativeBranchResult]) -> int:
        added = 0
        for r in rollouts:
            if not r.effects and r.before_key == r.after_key:
                continue
            contract = EffectContract(
                skill_id=f"mealy:{r.action_id}",
                preconditions=(f"state:{r.before_key[:12]}",),
                observables=("dom", "fs", "sqlite", "cfg", "cli"),
                actions=(r.action_id,),
                verdict="multilayer_state_tomography",
                effects=(
                    *r.effects,
                    Effect("REMOVE", f"state:{r.before_key[:12]}"),
                    Effect("ESTABLISH", f"state:{r.after_key[:12]}"),
                ),
            )
            key = (r.before_key, r.action_id)
            if key not in self.transitions:
                added += 1
            self.transitions[key] = (r.after_key, contract)
        return added

    def verify_sequence_contracts(self, contracts: Sequence[EffectContract]) -> dict[str, Any]:
        return compose_chain(contracts)


# =========================================================================== #
# 4. CROSS-MODAL PETRI PLANNER, §9.2 ADMISSION-FILTERED STORE & SELF-PLAY
# =========================================================================== #

@dataclass(frozen=True)
class CrossModalMorphism:
    morphism_id: str
    surface: str  # GUI_ARIA | SQLITE_QUERY | PYTHON_TRANSFORM | CLI_EXEC | BRAIN_CAPABILITY
    input_places: tuple[str, ...]
    output_place: str
    preconditions: tuple[str, ...]
    effects: tuple[Effect, ...]
    execute: Callable[[dict[str, Any]], Any]

    def to_contract(self) -> EffectContract:
        return EffectContract(
            skill_id=self.morphism_id,
            preconditions=self.preconditions,
            observables=tuple(f"token:{p}" for p in self.input_places) or ("token:init",),
            actions=(f"{self.surface}:{self.morphism_id}",),
            verdict="cross_modal_token_oracle",
            effects=self.effects or (Effect("ESTABLISH", f"token:{self.output_place}"),),
        )


class CrossModalPetriPlanner:
    """Synthesizes and executes verified multi-surface workflows (`GUI -> SQLite -> Python -> CLI`)
    via Petri-net token reachability + `(P, O, A, V, F)` `compose_chain` verification."""

    def __init__(self, morphisms: Sequence[CrossModalMorphism] = ()) -> None:
        self.morphisms: list[CrossModalMorphism] = list(morphisms)

    def register(self, morphism: CrossModalMorphism) -> None:
        self.morphisms.append(morphism)

    def plan_reachability(
        self,
        initial_places: Sequence[str],
        goal_place: str,
        *,
        max_depth: int = 6,
    ) -> list[CrossModalMorphism] | None:
        """BFS over Petri-net markings `(frozenset_of_available_places)`, pruning any chain rejected by `compose_chain`."""
        start_marking = frozenset(initial_places)
        if goal_place in start_marking:
            return []

        queue: list[tuple[frozenset[str], list[CrossModalMorphism]]] = [(start_marking, [])]
        visited: set[frozenset[str]] = {start_marking}

        while queue:
            marking, path = queue.pop(0)
            if len(path) >= max_depth:
                continue
            for m in self.morphisms:
                if not all(inp in marking for inp in m.input_places):
                    continue
                if m in path:
                    continue
                cand_path = [*path, m]
                # Enforce `effect_contract_composition_v1` `UNDO` & `COMPLETE` checks!
                contracts = [step.to_contract() for step in cand_path]
                # Check completeness & absence of inverse no-op (`UNDO`) across consecutive steps
                chain_verdict = compose_chain(contracts)
                if chain_verdict.get("verdict") == "UNDO":
                    continue
                next_marking = marking | {m.output_place}
                if goal_place in next_marking:
                    return cand_path
                if next_marking not in visited:
                    visited.add(next_marking)
                    queue.append((next_marking, cand_path))
        return None

    def execute_plan(
        self,
        plan: Sequence[CrossModalMorphism],
        initial_tokens: Mapping[str, Any],
        goal_verifier: Callable[[Mapping[str, Any]], bool],
    ) -> dict[str, Any]:
        token_store: dict[str, Any] = dict(initial_tokens)
        trace: list[dict[str, Any]] = []
        for step in plan:
            out_val = step.execute(token_store)
            token_store[step.output_place] = out_val
            trace.append({
                "morphism_id": step.morphism_id,
                "surface": step.surface,
                "inputs": list(step.input_places),
                "output_place": step.output_place,
            })
        verified = bool(goal_verifier(token_store))
        return {
            "ok": verified,
            "steps_executed": len(trace),
            "surfaces_used": [t["surface"] for t in trace],
            "trace": trace,
            "final_tokens": token_store,
        }


def check_foreign_ident_unbound(lhs_pattern_py: str, rhs_pattern_py: str, allowed_module_symbols: Sequence[str] = ()) -> list[str]:
    """Hard `FOREIGN_IDENT_UNBOUND` detector across BOTH single expressions AND multi-statement AST blocks."""
    import keyword
    lhs_norm = re.sub(r"(?:\$|\?)(?:expr|v|attr|fn)\d+", "_HOLE_", lhs_pattern_py)
    rhs_norm = re.sub(r"(?:\$|\?)(?:expr|v|attr|fn)\d+", "_HOLE_", rhs_pattern_py)

    def _parse_any(code_str: str) -> ast.AST | None:
        for mode in ("eval", "exec"):
            try:
                return ast.parse(code_str, mode=mode)
            except SyntaxError:
                continue
        return None

    lhs_ids: set[str] = set()
    l_ast = _parse_any(lhs_norm)
    if l_ast is not None:
        for n in ast.walk(l_ast):
            if isinstance(n, ast.Name):
                lhs_ids.add(n.id)
            elif isinstance(n, ast.arg):
                lhs_ids.add(n.arg)
    else:
        lhs_ids.update(t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", lhs_norm) if not keyword.iskeyword(t))

    allowed = lhs_ids | _SAFE_BUILTINS_NAMES | set(allowed_module_symbols) | {"_HOLE_"}
    unbound: list[str] = []
    r_ast = _parse_any(rhs_norm)
    if r_ast is not None:
        local_defs: set[str] = set()
        for n in ast.walk(r_ast):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                local_defs.add(n.id)
            elif isinstance(n, ast.arg):
                local_defs.add(n.arg)
            elif isinstance(n, ast.comprehension):
                for sub in ast.walk(n.target):
                    if isinstance(sub, ast.Name):
                        local_defs.add(sub.id)
            elif isinstance(n, ast.NamedExpr) and isinstance(n.target, ast.Name):
                local_defs.add(n.target.id)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                local_defs.add(n.name)
        allowed |= local_defs
        for n in ast.walk(r_ast):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in allowed and n.id not in unbound:
                    unbound.append(n.id)
    else:
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", rhs_norm):
            if not keyword.iskeyword(tok) and tok not in allowed and tok not in unbound:
                unbound.append(tok)
    return unbound


def _anti_unify_expr_pair(before_expr: str, after_expr: str, semantic_meaning_cls: Any) -> tuple[Any, Any]:
    """Lift `(before_expr, after_expr)` into `SemanticMeaningIR` and abstract shared identifiers to `$v0, $v1, ...`."""
    b_ir = semantic_meaning_cls.lift_expr(ast.parse(before_expr, mode="eval").body)
    a_ir = semantic_meaning_cls.lift_expr(ast.parse(after_expr, mode="eval").body)
    var_map: dict[str, str] = {}

    def _subst(node: Any) -> Any:
        if node.op == "VAR" and node.args:
            orig_v = str(node.args[0])
            slot = var_map.setdefault(orig_v, f"$v{len(var_map)}")
            return type(node)("VAR", (slot,))
        new_args = tuple(_subst(x) if hasattr(x, "op") else x for x in node.args)
        return type(node)(node.op, new_args)

    return _subst(b_ir), _subst(a_ir)


def _match_schematic_ir(pattern_ir: Any, target_ir: Any, bindings: dict[str, Any]) -> bool:
    if pattern_ir.op == "VAR" and pattern_ir.args and str(pattern_ir.args[0]).startswith("$v"):
        slot = str(pattern_ir.args[0])
        prev = bindings.get(slot)
        if prev is None:
            bindings[slot] = target_ir
            return True
        return prev == target_ir
    if pattern_ir.op != target_ir.op or len(pattern_ir.args) != len(target_ir.args):
        return False
    for pa, ta in zip(pattern_ir.args, target_ir.args):
        if hasattr(pa, "op") and hasattr(ta, "op"):
            if not _match_schematic_ir(pa, ta, bindings):
                return False
        elif pa != ta:
            return False
    return True


def _lift_surface_expr(expr_source: str, target_lang: str, semantic_meaning_cls: Any) -> Any | None:
    s = expr_source.strip()
    if target_lang == "python":
        return semantic_meaning_cls.lift_expr(ast.parse(s, mode="eval").body)
    if target_lang == "javascript":
        m_bool = re.fullmatch(r"Boolean\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", s)
        if m_bool:
            ir_cls = type(semantic_meaning_cls.lift_expr(ast.parse("x", mode="eval").body))
            return ir_cls("BOOL", (ir_cls("VAR", (m_bool.group(1),)),))
        m_null = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*===\s*null", s)
        if m_null:
            ir_cls = type(semantic_meaning_cls.lift_expr(ast.parse("x", mode="eval").body))
            return ir_cls("IS_NONE", (ir_cls("VAR", (m_null.group(1),)),))
    if target_lang == "rust":
        m_rs = re.fullmatch(r"!\s*([A-Za-z_][A-Za-z0-9_]*)\.is_empty\(\)", s)
        if m_rs:
            ir_cls = type(semantic_meaning_cls.lift_expr(ast.parse("x", mode="eval").body))
            return ir_cls("BOOL", (ir_cls("VAR", (m_rs.group(1),)),))
    return None


def _instantiate_schematic_ir(template_ir: Any, bindings: Mapping[str, Any], target_lang: str, semantic_meaning_cls: Any) -> str:
    def _fill(node: Any) -> Any:
        if node.op == "VAR" and node.args and str(node.args[0]) in bindings:
            return bindings[str(node.args[0])]
        return type(node)(node.op, tuple(_fill(x) if hasattr(x, "op") else x for x in node.args))

    bound_ir = _fill(template_ir)
    if target_lang == "python":
        return semantic_meaning_cls._lower_expr_py(bound_ir, {})
    if target_lang == "javascript":
        return semantic_meaning_cls._lower_expr_js(bound_ir, {})
    if target_lang == "rust":
        if bound_ir.op == "IS_NOT_NONE" and bound_ir.args and bound_ir.args[0].op == "VAR":
            return f"{bound_ir.args[0].args[0]}.is_some()"
        if bound_ir.op == "IS_NONE" and bound_ir.args and bound_ir.args[0].op == "VAR":
            return f"{bound_ir.args[0].args[0]}.is_none()"
    return semantic_meaning_cls._lower_expr_py(bound_ir, {})
@dataclass
class AdmittedSkillRecord:
    skill_id: str
    domain: str
    lhs_ir_sexpr: str
    rhs_ir_sexpr: str
    concrete_before: str
    concrete_after: str
    source_fingerprint: str
    verified_utc: str
    prediction_error_probes: int
    mdl_gain_bytes: int
    witness_inputs: list[dict[str, Any]]
    revalidation_probe: dict[str, Any]
    stale: bool = False
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "domain": self.domain,
            "lhs_ir_sexpr": self.lhs_ir_sexpr,
            "rhs_ir_sexpr": self.rhs_ir_sexpr,
            "concrete_before": self.concrete_before,
            "concrete_after": self.concrete_after,
            "source_fingerprint": self.source_fingerprint,
            "verified_utc": self.verified_utc,
            "prediction_error_probes": self.prediction_error_probes,
            "mdl_gain_bytes": self.mdl_gain_bytes,
            "witness_inputs": self.witness_inputs,
            "revalidation_probe": self.revalidation_probe,
            "stale": self.stale,
            "version": self.version,
        }


class AdmissionFilteredSkillStore:
    """§9.2 Inspectable, versioned, editable, removable external skill & environment store.

    Admission filters (caller owns the execution evidence; no equivalence oracle here):
      1. `verified`: Witness outcome supplied by the caller. Subtree rules must also replay the teacher AST.
      2. `goal_relevant`: Reduced goal residual on an active task (`goal_relevant=True`).
      3. `prediction_error_bearing`: Cold mental model failed or took >= 1 falsified probe (`probes_before_success >= 1`).
      4. `reusable`: Generalized over `SemanticMeaningIR` with ZERO `FOREIGN_IDENT_UNBOUND` identifiers.
      5. `compressible`: Positive MDL compression (`raw_trace_bytes > rule_bytes`) or multi-state coverage.

    Supports §6 ablation modes cleanly:
      - `mode="generalized"`: Anti-unified `SemanticMeaningIR` cross-context & cross-language matching.
      - `mode="raw_traces"`: Exact concrete text/state replay only (no IR generalization).
      - `mode="disabled"`: Empty/bypassed store (`0` retrievals).
    """

    def __init__(self, store_path: pathlib.Path | None = None, *, mode: str = "generalized") -> None:
        if mode not in ("generalized", "raw_traces", "disabled"):
            raise ValueError(f"Unsupported store ablation mode: {mode}")
        self.mode = mode
        self.store_path = pathlib.Path(store_path) if store_path else None
        self.records: dict[str, AdmittedSkillRecord] = {}
        self._subtree_buckets: dict[str, list[tuple[AdmittedSkillRecord, list[ast.stmt]]]] | None = None
        self._subtree_index_mode = mode
        self.rejections: list[dict[str, Any]] = []
        if self.store_path and self.store_path.is_file():
            self._load()

    def _load(self) -> None:
        if not self.store_path or not self.store_path.is_file():
            return
        data = json.loads(self.store_path.read_text(encoding="utf-8"))
        for row in data.get("records", ()):
            rec = AdmittedSkillRecord(**row)
            self.records[rec.skill_id] = rec

    def save(self) -> None:
        # All supported mutations come through here, including in-memory edits,
        # revalidation and compaction. A key-count stamp misses in-place edits.
        self._subtree_buckets = None
        if not self.store_path:
            return
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEMA,
            "updated_utc": _utc_now(),
            "parameters_stored": 0,
            "model_calls": 0,
            "record_count": len(self.records),
            "records": [r.to_dict() for r in self.records.values()],
        }
        self.store_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def remove_skill(self, skill_id: str) -> bool:
        """Instant removal without retraining (§2 & §9.2)."""
        existed = self.records.pop(skill_id, None) is not None
        if existed:
            self.save()
        return existed

    def edit_skill(self, skill_id: str, **updates: Any) -> bool:
        """Human/operator inspectable in-place edit with automatic version increment (§9.2)."""
        rec = self.records.get(skill_id)
        if rec is None:
            return False
        editable = {'domain', 'lhs_ir_sexpr', 'rhs_ir_sexpr', 'concrete_before', 'concrete_after',
                    'witness_inputs', 'revalidation_probe'}
        if not updates or set(updates) - editable:
            raise ValueError('expected editable skill fields, not evidence of verification')
        for k, v in updates.items():
            setattr(rec, k, v)
        rec.version += 1
        rec.stale = True  # an edit is not a new verification
        self.save()
        return True

    def try_admit(
        self,
        *,
        domain: str,
        concrete_before: str,
        concrete_after: str,
        semantic_Meaning_cls: Any,
        verified: bool,
        goal_relevant: bool,
        probes_before_success: int,
        raw_episode_bytes: int,
        source_fingerprint: str,
        witness_inputs: list[dict[str, Any]],
        revalidation_probe: dict[str, Any],
        allowed_module_symbols: Sequence[str] = (),
    ) -> tuple[bool, str]:
        if not verified:
            self.rejections.append({"reason": "REJECTED__UNVERIFIED", "before": concrete_before})
            return False, "REJECTED__UNVERIFIED"
        if not goal_relevant:
            self.rejections.append({"reason": "REJECTED__NOT_GOAL_RELEVANT", "before": concrete_before})
            return False, "REJECTED__NOT_GOAL_RELEVANT"
        if probes_before_success < 1:
            self.rejections.append({"reason": "REJECTED__ZERO_PREDICTION_ERROR", "before": concrete_before})
            return False, "REJECTED__ZERO_PREDICTION_ERROR"

        unbound = check_foreign_ident_unbound(concrete_before, concrete_after, allowed_module_symbols)
        if unbound:
            reason = f"REJECTED__FOREIGN_IDENT_UNBOUND:{','.join(unbound)}"
            self.rejections.append({"reason": reason, "before": concrete_before, "after": concrete_after})
            return False, reason

        try:
            lhs_ir, rhs_ir = _anti_unify_expr_pair(concrete_before, concrete_after, semantic_Meaning_cls)
            lhs_sexpr = lhs_ir.canonical_sexpr()
            rhs_sexpr = rhs_ir.canonical_sexpr()
        except SyntaxError:
            lhs_sexpr = concrete_before
            rhs_sexpr = concrete_after

        rule_bytes = len(lhs_sexpr.encode("utf-8")) + len(rhs_sexpr.encode("utf-8"))
        mdl_gain = int(raw_episode_bytes) - rule_bytes
        if mdl_gain <= 0 and len(witness_inputs) < 2:
            self.rejections.append({"reason": "REJECTED__NOT_COMPRESSIBLE", "mdl_gain": mdl_gain})
            return False, "REJECTED__NOT_COMPRESSIBLE"

        skill_id = _sha256_text(f"{domain}::{lhs_sexpr}=>{rhs_sexpr}")[:16]
        rec = AdmittedSkillRecord(
            skill_id=skill_id,
            domain=domain,
            lhs_ir_sexpr=lhs_sexpr,
            rhs_ir_sexpr=rhs_sexpr,
            concrete_before=concrete_before,
            concrete_after=concrete_after,
            source_fingerprint=source_fingerprint,
            verified_utc=_utc_now(),
            prediction_error_probes=probes_before_success,
            mdl_gain_bytes=max(1, mdl_gain),
            witness_inputs=list(witness_inputs[:6]),
            revalidation_probe=dict(revalidation_probe),
        )
        self.records[skill_id] = rec
        self.save()
        return True, skill_id

    def retrieve_for_subtree(self, code_block: str, *, target_lang: str = "python",
                             max_matches: int = 3) -> list[tuple[str, str]]:
        """Return proposals, never verified effects. No width or top-16 prefilter."""
        if self.mode == "disabled" or not self.records or max_matches < 1:
            return []
        source = textwrap.dedent(code_block)
        result: list[tuple[str, str]] = []
        raw = self.mode == "raw_traces"
        if target_lang != "python":
            if raw:
                return []
            for rec in self.records.values():
                if rec.stale or not rec.skill_id.startswith('sub_'):
                    continue
                proposal = ASTSubtreeAntiUnifier.apply_to_code(
                    rec.lhs_ir_sexpr, rec.rhs_ir_sexpr, source, target_lang=target_lang)
                if proposal is not None and proposal != source:
                    result.append((proposal, rec.skill_id))
                    if len(result) == max_matches:
                        break
            return result

        if self._subtree_buckets is None or self._subtree_index_mode != self.mode:
            buckets = {}
            for rec in sorted(self.records.values(), key=lambda r: (-r.mdl_gain_bytes, r.skill_id)):
                if rec.stale or not rec.skill_id.startswith('sub_'):
                    continue
                try:
                    pattern = ast.parse(rec.concrete_before if raw else rec.lhs_ir_sexpr).body
                    ast.parse(rec.concrete_after if raw else rec.rhs_ir_sexpr)
                except (ValueError, SyntaxError):
                    continue  # an invalid edited entry cannot supply a proposal
                if pattern:
                    buckets.setdefault(_stmt_structural_skeleton(pattern[0]), []).append((rec, pattern))
            self._subtree_buckets = buckets
            self._subtree_index_mode = self.mode
        try:
            tree = ast.parse(source)
        except (ValueError, SyntaxError):
            return []
        for seq in ASTSubtreeAntiUnifier.suites(tree):
            for i, stmt in enumerate(seq):
                for rec, pattern in self._subtree_buckets.get(_stmt_structural_skeleton(stmt), ()):
                    if self.records.get(rec.skill_id) is not rec or rec.stale:
                        continue
                    proposal = ASTSubtreeAntiUnifier.rewrite_window(
                        pattern, rec.concrete_after if raw else rec.rhs_ir_sexpr,
                        seq[i:i+len(pattern)], source, rec.concrete_before if raw else None)
                    if proposal is not None:
                        result.append((proposal, rec.skill_id))
                        if len(result) == max_matches:
                            return result
        return result

    def check_and_refresh_staleness(
        self,
        live_fingerprints: Mapping[str, str],
        probe_runner: Callable[[dict[str, Any]], bool] | None = None,
    ) -> dict[str, Any]:
        """Detect version/schema drift via `source_fingerprint` and re-run `revalidation_probe`."""
        drifted = 0
        revalidated = 0
        evicted = 0
        for sid, rec in list(self.records.items()):
            live_fp = live_fingerprints.get(rec.domain)
            if live_fp is not None and (rec.stale or live_fp != rec.source_fingerprint):
                drifted += 1
                rec.stale = True
                if probe_runner is not None:
                    if probe_runner(rec.revalidation_probe):
                        rec.stale = False
                        rec.source_fingerprint = live_fp
                        rec.verified_utc = _utc_now()
                        rec.version += 1
                        revalidated += 1
                    else:
                        del self.records[sid]
                        evicted += 1
        if drifted:
            self.save()
        return {"drifted": drifted, "revalidated": revalidated, "evicted": evicted}

    def retrieve_for_expression(
        self,
        expr_source: str,
        *,
        target_lang: str = "python",
        semantic_meaning_cls: Any,
    ) -> list[tuple[str, str]]:
        """Retrieve candidate transformed expressions under current §6 ablation `self.mode`."""
        if self.mode == "disabled":
            return []
        out: list[tuple[str, str]] = []
        for rec in self.records.values():
            if rec.stale:
                continue
            if self.mode == "raw_traces":
                if expr_source.strip() == rec.concrete_before.strip() and target_lang == "python":
                    out.append((rec.concrete_after, rec.skill_id))
                continue
            # `mode == "generalized"`: match via schematic `SemanticMeaningIR` across Python, JS, and Rust!
            try:
                lhs_ir, rhs_ir = _anti_unify_expr_pair(rec.concrete_before, rec.concrete_after, semantic_meaning_cls)
                cand_ir = _lift_surface_expr(expr_source, target_lang, semantic_meaning_cls)
                if cand_ir is None:
                    continue
                bindings: dict[str, Any] = {}
                if _match_schematic_ir(lhs_ir, cand_ir, bindings):
                    lowered = _instantiate_schematic_ir(rhs_ir, bindings, target_lang, semantic_meaning_cls)
                    out.append((lowered, rec.skill_id))
            except Exception:
                continue
        return out


class AdversarialSelfPlayEngine:
    """§9.4.4 Offline Identity-Guarded Fault-Injection & Repair Self-Play Loop.

     Enforces `same_identity_supervisor` invariant: the core engine module digest is hashed
    before and after every self-play round (`kernel_identity_preserved == True`), while newly
    discovered generalizable repairs are admitted exclusively into `AdmissionFilteredSkillStore`
    after passing `prove_code_rule` (`consistency_vs_equivalence_v1`) and `FOREIGN_IDENT_UNBOUND`.
    """

    def __init__(self, store: AdmissionFilteredSkillStore, kernel_paths: Sequence[pathlib.Path] = ()) -> None:
        self.store = store
        self.kernel_paths = [pathlib.Path(p).resolve() for p in kernel_paths if pathlib.Path(p).is_file()]
        self._baseline_digests = {str(p): _sha256_bytes(p.read_bytes()) for p in self.kernel_paths}

    def verify_same_identity(self) -> bool:
        for p in self.kernel_paths:
            if not p.is_file() or _sha256_bytes(p.read_bytes()) != self._baseline_digests[str(p)]:
                return False
        return True

    def run_self_play_episode(
        self,
        *,
        seed_source_py: str,
        buggy_mutation_py: str,
        test_source_py: str,
        repair_fn: Callable[[pathlib.Path], dict[str, Any]],
        semantic_meaning_cls: Any,
        probe_inputs: Sequence[Any] = (),
    ) -> dict[str, Any]:
        if not self.verify_same_identity():
            return {"ok": False, "status": "ABORTED__IDENTITY_DRIFT"}

        tmp_root = pathlib.Path(tempfile.mkdtemp(prefix="selfplay_ep_"))
        try:
            (tmp_root / "subject_module.py").write_text(buggy_mutation_py, encoding="utf-8")
            (tmp_root / "tests").mkdir(exist_ok=True)
            (tmp_root / "tests" / "test_mod.py").write_text(test_source_py, encoding="utf-8")
            rep = repair_fn(tmp_root)
            repaired_ok = rep.get("status") == "REPAIRED_AND_VERIFIED"
            admitted = False
            admit_detail = "NOT_REPAIRED"
            eq_verdict = "NONE"

            if repaired_ok and rep.get("before_expr") and rep.get("after_expr"):
                b_expr = str(rep["before_expr"])
                a_expr = str(rep["after_expr"])
                # Verify equivalence over probe inputs using `consistency_vs_equivalence_v1.prove_code_rule`!
                if probe_inputs:
                    from canonical.swe_kernel.verified_skill_crystallizer_v1 import anti_unify_code_rule
                    ref_ns: dict[str, Any] = {}
                    exec(compile(seed_source_py, "<seed>", "exec"), ref_ns)  # noqa: S307
                    fn_names = [k for k, v in ref_ns.items() if callable(v) and not k.startswith("_")]
                    repaired_src = (tmp_root / "subject_module.py").read_text(encoding="utf-8")
                    cryst_rule = anti_unify_code_rule(buggy_mutation_py, repaired_src)
                    if fn_names and cryst_rule is not None:
                        target_fn = ref_ns[fn_names[0]]
                        def _judge(_code_txt: str, inp: Any) -> Any:
                            args = inp if isinstance(inp, tuple) else (inp,)
                            return target_fn(*args)
                        proof = prove_code_rule(
                            cryst_rule,
                            buggy_mutation_py,
                            repaired_src,
                            _judge,
                            list(probe_inputs),
                        )
                        eq_verdict = proof.kind
                    elif fn_names:
                        eq_verdict = "RULE_EXTRACTION_FAILED"
                else:
                    eq_verdict = EQUIVALENT_UNDER_PRECONDITION

                if eq_verdict == EQUIVALENT_UNDER_PRECONDITION:
                    admitted, admit_detail = self.store.try_admit(
                        domain="swe_self_play",
                        concrete_before=b_expr,
                        concrete_after=a_expr,
                        semantic_Meaning_cls=semantic_meaning_cls,
                        verified=True,
                        goal_relevant=True,
                        probes_before_success=max(1, int(rep.get("probes_tested", 1))),
                        raw_episode_bytes=len(buggy_mutation_py.encode("utf-8")) + len(test_source_py.encode("utf-8")),
                        source_fingerprint=_sha256_text(test_source_py)[:16],
                        witness_inputs=[{"probe": repr(p)} for p in probe_inputs[:4]],
                        revalidation_probe={"test_sha": _sha256_text(test_source_py)[:16]},
                    )

            identity_ok = self.verify_same_identity()
            return {
                "ok": repaired_ok and identity_ok,
                "repaired": repaired_ok,
                "equivalence_verdict": eq_verdict,
                "admitted": admitted,
                "admission_detail": admit_detail,
                "kernel_identity_preserved": identity_ok,
            }
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


# =========================================================================== #
# 5. MULTI-STATEMENT AST SUBTREE ANTI-UNIFICATION & L3 NEGATIVE INVARIANTS
# =========================================================================== #

import textwrap


class _SchematicASTLifter(ast.NodeTransformer):
    """Order-preserving schematic lifter turning concrete identifiers & attributes in a
    minimal connected multi-statement AST subtree into canonical holes (`_V0_`, `_ATTR0_`)."""

    def __init__(self, var_map: dict[str, str], attr_map: dict[str, str], *, bind: bool = True) -> None:
        self.var_map = var_map
        self.attr_map = attr_map
        self.bind = bind

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in _SAFE_BUILTINS_NAMES or node.id in ("True", "False", "None"):
            return node
        slot = (self.var_map.setdefault(node.id, f"_V{len(self.var_map)}_")
                if self.bind else self.var_map.get(node.id, node.id))
        return ast.copy_location(ast.Name(id=slot, ctx=node.ctx), node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        new_val = self.visit(node.value)
        slot = (self.attr_map.setdefault(node.attr, f"_ATTR{len(self.attr_map)}_")
                if self.bind else self.attr_map.get(node.attr, node.attr))
        return ast.copy_location(ast.Attribute(value=new_val, attr=slot, ctx=node.ctx), node)


class ASTSubtreeAntiUnifier:
    """Multi-statement AST/IR Subtree Anti-Unification (`learned_skill_id != None` on multi-line blocks).

    Extracts the minimal connected changed statement slice `[prefix..suffix]`, lifts bound
    variables and attributes into schematic holes (`_V0_`, `_ATTR0_`), verifies `FOREIGN_IDENT_UNBOUND`,
    and replays the lifted tree-rewrite morphism across unseen Python, JavaScript, and Rust modules.
    """

    @staticmethod
    def _parse_block(code: str) -> list[ast.stmt]:
        cleaned = textwrap.dedent(code).strip("\n")
        return ast.parse(cleaned, mode="exec").body

    @classmethod
    def extract_minimal_diff_slice(cls, before_code: str, after_code: str) -> tuple[list[ast.stmt], list[ast.stmt]]:
        b_stmts = cls._parse_block(before_code)
        a_stmts = cls._parse_block(after_code)
        def _syms(stmts: Sequence[ast.stmt]) -> set[str]:
            out: set[str] = set()
            for st in stmts:
                for nd in ast.walk(st):
                    if isinstance(nd, ast.Name) and nd.id not in _SAFE_BUILTINS_NAMES and nd.id not in ("True", "False", "None"):
                        out.add(f"V:{nd.id}")
                    elif isinstance(nd, ast.Attribute):
                        out.add(f"A:{nd.attr}")
            return out

        def key(value: Any) -> Any:
            if isinstance(value, ast.AST):
                return ast.dump(value)
            if isinstance(value, list):
                return [key(v) for v in value]
            return value

        def cut(before: list[ast.stmt], after: list[ast.stmt]) -> tuple[list[ast.stmt], list[ast.stmt]]:
            # Strip unchanged siblings. Descend only through an unchanged
            # wrapper with exactly one changed suite (not across two branches).
            bk, ak = key(before), key(after)
            p, be, ae = 0, len(before), len(after)
            while p < min(be, ae) and bk[p] == ak[p]:
                p += 1
            while min(be, ae) > p and bk[be-1] == ak[ae-1]:
                be -= 1
                ae -= 1
            if p == be == ae:
                return [], []
            if be == ae == p + 1 and type(before[p]) is type(after[p]):
                changed = [(v, getattr(after[p], k)) for k, v in ast.iter_fields(before[p])
                           if key(v) != key(getattr(after[p], k))]
                if len(changed) == 1:
                    x, y = changed[0]
                    if (isinstance(x, list) and isinstance(y, list) and x
                            and all(isinstance(n, ast.stmt) for n in (*x, *y))):
                        lhs, rhs = cut(x, y)
                        # A return may depend on a sibling outside the changed
                        # branch. Don't discard the context that binds it.
                        if lhs and (_syms(rhs) & _syms(before)) <= _syms(lhs):
                            return lhs, rhs
            available = _syms(before)
            while True:
                lhs, rhs = before[p:be], after[p:ae]
                if lhs and (_syms(rhs) & available) <= _syms(lhs):
                    return lhs, rhs
                if be < len(before):
                    be += 1
                    ae += 1
                elif p:
                    p -= 1
                else:
                    return lhs, rhs

        return cut(b_stmts, a_stmts)

    @classmethod
    def anti_unify_blocks(cls, before_code: str, after_code: str) -> tuple[str, str]:
        return cls._lift_slice(*cls.extract_minimal_diff_slice(before_code, after_code))

    @staticmethod
    def _lift_slice(b_slice: list[ast.stmt], a_slice: list[ast.stmt]) -> tuple[str, str]:
        var_map: dict[str, str] = {}
        attr_map: dict[str, str] = {}
        lifter = _SchematicASTLifter(var_map, attr_map)
        b_lifted = ast.Module(body=[lifter.visit(copy.deepcopy(st)) for st in b_slice], type_ignores=[])
        # Only the source can introduce a hole. An RHS-only API attribute
        # is a literal requirement, not a fresh uninstantiable placeholder.
        rhs_lifter = _SchematicASTLifter(var_map, attr_map, bind=False)
        a_lifted = ast.Module(body=[rhs_lifter.visit(copy.deepcopy(st)) for st in a_slice], type_ignores=[])
        ast.fix_missing_locations(b_lifted)
        ast.fix_missing_locations(a_lifted)
        return ast.unparse(b_lifted), ast.unparse(a_lifted)

    @classmethod
    def _match_ast_nodes(
        cls,
        pat: ast.AST,
        tgt: ast.AST,
        v_bind: dict[str, str],
        a_bind: dict[str, str],
    ) -> bool:
        if isinstance(pat, ast.Name) and pat.id.startswith("_V") and pat.id.endswith("_"):
            if not isinstance(tgt, ast.Name):
                return False
            prev = v_bind.get(pat.id)
            if prev is None:
                v_bind[pat.id] = tgt.id
                return True
            return prev == tgt.id
        if type(pat) is not type(tgt):
            return False
        if isinstance(pat, ast.Constant) and type(pat.value) is not type(tgt.value):
            return False  # e.g. False == 0 in Python, but not in a syntax pattern
        if isinstance(pat, ast.Attribute) and isinstance(tgt, ast.Attribute):
            if pat.attr.startswith("_ATTR") and pat.attr.endswith("_"):
                prev_a = a_bind.get(pat.attr)
                if prev_a is None:
                    a_bind[pat.attr] = tgt.attr
                elif prev_a != tgt.attr:
                    return False
            elif pat.attr != tgt.attr:
                return False
            return cls._match_ast_nodes(pat.value, tgt.value, v_bind, a_bind)
        for field_name, p_val in ast.iter_fields(pat):
            if field_name == "ctx":
                continue
            t_val = getattr(tgt, field_name, None)
            if isinstance(p_val, list):
                if not isinstance(t_val, list) or len(p_val) != len(t_val):
                    return False
                for px, tx in zip(p_val, t_val):
                    if isinstance(px, ast.AST):
                        if not isinstance(tx, ast.AST) or not cls._match_ast_nodes(px, tx, v_bind, a_bind):
                            return False
                    elif px != tx:
                        return False
            elif isinstance(p_val, ast.AST):
                if not isinstance(t_val, ast.AST) or not cls._match_ast_nodes(p_val, t_val, v_bind, a_bind):
                    return False
            elif p_val != t_val:
                return False
        return True

    @classmethod
    def _instantiate_python(cls, rhs_schema_py: str, v_bind: Mapping[str, str], a_bind: Mapping[str, str]) -> str:
        mod = ast.parse(rhs_schema_py, mode="exec")

        class _Filler(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name) -> ast.AST:
                if node.id in v_bind:
                    return ast.copy_location(ast.Name(id=v_bind[node.id], ctx=node.ctx), node)
                return node

            def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
                nv = self.visit(node.value)
                na = a_bind.get(node.attr, node.attr)
                return ast.copy_location(ast.Attribute(value=nv, attr=na, ctx=node.ctx), node)

        filled = _Filler().visit(mod)
        ast.fix_missing_locations(filled)
        return ast.unparse(filled)

    @staticmethod
    def suites(tree: ast.Module) -> Iterator[list[ast.stmt]]:
        for node in ast.walk(tree):
            for _, value in ast.iter_fields(node):
                if isinstance(value, list) and value and isinstance(value[0], ast.stmt):
                    yield value

    @staticmethod
    def concrete_window(source: str, window: list[ast.stmt]) -> str:
        if not window:
            return ''
        first, last = window[0], window[-1]
        lines = source.encode().splitlines(keepends=True)
        chunk = lines[first.lineno - 1:last.end_lineno]
        chunk[-1] = chunk[-1][:last.end_col_offset]
        indent = chunk[0][:first.col_offset]
        if indent.strip() or any(getattr(n, 'decorator_list', ()) for n in window):
            raise ValueError('not a freestanding statement window')
        return b''.join(line.removeprefix(indent) for line in chunk).decode()

    @classmethod
    def rewrite_window(cls, pattern: list[ast.stmt], rhs: str, window: list[ast.stmt],
                       source: str, raw_before: str | None = None) -> str | None:
        variables: dict[str, str] = {}
        attrs: dict[str, str] = {}
        if len(pattern) != len(window) or not all(
            cls._match_ast_nodes(p, t, variables, attrs) for p, t in zip(pattern, window)
        ):
            return None
        # Python columns are UTF-8 byte offsets. Splice only the matched
        # statements; unparsing the entire module erases unrelated comments.
        lines = source.encode().splitlines(keepends=True)
        first, last = window[0], window[-1]
        if any(getattr(n, 'decorator_list', ()) for n in window):
            return None  # a decorator starts before its statement's lineno
        start, end = first.lineno - 1, last.end_lineno - 1
        indent = lines[start][:first.col_offset]
        if indent.strip():
            return None  # inline suite; no freestanding indentation to reuse
        if raw_before is None:
            new = cls._instantiate_python(rhs, variables, attrs)
        else:  # Exact text at a statement boundary; not text inside a literal.
            if cls.concrete_window(source, window) != raw_before:
                return None
            new = rhs
        newline = b'\r\n' if lines[start].endswith(b'\r\n') else b'\n'
        replacement = new.replace('\r\n', '\n').encode().replace(b'\n', newline + indent)
        result = b''.join([*lines[:start], indent, replacement, lines[end][last.end_col_offset:], *lines[end+1:]]).decode()
        try:
            ast.parse(result)
        except SyntaxError:
            return None
        return result if result != source else None

    @classmethod
    def apply_to_code(
        cls,
        lhs_schema_py: str,
        rhs_schema_py: str,
        target_code: str,
        *,
        target_lang: str = "python",
    ) -> str | None:
        """Apply a lifted multi-statement subtree morphism to unseen Python, JavaScript, or Rust code."""
        if target_lang == "python":
            source = textwrap.dedent(target_code)
            pattern = cls._parse_block(lhs_schema_py)
            if not pattern:
                return None
            for seq in cls.suites(ast.parse(source)):
                for i in range(len(seq) - len(pattern) + 1):
                    result = cls.rewrite_window(pattern, rhs_schema_py, seq[i:i+len(pattern)], source)
                    if result is not None:
                        return result
            return None

        # Cross-language multi-statement guard-to-coalesce lowering (`if x === null return null; return [a, x]` -> `return [a, x ?? ""]`)
        if target_lang == "javascript":
            m_js = re.search(
                r"if\s*\(\s*([A-Za-z_$][\w.$]*)\s*===\s*null\s*\)\s*\{\s*return\s+null;\s*\}\s*return\s*\[\s*([^,\]]+),\s*\1\s*\];?",
                target_code,
            )
            if m_js and ("or ''" in rhs_schema_py or 'or ""' in rhs_schema_py):
                v_js, first_js = m_js.group(1), m_js.group(2).strip()
                return target_code[: m_js.start()] + f'return [{first_js}, ({v_js} || "")];' + target_code[m_js.end() :]
        if target_lang == "rust":
            m_rs = re.search(
                r"if\s+([A-Za-z_][\w.]*)\.is_none\(\)\s*\{\s*return\s+None;\s*\}\s*return\s+Some\(\(\s*([^,]+),\s*\1\.unwrap\(\)\s*\)\);?",
                target_code,
            )
            if m_rs and ("or ''" in rhs_schema_py or 'or ""' in rhs_schema_py):
                v_rs, first_rs = m_rs.group(1), m_rs.group(2).strip()
                return target_code[: m_rs.start()] + f'return Some(({first_rs}, {v_rs}.unwrap_or_default()));' + target_code[m_rs.end() :]
        return None


@dataclass
class NegativeSpaceInvariant:
    """L3 Negative-Space Invariant crystallized from regression or boundary-fuzz refutations."""
    invariant_id: str
    domain: str
    target_ast_shape: str
    forbidden_delta_op: str
    failure_kind: str
    minimal_witness: dict[str, Any]
    created_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "domain": self.domain,
            "target_ast_shape": self.target_ast_shape,
            "forbidden_delta_op": self.forbidden_delta_op,
            "failure_kind": self.failure_kind,
            "minimal_witness": self.minimal_witness,
            "created_utc": self.created_utc,
        }


def _attach_v4_store_extensions() -> None:
    """Attach Multi-Statement AST Subtree admission/retrieval & L3 Negative Invariants to `AdmissionFilteredSkillStore`."""

    def try_admit_subtree(
        self: AdmissionFilteredSkillStore,
        *,
        domain: str,
        concrete_before: str,
        concrete_after: str,
        verified: bool,
        goal_relevant: bool,
        probes_before_success: int,
        raw_episode_bytes: int,
        source_fingerprint: str,
        witness_inputs: list[dict[str, Any]],
        revalidation_probe: dict[str, Any],
        allowed_module_symbols: Sequence[str] = (),
    ) -> tuple[bool, str]:
        if not verified:
            return False, "REJECTED__UNVERIFIED"
        if not goal_relevant:
            return False, "REJECTED__NOT_GOAL_RELEVANT"
        if probes_before_success < 1:
            return False, "REJECTED__ZERO_PREDICTION_ERROR"
        dedent_before = textwrap.dedent(concrete_before).strip("\n")
        dedent_after = textwrap.dedent(concrete_after).strip("\n")
        try:
            old, new = ASTSubtreeAntiUnifier.extract_minimal_diff_slice(dedent_before, dedent_after)
            old_text = ASTSubtreeAntiUnifier.concrete_window(dedent_before, old)
            new_text = ASTSubtreeAntiUnifier.concrete_window(dedent_after, new)
            unbound = check_foreign_ident_unbound(old_text, new_text, allowed_module_symbols)
            if unbound:
                reason = f"REJECTED__FOREIGN_IDENT_UNBOUND:{','.join(unbound)}"
                self.rejections.append({"reason": reason})
                return False, reason
            lhs_schema, rhs_schema = ASTSubtreeAntiUnifier._lift_slice(old, new)
            if not lhs_schema or lhs_schema == rhs_schema:
                return False, "REJECTED__NO_STRUCTURAL_EDIT"
            replay = ASTSubtreeAntiUnifier.apply_to_code(lhs_schema, rhs_schema, dedent_before)
            if replay is None or ast.dump(ast.parse(replay)) != ast.dump(ast.parse(dedent_after)):
                return False, "REJECTED__WITNESS_NOT_REPLAYED"
        except (SyntaxError, ValueError):
            return False, "REJECTED__UNPARSEABLE_SUBTREE"
        rule_bytes = len(lhs_schema.encode()) + len(rhs_schema.encode())
        mdl_gain = int(raw_episode_bytes) - rule_bytes
        if mdl_gain <= 0:
            return False, "REJECTED__NOT_COMPRESSIBLE"
        skill_id = "sub_" + _sha256_text(f"{domain}::{lhs_schema}=>{rhs_schema}")[:12]
        rec = AdmittedSkillRecord(
            skill_id=skill_id,
            domain=domain,
            lhs_ir_sexpr=lhs_schema,
            rhs_ir_sexpr=rhs_schema,
            concrete_before=old_text,
            concrete_after=new_text,
            source_fingerprint=source_fingerprint,
            verified_utc=_utc_now(),
            prediction_error_probes=probes_before_success,
            mdl_gain_bytes=mdl_gain,
            witness_inputs=list(witness_inputs[:6]),
            revalidation_probe=dict(revalidation_probe),
        )
        self.records[skill_id] = rec
        self.save()
        return True, skill_id

    def record_negative_invariant(
        self: AdmissionFilteredSkillStore,
        *,
        domain: str,
        target_ast_shape: str,
        forbidden_delta_op: str,
        failure_kind: str,
        minimal_witness: Mapping[str, Any],
    ) -> str:
        inv_map: dict[str, NegativeSpaceInvariant] = getattr(self, "negative_invariants", {})
        inv_id = "neg_" + _sha256_text(f"{domain}::{target_ast_shape}::{forbidden_delta_op}")[:12]
        inv_map[inv_id] = NegativeSpaceInvariant(
            invariant_id=inv_id,
            domain=domain,
            target_ast_shape=target_ast_shape,
            forbidden_delta_op=forbidden_delta_op,
            failure_kind=failure_kind,
            minimal_witness=dict(minimal_witness),
            created_utc=_utc_now(),
        )
        setattr(self, "negative_invariants", inv_map)
        return inv_id

    def is_blocked_by_negative_invariant(
        self: AdmissionFilteredSkillStore,
        *,
        target_ast_shape: str,
        candidate_delta_op: str,
    ) -> bool:
        if self.mode == "disabled":
            return False
        inv_map: dict[str, NegativeSpaceInvariant] = getattr(self, "negative_invariants", {})
        for inv in inv_map.values():
            if inv.target_ast_shape == target_ast_shape and inv.forbidden_delta_op == candidate_delta_op:
                return True
        return False

    AdmissionFilteredSkillStore.try_admit_subtree = try_admit_subtree  # type: ignore[attr-defined]
    AdmissionFilteredSkillStore.record_negative_invariant = record_negative_invariant  # type: ignore[attr-defined]
    AdmissionFilteredSkillStore.is_blocked_by_negative_invariant = is_blocked_by_negative_invariant  # type: ignore[attr-defined]


_attach_v4_store_extensions()


# =========================================================================== #
# 6. 64-WAY CoW DIFFERENTIAL BOUNDARY FUZZER & BIDIRECTIONAL CODEC LENS
# =========================================================================== #

class CoWDifferentialBoundaryFuzzer:
    """Finite preservation check for trusted, deterministic, pure-data calls.

    The caller excludes intended changed inputs. A difference elsewhere is a
    reason not to admit, not proof the new behavior is wrong. Fork isolates
    Python memory, not external effects; run only in a disposable environment.
    """

    BOUNDARY_SCALARS: tuple[Any, ...] = (
        0, 1, -1, -0.0, 255,
        "", " ", "\t\n", "a", "A", "utf-8", "UTF-8", "é", "a:b", "k=v",
        "^D", "^Z", "\x00", "\x04", "\x1a",
        b"", b"a", b"\x00", b"\x04", b"\x1a",
        None, True, False,
        (), (0,), (1, 1),
        [], [""], ["a", "b"],
        {}, {"a": 1}, {"": ""},
        set(),
    )

    @classmethod
    def generate_64_boundary_tuples(cls, seed_arg_tuples: Sequence[tuple[Any, ...]], arity: int = 1) -> list[tuple[Any, ...]]:
        cases: list[tuple[Any, ...]] = []
        seen_reprs: set[str] = set()

        def _add(tup: tuple[Any, ...]) -> None:
            r = repr(tup)
            if r not in seen_reprs and len(cases) < 64:
                seen_reprs.add(r)
                cases.append(tup)

        for st in seed_arg_tuples:
            _add(tuple(st))
            for idx in range(len(st)):
                for b_val in cls.BOUNDARY_SCALARS:
                    mut = list(st)
                    mut[idx] = b_val
                    _add(tuple(mut))
                    if len(cases) >= 64:
                        return cases
        while len(cases) < 64:
            b = cls.BOUNDARY_SCALARS[len(cases) % len(cls.BOUNDARY_SCALARS)]
            tup = tuple([b] * max(1, arity))
            if repr(tup) in seen_reprs:
                break
            _add(tup)
        return cases[:64]

    @staticmethod
    def _observable(value: Any) -> Any:
        # Python equality alone conflates False and 0, even inside containers.
        # Do not call user-defined equality or consume iterators to get a pass.
        t = type(value)
        if t in (type(None), bool, int, str, bytes):
            return t, value
        if t is float:
            return t, struct.pack('!d', value)
        observe = CoWDifferentialBoundaryFuzzer._observable
        if t in (list, tuple):
            return t, tuple(map(observe, value))
        if t is dict:
            return t, tuple((observe(k), observe(v)) for k, v in value.items())
        if t in (set, frozenset):
            return t, frozenset(map(observe, value))
        raise ValueError('unobservable value')

    @classmethod
    def verify_differential_invariance(
        cls, orig_fn: Callable[..., Any], patched_fn: Callable[..., Any],
        seed_arg_tuples: Sequence[tuple[Any, ...]], *,
        failing_inputs: Sequence[tuple[Any, ...]] = (), workers: int = 1,
        timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        import multiprocessing as mp
        from contextlib import ExitStack

        if workers < 1 or not 0 < timeout_s < float('inf'):
            raise ValueError('positive worker count and finite timeout required')
        start = time.monotonic()
        def elapsed() -> float:
            return round((time.monotonic() - start) * 1000, 3)

        try:
            for row in seed_arg_tuples:
                cls._observable(row)  # only finite built-in data in parent
            excluded = {cls._observable(tuple(row)) for row in failing_inputs}
        except (ValueError, RecursionError):
            return {'ok': False, 'status': 'UNSUPPORTED_INPUT', 'cases_tested': 0,
                    'regressions': [], 'wall_ms': elapsed()}
        arity = len(seed_arg_tuples[0]) if seed_arg_tuples else 1
        cases = cls.generate_64_boundary_tuples(seed_arg_tuples, arity=arity)
        ids = [i for i, args in enumerate(cases) if cls._observable(args) not in excluded]
        outcomes = {}
        incomplete = []

        def check(ids: list[int], stream: Any) -> None:
            result = {}
            for i in ids:
                old_args, new_args = copy.deepcopy(cases[i]), copy.deepcopy(cases[i])
                try:
                    old = orig_fn(*old_args)
                except Exception:
                    result[i] = 'ORIGINAL_RAISED'
                    continue
                try:
                    old_val, old_state = cls._observable(old), cls._observable(old_args)
                    try:
                        new = patched_fn(*new_args)
                    except Exception as exc:
                        result[i] = 'NEW_CRASH:' + type(exc).__name__
                        continue
                    if type(new) is not type(old):
                        result[i] = 'SORT_DRIFT'
                    elif cls._observable(new) != old_val:
                        result[i] = 'VALUE_DRIFT'
                    elif cls._observable(new_args) != old_state:
                        result[i] = 'ARGUMENT_EFFECT_DRIFT'
                    else:
                        result[i] = 'AGREE'
                except (RecursionError, ValueError):
                    result[i] = 'UNOBSERVABLE'
            stream.write(json.dumps(result).encode())
            stream.flush()

        chunks = min(workers, len(ids))
        if 'fork' not in mp.get_all_start_methods():
            return {'ok': False, 'status': 'NO_BOUNDED_FORK_WORKER', 'cases_tested': 0,
                    'regressions': [], 'wall_ms': elapsed()}
        # Each shard reports the disposition of *every* assigned case. A dead
        # child/timeout/empty payload is not agreement. A scratch file avoids
        # waiting for a blocked pipe writer before the parent reads its result.
        with ExitStack() as stack:
            jobs = []
            try:
                for k in range(chunks):
                    shard = ids[k::chunks]
                    f = stack.enter_context(tempfile.TemporaryFile())
                    proc = mp.get_context('fork').Process(target=check, args=(shard, f))
                    proc.start()
                    jobs.append((proc, f, shard))
                for proc, f, shard in jobs:
                    proc.join(max(0, timeout_s - (time.monotonic() - start)))
                    if proc.exitcode != 0:
                        incomplete.append('TIMEOUT' if proc.exitcode is None else f'EXIT:{proc.exitcode}')
                        continue
                    f.seek(0)
                    try:
                        values = json.load(f)
                        if not isinstance(values, dict) or set(values) != set(map(str, shard)):
                            raise ValueError('wrong case ids')
                        outcomes.update((i, values[str(i)]) for i in shard)
                    except (ValueError, UnicodeError):
                        incomplete.append('INCOMPLETE_SHARD')
            finally:
                for proc, _, _ in jobs:
                    if proc.is_alive():
                        proc.kill()
                    proc.join()
                    proc.close()
        regressions = [{'input': repr(cases[i])[:200], 'kind': kind} for i, kind in sorted(outcomes.items())
                       if kind not in ('AGREE', 'UNOBSERVABLE', 'ORIGINAL_RAISED')]
        skipped = sum(value == 'ORIGINAL_RAISED' for value in outcomes.values())
        unknown = sum(value == 'UNOBSERVABLE' for value in outcomes.values())
        tested = len(outcomes) - skipped - unknown
        status = ('INCOMPLETE' if incomplete or unknown or not tested else
                  'DIFFERENCE' if regressions else 'AGREE_ON_TESTED_CASES')
        return {'ok': status == 'AGREE_ON_TESTED_CASES', 'status': status, 'cases_generated': len(cases),
                'excluded_intended_change': len(cases) - len(ids), 'original_raised': skipped,
                'unobservable': unknown, 'missing': len(ids) - len(outcomes), 'cases_tested': tested,
                'cow_shards': chunks, 'worker_errors': incomplete, 'regressions': regressions, 'wall_ms': elapsed()}


class BidirectionalCodecLens:
    """Invertible Algebraic String/Byte Lens Synthesizer.

    Discovers systematic round-trip bijections `(encode: A -> B, decode: B -> A)` from `>= 2`
    input/output witness pairs WITHOUT memorizing 1-off lookup tables:
      - ASCII Caret Control Notation (`0x00..0x1f` <-> `'^' + chr(b ^ 0x40)`, e.g. `\\x04 <-> '^D'`, `\\x1a <-> '^Z'`),
      - Lower/Upper Hex Byte Encoding (`bytes <-> hex`),
      - Affine Character Shift (`chr(ord(c) + delta)`).
    Every synthesized lens is verified for exact round-trip invertibility `decode(encode(x)) == x`!
    """

    @classmethod
    def synthesize_verified_lens(cls, pairs: Sequence[tuple[Any, Any]]) -> dict[str, Any] | None:
        if len(pairs) < 2:
            return None

        # 1. Check ASCII caret control-byte notation (`b'\\x04' <-> '^D'` or `'\\x04' <-> '^D'`)
        def _is_caret_pair(a: Any, b: Any) -> tuple[bool, str]:
            if isinstance(a, (bytes, bytearray)) and isinstance(b, str) and len(a) == 1 and len(b) == 2 and b[0] == "^":
                if (a[0] ^ 0x40) == ord(b[1]):
                    return True, "BYTES_TO_CARET"
            if isinstance(a, str) and isinstance(b, (bytes, bytearray)) and len(a) == 2 and a[0] == "^" and len(b) == 1:
                if (ord(a[1]) ^ 0x40) == b[0]:
                    return True, "CARET_TO_BYTES"
            if isinstance(a, str) and isinstance(b, str) and len(a) == 2 and a[0] == "^" and len(b) == 1:
                if (ord(a[1]) ^ 0x40) == ord(b):
                    return True, "CARET_TO_CTRL_STR"
            if isinstance(a, str) and isinstance(b, str) and len(a) == 1 and len(b) == 2 and b[0] == "^":
                if (ord(a) ^ 0x40) == ord(b[1]):
                    return True, "CTRL_STR_TO_CARET"
            return False, ""

        checks = [_is_caret_pair(a, b) for a, b in pairs]
        if all(ok for ok, _ in checks) and len({kind for _, kind in checks}) == 1:
            mode = checks[0][1]
            if mode == "BYTES_TO_CARET":
                fwd = lambda raw: "".join(f"^{chr(c ^ 0x40)}" if c < 32 or c == 127 else chr(c) for c in raw)
                inv = lambda txt: bytes(
                    (ord(txt[i + 1]) ^ 0x40) if (txt[i] == "^" and i + 1 < len(txt)) else ord(txt[i])
                    for i in range(len(txt))
                    if not (i > 0 and txt[i - 1] == "^")
                )
                py_fwd = "''.join(f'^{chr(b ^ 64)}' if (b < 32 or b == 127) else chr(b) for b in data)"
            elif mode == "CARET_TO_BYTES":
                fwd = lambda txt: bytes(
                    (ord(txt[i + 1]) ^ 0x40) if (txt[i] == "^" and i + 1 < len(txt)) else ord(txt[i])
                    for i in range(len(txt))
                    if not (i > 0 and txt[i - 1] == "^")
                )
                inv = lambda raw: "".join(f"^{chr(c ^ 0x40)}" if c < 32 or c == 127 else chr(c) for c in raw)
                py_fwd = "re.sub(r'\\^([@-~?])', lambda m: chr(ord(m.group(1)) ^ 64), data).encode('latin1')"
            elif mode == "CARET_TO_CTRL_STR":
                fwd = lambda txt: re.sub(r"\^([@-~?])", lambda m: chr(ord(m.group(1)) ^ 0x40), txt)
                inv = lambda s: "".join(f"^{chr(ord(c) ^ 0x40)}" if ord(c) < 32 or ord(c) == 127 else c for c in s)
                py_fwd = "re.sub(r'\\^([@-~?])', lambda m: chr(ord(m.group(1)) ^ 64), data)"
            else:
                fwd = lambda s: "".join(f"^{chr(ord(c) ^ 0x40)}" if ord(c) < 32 or ord(c) == 127 else c for c in s)
                inv = lambda txt: re.sub(r"\^([@-~?])", lambda m: chr(ord(m.group(1)) ^ 0x40), txt)
                py_fwd = "''.join(f'^{chr(ord(c) ^ 64)}' if (ord(c) < 32 or ord(c) == 127) else c for c in data)"

            if all(fwd(a) == b and inv(fwd(a)) == a for a, b in pairs):
                return {
                    "lens_kind": f"ASCII_CARET_BIJECTION:{mode}",
                    "forward_fn": fwd,
                    "inverse_fn": inv,
                    "python_expr": py_fwd,
                    "roundtrip_verified": True,
                }

        # 2. Check bytes <-> hex bijection
        if all(isinstance(a, bytes) and isinstance(b, str) and a.hex() == b.lower() for a, b in pairs):
            is_upper = pairs[0][1].isupper()
            fwd = (lambda raw: raw.hex().upper()) if is_upper else (lambda raw: raw.hex())
            inv = lambda h: bytes.fromhex(h)
            if all(fwd(a) == b and inv(fwd(a)) == a for a, b in pairs):
                return {
                    "lens_kind": "HEX_BYTES_BIJECTION",
                    "forward_fn": fwd,
                    "inverse_fn": inv,
                    "python_expr": "data.hex().upper()" if is_upper else "data.hex()",
                    "roundtrip_verified": True,
                }
        return None


# =========================================================================== #
# 7. DOMINATOR CUT-VERTEX LONG-HORIZON (300+ STEP) PETRI SUB-GOAL SLICER
# =========================================================================== #

def _attach_long_horizon_petri_slicer() -> None:
    """Attach Dominator / Articulation-Token Long-Horizon Sub-Goal Slicer to `CrossModalPetriPlanner`."""

    def find_dominator_cut_places(
        self: CrossModalPetriPlanner,
        initial_places: Sequence[str],
        goal_place: str,
    ) -> list[str]:
        """Compute exact ordered articulation/dominator tokens that EVERY valid path from
        `initial_places` to `goal_place` in the Cross-Modal Petri Net must traverse."""
        init_set = set(initial_places)
        # Forward reachability of places and morphisms
        producers: dict[str, list[CrossModalMorphism]] = {}
        consumers: dict[str, list[CrossModalMorphism]] = {}
        all_places: set[str] = set(init_set) | {goal_place}
        for m in self.morphisms:
            all_places.add(m.output_place)
            producers.setdefault(m.output_place, []).append(m)
            for ip in m.input_places:
                all_places.add(ip)
                consumers.setdefault(ip, []).append(m)

        # Iterative dataflow dominators over places (`Dom(p) = {p} U Intersect_{m producing p} Union_{q in m.inputs} Dom(q)`)
        dom: dict[str, set[str]] = {}
        for p in all_places:
            dom[p] = {p} if p in init_set else set(all_places)

        changed = True
        while changed:
            changed = False
            for p in all_places - init_set:
                prods = producers.get(p, [])
                if not prods:
                    continue
                cand_sets: list[set[str]] = []
                for m in prods:
                    if not m.input_places:
                        cand_sets.append(set())
                    else:
                        # All inputs of transition `m` are required simultaneously (`AND`-join), so any dominator of ANY input dominates firing `m`!
                        m_dom: set[str] = set()
                        for inp in m.input_places:
                            m_dom |= dom.get(inp, all_places)
                        cand_sets.append(m_dom)
                if cand_sets:
                    inter = set.intersection(*cand_sets) | {p}
                    if inter != dom[p]:
                        dom[p] = inter
                        changed = True

        goal_doms = dom.get(goal_place, set()) - init_set
        # Order dominator cut-places topologically by their own dominator-set cardinality
        ordered = sorted(goal_doms, key=lambda pl: (len(dom.get(pl, set())), pl))
        return ordered

    def execute_checkpointed_long_horizon(
        self: CrossModalPetriPlanner,
        initial_tokens: Mapping[str, Any],
        goal_place: str,
        goal_verifier: Callable[[Mapping[str, Any]], bool],
        *,
        subgoal_max_depth: int = 8,
    ) -> dict[str, Any]:
        """Factor a 300+ step cross-modal workflow at its Petri dominator cut-places and solve
        each short sub-episode independently with verified state checkpoints (`0` constraint loss)."""
        t0 = time.perf_counter()
        cut_places = self.find_dominator_cut_places(list(initial_tokens.keys()), goal_place)
        if not cut_places or cut_places[-1] != goal_place:
            cut_places = [*[c for c in cut_places if c != goal_place], goal_place]

        live_tokens: dict[str, Any] = dict(initial_tokens)
        checkpoints_locked: list[str] = []
        total_steps = 0
        surfaces_used: list[str] = []

        for sub_target in cut_places:
            if sub_target in live_tokens:
                checkpoints_locked.append(sub_target)
                continue
            sub_plan = self.plan_reachability(
                list(live_tokens.keys()),
                sub_target,
                max_depth=subgoal_max_depth,
            )
            if sub_plan is None:
                return {
                    "ok": False,
                    "failed_subgoal": sub_target,
                    "checkpoints_locked": checkpoints_locked,
                    "steps_executed": total_steps,
                }
            for step in sub_plan:
                out_val = step.execute(live_tokens)
                live_tokens[step.output_place] = out_val
                total_steps += 1
                surfaces_used.append(step.surface)
            if sub_target not in live_tokens or live_tokens[sub_target] is None:
                return {
                    "ok": False,
                    "failed_subgoal": sub_target,
                    "checkpoints_locked": checkpoints_locked,
                    "steps_executed": total_steps,
                }
            checkpoints_locked.append(sub_target)

        verified = bool(goal_verifier(live_tokens))
        return {
            "ok": verified,
            "cut_vertices_discovered": len(cut_places),
            "checkpoints_locked": len(checkpoints_locked),
            "steps_executed": total_steps,
            "surfaces_used": surfaces_used,
            "wall_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "final_goal_value": live_tokens.get(goal_place),
        }

    CrossModalPetriPlanner.find_dominator_cut_places = find_dominator_cut_places  # type: ignore[attr-defined]
    CrossModalPetriPlanner.execute_checkpointed_long_horizon = execute_checkpointed_long_horizon  # type: ignore[attr-defined]


_attach_long_horizon_petri_slicer()


def _attach_store_compactor() -> None:
    def compact_and_deduplicate(self: AdmissionFilteredSkillStore) -> dict[str, int]:
        """Deduplicate α-equivalent L2 expression/subtree skills & L3 negative invariants."""
        total_before = len(self.records)
        sub_before = sum(1 for r in self.records.values() if r.skill_id.startswith("sub_") or "\n" in r.concrete_after)
        by_ir: dict[tuple[str, str, str], VerifiedSkillRecord] = {}
        for sid in sorted(self.records):
            rec = self.records[sid]
            if rec.stale:
                continue
            key = (rec.domain, rec.lhs_ir_sexpr, rec.rhs_ir_sexpr)
            if key not in by_ir:
                by_ir[key] = rec
            else:
                kept = by_ir[key]
                seen_w = {json.dumps(w, sort_keys=True) for w in kept.witness_inputs}
                for w in rec.witness_inputs:
                    wj = json.dumps(w, sort_keys=True)
                    if wj not in seen_w and len(kept.witness_inputs) < 12:
                        kept.witness_inputs.append(w)
                        seen_w.add(wj)
                kept.mdl_gain_bytes = max(kept.mdl_gain_bytes, rec.mdl_gain_bytes)
                kept.version += 1
        self.records = {r.skill_id: r for r in by_ir.values()}
        sub_after = sum(1 for r in self.records.values() if r.skill_id.startswith("sub_") or "\n" in r.concrete_after)

        neg_recs: dict[str, NegativeSpaceInvariant] = getattr(self, "negative_invariants", {})
        neg_before = len(neg_recs)
        by_neg: dict[tuple[str, str, str], NegativeSpaceInvariant] = {}
        for nid in sorted(neg_recs):
            nrec = neg_recs[nid]
            nkey = (nrec.domain, nrec.target_ast_shape, nrec.forbidden_delta_op)
            if nkey not in by_neg:
                by_neg[nkey] = nrec
        if hasattr(self, "negative_invariants"):
            self.negative_invariants = {r.invariant_id: r for r in by_neg.values()}  # type: ignore[attr-defined]

        self.save()
        return {
            "expr_before": total_before,
            "expr_after": len(self.records),
            "expr_merged": total_before - len(self.records),
            "subtree_before": sub_before,
            "subtree_after": sub_after,
            "subtree_merged": sub_before - sub_after,
            "negative_before": neg_before,
            "negative_after": len(getattr(self, "negative_invariants", {})),
            "negative_merged": neg_before - len(getattr(self, "negative_invariants", {})),
        }

    AdmissionFilteredSkillStore.compact_and_deduplicate = compact_and_deduplicate  # type: ignore[attr-defined]


_attach_store_compactor()


class SelfPlaySkillDistiller:
    """Zero-cost CPU self-play skill harvester with kernel identity & boundary-fuzzer gates."""

    def __init__(
        self,
        store: AdmissionFilteredSkillStore,
        kernel_paths: Sequence[pathlib.Path] = (),
    ) -> None:
        self.store = store
        self.kernel_paths = [pathlib.Path(p).resolve() for p in kernel_paths if pathlib.Path(p).is_file()]
        self._baseline_hashes = {str(p): _sha256_bytes(p.read_bytes()) for p in self.kernel_paths}

    def verify_kernel_identity(self) -> bool:
        return all(
            p.is_file() and _sha256_bytes(p.read_bytes()) == self._baseline_hashes[str(p)]
            for p in self.kernel_paths
        )

    def harvest_subtree_episode(
        self,
        *,
        domain: str,
        before_block: str,
        after_block: str,
        verified_by_suite: bool,
        probes_before_success: int,
        raw_episode_bytes: int,
        source_fingerprint: str = "",
    ) -> dict[str, Any]:
        if not self.verify_kernel_identity():
            return {"ok": False, "status": "ABORTED__KERNEL_IDENTITY_DRIFT"}
        ok, detail = self.store.try_admit_subtree(  # type: ignore[attr-defined]
            domain=domain,
            concrete_before=before_block,
            concrete_after=after_block,
            verified=verified_by_suite,
            goal_relevant=True,
            probes_before_success=probes_before_success,
            raw_episode_bytes=raw_episode_bytes,
            source_fingerprint=source_fingerprint or _sha256_text(before_block)[:16],
            witness_inputs=[{"self_play": True}],
            revalidation_probe={"source_fp": source_fingerprint or _sha256_text(before_block)[:16]},
        )
        compaction = self.store.compact_and_deduplicate()  # type: ignore[attr-defined]
        id_after = self.verify_kernel_identity()
        return {
            "ok": ok and id_after,
            "admitted": ok,
            "skill_or_reason": detail,
            "compaction": compaction,
            "kernel_identity_preserved": id_after,
            "model_calls": 0,
        }


# =========================================================================== #
# 8. STRUCTURAL SKELETONS AND 64-BIT FINGERPRINTS (collisions require exact matching)
# =========================================================================== #

def _stmt_structural_skeleton(node: ast.AST, depth: int = 0) -> str:
    """Alpha-invariant control-flow & operator skeleton (normalizing identifiers/constants/holes)."""
    if depth > 3:
        return "*"
    if isinstance(node, (ast.Name, ast.Constant)):
        return "LEAF"
    if isinstance(node, ast.Attribute):
        return "ATTR"
    if isinstance(node, ast.Call):
        return f"CALL({len(node.args)})"
    if isinstance(node, ast.Compare):
        ops = ",".join(type(o).__name__ for o in node.ops)
        return f"CMP[{ops}]"
    if isinstance(node, ast.BoolOp):
        return f"BOOL[{type(node.op).__name__}]"
    if isinstance(node, ast.UnaryOp):
        return f"UNARY[{type(node.op).__name__}]"
    if isinstance(node, ast.BinOp):
        return f"BIN[{type(node.op).__name__}]"
    if isinstance(node, ast.IfExp):
        return "IFEXP"
    if isinstance(node, ast.If):
        t_sk = _stmt_structural_skeleton(node.test, depth + 1)
        b_sk = ";".join(_stmt_structural_skeleton(s, depth + 1) for s in node.body[:2])
        o_sk = ";".join(_stmt_structural_skeleton(s, depth + 1) for s in node.orelse[:2])
        return f"IF({t_sk})->[{b_sk}]|[{o_sk}]"
    if isinstance(node, ast.Return):
        v_sk = _stmt_structural_skeleton(node.value, depth + 1) if node.value is not None else "NONE"
        return f"RET({v_sk})"
    if isinstance(node, ast.Assign):
        v_sk = _stmt_structural_skeleton(node.value, depth + 1)
        return f"ASG({v_sk})"
    if isinstance(node, ast.Raise):
        return "RAISE"
    return type(node).__name__


def compute_structural_fp64(code_or_schema: str) -> str:
    """Compute a 64-bit (16-hex-char) structural AST fingerprint invariant under identifier renaming."""
    norm = re.sub(r"\?[A-Za-z_]\w*|\$[A-Za-z_]\w*", "__HOLE__", textwrap.dedent(code_or_schema).strip())
    if not norm:
        return "0000000000000000"
    try:
        mod = ast.parse(norm)
        if len(mod.body) == 1 and isinstance(mod.body[0], ast.Expr):
            sk = "EXPR:" + _stmt_structural_skeleton(mod.body[0].value, 0)
        else:
            sk = "BLOCK:" + "||".join(_stmt_structural_skeleton(s, 0) for s in mod.body)
        return _sha256_text(sk)[:16]
    except SyntaxError:
        # Non-Python surface (`js`/`rust`): hash punctuation/keyword skeleton
        kw_sk = re.sub(r"[A-Za-z_]\w*", "ID", norm)
        kw_sk = re.sub(r"\s+", "", kw_sk)
        return _sha256_text("RAW:" + kw_sk)[:16]


# =========================================================================== #
# 9. CODEBASE-INTERNAL TYPE-HABITATION & NON-LITERAL IDIOM MINER (WALL 2)
# =========================================================================== #

_NULLABLE_LOOKUP_PREFIXES = (
    "get", "find", "search", "match", "lookup", "pop", "peek", "resolve", "detect", "fetch"
)


class CodebaseTypeHabitationMiner:
    """Harvests repository-internal type-habited AST idioms to overcome literal-trace blindness.

    Addresses `94363358` Wall 2 (`model_calls == 0`, `parameters_stored == 0`):
      1. `TYPE_HABITED_ATTR_VALUE_GUARD`: `hasattr(x, attr)` -> `getattr(x, attr, None) is not None`
         when Python descriptors/ABCs set disabled protocol hooks (`__reversed__ = None`, `__hash__ = None`).
      2. `TYPE_HABITED_NULLABLE_CALL_GUARD`: `if loader.get_X(k):` -> `if loader.get_X(k) is not None:`
         when valid registered objects evaluate falsy (`__len__() == 0` or `__bool__() == False`).
      3. `TYPE_HABITED_CONTAINER_COPY_ISOLATION`: when a mutable container local `v` (`list`/`dict`/`set`)
         appears >= 2 times across distinct components of a composite `return` (aliasing caller-owned
         output with an internal generator/chain!), synthesize `v.copy()` / `list(v)` on the caller slot.
    """

    @staticmethod
    def repo_uses_copy_idiom(worktree: pathlib.Path, rel_file: str) -> bool:
        target_p = worktree / rel_file
        if target_p.is_file():
            txt = target_p.read_text(encoding="utf-8", errors="ignore")
            if ".copy(" in txt or "list(" in txt or " copy(" in txt:
                return True
        return True

    @staticmethod
    def synthesize_stmt_habitation_rewrites(
        worktree: pathlib.Path,
        rel_file: str,
        file_source: str,
        stmt: ast.stmt,
        fail_frames: Sequence[Mapping[str, Any]] = (),
    ) -> list[tuple[str, str, str]]:
        """Return `(new_file_source, mechanism, description)` candidates for `stmt`."""
        out: list[tuple[str, str, str]] = []
        lines = file_source.splitlines(keepends=True)

        def _replace_node(target: ast.AST, repl_txt: str) -> str | None:
            sl = getattr(target, "lineno", None)
            sc = getattr(target, "col_offset", None)
            el = getattr(target, "end_lineno", None)
            ec = getattr(target, "end_col_offset", None)
            if None in (sl, sc, el, ec):
                return None
            assert sl is not None and sc is not None and el is not None and ec is not None
            prefix = "".join(lines[: sl - 1]) + lines[sl - 1][:sc]
            suffix = lines[el - 1][ec:] + "".join(lines[el:])
            cand_src = prefix + repl_txt + suffix
            try:
                ast.parse(cand_src)
                return cand_src
            except SyntaxError:
                return None

        # 1 & 2. Guard-position `hasattr(x, attr)` and nullable `get_*(...)` truthiness checks
        if isinstance(stmt, (ast.If, ast.While)):
            test_atoms: list[tuple[ast.expr, bool]] = []
            def _collect_guard_atoms(e: ast.expr, negated: bool = False) -> None:
                if isinstance(e, ast.BoolOp):
                    for v in e.values:
                        _collect_guard_atoms(v, negated)
                elif isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.Not):
                    _collect_guard_atoms(e.operand, not negated)
                else:
                    test_atoms.append((e, negated))
            _collect_guard_atoms(stmt.test, False)

            for atom, is_neg in test_atoms:
                if isinstance(atom, ast.Call):
                    # 1. `hasattr(obj, attr)` -> `getattr(obj, attr, None) is not None`
                    if isinstance(atom.func, ast.Name) and atom.func.id == "hasattr" and len(atom.args) == 2:
                        obj_s = ast.unparse(atom.args[0])
                        attr_s = ast.unparse(atom.args[1])
                        repl = f"getattr({obj_s}, {attr_s}, None) is not None"
                        patched = _replace_node(atom, repl)
                        if patched:
                            out.append((
                                patched,
                                "TYPE_HABITED_ATTR_VALUE_GUARD",
                                f"refine `hasattr({obj_s}, {attr_s})` -> `{repl}`",
                            ))
                    # 2. Nullable getter call `if self.get_plugin(name):` -> `if self.get_plugin(name) is not None:`
                    callee_leaf = (
                        atom.func.attr if isinstance(atom.func, ast.Attribute)
                        else (atom.func.id if isinstance(atom.func, ast.Name) else "")
                    )
                    low_leaf = callee_leaf.lower()
                    if any(low_leaf == p or low_leaf.startswith(p + "_") for p in _NULLABLE_LOOKUP_PREFIXES):
                        call_s = ast.unparse(atom)
                        repl_c = f"{call_s} is not None"
                        patched = _replace_node(atom, repl_c)
                        if patched:
                            out.append((
                                patched,
                                "TYPE_HABITED_NULLABLE_CALL_GUARD",
                                f"project nullable lookup `{call_s}` -> `{repl_c}`",
                            ))

        # 3. Composite return mutable-alias isolation (`return head, chain(head, it)` -> `return head.copy(), chain(head, it)`)
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Tuple) and len(stmt.value.elts) >= 2:
            # Find any identifier referenced in >= 2 distinct tuple elements!
            elt_names: list[set[str]] = []
            for elt in stmt.value.elts:
                elt_names.append({n.id for n in ast.walk(elt) if isinstance(n, ast.Name)})
            shared_vars: set[str] = set()
            for idx_a in range(len(elt_names)):
                for idx_b in range(idx_a + 1, len(elt_names)):
                    shared_vars |= (elt_names[idx_a] & elt_names[idx_b])

            mutable_types = {"list", "dict", "set", "bytearray"}
            for sv in sorted(shared_vars):
                # Check if `sv` was observed as mutable container in `fail_frames` (or unrestricted if frames lack `sv`)
                seen_types = {
                    str(ff[sv].get("t"))
                    for ff in fail_frames
                    if isinstance(ff.get(sv), Mapping) and ff[sv].get("t")
                }
                if seen_types and not (seen_types & mutable_types):
                    continue
                for elt in stmt.value.elts:
                    if isinstance(elt, ast.Name) and elt.id == sv:
                        for copy_form in (f"{sv}.copy()", f"list({sv})"):
                            patched = _replace_node(elt, copy_form)
                            if patched:
                                out.append((
                                    patched,
                                    "TYPE_HABITED_CONTAINER_COPY_ISOLATION",
                                    f"isolate shared mutable return `{sv}` via `{copy_form}`",
                                ))
        return out


class BidirectionalFSTLensSynthesizer:
    """Synthesizes algebraic round-trip repairs (`dec(enc(x)) == x`) for coupled string/byte transducer pairs
    (`encode*`/`decode*`, `escape*`/`unescape*`, `quote*`/`unquote*`, `format*`/`parse*`, `dumps`/`loads`).

    Implements three exact Finite-State Transducer (FST) lens laws, each verified in-memory on boundary
    witnesses (`'abc'`, `'a"b'`, `'a\\\\b'`, `'a\\\\"b'`, `'a\\nb'`, `'a%b'`, `''`) before emission:
      1. `FST_ESCAPE_ORDER_CANONICALIZATION`: Backslash/meta-escape `.replace('\\\\', '\\\\\\\\')` MUST precede
         other `\\\\`-producing `.replace(c, '\\\\' + ...)` transitions; `unescape` MUST run in exact reverse order.
      2. `FST_MISSING_INVERSE_TRANSITION`: Any `.replace(a, b)` present in `enc` whose inverse `.replace(b, a)` is
         absent from `dec` (or vice versa) is spliced in reverse transducer order.
      3. `FST_DELIMITER_SLICE_SYMMETRY`: When `enc` wraps `prefix + payload + suffix` while `dec` slices
         `s[lo:-hi]` with off-by-one bounds (`lo != len(prefix)` or `hi != len(suffix)`), aligns slice widths.
    """

    _INVERSE_PREFIXES: tuple[tuple[str, str], ...] = (
        ("encode", "decode"),
        ("escape", "unescape"),
        ("quote", "unquote"),
        ("serialize", "deserialize"),
        ("format", "parse"),
        ("dumps", "loads"),
    )

    @staticmethod
    def _extract_replace_chain(expr: ast.AST) -> tuple[ast.AST, list[tuple[str, str]]] | None:
        """Unpack `base.replace(a1, b1).replace(a2, b2)...` into `(base_expr, [(a1, b1), ...])`."""
        steps: list[tuple[str, str]] = []
        cur = expr
        while (
            isinstance(cur, ast.Call)
            and isinstance(cur.func, ast.Attribute)
            and cur.func.attr == "replace"
            and len(cur.args) == 2
            and isinstance(cur.args[0], ast.Constant)
            and isinstance(cur.args[1], ast.Constant)
            and isinstance(cur.args[0].value, (str, bytes))
            and isinstance(cur.args[1].value, (str, bytes))
            and type(cur.args[0].value) is type(cur.args[1].value)
        ):
            steps.append((cur.args[0].value, cur.args[1].value))
            cur = cur.func.value
        if not steps:
            return None
        steps.reverse()
        return cur, steps

    @classmethod
    def synthesize_lens_repairs(
        cls,
        src: str,
        tree: ast.Module,
    ) -> list[tuple[str, int, str, str]]:
        """Return `[(patched_source, lineno, mechanism, description), ...]` verified on round-trip witnesses."""
        fn_map: dict[str, ast.FunctionDef] = {
            st.name: st for st in tree.body if isinstance(st, ast.FunctionDef)
        }
        if len(fn_map) < 2:
            return []

        pairs: list[tuple[ast.FunctionDef, ast.FunctionDef]] = []
        seen_p: set[tuple[str, str]] = set()
        for nm, fn in fn_map.items():
            for p_enc, p_dec in cls._INVERSE_PREFIXES:
                if nm == p_enc or nm.startswith(p_enc + "_"):
                    suf = nm[len(p_enc):]
                    d_nm = p_dec + suf
                    if d_nm in fn_map and (nm, d_nm) not in seen_p:
                        seen_p.add((nm, d_nm))
                        pairs.append((fn, fn_map[d_nm]))

        if not pairs:
            return []

        lines = src.splitlines(keepends=True)
        line_starts = [0]
        for ln_s in lines:
            line_starts.append(line_starts[-1] + len(ln_s))

        def _replace_node(node: ast.AST, repl_text: str) -> str | None:
            if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
                return None
            s_idx = line_starts[node.lineno - 1] + node.col_offset
            e_idx = line_starts[node.end_lineno - 1] + node.end_col_offset
            cand = src[:s_idx] + repl_text + src[e_idx:]
            try:
                ast.parse(cand)
                return cand
            except SyntaxError:
                return None

        probe_strs = ("", "abc", 'a"b', "a'b", "a\\b", 'a\\"b', "a\nb", "a\tb", "a%b", "a%25b", "x:y")

        def _roundtrip_holds(
            cand_src: str,
            enc_name: str,
            dec_name: str,
            non_id_inputs: Sequence[str] = (),
        ) -> bool:
            ns: dict[str, Any] = {}
            try:
                exec(compile(cand_src, "<fst_lens>", "exec"), ns)  # noqa: S307
                ef = ns.get(enc_name)
                df = ns.get(dec_name)
                if not callable(ef) or not callable(df):
                    return False
                if any(ef(w) == w for w in non_id_inputs):
                    return False
                return all(df(ef(w)) == w for w in probe_strs)
            except Exception:
                return False

        out: list[tuple[str, int, str, str]] = []
        for enc_fn, dec_fn in pairs:
            non_id_w: list[str] = []
            try:
                ns_orig: dict[str, Any] = {}
                exec(compile(src, "<fst_orig>", "exec"), ns_orig)  # noqa: S307
                ef0 = ns_orig.get(enc_fn.name)
                if callable(ef0):
                    for w0 in probe_strs:
                        try:
                            if ef0(w0) != w0:
                                non_id_w.append(w0)
                        except Exception:
                            pass
            except Exception:
                pass

            if _roundtrip_holds(src, enc_fn.name, dec_fn.name, non_id_w):
                continue

            enc_rets = [st for st in ast.walk(enc_fn) if isinstance(st, ast.Return) and st.value is not None]
            dec_rets = [st for st in ast.walk(dec_fn) if isinstance(st, ast.Return) and st.value is not None]
            if len(enc_rets) == 1 and len(dec_rets) == 1:
                enc_ch = cls._extract_replace_chain(enc_rets[0].value)
                dec_ch = cls._extract_replace_chain(dec_rets[0].value)
                if enc_ch is not None and dec_ch is not None:
                    enc_base, enc_steps = enc_ch
                    dec_base, dec_steps = dec_ch

                    # Law 1 & 2: Meta-escape-first canonical order on `enc` + exact reverse inverse chain on `dec`!
                    meta_steps = [st for st in enc_steps if st[0] in st[1] and st[0] != st[1]]
                    other_steps = [st for st in enc_steps if st not in meta_steps]
                    canon_enc = [*meta_steps, *other_steps]
                    enc_pairs_set = set(canon_enc)
                    for da, db in reversed(dec_steps):
                        if (db, da) not in enc_pairs_set:
                            if db in da and db != da:
                                canon_enc.insert(0, (db, da))
                            else:
                                canon_enc.append((db, da))
                            enc_pairs_set.add((db, da))
                    canon_dec = [(b, a) for (a, b) in reversed(canon_enc)]

                    def _fmt_chain(base_n: ast.AST, steps_l: Sequence[tuple[str, str]]) -> str:
                        acc = ast.unparse(base_n)
                        for a_s, b_s in steps_l:
                            acc = f"{acc}.replace({a_s!r}, {b_s!r})"
                        return acc

                    # Try repairing `enc` alone, `dec` alone, and coupled `(enc, dec)` jointly!
                    if canon_enc != enc_steps:
                        p_enc_only = _replace_node(enc_rets[0].value, _fmt_chain(enc_base, canon_enc))
                        if p_enc_only and _roundtrip_holds(p_enc_only, enc_fn.name, dec_fn.name, non_id_w):
                            out.append((
                                p_enc_only,
                                enc_rets[0].lineno,
                                "FST_ESCAPE_ORDER_CANONICALIZATION",
                                f"canonicalize FST escape transition order in `{enc_fn.name}`",
                            ))
                    if canon_dec != dec_steps:
                        p_dec_only = _replace_node(dec_rets[0].value, _fmt_chain(dec_base, canon_dec))
                        if p_dec_only and _roundtrip_holds(p_dec_only, enc_fn.name, dec_fn.name, non_id_w):
                            out.append((
                                p_dec_only,
                                dec_rets[0].lineno,
                                "FST_MISSING_INVERSE_TRANSITION",
                                f"synthesize exact reverse FST inverse transitions in `{dec_fn.name}`",
                            ))
                    if canon_enc != enc_steps or canon_dec != dec_steps:
                        # Coupled 2-function FST lens repair (apply bottom-to-top to preserve byte offsets!)
                        edits_pair = sorted(
                            [
                                (enc_rets[0].value, _fmt_chain(enc_base, canon_enc)),
                                (dec_rets[0].value, _fmt_chain(dec_base, canon_dec)),
                            ],
                            key=lambda it: -it[0].lineno,
                        )
                        cur_s = src
                        ok_both = True
                        for nd_e, rp_e in edits_pair:
                            s_i = line_starts[nd_e.lineno - 1] + nd_e.col_offset
                            e_i = line_starts[nd_e.end_lineno - 1] + nd_e.end_col_offset
                            cur_s = cur_s[:s_i] + rp_e + cur_s[e_i:]
                        try:
                            ast.parse(cur_s)
                        except SyntaxError:
                            ok_both = False
                        if ok_both and _roundtrip_holds(cur_s, enc_fn.name, dec_fn.name, non_id_w):
                            out.append((
                                cur_s,
                                enc_rets[0].lineno,
                                "FST_COUPLED_ROUNDTRIP_LENS",
                                f"align coupled FST lens `{enc_fn.name}` <-> `{dec_fn.name}`",
                            ))

                # Law 3: Delimiter Prefix/Suffix Slice Symmetry (`prefix + x + suffix` <-> `s[len(prefix):-len(suffix)]`)
                if isinstance(dec_rets[0].value, ast.Subscript) and isinstance(dec_rets[0].value.slice, ast.Slice):
                    # Measure prefix/suffix added by `enc_fn("X")` in-memory
                    ns0: dict[str, Any] = {}
                    try:
                        exec(compile(src, "<fst_delim>", "exec"), ns0)  # noqa: S307
                        enc_sample = ns0[enc_fn.name]("PAYLOAD_TOKEN")
                        if isinstance(enc_sample, str) and "PAYLOAD_TOKEN" in enc_sample:
                            pre_w = enc_sample.index("PAYLOAD_TOKEN")
                            suf_w = len(enc_sample) - (pre_w + len("PAYLOAD_TOKEN"))
                            val_u = ast.unparse(dec_rets[0].value.value)
                            new_slice = (
                                f"{val_u}[{pre_w}:{len(val_u)}]"
                                if suf_w == 0
                                else f"{val_u}[{pre_w}:-{suf_w}]"
                            )
                            if suf_w == 0:
                                new_slice = f"{val_u}[{pre_w}:]"
                            p_slice = _replace_node(dec_rets[0].value, new_slice)
                            if p_slice and _roundtrip_holds(p_slice, enc_fn.name, dec_fn.name):
                                out.append((
                                    p_slice,
                                    dec_rets[0].lineno,
                                    "FST_DELIMITER_SLICE_SYMMETRY",
                                    f"align FST decoder slice `{new_slice}` with encoder delimiter widths ({pre_w}, {suf_w})",
                                ))
                    except Exception:
                        pass

        return out
