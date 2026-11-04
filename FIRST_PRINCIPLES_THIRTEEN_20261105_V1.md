# First principles, pass thirteen — S8 failed, and the failure was worth more than the hypothesis

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. The hypothesis, and its refutation

Pass twelve ended with S8: *route producers by failure kind instead of racing them all.* The reasoning
was sound — a `NameError`, a `TypeError`, a timeout and a wrong value need mutually exclusive repairs,
so the kind should pick the family.

**It is measurably false on this system.** Two reasons, both fatal:

**First, the board has no variety to route on.** Every one of the eight shapes I classify fails as
`VALUE`:

| shape | kind | operator_family | deterministic_ast |
|---|---|---|---|
| binop | VALUE | solved @0 | solved @0 |
| cmp_gte | VALUE | solved @0 | solved @1 |
| mul | VALUE | solved @1 | — |
| mod | VALUE | solved @4 | — |
| augassign | VALUE | solved @0 | — |
| whileacc | VALUE | solved @0 | solved @3 |
| floordiv | VALUE | solved @3 | solved @0 |
| offbyone | VALUE | — | solved @1 |

A router over one category is an identity function.

**Second — and this is the real finding — the non-value kinds have no producer at all.**

| kind | world | operator_family | det_ast | stun_guard |
|---|---|---|---|---|
| BINDING | misspelled name | — | — | no candidates |
| SIGNATURE | arity mismatch | — | — | no candidates |
| SYNTAX | missing colon | — | no candidates | no candidates |
| TERMINATION | non-terminating loop | **solved** | — | — |

Three of four non-value kinds are **unsolvable by every producer in the system**. So S8 was asking
which producer to try first in a situation where the answer was always "none of them". The
hypothesis was not wrong about the *idea* of routing; it was wrong about the *layer* — routing
organises capability that exists, and cannot substitute for capability that does not.

That distinction is the whole of this pass. Twelve passes were spent adding producers to a list;
this one found that the list's shape was never the problem.

## 2. What was closed, and how honestly

The tractable third of the gap is `BINDING`. A `NameError` names the offending identifier, and when
that identifier is a near-miss of something the module already defines, the repair is that
substitution. `binding_repair_v1.py` does exactly that, at real token spans — via `tokenize`, so a
string literal that merely *mentions* the name is never rewritten (a regex rewriter was measured to
corrupt exactly that case in pass ten and is not reused here).

It declines rather than guesses, twice:
- when the missing name **is** already defined — that is a scope or ordering problem, and no
  substitution from the file's vocabulary addresses it;
- when nothing clears the similarity floor — `totl` against `{a, b, f}` scores 0.0, and emitting
  `totl -> a` is noise dressed as a hypothesis.

Measured live, creature against creature, six interleaved runs each:

| | repaired |
|---|---|
| BEFORE (`a44028ad`) | **0 / 6** |
| AFTER (producer wired) | **6 / 6** |

A second, structurally different world (a loop-body typo) repairs after and not before. A world whose
missing name exists nowhere is correctly left alone in both.

## 3. A measurement that lied, and how it was caught

My first A/B said *unchanged* on all three worlds. The same code, run once interactively, repaired the
world. I did not pick the answer I preferred — I re-ran six times each way, interleaved, and got the
6/6-versus-0/6 split. The first script had been reading the file through a `TemporaryDirectory`
context manager that had already deleted it, so `read_text()` raised and the comparison silently
became "equal to itself".

Then a second discrepancy appeared: three worlds in one loop, all unchanged; the same world alone,
repaired. That one is still unexplained. It reproduced neither in six isolated runs nor four inline
runs, and I am recording it as unexplained rather than inventing a cause for it, because an invented
cause is how a real intermittent bug survives.

## 4. What the honest scoreboard says now

| kind | before this pass | after |
|---|---|---|
| VALUE | 7/8 solved | 7/8 |
| TERMINATION | 1/1 | 1/1 |
| **BINDING** | **0/1** | **1/1**, live, 6/6 against 0/6 |
| SIGNATURE | 0/1 | **0/1** |
| SYNTAX | 0/1 | **0/1** |

Two of the three remaining holes are still holes. Naming them is the point: `SIGNATURE` needs a
producer that can reconcile a call site with a definition (add the argument, or fix the call);
`SYNTAX` needs one that can repair a file that does not parse, where no behavioural screen is
available until it does — a genuinely harder class, because the oracle cannot run.

## 5. Next falsifier, stated so it can fail

**S9.** Build a `SIGNATURE` producer: from a `TypeError: f() takes N positional arguments but M were
given`, propose (a) adding the missing parameters at the definition with a default, and (b) removing
the surplus arguments at the call site — each as a real AST edit, both screened by execution. Measure
solved-rate on five arity worlds and probes-to-fix against the current total of **zero candidates**.
If it does not beat zero, the failure-kind diagnosis is decorative and the channel should be reported
as such rather than dressed up as a roadmap.

## 6. Standing bar

The creature is different at the end of this pass than at the start in a way that is checkable
without trusting me: worlds it could not repair before, it now repairs, six times out of six, with
the previous commit as the control. One capability, one class, honestly bounded — and two named holes
where the answer is still "nothing here can do this."
