"""The second closed contract, tested where the network cannot help it.

Every registry fact here is a stub the test hands the broker as a PARAMETER. Nothing is
patched, nothing is mocked into a module, and the bytes are real bytes: each test builds a
real wheel, serves it from a file:// URL, and lets pip install it into a real isolation.
So the things under test are the things that could be wrong -- the version comparator, the
declaration reader, digest agreement between two independent readers, the post-install
read-back, and whether a cache is believed or re-checked.
"""

import base64
import hashlib
import json
import pathlib
import sys
import zipfile

import pytest

from canonical.swe_kernel import the_environment_broker_v1 as B


# ------------------------------------------------------------------ fixtures
def build_wheel(dest: pathlib.Path, name: str = "toydep", version: str = "1.2.3",
                tag: str = "py3-none-any") -> pathlib.Path:
    """A real, installable wheel. The filename encodes the version and the tag, so the
    artifact chooser is exercised against the same naming a registry serves."""
    dist = name.replace("-", "_")
    wheel_name = f"{dist}-{version}-{tag}.whl"
    path = dest / wheel_name
    files = {
        f"{dist}/__init__.py": f"__version__ = {version!r}\nVALUE = 7\n",
        f"{dist}-{version}.dist-info/METADATA":
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        f"{dist}-{version}.dist-info/WHEEL":
            f"Wheel-Version: 1.0\nGenerator: brain-test\nRoot-Is-Purelib: true\nTag: {tag}\n",
    }
    record = [f"{p},," for p in files]
    record.append(f"{dist}-{version}.dist-info/RECORD,,")
    files[f"{dist}-{version}.dist-info/RECORD"] = "\n".join(record) + "\n"
    with zipfile.ZipFile(path, "w") as zf:
        for member, text in files.items():
            zf.writestr(member, text)
    return path


def registry_json(name: str, releases: dict[str, list[pathlib.Path]] | None = None,
                  *, tag: str = "py3-none-any", latest: str = "1.2.3",
                  sdist_only: bool = False, digest: str | None = None) -> dict:
    """The payload shape pypi.org/pypi/{name}/json actually returns, with file digests the
    broker must check against the bytes it downloads."""
    urls = []
    for version, wheels in (releases or {}).items():
        if sdist_only:
            urls.append({"packagetype": "sdist", "filename": f"{name}-{version}.tar.gz",
                         "url": "file:///nonexistent.tar.gz",
                         "digests": {"sha256": "0" * 64}, "size": 10})
            continue
        for wheel in wheels:
            blob = wheel.read_bytes()
            urls.append({"packagetype": "bdist_wheel", "filename": wheel.name,
                         "url": wheel.as_uri(), "size": len(blob),
                         "digests": {"sha256": digest or hashlib.sha256(blob).hexdigest()}})
    return {"info": {"name": name, "version": latest, "requires_python": ">=3.8"},
            "releases": {v: [u for u in urls if f"-{v}-" in u["filename"]] for v in (releases or {})},
            "urls": urls}


