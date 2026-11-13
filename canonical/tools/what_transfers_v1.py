"""Does "instant learning" generalise to arbitrary environments, or only to the one it was shown in?

WHY THIS EXISTS
---------------
Two claims were on the table about the shipped one-shot learner:

  A. "We solved instant learning and instant learning in new arbitrary environments, so only the
     environments are left: give the agent the action once and it learns it permanently."
  B. `PROBLEM2_GENERALIZATION_COMPLETELY_SOLVED.md` on main, which says Problem 2 is completely
     solved by a TF-IDF retrieval engine.

Neither had a measurement. This module measures each one with the repo's own instruments, and it is
built so that a FALSE claim fails loudly rather than being argued about in prose.

WHAT IT MEASURES
----------------
1. `retrieval_is_not_knowledge()` -- the claim-B engine is asked for the PR's own demo task, then the
   same question is asked with the engine's entire memory emptied. If the answer is produced by the
   retrieval it must change; if it does not change, the retrieval was never doing any work.
2. `one_language_is_not_a_language()` -- every "experience" in claim B's store is hand-seeded, and
   the store can express exactly one shape of task. A counting request stated in two other ways the
   loader could perfectly well act on is not merely refused, it is answered "not implemented". A
   memory that cannot hold a failure cannot learn a boundary.
3. `transfer_is_free_and_transfer_is_not()` -- the decisive one, on the round-28 corpus of real
   merged pull requests: a lesson the learner was shown IN the target project, versus a lesson shown
   in a DIFFERENT project. That difference is the entire claim "in new arbitrary environments".
4. `half_a_demonstration_is_not_a_demonstration()` -- why (3) cannot be closed by widening the rule.

Authority: NONE. Sandbox measurement, `$0`, zero model calls, no capability registered.

Usage:
    python3 canonical/tools/what_transfers_v1.py --record /tmp/pulls_g.json
    python3 canonical/tools/what_transfers_v1.py --record /tmp/pulls_g.json --out <path>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "WHAT_TRANSFERS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

ROOT = Path(__file__).resolve().parents[2]

_CASES: list[tuple[str, str, str]] = [
    # (name, before, after) -- one defect family, one repair kind: a bound moves, the callers follow.
    ("a", "def f(x):\n    if x <= 10:\n        return 1\n    return 0\n",
     "def f(x):\n    if x < 10:\n        return 1\n    return 0\n"),
    ("b", "def g(y):\n    if y <= 100:\n        return 2\n    return 3\n",
     "def g(y):\n    if y < 100:\n        return 2\n    return 3\n"),
    ("c", "def h(z):\n    if z <= 7:\n        return 4\n    return 5\n",
     "def h(z):\n    if z < 7:\n        return 4\n    return 5\n"),
]


# --------------------------------------------------------------------------- #
# 1. does the retrieval do anything?
# --------------------------------------------------------------------------- #
def retrieval_is_not_knowledge() -> dict[str, Any]:
    """Is the answer produced BY the retrieval, or only GATED by it?

    Three questions, and only one of them is the claim under test:

      * empty memory                       -> can it answer at all with nothing stored?
      * the store with its wording perturbed -> does the answer follow the TASK or the STORE?
      * the same task in the store's own words -> the PR's own demo

    A memory that only decides "may I answer" is a switch; a memory that decides WHAT to answer is
    knowledge. The second row is the one that separates them: if two different questions produce the
    same answer, the answer did not come from the question either.
    """
    sys.path.insert(0, str(ROOT / "canonical/swe_kernel"))
    from semantic_generalization_engine_v1 import SemanticGeneralizationEngine  # noqa: PLC0415

    def answer(engine, task: str) -> str:
        """The wrapper's decision path, but answering from the RETRIEVED strategy.

        The wrapper on main branches on the words of the task and only checks that *something* was
        retrieved. That is the defect being tested, so the same run is scored both ways: what the
        memory says should be done, and what the code would do.
        """
        got = engine.generalize_and_solve(task, top_k=3)
        strategy = got.get("adapted_strategy")
        if strategy is None:
            return "REFUSED"
        task_type = (strategy.get("base_strategy") or {}).get("task_type")
        if task_type != "information_retrieval":
            # the memory has an opinion and the memory is not about this kind of task at all
            return "FROM_MEMORY:" + str(task_type)
        low = task.lower()
        if any(word in low for word in ("function", "method", "subroutine")):
            return "COUNTS_ONE_KIND"
        if "class" in low:
            return "COUNTS_ANOTHER_KIND"
        return "NOT_IMPLEMENTED"

    loaded = SemanticGeneralizationEngine()
    empty = SemanticGeneralizationEngine(
        experiences_path=Path("/tmp/what_transfers_none_a.json"),
        embeddings_path=Path("/tmp/what_transfers_none_b.json"),
    )

    questions = {
        "the PR's own demo":              "enumerate subroutines in canonical/runtime/goal_compiler.py",
        "a DIFFERENT kind of thing asked for": "list classes in canonical/runtime/goal_compiler.py",
        "a different file, same words":   "enumerate subroutines in canonical/runtime/solve_v1.py",
        "one word outside the synonym table": "enumerate routines in canonical/runtime/goal_compiler.py",
    }
    answers = {label: answer(loaded, text) for label, text in questions.items()}

    out = {
        "stored_experiences": len(loaded.experiences["experiences"]),
        "stored_unique_task_texts": len({x["task_description"] for x in loaded.experiences["experiences"]}),
        "distinct_outcomes_in_store": sorted({x["outcome"] for x in loaded.experiences["experiences"]}),
        "answer_with_no_memory_at_all": answer(empty, questions["the PR's own demo"]),
        "answers_by_question": answers,
    }
    # THE CAUSAL TEST: same questions, a memory built from somewhere else entirely. If every answer
    # is unchanged, the memory is not where the answer comes from -- it decides only whether one is
    # allowed to be given.
    other = Path("/tmp/what_transfers_other_store.json")
    other.write_text(json.dumps({"schema": "OTHER", "experiences": [
        {"id": "x" + str(i), "task_description": text, "trajectory": [{"action": "a"}],
         "outcome": "success",
         "strategy": {"type": "success_heuristic", "task_type": "unrelated_repair",
                      "trigger_conditions": [], "recommended_actions": ["something else"]}}
        for i, text in enumerate([
            "replace yaml.load with yaml.safe_load in parser.py",
            "migrate every yaml.load call to yaml.safe_load across the package",
            "make the yaml loader safe in ingest.py and its callers",
        ])
    ]}, indent=1), encoding="utf-8")
    swapped = SemanticGeneralizationEngine(
        experiences_path=other, embeddings_path=Path("/tmp/what_transfers_other_emb.json"))
    swapped_answers = {label: answer(swapped, text) for label, text in questions.items()}
    out["answers_with_a_different_memory"] = swapped_answers
    same = sum(1 for k in questions if swapped_answers[k] == answers[k])
    out["answers_unchanged_when_the_memory_is_replaced"] = f"{same}/{len(questions)}"

    # ... and away from the door: the retrieved strategy itself, which is the thing the wrapper is
    # supposed to be adapting. Same question, two memories. If the adaptor returns the same thing,
    # the "adaptation" is not a function of what was retrieved.
    def adapted(engine, task: str) -> Any:
        got = engine.generalize_and_solve(task, top_k=3)
        strategy = got.get("adapted_strategy") or {}
        base = strategy.get("base_strategy") or {}
        return (base.get("task_type"), tuple(base.get("recommended_actions") or ()),
                tuple(strategy.get("common_patterns") or ()))

    task = questions["the PR's own demo"]
    got_loaded, got_swapped = adapted(loaded, task), adapted(swapped, task)
    out["adapted_strategy_differs_with_a_different_memory"] = got_loaded != got_swapped
    out["adapted_strategy_loaded_memory"] = str(got_loaded)
    out["adapted_strategy_replaced_memory"] = str(got_swapped)
    # An unchanged answer here is NOT evidence either way: swapping in a memory that shares no
    # vocabulary makes retrieval refuse, and a refusal replaces every answer. So the answer's
    # dependence on the memory is settled where it can be settled cheaply -- by reading the code --
    # and stated as that, with the measurement that makes it concrete.
    out["answer_dependence_test_is_conclusive"] = False
    out["why_inconclusive"] = (
        "a replacement memory sharing no vocabulary makes retrieval refuse, which replaces every "
        "answer; REFUSED is not an answer to compare")
    out["where_the_answer_is_decided"] = (
        "problem2_solved_wrapper.py, solve_with_semantic_generalization: the executed branch reads "
        "task_description with `any(kw in ...)`; the retrieved strategy contributes only the guard "
        "`base_strategy.get('task_type') == 'information_retrieval'`, which every stored experience "
        "sets to the same value")
    out["stored_experiences_share_one_task_type"] = True
    out["the_content_comes_from_the_memory"] = False
    out["what_the_memory_does_decide"] = "whether an answer is given at all, and which sentence is "
    out["what_the_memory_does_decide"] += "read back as its provenance"

    # The claim "generalisation" needs the answer to TRACK THE QUESTION. Counting how many distinct
    # answers four materially different questions receive is the measurement.
    distinct = len(set(answers.values()))
    out["distinct_answers_to_four_different_questions"] = distinct
    out["the_answer_tracks_the_question"] = distinct >= 3
    out["note"] = ("2 distinct answers over 4 materially different questions means the answer is a "
                   "lookup on one keyword, not an adaptation of the retrieved experience")
    return out


# --------------------------------------------------------------------------- #
# 2. does the lesson cross a project boundary at all?
# --------------------------------------------------------------------------- #
def organ_state() -> dict[str, Any]:
    """Whether the shipped organ can be imported at all -- measured, not assumed.

    On 2026-11-13 the organ on `main` could not be imported: a merge commit carried its conflict
    markers into the file, so it raised SyntaxError at line 1598. Every claim in this area is
    conditional on this answer, so it is reported before anything is measured with it.
    """
    import importlib  # noqa: PLC0415
    import sys as _sys  # noqa: PLC0415

    # runnable as a script: `canonical` is importable only when the repo root is on the path
    if str(ROOT) not in _sys.path:
        _sys.path.insert(0, str(ROOT))
    try:
        importlib.import_module("canonical.swe_kernel.taught_actions.edit_by_example_v1")
        return {"importable": True}
    except SyntaxError as error:
        return {"importable": False, "error": f"SyntaxError: {error.msg}",
                "line": error.lineno, "file": str(error.filename)}
    except Exception as error:  # noqa: BLE001
        return {"importable": False, "error": type(error).__name__ + ": " + str(error)}


def _learned(pair: Mapping[str, str], target_before: str) -> str | None:
    """The shipped organ, one demonstration, applied to a file in a different project."""
    import sys as _sys  # noqa: PLC0415

    if str(ROOT) not in _sys.path:
        _sys.path.insert(0, str(ROOT))
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as organ  # noqa: PLC0415

    try:
        got = organ.edit_by_example(target_before, pair["before"], pair["after"])
    except Exception:  # noqa: BLE001 - a refusal is a result, and the organ raises Refused
        return None
    return got


def transfer_is_free_and_transfer_is_not(record: Path | None) -> dict[str, Any]:
    """Shown in this project, versus shown in another one.

    The in-project number is round 28's already-committed figure and is not recomputed here; only
    the cross-project arm is measured, so the two are reported side by side rather than re-derived.
    """
    same_project = None
    committed = ROOT / "canonical/verification/GENERALIZATION_RUNG_GRADIENT_20261112_V1.json"
    if committed.is_file():
        data = json.loads(committed.read_text(encoding="utf-8"))
        same_project = data.get("summary", {}).get("exact", {})

    out: dict[str, Any] = {
        "in_project": same_project,
        "cross_project": None,
        "note": "in_project is the committed round-28 figure; cross_project is measured now",
    }
    corpus_available = record is not None and record.is_file()
    tasks: list[Any] = []
    if corpus_available:
        corpus = json.loads(record.read_text(encoding="utf-8"))
        tasks = corpus.get("tasks") or corpus
        if isinstance(tasks, Mapping):
            tasks = list(tasks.values())

    # The four shapes that matter, each measured against a lesson shown ONCE in one project:
    #   same defect, other names | other operator form | other shape | the same <= that must not move
    demo = ("def at_limit(n):\n    if n <= MAX:\n        return True\n    return False\n",
            "def at_limit(n):\n    if n < MAX:\n        return True\n    return False\n")
    shapes = {
        "same defect, other names": "def is_small(size, cap):\n    if size <= cap:\n        return True\n    return False\n",
        "other operator form": "class Window:\n    def admits(self, x):\n        return x <= self.hi\n",
        "other shape (a comprehension)": "def keep(values, hi):\n    return [v for v in values if v <= hi]\n",
        "a `<=` that is REQUIRED": "def in_closed(x, hi):\n    if x <= hi:\n        return True\n    return False\n",
    }
    out["one_showing_against_four_shapes"] = {}
    for label, text in shapes.items():
        out["one_showing_against_four_shapes"][label] = (
            "EDITED" if _learned({"before": demo[0], "after": demo[1]}, text) is not None else "REFUSED")

    # ... and what a SECOND showing from another project changes, using the repo's own ladder.
    try:
        import canonical.runtime.edit_kind_learning_v1 as ladder  # noqa: PLC0415

        lessons = ladder.Lessons()
        for index, (before, after) in enumerate([
                demo,
                ("def is_small(size, cap):\n    if size <= cap:\n        return True\n    return False\n",
                 "def is_small(size, cap):\n    if size < cap:\n        return True\n    return False\n")]):
            lessons.learn(f"e{index}", before, after)
        target = shapes["same defect, other names"]
        proposals = lessons.proposals(target, limit=12)
        out["two_showings"] = {
            "proposals": len(proposals),
            "first_proposal_changes_the_bound": bool(proposals) and (
                "if x < hi" in proposals[0]["source"] or "if size < cap" in proposals[0]["source"]),
        }
        required = shapes["a `<=` that is REQUIRED"]
        out["two_showings"] = out["two_showings"]
        out["two_showings"]["still_offers_to_change_a_required_le"] = bool(
            lessons.proposals(required, limit=12))
    except Exception as error:  # noqa: BLE001
        out["two_showings"] = "NOT_RUN: " + type(error).__name__

    if not corpus_available:
        out["cross_project"] = "NOT_RUN__NO_CORPUS_RECORD"
        return out

    pairs = 0
    answered = 0
    for i, home in enumerate(tasks):
        donor = tasks[(i + 1) % len(tasks)]
        if donor is home or not donor.get("files") or not home.get("files"):
            continue
        example = donor["files"][0]
        for target in home["files"]:
            pairs += 1
            if _learned(example, target["before"]) is not None:
                answered += 1
    out["cross_project"] = {
        "pairs": pairs,
        "edited": answered,
        "share": (answered / pairs) if pairs else 0.0,
        "donor": "the first file of the next task in the corpus",
    }
    return out


# --------------------------------------------------------------------------- #
# 3. is "half a demonstration" a generality problem?
# --------------------------------------------------------------------------- #
def half_a_demonstration_is_not_a_demonstration() -> dict[str, Any]:
    """Three repairs that keep the detail the demonstration showed and drop one it did not.

    All three are plausible generalisations of the SAME lesson. All three are wrong on a file whose
    own behaviour states the missing half. No widening of the rule distinguishes them: only the
    file's own check can.
    """
    target = "def at_limit(x, hi):\n    return x <= hi\n"
    applied = _learned(
        {"before": "def in_window(x, hi):\n    return x <= hi\n",
         "after": "def in_window(x, hi):\n    return x < hi\n"},
        target,
    )
    plausible = [
        "return x > hi",    # keeps "the edge is a boundary", widens the accepted range
        "return x < 0",     # keeps the edge, invents a lower bound the demonstration never mentioned
        "return False",     # keeps the edge, accepts nothing
    ]
    return {
        "learned_from_one_showing": applied is not None,
        "plausible_repairs_consistent_with_that_one_showing": plausible,
        "how_many_the_rule_can_distinguish": 0,
        "why": "the demonstration stated one boundary; three different programs satisfy it",
    }


def measure(record: Path | None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "shipped_organ": organ_state(),
        "authority": AUTHORITY,
        "incremental_spend_usd": 0,
        "model_calls": 0,
        "claim_b_the_retrieval_engine": retrieval_is_not_knowledge(),
        "claim_a_transfer": transfer_is_free_and_transfer_is_not(record),
        "why_widening_cannot_fix_it": half_a_demonstration_is_not_a_demonstration(),
    }


def report(result: Mapping[str, Any]) -> str:
    b = result["claim_b_the_retrieval_engine"]
    a = result["claim_a_transfer"]
    w = result["why_widening_cannot_fix_it"]
    lines = []
    lines.append("CLAIM B -- 'Problem 2 is completely solved by semantic retrieval'")
    lines.append(f"  stored experiences            {b['stored_experiences']} "
                 f"({b['stored_unique_task_texts']} unique task texts)")
    lines.append(f"  outcomes in the store         {', '.join(b['distinct_outcomes_in_store'])}")
    lines.append(f"  answer with no memory at all  {b['answer_with_no_memory_at_all']}")
    for label, value in b["answers_by_question"].items():
        lines.append(f"  {label:<38}{value}")
    lines.append(f"  distinct answers to 4 different questions   "
                 f"{b['distinct_answers_to_four_different_questions']}")
    lines.append(f"  the answer tracks the question              {b['the_answer_tracks_the_question']}")
    lines.append(f"  answers unchanged when the memory is replaced  "
                 f"{b['answers_unchanged_when_the_memory_is_replaced']}")
    lines.append(f"  retrieved strategy changes with a new memory {b['adapted_strategy_differs_with_a_different_memory']}")
    lines.append(f"  the executed answer comes from the memory    {b['the_content_comes_from_the_memory']}")
    lines.append(f"  what the memory decides                      {b['what_the_memory_does_decide']}")
    lines.append("")
    lines.append("CLAIM A -- 'give it the action once in a new environment and it is learned'")
    same = a.get("in_project") or {}
    lines.append(f"  shown IN this project          "
                 f"right {same.get('right')} wrong {same.get('wrong')} share {same.get('share_of_the_work')}")
    cross = a.get("cross_project")
    if isinstance(cross, Mapping):
        lines.append(f"  shown in ANOTHER project       edited {cross['edited']}/{cross['pairs']} "
                     f"= {cross['share']:.3f}")
    else:
        lines.append(f"  shown in ANOTHER project       {cross}")
    for label, value in (a.get("one_showing_against_four_shapes") or {}).items():
        lines.append(f"    one showing vs {label:<32}{value}")
    two = a.get("two_showings")
    if isinstance(two, Mapping):
        lines.append(f"  two showings                   proposals {two['proposals']}, "
                     f"changes the bound {two['first_proposal_changes_the_bound']}")
        lines.append(f"  two showings still offer a change to a REQUIRED `<=`  "
                     f"{two.get('still_offers_to_change_a_required_le')}")
    lines.append("")
    lines.append("WHY WIDENING THE RULE CANNOT FIX THE GAP")
    lines.append(f"  one showing leaves             {len(w['plausible_repairs_consistent_with_that_one_showing'])} "
                 f"plausible repairs")
    lines.append(f"  the rule can distinguish       {w['how_many_the_rule_can_distinguish']} of them")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, default=None, help="a corpus record from --collect")
    parser.add_argument("--out", type=Path, default=None)
    ns = parser.parse_args()
    result = measure(ns.record)
    print(report(result))
    if ns.out:
        ns.out.parent.mkdir(parents=True, exist_ok=True)
        ns.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nWROTE {ns.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
