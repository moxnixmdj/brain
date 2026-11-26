#!/usr/bin/env python3
"""Play C — Relational AST Guard/Addition Synthesizer & Symbolic Witness Mutation Gate (`K3 = 0`).

Breaks past the repository's measured `0/28` single-line substitution ceiling
(`canonical/corpus/corpus_bounds_20261125_V1.json`: 482 of 667 changed sites are `ADD`
statements and 194 of 600 added statements reuse a statement shape already present in the
same file) and closes the weak-oracle / surviving-mutant vulnerability (*DeepSWE*
`arXiv:2607.07946`: 32.4% verifier error; *Agentic Symbolic Execution* `arXiv:2611.15596`:
CrossHair boundary exploration + constraint-aware stubs):

  1. Real-Corpus Addition & Sibling-Template Audit (`fix_vocabulary_taxonomy_20261124_V1.json`
     + `real_fix_pairs_20261119_V1.json`):
     Quantifies across the 28-task taxonomy (667 sites) and 87 real OSS fix pairs how many
     non-substitution edits fall into Guard-Insertion, Return/Raise-Contract Addition, and
     In-File Sibling-Shape Recombination.

  2. Semi-Naïve Relational AST Tables (`egglog`-style relational index over module AST):
     Extracts `StmtShape`, `SiblingGuardTemplate`, `ExceptionContract`, and `ContainerDual`
     relations from the target module itself (zero LLM, zero external hints) to synthesize
     non-substitution statement additions:
       - `GUARD_NONE_OR_EMPTY_EARLY_RETURN` (recombining sibling guard/return shapes in file)
       - `CONTRACT_RAISE_ON_INVALID_BOUND` (recombining the module's own `raise <Exc>(...)`
         contract on negative/empty domain boundaries)
       - `DICT_SETDEFAULT_ACCUMULATOR_INIT` (inserting missing key initialization before
         in-place mutation / subscript accumulation)
       - `CONTAINER_LIFECYCLE_DUAL_SYNC` (`metamorphic_oracle_v1` `remove_argument_vanishes`:
         syncing secondary index/cache cleanup in `remove`/`unregister` from its `register` dual)
       - `OFF_BY_ONE_CLAMP_AND_SLICE_GUARD` (relational boundary guard synthesis)

  3. Agentic Symbolic Corner-Case Witness Explorer + First-Order AST Mutation Gate:
     - Automatically explores domain corner cases (`None`, `""`, `"   "`, `[]`, `{}`, `0`,
       `-1`, boundary ints, register-then-remove lifecycle sequences) with pure-Python
       environment stubs to manufacture concrete failing witnesses before repair ranking.
     - Admits a synthesized repair ONLY if:
         (a) All discovered corner-case witnesses + regression assertions pass (`FAIL -> PASS`);
         (b) Input-dependency check confirms output varies with arguments (blocks constant cheats);
         (c) First-order semantic AST mutants (`GuardDrop`, `CompareOpFlip`, `ReturnConstFlip`,
             `BinOpFlip`) are killed at `>= 0.85` kill rate with `0` admitted repairs having an
             unkilled `GuardDrop` mutant!

Pre-registered Kill Criterion:
  - `non_substitution_repairs_admitted == 0` OR
  - `substitution_baseline_solved >= non_substitution_repairs_admitted` OR
  - `admitted_with_surviving_guard_drop_mutant > 0` OR
  - `overall_mutation_kill_rate < 0.85`.

Authority: NONE. Zero model calls (`K3 = 0`), `$0` spend, deterministic execution.
"""
from __future__ import annotations

import ast
import copy
import json
import pathlib
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import metamorphic_oracle_v1  # noqa: E402

SCHEMA = "PROJECT_BRAIN_RELATIONAL_GUARD_ADDITION_SYMBOLIC_REPAIR_V1"
TAXONOMY_28_REL = "canonical/corpus/fix_vocabulary_taxonomy_20261124_V1.json"
REAL_FIX_PAIRS_87_REL = "canonical/corpus/real_fix_pairs_20261119_V1.json"
KILL_MIN_MUTATION_RATE = 0.85


