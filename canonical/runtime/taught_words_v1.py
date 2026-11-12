#!/usr/bin/env python3
"""Taught words: word meanings learned from example answers, and file questions answered from them.

What this is
------------
A lesson is one sentence, two or more example files, and the right answer for each file.  Nothing in a
lesson says which operation produced the answer, and no word is given a meaning by hand.  From the
lessons this module works out which word carries which part of an operation:

* for each lesson, every operation it can perform that gives the stated answer on EVERY example file;
* across lessons, a word can only mean something present in every lesson the word appears in, and every
  part of a lesson's operation must be carried by one of that lesson's words;
* it keeps the smallest lexicon that fits all lessons, and a word counts as known only when every
  smallest lexicon agrees on it.

A request is answered only when every word of it is a known word, a structure word, the file, or the
text to look for.  The meanings are put together by type: one thing to look at, filters, at most one
measure, one way to reduce.  Anything else is refused, and the refusal names the word.

Why it exists
-------------
Measured 2026-11-11 (external_probes_20261110/README.md, sections L, N and O).  A lesson stored whole
answers only itself: 0 of 18 other tasks.  A row chosen because it shares words with the sentence gave
13 wrong answers reported as passed in 96 requests.  Thirteen one-sentence lessons taught as words
answered 59 of 59 requests nobody showed, none wrong, because a word learned in one lesson combines
with the words learned in the others.

What it does not do
-------------------
It starts no program and writes nothing when it answers.  It does not model word order or scope: two
requests with the same words are one request to it.  The fifteen parts are built in; only the words
are learned.  One word cannot have two meanings.  A lesson with one example file is refused, because
one file left two of twelve wrong answers undetected.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import pathlib
import re
import sys

CAPABILITY_ID = "file.question.taught_words.v1"
SCHEMA = "PROJECT_BRAIN_TAUGHT_WORDS_V1"
HERE = pathlib.Path(__file__).resolve().parent
CODE_ROOT = HERE.parents[1]
SEED_LESSONS = HERE / "TAUGHT_WORD_LESSONS_V1.json"
SEED_LEXICON = HERE / "TAUGHT_WORD_LEXICON_V1.json"
LIVE_DIR = CODE_ROOT / "canonical" / "astra_runtime" / "state"
LIVE_LESSONS_NAME = "taught_word_lessons_v1.jsonl"
LIVE_LEXICON_NAME = "taught_word_lexicon_v1.json"
MAX_BYTES = 4 * 1024 * 1024

# Structure words are skipped, never taught, and never carry meaning.  No negation, number or
# quantity word may be added here: a skipped word is a word nobody accounted for.
STRUCTURE_WORDS = frozenset("the a an of in is are to me that file".split())
UNITS = ("lines", "words", "characters", "bytes", "numbers")
FILTERS = ("rest", "containing", "blank", "unique")
MEASURES = ("lengths",)
# median is the lower middle element of the sorted values (index len//2), so its answer is always
# a whole number even when the count is even.  It was added as a code change, not learned: see
# A_NEW_PART_COSTS_CODE_ONE_LESSON_BUYS_THE_WORD_20261112_V1.md.
REDUCERS = ("count", "sum", "max", "min", "median")
PARTS = UNITS + FILTERS + MEASURES + REDUCERS


class Refuse(Exception):
    """The parts do not make an operation this module can perform on this text."""


def run(parts, text, data=None):
    """The value of one operation, given as a set of parts, on a text.

    Parts combine by type in one fixed order: look at one kind of thing, drop the first, keep those
    containing the data, keep the blank ones, drop repeats, measure lengths, reduce.
    """
    parts = frozenset(parts)
    if parts - frozenset(PARTS):
        raise Refuse("UNKNOWN_PART")
    unit = [p for p in UNITS if p in parts]
    reducer = [p for p in REDUCERS if p in parts]
    if len(unit) != 1:
        raise Refuse("NOT_EXACTLY_ONE_THING_TO_LOOK_AT")
    if len(reducer) != 1:
        raise Refuse("NOT_EXACTLY_ONE_WAY_TO_REDUCE")
    unit, reducer = unit[0], reducer[0]
    if unit == "lines":
        items = text.split("\n")
        if items and items[-1] == "":
            items.pop()
    elif unit == "words":
        items = text.split()
    elif unit == "characters":
        items = list(text)
    elif unit == "bytes":
        items = list(text.encode("utf-8"))
    else:
        items = [int(t) for t in text.split() if re.fullmatch(r"-?\d+", t)]
    is_text = unit in ("lines", "words", "characters")
    if "rest" in parts:
        items = items[1:]
    if "containing" in parts:
        if not is_text or not data:
            raise Refuse("CONTAINING_NEEDS_TEXT_AND_SOMETHING_TO_LOOK_FOR")
        items = [x for x in items if data in x]
    elif data:
        raise Refuse("TEXT_TO_LOOK_FOR_BUT_NO_WORD_FOR_CONTAINING")
    if "blank" in parts:
        if unit != "lines":
            raise Refuse("ONLY_LINES_CAN_BE_BLANK")
        items = [x for x in items if x == ""]
    if "unique" in parts:
        items = list(dict.fromkeys(items))
    numeric = unit == "numbers"
    if "lengths" in parts:
        if not is_text:
            raise Refuse("ONLY_TEXT_HAS_LENGTH")
        if reducer == "count":
            raise Refuse("A_COUNT_OF_LENGTHS_IS_NOT_A_QUESTION")
        items = [len(x) for x in items]
        numeric = True
    if reducer == "count":
        return len(items)
    if not numeric:
        raise Refuse("CANNOT_%s_TEXT" % reducer.upper())
    if not items:
        raise Refuse("NOTHING_TO_REDUCE")
    if reducer == "median":
        # Lower middle element: whole number for every non-empty list, even or odd length.
        return sorted(items)[len(items) // 2]
    return {"sum": sum, "max": max, "min": min}[reducer](items)


# Every operation the learner may attribute a lesson to.  Two spellings of one operation are listed
# once: counting lengths is counting, and the largest of the unique is the largest.
ALL_OPERATIONS = [
    frozenset((u,) + f + m + (r,))
    for u in UNITS
    for k in range(len(FILTERS) + 1)
    for f in itertools.combinations(FILTERS, k)
    for m in ((), MEASURES)
    for r in REDUCERS
    if not (m and r == "count") and not ("unique" in f and r in ("max", "min"))
]

_QUOTED = re.compile(r"(?<![A-Za-z0-9])(['\"`])([^'\"`\n]+)\1(?![A-Za-z0-9])")


def _looks_like_path(token):
    return "/" in token or re.search(r"[^.]\.[A-Za-z0-9]{1,5}\.?$", token) is not None


def split_request(sentence):
    """(paths, quoted texts, other tokens).  A path is a token with a slash or a file extension."""
    quoted, paths = [], []

    def _take(match):
        inner = match.group(2)
        (paths if _looks_like_path(inner) else quoted).append(inner)
        return " "

    bare = _QUOTED.sub(_take, str(sentence or ""))
    tokens = []
    for token in re.findall(r"[^\s,;:!?()]+", bare):
        if _looks_like_path(token):
            paths.append(token.rstrip("."))
        else:
            token = token.strip(".")
            if token:
                tokens.append(token)
    return paths, quoted, tokens


def norm(token):
    """The form a word is learned and looked up under: lower case, one plural s removed."""
    t = token.lower()
    return t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t


def _lesson_words(tokens, data):
    return frozenset(norm(t) for t in tokens if t.lower() not in STRUCTURE_WORDS and t != data)


def candidates(sentence, examples):
    """Every (operation, data) that gives the stated answer on EVERY example file."""
    _, quoted, tokens = split_request(sentence)
    data_options = list(quoted) or [t for t in tokens if t.lower() not in STRUCTURE_WORDS
                                    and all(t in text for text, _ in examples)]
    found = []
    for operation in ALL_OPERATIONS:
        for data in (data_options if "containing" in operation else [None]):
            try:
                fits = all(run(operation, text, data) == answer for text, answer in examples)
            except Refuse:
                continue
            if fits:
                found.append((operation, data))
    return found


def solve(lessons):
    """lessons: [(words, parts)].  (lexicon, size) for the smallest lexicon, or None when none fits.

    The lexicon is a list of bundles {"words", "parts", "could_be"}.  Words that always occur together
    form one bundle.  ``size`` is the number of word-part assignments the smallest lexicon needs.

    The smallest lexicon is found one part at a time, because parts do not interact.  A word may carry
    a part only if every lesson containing the word has that part, and every lesson that has the part
    must contain a word that carries it.  That is a minimum cover.  ALL minimum covers are listed, and
    a bundle is settled only when, for every part, it is in all of them or in none; otherwise its
    ``parts`` is None and ``could_be`` gives the smallest and the largest meaning it might have.
    """
    signature = {}
    for index, (words, _) in enumerate(lessons):
        for word in words:
            signature.setdefault(word, set()).add(index)
    bundles = {}
    for word, where in signature.items():
        bundles.setdefault(frozenset(where), []).append(word)
    keys = sorted(bundles, key=lambda s: (len(s), sorted(s)))
    always = {s: set() for s in keys}
    sometimes = {s: set() for s in keys}
    size = 0
    for part in PARTS:
        universe = 0
        for index, (_, parts) in enumerate(lessons):
            if part in parts:
                universe |= 1 << index
        if not universe:
            continue
        carriers = [s for s in keys if all(part in lessons[i][1] for i in s)]
        masks = [sum(1 << i for i in s) for s in carriers]
        reachable = 0
        for mask in masks:
            reachable |= mask
        if reachable != universe:
            return None
        covers = None
        for k in range(1, len(carriers) + 1):
            if math.comb(len(carriers), k) > 2000000:
                break
            found = []
            for combo in itertools.combinations(range(len(carriers)), k):
                joined = 0
                for j in combo:
                    joined |= masks[j]
                if joined == universe:
                    found.append(combo)
            if found:
                covers = found
                break
        if covers is None:          # too many ways to list: nothing about this part is settled
            size += len(carriers)
            for s in carriers:
                sometimes[s].add(part)
            continue
        size += len(covers[0])
        in_all = set(covers[0]).intersection(*[set(c) for c in covers])
        in_any = set().union(*[set(c) for c in covers])
        for j in in_all:
            always[carriers[j]].add(part)
        for j in in_any - in_all:
            sometimes[carriers[j]].add(part)
    lexicon = [{"words": sorted(bundles[s]),
                "parts": sorted(always[s]) if not sometimes[s] else None,
                "could_be": [sorted(always[s]), sorted(always[s] | sometimes[s])] if sometimes[s] else None}
               for s in keys]
    return lexicon, size


def learn(lessons):
    """lessons: [(sentence, [(text, answer), ...])].  Returns (lexicon, set_aside).

    A lesson is used only when exactly one reading of it survives.  Otherwise it is set aside and
    named: fewer than two example files, no operation gives the answers, it contradicts what its words
    already mean, or two readings fit equally well.  Of several readings, the one that needs the
    fewest word-part assignments is kept; a tie is not broken.
    """
    accepted, set_aside = [], []
    for index, (sentence, examples) in enumerate(lessons):
        if len(examples) < 2:
            set_aside.append({"index": index, "lesson": sentence, "set_aside": "TWO_EXAMPLE_FILES_NEEDED"})
            continue
        found = candidates(sentence, examples)
        if not found:
            set_aside.append({"index": index, "lesson": sentence,
                              "set_aside": "NO_OPERATION_I_CAN_PERFORM_GIVES_THESE_ANSWERS"})
            continue
        tokens = split_request(sentence)[2]
        options = [(_lesson_words(tokens, data), operation) for operation, data in found]
        if len(options) == 1 and solve(accepted + options) is not None:
            accepted.append(options[0])
            continue
        fitting = []
        for option in options:
            solved = solve(accepted + [option])
            if solved is not None:
                fitting.append((solved[1], sorted(option[1]), option))
        if not fitting:
            set_aside.append({"index": index, "lesson": sentence,
                              "set_aside": "CONFLICTS_WITH_WHAT_THE_WORDS_ALREADY_MEAN",
                              "operations_with_these_answers": [sorted(o) for o, _ in found][:4]})
            continue
        fitting.sort(key=lambda f: (f[0], f[1]))
        if len(fitting) > 1 and fitting[0][0] == fitting[1][0]:
            set_aside.append({"index": index, "lesson": sentence,
                              "set_aside": "TWO_READINGS_FIT_EQUALLY_WELL__ANOTHER_EXAMPLE_FILE_NEEDED",
                              "readings": [f[1] for f in fitting[:3]]})
            continue
        accepted.append(fitting[0][2])
    solved = solve(accepted)
    return (solved[0] if solved else []), set_aside


def interpret(lexicon, sentence, text):
    """Read one request against one file's text.

    {"ok": True, "parts", "data", "meanings", "value"} when every word is accounted for and the parts
    make one operation; otherwise {"ok": False, "reason"} naming the word or the missing part.
    A refusal carries ``near: True`` when at most two words stand between the sentence and an answer.
    """
    reading = _interpret(lexicon, sentence, text)
    if not reading["ok"]:
        reading.setdefault("near", not reading["reason"].startswith(("UNKNOWN_WORD:", "NO_KNOWN_WORD")))
    return reading


def _interpret(lexicon, sentence, text):
    _, quoted, tokens = split_request(sentence)
    known = {word: bundle for bundle in lexicon for word in bundle["words"]}
    present, unknown = [], []
    for token in tokens:
        if token.lower() in STRUCTURE_WORDS:
            continue
        word = norm(token)
        if word in known:
            present.append(word)
        else:
            unknown.append(token)
    parts, meanings = set(), {}
    for word in sorted(set(present)):
        bundle = known[word]
        if bundle["parts"] is None:
            return {"ok": False, "reason": "WORD_NOT_SETTLED:" + word}
        missing = [w for w in bundle["words"] if w not in present]
        if missing:
            return {"ok": False, "reason": "WORD_ONLY_KNOWN_TOGETHER_WITH:%s:%s" % (word, ",".join(missing))}
        parts |= set(bundle["parts"])
        meanings[word] = list(bundle["parts"])
    data = None
    if "containing" in parts:
        if len(quoted) == 1 and not unknown:
            data = quoted[0]
        elif not quoted and len(unknown) == 1 and unknown[0] in text:
            data = unknown[0]
        elif not quoted and len(unknown) == 1:
            return {"ok": False, "reason": "WORD_NOT_KNOWN_AND_NOT_IN_THE_FILE__QUOTE_IT_IF_IT_IS_TEXT_TO_LOOK_FOR:" + unknown[0]}
        elif unknown:
            return {"ok": False, "reason": "UNKNOWN_WORD:" + ",".join(unknown), "near": len(unknown) <= 2}
        else:
            return {"ok": False, "reason": "NOTHING_TO_LOOK_FOR" if not quoted else "MORE_THAN_ONE_QUOTED_TEXT"}
    elif unknown:
        return {"ok": False, "reason": "UNKNOWN_WORD:" + ",".join(unknown),
                "near": len(unknown) <= 2 and bool(present)}
    elif quoted:
        return {"ok": False, "reason": "QUOTED_TEXT_NOT_ACCOUNTED_FOR"}
    if not parts:
        return {"ok": False, "reason": "NO_KNOWN_WORD"}
    try:
        value = run(parts, text, data)
    except Refuse as exc:
        return {"ok": False, "reason": str(exc)}
    return {"ok": True, "parts": sorted(parts), "data": data, "meanings": meanings, "value": value}


def _parse_lessons(seed_raw, live_raw):
    seed = json.loads(seed_raw.decode("utf-8"))
    files = seed["example_files"]
    lessons = [(row["sentence"], [(files[e["file"]], e["answer"]) for e in row["examples"]])
               for row in seed["lessons"]]
    for line in live_raw.decode("utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            lessons.append((row["sentence"], [(e["text"], e["answer"]) for e in row["examples"]]))
    return lessons


def _raw_lessons(live_dir=None):
    live = pathlib.Path(live_dir or LIVE_DIR) / LIVE_LESSONS_NAME
    seed_raw = SEED_LESSONS.read_bytes()
    live_raw = live.read_bytes() if live.is_file() else b""
    return seed_raw, live_raw, hashlib.sha256(seed_raw + b"\0" + live_raw).hexdigest()


_CACHE: dict = {}


def load_lexicon(live_dir=None):
    """(lexicon, lessons_sha256).  A stored lexicon is used only when it was compiled from exactly
    the lessons present now; otherwise the lexicon is learned again in memory.  Never writes."""
    seed_raw, live_raw, sha = _raw_lessons(live_dir)
    if sha in _CACHE:
        return _CACHE[sha], sha
    stored = (pathlib.Path(live_dir or LIVE_DIR) / LIVE_LEXICON_NAME) if live_raw else SEED_LEXICON
    try:
        document = json.loads(stored.read_text(encoding="utf-8"))
        if document.get("lessons_sha256") == sha and isinstance(document.get("lexicon"), list):
            _CACHE[sha] = document["lexicon"]
            return _CACHE[sha], sha
    except (OSError, ValueError):
        pass
    _CACHE[sha] = learn(_parse_lessons(seed_raw, live_raw))[0]
    return _CACHE[sha], sha


def _settled(lexicon):
    return {word: tuple(b["parts"]) for b in lexicon if b["parts"] is not None for word in b["words"]}


def teach(sentence, examples, live_dir=None):
    """Add one lesson: a sentence and (text, answer) for two or more example files.

    The lesson is kept, and survives a restart, only when exactly one reading of it fits everything
    taught before.  Otherwise nothing is written and the reason is returned.
    """
    examples = [(str(text), answer) for text, answer in examples]
    if any(isinstance(a, bool) or not isinstance(a, int) for _, a in examples):
        return {"taught": False, "reason": "ANSWERS_MUST_BE_WHOLE_NUMBERS"}
    seed_raw, live_raw, _ = _raw_lessons(live_dir)
    lessons = _parse_lessons(seed_raw, live_raw)
    lexicon_before = learn(lessons)[0]
    before = _settled(lexicon_before)
    lexicon, set_aside = learn(lessons + [(sentence, examples)])
    mine = [note for note in set_aside if note["index"] == len(lessons)]
    if mine:
        return {"taught": False, "reason": mine[0]["set_aside"], "detail": mine[0]}
    # NOTHING ALREADY KNOWN MAY BE LOST.  A lesson can be consistent with every earlier one and still
    # leave an earlier word with two possible meanings; that word would then be refused wherever it
    # is used.  Words that were only known together may split, as long as together they mean the same.
    now = _settled(lexicon)
    harmed = []
    for bundle in lexicon_before:
        if bundle["parts"] is None:
            continue
        if any(word not in now for word in bundle["words"]) or \
                set().union(*[set(now[word]) for word in bundle["words"]]) != set(bundle["parts"]):
            harmed.extend(bundle["words"])
    if harmed:
        return {"taught": False, "reason": "LESSON_WOULD_UNSETTLE_WORDS_ALREADY_KNOWN:" + ",".join(sorted(harmed)),
                "hint": "teach the new word in a sentence whose other words do not carry the same part"}
    directory = pathlib.Path(live_dir or LIVE_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    row = {"sentence": sentence, "examples": [{"text": t, "answer": a} for t, a in examples]}
    with open(directory / LIVE_LESSONS_NAME, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    _, _, sha = _raw_lessons(live_dir)
    temporary = directory / (LIVE_LEXICON_NAME + ".tmp")
    temporary.write_text(json.dumps({"schema": SCHEMA + "_LEXICON", "lessons_sha256": sha, "lexicon": lexicon},
                                    indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    os.replace(temporary, directory / LIVE_LEXICON_NAME)
    after = _settled(lexicon)
    return {"taught": True, "lessons": len(lessons) + 1, "lessons_sha256": sha,
            "words_now_known": {w: list(after[w]) for w in sorted(set(after) - set(before))}}


def read_request(sentence, root, live_dir=None):
    """For the front door.  {"ok": True, "path", "parts", "data", "meanings", "lessons_sha256"} when
    the sentence names exactly one regular UTF-8 file inside ``root`` and the taught words account
    for every other word of it; otherwise {"ok": False, "reason"}.  Reads one file; writes nothing."""
    paths, _, _ = split_request(sentence)
    if len(paths) != 1:
        return {"ok": False, "reason": "NOT_EXACTLY_ONE_FILE_NAMED"}
    root = pathlib.Path(root).resolve()
    target = (root / paths[0]).resolve()
    if root not in target.parents or not target.is_file():
        return {"ok": False, "reason": "NOT_A_REGULAR_FILE_INSIDE_THE_ROOT"}
    try:
        if target.stat().st_size > MAX_BYTES:
            return {"ok": False, "reason": "FILE_LARGER_THAN_%d_BYTES" % MAX_BYTES}
        text = target.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return {"ok": False, "reason": "NOT_READABLE_UTF8_TEXT"}
    lexicon, sha = load_lexicon(live_dir)
    reading = interpret(lexicon, sentence, text)
    if not reading["ok"]:
        return reading
    return {"ok": True, "path": paths[0], "parts": reading["parts"], "data": reading["data"],
            "meanings": reading["meanings"], "lessons_sha256": sha}


def compile_seed_lexicon():
    """Learn the tracked lessons and store the result next to them."""
    seed_raw = SEED_LESSONS.read_bytes()
    lessons = _parse_lessons(seed_raw, b"")
    lexicon, set_aside = learn(lessons)
    document = {"schema": SCHEMA + "_LEXICON", "lessons_sha256": hashlib.sha256(seed_raw + b"\0").hexdigest(),
                "lesson_count": len(lessons), "lexicon": lexicon, "set_aside": set_aside}
    SEED_LEXICON.write_text(json.dumps(document, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    return document


def main(argv):
    command = argv[1] if len(argv) > 1 else ""
    if command == "compile":
        document = compile_seed_lexicon()
        print(json.dumps({"lessons": document["lesson_count"], "set_aside": len(document["set_aside"]),
                          "words_known": len(_settled(document["lexicon"])), "lessons_sha256": document["lessons_sha256"]}))
        return 0
    if command == "lexicon":
        for bundle in load_lexicon()[0]:
            print("%-22s -> %s" % (" + ".join(bundle["words"]),
                                   bundle["parts"] if bundle["parts"] is not None else "NOT SETTLED %s" % bundle["could_be"]))
        return 0
    if command == "ask" and len(argv) == 3:
        print(json.dumps(read_request(argv[2], pathlib.Path.cwd()), sort_keys=True))
        return 0
    if command == "teach" and len(argv) >= 4:
        examples = []
        for pair in argv[3:]:
            path, _, answer = pair.rpartition("=")
            examples.append((pathlib.Path(path).read_text(encoding="utf-8"), int(answer)))
        result = teach(argv[2], examples)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["taught"] else 1
    print("usage: taught_words_v1.py compile | lexicon | ask SENTENCE | teach SENTENCE FILE=ANSWER FILE=ANSWER ...")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
