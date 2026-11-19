# The record is the commit

*Round dated 2026-11-16. Receipt: `canonical/verification/THE_RECORD_IS_THE_COMMIT_20261116_V1.json`.
Tool: `canonical/tools/the_record_is_the_commit_v1.py`. Tests: 18, all green. No model, no weights, no
parameters, no network. The effect under test is made by GNU tar extracting five members and `rm` deleting
one, on real trees; the crash is a real child process killed with `os._exit`.*

---

## 0. The answer on one page

The last round ended with a named residual and a falsifier. The residual: a multi-path commit is atomic only
where the filesystem can exchange two populated paths (`renameat2(RENAME_EXCHANGE)`, absent on NFS, CIFS,
9p, vfat/exfat and Windows), and everywhere else it is a sequence of renames with a window in which the live
path does not exist. The falsifier, written down before any code this round: *if a record-based commit cannot
recover byte-exactly from a crash between two single-path renames, multi-path commits have no sound portable
implementation.*

**The falsifier is refuted. The record recovers byte-exactly, at every boundary, including from a crash
inside recovery itself.**

| measured | result |
|---|---|
| boundaries a commit is crashed at | **10, all accounted for** |
| before the record is durable | **1 — the tree is provably still the pre-state, and no record exists** |
| at and after the durable record | **8 of 8 recover to the target byte-exactly** |
| after the record is cleaned | **1 — already the target, replay declines (`NO_RECORD`)** |
| a crash *inside* recovery, at every step, then recovery again | **56 of 56 reach the target byte-exactly** |
| the no-record control, same boundaries | **5 of 9 leave a tree that is neither state, 0 recoverable** |
| the quiet path | **byte-exact, no record, no stage, no temporary left** |
| every replace | **`fsync(file)` → `rename` → `fsync(dir)`, in that order, traced** |
| price | **868-byte record, 16 fsyncs, 7 renames per 6-operation commit** |
| model calls, parameters, network | **0, 0, 0** |

The residual is gone, and not by finding a filesystem that can do more. It is gone because **the commit
point was never the sequence of renames.** It is the durable record. Once the record is on disk, every
operation after it is idempotent and re-runnable, so a crash at any point is not a half-commit — it is a
commit with unfinished business, and the business is a fold over content digests that any process can finish.

That is the law this round adds:

> A commit is atomic exactly where its record is durable. Write the record, fsync it, then do any number of
> idempotent single-path steps. A crash anywhere after the record replays to the target. A crash before the
> record leaves the pre-state untouched, because nothing has happened yet.

Atomicity stops being a filesystem capability and becomes a per-path digest condition.

## 1. Why this works, in one line of arithmetic

The previous round committed with one rename, so the whole commit was one fact, and the fact was atomic. This
round has six operations and must commit them with six renames, each atomic only on its own. The move is to
stop asking the filesystem for a fact it cannot give, and manufacture the fact:

```
record := every operation, with the pre-image and post-image digest of its path, written durably
commit := for each operation: replace or delete that path, durably          (each step atomic on its own)
replay := for each operation: pre -> do it, post -> skip it, neither -> refuse
```

Three properties follow, and none of them needs a new syscall:

1. **Order stops mattering.** Every operation's applicability is decided by the digest of *its own path*, so
   the operations commute. A replay interrupted after operation 3 resumes at operation 1 without harm,
   because 1–3 report `ALREADY`.
2. **The commit point is a moment, not an interval.** Before the record is durable, no operation can have
   run, because the code writes the record first. After it, every operation must run, because the record says
   so. There is no state in which the commit has half-happened without a record that says so.
3. **Recovery needs no judgement.** It is a fold over digests. `pre` → apply, `post` → skip, `other` →
   `REFUSED_DRIFT` and touch nothing. There is no supervisor, no daemon, no external log, no "was it done?"
   question — the question has a byte-exact answer stored next to the tree.

