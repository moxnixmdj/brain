# One demonstration already gives 98% of what one demonstration can give. The corpus is not where Problem 2 is stuck.

**Problem 2, measured on the shipped organ.** Record:
`canonical/verification/WHAT_ONE_DEMONSTRATION_ALREADY_GIVES_20261112_V1.json`.

This round built a widening, proved it sound, measured it — and **did not ship it**, because it measured
zero. That is the result. It is also the most useful thing this round produced, because it moves the
question of where Problem 2 actually is.

---

## 1. The number that settles the argument

Files fetched again from the commits the record names, each checked against its sha256: *15 pull requests,
89 files, all as recorded*. One demonstration, leave-one-out over every drawn file.

| arm | coverage | precision | wrong changes |
|---|---|---|---|
| refuse every use the examples did not show | 16.01% | 92.41% | 14 |
| **the shipped organ, one demonstration** | **23.06%** | **94.61%** | 14 |
| **the shipped organ's own ceiling** | **23.48%** | 94.70% | 14 |

Read the last two rows together. The shipped organ is already at **98.2% of its own ceiling**, and the
0.42 pp between them is bought by *guessing* — the ceiling arm changes every place a rule fits, including
places no evidence settles, and it gets **no more of the developers' changes right and no more wrong**.

So the honest statement of Problem 2 on this corpus is not "16%, could be much higher". It is:

> One demonstration fixes what changed and applies it to **23.06%** of the developers' other non-import
> changes at **94.61%** precision, which is **all but 0.42 pp of what that demonstration can support**.
> Coverage cannot rise further without changing what a demonstration *means*.

That is a floor set by information, not by the algebra. And it is why "give it the smartest actions once
and it learns permanently" cannot close the gap by fitting better: there is nothing left to fit.

## 2. What was built, verified, and then withdrawn

The refusal *"this place is used a way the examples did not show"* is answered, in the shipped organ, by a
closed list of names the standard library kept for each other. That list is right and it is checked. But it
only covers *documented aliases*. The same question can be answered by **the file itself**: a file that
already calls `shapes.size(x, y, z)` with three arguments witnesses that `shapes.size` takes three.

That was implemented, and it was sound:

- the widening fires only when the new code is called that way **somewhere in the same file**, at a place
  the change leaves alone — a showing, not an assumption;
- shown with two arguments and with four still says nothing about three, which is the law that killed an
  earlier attempt to exempt renames wholesale (that attempt measured 23.06% and was still wrong, because a
  function is usually renamed *because* its signature changed);
- of the six tests, **exactly one** flips with the change and five are guards that pass either way.

Then it was measured on the corpus: **0 of 440 askings moved.** Coverage 23.06% → 23.06%. Not "small" —
zero. On the shipped organ there are now **0 call-shape refusals left to answer.** The alias exemption had
already answered every one this corpus contains.

A change that measures zero on the only corpus that prices it is a **claim, not a result**. It was
withdrawn rather than merged with a promise attached. Its record is kept here so it is not rebuilt:
`canonical/verification/A_USE_THE_EXAMPLES_DID_NOT_SHOW_SHOWN_BY_THE_FILE_20261112_V1.json`, and the tests it
was proved with are described in §2 above.

## 3. Attribution: where the 7 points between 16% and 23% came from

Not from this round. From the alias exemption already on main:

| | before | after | wrong |
|---|---|---|---|
| coverage | 16.01% | 23.06% | 14 → 14 |
| precision | 92.41% | 94.61% | |

Attributable, not a mixture: the gain is the call-shape class exactly, and `NO_FORM_IN_FILE` does not move.
**That is what a real generalization gain looks like** — precision goes *up*, wrong changes stay flat.
It is also the last one available at this granularity, because the class is now empty.

## 4. Where Problem 2 actually is now

The corpus has stopped being the constraint. Three facts say where it went:

1. **The ceiling is closed.** 23.06 of 23.48 available. Further coverage costs a second demonstration
   (about **+8 pp**, then it saturates) or a check of the project — a different arm, not a better fit.
2. **Half the pull requests return nothing, and four hold 370 of the 1,674 changes.** The headline is a
   mixture of "the demonstration was excellent" and "the demonstration was of a change that does not
   repeat". `inveniosoftware/invenio-pidstore#189` alone carries 115 changes the organ cannot reach. That is
   not a defect; it is what a repeated change looks like in the wild.
3. **The biggest refusal class is not an algebra failure.** 168 of 440 (38.2%) say *nothing in the file has
   the form the example changed*. There is no such code. Nothing can generalise to it, by any method.

So the next real lever is **not** another widening of the algebra. It is the two things the record names and
nobody has used yet:

- **The divide inside a pull request.** When a demonstration repeats in 5 of 6 files and not in the sixth,
  the developers are *telling* the organ where the change applies. That is free applicability evidence and
  it is untouched.
- **Cross-file witnesses.** The withdrawn widening read one file. The same evidence one file over is
  unmeasured, and it is the only evidence-shaped headroom left.

## 5. What not to do (each already priced)

- Do not chase the 0.42 pp to the ceiling. It is guessing, and it makes nothing more right.
- Do not widen the vocabulary. 38% of refusals are code that is not in the file.
- Do not chase the zero kinds (six removal, f-strings) with this organ: their demonstrations do not repeat
  by construction.
- Do not rebuild the file witness without a corpus where it can be priced. It is sound and it is worthless
  here, and the difference between those two is exactly what the record is for.

## 6. The answers to the questions asked

**"We solved instant learning perfectly — doesn't that solve everything?"** No. Problem 1 is memory;
Problem 2 is inference. A cache answers the first and is silent on the second. Retention is not transfer.

**"Can't we give it the smartest actions once and let it learn them?"** It already does, and the ceiling is
measured: one demonstration, permanently kept, priced at 98.2% of its own maximum. The limit is that one
demonstration does not *identify* a rule — 0/10 targets from one example, 10/10 from one example plus **two
chosen questions** — and a success teaches applicability almost nothing (0/200), while chosen failures teach
it fast (25/25 in 2.76 demonstrations). **Exposure informs; refutation identifies.**

**"Is this a revolutionary way to make agents learn faster?"** Yes, for one reason that is worth more than
speed: **the unit of learning is a checked change rather than a gradient**, so everything learnt is
verifiable, free to keep, and impossible to catastrophically forget. That is a real advantage in cost and
trustworthiness. It is not an advantage in *reach*.

**"What is real and what is not?"** Real: 23.06% at 94.61% precision, permanently, for $0, with zero model
calls, at 98.2% of its own ceiling. Not real: that the remaining gap is a fitting problem, or that more
exposure closes it.

Authority **NONE**. Cost **$0**. Model calls **0**. `truth.achieved` **false**. No capability registered,
no guard weakened, and one law *enforced* at the cost of a better-looking number.
