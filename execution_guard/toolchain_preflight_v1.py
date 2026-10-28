"""Is the software this machine claims to have actually installed?  Check, or install it.

A verified capability is an adapter PLUS the tool the adapter calls.  This repository
declared only the first half: the live registry records dependencies as human prose
(``"module": "python stdlib ast/pytest + git"``) and every one of the 419 entries leaves
``declared_dependency_executables`` empty.  Nothing could therefore install the toolchain,
and nothing could tell a missing tool from a broken adapter.

That is not hypothetical.  On a clean checkout of this branch the same commit, the same
code, and the same 22-task hardcore-SE probe read:

    bare python3                  bind 22/22  select 19/22  pass 14/22
    with this declaration         bind 22/22  select 22/22  pass 22/22

Eight capabilities appearing and disappearing on the strength of an undeclared venv.  The
adapters do not degrade either -- they exit their process, so the caller is told a
capability is BROKEN when it is merely ABSENT, which is the difference between debugging
code that is fine and installing a package.

Three modes, all measured rather than asserted:

    python3 execution_guard/toolchain_preflight_v1.py              # check this interpreter
    python3 execution_guard/toolchain_preflight_v1.py --python X   # check the one that will run work
    python3 execution_guard/toolchain_preflight_v1.py --bootstrap  # make .venv match the declaration
    python3 execution_guard/toolchain_preflight_v1.py --attribute  # re-derive which task needs what

``--attribute`` is how the declaration's ``blocks`` lists were produced: each distribution is
blocked with an import hook and the 22-task probe is re-run, so a dependency is recorded only
where a task actually fails without it.  Anything else would be a guess with a version number.

Exit codes: 0 the interpreter matches the declaration, 1 it does not, 2 the declaration itself
is unreadable or malformed (a gate that cannot read its own spec must not report PASS).
"""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECLARATION = ROOT / "canonical/runtime/TOOLCHAIN_DECLARATION_V1.json"
VENV = ROOT / ".venv"
BLOCKER_SOURCE = '''\
import os, sys
_blocked = set(filter(None, os.environ.get("BRAIN_BLOCK_MODULES", "").split(",")))
if _blocked:
    class _Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in _blocked:
                raise ImportError("BRAIN_TOOLCHAIN_BLOCKED: " + name)
            return None
    sys.meta_path.insert(0, _Blocker())
'''


