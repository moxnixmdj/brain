#!/usr/bin/env python3
"""Software patch synthesis — source-level CEGIS(T) when `source_root` is provided,
and bounded architecture-search diagnostic (honestly reporting `patch_synthesized=False`)
when invoked without `source_root`.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import pathlib
from typing import Any
from canonical.runtime.swe_task_artifacts_v1 import fresh_output, publish_report

SCHEMA = "PROJECT_BRAIN_SOFTWARE_PATCH_CEGIS_Z3_V1"
CAPABILITY_ID = "software.patch.synthesize.cegis.z3.v1"
PROVIDES = ["software.patch.synthesize.cegis.proven", "software.architect.synthesize.cegis.verified"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked"]

REPO = pathlib.Path(__file__).resolve().parents[3]


def _safe_dir(root: pathlib.Path, raw: str) -> pathlib.Path:
    p = (root / raw).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_dir():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _extract_method_io_examples_from_test_source(
    test_source: str,
    class_name: str,
    method_name: str,
    context_ns: dict[str, Any] | None = None,
) -> tuple[list[tuple[tuple[Any, ...], Any]], list[Any]]:
    """Extract `((receiver_self, *args), expected)` pairs for `ClassDef` methods from test AST."""
    from canonical.runtime import swe_observational_program_synthesizer_v1 as obs_synth

    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return [], []
    base_ns: dict[str, Any] = {"__builtins__": obs_synth._SAFE_EVAL_BUILTINS}
    if context_ns:
        base_ns.update(context_ns)
    target_cls = base_ns.get(class_name)

    examples: list[tuple[tuple[Any, ...], Any]] = []
    constants: list[Any] = []
    for nd in ast.walk(tree):
        if isinstance(nd, ast.Constant) and isinstance(nd.value, (int, float, str)) and not isinstance(nd.value, bool):
            if isinstance(nd.value, str) and len(nd.value) <= 24:
                constants.append(nd.value)
            elif isinstance(nd.value, (int, float)):
                constants.append(nd.value)

    def _eval_in(expr: ast.AST, env: dict[str, Any]) -> tuple[bool, Any]:
        try:
            code = compile(ast.Expression(expr), "<method_test_example>", "eval")
            return True, eval(code, base_ns, env)  # noqa: S307 - closed literal/class namespace
        except Exception:
            return False, None

    def _match_method_call(expr: ast.AST, env: dict[str, Any]) -> tuple[bool, tuple[Any, ...]]:
        if not isinstance(expr, ast.Call) or expr.keywords:
            return False, ()
        if not isinstance(expr.func, ast.Attribute) or expr.func.attr != method_name:
            return False, ()
        ok_r, recv_val = _eval_in(expr.func.value, env)
        if not ok_r:
            return False, ()
        if target_cls is not None and isinstance(target_cls, type) and not isinstance(recv_val, target_cls):
            return False, ()
        arg_vals: list[Any] = [recv_val]
        for a in expr.args:
            ok_a, av = _eval_in(a, env)
            if not ok_a:
                return False, ()
            arg_vals.append(av)
        return True, tuple(arg_vals)

    def _scan_stmts(stmts: list[ast.stmt], init_env: dict[str, Any]) -> None:
        local_env = dict(init_env)
        for st in stmts:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                ok_v, val = _eval_in(st.value, local_env)
                if ok_v:
                    local_env[st.targets[0].id] = val
                continue
            for node in ast.walk(st):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    mname = node.func.attr
                    if mname == "assertEqual" and len(node.args) >= 2:
                        ok_c, c_args = _match_method_call(node.args[0], local_env)
                        ok_e, exp_v = _eval_in(node.args[1], local_env)
                        if ok_c and ok_e:
                            examples.append((c_args, exp_v))
                            continue
                        ok_c2, c_args2 = _match_method_call(node.args[1], local_env)
                        ok_e2, exp_v2 = _eval_in(node.args[0], local_env)
                        if ok_c2 and ok_e2:
                            examples.append((c_args2, exp_v2))
                    elif mname in ("assertTrue", "assertFalse") and len(node.args) >= 1:
                        ok_c, c_args = _match_method_call(node.args[0], local_env)
                        if ok_c:
                            examples.append((c_args, mname == "assertTrue"))
                    elif mname == "assertIsNone" and len(node.args) >= 1:
                        ok_c, c_args = _match_method_call(node.args[0], local_env)
                        if ok_c:
                            examples.append((c_args, None))
                elif isinstance(node, ast.Assert):
                    t = node.test
                    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
                        ok_c, c_args = _match_method_call(t.left, local_env)
                        ok_e, exp_v = _eval_in(t.comparators[0], local_env)
                        if ok_c and ok_e:
                            examples.append((c_args, exp_v))
                    elif isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not):
                        ok_c, c_args = _match_method_call(t.operand, local_env)
                        if ok_c:
                            examples.append((c_args, False))
                    else:
                        ok_c, c_args = _match_method_call(t, local_env)
                        if ok_c:
                            examples.append((c_args, True))

    top_env: dict[str, Any] = {}
    for top in tree.body:
        if isinstance(top, ast.Assign) and len(top.targets) == 1 and isinstance(top.targets[0], ast.Name):
            ok_v, val = _eval_in(top.value, top_env)
            if ok_v:
                top_env[top.targets[0].id] = val
        elif isinstance(top, ast.FunctionDef):
            _scan_stmts(top.body, top_env)
        elif isinstance(top, ast.ClassDef):
            for sub in top.body:
                if isinstance(sub, ast.FunctionDef):
                    _scan_stmts(sub.body, top_env)
    _scan_stmts([s for s in tree.body if not isinstance(s, (ast.FunctionDef, ast.ClassDef))], {})

    dedup_consts: list[Any] = []
    seen_c: set[Any] = set()
    for c in constants:
        fk = obs_synth._freeze_val(c)
        if fk not in seen_c:
            seen_c.add(fk)
            dedup_consts.append(c)
    return examples, dedup_consts[:12]


def _synthesize_code_patch_cegis(repo: pathlib.Path, args: dict[str, Any]) -> dict[str, Any]:
    import sys as _sys
    from canonical.runtime import swe_observational_program_synthesizer_v1 as obs_synth
    from canonical.runtime.bound_capabilities import python_test_corpus_discovery_v1 as disc
    from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch_mod

    src_root = _safe_dir(repo, str(args["source_root"]))
    raw_tests = [str(x) for x in (args.get("test_paths") or []) if str(x).strip()]
    if raw_tests:
        test_files = [(repo / t).resolve() for t in raw_tests]
    else:
        try:
            test_files = disc.discover_test_files(src_root)
        except FileNotFoundError:
            sib = src_root.parent / "tests"
            test_files = disc.discover_test_files(sib) if sib.is_dir() else []
    if not test_files:
        raise RuntimeError("CEGIS_NO_TEST_FILES")

    argv = [str(x) for x in patch_mod.suite_argv(_sys.executable, *test_files)]
    timeout = float(args.get("timeout_s") or 30)
    env = patch_mod._source_env()
    # Include src_root and parent on PYTHONPATH
    extra_pp = f"{src_root}:{src_root.parent}"
    env["PYTHONPATH"] = f"{extra_pp}:{env.get('PYTHONPATH', '')}".rstrip(":")

    pre_run = patch_mod._run_tests(repo, argv, timeout, env)
    if pre_run.get("timed_out"):
        return {
            "mode": "code_cegis_observational_stun", "verified": False,
            "exact_over_declared_frontier": False,
            "pre_test_returncode": pre_run.get("returncode"),
            "failure_reason": "BASELINE_TIMEOUT",
        }
    combined_test_src = "\n\n".join(tf.read_text(encoding="utf-8", errors="replace") for tf in test_files if tf.is_file())

    py_sources = [
        p for p in sorted(src_root.rglob("*.py"))
        if "__pycache__" not in p.parts and not p.name.startswith("test_") and not p.name.endswith("_test.py")
    ]

    for src_file in py_sources:
        if src_file.is_symlink() or src_root not in src_file.resolve().parents:
            raise RuntimeError("CEGIS_SOURCE_OUTSIDE_DECLARED_ROOT")
        original_bytes = src_file.read_bytes()
        orig_text = original_bytes.decode("utf-8")
        try:
            tree = ast.parse(orig_text)
        except SyntaxError:
            continue
        lines = orig_text.splitlines(keepends=True)
        # Build safe context namespace of classes/constants in src_file for test constructor eval
        ctx_ns: dict[str, Any] = {"__builtins__": obs_synth._SAFE_EVAL_BUILTINS}
        for nd in tree.body:
            if isinstance(nd, (ast.ClassDef, ast.Assign)):
                try:
                    c_src = "".join(lines[nd.lineno - 1:nd.end_lineno])
                    exec(compile(c_src, str(src_file), "exec"), ctx_ns, ctx_ns)  # noqa: S102
                except Exception:
                    pass

        targets: list[tuple[str | None, ast.FunctionDef]] = []
        for nd in tree.body:
            if isinstance(nd, ast.FunctionDef):
                targets.append((None, nd))
            elif isinstance(nd, ast.ClassDef):
                for sub in nd.body:
                    if isinstance(sub, ast.FunctionDef) and not sub.name.startswith("__"):
                        targets.append((nd.name, sub))

        for cls_name, nd in targets:
            params = [a.arg for a in nd.args.args]
            if not params:
                continue
            if cls_name is None:
                exs, consts = obs_synth.extract_io_examples_from_test_source(combined_test_src, nd.name, ctx_ns)
            else:
                exs, consts = _extract_method_io_examples_from_test_source(
                    combined_test_src, cls_name, nd.name, ctx_ns
                )
            if not exs:
                continue
            synth_body = obs_synth.synthesize_python_function_body(params, exs, consts)
            if not synth_body:
                continue
            def_indent = " " * int(nd.col_offset)
            body_indent = def_indent + "    "
            sig_src = ast.unparse(nd.args)
            indented = "\n".join(body_indent + ln for ln in synth_body.splitlines())
            new_fn_src = f"{def_indent}def {nd.name}({sig_src}):\n{indented}\n"
            cand_text = "".join(lines[:nd.lineno - 1]) + new_fn_src + "".join(lines[nd.end_lineno:])
            if cand_text == orig_text:
                continue
            try:
                ast.parse(cand_text)
            except SyntaxError:
                continue
            accepted = False
            try:
                src_file.write_text(cand_text, encoding="utf-8")
                # Equal-sized edits can otherwise reuse the baseline's timestamp
                # based pyc. Reuse the test-guided search's invalidation boundary.
                patch_mod._purge_source_bytecode(src_file)
                post_run = patch_mod._run_tests(repo, argv, timeout, env)
                accepted = (post_run.get("returncode") == 0
                            and not post_run.get("timed_out", False)
                            and src_file.read_bytes() == cand_text.encode("utf-8"))
            finally:
                # Trials never promote source. run() owns promotion and rolls
                # it back even if publishing the acceptance report fails.
                src_file.write_bytes(original_bytes)
                patch_mod._purge_source_bytecode(src_file)
            if accepted:
                rel_src = src_file.relative_to(repo).as_posix()
                udiff = "".join(
                    difflib.unified_diff(
                        orig_text.splitlines(keepends=True),
                        cand_text.splitlines(keepends=True),
                        fromfile=f"a/{rel_src}",
                        tofile=f"b/{rel_src}",
                    )
                )
                return {
                    "mode": "code_cegis_observational_stun",
                    "verified": True,
                    "exact_over_declared_frontier": True,
                    "source_path": rel_src,
                    "class_name": cls_name,
                    "function": f"{cls_name}.{nd.name}" if cls_name else nd.name,
                    "synthesized_body": synth_body,
                    "_candidate_bytes": cand_text.encode("utf-8"),
                    "examples_used": len(exs),
                    "pre_test_returncode": int(pre_run.get("returncode", 1)),
                    "post_test_returncode": 0,
                    "unified_diff": udiff,
                }
    return {
        "mode": "code_cegis_observational_stun",
        "verified": False,
        "exact_over_declared_frontier": False,
        "pre_test_returncode": int(pre_run.get("returncode", 1)),
    }


def _load_cegis():
    import canonical.runtime.counterexample_guided_causal_architecture_synthesizer_v1 as mod
    return mod


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    import sys as _sys

    repo = pathlib.Path(root).resolve()
    output = fresh_output(repo, args.get("output_path"), "canonical/tmp_patch_cegis.json")
    if args.get("source_root"):
        orig_sys_path = list(_sys.path)
        orig_sys_mods = dict(_sys.modules)
        try:
            result = _synthesize_code_patch_cegis(repo, args)
        finally:
            _sys.path[:] = orig_sys_path
            for mk in list(_sys.modules):
                if mk not in orig_sys_mods:
                    _sys.modules.pop(mk, None)
            _sys.modules.update(orig_sys_mods)
        is_verified = bool(result.get("verified"))
        candidate_bytes = result.pop("_candidate_bytes", None)
        artifact = {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "adapter": "software_patch_cegis_z3_v1",
            "provides": PROVIDES,
            "cegis_synthesis_executed": True,
            "result": result,
            "patch_synthesized": is_verified,
            "pass": is_verified,
            "verified": is_verified,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }
        if is_verified and args.get("apply_in_place"):
            from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch_mod
            source = repo / result["source_path"]
            original_bytes = source.read_bytes()
            try:
                source.write_bytes(candidate_bytes)
                patch_mod._purge_source_bytecode(source)
                return publish_report(repo, output, artifact)
            except BaseException:
                source.write_bytes(original_bytes)
                patch_mod._purge_source_bytecode(source)
                raise
        return publish_report(repo, output, artifact)

    cegis = _load_cegis()
    manifest = args.get("manifest") or {
        "components": [
            {"id": "python.fault.localize.dynamic.dataflow.v1", "kind": "MECHANISM", "requires": ["python.source.file.available"], "provides": ["python.fault.localization.symbol_ranked"], "verified": True, "brain_owned": True, "donor_independent": True, "cost": {"wall_clock": 0.5, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
            {"id": "python.patch.search.test_guided.ast.v1", "kind": "MECHANISM", "requires": ["python.source.file.available"], "provides": ["python.patch.candidate.test_verified"], "verified": True, "brain_owned": True, "donor_independent": True, "cost": {"wall_clock": 0.6, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
            {"id": "evidence.oracle.concrete_execution.v1", "kind": "VERIFIER", "requires": ["python.source.file.available"], "provides": ["evidence.concrete_contract_violation"], "verified": True, "brain_owned": True, "donor_independent": True, "cost": {"wall_clock": 0.4, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
            {"id": "python.contract.check.crosshair.v1", "kind": "VERIFIER", "requires": ["python.source.file.available"], "provides": ["python.contract.verdict"], "verified": True, "brain_owned": True, "donor_independent": True, "cost": {"wall_clock": 1.0, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
        ],
        "counterexamples": args.get("counterexamples", []),
        "initial_facts": ["python.source.file.available", "python.test.corpus.available"],
        "target": {"required_effects": ["software.architect.synthesize.cegis.verified"], "forbidden_effects": [], "max_components": 12, "top_k": 3},
        "allow_candidate_components": False,
    }
    result = cegis.synthesize(manifest)
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "adapter": "software_patch_cegis_z3_v1", "result": result,
        "status": "OPEN__SOURCE_PATCH_SYNTHESIS_NOT_IMPLEMENTED",
        "classification": result.get("classification"),
        "architecture_search_completed": result.get("exact_over_declared_frontier") is True,
        "architecture_search_pass": result.get("pass") is True,
        "patch_synthesized": False, "pass": False, "verified": False,
        "verification_scope": "DECLARED_COMPONENT_FRONTIER_ONLY",
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    return publish_report(repo, output, artifact)
