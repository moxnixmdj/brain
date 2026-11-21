# The question is a real run

*2026-11-21 · branch `arena/8634d5e2-brain` · receipt `canonical/verification/THE_QUESTION_IS_A_REAL_RUN_20261121_V1.json` · tool `canonical/tools/the_question_is_a_real_run_v1.py` · 8 tests · 0 parameters · 0 model calls*

Authority: **NONE**. Producer-run measurement. Nothing here edits `truth.achieved`.

---

## 0. Requirements restated

Zero runtime model calls; no memorised world knowledge in weights; parameters only if derived; knowledge in an editable external store; one experience in a new environment should become permanent; no questions to the owner; research project then web; first principles; minimal ultimate design; hard honest tests with no leakage; loop to §6. §2 is unchanged and confirmed again: the learned sentence is a string in a JSON receipt, the learner code is the mechanism, no fact is stored in a parameter.

## 1. Project research (including non-obvious names)

- Last round, `the_witness_is_the_question_v1.py`, left a two-part residual: its one-bit sentence was **falsified** by a real machine (4/8 runs wrongly accepted), repaired with 10 user bits, and confirmed on machines it had not seen. Its §7 pre-registered the bottleneck: a hypothesis class that may not fit the goal, and witness situations that were hypothetical rather than executed.
- `the_goal_is_a_relation_over_the_run_v1.py` supplies the grounded term vocabulary (`created_once`, `monotone`, `two_copies`, `never_together`, `present_then_absent`, `final:has[...]`, …) and the two real goal judges.
- `the_goal_is_a_quotient_of_the_trace_v1.py` supplies `portable_judge` ("copy once and keep it") and `moved_judge` ("moved, not copied and deleted"). Its own receipt records the sharp limit: *the coarsest function of the trace is the label itself and it is unlearnable*.
- `applicability_v1.py` already learns conjunctions of positive facts and decides past an enumeration wall by arithmetic; it reports "add negation" as a possible next repair but does not implement negation. This round does not rebuild that learner: it uses a different object — conjunctions of negatable **run terms** with membership questions — and records where the existing learner's class stops.
- `THE_LEARNER_DECIDES_PAST_THE_ENUMERATION_WALL_20261116_V1.md` (exact survivor counting), `THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_20261129_V1.md` (CEGIS priced in cells and questions), `REFUSING_TO_GUESS_20261104_V1.md` (admissible-set multiplicity and honest refusal), `BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.md` (the class ends in words) were read as prior constraints, not re-proved.

## 2. Frontier research (2026, input not truth)

