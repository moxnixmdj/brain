# An action's effect is a provenance map — and one execution is enough to know it

**Receipt:** `canonical/verification/AN_ACTIONS_EFFECT_IS_A_PROVENANCE_MAP_20261119_V1.json` · 6 of 6 gates MET · 0.2 s, 8 real binaries, **24 of 24 unexecuted states predicted whole-tree exactly**, 0 model calls, 0 parameters, 0 network.

## Where the question now stands

The claim is: *learn each action once, keep it permanently, and you can do anything on a computer.* After two rounds the answer has a precise shape:

| question | answer | cost |
|---|---|---|
| when may I act? | derived from the action's **refusal surface** | one execution per condition (last round: 98 total) |
| what does acting do? | derived as a **provenance map** | **one** execution per action (this round: 8) |
| how do I chain them? | compose the two maps; the second step's precondition must be the first step's effect | verified by execution |

This round closes the second row, which was the documented wall of an artifact already in this tree:

> `compose_measured_effects_v1`: *"an atom whose measured effect is INERT or UNCLASSIFIED is not an operator, so `cp` (which duplicates a content, a shape outside the three-effect vocabulary) is unusable — the composer cannot use what the vocabulary cannot name."*

The vocabulary was hand-designed. It is now **derived from the action itself**.

## The principle

> Every changed path in the post-state got its value from somewhere in the pre-state: it *is* that value, or a decoding of it, or a member of it, or a sort of it — or it is a directory, a link, a deletion, or a mode.

If a path's new value is explained by a provenance relation **against one of the action's own arguments**, the effect is a *rule*, not a record of one run. That is exactly what makes one execution enough, and it is precisely what a trace-based world model cannot claim: a trace says what happened once; a rule says what happens whenever.

Everything that could be hardcoded was instead read off the observation — whether the changed path *is* an argument, lies *under* one (a container extracted into a directory), or is an argument with a suffix stripped (gzip). References are stored as **argument indices**, never as literal paths, which is why the rule survives a state where every name is different.

## The measurement

Eight real binaries — `tar -xzf`, `gzip -dk`, `cp`, `mkdir`, `ln -s`, `chmod`, `sort -o`, `rm -f`. Learn the rule on one state, then apply it **blind** to three states that were never executed, and compare the predicted tree against the tree the real binary actually produces.

```
held-out states 24/24 exact   (whole tree incl. mode 24/24)
actions that failed to transport: []
compose: second step alone rc=1 → after mkdir 0/0, goal reached, predicted first
```

Variant 3 does not merely rename things: it adds a **third archive member one level deeper** and moves an input into a nested directory. It is still predicted exactly, because the content comes from the *input's own contents*, not from the learned example.

Two failures found on the way, both real and both fixed rather than hidden: rules were keyed to literal paths (so nothing transported), and my own fixture reused one payload across eight actions, manufacturing a spurious provenance ambiguity — a copy that was *also* the decompression of an unrelated blob. The fix is principled: **provenance must cite the action's own argument**, and ties are reported, not silently broken.

## Why this is not a world model

The 2026 state of the art for computer use is parametric: CUWM fine-tunes a model on offline UI transitions so an agent can simulate a candidate action before committing. Ours has **zero parameters**, and predicts byte-exactly — because on a file system the effect *is* deterministic and its vocabulary *is* provenance.

That is the honest boundary too. A file system has a byte-identical delta; a GUI does not. The same idea would need a provenance lattice over UI elements, and this receipt does not claim it. And an action that reads **ambient** state — a build system reading timestamps, `git` reading an index — is not in this pool: its effect is *conditioned on facts*, and conditioning is exactly what the refusal-surface round supplies.

## What is real and what is not

- **Real:** one execution ⇒ a rule that predicts whole unexecuted trees, exactly, including modes, for tools that read their arguments. `cp` becomes nameable, so a goal about a duplicated content stops being inexpressible. Two actions compose when the second's precondition is the first's effect, verified by execution.
- **Not real:** "one experience, therefore all computer use". Effects are transportable *because* they are functions of the arguments; preconditions are not, and last round measured one success as wrong on 123 of 160 states. The two layers have opposite economics, and that difference is the thing to remember.
- **Not claimed:** sentience. But note what the two rounds together do give: an agent that knows when it may act, what acting does, and can predict the result *before* committing. That is the computable core of understanding an environment, and it needs no weights.

## The bottleneck has moved — to the goal

Both vocabularies are now derived. What remains hand-written in the composition demo is the **goal**: *"`out/deep/x.txt` has the source's content"* was stated by me.

That is the next wall, and it has the same shape as the last two. A goal is not a sentence; it is a **refusal by a goal-checker** — a failing test exits non-zero and names what it wanted, a type checker refuses with a diagnostic, a compiler rejects with an error. So the goal vocabulary is derivable by exactly the machinery of the precondition round: *the failing check is the refusal, and its message names the predicate.*

That is the next round: **the goal is a refusal too.** Not a plan search over a hand-written goal, but a transition system whose operators are verified (both rounds) and whose goal is read off the checker that says "no".
