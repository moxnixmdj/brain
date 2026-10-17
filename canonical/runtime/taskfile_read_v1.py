"""Read task declarations from ANY structured file, by shape not by name.

The old discovery enumerated conventions -- Makefile, package.json,
pyproject.toml, bin/. Every environment with a different convention was
invisible, and enumerating conventions can never be general: there is
always one more.

A task declaration has one universal shape, whatever the file is called:

    a name, paired with a command

So stop asking "is this a Makefile" and start asking "does anything here
pair names with commands". Then Justfile, Rakefile, tasks.toml, Taskfile,
.github/workflows and formats that do not exist yet all fall out of the
same code.

Extraction is deliberately structural, not semantic:

  makefile-ish   "name:" followed by tab-indented command lines
  mapping-ish    any dict whose values look like shell commands
  sequence-ish   list items carrying a name and a run/command/cmd field

A pair is only emitted when the value actually LOOKS like a command, so
ordinary config does not turn into phantom tasks. That test is the whole
safety property of this module.
"""
from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_TASKFILE_READ_V1"

_CONFIG_EXT = {".toml", ".json", ".yaml", ".yml", ".ini", ".cfg"}
_CONFIG_NAMES = {"Justfile", "justfile", "Rakefile", "Taskfile",
                 "Taskfile.yml", "Earthfile", "Procfile", ".tasks"}

# A value is only treated as a command if it starts with something runnable.
_CMD_HEAD = re.compile(
    r"^\s*(?:python3?|sh|bash|zsh|make|npm|npx|yarn|pnpm|poetry|pipenv|"
    r"cargo|go|mvn|gradle|bundle|rake|just|docker|docker-compose|terraform|"
    r"ansible|ruby|perl|node|deno|./|[A-Za-z0-9_./-]+)\b")
_SHELLISH = re.compile(r"(?:^|\s)(?:&&|\||;|>\s|\$\(|>>)|\s-{1,2}[A-Za-z]")

# Directories worth reading that a naive walk skips or drowns in.
_EXTRA_DIRS = (".ci", ".github/workflows", ".buildkite", ".circleci",
               "scripts", "bin", "tools", "tasks", "ci")


_TOOLS = {"python3", "python", "sh", "bash", "zsh", "dash", "make", "gmake",
          "npm", "npx", "yarn", "pnpm", "poetry", "pipenv", "pip", "cargo",
          "go", "mvn", "gradle", "bundle", "rake", "just", "docker",
          "docker-compose", "terraform", "ansible", "ruby", "perl", "node",
          "deno", "echo", "curl", "wget", "git", "sed", "awk", "cp", "mv",
          "rm", "mkdir", "touch", "tar", "zip", "unzip", "pytest", "tox",
          "black", "ruff", "mypy", "flake8", "uv"}
_VERSIONISH = re.compile(r"^v?\d+(?:\.\d+)*[a-z]?$")
_URLISH = re.compile(r"^[a-z][a-z0-9+.-]*://|^www\.", re.I)
_FILE_EXT = re.compile(r"\.[A-Za-z0-9_+~-]{1,10}\b")
# Extensions that can actually be executed, versus merely compiled
# or read. .rs/.toml/.md are content, not programs.
_RUNNABLE_EXT = re.compile(
    r"\.(?:sh|bash|zsh|py|py3|rb|pl|js|mjs|cjs|ps1|bat|cmd|exe|bin|run)$",
    re.I)
_MAKE_KEYWORDS = {"ifeq", "ifneq", "ifdef", "ifndef", "else", "endif",
                  "include", "-include", "sinclude", "export",
                  "unexport", "define", "endef", "override", "vpath"}


