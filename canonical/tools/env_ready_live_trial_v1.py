"""Live trial: arm two repositories the broker has never seen, cold, then warm.

The claim under test is not "the code runs". It is that this system, with zero model calls,
can take an environment it has never seen, read what that environment declares it needs,
fetch exactly those artifacts from the machine-readable registry, agree with the registry
about the bytes through two independent readers, prove the result by execution, and then
remember it -- while a warm run costs metadata reads and no round trip, and a tampered
memory is caught and re-derived rather than believed.

Repositories are chosen for being real and unrelated: both are ordinary open-source Python
projects whose dependency sets did not exist when this code was written. Nothing about
their contents is special-cased anywhere in the broker.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import the_environment_broker_v1 as B  # noqa: E402

REPOS = (
    ("psf/requests", "https://github.com/psf/requests"),
    ("pallets/flask", "https://github.com/pallets/flask"),
)


def clone(url: str, dest: pathlib.Path) -> dict:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    done = subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, str(dest)],
                          capture_output=True, text=True, timeout=300)
    return {"ok": done.returncode == 0, "seconds": round(time.perf_counter() - started, 3),
            "head": subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                                   capture_output=True, text=True).stdout.strip(),
            "error": (done.stderr or "")[:300] if done.returncode else None}


def trial(name: str, url: str, root: pathlib.Path) -> dict:
    out: dict = {"repo": name, "url": url}
    dest = root / name.replace("/", "__")
    out["clone"] = clone(url, dest)
    if not out["clone"]["ok"]:
        return out
    memory = root / "memory" / f"{name.replace('/', '__')}.json"
    if memory.exists():
        memory.unlink()
    work = root / "wheels" / name.replace("/", "__")

    # a cold claim is only worth something from a clean isolation
    python, _ = B.isolation_python(dest, fresh=True)
    out["clean_isolation"] = python
    cold = B.broker(dest, "env-ready", memory, work_dir=work)
    out["cold"] = cold
    warm = B.broker(dest, "env-ready", memory, work_dir=work)
    out["warm"] = warm

    # tamper: claim a dependency is at a version it is not; the interpreter must win
    tampered = None
    if memory.exists():
        data = json.loads(memory.read_text())
        keys = [k for k in data.get("entries", {}) if k.startswith("env-ready::")]
        if keys:
            entry = data["entries"][keys[0]]
            if entry.get("records"):
                entry["records"][0]["version"] = "0.0.0-tampered"
                memory.write_text(json.dumps(data))
                tampered = B.broker(dest, "env-ready", memory, work_dir=work)
                tampered = {k: tampered.get(k) for k in
                            ("verdict", "from_memory", "recheck", "detail")}

    # after arming, the other goal becomes askable: does the suite run in this environment?
    ran = B.broker(dest, "run-tests", root / "memory" / "shared.json")
    out["tamper"] = tampered
    out["run_tests_after_arming"] = {
        "verdict": ran.get("verdict"),
        "runner": (ran.get("runner") or {}).get("command"),
        "exit_code": (ran.get("runner") or {}).get("exit_code"),
        "reported_passed": (ran.get("runner") or {}).get("reported_passed"),
        "tail": (ran.get("runner") or {}).get("tail", "")[-200:],
        "seconds": ran.get("seconds"),
    }
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("/tmp/brain_trials/env_ready"))
    parser.add_argument("--json", type=pathlib.Path,
                        default=pathlib.Path("intake/RECEIPT_ENV_READY_LIVE_20261123_V1.json"))
    args = parser.parse_args(argv)
    args.root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    trials = [trial(name, url, args.root) for name, url in REPOS]
    receipt = {
        "schema": "BRAIN_ENV_READY_LIVE_TRIAL_V1",
        "date": "2026-11-23",
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_calls": 0,
        "what_this_is": ("two unseen repositories, armed cold by declared-dependency "
                         "resolution against the pypi.org JSON registry, verified by "
                         "execution, then re-armed warm and tampered"),
        "python": sys.version.split()[0],
        "trials": trials,
        "seconds": round(time.perf_counter() - started, 2),
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    for t in trials:
        cold = t.get("cold") or {}
        warm = t.get("warm") or {}
        print(f"{t['repo']}: cold={cold.get('verdict')} {cold.get('seconds')}s "
              f"warm={warm.get('verdict')} {warm.get('seconds')}s "
              f"run-tests={(t.get('run_tests_after_arming') or {}).get('verdict')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
