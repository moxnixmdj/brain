#!/usr/bin/env python3
"""A learned skill is only worth what its verdict can tell apart from doing nothing.

WHY THIS EXISTS
---------------
The previous measurement in this tree asked what a *test suite* is worth and found that a real
suite rejects 80.2% of behaviour-altering candidates while a law read off code structure adds
exactly 0. This module asks the same question about the objects the tree calls learned skills: the
compiled actions in `canonical/astra_runtime/skills/COMPILED_WORKFLOWS_BUNDLE_V1.json`.

Those skills are the "learn it once, keep it forever" artifacts. Each carries:

    goal_regex           the requests it claims to answer
    abstract_steps       the code that answers them, executed in a confined child
    abstract_postcondition   what the answer must satisfy
    hit_count            how often it has been used
    ownership_receipt    the credit flags it is allowed to grant

Every one of them is verified by a postcondition of kind `stdout_equals`: the step is run, its
last line of stdout is compared with the sentence the skill says it will print. That is the whole
verdict. So the question this module measures is exact, and it does not need an opinion:

    can the stored verdict tell the skill apart from a program that changes nothing and prints
    the same sentence?

THE CONTROL THAT MATTERS
------------------------
An oracle that admits a null program is not a weak oracle, it is not an oracle. So for every
skill this instrument runs two programs against the tree's OWN judge -- never a re-implementation
of it, `causal_trace_to_skill_compiler_v1.verify_postcondition` is imported and called:

    THE SKILL       the stored code, on a real request taken from this repository's own files,
                    run in a throwaway copy of the tree.
    THE IMPOSTOR    a two-line program that prints the sentence the postcondition expects and
                    touches nothing.

and next to the judge's verdict it reports an *independent* check of the same claim, read off the
filesystem rather than off the program's own output: did the target file change at all, does it
still parse, and is the variable the sentence names actually gone. A verdict that disagrees with
that check is a verdict that cannot be trusted, which is the only thing being measured here.

WHAT THIS IS NOT
----------------
Not a claim that the skills are useless, and not a claim about the agents that wrote them. Nine of
the eleven cannot be exercised without an example pair the bundle does not carry; they are
reported as unexercised, never as passing. Authority: NONE. `$0`. No model. No network. Nothing
outside a temporary directory is written.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler  # noqa: E402

SCHEMA = "PROJECT_BRAIN_LEARNED_SKILL_VERDICT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

BUNDLE = "canonical/astra_runtime/skills/COMPILED_WORKFLOWS_BUNDLE_V1.json"

ACCEPTED = "THE_VERDICT_ACCEPTED_IT"
REFUSED = "THE_VERDICT_REFUSED_IT"
NOTHING_CLAIMED = "NOTHING_TO_CHECK"


def load_skills(bundle_path: str | pathlib.Path = BUNDLE) -> list[dict[str, Any]]:
    """The learned actions, exactly as the tree stores them."""
    data = json.loads((ROOT / bundle_path).read_text(encoding="utf-8"))
    return list(data.get("skills") or [])


def _placeholder_values(request: Mapping[str, Any]) -> dict[str, Any]:
    return {("?" + key): value for key, value in request.items()}


def concrete_postcondition(skill: Mapping[str, Any],
                           request: Mapping[str, Any]) -> dict[str, Any]:
    """The postcondition with its `?str0`-style placeholders replaced by this request's values."""
    stored = dict(skill["abstract_postcondition"])
    values = _placeholder_values(request)

    def fill(text: str) -> str:
        for placeholder, value in values.items():
            text = text.replace(placeholder, str(value))
        return text

    return {"kind": stored.get("kind"), "expected": fill(str(stored.get("expected") or ""))}


def request_from_goal(skill: Mapping[str, Any], goal: str) -> dict[str, Any] | None:
    """Turn a real request sentence into the parameters the stored step expects."""
    match = re.match(str(skill["goal_regex"]), goal)
    if not match:
        return None
    groups = match.groupdict()
    names = [str(entry).lstrip("?") for entry in skill.get("param_order") or []]
    if set(groups) != set(names):
        return None
    return {name: groups[name] for name in names}


