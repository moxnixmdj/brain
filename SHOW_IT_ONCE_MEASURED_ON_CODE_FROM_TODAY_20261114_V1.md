# Is "show it once and it is learned forever" the answer? Measured on code collected today

**Date:** 2026-11-14 · **Branch:** `arena/98e3c624-brain` · **Authority:** NONE · `truth.achieved` stays `false`
**Record:** `canonical/verification/ORACLE_ACTIVE_ON_NEW_PULL_REQUESTS_20261114_V1.json`
**Instrument:** `canonical/tools/oracle_active_on_new_pull_requests_20261114_v1.py` · **Tests:** `canonical/tests/test_oracle_active_measure_v1.py`
**Fixture:** `canonical/tests/fixtures/fresh_heldout_pulls_20261114.json` (code frozen 2026-11-14, never read by me before)

---

## 1. The claim, at its strongest

You asked four things and they are not the same question:

1. We solved instant learning and learning in new environments **perfectly**.
2. Therefore we give the model the smartest actions, it meets each once, and it keeps them forever.
3. Therefore this solves anything on a computer, coding included.
4. Therefore we should build it this way, and it will be the most advanced agent on the planet.

Your own tree has already spent three rounds on this and left numbers. This round does not repeat
those. It tests the one thing that had never been measured: **on real code collected today, does an
oracle turn "shown once" into a solution — or is the oracle doing the work?**

Your intuition that this is the fastest lever is **right**. The measurements below say the *ceiling*
of that lever is much lower than "everything", and they say exactly where the ceiling is.

---

## 2. What was done

8 pull requests collected **today**, every one excluded because it appears in no earlier record in
this tree (42 prior names excluded before searching). One changed file is the demonstration; every
other changed file is a target; every *pair* of files is a second showing. The organ is
`edit_by_example_v1` exactly as it stands.

The oracle is the demonstration's own two versions of its own function, and it answers with the
**path the function takes** — not the value it returns. That distinction was not cosmetic: the first
version of this instrument compared returned values, reported every faithfully copied change as
wrong, and had to be thrown away.

230 pairs. Here is everything.

| arm | made a change | of the developers' changes, the organ made | changes the developers did **not** make | targets wholly right |
|---|---:|---:|---:|---:|
| **ONE** — shown once | 44 / 230 | **29.6%** (98/331) | 44 | 27.3% (12/44) |
| **TWO** — shown twice | 128 / 230 | **33.7%** (218/647) | 79 | 38.3% (49/128) |
| **FALSE** — the developers' own answer | 230 | 100% | 0 | 100% |

Read the middle column. **One showing buys 29.6% of a real migration. A second showing buys 33.7%.**
A fourth point, not a leap. That is coherence with what you already measured on constructed spaces —
*one showing memorises, two generalise* — and it is the first time it has been measured on code I had
never seen.

And the oracle, which is the whole point of the idea:

| | value |
|---|---|
| pairs where the organ altered anything | 230 → 44 |
| edited form that even loads as a callable function | **11 of 230 (4.8%)** |
| oracle confirmed the change inside its own probe grid | **2 of 11 (18%)** |
| organ reproduced something the developers actually did | **40 of 230 (17.4%)** |

So: an oracle can speak about **4.8%** of what the organ touches on real code. Of that, it confirms
**18%**. The arm that reaches 100% is the developers' answer itself, which is not a capability of any
system and is not knowable from one demonstration.

---

## 3. The bottleneck is not learning speed. It is reach.

The instrument records why it could not ask more questions. 219 of 230 pairs never reached a question:

| count | why |
|---:|---|
| 123 | the organ refused |
| 85 | the demonstration has no loadable function |
| 11 | the target has no loadable function |
| 11 | **probeable** |

The organ's own refusals, in its words:

```
101  nothing in the file has the form the example changed
 40  a line was changed, but the same code was left alone
 20  the two example files hold the same code, apart from import lines
 14  a line adds, removes or reshapes whole statements
```

**This is the answer to your question, and it is not about speed.** A taught edit needs a *single,
value-driven, loadable function* before any oracle can answer a question about it. Real code is
mostly `__init__` methods, class bodies, decorators, imports, async, call graphs and frameworks.
Showing an agent such a file once does not give it a rule; it gives it a refusal — and the refusal is
correct.

That is why "give it every action once" cannot compound into "anything on a computer". The number of
distinct *value-driven single functions* in the world is large but the number of *situations* on a
computer is not a set of functions at all. A GUI task is pixels, focus and timing. A build failure is
a toolchain. Neither is a function you can call with an integer and compare a path through.

---

## 4. What the world measured last week

Continual-ARC (arXiv **2611.14505**, submitted **10 November 2026** — four days ago) is this exact
experiment, run properly, on three agent harnesses:

| method | puzzles it had met | 100 new puzzles |
|---|---:|---:|
| notes in the harness, as shipped | −0.01 | **−0.01** |
| notes, with expert guidance | 0.03 | **−0.01** |
| a saved program per puzzle | 0.65 | **0.03** |
| **weights trained on the teacher's moves** | 0.57 | **0.29** |

Three agent harnesses as they ship, with persistence on: **no measurable gain on either column.**
Told exactly what to keep, they memorise (0.62–0.72 on met puzzles) and still gain nothing on new
ones. Only the weights moved the second column.

This matters to you directly because it is the strongest evidence yet about *which layer* the
capability will be in. Not the harness — the harness is the part that is currently failing. The
weights are where generalisation showed up. And your constraint (parameters computed, not a
knowledge house; instant knowledge connected in) is **compatible** with that: the weights would carry
*skill*, and knowledge stays in the connected source. That is a coherent architecture, and it is the
one the evidence supports. It is not "the best part is no part" at the level of the weights; it is no
part where a part would be a lookup table, which is the mistake Continual-ARC measured.

---

## 5. What is real and what is not — the verdict table

| what you said | verdict | the measurement |
|---|---|---|
| Instant learning, in new environments, **perfectly solved** | **Not perfect, and "new environments" is the weak half** | 29.6–33.7% of a real migration on code from today; 17.4% of targets touched at all; one showing memorises, two generalise — a 4-point difference |
| Give it an action once and it is **permanent** | **Storage: yes. Capability: no** | the rule is stored and reapplied (44 targets), but only 4.8% of pairs even reach a checkable form, and the oracle confirms 18% of those |
| An **oracle** makes this a solution | **It makes it usable, not general** | questions are worth 2.0 queries on a 47-program constructed space (`settled_admission_v1`); on real code there is mostly nothing to ask |
| Therefore **anything on a computer** | **No — different substrate** | GUI agents at ~20.6% binary on OSWorld 2.0; a finite operator basis is flat outside its classes (your own held-out record: 0/10 new kinds) |
| This is a **revolutionary** way to learn, faster than the current way | **Right about the lever, wrong about the magnitude** | one demonstration + chosen questions: 10% → 100% *on a constructed space*; on code, 29.6% → 33.7%. The revolution is in **verification**, not in speed |
| We are building a **sentient creature** | **Not measured, not required, and not helped by any of this** | the only in-tree proxy — does experience change competence on new problems — is what the 29.6% number says, and it says "a little" |

---

## 6. What is actually built, and what to do next

**Built and real (not a claim — records on disk):** a refuse-capable verifier around experience; a
taught-edit organ that reproduces 29.6–33.7% of a real migration from one or two showings; a
settlement layer that turns one demonstration into 2.0 chosen questions worth 10% → 100% on its own
space; a differential witness search that finds an input where two versions of the *same* code
disagree (this branch, this week, 6 witnesses on real commits, 4 on commits the suites could not see).

**Not built, and this round says it is the bottleneck:** a way to make an arbitrary piece of a real
program *observable* — callable, driven by values, with a path you can read. Everything else is
downstream of that. 219 of 230 pairs died there.

So the smartest next moves, in order of leverage, with the reason each is not the primitive one:

1. **Widen what a demonstration can be about, not how fast it is learned.** Class bodies, `__init__`,
   decorators, whole statements. This is what the 123 refusals are made of, and no oracle can help
   until it exists. This is the single highest-leverage change in the tree right now.
2. **Then** make the oracle cheap and automatic at the *class* level — one demonstration should
   produce the questions, the way `settled_admission_v1` already does for functions. That is the
   "show it once, ask two questions, be right" loop, which is real and measured; it is just applied
   to 4.8% of pairs today.
3. **Weights for skill, knowledge connected in.** Continual-ARC is unambiguous that the harness is
   not the layer that generalises. Your own constraint (computed parameters, no knowledge house)
   permits exactly this, and it is what the evidence supports — not a concession to what everyone
   else does, but the only layer in the 2026 measurements that moved the held-out column.

**Killed this round, with reasons:**

- *"Give the agent every action once and it learns anything."* Measured: the organ refuses 123 of
  230 real pairs because the code has no function-shaped place to put the rule. Speed was never the
  constraint.
- *"The oracle will make it general."* Measured: the oracle reaches 4.8% of pairs and confirms 18%
  of those. The 100% arm was the developers themselves.
- *"Test this on the corpus we already have."* The first collection returned the same 8 pull requests
  as every earlier round. That is self-congratulation; it was thrown away and 42 prior names were
  excluded before searching again.
- *"Compare what the functions return."* The first instrument did that and reported 0% because
  `return 1` and `return 2` are the same behaviour. Path, not value.

**One thing this round does not claim.** It is a producer measurement with no independent verifier,
it is one organ and one class of change in six files per pull request, and it says nothing about
computer use. `truth.achieved` stays `false`.
