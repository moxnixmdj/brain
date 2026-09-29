import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
MOD=ROOT/"canonical"/"runtime"/"capability_discovery.py"

def load_module():
    spec=importlib.util.spec_from_file_location("capability_discovery_fulltext_test",MOD)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._APT_PACKAGE_METADATA_CACHE=None
    mod._APT_EXECUTABLE_PATHS_CACHE={}
    return mod

class Result:
    def __init__(self,stdout="",stderr="",returncode=0):
        self.stdout=stdout
        self.stderr=stderr
        self.returncode=returncode

FULL="""Package: opaque-delta
Description: tiny command line utility
Description-en: tiny command line utility
 This program normalizes tabular records and converts them into delimited text while preserving field values.
Tag: interface::commandline, role::program, use::converting, works-with::text

Package: vague-helper
Description: tabular helper
Description-en: helper for tabular data.
Tag: role::program
"""

DUMP="""Package: fallback-only
Description: unrelated terminal utility

"""

def fake_which(name):
    return "/usr/bin/"+name if name in {"apt-cache","apt-file"} else None

def fake_run(argv,**kwargs):
    if argv[:3]==["apt-cache","search","--full"]:
        return Result(FULL)
    if argv[:2]==["apt-cache","dumpavail"]:
        return Result(DUMP)
    if argv[:2]==["apt-file","list"]:
        files={
            "opaque-delta":"opaque-delta: /usr/bin/zzq\n",
            "vague-helper":"vague-helper: /usr/bin/vague\n",
        }
        return Result(files.get(argv[2],""))
    if argv[:2]==["apt-cache","policy"]:
        return Result("  Candidate: 1.0\n")
    raise AssertionError("unexpected subprocess: "+repr(argv))

def test_native_apt_fulltext_long_description_drives_candidate_generation(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages(
        "Normalize tabular records and convert them into delimited text.",
        limit=10,
    )
    assert result["candidates"][0]["name"]=="opaque-delta"
    assert result["candidates"][0]["evidence_tier"]=="SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP"
    assert result["candidates"][0]["executable_semantic_evidence"]["command_paths"]==["/usr/bin/zzq"]

def test_fulltext_path_does_not_require_package_or_binary_name_overlap(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages(
        "Convert tabular records to delimited text.",
        limit=10,
    )
    names=[x["name"] for x in result["candidates"]]
    assert "opaque-delta" in names
    assert "fallback-only" not in names

def test_fulltext_unavailable_falls_back_to_cached_package_metadata(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    def fallback_run(argv,**kwargs):
        if argv[:3]==["apt-cache","search","--full"]:
            raise RuntimeError("fulltext unavailable")
        if argv[:2]==["apt-cache","dumpavail"]:
            return Result("""Package: opaque-fallback
Description: converts raster records into vector records

""")
        if argv[:2]==["apt-file","list"]:
            return Result("opaque-fallback: /usr/bin/zzf\n")
        if argv[:2]==["apt-cache","policy"]:
            return Result("  Candidate: 1.0\n")
        raise AssertionError(repr(argv))
    monkeypatch.setattr(d.subprocess,"run",fallback_run)
    result=d.search_apt_packages("Convert raster records into vector records.",limit=10)
    assert result["candidates"][0]["name"]=="opaque-fallback"
