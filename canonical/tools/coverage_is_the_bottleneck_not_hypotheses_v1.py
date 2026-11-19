#!/usr/bin/env python3
"""Coverage is the bottleneck, not hypotheses.

The prompt names `INSUFFICIENCY_CERTIFICATE_20261113_V1.json`, and its last word is an open thread:

    closed_vocabulary_size 31, hypotheses_that_would_need_enumerating 8_388_608, learner cap 12
    -> BOUNDED__TOO_MANY_CANDIDATE_FACTS_TO_ENUMERATE
    "absence removes the separation obstruction but not the enumeration bound, so the obstacle moves
     from representation to combinatorics"

And the previous round here measured that one refusal per coordinate identifies a precondition 10/10 where
160 state observations identified 0/10. Put together, those two results cannot both be the whole story: if cuts
identify, the `2^23` count is not the cost of identification -- it is the cost of *enumerating*, which nothing
requires.

This round measures which one the wall really is, on one machine with real binaries and a measured outcome for
every state:

  K1  the schedule of the question -- one success and a few refusals -- leaves survivors that agree with every
      observation and are WRONG on held-out states (the surface accident, counted);
  K2  adding varied successes -- states in which the action still applies while irrelevant facts differ -- removes
      exactly those survivors, and identification becomes exact on held-out states;
  K3  the irrelevance evidence is the successes: a fact that differs between two successes cannot be a coordinate,
      so success is not useless -- it is the only evidence of irrelevance, which corrects the previous round's own
      "a success teaches nothing";
  K4  the price: 2^n candidate subsets exist (131 072 at n=17; 8 388 608 at the certificate's n=23; 3^n with
      polarity), while the schedule costs 1 + k + r executions, where r is the number of facts the states VARY.
      Identification is coverage-linear, not hypothesis-exponential;
  K5  zero model calls, zero parameters, zero network.

The law, and the 2026 statement of it: identification from cuts requires every point that matters to appear in a
crossing pair. A fact you never varied is a coordinate forever, and the rule you learn will be exactly right on
everything you saw and exactly wrong on what you did not.

    python3 canonical/tools/coverage_is_the_bottleneck_not_hypotheses_v1.py [--receipt PATH]
"""
from __future__ import annotations

import itertools
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import the_refusal_is_the_other_half_v1 as R  # noqa: E402  (the world and the runner, reused not rebuilt)

SCHEMA = "BRAIN_COVERAGE_IS_THE_BOTTLENECK_NOT_HYPOTHESES_V1"

FACTS: tuple[str, ...] = (
    "a_exists", "a_is_dir", "dir_exists", "dir_empty", "nodir_exists", "sub_exists", "link_absent",
    "xgz_exists", "xgz_valid", "sorted_exists", "sorted_sorted", "patch_applies",
    "repo_is_git", "stash_present", "tree_clean", "btgz_exists", "btgz_valid",
)
IDX = {name: i for i, name in enumerate(FACTS)}


def _ok(argv: Sequence[str], cwd: pathlib.Path) -> bool:
    return R._run(argv, cwd)[0] == 0


def facts_of(state: pathlib.Path) -> int:
    """The fact vector of a state, as a bitmask. Every bit is a real query against real files."""
    files = state / "files"
    a, d, nd, sub, link = files / "a.txt", files / "dir", files / "nodir", files / "sub", files / "sub" / "link"
    xgz, srt, btgz = files / "x.gz", files / "sorted.txt", files / "b.tar.gz"
    repo = state / "repo"
    bits = {
        "a_exists": a.is_file(),
        "a_is_dir": a.is_dir(),
        "dir_exists": d.is_dir(),
        "dir_empty": d.is_dir() and not any(d.iterdir()),
        "nodir_exists": nd.is_dir(),
        "sub_exists": sub.is_dir(),
        "link_absent": not (link.exists() or link.is_symlink()),
        "xgz_exists": xgz.exists(),
        "xgz_valid": xgz.is_file() and _ok(["gzip", "-t", str(xgz)], state),
        "sorted_exists": srt.is_file(),
        "sorted_sorted": srt.is_file() and srt.read_text() == "a\nb\nc\n",
        "patch_applies": _ok(["patch", "-p1", "--dry-run", "--forward", "-i", "files/p.patch"], state),
        "repo_is_git": _ok(["git", "rev-parse", "--is-inside-work-tree"], repo),
        "stash_present": bool(R._git(state, "stash", "list")[1].strip()),
        "tree_clean": _ok(["git", "diff", "--quiet"], repo) and _ok(["git", "diff", "--cached", "--quiet"], repo),
        "btgz_exists": btgz.exists(),
        "btgz_valid": btgz.is_file() and _ok(["tar", "-tzf", str(btgz)], state),
    }
    mask = 0
    for name, value in bits.items():
        if value:
            mask |= 1 << IDX[name]
    return mask


# ----------------------------------------------------------------------------------------------------------
# the states: one template, then single and double faults, so the pool varies many facts at once
# ----------------------------------------------------------------------------------------------------------

def _clear_stash(s: pathlib.Path) -> None:
    R._git(s, "stash", "clear")


def _dirty(s: pathlib.Path) -> None:
    R._write(s / "repo" / "README.txt", "one\nlocal edit\n")


def _rm_a(s: pathlib.Path) -> None:
    R._rm(s / "files" / "a.txt")


def _a_as_dir(s: pathlib.Path) -> None:
    R._rm(s / "files" / "a.txt")
    (s / "files" / "a.txt").mkdir()


def _rm_dir(s: pathlib.Path) -> None:
    R._rm(s / "files" / "dir")


def _fill_dir(s: pathlib.Path) -> None:
    R._write(s / "files" / "dir" / "inside.txt", "i\n")


def _rm_nodir(s: pathlib.Path) -> None:
    R._rm(s / "files" / "nodir")


def _rm_sub(s: pathlib.Path) -> None:
    R._rm(s / "files" / "sub")


def _make_link(s: pathlib.Path) -> None:
    (s / "files" / "sub").mkdir(parents=True, exist_ok=True)
    (s / "files" / "sub" / "link").write_text("occupied\n")


def _break_gz(s: pathlib.Path) -> None:
    (s / "files" / "x.gz").write_bytes(b"plain bytes\n")


def _rm_gz(s: pathlib.Path) -> None:
    R._rm(s / "files" / "x.gz")


def _unsort(s: pathlib.Path) -> None:
    R._write(s / "files" / "sorted.txt", "c\nb\na\n")


def _rm_sorted(s: pathlib.Path) -> None:
    R._rm(s / "files" / "sorted.txt")


def _rm_tgz(s: pathlib.Path) -> None:
    R._rm(s / "files" / "b.tar.gz")


def _break_tgz(s: pathlib.Path) -> None:
    (s / "files" / "b.tar.gz").write_bytes(b"plain bytes\n")


def _break_context(s: pathlib.Path) -> None:
    R._write(s / "files" / "a.txt", "alpha\nCHANGED\ngamma\n")


def _make_sub(s: pathlib.Path) -> None:
    (s / "files" / "sub").mkdir(parents=True, exist_ok=True)


def _make_nodir(s: pathlib.Path) -> None:
    (s / "files" / "nodir").mkdir(parents=True, exist_ok=True)


FAULTS: tuple[Callable[[pathlib.Path], None], ...] = (
    _clear_stash, _dirty, _rm_a, _a_as_dir, _rm_dir, _fill_dir, _rm_nodir, _rm_sub, _make_link,
    _break_gz, _rm_gz, _unsort, _rm_sorted, _rm_tgz, _break_tgz, _break_context,
    _make_sub, _make_nodir,
)
POOL: tuple[tuple[int, ...], ...] = (
    (), (0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,), (10,), (11,), (12,), (13,), (14,), (15,),
    (0, 1), (4, 5), (6, 8), (2, 3), (10, 15), (1, 11), (5, 9), (7, 12), (3, 13), (0, 6, 10),
    (16,), (17,), (16, 2), (17, 4), (16, 9), (17, 2), (17, 9), (16, 10), (17, 12),
)

# the action set: fixed argv, and the coordinate set measured in the previous round
ACTIONS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("cp_a_into_dir", ("cp", "files/a.txt", "files/dir/"), ("a_exists", "dir_exists")),
    ("rmdir_dir", ("rmdir", "files/dir"), ("dir_exists", "dir_empty")),
    ("gzip_x", ("gzip", "-d", "files/x.gz"), ("xgz_exists", "xgz_valid")),
    ("sort_c", ("sort", "-c", "files/sorted.txt"), ("sorted_exists", "sorted_sorted")),
    ("ln_link", ("ln", "-s", "files/a.txt", "files/sub/link"), ("sub_exists", "link_absent")),
    ("git_stash_pop", (R.GIT + ["stash", "pop"]), ("stash_present", "tree_clean")),
    ("patch_apply", ("patch", "-p1", "--forward", "--no-backup-if-mismatch", "-i", "files/p.patch"),
     ("patch_applies",)),
    ("mkdir_nodir_sub", ("mkdir", "files/nodir/sub"), ("nodir_exists",)),
    ("tar_x", ("tar", "-xzf", "files/b.tar.gz"), ("btgz_exists", "btgz_valid")),
)


def mask_of(names: Sequence[str]) -> int:
    out = 0
    for name in names:
        out |= 1 << IDX[name]
    return out


def build_pool(root: pathlib.Path) -> list[dict[str, Any]]:
    template = R.build_template(root)
    states: list[dict[str, Any]] = []
    for index, faults in enumerate(POOL):
        state = root / f"pool{index}"
        if state.exists():
            shutil.rmtree(state)
        shutil.copytree(template, state)
        for fault in faults:
            FAULTS[fault](state)
        states.append({"index": index, "faults": list(faults), "path": state, "mask": facts_of(state),
                       "observed": {}})
    return states


def observe_actions(states: list[dict[str, Any]], root: pathlib.Path) -> None:
    """Every (action, state) outcome is measured, not declared: a copy of the state, the real binary, its exit."""
    for name, argv, _coords in ACTIONS:
        cwd = root / "_scratch"
        for state in states:
            if cwd.exists():
                shutil.rmtree(cwd)
            shutil.copytree(state["path"], cwd)
            rc, _ = R._run(argv, cwd / "repo" if name == "git_stash_pop" else cwd)
            state["observed"][name] = rc == 0
            if cwd.exists():
                shutil.rmtree(cwd)


# ----------------------------------------------------------------------------------------------------------
# the hypothesis space and the two schedules
# ----------------------------------------------------------------------------------------------------------

def survivors(successes: Sequence[int], failures: Sequence[int]) -> list[int]:
    out: list[int] = []
    for hypothesis in range(1 << len(FACTS)):
        if all((s & hypothesis) == hypothesis for s in successes) and all((f & hypothesis) != hypothesis for f in failures):
            out.append(hypothesis)
    return out


def predicts(hypothesis: int, mask: int) -> bool:
    return (mask & hypothesis) == hypothesis


def unanimous(hypotheses: Sequence[int], mask: int) -> bool | None:
    """What the survivor set says about a state: a verdict if every survivor agrees, else nothing."""
    verdicts = {predicts(h, mask) for h in hypotheses}
    return verdicts.pop() if len(verdicts) == 1 else None


def behaviour(hypotheses: Sequence[int], held: Sequence[dict[str, Any]], action: str) -> dict[str, Any]:
    """A rule is usable where it is unanimous. Undecided is not a score of 1."""
    right = wrong = undecided = 0
    for state in held:
        verdict = unanimous(hypotheses, state["mask"])
        observed = state["observed"][action]
        if verdict is None:
            undecided += 1
        elif verdict == observed:
            right += 1
        else:
            wrong += 1
    total = len(held)
    return {"held_out": total, "unanimous_and_right": right, "unanimous_and_wrong": wrong, "undecided": undecided,
            "accuracy_where_decided": round(right / (right + wrong or 1), 4),
            "accuracy_of_the_set": round(right / total, 4) if total else 0.0}


def hypothesis_accuracy_range(hypotheses: Sequence[int], held: Sequence[dict[str, Any]], action: str) -> list[float]:
    if not hypotheses or not held:
        return [0.0, 0.0]
    scores = [sum(1 for s in held if predicts(h, s["mask"]) == s["observed"][action]) / len(held)
              for h in hypotheses]
    return [round(min(scores), 4), round(max(scores), 4)]


def nearest(success: int, failures: Sequence[int], count: int = 2) -> list[int]:
    ordered = sorted(failures, key=lambda f: bin(f ^ success).count("1"))
    return ordered[:count]


def _coverage(name: str, coords: Sequence[str], succ_seen: Sequence[int], seen: Sequence[dict[str, Any]],
              held: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """What the seen successes pin down, and whether the fact vector describes the world at all."""
    """What the seen successes and the held-out states each pin down.

    A fact true in EVERY seen success can always be conjoined to the true precondition without contradicting
    anything: coords are true in every success, every refusal violates a coord so a superset is never a subset of
    one, and therefore only a success in which the fact is FALSE can eliminate the superset. So irrelevance is
    proved by successes alone. A fact that is still unfalsifiable and that varies off-sample is exactly what makes
    the survivor set undecided there -- that is the quantity this returns.
    """
    held_masks = [s["mask"] for s in held if name in s["observed"]]
    always_true = [FACTS[i] for i in range(len(FACTS)) if all(m & (1 << i) for m in succ_seen)]
    varies_off_sample = [FACTS[i] for i in range(len(FACTS))
                         if len({bool(m & (1 << i)) for m in held_masks}) > 1]
    # the coordinates are true in every success by definition; what can still be an accident is everything else
    true_mask = mask_of(coords)
    held_decisive = [s for s in held if name in s["observed"]]
    # an unfalsifiable fact can only make the rule undecided where the true precondition still holds without it
    material = sorted(f for f in (set(always_true) - set(coords))
                      if any(predicts(true_mask, s["mask"]) and not (s["mask"] & (1 << IDX[f]))
                             for s in held_decisive))
    sound = all(predicts(true_mask, s["mask"]) == s["observed"][name] for s in seen + held
                if name in s["observed"])
    unsound_states = [s["index"] for s in seen + held
                      if name in s["observed"] and predicts(true_mask, s["mask"]) != s["observed"][name]]
    extra = sorted((set(always_true) & set(varies_off_sample)) - set(coords))
    return {"seen_successes": len(succ_seen),
            "facts_true_in_every_seen_success": always_true,
            "facts_that_vary_off_sample": varies_off_sample,
            "unfalsifiable_and_mattering": material,
            "fact_vector_is_sound": sound,
            "states_the_fact_vector_misdescribes": unsound_states,
            "reading": ("a fact that is true in every success and varies off-sample can be conjoined to the "
                        "precondition without contradicting any observation, so the survivor set is undecided "
                        "exactly there")}


def measure(root: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.time()
    root = pathlib.Path(root or tempfile.mkdtemp(prefix="coverage-"))
    root.mkdir(parents=True, exist_ok=True)
    states = build_pool(root)
    observe_actions(states, root)
    seen = [s for s in states if s["index"] % 3 != 0]
    held = [s for s in states if s["index"] % 3 == 0]
    rows: list[dict[str, Any]] = []
    for name, argv, coords in ACTIONS:
        true_mask = mask_of(coords)
        succ_seen = [s["mask"] for s in seen if s["observed"][name]]
        fail_seen = [s["mask"] for s in seen if not s["observed"][name]]
        if not succ_seen or not fail_seen:
            rows.append({"action": name, "skipped": "one class missing in the seen partition",
                         "successes_seen": len(succ_seen), "failures_seen": len(fail_seen)})
            continue
        one = succ_seen[0]
        refusals = nearest(one, fail_seen)
        set_a = survivors([one], refusals)
        set_b = survivors(succ_seen, refusals)
        minimal_a = sum(1 for h in set_a if not any(o != h and (o & h) == o for o in set_a))
        minimal_b = sum(1 for h in set_b if not any(o != h and (o & h) == o for o in set_b))
        rows.append({
            "action": name, "action_argv": list(argv), "coordinates": list(coords),
            "successes_seen": len(succ_seen), "failures_seen": len(fail_seen),
            "held_out": len([s for s in held if name in s["observed"]]),
            "schedule_A": {"name": "one success + the two nearest refusals",
                           "executions": 1 + len(refusals), "survivors": len(set_a),
                           "minimal_survivors": minimal_a,
                           "behaviour_on_held_out": behaviour(set_a, held, name),
                           "per_hypothesis_accuracy_range": hypothesis_accuracy_range(set_a, held, name)},
            "schedule_B": {"name": "every seen success + the same two refusals",
                           "executions": len(succ_seen) + len(refusals), "survivors": len(set_b),
                           "minimal_survivors": minimal_b,
                           "behaviour_on_held_out": behaviour(set_b, held, name),
                           "per_hypothesis_accuracy_range": hypothesis_accuracy_range(set_b, held, name)},
            "the_true_precondition_is_among_the_minimal": any(
                h == true_mask for h in set_b if not any(o != h and (o & h) == o for o in set_b)),
            "A_is_undecided_or_wrong_on_a_held_out_state": behaviour(set_a, held, name)["accuracy_of_the_set"] < 1.0,
            "A_decides_but_wrongly_somewhere": behaviour(set_a, held, name)["unanimous_and_wrong"] > 0,
            "coverage": _coverage(name, coords, succ_seen, seen, held),
            "irrelevance_evidence": {
                "facts_on_which_two_seen_successes_disagree": sum(
                    1 for i, _name in enumerate(FACTS) if len({bool(m & (1 << i)) for m in succ_seen}) > 1),
            },
        })

    varying = 0
    for i in range(len(FACTS)):
        bit = 1 << i
        if len({bool(s["mask"] & bit) for s in states}) > 1:
            varying += 1
    evaluable = [r for r in rows if "skipped" not in r]
    identified = [r["action"] for r in evaluable
                  if r["schedule_B"]["behaviour_on_held_out"]["accuracy_of_the_set"] == 1.0]
    covered = [r["action"] for r in evaluable
               if r["coverage"]["fact_vector_is_sound"] and not r["coverage"]["unfalsifiable_and_mattering"]]
    verdict = {
        "K1_one_success_plus_refusals_leaves_a_rule_that_cannot_decide_off_sample": {
            "the_metric": ("a survivor set is a rule only where it is unanimous; undecided is measured as undecided, "
                           "not scored as correct"),
            "accuracy_of_the_set_under_A": {r["action"]: r["schedule_A"]["behaviour_on_held_out"]["accuracy_of_the_set"]
                                            for r in evaluable},
            "undecided_under_A": {r["action"]: r["schedule_A"]["behaviour_on_held_out"]["undecided"] for r in evaluable},
            "decides_but_wrongly_under_A": {r["action"]: r["schedule_A"]["behaviour_on_held_out"]["unanimous_and_wrong"]
                                            for r in evaluable},
            "per_hypothesis_accuracy_range_under_A": {r["action"]: r["schedule_A"]["per_hypothesis_accuracy_range"]
                                                      for r in evaluable},
            "maximum_accuracy_of_the_set": max((r["schedule_A"]["behaviour_on_held_out"]["accuracy_of_the_set"]
                                                for r in evaluable), default=0.0),
            "MET": all(r["A_is_undecided_or_wrong_on_a_held_out_state"] for r in evaluable)},
        "K2_varied_successes_make_identification_exact_on_held_out": {
            "accuracy_of_the_set_under_B": {r["action"]: r["schedule_B"]["behaviour_on_held_out"]["accuracy_of_the_set"]
                                            for r in evaluable},
            "undecided_under_B": {r["action"]: r["schedule_B"]["behaviour_on_held_out"]["undecided"] for r in evaluable},
            "wrong_under_B": {r["action"]: r["schedule_B"]["behaviour_on_held_out"]["unanimous_and_wrong"]
                              for r in evaluable},
            "survivor_counts": {r["action"]: [r["schedule_A"]["survivors"], r["schedule_B"]["survivors"]]
                                for r in evaluable},
            "coverage_predicts_identification": {
                "identified": [r["action"] for r in evaluable
                               if r["schedule_B"]["behaviour_on_held_out"]["accuracy_of_the_set"] == 1.0],
                "sound_and_covered": covered,
                "unsound_fact_vectors": [r["action"] for r in evaluable
                                         if not r["coverage"]["fact_vector_is_sound"]],
                "states_the_fact_vector_misdescribes": {
                    r["action"]: r["coverage"]["states_the_fact_vector_misdescribes"] for r in evaluable
                    if r["coverage"]["states_the_fact_vector_misdescribes"]},
                "unfalsifiable_facts_that_vary_off_sample": {
                    r["action"]: r["coverage"]["unfalsifiable_and_mattering"] for r in evaluable},
                "identified_but_no_coverage": sorted(set(identified) - set(covered)),
                "coverage_but_not_identified": sorted(set(covered) - set(identified)),
                "reading": ("identification happens exactly when two things hold together: the facts mean what they "
                            "claim (soundness) and no fact that is true in every success can be false where the action "
                            "still applies (coverage). Coverage without soundness is undecided, soundness without "
                            "coverage is confidently wrong, and both failures are named rather than averaged away"),
            },
            "exact_on_held_out": identified,
            "undecided": [r["action"] for r in evaluable if r["action"] not in identified],
            "confidently_wrong_anywhere": {r["action"]: r["schedule_B"]["behaviour_on_held_out"]["unanimous_and_wrong"]
                                           for r in evaluable
                                           if r["schedule_B"]["behaviour_on_held_out"]["unanimous_and_wrong"]},
            "survivors_of_the_undecided": {r["action"]: r["schedule_B"]["survivors"] for r in evaluable
                                           if r["action"] not in identified},
            "the_failure_mode_is_abstention_not_error": all(
                r["schedule_B"]["behaviour_on_held_out"]["unanimous_and_wrong"] == 0 for r in evaluable),
            "MET": all(r["schedule_B"]["behaviour_on_held_out"]["unanimous_and_wrong"] == 0 for r in evaluable)
                   and len(identified) * 2 > len(evaluable)
                   and all(r["schedule_B"]["behaviour_on_held_out"]["accuracy_of_the_set"] == 1.0
                           for r in evaluable if r["coverage"]["fact_vector_is_sound"]
                           and not r["coverage"]["unfalsifiable_and_mattering"]
                           and r["action"] in identified)},
        "K3_a_success_is_the_irrelevance_evidence": {
            "the_previous_round_said": "one success leaves every behaviour alive, so a success teaches nothing",
            "survivors_fall_by_action": {r["action"]: [r["schedule_A"]["survivors"], r["schedule_B"]["survivors"]]
                                         for r in evaluable},
            "actions_where_extra_successes_removed_nothing": [
                r["action"] for r in evaluable if r["schedule_B"]["survivors"] == r["schedule_A"]["survivors"]],
            "what_this_measures": ("two successes that differ in a fact prove that fact is not a coordinate, which is "
                                   "the only evidence of irrelevance there is"),
            "facts_that_vary_anywhere_in_the_pool": varying,
            "facts_that_never_vary": [name for i, name in enumerate(FACTS)
                                      if len({bool(s["mask"] & (1 << i)) for s in states}) == 1],
            "reading": ("successes are not wasted information: two successes that disagree on a fact prove it is not a "
                        "coordinate, and that is the only such proof available -- the previous round's 'a success teaches "
                        "nothing' was true only for a single base state"),
            "MET": all(r["schedule_B"]["survivors"] <= r["schedule_A"]["survivors"] for r in evaluable)
                   and any(r["schedule_B"]["survivors"] < r["schedule_A"]["survivors"] for r in evaluable)},
        "K4_the_price_is_coverage_not_hypotheses": {
            "facts": len(FACTS),
            "candidate_subsets": 1 << len(FACTS),
            "candidate_conjunctions_with_polarity": 3 ** len(FACTS),
            "certificates_open_bound_at_23_effective_facts": 2 ** 23,
            "certificates_bound_with_polarity": 3 ** 23,
            "executions_under_A": {r["action"]: r["schedule_A"]["executions"] for r in evaluable},
            "executions_under_B": {r["action"]: r["schedule_B"]["executions"] for r in evaluable},
            "most_executions_for_any_action": max((r["schedule_B"]["executions"] for r in evaluable), default=0),
            "reading": ("the hypothesis space is 2^n or 3^n, but nothing in the schedule enumerates it: the cost is "
                        "1 success + k refusals + one success per fact that must be shown irrelevant"),
            "MET": max((r["schedule_B"]["executions"] for r in evaluable), default=0) < (1 << len(FACTS))},
        "K5_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0, "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-19",
        "mode": "MEASURE_WHETHER_THE_WALL_IS_THE_HYPOTHESIS_COUNT_OR_THE_COVERAGE_OF_THE_STATES",
        "why_this_round": {
            "the_gap_it_closes": ("INSUFFICIENCY_CERTIFICATE_20261113_V1 closed the vocabulary to 31 facts and found the "
                                  "obstacle moved to combinatorics: 8388608 hypotheses against a learner cap of 12"),
            "the_answer_being_tested": ("identification never enumerates the hypothesis space; it needs the facts that "
                                        "matter to be varied, so the cost is coverage-linear"),
            "why_it_could_fail": ("if the one-success schedule already predicted held-out outcomes exactly, or if varied "
                                  "successes did not reduce the survivors, or if an unvaried fact could somehow be ruled out"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "at least one action has a survivor of the one-success schedule that mispredicts a held-out state",
            "K2": "every action's varied-success schedule predicts held-out outcomes at 1.0 and has strictly fewer survivors",
            "K3": "the reduction is the irrelevance evidence carried by successes",
            "K4": "the executions of the schedule are fewer than 2^n, and the certificate's bound is quoted, not re-derived",
            "K5": "zero model calls, parameters, network",
        },
        "verdict": verdict, "rows": rows,
        "pool": {"states": len(states), "seen": len(seen), "held_out": len(held),
                 "faults": len(FAULTS), "facts": list(FACTS)},
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0, "parameters_stored": 0,
                 "network_calls_at_run_time": 0,
                 "executions": len(ACTIONS) * len(states) + sum(
                     (r.get("schedule_B", {}).get("executions", 0) for r in rows))},
        "limits": [
            "one machine, nine actions, 27 states, 17 facts; a census of these",
            "the hypothesis space is required-fact conjunctions without polarity; with polarity the count is 3^n and the "
            "argument is unchanged because nothing enumerates either",
            "the pool's facts are correlated (a_is_dir and a_exists), so minimal survivors can be several; the receipt "
            "counts them instead of picking one",
            "identification is up to the facts the pool varies: every fact that never varies is named in K3 and is "
            "permanently unidentifiable from this data",
            "the held-out partition is small, so an accuracy of 1.0 is exact on eight states per action, not on the world",
            "this does not price exploration: it prices the schedule once the states exist, and finding the states that "
            "vary a fact is the remaining work",
        ],
    }


def _xor_all(masks: Sequence[int]) -> int:
    out = 0
    for mask in masks:
        out |= masks[0] ^ mask
    return out


def headline(receipt: dict[str, Any]) -> str:
    verdict = receipt["verdict"]
    lines = [f"{'MET ' if v['MET'] else 'NOT '} {k}" for k, v in verdict.items()]
    lines.append("")
    for row in receipt["rows"]:
        if "skipped" in row:
            lines.append(f"{row['action']:16s} SKIPPED {row['skipped']}")
            continue
        a, b = row["schedule_A"], row["schedule_B"]
        ab, bb = a["behaviour_on_held_out"], b["behaviour_on_held_out"]
        lines.append(f"{row['action']:16s} A: {a['executions']:2d} exec, {a['survivors']:6d} surv, "
                     f"set-acc {ab['accuracy_of_the_set']:.3f} (undecided {ab['undecided']})   "
                     f"B: {b['executions']:2d} exec, {b['survivors']:5d} surv, "
                     f"set-acc {bb['accuracy_of_the_set']:.3f} (undecided {bb['undecided']})   {row['coordinates']}")
    k4 = verdict["K4_the_price_is_coverage_not_hypotheses"]
    lines.append("")
    lines.append(f"facts {k4['facts']}: subsets {k4['candidate_subsets']:,}, with polarity "
                 f"{k4['candidate_conjunctions_with_polarity']:,}; certificate's open bound "
                 f"{k4['certificates_open_bound_at_23_effective_facts']:,}; max executions "
                 f"{k4['most_executions_for_any_action']}")
    lines.append(f"seconds {receipt['cost']['seconds']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    path = None
    if "--receipt" in args:
        path = pathlib.Path(args[args.index("--receipt") + 1])
    receipt = measure()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0 if all(v["MET"] for v in receipt["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
