"""THE MODEL IS NOT MISSING. IT WAS NEVER IN THE FILE.

r60 ranked "attach a model to selection" as rank 1 and said it could not be done from inside
this repository, because the repository contains 0 parameters. That was true about the files
and false about the system: every round was written by a language model that read the goals,
chose the code, and could equally have chosen the skill. The model has been in the loop since
round 34. It was just never given a socket.

This module is that socket, and nothing else. It defines the exact seam:

    an LLM reads (goal, catalog) and writes PROPOSALS -- a structured artifact
    this module loads the artifact and hands each proposal to the existing gate
    the gate decides whether the proposal may become an answer

Why an artifact and not an API call: no credential, no network dependency, and -- the reason
that matters -- the proposal is a FILE. It can be diffed, replayed, re-scored and audited
after the fact. A model whose choices are not recorded cannot be held to them.

The contract, and its only exit:

    proposal: {ask, skill_id, confidence, because}
    result:   ANSWERED | ASK | REFUSED_BY_GATE

A wrong proposal cannot become an answer. That is what the last twenty-eight rounds built,
and it is what makes attaching a model safe rather than optimistic.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Mapping

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

SCHEMA = "MODEL_PROPOSES_V1"


def load_proposals(path: str | pathlib.Path) -> dict[str, dict[str, Any]]:
    """Read the artifact a model wrote. Keyed by the ask it answers."""
    blob = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for p in blob.get("proposals", []):
        out[str(p["ask"])] = p
    return out


def answer_from_proposal(
    ask: str,
    proposal: Mapping[str, Any] | None,
    *,
    cwd: str | pathlib.Path | None = None,
    db_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Turn one recorded model choice into an answer, or refuse it.

    Three outcomes and no fourth. Note what is NOT here: there is no path where a
    low-confidence proposal becomes an answer. Confidence is recorded so it can be audited
    later; it is not a licence.
    """
    if proposal is None:
        return {"schema": SCHEMA, "ask": ask, "verdict": "NO_PROPOSAL"}
    if proposal.get("skill_id") in (None, "", "ABSTAIN"):
        return {"schema": SCHEMA, "ask": ask, "verdict": "ASK",
                "because": proposal.get("because"),
                "note": "the model declined; this is the correct behaviour under r55's ceiling"}
    skill_id = str(proposal["skill_id"])
    rows = [r for r in K._load_cached_skills(db_path=db_path)
            if isinstance(r, Mapping) and r.get("skill_id") == skill_id]
    if not rows:
        return {"schema": SCHEMA, "ask": ask, "verdict": "REFUSED_BY_GATE",
                "reason": "PROPOSED_SKILL_NOT_IN_THE_CATALOG", "skill_id": skill_id}
    skill = rows[0]
    bindings = K._bind_by_verb_selection(skill, ask, cwd)
    if bindings is None:
        return {"schema": SCHEMA, "ask": ask, "verdict": "REFUSED_BY_GATE",
                "reason": "NO_BINDING", "skill_id": skill_id}
    steps = K._instantiate_obj(skill["abstract_steps"], bindings)
    if not K._steps_are_all_carried(steps):
        return {"schema": SCHEMA, "ask": ask, "verdict": "REFUSED_BY_GATE",
                "reason": "NOT_CARRIED", "skill_id": skill_id}
    res = K.execute_compiled_steps(steps, cwd=cwd)
    if not res.get("ok"):
        return {"schema": SCHEMA, "ask": ask, "verdict": "REFUSED_BY_GATE",
                "reason": "EXECUTION_FAILED", "skill_id": skill_id}
    ok, why = K.verify_postcondition(skill.get("abstract_postcondition"),
                                     cwd=cwd, execution_result=res)
    if not ok:
        return {"schema": SCHEMA, "ask": ask, "verdict": "REFUSED_BY_GATE",
                "reason": f"POSTCONDITION_FAILED:{why}", "skill_id": skill_id}
    # r61: the operation the GOAL named must be the operation that ran
    cok, creason = K.verify_operation_commitment(K.infer_operation_commitment(ask), res)
    if not cok:
        return {"schema": SCHEMA, "ask": ask, "verdict": "REFUSED_BY_GATE",
                "reason": f"OPERATION_NOT_HONOURED:{creason}", "skill_id": skill_id}
    # r63: THE SHAPE GATE WAS MISSING FROM THIS PATH.
    #
    # Found by writing deliberately bad proposals rather than by reading the code: with the
    # model attached, "sha256 of" answered by `cat` returned the file contents and was
    # ACCEPTED, and "how many lines are in" answered by `sort -u` returned a listing and was
    # ACCEPTED. Both pass the skill's own postcondition -- the skill did what its contract
    # says -- and both are wrong answers to the question that was asked. The r49 shape audit
    # already existed and was simply not wired here, because until now nothing proposed a
    # skill that the question had not also selected.
    answer = K._contract_answer(skill.get("abstract_postcondition"), res)
    shape = K.audit_answer_shape(ask, {"answer": answer})
    if shape.get("shape_matches") is False:
        return {"schema": SCHEMA, "ask": ask, "verdict": "REFUSED_BY_GATE",
                "reason": f"ANSWER_SHAPE_DOES_NOT_MATCH_THE_GOAL:{shape.get('verdict')}",
                "skill_id": skill_id, "would_have_said": answer}
    return {"schema": SCHEMA, "ask": ask, "verdict": "ANSWERED",
            "answer": answer,
            "skill_id": skill_id, "operation": K._operation_signature(skill),
            "because": proposal.get("because"), "confidence": proposal.get("confidence"),
            "verification": creason}
