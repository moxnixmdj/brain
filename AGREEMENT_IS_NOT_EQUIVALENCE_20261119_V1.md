# Agreement is not equivalence

*Round dated 2026-11-19. Receipt: `canonical/verification/AGREEMENT_IS_NOT_EQUIVALENCE_20261119_V1.json`.
Tool: `canonical/tools/agreement_is_not_equivalence_v1.py`. Tests: 21, all green. Five real machines
(tarball, filesystem, SQLite, git, sort), one grammar of 244 terms, 983 executed runs, no model, no weights,
no parameters, no network. 138.7 s.*

---

## 0. The answer on one page

The question is the one this project keeps returning to: *if the agent does something once and keeps it
permanently, do we get all of computer use?* The last round answered half of it well. It measured that the
user's goal, over a 244-term grammar on 555 executed runs of three machines, has a minimal class of exactly
**two** statements:

```
created_once[probe_new_content]
monotone[probe_new_content] ∧ final:count[probe_new_content]==1
```

and it wrote the bottleneck like this: *"the residual class — and the fact that it can only be closed by
language, not by experience."* It then pre-registered the next step: ask the user one question, price it at
`log₂(2) = 1` bit, and validate the answer on an environment it was never fitted on.

**That sentence is wrong, and this round is the measurement that shows it.** The bit is real — no run of any
machine in this tree separates those two sentences — but it does not need the user's words. It needs a proof.

| measured | result |
|---|---|
| runs, five real machines (three fitted, two never fitted: git, sort) | **983** |
| traces on which *both* statements disagree with the goal's own judge | **0** |
| count histories checked against the judge (every history ≤ 6 steps, jumps −3…+3) | **38 791** |
| statements equivalent to the judge over that envelope | **exactly 1** — `monotone ∧ final:count==1` |
| the witness that separates them | counts **0 → 2** in one step |
| machines whose largest single-step increase is ≥ 2 (i.e. could exhibit it) | **none** (max 1; two machines 0) |
| questions of the user needed | **0** |
| the precondition that makes the survivor permanent | `count(initial state) == 0` — true on **5 of 5** machines, one read each |
| model calls, parameters, network | **0, 0, 0** |

So: 983 runs. Perfect agreement. And still two different functions. What separates them is not another run,
because **no run of any of these machines can produce the transition that separates them**: the difference
lives on a single step that adds *two* copies at once, and no atom of any machine does that. The residual was
never a shortage of evidence. It was outside the **action alphabet**.

The consequence is the round's law:

> **Agreement is not equivalence.** A rule learned from runs is consistent with the goal; a rule *proved*
> equal to the goal is the goal. Consistency is evidence, and evidence is always finite — an environment
> that cannot perform the distinguishing transition leaves the ambiguity open forever, at any depth, no
> matter how many runs you add. Permanence is not a property of having seen enough. It is a property of being
> the same function, under a precondition you can check with one read.

This is the correction to "learn it once and it is permanent": one trial does not even identify a rule among
two, let alone make it permanent. What makes a rule permanent is a proof that it *is* the definition — and
the definition, unlike the rule, is total by construction.

## 1. The arithmetic of "it agrees on everything"

Let `G` be the goal, a predicate on traces. A statement `S` is *consistent* with `G` on a set of runs `R` when
`S(r) = G(r)` for every `r ∈ R`. Two statements are *equivalent* when `S(r) = G(r)` for **every** trace,
including the ones no run produced.

```
consistency  =  |{ r ∈ R : S(r) ≠ G(r) }| = 0
equivalence  =  |{ t ∈ T : S(t) ≠ G(t) }| = 0        with T the set of ALL traces
```

The gap between them is `T \ R` — the traces the environment never produced. It is not a small set that more
runs shrink to nothing; it is exactly the set of behaviours the action alphabet cannot express. Add every run
at every depth and the gap stays: an alphabet without a two-copy atom can never produce a two-copy step.

This is why the previous round's number was both right and misleading. Right: `0` of 555 runs separate the
two statements. Misleading: no quantity of runs *could*, and the conclusion "therefore ask the user" skipped
the cheapest source of the bit. There are three places a bit can come from, and they are not equal:

| source | cost | what it can settle | permanent? |
|---|---|---|---|
| the world's own verdict (a run that fails) | one run | anything the alphabet can exhibit | yes, for that behaviour |
| **a judge plus a proof** | one definition, one check | **anything, including traces the world cannot produce** | **yes** |
| the user's words | `log₂(class)` questions | anything at all | only until the next question |

The middle row is what this round measures. It is cheaper than the third and strictly more powerful.

## 2. What the two sentences actually say, and the witness

Read the terms exactly, because the whole round turns on their definitions:

```
created_once[c]  :=  (the count of c increased on exactly one step)  AND  (it never decreased)
monotone[c]      :=  the count of c never decreased
portable_judge   :=  created_once[c]  AND  count(final) == 1
```

Three consequences, each measured:

1. **`created_once` is not "at least once."** On the history `0 → 1 → 0` it is **false**, while
   `at_least_once` is true. The term already carries "never removed". (Tested directly.)
2. **The survivor is the judge.** With the initial count at zero, `monotone ∧ final == 1` forces exactly one
   increase: non-negative integer increments that sum to one. So on every trace, not just the 983, the second
   statement and the judge are the same function. Over 38 791 count histories: **0 differences**.
3. **The other statement is not the judge.** `created_once` allows a *single jump of two*: counts `0 → 2`
   satisfies "increased once and never decreased", and violates "exactly one at the end". Over the same
   38 791 histories it differs on 42 of them. The witness is `[0, 2]`: the first statement says **true**, the
   judge says **false**.

That is the entire residual: one transition, `0 → 2` in a single step. Not a subtle philosophical ambiguity —
a specific missing action.

## 3. Why no machine can exhibit it — measured on the alphabet, not argued

The witness needs a step that adds two copies at once. So the question is not "did we run enough?" It is
"does any atom of any machine do that?" Measured, atom by atom, on a reset machine:

| machine | atoms | largest single-step increase in the probe content |
|---|---|---|
| TARBALL | 4 | 0 |
| FILESYSTEM | 5 | 1 |
| SQLITE | 4 | 1 |
| GIT | 5 | 1 |
| SORT | 4 | 0 |

**No machine can do it, so no depth can find it.** This is a structural fact about the five action alphabets,
not a statement about sampling. It is why the previous round's residual was real *and* why its proposed fix
was too expensive: the environment can never pay this bit, and the user does not have to.

And it sharpens the portability claim in the other direction. The survivor is not "fitted to five machines".
It is **equivalent to the goal's definition**, and the equivalence has one precondition: the initial count is
zero. That is checkable in a brand-new environment with **one read** — five machines, five reads, five zeros.
So the mechanism for learning a goal in an arbitrary new environment is not "try each action once". It is:

```
1. write down the goal as a total judge                     (once, ever)
2. enumerate the statements in a grammar over the observables
3. keep the class consistent with the runs                  -> usually > 1
4. prove one member equivalent to the judge under a
   precondition, or exhibit a witness that separates them   -> 1, or a named gap
5. in a new environment, check the precondition             -> one read, zero trials
```

Step 4 is the one nobody was doing. It costs a proof, not a run, not a question.

## 4. What the field already knows about this, and the two things it proves by accident

This is not a private insight; it is the standard distinction in two mature fields, and 2026 supplied the
evidence that ignoring it is expensive.

**Equivalence checking returns a proof or a counterexample, never a statistic.** Hardware's logic equivalence
checking is used as a correctness oracle precisely because *"conventional LEC provides a proof or
counterexample rather than a statistical confidence estimate, and current LLM-based approaches generally use
LLMs in conjunction with formal equivalence engines rather than as replacements for them"* [4]. And a
2026 conditional-equivalence validator states the contract this round measures: report
`EQUIVALENT_UNDER_ASSUMPTIONS`, `COUNTEREXAMPLE_IN_MODEL`, or `UNKNOWN`, with witnesses and an explicit
model boundary, and require that *"equivalence must cover the modeled observable state, not mere agreement on
a diagnostic label"* [5].

