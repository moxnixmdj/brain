"""An in-memory web app whose real state can be probed and never seen.

WHY THIS EXISTS
---------------
`minimal_experiment_v1` learns a machine from observations, and the only
observations that matter are the ones a real environment gives: a structured
snapshot of what it looks like, and what changed after one action. Without such
a source the learner is a library with no caller.

What this module provides is the smallest thing that behaves like the real one:

* it holds the app's actual state (a hidden field), which the agent never reads;
* `snapshot()` returns only the public DOM -- same elements, same order, same
  text -- for two different internal states, so the DOM alone cannot tell them
  apart;
* `probe(action)` executes one action and returns the DOM before and after,
  from which an observation is derived.

That gap between the DOM and the state is not a toy detail. It is the exact
failure named in this project's own bottleneck document: "3 pages stop because
the same look behaves differently; that is a missing observable". This module
makes that sentence executable, and lets a test ask whether a probe strategy
can find the missing observable or must report that it cannot.

The app modelled is the one every real application contains: a multi-step
wizard. The step is hidden; the buttons look identical at two steps; the
difference only appears downstream. A trace store replays clicks. A machine
store, once it has found the observable, predicts.

No model, no network, no browser. `osworld_v21_browser_cdp_v1.snapshot()` emits
the same shape (`pages[].elements[]` with tag/role/text/name), so the adapter
below accepts either.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DOM_STATE_ENVIRONMENT_V1"

# The hidden state, which the agent never observes directly.
STEP = "step"
SUBMITTED = "submitted"


class DomStateEnvironment:
    """A three-step form whose steps share an identical-looking page.

    Hidden state: `step` in {1,2,3} and `submitted` bool.
    Public DOM: identical for step 1 and step 2 (this is the whole point --
    it is why an observation-keyed scan cannot separate them), different at
    step 3, and different once submitted.
    """

    def __init__(self) -> None:
        self._state: dict[str, Any] = {STEP: 1, SUBMITTED: False}
        self._history: list[dict[str, Any]] = []

    # -- the contract the learner needs ------------------------------------ #

    def snapshot(self) -> dict[str, Any]:
        """Public DOM only. Never contains the hidden step number."""
        step = int(self._state[STEP])
        submitted = bool(self._state[SUBMITTED])
        if submitted:
            elements = [{"tag": "div", "role": "status", "text": "Submitted",
                         "name": "status", "disabled": True}]
        elif step >= 3:
            elements = [
                {"tag": "button", "role": "button", "text": "Confirm",
                 "name": "confirm", "disabled": False},
                {"tag": "button", "role": "button", "text": "Back",
                 "name": "back", "disabled": False},
            ]
        else:
            # steps 1 and 2 are INDISTINGUISHABLE from the DOM
            elements = [
                {"tag": "input", "role": "textbox", "text": "", "name": "field",
                 "disabled": False},
                {"tag": "button", "role": "button", "text": "Next",
                 "name": "next", "disabled": False},
            ]
        return {
            "schema": SCHEMA,
            "url": "app://form",
            "title": "Form",
            "elements": elements,
        }

    def state(self) -> dict[str, Any]:
        """The hidden truth. Available to the harness and to the goal check,
        never to the learner's observation path."""
        return dict(self._state)

    def actions(self) -> list[str]:
        return ["next", "back", "confirm", "type"]

    def act(self, action: str) -> None:
        """Execute one action. Unavailable actions raise, which is a real signal:
        an action that cannot be taken is not a prediction."""
        action = str(action)
        step = int(self._state[STEP])
        if bool(self._state[SUBMITTED]):
            raise ValueError("APP_TERMINAL__NO_ACTIONS")
        if action == "next":
            if step >= 3:
                raise ValueError("ACTION_UNAVAILABLE__next")
            self._state[STEP] = step + 1
        elif action == "back":
            if step <= 1:
                raise ValueError("ACTION_UNAVAILABLE__back")
            self._state[STEP] = step - 1
        elif action == "confirm":
            if step < 3:
                raise ValueError("ACTION_UNAVAILABLE__confirm")
            self._state[SUBMITTED] = True
        elif action == "type":
            if step >= 3:
                raise ValueError("ACTION_UNAVAILABLE__type")
            # typing does not change the public DOM: it is an action whose
            # effect is invisible, which the learner must learn to treat as
            # uninformative rather than as a state change
            pass
        else:
            raise ValueError("ACTION_UNKNOWN__" + action)
        self._history.append({"action": action, "state": dict(self._state)})

    # -- observation ------------------------------------------------ #

    def observation(self, action: str, *, access: Sequence[str] = ()) -> dict[str, Any]:
        """One observation in the form `minimal_experiment_v1` consumes.

        The observation is `accepting` = "this action was available". That is the
        only thing the DOM itself reveals reliably, and it is a genuine
        prediction: at step 1 `back` raises and at step 2 it does not, so
        availability separates two states the DOM cannot.
        """
        try:
            self.act(action)
            available = True
        except ValueError:
            available = False
        # `available` and `accepting` are DIFFERENT facts and both are reported.
        # Availability is what the DOM cannot show and what separates two states
        # that look identical. Acceptance is whether the state reached is a goal
        # state, which this app exposes only at the end. An earlier version set
        # `accepting` to availability and omitted `available` entirely, so every
        # refused action was silently recorded as a successful one.
        accepting = bool(self._state[SUBMITTED])
        return {
            "access": list(access),
            "action": str(action),
            "observation": (
                "TERMINAL" if accepting else "AVAILABLE" if available else "UNAVAILABLE"
            ),
            "available": available,
            "accepting": accepting,
        }

    def dom_digest(self) -> str:
        body = json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + sha256(body).hexdigest()


def snapshot_to_elements(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Accept either this module's DOM or `osworld_v21_browser_cdp_v1`'s pages."""
    if isinstance(snapshot.get("pages"), list):
        out: list[dict[str, Any]] = []
        for page in snapshot["pages"]:
            for el in page.get("elements") or ():
                out.append(dict(el))
        return out
    return [dict(el) for el in (snapshot.get("elements") or ()) if isinstance(el, Mapping)]


def stable_actions(elements: Sequence[Mapping[str, Any]]) -> list[str]:
    """The action alphabet an element list defines: its `name` attributes.

    Derived from the scan rather than declared, because a new environment is
    exactly the case where nobody told the agent what its actions are called.
    """
    names = []
    for el in elements:
        name = str(el.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names
