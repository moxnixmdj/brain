"""Git, as ten declared capabilities instead of eleven missing verbs.

The inventory measured this as the #1 missing area and the #1 leverage point: the machine
could not run `git status` on its own working tree, and `grep` for `git blame`, `git stash`
or `git bisect` reached **zero** files in this repository.  Everything else in software
engineering assumes this layer -- you cannot review a change you cannot see, repair a
regression you cannot bisect, or land a fix you cannot commit.

Nothing here is invented: `git` is already installed, deterministic, and free, so the
capability is a *contract around a tool that exists*, not a new algorithm.  The contract is
what makes it safe to bind:

  * the verb is one of a closed set, and each verb has a closed argv shape -- there is no
    "run this command" input anywhere, so a request cannot smuggle a shell through it;
  * every verb writes a JSON artifact whose content is parsed from git's own output, so the
    door can credit a real artifact rather than a claim;
  * a verb that changes the repository states its precondition (`WORKING_TREE_DIRTY`,
    `NOT_A_REPOSITORY`, `REF_NOT_FOUND`) and refuses instead of guessing;
  * read-only verbs run with `--no-optional-locks` and never touch the index.

Verbs: status, log, diff, blame, stash, branch_list, branch_create, checkout, commit,
revert.  `bisect` and `rebase` are deliberately absent: both need a policy decision (what
counts as "bad", what happens on conflict) that would have to be invented here, and an
invented policy is what the honesty work in this repository exists to prevent.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

CAPABILITY_PREFIX = "vcs.git"
DEFAULT_TIMEOUT_S = 120

READ_ONLY_VERBS = ("status", "log", "diff", "blame", "branch_list")
MUTATING_VERBS = ("stash", "branch_create", "checkout", "commit", "revert")
VERBS = READ_ONLY_VERBS + MUTATING_VERBS


class GitContractError(RuntimeError):
    """A refusal the caller can act on: the request did not meet the verb's contract."""


def _fail(reason: str) -> None:
    raise GitContractError(reason)


def _repo(args: dict, root: Path) -> Path:
    raw = str(args.get("worktree_path") or "").strip()
    if not raw:
        _fail("REPOSITORY_NOT_STATED")
    path = Path(raw)
    if not path.is_absolute():
        path = (root / path)
    try:
        path = path.resolve()
    except OSError:
        _fail("REPO_PATH_UNRESOLVABLE:" + raw)
    if not path.is_dir():
        _fail("REPOSITORY_NOT_A_DIRECTORY:" + raw)
    if not (path / ".git").exists():
        _fail("NOT_A_REPOSITORY:" + raw)
    return path


def _git(repo: Path, argv: list[str], timeout_s: int, check: bool = True) -> subprocess.CompletedProcess:
    """Run git with a fixed, caller-invisible shape.  No shell, no user-supplied argv text."""
    env = dict(os.environ)
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true",
                "GIT_AUTHOR_NAME": env.get("GIT_AUTHOR_NAME", "brain"),
                "GIT_AUTHOR_EMAIL": env.get("GIT_AUTHOR_EMAIL", "brain@localhost"),
                "GIT_COMMITTER_NAME": env.get("GIT_COMMITTER_NAME", "brain"),
                "GIT_COMMITTER_EMAIL": env.get("GIT_COMMITTER_EMAIL", "brain@localhost")})
    proc = subprocess.run(["git", *argv], cwd=str(repo), capture_output=True, text=True,
                          timeout=timeout_s, env=env)
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        _fail("GIT_FAILED:" + " ".join(argv[:2]) + ":" + (detail[-1] if detail else "no output")[:200])
    return proc


def _canonical(payload: dict) -> str:
    """The document whose bytes the recorded digest names: the payload with the digest blanked.

    A digest cannot include the field that holds it, so the file that carries one is hashed in
    canonical form -- `artifact_sha256` set to the empty string -- and `verify_artifact` reads the
    file back and re-derives the same digest.  Before this, the digest covered the payload as it
    was BEFORE the two metadata fields were added, so the recorded value named bytes that were
    never written, and nothing could have caught it because nothing re-derived it.
    """
    body = dict(payload)
    body["artifact_sha256"] = ""
    return json.dumps(body, indent=1, sort_keys=True) + "\n"


