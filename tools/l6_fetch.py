"""L6 real-corpus fetcher: rebuilds the BugsInPy tornado instances.

Reconstructs /tmp state (which evaporates between sandbox turns) and the
worlds under canonical/astra_runtime/tmp/bugsinpy/l6/:
  - buggy-commit checkout of the REAL repo
  - the FIXED-commit test file (BugsInPy pairs buggy source with the fixed
    test: the failing test is added by the fix commit)
  - satisfiability proof: applying the real fix greens the named test
Usage: python3 tools/l6_fetch.py          # fetch + verify all instances
       python3 tools/l6_fetch.py --check  # verify worlds exist + baseline red
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
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "canonical/astra_runtime/tmp/bugsinpy/l6"
RAW = "https://raw.githubusercontent.com/soarsmu/BugsInPy/master/projects"
REPO = "https://codeload.github.com/tornadoweb/tornado/tar.gz"
UA = {"User-Agent": "brain-l6"}

# (bug id, module file patched by the real fix, failing-test module path,
#  unittest target from run_test.sh)
INSTANCES = [
    (2, "tornado/http1connection.py", "tornado/test/httpclient_test.py",
     "tornado.test.httpclient_test.HTTPClientCommonTestCase."
     "test_redirect_put_without_body"),
    (4, "tornado/web.py", "tornado/test/web_test.py",
     "tornado.test.web_test.StaticFileTest."
     "test_static_with_range_neg_past_start"),
    (14, "tornado/ioloop.py", "tornado/test/ioloop_test.py",
     "tornado.test.ioloop_test.TestIOLoopCurrent.test_force_current"),
]


def _gh_file(path: str) -> str:
    req = urllib.request.Request(
        "https://api.github.com/repos/soarsmu/BugsInPy/contents/" + path,
        headers=UA)
    return base64.b64decode(json.load(
        urllib.request.urlopen(req, timeout=30))["content"]).decode()


def _meta(bug: int) -> dict:
    info = {}
    for line in _gh_file(f"projects/tornado/bugs/{bug}/bug.info").splitlines():
        k, _, v = line.partition("=")
        info[k] = v.strip('"')
    info["patch"] = _gh_file(f"projects/tornado/bugs/{bug}/bug_patch.txt")
    return info


def _unpack(tar: str, dest: pathlib.Path) -> pathlib.Path:
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    with tarfile.open(tar) as tf:
        tf.extractall(str(dest))
    return next(dest.iterdir())


def fetch() -> list[dict]:
    out = []
    for bug, module, test_mod, target in INSTANCES:
        meta = _meta(bug)
        buggy_tar = f"/tmp/tornado_{bug}.tar.gz"
        if not os.path.exists(buggy_tar):
            subprocess.run(["curl", "-sL", "--max-time", "120", "-o",
                            buggy_tar, f"{REPO}/{meta['buggy_commit_id']}"],
                           check=True)
        fixed_tar = f"/tmp/tornado_{bug}_fixed.tar.gz"
        if not os.path.exists(fixed_tar):
            subprocess.run(["curl", "-sL", "--max-time", "120", "-o",
                            fixed_tar, f"{REPO}/{meta['fixed_commit_id']}"],
                           check=True)
        world_dir = BASE / f"tornado_{bug}"
        root = _unpack(buggy_tar, world_dir)
        # the FIXED test file replaces the buggy-checkout one
        tmp = pathlib.Path(f"/tmp/fixext_{bug}")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        with tarfile.open(fixed_tar) as tf:
            tf.extractall(str(tmp))
        fixed_root = next(tmp.iterdir())
        test_rel = pathlib.Path(test_mod)
        shutil.copy2(fixed_root / test_rel, root / test_rel)
        patch_path = pathlib.Path(f"/tmp/real_tornado_{bug}.diff")
        patch_path.write_text(meta["patch"])
        cmd = ["-m", "unittest", "-q", target]
        env = dict(os.environ, PYTHONPATH=str(root))

        def run() -> subprocess.CompletedProcess:
            return subprocess.run(["python3", "-B"] + cmd, cwd=str(root),
                                  env=env, text=True, capture_output=True,
                                  timeout=150)

        base = run()
        if base.returncode == 0:
            raise SystemExit(f"tornado/{bug}: baseline unexpectedly green")
        subprocess.run(["patch", "-p1", "--forward", "-i", str(patch_path)],
                       cwd=str(root), capture_output=True)
        fixed_green = run().returncode == 0
        # restore the buggy world for the repair measurement
        root2 = _unpack(buggy_tar, world_dir)
        shutil.copy2(fixed_root / test_rel, root2 / test_rel)
        row = {"project": "tornado", "bug": bug, "root": str(root2),
               "cmd": cmd, "info": meta, "file": module,
               "baseline_red": base.returncode != 0,
               "real_fix_greens": fixed_green,
               "satisfiable": fixed_green}
        out.append(row)
        print(f"tornado/{bug}: baseline red={row['baseline_red']} "
              f"real-fix green={fixed_green} SATISFIABLE={row['satisfiable']}")
    json.dump(out, open("/tmp/l6_accepted.json", "w"), indent=1)
    return out


def check() -> list[dict]:
    out = []
    for bug, module, test_mod, target in INSTANCES:
        worlds = sorted(BASE.glob(f"tornado_{bug}/tornado-*"))
        if not worlds:
            print(f"tornado/{bug}: MISSING -> run fetch")
            continue
        root = worlds[0]
        env = dict(os.environ, PYTHONPATH=str(root))
        r = subprocess.run(["python3", "-B", "-m", "unittest", "-q", target],
                           cwd=str(root), env=env, text=True,
                           capture_output=True, timeout=150)
        ok = r.returncode != 0
        print(f"tornado/{bug}: exists, baseline red={ok}")
        out.append({"project": "tornado", "bug": bug, "root": str(root),
                    "cmd": ["-m", "unittest", "-q", target],
                    "file": module})
    json.dump(out, open("/tmp/l6_accepted.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        fetch()
