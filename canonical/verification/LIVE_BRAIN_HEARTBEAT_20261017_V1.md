# Live Brain heartbeat

**Verdict: ALIVE** - seed 448269056761677376, python 3.11.2, platform linux

| Fresh-goal family | new |
|---|---|
| ARCHIVE_TAR_GZ_FROM_MANIFEST | 8/8 |
| ARCHIVE_VERIFY_GNU | 8/8 |
| CODEC_BSON | 8/8 |
| CODEC_CBOR | 8/8 |
| CODEC_CBOR_FLOATS_FAIL_CLOSED | 8/8 |
| CODEC_MSGPACK | 8/8 |
| CODEC_MSGPACK_NPM | 8/8 |
| COMPOUND_TWO_STEP_LITERAL_JSON | 8/8 |
| DECISION_SYNTHESIS | 8/8 |
| DOCX_CREATE | 8/8 |
| EXACT_LITERAL_RESPONSE | 8/8 |
| JQ_QUERY | 8/8 |
| JSON_QUERY_JQ | 8/8 |
| LITERAL_JSON_RECORDS | 8/8 |
| MATH_NUMERIC_SYMPY | 8/8 |
| NUMERIC_EXPRESSION | 8/8 |
| OUT_OF_SCOPE_MUST_FAIL_CLOSED | 40/40 |
| PDF_TEXT_EXTRACT | 8/8 |
| PYTHON_AST_PATCH_SEARCH | 8/8 |
| PYTHON_FAULT_LOCALIZE | 8/8 |
| PYTHON_REPAIR_STRICT_PROGRESS | 8/8 |
| PYTHON_REPAIR_TEST_GUIDED | 8/8 |
| PYTHON_SOURCE_AUDIT | 8/8 |
| PYTHON_TESTS_AUDIT | 8/8 |
| SOURCE_RANKING_BM25 | 8/8 |
| SQLITE_FROM_RECORDS | 8/8 |
| SQLITE_VERIFY_RECORDS | 8/8 |
| XLSX_CREATE | 8/8 |
| XLSX_VERIFY | 8/8 |
| YAML_TO_JSON | 8/8 |

Reachability from the one entry: BLOCKED_ZERO_INPUT 1, REACHED_AND_BOUND 66 (of 67)

Tools runnable on this machine: 52 of 67

Not runnable here:

- `auto.apt.zint`
- `chart.raster.axis_title_unit_binding.v1` - dependency the registry never declared: tesseract-ocr
- `chart.raster.curve_value_query.v1` - dependency the registry never declared: tesseract-ocr
- `chart.raster.curve_x_at_y_query.v1` - dependency the registry never declared: tesseract-ocr
- `chart.raster.direct_curve_label_family_rank.v1` - dependency the registry never declared: tesseract-ocr
- `chart.raster.legend_style_binding.v1` - dependency the registry never declared: tesseract-ocr
- `chart.read.binary_phase_solvus.v1` - dependency the registry never declared: tesseract-ocr
- `chart.read.legend_linear_intersection.v1` - dependency the registry never declared: tesseract-ocr
- `document.convert.markdown_pdf.pandoc_weasyprint`
- `image.code.decode.zbarimg`
- `image.extract.ocr.tesseract` - dependency the registry never declared: tesseract-ocr
- `image.qr.generate.qrencode`
- `pdf.extract.ocr.tesseract`
- `professional.artifact.visual_observer.v1` - dependency the registry never declared: tesseract-ocr
- `web.browser.rendered.capture.chromedriver` - dependency the registry never declared: chromedriver

> **Undeclared dependencies.** The registry's hand-written `source.packages` does not name these, so until this run they were invisible to the heartbeat and every runnability count taken from it was too high. They are derived here from the adapter's real import graph.

Capabilities not reached from a sentence (or blocked by design):

- `terminal.kstar.root.assess.stdlib`: BLOCKED_ZERO_INPUT - takes no input; never routable from a sentence

Families not measured here: BROWSER_CAPTURE, CHART_RASTER_READERS, HTTP_JSON_FETCH__PYPI_AUDIT__WEB_RELEASE, KNOWLEDGE_FETCH_ASSESS_ASSERT, MARKDOWN_TO_PDF, PDF_TEXT_OCR, QR_BARCODE_GENERATE_DECODE

Authority NONE. Credit 0. Nothing here is a capability claim.
