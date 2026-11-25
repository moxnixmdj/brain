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
from typing import Any

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


def _trial_dirs(jobs_dir: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p.parent for p in jobs_dir.glob("*/*/result.json"))


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


def collect(jobs_dirs: list[pathlib.Path], *, arm: str, expected_ids: list[str]) -> dict[str, Any]:
    per_task: dict[str, Any] = {}
    for jd in jobs_dirs:
        for td in _trial_dirs(jd):
            try:
                res = json.loads((td / "result.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            tid = str(res.get("task_name") or td.name)
            reward = _reward(td, res)
            rep = _agent_report(td)
            start = res.get("started_at")
            end = res.get("finished_at")
            secs: float | None = None
            if rep.get("wall_seconds") is not None:
                secs = float(rep["wall_seconds"])
            elif start and end:  # pragma: no cover - ISO parse kept simple
                try:
                    from datetime import datetime

                    secs = round((datetime.fromisoformat(str(end).replace("Z", "+00:00")) - datetime.fromisoformat(str(start).replace("Z", "+00:00"))).total_seconds(), 3)
                except Exception:
                    secs = None
            n_changed = len((rep.get("changed") or {}).get("modified") or []) + len((rep.get("changed") or {}).get("added") or [])
            per_task[tid] = {
                "reward": reward,
                "resolved": reward is not None and float(reward) >= 1.0,
                "exception": (res.get("exception_info") or {}).get("exception_type") if isinstance(res.get("exception_info"), dict) else None,
                "agent_status": rep.get("status"),
                "engine_status": rep.get("engine_result_status"),
                "model_calls": rep.get("model_calls", 0),
                "cost_usd": rep.get("cost_usd", 0.0),
                "n_files_changed": n_changed,
                "seconds": secs,
                "store_ablated": rep.get("store_ablated"),
                "trial_dir": td.name,
            }

    ordered = {tid: per_task.get(tid, {"reward": None, "resolved": False, "agent_status": "NOT_RUN", "n_files_changed": 0}) for tid in expected_ids}
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
        "resolved": resolved,
        "resolve_rate_pct": round(100.0 * resolved / n, 2) if n else 0.0,
        "model_calls_total": sum(int(v.get("model_calls") or 0) for v in ordered.values()),
        "cost_usd_total": round(sum(float(v.get("cost_usd") or 0.0) for v in ordered.values()), 4),
        "wall_seconds_total": round(sum(secs), 2) if secs else None,
        "wall_seconds_mean": round(sum(secs) / len(secs), 2) if secs else None,
        "tasks": ordered,
    }


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
    ordered = {tid: tasks.get(tid, {"reward": None, "resolved": False, "agent_status": "NOT_RUN", "n_files_changed": 0}) for tid in expected}
    resolved = sum(1 for v in ordered.values() if v.get("resolved"))
    secs = [v["seconds"] for v in ordered.values() if isinstance(v.get("seconds"), (int, float))]
    arm = str((reports[0].get("arm") if reports else "") or "causal")
    return {
        "arm": arm,
        "n_expected": len(expected),
        "n_reported": len(tasks),
        "n_missing_trial": sum(1 for v in ordered.values() if v.get("agent_status") == "NOT_RUN"),
        "missing_trials": [t for t, v in ordered.items() if v.get("agent_status") == "NOT_RUN"],
        "n_shard_reports": len(reports),
        "resolved": resolved,
        "resolve_rate_pct": round(100.0 * resolved / len(expected), 2) if expected else 0.0,
        "model_calls_total": sum(int(v.get("model_calls") or 0) for v in ordered.values()),
        "cost_usd_total": round(sum(float(v.get("cost_usd") or 0.0) for v in ordered.values()), 4),
        "wall_seconds_total": round(sum(secs), 2) if secs else None,
        "wall_seconds_mean": round(sum(secs) / len(secs), 2) if secs else None,
        "tasks": ordered,
    }


def to_markdown(arm_reports: dict[str, dict[str, Any]], *, benchmark: str, commit: str) -> list[str]:
    lines = [
        f"# {benchmark} — engine eval (real run)",
        "",
        f"- upstream/eval commit recorded by CI: `{commit}`",
        "- Resolve decisions come from each task's own verifier inside the official container image.",
        "- `nop` must resolve 0/N and `oracle` must resolve N/N or the causal number is not interpretable.",
        "",
        "| arm | resolved | tasks | resolve % | model calls | cost USD | wall s (total) | wall s (mean) | missing trials |",
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
                wm=rep["wall_seconds_mean"],
                miss=rep["n_missing_trial"],
            )
        )
    lines.append("")
    causal = arm_reports.get("causal") or {}
    oracle = arm_reports.get("oracle") or {}
    nop = arm_reports.get("nop") or {}
    gates = {
        "oracle_gate_pass": bool(oracle) and oracle["resolved"] == oracle["n_expected"],
        "nop_gate_pass": bool(nop) and nop["resolved"] == 0,
    }
    lines += ["## Harness gates", ""]
    for k, v in gates.items():
        lines.append(f"- `{k}`: **{'PASS' if v else 'FAIL'}**")
    lines += [
        "",
        "## Per-task (causal arm)",
        "",
        "| task | reward | resolved | agent status | engine status | files changed |",
        "|---|---|---|---|---|---|",
    ]
    for tid, t in (causal.get("tasks") or {}).items():
        lines.append(
            f"| `{tid[:56]}` | {t.get('reward')} | {'yes' if t.get('resolved') else 'no'} "
            f"| {t.get('agent_status')} | {t.get('engine_status')} | {t.get('n_files_changed')} |"
        )
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
        rep = collect([pathlib.Path(p) for p in args.jobs_dir], arm=args.arm, expected_ids=list(manifest["tasks"]))
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
        out = {
            "schema": "brain.bench_eval_report.v1",
            "arms": reports,
            "n_reports_read": len(args.reports),
            "note": "Resolve decisions come from each task's own verifier inside the "
            "official container image. Merged across shards by task union.",
        }
        pathlib.Path(args.out_json).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
        pathlib.Path(args.out_md).write_text("\n".join(to_markdown(reports, benchmark=args.benchmark, commit=args.commit)) + "\n", encoding="utf-8")
        return 0

    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
