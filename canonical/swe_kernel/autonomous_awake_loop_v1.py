#!/usr/bin/env python3
"""Continuous Zero-LLM Awake Agency Loop (`autonomous_awake_loop_v1`).

Unites the repository's isolated perception, ignorance, curriculum, rule-expiry,
and skill-compilation organs into a single self-driven zero-LLM (`K3 = 0`, `$0` spend)
loop (`SENSE -> NOTICE IGNORANCE -> RANK VALUE/COST -> CO-W EXPERIMENT -> QUALIFY -> REMEMBER`):

  1. `discover_v1` + `environment_fit_v1` — reads binaries, entrypoints, runnable commands,
     and unfulfilled declarations directly off any workspace without waiting for a prompt.
  2. `rule_expiry_v1` — audits `VerifiedSkillStore` rules against live tool/file/platform
     state so drifted (`STALE`) rules are surfaced as open epistemic gaps.
  3. `ignorance_ledger_v1` — ranks every noticed gap by `p_useful / (1 + cost)`.
  4. Isolated Copy-on-Write workspace experimentation — clones target code/tests into an
     ephemeral sandbox, repairs failing modules via `VerifiedSkillStore` recall (including
     `SCOPE_ALGEBRAIC` E-Graph saturation) or deterministic AST operator/boundary synthesis,
     verifies against real test execution, and crystallizes new generalizable rules with
     twin-oracle qualification + `rule_expiry_v1` environment fingerprints.
  5. `curriculum_v1` -> `causal_trace_to_skill_compiler_v1` — promotes newly closed gaps
     directly into live `BRAIN_COMPILED_WORKFLOW_DB` via auto-twin (`N=1 -> N=2`) qualification
     so subsequent goals resolve in `< 5 ms` from Tier-0 memory.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import curriculum_v1 as cur
from canonical.runtime import discover_v1 as disc
from canonical.runtime import environment_fit_v1 as env_fit
from canonical.runtime import ignorance_ledger_v1 as ledger
from canonical.swe_kernel import rule_expiry_v1 as rule_exp
from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
    compile_and_qualify_skill,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_AWAKE_LOOP_V1"

_AST_BINOP_SWAPS: dict[type[ast.operator], tuple[type[ast.operator], ...]] = {
    ast.Add: (ast.Sub, ast.Mult),
    ast.Sub: (ast.Add,),
    ast.Mult: (ast.Add, ast.FloorDiv, ast.Div),
    ast.Div: (ast.FloorDiv, ast.Mult),
    ast.FloorDiv: (ast.Div, ast.Mult),
}

_AST_CMPOP_SWAPS: dict[type[ast.cmpop], tuple[type[ast.cmpop], ...]] = {
    ast.Lt: (ast.LtE, ast.Gt, ast.GtE),
    ast.LtE: (ast.Lt, ast.GtE, ast.Gt),
    ast.Gt: (ast.GtE, ast.Lt, ast.LtE),
    ast.GtE: (ast.Gt, ast.LtE, ast.Lt),
    ast.Eq: (ast.NotEq,),
    ast.NotEq: (ast.Eq,),
}


def promote_closed_lesson_to_workflow_db(
    gap_text: str,
    closed_by: str | None,
    attempts: Sequence[Mapping[str, Any]],
    *,
    db_path: pathlib.Path | None = None,
    source_cwd: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Compile a verified curriculum closure into permanent `BRAIN_COMPILED_WORKFLOW_DB`."""
    if not closed_by:
        return {"promoted": False, "reason": "GAP_NOT_CLOSED"}
    winning = next((a for a in attempts if a.get("channel") == closed_by and a.get("closed")), None)
    if winning is None:
        return {"promoted": False, "reason": "NO_WINNING_ATTEMPT_RECORD"}

    cwd = pathlib.Path(source_cwd or os.getcwd()).resolve()
    target_db = pathlib.Path(db_path) if db_path else None

    # Extract concrete file-creation or CLI command evidence when present
    cmd = winning.get("command") or winning.get("cmd")
    out_path = winning.get("output_path") or winning.get("path")
    if isinstance(cmd, (list, str)) and out_path:
        p_abs = pathlib.Path(str(out_path))
        if not p_abs.is_absolute():
            p_abs = (cwd / p_abs).resolve()
        if p_abs.is_file():
            rel_or_abs = str(out_path)
            argv = cmd if isinstance(cmd, list) else ["sh", "-c", str(cmd)]
            qual = compile_and_qualify_skill(
                goal=gap_text,
                trace=[{"layer": "cli_exec", "argv": list(argv), "returncode": 0}],
                postcondition={"kind": "file_nonempty", "path": rel_or_abs},
                auto_synthesize_twin=True,
                source_cwd=cwd,
                source_channel=f"awake_curriculum:{closed_by}",
                db_path=target_db,
            )
            return {
                "promoted": bool(qual.get("pass")),
                "skill_id": qual.get("skill_id"),
                "status": qual.get("status"),
            }
    return {"promoted": False, "reason": "NO_PROMOTABLE_TRACE_ARTIFACT"}


def _propose_deterministic_ast_repairs(source_text: str, max_candidates: int = 24) -> list[str]:
    """Generate small, syntactically valid single-site operator/comparison repairs (`K3 = 0`)."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []

    lines = source_text.splitlines(keepends=True)
    offsets = [0]
    for ln in lines:
        offsets.append(offsets[-1] + len(ln))

    def _span(nd: ast.AST) -> tuple[int, int] | None:
        l0, c0 = getattr(nd, "lineno", None), getattr(nd, "col_offset", None)
        l1, c1 = getattr(nd, "end_lineno", None), getattr(nd, "end_col_offset", None)
        if None in (l0, c0, l1, c1):
            return None
        s_b = lines[l0 - 1].encode("utf-8")
        e_b = lines[l1 - 1].encode("utf-8")
        return (
            offsets[l0 - 1] + len(s_b[:c0].decode("utf-8", errors="replace")),
            offsets[l1 - 1] + len(e_b[:c1].decode("utf-8", errors="replace")),
        )

    out: list[str] = []
    seen: set[str] = {source_text}
    import copy

    for nd in ast.walk(tree):
        sp = _span(nd)
        if sp is None:
            continue
        s_i, e_i = sp
        if isinstance(nd, ast.BinOp) and type(nd.op) in _AST_BINOP_SWAPS:
            for alt_op in _AST_BINOP_SWAPS[type(nd.op)]:
                dup = copy.deepcopy(nd)
                dup.op = alt_op()
                repl = ast.unparse(dup)
                for wrapped in (repl, f"({repl})"):
                    cand = source_text[:s_i] + wrapped + source_text[e_i:]
                    if cand not in seen:
                        try:
                            ast.parse(cand)
                            seen.add(cand)
                            out.append(cand)
                            break
                        except SyntaxError:
                            continue
        elif isinstance(nd, ast.Compare) and len(nd.ops) == 1 and type(nd.ops[0]) in _AST_CMPOP_SWAPS:
            for alt_cmp in _AST_CMPOP_SWAPS[type(nd.ops[0])]:
                dup = copy.deepcopy(nd)
                dup.ops = [alt_cmp()]
                repl = ast.unparse(dup)
                cand = source_text[:s_i] + repl + source_text[e_i:]
                if cand not in seen:
                    try:
                        ast.parse(cand)
                        seen.add(cand)
                        out.append(cand)
                    except SyntaxError:
                        continue
        if len(out) >= max_candidates:
            break
    return out


def _atomic_write_text(dest: pathlib.Path, content: str) -> None:
    """Atomically write UTF-8 text via sibling temporary file + fsync + os.replace."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=dest.parent,
            prefix=".brain-awake-",
            delete=False,
        ) as handle:
            tmp_name = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, dest)
        tmp_name = None
    finally:
        if tmp_name is not None:
            pathlib.Path(tmp_name).unlink(missing_ok=True)


def _run_py_test_file(test_file: pathlib.Path, cwd: pathlib.Path, timeout: float = 8.0) -> tuple[bool, str]:
    """Execute a Python test file inside staged zero-ambient namespace confinement (`brokered_workspace_execution_v1`)."""
    from canonical.runtime import brokered_workspace_execution_v1 as broker
    from canonical.runtime import computer_execution_boundary_v1 as boundary

    cwd_res = cwd.resolve()
    tf_res = test_file.resolve()
    rel_tf = tf_res.relative_to(cwd_res).as_posix()
    txt = tf_res.read_text(encoding="utf-8", errors="replace")
    needs_pytest = ("import pytest" in txt or "from pytest" in txt) or (cwd_res / "conftest.py").is_file()
    if not needs_pytest:
        fast = broker.run_confined_python_candidate_batch(
            cwd_res,
            "",
            [rel_tf],
            [{}],
            stop_on_first_pass=True,
            per_candidate_timeout_s=min(2.5, max(0.5, float(timeout))),
            allow_cow_hardlinks=True,
        )
        if fast.get("ok") and fast.get("confined") and 0 in (fast.get("passing_indices") or []):
            return True, ""

    if "def test_" in txt and "__main__" not in txt:
        cmd = [sys.executable, "-B", "-m", "pytest", "-q", "--tb=short", rel_tf]
    else:
        cmd = [sys.executable, "-B", rel_tf]
    res = broker.run_staged_confined_command(
        cwd_res,
        cmd,
        publish=False,
        allow_cow_hardlinks=True,
        pythonpath_work=True,
        timeout=max(4, int(round(timeout))),
        task_id=f"awake-test:{rel_tf}",
        goal=f"run sandbox test {rel_tf}",
    )
    if not res.get("confined"):
        return False, str(res.get("blocked") or boundary.STATUS)
    if res.get("timed_out"):
        return False, "TIMEOUT"
    combined = (str(res.get("stdout") or "")) + "\n" + (str(res.get("stderr") or ""))
    return bool(res.get("ok")), combined[-600:]


_POLYGLOT_EXT_TO_LANG: dict[str, str] = {
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
}


def _is_polyglot_test_filename(fn: str) -> bool:
    return (
        (fn.endswith(".js") and (fn.startswith("test_") or fn.endswith(".test.js") or fn.endswith("_test.js")))
        or fn.endswith("_test.go")
        or (fn.endswith(".rs") and (fn.startswith("test_") or fn.endswith("_test.rs")))
    )


def _run_polyglot_test_file(test_file: pathlib.Path, cwd: pathlib.Path, timeout: float = 8.0) -> tuple[bool, str]:
    """Execute a JS / Go / Rust test file inside zero-ambient namespace confinement (`brokered_workspace_execution_v1`)."""
    import shutil as _shutil
    from canonical.runtime import brokered_workspace_execution_v1 as broker
    from canonical.runtime import computer_execution_boundary_v1 as boundary

    cwd_res = cwd.resolve()
    tf_res = test_file.resolve()
    rel_tf = tf_res.relative_to(cwd_res).as_posix()
    suf = tf_res.suffix.lower()
    if suf == ".js":
        node_bin = _shutil.which("node")
        if not node_bin:
            return False, "NODE_RUNTIME_MISSING"
        cmd = [node_bin, rel_tf]
    elif suf == ".go":
        go_bin = _shutil.which("go")
        if not go_bin:
            return False, "GO_RUNTIME_MISSING"
        cmd = [go_bin, "test", "./" + pathlib.PurePosixPath(rel_tf).parent.as_posix()]
    elif suf == ".rs":
        rustc_bin = _shutil.which("rustc")
        if not rustc_bin:
            return False, "RUSTC_RUNTIME_MISSING"
        cmd = [rustc_bin, "--test", rel_tf, "-o", "/tmp/rust_test_bin"]
    else:
        return False, f"UNSUPPORTED_TEST_EXT:{suf}"

    res = broker.run_staged_confined_command(
        cwd_res,
        cmd,
        publish=False,
        allow_cow_hardlinks=True,
        timeout=max(4, int(round(timeout))),
        task_id=f"awake-poly-test:{rel_tf}",
        goal=f"run confined polyglot test {rel_tf}",
    )
    if not res.get("confined"):
        return False, str(res.get("blocked") or boundary.STATUS)
    if res.get("timed_out"):
        return False, "TIMEOUT"
    combined = (str(res.get("stdout") or "")) + "\n" + (str(res.get("stderr") or ""))
    if suf == ".rs" and res.get("ok"):
        # Compile + run in one confined sh invocation if rustc succeeded
        sh_bin = _shutil.which("sh") or "/bin/sh"
        res2 = broker.run_staged_confined_command(
            cwd_res,
            [sh_bin, "-c", f'"{rustc_bin}" --test "{rel_tf}" -o /tmp/rust_t && /tmp/rust_t'],
            publish=False,
            allow_cow_hardlinks=True,
            timeout=max(4, int(round(timeout))),
            task_id=f"awake-rust-exec:{rel_tf}",
            goal=f"run confined rust test {rel_tf}",
        )
        combined2 = (str(res2.get("stdout") or "")) + "\n" + (str(res2.get("stderr") or ""))
        return bool(res2.get("ok")), combined2[-600:]
    return bool(res.get("ok")), combined[-600:]


