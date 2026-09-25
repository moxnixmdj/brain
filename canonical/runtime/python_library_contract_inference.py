#!/usr/bin/env python3
"""Infer conservative task contracts from pinned Python-library probe evidence."""
from __future__ import annotations
import pathlib,re

class ContractInferenceFailure(RuntimeError): pass

def _functions(module):
    return {str(x.get("name")) for x in module.get("functions") or [] if isinstance(x,dict)}

def _classes(module):
    return {str(x.get("name")):x for x in module.get("classes") or [] if isinstance(x,dict)}

def infer_contract(probe,goal):
    if probe.get("schema")!="PROJECT_BRAIN_APT_PYTHON_LIBRARY_PROBE_V1":
        raise ContractInferenceFailure("PYTHON_PROBE_SCHEMA_INVALID")
    paths=re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",str(goal or ""))
    outputs=[p for p in paths if pathlib.Path(p).suffix.lower()==".docx"]
    if len(outputs)!=1:
        raise ContractInferenceFailure("PYTHON_DOCUMENT_OUTPUT_PATH_REQUIRED")
    modules=[x for x in probe.get("modules") or [] if isinstance(x,dict) and x.get("import_ok") is True]
    top=None
    document_module=None
    for mod in modules:
        if "Document" in _functions(mod):
            top=mod
        cls=_classes(mod).get("Document")
        if cls:
            methods={str(m.get("name")) for m in cls.get("methods") or [] if isinstance(m,dict)}
            if {"add_heading","add_paragraph","add_table","save"}.issubset(methods):
                document_module=mod
    if top is None or document_module is None:
        raise ContractInferenceFailure("PYTHON_DOCUMENT_BUILDER_API_NOT_PROVEN")
    return {
      "schema":"PROJECT_BRAIN_PYTHON_LIBRARY_CONTRACT_V1",
      "family":"PYTHON_DOCUMENT_BUILDER_V1",
      "module":top["module"],
      "factory":"Document",
      "document_class_module":document_module["module"],
      "required_methods":["add_heading","add_paragraph","add_table","save"],
      "output_extension":".docx",
      "output_path":outputs[0],
      "evidence":{
        "factory_module":top["module"],
        "document_class_module":document_module["module"],
        "required_methods":["add_heading","add_paragraph","add_table","save"],
      }
    }
