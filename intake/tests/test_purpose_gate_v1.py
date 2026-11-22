"""The purpose gate may ask only on a real contrast, and only an authorized typed answer lands.

Every trace is executed on a real machine. No verdict is hand-written.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
for path in (str(ROOT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402

from intake import bulk_copy_environment_v1 as bulk  # noqa: E402
from intake import purpose_gate_v1 as P  # noqa: E402
from intake import residual_question_gate_v1 as G  # noqa: E402

ARGS = {"content": env.PROBE_NEW, "old": env.PROBE_OLD,
        "name": "seed", "target": "copy"}
CREATED = "created_once[probe_new_content]"
MONOTONE = "monotone[probe_new_content] and final:count[probe_new_content]==1"


def _candidates() -> list[G.Candidate]:
    def created(trace: G.Trace) -> bool:
        return runs._increased_once(trace, env.PROBE_NEW)

    def monotone_final_one(trace: G.Trace) -> bool:
        return (runs._count(trace[-1], env.PROBE_NEW) == 1
                and all(runs._count(trace[i + 1], env.PROBE_NEW)
                        >= runs._count(trace[i], env.PROBE_NEW)
                        for i in range(len(trace) - 1)))

    return G.from_predicates([(CREATED, created), (MONOTONE, monotone_final_one)])


def _traces(kind: str, root: pathlib.Path) -> list[G.Trace]:
    if kind == "GIT":
        machine = env.build_git(root)
        depth = 2
    else:
        machine = bulk.build(root)
        depth = 1
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    return runs.traces_for(machine, ARGS, depth=depth)


def _state(answer: dict[str, object] | None = None) -> dict[str, object]:
    return {"instruction": "probe_new_content must arrive once and stay",
            "authorized_users": ["owner"], "purpose_answer": answer}


def _answer(decision: dict[str, object], *, author: str = "owner") -> dict[str, object]:
    options = decision["payload"]["options"]
    return {
        "author": author,
        "instruction_sha256": decision["instruction_sha256"],
        "question_fingerprint": decision["question_fingerprint"],
        "kind": P.ANSWER_KIND,
        "candidate_id": options[0]["candidate_id"],
    }


def test_zero_information_residual_is_not_asked(tmp_path: pathlib.Path) -> None:
    state = _state({"schema": "x"})  # deliberately malformed; must be ignored
    decision = P.decide(state, _candidates(), _traces("GIT", tmp_path),
                        goal_judge=quotient.portable_judge)
    assert decision["action"] == P.NO_QUESTION
    assert decision["gate"]["distinguishing_runs"] == 0
    assert "payload" not in decision


def test_real_contrast_asks_and_accepts_only_a_typed_authorized_selection(
        tmp_path: pathlib.Path) -> None:
    candidates = _candidates()
    traces = _traces("BULK_COPY", tmp_path)
    open_question = P.decide(_state(), candidates, traces,
                             goal_judge=quotient.portable_judge)
    assert open_question["action"] == P.ASK_USER
    assert open_question["gate"]["distinguishing_runs"] == 1
    assert quotient.portable_judge(traces[0]) is False
    mismatches = open_question["gate"]["mismatches_with_goal_judge"]
    assert sorted(mismatches.values()) == [0, 1]
    correct_id = next(cid for cid, count in mismatches.items() if count == 0)
    correct = next(option for option in open_question["payload"]["options"]
                   if option["candidate_id"] == correct_id)
    assert correct["text"] == MONOTONE

    bad_author = P.decide(_state(_answer(open_question, author="stranger")), candidates, traces)
    assert bad_author["reason"] == "ANSWER_AUTHOR_NOT_AUTHORIZED"

    bad_candidate = _answer(open_question)
    bad_candidate["candidate_id"] = "not-in-the-residual"
    assert P.decide(_state(bad_candidate), candidates, traces)["reason"] == \
        "CANDIDATE_NOT_IN_COMPUTED_RESIDUAL"

    bad_kind = _answer(open_question)
    bad_kind["kind"] = "FREE_PROSE"
    assert P.decide(_state(bad_kind), candidates, traces)["reason"] == "ANSWER_KIND_UNSUPPORTED"

    accepted = P.decide(_state(_answer(open_question)), candidates, traces)
    assert accepted["action"] == P.ACCEPTED
    assert accepted["chosen_text"] in {CREATED, MONOTONE}
    assert accepted["action"] != "DONE"


def test_persistence_is_external_deletable_and_reversible(tmp_path: pathlib.Path) -> None:
    candidates = _candidates()
    traces = _traces("BULK_COPY", tmp_path / "machine")
    store = tmp_path / "purpose_store.json"
    answer = _answer(P.decide(_state(), candidates, traces))
    decision = P.decide(_state(answer), candidates, traces)
    written = P.persist(_state(answer), decision, store)
    assert written["written"] == 1

    reloaded = P.stored_answer(store, decision["question_fingerprint"])
    assert reloaded is not None
    replay = P.decide(_state(P.as_state_answer(reloaded)), candidates, traces)
    assert replay["action"] == P.ACCEPTED

    store.unlink()
    assert P.load(store) == []
    assert P.decide(_state(), candidates, traces)["action"] == P.ASK_USER
