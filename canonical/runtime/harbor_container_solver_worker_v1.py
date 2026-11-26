#!/usr/bin/env python3
"""Container-side Brain solve worker. Never grants authority or verifies isolation.

This program must only be dispatched inside a suitably confined task container.
The experimental Harbor path checks Docker configuration but has not been
independently verified. The JSON output is an untrusted raw solver response,
not a verified effect.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
from pathlib import Path

MARKER = "BRAIN_CONTAINER_SOLVE_V1:"
MAX_REQUEST_BYTES = 64_000


def _detect_repo_language(cwd: Path) -> str:
    if (cwd / "Cargo.toml").is_file():
        return "rust"
    if (cwd / "go.mod").is_file():
        return "go"
    if (cwd / "tsconfig.json").is_file():
        return "typescript"
    if (cwd / "package.json").is_file():
        return "javascript"
    counts = {"python": 0, "cpp": 0, "c": 0, "javascript": 0, "typescript": 0, "rust": 0, "go": 0}
    skip_dirs = {".git", "node_modules", "vendor", ".venv", "venv", "dist", "build", "__pycache__"}
    ext_map = {
        ".py": "python",
        ".c": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".js": "javascript",
        ".ts": "typescript",
        ".rs": "rust",
        ".go": "go",
    }
    try:
        for dirpath, dirnames, filenames in os.walk(cwd):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs][:16]
            for fn in filenames[:64]:
                lang = ext_map.get(Path(fn).suffix.lower())
                if lang:
                    counts[lang] += 1
            if sum(counts.values()) >= 40:
                break
    except OSError:
        pass
    best_lang, best_cnt = max(counts.items(), key=lambda kv: kv[1])
    return best_lang if best_cnt > 0 else "python"


def _fallback_zero_llm_container_solve(
    task_instruction: str,
    cwd: Path,
    brain_root: Path,
) -> dict | None:
    """Zero-model-call container-native fallback using Speculative CoW Petri Rollouts
    (terminal environments) and CausalCEGISInventor + Issue-to-Oracle Abduction (Git repos).
    All scratch/store writes stay strictly under /tmp (never touching read-only /opt/brain-ro)."""
    clean_instruction = (
        task_instruction.split("Task instruction:\n", 1)[1].strip()
        if "Task instruction:\n" in task_instruction
        else task_instruction
    )
    try:
        from canonical.swe_kernel.speculative_cow_petri_agent_v1 import (
            EpistemicPetriSkillStore,
            solve_terminal_workspace,
        )

        tmp_skills = Path("/tmp/brain-harbor-petri-skills.json")
        term_out = solve_terminal_workspace(
            cwd,
            clean_instruction,
            skill_store=EpistemicPetriSkillStore(tmp_skills),
        )
        if term_out.committed:
            return {
                "pass": True,
                "status": "PASS__ZERO_LLM_COW_PETRI_TERMINAL",
                "model_calls": 0,
                "actions": [{"type": "finish", "args": {"summary": term_out.mechanism}}],
            }
    except Exception:
        pass

    if cwd.is_dir():
        try:
            from canonical.swe_kernel.causal_cegis_inventor_v1 import CausalCEGISInventor

            ro_laws = brain_root / "canonical" / "astra_runtime" / "state" / "SEMANTIC_CAUSAL_LAWS_V1.json"
            tmp_laws = Path("/tmp/brain-harbor-semantic-laws.json")
            if ro_laws.is_file() and not tmp_laws.exists():
                shutil.copyfile(ro_laws, tmp_laws)
            inv = CausalCEGISInventor(
                law_store_path=tmp_laws,
                negative_store_path=Path("/tmp/brain-harbor-neg-invariants.json"),
                enable_law_crystallization=False,
                sandbox_budget=28,
            )
            swe_res = inv.solve_repository(
                cwd,
                language=_detect_repo_language(cwd),
                problem_statement=clean_instruction,
                timeout_sec=18.0,
            )
            if swe_res.solved and swe_res.modified_files:
                for rel_p, new_src in swe_res.modified_files.items():
                    if "_cogs_" in rel_p:
                        continue
                    dest = (cwd / rel_p).resolve()
                    if str(dest).startswith(str(cwd.resolve()) + os.sep):
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_text(new_src, encoding="utf-8")
                return {
                    "pass": True,
                    "status": "PASS__ZERO_LLM_COGS_SWE_REPAIR",
                    "model_calls": 0,
                    "actions": [{"type": "finish", "args": {"summary": swe_res.mechanism}}],
                }
        except Exception:
            pass
    return None


def main() -> int:
    if len(sys.argv) != 2:
        raise ValueError("REQUEST_ARGUMENT_REQUIRED")
    raw = base64.b64decode(sys.argv[1], validate=True)
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError("REQUEST_TOO_LARGE")
    request = json.loads(raw)
    if not isinstance(request, dict) or not isinstance(request.get("goal"), str):
        raise ValueError("REQUEST_INVALID")
    inputs = request.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("INPUTS_INVALID")
    mode = request.get("mode")
    if not isinstance(mode, str) or len(mode) > 64:
        raise ValueError("MODE_INVALID")

    # This file is invoked as a script under an externally read-only Brain
    # root. -I -B is used by the dispatcher; never rely on task PYTHONPATH.
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from canonical.runtime.brain_unified_model_v1 import open_model

    # Keep the routing ledger out of the read-only Brain tree. This setting
    # alone cannot constrain all writes made by every route.
    inputs = dict(inputs)
    inputs["ledger_db_path"] = "/tmp/brain-harbor-routing.sqlite"
    result = open_model(root=root).solve(
        request["goal"], inputs=inputs, mode=mode, context_paths=[], cwd=os.getcwd()
    )
    if not isinstance(result, dict):
        raise ValueError("SOLVER_RESULT_NOT_OBJECT")
    if (
        result.get("pass") is not True
        and isinstance(inputs.get("harbor_task"), str)
        # Legacy task-only requests use the one-shot worker. A cycle request
        # is proposal-only, even when the controller refuses it.
        and "cycle" not in inputs and "observations" not in inputs
        and not inputs.get("observation_history")
    ):
        fb = _fallback_zero_llm_container_solve(
            inputs["harbor_task"], Path(os.getcwd()), root
        )
        if isinstance(fb, dict):
            result = fb
    print(MARKER + json.dumps(result, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
