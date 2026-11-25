"""CI driver for the official SWE-bench Pro V2 (Harbor) eval.

Subcommands
-----------
``materialize``  copy task directories out of a pinned upstream checkout into a
                 work dir, refusing any task whose grading scaffolding is missing
                 (instruction.md / task.toml / tests/) so a silently-neutered task
                 can never inflate a score.
``job-config``   write one Harbor job YAML per shard for a given arm.
``collect``      read a Harbor jobs dir and emit the per-task + aggregate JSON and
                 the markdown table that gets committed under
                 ``canonical/eval/results/``. Numbers come only from files Harbor
                 and the verifier wrote.

Arms
----
``causal``   our engine (zero model calls, zero parameters stored).
``nop``      Harbor's built-in no-op agent: an empty patch MUST resolve nothing.
``oracle``   Harbor's built-in oracle agent: the reference patch MUST resolve
             everything. If this control is not N/N, the task/verifier wiring is
             broken and no causal number from that run means anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
from typing import Any, Mapping

AGENT_IMPORT_PATH = "canonical.eval.harbor.swebench_pro_v2_agent:CausalEngineAgent"
REQUIRED_TASK_FILES = ("instruction.md", "task.toml")
REQUIRED_TASK_DIRS = ("tests",)

ARMS = ("causal", "nop", "oracle")


def read_ids(path: pathlib.Path) -> list[str]:
    ids = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"DUPLICATE_IDS:{path}")
    return ids


def materialize(upstream: pathlib.Path, ids: list[str], dest: pathlib.Path) -> dict[str, Any]:
    tasks_root = upstream / "v2" / "tasks"
    if not tasks_root.is_dir():
        raise SystemExit(f"UPSTREAM_TASKS_MISSING:{tasks_root}")
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for tid in ids:
        src = tasks_root / tid
        missing = [f for f in REQUIRED_TASK_FILES if not (src / f).is_file()]
        missing += [d for d in REQUIRED_TASK_DIRS if not (src / d).is_dir()]
        if not (src / "solution").is_dir():
            missing.append("solution")
        if missing:
            raise SystemExit(f"TASK_INCOMPLETE:{tid}:{','.join(missing)}")
        target = dest / tid
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target, symlinks=True)
        copied.append(tid)
    return {"n_tasks": len(copied), "tasks": copied, "tasks_root": str(dest)}


def job_config(
    *,
    arm: str,
    tasks: list[pathlib.Path],
    jobs_dir: pathlib.Path,
    store_path: pathlib.Path | None = None,
    memory_path: pathlib.Path | None = None,
    n_concurrent: int = 1,
    agent_timeout_s: float = 900.0,
    verifier_timeout_s: float = 1800.0,
    repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    if arm not in ARMS:
        raise SystemExit(f"UNKNOWN_ARM:{arm}")
    agent: dict[str, Any]
    if arm == "causal":
        kwargs: dict[str, Any] = {"agent_timeout_s": agent_timeout_s}
        if store_path:
            kwargs["store_path"] = str(store_path)
        if memory_path:
            kwargs["memory_path"] = str(memory_path)
        agent = {
            "import_path": AGENT_IMPORT_PATH,
            "kwargs": kwargs,
            "override_timeout_sec": agent_timeout_s,
        }
    elif arm == "nop":
        agent = {"name": "nop"}
    else:
        agent = {"name": "oracle"}

    # repo_root is only used to pin where the agent module is imported from; the
    # runner puts it on PYTHONPATH for the host-side agent process (harbor ships no
    # __main__, so `python -m harbor` is not an option).
    repo = repo_root or pathlib.Path(__file__).resolve().parents[3]
    del repo  # not part of the Harbor JobConfig schema; keep the config minimal
    return {
        "job_name": f"swe-pro-v2-{arm}",
        "jobs_dir": str(jobs_dir),
        "n_attempts": 1,
        "timeout_multiplier": 1.0,
        "n_concurrent_trials": n_concurrent,
        "quiet": True,
        "environment": {"type": "docker", "delete": True},
        "verifier": {"override_timeout_sec": verifier_timeout_s},
        "agents": [agent],
        "tasks": [{"path": str(t)} for t in tasks],
    }


def write_job_configs(cfg: dict[str, Any], out_dir: pathlib.Path, shard_ids: list[list[str]], tasks_root: pathlib.Path) -> list[pathlib.Path]:
    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover - PyYAML ships with harbor
        yaml = None  # type: ignore[assignment]
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []
    for idx, ids in enumerate(shard_ids):
        shard_cfg = dict(cfg)
        shard_cfg["job_name"] = f"{cfg['job_name']}-s{idx}"
        shard_cfg["tasks"] = [{"path": str(tasks_root / tid)} for tid in ids]
        p = out_dir / f"job-{idx}.yaml"
        if yaml is not None:
            p.write_text(yaml.safe_dump(shard_cfg, sort_keys=False), encoding="utf-8")
        else:  # pragma: no cover
            p.write_text(json.dumps(shard_cfg, indent=2), encoding="utf-8")
        written.append(p)
    return written


def split_shards(ids: list[str], n_shards: int) -> list[list[str]]:
    """Deterministic round-robin sharding (stable across runs, no hash randomization)."""
    shards: list[list[str]] = [[] for _ in range(max(1, int(n_shards)))]
    for i, tid in enumerate(ids):
        shards[i % len(shards)].append(tid)
    return [s for s in shards if s]


def _looks_like_trial(data: Any) -> bool:
    return bool(
        isinstance(data, dict)
        and "task_name" in data
        and any(
            k in data
            for k in ("trial_name", "verifier_result", "agent_result", "exception_info")
        )
    )


def iter_trial_results(jobs_dir: pathlib.Path):
    """Yield (trial_dir, parsed trial result) for a Harbor jobs directory.

    Located by content, not by depth. Two on-disk shapes are accepted because which
    one exists depends on how the run was invoked: a per-trial ``result.json``
    (a ``TrialResult`` object), and a job-level ``result.json`` carrying the same
    objects in its ``trial_results`` list. Recognising only the first shape made a
    run in which harbor reported ``Trials 3 / Exceptions 0`` and
    ``oracle Mean 1.000`` come out as "no data" — a harness bug dressed up as a
    benchmark result.
    """
    jobs_dir = pathlib.Path(jobs_dir)
    if not jobs_dir.is_dir():
        return
    for path in sorted(jobs_dir.rglob("result.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if _looks_like_trial(data):
            yield path.parent, data
            continue
        if isinstance(data, dict) and isinstance(data.get("trial_results"), list):
            for entry in data["trial_results"]:
                if not _looks_like_trial(entry):
                    continue
                trial_name = str(entry.get("trial_name") or "")
                cand = path.parent / trial_name if trial_name else path.parent
                yield (cand if cand.is_dir() else path.parent), entry


def _reward(trial_dir: pathlib.Path, result: dict[str, Any]) -> float | None:
    vres = result.get("verifier_result") or {}
    rewards = vres.get("rewards")
    if isinstance(rewards, dict) and rewards:
        vals = [float(v) for v in rewards.values() if isinstance(v, (int, float))]
        if vals:
            return max(vals)
    for cand in (
        trial_dir / "verifier" / "reward.txt",
        trial_dir / "logs" / "verifier" / "reward.txt",
    ):
        if cand.is_file():
            try:
                return float(cand.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                return None
    return None


def _agent_report(trial_dir: pathlib.Path) -> dict[str, Any]:
    for cand in (
        trial_dir / "agent" / "causal_engine_report.json",
        trial_dir / "logs" / "agent" / "causal_engine_report.json",
    ):
        if cand.is_file():
            try:
                return json.loads(cand.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}
    hits = sorted(trial_dir.rglob("causal_engine_report.json"))
    for h in hits:
        try:
            return json.loads(h.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
    return {}


def trial_keys(trial_dir: pathlib.Path, res: dict[str, Any]) -> list[str]:
    """Every name a trial answers to, most authoritative first.

    Harbor builds its trial directory from the task name truncated to 32 characters
    (`instance_qutebrowser__qutebrowser-3e21c…` becomes the directory
    `instance_qutebrowser__qutebrowse__42E7bj6`), so a task id read back from the
    trial path or even from ``task_name`` need not equal the id in the manifest. All
    of the plausible spellings are collected and matched tolerantly below.
    """
    out: list[str] = []
    for raw in (
        res.get("task_name"),
        (res.get("task_id") or {}).get("path") if isinstance(res.get("task_id"), dict) else res.get("task_id"),
        res.get("trial_name"),
        trial_dir.name,
    ):
        if not raw:
            continue
        s = str(raw)
        if "/" in s:
            s = s.rstrip("/").rsplit("/", 1)[-1]
        if "__" in s:  # strip harbor's per-trial suffix: <task>__<6 chars>
            head = s.rsplit("__", 1)[0]
            if head:
                out.append(head)
        out.append(s)
    seen: list[str] = []
    for s in out:
        if s and s not in seen:
            seen.append(s)
    return seen


def resolve_task_id(keys: list[str], expected_ids: list[str]) -> str:
    """Which manifest id this trial belongs to, tolerating truncation.

    Exact match wins. Otherwise a key that is a prefix of exactly one expected id is
    accepted — that is what a 32-character harbor name looks like next to a 54-character
    instance id. An ambiguous or unmatched trial keeps its own first key so it still
    appears in the report as an unexplained extra row instead of silently vanishing.
    """
    expected = list(dict.fromkeys(expected_ids))
    for k in keys:
        if k in expected:
            return k
    for k in keys:
        if len(k) < 12:
            continue
        hits = [e for e in expected if e.startswith(k) or k.startswith(e)]
        if len(hits) == 1:
            return hits[0]
    return keys[0] if keys else "UNKNOWN_TRIAL"


def collect(
    jobs_dirs: list[pathlib.Path],
    *,
    arm: str,
    expected_ids: list[str],
    notes: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """`notes` records the conditions a number was measured under (budgets, flags).

    A resolve rate means nothing without the budget it was produced under, and the
    aggregate runs as a different job, so each shard has to carry its own conditions.
    """
    per_task: dict[str, Any] = {}
    for jd in jobs_dirs:
        for td, res in iter_trial_results(pathlib.Path(jd)):
            tid = resolve_task_id(trial_keys(td, res), expected_ids)
            reward = _reward(td, res)
            rep = _agent_report(td)
            start = res.get("started_at")
            end = res.get("finished_at")
            secs: float | None = None
            # `agent_seconds` is what our engine spent; `secs` is harbor's own trial
            # span (container start, agent, verifier). The first smoke run averaged
            # 3.54 s/trial for the causal arm against 48.6 s for the nop control, which
            # is only readable if the two quantities stay in separate columns.
            agent = rep.get("wall_seconds")
            if agent is None:
                agent = rep.get("seconds")
            agent_seconds = round(float(agent), 3) if agent is not None else None
            if start and end:  # pragma: no cover - ISO parse kept simple
                try:
                    from datetime import datetime

                    secs = round((datetime.fromisoformat(str(end).replace("Z", "+00:00")) - datetime.fromisoformat(str(start).replace("Z", "+00:00"))).total_seconds(), 3)
                except Exception:
                    secs = None
            if secs is None:
                secs = agent_seconds
            n_changed = len((rep.get("changed") or {}).get("modified") or []) + len((rep.get("changed") or {}).get("added") or [])
            per_task[tid] = {
                "reward": reward,
                "resolved": reward is not None and float(reward) >= 1.0,
                "exception": (res.get("exception_info") or {}).get("exception_type") if isinstance(res.get("exception_info"), dict) else None,
                "agent_status": rep.get("status") or "NO_AGENT_REPORT",
                "engine_status": rep.get("engine_result_status"),
                "model_calls": rep.get("model_calls", 0),
                "cost_usd": rep.get("cost_usd", 0.0),
                "n_files_changed": n_changed,
                "edits_applied_by": rep.get("edits_applied_by"),
                "tree_changed": rep.get("tree_changed"),
                "store_saved": rep.get("store_saved"),
                "engine_notes": rep.get("notes") or [],
                "error": rep.get("error"),
                "network_attempts": rep.get("network_attempts"),
                "network_guard": rep.get("network_guard"),
                "engine_pass": rep.get("engine_pass"),
                "skills_newly_admissible": rep.get("skills_newly_admissible"),
                "store_note": rep.get("store_note"),
                "seconds": secs,
                "agent_seconds": agent_seconds,
                "store_ablated": rep.get("store_ablated"),
                "trial_dir": str(res.get("trial_name") or td.name),
            }

    ordered = {tid: per_task.get(tid, {"reward": None, "resolved": False, "agent_status": "NOT_RUN", "n_files_changed": 0}) for tid in expected_ids}
    # A trial whose name resolves to nothing in the manifest is kept as an extra row:
    # dropping it is how three scored trials became "no data" here.
    unmatched = [k for k in per_task if k not in set(expected_ids)]
    for k in sorted(unmatched):
        ordered[k] = per_task[k]
    n = len(expected_ids)
    resolved = sum(1 for v in ordered.values() if v.get("resolved"))
    missing = [tid for tid in expected_ids if tid not in per_task]
    secs = [v["seconds"] for v in ordered.values() if isinstance(v.get("seconds"), (int, float))]
    return {
        "arm": arm,
        "n_expected": n,
        "n_reported": len(per_task),
        "n_missing_trial": len(missing),
        "missing_trials": missing,
        "unmatched_trial_keys": sorted(unmatched),
        "conditions": dict(notes or {}),
        "resolved": resolved,
        "resolve_rate_pct": round(100.0 * resolved / n, 2) if n else 0.0,
        "model_calls_total": sum(int(v.get("model_calls") or 0) for v in ordered.values()),
        "cost_usd_total": round(sum(float(v.get("cost_usd") or 0.0) for v in ordered.values()), 4),
        "wall_seconds_total": round(sum(secs), 2) if secs else None,
        "wall_seconds_mean": round(sum(secs) / len(secs), 2) if secs else None,
        "engine_statuses": status_tally(ordered),
        "agent_wall_seconds_total": round(sum(a, 4), 3) if (a := [v["agent_seconds"] for v in ordered.values() if isinstance(v.get("agent_seconds"), (int, float))]) else None,
        "tasks": ordered,
    }


def row_is_real(row: dict[str, Any]) -> bool:
    """True for a row read from a trial harbor ran, false for a NOT_RUN placeholder."""
    return bool(row.get("trial_dir")) or row.get("agent_status") not in (None, "NOT_RUN")


def real_trial_count(rep: dict[str, Any]) -> int:
    """How many rows of an arm report came from a trial harbor actually ran.

    Rows for tasks with no trial data are ``NOT_RUN`` placeholders and carry no
    ``trial_dir``. Counting them as reported is what made two void runs look, in the
    machine-readable report, like a measured 0/N — the markdown shouted "no trial
    data" while the JSON said ``run_produced_number: true``.
    """
    return sum(1 for v in (rep.get("tasks") or {}).values() if row_is_real(v))


def compute_gates(arm_reports: dict[str, dict[str, Any]]) -> dict[str, bool]:
    causal_oracle = arm_reports.get("oracle") or {}
    nop = arm_reports.get("nop") or {}
    return {
        "oracle_gate_pass": bool(causal_oracle.get("n_expected"))
        and real_trial_count(causal_oracle) == causal_oracle["n_expected"]
        and all(v.get("resolved") for v in (causal_oracle.get("tasks") or {}).values()),
        "nop_gate_pass": bool(nop.get("n_expected"))
        and real_trial_count(nop) == nop["n_expected"]
        and not any(v.get("resolved") for v in (nop.get("tasks") or {}).values()),
    }


def status_tally(ordered: dict[str, Any]) -> dict[str, int]:
    """How the agent behaved, independent of whether it passed.

    0/N reads differently if the engine never acted (NO_EDITS / UPLOAD_BLOCKED /
    NO_AGENT_REPORT) than if it edited every tree and the hidden tests disagreed.
    """
    tally: dict[str, int] = {}
    for v in ordered.values():
        key = str(v.get("agent_status") or "UNKNOWN")
        tally[key] = tally.get(key, 0) + 1
    return tally


def merge_arm_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge per-shard reports of one arm into a single view.

    Shards are disjoint by construction, so the honest merge is by TASK union:
    a task counts once (real entries win over ``NOT_RUN`` placeholders), the
    expectation set is the union of every shard's expected ids, and totals are
    recomputed from the union rather than summed across shards.
    """
    tasks: dict[str, dict[str, Any]] = {}
    expected: list[str] = []
    for rep in reports:
        for tid in rep.get("tasks") or {}:
            if tid not in expected:
                expected.append(tid)
        for tid, row in (rep.get("tasks") or {}).items():
            cur = tasks.get(tid)
            if cur is None or (cur.get("agent_status") == "NOT_RUN" and row.get("agent_status") != "NOT_RUN"):
                tasks[tid] = dict(row)
    expected.sort()
    unmatched = sorted({k for rep in reports for k in (rep.get("unmatched_trial_keys") or [])})
    conditions: dict[str, Any] = {}
    for rep in reports:
        conditions.update(rep.get("conditions") or {})
    ordered = {tid: tasks.get(tid, {"reward": None, "resolved": False, "agent_status": "NOT_RUN", "n_files_changed": 0}) for tid in expected}
    resolved = sum(1 for v in ordered.values() if v.get("resolved"))
    secs = [v["seconds"] for v in ordered.values() if isinstance(v.get("seconds"), (int, float))]
    arm = str((reports[0].get("arm") if reports else "") or "causal")
    return {
        "arm": arm,
        "n_expected": len(expected),
        "n_reported": sum(1 for v in ordered.values() if row_is_real(v)),
        "n_missing_trial": sum(1 for v in ordered.values() if v.get("agent_status") == "NOT_RUN"),
        "missing_trials": [t for t, v in ordered.items() if v.get("agent_status") == "NOT_RUN"],
        "unmatched_trial_keys": unmatched,
        "conditions": conditions,
        "n_shard_reports": len(reports),
        "resolved": resolved,
        "resolve_rate_pct": round(100.0 * resolved / len(expected), 2) if expected else 0.0,
        "model_calls_total": sum(int(v.get("model_calls") or 0) for v in ordered.values()),
        "cost_usd_total": round(sum(float(v.get("cost_usd") or 0.0) for v in ordered.values()), 4),
        "wall_seconds_total": round(sum(secs), 2) if secs else None,
        "wall_seconds_mean": round(sum(secs) / len(secs), 2) if secs else None,
        "agent_wall_seconds_total": round(sum(a, 4), 3) if (a := [v["agent_seconds"] for v in ordered.values() if isinstance(v.get("agent_seconds"), (int, float))]) else None,
        "engine_statuses": status_tally(ordered),
        "tasks": ordered,
    }


