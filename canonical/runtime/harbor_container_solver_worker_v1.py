#!/usr/bin/env python3
"""Container-side Brain solve worker. Never grants authority or verifies isolation.

This program must only be dispatched inside a suitably confined task container.
The experimental Harbor path checks Docker configuration but has not been
independently verified. The JSON output is an untrusted raw solver response,
not a verified effect.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import stat
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

MARKER = "BRAIN_CONTAINER_SOLVE_V1:"
MAX_REQUEST_BYTES = 64_000
IMPORT_PROPOSAL_SOURCE = "DETERMINISTIC_IMPORTED_ENGINES_V1"


def _compact_engine_result(result):
    if not isinstance(result, dict):
        return {"status": "ENGINE_RESULT_INVALID"}
    winner = result.get("winner") if isinstance(result.get("winner"), dict) else {}
    keep = {}
    for key in ("status", "verified", "language", "runner", "runner_kind",
                "attempts", "candidates_generated", "seconds", "model_calls",
                "parameters_stored", "full_verifications"):
        if key in result:
            value = result.get(key)
            if isinstance(value, list):
                value = value[:12]
            keep[key] = value
    if winner:
        diff = winner.get("diff") if isinstance(winner.get("diff"), str) else ""
        keep["winner"] = {k: winner.get(k) for k in (
            "file", "lineno", "tier", "attempt",
        ) if k in winner}
        keep["winner"]["diff_bytes"] = len(diff.encode("utf-8"))
        keep["winner"]["diff_sha256"] = hashlib.sha256(diff.encode("utf-8")).hexdigest() if diff else None
    return keep


def _scan_languages(root: Path) -> tuple[Counter, list[str], list[str]]:
    counts: Counter = Counter()
    package_json = False
    c_names = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp")
    js_names = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
    excluded = {".git", ".hg", ".svn", "node_modules", "vendor", "third_party",
                "__pycache__", "dist", "build"}
    visited = 0
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in excluded and not d.startswith(".")]
        visited += len(dirs) + len(files)
        if visited > 50_000:
            break
        for name in files:
            lower = name.lower()
            if lower == "package.json":
                package_json = True
            if lower.endswith(".py"):
                counts["python"] += 1
            elif lower.endswith(js_names):
                counts["javascript_typescript"] += 1
            elif lower.endswith(c_names):
                counts["c_cpp"] += 1
    return counts, (["package.json"] if package_json else []), []


def _finish(summary: str, **details):
    result = {
        "schema": "brain.imported_engine_cycle.v1",
        "authority": "NONE__UNVERIFIED_CONTAINER_CANDIDATE",
        "proposal_source": IMPORT_PROPOSAL_SOURCE,
        "status": details.pop("engine_status", "IMPORTED_ENGINES_ATTEMPTED__UNVERIFIED"),
        "pass": True,
        "capability_id": IMPORT_PROPOSAL_SOURCE,
        "task_completion_claimed": False,
        "official_verifier_expected": True,
        "runtime_model_calls_verified": False,
        "parameters_stored_verified": False,
        "actions": [{"type": "finish", "args": {"summary": summary[:1500]}}],
    }
    result.update(details)
    # Mirror the routing status under engine_status for uniform diagnostics;
    # status remains the machine-readable envelope state.
    result["engine_status"] = result["status"]
    return result


def _open_model_fallback(goal: str, mode: str, inputs, root):
    """Invoke Brain's ordinary solve() route (zero external model calls).

    Returns the raw solver envelope; the caller annotates it. Raises on any
    failure so the caller can record an honest finish instead of crashing.
    """
    from canonical.runtime.brain_unified_model_v1 import open_model

    forwarded = dict(inputs)
    forwarded.pop("workspace_baseline", None)
    forwarded["ledger_db_path"] = "/tmp/brain-harbor-routing.sqlite"
    result = open_model(root=root).solve(
        goal, inputs=forwarded, mode=mode, context_paths=[], cwd=os.getcwd()
    )
    if not isinstance(result, dict):
        raise ValueError("SOLVER_RESULT_NOT_OBJECT")
    return result


def _pro_imported_cycle(inputs, repo: str) -> dict:
    from canonical.runtime.harbor_pro_worktree_v1 import StageError, stage_worktree
    from canonical.runtime.harbor_pro_grounding_v1 import ground
    from canonical.runtime.harbor_pro_candidate_write_map_v1 import (
        CandidateApplyError, apply_source_map, source_map_from_winner,
    )

    instruction = str(inputs.get("harbor_task") or "")
    temp_parent = Path(tempfile.mkdtemp(prefix="brain-swe-work-", dir="/tmp"))
    staged = temp_parent / "work"
    staged.mkdir(mode=0o700)
    try:
        staging = stage_worktree(repo, staged, authorize_test_execution=True)
        language_counts, markers, marker_errors = _scan_languages(staged)
        js_count = int(language_counts.get("javascript_typescript", 0))
        py_count = int(language_counts.get("python", 0))
        c_count = int(language_counts.get("c_cpp", 0))
        if js_count and (js_count >= py_count or "package.json" in markers):
            language = "javascript_typescript"
        elif c_count and c_count > py_count:
            language = "c_cpp"
        else:
            language = "python"

        grounding = ground(instruction, repo)
        reported = {}
        engine_name = language
        try:
            if language == "javascript_typescript":
                from canonical.runtime.multilang_causal_swe_engine_v1 import solve_js_repository
                raw = solve_js_repository(staged, timeout_s=20.0, max_candidates=30)
            elif language == "c_cpp":
                from canonical.runtime.multilang_causal_swe_engine_v1 import solve_c_repository
                raw = solve_c_repository(staged, timeout_s=20.0, max_candidates=30)
            else:
                from canonical.runtime.causal_angelic_swe_engine_v1 import solve_repository
                targets = grounding.get("test_candidates") if isinstance(grounding, dict) else []
                targets = [str(t) for t in (targets or [])[:30]]
                raw = solve_repository(staged, targets, timeout_s=20.0, max_candidates=40)
        except Exception as exc:
            raw = {"status": "ENGINE_EXCEPTION", "error_type": type(exc).__name__,
                   "error": str(exc)[:300], "model_calls": 0, "parameters_stored": 0}
        compact = _compact_engine_result(raw)
        winner = raw.get("winner") if isinstance(raw, dict) else None
        diff_bytes = 0
        apply_report = {"status": "NO_CANDIDATE_APPLIED", "official_verifier_invoked": False}
        try:
            source_map, diff_bytes, nonempty = source_map_from_winner(winner)
            if nonempty:
                applied = apply_source_map(repo, source_map)
                apply_report = applied
            candidate_ready = bool(nonempty)
        except CandidateApplyError as exc:
            apply_report = {"status": "CANDIDATE_APPLY_REFUSED", "error": str(exc)[:300],
                            "repository_modified": False,
                            "official_verifier_invoked": False}
            candidate_ready = False
        engine_status = str(raw.get("status") or "ENGINE_RESULT_INVALID") if isinstance(raw, dict) else "ENGINE_RESULT_INVALID"
        summary = (f"Imported zero-call {language} repair engine ran in a disposable copy; "
                   f"engine_status={engine_status}; candidate_applied={apply_report.get('files_written', 0)}; "
                   f"diff_bytes={diff_bytes}. Official pristine replay decides.")
        return _finish(summary, engine_status=engine_status, language=language,
                       engine=engine_name, engine_result=compact,
                       language_counts=dict(language_counts), markers=markers,
                       marker_errors=marker_errors, staging=staging,
                       test_targets_count=(len(grounding.get("test_candidates", [])[:30]) if language == "python" else 0),
                       candidate_applied=apply_report.get('status') == 'APPLIED__UNVERIFIED',
                       apply=apply_report, diff_bytes=diff_bytes)
    except StageError as exc:
        return _finish(f"Imported repair engines could not stage the workspace: {exc}. Official replay decides.",
                       engine_status="STAGING_REFUSED", staging={"status": "REFUSED", "error": str(exc)},
                       candidate_applied=False, apply={"status": "NO_CANDIDATE_APPLIED"},
                       diff_bytes=0)
    finally:
        shutil.rmtree(temp_parent, ignore_errors=True)


_CIPHER_MARKERS = ("cipher", "ciphertext", "decrypt", "encrypt", "vigenere",
                   "plaintext", "cryptanalysis", "keystream")


def _find_letter_specimen(root: str) -> tuple[str | None, dict[str, int]]:
    """Locate the one letter-dense regular file that may be a ciphertext specimen.

    Computed from the filesystem at decision time; never assumes a filename.
    Bounded: skips bloat dirs, caps scanned files and probe bytes.
    """
    from canonical.runtime.harbor_pro_worktree_v1 import SKIPPED_DIRS  # reuse inspected constants
    best: tuple[int, str] | None = None
    scanned = seen = 0
    SKIP_SUFFIXES = (".py", ".md", ".json", ".toml", ".yaml", ".yml", ".js", ".ts",
                     ".css", ".html", ".so", ".a", ".o", ".bin", ".png", ".jpg", ".gif", ".pdf", ".zip")
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIPPED_DIRS and not d.startswith(".")]
            for name in filenames:
                if scanned >= 1500:
                    return (best[1] if best else None), {"scanned": scanned, "seen": seen}
                scanned += 1
                path = os.path.join(dirpath, name)
                try:
                    if name.lower().endswith(SKIP_SUFFIXES):
                        continue
                    st = os.lstat(path)
                    if not stat.S_ISREG(st.st_mode) or st.st_size < 120 or st.st_size > 512 * 1024:
                        continue
                    with open(path, "rb") as handle:
                        blob = handle.read(8192)
                    letters = sum(1 for b in blob if (65 <= b <= 90) or (97 <= b <= 122))
                    frac = letters / max(len(blob), 1)
                    seen += 1
                    if frac >= 0.85 and letters >= 100:
                        score = letters
                        if best is None or score > best[0]:
                            best = (score, path)
                except OSError:
                    continue
    except OSError:
        pass
    return (best[1] if best else None), {"scanned": scanned, "seen": seen}


def _cipher_candidate_cycle(request, inputs, repo: str) -> dict | None:
    """General classical-cipher capability cycle for TB4-style environments.

    Fires only when the goal names cipher concepts AND the filesystem holds a
    letter-dense specimen. Writes a self-contained cracker (generic algorithm,
    admitted on unseen real-prose victims, never tuned to the task). The
    artifact is a candidate, not a claim of correctness: the official verifier
    decides. Returns None when this capability does not apply.
    """
    instruction = str(inputs.get("harbor_task") or "") + "\n" + str(request.get("goal") or "")
    goal_hit = any(marker in instruction.lower() for marker in _CIPHER_MARKERS)
    if not goal_hit:
        return None
    workspace = repo if Path(repo).is_absolute() else os.getcwd()
    specimen, census = _find_letter_specimen(workspace)
    if specimen is None:
        return None
    from canonical.runtime import classical_cipher_v1 as cc
    try:
        text = Path(specimen).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    cracked = cc.crack(text)
    applied = {"status": "CANDIDATE_EXECUTED_IN_PLACE__UNVERIFIED",
               "official_verifier_invoked": False}
    match = re.search(r"(/[A-Za-z0-9_./-]+\.py)\b", str(request.get("goal") or ""))
    target = None
    if match:
        cand = os.path.normpath(match.group(1))
        if cand.startswith(str(Path(workspace).resolve())) and ".." not in cand:
            target = cand
    if target is None:
        target = str(Path(workspace) / "cracker.py")
    artifact = cc.emit_cracker(target)
    best = cracked.get("best") or {}
    out = _finish(
        (f"Brain classical-cipher engine analysed the specimen ({os.path.basename(specimen)}): "
         f"variant={best.get('variant')}, period(s)={best.get('period')}, "
         f"zlib_margin={cracked.get('zlib_margin_vs_runner_up')}, "
         f"ioc_ciphertext={cracked.get('ioc_ciphertext')}. General cracker written to "
         f"{os.path.basename(target)} (admitted on unseen victims only). Official task verifier decides."),
        engine_status="CANDIDATE_WRITTEN__UNVERIFIED",
        classical_cipher={
            "specimen_scanned": census,
            "ioc_ciphertext": cracked.get("ioc_ciphertext"),
            "variant": best.get("variant"),
            "period": best.get("period"),
            "candidates_tried": cracked.get("candidates_tried"),
            "compressibility_verdict": cracked.get("compressibility_verdict"),
            "zlib_margin_vs_runner_up": cracked.get("zlib_margin_vs_runner_up"),
            "key_recovered_on_specimen": bool(best.get("key")),
            "stats_refused": cracked.get("stats_refused"),
            "artifact_path": artifact.get("path"),
            "artifact_bytes": artifact.get("bytes"),
            "official_verifier_invoked": False,
            "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        },
        workspace=workspace, apply=applied)
    out["engine"] = "classical_cipher_v1"
    out["official_verifier_expected"] = True
    return out


def _terminal_imported_cycle(request, inputs, repo: str) -> dict:
    from canonical.runtime.epistemic_doc_compiler_agent_v1 import (
        solve_multi_step_with_instant_knowledge,
    )

    instruction = str(inputs.get("harbor_task") or "")
    workspace = repo if Path(repo).is_absolute() else os.getcwd()
    cipher = _cipher_candidate_cycle(request, inputs, repo)
    if cipher is not None:
        return cipher
    try:
        doc = solve_multi_step_with_instant_knowledge(
            instruction, workspace=workspace, knowledge_source=None,
            base_url=None, timeout_s=20.0)
    except Exception as exc:
        doc = {"status": "ENGINE_EXCEPTION", "error_type": type(exc).__name__,
               "error": str(exc)[:300], "model_calls": 0, "parameters_stored": 0}

    urls = re.findall(r"https?://[^\s)\]}'\"]+", instruction)
    world = {"status": "NOT_INVOKED__NO_SUPPORTED_URL", "steps": 0}
    if urls:
        try:
            from canonical.runtime.epistemic_world_model_planner_v1 import (
                LiveHTTPWorldAdapter, solve_with_epistemic_world_model)
            adapter = LiveHTTPWorldAdapter(urls[0], timeout_s=5.0)
            raw_world = solve_with_epistemic_world_model(adapter, instruction, max_steps=8)
            world = {k: raw_world.get(k) for k in (
                "status", "mode", "steps", "screens_completed", "actions_executed",
                "destructive_traps_blocked", "model_calls", "parameters_stored")}
            world["status"] = world.get("status") or "PLANNER_ATTEMPTED"
        except Exception as exc:
            world = {"status": "ENGINE_EXCEPTION", "error_type": type(exc).__name__,
                     "error": str(exc)[:300], "steps": 0, "model_calls": 0,
                     "parameters_stored": 0}

    compact_doc = {k: doc.get(k) for k in (
        "status", "mode", "steps_completed", "failed_step_index",
        "binary_used", "subcommand_used", "verification",
        "model_calls", "parameters_stored", "elapsed_ms") if isinstance(doc, dict) and k in doc}
    argv = doc.get("winning_argv") if isinstance(doc, dict) else None
    if isinstance(argv, list):
        compact_doc["winning_argv_sha256"] = hashlib.sha256(
            json.dumps([str(x) for x in argv], sort_keys=True).encode("utf-8")
        ).hexdigest()
        compact_doc["winning_argv_tokens"] = len(argv)
    doc_status = str(doc.get("status") if isinstance(doc, dict) else "ENGINE_RESULT_INVALID")
    summary = (f"Imported local doc compiler ran (status={doc_status}); "
               f"world_model={world.get('status')}. Official task verifier decides.")
    applied = {"status": "CANDIDATE_EXECUTED_IN_PLACE__UNVERIFIED",
               "official_verifier_invoked": False}
    # The in-place candidate ran; the agent (or a later cycle) measures the
    # cumulative /app mutation. No self-reported verification is trusted.
    if doc_status == "VERIFIED":
        return _finish(summary, engine_status="DOC_COMPILER_" + doc_status,
                       doc_compiler=compact_doc, world_model=world,
                       workspace=workspace, apply=applied)
    # Deterministic compiler could not verify locally: fall back to Brain's
    # ordinary solve()/agent loop against the task workspace instead of
    # hard-exiting with zero model invocations.
    root = Path(__file__).resolve().parents[2]
    goal = str(request.get("goal") or "")
    mode = str(request.get("mode") or "EPISTEMIC")
    try:
        fallback = _open_model_fallback(goal, mode, inputs, root)
    except Exception as exc:
        return _finish(summary + f" Fallback to Brain solve failed ({type(exc).__name__}).",
                       engine_status="DOC_COMPILER_" + doc_status,
                       doc_compiler=compact_doc, world_model=world,
                       workspace=workspace, apply=applied,
                       fallback="OPEN_MODEL_UNAVAILABLE",
                       doc_compiler_fallback=compact_doc,
                       fallback_error=type(exc).__name__ + ":" + str(exc)[:200])
    fallback["fallback"] = "OPEN_MODEL_AFTER_" + doc_status
    fallback["engine_status"] = "DOC_COMPILER_" + doc_status
    fallback["doc_compiler"] = compact_doc
    fallback["doc_compiler_fallback"] = compact_doc
    fallback["world_model"] = world
    fallback["workspace"] = workspace
    fallback["apply"] = applied
    return fallback


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
    # Try only the narrow, exact terminal grammar before ordinary model routing.
    # The bridge reads the task workspace and proposes an action; it does not
    # execute the copy or call solve. Unknown tasks use the existing route.
    if inputs.get("harbor_suite") == "terminal-bench-4":
        from canonical.runtime.harbor_terminal_copy_bridge_v1 import propose
        proposal = propose(inputs.get("harbor_task"), inputs.get("observations"), os.getcwd())
        if proposal is not None:
            proposal["proposal_source"] = "DETERMINISTIC_TERMINAL_COPY_V1"
            print(MARKER + json.dumps(proposal, sort_keys=True), flush=True)
            return 0

    # Run the imported zero-call engines before any ordinary model route. This
    # is experimental: it does not establish isolation or official verification.
    repo = inputs.get("harbor_repo")
    if not isinstance(repo, str) or not repo.startswith("/"):
        repo = os.getcwd()
    if inputs.get("observations") == [] and inputs.get("harbor_suite") == "pro-v2":
        result = _pro_imported_cycle(inputs, repo)
        print(MARKER + json.dumps(result, sort_keys=True, default=str), flush=True)
        return 0
    if inputs.get("observations") == [] and inputs.get("harbor_suite") == "terminal-bench-4":
        result = _terminal_imported_cycle(request, inputs, repo)
        print(MARKER + json.dumps(result, sort_keys=True, default=str), flush=True)
        return 0
    if inputs.get("observations") != [] and inputs.get("harbor_suite") in ("pro-v2", "terminal-bench-4"):
        if inputs.get("experimental_candidate_path") is True:
            # Multi-cycle experimental candidate path: keep the Brain agent
            # loop against the workspace instead of hard-exiting.
            root = Path(__file__).resolve().parents[2]
            try:
                result = _open_model_fallback(str(request.get("goal") or ""),
                                              str(request.get("mode") or "EPISTEMIC"),
                                              inputs, root)
                result["fallback"] = "OPEN_MODEL_AFTER_IMPORTED_ENGINE_ROUTE"
            except Exception as exc:
                result = _finish(
                    f"Brain solve() route failed after observed workspace actions ({type(exc).__name__}); finishing.",
                    engine_status="OPEN_MODEL_ROUTE_FAILED",
                    fallback="OPEN_MODEL_UNAVAILABLE",
                    fallback_error=type(exc).__name__ + ":" + str(exc)[:200],
                    apply={"status": "CANDIDATE_EXECUTED_IN_PLACE__UNVERIFIED",
                           "official_verifier_invoked": False})
            print(MARKER + json.dumps(result, sort_keys=True, default=str), flush=True)
            return 0
        result = _finish("Unexpected observations reached the one-cycle imported-engine worker; finishing without further actions.",
                         engine_status="UNEXPECTED_OBSERVATIONS", candidate_applied=False,
                         diff_bytes=0, apply={"status": "NO_CANDIDATE_APPLIED"})
        print(MARKER + json.dumps(result, sort_keys=True, default=str), flush=True)
        return 0

    # Inspect only through this container worker; these hints are untrusted
    # observations, not an executable plan or evidence of a failing test.
    grounding = None
    if inputs.get("harbor_suite") == "pro-v2" and inputs.get("observations") == []:
        from canonical.runtime.harbor_pro_grounding_v1 import ground
        grounding = ground(inputs.get("harbor_task"), inputs.get("harbor_repo"))

    from canonical.runtime.brain_unified_model_v1 import open_model

    # Keep the routing ledger out of the read-only Brain tree. This setting
    # alone cannot constrain all writes made by every route.
    inputs = dict(inputs)
    if grounding is not None:
        inputs["harbor_grounding"] = grounding
    inputs["ledger_db_path"] = "/tmp/brain-harbor-routing.sqlite"
    result = open_model(root=root).solve(
        request["goal"], inputs=inputs, mode=mode, context_paths=[], cwd=os.getcwd()
    )
    if not isinstance(result, dict):
        raise ValueError("SOLVER_RESULT_NOT_OBJECT")
    if grounding is not None:
        result["harbor_grounding"] = grounding
    print(MARKER + json.dumps(result, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