The arithmetic is the previous round's, one level up. Then: *a wrong attempt costs a copy*. Now: *a crash
costs one replay*. Both replace a capability (an oracle; an atomic multi-rename) with a property of the data
(a stage the live tree cannot see; digests that name their own completion).

## 2. What the commit is, measured rather than assumed

The effect is not written into the target. It is produced the way a real action produces it: `tar` packs five
members, `tar` extracts them into a stage, `rm -f` deletes a sixth file that existed before. The stage and the
live tree are then compared, and **every path whose digest differs, or that exists on only one side, becomes
one operation**. Six operations: five creates, one delete. Nothing about the target is typed by hand.

Then the commit is crashed at every boundary it has — `before_journal`, `after_journal`, `after_op:<path>`
for each of the six, `after_committed`, `after_cleanup` — in a **real child process**, and a fresh process is
asked to recover. The result is not one number, because one number would hide the interesting structure.
Every boundary lands in exactly one bucket, and each bucket has its own asserted outcome:

| bucket | boundaries | what must be true |
|---|---|---|
| unarmed — before the record is durable | `before_journal` | tree **is** the pre-state; **no record exists**; nothing to recover |
| armed — at and after the record | 8 boundaries | recovery reaches the target **byte-exactly**; no record left behind |
| completed — after cleanup | `after_cleanup` | the target is already in place; replay declines |

The first draft of this criterion was cruder — "every boundary recovers to the target" — and the first run
measured 8 of 9. The exception was `before_journal`, where the record cannot exist by construction and the
tree is still the pre-state. That is not a recovery failure; it is the all-or-nothing property, and the
receipt discloses the refinement in its own field, including why it *strengthens* rather than relaxes the
claim: a pre-record crash now has to prove the tree is untouched **and** that no record exists, which the
crude criterion would have said nothing about. No measured boundary was dropped, and the buckets together
account for all ten.

Two smaller measurements are the ones that make the result trustworthy rather than decorative:

- **The control.** The same commit with `--no-record`, crashed at the same nine pre-cleanup boundaries,
  leaves a tree that is neither the pre-state nor the target at **five** of them, and there is no record to
  recover from — `recover` returns `NO_RECORD` and the tree stays half-applied. That is exactly the failure
  the previous round named, reproduced on demand. The record is not a story about why the old limit was
  wrong; the old limit was right, and this is the measurement that shows the difference a record makes.
- **Recovery crashed inside itself.** A recovery that is not crash-safe is not a recovery. For each of the
  eight armed commit-boundaries, recovery is killed at each of its own seven steps, then run again: **56 of
  56 second recoveries reach the target byte-exactly.** Replay is idempotent per path, so being killed during
  it costs one more replay.

## 3. The boundary the web had already proved against the naive version

The obvious version of this round is wrong, and it is worth saying who measured that before we did.

`rename` is atomic with respect to *readers* and **not durable** with respect to *power loss*. Without an
`fsync` of the parent directory, a crash after the rename returns the target to its **old** contents, with
the fsynced temp file orphaned beside it — reproduced in October 2026 with `dm-log-writes` and a replay at
every crash point on ext4, xfs and btrfs, and filed against `write-file-atomic` and `atomically` as a
correction to "rename is atomic, therefore safe" [1, 2]. The window is roughly the journal commit interval —
about five seconds on ext4's default. The same correction appears in a durable-write package that states its
own honest limit ("has not been tested against a real crash or power-loss event") [3], in a bug report that
puts it exactly right — "atomic rename prevents readers observing a partial replacement, but is not by itself
a power-loss durability barrier" — and adds that a `kill -9` alone cannot validate anything [4], and in a
journaled state machine that implements the prepared/committed/recovery cycle with `SIGKILL` at eleven fsync
and five replace boundaries while explicitly recording physical power loss as **`NOT TESTED`** [5]. One
implementation goes further and fsyncs the parent *and its ancestors* up to a trusted root, and notes that a
deletion must sync its parent too or the deletion comes back after a crash [6].

