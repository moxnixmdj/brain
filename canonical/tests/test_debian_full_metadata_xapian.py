#!/usr/bin/env python3
import importlib.util
import pathlib
from unittest import mock
import pytest

ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical"/"runtime"/"capability_discovery.py"

def load_module():
    spec=importlib.util.spec_from_file_location("capability_discovery_full_metadata_test",PATH)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._APT_FULL_METADATA_CACHE=None
    mod._APT_XAPIAN_CACHE=None
    mod._APT_EXECUTABLE_OWNERS_CACHE=None
    return mod

class R:
    def __init__(self,stdout="",returncode=0,stderr=""):
        self.stdout=stdout
        self.returncode=returncode
        self.stderr=stderr

def test_translation_en_joins_by_description_md5():
    d=load_module()
    packages="""Package: opaque-tool
Version: 1
Description: short summary
Description-md5: abc123
Tag: interface::commandline, role::program, use::converting

"""
    translation="""Package: opaque-tool
Description-md5: abc123
Description-en: long capability description
 that continues on another line and contains decisive semantics.

"""
    def fake_run(argv,**kwargs):
        if argv[:2]==["apt-cache","dumpavail"]:
            return R(packages)
        raise AssertionError(argv)
    with mock.patch.object(d.subprocess,"run",side_effect=fake_run), \
         mock.patch.object(d,"_apt_index_target_files",return_value=["/fake/Translation-en"]), \
         mock.patch.object(d,"_read_apt_index",return_value=translation):
        records=d._apt_full_metadata_records()
    assert len(records)==1
    assert records[0]["name"]=="opaque-tool"
    assert "decisive semantics" in records[0]["description"]
    assert records[0]["tags"].startswith("interface::commandline")

def test_xapian_tags_rescue_opaque_capability_role():
    pytest.importorskip("xapian")
    d=load_module()
    records=[
        {
            "name":"opaque-role-tool",
            "description":"general sound processing utility that converts, transforms, and processes audio data through a command-line workflow",
            "short_description":"general sound processing utility",
            "tags":"interface::commandline, role::program, use::converting, works-with::audio, works-with-format::wav, works-with-format::flac",
            "version":"1","archive_sha256":None,
        }
    ]
    for i in range(30):
        records.append({
            "name":f"audio-decoy-{i}",
            "description":"audio FLAC WAV playback files and recordings",
            "short_description":"audio FLAC WAV playback files and recordings",
            "tags":"role::program, use::playing, works-with::audio",
            "version":"1","archive_sha256":None,
        })
    d._APT_FULL_METADATA_CACHE=records
    d._APT_EXECUTABLE_OWNERS_CACHE={
        x["name"]:[f"/usr/bin/{x['name']}"] for x in records
    }
    out=d._search_apt_packages_full_metadata(
        "Convert a WAV audio recording into FLAC audio.",
        limit=20,
    )
    names=[x["name"] for x in out["candidates"]]
    assert "opaque-role-tool" in names[:20]
    cand=next(x for x in out["candidates"] if x["name"]=="opaque-role-tool")
    assert cand["evidence_tier"]=="SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP"
    assert cand["executable_semantic_evidence"]["acquisition_mode"]=="APT_CONTENTS_DIRECT_STREAM"

def test_full_metadata_path_has_no_remote_manpage_dependency():
    d=load_module()
    source=PATH.read_text(encoding="utf-8")
    section=source[source.index("def _search_apt_packages_full_metadata"):source.index("def search_apt_packages(effect")]
    assert "_fetch_ubuntu_manpage_text" not in section
    assert "urlopen(" not in section.lower()
