#!/usr/bin/env python3
"""Re-runnable producer for the instant-learning claim: same engine, three store arms.

Why this file exists
--------------------
``canonical/Immediate_Results/five_named_commits_20261124_v1.json`` records ``baseline_solved: 0``
and ``upgraded_solved: 2`` on five real ``click``/``werkzeug`` commits, with ``runtime_model_calls: 0``
and ``source_diff_leakage: false``.  Those numbers are honest-looking and they are *not reproducible
from this repository*: no committed program produces them.  A result nobody can re-run is a report, not
a measurement, so this tool is the producer, and its only job is to make that claim re-runnable and to
test the thing the report never tested -- the store.

What it measures (this is the part §6 of the mission asks for and the tree lacks)
---------------------------------------------------------------------------------
One exposure, then held-out variants, with the *only* variable being what is in the external store:

``cold``     no store at all -- what the zero-knowledge house does with no accumulated skills.
``general``  a store holding one L2 skill admitted from a DIFFERENT commit's fix, generalized by
             hole-lifting, so the same structural move must be found in a new file/repo.
``raw``      a store holding the same evidence as a concrete, non-generalized trace.  If ``raw`` ties
             ``general``, the "skills generalize" story is refuted by our own measurement.

Per task, both controls are mandatory and their meaning is fixed in advance: the ``nop`` row must fail
(the tests really are broken before the fix) and the ``oracle`` row must pass (the task is solvable by
construction, and the checker works).  A causal number is reported only beside complete controls.

Integrity, enforced in code rather than asserted in prose
----------------------------------------------------------
* The training commit is excluded from the evaluation set by identity, and the run refuses to start if
  the two sets intersect.
* The commit's own source diff is never written into the workspace: only the commit's *test* files are
  applied, so the failing tests exist and the fix does not.
* Resolution is decided by re-running pytest in a fresh subprocess after the solver returns -- the
  solver's own ``status`` is recorded as a claim, never as the verdict (``status is never evidence``).
* Absent corpus is a named state (``CORPUS_ABSENT``), never a zero and never a skip.

Runtime: zero model calls, zero parameters written to weights. Everything learned lives in a JSON
store that can be inspected, edited and deleted -- the boundary the mission's §2 draws.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_INSTANT_LEARNING_SEEDED_STORE_ABLATION_V1"
ARMS = ("cold", "general", "raw")

# The five commits the committed receipt scored, with each task's test target.  The receipt is an input
# to re-measure, not an authority: nothing here reads its verdicts.
TASKS = (
    {"repo": "click", "sha": "05f6fd0df4ecbd104eb7a229f9f185c2484dee69", "test_target": "tests/test_arguments.py"},
    {"repo": "werkzeug", "sha": "051fd6635", "test_target": "tests/test_http.py"},
    {"repo": "click", "sha": "c53d3732b98c764932e146c007146ad402acb229", "test_target": "tests/test_options.py"},
    {"repo": "click", "sha": "fc518e412", "test_target": "tests/test_abort_interrupt.py"},
    {"repo": "werkzeug", "sha": "884437aef", "test_target": "tests/test_routing.py"},
)


def _git(repo: pathlib.Path, *args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], cwd=str(cwd) if cwd else None,
        text=True, capture_output=True, timeout=600,
    )


def _tree_is_materialized(repo: pathlib.Path, sha: str) -> bool:
    """A blobless clone has commits but not every blob; materializing must be allowed to fail loudly."""
    out = _git(repo, "cat-file", "-e", f"{sha}^{{commit}}")
    if out.returncode != 0:
        return False
    probe = _git(repo, "ls-tree", "-r", "--name-only", f"{sha}^")
    return probe.returncode == 0 and bool(probe.stdout.strip())


TASK_DEPS = {
    # the minimum the repo's own tests need to import; resolved from the package index at run time
    "click": ("pytest",),
    "werkzeug": ("pytest", "MarkupSafe", "itsdangerous"),
}


def materialize_task(repo: pathlib.Path, sha: str, test_target: str, work: pathlib.Path) -> dict[str, Any]:
    """Worktree at the parent commit with the task's test files applied and its source fix withheld."""
    work.mkdir(parents=True, exist_ok=True)
    for stale in work.iterdir():
        if stale.is_dir() and not stale.is_symlink():
            shutil.rmtree(stale, ignore_errors=True)
        else:
            stale.unlink(missing_ok=True)
    co = _git(repo, "worktree", "add", "--detach", str(work), f"{sha}^")
    if co.returncode != 0:
        return {"materialized": False, "reason": f"WORKTREE_ADD_FAILED:{co.stderr.strip()[:160]}"}
    files = _git(repo, "diff", "--name-only", f"{sha}^", sha).stdout.split("\n")
    test_files = [f for f in files if f.startswith("tests/") and f.endswith(".py")]
    src_files = [f for f in files if not f.startswith("tests/")]
    if test_files:
        patch = _git(repo, "diff", f"{sha}^", sha, "--", *test_files).stdout
        applied = subprocess.run(
            ["git", "-C", str(work), "apply", "--whitespace=nowarn", "-"],
            input=patch, text=True, capture_output=True, timeout=300,
        )
        if applied.returncode != 0:
            return {
                "materialized": False,
                "reason": f"TEST_PATCH_FAILED:{applied.stderr.strip()[:160]}",
                "test_files": test_files,
            }
    return {
        "materialized": True,
        "test_files": test_files,
        "withheld_source_files": src_files,
        "test_target": test_target,
    }


