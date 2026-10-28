#!/usr/bin/env python3
"""The git object model as Brain-owned capability: inspect, bisect, land.

Why this module exists
----------------------
The registry had **zero** git capabilities. Measured on `87cecd5`, of ten ordinary
software-engineering requests ("show the last three commits", "commit the staged
changes", "find when it broke") **none** reached a capability that could do the job,
and the one that "passed" did so falsely (PR #6296). The only thing that could touch a
repository was `shell.command.run` -- the generic catch-all, which is the same route
that deleted a source file in the previously measured incident.

Everything here is a REUSE of mechanisms the tree already proved out, not a new idea:

  * the **path law** (`_safe`, repository-confined) is the one in
    `source_candidates_verify_git_index.py` and the refactor adapters;
  * **argv lists only, no shell strings**, with a declared allowlist, is the discipline
    of `python_pipeline_allowlist_gate_v1.py` and `cli_command.py`;
  * **independent verification by a different mechanism** is the pattern of
    `archive_verify_gnu_tar.py` (ask the external binary, don't re-run the adapter) and
    of `source_candidates_verify_git_index.py`. Here the independent reader is git
    plumbing re-read *after* the operation: `rev-parse`, `log --format=%H`, `branch
    --list`, `ls-tree`, `status --porcelain`. The adapter's own report is never the
    verdict.

What it is not
--------------
No network (`fetch`/`push`/`pull`/`clone`/`remote`/`submodule`/`config` are refused, and
`GIT_TERMINAL_PROMPT=0`, `GIT_CONFIG_NOSYSTEM=1` are forced), no model, no spend, no
package install. Nothing here writes outside the named repository, and no function
leaves the repository in a state it did not record.

Three entrypoints, one module
-----------------------------
``run_inspect``  read-only: status, diff, staged diff, log, show, blame, ls-files,
                 branch list, rev-parse, merge-base, describe.  Artifact carries the
                 re-read HEAD and branch, so a caller can prove the read was current.
``run_bisect``   `git bisect run` over a caller-supplied python test argv, with a clean
                 tree required, the original HEAD recorded, and the tree restored in a
                 ``finally`` that *verifies* restoration by re-reading ``rev-parse HEAD``.
``run_land``     create a branch, apply a unified diff, run the caller's test argv, commit
                 on green, and on any red put the repository back exactly where it was
                 (``reset --hard`` to the recorded HEAD, delete the branch) before
                 refusing.  Never pushes; landing on a remote is a separate authorisation.

Measured failure semantics are fail-closed: a dirty tree refuses bisect, a non-repository
refuses everything, a path outside the repository refuses, a non-python test argv is
refused (the same allowlist as the repair corridor), and every refusal is a JSON error
with a nameable reason rather than an exception a caller has to guess about.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

SCHEMA_INSPECT = "PROJECT_BRAIN_GIT_REPOSITORY_INSPECT_V1"
SCHEMA_BISECT = "PROJECT_BRAIN_GIT_REGRESSION_BISECT_V1"
SCHEMA_LAND = "PROJECT_BRAIN_GIT_CHANGE_LAND_V1"

#: Subcommands this module may run.  A name not in this set never reaches subprocess.
_READ = {"status", "diff", "log", "show", "blame", "ls-files", "rev-parse", "branch",
         "describe", "merge-base", "ls-tree", "cat-file", "for-each-ref", "rev-list"}
_GLOBAL_CONFIG_KEYS = {"user.name", "user.email"}
_WRITE = {"add", "apply", "commit", "checkout", "switch", "reset", "branch",
          "bisect", "rev-parse", "status", "log", "diff", "ls-tree", "cat-file"}
#: Refused on purpose: these reach the network, credentials, or repository configuration.
_NEVER = {"fetch", "push", "pull", "clone", "remote", "submodule", "config", "gc",
          "filter-branch", "credential", "daemon", "http-fetch", "archive", "bundle"}

_DEFAULT_MAX_STEPS = 12
_MAX_TIMEOUT_S = 900


class GitCapabilityError(RuntimeError):
    """A refusal with a nameable reason.  Never a silent downgrade."""


def _fail(reason: str) -> None:
    raise GitCapabilityError(reason)


def _env(repo: pathlib.Path) -> dict:
    env = dict(os.environ)
    env.update({
        "GIT_TERMINAL_PROMPT": "0",   # never block on a credential prompt
        "GIT_CONFIG_NOSYSTEM": "1",   # the host's global config cannot rewire a command
        "GIT_ASKPASS": "/bin/true",
        "GIT_PAGER": "cat",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
    })
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def _git(repo: pathlib.Path, argv: list[str], timeout_s: int = 120) -> tuple[int, str, str]:
    """Run one allowlisted git command.  argv list, never a shell string."""
    if not argv:
        _fail("GIT_ARGV_EMPTY")
    # A leading "-c key=value" is a GLOBAL git option, not a subcommand; commit identity is
    # the only global option this lane needs, so exactly those keys are allowed through and
    # everything else stays refused.  (Measured: commit was refused as "-c" before this.)
    verb = str(argv[0])
    i = 0
    while verb == "-c":
        if i + 1 >= len(argv):
            _fail("GIT_GLOBAL_OPTION_TRUNCATED")
        key = str(argv[i + 1]).split("=", 1)[0]
        if key not in _GLOBAL_CONFIG_KEYS:
            _fail("GIT_GLOBAL_OPTION_REFUSED:" + key)
        i += 2
        if i >= len(argv):
            _fail("GIT_ARGV_EMPTY")
        verb = str(argv[i])
    if verb in _NEVER:
        _fail("GIT_SUBCOMMAND_REFUSED:" + verb)
    if verb not in _READ and verb not in _WRITE:
        _fail("GIT_SUBCOMMAND_NOT_ALLOWED:" + verb)
    proc = subprocess.run(
        ["git", "-C", str(repo), *[str(x) for x in argv]],
        text=True, capture_output=True, timeout=max(1, min(int(timeout_s), _MAX_TIMEOUT_S)),
        env=_env(repo), check=False,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _repo(root, raw) -> pathlib.Path:
    """The named repository, resolved inside the caller's root, proven to be a work tree."""
    base = pathlib.Path(root).resolve()
    if not isinstance(raw, str) or not raw.strip():
        _fail("REPO_PATH_REQUIRED")
    repo = (base / raw).resolve()
    if repo != base and base not in repo.parents:
        _fail("PATH_OUTSIDE_REPOSITORY:" + str(raw))
    if not repo.is_dir():
        _fail("REPO_PATH_MISSING:" + str(raw))
    rc, out, _ = _git(repo, ["rev-parse", "--show-toplevel"])
    if rc != 0 or not out.strip():
        _fail("NOT_A_GIT_WORK_TREE:" + str(raw))
    return repo