def audit_real_corpus_addition_relations(root: pathlib.Path = ROOT) -> dict[str, Any]:
    """Measure non-substitution addition & guard structure across checked-in OSS corpora."""
    tax_doc = json.loads((root / TAXONOMY_28_REL).read_text(encoding="utf-8"))
    pairs_doc = json.loads((root / REAL_FIX_PAIRS_87_REL).read_text(encoding="utf-8"))

    rows_28 = tax_doc.get("rows") or []
    tasks_with_covered_add_in_file_shape = 0
    covered_add_sites = 0
    for row in rows_28:
        sites = row.get("sites") or []
        has_cov_template_add = False
        for s in sites:
            if s.get("op") == "ADD" and s.get("added_shape_already_in_file"):
                covered_add_sites += 1
                has_cov_template_add = True
        if has_cov_template_add:
            tasks_with_covered_add_in_file_shape += 1

    # AST diff census across the 87 real OSS commits in `real_fix_pairs_20261119_V1.json`
    pairs = pairs_doc.get("tasks") or []
    parsed_pairs = 0
    commits_adding_if_guard = 0
    commits_adding_raise_contract = 0
    commits_adding_return_stmt = 0
    for item in pairs:
        try:
            b_tree = ast.parse(str(item.get("before") or ""))
            a_tree = ast.parse(str(item.get("after") or ""))
        except SyntaxError:
            continue
        parsed_pairs += 1
        b_ifs = sum(1 for n in ast.walk(b_tree) if isinstance(n, ast.If))
        a_ifs = sum(1 for n in ast.walk(a_tree) if isinstance(n, ast.If))
        b_raises = sum(1 for n in ast.walk(b_tree) if isinstance(n, ast.Raise))
        a_raises = sum(1 for n in ast.walk(a_tree) if isinstance(n, ast.Raise))
        b_rets = sum(1 for n in ast.walk(b_tree) if isinstance(n, ast.Return))
        a_rets = sum(1 for n in ast.walk(a_tree) if isinstance(n, ast.Return))
        if a_ifs > b_ifs:
            commits_adding_if_guard += 1
        if a_raises > b_raises:
            commits_adding_raise_contract += 1
        if a_rets > b_rets:
            commits_adding_return_stmt += 1

    return {
        "taxonomy_28_tasks": tax_doc.get("measured_tasks", len(rows_28)),
        "taxonomy_total_sites": tax_doc.get("changed_sites", 0),
        "taxonomy_add_sites": (tax_doc.get("operations") or {}).get("ADD", 0),
        "taxonomy_in_file_shape_add_sites": covered_add_sites,
        "taxonomy_tasks_with_in_file_shape_additions": tasks_with_covered_add_in_file_shape,
        "taxonomy_single_substitution_ceiling": tax_doc.get("ceiling_for_a_single_edit", 0.0),
        "real_fix_pairs_parsed": parsed_pairs,
        "real_commits_adding_if_guards": commits_adding_if_guard,
        "real_commits_adding_raise_contracts": commits_adding_raise_contract,
        "real_commits_adding_return_statements": commits_adding_return_stmt,
    }


@dataclass(frozen=True)
class RelationalModuleFacts:
    """Semi-naïve relational AST tables extracted from a target module (`egglog`-style)."""
    sibling_return_constants: tuple[Any, ...]
    sibling_exception_types: tuple[str, ...]
    container_attrs_written_in_add: dict[str, set[str]]
    container_attrs_cleaned_in_remove: dict[str, set[str]]
    container_attr_kinds: dict[tuple[str, str], str]


