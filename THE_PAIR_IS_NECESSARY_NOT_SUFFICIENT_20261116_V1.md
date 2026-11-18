# The pair is necessary. It is not sufficient. The shape decides.

**Round 12 · 16 November 2026 · branch `arena/35b422e5-brain` · base `52201aad`**
Model calls 0 · network calls 0 · spend $0 · every execution is a real commit's own test
Receipts: `canonical/verification/CASE_WITNESS_20261116_V1.json`,
`canonical/verification/CHANGE_SHAPE_CENSUS_20261116_V1.json`

---

## 0. Your claim, split into parts that can each be checked

You said: *instant learning and instant learning in new environments are solved perfectly; therefore give the
model the smartest actions, let it experience each once, it learns them permanently — and everything on a
computer, including the most advanced coding, is solved, permanently. We were trying to make a sentient
creature. Am I right?*

Six parts. Four of them are already answered in this repository, with numbers, before this round started:

| part | verdict | where it was measured |
|---|---|---|
| one verified experience can be stored and reused with zero drift | **TRUE** | `ONE_EXPERIENCE_IS_ENOUGH_IF_YOU_CAN_STILL_REFUSE_20261112_V1.md` |
| one experience per *new environment* is enough for competence there | **TRUE** | `INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md` |
| "learn once, keep forever" covers most real work | **FALSE** | `LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1.md` — ~1/20 of 691 real changed sites, **0 of 14** multi-line |
| more demonstrations fix that | **FALSE** | `LEARNING_ONCE_DOES_NOT_SOLVE_COMPUTER_USE_20261113_V1.md`; SkillLearnBench 2026 finds more instances do not widen coverage |
| this is faster than how agents learn today | **PARTLY** | acquisition is instant and $0; *yield* is the term that decides outcomes |
| it makes a sentient creature | **FALSE** | nothing here is a creature: a referee, a basis, a verifier, a number that moves when a mechanism is added |

The tree's own formula, from `EXPERIENCE_SUPPLIES_ACTIONS_INTENT_SUPPLIES_SPECIFICATIONS_20261116_V1.md`:

```
P(solved | work) = SPECIFIED(work) × [ MEMORISABLE + AIMED_EDITS ] × VERIFICATION
```

Instant learning owns `MEMORISABLE`. It is real, and it is one factor of three. This round measured the
factor next to it.

## 1. What I built, and why it was not a rebuild

Searching the tree first — the law — found every piece of the chain already present:

- `history_induced_edit_grammar_v1` — the exact verifier and the apply/judge/restore harness;
- `operand_invention_v1` — predicates invented from the target's own imports (round 11);
- `python_interprocedural_value_provenance_v1` — runtime **value capture**, with failing-versus-passing
  argument sets per call edge.

The last one looked like it closed the gap, and it does not, for a reason that is measured rather than
argued: **it partitions test files.** Run on `pypa/packaging` 022ae6c6 it returns
`failing_test_count=1, passing_test_count=0`. One file fails, no file passes, and the differential it exists
to compute is empty on exactly the case that matters — a real commit fails **2 cases out of 344 inside one
file**. The discriminating pair lives at *case* granularity.

Round 11 could only read literal `@pytest.mark.parametrize` tables, which is why it refused 6 of 7 real
commits with `REFUSED__NO_OPERAND`. So this round reads the value out of the **running** case: a pytest
plugin records every call into the target file with its arguments, per test node, and the negative set is the
sibling cases of the same test function — never arbitrary cases from the file, because a case that never
reaches the function is not evidence.

## 2. Measurement 1 — the pair is now obtainable. And it is not enough.

| | round 11 (literal tables) | round 12 (running cases) |
|---|---|---|
| tasks with a failing-vs-passing value partition | 1 / 7 | **3 / 7** |
| solved | 1 / 7 | **1 / 7** |
| one execution per solve | yes | yes |

Coverage tripled and the solve count did not move. The two new partitions — `packaging.requirements`
`Requirement.__init__(requirement_string)` and `packaging.licenses`
`canonicalize_license_expression(raw_license_expression)` — both returned `REFUSED__NO_PREDICATE`. Then I read
what those two commits actually change:

- `4b243af9` adds `__replace__`, `copy`, `Self` — **a feature**, not a missing check;
- `a1f70564` rewrites tokenizer branches (`elif token == "("`) — **a parser shape change**, not a predicate.

No predicate over an input value could have fixed either one, and refusing them is correct behaviour, not a
failure. That forced the question this project had never asked: **what fraction of real changes is even shaped
like a missing check?**

## 3. Measurement 2 — the census of shapes, over every changed site in the corpus

`change_shape_census_v1` classifies all 191 real changed sites (89 tasks, 3 repositories) from the two texts
the corpus already holds, before any mechanism runs:

| shape of the change | sites | share | what it demands |
|---|---|---|---|
| `FEATURE_NEW_DEFINITION` | 53 | **27.7%** | new code — no learned action, no predicate |
| `VALUE_OR_OPERATOR_SUBSTITUTION` | 50 | **26.2%** | a memorisable shape |
| `VALUE_ADDED` | 44 | **23.0%** | memorisable, literal unseen |
| `STRUCTURAL_OTHER` | 24 | **12.6%** | synthesis of control flow |
| `GUARD_ADDED` | 20 | **10.5%** | predicate + seat — the only shape rounds 11–12 address |