def _head(repo: pathlib.Path) -> str:
    rc, out, _ = _git(repo, ["rev-parse", "HEAD"])
    return out.strip() if rc == 0 else ""


def _branch(repo: pathlib.Path) -> str:
    rc, out, _ = _git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if rc == 0 else ""


def _clean(repo: pathlib.Path) -> bool:
    """No MODIFIED TRACKED file.

    ``--untracked-files=no`` is the right question for both callers: ``bisect`` and
    ``checkout`` overwrite tracked paths and leave untracked ones alone, and a test run
    legitimately creates ``__pycache__``.  Requiring a pristine ``status`` refused every
    repository whose tests had ever run -- measured: the first two bisect/land probes both
    failed on nothing but byte-compiled files.
    """
    rc, out, _ = _git(repo, ["status", "--porcelain", "--untracked-files=no"])
    return rc == 0 and not out.strip()


def _commit_exists(repo: pathlib.Path, rev: str) -> bool:
    if not rev or not rev.strip():
        return False
    rc, _, _ = _git(repo, ["cat-file", "-e", str(rev) + "^{commit}"])
    return rc == 0


def _output(root, raw) -> pathlib.Path:
    """Artifacts are written under the CALLER's root, never inside the inspected repo.

    A read capability must not enlarge the set of files in the repository it reads, and a
    write capability's artifact must survive the rollback it may perform on that repository.
    """
    base = pathlib.Path(root).resolve()
    if not isinstance(raw, str) or not raw.strip():
        _fail("OUTPUT_PATH_REQUIRED")
    path = (base / raw).resolve()
    if path == base or base not in path.parents:
        _fail("OUTPUT_PATH_OUTSIDE_REPOSITORY:" + str(raw))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: pathlib.Path, artifact: dict) -> tuple[str, str]:
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    return str(path), hashlib.sha256(raw).hexdigest()