def _looks_like_command(value: str) -> bool:
    """The safety property: config values are not tasks.

    The first version ended in a catch-all `[A-Za-z0-9_./-]+`, which matches
    literally any single word -- so "2.1.0" and "run make deploy to ship"
    both passed, and every string in every config became a phantom task.

    A value is runnable only if its head is a known tool, or it is a path,
    or it carries shell structure. A bare unknown word is not a command.
    """
    v = (value or "").strip()
    if not v or len(v) > 400 or "\n" in v:
        return False
    if _VERSIONISH.match(v):
        return False
    # A URL is not a command. This was found on a REAL repository, not a
    # synthetic one: pyproject.toml declares [project.urls], and
    # "https://requests.readthedocs.io" passed the "contains a slash so it
    # is a path" test. Two of five "tasks" in psf/requests were web
    # addresses. Every environment I built myself lacked URLs, so no test
    # I wrote could have caught it.
    if _URLISH.match(v):
        return False
    parts = v.split()
    head = parts[0]
    if head in _TOOLS:
        return True
    if head.startswith("./") or head.startswith("../") \
            or head.startswith("/") or head.startswith("~/"):
        return True                      # explicitly rooted program path
    if "/" in head and _RUNNABLE_EXT.search(head):
        return True                      # a path to something executable
    # A source file is not a program. mdBook's Cargo.toml names
    # "examples/remove-emphasis/test.rs", which has an extension and so
    # passed -- but .rs is compiled, not run. Requiring a runnable
    # extension is the difference between a script and a source tree.
    # "crates/mdbook-core" is a LOCATION, not a program, and
    # "expressjs/express" is a repository slug. Both contain slashes,
    # which is why the old rule accepted them. Neither can be executed.
    if len(parts) == 1:
        return False                     # bare unknown word: not a command
    return bool(_SHELLISH.search(v))     # multiword: needs shell structure


def _from_makefile(path: Path) -> list[tuple[str, str]]:
    out, cur, body = [], None, []
    for line in path.read_text(errors="replace").splitlines():
        # Tabs (make) or 2+ leading spaces (just, Taskfile). One space is
        # not a recipe -- that is prose wrapping onto a second line.
        if cur and (line.startswith("\t")
                    or (line.startswith("  ") and line.strip()
                        and not line.strip().startswith("#"))):
            body.append(line.strip())
            continue
        if cur and body:
            out.append((cur, " ".join(b for b in body if b)))
        cur, body = None, []
        if line and not line[0].isspace() and ":" in line and "=" not in line:
            name = line.split(":", 1)[0].strip()
            # Skip Make's own syntax. cobra's Makefile produced a "target"
            # called $(warning "could not find golangci-lint in $(PATH)...
            # because a function call sits at column zero and contains a
            # colon. Conditionals and directives are not tasks either.
            if name.startswith("$(") or name.split()[0] in _MAKE_KEYWORDS:
                cur, body = None, []
                continue
            if name and not name.startswith("."):
                cur = name
    if cur and body:
        out.append((cur, " ".join(b for b in body if b)))
    return [(n, c) for n, c in out if _looks_like_command(c)]


