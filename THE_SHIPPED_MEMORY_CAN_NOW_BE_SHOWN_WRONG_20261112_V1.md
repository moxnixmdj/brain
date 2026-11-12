# The shipped memory can now be shown wrong

**2026-11-12.** Base `8cfbd57d`. Branch `arena/00cef34c-brain`. Round 9 of the owner's question.

Authority **NONE**. Sandbox measurement and decision record, producer-run, one machine. $0, zero
model dependency. No capability registered, no family flipped, no receipt minted, no tolerance
widened. `truth.achieved` stays `false`.

The owner asked whether solved instant learning means one try in each new coding or computer
environment permanently teaches everything, and whether that already makes the strongest
coding/computer-use system. This round re-ran the tree's own instruments instead of quoting its
documents, took the 2026 public numbers, and then fixed the one thing both pointed at.

---

## 1. The answer, in one line

> **One experience buys a binding among operators you already have, plus a record. It becomes a
> permanent *ability* only where something can re-run it and contradict it. Until today this tree
> could not contradict a single lesson it ships. Now it can, and the count moved 0/5 → 5/5.**

| the owner's claim | verdict | the number that decides it |
|---|---|---|
| one try teaches the procedure | **largely right** | 14.1 of 47 programs survive one demo; a taught word composes into 11/12 unanswered requests |
| one try identifies *which* procedure | **wrong** | leader right on 10% of held-out inputs, 0/10 exactly identified; 3 demos → 80%, still 0 for `mod:5`/`mod:7` |
| ~2 chosen questions identify it | **right, and cheap** | 2.0 queries → 100%, 10/10 settled (`settlement_v1`, exact information gain) |
| once learned it is permanent | **right for new lessons, measured today** | teach on A → ship → land on B that never learned anything → re-check on B: **PASS 1/1** |
| ...including the lessons the repo ships | **was false, now fixed** | shipped rules re-checkable by demonstration **0/5**; by self-witness **5/5** |
| therefore anything on a computer is solvable | **wrong, and 2026 bounds it** | OSWorld V2 best **21.3%**; ARC-AGI-3 semi-private best **30.2%**; Terminal-Bench 4.0 **64.85%** |
| therefore the strongest coding agent | **wrong where it is hard** | SWE-bench Pro public **61.5%**; SWE-bench Verified saturated (~97%) and archived as non-separating |

## 2. Re-run today, not quoted

```
one_shot_regime_census_20261112.py      145 bound; 111 typed; 60 typed+receipted (41%);
                                        29 typed with nothing checking them (20%);
                                        8 declared receipts absent; 20 unattributed
one_shot_identifiability_probe_20261112.py
                                        1 demo: 14.1/47 survivors, 10% leader, 0/10 identified
                                        3 demos: 3.1 survivors, 80%, 5/10
                                        1 demo + chosen probes: 2.0 queries, 100%, 10/10
                                        same observation, narrow prior: 100%
auditability_report_v1.py (before)      capabilities 0/294, skills 0/5, process_sites 0/18,
                                        receipts 0/67, binary_identity 5/5
```

Every figure reproduced the documents that claimed it. The documents were honest; they were also
all *arguments about* the same missing mechanism.

## 3. What 2026 measured outside this tree

The ceiling on "solve everything on a computer", from the benchmarks that resist memorisation:

- **Computer use.** OSWorld V2 (108 long-horizon tasks): Agent S4 with Qwen3.8-27B **21.3%**,
  **3.8×** the same model with fixed interfaces, above GPT-5.5 (13.0%) and Claude Opus 4.8
  (20.6%) at ~4.3% and ~1.5% of their cost (arXiv 2610.28601). ScienceBoard 41.4% → 58.6%.
- **Learning in a novel environment from scratch.** ARC-AGI-3 semi-private: best verified
  **30.2%** (Claude Opus 5 High, Jul 2026), GPT-5.6 Sol 7.8%, Opus 4.8 1.5%; at launch in March
  every frontier model was under 0.4% against a 100% human baseline.
- **Coding.** Terminal-Bench 4.0 **64.85%** (Claude Code + Opus 5.5); SWE-bench Pro public
  **61.5%**; Terminal-Bench 2.1 92.8% and SWE-bench Verified ~97% — the latter archived on
  2026-09-01 because it no longer separates frontier models.
- **One-shot skill acquisition is the *baseline*, not the result.** SkillRevise on SkillsBench:
  no skill 36.05%, one-shot generated skill **39.53%**, three rounds of execution-grounded
  revision **61.63%** (arXiv 2606.01139). SkillOpt beats one-shot LLM skills in **52/52**
  evaluation cells, and a skill *trained* in Codex then dropped into Claude Code lifts the
  no-skill baseline 22.1 → **81.8** (arXiv 2605.23904). SkillLearnBench names One-Shot "a lower
  bound on skill-level knowledge acquisition" (arXiv 2604.20087). Skill-Pro's ablation: without
  the PPO Gate, "hallucinated skills enter the pool; performance becomes unstable or degrades".
