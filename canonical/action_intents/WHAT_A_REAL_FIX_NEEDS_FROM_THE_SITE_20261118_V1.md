# What a real fix needs from the site

*241 real single-line edits, four real projects. 48.6% need only what is already there. 0.4% need a
name the site does not have.*

## Why this measurement exists

Every claim in this tree so far rests on a corpus of 40 known bugs. That is self-congratulation, and
the number that decides whether the whole family is worth anything had never been measured: **of the
fixes real people actually wrote, what fraction could a site's own material build?**

The last build showed expressiveness to be the first obstacle, ahead of evidence and memory. This
measures it on real code.

Population: every commit in four real projects (`requests`, `click`, `tqdm`, `httpx`) whose entire
diff for one Python file is **one removed line and one added line**. That is exactly the population a
single-site expression replacement can address, so it is the population the question is about -- no
hand-picked bugs, no benchmark harness, no model, no network at run time.

For each, the AST diff of the parent line and the child line, the deepest change point, and whether
every free name of the new expression is already in scope at that site in the parent version.

## The numbers

| verdict | count | rate |
|---------|------:|-----:|
| `IN_VOCABULARY` -- names in scope, within node budget | **117** | **48.6%** |
| `NOT_SINGLE_EXPRESSION` -- docstring/comment (80) or a structural change (38) | 118 | 49.0% |
| `TOO_LARGE` -- beyond the enumerator's node budget | 5 | 2.1% |
| `NEEDS_NEW_NAME` -- uses something the site does not have | **1** | **0.4%** |

Of single-line edits that are *code* at all (excluding the 80 lines that do not parse), the
in-vocabulary rate is **72.7%**.

## What this says, and it contradicts the plan the project has been following

**Vocabulary insufficiency is essentially absent.** One edit in 241 had a free name the site did not
have (`len` → `length_hint`). Every plan to grow the vocabulary -- more builtins, more atoms, more
learned actions, more names in scope -- is aimed at **0.4%** of the population.

**The insufficiency is SHAPE.** Half of real single-line edits are not a single expression
replacement: they change a docstring, a comment, a signature, a statement's structure. Another 2.1%
are expressions too large to enumerate. That is **51.4%** of the population, and it is where the
capability actually is.

So the decomposition of the single bottleneck, now measured rather than argued:

> **1. Form: can the edit be expressed at this site at all (49.4% of real single-line edits say no).**
> **2. Evidence: does the next observation separate the surviving candidates (previous build: 1–4
> chosen queries).**
> **3. Vocabulary: 0.4%. It is not the bottleneck and has not been for some time.**

## The defect this measurement had, and how it was caught

The first run classified **100%** of 242 real edits as `NOT_SINGLE_EXPRESSION`. That is the third time
in this project a 100% result was the instrument and not the world: the AST comparison picked the
*shallowest* differing node -- always the module, since every ancestor of an edit differs too -- and
read that as "not an expression". Fixed to the deepest change point; the distribution above is after
the fix. The test file pins this exact regression.

## What to build next, given this

1. **Statement-level and structural repair, not expression-level.** Half the population. A site's
   *form* (its statement shape, its guard structure, its signature) is what real fixes change most.
2. **Multi-site edits.** 38 of the structural changes are decomposable into one edit per site; the
   machinery already exists for one site and needs the joint search the earlier build refused.
3. **The node budget.** 5 of 241 fixes exceed it; the budget is a search parameter, not a law.
4. **Nothing about vocabulary.** Adding atoms cannot move a number that is 0.4%.

## Ship list

- `canonical/tools/what_a_real_fix_needs_from_the_site_v1.py` -- streams real git history, extracts
  single-line edits, diffs their ASTs at the deepest change point, and classifies what the fix needed.
- `canonical/verification/WHAT_A_REAL_FIX_NEEDS_FROM_THE_SITE_20261118_V1.json` -- every number, the
  population, the caveat that `IN_VOCABULARY` is a *necessary* condition, and the examples.
- Tests pinning the deepest-change-point regression and the scope computation.
