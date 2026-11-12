#!/usr/bin/env python3
"""What does one bug fix teach? Measured on QuixBugs with the tree's own retention organ, unchanged.

The claim under test, in the coding domain: "let the system experience a fix once and it has
learned it" -- so that the next bug is repaired from what was learned.

The environment nobody here wrote: QuixBugs (github.com/jkoppel/QuixBugs, MIT). Forty small
Python programs, each with a defect on one line, each with its own tests and its published
correct version. It is the EASIEST setting there is for program repair: one file, one line.

The organ, used as it is in the tree and not edited:
    canonical/swe_kernel/verified_skill_crystallizer_v1.VerifiedSkillStore
      crystallize_code_fix        one verified fix in  -> a stored rule (or a stated refusal)
      recall_and_apply_verified   new source in        -> a patch proposed from the stored rules,
                                                          accepted only if the target's tests pass
    canonical/swe_kernel/skill_verification_contract_v1.ProjectTestOracle
      the verifier: copies the bounded project, writes the candidate, runs the project's tests

Four questions, each answered by the target program's own tests:
    same_bug_again     taught fix i; a fresh copy of bug i  -> repaired from memory?      (recall)
    one_fix            taught fix i and nothing else; every other bug j -> repaired?      (transfer)
    all_other_fixes    taught the fixes of all the other programs; bug j -> repaired?     (transfer)
    already_held       taught nothing here; the rules the tree ships with as what it has
                       already learned (its seed bundle); bug j -> repaired?              (transfer)
Two settings of the organ:
    as_taught          its defaults
    widest             every generalisation it offers switched on (operator generalisation,
                       scope escalation, cross-scope transfer)

Before anything is taught, each program is checked: its buggy version must fail its tests in
a way the oracle can count, and the buggy text with the published fix applied must pass. What
fails that check is reported and left out, not repaired by hand.

Nothing here searches for a fix: a repair is whatever the organ proposes from what it was
taught, and it counts only if the target's own tests pass on it (checked a second time with a
fresh oracle). For every repair the record says which lesson's rule produced it, by which of
the organ's strategies, and whether the patch is the published fix or another one that passes.
A target that many unrelated lessons "repair" was repaired by the organ's generic operator
swaps, not by what any one lesson said; the per-target count of such lessons is reported so
that the two are not confused.

No model is called anywhere. Authority: none; this is a producer-run measurement.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import pathlib
import shutil
import sys
import tempfile
import time
import tokenize
from typing import Any, Callable, Iterable, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "BRAIN_QUIXBUGS_ONE_FIX_TRANSFER_MEASUREMENT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
SCOPE = "quixbugs-python"
CONTRACT = {"schema_version": 1, "scope_id": SCOPE, "verification_kind": "TEST_SUITE"}
CONTEXT = {"dependencies": {}, "preconditions": {}}
SETTINGS: dict[str, dict[str, bool]] = {
    "as_taught": {"allow_operator_generalization": False, "allow_scope_escalation": False,
                  "allow_cross_scope_transfer": False},
    "widest": {"allow_operator_generalization": True, "allow_scope_escalation": True,
               "allow_cross_scope_transfer": True},
}
DEFAULT_TIMEOUT_S = 8
HELPERS = ("load_testdata.py", "node.py")


# --------------------------------------------------------------------------- #
# the benchmark as it is on disk
# --------------------------------------------------------------------------- #
def program_names(root: pathlib.Path) -> list[str]:
    """Every program that has a buggy version, a correct version and a test file."""
    names = []
    for test in sorted((root / "python_testcases").glob("test_*.py")):
        name = test.stem[len("test_"):]
        if (root / "python_programs" / f"{name}.py").is_file() and (root / "correct_python_programs" / f"{name}.py").is_file():
            names.append(name)
    return names


def split_trailing_docstring(text: str) -> tuple[str, str]:
    """(code, tail). The buggy files end with a description in a triple-quoted string that the
    correct files do not carry; it is not part of the defect and is kept as it is."""
    stripped = text.rstrip()
    if not stripped.endswith('"""'):
        return text, ""
    opening = stripped.rfind('"""', 0, len(stripped) - 3)
    if opening < 0:
        return text, ""
    line_start = stripped.rfind("\n", 0, opening) + 1
    if stripped[line_start:opening].strip():
        return text, ""                      # the string is part of a statement, not a trailing description
    kept = text[:line_start].rstrip("\n")
    if not kept:
        return text, ""                      # nothing but a description: there is no code to split it from
    return kept + "\n", text[len(kept) + 1:]


