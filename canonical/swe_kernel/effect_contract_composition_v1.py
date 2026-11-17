#!/usr/bin/env python3
"""Effect-carrying skill contracts (P, O, A, V, F) — compose only what is compatible.

THE DEFECT THIS CLOSES
----------------------
Two individually verified skills do not compose. Measured 2026-11-12
(`SKILLS_DONT_COMPOSE_20261112_V1.md`): teach A `x <= 10` -> `x < 10` and teach B
`x < 10` -> `x <= 10`, apply both, net change none — every local check passes.

Two organs already exist and are deliberately NOT replaced here:

  * `skill_sequence_verify_v1` — textual, post-hoc: names a revert after the fact.
  * `proved_composition_v1`     — runtime premise/proof/history on a concrete state;
                                  refuses dead premises before execution and names
                                  STEP_REVERTED_EARLIER_STATE via the history check.

Neither is a *contract* check. A contract check is static and declarative: it reads
only what each skill DECLARES about itself (preconditions, observables, actions,
verdict instrument, effects) and refuses an incompatible pair before any state is
touched. That is the missing half named as rank-2 in
`WHAT_IS_REAL_AND_THE_ONE_CLASS_OF_PAGE_20261117_V1.md` §9 and converges on by the
Nov-2026 literature (Skill-V arXiv:2610.11781 — skills as versioned falsifiable
contracts with pre/postconditions; CompoSkill arXiv:2608.16246 — per-item
verification is not composition verification).

THE FIVE FIELDS (the owner's three barriers, one organ)
-------------------------------------------------------
  P  preconditions   what must hold before this skill may run
  O  observables     names the skill READS from the representation
                     (vocabulary barrier: if the cause is not in O, no verdict
                      over O can separate success from failure)
  A  actions         what the skill does (declared, not inferred here)
  V  verdict         the instrument that decides success
                     (identifiability + synthesis-verification: a skill with no
                      separating verdict cannot identify or repair itself)
  F  effects         postconditions: claims that hold AFTER the skill runs
                     (composition barrier: F_A must not be undone by F_B)

THE RULE (checks, in order, first failure wins)
----------------------------------------------
  1. COMPLETE   every field present; O, V, F non-empty; V names a real instrument.
                Missing O  => INSUFFICIENT_OBSERVABLES  (vocabulary barrier)
                missing V  => NO_SEPARATING_VERDICT     (identifiability barrier)
  2. COVERAGE   every precondition of B is satisfied by A's effects (or is already
                an axiom both share). Unsatisfied P_B => PRECONDITION_NOT_ESTABLISHED.
  3. UNDO       full inverse on the same subjects:
                  establish(B) ⊇ remove(A)  AND  remove(B) ⊇ establish(A)
                => EFFECT_UNDO. This is the measured no-op pair, refused here
                WITHOUT running sequence or history checks.
  4. PASS       otherwise CONTRACT_COMPATIBLE.

A partial overlap (a later skill advancing past an earlier claim) is NOT an undo:
C that replaces `x < 10` with `x < 11` removes what A established but does not
restore what A removed, so it is compatible. Only the full inverse — restore what
was removed AND remove what was established — is refused.

RELATION TO THE OTHER TWO
-------------------------
Same measured defect, three complementary instruments:
  * sequence verify: post-hoc textual witness (no premises, no effects);
  * proved composition: runtime premise/proof/history on concrete state;
  * this module: static declared-effect compatibility, before any state exists.
The measured no-op pair must be refused by all three, each under its own name.

AUTHORITY: NONE. Producer-run sandbox measurement. No model, no network, no spend.
Every number this module reports is folded from its own run.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_EFFECT_CONTRACT_COMPOSITION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

# verdicts
PASS = "CONTRACT_COMPATIBLE"
INCOMPLETE = "INCOMPLETE_CONTRACT"
NO_OBSERVABLES = "INSUFFICIENT_OBSERVABLES"
NO_VERDICT = "NO_SEPARATING_VERDICT"
PRECONDITION_UNMET = "PRECONDITION_NOT_ESTABLISHED"
UNDO = "EFFECT_UNDO"
RAISED = "CONTRACT_CHECK_RAISED"


# --------------------------------------------------------------------------- #
# the contract
# --------------------------------------------------------------------------- #
@dataclasses.dataclass(frozen=True)
class Effect:
    """One declared effect claim.

    kind  ESTABLISH | REMOVE
    subject  a feature the claim is about (opaque to this organ; compared by string)
    """
    kind: str          # "ESTABLISH" | "REMOVE"
    subject: str

    def __post_init__(self) -> None:
        if self.kind not in ("ESTABLISH", "REMOVE"):
            raise ValueError(f"EFFECT_KIND_UNSUPPORTED:{self.kind}")
        if not self.subject or not isinstance(self.subject, str):
            raise ValueError("EFFECT_SUBJECT_REQUIRED")


@dataclasses.dataclass(frozen=True)
class EffectContract:
    """P, O, A, V, F — what a skill declares about itself.

    skill_id       stable name
    preconditions  P: subjects that must hold before (strings; compared to F of the prior skill)
    observables    O: names the skill reads (non-empty required)
    actions        A: declared actions (non-empty required)
    verdict        V: named instrument that decides success (non-empty, not 'none'/'self')
    effects        F: Effect claims that hold after the skill runs
    """
    skill_id: str
    preconditions: tuple[str, ...]
    observables: tuple[str, ...]
    actions: tuple[str, ...]
    verdict: str
    effects: tuple[Effect, ...]

    @classmethod
    def of(
        cls,
        skill_id: str,
        *,
        preconditions: Sequence[str],
        observables: Sequence[str],
        actions: Sequence[str],
        verdict: str,
        effects: Sequence[Effect | tuple[str, str] | Mapping[str, str]],
    ) -> "EffectContract":
        normalized: list[Effect] = []
        for e in effects:
            if isinstance(e, Effect):
                normalized.append(e)
            elif isinstance(e, tuple) and len(e) == 2:
                normalized.append(Effect(e[0], e[1]))
            elif isinstance(e, Mapping):
                normalized.append(Effect(str(e["kind"]), str(e["subject"])))
            else:
                raise ValueError("EFFECT_SHAPE_UNSUPPORTED")
        return cls(
            skill_id=str(skill_id),
            preconditions=tuple(str(p) for p in preconditions),
            observables=tuple(str(o) for o in observables),
            actions=tuple(str(a) for a in actions),
            verdict=str(verdict),
            effects=tuple(normalized),
        )

    def established(self) -> frozenset[str]:
        return frozenset(e.subject for e in self.effects if e.kind == "ESTABLISH")

    def removed(self) -> frozenset[str]:
        return frozenset(e.subject for e in self.effects if e.kind == "REMOVE")


# --------------------------------------------------------------------------- #
# completeness (barriers 1 and 2: vocabulary + identifiability)
# --------------------------------------------------------------------------- #
def _is_real_verdict(verdict: str) -> bool:
    v = verdict.strip().lower()
    if not v:
        return False
    return v not in {
        "none", "self", "self_judge", "always_pass", "majority_vote",
        "screen", "stdout", "truthiness", "name", "true", "1", "yes",
    }


def check_complete(contract: EffectContract) -> tuple[str, str] | None:
    """None when complete; else (verdict, reason)."""
    if not contract.observables:
        return (NO_OBSERVABLES, f"{contract.skill_id}:NO_OBSERVABLES")
    if not contract.actions:
        return (INCOMPLETE, f"{contract.skill_id}:NO_ACTIONS")
    if not contract.verdict.strip():
        return (NO_VERDICT, f"{contract.skill_id}:NO_VERDICT")
    if not _is_real_verdict(contract.verdict):
        return (NO_VERDICT, f"{contract.skill_id}:VERDICT_NOT_SEPARATING:{contract.verdict}")
    if not contract.effects:
        return (INCOMPLETE, f"{contract.skill_id}:NO_EFFECTS")
    return None


# --------------------------------------------------------------------------- #
# coverage: do A's effects establish B's preconditions?
# --------------------------------------------------------------------------- #
def check_coverage(a: EffectContract, b: EffectContract) -> tuple[str, str] | None:
    """Every precondition of B must be among A's established effects (or axioms.

    An axiom is a precondition B lists that A also lists — shared context both
    skills take for granted. Anything else B needs must come from A's F.
    """
    shared = set(a.preconditions) & set(b.preconditions)
    established = a.established()
    for req in b.preconditions:
        if req in shared or req in established:
            continue
        return (PRECONDITION_UNMET, f"{b.skill_id}:P_NOT_IN_F_OF_{a.skill_id}:{req}")
    return None


# --------------------------------------------------------------------------- #
# undo: full inverse on the same subjects
# --------------------------------------------------------------------------- #
def check_undo(a: EffectContract, b: EffectContract) -> tuple[str, str] | None:
    """Refuse only the full inverse — the measured no-op/revert class.

    undo  <=>  establish(B) ⊇ remove(A)  AND  remove(B) ⊇ establish(A)

    Partial overlap (a later skill advancing past an earlier claim) is compatible.
    """
    est_a, rem_a = a.established(), a.removed()
    est_b, rem_b = b.established(), b.removed()
    restores = est_b & rem_a          # B re-establishes what A removed
    retracts = rem_b & est_a          # B removes what A established
    if restores and retracts and restores >= rem_a and retracts >= est_a:
        return (UNDO, f"{b.skill_id}:EFFECT_UNDO_OF_{a.skill_id}")
    return None


# --------------------------------------------------------------------------- #
# compose
# --------------------------------------------------------------------------- #
def compose_contracts(
    a: EffectContract,
    b: EffectContract,
) -> dict[str, Any]:
    """Static declared-effect compatibility of A then B. No state, no execution.

    Returns a receipt dict: verdict, reason, field-level traces, digests.
    """
    started = time.time()
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "a": a.skill_id,
        "b": b.skill_id,
        "a_sha256": _contract_sha(a),
        "b_sha256": _contract_sha(b),
        "checks": {},
        "model_dependency_count": 0,
        "network_calls_at_run_time": 0,
    }
    try:
        for name, c in (("a", a), ("b", b)):
            fail = check_complete(c)
            receipt["checks"][f"complete_{name}"] = (
                "PASS" if fail is None else fail[0]
            )
            if fail is not None:
                receipt["verdict"] = fail[0]
                receipt["reason"] = fail[1]
                receipt["seconds"] = round(time.time() - started, 4)
                return receipt

        cov = check_coverage(a, b)
        receipt["checks"]["coverage"] = "PASS" if cov is None else cov[0]
        if cov is not None:
            receipt["verdict"] = cov[0]
            receipt["reason"] = cov[1]
            receipt["seconds"] = round(time.time() - started, 4)
            return receipt

        undo = check_undo(a, b)
        receipt["checks"]["undo"] = "PASS" if undo is None else undo[0]
        if undo is not None:
            receipt["verdict"] = undo[0]
            receipt["reason"] = undo[1]
            receipt["seconds"] = round(time.time() - started, 4)
            return receipt

        receipt["verdict"] = PASS
        receipt["reason"] = "EFFECTS_COMPATIBLE"
        receipt["seconds"] = round(time.time() - started, 4)
        return receipt
    except Exception as error:  # noqa: BLE001
        receipt["verdict"] = RAISED
        receipt["reason"] = f"{type(error).__name__}:{error}"
        receipt["seconds"] = round(time.time() - started, 4)
        return receipt


def compose_chain(contracts: Sequence[EffectContract]) -> dict[str, Any]:
    """Pairwise-compose a chain; first incompatibility wins."""
    if len(contracts) < 2:
        return {
            "schema": SCHEMA,
            "verdict": INCOMPLETE,
            "reason": "CHAIN_TOO_SHORT",
            "steps": [],
        }
    steps: list[dict[str, Any]] = []
    for i in range(len(contracts) - 1):
        outcome = compose_contracts(contracts[i], contracts[i + 1])
        steps.append(outcome)
        if outcome["verdict"] != PASS:
            return {
                "schema": SCHEMA,
                "verdict": outcome["verdict"],
                "reason": outcome["reason"],
                "refused_at_pair": i + 1,
                "steps": steps,
            }
    return {
        "schema": SCHEMA,
        "verdict": PASS,
        "reason": "CHAIN_COMPATIBLE",
        "steps": steps,
    }


def _contract_sha(c: EffectContract) -> str:
    payload = json.dumps(
        {
            "skill_id": c.skill_id,
            "preconditions": list(c.preconditions),
            "observables": list(c.observables),
            "actions": list(c.actions),
            "verdict": c.verdict,
            "effects": [{"kind": e.kind, "subject": e.subject} for e in c.effects],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# the measured no-op pair, as contracts (from SKILLS_DONT_COMPOSE_20261112)
# --------------------------------------------------------------------------- #
def measured_no_op_pair() -> tuple[EffectContract, EffectContract]:
    """A then B: the pair that each verifies locally and cancels globally."""
    a = EffectContract.of(
        "A_TIGHTEN_LE_TO_LT",
        preconditions=("comparator:<=:10",),
        observables=("source:return-comparison",),
        actions=("replace:<=:<",),
        verdict="crystallizer:verified_pattern_match",
        effects=(
            ("ESTABLISH", "comparator:<:10"),
            ("REMOVE", "comparator:<=:10"),
        ),
    )
    b = EffectContract.of(
        "B_LOOSEN_LT_TO_LE",
        preconditions=("comparator:<:10",),
        observables=("source:return-comparison",),
        actions=("replace:<:<=",),
        verdict="crystallizer:verified_pattern_match",
        effects=(
            ("ESTABLISH", "comparator:<=:10"),
            ("REMOVE", "comparator:<:10"),
        ),
    )
    return a, b


def measured_advance_pair() -> tuple[EffectContract, EffectContract]:
    """A then C: tighten, then legitimately advance — must stay compatible."""
    a, _ = measured_no_op_pair()
    c = EffectContract.of(
        "C_ADVANCE_LT_TO_LT11",
        preconditions=("comparator:<:10",),
        observables=("source:return-comparison",),
        actions=("replace:10:11",),
        verdict="crystallizer:verified_pattern_match",
        effects=(
            ("ESTABLISH", "comparator:<:11"),
            ("REMOVE", "comparator:<:10"),
        ),
    )
    return a, c


# --------------------------------------------------------------------------- #
# cross-instrument: sequence + proved_composition + this contract layer
# --------------------------------------------------------------------------- #
def _cross_instrument() -> dict[str, Any]:
    """Run the same measured pairs through all three organs.

    Refusal must be unanimous for the no-op pair (each under its own name) and
    acceptance unanimous for the advance pair. If any instrument disagrees the
    fold fails — a single instrument cannot carry the claim alone.
    """
    forward_before = "def f(x):\n    return x <= 10\n"
    forward_after = "def f(x):\n    return x < 10\n"
    backward_before = "def f(x):\n    return x < 10\n"
    backward_after = "def f(x):\n    return x <= 10\n"
    advance_after = "def f(x):\n    return x < 11\n"

    import json as _json
    import sqlite3 as _sqlite3
    import tempfile as _tempfile

    from canonical.swe_kernel import proved_composition_v1 as _P
    from canonical.swe_kernel.skill_sequence_verify_v1 import verify_sequence
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

    def _crystallize(pairs: list[tuple[str, str, str]]) -> list[dict]:
        with _tempfile.TemporaryDirectory() as td:
            db = pathlib.Path(td) / "s.sqlite"
            store = VerifiedSkillStore(db_path=db, seed=False)
            for before, after, error_class in pairs:
                result = store.crystallize_code_fix(
                    before_snippet=before, after_snippet=after,
                    language="python", error_class=error_class,
                )
                if not result.get("crystallized"):
                    raise RuntimeError(f"CRYSTALLIZE_FAILED:{error_class}:{result}")
            conn = _sqlite3.connect(str(db))
            try:
                return [
                    _json.loads(row[0])
                    for row in conn.execute(
                        "SELECT pattern_json FROM crystallized_skills"
                    )
                ]
            finally:
                conn.close()

    noop_rules = _crystallize([
        (forward_before, forward_after, "A"),
        (backward_before, backward_after, "B"),
    ])
    adv_rules = _crystallize([
        (forward_before, forward_after, "A"),
        (forward_before.replace("<= 10", "< 10"), advance_after, "C"),
    ])

    noop_seq = verify_sequence(forward_before, noop_rules)
    noop_prov = _P.compose(
        forward_before,
        [_P.rule_op("A", noop_rules[0]), _P.rule_op("B", noop_rules[1])],
    )
    a, b = measured_no_op_pair()
    noop_con = compose_contracts(a, b)

    adv_seq = verify_sequence(forward_before, adv_rules)
    adv_prov = _P.compose(
        forward_before,
        [_P.rule_op("A", adv_rules[0]), _P.rule_op("C", adv_rules[1])],
    )
    a2, c = measured_advance_pair()
    adv_con = compose_contracts(a2, c)

    return {
        "no_op": {
            "sequence": {"verdict": noop_seq["verdict"],
                         "reason": noop_seq.get("reason")},
            "proved_composition": {"verdict": noop_prov["verdict"],
                                   "reason": noop_prov.get("reason")},
            "contract": {"verdict": noop_con["verdict"],
                         "reason": noop_con["reason"]},
        },
        "advance": {
            "sequence": {"verdict": adv_seq["verdict"],
                         "reason": adv_seq.get("reason")},
            "proved_composition": {"verdict": adv_prov["verdict"],
                                   "reason": adv_prov.get("reason")},
            "contract": {"verdict": adv_con["verdict"],
                         "reason": adv_con["reason"]},
        },
        "all_three_refuse_no_op": (
            noop_seq["verdict"] != "PASS"
            and noop_prov["verdict"] == _P.REVERTED
            and noop_con["verdict"] == UNDO
        ),
        "all_three_pass_advance": (
            adv_seq["verdict"] == "PASS"
            and adv_prov["verdict"] == _P.PASS
            and adv_con["verdict"] == PASS
        ),
        "model_dependency_count": 0,
        "network_calls_at_run_time": 0,
    }


# --------------------------------------------------------------------------- #
# CLI: fold a receipt from the measured pairs
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    a, b = measured_no_op_pair()
    undo = compose_contracts(a, b)
    a2, c = measured_advance_pair()
    advance = compose_contracts(a2, c)

    # incomplete / no-verdict barriers
    weak = EffectContract.of(
        "WEAK_NO_VERDICT",
        preconditions=(),
        observables=("source",),
        actions=("replace",),
        verdict="self",
        effects=(("ESTABLISH", "x"),),
    )
    weak_out = compose_contracts(a, weak)

    no_obs = EffectContract.of(
        "WEAK_NO_OBSERVABLES",
        preconditions=(),
        observables=(),
        actions=("replace",),
        verdict="pytest",
        effects=(("ESTABLISH", "x"),),
    )
    no_obs_out = compose_contracts(no_obs, a)

    # Cross-instrument: the two pre-existing organs must refuse the SAME pair
    # under their own names, and accept the advance pair. Folded here so this
    # receipt is self-contained evidence that all three instruments agree.
    cross = _cross_instrument()

    receipt = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_dependency_count": 0,
        "network_calls_at_run_time": 0,
        "incremental_spend_usd": 0,
        "measured": {
            "no_op_pair": undo,
            "advance_pair": advance,
            "weak_verdict": weak_out,
            "missing_observables": no_obs_out,
        },
        "cross_instrument": cross,
        "summary": {
            "no_op_pair_refused_by_contract": undo["verdict"] == UNDO,
            "advance_pair_compatible": advance["verdict"] == PASS,
            "weak_verdict_refused": weak_out["verdict"] == NO_VERDICT,
            "missing_observables_refused": no_obs_out["verdict"] == NO_OBSERVABLES,
            "contract_layer_did_not_run_sequence_or_history": True,
            "all_three_instruments_refuse_no_op": cross["all_three_refuse_no_op"],
            "all_three_instruments_pass_advance": cross["all_three_pass_advance"],
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    ok = all(receipt["summary"].values())
    receipt["audit_pass"] = ok

    text = json.dumps(receipt, indent=1) + "\n"
    if args.out:
        pathlib.Path(args.out).write_text(text)
    print(
        f"no_op={undo['verdict']} advance={advance['verdict']} "
        f"weak={weak_out['verdict']} no_obs={no_obs_out['verdict']} "
        f"audit_pass={ok}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
