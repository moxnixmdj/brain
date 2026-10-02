"""Hermetic adapter for the pinned LiveBench IFBench verifier candidate."""
from __future__ import annotations

from pathlib import Path
import sys
import types

VENDOR_ROOT = Path(__file__).resolve().parent / "vendor"
sys.path.insert(0, str(VENDOR_ROOT))

import nltk  # pinned by the verification workflow

_DOWNLOAD_CALLS: list[str] = []
_RESOURCE_MAP = {
    "punkt": "tokenizers/punkt",
    "punkt_tab": "tokenizers/punkt_tab",
    "stopwords": "corpora/stopwords",
    "averaged_perceptron_tagger": "taggers/averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng": "taggers/averaged_perceptron_tagger_eng",
}

def _local_only_download(resource: str, *args, **kwargs):
    """Replace nltk.download with a fail-closed local resource check."""
    _DOWNLOAD_CALLS.append(resource)
    target = _RESOURCE_MAP.get(resource)
    if target is None:
        raise RuntimeError(f"unapproved NLTK resource request: {resource}")
    nltk.data.find(target)
    return True

nltk.download = _local_only_download

# The pinned upstream IFBench instructions module imports spaCy and tries to
# download en_core_web_sm, but static inspection found zero checker references
# to spaCy. Supply a stub that makes the dead bootstrap path inert without
# changing any scoring/checker logic.
spacy_mod = types.ModuleType("spacy")
spacy_mod.util = types.SimpleNamespace(is_package=lambda _name: True)
spacy_cli_mod = types.ModuleType("spacy.cli")

def _forbidden_spacy_download(*_args, **_kwargs):
    raise RuntimeError("spaCy download is forbidden in the hermetic verifier route")

spacy_cli_mod.download = _forbidden_spacy_download
sys.modules["spacy"] = spacy_mod
sys.modules["spacy.cli"] = spacy_cli_mod

from livebench.if_runner.ifbench import evaluation_lib, instructions, instructions_registry, instructions_util

download_calls = _DOWNLOAD_CALLS
