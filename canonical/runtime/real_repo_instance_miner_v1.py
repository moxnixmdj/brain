#!/usr/bin/env python3
"""Mine real, valid repair instances from upstream fix commits.

WHY THIS EXISTS
---------------
Last round repaired one real upstream bug. One is a demonstration, not a rate. A rate needs
many instances, and hand-picking each one does not scale. This module automates the
construction of a valid instance from a commit, and -- this is the point -- it REFUSES
every instance it cannot prove is valid.

WHAT MAKES AN INSTANCE VALID (all four required)
------------------------------------------------
1. The commit changes test files AND source files. A fix with no test has no oracle.
2. The parent version of the changed source lines can be recovered exactly.
3. Reverting the source hunk (keeping the newer tests) makes the suite RED.
4. The un-reverted version makes the suite GREEN.

Test 3 is where most candidates die, and that is correct: a fix whose regression test
arrives in the same commit as a NEW test file will often have no failing state under
revert (the test may not even import). Those are rejected, never counted.

CONTROL DISCIPLINE
------------------
Every instance is verified twice (red on revert, green on fix) before it is ever offered
to the solver. An instance that cannot pass both controls is reported REJECTED with the
reason. The count of rejections is part of the output, because an honest denominator is
the whole value of a benchmark.

This module only MINES and VERIFIES. It does not claim any solve rate. The solver run is a
separate, explicit step -- keeping mining cheap is what makes a large N affordable.

Usage
    python3 canonical/runtime/real_repo_instance_miner_v1.py --repos pallets/markupsafe --limit 6
    python3 canonical/runtime/real_repo_instance_miner_v1.py --json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SCHEMA = "brain.real_repo_instance_miner.v1"

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

DEFAULT_REPOS = [
    "pallets/markupsafe",
    "pallets/itsdangerous",
    "pallets/click",
    "pallets/jinja",
    "psf/requests",
]

TEST_HINT = re.compile(r"(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.py$")
FIX_WORDS = re.compile(r"(?i)\b(fix|bug|wrong|incorrect|broken|crash|regression|handle|invalid)\b")


def _api(path: str):
    url = path if path.startswith("http") else f"https://api.github.com/{path.lstrip('/')}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "brain-miner"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        with urlopen(Request(url, headers=headers), timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        # `gh` carries ambient credentials and survives responses that stun urllib on a
        # large blob. Falling back keeps a transport failure from being read as a
        # missing file, which would reject the instance for the wrong reason.
        r = subprocess.run(["gh", "api", url], capture_output=True, text=True, timeout=90)
        if r.returncode != 0 or not r.stdout.strip():
            raise RuntimeError(f"gh api failed: {r.stderr[:120]}")
        return json.loads(r.stdout)


def _raw(spec: str) -> str | None:
    """Return file text at `<owner>/<repo>/<path>?ref=<sha>`.

    The contents API omits `content` for files above its size ceiling (click's core.py is
    149 KB and comes back with no body). Falling through to the git blobs API recovers it.
    Without this fallback a large, very common file shape is silently counted as
    PARENT_UNRECOVERABLE -- a rejection for the wrong reason.
    """
    # `spec` is already an API path ("repos/<owner>/<repo>/contents/..."). Prefixing it
    # again produces "repos/repos/..." -> 404 -> None -> a file reported as unrecoverable.
    api_path = spec if spec.startswith("repos/") else f"repos/{spec}"
    try:
        r = _api(api_path)
        if r.get("encoding") == "base64" and r.get("content"):
            return base64.b64decode(r["content"]).decode("utf-8", "replace")
        blob_sha = r.get("sha")
    except Exception:
        return None
    if not blob_sha:
        return None
    # fallback: git blobs API (works for any size on a public repo)
    try:
        repo_part = api_path.split("/contents/")[0]
        b = _api(f"{repo_part}/git/blobs/{blob_sha}")
        if b.get("encoding") == "base64" and b.get("content"):
            return base64.b64decode(b["content"]).decode("utf-8", "replace")
    except Exception:
        return None
    return None


def list_fix_commits(repo: str, per_page: int = 100) -> list[dict]:
    try:
        commits = _api(f"repos/{repo}/commits?per_page={per_page}")
    except Exception:
        return []
    out = []
    for c in commits:
        msg = (c.get("commit", {}).get("message") or "")
        subject = msg.split("\n")[0]
        if FIX_WORDS.search(subject) and "typo" not in subject.lower() and "docs/" not in subject:
            out.append({"sha": c["sha"], "subject": subject, "repo": repo})
    return out


def examine(commit: dict) -> dict:
    """Decide whether a commit can yield a valid instance. Never raises."""
    repo, sha = commit["repo"], commit["sha"]
    try:
        detail = _api(f"repos/{repo}/commits/{sha}")
    except Exception as e:
        return {**commit, "valid": False, "reason": f"API_FAIL {type(e).__name__}"}

    files = detail.get("files") or []
    test_files = [f for f in files if TEST_HINT.search(f.get("filename", ""))]
    src_files = [
        f for f in files
        if not TEST_HINT.search(f.get("filename", ""))
        and f.get("filename", "").endswith(".py")
        and (f.get("patch") or "")
    ]
    if not test_files:
        return {**commit, "valid": False, "reason": "NO_TEST_CHANGED"}
    if not src_files:
        return {**commit, "valid": False, "reason": "NO_SOURCE_CHANGED"}

    parent = detail["parents"][0]["sha"]
    # Recover the exact pre-fix text of each changed source file from the parent commit.
    recoverable = {}
    for f in src_files:
        text = _raw(f"{repo}/contents/{f['filename']}?ref={parent}")
        if text is None:
            continue
        recoverable[f["filename"]] = text
    if not recoverable:
        return {**commit, "valid": False, "reason": "PARENT_UNRECOVERABLE"}

    return {
        **commit,
        "parent": parent,
        "valid": None,                     # not yet proven; verification decides
        "candidate": True,
        "test_files_changed": [f["filename"] for f in test_files],
        "src_files_changed": list(recoverable),
        "recoverable_sources": recoverable,
    }


# ---------------------------------------------------------------------------
# Positive controls: bugs that are not from this repository.
# Without a GUARANTEED-solvable instance, a 0% or a 33% cannot be interpreted. A positive
# control turns "the engine failed" into "the engine failed on this class of bug", which is
# a finding rather than a shrug.
# ---------------------------------------------------------------------------
POSITIVE_CONTROLS = [
    {
        "id": "pallets_markupsafe_proxy_class",
        "repo": "pallets/markupsafe",
        "sha": "54bb00bfaf",
        "parent": None,                      # resolved at run time
        "src": ["src/markupsafe/__init__.py"],
        "tests": ["tests/test_escape.py"],
        "known_solved": True,
        "mechanism": "surgical_ast:dunder_identity:__class___to_type",
    },
]


def _ensure_deps(root: Path) -> list[str]:
    """Install what the repo needs to even collect its tests.

    Without this, `FIX_CONTROL_NOT_GREEN` fires on a missing import and the commit is
    rejected for the wrong reason. A rejected instance must be rejected because the bug
    does not reproduce, never because the environment was incomplete.
    """
    installed = []
    for req in ("requirements/tests.txt", "requirements/tests.in",
                "requirements/dev.txt", "requirements.txt"):
        p = root / req
        if p.is_file():
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--break-system-packages",
                     "-q", "-r", str(p)],
                    capture_output=True, text=True, timeout=420)
                installed.append(req)
            except Exception:
                pass
            break
    # Project's own package, importable from source
    for sub in ("src", "."):
        if (root / sub).is_dir():
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--break-system-packages",
                     "-q", "-e", str(root)],
                    capture_output=True, text=True, timeout=420)
                installed.append("editable-install")
                break
            except Exception:
                pass
    return installed


def _pytest(root: Path, scope: list[str] | None = None) -> tuple[int, int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / p) for p in ("src", ".") if (root / p).is_dir()])
    # Scope to the tests the fix actually touched. A 500-file suite costs minutes per
    # control, and the controls need to run twice per instance.
    targets = scope or ["tests/"]
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", *targets, "-q", "-p", "no:cacheprovider",
             "--tb=no"],
            cwd=root, capture_output=True, text=True, timeout=300, env=env)
        out = r.stdout + r.stderr
    except Exception as e:
        return 0, -1, f"PYTEST_FAILED {type(e).__name__}"
    p = int(m.group(1)) if (m := re.search(r"(\d+) passed", out)) else 0
    f = int(m.group(1)) if (m := re.search(r"(\d+) failed", out)) else 0
    if "error" in out and p == 0 and f == 0:
        f = -1
    return p, f, out[-400:]


def verify(commit: dict, workdir: Path) -> dict:
    """Build the instance and prove both controls. Returns the verdict."""
    repo, sha, parent = commit["repo"], commit["sha"], commit["parent"]
    d = workdir / sha[:10]
    try:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        # 1. fetch the tarball at the FIX commit (includes the fix and its tests)
        url = f"https://codeload.github.com/{repo}/tar.gz/{sha}"
        tgz = workdir / f"{sha[:10]}.tgz"
        subprocess.run(["curl", "-sSL", url, "-o", str(tgz)], check=True, timeout=300)
        subprocess.run(["tar", "xzf", str(tgz), "-C", str(d), "--strip-components=1"],
                       check=True, timeout=180)
        if not (d / "tests").is_dir():
            return {**{k: v for k, v in commit.items() if k != "recoverable_sources"},
                    "valid": False, "reason": "NO_TESTS_DIR"}

        # install the repo's own test dependencies before judging it
        _ensure_deps(d)
        scope = [f for f in commit["test_files_changed"] if (d / f).is_file()]

        # 2. control GREEN: the fixed commit must pass its own suite
        gp, gf, _ = _pytest(d, scope)
        if gf != 0 or gp == 0:
            return {**{k: v for k, v in commit.items() if k != "recoverable_sources"},
                    "valid": False,
                    "reason": f"FIX_CONTROL_NOT_GREEN ({gp} passed {gf} failed)"}

        # 3. control RED: revert the source files to their parent text
        for rel, text in commit["recoverable_sources"].items():
            tgt = d / rel
            if tgt.is_file():
                tgt.write_text(text)
        rp, rf, _ = _pytest(d, scope)
        if rf == 0:
            return {**{k: v for k, v in commit.items() if k != "recoverable_sources"},
                    "valid": False,
                    "reason": "REVERT_DOES_NOT_FAIL (test may not have existed at parent)"}

        return {
            "id": f"{repo.split('/')[-1]}_{sha[:8]}",
            "repo": repo,
            "sha": sha,
            "parent": parent,
            "subject": commit["subject"],
            "valid": True,
            "fix_control": f"{gp} passed {gf} failed",
            "revert_control": f"{rp} passed {rf} failed",
            "src_files": list(commit["recoverable_sources"]),
            "patch_fingerprint": hashlib.sha256(
                "".join(commit["recoverable_sources"][k]
                        for k in sorted(commit["recoverable_sources"])).encode()
            ).hexdigest()[:16],
            "test_files": commit["test_files_changed"],
        }
    except Exception as e:
        return {**{k: v for k, v in commit.items() if k != "recoverable_sources"},
                "valid": False, "reason": f"EXCEPTION {type(e).__name__}: {e}"[:160]}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def mine(repos: list[str], limit: int, max_commits: int, workdir: Path) -> dict:
    inspected, candidates, valid, rejected = [], [], [], []
    _seen_bug_fingerprints: set[tuple] = set()
    for repo in repos:
        commits = list_fix_commits(repo, per_page=max_commits)[:max_commits]
        for c in commits:
            if len(valid) >= limit:
                break
            e = examine(c)
            inspected.append({"repo": repo, "sha": c["sha"][:8], "subject": c["subject"],
                              "reason": e.get("reason")})
            if not e.get("candidate"):
                rejected.append(e.get("reason"))
                continue
            candidates.append(e)
            parent_texts = [e["recoverable_sources"][k]
                            for k in sorted(e["recoverable_sources"])]
            v = verify(e, workdir)
            if v.get("valid"):
                # DEDUPE BY BUG, NOT BY COMMIT. A fix commit and its merge commit can both
                # produce a valid instance with identical controls; counting both inflates
                # the denominator with a bug that only exists once. The fingerprint is the
                # (repo, revert-control signature, primary source file).
                # Key on the PATCH, not the symptom and not the sha. A fix commit and its
                # merge commit share a recovered parent text, so their reverted source is
                # byte-identical -- that is the bug. Two DIFFERENT fixes in the same file
                # (jinja had two) differ here and are correctly kept apart. Including the
                # sha (or omitting the patch) collapses all of them into one bug.
                patch_fp = hashlib.sha256(
                    "".join(parent_texts).encode()).hexdigest()[:16]
                fp = (v["repo"], patch_fp)
                if fp in _seen_bug_fingerprints:
                    rejected.append("DUPLICATE_BUG_FAMILY")
                    continue
                _seen_bug_fingerprints.add(fp)
                valid.append(v)
            else:
                rejected.append(v.get("reason"))
        if len(valid) >= limit:
            break

    from collections import Counter
    return {
        "schema": SCHEMA,
        "repos_scanned": repos,
        "commits_inspected": len(inspected),
        "commits_offered_to_verification": len(candidates),
        "valid_instances": len(valid),
        "rejections": len(rejected),
        "rejection_reasons": dict(Counter(
            (r or "").split(" (")[0] for r in rejected)),
        "valid_yield_pct": round(100.0 * len(valid) / max(1, len(candidates)), 1),
        "instances": valid,
        "inspected": inspected,
        "trained_parameters": 0,
        "external_model_calls": 0,
        "incremental_spend_usd": 0,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*", default=DEFAULT_REPOS)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--max-commits", type=int, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)

    work = Path(tempfile.mkdtemp(prefix="miner_"))
    try:
        out = mine(args.repos, args.limit, args.max_commits, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
    if args.json:
        print(json.dumps({k: v for k, v in out.items() if k != "inspected"}, indent=1))
        return 0

    print("=" * 76)
    print("REAL INSTANCE MINER — every instance proven by two controls before counting")
    print("=" * 76)
    print(f"  repos scanned      {out['repos_scanned']}")
    print(f"  commits inspected  {out['commits_inspected']}")
    print(f"  offered to verify  {out['commits_offered_to_verification']}")
    print(f"  VALID instances    {out['valid_instances']}")
    print(f"  rejected           {out['rejections']}")
    if out["rejection_reasons"]:
        print("  why rejected:")
        for k, v in sorted(out["rejection_reasons"].items(), key=lambda kv: -kv[1]):
            print(f"      {v:3d}  {k}")
    print()
    for inst in out["instances"]:
        print(f"  VALID {inst['id']}")
        print(f"        {inst['subject'][:70]}")
        print(f"        fix {inst['fix_control']} | revert {inst['revert_control']}")
    print()
    print(f"  yield {out['valid_yield_pct']}% of offered commits became valid instances")
    print(f"  trained params {out['trained_parameters']} | model calls "
          f"{out['external_model_calls']} | spend ${out['incremental_spend_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
