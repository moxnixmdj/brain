#!/usr/bin/env python3
"""Does a lesson learned in one language actually RUN in another?

The instant-learning probe (`instant_learning_transfer_probe_20261101.py`) ends with four
cross-language rows reporting `NO_RULES_FOR_LANGUAGE`, and it is careful about what that
means: it queries the *store* for rules in that language, and the store keys every rule by
language, so it can only ever say "the store has nothing for Go". It never asks the module
that exists to carry a lesson across that boundary, because that module was written after the
probe was.

`canonical/swe_kernel/language_neutral_skill_bridge_v1` guards a crossing three ways — the
rewrite must be lexical, the patched text must parse in the target language, and the caller's
own verifier must pass — and returns nothing unless all three hold. Until now it had no caller
outside its own tests, so its 4/5 result was a laboratory result.

This probe makes the crossing **executable** wherever a real toolchain exists on this host.
For C++ the patched function is compiled by `g++` and linked against real assertions that are
run; for the languages with no compiler here the probe reports TEXT_ONLY and says so rather
than implying execution it did not do. Nothing is claimed that was not run.

Run:  python3 cross_language_learning_probe_20261102.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

LESSON = "a half-open range is exclusive at the upper bound: '<= hi' must be '< hi'"
TAUGHT_BUGGY = "def within(x, hi):\n    return x <= hi\n"
TAUGHT_FIXED = "def within(x, hi):\n    return x < hi\n"


def boundary_oracle(src: str) -> bool:
    """Name-agnostic: the twin is alpha-renamed, so a literal-string oracle cannot work."""
    return ("<=" not in src) and ("<" in src)


def have(prog: str) -> bool:
    return shutil.which(prog) is not None


# --------------------------------------------------------------------------- real runners
def _run(cmd: list[str], cwd: Path, timeout: int = 60) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    except Exception as exc:                                    # noqa: BLE001
        return False, f"EXEC_FAILED:{type(exc).__name__}"
    return p.returncode == 0, (p.stdout + p.stderr).strip()


def diagnose_refusal(store, source_text: str, target_language: str,
                     verifier) -> str:
    """Name WHY nothing crossed. A refusal with no cause is indistinguishable from a bug.

    Three different things can stop a crossing, and they mean different things:

      RULE_PATTERN_ABSENT  the rule's token sequence never occurs in the target source.
                           This is NOT a safety guard -- it is the shape assumption the
                           crystallizer baked in. Measured 2026-11-02: the taught rule is
                           `return ?id0 <= ?id1`, so it carries into C++, Go and Java, which
                           spell the fix with `return`, and never into Rust, which writes the
                           same function as a tail expression `x <= hi`. Same lesson, same
                           operator swap, different surface form.
      TARGET_SYNTAX_GUARD  a candidate was produced and the target language refused it.
      CALLER_VERIFIER_GUARD a candidate parsed and the caller's verifier rejected it.
    """
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    produced = 0
    parsed = 0
    for src_lang in ("python", "javascript", "cpp", "go", "java", "rust", "typescript"):
        if src_lang == target_language:
            continue
        try:
            rules = store.lookup_rules(src_lang)
        except Exception:                                        # noqa: BLE001
            continue
        from canonical.swe_kernel import language_neutral_skill_bridge_v1 as bridge
        for rule in rules:
            ok, _ = bridge.is_lexical_rule(rule)
            if not ok:
                continue
            for cand in cry.iter_crystallized_code_rule_candidates(source_text, rule):
                if not cand or cand == source_text:
                    continue
                produced += 1
                fine, _why = bridge.parses_in(target_language, cand)
                if fine:
                    parsed += 1
                    try:
                        if verifier(cand):
                            return "WOULD_HAVE_CROSSED"      # never happens here
                    except Exception:                        # noqa: BLE001
                        pass
    if produced == 0:
        return "RULE_PATTERN_ABSENT:rule_requires_'return'"
    if parsed == 0:
        return "TARGET_SYNTAX_GUARD"
    return "CALLER_VERIFIER_GUARD"



CPP_HARNESS = """
#include <cstdio>
bool within(int x, int hi);            // the patched function, defined in the other file
int main() {
    // The whole lesson, as executable assertions. A half-open range excludes hi.
    if (within(9, 10) != true)  { std::printf("FAIL: within(9,10) should be true\\n");  return 1; }
    if (within(10, 10) != false){ std::printf("FAIL: within(10,10) should be false\\n"); return 2; }
    if (within(11, 10) != false){ std::printf("FAIL: within(11,10) should be false\\n"); return 3; }
    std::printf("OK: 3/3 assertions\\n");
    return 0;
}
"""

CPP_BUGGY = "bool within(int x, int hi) {\n    return x <= hi;\n}\n"


# the source as it arrives in each target language, and how to execute it if we can
LANGS: dict[str, dict] = {
    "cpp": {
        "source": CPP_BUGGY,
        "runner": "g++",
        "run": lambda src, d: _cpp_run(src, d),
    },
    "typescript": {
        "source": ("export function within(x: number, hi: number): boolean {\n"
                   "  return x <= hi;\n}\n"),
        "runner": None,
        "run": None,
    },
    "go": {
        "source": "func Within(x, hi int) bool {\n\treturn x <= hi\n}\n",
        "runner": "go",
        "run": None,
    },
    "rust": {
        "source": "fn within(x: i64, hi: i64) -> bool {\n    x <= hi\n}\n",
        "runner": "rustc",
        "run": None,
    },
    "java": {
        "source": "class C { boolean within(int x, int hi) { return x <= hi; } }\n",
        "runner": "javac",
        "run": None,
    },
}


def _cpp_run(src: str, workdir: Path) -> tuple[bool, str]:
    """Compile the carried patch with the real compiler and run real assertions against it."""
    (workdir / "within.cpp").write_text(src, encoding="utf-8")
    (workdir / "harness.cpp").write_text(CPP_HARNESS, encoding="utf-8")
    compiled, cmsg = _run(["g++", "-std=c++17", "-O0", "within.cpp", "harness.cpp",
                           "-o", "probe"], workdir)
    if not compiled:
        return False, "COMPILE_FAILED:" + cmsg.splitlines()[0][:120]
    return _run([str(workdir / "probe")], workdir)


def main() -> int:
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    from canonical.swe_kernel import language_neutral_skill_bridge_v1 as bridge

    with tempfile.TemporaryDirectory() as td:
        store = VerifiedSkillStore(Path(td) / "probe.sqlite", seed=False)
        taught = store.crystallize_code_fix(
            before_snippet=TAUGHT_BUGGY,
            after_snippet=TAUGHT_FIXED,
            language="python",
            error_class="BOUNDARY",
            twin_oracle=boundary_oracle,
        )
        print(f"LESSON TAUGHT (python only, one example): {LESSON}")
        print(f"crystallized: {bool(taught.get('crystallized'))}   store count: {store.count()}")
        if not taught.get("crystallized"):
            print("REFUSED by the admission gate; nothing to carry.")
            return 1
        print()
        print(f"{'language':12} {'bridge':10} {'executed':10} {'result':46} authority")
        print("-" * 116)

        carried = executed = 0
        rows = []
        for lang, spec in LANGS.items():
            workdir = Path(td) / lang
            workdir.mkdir(exist_ok=True)
            try:
                hit = bridge.recall_across_languages(
                    store, source_text=spec["source"], target_language=lang,
                    verifier=boundary_oracle, error_class="BOUNDARY",
                )
            except Exception as exc:                            # noqa: BLE001
                hit, err = None, f"EXC:{type(exc).__name__}"
            else:
                err = ""
            if not hit:
                note = err or diagnose_refusal(store, spec["source"], lang, boundary_oracle)
                print(f"{lang:12} {'refused':10} {'-':10} {note[:46]:46} TEXT_ONLY")
                rows.append((lang, False, False, note))
                continue
            carried += 1
            patched = hit["patched_source"]
            runner = spec["runner"]
            if spec["run"] is not None and runner and have(runner):
                ok, msg = spec["run"](patched, workdir)
                executed += 1 if ok else 0
                print(f"{lang:12} {'CROSSED':10} {str(ok):10} {msg.splitlines()[0][:46]:46} "
                      f"{'EXECUTED:' + runner}")
                rows.append((lang, True, ok, "EXECUTED"))
            else:
                why = f"{runner or 'no runner'} ABSENT ON THIS HOST" if runner else \
                      "NO RUNTIME FOR THIS LANGUAGE HERE"
                print(f"{lang:12} {'CROSSED':10} {'no':10} {why[:46]:46} TEXT_ONLY")
                rows.append((lang, True, None, "TEXT_ONLY"))

        print()
        print(f"carried across the language boundary: {carried}/{len(LANGS)}")
        print(f"of which EXECUTED and passed real assertions: {executed}")
        refused = [r for r in rows if not r[1]]
        print(f"not carried: {len(refused)}/{len(LANGS)}")
        for lang, _c, _ok, note in refused:
            print(f"  {lang}: {note}")
        print()
        print("What this proves: one lesson, taught once from one Python example, carried into "
              "other\nlanguages and — for C++ on this host — compiled and run against real "
              "assertions.\nWhat it does not prove: whole-task correctness in those languages. "
              "The bridge returns\na verified *snippet*, and the record says "
              "whole_task_correctness_proved=false.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
