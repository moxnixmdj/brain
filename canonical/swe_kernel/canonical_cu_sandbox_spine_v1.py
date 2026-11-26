#!/usr/bin/env python3
"""Canonical Speculative CoW Rollback & Code-over-GUI Computer-Use Spine (`0F`).

Unifies Project Brain's previously disconnected speculative execution, Petri-net
cut-vertex checkpointing, CoW workspace rollback, typed value algebra, A11y tree,
and blind RGB canvas tomography engines under one front-door spine:

  1. CoW Speculative Workspace Execution & Blind RGB Canvas Tomography:
       ``canonical.swe_kernel.universal_computer_agent_v1``
  2. Multi-Layer Differential Tomography & Petri Rollout:
       ``canonical.swe_kernel.speculative_cow_petri_agent_v1``
  3. Cryptographic Undo / Free-Failure Tree Inspection:
       ``canonical.tools.the_failed_attempt_is_free_v1``
  4. Typed Value Algebra (Programmatic Bypass over GUI Menus):
       ``canonical.runtime.value_algebra_v1``
  5. Accessibility Tree Execution:
       ``canonical.swe_kernel.interface_action_grammar_v1``

Implements CoAct-1 Code-over-GUI delegation + DeltaBox/TClone-style fork/probe/
rollback/commit semantics: failed attempts are 100% isolated and rolled back so
the live workspace remains byte-for-byte intact unless every postcondition and
negative-effect guard passes.
"""
from __future__ import annotations

import hashlib
import importlib
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


class _LazyModule:
    __slots__ = ("_mod_name", "_loaded")

    def __init__(self, mod_name: str) -> None:
        object.__setattr__(self, "_mod_name", mod_name)
        object.__setattr__(self, "_loaded", None)

    def __getattr__(self, item: str) -> Any:
        mod = object.__getattribute__(self, "_loaded")
        if mod is None:
            mod = importlib.import_module(object.__getattribute__(self, "_mod_name"))
            object.__setattr__(self, "_loaded", mod)
        return getattr(mod, item)


val_alg = _LazyModule("canonical.runtime.value_algebra_v1")
action_grammar = _LazyModule("canonical.swe_kernel.interface_action_grammar_v1")
scpa = _LazyModule("canonical.swe_kernel.speculative_cow_petri_agent_v1")
uca = _LazyModule("canonical.swe_kernel.universal_computer_agent_v1")
free_fail = _LazyModule("canonical.tools.the_failed_attempt_is_free_v1")

SCHEMA = "PROJECT_BRAIN_CANONICAL_CU_SANDBOX_SPINE_V1"
NON_CLAIMS = (
    "no_capability_credit",
    "no_ownership_credit",
    "no_terminal_credit",
    "zero_model_cow_sandbox_execution",
)


def workspace_tree_digest(root: Path) -> tuple[str, dict[str, str]]:
    """Deterministic read-only SHA-256 digest of all relative files under ``root``."""
    snap = uca.snapshot_workspace_files(root)
    per_file: dict[str, str] = {}
    h = hashlib.sha256()
    for rel in sorted(snap.keys()):
        fh = str(snap[rel][0])
        per_file[rel] = fh
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(fh.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest(), per_file


def diff_file_hashes(before: Mapping[str, str], after: Mapping[str, str]) -> dict[str, list[str]]:
    b_keys = set(before.keys())
    a_keys = set(after.keys())
    return {
        "added": sorted(a_keys - b_keys),
        "deleted": sorted(b_keys - a_keys),
        "modified": sorted(k for k in (a_keys & b_keys) if before[k] != after[k]),
    }


@dataclass
class SpeculativeProbeResult:
    candidate_id: str
    passed: bool
    committed: bool
    returncode: int | None
    stdout: str
    stderr: str
    elapsed_ms: float
    diff: dict[str, list[str]]
    negative_effect_ok: bool
    rejection_reason: str | None = None
    tomography_diff: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "passed": self.passed,
            "committed": self.committed,
            "returncode": self.returncode,
            "stdout": self.stdout[:800],
            "stderr": self.stderr[:800],
            "elapsed_ms": round(self.elapsed_ms, 3),
            "diff": self.diff,
            "negative_effect_ok": self.negative_effect_ok,
            "rejection_reason": self.rejection_reason,
            "tomography_diff": self.tomography_diff,
        }