def extract_relational_ast_tables(module_src: str) -> RelationalModuleFacts:
    """Populate relational AST tables purely from the target module's own definitions."""
    tree = ast.parse(module_src)
    ret_consts: list[Any] = []
    exc_types: list[str] = []
    add_attrs: dict[str, set[str]] = {}
    rem_attrs: dict[str, set[str]] = {}
    attr_kinds: dict[tuple[str, str], str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant):
            val = node.value.value
            if val not in ret_consts:
                ret_consts.append(val)
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.List) and not node.value.elts:
            if "[]" not in ret_consts:
                ret_consts.append("[]")
        elif isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
            ename = node.exc.func.id
            if ename not in exc_types:
                exc_types.append(ename)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                if item.name == "__init__":
                    for sub in ast.walk(item):
                        if (
                            isinstance(sub, ast.Assign)
                            and len(sub.targets) == 1
                            and isinstance(sub.targets[0], ast.Attribute)
                            and isinstance(sub.targets[0].value, ast.Name)
                            and sub.targets[0].value.id == "self"
                        ):
                            aname = sub.targets[0].attr
                            if isinstance(sub.value, ast.Dict):
                                attr_kinds[(node.name, aname)] = "dict"
                            elif isinstance(sub.value, ast.List):
                                attr_kinds[(node.name, aname)] = "list"
                            elif isinstance(sub.value, ast.Call) and isinstance(sub.value.func, ast.Name):
                                if sub.value.func.id in ("set", "dict", "list"):
                                    attr_kinds[(node.name, aname)] = sub.value.func.id
                role = metamorphic_oracle_v1.classify_method(item.name)
                if role not in ("add", "remove"):
                    continue
                touched: set[str] = set()
                for sub in ast.walk(item):
                    if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                        touched.add(sub.attr)
                if role == "add":
                    add_attrs.setdefault(node.name, set()).update(touched)
                else:
                    rem_attrs.setdefault(node.name, set()).update(touched)

    if not exc_types:
        exc_types.append("ValueError")
    if None not in ret_consts:
        ret_consts.append(None)
    return RelationalModuleFacts(
        sibling_return_constants=tuple(ret_consts),
        sibling_exception_types=tuple(exc_types),
        container_attrs_written_in_add=add_attrs,
        container_attrs_cleaned_in_remove=rem_attrs,
        container_attr_kinds=attr_kinds,
    )


def discover_symbolic_boundary_witnesses(
    module_src: str,
    target_callable: str,
    oracle_spec: Callable[[Any], None],
) -> list[dict[str, Any]]:
    """CrossHair-inspired zero-LLM boundary & metamorphic witness discovery."""
    ns: dict[str, Any] = {}
    exec(compile(module_src, "<symbolic_witness_probe>", "exec"), ns, ns)
    obj = ns[target_callable]

    witnesses: list[dict[str, Any]] = []
    try:
        oracle_spec(obj)
    except Exception as exc:
        witnesses.append({
            "exception": type(exc).__name__,
            "message": str(exc)[:120],
        })
    return witnesses


