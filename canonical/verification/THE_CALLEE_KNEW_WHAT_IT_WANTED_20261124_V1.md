# The callee knew what it wanted: one blind fix, honestly scoped

**2026-11-24.** Tool: `canonical/tools/pass_what_the_callee_wanted_v1.py`.
Receipt: `canonical/verification/PASS_WHAT_THE_CALLEE_WANTED_20261124_V1.json`.

## The result

On `jinja d05bd3858c` — one of the six rows no engine could enter — a rule that knows
nothing about the human fix produced it exactly, and it verified.

The rule: at the frame that raised, take the `Call` on that line; let `M` be the
parameters the callee declares minus those the call supplies; let `L` be the names live
in the enclosing scope; if `M ∩ L` has **exactly one** element, append it. Require the
fault to disappear and the existing suite to stay green.

Fault capture, from the parent tree with no reference to the patch:

```
fault frames in filters.py: [('func', 1783), ('<lambda>', 1788), ('select_or_reject', 1803)]
ERROR: TemplateRuntimeError Attempted to invoke a context test without context.
```

Derivation:

```
callee  context.environment.call_test
params  ['self','name','value','args','kwargs','context','eval_ctx']
not supplied: ['value','context','eval_ctx']
live in scope: ['context']
-> single candidate: context
```

Proposal, against the actual human edit:

```diff
-            return context.environment.call_test(name, item, args, kwargs)
+            return context.environment.call_test(name, item, args, kwargs, context)
```

Identical. Verification:

| check | result |
|---|---|
| issue-derived oracle on the parent | **1 failed** (`Attempted to invoke a context test without context`) |
| issue-derived oracle on the patched tree | **2 passed** (fail-to-pass + pass-to-pass anchor) |
| full existing suite on the patched tree | **905 passed, 0 failed** |
| human fix used to choose the patch | **no** |

This is the first row in this repository that goes from *issue text* to *verified patch*
with zero model calls, where the oracle and the repair both came from mechanical
derivation.

## The honest scope, which is narrower than the result suggests

A first version of the rule ignored the fault and fired on arity alone: **402 times
across 11 repos**, and every instance inspected was wrong — `dict.pop(default=...)`,
`astuple(recurse=..., filter=...)`, `attrib(kw_only=...)` are optional parameters
omitted on purpose.

Restricting to a single live candidate does **not** fix that: it still fires **546 times
in 139 files**. Arity is not evidence, no matter how it is narrowed.

**What makes the rule sound is the raised exception, not the syntax.** Gated on a fault
at that exact line, it fires rarely and it was right on the one row I tested. So the
claim is:

> at a frame that has already raised, the unique live parameter the callee declares and
> the call omits is a correct repair, and it can be verified.

Not: > the rule finds bugs by inspection. It cannot. It is an *oracle-consumer*, and it
needs a failing run to exist first — which is exactly why the oracle work had to precede
it.

## What this does and does not cover

Covered: the "failed to thread a live dependency" fix class. The callee already accepted
the parameter with a `None` default and raised when it was absent; the caller had the
object in scope and did not pass it.

Not covered: `urllib3 77fa67aaf2`, where the fix is one character in a module-level regex
constant (`([0-9]{0,5})` → `(0*([0-9]{0,5}))`). There is no call to repair and no live
name to pass; the defect is a literal's internal structure. The guard-rule engine cannot
see it either — its 44 guard sites contain no regex and the nearest branch is correct
code reading a faulty string. That row now has an oracle and no generator, and I am
recording it as such rather than as a near-miss.

## Ledger

| row | oracle | generator | end-to-end |
|---|---|---|---|
| `d05bd3858c` jinja | issue prose, fail-to-pass verified | blind rule, exact human patch | **SOLVED** |
| `77fa67aaf2` urllib3 | issue prose, fail-to-pass verified | none — constant refinement | not solved |
| other 43 rows | 2 more reproducible, rest prose-only | unchanged | unchanged |

Corpus-level: **20/41 attemptable solved** (19 union + `d05bd3858c`), up from 19.
The honest headline stays split: 20/45 = 44.4% of rows are now reachable with an oracle
derived from issue prose plus two mechanical rules, and that is still far from §6.