def make_tree(tmp_path: pathlib.Path, dependencies: list[str] | None = None,
              *, requires_python: str = ">=3.8", requirements: str | None = None) -> pathlib.Path:
    deps = dependencies if dependencies is not None else []
    if requirements is None:
        listing = ", ".join(f'"{d}"' for d in deps)
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname = \"toypkg\"\nversion = \"0.1.0\"\n"
            f"requires-python = \"{requires_python}\"\ndependencies = [{listing}]\n"
            )
    else:
        (tmp_path / "requirements.txt").write_text(requirements)
    (tmp_path / "src" / "toypkg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "toypkg" / "__init__.py").write_text("X = 1\n")
    return tmp_path


def rich_payload(*wheels: pathlib.Path, requires: list[str] | None = None) -> dict:
    """A registry payload for wheels that already exist on disk, with requires_dist."""
    urls = []
    releases: dict[str, list[dict]] = {}
    for wheel in wheels:
        parts = wheel.name[:-4].split("-")
        version = parts[1]
        blob = wheel.read_bytes()
        entry = {"packagetype": "bdist_wheel", "filename": wheel.name,
                 "url": wheel.as_uri(), "size": len(blob),
                 "digests": {"sha256": hashlib.sha256(blob).hexdigest()},
                 "requires_dist": requires or []}
        urls.append(entry)
        releases.setdefault(version, []).append(entry)
    name = wheels[0].name.split("-")[0]
    return {"info": {"name": name, "version": wheels[-1].name.split("-")[1],
                     "requires_dist": requires or []},
            "releases": releases, "urls": urls}


class Registry:
    """A stub registry. It counts what was asked, because 'host-first' is a claim about
    calls that did NOT happen, and that is only checkable by counting."""

    def __init__(self, payloads: dict[str, dict] | None = None):
        self.payloads = payloads or {}
        self.json_calls: list[str] = []
        self.bytes_calls: list[str] = []

    def fetch_json(self, url: str) -> dict:
        self.json_calls.append(url)
        name = url.split("/pypi/")[1].split("/")[0]
        if name not in self.payloads:
            raise RuntimeError("HTTP Error 404: Not Found")
        return self.payloads[name]

    def fetch_bytes(self, url: str) -> bytes:
        self.bytes_calls.append(url)
        return pathlib.Path(url.replace("file://", "")).read_bytes()


@pytest.fixture(autouse=True)
def isolated_env_dir(tmp_path, monkeypatch):
    """Each test gets its own isolation root, so a venv from one test can never answer
    another test's question."""
    monkeypatch.setenv("BRAIN_ENV_DIR", str(tmp_path / "_envs"))
    yield


# ------------------------------------------------------------------ the comparator
def test_version_key_orders_the_way_a_resolver_needs():
    k = B.version_key
    assert k("1.10") > k("1.9")
    assert k("2.0") > k("2.0rc1")
    assert k("2.0.post1") > k("2.0")
    assert k("2.0") > k("2.0.dev1")
    assert k("1!1.0") > k("2.0")
    assert k("2.0b1") > k("2.0a1")
    assert k("v1.2.3") == k("1.2.3")
    assert k("not-a-version") is None


def test_specifiers_the_environment_actually_writes():
    s = B.specifier_satisfied
    assert s("2.5", ">=2") and not s("1.0", ">=2")
    assert s("2.5", "~=2.0") and not s("3.0", "~=2.0") and s("2.0", "~=2.0")
    assert s("2.1", "~=2.1.0") and not s("2.2", "~=2.1.0")
    assert not s("2.0", "!=2.0") and s("2.1", "!=2.0")
    assert s("2.5", ">=2,<3") and not s("3.1", ">=2,<3")
    assert s("2.0", "==2.0.*") and s("2.0.4", "==2.0.*")
    assert s("0.0.1", "")            # no specifier: any real version satisfies it
    assert not s("not-a-version", "")  # a non-version is never evidence


def test_a_declaration_this_reader_cannot_read_is_refused_not_guessed(tmp_path):
    tree = make_tree(tmp_path, ["pkg @ https://example.com/pkg-1.0.whl"])
    got = B.broker(tree, "env-ready", tmp_path / "memory.json")
    assert got["verdict"] == "REFUSE__DECLARATION_NOT_UNDERSTOOD"
    assert got["records"] == []


# ------------------------------------------------------------------ host first
def test_a_dependency_the_isolation_already_has_costs_no_round_trip(tmp_path):
    """`pip` is in every venv. Host-first is not a preference here, it is a measurement:
    the registry must not even be asked."""
    tree = make_tree(tmp_path, ["pip>=20"])
    registry = Registry()
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    assert registry.json_calls == [] and registry.bytes_calls == []
    record = got["records"][0]
    assert record["status"] == "SATISFIED_BY_HOST" and record["verified_by_execution"] is True


# ------------------------------------------------------------------ the full contract
def test_one_declared_dependency_is_fetched_hashed_installed_and_read_back(tmp_path):
    wheels = tmp_path / "w"
    wheels.mkdir()
    wheel = build_wheel(wheels, "toydep", "1.2.3")
    registry = Registry({"toydep": registry_json("toydep", {"1.2.3": [wheel]})})
    tree = make_tree(tmp_path, ["toydep>=1.0"])
    memory = tmp_path / "memory.json"

    got = B.broker(tree, "env-ready", memory, fetch_json=registry.fetch_json,
                   fetch_bytes=registry.fetch_bytes, work_dir=tmp_path / "wheelcache")
    assert got["verdict"] == "ENVIRONMENT_BROKERED", got
    assert got["from_memory"] is False
    record = got["records"][0]
    assert record["status"] == "ACQUIRED_VERIFIED"
    assert record["version"] == "1.2.3"
    assert record["sha256_observed"] == record["sha256_registry"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert got["network"]["artifact_downloads"] == 1
    assert got["verified_versions"] == {"toydep": "1.2.3"}

    # the isolation really has it: reading it back is an execution, not a claim
    python = got["isolation"]["python"]
    import subprocess
    out = subprocess.run([python, "-c", "import toydep; print(toydep.VALUE)"],
                         capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "7"


def test_the_newest_satisfying_version_is_the_one_acquired(tmp_path):
    wheels = tmp_path / "w"
    wheels.mkdir()
    old, new = build_wheel(wheels, "toydep", "1.0"), build_wheel(wheels, "toydep", "2.5")
    registry = Registry({"toydep": registry_json(
        "toydep", {"1.0": [old], "2.5": [new]}, latest="2.5")})
    tree = make_tree(tmp_path, ["toydep>=2"])
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes,
                   work_dir=tmp_path / "wheelcache")
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    assert got["records"][0]["version"] == "2.5"
    assert len(registry.bytes_calls) == 1


def test_acquisition_is_not_the_arbiter_the_install_is(tmp_path):
    """A version string inside a wheel's metadata is a claim until the interpreter reads it."""
    wheels = tmp_path / "w"
    wheels.mkdir()
    honest = build_wheel(wheels, "toydep", "1.5")
    liar = build_wheel(wheels, "toydep", "9.9")     # file says 1.5, metadata says 9.9
    payload = registry_json("toydep", {"1.5": [honest]})
    payload["releases"]["9.9"] = [{"packagetype": "bdist_wheel", "filename": liar.name,
                                   "url": liar.as_uri(), "size": len(liar.read_bytes()),
                                   "digests": {"sha256": hashlib.sha256(liar.read_bytes()).hexdigest()}}]
    registry = Registry({"toydep": payload})
    tree = make_tree(tmp_path, ["toydep>=1"])
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes,
                   work_dir=tmp_path / "wheelcache")
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    # 9.9 sorts highest and satisfies >=1, so it is chosen -- and the read-back must show 9.9
    assert got["records"][0]["version"] == "9.9"


# ------------------------------------------------------------------ refusals by name
def test_a_registry_digest_that_disagrees_with_the_bytes_refuses_and_installs_nothing(tmp_path):
    wheels = tmp_path / "w"
    wheels.mkdir()
    wheel = build_wheel(wheels, "toydep", "1.2.3")
    registry = Registry({"toydep": registry_json("toydep", {"1.2.3": [wheel]},
                                                 digest="ab" * 32)})
    tree = make_tree(tmp_path, ["toydep>=1"])
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes,
                   work_dir=tmp_path / "wheelcache")
    assert got["verdict"] == "REFUSE__DIGEST_DISAGREE"
    assert "ab" * 32 in got["detail"]
    assert not (tmp_path / "memory.json").exists()
    python = got.get("isolation", {}).get("python")
    if python:
        import subprocess
        assert subprocess.run([python, "-c", "import toydep"], capture_output=True).returncode != 0


