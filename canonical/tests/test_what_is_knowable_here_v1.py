"""Pins the mechanism of the knowable-here instrument on a synthetic host.

The real host is measured by the runner; these tests use three tiny programs so the
bits that matter (citation, contradiction, perishability, retention) fail loudly if
they are quietly broken later.
"""
from __future__ import annotations

import json
import pathlib
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import what_is_knowable_here_v1 as know  # noqa: E402

HONEST = """#!/bin/sh
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "Usage: honest [-o OUT] FILE" >&2
  echo "options: --output --verbose" >&2
  exit 0
fi
out=/dev/stdout
if [ "$1" = "-o" ]; then out="$2"; shift 2; fi
printf 'honest %s\\n' "$1" > "$out"
"""

LIAR = """#!/bin/sh
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "Usage: liar --output FILE" >&2
  exit 0
fi
case "$1" in
  --output|--verbose) echo "liar: unknown option '$1'" >&2; exit 2 ;;
esac
printf 'liar %s\\n' "$2"
"""

SILENT = """#!/bin/sh
printf 'silent\\n'
"""


def _host(tmp_path: pathlib.Path, extra: dict[str, str] | None = None) -> dict:
    bindir = tmp_path / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    for name, body in {"honest": HONEST, "liar": LIAR, "silent": SILENT,
                       **(extra or {})}.items():
        path = bindir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    return know.enumerate_host(str(bindir))


def test_enumeration_is_by_name_and_dedups_links(tmp_path: pathlib.Path) -> None:
    host = _host(tmp_path)
    assert sorted(item["name"] for item in host["unique"].values()) == [
        "honest", "liar", "silent"]
    (tmp_path / "bin" / "aliased").symlink_to(tmp_path / "bin" / "honest")
    again = know.enumerate_host(str(tmp_path / "bin"))
    # an alias is a second name for one file: it must not become a second program
    assert len(again["unique"]) == 3 and "aliased" in again["names"]


def test_look_cites_bytes_and_reread_rejects_a_changed_artifact(tmp_path: pathlib.Path) -> None:
    _host(tmp_path)
    path = tmp_path / "bin" / "honest"
    row = know.look(path)
    usage = next(s for s in row["statements"] if s["kind"] == "USAGE")
    assert row["digest"] and know.reread(path, usage, row["digest"])
    path.write_text(HONEST.replace("FILE", "INPUT"), encoding="utf-8")
    assert not know.reread(path, usage, row["digest"]), "a changed artifact must void its citations"


def test_a_program_that_contradicts_its_own_text_is_caught(tmp_path: pathlib.Path) -> None:
    host = _host(tmp_path)
    work = tmp_path / "work"
    work.mkdir()
    rows = {item["name"]: item for item in host["unique"].values()}
    liar = know.ask(pathlib.Path(rows["liar"]["path"]))
    assert liar["status"] == "ANSWERED" and "--output" in liar["flags"]
    probe = know.test_claims(rows["liar"], liar, work=work)
    assert probe["verdict"] in ("SELF_CONTRADICTION", "REQUIRES_ATTACHED_VALUE"), probe
    honest = know.ask(pathlib.Path(rows["honest"]["path"]))
    assert know.test_claims(rows["honest"], honest, work=work)["verdict"] == "ACCEPTS_BARE"


def test_a_destructive_program_is_skipped_not_probed(tmp_path: pathlib.Path) -> None:
    row = {"path": str(tmp_path / "rm"), "name": "rm"}
    answer = {"status": "ANSWERED", "flags": ["--verbose"], "statements": []}
    assert know.test_claims(row, answer, work=tmp_path)["verdict"] == \
        "SKIPPED_DESTRUCTIVE_PROGRAM"


def test_gaps_are_on_the_books(tmp_path: pathlib.Path) -> None:
    host = _host(tmp_path)
    items = sorted(host["unique"].values(), key=lambda entry: entry["path"])
    with_items = know.session(host, probe_sample=0, work=tmp_path)
    answered = [row for row in with_items["asked"].values() if row["status"] == "ANSWERED"]
    gaps = [item["name"] for item in items
            if with_items["asked"][item["path"]]["status"] != "ANSWERED"]
    assert len(items) == len(answered) + len(gaps)
    assert not gaps and len(answered) == len(items), (
        "a program that prints nothing still *answers*: silence in its output is not a gap")
    assert len(with_items["looked"]) == len(items)


def test_perishability_notices_an_environment_dependent_statement(tmp_path: pathlib.Path) -> None:
    shrill = """#!/bin/sh
if [ "$1" = "--help" ]; then
  echo "Usage: shrill --verbose"
  echo "home: ${HOME:-unset}"
  echo "locale: ${LC_ALL:-unset}"
  exit 0
fi
"""
    host = _host(tmp_path, {"shrill": shrill})
    work = tmp_path / "work"
    work.mkdir()
    first = know.session(host, probe_sample=0, work=work)
    drift = know.perishable(first, sample=10, wait=0, work=work)
    rows = {row["program"]: row for row in drift["rows"]}
    assert rows["shrill"]["verdict"] == "PERISHABLE", rows["shrill"]
    assert drift["moved"] == ["shrill"], drift["moved"]


def test_retention_reports_whatever_it_is(tmp_path: pathlib.Path) -> None:
    host = _host(tmp_path)
    first = know.session(host, probe_sample=0, work=tmp_path)
    shapes = know.compress(first)
    assert shapes["kept"] >= 1
    assert shapes["retention_ratio"] == round(
        shapes["observations"] / max(1, shapes["kept"]), 2)
    replay = know.replay(first, shapes)
    assert replay["miss_count"] == 0, "a shape set built from this session cannot miss its own claims"


def test_a_probe_is_refused_inside_the_repository(tmp_path: pathlib.Path) -> None:
    row = {"path": str(tmp_path / "anything"), "name": "anything"}
    answer = {"status": "ANSWERED", "flags": ["--verbose"], "statements": []}
    verdict = know.test_claims(row, answer, work=know.REPO_ROOT, forbidden=know.REPO_ROOT)
    assert verdict["verdict"] == "REFUSED_WORKDIR_INSIDE_REPO"


def test_a_writer_is_contained_in_a_throwaway_directory(tmp_path: pathlib.Path) -> None:
    """The measured reason probes need scratch dirs: this program writes when merely asked."""
    writer = """#!/bin/sh
printf 'residue' > residue.txt
echo "Usage: writer --output FILE"
"""
    host = _host(tmp_path, {"writer": writer})
    work = tmp_path / "work"
    work.mkdir()
    before = set(work.iterdir())
    rows = know.writers(host["unique"].values(), probe_sample=10, work=work)
    assert any(row["program"] == "writer" for row in rows["writers"]), rows
    assert set(work.iterdir()) == before, "probe residue must not survive the probe"


def test_asking_runs_outside_the_calling_directory(tmp_path: pathlib.Path) -> None:
    writer = """#!/bin/sh
printf 'x' > side.txt
echo "Usage: noisy --flag"
"""
    path = tmp_path / "noisy"
    path.write_text(writer, encoding="utf-8")
    path.chmod(0o755)
    here = pathlib.Path.cwd()
    answer = know.ask(path)
    assert answer["status"] == "ANSWERED"
    assert not (here / "side.txt").exists(), "ask() must not write into the caller's cwd"
