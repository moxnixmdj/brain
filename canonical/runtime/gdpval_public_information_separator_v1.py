from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Outcome = Literal["BRAIN_WIN", "TIE", "OPUS_WIN"]


@dataclass(frozen=True)
class PublicWorld:
    public_signature: str
    brain_vs_opus_outcome: Outcome


def two_publicly_indistinguishable_completions(
    public_signature: str = "GDPVAL_AA_V21_CURRENT_PUBLIC_FACTS_20261008"
) -> tuple[PublicWorld, PublicWorld]:
    """Return two completions of the same public facts with opposite unseen target order.

    The public signature stands for the currently bound GDPval-AA public structure,
    existing-model leaderboard/aggregate data, and presentation contract. Brain is
    not part of the observed owner comparison graph, so changing only the hidden
    Brain-vs-Opus relation leaves that public projection unchanged.
    """
    if not isinstance(public_signature, str) or not public_signature.strip():
        raise ValueError("public_signature must be a non-empty string")
    return (
        PublicWorld(public_signature, "BRAIN_WIN"),
        PublicWorld(public_signature, "OPUS_WIN"),
    )


def public_projection_identifies_brain_vs_opus() -> bool:
    w_brain, w_opus = two_publicly_indistinguishable_completions()
    same_observation = w_brain.public_signature == w_opus.public_signature
    different_target = w_brain.brain_vs_opus_outcome != w_opus.brain_vs_opus_outcome
    assert same_observation
    assert different_target
    return False


def classify_escape(
    *,
    explicit_owner_relation_bound: bool = False,
    proved_owner_class_excludes_opus_world: bool = False,
    exact_exchangeable_owner_visible_input_law: bool = False,
    stronger_sound_bypass_bound: bool = False,
) -> dict[str, object]:
    """Classify what information can break or bypass the current public cut.

    E and M distinguish the target worlds by binding the owner relation or a
    sound class restriction that rules out the adverse completion. U does not
    recover the hidden relation; it makes model identity irrelevant to every
    owner-visible evaluator by exact exchangeability of the complete comparison
    input law under the same anonymization and judge-sampling law.

    A future stronger sound theorem is explicitly allowed. This routine does not
    claim E/M/U are metaphysically exhaustive.
    """
    selected: list[str] = []
    if explicit_owner_relation_bound:
        selected.append("E_EXPLICIT_OWNER_RELATION")
    if proved_owner_class_excludes_opus_world:
        selected.append("M_PROVED_RESTRICTED_OWNER_CLASS")
    if exact_exchangeable_owner_visible_input_law:
        selected.append("U_EXACT_EXCHANGEABLE_INPUT_LAW_BYPASS")
    if stronger_sound_bypass_bound:
        selected.append("S_FUTURE_STRONGER_SOUND_BYPASS")

    return {
        "public_facts_identify_target_relation": False,
        "selected_escape_classes": selected,
        "current_public_cut_broken_or_bypassed": bool(selected),
        "general_metadata_search_without_new_separator": "NON_IDENTIFYING",
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def verify_current_public_information_cut() -> dict[str, object]:
    w_brain, w_opus = two_publicly_indistinguishable_completions()
    same_public_projection = w_brain.public_signature == w_opus.public_signature
    opposite_target_order = (
        w_brain.brain_vs_opus_outcome == "BRAIN_WIN"
        and w_opus.brain_vs_opus_outcome == "OPUS_WIN"
    )
    no_separator = classify_escape()

    assert same_public_projection
    assert opposite_target_order
    assert public_projection_identifies_brain_vs_opus() is False
    assert no_separator["current_public_cut_broken_or_bypassed"] is False

    return {
        "same_public_projection": same_public_projection,
        "opposite_unseen_brain_vs_opus_order": opposite_target_order,
        "current_public_facts_non_identifying": True,
        "minimum_next_information_kind": (
            "ONE_SOUND_SEPARATOR_OR_BYPASS_THAT_DISTINGUISHES_OR_MAKES_IRRELEVANT_"
            "THE_PUBLICLY_INDISTINGUISHABLE_BRAIN_WIN_AND_OPUS_WIN_COMPLETIONS"
        ),
        "known_sound_escape_classes": [
            "E_EXPLICIT_OWNER_RELATION",
            "M_PROVED_RESTRICTED_OWNER_CLASS",
            "U_EXACT_EXCHANGEABLE_INPUT_LAW_BYPASS",
            "S_FUTURE_STRONGER_SOUND_BYPASS",
        ],
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
