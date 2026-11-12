#!/usr/bin/env python3
"""One demonstration: what does it actually buy, where does it stop, and what did we already claim?

The owner's question, in its sharpest form:

    "Why can't we just give our model the most advanced coding actions and let him experience
     them once and then he will learn them? Can't we do this now?"

Previous rounds answered this by argument and by measuring other mechanisms. This tool asks the
tree's OWN "learn it once, keep it forever" layer, in the order a user would hit it:

  1. `solve_or_learn(...)` -- the front door the repository itself points at as the instant-learning
     system. One ordinary request, both flag settings.
  2. The write path that actually stores a repair lesson
     (`verified_skill_crystallizer_v1.VerifiedSkillStore`), on three languages, each taught once.
  3. **The surface/meaning split**: one lesson from ONE demonstration, then six targets. Two of them
     matter -- a target whose *surface* matches but whose meaning differs, and a target with the
     *same meaning* (an off-by-one) whose surface differs.
  4. Process death: does the lesson survive a fresh interpreter, and what does it do on return.

Everything here runs in temporary directories, calls no model, uses no network, spends $0, writes
nothing into the repository, registers no capability and flips no family. `truth.achieved` stays
`false`. Authority: **NONE**.

Run from anywhere:
    python3 canonical/tools/one_lesson_one_kind_probe_20261112_v1.py
    python3 canonical/tools/one_lesson_one_kind_probe_20261112_v1.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: The one demonstration. A real one-line repair, of the kind the store is built for.
BEFORE = "def below_limit(n):\n    return n <= 10\n"
AFTER = "def below_limit(n):\n    return n < 10\n"

#: Six targets, ordered by how much they ask of one demonstration.
TARGETS: list[tuple[str, str, str]] = [
    ("same kind, surface matches",
     "surface",
     "def other(n):\n    return n <= 999\n"),
    ("same kind, different variable",
     "surface",
     "def cap(total):\n    return total <= 3\n"),
    ("surface matches, MEANING DIFFERS (a <= that is required)",
     "meaning",
     "def allows_edge(x):\n    return x <= 60\n"),
    ("SAME MEANING, different surface (off-by-one in range)",
     "meaning",
     "def walk(n):\n    for i in range(n + 1):\n        yield i\n"),
    ("same meaning, different language (Rust)",
     "kind",
     "fn below_limit(n: usize) -> bool {\n    n <= 10\n}\n"),
    ("different kind entirely (return-path fix)",
     "kind",
     "def get(d, k):\n    return d[k]\n"),
]

#: Three languages, each taught ONCE, to see whether the write path is language-bound.
POLYGLOT: list[tuple[str, str, str, str]] = [
    ("python", "py_repair", BEFORE, AFTER),
    ("rust", "rust_repair",
     "pub fn sum_slice(xs: &[i32]) -> i32 {\n    let mut total = 0;\n    for i in xs {\n"
     "        total += i;\n    }\n    total\n}\n",
     "pub fn sum_slice(xs: &[i32]) -> i32 {\n    let mut total = 0;\n    for i in xs.iter() {\n"
     "        total += i;\n    }\n    total\n}\n"),
    ("go", "go_repair",
     "package main\nfunc main() {\n\tvar m map[string]int\n\tm[\"a\"] = 1\n}\n",
     "package main\nfunc main() {\n\tm := make(map[string]int)\n\tm[\"a\"] = 1\n}\n"),
]


def _front_door() -> dict[str, Any]:
    """One ordinary request through the mechanism the repository says is the answer."""
    out: dict[str, Any] = {}
    try:
        from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn

        res = solve_or_learn("Add two numbers in Python", learn=True)
        out["default"] = {
            "status": res.get("status"),
            "tier_used": res.get("tier_used"),
            "pass": res.get("pass"),
            "skill_id": res.get("skill_id"),
        }
        res2 = solve_or_learn("Add two numbers in Python", learn=True, confinement_admitted=True)
        out["confinement_admitted_true"] = {
            "status": res2.get("status"),
            "tier_used": res2.get("tier_used"),
            "pass": res2.get("pass"),
        }
    except Exception as exc:  # a front door that raises is a finding, not a crash
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def _write_path(tmp: pathlib.Path) -> dict[str, Any]:
    """Does the store keep a lesson from one demonstration? Three languages, one lesson each."""
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    rows: list[dict[str, Any]] = []
    tmp.mkdir(parents=True, exist_ok=True)
    for language, error_class, before, after in POLYGLOT:
        store = cry.VerifiedSkillStore(tmp / f"{language}.sqlite")
        before_count = store.count()
        rec = store.crystallize_verified_fix(language, error_class, before, after, "ONE_DEMONSTRATION")
        after_count = store.count()
        # A store seeded from the repository's own bundle may already hold this exact rule:
        # then the return value says "crystallized" but nothing was *learned*, only reinforced.
        rows.append({
            "language": language,
            "crystallized": rec is not None,
            "skill_id": (rec or {}).get("skill_id"),
            "store_before": before_count,
            "store_after": after_count,
            "newly_learned": after_count > before_count,
            "reinforced_shipped_rule": rec is not None and after_count == before_count,
        })
    return {"per_language": rows}


def _surface_vs_meaning(tmp: pathlib.Path) -> dict[str, Any]:
    """ONE lesson, six targets, and the two that decide the question."""
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    rule = cry.anti_unify_code_rule(BEFORE, AFTER, language="python", error_class="py_repair")
    out: dict[str, Any] = {
        "rule_pattern": [t[1] for t in (rule or {}).get("pattern_tokens", [])],
        "rule_replacement": [t[1] for t in (rule or {}).get("replacement_tokens", [])],
        "twin_verified": bool(cry.verify_rule_on_mutated_twin(BEFORE, rule)) if rule else False,
        "targets": [],
    }
    for label, asked_for, src in TARGETS:
        rewritten = cry.apply_crystallized_code_rule(src, rule) if rule else None
        out["targets"].append({
            "label": label,
            "asks": asked_for,
            "fired": rewritten is not None,
            "result_line": (
                rewritten.rstrip().splitlines()[-1].strip() if rewritten else None
            ),
            "changed_input_text": rewritten is not None and rewritten != src,
        })
    return out


_CHILD = r'''
import json, pathlib, sys
sys.path.insert(0, r"{root}")
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry
store = cry.VerifiedSkillStore(pathlib.Path(r"{db}"))
src = "def other(n):\n    return n <= 999\n"
print(json.dumps({{
    "count": store.count(),
    "seed_result": store.seed_result,
    "fired_with_oracle": store.recall_and_apply_verified(
        source_text=src, language="python", error_class="py_repair",
        verifier=lambda c: "n < 999" in c and "<=" not in c) is not None,
    "fired_without_check": store.recall_and_apply_verified(
        source_text=src, language="python", error_class="py_repair",
        verifier=lambda c: True) is not None,
}}))
'''


def _survives_process_death(tmp: pathlib.Path) -> dict[str, Any]:
    """A lesson in one interpreter, read back in a fresh one, and re-checked on return."""
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    tmp.mkdir(parents=True, exist_ok=True)
    db = tmp / "survive.sqlite"
    store = cry.VerifiedSkillStore(db)
    store.crystallize_verified_fix("python", "py_repair", BEFORE, AFTER, "ONE_DEMONSTRATION")
    learned_here = store.count()
    child = subprocess.run(
        [sys.executable, "-c", _CHILD.format(root=str(ROOT), db=str(db))],
        capture_output=True, text=True, timeout=120,
    )
    out: dict[str, Any] = {"learned_in_parent": learned_here, "child_returncode": child.returncode}
    if child.returncode == 0:
        out.update(json.loads(child.stdout.strip().splitlines()[-1]))
    else:
        out["child_stderr_tail"] = child.stderr.strip().splitlines()[-3:]
    return out


#: A new environment has no tests. The only oracle is "it still compiles". Is that enough?
COMPILE_ONLY_BEFORE = "def scale(xs, k):\n    return [x * k for x in xs]\n"
COMPILE_ONLY_WRONG = "def scale(xs, k):\n    return [x + k for x in xs]\n"


def _oracle_is_the_missing_piece(tmp: pathlib.Path) -> dict[str, Any]:
    """Store a wrong-but-compiling 'lesson' under a compile-only oracle, then recall it."""
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    tmp.mkdir(parents=True, exist_ok=True)
    store = cry.VerifiedSkillStore(tmp / "compile_only.sqlite")
    rec = store.crystallize_verified_fix("python", "compile_only_repair",
                                         COMPILE_ONLY_BEFORE, COMPILE_ONLY_WRONG, "COMPILE_ONLY")
    hit = store.recall_and_apply_verified(
        source_text="def scale2(xs, k):\n    return [x * k for x in xs]\n",
        language="python", error_class="compile_only_repair",
        verifier=lambda c: compile(c, "<candidate>", "exec") is not None,
    )
    return {
        "wrong_lesson_accepted": rec is not None,
        "wrong_lesson_reproduced_on_new_source": hit is not None,
        "reproduced_line": (hit or {}).get("patched_source", "").strip().splitlines()[-1]
        if hit else None,
        "note": "no test existed in this environment; 'compiles' was the only available oracle",
    }


def _what_was_already_claimed() -> dict[str, Any]:
    """The note on `main` answers this question with YES. Check its factual claims against the tree."""
    note = ROOT / "YOU_WERE_RIGHT_ALL_ALONG.md"
    bundle_p = ROOT / "canonical/astra_runtime/skills/VERIFIED_SKILLS_BUNDLE_V1.json"
    workflows_p = ROOT / "canonical/astra_runtime/skills/COMPILED_WORKFLOWS_BUNDLE_V1.json"
    out: dict[str, Any] = {"note_present": note.is_file()}
    if bundle_p.is_file():
        out["verified_skills_bundle_rule_count"] = json.loads(
            bundle_p.read_text(encoding="utf-8")).get("rule_count")
    if workflows_p.is_file():
        out["compiled_workflows_skill_count"] = json.loads(
            workflows_p.read_text(encoding="utf-8")).get("skill_count")
    if note.is_file():
        text = note.read_text(encoding="utf-8")
        out["note_claims_bundle_empty"] = "0 skills" in text or "is EMPTY" in text
        out["note_says_solve_or_learn_works"] = "you were right" in text.lower()
    return out


def measure() -> dict[str, Any]:
    out: dict[str, Any] = {"schema": "ONE_LESSON_ONE_KIND_PROBE_V1", "authority": "NONE"}
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        out["front_door"] = _front_door()
        out["write_path"] = _write_path(tmp / "write")
        out["surface_vs_meaning"] = _surface_vs_meaning(tmp)
        out["survives_process_death"] = _survives_process_death(tmp / "survive")
        out["oracle_is_the_missing_piece"] = _oracle_is_the_missing_piece(tmp / "compile_only")
    out["already_claimed"] = _what_was_already_claimed()
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = measure()
    print("one lesson, one kind  --  authority NONE, temp dirs only, $0, zero model\n")

    fd = result["front_door"]
    print("1. FRONT DOOR (solve_or_learn, one ordinary request)")
    for key in ("default", "confinement_admitted_true"):
        if key in fd:
            row = fd[key]
            print(f"   {key:26s} {row['status']}")
            print(f"   {'':26s} tier={row['tier_used']} pass={row['pass']}")
    if "error" in fd:
        print("   ERROR", fd["error"])

    print("\n2. WRITE PATH (one demonstration per language)")
    for row in result["write_path"]["per_language"]:
        verdict = ("NEW LESSON" if row["newly_learned"]
                   else "ALREADY SHIPPED (reinforced)" if row["reinforced_shipped_rule"]
                   else "not learned")
        print(f"   {row['language']:10s} {str(row['crystallized']):5s} "
              f"{row['store_before']}->{row['store_after']}  {verdict:26s} id={row['skill_id']}")

    sm = result["surface_vs_meaning"]
    print("\n3. ONE LESSON -> SIX TARGETS")
    print(f"   rule: {' '.join(sm['rule_pattern'])}  ->  {' '.join(sm['rule_replacement'])}")
    print(f"   twin verified: {sm['twin_verified']}")
    for t in sm["targets"]:
        mark = "FIRED   " if t["fired"] else "refused "
        print(f"   {mark} [{t['asks']:7s}] {t['label']}")
        if t["fired"]:
            print(f"            -> {t['result_line']}")

    sd = result["survives_process_death"]
    print("\n4. PROCESS DEATH")
    print(f"   learned in parent {sd['learned_in_parent']} | fresh interpreter sees "
          f"{sd.get('count')}")
    print(f"   fires with a checking oracle : {sd.get('fired_with_oracle')}")
    print(f"   fires with a vacuous oracle  : {sd.get('fired_without_check')}")

    om = result["oracle_is_the_missing_piece"]
    print("\n5. THE NEW-ENVIRONMENT CASE (no tests; 'it compiles' is the only oracle)")
    print(f"   wrong-but-compiling lesson stored   {om['wrong_lesson_accepted']}")
    print(f"   later reproduced on a fresh source  {om['wrong_lesson_reproduced_on_new_source']}")
    print(f"   -> {om['reproduced_line']}   (the original was [x * k for x in xs])")

    ac = result["already_claimed"]
    print("\n6. WHAT WAS ALREADY CLAIMED (YOU_WERE_RIGHT_ALL_ALONG.md, on main)")
    print(f"   note present on main                    {ac['note_present']}")
    print(f"   note says 'the skills bundle is EMPTY'  {ac.get('note_claims_bundle_empty')}")
    print(f"   actual VERIFIED_SKILLS_BUNDLE rule_count {ac.get('verified_skills_bundle_rule_count')}")
    print(f"   actual COMPILED_WORKFLOWS skill_count    {ac.get('compiled_workflows_skill_count')}")
    print(f"   note answers the owner with YES          {ac.get('note_says_solve_or_learn_works')}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("\nWROTE", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