def test_a_name_the_registry_does_not_have_is_refused_by_name(tmp_path):
    tree = make_tree(tmp_path, ["no-such-package-ever>=1"])
    registry = Registry({})
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "REFUSE__DEPENDENCY_NOT_ON_REGISTRY"


def test_an_sdist_only_release_has_no_bytes_two_readers_can_agree_on(tmp_path):
    tree = make_tree(tmp_path, ["sourcedep>=1"])
    registry = Registry({"sourcedep": registry_json("sourcedep", {"1.0": []}, sdist_only=True)})
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "REFUSE__NO_COMPATIBLE_VERIFIED_ARTIFACT"


def test_a_wheel_for_another_interpreter_is_not_an_artifact_we_can_verify(tmp_path):
    wheels = tmp_path / "w"
    wheels.mkdir()
    wheel = build_wheel(wheels, "toydep", "1.0", tag="cp27-cp27m-manylinux1_x86_64")
    registry = Registry({"toydep": registry_json("toydep", {"1.0": [wheel]})})
    tree = make_tree(tmp_path, ["toydep>=1"])
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "REFUSE__NO_COMPATIBLE_VERIFIED_ARTIFACT"


def test_an_unreachable_registry_is_named_not_hidden(tmp_path):
    tree = make_tree(tmp_path, ["toydep>=1"])

    def broken(url):
        raise OSError("connection reset by peer")

    got = B.broker(tree, "env-ready", tmp_path / "memory.json", fetch_json=broken,
                   fetch_bytes=broken)
    assert got["verdict"] == "REFUSE__REGISTRY_UNREACHABLE"


