# The goal picks the door

**Round 4 verdict. Branch `arena/1b6969f0-brain`, base `5abc439a`.**

Round 3 ended with an honest number and an honest wall: **76 doors discovered, and no way to
choose among them.** The census answered *what can be done here*; nothing answered *which of
these does what I was asked*. This round joins them, and the join took three designs because
the first two were measured and found wrong.

---

## 1. The requirements this had to meet

Unchanged and binding: own model only, **zero model calls**, **zero knowledge house**,
knowledge outside the weights, single-experience learning in unseen environments, insanely
fast, best-part-is-no-part, honesty separating verified from unverified.

The user's question, in their terms, was: *should he be goal-directed and save only the
important learning? Because saving his exact experience is dumb — environments always
change. Do generalization.*

That is not a preference. It is a **testable requirement**: a saved row must be worth
something in an environment that shares nothing with the one it was measured in. This round
measures exactly that.

## 2. The wall, stated precisely

A goal arrives as a request. A door is a measured effect. The two were recorded in different
vocabularies, and the census's own record of a door was too coarse to serve a request:

| | round 3's record | what a request needs |
|---|---|---|
| goal | — | a demanded change |
| door | `CREATES`, `RENAMES`, `REWRITES`, `DELETES` | which relation moved, and which way |

Nothing could match across that gap, so the machinery that already existed —
`perfect_algorithm_v1.plan()`, `environment_learning_v1.shortest_plan()` — could not be
pointed at a request. They search for a **goal state that has already been observed**. Neither
can take a request that names a change.

## 3. Three designs, two of them wrong

### Design 1 — per-content conditions. Measured, failed.

A goal was a condition on a content (ABSENT / PRESENT / SAME / DIFFERENT); a door was the
set of conditions it moved. Precision, leave-one-out over 62 real rows: **0.4677**. Held-out
program (`mv`): **0.0**.

The diagnosis was not tuning. **A content-level condition is the wrong unit.** Thirty-three
gzip requests produced thirty-three different contents, so the predictor had nothing to carry
across requests and its "choice" was a sort by name.

### Design 2 — the project's five relations. Measured, failed.

The project already owns a better vocabulary and has measured A1–A5 on it. A door's effect is
*which of the five relations moved*, which is a property of the kind of move and not of the
files it touched. That is the right idea.

Measured on the same rows: **the five relations collapse the entire surface into 3 classes.**
The reason is structural — all five are **commutative**. Each is a function of a *set* of
`(name, content)` pairs, so `mv a b` and `rm a` read identically: both remove a name. A
vocabulary that cannot see the difference cannot be used to choose between them.

### Design 3 — the five relations plus one relation about the *step*. Measured, kept.

The missing relation is not a sixth observable. It is a question the project could always
have asked and did not, because `effect()` compares two states for equality and throws away
which one came first:

> **`LOT`** — after this step, can every content that was readable before still be recovered?

`mv a b` retains. `rm a` loses. `gzip a` **retains, one layer down, inside `a.gz`**. Three
programs, one question, no tool name anywhere in it.

Adding it gives **5 distinct moves** instead of 3, and it separates the case `CARD` cannot see
at all: compressing one file and renaming one file both leave the count unchanged.

## 4. What is saved, and why it is generalization

The saved row is:

```
(tool, relation signature, artifact span)
```

It contains **no path, no argv, no content, and no example.** That is the answer to "what
should he save", and it is not a slogan — it is checked:

- **Stability across worlds.** Every door was run in **three unrelated worlds** — different
  filenames, different contents, different sizes. **18 of 18** doors reported an *identical*
  signature in all three.
- **Transfer across programs.** Each program's requests were answered with that program's rows
  **removed**. `cp` 3/3, `mv` 3/3, `rm` 21/21, `gzip` 33/33 — **60 of 60**, from other
  programs' measurements alone.
- **Leave-one-out.** **61 of 62**, so a door never vouches for itself.

### The control that keeps that honest

An answer rate of 1.0 on its own means nothing, and reporting it alone would be the kind of
number this project exists to refuse. So the join reports **coverage** — how many candidates
each answer was chosen from:

| program | requests | answered | mean candidates matched | of |
|---|---|---|---|---|
| `rm` | 21 | 21 | **3.0** | 47 |
| `cp` | 3 | 3 | 7.0 | 59 |
| `gzip` | 33 | 33 | 23.4 | 29 |
| `mv` | 3 | 3 | **59.0** | 59 |

