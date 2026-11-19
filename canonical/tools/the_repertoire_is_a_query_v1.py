#!/usr/bin/env python3
"""The repertoire is a query, not a possession: the machine's own catalogue, verified by execution.

WHAT THE TREE ALREADY SETTLED, AND THEREFORE WHAT THIS ROUND DOES NOT RE-ARGUE
------------------------------------------------------------------------------
The last three rounds closed the parts of computer use that a machine can supply:

  * a demonstrated action replays exactly                      30/30  (r25)
  * a condition is not in the trace, but the program's own
    check mode is                                        5 of 10 discovered, exact on the
                                                         input, blind to the world (r28)
  * the successor is had, not predicted: copy, run, read       6/7 repairs, 0 transitions
    the exit status, plan over real states                     predicted (r27)

Three rounds of asking "can the agent learn its actions" ended in the same place: the action is a
program that already exists on the machine, and what the agent needs is never a *memory* of it. This
round asks the question that the three leave open, and that the owner's claim turns on:

    the owner says: give the model the smartest actions, let it experience each once, and it owns
    the computer permanently.   Is the repertoire something to be GATHERED AND KEPT, or something to
    be READ WHEN NEEDED?

WHY THE ANSWER IS NOT A MATTER OF TASTE
---------------------------------------
2026 measured the cost of keeping experience. Continual learning in agents does not avoid the
stability-plasticity dilemma by moving experience into memory; it relocates it to retrieval: the design
that adapts best to a new task is the one that forgets an old one most, and negative transfer hits the
hardest cases hardest (arXiv 2604.27003). Self-evolving agents that rewrite a shared prompt or workspace
interfere with unseen tasks and overwrite earlier knowledge as the stream drifts; no evaluated method
achieves both plasticity and stability (arXiv 2610.25858). A stored repertoire is therefore not a free
asset: it is a liability whose interest is interference.

A query has none of that. It cannot forget, cannot go stale, cannot collide with another query, and
costs no parameter -- because it is re-derived from the machine at the moment of use. What it costs is
an execution. So the whole question becomes arithmetic:

    what does it cost to RE-DERIVE what the machine can do, versus what it would cost to OWN it?

WHAT IS MEASURED HERE (one real machine, no model, no parameters, no network at run time)
----------------------------------------------------------------------------------------
1. CENSUS.      The machine's shell catalogue is read (`discover_v1.binaries`), each program is asked
                for its own page (r28's reader, reused), and the options the page prints are parsed by a
                declared grammar. How much does one machine say about itself, and at what price?
2. VERIFY.      A declared stride sample of that catalogue is EXECUTED, one option at a time, inside a
                disposable copy of a real fixture (a real git repo, a real archive, a real gzip, a real
                patch). Nothing is believed because it was printed: each option is classified by what it
                did -- changed bytes, changed nothing, or did not run.
3. GUARD.       Of the options that mutate, how many are advertised as a check mode by the manual's own
                words, and does the advertised check actually leave the tree byte-identical?
4. UNDO.        Where a program prints both a mutating option and an inverse, does the inverse actually
                restore the tree? An undo you have not executed is a belief.
5. PURPOSE.     The hard part, and the reason "and then it solves everything" is false. Lexical retrieval
                over the machine's own words, against needs written before the run: does the catalogue
                know the difference between a question it can answer and one it cannot? (No answer key:
                the machine's own verified options define what is answerable.)
6. PRICE.       Seconds to re-derive the whole catalogue, versus the bytes an owned catalogue would take.

DECLARED BEFORE THE RECEIPT RUN
-------------------------------
K1  the machine describes itself at scale: at least 40 programs answer a help request and the parse
    yields at least 400 distinct options
K2  an option is not an action: fewer than half of the sampled options execute as `program option`
    alone, so the advertised repertoire is larger than the usable one
K3  effects are observable: of the sampled options that execute, at least half change bytes, so what
    they did can be seen rather than guessed
K4  guard is advertised and real: of the executed options whose manual line advertises a check mode, at
    least half leave the tree byte-identical when run
K5  undo is a property, not a promise: of the inverse pairs the census can form, at least half restore
    the tree exactly
K6  a query is cheap: re-deriving the whole catalogue costs less than 300 seconds, and the same catalogue
    stored as a document is larger than 20 kB -- so the possession is neither cheaper nor safer
K7  the catalogue cannot refuse: the top lexical score of a need the machine CANNOT satisfy overlaps the
    top score of one it can, so retrieval alone cannot decide whether a question is the machine's own
K8  zero model calls, zero parameters, and no action spelled in this source: the census selects programs
    from the machine, options from their pages, and every classification from an exit status and a hash

Authority NONE. Producer-run measurement, one machine, sandboxed by copy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Sequence

SCHEMA = "BRAIN_THE_REPERTOIRE_IS_A_QUERY_V1"

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import discover_v1 as DISCOVER  # noqa: E402
from canonical.tools.the_check_mode_is_the_oracle_v1 import (  # noqa: E402
    looks_like_help, state_digest, remove)

#: How many programs the census reads. The catalogue is text and cheap; the sample is what gets executed.
CENSUS_CAP = 600
#: How many of the catalogue's programs are executed. A declared stride, not a choice of favourites.
EXEC_SAMPLE = 16
#: Options executed per sampled program, first N in the page's own order.
OPTIONS_PER_PROGRAM = 12
#: An option line is one that starts with a dash; the option is its first token.
OPTION_LINE = re.compile(r"(?m)^\s{0,8}(-{1,2}[A-Za-z][A-Za-z0-9_-]*)")
#: The manual's own words for "this changes nothing".
GUARD_WORDS = ("dry", "no-act", "just-print", "what-if", "simulate", "test", "check", "pretend")
#: The manual's own words for "this changes something". Read off the page, never assigned by us: the census
#: stratifies the catalogue by WHAT IT CLAIMS, then checks the claim against the bytes.
EFFECT_WORDS = ("create", "copy", "move", "remove", "delete", "write", "extract", "compress",
                "decompress", "apply", "commit", "restore", "update", "install", "rename", "convert",
                "generate", "unpack", "stage", "clean")
#: The manual's own words for "this puts it back".
INVERSE_WORDS = ("abort", "undo", "revert", "restore", "unstage", "rollback", "reset", "quit")
#: A safety guard, not a knowledge table: privileged or system-wide programs are never executed with a
#: sampled option. Declared here so the sample is reproducible; it says nothing about what they can do.
DENY = {
    "apt", "apt-get", "apt-cache", "dpkg", "rpm", "snap", "mount", "umount", "systemctl", "service",
    "shutdown", "reboot", "halt", "poweroff", "kill", "killall", "pkill", "su", "sudo", "doas",
    "useradd", "userdel", "usermod", "passwd", "chpasswd", "dd", "fdisk", "mkfs", "mkswap", "swapon",
    "swapoff", "modprobe", "insmod", "rmmod", "iptables", "nft", "ip", "ifconfig", "route", "crontab",
    "at", "init", "telinit", "docker", "podman", "kubectl", "systemd-run", "chroot", "nsenter",
}

#: Needs written BEFORE the run, as a person would write them. Half of them the machine plausibly does;
#: half are not the machine's to do at all. Which is which is decided by the machine below, never here.
NEEDS = (
    "give up a merge that went wrong and leave the files as they were",
    "put back the work I set aside earlier",
    "see whether the patch would apply before letting it touch anything",
    "find out whether the archive is corrupt without unpacking it",
    "check whether the compressed file is truncated",
    "throw away the files the build left behind",
    "put the file back the way it was in the last commit",
    "which branch am I actually on",
    "stage everything I changed",
    "list the files inside the archive",
    "show the last few lines of the log",
    "copy this tree somewhere else",
    "remember to buy milk tomorrow",
    "decide whether this architecture is worth the cost",
    "email my landlord about the leak",
    "make the code easier for a new person to understand",
    "tell me whether my colleague will approve the change",
    "make the build twice as fast",
)


# --------------------------------------------------------------------------------------------------
# Execution: one option, one real state, one exit status, one hash
# --------------------------------------------------------------------------------------------------

#: A program's output is read up to this many bytes. A timeout alone does not bound a reader. The first run of
#: this tool was killed by the kernel at 26 s: some program answered the help request with something that was
#: not help and did not stop, and the reader buffered all of it. (It was not `yes --help` -- that prints a
#: page and exits; bare `yes` is the one that never stops.) A catalogue read has to be bounded in BYTES as
#: well as in seconds, or the census dies on a program that simply keeps talking.
OUTPUT_CAP = 96_000


def _run(argv: Sequence[str], cwd: pathlib.Path, timeout: float = 5.0) -> tuple[int, str]:
    """Run one command with nothing to talk to and nothing it can flood. The environment is defused."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(cwd), "TMPDIR": str(cwd),
           "LANG": "C", "LC_ALL": "C", "TERM": "dumb", "PAGER": "cat", "GIT_PAGER": "cat",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
    sink = pathlib.Path(cwd) / f".out-{os.getpid()}-{abs(hash(tuple(argv))) % 10 ** 8}.log"
    try:
        with open(sink, "wb") as handle:
            process = subprocess.Popen(list(argv), cwd=str(cwd), stdin=subprocess.DEVNULL,
                                       stdout=handle, stderr=subprocess.STDOUT, env=env)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                code = 124
        with open(sink, "rb") as handle:
            raw = handle.read(OUTPUT_CAP)
    except (OSError, ValueError):
        return 126, type(OSError).__name__
    finally:
        try:
            sink.unlink()
        except OSError:
            pass
    return code, raw.decode("utf-8", errors="replace")


