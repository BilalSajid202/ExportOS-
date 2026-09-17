"""
ExportOS — Multi-Document Generation Engine (Phase 10)

Generates standardized, authoritative export documents from a single deal revision:
1. Proforma Invoice (PI)
2. Commercial Invoice (CI)
3. Packing List (PL)
4. Certificate of Origin (Draft CoO)

Includes cryptographic SHA-256 integrity hash and clean printable HTML templates.
"""

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.costing import DealQuote, QuoteStatus
from app.models.deal import Deal, DealLineItem
from app.models.documents import (
    DocumentSet,
    DocumentStatus,
    DocumentType,
    GeneratedDocument,
)
from app.models.organisation import Organisation
from app.services.costing import round_curr


def compute_sha256(data: Dict[str, Any]) -> str:
    """Computes a reproducible SHA-256 hash of structured document JSON."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def generate_deal_document_set(
    db: AsyncSession,
    deal: Deal,
    organisation: Organisation,
    notes: Optional[str] = None,
    override_port_of_loading: str = "Karachi Port (PKBQM/PKKHI), Pakistan",
    payment_terms: str = "100% LC at sight",
) -> DocumentSet:
    """
    Constructs a complete set of export documents (PI, CI, PL, CoO) for a deal revision.
    """
    # 1. Determine revision number
    rev_q = (
        select(DocumentSet)
        .where(DocumentSet.deal_id == deal.id)
        .order_by(DocumentSet.revision_number.desc())
    )
    rev_res = await db.execute(rev_q)
    prev_set = rev_res.scalars().first()
    revision_num = (prev_set.revision_number + 1) if prev_set else 1

    # Mark previous document sets as not active
    if prev_set:
        prev_set.is_active = False
        db.add(prev_set)

    # 2. Fetch latest approved or active quote
    quote_q = (
        select(DealQuote)
        .where(
            DealQuote.deal_id == deal.id,
            DealQuote.organisation_id == deal.organisation_id,
        )
        .order_by(DealQuote.created_at.desc())
    )
    quote_res = await db.execute(quote_q)
    quotes = quote_res.scalars().all()
    quote = next((q for q in quotes if q.status == QuoteStatus.APPROVED), quotes[0] if quotes else None)

    incoterm = quote.incoterm.value if quote else "FOB"
    incoterm_place = quote.incoterm_place if quote else "Karachi, Pakistan"
    currency = quote.currency if quote else "USD"
    unit_price = quote.unit_price if quote else Decimal("15.00")
    total_quote_price = quote.total_quote_price if quote else sum(li.quantity * Decimal("15.00") for li in deal.line_items)

    # Create parent DocumentSet
    doc_set = DocumentSet(
        organisation_id=deal.organisation_id,
        deal_id=deal.id,
        revision_number=revision_num,
        status=DocumentStatus.DRAFT,
        is_active=True,
        notes=notes or f"Generated document set revision #{revision_num}",
    )
    db.add(doc_set)
    await db.flush()

    # Base metadata shared across documents
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ref_code = deal.reference.replace("EO-", "")
    exporter_name = organisation.name
    country_of_origin = "Pakistan"

    # Line items calculation
    lines_data = []
    total_qty = Decimal("0.00")
    total_net_weight = Decimal("0.00")
    total_cartons = 0

    for idx, li in enumerate(deal.line_items, start=1):
        prod = li.product
        qty = li.quantity
        total_qty += qty
        uom = prod.unit_of_measure if prod else "PCS"
        hs_code = prod.default_hs_code if (prod and prod.default_hs_code) else "9506.62.10"
        item_weight = prod.weight_kg if (prod and prod.weight_kg) else Decimal("0.450")
        carton_cap = prod.carton_capacity if (prod and prod.carton_capacity and prod.carton_capacity > 0) else 20

        line_net_wt = round_curr(qty * item_weight)
        total_net_weight += line_net_wt

        line_cartons = math.ceil(float(qty) / float(carton_cap))
        total_cartons += line_cartons

        line_total = round_curr(qty * unit_price)

        lines_data.append({
            "line_no": idx,
            "product_id": str(li.product_id),
            "sku": prod.sku if prod else f"SKU-{idx}",
            "name": prod.name if prod else "Export Product",
            "description": li.description or (prod.description if prod else "Export Quality Goods"),
            "hs_code": hs_code,
            "quantity": float(qty),
            "uom": uom,
            "unit_price": float(unit_price),
            "total_price": float(line_total),
            "unit_weight_kg": float(item_weight),
            "total_net_weight_kg": float(line_net_wt),
            "carton_capacity": carton_cap,
            "cartons_count": line_cartons,
        })

    total_gross_weight = round_curr(total_net_weight * Decimal("1.10"))  # +10% tare weight
    total_cbm = round_curr(Decimal(str(total_cartons)) * Decimal("0.045"))  # ~0.045 m3 per carton

    # ── 1. Proforma Invoice (PI) ──────────────────────────────
    pi_number = f"PI-{ref_code}-R{revision_num}"
    pi_content = {
        "document_type": "PROFORMA_INVOICE",
        "document_number": pi_number,
        "date": today_str,
        "valid_until": "14 days from date of issuance",
        "deal_reference": deal.reference,
        "exporter": {
            "name": exporter_name,
            "country": country_of_origin,
            "ntn": "7294819-3",
            "strn": "3277876123456",
            "address": "Export Processing Zone, Sialkot / Karachi, Pakistan",
        },
        "buyer": {
            "name": deal.buyer_name,
            "destination": incoterm_place,
        },
        "commercial_terms": {
            "incoterm": incoterm,
            "incoterm_place": incoterm_place,
            "currency": currency,
            "payment_terms": payment_terms,
            "port_of_loading": override_port_of_loading,
            "port_of_discharge": incoterm_place,
        },
        "line_items": lines_data,
        "financial_summary": {
            "total_quantity": float(total_qty),
            "subtotal": float(total_quote_price),
            "total_amount": float(total_quote_price),
            "currency": currency,
        },
        "instructions": "Please sign and return copy for production scheduling and banking Form-E filing.",
    }
    db.add(
        GeneratedDocument(
            organisation_id=deal.organisation_id,
            deal_id=deal.id,
            document_set_id=doc_set.id,
            doc_type=DocumentType.PROFORMA_INVOICE,
            document_number=pi_number,
            title=f"Proforma Invoice ({pi_number})",
            content_json=pi_content,
            sha256_hash=compute_sha256(pi_content),
            status=DocumentStatus.DRAFT,
        )
    )

    # ── 2. Commercial Invoice (CI) ────────────────────────────
    ci_number = f"CI-{ref_code}-R{revision_num}"
    ci_content = {
        "document_type": "COMMERCIAL_INVOICE",
        "document_number": ci_number,
        "date": today_str,
        "deal_reference": deal.reference,
        "form_e_number": f"EFE-SBP-{ref_code}",
        "exporter": {
            "name": exporter_name,
            "country": country_of_origin,
            "ntn": "7294819-3",
            "strn": "3277876123456",
            "address": "Export Processing Zone, Sialkot / Karachi, Pakistan",
        },
        "consignee": {
            "name": deal.buyer_name,
            "destination": incoterm_place,
        },
        "shipping_details": {
            "port_of_loading": override_port_of_loading,
            "port_of_discharge": incoterm_place,
            "incoterm": incoterm,
            "incoterm_place": incoterm_place,
            "currency": currency,
            "payment_terms": payment_terms,
        },
        "line_items": lines_data,
        "financial_summary": {
            "total_quantity": float(total_qty),
            "total_amount": float(total_quote_price),
            "currency": currency,
        },
        "declaration": "We certify that this invoice shows the actual price of the goods described and that all particulars are true and correct.",
    }
    db.add(
        GeneratedDocument(
            organisation_id=deal.organisation_id,
            deal_id=deal.id,
            document_set_id=doc_set.id,
            doc_type=DocumentType.COMMERCIAL_INVOICE,
            document_number=ci_number,
            title=f"Commercial Invoice ({ci_number})",
            content_json=ci_content,
            sha256_hash=compute_sha256(ci_content),
            status=DocumentStatus.DRAFT,
        )
    )

    # ── 3. Packing List (PL) ──────────────────────────────────
    pl_number = f"PL-{ref_code}-R{revision_num}"
    pl_content = {
        "document_type": "PACKING_LIST",
        "document_number": pl_number,
        "date": today_str,
        "deal_reference": deal.reference,
        "exporter": {
            "name": exporter_name,
            "country": country_of_origin,
        },
        "consignee": {
            "name": deal.buyer_name,
            "destination": incoterm_place,
        },
        "shipping_details": {
            "port_of_loading": override_port_of_loading,
            "port_of_discharge": incoterm_place,
        },
        "line_items": lines_data,
        "packaging_summary": {
            "total_packages_cartons": total_cartons,
            "total_quantity": float(total_qty),
            "total_net_weight_kg": float(total_net_weight),
            "total_gross_weight_kg": float(total_gross_weight),
            "total_cbm_m3": float(total_cbm),
        },
        "shipping_marks": f"MADE IN PAKISTAN / {exporter_name.upper()} / {deal.reference} / 1-{total_cartons}",
    }
    db.add(
        GeneratedDocument(
            organisation_id=deal.organisation_id,
            deal_id=deal.id,
            document_set_id=doc_set.id,
            doc_type=DocumentType.PACKING_LIST,
            document_number=pl_number,
            title=f"Packing List ({pl_number})",
            content_json=pl_content,
            sha256_hash=compute_sha256(pl_content),
            status=DocumentStatus.DRAFT,
        )
    )

    # ── 4. Certificate of Origin (Draft CoO) ──────────────────
    coo_number = f"COO-{ref_code}-R{revision_num}"
    coo_content = {
        "document_type": "CERTIFICATE_OF_ORIGIN",
        "document_number": coo_number,
        "date": today_str,
        "deal_reference": deal.reference,
        "exporter": {
            "name": exporter_name,
            "address": "Pakistan",
        },
        "consignee": {
            "name": deal.buyer_name,
            "country": incoterm_place,
        },
        "transport_details": {
            "port_of_loading": override_port_of_loading,
            "port_of_discharge": incoterm_place,
            "means_of_transport": "Ocean Vessel / Air Freight",
        },
        "items": [
            {
                "item_no": l["line_no"],
                "description": l["name"],
                "hs_code": l["hs_code"],
                "quantity": l["quantity"],
                "uom": l["uom"],
                "gross_weight_kg": round(l["total_net_weight_kg"] * 1.10, 2),
            }
            for l in lines_data
        ],
        "origin_declaration": "The undersigned exporter hereby declares that the goods described above originated and were manufactured in Pakistan.",
        "certifying_body": "Sialkot / Karachi Chamber of Commerce and Industry (SCCI / KCCI), Pakistan",
    }
    db.add(
        GeneratedDocument(
            organisation_id=deal.organisation_id,
            deal_id=deal.id,
            document_set_id=doc_set.id,
            doc_type=DocumentType.CERTIFICATE_OF_ORIGIN,
            document_number=coo_number,
            title=f"Certificate of Origin ({coo_number})",
            content_json=coo_content,
            sha256_hash=compute_sha256(coo_content),
            status=DocumentStatus.DRAFT,
        )
    )

    await db.commit()
    await db.refresh(doc_set)
    return doc_set


def render_document_html(doc: GeneratedDocument) -> str:
    """Generates clean, printable HTML presentation for an export document."""
    data = doc.content_json
    doc_type = doc.doc_type.value

    # Shared Header
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{doc.title}</title>
<style>
  body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; margin: 40px; color: #1e293b; background: #ffffff; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #0f172a; padding-bottom: 20px; margin-bottom: 25px; }}
  .title {{ font-size: 24px; font-weight: 800; text-transform: uppercase; color: #0f172a; letter-spacing: 0.5px; }}
  .doc-num {{ font-family: monospace; font-size: 14px; font-weight: 700; color: #4338ca; margin-top: 4px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 25px; }}
  .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; font-size: 13px; }}
  .card-title {{ font-weight: 700; text-transform: uppercase; font-size: 11px; color: #64748b; margin-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 13px; }}
  th {{ background: #0f172a; color: #ffffff; text-align: left; padding: 10px; font-size: 11px; text-transform: uppercase; }}
  td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
  tr:nth-child(even) {{ background: #f8fafc; }}
  .text-right {{ text-align: right; }}
  .totals {{ display: flex; justify-content: flex-end; margin-bottom: 30px; }}
  .totals-box {{ width: 300px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; font-size: 13px; }}
  .totals-row {{ display: flex; justify-content: space-between; padding: 4px 0; }}
  .totals-row.final {{ border-top: 2px solid #0f172a; font-weight: 800; font-size: 15px; color: #4338ca; padding-top: 8px; margin-top: 4px; }}
  .footer {{ border-top: 1px solid #e2e8f0; padding-top: 20px; font-size: 11px; color: #64748b; display: flex; justify-content: space-between; }}
  .hash {{ font-family: monospace; font-size: 10px; color: #94a3b8; word-break: break-all; max-width: 400px; }}
  @media print {{ body {{ margin: 0; }} }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="title">{doc_type.replace('_', ' ')}</div>
      <div class="doc-num">{doc.document_number}</div>
    </div>
    <div style="text-align: right; font-size: 13px;">
      <div><strong>Date:</strong> {data.get('date', '')}</div>
      <div><strong>Deal Ref:</strong> {data.get('deal_reference', '')}</div>
      {f"<div><strong>SBP Form-E:</strong> {data.get('form_e_number', '')}</div>" if data.get('form_e_number') else ""}
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">Exporter / Shipper</div>
      <strong>{data.get('exporter', {}).get('name', 'ExportOS Exporter')}</strong><br>
      {data.get('exporter', {}).get('address', 'Pakistan')}<br>
      NTN: {data.get('exporter', {}).get('ntn', '7294819-3')} | STRN: {data.get('exporter', {}).get('strn', '3277876123456')}
    </div>
    <div class="card">
      <div class="card-title">Buyer / Consignee</div>
      <strong>{data.get('buyer', {}).get('name') or data.get('consignee', {}).get('name', 'Buyer')}</strong><br>
      Destination: {data.get('buyer', {}).get('destination') or data.get('consignee', {}).get('destination', 'International Destination')}
    </div>
  </div>
"""

    # Line Items Table
    if "line_items" in data:
        html += """<table>
        <thead>
          <tr>
            <th>#</th>
            <th>Description & SKU</th>
            <th>HS Code</th>
            <th class="text-right">Quantity</th>
            <th class="text-right">Unit Price</th>
            <th class="text-right">Total Price</th>
          </tr>
        </thead>
        <tbody>"""
        for item in data["line_items"]:
            html += f"""<tr>
              <td>{item['line_no']}</td>
              <td><strong>{item['name']}</strong><br><small style="color:#64748b">SKU: {item['sku']}</small></td>
              <td><code>{item['hs_code']}</code></td>
              <td class="text-right">{item['quantity']:,} {item['uom']}</td>
              <td class="text-right">${item['unit_price']:,.2f}</td>
              <td class="text-right"><strong>${item['total_price']:,.2f}</strong></td>
            </tr>"""
        html += "</tbody></table>"

    # Totals Box
    if "financial_summary" in data:
        fin = data["financial_summary"]
        html += f"""<div class="totals">
          <div class="totals-box">
            <div class="totals-row"><span>Total Quantity:</span><strong>{fin.get('total_quantity', 0):,}</strong></div>
            <div class="totals-row"><span>Currency:</span><strong>{fin.get('currency', 'USD')}</strong></div>
            <div class="totals-row final"><span>Grand Total:</span><span>{fin.get('currency', 'USD')} ${fin.get('total_amount', 0):,.2f}</span></div>
          </div>
        </div>"""

    # Packaging summary for Packing List
    if "packaging_summary" in data:
        pkg = data["packaging_summary"]
        html += f"""<div class="card" style="margin-bottom: 25px;">
          <div class="card-title">Packaging & Shipment Metrics</div>
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
            <div><strong>Total Cartons:</strong><br>{pkg.get('total_packages_cartons', 0):,} ctns</div>
            <div><strong>Net Weight:</strong><br>{pkg.get('total_net_weight_kg', 0):,.2f} kg</div>
            <div><strong>Gross Weight:</strong><br>{pkg.get('total_gross_weight_kg', 0):,.2f} kg</div>
            <div><strong>Total Volume:</strong><br>{pkg.get('total_cbm_m3', 0):,.2f} m³</div>
          </div>
        </div>"""

    # Footer with SHA-256 Stamp
    html += f"""
    <div class="footer">
      <div>
        <strong>ExportOS Cryptographic Stamp:</strong>
        <div class="hash">SHA-256: {doc.sha256_hash}</div>
      </div>
      <div style="text-align: right;">
        <div>Status: <strong>{doc.status.value}</strong></div>
        <div>Page 1 of 1</div>
      </div>
    </div>
  </body>
  </html>"""
    return html
