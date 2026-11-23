#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code-repair env for the GENERIC perfect-algorithm scan.

The specialist twin (code_repair_env_v1.py, §21) teaches from ONE demonstrated
(broken, fixed) pair via the anti-unify path. This is the OTHER half the repo
recorded as missing: a code-repair env the GENERIC scan loop can handle --
same env protocol (reset/act/state/snapshot/restore), same plan/admit/persist
chain (perfect_algorithm_v1.run), no other machinery.

What makes it a code-repair env, and what makes it transfer:

  Actions are CONTENT-INVARIANT textual rules, not instance coordinates.
  `fix_op:<=|<` replaces every occurrence of `<=` in the module with `<`,
  wherever they appear. A rule learned on one broken file transfers to ANY
  fresh broken file containing the same defect -- the fresh variants do not
  need to be byte-identical, only same-shape. The same invariant the archive
  family already proves (tool names rather than content-specific coordinates).

  State is the module source plus the real subprocess test verdict:
  {"content": str, "passes": bool}. `passes` is the REAL oracle -- the test
  file runs in a subprocess exactly as the final verification runs it --
  never a re-read of the file, never a claim.

  Honest heuristic (flat, zero-knowledge): 0.0 when the test passes, 1.0 when
  it does not. The scan is then goal-directed best-first; nothing is known
  about the fix before the scan tries things.

  Snapshot/restore are real (file bytes), so the scan can probe freely without
  corrupting the very state it studies.

What it refuses to claim: it is not the specialist twin's anti-unifying gate;
it is the honest scan-level code-repair env §17 named. The one demonstrated
lesson (§21) and this honest scan (§23) are two paths to the same goal.

Model calls: 0. Network: 0. Spend: $0.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_CODE_REPAIR_SCAN_ENV_V1"
AUTHORITY = "NONE__OBSERVED_HOST_EVIDENCE_AND_GATES"
KIND = "code_repair"

# The honest minimal envelope for a single-token-operator defect family:
# the operators a broken Python expression can plausibly hold. The caller
# declares it; the scan never invents it.
DEFAULT_CANDIDATES: tuple[str, ...] = (
    "+", "-", "*", "/",
    "<", ">", "<=", ">=",
    "==", "!=",
)


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)


class CodeRepairEnv:
    """A real broken module in a real temp directory plus a real oracle test."""

    def __init__(self,
                 broken_source: str,
                 test_source: str,
                 candidates: Sequence[str] = DEFAULT_CANDIDATES,
                 *,
                 workdir: str | pathlib.Path | None = None,
                 module_name: str = "broken_module",
                 test_name: str = "test_module.py",
                 kind: str = KIND) -> None:
        self._owned = workdir is None
        self.root = pathlib.Path(workdir) if workdir is not None else pathlib.Path(
            tempfile.mkdtemp(prefix="code_repair_scan_env_"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.kind = kind
        self.candidates = tuple(candidates)
        self.module_name = _safe_name(module_name)
        self.test_name = _safe_name(test_name)
        self._module_file = self.root / f"{self.module_name}.py"
        self._test_file = self.root / f"{self.test_name}.py"
        self._original = broken_source
        self._test_source_text = test_source
        self.reset()

    # -- lifecycle -- #
    def reset(self) -> None:
        self._module_file.write_text(self._original, encoding="utf-8")
        self._test_file.write_text(self._test_source_text, encoding="utf-8")

    def close(self) -> None:
        if self._owned:
            shutil.rmtree(self.root, ignore_errors=True)

    # -- env protocol -- #
    def act(self, action: str) -> bool:
        name = str(action)
        prefix = "fix_op:"
        if not name.startswith(prefix):
            return False
        rest = name[len(prefix):]
        if "|" not in rest:
            return False
        old, new = rest.split("|", 1)
        if not old or not new or old == new or old not in self.candidates \
                or new not in self.candidates:
            return False
        text = self._module_file.read_text(encoding="utf-8")
        if old not in text:
            return False  # no occurrence: an honest no-op that still validates
        self._module_file.write_text(text.replace(old, new), encoding="utf-8")
        return True

    def state(self) -> dict[str, Any]:
        text = self._module_file.read_text(encoding="utf-8", errors="replace")
        return {"content": text, "passes": self._test_passes()}

    def snapshot(self) -> dict[str, Any]:
        # the A* scan restores the snapshot it recorded; it must round-trip
        # the state observation, not a byte blob (same contract as the
        # file-transform env)
        return self.state()

    def restore(self, token: Mapping[str, Any]) -> None:
        if isinstance(token, Mapping) and "content" in token:
            self._module_file.write_text(token["content"], encoding="utf-8")

    def action_names(self) -> list[str]:
        out: list[str] = []
        for old in self.candidates:
            for new in self.candidates:
                if old != new:
                    out.append(f"fix_op:{old}|{new}")
        return sorted(out)

    # -- the oracle -- #
    def _test_passes(self) -> bool:
        try:
            proc = subprocess.run(
                [sys.executable, "-B", f"{self.test_name}.py"], cwd=str(self.root),
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "PYTHONPATH": str(self.root),
                     "PYTHONDONTWRITEBYTECODE": "1"})
            return proc.returncode == 0
        except Exception:
            return False

    def test_passes(self) -> bool:
        return self._test_passes()


def build_code_repair_env(
    broken_source: str,
    test_source: str,
    *,
    candidates: Sequence[str] = DEFAULT_CANDIDATES,
    module_name: str = "broken_module",
    test_name: str = "test_module",
    workdir: str | pathlib.Path | None = None,
) -> tuple[CodeRepairEnv, dict[str, Any]]:
    """Construct the env plus the meta the perfect-algorithm loop needs.

    Returns (env, meta) where meta carries:
      is_goal    -- real subprocess test gate (the final authority)
      heuristic  -- flat flat prior: 0.0 at the goal, 1.0 elsewhere (honest)
      state      -- same predicate for admission fresh instances
    """
    env = CodeRepairEnv(broken_source, test_source, candidates,
                       workdir=workdir, module_name=module_name,
                       test_name=test_name)

    def is_goal(state: Any) -> bool:
        try:
            return bool(state.get("passes")) if isinstance(state, dict) else False
        except Exception:
            return False

    def heuristic(state: Any) -> float:
        try:
            return 0.0 if (state or {}).get("passes") else 1.0
        except Exception:
            return 1.0

    meta = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "is_goal": is_goal,
        "heuristic": heuristic,
        "env_kind": KIND,
    }
    return env, meta


