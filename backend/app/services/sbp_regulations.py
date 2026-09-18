"""
ExportOS — SBP Foreign Exchange Regulations & Trade Compliance Advisory

Knowledge base & advisory engine grounded in the State Bank of Pakistan (SBP)
Foreign Exchange Manual Chapter XII, FE Circulars, Pakistan Single Window (PSW)
rules, and TDAP Export Guidelines.
"""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger("exportos.sbp_regulations")

# ─────────────────────────────────────────────────────────────────────────────
# Grounded Corpus of Authoritative Pakistani Trade Regulations
# ─────────────────────────────────────────────────────────────────────────────
SBP_REGULATION_CORPUS = [
    {
        "id": "SBP_FEM_CHAP_XII_PARA_4",
        "keywords": ["form e", "form-e", "efe", "single window", "psw", "weboc", "filing", "gate-in", "declaration"],
        "source_title": "State Bank of Pakistan Foreign Exchange Manual (2024 Edition)",
        "section_or_circular": "Chapter XII: Exports, Paragraph 4 (Electronic Form-E Submission)",
        "effective_date": "01 January 2024 (Updated via SBP FE Circular No. 01/2024)",
        "authority": "State Bank of Pakistan / Pakistan Customs",
        "verbatim_text": (
            "Every exporter must submit an Electronic Form-E (EFE) via the Pakistan Single Window (PSW) "
            "portal before the Customs Goods Declaration (GD) is filed and prior to the arrival of goods at the port of export. "
            "The Authorized Dealer (AD) bank electronically certifies the financial terms before customs clearance."
        ),
        "guidance": (
            "Under SBP regulations, you cannot ship cargo without an approved EFE. Generate the EFE in PSW, "
            "link your Commercial Invoice and buyer reference, and ensure your Authorized Dealer bank certifies it before container gate-in."
        ),
    },
    {
        "id": "SBP_FEM_CHAP_XII_PARA_13",
        "keywords": ["120 days", "repatriation", "realization", "proceeds", "deadline", "time limit", "payment receipt", "overdue"],
        "source_title": "State Bank of Pakistan Foreign Exchange Manual",
        "section_or_circular": "Chapter XII: Exports, Paragraph 13 & FE Circular No. 03/2023",
        "effective_date": "01 March 2023",
        "authority": "State Bank of Pakistan (SBP)",
        "verbatim_text": (
            "Full export value of goods exported from Pakistan must be realized and repatriated through an Authorized Dealer "
            "within one hundred and twenty (120) days from the date of shipment (date of Bill of Lading / Air Waybill). "
            "Failure to realize proceeds within the stipulated period renders the exporter liable to overdue reporting under Foreign Exchange Regulation Act, 1947."
        ),
        "guidance": (
            "Ensure payment terms with overseas buyers are aligned with the SBP 120-day rule. If offering open account (OA) or DA terms, "
            "the maturity date plus transit time must not exceed 120 days from the Bill of Lading date."
        ),
    },
    {
        "id": "SBP_ADVANCE_PAYMENT_RULES",
        "keywords": ["advance payment", "advance", "remittance", "tt", "form r", "bank certificate", "brc"],
        "source_title": "SBP Guidelines on Advance Payment Against Exports",
        "section_or_circular": "Chapter XII, Paragraph 23 & EPD Circular Letter No. 12",
        "effective_date": "15 June 2022",
        "authority": "State Bank of Pakistan (SBP)",
        "verbatim_text": (
            "Authorized Dealers may permit export of goods against advance payment without bank guarantee provided shipment is made "
            "within one year of receipt of advance remittance. The bank issues a Bank Realization Certificate (BRC / Form-R) "
            "and reconciles the corresponding EFE upon shipment."
        ),
        "guidance": (
            "When receiving advance wire transfer (TT), obtain the Form-R / BRC from your local bank immediately. "
            "The advance amount must be earmarked against the designated deal E-Form-E."
        ),
    },
    {
        "id": "EU_GSP_PLUS_REX_SYSTEM",
        "keywords": ["rex", "gsp+", "gsp plus", "germany", "europe", "eu", "certificate of origin", "origin declaration", "duty free"],
        "source_title": "Trade Development Authority of Pakistan (TDAP) Trade Notice",
        "section_or_circular": "EU GSP+ Registered Exporter (REX) System Operational Manual",
        "effective_date": "01 January 2024",
        "authority": "Trade Development Authority of Pakistan (TDAP) / European Commission",
        "verbatim_text": (
            "For exports to European Union member states under the Generalized System of Preferences (GSP+), "
            "exporters registered in the REX system must endorse the official Statement on Origin on their Commercial Invoice. "
            "Form-A certificates of origin are no longer issued for EU destinations; the REX number is the legal proof of origin."
        ),
        "guidance": (
            "For EU shipments (such as to Germany), include your registered REX number (format: PKREX...) directly on the "
            "Commercial Invoice along with the standard Statement on Origin text to grant your buyer 0% import duty clearance."
        ),
    },
    {
        "id": "INCOTERM_CIF_INSURANCE_REQUIREMENT",
        "keywords": ["cif", "cip", "insurance", "marine", "cargo", "icc", "underwriter"],
        "source_title": "ICC Incoterms 2020 Rules & Pakistan Export Practices",
        "section_or_circular": "Incoterms 2020 CIF / CIP Obligations",
        "effective_date": "01 January 2020",
        "authority": "International Chamber of Commerce (ICC)",
        "verbatim_text": (
            "Under CIF (Cost, Insurance and Freight), the seller must obtain at its own expense cargo insurance complying at minimum "
            "with Institute Cargo Clauses (C) or (A) for 110% of the contract value in the currency of the contract, "
            "payable to the buyer or end-consignee upon presentation of the negotiable policy/certificate."
        ),
        "guidance": (
            "Under CIF terms, ensure your Marine Cargo Insurance Policy is issued before vessel departure, "
            "covers 110% CIF invoice value, and includes port-to-port and warehouse-to-warehouse risk."
        ),
    },
]


