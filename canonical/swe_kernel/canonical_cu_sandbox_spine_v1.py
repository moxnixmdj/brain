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
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import value_algebra_v1 as val_alg
from canonical.swe_kernel import interface_action_grammar_v1 as action_grammar
from canonical.swe_kernel import speculative_cow_petri_agent_v1 as scpa
from canonical.swe_kernel import universal_computer_agent_v1 as uca
from canonical.swe_kernel import zygote_worker_pool_v1 as zygote_pool
from canonical.tools import the_failed_attempt_is_free_v1 as free_fail

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

    def _commit_clone(self, clone_root: Path, diff: Mapping[str, Sequence[str]]) -> str:
        """Commit verified clone changes using atomic `renameat2(RENAME_EXCHANGE)` per file when supported."""
        commit_mechanism = "atomic_renameat2_exchange"
        for rel in diff.get("deleted", ()):
            p = self.workspace_root / rel
            if p.exists() and p.is_file():
                p.unlink()
        for rel in list(diff.get("added", ())) + list(diff.get("modified", ())):
            src = clone_root / rel
            dst = self.workspace_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            staged = dst.parent / f".cow_stage_{dst.name}_{time.time_ns()}"
            shutil.copy2(src, staged)
            try:
                if dst.exists():
                    free_fail.exchange(dst, staged)
                    staged.unlink(missing_ok=True)
                else:
                    staged.replace(dst)
            except Exception:
                commit_mechanism = "posix_replace_fallback"
                staged.replace(dst)
        return commit_mechanism

    def evaluate_cow_zygote_batch(
        self,
        cow_candidates: Sequence[tuple[str, Callable[[], tuple[bool, Any]]]],
        *,
        max_parallel: int = 4,
        per_worker_timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        """Zero-disk `os.fork()` CoW parallel candidate screening via `ZygotePrewarmedPool.run_parallel_sharded`."""
        t0 = time.perf_counter()
        pool = zygote_pool.ZygotePrewarmedPool(prewarm_enabled=False)
        all_results: list[dict[str, Any]] = []
        winner_id: str | None = None
        winner_payload: Any = None
        forked_count = 0
        cancelled_count = 0

        items = list(cow_candidates)
        if not items:
            return {
                "passed": False,
                "winner_id": None,
                "winner_payload": None,
                "forked_count": 0,
                "cancelled_count": 0,
                "elapsed_ms": 0.0,
                "results": [],
                "execution_engine": "ZygotePrewarmedPool_os_fork_CoW",
            }

        # Partition `items` across `num_workers` (`<= cpu_count`) CoW worker shards so we pay
        # kernel `os.fork()` page-table clone only `num_workers` times instead of `len(items)` times!
        num_workers = min(len(items), max(1, min(int(max_parallel), os.cpu_count() or 4)))
        worker_buckets: list[list[tuple[str, Callable[[], tuple[bool, Any]]]]] = [
            items[w_idx::num_workers] for w_idx in range(num_workers)
        ]

        shard_fns: list[Callable[[], Mapping[str, Any]]] = []
        for bucket in worker_buckets:
            def _make_bucket_shard(
                b_items: list[tuple[str, Callable[[], tuple[bool, Any]]]] = bucket,
            ) -> Callable[[], Mapping[str, Any]]:
                def _shard() -> Mapping[str, Any]:
                    sub_rows: list[dict[str, Any]] = []
                    for c_id, fn in b_items:
                        ts = time.perf_counter()
                        try:
                            ok, payload = fn()
                            err = None
                        except BaseException as exc:  # noqa: BLE001
                            ok, payload, err = False, None, f"{type(exc).__name__}:{exc}"
                        row = {
                            "candidate_id": c_id,
                            "passed": bool(ok),
                            "payload": payload,
                            "error": err,
                            "elapsed_ms": round((time.perf_counter() - ts) * 1000.0, 3),
                        }
                        sub_rows.append(row)
                        if ok:
                            return {
                                "passed": True,
                                "candidate_id": c_id,
                                "payload": payload,
                                "sub_results": sub_rows,
                            }
                    return {"passed": False, "candidate_id": None, "payload": None, "sub_results": sub_rows}

                return _shard

            shard_fns.append(_make_bucket_shard())

        forked_count = len(shard_fns)
        res = pool.run_parallel_sharded(
            shard_fns,
            winner_predicate=lambda item: bool(item.get("passed")),
            timeout_s=per_worker_timeout_s,
        )
        cancelled_count = int(res.get("siblings_cancelled", 0))
        for item in res.get("results", ()):
            for sr in item.get("sub_results") or ():
                all_results.append(dict(sr))
        if res.get("found_winner") and res.get("winner"):
            win_item = res["winner"]
            winner_id = str(win_item.get("candidate_id"))
            winner_payload = win_item.get("payload")

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        return {
            "passed": winner_id is not None,
            "winner_id": winner_id,
            "winner_payload": winner_payload,
            "forked_count": forked_count,
            "cancelled_count": cancelled_count,
            "elapsed_ms": elapsed_ms,
            "results": all_results,
            "execution_engine": "ZygotePrewarmedPool_os_fork_CoW",
        }

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
        """Speculatively evaluate candidates using a single reusable CoW staging workspace
        with O(|diff|) microsecond rollback + `ZygotePrewarmedPool` `os.fork()` screening
        for pure `cow_fn` candidates + `renameat2(RENAME_EXCHANGE)` atomic commit."""
        pre_digest, pre_hashes = workspace_tree_digest(self.workspace_root)
        pre_tomo = scpa.capture_tomography_snapshot(self.workspace_root)
        allowed_set = {str(p).lstrip("./") for p in allowed_write_paths}

        probe_results: list[SpeculativeProbeResult] = []
        winner_id: str | None = None
        committed = False
        commit_mechanism = "none"

        # Fast Lane 0: If all candidates provide zero-disk `cow_fn` callables, screen in parallel via `os.fork()` CoW!
        if candidates and all(callable(c.get("cow_fn")) and not c.get("write_files") and not c.get("fn") and not c.get("argv") for c in candidates):
            batch = [
                (str(c.get("id") or f"cand_{i}"), c["cow_fn"])
                for i, c in enumerate(candidates)
            ]
            cow_res = self.evaluate_cow_zygote_batch(batch, per_worker_timeout_s=timeout_s)
            winner_id = cow_res["winner_id"]
            for row in cow_res["results"]:
                probe_results.append(
                    SpeculativeProbeResult(
                        candidate_id=str(row["candidate_id"]),
                        passed=bool(row["passed"]),
                        committed=False,
                        returncode=0 if row["passed"] else 1,
                        stdout="",
                        stderr=str(row.get("error") or ""),
                        elapsed_ms=float(row.get("elapsed_ms") or 0.0),
                        diff={"added": [], "modified": [], "deleted": []},
                        negative_effect_ok=True,
                        rejection_reason=row.get("error") if not row["passed"] else None,
                        tomography_diff={},
                    )
                )
            return {
                "passed": winner_id is not None,
                "winner_id": winner_id,
                "winner_payload": cow_res["winner_payload"],
                "committed": False,
                "commit_mechanism": "zero_disk_cow_fork",
                "pre_digest": pre_digest,
                "post_digest": pre_digest,
                "workspace_preserved_on_failure": True,
                "probes": [p.as_dict() for p in probe_results],
            }

        # Fast Lane 1: Single reusable staging clone + O(|diff|) rollback (deletes K-1 `shutil.copytree` calls!)
        # Snapshot baseline bytes once in RAM so failed candidates revert ONLY touched files in microseconds.
        baseline_bytes: dict[str, bytes] = {
            rel: (self.workspace_root / rel).read_bytes()
            for rel in pre_hashes
            if (self.workspace_root / rel).is_file()
        }

        with tempfile.TemporaryDirectory(prefix="brain_cow_stage_") as tmp_dir:
            clone = Path(tmp_dir) / "ws"
            self._copy_to_clone(clone)
            clone_before_snap = uca.snapshot_workspace_files(clone)

            for idx, cand in enumerate(candidates):
                cid = str(cand.get("id") or f"cand_{idx}")
                t0 = time.perf_counter()

                rc: int | None = 0
                stdout = ""
                stderr = ""
                exec_err: str | None = None
                fast_write_only = False
                written_rels: list[str] = []

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
                        fast_write_only = True
                        for rel, content in cand["write_files"].items():
                            norm_rel = str(rel).lstrip("./")
                            written_rels.append(norm_rel)
                            target = clone / norm_rel
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

                if fast_write_only:
                    # O(|write_files|) incremental hash diff instead of O(|workspace|) full directory rescan!
                    added = sorted(r for r in written_rels if r not in pre_hashes)
                    modified = sorted(
                        r for r in written_rels
                        if r in pre_hashes
                        and hashlib.sha256((clone / r).read_bytes()).hexdigest() != pre_hashes[r]
                    )
                    diff = {"added": added, "modified": modified, "deleted": []}
                    tomo_diff: dict[str, Any] = {"fast_overlay_paths": written_rels}
                    neg_oracle: Mapping[str, Any] = {}
                else:
                    _, clone_after_hashes = workspace_tree_digest(clone)
                    clone_after_snap = uca.snapshot_workspace_files(clone)
                    clone_after_tomo = scpa.capture_tomography_snapshot(clone)
                    diff = diff_file_hashes(pre_hashes, clone_after_hashes)
                    tomo_diff = scpa.diff_tomography(pre_tomo, clone_after_tomo)
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
                        commit_mechanism = self._commit_clone(clone, diff)
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

                # O(|diff|) microsecond rollback of `clone` back to exact `pre_hashes` state!
                for rel in diff["added"]:
                    (clone / rel).unlink(missing_ok=True)
                for rel in diff["modified"] + diff["deleted"]:
                    if rel in baseline_bytes:
                        dst_p = clone / rel
                        dst_p.parent.mkdir(parents=True, exist_ok=True)
                        dst_p.write_bytes(baseline_bytes[rel])

        post_digest, _ = workspace_tree_digest(self.workspace_root)
        workspace_preserved_on_failure = (winner_id is None and post_digest == pre_digest)
        return {
            "passed": winner_id is not None,
            "winner_id": winner_id,
            "committed": committed,
            "commit_mechanism": commit_mechanism,
            "pre_digest": pre_digest,
            "post_digest": post_digest,
            "workspace_preserved_on_failure": workspace_preserved_on_failure,
            "probes": [p.as_dict() for p in probe_results],
        }


def execute_speculative_computer_task(
    *,
    workspace_root: str | Path | None = None,
    candidates: Sequence[Mapping[str, Any]] = (),
    cow_python_candidates: Sequence[tuple[str, Callable[[], tuple[bool, Any]]]] = (),
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

    # Route 1A.0 (Zero-Disk Parallel `os.fork()` CoW Python Candidate Screening via `ZygotePrewarmedPool`)
    if cow_python_candidates:
        report["modules_invoked"].append("canonical.swe_kernel.zygote_worker_pool_v1:screen_python_candidates_cow")
        sb_root = Path(workspace_root) if workspace_root is not None else Path.cwd()
        cow_batch_out = SpeculativeSandbox(sb_root).evaluate_cow_zygote_batch(
            cow_python_candidates,
            per_worker_timeout_s=timeout_s,
        )
        report["cow_zygote_result"] = cow_batch_out
        if cow_batch_out["passed"]:
            report["route_selected"] = "ZYGOTE_OS_FORK_COW_PARALLEL_POOL"
            report["pass"] = True
            report["status"] = "PASS__ZYGOTE_COW_VERIFIED"
            report["reason"] = None
            return report

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


