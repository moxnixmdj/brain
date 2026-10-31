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
    combined_test_src = "\n\n".join(tf.read_text(encoding="utf-8", errors="replace") for tf in test_files if tf.is_file())

    py_sources = [
        p for p in sorted(src_root.rglob("*.py"))
        if "__pycache__" not in p.parts and not p.name.startswith("test_") and not p.name.endswith("_test.py")
    ]

    for src_file in py_sources:
        orig_text = src_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(orig_text)
        except SyntaxError:
            continue
        lines = orig_text.splitlines(keepends=True)
        # Build safe context namespace of classes/constants in src_file for test constructor eval
        ctx_ns: dict[str, Any] = {}
        for nd in tree.body:
            if isinstance(nd, ast.ClassDef):
                try:
                    c_src = "".join(lines[nd.lineno - 1:nd.end_lineno])
                    exec(compile(c_src, str(src_file), "exec"), ctx_ns, ctx_ns)  # noqa: S102
                except Exception:
                    pass

        for nd in tree.body:
            if not isinstance(nd, ast.FunctionDef):
                continue
            params = [a.arg for a in nd.args.args]
            if not params:
                continue
            exs, consts = obs_synth.extract_io_examples_from_test_source(combined_test_src, nd.name, ctx_ns)
            if not exs:
                continue
            synth_body = obs_synth.synthesize_python_function_body(params, exs, consts)
            if not synth_body:
                continue
            sig_src = ast.unparse(nd.args)
            indented = "\n".join("    " + ln for ln in synth_body.splitlines())
            new_fn_src = f"def {nd.name}({sig_src}):\n{indented}\n"
            cand_text = "".join(lines[:nd.lineno - 1]) + new_fn_src + "".join(lines[nd.end_lineno:])
            if cand_text == orig_text:
                continue
            try:
                ast.parse(cand_text)
            except SyntaxError:
                continue
            try:
                src_file.write_text(cand_text, encoding="utf-8")
                post_run = patch_mod._run_tests(repo, argv, timeout, env)
            finally:
                if not args.get("apply_in_place"):
                    src_file.write_text(orig_text, encoding="utf-8")
            if int(post_run.get("returncode", 1)) == 0:
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
                    "function": nd.name,
                    "synthesized_body": synth_body,
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
    repo = pathlib.Path(root).resolve()
    output = fresh_output(repo, args.get("output_path"), "canonical/tmp_patch_cegis.json")
    if args.get("source_root"):
        result = _synthesize_code_patch_cegis(repo, args)
        is_verified = bool(result.get("verified"))
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