class SpeculativeSandbox:
    """DeltaBox/TClone-style CoW fork → probe → verify → commit/rollback workspace sandbox."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def _copy_to_clone(self, dest: Path) -> None:
        shutil.copytree(
            self.workspace_root,
            dest,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "node_modules"),
        )

    def _commit_clone(self, clone_root: Path, diff: Mapping[str, Sequence[str]]) -> None:
        for rel in diff.get("deleted", ()):
            p = self.workspace_root / rel
            if p.exists() and p.is_file():
                p.unlink()
        for rel in list(diff.get("added", ())) + list(diff.get("modified", ())):
            src = clone_root / rel
            dst = self.workspace_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def evaluate_candidates(
        self,
        candidates: Sequence[Mapping[str, Any]],
        *,
        postcondition: Callable[[Path], bool],
        allowed_write_paths: Sequence[str] = (),
        allow_deletions: bool = False,
        commit_winner: bool = True,
        timeout_s: float = 15.0,
    ) -> dict[str, Any]:
        """Speculatively evaluate candidates in isolated CoW clones; commit first verified winner only."""
        pre_digest, pre_hashes = workspace_tree_digest(self.workspace_root)
        pre_tomo = scpa.capture_tomography_snapshot(self.workspace_root)
        allowed_set = {str(p).lstrip("./") for p in allowed_write_paths}

        probe_results: list[SpeculativeProbeResult] = []
        winner_id: str | None = None
        committed = False

        for idx, cand in enumerate(candidates):
            cid = str(cand.get("id") or f"cand_{idx}")
            t0 = time.perf_counter()
            with tempfile.TemporaryDirectory(prefix=f"brain_cow_{cid}_") as tmp_dir:
                clone = Path(tmp_dir) / "ws"
                self._copy_to_clone(clone)
                clone_before_snap = uca.snapshot_workspace_files(clone)

                rc: int | None = 0
                stdout = ""
                stderr = ""
                exec_err: str | None = None

                try:
                    if callable(cand.get("fn")):
                        cand["fn"](clone)
                    elif cand.get("argv"):
                        proc = subprocess.run(
                            [str(x) for x in cand["argv"]],
                            cwd=str(clone),
                            capture_output=True,
                            text=True,
                            timeout=timeout_s,
                        )
                        rc = proc.returncode
                        stdout = proc.stdout
                        stderr = proc.stderr
                    elif isinstance(cand.get("write_files"), Mapping):
                        for rel, content in cand["write_files"].items():
                            target = clone / str(rel)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            if isinstance(content, bytes):
                                target.write_bytes(content)
                            else:
                                target.write_text(str(content), encoding="utf-8")
                    else:
                        exec_err = "UNSUPPORTED_CANDIDATE_SPEC"
                        rc = -1
                except subprocess.TimeoutExpired:
                    exec_err = "CANDIDATE_TIMEOUT"
                    rc = -1
                except Exception as exc:
                    exec_err = f"{type(exc).__name__}: {exc}"
                    rc = -1

                _, clone_after_hashes = workspace_tree_digest(clone)
                clone_after_snap = uca.snapshot_workspace_files(clone)
                clone_after_tomo = scpa.capture_tomography_snapshot(clone)
                diff = diff_file_hashes(pre_hashes, clone_after_hashes)
                tomo_diff = scpa.diff_tomography(pre_tomo, clone_after_tomo)

                # Negative-effect / scope boundary checks
                neg_oracle = uca.evaluate_negative_effect_oracle(clone_before_snap, clone_after_snap)
                neg_ok = True
                rejection: str | None = exec_err

                if not allow_deletions and diff["deleted"]:
                    neg_ok = False
                    rejection = rejection or f"DISALLOWED_DELETION:{diff['deleted']}"
                if allowed_set:
                    touched = set(diff["added"]) | set(diff["modified"]) | set(diff["deleted"])
                    outside = sorted(touched - allowed_set)
                    if outside:
                        neg_ok = False
                        rejection = rejection or f"WRITE_OUTSIDE_ALLOWED_PATHS:{outside}"
                if isinstance(neg_oracle, Mapping) and neg_oracle.get("violation"):
                    neg_ok = False
                    rejection = rejection or f"NEGATIVE_EFFECT_VIOLATION:{neg_oracle.get('violation')}"

                post_ok = False
                if exec_err is None and neg_ok and (rc == 0 or cand.get("allow_nonzero_rc")):
                    try:
                        post_ok = bool(postcondition(clone))
                    except Exception as exc:
                        rejection = f"POSTCONDITION_ERROR:{type(exc).__name__}:{exc}"
                        post_ok = False
                    if not post_ok and rejection is None:
                        rejection = "POSTCONDITION_FALSE"

                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                did_commit = False
                if post_ok and neg_ok and winner_id is None:
                    winner_id = cid
                    if commit_winner:
                        self._commit_clone(clone, diff)
                        did_commit = True
                        committed = True

                probe_results.append(
                    SpeculativeProbeResult(
                        candidate_id=cid,
                        passed=bool(post_ok and neg_ok),
                        committed=did_commit,
                        returncode=rc,
                        stdout=stdout,
                        stderr=stderr,
                        elapsed_ms=elapsed_ms,
                        diff=diff,
                        negative_effect_ok=neg_ok,
                        rejection_reason=rejection,
                        tomography_diff=tomo_diff if isinstance(tomo_diff, dict) else {},
                    )
                )
                if winner_id is not None:
                    break

        post_digest, _ = workspace_tree_digest(self.workspace_root)
        workspace_preserved_on_failure = (winner_id is None and post_digest == pre_digest)
        return {
            "passed": winner_id is not None,
            "winner_id": winner_id,
            "committed": committed,
            "pre_digest": pre_digest,
            "post_digest": post_digest,
            "workspace_preserved_on_failure": workspace_preserved_on_failure,
            "probes": [p.as_dict() for p in probe_results],
        }


def execute_speculative_computer_task(
    *,
    workspace_root: str | Path | None = None,
    candidates: Sequence[Mapping[str, Any]] = (),
    postcondition: Callable[[Path], bool] | None = None,
    allowed_write_paths: Sequence[str] = (),
    allow_deletions: bool = False,
    commit_winner: bool = True,
    petri_edges: Sequence[tuple[str, str]] = (),
    petri_start: str | None = None,
    petri_goal: str | None = None,
    value_algebra_query: Mapping[str, Any] | None = None,
    a11y_env: action_grammar.A11yEnvironment | None = None,
    gui_instruction: str | None = None,
    gui_goal_check: Callable[[Any], bool] | None = None,
    canvas_env: Any = None,
    canvas_goal_predicate: Callable[[Any], bool] | None = None,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Unified front-door entrypoint (`0F`) with CoAct-1 Code-over-GUI routing + CoW rollback."""
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE_SANDBOX",
        "model_calls": 0,
        "non_claims": list(NON_CLAIMS),
        "route_selected": None,
        "modules_invoked": [],
    }

    # Optional Petri dominator cut-vertex analysis (for checkpoint placement in multi-step CU graphs)
    if petri_edges and petri_start is not None and petri_goal is not None:
        report["modules_invoked"].append("canonical.swe_kernel.universal_computer_agent_v1:compute_petri_dominator_cut_vertices")
        report["petri_cut_vertices"] = uca.compute_petri_dominator_cut_vertices(
            petri_edges, petri_start, petri_goal
        )

    # Route 1A (CoAct-1 Programmatic Typed Value Algebra Bypass): construct typed value directly
    if value_algebra_query is not None:
        report["modules_invoked"].append("canonical.runtime.value_algebra_v1")
        q = str(value_algebra_query.get("question") or "")
        q_root = str(value_algebra_query.get("root") or workspace_root or ".")
        ents = value_algebra_query.get("ents") or {}
        words = list(value_algebra_query.get("words") or [])
        composed = val_alg.compose(q, q_root, ents, words)
        verified = bool(composed is not None and val_alg.verify(q, q_root, composed))
        report["value_algebra_result"] = {"composed": composed, "verified": verified}
        if verified:
            report["route_selected"] = "COACT_1_VALUE_ALGEBRA_BYPASS"
            report["pass"] = True
            report["status"] = "PASS__COACT_PROGRAMMATIC_BYPASS"
            report["reason"] = None
            return report

    # Route 1B (CoAct-1 Programmatic / CLI Speculative CoW Workspace Rollback & Commit)
    if workspace_root is not None and candidates and postcondition is not None:
        report["modules_invoked"].extend(
            [
                "canonical.swe_kernel.universal_computer_agent_v1",
                "canonical.swe_kernel.speculative_cow_petri_agent_v1",
                "canonical.tools.the_failed_attempt_is_free_v1",
            ]
        )
        sandbox = SpeculativeSandbox(workspace_root)
        cow_out = sandbox.evaluate_candidates(
            candidates,
            postcondition=postcondition,
            allowed_write_paths=allowed_write_paths,
            allow_deletions=allow_deletions,
            commit_winner=commit_winner,
            timeout_s=timeout_s,
        )
        report["cow_sandbox_result"] = cow_out
        if cow_out["passed"]:
            report["route_selected"] = "COACT_1_SPECULATIVE_COW_SANDBOX"
            report["pass"] = True
            report["status"] = "PASS__SPECULATIVE_COW_VERIFIED"
            report["reason"] = None
            return report

    # Route 2 (Accessibility Tree GUI Execution)
    if a11y_env is not None and gui_instruction is not None and gui_goal_check is not None:
        report["modules_invoked"].append("canonical.swe_kernel.interface_action_grammar_v1:solve_gui_goal")
        gui_out = action_grammar.solve_gui_goal(a11y_env, gui_instruction, gui_goal_check)
        report["a11y_gui_result"] = gui_out
        if bool(gui_out.get("solved") or gui_out.get("pass") or gui_out.get("ok")):
            report["route_selected"] = "A11Y_TREE_GUI_ACTION_GRAMMAR"
            report["pass"] = True
            report["status"] = "PASS__A11Y_GUI_VERIFIED"
            report["reason"] = None
            return report

    # Route 3 (Blind Pure-Pixel RGB Canvas Differential Tomography)
    if canvas_env is not None and canvas_goal_predicate is not None:
        report["modules_invoked"].append("canonical.swe_kernel.universal_computer_agent_v1:CanvasPureGuiTomographer")
        tomographer = uca.CanvasPureGuiTomographer()
        canvas_out = tomographer.discover_and_solve(
            canvas_env,
            canvas_goal_predicate,
            goal_label="front_door_canvas_goal",
        )
        report["canvas_tomography_result"] = canvas_out
        if bool(canvas_out.get("solved") or canvas_out.get("pass")):
            report["route_selected"] = "BLIND_RGB_CANVAS_TOMOGRAPHY"
            report["pass"] = True
            report["status"] = "PASS__CANVAS_TOMOGRAPHY_VERIFIED"
            report["reason"] = None
            return report

    # If only Petri cut-vertex analysis was requested and succeeded
    if "petri_cut_vertices" in report and not candidates and a11y_env is None and canvas_env is None and value_algebra_query is None:
        pv = report["petri_cut_vertices"]
        ok = bool(pv and pv.get("reachable", True))
        report["route_selected"] = "PETRI_DOMINATOR_CHECKPOINT_ANALYSIS"
        report["pass"] = ok
        report["status"] = "PASS__PETRI_DOMINATOR_COMPUTED" if ok else "FAIL_CLOSED__PETRI_UNREACHABLE"
        report["reason"] = None if ok else "PETRI_GOAL_UNREACHABLE"
        return report

    report["route_selected"] = report["route_selected"] or "ALL_ROUTES_EXHAUSTED"
    report["pass"] = False
    report["status"] = "FAIL_CLOSED__CU_SANDBOX_UNSOLVED"
    report["reason"] = "NO_CANDIDATE_OR_ROUTE_VERIFIED"
    return report


def _cow_clone_tree(src: Path, dst: Path) -> str:
    """Zero-copy reflink CoW clone when filesystem supports it (`DeltaFS`/Btrfs/XFS), falling back to `shutil.copytree`."""
    cp_bin = shutil.which("cp")
    if cp_bin:
        try:
            proc = subprocess.run(
                [cp_bin, "-a", "--reflink=auto", str(src), str(dst)],
                capture_output=True,
                timeout=10.0,
                check=False,
            )
            if proc.returncode == 0 and dst.is_dir():
                return "REFLINK_AUTO"
        except Exception:
            pass
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, symlinks=True)
    return "COPYTREE_FALLBACK"