def stored_request_shape(source: str) -> tuple[str, ...]:
    """The order the stored step actually unpacks its REQUEST tuple in.

    `param_order` is NOT that order: for the inline family it lists (str0, str1, path0) while the
    stored code unpacks (path0, str1, str0). Binding by `param_order` therefore handed the skill
    its variable name where it wanted a path, and every attempt was refused with "there is no
    file probes" -- a refusal that looks like the skill being careful and is really this
    instrument passing the arguments in the wrong order.
    """
    import ast

    match = re.search(r"(?m)^REQUEST\s*=\s*(.+)$", source)
    if not match:
        raise ValueError("THE_STORED_STEP_HAS_NO_REQUEST_LINE")
    shape = ast.literal_eval(match.group(1).split("#")[0].strip())
    return tuple(str(entry) for entry in shape)


def request_tuple(skill: Mapping[str, Any], request: Mapping[str, Any]) -> tuple[Any, ...]:
    code = "\n".join(str(step.get("code") or "") for step in skill.get("abstract_steps") or [])
    return tuple(request[entry.lstrip("?")] for entry in stored_request_shape(code))


def source_with_request(skill: Mapping[str, Any], request: Mapping[str, Any]) -> str:
    """The stored code with its REQUEST line bound to a real request. Nothing else is touched."""
    code = "\n".join(str(step.get("code") or "") for step in skill.get("abstract_steps") or [])
    bound = "REQUEST = %r" % (request_tuple(skill, request),)
    rewritten, count = re.subn(r"(?m)^REQUEST\s*=\s*.*$", lambda _m: bound, code, count=1)
    if count != 1:
        raise ValueError("THE_STORED_STEP_HAS_NO_REQUEST_LINE")
    return rewritten


def impostor_source(skill: Mapping[str, Any], request: Mapping[str, Any]) -> str:
    """A program that claims the success the postcondition looks for and does nothing else.

    This is the mutation-testing null program: if the oracle cannot reject *this*, then no
    behaviour the oracle can see distinguishes a skill from no skill.
    """
    expected = concrete_postcondition(skill, request)["expected"]
    return (
        "import sys\n"
        "print(%r)\n"
        "sys.exit(0)\n" % expected
    )


def run_program(source: str, *, workdir: pathlib.Path, timeout_s: float = 120.0,
                python_executable: str | None = None) -> dict[str, Any]:
    """Run one program in the thrown-away copy and return what it printed."""
    step = pathlib.Path(workdir) / "step.py"
    step.write_text(source, encoding="utf-8")
    executable = python_executable or sys.executable
    try:
        process = subprocess.run([executable, "-B", "step.py"], cwd=str(workdir),
                                 capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "", "returncode": None, "why": "TIMEOUT"}
    return {"stdout": process.stdout or "", "stderr": process.stderr or "",
            "returncode": process.returncode, "why": "RAN"}


def judge(postcondition: Mapping[str, Any], *, workdir: pathlib.Path,
          run: Mapping[str, Any]) -> dict[str, Any]:
    """The tree's own oracle, called rather than re-implemented."""
    ok, why = compiler.verify_postcondition(
        dict(postcondition), cwd=workdir,
        execution_result={"step_receipts": [{"stdout": run.get("stdout") or ""}]},
    )
    return {"accepted": bool(ok), "why": why}