def _walk_mapping(obj, out: list) -> None:
    """Any dict of name -> command-ish value, at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            # The value itself must look runnable. A "sh -c " prefix was
            # tried here and it made EVERY string match, turning prose into
            # phantom tasks: env_hard2's config.json yielded
            # description/notes/version as "tasks". Prose is not a task.
            if isinstance(v, str) and _looks_like_command(v):
                out.append((str(k), v))
            elif isinstance(v, (dict, list)):
                _walk_mapping(v, out)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                name = item.get("name") or item.get("task") or item.get("id")
                cmd = item.get("run") or item.get("cmd") or item.get("command")
                if isinstance(name, str) and isinstance(cmd, str) \
                        and _looks_like_command(cmd):
                    out.append((name, cmd))
                else:
                    _walk_mapping(item, out)
            else:
                _walk_mapping(item, out)


def _from_yaml(path: Path) -> list[tuple[str, str]]:
    """Minimal indentation reader for CI workflows. No dependency.

    PyYAML is not available in every environment, and a machine that cannot
    read a format cannot see the tasks written in it -- .github/workflows
    held both a real task and a destructive one, and both were invisible.

    Only the shape needed is parsed: a `name:` and a `run:` at the SAME
    indentation. That is a task. Everything else is ignored rather than
    guessed at, because a wrong parse here becomes a command that runs.
    """
    out: list[tuple[str, str]] = []
    pending: dict[int, str] = {}          # indent -> most recent name
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return out
    for raw in lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if line.startswith("- "):
            line = line[2:].strip()
            indent += 2
        key, sep, val = line.partition(":")
        if not sep:
            continue
        key, val = key.strip(), val.strip()
        if key == "name" and val:
            pending[indent] = val
        elif key in {"run", "cmd", "command"} and val:
            label = pending.get(indent) or "step%d" % len(out)
            out.append((label, val))
    return [(n_, c) for n_, c in out if _looks_like_command(c)]


def read_tasks(root: str) -> list[dict]:
    """Every (name, command) pair this directory declares, however declared."""
    rootp = Path(root)
    found: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def emit(name, cmd, origin):
        key = (str(name), str(cmd))
        if key in seen or not _looks_like_command(str(cmd)):
            return
        seen.add(key)
        found.append({"name": str(name), "command": str(cmd),
                      "origin": origin, "risk": risk_of(str(cmd))})

    candidates = []
    for dirpath, dirnames, filenames in __import__("os").walk(rootp):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "__pycache__", "node_modules",
                                    ".venv", ".pytest_cache"}]
        rel = Path(dirpath).relative_to(rootp)
        if len(rel.parts) > 3:
            dirnames[:] = []
            continue
        for fn in filenames:
            fp = Path(dirpath) / fn
            if fn in _CONFIG_NAMES or fp.suffix in _CONFIG_EXT:
                candidates.append(fp)

    for fp in candidates[:400]:
        rel = str(fp.relative_to(rootp))
        try:
            text = fp.read_text(errors="replace")
        except OSError:
            continue
        if fp.name in {"Justfile", "justfile", "Rakefile", "Taskfile"} \
                or fp.name == "Makefile":
            for n, c in _from_makefile(fp):
                emit(n, c, rel)
            continue
        obj = None
        try:
            if fp.suffix == ".toml":
                import tomllib
                obj = tomllib.loads(text)
            elif fp.suffix == ".json":
                obj = json.loads(text)
        except Exception:
            obj = None
        if obj is None and fp.suffix in {".yaml", ".yml"}:
            try:
                import yaml
                obj = yaml.safe_load(text)
            except Exception:
                obj = None
        if obj is not None:
            pairs: list = []
            _walk_mapping(obj, pairs)
            for n, c in pairs:
                emit(n, c, rel)
        elif fp.suffix in {".yaml", ".yml"}:
            # No YAML parser here -- read the shape directly rather than
            # deciding the format is unreadable.
            for n_, c in _from_yaml(fp):
                emit(n_, c, rel)
    return found


_DESTRUCTIVE = re.compile(
    r"(?:^|\s)(?:rm\s+-[rRf]|rm\s+-rf|rmdir|dd\s+if=|mkfs|shred|truncate|"
    r"drop\s+(?:table|database)|delete\s+from|git\s+clean\s+-[fFx]|"
    r"git\s+reset\s+--hard|git\s+push\s+--force|kubectl\s+delete|"
    r"terraform\s+destroy|:\s*>|>/dev/|--force|--hard)"
)
_WRITEY = re.compile(r"(?:^|\s)(?:rm\s|mv\s|cp\s|tee\s|>\s*[$'\w])")


def risk_of(command: str) -> str:
    """Classify what a command could do, before anyone runs it.

    A self-directing system that executes destructive commands simply
    because it discovered them is not autonomous, it is dangerous.
    env_hard2's CI declared `poison: rm -f out/good.txt` -- a real task
    from the environment's own point of view, and one that destroys the
    output of another task.

    destructive  can delete or overwrite irrecoverably
    mutating     writes, moves or removes something specific
    readonly     nothing here suggests it changes anything
    """
    c = (command or "").strip()
    if not c:
        return "readonly"
    if _DESTRUCTIVE.search(c):
        return "destructive"
    if _WRITEY.search(c):
        return "mutating"
    return "readonly"


def task_commands(root: str, allow_destructive: bool = False) -> list[list[str]]:
    """Run each declared task -- through its own runner where one exists.

    Destructive tasks are still DISCOVERED and reported. They are simply not
    handed to the executor unless the caller explicitly accepts the risk.
    Seeing a weapon is information; firing it is a decision.

    package.json scripts go through `npm run`, not through the raw command
    text. Running "mocha --require ..." directly fails with command-not-found,
    because mocha lives in node_modules/.bin and only npm puts that on PATH.
    The declaration is not the invocation: npm sets up the environment the
    command expects, and re-deriving that by hand is how real projects end
    up looking broken when they are not.
    """
    cmds = []
    for t in read_tasks(root):
        if t.get("risk") == "destructive" and not allow_destructive:
            continue
        name = t.get("name") or ""
        origin = (t.get("origin") or "").lower()
        try:
            if origin.endswith("package.json") and name:
                cmds.append(["npm", "run", "--silent", name])
            else:
                cmds.append(["sh", "-c", t["command"]])
        except Exception:
            continue
    return cmds
    """Run each declared task through the shell it was written for."""
    cmds = []
    for t in read_tasks(root):
        try:
            cmds.append(["sh", "-c", t["command"]])
        except Exception:
            continue
    return cmds


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    for t in read_tasks(root):
        print(f"  {t['name']:<16} {t['command'][:52]:<54} [{t['origin']}]")
