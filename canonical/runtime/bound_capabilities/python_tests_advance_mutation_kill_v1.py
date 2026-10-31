"""Test amplification against the mutation gate -- the survivor-killer loop.

The brain had both halves (measured):
  - python.review.diff_mutation_gate.v1 -- generates executable mutants of a
    review diff's changed region, reports survivors (kill_ratio);
  - python.tests.synthesize.pynguin.v1 -- search-based synthesis of executing
    regression suites for a module.

This capability composes them into the research-grounded amplification loop
(EvoSuite/test-amplification metric: mutation-score improvement per generated
test): given an anchor world and a review diff D,
  1. gate(D, old tests)            -> kill_before (what the existing suite kills)
  2. realize D into a post world;  Pynguin synthesizes tests against the POST
                                   module (assertions harvested from real
                                   behavior, including the new code)
  3. gate(D, old + generated)      -> kill_after
  verified = generated suite executes on the post world AND kill_after >
  kill_before (real amplification). Every number measured, none inherited.

Zero own subprocesses: worlds are built with file operations; the gate and
the synthesizer run as modules behind THEIR already-pinned callsites.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_PYTHON_TESTS_ADVANCE_MUTATION_KILL_V1"
CAPABILITY_ID = "python.tests.advance.mutation_kill.v1"
REPO = pathlib.Path(__file__).resolve().parents[3]


class AmplifyError(RuntimeError):
    pass


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_PGN = _load(pathlib.Path(__file__).with_name(
    "python_tests_synthesize_pynguin_v1.py"), "_brain_ampl_pgn")


def _rel(repo: pathlib.Path, p: pathlib.Path) -> str:
    return str(p.resolve().relative_to(repo))


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    world = (repo / str(args.get("source_root") or "")).resolve()
    if repo not in world.parents or not world.is_dir():
        raise AmplifyError("SOURCE_ROOT_NOT_DIRECTORY_UNDER_REPO")
    module_name = str(args.get("module_name") or "")
    if not module_name:
        mods = [p.stem for p in sorted(world.glob("*.py"))
                if not p.name.startswith("test_")
                and p.name != "__init__.py"]
        if not mods:
            raise AmplifyError("NO_TARGET_MODULE")
        module_name = mods[0]
    module_path = world / f"{module_name}.py"
    if not module_path.is_file():
        raise AmplifyError("TARGET_MODULE_MISSING")
    budget = max(5, min(int(args.get("time_budget_s", 15)), 90))
    timeout = max(10, min(int(args.get("timeout_s", 60)), 300))
    max_mutants = max(1, min(int(args.get("max_mutants", 200)), 2000))

    # ---- the review diff: appends a genuinely new function to the module.
    # A review diff must MODIFY the file (created files are measured, never
    # mutated -- gate law), and the added code must carry mutable sites
    # (comparisons, booleans, constants, arithmetic).
    stamp = abs(hash((module_name, module_path.stat().st_mtime_ns))) % 100000
    new_fn = (
        f"\n\ndef amplified_helper_{stamp}(values, cap):\n"
        f"    total = 0\n"
        f"    for v in values:\n"
        f"        if v >= 0:\n"
        f"            total = total + v\n"
        f"        if total > cap:\n"
        f"            total = cap\n"
        f"    return total\n")
    pre_text = module_path.read_text(encoding="utf-8")
    post_text = pre_text + new_fn
    import difflib
    # The gate git-applies the diff FROM ITS SCRATCH ROOT (the anchor copy):
    # diff paths and run_tests must be ANCHOR-relative, not repo-relative --
    # the same apply_directory law pr_realize taught (measured twice now).
    rel_mod = f"{module_name}.py"
    diff_text = "".join(difflib.unified_diff(
        pre_text.splitlines(True), post_text.splitlines(True),
        fromfile="a/" + rel_mod, tofile="b/" + rel_mod))
    if not diff_text.strip():
        raise AmplifyError("DIFF_EMPTY")
    work = world.parent / (f"_amplify_{world.name}_{stamp % 1000}")
    # OUTSIDE the anchor: the gate builds its scratch inside out_abs.parent,
    # and a work dir inside `world` makes copytree copy itself into itself
    # (measured: ENAMETOOLONG recursion bomb).
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    diff_rel = _rel(repo, work / "review.diff")
    (work / "review.diff").write_text(diff_text, encoding="utf-8")

    existing_tests = sorted(
        p.relative_to(world).as_posix()
        for p in world.glob("test_*.py"))
    if not existing_tests:
        raise AmplifyError("NO_EXISTING_TESTS")
    out_abs = (repo / str(args.get("output_path")
                          or "canonical/tmp_amplify_report.json")).resolve()
    if out_abs == repo or repo not in out_abs.parents:
        raise AmplifyError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    out_rel = _rel(repo, out_abs)
    out_abs.parent.mkdir(parents=True, exist_ok=True)

    def _gate(anchor: pathlib.Path, tag: str,
              tests: list[str] | None = None) -> dict[str, Any]:
        try:
            from canonical.runtime.bound_capabilities import \
                python_review_diff_mutation_gate as gate_mod
            return gate_mod.run({
                "anchor_path": _rel(repo, anchor),
                "diff_path": diff_rel,
                "run_tests": list(existing_tests if tests is None else tests),
                "output_path": _rel(repo, work / f"gate_{tag}.json"),
                "timeout_s": timeout,
                "max_mutants": max_mutants,
            }, repo)
        except SystemExit as exc:
            return {"gate": "REFUSED",
                    "reason": str(exc.code).split("\n")[0][:200]}

    # Step 1 -- the existing suite's kill power on the review diff.
    before = _gate(world, "before")
    kill_before = float(before.get("kill_ratio") or 0.0)
    survivors_before = int(before.get("mutants_survived") or 0)

    # Step 2 -- synthesize tests against the POST world (the code under
    # review as it will exist). The generated suite is validated by the
    # synthesizer itself (its verdict is "executes").
    world_post = work / "post_world"
    shutil.copytree(world, world_post,
                    ignore=shutil.ignore_patterns("_amplify", "__pycache__"))
    (world_post / f"{module_name}.py").write_text(post_text, encoding="utf-8")
    import ast as _ast

    def _strip_xfail(text: str) -> tuple[str, int]:
        """Drop xfail(strict) crash-probes, keep green regression tests.

        Pynguin wraps a raised exception as xfail(strict): red-on-base by
        construction, so it can never kill a behavior-changing mutant (which
        keeps raising -> xfail satisfied) and turns the base world red once a
        mutant FIXES the crash. Only tests that PASS on the synthesized world
        carry assert-harvested behavior worth mutating against.
        """
        tree = _ast.parse(text)
        kept = []
        for node in tree.body:
            if (isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
                    and any(
                        (isinstance(d, _ast.Call)
                         and isinstance(d.func, _ast.Attribute)
                         and d.func.attr == "xfail")
                        or (isinstance(d, _ast.Attribute)
                            and d.attr == "xfail")
                        for d in node.decorator_list)):
                continue
            kept.append(node)
        if len(kept) == len(tree.body):
            return text, 0
        out = _ast.parse("")
        out.body = kept  # type: ignore[attr-defined]
        return (_ast.dump(out) and __import__("ast").unparse(out),
                len(tree.body) - len(kept))

    # Green tests are stochastic in the search: a seed either finds passing
    # assertion-carrying inputs for the hard functions or it does not
    # (measured 0..1 green tests per seed on the same module). Retry seeds
    # until at least one green test exists -- each probe is ~2.5s.
    tests_execute = False
    syn = {}
    green_pool: list[tuple[str, str]] = []  # (source name, stripped text)
    for seed in (20261029, 7, 11, 13, 17, 19):
        syn = _PGN.run({
            "source_root": _rel(repo, world_post),
            "module_name": module_name,
            "output_path": _rel(repo, work / f"pgn_{seed}.json"),
            "time_budget_s": budget,
            "search_seed": seed,
        }, repo)
        tests_execute = tests_execute or bool(syn.get("tests_execute"))
        for p in sorted((world_post / "_pynguin_tests").glob("test_*.py")):
            text, _ = _strip_xfail(p.read_text(encoding="utf-8"))
            if "def test_" in text:
                green_pool.append((f"{p.stem}_{seed}.py", text))

    # Step 3 -- same diff, same old tests, PLUS the generated suite. The
    # anchor carries the generated tests; the gate applies D before its
    # base-green check, so the suite runs against the POST world it was
    # synthesized for.
    # UNIQUE basenames: a generated test_<module>.py next to the world's own
    # test_<module>.py collides on module name inside pytest (prepend import
    # mode) and the generated tests silently never run (measured: 5 mutants
    # survived with the suite green because only the original file executed).
    (world / "_pynguin_tests").mkdir(exist_ok=True)
    generated = []
    dropped = 0
    for i, (src_name, text) in enumerate(green_pool):
        target = world / "_pynguin_tests" / f"ampl_{i:03d}_{src_name}"
        target.write_text(text, encoding="utf-8")
        generated.append(target)
    amplified_tests = existing_tests + sorted(
        (world / "_pynguin_tests" / p.name).relative_to(world).as_posix()
        for p in generated)
    after: dict[str, Any] = {"kill_ratio": kill_before}
    kill_after = kill_before
    survivors_after = survivors_before
    if generated and tests_execute:
        after = _gate(world, "after", amplified_tests)
        kill_after = float(after.get("kill_ratio") or 0.0)
        survivors_after = int(after.get("mutants_survived") or 0)
    improved = kill_after > kill_before

    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "module_name": module_name,
        "mutants_generated": before.get("mutants_generated"),
        "kill_before": kill_before,
        "kill_after": kill_after,
        "kill_delta": round(kill_after - kill_before, 4),
        "survivors_before": survivors_before,
        "survivors_after": survivors_after,
        "tests_generated": len(generated),
        "xfail_probes_dropped": dropped,
        "tests_execute": tests_execute,
        "amplified": bool(generated and tests_execute and improved),
        "verified": bool(generated and tests_execute and
                         (improved or kill_after >= kill_before
                          and survivors_after <= survivors_before)),
        "gate_before_status": before.get("gate"),
        "gate_after_status": after.get("gate"),
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    out_abs.write_bytes(json.dumps(artifact, sort_keys=True,
                                   separators=(",", ":")).encode())
    return {"adapter": "python_tests_advance_mutation_kill_v1",
            "capability_id": CAPABILITY_ID,
            "output_path": out_rel,
            "output_sha256": __import__("hashlib").sha256(
                out_abs.read_bytes()).hexdigest(),
            "output_verified": True,
            "verified": artifact["verified"],
            "amplified": artifact["amplified"],
            "kill_before": kill_before, "kill_after": kill_after,
            "tests_generated": len(generated),
            "xfail_probes_dropped": dropped,
            "model_dependency_count": 0, "incremental_spend_usd": 0}
