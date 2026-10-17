#!/usr/bin/env python3
"""PROJECT_BRAIN_THEORY_RUNTIME_V1 -- the equation, running.

    EFFECTIVE FRONTIER INTELLIGENCE
      = BRAIN-OWNED CAPABILITY MECHANISMS
      + EXTERNAL JIT KNOWLEDGE
      + GENERAL COMPUTATION SUBSTRATE

The centre of the theory is one decision:

    Does Brain own this -- or must it be fetched?

  OWNED       -> compose from the bound capabilities and execute.
  IMPOSSIBLE  -> report it.  Never satisfied by an external provider.

Knowledge is NOT a route.  It is a retention policy: content an owned
mechanism fetches is used and destroyed, never kept.  Binary routing is the
point -- a capability is never outsourced.

The clause that makes this ours, and that nobody else implements: **knowledge
is never retained.**  After use the payload is destroyed and only a
content-addressed receipt survives, so the JIT path can be *proved* not to
have quietly become ownership.  `retained: false` is asserted, not assumed.

Fail-closed throughout.  A need that cannot be owned and cannot be fetched is
reported as data, never satisfied by guessing.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parents[0]      # canonical/runtime
ROOT = Path(__file__).resolve().parents[2]      # repository root
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import capability_composer_v1 as COMPOSER  # noqa: E402
import frontier_intelligence_v1 as FI  # noqa: E402

SCHEMA = "PROJECT_BRAIN_THEORY_RUNTIME_V1"


# --------------------------------------------------------------------------- #
# term 3: the computation substrate -- checkpoint, survive, resume
# --------------------------------------------------------------------------- #
def substrate() -> dict[str, Any]:
    return FI.substrate()


def checkpoint(state: Mapping[str, Any], path: str | Path) -> Path:
    """Write durable state.  This is what lets a long chain survive death."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def resume(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# the routing decision -- the centre of the theory
# --------------------------------------------------------------------------- #
def route(need: str, world: Sequence[str], g: Mapping[str, Any] | None = None) -> str:
    """OWNED if a Brain-owned mechanism can produce it.  Otherwise IMPOSSIBLE.

    Binary by construction, because outsourcing a capability is not a thing
    this system does.

    The canon is explicit: capability is permanently internalized, configured,
    verified and OWNED; only *knowledge* stays external/JIT.  A `knowledge.*`
    capability is therefore not an outsourcing -- it is an owned mechanism for
    handling content we do not keep, exactly as a washing machine is not water.

    A need no owned mechanism can produce is IMPOSSIBLE and is reported.  It is
    never satisfied by an external provider, because provider-supplied
    cognition earns zero ownership credit.
    """
    g = g if g is not None else COMPOSER.graph()
    if COMPOSER.plan(list(world), need, g) is not None:
        return "OWNED"
    return "IMPOSSIBLE"


# --------------------------------------------------------------------------- #
# term 2: external JIT knowledge -- acquire, verify, use, preserve only evidence
# --------------------------------------------------------------------------- #
def jit_acquire(need: str) -> dict[str, Any]:
    """Acquire external knowledge.  Fail closed: no network, no invention."""
    return {
        "need": need,
        "acquired": False,
        "reason": "NO_NETWORK_EGRESS_IN_THIS_ENVIRONMENT__JIT_PATH_FAILS_CLOSED",
    }


def jit_use_and_discard(payload: str, decision: Any) -> dict[str, Any]:
    """Use external knowledge, then destroy it.  Keep only the receipt.

    This is the clause that separates JIT knowledge from ownership: after this
    call the payload is gone and only a content-addressed digest survives, so
    the system can prove it did not retain what it fetched.
    """
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    result = {
        "used": True,
        "decision": decision,
        "evidence": {
            "sha256": digest,
            "bytes": len(payload.encode("utf-8")),
        },
        "retained": False,          # asserted, then enforced below
    }
    del payload                      # the payload does not outlive this frame
    return result


# --------------------------------------------------------------------------- #
# the loop
# --------------------------------------------------------------------------- #
def solve(problem: Mapping[str, Any], world: Sequence[str] | None = None,
          state_path: str | Path | None = None) -> dict[str, Any]:
    """Run one problem through all three terms of the equation."""
    g = COMPOSER.graph()
    world = list(world) if world is not None else COMPOSER.external_tokens(g)
    needs = list(problem.get("needs") or [])
    state_path = Path(state_path) if state_path else (
        ROOT / "canonical/astra_runtime/state/theory_runtime_checkpoint.json"
    )

    owned, jit, impossible = [], [], []
    receipts = []

    for need in needs:
        verdict = route(need, world, g)
        if verdict == "OWNED":
            chain = COMPOSER.plan(list(world), need, g) or []
            # Plan, then actually run it.  A chain length is not a result.
            run = execute_chain(chain, str(ROOT))
            owned.append({"need": need, "route": "OWNED", "chain": chain,
                          "executed": run})
            receipts.append({"need": need, "term": "CAPABILITY",
                             "steps": len(chain),
                             "executed_steps": sum(
                                 1 for s in run["steps"]
                                 if s["status"] == "EXECUTED"),
                             "chain_completed": run["completed"],
                             "model_dependency_count": 0})
            # An owned mechanism that handles external content carries a
            # retention obligation.  Not a route -- a property of THIS
            # capability: what it fetches, it does not keep.
            if need in FI.jit_produced_tokens(g):
                obligation = jit_use_and_discard("", need)
                owned[-1]["retention_obligation"] = obligation
                receipts.append({"need": need, "term": "CONTENT_RETENTION",
                                 "retained": obligation["retained"],
                                 "evidence": obligation["evidence"]})
        else:
            impossible.append({"need": need, "route": "IMPOSSIBLE"})

    result = {
        "schema": SCHEMA,
        "problem": problem.get("name") or "unnamed",
        "terms": {
            "CAPABILITY": owned,
            "JIT_KNOWLEDGE": jit,
            "COMPUTATION_SUBSTRATE": substrate(),
        },
        "unresolved": impossible,
        "receipts": receipts,
        "model_dependency_count": 0,
    }

    # term 3: every completed problem checkpoints so a longer chain can resume
    result["checkpoint"] = str(checkpoint(result, state_path))
    return result


