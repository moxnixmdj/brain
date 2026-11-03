# Does "instant learning, in new environments, one try each" solve everything — permanently?

**2026-11-03.** Written after P1 (carried-model planning) and P2 (honest denominator) both
measured. Every number below was produced on this machine today; none is independently verified.
The question is taken seriously, because the direction is right — it is the quantifiers
(*everything*, *perfectly*, *permanently*) and one structural claim (*one try is enough*) that
the measurements refuse.

`truth.achieved` stays `false`. Nothing here flips a family or registers a capability.

---

## 1. What is real — and it is more than the sceptical version admits

This is not a project that has nothing. Four things are built and measured:

1. **It persists.** Teach a lesson, restart the process, and the lesson is still there. Memory
   survives death, which is the one property that makes "learning" mean anything.
2. **It recalls in the same environment.** Repeating a goal in the environment it was learned in
   is genuinely faster, not marginally: the fingerprint cache turns a 4.8 s cold probe into a
   recall.
3. **It transfers to a genuinely new instance of the same kind.** Measured today on 15 cases
   with source ≠ target: **8/15 solved in a single trial** after carrying the model, up from
   **1/15** before P1. Mean trial speedup **6.33×**, mean act-call speedup **2.26×**, and
   **0/15 got worse on trials**. On the second benchmark, **6/10** one-trial (was 0/10).
4. **The learning is gated by a verifier.** A weak verifier receiving a broadened pattern
   produced **0 proposals**, and the gate is enforced in code, not by convention.

Point 3 is the one most people would not expect, and it is the honest core of "instant learning
in a new environment": the stored model is *planned through before searching*, and every edge of
that plan is validated against the real environment during the walk. That is a real capability,
not a demonstration.

## 2. What is not real

**(a) "One try in each new environment" does not mean it learns each new environment.** The
target environment is not consulted to *learn*; it is consulted to *check*. The carried model
comes from a prior environment of the same kind. So the true statement is: **it applies what it
already knows to a new instance, and it learns nothing from the new instance.** Measured: after
carrying, the store is byte-identical (`/tmp/scale.py`: clean vs loaded store, 15/15 identical).
The environment was solved by the model it arrived with.

**(b) Learning is not accumulated across kinds — it is not accumulation at all.**
The decisive measurement: a store containing **4 other kinds** of environment behaves
*byte-identically* to a store containing only its own kind.

| store | solved | one-trial | mean trials | mean acts |
|---|---|---|---|---|
| clean (own kind only) | 15/15 | 8/15 | 22.4 | 182 |
| loaded (+4 other kinds) | 15/15 | 8/15 | 22.4 | 182 |

**A memory that grows and does not change is storage, not learning.** Compounding exists *inside*
a kind (8/15), and **0/5 across kinds**. So "we learn everything, and everything we learn makes
the next thing easier" is false as measured. Five separate environments did not make the sixth
cheaper.

**(c) One try is not enabled, structurally, for a new *kind*.** The measured distribution is not
"one try"; it is **22.4 trials on average**, and it is wildly uneven — `grid`, `modulo` and
`toggles` reach one trial immediately, while `lock_3dial` takes **24 to 200 trials**. Reporting
"one try" as the property of the system is reporting the best-behaved quarter of the results.

**(d) "Everything on a computer" is not the shape of the coverage.** The front-door census is
**8 of 149** verified bound capabilities reachable from a sentence (5.4%), and the largest red
cluster in the suite — **233 failures** in
`test_an_ordinary_sentence_runs_the_command_it_states_v1.py` — is not a missing capability at
all. I checked: the front compiler turns ordinary prose into exactly the right command.

```
"the first word of each line in the file F"  ->  ['cut','-d',' ','-f','1', F]
"sort the lines of the file F"               ->  ['sort', F]
"compress the file F"                        ->  ['gzip', F]
```

The capability exists; the door does not reach it. That is one defect with a count of 233, and
it is the strongest current argument that **the bottleneck is the front door, not learning.**

**(e) The sentient-creature framing is not supported, and the measurements are why.**
A creature that learns permanently has a property this system demonstrably lacks: **its
experience changes its future.** Here the store grows and its behaviour does not change
(§2b), it forgets (the fingerprint cache had a real, now-fixed eviction defect — see §4), and it
learns nothing from a new environment (§2a). What exists is a **persistent, verifier-gated,
per-kind skill cache with a planning step in front of it.** That is a genuinely useful artefact.
It is not a creature, and the word "creature" is doing work the measurements do not support.

