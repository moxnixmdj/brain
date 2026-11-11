# What this model can actually do, in plain words

**Measured, not claimed. 13 ordinary computer tasks, tried once each.**

| | |
|---|---|
| **3 of 13** the machine can attempt **and check** | compress → `.gz`, hash → `.sha256`, compress logs → `.zip` |
| **10 of 13** it **refuses** | the rest |

It refuses the 10 for one reason: **it cannot tell whether it succeeded.**
`.txt`, `.md`, `.py` are plain text — if the file appears, that proves nothing about
whether the content is right. A question like "count the lines in a.txt" has no file
as its answer at all. `out.tar.gz` needs two steps, and each step is thrown away
before the next, so the middle cannot be checked.

# Why refusing is the right behaviour

A machine that cannot tell success from failure, and reports success anyway, is
a liar. The expensive failures in this repo are exactly that:

- a `.tar.gz` goal burned 95 seconds, then reported PASS **with an empty plan**
- a goal naming an existing file spent 48.7 seconds, 442 actions, 5,046 subprocesses
- `md5sum` was accepted as the answer to "the different lines of a.txt"

Every one of those was a pass that meant nothing. Ten refusals are cheaper than
one lie, because a lie is remembered forever and a refusal is not.

# What IS real

1. **Learn once, remember forever.** Compress a file, and the exact command is
   stored as a recipe. A *new process* recalls it in 0 actions and **re-verifies
   it**. That is your thesis, and it works.
2. **3 of 13 checkable tasks close on the first try**, in about 26 milliseconds.
3. **The absence of this is not a learning failure.** Learning was never the limit.

# What the limit actually is

**Verification, not learning.**

Your thesis says: run it once, it learns forever, so we solve everything.
The first half is true. The second half needs a piece the thesis skips —
the machine must be able to tell, by itself, that the one time it ran it
**actually worked**. Where it can (3/13), it learns permanently. Where it cannot
(10/13) it must not pretend, and so it does not learn at all, because learning
something you cannot check means memorising a guess.

# Why the model does not simply try anyway

There is a hard rule in the code, with a test named after it:

    test_curriculum_explore_does_not_run_programs
    -> discover.assert_not_called()

The curriculum is **forbidden** from running programs. Execution lives behind an
admission gate. Two test files currently disagree about where that line sits —
one expects the curriculum to close these goals, the other forbids it. That is a
real open contradiction, not a bug I can quietly pick a side on.

# The three things that would move this

1. **Make more goals checkable.** Every new verifier turns an impossible task into
   a permanent one. This is the highest-value work available, and it is the real
   answer to "why not all computer use".
2. **Settle the boundary contradiction** — may the curriculum execute, or not.
3. **Widen the *seeing*, not the learning.** GUI reach is 56.3%; the losses are at
   locating the right element, not at knowing what to do.

# Sentient

No.
