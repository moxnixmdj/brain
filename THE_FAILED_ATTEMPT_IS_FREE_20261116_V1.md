# The failed attempt is free

*Round dated 2026-11-16. Receipt: `canonical/verification/THE_FAILED_ATTEMPT_IS_FREE_20261116_V1.json`.
Tool: `canonical/tools/the_failed_attempt_is_free_v1.py`. Tests: 12, all green. No model, no weights, no
parameters, no network. The systems under test are git, GNU tar, gzip, chmod and patch, executed on real
states; nothing here is a model of them.*

---

## 0. The answer on one page

The question is whether one trial per action, learned permanently, solves all computer use. The previous
round answered half of it: the *decision* is exact for 5 of 10 real actions when a program prints a check
mode, and blind for the other 5 and for a refusing world. That looked like a ceiling on trial-and-error.

It is not a ceiling, because trial-and-error does not need a decision procedure at all. It needs a **free
failure**. Stage the attempt where nobody can see it, let the action run there, and commit the result with
one rename:

```
stage  := a copy of the live tree
run    := the action, in the stage        -> its exit status is the decision
verify := the stage's digest              -> its content is the effect
commit := one rename, swapping stage into the live position
undo   := the same rename, back
```

Measured on the same machine as the last round — 10 real actions, 160 real states, 4 traps:

| | |
|---|---|
| staged decision equals the real decision | **10 of 10 actions, 1.0** |
| refused attempts | **80, every one left the live tree byte-identical** |
| committed attempts | **80, every one: live == stage, displaced == pre-state, undo == pre-state** |
| `os.replace` of a populated directory | **fails: `ENOTEMPTY`** |
| `renameat2(RENAME_EXCHANGE)` | **swaps two populated trees in one step** |
| two-rename fallback | **a measured window in which the live path does not exist** |
| read-only parent at the commit | **commit refused, live unchanged** |
| price | one copy of the tree per attempt (≈29 KB here), 9.1 s for all 160 |

The five actions no check mode could guard — `stash pop`, `merge --abort`, `checkout`, `branch -d`,
`chmod` — are decided at exactly the same accuracy as the five that could. **The census that limited the
last round stops being the ceiling**, and not because a better oracle was found: because the question "will
this apply?" was replaced by "did the attempt fail?", and a failed attempt now costs nothing.

## 1. Why this works, in one line of arithmetic

Let `L` be the live tree, `S` a copy. Running the action on `S` costs `copy(L)` and cannot touch `L`. So:

```
cost of a wrong attempt = copy(L) + 0        (L is untouched; discard S)
cost of a right attempt = copy(L) + one rename
```

Compare with the two alternatives. Reading the state costs 0 but is blind to the world (3 of 3 refusals
mispredicted last round, and 5 of 10 actions unreadable). Acting in place costs the effect, and a wrong
attempt costs *the world*. Staging is the only one of the three where a wrong attempt is free — and that,
not the oracle, is what makes "try each action once" sound.

## 2. What the commit is, measured rather than assumed

This is the part that decides whether the claim survives, so it is not taken from a manual.

```
os.replace(stage, live)        -> OSError: ENOTEMPTY: Directory not empty
renameat2(AT_FDCWD, stage, AT_FDCWD, live, RENAME_EXCHANGE)  -> 0
```

That first line matters more than it looks. **This tree already contains an "atomic publication" step** —
`brokered_workspace_execution_v1` (snapshot → confined worker → stage → checker → publish) publishes with
`NamedTemporaryFile` + `fsync` + `os.replace`. It is atomic **only because its target does not yet exist**.
The moment the target is a *live, populated* workspace, that primitive does not apply: a rename can replace
a file or an empty directory, never a populated one. The one-step commit needs
`renameat2(RENAME_EXCHANGE)`, which this filesystem supports and NFS, CIFS, 9p, vfat/exfat and Windows do
not. Where it is absent, the portable fallback is two renames with a window:

```
rename(live, old)      -> live no longer exists    <-- measured: live_path_missing_between_renames = true
rename(stage, live)    -> live exists again
```

A crash inside that window leaves no live tree at all. That is why every serious implementation in the
November-2026 record carries a journal or recovery record, and why this receipt reports the window instead
of assuming it away.

## 3. The boundary that the web already proved against the naive version