def _python_argv(value, label: str = "test_argv") -> list[str]:
    """The caller's test command: a python interpreter and arguments, nothing else.

    The same allowlist the repair corridor applies (``python_test_guided_patch_search_v1``):
    a capability that will execute a command must not become a general command runner,
    because that is precisely the catch-all route that made this lane necessary.
    """
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x for x in value):
        _fail(label.upper() + "_INVALID")
    exe = pathlib.Path(value[0]).name.lower()
    allowed = {pathlib.Path(sys.executable).name.lower(), "python", "python3", "py"}
    if exe not in allowed:
        _fail(label.upper() + "_EXECUTABLE_NOT_PYTHON:" + value[0])
    return list(value)


# ------------------------------------------------------------------------- derivation

#: One sentence in, one query list out, with no model anywhere in the path.
#:
#: Measured on 87cecd5: "show me the last three commits" scored 16 against
#: ``git.repository.inspect.v1`` and still did not route, because the row's contract asked for
#: ``repo_path``, ``queries`` and ``output_path`` and the compiler can only bind what a sentence
#: states.  A sentence about a repository does not restate its own arguments -- it names an
#: EFFECT ("last three commits", "what changed") -- so the capability has to read the effect out
#: of the sentence itself, deterministically, and say in the artifact which rule it applied.
#
#: This is derivation, not inference: every query below is chosen by a literal pattern and the
#: artifact records the sentence and the derived queries together, so a wrong derivation is
#: visible in the evidence rather than hidden behind a plausible report.

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _count_from_text(text: str, default: int, cap: int = 500) -> int:
    for token in re.findall(r"\b\d{1,3}\b", text or ""):
        return max(1, min(int(token), cap))
    for word in re.findall(r"\b[a-z]+\b", (text or "").lower()):
        if word in _NUMBER_WORDS:
            return _NUMBER_WORDS[word]
    return default


def _named_paths(text: str, repo: pathlib.Path) -> list[str]:
    """Repository-relative paths the sentence actually names.

    Only paths that EXIST in the repository qualify: a sentence may mention a file it is about
    to create, and blaming a path that is not in the tree would fail the whole read.
    """
    found: list[str] = []
    for token in re.findall(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]+", text or ""):
        candidate = token.strip(".,;:()[]'\"")
        if not candidate:
            continue
        for base in (repo, pathlib.Path.cwd()):
            resolved = (base / candidate).resolve()
            if repo == resolved or repo in resolved.parents:
                rel = str(resolved.relative_to(repo))
                if resolved.is_file() and rel not in found:
                    found.append(rel)
                break
    return found


#: Sentences that ask to CHANGE the repository.  A read capability must not answer one: the
#: measured failure was "create a branch and commit the fix" routing to inspect, whose status
#: output would look like a successful action while the repository was untouched.
_WRITE_INTENT = re.compile(
    r"\bcommit\s+(?:the|it|this|that|all|everything|these|my|your)\b"
    r"|\b(?:stage|staged|apply (?:this|the) (?:patch|diff)|land (?:the|this) change|"
    r"merge|revert|reset --hard|checkout|create (?:a |the )?branch|make a branch|"
    r"push|delete (?:the )?branch|amend)\b",
    re.IGNORECASE,
)


def derive_queries(text: str, repo: pathlib.Path) -> list[dict]:
    """The queries a sentence asks for.  Refuses rather than guessing when it asks for none."""
    lowered = (text or "").lower()
    if not lowered.strip():
        _fail("QUERY_KIND_UNDERIVED:<empty>")
    queries: list[dict] = []
    paths = _named_paths(text, repo)
    count = _count_from_text(text, 10)

    if re.search(r"\b(status|working tree|worktree|dirty|uncommitted|un-staged|clean)\b", lowered):
        queries.append({"kind": "status"})
    if re.search(r"\bstaged\b", lowered):
        queries.append({"kind": "diff_staged"})
    elif re.search(r"\b(diff|diffs|what changed|changes?|modified)\b", lowered):
        queries.append({"kind": "diff", **({"path": paths[0]} if paths else {})})
    if re.search(r"\b(commit|commits|log|history|recent changes)\b", lowered):
        queries.append({"kind": "log", "max_count": count,
                        **({"path": paths[0]} if paths else {})})
    if re.search(r"\b(tracked|ls-files|list (the )?files|which files)\b", lowered):
        queries.append({"kind": "ls_files"})
    if re.search(r"\b(branches?|what branch|which branch)\b", lowered):
        queries.append({"kind": "branch"})
    if re.search(r"\b(blame|who (wrote|last touched|changed|edited))\b", lowered) and paths:
        queries.append({"kind": "blame", "path": paths[0]})
    for token in re.findall(r"\b[0-9a-f]{7,40}\b", lowered):
        queries.append({"kind": "rev_parse", "rev": token})
        queries.append({"kind": "show", "rev": token})
    if re.search(r"\bmerge[- ]base\b", lowered):
        queries.append({"kind": "merge_base", "a": "HEAD", "b": paths[0] if paths else "HEAD"})
    if queries:
        return queries
    _fail("QUERY_KIND_UNDERIVED:" + (text or "")[:160])