def independent_check(claim: str, *, before: str, after: str,
                      function: str | None, variable: str | None) -> dict[str, Any]:
    """What the filesystem says, with no reference to what the program printed.

    Three questions, each decidable without trusting the skill: did anything change, is the
    result still Python, and is the variable the sentence named actually gone from that function.
    """
    import ast

    if before == after:
        return {"holds": False, "why": "THE_FILE_DID_NOT_CHANGE", "claim": claim}
    try:
        tree = ast.parse(after)
    except SyntaxError as exc:
        return {"holds": False, "why": "THE_RESULT_DOES_NOT_PARSE:" + type(exc).__name__,
                "claim": claim}
    if variable is None or function is None:
        return {"holds": True, "why": "THE_FILE_CHANGED_AND_STILL_PARSES", "claim": claim}
    target = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
            target = node
    if target is None:
        return {"holds": False, "why": "THE_FUNCTION_IS_GONE", "claim": claim}
    still_assigned = [
        node for statement in target.body for node in ast.walk(statement)
        if isinstance(node, ast.Name) and node.id == variable
        and isinstance(node.ctx, ast.Store)
    ]
    if still_assigned:
        return {"holds": False, "why": "THE_VARIABLE_IS_STILL_ASSIGNED", "claim": claim}
    return {"holds": True, "why": "THE_VARIABLE_IS_GONE_AND_THE_FILE_PARSES", "claim": claim}


def witness_postcondition(skill: Mapping[str, Any], request: Mapping[str, Any],
                          before: str) -> dict[str, Any]:
    """The same claim, expressed so that it can only be satisfied by changing the file.

    This is not a second opinion bolted on for sympathy: it is the postcondition the learned edit
    skills *needed* and did not carry. `file_edit_claim` reads the file the skill claims to have
    edited, so a program that prints the sentence and writes nothing cannot satisfy it.
    """
    import hashlib

    function_key, variable_key = claim_roles(skill)
    return {
        "kind": "file_edit_claim",
        "path": str(request.get("path0") or ""),
        "function": request.get(function_key) if function_key else "",
        "symbol": request.get(variable_key) if variable_key else "",
        "before_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
    }


def _copy_target(path: str, workdir: pathlib.Path, repo: pathlib.Path) -> str:
    source = (repo / path).read_text(encoding="utf-8")
    destination = pathlib.Path(workdir) / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source, encoding="utf-8")
    return source


def _read_back(path: str, workdir: pathlib.Path) -> str:
    destination = pathlib.Path(workdir) / path
    return destination.read_text(encoding="utf-8") if destination.is_file() else ""


def exercise(skill: Mapping[str, Any], request: Mapping[str, Any], *,
             repo: pathlib.Path = ROOT, python_executable: str | None = None,
             timeout_s: float = 120.0) -> dict[str, Any]:
    """Run the skill and the impostor against the tree's own judge, plus an independent check."""
    path = str(request.get("path0") or "")
    function_key, variable_key = claim_roles(skill)
    function = request.get(function_key) if function_key else None
    variable = request.get(variable_key) if variable_key else None
    concrete = concrete_postcondition(skill, request)
    result: dict[str, Any] = {"goal": str(skill.get("goal_skeleton")), "request": dict(request),
                              "postcondition": concrete}

    with tempfile.TemporaryDirectory(prefix="brain_learned_skill_") as first:
        workdir = pathlib.Path(first)
        before = _copy_target(path, workdir, repo)
        skill_run = run_program(source_with_request(skill, request), workdir=workdir,
                                timeout_s=timeout_s, python_executable=python_executable)
        after = _read_back(path, workdir)
        witness = witness_postcondition(skill, request, before)
        result["skill"] = {
            "returncode": skill_run.get("returncode"),
            "verdict": judge(concrete, workdir=workdir, run=skill_run),
            "witness_verdict": judge(witness, workdir=workdir, run=skill_run),
            "independent": independent_check(result["goal"], before=before, after=after,
                                             function=function, variable=variable),
            "stderr_tail": (skill_run.get("stderr") or "")[-300:],
        }

    with tempfile.TemporaryDirectory(prefix="brain_learned_impostor_") as second:
        workdir = pathlib.Path(second)
        before = _copy_target(path, workdir, repo)
        impostor_run = run_program(impostor_source(skill, request), workdir=workdir,
                                   timeout_s=timeout_s, python_executable=python_executable)
        after = _read_back(path, workdir)
        witness = witness_postcondition(skill, request, before)
        result["impostor"] = {
            "returncode": impostor_run.get("returncode"),
            "verdict": judge(concrete, workdir=workdir, run=impostor_run),
            "witness_verdict": judge(witness, workdir=workdir, run=impostor_run),
            "independent": independent_check(result["goal"], before=before, after=after,
                                             function=function, variable=variable),
        }
    result["verdict_has_power"] = not result["impostor"]["verdict"]["accepted"]
    return result


