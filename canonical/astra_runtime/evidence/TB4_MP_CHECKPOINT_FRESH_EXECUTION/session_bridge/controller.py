#!/usr/bin/env python3
"""Brain-side Harbor bridge controller.

Builds and runs the leased Terminal-Bench task inside the official Harbor
Docker environment, drives it through the branch-command bridge agent, and
collects the independent verifier result.

The task tree is cloned at the pinned release commit from the public
terminal-bench repository; it is never modified by the brain side.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path.cwd()
OBS = Path("/tmp/harbor-bridge-observations")
TB = Path("/tmp/terminal-bench-harbor")
EVIDENCE = Path("/tmp/bridge-evidence")
CFG_REL = os.environ.get(
    "BRAIN_SESSION_CONFIG",
    "canonical/astra_runtime/evidence/TB4_MP_CHECKPOINT_FRESH_EXECUTION/session_bridge/session.json",
)
CFG = json.loads((ROOT / CFG_REL).read_text())


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def git(*args, cwd=ROOT, check=True):
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True,
                          check=check)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def commit_obs(rel, value, message):
    p = OBS / rel
    write_json(p, value)
    git("add", rel, cwd=OBS)
    cp = git("diff", "--cached", "--quiet", cwd=OBS, check=False)
    if cp.returncode:
        git("commit", "-m", message, cwd=OBS)
        git("push", "origin", f"HEAD:refs/heads/{CFG['observation_branch']}", cwd=OBS)


def init_obs():
    if OBS.exists():
        shutil.rmtree(OBS)
    git("worktree", "add", "-b", "harbor-observation-work", str(OBS), "HEAD")
    git("config", "user.email", "brain-harbor-bridge@users.noreply.github.com", cwd=OBS)
    git("config", "user.name", "Brain Harbor Bridge", cwd=OBS)
    git("push", "origin", f"HEAD:refs/heads/{CFG['observation_branch']}", cwd=OBS)


def ensure_harbor():
    cp = run([sys.executable, "-m", "pip", "install", "--quiet", "harbor"], timeout=600)
    if cp.returncode:
        raise RuntimeError("HARBOR_INSTALL_FAILED:" + cp.stderr[-5000:])
    harbor = shutil.which("harbor")
    if harbor is None:
        raise RuntimeError("HARBOR_BINARY_NOT_FOUND")
    return harbor


def clone_task():
    if TB.exists():
        shutil.rmtree(TB)
    cp = run(["git", "clone", "--filter=blob:none", "--no-checkout",
              "https://github.com/harbor-framework/terminal-bench.git", str(TB)],
             timeout=600)
    if cp.returncode:
        raise RuntimeError("TB_CLONE_FAILED:" + cp.stderr[-5000:])
    git("sparse-checkout", "init", "--no-cone", cwd=TB)
    (TB / ".git/info/sparse-checkout").write_text(f"tasks/{CFG['task']}/*\n",
                                                  encoding="utf-8")
    git("checkout", "--detach", CFG["terminal_bench_ref"], cwd=TB)
    return TB / "tasks" / CFG["task"]


def collect_results(started):
    candidates = []
    for p in (ROOT / "jobs").glob("**/result.json"):
        try:
            if p.stat().st_mtime >= started - 5:
                candidates.append(p)
        except FileNotFoundError:
            pass
    payload = []
    for p in sorted(candidates, key=lambda x: x.stat().st_mtime):
        try:
            payload.append({"path": str(p.relative_to(ROOT)),
                            "result": json.loads(p.read_text())})
        except Exception as exc:
            payload.append({"path": str(p), "read_error": repr(exc)})
    return payload


def main():
    global CFG, CFG_REL
    args = sys.argv[1:]
    if "--session-config" in args:
        CFG_REL = args[args.index("--session-config") + 1]
        CFG = json.loads((ROOT / CFG_REL).read_text())
    init_obs()
    commit_obs(f"{CFG['command_prefix']}/status.json", {
        "status": "STARTING_HARBOR", "session_id": CFG["session_id"],
        "task": CFG["task"], "terminal_bench_ref": CFG["terminal_bench_ref"]
    }, "harbor bridge: initialize")
    try:
        harbor = ensure_harbor()
        task_dir = clone_task()
        commit_obs(f"{CFG['command_prefix']}/status.json", {
            "status": "STARTING_TASK_RUNTIME", "session_id": CFG["session_id"],
            "task": CFG["task"], "runner": "HARBOR_DOCKER"
        }, "harbor bridge: start official runtime")
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(ROOT),
            "BRAIN_REPO_ROOT": str(ROOT),
            "BRAIN_OBSERVATION_DIR": str(OBS),
            "BRAIN_CONTROL_BRANCH": os.environ.get("GITHUB_HEAD_REF", ""),
            "BRAIN_OBSERVATION_BRANCH": CFG["observation_branch"],
            "BRAIN_SESSION_ID": CFG["session_id"],
            "BRAIN_COMMAND_PREFIX": CFG["command_prefix"],
            "BRAIN_POLL_INTERVAL_SEC": str(CFG.get("poll_interval_sec", 3)),
            "BRAIN_COMMAND_TIMEOUT_SEC": str(CFG.get("command_timeout_sec", 900)),
            "BRAIN_MAX_STEPS": str(CFG.get("max_steps", 80)),
            "BRAIN_SESSION_TIMEOUT_SEC": str(CFG.get("session_timeout_sec", 14000)),
            "BRAIN_OBSERVATION_CHAR_LIMIT": str(CFG.get("observation_char_limit", 120000)),
        })
        started = time.time()
        cmd = [harbor, "run", "-p", str(task_dir), "--agent",
               f"{CFG.get('agent_import_path', 'mpc_bridge:HarborBranchBridgeAgent')}",
               "--env", "docker", *[str(a) for a in CFG.get("harbor_extra_args", [])]]
        cp = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True,
                            timeout=int(CFG.get("harbor_timeout_sec", 15000)))
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / "harbor.stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
        (EVIDENCE / "harbor.stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
        results = collect_results(started)
        write_json(EVIDENCE / "harbor_results.json", results)
        final = {
            "schema": "BRAIN_HARBOR_FINAL_RUN_V1", "session_id": CFG["session_id"],
            "task": CFG["task"], "terminal_bench_ref": CFG["terminal_bench_ref"],
            "harbor_exit_code": cp.returncode, "results": results,
            "stdout_tail": (cp.stdout or "")[-120000:],
            "stderr_tail": (cp.stderr or "")[-120000:], "incremental_spend_usd": 0
        }
        commit_obs(f"{CFG['command_prefix']}/final_verification.json", final,
                   "harbor bridge: final result")
        commit_obs(f"{CFG['command_prefix']}/status.json", {
            "status": "COMPLETE" if cp.returncode == 0 else "HARBOR_RUN_FAILED",
            "session_id": CFG["session_id"], "harbor_exit_code": cp.returncode
        }, "harbor bridge: complete")
        return cp.returncode
    except Exception as exc:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        err = {"status": "BRIDGE_FAILED", "session_id": CFG["session_id"],
               "error": f"{type(exc).__name__}: {exc}"}
        write_json(EVIDENCE / "bridge_error.json", err)
        commit_obs(f"{CFG['command_prefix']}/status.json", err, "harbor bridge: failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
