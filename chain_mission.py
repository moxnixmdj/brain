#!/usr/bin/env python3
"""Flagship composition chain: issue -> edits -> gates -> PR realization.

One seeded repository goes through the whole proven SWE pipeline in a single
mediated process, and each stage CONSUMES the previous stage's artifacts:

  1. python.software.issue_to_pr.orchestrate.v1  (seeded issue -> worktree edit + diff + pr_intent)
  2. python.review.diff_type_gate.v1             (mypy over the produced diff/worktree)
  3. python.review.diff_static_triage.v1         (ruff over the same)
  4. python.review.diff_security_gate.v1         (bandit-oriented static security pass)
  5. python.repo.pr_realize.v1                   (apply the same diff onto a pristine
                                                  git baseline and open the branch)

Every stage runs AFTER root3 mediation is installed, so every subprocess the
adapters spawn (git, pytest, mypy, ruff) passes the attempt authority. The
chain receipt requires every stage's verified flag to be true.

This is the P1-3 gap closed: the primitives were proven separately; this proves
they compose on one repository with artifact hand-off, not just side by side.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/home/user/brain")
sys.path.insert(0, str(REPO))

from canonical.runtime import root3_strict_current_bootstrap_v3 as bootstrap
from canonical.runtime import root3_three_class_attempt_authorizer_v1 as attempt_authorizer

BED = REPO / "canonical/astra_runtime/chain_bed"


def seed_bed() -> None:
    shutil.rmtree(BED, ignore_errors=True)
    src = BED / "src"
    art = BED / "artifacts"
    src.mkdir(parents=True, exist_ok=True)
    art.mkdir(parents=True, exist_ok=True)
    (src / "calc.py").write_text(
        "def compute_total(items):\n"
        "    return sum(x * 2 for x in items)\n"
        "\n\n"
        "def render(items):\n"
        '    parts = [str(x) for x in items]\n'
        '    joined = ",".join(parts)\n'
        "    return joined\n",
        encoding="utf-8",
    )
    (src / "user_mod.py").write_text(
        "from calc import compute_total\n\n\n"
        "def twice(items):\n"
        "    return compute_total(items) * 2\n",
        encoding="utf-8",
    )
    (src / "test_calc.py").write_text(
        "import unittest\n"
        "from calc import compute_total\n\n\n"
        "class TestTotal(unittest.TestCase):\n"
        "    def test_doubled_total(self):\n"
        "        self.assertEqual(compute_total([1, 2, 3]), 12)\n",
        encoding="utf-8",
    )
    (BED / "task.json").write_text(json.dumps({
        "issue_id": "CHAIN-001",
        "title": "Rename compute_total to weighted_total",
        "edits": [{"op": "rename_symbol", "module": "calc.py",
                   "name": "compute_total", "new_name": "weighted_total"}],
    }), encoding="utf-8")


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, REPO / path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def prep_git_baseline() -> None:
    """All git scaffolding happens BEFORE bootstrap: after install_current the
    mediator governs every subprocess in the process, and this harness is not a
    registered callsite (only the adapters are)."""
    repo = BED / "repo"
    shutil.rmtree(repo, ignore_errors=True)
    shutil.copytree(BED / "src", repo)  # full baseline incl. tests: the
    # orchestrate diff touches the whole worktree and must apply cleanly
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=chain@example.invalid",
                    "-c", "user.name=Chain", "commit", "-qm", "baseline"], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(repo)], check=True)


def main() -> int:
    seed_bed()
    prep_git_baseline()
    status = bootstrap.install_current(
        attempt_authorizer.authorize, authority_id=attempt_authorizer.AUTHORITY_ID,
    )
    assert status.get("run_guard_active") is True, status

    orch = load("chain_orch", "canonical/runtime/bound_capabilities/python_issue_to_pr_orchestrate.py")
    type_gate = load("chain_tg", "canonical/runtime/bound_capabilities/python_review_diff_type_gate.py")
    static_gate = load("chain_sg", "canonical/runtime/bound_capabilities/python_review_diff_static_triage.py")
    sec_gate = load("chain_sec", "canonical/runtime/bound_capabilities/python_review_diff_security_gate.py")
    pr_realize = load("chain_pr", "canonical/runtime/bound_capabilities/python_repo_pr_realize.py")

    src = "canonical/astra_runtime/chain_bed/src"
    art = BED / "artifacts"
    t0 = time.monotonic()

    # --- stage 1: issue -> edited worktree + diff + pr_intent
    o = orch.run({
        "task_path": "canonical/astra_runtime/chain_bed/task.json",
        "source_root": src,
        "worktree_path": "canonical/astra_runtime/chain_bed/work",
        "output_path": "canonical/astra_runtime/chain_bed/artifacts/orchestrate.json",
        "diff_path": "canonical/astra_runtime/chain_bed/artifacts/chain.diff",
        "pr_intent_path": "canonical/astra_runtime/chain_bed/artifacts/pr_intent.json",
        "python_executable": sys.executable,
        "timeout_s": 60,
    }, str(REPO))
    assert o.get("verified") is True and o.get("edits_verified") is True, o

    diff = "canonical/astra_runtime/chain_bed/artifacts/chain.diff"
    worktree = "canonical/astra_runtime/chain_bed/work"

    # --- stage 2-4: the review gates consume the produced diff/worktree
    gates = {}
    for name, mod in (("type", type_gate), ("static", static_gate), ("security", sec_gate)):
        r = mod.run({
            "diff_path": diff,
            "worktree_path": worktree,
            "output_path": f"canonical/astra_runtime/chain_bed/artifacts/gate_{name}.json",
            "python_executable": sys.executable,
            "timeout_s": 120,
        }, str(REPO))
        gates[name] = r

    # --- stage 5: pristine git baseline receives the reviewed diff on a branch
    repo = BED / "repo"
    shutil.copy(REPO / diff, repo / "chain.diff")
    shutil.copy(art / "pr_intent.json", repo / "pr_intent.json")

    pr = pr_realize.run({
        "repo_path": "canonical/astra_runtime/chain_bed/repo",
        "diff_path": "chain.diff",
        "apply_directory": "",
        "branch_name": "swe/chain-001-weighted-total",
        "base_branch": "main",
        "pr_intent_path": "pr_intent.json",
        "output_path": "canonical/astra_runtime/chain_bed/artifacts/pr_realize.json",
        "python_executable": sys.executable,
        "timeout_s": 60,
    }, str(REPO))

    seconds = round(time.monotonic() - t0, 3)
    chain = {
        "schema": "PROJECT_BRAIN_SWE_CHAIN_PROOF_V1",
        "stages": {
            "orchestrate": {"verified": o.get("verified"), "edits_verified": o.get("edits_verified"),
                            "applied_site_count": o.get("applied_site_count")},
            "gate_type": {"verified": gates["type"].get("verified"),
                          "gate": gates["type"].get("gate")},
            "gate_static": {"verified": gates["static"].get("verified"),
                            "gate": gates["static"].get("gate")},
            "gate_security": {"verified": gates["security"].get("verified"),
                              "gate": gates["security"].get("gate")},
            "pr_realize": {"verified": pr.get("verified"),
                           "push_verified": pr.get("push_verified"),
                           "pushed_or_already_realized": bool(
                               pr.get("pushed") or pr.get("already_realized"))},
        },
        "seconds": seconds,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    clean_vals = []
    for svals in chain["stages"].values():
        clean_vals.append(all(v not in (False, None) for v in svals.values()))
    chain["chain_verified"] = all(clean_vals)
    out = art / "chain_receipt.json"
    out.write_text(json.dumps(chain, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(chain, indent=2))
    # the PR branch head tree actually carries the edited file. Read the git
    # object store directly (no spawned git: mediated, and this harness is not
    # a registered callsite). Loose-object zlib decode is honest proof.
    import re as _re
    import zlib as _zlib
    ok = False
    ref = (repo / ".git" / "refs" / "heads" / "swe" / "chain-001-weighted-total")
    if ref.is_file():
        # commit -> tree -> calc.py blob, all loose objects after git plumbing
        commit = _zlib.decompress((repo / ".git" / "objects" / ref.read_text().strip()[:2] / ref.read_text().strip()[2:]).read_bytes()).decode(errors="replace")
        tree_sha = _re.search(r"tree ([0-9a-f]{40})", commit).group(1)
        tree_raw = _zlib.decompress((repo / ".git" / "objects" / tree_sha[:2] / tree_sha[2:]).read_bytes())
        for m in _re.finditer(rb"([0-9a-f]{40})", tree_raw.hex().encode()):
            pass
        # simpler: scan tree entries by parsing the binary tree format
        i = tree_raw.index(b"\x00") if False else None
        entries = []
        pos = tree_raw.index(b" ") - 7  # skip obj header "tree N\0"
        start = tree_raw.index(b"\x00") + 1
        while True:
            nul = tree_raw.find(b"\x00", start)
            if nul < 0:
                break
            mode_name = tree_raw[start:nul].decode()
            sha = tree_raw[nul + 1:nul + 21].hex()
            entries.append((mode_name, sha))
            start = nul + 21
        for mode_name, sha in entries:
            if mode_name.endswith("calc.py"):
                blob = _zlib.decompress((repo / ".git" / "objects" / sha[:2] / sha[2:]).read_bytes()).decode(errors="replace")
                if "weighted_total" in blob:
                    ok = True
    print("=== branch calc.py carries rename:", ok)
    return 0 if chain["chain_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