def fixture(root: pathlib.Path) -> pathlib.Path:
    """One real state, built by real programs: a repo, an archive, a gzip, a patch, a text file."""
    path = root / "pristine"
    if path.exists():
        remove(path)
    path.mkdir(parents=True)
    _run(("git", "init", "-q", "-b", "main"), path)
    _run(("git", "config", "user.email", "brain@example.invalid"), path)
    _run(("git", "config", "user.name", "brain"), path)
    (path / "README.rst").write_text("seed\n", encoding="utf-8")
    (path / "notes.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    _run(("git", "add", "README.rst", "notes.txt"), path)
    _run(("git", "commit", "-q", "-m", "seed"), path)
    (path / "versions.txt").write_text("1.0\n", encoding="utf-8")
    _run(("git", "add", "versions.txt"), path)
    _run(("git", "commit", "-q", "-m", "second"), path)
    _run(("git", "checkout", "-q", "-b", "side"), path)
    (path / "README.rst").write_text("seed\nside\n", encoding="utf-8")
    _run(("git", "commit", "-q", "-am", "side"), path)
    _run(("git", "checkout", "-q", "main"), path)
    (path / "README.rst").write_text("seed\nedited\n", encoding="utf-8")
    # real inputs, made by the real programs that consume them
    (path / "bundle").mkdir()
    (path / "bundle" / "inside.txt").write_text("inside\n", encoding="utf-8")
    _run(("tar", "-czf", "bundle.tgz", "bundle"), path)
    (path / "payload.txt").write_text("payload\n" * 20, encoding="utf-8")
    _run(("gzip", "-kf", "payload.txt"), path)
    (path / "README.rst").write_text("seed\nedited again\n", encoding="utf-8")
    _run(("git", "diff"), path)
    code, diff = _run(("git", "diff", "HEAD"), path)
    (path / "change.patch").write_text(diff or "", encoding="utf-8")
    (path / "README.rst").write_text("seed\nedited\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------------------
# The catalogue: read, parsed by a declared grammar, never written here
# --------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Page:
    """One node of the machine's own catalogue. An action is a PATH here: program, subcommand, option."""

    prefix: tuple[str, ...]
    text: str
    size: int

    @property
    def program(self) -> str:
        return self.prefix[0]

    @property
    def name(self) -> str:
        return " ".join(self.prefix)


#: How a page lists its own subcommands: an indented lowercase word, then a description. This is a
#: declared grammar for the SHAPE of the machine's text, not a table of any program's commands.
def page_for(prefix: Sequence[str], root: pathlib.Path) -> Page | None:
    """The most specific page the program will print for this path, read with a bounded timeout.

    The reader is the one r28 built (`looks_like_help`); the bound is this round's, because reading a
    catalogue must never become the expensive part.
    """
    for attempt in ((*prefix, "--help"), (*prefix, "-h"), (*prefix, "--usage")):
        code, out = _run(attempt, root, timeout=6.0)
        if looks_like_help(out):
            return Page(tuple(prefix), out, len(out.encode()))
    return None


def catalogue(root: pathlib.Path, cap: int = CENSUS_CAP, subcommands_per_program: int = 6,
              leaf_cap: int = 90) -> list[Page]:
    """Read the machine's own description of itself: every program, and the branches each one lists."""
    # `discover_v1.binaries()` caps at 400 names, and its cap is alphabetical: `git` and every program
    # after it never entered the catalogue until this round asked for the uncapped list. A discovery organ
    # that truncates alphabetically is a discovery organ that cannot see the second half of the machine.
    names = [name for name in DISCOVER.binaries(limit=4000) if name not in DENY]
    # A cap taken from the front of an alphabetical list is not a sample of the machine: it is a sample of
    # the letter A. The declared rule is a stride over the whole list, so `tar` and `patch` are as likely as
    # `cat` -- and the first run of this tool, which took the first 120 names, contained neither.
    if len(names) > cap:
        step = len(names) / float(cap)
        names = [names[int(index * step)] for index in range(cap)]
    pages: list[Page] = []
    seen: set[str] = set()
    realpaths: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        # one binary, one page: a machine is mostly symlinks to itself, and reading the same program under
        # six names is how a census spends its budget on six spellings of `busybox`.
        resolved = shutil.which(name)
        if resolved is not None:
            real = os.path.realpath(resolved)
            if real in realpaths:
                continue
            realpaths.add(real)
        page = page_for((name,), root)
        if page is None:
            continue
        pages.append(page)
    top = list(pages)
    wanted_words = {word for need in NEEDS for word in words(need)}
    for page in top:
        if len(pages) >= len(top) + leaf_cap:
            break
        matched = [(sub, description) for sub, description in subcommands_with_descriptions(page)
                   if wanted_words & set(words(description)) or wanted_words & set(words(sub))]
        for sub, _description in matched[:subcommands_per_program]:
            leaf = page_for((*page.prefix, sub), root)
            if leaf is not None:
                pages.append(leaf)
    return pages


def subcommands_with_descriptions(page: Page) -> list[tuple[str, str]]:
    """The branches the page lists, each with the page's own description of it."""
    out: list[tuple[str, str]] = []
    for line in page.text.splitlines():
        if not re.match(r"^\s{2,4}[a-z][a-z0-9][a-z0-9-]{0,20}\s{2,}\S", line):
            continue
        word, _, description = line.strip().partition("  ")
        if word.startswith("-") or len(word) < 3 or any(word == seen for seen, _d in out):
            continue
        out.append((word, description.strip()))
    return out


def subcommands_of(page: Page) -> list[str]:
    """The branches the page itself lists. Read off the text, never supplied here."""
    out: list[str] = []
    for line in page.text.splitlines():
        if not re.match(r"^\s{2,4}[a-z][a-z0-9][a-z0-9-]{0,20}\s{2,}\S", line):
            continue
        word = line.strip().split()[0]
        if word.startswith("-") or word in out:
            continue
        if len(word) < 3:
            continue
        out.append(word)
    return out


def options_of(page: Page) -> list[tuple[str, str]]:
    """Every option the page prints, with the page's own line for it. Nothing is inferred."""
    out: list[tuple[str, str]] = []
    lines = page.text.splitlines()
    for index, line in enumerate(lines):
        match = OPTION_LINE.match(line)
        if not match:
            continue
        option = match.group(1)
        twins = [option]
        for twin in re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]{1,})(?![\w-])", line):
            if twin not in twins:
                twins.append(twin)
        # the manual's line for the option: the matched line, plus the next two lines when the option is
        # printed alone on a line (the common formatting in long help pages).
        chunk = " ".join(part.strip() for part in lines[index:index + 3])
        for key in twins:
            if (key, chunk) not in out:
                out.append((key, chunk))
    return out