`rm`'s answer is discriminating: 3 of 47. `mv`'s is **not** — its move was matched by every
candidate, so the join's answer there carries no information. Both are in the receipt.
`selectivity()` returns `UNINFORMATIVE__EVERY_DOOR_MATCHES` rather than a success.

## 5. What is refused, by name

- **A goal about meaning.** "Is this a valid PNG", "is this text French", "is this archive
  intact" are not functions of the five relations' structure. `choose()` returns
  **`UNSTATEABLE`** and says which vocabulary would be needed. It does not rank doors by a
  guess.
- **A malformed direction.** A relation with a value the vocabulary never produces is refused,
  not ranked.

This is the honest boundary of the whole design: it reads **structure**, not **meaning**.

## 6. Defects found this round

Each was caught by disbelieving a number, and each is recorded because the test that covers it
names the reason.

1. **A parser that read bracketed words instead of operands.** `cp --help` says
   `Usage: cp [OPTION]... [-T] SOURCE DEST`; the parser returned `['OPTION', '-T']` and bound
   *one* filename to a command needing two. **33 of 33 cp and 14 of 14 mv operations came back
   inert**, so their real doors were invisible. The operand slots are the *unbracketed* words.
2. **The program's own name counted as an operand**, making cp look like it declared three
   slots.
3. **A second operand supplied eagerly.** Appending two operands to every operation took
   **git from 42 doors to 7** with 57 litter, because a failed `git commit tree ref in.txt
   out.bin` still writes a tree. The second operand is now supplied **only when the
   one-operand form did nothing** — the exact condition `cp --force in.txt` is in and
   `git mv --force in.txt` is not.
4. **`git`'s wrapped usage line read as eleven slots.** Reading the continuation made every
   git subcommand look like it wanted two operands. Reverted: the first line is the
   declaration.
5. **`stateable()` checked against a tuple that omitted `LOT`.** Every goal mentioning
   retention was refused as `UNSTATEABLE`: `rm` answered **0 of 21** while `cp` answered all of
   its own. It read exactly like a finding and was a bug.
6. **`LOT` computed from already-normalised state.** The tuples had turned every binary into a
   digest, so a compressed file could no longer be opened to see what it held, and a
   compression reported **`LOST`** — the precise confusion between "the name is gone" and "the
   bytes are gone" that the relation exists to prevent.
7. **Bytes decoded with `errors="replace"`.** A gzip stream and any other binary both became a
   run of `U+FFFD`, so losing one looked like losing nothing.
8. **A control sharing the subject's content.** The first fixture seeded the same content
   twice, plain and gzipped, so destroying the plain copy looked like destroying nothing.
9. **Two record fields named `argv`** (round 3's follow-up): the declaration-floor instrument
   reads any dict with `argv` as a *verification predicate*, so 28 census observations became
   28 empty declarations and moved the floor from 595 to 623. Now `invoked_as`.

## 7. Measurements

- **62 measured rows**: 54 census door rows (4 programs × 3 worlds) + 8 project-machine atoms.
- **5 distinct moves** among them.
- **18/18** doors with an identical signature across three unrelated worlds.
- **60/60** held-out requests answered from other programs; **61/62** leave-one-out.
- **1.8 s**, 0 model calls, 0 parameters, 0 network calls.
- Tests: **15 new**, and **111 passed, 2 skipped** across the relevant surface.

## 8. Limits (all of them real)

- **The vocabulary is coarse.** Five moves describe *whether* something was added, removed,
  renamed, rewritten or destroyed — not what happened to the bytes. Two doors that both
  "rewrite" are one move here.
- **`mv`'s answer is uninformative** in this sample, and the control says so.
- **Semantic goals are out of reach** by construction, not by oversight.
- **`git`'s door count varies between identical runs**: measured 42, 40, 42 across three runs
  of the same code. This is **pre-existing in round 3**, not introduced here, and it is why
  git's fleet total is reported as a range rather than a point.
- **Producer-run sandbox only.** No independent identity re-ran any of it. `truth.achieved`
  stays **false**.

## 9. The next wall

The join answers **which door** for **one** move. A goal that needs **several** moves in order
is not yet answered, and the pieces to answer it exist and are unjoined: `plan()` searches a
learned model for a shortest path, and the census's environment now carries a signature per
transition. A goal stated as a conjunction of moves, planned over signatures rather than over
whole states, is the next bottleneck — and it is where the project's `shortest_plan()` stops
being a lookup and becomes a search over *kinds of change*.
