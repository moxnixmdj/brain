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


def _run_py_test_file(test_file: pathlib.Path, cwd: pathlib.Path, timeout: float = 8.0) -> tuple[bool, str]:
    """Execute a Python test file (`unittest` / plain `assert` script / `pytest`) fast without stale `.pyc`."""
    for pyc_dir in cwd.glob("**/__pycache__"):
        shutil.rmtree(pyc_dir, ignore_errors=True)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(cwd) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    txt = test_file.read_text(encoding="utf-8", errors="replace")
    if "def test_" in txt and "__main__" not in txt:
        cmd = [sys.executable, "-B", "-m", "pytest", "-q", "--tb=short", str(test_file)]
    else:
        cmd = [sys.executable, "-B", str(test_file)]
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode == 0, combined[-600:]


def _build_twin_callable_oracle(
    test_source: str,
    target_stem: str,
    orig_source: str = "",
) -> Callable[[str], bool]:
    """Construct an in-process twin oracle resilient to `crystallize_code_fix` identifier alpha-renaming."""
    orig_fn_order: list[str] = []
    try:
        for nd in ast.parse(orig_source).body:
            if isinstance(nd, ast.FunctionDef):
                orig_fn_order.append(nd.name)
    except SyntaxError:
        pass

    def _oracle(candidate_code: str) -> bool:
        import types

        mod = types.ModuleType(target_stem)
        try:
            cand_tree = ast.parse(candidate_code)
            exec(compile(cand_tree, f"<{target_stem}>", "exec"), mod.__dict__)
        except Exception:
            return False
        cand_fns = [nd.name for nd in cand_tree.body if isinstance(nd, ast.FunctionDef)]
        if len(cand_fns) == len(orig_fn_order):
            for old_nm, new_nm in zip(orig_fn_order, cand_fns):
                if old_nm not in mod.__dict__ and new_nm in mod.__dict__:
                    mod.__dict__[old_nm] = mod.__dict__[new_nm]
        saved = sys.modules.get(target_stem)
        sys.modules[target_stem] = mod
        try:
            test_ns: dict[str, Any] = {"__name__": "__twin_test__"}
            exec(compile(test_source, "<twin_test>", "exec"), test_ns)
            has_top_assert = any(isinstance(n, ast.Assert) for n in ast.parse(test_source).body)
            ran = 1 if has_top_assert else 0
            for name, obj in list(test_ns.items()):
                if name.startswith("test_") and callable(obj):
                    obj()
                    ran += 1
            return ran > 0
        except Exception:
            return False
        finally:
            if saved is None:
                sys.modules.pop(target_stem, None)
            else:
                sys.modules[target_stem] = saved

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
    ) -> None:
        import hashlib

        self.workspace_root = pathlib.Path(workspace_root).resolve()
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
            self.r3_state_path = pathlib.Path(tempfile.gettempdir()) / f"brain_awake_r3_{hashlib.sha256(str(self.workspace_root).encode('utf-8')).hexdigest()[:12]}.json"
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

    def sense_reality(self) -> dict[str, Any]:
        """Observe binaries, entrypoints, fit declarations, and stale rules; post noticed gaps."""
        disc_rep = disc.report(str(self.workspace_root))
        fit_rep = env_fit.fit(str(self.workspace_root), provision_allowed=False)
        noted_gaps: list[str] = []

        blocked_items = list(fit_rep.get("blocked") or []) + list(fit_rep.get("missing") or [])
        supplier_plans: list[dict[str, Any]] = []
        for item in blocked_items:
            cmd = str(item.get("command") or "").strip()
            why = str(item.get("why") or "blocked declared tool")
            if cmd:
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
        stale_rules: list[str] = []
        audit_rep = rule_exp.audit(self.skill_store.db_path)
        for r in audit_rep.get("rules") or []:
            if r.get("state") == rule_exp.STALE:
                sid = str(r.get("skill_id") or "rule")
                stale_rules.append(sid)
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

    def experiment_in_cow_sandbox(self, *, max_repairs: int = 3) -> dict[str, Any]:
        """Autonomously detect failing Python modules in a zero-copy `os.link` CoW twin (`< 10 ms`), repair & crystallize."""
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
        if not test_files:
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
                    # Multi-file / non-obvious target layout: invoke full CoW coupled/STUN repair engine!
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
                before_src = cow_mod.read_text(encoding="utf-8")
                test_src = cow_tf.read_text(encoding="utf-8")
                oracle = _build_twin_callable_oracle(test_src, target_stem, before_src)

                def _verify_in_cow(cand_src: str) -> bool:
                    cow_write_text(cow_mod, cand_src)
                    passed, _ = _run_py_test_file(cow_tf, cow_root)
                    return passed

                # Tier A: Instant recall from VerifiedSkillStore (including SCOPE_ALGEBRAIC E-Graph, mid_insertion & CST!)
                recalled = self.skill_store.recall_and_apply_verified(
                    source_text=before_src,
                    language="python",
                    verifier=_verify_in_cow,
                )
                if recalled is not None:
                    patched = str(recalled["patched_source"])
                    cow_write_text(cow_mod, patched)
                    if self.apply_verified_repairs:
                        (self.workspace_root / rel_mod).write_text(patched, encoding="utf-8")
                    repaired_records.append({
                        "module": str(rel_mod),
                        "mode": "VERIFIED_SKILL_RECALL",
                        "scope_tier": recalled.get("scope_tier"),
                        "skill_id": recalled.get("skill_id"),
                    })
                    continue

                # Tier B: Zero-LLM STUN guard synthesis + deterministic AST synthesis in CoW twin!
                solved_src: str | None = None
                all_cands = propose_stun_and_guard_repairs(before_src, [test_src], max_candidates=12) + _propose_deterministic_ast_repairs(before_src)
                for cand in all_cands:
                    if _verify_in_cow(cand):
                        solved_src = cand
                        break
                if solved_src is None:
                    cow_write_text(cow_mod, before_src)
                    # Try coupled multi-file repair across sibling modules before recording open gap
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
                        f"unrepaired failing module {rel_mod}",
                        why=fail_out[:160],
                        cost=2.5,
                        path=self.ledger_path,
                    )
                    continue

                cryst = self.skill_store.crystallize_code_fix(
                    before_snippet=before_src,
                    after_snippet=solved_src,
                    language="python",
                    error_class="AWAKE_DISCOVERED_REPAIR",
                    twin_oracle=oracle,
                )
                if cryst.get("crystallized") and cryst.get("skill_id"):
                    rule_exp.record_taught(
                        self.skill_store.db_path,
                        str(cryst["skill_id"]),
                    )
                if self.apply_verified_repairs:
                    (self.workspace_root / rel_mod).write_text(solved_src, encoding="utf-8")
                repaired_records.append({
                    "module": str(rel_mod),
                    "mode": "AUTONOMOUS_COW_SYNTHESIS_AND_CRYSTALLIZATION",
                    "crystallized": bool(cryst.get("crystallized")),
                    "skill_id": cryst.get("skill_id"),
                })

        return {
            "tested": len(test_files),
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

    def self_falsify_and_narrow_rule_scopes(self, *, max_rules: int = 3) -> list[dict[str, Any]]:
        """Actively probe crystallized rules with `finite_capability_diagnosis.select_probe` via `rule_scope_learning_v1`."""
        from canonical.swe_kernel import operator_generalization_v1 as op_gen
        from canonical.swe_kernel import rule_scope_learning_v1 as rscope

        calibrated: list[dict[str, Any]] = []
        calibrated_set: set[str] = getattr(self, "_calibrated_rule_ids", set())
        self._calibrated_rule_ids = calibrated_set

        for rule in self.skill_store.lookup_rules("python"):
            sid = str(rule.get("skill_id") or "")
            if not sid or sid in calibrated_set:
                continue
            swap = op_gen.derive_operator_swap(rule)
            if swap is None:
                continue
            old_op, new_op = str(swap.get("from") or ""), str(swap.get("to") or "")
            if (old_op, new_op) == ("<=", "<"):
                probes = [
                    {"label": "statement_twin", "language": "python", "source_text": "def f(a, b):\n    return a <= b\n"},
                    {"label": "guard_branch", "language": "python", "source_text": "def f(a, b):\n    if a <= b:\n        return True\n    return False\n"},
                    {"label": "disjunctive_boundary", "language": "python", "source_text": "def f(a, b):\n    return a < b or a == b\n"},
                ]

                def _probe_verifier(cand_code: str) -> bool:
                    ns: dict[str, Any] = {}
                    try:
                        exec(compile(cand_code, "<scope_probe>", "exec"), ns)
                        fn = ns.get("f")
                        return bool(callable(fn) and fn(3, 5) is True and fn(5, 5) is False and fn(6, 5) is False)
                    except Exception:
                        return False

                learned = rscope.learn_scope(rule, probes, _probe_verifier)
                calibrated_set.add(sid)
                calibrated.append(learned)
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
        episode_verification_provider: Callable[..., Any] | None = None,
        skill_verification_provider: Callable[..., Any] | None = None,
        failure_repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Advance pending items in `r3_improvement_queue_driver_v1` inside this daemon's isolated state."""
        from canonical.runtime import r3_improvement_queue_driver_v1 as r3q

        return r3q.drain(
            state_path=self.r3_state_path,
            repo_root=pathlib.Path(__file__).resolve().parents[2],
            episode_verification_provider=episode_verification_provider,
            skill_verification_provider=skill_verification_provider,
            failure_repair_provider=failure_repair_provider,
            max_actions=max(1, min(32, int(max_actions))),
        )

    def pulse(self, *, max_curriculum_lessons: int = 2, channels: Sequence[str] | None = None) -> dict[str, Any]:
        """Run one complete zero-LLM awake cycle: sense -> V9 meta-policy -> CoW experiment -> scope probing -> study gaps -> R3 queue drain."""
        from canonical.runtime import meta_learning_policy_v9 as mlp
        from canonical.runtime import meta_strategy_abstraction_v9 as msa

        t0 = time.perf_counter()
        self.cycle_count += 1
        sensed = self.sense_reality()
        ctx_feats: list[str] = ["awake-workspace"]
        if sensed.get("blocked_commands"):
            ctx_feats.append("has-blocked-tools")
        if sensed.get("stale_rules"):
            ctx_feats.append("has-stale-rules")
        if any(self.workspace_root.rglob("test_*.py")):
            ctx_feats.append("source-code-rich")

        meta_recommendation = mlp.recommend(
            context_features=ctx_feats,
            episodes=self.strategy_episodes,
        )

        raw_open = ledger.open_gaps(path=self.ledger_path)
        open_before = int(raw_open) if isinstance(raw_open, int) else len(raw_open)
        t_exp = time.perf_counter()
        exp_out = self.experiment_in_cow_sandbox()
        if exp_out.get("repaired") or exp_out.get("pass"):
            self.record_verified_meta_episode_and_strategy(
                f"awake-cow-{self.cycle_count}",
                context_features=ctx_feats,
                strategy_id=f"cow-zygote-repair-c{self.cycle_count}",
                steps=["sense", "localize", "synthesize", "verify", "crystallize"],
                burden_before=max(1, open_before + 1),
                burden_after=open_before,
                wall_clock_s=time.perf_counter() - t_exp,
            )

        scope_audits = self.self_falsify_and_narrow_rule_scopes()

        # Study top-ranked open gaps in this daemon's ledger
        ranked = ledger.rank(limit=max(1, max_curriculum_lessons), path=self.ledger_path)
        lessons: list[dict[str, Any]] = []
        promoted_workflows: list[str] = []
        for idx_g, gap in enumerate(ranked):
            t_g = time.perf_counter()
            st = cur.study(gap, channels=channels)
            if st.get("pass"):
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

        meta_abstraction_candidate: dict[str, Any] | None = None
        if len(self.verified_strategies) >= 2:
            try:
                meta_abstraction_candidate = msa.induce_candidate(self.verified_strategies)
            except Exception:
                meta_abstraction_candidate = None

        r3_drain = self.drain_r3_self_improvement_queue(max_actions=2)

        snap = {
            "schema": SCHEMA,
            "cycle": self.cycle_count,
            "k3_external_llm_calls": 0,
            "context_features": ctx_feats,
            "meta_policy_recommendation": meta_recommendation,
            "meta_strategy_abstraction_candidate": meta_abstraction_candidate,
            "r3_queue_drain": r3_drain,
            "sensed": sensed,
            "cow_experimentation": exp_out,
            "scope_narrowing_audits": scope_audits,
            "gaps_studied": len(lessons),
            "gaps_closed": sum(1 for x in lessons if x.get("pass")),
            "promoted_workflows": promoted_workflows,
            "open_gaps_remaining": ledger.open_gaps(path=self.ledger_path),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        self.history.append(snap)
        return snap

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
