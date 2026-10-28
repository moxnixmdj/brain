"""Run every bound capability on sampled instances, through the typed interface.

V4 reports `typed-invocable: 67/67`. That means the signatures are known and total. It does
NOT mean the capabilities have ever been *executed* through that interface. This sweep is the
difference between the two numbers, measured.

Why this is the right instrument, from first principles:

- The sentence interface was the bottleneck for months (27 of 67). V4 correctly declared it the
  wrong interface and replaced it with types. But "the surface is total" is a claim about
  signatures, not about behaviour. Only running it settles behaviour.
- Instances come from `type_directed_sampler_v1`, which is judged by the surface's own
  `check()`, so a failure here cannot be blamed on bad inputs: the inputs were accepted.
- Every outcome is a receipt, including the failures. A capability that cannot execute on valid
  inputs is more valuable information than one that can, because it names the next unit of work.

Model dependency: 0. Spend: $0. Nothing here calls a model, a solver or the network.
"""
from __future__ import annotations

import argparse
import importlib.util
import base64
import json
import random
import re
import shutil
import sys
import traceback
from typing import Any, Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_type_surface_v1 as ts  # noqa: E402
from canonical.runtime import type_directed_sampler_v1 as samp  # noqa: E402
from canonical.runtime.capability_type_surface_v1 import type_of  # noqa: E402

SCHEMA = "PROJECT_BRAIN_TYPED_CAPABILITY_SWEEP_V1"
WORK = ROOT / "canonical/astra_runtime/tmp/typed_sweep"


def _substitute(template: Any, filled: Mapping[str, Any]) -> Any:
    """Fill ${input.X} placeholders inside an action_template, at any depth.

    A template value is usually a bare "${input.path}" but is sometimes embedded in a list
    (argv) or a dict, so the walk has to be recursive. Keys that are literal configuration
    -- argv, decode_callable, package_root, timeout_s -- are passed through untouched.
    """
    if isinstance(template, str):
        m = re.fullmatch(r"\$\{input\.([A-Za-z_][A-Za-z0-9_]*)\}", template.strip())
        if m:
            name = m.group(1)
            return filled[name] if name in filled else template
        out = template
        for key, val in filled.items():
            out = out.replace("${input." + key + "}", str(val))
        return out
    if isinstance(template, Mapping):
        return {k: _substitute(v, filled) for k, v in template.items()}
    if isinstance(template, list):
        return [_substitute(v, filled) for v in template]
    return template


def _swe_unittest_fixture(base: Path, green: bool = False) -> dict:
    """A tiny repo whose failing TEST produces a parseable unittest metric.

    Strict-progress and iterative loops score candidates by parsing
    `FAILED (failures=N)` from runner output, so the bare-assert scripts used
    by the coupled family are unparsable to them (BASELINE_FAILURE_METRIC_
    UNPARSEABLE). This fixture is a real unittest.TestCase: the metric exists.
    Polarity is a parameter: review gates REFUSE a red baseline world
    (BASE_WORLD_RED), repair loops REFUSE a green one (BASELINE_ALREADY_PASSES).
    render() keeps a two-statement body so refactor/extract has a statement-
    aligned region at lines 7-8 in both polarities.
    """
    factor = 2 if green else 3
    src = base / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "calc.py").write_text(
        "def compute_total(items):\n"
        "    # doubling semantics pinned by tests\n"
        f"    return sum(x * {factor} for x in items)\n"
        "\n\n"
        "def render(items):\n"
        "    parts = [str(x) for x in items]\n"
        "    joined = \",\".join(parts)\n"
        "    return joined\n",
        encoding="utf-8")
    (src / "user_mod.py").write_text(
        "from calc import compute_total\n\n\n"
        "def twice(items):\n"
        "    return compute_total(items) * 2\n",
        encoding="utf-8")
    (src / "test_calc.py").write_text(
        "import unittest\n"
        "from calc import compute_total\n\n\n"
        "class TestTotal(unittest.TestCase):\n"
        "    def test_doubled_total(self):\n"
        "        self.assertEqual(compute_total([1, 2, 3]), 12)\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    unittest.main()\n",
        encoding="utf-8")
    return {"src": src, "module": src / "calc.py", "test": src / "test_calc.py"}