def test_a_project_that_declares_nothing_is_ready_without_touching_anything(tmp_path):
    tree = make_tree(tmp_path, [])
    registry = Registry()
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "ENVIRONMENT_READY_NO_DECLARED_DEPENDENCIES"
    assert registry.json_calls == [] and "isolation" not in got


def test_a_project_without_a_build_backend_is_armed_without_being_installed(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = \"toypkg\"\nversion = \"0.1.0\"\ndependencies = [\"pip>=20\"]\n")
    (tmp_path / "src" / "toypkg").mkdir(parents=True)
    (tmp_path / "src" / "toypkg" / "__init__.py").write_text("X = 1\n")
    registry = Registry({})
    got = B.broker(tmp_path, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    assert got.get("project_install") is None      # nothing declared a way to build it
    assert registry.json_calls == []


def test_a_project_that_states_how_it_builds_is_installed_from_a_staged_copy(tmp_path):
    """flask's own suite fails with 'No package metadata was found for flask' until the
    project is installed. Whether the build succeeds is the project's business and is
    recorded either way; that the broker TRIES, from a copy, and never writes into the tree
    is the contract. (The end-to-end proof is the live receipt: flask 494 passed, requests
    619 passed, both in the armed isolation.)"""
    tree = make_tree(tmp_path, ["pip>=20"])
    (tree / "pyproject.toml").write_text(
        (tree / "pyproject.toml").read_text()
        + "\n[build-system]\nrequires = [\"setuptools>=61\"]\n"
          "build-backend = \"setuptools.build_meta\"\n"
          "\n[tool.setuptools]\npackage-dir = {\"\" = \"src\"}\n"
          "\n[tool.setuptools.packages.find]\nwhere = [\"src\"]\n")
    project_files = ("pyproject.toml", "setup.py")
    before = {n: (tree / n).read_bytes() for n in project_files if (tree / n).is_file()}
    registry = Registry({"wheel": rich_payload(build_wheel(tmp_path, "wheel", "0.45.1"))})
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes,
                   work_dir=tmp_path / "wheelcache")
    assert got["verdict"] in ("ENVIRONMENT_BROKERED", "REFUSE__VERSION_CHECK_FAILED"), got
    assert got["project_install"] is not None          # the attempt happened
    after = {n: (tree / n).read_bytes() for n in project_files if (tree / n).is_file()}
    assert after == before                             # the tree was not written into


def test_a_manifest_that_only_lists_dependencies_is_not_built(tmp_path):
    tree = make_tree(tmp_path, ["pip>=20"])
    registry = Registry({})
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    assert got.get("project_install") is None
    assert registry.json_calls == []


def test_the_project_does_not_send_the_broker_to_the_registry_for_itself(tmp_path):
    """A project that lists its own name as a dependency (a real pattern in test groups)
    must not send the broker to the registry for a package the tree already is."""
    tree = make_tree(tmp_path, ["toypkg", "pip>=20"])
    registry = Registry({})
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    assert registry.json_calls == []
    assert not any(r["name"] == "toypkg" and r.get("source") == "registry"
                   for r in got["records"])   # nothing was fetched to obtain the project


