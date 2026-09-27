#!/usr/bin/env python3
"""Independent content-addressed C++ codec verifier.

This module is a verifier supplier, not a producer. It fails closed unless
the vendored nlohmann/json header matches the externally published Debian
source digest recorded in the manifest.
"""
from __future__ import annotations
import hashlib,json,pathlib,shutil,subprocess,tempfile

EXPECTED_HEADER_SHA256="9bea4c8066ef4a1c206b2be5a36302f8926f7fdc6087af5d20b417d0cf103ea6"
HEADER_REL="canonical/runtime/vendor/nlohmann_json_3_11_3/json.hpp"
MANIFEST_REL="canonical/runtime/vendor/nlohmann_json_3_11_3/MANIFEST.json"

class IndependentSystemCodecVerifierFailure(RuntimeError):
    pass

def _inside(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw)).resolve()
    if p!=root and root not in p.parents:
        raise IndependentSystemCodecVerifierFailure("PATH_OUTSIDE_REPOSITORY")
    return p

def _normalized_format(value):
    fmt=str(value or "").strip().lower()
    aliases={"ubjson":"ubj","messagepack":"msgpack"}
    return aliases.get(fmt,fmt)

def _decoder_expr(fmt):
    table={
      "ubj":"nlohmann::json::from_ubjson(bytes, true, false)",
      "cbor":"nlohmann::json::from_cbor(bytes, true, false)",
      "msgpack":"nlohmann::json::from_msgpack(bytes, true, false)",
      "bson":"nlohmann::json::from_bson(bytes, true, false)",
      "bjdata":"nlohmann::json::from_bjdata(bytes, true, false)",
    }
    if fmt not in table:
        raise IndependentSystemCodecVerifierFailure("SYSTEM_VERIFIER_FORMAT_UNSUPPORTED:"+fmt)
    return table[fmt]

def verify(format_name,json_path,binary_path,producer_project,root):
    root=pathlib.Path(root).resolve()
    header=root/HEADER_REL
    manifest_path=root/MANIFEST_REL
    if not header.is_file() or not manifest_path.is_file():
        raise IndependentSystemCodecVerifierFailure("SYSTEM_VERIFIER_SOURCE_MISSING")
    raw=header.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=EXPECTED_HEADER_SHA256:
        raise IndependentSystemCodecVerifierFailure(
            "SYSTEM_VERIFIER_PROVENANCE_HASH_MISMATCH:"+digest
        )
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema")!="PROJECT_BRAIN_INDEPENDENT_CODEC_VERIFIER_SOURCE_V1"
        or manifest.get("expected_sha256")!=EXPECTED_HEADER_SHA256
        or manifest.get("upstream_git_blob_sha")!="8b72ea6539f40e4e3f7762d17e30c67f2a8308ed"
    ):
        raise IndependentSystemCodecVerifierFailure("SYSTEM_VERIFIER_MANIFEST_INVALID")
    compiler=shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        raise IndependentSystemCodecVerifierFailure("SYSTEM_VERIFIER_CPP_COMPILER_UNAVAILABLE")
    src=_inside(root,json_path)
    binary=_inside(root,binary_path)
    if not src.is_file() or not binary.is_file():
        raise IndependentSystemCodecVerifierFailure("SYSTEM_VERIFIER_INPUT_MISSING")
    fmt=_normalized_format(format_name)
    expr=_decoder_expr(fmt)
    cpp=r'''#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>
#include "json.hpp"
int main(int argc,char** argv){
  if(argc!=3) return 64;
  std::ifstream jf(argv[1],std::ios::binary);
  std::ifstream bf(argv[2],std::ios::binary);
  if(!jf||!bf) return 65;
  std::string js((std::istreambuf_iterator<char>(jf)),std::istreambuf_iterator<char>());
  std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(bf)),std::istreambuf_iterator<char>());
  try {
    auto expected=nlohmann::json::parse(js);
    auto observed=__DECODE__;
    if(observed!=expected) return 3;
    std::cout << observed.dump();
    return 0;
  } catch(const std::exception& e) {
    std::cerr << e.what();
    return 4;
  }
}
'''.replace("__DECODE__",expr)
    with tempfile.TemporaryDirectory(prefix="brain-system-codec-verifier-") as td:
        td=pathlib.Path(td)
        cpp_path=td/"verify.cpp"
        exe=td/"verify"
        cpp_path.write_text(cpp,encoding="utf-8")
        build=subprocess.run(
            [compiler,"-std=c++11","-O0","-I",str(header.parent),str(cpp_path),"-o",str(exe)],
            cwd=root,text=True,capture_output=True,timeout=120
        )
        if build.returncode!=0:
            raise IndependentSystemCodecVerifierFailure(
                "SYSTEM_VERIFIER_COMPILE_FAILED:"+build.stderr[-1600:]
            )
        run=subprocess.run(
            [str(exe),str(src),str(binary)],
            cwd=root,text=True,capture_output=True,timeout=60
        )
        if run.returncode!=0:
            raise IndependentSystemCodecVerifierFailure(
                "SYSTEM_VERIFIER_SEMANTIC_MISMATCH:"
                +str(run.returncode)+":"+run.stderr[-1200:]
            )
    return {
      "schema":"PROJECT_BRAIN_INDEPENDENT_SYSTEM_CODEC_VERIFICATION_V1",
      "verified":True,
      "format":fmt,
      "producer_project":producer_project,
      "verifier_id":"nlohmann-json-3.11.3-debian-source-mirror",
      "verifier_source_type":"debian_source_package_mirror",
      "implementation_independent":True,
      "supplier_class_independent":True,
      "verifier_language":"cpp",
      "header_sha256":digest,
      "upstream_git_blob_sha":manifest["upstream_git_blob_sha"],
      "incremental_spend_usd":0,
    }
