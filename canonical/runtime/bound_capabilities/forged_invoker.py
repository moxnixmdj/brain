"""Run a capability the forge admitted on its own.

Every other bound capability is a file an engineer wrote, exposing
`run(args, root)`. A forged capability is different: it is a function that
already existed in the inventory and was admitted by evidence. Making it
executable by writing it its own adapter file would mean hand-writing
exactly what the forge exists to avoid writing.

So this is one adapter, not one adapter per capability. It looks the
capability_id up in the forged registry and calls the admitted function
through the same sandboxed invoker the forge used to admit it -- so the
execution path at use time is the execution path that was tested.

THE REGISTRY IS THE ALLOWLIST. A capability_id that is not in the forged
state was never admitted and is refused. Nothing here accepts an
arbitrary module or function name from its caller, and the payload is
restricted to the parameters the admitted contract declares. This file is
therefore not a way to call arbitrary code; it is a way to call only the
code that already survived the forge.
"""
from __future__ import annotations

import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _forged() -> dict:
    from canonical.runtime import capability_forge_v1 as FG
    return FG._state().get("forged") or {}


def run(args, root=None):
    """Invoke one admitted capability: run({"capability_id": ..., <params>}, root)."""
    args = dict(args or {})
    cid = str(args.get("_forged_id") or args.get("capability_id") or "")
    rec = _forged().get(cid)
    if not rec:
        return {"ok": False, "adapter": "forged_invoker",
                "capability_id": cid,
                "error": "NOT_AN_ADMITTED_CAPABILITY"}
    module_rel = str(rec.get("module") or "")
    function = str(rec.get("function") or "")
    if not module_rel or not function:
        return {"ok": False, "adapter": "forged_invoker",
                "capability_id": cid,
                "error": "FORGED_RECORD_HAS_NO_MODULE_OR_FUNCTION"}
    params = ((rec.get("contract") or {}).get("parameters")) or []
    payload = {}
    for name in params:
        if name in args:
            payload[name] = args[name]
        elif name == "root" and root is not None:
            payload[name] = str(root)
    try:
        from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as B
        result = B.invoke(pathlib.Path(root) if root else _ROOT,
                          module_rel, function, payload)
    except Exception as exc:  # a refusal must come back as data, not a crash
        return {"ok": False, "adapter": "forged_invoker",
                "capability_id": cid, "function": function,
                "error": "%s:%s" % (type(exc).__name__, str(exc)[:200])}
    if not isinstance(result, dict):
        result = {"result": result}
    result = dict(result)
    result.setdefault("ok", True)
    result.setdefault("adapter", "forged_invoker")
    result.setdefault("capability_id", cid)
    result.setdefault("function", function)
    return result
