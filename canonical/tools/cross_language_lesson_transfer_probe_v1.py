#!/usr/bin/env python3
"""One lesson, taught once, admitted in other languages — verified by their own toolchains.

THE CLAIM UNDER TEST

    "Give the model the most advanced coding actions, let it experience them
     once, and it learns them permanently."

Today's measured wall (`INSTANT_LEARNING_AND_COMPUTER_USE_VERDICT_20261112_V1.md`
§2/W1) is that a crystallized lesson is *retrieved* by language: a Python lesson is
offered to `python` and to nothing else, even though the lesson itself is an
operator rewrite with parameter holes and contains no Python.

Two possible reasons, and they need different work:

  (a) THE STORE IS THE WALL. The rule is language-free; `WHERE language = ?` is
      the only thing hiding it. Then the fix is a retrieval predicate plus a
      per-language acceptance gate, and this file can demonstrate it today.
  (b) THE PROPOSER IS THE WALL. `propose_operator_swaps` only works on text that
      looks like the language the rule was learned in. Then the fix is research.

METHOD

  1. Teach ONE lesson in Python through `VerifiedSkillStore.crystallize_code_fix`
     and keep the admitted rule object.
  2. For each target language, write the SAME bug in that language's idiom.
  3. Ask the store for a lesson in that language. Record what it offers --
     this is the wall, stated as a number.
  4. Ask the *proposer* for candidates from the Python rule on that source.
  5. Gate every candidate by EXECUTING it in that language's real toolchain
     (node / gcc / g++ / python3) against the taught semantics. A candidate that
     does not compile, does not run, or does not produce the taught answers is
     refused. Nothing is admitted on the strength of the diff looking right.
  6. Two negative controls per language, both of which MUST be refused:
       already-correct  -- the function already has the taught semantics
       unrelated-bug    -- a real bug, but not this one

WHAT THIS DOES AND DOES NOT SHOW

* It shows the store's language key is the wall and the proposer is not, for the
  languages whose toolchains exist on this machine. It does not show that every
  lesson in the bank is operator-shaped; it shows that THIS one is, and that the
  admission gate can be made real rather than syntactic.
* It does NOT claim the rule is "language-free". It records the languages in
  which the rule has actually been *verified*, which is the only honest sense in
  which a lesson is cross-language.
* It does NOT modify the shipped store. It composes the pieces that already
  exist, so the measurement is of present capability rather than of a plan.
* Absent toolchains are reported as ABSENT, never as a pass. On a machine with
  no `go` or `rustc`, Go and Rust are unmeasured -- not refused, not admitted.

Authority: NONE. Producer-run measurement on constructed fixtures.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POINTS = [(-2, -2), (-1, 0), (0, 0), (0, 3), (3, 3), (4, 3), (10, 10), (9, 10)]
# The taught semantics: "within" is EXCLUSIVE. Integer-only so every language
# below can express the same test without float formatting questions.
EXPECTED_EXCLUSIVE = [(x, h, x < h) for x, h in POINTS]

TEACH_BEFORE = "def within(x, hi):\n    return x <= hi\n"
TEACH_AFTER = "def within(x, hi):\n    return x < hi\n"


# --------------------------------------------------------------------------- #
# the lesson, exactly as the shipped store admits it
# --------------------------------------------------------------------------- #
def teach_python_lesson(db: Path):
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

    def twin(source: str) -> bool:
        try:
            ns: dict = {}
            exec(compile(source, "<python-twin>", "exec"), ns)  # noqa: S102
            fn = next(v for v in ns.values() if callable(v) and not isinstance(v, type))
            return all(fn(x, h) is (x < h) for x, h in POINTS)
        except Exception:  # noqa: BLE001
            return False

    store = VerifiedSkillStore(db_path=db, seed=False)
    result = store.crystallize_code_fix(
        before_snippet=TEACH_BEFORE, after_snippet=TEACH_AFTER,
        language="python", error_class="BOUNDARY", twin_oracle=twin,
    )
    if not result.get("crystallized"):
        raise RuntimeError("LESSON_NOT_ADMITTED:" + str(result.get("reason")))
    rules = store.lookup_rules("python", "BOUNDARY")
    if len(rules) != 1:
        raise RuntimeError("EXPECTED_EXACTLY_ONE_LESSON")
    return store, rules[0]


# --------------------------------------------------------------------------- #
# a real toolchain is the only oracle allowed to admit a lesson
# --------------------------------------------------------------------------- #
def _run(cmd, cwd, timeout=60):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _python_gate(source: str, workdir: Path) -> tuple[bool, str]:
    script = workdir / "candidate.py"
    script.write_text(source + "\n\n" + _python_driver(), encoding="utf-8")
    proc = _run([sys.executable, "-B", str(script)], workdir)
    if proc is None:
        return False, "python:did-not-run"
    if proc.returncode != 0:
        return False, "python:" + (proc.stderr.strip().splitlines() or ["error"])[-1][:120]
    return proc.stdout.strip() == "OK", "python:" + proc.stdout.strip()[:40]


def _python_driver() -> str:
    rows = ",".join("(%d,%d,%s)" % (x, h, "True" if want else "False") for x, h, want in EXPECTED_EXCLUSIVE)
    return (
        "CASES=[%s]\n"
        "def _check():\n"
        "    for x,h,want in CASES:\n"
        "        if bool(within(x,h)) is not want:\n"
        "            return 'FAIL %%r' %% ((x,h,want),)\n"
        "    return 'OK'\n"
        "print(_check())\n" % rows
    )


def _node_gate(source: str, workdir: Path) -> tuple[bool, str]:
    script = workdir / "candidate.js"
    script.write_text(source + "\n\n" + _node_driver(), encoding="utf-8")
    proc = _run(["node", str(script)], workdir)
    if proc is None:
        return False, "node:did-not-run"
    if proc.returncode != 0:
        return False, "node:" + (proc.stderr.strip().splitlines() or ["error"])[-1][:120]
    return proc.stdout.strip() == "OK", "node:" + proc.stdout.strip()[:40]


def _node_driver() -> str:
    rows = ",".join("[%d,%d,%s]" % (x, h, "true" if want else "false") for x, h, want in EXPECTED_EXCLUSIVE)
    return (
        "const CASES=[%s];\n"
        "let bad=null;\n"
        "for (const [x,h,want] of CASES) { if (Boolean(within(x,h)) !== want) { bad=[x,h,want]; } }\n"
        "console.log(bad === null ? 'OK' : 'FAIL ' + JSON.stringify(bad));\n" % rows
    )


def _c_family_gate(source: str, workdir: Path, compiler: str, ext: str) -> tuple[bool, str]:
    """Compile AND run. A candidate that merely parses is not a candidate."""
    program = workdir / ("candidate" + ext)
    program.write_text(source + "\n\n" + _c_driver(), encoding="utf-8")
    binary = workdir / ("candidate" + ext + ".bin")
    build = _run([compiler, "-std=c11" if compiler == "gcc" else "-std=c++17",
                  "-O0", "-w", "-o", str(binary), str(program)], workdir)
    if build is None:
        return False, "%s:did-not-run" % compiler
    if build.returncode != 0:
        first = (build.stderr.strip().splitlines() or ["error"])[0]
        return False, "%s:compile:%s" % (compiler, first[:100])
    run = _run([str(binary)], workdir)
    if run is None or run.returncode != 0:
        return False, "%s:did-not-run" % compiler
    return run.stdout.strip() == "OK", "%s:%s" % (compiler, run.stdout.strip()[:40])


def _c_driver() -> str:
    rows = ",\n".join("    {%d, %d, %d}" % (x, h, 1 if want else 0) for x, h, want in EXPECTED_EXCLUSIVE)
    return (
        "#include <stdio.h>\n"
        "typedef struct { int x; int h; int want; } Case;\n"
        "int main(void) {\n"
        "  static const Case CASES[] = {\n%s\n  };\n"
        "  int bad = 0;\n"
        "  for (unsigned i = 0; i < sizeof(CASES)/sizeof(CASES[0]); i++) {\n"
        "    int got = within(CASES[i].x, CASES[i].h) ? 1 : 0;\n"
        "    if (got != CASES[i].want) bad = 1;\n"
        "  }\n"
        "  printf(bad ? \"FAIL\" : \"OK\");\n"
        "  return 0;\n"
        "}\n" % rows
    )


# --------------------------------------------------------------------------- #
# per-language fixtures: the SAME bug, written the way that language writes it
# --------------------------------------------------------------------------- #
LANGUAGES = {
    "python": {
        "toolchain": sys.executable,
        "buggy": "def within(x, hi):\n    return x <= hi\n",
        "correct": "def within(x, hi):\n    return x < hi\n",
        "unrelated": "def within(x, hi):\n    return x >= hi\n",
        "gate": _python_gate,
    },
    "javascript": {
        "toolchain": "node",
        "buggy": "function within(x, hi) {\n  return x <= hi;\n}\n",
        "correct": "function within(x, hi) {\n  return x < hi;\n}\n",
        "unrelated": "function within(x, hi) {\n  return x >= hi;\n}\n",
        "gate": _node_gate,
    },
    "c": {
        "toolchain": "gcc",
        "buggy": "int within(int x, int hi) {\n    return x <= hi;\n}\n",
        "correct": "int within(int x, int hi) {\n    return x < hi;\n}\n",
        "unrelated": "int within(int x, int hi) {\n    return x >= hi;\n}\n",
        "gate": lambda s, w, ext=".c", comp="gcc": _c_family_gate(s, w, comp, ext),
    },
    "cpp": {
        "toolchain": "g++",
        "buggy": "bool within(int x, int hi) {\n    return x <= hi;\n}\n",
        "correct": "bool within(int x, int hi) {\n    return x < hi;\n}\n",
        "unrelated": "bool within(int x, int hi) {\n    return x >= hi;\n}\n",
        "gate": lambda s, w, ext=".cpp", comp="g++": _c_family_gate(s, w, comp, ext),
    },
    "go": {
        "toolchain": "go",
        "buggy": "package main\n\nfunc within(x, hi int) bool {\n\treturn x <= hi\n}\n",
        "correct": "package main\n\nfunc within(x, hi int) bool {\n\treturn x < hi\n}\n",
        "unrelated": "package main\n\nfunc within(x, hi int) bool {\n\treturn x >= hi\n}\n",
        "gate": None,   # no go toolchain on this machine: reported ABSENT, never a pass
    },
    "rust": {
        "toolchain": "rustc",
        "buggy": "fn within(x: i32, hi: i32) -> bool {\n    x <= hi\n}\n",
        "correct": "fn within(x: i32, hi: i32) -> bool {\n    x < hi\n}\n",
        "unrelated": "fn within(x: i32, hi: i32) -> bool {\n    x >= hi\n}\n",
        "gate": None,   # no rustc on this machine
    },
}


def _propose(source: str, rule, language: str) -> list[str]:
    from canonical.swe_kernel import operator_generalization_v1 as op

    try:
        return list(op.propose_operator_swaps(source, rule, language=language))
    except TypeError:
        return list(op.propose_operator_swaps(source, rule))


def measure() -> dict:
    db_dir = Path(tempfile.mkdtemp(prefix="brain_xlang_store_"))
    store, rule = teach_python_lesson(db_dir / "skills.sqlite")
    lesson = {
        "skill_id": rule.get("skill_id"),
        "language_learned_in": rule.get("language"),
        "error_class": rule.get("error_class"),
        "pattern_tokens": rule.get("pattern_tokens"),
        "replacement_tokens": rule.get("replacement_tokens"),
    }

    rows = {}
    for language, spec in LANGUAGES.items():
        offered = len(store.lookup_rules(language, "BOUNDARY"))
        present = spec["gate"] is not None and (
            Path(spec["toolchain"]).is_file() if "/" in str(spec["toolchain"])
            else shutil.which(str(spec["toolchain"])) is not None)
        row = {
            "offered_by_store": offered,
            "toolchain": spec["toolchain"],
            "toolchain_present": bool(present),
            "proposed_on_buggy": 0, "admitted_by_toolchain": 0, "gate_evidence": None,
            "controls": {},
            "verdict": None,
        }
        candidates = _propose(spec["buggy"], rule, language)
        row["proposed_on_buggy"] = len(candidates)
        workdir = Path(tempfile.mkdtemp(prefix="brain_xlang_%s_" % language))
        admitted, evidence = 0, []
        if present:
            for candidate in candidates:
                ok, why = spec["gate"](candidate, workdir)
                if ok:
                    admitted += 1
                    evidence.append(why)
        row["admitted_by_toolchain"] = admitted
        row["gate_evidence"] = evidence[:3] or None

        # The controls exist to make "admitted" mean something. Both must be refused.
        for label, field in (("already_correct", "correct"), ("unrelated_bug", "unrelated")):
            proposals = _propose(spec[field], rule, language)
            if not present:
                row["controls"][label] = {"proposed": len(proposals), "accepted": None,
                                          "reason": "TOOLCHAIN_ABSENT"}
                continue
            accepted = [c for c in proposals if spec["gate"](c, workdir)[0]]
            row["controls"][label] = {"proposed": len(proposals), "accepted": len(accepted),
                                      "reason": "REFUSED_BY_TOOLCHAIN" if not accepted else "ACCEPTED"}

        if not present:
            row["verdict"] = "UNMEASURED_TOOLCHAIN_ABSENT"
        elif admitted == 0:
            row["verdict"] = "PROPOSER_IS_THE_WALL"
        elif row["controls"]["already_correct"]["accepted"] or row["controls"]["unrelated_bug"]["accepted"]:
            row["verdict"] = "ADMITTED_BUT_NOT_NARROW"
        else:
            row["verdict"] = "LESSON_TRANSFERS_AND_STAYS_NARROW"
        rows[language] = row

    return {
        "schema": "BRAIN_CROSS_LANGUAGE_LESSON_TRANSFER_V1",
        "authority": "NONE",
        "scope": ("one operator-shaped boundary lesson taught in Python; six languages attempted, "
                  "admitted only where that language's own compiler/interpreter runs the candidate"),
        "lesson": lesson,
        "languages": rows,
        "summary": {
            "measured": [k for k, v in rows.items() if v["verdict"] != "UNMEASURED_TOOLCHAIN_ABSENT"],
            "unmeasured": [k for k, v in rows.items() if v["verdict"] == "UNMEASURED_TOOLCHAIN_ABSENT"],
            "transferred_and_narrow": [k for k, v in rows.items()
                                       if v["verdict"] == "LESSON_TRANSFERS_AND_STAYS_NARROW"],
            "store_offered_any_non_python": any(v["offered_by_store"] for k, v in rows.items()
                                                if k != "python"),
        },
    }


def main() -> int:
    started = time.perf_counter()
    report = measure()
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
    if len(sys.argv) == 3 and sys.argv[1] == "--json":
        Path(sys.argv[2]).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