# ------------------------------------------------------------------ memory
def test_a_warm_arm_is_read_back_not_refetched(tmp_path):
    wheels = tmp_path / "w"
    wheels.mkdir()
    wheel = build_wheel(wheels, "toydep", "1.2.3")
    registry = Registry({"toydep": registry_json("toydep", {"1.2.3": [wheel]})})
    tree = make_tree(tmp_path, ["toydep>=1"])
    memory = tmp_path / "memory.json"
    first = B.broker(tree, "env-ready", memory, fetch_json=registry.fetch_json,
                     fetch_bytes=registry.fetch_bytes, work_dir=tmp_path / "wheelcache")
    assert first["verdict"] == "ENVIRONMENT_BROKERED"
    calls = len(registry.json_calls)

    second = B.broker(tree, "env-ready", memory, fetch_json=registry.fetch_json,
                      fetch_bytes=registry.fetch_bytes, work_dir=tmp_path / "wheelcache")
    assert second["verdict"] == "ENVIRONMENT_BROKERED_FROM_MEMORY"
    assert second["from_memory"] is True
    assert len(registry.json_calls) == calls          # the registry was not asked again
    assert second["recheck"]["ok"] is True


def test_an_edited_declaration_invalidates_the_arm(tmp_path):
    wheels = tmp_path / "w"
    wheels.mkdir()
    a = build_wheel(wheels, "toydep", "1.2.3")
    b = build_wheel(wheels, "toydep", "2.0.0")
    registry = Registry({"toydep": registry_json(
        "toydep", {"1.2.3": [a], "2.0.0": [b]}, latest="2.0.0")})
    tree = make_tree(tmp_path, ["toydep>=1"])
    memory = tmp_path / "memory.json"
    B.broker(tree, "env-ready", memory, fetch_json=registry.fetch_json,
             fetch_bytes=registry.fetch_bytes, work_dir=tmp_path / "wheelcache")
    text = (tree / "pyproject.toml").read_text().replace("toydep>=1", "toydep>=2")
    (tree / "pyproject.toml").write_text(text)
    again = B.broker(tree, "env-ready", memory, fetch_json=registry.fetch_json,
                     fetch_bytes=registry.fetch_bytes, work_dir=tmp_path / "wheelcache")
    assert again["from_memory"] is False
    assert again["verdict"] == "ENVIRONMENT_BROKERED"
    assert again["records"][0]["version"] == "2.0.0"


def test_a_cache_that_no_longer_reads_back_is_rederived_not_believed(tmp_path):
    """Someone edited the memory. The memory is a claim; the interpreter is the fact."""
    wheels = tmp_path / "w"
    wheels.mkdir()
    wheel = build_wheel(wheels, "toydep", "1.2.3")
    registry = Registry({"toydep": registry_json("toydep", {"1.2.3": [wheel]})})
    tree = make_tree(tmp_path, ["toydep>=1"])
    memory = tmp_path / "memory.json"
    B.broker(tree, "env-ready", memory, fetch_json=registry.fetch_json,
             fetch_bytes=registry.fetch_bytes, work_dir=tmp_path / "wheelcache")
    data = json.loads(memory.read_text())
    key = next(iter(data["entries"]))
    data["entries"][key]["records"][0]["version"] = "0.0.1"
    memory.write_text(json.dumps(data))

    got = B.broker(tree, "env-ready", memory, fetch_json=registry.fetch_json,
                   fetch_bytes=registry.fetch_bytes, work_dir=tmp_path / "wheelcache")
    assert got["from_memory"] is False
    assert got["recheck"]["ok"] is False
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    assert got["records"][0]["version"] == "1.2.3"


def test_the_two_contracts_have_separate_memory_records(tmp_path):
    tree = make_tree(tmp_path, [])
    memory = tmp_path / "memory.json"
    armed = B.broker(tree, "env-ready", memory)
    assert armed["verdict"] == "ENVIRONMENT_READY_NO_DECLARED_DEPENDENCIES"
    ran = B.broker(tree, "run-tests", memory)
    # run-tests has no pytest in this tree's isolation; whichever way it lands, it must not
    # report the env-ready answer as its own
    assert ran["goal"] == "run-tests"
    assert "ENVIRONMENT_READY" not in str(ran["verdict"])