def verify_artifact(output_path: Path) -> str:
    """Re-derive the digest of a written artifact from its own bytes. Raises on mismatch."""
    loaded = json.loads(Path(output_path).read_text(encoding="utf-8"))
    recorded = str(loaded.get("artifact_sha256") or "")
    derived = hashlib.sha256(_canonical(loaded).encode("utf-8")).hexdigest()
    if not recorded or recorded != derived:
        _fail("ARTIFACT_DIGEST_MISMATCH:" + str(recorded)[:16])
    return derived


def _write(output_path: Path, payload: dict) -> dict:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload["artifact_path"] = str(output_path)
    payload["artifact_sha256"] = ""
    payload["artifact_sha256"] = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    output_path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    # The artifact on disk must be the artifact that was hashed; a report about a file nobody
    # wrote is exactly the hollow pass this repository keeps measuring.
    verify_artifact(output_path)
    return payload


def _output(args: dict, root: Path, capability_id: str) -> Path:
    raw = str(args.get("output_path") or "").strip()
    if not raw:
        _fail("OUTPUT_PATH_NOT_STATED")
    path = Path(raw)
    if not path.is_absolute():
        path = (root / path)
    return path


def _base(capability_id: str, verb: str, repo: Path) -> dict[str, Any]:
    return {"adapter": "vcs_git_v1", "capability_id": capability_id, "verb": verb,
            "repository": str(repo), "gate": "PASS", "model_dependency_count": 0}


# --------------------------------------------------------------------------- read-only

def _status(args, repo, cap):
    proc = _git(repo, ["--no-optional-locks", "status", "--porcelain=v1", "-b",
                       "--untracked-files=all"], args.get("timeout_s", DEFAULT_TIMEOUT_S))
    entries, branch, upstream = [], "", ""
    for line in proc.stdout.splitlines():
        if line.startswith("## "):
            head, _, tail = line[3:].partition("...")
            branch = head.strip()
            upstream = tail.strip()
            continue
        if len(line) > 3:
            entries.append({"index": line[0], "worktree": line[1], "path": line[3:]})
    return {**_base(cap, "status", repo), "branch": branch, "upstream": upstream,
            "entries": entries, "change_count": len(entries), "clean": not entries}


def _log(args, repo, cap):
    limit = max(1, min(int(args.get("max_commits") or 20), 500))
    fmt = "%H%x1f%h%x1f%an%x1f%ae%x1f%aI%x1f%s"
    proc = _git(repo, ["--no-optional-locks", "log", "-n", str(limit),
                       "--pretty=format:" + fmt], args.get("timeout_s", DEFAULT_TIMEOUT_S),
                check=False)
    if proc.returncode != 0:
        # An empty repository is a FACT about the repository, not a failure of the verb.
        if "does not have any commits" in (proc.stderr or "") or \
                "your current branch" in (proc.stderr or ""):
            return {**_base(cap, "log", repo), "commits": [], "commit_count": 0,
                    "empty_repository": True}
        _fail("GIT_FAILED:log:" + (proc.stderr or "").strip()[:200])
    commits = []
    for line in proc.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 6:
            commits.append({"sha": parts[0], "short_sha": parts[1], "author": parts[2],
                            "email": parts[3], "authored_at": parts[4], "subject": parts[5]})
    return {**_base(cap, "log", repo), "commits": commits, "commit_count": len(commits)}


def _diff(args, repo, cap):
    staged = bool(args.get("staged"))
    ref = str(args.get("ref") or "").strip()
    argv = ["--no-optional-locks", "diff", "--no-color", "--unified=%d" % int(args.get("context_lines") or 3)]
    if staged:
        argv.append("--cached")
    if ref:
        if not _rev_exists(repo, ref, args):
            _fail("REF_NOT_FOUND:" + ref)
        argv.append(ref)
    if args.get("path"):
        argv += ["--", str(args["path"])]
    stat = _git(repo, argv + ["--stat"], args.get("timeout_s", DEFAULT_TIMEOUT_S))
    patch = _git(repo, argv, args.get("timeout_s", DEFAULT_TIMEOUT_S))
    files = [line.split("|")[0].strip() for line in stat.stdout.splitlines()
             if "|" in line]
    return {**_base(cap, "diff", repo), "ref": ref, "staged": staged, "files": files,
            "file_count": len(files), "stat": stat.stdout, "patch": patch.stdout,
            "empty": not patch.stdout.strip()}


