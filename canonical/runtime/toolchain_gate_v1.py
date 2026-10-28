# PROJECT_BRAIN
"""python.toolchain.gate.v1 — a capability is the adapter PLUS the software it calls, and the
door must not promise the second half without checking it.

Measured, on the same commit, three times (43 acts, `execution_guard/hardcore_se_missing_verb_probe_v1.py`):

    before the gate, .venv                 32 answered / 11 honest /  0 owned-but-failed / 0 silent
    before the gate, /usr/bin/python3      16 answered / 11 honest / 13 owned-but-failed / 3 silent
    after  the gate, /usr/bin/python3      18 answered / 25 honest /  0 owned-but-failed / 0 silent

Half of what this machine says it can do evaporated on a clean box, and it evaporated *as a
capability defect* -- `python.toolchain.ruff_lint.v1` was reported broken when ruff was never
installed.  The 25 refusals are exactly the 14 acts the installed toolchain supplies plus the 11
goal-level refusals that were already honest; not one working act is refused.  That is the same misreporting Class B and P1 already fixed twice at other layers: a
confident wrong answer (here: "the capability is broken") costs more than an honest one ("ruff is
missing; install it with this command").

The law, in order of preference:

1. **the tool is there** -> run.
2. **the tool is missing and this interpreter is one we manage** (a venv, not a system
   interpreter, not an externally-managed environment) -> INSTALL it from the pinned declaration,
   then run.  Autonomy where it is safe: the machine does not need a human to pip install.
3. **otherwise** -> REFUSE, naming the tool and the exact command that installs it.  Never
   "capability failed", never an empty success.

The tool set for a capability is not guessed.  `TOOLCHAIN_DECLARATION_V1.json` states it per
capability (`capability_tools`), because one adapter serves many verbs and the adapter's union
would make `ruff_format` demand mypy; an empty row is the claim "no external tool", and is
authoritative.  Only a capability the declaration does not mention falls back to reading its
adapter's own source -- `["-m", "ruff"]`, `_resolve_tool("ruff")`, `shutil.which("git")` -- since a
quoted word is not a dependency (a looser scan refused `quality_v1` for "perf", a metric label).

Cached per interpreter, because this runs on every request: a dict lookup, ~0 ms after the first.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DECLARATION = ROOT / "canonical/runtime/TOOLCHAIN_DECLARATION_V1.json"

# Modules that exist wherever python does; naming one of these is not a dependency.
_STDLIB = {
    "ast", "asyncio", "base64", "binascii", "bisect", "builtins", "calendar", "collections",
    "concurrent", "contextlib", "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal",
    "difflib", "enum", "errno", "fnmatch", "fractions", "functools", "gc", "getpass", "glob",
    "gzip", "hashlib", "heapq", "hmac", "html", "http", "importlib", "inspect", "io", "ipaddress",
    "itertools", "json", "keyword", "linecache", "locale", "logging", "lzma", "marshal", "math",
    "mimetypes", "multiprocessing", "operator", "os", "pathlib", "pickle", "pkgutil", "platform",
    "pprint", "queue", "random", "re", "secrets", "selectors", "shlex", "shutil", "signal",
    "site", "socket", "sqlite3", "ssl", "stat", "statistics", "string", "struct", "subprocess",
    "sys", "sysconfig", "tarfile", "tempfile", "textwrap", "threading", "time", "timeit",
    "tokenize", "traceback", "tracemalloc", "types", "typing", "unicodedata", "unittest",
    "urllib", "uuid", "venv", "warnings", "weakref", "xml", "zipfile", "zlib", "cProfile",
    "profile", "pstats", "doctest", "compileall", "py_compile", "lib2to3",
}

# External binaries an adapter may name.  Only these are checked with `which`, because a bare
# string is not a promise: `re.search("...")` must not make the gate demand a program called
# "search".
_BINARIES = {
    "git", "jq", "yq", "node", "npm", "npx", "make", "gcc", "cc", "clang", "cmake", "cargo",
    "rustc", "go", "java", "javac", "mvn", "gradle", "docker", "podman", "kubectl", "terraform",
    "gdb", "lldb", "strace", "ltrace", "perf", "valgrind", "py-spy", "memray", "hyperfine",
    "shellcheck", "hadolint", "tesseract", "qrencode", "zbarimg", "pandoc", "chromedriver",
    "openssl", "gpg", "tar", "gzip", "zstd", "unzip", "curl", "rsync", "sqlite3", "psql",
}

_CACHE: dict[str, tuple[bool, list[str], list[str]]] = {}
_TOOLS_CACHE: dict[str, tuple[list[str], list[str]]] = {}


def _declaration() -> dict[str, Any]:
    try:
        return json.loads(DECLARATION.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _pins(modules: list[str]) -> list[str]:
    """The pinned requirements for these import names, from the declaration."""
    distribution = (_declaration().get("distribution") or {})
    pins: list[str] = []
    for module in modules:
        for name, entry in distribution.items():
            if str(entry.get("import") or "") == module:
                version = str(entry.get("version") or "")
                pins.append(f"{name}=={version}" if version else name)
                break
    return pins


def required_tools(module_path: Path) -> tuple[list[str], list[str]]:
    """(python modules, external binaries) the adapter itself names.  Cached by path."""
    key = str(module_path)
    if key in _TOOLS_CACHE:
        return _TOOLS_CACHE[key]
    try:
        source = module_path.read_text(encoding="utf-8")
    except OSError:
        _TOOLS_CACHE[key] = ([], [])
        return _TOOLS_CACHE[key]
    # ONLY WHAT THE ADAPTER PROVABLY INVOKES.  A quoted word is not a dependency: an earlier,
    # looser scan read `"perf"` out of a display-name dict and `"sqlite3"` out of a dict key in
    # quality_v1 and would have refused a working capability for a program it never runs.  Three
    # shapes mean "this is executed", and nothing else counts:
    #   ["-m", "ruff", ...]          a module invocation
    #   _resolve_tool("ruff")        the helpers this repository uses to find a tool
    #   shutil.which("git")          an explicit PATH lookup
    modules: list[str] = []
    for match in re.finditer(r'"-m"\s*,\s*"([A-Za-z_][A-Za-z0-9_.]*)"', source):
        name = match.group(1).split(".")[0]
        if name not in _STDLIB and name not in modules:
            modules.append(name)
    binaries: list[str] = []
    for pattern in (r'_resolve_tool\(\s*"([A-Za-z][A-Za-z0-9_+-]*)"\s*\)',
                    r'shutil\.which\(\s*"([A-Za-z][A-Za-z0-9_+-]*)"\s*\)',
                    r'"(?:-m)"\s*,\s*"([A-Za-z][A-Za-z0-9_+-]*)"'):
        for match in re.finditer(pattern, source):
            name = match.group(1)
            if name in _STDLIB or name in modules or name in binaries:
                continue
            # a helper may look up either kind; the SET decides which check applies, and a
            # name that is neither a known binary nor importable is reported as a module so the
            # refusal can still name it
            if name in _BINARIES:
                binaries.append(name)
            else:
                modules.append(name)
    _TOOLS_CACHE[key] = (modules, binaries)
    return modules, binaries


def _importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def _managed_interpreter() -> bool:
    """True when installing here is safe: a venv we can write, not a system/externally-managed one."""
    if os.environ.get("BRAIN_TOOLCHAIN_INSTALL") == "0":
        return False
    if sys.prefix == sys.base_prefix:
        return False  # not a virtualenv
    marker = Path(sys.prefix) / "pyvenv.cfg"
    if not marker.is_file():
        return False
    return os.access(str(Path(sys.prefix) / "lib"), os.W_OK)


def install(modules: list[str], timeout_s: int = 180) -> tuple[bool, str]:
    """Install the pinned distributions for these modules into THIS interpreter."""
    pins = _pins(modules) or modules
    if not pins:
        return False, "not declared"
    try:
        proc = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                               "--disable-pip-version-check"] + pins,
                              capture_output=True, text=True, timeout=timeout_s, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)[:200]
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "").strip()[-200:]
    for name in modules:
        importlib.invalidate_caches()
        if not _importable(name):
            return False, "installed but still not importable: " + name
    return True, "installed " + " ".join(pins)


def declared_tools(capability_id: str) -> list[str] | None:
    """The MEASURED per-capability tool list, when the declaration states one.

    Static attribution reads the tools out of a shared adapter, which gives every verb the union
    of what the module can call -- `ruff_format` would demand mypy.  The declaration's
    `capability_tools` map is per verb and every row in it was measured (see its `why`).
    """
    mapping = (_declaration().get("capability_tools") or {})
    if capability_id not in mapping:
        return None            # unstated: fall back to reading the adapter
    return [str(name) for name in (mapping.get(capability_id) or [])]


def _split(names: list[str]) -> tuple[list[str], list[str]]:
    modules = [n for n in names if n not in _BINARIES and n not in _STDLIB]
    binaries = [n for n in names if n in _BINARIES]
    return modules, binaries


def check(capability_id: str, module_path: str | Path | None,
          allow_install: bool = True) -> tuple[bool, list[str], list[str], str]:
    """(ok, missing, installed, detail) for one capability.

    `ok` is False only when the capability cannot run; `missing` then names what is absent, in
    the words a reader can act on.
    """
    stated = declared_tools(capability_id)
    if stated is not None:
        modules, binaries = _split(stated)
    elif module_path is None:
        modules, binaries = [], []
    else:
        modules, binaries = required_tools(Path(module_path))
    if not modules and not binaries:
        return True, [], [], ""
    key = f"{capability_id}|{sys.executable}|{allow_install}"
    if key in _CACHE:
        ok, missing, installed = _CACHE[key]
        return ok, missing, installed, ""

    missing = [name for name in modules if not _importable(name)]
    missing_bins = [name for name in binaries if shutil.which(name) is None]
    installed: list[str] = []
    if missing and allow_install and _managed_interpreter():
        ok_install, detail = install(missing)
        if ok_install:
            installed = list(missing)
            missing = []
        else:
            _CACHE[key] = (False, missing + missing_bins, installed)
            return False, missing + missing_bins, installed, detail
    missing_all = missing + missing_bins
    _CACHE[key] = (not missing_all, missing_all, installed)
    return not missing_all, missing_all, installed, ""


def refuse_reason(missing: list[str]) -> str:
    """A refusal a reader can act on: what is missing and the one command that installs it."""
    pins = _pins([name for name in missing])
    command = ("python3 execution_guard/toolchain_preflight_v1.py --bootstrap")
    detail = "TOOLCHAIN_MISSING:" + ",".join(missing)
    if pins:
        detail += " (declared: " + " ".join(pins) + ")"
    return detail + "; install with: " + command


def status() -> dict[str, Any]:
    """What this interpreter can and cannot run, for the receipt."""
    return {
        "interpreter": sys.executable,
        "managed": _managed_interpreter(),
        "declared_distributions": len(_declaration().get("distribution") or {}),
        "install_allowed": os.environ.get("BRAIN_TOOLCHAIN_INSTALL") != "0",
    }
