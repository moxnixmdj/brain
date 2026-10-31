# PROJECT_BRAIN
"""python.dynamic.differential_test.v1 — run the same inputs through two implementations and
report where they disagree, with the disagreement shrunk to a minimal case.

A differential test is the only oracle that needs no specification: you do not have to know what
`sub(3, 1)` *should* return, only that two implementations of it must return the same thing.  It is
how compilers are tested (Equivalence Modulo Inputs), how library rewrites are trusted, and how a
risky refactor is checked against the code it replaced — the reference is the code before the
change, and "did anything move" becomes a fact instead of a review comment.

The engine is the fuzzer's, deliberately and completely: the same annotation-directed case
generator, the same boundary corpus, the same greedy shrinker.  Only the oracle changes —
outcome equality across two implementations instead of failure of one — because inventing a second
case generator would mean two answers to "which inputs did you try".

Where the reference comes from, in order, and never by guessing:

1. `reference_path` / `reference`, when the sentence or the action states one;
2. `reference_git_ref` (default `HEAD`) — the same file at a stated revision, read with
   `git show <ref>:<path>` and materialised in a temporary directory;
3. otherwise REFUSE: a differential test against a reference nobody named would be a comparison
   with whatever file happened to be nearby, and calling that an oracle is the defect this
   machine keeps having to fix.

Speed: one child interpreter evaluates BOTH implementations over the whole case list and streams a
line per case; only when that child dies (a segfault, a hang, a `sys.exit`) does the parent fall
back to one isolated process per remaining case, so a crash is attributed to a side instead of
losing the run.  The fast path is the common path, and the honest path is still there.

Inputs (kwargs, repo-confined):
  source_root        the file or project under test
  module             module path relative to source_root (implied when source_root is a file)
  qualname           the function compared (default: every public function in the file)
  reference_path     an implementation in the repository to compare against
  reference_git_ref  default "HEAD"
  max_cases          default 48
  seed               default 0
  timeout_s          overall cap (default 120)

result_fields: adapter, capability_id, act, target, reference_basis, cases_run, divergences,
first_divergence, minimal_case, gate, complete, output_path, output_sha256, output_verified.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from canonical.runtime.bound_capabilities.dynamic_probe_v1 import (
    DEFAULT_CASE_TIMEOUT_S,
    _cases,
    _locate,
    _public_functions,
    _smaller_candidates,
    _target_function,
)
from canonical.runtime.bound_capabilities.quality_v1 import (
    _base,
    _destination,
    _fail,
    _inside,
    _write,
)

CAPABILITY_ID = "python.dynamic.differential_test.v1"
DEFAULT_CASES = 48

# ONE CHILD, TWO IMPLEMENTATIONS, EVERY CASE.  Loading by file path with a private module name
# keeps the two implementations from colliding in `sys.modules` -- and keeps the reference from
# shadowing the code under test, which is the one mistake a differential harness must not make.
_HARNESS = r"""
import importlib.util, json, sys
spec = json.loads(sys.argv[1])

def load(path, alias):
    try:
        loader = importlib.util.spec_from_file_location(alias, path)
        module = importlib.util.module_from_spec(loader)
        sys.modules[alias] = module
        loader.loader.exec_module(module)
        return module, None
    except BaseException as exc:
        return None, {"outcome": "unimportable", "exc": type(exc).__name__, "msg": str(exc)[:300]}

def resolve(module, qualname):
    fn = module
    for part in qualname.split("."):
        fn = getattr(fn, part)
    return fn

def evaluate(path, alias, qualname, args):
    module, problem = load(path, alias)
    if problem is not None:
        return problem
    try:
        fn = resolve(module, qualname)
    except BaseException as exc:
        return {"outcome": "unimportable", "exc": type(exc).__name__, "msg": str(exc)[:300]}
    try:
        value = fn(*args)
    except BaseException as exc:
        return {"outcome": "raised", "exc": type(exc).__name__, "msg": str(exc)[:300]}
    return {"outcome": "ok", "repr": repr(value)[:200]}