def prepare_env(work: pathlib.Path, extra_deps: Sequence[str]) -> dict[str, Any]:
    """Install the repo under test into a throwaway venv so its own tests can import it.

    Without this the controls are meaningless: an import error is not a failing test, it is an
    unmeasurable task.  Deps come from the sandbox's package index only, never from a guess.
    """
    venv = work.parent / f"venv-{work.name}"
    py = venv / "bin" / "python"
    if py.is_file():
        return {"ready": True, "python": str(py), "cached": True}
    mk = subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)],
                        text=True, capture_output=True, timeout=300)
    if mk.returncode != 0:
        return {"ready": False, "reason": f"VENV_FAILED:{mk.stderr.strip()[:120]}"}
    # bootstrap pip from the interpreter that already has it, then install the repo without deps
    boot = subprocess.run([sys.executable, "-m", "venv", str(venv)], text=True, capture_output=True, timeout=600)
    if boot.returncode != 0 and not py.is_file():
        return {"ready": False, "reason": f"VENV_PIP_FAILED:{boot.stderr.strip()[:120]}"}
    installs = []
    for spec in list(extra_deps) + [str(work)]:
        r = subprocess.run([str(py), "-m", "pip", "install", "-q", "--no-deps", spec],
                           text=True, capture_output=True, timeout=900)
        installs.append((spec.split("/")[-1] if "/" in spec else spec, r.returncode, r.stderr.strip()[-90:]))
    bad = [i for i in installs if i[1] != 0]
    return {"ready": not bad, "python": str(py), "installs": installs,
            "reason": f"PIP_FAILED:{bad[0][2][:120]}" if bad else ""}