def reference_fix(buggy: str, correct: str) -> dict[str, Any]:
    """The buggy text with the published fix applied and nothing else changed, and which lines
    that touched. The fix is read off the two published versions; it is never written here."""
    code, tail = split_trailing_docstring(buggy)
    right, _ = split_trailing_docstring(correct)       # some correct files end with other solutions in a string
    body = code.strip("\n")
    lead = code[:len(code) - len(code.lstrip("\n"))]    # blank lines a file starts with are not a defect either
    before = body.split("\n")
    after = right.strip("\n").split("\n")
    hunks = []
    out: list[str] = []
    matcher = difflib.SequenceMatcher(a=[l.rstrip() for l in before], b=[l.rstrip() for l in after], autojunk=False)
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            out += before[a0:a1]
        else:
            out += after[b0:b1]
            hunks.append({"removed": before[a0:a1], "added": after[b0:b1]})
    fixed = lead + "\n".join(out) + "\n" + tail
    return {"fixed_source": fixed, "hunks": hunks,
            "lines_removed": sum(len(h["removed"]) for h in hunks),
            "lines_added": sum(len(h["added"]) for h in hunks)}


def build_project(root: pathlib.Path, name: str, where: pathlib.Path) -> pathlib.Path:
    """One program as a small project of its own: the buggy source, its tests, what the tests
    load, and the benchmark's own pytest configuration. The correct version is NOT copied in."""
    project = where / name
    if project.exists():
        shutil.rmtree(project)
    for folder in ("python_programs", "python_testcases", "json_testcases"):
        (project / folder).mkdir(parents=True)
    shutil.copy(root / "conftest.py", project / "conftest.py")
    shutil.copy(root / "python_programs" / f"{name}.py", project / "python_programs" / f"{name}.py")
    if (root / "python_programs" / "node.py").is_file() and name != "node":
        shutil.copy(root / "python_programs" / "node.py", project / "python_programs" / "node.py")
    shutil.copy(root / "python_testcases" / f"test_{name}.py", project / "python_testcases" / f"test_{name}.py")
    for helper in HELPERS:
        if (root / "python_testcases" / helper).is_file():
            shutil.copy(root / "python_testcases" / helper, project / "python_testcases" / helper)
    data = root / "json_testcases" / f"{name}.json"
    if data.is_file():
        shutil.copy(data, project / "json_testcases" / f"{name}.json")
    return project


def oracle_for(project: pathlib.Path, name: str, *, timeout_s: int = DEFAULT_TIMEOUT_S) -> Any:
    from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
    return ProjectTestOracle(project, f"python_programs/{name}.py", [f"python_testcases/test_{name}.py"],
                             SCOPE, timeout_s=timeout_s)


def verdict(result: Any) -> dict[str, Any]:
    evidence = dict(getattr(result, "evidence", {}) or {})
    return {"passed": bool(getattr(result, "passed", False)), "test_count": evidence.get("test_count"),
            "returncode": evidence.get("returncode"), "oracle_error": evidence.get("error")}