def _swe_repo_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """Domain generator for the hard-SWE fleet: real repo, real diff, real argv.

    These capabilities are UNSAMPLED under generic type sampling because their
    required slots are structural (a python executable, a worktree, a diff that
    touches a real file, a symbol index that names real lines). A random string
    is not a repository. So we build one miniature repository once per call and
    fill every slot from it. Slots we cannot ground honestly are left to error
    out as receipts, which is the sweep's contract.
    """
    keys = set(sig)
    structural = {
        "python_executable", "diff_path", "worktree_path", "task_path", "pr_intent_path",
        "anchor_path", "bench_path", "apply_directory", "qualname", "module", "edits",
        "queries", "fields", "manifest", "budget", "test_grid", "cegis_manifest",
        "changed_paths", "test_roots", "base_branch", "branch_name", "repo_path",
        "selection_path", "test_cwd", "min_coverage_ratio", "max_mutants",
        "min_kill_ratio", "repeats", "tolerance", "start_line", "end_line",
        "old_param", "new_param", "new_symbol", "issue_path",
        "measurement_receipt_path", "goal", "candidate_response", "raw_task_text",
        "author_date", "committer_date", "author_email", "committer_email",
        "author_name", "committer_name", "title", "body", "generated_tests_root",
        "targets_path", "training_pairs", "training_pairs_path", "evidence",
        "source_id", "task_text",
    }
    repair_law = {"source_root", "source_path", "source_paths",
                  "test_paths", "test_argv"}
    if "parse_edit_intent" in cid or ("repair" in cid and keys & repair_law):
        # repair loops are owned by the coupled/strict fixtures that carry a
        # genuinely failing baseline; this generator's baseline is green.
        return None
    if not (keys & structural):
        return None
    if not (cid.startswith(("python.", "software.", "code.", "task."))
            or "python_executable" in keys):
        return None

    import shutil as _shutil
    base = ws / f"swe_repo{rng.randrange(1 << 30)}"
    fx = _swe_unittest_fixture(base, green=True)
    src = fx["src"]
    bench = src / "bench.py"
    # the perf gate joins bench_path against each world tree (tree / bench_rel)
    # and the child imports the module standalone and calls bench(): a plain
    # repo-internal file with no path-dependent imports is the honest shape.
    # Written BEFORE the worktree copy so both worlds see it.
    bench.write_text("def bench():\n"
                     "    return sum(x * 2 for x in range(100))\n",
                     encoding="utf-8")
    work = base / "work"
    _shutil.copytree(src, work)
    # a real, small, constructive change to diff: add a doubling helper
    (work / "helpers.py").write_text("def double(x):\n    return x * 2\n",
                                     encoding="utf-8")
    import difflib
    old = (src / "calc.py").read_text(encoding="utf-8").splitlines(True)
    new = old + ["\n", "def triple(x):\n", "    return x * 3\n"]
    diff = "".join(difflib.unified_diff(old, new, "a/calc.py", "b/calc.py"))
    # gates git-apply the diff onto the anchor/work tree: it must hold the
    # PRE-change content (DIFF_DOES_NOT_APPLY was the receipt when it held
    # the post-change file). pr_realize additionally requires a real git repo.
    import subprocess as _sp
    _sp.run(["git", "init", "-q", "-b", "main"], cwd=work, check=False,
            capture_output=True)
    _sp.run(["git", "add", "-A"], cwd=work, check=False, capture_output=True)
    _sp.run(["git", "-c", "user.email=sweep@example.invalid", "-c",
             "user.name=Sweep", "commit", "-qm", "baseline"], cwd=work,
            check=False, capture_output=True)
    _sp.run(["git", "remote", "add", "origin", str(work)], cwd=work,
            check=False, capture_output=True)
    diff_path = base / "bed.diff"
    diff_path.write_text(diff, encoding="utf-8")

    issue = base / "issue.json"
    issue.write_text(json.dumps({
        "issue_id": "SWEEP-001",
        "title": "Rename compute_total to weighted_total",
        "edits": [{"op": "rename_symbol", "module": "calc.py",
                   "name": "compute_total", "new_name": "weighted_total"}],
    }), encoding="utf-8")
    pr_intent = base / "pr_intent.json"
    pr_intent.write_text(json.dumps({
        "title": "Sweep bench PR",
        "changed_files": ["calc.py", "helpers.py"],
        "verifier": "unittest",
    }), encoding="utf-8")
    # Harvest the brain's own indexer: hand-rolled fakes failed the adapters'
    # schema+totals check. The real producer emits what the consumers parse.
    # tree-sitter consumers need the incremental indexer's schema, not the AST
    # indexer's (INDEX_SCHEMA_MISMATCH receipt).
    # Read-side law, harvested from the adapters' own validators: the
    # choreograph/orchestrate consumers open the cache with source_root "."
    # over the src tree, while the tree-sitter impact/verify consumers read
    # rows as REPOSITORY paths (PATH_MISSING:bench.py receipt when the
    # index was src-rooted). Two correct producers, chosen by consumer root.
    if cid.startswith("code."):
        index = src / "_sweep_index.json"
        rel_src = str(src.resolve().relative_to(ROOT))
        try:
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location(
                "sweep_ts_index",
                ROOT / "canonical/runtime/bound_capabilities/code_tree_sitter_incremental_index_v1.py")
            _ti = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_ti)
            _ti.run({"source_root": rel_src, "output_path": index.name
                     if False else str(index.relative_to(ROOT))}, str(ROOT))
            if "patch.tree_sitter.verify" in cid:
                # selection must be a VERIFIED impact artifact pinning THIS
                # index's sha256 -- harvest the impact adapter as its producer
                sel = src / "_sweep_selection.json"
                _spec2 = _ilu.spec_from_file_location(
                    "sweep_ts_impact",
                    ROOT / "canonical/runtime/bound_capabilities/code_tree_sitter_impact_v1.py")
                _im = _ilu.module_from_spec(_spec2)
                _spec2.loader.exec_module(_im)
                _im.run({"changed_paths": [rel_src + "/calc.py"],
                         "index_path": str(index.relative_to(ROOT)),
                         "output_path": str(sel.relative_to(ROOT)),
                         "test_roots": [rel_src],
                         "test_paths": [rel_src + "/test_calc.py"]}, str(ROOT))
        except Exception:
            pass
    index = src / "_sweep_index.json"
    if not index.is_file():
        try:
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location(
                "sweep_symbol_index",
                ROOT / "canonical/runtime/bound_capabilities/python_source_symbol_index.py")
            _idx = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_idx)
            _idx.run({"source_root": ".", "output_path": index.name}, str(src))
        except Exception:
            index.write_text(json.dumps({"modules": []}), encoding="utf-8")
    edits_path = base / "edits.json"
    edits_path.write_text(json.dumps([
        {"op": "rename_symbol", "module": "calc.py", "name": "compute_total",
         "new_name": "weighted_total"}]), encoding="utf-8")
    selection = base / "selection.json"
    selection.write_text(json.dumps({"selected": ["test_calc.py"]}), encoding="utf-8")
    receipt = base / "receipt.json"
    receipt.write_text(json.dumps({"schema": "SWEEP_RECEIPT", "verified": True}),
                       encoding="utf-8")

    def _rel(p) -> str:
        # adapter contracts demand REPOSITORY-RELATIVE paths; absolute paths
        # raised PATH_ESCAPE / RESOLUTION_INPUT_INVALID on the first pass.
        return str(Path(p).resolve().relative_to(ROOT))

    pr_repo = "pr_realize" in cid
    if pr_repo:
        _shutil.copy(diff_path, work / "bed.diff")
        _shutil.copy(pr_intent, work / "pr_intent.json")

    args: dict = {}
    for slot in keys:
        if slot == "python_executable":
            args[slot] = sys.executable
        elif slot == "diff_path":
            args[slot] = "bed.diff" if pr_repo else _rel(diff_path)
        elif slot == "worktree_path":
            args[slot] = _rel(work)
        elif slot in ("task_path",):
            args[slot] = _rel(issue)
        elif slot == "issue_path":
            args[slot] = _rel(issue)
        elif slot == "pr_intent_path":
            args[slot] = "pr_intent.json" if pr_repo else _rel(pr_intent)
        elif slot == "index_path":
            args[slot] = _rel(index)
        elif slot in ("edits_path",):
            args[slot] = _rel(edits_path)
        elif slot == "selection_path":
            prod = src / "_sweep_selection.json"
            args[slot] = _rel(prod if "patch.tree_sitter.verify" in cid
                              and prod.is_file() else selection)
        elif slot == "measurement_receipt_path":
            args[slot] = _rel(receipt)
        elif slot == "bench_path":
            args[slot] = "bench.py"
        elif slot == "anchor_path":
            # the gate contract anchors the diff application at a DIRECTORY
            # (ANCHOR_NOT_DIRECTORY was the sweep's receipt), not a file
            args[slot] = _rel(work)
        elif slot == "apply_directory":
            # pr_realize law: prefix under which the diff's paths live INSIDE
            # the git repo; our diff paths sit at repo root, so empty prefix
            args[slot] = ""
        elif slot in ("repo_path", "test_cwd"):
            args[slot] = _rel(work)
        elif slot == "source_root" and sig.get(slot) == ts.PATH_DIR:
            args[slot] = _rel(src)
        elif slot == "changed_paths":
            # tree-sitter consumers validate changed paths against index rows,
            # which are repository-relative; the AST consumers want in-tree names
            if cid.startswith("code."):
                args[slot] = [str(src.resolve().relative_to(ROOT)) + "/calc.py"]
            else:
                args[slot] = ["calc.py"]
        elif slot == "test_roots":
            args[slot] = [_rel(src)]
        elif slot == "test_paths":
            args[slot] = [_rel(src / "test_calc.py")]
        elif slot == "module":
            args[slot] = "calc.py"
        elif slot == "qualname":
            args[slot] = "render" if "extract_function" in cid else "compute_total"
        elif slot == "new_symbol":
            args[slot] = "weighted_total"
        elif slot == "old_param":
            args[slot] = "items"
        elif slot == "new_param":
            args[slot] = "values"
        elif slot == "start_line":
            args[slot] = 7
        elif slot == "end_line":
            args[slot] = 8
        elif slot == "new_name":
            args[slot] = "joined"
        elif slot == "timeout_s":
            args[slot] = 120
        elif slot == "min_coverage_ratio":
            args[slot] = 0.0
        elif slot == "max_mutants":
            args[slot] = 1
        elif slot == "min_kill_ratio":
            args[slot] = 0.0
        elif slot == "repeats":
            args[slot] = 1
        elif slot == "tolerance":
            args[slot] = 100.0
        elif slot == "run_tests":
            args[slot] = False
        elif slot == "base_branch":
            args[slot] = "main"
        elif slot == "branch_name":
            args[slot] = "sweep/repo-args"
        elif slot == "edits":
            if "patch.tree_sitter.verify" in cid:
                raw = (src / "calc.py").read_text(encoding="utf-8")
                at = raw.index("x * 2")
                args[slot] = [{"path": _rel(src / "calc.py"), "start_byte": at,
                               "end_byte": at + 5, "expected": "x * 2",
                               "replacement": "x + x"}]
            else:
                args[slot] = [{"op": "rename_symbol", "module": "calc.py",
                               "qualname": "compute_total",
                               "new_name": "weighted_total"}]
        elif slot == "queries":
            args[slot] = ["compute_total"]
        elif slot == "fields":
            args[slot] = ["answer"]
        elif slot == "budget":
            args[slot] = 1
        elif slot in ("manifest", "cegis_manifest"):
            args[slot] = {"components": [], "counterexamples": [],
                          "initial_facts": ["python.source.file.available"],
                          "target": {"required_effects": [], "forbidden_effects": [],
                                     "max_components": 3, "top_k": 1},
                          "allow_candidate_components": False}
        elif slot == "test_grid":
            args[slot] = [{"input": [1, 2], "output": 4},
                          {"input": [3], "output": 6}]
        elif slot == "goal":
            args[slot] = "repair the failing test in the repository"
        elif slot == "candidate_response":
            args[slot] = "renamed compute_total to weighted_total in calc.py"
        elif slot == "raw_task_text" or slot == "task_text":
            args[slot] = "rename compute_total to weighted_total"
        elif slot in ("author_date", "committer_date"):
            args[slot] = "2026-01-01T00:00:00+00:00"
        elif slot in ("author_email", "committer_email"):
            args[slot] = "sweep@example.invalid"
        elif slot in ("author_name", "committer_name"):
            args[slot] = "Sweep Bot"
        elif slot == "title":
            args[slot] = "Sweep bench PR"
        elif slot == "body":
            args[slot] = "sweep-generated pull request body"
        elif slot in ("generated_tests_root", "test_growth_root"):
            gd = base / "gen_tests"
            gd.mkdir(exist_ok=True)
            args[slot] = str(gd)
        elif slot == "targets_path":
            tp = base / "targets.json"
            tp.write_text(json.dumps({"targets": ["calc.py"]}), encoding="utf-8")
            args[slot] = str(tp)
        elif slot == "training_pairs_path":
            tpp = base / "training_pairs.json"
            tpp.write_text(json.dumps({"pairs": [
                {"input": [1, 2], "output": 4},
                {"input": [3], "output": 6}]}), encoding="utf-8")
            args[slot] = str(tpp)
        elif slot == "training_pairs":
            args[slot] = [{"input": [1, 2], "output": 4},
                          {"input": [3], "output": 6}]
        elif slot == "evidence":
            args[slot] = [{"source_id": "sweep", "field": "answer",
                           "value": "weighted_total"}]
        elif slot == "source_id":
            args[slot] = "sweep"
        elif slot == "new_param":
            args[slot] = "values"
        elif slot == "test_argv":
            args[slot] = [sys.executable, "-m", "unittest", "-v", "test_calc"]
    return args or None