- Exact learning theory: membership queries can be exponentially better than pool-based active learning, but **halving is the mechanism, not a magic oracle**; synthesized queries can beat random pool scans [1](https://arxiv.org/html/2609.27241). k-term DNF with membership+equivalence queries is hard in general; read-twice DNF and read-once classes are learnable [2](https://arxiv.org/pdf/1706.03935) [3](https://pith.science/paper/2507.20336). This explains why the bounded class here is two literals, not "all boolean formulas": beyond that the honest answer is refusal, not a fake learner.
- AutoSpec (2026) evolves agent rules by CEGIS over annotated traces, converging in 4–5 iterations, and reports learned rules as human-readable and auditable [4](https://arxiv.org/html/2606.24245). C-GRiD (ASE 2026) turns a counterexample trace into a deterministic clarification question and human-in-the-loop specification repair [5](https://dl.acm.org/doi/pdf/10.1145/3832783.3834379). Both confirm the shape of this round; neither was used at runtime.
- Hardest open bars as of Nov 2026: SWE-bench Verified ~76.8–79.2% harness-dependent, SWE-bench Pro ~61.5% on the public set with ~30% of tasks flagged broken, OSWorld 2.0 binary completion ~20.6% [6](https://personalagentbench.com/benchmarks/swe-bench/) [7](https://decodethefuture.org/en/ai-agent-benchmarks-2026/) [8](https://github.com/Exgentic/eval-containers/issues/733). Our system has not been run on any of them; claiming otherwise would be false.

## 3. Verdict on §3, updated

- **True:** one verified experience creates a reusable rule; new environments buy new distinctions; language closes what runs cannot.
- **False:** that one bit closes the residual once a new environment appears; that a residual computed over fixed machines contains the user's goal; that the old positive-conjunction class can express every real goal in this project.
- **Newly measured false:** a learner can be *identified* by membership questions and still be wrong on an unasked run of the same pool. Verification is a separate organ; identification is not correctness.
- **Still unproven:** sentience; coding or GUI competence on frontier benchmarks.

Real bottleneck now: **verification coverage and class fit**, not replay volume or weights. A concise class is learnable in a handful of user bits, but the bits must be spent on the right situations and the result must be checked on runs that were never queried.

## 4. Single plan and rejected ideas

**Plan:** execute a pool of real runs; ground literal masks (term + negation); enumerate conjunctions of at most two literals as bitmasks; ask the user about the pool run that most evenly splits surviving behaviours; verify the surviving sentence against *every* pool run through more user bits; then check it on deeper runs never in the pool. Fail closed when no sentence fits.

**Rejected:**
- *Keep positive conjunctions and ask more.* On 68 real runs `moved_judge` has **zero** positive-conjunction representations of size ≤2. The question budget cannot fix a missing literal.
- *Learn arbitrary DNF.* Theory says membership+equivalence learning of general DNF is hard; a system that claims it by enumeration would be a fake. Two literals with refusal is the maximal honest class here.
- *Ask hypothetical questions again.* Last round's hypothetical witness was falsified; real executed runs are the only situations used here.
- *Use the judge to pick the query.* Queries are chosen from unlabelled version-space balance only; the judge answers, never selects.
- *Treat "identified" as "correct".* The out-of-class control proves that false: identification after 9 bits, then a mismatch on pool run 30, then refusal.
- *Hand-pick an "impossible" goal.* The first control (portable XOR moved) turned out to be a two-literal conjunction on this pool, so it was replaced by a mask computed to be absent from the class. The mistake is recorded rather than hidden.

## 5. Build and results

| goal | representation on 68 real runs | questions | sentence | deeper runs |
|---|---|---|---|---|
| portable | 5 positive conjunctions | 8 (budget 9) | `created_once[probe_new_content]` | 128/128 |
| moved | **0 positive, 1 with negation** | 9 (budget 9) | `monotone[probe_seed_content] ∧ ¬final:has[seed]=probe_seed_content` | 128/128 |
| computed out-of-class mask | 0 in class | 9 then audit | **refused** after mismatch on pool run 30 | no sentence |

All six declared criteria D1–D6 are MET; 8/8 dedicated tests pass; 0 model calls, 0 parameters, 0 network calls at run time; 230 user bits total, of which 204 are verification answers on pool runs. The first question for `moved` is a rendering of an actual executed run, for example a start state followed by a sequence of content-count changes and holder changes, ending "Is the goal already achieved in this situation?" No answer was guessed by the tool.

**Adversarial cross-tool probe (not part of the receipt).** The learned sentences were evaluated on 17 executed GIT runs and 11 TARBALL runs with a different atom set. `portable` transferred with 17/17 and 11/11. `moved` could not be evaluated on GIT at all: its sentence contains `final:has[seed]=probe_seed_content`, and GIT's reader holds commit hashes, not the name `seed`. On TARBALL it evaluated to 11/11 only because no run there satisfies the goal. TARBALL's 11 runs are a weak check and are reported as such. The failure is a **representation** failure, not a verdict failure: a whole class of the term grammar is tied to a tool's private identities.

**Honest limits.** Pool and deeper runs come from the same filesystem tool at depths 3 and 4. The class is two literals; a goal needing three is refused. The scripted user's bits come from the project's own judges, which are the specification, not a model output. No edit, GUI, SWE-bench or OSWorld task is attempted.

## 6. Next bottleneck, pre-registered

**Surface-neutral relations.** Cross-tool checking is no longer hypothetical: it has already found that the `moved` sentence cannot even be evaluated on git because it names the filesystem's private identity `seed`. The two representations of that goal on the pool both contain a private identity. The next mechanism must express goals over **roles computed from the reading** ("the initial holder", "the final holder", "never two holders at once") rather than over a tool's names; the project's `holders_by_step` projection is the existing starting point. Then verify on a tool with different atoms, compose one edit against a live codebase using the stored sentence as the verifier, and take the resulting agent to an untouched hard benchmark rather than report another CLI count as capability. Pre-registered falsifiers: a role-based sentence that is ungrounded on a second tool; a goal expressible on tool A but not on B; or any repair that uses a held-out label instead of a user bit.

Reproduction:

```
python3 canonical/tools/the_question_is_a_real_run_v1.py \
  --receipt canonical/verification/THE_QUESTION_IS_A_REAL_RUN_20261121_V1.json --depth 3
python3 -m pytest canonical/tests/test_the_question_is_a_real_run_v1.py -q   # 8 passed
```
