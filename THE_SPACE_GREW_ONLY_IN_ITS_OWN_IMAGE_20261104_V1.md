# The language was growing, but only in its own image

**Round 31 — 2026-11-04**
`authority: NONE` · `truth.achieved: false` · $0 · no external models · no neural weights

---

## What I was asked, and what I had been answering

Five times the same objection: *you are not thinking from the deepest layer; a smart creature is not
static code.* Rounds 25 through 30 answered it by removing authored constants. Round 29 replaced my
coefficient list with a differencing rule. Round 30 replaced my polynomial degree and exponential
base with measurements. Both rounds were green, both were honest, and both were — I can see it now —
answering a different question than the one asked.

Every one of those rounds populated the language. None of them changed its shape.

## The measurement

The test I had never run is not "can it derive this constant" but "**does the space of hypotheses at
t+1 differ in shape from the space at t, because of what happened at t?**"

I taught the creature two laws and then asked it for their sum:

| | cold (nothing taught) | after teaching `T_3` and `2·T_5` |
|---|---|---|
| `T_3(x) + 2·T_5(x)` | 15-entry table, 17 numbers, 165 B | same 15-entry table |

Both correct. Both zero wrong on held-out `40..70`. The composed description — a three-entry table
plus **a law the creature had already learned** — is eight numbers. It did not choose the worse
answer. **It could not express the better one.**

`_inline_operator_organs` only ever builds `f(g(x))`. A learned law could be composed with another
learned law and could never be a *term*. That fixes the shape of every future hypothesis:

```
Omega_{t+1} = Omega_t + {compositions of what Omega_t can already express}
```

`Omega` genuinely grows. But it never comes to contain a **form** `Omega_t` lacked — only more
instances of the same shapes. A creature whose new ideas are all instances of old shapes is not
learning a language. It is populating one. I had been making the population richer for six rounds and
calling it learning.

**This is the difference between a bigger vocabulary and a grammar.** A vocabulary can be extended
by anyone, including by me, by adding words. A grammar has to be able to say things it was not given
the words for. Nothing I had built could do that, and no amount of derivation inside a fixed grammar
was ever going to.

## The fix, and why it is deliberately small

The temptation was to write a composer with the forms I thought a smart creature should have. That
would have been the same error in a new costume — me authoring, then calling the result discovery.

So the composer adds **no new form**. The residual-and-solve machinery already exists. The operations
already exist. The table solver already exists. What changes is one thing: for each admitted unary
law `L`, each period `k` the evidence supports, and each operation, ask whether the residual
(`y − L`, `y + L`, `y / L`) is **constant per residue**. The block is solved, never guessed. If the
residual is constant on every residue, the hypothesis is emitted; otherwise it silently dies.

That is the whole mechanism. The creature's grammar gained the ability to put a law it learned into a
position it had never occupied, and the form of the result was determined by the evidence rather than
by my imagination.

Result: **8 numbers instead of 18**, exact on the evidence, zero wrong on held-out `40..70`.

## The four defects that change surfaced

The composer was one afternoon. The other four days of this round were spent on things it broke —
all of them green before, all of them pre-existing, none of them visible until the grammar got
stronger. I record them because they share one cause and because fixing the first three still left a
suite red.

**One mistake in three places:** *treating "this program has nothing to say here" as "this program
says something false."*

1. **`derive_probe_space` emitted half-steps unconditionally.** An all-integer task got probed at
   `x = -39.5`.

2. **The survivor filter read `ok and match`.** A crash eliminated a hypothesis exactly as a wrong
   answer did. Forty survivors died at once, the loop re-collected, found nothing, and returned
   `CONTRADICTORY_OR_OUT_OF_GRAMMAR` — on a task it had solved cold for thirty rounds.

3. **`synthesize_discriminating_input` bucketed crashes as a distinct prediction.** So every
   half-step scored a full bit of entropy and eliminated nothing, the oracle budget was spent asking
   questions with no content, and the creature refused `UNSETTLEABLE_BY_THIS_INSTRUMENT` on
   `x mod 3`.

