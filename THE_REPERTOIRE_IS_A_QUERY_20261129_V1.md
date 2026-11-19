# The repertoire is a query, not a possession: 437 programs, 4,621 options, 47 seconds — and not one sampled option is an action

*2026-11-29. The question, taken whole: instant learning and instant learning in new environments are solved, so
give the model the smartest actions, let it experience each once, and it owns any computer permanently. Is that
true, what is wrong, what is real, and what is the smartest thing to do?*

## What the tree had already settled, so this round does not re-argue it

Three rounds closed the parts of computer use a machine can supply. A demonstrated action replays exactly, 30 of
30. A condition is not in the trace (0 of 10 named), but the program's own check mode is, for 5 of 10 actions,
exact on the input and blind to the world. The successor of an action is not predicted but **had** — copy, run,
read the exit status — and a planner that does that repaired 5 of 6 real damaged repositories with
`transitions_predicted = 0`.

What none of them answered is where the *actions* come from. r27 said so in its own essay: "the ten git actions
here were written by me; nothing in this round discovers that `git rebase --abort` exists." The owner's claim
turns on exactly that: gather the actions, experience them once, keep them forever.

## Why "keep them forever" is the wrong frame, and it is not a matter of taste

2026 measured the cost of keeping experience. Moving it into memory does not avoid the stability–plasticity
dilemma, it relocates it to retrieval: the design that adapts best to a new task is the one that forgets an old
one most, and negative transfer hits the hardest cases hardest (arXiv 2604.27003). Self-evolving agents that
rewrite a shared prompt or workspace interfere with unseen tasks and overwrite earlier knowledge as the stream
drifts; no evaluated method achieves both plasticity and stability (arXiv 2610.25858).

A **query** has none of those failure modes. It cannot forget, cannot drift, cannot collide with another query,
and stores nothing — because it is re-derived from the machine at the moment of use. Its currency is executions.
So the question is arithmetic, and this round pays it:

> what does it cost to RE-DERIVE what the machine can do, versus what it would cost to OWN it?

## The catalogue, read off a real machine, in 47 seconds

No table in the source, no program named in advance: the shell's own list of binaries, each asked for its own
page, the page parsed by a declared grammar for option declarations, and the branches of each program's own page
followed when a declared need's words reach them.

| what | number |
|---|---|
| programs that answered | **437** |
| pages read (programs plus branches) | 492 |
| option lines printed | 13,250 |
| distinct options | **4,621** |
| catalogue size | 1,147,792 bytes |
| time to re-derive it | **46.6 s** |
| parameters stored | **0** |
| model calls | **0** |

That is the entire action vocabulary of this machine, available on demand, for three quarters of a minute, with
nothing to keep. It is also the first real defect this round found **in our own tree**: `discover_v1.binaries()`
returns 400 names and its cap is *alphabetical*, so `git` — and every program after it — was invisible to the
project's own discovery organ. A discovery organ that truncates alphabetically cannot see the second half of the
machine. Asking for the uncapped list put 437 programs in view where 115 had been.

## Result 1: an option is not an action, and the catalogue cannot make it one

164 sampled options were executed against a real state — a real git repository with a real archive, a real gzip,
a real patch — each option bound to a real object from that state whenever the program itself complained of a
missing operand.

| what happened | number |
|---|---|
| executed | 164 |
| **accepted by their own program** | **80** |
| **changed a byte of the state** | **0** |
| needed an object bound from the state | 44 |

Zero. Not one option, run by its own program against a real object, changed anything. The reason is not a
measurement artifact and it is not subtle: **a printed option is a modifier, not an action.** `cut -b` selects
bytes, `touch -c` updates a timestamp the content hash does not see, `gzip -f` reads standard input because
nobody told it what to compress. The page never says which of its programs is a *mutator*, and it never binds the
object — `gzip -f payload.txt` and `gzip -f` are different acts, and only the state knows the difference.

So the catalogue hands you **verbs and knobs**. The object comes from the state. Neither comes with a purpose.

## Result 2: the catalogue cannot tell which questions are its own

Twelve needs were written before the run, six that a shell can serve and six that nothing on a machine can. The
catalogue was asked the same way a person would ask it, and its own words were ranked lexically against each.

