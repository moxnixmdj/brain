# The branch is the model: 6 of 7 real repairs found with zero predictions — and the one that was lost was lost to pruning, not to ignorance

*2026-11-28. The question, taken whole: instant learning and instant learning in new environments are solved,
so give the model each action once, let it experience each permanently, and it owns everything on a computer.
Is this true, what is wrong, what is real, and what is the smartest thing to do?*

## The thing this round deletes

The project already contains the obvious next step, under a non-obvious name:
`canonical/runtime/environment_learning_v1.py` learns a transition model `(state, action) -> state` by acting,
then plans a shortest path **over the model**. It is the natural design, and it is the design 2026 arrived at
independently — WEVA (EMNLP 2026) carries a learned world model and reports verified lookahead as the gain;
NSPI puts a learned verifier in front of every mutating step; Dual-Frontier (arXiv 2609.26293) is a paper
about how hard it is to attribute a failure between the decision rule and that model.

All of it is machinery for *predicting* a consequence. On a computer you do not have to predict:

    copy the state, run the action, read the exit status.

One execution answers **both** questions at once — *does this action apply here?* (the status) and *what state
results?* (the copy you are holding). The successor is not predicted, it is **had**, exactly, with no
parameters and no error. The planner therefore searches over real states and needs no world model at all.
This round measures that, and reports `transitions_predicted = 0` in the receipt as a fact, not a promise.

It is the best-part-is-no-part applied to planning: the part that is deleted is the model.

## The machine, and what is not rehearsed

Not a fixture. A real clone of `pypa/packaging`, put into a real bad state by running real commands, with a
repertoire of **ten real git actions** — `merge --abort`, `rebase --abort`, `checkout main`, `stash pop`,
`stash drop`, `checkout -- .`, `clean -fdq`, `add -A`, `commit`, `branch -D` — and a goal the repository
itself answers. No annotation says how long the repair is or which actions it uses. Every candidate is a
`copytree` plus one process (`try_edge`): the frontier of the search holds **directories**, not descriptions
of them.

The tasks are the six states a person actually ends up in: on the wrong branch; a conflicted merge; a
conflicted rebase; work stashed and then the wrong branch; a conflicted merge *with* work stashed; and a
four-way mess (stashed work, wrong branch, conflict, a deleted tracked file).

## Result: the repair is found without predicting anything

| stream | solved | executions | edges deleted by knowledge | tasks lost |
|---|---|---|---|---|
| **learn, then prune on the learned conditions** | 6 / 7 | **658** | 318 | **1 (`deep`)** |
| no knowledge at all (the control) | **7 / 7** | 1315 | 0 | 0 |
| knowledge used to ORDER, never to delete | **7 / 7** | 1337 | 0 | 0 |
| the same stream again, warm | 6 / 7 | 639 | — | 1 |

What the search actually found, at the depth it found it (all six on `main`, clean, nothing in progress, the
only difference from the starting commit being the work that had been hidden):

| task | depth | plan |
|---|---|---|
| wrong branch | 2 | `checkout main`, `clean -fdq` |
| conflicted merge | 3 | `merge --abort`, `checkout main`, `clean -fdq` |
| conflicted rebase | 3 | `rebase --abort`, `checkout main`, `clean -fdq` |
| stashed, wrong branch | 5 | `checkout main`, `stash pop`, `clean -fdq`, `add -A`, `commit` |
| conflicted merge and a stash | 6 | `merge --abort`, `checkout main`, `stash pop`, `clean -fdq`, `add -A`, `commit` |

Five repairs in the learned stream and six in the control — twenty-five actions across the five — with no
world model, no weights and no model call, each one verified by `git` itself. The sixth state, `deep`, is
solved by the control in six actions (`merge --abort`, `checkout main`, `stash pop`, `clean -fdq`, `add -A`,
`commit`) and lost by the learned stream, which is the finding two sections down.

## The three goals I had to throw away before any of this counted

This is the part that matters more than the table, because each discarded goal was a plan the search produced
that I had not imagined.

**The weak goal.** "On `main`, clean, no stash, at the starting commit" is a cleanliness invariant, and it is
satisfiable by destroying the work: for the stashed task the planner returned `checkout main; stash drop;
clean -fdq` and reported success. It had thrown the stash away. A goal that can be met by deleting the thing
the user cares about is not a goal; it is a spell-checker.

**The contradictory goal.** Adding "the stashed work must be in the commit" while keeping "at the starting
commit" makes the task *unsatisfiable*, because rescuing work adds a commit. 204 executions, nothing solved,
and the reason is not the planner. The goal had to become: the original history is still an **ancestor**, the
rescued content is in `HEAD`, and the only file that differs from the starting commit is the one that was
rescued.

**The hole the search found by itself.** With that goal, `deep` was solved in 96 executions by
`add -A; commit; checkout main; stash pop; add -A; commit`: commit the conflict and the deleted file **onto
the branch it was already on**, walk away, and `main` is clean. Every clause was satisfied — the mess was now
permanent history on `side`. A human reviewer would not have predicted that plan; the search produced it in
seconds. The goal gained its last clause: **no other branch's tip may move.** Testing that clause cost `deep`
its solution under pruning (below), which is how it should be: the clause is true, so the stream must pay for
it.