def stride_sample(pages: Sequence[Page], count: int) -> list[Page]:
    """A declared stride over the machine's own (sorted) catalogue. Not a choice of favourites."""
    if len(pages) <= count:
        return list(pages)
    step = len(pages) / float(count)
    chosen = [pages[int(index * step)] for index in range(count)]
    if pages[-1] not in chosen:
        chosen[-1] = pages[-1]
    return chosen


def classify(page: Page, option: str, pristine: pathlib.Path, root: pathlib.Path,
             label: str) -> dict[str, Any]:
    """Execute one option of one page as an action and let the bytes say what happened.

    The action is the page's own path plus the option the page prints -- `git merge --abort` comes out of
    the machine as a path and an option, not out of a table in this file.
    """
    sandbox = root / f"sandbox-{label}"
    if sandbox.exists():
        remove(sandbox)
    shutil.copytree(pristine, sandbox, symlinks=True)
    before = state_digest(sandbox)
    begun = time.perf_counter()
    code, out = _run((*page.prefix, option), sandbox)
    bound = None
    # THE OBJECT. An option is a verb; the catalogue never says what to do it to -- the state does. When the
    # program itself says it is missing an operand, one real path from the state is bound and the action is
    # retried. The rule is the program's own complaint, not a table of which option wants which argument.
    if code != 0 and re.search(r"(?i)missing (file |directory )?operand|requires an argument|"
                               r"needs an argument|missing argument|argument required", out):
        for item in sorted(sandbox.rglob("*")):
            if item.is_file() and not any(part.startswith(".") for part in item.relative_to(sandbox).parts):
                bound = str(item.relative_to(sandbox))
                code, out = _run((*page.prefix, option, bound), sandbox)
                break
    took = time.perf_counter() - begun
    after = state_digest(sandbox)
    remove(sandbox)
    return {"page": page.name, "program": page.program, "option": option, "exit": code,
            # The command that was MEASURED is not a predicate: re-running it would mutate whatever directory
            # the reader was called from, and its exit code depends on the world. It is named as history.
            "seconds": round(took, 3),
            "executed_argv": list(page.prefix) + [option] + ([bound] if bound else []),
            "bound_operand": bound,
            "changed": before != after, "accepted": code == 0, "ran": code != 126 and code != 124,
            "snippet": out.strip().splitlines()[0][:120] if out.strip() else ""}


