# One demonstration does not generalise by being repeated. It generalises by being *widened by evidence* — and the leftover is not an algebra gap

**Problem 2, measured.** Branch base `642bcd6661`. Verification record:
`canonical/verification/A_USE_THE_EXAMPLES_DID_NOT_SHOW_SHOWN_BY_THE_FILE_20261112_V1.json`.

---

## 1. The claim under test, said exactly

> "We already solved instant learning perfectly. So give the model the smartest actions once, in each
> environment, and it learns them permanently. That solves all computer use and all software engineering."

This is **half right, and the wrong half is the load-bearing one.** It is right that a demonstration is
retained permanently and costs nothing to reuse. It is wrong that retention is the same thing as transfer.
Problem 1 is memory. Problem 2 is *inference*. A cache answers problem 1 and is silent on problem 2, so
"we solved problem 1 perfectly, therefore problem 2 follows" does not follow.

The honest version of the owner's sentence, which the repository can already defend:

> One demonstration permanently fixes **what changed**. It does not by itself fix **where that change
> applies, or how the changed code may be used**.

That gap is not a mystery and it is not a wall. It is a **finite list of named questions**, and asking a
question costs a piece of evidence, not another demonstration of the whole task.

---

## 2. What is real (re-measured this round, not quoted)

The 15 pull requests and 89 files of `REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json` were **fetched again**
from the commits the record names, each file checked against the sha256 the record holds: *15 pull requests,
89 files, all as recorded*. The organ was then run with one demonstration, leave-one-out over every drawn
file.

| arm | coverage | precision | wrong changes | edits made |
|---|---|---|---|---|
| refuse every use the examples did not show (as shipped) | **16.01%** | 92.41% | 14 | 290 |
| **the file itself shows the use** (this round) | **17.03%** | 92.83% | 14 | 307 |
| the organ's own ceiling, every try kept | **23.48%** | 94.70% | 14 | 415 |

Read the third row before anything else. **The organ's own ceiling on this corpus is 23.48%.** Every
improvement this round or any round can make, without changing what a demonstration *means*, lives between
16.01 and 23.48. Turning "16%" into "90%" is not a matter of a better fit. There is not enough information
in one before/after pair about six 100 KB files to determine 90% of 1,674 edits. Any claim otherwise would be
a claim to have compressed behaviour into nothing.

So the real state of Problem 2 is: **one demonstration returns 72.5% of everything that demonstration can
ever return, at 93% precision, and nothing in the algebra can push past 23.5%.** The remaining 76.5% is
mostly *not* a defect. That distinction is the whole answer, and it is measured in §3.

### 2.1 The number's denominator is honest

`usable()` admits a file only when its statement lines differ before and after, so a file that did not
really change never enters the denominator. The share is
`right_not_imports / developers_changes_not_imports` — the developers' own non-import changes, not a count
the organ chose. The measurement cannot be inflated by picking easier files, because leave-one-out uses
**every** drawn file as the demonstration in turn.

### 2.2 A change that looks free is not free

Two things were tried and only one survived. Both matter, because the survivor is the shape of the answer.

**Rejected — "a rename cannot care about arguments, so drop the check."** A rule that puts a name where a
name stood (`shapes.area` → `shapes.size`, `self.assertEquals` → `self.assertEqual`) writes inside the
callee's span, and a call's arguments lie outside that span. It is tempting to conclude the change is
therefore indifferent to how it is called. It is not: **a function is usually renamed because its signature
changed.** That is why `assertEquals` became `assertEqual`. Dropping the check measured well — 23.06%
coverage, 94.61% precision — and was still wrong. The repository already recorded the law it broke:

> shown with two arguments and with four is not shown with three: nothing between two showings is assumed.

Three of the organ's own tests say so explicitly. A number that improves by breaking a stated law is not an
improvement, which is the whole reason the law was written down first.

**Kept — let the file answer the question the refusal asks.** The refusal does not say "I do not know".
It says *"show that use too, changed or left alone"*, and names the use. Sometimes **the answer is already
in the file**: a file that already calls `shapes.size(x, y, z)` with three arguments is its own witness
that `shapes.size` takes three arguments. That is not an assumption. It is a showing — the same widening a
second demonstration gives, read off the file instead of off a second demonstration, so it costs no
demonstration. Shown with two and four still says nothing about three; the file has to say three.

