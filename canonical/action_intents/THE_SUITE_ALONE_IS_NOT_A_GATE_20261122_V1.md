# The suite alone is not a gate

*`canonical/tools/the_assertion_is_the_demand_v1.py` · specification demand + candidate-side slot gate · 22 tests · receipt `canonical/verification/THE_SUITE_ALONE_IS_NOT_A_GATE_20261122_V1.json` · 30 real commits · 82.8 s · 0 parameters*

---

## What this round set out to do, and what it actually found

Last round's declared next step was to read the demand from the assertion's own text instead of reconstructing it from a captured failure value, because 13 of 30 real commits had no bindable demand. That is now built and measured. It works — and it immediately certified a patch that was not a repair.

**click `91de59c6c8`, ungated:** the site is the boolean `self.default is UNSET`. A demand read from the failing test's own literal was satisfied by `flag_value` — a bare frame name of another type — which greened **533 tests** while preserving **0 of 12** recorded passing values of the site. The human's own fix preserves **12 of 12**. The suite said yes to a function that was never the fix.

That is the round. Not a larger search, not a better vocabulary: the acceptance evidence my instrument was using is not sufficient to certify capability, and *I am the one who has been treating "the file goes green" as the only gate.*

## The mechanism, honestly

A test states what it expects, in source. When the runtime cannot bind a demand, the expected value is not unknown — it is written down. `test_literals()` reads the failing test's own literals (per test, never the whole file: attaching `test_two`'s values to `test_three` makes the filter unsatisfiable by construction, which is how a first version reported "searched 20,632 candidates and found nothing" while no demand had been installed at all).

Becuase that demand is **weaker evidence than a bound one**, it forces a **stronger acceptance requirement**:

| demand provenance | what proves the assertion is about this site | what a candidate must also do |
|---|---|---|
| `BOUND_ASSERTION` | an assertion operand already holds what the site produced | produce the demand and differ from the site's value |
| `SPEC_LITERALS` | nothing at runtime | keep the site's **slot** (same type at every recorded frame) **and** preserve every recorded passing value |

The candidate-side rule is the same law as the demand binder — *same slot, not same value* — one level up. Applied: `flag_value` (a list/string where the site returns a bool) is refused, and `91de59c6c8` becomes `SPEC_DEMAND_FOUND_NOTHING` instead of a false `DEMAND_MET`.

## After, on all 30 real commits

| stage | rows | note |
|---|---|---|
| not a single-expression replacement | 15 | **all 15 are `MULTI_LINE_EDIT`** — the human's hunk is not one line |
| the fix introduces a name | 3 | up from 2: the specification demand unblocked the audit on a row that used to stop at the pairing |
| searched, nothing admissible | 5 | 150,000+ candidates offered per row |
| no relation (demand refused) | 5 | |
| the site never ran in the failing test | 1 | |
| `DEMAND_MET`, human's own fix, whole file green | **1** | **unchanged** |

Accusations against the truth: **0 of 30**. Parameters: **0**. Verified repairs: **1**, the same one as before.

## The two numbers that decide the next round

**150,000 candidates, 0 admissible.** On the rows the fallback made searchable, ~150,000 expressions were offered over the site's own frame and *none* satisfied the demand while keeping the slot and the passing rows. The candidate supply is not the shortage. The **shape** is: a real fix is a composition — a value produced in one place, consumed in another, often with a new name introduced — and every mechanism here assumes one expression at one site. That is also why 15 of 30 rows leave the population before the reader is even consulted: not because those fixes are uninteresting, but because their *diff* is not one line, and the instrument derives its site from the diff.

**533 greens, 0 of 12 preserved.** The gate is the currency. A verifier that only says "green" cannot distinguish a repair from a different function that happens to pass, which is precisely the failure this project keeps naming in its own history and had not yet caught in its own gate.

## What is not claimed

- That the specification fallback adds verified repairs on this corpus. It adds **searchable rows** (8), and the honest count of new repairs is **zero**.
- That `91de59c6c8` is unsolvable. Only that the instrument, gated, cannot certify a patch there.
- That preservation is a valid gate in general — it is a gate *for weak demands only*, because for bound demands it rejected 13 of 14 real human fixes on an earlier round.
- That 1 verified repair is capability.

## Next step

Admit shape: a hypothesis may be **a value produced at one site and consumed at another**, and may **introduce a name**, because that is what 18 of 30 real fixes are. Declared acceptance, before building: at least **1 verified repair whose human fix is multi-line**, accusations still **0**, and no verified row that preserves 0 recorded passing values. The ceiling argument is stated up front this time: the corpus has 30 rows, 18 of them composite, so a shape-admitting search can be judged on at most 18.