- **The verifier is the bottleneck, and it cannot be certified by score.** "Removing the anchor
  guards collapses the verifier into a vacuous always-pass grader, yet that collapsed verifier
  trains skills just as well. Downstream task score cannot certify a self-evolved verifier"
  (arXiv 2610.11464).
- **The strongest honest support for the owner is embodied.** GEN-1.5 learns a new physical task
  from a 3–12 s single demonstration with no gradient updates — **59%** average success over 10
  tasks, rising to 83% only after 10 gradient steps — and its authors attribute the ability to
  pretraining at physical-data scale. The prior did the work; the demonstration selected.
- **And the largest single 2026 transfer number is a compiled artifact with the donor deleted.**
  On the ARC-AGI-3 arcade, gemini-3.7-flash cold **37.33** RHAE; handed gpt-5.6's *manuals*,
  **96.42** — above the 95.4 human baseline. 2.6× from an artifact, 0 from weights.

Read together: every large gain came from **compiling experience into an artifact and selecting it
with a check the loop cannot edit** — interfaces (3.8×), manuals (37→96), skills under held-out
validation (+59.7 cross-harness), revision against a verifier (+25.6pp). None came from exposure
count. That is the same sentence this tree reached from its own probes: *the example selects, the
prior and the check generalise.*

## 4. What was actually broken here

Two different things, and only one of them was still broken.

**Transport is no longer the bottleneck.** `crystallize_code_fix` keeps
`provenance.taught_sources` (2026-11-12), and nothing had measured whether that survives the trip.
`skill_transport_roundtrip_probe_20261112.py` measures it: teach on A, export the bundle, import
into a store that has never learned anything, re-check there.

```
teach on machine A                       True
A can re-check it against the demo       {'PASS': 1, 'FAIL': 0, 'ABSENT': 0}
bundle carries the demonstration text    True
imported on machine B (never learned)    {'accepted': 1, 'merged': 0, 'refused': 0}
B can re-check it against the demo       {'PASS': 1, 'FAIL': 0, 'ABSENT': 0}
B can re-check it by self-witness        {'PASS': 1, 'FAIL': 0, 'ABSENT': 0}
VERDICT: SURVIVED
```

**The five rules the repository *ships* could never be contradicted.** They were taught before the
provenance fix; the demonstrations are gone. `recheck` reported ABSENT 5/5, so the auditability
report read `skills 0/5 = 0.0%`: a fresh clone wakes up holding five lessons that nothing, on any
machine, could ever show to be wrong. Attaching a source they were never taught on would be
fabricating provenance — strictly worse than the gap.

## 5. What was built

**`skill_recheck_v1.self_witness(rule)`** — a token rule is not only a record of a demonstration,
it is a *denotation*. Its `pattern_tokens` name a text and its `replacement_tokens` name another,
so the smallest text the pattern denotes can be rendered, put through the **production applier**
(`apply_crystallized_code_rule`), and compared with the text the replacement denotes — plus a
near-miss text (one concrete token altered) that the rule must leave alone.

```
shipped rules                            5
re-checkable by demonstration            0     (unchanged; those demonstrations are gone)
re-checkable by self-witness             5     PASS 5, FAIL 0
auditability, skills layer               0.0%  ->  100.0%
```

The witnesses, each refused on its near-miss by the real applier:

| rule | witness | declared rewrite |
|---|---|---|
| `skill_5b30b7cd…` python | `return w0 + w0 * w1` | `return w0 - w0 * w1` |
| `skill_5e717ccb…` python | `return w0(w1, w2) - w3` | `return w0(w1, w2) + w3` |
| `skill_72276765…` go | `var w0 map[string]int` | `w0 := make(map[string]int)` |
| `skill_9df30abe…` typescript | `return w0.w1;` | `return w0?.w1 ?? 0;` |
| `skill_f8b41c7e…` rust | `for w0 in 1..=w2.len() {` | `for w0 in 1..w2.len() {` |

Two-sided on purpose: a check that only asks "does it fire?" is passed by an applier that rewrites
everything, which is exactly the always-pass grader arXiv 2610.11464 measured and this tree keeps
finding. Failure arms, all reachable and all tested: `WITNESS_NOT_REWRITTEN`,
`REWRITE_DIFFERS_FROM_DECLARED`, `OVER_APPLIES_TO_NEAR_MISS`, `APPLY_RAISED:<Exc>`,
`UNBOUND_HOLE_IN_REPLACEMENT` (a contradiction, so FAIL, not ABSENT). ABSENT stays the safe
direction for an unknown hole kind (a filler is never invented), a pattern with no concrete anchor
(a PASS could not be contradicted), and a refuted rule (inert by design, not broken).

`recheck_bundle(path)` measures the **shipped file** rather than the local store, because the
SQLite store is gitignored generated state and the bundle is the memory that travels.
`main()` gained `--bundle`, and now goes red on a self-witness FAIL as well as a taught FAIL.

