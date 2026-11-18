# The term that learning multiplies: why instant learning does not solve all computer use

You asked a question with a shape: *we solved instant learning and instant learning in a new environment, so
give the model the most advanced coding actions, let it experience each once, it learns them permanently, and
we have solved every problem and all computer use. Is that true?*

It is **true as a cost law and false as a coverage law** — and this round found the exact term it multiplies,
measured it on real code, and refused to believe its own first number because that number was an artefact.

## The honest answer in one line

You cannot learn against nothing, verify what nobody specified, or synthesise towards a target that has not
been stated. Learning multiplies **checkability**, and checkability is knowledge. That is the bottleneck.

```
P(solved | work) = CHECKABLE(work) × [ MEMORISABLE + IN-GRAMMAR + SYNTHESISABLE ] × VERIFICATION
```

Every term except checkability has been driven high in this tree. `MEMORISABLE` is 4.814% of real fixes.
`IN-GRAMMAR + SYNTHESISABLE` covers the work that has a mechanical postcondition. `VERIFICATION` is exact.
Experience enlarges only `MEMORISABLE` — the smallest term in the product.

## What we built this round

A **constructor** (`canonical/swe_kernel/checkability_by_differential_pin_v1.py`) that asks the only question
left standing after last round's refusals: *of the real work that ships no tests at all, how much already has
a postcondition that can be built without the author's tests, without the author's intent and without a
model?*

It takes a real commit's touched modules at both the parent and the fixed state, drives every public callable
the module itself defines through an alphabet of empty-ish values **plus the string literals the module itself
contains**, and keeps a difference only if it is stable inside one interpreter, with object identity removed
and iterators consumed so the *yielded* behaviour is compared.

### The result, on real commits

| | |
|---|---|
| real commits, both states materialised (`git archive`, pinned releases) | **40** |
| shipped their own tests — work that arrives with a specification | 21 |
| shipped none — work with no mechanical postcondition of its own | **19** |
| drivable through the module's own public surface | 13 |
| converted into a stable differential pin | **0** |
| unguarded states | `NO_DIFFERENCE_VISIBLE_FROM_THE_PUBLIC_SURFACE` 13, `NOTHING_PROBEABLE` 6 |

**0 of 13.** And the second specification source was tried and refused by measurement: **the artifact's own
doctests discriminate 0 times**, because a doctest lives in the same file as the code, so the author of a
change updates it in the same commit and it passes at *both* states. It looks like an independent
specification and is not one.

### The number I had to destroy

The first run reported **21.1% converted — 4 of 19**. Every one of those "pins" differed only by a generator's
memory address (`<generator object platform_tags at 0x7f…>`). After removing identity from the comparison and
consuming iterators, the answer is 0. Both numbers are in the receipt: the 21.1% because it was measured, and
its refutation because it was an artefact. This is the mistake that would have made this round worthless, and
the instrument is what caught it. The instrument itself is proven in `canonical/tests/` on a real git history
with a real behaviour change: it *does* find a pin when a change is visible on an input the artifact already
contains.

## Why zero is the answer and not a failure

A behaviour change is **input-specific**. The empty string, the empty tuple and the module's own literals are
not the inputs the change was made for — and the input that discriminates, paired with the outcome expected on
it, **is itself the knowledge**. It arrives with a test, with a demonstration, or with a stated intent. There
is no way to derive it from the code, from repetition, or from any amount of experience, because the code
before the change and the code after it are both consistent with every input the artifact happens to contain.

Three independent instruments in this tree now agree, and the field agrees from the other side:

- **last round**: 18 of 18 real witnesses demanded content that did not exist in the artifact; a perfect
  oracle at a localised site still could not name the edit;
- **the reach law**: 75.2% of 2,178 real fix pieces are named by no operator any other task ever produced, and
  coverage with every other task as experience is 18.7%;
- **the refuse share**: 10 of 14 real commits have no mechanical postcondition at all;
- **arXiv 2607.18057 (July 2026)**, 4,882 agent-authored PRs: existing tests execute 27.0% of changed Python
  lines, and in **64.8%** of Python PRs not one changed line is executed by any test;
- **industry analysis, November 2026**: "the verification bottleneck is now the center of the workflow";
- **Stanford CS329A, August 2026**: "verification is the bottleneck for self-improvement";
- **Stack Overflow, 13 November 2026**: of 1,000 AI-authored unit tests audited, **9.6%** were useful
  verification checks — an agent grading its own homework is not verification.

## What is real and what is not

**Real.** One execution plus a sufficiency verdict settles an action where survivors agree. Instant learning of
a new environment is a genuine cost law (29 trials, 25.78-request payback). Exact verification is cheap, and it
is why coding compounds while creative work does not. A model can be built with no knowledge in its parameters
and no external model in the loop — that principle stands and this round violates none of it. And a mechanical
constructor *can* pin a behaviour change — just only when the discriminating input is already in the artifact.

**Not real.** That the learning rate is the bottleneck: it multiplies a term that is already small. That
experience makes capability grow: it names no new reach. That a perfect oracle makes edits namable: 18 of 18
refusals. That checkability can be manufactured out of the artifact: 0 of 13. That an agent can verify itself:
9.6%. That the artifact's own examples are an independent specification: 0 discriminating.

**Declined.** Sentience. We were never building a creature; we are building a capability engine, and
"sentient" buys nothing a measurement can use. The creature framing is the source of the two most expensive
mistakes in this project: believing that *being* more is the same as *being able* to do more, and spending on
the learner when the ceiling was on the specification.

## Is it revolutionary versus how agents learn today?

Yes — but not for the reason in the question. Frontier agents learn by putting knowledge into parameters and
by generating enormous volumes of self-graded experience. The three-quarters of capability that is missing is
not in the learner: it is in the specification, and 64.8% of real Python work arrives with no executable
specification at all. An agent that spends its budget on the learning term is optimising a multiplier of the
smallest factor in the product.

## The smartest next move

Stop raising the learning term. Every remaining point of capability sits behind **specification**:

1. **Construct the discriminating input** from stated intent — the user's sentence, a demonstration, or a
   witness the failure itself supplies — then let the existing exact verifier and the existing search do the
   rest. That is the only lever whose ceiling has not already been measured.
2. **Never let the artifact grade itself.** The doctest result is the general warning: anything that moves with
   the code is not a specification. Independence is the property that makes a check worth anything.
3. **Keep the refusal honest.** A refusal with a named reason is a result; a converted number that turns out to
   be a memory address is the thing that kills a project. This round produced both, and only published the
   second because it had caught the first.

Reproduce every number above with:

```
.venv/bin/python -m pytest canonical/tests/test_checkability_by_differential_pin_v1.py -q
.venv/bin/python canonical/swe_kernel/checkability_by_differential_pin_v1.py --corpus --limit 40 \
    --json canonical/verification/CHECKABILITY_BY_DIFFERENTIAL_PIN_20261116_V1.json
```
