# Same slot, not same value: a demand is bound to an assertion or it is refused

*`canonical/tools/the_assertion_is_the_demand_v1.py` · paired binder · 19 tests · receipt `canonical/verification/A_DEMAND_MUST_BE_BOUND_TO_THE_SITE_20261122_V1.json` · 30 real commits · 31.7 s · 0 parameters*

---

## The number I declared, and the number that is true

Last round's stated next step carried an acceptance I set myself: **accusations against the truth = 0, ADMISSIBLE ≥ 6, verified count unchanged.** Two of those three landed. The middle one cannot land on this corpus, and it is worth saying exactly why instead of letting the round quietly miss it.

Of 30 real commits, **15 are not single-expression replacements at all** — the human's fix introduces a name, a statement, a new branch. Of the 15 that reach the demand reader, **13 have no demand that can be bound** to the site. So the ceiling for *any* binder on this corpus is **1 admissible row**, and 1 is what it reports. Claiming "≥ 6" was a forecast made before the exclusions were counted; the honest form of the number is: *the reader binds 1 of 2 in-class rows, and the corpus is the limit, not the reader.* Any future acceptance on admissibility has to be measured against a corpus where more than 2 rows are in class.

## The two ways to get binding wrong

The demand is the value a failing assertion says the site owes. Binding it means deciding *which* assertion speaks about *that* site. I tried the two obvious rules and both are wrong, and both were wrong **measurably**, not theoretically.

**Rule 1: the demand must equal what the site produced.** This destroys the instrument. The demanded value is *meant* to differ from the one the site produced — that difference **is the repair**. Under this rule the single row this instrument verifies fell to `NO_VALUE_MATCHES`: a test demanding `"…for 'x'."` against a site emitting `"…"` is not a contradiction, it is the fix.

**Rule 2: the demand must share the site's type.** This accuses the truth, because Python says `0 == False`. The row that kept slipping through is `demanded=[0] produced=[False]`: an integer demand bound to a boolean predicate it has nothing to do with, and then reported as the human's fix producing the wrong value.

Type-strict equality is a patch on both, and it has the same defect as Rule 1: it refuses every numeric repair, where the site produces `3` and the test demands `2`.

## The law

Neither the demand nor the site can be read in isolation. **The assertion itself supplies the evidence**: an assertion is about the site only if one of its operands already holds exactly what the site produced. That operand **is** the site. The demand is **the other operand**, and it is not compared to the site's value at all — only its structure is read (`assert (msg,) == exc.args` demands the message, not a one-tuple).

```
pair:    type(operand) is type(produced) and operand == produced   -> this side is the site
demand:  the other operand, with one-element sequence structure unwrapped
refuse:  no operand holds what the site produced, or the demand is prose
```

Equality survives only where it is evidence — identifying which operand is the site — and never where it would be a verdict on the demand.

## The four rows that were accused, before and after

| commit | before | after |
|---|---|---|
| `1c962d15a7` attrs | `ADMISSIBLE` | `DEMAND_MET`, 2 survivors, the human's expression admissible, **verified** |
| `91de59c6c8` click (`[0]` vs `[False]`) | `VALUE_DIFFERS` | `NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE` |
| `13105a64f2` attrs (exception message) | `VALUE_DIFFERS` | `NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE` |
| `a150ff749a` jinja (coroutine message) | `VALUE_DIFFERS` | `NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE` |

## After, on all 30

| stage | rows |
|---|---|
| not a single-expression replacement | 15 |
| no relation — the demand is refused, reason named | 13 |
| the site never ran in the failing test | 1 |
| `DEMAND_MET` (the human's own fix, whole test file green) | 1 |

Against last round: 15 · 2 · 6 · 5 · 1 (site-never-ran) · 1. **The 5 `NO_VALUE_MATCHES` and the 2 `EXCLUDED__THE_FIX_INTRODUCES_A_NAME` rows are exactly the 13 − 6 = 7** that moved. Accusation-shaped stages are now **0 of 30**. No row accuses the human of producing a wrong value for an assertion the site has nothing to do with.

## A refusal now shows its operands

A refusal is a claim too, and an unchecked claim is worth nothing. Every refused demand is written into the receipt with what the site actually produced, under one of two names that had been conflated:

```
reason:   THE_SITE_PRODUCED_NO_VALUE
demanded: ('I/O operation on closed file.',)
produced: []

reason:   NO_SLOT_IS_SHARED_WITH_WHAT_THE_SITE_PRODUCED
demanded: 0
produced: ['False']
```

30 refusals are `THE_SITE_PRODUCED_NO_VALUE` and 40 are `NO_SLOT_…`. That split matters: the first is a **limit of the driver** — nothing was captured at the site, so nothing could be bound — and the second is a **fact about the assertion**, which is about some other value entirely. Calling both "no relation" hid the difference between "I could not see" and "it is not there".

## What this does not claim

- **Not that refusals are losses.** A refusal costs a row we could not verify; an accusation costs the instrument's credibility, permanently. Zero accusations is the correct order of priority.
- **Not that the 2 name-introducing rows are gone.** They stop earlier now, at the pairing, and are reported as `NO_RELATION…`. Both are exclusions either way, but the *reason* is coarser than the audit's — a diagnostic regression this round accepts knowingly rather than re-running the driver on rows it already refuses.
- **Not that 1 is capability.** It is one verified repair, on material the instrument has already been tuned against. The transfer claim in the standing argument is still unsupported, and this round does not touch it.
- **Not that the pairing is sound in general.** It shows the assertion is about the site *in the frame that ran*. A site that feeds a value into a helper the assertion then tests is refused, and that class is invisible in this census.

## Next step

Thirty of 70 refusals say the site produced no value the driver could see, and 14 demand strings are still prose. The demand therefore has to be read from **the assertion's own expression against the frames the site ran in**, not reconstructed from a captured failure value — the assertion text is committed source, and the site's own execution is the frame. Declared acceptance for that round: bound demands on **≥ half of the in-class rows**, accusations still **0**, verified count **≥ 1**, and the ceiling reported as a ceiling.
