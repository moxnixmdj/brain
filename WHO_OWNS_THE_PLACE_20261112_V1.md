# Who owns the place: naming the changed symbol halves the damage, and the corpus cannot evidence weights

**2026-11-12.** Branch `arena/6fe0e35a-brain`, base `d314e2fe`. Authority **NONE** — producer-run
sandbox measurement, `$0`, zero model calls, no capability registered, no family flipped, no test
weakened.

Last round ended with a measurement and a named next step:

> *A pool of 52 lessons writes 39 lines no developer wrote, because nothing decides which lesson owns
> a place. That is an index wall, not a modelling wall. Scope by the changed name.*

This round does two things: it **runs that step**, and it **answers the weight-space question with a
number instead of an opinion**. Both answers were declared before the runs.

---

## 1. The step, run

Ownership by symbol: a lesson owns a target file when the names its own example **added or took away**
appear in that file. `yaml.load → yaml.safe_load` owns a file that mentions `load` or `safe_load`; it
has nothing to say about a file that mentions neither.

52 lessons, 232 fixed targets, two arms, one corpus:

| lessons loaded | unscoped correct | unscoped **wrong** | scoped correct | scoped **wrong** |
|---:|---:|---:|---:|---:|
| 8 | 1 | 0 | 1 | 0 |
| 13 | 24 | **5** | 24 | **0** |
| 21 | 102 | **21** | 87 | **12** |
| 34 | 157 | **32** | 133 | **15** |
| 52 | 270 | **39** | 231 | **20** |

The scope halves the damage. It is also **not free**: correct changes fall 270 → 231. Both numbers
are reported because either one alone is a lie — a system that does less is easily mistaken for a
system that does better.

## 2. The control that decides whether that is a result

"Do less" writes fewer wrong lines for the trivial reason that it writes fewer lines. So the claim is
not the wrong-line count; it is **wrong lines per edit**, against blind random lessons at comparable
volume:

| arm | files edited | correct | **wrong per edit** |
|---|---:|---:|---:|
| **symbol scope** | 106 | 231 | **0.19** |
| blind random (5 trials) | 81, 85, 75, 79, 74 | 171, 161, 145, 148, 143 | 0.43, 0.39, 0.37, 0.39, 0.53 |

The scope edits *more* files and writes *fewer* wrong lines per edit than every blind trial. Volume
does not explain it. **The scope is a decision about which lesson owns a place, not caution.**

And the honest ceiling, from the second control: the symbol filter leaves exactly **one** lesson
standing on **36 of 232 targets — 15.5%**. A rule that decides one time in six is a beginning, not a
solution. Last round's rejected import scope was unique on 1 of 232; this one is 36 times better and
still silent most of the time. It must not be quoted as a general rule.

## 3. The weight-space question, answered with a number

The critique says the missing layer is weight-space learning, and asks for training on execution
traces. That is a testable claim, and the test needs one thing: **a stream from the same project with
tasks held back.** Training on tasks you then test on measures memorisation, not learning.

The corpus this tree actually has, counted:

```
commits                                        207
distinct projects                              205
projects with three or more commits              0
projects with two or more lessons                1
```

**207 commits across 205 projects. No project contributes three commits. One contributes two lessons.**

So a weight-update experiment on this corpus cannot separate training from held-out at all. Every
"held-out" task would be a different project, and a weight update measured on a different project
from the one it was trained on is not the experiment the critique describes — it is a
cross-project generalisation test with n = 1 per domain and no fine-tuning signal to learn from.

This is not an argument that weights are unnecessary. It is a **data-shape fact** that fixes the
order of the roadmap: **you cannot buy weight learning before you have a stream.** Building the
training harness first would produce a number that means nothing, and the tree has already paid for
that mistake once — the 32/33 artifact that had been compiled before its own intent existed.

## 4. The four requirements, judged again — one has moved

| requirement | last round | now |
|---|---|---|
| **Model training (weights)** | *real but downstream* | **measured as unevidenceable on this corpus** (207/205, 0 projects with 3+ commits). The blocker is data, not compute. |
| **Conceptual understanding** | *already real in one organ* | **now has a second, executable instance**: ownership is expressed over the names a file mentions, and the measured cost of getting it wrong is 21 wrong lines instead of 12. The difference between a scope and a guess is now a number. |
| **Transfer across domains** | *not the binding constraint* | unchanged. The corpus is *entirely* cross-project — 205 projects — so cross-domain transfer is the thing it measures best, and it still fails on composition rather than on domain. |
| **Reasoning about why** | *not measurable yet* | unchanged, and now with a reason: the tree can compute **where** a lesson applies and still cannot compute **why** the replacement is right. That is the oracle's business and it is not solved. |

## 5. What is real and what is not, in the owner's words

* **"Instant learning is solved perfectly."** Recall: yes. Perfectly: no.
* **"Give it each action once and it learns them permanently."** It learns each one **exactly** and
  cannot yet hold many at once without writing foreign lines. This round *reduced* the rate at which
  that happens from 0.37–0.53 to 0.19 wrong lines per edit. Reduced, not solved: 20 wrong lines
  remain at the full pool, and the ownership rule is silent on 84.5% of targets.
* **"The gap is that we are not training weights."** **Half true, and this round shows the half that
  matters is not the half you can attack next.** Weights are the right destination. The corpus cannot
  yet state the experiment. The first move is not a GPU; it is a stream of same-project tasks.
* **"We were trying to make a sentient creature."** Nothing here measures sentience and this round
  does not claim it. What it does establish is narrower and checkable: the system can now say **which
  of its lessons owns a given place**, and can be measured on how often it is right. That is a
  self-model of competence, not of experience.
* **"Isn't this a revolutionary way to learn faster?"** The claim that survives is narrower than the
  one asked for, and it is still worth something: **one demonstration, repeated exactly, at
  precision 1.000 — and an ownership rule that cuts the cost of holding many lessons by more than
  half.** The revolutionary part is the cheapness, not the coverage.

## 6. Reproduce

```
# corpus (needs gh; ~6 min for all three sets)
for s in seen held_out fresh; do
  python3 canonical/tools/edits_repeated_across_projects_v1.py fetch $s
done

# ~6 min: the curve, the two controls, and the corpus-shape count
python3 canonical/tools/lesson_ownership_measure_v1.py \
    --json canonical/verification/LESSON_OWNERSHIP_20261112_V1.json

python3 -m pytest canonical/tests/test_lesson_ownership_is_a_decision_not_caution_v1.py   # 8 passed
```

## 7. Where this round was wrong

1. **I nearly quoted the halving as the result.** The wrong-line count falls because *some* files get
   fewer edits, and the first draft of this measurement had no volume control at all. It was added
   because the previous round's import scope had been killed by exactly that kind of tautology, and
   the lesson was still fresh enough to apply before publishing rather than after.
2. **My first attempt at the blind control was not volume-matched** (it sampled a random lesson count
   rather than the count the symbol filter chose). The reported trials keep their own volumes and are
   quoted per trial, so the comparison is honest, but a strictly volume-matched version would be
   better and is not what was run.
3. **The tool crashed on a kind with no commits** on its first run (an `IndexError` while counting
   corpus shape). Fixed, and the count is what the record now reports.
