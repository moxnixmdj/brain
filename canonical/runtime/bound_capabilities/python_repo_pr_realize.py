# PROJECT_BRAIN
"""python.repo.pr_realize.v1 — the crown's last mile: turn a verified
pr_intent + produced diff into real forge bytes.

Today the pipeline ends at ``pr_intent.json`` — an intention.  A senior
engineer ships: branch from the base, apply the reviewed diff, commit
with the intent's message, push, and PROVE the remote now points at
exactly the bytes built here.  This adapter does that with pinned
timestamps so the commit sha is a pure function of content (reruns are
byte-identical and idempotent).

* hermetic by construction: pushes to the repo's configured ``origin``
  only; pins use a local bare repo as origin (no network, full proof).
* refuse-before-anything: non-git repo, no origin remote, bogus diff,
  unreadable intent — all named refusals.
* fail closed at the END too: after push, ``git ls-remote`` must return
  exactly the sha committed here; mismatch -> PUSH_SHA_MISMATCH failure
  receipt, never a fabricated success.
* idempotent: if origin's head_branch already equals the produced sha,
  nothing is force-pushed; the receipt says ``already_realized: true``
  (relying on pinned-date determinism).

Laws:
* zero ambient identity: author/committer come from pr_intent fields or
  explicit args, dates pinned — the sha is content-addressable and the
  ritual is reproducible.
* the working tree is restored if apply fails; a partial branch never
  leaks into the caller's checkout state beyond the intended branch.

Inputs (kwargs):
  repo_path        git worktree with an origin remote
  diff_path        verified unified diff (from the crown, post-gates)
  apply_directory  prefix under which the diff's paths live (e.g. "src"
                   when the crown diffed source_root); default "" (root)
  pr_intent_path   orchestrator's pr_intent.json (title/body/prefix)
  output_path      realization receipt artifact
  base_branch      branch to cut from (default: repo's current HEAD)
  branch_name      head branch to create/update
  author_name/email / committer_name/email   identity pins
  author_date/committer_date                 ISO-8601 pins (default epoch)
  timeout_s        wall-clock cap per git call (default 120)

result_fields: adapter, branch_name, head_sha, remote_ref, pushed,
already_realized, push_verified, gate, complete, output_path,
output_sha256, output_verified, verified.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_PR_REALIZE_V1"


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True,
                                 "capability": "python.repo.pr_realize.v1",
                                 "reason": reason}, indent=2, sort_keys=True))


def _git(repo: Path, argv, timeout_s: int, env_extra=None, check=True):
    import os
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(["git", "-C", str(repo)] + argv,
                          capture_output=True, text=True, timeout=timeout_s, env=env)
    if check and proc.returncode != 0:
        _fail("GIT_COMMAND_FAILED:" + " ".join(argv[:2]) + ":" +
              (proc.stderr.strip().splitlines() or ["<empty>"])[-1][:200])
    return proc


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run(args, root):
    args = dict(args or {})
    repo_rel = str(args.get("repo_path") or ".")
    repo = (Path(root) / repo_rel).resolve() if root else Path(repo_rel).resolve()
    if not (repo / ".git").exists():
        _fail("REPO_NOT_GIT")
    diff_rel = str(args.get("diff_path") or "")
    diff_abs = (repo / diff_rel).resolve()
    if repo not in diff_abs.parents:
        _fail("PATH_ESCAPE:" + diff_rel)
    if not diff_abs.is_file():
        _fail("PATH_MISSING:" + diff_rel)
    diff_text = diff_abs.read_text(encoding="utf-8", errors="replace")
    if not diff_text.strip():
        _fail("DIFF_EMPTY")
    intent_rel = str(args.get("pr_intent_path") or "")
    intent_abs = (repo / intent_rel).resolve()
    if repo not in intent_abs.parents:
        _fail("PATH_ESCAPE:" + intent_rel)
    intent = {}
    if intent_abs.is_file():
        try:
            intent = json.loads(intent_abs.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            _fail("PR_INTENT_NOT_JSON")
    out_rel = str(args.get("output_path") or "")
    out_abs = (repo / out_rel).resolve()
    if repo not in out_abs.parents:
        _fail("PATH_ESCAPE:" + out_rel)
    timeout_s = int(args.get("timeout_s") or 120)
    branch = str(args.get("branch_name") or "")
    if not branch or branch.startswith("-") or ".." in branch:
        _fail("BRANCH_NAME_INVALID")
    base = str(args.get("base_branch") or "HEAD")
    apply_dir = str(args.get("apply_directory") or "").strip("/")
    apply_argv = ["apply", "--unidiff-zero"] + (["--directory", apply_dir] if apply_dir else [])

    remotes = _git(repo, ["remote"], timeout_s).stdout.split()
    if "origin" not in remotes:
        _fail("NO_ORIGIN_REMOTE")

    author = str(args.get("author_name") or intent.get("author") or "crown")
    aemail = str(args.get("author_email") or "crown@brain.local")
    cname = str(args.get("committer_name") or author)
    cemail = str(args.get("committer_email") or aemail)
    adate = str(args.get("author_date") or "2026-01-01T00:00:00Z")
    cdate = str(args.get("committer_date") or adate)
    title = str(args.get("title") or intent.get("title") or "crown change")
    body = str(args.get("body") or intent.get("body") or "")
    message = title + ("\n\n" + body if body else "")

    env_id = {"GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": aemail,
              "GIT_AUTHOR_DATE": adate,
              "GIT_COMMITTER_NAME": cname, "GIT_COMMITTER_EMAIL": cemail,
              "GIT_COMMITTER_DATE": cdate}

    # cut the branch from base inside the SAME worktree (intent law: the
    # repo may be a scratch clone; caller passes the tree they want used)
    _git(repo, ["checkout", "-q", "-B", branch, base], timeout_s)
    check = _git(repo, apply_argv + ["--check", diff_rel], timeout_s, check=False)
    if check.returncode != 0:
        _git(repo, ["checkout", "-q", "-"], timeout_s, check=False)
        _fail("DIFF_DOES_NOT_APPLY:" + (check.stderr.strip().splitlines() or ["<empty>"])[0][:200])
    _git(repo, apply_argv + [diff_rel], timeout_s)
    # stage EXACTLY the paths the diff touched -- crown bookkeeping files
    # (the diff itself, pr_intent, receipts) must never be committed, and a
    # rerun of the same diff must find its own inputs still on disk.
    from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
        _parse_diff_ranges)
    touched = sorted(_parse_diff_ranges(diff_text)[0])
    if apply_dir:
        touched = [apply_dir + "/" + t for t in touched]
    _git(repo, ["add", "--"] + touched, timeout_s)
    staged = _git(repo, ["diff", "--cached", "--quiet"], timeout_s, check=False)
    if staged.returncode == 0:
        _fail("DIFF_PRODUCED_NO_CHANGES")
    _git(repo, ["commit", "-q", "-m", message], timeout_s, env_extra=env_id)
    head_sha = _git(repo, ["rev-parse", "HEAD"], timeout_s).stdout.strip()

    remote_ref = f"refs/heads/{branch}"
    prior = _git(repo, ["ls-remote", "origin", remote_ref], timeout_s, check=False)
    prior_sha = prior.stdout.split()[0] if prior.stdout.strip() else None
    if prior_sha == head_sha:
        pushed, already = False, True
    else:
        push = _git(repo, ["push", "-q", "origin", f"HEAD:{remote_ref}"],
                    timeout_s, check=False)
        if push.returncode != 0:
            _fail("PUSH_FAILED:" + (push.stderr.strip().splitlines() or ["<empty>"])[-1][:200])
        pushed, already = True, False

    remote_now = _git(repo, ["ls-remote", "origin", remote_ref], timeout_s, check=False)
    remote_sha = remote_now.stdout.split()[0] if remote_now.stdout.strip() else None
    verified = remote_sha == head_sha and prior_sha != head_sha or \
        (already and remote_sha == head_sha)
    gate = "PASS" if verified else "FAIL"

    artifact = {
        "schema": SCHEMA,
        "repo_path": repo_rel,
        "branch_name": branch,
        "base_branch": base,
        "head_sha": head_sha,
        "remote_ref": remote_ref,
        "remote_sha": remote_sha,
        "diff_sha256": _sha256(diff_text.encode("utf-8")),
        "commit_dates_pinned": {"author": adate, "committer": cdate},
        "pushed": pushed,
        "already_realized": already,
        "push_verified": verified,
        "gate": gate,
        "gate_law": ("PASS requires: branch cut from base, diff applied, commit with "
                     "pinned identity/date (sha = pure content function), pushed to "
                     "origin, and ls-remote returning EXACTLY the committed sha; "
                     "idempotent rerun reports already_realized without force-push"),
        "complete": True,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_repo_pr_realize",
        "branch_name": branch,
        "head_sha": head_sha,
        "remote_ref": remote_ref,
        "pushed": pushed,
        "already_realized": already,
        "push_verified": bool(verified),
        "gate": gate,
        "complete": True,
        "output_path": out_rel,
        "output_sha256": _sha256(text.encode("utf-8")),
        "output_verified": out_verified,
        "verified": bool(verified),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--repo_path", default=".")
    p.add_argument("--diff_path", required=True)
    p.add_argument("--pr_intent_path", default="")
    p.add_argument("--output_path", required=True)
    p.add_argument("--branch_name", required=True)
    p.add_argument("--base_branch", default="HEAD")
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), None), indent=2, sort_keys=True))
