# PRE-REGISTRATION — *The creature cannot reach its own synthesizer*

2026-11-04, V1. Written **before** implementation, after measuring.
Base `9c4bdb0f`. Branch `arena/af0328d9-brain`.

---

## The measurement that produced this round

Rounds 15–19 built three things the tree now reports as capabilities: settlement (settled is computed,
not reached), operator acquisition from evidence, and period-table induction with arbitrary blocks
at 150/150 held-out. Each round measured the thing it built.

This round I measured **reachability**, the way I caught myself two rounds ago:

```
$ grep -rn "synthesize_or_disambiguate_skill" --include=*.py . | grep -v tests
(no output)
```

**No production code calls it.** `MetaCircularOrganGraph` is constructed by the live
`SentientCognitiveCore`, but the core calls exactly three of its methods —
`record_transition`, `organs_in_stratum`, `register_organ` — and never synthesizes a skill.
Empirically: instrumenting the method and building a full `SentientCognitiveCore` produced **zero**
calls.

So the path that actually executes work is `sovereign_perform` in `creature_runtime_v1`, whose routing
is a frozen list of four work-id prefixes:

```
chase:   gap:   inspector:   repair:
   ... else -> {"blocked": "UNSUPPORTED_WORK_KIND"}
```

**That list is the boundary of what the creature can attempt.** A problem whose id does not begin with
one of four strings is refused before any reasoning happens. This is not a defence of anything — the
synthesizer it would need is right there, and I verified it works on arbitrary unseen tasks with no
prefix guidance:

| unseen task | status | held-out (150 inputs never shown) |
|---|---|---|
| period-3 arbitrary block `[5,-2,7]` | INDUCED_OPERATOR_CRYSTALLIZED | 150/150 |
| period-7 ramp | INDUCED_OPERATOR_CRYSTALLIZED | 150/150 |
| affine `3x-4` | DISAMBIGUATED_AND_CRYSTALLIZED | 150/150 |

And checked directly: `task_signature` is consulted only as a **cache key** (`get_primary`,
`organs_in_stratum`) and never to decide *whether* or *how* to synthesize.

So this is the same defect one level up from the synthesizer itself. Not a frozen table of functions,
not a frozen threshold of evidence — **a frozen list of four problem names deciding what the creature
is allowed to try to understand.**

## What I will build

1. **An unrouted-problem route in `sovereign_perform`.** When no prefix matches *and* the work carries
   answerable evidence, hand it to the settled synthesizer instead of returning `UNSUPPORTED_WORK_KIND`.

2. **Fail closed when there is nothing to learn from.** The route must demand examples and a way to
   check an answer. No examples → refuse. No oracle → the synthesizer's own `NO_ORACLE` refusal
   stands. The new route must never invent evidence to have something to do.

3. **No name-based privilege.** The route must not branch on the work id beyond "not a known kind".
   If the answer depends on the id's spelling, the defect is still there in a new place.

4. **Report what it learned, through the existing organs.** The synthesized organ is registered in
   `P_t` with a signature derived from the *evidence*, so the next problem of the same shape recalls it
   — and the recall passes through the settlement layer's refutation check rather than trusting itself.

## Predictions — stated so they can fail

- **P1 (reachability).** A `Work` whose id has no known prefix, carrying examples and an oracle, must
  reach the synthesizer and return a verified answer instead of `UNSUPPORTED_WORK_KIND`.
  *Falsified if it still returns UNSUPPORTED_WORK_KIND.*
- **P2 (no privilege by name).** Two identical problems with different unrecognised ids must get the
  same treatment. *Falsified if behaviour differs.*
- **P3 (fail closed).** A work item with no examples, or with no oracle, must refuse with a named
  reason — never fabricate. *Falsified if anything is crystallized.*
- **P4 (it learns across work items).** A second work item of the same shape must be cheaper than the
  first — measured in oracle queries — while remaining correct on held-out inputs. *Falsified if the
  cost is flat or accuracy drops.*
- **P5 (nothing else regresses).** The four existing routes behave exactly as before, and the
  previously-merged suites still pass. *Falsified by any regression.*
- **P6 (the honesty machinery is preserved).** The route reports `predicted_probability` and settles
  through the same calibration ledger as every other route; a new route must not bypass the record of
  what the creature believed before it acted. *Falsified if it returns a result without settling.*

## Non-claims

- This does not make the creature generally capable. It connects one existing organ to one existing
  door; problems needing perception, code repair, or tool use still route as before, and problems
  outside the synthesizer's diagnosed structures still refuse.
- Reaching the synthesizer is not truth: `INDUCED_OPERATOR_CRYSTALLIZED` remains relative to the
  evidence and the reachable probe space. `truth.achieved` false, `authority: NONE`, $0.
- No sentience claim.

## Why this is the deepest remaining layer

Every previous round made a part better. This asks the question that decides whether any of it is part
of a creature at all: **can the thing that reasons be reached by the thing that lives?** A synthesizer
that nothing calls is not a capability, it is a library — and the creature that owns it is still the
static router it was before, wearing a brain it cannot touch.