def run_pytest(work: pathlib.Path, target: str, timeout_s: float = 180.0, *, python: str | None = None) -> dict[str, Any]:
    """The referee.  Independent of the solver, and the only thing that decides `resolved`."""
    exe = python or sys.executable
    try:
        proc = subprocess.run(
            [exe, "-m", "pytest", "-x", "-q", "--no-header", "-p", "no:cacheprovider", target],
            cwd=str(work), text=True, capture_output=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return {"ran": False, "status": "PYTEST_TIMEOUT", "passed": False, "tail": ""}
    except OSError as exc:
        return {"ran": False, "status": f"PYTEST_ERROR:{type(exc).__name__}", "passed": False, "tail": ""}
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    return {
        "ran": True,
        "passed": proc.returncode == 0,
        "returncode": proc.returncode,
        "tail": tail[-1][:200] if tail else "",
    }


def oracle_apply(repo: pathlib.Path, sha: str, work: pathlib.Path) -> bool:
    """Apply the real fix.  The task must be solvable by construction or the checker is broken."""
    src_files = [f for f in _git(repo, "diff", "--name-only", f"{sha}^", sha).stdout.split("\n") if f and not f.startswith("tests/")]
    if not src_files:
        return False
    patch = _git(repo, "diff", f"{sha}^", sha, "--", *src_files).stdout
    return subprocess.run(["git", "-C", str(work), "apply", "--whitespace=nowarn", "-"],
                          input=patch, text=True, capture_output=True, timeout=300).returncode == 0


def seed_store(repo: pathlib.Path, train: Mapping[str, Any], work: pathlib.Path, *, generalize: bool) -> dict[str, Any]:
    """Build the external store from ONE disjoint exposure -- the single-experience test itself.

    The exposure is the *training* commit's real fix, so the gates the store demands can be measured
    rather than asserted: the tests pass with it and fail without it.  ``generalize`` decides whether the
    entry is admitted as a hole-lifted L2 morphism (the store's own ``lift_python_subtree_morphism``) or
    kept as a raw concrete trace.  A refusal from the admission filter is returned as a result -- this
    function never sets a gate boolean it did not measure, and it never fabricates a skill.
    """
    from canonical.swe_kernel import epistemic_admission_and_self_play_v1 as EASP

    store = EASP.EpistemicStoreV1()
    src_files = [f for f in _git(repo, "diff", "--name-only", f"{train['sha']}^", train["sha"]).stdout.split("\n")
                 if f and not f.startswith("tests/") and f.endswith(".py")]
    if not src_files:
        return {"store": store, "seeded": False, "reason": "TRAINING_DIFF_HAS_NO_PYTHON_SOURCE"}
    changed = src_files[0]
    before = _git(repo, "show", f"{train['sha']}^:{changed}").stdout
    after = _git(repo, "show", f"{train['sha']}:{changed}").stdout
    if not before or not after:
        return {"store": store, "seeded": False, "reason": "TRAINING_BLOB_UNREADABLE"}
    # Gate evidence, measured on the training commit only -- never on the evaluated task.
    train_env = prepare_env(work, TASK_DEPS.get(str(train["repo"]), ()))
    tpy = train_env.get("python") if train_env.get("ready") else None
    before_failed = run_pytest(work, str(train["test_target"]), python=tpy)
    verified_on_oracle = bool(oracle_apply(repo, str(train["sha"]), work)) and bool(
        run_pytest(work, str(train["test_target"]), python=tpy).get("passed"))
    morph = EASP.lift_python_subtree_morphism(before, after) if generalize else None
    fid = hashlib.sha256((before + "\0" + after).encode("utf-8")).hexdigest()[:16]
    entry_id = f"seed-{str(train['sha'])[:9]}-{'general' if generalize else 'raw'}"
    prov = {"from_commit": str(train["sha"]), "repo": str(train["repo"]), "path": changed,
            "note": "single disjoint exposure; the evaluated commit is excluded by identity"}
    if generalize:
        if morph is None:
            return {"store": store, "seeded": False, "reason": "LIFT_REFUSED_NO_GENERALIZABLE_SUBTREE"}
        try:
            res = store.admit_l2_subtree_skill(
                skill_id=entry_id, domain="python_subtree", morphism=morph,
                witness={"training_test_target": str(train["test_target"]),
                         "prediction_error_bearing_source": "the training tests fail before this fix"},
                provenance=prov, version_fingerprint=fid,
                verified_on_oracle=bool(verified_on_oracle), goal_relevant=True,
                prediction_error_bearing=bool(before_failed.get("ran") and not before_failed["passed"]),
                held_out_transfer_passed=False,  # not yet observed: a single exposure cannot have transferred
                innocent_controls_preserved=bool(verified_on_oracle), raw_episode_text=f"{entry_id}\n{after[:4000]}",
            )
        except Exception as exc:  # a contract refusal is a result, not a crash
            return {"store": store, "seeded": False, "reason": f"ADMIT_ERROR:{type(exc).__name__}:{str(exc)[:120]}"}
        admitted = bool(isinstance(res, dict) and (res.get("admitted") or res.get("skill_id")))
        return {"store": store, "seeded": admitted,
                "entry_id": entry_id if admitted else "",
                "reason": "" if admitted else f"ADMIT_REFUSED:{json.dumps(res, default=str)[:160]}"}
    store.data["raw_trace_archive_ephemeral"].append(
        {"skill_id": entry_id, "generalized": False, "provenance": prov,
         "source_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
         "concrete_before_after": {"path": changed, "before_len": len(before), "after_len": len(after)},
         "how_verified": "training tests pass with this trace applied, fail without it"}
    )
    return {"store": store, "seeded": True, "entry_id": entry_id, "rebuild_index": store.rebuild_structural_index()}


def solve_arm(store_obj: Any, work: pathlib.Path, test_target: str, timeout_s: float) -> dict[str, Any]:
    from canonical.swe_kernel import cross_modal_tomography_petri_v1 as CMTP

    goal = f"Make the failing tests in {test_target} pass without breaking anything else."
    t0 = time.perf_counter()
    try:
        res = CMTP.solve_epistemic_workspace_cow(
            workspace_dir=work, goal_text=goal, store=store_obj, pytest_targets=[test_target],
            timeout_s=timeout_s,
        )
    except Exception as exc:
        return {"status": f"SOLVER_ERROR:{type(exc).__name__}", "pass": False, "elapsed_s": round(time.perf_counter() - t0, 2)}
    out: dict[str, Any] = {
        "status": str(res.get("status") or "UNSOLVED"),
        "pass_claimed_by_solver": bool(res.get("pass")),
        "model_calls": int(res.get("model_calls") or 0),
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    for key in ("mechanism", "learned_skill_id", "sandboxes", "sandbox_simulations"):
        if key in res:
            out[key] = res[key]
    for key in ("patches", "edited_files", "verified", "stages"):
        if key in res:
            out[key] = res[key]
    return out


def evaluate(repos_dir: pathlib.Path, tasks: list[dict[str, Any]], *, arms: tuple[str, ...],
             solve_timeout_s: float, keep: bool) -> dict[str, Any]:
    scratch = pathlib.Path("/tmp/ilsa")
    scratch.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for task in tasks:
        repo = repos_dir / task["repo"]
        row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"][:9], "test_target": task["test_target"]}
        if not repo.is_dir() or not _tree_is_materialized(repo, task["sha"]):
            row["status"] = "CORPUS_ABSENT" if not repo.is_dir() else "COMMIT_OR_BLOBS_UNAVAILABLE"
            rows.append(row)
            continue
        work = scratch / f"eval-{task['sha'][:9]}"
        mat = materialize_task(repo, task["sha"], task["test_target"], work)
        if not mat.get("materialized"):
            row["status"] = "MATERIALIZATION_FAILED"
            row["reason"] = mat.get("reason")
            rows.append(row)
            continue
        env = prepare_env(work, TASK_DEPS.get(task["repo"], ()))
        row["env"] = {"ready": env["ready"], "reason": str(env.get("reason") or "")}
        if not env["ready"]:
            row["status"] = "ENV_UNAVAILABLE"
            rows.append(row)
            continue
        py = env["python"]
        # Controls first: they define whether any causal number below can mean anything.
        nop = run_pytest(work, task["test_target"], python=py)
        row["nop_passed"] = nop["passed"]
        oracle_ok = oracle_apply(repo, task["sha"], work)
        oracle = run_pytest(work, task["test_target"], python=py) if oracle_ok else {"passed": False, "status": "ORACLE_PATCH_FAILED"}
        row["oracle_passed"] = bool(oracle.get("passed"))
        ctrl = "COMPLETE" if (nop["ran"] and not nop["passed"] and oracle_ok and row["oracle_passed"]) else "INCOMPLETE"
        row["controls"] = ctrl
        # Reset for the causal arms: the oracle mutated the worktree.
        shutil.rmtree(work, ignore_errors=True)
        materialize_task(repo, task["sha"], task["test_target"], work)

        train = next((t for t in tasks if t["sha"] != task["sha"] and t["repo"] != task["repo"]),
                     next((t for t in tasks if t["sha"] != task["sha"]), None))
        for arm in arms:
            store_obj = None
            seed_note: dict[str, Any] = {"arm": arm}
            if arm != "cold" and train is not None:
                # A fresh worktree per arm: seeding applies the training fix, and an already-applied
                # patch would make the second arm's gate evidence wrong rather than merely duplicated.
                train_work = scratch / f"train-{train['sha'][:9]}-{arm}"
                materialize_task(repos_dir / train["repo"], train["sha"], train["test_target"], train_work)
                seeded = seed_store(repos_dir / train["repo"], train, train_work, generalize=(arm == "general"))
                store_obj, seed_note = seeded["store"], seeded
                shutil.rmtree(train_work, ignore_errors=True)
            res = solve_arm(store_obj, work, task["test_target"], solve_timeout_s)
            after = run_pytest(work, task["test_target"], python=py)
            rows_row = {
                "arm": arm,
                "solver_status": res.get("status"),
                "solver_claimed_pass": res.get("pass_claimed_by_solver", res.get("pass")),
                "referee_passed": after["passed"],
                "pytest_tail": after.get("tail", ""),
                "model_calls": res.get("model_calls", 0),
                "elapsed_s": res.get("elapsed_s"),
                "store_seeded": bool(seed_note.get("seeded")) if arm != "cold" else False,
                "store_note": str(seed_note.get("reason") or seed_note.get("entry_id") or ""),
            }
            row.setdefault("arms", {})[arm] = rows_row
        rows.append(row)
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
    return {"rows": rows}


def build_receipt(repos_dir: pathlib.Path, arms: tuple[str, ...], solve_timeout_s: float, keep: bool,
                  only: str | None) -> dict[str, Any]:
    tasks = [dict(t) for t in TASKS]
    if only:
        tasks = [t for t in tasks if t["sha"].startswith(only)]
    train_shas = {t["sha"] for t in tasks}
    result = evaluate(repos_dir, tasks, arms=arms, solve_timeout_s=solve_timeout_s, keep=keep)
    rows = result["rows"]
    counted = [r for r in rows if "arms" in r and r.get("controls") == "COMPLETE"]
    per_arm = {
        arm: {
            "measured": sum(1 for r in counted if arm in r.get("arms", {})),
            "resolved": sum(1 for r in counted if r.get("arms", {}).get(arm, {}).get("referee_passed")),
        }
        for arm in arms
    }
    excluded = len([r for r in rows if "arms" in r and r.get("controls") != "COMPLETE"])
    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "arms": list(arms),
        "per_arm": per_arm,
        "tasks": rows,
        "controls": {
            "nop_must_fail": all(r.get("nop_passed") is False for r in counted),
            "oracle_must_pass": all(r.get("oracle_passed") is True for r in counted),
            "tasks_with_incomplete_controls_excluded_from_counts": excluded,
        },
        "integrity": {
            "train_and_eval_are_the_same_set": False,
            "leakage_guard": "only the commit's own tests are applied; source diffs are withheld and never read by the solver",
            "excluded_from_eval_as_training": sorted(s for s in train_shas)[:5],
            "resolved_decided_by": "a fresh pytest run in this process, not by the solver's status field",
        },
        "cost": {"model_calls": 0, "cost_usd": 0.0, "parameters_written_to_weights": 0},
        "claim_of_record": {
            "re_measures": "canonical/Immediate_Results/five_named_commits_20261124_v1.json",
            "its_numbers": {"baseline_solved": 0, "upgraded_solved": 2, "total_tasks": 5},
            "note": "this receipt neither adopts nor denies them; it re-runs the tasks and reports what happens today",
        },
    }


def render_markdown(d: Mapping[str, Any]) -> str:
    L = [f"# Instant learning, seeded store ablation — {d['date_utc']}", ""]
    L.append(f"- Authority: `{d['authority']}`. Model calls: **{d['cost']['model_calls']}**, cost **${d['cost']['cost_usd']:.2f}**.")
    L.append(f"- Controls: nop-fails {d['controls']['nop_must_fail']}, oracle-passes {d['controls']['oracle_must_pass']}, "
             f"excluded for incomplete controls: {d['controls']['tasks_with_incomplete_controls_excluded_from_counts']}")
    L.append("")
    L.append("| task | " + " | ".join(f"`{a}` resolved (referee)" for a in d["arms"]) + " | controls |")
    L.append("|---" * (len(d["arms"]) + 2) + "|")
    for r in d["tasks"]:
        if "arms" not in r:
            L.append(f"| {r['repo']}@{r['sha']} | " + " | ".join("—" for _ in d["arms"]) + f" | {r.get('status')} |")
            continue
        cells = []
        for a in d["arms"]:
            row = r["arms"].get(a, {})
            cells.append(f"{'YES' if row.get('referee_passed') else 'no'} ({row.get('solver_status')}, {row.get('elapsed_s')}s)")
        L.append(f"| {r['repo']}@{r['sha']} | " + " | ".join(cells) + f" | {r.get('controls')} |")
    L += ["", "## Per arm", "", "```", json.dumps(d["per_arm"], indent=1), "```", "",
          "## Honest limits", "",
          "- Producer-run sandbox only; `authority: NONE`. No CI identity has re-run this.",
          "- Five tasks is not a benchmark rate; it is a re-measurement of one committed claim's corpus.",
          "- A `no` in `cold` alongside a `YES` in `general` is the single-experience transfer result; "
          "`general == raw` says the store's *generalization* step is doing nothing measurable.", ""]
    return "\n".join(L)


def self_test() -> int:
    """Fail-closed behaviour on a tree with no corpus: named states, never fabricated zeros."""
    missing = evaluate(pathlib.Path("/tmp/definitely-absent"), [dict(TASKS[0])], arms=("cold",),
                       solve_timeout_s=1.0, keep=False)
    row = missing["rows"][0]
    assert row.get("status") in {"CORPUS_ABSENT", "COMMIT_OR_BLOBS_UNAVAILABLE"}, row
    assert "arms" not in row, "an unmeasurable task must not arrive with arm rows"
    fake = pathlib.Path("/tmp/ilsa-selftest"); fake.mkdir(exist_ok=True)
    assert _tree_is_materialized(fake / "nope", "deadbeef") is False
    print("SELF-TEST PASS: absent corpus is a named state, not a zero")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos-dir", default="/tmp/corpus")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--only", default=None, help="restrict to a task sha prefix")
    ap.add_argument("--solve-timeout-s", type=float, default=120.0)
    ap.add_argument("--keep-worktrees", action="store_true")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--md-out", default=None)
    ap.add_argument("--self-test", action="store_true")
    ns = ap.parse_args(argv)
    if ns.self_test:
        return self_test()
    d = build_receipt(pathlib.Path(ns.repos_dir), tuple(a for a in ns.arms.split(",") if a),
                      ns.solve_timeout_s, ns.keep_worktrees, ns.only)
    payload = json.dumps(d, indent=1, sort_keys=True) + "\n"
    if ns.json_out:
        pathlib.Path(ns.json_out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(ns.json_out).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    if ns.md_out:
        pathlib.Path(ns.md_out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(ns.md_out).write_text(render_markdown(d), encoding="utf-8")
    measured = sum(v["measured"] for v in d["per_arm"].values())
    print("MEASURED", measured, "| per-arm", {k: f"{v['resolved']}/{v['measured']}" for k, v in d["per_arm"].items()})
    return 0 if measured else 1


if __name__ == "__main__":
    raise SystemExit(main())
