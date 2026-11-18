# The statement names the change and never specifies it

Five dimensions are now spent against the same residual work — the parts a change's own suite accepts without
pinning. Input **shape** (round 17, 2 of 8), the **value** a condition wants (18, none more), the repository's own
**documents** (19, none more and one lost), the language's **protocol operations** (20, none more). Round 20 found
the structure underneath all four: 27 of 36 fixes are fully pinned by their own suites, and what stays open is what
nobody tested.

That leaves exactly one source in the loop that contains what the artifact does not: **the sentence the author
wrote about the change.** `declared_input_derivation_v1` already binds slot values from human sentences — which
file, which name, which test command. Nothing in the tree asked the harder question:

> does the statement say what the behaviour should **be** — an expected value, an expected exception, a number?

This round asks it, and answers it the only way that counts: by trying to build the pin from the statement alone
and verifying it against both states.

## The two columns

For every part the suite accepts without, two things are measured separately:

- **names** — does a quoted literal, a code identifier or an exception name from the statement appear in the changed
  hunk? (the weak form: the sentence mentions the change)
- **specifies** — can a pin be *constructed* from the statement alone — its quoted literals as inputs, its exception
  and identifier names as expectations — and does that pin pass at the fixed state and **fail** at the state with
  the part reverted? (the strong form, and the only one that buys capability)

| corpus | fixes | parts the suite accepts without | **names** | **specifies** | candidates walked |
| --- | --- | --- | --- | --- | --- |
| `--limit 17` | 11 (11 with a statement) | 11 | **6 (54.5%)** | **0** | 0 |
| `--limit 24` | 17 (16 with a statement) | 8 | **4 (50.0%)** | **0** | 0 |

The statements are what real repositories actually write:

```
access sha1 lazily
perf: add __slots__ to Requirement (#1320)
Error messages: Surround illegal character by only one pair of quotation marks
NEW: Print line and column in error message when relevant (#8)
fix(metadata): charset error message formatting (#1121)
```

Titles. They name a subject. Not one of them states an input and the outcome it must produce.

## The detail that makes the zero honest rather than convenient

Three statements in the wider sample *do* quote something — `Correct regex for metadata 'name' format (#925)` with
three quotations, `fix: dependency group malformed parse caching (#1248)` and `tomli.loads: Raise TypeError not
AttributeError` with one each. Those three fixes have **no open parts at all**: their own suites pin everything. The
quotation and the open part never meet.

So the census is not "we looked in the wrong place". It is: *where the statement is explicit, the work is already
tested; where the work is untested, the statement is a title.*

## What this closes, and the contract it leaves

A demonstration is checkable exactly to the extent that it **ships its discriminating input**. That is now measured
from six independent sides — tests (16), shape (17), wanted values (18), corpus (19), operations (20), and the
author's own words (21) — and it is the same law the 2026 field reports from its own measurements: *All Smoke, No
Alarm* found weak or absent oracle signals in **80.2%** of 86,156 agent-authored test patches, and SpecCoder (July
2026) found that even with a model in the loop, generated assertions are "syntactically invalid, trivial, or too
weak to reject behavior-changing faults".

What follows is not a seventh search dimension. It is a **contract**:

> When no discriminating input exists, the agent's first action is not to search harder — it is to acquire one.
> The module now emits the question explicitly: *these are the callables the test already reaches, the two states
> agree on every input the statement states, and the missing object is the outcome that should differ.*

That is what a capability engine owes a user who is not technical: not a guess, and not a silent failure, but the
smallest question that would make the work checkable. `the_question` is written into every residual row, and
`parts_that_require_a_question` is the size of that debt — 11 of 11 and 8 of 8 here.

## What is real and what is not

Real: the mechanism works — the fire proof builds a pin from a sentence quoting `"beta-omega"` and naming
`ValueError`, and that pin passes at the fixed state and fails at the reverted one, with the tree restored and no
pin file left behind. Real: in this corpus, naming is common (50–55%) and specifying never happens (0 of 19).

Not real: that a better extractor would change the answer — the statements do not contain expected values to
extract, and the three that quote something sit on work that is already pinned. Not real: that "experience it once"
can transfer a behaviour the demonstration never separated. Not real: that the remaining work is a search problem.

**The single bottleneck, final form: the discriminating input is knowledge.** It is authored, it arrives with the
change, and no mechanism inside the loop — corpus, mutation, wanted value, protocol operation, statement — can
manufacture it. What remains to be built is not a better search but an *acquisition*: the agent must be able to
recognise that the spec is missing, state the smallest question that would supply it, and continue the moment it
arrives.