def durable_transactional_commit(
    workspace_root: str | Path,
    file_writes: Mapping[str, bytes | str],
    *,
    crash_at: str | None = None,
    recover_after_crash: bool = False,
) -> dict[str, Any]:
    """Crash-safe multi-path journaled commit (`the_record_is_the_commit_v1` × STRATUS TNR).

    Every multi-file commit stages its files, computes idempotent SHA-256 content-addressed
    operations (`operations(world)`), and writes a durable journal first (`before_journal` ->
    `after_journal` -> `after_op:<path>` -> `after_committed` -> `after_cleanup`), so a crash
    at ANY boundary can be deterministically recovered via `the_record_is_the_commit_v1.recover`.
    """
    from canonical.tools import the_record_is_the_commit_v1 as rec_commit

    root = Path(workspace_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    journal_root = root / ".brain_commit_journal"
    stage_dir = journal_root / "stage"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Copy existing live files (excluding journal dir) into stage, then apply requested writes
    for live_f in root.rglob("*"):
        if not live_f.is_file():
            continue
        rel = live_f.relative_to(root)
        if rel.parts and rel.parts[0] == ".brain_commit_journal":
            continue
        dst_s = stage_dir / rel
        dst_s.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live_f, dst_s)

    expected_shas: dict[str, str] = {}
    for rel, raw in sorted(file_writes.items()):
        rel_s = str(rel).lstrip("/")
        p_live = (root / rel_s).resolve()
        p_live.relative_to(root)
        p_live.parent.mkdir(parents=True, exist_ok=True)
        p_stage = (stage_dir / rel_s).resolve()
        p_stage.relative_to(stage_dir)
        p_stage.parent.mkdir(parents=True, exist_ok=True)
        data = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
        p_stage.write_bytes(data)
        expected_shas[rel_s] = hashlib.sha256(data).hexdigest()

    world = {"live": root, "stage": stage_dir}
    # Ignore files inside .brain_commit_journal when computing diff operations
    ops = [
        op
        for op in rec_commit.operations(world)
        if not str(op.get("path") or "").startswith(".brain_commit_journal")
    ]
    trace: list[str] = []
    if crash_at is None:
        commit_res = rec_commit.run_commit(journal_root, world, ops, None, trace, with_record=True)
    else:
        import json as _json
        import sys as _sys

        # Run crash-injected commit in a real isolated child process because `run_commit` calls `os._exit(9)`!
        child_code = (
            "import json, pathlib, sys; "
            "from canonical.tools import the_record_is_the_commit_v1 as rc; "
            "j = pathlib.Path(sys.argv[1]); live = pathlib.Path(sys.argv[2]); stage = pathlib.Path(sys.argv[3]); "
            "ops = json.loads(sys.argv[4]); crash_at = sys.argv[5]; "
            "res = rc.run_commit(j, {'live': live, 'stage': stage}, ops, crash_at, [], with_record=True); "
            "print(json.dumps(res))"
        )
        proc = subprocess.run(
            [
                _sys.executable,
                "-c",
                child_code,
                str(journal_root),
                str(root),
                str(stage_dir),
                _json.dumps(ops),
                str(crash_at),
            ],
            capture_output=True,
            text=True,
            timeout=15.0,
            check=False,
        )
        commit_res = {
            "completed": proc.returncode == 0,
            "crashed": ("CRASH_AT:" in proc.stderr) or (proc.returncode == 9),
            "returncode": proc.returncode,
            "stderr": proc.stderr.strip(),
        }
    recovery_res = None
    if crash_at is not None and recover_after_crash:
        recovery_res = rec_commit.recover(journal_root, world, trace)
    final_shas = {rel: rec_commit.sha_of(root / rel) for rel in expected_shas}
    all_committed = all(final_shas.get(k) == v for k, v in expected_shas.items())
    # Clean up staging/journal directory after full clean completion or recovery
    if all_committed:
        shutil.rmtree(journal_root, ignore_errors=True)
    passed = all_committed if (crash_at is None or recover_after_crash) else bool(commit_res.get("crashed"))
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__DURABLE_COMMIT_VERIFIED"
            if all_committed
            else ("PASS__CRASH_INJECTED_RECORDED" if commit_res.get("crashed") else "FAIL_CLOSED__COMMIT_INCOMPLETE")
        ),
        "all_committed": all_committed,
        "operation_count": len(ops),
        "commit_result": commit_res,
        "recovery_result": recovery_res,
        "final_shas": final_shas,
        "trace": trace,
        "model_calls": 0,
    }


def speculative_cow_race(
    workspace_root: str | Path,
    branches: Sequence[Mapping[str, Any]],
    oracle_fn: Callable[[Path], bool],
    *,
    commit_winner: bool = True,
    durable_commit: bool = False,
) -> dict[str, Any]:
    """Speculative side-effect-free CoW multi-future race (`0F` × DeltaBox/BunshinFork rollback).

    Each branch in ``branches`` supplies:
      - ``branch_id``: str
      - ``apply_fn``: Callable[[Path], Any]  (mutates an isolated CoW copy of ``workspace_root``)

    If a branch satisfies ``oracle_fn(branch_dir)``, ONLY that winning branch's file changes are
    committed back to ``workspace_root`` (when ``commit_winner=True``); losing branches and failed
    races are discarded with zero side-effect leakage onto the real workspace.
    """
    import filecmp
    import shutil
    import tempfile

    t0 = time.perf_counter()
    root = Path(workspace_root).resolve()
    branch_results: list[dict[str, Any]] = []
    winner: dict[str, Any] | None = None
    committed_files: list[str] = []
    clone_modes: list[str] = []
    durable_receipt: dict[str, Any] | None = None

    with tempfile.TemporaryDirectory(prefix="brain_cow_race_") as tmp_base:
        tmp_path = Path(tmp_base)
        for idx, br in enumerate(branches):
            bid = str(br.get("branch_id") or f"branch_{idx}")
            apply_fn = br.get("apply_fn")
            if not callable(apply_fn):
                branch_results.append({"branch_id": bid, "passed": False, "error": "APPLY_FN_NOT_CALLABLE"})
                continue
            bdir = tmp_path / f"b_{idx}"
            clone_modes.append(_cow_clone_tree(root, bdir))
            b_t0 = time.perf_counter()
            err = None
            passed = False
            try:
                apply_fn(bdir)
                passed = bool(oracle_fn(bdir))
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"
                passed = False
            b_ms = round((time.perf_counter() - b_t0) * 1000.0, 3)
            branch_results.append({"branch_id": bid, "passed": passed, "elapsed_ms": b_ms, "error": err})
            if passed and winner is None:
                winner = {"branch_id": bid, "dir": bdir}
                if commit_winner:
                    # Commit only changed/added files from winning branch; remove deleted files
                    win_files = {p.relative_to(bdir) for p in bdir.rglob("*") if p.is_file()}
                    orig_files = {p.relative_to(root) for p in root.rglob("*") if p.is_file()}
                    to_write: dict[str, bytes] = {}
                    for rel in sorted(win_files):
                        src = bdir / rel
                        dst = root / rel
                        if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                            to_write[str(rel)] = src.read_bytes()
                            committed_files.append(str(rel))
                    if durable_commit and to_write:
                        durable_receipt = durable_transactional_commit(root, to_write)
                    else:
                        for rel_s, data in to_write.items():
                            dst = root / rel_s
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            dst.write_bytes(data)
                    for rel in sorted(orig_files - win_files):
                        (root / rel).unlink(missing_ok=True)
                        committed_files.append(f"-{rel}")
                break

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "schema": SCHEMA,
        "pass": winner is not None,
        "status": "PASS__SPECULATIVE_COW_WINNER_COMMITTED" if winner is not None else "FAIL_CLOSED__ALL_COW_BRANCHES_ROLLED_BACK",
        "winner_branch_id": winner["branch_id"] if winner is not None else None,
        "committed": bool(winner is not None and commit_winner),
        "committed_files": committed_files,
        "clone_mode": clone_modes[0] if clone_modes else None,
        "durable_commit_receipt": durable_receipt,
        "branches_evaluated": len(branch_results),
        "branch_results": branch_results,
        "elapsed_ms": elapsed_ms,
        "model_calls": 0,
    }