So the primitive in this round is not `os.replace`. It is:

```python
write temp; fsync(temp); fchmod(temp, mode); rename(temp, path); fsync(parent directory)
```

and the order is asserted, not assumed: the trace of a representative commit is checked entry by entry, and
every `fsync(file)` must be followed by a `rename` and then an `fsync(dir)` with nothing in between. A
`rename` that is not the middle of that triple is a failure of the discipline, and the test says so.

The honest limit is the one the sources name. **`os._exit` is not a power cut.** It kills a process; the page
cache and the filesystem stay alive. What this round measures is the recovery *logic* and the *visibility* of
a half-commit — not the order of writes after a power cut, which needs `dm-log-writes` and a replay of the
block log, and which this sandbox does not have. The receipt says so in its `limits`, the essay says so here,
and the next round's falsifier is written against exactly that gap. And beneath it: `fsync` returning success
is a promise the device can break — PostgreSQL's 2018 fsync-error incident is the canonical demonstration —
and no amount of ordering in the caller can detect a disk that lies.

## 3b. The mechanism is not new, and that is the strongest thing about it

A round that claims a mechanism should say who already has it. Write-ahead logging plus idempotent redo is
**ARIES**, 1992: force the log record before the data, make redo idempotent by stamping every page with the LSN
of the last record applied to it, and recover with analysis → redo → undo. This round's per-path sha256
pre/post digest is the file-granularity version of the per-page LSN and nothing more [7].

And the whole shape exists in the open, more than once:

- **`fstx`** (Sep 2026) stages changes in a private directory, writes a **journal listing every entry**, applies
  them as **no-replace renames in waves separated by fsync barriers**, writes a durable **`COMMITTED`** marker,
  and — the detail worth copying — **refuses rather than guesses**: `RecoveryRequired` and `inspect()`, touching
  nothing [8]. Its key is the inode number; this round's is the content digest.
- **`bx`** journals every write, rolls an interrupted one back, restores exactly, and states the one rule this
  round also obeys: **unlink the journal last** [9].
- **`soqrates`** writes the intended end state as one durable entry, applies it idempotently, and says why
  recovery must be re-runnable — *"recovery can itself crash and be rerun … idempotent writes of the full end
  state make repeated replay converge"* [10].
- **`tessera`** had to fix exactly the bug that makes a recovery worthless: `recover` rewrote the journal with
  `fs::write` instead of the durable path, so *"a crash during recovery could lose the journal, and every
  committed block with it"* [11].
- **`openscion`** asserts the durability order out of a recorded log and adds `dm-log-writes` **mutation
  checks** — remove the directory fsync, and the suite must fail [12]. **`keel`** files the same correction as a
  bug: `SIGKILL` leaves the page cache alive, so it cannot prove fsync ordering [13].

This is corroboration, not competition, and it changes what the round can honestly claim. **It did not invent
the mechanism; it answered a falsifier.** The falsifier was posed inside this tree, about a specific residual:
*a multi-path commit is atomic only where the filesystem can exchange two populated paths.* The answer is the
measurement — ten boundaries of a real `tar`/`rm` commit, seven steps inside recovery crashed and re-run
(56/56), the no-record control reproducing the old failure on demand, and the three-bucket separation that
turns "a crash before the record" into an asserted pre-state instead of a silent gap.

That the idea is standard is the point the governing law makes. A mechanism that has survived thirty years of
database engineering and has independent implementations in four languages is not an incremental invention to
be replaced next round. It is the final form, and the work is to show it holds here, with no new part.

## 4. What is real, what is not, and the single limiting factor

Three rounds, in order, each removing one reason for the same answer:

| round | the claim it killed | what replaced it |
|---|---|---|
| the precondition is not in the trace | a check mode decided 5 of 10 real actions and was blind to the world | the *attempt* is the decision |
| the failed attempt is free | a wrong attempt costs the effect | a stage, and the commit as one rename |
| **the record is the commit** | the commit is atomic only where the filesystem can exchange two paths | **a durable record, and the commit as a replayable fold** |

The original question — does one trial per action, learned permanently, plus frontier coding, *completely* and
*permanently* solve all computer use? — is still **no**. But the answer is now shorter by the strongest
objection in the list, and the remaining reason is not the one people expect.

It is not "the model is not good enough." It is not "durability" — that is a boundary of the device, and it
does not stop a commit from being correct; it makes a promise about hardware that a caller cannot keep for it.
It is not "atomicity" — measured, and dissolved this round. **It is the scope of an effect.**

Look at what the mechanism actually demands of an effect: a finite set of paths, each with a pre-image digest
and a post-image digest, all inside a tree that the record sits beside. Every property that makes the commit
sound follows from that closure — idempotence per path, commutation, replay, refusal. Nothing else was needed.
So the mechanism's exact reach is: *any effect that can be fully described as a change of local, named,
content-addressable state.*

And the boundary is precisely where that description cannot be closed: a request already delivered to another
machine, a row already committed in someone else's database, an email already sent, a keystroke already
accepted by a window that is not a file. Those effects are not in the tree, so no digest can name them, so no
replay can finish them and no record can refuse them. This is the first-principles statement of the residual:
**reversibility is limited by the information that has left your boundary.** Inside the boundary, the record
makes any local effect reversible, portably, with no new syscall. Outside it, the effect is not atomic, and no
cleverness in the commit will make it so — the fix there is negotiation (a two-phase protocol with the other
party, an idempotency key), which is a different mechanism for a different reason, and it is not built here.

That is the single limiting factor, and it is a *scope*, not a difficulty. Which is why it is good news: the
hard part of "any computer use" was never that computers refuse to undo things. It is that some things are
already outside.

## 5. The price, and why it is the price of the record and not of the edit

A six-operation commit on this tree costs:

| item | count |
|---|---|
| record | 1 file, **868 bytes**, written twice (PREPARED, then COMMITTED) |
| renames | **7** — two for the record, five for the created paths |
| unlinks | **1** |
| `fsync` calls | **16** — file and parent directory, for the record and for every path |
| traced steps | 24 |

That is 2.7 fsyncs per operation. It is not free, and the web has measured what a full durable write costs:
on the order of 6–8 ms against 100–160 µs for an unsynced write [3]. The design's whole claim to being
economical is that the expensive part is paid **once per commit**, not once per attempt: the record is written
twice, and the operations pay one file-fsync and one directory-fsync each because that is what makes a crash
between two of them survivable. An attempt that is thrown away pays nothing at all — that was last round's
result, and this round does not touch it.

The honest comparison is not "record versus no record." It is "record versus a commit that can leave a tree
that is neither the old state nor the new one." Five of nine control boundaries produced exactly that. A tree
in that state cannot be reasoned about, cannot be retried safely, and cannot be undone — its cost is not
milliseconds, it is a corrupted world.

## 6. Why this is the ultimate mechanism and not the incremental one

The incremental move was available and is wrong: widen the syscall. Add `RENAME_EXCHANGE` where it is missing,
or fall back to a two-rename swap with a window, or make the commit a special case of the filesystem's own
journaling. Every one of those makes the mechanism depend on something outside the data — a capability that
some filesystems have, some do not, and none guarantees across a power cut.

This mechanism depends on **`rename` and `fsync`**, which the portability matrix from last round shows are
everywhere the exchange is not. It adds no capability; it removes the need for one. That is the governing law
applied literally — the best part is no part:

- no exchange syscall, and no detection of whether one exists;
- no supervisor or recovery daemon: recovery is a fold that any process can run, including the next one to
  start;