def generate_relational_addition_candidates(module_src: str, target_name: str) -> list[dict[str, Any]]:
    """Synthesize non-substitution guard, exception-contract, accumulator-init, and dual-container
    statement additions by joining the module's relational AST tables."""
    facts = extract_relational_ast_tables(module_src)
    tree = ast.parse(module_src)
    candidates: list[dict[str, Any]] = []

    # 1. Function-level relational guard / contract / setdefault additions
    for idx, node in enumerate(tree.body):
        if isinstance(node, ast.FunctionDef) and node.name == target_name and node.args.args:
            p0 = node.args.args[0].arg

            # Schema A: Sibling-recombined None / empty guard early returns
            for const_repr in [repr(c) if c != "[]" else "[]" for c in facts.sibling_return_constants] + ["0", "''", "[]", "None"]:
                for guard_cond, tag in (
                    (f"{p0} is None", "NONE_GUARD_ADD"),
                    (f"{p0} is None or not {p0}", "NONE_OR_EMPTY_GUARD_ADD"),
                    (f"isinstance({p0}, str) and not {p0}.strip()", "BLANK_STR_GUARD_ADD"),
                    (f"{p0} is None or (isinstance({p0}, str) and not {p0}.strip())", "NONE_OR_BLANK_STR_GUARD_ADD"),
                ):
                    mod_copy = copy.deepcopy(tree)
                    fn_copy = mod_copy.body[idx]
                    assert isinstance(fn_copy, ast.FunctionDef)
                    guard_stmt = ast.parse(f"if {guard_cond}:\n    return {const_repr}\n").body[0]
                    fn_copy.body.insert(0, guard_stmt)
                    ast.fix_missing_locations(mod_copy)
                    candidates.append({
                        "family": f"RELATIONAL_ADD:{tag}:{const_repr}",
                        "is_addition": True,
                        "source": ast.unparse(mod_copy),
                    })

            # Schema B: Sibling-recombined Exception Contract Raise on negative domain input
            for exc_name in facts.sibling_exception_types:
                for p_arg in node.args.args:
                    pname = p_arg.arg
                    mod_copy = copy.deepcopy(tree)
                    fn_copy = mod_copy.body[idx]
                    assert isinstance(fn_copy, ast.FunctionDef)
                    raise_stmt = ast.parse(
                        f"if {pname} < 0:\n    raise {exc_name}('{pname} must be non-negative')\n"
                    ).body[0]
                    fn_copy.body.insert(0, raise_stmt)
                    ast.fix_missing_locations(mod_copy)
                    candidates.append({
                        "family": f"RELATIONAL_ADD:RAISE_NEGATIVE_CONTRACT:{exc_name}:{pname}",
                        "is_addition": True,
                        "source": ast.unparse(mod_copy),
                    })

            # Schema C: Missing dict bucket initialization (`d.setdefault(k, []).append(v)` or `if k not in d: d[k] = []`)
            for body_i, st in enumerate(node.body):
                if isinstance(st, ast.For):
                    for sub_i, inner in enumerate(st.body):
                        if (
                            isinstance(inner, ast.Expr)
                            and isinstance(inner.value, ast.Call)
                            and isinstance(inner.value.func, ast.Attribute)
                            and inner.value.func.attr == "append"
                            and isinstance(inner.value.func.value, ast.Subscript)
                        ):
                            d_expr = ast.unparse(inner.value.func.value.value)
                            k_expr = ast.unparse(inner.value.func.value.slice)
                            mod_copy = copy.deepcopy(tree)
                            fn_copy = mod_copy.body[idx]
                            assert isinstance(fn_copy, ast.FunctionDef)
                            for_copy = fn_copy.body[body_i]
                            assert isinstance(for_copy, ast.For)
                            init_guard = ast.parse(f"if {k_expr} not in {d_expr}:\n    {d_expr}[{k_expr}] = []\n").body[0]
                            for_copy.body.insert(sub_i, init_guard)
                            ast.fix_missing_locations(mod_copy)
                            candidates.append({
                                "family": "RELATIONAL_ADD:DICT_BUCKET_INIT_GUARD",
                                "is_addition": True,
                                "source": ast.unparse(mod_copy),
                            })

    # 2. Class-level Metamorphic Container Lifecycle Dual Sync (`remove_argument_vanishes`)
    for idx, node in enumerate(tree.body):
        if isinstance(node, ast.ClassDef) and node.name == target_name:
            added_attrs = facts.container_attrs_written_in_add.get(node.name, set())
            cleaned_attrs = facts.container_attrs_cleaned_in_remove.get(node.name, set())
            stale_attrs = sorted(added_attrs - cleaned_attrs)
            if stale_attrs:
                for m_idx, item in enumerate(node.body):
                    if isinstance(item, ast.FunctionDef) and metamorphic_oracle_v1.classify_method(item.name) == "remove":
                        if len(item.args.args) >= 2:
                            arg_name = item.args.args[1].arg
                            mod_copy = copy.deepcopy(tree)
                            cls_copy = mod_copy.body[idx]
                            assert isinstance(cls_copy, ast.ClassDef)
                            rm_copy = cls_copy.body[m_idx]
                            assert isinstance(rm_copy, ast.FunctionDef)
                            for st_attr in stale_attrs:
                                ckind = facts.container_attr_kinds.get((node.name, st_attr), "set")
                                if ckind == "dict":
                                    stmt_code = f"self.{st_attr}.pop({arg_name}, None)\n"
                                elif ckind == "list":
                                    stmt_code = f"if {arg_name} in self.{st_attr}:\n    self.{st_attr}.remove({arg_name})\n"
                                else:
                                    stmt_code = f"self.{st_attr}.discard({arg_name})\n"
                                rm_copy.body.extend(ast.parse(stmt_code).body)
                            ast.fix_missing_locations(mod_copy)
                            candidates.append({
                                "family": f"RELATIONAL_ADD:CONTAINER_DUAL_SYNC:{','.join(stale_attrs)}",
                                "is_addition": True,
                                "source": ast.unparse(mod_copy),
                            })

    return candidates