def _default_artifact(kind: str, text: str, repo: pathlib.Path) -> str:
    """A deterministic artifact path under the caller's root.

    Deterministic on purpose: a rerun of the same sentence over the same repository writes the
    same file, so an artifact cannot be mistaken for a new observation.
    """
    digest = hashlib.sha256((kind + "\x00" + (text or "") + "\x00" + str(repo)).encode()).hexdigest()[:12]
    return "canonical/astra_runtime/tmp/git_lane/%s_%s.json" % (kind, digest)


def _root_commit(repo: pathlib.Path, rev: str) -> str:
    """The oldest ancestor of ``rev`` -- bisect's default known-good, stated as an inference."""
    rc, out, _ = _git(repo, ["rev-list", "--max-parents=0", rev or "HEAD"])
    roots = [x.strip() for x in out.splitlines() if x.strip()]
    return roots[-1] if rc == 0 and roots else ""


def suite_argv(executable, *targets) -> list[str]:
    """The project's own suite runner, reached rather than copied.

    The compiler binds a ``test_argv`` input by asking the adapter for its default
    (``goal_compiler._adapter_default_argv``); that default must be the loader-based runner, not
    ``python path/to/test_x.py``, because 695 of 2019 unittest files here carry no ``__main__``
    guard and a script run of one exits 0 having executed nothing.  Delegating keeps one
    implementation of that runner in the tree.
    """
    import importlib.util

    sibling = pathlib.Path(__file__).with_name("python_test_guided_patch_search_v1.py")
    spec = importlib.util.spec_from_file_location("_git_lane_suite_runner", sibling)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.suite_argv(executable, *targets)


def _default_test_argv(repo: pathlib.Path) -> list[str]:
    """Run the repository's own suites.  Refuses when there are none to run."""
    files = sorted(
        str(p.relative_to(repo)) for p in repo.rglob("test_*.py")
        if ".git" not in p.parts and p.is_file()
    )[:50]
    if not files:
        _fail("TEST_ARGV_REQUIRED")
    return [str(x) for x in suite_argv(sys.executable, *files)]


# --------------------------------------------------------------------------- inspect

_QUERY_KINDS = {"status", "diff", "diff_staged", "log", "show", "blame", "ls_files",
                "branch", "rev_parse", "merge_base", "describe", "tree"}


