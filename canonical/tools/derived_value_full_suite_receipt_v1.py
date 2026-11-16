"""Turn the full-suite MiniWoB run into one receipt.

Two seeds, 130 real pages each, real headless Chromium. Three arms that differ ONLY in what
may be typed, so any difference is the typing vocabulary and nothing else:

    A_shipped_hand    the shipped literal vocabulary (quoted spans / instruction words / page text)
    U_union           A plus the derived-value algebra           -- ADDITION
    D_decoy_derived   same shape and size as the addition, wrong witness -- negative control

Also carried: E_derived_hand on the jsdom substrate (the tree's earlier 8-page study), recorded
so the two substrates and the two seeds can be read side by side and any disagreement is visible
rather than averaged away.
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

#: The eight pages the value operators were written against, named in
#: `canonical/verification/DERIVED_VALUE_20261116_V1.json` and `THE_HAND_WAS_NEVER_THE_BOTTLENECK_20261116_V1.md`.
#: Everything else is held out. The distinction is the whole point: a gain on these eight is a
#: re-measurement of a design; a gain outside them would be transfer.
DESIGN_SET = frozenset({
    "simple-arithmetic", "simple-algebra", "scroll-text", "text-transform",
    "enter-time", "search-engine", "use-slider", "guess-number",
})

ARMS = ("A_shipped_hand", "U_union", "D_decoy_derived")


def load(pattern: str) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(glob.glob(pattern)):
        rows += [json.loads(line) for line in pathlib.Path(path).read_text().splitlines() if line.strip()]
    return rows


def summarise(rows: list[dict], arms=ARMS) -> dict:
    out: dict = {"pages": len(rows), "arms": {}}
    for arm in arms:
        won = {r["task"] for r in rows if r["arms"][arm]["pass"]}
        out["arms"][arm] = {
            "solved": len(won),
            "actions_spent": sum(int(r["arms"][arm]["budget_spent"]) for r in rows),
            "verified_on_fresh_page": sum(1 for r in rows if r["arms"][arm]["verified_on_fresh_page"]),
            "solved_tasks": sorted(won),
        }
    return out


def compare(rows: list[dict], treatment: str, control: str = "A_shipped_hand") -> dict:
    t = {r["task"] for r in rows if r["arms"][treatment]["pass"]}
    c = {r["task"] for r in rows if r["arms"][control]["pass"]}
    gains, losses = sorted(t - c), sorted(c - t)
    return {
        "treatment": treatment,
        "control": control,
        "gains": gains,
        "losses": losses,
        "net": len(t) - len(c),
        "gains_outside_design_set": [g for g in gains if g not in DESIGN_SET],
        "losses_inside_design_set": [l for l in losses if l in DESIGN_SET],
    }


def held_out_only(rows: list[dict], arms=ARMS) -> dict:
    """The pages that never touched the design: the only place a gain would be transfer."""
    held = [r for r in rows if r["task"] not in DESIGN_SET]
    return {"pages": len(held),
            **{arm: sum(1 for r in held if r["arms"][arm]["pass"]) for arm in arms}}


def main(argv: list[str]) -> int:
    run1 = load(argv[0])
    run2 = load(argv[1]) if len(argv) > 1 and argv[1] else []
    jsdom = load(argv[2]) if len(argv) > 2 and argv[2] else []
    receipt = {
        "schema": "BRAIN_DERIVED_VALUE_FULL_SUITE_V1",
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "kind": "receipt",
        "incremental_spend_usd": 0,
        "producer_cognition_model_dependency_count": 0,
        "substrate": "chromium (headless, real layout/hit-testing/mouse)",
        "design_set": sorted(DESIGN_SET),
        "seeds": {},
    }
    if run1:
        receipt["seeds"]["1060"] = {
            "summary": summarise(run1),
            "union_vs_shipped": compare(run1, "U_union"),
            "decoy_vs_shipped": compare(run1, "D_decoy_derived"),
            "held_out_only": held_out_only(run1),
        }
    if run2:
        receipt["seeds"]["771"] = {
            "summary": summarise(run2),
            "union_vs_shipped": compare(run2, "U_union"),
            "decoy_vs_shipped": compare(run2, "D_decoy_derived"),
            "held_out_only": held_out_only(run2),
        }
    if jsdom:
        receipt["jsdom_substrate_seed_1060"] = {
            "summary": summarise(jsdom, ("A_shipped_hand", "E_derived_hand", "D_decoy_derived")),
            "replacement_vs_shipped": compare(jsdom, "E_derived_hand"),
            "union_vs_shipped": compare(jsdom, "U_union") if all(
                "U_union" in r["arms"] for r in jsdom) else None,
        }
    receipt["pages"] = run1
    text = json.dumps(receipt, indent=1, sort_keys=True)
    out = argv[3] if len(argv) > 3 else None
    if out:
        pathlib.Path(out).write_text(text + "\n")
        print(f"written {out} ({len(text)} bytes)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