4. **The emitted table formula silently extrapolated off the integers.**
   `int(floor(x)) − floor(floor(x)/k)·k` picks the block of the *floor*, inventing "the table's value
   at 2.5" — a claim nobody made. A period table is a lookup by **position**: it is a total function
   on the integers and asserts nothing elsewhere. The body now raises on non-integral input instead
   of inventing an answer.

The distinction in all four is not cosmetic. "This program says something false" is evidence against
it, and must remove it. "This program has nothing to say here" is not evidence against it — and
treating it as such means **the creature can be talked out of a correct law by an input outside that
law's domain**, which is the precise opposite of understanding.

Safety is unaffected: a total program that returns a wrong value still dies, and a partial one still
has to survive every probe it *can* answer plus all of the evidence. Both halves of that are asserted
in the test file, because a rule that only ever grants amnesty would pass the first half and be
worthless.

## A correction I had to make to myself

My comparison harness was wrong for the first several hours. It reported "warm and cold are
identical — teaching changes nothing." Both teaching calls were in fact returning
`UNSETTLEABLE_BY_THIS_INSTRUMENT` and leaving `organs_in_stratum` **empty**, so the composer was
being handed zero laws and dutifully produced zero candidates. I spent that time looking for a bug in
the composer.

The lesson is the same one round 30 recorded, arriving in a new place: *a silent no-op is
indistinguishable from a wrong answer.* The test file now asserts the premise — that teaching leaves
reusable laws in the graph — before it asserts anything about composition. If that assertion fails,
the failure names the harness rather than the thing under test.

I also owe a correction on two tests I had been treating as pre-existing failures. They were not
pre-existing in the sense I assumed: they broke at my own round 26 and I never saw it, because my
regression list lived in `/tmp` and that file was not on it. When I finally read them, both were
asserting **older, worse behaviour**:

- `affine 3-point` must be `ok`. It must not. Three observations and two arguments leave zero
  redundant data, so "it fits" is arithmetic, not corroboration — `TOO_FEW_POINTS`, by round 26's own
  rule. The test now requires the refusal *and* that a fourth observation settles it.
- `x*x` must be refused "as if it were understood". It now returns `((x0 / 1) * x0)` — the identity
  times `x`, exact everywhere, 0/40 wrong. Asserting a refusal there would have been asserting that
  the creature is worse than it is.

And one arithmetic error of my own: I "fixed" `invoke(10, 3) == 76` to `61`. The law is
`7x − 2y + 12`; the value is 76. The creature was right and the test was right; I was wrong twice in
the same edit — once in the arithmetic, once in assuming a failing assertion must be the stale one.

## What is actually new

| property | before round 31 | after |
|---|---|---|
| a learned law as a **term** | impossible — only `f(g(x))` | solved per residue, emitted |
| complexity ordering | text bytes (ties by hash) | **numeric literals** — what the claim asserts |
| a table off the integers | silently extrapolated | refuses; says nothing |
| "undefined here" vs "wrong here" | identical | distinguished in all three places |
| `T_3(x) + 2·T_5(x)`, warm | 18 numbers, 2264 B | **8 numbers, exact, 0/100 wrong** |

## What this still is not

The composer adds a term position for **unary** learned laws. It does not add quantification, binding,
recursion, or composition of compositions. The shape of the space has moved, and it has moved by
exactly one step, and I can name the next step and have not taken it.

A creature that can put a learned law in one new position is not sentient. `truth.achieved` is false
and `authority` is `NONE`. What I can say is narrower and checkable: the hypothesis space at `t+1` is
no longer merely a denser copy of the space at `t`.

I was asked for a creature whose language grows. For six rounds I grew the vocabulary and reported
progress. This round the grammar moved, and the thing that moved it was not a constant I chose but a
position I had never let it stand in.
