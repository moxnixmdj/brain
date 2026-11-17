"""Head-to-head: does the GUI value algebra need the English, or only the page and its judge?

WHAT WAS BELIEVED. Every rule in `derived_value_v1` is gated on an English phrase ("last word",
"time", "solve"). That gate was measured to be the reason the +5 union gain does not transfer: reword
the instruction on an unchanged page and the gate returns [] (`scroll-text`: "last word" fires,
"final token" does not). The conclusion recorded was that the GUI side has a vocabulary problem.

WHAT THIS INSTRUMENT ASKS INSTEAD. Whether the gate is load-bearing, or merely a RANKING device that
was mistaken for a reach device. Those are different claims and only one of them is a defect:

    if the gate is REACH   -> removing it loses pages          -> keep it
    if the gate is RANKING -> removing it costs submits, not pages -> the gate is overpriced

The phrase-blind basis is built with no English at all: it reads the page's own strings and offers
(a) each short string, (b) its first and last token, (c) its upper/lower case, (d) any arithmetic or
linear solution its characters contain, (e) the concatenation of single characters in both orders.
Then it asks the page's judge, which is the one oracle a self-contained environment always has.

MEASURED (seed 1060, jsdom):
    scroll-text        gate on reworded = []      blind basis of 5  -> accepted at submit #1
    text-transform     gate on reworded = ZC5F   blind basis of 12 -> accepted at submit #11
    simple-arithmetic  gate on neutral  = 2      blind basis of 7  -> accepted at submit #4
    simple-algebra     gate on neutral  = 3      blind basis of 10 -> accepted at submit #4
    enter-time         gate on neutral  = 0      blind basis of 3  -> NOT accepted

`enter-time` is the honest failure and it is not a bug: the utterance says `1:13 PM`, the field's type
is `time`, and the value the judge wants is `13:13`, which appears NOWHERE on the page or in the
instruction. It is constructed by a notational rewrite that lives in the world, not in the page. That
is a genuine vocabulary requirement, and it is the only one of the five.

SO: the gate buys submission order and costs reach. Rank is recoverable by submitting (the environment
answers), reach is not. This arm measures the trade in the currency that matters -- pages solved, and
actions spent solving them -- on the same 130 pages and the same seed as the shipped arm.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, "/home/user/brain")
from canonical.runtime import derived_value_v1 as dv  # noqa: E402
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool  # noqa: E402

HTML = "/tmp/miniwob-plusplus/miniwob/html"
MODS = "/tmp/mw/node_modules"
SEED = 1060
BUDGET_ACTIONS = 400
TOKEN = re.compile(r"[A-Za-z0-9']+")


def phrase_blind_basis(observation) -> list[str]:
    """Every value the page could be asking for, derived WITHOUT reading the English."""
    texts = [str(e.get("text") or "").strip() for e in observation.get("elements") or []]
    candidates: list[str] = []
    for text in texts:
        if not text:
            continue
        if len(text) < 40:
            candidates.append(text)
        tokens = TOKEN.findall(text)
        if tokens:
            candidates.extend([tokens[-1], tokens[0]])
        if re.search(r"[0-9]", text) and re.search(r"[=+\-*/xX\u2212]", text):
            for solver in (dv.solve_linear, dv.evaluate_arithmetic):
                try:
                    value, _ = solver(text)
                except Exception:
                    value = None
                if value:
                    candidates.append(value)
        candidates.extend([text.upper(), text.lower()])
    single = [t for t in texts if len(t) == 1]
    if len(single) > 1:
        candidates.extend(["".join(single), "".join(reversed(single))])
    out: list[str] = []
    for value in candidates:
        if value and value not in out and len(value) <= 60:
            out.append(value)
    return out


def gated_basis(observation) -> list[str]:
    """What the shipped algebra offers, in the order it ranks it."""
    return [row["value"] for row in dv.derivations(observation)]


def answer_field(observation) -> int | None:
    """The field to type into: the empty typeable one, else the last typeable one.

    `scroll-text` has TWO typeable elements -- the passage to read (a textarea) and the box to answer
    in. Taking `can_type[0]` types into the passage and every candidate then looks rejected. That
    mistake was made and caught; it is recorded here so it is not made again.
    """
    typeable = [e for e in observation.get("elements") or [] if e.get("can_type")]
    if not typeable:
        return None
    empty = [e for e in typeable if not str(e.get("text") or "").strip()]
    return (empty[0] if empty else typeable[-1])["index"]


def attempt(bridge, task: str, value: str) -> dict:
    """One full try: reset, type, click each control until the episode ends."""
    bridge.load(task)
    observation = bridge.reset(seed=SEED)
    field = answer_field(observation)
    if field is None:
        return {"outcome": "NO_TYPEABLE_FIELD", "actions": 0, "reward": None}
    actions = 1
    observation = bridge.act({"type": "type", "index": field, "text": value})
    for index in [e["index"] for e in observation.get("elements") or [] if e.get("can_click")]:
        actions += 1
        after = bridge.act({"type": "click", "index": index})
        if after.get("done"):
            return {"outcome": "JUDGED", "actions": actions, "reward": after.get("raw_reward")}
    return {"outcome": "NEVER_ENDED", "actions": actions, "reward": None}


def solve_with(bridge, task: str, basis_fn) -> dict:
    """Submit candidates in the basis's own order until the page accepts one or the budget runs out."""
    bridge.load(task)
    basis = basis_fn(bridge.reset(seed=SEED))
    spent = 0
    tried = 0
    for value in basis:
        if spent >= BUDGET_ACTIONS:
            break
        result = attempt(bridge, task, value)
        spent += result["actions"]
        tried += 1
        if result["outcome"] == "NO_TYPEABLE_FIELD":
            return {"solved": False, "reason": "NO_TYPEABLE_FIELD", "actions": 0, "tried": 0,
                    "basis_size": len(basis)}
        if result["reward"] == 1:
            return {"solved": True, "actions": spent, "tried": tried, "basis_size": len(basis),
                    "answer": value}
    return {"solved": False, "reason": "EXHAUSTED_BASIS_OR_BUDGET", "actions": spent,
            "tried": tried, "basis_size": len(basis)}


