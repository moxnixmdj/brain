# The pieces are already in the repository. Twenty-six of them.

Compared every module in `canonical/runtime/bound_capabilities/` against
every `adapter_module` referenced by the 68-capability registry.

    adapter modules present but bound to no capability: 26

The registry exposes 68 capabilities. Another 26 mechanisms exist as working
modules that no capability points at, so nothing can call them.

## The list

    brain_module_invoke_runner_v1          browser_chromedriver_interact
    brain_module_invoke_v1                 chart_positioned_ocr_axis_binding_v1
    broad_objective_decompose              concrete_execution_oracle
    first_party_objective_relevance_verify grounded_executable_composition
    grounded_executable_composition_verify image_ocr_tesseract_positioned
    open_research_source_frontend          open_web_source_candidate_discovery
    python_request_semantic_acceptance_cells_v1
    python_source_tree_codec               qr_qrencode
    relevant_source_evidence_extract       research_query_focus
    research_tool_loader_v1                sec_companyconcept_source_native
    sec_extracted_xbrl_instance_source_native_v1
    sec_inline_xbrl_fact_anchor_v1         sec_issuer_extension_concept_semantics_v1
    source_candidate_provenance_verify     wikidata_entity_neighborhood_v1
    wikidata_entity_search_v1

## Why this is the answer to the current goal

The goal is a system that uses the computer and decides for itself. The
unbound set contains precisely the missing parts:

| Unbound module | What it unlocks |
|---|---|
| `browser_chromedriver_interact` | driving a real browser — computer use |
| `open_web_source_candidate_discovery` | finding sources on the open web |
| `open_research_source_frontend` | the research retrieval path |
| `first_party_objective_relevance_verify` | the SECOND relevance route, the one the extractor will also admit |
| `research_query_focus` | resolving what a question is really asking |
| `wikidata_entity_search_v1` / `_neighborhood_v1` | structured knowledge lookup |
| `broad_objective_decompose` | breaking a large goal into parts |
| `concrete_execution_oracle` | our own second oracle, never bound |

## This is the same defect found twice earlier

It is the same shape as two findings from this session:

- `knowledge.status.assert` pointed at `runtime_native_action` while the real
  verification machinery sat unbound — fixed by writing the binding.
- the decider was input-starved because only two capabilities were callable.

Now, at larger scale: **26 mechanisms built, tested and unreachable.**

## Note on `first_party_objective_relevance_verify`

This is the other branch inside `objective_evidence_unit_extract`. That
extractor accepts admission via EITHER first-party verification OR the BM25
route. Only the BM25 route is reachable through the registry. The
first-party route — which may be the stronger one — is bound to nothing.

## Recommended next step

Not research. Not new code. **Bind what exists.**

Each binding needs: a capability id, a typed signature, the provides/inputs
declaration, and the action template. `knowledge_status_adapter` demonstrates
the pattern already.

Priority order for the stated goal:
1. `browser_chromedriver_interact` — computer use
2. `open_web_source_candidate_discovery` — finding things to act on
3. `first_party_objective_relevance_verify` — the missing admission route
4. `broad_objective_decompose` — handling large goals
