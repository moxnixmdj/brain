"""The two acts that stand between this machine and using any project it is pointed at.

`dependency_add` and `build_package` are the entry points to the whole pypi lane: nothing that
needs a new dependency or a distributable artifact can be served until a project can be edited and
packed. Neither needs a new tool, and neither needed to be invented:

  dependency_add   the manifest is already parsed here -- `environment_fit_v1` reads
                   `[project].dependencies` and `requirements*.txt` with `tomllib` to decide what
                   to install.  Adding a dependency is the same read, plus one inserted line.
  build_package    `pip wheel` is installed, it is the tool that builds wheels, and it does it in
                   1.5 seconds on a small project.  The oracle is the artifact: a wheel is a zip
                   with a `.dist-info/METADATA` inside it, and that is checkable with `zipfile`.

The rules both verbs keep:

  * the manifest is SPLICED, never re-serialised -- the same law the bound registry obeys.  A tool
    that loads a project file and dumps it back rewrites formatting the owner wrote;
  * the act is IDEMPOTENT and says which it was: `already_present: true` is an answer, not a
    failure, and it still writes the artifact;
  * the refusal names the reason (`NO_MANIFEST`, `NO_DEPENDENCY_LIST`, `BUILD_FAILED:<tail>`),
    because an empty result is never how "I did not do it" is reported;
  * the artifact law is `quality_v1`'s -- the same digest, the same verification, the same FAIL
    artifact on refusal -- rather than a second implementation of it.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from canonical.runtime.bound_capabilities.quality_v1 import (
    QualityError,
    _base,
    _destination,
    _fail,
    _inside,
    _write,
)

DEFAULT_TIMEOUT_S = 600

_MANIFEST_NAMES = ("pyproject.toml", "setup.cfg")

# A requirement string as PEP 508 writes it: name, optional extras, optional specifier, optional
# marker.  The NAME is what decides whether the dependency is already there -- `requests>=2` and
# `requests` are the same dependency asked for twice.
_REQUIREMENT = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<rest>.*)$")


def _requirement_name(spec: str) -> str:
    found = _REQUIREMENT.match(str(spec or ""))
    return (found.group("name") if found else "").lower().replace("_", "-").replace(".", "-")


def _project_root(target: Path) -> Path:
    """The directory that owns the manifest, whether we were pointed at the file or the folder."""
    if target.is_file():
        return target.parent
    return target


def _find_manifest(project: Path) -> Path | None:
    for name in _MANIFEST_NAMES:
        candidate = project / name
        if candidate.is_file():
            return candidate
    requirements = sorted(project.glob("requirements*.txt"))
    return requirements[0] if requirements else None


# --------------------------------------------------------------------------- dependency_add


def _dependency_block(text: str) -> tuple[int, int] | None:
    """The character span of the `dependencies = [ ... ]` array inside `[project]`.

    Deliberately a scan and not a parse-then-dump: the manifest is the owner's file, and the only
    thing this verb is allowed to do to it is insert one line.  The scan is anchored on the
    `[project]` table so a `dependencies` key under `[tool.*]` cannot be edited by mistake.
    """
    table = re.search(r"^\[project\]\s*$", text, re.MULTILINE)
    if table is None:
        return None
    end_of_table = re.search(r"^\[", text[table.end():], re.MULTILINE)
    stop = table.end() + (end_of_table.start() if end_of_table else len(text) - table.end())
    key = re.search(r"^dependencies\s*=\s*\[", text[table.end():stop], re.MULTILINE)
    if key is None:
        return None
    start = table.end() + key.start()
    opened = text.index("[", start)
    depth = 0
    in_str: str | None = None
    for index in range(opened, len(text)):
        char = text[index]
        if in_str:
            if char == "\\":
                continue
            if char == in_str and text[index - 1] != "\\":
                in_str = None
            continue
        if char in "\"'":
            in_str = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return start, index + 1
    return None


def _existing_dependency_names(text: str) -> list[str]:
    span = _dependency_block(text)
    if span is None:
        return []
    body = text[span[0]:span[1]]
    return [_requirement_name(m) for m in re.findall(r"[\"']([^\"']+)[\"']", body)]


def _requirements_lines(text: str) -> list[str]:
    """The requirement lines a requirements file states, comments and blanks removed."""
    return [line.split("#", 1)[0].strip() for line in text.splitlines()
            if line.split("#", 1)[0].strip()]


def _requirements_names(text: str) -> list[str]:
    return [_requirement_name(line) for line in _requirements_lines(text)]


def _dependency_add(args, target: Path, cap: str) -> dict:
    spec = str(args.get("dependency") or args.get("distribution") or args.get("requirement")
               or "").strip()
    if not spec:
        _fail("DEPENDENCY_NOT_STATED")
    if spec.startswith("-") or "\n" in spec:
        # A manifest is code that an installer will execute.  A line that starts an option, or
        # carries a second line, is not a requirement and cannot be spliced in as one.
        _fail("DEPENDENCY_NOT_A_REQUIREMENT:" + spec[:60])
    project = _project_root(target)
    manifest = _find_manifest(project)
    if manifest is None:
        _fail("NO_MANIFEST:" + str(project))
    text = manifest.read_text(encoding="utf-8")
    wanted = _requirement_name(spec)

    if manifest.suffix == ".txt":
        names = _requirements_names(text)
        already = wanted in names
        if not already:
            separator = "" if text.endswith("\n") or not text else "\n"
            manifest.write_text(text + separator + spec + "\n", encoding="utf-8")
        new_text = manifest.read_text(encoding="utf-8")
        verified = wanted in _requirements_names(new_text)
        return {
            **_base(cap, "dependency_add", target),
            "manifest": str(manifest),
            "manifest_kind": "requirements",
            "dependency": spec,
            "already_present": already,
            "line": spec,
            "verified": verified,
            "dependencies": _requirements_lines(new_text),
        }

    span = _dependency_block(text)
    if span is None:
        _fail("NO_DEPENDENCY_LIST:" + str(manifest))
    names = _existing_dependency_names(text)
    already = wanted in names
    if not already:
        block = text[span[0]:span[1]]
        close = span[1] - 1
        line_start = text.rfind("\n", span[0], close) + 1
        indent = text[line_start:close]
        if indent.strip():
            # one-line array: `dependencies = ["a", "b"]`
            opened = text.index("[", span[0])
            inner = block[block.index("[") + 1:block.rindex("]")].strip()
            joined = (inner + ", " if inner else "") + json.dumps(spec)
            # replace the ARRAY, not the whole `dependencies = ...` assignment: the first version
            # replaced from the key, which deleted the assignment and produced a manifest that no
            # longer parsed -- caught by the re-read verification, not by the splice.
            edited = text[:opened] + "[" + joined + "]" + text[span[1]:]
        else:
            # multi-line array: insert a line with the same indentation as the last entry
            last_line_start = text.rfind("\n", 0, close) + 1
            previous = text.rfind("\n", 0, last_line_start - 1) + 1
            previous_line = text[previous:last_line_start]
            entry_indent = re.match(r"\s*", previous_line).group(0) or indent + "    "
            insert = entry_indent + json.dumps(spec) + ",\n"
            edited = text[:last_line_start] + insert + text[last_line_start:]
        manifest.write_text(edited, encoding="utf-8")

    # THE EDIT IS VERIFIED BY RE-READING THE MANIFEST, NOT BY TRUSTING THE SPLICE.
    new_text = manifest.read_text(encoding="utf-8")
    try:
        import tomllib
        parsed = tomllib.loads(new_text)
    except Exception as exc:  # noqa: BLE001 - an unparseable manifest is the finding
        _fail("MANIFEST_NO_LONGER_PARSES:" + type(exc).__name__ + ":" + str(exc)[:120])
    declared = [str(x) for x in (((parsed.get("project") or {}).get("dependencies")) or [])]
    verified = sum(1 for d in declared if _requirement_name(d) == wanted) == 1
    if not verified:
        _fail("DEPENDENCY_NOT_IN_THE_MANIFEST_AFTER_THE_EDIT:" + wanted)
    # ...and nothing else moved: the same bytes except the line that was added.
    before = [line for line in text.splitlines() if line.strip()]
    after = [line for line in new_text.splitlines() if line.strip()]
    added = [line for line in after if line not in before]
    removed = [line for line in before if line not in after]
    # A one-line array has to be rewritten to grow, so the law is not "every line survives" --
    # it is "nothing outside the dependency array moved".  A removed line is allowed only when it
    # is the array's own line, i.e. when every requirement it stated is still declared.
    for line in removed:
        quoted = re.findall(r"[\"']([^\"']+)[\"']", line)
        if quoted and all(any(_requirement_name(q) == _requirement_name(d) for d in declared)
                          for q in quoted):
            continue
        _fail("EDIT_REWROTE_EXISTING_LINES:" + line[:80])
    return {
        **_base(cap, "dependency_add", target),
        "manifest": str(manifest),
        "manifest_kind": "pyproject",
        "dependency": spec,
        "already_present": already,
        "lines_added": added,
        "verified": verified,
        "dependencies": declared,
        "other_lines_changed": 0,
    }


# --------------------------------------------------------------------------- build_package


def _wheel_metadata(wheel: Path) -> dict:
    """What the artifact says about itself, read out of the artifact.

    A wheel is a zip with `<name>-<version>.dist-info/METADATA` inside it.  Reading that is the
    whole verification: a build that produced a file with the wrong name, no metadata, or no
    RECORD has not built the package it claims to have built.
    """
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = [n for n in names if n.endswith(".dist-info/METADATA")]
        record = [n for n in names if n.endswith(".dist-info/RECORD")]
        if not metadata:
            _fail("WHEEL_HAS_NO_METADATA:" + wheel.name)
        if not record:
            _fail("WHEEL_HAS_NO_RECORD:" + wheel.name)
        raw = archive.read(metadata[0]).decode("utf-8", "replace")
        modules = sorted({n.split("/")[0] for n in names
                          if "/" in n and ".dist-info" not in n and ".data" not in n})
    fields = {}
    for line in raw.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()
    return {
        "dist_info": metadata[0].split("/")[0],
        "name": fields.get("name", ""),
        "version": fields.get("version", ""),
        "requires_python": fields.get("requires-python", ""),
        "requires_dist": [f.strip() for f in fields.get("requires-dist", "").split(",")
                          if f.strip()],
        "member_count": len(names),
        "top_level": modules,
        "has_record": True,
    }


def _build_package(args, target: Path, cap: str) -> dict:
    project = _project_root(target)
    manifest = _find_manifest(project)
    if manifest is None:
        _fail("NO_MANIFEST:" + str(project))
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    python = str(args.get("python_executable") or sys.executable)
    wheelhouse = Path(tempfile.mkdtemp(prefix="brain_wheel_"))
    # `pip wheel` is the tool that builds wheels, and it is already installed.  Building in a
    # temporary wheelhouse means the project is not polluted and a stale wheel cannot be mistaken
    # for a fresh one.
    proc = subprocess.run(
        [python, "-m", "pip", "wheel", "--no-deps", "--quiet",
         "--wheel-dir", str(wheelhouse), str(project)],
        capture_output=True, text=True, timeout=timeout_s, cwd=str(project), check=False,
    )
    wheels = sorted(wheelhouse.glob("*.whl"))
    if proc.returncode != 0 or not wheels:
        tail = ((proc.stderr or proc.stdout or "").strip().splitlines() or ["<no output>"])[-1]
        _fail("BUILD_FAILED:" + tail[:200])
    wheel = max(wheels, key=lambda p: p.stat().st_mtime)
    data = _wheel_metadata(wheel)
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    # The wheel is kept where the caller can find it, named by its own metadata.
    keep_dir = Path(project) / "dist"
    keep_dir.mkdir(parents=True, exist_ok=True)
    kept = keep_dir / wheel.name
    if not kept.exists() or hashlib.sha256(kept.read_bytes()).hexdigest() != digest:
        kept.write_bytes(wheel.read_bytes())
    return {
        **_base(cap, "build_package", target),
        "manifest": str(manifest),
        "wheel": str(kept),
        "wheel_name": wheel.name,
        "wheel_sha256": digest,
        "wheel_bytes": kept.stat().st_size,
        **{k: data[k] for k in ("name", "version", "requires_python", "requires_dist",
                                "member_count", "top_level", "has_record")},
        "verified": bool(data["name"]) and bool(data["version"]) and data["has_record"],
    }


_HANDLERS = {
    "dependency_add": _dependency_add,
    "build_package": _build_package,
}


def run(args: dict, root: Path) -> dict:
    """The one entrypoint, with the artifact law `quality_v1` already established."""
    args = dict(args or {})
    root = Path(root)
    verb = str(args.get("act_verb") or "").strip()
    capability_id = str(args.get("capability_id") or "")
    output_path = str(args.get("output_path") or "").strip()
    if not output_path:
        _fail("OUTPUT_PATH_NOT_STATED")
    destination = _destination(root, output_path)
    try:
        if verb not in _HANDLERS:
            _fail("ACT_NOT_SUPPORTED:" + (verb or "<none>"))
        stated = str(args.get("source_root") or args.get("path") or args.get("project_path")
                     or "").strip()
        if not stated:
            _fail("PATH_NOT_STATED")
        target = _inside(root, stated)
        if target is None:
            _fail("PATH_NOT_IN_THE_REPOSITORY:" + stated)
        payload = _HANDLERS[verb](args, target, capability_id)
    except QualityError as exc:
        _write(destination, {"adapter": "packaging_v1", "capability_id": capability_id,
                             "act": verb, "gate": "FAIL", "reason": str(exc)})
        raise
    return _write(destination, payload)