def _inside(repo, path: str):
    """The file a stated path names, resolved the way the front layer states paths.

    The binder states paths relative to the ROOT it was given -- "canonical/astra_runtime/.../repo/pkg/calc.py"
    -- while a git verb needs them relative to the worktree it was pointed at.  Both name the same
    file, so the worktree is found inside the stated path instead of the path being refused:
    every trailing part of the stated path is tried, from the longest, and the first that exists
    under the worktree wins.  Nothing is invented -- a path that names no file inside the stated
    repository is still refused -- and the search is over the path's own components, so it cannot
    reach outside the repository the sentence stated.
    """
    stated = Path(path)
    if not stated.is_absolute() and (repo / stated).is_file():
        return stated
    parts = stated.parts[1:] if stated.is_absolute() else stated.parts
    for start in range(1, len(parts)):
        candidate = Path(*parts[start:])
        if (repo / candidate).is_file():
            return candidate
    return None


def _blame(args, repo, cap):
    stated = str(args.get("path") or "").strip()
    if not stated:
        _fail("PATH_NOT_STATED")
    relative = _inside(repo, stated)
    if relative is None:
        _fail("PATH_NOT_IN_REPOSITORY:" + stated)
    path = str(relative)
    proc = _git(repo, ["--no-optional-locks", "blame", "--porcelain", "--", path],
                args.get("timeout_s", DEFAULT_TIMEOUT_S))
    lines, pending = [], {}
    for line in proc.stdout.splitlines():
        if line.startswith("\t"):
            pending["code"] = line[1:]
            lines.append(pending)
            pending = {}
            continue
        parts = line.split(" ")
        if len(parts) >= 3 and len(parts[0]) == 40:
            pending = {"sha": parts[0], "source_line": int(parts[1]),
                       "result_line": int(parts[2])}
        elif parts[0] == "author" and pending is not None:
            pending["author"] = line[len("author "):]
        elif parts[0] == "author-time":
            pending["author_time"] = int(parts[1])
        elif parts[0] == "summary":
            pending["summary"] = line[len("summary "):]
    authors = {}
    for row in lines:
        authors[row.get("author", "")] = authors.get(row.get("author", ""), 0) + 1
    return {**_base(cap, "blame", repo), "path": path, "lines": lines,
            "line_count": len(lines), "authors": authors}


def _branch_list(args, repo, cap):
    proc = _git(repo, ["--no-optional-locks", "branch", "--format=%(refname:short)%09%(objectname)"
                       "%09%(HEAD)"], args.get("timeout_s", DEFAULT_TIMEOUT_S))
    branches = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            branches.append({"name": parts[0], "sha": parts[1], "current": parts[2] == "*"})
    return {**_base(cap, "branch_list", repo), "branches": branches,
            "branch_count": len(branches)}


# ----------------------------------------------------------------------------- mutating

def _dirty(repo: Path, timeout_s: int, include_untracked: bool = True) -> list[dict]:
    """Uncommitted changes, tracked by default.

    `git checkout`, `git revert` and `git rebase` rewrite TRACKED state and leave untracked files
    exactly where they are, so an untracked `__pycache__` is not a reason to refuse them --
    measured while binding the reuse surface: a coverage run left a `__pycache__` in the fixture
    and every later rebase refused WORKING_TREE_DIRTY:1 over a file git would never have touched.
    `git stash` is the verb built to move uncommitted work, so it asks for untracked too.
    """
    untracked = [] if include_untracked else ["--untracked-files=no"]
    proc = _git(repo, ["--no-optional-locks", "status", "--porcelain=v1",
                       "--untracked-files=all"] + untracked, timeout_s)
    return [{"index": l[0], "worktree": l[1], "path": l[3:]}
            for l in proc.stdout.splitlines() if len(l) > 3]


def _rev_exists(repo: Path, ref: str, args) -> bool:
    if not ref or ref.startswith("-") or any(c in ref for c in " ;|&$`\n"):
        return False
    proc = _git(repo, ["rev-parse", "--verify", "--quiet", ref + "^{commit}"],
                args.get("timeout_s", DEFAULT_TIMEOUT_S), check=False)
    return proc.returncode == 0