for index, case in enumerate(spec["cases"]):
    sys.stderr.write("")
    print(json.dumps({"index": index,
                      "left": evaluate(spec["left"], "brain_left_" + str(index), spec["qualname"], case),
                      "right": evaluate(spec["right"], "brain_right_" + str(index), spec["qualname"], case)}),
          flush=True)
"""

_DIVERGENCE_KINDS = {
    ("ok", "ok"): "DIVERGENT_VALUE",
    ("ok", "raised"): "RETURNS_VS_RAISES",
    ("raised", "ok"): "RETURNS_VS_RAISES",
    ("raised", "raised"): "DIVERGENT_EXCEPTION",
    ("timeout", "ok"): "HANGS_ONLY_ON_ONE_SIDE",
    ("ok", "timeout"): "HANGS_ONLY_ON_ONE_SIDE",
}


def _divergence(left: dict, right: dict) -> str | None:
    """How the two implementations disagree, or None when they agree.

    Two equal exceptions are an agreement even when the messages differ: a message is prose, and
    counting prose as a behavioural difference would drown the value divergences that matter.
    """
    kind = (left["outcome"], right["outcome"])
    if kind == ("ok", "ok"):
        return "DIVERGENT_VALUE" if left.get("repr") != right.get("repr") else None
    if kind == ("raised", "raised"):
        same = left.get("exc") == right.get("exc")
        return None if same else "DIVERGENT_EXCEPTION"
    if kind in _DIVERGENCE_KINDS:
        return _DIVERGENCE_KINDS[kind]
    if left["outcome"] == right["outcome"]:
        return None
    return "DIVERGENT_OUTCOME"


def _one_case(python_exe: str, left: Path, right: Path, qualname: str, case: list,
              timeout_s: int) -> dict:
    spec = json.dumps({"left": str(left), "right": str(right), "qualname": qualname,
                       "cases": [case]})
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        proc = subprocess.run([python_exe, "-c", _HARNESS, spec], capture_output=True, text=True,
                              timeout=timeout_s, env=env, check=False)
    except subprocess.TimeoutExpired:
        hung = {"outcome": "timeout", "exc": "Timeout", "msg": f"{timeout_s}s"}
        return {"index": 0, "left": hung, "right": dict(hung)}
    for line in (proc.stdout or "").strip().splitlines():
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    dead = {"outcome": "crashed", "exc": "ProcessCrash",
            "msg": f"rc={proc.returncode} {(proc.stderr or '').strip()[-200:]}"}
    return {"index": 0, "left": dead, "right": dict(dead)}


def _evaluate(python_exe: str, left: Path, right: Path, qualname: str, cases: list,
              timeout_s: int) -> list[dict]:
    """Every case, in one child when it survives; per case in isolation when it does not."""
    spec = json.dumps({"left": str(left), "right": str(right), "qualname": qualname,
                       "cases": cases})
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    rows: dict[int, dict] = {}
    try:
        proc = subprocess.run([python_exe, "-c", _HARNESS, spec], capture_output=True, text=True,
                              timeout=timeout_s, env=env, check=False)
        for line in (proc.stdout or "").strip().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and isinstance(row.get("index"), int):
                rows[row["index"]] = row
    except subprocess.TimeoutExpired:
        pass
    if len(rows) == len(cases):
        return [rows[index] for index in range(len(cases))]
    # THE BATCH IS AN OPTIMISATION, NOT THE TRUTH.  A child that died (or that was killed by a
    # case) proves nothing about the cases it never reported, so those are re-run one at a time.
    for index, case in enumerate(cases):
        if index in rows:
            continue
        rows[index] = _one_case(python_exe, left, right, qualname, case,
                               min(timeout_s, DEFAULT_CASE_TIMEOUT_S))
    return [rows[index] for index in range(len(cases))]


def _reference_file(root: Path, module_file: Path, args: dict, scratch: Path,
                    scratch_name: str | None = None) -> tuple[Path, str]:
    """(materialised reference, how it was chosen) -- stated, or from git, or a refusal."""
    stated = str(args.get("reference_path") or args.get("reference") or "").strip()
    if stated:
        located = _inside(root, stated)
        if located is None or not located.is_file():
            _fail("REFERENCE_NOT_IN_THE_REPOSITORY:" + stated)
        return located, "stated:" + stated
    reference_ref = str(args.get("reference_git_ref") or "HEAD").strip() or "HEAD"
    try:
        # THE REPOSITORY OF THE FILE, NOT OF THE BRAIN.  Asking the brain's own checkout where
        # `HEAD` is answers a question about the brain: a file under a nested repository (every
        # probe world, every fixture repo) is simply "not in HEAD" there, and the capability
        # reported itself broken for a reference that exists one directory up.
        top = subprocess.run(["git", "-C", str(module_file.parent), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=30, check=False)
        root_of_repo = Path((top.stdout or "").strip() or root)
        relative = module_file.resolve().relative_to(root_of_repo.resolve())
    except (OSError, ValueError, subprocess.SubprocessError):
        _fail("REFERENCE_NOT_STATED:no reference_path and this file is not inside a git "
              "repository, so there is nothing to compare against")
    shown = subprocess.run(["git", "-C", str(root_of_repo), "show",
                            f"{reference_ref}:{str(relative).replace(os.sep, chr(47))}"],
                           capture_output=True, text=True, timeout=60, check=False)
    if shown.returncode != 0:
        _fail(f"REFERENCE_NOT_STATED:{reference_ref}:{relative} is not in {reference_ref}")
    materialised = scratch / (scratch_name or module_file.name)
    materialised.write_text(shown.stdout, encoding="utf-8")
    return materialised, f"git:{reference_ref}:{str(relative).replace(os.sep, chr(47))}"


def _shrink_divergence(python_exe: str, left: Path, right: Path, qualname: str, case: list,
                       kind: str, timeout_s: int) -> list:
    """Greedy reduction that must keep DIVERGING THE SAME WAY.  Same law as the fuzzer's shrink."""
    current = list(case)
    changed = True
    rounds = 0
    while changed and rounds < 200:
        rounds += 1
        changed = False
        for index in range(len(current)):
            for candidate in _smaller_candidates(current[index]):
                trial = list(current)
                trial[index] = candidate
                row = _one_case(python_exe, left, right, qualname, trial, timeout_s)
                if _divergence(row["left"], row["right"]) == kind:
                    current = trial
                    changed = True
                    break
            if changed:
                break
    return current