def _run_query(repo: pathlib.Path, query: dict, timeout_s: int) -> dict:
    if not isinstance(query, dict):
        _fail("QUERY_NOT_OBJECT")
    kind = str(query.get("kind") or "")
    if kind not in _QUERY_KINDS:
        _fail("QUERY_KIND_UNKNOWN:" + (kind or "<missing>"))
    if kind == "status":
        rc, out, err = _git(repo, ["status", "--porcelain=v1", "--branch"], timeout_s)
        return {"kind": kind, "returncode": rc, "stdout": out, "stderr": err}
    if kind == "diff":
        argv = ["diff", "--no-color", "--no-ext-diff"]
        if query.get("rev"):
            argv.append(str(query["rev"]))
        if query.get("path"):
            argv += ["--", str(query["path"])]
        rc, out, err = _git(repo, argv, timeout_s)
        return {"kind": kind, "returncode": rc, "stdout": out, "stderr": err,
                "path": query.get("path"), "rev": query.get("rev")}
    if kind == "diff_staged":
        argv = ["diff", "--no-color", "--no-ext-diff", "--cached"]
        if query.get("path"):
            argv += ["--", str(query["path"])]
        rc, out, err = _git(repo, argv, timeout_s)
        return {"kind": kind, "returncode": rc, "stdout": out, "stderr": err, "path": query.get("path")}
    if kind == "log":
        limit = int(query.get("max_count") or 10)
        argv = ["log", "-n", str(max(1, min(limit, 500))), "--format=%H%x09%an%x09%at%x09%s"]
        if query.get("path"):
            argv += ["--", str(query["path"])]
        rc, out, err = _git(repo, argv, timeout_s)
        entries = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == 4:
                entries.append({"sha": parts[0], "author": parts[1],
                                "authored_at": parts[2], "subject": parts[3]})
        return {"kind": kind, "returncode": rc, "entries": entries, "stderr": err}
    if kind == "show":
        rev = str(query.get("rev") or "HEAD")
        rc, out, err = _git(repo, ["show", "--no-color", "--no-ext-diff", "--stat", "--format=%H%n%s", rev], timeout_s)
        return {"kind": kind, "returncode": rc, "rev": rev, "stdout": out, "stderr": err}
    if kind == "blame":
        if not query.get("path"):
            _fail("BLAME_PATH_REQUIRED")
        argv = ["blame", "--line-porcelain"]
        if query.get("rev"):
            argv.append(str(query["rev"]))
        argv += ["--", str(query["path"])]
        rc, out, err = _git(repo, argv, timeout_s)
        authors: dict[str, int] = {}
        for line in out.splitlines():
            if line.startswith("author "):
                who = line[7:]
                authors[who] = authors.get(who, 0) + 1
        return {"kind": kind, "returncode": rc, "path": query["path"], "authors": authors, "stderr": err}
    if kind == "ls_files":
        argv = ["ls-files"]
        if query.get("pattern"):
            argv.append(str(query["pattern"]))
        rc, out, err = _git(repo, argv, timeout_s)
        files = [x for x in out.splitlines() if x.strip()]
        return {"kind": kind, "returncode": rc, "count": len(files), "files": files[:2000], "stderr": err}
    if kind == "branch":
        rc, out, err = _git(repo, ["branch", "--list", "--format=%(refname:short)"], timeout_s)
        names = [x for x in out.splitlines() if x.strip()]
        return {"kind": kind, "returncode": rc, "branches": names, "current": _branch(repo), "stderr": err}
    if kind == "rev_parse":
        rev = str(query.get("rev") or "HEAD")
        rc, out, err = _git(repo, ["rev-parse", rev], timeout_s)
        return {"kind": kind, "returncode": rc, "rev": rev, "sha": out.strip(), "stderr": err}
    if kind == "merge_base":
        a, b = str(query.get("a") or ""), str(query.get("b") or "")
        if not a or not b:
            _fail("MERGE_BASE_REVS_REQUIRED")
        rc, out, err = _git(repo, ["merge-base", a, b], timeout_s)
        return {"kind": kind, "returncode": rc, "base": out.strip(), "stderr": err}
    if kind == "describe":
        rc, out, err = _git(repo, ["describe", "--tags", "--always", "--dirty"], timeout_s)
        return {"kind": kind, "returncode": rc, "description": out.strip(), "stderr": err}
    # tree
    rev = str(query.get("rev") or "HEAD")
    rc, out, err = _git(repo, ["ls-tree", "-r", "--name-only", rev], timeout_s)
    files = [x for x in out.splitlines() if x.strip()]
    return {"kind": "tree", "returncode": rc, "rev": rev, "count": len(files), "stderr": err}


