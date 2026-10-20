"""The socket the brain plugs into.

Everything else in this system is built. Perception, action,
confinement, verification, and a memory that measurably reduces the
number of steps. And with all of it in place, solve() does nothing at
all until someone supplies a model -- which, until now, meant me,
typing programs by hand, in every single demonstration.

That is the whole remaining gap, and it is worth being precise about
what kind of gap it is. It is not a missing feature. It is a missing
COMPONENT: the thing that looks at a situation and decides. Perception
and action can be built once and work everywhere; judgement cannot be
built at all, because any rule that decides whether an ARBITRARY task
is finished is a rule about that task and fails on the next one.

So this file does not contain a model. It contains the shape one must
have, and the means to plug one in.

THE CONTRACT. A model is any callable:

    model(goal, seeing) -> program | None

    goal    the task, in plain language
    seeing  what the machine says is true: the tree, what changed,
            previews of small files, the result of the last action,
            and anything the memory has earned the right to say
    returns code to run, or None to propose that the goal is reached

That is the entire interface. No SDK, no client, no framework. A
function. Anything that can produce text from text satisfies it, which
is deliberate: the moment the harness depends on a vendor's shape, it
stops being the general part and becomes that vendor's plugin.

BINDING comes from the environment, never from this file:

    BRAIN_MODEL   an import path to a callable, e.g. "mypkg:choose"
                  or "mypkg.choose"

WHEN NOTHING IS BOUND, it says so. It does not fall back to a
placeholder that returns something plausible, because a model-shaped
hole filled with a confident guess is how a system reports success
while doing nothing -- the exact failure this system has punished
roughly forty times now, and the one it must never commit itself.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_MODEL_V1"

# Written where a human will find it, because "the model is not
# configured" is a fact about the machine and belongs somewhere
# readable, not buried in a traceback.
ENV_VAR = "BRAIN_MODEL"


def bound() -> bool:
    """Is a model actually plugged in?"""
    return bool(os.environ.get(ENV_VAR, "").strip())


def bind(spec: str | None = None):
    """Return the model callable named by the environment.

    Accepts "package.module:attr" or "package.module.attr". Raises on
    a bad specification rather than returning None, because a binding
    that silently fails is indistinguishable from one that worked and
    returned nothing.
    """
    target = (spec if spec is not None
              else os.environ.get(ENV_VAR, "")).strip()
    if not target:
        raise UnboundModelError(
            f"no model is bound: set {ENV_VAR} to an import path of a "
            f"callable taking (goal, seeing) and returning code or None")

    if ":" in target:
        module_name, _, attr = target.partition(":")
    else:
        module_name, _, attr = target.rpartition(".")

    if not module_name or not attr:
        raise UnboundModelError(
            f"{ENV_VAR}={target!r} is not a valid import path; expected "
            f"'package.module:callable'")

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise UnboundModelError(
            f"cannot import {module_name!r}: {exc}") from exc

    obj = getattr(module, attr, None)
    if obj is None:
        raise UnboundModelError(
            f"{module_name} has no attribute {attr!r}")
    if not callable(obj):
        raise UnboundModelError(
            f"{target} is not callable; a model must be a function "
            f"taking (goal, seeing)")
    return obj


class UnboundModelError(RuntimeError):
    """No model is configured. Raised rather than guessed around."""


def describe(model) -> dict:
    """What is plugged in, for the receipt."""
    if model is None:
        return {"bound": False, "name": None}
    name = getattr(model, "__name__", None) or type(model).__name__
    module = getattr(model, "__module__", None)
    return {"bound": True, "name": name, "module": module}


def conformance(model) -> dict:
    """Does this thing actually satisfy the contract?

    Checked by calling it, which is the only check that means
    anything: a signature alone cannot tell you whether it returns
    code, None, or an essay about code.
    """
    if not callable(model):
        return {"ok": False, "reason": "not callable"}
    seeing = {"step": 1, "tree": [], "count": 0, "changed": [],
              "preview": {}, "last": None, "learned": None}
    try:
        out = model("a goal no one has ever had before", seeing)
    except Exception as exc:
        return {"ok": False,
                "reason": f"raised {type(exc).__name__}: {exc}"}
    if out is None:
        return {"ok": True, "returned": None}
    if isinstance(out, str):
        return {"ok": True, "returned": "program", "length": len(out)}
    return {"ok": False,
            "reason": f"returned {type(out).__name__}, "
                      f"must be code (str) or None"}


def status() -> dict:
    """Is the system able to think right now? Answerable in one call."""
    if not bound():
        return {"schema": SCHEMA, "bound": False,
                "detail": f"{ENV_VAR} is not set; the loop cannot act "
                          f"on its own",
                "ready": False}
    try:
        m = bind()
    except UnboundModelError as exc:
        return {"schema": SCHEMA, "bound": False, "detail": str(exc),
                "ready": False}
    conf = conformance(m)
    return {"schema": SCHEMA, "bound": True, "model": describe(m),
            "conformance": conf, "ready": bool(conf["ok"])}