# ------------------------------------------------------------------ evidence
def test_a_requirements_file_is_an_environment_declaration_too(tmp_path):
    tree = make_tree(tmp_path, requirements="pip>=20\n# a comment\n")
    registry = Registry({})
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes)
    assert got["verdict"] == "ENVIRONMENT_BROKERED"
    assert registry.json_calls == []


def test_every_requirements_file_counts_in_the_digest(tmp_path):
    tree = make_tree(tmp_path, ["pip>=20"])
    tree.joinpath("requirements-dev.txt").write_text("pip>=20\n")
    before = B.evidence_digest(tree)[0]
    tree.joinpath("requirements-dev.txt").write_text("pip>=21\n")
    assert B.evidence_digest(tree)[0] != before
    assert "requirements-dev.txt" in B.evidence_digest(tree)[1]


def test_the_cli_exit_code_accepts_a_ready_environment(tmp_path):
    tree = make_tree(tmp_path, [])
    memory = tmp_path / "memory.json"
    assert B.main([str(tree), "--goal", "env-ready", "--memory", str(memory)]) == 0


# ------------------------------------------------------------------ the sixth to ninth trials
def test_a_dev_bound_is_a_version_and_sorts_below_its_release():
    """tox 4 declares `pytest<4dev`; a comparator that cannot read a PEP 440 dev shorthand
    refuses a correct environment."""
    assert B.version_key("4dev") is not None
    assert B.version_key("4.0") > B.version_key("4dev")
    assert B.version_key("2.0") > B.version_key("2.0.dev1")
    assert B.specifier_satisfied("3.0", "<4dev")
    assert not B.specifier_satisfied("8.0", "<4dev")


def test_a_declaration_whose_marker_excludes_this_interpreter_is_not_a_dependency(tmp_path):
    """black's uvloop extra declares winloop for win32. Refusing the whole environment
    because a Windows wheel has no linux tag would blame the project for being correct."""
    tree = make_tree(tmp_path, [])
    (tree / "pyproject.toml").write_text(
        "[project]\nname = \"toypkg\"\nversion = \"0.1.0\"\n"
        "dependencies = [\n"
        "  \"pip>=20\",\n"
        "  \"winloop>=0.5.0; sys_platform == 'win32'\",\n"
        "  \"typing-extensions>=4.15; python_version<'3.13'\",\n"
        "]\n")
    # typing-extensions DOES apply to this interpreter, so it is fetched; winloop does not
    wheel = build_wheel(tmp_path, "typing_extensions", "4.15.0")
    registry = Registry({"typing-extensions": rich_payload(wheel)})
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes,
                   work_dir=tmp_path / "wheelcache")
    assert got["verdict"] == "ENVIRONMENT_BROKERED", got
    assert any("winloop" in s for s in got["declarations"]["skipped_for_this_interpreter"])
    assert not any(r["name"] == "winloop" for r in got["records"])
    assert any(r["name"] == "typing-extensions" for r in got["records"])


def test_a_plugin_is_armed_when_its_host_is_armed_not_in_isolation(tmp_path):
    """A plugin imports its host at module level and correctly does NOT declare it.
    Measured twice live: matplotlib-inline and detect-test-pollution."""
    wheels = tmp_path / "w"
    wheels.mkdir()
    plug = build_wheel(wheels, "toyplug", "1.0")
    # rewrite the wheel with a pytest hook, so it looks like what a real plugin is
    with zipfile.ZipFile(plug, "w") as zf:
        zf.writestr("toyplug.py", "import pytest\n\ndef pytest_configure(config):\n    pass\n")
        zf.writestr("toyplug-1.0.dist-info/METADATA",
                    "Metadata-Version: 2.1\nName: toyplug\nVersion: 1.0\n")
        zf.writestr("toyplug-1.0.dist-info/WHEEL",
                    "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        zf.writestr("toyplug-1.0.dist-info/top_level.txt", "toyplug\n")
        zf.writestr("toyplug-1.0.dist-info/RECORD", "toyplug.py,,\n")
    registry = Registry({"toyplug": rich_payload(plug)})
    tree = make_tree(tmp_path, ["toyplug>=1"])
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes,
                   work_dir=tmp_path / "wheelcache")
    assert got["verdict"] == "ENVIRONMENT_BROKERED", got
    record = got["records"][0]
    assert record["plugin_host"] == "pytest"
    assert record["status"] == "PLUGIN_ARMED_IMPORTED_BY_HOST"
    assert record["import"] == "deferred-to-host"