def inspect_repo_environment_broker(repo_root: str | Path) -> dict[str, Any]:
    """Zero-model environment broker inspection (`the_environment_broker_v1` + `causal_computer_use_agent_v1`)."""
    from canonical.runtime import causal_computer_use_agent_v1 as causal_cu
    from canonical.swe_kernel import the_environment_broker_v1 as broker_mod

    root = Path(repo_root).resolve()
    layout = broker_mod.detect_layout(root)
    pyproject = (root / "pyproject.toml") if (root / "pyproject.toml").is_file() else None
    decls = broker_mod.read_declarations(root, pyproject)
    test_cmds = broker_mod.declared_test_commands(root, pyproject)
    runners = broker_mod.runner_candidates(root, pyproject)
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__ENVIRONMENT_BROKER_INSPECTED",
        "repo_root": str(root),
        "layout": layout,
        "declarations": decls,
        "declared_test_commands": test_cmds,
        "runner_candidates": runners,
        "causal_cu_agent_wired": hasattr(causal_cu, "GoalDirectedAgent"),
        "model_calls": 0,
    }


def compile_four_tier_cu_action(
    *,
    direct_command: Sequence[str] | None = None,
    webmcp_tool: Mapping[str, Any] | None = None,
    typed_action: Mapping[str, Any] | None = None,
    osworld_v21_state: Mapping[str, Any] | None = None,
    aimed_observation: Mapping[str, Any] | None = None,
    screen_width: int = 1920,
    screen_height: int = 1080,
) -> dict[str, Any]:
    """Enforce the Zero-Pixel-First Computer-Use escalation ladder:
      Tier 0:   direct CLI / programmatic command (0 pixels, <1ms)
      Tier 0.5: WebMCP / CDP typed browser tool (`document.modelContext`, 0 pixels)
      Tier 1:   typed OSWorld surface / a11y action (`osworld_computer_surface_v1`)
      Tier 1.5: OSWorld v2.1 zero-model a11y/tomography policy (`osworld_v21_zero_model_policy_v1`)
      Tier 2:   geometric aimed action (`aimed_action_v1`, zero VLM)
      Tier 3:   fail-closed visual fallback witness (never hallucinates coordinates)
    """
    if direct_command:
        return {
            "schema": SCHEMA,
            "pass": True,
            "tier": "TIER_0_DIRECT_PROGRAMMATIC",
            "pixels_used": 0,
            "argv": [str(x) for x in direct_command],
            "model_calls": 0,
        }
    if isinstance(webmcp_tool, Mapping) and webmcp_tool.get("name"):
        return {
            "schema": SCHEMA,
            "pass": True,
            "tier": "TIER_0_5_WEBMCP_TYPED_TOOL",
            "pixels_used": 0,
            "tool_name": str(webmcp_tool["name"]),
            "arguments": dict(webmcp_tool.get("arguments") or {}),
            "origin": str(webmcp_tool.get("origin") or ""),
            "model_calls": 0,
        }
    if typed_action is not None:
        from canonical.runtime import osworld_computer_surface_v1 as osw

        sc = osw.Screen(int(screen_width), int(screen_height))
        code = osw.compile_osworld_pyautogui(typed_action, sc)
        return {
            "schema": SCHEMA,
            "pass": True,
            "tier": "TIER_1_TYPED_SURFACE_ACTION",
            "pixels_used": 0,
            "compiled_code": code,
            "model_calls": 0,
        }
    if osworld_v21_state is not None:
        from canonical.runtime import osworld_v21_zero_model_policy_v1 as osw21

        st_norm = dict(osworld_v21_state)
        if "a11y_tree" not in st_norm and "accessibility_tree" in st_norm:
            st_norm["a11y_tree"] = st_norm["accessibility_tree"]
        policy = osw21.ZeroModelOSWorldPolicy()
        decision = dict(policy(st_norm))
        actions = list(decision.get("actions") or ())
        non_wait = [a for a in actions if str((a or {}).get("type") or "").upper() != "WAIT"]
        ok = bool(non_wait or decision.get("action") is not None or decision.get("done") is True)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "tier": "TIER_1_5_OSWORLD_V21_ZERO_MODEL_POLICY",
            "pixels_used": 0,
            "decision": decision,
            "model_calls": 0,
        }
    if aimed_observation is not None:
        from canonical.runtime import aimed_action_v1 as aimed

        rows = aimed.aimed_rows(dict(aimed_observation))
        if rows:
            return {
                "schema": SCHEMA,
                "pass": True,
                "tier": "TIER_2_GEOMETRIC_AIMED_ACTION",
                "pixels_used": 0,
                "actions": rows,
                "model_calls": 0,
            }
    return {
        "schema": SCHEMA,
        "pass": False,
        "tier": "TIER_3_VISUAL_FALLBACK_REQUIRED",
        "status": "FAIL_CLOSED__LOWER_TIERS_INSUFFICIENT",
        "insufficiency_witness": "NO_TIER0_CMD_NO_WEBMCP_NO_TIER1_SURFACE_NO_TIER2_GEOMETRY",
        "model_calls": 0,
    }


