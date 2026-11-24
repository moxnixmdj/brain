# Does experience compound? No — measured

**Round 13. Rounds 9–12 built a machine that can produce a missing kind and judge it, and by round 12 it read 98.2% of a real system. Before building round 13 on the same pattern, I tested the strategy those rounds assume. It does not hold as stated.**

Date: 2026-11-24 · Base: `b182859b` (PR #7061) · Branch: `arena/2ebebc2e-brain`

---

## 1. The bet under test

> the agent does something once, learns it permanently, and the world already publishes a guide for everything — so one demonstration per environment should total computer use.

The tree already held the numbers to test this, so **no new episode was run.** Round 13 is a measurement over one recorded run: 130 tasks, 78 that produced a program, 478 steps each carrying a measured `descriptions_left`.

## 2. The currency: bits, not success rates

Every earlier answer measured *rates* — "one success generalises to 60-70%", "new task kind is 0/10". A rate says how good a skill is. It cannot say whether experience makes the **next** task cheaper, which is what a strategy turns on.

The currency that can: a step leaving `d` candidate descriptions costs **log2(d) bits**. That is arithmetic, not a judgement about the learner.

The prior, re-measured: **a step costs ~5 bits; one experience pays ~1.** So one demonstration cannot identify a program.

## 3. The three new measurements

### (1) Does it compound?

Walk the 78 tasks **in order**, weighted by steps actually taken:

| | bits/step |
|---|---|
| first half of the run | **5.49** |
| second half | **5.39** |
| **change** | **−0.10** |

**Flat.** The threshold is 0.25 bits and is stated in the receipt so a later round cannot call a 0.1-bit drift compounding.

The vocabulary *does* keep growing — 96 descriptions, **57% arriving in the second half**. Reuse is real (1.55×). **Neither is compounding**, and quoting the first as if it were the second is the mistake this round exists to prevent.

### (2) Where does the cost live?

The tree named the remaining lever: *a smaller description language.* Tested:

| attribute | n | bits |
|---|---|---|
| `self.tag` | 61 | 263.1 |
| `self.classes` | 43 | 250.6 |
| `self.id` | 28 | 165.4 |
| everything else | 14 | 72.6 |
| **total** | 146 | **751.7** |

**90.3% of the bill sits in three attributes that each name an element.** Zero conjunctions — every description is already a single atom. Removing one attribute removes the ability to say what a step targets.

**The language is already minimal. That lever is spent.**

### (3) Is the cost learnable or page-shaped?

| candidates left | steps | share |
|---|---|---|
| 1–5 | 22 | 4.6% |
| 6–20 | 72 | 15.1% |
| **21–60** | **221** | **46.2%** |
| 61–150 | 146 | 30.5% |
| 151+ | 17 | 3.6% |

**63% of real steps face more than 30 candidates.** The cost is log2 of what the page does not distinguish — which **no learner can lower by seeing more pages.**

## 4. The verdict on the strategy

**Retracted as a total answer.** "Learn each environment once and that totals computer use" is *false* for the measured cost of identifying a step: the price is set by page density and does not fall with experience.

What survives is narrower and still real: **each experience permanently removes about one bit** — measured, permanent, costs no parameter. And rounds 9–12 built the mechanism that reads and judges the environment that bit is about.

## 5. What this refuses to claim

- **That one experience is useless.** It pays about one bit, permanently.
- **That the 5 bits are irreducible in principle.** A *different* description language would lower them. What is measured is that *this* language is already minimal at this size.
- **That a better learner fixes it.** The cost is log2 of what the page does not distinguish.
- **That this generalises beyond MiniWoB-shaped pages.** It is one recorded run.

## 6. The lever that remains

The bill falls when an **observation removes candidates** — an *acting* question, not a learning one. Looking before choosing lowers the price in a way no amount of experience can.

That is where round 14 belongs: not another judge, but the loop that **asks before it chooses**.

## 7. Verification

- 9 new tests, including **two synthetic receipts** proving the verdict follows the data rather than being a hard-coded constant (FLAT / COMPOUNDS / ANTI_COMPOUNDS all reachable)
- `read_from` names the receipt; `model_calls = network_calls = parameters = 0`
- Self-consistency asserted: the by-attribute bits sum to the stated total

## 8. Limits

- One recorded run; MiniWoB-shaped pages only.
- The 0.25-bit threshold is a resolution statement, not a law.
- The receipt holds `first_success` programs, so skills beyond first success are not counted.
- No new episode and no benchmark task.

Authority `NONE`, sandbox only, independent verification **OPEN**.