- no external log service, because the record is a file beside the tree, written with the same primitive the
  project already uses for its own durable writes (`root3_typed_durable_admin_write_v1.py`, reused, not
  rebuilt);
- no rollback journal, no undo log, no ordering protocol beyond "the record first, then the paths."

What is left is one file and one rule. A commit that needs nothing but a rename and a directory fsync is not
an incremental improvement on a commit that needs an exchange — it is the same guarantee, delivered where the
exchange does not exist, which is to say everywhere the interesting computers are.

## 7. The next step, and its falsifier

**Durability, at the only layer that can test it.** Put the same commit under `dm-log-writes`, replay the
block log at every crash point, and check two things that process death cannot: that no replayed image contains
a torn or zero-length file, and that the record is either absent (pre-state) or complete and replayable — never
present but naming operations whose pre-images were never durable.

*Prediction:* both hold, because every step is `fsync(file)` → `rename` → `fsync(dir)`, so the record and the
tree can only become durable in an order that replay can finish. *Falsifier:* if any replayed image has a torn
file, or a record that describes a state the tree was never in, then the ordering is wrong and the residual
moves back from the device into the mechanism.

**And the scope, which is the real remaining limit.** Write down one effect that leaves the tree — a request
to another machine — and ask the record to make it reversible. It cannot, and the reason is not an
implementation gap: there is no digest for a message already read. The next round's honest question is
therefore not "how do we commit more things" but "what does a commit look like when one of its operations is a
promise someone else has already kept?" That is a protocol, not a syscall, and it is the first thing in this
sequence that the local record cannot answer.

Until then, the statement stands with its scope attached: **any effect that can be described as changes to
local named state is now committable, atomic, crash-recoverable and portable, with no capability beyond
`rename` and `fsync`** — and the part of "any computer use" that remains is the part that has already left.

---

## Sources

1. `atomically#22` (Oct 2026) — `dm-log-writes` replay on ext4/xfs/btrfs: without a parent-directory fsync,
   the target keeps its old contents after recovery and the fsynced temp is orphaned.
2. `write-file-atomic#243` (Oct 2026) — the same finding, and the fix: open the parent and `fsync` it, tolerating
   `EPERM`/`EISDIR` on Windows.
3. `durablewrite` — the four-step contract, its order, the measured price of a durable write, and its own
   stated limit: not tested against a real crash or power loss; not atomic on multi-client NFS.
4. `evener#2338` (Sep 2026) — "atomic rename … is not by itself a power-loss durability barrier"; a `kill -9`
   cannot validate it.
5. `repocache#34` (Oct 2026) — prepared/activating/committed/recovery with `SIGKILL` at every fsync and replace
   boundary, and physical power loss recorded as `NOT TESTED`.
6. `AgentDesk#7239` (Oct 2026) — fsync the parent and its ancestors up to a trusted root; a deletion must sync
   its parent or the deletion comes back.
7. ARIES (Mohan et al., 1992) — WAL, per-page LSN, idempotent redo, three-pass recovery.
8. `fstx` (neptro/fstx, Sep 2026) — journal + no-replace renames in fsync-separated waves + durable `COMMITTED`
   marker + refuse-rather-than-guess recovery.
9. `bx` (getkono/bx, PR 9) — journal every write, restore exactly, unlink the journal last.
10. `soqrates` (jvanbuel/soqrates, PRs 6, 27) — durable end-state journal, idempotent apply, recovery may itself
   crash and be re-run.
11. `tessera` (vig-os/tessera, PR 696) — recovery must be rewritten through the durable write path.
12. `openscion` (bnsd55/openscion, issue 237) — durability order asserted from a recorded log, with
   `dm-log-writes` mutation checks.
13. `keel` (Nuu-maan/keel, issue 2) — `SIGKILL` is not a power cut; it cannot prove fsync ordering.
14. PostgreSQL fsync-error incident, 2018 — a device can accept a flush and lie.
