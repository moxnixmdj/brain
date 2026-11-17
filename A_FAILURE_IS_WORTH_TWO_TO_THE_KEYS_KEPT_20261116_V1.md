# A failure is worth 2^k, where k is what it kept

**Date:** 2026-11-16 · **Branch:** `arena/f68feb16-brain` · **Base:** `68e8d11b`
**Authority:** `NONE__PRODUCER_RUN`. Producer-run, this machine, $0, zero model dependency.

---

## 0. The honest part first

I was going to ship a combinatorics repair this session. **It already existed.**

`THE_LEARNER_DECIDES_PAST_THE_ENUMERATION_WALL_20261116_V1.md`, merged yesterday, shipped
inclusion-extraction: `learn` now decides every case whose failure side fits a budget, counting survivors arithmetically instead of listing them, verified exact against brute force on 5,058 exclusion families. The `2^23` enumeration wall the `INSUFFICIENCY_CERTIFICATE` moved us to **is closed**.

Reading that receipt instead of rebuilding it is what produced this document. Its own real-corpus measurement contains a number nobody had read:

```
vocab 31, |A| = 23, m = 2 failures, D_i = [20, 20], raw survivors 8,388,600 = 2^23 - 8
```

**That number is 8 hypotheses killed, out of 8,388,608, for two failures.** This document is the arithmetic of why, and it is not what it looks like.

---

## 1. The arithmetic the receipt contains

A survivor is a subset `C ⊆ A` that hits every `D_i = A \ F_i`. `C` misses `D_i` only when `C` is built entirely from the facts the failure **kept**. So one failure eliminates exactly

```
2^|F_i ∩ A|
```

Using inclusion-exclusion on the receipt's own numbers:

```
survivors = 2^23 − 8 − 8 + |miss both|   =   2^23 − 8
      ⇒   |miss both| = 8
      ⇒   A\D₁ = A\D₂
```

**The two failures omitted the identical three candidates. They were the same failure recorded twice.**

Verified against the live counter, not by algebra alone:

| 23 candidates, 2 failures | eliminated |
|---|---:|
| the SAME three dropped twice | **8** — and survivors are exactly `2^23 − 8`, matching the receipt |
| two DISTINCT triples | **15** |

**A second failure bought 7 hypotheses out of 8,388,608.** The corpus produced two failures and the learner gained almost nothing from the second, because it was the same evidence twice.

---

## 2. The law, and why it inverts the instinct

```
one failure eliminates 2^k, where k = the shared candidates it KEPT
```

| kept | dropped | hypotheses killed | share of 2^23 |
|---:|---:|---:|---:|
| 1 | 22 | 2 | 0.0000 % |
| 3 | 20 | 8 | 0.0001 % |
| 10 | 13 | 1,024 | 0.0122 % |
| 20 | 3 | **1,048,576** | **12.5 %** |

**The most informative failure is the nearest miss, not the biggest failure.**

A dramatic failure — one that drops most of what was shared, i.e. fails for a completely different reason — kills two hypotheses. A **near miss that differs on a single candidate fact** kills half the space. The instinct that learning comes from *failing more* or *failing harder* is exactly backwards. Learning comes from failing **as close to success as possible**.

This is why the corpus above is a warning and not a success story: it produced two failures of the worst kind in terms of information, and they were duplicates of each other.

---

## 3. What this says about your three blockers, in order

**Identifiability — solved where the space is written, and the arithmetic is now exact past the cap.** `learn` decides `|A| = 23` in `0.000 s` instead of listing `2^23`. Nothing to fix.

**Vocabulary — closed to kinds and absence, and the obstruction moved to combinatorics, which is now closed too.** Two walls, both fallen, both measured.

**The third one is where the capability actually is, and it is now priced.** The certificate's wall was *enumeration*. The enumeration wall is gone. What remains is not a wall of compute — it is that **the evidence we generate is worth almost nothing per failure**. Two failures, 8 hypotheses. That is not a learner limitation. It is an **experiment-design** limitation, and it is measurable in bits:

```
one contrast that drops 1 fact   =  ≤ 1 bit  (kills 2^(n-1) = half the space)
one contrast that drops 20 facts = 0.0001 bit
```

So the highest-leverage action is not more failures, not more environments, and not a bigger vocabulary. It is **choosing the failure that differs on one candidate.** `contrast_selection_v1` already does the choosing, by the exact split it produces — this document supplies the *price*, which is what a redesign of the observable budget needs to be aimed at.

---

## 4. Why "the best part is no part" applies here, concretely

The tempting next move is: **add more facts to the vocabulary so failures can differ more.** That is the wrong direction, and the arithmetic says so. With `|A| = 23`, a failure that drops one fact still halves the space; adding facts to `A` does not change the `2^k` law, it only raises `n` and makes each hypothesis smaller. **The lever is the contrast, not the vocabulary.** The vocabulary work is already done and closed.

The one part that is worth building is the one that was missing: **a selector that prices a candidate contrast by `2^k` and refuses one that cannot move the count.** That part does not exist as a price; `contrast_selection_v1` computes the split but nothing currently says *"this failure is worth 2 hypotheses and is therefore not worth running."*

---

## 5. Non-claims

- Constructed universes at the receipt's own scale, one machine, producer-run. This prices the law; it does not re-run the real corpus.
- The `2^k` result is an identity of the surviving-set structure, not an empirical finding. Its *use* — that the real corpus's two failures were duplicates worth 8 total — is the empirical part, and it is derived from the receipt's own recorded numbers.
- `|F_i ∩ A|` counts only shared candidates. A failure that keeps facts *outside* `A` gains nothing, which is stated in the law and not glossed.
- The most informative single failure available kills **half** the space (one bit), not all of it. No single failure finishes identification; that is why `contrast_selection_v1` exists and why §3 calls this an experiment-design problem rather than a data-volume problem.
- No capability, benchmark, ownership, terminal or sentience credit follows. `truth.achieved` is false.

## 6. Reproduce

```bash
python3 canonical/tools/a_failure_is_worth_two_to_the_keys_kept_v1.py \
        canonical/verification/A_FAILURE_IS_WORTH_TWO_TO_THE_KEYS_KEPT_20261116_V1.json
python3 -m pytest canonical/tests/test_a_failure_is_worth_two_to_the_keys_kept_v1.py -q   # 7 passed
```