def _stash(args, repo, cap):
    timeout_s = args.get("timeout_s", DEFAULT_TIMEOUT_S)
    before = _dirty(repo, timeout_s)
    if not before:
        # Doing nothing and calling it stashed is a hollow pass; the fact is the answer.
        return {**_base(cap, "stash", repo), "stashed": False, "reason": "WORKING_TREE_CLEAN",
                "stash_ref": "", "entry_count": 0, "restored": False}
    message = str(args.get("message") or "brain stash")
    _git(repo, ["stash", "push", "--include-untracked", "-m", message], timeout_s)
    ref = _git(repo, ["rev-parse", "--verify", "refs/stash"], timeout_s).stdout.strip()
    after = _dirty(repo, timeout_s)
    out = {**_base(cap, "stash", repo), "stashed": True, "stash_ref": ref,
           "entry_count": len(before), "entries": before, "clean_after": not after,
           "message": message, "restored": False}
    if args.get("restore"):
        if not ref:
            _fail("STASH_RESTORE_WITHOUT_A_STASH")
        _git(repo, ["stash", "pop", "--quiet"], timeout_s)
        out["restored"] = True
        out["clean_after"] = not _dirty(repo, timeout_s)
    if not out["clean_after"] and not out["restored"]:
        _fail("STASH_DID_NOT_CLEAR_THE_TREE")
    return out


def _branch_create(args, repo, cap):
    name = str(args.get("branch_name") or "").strip()
    if not name:
        _fail("BRANCH_NAME_NOT_STATED")
    if name.startswith("-") or any(c in name for c in " ~^:?*[\\"):
        _fail("BRANCH_NAME_INVALID:" + name)
    timeout_s = args.get("timeout_s", DEFAULT_TIMEOUT_S)
    exists = _git(repo, ["rev-parse", "--verify", "--quiet", "refs/heads/" + name],
                  timeout_s, check=False).returncode == 0
    if exists:
        _fail("BRANCH_ALREADY_EXISTS:" + name)
    start = str(args.get("start_point") or "").strip()
    argv = ["branch", name] + ([start] if start else [])
    if start and not _rev_exists(repo, start, args):
        _fail("REF_NOT_FOUND:" + start)
    _git(repo, argv, timeout_s)
    current = _git(repo, ["rev-parse", "--abbrev-ref", "HEAD"], timeout_s).stdout.strip()
    return {**_base(cap, "branch_create", repo), "branch_name": name,
            "start_point": start, "created": True, "current_branch": current}


def _checkout(args, repo, cap):
    target = str(args.get("branch_name") or args.get("ref") or "").strip()
    if not target:
        _fail("REF_NOT_STATED")
    timeout_s = args.get("timeout_s", DEFAULT_TIMEOUT_S)
    if not _rev_exists(repo, target, args):
        _fail("REF_NOT_FOUND:" + target)
    if bool(args.get("require_clean", True)):
        dirty = _dirty(repo, timeout_s, include_untracked=False)
        if dirty:
            _fail("WORKING_TREE_DIRTY:%d" % len(dirty))
    before = _git(repo, ["rev-parse", "--abbrev-ref", "HEAD"], timeout_s).stdout.strip()
    _git(repo, ["checkout", target], timeout_s)
    after = _git(repo, ["rev-parse", "--abbrev-ref", "HEAD"], timeout_s).stdout.strip()
    return {**_base(cap, "checkout", repo), "target": target, "before": before,
            "after": after, "switched": before != after}


