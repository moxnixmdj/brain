"""Fresh instances for FILE_QUESTION_TAUGHT_WORDS_V1.  Imports nothing from the runtime.

An instance is a text file described line by line (so the truth is known without reading the file
back), one question in structured form, and one English sentence for that question built from this
file's own phrase tables.  About three in ten instances carry one word nobody taught; the only
correct output for those is no answer.

Only questions whose meaning does not depend on word order are generated: "after the first" is never
combined with another filter.
"""
from __future__ import annotations

import random

WORDS = ["alpha", "beta", "gamma", "delta", "disk", "full", "node", "queue", "retry", "caf\u00e9",
         "na\u00efve", "x9", "ok", "job", "host7", "zeta"]
TOKENS = ["ERROR", "WARN", "TODO", "FAIL"]
UNTAUGHT = ["not", "never", "twice", "yesterday", "approximately", "excluding", "except", "without",
            "second", "median", "average", "odd", "even", "sorted", "reversed", "nonblank", "exactly",
            "halved", "delete", "remove"]


def file_text(lines, trailing_newline):
    return "\n".join(lines) + ("\n" if trailing_newline else "")


def _text_world(rng: random.Random) -> dict:
    token = rng.choice(TOKENS)
    lines: list[str] = []
    for _ in range(rng.randint(2, 14)):
        roll = rng.random()
        if roll < 0.18:
            lines.append("")
        elif roll < 0.40 and lines:
            lines.append(rng.choice(lines))
        else:
            words = [rng.choice(WORDS) for _ in range(rng.randint(1, 6))]
            if rng.random() < 0.4:
                words.insert(rng.randrange(len(words) + 1), token)
            lines.append(" ".join(words))
    # a file that ends in an empty line is only that file when a newline follows it
    trailing = True if lines[-1] == "" else rng.random() < 0.7
    return {"kind": "text", "lines": lines, "trailing_newline": trailing, "token": token}


def _number_world(rng: random.Random) -> dict:
    count = rng.randint(2, 12)
    numbers = [rng.randint(-50, 999) for _ in range(count)]
    if rng.random() < 0.5:
        numbers[rng.randrange(count)] = rng.choice(numbers)
    per_line = rng.choice([1, 1, 2, 3])
    lines = [" ".join(str(x) for x in numbers[i:i + per_line]) for i in range(0, count, per_line)]
    return {"kind": "numbers", "numbers": numbers, "lines": lines, "trailing_newline": True, "token": None}


def _question(rng: random.Random, world: dict) -> dict:
    q = {"unit": "lines", "reduce": "count", "lengths": False, "unique": False, "blank": False,
         "containing": None, "rest": False}
    if world["kind"] == "numbers":
        q["unit"] = "numbers"
        q["reduce"] = rng.choice(["count", "sum", "max", "min", "sum", "max"])
        roll = rng.random()
        if roll < 0.35:
            q["rest"] = True
        elif roll < 0.60 and q["reduce"] in ("count", "sum"):
            q["unique"] = True
        return q
    if rng.random() < 0.2:
        q["lengths"], q["reduce"], q["rest"] = True, rng.choice(["max", "min"]), rng.random() < 0.3
        return q
    q["unit"] = rng.choice(["lines", "lines", "words", "characters", "bytes"])
    roll = rng.random()
    if roll < 0.20:
        q["rest"] = True
    elif roll < 0.40:
        q["unique"] = True
    elif roll < 0.55 and q["unit"] == "lines":
        q["blank"] = True
    elif roll < 0.85 and q["unit"] in ("lines", "words"):
        q["containing"] = world["token"]
        q["unique"] = rng.random() < 0.3
    return q


def _sentence(rng: random.Random, q: dict, world: dict) -> str:
    tail = " after the first" if q["rest"] else ""
    if q["lengths"]:
        return "what is the length of the %s line in {file}%s" % ("longest" if q["reduce"] == "max" else "shortest", tail)
    if q["unit"] == "numbers" and q["reduce"] in ("max", "min"):
        word = rng.choice(["largest", "biggest"]) if q["reduce"] == "max" else "smallest"
        return "what is the %s number in {file}%s" % (word, tail)
    if q["reduce"] == "sum":
        if not q["unique"] and rng.random() < 0.3:
            return "add up the numbers in {file}" + tail
        return "what is the sum of the %snumbers in {file}%s" % ("unique " if q["unique"] else "", tail)
    words = []
    if q["unique"]:
        words.append(rng.choice(["unique", "different", "distinct"]))
    if q["blank"]:
        words.append(rng.choice(["blank", "empty"]))
    words.append(rng.choice(["lines", "rows"]) if q["unit"] == "lines" else q["unit"])
    lead = " ".join(words)
    if q["containing"] is not None:
        present = any(q["containing"] in line for line in world["lines"])
        shown = q["containing"] if (present and rng.random() < 0.5) else "'%s'" % q["containing"]
        return "how many %s %s %s in {file}%s" % (lead, rng.choice(["contain", "mention"]), shown, tail)
    if rng.random() < 0.25:
        return "count the %s in {file}%s" % (lead, tail)
    return "how many %s are in {file}%s" % (lead, tail)


def _with_untaught_word(rng: random.Random, sentence: str, word: str) -> str:
    parts = sentence.split(" ")
    stop = parts.index("{file}")
    place = rng.randint(1, stop - 1)
    return " ".join(parts[:place] + [word] + parts[place:])


def generate(rng: random.Random, n: int) -> list[dict]:
    out = []
    for index in range(n):
        world = _number_world(rng) if rng.random() < 0.35 else _text_world(rng)
        question = _question(rng, world)
        sentence = _sentence(rng, question, world)
        instance = {
            "kind": "ask", "world": world, "question": question, "sentence": sentence,
            "file_name": "q%06x.txt" % rng.getrandbits(24),
            "file_text": file_text(world["lines"], world["trailing_newline"]),
        }
        if rng.random() < 0.30:
            first, second = rng.sample(UNTAUGHT, 2)
            instance["kind"] = "untaught"
            instance["untaught_word"], instance["other_untaught_word"] = first, second
            instance["sentence_before_the_word"] = sentence
            instance["sentence"] = _with_untaught_word(rng, sentence, first)
        out.append(instance)
    return out