## 3. Where the framing is right and I was wrong to let it sound refuted

The claim "it solved instant learning and instant learning in new environments" was recorded as
a concession on 2026-11-01 and stands: **the mechanisms exist and measure**. What was wrong in
the *reporting* was the instrument and the quantifier, not the achievement:

- the original probe re-created the instance it was teaching, so it measured recall and reported
  it as transfer — an instrument defect;
- and the extension from "*this* transfers" to "*everything* on a computer, *perfectly and
  permanently*" was a quantifier defect.

Both are fixed by counting, not by arguing.

## 4. The defect I found *while* writing this, because it is the answer in miniature

The mechanism that makes recall instant was **FIFO, not LRU**. Measured: a fingerprint key read
**20 times** was evicted by 256 one-shot keys, while a one-shot key written most recently
survived. A fingerprint costs **5–8 s of real acting** to produce; a cache write costs **3.2 ms**.
So the system was discarding its most-used knowledge to keep its least-used knowledge.

Fixed (`766f40e`): evict by last use, rate-limit the touch to keep reads at 0.39 ms, and keep
bookkeeping out of the returned value. Pinned by 5 tests.

**Why this belongs in the answer:** "permanently" is exactly the property nobody has measured.
The one memory that *is* supposed to be permanent was silently throwing away its hottest entries,
and **nothing in the suite called that a defect.** Permanence is not a property you get by
believing it; it is a property you have to test, and this one failed the test the first time it
was looked at.

## 5. The honest one-paragraph answer

> It genuinely learns a *kind* of environment, once, and then solves new instances of that kind
> about half the time in a single trial, verifiably and without getting worse. It does **not**
> learn a new environment from one try — it checks its old model against it. It does **not**
> accumulate across kinds: five environments make the sixth no cheaper. It covers **8 of 149**
> capabilities at the front door, and the largest block of red tests is that door, not the
> learner. So the correct claim is: **a real, bounded, per-kind instant-transfer skill memory —
> not a permanent general learner, and not a creature.**

## 6. The smartest moves, ranked by (evidence × cost)

| # | move | why it is ranked here | cost |
|---|---|---|---|
| 1 | **Fix the front door (P3)** | 233 of 978 real failures are one door defect, and the capability behind it already works. Highest measured evidence-per-hour in the repo. | high — needs a real verifier, or stop at step 1 and say so |
| 2 | **Hold cross-kind compounding to a bet (P4/P5)** | The 0/5 across kinds is the actual ceiling on "learns everything". One bounded, held-out experiment decides whether it is reachable. Do not assume it. | medium |
| 3 | **Make permanence a tested property, not an assumption** | §4 was found by accident. Eviction, cap, corruption and restart are four testable claims about memory that currently have thin coverage. | low |
| 4 | **Author a held-out routing set by hand (P4)** | Routing claims are hypotheses until the sentences are written by someone who has not seen the trigger list. This is what turns 8/149 into a measurement. | medium |
| 5 | **Repair the 69 currentness-guard drifts** | Mechanical, no judgement, removes 69 failures from the denominator so the real ones are visible. | low |
| 6 | **Keep measuring on a clean machine** | Substrate was 1/10 today; a missing `cv2` and a broken invariant both print `F`. Fixing this changed 25 failures legitimately. | trivial |

**Explicitly not on the list:** breadth of environments as a strategy (five cheap environments
taught nothing that transferred — measured), scheduled/background runs, new organs, using the
model at solve time to look cleverer, and sentience as a target.

**The one route to real compounding, stated honestly:** a bounded donor-model acquisition that is
deleted after use and is qualified on a held-out set. If that is what "learns everything" is meant
to mean, it has to be *measured that way* — and it is not in the tree today.

## 7. Standing non-claims

One machine, one run, no independent verifier, disposable state, $0 spent. `truth.achieved` is
`false`. 8/15 and 6/10 are producer-run measurements on constructed environments and say nothing
about GUI, unbounded computer use, or any environment the code has not seen.