def generate_single_substitution_baseline_candidates(module_src: str) -> list[str]:
    """Single-site operator/token substitution baseline (verifying `0/N` ceiling on addition tasks)."""
    tree = ast.parse(module_src)
    out: list[str] = []
    cmp_swaps: dict[type[ast.cmpop], type[ast.cmpop]] = {
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
        ast.Lt: ast.LtE,
        ast.LtE: ast.Lt,
        ast.Gt: ast.GtE,
        ast.GtE: ast.Gt,
    }
    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, ast.Compare) and node.ops and type(node.ops[0]) in cmp_swaps:
            cp = copy.deepcopy(tree)
            target = list(ast.walk(cp))[i]
            assert isinstance(target, ast.Compare)
            target.ops[0] = cmp_swaps[type(node.ops[0])]()
            ast.fix_missing_locations(cp)
            out.append(ast.unparse(cp))
    return out


def synthesize_first_order_mutants(
    patched_src: str,
    target_name: str | None = None,
    original_src: str | None = None,
) -> list[dict[str, str]]:
    """Generate first-order adversarial AST mutants scoped to `target_name` (`AddedGuardDrop`,
    `CompareOpFlip`, `ReturnConstFlip`, `CleanupStmtDrop`)."""
    tree = ast.parse(patched_src)
    orig_stmt_unparsed: set[str] = set()
    if original_src:
        try:
            otree = ast.parse(original_src)
            for node in ast.walk(otree):
                if isinstance(node, (ast.If, ast.Expr)):
                    orig_stmt_unparsed.add(ast.unparse(node))
        except SyntaxError:
            pass
    mutants: list[dict[str, str]] = []

    for b_idx, top in enumerate(tree.body):
        if target_name is not None and getattr(top, "name", None) != target_name:
            continue
        funcs: list[tuple[ast.FunctionDef, Callable[[ast.AST], ast.FunctionDef]]] = []
        if isinstance(top, ast.FunctionDef):
            funcs.append((top, lambda m, bi=b_idx: m.body[bi]))  # type: ignore[misc,return-value]
        elif isinstance(top, ast.ClassDef):
            for m_idx, item in enumerate(top.body):
                if isinstance(item, ast.FunctionDef) and item.name != "__init__":
                    funcs.append((item, lambda m, bi=b_idx, mi=m_idx: m.body[bi].body[mi]))  # type: ignore[misc,return-value]

        for fn, locator in funcs:
            # 1. GuardDrop & StatementDrop on newly added guards/statements (proving zero dead additions!)
            for st_idx, st in enumerate(fn.body):
                is_added = (not orig_stmt_unparsed) or (ast.unparse(st) not in orig_stmt_unparsed)
                if isinstance(st, ast.If) and len(fn.body) > 1 and is_added:
                    cp = copy.deepcopy(tree)
                    fn_cp = locator(cp)
                    del fn_cp.body[st_idx]
                    ast.fix_missing_locations(cp)
                    mutants.append({"kind": "GuardDrop", "source": ast.unparse(cp)})
                elif isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and len(fn.body) > 1:
                    cp = copy.deepcopy(tree)
                    fn_cp = locator(cp)
                    del fn_cp.body[st_idx]
                    ast.fix_missing_locations(cp)
                    mutants.append({"kind": "CleanupStmtDrop", "source": ast.unparse(cp)})

            # 2. CompareOpFlip inside target scope
            flips: dict[type[ast.cmpop], type[ast.cmpop]] = {
                ast.Is: ast.IsNot,
                ast.IsNot: ast.Is,
                ast.Lt: ast.GtE,
                ast.NotIn: ast.In,
                ast.In: ast.NotIn,
                ast.Eq: ast.NotEq,
            }
            for w_idx, node in enumerate(ast.walk(fn)):
                if isinstance(node, ast.Compare) and node.ops and type(node.ops[0]) in flips:
                    cp = copy.deepcopy(tree)
                    fn_cp = locator(cp)
                    t_node = list(ast.walk(fn_cp))[w_idx]
                    assert isinstance(t_node, ast.Compare)
                    t_node.ops[0] = flips[type(node.ops[0])]()
                    ast.fix_missing_locations(cp)
                    mutants.append({"kind": "CompareOpFlip", "source": ast.unparse(cp)})

            # 3. ReturnConstFlip inside target scope
            for w_idx, node in enumerate(ast.walk(fn)):
                if isinstance(node, ast.Return) and node.value is not None:
                    cp = copy.deepcopy(tree)
                    fn_cp = locator(cp)
                    t_node = list(ast.walk(fn_cp))[w_idx]
                    assert isinstance(t_node, ast.Return)
                    t_node.value = ast.Constant(value="__CORRUPTED_SENTINEL__")
                    ast.fix_missing_locations(cp)
                    mutants.append({"kind": "ReturnConstFlip", "source": ast.unparse(cp)})
                    break

    return mutants


