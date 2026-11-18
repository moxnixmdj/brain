# The shape obstacle was a parsing artifact

*Correction of the previous build. Of real single-line **code** edits, 81.3% need only a single
in-vocabulary expression and 86.1% are addressable by the machinery that already exists. Statement-form
repairs are 8.7%, not 51.4%.*

## What was published, and what was wrong with it

The previous build measured 241 real single-line edits from four real projects and concluded:

> "The insufficiency is SHAPE: half of real single-line edits are not a single expression replacement
> — 51.4% — and that is where the capability is. Next: statement-level repair."

That conclusion was the instrument. Decomposing the 118 edits it called "not a single expression":

| what they actually were | count |
|-------------------------|------:|
| a comment or a docstring — not code at all | 26 |
| **code split across lines**, invisible to a line-pair diff | **71** |
| a genuine statement-form change | 13 |
| other | 8 |

A line-pair diff cannot see code that spans lines. My classifier treated a `SyntaxError` on a single
line as *"this is not an expression change"* when the truth was *"this instrument cannot see this
edit."* Resolving those cases at statement level — parse both files, find the innermost statement
spanning the changed line in the parent, look up the same structural path in the child, diff the two
statements — removes the artifact.

## The corrected numbers (241 real single-line edits, `requests`, `click`, `tqdm`, `httpx`)

| verdict | count | of all | of code edits (208) |
|---------|------:|-------:|--------------------:|
| Single expression, in vocabulary | **169** | 70.1% | **81.3%** |
| Two expressions, jointly addressable | 10 | 4.2% | **4.8%** |
| Statement form (not an expression) | 18 | 7.5% | 8.7% |
| Too large for the node budget | 9 | 3.7% | 4.3% |
| Needs a name the site does not have | **1** | 0.4% | 0.5% |
| Not code (comment/docstring) | 33 | 13.7% | — |
| Unresolved continuation | 1 | 0.4% | 0.5% |

**86.1% of real single-line code edits are addressable by the repair form this project already has**
— one or two expressions over names already in scope, within the node budget (a necessary condition,
not a proof of generation).

## Why this matters more than the number

The previous conclusion would have sent the next build at **7.5%** of the population — statement-form
repair — while the actual obstacle was already measured and left unaddressed: **identification**. The
project would have spent its next cycle building the wrong organ, for the third time, on the strength
of a confident measurement.

The corrected decomposition of the single bottleneck:

> **1. Evidence, not expressiveness.** 86.1% of real single-line code edits are in the vocabulary and
> shape of the existing machinery. What is missing is the observations that separate the candidates —
> the previous build's 1–4 chosen queries.
> **2. Vocabulary: 0.5%. Statement form: 8.7%. Node budget: 4.3%.** All three are small and closed to
> further work until the first one is done.

## The three instrument defects in this series, and the pattern

1. **Shallowest instead of deepest AST change point** — reported 100% `NOT_SINGLE_EXPRESSION`.
2. **Ancestors counted as independent change points** — reported every edit as two or more changes.
3. **Line-pair diffing** — reported 51.4% "shape" where the truth is 7.5%.

Each produced a confident, publishable, wrong number. Each was caught by looking at *examples of the
verdict*, not at the totals. The rule this leaves behind: **a new instrument must print its verdicts
next to the inputs that produced them, before any total is quoted.** Totals hide generators.

## What is real, after the correction

- Real code is overwhelmingly *single-expression* work at the line level (81.3%), and that is the
  repair form already built here.
- The scarcity is **evidence per task**: how many observations a task gives you, and whether you
  choose them. That is the previous build's result (1–4 chosen queries, verified held out) and it is
  the only place worth building next.
- Nothing about new vocabulary. Nothing about statement-level synthesis yet — 8.7% does not justify a
  synthesizer before the 86.1% is actually solved on real repositories.

## Ship list

- `canonical/tools/what_a_real_fix_needs_from_the_site_v1.py` — now resolves edits at statement level
  and reports the classes a repair form can act on.
- `canonical/verification/THE_SHAPE_OBSTACLE_WAS_A_PARSING_ARTIFACT_20261118_V1.json` — the correction,
  the corrected table, and the three defects.
- A correction notice on the previous document, because a wrong claim that stays in the tree is worse
  than one that was never made.