def declaration() -> dict:
    try:
        data = json.loads(DECLARATION.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - an unreadable spec is a refusal, never a pass
        print("toolchain-preflight: cannot read %s: %s" % (DECLARATION, exc))
        raise SystemExit(2)
    if not isinstance(data, dict) or not isinstance(data.get("distribution"), dict):
        print("toolchain-preflight: %s has no `distribution` object" % DECLARATION)
        raise SystemExit(2)
    return data


def installed_version(import_name: str, metadata_name: str | None = None) -> str | None:
    """The version of the distribution providing ``import_name``, if it is importable.

    The import decides PRESENCE and the metadata decides VERSION, because they are not
    the same name: `crosshair` is shipped by `crosshair-tool`, `z3` by `z3-solver`,
    `tree_sitter` by `tree-sitter`.
    """
    if importlib.util.find_spec(import_name) is None:
        return None
    for candidate in (metadata_name, import_name):
        if not candidate:
            continue
        try:
            return importlib.metadata.distribution(candidate).version
        except importlib.metadata.PackageNotFoundError:
            continue
    # Present but unversionable: reported as the import working, the pin unproven.
    return "UNVERSIONED"


def probe_tasks() -> list[str]:
    """The 22 hardcore-SE tasks, read from the instrument that owns them."""
    import importlib.util
    path = ROOT / "execution_guard/hardcore_se_reachability_v1.py"
    spec = importlib.util.spec_from_file_location("_se_reachability", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return [tag for tag, _cid, _goal in module.PROBES]


def report(python: str | None, as_json: str) -> int:
    spec = declaration()
    dist = spec["distribution"]
    rows = []
    for name, entry in sorted(dist.items()):
        want = str(entry.get("version") or "")
        have = installed_version(str(entry.get("import") or name), entry.get("metadata_name"))
        # Strict on purpose: the pin is the version this repository MEASURED, and a
        # drifted toolchain is exactly the state that silently changed 22/22 into 14/22.
        ok = have is not None and (not want or have == want)
        rows.append({"distribution": name, "import": entry.get("import"),
                     "required": want, "installed": have, "ok": ok,
                     "blocks": list(entry.get("blocks") or [])})
    missing = [r for r in rows if not r["ok"]]
    blocked: list[str] = []
    for row in missing:
        for task in row["blocks"]:
            if task not in blocked:
                blocked.append(task)
    try:
        total = len(probe_tasks())
    except Exception:  # noqa: BLE001 - the count is decoration; the verdict is not
        total = None
    interpreter = sys.executable
    for row in rows:
        print("  %-4s %-14s %-10s needs %-9s blocks %s"
              % ("OK" if row["ok"] else "MISS", row["distribution"],
                 row["installed"] or "-", row["required"] or "-",
                 ", ".join(row["blocks"]) or "-"))
    verdict = "PASS" if not missing else "FAIL_CLOSED"
    print("\ntoolchain-preflight: python=%s %s : %d of %d declared distributions present"
          % (interpreter, verdict, len(rows) - len(missing), len(rows)))
    if missing:
        print("capabilities this interpreter cannot run: %d of %s measured hardcore-SE tasks (%s)"
              % (len(blocked), total if total is not None else "?", ", ".join(blocked)))
        print("install with: python3 execution_guard/toolchain_preflight_v1.py --bootstrap")
    if as_json:
        Path(as_json).write_text(json.dumps(
            {"schema": "brain.toolchain.preflight.v1", "python": interpreter,
             "verdict": verdict, "rows": rows, "blocked_tasks": blocked,
             "measured_tasks": total}, indent=1), encoding="utf-8")
    return 0 if not missing else 1


def bootstrap() -> int:
    """Create .venv (once) and install the pinned set into it."""
    spec = declaration()
    pins = ["%s==%s" % (name, entry["version"])
            for name, entry in sorted(spec["distribution"].items()) if entry.get("version")]
    if not VENV.exists():
        print("creating %s" % VENV)
        subprocess.run([sys.executable, "-m", "venv", str(VENV), "--system-site-packages"], check=True)
    pip = VENV / "bin" / "pip"
    print("installing: %s" % " ".join(pins))
    subprocess.run([str(pip), "install", "--quiet", *pins], check=True)
    python = str(VENV / "bin" / "python")
    print("\nbootstrapped.  Run work with: %s\n" % python)
    return report(python, "")


def attribute(only: str = "") -> int:
    """Re-derive the dependency matrix by blocking each distribution in turn.

    This is the measurement the declaration records, kept runnable so the declaration
    cannot drift away from the code: if an adapter starts calling a new tool, blocking it
    here shows the new task failing and the file is wrong until it is updated.
    """
    spec = declaration()
    shim = ROOT / "canonical/astra_runtime/tmp/toolchain_blocker"
    shim.mkdir(parents=True, exist_ok=True)
    (shim / "sitecustomize.py").write_text(BLOCKER_SOURCE, encoding="utf-8")
    python = str(VENV / "bin" / "python") if (VENV / "bin/python").exists() else sys.executable
    probe = ROOT / "execution_guard/hardcore_se_reachability_v1.py"
    env = dict(os.environ)
    env["PYTHONPATH"] = "%s:%s" % (shim, ROOT)
    out = {}
    for name, entry in sorted(spec["distribution"].items()):
        if only and name not in only.split(","):
            continue
        env["BRAIN_BLOCK_MODULES"] = str(entry.get("import") or name)
        proc = subprocess.run([python, str(probe)], capture_output=True, text=True, env=env)
        failed = [line.split()[0] for line in proc.stdout.splitlines() if "pass=N" in line]
        out[name] = failed
        print("  %-14s blocked -> %s" % (name, ", ".join(failed) or "no task loses it"))
    print("\nWrite these into %s if any row moved." % DECLARATION.name)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--bootstrap", action="store_true")
    ap.add_argument("--attribute", action="store_true")
    ap.add_argument("--only", default="")
    ns = ap.parse_args()
    if ns.bootstrap:
        return bootstrap()
    if ns.attribute:
        return attribute(ns.only)
    if ns.python:
        # The declaration is about the interpreter that WILL run the work, which need
        # not be the one running this check.  Re-exec there rather than guess: checking
        # sys.path from here would answer a question nobody asked.
        # Deliberately NOT resolved: a venv's python is a symlink to the base
        # interpreter, and resolving it erased the very difference being checked.
        target = os.path.abspath(ns.python)
        if target != os.path.abspath(sys.executable):
            cmd = [target, str(Path(__file__).resolve())]
            if ns.json:
                cmd += ["--json", ns.json]
            return subprocess.run(cmd).returncode
    return report(ns.python, ns.json)


if __name__ == "__main__":
    raise SystemExit(main())
