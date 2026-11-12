# Mission ASTRA-VERIFY-FILE-QUESTION-TAUGHT-WORDS-001

**Row:** `file.question.taught_words.v1` (adapter `canonical/runtime/bound_capabilities/file_question_taught_words.py`).

**Claim.** A question about one file is answered only when every word of the sentence is accounted for by words
whose meaning was taught through example answers (`canonical/runtime/taught_words_v1.py`, lessons in
`TAUGHT_WORD_LESSONS_V1.json`). The answer is the value of the operation those words make. Any other sentence is
refused and the refusal names the word. The row never writes and never starts a process.

**How it is checked** (`canonical/runtime/verify_taught_words_provenance_v1.py`):

1. The stored lexicon is exactly what the tracked lessons give when learned again.
2. Every lesson the learner accepted is reproduced on its own example files.
3. A world is built by the verifier, so every expected answer is known by construction and written as a literal.
   The row is reached through the real dispatcher with its declared expectation, so the door's own recomputation
   (`taught_words_check_v1.py`, which shares no code with the producer) runs on every case. The cases include
   combinations of taught words that no lesson shows.
4. Where `wc` and `grep` exist, the answers are compared with theirs.
5. Sentences with an unknown word, with a negation, with two files, with a path outside the repository, with a
   directory, with a file that is not UTF-8, or with a report path are refused.
6. A reported answer that is off by one is caught by the checker.
7. The producer and the checker agree on every valid operation over the world's texts.
8. No file of the world changes and none is added.
9. A lesson with one example file, and a lesson with a wrong answer, are refused by the teacher entry.

**Independence.** Code-level only. The producer, the checker and the verifier were written in one agent session on
2026-11-11. This is not independent-personnel verification and the receipt records that.

**What the check does not show.** That the operation is what an arbitrary English sentence means. The lexicon ignores
word order and scope, the fifteen operation parts are built in, and the lessons were written by the same session.

**Replay.** `python3 canonical/runtime/verify_taught_words_provenance_v1.py --check`