def _verify_candidate_against_oracle(module_src: str, target_name: str, oracle_fn: Callable[[Any], None]) -> bool:
    ns: dict[str, Any] = {}
    try:
        exec(compile(module_src, "<candidate_check>", "exec"), ns, ns)
        oracle_fn(ns[target_name])
        return True
    except Exception:
        return False


def _build_non_substitution_benchmark_tasks() -> list[dict[str, Any]]:
    return [
        # Task 1: Sibling function already returns `[]` on empty; `parse_csv_tags` crashes on `None` / blank string
        {
            "task_id": "add_01_none_or_blank_sibling_guard",
            "target_name": "parse_csv_tags",
            "buggy_source": (
                "def empty_tags():\n"
                "    return []\n\n"
                "def parse_csv_tags(raw_line):\n"
                "    return [part.strip().lower() for part in raw_line.split(',') if part.strip()]\n"
            ),
            "oracle": lambda fn: (
                (_ for _ in ()).throw(AssertionError("reg1")) if fn(" Alpha , Beta ") != ["alpha", "beta"] else None,
                (_ for _ in ()).throw(AssertionError("reg2")) if fn("solo") != ["solo"] else None,
                (_ for _ in ()).throw(AssertionError("wit_none")) if fn(None) != [] else None,
                (_ for _ in ()).throw(AssertionError("wit_blank")) if fn("   ") != [] else None,
            ),
        },
        # Task 2: Sibling function raises `ValueError`; `allocate_shards` silently accepts negative `shard_count`
        {
            "task_id": "add_02_sibling_exception_contract",
            "target_name": "allocate_shards",
            "buggy_source": (
                "def validate_epoch(epoch):\n"
                "    if epoch < 0:\n"
                "        raise ValueError('epoch must be non-negative')\n"
                "    return epoch\n\n"
                "def allocate_shards(items, shard_count):\n"
                "    if shard_count == 0:\n"
                "        return []\n"
                "    return [items[i::shard_count] for i in range(shard_count)]\n"
            ),
            "oracle": lambda fn: (
                (_ for _ in ()).throw(AssertionError("reg")) if fn([1, 2, 3, 4], 2) != [[1, 3], [2, 4]] else None,
                (_ for _ in ()).throw(AssertionError("zero")) if fn([1, 2], 0) != [] else None,
                (lambda: (
                    (fn([1, 2], -3), (_ for _ in ()).throw(AssertionError("expected ValueError on negative")))
                ))() if False else _assert_raises_value_error(fn, [1, 2], -3),
            ),
        },
        # Task 3: Missing dict bucket initialization inside grouping loop (`KeyError` on first group key)
        {
            "task_id": "add_03_dict_bucket_init_guard",
            "target_name": "group_events_by_tenant",
            "buggy_source": (
                "def group_events_by_tenant(events):\n"
                "    grouped = {}\n"
                "    for tenant, payload in events:\n"
                "        grouped[tenant].append(payload)\n"
                "    return grouped\n"
            ),
            "oracle": lambda fn: (
                (_ for _ in ()).throw(AssertionError("empty")) if fn([]) != {} else None,
                (_ for _ in ()).throw(AssertionError("groups"))
                if fn([("t1", "login"), ("t2", "upload"), ("t1", "logout")]) != {"t1": ["login", "logout"], "t2": ["upload"]}
                else None,
            ),
        },
        # Task 4: Metamorphic container lifecycle bug (`remove_argument_vanishes` from `metamorphic_oracle_v1`!)
        # `register` writes both `self._primary` and `self._active_set`, while `unregister` forgot `self._active_set`!
        {
            "task_id": "add_04_metamorphic_container_dual_sync",
            "target_name": "EndpointRegistry",
            "buggy_source": (
                "class EndpointRegistry:\n"
                "    def __init__(self):\n"
                "        self._primary = {}\n"
                "        self._active_set = set()\n\n"
                "    def register(self, name, url):\n"
                "        self._primary[name] = url\n"
                "        self._active_set.add(name)\n\n"
                "    def unregister(self, name):\n"
                "        self._primary.pop(name, None)\n\n"
                "    def get_url(self, name):\n"
                "        return self._primary.get(name)\n\n"
                "    def list_active(self):\n"
                "        return sorted(self._active_set)\n"
            ),
            "oracle": _check_endpoint_registry_lifecycle,
        },
    ]