def test_a_manifest_is_read_by_the_standard_parser_not_by_quoting_rules(tmp_path):
    """A single quote inside a double-quoted requirement is valid TOML and broke a regex
    reader on a real repository (tox)."""
    tree = make_tree(tmp_path, [])
    (tree / "pyproject.toml").write_text(
        "[project]\nname = \"toypkg\"\nversion = \"0.1.0\"\n"
        "dependencies = [\n"
        "  \"pip>=20\",\n"
        "  \"winloop>=0.5.0; sys_platform == 'win32'\",\n"
        "  \"typing-extensions>=4.15; python_version<'3.13'\",\n"
        "]\n")
    # typing-extensions applies here, so it is one registry read; the point of the test is
    # that a quoted inner comparison parses and a win32 marker is skipped, not fetched
    te = build_wheel(tmp_path, "typing_extensions", "4.15.0")
    registry = Registry({"typing-extensions": rich_payload(te)})
    got = B.broker(tree, "env-ready", tmp_path / "memory.json",
                   fetch_json=registry.fetch_json, fetch_bytes=registry.fetch_bytes,
                   work_dir=tmp_path / "wheelcache")
    # the quoted inner comparison is read as a requirement under a marker, not as text,
    # and a declaration whose marker excludes this interpreter is skipped, not fetched
    parsed = {r["name"]: r for r in got["declarations"]["required"]}
    assert parsed["typing-extensions"]["marker"] == "python_version<'3.13'"
    assert any("winloop" in s for s in got["declarations"]["skipped_for_this_interpreter"])


def test_the_test_command_is_read_from_the_project(tmp_path):
    """run-tests must read the command the project declares, not assume pytest."""
    tree = make_tree(tmp_path, [])
    (tree / "Makefile").write_text("test:\n\tpython -m pytest tests\n")
    commands = B.declared_test_commands(tree, tree / "pyproject.toml")
    assert commands[0][-1] == "tests"
    (tree / "Makefile").write_text("test:\n\tcat README.md\n")   # not a test runner
    again = B.declared_test_commands(tree, tree / "pyproject.toml")
    assert all("README" not in " ".join(c) for c in again)


def test_extras_the_projects_own_test_environment_installs_are_read(tmp_path):
    """black's unit-test env installs `.[d]`; nothing else in its manifest says so."""
    tree = make_tree(tmp_path, [])
    (tree / "pyproject.toml").write_text(
        "[project]\nname = \"toypkg\"\nversion = \"0.1.0\"\ndependencies = []\n"
        "\n[project.optional-dependencies]\nd = [\"aiohttp>=3.10\"]\n"
        "\n[tool.tox.testenv]\ncommands = [[\"pip install -e .[d]\"], [\"pytest tests\"]]\n")
    extras = B.declared_extras_in(tree, tree / "pyproject.toml")
    assert extras == ["d"]
    # an extra the manifest does not declare is never installed
    (tree / "Makefile").write_text("test:\n\tpip install -e .[not-declared]\n")
    assert "not-declared" not in B.declared_extras_in(tree, tree / "pyproject.toml")

def test_extras_declared_as_data_in_tox_toml_are_read(tmp_path):
    """tox-dev/tox declares `extras = [ "completion" ]` in tox.toml, and its suite imports
    argcomplete only because of that. A reader that scans command strings alone misses it,
    and the suite then cannot even be collected -- measured on tox, not hypothetical."""
    tree = make_tree(tmp_path, [])
    (tree / "pyproject.toml").write_text(
        '[project]\nname = "toypkg"\nversion = "0.1.0"\n'
        'dependencies = []\n'
        '[project.optional-dependencies]\ncompletion = ["argcomplete>=3.6.3"]\n')
    (tree / "tox.toml").write_text(
        '[env.type]\nextras = [ "completion" ]\n'
        '[env.py]\nextras = [ "completion", "not-declared" ]\n')
    got = B.declared_extras_in(tree, tree / "pyproject.toml")
    # the declared extra is read; the undeclared name is not invented into an install
    assert got == ["completion"]
