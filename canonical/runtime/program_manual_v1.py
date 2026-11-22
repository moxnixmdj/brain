"""A program's real manual, fetched from the web and read for the question asked.

A15 measured the limit of the existing web channel: it can say whether a *named* thing exists,
and it cannot answer an *operational* question, because the reachable sources are a code host
and package registries. The premise it could not satisfy is that a manual is on the web. It is
-- in the program's own repository, as the manual its authors wrote.

This module closes that gap and nothing more. It does not summarise, does not paraphrase, and
holds no knowledge of any program: it fetches the manual for the program named in a command, and
returns the passage that mentions the question's words. Every sentence it returns is the
authors' sentence, with the URL it came from.

The rule the rest of this round has enforced applies here too: a source's answer is used only if
it can be checked. A passage is returned with its own words, so the caller can read it.

What is *not* here: a general web crawler. `github.com`, `api.github.com` and `codeload` are what
this machine can reach, so a manual is looked for where manuals live -- the repository of the
program, when the program's repository can be named. That is a real limit and it is stated, not
hidden behind a search that would silently fail.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PROGRAM_MANUAL_V1"
API = "https://api.github.com"
TIMEOUT_S = 20
CACHE_DIR = os.environ.get("BRAIN_PROGRAM_MANUAL_CACHE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "astra_runtime", "state", "manual_cache")
_CACHE: dict[str, tuple[float, Any]] = {}
CACHE_TTL_S = 6 * 3600

# Repositories that hold the manuals of whole families of programs. The table maps a program
# name to the repository whose manual documents it. This is provenance, not knowledge: it says
# where a manual lives, the same way a library catalogue says which shelf a book is on.
FAMILIES = {
    "coreutils": ("coreutils/coreutils", "doc/coreutils.texi"),
    "gnu": ("coreutils/coreutils", "doc/coreutils.texi"),
}
MEMBERS = {
    "coreutils": """arch b2sum base32 base64 basename basenc cat chcon chgrp chmod chown chroot
        cksum comm cp csplit cut date dd df dir dircolors dirname du echo env expand expr factor
        false fmt fold groups head hostid hostname id install join kill link ln logname ls md5sum
        mkdir mkfifo mknod mktemp mv nice nl nohup nproc numfmt od paste pathchk pinky pr printenv
        printf ptx pwd readlink realpath rm rmdir runcon seq sha1sum sha224sum sha256sum sha384sum
        sha512sum shred shuf sleep sort split stat stdbuf stty sum sync tac tail tee test timeout
        touch tr true truncate tsort tty uname unexpand uniq unlink users vdir wc who whoami yes
        """.split(),
}


def _get(url: str, timeout: int = TIMEOUT_S) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "brain-manual-reader",
                                                   "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def _repo_for(program: str) -> tuple[str, str] | None:
    """Where the manual for this program lives, if this machine knows a catalogue entry."""
    name = str(program or "").strip().rsplit("/", 1)[-1].lower()
    if not name:
        return None
    for family, members in MEMBERS.items():
        if name in members:
            return FAMILIES[family]
    return None


def fetch_manual(program: str, *, timeout: int = TIMEOUT_S) -> dict[str, Any]:
    """The program's manual text, or the reason it could not be had.

    Returned with its provenance: which repository, which file, which URL, and the sha256 of
    exactly the bytes read. A caller can therefore check the claim rather than trust it.
    """
    import hashlib
    key = f"manual:{program}"
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    found = _repo_for(program)
    if not found:
        out = {"schema": SCHEMA, "program": program, "ok": False,
               "reason": "NO_CATALOGUE_ENTRY_FOR_THIS_PROGRAM",
               "detail": ("This machine can reach github.com, and a manual is in the program's "
                          "repository; naming which repository holds which program is the one "
                          "thing this reader does not guess.")}
        _CACHE[key] = (time.time() + CACHE_TTL_S, out)
        return out
    repo, path = found
    url = f"{API}/repos/{repo}/contents/{path}"
    try:
        status, body = _get(url, timeout=timeout)
        payload = json.loads(body)
        if isinstance(payload, list):
            payload = next((x for x in payload if x.get("name", "").endswith(".texi")), {})
        text = base64.b64decode(payload.get("content") or "").decode("utf-8", "replace")
        out = {"schema": SCHEMA, "program": program, "ok": bool(text), "repo": repo,
               "path": path, "url": payload.get("html_url") or url,
               "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
               "bytes": len(text), "text": text}
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        out = {"schema": SCHEMA, "program": program, "ok": False,
               "reason": f"{type(exc).__name__}: {exc}", "repo": repo, "path": path}
    _CACHE[key] = (time.time() + CACHE_TTL_S, out)
    return out


def _clean_texi(text: str) -> str:
    """Strip the markup that would otherwise be read as the manual's meaning.

    Texinfo directives (`@node`, `@deffn`), escapes (`\\-`, `@var{...}`) and the licence prose are
    not the program's behaviour. Removing them is not summarising: what remains is still the
    authors' words, in their order.
    """
    text = re.sub(r"^@(?:c|comment|ignore)\b.*$", "", text, flags=re.M)
    text = re.sub(r"@(?:node|anchor|xref|pxref|ref|direntry|end direntry|menu|end menu|top|"
                  r"titlepage|end titlepage|settitle|cindex|vindex|findex|kindex|sp|newline|"
                  r"dots|indent|noindent|need|page|vskip|group|end group|example|end example|"
                  r"smallexample|end smallexample|smallformat|end smallformat|table|end table|"
                  r"item|itemx|enumerate|end enumerate|itemize|end itemize|quotation|"
                  r"end quotation|format|end format|display|end display|deffn|deffnx|defvr|"
                  r"defvrx|defun|defmac|defopt|deftypefn|deftypefnx|defcv|deftp)\b[^\n]*", "", text)
    text = re.sub(r"@[a-zA-Z]+\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"@[a-zA-Z]+", "", text)
    text = text.replace("\\-", "-").replace("``", '"').replace("''", '"')
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def section_for(manual: str, program: str) -> str:
    """The part of a manual that documents this one program.

    A family manual documents dozens of programs (`cmp invocation`, `cp invocation`), and the
    answer to a question about `cp` is not in the section about `cmp`. The section is delimited
    by the manual's own headings, which name the program.
    """
    name = str(program or "").strip().rsplit("/", 1)[-1].lower()
    if not name:
        return ""
    # Texinfo names a command's section exactly: `@node base32 invocation`. That is the manual's
    # own delimiter and it is unambiguous -- a table-of-contents line also mentions the program,
    # and choosing it returns the wrong section.
    node = re.compile(r"^@node\s+" + re.escape(name) + r"\s+invocation\s*$", re.M | re.I)
    found = node.search(manual)
    if found:
        after = manual[found.end():]
        nxt = re.search(r"^@node\s+", after, re.M)
        return _clean_texi(after[:nxt.start()] if nxt else after[:40000])
    cleaned = _clean_texi(manual)
    pattern = re.compile(r"^[^\n]*\b" + re.escape(name) + r"\b[^\n]*\n", re.M | re.I)
    starts = [m.start() for m in pattern.finditer(cleaned)]
    return cleaned[starts[0]:starts[0] + 20000] if starts else ""


def passages_for(program: str, question: str, *, limit: int = 3,
                 timeout: int = TIMEOUT_S) -> dict[str, Any]:
    """The manual's own sentences that speak to the question.

    Returns passages with their provenance. An empty result is reported as empty -- a manual
    that does not mention the question is a fact about the manual, and it is the caller's job to
    decide what to do with it.
    """
    got = fetch_manual(program, timeout=timeout)
    if not got.get("ok"):
        return {"schema": SCHEMA, "program": program, "ok": False,
                "reason": got.get("reason"), "passages": []}
    body = section_for(got["text"], program)
    words = {w for w in re.findall(r"[a-z][a-z0-9.+-]{2,}", str(question or "").lower())}
    sentences = re.split(r"(?<=[.!?:])\s+|\n\n", body)
    scored = []
    for sentence in sentences:
        flat = re.sub(r"\s+", " ", sentence).strip()
        if len(flat) < 24:
            continue
        shared = len(words & {w for w in re.findall(r"[a-z][a-z0-9.+-]{2,}", flat.lower())})
        if shared:
            scored.append((shared, flat))
    scored.sort(key=lambda item: -item[0])
    return {"schema": SCHEMA, "program": program, "ok": True, "repo": got.get("repo"),
            "url": got.get("url"), "sha256": got.get("sha256"),
            "passages": [text for _, text in scored[:limit]],
            "matched": len(scored), "section_chars": len(body)}


# --------------------------------------------------------------------- as a planner channel

def read_for_plan(tool: str, requirement: Mapping[str, Any], *,
                  limit: int = 3) -> dict[str, Any]:
    """The manual passages for a request the program's own pages did not settle.

    Called only when the planner has a gap: a word the request named that no page and no
    rejection could place. The question put to the manual is built from the request's own words
    plus the program's name -- not from a guess about what the manual might say -- and what
    comes back is quoted, with its URL, so it can be checked.

    This function does not change a plan. It returns text; the caller decides. That separation
    is deliberate: reading a manual is cheap and safe, and acting on it is neither, so the
    reading is never allowed to act by itself.
    """
    question = " ".join([str(requirement.get("instruction") or "")])
    got = passages_for(tool, question, limit=limit)
    if not got.get("ok"):
        return {"ok": False, "reason": got.get("reason"), "passages": []}
    words = {w for w in re.findall(r"[a-z][a-z0-9.+-]{2,}", question.lower())}
    useful = [p for p in got.get("passages") or []
              if len(set(re.findall(r"[a-z][a-z0-9.+-]{2,}", p.lower())) & words) >= 2]
    return {"ok": True, "url": got.get("url"), "repo": got.get("repo"),
            "sha256": got.get("sha256"), "passages": useful,
            "raw_matches": got.get("matched")}


# An example in a manual states a form: `sort --key=2,2` or `cut -f 2,3`. That is a fact about
# how the program is spelled, which no amount of reading a usage line produces, and which the
# program itself will confirm in one run.
_EXAMPLE = re.compile(r"(?<![\w-])(--?[A-Za-z][A-Za-z0-9-]*)(?:[= ]([A-Za-z0-9_,.:+/-]+))?")


def forms_in(passages: Sequence[str], flag: str,
             options: Sequence[Mapping[str, Any]] = ()) -> list[str]:
    """The ways the manual's own examples spell one option, e.g. `--key=2,2` for `--key`.

    Only the option the document already declares is accepted (`--key` must be in the program's
    own list), so a manual example can supply the *form* of a known flag but cannot introduce a
    flag the program does not document. That is the difference between reading a manual and
    trusting one.
    """
    declared = {str(o.get("flag")) for o in options or []}
    aliases = {}
    for option in options or []:
        for alias in option.get("aliases") or []:
            aliases[str(alias)] = str(option.get("flag"))
    spoken = []
    for passage in passages or []:
        for match in _EXAMPLE.finditer(str(passage)):
            name, value = match.group(1), match.group(2)
            canonical = name if name in declared else aliases.get(name)
            if canonical is None:
                continue
            if canonical != flag and name != flag:
                continue
            if value is None:
                continue
            value = value.strip(".,;:)]}")
            if not value:
                continue
            spoken.append(f"{canonical}={value}" if canonical.startswith("--") else
                          f"{canonical}{value}" if len(canonical) == 2 else canonical)
    # keep the order first seen, drop duplicates
    out, seen = [], set()
    for form in spoken:
        if form not in seen:
            seen.add(form)
            out.append(form)
    return out


def planned_forms(tool: str, requirement: Mapping[str, Any],
                  options: Sequence[Mapping[str, Any]], *, limit: int = 4
                  ) -> list[dict[str, Any]]:
    """Argv fragments the manual states for a flag the request's own words reach.

    The bridge is the document's option list: a flag whose *description* uses a word the request
    used (`--numeric-sort` says "numerical", and the request says "numerically") is the option
    the request is asking for. The manual then supplies how that option is spelled when it needs
    a value (`--key=2,2n`), which no usage line shows.

    Each fragment carries the passage and URL it came from, so a caller can check the claim
    instead of taking it. Nothing is returned when the manual states no form -- an empty result
    is the honest answer and is not filled with a guess.
    """
    import re as _re
    spoke = {w for w in _re.findall(r"[a-z][a-z0-9.+-]{2,}",
                                    str(requirement.get("instruction") or "").lower())}
    wanted = []
    for option in options or []:
        words = {w for w in _re.findall(r"[a-z][a-z0-9.+-]{2,}",
                                        str(option.get("words") or "").lower())}
        if words & spoke:
            wanted.append(str(option.get("flag")))
    if not wanted:
        return []
    got = read_for_plan(tool, requirement, limit=max(3, limit))
    if not got.get("ok"):
        return []
    out: list[dict[str, Any]] = []
    for flag in wanted:
        for form in forms_in(got.get("passages") or [], flag, options):
            out.append({"flag": flag, "form": form, "url": got.get("url"),
                        "sha256": got.get("sha256"),
                        "passage": next((p for p in got.get("passages") or []
                                         if form.split("=")[-1] in p or form in p), "")[:300]})
    return out[:limit]
