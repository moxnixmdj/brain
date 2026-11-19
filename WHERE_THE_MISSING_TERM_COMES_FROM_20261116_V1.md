# The vocabulary was already at the site

*2026-11-16. Producer-run, 87 real fixes, 0 model calls, 0 parameters, no network, no execution.*

## The correction

Nine rounds said the bottleneck was **generation of structure**: the missing statement is never shown in that
position, so nothing that selects from what the machine displays can reach it. That is still true as a statement about
*selection*. This round shows it is the wrong name for the obstruction.

The missing term was never checked for whether it is **sayable** — whether every word it needs is already available
where the failure happens. It usually is.

## Measured (symbolic, on the pre-fix file alone)

For each of the 87 fixes: the post-fix lines that were added, the outermost expressions lying inside them (the terms
the fix had to produce), and every identifier those terms need — classified against the **pre-fix** file, with names
the fix itself binds excluded, because a temp is alpha-renamable and is not vocabulary.

| where the term's words come from | fixes | share |
|---|---|---|
| **in scope at the site** — a composition of names already available there | **47** | **54.0%** |
| in the file but not in scope — computable, but needs a value threaded, not a term | **15** | **17.2%** |
| not in the file at all — must be imported or defined | **24** | **27.6%** |
| literals only — the constant itself is the thing to invent | **1** | **1.1%** |

**72.4% of real fixes need no word that the file does not already give them, in scope, where they are needed.**
And the terms are built from a basis of **11 operators covering 90%** of all operator occurrences (17 distinct):
`Eq, Not, And, BitOr, Or, Is, IsNot, In, NotIn, USub` and one more. The terms are small: depth 2–7, median 4.

Examples of what had to be produced, none of them present anywhere in that position before:
`token is None or not token.text`, `suffixed_err(src, new_pos, f'Expected {expect!r}')`,
`re.compile('(\\d+)(.*)\\Z', re.ASCII)`, `not ref.isascii()`.

## What this means

The vocabulary-insufficiency objection **does not bind as the main obstruction**. In 72% of cases the words are at the
site. The operator basis is tiny and is exactly what instant learning establishes with zero parameters. So the missing
term is **expressible from what is already in scope, in a small language**.

What is missing is not vocabulary and not expressiveness. It is **the choice**: which composition of available names
and eleven operators is the one the failure wants. That is identifiability — one trace fitting exponentially many
hypotheses — not insufficiency. The binding object is a **pruner**: something that can reject a candidate term before
it is executed, because a test run is expensive and the test's verdict arrives once, at the end.

And that is precisely why computer use behaves differently from code repair, from first principles: in computer use the
environment **displays the state after every action**, so the pruner is free, dense and per-step — a plan is *solved*
one action at a time and each choice is checked by the next observation. In code repair the pruner is one distant bit,
so the choice must be made **unexecuted**, which is only possible with a computed structure — types, effects, and the
site's own invariants.

**The bottleneck, final form: a computed pruner over a finite term language at the site.** Not a generator of new
words (the words are there), not a bigger action list (actions were never the constraint), not parameters (nothing here
needs a stored fact).

## What is real in "learn each action once and everything on a computer is solved"

Real: operators, their effects, and their composition are identified exactly from one observable trace —
refusal surface 160/160, provenance 24/24 — and an operator basis of 11 covers 90% of the terms missing from real
fixes. A whole agent's worth of computer use, permanently, zero parameters. That half of the claim stands.

Not real: the leap from *having the actions* to *producing the right composition*. The actions are the cheap part; they
were never the constraint. What costs is choosing among compositions when the only feedback is one distant bit.

## Bounds on this claim (stated so it cannot be over-read)

- This is a **structural** result. No repair was executed on these 87 this round; it does not claim 54% of fixes are
  now repairable, only that 54% *need no word that is not already in scope*.
- "In scope" is computed generously in ways that could only **over-credit** term-locality, so 54.0% is an upper bound
  and 27.6% is a lower bound on how much must come from outside the file.
- The 24 out-of-file fixes are not split between "import a symbol that exists elsewhere" (knowledge, which instant
  knowledge supplies) and "define a helper the fix creates" (new code, which does not). That split is the next
  measurement, and until it exists neither side of it may be claimed.
- A temp introduced by a fix would have inflated the knowledge share; the instrument excludes names the fix binds. That
  exclusion was added after the first run, which reported 44.8% instead of 27.6% — the difference was almost entirely
  `i`, `p`, `s`, `msg`, `inner`.

Receipt: `canonical/verification/WHERE_THE_MISSING_TERM_COMES_FROM_20261116_V1.json`. Instrument:
`canonical/tools/where_the_missing_term_comes_from_v1.py`.
