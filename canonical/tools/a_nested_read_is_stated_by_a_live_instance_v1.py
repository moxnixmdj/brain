#!/usr/bin/env python3
"""A nested attribute read is stated by a live instance, not by the class.

Item 181's answer is one constructor call whose keyword arguments are NESTED reads:

    PinJoint('pin', parent, child, parent_point=parent.frame.x, child_point=-child.frame.x)

`attribute_paths` reaches ONE level because it walks `dir(cls)`. That is a hard limit of walking
a class: `Body.frame` is a *property*, so `dir(Body)` reports the property object, whose only
members are `fget`/`fset`/`getter`/`setter`. The nested member `x` therefore does not exist
anywhere in the one-level space, and no amount of ranking can reach it.

The artifact states it anyway. A live instance exposes the property's real value:

    >>> Body("b").frame
    b_frame
    >>> Body("b").frame.x
    b_frame.x

So the space is walked from an INSTANCE, which the type's own signature makes constructible. That
is not knowledge about `Body`: it is the same rule already used for the guide mechanism — the
declared type is instantiated from its own signature, and the instance states what the class
cannot.

Authority: NONE. Sandbox measurement. Zero model calls.
"""
from __future__ import annotations

import json
import subprocess
from typing import Sequence

SCHEMA = "BRAIN_NESTED_READ_FROM_A_LIVE_INSTANCE_V1"

_WALK = r"""
import json
imports = __imports__
for line in imports:
    exec(line, globals())
spec = __spec__

# The type's own signature states whether it needs an argument. These are stated attempts, in
# the same order used elsewhere in this project; a type that cannot be instantiated yields no
# nested paths, which is an empty space, never a wrong answer.
MAKERS = (lambda c, t: c(), lambda c, t: c(t), lambda c, t: c(t + "_probe"),
          lambda c, t: c(t, 1), lambda c, t: c(t, mass=1))

def build(anno, param):
    tail = anno.rsplit(".", 1)[-1]
    try:
        cls = eval(anno, globals())
    except BaseException:
        try:
            import sympy as sp
            cls = getattr(sp, tail, None)
        except BaseException:
            cls = None
    if cls is None:
        return None
    for maker in MAKERS:
        try:
            obj = maker(cls, param)
        except BaseException:
            continue
        try:
            if obj is None:
                continue
        except BaseException:
            continue
        return obj
    return None

out = {}
for param, anno in spec.items():
    obj = build(anno, param)
    if obj is None:
        out[param] = []
        continue
    level1 = []
    for n1 in dir(obj):
        if n1.startswith("_"):
            continue
        try:
            v1 = getattr(obj, n1)
        except BaseException:
            continue
        if v1 is None or callable(v1):
            level1.append([n1, []])
            continue
        nested = []
        try:
            for n2 in dir(v1):
                if n2.startswith("_"):
                    continue
                try:
                    getattr(v1, n2)
                except BaseException:
                    continue
                nested.append(n2)
        except BaseException:
            pass
        level1.append([n1, nested[:40]])
    out[param] = level1
print(json.dumps(out))
"""


def nested_paths(python: str, imports: Sequence[str], spec: dict[str, str],
                 *, timeout: float = 300.0) -> dict[str, list[str]]:
    """Dotted paths TWO levels deep, read from a live instance of each declared type.

    Returned as flat dotted strings (`parent.frame.x`) because that is what a body needs. The
    one-level space produced by walking the class is a strict subset, so results from here are
    new only where a property returns a real object.
    """
    if not imports or not spec:
        return {}
    code = _WALK.replace("__imports__", repr(list(imports))).replace("__spec__", repr(dict(spec)))
    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    rows = [l for l in (proc.stdout or "").strip().splitlines() if l.startswith("{")]
    if not rows:
        return {}
    try:
        data = json.loads(rows[-1])
    except (json.JSONDecodeError, ValueError):
        return {}
    out: dict[str, list[str]] = {}
    for param, level1 in data.items():
        paths: list[str] = []
        for name, nested in level1:
            if nested:                       # only the two-level paths are new information
                paths.extend(f"{name}.{sub}" for sub in nested)
        out[param] = sorted(set(paths), key=lambda p: (len(p), p))
    return out


_KWS = r"""
import inspect, json
imports = __imports__
for line in imports:
    exec(line, globals())
cls = eval(__cls__, globals())
names = []
try:
    sig = inspect.signature(cls.__init__)
    names = [n for n, prm in sig.parameters.items()
             if n not in ("self", "name") and prm.kind in (prm.POSITIONAL_OR_KEYWORD, prm.KEYWORD_ONLY)]
except BaseException:
    try:
        sig = inspect.signature(cls)
        names = [n for n, prm in sig.parameters.items()
                 if n not in ("self", "name") and prm.kind in (prm.POSITIONAL_OR_KEYWORD, prm.KEYWORD_ONLY)]
    except BaseException:
        names = []
print(json.dumps(names))
"""


def constructor_keywords(python: str, imports: Sequence[str], cls_tail: str,
                         *, timeout: float = 180.0) -> list[str]:
    """The constructor's own parameter names, read from its signature.

    `PinJoint.__init__` states `parent_point` and `child_point`; the prose says "the connection
    point on the parent body" and "on the child body". Neither the name nor the meaning has to be
    guessed -- the artifact declares its own keyword names in the signature it exposes.
    """
    if not imports or not cls_tail:
        return []
    code = _KWS.replace("__imports__", repr(list(imports))).replace("__cls__", repr(cls_tail))
    try:
        proc = subprocess.run([python, "-c", code], capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return []
    rows = [l for l in (proc.stdout or "").strip().splitlines() if l.startswith("[")]
    if not rows:
        return []
    try:
        return [str(n) for n in json.loads(rows[-1])]
    except (json.JSONDecodeError, ValueError):
        return []
