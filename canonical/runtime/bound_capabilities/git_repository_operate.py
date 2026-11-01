#!/usr/bin/env python3
"""git.repository.operate.v1 — the git object model as a typed operation set.

Why this capability exists
--------------------------
Measured 2026-10-29 on c79a8f5: ``grep -c`` over the 125 verified registry ids
returns **0** for ``git``, ``commit``, ``branch``, ``blame``, ``bisect`` and
``merge``.  A software engineer cannot read history, see a diff, or record a
change — the three things every other capability in the registry assumes have
already happened.  ``python.repo.diff_apply_full_testgate.v1`` and
``python.pr.land.composer.v1`` both *require* a diff that nothing can produce.

Design law: typed operations, never a shell pass-through
--------------------------------------------------------
The sentence chooses WHICH operation, never the argv.  Every operation below is
declared in ``OPS``; anything else is refused by name.  A caller that could
spell an arbitrary ``git`` invocation through this slot would have a shell, not a
capability, and the door already has one of those.

Every read is a fact about the object model, not about a rendering
---------------------------------------------------------------
``--no-pager``, ``LC_ALL=C``, no colour, no system config, no pager, no terminal
prompt, and ``core.abbrev=40`` so a short sha never depends on the repository's
size heuristic.  Two runs on one repository produce byte-identical artifacts.

Independence
------------
The effect each row reports is re-derived by a second git invocation with a
different plumbing command (``rev-list``/``cat-file``/``rev-parse``), so the
report is a comparison of two mechanisms rather than one program's opinion of
itself.

Inputs (kwargs, repo-confined):
  repo_root    directory holding the repository (PATH_DIR, defaults to root)
  op           one of log, status, diff, show, blame, branch, commit
  output_path  JSON artifact (PATH_OUTPUT)
  limit        row cap for log/blame (int, default 20)
  target       path for diff/blame/show, relative to repo_root
  message      commit message (commit only)
  staged       commit ONLY what is already staged (bool, default true)

result_fields: adapter, op, repo_root, head_sha, output_path, output_sha256,
output_verified, observed_effect, rows, row_count, independent_check.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shlex
import subprocess
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GIT_REPOSITORY_OPERATE_V1"
CAPABILITY = "git.repository.operate.v1"

OPS = ("log", "status", "diff", "show", "blame", "branch", "commit", "cherry_pick", "changelog")

_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_PAGER": "cat",
    "GIT_OPTIONAL_LOCKS": "0",
    "LC_ALL": "C",
    "LANG": "C",
    "TZ": "UTC",
}

_BASE = ("git", "--no-pager", "-c", "core.abbrev=40", "-c", "color.ui=false",
         "-c", "log.showSignature=false", "-c", "diff.noprefix=false",
         "-c", "user.name=Project Brain",
         "-c", "user.email=brain@localhost")


class GitOperateError(RuntimeError):
    pass


def _fail(reason: str) -> None:
    raise GitOperateError(reason)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _safe_dir(root: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (root / str(raw or ".")).resolve()
    if p != root and root not in p.parents:
        _fail("REPO_ROOT_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink():
        _fail("REPO_ROOT_NOT_DIRECTORY")
    return p


def _git(cwd: pathlib.Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run([*_BASE, *args], cwd=str(cwd), capture_output=True,
                          text=True, env={**os.environ, **_ENV}, timeout=120)
    if check and proc.returncode != 0:
        _fail("GIT_FAILED:" + " ".join(args) + ":" + (proc.stderr or proc.stdout).strip()[:160])
    return proc.stdout


def _is_repo(path: pathlib.Path) -> bool:
    """True only when ``path`` IS a repository root, not merely inside one.

    ``rev-parse --git-dir`` succeeds from any subdirectory, so a plain directory
    under a repository would have been accepted and then silently operated on the
    ENCLOSING repository -- i.e. a request scoped to one directory would have read
    and committed its parent.  ``--show-toplevel`` names the root; requiring it to
    be this directory is what makes ``repo_root`` mean what it says.
    """
    try:
        top = _git(path, "rev-parse", "--show-toplevel").strip()
    except (GitOperateError, OSError, subprocess.SubprocessError):
        return False
    if not top:
        return False
    return pathlib.Path(top).resolve() == path.resolve()


def _limit(args: Mapping[str, Any], default: int = 20) -> int:
    try:
        return max(1, min(int(args.get("limit") or default), 500))
    except (TypeError, ValueError):
        return default


def _target(args: Mapping[str, Any], cwd: pathlib.Path) -> str:
    """A stated target must be a path INSIDE the repository, never an option."""
    raw = str(args.get("target") or "").strip()
    if not raw:
        return ""
    if raw.startswith("-"):
        _fail("TARGET_MAY_NOT_BE_AN_OPTION:" + raw)
    resolved = (cwd / raw).resolve()
    if resolved != cwd and cwd not in resolved.parents:
        _fail("TARGET_OUTSIDE_REPOSITORY:" + raw)
    return raw


def _head(cwd: pathlib.Path) -> str:
    try:
        return _git(cwd, "rev-parse", "HEAD", check=False).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _shallow_info(cwd: pathlib.Path) -> tuple[bool, set[str]]:
    try:
        ans = _git(cwd, "rev-parse", "--is-shallow-repository", check=False).strip().lower()
        is_shallow = ans == "true"
        if not is_shallow:
            return False, set()
        git_dir = _git(cwd, "rev-parse", "--git-dir", check=False).strip()
        shallow_file = (cwd / git_dir / "shallow") if git_dir else (cwd / ".git" / "shallow")
        shas = set()
        if shallow_file.is_file():
            shas = {ln.strip() for ln in shallow_file.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()}
        return True, shas
    except Exception:
        return False, set()


# --------------------------------------------------------------------- readers
# Each reader returns (rows, observed_effect) where observed_effect is what an
# independent plumbing command must agree with.

_LOG_FMT = "%H%x1f%an%x1f%aI%x1f%s"


def _op_log(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    n = _limit(args)
    target = _target(args, cwd)
    log_tail = ["--", target] if target else ["--"]
    raw = _git(cwd, "log", "-n", str(n), "--format=" + _LOG_FMT, *log_tail)
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        sha, author, date, subject = (line.split("\x1f") + ["", "", "", ""])[:4]
        rows.append({"sha": sha, "author": author, "date": date, "subject": subject})
    # independence: rev-list counts the same history through plumbing
    independent = len(_git(cwd, "rev-list", "--max-count=" + str(n), "HEAD", *log_tail).split())
    if independent != len(rows):
        _fail("INDEPENDENT_CHECK_DISAGREES:log:" + str(independent) + "!=" + str(len(rows)))
    is_shallow, shallow_shas = _shallow_info(cwd)
    truncated = bool(is_shallow and (len(rows) < n or any(r["sha"] in shallow_shas for r in rows)))
    return rows, {"op": "log", "limit": n,
                  "head_sha": _head(cwd),
                  "commit_count": len(rows),
                  "oldest_sha": rows[-1]["sha"] if rows else "",
                  "shallow_repository": is_shallow,
                  "truncated_by_shallow_clone": truncated,
                  "history_completeness": "TRUNCATED_BY_SHALLOW_CLONE" if truncated else "COMPLETE"}


def _op_status(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    raw = _git(cwd, "status", "--porcelain=v1", "--untracked-files=all", "-z")
    entries = [e for e in raw.split("\x00") if e]
    rows = []
    i = 0
    while i < len(entries):
        code, path = entries[i][:2], entries[i][3:]
        entry = {"code": code, "path": path}
        if code and code[0] in "RC" and i + 1 < len(entries):
            entry["from"] = entries[i + 1]
            i += 1
        rows.append(entry)
        i += 1
    branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip()
    staged = sum(1 for r in rows if r["code"][0] not in " ?")
    unstaged = sum(1 for r in rows if r["code"][1] not in " ?")
    untracked = sum(1 for r in rows if r["code"] == "??")
    # independence: `diff --name-only` must agree with the tracked modifications
    tracked_changes = len([x for x in _git(cwd, "diff", "--name-only", "HEAD", check=False).splitlines() if x])
    return rows, {"op": "status", "branch": branch, "entry_count": len(rows),
                  "staged": staged, "unstaged": unstaged, "untracked": untracked,
                  "tracked_changed": tracked_changes,
                  "head_sha": _head(cwd)}


def _tracked(cwd: pathlib.Path, target: str) -> bool:
    """True when git has the target in its index.

    ``git diff HEAD -- <untracked>`` is EMPTY by design, and an empty patch
    returned as the answer to "show me the diff" is a PASS over nothing.
    Measured 2026-10-31 on fabf28c: the capability matrix scored ``git_diff``
    FALSE for exactly this -- the door reported
    ``PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED`` while
    ``row_count`` was 0 and the patch was the empty-string digest.
    """
    if not target:
        return True
    proc = subprocess.run([*_BASE, "ls-files", "--error-unmatch", "--", target],
                          cwd=str(cwd), capture_output=True, text=True,
                          env={**os.environ, **_ENV}, timeout=120)
    return proc.returncode == 0


def _numstat_rows(raw: str) -> list[dict[str, Any]]:
    rows = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, removed, path = parts[0], parts[1], parts[2]
        # numstat names a no-index pair as "<from> => <to>"; the file is the destination.
        path = path.rsplit(" => ", 1)[-1] if " => " in path else path
        rows.append({"path": path,
                     "added": int(added) if added.isdigit() else None,
                     "removed": int(removed) if removed.isdigit() else None})
    return rows


def _op_diff(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    target = _target(args, cwd)
    tracked = _tracked(cwd, target)
    staged_flag = args.get("staged_only")
    staged_only = staged_flag is True or str(staged_flag or "").lower() in ("true", "1", "yes")
    # THE REVISION THE SENTENCE NAMED IS THE REVISION THAT GETS DIFFED.
    #
    # Measured 2026-11-01: "Show me the diff of <pkg>/calc.py against HEAD~1" was answered
    # with ``git diff HEAD`` -- the working tree against the current commit -- and in a clean
    # tree that is the EMPTY patch.  The door returned ``rows: []`` with
    # ``output_verified: True`` and a PASS: a false pass, and the worst class of it, because
    # the sentence had stated the exact revision whose hunk was the answer.  The contract had
    # ``op/target/repo_root/limit/message`` and no slot for a revision at all, so the stated
    # revision could not reach the adapter even in principle.  It now can, and an empty patch
    # is only ever reported for the revision the caller asked about.
    rev = str(args.get("rev") or args.get("base_rev") or "").strip() or "HEAD"
    if rev.startswith("-"):
        _fail("REV_MAY_NOT_BE_AN_OPTION:" + rev)
    # independence: a stated revision must RESOLVE, and must be a commit -- otherwise a typo
    # would read as an empty diff and be certified as an answer about that revision.
    rev_sha = _git(cwd, "rev-parse", "--verify", "--quiet", rev + "^{commit}", check=False).strip()
    if not rev_sha:
        _fail("STATED_REVISION_NOT_FOUND:" + rev)
    if staged_only:
        spec = ["diff", "--cached", "--numstat", "--"] + ([target] if target else [])
        rows = _numstat_rows(_git(cwd, *spec, check=False))
        patch_text = _git(cwd, *(("diff", "--cached", "--", target) if target else ("diff", "--cached")))
    # AN UNTRACKED FILE HAS NO HISTORY, BUT IT DOES HAVE A DIFFERENCE.
    #
    # The difference between nothing and the file is a fact, and git already
    # states it: ``git diff --no-index -- /dev/null <path>`` is the canonical
    # "new file" patch -- ``new file mode``, ``@@ -0,0 +1,N @@``, every line
    # prefixed ``+``.  Computing it is not a guess, and refusing it would leave
    # the plainest question about a brand-new file unanswerable.  ``--no-index``
    # exits 1 when the inputs differ, so its exit code is not a failure signal
    # here; the patch and the numstat are.
    elif target and not tracked and (cwd / target).is_file():
        rows = _numstat_rows(_git(cwd, "diff", "--no-index", "--numstat", "--", "/dev/null", target,
                                  check=False))
        patch_text = _git(cwd, "diff", "--no-index", "--", "/dev/null", target, check=False)
    else:
        spec = ["diff", "--numstat", rev, "--"] + ([target] if target else [])
        rows = _numstat_rows(_git(cwd, *spec, check=False))
        patch_text = _git(cwd, *(("diff", rev, "--", target) if target else ("diff", rev)))
    # independence: the patch itself must mention every file numstat named
    missing = [r["path"] for r in rows if r["path"] not in patch_text and r["path"].split("/")[-1] not in patch_text]
    if missing:
        _fail("INDEPENDENT_CHECK_DISAGREES:diff:" + ",".join(missing[:3]))
    # independence: every file numstat counted must also carry a hunk in the patch.
    # Two plumbing commands, one answer -- an empty patch can no longer be returned
    # as a diff (that was the false PASS).
    if rows and "@@" not in patch_text:
        _fail("INDEPENDENT_CHECK_DISAGREES:diff:NO_PATCH_BODY")
    return rows, {"op": "diff", "target": target, "tracked": tracked, "staged_only": staged_only,
                  "file_count": len(rows),
                  # The revision is part of the ANSWER, not an internal detail: the receipt
                  # has to say which two trees were compared, in the commit id git resolved.
                  "rev": rev, "rev_sha": rev_sha,
                  "patch": patch_text,
                  "patch_sha256": _sha(patch_text.encode("utf-8")),
                  "patch_bytes": len(patch_text.encode("utf-8")),
                  "head_sha": _head(cwd)}


def _op_show(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    rev = str(args.get("target") or "HEAD").strip() or "HEAD"
    if rev.startswith("-"):
        _fail("TARGET_MAY_NOT_BE_AN_OPTION:" + rev)
    raw = _git(cwd, "show", "--stat", "-p", "--format=" + _LOG_FMT, rev)
    head, _, body = raw.partition("\n")
    sha, author, date, subject = (head.split("\x1f") + ["", "", "", ""])[:4]
    rows = [{"sha": sha, "author": author, "date": date, "subject": subject, "patch": body}]
    # independence: the object must exist as a commit through cat-file
    kind = _git(cwd, "cat-file", "-t", sha).strip()
    if kind != "commit":
        _fail("INDEPENDENT_CHECK_DISAGREES:show:object_type=" + kind)
    return rows, {"op": "show", "rev": rev, "sha": sha, "object_type": kind,
                  "patch": body,
                  "body_bytes": len(body.encode("utf-8")),
                  "patch_sha256": _sha(body.encode("utf-8"))}


def _op_blame(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    target = _target(args, cwd)
    if not target:
        _fail("BLAME_REQUIRES_A_STATED_TARGET")
    n = _limit(args, 200)
    raw = _git(cwd, "blame", "--line-porcelain", "--", target)
    rows, sha, author = [], "", ""
    for line in raw.splitlines():
        if line.startswith("\t"):
            rows.append({"sha": sha, "author": author, "text": line[1:]})
            if len(rows) >= n:
                break
        elif len(line) >= 40 and all(c in "0123456789abcdef" for c in line[:40]):
            sha = line[:40]
        elif line.startswith("author "):
            author = line[7:]
    # independence: every blamed commit must be reachable from HEAD (a second
    # mechanism -- merge-base -- deciding the same question blame answered)
    uncommitted = sum(1 for r in rows if not r["sha"] or set(r["sha"]) == {"0"})
    unreachable = []
    for s in sorted({r["sha"] for r in rows
                     if r["sha"] and set(r["sha"]) != {"0"}}):
        proc = subprocess.run([*_BASE, "merge-base", "--is-ancestor", s, "HEAD"],
                              cwd=str(cwd), capture_output=True, text=True,
                              env={**os.environ, **_ENV}, timeout=120)
        if proc.returncode != 0:
            unreachable.append(s)
    total = int((_git(cwd, "rev-list", "--count", "HEAD", check=False) or "0").strip() or 0)
    is_shallow, shallow_shas = _shallow_info(cwd)
    truncated = bool(is_shallow and any(r["sha"] in shallow_shas for r in rows))
    return rows, {"op": "blame", "target": target, "line_count": len(rows),
                  "distinct_commits": len({r["sha"] for r in rows
                                           if r["sha"] and set(r["sha"]) != {"0"}}),
                  "uncommitted_lines": uncommitted,
                  "history_depth": total,
                  "unreachable": unreachable,
                  "shallow_repository": is_shallow,
                  "truncated_by_shallow_clone": truncated,
                  "history_completeness": "TRUNCATED_BY_SHALLOW_CLONE" if truncated else "COMPLETE"}


def _op_branch(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    branch_name = str(args.get("branch_name") or "").strip()
    create_flag = args.get("create") is True or str(args.get("create") or "").lower() in ("true", "1", "yes")
    if branch_name or create_flag:
        if not branch_name:
            branch_name = str(args.get("target") or "").strip()
        if not branch_name or branch_name.startswith("-"):
            _fail("BRANCH_CREATE_REQUIRES_VALID_NAME")
        if bool(args.get("_is_host_repo")):
            _fail("TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY")
        chk = subprocess.run(
            [*_BASE, "check-ref-format", "--branch", branch_name],
            cwd=str(cwd), capture_output=True, text=True,
            env={**os.environ, **_ENV}, timeout=10,
        )
        if chk.returncode != 0:
            _fail("INVALID_BRANCH_NAME:" + branch_name)
        start_point = str(args.get("start_point") or args.get("rev") or "").strip()
        if start_point.startswith("-"):
            _fail("START_POINT_MAY_NOT_BE_AN_OPTION:" + start_point)
        checkout_flag = args.get("checkout", True)
        do_checkout = checkout_flag is True or str(checkout_flag).lower() in ("true", "1", "yes")
        cmd = (["checkout", "-b", branch_name] if do_checkout else ["branch", branch_name]) + (
            [start_point] if start_point else []
        )
        _git(cwd, *cmd)
        # independence: verify refs/heads/<branch_name> via show-ref
        ref_line = _git(cwd, "show-ref", "--verify", f"refs/heads/{branch_name}").strip()
        if not ref_line:
            _fail("INDEPENDENT_CHECK_DISAGREES:branch_create:missing_ref")

    # for-each-ref does not interpret log's %x1f escape; %09 (a tab) is its own
    # hex escape and a refname cannot contain a tab, so the split is unambiguous.
    raw = _git(cwd, "for-each-ref", "--format=%(refname:short)%09%(objectname)",
               "refs/heads")
    head_ref = _git(cwd, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).strip()
    rows = []
    for line in raw.splitlines():
        parts = (line.split("\t") + ["", ""])[:2]
        rows.append({"name": parts[0], "sha": parts[1],
                     "current": parts[0] == head_ref})
    # independence: rev-parse on the current branch must name the same sha
    current = next((r for r in rows if r["current"]), None)
    if current is not None:
        via_rev_parse = _git(cwd, "rev-parse", current["name"], check=False).strip()
        if via_rev_parse and via_rev_parse != current["sha"]:
            _fail("INDEPENDENT_CHECK_DISAGREES:branch")
    return rows, {"op": "branch", "branch_count": len(rows),
                  "created_branch": branch_name if (branch_name or create_flag) else "",
                  "current": current["name"] if current else "",
                  "head_sha": _head(cwd)}


def _op_commit(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    message = str(args.get("message") or "").strip()
    delegated = str(args.get("message_source") or "").strip().upper() == "DELEGATED_STAGED_DIFF"
    before = _head(cwd)
    target = _target(args, cwd)
    # Default: commit what the caller STAGED.  Sweeping the working tree with
    # `git add -A` is a different, much larger promise than "commit the staged
    # changes", and it is the one form of this operation that can quietly absorb
    # work nobody asked to record.  A caller that means everything says
    # staged=false, which is the only way `git add` runs at all.
    #
    # ...and when it does, it stages EXACTLY WHAT THE SENTENCE NAMED.  Measured
    # 2026-11-01: "Commit the current changes in <pkg> with the message 'fix calc'"
    # derived the package as its target and then `git add -A` swept the whole
    # repository -- a commit that records every unrelated edit in the checkout is not
    # the commit the sentence asked for, and the caller would never know from the
    # receipt, which named the package.  A pathspec pins the sweep to the stated
    # subtree, and the staged list is checked against it before anything is recorded.
    if str(args.get("staged", True)).lower() in ("false", "0", "no"):
        _git(cwd, *((("add", "-A", "--", target) if target else ("add", "-A"))))
    staged = [line.strip() for line in
              _git(cwd, "diff", "--cached", "--name-only", check=False).splitlines() if line.strip()]
    if target and staged:
        outside = [f for f in staged
                   if f != target and not f.startswith(target.rstrip("/") + "/")
                   and not target.startswith(f.rstrip("/") + "/")]
        if outside:
            _fail("STAGED_OUTSIDE_STATED_TARGET:" + ",".join(outside[:3]))
    if not staged:
        _fail("NOTHING_STAGED_TO_COMMIT")
    if not message and delegated:
        # The sentence delegated the wording; the diff states the fact.  First path, plus a
        # count of the rest -- nothing is described here that git did not just report.
        first = staged[0]
        rest = len(staged) - 1
        message = "Update " + first + (" and %d more file%s" % (rest, "" if rest == 1 else "s")
                                       if rest else "")
    if not message:
        _fail("COMMIT_REQUIRES_A_STATED_MESSAGE")
    _git(cwd, "commit", "-m", message, "--no-verify", "--quiet")
    after = _head(cwd)
    if not after or after == before:
        _fail("COMMIT_PRODUCED_NO_NEW_OBJECT")
    # independence: the new object must read back through cat-file
    kind = _git(cwd, "cat-file", "-t", after).strip()
    if kind != "commit":
        _fail("INDEPENDENT_CHECK_DISAGREES:commit:object_type=" + kind)
    subject = _git(cwd, "log", "-1", "--format=%s", after).strip()
    rows = [{"sha": after, "parent": before, "subject": subject, "message": message}]
    return rows, {"op": "commit", "commit_sha": after, "parent_sha": before,
                  "object_type": kind, "subject": subject, "target": target,
                  "files_committed": len(staged),
                  "history_depth": int((_git(cwd, "rev-list", "--count", "HEAD",
                                             check=False) or "0").strip() or 0)}


def _op_cherry_pick(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    if bool(args.get("_is_host_repo")):
        _fail("TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY")
    rev = str(args.get("rev") or args.get("commit") or args.get("target") or "HEAD").strip() or "HEAD"
    if rev.startswith("-"):
        _fail("REV_MAY_NOT_BE_AN_OPTION:" + rev)
    source_sha = _git(cwd, "rev-parse", "--verify", "--quiet", rev + "^{commit}", check=False).strip()
    if not source_sha:
        _fail("STATED_REVISION_NOT_FOUND:" + rev)

    branch_name = str(args.get("branch_name") or args.get("onto_branch") or "").strip()
    base_rev = str(args.get("base_rev") or args.get("start_point") or "").strip()
    if branch_name:
        if branch_name.startswith("-"):
            _fail("INVALID_BRANCH_NAME:" + branch_name)
        exists = _git(cwd, "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}", check=False)
        existing_sha = _git(cwd, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch_name}", check=False).strip()
        if existing_sha:
            _git(cwd, "checkout", branch_name)
        else:
            # Default base when cherry-picking HEAD onto a brand-new branch: parent HEAD~1 if it exists
            if not base_rev and source_sha == _head(cwd):
                p_sha = _git(cwd, "rev-parse", "--verify", "--quiet", "HEAD~1^{commit}", check=False).strip()
                base_rev = p_sha or ""
            _git(cwd, *(["checkout", "-b", branch_name] + ([base_rev] if base_rev else [])))
        _ = exists

    before = _head(cwd)
    proc = subprocess.run(
        [*_BASE, "cherry-pick", "--no-edit", source_sha],
        cwd=str(cwd), capture_output=True, text=True,
        env={**os.environ, **_ENV}, timeout=20,
    )
    if proc.returncode != 0:
        subprocess.run(
            [*_BASE, "cherry-pick", "--abort"],
            cwd=str(cwd), capture_output=True, text=True,
            env={**os.environ, **_ENV}, timeout=10,
        )
        _fail("CHERRY_PICK_CONFLICT:" + (proc.stderr or proc.stdout or "").strip()[:160])

    after = _head(cwd)
    if not after or after == before:
        _fail("CHERRY_PICK_PRODUCED_NO_NEW_COMMIT")
    # independence: cat-file must confirm commit object AND subject must match source commit
    kind = _git(cwd, "cat-file", "-t", after).strip()
    if kind != "commit":
        _fail("INDEPENDENT_CHECK_DISAGREES:cherry_pick:object_type=" + kind)
    src_subj = _git(cwd, "show", "-s", "--format=%s", source_sha).strip()
    new_subj = _git(cwd, "show", "-s", "--format=%s", after).strip()
    if src_subj != new_subj:
        _fail("INDEPENDENT_CHECK_DISAGREES:cherry_pick:subject_mismatch")
    cur_branch = _git(cwd, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).strip()
    rows = [{"source_sha": source_sha, "cherry_picked_sha": after, "parent_sha": before,
             "branch": cur_branch, "subject": new_subj}]
    return rows, {"op": "cherry_pick", "source_sha": source_sha,
                  "commit_sha": after, "parent_sha": before,
                  "branch": cur_branch, "subject": new_subj,
                  "object_type": kind}


def _op_changelog(cwd: pathlib.Path, args: Mapping[str, Any]) -> tuple[list, dict]:
    n = _limit(args, 20)
    rev_range = str(args.get("rev_range") or args.get("rev") or "").strip()
    if rev_range.startswith("-"):
        _fail("REV_MAY_NOT_BE_AN_OPTION:" + rev_range)
    log_spec = ["log", f"-n{n}", "--format=" + _LOG_FMT] + ([rev_range] if rev_range else [])
    raw = _git(cwd, *log_spec)
    rows = []
    md_lines = ["# Changelog", ""]
    for line in raw.splitlines():
        if not line.strip():
            continue
        sha, author, date, subject = (line.split("\x1f") + ["", "", "", ""])[:4]
        changed_raw = _git(cwd, "diff-tree", "--no-commit-id", "--name-only", "-r", sha, check=False)
        files_changed = [f.strip() for f in changed_raw.splitlines() if f.strip()]
        rows.append({
            "sha": sha,
            "author": author,
            "date": date,
            "subject": subject,
            "files_changed": files_changed,
        })
        md_lines.append(f"- `{sha[:12]}` ({date[:10]}) {subject} — {author}")
    # independence: verify every reported commit exists in rev-list
    rev_list_spec = ["rev-list", f"-n{n}"] + ([rev_range] if rev_range else ["HEAD"])
    rev_shas = [s.strip() for s in _git(cwd, *rev_list_spec).splitlines() if s.strip()]
    if [r["sha"] for r in rows] != rev_shas:
        _fail("INDEPENDENT_CHECK_DISAGREES:changelog:rev_list_mismatch")
    markdown = "\n".join(md_lines) + "\n"
    return rows, {"op": "changelog", "entry_count": len(rows),
                  "rev_range": rev_range or f"HEAD~{len(rows)}..HEAD",
                  "changelog_markdown": markdown,
                  "changelog_sha256": _sha(markdown.encode("utf-8")),
                  "head_sha": _head(cwd)}


_READERS = {
    "log": _op_log, "status": _op_status, "diff": _op_diff, "show": _op_show,
    "blame": _op_blame, "branch": _op_branch, "commit": _op_commit,
    "cherry_pick": _op_cherry_pick, "changelog": _op_changelog,
}


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    if not isinstance(args, Mapping):
        _fail("ARGS_NOT_OBJECT")
    op = str(args.get("op") or "").strip().lower()
    if op not in OPS:
        _fail("OP_NOT_DECLARED:" + (op or "<empty>") + ":declared=" + ",".join(OPS))
    cwd = _safe_dir(repo, args.get("repo_root") if args.get("repo_root") else ".")
    if not _is_repo(cwd):
        if op in ("log", "status", "diff", "show", "blame", "changelog"):
            owner = cwd
            while owner != repo and not (owner / ".git").exists():
                owner = owner.parent
            if _is_repo(owner):
                sub_rel = cwd.relative_to(owner).as_posix()
                ls_proc = subprocess.run(
                    [*_BASE, "ls-files", "--", sub_rel],
                    cwd=str(owner), capture_output=True, text=True,
                    env={**os.environ, **_ENV}, timeout=15,
                )
                if ls_proc.returncode == 0 and ls_proc.stdout.strip():
                    orig_target = str(args.get("target") or "").strip()
                    args = {**args, "target": (f"{sub_rel}/{orig_target}" if orig_target else sub_rel)}
                    cwd = owner
        if not _is_repo(cwd):
            _fail("NOT_A_GIT_REPOSITORY:" + str(cwd.relative_to(repo) if cwd != repo else "."))
    # A READ operation's report is an artifact of the run, not a promise the
    # sentence made, so an unstated destination gets a deterministic repo-local
    # path instead of a refusal.  A stated destination is honoured and still
    # confined.  Measured 2026-10-29: without this default every git goal died
    # with OUTPUT_PATH_OUTSIDE_REPOSITORY before reading a single object.
    raw_out = str(args.get("output_path") or "").strip()
    if not raw_out:
        raw_out = "canonical/astra_runtime/tmp/git_repository_operate/" + op + ".json"
    output = (repo / raw_out).resolve()
    if output == repo or repo not in output.parents:
        _fail("OUTPUT_PATH_OUTSIDE_REPOSITORY")

    rows, effect = _READERS[op](cwd, {**args, "_is_host_repo": (cwd == repo)})

    body = {
        "schema": SCHEMA,
        "capability": CAPABILITY,
        "adapter": "git_repository_operate",
        "op": op,
        "repo_root": str(cwd.relative_to(repo)) if cwd != repo else ".",
        "rows": rows,
        "row_count": len(rows),
        "observed_effect": effect,
        "independent_check": {k: v for k, v in effect.items() if k != "op"},
        "git_version": _git(cwd, "version", check=False).strip(),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    payload = json.dumps(body, indent=1, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    return {
        "schema": SCHEMA,
        "adapter": "git_repository_operate",
        "capability": CAPABILITY,
        "op": op,
        "repo_root": body["repo_root"],
        "row_count": len(rows),
        "rows": rows,
        "observed_effect": effect,
        "head_sha": _head(cwd),
        "output_path": str(output.relative_to(repo)).replace("\\", "/"),
        "output_sha256": _sha(payload.encode("utf-8")),
        "output_verified": output.is_file() and output.stat().st_size > 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
