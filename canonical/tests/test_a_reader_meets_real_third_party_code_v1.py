"""§A127/A128 — the reader meets real code for the first time, and it was wrong about most of it.

Every test in §A113–§A126 used programs written in this repository, by the same person who wrote the reader.
That is the weakest possible test: the reader and the programs share assumptions, so agreement is guaranteed
and proves nothing. This file brings in code written by strangers, from PyPI, and scores the reader against
what `import` actually does.

MEASURED BEFORE ANY FIX: 5 of 17 files in `click` agreed with a real import. The nine defects that followed are
all the same defect in different clothes -- THE READER WAS ANSWERING A QUESTION ABOUT ITS OWN STANDING RATHER
THAN ABOUT THE PROGRAM:

    if TYPE_CHECKING: import x        an import that never runs is not an import
    if sys.platform == "win32": ...   a branch this machine does not take is not the program's startup
    from .constant import y           a relative import is the file's most important import
    from click.x import y             a package importing itself is not a missing module
    cwd=<package> on the prober       the package's own types.py shadowed the standard library
    asking about Sentinel             a name the file defines is invisible to the world
    os.environ.get(...)               a mapping read was refused as a world-changing call

Each fix is in the reader, not in a table of facts about these packages. The packages are only a test.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from canonical.runtime import read_before_running_v1 as R

pytestmark = pytest.mark.skipif(
    subprocess.run([sys.executable, "-c", "import urllib.request;urllib.request.urlopen('https://pypi.org',timeout=5)"],
                   capture_output=True).returncode != 0,
    reason="PyPI unreachable; this test needs real third-party source")


def _fetch(package: str, target: pathlib.Path) -> bool:
    probe = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target", str(target), package],
                           capture_output=True, text=True, timeout=600)
    return probe.returncode == 0


def _agreement(root: pathlib.Path, package: str) -> tuple[int, int, list[str]]:
    """Compare the reader against a real import, file by file."""
    rows: list[str] = []
    agree = total = 0
    for path in sorted(root.rglob("*.py")):
        module = str(path.relative_to(root)).replace("/", ".")[:-3]
        if module.endswith(".__init__"):
            module = module[:-9]
        real = subprocess.run(
            [sys.executable, "-c", "import " + module], capture_output=True, text=True,
            env={"PYTHONPATH": str(root), "PATH": "/usr/bin:/bin"}, timeout=180).returncode != 0
        said = bool(R.predict(path.read_text(errors="replace"), world=str(path.parent)).get("will_fail"))
        total += 1
        if real == said:
            agree += 1
        else:
            rows.append("%s REAL=%s SAID=%s" % (module, real, said))
    return agree, total, rows


@pytest.mark.parametrize("package", ["charset_normalizer", "click"])
def test_the_reader_agrees_with_a_real_import_on_third_party_code(package: str, tmp_path: pathlib.Path) -> None:
    """The whole point: not one fixture, not one program we wrote -- code from strangers, scored against a run."""
    if not _fetch(package, tmp_path / "site"):
        pytest.skip("could not fetch %s" % package)
    agree, total, rows = _agreement(tmp_path / "site", package)
    assert rows == [], "reader disagreed with a real import on %s:\n%s" % (package, "\n".join(rows))
    assert agree == total and total >= 10, "only %d/%d files checked" % (agree, total)


def test_a_reader_that_agrees_with_everything_cannot_catch_a_real_fault(tmp_path: pathlib.Path) -> None:
    """THE MIRROR. A predictor that says "fine" to every file would score 29/29 above and be worthless.

    So the same reader must still catch a program that genuinely cannot import -- otherwise every fix in §A127
    would have been a way of buying agreement by giving up the ability to accuse.
    """
    package = tmp_path / "realpkg"
    package.mkdir()
    (package / "__init__.py").write_text("import definitely_not_a_real_module_xyz\n")
    (package / "ok.py").write_text("VALUE = 1\n")
    (package / "sub.py").write_text("from realpkg import ok\n")

    broken = R.predict((package / "__init__.py").read_text(), world=str(package))
    assert broken["will_fail"] is True
    assert any(f["class"] == "missing_python_module" and f["module"] == "definitely_not_a_real_module_xyz"
               for f in broken["faults"])

    # and the sibling files, which import fine, are not accused
    for good in ("ok", "sub"):
        clean = R.predict((package / ("%s.py" % good)).read_text(), world=str(package))
        assert clean["will_fail"] is False, (good, clean.get("faults"))
