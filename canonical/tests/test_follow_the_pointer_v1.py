"""Pins the follower: a stub that names its logic must be resolvable without running it.

The fixtures are shaped like the real thing measured on this machine -- a console
script stub that imports its entry point, a click group whose flags belong to
subcommands, and a plain command whose flags are top-level despite being decorated.
"""
from __future__ import annotations

import ast
import pathlib
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import follow_the_pointer_v1 as follow  # noqa: E402

STUB = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from thing.cli import main
if __name__ == '__main__':
    sys.exit(main())
"""

THING_CLI = '''import click


@click.group()
@click.option("--version", is_flag=True)
@click.version_option()
def main(version):
    pass


@main.command()
@click.option("--roundtrip", is_flag=True)
@click.option("--style")
def write(roundtrip, style):
    pass
'''

FLAT_CLI = '''import click


@click.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8000)
@click.option("--reload", is_flag=True)
def main(host, port, reload):
    pass
'''

ARGPARSE_CLI = '''import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", default="-")
    return parser
'''


def _venv(tmp_path: pathlib.Path, cli_source: str,
          name: str = "fakevenv") -> tuple[pathlib.Path, pathlib.Path]:
    root = tmp_path / name
    scripts = root / "bin"
    site = root / "lib" / "python3.11" / "site-packages" / "thing"
    scripts.mkdir(parents=True)
    site.mkdir(parents=True)
    (site / "__init__.py").write_text("", encoding="utf-8")
    (site / "cli.py").write_text(cli_source, encoding="utf-8")
    stub = scripts / "thing"
    stub.write_text(STUB, encoding="utf-8")
    stub.chmod(0o755)
    return stub, root


def test_the_stub_states_where_its_logic_lives(tmp_path: pathlib.Path) -> None:
    stub, _ = _venv(tmp_path, THING_CLI)
    pointers = follow.shebang_pointer(stub)
    assert any(pointer["target"] == "thing.cli" for pointer in pointers), pointers


def test_following_a_pointer_lands_declarations_without_running_anything(tmp_path: pathlib.Path) -> None:
    stub, _ = _venv(tmp_path, ARGPARSE_CLI)
    result = follow.follow({"path": str(stub), "name": "thing"}, verdict=False)
    flags = {row["flag"] for row in result["flags"]}
    assert {"--strict", "--output"} <= flags, flags
    for row in result["flags"]:
        assert row["file"] and row["line"] and row["citation"], row
        assert "site-packages" in row["file"]


def test_the_follower_never_executes_the_program(tmp_path: pathlib.Path) -> None:
    """P2 is not a promise; it is checked against the source of the walking code."""
    tree = ast.parse(pathlib.Path(follow.__file__).read_text(encoding="utf-8"))
    walkers = {"shebang_pointer", "resolve_python", "resolve_js", "declarations",
               "_click_options", "follow"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in walkers:
            names = {getattr(inner, "id", None) for inner in ast.walk(node)}
            assert "subprocess" not in names, f"{node.name} must not invoke a program"
            assert "run" not in {getattr(call.func, "id", None)
                                 for call in ast.walk(node)
                                 if isinstance(call, ast.Call)}, node.name


def test_a_group_hides_its_command_flags_and_a_command_does_not(tmp_path: pathlib.Path) -> None:
    stub, _ = _venv(tmp_path, THING_CLI)
    nested = follow.follow({"path": str(stub), "name": "thing"}, verdict=True)
    by_flag = {row["flag"]: row for row in nested["flags"]}
    assert by_flag["--roundtrip"]["nested"] is True
    assert by_flag["--style"]["nested"] is True
    assert by_flag["--version"]["nested"] is False

    flat, _ = _venv(tmp_path, FLAT_CLI, name="flatvenv")
    exposed = follow.follow({"path": str(flat), "name": "flat"}, verdict=False)
    assert all(row["nested"] is False for row in exposed["flags"]), exposed["flags"]


def test_undecidable_nesting_is_reported_not_guessed(tmp_path: pathlib.Path) -> None:
    stub, _ = _venv(tmp_path, THING_CLI)
    unknown = follow.follow({"path": str(stub), "name": "thing"}, verdict=None)
    command_flags = [row for row in unknown["flags"]
                     if row.get("command_decorated")]
    assert command_flags and all(row["nested"] is None for row in command_flags), command_flags


def test_a_dead_end_is_reported_not_smoothed(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "broken"
    scripts = root / "bin"
    scripts.mkdir(parents=True)
    stub = scripts / "lost"
    stub.write_text(STUB.replace("thing.cli", "nowhere.at.all"), encoding="utf-8")
    stub.chmod(0o755)
    result = follow.follow({"path": str(stub), "name": "lost"}, verdict=False)
    assert result["flags_found"] == 0
    assert any(dead["target"] == "nowhere.at.all" for dead in result["dead_ends"])
