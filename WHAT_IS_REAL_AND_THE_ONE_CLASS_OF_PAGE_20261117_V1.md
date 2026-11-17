# What is real, what is not — and the one class of page one experience can never reach

**17 November 2026.** Branch `arena/d51f56f7-brain`, base `68e8d11b`.
Authority **NONE**. Producer-run sandbox, one substrate, no model, $0. No capability registered, no
family flipped, no weight touched, `truth.achieved` unchanged. Independent verification is open.

You asked four things. I answer them in your order, and every number below was measured today in
this tree, on real MiniWoB++ pages with real layout, against each page's own reward.

---

## 1. "We already solved instant learning perfectly — doesn't that mean any computer use is solved?"

No, and the gap is narrower and more interesting than "learning is imperfect."

Your own tree has already measured the parts of this chain that work. **One demonstration gives
precision 0.069 with 297 dangerous errors out of 319.** Two *chosen* observations give **precision
1.000 with 0 dangerous errors**. Random observations identify nothing in **0 of 12** seeds. So the
honest statement of your idea is not "show it once": it is **"show it twice, and choose what the
second showing is."** That mechanism is already built here (`contrast_selection_v1`, which ranks
which observation to ask for). One demonstration is a *point*; a second identical demonstration is
the *same point* and adds exactly zero bits.

That is a real correction to "once," but it is not the wall I found today. The wall is smaller and
worse.

## 2. "Just give it a try in all those new environments, and let it do the thing once."

This is the sharpest version of the claim, and it fails on a class of page where **budget is
irrelevant**, which is what makes it worth your attention.

Take `simple-arithmetic`. Its instruction is *"Solve the math problem and type your answer into the
textbox. Press submit when done."* Its only page text is **`8 + 3 =`** and **`Submit`**. The answer
is **`11`**.

`11` appears nowhere on the page. And the part of the system that decides **what may be typed**
proposes only strings the page already states: quoted spans, words of the instruction, then any
text on the page. At every tier:

| tier | candidates offered | is `11` among them |
|---|---|---|
| 0 | 0 | no |
| 1 | 14 | no |
| 2 | 16 | no |
| 3 | 16 | no |

I did not conclude this from the candidate list. I tried to solve the page four different ways,
each with **1200 actions**:

| arm | what it had | actions spent | solved |
|---|---|---|---|
| baseline | the shipped search | 1200 | **no** |
| learned prior | inert-action prior learned on *other* pages | 1200 | **no** |
| page-local **oracle** | perfect knowledge of this page's inert actions | 1200 | **no** |
| shuffled control | the learned prior, association destroyed | 1200 | **no** |

An **oracle** failed. That rules out "the prior is wrong" and "the search is weak" and "the budget is
small." The search was never allowed to *say* the answer. A hand typing `11` and pressing Submit
succeeded immediately.

**So: one experience does not help, because there is no first success to have an experience of.**
You cannot learn from an action your system cannot propose.

## 3. What I built, and how much it actually bought

I added the smallest thing that is not a hardcoded answer: read the arithmetic the page itself
prints, and answer it with the operator the page itself printed.

It stores **the reading of `+ - * /`**. It does not store answers. On three fresh instances the page
said `8 + 3 =`, `1 + 7 =`, `7 x 1 =` and the module derived `11`, `8`, `7`.

Wired into the same explorer, same seeds, same budget:

| | verified on a fresh page | actions spent |
|---|---|---|
| without | 11 of 14 | 1232 |
| **with** | **13 of 14** | **472** |

Every page that already worked was **bit-identical** — same pass, same spend. The only two pages
that changed both went from *fail at 400 actions* to *pass at 20*.

**The control that matters.** Is that from *arithmetic*, or just from offering more strings? Three
random numbers of the same count, three seeds: **all fail at 400**. The derived value: **succeeds at
20, all three**. It is the content, not the volume.

## 4. "So we solve everything on a computer, perfectly and permanently?"

No — and now I can say precisely which classes are open, because I measured the ones this fix
*doesn't* touch. On the same pages:

- **`count-sides`** — the answer is how many sides a *drawn shape* has. The page states buttons
  `3 4 5 6 7`; the correct one depends on geometry the text does not carry. **4 of 20.**
- **`find-greatest`** — pick the card with the greatest number. All numbers *are* on the page, so
  this is a comparison over the page's own cards, not an arithmetic expression. 11 of 20.
- **`bisect-angle`** — build a line that bisects an angle. A spatial construction. The candidate set
  contains none of it.

These are three different missing abilities, not three instances of one. **A single fix does not
generalize across them, which is exactly why "do it once and it's solved" cannot be one mechanism.**

## 5. The three obstacles you named, in this tree's own numbers

You restated them as identifiability, vocabulary insufficiency, and synthesis–verification
asymmetry. Measured here:

| your obstacle | the number today | what it means for your plan |
|---|---|---|
| **Identifiability** — one trace fits exponentially many rules | 1 demo: precision **0.069**, **297/319** dangerous. 2 chosen: precision **1.000**, 0 dangerous. Random: **0/12** | "Once" is wrong by exactly one demonstration — *if* you choose the second. Choosing is built. |
| **Vocabulary insufficiency** — the needed observable is not in the representation | **`11` is not in the candidate set at any tier.** 4 arms × 1200 actions fail, including an oracle | This is the wall that budget cannot cross. Fixing one class: **11→13 of 14 verified, 1232→472 actions.** |
| **Synthesis–verification asymmetry** — replay covers only what was derived | recorded plans stale in **122 of 228 (53.5%)**; **71 (31.1%)** silently corrupt; **106 of 106** correct replays had zero drift | The permanent thing is the *method*, not the *plan*. A plan is a function of the state it was proved on. |

