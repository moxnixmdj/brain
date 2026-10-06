from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.k6_policy_index_refinement_and_persistence_compiler_v1 import (
    PolicyIndexCompilerError,
    compile_policy_index,
)


class PositiveAdequacyCertificateError(ValueError):
    pass


def certify_positive_cover(
    *,
    worlds: Sequence[str],
    policies: Sequence[str],
    certified_adequate: Mapping[str, Sequence[str]],
    discriminators: Sequence[Mapping[str, Any]],
    commitment_deadline: float,
    separator_reacquirable_after_restart_before_deadline: bool,
    adequacy_relation_complete: bool,
    discriminator_universe_complete: bool,
) -> dict[str, Any]:
    ws = tuple(str(w) for w in worlds)
    ps = tuple(str(p) for p in policies)
    if not ws or len(set(ws)) != len(ws):
        raise PositiveAdequacyCertificateError("WORLD_DOMAIN_INVALID")
    if not ps or len(set(ps)) != len(ps):
        raise PositiveAdequacyCertificateError("POLICY_DOMAIN_INVALID")
    if not isinstance(adequacy_relation_complete, bool):
        raise PositiveAdequacyCertificateError("ADEQUACY_COMPLETENESS_FLAG_INVALID")
    if not isinstance(discriminator_universe_complete, bool):
        raise PositiveAdequacyCertificateError("DISCRIMINATOR_COMPLETENESS_FLAG_INVALID")

    pset = set(ps)
    cert: dict[str, tuple[str, ...]] = {}
    empty_worlds: list[str] = []
    for w in ws:
        if w not in certified_adequate:
            raise PositiveAdequacyCertificateError("CERTIFIED_ADEQUACY_MISSING:" + w)
        vals = tuple(dict.fromkeys(str(p) for p in certified_adequate[w]))
        if any(p not in pset for p in vals):
            raise PositiveAdequacyCertificateError("UNKNOWN_POLICY_IN_CERTIFIED_ADEQUACY:" + w)
        cert[w] = vals
        if not vals:
            empty_worlds.append(w)

    if empty_worlds:
        if adequacy_relation_complete:
            return {
                "status": "NO_ADEQUATE_POLICY_IN_COMPLETE_DECLARED_POLICY_UNIVERSE",
                "empty_worlds": empty_worlds,
                "capability_gap_candidate": True,
                "absolute_terminal_claim": False,
                "terminal_credit_delta": 0,
            }
        return {
            "status": "UNKNOWN__POSITIVE_ADEQUACY_BINDING_INCOMPLETE",
            "empty_certified_worlds": empty_worlds,
            "capability_gap_candidate": False,
            "absolute_terminal_claim": False,
            "terminal_credit_delta": 0,
        }

    try:
        out = compile_policy_index(
            worlds=ws,
            policies=ps,
            adequate=cert,
            discriminators=discriminators,
            commitment_deadline=commitment_deadline,
            separator_reacquirable_after_restart_before_deadline=separator_reacquirable_after_restart_before_deadline,
        )
    except PolicyIndexCompilerError as exc:
        raise PositiveAdequacyCertificateError(str(exc)) from exc

    relation_mode = "EXACT_DECLARED_RELATION" if adequacy_relation_complete else "SOUND_POSITIVE_SUBRELATION"
    tau_semantics = "EXACT_FOR_DECLARED_COMPLETE_RELATION" if adequacy_relation_complete else "UPPER_BOUND_ON_TRUE_MINIMUM"

    if out["status"] == "SUFFICIENT_POLICY_INDEX_PARTITION_FOUND":
        return {
            "status": "CERTIFIED_SUFFICIENT_POSITIVE_POLICY_COVER",
            "relation_mode": relation_mode,
            "selected_discriminators": out["selected_discriminators"],
            "decisions": out["decisions"],
            "certified_policy_cover": out["policy_cover"],
            "certified_cover_number_hat_tau": out["tau"],
            "hat_tau_semantics": tau_semantics,
            "certified_relation_index_bits": out["minimum_policy_index_bits"],
            "true_minimum_tau_claimed": adequacy_relation_complete,
            "sound_under_additional_true_adequacy_edges": True,
            "terminal_credit_delta": 0,
        }

    if out["status"] == "NONIDENTIFIABLE_WITH_ADMISSIBLE_PRECOMMITMENT_INFORMATION":
        if adequacy_relation_complete and discriminator_universe_complete:
            return {
                "status": "PROVED_NONIDENTIFIABLE_IN_COMPLETE_DECLARED_MODEL",
                "witness_cells": out["witness_cells"],
                "relation_mode": relation_mode,
                "absolute_terminal_claim": False,
                "terminal_credit_delta": 0,
            }
        return {
            "status": "UNKNOWN__ADEQUACY_OR_DISCRIMINATOR_BINDING_INCOMPLETE",
            "witness_cells": out["witness_cells"],
            "relation_mode": relation_mode,
            "adequacy_relation_complete": adequacy_relation_complete,
            "discriminator_universe_complete": discriminator_universe_complete,
            "absolute_terminal_claim": False,
            "terminal_credit_delta": 0,
        }

    raise PositiveAdequacyCertificateError("UNEXPECTED_COMPILER_STATUS:" + str(out["status"]))


def finite_countermodel() -> dict[str, Any]:
    worlds = ("w0", "w1")
    policies = ("p0", "p1", "p2")
    certified = {"w0": ("p0",), "w1": ("p1",)}
    discriminators = (
        {
            "id": "bit",
            "observations": {"w0": 0, "w1": 1},
            "cost": 1,
            "arrival": 0,
            "authorized": True,
            "owned_operator": True,
        },
    )
    return certify_positive_cover(
        worlds=worlds,
        policies=policies,
        certified_adequate=certified,
        discriminators=discriminators,
        commitment_deadline=0,
        separator_reacquirable_after_restart_before_deadline=True,
        adequacy_relation_complete=False,
        discriminator_universe_complete=False,
    )
