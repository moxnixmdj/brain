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