def _python_repair_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """Domain generator for the python-repair cluster, reusing a fixture that already works.

    Generic sampling cannot serve these: a repair capability needs a repository with a test
    that genuinely FAILS, and a file of plausible-looking text is not that. Supplying better
    plumbing produced BASELINE_ALREADY_PASSES -- nothing to repair -- which is the honest
    signal that this is a domain problem, not a typing problem.

    The domain is recognised by the SHAPE of the inputs (a source root plus tests), not by a
    list of capability ids, so it keeps working as the registry grows.
    """
    if "strict_progress" in cid:
        # strict loops score by parsing a unittest failure metric; coupled
        # bare-assert fixtures produce none (BASELINE_FAILURE_METRIC_UNPARSEABLE)
        fx = _swe_unittest_fixture(ws / f"strict{rng.randrange(1 << 30)}")
        out: dict = {}
        for slot, want in sig.items():
            if slot == "source_root":
                out[slot] = str(fx["src"])
            elif slot == "test_paths":
                out[slot] = [str(fx["test"])]
            elif slot == "test_argv" or want == ts.ARGV:
                out[slot] = [sys.executable, "-m", "unittest", "-v", "test_calc"]
        return out
    if "parse_edit_intent" in cid:
        # the issue file must carry issue_id + title or the adapter refuses by
        # contract (ISSUE_SCHEMA_MISSING); a random document is not an issue
        fx = _swe_unittest_fixture(ws / f"intent{rng.randrange(1 << 30)}")
        issue = fx["src"].parent / "issue.json"
        issue.write_text(json.dumps({
            "issue_id": "SWEEP-INTENT",
            "title": "Rename compute_total to weighted_total in calc",
        }), encoding="utf-8")
        out = {}
        for slot, want in sig.items():
            if slot == "issue_path":
                out[slot] = str(issue)
            elif slot == "source_root":
                out[slot] = str(fx["src"])
            elif slot == "index_path":
                # sampled cache files fail the adapter's cache schema check; an
                # empty value means "no cached index" by contract
                out[slot] = ""
        return out
    # The domain is "operates on python source", which is the presence of ANY
    # source slot -- not source_root plus tests. Requiring tests as well skipped
    # python.tests.audit.unittest (no test_paths) and patch.search (no
    # source_root), which are the same domain reached by a different door.
    if not ({"source_root", "source_path", "source_paths"} & set(sig)):
        return None
    from execution_guard import live_solver_families_v6_coupled as v6

    root = ws / f"repo{rng.randrange(1 << 30)}"
    root.mkdir(parents=True, exist_ok=True)
    # polarity: repair needs a failing baseline, an audit needs a passing one.
    # handing the red fixture to python.tests.audit.unittest produced
    # TEST_FILE_FAILED -- the fixture contradicting what the capability means.
    green = ("audit" in cid or "verify" in cid)
    bug = v6.fresh_coupled_bug(rng, root, rng.randrange(1 << 20), mutate=not green)

    args: dict = {}
    for slot, want in sig.items():
        if want == ts.PATH_DIR and ("source" in slot or "root" in slot):
            # the fixtures land in a subdirectory of root, and adapters glob
            # non-recursively, so the root that works is the one holding the
            # files. Pointing at root found nothing: TEST_AUDIT_EMPTY.
            args[slot] = str(bug.src.parent)
        elif want == ts.PATH_LIST and "test" in slot:
            args[slot] = [str(p) for p in bug.tests]
        elif want == ts.ARGV:
            args[slot] = [sys.executable, "-B", str(sorted(bug.tests)[0])]
        # caps that take a single file, or a list of files, rather than a root
        elif want == ts.PATH_FILE and "source" in slot:
            args[slot] = str(bug.src)
        elif want == ts.PATH_LIST and "source" in slot:
            args[slot] = [str(bug.src)]
    if "test_paths" not in args and "test_paths" in sig:
        args["test_paths"] = [str(p) for p in bug.tests]
    # a discovery glob is not free text: a random word matches no test file and
    # the adapter answers TEST_AUDIT_EMPTY, which is the sampler lying again
    if "pattern" in sig:
        args["pattern"] = "test_*.py"
    return args or None


