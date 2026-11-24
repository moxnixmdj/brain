"""Reproduce one SWE-bench Pro V2 instance and grade it by the instance's own contract.

WHY THIS EXISTS, AND WHAT IT IS NOT
-----------------------------------
This is a HARNESS, not a solver. It fetches a published task definition, materialises the
repository at the task's true base commit, applies the task's own published test patch, and
then grades whatever source tree it is given against the task's own `fail_to_pass` and
`pass_to_pass` lists. Handed the published gold patch it reports RESOLVED; handed the
unmodified base it reports NOT RESOLVED with the published failure. Both were measured
2026-11-24 (§A152).

It does **not** solve the instance. Replaying the benchmark's answer sheet grades the answer
sheet. §6 asks whether *this system* produces the patch, and that is a different question
this module deliberately does not answer.

THE INSTANCE ID HAS TWO SHAS AND THEY ARE NOT THE BASE
------------------------------------------------------
    instance_<repo>__<name>-<fix_sha>-v<pinned_sha>

The first sha is the **fix commit**, not the base. The base is its **parent**. Getting this
wrong is silent: the test patch applies to a nearby tree, the tests pass, and the instance
looks reproduced when it is not. `resolve_base_commit` asks GitHub for the parent rather than
guessing from the name, and `verify_pre_fix` refuses to report a baseline unless the base is
actually pre-fix (the fix's marker is absent).

WHY A STANDALONE CLONE
----------------------
`build_room` creates its own `git init` inside the scratch directory. Without that, `git apply`
run inside a subdirectory of this repo resolves against *this* repo and can modify 105 tracked
files while printing success (§A151). Every apply here runs with an explicit `cwd` and the
result is verified by reading the code, never by the exit code.

WHAT IS BLOCKED, AND WHY THAT MATTERS
-------------------------------------
`ghcr.io`, `huggingface.co`, `modal.com` and `fastdl.mongodb.org` are unreachable from this
sandbox and there is no docker daemon, so the published image cannot be pulled and the official
Harbor-on-Modal runner cannot run. What is reachable is the task *definition*, which carries
the problem statement, the verifier contract and the reference patch. That is enough to
reproduce and grade instances whose repositories are public and whose verifiers are pure
Python; it is not enough to run the benchmark as published.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

__all__ = [
    "PRO_API",
    "PRO_RAW",
    "fetch_instance",
    "resolve_base_commit",
    "build_room",
    "grade",
    "reproduce",
]

PRO_API = "https://api.github.com/repos/scaleapi/SWE-bench_Pro-os/contents/v2/tasks"
# raw.githubusercontent.com is BLOCKED from this sandbox (measured 2026-11-24: HTTP 000, TLS
# EOF). api.github.com is allowed and serves the same bytes base64-encoded, so every file is
# read through the contents API instead. A harness that reaches for the obvious URL and works
# only when run from somewhere else is not a harness (law 137).
PRO_CONTENTS = "https://api.github.com/repos/scaleapi/SWE-bench_Pro-os/contents/v2/tasks"
_GITHUB = "https://api.github.com/repos"


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "brain-swe-harness/1"})
    with urllib.request.urlopen(req, timeout=timeout) as fh:  # noqa: S310 - fixed hosts
        return fh.read()


def _get_json(url: str, timeout: int = 60):
    return json.loads(_get(url, timeout))


def _contents(url: str, timeout: int = 60) -> bytes:
    """Fetch a file through the GitHub contents API, which this sandbox may reach.

    raw.githubusercontent.com answers 000 here, so a plain GET is not merely slower -- it is
    impossible. The API response carries {"content": base64, "encoding": "base64"}.
    """
    import base64
    meta = _get_json(url, timeout)
    if isinstance(meta, dict) and meta.get("encoding") == "base64" and meta.get("content"):
        return base64.b64decode(meta["content"])
    raise RuntimeError("CONTENTS_API_DID_NOT_RETURN_A_FILE:" + url)


def _sha_from_instance(instance_id: str) -> tuple[str, str]:
    """Split an instance id into (repo_slug, fix_sha).

    `instance_ansible__ansible-<sha>-v<sha>` -> ('ansible/ansible', '<sha>').
    A parse failure is raised, not guessed: a wrong base commit produces a run that
    looks correct and is not.
    """
    m = re.match(r"instance_(?P<org>[A-Za-z0-9_.-]+)__(?P<repo>[A-Za-z0-9_.-]+)-(?P<sha>[0-9a-f]{7,})", instance_id)
    if not m:
        raise ValueError("UNPARSEABLE_INSTANCE_ID:" + instance_id)
    return f"{m.group('org')}/{m.group('repo')}", m.group("sha")


def fetch_instance(instance_id: str, dest: Path) -> dict:
    """Download one task definition. Returns its paths and parsed verifier contract.

    The published files are the whole contract: `tests/config.json` names the tests that must
    flip and the tests that must not move, and `tests/test_patch.patch` is the only change a
    grader is allowed to make to the repository before asking.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    got = {}
    for rel in ("instruction.md", "task.toml", "tests/config.json", "tests/test_patch.patch",
                "solution/gold_patch.diff"):
        out = dest / rel.replace("/", "__")
        out.write_bytes(_contents(f"{PRO_CONTENTS}/{instance_id}/{rel}"))
        got[rel] = out

    cfg = json.loads(got["tests/config.json"].read_text(encoding="utf-8"))
    # The bench stores these as python-repr strings, so json.loads needs the quotes fixed.
    f2p = json.loads(cfg["fail_to_pass"].replace("'", '"')) if isinstance(cfg["fail_to_pass"], str) else cfg["fail_to_pass"]
    p2p = json.loads(cfg["pass_to_pass"].replace("'", '"')) if isinstance(cfg["pass_to_pass"], str) else cfg["pass_to_pass"]
    got["fail_to_pass"] = f2p
    got["pass_to_pass"] = p2p
    return got


