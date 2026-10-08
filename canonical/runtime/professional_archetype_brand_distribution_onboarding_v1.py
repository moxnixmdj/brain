#!/usr/bin/env python3
"""Reusable model-independent brand/distributor onboarding questionnaire archetype.

Selection is intentionally narrow and fail-closed. The archetype is professional
knowledge, not benchmark-specific rubric logic. Its dimensions are derived from
public supplier/distributor onboarding practice: item setup/product information,
order management, fulfillment models, EDI/data exchange, inventory, shipment and
invoice flows, compliance readiness, and supplier performance.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUESTIONNAIRE_SPEC_V1"
ARCHETYPE = "BRAND_DISTRIBUTOR_ONBOARDING_QUESTIONNAIRE_V1"

PROVENANCE = [
    "https://www.spscommerce.com/retailers/vendor-onboarding/",
    "https://www.spscommerce.com/products/",
    "https://community.spscommerce.com/wp-content/uploads/2025/01/Drop_Ship_Vendor_Guide_v3.0_-Sept-2024.pdf",
]

PAGES = [
    {
        "heading": "Company, Sales and Commercial Readiness",
        "intro": "Please provide current information. If an item does not apply, enter N/A.",
        "questions": [
            "Legal company and brand name, website, headquarters address, and year established",
            "Primary Sales contact: name, title, email, phone, and time zone",
            "Primary Operations contact and escalation contact: name, title, email, and phone",
            "Briefly describe the brand, core product categories, target customer, and key differentiators",
            "List current sales channels and geographic markets served",
            "List major current retail, wholesale, marketplace, or distributor relationships",
            "Provide trailing 12-month sales and the next 12-month sales target or growth expectation",
            "Provide the best available demand forecast by month, quarter, channel, or region",
            "Provide wholesale pricing, suggested retail pricing, applicable MAP policy, and effective dates",
            "State minimum order quantity, minimum order value, case-pack rules, and any mixed-case rules",
            "State requested payment terms, currency, early-pay discounts, deposits, or credit requirements",
            "Describe planned launches, promotions, seasonal peaks, and expected first-order timing",
            "State distribution goals, territory expectations, exclusivity requests, or channel restrictions",
        ],
    },
    {
        "heading": "Product Data, Supply and Fulfillment",
        "intro": "Complete at SKU level where applicable and attach master-data files separately if available.",
        "questions": [
            "List active SKUs, variants, item descriptions, and GTIN/UPC/EAN identifiers",
            "Provide unit, inner-pack, case and pallet dimensions, weights, pack quantities, and hierarchy",
            "Provide country of origin and any required customs, tariff, regulatory, or handling information",
            "Identify shelf-life, lot/serial tracking, storage, temperature, hazmat, or special-handling needs",
            "State current finished-goods inventory and the warehouse or fulfillment locations holding it",
            "State normal production capacity and any surge-capacity limits",
            "State standard initial-order lead time and replenishment lead time",
            "Identify supported fulfillment models: ship-to-DC, ship-to-store, drop-ship, cross-dock, or other",
            "State order cutoffs, processing cadence, business days, and typical time from order to ship",
            "Provide current fill rate, on-time shipment rate, backorder rate, or comparable service metrics",
            "Describe preferred carriers, freight terms, parcel/LTL capabilities, and shipping account rules",
            "Confirm ability to meet routing-guide, carton-label, packing-slip, ASN, and appointment requirements",
            "Describe returns, damages, shortages, claims, substitutions, cancellations, and restocking policies",
        ],
    },
    {
        "heading": "Systems, Compliance, Launch Support and Performance",
        "intro": "Use this section to identify integration effort, launch dependencies, and ongoing support needs.",
        "questions": [
            "Identify ERP, WMS, order-management, inventory, and accounting systems currently used",
            "Describe EDI, API, portal, or other B2B integration capability and identify the integration provider",
            "Identify supported documents or messages, including PO, PO acknowledgment, ASN, invoice, and inventory",
            "Describe how product catalog data, pricing, images, attributes, and updates can be supplied",
            "Describe inventory-availability and forecast data feeds, including update frequency",
            "State customer-service contacts, operating hours, response targets, and escalation process",
            "List relevant licenses, certifications, insurance, tax registrations, or compliance documents",
            "Describe quality-control, traceability, recall, and corrective-action processes",
            "Disclose material chargebacks, compliance issues, supply interruptions, or recurring service failures",
            "List available product images, copy, training, samples, merchandising, and marketing assets",
            "Describe launch support, account-management coverage, field sales support, and training availability",
            "Identify KPIs you can report regularly, such as fill rate, order accuracy, on-time shipment, and returns",
            "List known launch risks, capacity constraints, system dependencies, or decisions still required",
            "Provide target onboarding completion date, earliest ship date, approver name, and approval status",
            "Additional notes, assumptions, or information the distribution team should review",
        ],
    },
]


def _title(prompt: str) -> str:
    m = re.search(r'titled\s+["“]([^"”]+)["”]', prompt, flags=re.I)
    return m.group(1).strip() if m else "Brand Data Gathering"


def select(prompt: str, reference_files: list[str] | None = None) -> dict[str, Any]:
    text = " ".join(str(prompt or "").split())
    low = text.lower()
    if reference_files:
        return {"status": "UNSUPPORTED", "reason": "ARCHETYPE_REQUIRES_NO_REFERENCE_FILES"}
    if "pdf" not in low or "brand" not in low or "distribution" not in low:
        return {"status": "UNSUPPORTED", "reason": "BRAND_DISTRIBUTION_PDF_SIGNAL_MISSING"}
    signals = sum(token in low for token in ("onboarding", "readiness", "operational", "sales", "brand partner"))
    if signals < 3:
        return {"status": "UNSUPPORTED", "reason": "PROFESSIONAL_INTENT_SIGNALS_INSUFFICIENT"}
    page_m = re.search(r"\b(\d+)\s*[- ]page\b", low)
    if not page_m or int(page_m.group(1)) != 3:
        return {"status": "UNSUPPORTED", "reason": "EXACT_THREE_PAGE_SCOPE_REQUIRED"}
    return {
        "status": "SELECTED",
        "archetype": ARCHETYPE,
        "spec": {
            "schema": SCHEMA,
            "title": _title(text),
            "pages": PAGES,
            "provenance": PROVENANCE,
            "generation_boundary": "PUBLIC_PROFESSIONAL_PRACTICE_AND_TASK_PROMPT_ONLY__NO_BENCHMARK_RUBRIC_OR_GOLD_DELIVERABLE_INPUT",
        },
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
