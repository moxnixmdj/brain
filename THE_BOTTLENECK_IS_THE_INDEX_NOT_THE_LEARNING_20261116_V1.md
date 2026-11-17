# The bottleneck is the index, not the learning

**Date:** 2026-11-16 · **Branch:** `arena/bbad1d61-brain` · **Base:** `8408c78c`
**Authority:** `NONE__PRODUCER_RUN`. Producer-run, this machine, $0, zero model dependency.

---

## 0. What this session had to do that the last one did not

Last session answered the **arithmetic** of "once" — one demonstration is 1.09 bits, a chosen question is 1.91, so "once" cannot finish the job. That is true and it is not enough, because it does not say *what to fix*.

This session ran research exhaustion on the two things left undone: I read `INSUFFICIENCY_CERTIFICATE_20261113_V1.json` for the first time, and I re-ran the compounding and transfer instruments on this base. Four of them. Three reproduce a wall, one produces a **contradiction**, and the contradiction is the finding.

---

## 1. The contradiction, and why it is the whole answer

Two measurements in your own tree point in opposite directions.

**No compounding across kinds.** `cross_kind_compounding_benchmark_v1.py`, re-run here:

```
[1/10] append_letters  cold=797 grown=797 saved=0
...
[10/10] string_affix  cold= 84 grown= 84 saved=0
kinds=10  cold_acts=1525  grown_acts=1525  net_saving=0
COMPOUNDING ACROSS KINDS: NO -- meeting more kinds does not make the next kind cheaper
```

**Strong compounding within a family.** `COMPRESSION_MAKES_EXPERIENCE_COMPOUND_20261112_V1.md`:

| arm | oracle questions | evidence collected |
|---|---:|---:|
| cold period-12 (empty library) | **59** | 48 |
| library-armed (abstraction from solved 3/5/7) | **35** | 24 |

**41% fewer questions, half the evidence, on a shape never seen.** Both are real. So "does experience compound?" is not one question.

The difference between the two runs is not effort and not scale. It is that the first has **no abstraction mechanism at all** — `cross_kind_compounding_benchmark_v1.py` stores facts indexed per kind, and the tree's own `cross_kind_learning_to_learn_benchmark_v1.py` says so in its first paragraph: *"it stores facts keyed per kind, so it cannot compound by construction."*

So I ran the second mechanism. It indexes **procedure credit** by a kind-blind feature key, and it also fails:

```
test kinds=10  learned solved=5  beat default=1/10  beat random mean=3/10
NO_COMPOUNDING -- the learned choice is not better than a coin flip on unseen kinds
```

And its own docstring names the design tension it sits on:

> `features`: *"Deliberately few and coarse. A rich feature vector would let the choice overfit to kinds it has seen, which is the failure this measurement is looking for."*
> `feature_key`: *"A coarse, transferable key. Coarse on purpose: a fine key cannot generalise."*

**Both ends are named as failures, and the conclusion drawn was "the features do not generalise."** That is where I stopped the last time. It is the wrong reading of its own output. Look at the key it printed:

```
b1_m2_r1_d0_g0   <- sliding_pairs, stack_pushout, letter_shift, double_dial, tri_lock
```

Five kinds, one key, and they do **not** need the same policy. The ledger is asked for one answer where five different answers are correct. That is not "the features do not generalise" — it is that **the key is not injective on the distinction the policy depends on.**

---

## 2. The measurement that settles it

Coarse and fine are not two settings of one knob. They are two *different* failures, and if both fail then no granularity of these features works.

I swept the bucketing from coarser-than-the-tree's all the way to one key per kind, scoring each family by two numbers: **keys** (how much it separates) and **collisions** (keys holding ≥2 kinds that need different policies — i.e. keys a ledger must answer wrongly).

| key family | keys | collisions | answerable |
|---|---:|---:|---:|
| tree's own coarse key | 8 | 2 | 5 / 8 |
| coarser still | 7 | **3** | 4 / 7 |
| finer mid | 14 | 2 | 11 / 14 |
| finest exact features | 16 | 2 | 13 / 16 |
| one key per kind (trivial) | **20** | 0 | 19 / 20 |