# --------------------------------------------------------------------------- #
# the check before anything is taught
# --------------------------------------------------------------------------- #
def census(root: pathlib.Path, names: Sequence[str], work: pathlib.Path, *, timeout_s: int = DEFAULT_TIMEOUT_S,
           progress: Callable[[str], None] | None = None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name in names:
        buggy = (root / "python_programs" / f"{name}.py").read_text(encoding="utf-8")
        correct = (root / "correct_python_programs" / f"{name}.py").read_text(encoding="utf-8")
        fix = reference_fix(buggy, correct)
        project = build_project(root, name, work)
        oracle = oracle_for(project, name, timeout_s=timeout_s)
        started = time.time()
        as_published = verdict(oracle(buggy))
        buggy_seconds = round(time.time() - started, 2)
        started = time.time()
        with_fix = verdict(oracle(fix["fixed_source"]))
        fixed_seconds = round(time.time() - started, 2)
        counted_failure = (not as_published["passed"] and not as_published["oracle_error"]
                           and (as_published["test_count"] or 0) > 0 and as_published["returncode"] not in (0, None))
        out[name] = {
            "fix": {k: fix[k] for k in ("hunks", "lines_removed", "lines_added")},
            "buggy": as_published, "buggy_seconds": buggy_seconds,
            "with_the_published_fix": with_fix, "fixed_seconds": fixed_seconds,
            "can_be_a_target": bool(with_fix["passed"] and not as_published["passed"]),
            "buggy_fails_in_a_way_the_oracle_counts": bool(counted_failure),
        }
        if progress:
            row = out[name]
            progress(f"{name:<28} buggy: passed={as_published['passed']} tests={as_published['test_count']} "
                     f"rc={as_published['returncode']} err={as_published['oracle_error']} {buggy_seconds}s | "
                     f"fixed: passed={with_fix['passed']} {fixed_seconds}s | -{fix['lines_removed']}+{fix['lines_added']} "
                     f"| target={row['can_be_a_target']} countable={row['buggy_fails_in_a_way_the_oracle_counts']}")
    return out


# --------------------------------------------------------------------------- #
# teaching and recalling, through the organ as it is
# --------------------------------------------------------------------------- #
ERROR_CLASS = "quixbugs_python"        # one class for every lesson: it must not say which program a lesson came from
RECALL_WALL_LIMIT_S = 240


def _store(path: pathlib.Path) -> Any:
    """A store that holds what is put into it here and nothing else. (Left to itself, a new store
    of this organ starts from the rules the tree ships with; that would be a lesson nobody gave.)"""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    return VerifiedSkillStore(pathlib.Path(path), seed=False)


def _shipped_store(path: pathlib.Path) -> Any:
    """A new store as the organ makes one by default: started from the rules the tree ships with."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    if pathlib.Path(path).exists():
        pathlib.Path(path).unlink()
    return VerifiedSkillStore(pathlib.Path(path), seed=True)


def teach(store_path: pathlib.Path, buggy: str, fixed: str, oracle: Any) -> dict[str, Any]:
    """One verified fix into an empty store. What comes back is the organ's own answer: a rule
    was stored, or the reason it refused."""
    taught = _store(store_path).crystallize_code_fix(
        before_snippet=buggy, after_snippet=fixed, language="python", error_class=ERROR_CLASS,
        contract=CONTRACT, training_verifier=oracle)
    return {"crystallized": bool(taught.get("crystallized")), "reason": taught.get("reason"),
            "skill_id": taught.get("skill_id"), "hole_count": taught.get("hole_count")}


def calibrate(store_path: pathlib.Path) -> dict[str, Any]:
    """What the production path does after it has stored a lesson
    (retained_repair_session_v1.RetainedRepairSession.learn): the rule looks for its own scope."""
    from canonical.swe_kernel.rule_scope_learning_v1 import calibrate_rule_scope
    store = _store(store_path)
    out: dict[str, Any] = {}
    for rule in store.lookup_rules("python"):
        try:
            report = calibrate_rule_scope(rule, store=store)
            out[str(rule.get("skill_id"))] = {"result": report.get("result"), "scope": report.get("scope")}
        except Exception as error:  # noqa: BLE001 -- production swallows this too; here it is at least written down
            out[str(rule.get("skill_id"))] = {"error": type(error).__name__}
    return out


def store_holding(lessons: Iterable[pathlib.Path], where: pathlib.Path) -> tuple[pathlib.Path, dict[str, int]]:
    """A new store holding the rules of the given stores, moved with the organ's own export and
    import. Every recall gets one of its own: a recall writes to the store it reads. What comes
    back with it is counted from the new store: how many lessons went in, how many different
    rules it now holds (two lessons can be one rule), and how many the import refused."""
    for stale in (where, where.with_name(where.name + "-wal"), where.with_name(where.name + "-shm")):
        if stale.exists():
            stale.unlink()
    target = _store(where)
    given, refused = 0, 0
    for lesson in lessons:
        given += 1
        refused += int(target.import_bundle(_store(lesson).export_bundle()).get("refused") or 0)
    return where, {"lessons": given, "rules": len(target.lookup_rules("python")), "refused": refused}


class _RecallTookTooLong(Exception):
    pass


def recall(store_path: pathlib.Path, source: str, oracle: Any, setting: str) -> dict[str, Any]:
    """New source in; a patch out, or nothing. The organ verifies with the target's tests itself."""
    import signal

    def _stop(signum: int, frame: Any) -> None:
        raise _RecallTookTooLong()

    calls_before = int(getattr(oracle, "calls", 0))
    started = time.time()
    previous = signal.signal(signal.SIGALRM, _stop)
    signal.alarm(RECALL_WALL_LIMIT_S)
    hit, problem = None, None
    try:
        hit = _store(store_path).recall_and_apply_verified(
            source_text=source, language="python", verifier=oracle, required_verification_kind="TEST_SUITE",
            scope_id=SCOPE, context=CONTEXT, **SETTINGS[setting])
    except _RecallTookTooLong:
        problem = "RECALL_TOOK_TOO_LONG"
    except Exception as error:  # noqa: BLE001 -- one recall must not take the others' results with it
        problem = "ORGAN_RAISED_" + type(error).__name__
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    out: dict[str, Any] = {"proposed": hit is not None, "oracle_calls": int(getattr(oracle, "calls", 0)) - calls_before,
                           "seconds": round(time.time() - started, 2)}
    if problem:
        out["problem"] = problem
    if hit is not None:
        out.update(patched_source=hit["patched_source"], skill_id=hit.get("skill_id"),
                   strategy=hit.get("recall_strategy"), scope_tier=hit.get("scope_tier"))
    return out


def _same_code(a: str, b: str) -> bool:
    """The same program text, blank lines and trailing spaces aside."""
    def lines(text: str) -> list[str]:
        return [line.rstrip() for line in text.split("\n") if line.strip()]
    return lines(a) == lines(b)


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #
def measure(root: pathlib.Path, names: Sequence[str], work: pathlib.Path, *, timeout_s: int = DEFAULT_TIMEOUT_S,
            settings: Sequence[str] = tuple(SETTINGS), one_fix_teachers: int | None = None, seed: int = 0,
            checked: Mapping[str, Mapping[str, Any]] | None = None,
            progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    import random

    say = progress or (lambda line: None)
    for setting in settings:
        if setting not in SETTINGS:
            raise ValueError("SETTING_UNKNOWN")
    projects, stores, scratch = work / "projects", work / "stores", work / "scratch"
    for folder in (stores, scratch):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
    if checked is None:
        checked = census(root, names, projects, timeout_s=timeout_s, progress=progress)
    else:
        for name in names:
            build_project(root, name, projects)
    targets = [name for name in names if checked[name]["can_be_a_target"]]

    buggy, fixed, verifier = {}, {}, {}
    for name in names:
        buggy[name] = (root / "python_programs" / f"{name}.py").read_text(encoding="utf-8")
        correct = (root / "correct_python_programs" / f"{name}.py").read_text(encoding="utf-8")
        fixed[name] = reference_fix(buggy[name], correct)["fixed_source"]
        verifier[name] = oracle_for(projects / name, name, timeout_s=timeout_s)

    # ---- every fix is taught once, alone, into an empty store ------------------------------------------------
    lessons: dict[str, dict[str, Any]] = {}
    plain: dict[str, pathlib.Path] = {}            # the lesson as stored
    calibrated: dict[str, pathlib.Path] = {}       # the same lesson after the rule has looked for its own scope
    rule_of: dict[str, str] = {}                   # lesson -> the rule it became (two lessons can become the same rule)
    for name in targets:
        path = stores / f"{name}.sqlite"
        lesson = teach(path, buggy[name], fixed[name], verifier[name])
        if lesson["crystallized"]:
            plain[name] = path
            rule_of[name] = str(lesson["skill_id"])
            second, copied = store_holding([path], stores / f"{name}.calibrated.sqlite")
            lesson["rules_in_the_calibrated_copy"] = copied["rules"]       # 1, unless the organ refused its own export
            lesson["scope_calibration"] = calibrate(second)
            calibrated[name] = second
        lessons[name] = lesson
        say(f"taught {name:<28} {'stored' if lesson['crystallized'] else 'REFUSED ' + str(lesson['reason'])}")
    taught = sorted(plain)

    def lesson_stores(setting: str) -> dict[str, pathlib.Path]:
        # production calibrates after teaching and recalls with its defaults; the widest setting leaves the
        # rule at the broadest scope the organ assumes for a rule nobody calibrated, and switches everything on
        return calibrated if setting == "as_taught" else plain

    def attempt(teachers: Sequence[str], target: str, setting: str) -> dict[str, Any]:
        held, tally = store_holding([lesson_stores(setting)[t] for t in teachers], scratch / "recall.sqlite")
        outcome = recall(held, buggy[target], verifier[target], setting)
        outcome.update(lessons_given=tally["lessons"], rules_held=tally["rules"], rules_refused_on_the_way=tally["refused"])
        patched = outcome.pop("patched_source", None)
        repaired = False
        if patched is not None:
            # the organ accepted it on the target's tests; ask the tests once more, with nothing of the organ in between
            repaired = bool(oracle_for(projects / target, target, timeout_s=timeout_s)(patched).passed)
            outcome["is_the_published_fix"] = _same_code(patched, fixed[target])
            outcome["from_the_lesson_of"] = sorted(t for t in teachers if rule_of[t] == str(outcome.get("skill_id")))
        outcome["repaired"] = repaired
        return outcome

    result: dict[str, Any] = {"same_bug_again": {}, "one_fix": {}, "all_other_fixes": {}, "already_held": {}}
    shipped_path = stores / "shipped_with_the_tree.sqlite"
    shipped_rules = len(_shipped_store(shipped_path).lookup_rules("python"))

    def with_what_the_tree_ships(target: str, setting: str) -> dict[str, Any]:
        held, tally = store_holding([shipped_path], scratch / "recall.sqlite")
        outcome = recall(held, buggy[target], verifier[target], setting)
        outcome.update(lessons_given=0, rules_held=tally["rules"], rules_refused_on_the_way=tally["refused"])
        patched = outcome.pop("patched_source", None)
        outcome["repaired"] = bool(patched is not None
                                   and oracle_for(projects / target, target, timeout_s=timeout_s)(patched).passed)
        if patched is not None:
            outcome["is_the_published_fix"] = _same_code(patched, fixed[target])
        return outcome
    rng = random.Random(seed)
    teachers = taught if one_fix_teachers is None or one_fix_teachers >= len(taught) else sorted(rng.sample(taught, one_fix_teachers))
    for setting in settings:
        again = {name: attempt([name], name, setting) for name in taught}
        result["same_bug_again"][setting] = again
        say(f"[{setting}] same bug again: {sum(1 for o in again.values() if o['repaired'])} of {len(again)}")
        pairs: dict[str, dict[str, Any]] = {}
        for teacher in teachers:
            row = {target: attempt([teacher], target, setting) for target in targets if target != teacher}
            pairs[teacher] = row
            say(f"[{setting}] one fix, {teacher:<28} repairs {sum(1 for o in row.values() if o['repaired'])} of {len(row)} others"
                f" ({sum(o['oracle_calls'] for o in row.values())} test runs)")
        result["one_fix"][setting] = pairs
        others = {target: attempt([t for t in taught if t != target], target, setting) for target in targets}
        result["all_other_fixes"][setting] = others
        say(f"[{setting}] all other fixes: {sum(1 for o in others.values() if o['repaired'])} of {len(others)}")
        shipped = {target: with_what_the_tree_ships(target, setting) for target in targets}
        result["already_held"][setting] = shipped
        say(f"[{setting}] what the tree ships with: {sum(1 for o in shipped.values() if o['repaired'])} of {len(shipped)}")
    return {"programs": list(names), "targets": targets, "lessons": lessons, "taught": taught,
            "one_fix_teachers": teachers, "census": dict(checked), "outcomes": result,
            "python_rules_the_tree_ships_with": shipped_rules}


def summarise(measured: Mapping[str, Any]) -> dict[str, Any]:
    lessons = measured["lessons"]
    refused: dict[str, list[str]] = {}
    for name, lesson in lessons.items():
        if not lesson["crystallized"]:
            refused.setdefault(str(lesson["reason"]), []).append(name)
    out: dict[str, Any] = {
        "programs": len(measured["programs"]),
        "usable_as_targets": len(measured["targets"]),
        "not_usable": sorted(set(measured["programs"]) - set(measured["targets"])),
        "fixes_the_organ_stored_as_lessons": len(measured["taught"]),
        "fixes_the_organ_refused_to_store": {reason: sorted(names) for reason, names in sorted(refused.items())},
        "python_rules_the_tree_ships_with": measured.get("python_rules_the_tree_ships_with"),
        "lessons_whose_calibrated_copy_lost_the_rule": sorted(
            name for name, lesson in lessons.items() if lesson["crystallized"] and not lesson.get("rules_in_the_calibrated_copy")),
        "settings": {},
    }
    for setting, again in measured["outcomes"]["same_bug_again"].items():
        pairs = measured["outcomes"]["one_fix"][setting]
        others = measured["outcomes"]["all_other_fixes"][setting]
        flat = [(teacher, target, o) for teacher, row in pairs.items() for target, o in row.items()]
        repaired_pairs = [(teacher, target, o) for teacher, target, o in flat if o["repaired"]]
        by_target: dict[str, int] = {}
        for _, target, _ in repaired_pairs:
            by_target[target] = by_target.get(target, 0) + 1
        per_teacher = sorted(sum(1 for o in row.values() if o["repaired"]) for row in pairs.values())
        strategies: dict[str, int] = {}
        for _, _, o in repaired_pairs:
            strategies[str(o.get("strategy"))] = strategies.get(str(o.get("strategy")), 0) + 1
        shipped = (measured["outcomes"].get("already_held") or {}).get(setting) or {}
        out["settings"][setting] = {
            "what_the_tree_ships_with_then_this_bug": {
                "repaired": sum(1 for o in shipped.values() if o["repaired"]), "of": len(shipped),
                "which": sorted(t for t, o in shipped.items() if o["repaired"]),
                "rules_held": sorted({o["rules_held"] for o in shipped.values()}),
                "test_runs": sum(o["oracle_calls"] for o in shipped.values())},
            "same_bug_again": {"repaired": sum(1 for o in again.values() if o["repaired"]), "of": len(again),
                               "not_repaired": sorted(n for n, o in again.items() if not o["repaired"])},
            "one_fix_then_another_bug": {
                "pairs_repaired": len(repaired_pairs), "pairs_tried": len(flat),
                "of_which_with_the_published_fix": sum(1 for _, _, o in repaired_pairs if o.get("is_the_published_fix")),
                "lessons_tried": len(pairs),
                "other_bugs_repaired_per_lesson": {"least": per_teacher[0] if per_teacher else None,
                                                   "middle": per_teacher[len(per_teacher) // 2] if per_teacher else None,
                                                   "most": per_teacher[-1] if per_teacher else None},
                "lessons_that_repair_no_other_bug": sum(1 for n in per_teacher if n == 0),
                "targets_some_lesson_repairs": len(by_target),
                "lessons_that_repair_each_such_target": dict(sorted(by_target.items())),
                "by_strategy": dict(sorted(strategies.items())),
                "test_runs": sum(o["oracle_calls"] for _, _, o in flat),
                "recalls_with_a_problem": sum(1 for _, _, o in flat if o.get("problem")),
                "recalls_that_lost_a_rule_on_the_way": sum(1 for _, _, o in flat if o["rules_refused_on_the_way"] or o["rules_held"] < 1),
            },
            "all_other_fixes_then_this_bug": {
                "repaired": sum(1 for o in others.values() if o["repaired"]), "of": len(others),
                "which": {t: {"from_the_lesson_of": o.get("from_the_lesson_of"), "strategy": o.get("strategy"),
                              "is_the_published_fix": o.get("is_the_published_fix")}
                          for t, o in sorted(others.items()) if o["repaired"]},
                "proposed_but_failed_the_second_check": sorted(t for t, o in others.items() if o["proposed"] and not o["repaired"]),
                "recalls_with_a_problem": sorted(t for t, o in others.items() if o.get("problem")),
                "recalls_that_lost_a_rule_on_the_way": sorted(t for t, o in others.items() if o["rules_refused_on_the_way"]),
                "lessons_given_and_different_rules_held": {"least": [min(o["lessons_given"] for o in others.values()),
                                                                     min(o["rules_held"] for o in others.values())],
                                                           "most": [max(o["lessons_given"] for o in others.values()),
                                                                    max(o["rules_held"] for o in others.values())]} if others else None,
                "test_runs": sum(o["oracle_calls"] for o in others.values()),
            },
        }
    return out


def code_sha256() -> dict[str, str]:
    files = {"tool": pathlib.Path(__file__),
             "organ_store": REPO / "canonical/swe_kernel/verified_skill_crystallizer_v1.py",
             "organ_contract_and_oracle": REPO / "canonical/swe_kernel/skill_verification_contract_v1.py",
             "organ_scope_learning": REPO / "canonical/swe_kernel/rule_scope_learning_v1.py",
             "organ_operator_generalization": REPO / "canonical/swe_kernel/operator_generalization_v1.py",
             "test_measurement": REPO / "canonical/runtime/bound_capabilities/python_repository_acceptance_measurement_v1.py"}
    return {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in files.items() if path.is_file()}


def benchmark_sha256(root: pathlib.Path, names: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(names):
        for path in (root / "python_programs" / f"{name}.py", root / "correct_python_programs" / f"{name}.py",
                     root / "python_testcases" / f"test_{name}.py", root / "json_testcases" / f"{name}.json"):
            if path.is_file():
                digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--quixbugs-dir", required=True, help="a checkout of github.com/jkoppel/QuixBugs")
    parser.add_argument("--work-dir", help="where the per-program projects and stores are built (default: a temporary directory)")
    parser.add_argument("--programs", nargs="*", help="program names (default: all)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S, help="seconds one run of a program's tests may take")
    parser.add_argument("--settings", nargs="*", default=list(SETTINGS), choices=list(SETTINGS))
    parser.add_argument("--one-fix-teachers", type=int, default=None,
                        help="how many lessons the one-fix question is asked of, drawn at random (default: every lesson)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--census-only", action="store_true")
    parser.add_argument("--census-from", help="a result file whose census is reused instead of being run again")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.quixbugs_dir).resolve()
    names = list(args.programs) if args.programs else program_names(root)
    work = pathlib.Path(args.work_dir).resolve() if args.work_dir else pathlib.Path(tempfile.mkdtemp(prefix="quixbugs-one-fix-"))
    work.mkdir(parents=True, exist_ok=True)
    say = lambda line: print(line, flush=True)  # noqa: E731
    result: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {"source": "github.com/jkoppel/QuixBugs (MIT), python_programs / correct_python_programs / python_testcases",
                        "benchmark_sha256": benchmark_sha256(root, names), "python": sys.version.split()[0],
                        "code_sha256": code_sha256()},
        "parameters": {"timeout_s": args.timeout, "settings": {k: SETTINGS[k] for k in args.settings}, "scope_id": SCOPE,
                       "one_fix_teachers": args.one_fix_teachers, "seed": args.seed,
                       "recall_wall_limit_s": RECALL_WALL_LIMIT_S},
        "producer_cognition_model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    if args.census_only:
        result["census"] = census(root, names, work / "projects", timeout_s=args.timeout, progress=say)
    else:
        checked = None
        if args.census_from:
            earlier = json.loads(pathlib.Path(args.census_from).read_text())
            checked = {name: earlier["census"][name] for name in names}
        measured = measure(root, names, work, timeout_s=args.timeout, settings=args.settings,
                           one_fix_teachers=args.one_fix_teachers, seed=args.seed, checked=checked, progress=say)
        result.update(measured)
        result["summary"] = summarise(measured)
        print(json.dumps(result["summary"], indent=1, sort_keys=True))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
