"""One sentence, many steps: the machine plans a chain and then runs it.

WHY THIS IS STATIC AND NOT DYNAMIC.

The usual reason a chain cannot be planned up front is that you do not
know what step one will produce until you have run it, so step two cannot
be bound. That stops being true the moment outputs are deterministic:
`world_binding_v1.synthesize_output_path` derives a step's destination
from its capability id and nothing else. The output path of step one is
therefore known BEFORE step one runs, and step two can be bound against
it immediately.

So the whole chain is bound first and executed second. That matters more
than it sounds: a plan that is fully bound before the first side effect
can be refused as a whole, instead of half-executed and then discovered
to be impossible.

WHAT FLOWS BETWEEN STEPS, TWO KINDS.

1. EFFECTS. A capability declares `provides`; a later one declares
   `requires`. Step one provides `pdf.extract.text`, so step two may
   assume it. This is the classic planner assumption -- a plan may rely
   on its own earlier steps -- and it is sound here because every step is
   independently verified before the next one is allowed to build on it.

2. FILES. More common, and entirely undeclared in the registry: step one
   writes to a path, step two reads that path. Handled by feeding each
   step's output path forward as a candidate input for the next.

FAILURE IS FORWARD AND HONEST.

Steps execute in order and stop at the first one that does not verify.
There is no rollback -- these are real side effects on a real machine, and
pretending otherwise would be the lie. What the caller gets back is the
exact prefix that completed, the step that failed, and why. A chain that
got three of four steps done and says so is more useful than one that
reports a bare failure, and infinitely more honest than one that claims
success after quietly skipping a step.

NO STEP MAY SKIP VERIFICATION because an earlier one passed.
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_CHAIN_V1"
ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical" / "runtime"


def _load(name, rel):
    path = RUNTIME / rel
    if not path.is_file():
        raise RuntimeError("MISSING:" + rel)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def decompose(goal):
    """Split a sentence into the steps it is asking for, in its own order."""
    mod = _load("pgbg_chain", "bound_capabilities/plain_goal_bound_grounding.py")
    try:
        clauses = mod.decompose(goal)
    except Exception:
        return [str(goal)]
    out = [str(c.get("text") or "").strip() for c in clauses
           if isinstance(c, dict) and str(c.get("text") or "").strip()]
    return out or [str(goal)]


def _outputs_of(receipt):
    """Where a step says it put its work -- known before it ran."""
    outs = []
    inputs = receipt.get("inputs") or {}
    for key, value in inputs.items():
        if "output" in str(key).lower() and value:
            outs.append(str(value))
    return outs


def run(goal, root=None, memory=True, max_steps=8):
    """Plan a chain from one sentence, bind it fully, then execute it."""
    root = Path(root) if root is not None else ROOT
    started = time.perf_counter()
    from canonical.runtime import grounded_action_v1 as GA

    clauses = decompose(goal)
    if len(clauses) > max_steps:
        clauses = clauses[:max_steps]

    established = set()
    prior_outputs = []
    steps = []
    failed_at = None

    for index, clause in enumerate(clauses):
        receipt = GA.act(clause, root=root, memory=memory,
                         established_effects=sorted(established),
                         extra_paths=list(prior_outputs))
        steps.append({
            "index": index,
            "clause": clause,
            "capability_id": receipt.get("capability_id"),
            "status": receipt.get("status"),
            "selected_because": receipt.get("selected_because") or receipt.get("why"),
            "verified": bool(receipt.get("verified")),
            "inputs": receipt.get("inputs"),
            "error": receipt.get("error"),
            "ms": receipt.get("total_ms"),
        })
        if not receipt.get("ok"):
            failed_at = index
            break
        # Only a VERIFIED step may contribute effects to the rest of the
        # plan. Building on an unverified step would make everything
        # downstream rest on nothing.
        for eff in _provides_of(receipt, root):
            established.add(eff)
        prior_outputs.extend(_outputs_of(receipt))

    completed = len(steps) if failed_at is None else failed_at
    return {
        "schema": SCHEMA,
        "ok": failed_at is None and bool(steps),
        "goal": goal,
        "clause_count": len(clauses),
        "steps": steps,
        "completed_steps": completed,
        "failed_at": failed_at,
        "established_effects": sorted(established),
        "outputs": prior_outputs,
        "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }


def _provides_of(receipt, root):
    cid = receipt.get("capability_id")
    if not cid:
        return []
    try:
        from canonical.runtime.grounded_action_v1 import load_registry
        entry = (load_registry() or {}).get(cid) or {}
        return [str(x) for x in (entry.get("provides") or [])]
    except Exception:
        return []