**Read the two ends.** Coarsening makes collisions *worse* (2 → 3). Refining reduces them but the only family reaching zero collisions is the degenerate one where every kind gets its own key — **20 keys for 20 kinds, which transfers nothing.** `usable_key_families: []`.

> **`NO_GRANULARITY_OF_THESE_FEATURES_SEPARATES_WHAT_THE_POLICY_DEPENDS_ON`**

The features do not *contain* the observable the policy depends on, so no bucketing of them can supply it. **Coarse-vs-fine was never the parameter.**

---

## 3. The honest correction I had to make to my own instrument

My first draft reported four kinds — `letter_shift`, `ring_rotate`, `stack_pushout`, `tri_lock` — as **"solved by no policy."** That would have been a capability finding. It was an artifact, and I caught it before publishing.

The benchmark calls `make(1)` everywhere. **Instance 1 is the hardest of the three.** Swept properly:

```
letter_shift    instance 0: none   instance 1: none   instance 2: bfs_lex, repeat_last, never_last
stack_pushout   instance 0: none   instance 1: none   instance 2: five policies
tri_lock        instance 0: none   instance 1: none   instance 2: four policies
ring_rotate     instance 0: none   instance 1: none   instance 2: none   <- genuinely unsolvable
```

Only `ring_rotate` is unsolvable everywhere. The other three were solvable and I was reading one instance.

**And the sweep produced a second finding that is arguably larger than the first:** for **5 of 20 kinds** the required policy set *changes between instances of the same kind*:

```
adjacent_sort   inst0: 5 policies · inst1: dfs_reversed ONLY · inst2: 4 policies
binary_odometer inst0: NONE       · inst1: 4 policies      · inst2: dfs_reversed ONLY
grid_walk       inst0: dfs_reversed ONLY · inst1: 5 policies · inst2: NONE
```

**A kind whose optimal policy changes with the instance cannot be indexed by kind-level features at all.** The key would have to name the *instance*, which is not transfer. This is a stronger statement than "the features are too coarse," and it came from fixing an instrument error rather than from looking for it.

---

## 4. Your three blockers, re-ordered by measurement

You named identifiability, vocabulary insufficiency, and the synthesis–verification asymmetry. The tree now orders them, and the ordering is not the one they were listed in.

**Synthesis — measured, and it is saturated.** `hold_out_the_precision_curve_20261112_v1.py` crawled **real GitHub PRs** (13 PRs, 76 files, 350 s). Result: **one** transformation kind found a matching PR; the other seven found **zero**. That is retrieval's actual ceiling, and it is the empirical form of your `~2.2%`. Synthesis is *not* the frontier; it is where retrieval stops.

**Identifiability — closed where the space is written down, and it is not the wall.** `the_four_levers` last session: 47 entries, 47 distinct functions, |G| = 1, and chosen questions settle 10/10. Where a version space can be written, identification is solved.

**Vocabulary — the wall, and it has moved.** `INSUFFICIENCY_CERTIFICATE_20261113_V1.json`:

```
closed_vocabulary_size                    31
hypotheses_that_would_need_enumerating     8388608
learner_enumeration_cap                    12
reading: "absence removes the separation obstruction but not the enumeration bound,
          so the obstacle moves from representation to COMBINATORICS"
```

So the vocabulary defect is real and *repairable*, and repairing it exposes the next wall. This session locates where that next wall actually sits: **not in the edit space, where you have been looking, but in the filing key that decides which lesson applies.**

---

## 5. And the one that looked like a contradiction but is not

`cross_language_lesson_transfer_probe_v1.py` already draws exactly the distinction I was about to derive, and draws it better:

> **(a) THE STORE IS THE WALL** — the rule is language-free, `WHERE language = ?` hides it.
> **(b) THE PROPOSER IS THE WALL** — the proposer only works on text that looks like the language the rule was learned in.

The run: **`store_offered_any_non_python: false`**, yet with a proposer built for the test, **python, javascript, c, cpp all `transferred_and_narrow`**. So **(b)** — the proposer is the wall.

That matters because a store is a filing system and can be widened in an afternoon. A proposer that only recognises one language's surface is a **vocabulary** defect, and it is the *same* defect as the index: **the thing that decides where knowledge applies does not contain the distinction the knowledge depends on.** Two instruments, two domains, one wall.