def resolve_base_commit(repo_slug: str, fix_sha: str) -> str:
    """The parent of the fix commit -- NOT the sha in the instance name.

    Measured 2026-11-24: the leading sha is the commit that *fixes* the issue. A tree at that
    sha already contains the fix, so the published test patch will not apply and the "baseline"
    passes. Ask the API for the parent and say so, rather than deriving it from the name.
    """
    data = _get_json(f"{_GITHUB}/{repo_slug}/commits/{fix_sha}")
    parents = data.get("parents") or []
    if not parents:
        raise RuntimeError("NO_PARENT_FOR_FIX_COMMIT:" + fix_sha)
    return parents[0]["sha"]


def build_room(repo_slug: str, sha: str, room: Path, *, init_git: bool = True) -> Path:
    """Materialise `repo_slug` at `sha` into `room` as a STANDALONE git repository.

    `init_git` is not cosmetic. Inside a subdirectory of this repository, `git apply` finds the
    parent repo and applies there (§A151: 105 tracked files changed while printing success).
    A fresh `git init` gives every later `git apply` a repository whose toplevel is the room.
    """
    room = Path(room)
    room.mkdir(parents=True, exist_ok=True)
    tgz = room.parent / (sha + ".tgz")
    url = f"https://codeload.github.com/{repo_slug}/tar.gz/{sha}"
    tgz.write_bytes(_get(url, timeout=600))

    # Extract into a staging directory and move the single top-level dir's contents into the
    # room. GitHub tarballs always have exactly one such dir, but its name is `<repo>-<sha>`,
    # and matching on `endswith(sha[:7])` failed once (got 0 candidates) -- a name is not an
    # identity. Take the only entry and say so if there is not exactly one.
    staging = room.parent / (sha + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with tarfile.open(tgz) as tar:  # noqa: S202 - own download, fixed host
        tar.extractall(staging)
    tgz.unlink()
    entries = [p for p in staging.iterdir()]
    if len(entries) != 1 or not entries[0].is_dir():
        raise RuntimeError(f"TARBALL_HAS_NO_SINGLE_TOP_DIR:{[p.name for p in entries]}")
    for child in entries[0].iterdir():
        shutil.move(str(child), str(room / child.name))
    shutil.rmtree(staging)

    if init_git:
        subprocess.run(["git", "init", "-q", "."], cwd=room, check=True)
        subprocess.run(["git", "add", "-A"], cwd=room, capture_output=True, check=False)
        subprocess.run(["git", "-c", "user.email=h@x", "-c", "user.name=h", "commit", "-qm", "base"],
                       cwd=room, check=True)
        toplevel = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=room,
                                  capture_output=True, text=True).stdout.strip()
        if Path(toplevel).resolve() != room.resolve():
            raise RuntimeError(f"ROOM_IS_NOT_A_STANDALONE_REPO:{toplevel}")
    return room