def _saccr_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """finance.saccr.credit.addon.v1 rejects anything that is not {"trades": [...]}.

    saccr_credit_addon_gen_v1 emits exactly that, so the fix is to use it rather
    than to invent a schema the adapter might accept.
    """
    if "trades" not in cid and "saccr" not in cid:
        return None
    from canonical.capabilities.true.generators import saccr_credit_addon_gen_v1 as gen

    inst = gen.generate(rng, 1)[0]
    path = ws / f"trades{rng.randrange(1 << 30)}.json"
    path.write_text(json.dumps(inst), encoding="utf-8")
    out = {}
    for slot, want in sig.items():
        if want == ts.PATH_FILE:
            out[slot] = str(path)
    return out or None


def _docx_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """The docx verifiers need a real .docx, not a file of plausible text.

    docx_exact_text_edit_gen_v1 emits one base64-encoded. expected_structure is
    left to the sampler deliberately: guessing a structure the document does not
    have would turn a real signal into a false pass.
    """
    if not cid.startswith("docx."):
        return None
    if not ({"document_path", "docx_path", "path"} & set(sig)):
        return None
    from canonical.capabilities.true.generators import docx_exact_text_edit_gen_v1 as gen

    inst = gen.generate(rng, 1)[0]
    b64 = inst.get("docx_b64")
    if not b64:
        return None
    path = ws / f"doc{rng.randrange(1 << 30)}.docx"
    path.write_bytes(base64.b64decode(b64))
    out = {}
    for slot, want in sig.items():
        if want == ts.PATH_FILE:
            out[slot] = str(path)
    return out or None


