# The bottleneck is option generation, and it is severe

The decision core works. It has almost nothing to decide between.

## Measurements

`decide_v1.py`, three goals:

| Goal | Result |
|---|---|
| Find out whether Brain owns its capability mechanisms and report the evidence | DECIDED, 1 candidate, score 0.25 |
| Extract the text from a PDF file and verify it | **NO_CANDIDATES** |
| Verify the archive tar file and check python contract violations | **NO_CANDIDATES** |

Two of three goals produce no options at all. The one that does produces a
single weak one.

## It is not the cap

`plain_goal_bound_grounding` allows up to 8 candidates per clause
(`max_candidates_per_clause=8`, hard ceiling 32). The cap is not binding.
The goals genuinely match nothing.

## What this means

The search machinery harvested from LATS is correct and idle. With one
option there is nothing to explore; with zero there is nothing to start.

**The system cannot decide well because it cannot imagine options, not because
it chooses badly.**

This reverses the priority from a few turns ago. It is not that the search
needs tuning. It is that the thing feeding it is nearly closed.

## Why the grounding is so narrow

It keeps a capability only on lexical overlap between goal tokens and the
capability's own metadata. Goals phrased in ordinary language ("extract the
text from a PDF") often share no significant tokens with capability names and
keywords, so nothing survives.

The single successful match worked because the goal happened to say "brain",
"capability" and "evidence" — words that appear in the metadata of a
capability that turned out not to be able to act on the goal at all.

So the current filter is both too narrow (most real goals yield nothing) and
unreliable (the one match it did produce was a false positive).

## Consequence for the mission

A system that "takes the right decisions by itself" needs, above all, the
ability to generate plausible candidate actions. That is now the binding
constraint, and it is the one thing we deliberately left plugged into a model
when harvesting LATS.

Options, ranked by ownability:

1. **Semantic matching on owned data** — match goal tokens against capability
   metadata using a deterministic measure (character n-grams, stemming,
   synonym sets already in the registry's `keywords`). No model.
2. **Type-directed enumeration** — ignore wording entirely; enumerate
   capabilities whose declared INPUTS can be produced from what we already
   hold. This is what the composer was built for and is fully deterministic.
3. Allow a model to propose options — but that is the one slot LATS needs a
   model for, and it earns zero ownership credit under our rule.

Option 2 is preferred: it selects on capability, which is the exact gap
identified when the grounding matched on vocabulary instead.

## Honest close

The decision machinery is harvested and works. It is starved. The next piece
to gather is not a smarter chooser — it is a generator of options.
