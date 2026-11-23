# Is the saved form sufficient, or merely small?

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 74 tests pass

> "Saving his exact experience must be in a very sufficient way, not just saving the exact
> experience in a dumb way."

Small is easy to fake. Sufficiency is testable, and this is the test.

---

## The test

Build a store by asking every program on a host. Then, **in a fresh process, with only the
store and the host**, rebuild every answer using nothing but `scan()` + `known_answer()`.
Compare against what the asking pass reported.

```
host            /usr/bin
answers         125  (decompress 32, compress 41, stdout 52)
rebuilt         125
sound           true      no invented answer
complete        true      no lost answer
probes at rebuild   0
store           25,768 bytes
verdict         SUFFICIENT
```

**No probing at all on the rebuild.** Every answer came from the store plus the 48 ms scan.

## Why a fresh process, not a function call

A function-call round trip can pass state through a live Python object that a restarted machine
would never have — the same error as a cache that only works warm. The rebuild reads the JSON from
disk in a separate interpreter.

## Why the check must be able to fail

A sufficiency test that cannot fail proves nothing. Five tests build the failing cases
deliberately:

| case | caught as |
|---|---|
| an answer dropped | `lost` — `complete` fails |
| an answer added | `invented` — `sound` fails |
| the right name with the wrong flag | **both** `invented` and `lost` |
| the rebuild calling `ask_role`/`resolve` | forbidden by test — it would hide a gap by probing |

An invented answer is worse than a lost one: it is indistinguishable from a measured answer until
it is used, and by then it has already acted.

## What this settles, and what it does not

**Settled:** the store is a faithful, sufficient summary of a pass, and it is *not* a
transcription. 25,768 bytes rebuilds 125 answers exactly. The generality claim the user asked for
— "generalized, not literal replay" — is met *for this environment family*, by construction
(vocabulary + read-set) and by test (sound + complete + zero probes).

**Not settled:** this is one host family and one closed vocabulary of five role words. The store
is sufficient *for the questions it knows how to ask*. It says nothing about a question it has
never been asked, and nothing at all about a GUI.

That limit is the next bottleneck, and it is the last one that matters: **the vocabulary of
questions is chosen, not derived.** A general environment needs the question derived from the goal
and the artifact. Until that is done, "sufficient" means sufficient for this family.

`truth.achieved` remains `false`.