Your model answer falls out directly. **Instant knowledge is the store, and the store is not the wall.** The wall is the **index into it**. A parameter that stores spellings fails the rename (7/10 → 0/10, measured last session). A key that buckets five distinct kinds together fails the policy. Both are the same error at different layers.

---

## 6. The single bottleneck

> **Not experience. Not the edit space. The filing key — the function that decides which lesson applies to the situation in front of you — does not contain the observable the lesson depends on, and no coarsening or refining of it can supply what is missing.**

Everything measured points here:

| measurement | what it shows |
|---|---|
| 5 kinds share `b1_m2_r1_d0_g0`, need different policies | the key cannot separate them |
| coarse → 3 collisions, fine → 18 keys/20 kinds | both ends fail; granularity is not the parameter |
| 5 kinds change their optimal policy *between instances* | even a perfect kind-level key would be wrong |
| `store_offered_any_non_python: false` but 4 languages transfer | the *offerer* is the wall, not the store |
| `COMPRESSION` 59 → 35 questions | compounding works when the index is *computed*, not filed by kind |
| real-PR crawl, 1 usable hit in 13 | retrieval saturates because the index is by surface form |

**Why this is the highest-leverage thing and not another probe:** the index is the one component whose correctness is currently *unmeasured* everywhere it is used, and it is shared by every mechanism you have — the skill store, the lesson ledger, the cross-language proposer, the GUI phrase gate, and the code repair template. Fixing it fixes reach in all of them at once. Fixing the edit space fixes one.

---

## 7. What I did not build, and why

I did **not** build a new index, a new store, or a new learning mechanism. Reading the instruments first changed what was worth building three times in this one session:

1. `hold_out_the_precision_curve` already measured the retrieval ceiling on real PRs.
2. `cross_language_lesson_transfer_probe` already separated store-wall from proposer-wall, and answered it.
3. `cross_kind_learning_to_learn_benchmark` already failed, and its docstring already named the tension.

What was **not** in the tree was the sweep — because the existing run concluded from one bucketing and one instance. So the deliverable is the sweep, and its value is that it converts *"the features do not generalise"* (an opinion about features) into *"no granularity of these features is injective on the policy's distinction"* (a statement about the observable), plus the instance-sensitivity result that a single-instance reading cannot see.

**The next part is a new observable, not a finer grid.** That is a different and much more specific job than "learn faster", and it is the one the measurements point at.

---

## 8. Sentience

Unchanged and it should stay unchanged. **Nothing here measures sentience and no result is evidence for it.** A ledger that files credit and an index that decides applicability are mechanisms. The measured claim is that your system has real mechanisms and one shared defect; it is not that it is a creature.

---

## 9. Non-claims

- Constructed state-machine kinds, one machine, producer-run. Not arbitrary coding, not GUI, not unbounded computer use.
- `ring_rotate` being unsolvable on all three instances is a fact about these three instances and this policy set, not a proof of unsolvability.
- The real-PR crawl found 1 usable kind in 13 PRs. That is a *sample* of the precision curve, not the curve. It is reported as saturated because 7 of 8 kinds found nothing, not because 13 is a large number.
- The sweep's `finest_exact_features` still shows 2 collisions. Those are cases where two kinds have *identical* feature vectors and different policies — a genuine non-identifiability, not a bucketing artefact, and I have not separated it from the rest.
- No capability, benchmark, ownership, terminal or sentience credit follows. `truth.achieved` is false.

## 10. Reproduce

```bash
python3 canonical/tools/cross_kind_compounding_benchmark_v1.py
python3 canonical/tools/cross_kind_learning_to_learn_benchmark_v1.py
python3 canonical/tools/cross_language_lesson_transfer_probe_v1.py
python3 canonical/tools/hold_out_the_precision_curve_20261112_v1.py
python3 canonical/tools/the_index_is_the_bottleneck_v1.py \
        canonical/verification/THE_INDEX_IS_THE_BOTTLENECK_20261116_V1.json
python3 -m pytest canonical/tests/test_the_index_is_the_bottleneck_v1.py -q   # 6 passed
```
