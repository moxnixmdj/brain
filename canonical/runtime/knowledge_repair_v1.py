"""An UNTYPED slot becomes DO by reading the environment's own answers, one refusal at a time.

WHAT WAS MEASURED, AND HOW IT CHANGED THE DESIGN. The plan was to wire `known_and_unknown_v1`'s 14 UNTYPED
rows into `require_survey_plan_v1` so it would read a tool's documentation and fetch what was missing.
That is the right idea for an EXTERNAL tool. For a brain-native capability it is the wrong shape, because
the documentation is the source and the source cannot tell you about the environment.

What the environment does instead, measured 2026-11-23 on `python.refactor.move_function.v1`:

    call with guessed values -> REFUSES: TEST_ROOT_MISSING
    add a tests dir           -> REFUSES: MODULE_NOT_FOUND:file_survey
    pass a path not a name    -> REFUSES: MODULE_NOT_FOUND:file_survey   (it wanted "<path>.py")
    give it "file_survey.py"  -> REFUSES: NAME_COLLISION_TARGET_MODULE:archive_tarfile.py:run
    pick a target without it  -> REFUSES: SUITE_FAILED_AFTER_MOVE: Start directory is not importable
    add tests/__init__.py     -> PASS   suite_passed: true, output_verified: true

SIX REFUSALS, EACH NAMING THE EXACT FACT THAT WAS MISSING, and the last call verified. That is a better
knowledge source than a document ever is: the refusal is about THIS environment, and it cannot be out of
date. It is the owner's "get what you don't know instantly" with the fetching done by asking the thing
itself.

SO THE MECHANISM IS NOT A DOCUMENT READER, IT IS A REPAIR LOOP:

    for each refusal shaped `CODE:arg`, ask this module's own TABLE what that code means, apply the
    smallest action that answers it, and try again. Bounded, and every step is recorded.

THE TABLE IS THE KNOWLEDGE, AND IT IS SMALL ON PURPOSE. Each entry is one fact about the shape a capability
needs -- "a project needs an importable tests directory next to it". It is not a script per capability and
it is not a model of the world; it is a fact learned once, here, from a refusal. That is what the owner
asked to have generalised: the ACT, not the environment.

WHAT THIS FILE REFUSES TO DO:
  * It never invents a value the refusal did not name. `x_value` and `label` cannot be repaired from a
    refusal, and rows needing them stay TYPED_OUT.
  * It never weakens a check to make a row pass. `SUITE_FAILED_AFTER_MOVE` is answered by making the suite
    runnable, not by skipping it.
  * It never records a claim as learned until the call verified. The receipt is the run.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import tempfile
from collections.abc import Callable, Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_KNOWLEDGE_REPAIR_V1"

# Each entry answers one refusal shape. `pattern` is the runtime's own code; `repair` does the smallest
# thing that could satisfy it and returns a note, or None when it cannot help.
_MISSING_ROOT = re.compile(r"TEST_ROOT_MISSING(?::(?P<path>[^\s]+))?")
_IMPORTABLE = re.compile(r"Start directory is not importable: '([^']+)'")
_COLLISION = re.compile(r"NAME_COLLISION_TARGET_MODULE:([^:]+):(.+)")


def _ensure_tests(project: pathlib.Path, detail: str) -> str | None:
    """Create the tests directory THE REFUSAL NAMED, falling back to the project root only if it is silent.

    The first version guessed `<project>/tests` and the row wanted `<project>.parent/tests`; the loop made
    the same directory twice and reported the same refusal. A refusal that carries its own path is
    actionable; one that does not is a riddle. This reads the path when the message has one.
    """
    match = _MISSING_ROOT.search(detail)
    named = match.group("path") if match and match.groupdict().get("path") else None
    tests = pathlib.Path(named) if named else (project / "tests")
    if tests.is_dir():
        return None
    try:
        tests.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return "created %s" % tests


def _make_importable(project: pathlib.Path, detail: str) -> str | None:
    """An importable test directory needs `__init__.py`. That is a fact about Python, learned once.

    The refusal NAMES the directory it could not import; using `project / "tests"` instead made the repair
    miss a directory that lives one level up, and the loop spent its budget on a refusal it had already
    been told how to answer.
    """
    match = _IMPORTABLE.search(detail)
    tests = pathlib.Path(match.group(1)) if match else (project / "tests")
    init = tests / "__init__.py"
    if init.is_file():
        return None
    if not tests.is_dir():
        return None
    init.write_text("")
    return "added %s" % init


def _collision_name(detail: str) -> str | None:
    match = _COLLISION.search(detail)
    return match.group(2) if match else None


def repair_once(call: Callable[[], Any], project: pathlib.Path,
                args: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
    """Call, read the refusal, answer it, call again. Bounded to the facts in this file.

    The returned record is the evidence: every repeated refusal, every repair, every value that changed.
    """
    record: dict[str, Any] = {"attempts": [], "repairs": [], "verified": False}
    current = dict(args)
    for _ in range(8):
        try:
            result = call(current)
            record["attempts"].append({"outcome": "PASS"})
            record["verified"] = bool(isinstance(result, Mapping) and
                                      (result.get("output_verified") or result.get("verified")
                                       or result.get("suite_passed")))
            return result, record
        except Exception as exc:  # noqa: BLE001 - a refusal is the input
            detail = "%s:%s" % (type(exc).__name__, exc)
            record["attempts"].append({"outcome": "REFUSED", "detail": detail[:200]})
            if _MISSING_ROOT.search(detail):
                note = _ensure_tests(project, detail)
            elif _IMPORTABLE.search(detail):
                note = _make_importable(project, detail)
            elif _collision_name(detail):
                # The target already defines this name. A move is not the right act; say so and stop
                # rather than renaming the user's function behind their back.
                record["why"] = "TARGET_ALREADY_DEFINES_THAT_NAME"
                return None, record
            else:
                note = None
            if note is None:
                record["why"] = "NO_REPAIR_KNOWN_FOR_THIS_REFUSAL"
                return None, record
            record["repairs"].append(note)
    record["why"] = "BUDGET_EXHAUSTED"
    return None, record


def _copy_environment(source: str | pathlib.Path) -> pathlib.Path:
    """A private copy, so the repair loop's writes are not the user's tree."""
    destination = pathlib.Path(tempfile.mkdtemp(prefix="brain_repair_env_"))
    shutil.copytree(source, destination / "pkg", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    return destination


def repair_untyped(capability_id: str, seed_args: Mapping[str, Any], source_environment: str | pathlib.Path,
                   *, root: str | pathlib.Path = ".") -> dict[str, Any]:
    """Take one UNTYPED row and try to make it DO, by asking the capability what it needs.

    The capability is called in a COPY of `source_environment`. `seed_args` are the values the caller
    could supply; the loop only adds what a refusal named.
    """
    from canonical.runtime import reachability_v2 as reach
    from canonical.runtime import live_integrated_brain_v1 as brain

    reg = brain.load_verified_registry()
    entry = reg.get(capability_id) or {}
    adapter = reach._adapter_path(entry)
    if not adapter:
        return {"schema": SCHEMA, "capability_id": capability_id, "verified": False,
                "why": "NO_ADAPTER_DECLARED"}

    env = _copy_environment(source_environment)
    project = env / "pkg"
    args = {str(k): v for k, v in seed_args.items()}

    def call(current: Mapping[str, Any]) -> Any:
        import importlib.util
        module_name = "_knr_" + capability_id.replace(".", "_")
        spec = importlib.util.spec_from_file_location(module_name, adapter)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.run(dict(current), str(env))

    result, record = repair_once(call, project, args)
    return {"schema": SCHEMA, "capability_id": capability_id,
            "verified": record["verified"], "result": result,
            "attempts": record["attempts"], "repairs": record["repairs"],
            "why": record.get("why"), "environment": str(env)}


def main() -> None:
    report = repair_untyped(
        "python.refactor.move_function.v1",
        {"capability_id": "python.refactor.move_function.v1", "source_root": "pkg",
         "module": "file_survey.py", "symbol": "run", "to_module": "broad_objective_decompose.py",
         "output_path": "pkg/out.json", "timeout_s": 120},
        pathlib.Path(__file__).resolve().parents[2] / "canonical/runtime/bound_capabilities",
    )
    print(json.dumps({k: report[k] for k in ("capability_id", "verified", "repairs", "why")}, indent=1))


if __name__ == "__main__":
    main()