def to_markdown(
    arm_reports: dict[str, dict[str, Any]],
    *,
    benchmark: str,
    commit: str,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[str]:
    void = all(not rep.get("n_reported") for rep in arm_reports.values()) if arm_reports else True
    lines = [
        f"# {benchmark} — engine eval (measured run)",
        "",
        f"- upstream/eval commit recorded by CI: `{commit}`",
        "- Resolve decisions come from each task's own verifier inside the official container image.",
        "- `nop` must resolve 0/N and `oracle` must resolve N/N or the causal number is not interpretable.",
        "",
        *(
            ["- Measured under: " + ", ".join(f"`{k}={v}`" for k, v in sorted(conditions.items()))]
            if (conditions := {k: v for rep in arm_reports.values() for k, v in (rep.get("conditions") or {}).items()})
            else []
        ),
        "| arm | resolved | tasks | resolve % | model calls | cost USD | trial wall s (total) | engine s (total) | missing trials |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for arm in ARMS:
        rep = arm_reports.get(arm)
        if not rep:
            continue
        lines.append(
            "| {arm} | {res} | {n} | {rate} | {mc} | {cost} | {wt} | {wm} | {miss} |".format(
                arm=arm,
                res=rep["resolved"],
                n=rep["n_expected"],
                rate=rep["resolve_rate_pct"],
                mc=rep["model_calls_total"],
                cost=rep["cost_usd_total"],
                wt=rep["wall_seconds_total"],
                wm=rep.get("agent_wall_seconds_total"),
                miss=rep["n_missing_trial"],
            )
        )
    lines.append("")
    causal = arm_reports.get("causal") or {}
    gates = compute_gates(arm_reports)
    lines += ["## Harness gates", ""]
    for k, v in gates.items():
        lines.append(f"- `{k}`: **{'PASS' if v else 'FAIL'}**")
    if void:
        lines += [
            "",
            "> **NO TRIAL DATA — THIS RUN PRODUCED NO BENCHMARK NUMBER.**",
            "> No `result.json` was found for any expected task, so the 0/N columns below are",
            "> a harness failure, not a score. Do not quote them as a resolve rate.",
        ]
    if diagnostics:
        lines += [
            "",
            "## Shard diagnostics (harness truth: did harbor even start trials?)",
            "",
            "| artifact | harbor exit | log lines kept | last line |",
            "|---|---|---|---|",
        ]
        for d in diagnostics:
            lines.append(
                f"| `{d.get('source', '?')}` | {d.get('harbor_exit_code')} "
                f"| {d.get('harbor_log_line_count')} | `{str((d.get('harbor_log_last_lines') or [''])[-1])[:110]}` |"
            )
    lines += [
        "",
        "## Per-task (causal arm)",
        "",
        "| task | reward | resolved | agent status | engine status | engine pass | files | harness error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for tid, t in (causal.get("tasks") or {}).items():
        lines.append(
            f"| `{tid[:56]}` | {t.get('reward')} | {'yes' if t.get('resolved') else 'no'} "
            f"| {t.get('agent_status')} | {t.get('engine_status')} | {t.get('engine_pass')} "
            f"| {t.get('n_files_changed')} | {(str(t.get('error'))[:48] if t.get('error') else '')} |"
        )
    not_engine = sum(
        1
        for t in (causal.get("tasks") or {}).values()
        if t.get("agent_status")
        in ("HARNESS_ERROR", "NO_AGENT_REPORT", "UPLOAD_BLOCKED", "TREE_TOO_BIG", "EMPTY_TREE", "NOT_RUN")
    )
    if not_engine:
        lines += [
            "",
            f"**{not_engine} of {causal.get('n_expected')} causal trials are not attributable to the engine** "
            "(harness error, blocked upload, or no trial read). The measured rate stays "
            f"0/{causal.get('n_expected')} as a benchmark number — a run counts what actually ran, failures "
            f"included — but the engine-attributable denominator is {causal.get('n_expected') - not_engine}, "
            "and that is the number to quote about the engine.",
        ]
    stray = sorted({k for rep in arm_reports.values() for k in (rep.get("unmatched_trial_keys") or [])})
    if stray and any(rep.get("n_missing_trial") for rep in arm_reports.values()):
        lines += [
            "",
            "### Names the manifest did not recognise (read this before the table above)",
            "",
            "Trials ran and were scored, but their task names do not match the ids the job "
            "asked for — harbor builds a trial's name from the task name truncated to 32 "
            "characters. The resolve rate is therefore about those rows, not about the "
            "manifest, and the mismatch must be reconciled before any number is quoted: "
            + ", ".join(f"`{s}`" for s in stray[:8]),
        ]
    tally = (causal.get("engine_statuses") or {}) if causal else {}
    if tally:
        lines += [
            "",
            "What the engine did across the causal arm (behaviour, not a score): "
            + ", ".join(f"`{k}`×{v}" for k, v in sorted(tally.items()))
            + ". Resolve rate is decided only by each task's own verifier.",
        ]
    net = sum(int(t.get("network_attempts") or 0) for t in (causal.get("tasks") or {}).values())
    if net:
        lines += [
            "",
            f"Outbound network attempts refused by the harness during the causal arm: **{net}** "
            "(`allow_web` is enforced, not requested). A zero here is what 'this run needed no "
            "external knowledge' means operationally.",
        ]
    lines.append("")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="swe_pro_v2_ci")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("materialize")
    m.add_argument("--upstream", required=True)
    m.add_argument("--ids", required=True)
    m.add_argument("--dest", required=True)
    m.add_argument("--out-manifest", default="")

    j = sub.add_parser("job-config")
    j.add_argument("--arm", required=True, choices=list(ARMS))
    j.add_argument("--manifest", required=True)
    j.add_argument("--jobs-dir", required=True)
    j.add_argument("--out-dir", required=True)
    j.add_argument("--n-shards", type=int, default=1)
    j.add_argument("--store-path", default="")
    j.add_argument("--memory-path", default="")
    j.add_argument("--n-concurrent", type=int, default=1)
    j.add_argument("--agent-timeout-s", type=float, default=900.0)

    c = sub.add_parser("collect")
    c.add_argument("--jobs-dir", action="append", required=True)
    c.add_argument("--manifest", required=True)
    c.add_argument("--arm", required=True, choices=list(ARMS))
    c.add_argument("--out", required=True)

    s = sub.add_parser("split")
    s.add_argument("--ids", required=True)
    s.add_argument("--n-shards", type=int, default=6)
    s.add_argument("--shard", type=int, required=True)
    s.add_argument("--out", required=True)

    a = sub.add_parser("aggregate")
    a.add_argument("--reports", action="append", required=True)
    a.add_argument(
        "--meta",
        action="append",
        default=[],
        help="per-shard diagnostics JSON (harbor exit code + log tail)",
    )
    a.add_argument("--out-json", required=True)
    a.add_argument("--out-md", required=True)
    a.add_argument("--benchmark", default="SWE-bench Pro V2 (HARD-51)")
    a.add_argument("--commit", default="unknown")

    args = ap.parse_args(argv)

    if args.cmd == "materialize":
        ids = read_ids(pathlib.Path(args.ids))
        rep = materialize(pathlib.Path(args.upstream), ids, pathlib.Path(args.dest))
        if args.out_manifest:
            pathlib.Path(args.out_manifest).write_text(json.dumps(rep, indent=2), encoding="utf-8")
        print(json.dumps({"n_tasks": rep["n_tasks"]}))
        return 0

    if args.cmd == "split":
        ids = read_ids(pathlib.Path(args.ids))
        shards = split_shards(ids, args.n_shards)
        if args.shard >= len(shards):
            print("")  # empty shard: job skips
            return 0
        pathlib.Path(args.out).write_text("\n".join(shards[args.shard]) + "\n", encoding="utf-8")
        return 0

    if args.cmd == "job-config":
        manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
        tasks_root = pathlib.Path(manifest["tasks_root"])
        ids = list(manifest["tasks"])
        shards = split_shards(ids, args.n_shards)
        cfg = job_config(
            arm=args.arm,
            tasks=[tasks_root / t for t in ids],
            jobs_dir=pathlib.Path(args.jobs_dir),
            store_path=pathlib.Path(args.store_path) if args.store_path else None,
            memory_path=pathlib.Path(args.memory_path) if args.memory_path else None,
            n_concurrent=args.n_concurrent,
            agent_timeout_s=args.agent_timeout_s,
        )
        written = write_job_configs(cfg, pathlib.Path(args.out_dir), shards, tasks_root)
        print(json.dumps({"configs": [str(p) for p in written], "n_shards": len(written)}))
        return 0

    if args.cmd == "collect":
        manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
        notes: dict[str, Any] = {}
        for raw in args.note:
            k, sep, v = raw.partition("=")
            if not sep:
                raise SystemExit(f"--note expects KEY=VALUE, got {raw!r}")
            try:
                notes[k.strip()] = int(v)
            except ValueError:
                notes[k.strip()] = v
        rep = collect([pathlib.Path(p) for p in args.jobs_dir], arm=args.arm, expected_ids=list(manifest["tasks"]), notes=notes)
        pathlib.Path(args.out).write_text(json.dumps(rep, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({k: rep[k] for k in ("arm", "resolved", "n_expected", "resolve_rate_pct", "model_calls_total", "cost_usd_total")}))
        return 0

    if args.cmd == "aggregate":
        by_arm: dict[str, list[dict[str, Any]]] = {}
        for p in args.reports:
            data = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
            if data.get("error"):
                continue
            by_arm.setdefault(str(data.get("arm") or "causal"), []).append(data)
        reports = {arm: merge_arm_reports(rep_list) for arm, rep_list in by_arm.items()}
        diagnostics: list[dict[str, Any]] = []
        for mp in args.meta:
            try:
                data = json.loads(pathlib.Path(mp).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            data["source"] = pathlib.Path(mp).name
            diagnostics.append(data)
        void_run = all(not real_trial_count(r) for r in reports.values()) if reports else True
        out = {
            "schema": "brain.bench_eval_report.v1",
            "arms": reports,
            "run_produced_number": not void_run,
            "n_reports_read": len(args.reports),
            "benchmark": args.benchmark,
            "commit": args.commit,
            "gates": compute_gates(reports),
            "conditions": {k: v for rep in reports.values() for k, v in (rep.get("conditions") or {}).items()},
            "shard_diagnostics": diagnostics,
            "note": "Resolve decisions come from each task's own verifier inside the "
            "official container image. Merged across shards by task union.",
        }
        pathlib.Path(args.out_json).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
        pathlib.Path(args.out_md).write_text(
            "\n".join(
                to_markdown(
                    reports,
                    benchmark=args.benchmark,
                    commit=args.commit,
                    diagnostics=diagnostics,
                )
            )
            + "\n",
            encoding="utf-8",
        )
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
