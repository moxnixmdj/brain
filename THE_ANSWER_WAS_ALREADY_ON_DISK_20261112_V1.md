# The answer was already on disk. I argued with you from the literature instead.

**2026-11-12.** Authority **NONE**. `truth.achieved` = `false`.

This document exists because of a specific failure of mine, and it changes the answer I have
been giving for five passes.

---

## 1. What I did wrong

For five passes I answered "does one demonstration become a skill in an arbitrary environment"
with citations: SkillsBench "no benefit on average", SkillRevise "3 rounds", PolySkill "<9%
unseen-site reuse". All real. All second-hand.

Meanwhile, in this repository:

```
canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json
canonical/verification/MINIWOB_ONE_MEMORY_FOR_ALL_TASKS_20261111_V1.json
```

...sat a **direct measurement of exactly that claim**, on 130 MiniWoB++ pages nobody here wrote,
scored on seeds **1060–1079 that nobody had looked at before the run**, with the page's own full
reward as the only judge. I never opened it. My greps were for `*.md`; the result is `.json`; I
concluded the tree had no such measurement and said so out loud, three times.

The tree also already knew the shape of the failure — its own intent record reads:

> `causal_blocker: EVERY_MEASUREMENT_OF_LEARNING_IN_A_NEW_ENVIRONMENT_IN_THIS_TREE_WAS_TAKEN_ON_ENVIRONMENTS_WRITTEN_IN_THIS_TREE`

That record is from 2026-11-11. It was already out of date when it was written.

## 2. The measurement, as it stands

Run 5, `cfbc9ff8`, headless Chromium, real mouse and key events, 20 instances per page, one try
each. Not a leaderboard entry; the first success is found by the machine with the page's reward
as its only judge.

```
  arm                       success  replay-not-enough  pages>=18/20
  random                      10.7%               6.6%             2
  verbatim                    26.2%              14.0%            11
  existing_compiler           23.6%              16.7%            13
  version_space               70.3%              65.5%            45
  version_space_blind         29.6%              18.1%            12
  version_space_practice      77.7%              74.0%            51
```

**One demonstration, generalised: 65.5%** where replaying the demonstration is not enough,
against **14.0%** for replaying it. 45 of 130 pages at ≥18/20 from a single success.

### You are right, and more strongly than I said

- One success **does** become a transferable skill: **45 pages at ≥18/20**, on instances never
  seen, judged by the page.
- It is **not a cache**: the cache arm (`verbatim`, replay by position) is 14.0%. That was
  never in dispute and is now the *weak* rung.
- It **beats the tree's own prior generaliser** (16.7%) by four times, on the same board.
- It **generalises across instruction wording**: 33 of the generalising tasks *fail* when denied
  the instance's instruction and 1 still succeeds. What it loses when blind (65.5% → 18.1%), it
  was reading.

This is a real, re-runnable, third-party-environment result, and it was built here before this
conversation started.

## 3. Where your claim still breaks — measured, not cited

**(a) "Once" is not enough for a new instruction.** Zero of the generalising tasks survive an
instruction change. The skill binds new wording by reading it every time; it does not learn the
wording's meaning. `of_which_still_succeed_although_the_instruction_changes: 0`.

**(b) It is not learn-once-forever; it is learn-a-little-more.** Three practice instances move
65.5% → 74.0% (+8.5 points) on the *same* instances — 207 practice episodes, ~45 exploration
actions per task to earn them. If one demonstration were sufficient, practice would be worth
nothing. It is worth 8.5 points.

**(c) The ceiling is 78 of 130.** A first success was found on 78 pages. The rest were never
done at first sight, so **no amount of transfer reaches them.** Transfer here reaches relatives of
learned tasks and no further.

**(d) The remaining failures are action-shape, not understanding.** The run's own `not_done`:
pages needing *"a drag to a place that is not an element, scrolling inside a box, several drags in
a row, or typed text that is not one word of the instruction."* The hand is the limit, not the
skill.

**(e) One memory for all tasks: 26.6%.** `MINIWOB_ONE_MEMORY_FOR_ALL_TASKS` gives a single agent
every skill it ever kept (127 programs, 69 tasks) and lets it meet each task for the first time:

| | mean success | pages ≥90% |
|---|---|---|
| all skills held | 38.2% | 36 |
| **met for the first time** (`without_this_task`) | **26.6%** | **24** |

So "we solve everything on a computer" is measured, and it is **26.6%** when the agent has to
meet a task with no skill of its own — with the caveat that `of_which_had_no_skill_of_their_own`
is empty, i.e. a page with no first success was never solved at first sight at all.

## 4. The lesson that generalises

Five passes of argument, one file. The failure mode is not "the model was wrong about the
repository" — it is that **an unread correct measurement and an absent measurement are
indistinguishable from the outside.** That is the same defect I spent the last five passes
finding in code: `verified_hits` that counted approvals, receipts naming a program nobody
checked, a refuted rule still firing, a missing dependency reported as a failed learner.

It was also true of *me*, reading.

So the fix is not another document. It is
`canonical/tools/one_success_where_it_counts_v1.py`: the ladder above made callable, which

- reads the **newest** recorded run from disk rather than trusting a constant;
- prints every rung including the ones that make the claim modest (`verbatim` as the cache arm,
  `version_space_blind` as the control);
- prints `not_done` — what the run never attempted;
- and **returns 1 if the board contradicts itself**, specifically when a lift is reported without
  a replay baseline, or without the denied-instruction control, or when nothing needed
  generalising.

It is now the 8th layer of `auditability_report_v1`, so the one layer measured on environments
written outside this tree is in the same report as the seven that audit the tree's opinion of
itself. All seven of those are audits of self-report. This is the only one with an external
judge, and it is the only one at 100%.

---

## Verdict, final form

**Is one demonstration enough?** No — measured, not cited: 0 of the generalising tasks survive an
instruction change, and practice is still worth +8.5 points.

**Is one demonstration worth a great deal?** Yes, and I understated it for five passes. 65.5% vs
14.0% on unseen instances, 45 pages at ≥18/20, judged by a page nobody here wrote. That is the
strongest single number this repository has, and it argues *for* your thesis.

**Does this reach "anything on a computer"?** No. 78 of 130 pages ever produced a first success;
a shared memory meets a new task at **26.6%**; and the residual failures are missing action
primitives (drag-to-nowhere, inner scroll, multi-drag), not missing skill.

**Am I right or wrong?** Right about the architecture and now measurably right about one
demonstration's value. Wrong that it is *sufficient* — for a new instruction it is zero, and the
ceiling is set by whether a first success is reachable at all.

**The smartest next move is no longer mine to guess.** The run states it: extend the hand
(drag-to-a-point, inner scrolling, sequences of drags, multi-word typing) and re-measure the same
board on fresh seeds. That is one change with a pre-registered number attached, unlike anything
else available here.