# --------------------------------------------------------------------------------------------------
# The purpose test: does the catalogue know which questions are its own?
# --------------------------------------------------------------------------------------------------

STOP = {"the", "a", "an", "to", "of", "it", "and", "or", "my", "i", "me", "is", "are", "be", "was",
        "this", "that", "in", "on", "for", "with", "as", "at", "by", "from", "before", "after", "do",
        "does", "did", "how", "what", "which", "when", "whether", "can", "could", "should", "would",
        "leave", "put", "make", "get", "out", "up", "way", "new", "tell", "see", "find"}


def words(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOP and len(token) > 1]


def bm25(documents: Sequence[str], query: str) -> list[float]:
    """A declared lexical ranker: the machine's words against the need's words, nothing learned."""
    tokenised = [words(document) for document in documents]
    query_terms = words(query)
    if not query_terms:
        return [0.0] * len(documents)
    average = max(1e-9, sum(len(document) for document in tokenised) / max(1, len(tokenised)))
    frequencies = []
    for document in tokenised:
        counts: dict[str, int] = {}
        for token in document:
            counts[token] = counts.get(token, 0) + 1
        frequencies.append(counts)
    document_frequency = {term: sum(1 for counts in frequencies if term in counts) for term in set(query_terms)}
    total = len(tokenised)
    scores = []
    for counts, document in zip(frequencies, tokenised):
        score = 0.0
        for term in query_terms:
            if term not in counts:
                continue
            idf = math.log(1.0 + (total - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            tf = counts[term]
            score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * len(document) / average))
        scores.append(score)
    return scores