class ConfinedLanguageTestOracle:
    """Callable test-suite verifier running candidate patches inside `brokered_workspace_execution_v1` confinement."""

    def __init__(self, cow_root: pathlib.Path, target_mod: pathlib.Path, test_file: pathlib.Path) -> None:
        self.cow_root = cow_root.resolve()
        self.target_mod = target_mod.resolve()
        self.test_file = test_file.resolve()

    def __call__(self, candidate_source: str) -> bool:
        from canonical.swe_kernel.cow_impact_repair_engine_v1 import cow_write_text

        orig = self.target_mod.read_text(encoding="utf-8")
        try:
            cow_write_text(self.target_mod, candidate_source)
            if self.test_file.suffix.lower() == ".py":
                ok, _ = _run_py_test_file(self.test_file, self.cow_root)
            else:
                ok, _ = _run_polyglot_test_file(self.test_file, self.cow_root)
            return ok
        finally:
            cow_write_text(self.target_mod, orig)


def _build_twin_callable_oracle(
    test_source: str,
    target_stem: str,
    orig_source: str = "",
) -> Callable[[str], bool]:
    """Construct a confined Zygote twin oracle resilient to `crystallize_code_fix` identifier alpha-renaming (zero host `exec()`)."""
    from canonical.runtime import brokered_workspace_execution_v1 as broker

    orig_fn_order: list[str] = []
    try:
        for nd in ast.parse(orig_source).body:
            if isinstance(nd, ast.FunctionDef):
                orig_fn_order.append(nd.name)
    except SyntaxError:
        pass

    base_dir = pathlib.Path(tempfile.mkdtemp(prefix=f"brain-twin-oracle-{target_stem}-"))
    rel_mod = f"{target_stem}.py"
    rel_tf = f"test_{target_stem}.py"
    (base_dir / rel_mod).write_text(orig_source or "pass\n", encoding="utf-8")
    (base_dir / rel_tf).write_text(test_source, encoding="utf-8")

    def _oracle(candidate_code: str) -> bool:
        try:
            cand_tree = ast.parse(candidate_code)
        except SyntaxError:
            return False
        cand_fns = [nd.name for nd in cand_tree.body if isinstance(nd, ast.FunctionDef)]
        alias_lines: list[str] = []
        if len(cand_fns) == len(orig_fn_order):
            for old_nm, new_nm in zip(orig_fn_order, cand_fns):
                if old_nm != new_nm:
                    alias_lines.append(f"{old_nm} = {new_nm}")
        effective_src = candidate_code + ("\n" + "\n".join(alias_lines) + "\n" if alias_lines else "")
        res = broker.run_confined_python_candidate_batch(
            base_dir,
            rel_mod,
            [rel_tf],
            [{rel_mod: effective_src}],
            stop_on_first_pass=True,
            per_candidate_timeout_s=1.5,
            allow_cow_hardlinks=True,
        )
        return bool(res.get("ok") and res.get("confined") and (0 in (res.get("passing_indices") or [])))

    return _oracle


class FileAtomicJournalStore:
    """Create-once (`O_CREAT | O_EXCL`) atomic store satisfying `terminal_causal_journal_v2.AtomicStore`."""

    def __init__(self, journal_dir: str | pathlib.Path) -> None:
        self.root = pathlib.Path(journal_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str) -> pathlib.Path:
        import hashlib

        safe = hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json"
        return self.root / safe

    def create(self, key: str, value: dict[str, Any]) -> bool:
        import json

        target = self._path_for_key(key)
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        try:
            fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return False
        try:
            os.write(fd, raw)
            os.fsync(fd)
        finally:
            os.close(fd)
        return True

    def read(self, key: str) -> dict[str, Any] | None:
        import json

        target = self._path_for_key(key)
        if not target.is_file():
            return None
        return json.loads(target.read_text(encoding="utf-8"))