Result: 16.01% → 17.03% coverage, precision **up** 92.41% → 92.83%, wrong changes **unchanged at 14**, and
the organ's own test file goes from 4/5 to 5/5 with exactly **one** test flipping — the one named for the
behaviour. The gain is small on purpose. It is the part of the ceiling that was reachable by **evidence**
rather than by **guessing**.

---

## 3. Where the missing 76.5% actually is

This is the part that decides where to work next, so it must be read as counts, not as an apology.

**By kind of change** (8 kinds, 2 pull requests each — a per-kind number is n≈2 and is not a rate):

| kind of change | coverage | precision |
|---|---|---|
| a call written the old way | 43.23% | 1.00 |
| a call that is no longer to be used | 29.73% | 1.00 |
| an old name of a test method | 32.70% | 1.00 |
| an old name of a test method, second | 17.02% | 1.00 |
| an old name of a logging method | 8.42% | 0.98 |
| types written another way (PEP 585) | 7.20% | 0.73 |
| a library taken out (remove six) | **0.00%** | — |
| text put together another way (f-strings) | **0.00%** | — |

The two zeros are structural, not accidental. **Removing `six` leaves the import lines changed and every
call site untouched** — the developers' change *is* the imports, and this measure deliberately excludes
imports from the denominator, so the kind has nowhere to score even though the organ handles it. **Turning
`"%s" % x` into an f-string rewrites a whole expression in place**, and a rule learned from one such
rewrite fits nothing else until the exact text matches. Both are cases where *the form of the demonstration
itself* carries too little, not cases where the algebra failed.

**By pull request** (the denominator is very unevenly spread):

| pull request | coverage | denominator |
|---|---|---|
| `inveniosoftware/invenio-pidstore#189` | 0.0% | 115 |
| `nipy/nibabel#1609` | 0.0% | 70 |
| `InterDigitalInc/CompressAI-Vision#40` | 0.0% | 35 |
| `jupyter/jupyter-sphinx#301` | 0.0% | 110 |
| `kuangjiafa/automagician#55` | 0.0% | 40 |
| `Cytomine-ULiege/Cytomine-python-client#61` | 58.8% | 85 |
| `apache/libcloud#2217` | 40.0% | 30 |
| `arigatoexpress/Project-Go-Forward#483` | 27.7% | 155 |
| `openimis/openimis-be-core_py#414` | 28.3% | 315 |

**Half the pull requests return nothing, and four of them hold 370 of the 1,674 changes.** The headline
number is a mixture of "the demonstration was excellent" and "the demonstration was of a change that does
not repeat". This is the single most important fact about Problem 2 and it is invisible in the average.

**The refusals are the roadmap.** 440 askings, and the classes are questions, not walls:

| refusal | count | share | is it the algebra's fault? |
|---|---|---|---|
| nothing in the file has the form the example changed | 168 | 38.2% | **No.** The file has no such code. There is nothing to generalise to. |
| edited | 90 | 20.5% | No. This is success. |
| the two example files hold the same code apart from imports | 60 | 13.6% | **Yes.** The demonstration showed nothing to repeat. |
| only a change inside one expression is shown | 25 | 5.7% | **Yes.** The demonstration reshaped a whole statement. |
| the change reads a name the file does not have | 22 | 5.0% | **Yes**, and partly: a name that arrives by an added import is findable. |
| called with a number of arguments the examples did not show | 46 | 10.5% | **Yes**, and it is answerable by evidence (§2.2). |
| the same code was left alone elsewhere | 15 | 3.4% | No. The developers were inconsistent; refusing is correct. |
| the edited example text does not parse | 10 | 2.3% | Yes, but it is an input artefact. |

So "43% of askings are the algebra failing" is roughly true, and **the single biggest class — 38% — is not
an algebra failure at all**: it is the corpus showing the organ a change that the file does not contain.
That class is a property of *what a repeated change looks like in the wild*, not something to fix. It is
also the reason a higher coverage number on this corpus would be suspicious.

---

## 4. Why "give it the smartest actions once and it learns permanently" cannot close the gap

Four independent reasons, each of which would have to be false for the owner's plan to work, and each of
which the repository has already measured:

