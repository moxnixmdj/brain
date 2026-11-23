# Ask the subcommand before you call it unbound

**Round 6. What the machine "does not know" was mostly a question it never asked —
measured, not argued.**

Date: 2026-11-23 · Base: `0bbdf5c0` (PR #7053) · Branch: `arena/9db0fc92-brain`

---

## 1. The idea under test

> *"All he should do is scan everything in the environment, then retrieve from memory
> what he knows and what he doesn't know. What he doesn't know, he should get instantly
> from the web."*

Every half of that already existed in the tree — and that is the finding, not a comfort:

| half | module | state before this round |
|---|---|---|
| scan + classify | `tool_census_v1` | 76 doors, 2,134 declarations |
| instant knowledge | `local_guide_v1` → `jit_knowledge_v1` | wired into `perfect_algorithm_v1`, completeness-gated |
| ranks what it does not know | `ignorance_ledger_v1` | **82 gaps, 0 resolved** |
| the ask→close→did-it-help circuit | `ignorance_loop_v1` | assembled, for the financial-QA path only |

Nothing joined them. So the deciding quantity — **what it actually does not know** — had
never been measured. That is what this round measured, and the answer changed the design.

## 2. Three defects, each found by disbelieving a number

**1. One contract per program.** `_own_text(prog)` asks `prog -h` and nothing else, so a
program with subcommands was read from its parent text and every child operation judged
against it.

```
openssl --help           -> no usage line, 0 flags, 38 subcommand candidates
openssl asn1parse -help  -> "Usage: asn1parse [options]" and 9 flags
```

Measured: **38 of 38** admitted subcommands print their own `Usage:` line, and all 38 were
reported as though they had none.

**2. A failed run called a clean one.** `verdict = "NO_EFFECT"` was assigned to any run
that left the tree alone, whatever its exit status — and the census's own wording for that
verdict is *"exited cleanly and moved nothing: a value was computed, so this is a sensor."*
Measured on openssl: **545 of 676** rows carried exit 1 and every one was described as
having exited cleanly. A program that refused the invocation has answered nothing.

**3. The parent's documentation gap applied to the child.** `classify()` derived one
construction reason from the parent contract and used it to move every `NO_EFFECT` row to
UNBOUND — the last thing standing between 118 genuinely-answering openssl operations and
being counted as sensors.

## 3. Measured effect

Same 20 programs, before and after, by reproduction rather than by memory
(`_before()` deliberately restores the old verdict rule):

| | DOOR | SENSOR | UNBOUND |
|---|---|---|---|
| before | 33 | **880** | 104 |
| after | 33 | **198** | 786 |

**`sensor_delta = 682`.** That is the headline: **682 operations were being credited as
"the machine can compute a value here" when the run had failed or its own document had
never been opened.** A number that flattered the machine fell by 682. No door was lost —
the control that matters, because a change to binding that costs a door is a regression
(measured: one such rule was written, cost `cp` a door, and was reverted).

## 4. What "does not know" turns out to be

```json
{"DROVE_IT_WRONG": 772, "SLOT_UNSUPPLIED": 14,
 "NOT_ASKED": 0, "NO_DOCUMENT": 0, "NEEDS_CONSTRUCTION": 0}
```

Not 786 unknowns. **One kind with 772 members**, and its name is precise: we handed the
program an argument it refused. For openssl that is `-inform in.txt` where the usage line
says `-inform PEM|DER` — *"Invalid format 'in.txt' for option -inform"*.

The unit of ignorance is therefore **a question, not an operation**, and its price is
measured rather than fitted:

```
worth(question) = how many operation verdicts this one question decides
```

The worst offender needs **three asks** to cover most of its 558 operations
(`openssl x509 -h` decides 59, `openssl cms -h` decides 57, `openssl pkcs12 -h` decides 49).

## 5. The axis the kinds were missing — from the frontier, earned by measurement

**LLM-IDEA (arXiv 2610.11253)** triages a plateau three ways — capability limit /
resolvable within the design class / certified exhausted — because an agent that cannot
tell *"I have not looked yet"* from *"no further search will recover this"* either refines
against a target its data cannot constrain or abandons something one question would have
settled. That axis was **added**, decided per kind from evidence:

```json
{"RESOLVABLE_BY_DRIVING": 786, "RESOLVABLE_BY_ASKING": 0,
 "CERTIFIED_EXHAUSTED": 0, "UNDETERMINED": 0}
```

**Not one doubt in the tree is worth abandoning.** Every one is rescuable, and all but 14
are rescuable by driving. That is a verdict the tree could not previously state.

Two further frontier results shaped it, and both were beaten on cost rather than copied:

- **KBD (arXiv 2603.21022)** discovers a knowledge boundary with an **RL policy rewarded
  by entropy reduction**. `worth(question)` is the same quantity in the discrete case —
  the count of verdicts one question decides — so the ranking is *measured*, with no
  policy and no parameters.
- **OSExpert / skill-boundary (Mar 2026)** reports +20% performance and 80% efficiency
  from exploring before acting, and runs that loop inside a **120B model**. The loop here
  is deterministic at **0 model calls**; what it lacked was OSExpert's boundary report,
  which is now the kind table.

## 6. The doubt now survives the process

`index_capability_evidence_v1` describes the ledger as *"ranks what it does not know by
expected value"* — and **nothing on the census path had ever written to it.** 786 unbound
operations were re-derived from nothing on every run.

`note_to_ledger()` writes each kind with its measured price. Verified in a temp ledger:
`open_after: 1`, persisted to disk. One honest wrinkle, recorded rather than hidden: the
ledger ranks by `p_useful/(1+cost)`, so a doubt blocking 772 operations ranks *below* one
blocking 2, because cost is a penalty there. `what_to_ask()` is the ordering used for
action, and the receipt reports both rather than merging them into one dishonest number.

## 7. Honest limits

- **Asking correctly does not make an operation a door.** 786 operations are still
  unknown, now for a true reason. The claim is that the doubt is stated correctly and
  cheaply, not that it is closed.
- A kind is a *belief about why* a verdict is unknown, decided from documents and real
  exit codes — not a proof of what the operation does.
- No operation outside the seeded directory was attempted, so a program whose required
  slot needs a file elsewhere is still `DROVE_IT_WRONG`.
- A program with no help text at any scope cannot be asked at all, and is reported
  `NO_DOCUMENT` rather than guessed at.
- `_VALUE_SLOTS` remains a hand-written name list. Generalising it was tried, **measured
  wrong** (cost `cp` a door), reverted, and pinned by a test.
- Producer-run sandbox only. **No independent identity has re-run any of it.**

## 8. What is not claimed

`truth.achieved` stays **false**. What is real: 682 false sensor credits removed, the
unknown collapsed to five evidence-backed kinds, the rescuable/exhausted axis added, and
the doubt made to persist. What is not: closing the 786, reading a *goal* from words, any
benchmark score, and independent verification — which remains **OPEN**.