**Behavioural equivalence is coinductive, and provability is not the same relation as equivalence.** In the
algebraic treatment, two objects are behaviourally equivalent when every context returns the same visible
result; behavioural *provability* is a separate, coinductive notion, and the inclusion between them is proper
in general [6]. Two programs that agree on every test you ran and differ on one you did not are not the same
program — they are the same *test result*.

**The quotient is the right object, and it must be computed, not stored.** A June 2026 framework builds
identity on the behavioural quotient `S/≡` under a declared observation model and proves a uniqueness result:
any identity mechanism satisfying invariance and drift-stability must factor through that quotient [7]. That
is this project's `the_goal_is_a_quotient_of_the_trace_v1` reached independently — and it says the quotient is
what survives migration between substrates, which is exactly the "new arbitrary environment" question.

**And the field's own headline benchmark died of exactly this confusion.** OpenAI retired SWE-bench Verified
on 23 February 2026 as *"saturated and also highly contaminated"*, after finding that frontier models could
reproduce gold patches **verbatim from task IDs alone**, and that 59.4% of the hardest unsolved tasks were
structurally flawed; the replacement, SWE-bench Pro, drops top scores to roughly 23% [1, 2]. The companion
measurement is the one that matters here: models name the buggy file from the issue text alone at **63–76%**
on SWE-bench Verified and only ~53% on repositories outside it [3]. Agreement with a benchmark is not
capability; it is agreement with a benchmark. The same substitution — a finite sample of agreements standing
in for a function — is what the two statements in §2 are doing, and it is what the proof removes.

None of these sources is holy. They converge on one arithmetic point that is checkable here: a finite set of
agreements cannot identify a function, and pretending otherwise is what makes "learn it once" fail.

## 5. The single bottleneck, sharpened

The last round said the bottleneck was *the residual class, closable only by language*. The correct statement
is narrower and more useful:

> **The bottleneck is the gap between consistency and equivalence — and the only thing that closes it is a
> proof (or a witness), not more experience and not more words.**

Everything else in this project's chain is now measured and cheap:

- the attempt is decided by trying it, and failure is free (staged, undoable, crash-safe commit);
- the goal's class shrinks with breadth, and breadth saturates;
- one observation collapses a hypothesis space exactly as far as the candidates are behaviourally
  distinguishable on it, and the optimal next probe is the one that splits hardest;
- and now: **agreement on a space of runs is not identity, and the identity is cheap to check.**

Which means the fastest path is not a bigger learner and not a longer experience. It is:

1. **Make the goal total.** A judge, a program, no parameters. (This project has one; so does every test
   suite; so does a type checker. That is why they work.)
2. **Enumerate statements over the observables** and keep the consistent class. Breadth is worth exactly what
   it removes from the class, and it saturates.
3. **Close the class by proof or by witness**, with the precondition named. This is `O(class)` arithmetic, not
   `O(runs)`, and it is what makes a rule portable to environments that do not exist yet.
4. **Reserve the user's words for goals with no total judge.** That is the only place the price in questions
   is real — and it is a statement about the *goal*, not about the learner.

## 6. What this says about our model, our weights, and the sentient creature

The prompt asks whether we should build a model, give it weights, and whether "sentient" is the target. The
measurement above says something specific about what belongs in the weights and what does not.

**What belongs in the weights: nothing that is a fact.** A statement in a 244-term grammar was enough to carry
the goal here; a proof was enough to identify it; a precondition check was enough to carry it into a new
machine. Facts belong in judges and in the environment's own reader, which are programs — instant knowledge,
zero parameters, and exactly the "best part is no part" rule. The frontier's own numbers agree for a
different reason: a benchmark that a model can answer by memorising gold patches is measuring the parameters,
and it was retired when that became undeniable [1, 2].

**What may belong in the weights: the computation, not the knowledge.** Choosing the statement grammar,
choosing the probe that splits hardest, proposing the invariant that makes an equivalence provable, deciding
which precondition to check in a new environment — those are computations over a problem, and a parameter
that computes is not a knowledge house. This round used none, because for two statements and 983 runs, an
enumerator and a proof are smaller than any network would be. A part that is not needed is not built.

