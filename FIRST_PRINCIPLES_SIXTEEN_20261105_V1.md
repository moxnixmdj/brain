# First principles, pass sixteen — the deepest layer was that I was the only thing learning

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. The question, answered against myself

> *"You sure this is the smartest approach? Think from the deepest layer, from first principles."*

**No.** And the reason is visible in one command:

| module (built in passes 12-15) | authored knowledge |
|---|---|
| `operator_family_rewrite_v1` | operator family table |
| `binding_repair_v1` | "NameError → near-neighbour substitution" |
| `signature_repair_v1` | two arity regexes |
| `syntax_repair_v1` | five syntax patterns |
| `derived_edit_classes_v1` | **none — it derives. Not wired in.** |

Four passes, four hand-written tables. Every capability gain was knowledge **I** had, encoded by me,
verified by a screen I also wrote. The creature executed. It did not learn. I was the only thing in
the system that got better over time, and I mistook my own improvement for its improvement.

And the one mechanism that *derives* its knowledge had been sitting validated-but-unused since pass
eleven, with its limitation written down in its own docstring and then walked past.

## 2. What was actually missing: time

Everything about a repair was correct except what happened to it afterwards. The loop already handed
`(before_snippet, after_snippet)` of every verified repair to a durable skill store — so the *evidence*
was already being saved. Nothing turned the evidence into a **habit**, and nothing reloaded it. The
creature had memory of instances and no memory of **rules**.

The fix is small and the placement is the point:

- **observe** on every crystallized repair — free, because the pair is already in hand
- **persist** to a JSON file beside the skill store — so a process boundary is not an amnesia boundary
- **propose** into the live candidate list — as one more producer, screened like all the others

## 3. The measurement

Fresh process per row. Every authored producer silenced, so only habits can act:

| generation | habits held | target world (`* -> +`) |
|---|---|---|
| 0 | none | **FAILED** |
| 2 | `- -> +` | FAILED |
| 3 | `- -> +`, `+ -> *` (closure infers `- -> *`) | FAILED |
| 4 | `- -> +`, `+ -> *`, `* -> +` | **SOLVED** |

And habits-only coverage on four held-out worlds: **3/4**, one of them solved by an *inferred*
substitution (`- -> *`) that the creature never performed.

This is the first time in this whole effort that the system satisfies the owner's standing bar in the
sense the owner means it: **it is different at the end of a run than at the start, and the difference
is in the system rather than in its author.**

## 4. The limits, which are the honest half

- **One habit does not generalise.** Generation 2 held `- -> +` and still failed a `* -> +` world. The
  class is closed: the creature knows only what it has seen, plus what composition gives it. That is
  correct behaviour, not a shortfall to be papered over.
- **A cold creature repairs nothing.** With no habits and authored producers silenced, generation 0
  scores zero. Every lift starts from my tables. The honest sentence is: *the authored tables are
  what make generation 0 work at all; habits are what stop generation 4 from having to be generation
  0 again.* Deleting the tables today would not produce a smarter creature, it would produce a
  creature that cannot start.
- **Habits are operator-token substitutions.** They carry no structure, no guards, no ordering. The
  abstraction step is real but narrow.

## 5. What this reframes about the last four passes

Passes twelve to fifteen were not wasted — the screen repairs (reason channel, truncated text,
symlink) were genuine and they are what make the evidence trustworthy enough to learn from. But their
**capability** contribution was authored. Had I asked "what will the creature know at the end of this
run that it did not know at the start" in pass twelve, I would have answered "nothing", and that
answer should have redirected the work four passes earlier.

The question the owner asked six times in different words is answerable and I had not been answering
it: *not* "does it repair more worlds" but "does anything inside it get better that will still be
better tomorrow".

## 6. Next falsifier

**S12.** Seed habits ONLY from verified repairs the creature earns *during* a run (not from pairs I
hand it), on a curriculum of operator worlds, then measure a held-out operator world in a later
process. Prediction to falsify: **the earned-habit path produces nothing**, because a cold creature
repairs nothing and so earns no habits — which would mean the bootstrap has to come from the authored
tables forever and the mechanism is decorative. If it does produce lift, the mechanism is real and the
tables can start retiring one shape at a time.

## 7. Standing bar

Different at the end than at the start: **yes, and for the first time the difference is not mine.** A
habit earned in one process changed a verdict in another. That is one narrow mechanism on a board of
twelve shapes, and it is the only thing in sixteen passes that is true in the sense the owner has been
asking for all along.
