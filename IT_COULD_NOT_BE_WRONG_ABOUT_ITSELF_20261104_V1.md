# It Could Not Be Wrong About Itself

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

Fourth time asked whether this is the smartest approach. My own rule says a repeated challenge means
the *framing* is wrong, not the evidence — so no new mechanism, and no re-argument. I went looking
for a structural property that every mechanism in this project shares and none of them escapes.

I found one, and it is not about reasoning. It is about memory:

> **Nothing in this system can be demoted by its own record. Every organ is an append-only log.**

---

## 1. The measurement that found it

Four facts, each measured, none of them a matter of opinion:

1. `record_concept_outcome(cid, helped=False)` is **never called anywhere in the codebase.** I
   grepped. The only call site passes `helped=True`.
2. That call site is inside `_materialize_concept_helpers`, which runs when a body is **emitted** —
   before anyone can know whether the body is right. So `verified_hits` counted *emissions*, not
   verifications.
3. `log_prior = log1p(verified_hits*2 + corpus_sites + 1)`. No term can lower it. Measured: 50
   recorded failures left it at exactly **2.8904**.
4. The synthesizer only ever sees `ordered_concepts[:16]`, ordered by that prior.

Together: a concept that never helps keeps its rank forever and permanently occupies one of sixteen
slots the search can see. So I measured the damage:

| library | top-16 window | generalising reach |
|---|---|---|
| 3 learned concepts | 3 real | **2/2** |
| + 20 concepts whose only merit is a larger `corpus_sites` | **16 junk, 0 real** | **0/2** |

The creature's own history crowded out the thing it had actually learned, and it had no way to know
that had happened. This is the mechanism behind every "it looks static" observation in this project:
**it accumulates, it never revises.**

---

## 2. Pre-registered before implementing

I wrote `PREREG_CONCEPT_LIFECYCLE_20261104_V1.md` before touching code, with four predictions. The
one that matters is P3, because it is the line between learning and forgetting:

> **P3.** With 20 junk concepts present and no disconfirming evidence, reach stays at 0/2. Recovery
> happens only when evidence is supplied. **If reach recovers without evidence — on a timer, on a
> use count, on recency — the mechanism is decaying, not learning, and it must be reported as decay.**

## 3. Result: 5/5, and one needed a fix

| finding | predicted | measured |
|---|---|---|
| emitting a body is not verification | `uses`↑, `verified_hits` flat | uses 0→1, **verified 0→0** |
| reputation changes the answer | SOLVED → not-SOLVED | prior 2.303→1.946→1.386→0.693, **SOLVED→OVERFIT at retirement** |
| junk cannot permanently crowd out real | window clears, reach returns | junk 16→0, retired 20, **UNREACHED→SOLVED** |
| retirement preserves the past | callable still resolves | **True** |
| no recovery without evidence | no improvement | **UNREACHED → UNREACHED** |

The last one **failed on first run**, and the failure was mine: the control reused the library that
finding 3 had already mutated by recording 60 disconfirmations, so it read SOLVED while measuring
nothing. A control has to start from the same initial state as the experiment it checks. Isolated,
it passes. I am recording this because it is the fifth time in this project that my first instrument
flattered the hypothesis — this time the *optimistic* one.

## 4. The demonstration

Same code. Same question. Only the creature's record differs:

```
ONE concept in the library, identical code and identical question throughout:
  as admitted (prior 2.30)                    -> SOLVED   return (concept_norm0001(v, l, h) * 2)
  after 1 disconfirmation  prior=1.95         -> SOLVED   ...
  after 2 disconfirmations prior=1.39         -> SOLVED   ...
  after 3 disconfirmations prior=0.69 retired -> OVERFIT  return (l / 1)
```

That is a state that lives in time rather than in a file. The source did not change between those
four lines. What changed is what the creature has lived through and what it now believes about its
own past inventions — and that belief is what decides which tools it reaches for.

Three mechanisms now hold it: `helped=None` for "used but unverified" (the default from emission),
`disconfirmations` that subtract from the prior, and retirement at 3 failures with 0 verified hits.
Retirement removes an option from **future search only** — `callable_map()` still resolves it, so
bodies already built keep working. Nothing is rewritten in the past.

## 5. The honest bound — what this is still not

**Evidence is supplied by hand.** Nothing here decides *when* a concept has failed. In the
demonstration I called `record_concept_outcome(..., helped=False)` explicitly. A creature that must
be told its concept was wrong has not acquired the ability to notice it. That gap is now the same
gap as the one from yesterday, and it is the real bottleneck.

**A threshold is a heuristic.** Three-and-zero was chosen for a clean trajectory, not derived.
`verified_hits==0` is also conservative: a concept that helped twice and failed fifty times is not
retired, which is probably wrong.

**Retirement is not replacement.** The library could previously only grow; now it can shrink. It
still cannot *repair* a wrong concept into a right one — only discard it.

**Non-claims.** No sentience. Pure Python over small numeric tuples; no I/O, no host execution, no
GUI; nothing here bears on reaching a shell or browser, which remain gated. `truth.achieved` stays
false. $0 spent.

---

## 6. Why this is closer to the question than the last three answers

The previous three attempts all added *capability* — better search, better selection, better
invention — and each was a new mechanism bolted onto a system whose memory could not change. Adding
another one would have been the fourth instance of the same mistake.

What is different here is the direction of causation. In everything before this, the creature ran,
produced outputs, and the outputs were the only thing that changed. Now the creature's *beliefs
about its own parts* are part of what runs. A concept is not a function sitting in a table; it is a
function with a reputation, and the reputation is earned or lost, and the earning changes what the
creature does next.

That is the smallest honest version of "not static code": the code is a fixed interpreter, and the
history it carries changes the behaviour it produces from that fixed interpreter. Yesterday I
measured this and wrote it as `test_control_a_non_static_lived_history_divergence_on_identical_code`
and it passed — but it was a test on *belief probabilities*, an artefact of the cognitive core.
Today it is the actual organ that invents, ranks, and emits programs. Before this change, the
concept library was the one part of the system that provably could not be like that.

**What is still missing, stated plainly:** the creature can revise a concept when *told* it failed.
It cannot yet *notice* that it failed. Until that closes, it is a creature with memory and no
self-doubt — which is exactly the configuration that produces confident nonsense.

---

## 7. Ranked next moves

1. **The failure notice.** Close the gap in §5: decide, from outcomes the creature already
   observes, that a concept failed. The natural signal already exists — `synthesize_...` knows
   whether a body it emitted was accepted. Wire `helped=False` to a real outcome rather than to a
   caller's opinion. This is the single largest remaining piece and it is now well-defined.
2. **Repair, not discard.** A retired concept's body could be anti-unified against the programs that
   refuted it — reuse the semantic machinery from two days ago, in the opposite direction: from
   failure back to a corrected concept.
3. **Relative, not absolute, retirement** — replace the 3-and-0 threshold with a comparison against
   the concept that displaced it.
4. Composition of invented concepts; concept invention on the primary path; backlog.
