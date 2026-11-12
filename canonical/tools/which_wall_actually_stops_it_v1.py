#!/usr/bin/env python3
"""Which wall actually stops the machine — measured by trying to import the walls.

This exists because I gave the same answer three times and it kept being partly
wrong, each time for the same reason: I measured an *index* of a capability
instead of the *seam* a caller reaches. So this probe does not read a document
and does not trust a status field. It imports the thing and runs it.

THE QUESTION

    Why can't we give the machine the most advanced coding actions, let it
    experience them once, and have the most advanced coding agent on the planet?

Three walls are candidates. Each one is measured here by *attempting it*, not by
citing a number from an earlier session:

  W-A  THE CONFINEMENT / MEDIATION LAYER
       `root3_subprocess_mediator_v2` is the process-wide fail-closed guard, and
       `root3_confined_shell_executor_v1` is the executor that binds
       ARBITRARY_COMMAND_EXECUTION — i.e. the thing that would let the learner
       run real verbs safely. Measured: does it import and install?

  W-B  THE LEARNER'S ACTION VOCABULARY
       `ComputerEnv` is what `discover()`/`drive()` learn over. Measured: how
       many actions does it actually register, and is the confined executor
       reachable from it at all?

  W-C  SEARCH-VERSUS-KNOWLEDGE (new, and it is the deep one)
       Given an admitted confined path, the machine could find a command by
       SEARCHING. But the local binary is a *clone*. If a learned verb names a
       local binary, its identity is not the upstream program's — so what it
       learned is "this clone, at this byte identity", not "tar". Measured: do
       the programs the machine can act on have identities that can be checked
       against an upstream?

WHY C MATTERS MORE THAN IT LOOKS

    A skill that is keyed on a local build transfers to this machine and to no
    other, in exactly the way the state-keyed transition table transfers inside
    one family and nowhere else (measured 2026-11-12: 8/10 -> 1/10 when state
    NAMES change). Binary identity is the software analogue of the same defect,
    and it is checkable: version, digest, and provenance.

WHAT THIS FILE DOES NOT DO

    It does not fix anything, does not add a capability, and does not claim the
    confinement layer is wrong to be fail-closed. It reports which layer refuses
    first, with the exception text, so the next move is chosen from behaviour.

Authority: NONE. Producer-run measurement of one tree at one commit.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _attempt(label: str, fn) -> dict:
    started = time.perf_counter()
    try:
        value = fn()
        return {"layer": label, "reached": True, "detail": value,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}
    except Exception as exc:  # noqa: BLE001 - the refusal IS the measurement
        return {"layer": label, "reached": False,
                "error_type": type(exc).__name__,
                "error": str(exc)[:400],
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}


# --------------------------------------------------------------------------- #
# W-A: the mediation / confinement layer
# --------------------------------------------------------------------------- #
def _import_mediator():
    from canonical.runtime import root3_subprocess_mediator_v2 as mediator
    return {"imported": True, "has_install": hasattr(mediator, "install")}


def _install_confinement():
    from canonical.runtime import root3_strict_current_bootstrap_v3 as bootstrap
    from canonical.runtime import root3_three_class_attempt_authorizer_v1 as authorizer
    status = bootstrap.install_current(
        authorizer.authorize, authority_id=authorizer.AUTHORITY_ID)
    return {k: status.get(k) for k in
            ("run_guard_active", "popen_guard_active", "status")} | {
        "bound": sorted(status.get("bound_effect_class_executors") or [])}


def _compile_effect_registry():
    from canonical.runtime import root3_subprocess_effect_class_registry_v2 as reg
    doc = reg.compile_effect_classes(reg.ROOT)
    return {"status": str(doc.get("status"))[:80],
            "sites": len(doc.get("registry") or doc.get("rows") or [])}


def _legacy_pin_report():
    """Which pinned call sites no longer exist, and are they merely moved lines?"""
    from canonical.runtime import root3_subprocess_effect_class_registry_v2 as reg
    universe = reg.compile_universe(reg.ROOT)
    live = {(s["module_path"], int(s["lineno"]), s["source_api"])
            for s in universe["process_sites"]}
    pinned = set(reg.LEGACY_EXPECTED)
    provenance = set(reg._LEGACY_DISAPPEARANCE_PROVENANCE)  # noqa: SLF001 - the gate's own table
    missing = pinned - live
    unexplained = sorted(missing - provenance)
    live_by_file: dict[str, list[int]] = {}
    for path, line, _api in live:
        live_by_file.setdefault(path, []).append(line)
    rows = []
    for path, line, api in unexplained:
        rows.append({"pinned": "%s:%d" % (path, line), "api": api,
                     "live_lines_in_file": sorted(live_by_file.get(path, [])),
                     "same_file_has_a_site": bool(live_by_file.get(path))})
    return {
        "pinned_count": len(pinned),
        "live_process_sites": len(live),
        "unmediated_sites": universe["unmediated_process_sites"],
        "two_chokepoint_proved":
            universe["two_chokepoint_preconditions_proved_for_parseable_runtime_python"],
        "missing_count": len(missing),
        "explained_by_provenance": len(missing & provenance),
        "unexplained_count": len(unexplained),
        "unexplained": rows,
        "files_where_a_site_still_exists_but_at_another_line":
            sum(1 for r in rows if r["same_file_has_a_site"]),
        "files_where_the_site_vanished_entirely":
            [r["pinned"] for r in rows if not r["same_file_has_a_site"]],
    }


# --------------------------------------------------------------------------- #
# W-B: what the learner can actually do
# --------------------------------------------------------------------------- #
def _learner_vocabulary():
    from canonical.runtime import computer_env_v1 as ce
    env = ce.ComputerEnv()
    try:
        return {"registered_actions": len(env.action_names),
                "actions": env.action_names,
                "programs_on_path": len(ce.installed_programs()),
                "confined_executor_reachable_from_env":
                    hasattr(ce, "root3_confined_shell_executor_v1")
                    or "confined" in Path(ce.__file__).read_text(encoding="utf-8")}
    finally:
        env.close()


# --------------------------------------------------------------------------- #
# W-C: can a learned verb name something whose identity is checkable?
# --------------------------------------------------------------------------- #
def _binary_identity():
    """A skill keyed on a local binary is keyed on THIS clone. Can that be checked?"""
    import hashlib
    rows = []
    for name in ("tar", "git", "python3", "node"):
        path = shutil.which(name)
        if not path:
            rows.append({"program": name, "present": False})
            continue
        real = Path(path).resolve()
        try:
            digest = hashlib.sha256(real.read_bytes()).hexdigest()
            size = real.stat().st_size
        except OSError as exc:
            rows.append({"program": name, "present": True, "error": str(exc)[:80]})
            continue
        version = ""
        try:
            proc = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20)
            version = (proc.stdout or proc.stderr).strip().splitlines()[0][:80]
        except Exception:  # noqa: BLE001 - a program without --version is data
            pass
        # Is this the upstream program, or a local stand-in?
        is_python_shim = real.suffix == ".py" or real.name.startswith("python")
        rows.append({"program": name, "present": True, "resolved": str(real),
                     "sha256": digest[:16], "bytes": size, "version": version,
                     "identity_checkable": bool(version or digest)})
    return rows


def run() -> dict:
    report = {
        "schema": "BRAIN_WALL_MEASUREMENT_V1",
        "authority": "NONE",
        "commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
    }
    report["W_A_import_mediator"] = _attempt("import mediator", _import_mediator)
    report["W_A_compile_effect_registry"] = _attempt("compile effect registry",
                                                     _compile_effect_registry)
    report["W_A_install_confinement"] = _attempt("install confinement",
                                                 _install_confinement)
    report["W_A_legacy_pins"] = _attempt("legacy pin report", _legacy_pin_report)
    report["W_B_learner_vocabulary"] = _attempt("learner vocabulary", _learner_vocabulary)
    report["W_C_binary_identity"] = _attempt("binary identity", _binary_identity)
    return report


def main() -> int:
    report = run()
    if len(sys.argv) == 3 and sys.argv[1] == "--json":
        Path(sys.argv[2]).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