| needs | median top-3 page score |
|---|---|
| a shell can serve it (undo a merge, put back stashed work, check an archive, stage changes…) | **7.55** |
| nothing can serve it (buy milk, email the landlord, will my colleague approve…) | 5.36 |
| a threshold that separates them | **NONE** |

The top answer for "give up a merge that went wrong" was `lzfgrep`. The scores overlap completely: the machine
answers every question with equal confidence and cannot say *this one is not mine*. That is not a defect of the
ranker that a better ranker fixes — the median gap is 2 points and the overlap is total; what is missing is the
step from words to purpose, which is comprehension, not lookup.

## What is real, and what is not

**Real.** The vocabulary is free and instant: 437 programs, 4,621 options, 47 s, zero parameters, read off the
machine and never stored. The successor of an action is free (r27). Applicability is askable for half the
actions (r28). None of the three needs a parameter, a training run, or a memory.

**Not real.** That gathering actions and keeping them is the path to owning a computer. Three things are outside
the catalogue and none of them is an action: the **object** (which file, which branch, which commit — the state
supplies it), the **check** (whether the effect is the one wanted — r28's traps: the check sees the input, not
the world), and the **purpose** (which of 4,621 options, on which object, for what end). The measurements above
are the arithmetic: 0 of 80 accepted options did anything, and 0 of 12 needs were distinguishable from the ones
the machine cannot serve.

And "permanently" is the wrong property to want. What would be permanent is exactly what goes stale — a stored
catalogue of a machine that has since changed, a memorised condition whose environment has moved, a check whose
input is valid and whose world refuses. A query cannot go stale by construction, which is why the right design
is to keep **nothing** and re-derive: the same "best part is no part" that deleted the world model in r27 deletes
the repertoire here.

## The single bottleneck

Not learning speed, not the action space, not the planner. **The purpose-bearing command line**: which program,
which object, which end. The machine supplies the first, the state the second, and nothing supplies the third.
This is also where the frontier's own failures live: OSWorld 2.0's best binary completion is 20.6% over 108
multi-hour workflows, agents spend under 7% of their budget on self-repair, and the failure axes are lost
constraints, missing mid-task updates and skipped verification — memory and verification, not action competence
(arXiv 2606.29537).

So the smartest next thing is not to gather more actions or to learn them faster. It is to make the **purpose**
executable: a statement the owner makes and the machine can check, so that "which of these 4,621 options, on
which object" stops being a matter of taste. That is the same conclusion r27 reached from the other side, where
three successive goals were satisfiable by destroying the work.

## What this round's own criteria say, including the ones that failed

Declared before the run: K1 the machine describes itself (met: 437 programs, 13,250 option lines); K2 an option
is not an action (met: 80 of 164 accepted); K3 pages that advertise an effect produce one (**failed**: 0 of 6);
K4 an advertised check is real (**void** — with nothing mutating, a check cannot be told from doing nothing);
K5 an undo restores the tree (**void** — no inverse pair could be formed); K6 a query is cheap (met: 46.7 s,
1.15 MB); K7 the catalogue cannot refuse (met: no separating threshold); K8 nothing hand-written (met).

Four met, one failed, two void. The failure and the voids are reported, not hidden, because they are the same
finding from three directions: **on a machine, a list of options is not a repertoire of actions.** The executed
sample is a stratified stride over the catalogue — half the pages advertising an effect, half not — so it is not
a census of every page; a page it never reached is unmeasured, not unusable. Argument synthesis is a separate
problem (r22: the caller passes variables), and this round binds only the object a program explicitly asks for.

## Reproduction

```
python3 canonical/tools/the_repertoire_is_a_query_v1.py \
    --receipt canonical/verification/THE_REPERTOIRE_IS_A_QUERY_20261129_V1.json
.venv/bin/python -m pytest canonical/tests/test_the_repertoire_is_a_query_v1.py -q
```

Authority **NONE**. One machine, one producer, sandboxed by copy, no model, no parameters, no network at run
time. Schema `BRAIN_THE_REPERTOIRE_IS_A_QUERY_V1`.