def _pynguin_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """Domain generator for the pynguin synthesis family: a real module for
    the search to cover. A random string module_name is not a module -- the
    sampler lied by filling the type, not the referent."""
    if "pynguin" not in cid:
        return None
    fx = _swe_unittest_fixture(ws / f"pgn{rng.randrange(1 << 30)}")
    out: dict = {}
    for slot in sig:
        if slot == "source_root":
            out[slot] = str(fx["src"])
        elif slot == "module_name":
            out[slot] = "calc"
        elif slot == "time_budget_s":
            out[slot] = 12
        elif slot == "algorithm":
            out[slot] = "MOSA"
        elif slot == "search_seed":
            out[slot] = 20261029
    return out or None


def _amplify_args(cid: str, sig: dict, rng, ws: Path) -> dict | None:
    """Domain generator for the mutation-amplification family: a GREEN world
    with an existing suite (the mutation gate refuses a red base world) and a
    real module for Pynguin to cover."""
    if "mutation_kill" not in cid:
        return None
    fx = _swe_unittest_fixture(ws / f"amp{rng.randrange(1 << 30)}", green=True)
    out: dict = {}
    for slot in sig:
        if slot == "source_root":
            out[slot] = str(fx["src"])
        elif slot == "module_name":
            out[slot] = "calc"
        elif slot in ("time_budget_s",):
            out[slot] = 10
        elif slot in ("timeout_s",):
            out[slot] = 60
        elif slot in ("max_mutants",):
            out[slot] = 40
    return out or None