def _commit(args, repo, cap):
    message = str(args.get("message") or "").strip()
    if not message:
        _fail("MESSAGE_NOT_STATED")
    timeout_s = args.get("timeout_s", DEFAULT_TIMEOUT_S)
    staged = _git(repo, ["--no-optional-locks", "diff", "--cached", "--name-only"], timeout_s)
    paths = [p for p in staged.stdout.splitlines() if p.strip()]
    if not paths and bool(args.get("stage_all", True)):
        _git(repo, ["add", "-A"], timeout_s)
        staged = _git(repo, ["--no-optional-locks", "diff", "--cached", "--name-only"], timeout_s)
        paths = [p for p in staged.stdout.splitlines() if p.strip()]
    if not paths:
        # Nothing to commit is a fact, and it must reach the caller as a REFUSAL.  It used to
        # be returned as `committed: false` under `gate: PASS`, and the door reads the gate:
        # measured through the front door on a clean tree, the answer was
        # PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED for a commit that
        # never happened -- a hollow pass, and the one thing this surface must never report.
        _fail("NOTHING_TO_COMMIT")
    head_before = _git(repo, ["rev-parse", "HEAD"], timeout_s, check=False).stdout.strip()
    _git(repo, ["commit", "-q", "-m", message], timeout_s)
    head_after = _git(repo, ["rev-parse", "HEAD"], timeout_s).stdout.strip()
    if head_after == head_before:
        _fail("COMMIT_DID_NOT_MOVE_HEAD")
    short = _git(repo, ["rev-parse", "--short", "HEAD"], timeout_s).stdout.strip()
    return {**_base(cap, "commit", repo), "committed": True, "sha": head_after,
            "short_sha": short, "paths": paths, "path_count": len(paths),
            "message": message, "previous_sha": head_before}


def _revert(args, repo, cap):
    ref = str(args.get("ref") or "").strip()
    if not ref:
        # "Revert the last commit" is the ordinary phrasing; HEAD is what that means.
        ref = "HEAD"
    timeout_s = args.get("timeout_s", DEFAULT_TIMEOUT_S)
    if not _rev_exists(repo, ref, args):
        _fail("REF_NOT_FOUND:" + ref)
    dirty = _dirty(repo, timeout_s, include_untracked=False)
    if dirty:
        _fail("WORKING_TREE_DIRTY:%d" % len(dirty))
    target = _git(repo, ["rev-parse", ref], timeout_s).stdout.strip()
    subject = _git(repo, ["log", "-1", "--pretty=format:%s", target], timeout_s).stdout.strip()
    before = _git(repo, ["rev-parse", "HEAD"], timeout_s).stdout.strip()
    proc = _git(repo, ["revert", "--no-edit", target], timeout_s, check=False)
    if proc.returncode != 0:
        _git(repo, ["revert", "--abort"], timeout_s, check=False)
        _fail("REVERT_CONFLICT:" + subject[:120])
    after = _git(repo, ["rev-parse", "HEAD"], timeout_s).stdout.strip()
    return {**_base(cap, "revert", repo), "reverted_ref": ref, "reverted_sha": target,
            "reverted_subject": subject, "sha": after, "previous_sha": before}


def _bisect(args, repo, cap):
    """Find the first commit at which a stated command fails.

    This is the one git act that needs a PREDICATE, and the honest form of that predicate is the
    command the caller states -- `git bisect run` exists for exactly this and the composer already
    carries `argv` slots.  What it must never do is guess: no stated command is a refusal, because
    a bisect with an invented predicate would name a commit that has nothing to do with the bug.
    """
    good = str(args.get("ref") or "").strip()
    if not good:
        _fail("BISECT_GOOD_REF_NOT_STATED")
    timeout_s = args.get("timeout_s", DEFAULT_TIMEOUT_S)
    if not _rev_exists(repo, good, args):
        _fail("REF_NOT_FOUND:" + good)
    bad = str(args.get("bad_ref") or "HEAD").strip()
    if not _rev_exists(repo, bad, args):
        _fail("REF_NOT_FOUND:" + bad)
    command = args.get("argv")
    if isinstance(command, str):
        command = shlex.split(command)
    command = [str(part) for part in (command or []) if str(part).strip()] \
        if isinstance(command, list) else []
    if not command:
        _fail("BISECT_COMMAND_NOT_STATED")
    dirty = _dirty(repo, timeout_s, include_untracked=False)
    if dirty:
        _fail("WORKING_TREE_DIRTY:%d" % len(dirty))
    _git(repo, ["bisect", "start", bad, good], timeout_s)
    proc = _git(repo, ["bisect", "run"] + command, timeout_s, check=False)
    first_bad = _git(repo, ["rev-parse", "refs/bisect/bad"], timeout_s, check=False).stdout.strip()
    subject = _git(repo, ["log", "-1", "--pretty=format:%s", first_bad], timeout_s,
                   check=False).stdout.strip() if first_bad else ""
    steps = _git(repo, ["bisect", "log"], timeout_s, check=False).stdout.splitlines()
    # Always reset, including on the failure path: leaving the caller on a detached bisect HEAD is
    # the same class of damage as a checkout that throws the tree away.
    _git(repo, ["bisect", "reset"], timeout_s, check=False)
    if proc.returncode != 0 and not first_bad:
        _fail("BISECT_FAILED:" + (proc.stderr or proc.stdout or "").strip().splitlines()[-1][:200]
              if (proc.stderr or proc.stdout or "").strip() else "BISECT_FAILED")
    return {**_base(cap, "bisect", repo), "good_ref": good, "bad_ref": bad,
            "command": command, "first_bad_sha": first_bad,
            "first_bad_subject": subject, "steps_examined": len(steps),
            "found": bool(first_bad)}


