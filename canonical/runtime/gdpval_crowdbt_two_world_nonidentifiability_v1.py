"""Executable two-world non-identifiability witness for GDPval-AA style Crowd-BT.

Purpose:
Hold fixed one admissible public-compatible Crowd-BT world for the current
Opus-vs-anchor state, then extend it with previously unobserved Brain comparisons
in two ways that differ only in Brain judge outcomes.

If one extension fits Brain above Opus and the other below Opus, the current
public surface alone cannot decide Brain >= Opus. This does not claim the
synthetic world is the real Artificial Analysis epoch; it proves non-identifiability
whenever both extensions remain compatible with the disclosed methodology.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime.gdpval_aa_v21_crowd_bt_kernel_v1 import (
    crowd_bt_probability,
    fit_fixed_quality,
)

ANCHOR="DeepSeek V4.1 Flash (max)"
OPUS="Claude Opus 5.5 (Max, Default Fallback)"
BRAIN="Brain"
ANCHOR_ELO=1600.0
OPUS_PUBLIC_ELO=1866.0
QUALITIES={"Claude Opus 5":0.90,"GPT-5.6 Sol":0.85,"Gemini 3.8 Flash":0.80}


def _votes(a:str,b:str,judge:str,wins_a:int,total:int)->list[dict[str,Any]]:
    return (
        [{"a":a,"b":b,"judge":judge,"outcome_a":1} for _ in range(wins_a)]
        + [{"a":a,"b":b,"judge":judge,"outcome_a":0} for _ in range(total-wins_a)]
    )


def _base_graph(per_judge:int=1000)->list[dict[str,Any]]:
    rows=[]
    for judge,eta in QUALITIES.items():
        p=crowd_bt_probability(OPUS_PUBLIC_ELO,ANCHOR_ELO,eta)
        wins=round(per_judge*p)
        rows.extend(_votes(OPUS,ANCHOR,judge,wins,per_judge))
    return rows


def _brain_extension(outcome:str,per_judge:int=220)->list[dict[str,Any]]:
    if outcome not in {"ALL_BRAIN_WIN","ALL_OPUS_WIN"}:
        raise ValueError("unsupported outcome")
    rows=[]
    for judge in QUALITIES:
        brain_wins=per_judge if outcome=="ALL_BRAIN_WIN" else 0
        rows.extend(_votes(BRAIN,OPUS,judge,brain_wins,per_judge))
    return rows


def run()->dict[str,Any]:
    base=_base_graph()
    base_fit=fit_fixed_quality({
        "comparisons":base,
        "judge_quality":QUALITIES,
        "anchor_model":ANCHOR,
        "anchor_elo":ANCHOR_ELO,
    })
    worlds={}
    for label in ("ALL_BRAIN_WIN","ALL_OPUS_WIN"):
        fit=fit_fixed_quality({
            "comparisons":base+_brain_extension(label),
            "judge_quality":QUALITIES,
            "anchor_model":ANCHOR,
            "anchor_elo":ANCHOR_ELO,
        })
        rb=fit["ratings"][BRAIN]
        ro=fit["ratings"][OPUS]
        worlds[label]={
            "brain_elo":rb,
            "opus_elo":ro,
            "brain_minus_opus":rb-ro,
            "brain_ge_opus":rb>=ro,
            "comparison_count":fit["comparisons"],
        }
    opposite=(
        worlds["ALL_BRAIN_WIN"]["brain_ge_opus"] is True
        and worlds["ALL_OPUS_WIN"]["brain_ge_opus"] is False
    )
    return {
        "schema":"PROJECT_BRAIN_GDPVAL_CROWDBT_TWO_WORLD_NONIDENTIFIABILITY_RESULT_V1",
        "status":"PASS__TWO_PUBLIC_COMPATIBLE_EXTENSIONS_REVERSE_BRAIN_VS_OPUS" if opposite else "FAIL",
        "fixed_public_compatible_structure":{
            "anchor_model":ANCHOR,
            "anchor_elo":ANCHOR_ELO,
            "opus_reference_target_elo":OPUS_PUBLIC_ELO,
            "judge_panel":list(QUALITIES),
            "balanced_base_comparisons_per_judge":1000,
            "balanced_brain_extension_comparisons_per_judge":220,
            "judge_qualities_same_in_both_worlds":QUALITIES,
        },
        "base_fit_opus_elo":base_fit["ratings"][OPUS],
        "worlds":worlds,
        "only_deliberate_world_difference":"PREVIOUSLY_UNOBSERVED_BRAIN_PAIRWISE_JUDGE_OUTCOMES",
        "consequence":"CURRENT_PUBLIC_SCORING_SURFACE_ALONE_CANNOT_DECIDE_BRAIN_GE_OPUS__BRAIN_OWNER_OUTCOMES_OR_A_SOUND_STRONGER_TARGET_RELATION_BRIDGE_IS_REQUIRED",
        "hard_nonclaims":[
            "SYNTHETIC_WORLDS_ARE_NOT_CLAIMED_TO_BE_THE_REAL_AA_EPOCH",
            "NO_CLAIM_THE_CHOSEN_JUDGE_QUALITY_VALUES_EQUAL_AA_HISTORICAL_FITS",
            "NO_BRAIN_GDPVAL_SCORE_OR_TERMINAL_CREDIT",
        ],
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


if __name__=="__main__":
    import json
    print(json.dumps(run(),indent=2,sort_keys=True))