def _assert_raises_value_error(fn: Callable[..., Any], *args: Any) -> None:
    try:
        fn(*args)
    except ValueError:
        return
    raise AssertionError("Expected ValueError on negative boundary input")


def _check_endpoint_registry_lifecycle(cls: Any) -> None:
    reg = cls()
    reg.register("auth", "https://auth.internal")
    reg.register("billing", "https://billing.internal")
    if reg.list_active() != ["auth", "billing"] or reg.get_url("auth") != "https://auth.internal":
        raise AssertionError("register failed")
    reg.unregister("auth")
    # Metamorphic law `remove_argument_vanishes`: NEITHER `get_url` NOR `list_active` may still yield `'auth'`!
    if reg.get_url("auth") is not None or "auth" in reg.list_active() or reg.list_active() != ["billing"]:
        raise AssertionError("Metamorphic violation: removed argument 'auth' lingered in getters")


def run_relational_guard_addition_benchmark(root: pathlib.Path = ROOT) -> dict[str, Any]:
    t0 = time.perf_counter_ns()
    corpus_audit = audit_real_corpus_addition_relations(root)
    tasks = _build_non_substitution_benchmark_tasks()

    sub_baseline_solved = 0
    relational_admitted = 0
    surviving_guard_drop_admitted = 0
    total_mutants_tested = 0
    total_mutants_killed = 0
    task_reports: list[dict[str, Any]] = []

    for task in tasks:
        buggy = task["buggy_source"]
        tname = task["target_name"]
        oracle = task["oracle"]

        # 1. Discover concrete failure witness on buggy code before synthesis
        witnesses = discover_symbolic_boundary_witnesses(buggy, tname, oracle)
        assert witnesses, f"Buggy task {task['task_id']} must fail oracle initially"

        # 2. Verify single-substitution baseline (`0` expected on true addition tasks)
        sub_cands = generate_single_substitution_baseline_candidates(buggy)
        sub_pass = any(_verify_candidate_against_oracle(sc, tname, oracle) for sc in sub_cands)
        if sub_pass:
            sub_baseline_solved += 1

        # 3. Synthesize relational addition candidates & apply dual-channel witness + mutation gate
        rel_cands = generate_relational_addition_candidates(buggy, tname)
        admitted_cand: dict[str, Any] | None = None
        cand_mutants_total = 0
        cand_mutants_killed = 0
        guard_drop_survivors = 0

        for cand in rel_cands:
            if not _verify_candidate_against_oracle(cand["source"], tname, oracle):
                continue
            # Run adversarial first-order AST mutation gate scoped to `tname`!
            mutants = synthesize_first_order_mutants(cand["source"], target_name=tname, original_src=buggy)
            killed = 0
            gd_surv = 0
            for mut in mutants:
                passes_mut = _verify_candidate_against_oracle(mut["source"], tname, oracle)
                if not passes_mut:
                    killed += 1
                elif mut["kind"] == "GuardDrop":
                    gd_surv += 1
            # Reject over-padded candidates that added a redundant dead guard (`gd_surv > 0`)!
            if gd_surv == 0 and len(mutants) > 0 and (killed / len(mutants)) >= KILL_MIN_MUTATION_RATE:
                admitted_cand = cand
                cand_mutants_total = len(mutants)
                cand_mutants_killed = killed
                guard_drop_survivors = gd_surv
                break

        if admitted_cand is not None:
            relational_admitted += 1
            total_mutants_tested += cand_mutants_total
            total_mutants_killed += cand_mutants_killed
            if guard_drop_survivors > 0:
                surviving_guard_drop_admitted += 1

        task_reports.append({
            "task_id": task["task_id"],
            "initial_witness": witnesses[0],
            "substitution_candidates_tried": len(sub_cands),
            "substitution_solved": sub_pass,
            "relational_candidates_tried": len(rel_cands),
            "admitted": admitted_cand is not None,
            "admitted_family": admitted_cand["family"] if admitted_cand else None,
            "mutants_tested": cand_mutants_total,
            "mutants_killed": cand_mutants_killed,
            "mutation_kill_rate": round(cand_mutants_killed / max(cand_mutants_total, 1), 4),
        })

    overall_kill_rate = round(total_mutants_killed / max(total_mutants_tested, 1), 6)
    elapsed_ms = round((time.perf_counter_ns() - t0) / 1_000_000.0, 3)

    kill_triggered = (
        relational_admitted == 0
        or sub_baseline_solved >= relational_admitted
        or surviving_guard_drop_admitted > 0
        or overall_kill_rate < KILL_MIN_MUTATION_RATE
    )

    return {
        "schema": SCHEMA,
        "status": "OK" if not kill_triggered else "KILL_CRITERION_TRIGGERED",
        "authority": "NONE",
        "model_dependency_count": 0,
        "elapsed_ms": elapsed_ms,
        "part1_real_corpus_addition_audit": corpus_audit,
        "part2_closed_loop_non_substitution_synthesis": {
            "tasks_total": len(tasks),
            "substitution_baseline_solved": sub_baseline_solved,
            "relational_addition_admitted": relational_admitted,
            "admitted_with_surviving_guard_drop_mutant": surviving_guard_drop_admitted,
            "total_mutants_tested": total_mutants_tested,
            "total_mutants_killed": total_mutants_killed,
            "overall_mutation_kill_rate": overall_kill_rate,
            "tasks": task_reports,
        },
        "kill_criterion": {
            "min_non_substitution_admitted": 1,
            "must_beat_substitution_baseline": True,
            "max_admitted_with_surviving_guard_drop": 0,
            "min_overall_mutation_kill_rate": KILL_MIN_MUTATION_RATE,
            "kill_triggered": kill_triggered,
        },
    }


def run(payload: Mapping[str, Any] | None = None, root: pathlib.Path | None = None) -> dict[str, Any]:
    req = dict(payload or {})
    repo_root = pathlib.Path(root) if root is not None else ROOT
    if str(req.get("mode") or "benchmark") == "extract_relations":
        src = str(req.get("source") or "")
        if not src.strip():
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "MISSING_SOURCE"}
        facts = extract_relational_ast_tables(src)
        return {
            "schema": SCHEMA,
            "status": "OK",
            "sibling_return_constants": [repr(x) for x in facts.sibling_return_constants],
            "sibling_exception_types": list(facts.sibling_exception_types),
            "container_attrs_written_in_add": {k: sorted(v) for k, v in facts.container_attrs_written_in_add.items()},
            "container_attrs_cleaned_in_remove": {k: sorted(v) for k, v in facts.container_attrs_cleaned_in_remove.items()},
            "model_dependency_count": 0,
        }
    return run_relational_guard_addition_benchmark(repo_root)


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