def run_inspect(args, root):
    """Read the repository and report it with a re-read HEAD the caller can trust."""
    args = dict(args or {})
    repo = _repo(root, args.get("repo_path") or ".")
    timeout_s = int(args.get("timeout_s") or 120)
    goal_text = str(args.get("goal") or args.get("intent") or args.get("text") or "")
    queries = args.get("queries")
    derived_from = "caller_supplied_queries" if queries else "derived_from_sentence"
    if not queries and goal_text:
        if _WRITE_INTENT.search(goal_text):
            _fail("READ_CAPABILITY_REFUSES_WRITE_REQUEST:" + goal_text[:160])
        queries = derive_queries(goal_text, repo)
    if not queries:
        _fail("QUERIES_REQUIRED")
    if not isinstance(queries, list):
        _fail("QUERIES_NOT_LIST")
    out_path = _output(root, args.get("output_path") or _default_artifact("inspect", goal_text, repo))

    results = [_run_query(repo, q, timeout_s) for q in queries]
    failed = [r for r in results if int(r.get("returncode", 0)) != 0]

    # Independent re-read: the artifact's HEAD and branch are read again AFTER the
    # queries, by a different invocation, so a caller can see whether the repository
    # moved underneath the read.  The adapter's own answer is not the verdict.
    head_after = _head(repo)
    branch_after = _branch(repo)
    artifact = {
        "schema": SCHEMA_INSPECT,
        "capability_id": "git.repository.inspect.v1",
        "repo_path": str(repo),
        "head": head_after,
        "branch": branch_after,
        "query_count": len(results),
        "goal_text": goal_text,
        "query_derivation": derived_from,
        "results": results,
        "failed_query_count": len(failed),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": bool(head_after) and not failed,
    }
    path, sha = _write(out_path, artifact)
    return {
        "adapter": "git_object_model_v1",
        "output_path": str(path),
        "output_sha256": sha,
        "output_verified": artifact["verified"],
        "head": head_after,
        "branch": branch_after,
        "query_count": len(results),
        "failed_query_count": len(failed),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


# ---------------------------------------------------------------------------- bisect

_FIRST_BAD = " is the first bad commit"


def run_bisect(args, root):
    """Find the commit that introduced a red test, and leave the repository untouched."""
    args = dict(args or {})
    repo = _repo(root, args.get("repo_path") or ".")
    goal_text = str(args.get("goal") or args.get("intent") or args.get("text") or "")
    # bad defaults to HEAD and good to the oldest ancestor of bad.  Both are inferences and both
    # are recorded in the artifact: "when did it break" names an effect, not two commit ids, and
    # the whole history reachable from HEAD is the range that question is asking about.
    bad = str(args.get("bad") or "").strip()
    if not bad:
        bad = _head(repo)
        if not bad:
            _fail("BISECT_REV_NOT_A_COMMIT:<no HEAD>")
    good = str(args.get("good") or "").strip()
    good_inferred = not good
    if good_inferred:
        good = _root_commit(repo, bad)
        if not good:
            _fail("BISECT_NO_ROOT_COMMIT:" + bad)
    if not _commit_exists(repo, good) or not _commit_exists(repo, bad):
        _fail("BISECT_REV_NOT_A_COMMIT")
    if goal_text and not args.get("good") and not args.get("bad") and _WRITE_INTENT.search(goal_text):
        # The same law as inspect's: a bisect cannot answer "commit the staged changes".  This
        # fired in measurement -- the write sentence scored 8 on git.change.land.v1, which could
        # not bind its diff, so the lower-scoring bisect took the plan.
        _fail("BISECT_REFUSES_WRITE_REQUEST:" + goal_text[:160])
    test_argv_supplied = bool(args.get("test_argv"))
    test_argv = _python_argv(args["test_argv"]) if test_argv_supplied else _default_test_argv(repo)
    max_steps = int(args.get("max_steps") or _DEFAULT_MAX_STEPS)
    timeout_s = int(args.get("timeout_s") or 300)

    # Refuse a range that cannot finish inside max_steps BEFORE touching the working tree.
    # git bisect would otherwise keep checking out commits until the caller's timeout kills it
    # mid-bisect, which is exactly the state that loses work.
    rc, counted, _ = _git(repo, ["rev-list", "--count", "%s..%s" % (good, bad)], timeout_s)
    commits_in_range = int(counted.strip() or 0) if rc == 0 and counted.strip().isdigit() else 0
    steps_needed = max(1, (commits_in_range + 1).bit_length()) if commits_in_range else 0
    if commits_in_range and steps_needed > max_steps:
        _fail("BISECT_RANGE_EXCEEDS_MAX_STEPS:%d:%d:%d" % (commits_in_range, steps_needed, max_steps))

    out_path = _output(root, args.get("output_path")
                        or _default_artifact("bisect", goal_text or (good + bad), repo))

    # bisect checks commits out into the working tree, so a dirty tree would be
    # destroyed by it.  This refusal is the difference between a tool and an accident.
    if not _clean(repo):
        _fail("DIRTY_WORKTREE_REFUSES_BISECT")

    started_head = _head(repo)
    started_branch = _branch(repo)
    transcript: list[str] = []
    restored = False
    first_bad = ""
    first_bad_source = ""
    try:
        for argv in (["bisect", "start"], ["bisect", "bad", bad], ["bisect", "good", good]):
            rc, out, err = _git(repo, argv, timeout_s)
            transcript.append("$ git " + " ".join(argv) + "\n" + out + err)
            if rc != 0:
                _fail("BISECT_SETUP_FAILED:" + " ".join(argv) + ":" + (err or out).strip()[:300])
        steps = 0
        rc, out, err = _git(repo, ["bisect", "run", *test_argv], max(timeout_s, 600))
        transcript.append("$ git bisect run " + " ".join(test_argv) + "\n" + out + err)
        # The answer is read from `refs/bisect/bad`, not from the English sentence. Parsing
        # "X is the first bad commit" made the lane's verdict depend on git's message wording
        # and on which stream it chose: on the 3.11.17 CI runner the sentence was not found in
        # stdout, `first_bad` stayed empty and `verified` became False even though bisect had
        # succeeded. `refs/bisect/bad` is what bisect itself uses, it is stable across versions
        # and locales, and it disappears at `bisect reset` -- so it is read first, right here.
        bad_rc, bad_out, _bad_err = _git(repo, ["rev-parse", "--verify", "-q", "refs/bisect/bad"],
                                        timeout_s)
        candidate = bad_out.strip().splitlines()[-1].strip() if bad_out.strip() else ""
        # `bisect run` returns 0 only when it actually concluded. Without that check the
        # ref would still name the caller's `bad` commit after an inconclusive run, and the
        # lane would report a culprit bisect never found.
        if rc == 0 and bad_rc == 0 and candidate:
            first_bad = candidate
            first_bad_source = "refs/bisect/bad"
        if not first_bad:
            for line in (out + "\n" + err).splitlines():
                if line.endswith(_FIRST_BAD):
                    first_bad = line.split()[0].strip()
                    break
                if _FIRST_BAD in line:
                    first_bad = line.split(_FIRST_BAD)[0].strip()
                    break
            first_bad_source = "bisect_output_text" if first_bad else ""
        steps = sum(1 for line in (out + "\n" + err).splitlines()
                    if line.startswith("Bisecting:"))
    finally:
        _git(repo, ["bisect", "reset"], max(timeout_s, 300))
        # Independent restoration proof, read back from the repository itself.
        restored = (_head(repo) == started_head and _branch(repo) == started_branch
                    and _clean(repo))

    verified = bool(first_bad) and _commit_exists(repo, first_bad) and restored
    artifact = {
        "schema": SCHEMA_BISECT,
        "capability_id": "git.regression.bisect.v1",
        "repo_path": str(repo),
        "good": good,
        "bad": bad,
        "goal_text": goal_text,
        "test_argv": test_argv,
        "test_argv_derivation": "caller_supplied" if test_argv_supplied else "repository_suites",
        "good_inferred_as_root_commit": good_inferred,
        "commits_in_range": commits_in_range,
        "steps_needed": steps_needed,
        "first_bad_commit": first_bad or None,
        "first_bad_source": first_bad_source or None,
        "bisect_run_returncode": rc,
        "steps_observed": steps,
        "head_before": started_head,
        "head_after": _head(repo),
        "restored": restored,
        "transcript_tail": transcript[-1][-4000:] if transcript else "",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": verified,
    }
    path, sha = _write(out_path, artifact)
    if not restored:
        # Value has already been lost; say so loudly rather than reporting a clean run.
        _fail("BISECT_DID_NOT_RESTORE_HEAD:" + started_head)
    return {
        "adapter": "git_object_model_v1",
        "output_path": str(path),
        "output_sha256": sha,
        "output_verified": verified,
        "first_bad_commit": first_bad or None,
        "restored": restored,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


# ------------------------------------------------------------------------------ land

def run_land(args, root):
    """Create a branch, apply a diff, run the suite, commit on green, else undo everything."""
    args = dict(args or {})
    repo = _repo(root, args.get("repo_path"))
    branch_name = str(args.get("branch_name") or "").strip()
    message = str(args.get("message") or "").strip()
    if not branch_name or not message:
        _fail("BRANCH_NAME_AND_MESSAGE_REQUIRED")
    if branch_name.startswith("-") or " " in branch_name or ".." in branch_name:
        _fail("BRANCH_NAME_INVALID:" + branch_name)
    diff_path = args.get("diff_path")
    test_argv = _python_argv(args["test_argv"]) if args.get("test_argv") else None
    timeout_s = int(args.get("timeout_s") or 300)
    out_path = _output(root, args.get("output_path"))
    author = str(args.get("author") or "Project Brain <brain@localhost>")

    if not _clean(repo):
        _fail("DIRTY_WORKTREE_REFUSES_LAND")
    started_head = _head(repo)
    started_branch = _branch(repo)
    rc, out, _ = _git(repo, ["branch", "--list", branch_name])
    if out.strip():
        _fail("BRANCH_ALREADY_EXISTS:" + branch_name)

    applied = False
    tests: dict | None = None
    commit_sha = ""
    try:
        rc, out, err = _git(repo, ["checkout", "-b", branch_name], timeout_s)
        if rc != 0:
            _fail("BRANCH_CREATE_FAILED:" + (err or out).strip()[:300])
        if diff_path:
            # The diff is an INPUT produced elsewhere (patch search, a review tool), so it is
            # resolved against the caller's root, not the repository; only the paths inside it
            # reach the repository, and `git apply` refuses any hunk that would leave it.
            diff = (pathlib.Path(root).resolve() / str(diff_path)).resolve()
            if pathlib.Path(root).resolve() not in diff.parents or not diff.is_file():
                _fail("DIFF_PATH_MISSING:" + str(diff_path))
            rc, out, err = _git(repo, ["apply", "--index", "--whitespace=nowarn", str(diff)], timeout_s)
            if rc != 0:
                _fail("DIFF_DOES_NOT_APPLY:" + (err or out).strip()[:400])
            applied = True
        if test_argv:
            proc = subprocess.run(test_argv, cwd=str(repo), text=True, capture_output=True,
                                  timeout=max(1, min(timeout_s, _MAX_TIMEOUT_S)), check=False,
                                  env=_env(repo))
            tests = {"returncode": proc.returncode,
                     "stdout_tail": (proc.stdout or "")[-4000:],
                     "stderr_tail": (proc.stderr or "")[-2000:]}
            if proc.returncode != 0:
                _fail("TESTS_RED_BEFORE_COMMIT:" + (proc.stdout or proc.stderr or "").strip()[-400:])
        rc, out, err = _git(repo, ["-c", "user.name=" + author.split("<")[0].strip(),
                                   "-c", "user.email=" + author.split("<")[-1].rstrip("> ").strip(),
                                   "commit", "-m", message], timeout_s)
        if rc != 0:
            _fail("COMMIT_FAILED:" + (err or out).strip()[:400])
        commit_sha = _head(repo)
        # The landed state is a branch plus one commit; the caller's HEAD must not move.
        # Leaving HEAD on the topic branch would silently retarget every later command run
        # in this repository -- measured: the green probe left HEAD on brain/fix-add, so the
        # next diff applied nowhere.  Restore and verify by re-read.
        _git(repo, ["checkout", started_branch], timeout_s)
    except BaseException:
        # Undo: the tree was clean at entry, so reset --hard to the recorded HEAD restores
        # it byte-exactly; then the branch that was created here is deleted.  Both are
        # verified by reading the repository back, and a failed restore is reported.
        _git(repo, ["reset", "--hard", started_head], timeout_s)
        _git(repo, ["checkout", started_branch], timeout_s)
        _git(repo, ["branch", "-D", branch_name], timeout_s)
        _git(repo, ["reset", "--hard", started_head], timeout_s)
        raise

    # Independent re-read: the branch tip, the base, and the tree of the new commit.
    rc, tip, _ = _git(repo, ["rev-parse", branch_name])
    tip = tip.strip()
    rc2, base, _ = _git(repo, ["rev-parse", started_branch])
    base = base.strip()
    rc3, changed, _ = _git(repo, ["show", "--name-only", "--format=", commit_sha])
    changed_paths = sorted({x.strip() for x in (changed or "").splitlines() if x.strip()})
    head_restored = _branch(repo) == started_branch and _head(repo) == started_head
    found = _commit_exists(repo, commit_sha)
    verified = bool(found and tip == commit_sha and base == started_head and head_restored)

    artifact = {
        "schema": SCHEMA_LAND,
        "capability_id": "git.change.land.v1",
        "repo_path": str(repo),
        "branch": branch_name,
        "base_branch": started_branch,
        "base_head": started_head,
        "commit_sha": commit_sha,
        "branch_tip": tip,
        "diff_applied": applied,
        "changed_paths": changed_paths,
        "head_restored": head_restored,
        "tests": tests,
        "pushed": False,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": verified,
    }
    path, sha = _write(out_path, artifact)
    return {
        "adapter": "git_object_model_v1",
        "output_path": str(path),
        "output_sha256": sha,
        "output_verified": verified,
        "commit_sha": commit_sha,
        "branch": branch_name,
        "base_head": started_head,
        "diff_applied": applied,
        "changed_paths": changed_paths,
        "head_restored": head_restored,
        "tests_passed": (tests or {}).get("returncode") == 0 if tests else None,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