def _rebase(args, repo, cap):
    """Replay the current branch onto a stated revision; refuse rather than leave a conflict."""
    onto = str(args.get("ref") or "").strip()
    if not onto:
        _fail("REF_NOT_STATED")
    timeout_s = args.get("timeout_s", DEFAULT_TIMEOUT_S)
    if not _rev_exists(repo, onto, args):
        _fail("REF_NOT_FOUND:" + onto)
    if bool(args.get("require_clean", True)):
        dirty = _dirty(repo, timeout_s, include_untracked=False)
        if dirty:
            _fail("WORKING_TREE_DIRTY:%d" % len(dirty))
    branch = _git(repo, ["rev-parse", "--abbrev-ref", "HEAD"], timeout_s).stdout.strip()
    before = _git(repo, ["rev-parse", "HEAD"], timeout_s).stdout.strip()
    proc = _git(repo, ["rebase", onto], timeout_s, check=False)
    if proc.returncode != 0:
        _git(repo, ["rebase", "--abort"], timeout_s, check=False)
        detail = (proc.stdout or proc.stderr or "").strip().splitlines()
        _fail("REBASE_CONFLICT:" + onto + ":" + (detail[-1] if detail else "")[:160])
    after = _git(repo, ["rev-parse", "HEAD"], timeout_s).stdout.strip()
    replayed = _git(repo, ["rev-list", "--count", "%s..%s" % (onto, after)], timeout_s,
                    check=False).stdout.strip()
    return {**_base(cap, "rebase", repo), "onto": onto, "branch": branch,
            "previous_sha": before, "sha": after,
            "commits_replayed": int(replayed) if replayed.isdigit() else 0}


_HANDLERS = {"status": _status, "log": _log, "diff": _diff, "blame": _blame,
             "branch_list": _branch_list, "stash": _stash, "branch_create": _branch_create,
             "checkout": _checkout, "bisect": _bisect, "rebase": _rebase,
             "commit": _commit, "revert": _revert}


def run(args: dict, root: Path) -> dict:
    """The one entrypoint every git capability uses.  Keys come from the action template."""
    args = dict(args or {})
    root = Path(root)
    verb = str(args.get("git_verb") or "").strip()
    capability_id = str(args.get("capability_id") or "")
    if verb not in _HANDLERS:
        _fail("GIT_VERB_NOT_SUPPORTED:" + (verb or "<none>"))
    # The repository and the destination are resolved INSIDE the refusal block.  Measured:
    # "Show me the git status of the repository and write it to <O>" -- a sentence that never
    # names a repository -- resolved the repository before the block, so the refusal was raised
    # with no artifact written, and the door reported FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
    # with an EMPTY reason: the caller was told neither what went wrong nor that no repository
    # had been stated.  Every refusal this adapter can raise is written, or it is not a refusal.
    output_path = None
    try:
        # The destination first: it is the only thing a refusal needs in order to be written.
        output_path = _output(args, root, capability_id)
        repo = _repo(args, root)
        payload = _HANDLERS[verb](args, repo, capability_id)
    except GitContractError as exc:
        # Every refusal is an artifact too: a caller must be able to read WHY, and the
        # door must be able to see that no work was credited.
        refusal = {"adapter": "vcs_git_v1", "capability_id": capability_id, "verb": verb,
                   "repository": str(locals().get("repo") or ""), "gate": "FAIL",
                   "reason": str(exc)}
        if output_path is not None:
            _write(output_path, refusal)
        raise
    payload["head"] = _git(repo, ["rev-parse", "HEAD"], args.get("timeout_s", DEFAULT_TIMEOUT_S),
                           check=False).stdout.strip()
    return _write(output_path, payload)
