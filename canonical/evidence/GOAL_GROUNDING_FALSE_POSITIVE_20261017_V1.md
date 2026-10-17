# The front door matches vocabulary, not fitness

`plain_goal.bound_capability.grounding.stdlib` runs and returns a grounded,
scored capability. This records why that is not yet sufficient for autonomy.

## The selection examined

Goal:

    "Find out whether Brain owns its capability mechanisms and report the evidence"

Selected:

    terminal.kstar.root.assess.stdlib
    combined_score 25.27
    matched_goal_tokens [brain, capability, evidence]

## What that capability actually is

`terminal_kstar_root_assess.run(args, root)` ignores `args` entirely. It reads
seven fixed, repo-relative files — authority, architecture, current-truth,
bridge, reducer, p3-cut, p3-verify — and returns an assessment of the
repository's own canonical truth state.

Its registry signature is `{}`, and that is correct, not under-declared. It is
a **repo-scoped** capability: it evaluates the Brain, not a caller's question.

## Therefore the match was spurious

It was selected on shared vocabulary. The goal said "brain", "capability",
"evidence"; the capability's metadata contains those words. It cannot accept
a goal and cannot act on one.

The door worked. The choice was wrong.

## The general gap

**Similarity is not fitness.** The grounding scores how much a capability
*sounds like* the question, not whether it *can answer* it.

A system that selects tools by word overlap will confidently select the wrong
tool. That is worse than selecting nothing, because the wrong selection
presents itself as a successful one — it returns GROUNDED, with a score.

## What is required

Before executing any selected capability, something must ask a second question:

    can this capability actually act on this goal?

Concretely, for the current registry that means checking whether the goal's
requirements can be supplied to the capability's declared inputs. A capability
with an empty signature can only be correct for goals that need no input —
which is a small and unusual class.

Until that check exists, the front door is a similarity ranking wearing the
clothes of a decision.

## Status

Not fixed. Recorded so the next session wires the fitness check alongside the
executor rather than after it.