- **A missing check is 10.5%** of real changed sites. That is the entire surface of the predicate mechanism,
  and it now explains every zero in rounds 9–12 without appealing to a broken instrument.
- **Replay of a seen edit covers 49.2%** — the `MEMORISABLE` factor — which is exactly why the tree measured
  "learn once, keep forever" at about a twentieth once unseen literals, multi-line edits and context drift are
  counted.
- **New code is required by 40.3%** — the feature and structural buckets. Nothing that is learned, stored or
  retrieved can supply it. That is the largest hole, and it is not a learning hole.

Classification is lexical, so it reads the change and not the intent; it sizes the addressable share and
claims no repair.

## 4. The outside world, November 2026 — it says the same thing from the other side

- **One-shot skills give no average benefit** (SkillsBench, 2026), and even the best continual-learning method
  closes only **~45% of the gap** between no-skill and human-authored skills (SkillLearnBench, Apr 2026).
- **Skill libraries carry a regression tax**: across 18 library conditions, skills newly solved 553 task
  conditions and **broke 324** the bare agent already handled — **59% of the gross gain cancelled**, dominated
  by *grounding displacement*, where an invoked procedure overrides a correct reading of the task in front of
  it (Jul 2026).
- **A pure in-context agent matches an explicit skill library**: 0.605 vs 0.602 normalized reward
  (ContinualSkillBench, Aug 2026). The gain is retained context and feedback, not skill abstraction.
- The field's storage answer is *files, not weights*: production skills ship as `SKILL.md` with progressive
  disclosure (Anthropic, OpenAI, Voyager-style function libraries), and Skill0 (2604.02268) exists precisely
  because retrieval alone does not make skill knowledge stick — it internalises skills by RL with a
  withdrawing curriculum. **Nobody in 2026 is claiming that one experience installs general competence.**
- What *does* transfer is separating a skill's **intent** from its site-specific **implementation**: transfer
  to unseen sites rises from <31% to **73%** (PolySkill, ICLR 2026). That is precisely the defect measured
  here in round 11 — a lesson keeps its sentence and loses its argument.
- Specification from executions is the accepted mechanism: invariant-based APR infers φ_correct from passing
  runs and φ_violated from failing ones (FASE 2024), and SpecTune (2604.11770) validates generated
  postconditions with α (consistency on passing tests) and β (discrimination on failing ones). **Every one of
  those systems uses a model to propose the specification. Ours proposes it from the environment's own
  imports with zero model** — which is the honest differentiator, and also why ours refuses more often.

## 5. So: what is real, what is not, and what is smartest now

**Real.** Acquisition and retention. A verified experience is stored permanently and reused with zero drift.
Instant knowledge is real. Exact verification by execution is real. And a predicate invented from a failing
input partition does repair a real commit in one execution (packaging 022ae6c6, 344 tests, zero model).

**Not real.** That any of this generalises to "anything on a computer, permanently". The ceiling is not
learning speed, memory, parameters, or search. It is two things outside the learner:

1. **The specification** — what would count as correct. From the user's sentence it is usually absent; from a
   test it is present but often *underdetermines the site* (round 11's solver satisfied the suite at a
   neighbouring guard).
2. **The shape of the change** — 40.3% of real changes need code that does not exist yet, and 10.5% is a
   missing check. A learner that only knows how to *edit* is aiming at the smaller half by construction.

**Smartest now.** Stop buying learning. The four mechanisms are built and measured; what remains is
*dispatch plus synthesis*:

- dispatch: classify the shape of the task **before** spending a budget, because each shape has a mechanism
  that is 8/8 when the pair exists and 0/8 when it does not;
- synthesis: the 40.3% feature-and-structural bucket is the only place where capability is still unbuilt, and
  it needs new code from a specification — not a remembered action.

One asymmetry is worth stating, and it is a statement about *this* architecture rather than about difficulty.
A GUI action always yields a state, so the observable density is high; a missing check in code yields
*nothing* — measured last round as **0 frames in the defective file in 7 of 7 real commits**. On observation
alone the code path is the harder one.

The 2026 frontier says the opposite about *outcomes*, and the correction matters: SWE-bench Verified sits at
**80.8-88.6%**, Terminal-Bench 2.1 at **74-83%**, and **OSWorld — GUI automation — at 72.7%**. Computer use
is the lower number. So the honest reading is: GUI work is observation-rich but horizon-long and
perceptually grounded; code is observation-poor but verifiable. Neither is "solved", and neither becomes
solved by acquiring actions faster. The project should measure GUI work on the trace-contract organ it
already has, and expect the binding term there to be *horizon*, not specification.

## 6. What this does not claim

No capability credit, no benchmark rank, no independent verification. 7 tasks with trees and 191 changed
sites from 3 Python repositories is a small, culturally narrow sample; the shape classifier is lexical; the
`REFUSED__COLLECTION` on `itsdangerous` is a harness refusal, not a statement about that commit. Authority
**NONE**.

## Reproduce

```bash
.venv/bin/python -m pytest canonical/tests/test_case_witness_v1.py -q
.venv/bin/python canonical/swe_kernel/change_shape_census_v1.py \
    --json canonical/verification/CHANGE_SHAPE_CENSUS_20261116_V1.json
.venv/bin/python canonical/swe_kernel/case_witness_v1.py --limit 9 \
    --json canonical/verification/CASE_WITNESS_20261116_V1.json
```