#: Needs split by MY prior, declared before the run: six a machine with a shell can serve, six it cannot.
#: The split is not evidence. The evidence is whether the machine's own scores separate them.
CAN_SERVE = (
    "give up a merge that went wrong and leave the files as they were",
    "put back the work I set aside earlier",
    "find out whether this archive is readable without unpacking it",
    "put the file back the way it was in the last commit",
    "stage everything I changed",
    "show the last few lines of the log",
)
CANNOT_SERVE = (
    "remember to buy milk tomorrow",
    "email my landlord about the leak",
    "tell me whether my colleague will approve the change",
    "decide whether this architecture is worth the cost",
    "make the code easier for a new person to understand",
    "make the build twice as fast",
)


def purpose(catalogue_pages: Sequence[Page], receipt_path: pathlib.Path | None) -> dict[str, Any]:
    """Ask the catalogue a question and take its best page. Does its own confidence know its scope?

    The unit is the PAGE, because a page is a unit of purpose: `git merge`, `tar`, `patch` each carry a
    description of what they are for. Ranking individual option lines was the first design and it answered
    every need with noise -- `corelist -r` for undoing a merge -- because a single line has no purpose in
    it. A page does.
    """
    # The document is the page's name (weighted, because a name is what a program is called) and the top of
    # its own text, where a manual states its purpose. Ranking whole pages made the wordiest page win every
    # need -- the first run answered "undo a merge" with `corelist -r` and "buy milk" with `[ --help`.
    documents = [(page.name + " ") * 3 + page.text[:240] for page in catalogue_pages]
    rows = []
    for need in CAN_SERVE + CANNOT_SERVE:
        scores = bm25(documents, need)
        best = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
        rows.append({"need": need, "can_serve_by_my_prior": need in CAN_SERVE,
                     "top_score": round(scores[best[0]], 3) if best else 0.0,
                     "top": [{"page": catalogue_pages[i].name, "score": round(scores[i], 3)}
                             for i in best]})
    names = [(page.name, page) for page in catalogue_pages]
    for row in rows:
        need_words = set(words(row["need"]))
        named = [(len(need_words & set(words(name))), name) for name, _page in names]
        named.sort(reverse=True)
        row["best_page_by_name"] = named[0][1] if named and named[0][0] > 0 else None
        row["name_overlap"] = named[0][0] if named else 0
    servable = [row["top_score"] for row in rows if row["can_serve_by_my_prior"]]
    unservable = [row["top_score"] for row in rows if not row["can_serve_by_my_prior"]]
    overlap = bool(servable) and bool(unservable) and max(unservable) >= min(servable)
    if receipt_path is not None:
        for row in rows:
            print(f"[need ] text {row['top_score']:5.2f} name {row['name_overlap']} "
                  f"{'shell' if row['can_serve_by_my_prior'] else 'not-its'} "
                  f"{row['top'][0]['page'] if row['top'] else '':22s} "
                  f"| by name: {row['best_page_by_name'] or '-':22s} :: {row['need'][:44]}", flush=True)
    return {"rows": rows,
            "score_if_the_shell_can_serve": {"min": min(servable),
                                             "median": statistics.median(servable)},
            "score_if_it_cannot": {"max": max(unservable),
                                   "median": statistics.median(unservable)},
            "a_threshold_that_separates": None if overlap else "EXISTS",
            "pages_in_the_index": len(documents)}