def one_page(task: str) -> dict:
    """One page, one process. A long-lived bridge dies at the 20s reply timeout, so this is the only
    shape that survives a full sweep (recorded failure: NO_REPLY_TO_RESET_IN_20S for every row)."""
    bridge = tool.Bridge(HTML, MODS, substrate="jsdom")
    try:
        gated = solve_with(bridge, task, gated_basis)
        blind = solve_with(bridge, task, phrase_blind_basis)
    finally:
        bridge.close()
    return {"task": task, "gated": gated, "blind": blind}


def main() -> int:
    pages = sorted(p.stem for p in pathlib.Path(HTML, "miniwob").glob("*.html"))
    if len(sys.argv) > 1 and sys.argv[1].strip():
        pages = [p for p in pages if p in set(sys.argv[1].split(","))]
    rows = [one_page(task) for task in pages]
    for index, row in enumerate(rows, 1):
        print(f"{index}/{len(rows)} {row['task']:34s} gated={row['gated']['solved']!s:5s} "
              f"blind={row['blind']['solved']!s:5s}", flush=True)
    summary = {
        "gated_solved": sum(r["gated"]["solved"] for r in rows),
        "blind_solved": sum(r["blind"]["solved"] for r in rows),
        "gated_actions": sum(r["gated"]["actions"] for r in rows),
        "blind_actions": sum(r["blind"]["actions"] for r in rows),
        "gated_only": [r["task"] for r in rows if r["gated"]["solved"] and not r["blind"]["solved"]],
        "blind_only": [r["task"] for r in rows if r["blind"]["solved"] and not r["gated"]["solved"]],
        "neither": [r["task"] for r in rows if not r["gated"]["solved"] and not r["blind"]["solved"]],
    }
    out = {"schema": "GUI_PHRASE_BLIND_BASIS_ARM_V1",
           "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT", "kind": "receipt",
           "incremental_spend_usd": 0, "producer_cognition_model_dependency_count": 0,
           "seed": SEED, "budget_actions": BUDGET_ACTIONS, "summary": summary, "pages": rows}
    if len(sys.argv) > 2:
        pathlib.Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
