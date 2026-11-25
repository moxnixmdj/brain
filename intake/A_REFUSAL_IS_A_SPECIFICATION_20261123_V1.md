# A refusal is a specification

**Round 8. The precondition was never unknown. The program states it, in the one channel nobody reads.**

Date: 2026-11-23 · Base: `202d53c1` (PR #7055) · Branch: `arena/7c6754ec-brain`

---

## 1. §3 verdict, stated before the build

The user's core hypothesis was: *we already solved instant learning in arbitrary
environments; the agent should scan, ask what it does not know, and fetch it.* Round 7
tested half of that and the half that survived was not the half claimed. This round settles
the rest.

| claim | verdict | evidence |
|---|---|---|
| The agent can scan an arbitrary environment and say what it knows | **TRUE, with a correction** | The census reads 2,134 declarations from 20 programs with no table. It can say what it can *do*. |
| What it "does not know" is a knowledge gap to fetch from the web | **FALSE, and this was the real bottleneck** | 786 "unknown" operations were 5 false assumptions about the program's own help text (round 7). The remainder diagnosed as PRECONDITION turned out to be 6 sentence forms the program prints **when it refuses** (round 8). Unknown was never missing knowledge; it was unread text. |
| Instant knowledge from the web is the route to new environments | **UNPROVEN as stated; not needed for this mass** | Nothing fetched from the web moved a door in rounds 7 or 8. Every door came from a local string. |
| One experience, learned permanently | **TRUE for the thing worth learning, FALSE for the action** | A saved command expires; `world clause -> resolve with the program's own initialiser -> paid` does not. Measured 435 times. |
| Therefore the remaining blocker is capability | **FALSE** | The dominant remaining blocker is **reading**, then **state**. In git's case one sentence accounted for 435 failures. |

**The real limiting factors, in order:**

1. **The refusal is unread.** Not knowledge, not model capacity, not planning. Six sentence
   forms, 435 of one of them inside a single program.
2. **The environment's state, not its contents.** `git add` fails 435 times because a
   *world* is absent, and the program that needs it also ships the operation that creates
   it. No amount of scanning file contents finds that.
3. **The oracle is half-blind.** A file-only digest cannot see `.git/` appear. The census
   has this same defect and it is recorded below, unfixed, rather than quietly patched.

## 2. Why we cannot just "let it experience the actions once"

Because **the action is the wrong unit of experience**, and this round is the measurement of
what the right unit is. git's 480 refusals contain 435 copies of one sentence. Learning 435
commands would have learned nothing; learning that `not a git repository` is answered by the
program's own `init` learned everything the 435 needed, in one clause, and it will be true
in a repository layout that does not exist yet.

The frontier makes the opposite bet. PALADIN, Tool-Reflection-Bench and ToolMaze all make
recovery a **learned** behaviour: train a model to diagnose an error and emit a repair. The
published single-shot repair rate for open baselines is **at most 9.6%**. Here the refusal is
*parsed*, so there is nothing to imitate — a `-signature` the program named is a fact inside
the string.

## 3. The design, six clause forms and no tables

Each form is anchored on the program's own words and reduced to one thing to try:

| form | the program's sentence | the repair |
|---|---|---|
| `OFFERED` | `No signature to verify: use the -signature option` | add `-signature` |
| `ENUMERAL` | `No operation option (-encrypt\|-decrypt\|…) specified` | add the first alternative |
| `WITNESS` | `No recipient(s) certificate(s) specified` | supply a file **whose content is that kind** |
| `UNLOADABLE` | `Unable to load certificate` | swap in a file **whose content is that kind** |
| `RANGE` | `Error: offset out of range` | re-bind the declared numeric slot to 0 |
| `CONFLICT` | `You may not specify more than one '-Acdtrux' … option` | remove a member of the group |
| `WORLD` | `fatal: not a git repository (or any of the parent directories)` | run the initialiser **the same program admits** |

Three properties decide whether this is understanding or pattern matching:

- **Placement is part of the repair.** A flag goes where the option parser reads; a value
  goes with the operands. `openssl cms -stream in.txt -encrypt` fails and
  `openssl cms -encrypt -in=in.txt -out=out.bin cert.pem` succeeds. Appending was the first
  version's bug, and it is the same bug round 7 found in the binder.
- **A name is not evidence.** `Unable to load certificate` with `in.txt` in the argument is
  a file whose bytes are text. The witness is accepted only if its **content signature**
  matches (`-----BEGIN CERTIFICATE-----`), which is a format fact, not a program table.
- **Nothing is tried that the program did not offer.** The world action is taken from the
  program's own admitted subcommands. When the clause names a group but not the member,
  the module reports `CONFLICT` and does not pay — honestly.

## 4. Measured, and measured small

Same seed, same script, same machine; the only change is the repair pass.

**Doors 61 → 497.** Zero regressions. And the breakdown, which is the honest part:

| form | read | answered | rate |
|---|---|---|---|
| `WORLD` | 435 | **435** | 1.00 |
| `UNLOADABLE` | 87 | 0 | 0.00 |
| `ENUMERAL` | 18 | 1 | 0.06 |
| `WITNESS` | 14 | 0 | 0.00 |
| `OFFERED` | 12 | 0 | 0.00 |
| `RANGE` | 7 | 0 | 0.00 |
| `CONFLICT` | 4 | 0 | 0.00 |
| unread | 523 | — | — |

**435 of the 436 answers are one clause form, from one program.** The other five forms
answered **1 of 138** on refusals they were never tuned for. Reporting the aggregate alone
would present a tuned reader as a general one, so both numbers are in the receipt.

With a seed that actually contains what the refusals ask for (a real certificate),
`UNLOADABLE` and `WITNESS` pay too: **openssl 24 → 54**, and 465 of 1,036 refusals answered
across nine programs. Both numbers are real; neither is the whole truth without its seed.

## 5. What round 8 answers to the user's four questions

1. **Learn everything, or be goal-directed?** Neither. Read what the environment
   **declares when it refuses you**. That is goal-directed (you only read the refusals your
   goal produced) and it is not the action (it is the missing term).
2. **What should be saved?** `clause form → how it is supplied → did it pay`. Not the
   command. A command expires; "a missing world is created by the program's own initialiser"
   does not. 435/435 is that rate measured.
3. **Scan and fetch only the unknown?** The scan already exists. What it must add is a
   **read of what the environment says when it says no** — that is where the largest single
   gain in the whole project's census work came from.
4. **What generalises?** Declarations and refusal forms. Measured: `WORLD` 435/435.
   Unmeasured: every other form, at 1/138. That gap is the next bottleneck, not a footnote.

## 6. Limits, stated plainly

- The world clause is measured on **git alone**; no second toolchain is installed in this
  sandbox, so `npm init`-style worlds are unmeasured. The mechanism reads only the program's
  own admitted subcommands, so it is not git-specific *by construction* — an argument, not
  a measurement.
- `UNLOADABLE`/`WITNESS` cannot pay on a plain-text seed. The zero is the seed's, and the
  rich-seed run shows the same reader at 22.
- `CONFLICT` is read but does not pay: tar names the group, not the member.
- The oracle blind spot is **fixed in this module only**. `tool_census_v1` still cannot see
  a directory appear; that is recorded as the open item and deliberately not silently
  patched, because changing the census oracle would move round 7's published numbers.
- Authority `NONE`, sandbox only, independent verification **OPEN**.

## 7. The next bottleneck

Not binding, not reading — **state**. The same measurement says it twice: 87 `UNLOADABLE`
refusals with nothing of the right kind to substitute, and 18 `ENUMERAL` modes each waiting
on its own further precondition. The next round asks what an environment needs to *contain*
before the doors exist, and whether that can be composed from the program's own operations
rather than supplied by a seed — which is the same WORLD mechanism, one level down.
