"""L6 corpus scale-out: screen BugsInPy projects for satisfiable instances.

The tornado trio proved the harness (buggy checkout + FIXED test file +
satisfiability gate). This tool screens further projects -- chosen for small
repos and fast suites (wall-friendly for the repair stack) -- and caches a
manifest of verified instances:

  per bug: bug.info + bug_patch + run_test.sh -> single-file patch only ->
  buggy tarball -> fixed test file copied in -> baseline must be RED with the
  REAL bug symptom (import-broken = environment, skip) -> real patch must
  GREEN it (satisfiability) -> world rebuilt buggy for measurement.

Usage:
  python3 tools/l6_scale.py                 # screen + write manifest
  python3 tools/l6_scale.py --measure       # run the router on new instances
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # the repair stack imports canonical.*
BASE = ROOT / "canonical/astra_runtime/tmp/bugsinpy/l6"
API = "https://api.github.com/repos/soarsmu/BugsInPy/contents/projects"
UA = {"User-Agent": "brain-l6"}

PROJECTS = {
    "tqdm": "tqdm/tqdm",
    "httpie": "httpie/cli",
    "PySnooper": "cool-RR/PySnooper",
    "cookiecutter": "cookiecutter/cookiecutter",
}
MAX_IDS = 10
IMPORT_BROKEN = ("ModuleNotFoundError", "AttributeError: module",
                 "ImportError: cannot import name", "SyntaxError")


def _gh(path: str):
    req = urllib.request.Request(API.replace("/projects", "") + path,
                                 headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=30))


def _gh_text(path: str) -> str:
    return base64.b64decode(_gh(path)["content"]).decode()


def _parse_cmd(run_sh: str) -> list[str] | None:
    """The failing-test command: unittest preferred, else pytest node."""
    unittest = None
    pytest = None
    for line in run_sh.splitlines():
        s = line.strip()
        if s.startswith("#") or not s:
            continue
        if s.startswith("python") and "-m unittest" in s and unittest is None:
            unittest = s.split()
        if s.startswith("python") and "pytest" in s and pytest is None:
            pytest = s.split()
    cmd = unittest or pytest
    if not cmd:
        return None
    if cmd[0] in ("python", "python3"):
        cmd[0] = sys.executable
    return cmd


def _unpack(tar: str, dest: pathlib.Path) -> pathlib.Path:
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    with tarfile.open(tar) as tf:
        tf.extractall(str(dest))
    return next(dest.iterdir())


def screen() -> list[dict]:
    manifest_path = BASE / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    known = {(m["project"], m["bug"]) for m in manifest}
    out = list(manifest)
    for project, repo in PROJECTS.items():
        for bug in range(1, MAX_IDS + 1):
            if (project, bug) in known:
                continue
            try:
                info = {}
                for line in _gh_text(
                        f"/projects/{project}/bugs/{bug}/bug.info").splitlines():
                    k, _, v = line.partition("=")
                    info[k] = v.strip('"')
                patch = _gh_text(f"/projects/{project}/bugs/{bug}/bug_patch.txt")
                files = [l[6:] for l in patch.splitlines()
                         if l.startswith("+++ b/")]
                if len(files) != 1:
                    print(f"{project}/{bug}: skip multi-file patch {files}")
                    continue
                run_sh = _gh_text(f"/projects/{project}/bugs/{bug}/run_test.sh")
                cmd = _parse_cmd(run_sh)
                if not cmd:
                    print(f"{project}/{bug}: skip no-test-command")
                    continue
                tar = f"/tmp/l6_{project}_{bug}.tar.gz"
                if not os.path.exists(tar):
                    subprocess.run(
                        ["curl", "-sL", "--max-time", "120", "-o", tar,
                         f"https://codeload.github.com/{repo}/tar.gz/"
                         f"{info['buggy_commit_id']}"], check=True)
                world_dir = BASE / f"{project}_{bug}"
                root = _unpack(tar, world_dir)
                # the FIXED-commit test file (the failing test is added by the fix)
                fixed_tar = f"/tmp/l6_{project}_{bug}_fixed.tar.gz"
                if not os.path.exists(fixed_tar):
                    subprocess.run(
                        ["curl", "-sL", "--max-time", "120", "-o", fixed_tar,
                         f"https://codeload.github.com/{repo}/tar.gz/"
                         f"{info['fixed_commit_id']}"], check=True)
                froot = _unpack(fixed_tar, pathlib.Path(
                    f"/tmp/l6_fix_{project}_{bug}"))
                test_rel = pathlib.Path(info["test_file"])
                if not (froot / test_rel).is_file():
                    print(f"{project}/{bug}: skip fixed test file missing")
                    continue
                shutil.copy2(froot / test_rel, root / test_rel)
                patch_path = pathlib.Path(f"/tmp/l6_{project}_{bug}.diff")
                patch_path.write_text(patch)
                env = dict(os.environ, PYTHONPATH=str(root))

                def run() -> subprocess.CompletedProcess:
                    return subprocess.run(cmd, cwd=str(root), env=env,
                                          text=True, capture_output=True,
                                          timeout=150)

                base = run()
                if base.returncode == 0:
                    print(f"{project}/{bug}: skip baseline green")
                    continue
                tail = base.stderr or base.stdout
                if any(k in tail for k in IMPORT_BROKEN) and \
                        "Ran 0 tests" in tail:
                    print(f"{project}/{bug}: skip env-broken import")
                    continue
                subprocess.run(["patch", "-p1", "--forward", "-i",
                                str(patch_path)], cwd=str(root),
                               capture_output=True)
                green = run().returncode == 0
                # rebuild buggy world for the repair measurement
                root2 = _unpack(tar, world_dir)
                shutil.copy2(froot / test_rel, root2 / test_rel)
                row = {"project": project, "repo": repo, "bug": bug,
                       "root": str(root2), "cmd": cmd, "info": info,
                       "file": files[0], "baseline_red": True,
                       "satisfiable": green}
                if green:
                    out.append(row)
                    print(f"{project}/{bug}: SATISFIABLE "
                          f"({files[0]}, {' '.join(cmd[1:4])})")
                else:
                    print(f"{project}/{bug}: NOT satisfiable in this env")
            except urllib.error.HTTPError as e:
                print(f"{project}/{bug}: none ({e.code})")
            except Exception as e:
                print(f"{project}/{bug}: skip {type(e).__name__} {str(e)[:60]}")
    manifest_path.write_text(json.dumps(out, indent=1))
    print(f"manifest: {len(out)} satisfiable instances -> {manifest_path}")
    return out


def measure(manifest: list[dict]) -> None:
    for m in manifest:
        if m["project"] == "tornado":
            continue  # measured in rounds 1-2
        root = pathlib.Path(m["root"]).resolve()
        env = dict(os.environ, PYTHONPATH=str(root))
        argv = list(m["cmd"])
        b = subprocess.run(argv, cwd=str(root), env=env, text=True,
                           capture_output=True, timeout=150)
        if b.returncode == 0:
            print(f"{m['project']}/{m['bug']}: baseline green?!")
            continue
        sp = importlib.util.spec_from_file_location(
            "rt", str(ROOT / "canonical/runtime/bound_capabilities/"
                       "python_software_repair_router_v1.py"))
        rt = importlib.util.module_from_spec(sp)
        sys.modules["rt"] = rt
        sp.loader.exec_module(rt)
        test_rel = pathlib.Path(m["info"]["test_file"])
        test_brainrel = str((root / test_rel).relative_to(ROOT))
        out = (ROOT / f"canonical/astra_runtime/tmp/bugsinpy/l6/"
                      f"{m['project']}_{m['bug']}_router.json")
        import time
        t0 = time.monotonic()
        try:
            r = rt.run({"source_root": str(root.relative_to(ROOT)),
                        "test_paths": [test_brainrel],
                        "test_argv": argv,
                        "output_path": str(out.relative_to(ROOT)),
                        "timeout_s": 40, "budget": 1,
                        "wall_budget_s": 290}, str(ROOT))
            repaired = r["repaired"]
            trace = [(s["step"], str(s.get("status", ""))[:36])
                     for s in r["route_trace"]]
        except Exception as e:
            repaired = False
            trace = [(type(e).__name__, str(e)[:70])]
        seconds = round(time.monotonic() - t0, 1)
        independent = subprocess.run(
            argv, cwd=str(root), env=env, text=True, capture_output=True,
            timeout=150).returncode == 0
        print(json.dumps({"bug": f"{m['project']}/{m['bug']}",
                          "repaired": repaired,
                          "independent": independent,
                          "seconds": seconds, "trace": trace}))


if __name__ == "__main__":
    import importlib.util
    if "--measure" in sys.argv:
        measure(json.loads((BASE / "manifest.json").read_text()))
    else:
        screen()
