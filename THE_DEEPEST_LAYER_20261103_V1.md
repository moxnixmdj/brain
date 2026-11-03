# The deepest layer: it is not sentient-like, and the reason is now measured

**2026-11-03.** Written because the question was "is this the smartest approach?" and the honest
answer is **no, not by itself** — and because the fix is not more of what I was doing.

---

## 1. What I was doing, stated plainly

P1 made the carried model actually get used (1/15 → 8/15 one-trial transfer). P2 measured the
denominator. Then I spent the rest of the session repairing pinned invariants, refusals and
bindings.

**Every one of those changes the audit, not the ability.** A system defined by a shrinking failure
count is a very well-audited *static program*. It does what its code says. That is a good property
for a library and a fatal one for what you say you want.

## 2. The line that separates a creature from a skill cache

One property, and it is the only one that matters here:

> A program does what its code says. A creature gets better at **new** problems because it has met
> **old** ones.

That was unmeasured in this repository. So I measured it, twice, with the confound removed.

### Measurement A — does meeting more KINDS make the next kind cheaper?

Ten kinds, none sharing declared structure. Each solved cold (empty store) and "grown" (a store
that has already solved every earlier kind).

```
kinds=10   cold_acts=1525   grown_acts=1525   net_saving=0
improved=0  worsened=0  unchanged=10
COMPOUNDING ACROSS KINDS: NO
```

**Byte-identical, 10/10.** Meeting nine kinds — appending, grid-walking, counting, dial locks,
toggle banks, sorts, jugs, queues, registers — made the tenth cost *exactly* the same.

**And my first version of this benchmark said "COMPOUNDING: YES, 261 acts saved."** The confound
was mine: the grown arm also solved a same-kind sibling first, so it measured the per-kind
transfer that already works and labelled it compounding. *The mechanism is keyed per kind, so it
cannot compound by construction* — and a badly designed arm made it look like it could.

### Measurement B — can the searcher learn WHICH SEARCH to use?

I built the smallest honest learning-to-learn: five search policies, credit recorded for
procedures (not facts) against a **kind-blind** feature view, then tested on kinds never trained
on — against both a default and, crucially, **a coin flip**.

```
test kinds=4  learned solved=4
beat default=1/4   beat random mean=4/4
NO_COMPOUNDING -- the features do not generalise
```

It beat the random mean 4/4 and the default 1/4. That is **not** compounding: the honest reason
is that the feature view cannot tell the kinds apart. My first feature view collapsed six
distinct training kinds into **one key** (branching, moved-fraction). I added a real structural
reading — do actions *decompose* the problem or merely *permute* it, measured by one-action vs
two-action reachable-set growth — and four of four test kinds still land in buckets it has
already seen.

**So: the mechanism I would want works in principle and does not work yet. That is a different
statement from "impossible", and it is the truthful one.**

## 3. A defect that made the headline number fragile

Checking goal identity while building the above:

```
_goal_key for three DIFFERENT goals -> ['<lambda>', '<lambda>', '<lambda>']
distinct: 1 of 3
```

`_goal_key` returned `__name__`. **Every lambda is named `<lambda>`.** So "recall the plan for
*this* goal" was never implemented — only "recall a plan for *any* goal". Fixed: identity now
comes from closure values plus a behavioural probe ladder. Different captured targets → different
keys; the same goal → the same key.

Re-measured after the fix: **8/15 one-trial, 0/15 worse, 6.33× trial speedup — unchanged.** The
P1 result survives, which is the only good news in this section.

## 4. So what is the smartest approach? Not the one I was taking.

Ranked by how much they change what the system *can do*, not by how they read on a dashboard:

1. **Make the feature view actually kind-blind and discriminative — or conclude it cannot be.**
   This is the one item with a real chance of producing compounding. It needs more kinds (4 test
   kinds is not a measurement), features that survive a kind the designer never imagined, and the
   random arm kept permanently. **If it still fails at 20 kinds, the answer is no, and that is a
   finding worth more than another 200 green tests.**
2. **Give the system its own policy vocabulary.** Today I wrote the five policies. Learning which
   one to apply is real but narrow. Composing *sequences* of policies, or mutating a policy when
   none fits, is the next rung — and it is where most "sentient-like" claims quietly become false,
   so it must be measured the same way: unseen kinds, a coin-flip arm, a verdict that can be no.
3. **Make permanence a property, not an assumption** (already started: the FIFO cache bug).
4. Only then the backlog — because a system that cannot compound is a system whose failure count
   is the most interesting thing about it, and a system that can is one where a few hundred red
   tests are a maintenance detail.

## 5. What is still not true, and must stay written down

- **Not sentient, not sentient-like.** Two of three attempts at the property that would begin to
  justify that word produced **no** compounding. The third (learning-to-learn) has a mechanism
  and a negative result.
- **The policy vocabulary is mine.** Any success would mean the system learns *which* of my five
  strategies to apply — never that it invents strategies. The document says so in the JSON too.
- 4 test kinds and 10 constructed environments are small. `state()` being a hashable value is the
  entire difficulty of real computer use and none of this touches it.
- `truth.achieved` stays `false`. No family flipped. $0 spent.

## 6. The sentence I would put on the front of the repository

> It is a **skill cache with a verifier** — genuinely fast at problems that resemble ones it has
> solved, provably unchanged by having solved unrelated ones. Getting from there to a creature is
> one specific, currently failing experiment: making *which strategy to use* transfer between
> kinds. Everything else is maintenance.