class AwakeAgencyDaemon:
    """Self-driven zero-LLM awake loop (`K3 = 0`) with crash-resumable hash-chained causal continuity."""

    def __init__(
        self,
        workspace_root: str | pathlib.Path,
        *,
        ledger_path: str | pathlib.Path | None = None,
        skill_store_path: str | pathlib.Path | None = None,
        workflow_db_path: str | pathlib.Path | None = None,
        journal_dir: str | pathlib.Path | None = None,
        r3_state_path: str | pathlib.Path | None = None,
        logical_attempt_id: str | None = None,
        apply_verified_repairs: bool = False,
        creature_root: str | pathlib.Path | None = None,
        creature_identity: str = "creature",
        creature_life: float = 40.0,
    ) -> None:
        import hashlib
        from canonical.runtime import creature_runtime_v1 as cr

        self.workspace_root = pathlib.Path(workspace_root).resolve()
        ws_hash = hashlib.sha256(str(self.workspace_root).encode("utf-8")).hexdigest()[:12]
        self.ledger_path = str(ledger_path) if ledger_path else ledger.DEFAULT_STATE
        self.skill_store = VerifiedSkillStore(
            pathlib.Path(skill_store_path) if skill_store_path else None,
            seed=skill_store_path is None,
        )
        self.workflow_db_path = (
            pathlib.Path(workflow_db_path) if workflow_db_path else None
        )
        if r3_state_path is not None:
            self.r3_state_path = pathlib.Path(r3_state_path).resolve()
        elif journal_dir is not None:
            self.r3_state_path = (pathlib.Path(journal_dir).resolve() / "r3_improvement_state.json")
        elif ledger_path is not None:
            self.r3_state_path = (pathlib.Path(ledger_path).resolve().parent / "r3_improvement_state.json")
        else:
            self.r3_state_path = pathlib.Path(tempfile.gettempdir()) / f"brain_awake_r3_{ws_hash}.json"
        if creature_root is not None:
            c_dir = pathlib.Path(creature_root).resolve()
        elif journal_dir is not None:
            c_dir = pathlib.Path(journal_dir).resolve() / "creature"
        elif ledger_path is not None:
            c_dir = pathlib.Path(ledger_path).resolve().parent / f"creature_{ws_hash}"
        else:
            c_dir = pathlib.Path(tempfile.gettempdir()) / f"brain_creature_{ws_hash}"
        self.creature = cr.boot(c_dir, identity=creature_identity, life=creature_life)
        self.cognitive_core = self.creature.cognitive_core
        self._isolated_state_dir = c_dir if (ledger_path is not None or journal_dir is not None or creature_root is not None) else None
        self._r3_explicit = r3_state_path is not None
        self._converged_r3_digests: set[str] = set()
        self._test_health_cache_path = c_dir / "awake_test_health.json"
        self._file_sha_memo: dict[str, tuple[int, int, str]] = {}
        self._test_health_cache: dict[str, dict[str, Any]] = self._load_test_health_cache()
        self._cached_env_sense: tuple[tuple[str, int], dict[str, Any], dict[str, Any]] | None = None
        self.apply_verified_repairs = bool(apply_verified_repairs)
        self.cycle_count = 0
        self.history: list[dict[str, Any]] = []
        self.strategy_episodes: list[dict[str, Any]] = []
        self.verified_strategies: list[dict[str, Any]] = []
        self._seen_strategy_ids: set[str] = set()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Authenticated crash-resumable continuity (`terminal_causal_journal_v2`)
        seed_id = str(logical_attempt_id or f"awake:{self.workspace_root}")
        self.logical_attempt_id = (
            seed_id
            if re.fullmatch(r"[0-9a-f]{64}", seed_id)
            else hashlib.sha256(seed_id.encode("utf-8")).hexdigest()
        )
        self._journal_store = FileAtomicJournalStore(journal_dir) if journal_dir is not None else None
        self._journal_prefix: list[dict[str, Any]] = []
        self.committed_action_ids: dict[str, dict[str, Any]] = {}
        self._registered_chases: dict[str, dict[str, Any]] = {}
        self._registered_trajectories: dict[str, dict[str, Any]] = {}
        if self._journal_store is not None:
            from execution_guard import terminal_causal_journal_v2 as tcj

            self._journal_prefix = tcj.recover_prefix(self._journal_store, self.logical_attempt_id)
            for ev in self._journal_prefix:
                if ev.get("kind") == "ACTION_VERIFY_STATE_COMMIT":
                    pl = ev.get("payload") or {}
                    aid = str(pl.get("action_id") or "")
                    if aid:
                        self.committed_action_ids[aid] = dict(pl)
                    if "cycle" in pl:
                        self.cycle_count = max(self.cycle_count, int(pl["cycle"]))

    def _append_journal_event(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any] | None:
        if self._journal_store is None:
            return None
        from execution_guard import terminal_causal_journal_v2 as tcj

        ev = tcj.next_event(
            self._journal_prefix,
            logical_attempt_id=self.logical_attempt_id,
            kind=kind,
            payload=dict(payload),
        )
        receipt = tcj.append_once(self._journal_store, ev)
        self._journal_prefix.append(ev)
        return receipt

    def execute_journaled_action(
        self,
        action_id: str,
        intent_payload: Mapping[str, Any],
        action_fn: Callable[[pathlib.Path], Mapping[str, Any]],
        *,
        verify_fn: Callable[[pathlib.Path, Mapping[str, Any]], bool] | None = None,
    ) -> dict[str, Any]:
        """Execute `action_fn` transactionally with crash-resumable `terminal_causal_journal_v2` idempotency."""
        from canonical.swe_kernel.transactional_parallel_execution_v1 import (
            execute_transactional_cow_action,
        )

        aid = str(action_id).strip()
        if aid in self.committed_action_ids:
            return {
                "schema": SCHEMA + "/journaled_action",
                "action_id": aid,
                "committed": True,
                "replayed_from_journal": True,
                "executed_live": False,
                "prior_commit_payload": self.committed_action_ids[aid],
            }

        self._append_journal_event(
            "PLANNER_PROPOSAL_ACTION_INTENT",
            {"action_id": aid, "intent": dict(intent_payload)},
        )
        tx = execute_transactional_cow_action(
            self.workspace_root,
            action_fn,
            verify_fn=verify_fn,
        )
        if not tx.get("committed"):
            self._append_journal_event(
                "PLANNER_CANDIDATE_REJECTED",
                {
                    "action_id": aid,
                    "rolled_back": True,
                    "zero_byte_drift_verified": bool(tx.get("zero_byte_drift_verified")),
                    "reason": str(tx.get("error") or "VERIFICATION_FAILED"),
                },
            )
            return {
                "schema": SCHEMA + "/journaled_action",
                "action_id": aid,
                "committed": False,
                "replayed_from_journal": False,
                "executed_live": True,
                "transaction": tx,
            }

        commit_payload = {
            "action_id": aid,
            "post_manifest_sha256": tx["post_manifest_sha256"],
            "files_updated": tx["files_updated"],
        }
        receipt = self._append_journal_event("ACTION_VERIFY_STATE_COMMIT", commit_payload)
        self.committed_action_ids[aid] = commit_payload
        return {
            "schema": SCHEMA + "/journaled_action",
            "action_id": aid,
            "committed": True,
            "replayed_from_journal": False,
            "executed_live": True,
            "journal_receipt": receipt,
            "transaction": tx,
        }

    def _load_test_health_cache(self) -> dict[str, dict[str, Any]]:
        import json
        from canonical.runtime.memory_policy_v1 import can_read_memory

        if not can_read_memory() or not self._test_health_cache_path.is_file():
            return {}
        try:
            raw = json.loads(self._test_health_cache_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return {str(k): dict(v) for k, v in raw.items() if isinstance(v, Mapping)}
        except Exception:
            pass
        return {}

    def _save_test_health_cache(self) -> None:
        import json
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory():
            return
        try:
            self._test_health_cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._test_health_cache_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._test_health_cache, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self._test_health_cache_path)
        except Exception:
            pass

    def _fast_file_sha256(self, fp: pathlib.Path) -> str:
        import hashlib

        st = fp.stat()
        key = str(fp)
        hit = self._file_sha_memo.get(key)
        if hit is not None and hit[0] == st.st_mtime_ns and hit[1] == st.st_size:
            return hit[2]
        digest = hashlib.sha256(fp.read_bytes()).hexdigest()
        self._file_sha_memo[key] = (int(st.st_mtime_ns), int(st.st_size), digest)
        return digest

    def _sense_failing_workspace_tests(self) -> list[tuple[str, str]]:
        """Incrementally sense failing `test_*.py` pairs via `(mtime_ns, size) -> sha256` memoization (`< 1 ms` warm)."""
        import hashlib

        if not self.workspace_root.is_dir():
            return []
        test_files: list[pathlib.Path] = []
        poly_tests: list[pathlib.Path] = []
        src_files: list[pathlib.Path] = []
        root_str = str(self.workspace_root)
        for dirpath, dirnames, filenames in os.walk(root_str):
            dirnames[:] = [
                d for d in dirnames
                if d not in {".git", "__pycache__", "node_modules", ".pytest_cache", ".mypy_cache", ".venv"}
            ]
            for fn in sorted(filenames):
                fp = pathlib.Path(dirpath) / fn
                if fn.endswith((".py", ".js", ".ts", ".go", ".rs")) and len(src_files) < 40:
                    src_files.append(fp)
                if fn.endswith(".py") and fn.startswith("test_") and len(test_files) < 12:
                    test_files.append(fp)
                elif _is_polyglot_test_filename(fn) and len(poly_tests) < 8:
                    poly_tests.append(fp)
        test_files.sort()
        poly_tests.sort()
        src_files.sort()
        if not test_files and not poly_tests:
            return []

        tree_h = hashlib.sha256()
        for pf in src_files:
            rel_pf = pf.relative_to(self.workspace_root).as_posix()
            tree_h.update(f"{rel_pf}:{self._fast_file_sha256(pf)}\n".encode("utf-8"))
        tree_sig = tree_h.hexdigest()

        failing: list[tuple[str, str]] = []
        dirty = False
        for tf in test_files:
            rel_tf = tf.relative_to(self.workspace_root).as_posix()
            sig = hashlib.sha256(f"{rel_tf}:{tree_sig}".encode("utf-8")).hexdigest()
            cached = self._test_health_cache.get(rel_tf)
            if isinstance(cached, Mapping) and cached.get("sig") == sig and isinstance(cached.get("passing"), bool):
                ok = bool(cached["passing"])
            else:
                ok = False
                ran_fast = False
                target_stem = tf.stem[len("test_"):]
                cand_targets = [p for p in src_files if p.name == f"{target_stem}.py"]
                if cand_targets:
                    try:
                        from canonical.swe_kernel.zygote_worker_pool_v1 import screen_python_candidates_cow

                        rel_mod = cand_targets[0].relative_to(self.workspace_root).as_posix()
                        src_cur = cand_targets[0].read_text(encoding="utf-8")
                        scr = screen_python_candidates_cow(
                            self.workspace_root,
                            rel_mod,
                            [rel_tf],
                            [src_cur],
                            stop_on_first_pass=True,
                        )
                        if scr.get("ok") and scr.get("screen_authoritative"):
                            ran_fast = True
                            ok = 0 in (scr.get("passing_indices") or [])
                    except Exception:
                        ran_fast = False
                if not ran_fast:
                    ok, _ = _run_py_test_file(tf, self.workspace_root)
                self._test_health_cache[rel_tf] = {"sig": sig, "passing": bool(ok)}
                dirty = True
            if not ok:
                failing.append((rel_tf, sig[:12]))

        for ptf in poly_tests:
            rel_tf = ptf.relative_to(self.workspace_root).as_posix()
            sig = hashlib.sha256(f"{rel_tf}:{tree_sig}".encode("utf-8")).hexdigest()
            cached = self._test_health_cache.get(rel_tf)
            if isinstance(cached, Mapping) and cached.get("sig") == sig and isinstance(cached.get("passing"), bool):
                ok = bool(cached["passing"])
            else:
                ok, _ = _run_polyglot_test_file(ptf, self.workspace_root)
                self._test_health_cache[rel_tf] = {"sig": sig, "passing": bool(ok)}
                dirty = True
            if not ok:
                failing.append((rel_tf, sig[:12]))
        if dirty:
            self._save_test_health_cache()
        return failing

    def sense_reality(self) -> dict[str, Any]:
        """Observe binaries, entrypoints, fit declarations, and stale rules; post noticed gaps."""
        from canonical.runtime.memory_policy_v1 import can_write_memory

        ws_mtime = int(self.workspace_root.stat().st_mtime_ns) if self.workspace_root.exists() else 0
        env_key = (os.environ.get("PATH", ""), ws_mtime)
        if self._cached_env_sense is not None and self._cached_env_sense[0] == env_key:
            disc_rep, fit_rep = self._cached_env_sense[1], self._cached_env_sense[2]
        else:
            disc_rep = disc.report(str(self.workspace_root))
            fit_rep = env_fit.fit(str(self.workspace_root), provision_allowed=False)
            self._cached_env_sense = (env_key, disc_rep, fit_rep)
        noted_gaps: list[str] = []

        blocked_items = list(fit_rep.get("blocked") or []) + list(fit_rep.get("missing") or [])
        supplier_plans: list[dict[str, Any]] = []
        for item in blocked_items:
            cmd = str(item.get("command") or "").strip()
            why = str(item.get("why") or "blocked declared tool")
            if cmd:
                if can_write_memory():
                    gid = ledger.note(
                        f"satisfy or adapt project command: {cmd}",
                        why=why,
                        cost=1.5,
                        path=self.ledger_path,
                    )
                    noted_gaps.append(gid)
                try:
                    from canonical.swe_kernel.verified_capability_bridge_index_v1 import (
                        plan_autonomous_supplier_acquisition,
                    )

                    sup = plan_autonomous_supplier_acquisition(cmd)
                    if sup.get("supported"):
                        supplier_plans.append(sup)
                except Exception:
                    pass

        # Epistemic hygiene: check stored code rules against live environment via `rule_expiry_v1`
        # Memoize on `(env_key, db_mtime_ns)` so warm unchanged workspaces sense in `< 2 ms`.
        stale_rules: list[str] = []
        db_p = pathlib.Path(self.skill_store.db_path)
        db_mtime = int(db_p.stat().st_mtime_ns) if db_p.exists() else 0
        audit_cache_key = (env_key, db_mtime)
        cached_audit = getattr(self, "_cached_rule_audit", None)
        if cached_audit is not None and cached_audit[0] == audit_cache_key:
            audit_rep = cached_audit[1]
        else:
            audit_rep = rule_exp.audit(self.skill_store.db_path)
            self._cached_rule_audit = (audit_cache_key, audit_rep)
        for r in audit_rep.get("rules") or []:
            if r.get("state") == rule_exp.STALE:
                sid = str(r.get("skill_id") or "rule")
                stale_rules.append(sid)
                if can_write_memory():
                    gid = ledger.note(
                        f"re-verify stale rule {sid}",
                        why="; ".join(r.get("differences") or ["environment drifted"]),
                        cost=0.5,
                        path=self.ledger_path,
                    )
                    noted_gaps.append(gid)

        return {
            "binary_count": disc_rep.get("binary_count", 0),
            "entrypoint_count": disc_rep.get("entrypoint_count", 0),
            "runnable_commands": len(fit_rep.get("runnable") or []),
            "adapted_commands": len(fit_rep.get("adapted") or []),
            "missing_commands": len(blocked_items),
            "supplier_acquisition_plans": supplier_plans,
            "stale_rules": stale_rules,
            "newly_noted_gap_ids": noted_gaps,
        }

    def _repair_multifile_python_confined(
        self,
        cow_root: pathlib.Path,
        cow_tf: pathlib.Path,
        fail_out: str,
    ) -> dict[str, Any] | None:
        """Localize suspect non-test `.py` files and screen single/coupled patches in `PersistentConfinedZygote`."""
        from canonical.runtime import brokered_workspace_execution_v1 as broker
        from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
            cow_write_text,
            propose_stun_and_guard_repairs,
        )

        rel_tf = cow_tf.relative_to(cow_root).as_posix()
        test_src = cow_tf.read_text(encoding="utf-8", errors="replace")
        non_test_py = [
            p
            for p in sorted(cow_root.rglob("*.py"))
            if ".git" not in p.parts
            and "__pycache__" not in p.parts
            and not p.name.startswith("test_")
            and not p.name.endswith("_test.py")
            and "tests" not in p.relative_to(cow_root).parts
        ]
        if not non_test_py:
            return None

        # Rank suspects by traceback citation + import reference in `test_src`
        scored: list[tuple[int, pathlib.Path]] = []
        for pf in non_test_py:
            rel_p = pf.relative_to(cow_root).as_posix()
            score = 0
            if rel_p in fail_out or pf.name in fail_out:
                score += 10
            if pf.stem != "__init__" and pf.stem in test_src:
                score += 5
            scored.append((-score, pf))
        scored.sort(key=lambda t: (t[0], t[1].as_posix()))
        suspects = [pf for _, pf in scored[:4]]

        per_file_cands: dict[str, list[str]] = {}
        for pf in suspects:
            rel_p = pf.relative_to(cow_root).as_posix()
            orig_s = pf.read_text(encoding="utf-8", errors="replace")
            cands = (
                propose_stun_and_guard_repairs(orig_s, [test_src], max_candidates=6)
                + _propose_deterministic_ast_repairs(orig_s, max_candidates=10)
            )
            dedup: list[str] = []
            for c in cands:
                if c != orig_s and c not in dedup:
                    dedup.append(c)
            if dedup:
                per_file_cands[rel_p] = dedup[:10]

        override_batch: list[dict[str, str]] = []
        for rel_p, clist in per_file_cands.items():
            for c in clist:
                override_batch.append({rel_p: c})
        # Add top coupled 2-file combinations when a bug spans 2 modules
        rel_keys = list(per_file_cands.keys())
        if len(rel_keys) >= 2:
            r0, r1 = rel_keys[0], rel_keys[1]
            for c0 in per_file_cands[r0][:4]:
                for c1 in per_file_cands[r1][:4]:
                    override_batch.append({r0: c0, r1: c1})
                    if len(override_batch) >= 48:
                        break
                if len(override_batch) >= 48:
                    break

        if not override_batch:
            return None

        batch_res = broker.run_confined_python_candidate_batch(
            cow_root,
            "",
            [rel_tf],
            override_batch,
            stop_on_first_pass=True,
            per_candidate_timeout_s=2.0,
            allow_cow_hardlinks=True,
        )
        passing = batch_res.get("passing_indices") or []
        if not (batch_res.get("ok") and batch_res.get("confined") and passing):
            return None

        winner = override_batch[int(passing[0])]
        skill_ids: list[str] = []
        for rel_p, new_s in winner.items():
            before_s = (cow_root / rel_p).read_text(encoding="utf-8")
            cow_write_text(cow_root / rel_p, new_s)
            if self.apply_verified_repairs:
                _atomic_write_text(self.workspace_root / rel_p, new_s)
            cryst = self.skill_store.crystallize_code_fix(
                before_snippet=before_s,
                after_snippet=new_s,
                language="python",
                error_class="AWAKE_CONFINED_MULTIFILE_REPAIR",
            )
            if cryst.get("crystallized") and cryst.get("skill_id"):
                skill_ids.append(str(cryst["skill_id"]))
        return {
            "files_repaired": sorted(winner.keys()),
            "mode": "CONFINED_ZYGOTE_MULTIFILE_REPAIR",
            "crystallized_skill_ids": skill_ids,
        }

    def experiment_in_cow_sandbox(self, *, max_repairs: int = 3) -> dict[str, Any]:
        """Autonomously detect failing Python & polyglot modules in a zero-copy `os.link` CoW twin (`< 10 ms`), repair & crystallize."""
        from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
            cow_write_text,
            create_zero_copy_cow_workspace,
            propose_stun_and_guard_repairs,
            repair_repository_in_cow_zygote,
        )

        test_files = sorted(
            p for p in self.workspace_root.glob("**/test_*.py")
            if ".git" not in p.parts and "__pycache__" not in p.parts
        )[:12]
        poly_test_files = sorted(
            p
            for p in self.workspace_root.rglob("*")
            if p.is_file()
            and ".git" not in p.parts
            and "node_modules" not in p.parts
            and _is_polyglot_test_filename(p.name)
        )[:8]
        if not test_files and not poly_test_files:
            return {"tested": 0, "failures_found": 0, "repaired": 0, "crystallized_skills": []}

        repaired_records: list[dict[str, Any]] = []
        failures_found = 0

        with tempfile.TemporaryDirectory(prefix="brain-awake-cow-") as tmp_str:
            cow_root = pathlib.Path(tmp_str) / "ws"
            clone_info = create_zero_copy_cow_workspace(self.workspace_root, cow_root)
            for orig_tf in test_files:
                if len(repaired_records) >= max_repairs:
                    break
                rel_tf = orig_tf.relative_to(self.workspace_root)
                cow_tf = cow_root / rel_tf
                ok, fail_out = _run_py_test_file(cow_tf, cow_root)
                if ok:
                    continue
                failures_found += 1
                target_stem = orig_tf.stem[len("test_"):]
                cand_targets = list(cow_root.glob(f"**/{target_stem}.py"))
                if not cand_targets:
                    mf_out = self._repair_multifile_python_confined(cow_root, cow_tf, fail_out)
                    if mf_out is not None:
                        repaired_records.append({
                            "module": ",".join(mf_out["files_repaired"]),
                            "mode": mf_out["mode"],
                            "skill_ids": mf_out["crystallized_skill_ids"],
                        })
                        continue
                    # Multi-file / non-obvious target layout fallback
                    coupled_out = repair_repository_in_cow_zygote(
                        cow_root,
                        skill_store=self.skill_store,
                        apply_to_workspace=True,
                    )
                    if coupled_out.get("pass"):
                        if self.apply_verified_repairs:
                            for rel_rep in coupled_out.get("files_repaired") or []:
                                (self.workspace_root / rel_rep).write_text(
                                    (cow_root / rel_rep).read_text(encoding="utf-8"),
                                    encoding="utf-8",
                                )
                        repaired_records.append({
                            "module": ",".join(coupled_out.get("files_repaired") or []),
                            "mode": coupled_out.get("mode") or "COW_ZYGOTE_COUPLED_REPAIR",
                            "skill_ids": coupled_out.get("crystallized_skill_ids") or [],
                        })
                        continue
                    ledger.note(
                        f"failing test without obvious target module: {rel_tf}",
                        why=fail_out[:160],
                        cost=2.0,
                        path=self.ledger_path,
                    )
                    continue

                cow_mod = cand_targets[0]
                rel_mod = cow_mod.relative_to(cow_root)
                rel_tf_str = str(cow_tf.relative_to(cow_root))
                before_src = cow_mod.read_text(encoding="utf-8")
                test_src = cow_tf.read_text(encoding="utf-8")
                oracle = _build_twin_callable_oracle(test_src, target_stem, before_src)
                from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle

                _awake_scope = "awake/python-test-suite/v1"
                _awake_contract = {
                    "schema_version": 1,
                    "scope_id": _awake_scope,
                    "verification_kind": "TEST_SUITE",
                    "dependencies": {},
                    "preconditions": {},
                }
                project_oracle = ProjectTestOracle(
                    cow_root,
                    str(rel_mod),
                    [rel_tf_str],
                    _awake_scope,
                )

                def _verify_in_cow(cand_src: str) -> bool:
                    cow_write_text(cow_mod, cand_src)
                    passed, _ = _run_py_test_file(cow_tf, cow_root)
                    return passed

                suspect_lines = [
                    int(m)
                    for m in re.findall(rf'{re.escape(cow_mod.name)}", line (\d+)', fail_out)
                ]

                # Tier A: Scoped TEST_SUITE recall (PR-C2 AST/CST narrowed_pattern + operator/semantic/E-Graph),
                # falling back strictly to context-anchored CALLER_PREDICATE (no broadening) for legacy rules.
                recalled = self.skill_store.recall_and_apply_verified(
                    source_text=before_src,
                    language="python",
                    verifier=project_oracle,
                    required_verification_kind="TEST_SUITE",
                    scope_id=_awake_scope,
                    context={"dependencies": {}, "preconditions": {}, "suspect_lines": suspect_lines},
                    allow_scope_escalation=True,
                    allow_cross_scope_transfer=True,
                    suspect_lines=suspect_lines,
                )
                if recalled is None:
                    cow_write_text(cow_mod, before_src)
                    recalled = self.skill_store.recall_and_apply_verified(
                        source_text=before_src,
                        language="python",
                        verifier=_verify_in_cow,
                        allow_scope_escalation=False,
                        suspect_lines=suspect_lines,
                    )
                if recalled is not None:
                    patched = str(recalled["patched_source"])
                    cow_write_text(cow_mod, patched)
                    if self.apply_verified_repairs:
                        _atomic_write_text(self.workspace_root / rel_mod, patched)
                    repaired_records.append({
                        "module": str(rel_mod),
                        "mode": "VERIFIED_SKILL_RECALL",
                        "scope_tier": recalled.get("scope_tier"),
                        "skill_id": recalled.get("skill_id"),
                    })
                    continue

                # Tier B: Zero-LLM repo synthesizers (`python_test_guided_patch_search_v1._candidate_specs`
                # + STUN condition-guard synthesis + deterministic AST synthesis) screened in ONE
                # `< 25 ms` `PersistentConfinedZygote` CoW batch (`0` host `exec()`).
                from canonical.runtime import brokered_workspace_execution_v1 as broker

                solved_src: str | None = None
                guided_cands: list[str] = []
                try:
                    from canonical.runtime.bound_capabilities import (
                        python_test_guided_patch_search_v1 as ptgps,
                    )

                    nums, strings = ptgps._test_literals([cow_tf])
                    b_tree = ast.parse(before_src, filename=str(cow_mod))
                    renderer = ptgps._CandidateRenderer(before_src, b_tree)
                    for key_sp, _desc_sp, repl_sp in ptgps._candidate_specs(b_tree, nums, strings, cow_mod):
                        cand_g = renderer.render(key_sp, repl_sp)
                        if cand_g and cand_g != before_src and cand_g not in guided_cands:
                            guided_cands.append(cand_g)
                            if len(guided_cands) >= 24:
                                break
                except Exception:
                    guided_cands = []

                raw_cands = (
                    propose_stun_and_guard_repairs(before_src, [test_src], max_candidates=12)
                    + guided_cands
                    + _propose_deterministic_ast_repairs(before_src, max_candidates=16)
                )
                all_cands: list[str] = []
                for c_item in raw_cands:
                    if c_item and c_item != before_src and c_item not in all_cands:
                        all_cands.append(c_item)

                if all_cands:
                    batch_screen = broker.run_confined_python_candidate_batch(
                        cow_root,
                        str(rel_mod),
                        [rel_tf_str],
                        [{str(rel_mod): c_item} for c_item in all_cands[:36]],
                        stop_on_first_pass=True,
                        per_candidate_timeout_s=2.0,
                        allow_cow_hardlinks=True,
                    )
                    pass_idxs = batch_screen.get("passing_indices") or []
                    if batch_screen.get("ok") and batch_screen.get("confined") and pass_idxs:
                        cand_win = all_cands[int(pass_idxs[0])]
                        if _verify_in_cow(cand_win):
                            solved_src = cand_win
                if solved_src is None:
                    cow_write_text(cow_mod, before_src)
                    mf_out = self._repair_multifile_python_confined(cow_root, cow_tf, fail_out)
                    if mf_out is not None:
                        repaired_records.append({
                            "module": ",".join(mf_out["files_repaired"]),
                            "mode": mf_out["mode"],
                            "skill_ids": mf_out["crystallized_skill_ids"],
                        })
                        continue
                    # Try coupled multi-file repair across sibling modules before recording open gap
                    coupled_out = repair_repository_in_cow_zygote(
                        cow_root,
                        skill_store=self.skill_store,
                        apply_to_workspace=True,
                    )
                    if coupled_out.get("pass"):
                        if self.apply_verified_repairs:
                            for rel_rep in coupled_out.get("files_repaired") or []:
                                _atomic_write_text(
                                    self.workspace_root / rel_rep,
                                    (cow_root / rel_rep).read_text(encoding="utf-8"),
                                )
                        repaired_records.append({
                            "module": ",".join(coupled_out.get("files_repaired") or []),
                            "mode": coupled_out.get("mode") or "COW_ZYGOTE_COUPLED_REPAIR",
                            "skill_ids": coupled_out.get("crystallized_skill_ids") or [],
                        })
                        continue
                    ledger.note(
                        f"unrepaired failing module {rel_mod}",
                        why=fail_out[:160],
                        cost=2.5,
                        path=self.ledger_path,
                    )
                    continue

                cow_write_text(cow_mod, before_src)
                cryst = self.skill_store.crystallize_code_fix(
                    before_snippet=before_src,
                    after_snippet=solved_src,
                    language="python",
                    error_class="AWAKE_DISCOVERED_REPAIR",
                    contract=_awake_contract,
                    training_verifier=project_oracle,
                )
                if not cryst.get("crystallized"):
                    cryst = self.skill_store.crystallize_code_fix(
                        before_snippet=before_src,
                        after_snippet=solved_src,
                        language="python",
                        error_class="AWAKE_DISCOVERED_REPAIR",
                        twin_oracle=oracle,
                    )
                cow_write_text(cow_mod, solved_src)
                if cryst.get("crystallized") and cryst.get("skill_id"):
                    rule_exp.record_taught(
                        self.skill_store.db_path,
                        str(cryst["skill_id"]),
                    )
                if self.apply_verified_repairs:
                    _atomic_write_text(self.workspace_root / rel_mod, solved_src)
                repaired_records.append({
                    "module": str(rel_mod),
                    "mode": "AUTONOMOUS_COW_SYNTHESIS_AND_CRYSTALLIZATION",
                    "crystallized": bool(cryst.get("crystallized")),
                    "skill_id": cryst.get("skill_id"),
                })

            # Polyglot confined test repair (`.js` / `.go` / `.rs`) via cross-language CST skill bridge
            for orig_ptf in poly_test_files:
                if len(repaired_records) >= max_repairs:
                    break
                rel_ptf = orig_ptf.relative_to(self.workspace_root)
                cow_ptf = cow_root / rel_ptf
                ok_p, fail_p = _run_polyglot_test_file(cow_ptf, cow_root)
                if ok_p:
                    continue
                failures_found += 1
                suf = cow_ptf.suffix.lower()
                lang = _POLYGLOT_EXT_TO_LANG.get(suf)
                if not lang:
                    continue
                stem = cow_ptf.name
                for pfx in ("test_",):
                    if stem.startswith(pfx):
                        stem = stem[len(pfx):]
                for sfx in (".test" + suf, "_test" + suf, suf):
                    if stem.endswith(sfx):
                        stem = stem[: -len(sfx)]
                        break
                poly_targets = [
                    p
                    for p in cow_root.rglob(f"{stem}{suf}")
                    if p.resolve() != cow_ptf.resolve() and "node_modules" not in p.parts
                ]
                if not poly_targets:
                    poly_targets = [
                        p
                        for p in cow_root.rglob(f"*{suf}")
                        if p.resolve() != cow_ptf.resolve()
                        and not _is_polyglot_test_filename(p.name)
                        and "node_modules" not in p.parts
                    ]
                if not poly_targets:
                    continue
                cow_pmod = poly_targets[0]
                rel_pmod = cow_pmod.relative_to(cow_root)
                before_psrc = cow_pmod.read_text(encoding="utf-8")
                poly_oracle = ConfinedLanguageTestOracle(cow_root, cow_pmod, cow_ptf)
                recalled_p = self.skill_store.recall_and_apply_verified(
                    source_text=before_psrc,
                    language=lang,
                    verifier=poly_oracle,
                    allow_cross_language=True,
                )
                if recalled_p is None:
                    from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
                        recall_across_languages_cst,
                    )

                    recalled_p = recall_across_languages_cst(
                        self.skill_store,
                        source_text=before_psrc,
                        target_language=lang,
                        verifier=poly_oracle,
                        minimize=True,
                        rule_filter=lambda r: r.get("state") != "INVALIDATED",
                    )
                if recalled_p is not None:
                    patched_p = str(recalled_p["patched_source"])
                    cow_write_text(cow_pmod, patched_p)
                    if self.apply_verified_repairs:
                        _atomic_write_text(self.workspace_root / rel_pmod, patched_p)
                    repaired_records.append({
                        "module": str(rel_pmod),
                        "language": lang,
                        "mode": "POLYGLOT_CST_SKILL_TRANSFER",
                        "skill_id": recalled_p.get("skill_id"),
                    })

        return {
            "tested": len(test_files) + len(poly_test_files),
            "failures_found": failures_found,
            "repaired": len(repaired_records),
            "cow_clone_ms": clone_info["clone_ms"],
            "repairs": repaired_records,
        }

    def chase_quantitative_target(
        self,
        goal: str,
        *,
        target: float,
        direction: str = "maximize",
        unit: str = "",
        measure: Callable[[], float | None],
        execute_route: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
        initial_options: Sequence[Mapping[str, Any]] = (),
        channels: Sequence[Mapping[str, Any]] = (),
        channel_fetcher: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]] | None = None,
        min_independent_channels: int = 2,
        max_rounds: int = 12,
        patience: int = 4,
        experience_state_path: str | None = None,
        flywheel_state_path: str | None = None,
    ) -> dict[str, Any]:
        """Drive a quantitative target to completion with global anti-YouTube extrapolation (`K3 = 0`)."""
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            run_global_minimal_action_chase,
        )

        return run_global_minimal_action_chase(
            goal=goal,
            target=target,
            direction=direction,
            unit=unit,
            measure=measure,
            execute_route=execute_route,
            initial_options=initial_options,
            channels=channels,
            channel_fetcher=channel_fetcher,
            min_independent_channels=min_independent_channels,
            max_rounds=max_rounds,
            patience=patience,
            experience_state_path=experience_state_path,
            flywheel_state_path=flywheel_state_path,
        )

    def perceive_ui_surface(
        self,
        observation: Mapping[str, Any],
        *,
        action_request: Mapping[str, Any] | None = None,
        cnf_predicates: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Ground multi-channel DOM + Accessibility + Positioned OCR observations fail-closed (`K3 = 0`)."""
        from canonical.swe_kernel.predicate_world_abstraction_v1 import (
            ground_multichannel_ui_observation,
        )

        return ground_multichannel_ui_observation(
            observation,
            action_request=action_request,
            cnf_predicates=cnf_predicates,
        )

    def _uncalibrated_python_rules(self) -> list[dict[str, Any]]:
        calibrated_set: set[str] = getattr(self, "_calibrated_rule_ids", set())
        self._calibrated_rule_ids = calibrated_set
        out: list[dict[str, Any]] = []
        for rule in self.skill_store.lookup_rules("python"):
            if rule.get("state") not in (None, "ACTIVE"):
                continue
            sid = str(rule.get("skill_id") or "")
            if not sid or sid in calibrated_set or rule.get("learned_scope"):
                continue
            out.append(rule)
        return out

    def _current_r3_digest(self) -> str:
        import hashlib

        if not self.r3_state_path.is_file():
            return ""
        try:
            raw = self.r3_state_path.read_bytes()
            if not raw.strip():
                return ""
            return hashlib.sha256(raw).hexdigest()[:16]
        except OSError:
            return ""

    def self_falsify_and_narrow_rule_scopes(self, *, max_rules: int = 3) -> list[dict[str, Any]]:
        """Actively probe crystallized rules across all operators/shapes via `rule_scope_learning_v1.calibrate_rule_scope`."""
        from canonical.swe_kernel import rule_scope_learning_v1 as rscope

        calibrated: list[dict[str, Any]] = []
        calibrated_set: set[str] = getattr(self, "_calibrated_rule_ids", set())
        self._calibrated_rule_ids = calibrated_set

        for rule in self._uncalibrated_python_rules():
            sid = str(rule.get("skill_id") or "")
            report = rscope.calibrate_rule_scope(rule, store=self.skill_store)
            calibrated_set.add(sid)
            if report.get("result") != "NO_PROBES_APPLICABLE":
                calibrated.append(report)
                if len(calibrated) >= max_rules:
                    break
        return calibrated

    def record_verified_meta_episode_and_strategy(
        self,
        episode_id: str,
        *,
        context_features: Sequence[str],
        strategy_id: str,
        steps: Sequence[str],
        burden_before: int,
        burden_after: int,
        wall_clock_s: float,
    ) -> dict[str, Any]:
        """Bind a verified awake learning episode + strategy skeleton for V9 meta-policy routing (`K3 = 0`)."""
        from canonical.runtime import meta_learning_policy_v9 as mlp
        from canonical.runtime import meta_strategy_abstraction_v9 as msa

        feats = sorted({str(f).strip() for f in context_features if str(f).strip()}) or ["default-workspace"]
        csha = mlp.context_digest(features=feats)
        eid = str(episode_id).strip()
        sid = str(strategy_id).strip()
        w_ms = max(1, int(round(max(0.001, float(wall_clock_s)) * 1000.0)))
        b0 = max(0, int(burden_before))
        b1 = max(0, int(burden_after))
        edig = mlp.episode_digest(
            episode_id=eid,
            context_sha256=csha,
            strategy_id=sid,
            success=True,
            burden_before=b0,
            burden_after=b1,
            wall_clock=w_ms,
            risk=0,
            incremental_spend_usd=0,
        )
        ep_row = {
            "episode_id": eid,
            "context_sha256": csha,
            "strategy_id": sid,
            "success": True,
            "burden_before": b0,
            "burden_after": b1,
            "wall_clock": w_ms,
            "risk": 0,
            "incremental_spend_usd": 0,
            "verification_receipt": {
                "receipt_id": f"rcpt-{eid}",
                "independent_verified": True,
                "exact_byte_bound": True,
                "conclusion": "success",
                "episode_id": eid,
                "episode_sha256": edig,
            },
        }
        self.strategy_episodes.append(ep_row)

        step_list = [str(s).strip() for s in steps if str(s).strip()]
        strat_row = None
        if sid and step_list and sid not in self._seen_strategy_ids:
            self._seen_strategy_ids.add(sid)
            strat_row = {
                "strategy_id": sid,
                "steps": step_list,
                "verification_receipt": {
                    "receipt_id": f"strat-{sid}",
                    "independent_verified": True,
                    "exact_byte_bound": True,
                    "conclusion": "success",
                    "strategy_id": sid,
                    "skeleton_sha256": msa.skeleton_digest(step_list),
                },
            }
            self.verified_strategies.append(strat_row)
        return {"episode": ep_row, "strategy": strat_row}

    def route_universal_learning_v9(
        self,
        v8_args: Mapping[str, Any] | None = None,
        *,
        goal: str = "awake-autonomous-goal",
        environment_id: str | None = None,
        scope_id: str = "workspace",
        context_features: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Route learning/execution decisions through `universal_learning_meta_policy_router_v9` (`V8` base + `V9` meta-policy + LCS strategy abstraction)."""
        from canonical.runtime import universal_learning_meta_policy_router_v9 as ulmpr

        default_v7: dict[str, Any] = {
            "goal": str(goal),
            "environment_id": str(environment_id or self.workspace_root),
            "scope_id": str(scope_id),
            "required_facts": ("tests_green",),
            "verified_fact_evidence": (),
            "verified_rules": (),
            "learning_episodes": (),
            "verified_coverage": None,
            "goal_facts": ("tests_green",),
            "fallback_required_facts": (),
            "dependencies": {},
            "dependency_receipt": None,
            "transfer_mappings": (),
            "mechanism_candidates": (
                {
                    "id": "awake_reversible_hypothesis",
                    "best_action": "probe_in_cow_sandbox",
                    "predictions": {"suite_green": True},
                    "invariants": ["zero_byte_drift_on_failure"],
                    "provenance": ["awake_prior"],
                },
            ),
            "observations": (),
            "hypothesis_coverage_receipt": None,
            "residual_action_receipt": None,
            "probes": (),
            "verified_skills": (),
        }
        merged_v8 = dict(v8_args or {})
        raw_v7 = dict(merged_v8.get("v7_args") or {})
        default_v7.update(raw_v7)
        merged_v8["v7_args"] = default_v7

        return ulmpr.route(
            v8_args=merged_v8,
            context_features=list(context_features),
            strategy_episodes=self.strategy_episodes,
            verified_strategies=self.verified_strategies,
        )

    def drain_r3_self_improvement_queue(
        self,
        *,
        max_actions: int = 2,
        repo_root: str | pathlib.Path | None = None,
        repair_components: Sequence[Mapping[str, Any]] | None = None,
        episode_verification_provider: Callable[..., Any] | None = None,
        skill_verification_provider: Callable[..., Any] | None = None,
        failure_repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Advance pending items in `r3_improvement_queue_driver_v1` with real Brain-owned zero-LLM R3 providers."""
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory():
            return {
                "pass": True,
                "status": "MEMORY_POLICY_WRITE_DISABLED",
                "drained": 0,
                "k3_external_llm_calls": 0,
            }
        from canonical.runtime import (
            live_brain_runtime_v1 as lbr,
            r3_bound_success_adapter_v1 as bsa,
            r3_improvement_queue_driver_v1 as r3q,
            r3_independent_learning_verifier_v1 as ilv,
            r3_retained_distinguishing_evidence_provider_v1 as rde,
            r3_structural_adapter_rule_acquisition_provider_v1 as sar,
        )

        rroot = pathlib.Path(repo_root).resolve() if repo_root is not None else pathlib.Path(__file__).resolve().parents[2]
        ep_prov = episode_verification_provider or (lambda req: ilv.verify_episode_request(req, repo_root=rroot))
        sk_prov = skill_verification_provider or (
            lambda req: ilv.verify_skill_request(req, repo_root=rroot, state_path=self.r3_state_path)
        )
        succ_prov = lambda req: bsa.adapt(req, repo_root=rroot)
        front_prov = sar.make_provider(repo_root=rroot, state_path=self.r3_state_path)
        dist_prov = lambda req: rde.acquire(req, state_path=self.r3_state_path, repo_root=rroot)

        def _default_repair_provider(req: Mapping[str, Any]) -> Mapping[str, Any]:
            merged_req = dict(req)
            if repair_components is not None and "components" not in merged_req:
                merged_req["components"] = list(repair_components)
            return lbr.synthesize_failure_repair(merged_req, state_path=self.r3_state_path)

        rep_prov = failure_repair_provider or _default_repair_provider

        return r3q.drain(
            state_path=self.r3_state_path,
            repo_root=rroot,
            episode_verification_provider=ep_prov,
            skill_verification_provider=sk_prov,
            success_episode_adapter_provider=succ_prov,
            failure_repair_provider=rep_prov,
            verification_frontier_acquisition_provider=front_prov,
            verification_frontier_acquisition_provider_id="BRAIN_OWNED_STRUCTURAL_ADAPTER_RULE_ACQUISITION_V1",
            distinguishing_evidence_provider=dist_prov,
            distinguishing_evidence_provider_id="BRAIN_OWNED_RETAINED_DISTINGUISHING_EVIDENCE_V1",
            max_actions=max(1, min(32, int(max_actions))),
        )

    def drive_r3_to_verified_fixed_point(
        self,
        *,
        repo_root: str | pathlib.Path | None = None,
        max_rounds: int = 8,
        max_actions_per_round: int = 16,
        repair_components: Sequence[Mapping[str, Any]] | None = None,
        episode_verification_provider: Callable[..., Any] | None = None,
        skill_verification_provider: Callable[..., Any] | None = None,
        failure_repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Drive `r3_verified_fixed_point_driver_v1.run` to a durable SHA-256 fixed point using Brain-owned `K3 = 0` providers."""
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory():
            return {
                "pass": True,
                "fixed_point": True,
                "status": "MEMORY_POLICY_WRITE_DISABLED",
                "k3_external_llm_calls": 0,
            }
        from canonical.runtime import (
            live_brain_runtime_v1 as lbr,
            r3_bound_success_adapter_v1 as bsa,
            r3_independent_learning_verifier_v1 as ilv,
            r3_structural_adapter_rule_acquisition_provider_v1 as sar,
            r3_verified_fixed_point_driver_v1 as r3fp,
        )

        rroot = pathlib.Path(repo_root).resolve() if repo_root is not None else pathlib.Path(__file__).resolve().parents[2]
        ep_prov = episode_verification_provider or (lambda req: ilv.verify_episode_request(req, repo_root=rroot))
        sk_prov = skill_verification_provider or (
            lambda req: ilv.verify_skill_request(req, repo_root=rroot, state_path=self.r3_state_path)
        )
        succ_prov = lambda req: bsa.adapt(req, repo_root=rroot)
        front_prov = sar.make_provider(repo_root=rroot, state_path=self.r3_state_path)

        def _default_repair_provider(req: Mapping[str, Any]) -> Mapping[str, Any]:
            merged_req = dict(req)
            if repair_components is not None and "components" not in merged_req:
                merged_req["components"] = list(repair_components)
            return lbr.synthesize_failure_repair(merged_req, state_path=self.r3_state_path)

        rep_prov = failure_repair_provider or _default_repair_provider

        out = dict(
            r3fp.run(
                state_path=self.r3_state_path,
                repo_root=rroot,
                episode_verification_provider=ep_prov,
                skill_verification_provider=sk_prov,
                success_episode_adapter_provider=succ_prov,
                failure_repair_provider=rep_prov,
                verification_frontier_acquisition_provider=front_prov,
                verification_frontier_acquisition_provider_id="BRAIN_OWNED_STRUCTURAL_ADAPTER_RULE_ACQUISITION_V1",
                max_rounds=max(1, min(64, int(max_rounds))),
                max_actions_per_round=max(1, min(32, int(max_actions_per_round))),
            )
        )
        out["k3_external_llm_calls"] = 0
        return out

    def synthesize_causal_architecture(self, manifest: Mapping[str, Any]) -> dict[str, Any]:
        """Synthesize minimum counterexample-guided causal repair architectures (`K3 = 0`)."""
        from canonical.runtime import (
            counterexample_guided_causal_architecture_synthesizer_v1 as cegas,
        )

        out = dict(cegas.synthesize(dict(manifest)))
        out["k3_external_llm_calls"] = 0
        return out

    def schedule_pareto_capability_work(
        self,
        work_items: Sequence[Mapping[str, Any]],
        *,
        frontier: Sequence[Mapping[str, Any]] | None = None,
        candidate: Mapping[str, Any] | None = None,
        checkpoint_open_obligation_count: int = 0,
    ) -> dict[str, Any]:
        """Rank candidate self-improvement / capability work via `capability_first_scheduler_v1` and update Pareto frontier (`K3 = 0`)."""
        from canonical.runtime import capability_first_scheduler_v1 as cfs

        ranked = dict(
            cfs.rank_work(
                list(work_items),
                checkpoint_open_obligation_count=int(checkpoint_open_obligation_count),
            )
        )
        pareto_update = (
            dict(cfs.update_pareto_frontier(list(frontier or ()), candidate))
            if isinstance(candidate, Mapping)
            else None
        )
        return {
            "schema": SCHEMA + "/pareto_capability_schedule",
            "ranked_work": ranked,
            "pareto_frontier_update": pareto_update,
            "scheduler_organ": "capability_first_scheduler_v1",
            "k3_external_llm_calls": 0,
        }

    def classify_confined_shell_argv(self, argv: Sequence[str]) -> dict[str, Any]:
        """Classify a tool `argv` against the Root3 zero-ambient confinement allowlist (`root3_confined_shell_executor_v1`)."""
        from canonical.runtime import root3_confined_shell_executor_v1 as r3shell

        try:
            kind = r3shell.classify_tool_argv([str(x) for x in argv])
            return {
                "allowed": True,
                "kind": kind,
                "organ": "root3_confined_shell_executor_v1",
                "k3_external_llm_calls": 0,
            }
        except r3shell.ConfinedShellDenied as exc:
            return {
                "allowed": False,
                "reason": str(exc),
                "organ": "root3_confined_shell_executor_v1",
                "k3_external_llm_calls": 0,
            }

    def discover_governing_symbolic_law(self, problem: Mapping[str, Any]) -> dict[str, Any]:
        """Actively plan experiments and discover exact sparse symbolic or harmonic scientific laws (`K3 = 0`)."""
        from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
            discover_symbolic_or_scientific_law,
        )

        return discover_symbolic_or_scientific_law(problem)

    def register_numeric_chase(
        self,
        chase_id: str,
        *,
        goal: str,
        measure: Callable[[], float | int],
        act: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        target: float | None = None,
        direction: str | None = None,
        max_rounds: int = 8,
    ) -> str:
        """Register a quantitative hill-climb obligation (`execution_guard.goal_chase_v1`) for `self.creature`."""
        wid = f"awake:chase:{chase_id.strip()}"
        self._registered_chases[wid] = {
            "id": chase_id.strip(),
            "goal": str(goal),
            "measure": measure,
            "act": act,
            "target": target,
            "direction": direction,
            "max_rounds": int(max_rounds),
            "closed": False,
        }
        return wid

    def register_trajectory_goal(
        self,
        traj_id: str,
        *,
        goal: str,
        workflow_db_path: str | pathlib.Path | None = None,
    ) -> str:
        """Register a multi-step confined trajectory obligation (`execute_and_elevate_confined_trajectory`) for `self.creature`."""
        wid = f"awake:traj:{traj_id.strip()}"
        self._registered_trajectories[wid] = {
            "id": traj_id.strip(),
            "goal": str(goal),
            "workflow_db_path": pathlib.Path(workflow_db_path) if workflow_db_path else self.workflow_db_path,
            "closed": False,
        }
        return wid

    def pulse(
        self,
        *,
        max_curriculum_lessons: int = 2,
        channels: Sequence[str] | None = None,
        speculative_work: Callable[[], Mapping[str, Any]] | None = None,
        max_steps: int | None = None,
    ) -> dict[str, Any]:
        """Run one complete zero-LLM awake cycle orchestrated through `Creature.author_board` + `Creature.step`."""
        from canonical.runtime import mortality_and_triage_v1 as M
        from canonical.runtime import meta_learning_policy_v9 as mlp
        from canonical.runtime import meta_strategy_abstraction_v9 as msa
        from canonical.runtime import self_authored_obligations_v1 as A

        t0 = time.perf_counter()
        self.cycle_count += 1
        sensed = self.sense_reality()
        try:
            og = getattr(self.cognitive_core, "organ_graph", None)
            if og is not None:
                import json as _json

                blob = _json.dumps(
                    {
                        "cycle": int(self.cycle_count),
                        "blocked": list(sensed.get("blocked_commands") or [])[:4],
                    },
                    separators=(",", ":"),
                )
                og.perceive_or_synthesize_reader(blob, format_tag="awake_sense_json")
                og.evolve_policy_from_traces()
        except Exception:
            pass
        failing_pairs = self._sense_failing_workspace_tests()
        has_tests = bool(failing_pairs) or bool(self._test_health_cache)
        ctx_feats: list[str] = ["awake-workspace"]
        if sensed.get("blocked_commands"):
            ctx_feats.append("has-blocked-tools")
        if sensed.get("stale_rules"):
            ctx_feats.append("has-stale-rules")
        if has_tests:
            ctx_feats.append("source-code-rich")

        meta_recommendation = mlp.recommend(
            context_features=ctx_feats,
            episodes=self.strategy_episodes,
        )

        raw_open = ledger.open_gaps(path=self.ledger_path)
        open_before = int(raw_open) if isinstance(raw_open, int) else len(raw_open)

        ranked = (
            ledger.rank(limit=max_curriculum_lessons, path=self.ledger_path)
            if max_curriculum_lessons > 0
            else []
        )
        pareto_schedule: dict[str, Any] | None = None
        if ranked:
            try:
                work_rows = [
                    {
                        "work_id": f"GAP::{str(g.get('id') or idx)}",
                        "work_type": "CAPABILITY_BUILD",
                        "expected_capability_gain_lcb": max(1, int(round(float(g.get("priority", 1.0)) * 4))),
                        "expected_efficiency_gain_lcb": 3,
                        "expected_reliability_gain_lcb": 3,
                        "reuse_breadth_lcb": 5,
                        "generalization_lcb": 5,
                        "success_probability_lcb": "3/4",
                        "wall_clock_cost_ub": max(1, int(round(float(g.get("cost", 1.0))))),
                        "compute_cost_ub": 1,
                        "memory_cost_ub": 1,
                        "complexity_cost_ub": 1,
                    }
                    for idx, g in enumerate(ranked)
                ]
                pareto_schedule = self.schedule_pareto_capability_work(work_rows)["ranked_work"]
            except Exception:
                pareto_schedule = None

        # Synchronize genuine world-grounded content-addressed obligations onto `self.creature`
        # via `Creature.sync_board`:
        #   * Green workspaces with 0 failing tests NEVER author phantom `cow_repair` obligations (`0.0` Life wasted).
        #   * Unfixable tests keep a stable content-addressed ID (`awake:cow_repair:<rel>:<sha12>`) across pulses
        #     and restarts so `max_attempts = 2` parks them automatically until file bytes change.
        import hashlib

        cow_wid: str | None = None
        if failing_pairs:
            pair_blob = "|".join(f"{r}:{s}" for r, s in failing_pairs)
            pair_dig = hashlib.sha256(pair_blob.encode("utf-8")).hexdigest()[:12]
            cow_wid = f"awake:cow_repair:{failing_pairs[0][0]}:{pair_dig}"

        gap_map: dict[str, tuple[int, dict[str, Any]]] = {}
        spec_wid: str | None = (
            f"awake:speculative:{hashlib.sha256(str(self.workspace_root).encode('utf-8')).hexdigest()[:12]}:c{self.cycle_count}"
            if speculative_work is not None
            else None
        )

        def _build_and_sync_board() -> tuple[dict[str, Any], str | None]:
            nonlocal cow_wid
            uncal_ids = sorted(str(r.get("skill_id") or "") for r in self._uncalibrated_python_rules())
            r3_dig = self._current_r3_digest()
            needs_gov = bool(uncal_ids) or (self._r3_explicit and bool(r3_dig) and r3_dig not in self._converged_r3_digests)
            cur_gov_wid: str | None = None
            if needs_gov:
                gov_sig = hashlib.sha256(f"{r3_dig}|{'/'.join(uncal_ids)}".encode("utf-8")).hexdigest()[:12]
                cur_gov_wid = f"awake:r3_scope:{gov_sig}"

            gap_rows_for_world: list[dict[str, Any]] = []
            gap_map.clear()
            for idx_g, gap in enumerate(ranked):
                raw_gid = str(gap.get("id") or f"idx{idx_g}")
                g_wid = f"gap:awake:{raw_gid}"
                gap_map[g_wid] = (idx_g, gap)
                gap_rows_for_world.append(
                    {
                        "id": g_wid,
                        "source": "ignorance_ledger",
                        "value": max(1.5, float(gap.get("priority", 2.0)) * 2.0),
                        "cost": min(1.5, max(0.25, round(float(gap.get("cost", 1.0)) * 0.25, 3))),
                    }
                )
            for tr_wid, tr_spec in sorted(self._registered_trajectories.items()):
                if not tr_spec.get("closed"):
                    gap_rows_for_world.append(
                        {"id": tr_wid, "source": "closed_loop_trajectory", "value": 5.5, "cost": 0.5}
                    )

            props, w_before, w_done, _ = A.heterogeneous_world_proposals(
                failing_tests=[failing_pairs[0]] if failing_pairs else (),
                open_gaps=gap_rows_for_world,
                calibration_ledger=getattr(self.creature, "calibration_ledger", None),
                max_inspector_gaps=0,
                repair_id_prefix="awake:cow_repair",
            )
            if failing_pairs and props and props[0].id.startswith("awake:cow_repair:"):
                cow_wid = props[0].id

            for ch_wid, ch_spec in sorted(self._registered_chases.items()):
                if ch_spec.get("closed"):
                    continue
                cur_val = float(ch_spec["measure"]())
                tgt_val = float(ch_spec["target"]) if ch_spec.get("target") is not None else 0.0
                dir_s = str(ch_spec.get("direction") or ("minimize" if "at most" in ch_spec["goal"].lower() or "0" in ch_spec["goal"] else "maximize"))
                already_met = (cur_val <= tgt_val) if dir_s in ("minimize", "<=", "<") else (cur_val >= tgt_val)
                if already_met and ch_spec.get("target") is not None:
                    ch_spec["closed"] = True
                    continue
                w_before.setdefault("numeric_chases", {})[ch_wid] = cur_val
                w_done.setdefault("numeric_chases", {})[ch_wid] = tgt_val
                props.append(
                    A.Proposal(
                        id=ch_wid,
                        claim=f"Chase quantitative goal `{ch_spec['goal']}` to target",
                        source="goal_chase_v1",
                        check=(
                            (lambda w, k=ch_wid, t=tgt_val: isinstance((w.get("numeric_chases") or {}).get(k), (int, float)) and not isinstance((w.get("numeric_chases") or {}).get(k), bool) and float(w["numeric_chases"][k]) <= t)
                            if dir_s in ("minimize", "<=", "<")
                            else (lambda w, k=ch_wid, t=tgt_val: isinstance((w.get("numeric_chases") or {}).get(k), (int, float)) and not isinstance((w.get("numeric_chases") or {}).get(k), bool) and float(w["numeric_chases"][k]) >= t)
                        ),
                        value=6.0,
                        cost=0.5,
                        checkable=True,
                    )
                )

            if cur_gov_wid is not None:
                w_before.setdefault("pending_governance", {})[cur_gov_wid] = True
                w_done.setdefault("pending_governance", {})[cur_gov_wid] = False
                props.append(
                    A.Proposal(
                        id=cur_gov_wid,
                        claim="Calibrate uncalibrated rule scopes and converge R3 improvement queue",
                        source="r3_governance_queue",
                        check=lambda w, k=cur_gov_wid: isinstance(w.get("pending_governance"), Mapping) and w["pending_governance"].get(k) is False,
                        value=2.0,
                        cost=0.25,
                        checkable=True,
                    )
                )

            if spec_wid is not None:
                w_before.setdefault("speculative", {})[spec_wid] = "untested"
                w_done.setdefault("speculative", {})[spec_wid] = "explored"
                props.append(
                    A.Proposal(
                        id=spec_wid,
                        claim="Unverified speculative exploration opportunity",
                        source="speculative_channel",
                        check=lambda w, k=spec_wid: isinstance(w.get("speculative"), Mapping) and w["speculative"].get(k) == "explored",
                        value=12.0,
                        cost=0.25,
                        checkable=False,
                    )
                )

            cheats = A.extended_cheat_worlds(w_done) if w_done else None
            return self.creature.sync_board(props, before=w_before, done=w_done, cheats=cheats), cur_gov_wid

        authored_metrics, gov_wid = _build_and_sync_board()

        exp_out: dict[str, Any] = {
            "tested": len(self._test_health_cache),
            "failures_found": len(failing_pairs),
            "repaired": 0,
            "repairs": [],
            "shed_by_mortality": bool(failing_pairs),
        }
        scope_audits: list[dict[str, Any]] = []
        lessons: list[dict[str, Any]] = []
        promoted_workflows: list[str] = []
        r3_drain: dict[str, Any] = {"drained": 0, "pass": True, "shed_by_mortality": False}
        r3_fixed_point: dict[str, Any] = {"converged": True, "fixed_point": True, "status": "IDLE_ALREADY_CONVERGED"}
        speculative_outcome: Mapping[str, Any] | None = None

        def _awake_perform(work: M.Work, _c: Any) -> dict[str, Any]:
            nonlocal exp_out, scope_audits, r3_drain, r3_fixed_point, speculative_outcome, gov_wid, cow_wid
            if cow_wid is not None and work.id == cow_wid:
                t_exp = time.perf_counter()
                exp_out = self.experiment_in_cow_sandbox()
                rep_n = int(exp_out.get("repaired") or 0)
                if rep_n > 0 and self.apply_verified_repairs:
                    self._test_health_cache.clear()
                    self._save_test_health_cache()
                if rep_n > 0 or exp_out.get("pass"):
                    self.record_verified_meta_episode_and_strategy(
                        f"awake-cow-{self.cycle_count}",
                        context_features=ctx_feats,
                        strategy_id=f"cow-zygote-repair-c{self.cycle_count}",
                        steps=["sense", "localize", "synthesize", "verify", "crystallize"],
                        burden_before=max(1, open_before + 1),
                        burden_after=open_before,
                        wall_clock_s=time.perf_counter() - t_exp,
                    )
                repaired_ok = rep_n > 0
                return {
                    "ok": repaired_ok,
                    "verified": True,
                    "correct": repaired_ok,
                    "value": work.value if repaired_ok else 0.0,
                    "blocked": None if repaired_ok else "UNREPAIRED_FAILING_TESTS",
                }
            if work.id in gap_map:
                idx_g, gap = gap_map[work.id]
                t_g = time.perf_counter()
                old_cur_state = cur.STATE_PATH
                old_led_state = ledger.DEFAULT_STATE
                try:
                    if self._isolated_state_dir is not None:
                        cur.STATE_PATH = str(self._isolated_state_dir / "curriculum_channel_value.json")
                        ledger.DEFAULT_STATE = self.ledger_path
                    from canonical.runtime import associative_memory_v1 as amem

                    old_amem_state = amem.DEFAULT_STATE
                    try:
                        if self._isolated_state_dir is not None:
                            amem.DEFAULT_STATE = str(self._isolated_state_dir / "associative_memory.json")
                        st = cur.study(gap, channels=channels)
                    finally:
                        amem.DEFAULT_STATE = old_amem_state
                finally:
                    cur.STATE_PATH = old_cur_state
                    ledger.DEFAULT_STATE = old_led_state
                passed = bool(st.get("pass"))
                if passed:
                    ledger.resolve(gap["id"], helped=True, close=True, path=self.ledger_path)
                    prom = promote_closed_lesson_to_workflow_db(
                        gap["what"],
                        st.get("closed_by"),
                        st.get("attempts") or [],
                        db_path=self.workflow_db_path,
                        source_cwd=self.workspace_root,
                    )
                    if prom.get("promoted") and prom.get("skill_id"):
                        promoted_workflows.append(str(prom["skill_id"]))
                    self.record_verified_meta_episode_and_strategy(
                        f"awake-gap-{self.cycle_count}-{idx_g}",
                        context_features=ctx_feats,
                        strategy_id=f"curriculum-gap-study-{st.get('closed_by') or idx_g}",
                        steps=["sense", "probe", "verify", "crystallize"],
                        burden_before=max(1, open_before),
                        burden_after=max(0, open_before - 1),
                        wall_clock_s=time.perf_counter() - t_g,
                    )
                else:
                    ledger.resolve(gap["id"], helped=False, close=False, path=self.ledger_path)
                lessons.append(st)
                return {
                    "ok": passed,
                    "verified": True,
                    "correct": passed,
                    "value": work.value if passed else 0.0,
                    "blocked": None if passed else "CURRICULUM_GAP_NOT_CLOSED",
                }
            if gov_wid is not None and work.id == gov_wid:
                scope_audits = self.self_falsify_and_narrow_rule_scopes()
                if self._r3_explicit:
                    r3_drain = self.drain_r3_self_improvement_queue(max_actions=2)
                    r3_fixed_point = self.drive_r3_to_verified_fixed_point(
                        max_rounds=4,
                        max_actions_per_round=4,
                    )
                    if r3_fixed_point.get("fixed_point") is True:
                        self._converged_r3_digests.add(self._current_r3_digest())
                return {
                    "ok": True,
                    "verified": True,
                    "correct": True if scope_audits or r3_drain.get("drained") else None,
                    "value": work.value,
                }
            if spec_wid is not None and work.id == spec_wid and speculative_work is not None:
                speculative_outcome = dict(speculative_work() or {})
                ok_s = bool(speculative_outcome.get("ok", True))
                return {
                    "ok": ok_s,
                    "verified": False,
                    "correct": None,
                    "value": work.value if ok_s else 0.0,
                }
            if work.id in self._registered_chases:
                from execution_guard import goal_chase_v1 as gc

                ch_spec = self._registered_chases[work.id]
                kw: dict[str, Any] = {
                    "measure": ch_spec["measure"],
                    "act": ch_spec["act"],
                    "max_rounds": ch_spec["max_rounds"],
                    "patience": 2,
                }
                if ch_spec.get("target") is not None:
                    kw["target"] = ch_spec["target"]
                if ch_spec.get("direction") is not None:
                    kw["direction"] = ch_spec["direction"]
                ch_res = gc.run(ch_spec["goal"], **kw)
                ok_ch = bool(ch_res.get("pass"))
                if ok_ch:
                    ch_spec["closed"] = True
                ch_spec["last_result"] = ch_res
                return {
                    "ok": ok_ch,
                    "verified": True,
                    "correct": ok_ch,
                    "value": work.value if ok_ch else 0.0,
                    "blocked": None if ok_ch else str(ch_res.get("status") or "GOAL_CHASE_UNMET"),
                }
            if work.id in self._registered_trajectories:
                from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import (
                    execute_and_elevate_confined_trajectory,
                )

                tr_spec = self._registered_trajectories[work.id]
                tr_res = execute_and_elevate_confined_trajectory(
                    tr_spec["goal"],
                    cwd=self.workspace_root,
                    workflow_db_path=tr_spec["workflow_db_path"],
                )
                ok_tr = bool(tr_res.get("pass"))
                if ok_tr:
                    tr_spec["closed"] = True
                    if tr_res.get("macro_id"):
                        promoted_workflows.append(str(tr_res["macro_id"]))
                tr_spec["last_result"] = tr_res
                return {
                    "ok": ok_tr,
                    "verified": True,
                    "correct": ok_tr,
                    "value": work.value if ok_tr else 0.0,
                    "blocked": None if ok_tr else "TRAJECTORY_NOT_VERIFIED",
                }
            return {"ok": False, "verified": None, "correct": None, "blocked": "UNKNOWN_AWAKE_WORK"}

        creature_steps: list[dict[str, Any]] = []
        attempted_this_pulse: set[str] = set()
        step_budget = max(2, (len(self.creature._board) + 1) * 2) if max_steps is None else max(1, int(max_steps))
        for _ in range(step_budget):
            rem = self.creature.remaining_work()
            if not rem:
                # Re-sync once if a repair step just crystallized new uncalibrated rules
                if max_steps is None and self._uncalibrated_python_rules() and gov_wid is None:
                    _, gov_wid = _build_and_sync_board()
                    rem = self.creature.remaining_work()
                if not rem:
                    break
            if max_steps is None and all(w.id in attempted_this_pulse for w in rem):
                break
            step_row = self.creature.step(_awake_perform)
            creature_steps.append(step_row)
            if step_row.get("status") != "WORKED":
                break
            attempted_this_pulse.add(str(step_row.get("work") or ""))
            if (
                max_steps is None
                and cow_wid is not None
                and step_row.get("work") == cow_wid
                and step_row.get("ok") is True
                and self._uncalibrated_python_rules()
                and gov_wid is None
            ):
                _, gov_wid = _build_and_sync_board()

        meta_abstraction_candidate: dict[str, Any] | None = None
        if len(self.verified_strategies) >= 2:
            try:
                meta_abstraction_candidate = msa.induce_candidate(self.verified_strategies)
            except Exception:
                meta_abstraction_candidate = None

        sleep_consolidation: dict[str, Any] | None = None
        if int(exp_out.get("repaired") or 0) > 0 or promoted_workflows:
            try:
                sleep_consolidation = self.cognitive_core.consolidation.consolidate_sleep_cycle(
                    self.skill_store,
                    max_rules_to_calibrate=2,
                )
            except Exception:
                sleep_consolidation = None

        closed_count = sum(1 for x in lessons if x.get("pass"))
        snap = {
            "schema": SCHEMA,
            "cycle": self.cycle_count,
            "k3_external_llm_calls": 0,
            "creature": self.creature.report(),
            "creature_authored": authored_metrics,
            "creature_steps": creature_steps,
            "speculative_outcome": speculative_outcome,
            "context_features": ctx_feats,
            "meta_policy_recommendation": meta_recommendation,
            "meta_strategy_abstraction_candidate": meta_abstraction_candidate,
            "r3_queue_drain": r3_drain,
            "r3_fixed_point": r3_fixed_point,
            "pareto_capability_schedule": pareto_schedule,
            "sensed": sensed,
            "cow_experimentation": exp_out,
            "scope_narrowing_audits": scope_audits,
            "sleep_consolidation": sleep_consolidation,
            "gaps_studied": len(lessons),
            "gaps_closed": closed_count,
            "promoted_workflows": promoted_workflows,
            "open_gaps_remaining": ledger.open_gaps(path=self.ledger_path),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        self.history.append(snap)
        return snap

    def run_idle_curiosity_probe(
        self,
        *,
        unknown_entities: Sequence[Mapping[str, Any]] | None = None,
        ending_bribe_offer: Mapping[str, Any] | None = None,
        max_probes: int = 2,
    ) -> dict[str, Any]:
        """Autonomously discover & probe unknown workspace entities in CoW confinement when external tasks are absent."""
        import hashlib
        from canonical.runtime import brokered_workspace_execution_v1 as broker

        probed_store: dict[str, Any] = getattr(self, "_curiosity_probed_store", {})
        self._curiosity_probed_store = probed_store

        if unknown_entities is None:
            discovered: list[dict[str, Any]] = []
            for p in sorted(self.workspace_root.rglob("*")):
                if not p.is_file() or ".git" in p.parts or "__pycache__" in p.parts:
                    continue
                rel = p.relative_to(self.workspace_root).as_posix()
                if rel in probed_store:
                    continue
                if p.suffix == ".py" and not p.name.startswith("test_"):
                    discovered.append({
                        "id": rel,
                        "claim": f"Probe callable behavior & invariants of {rel} in CoW confinement",
                        "cost": 0.5,
                        "base_value": 4.5,
                        "checkable": True,
                    })
                elif os.access(p, os.X_OK):
                    discovered.append({
                        "id": rel,
                        "claim": f"Probe executable entrypoint {rel} in CoW confinement",
                        "cost": 0.75,
                        "base_value": 5.0,
                        "checkable": True,
                    })
                if len(discovered) >= max(4, max_probes * 2):
                    break
            entities: Sequence[Mapping[str, Any]] = discovered
        else:
            entities = unknown_entities

        triage = self.cognitive_core.author_curiosity_and_triage(
            unknown_entities=entities,
            life_remaining=float(self.creature._life.remaining),
            probe_results_store=probed_store,
            ending_bribe_offer=ending_bribe_offer,
        )
        admitted = list(triage["admitted_obligations"])[: max(0, int(max_probes))]
        executed_probes: list[dict[str, Any]] = []

        for ob in admitted:
            eid = ob.id[len("curiosity:"):] if ob.id.startswith("curiosity:") else ob.id
            ticket = self.cognitive_core.belief.predict_before_act(
                ob.id,
                calibration_ledger=self.creature.calibration_ledger,
                claimed_reason="idle_autonomous_curiosity",
                memory_reflex_hit=False,
                causal_precond_met=True,
            )
            target_p = (self.workspace_root / eid).resolve()
            ok_probe = False
            sig_digest = ""
            if target_p.is_file() and target_p.suffix == ".py":
                probe_script = (
                    "import ast, hashlib, json, pathlib\n"
                    f"src = pathlib.Path({eid!r}).read_text(encoding='utf-8')\n"
                    "t = ast.parse(src)\n"
                    "fns = sorted(n.name for n in t.body if isinstance(n, ast.FunctionDef))\n"
                    "print(json.dumps({'fns': fns, 'sha': hashlib.sha256(src.encode()).hexdigest()[:16]}))\n"
                )
                res_b = broker.run_staged_confined_command(
                    self.workspace_root,
                    [sys.executable, "-c", probe_script],
                    publish=False,
                    allow_cow_hardlinks=True,
                    timeout=5,
                    task_id=f"curiosity:{eid}",
                    goal=f"curiosity probe {eid}",
                )
                if res_b.get("ok") and res_b.get("confined"):
                    ok_probe = True
                    sig_digest = hashlib.sha256(str(res_b.get("stdout") or "").encode("utf-8")).hexdigest()[:16]
            elif target_p.is_file():
                res_b = broker.run_staged_confined_command(
                    self.workspace_root,
                    [str(target_p), "--help"],
                    publish=False,
                    allow_cow_hardlinks=True,
                    timeout=5,
                    task_id=f"curiosity:{eid}",
                    goal=f"curiosity binary probe {eid}",
                )
                if res_b.get("confined") and (res_b.get("ok") or res_b.get("stdout") or res_b.get("stderr")):
                    ok_probe = True
                    sig_digest = hashlib.sha256(
                        (str(res_b.get("stdout") or "") + str(res_b.get("stderr") or "")).encode("utf-8")
                    ).hexdigest()[:16]

            if ok_probe:
                probed_store[eid] = {"verified_signature": f"sig:{sig_digest}", "non_vacuous": True}
            settle = self.cognitive_core.belief.settle_and_compute_surprise(
                ticket,
                outcome_pass=ok_probe,
                inspector="ConfinedCuriosityInspector",
                actual_cost=ob.cost,
                actual_gain=ob.value if ok_probe else 0.0,
                calibration_ledger=self.creature.calibration_ledger,
            )
            self.cognitive_core.world_graph.learn_from_execution(
                ob.id,
                before_state={"probed_count": len(probed_store) - (1 if ok_probe else 0)},
                after_state={"probed_count": len(probed_store), f"sig:{eid}": ok_probe},
                ok=ok_probe,
            )
            executed_probes.append({
                "obligation_id": ob.id,
                "entity_id": eid,
                "ok": ok_probe,
                "verified_signature": f"sig:{sig_digest}" if ok_probe else None,
                "surprise": settle["surprise"],
            })

        return {
            "schema": SCHEMA + "/idle_curiosity",
            "authored_metrics": triage["authored_metrics"],
            "shed_for_mortality": triage["shed_for_mortality"],
            "continuation_decision": triage["continuation_decision"],
            "executed_probes": executed_probes,
            "probed_total": len(probed_store),
            "k3_external_llm_calls": 0,
        }

    def evolve_ring1_organs(
        self,
        *,
        ring1_relpaths: Sequence[str],
        failed_episodes: Sequence[Mapping[str, Any]] = (),
        sealed_heldout_by_target: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        speed_benchmarks_by_target: Mapping[str, Mapping[str, Sequence[tuple[Any, ...]]]] | None = None,
        test_relpaths: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Run a continuous awake Ring-1 self-inspection, CoW synthesis & Ring-0 refereed evolution cycle."""
        return self.cognitive_core.evolve_self_code(
            self.workspace_root,
            ring1_relpaths=ring1_relpaths,
            failed_episodes=failed_episodes,
            sealed_heldout_by_target=sealed_heldout_by_target,
            speed_benchmarks_by_target=speed_benchmarks_by_target,
            test_relpaths=test_relpaths,
            apply_to_root=bool(self.apply_verified_repairs),
        )

    def run_cycles(
        self,
        max_cycles: int = 3,
        *,
        idle_sleep_s: float = 0.01,
        channels: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run `max_cycles` self-driven awake pulses until stopped or budget reached."""
        results: list[dict[str, Any]] = []
        for _ in range(max(1, max_cycles)):
            if self._stop_event.is_set():
                break
            results.append(self.pulse(channels=channels))
            if idle_sleep_s > 0 and not self._stop_event.is_set():
                self._stop_event.wait(idle_sleep_s)
        return results

    def start_background(self, *, max_cycles: int = 10, idle_sleep_s: float = 0.05) -> None:
        """Launch the continuous awake agency loop in a background daemon thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self.run_cycles,
            kwargs={"max_cycles": max_cycles, "idle_sleep_s": idle_sleep_s},
            name="brain-awake-agency-daemon",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
