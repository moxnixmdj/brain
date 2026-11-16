"""Which of the offered actions can do nothing here — learned by property, not by page.

The wall this attacks
---------------------
`systematic_exploration_v1` tries every (state, action) pair once and never twice, which is
already optimal *given the action set*. On MiniWoB++ it measured 8.34 actions per
distinguishable state, so the first solve of a new page costs roughly `8.34 ** depth` actions
and the budget reaches about depth 3. Spending more budget buys almost nothing (2.26x compute
-> 1 page in 37). The only lever that changes the exponent is the *effective branching factor*,
and there is exactly one way to lower it without lowering coverage: stop paying for actions
that cannot do anything.

Measured on 8 of the 32 pages the 1500-action budget never solved, one reset per action,
counting a change in what the agent can see and nothing else:

    actions sampled from the initial state      314
    of those, changed nothing visible           148   (47.1%)
    pages where more than half the hand is inert 3

Almost half of the experiment budget is spent discovering that the visible world is
indifferent. That is the free lunch, and it is not free at the moment: it is paid every time,
on every page, for ever, because nothing remembers it.

What is remembered, and the one design decision that makes it transferable
--------------------------------------------------------------------------
The existing `effect_prior` in the explorer pools effect statistics per `action_class`, which
by default is the action STRING (`click@7`). A string key cannot transfer: `click@7` on this
page is not `click@7` on the next one, so nothing learned on page A is usable on page B and
every page is the first page for ever.

This module keys the same counter on the **affordance**: the kind of action crossed with the
properties of the element it is taken on that the agent can see. `hover|div|plain`,
`type|input-text|empty|instruction_word`, `click|button|named`. Those keys mean the same thing
on a page nobody has seen, which is what makes one environment teach the next.

Why an ORDER and not a FILTER
-----------------------------
Two different claims hide in "this action is inert":

  * it changed nothing visible HERE, once. That is a FACT, and it is exactly what was measured.
  * it can never change anything HERE, ever, and nothing depends on it. That is a THEORY, and
    it is false in general: a press may set hidden state that only shows two steps later, and
    hidden state is not in the observation this module reads.

Because the second does not follow from the first, this module never removes an action. It
prices it. An action whose affordance class has never changed anything is DEFERRED, by a
finite price, behind every action that has. The explorer still tries it if the budget lasts
(`systematic_exploration_v1`: "The prices are an ORDER, never a filter: every offered action
is still tried if the budget lasts, so a bad price list costs actions and cannot hide a goal").
Completeness is therefore untouched: what this buys is fewer actions spent before the useful
ones, and what it can lose is actions at the very end of a budget — which is reported, per run,
as `deferred_untried`.

What it is not
--------------
  * Not a world model: it predicts nothing about a state it has not priced, only about an
    action's CLASS. It cannot say what an action does, only whether its kind has ever done
    anything.
  * Not a learner of tasks: it never sees a reward, a goal or a `done` flag, so it cannot
    learn what "success" looks like. That is deliberate -- a prior that reads the reward is
    the oracle the deployment does not have.
  * Not a model, not weights, not a network, not random. `K3 = 0`, `$0`, no I/O.

Usage
-----
    prior = InertActionPrior()
    prior.observe(observation, "hover@4", changed=False)      # after acting, from the SAME state
    price, turn = prior.price(observation, "click@3")          # order="cheapest" cost_of hook
    report = prior.table()                                     # every count, as measured
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_INERT_ACTION_PRIOR_V1"

# The deferral is a SURCHARGE, not a wall, and both numbers below were measured rather than
# chosen. A draft used 10**9 ("certainly last") and it made a page the baseline solved in 3
# actions take 400: the explorer prices ROUTES, so an action that no route can afford makes
# endless resets cheaper than finishing, and the search roams instead of solving (measured
# 2026-11-16, search-engine). A surcharge of ONE unit matches the cheapest action the shipped
# price list already quotes, so a deferred action costs no more than the cheapest live thing
# the caller can do -- it is reordered, never priced out.
LIVE_PRICE = 0
DEFERRED_SURCHARGE = 1

# A class with plenty of tries and no change is not merely unknown, it is FAMILIAR AS INERT.
# Pricing it at a constant surcharge still lets it be tried before an unexplored class (which
# sits at price 0 with an optimistic rate and is therefore "cheaper"), and that ordering was
# measured to starve the useful actions: on MiniWoB++ the first page tried every nudging
# variant of every element -- all cheaper than the same classes with evidence -- while the one
# button that ends the page stayed unexplored. So the price of a class with no recorded change
# grows with how often it has done nothing, and the growth per try is the same +1 as above.
DEFERRED_GROWTH = 1

# How many observations a class needs before its rate may defer anything. With one observation
# a class that did nothing might simply not have been tried in the right place; the arithmetic
# below is Laplace-smoothed, and this floor keeps the smoothing honest rather than decorative.
MIN_OBSERVATIONS_TO_DEFER = 2


def classify(observation: Mapping[str, Any], action: str) -> str:
    """The affordance an action is taken on, as a string that means the same on any page.

    An action is `kind@index`, `kind@index=payload`, or `kind=payload` (a wait). The element's
    properties are read from the observation the action was offered in -- the same observation
    the caller prices against -- so the key is a function of what the agent can see and nothing
    else. Unknown shapes yield a key that names the shape, so a new kind of action is counted
    and reported rather than silently pooled with the known ones.
    """
    text = str(action)
    if text.startswith("wait="):
        return "wait"
    kind, _, rest = text.partition("@")
    index_text, _, payload = rest.partition("=")
    try:
        index = int(index_text)
    except ValueError:
        return f"{kind}|unindexed"
    elements = observation.get("elements") or []
    if not 0 <= index < len(elements):
        return f"{kind}|off-page"
    element = elements[index]
    tag = str(element.get("tag") or "?")
    # The four properties that decide what an element can do at all. Deliberately coarse: a
    # finer key fits the pages already seen and transfers worse, which is the trade this file
    # exists to make in the transferable direction.
    if element.get("can_type"):
        ability = "typable"
    elif element.get("can_click"):
        ability = "pressable"
    else:
        ability = "plain"
    if element.get("disabled"):
        ability += "-disabled"
    elif element.get("checked") or element.get("selected"):
        ability += "-chosen"
    if kind == "type":
        own = str(element.get("value") or "")
        payload_class = "empty" if not own else ("same" if payload == own else "replacing")
        return f"{kind}|{tag}|{ability}|{payload_class}"
    if kind in ("nudge",):
        return f"{kind}|{tag}|{ability}|{payload}"
    return f"{kind}|{tag}|{ability}"


class InertActionPrior:
    """A counted table of (affordance class -> tries, tries that changed anything).

    Every observation is recorded as it is made; nothing is inferred. `price` returns an order,
    and `deferred` names the classes it deferred with their counts, so a bad prior is visible
    in the receipt instead of being an invisible tax on the search.
    """

    def __init__(self, *, min_observations: int = MIN_OBSERVATIONS_TO_DEFER) -> None:
        self._tries: dict[str, int] = {}
        self._changes: dict[str, int] = {}
        self._min = max(1, int(min_observations))
        self._deferred_paid: dict[str, int] = {}

    # -- learning ---------------------------------------------------------------------------
    def observe(self, observation: Mapping[str, Any], action: str, *, changed: bool) -> str:
        """Record what ONE action did from ONE state. `changed` is the caller's comparison of the
        observation before and after; this module cannot compute it and does not guess it."""
        cls = classify(observation, action)
        self._tries[cls] = self._tries.get(cls, 0) + 1
        if changed:
            self._changes[cls] = self._changes.get(cls, 0) + 1
        return cls

    def absorb(self, other: "InertActionPrior") -> None:
        """Merge another prior's counts (e.g. one learned on another page, or another machine).
        Counts add; nothing is averaged, and no class is lost."""
        for cls, n in other._tries.items():
            self._tries[cls] = self._tries.get(cls, 0) + n
        for cls, n in other._changes.items():
            self._changes[cls] = self._changes.get(cls, 0) + n

    # -- using ------------------------------------------------------------------------------
    def rate(self, cls: str) -> float:
        """Laplace-smoothed chance that an action of this class changes anything. Unobserved
        classes get 0.5: optimistic, so nothing is deferred before it has been looked at."""
        return (self._changes.get(cls, 0) + 1.0) / (self._tries.get(cls, 0) + 2.0)

    def is_deferred(self, cls: str) -> bool:
        """A class is deferred only once it has been observed enough to have a rate worth acting
        on, and has never changed anything in that time."""
        return (self._tries.get(cls, 0) >= self._min and self._changes.get(cls, 0) == 0)

    def price(self, observation: Mapping[str, Any], action: str) -> tuple[int, int]:
        """`cost_of` for `systematic_exploration_v1(order="cheapest")`: (price, turn).

        A deferred action is not forbidden, only postponed behind everything live offered in
        the same state, by an amount that grows with the evidence that its class does nothing.
        """
        cls = classify(observation, action)
        if self.is_deferred(cls):
            self._deferred_paid[cls] = self._deferred_paid.get(cls, 0) + 1
            return DEFERRED_SURCHARGE + DEFERRED_GROWTH * self._tries.get(cls, 0), 9
        return LIVE_PRICE, 1

    # -- reporting --------------------------------------------------------------------------
    def table(self) -> dict[str, dict[str, Any]]:
        """Every class as measured, so a claim about the prior can be checked against the counts
        that produced it rather than against a summary written by hand."""
        out: dict[str, dict[str, Any]] = {}
        for cls in sorted(self._tries):
            tries = self._tries[cls]
            changes = self._changes.get(cls, 0)
            out[cls] = {"tries": tries, "changes": changes,
                        "rate": round(self.rate(cls), 4),
                        "deferred": self.is_deferred(cls)}
        return out

    def summary(self) -> dict[str, Any]:
        classes = len(self._tries)
        deferred = sorted(cls for cls in self._tries if self.is_deferred(cls))
        return {
            "schema": SCHEMA,
            "classes": classes,
            "tries": sum(self._tries.values()),
            "changes": sum(self._changes.values()),
            "deferred_classes": deferred,
            "deferred_classes_count": len(deferred),
            "deferred_offers": dict(sorted(self._deferred_paid.items())),
            "min_observations": self._min,
            "digest": self.digest(),
        }

    def digest(self) -> str:
        import hashlib

        body = json.dumps({"tries": sorted(self._tries.items()),
                           "changes": sorted(self._changes.items())}, sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()[:20]

    # -- the probe --------------------------------------------------------------------------
    @classmethod
    def from_probe(cls, rows: Sequence[Mapping[str, Any]], *,
                   min_observations: int = MIN_OBSERVATIONS_TO_DEFER) -> "InertActionPrior":
        """Build a prior from rows of {observation, action, changed} -- e.g. what a goal-free
        probe run wrote. Kept here so the probe and the search cannot disagree about the key."""
        prior = cls(min_observations=min_observations)
        for row in rows:
            prior.observe(row["observation"], str(row["action"]),
                          changed=bool(row.get("changed")))
        return prior