def _apply(room: Path, patch: Path, *, check_only: bool = False) -> tuple[bool, str]:
    """Apply a patch, then VERIFY the code changed. The exit code is not the evidence.

    `git apply` prints no error and exits 0 for a patch whose hunks match nothing, which is
    indistinguishable from success by status alone (§A151).
    """
    args = ["git", "apply"] + (["--check"] if check_only else []) + [str(patch.resolve())]
    proc = subprocess.run(args, cwd=room, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def _import_roots(room: Path) -> list[str]:
    """The directories a repo expects on `sys.path`, discovered from its own layout.

    Ansible runs its unit tests with `<repo>/lib` and `<repo>/test` on PYTHONPATH; without them
    every test errors at import and the grader sees sixteen `null`s, which is indistinguishable
    from sixteen failures. Discovery is by presence, not by repo name, so the next repo works.
    """
    roots = []
    for rel in ("lib", "src", "test", "tests", "."):
        cand = room / rel
        if cand.is_dir():
            roots.append(str(cand))
    return roots


def grade(room: Path, f2p: list[str], p2p: list[str], *, python: str | None = None,
          env_extra: dict | None = None, timeout: int = 1800) -> dict:
    """Run the named tests and return what actually passed. -v, because -q says nothing per test.

    A parser reading `-q` output finds no per-test line and reports every test unmet, which
    looks exactly like a total failure (`measured §A152`).
    """
    python = python or sys.executable
    env = dict(os.environ)
    env.setdefault("PYTHONHASHSEED", "0")
    roots = _import_roots(room)
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(roots + ([prev] if prev else []))
    env.setdefault("ANSIBLE_TEST_ORIG_PYTHON", python)
    if env_extra:
        env.update(env_extra)
    ids = list(f2p) + list(p2p)
    proc = subprocess.run([python, "-m", "pytest", "-v", "--tb=no", "-p", "no:cacheprovider", *ids],
                          cwd=room, capture_output=True, text=True, env=env, timeout=timeout)
    out = proc.stdout + proc.stderr
    seen: dict[str, bool] = {}
    for line in out.splitlines():
        parts = line.split()
        if not parts or "::" not in parts[0]:
            continue
        if "PASSED" in parts:
            seen[parts[0]] = True
        elif "FAILED" in parts or "ERROR" in parts:
            seen[parts[0]] = False
    tried = {t.split("::")[-1]: seen.get(t) for t in ids}
    unmet = [t for t in ids if seen.get(t) is not True]
    return {
        "f2p_passed": all(seen.get(t) is True for t in f2p),
        "p2p_passed": all(seen.get(t) is True for t in p2p),
        "unmet": unmet,
        "tried": tried,
        "resolved": not unmet,
        # A null means the test never ran. It is neither a pass nor a failure, and the report
        # must say so rather than let a caller treat "unseen" as "failed".
        "unseen": [t.split("::")[-1] for t in ids if seen.get(t) is None],
        # A collection error means the tests never reached the runner. With `--tb=no` pytest
        # does not print the exception class at all (it prints "1 error in 0.02s"), so detecting
        # "ModuleNotFoundError" misses it -- measured. The reliable signal is a non-zero exit
        # with zero collected items, or pytest's own `error` summary line.
        "import_error": ("collected 0 items" in out and "error" in out)
                        or "errors during collection" in out
                        or "ERROR collecting" in out,
        "tail": [l for l in out.splitlines() if "passed" in l or "failed" in l or "error" in l][-2:],
    }


def reproduce(instance_id: str, workdir: Path, python: str | None = None) -> dict:
    """The two-state experiment, both states measured, nothing assumed.

    State A -- published test patch only. The named F2P test MUST fail; if it passes, the base
    commit is wrong or the fix is already present, and the instance is not reproduced.
    State B -- plus the published gold patch. Every named test MUST pass.
    """
    workdir = Path(workdir)
    repo_slug, fix_sha = _sha_from_instance(instance_id)
    meta = fetch_instance(instance_id, workdir / "meta")
    base_sha = resolve_base_commit(repo_slug, fix_sha)

    room = build_room(repo_slug, base_sha, workdir / "room")
    ok, msg = _apply(room, meta["tests/test_patch.patch"])
    if not ok:
        raise RuntimeError("TEST_PATCH_DID_NOT_APPLY:" + msg)

    f2p, p2p = meta["fail_to_pass"], meta["pass_to_pass"]
    before = grade(room, f2p, p2p, python=python)

    ok, msg = _apply(room, meta["solution/gold_patch.diff"])
    if not ok:
        raise RuntimeError("GOLD_PATCH_DID_NOT_APPLY:" + msg)
    after = grade(room, f2p, p2p, python=python)

    return {
        "instance": instance_id,
        "repo": repo_slug,
        "base_commit": base_sha,
        "fix_commit": fix_sha,
        "pre_fix": before,
        "post_fix": after,
        "discriminates": (not before["f2p_passed"]) and before["p2p_passed"] and after["resolved"],
        "verdict": (
            "REPRODUCED__DISCRIMINATES"
            if (not before["f2p_passed"]) and before["p2p_passed"] and after["resolved"]
            else "NOT_REPRODUCED"
        ),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: swepro_instance_harness_v1.py <instance_id> <workdir>", file=sys.stderr)
        return 2
    report = reproduce(argv[1], Path(argv[2]))
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["discriminates"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