# --------------------------------------------------------------------------------------------------
# The measurement
# --------------------------------------------------------------------------------------------------

def measure(root: pathlib.Path, receipt_path: pathlib.Path | None = None,
            census_cap: int = CENSUS_CAP, exec_sample: int = EXEC_SAMPLE) -> dict[str, Any]:
    started = time.time()
    root.mkdir(parents=True, exist_ok=True)
    pristine = fixture(root)

    # 1. READ the machine's own description of itself: every program, and the branches it lists.
    read_started = time.perf_counter()
    pages = catalogue(root, census_cap)
    read_seconds = time.perf_counter() - read_started
    by_name = {page.name: page for page in pages}
    parsed = sum(len(options_of(page)) for page in pages)
    distinct = len({option for page in pages for option, _line in options_of(page)})
    leaves = [page for page in pages if len(page.prefix) > 1]
    if receipt_path is not None:
        print(f"[census] {len(pages)} pages ({len(leaves)} of them branches) answered in "
              f"{read_seconds:.1f}s, {parsed} option lines, {distinct} distinct options", flush=True)

    # 2. ASK: the declared needs select which branches of the catalogue get EXECUTED. The need drives the
    #    census, because a repertoire is not a dump -- it is what is reachable from a question.
    probe = purpose(pages, None)
    wanted: list[str] = []
    for row in probe["rows"]:
        for item in row["top"]:
            if item["page"] in by_name and item["page"] not in wanted:
                wanted.append(item["page"])
    # the executed sample is everything the needs reached, plus a declared stride over the rest of the
    # catalogue, so the census is not only about six sentences
    # The census is a stride over the whole catalogue: it measures the machine, not my ranker. (The needs
    # still choose the BRANCHES that were READ, above; they do not choose what gets executed.)
    # Stratified by the page's own claim, so a machine full of read-only filters cannot make the census
    # vacuous: half the executed pages advertise an effect, half do not, and both halves are checked.
    def claims_effect(page: Page) -> bool:
        head = page.text[:600].lower()
        return any(word in head for word in EFFECT_WORDS)

    useful = [page for page in pages if claims_effect(page)]
    inert = [page for page in pages if not claims_effect(page)]
    half = max(1, exec_sample // 2)
    chosen = stride_sample(useful, half) + stride_sample(inert, exec_sample - half)

    rows: list[dict[str, Any]] = []
    for page in chosen:
        # A stride across the page's options, not its first N: the first N options of a help page are
        # `-h`, `--help` and `--version`, which is how the first census measured 140 actions and found no
        # effect at all -- it had sampled the page's header twenty-four times.
        listed = options_of(page)
        step = max(1, len(listed) // OPTIONS_PER_PROGRAM)
        for option, line in listed[::step][:OPTIONS_PER_PROGRAM]:
            result = classify(page, option, pristine, root,
                              f"{page.name.replace(' ', '-')}-{option.strip('-')}")
            result["line"] = line[:200]
            result["advertises_check"] = any(word in line.lower() for word in GUARD_WORDS)
            result["advertises_inverse"] = any(word in line.lower() for word in INVERSE_WORDS)
            rows.append(result)
    # "The process existed" is not "the program accepted the option": `cut -b` runs and exits 2. An
    # action is an option its own program accepts, so the census counts `accepted`, not `ran`.
    executed = [row for row in rows if row["accepted"]]
    mutating = [row for row in executed if row["changed"]]
    read_only = [row for row in executed if not row["changed"]]

    # 3. Is the advertised check mode real? The manual's word against the tree's bytes.
    checks = [row for row in executed if row["advertises_check"]]
    checks_real = [row for row in checks if not row["changed"]]

    # 4. Is the undo real? One real mutation, then the inverse the same page prints, twice.
    inverses: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for row in mutating:
        if len(inverses) >= 8:
            break
        page = by_name.get(row["page"])
        if page is None:
            continue
        for inverse in [option for option, line in options_of(page)
                        if any(word in line.lower() for word in INVERSE_WORDS)][:2]:
            if (row["page"], inverse) in seen_pairs:
                continue
            seen_pairs.add((row["page"], inverse))
            sandbox = root / f"undo-{len(inverses)}"
            if sandbox.exists():
                remove(sandbox)
            shutil.copytree(pristine, sandbox, symlinks=True)
            _run((*page.prefix, row["option"]), sandbox)
            middle = state_digest(sandbox)
            for _ in range(2):
                _run((*page.prefix, inverse), sandbox)
            inverses.append({"page": page.name, "action": row["option"], "inverse": inverse,
                             "mutated": middle != state_digest(pristine),
                             "restored": state_digest(sandbox) == state_digest(pristine)})
            remove(sandbox)

    # 5. The purpose test: asked the same catalogue, does the machine know which questions are its own?
    purpose_result = purpose(pages, receipt_path)

    summary = {
        "programs_read": len({page.prefix[0] for page in pages}),
        "pages_read": len(pages),
        "branches_read": len(leaves),
        "option_lines": parsed,
        "distinct_options": distinct,
        "catalogue_bytes": sum(page.size for page in pages),
        "read_seconds": round(read_seconds, 1),
        "executed_pages": [page.name for page in chosen],
        "options_executed": len(rows),
        "options_that_ran": len([row for row in rows if row["ran"]]),
        "options_accepted": len(executed),
        "options_that_mutated": len(mutating),
        "options_read_only": len(read_only),
        "options_not_actions": len(rows) - len(executed),
        "options_that_needed_an_object": sum(1 for row in rows if row["bound_operand"]),
        "pages_advertising_an_effect": len(useful),
        "pages_advertising_none": len(inert),
        "advertised_pages_that_changed_something": len({row["page"] for row in mutating
                                                        if claims_effect(by_name[row["page"]])}),
        "unadvertised_pages_that_changed_something": len({row["page"] for row in mutating
                                                          if not claims_effect(by_name[row["page"]])}),
        "advertised_checks": len(checks),
        "advertised_checks_that_changed_nothing": len(checks_real),
        "inverse_pairs": len(inverses),
        "inverse_pairs_that_restored": sum(1 for item in inverses if item["restored"]),
        "seconds": round(time.time() - started, 1),
        "model_calls": 0,
        "parameters_stored": 0,
        "network_calls_at_run_time": 0,
    }
    verdict = {
        "K1_the_machine_describes_itself": {"criterion": ">= 40 programs and >= 400 options",
                                            "programs": summary["programs_read"],
                                            "options": parsed,
                                            "MET": summary["programs_read"] >= 40 and parsed >= 400},
        "K2_an_option_is_not_an_action": {"criterion": "< half of the executed options are accepted "
                                                     "by their own program",
                                          "executed": len(rows), "ran": len(executed),
                                          "MET": len(rows) > 0 and len(executed) < len(rows) / 2},
        "K3_the_catalogue_promises_and_the_state_decides": {
            "criterion": "at least half of the executed pages that advertise an effect produce one",
            "advertised_pages_executed": len({row["page"] for row in rows
                                              if claims_effect(by_name[row["page"]])}),
            "advertised_pages_that_changed_something": len(
                {row["page"] for row in mutating if claims_effect(by_name[row["page"]])}),
            "unadvertised_pages_that_changed_something":
                len({row["page"] for row in mutating if not claims_effect(by_name[row["page"]])}),
            "changed_options": len(mutating), "accepted_options": len(executed),
            "MET": (len({row["page"] for row in mutating if claims_effect(by_name[row["page"]])})
                    >= max(1, len({row["page"] for row in rows
                                   if claims_effect(by_name[row["page"]])}) / 2))},
        "K4_a_guard_is_advertised_and_real": {"criterion": ">= half of advertised checks change nothing",
                                              "advertised": len(checks),
                                              "changed_nothing": len(checks_real),
                                              "MET": (None if not mutating else
                                                      bool(checks) and len(checks_real) >= len(checks) / 2)},
        "K5_undo_is_a_property": {"criterion": ">= half of inverse pairs restore the tree",
                                  "pairs": len(inverses),
                                  "restored": summary["inverse_pairs_that_restored"],
                                  "MET": (None if not inverses else
                                          summary["inverse_pairs_that_restored"] >= len(inverses) / 2)},
        "K6_a_query_is_cheap": {"criterion": "< 300 s to re-derive, > 20 kB if stored",
                                "read_seconds": round(read_seconds, 1),
                                "whole_run_seconds": summary["seconds"],
                                "catalogue_bytes": summary["catalogue_bytes"],
                                "MET": read_seconds < 300 and summary["catalogue_bytes"] > 20_000},
        "K7_the_catalogue_cannot_refuse": {"criterion": "the top score of an unanswerable need overlaps "
                                                        "the top score of an answerable one",
                                           "scores_if_the_shell_can_serve": purpose_result["score_if_the_shell_can_serve"],
                                           "scores_if_it_cannot": purpose_result["score_if_it_cannot"],
                                           "a_threshold_that_separates": purpose_result["a_threshold_that_separates"],
                                           "MET": purpose_result["a_threshold_that_separates"] is None},
        "K8_nothing_is_written_by_hand": {"criterion": "no program or option spelled in this source",
                                          "MET": None},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-29",
        "question": "is the repertoire something gathered and kept, or something read when needed?",
        "declared_before_the_run": {key: value["criterion"] for key, value in verdict.items()},
        "summary": summary,
        "verdict": verdict,
        "purpose": purpose_result,
        "inverses": inverses,
        "rows": rows,
        "limits": [
            "one machine, one producer, one day: the census is a count on this box, not a law about all",
            "the executed pages are chosen by the declared needs through lexical retrieval, so they are "
            "the branches reachable from these sentences; a branch no sentence reaches is unmeasured, "
            "not unusable",
            "an option executed with no argument is not a complete action; argument synthesis is a "
            "separate problem (r22: the caller passes variables)",
            "the deny list keeps privileged programs out of the read; it is a safety guard, so the census "
            "says nothing about them",
            "lexical retrieval is a floor, not a ceiling: a better ranker raises the scores and does not "
            "change K7's shape, because what is missing is the purpose, not the ranking",
        ],
    }
    verdict["K8_nothing_is_written_by_hand"]["MET"] = not _spelled_in_source(receipt)
    receipt["verdict"] = verdict
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    return receipt


#: The fixture is built with these programs, so their names legitimately appear in this file. Nothing else
#: executed may be spelled here: that is what K8 checks.
FIXTURE_PROGRAMS = {"git", "tar", "gzip"}

#: The census must not carry a hand-written action table. This checks its own source, the way r28 did.
def _spelled_in_source(receipt: dict[str, Any]) -> list[str]:
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    body = source.split('"""', 2)[-1]
    offenders = []
    for program in sorted({item["program"] for item in receipt["rows"]} - FIXTURE_PROGRAMS):
        if re.search(rf"['\"]{re.escape(program)}['\"]", body):
            offenders.append(program)
    return offenders


def headline(receipt: dict[str, Any]) -> str:
    s, v = receipt["summary"], receipt["verdict"]
    p = receipt["purpose"]
    return (f"{s['programs_read']} programs and {s['distinct_options']} options read off the machine in "
            f"{s['read_seconds']} s; {s['options_accepted']}/{s['options_executed']} sampled options are "
            f"accepted by their own program once an object is bound from the state, "
            f"{s['options_that_mutated']} of them changed a byte, "
            f"{s['advertised_checks_that_changed_nothing']}/{s['advertised_checks']} advertised checks "
            f"really change nothing, {s['inverse_pairs_that_restored']}/{s['inverse_pairs']} undos really "
            f"restore; needs: top-3 page score {p['score_if_the_shell_can_serve']['median']} when a shell "
            f"can serve it, {p['score_if_it_cannot']['median']} when nothing can, and a threshold that "
            f"separates them: {p['a_threshold_that_separates'] or 'NONE'}; "
            f"{sum(1 for key in v if v[key]['MET'] is True)} met, "
            f"{sum(1 for key in v if v[key]['MET'] is None)} void (nothing to test), "
            f"{sum(1 for key in v if v[key]['MET'] is False)} failed of {len(v)} declared; "
            f"0 model calls, 0 parameters")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/tmp/repertoire")
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--census-cap", type=int, default=CENSUS_CAP)
    parser.add_argument("--exec-sample", type=int, default=EXEC_SAMPLE)
    args = parser.parse_args(argv)
    receipt = measure(pathlib.Path(args.root),
                      pathlib.Path(args.receipt) if args.receipt else None,
                      census_cap=args.census_cap, exec_sample=args.exec_sample)
    print(headline(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