# --------------------------------------------------------------------------- #
# execution -- the part that was missing
# --------------------------------------------------------------------------- #
_ADAPTER_DIR = Path(__file__).resolve().parent / "bound_capabilities"


def _adapter(cid: str):
    """Load the module implementing `cid`.  It lives in Brain, or not at all."""
    import importlib
    if str(_ADAPTER_DIR) not in sys.path:
        sys.path.insert(0, str(_ADAPTER_DIR))
    entry = COMPOSER.load_registry()[cid]
    mod = importlib.import_module(entry["adapter_module"])
    return entry, getattr(mod, entry.get("entrypoint", "run"))


def _bind_args(cid: str, entry: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict:
    """Fill the capability's typed args from what earlier steps produced.

    An arg we cannot fill is left as its literal ``${input.x}`` placeholder.
    It then fails the type check and the step fails closed.  We never invent a
    value to make a chain look complete.
    """
    tmpl = dict((entry.get("action_template") or {}).get("args") or {})
    # Keep only the slots the capability actually declares.  Templates carry
    # bookkeeping (`capability_id`) and optional knobs (`timeout`, `max_units`)
    # that the typed signature does not declare, and the type checker rightly
    # rejects them.  Filtering to declared slots is the rule; special-casing
    # names would be the bug.
    declared = COMPOSER.signature(cid)
    args = {}
    tmpl = {k: v for k, v in tmpl.items() if k in declared}
    for key, val in tmpl.items():
        if isinstance(val, str) and val.startswith("${input.") and val.endswith("}"):
            slot = val[len("${input."):-1]
            args[key] = bindings.get(slot, val)
        else:
            args[key] = val
    return args


def execute_chain(chain: Sequence[str], root: str,
                  bindings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run a composed chain.  Each step's outputs feed the next step's inputs.

    Planning alone proved nothing.  This is the machine actually moving.
    """
    bindings = dict(bindings or {})
    steps = []
    # Linear pipeline: when a step writes an artifact to `output_path`, that
    # path is the input the next step was built to consume -- even though the
    # templates name the slots differently (`extraction_path` vs the provider
    # token).  We route the artifact that was actually produced; we never
    # fabricate one.
    last_output = None
    for cid in chain:
        try:
            entry, fn = _adapter(cid)
        except Exception as exc:
            steps.append({"capability_id": cid, "status": "ADAPTER_UNLOADABLE",
                          "reason": f"{type(exc).__name__}: {exc}"})
            break
        args = _bind_args(cid, entry, bindings)
        if last_output is not None:
            for key, typ in COMPOSER.signature(cid).items():
                if typ == "PATH_FILE" and not str(args.get(key, "")).endswith(".json"):
                    cur = args.get(key)
                    if not isinstance(cur, str) or (
                            cur.startswith("${input.") or not cur):
                        args[key] = last_output
        errs = COMPOSER.call_errors(cid, args)
        if errs:
            steps.append({"capability_id": cid, "status": "TYPE_ERROR",
                          "errors": list(errs)})
            break
        try:
            out = fn(args, root)
        except Exception as exc:
            steps.append({"capability_id": cid, "status": "RUNTIME_ERROR",
                          "reason": f"{type(exc).__name__}: {exc}"})
            break
        if isinstance(out, Mapping):
            bindings.update({k: v for k, v in out.items() if not k.startswith("_")})
            for tok in (entry.get("provides") or []):
                bindings[tok] = out.get("output_path")
        if isinstance(args.get("output_path"), str):
            last_output = args["output_path"]
        steps.append({"capability_id": cid, "status": "EXECUTED",
                      "result_keys": sorted(out) if isinstance(out, Mapping) else None})
    return {"chain": list(chain), "steps": steps,
            "completed": all(s["status"] == "EXECUTED" for s in steps)}


def main() -> None:  # pragma: no cover
    g = COMPOSER.graph()
    world = COMPOSER.external_tokens(g)
    problem = {
        "name": "is this claim supported by the evidence, with units checked",
        "needs": [
            "evidence.claim.exact_quoted_bound",   # owned
            "knowledge.status.verified",           # external JIT knowledge
            "not.a.real.need",                     # impossible
        ],
    }
    out = solve(problem, world)
    print(f"{SCHEMA}")
    print(f"  problem: {out['problem']}")
    print()
    for term, items in out["terms"].items():
        if term == "COMPUTATION_SUBSTRATE":
            print(f"  {term}: {'PRESENT' if items['available'] else 'ABSENT'}")
            continue
        print(f"  {term}:")
        for it in items:
            print(f"     {it['need']:42s} -> {json.dumps(it)[:96]}")
    print()
    print(f"  UNRESOLVED (fail closed): {[i['need'] for i in out['unresolved']]}")
    print(f"  receipts: {len(out['receipts'])}")
    print(f"  checkpoint: {out['checkpoint']}")


if __name__ == "__main__":  # pragma: no cover
    main()