def claim_roles(skill: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Which parameter the skill's own sentence calls the function, and which the variable."""
    claim = str(skill.get("goal_skeleton") or "")
    function = re.search(r"in the function '(\?[A-Za-z0-9_]+)'", claim)
    variable = re.search(r"the variable '(\?[A-Za-z0-9_]+)'", claim)
    strip = lambda match: match.group(1).lstrip("?") if match else None  # noqa: E731
    return strip(function), strip(variable)


def _local_names(function_node: Any) -> list[str]:
    import ast

    names: list[str] = []
    for statement in function_node.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id not in names:
                    names.append(target.id)
    return names


def candidate_requests(path: str, param_names: Sequence[str] | None = None, *,
                       repo: pathlib.Path = ROOT,
                       limit: int = 12) -> list[dict[str, str]]:
    """Real (file, function, variable) triples read out of this repository, not invented.

    Two shapes exist in the bundle and both are filled from the same facts: a variable in a
    function in a file, plus -- for the rename family -- the new name, which is derived from the
    real one rather than made up.
    """
    import ast

    names = list(param_names or ("path0", "str1", "str0"))
    if set(names) not in ({"path0", "str1", "str0"}, {"path0", "str2", "str0", "str1"}):
        return []
    import ast as _ast

    function_key = "str2" if "str2" in names else "str1"
    tree = _ast.parse((repo / path).read_text(encoding="utf-8"))
    ranked: list[tuple[int, dict[str, str]]] = []
    for node in tree.body:
        if not isinstance(node, _ast.FunctionDef):
            continue
        for variable in _local_names(node):
            stores = sum(
                1 for statement in node.body for inner in _ast.walk(statement)
                if isinstance(inner, _ast.Name) and inner.id == variable
                and isinstance(inner.ctx, _ast.Store)
            )
            loads = sum(
                1 for statement in node.body for inner in _ast.walk(statement)
                if isinstance(inner, _ast.Name) and inner.id == variable
                and isinstance(inner.ctx, _ast.Load)
            )
            request = {"path0": path, function_key: node.name, "str0": variable}
            if "str2" in names:
                request["str1"] = variable + "_brain_renamed"
            # Ranked, not invented: a name assigned once and read once is what the inline family
            # says it accepts, so those candidates are tried first instead of being stumbled on.
            ranked.append(((0 if stores == 1 else 1) * 10 + (0 if loads == 1 else 1), request))
    ranked.sort(key=lambda item: item[0])
    return [request for _score, request in ranked[:limit]]


def find_an_accepted_request(skill: Mapping[str, Any], paths: Sequence[str], *,
                             repo: pathlib.Path = ROOT,
                             python_executable: str | None = None,
                             limit: int = 40) -> dict[str, Any] | None:
    """Search this repository's own code for one request the stored skill actually answers."""
    tried = 0
    param_names = [str(entry).lstrip("?") for entry in skill.get("param_order") or []]
    for path in paths:
        for request in candidate_requests(path, param_names, repo=repo):
            if tried >= limit:
                return None
            tried += 1
            attempt = exercise(skill, request, repo=repo, python_executable=python_executable)
            if (attempt["skill"]["verdict"]["accepted"]
                    and attempt["skill"]["independent"]["holds"]):
                attempt["attempts"] = tried
                return attempt
    return None


def measure(paths: Sequence[str] | None = None, *,
            bundle_path: str | pathlib.Path = BUNDLE,
            repo: pathlib.Path = ROOT,
            python_executable: str | None = None) -> dict[str, Any]:
    """One row per learned skill: was it exercised, and can its verdict tell it from nothing."""
    skills = load_skills(bundle_path)
    search_paths = list(paths or ["canonical/swe_kernel/lesson_admission_gate_v1.py",
                                  "canonical/swe_kernel/rule_expiry_v1.py",
                                  "canonical/tools/specification_from_structure_measure_v1.py"])
    rows: list[dict[str, Any]] = []
    for skill in skills:
        row: dict[str, Any] = {
            "skill_id": skill.get("skill_id"),
            "goal_skeleton": skill.get("goal_skeleton"),
            "postcondition_kind": (skill.get("abstract_postcondition") or {}).get("kind"),
            "hit_count": skill.get("hit_count"),
            "needs_an_example_pair": "path1" in str(skill.get("goal_skeleton")),
        }
        if row["needs_an_example_pair"]:
            row["status"] = "UNEXERCISED_THE_BUNDLE_CARRIES_NO_EXAMPLE_PAIR"
            rows.append(row)
            continue
        found = find_an_accepted_request(skill, search_paths, repo=repo,
                                         python_executable=python_executable)
        if found is None:
            row["status"] = "UNEXERCISED_NO_REQUEST_IN_THESE_PATHS_IT_ANSWERS"
            rows.append(row)
            continue
        row["status"] = "EXERCISED"
        row.update(found)
        rows.append(row)

    exercised = [row for row in rows if row["status"] == "EXERCISED"]
    accepted_impostors = [row for row in exercised if row["impostor"]["verdict"]["accepted"]]
    witness_accepted_impostors = [
        row for row in exercised if row["impostor"]["witness_verdict"]["accepted"]
    ]
    witness_accepted_skills = [
        row for row in exercised if row["skill"]["witness_verdict"]["accepted"]
    ]
    summary = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "network_calls": 0,
        "bundle": str(bundle_path),
        "skills": len(skills),
        "skills_ever_used": sum(1 for skill in skills if (skill.get("hit_count") or 0) > 0),
        "skills_judged_only_by_their_own_stdout": sum(
            1 for skill in skills
            if (skill.get("abstract_postcondition") or {}).get("kind") == "stdout_equals"),
        "skills_exercised": len(exercised),
        "skills_unexercised": len(rows) - len(exercised),
        "impostors_the_stored_verdict_accepted": len(accepted_impostors),
        "impostors_a_file_witness_verdict_accepted": len(witness_accepted_impostors),
        "real_skills_a_file_witness_verdict_accepted": len(witness_accepted_skills),
        "verdicts_with_power": sum(1 for row in exercised if row["verdict_has_power"]),
        "rows": rows,
    }
    return summary