**A second defect, found by the new test and not by reading code.** The auditability layer counted
*recallable* rules as its denominator — `_load_rules` reads one `domain` only — while re-executing
*every stored row*. Measured with one recallable rule and one stored-but-unrecallable rule in the
same store: `checkable 2` over `total 1`. **Auditability of 200%.** The denominator is now the
population the check ran over, and the difference is reported as what it is
(`N stored but not recallable by any lookup` — the same class as the `LIMIT 128` defect that once
made lessons 129+ unreachable). A layer's own FAIL now contributes to `red`, so the audit can gate
on a contradicted lesson and not only on a contradicted predicate.

## 6. Mutation-tested — 5 of 5 killed

| mutation | killed by |
|---|---|
| drop the near-miss arm | `test_an_applier_that_rewrites_the_near_miss_too_FAILS` |
| count one rule twice (taught + witness merged) | `test_a_rule_checkable_by_both_mechanisms_is_counted_once` |
| invent a filler for an unknown hole kind | `test_no_witness_is_invented_for_a_hole_kind_nobody_declared` |
| score a refuted rule FAIL instead of inert | `test_a_refuted_rule_is_inert_by_design_not_broken` |
| restore the mixed denominator (>100%) | `test_the_audit_goes_red_when_a_re_executable_lesson_contradicts_itself` |

Plus six parametrised arms pinning that the transport verdict is reachable as `BROKEN`, and one
pinning that the probe does not write into the live store or the shipped bundle it measures.

## 7. The fastest path from here, ranked

1. **Give an executed two-sided check to the 29 typed-but-unchecked doors** (9 are
   `python.software.*` repair, where the check is mechanical). Round 3 named this; it is still the
   highest-value work in the tree, and "give it a try in every environment" would preferentially
   fill exactly those cells, because they are the ones that say yes. *Falsified if* the census's
   `TYPED/NONE` cell does not fall.
2. **Make the rule store ask questions.** `settlement_v1` already selects by exact expected
   information gain: 2.0 queries → 100% identification against 10% for one demonstration. The
   store still does not ask. Nothing in the environment story competes on cost per bit.
3. **Compile experience into an artifact a *different* executor can use, and select it on held-out
   tasks.** This is the only mechanism with a large 2026 number behind it (manuals 37→96 with the
   donor deleted; interfaces 3.8×; cross-harness +59.7). It is also what `THE_PRIOR_IS_THE_WHOLE_GAME`
   §6 B1 already specifies.
4. **Grow the operator space in code.** `taught_words_v1` has 14 built-in parts and refuses
   `median` forever: one experience selects a binding among operators you already have, and never
   creates one. Exposure cannot raise that ceiling; ~500 lines of enumerated, recomputable,
   refusal-carrying parts can.
5. **Only then widen environments.** More environments multiply bindings, not operators, and make
   the reward problem worse (cross-kind compounding is this tree's pinned negative:
   `cold_acts=1525 grown_acts=1525`, byte-identical; learning-to-learn beat a coin flip 3/10).

On the creature: a creature is something whose model of itself can be shown false. Five shipped
lessons just became falsifiable, and the instrument that measures it can now go red from a layer.
That is the part of the creature that can be built from here; it is not sentience and nothing here
is evidence of experience.

## 8. Receipts

```
python3 skill_transport_roundtrip_probe_20261112.py                       VERDICT: SURVIVED, exit 0
python3 -m canonical.swe_kernel.skill_recheck_v1                          taught 0/5, witness 5/5, exit 0
python3 -m canonical.swe_kernel.skill_recheck_v1 \
        --bundle canonical/astra_runtime/skills/VERIFIED_SKILLS_BUNDLE_V1.json
                                                                          5 shipped, 5 re-checkable, exit 0
python3 canonical/tools/auditability_report_v1.py                          skills 5/5 = 100.0%
python3 -m pytest -q canonical/tests/test_skill_self_witness_v1.py \
                     canonical/tests/test_skill_transport_roundtrip_probe_v1.py \
                     canonical/tests/test_skill_recheck_v1.py \
                     canonical/tests/test_the_repo_ships_its_lessons_v1.py \
                     canonical/tests/test_skill_sequence_verify_v1.py \
                     canonical/tests/test_auditability_report_v1.py \
                     canonical/tests/test_invalidation_enforcement_v1.py \
                     canonical/tests/test_rule_generalization_probe_v1.py  101 passed
python3 execution_guard/repo_integrity_guard_v1.py --static-only           rules=11 violations=0 PASS
```

New: 14 tests in `test_skill_self_witness_v1.py`, 11 in
`test_skill_transport_roundtrip_probe_v1.py`. No existing test was edited or deleted.

## 9. Non-claims

A self-witness PASS is **weaker** than a taught-source PASS and is never reported as one: it shows
a rule still means what it says to the engine that applies it, not that it still fixes the bug it
was learned from. The witness is rendered from the rule's own tokens, so the check proves the rule
and the applier agree — that is transport, not correctness, and it is not independent verification.
`whole_task_correctness_proved` remains `False` everywhere and is still read by nothing.
`skills 100.0%` is 5 records over 5 records; it is not a capability count and it does not move the
41%/20% census, which measures receipts, not gates. Five rules, one machine, producer-run, no
independent verifier, no GUI, no unbounded computer use. The external numbers in §3 are public
reports, not reproduced here. Authority NONE.