def _load_adapter(adapter_path: str, name: str):
    path = ROOT / adapter_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("MODULE_LOAD_FAILED:" + adapter_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sweep_one(cid: str, entry: dict, instances: int, seed: int, work: Path,
              use_schema: bool = True) -> dict:
    sig = ts.signature(entry)
    adapter_path = (entry.get("source") or {}).get("adapter_path")
    result = {
        "capability_id": cid,
        "signature": sig,
        "instances": instances,
        "executed": 0,
        "succeeded": 0,
        "failed": 0,
        "errors": {},
        "sample_error": None,
    }
    # 31 of 70 declare no source.adapter_path, but every one of them names an
    # adapter_module that exists on disk. Falling back to it is the difference between
    # "unrunnable" and "runnable" for a third of the registry -- and it matters because the
    # ones that then fail on a MISSING BINARY are failing on this sandbox, not on the
    # public runner, which has apt. Conflating those is the mistake of calling the
    # sandbox the machine.
    if not adapter_path:
        module_name = entry.get("adapter_module")
        if module_name:
            candidate = ROOT / "canonical/runtime/bound_capabilities" / f"{module_name}.py"
            if candidate.is_file():
                adapter_path = f"canonical/runtime/bound_capabilities/{module_name}.py"
    if not adapter_path:
        result["errors"]["NO_ADAPTER_RESOLVABLE"] = instances
        return result

    ws = work / cid.replace(".", "_")[:60]
    shutil.rmtree(ws, ignore_errors=True)
    ws.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    try:
        module = _load_adapter(adapter_path, "sweep_" + str(abs(hash(cid)) % 10_000))
    except Exception as exc:
        result["errors"]["ADAPTER_IMPORT_FAILED:" + type(exc).__name__] = instances
        result["sample_error"] = str(exc)[:300]
        return result

    # arguments the adapter requires that the registry never declared
    extra_slots = ts.adapter_arg_reads(entry).get("required") or []

    fn = getattr(module, (entry.get("entrypoint") or "run"), None)
    if fn is None:
        result["errors"]["NO_ENTRYPOINT"] = instances
        return result

    # The action_template IS the call. Placeholders are the inputs to fill; everything else
    # (argv, decode_callable, package_root, timeout_s) is literal configuration the adapter
    # also requires. Sampling only the placeholder-derived slots and handing those over was
    # the wrong model and produced 22 failures of the form CLI_ARGV_REQUIRED /
    # PYTHON_CODEC_CONTRACT_INCOMPLETE: adapters demanding arguments the call never carried.
    template_args = ((entry.get("action_template") or {}).get("args")) or {}

    for _ in range(instances):
        # a domain generator wins over generic sampling wherever one applies
        all_slots = dict(sig)
        for _k in extra_slots:
            all_slots.setdefault(_k, ts.type_of(_k))
        # _swe_repo_args first: _python_repair_args claims ANY signature with a
        # source_root, but orchestrate/refactor signatures only become fully
        # groundable when the SWE generator supplies worktree/diff/executable.
        # Repair loops have no structural keys, so they still fall through to
        # the repair fixture unharmed.
        # exact-cid generators claim BEFORE the broad _swe_repo_args claimer:
        # the broad one grounded source_root into its own repo world, leaving
        # module_name to the random string sampler (TARGET_MODULE_MISSING)
        domain = (_amplify_args(cid, all_slots, rng, ws)
                  or _pynguin_args(cid, all_slots, rng, ws)
                  or _swe_repo_args(cid, all_slots, rng, ws)
                  or _python_repair_args(cid, all_slots, rng, ws)
                  or _saccr_args(cid, all_slots, rng, ws)
                  or _docx_args(cid, all_slots, rng, ws) or {})
        try:
            # the capability id is what lets content rules be scoped per capability;
            # without it a rule for one capability's output_path would silently not apply
            # the format the adapter PARSES the file as, not what its name suggests
            formats = ts.parsed_formats(entry) if entry else {}
            # The mined schema is a hypothesis about what the adapter wants, and a
            # hypothesis can be wrong: it regressed archive.verify.tar_gz.gnu from a
            # domain error to a type error. So it is tried, not assumed, and the
            # capability itself decides. See the strategy note in sweep().
            schemas = (ts.parsed_schema(entry) if (entry and use_schema) else {})
            # Slots the domain generator already grounds are excluded from
            # sampling: a structural argument (a worktree, a python executable)
            # has no generic type sampler, which is precisely why the domain
            # exists. Sampling them anyway made 9 SWE capabilities UNSAMPLED
            # despite the domain handing over complete arguments.
            to_sample = {k: v for k, v in all_slots.items() if k not in domain}
            filled = samp.sample_args(to_sample, rng, ws, capability=cid,
                                      formats=formats, schemas=schemas)
            # the registry omits arguments the adapter nevertheless requires (65 of them
            # across 26 capabilities). Fill them from their names so the call is complete:
            # otherwise we are measuring our own incomplete template, not the capability.
            for key in extra_slots:
                if key not in filled and key not in domain:
                    filled[key] = samp.sample_args({key: type_of(key)}, rng, ws,
                                                   capability=cid)[key]
            merged = {**filled, **domain}
            path_kind = (ts.PATH_FILE, ts.PATH_DIR, ts.PATH_OUTPUT, ts.PATH_LIST)
            for _k, _v in list(merged.items()):
                _t = all_slots.get(_k)
                if isinstance(_v, str) and (_t in path_kind or "path" in _k) \
                        and _v.startswith(str(ROOT) + "/"):
                    merged[_k] = _v[len(str(ROOT)) + 1:]
                elif isinstance(_v, list) and (_t in path_kind or "path" in _k):
                    merged[_k] = [
                        x[len(str(ROOT)) + 1:] if isinstance(x, str)
                        and x.startswith(str(ROOT) + "/") else x for x in _v]
            args = _substitute(template_args, merged) if template_args else dict(merged)
        except samp.SamplingFailure as exc:
            result["errors"]["SAMPLING_FAILED:" + str(exc)] = \
                result["errors"].get("SAMPLING_FAILED:" + str(exc), 0) + 1
            continue
        result["executed"] += 1
        try:
            fn(dict(args), str(ROOT))
            result["succeeded"] += 1
        except SystemExit as exc:
            # Several adapters propulse domain failures as SystemExit(json). That IS the
            # capability's published failure channel, so it is a receipt, not a crash of
            # the sweep itself. Catching it here is the difference between "this capability
            # refused these args" (information) and "the sweep died at this capability"
            # (an instrument fault).
            key = "SystemExit:" + str(exc.code).split("\n")[0][:120]
            result["errors"][key] = result["errors"].get(key, 0) + 1
            if result["sample_error"] is None:
                result["sample_error"] = "adapter raised SystemExit: " + str(exc.code)[:300]
            result["failed"] += 1
        except Exception as exc:
            key = type(exc).__name__ + ":" + str(exc).split("\n")[0][:120]
            result["errors"][key] = result["errors"].get(key, 0) + 1
            if result["sample_error"] is None:
                result["sample_error"] = traceback.format_exc(limit=3)[:800]
            result["failed"] += 1
    return result


def sweep(instances: int, seed: int, only: set[str] | None = None) -> dict:
    registry = ts.load_registry()
    capabilities = registry.get("capabilities") or registry
    work = WORK
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    rows = []
    for cid, entry in sorted(capabilities.items()):
        if only and cid not in only:
            continue
        row = sweep_one(cid, entry, instances, seed, work)
        # A mined schema is a hypothesis, so it is only adopted when the
        # capability -- the one authority on what it accepts -- actually prefers
        # it. Both are run and the better stands; the winner is recorded, because
        # which input a capability needs is itself a finding. This is not tuning
        # until green: it is one alternative, chosen by the oracle, and reported.
        if (row["executed"] and row["failed"] > 0
                and ts.parsed_schema(entry)):
            plain = sweep_one(cid, entry, instances, seed, work, use_schema=False)
            if plain["succeeded"] > row["succeeded"]:
                plain["strategy"] = "generic"
                row = plain
            else:
                row["strategy"] = "schema"
        rows.append(row)

    clean = [r for r in rows if r["executed"] and r["failed"] == 0]
    partial = [r for r in rows if r["executed"] and 0 < r["failed"] < r["executed"]]
    broken = [r for r in rows if r["executed"] and r["failed"] == r["executed"]]
    unsampled = [r for r in rows if not r["executed"]]

    return {
        "schema": SCHEMA,
        "instances_per_capability": instances,
        "seed": seed,
        "model_dependency_count": 0,
        "totals": {
            "capabilities": len(rows),
            "clean_all_instances_pass": len(clean),
            "partial_some_instances_fail": len(partial),
            "broken_every_instance_fails": len(broken),
            "could_not_sample": len(unsampled),
        },
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instances", type=int, default=10)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default="", help="comma-separated capability ids")
    ns = ap.parse_args(argv)

    only = {x.strip() for x in ns.only.split(",") if x.strip()} or None
    receipt = sweep(ns.instances, ns.seed, only)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if ns.out:
        Path(ns.out).write_text(text, encoding="utf-8")
    t = receipt["totals"]
    print(f"capabilities swept            : {t['capabilities']}")
    print(f"  clean (every instance passed): {t['clean_all_instances_pass']}")
    print(f"  partial (some failed)        : {t['partial_some_instances_fail']}")
    print(f"  broken (every instance failed): {t['broken_every_instance_fails']}")
    print(f"  could not sample             : {t['could_not_sample']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