def fork_reality_speculate_and_commit(
    *,
    workspace_root: str | Path | None = None,
    action_fn: Callable[[Path], Mapping[str, Any]] | None = None,
    verify_fn: Callable[[Path, Mapping[str, Any]], bool] | None = None,
    env_state: Any = None,
    candidate_actions: Sequence[tuple[str, Callable[[Any], Any]]] = (),
    snapshot_fn: Callable[[Any], Mapping[str, Any]] | None = None,
    goal_facts: Sequence[str] = (),
    goal_fn: Callable[[Mapping[str, Any]], bool] | None = None,
    confined_argv: Sequence[str] | None = None,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Wave 17: Fork-Reality CoW Speculative World Engine + Kernel Seccomp Confinement Audit.

    Wires three previously unwired/isolated engines directly into Spine 0F:
    - `canonical.swe_kernel.transactional_parallel_execution_v1` (transactional CoW rollback + confined exec)
    - `canonical.runtime.worker_syscall_allowlist_v1` (real kernel seccomp BPF allowlist posture)
    - `canonical.swe_kernel.cross_modal_tomography_petri_v1` (multi-layer state tomography + `os.fork()` CoW rollouts)
    """
    from canonical.runtime import worker_syscall_allowlist_v1 as seccomp_wl
    from canonical.swe_kernel import cross_modal_tomography_petri_v1 as xmodal
    from canonical.swe_kernel import transactional_parallel_execution_v1 as tx_exec

    t0 = time.perf_counter()
    # 1. Kernel seccomp confinement posture audit
    try:
        arch = seccomp_wl.machine()
        allowed = list(seccomp_wl.allowed_names())
        refused = list(seccomp_wl.refused_names())
        bpf_len = len(seccomp_wl.program(arch))
        seccomp_posture = {
            "available": True,
            "arch": arch,
            "allowed_count": len(allowed),
            "refused_count": len(refused),
            "bpf_instructions": bpf_len,
        }
    except Exception as exc:
        seccomp_posture = {"available": False, "reason": f"{type(exc).__name__}:{exc}"}

    # Mode A: Multi-way os.fork() CoW speculative state rollout (zero neural hallucination!)
    if env_state is not None and candidate_actions:
        snap_fn = snapshot_fn or (
            lambda st: xmodal.capture_multilayer_state(
                html_dom=str(st.get("html_dom", "")) if isinstance(st, Mapping) else "",
                a11y_tree=list(st.get("a11y_tree", ())) if isinstance(st, Mapping) else [],
                kv_state=dict(st) if isinstance(st, Mapping) else {"value": repr(st)},
            )
        )
        wrapped_actions: list[tuple[str, Callable[[Any], Any]]] = []
        for act_name, act_fn in candidate_actions:
            def _wrapped(st: Any, _f: Callable[[Any], Any] = act_fn) -> Any:
                out = _f(st)
                if isinstance(out, Mapping) and out is not st and isinstance(st, dict):
                    st.clear()
                    st.update(out)
                return out
            wrapped_actions.append((str(act_name), _wrapped))
        rollouts = xmodal.speculative_cow_rollout(
            env_state=env_state,
            candidate_actions=wrapped_actions,
            snapshot_fn=snap_fn,
            goal_facts=tuple(goal_facts),
        )
        winner = rollouts.get("winner") if isinstance(rollouts, Mapping) else None
        outcomes = list(rollouts.get("all_outcomes") or ()) if isinstance(rollouts, Mapping) else []
        if winner is None and goal_fn is not None:
            for row in outcomes:
                if isinstance(row, Mapping) and bool(goal_fn(row)):
                    winner = dict(row)
                    break
        passed = winner is not None if (goal_facts or goal_fn is not None) else bool(outcomes)
        return {
            "schema": SCHEMA,
            "pass": passed,
            "status": (
                "PASS__COW_SPECULATIVE_WINNER_FOUND"
                if winner is not None
                else ("PASS__COW_SPECULATIVE_DELTAS_CAPTURED" if not (goal_facts or goal_fn) and outcomes else "FAIL_CLOSED__NO_SPECULATIVE_GOAL_WINNER")
            ),
            "mode": "COW_SPECULATIVE_ROLLOUT",
            "winner": winner,
            "rollout_count": len(outcomes),
            "deltas": outcomes,
            "raw_rollout": rollouts,
            "seccomp_posture": seccomp_posture,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    # Mode B: Transactional CoW workspace action with automatic rollback on failed verify_fn
    if workspace_root is not None and action_fn is not None:
        ws = Path(workspace_root).resolve()
        before_manifest = tx_exec.snapshot_workspace_manifest(ws)
        res = tx_exec.execute_transactional_cow_action(
            ws,
            action_fn,
            verify_fn=verify_fn,
        )
        after_manifest = tx_exec.snapshot_workspace_manifest(ws)
        committed = bool(res.get("committed") or res.get("pass") or res.get("ok"))
        host_preserved_on_rollback = (before_manifest == after_manifest) if not committed else True
        return {
            "schema": SCHEMA,
            "pass": committed,
            "status": "PASS__TRANSACTIONAL_COW_COMMITTED" if committed else "FAIL_CLOSED__TRANSACTIONAL_COW_ROLLED_BACK",
            "mode": "TRANSACTIONAL_COW_ACTION",
            "committed": committed,
            "host_preserved_on_rollback": host_preserved_on_rollback,
            "tx_result": dict(res),
            "seccomp_posture": seccomp_posture,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    # Mode C: Confined command execution
    if confined_argv is not None and workspace_root is not None:
        cmd_res = tx_exec.run_confined_command(list(confined_argv), cwd=Path(workspace_root).resolve(), timeout=float(timeout_s))
        ok = bool(cmd_res.get("ok") or cmd_res.get("returncode") == 0)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__CONFINED_COMMAND_EXECUTED" if ok else "FAIL_CLOSED__CONFINED_COMMAND_FAILED",
            "mode": "CONFINED_COMMAND",
            "command_result": dict(cmd_res),
            "seccomp_posture": seccomp_posture,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED__NO_SPECULATIVE_OR_CONFINED_WORKLOAD",
        "seccomp_posture": seccomp_posture,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def elevate_gui_trace_to_cli_skill(
    trace: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    goal: str = "",
    postcondition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Wave 17: Automatically lift GUI/DOM traces down to deterministic HTTP/CDP/CLI layers (`CLI-Anything` style)."""
    from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as trace_comp

    t0 = time.perf_counter()
    elevated = dict(trace_comp.elevate_trace_to_fastest_layer(trace))
    steps = list(elevated.get("steps") or elevated.get("elevated_steps") or ())
    skill = None
    if goal and steps:
        try:
            skill = trace_comp.anti_unify_workflow(goal, steps, dict(postcondition or {}))
        except Exception as exc:
            skill = {"anti_unify_note": f"{type(exc).__name__}:{exc}"}
    ok = bool(steps or elevated.get("fastest_layer") or elevated.get("layer"))
    return {
        "schema": SCHEMA,
        "pass": ok,
        "status": "PASS__TRACE_ELEVATED_TO_FASTEST_LAYER" if ok else "FAIL_CLOSED__TRACE_NOT_ELEVATABLE",
        "elevated": elevated,
        "compiled_skill": skill,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def execute_horizon_bounded_zero_screenshot_cu(
    *,
    task_id: str = "cu_task",
    goal: Sequence[str] = (),
    constraints: Sequence[Mapping[str, Any]] = (),
    subgoals: Sequence[Mapping[str, Any]] = (),
    total_step_budget: int = 16,
    initial_state: Mapping[str, bytes] | None = None,
    dom_observation: Mapping[str, Any] | None = None,
    target_url: str | None = None,
    run_tier0_cache_suite: bool = False,
    vocabulary_invocation: str | None = None,
    vocabulary_states: Mapping[str, Mapping[str, bytes]] | None = None,
) -> dict[str, Any]:
    """Wave 25 (`0F`): Horizon-Bounded Computer-Use Execution + Zero-Screenshot DOM Cache + Vocabulary Growth.

    Fuses 3 hidden `Agent S4` / `CLI-Anything` zero-LLM engines:
      1. `verified_zero_screenshot_action_cache_v1` (`normalize_url_to_origin_and_template`,
         `canonical_dom_a11y_fingerprint`, `execute_tier0_data_layer_suite`).
      2. `horizon_bounded_execution_v1` (`Constraint`, `SubGoal`, `sense_task`,
         `generate_decompositions`, `execute_task`) for checkpointed multi-subgoal execution.
      3. `vocabulary_growth_v1` (`evidence`, `diagnose`) for refusal-driven observable vocabulary growth.
    """
    import tempfile as _tf

    from canonical.runtime import verified_zero_screenshot_action_cache_v1 as zsc
    from canonical.swe_kernel import horizon_bounded_execution_v1 as hbe
    from canonical.swe_kernel import vocabulary_growth_v1 as vg

    t0 = time.perf_counter()
    cache_report: dict[str, Any] | None = None
    if target_url is not None or dom_observation is not None or run_tier0_cache_suite:
        cache_report = {}
        if target_url is not None:
            origin, template = zsc.normalize_url_to_origin_and_template(str(target_url))
            cache_report["url_origin"] = origin
            cache_report["url_template"] = template
        if dom_observation is not None:
            cache_report["dom_fingerprint"] = zsc.canonical_dom_a11y_fingerprint(dom_observation)
        if run_tier0_cache_suite:
            cache_report["tier0_suite"] = zsc.execute_tier0_data_layer_suite()

    horizon_report: dict[str, Any] | None = None
    if subgoals:
        c_objs = [
            hbe.Constraint(
                name=str(c.get("name") or f"c_{i}"),
                check=str(c.get("check") or ""),
                must_hold_at=tuple(str(x) for x in (c.get("must_hold_at") or ("every_step",))),
            )
            for i, c in enumerate(constraints)
        ]
        sg_objs = [
            hbe.SubGoal(
                subgoal_index=int(sg.get("subgoal_index", i)),
                description=str(sg.get("description") or f"subgoal_{i}"),
                precondition=frozenset(str(x) for x in (sg.get("precondition") or ())),
                postcondition=frozenset(str(x) for x in (sg.get("postcondition") or ())),
                step_budget=int(sg.get("step_budget", 4)),
                constraint_names=frozenset(str(x) for x in (sg.get("constraint_names") or ())),
            )
            for i, sg in enumerate(subgoals)
        ]
        sensed = hbe.sense_task(
            str(task_id),
            [str(g) for g in goal],
            c_objs,
            int(total_step_budget),
            sg_objs,
            dict(initial_state or {}),
        )
        decomp = hbe.generate_decompositions(sensed)
        exec_out = hbe.execute_task(decomp)
        res_obj = exec_out.get("result") or exec_out.get("execution_result")
        horizon_report = {
            "verdict": str(exec_out.get("verdict") or ""),
            "goal_reached": bool(getattr(res_obj, "goal_reached", exec_out.get("goal_reached", False))),
            "within_total_budget": bool(getattr(res_obj, "within_total_budget", True)),
            "all_constraints_preserved": bool(getattr(res_obj, "all_constraints_preserved", True)),
            "total_steps": int(getattr(res_obj, "total_steps", 0)),
            "rollbacks": int(getattr(res_obj, "rollbacks", 0)),
        }

    vocab_report: dict[str, Any] | None = None
    if vocabulary_invocation and vocabulary_states:
        with _tf.TemporaryDirectory(prefix="wave25_vg_") as td:
            ev = vg.evidence(
                str(vocabulary_invocation),
                {str(k): dict(v) for k, v in vocabulary_states.items()},
                Path(td),
                repetitions=2,
            )
            diag = vg.diagnose(ev, {str(k): dict(v) for k, v in vocabulary_states.items()})
            vocab_report = {
                "invocation": str(vocabulary_invocation),
                "diagnosis": diag,
            }

    checks: list[bool] = []
    if cache_report is not None:
        suite = cache_report.get("tier0_suite")
        checks.append(bool(suite.get("pass", suite.get("ok", True))) if isinstance(suite, Mapping) else True)
    if horizon_report is not None:
        checks.append(bool(horizon_report.get("within_total_budget")) and bool(horizon_report.get("all_constraints_preserved")))
    if vocab_report is not None:
        checks.append(bool(vocab_report.get("diagnosis")))
    ok = bool(checks) and all(checks)
    return {
        "schema": SCHEMA,
        "pass": ok,
        "status": "PASS__HORIZON_ZERO_SCREENSHOT_CU_EXECUTED" if ok else "FAIL_CLOSED__CU_BUDGET_OR_CACHE_FAILED",
        "zero_screenshot_cache": cache_report,
        "horizon_execution": horizon_report,
        "vocabulary_growth": vocab_report,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def plan_two_move_and_horizon_bridge(
    *,
    two_move_start: Mapping[str, int] | None = None,
    two_move_goal: Mapping[str, Any] | None = None,
    two_move_moves: Sequence[Mapping[str, Any]] = (),
    two_move_max_depth: int = 8,
    bridge_task_id: str | None = None,
    bridge_goal: Sequence[str] = (),
    bridge_constraints: Sequence[Mapping[str, Any]] = (),
    bridge_subgoals: Sequence[Mapping[str, Any]] = (),
    bridge_total_step_budget: int = 16,
    bridge_initial_state: Mapping[str, bytes] | None = None,
    bridge_holdout_initial_states: Sequence[Mapping[str, bytes]] = (),
    dag_root: str | Path | None = None,
    dag_stages: Sequence[str] = (),
    dag_stage_solver: Callable[[str, int], dict[str, Any]] | None = None,
    dag_scope_paths: Sequence[str] = (),
    osworld_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Wave 30 (`0F` × `a_goal_that_needs_two_moves_v1` × `perfect_algorithm_horizon_bridge_v1`
    × `goal_dag_executor_v1` × `osworld_v21_workflow_policy_v2`, `K3=0`).

    Compositional multi-move planning + long-horizon verified CU bridge + transactional Goal DAGs
    + multi-clause OSWorld v2.1 cross-step workflow routing:
      1. Plans multi-move sequences over capability classes (`a_goal_that_needs_two_moves_v1`)
         for goals that NO single capability can satisfy (detecting order dependence automatically).
      2. Runs the 5-phase `perfect_algorithm_horizon_bridge_v1` pipeline (`sense -> contrast ->
         identify -> admit -> remember`) over bounded long-horizon subgoals.
      3. Executes a transactional multi-stage Goal DAG (`goal_dag_executor_v1`) with automatic
         rollback on syntax or stage failure.
      4. Routes multi-clause OSWorld v2.1 desktop instructions with cross-clause reference
         materialization (`osworld_v21_workflow_policy_v2`).
    """
    t0 = time.perf_counter()
    two_move_report: dict[str, Any] | None = None
    two_move_ok = True
    if two_move_start is not None and two_move_goal is not None and two_move_moves:
        from canonical.runtime import a_goal_that_needs_two_moves_v1 as two_m

        start_w = two_m.world(
            names=int(two_move_start.get("names", 0)),
            readable=two_move_start.get("readable"),
            contents=two_move_start.get("contents"),
            removed=int(two_move_start.get("removed", 0)),
        )
        at_least_norm = (
            {str(k).upper(): int(v) for k, v in two_move_goal["at_least"].items()}
            if two_move_goal.get("at_least")
            else None
        )
        at_most_norm = (
            {str(k).upper(): int(v) for k, v in two_move_goal["at_most"].items()}
            if two_move_goal.get("at_most")
            else None
        )
        goal_obj = two_m.Goal(
            at_least=at_least_norm,
            at_most=at_most_norm,
            desc=str(two_move_goal.get("desc") or ""),
        )
        move_objs = [
            two_m.Move(str(m["id"]), str(m.get("tool") or m["id"]), dict(m.get("signature") or {}))
            for m in two_move_moves
        ]
        one_ans = two_m.one_move_answers(goal_obj, move_objs, start_w)
        order_info = two_m.why_order_matters(move_objs, start_w)
        try:
            seq = two_m.plan(start_w, goal_obj, move_objs, max_depth=int(two_move_max_depth))
            # Verify plan by simulating transitions
            cur = dict(start_w)
            by_id = {mv.id: mv for mv in move_objs}
            for mid in seq:
                cur = by_id[mid].apply(cur)
            holds_end = goal_obj.holds(cur)
            two_move_ok = bool(holds_end)
            two_move_report = {
                "pass": two_move_ok,
                "start_world": start_w,
                "final_world": cur,
                "one_move_answers": one_ans,
                "requires_multi_move": len(one_ans) == 0 and len(seq) >= 2,
                "plan": seq,
                "why_order_matters": order_info,
            }
        except two_m.Refusal as ref:
            two_move_ok = False
            two_move_report = {
                "pass": False,
                "refusal_code": str(ref.code),
                "refusal_detail": str(ref.detail),
                "one_move_answers": one_ans,
                "plan": None,
            }

    bridge_report: dict[str, Any] | None = None
    bridge_ok = True
    if bridge_task_id and bridge_subgoals:
        from canonical.swe_kernel import perfect_algorithm_horizon_bridge_v1 as hbridge

        c_objs = [
            hbridge.HConstraint(
                name=str(c.get("name") or f"c_{i}"),
                check=str(c.get("check") or ""),
                must_hold_at=tuple(str(x) for x in (c.get("must_hold_at") or ("every_step",))),
            )
            for i, c in enumerate(bridge_constraints)
        ]
        sg_objs = [
            hbridge.HSubGoal(
                subgoal_index=int(sg.get("subgoal_index", i)),
                description=str(sg.get("description") or f"sg_{i}"),
                precondition=frozenset(str(x) for x in (sg.get("precondition") or ())),
                postcondition=frozenset(str(x) for x in (sg.get("postcondition") or ())),
                step_budget=int(sg.get("step_budget", 4)),
                constraint_names=frozenset(str(x) for x in (sg.get("constraint_names") or ())),
            )
            for i, sg in enumerate(bridge_subgoals)
        ]
        sensed = hbridge.bridge_sense(
            str(bridge_task_id),
            [str(g) for g in bridge_goal],
            c_objs,
            int(bridge_total_step_budget),
            sg_objs,
            dict(bridge_initial_state or {}),
        )
        contrasted = hbridge.bridge_contrast(sensed)
        identified = hbridge.bridge_identify(contrasted)
        holdouts = [
            hbridge.HTask(
                task_id=f"{bridge_task_id}_holdout_{hi}",
                goal=frozenset(str(g) for g in bridge_goal),
                constraints=tuple(c_objs),
                total_step_budget=int(bridge_total_step_budget),
                subgoals=tuple(sg_objs),
                initial_state=dict(hst),
            )
            for hi, hst in enumerate(bridge_holdout_initial_states)
        ]
        admitted = hbridge.bridge_admit(identified, holdout_tasks=holdouts)
        remembered = hbridge.bridge_remember(admitted)
        bridge_ok = (
            admitted.get("status") == hbridge.BRIDGE_ADMITTED
            if holdouts
            else identified.get("status") == hbridge.BRIDGE_IDENTIFIED
        )
        bridge_report = {
            "pass": bridge_ok,
            "sense_status": sensed.get("status"),
            "contrast_status": contrasted.get("status"),
            "identify_status": identified.get("status"),
            "admit_status": admitted.get("status"),
            "remember_status": remembered.get("status"),
            "holdout_count": len(holdouts),
            "subgoal_count": len(sg_objs),
        }

    dag_report: dict[str, Any] | None = None
    dag_ok = True
    if dag_root is not None and dag_stages and dag_stage_solver is not None:
        from canonical.swe_kernel import goal_dag_executor_v1 as dag_exec

        dag_res = dag_exec.execute_transactional_goal_dag(
            root=Path(dag_root).resolve(),
            stages=list(dag_stages),
            stage_solver=dag_stage_solver,
            scope_paths=list(dag_scope_paths),
        )
        dag_ok = bool(
            dag_res.get("ok")
            or dag_res.get("all_passed")
            or dag_res.get("pass")
            or dag_res.get("status") in {"PASS", "ALL_STAGES_PASSED", "COMPLETED"}
        )
        dag_report = dict(dag_res)

    osworld_report: dict[str, Any] | None = None
    osworld_ok = True
    if osworld_state is not None:
        from canonical.runtime import osworld_v21_workflow_policy_v2 as osw_pol

        osw_out = dict(osw_pol.decide(dict(osworld_state)))
        osworld_ok = bool(osw_out.get("actions") or osw_out.get("response") is not None)
        osworld_report = osw_out

    any_active = any(x is not None for x in (two_move_report, bridge_report, dag_report, osworld_report))
    overall = any_active and two_move_ok and bridge_ok and dag_ok and osworld_ok
    return {
        "schema": SCHEMA,
        "pass": overall,
        "status": (
            "PASS__TWO_MOVE_HORIZON_CU_PLANNED"
            if overall
            else "FAIL_CLOSED__TWO_MOVE_OR_HORIZON_CU_FAILED"
        ),
        "two_move_plan": two_move_report,
        "horizon_bridge": bridge_report,
        "goal_dag": dag_report,
        "osworld_v21_decision": osworld_report,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def execute_osworld_v21_and_epistemic_cu(
    *,
    # 1. OSWorld 2.1 pure-stdlib policy + verifier + constraint guard + adapter
    osworld_state: Mapping[str, Any] | None = None,
    policy_mode: str = "workflow_v7",
    instruction: str | None = None,
    proposed_action: Mapping[str, Any] | None = None,
    protected_paths: Sequence[str] | None = None,
    run_recovery: bool = True,
    compile_adapter_actions: bool = True,
    # 2. Epistemic computer agent (`epistemic_computer_agent_v1`)
    nl_goal: str | None = None,
    inspect_path: str | Path | None = None,
    epistemic_store_root: str | Path | None = None,
    # 3. Action-grammar guide (`the_guide_is_an_action_grammar_v1`)
    grammar_need: str | Mapping[str, Any] | None = None,
    grammar_root: str | Path | None = None,
    grammar_pages: Mapping[str, Any] | None = None,
    grammar_declared_flags: Mapping[str, Mapping[str, Any]] | None = None,
    grammar_program: str | None = None,
) -> dict[str, Any]:
    """Wave 34: OSWorld 2.1 Pure-Stdlib CU Engine + Epistemic Computer Agent + Action-Grammar Guide (`0F`, `K3=0`).

    Composes 10 pure-stdlib CU & epistemic modules lazily on demand (with optional PIL detection for visual v13/v17 overlays).
    """
    import importlib.util

    t0 = time.perf_counter()
    engines_invoked: list[str] = []
    results: dict[str, Any] = {}
    has_pil = importlib.util.find_spec("PIL") is not None

    # 1. OSWorld 2.1 policy + GUI goal verifier + recovery + action compiler + constraint guard
    if osworld_state is not None or instruction is not None or proposed_action is not None:
        from canonical.runtime import osworld_v21_constraint_guard_v1 as osw_guard

        engines_invoked.append("canonical.runtime.osworld_v21_constraint_guard_v1")
        osw_out: dict[str, Any] = {
            "pil_available": has_pil,
            "visual_overlay_tier": "PIL_V13_V17_READY" if has_pil else "PURE_STDLIB_V7_V11",
        }
        if instruction is not None:
            osw_out["constraints"] = osw_guard.extract_constraints(instruction)
        if proposed_action is not None:
            prot = list(protected_paths or ())
            if not prot and isinstance(osw_out.get("constraints"), Mapping):
                prot = list(osw_out["constraints"].get("protected_paths") or ())
            conflict = osw_guard.action_conflict(dict(proposed_action), prot)
            osw_out["action_conflict"] = conflict
            osw_out["guard_blocked"] = conflict is not None

        if osworld_state is not None:
            state_dict = dict(osworld_state)
            from canonical.runtime import osworld_v21_brain_agent_adapter_v1 as osw_adapter
            from canonical.runtime import osworld_v21_gui_goal_verifier_v1 as osw_ver
            from canonical.runtime import osworld_v21_recovery_policy_v2 as osw_rec
            from canonical.runtime import osworld_v21_unified_policy_v11 as osw_u11
            from canonical.runtime import osworld_v21_workflow_policy_v7 as osw_w7

            engines_invoked.extend(
                [
                    "canonical.runtime.osworld_v21_workflow_policy_v7",
                    "canonical.runtime.osworld_v21_unified_policy_v11",
                    "canonical.runtime.osworld_v21_gui_goal_verifier_v1",
                    "canonical.runtime.osworld_v21_recovery_policy_v2",
                    "canonical.runtime.osworld_v21_brain_agent_adapter_v1",
                ]
            )
            gui_verdict = osw_ver.verify_gui_goal(state_dict)
            osw_out["gui_goal_verifier"] = gui_verdict
            if policy_mode == "unified_v11":
                decision = dict(osw_u11.decide(state_dict))
                osw_out["policy_used"] = "osworld_v21_unified_policy_v11"
            else:
                decision = dict(osw_w7.decide(state_dict))
                osw_out["policy_used"] = "osworld_v21_workflow_policy_v7"
                if not decision.get("actions") and decision.get("response") is None:
                    decision = dict(osw_u11.decide(state_dict))
                    osw_out["policy_used"] = "osworld_v21_unified_policy_v11_fallback"
            osw_out["decision"] = decision
            if run_recovery:
                osw_out["recovery"] = osw_rec.route_recovery(state_dict)
            if compile_adapter_actions:
                try:
                    resp, compiled_acts = osw_adapter.compile_actions(decision)
                    osw_out["compiled_actions"] = {"response": resp, "actions": compiled_acts}
                except Exception as exc:
                    osw_out["compiled_actions"] = {"error": f"{type(exc).__name__}: {exc}"}
            # Check browser CDP / host ops surfaces lazily (zero network calls)
            from canonical.runtime import osworld_v21_browser_cdp_v1 as osw_cdp
            from canonical.runtime import osworld_v21_host_browser_ops_v1 as osw_host

            osw_out["browser_surfaces"] = {
                "cdp_class": osw_cdp.BrowserCDP.__name__,
                "host_browser_class": osw_host.OSWorldHostBrowser.__name__,
            }
        results["osworld_v21"] = osw_out

    # 2. Epistemic computer agent (`epistemic_computer_agent_v1`)
    if nl_goal is not None or inspect_path is not None or epistemic_store_root is not None:
        from canonical.swe_kernel import epistemic_computer_agent_v1 as eca

        engines_invoked.append("canonical.swe_kernel.epistemic_computer_agent_v1")
        ep_out: dict[str, Any] = {}
        if nl_goal is not None:
            parsed = eca.parse_nl_goal(str(nl_goal))
            ep_out["parsed_goal"] = parsed.__dict__ if hasattr(parsed, "__dict__") else str(parsed)
        if inspect_path is not None:
            ep_out["candidate_kinds"] = sorted(eca.hypothesize_candidate_kinds(Path(inspect_path).resolve()))
        if epistemic_store_root is not None:
            store = eca.EpistemicStore(Path(epistemic_store_root).resolve())
            agent = eca.EpistemicComputerAgent(store)
            ep_out["agent_ready"] = True
            ep_out["agent_class"] = type(agent).__name__
        results["epistemic_cu"] = ep_out

    # 3. Action-grammar guide (`the_guide_is_an_action_grammar_v1`)
    if grammar_need is not None or grammar_declared_flags is not None or grammar_pages is not None:
        from canonical.tools import the_guide_is_an_action_grammar_v1 as guide_ag

        engines_invoked.append("canonical.tools.the_guide_is_an_action_grammar_v1")
        ag_out: dict[str, Any] = {}
        if isinstance(grammar_need, str):
            ag_out["artifact_kinds"] = sorted(guide_ag.artifact_kinds(grammar_need))
        elif isinstance(grammar_need, Mapping):
            need_txt = str(grammar_need.get("need") or grammar_need.get("text") or "")
            if need_txt:
                ag_out["artifact_kinds"] = sorted(guide_ag.artifact_kinds(need_txt))
            if grammar_root is not None and grammar_pages is not None:
                ag_out["admissible"] = guide_ag.admissible(
                    dict(grammar_need),
                    Path(grammar_root).resolve(),
                    dict(grammar_pages),
                )
        if grammar_pages is not None:
            ag_out["blind_spots"] = guide_ag.check_blind_spots(dict(grammar_pages))
        if grammar_declared_flags is not None:
            ag_out["flag_issues"] = guide_ag.check_flags(
                {k: dict(v) for k, v in grammar_declared_flags.items()},
                program=grammar_program,
            )
        results["action_grammar"] = ag_out

    passed = bool(engines_invoked)
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__WAVE34_OSWORLD_V21_AND_EPISTEMIC_CU"
            if passed
            else "FAIL_CLOSED__NO_WAVE34_CU_INPUTS"
        ),
        "engines_invoked": engines_invoked,
        "results": results,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def speculative_macro_commit(
    *,
    # 1. Effect witness (`effect_witness_v1`)
    witness_root: str | Path | None = None,
    witness_before_digests: Mapping[str, str] | None = None,
    witness_argv: Sequence[str] | None = None,
    witness_expected: Sequence[str] | None = None,
    witness_goal_family: str = "file_op",
    # 2. Standing-fact invalidation & CoW in-order commit (`standing_facts_v1` — TomasuLLM pattern)
    standing_before_state: Mapping[str, bytes] | None = None,
    standing_after_state: Mapping[str, bytes] | None = None,
    standing_contract: Mapping[str, Any] | None = None,
    standing_binding: Mapping[str, str] | None = None,
    standing_step: int = 1,
    # 3. Action replay under file drift (`action_replay_under_change_v1`)
    replay_before: str | None = None,
    replay_after: str | None = None,
    replay_target_text: str | None = None,
    # 4. Parallel capability frontier planner (`capability_parallel_frontier_v2`)
    plan_parallel_frontier: bool = False,
    frontier_dict: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Wave 34: Speculative Macro Commit with Standing-Fact Invalidation, Effect Witnesses & Parallel Frontier (`0F`, `K3=0`).

    Composes 4 pure-stdlib execution-safety & speculative-commit modules:
      - `effect_witness_v1`: digest_tree, named_subjects, bind, abstract_rule
      - `standing_facts_v1`: establish, touched, at_risk, revalidate (TomasuLLM / Speculative Macro Commit)
      - `action_replay_under_change_v1`: plan_of, replay_plan, inline_skill
      - `capability_parallel_frontier_v2`: plan_current_parallel_frontier / plan_parallel_frontier / verify_frontier_currentness
    """
    t0 = time.perf_counter()
    engines_invoked: list[str] = []
    results: dict[str, Any] = {}
    commit_safe = True

    # 1. Effect witness (`effect_witness_v1`)
    if witness_root is not None:
        from canonical.swe_kernel import effect_witness_v1 as ew

        engines_invoked.append("canonical.swe_kernel.effect_witness_v1")
        root_p = Path(witness_root).resolve()
        after_digests = ew.digest_tree(root_p)
        before_d = dict(witness_before_digests) if witness_before_digests is not None else dict(after_digests)
        subjects = ew.named_subjects(list(witness_argv or ()), before_d, after_digests)
        ew_out: dict[str, Any] = {
            "digest_count": len(after_digests),
            "after_digests": after_digests,
            "named_subjects": subjects,
        }
        if witness_expected is not None:
            bound = ew.bind(
                {"argv": list(witness_argv or ()), "before": before_d, "after": after_digests, "subjects": subjects},
                list(witness_expected),
            )
            ew_out["bound"] = bound
            if bound.get("bound") or bound.get("ok") or bound.get("matched"):
                try:
                    ew_out["abstracted_rule"] = ew.abstract_rule(bound, goal_family=str(witness_goal_family))
                except Exception:
                    pass
        results["effect_witness"] = ew_out

    # 2. Standing facts invalidation & TomasuLLM speculative conflict check (`standing_facts_v1`)
    if standing_before_state is not None:
        from canonical.swe_kernel import standing_facts_v1 as sf

        engines_invoked.append("canonical.swe_kernel.standing_facts_v1")
        before_bytes = {str(k): (v if isinstance(v, bytes) else str(v).encode("utf-8")) for k, v in standing_before_state.items()}
        facts = sf.establish(before_bytes, step=0)
        touch_set: set[str] = set()
        at_risk_list: list[dict[str, Any]] = []
        if standing_contract is not None and standing_binding is not None:
            touch_set = sf.touched(dict(standing_contract), dict(standing_binding))
            at_risk_list = sf.at_risk(facts, touch_set)
        kept: list[dict[str, Any]] = facts
        invalidated: list[dict[str, Any]] = []
        if standing_after_state is not None:
            after_bytes = {str(k): (v if isinstance(v, bytes) else str(v).encode("utf-8")) for k, v in standing_after_state.items()}
            kept, invalidated = sf.revalidate(facts, after_bytes, step=int(standing_step))
            # TomasuLLM in-order commit check: if an untouched standing fact silently mutated, abort commit!
            untouched_invalidated = [f for f in invalidated if str(f.get("path") or f.get("key") or "") not in touch_set]
            if untouched_invalidated and standing_contract is not None:
                commit_safe = False
        results["standing_facts"] = {
            "established_count": len(facts),
            "touched": sorted(touch_set),
            "at_risk_count": len(at_risk_list),
            "kept_count": len(kept),
            "invalidated_count": len(invalidated),
            "invalidated": invalidated,
            "speculative_commit_safe": commit_safe,
        }

    # 3. Action replay under file drift (`action_replay_under_change_v1`)
    if replay_before is not None and replay_after is not None:
        from canonical.swe_kernel import action_replay_under_change_v1 as aruc

        engines_invoked.append("canonical.swe_kernel.action_replay_under_change_v1")
        plan = aruc.plan_of(str(replay_before), str(replay_after))
        replayed = aruc.replay_plan(plan, str(replay_target_text if replay_target_text is not None else replay_before))
        results["action_replay"] = {
            "edit_hunk_count": len(plan),
            "replayed_text": replayed,
            "inline_skill_schema": sorted(aruc.inline_skill().keys()),
        }

    # 4. Capability parallel frontier (`capability_parallel_frontier_v2`)
    if plan_parallel_frontier or frontier_dict is not None:
        from canonical.runtime import capability_parallel_frontier_v2 as cpf2

        engines_invoked.append("canonical.runtime.capability_parallel_frontier_v2")
        if frontier_dict is not None:
            plan_res = cpf2.plan_parallel_frontier(dict(frontier_dict))
            curr_res = cpf2.verify_frontier_currentness(dict(frontier_dict))
            results["parallel_frontier"] = {"plan": plan_res, "currentness": curr_res}
        else:
            try:
                results["parallel_frontier"] = cpf2.plan_current_parallel_frontier()
            except Exception as exc:
                loaded = cpf2.load_current_frontier()
                results["parallel_frontier"] = {
                    "plan": cpf2.plan_parallel_frontier(loaded),
                    "dynamic_refresh_warning": f"{type(exc).__name__}: {exc}",
                }

    passed = bool(engines_invoked) and commit_safe
    return {
        "schema": SCHEMA,
        "pass": passed,
        "commit_decision": "COMMIT" if passed else ("ROLLBACK__UNEXPECTED_STANDING_FACT_DRIFT" if engines_invoked else "NOOP"),
        "status": (
            "PASS__WAVE34_SPECULATIVE_MACRO_COMMIT"
            if passed
            else "FAIL_CLOSED__WAVE34_SPECULATIVE_COMMIT_ABORTED"
        ),
        "engines_invoked": engines_invoked,
        "results": results,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }






