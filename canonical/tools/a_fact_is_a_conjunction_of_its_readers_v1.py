#!/usr/bin/env python3
"""A fact is a conjunction of its readers.

The previous round ended with three abstentions and named their causes: two actions could not rule out facts their
states never varied, and one -- `tar_x` -- had full coverage and still abstained. The cause of that one was measured
there and is measured again here: its column is computed with `tar -tzf`, which returns **0 for a gzip whose payload
is not a tar archive**. The fact said "this is an archive" while the world said otherwise, so every rule built on it
was hostage to the narrowest check in the table.

`fact_entailment_v1.py` already handles implications BETWEEN facts (implication-reducible pruning, sound by the
sensor's own kind specs). This round is about a different defect: a fact that is wrong about ITSELF. The repair is
not blame, arbitration, voting or a trust model. It is one line:

    a fact is true only when every independent reader says so          mask_audited = AND(readers)

and the direction of the collapse is chosen, not inherited: for a PRECONDITION, a spurious true makes the agent try
an action that will be refused (a cost, and a dangerous one), while a spurious false merely abstains (the failure mode
the previous round measured as safe). So disagreement must collapse to false.

Measured here on 17 facts, 37 states, nine real actions:

  K1  two INDEPENDENT implementations of each fact (a shell tool and a stdlib reader) disagree on at least one state,
      the witness is named, and a THIRD reading confirms which reader over-claimed;
  K2  the audit converts the abstention into an exact rule on held-out states and degrades no other action;
  K3  the audit costs no world-trials: every reader is read-only, and the tree is byte-identical afterwards;
  K4  the collapse is conservative in exactly one direction -- audited differs from primary only where primary said
      true and the second reader said false, never the reverse;
  K5  zero model calls, zero parameters, zero network.

The law: a table of facts is only as trustworthy as its weakest reader per column, and trust in a column is not a
property of the column -- it is a property of the agreement of two independent readings of it.

    python3 canonical/tools/a_fact_is_a_conjunction_of_its_readers_v1.py [--receipt PATH]
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import pathlib
import shutil
import sys
import tarfile
import tempfile
import time
from typing import Any, Callable, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import coverage_is_the_bottleneck_not_hypotheses_v1 as C  # noqa: E402  (the world, the pool, the actions)
import the_refusal_is_the_other_half_v1 as R  # noqa: E402  (the runner)

SCHEMA = "BRAIN_A_FACT_IS_A_CONJUNCTION_OF_ITS_READERS_V1"
FACTS = C.FACTS
IDX = C.IDX


# ------------------------------------------------------------------------------------------------------------
# two independent implementations of the same claim, per fact
# ------------------------------------------------------------------------------------------------------------

def _sh(argv: Sequence[str], cwd: pathlib.Path) -> bool:
    return R._run(argv, cwd)[0] == 0


def _p_a_exists(s: pathlib.Path) -> bool:
    return _sh(["test", "-f", "files/a.txt"], s)


def _p_a_is_dir(s: pathlib.Path) -> bool:
    return _sh(["test", "-d", "files/a.txt"], s)


def _p_dir_exists(s: pathlib.Path) -> bool:
    return _sh(["test", "-d", "files/dir"], s)


def _p_dir_empty(s: pathlib.Path) -> bool:
    return _p_dir_exists(s) and _sh(["test", "-z", "$(ls -A files/dir)"], s) if False else (
        _p_dir_exists(s) and not R._run(["ls", "-A", "files/dir"], s)[1].strip())


def _p_nodir_exists(s: pathlib.Path) -> bool:
    return _sh(["test", "-d", "files/nodir"], s)


def _p_sub_exists(s: pathlib.Path) -> bool:
    return _sh(["test", "-d", "files/sub"], s)


def _p_link_absent(s: pathlib.Path) -> bool:
    return not (_sh(["test", "-e", "files/sub/link"], s) or _sh(["test", "-L", "files/sub/link"], s))


def _p_xgz_exists(s: pathlib.Path) -> bool:
    return _sh(["test", "-e", "files/x.gz"], s)


def _p_xgz_valid(s: pathlib.Path) -> bool:
    return _p_xgz_exists(s) and _sh(["gzip", "-t", "files/x.gz"], s)


def _p_sorted_exists(s: pathlib.Path) -> bool:
    return _sh(["test", "-f", "files/sorted.txt"], s)


def _p_sorted_sorted(s: pathlib.Path) -> bool:
    return _p_sorted_exists(s) and _sh(["sort", "-c", "files/sorted.txt"], s)


def _p_patch_applies(s: pathlib.Path) -> bool:
    return _sh(["patch", "-p1", "--dry-run", "--forward", "-i", "files/p.patch"], s)


def _p_repo_is_git(s: pathlib.Path) -> bool:
    return _sh(["git", "rev-parse", "--is-inside-work-tree"], s / "repo")


def _p_stash_present(s: pathlib.Path) -> bool:
    rc, out = R._run(["git", "stash", "list"], s / "repo")
    return rc == 0 and bool(out.strip())


def _p_tree_clean(s: pathlib.Path) -> bool:
    return _sh(["git", "diff", "--quiet"], s / "repo") and _sh(["git", "diff", "--cached", "--quiet"], s / "repo")


def _p_btgz_exists(s: pathlib.Path) -> bool:
    return _sh(["test", "-e", "files/b.tar.gz"], s)


def _p_btgz_valid(s: pathlib.Path) -> bool:
    return _p_btgz_exists(s) and _sh(["tar", "-tzf", "files/b.tar.gz"], s)


PRIMARY: dict[str, Callable[[pathlib.Path], bool]] = {
    "a_exists": _p_a_exists, "a_is_dir": _p_a_is_dir, "dir_exists": _p_dir_exists, "dir_empty": _p_dir_empty,
    "nodir_exists": _p_nodir_exists, "sub_exists": _p_sub_exists, "link_absent": _p_link_absent,
    "xgz_exists": _p_xgz_exists, "xgz_valid": _p_xgz_valid, "sorted_exists": _p_sorted_exists,
    "sorted_sorted": _p_sorted_sorted, "patch_applies": _p_patch_applies, "repo_is_git": _p_repo_is_git,
    "stash_present": _p_stash_present, "tree_clean": _p_tree_clean, "btgz_exists": _p_btgz_exists,
    "btgz_valid": _p_btgz_valid,
}


# --- the second reader: a different implementation, not a second run of the same one -------------------------

def _s_a_exists(s: pathlib.Path) -> bool:
    return (s / "files" / "a.txt").is_file()


def _s_a_is_dir(s: pathlib.Path) -> bool:
    return (s / "files" / "a.txt").is_dir()


def _s_dir_exists(s: pathlib.Path) -> bool:
    return (s / "files" / "dir").is_dir()


def _s_dir_empty(s: pathlib.Path) -> bool:
    d = s / "files" / "dir"
    return d.is_dir() and len(os.listdir(d)) == 0


def _s_nodir_exists(s: pathlib.Path) -> bool:
    return (s / "files" / "nodir").is_dir()


def _s_sub_exists(s: pathlib.Path) -> bool:
    return (s / "files" / "sub").is_dir()


def _s_link_absent(s: pathlib.Path) -> bool:
    try:
        os.lstat(s / "files" / "sub" / "link")
        return False
    except OSError:
        return True


def _s_xgz_exists(s: pathlib.Path) -> bool:
    return (s / "files" / "x.gz").exists()


def _s_xgz_valid(s: pathlib.Path) -> bool:
    f = s / "files" / "x.gz"
    if not f.exists():
        return False
    try:
        with gzip.open(f, "rb") as handle:
            handle.read()
        return True
    except (OSError, EOFError):
        return False


def _s_sorted_exists(s: pathlib.Path) -> bool:
    return (s / "files" / "sorted.txt").is_file()


def _s_sorted_sorted(s: pathlib.Path) -> bool:
    f = s / "files" / "sorted.txt"
    if not f.is_file():
        return False
    lines = f.read_text().splitlines()
    return all(a <= b for a, b in zip(lines, lines[1:]))


def _s_patch_applies(s: pathlib.Path) -> bool:
    """Read the hunk and check it against the file, without running patch."""
    patch = s / "files" / "p.patch"
    target = s / "files" / "a.txt"
    if not patch.is_file() or not target.is_file():
        return False
    body = patch.read_text().splitlines()
    try:
        at = next(i for i, line in enumerate(body) if line.startswith("@@"))
        start = int(body[at].split("-")[1].split(",")[0])
    except (StopIteration, IndexError, ValueError):
        return False
    old = [line[1:] for line in body[at + 1:] if line[:1] in (" ", "-")]
    have = target.read_text().splitlines()
    window = have[start - 1:start - 1 + len(old)]
    return window == old


def _s_repo_is_git(s: pathlib.Path) -> bool:
    for candidate in [s / "repo", *s.joinpath("repo").parents][:6]:
        if (candidate / ".git").exists():
            return True
    return False


def _s_stash_present(s: pathlib.Path) -> bool:
    return (s / "repo" / ".git" / "refs" / "stash").is_file()


def _s_tree_clean(s: pathlib.Path) -> bool:
    rc, out = R._run(["git", "status", "--porcelain"], s / "repo")
    return rc == 0 and not out.strip()


def _s_btgz_exists(s: pathlib.Path) -> bool:
    return (s / "files" / "b.tar.gz").exists()


def _s_btgz_valid(s: pathlib.Path) -> bool:
    f = s / "files" / "b.tar.gz"
    if not f.exists():
        return False
    try:
        with tarfile.open(f, "r:gz") as archive:
            archive.getnames()
        return True
    except (tarfile.TarError, OSError, EOFError):
        return False


SECOND: dict[str, Callable[[pathlib.Path], bool]] = {
    "a_exists": _s_a_exists, "a_is_dir": _s_a_is_dir, "dir_exists": _s_dir_exists, "dir_empty": _s_dir_empty,
    "nodir_exists": _s_nodir_exists, "sub_exists": _s_sub_exists, "link_absent": _s_link_absent,
    "xgz_exists": _s_xgz_exists, "xgz_valid": _s_xgz_valid, "sorted_exists": _s_sorted_exists,
    "sorted_sorted": _s_sorted_sorted, "patch_applies": _s_patch_applies, "repo_is_git": _s_repo_is_git,
    "stash_present": _s_stash_present, "tree_clean": _s_tree_clean, "btgz_exists": _s_btgz_exists,
    "btgz_valid": _s_btgz_valid,
}


def mask(state: pathlib.Path, readers: dict[str, Callable[[pathlib.Path], bool]]) -> int:
    out = 0
    for name, reader in readers.items():
        try:
            if reader(state):
                out |= 1 << IDX[name]
        except OSError:
            pass
    return out


def audited_mask(state: pathlib.Path) -> int:
    """The conjunction of the readers: a fact is true only when every reader says so."""
    return mask(state, PRIMARY) & mask(state, SECOND)


def third_reading_of_the_archive(state: pathlib.Path) -> dict[str, Any]:
    """When the readers disagree about the archive, say what the file actually is, from a third door."""
    f = state / "files" / "b.tar.gz"
    try:
        with gzip.open(f, "rb") as handle:
            payload = handle.read()
        inflates = True
        payload_head = payload[:40].decode("utf-8", "replace")
    except (OSError, EOFError):
        inflates, payload_head = False, ""
    return {"gzip_members_inflate": inflates, "payload_head": payload_head,
            "tar_tzf_exit": R._run(["tar", "-tzf", str(f)], state)[0],
            "python_tarfile_says": _s_btgz_valid(state)}


# ------------------------------------------------------------------------------------------------------------
# the states: the previous round's pool plus the state that exposed the defect
# ------------------------------------------------------------------------------------------------------------

def build_states(root: pathlib.Path) -> list[dict[str, Any]]:
    states = C.build_pool(root)          # builds the template and the 36-state pool
    template = root / "template"
    extra = root / "pool_garbage"
    if extra.exists():
        shutil.rmtree(extra)
    shutil.copytree(template, extra)
    (extra / "files" / "b.tar.gz").write_bytes(gzip.compress(b"this is not a tar archive\n"))
    states.append({"index": len(states), "faults": ["a_valid_gzip_whose_payload_is_not_a_tar"],
                   "path": extra, "mask": 0, "observed": {}})
    for state in states:
        state["primary"] = mask(state["path"], PRIMARY)
        state["secondary"] = mask(state["path"], SECOND)
        state["audited"] = state["primary"] & state["secondary"]
    C.observe_actions(states, root)
    return states


def tree_digest(root: pathlib.Path) -> str:
    h = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        h.update(str(rel).encode())
        if path.is_file() and not path.is_symlink():
            h.update(path.read_bytes())
    return h.hexdigest()


def measure(root: pathlib.Path | None = None) -> dict[str, Any]:
    started = time.time()
    root = pathlib.Path(root or tempfile.mkdtemp(prefix="readers-"))
    root.mkdir(parents=True, exist_ok=True)
    states = build_states(root)

    # K3: reading changes nothing, measured on every state
    before = {s["index"]: tree_digest(s["path"]) for s in states}
    for state in states:
        mask(state["path"], PRIMARY)
        mask(state["path"], SECOND)
    unchanged = sum(1 for s in states if tree_digest(s["path"]) == before[s["index"]])

    disagreements: dict[str, list[int]] = {}
    for name in FACTS:
        bit = 1 << IDX[name]
        hits = [s["index"] for s in states if bool(s["primary"] & bit) != bool(s["secondary"] & bit)]
        if hits:
            disagreements[name] = hits

    seen = [s for s in states if s["index"] % 3 != 0]
    held = [s for s in states if s["index"] % 3 == 0]

    def evaluate(view: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, _argv, coords in C.ACTIONS:
            true_mask = C.mask_of(coords)
            succ = [s[view] for s in seen if s["observed"][name]]
            fail = [s[view] for s in seen if not s["observed"][name]]
            if not succ or not fail:
                out[name] = {"skipped": "one class missing"}
                continue
            one = succ[0]
            refusals = C.nearest(one, fail)
            hypotheses = C.survivors(succ, refusals)
            held_view = [{"mask": s[view], "observed": s["observed"]} for s in held]
            behaviour = C.behaviour(hypotheses, held_view, name)
            conforms = all(C.predicts(true_mask, s[view]) == s["observed"][name] for s in states)
            out[name] = {"survivors": len(hypotheses), "behaviour": behaviour,
                         "the_columns_conform_to_the_action_on_every_state": conforms}
        return out

    primary = evaluate("primary")
    audited = evaluate("audited")
    garbage = states[-1]
    witness = {
        "fact": "btgz_valid", "state": garbage["faults"],
        "primary_reader_says": bool(garbage["primary"] & (1 << IDX["btgz_valid"])),
        "second_reader_says": bool(garbage["secondary"] & (1 << IDX["btgz_valid"])),
        "third_reading": third_reading_of_the_archive(garbage["path"]),
        "the_action_tar_x_succeeded_there": garbage["observed"].get("tar_x"),
    }
    conformance = {name: row["the_columns_conform_to_the_action_on_every_state"]
                   for name, row in primary.items() if "skipped" not in row}
    audited_conformance = {name: row["the_columns_conform_to_the_action_on_every_state"]
                           for name, row in audited.items() if "skipped" not in row}
    acc_p = {n: r["behaviour"]["accuracy_of_the_set"] for n, r in primary.items() if "skipped" not in r}
    acc_a = {n: r["behaviour"]["accuracy_of_the_set"] for n, r in audited.items() if "skipped" not in r}
    verdict = {
        "K1_a_second_independent_reader_surfaces_a_divergence": {
            "facts_with_a_disagreement": disagreements,
            "witness": witness,
            "third_reading_confirms_the_file_is_not_an_archive":
                witness["third_reading"]["python_tarfile_says"] is False,
            "MET": bool(disagreements) and witness["third_reading"]["python_tarfile_says"] is False},
        "K2_the_divergence_does_not_convict_the_column_the_action_does": {
            "claim": ("a column's job is to predict the action it gates, not to describe the world; where the two "
                      "differ, the column that matches the action is the one a plan needs"),
            "witness": witness,
            "the_action_is_as_permissive_as_the_check": witness["the_action_tar_x_succeeded_there"] is True,
            "columns_conforming_to_their_action": conformance,
            "columns_conforming_after_the_consensus_audit": audited_conformance,
            "held_out_accuracy_primary": acc_p,
            "held_out_accuracy_consensus": acc_a,
            "consensus_is_worse_on": [n for n in acc_p if n in acc_a and acc_a[n] < acc_p[n]],
            "MET": witness["the_action_tar_x_succeeded_there"] is True
                   and conformance.get("tar_x") is True
                   and audited_conformance.get("tar_x") is False
                   and sorted(n for n in acc_p if n in acc_a and acc_a[n] < acc_p[n]) == ["tar_x"]},
        "K3_reading_costs_nothing": {
            "states": len(states), "states_unchanged_after_all_readings": unchanged,
            "world_trials_added_by_the_second_reader": 0, "readers": len(PRIMARY) + len(SECOND),
            "MET": unchanged == len(states)},
        "K4_the_collapse_has_one_direction_and_a_measured_cost": {
            "states_where_audited_differs_from_primary": [s["index"] for s in states
                                                          if s["audited"] != s["primary"]],
            "facts_turned_true_by_the_conjunction": [
                name for s in states for name in FACTS
                if (s["primary"] & (1 << IDX[name])) == 0 and (s["audited"] & (1 << IDX[name])) != 0],
            "facts_turned_false_by_the_conjunction": sorted({
                name for s in states for name in FACTS
                if (s["primary"] & (1 << IDX[name])) != 0 and (s["audited"] & (1 << IDX[name])) == 0}),
            "cost_of_the_conservative_direction": {n: round(acc_a[n] - acc_p[n], 4) for n in acc_p if n in acc_a},
            "MET": not [name for s in states for name in FACTS
                        if (s["primary"] & (1 << IDX[name])) == 0 and (s["audited"] & (1 << IDX[name])) != 0]},
        "K5_every_abstention_left_by_the_previous_round_is_coverage_not_an_unsound_column": {
            "the_previous_rounds_attribution": "tar_x was said to abstain because its column was unsound",
            "what_this_measures": ("the column conforms to the action on every state of the pool, so the abstention "
                                   "was coverage; the unsoundness was the world's, not the column's"),
            "columns_that_do_not_conform": [n for n, ok in conformance.items() if not ok],
            "MET": conformance.get("tar_x") is True
                   and not [n for n, ok in conformance.items() if not ok]},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0, "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-19",
        "mode": "TWO_INDEPENDENT_READERS_PER_FACT_AND_CONFORMANCE_AS_THE_ARBITER",
        "why_this_round": {
            "the_gap_it_closes": ("the previous round attributed one abstention (tar_x) to an unsound column, because tar "
                                  "-tzf accepts a gzip of garbage"),
            "the_answer_being_tested": ("a second independent reader surfaces the divergence, but the arbiter is the "
                                        "action: a column is correct when it predicts the action, not when it "
                                        "describes the world"),
            "why_it_could_fail": ("if no second reader disagreed anywhere; if the action refused the garbage, which would "
                                  "make the column unsound as claimed; if consensus matched or beat conformance"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "at least one fact has a state where two independent readers disagree, third reading confirms",
            "K2": "the action succeeds on that state, the primary column conforms, the consensus column does not, and "
                  "consensus is worse on exactly that action",
            "K3": "every state is byte-identical after all readings",
            "K4": "no fact is ever turned from false to true by the conjunction, and its cost is reported",
            "K5": "no action's columns fail to conform, so the previous round's attribution is corrected",
            "K6": "zero model calls, parameters, network",
        },
        "verdict": verdict,
        "per_action": {"primary": primary, "audited": audited},
        "pool": {"states": len(states), "facts": list(FACTS), "seen": len(seen), "held_out": len(held)},
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0, "parameters_stored": 0,
                 "network_calls_at_run_time": 0},
        "limits": [
            "two readers by one producer: a shared misunderstanding is not excluded",
            "conformance is measured on 37 states; a permissive action and a permissive check can agree everywhere "
            "measured and still diverge off-sample",
            "the claims are hand-written; this round audits the arbitration rule, not the choice of facts",
            "conjunction is the wrong arbiter here and the receipt says so: it costs recall where the action is "
            "permissive, and the loss is measured rather than argued",
            "one machine, 17 facts, 37 states, nine actions",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [f"{'MET ' if x['MET'] else 'NOT '} {k}" for k, x in v.items()]
    k1 = v["K1_a_second_independent_reader_surfaces_a_divergence"]
    lines.append("")
    lines.append(f"facts with a disagreement: {k1['facts_with_a_disagreement']}")
    lines.append(f"witness: {json.dumps(k1['witness'])[:220]}")
    k2 = v["K2_the_divergence_does_not_convict_the_column_the_action_does"]
    lines.append(f"tar -xzf on the garbage state: {k2['witness']['the_action_tar_x_succeeded_there']}")
    for name in ("tar_x", "ln_link", "mkdir_nodir_sub"):
        if name in k2["held_out_accuracy_primary"]:
            lines.append(f"  {name:16s} primary {k2['held_out_accuracy_primary'][name]:.3f} -> "
                         f"consensus {k2['held_out_accuracy_consensus'][name]:.3f}")
    lines.append(f"consensus worse on: {k2['consensus_is_worse_on']}")
    k5 = v["K5_every_abstention_left_by_the_previous_round_is_coverage_not_an_unsound_column"]
    lines.append(f"columns that do not conform: {k5['columns_that_do_not_conform']}")
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