**On sentience, one line.** The missing object in "learn it once, permanently" was never a creature. It was
the *totality* of the goal's definition: a creature that knows what it wants is one whose goal is a function
of everything it can experience, rather than a rule fitted to what it happened to see. Totality is checkable —
this round checked it in five machines for one goal — and a checkable property is a better target than an
adjective.

## 7. What is real, what is not

**Real.** No run separates the two statements (983 runs, 0 differences). The survivor is equivalent to the
judge on every count history in a 38 791-history envelope. The witness is one step, `0 → 2`. No atom of any of
the five machines can perform it, so the ambiguity is structural, not statistical. The precondition is one read
and holds on all five. Zero questions of the user were needed, and zero parameters were stored.

**Not real.** "It generalises because it agreed on everything we ran." "The last bit must come from the user."
"More environments will settle it." And the framing the whole project has been circling: that permanence is
what learning gives you. Permanence is what *equivalence* gives you; learning only gives you a candidate.

**Honest limits.** The equivalence is proved for this judge and this grammar, over a bounded count envelope
that is a complete quotient for statements reading only that count — not for goals in general. The witness is a
model, not a run; it refutes an equivalence, and that is legitimate, but it does not show the run exists. And
none of this touches synthesis: the judge can *verify* an edit, but producing the edit is a different problem,
and the asymmetry between them is the next one.

## 8. Next step, pre-registered

**Add the atom that can exhibit the witness, and see whether the proof was load-bearing.** Give one machine a
single atom that places two copies at once — a real command, e.g. `cp file a && cp file b` in one step — and
run it. If the account in this round is right, three things follow and all three can fail:

1. on that run the two statements **diverge** (`created_once` true, judge false), so the class collapses by
   pure experience, with no proof and no question;
2. the run is found by *enumerating the new atom*, not by asking — the alphabet, not the evidence, was the
   binding constraint;
3. the survivor from this round predicts the judge on that machine **before** it is run, because equivalence
   does not need to observe what it already covers.

Falsifiers: if the statements do not diverge on a two-copy atom, then `created_once` is not what §2 says and
this round's witness is wrong. If they diverge but the survivor mispredicts the judge there, then the
equivalence proof is wrong. If neither fails, the criterion — permanence is proven equivalence under a
checkable precondition — is what the field should be building on, and the next bottleneck is synthesis, not
identification.

---

## Sources

1. OpenAI Frontier Evals retired SWE-bench Verified, 23 Feb 2026 — "saturated and also highly contaminated";
   gold patches reproducible from task IDs alone; 59.4% of hardest unsolved tasks structurally flawed;
   ~23% top score on SWE-bench Pro.
2. *Agentic coding benchmarks in 2026* — Verified retired; Pro's public split partly broken; memorisation gap
   measured.
3. *The SWE-Bench Illusion* (ACM, 2026) — 63–76% buggy-file identification from issue text alone on
   SWE-bench Verified versus ~53% outside it; 5-gram overlap by curation.
4. *A Survey on LLM-Integrated Hardware Design Verification* (arXiv 2610.10580, 2026) — LEC returns a proof
   or a counterexample, not a statistical estimate; formal engines are used as the oracle, LLMs around them.
5. FORVES2-style conditional semantic validation (Own.NET #445, Oct 2026) — `EQUIVALENT_UNDER_ASSUMPTIONS` /
   `COUNTEREXAMPLE_IN_MODEL` / `UNKNOWN`, with witnesses and a declared model boundary; equivalence must cover
   the modelled observable state, not agreement on a label.
6. Leavens & Pigozzi, *Equational reasoning with subtypes* — behavioural equivalence versus behavioural
   provability; the inclusion between them is proper in general.
7. *Cross-substrate execution identity* (Zenodo, June 2026) — identity must factor through the behavioural
   quotient `S/≡` under a declared observation model; uniqueness under invariance and drift-stability.