**And the fourth thing, which none of the three names:** an inert-action prior that is *correct on
its own page* does not transfer to another page. The oracle saved 4→3 actions on `count-sides`; the
same insight learned on other pages saved **zero**. Your "learn it anywhere, use it everywhere" is
measured to be **false at the level of the key that carries it** (`click|div|pressable` pools a dead
div with a live one, so it can never be deferred).

## 6. What is real — the part of your idea that is already working

I will not bury this, because it is the strongest thing in the tree:

- **One success, found by the machine, becomes a rule for the next instance: 60.0%** versus 15.0%
  for a cache — **four times**, judged by each page's own reward, on pages nobody here wrote.
- **Two chosen observations identify a rule at precision 1.000**, and the chooser already exists.
- **The reach is real and large**: an operation learned inline reaches 5.3% of sites alone, 86.3%
  composed with rename, 45.8% combined.

So the direction is right. The chaining is what fails, and it fails for a reason that is *specific*
and now *named*.

## 7. What is not real, said plainly

- **"Do it once"** — precision 0.069. It is "do it twice, chosen."
- **"Any computer use"** — OSWorld 2.0 best 2026 agent: **20.6%** binary on 108 long-horizon tasks.
- **"Permanently"** — 31.1% of replays silently corrupt under state drift.
- **"Learn anywhere, use everywhere"** — the transferable prior saved **zero** actions where the
  oracle saved 25%.
- **"More budget fixes the hard pages"** — 2.26× compute bought 1 page. Near-inelastic.
- **"A sentient creature that learns from one act"** — nothing here is sentience, and I will not
  dress a search over a candidate set as one.

## 8. The single bottleneck, stated as of today

> **The set of things the system is allowed to try is generated by COPYING what the page states, and
> a growing share of real tasks need a value or an action that nothing on the page states.**

This is why the three obstacles feel like walls and are not: they are all **one missing generator**,
seen from three sides. Identifiability is about *which* observation to ask for. Vocabulary
insufficiency is about *what may be said*. Synthesis–verification is about *whether what was said
still applies*. Each is a different question about the same artefact — the candidate the system is
allowed to put forward.

The evidence that this is the right bottleneck: fixing **one word** of that generator (the `id`
binding, earlier) took a page from 0.05 to 1.00; fixing **one operator** (today) took a page from
unsolvable-at-1200 to solved-at-20. Small fixes to the candidate set move pages that no amount of
search moves.

## 9. The smartest next things, ranked, with pass conditions

1. **A typed generator of *derived* candidates, not an arithmetic module.** The general form is
   already in the tree: `value_algebra_v1` composes typed operators so the answer space is the
   *product* of primitives rather than their sum, and `acquired_operator_memory_v1` can *induce* an
   operator from worked examples instead of naming it by hand. Today's arithmetic is the one case
   this substrate contains; the next probe should make the generator read "the value that follows
   from what the page states" generally.
   *Pass:* on the same pages, the pages no budget could reach become reachable. *Fail:* any page that
   already worked changes its spend or its verdict.
2. **An effect-carrying skill contract (P, O, A, V, F).** Every field the field converges on in 2026
   (Skill-V, SkillOps, SkillFusion) is about the same thing: a skill must carry what it requires and
   what it produces, so that two skills can be *checked against each other*. This tree has sequence
   verification (cancellation) and nothing that says whether one skill's output satisfies another's
   precondition.
   *Pass:* the known no-op pair is refused by the contract, not by the sequence check. *Fail:* a
   contract that accepts the pair.
3. **Re-key the inert prior by a property that decides liveness.** The measured transfer failure is
   a key problem: `click|div|pressable` cannot separate a dead div from a live one. The tree already
   binds instruction-quoted properties to elements; that is a better key than tag+ability.
   *Pass:* the transferable arm beats the shuffled control on pages it did not learn from. *Fail:*
   it ties the shuffled arm, which is what it does today.
4. **Do not train weights.** Unchanged from the tree's own ruling: the data that exists is
   identified-success-free at the rate that matters (precision 0.069 from one demonstration).

## 10. Honest limits of this document

- **Seven pages, two seeds.** Enough to establish a mechanism, not a rate. I say "mechanism" and not
  "improvement" on purpose.
- **One substrate.** Chromium 480×360, real layout and hit-testing, not a person's desktop.
- **The fix is narrow.** Integer and simple decimal arithmetic, four operators. It does not touch
  geometry, comparison over the page's own cards, or spatial construction, and I measured those as
  still failing rather than claiming them.
- **Three of fourteen page-instances were still unsolved after the change.**
- **I retracted two of my own conclusions today**, and both are in the receipt: a "blind observation"
  claim that came from a malformed action, and a "four arms never differed" claim that came from
  reading a consolidator that hardcodes `null` rather than from the arms.
- **Nothing is credited.** No capability, weight, terminal, family or benchmark claim.