`RENAME_EXCHANGE` followed by validation is **not** a compare-and-swap. A same-UID writer that replaces the
live path between the check and the exchange can be displaced and lost; the record is explicit that
exchange-then-rollback is "not an atomic compare-and-swap transaction" (harness-evolver #124, Sep 2026), and
that a two-rename fallback is "not the required continuously atomic swap" with a directly observed `ENOENT`
interval (#1730, Oct 2026).

So this round declares the concurrency boundary instead of pretending to have CAS: **the agent owns the live
path.** An uncooperative writer of the same workspace is outside the contract. With that boundary, the claim
is exactly what was measured — free refusal, exact commit, exact undo — and nothing more.

## 4. What is real, what is false, and the single bottleneck

**Real.**

- A wrong attempt costs a copy of the tree and nothing else: 80 of 80 refusals left the live tree
  byte-identical, including three input-valid/read-only-target traps where the *check modes of the previous
  round said yes*. The stage reproduced the live refusal exactly (exit 2 vs 2, 1 vs 1, 2 vs 2).
- A right attempt is exact and undoable: 80 of 80 commits gave `live == stage`, `displaced == pre-state`,
  and an undo that restored the pre-state byte for byte.
- The decision no longer depends on the action being readable. `chmod`, `checkout`, `branch -d`,
  `stash pop` and `merge --abort` — five actions with no read-only decision procedure — are decided at 1.0
  by attempt.
- The commit is atomic where the filesystem can exchange two populated paths, and nowhere else. That is a
  property of the world, not of the method.

**False.**

- *"Learn each action once and it is permanent, so give it the smartest actions and all computer use
  follows."* What is permanent is the *decision*, and only because failure is free. The action's *effect*
  is a function of the environment, so the first attempt on a new machine can still refuse — it just costs
  nothing now. "Permanent" describes the licence to try, not knowledge of the outcome.
- *"The oracle is the missing part."* After this round the oracle is not needed for the decision at all:
  attempt replaces reading. What remains is the **commit**, and the commit is the only irreversible step.
- *"The tree's atomic publication is atomic."* It is atomic for an absent target. Measured: `ENOTEMPTY` on a
  populated one.
- *"Trial-and-error is safe."* It is safe exactly to the extent that the effect is confined to the staged
  tree. A network call, a process, an absolute path outside the workspace, another user's file — none of
  these are stageable. These ten actions are confined; that is a scope, not a proof.

**The single bottleneck.** Not learning, not the vocabulary, not the oracle: **the commit**. Every sound
agent architecture reduces to "make the failure free, then make the commit one step". The first half is now
measured on real actions. The second half is a filesystem primitive that exists on ext4/xfs/btrfs/tmpfs and
does not exist on NFS/CIFS/9p/vfat or on Windows — and even where it exists it is not a compare-and-swap
against an uncooperative writer. Whoever wants "any computer use" must answer for the commit on
filesystems that cannot swap two directories, because that is where the free failure stops being free.

That is also the honest answer to the sentience question: a creature that can act on its world without
being able to withdraw the act is not free, it is only fast. The reversible act is the precondition for
learning by trying, and this round measured where reversibility actually ends.

## 5. The price, and why it is the price of the tree and not of the edit

| action | content bytes of the effect | bytes staged | amplification |
|---|---|---|---|
| gzip_decompress | 48 | 28,858 | 601× |
| patch_apply_real | 6 | 28,869 | 4,812× |
| git_branch_delete_feature | 192 | 29,012 | 151× |
| git_stash_pop | 630 | 29,751 | 47× |
| chmod_exec | 0 (mode only) | 28,876 | — |

The price of undo is the size of the tree, not the size of the edit. That is not a defect of this design; it
is the definition of undo. It also names the only optimisation worth doing — make the copy cheap (reflink,
hardlink farm, CoW snapshot, `git worktree`) — and it says why that optimisation changes the constant and
not the law.

## 6. Why this is the ultimate mechanism and not the incremental one

The primitive answer is a better predictor, a bigger vocabulary, or a model of each program — the round that
returned 0.7647 and, earlier, 30 proposals and 0 solved tasks. The ultimate answer removes the part: **do not
predict the world; make being wrong cheap.** No oracle, no vocabulary, no weights, no parameters. One copy,
one exit status, one rename. "The best part is no part": the part removed is the prediction.

## 7. The next step, and its falsifier

Take the commit to the place it does not exist. For the class of effects where `RENAME_EXCHANGE` is
unavailable, the portable answer is a write-ahead record plus replay: write the intent (paths, preimage
digests, staged tree), fsync it, then perform the commit as a sequence of single-path renames, each of which
is atomic on its own, and recover from the record on the next start. Prediction, stated before the run: a
record-based commit recovers *byte-exactly* from a crash injected at every step of a multi-path commit, and
its cost is one fsync per step, which is measurable in milliseconds rather than in copies.

Falsifier: if the record-based commit cannot recover byte-exactly from a crash injected between two
single-path renames — or if recovery requires a step that is itself not atomic — then multi-path commits
have no sound portable implementation at all, and "any computer use" must be restricted to effects that fit
in one rename. That is the last honest place for this line of work to stop.
