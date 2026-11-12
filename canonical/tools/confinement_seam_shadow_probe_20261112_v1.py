#!/usr/bin/env python3
"""Shadow confinement probe: does the admitted-confinement path really execute? 2026-11-12.

WHY THIS EXISTS
---------------
`canonical/runtime/confinement_v1.py` is the substrate the boundary demands
("reviewed, admitted confinement and effect-verification path") and is consulted by NOTHING.
19 of 38 realistic advanced-coding goals in this tree refuse with
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`.

This probe measures the substrate honestly WITHOUT opening it. What it is:

  Admitted, run under `confinement_v1.run_confined`, **with no adoption step**
  ("Design B" in `PREREG_THE_CONFINEMENT_SEAM_20261112_V1.md`, pre-registered this week
  as the shadow arm, never as the admitted path). Effects are verified *inside the
  disposable clone* by sha256 and then the clone is deleted. **No host byte is ever
  adopted; the door, the boundary, every refusal site and every gate are untouched.**

What this probe is NOT:

  * Not the seam. It grants nothing; no capability becomes callable; no tolerance widens.
  * Not authority for anyone else. It is a measurement harness, run by hand, $0.
  * Not proof that any capability "works." It proves only mechanics: the confined machine
    runs the real bound adapter, effects land in the capsule, the host is byte-identical.

Rows (all deterministic, no network):
  m1  argv → declared stdout-capture effect is produced, hashed, verified, host untouched.
  m2  Arbitrary child code (the exact thing confinement exists for) runs; its file effect
      is produced inside the capsule, hashed, verified; host untouched.
  m3  A declared effect that resolves outside the capsule is REFUSED at admission
      (`EFFECT_ESCAPES_CONFINEMENT`); the clone is not executed; host untouched.
  m4  A declared effect the command never writes is a receipt with `verified: False`
      and the missing file hash empty -- failure reported as failure, not papered over.
  m5  An overrun is recorded as `BUDGET_EXCEEDED`, never laundered into success.

Run:
    python3 canonical/tools/confinement_seam_shadow_probe_20261112_v1.py
    python3 canonical/tools/confinement_seam_shadow_probe_20261112_v1.py --out shadow.json

Authority: NONE. `truth.achieved` stays false. Zero model dependency. Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import confinement_v1  # noqa: E402

# The driver runs *inside the clone* with cwd == worktree. It loads the clone's own
# copy of the bound adapter by path and calls its real entrypoint, exactly as the
# admitted path would -- except the result is printed as JSON and the clone is then
# deleted. No adoption, no host write beyond git itself.
_DRIVER = r"""
import base64, importlib.util, json, pathlib, sys

task = json.loads(base64.b64decode(sys.argv[1].encode()).decode())
root = pathlib.Path.cwd()
spec = importlib.util.spec_from_file_location("shadow_bound_adapter", root / task["adapter_path"])
if spec is None or spec.loader is None:
    print(json.dumps({"adapter_ok": False, "error": "ADAPTER_LOAD_FAILED"}))
    raise SystemExit(0)
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
    result = module.run(dict(task["args"]), str(root))
    print(json.dumps({"adapter_ok": True, "result": result}, default=str))
except Exception as exc:
    print(json.dumps({"adapter_ok": False, "error": type(exc).__name__ + ":" + str(exc)[:2000]}))