The lesson is older than this round and now has a third measurement: **the goal is the specification, and every
hole in it is a legal plan.** Verification is not a rubber stamp on the search; it is the thing the search is
allowed to satisfy.

## The one part that still has to be designed, and it is not the model

The first version of this tool solved 3 of 6 and then 0 of 3, and the cause was not the planner and not the
goal: it was `observe()`, the **key** used to decide whether two states are the same. The key reported branch,
commit and file types — so a state with a stash and a state with the stash dropped were *the same state*, and
the search silently pruned away the entire branch it needed. Nothing failed. The search simply ran out of
frontier.

With the key widened to what git already prints — staged count, dirty count, untracked count, stash count,
and which operation is in progress — the same three tasks went from unsolved (at a budget of 1500 expansions)
to solved at depth 5, 6 and 6 in 244, 331 and 328 executions.

So: the successor is exact and free of error, and the search is complete **only with respect to the key**. A
coarse key is silent incompleteness — the same class of mistake as a coarse sensor, in a place where nobody
looks for a sensor.

## The price, stated exactly

- **Per edge: one copy plus one execution.** In the previous round a copy measured 14 ms; here the whole
  seven-task stream is 1315 executions, about two minutes of wall clock on one core, for six verified repairs
  of real repositories. Nothing is learned, nothing is stored.
- **Depth is the cost.** Two actions for the easy states, six for the hard ones, ten edges to choose from.
  Branching is the entire expense, and it is the only thing the learned conditions can reduce.
- **Deleting edges buys 50%** (1315 → 658 executions) **and cost one task in seven.** Ordering the same
  knowledge instead of deleting with it bought **nothing here** (1337 vs 1315). That is the exchange rate, and
  it is the honest one: a prior that only sorts is free of risk and worth little; a prior that deletes is
  worth a lot and can be wrong.
- **The conditions are never identified.** In this stream `applicability_v1` names **0 of 10** action
  requirements — every one returns `UNDETERMINED` — yet the consensus over its surviving hypotheses deleted
  318 edges, one of them the only path to `deep`. That is the vocabulary-insufficiency result from rounds 23
  and 25 arriving in a planner: an agent can act on conditions it cannot name, and the ones it cannot name are
  exactly where it will be wrong.

## What is real, and what is not

**Real.** A repair of a real repository can be found with no world model, and the verification is free
because it is the same execution that produced the successor. Instant adaptation to a new environment needs
zero training: the environment is copied, not compiled into weights. Learning the actions once is unnecessary
— the action is a program that already exists on the machine.

**Not real.** That this makes the model own "everything on a computer". Three things are still missing, and
none of them is a transition model: (1) a **key** that separates the states that matter; (2) a **goal** that
cannot be satisfied by destroying what the user cares about — three goals in a row failed exactly here; (3)
the **repertoire**, which is the thing the agent does not have and cannot learn from exit codes. The ten git
actions here were written by me. Nothing in this round discovers that `git rebase --abort` exists.

And the branch is exponential in the goal's depth. The reason 2026's agents cannot simply do this is not that
copying is expensive; it is that a six-step repair from ten unordered actions is a million candidate states,
and the previous sentence is why a learned model is attractive in the first place. The correct response is not
to learn the model. It is to spend the branching on the states that matter, with a key that is honest.

## The single bottleneck, and what to do about it

The bottleneck is not the world model and it is not the action repertoire. It is **the specification**: the
goal must say what must survive. Every collapse in this round came from a goal that was satisfiable by
throwing something away — a stash, an ancestor, another branch — and each was found by a plan, not by review.
That is also where the frontier's own failures live (OSWorld 2.0: best 20.6%, failure axes verification and
memory). The smartest move is therefore not to buy a bigger planner; it is to make the goal a statement about
content the owner can check, and to let the search try to satisfy it adversarially.

Concretely, next: keep the branch, keep the exact successor, and treat the learned conditions as an
**ordering** with a budget, not a deletion — because ordering cannot lose a task, and deletion already has.
Then spend the saving where it is not free: on writing goals that name the thing that must survive.

## Reproduction

```
python3 canonical/tools/the_branch_is_the_model_v1.py \
    --receipt canonical/verification/THE_BRANCH_IS_THE_MODEL_20261128_V1.json
.venv/bin/python -m pytest canonical/tests/test_the_branch_is_the_model_v1.py -q   # 8 passed
```

The receipt carries every row, the plan found, the goal reason at the start of each state, the depth, the
execution and copy counts, the prunings, the branch tips it was given, and the streams that were run. The tool
clones its own repository over the network; nothing else in the round touches it.

Authority: **NONE**. Producer-run measurement on a sandboxed machine. No model, no parameters, no weights, no
distillation, no external answer key. Schema `BRAIN_THE_BRANCH_IS_THE_MODEL_V1`.
