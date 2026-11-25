# Claim audit, 2026-11-24

Every quoted claim in the current prompt, checked against what can actually be
inspected. The rule this file enforces: a claim is **verifiable** only if a tool in this
workspace can be pointed at it. Everything else is marked UNVERIFIABLE and must not be
used as a premise.

## Verified

| claim | verdict | evidence |
|---|---|---|
| Claude Sonnet 5.5 = 70.6% on Terminal-Bench 4.0 | **VERIFIED (vendor-reported)** | Anthropic launch table, 28 Sep 2026; reproduced by six independent outlets. **Caveat:** Artificial Analysis' independent harness measures **63.6%** (Opus 5.5: 59.6%), so the number is a vendor figure, not a neutral one. |
| Muse Spark 1.1 = 61.5% on SWE-bench Pro | **VERIFIED (Scale AI SEAL)** | Scale SEAL standardized public set, 731 tasks, result dated 9 Jul 2026; also 51.5% on the 276-task commercial set. **Caveat:** one aggregation board reports "SWE-bench Verified 61.5%" for the same model, so the figure must always be quoted *with its benchmark name*. |

Both of these are the bar §6 has to clear, and both are far above anything measured in
this workspace. That is the honest context for 10/41.

## Unverifiable in this workspace — and must not be treated as fact

| claim | verdict | why |
|---|---|---|
| Iteration 83 = commit `92b6db85` | **ABSENT** | `git cat-file -t 92b6db85` fails; the hash appears in no local or remote ref, in any of the 11 clones or the brain repo. |
| Iteration 84 = commit `d6c1661a` | **ABSENT** | same. |
| "you already proved" the copy-on-write rollout mechanism | **NO ARTEFACT** | `grep -ril "copy-on-write\|copy on write" canonical/*.md` returns nothing. There is no proof, receipt, document or test in this repository for a CoW rollout mechanism. |
| "you already proved" the cross-modal Petri-net mechanism | **NO ARTEFACT** | `grep -ril "petri" canonical/*.md` returns nothing. |
| 447 capabilities / 226 tricks | **UNVERIFIABLE** | no store dump or counter in the workspace reproduces either number. The store's own receipt says **6 skills admitted, 0 refused, 0 outcomes changed** on packaging. |

The four "already proved" mechanisms — repo-native vocabulary mining, dual-program
splicing, 16-way CoW rollouts, cross-modal Petri nets — are therefore **proposals with
no supporting artefact in this repository**, which is consistent with the prompt's own
framing of them as things to evaluate rather than accept.

## What this changes about how the plan should be read

The prompt presents these mechanisms as established and asks which to build next. They
are not established *here*. Nothing in this workspace has ever run a rollout, a splice,
a Petri net, or a vocabulary mine. What has actually run, and what the receipts show:

- a relation engine over 11 real Python repositories, 10 of 41 verified;
- a store that learns relations and changes **zero** outcomes, with the ceiling now
  measured at zero by construction;
- 37 classified unsolved rows, of which the majority are not reachable by any relation
  over a test run's evidence.

So the proposal to evaluate is not "which of these four proven mechanisms do we
productise" but "do any of these four reduce the 37, and is there a benchmark here that
could even measure it". On the same evidence, the answer for cross-modal Petri nets is
no, because there is no cross-modal task in this workspace at all — every task is a
single Python file plus pytest.

## The one claim I can make about the frontier

The frontier numbers are real and they are ~6x this build on the closest comparable
measure. Stating that plainly is the only useful thing to do with them; §6 is not met
and no combination of local results changes that.