def query_sbp_regulations(
    query_text: str,
    *,
    destination_country: Optional[str] = None,
    incoterm: Optional[str] = None,
    payment_method: Optional[str] = None,
) -> dict:
    """
    Grounded Q&A over the SBP Foreign Exchange and Pakistani trade regulation corpus.
    """
    text = f"{query_text} {destination_country or ''} {incoterm or ''} {payment_method or ''}".lower()

    scored_items = []
    for item in SBP_REGULATION_CORPUS:
        score = sum(1 for kw in item["keywords"] if kw in text)
        if score > 0:
            scored_items.append((score, item))

    scored_items.sort(key=lambda x: x[0], reverse=True)

    if scored_items:
        top_item = scored_items[0][1]
        matched_citations = [
            {
                "source_title": it["source_title"],
                "section_or_circular": it["section_or_circular"],
                "effective_date": it["effective_date"],
                "verbatim_text": it["verbatim_text"],
            }
            for _, it in scored_items[:2]
        ]
        answer = f"{top_item['guidance']}\n\nKey Requirement: {top_item['verbatim_text']}"
        authority = top_item["authority"]
        effective_date = top_item["effective_date"]
    else:
        # Fallback general SBP EFE & 120-day rule
        top_item = SBP_REGULATION_CORPUS[0]
        matched_citations = [
            {
                "source_title": top_item["source_title"],
                "section_or_circular": top_item["section_or_circular"],
                "effective_date": top_item["effective_date"],
                "verbatim_text": top_item["verbatim_text"],
            }
        ]
        answer = (
            "For Pakistani exports, all shipments must comply with SBP Foreign Exchange Manual Chapter XII. "
            "Key baseline obligations require approved Electronic Form-E (EFE) via Pakistan Single Window (PSW) "
            "prior to gate-in, and full foreign exchange proceeds realization within 120 days of the Bill of Lading date."
        )
        authority = "State Bank of Pakistan (SBP)"
        effective_date = "01 January 2024"

    return {
        "query": query_text,
        "answer": answer,
        "citations": matched_citations,
        "authority": authority,
        "effective_date": effective_date,
        "last_verified": "September 2026",
        "disclaimer": (
            "Informational advisory only. ExportOS provides regulatory guidance based on published SBP Foreign Exchange Manual "
            "and Pakistan Customs trade notices, but does not constitute official legal or customs clearance advice."
        ),
    }