def summarize(report: Mapping[str, Any]) -> str:
    lines = [
        "LEARNED SKILLS -- what their stored verdict can tell apart",
        f"  skills in the bundle                 {report['skills']}",
        f"  judged only by their own stdout      {report['skills_judged_only_by_their_own_stdout']}",
        f"  ever used (hit_count > 0)            {report['skills_ever_used']}",
        f"  exercised here                       {report['skills_exercised']}",
        f"  unexercised (no example pair)        {report['skills_unexercised']}",
        "",
        f"  a do-nothing program the STORED verdict accepted   "
        f"{report['impostors_the_stored_verdict_accepted']} of {report['skills_exercised']}",
        f"  a do-nothing program a FILE WITNESS accepted       "
        f"{report['impostors_a_file_witness_verdict_accepted']} of {report['skills_exercised']}",
        f"  the REAL skills a file witness still accepts       "
        f"{report['real_skills_a_file_witness_verdict_accepted']} of {report['skills_exercised']}",
    ]
    for row in report["rows"]:
        if row["status"] != "EXERCISED":
            continue
        lines.append(
            f"    {row['goal_skeleton'][:54]:<54} skill={'Yes' if row['skill']['verdict']['accepted'] else 'No '}"
            f" independent={'Yes' if row['skill']['independent']['holds'] else 'No '}"
            f" impostor={'ACCEPTED' if row['impostor']['verdict']['accepted'] else 'refused '}"
        )
    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Measure what a learned skill's verdict is worth.")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--paths", nargs="*", default=None)
    ns = parser.parse_args()
    report = measure(ns.paths)
    print(summarize(report))
    if ns.json_path:
        path = pathlib.Path(ns.json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