1. **A demonstration underdetermines a rule, and one demonstration identifies nothing.** Over 47 programs
   and 10 targets: one demonstration leaves **14.1 surviving rules** and identifies **0/10**. Three
   demonstrations identify 5/10. But **one demonstration plus two well-chosen questions identifies 10/10.**
   More demonstrations is the *expensive* way to buy information that questions buy cheaply.
2. **A success teaches applicability almost nothing.** Over 200 exhaustive cases, one successful
   demonstration answers **0/200** applicability questions. **Chosen failures answer 25/25 in a mean of 2.76
   demonstrations.** Exposure informs; refutation identifies.
3. **Uncurated exposure is worse than no exposure.** Curated skills: **+16.2 pp**. Self-generated skills:
   **−1.3 pp**, with 16 of 84 tasks negative. Across 49 skills on SWE-Skills-Bench, 39 are zero and the mean
   is **+1.2%**. A model that experiences the most advanced actions once and keeps them is, measured, the
   negative case — unless something curates what it keeps. That curator is the operator algebra, and it is
   the only part of this that is not a matter of more data.
4. **Everything that generalises on unseen tasks pays in search, not in exposure.** DGM and SICA move
   SWE-bench 20→50 and 17→53 by archive-and-select over many generations at ~$22k of search. Weight training
   is the only method that beats a cache-each-task floor across a lifelong stream (held-out 0.29 vs seen
   0.57). In-context state alone never does.

The owner is **right** that this is a better learning mechanism than the current one — but for a sharper
reason than stated. It is not better because it is faster at absorbing. It is better because **the unit of
learning is a checked change rather than a gradient**, so every item learned is verifiable, free to keep,
and impossible to catastrophically forget. That is a real and under-exploited advantage. It is an advantage
in *cost and in trustworthiness*, not in *reach*.

---

## 5. What to do next, in order, and what not to do

**Do not** do these. Each is attractive and each is already refuted here or in the record:

- Do not "just show it more examples". A second demonstration buys **+8.13 to +9.6 pp** and then saturates.
  Questions buy the same information for 2.0 askings.
- Do not "just run the ceiling". 23.48% is 6.45 pp above where the organ already is with evidence. Every
  further point there is bought by *guessing*, and a guess that is right is indistinguishable from a guess.
- Do not use a model to widen the rule. That is producer cognition and it is forbidden.
- Do not widen the vocabulary. The corpus's biggest failure class is files that do not contain the change.
  More rule kinds cannot help code that is not there.
- Do not chase the zero kinds (six removal, f-strings) with the same organ. Their demonstrations do not
  repeat by construction.

**Do**, in this order, because each step re-measures the same 8 kinds from the same re-fetchable bytes:

1. **Cross-file witnesses.** This round reads the file. A use shown by *another* file of the same project
   is the same evidence, one file over, and is untouched. Cheap, sound, and it is the largest remaining
   evidence-shaped gain.
2. **Make the demonstration informative (13.6% + 5.7% = 19.3% of refusals).** Both classes say the same
   thing: the demonstration's *form* carried too little. When the example holds the same code apart from
   imports, or reshapes a whole statement, the honest move is to ask for the smallest demonstration that
   does repeat — not to widen the algebra.
3. **Report per-pull-request, never as a mean.** Half of these pull requests return nothing and four hold a
   fifth of the denominator. A mean over them is a claim about nothing. The per-PR table is the real result.
4. **Before any of that, watch the divide.** When a demonstration repeats in 5 of 6 files and not in the
   sixth, that is the developers *telling* the organ where the change applies. This is the cheapest
   applicability evidence in the corpus and it has never been exploited.

---

## 6. The scorecard, unchanged where it must be

Authority **NONE**. Cost **$0**. Model calls **0**. `truth.achieved` **false**. No capability registered, no
guard weakened, no law relaxed — one was *enforced* at the cost of a better-looking number (§2.2).

**Answer to "is this a revolutionary way to make agents learn faster?"** Yes, and it is the only one on this
list whose every learned item is verifiable, free to keep and impossible to forget. **Answer to "can we just
let it experience everything once?"** No, and the corpus says exactly why: exposure informs, refutation
identifies, and one experience identifies nothing. **What is real:** one demonstration permanently fixes what
changed, returns 72.5% of what it can ever return at 93% precision, and 76.5% of the corpus was never reachable
from it. **What is not:** that retention is transfer, and that reaching 90% is a matter of a better fit
rather than of asking better questions.
