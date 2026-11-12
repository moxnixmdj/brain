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


#: Ceiling on precondition facts sensed before a chain runs. Bounds the per-chain cost of the
#: snapshot; the universe is the declared `requires` of the capabilities that could serve these
#: clauses, which is small in practice.
MAX_PRECONDITION_FACTS = 64


def precondition_context(clauses, root, goal, extra_capability_ids=()):
    """The facts observed TRUE **before** the plan runs. Never the facts it produced.

    WHY NOT `established`. `chain_v1` starts `established` empty and fills it from each verified
    step's `provides`. By the end of a successful chain it holds exactly the effects the plan
    itself created, and by the end of a failed chain it holds a shorter prefix of them. Handing
    that to a learner as "the state" would teach a CIRCULAR requirement -- "this plan requires the
    effects this plan produces" -- which is true of every success and false of every failure by
    construction. It would look like a perfectly identified boundary and would then withhold the
    plan in every fresh state, because a fresh state has none of those effects yet. That is
    `false lesson propagation`: a spurious causal lesson drawn from a handful of trajectories and
    applied where it does not hold.

    So the snapshot is taken here, before the first side effect, from the world itself: the
    declared `requires` of the capabilities that could serve these clauses, each decided by
    `world_probe_v1`. A fact the perceiver cannot decide is simply absent -- it is not guessed,
    and it cannot become a spurious discriminator.

    Fail-open by construction: any error returns None, and a None context means macro_v1 behaves
    exactly as it did before this existed.
    """
    try:
        from canonical.runtime import grounded_action_v1 as GA
        from canonical.runtime import world_probe_v1 as WP

        registry = GA.load_registry()
        wanted = {str(cid) for cid in (extra_capability_ids or ()) if cid}
        for clause in clauses or ():
            for candidate in GA.keyword_candidates(str(clause), registry, k=8):
                cid = str(candidate.get("capability_id") or "")
                if cid:
                    wanted.add(cid)
        facts = set()
        for cid in sorted(wanted):
            entry = registry.get(cid)
            if isinstance(entry, dict):
                facts.update(str(f) for f in (entry.get("requires") or ()) if f)
        if not facts:
            return frozenset()
        observed = set()
        for fact in sorted(facts)[:MAX_PRECONDITION_FACTS]:
            try:
                if WP.probe_effect(fact, goal=str(goal), goal_paths=(), root=root).get("true") is True:
                    observed.add(fact)
            except Exception:
                continue
        return frozenset(observed)
    except Exception:
        return None


def _vocabulary_gap(clauses, memory):
    """Advisory: proof that this plan needs a fact the sensor cannot express. Executes nothing."""
    if not memory or not clauses or len(clauses) < 2:
        return None
    try:
        from canonical.runtime import macro_v1 as MC
        return MC.vocabulary_gap(MC.signature(clauses))
    except Exception:
        return None


def _next_contrast(clauses, preconditions, memory):
    """Advisory: the state to try next so the next run teaches something. Never executes anything."""
    if not memory or not clauses or len(clauses) < 2:
        return None
    try:
        from canonical.runtime import macro_v1 as MC
        pool = () if preconditions is None else (preconditions,)
        return MC.next_contrast(MC.signature(clauses), pool).as_row()
    except Exception:
        return None


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

    # A chain that finished once is a plan worth keeping. Looked up by the
    # SHAPE of the job, honoured only while it still binds, and forgotten
    # the first time it fails.
    macro = None
    if memory and len(clauses) >= 2:
        try:
            from canonical.runtime import macro_v1 as MC
            macro = MC.lookup(clauses)
        except Exception:
            macro = None
    used_macro = False

    # Taken BEFORE the first side effect, and reused unchanged for both the success and the
    # failure record, so the two are descriptions of the same starting state.
    preconditions = None
    macro_out_of_scope = False
    if memory and len(clauses) >= 2:
        remembered = []
        if isinstance(macro, dict):
            remembered = [step.get("capability_id") for step in (macro.get("plan") or [])
                          if isinstance(step, dict)]
        preconditions = precondition_context(clauses, root, goal, remembered)
        # The offer is withdrawn only where the retained evidence says the plan does not apply.
        # An undetermined or ambiguous boundary withdraws nothing.
        if isinstance(macro, dict) and preconditions is not None:
            try:
                from canonical.runtime import macro_v1 as MC
                if not MC.applicable(str(macro.get("key") or ""), preconditions):
                    macro_out_of_scope = True
                    macro = None
            except Exception:
                pass

    for index, clause in enumerate(clauses):
        prefer = None
        if isinstance(macro, dict):
            plan = macro.get("plan") or []
            if index < len(plan) and isinstance(plan[index], dict):
                prefer = plan[index].get("capability_id")
        receipt = GA.act(clause, root=root, memory=memory,
                         established_effects=sorted(established),
                         extra_paths=list(prior_outputs),
                         prefer=prefer)
        if prefer and str(receipt.get("capability_id")) == str(prefer):
            used_macro = True
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
            # A failure is counted, not obeyed. The plan is dropped only
            # when the evidence against it outweighs the evidence for it:
            # one instance failing says nothing about the shape.
            if isinstance(macro, dict):
                try:
                    from canonical.runtime import macro_v1 as MC
                    MC.note_failure(str(macro.get("key") or ""), context=preconditions)
                except Exception:
                    pass
            break
        # Only a VERIFIED step may contribute effects to the rest of the
        # plan. Building on an unverified step would make everything
        # downstream rest on nothing.
        for eff in _provides_of(receipt, root):
            established.add(eff)
        prior_outputs.extend(_outputs_of(receipt))

    completed = len(steps) if failed_at is None else failed_at
    learned = None
    if memory and failed_at is None and len(clauses) >= 2:
        try:
            from canonical.runtime import macro_v1 as MC
            learned = MC.record(clauses, steps, context=preconditions)
        except Exception:
            learned = None
    return {
        "schema": SCHEMA,
        "ok": failed_at is None and bool(steps),
        "used_macro": bool(used_macro),
        "macro_withheld_out_of_scope": bool(macro_out_of_scope),
        "next_contrast": _next_contrast(clauses, preconditions, memory),
        "vocabulary_gap": _vocabulary_gap(clauses, memory),
        "preconditions_observed": (
            None if preconditions is None else sorted(preconditions)
        ),
        "macro_recorded": bool(learned),
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
