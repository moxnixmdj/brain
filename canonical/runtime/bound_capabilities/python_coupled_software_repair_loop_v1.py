#!/usr/bin/env python3
"""Bounded donor-free Python repair loop with atomic neutral-intermediate coupled edits.

This capability extends the strict-progress loop with one narrowly defined
mechanism: when no single candidate strictly improves the aggregate test
failure score, it may cross ONE neutral intermediate state by pairing two
deterministically generated edits. The first edit is never retained alone.
The pair is accepted atomically only when the aggregate oracle strictly
improves. All probe mutations are restored.

No model calls, network calls, package installation, benchmark-specific data,
or canonical writes occur.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import pathlib
import re
import sys
from typing import Any, Iterable, Mapping

from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch

SCHEMA = "PROJECT_BRAIN_PYTHON_COUPLED_SOFTWARE_REPAIR_LOOP_V1"
CAPABILITY_ID = "python.software.repair.loop.coupled_neutral.ast.v1"


class CoupledRepairError(RuntimeError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_dir(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (repo / str(raw or ".")).resolve()
    if p != repo and repo not in p.parents:
        raise CoupledRepairError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink():
        raise CoupledRepairError("DIRECTORY_INVALID")
    return p


def _safe_file(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p == repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix != ".py":
        raise CoupledRepairError("FILE_INVALID:" + str(raw))
    return p


def _rel(repo: pathlib.Path, p: pathlib.Path) -> str:
    return str(p.relative_to(repo)).replace("\\", "/")


def _text(result: Mapping[str, Any]) -> str:
    return str(result.get("stdout") or "") + "\n" + str(result.get("stderr") or "")


def _score(result: Mapping[str, Any]) -> int | None:
    if result.get("timed_out"):
        return None
    if result.get("returncode") == 0:
        return 0
    text = _text(result)
    m = re.search(r"FAILED\s*\(([^)]*)\)", text)
    if m:
        values = re.findall(r"(failures|errors)=(\d+)", m.group(1))
        total = sum(int(v) for _, v in values)
        if total:
            return total
    count = len(re.findall(r"(?m)^(?:FAIL|ERROR):\s", text))
    return count or None


def _purge(paths: Iterable[pathlib.Path]) -> None:
    for p in paths:
        patch._purge_source_bytecode(p)


def _source_symbols(path: pathlib.Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Name):
            out.add(node.id)
    return {x for x in out if len(x) >= 2}


def _import_targets(repo: pathlib.Path, test: pathlib.Path, source_root: pathlib.Path) -> set[pathlib.Path]:
    try:
        tree = ast.parse(test.read_text(encoding="utf-8"), filename=str(test))
    except Exception:
        return set()
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    out: set[pathlib.Path] = set()
    for name in names:
        rel = pathlib.Path(*name.split("."))
        for candidate in (source_root / rel.with_suffix(".py"), source_root / rel / "__init__.py"):
            try:
                q = candidate.resolve()
            except OSError:
                continue
            if q.is_file() and q.suffix == ".py" and (q == source_root or source_root in q.parents):
                out.add(q)
    return out


def localize_sources(
    repo: pathlib.Path,
    source_root: pathlib.Path,
    tests: list[pathlib.Path],
    failure: Mapping[str, Any],
    *,
    max_files: int,
) -> list[dict[str, Any]]:
    failure_text = _text(failure)
    traceback_paths: set[pathlib.Path] = set()
    for raw in re.findall(r'File "([^"]+\.py)"', failure_text):
        p = pathlib.Path(raw)
        q = (p if p.is_absolute() else repo / p).resolve()
        if q.is_file() and q.suffix == ".py" and q not in tests and (q == source_root or source_root in q.parents):
            traceback_paths.add(q)

    imported: set[pathlib.Path] = set()
    for test in tests:
        imported |= _import_targets(repo, test, source_root)

    candidates: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()
    for p in list(traceback_paths) + list(imported) + sorted(source_root.rglob("*.py")):
        q = p.resolve()
        if q in seen or q in tests or q.name.startswith("test_") or q.suffix != ".py":
            continue
        if q != source_root and source_root not in q.parents:
            continue
        seen.add(q)
        candidates.append(q)

    rows: list[dict[str, Any]] = []
    lowered = failure_text.lower()
    for p in candidates:
        symbols = _source_symbols(p)
        symbol_hits = sorted(s for s in symbols if s.lower() in lowered)
        traceback_hit = p in traceback_paths
        import_hit = p in imported
        score = (100 if traceback_hit else 0) + (50 if import_hit else 0) + 5 * len(symbol_hits)
        rows.append({
            "path": p,
            "source_path": _rel(repo, p),
            "localization_score": score,
            "traceback_hit": traceback_hit,
            "test_import_hit": import_hit,
            "symbol_hits": symbol_hits[:20],
        })
    rows.sort(key=lambda r: (-int(r["localization_score"]), str(r["source_path"])))
    return rows[:max_files]


def _mutations(source: pathlib.Path, tests: list[pathlib.Path], limit: int):
    raw = source.read_bytes()
    try:
        text = raw.decode("utf-8")
        tree = ast.parse(text, filename=str(source))
    except Exception:
        return
    nums, strings = patch._test_literals(tests)
    emitted = 0
    for key, desc, replacer in patch._candidate_specs(tree, nums, strings):
        if emitted >= limit:
            break
        candidate = patch._render_candidate(text, key, replacer)
        if not candidate or candidate == text:
            continue
        emitted += 1
        yield {
            "bytes": candidate.encode("utf-8"),
            "mutation": desc,
            "sha256": _sha(candidate.encode("utf-8")),
        }


def _run(repo: pathlib.Path, argv: list[str], timeout: int) -> dict[str, Any]:
    return patch._run_tests(repo, argv, timeout)


def _diff(repo: pathlib.Path, p: pathlib.Path, before: bytes, after: bytes) -> str:
    return "".join(difflib.unified_diff(
        before.decode("utf-8").splitlines(True),
        after.decode("utf-8").splitlines(True),
        fromfile="a/" + _rel(repo, p),
        tofile="b/" + _rel(repo, p),
    ))


def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise CoupledRepairError("ARGS_NOT_OBJECT")
    repo = pathlib.Path(root).resolve()
    source_root = _safe_dir(repo, args.get("source_root", "."))
    raw_tests = args.get("test_paths") or []
    if not isinstance(raw_tests, list) or not raw_tests:
        raise CoupledRepairError("TEST_PATHS_REQUIRED")
    tests = [_safe_file(repo, x) for x in raw_tests]
    argv = [str(x) for x in (args.get("test_argv") or [sys.executable] + [_rel(repo, p) for p in tests])]
    if not argv:
        raise CoupledRepairError("TEST_ARGV_REQUIRED")

    timeout = max(1, min(int(args.get("timeout_s", 30)), 300))
    max_rounds = max(1, min(int(args.get("max_rounds", 6)), 20))
    max_files = max(1, min(int(args.get("max_files", 8)), 50))
    per_file = max(1, min(int(args.get("max_candidates_per_file", 60)), 1000))
    max_pair_first = max(1, min(int(args.get("max_pair_first_candidates", 80)), 2000))
    max_pair_second = max(1, min(int(args.get("max_pair_second_candidates", 80)), 2000))
    total_budget = max(1, min(int(args.get("max_total_candidates", 3000)), 50000))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise CoupledRepairError("OUTPUT_PATH_OUTSIDE_REPOSITORY")

    baseline = _run(repo, argv, timeout)
    baseline_score = _score(baseline)
    if baseline.get("timed_out"):
        raise CoupledRepairError("BASELINE_TIMEOUT")
    if baseline.get("returncode") == 0:
        raise CoupledRepairError("BASELINE_ALREADY_PASSES")
    if baseline_score is None:
        raise CoupledRepairError("BASELINE_FAILURE_METRIC_UNPARSEABLE")

    all_sources = [p for p in sorted(source_root.rglob("*.py")) if p not in tests and not p.name.startswith("test_")]
    originals = {p: p.read_bytes() for p in all_sources}
    current = baseline
    current_score = baseline_score
    accepted: list[dict[str, Any]] = []
    localization_history: list[dict[str, Any]] = []
    tested_total = 0
    pair_probe_count = 0
    neutral_first_count = 0
    final_bytes: dict[pathlib.Path, bytes] = {}
    verification_replays: list[dict[str, Any]] = []
    status = "OPEN__NO_COMPLETE_REPAIR_IN_BOUNDED_SEARCH"

    try:
        for round_index in range(1, max_rounds + 1):
            localized = localize_sources(repo, source_root, tests, current, max_files=max_files)
            localization_history.append({
                "round": round_index,
                "failure_score": current_score,
                "ranked": [{k: v for k, v in row.items() if k != "path"} for row in localized],
            })
            if not localized:
                status = "OPEN__NO_LOCALIZED_SOURCES"
                break

            # Phase A: ordinary strict-progress single edit.
            single_winner = None
            for row in localized:
                source = row["path"]
                before = source.read_bytes()
                for cand in _mutations(source, tests, min(per_file, total_budget - tested_total)):
                    if tested_total >= total_budget:
                        break
                    tested_total += 1
                    source.write_bytes(cand["bytes"])
                    _purge([source])
                    obs = _run(repo, argv, timeout)
                    source.write_bytes(before)
                    _purge([source])
                    score = _score(obs)
                    if score is not None and score < current_score:
                        single_winner = (source, cand, score)
                        break
                if single_winner or tested_total >= total_budget:
                    break

            if single_winner:
                source, cand, new_score = single_winner
                before = source.read_bytes()
                source.write_bytes(cand["bytes"])
                _purge([source])
                replay = _run(repo, argv, timeout)
                replay_score = _score(replay)
                if replay_score != new_score or replay_score is None or replay_score >= current_score:
                    raise CoupledRepairError("SINGLE_WINNER_REPLAY_NOT_STRICT")
                accepted.append({
                    "round": round_index,
                    "kind": "STRICT_SINGLE",
                    "edits": [{
                        "source_path": _rel(repo, source),
                        "mutation": cand["mutation"],
                        "candidate_sha256": cand["sha256"],
                    }],
                    "score_before": current_score,
                    "score_after": replay_score,
                })
                current = replay
                current_score = replay_score
                if current_score == 0:
                    status = "PASS__BOUNDED_COUPLED_REPAIR_FOUND"
                    break
                continue

            # Phase B: atomic pair search across one neutral intermediate.
            pair_winner = None
            first_seen = 0
            for row1 in localized:
                source1 = row1["path"]
                base1 = source1.read_bytes()
                for cand1 in _mutations(source1, tests, per_file):
                    if first_seen >= max_pair_first or tested_total >= total_budget:
                        break
                    first_seen += 1
                    tested_total += 1
                    source1.write_bytes(cand1["bytes"])
                    _purge([source1])
                    obs1 = _run(repo, argv, timeout)
                    score1 = _score(obs1)
                    if score1 != current_score:
                        source1.write_bytes(base1)
                        _purge([source1])
                        continue
                    neutral_first_count += 1

                    localized2 = localize_sources(repo, source_root, tests, obs1, max_files=max_files)
                    second_seen = 0
                    for row2 in localized2:
                        source2 = row2["path"]
                        state2 = source2.read_bytes()
                        for cand2 in _mutations(source2, tests, per_file):
                            if second_seen >= max_pair_second or tested_total >= total_budget:
                                break
                            second_seen += 1
                            pair_probe_count += 1
                            tested_total += 1
                            source2.write_bytes(cand2["bytes"])
                            _purge({source1, source2})
                            obs2 = _run(repo, argv, timeout)
                            score2 = _score(obs2)
                            source2.write_bytes(state2)
                            _purge({source1, source2})
                            if score2 is not None and score2 < current_score:
                                pair_winner = (
                                    source1, cand1, source2, cand2, score2
                                )
                                break
                        if pair_winner or second_seen >= max_pair_second or tested_total >= total_budget:
                            break
                    source1.write_bytes(base1)
                    _purge([source1])
                    if pair_winner:
                        break
                if pair_winner or first_seen >= max_pair_first or tested_total >= total_budget:
                    break

            if pair_winner is None:
                status = (
                    "OPEN__NO_STRICT_OR_NEUTRAL_COUPLED_IMPROVEMENT"
                    if tested_total < total_budget
                    else "OPEN__CANDIDATE_BUDGET_EXHAUSTED"
                )
                break

            source1, cand1, source2, cand2, pair_score = pair_winner
            # Apply the pair atomically. If source2 == source1, cand2 was generated
            # from the first-edited source and therefore already contains both edits.
            if source2 == source1:
                source1.write_bytes(cand2["bytes"])
            else:
                source1.write_bytes(cand1["bytes"])
                source2.write_bytes(cand2["bytes"])
            _purge({source1, source2})
            replay = _run(repo, argv, timeout)
            replay_score = _score(replay)
            if replay_score != pair_score or replay_score is None or replay_score >= current_score:
                raise CoupledRepairError("COUPLED_WINNER_REPLAY_NOT_STRICT")
            accepted.append({
                "round": round_index,
                "kind": "NEUTRAL_INTERMEDIATE_COUPLED_PAIR",
                "edits": [
                    {
                        "source_path": _rel(repo, source1),
                        "mutation": cand1["mutation"],
                        "candidate_sha256": cand1["sha256"],
                    },
                    {
                        "source_path": _rel(repo, source2),
                        "mutation": cand2["mutation"],
                        "candidate_sha256": cand2["sha256"],
                    },
                ],
                "intermediate_score": current_score,
                "score_before": current_score,
                "score_after": replay_score,
            })
            current = replay
            current_score = replay_score
            if current_score == 0:
                status = "PASS__BOUNDED_COUPLED_REPAIR_FOUND"
                break

        if current_score == 0:
            touched = [p for p in all_sources if p.read_bytes() != originals[p]]
            for _ in range(2):
                _purge(touched)
                rr = _run(repo, argv, timeout)
                rs = _score(rr)
                verification_replays.append({
                    "returncode": rr.get("returncode"),
                    "timed_out": rr.get("timed_out"),
                    "failure_score": rs,
                })
                if rr.get("returncode") != 0 or rs != 0:
                    raise CoupledRepairError("FINAL_REPLAY_FAILED")
            final_bytes = {p: p.read_bytes() for p in touched}
            status = "PASS__BOUNDED_COUPLED_REPAIR_FOUND"
    finally:
        for p, raw in originals.items():
            p.write_bytes(raw)
        _purge(originals)

    patches = [
        {
            "source_path": _rel(repo, p),
            "original_sha256": _sha(originals[p]),
            "candidate_sha256": _sha(final_bytes[p]),
            "unified_diff": _diff(repo, p, originals[p], final_bytes[p]),
        }
        for p in sorted(final_bytes, key=lambda q: _rel(repo, q))
    ]

    result = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": status,
        "pass": status.startswith("PASS__"),
        "baseline_failure_score": baseline_score,
        "final_failure_score": current_score,
        "accepted_actions": accepted,
        "accepted_action_count": len(accepted),
        "coupled_pair_count": sum(x["kind"] == "NEUTRAL_INTERMEDIATE_COUPLED_PAIR" for x in accepted),
        "neutral_first_candidates_observed": neutral_first_count,
        "pair_probe_count": pair_probe_count,
        "tested_candidate_count": tested_total,
        "localization_history": localization_history,
        "final_verification_replays": verification_replays,
        "patches": patches,
        "source_restored": all(p.read_bytes() == raw for p, raw in originals.items()),
        "model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_UNIVERSAL_SOFTWARE_REPAIR_COMPLETENESS",
            "NO_GENERAL_SEMANTIC_FAULT_LOCALIZATION_COMPLETENESS",
            "NO_NON_PYTHON_SUPPORT",
            "NO_HIDDEN_REQUIREMENTS_OR_MERGEABILITY_PROOF",
            "NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY",
            "NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["output_path"] = _rel(repo, output)
    result["output_sha256"] = _sha(output.read_bytes())
    result["output_verified"] = True
    return result