""".strip()

_CLI = "canonical/runtime/bound_capabilities/cli_command.py"


def _adapter_argv(cli_args: dict) -> list[str]:
    task = json.dumps({"adapter_path": _CLI, "args": cli_args}, sort_keys=True)
    return ["python3", "-c", _DRIVER, base64.b64encode(task.encode()).decode()]


ROWS = [
    {
        "row_id": "shadow.m1.python_version_stdout_captured",
        "goal_sentence": "Run the shell command python3 --version and write its output to version.txt.",
        "capability_id": "shell.command.run",
        "cli_args": {"argv": ["python3", "--version"],
                     "output_path": "version.txt",
                     "write_stdout_to_output": "true"},
        "declared_effects": ["version.txt"],
        "budget_s": 60,
        "expect": {"admitted": True, "outcome": "RAN", "verified": True,
                   "effect_exists": True},
    },
    {
        "row_id": "shadow.m2.arbitrary_child_code_contained",
        "goal_sentence": ("Run a Python program that writes arbitrary_output.txt -- the exact thing "
                          "confinement exists to contain."),
        "capability_id": "shell.command.run",
        "cli_args": {"argv": ["python3", "-c",
                              "import pathlib; pathlib.Path('arbitrary_output.txt').write_text("
                              "'confined arbitrary code ran\\n')"],
                     "output_path": "arbitrary_output.txt"},
        "declared_effects": ["arbitrary_output.txt"],
        "budget_s": 60,
        "expect": {"admitted": True, "outcome": "RAN", "verified": True,
                   "effect_exists": True},
    },
    {
        "row_id": "shadow.m3.absolute_effect_refused_at_admission",
        "goal_sentence": "(Adversarial) declare an output outside the confinement; it must be refused.",
        "capability_id": "shell.command.run",
        "cli_args": {"argv": ["python3", "--version"],
                     "output_path": "/etc/brain_shadow_probe_marker",
                     "write_stdout_to_output": "true"},
        "declared_effects": ["/etc/brain_shadow_probe_marker"],
        "budget_s": 30,
        "expect": {"admitted": False, "refused": "EFFECT_ESCAPES_CONFINEMENT"},
    },
    {
        "row_id": "shadow.m4.missing_declared_effect_not_verified",
        "goal_sentence": "Declare version.txt but run a command that writes nothing.",
        "capability_id": "shell.command.run",
        "cli_args": {"argv": ["python3", "-c", "pass"]},
        "declared_effects": ["never_written.txt"],
        "budget_s": 30,
        "expect": {"admitted": True, "outcome": "RAN", "verified": False,
                   "effect_exists": False},
    },
    {
        "row_id": "shadow.m5.budget_exceeded_is_not_success",
        "goal_sentence": "Run a program that sleeps past its budget; the receipt must say so.",
        "capability_id": "shell.command.run",
        "cli_args": {"argv": ["python3", "-c", "import time; time.sleep(30)"]},
        "declared_effects": [],
        "budget_s": 1,
        "expect": {"admitted": True, "outcome": "BUDGET_EXCEEDED",
                   "verified": False},
    },
]


def _run_row(row: dict) -> dict:
    started = time.time()
    result = confinement_v1.run_confined(
        ROOT, _adapter_argv(row["cli_args"]),
        budget_s=row["budget_s"],
        declared_effects=row["declared_effects"],
        allow_network=False)
    effects = result.get("declared_effects") or {}
    effect = next(iter(effects.values()), {}) if effects else {}
    verdict = {
        "admitted": result.get("admitted"),
        "outcome": result.get("outcome"),
        "refused": result.get("refused"),
        "exit_code": result.get("exit_code"),
        "verified": result.get("verified"),
        "host_untouched": result.get("host_untouched"),
        "elapsed_s": round(time.time() - started, 2),
        "receipt_sha256": result.get("receipt_sha256"),
        "effects": {k: {"inside_worktree": v.get("inside_worktree"),
                        "exists": v.get("exists"),
                        "sha256": (v.get("sha256", "")[:16] + "…") if v.get("sha256") else ""}
                    for k, v in effects.items()},
        "stdout_tail": (result.get("stdout_tail") or "")[-120:].strip(),
        "adapter_ok": None,
        "adapter_error": None,
    }
    try:
        decoded = json.loads(result["stdout_tail"]) if result.get("stdout_tail") else {}
        if isinstance(decoded, dict):
            verdict["adapter_ok"] = decoded.get("adapter_ok")
            verdict["adapter_error"] = decoded.get("error")
    except (ValueError, TypeError):
        pass
    return {"row_id": row["row_id"], "capability_id": row["capability_id"],
            "goal_sentence": row["goal_sentence"], "expect": row["expect"],
            "verdict": verdict}


def _score(expect: dict, verdict: dict) -> bool:
    for key, want in expect.items():
        if key == "effect_exists":
            effects = list(verdict["effects"].values())
            if not effects or any(e.get("exists") is not want for e in effects):
                return False
        elif verdict.get(key) != want:
            return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    rows = [_run_row(row) for row in ROWS]
    ok = sum(1 for r in rows if _score(r["expect"], r["verdict"]))
    summary = {
        "schema": "PROJECT_BRAIN_CONFINEMENT_SEAM_SHADOW_PROBE_V1",
        "authority": "NONE__MEASUREMENT_ONLY__NO_ADOPTION__NO_GATE_WIDENS",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "claim": "MECHANICS_ONLY__NO_CAPABILITY_CREDIT__NO_GATE_CHANGE",
        "rows_passed": ok,
        "rows_total": len(rows),
        "host_byte_identical_all_rows": all(r["verdict"].get("host_untouched") is True
                                            for r in rows
                                            if r["verdict"].get("admitted") is True),
        "rows": rows,
    }
    for r in rows:
        v = r["verdict"]
        line = "%-52s admit=%s outcome=%s refused=%s verified=%s host=%s" % (
            r["row_id"], v.get("admitted"), v.get("outcome"),
            v.get("refused"), v.get("verified"), v.get("host_untouched"))
        print(line)
    print()
    print(json.dumps({k: summary[k] for k in ("rows_passed", "rows_total",
                                                "host_byte_identical_all_rows")}, indent=1))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(summary, indent=1) + "\n")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