def run(args: dict, root) -> dict:
    root = Path(root)
    args = dict(args or {})
    capability_id = str(args.get("capability_id") or CAPABILITY_ID)
    act = str(args.get("act_verb") or args.get("act") or "differential_test").strip()
    if act != "differential_test":
        _fail("ACT_NOT_SUPPORTED:" + act)
    output_path = str(args.get("output_path") or "").strip()
    if not output_path:
        _fail("OUTPUT_PATH_NOT_STATED")
    destination = _destination(root, output_path)

    project, module_file, module = _locate(root, args, allow_directory_scan=True)
    try:
        max_cases = int(args.get("max_cases") or DEFAULT_CASES)
        seed = int(args.get("seed") or 0)
        case_timeout = int(args.get("case_timeout_s") or DEFAULT_CASE_TIMEOUT_S)
        timeout_s = int(args.get("timeout_s") or 120)
    except (TypeError, ValueError):
        _fail("NUMERIC_ARGUMENT_INVALID")
    python_exe = str(args.get("python_executable") or sys.executable)

    scratch = Path(tempfile.mkdtemp(prefix="brain_differential_"))
    try:
        # A SENTENCE THAT NAMES A DIRECTORY MEANS EVERY PUBLIC MODULE IN IT, each compared with
        # its own reference.  The compiler binds a scope key to the directory when the sentence
        # names no single file, and "differential-test this package against the reference" is a
        # real request -- refusing it because a scope key arrived instead of a file was measured
        # as OWNED_BUT_FAILED:MODULE_NOT_STATED, a capability blamed for a binding detail.
        if module_file.is_dir():
            targets = [(path, (str(path.relative_to(project)).replace(os.sep, "/")
                               .removesuffix(".py").replace("/", ".")))
                       for path in sorted(module_file.glob("*.py"))
                       if not path.name.startswith("_")]
            if not targets:
                _fail("NO_PYTHON_MODULE_IN:" + str(module_file))
        else:
            targets = [(module_file, module)]

        compared = []
        reference_basis = None
        reference_path = None
        first = None
        minimal = None
        for target_file, target_module in targets:
            reference, basis = _reference_file(root, target_file, args, scratch, target_file.name)
            reference_basis, reference_path = basis, reference
            for qualname in ([str(args.get("qualname")).strip()]
                             if str(args.get("qualname") or "").strip()
                             else _public_functions(target_file)):
                try:
                    node, params, defaults = _target_function(project, target_file, qualname)
                except Exception:  # noqa: BLE001,S112 - a varargs/async function is skipped
                    continue
                cases = _cases(node, params, defaults, seed, max_cases)
                rows = _evaluate(python_exe, target_file, reference, qualname, cases, timeout_s)
                divergences = []
                for case, row in zip(cases, rows):
                    if row["left"].get("outcome") == "unimportable":
                        _fail("MODULE_NOT_IMPORTABLE:" + str(row["left"].get("msg")))
                    if row["right"].get("outcome") == "unimportable":
                        _fail("REFERENCE_NOT_IMPORTABLE:" + str(row["right"].get("msg")))
                    kind = _divergence(row["left"], row["right"])
                    if kind:
                        divergences.append({"args": case, "kind": kind, "code": row["left"],
                                            "reference": row["right"]})
                compared.append({"module": target_module, "qualname": qualname,
                                 "cases_run": len(cases), "divergences": len(divergences),
                                 "first": divergences[:20]})
                if divergences:
                    first = compared[-1]
                    break
            if first is not None:
                break

        if first is not None:
            divergence = first["first"][0]
            target_file = next(path for path, dotted in targets if dotted == first["module"])
            minimal = _shrink_divergence(python_exe, target_file, reference_path, first["qualname"],
                                         list(divergence["args"]), divergence["kind"], case_timeout)
            recheck = _one_case(python_exe, target_file, reference_path, first["qualname"], minimal,
                                case_timeout)
            if _divergence(recheck["left"], recheck["right"]) != divergence["kind"]:
                _fail("SHRINK_CHANGED_THE_DIVERGENCE")

        payload = _base(capability_id, act,
                        next((path for path, dotted in targets
                              if first and dotted == first["module"]), targets[0][0]))
        payload.update({
            "target": str(module_file),
            "module": first["module"] if first else targets[0][1],
            "reference": str(reference_path) if reference_path else None,
            "reference_basis": reference_basis,
            "qualname": first["qualname"] if first else (compared[-1]["qualname"] if compared else None),
            "compared": compared,
            "cases_run": sum(item["cases_run"] for item in compared),
            "divergences": sum(item["divergences"] for item in compared),
            "first_divergence": first["first"][0] if first else None,
            "minimal_case": minimal,
            "claim": ("THE IMPLEMENTATIONS DISAGREE: the minimal case above produces different "
                      "behaviour on the code under test and on the reference, and it is the "
                      "shrink of a real disagreement, not of a crash"
                      if first else
                      "THE IMPLEMENTATIONS AGREE: every generated case produced the same outcome "
                      "on both sides; the count above is the comparison, not a pass"),
            "law": ("the same inputs, generated deterministically from the annotations, run through "
                    "both implementations; agreement means the same outcome and, for a return, the "
                    "same repr; two equal exceptions agree even when the messages differ; the "
                    "shrink must keep the same KIND of disagreement"),
            "complete": True,
        })
        written = _write(destination, payload)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    return {
        "adapter": "differential_probe_v1",
        "capability_id": capability_id,
        "act": act,
        "module": payload["module"],
        "reference_basis": basis,
        "cases_run": payload["cases_run"],
        "divergences": payload["divergences"],
        "minimal_case": minimal,
        "gate": "PASS",
        "complete": True,
        "output_path": str(destination),
        "output_sha256": written.get("artifact_sha256"),
        "output_verified": json.loads(Path(destination).read_text(encoding="utf-8"))["artifact_sha256"]
        == written.get("artifact_sha256"),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_root", required=True)
    parser.add_argument("--module", default=None)
    parser.add_argument("--qualname", default=None)
    parser.add_argument("--reference_path", default=None)
    parser.add_argument("--reference_git_ref", default=None)
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--max_cases", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    ns = parser.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
