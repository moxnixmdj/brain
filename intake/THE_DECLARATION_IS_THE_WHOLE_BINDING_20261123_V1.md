# The declaration is the whole binding

**Round 7. The 786 operations called "unknown" were not unknown. They were unread.**

Date: 2026-11-23 · Base: `bbbe6af2` (PR #7054) · Branch: `arena/67f07f33-brain`

---

## 1. What was open

Round 6 ended with a triage: of the operations the census could not bind, **786** were
`RESOLVABLE_BY_DRIVING` — the program documents itself, so the fix is ours — and **0**
were `CERTIFIED_EXHAUSTED`. Round 7's job was to drive them.

The number to beat was not 786. It was the sentence *"there are 786 things this machine
does not know."* A census that says that has already conceded that capability is a
matter of coverage. Round 7 tested the opposite hypothesis: that these are a **small
number of assumptions**, each contradicting a line the program had already printed.

## 2. Five assumptions, each found by reading one error message

A 120-row sample of openssl's 558 failures, with stderr attached, contained no 558
separate unknowns. It contained this:

```
62   Invalid command 'cms=out.bin'
16   No operation option (-encrypt|-decrypt|-sign|...) specified
 9   Warning: recipient certificate file parameters ignored for operation ...
11   Can't parse "in.txt" as a number
11   Use -help for summary
```

**1. `bind` assumed `argv[1]` is the flag.** True for `cp --backup`. False for
`openssl asn1parse -in`, where `argv[1]` is the subcommand — so the binder wrote
`openssl asn1parse=out.bin`, giving the subcommand a value, and openssl answered
`Invalid command`. A flag is identified by *being* the flag: a lookup, not a position.
Four sites made the same assumption.

**2. A usage line's own name and `[options]` are not operands.** `openssl asn1parse -h`
says `Usage: asn1parse [options]`. Parsed, that became `['ASN1PARSE', 'OPTIONS']`, so
every openssl subcommand declared a phantom operand and the binder appended a seed
filename the program refuses with `Use -help for summary`. The bracketed path already
skipped `OPTION`; the bare path did not; and `OPTION...` (tar's spelling) missed both.
One declaration, read three ways. **143 of 258 sampled subcommand failures.**

**3. `-offset +int` declares a signed integer, and `+` was outside the regex.** The spec
never parsed, the placeholder came back `None`, the binder fell through to a filename,
and openssl said `Can't parse "in.txt" as a number`. The `+` is half the declaration.

**4. A declared path flag is not an artifact and nothing else.** `openssl x509 -h`
prints two lines:

```
 -in infile       input file
 -out outfile     output file (output format is always DER)
```

The binder read the second and never the first, so `openssl x509 -out out.bin` read an
empty stdin and wrote nothing. Half an action — which is exactly what the planning
literature says cannot be planned with, only here it was half an *invocation*.

**5. A passphrase is declared too.** **108** of the remaining failures were the program
printing `enter AES-128-CBC encryption password:` and waiting. The same help text
declares `-k val  Passphrase` and `-passin val  ... pass-phrase source`. The flag *and
the form of its value* are both in the declaration — bare phrase versus `pass:` source.

And one defect the five share: **`census()` parsed each subcommand's contract and then
dropped it**, handing every sub-operation the *parent's* flags. `openssl -h` prints no
`-offset`. So the declaration the binder needed was already in hand and thrown away.

## 3. What the fix is, in one sentence

**Read the declaration that describes the operation, and take every part of the
invocation from it** — the flag by lookup, the value's type from the spec, the value's
*form* from the description, the input from the flag the program says is its input, the
passphrase from the flag it says is its passphrase.

No table of programs. No table of flags. The words `input file` and `Phrase source` are
the program's own, and `carrier()` was already reading the description exactly this way
for the artifact role — the input and passphrase roles are the same mechanism pointed at
the lines that were being skipped.

## 4. Measured

Same script, same seeds, 15 programs; BEFORE is the shipped module checked out on the
same machine and run by the same script.

| | DOOR | FAILED_NO_EFFECT | NO_EFFECT | LITTER |
|---|---|---|---|---|
| before | 33 | 759 | 192 | 1 |
| after | **57** | **641** | 278 | 9 |

Per program, doors before → after: `openssl` **0 → 24**; `cp` 2→2, `mv` 2→2, `rm` 7→7,
`gzip` 12→12, `tar` 4→4, `install` 3→3, `sort`/`find`/`sed` 1→1, `grep`/`zip`/`ln`/
`touch`/`dd` 0→0. **Zero regressions.**

On the round-6 fleet of 20 programs: **DOOR 33 → 57**, **UNBOUND 786 → 676**, sensors
568 → 284. `UNDETERMINED` rose 0 → 8 because 14 `SLOT_UNSUPPLIED` operations are now
correctly named as needing a construction rather than being silently counted as
driveable.

## 5. Why the litter is litter

Nine rows end in a changed tree with a failed command. Four are the `-param` family:
`openssl asn1parse -out=out.bin` **creates `out.bin` before it reads its input**, so a
refused request still leaves a file. Verified by running each with and without `-in`:
the file is left in both cases and the command exits non-zero having done nothing the
goal asked for. Four are `-writerand` doing the same. One is `tar --delete`. The census
must never credit a run that refused the request and left a file behind, and it does not.

## 6. What this does not say

- The remaining **676** are not close. 654 are `DROVE_IT_WRONG` on the 20-program fleet,
  and openssl's largest cluster has moved from *binding* defects to real
  **preconditions** — an offset into a DER stream, a certificate to verify against.
  Those need state built before the door exists, which is a different mechanism.
- The `-out`-reads-stdin composition pays only with a **type-matched** seed: with
  printable text it moved nothing, with a real DER certificate it moved openssl 12 → 14.
  The default trial seed is printable text, so the standard measurement
  *understates* it. The next question is whether the seed's type belongs in the
  declaration join, since `-inform PEM|DER` is the program naming the form it expects.
- `_declared_passphrase` writes a literal passphrase into a trial's own temporary tree.
  That is a fixture, never a credential; nothing is persisted and no real key is touched.
- Authority is `NONE`, the run is sandbox-only, and independent verification is **OPEN**.

## 7. What round 7 answers to round 6's four open questions

1. **Learn everything, or be goal-directed?** Neither, as posed. Read **what the program
   declares**: it is bounded (the help text), it is exactly what binding needs, and it is
   the same on every machine that ships the program.
2. **What should be saved?** Not the raw action — environments change, and the round-6
   receipt already showed why. **Save the declaration.** `-in infile  input file` was
   true before this round and will be true in an environment that has never existed.
3. **Scan the whole environment and fetch only the unknown?** The scan is not a matter of
   coverage. The same 20 programs produced 33 doors when the declarations were misread
   and 57 when they were read, with no new knowledge fetched. The quantity to reduce is
   not "what is unknown" but "what is unread".
4. **What generalises?** The declarations generalise; the invocation does not. That is
   why the mechanism is a reader of programs, and not a record of commands.
