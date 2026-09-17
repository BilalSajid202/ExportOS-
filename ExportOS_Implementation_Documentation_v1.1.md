# ExportOS — AI Export Operations Copilot
## Updated Implementation Documentation
**Version:** 1.1 Draft  
**Date:** 16 September 2026

> This document updates the original ExportOS SRS with the requested **inventory-aware workflow** and converts the project requirements into an implementation roadmap.

---

# 1. Product Overview

ExportOS is an AI-assisted export operations platform for small and medium exporters in Pakistan.

The platform keeps one authoritative deal record from:

**Buyer Inquiry → Inventory Check → Quotation → Order Confirmation → Document Preparation → Compliance Checks → Shipment → Payment → Closure**

The original SRS describes the problem as fragmented work across email, WhatsApp, quotation spreadsheets, invoice templates and manual checklists. ExportOS centralizes that workflow and uses AI for interpretation while keeping financial calculations, validation and approvals deterministic. 

---

# 2. New Feature: Inventory-Aware Export Operations

## 2.1 Goal

ExportOS should connect each organisation's product catalogue with its inventory so that employees can immediately determine whether the requested quantity is available.

Example:

A Sialkot exporter receives:

> "We need 2,500 Size-5 footballs for Germany."

The system extracts:

- Product: Size-5 Football
- Quantity: 2,500
- Destination: Germany

Then it checks inventory:

```text
Current stock:       3,000
Reserved stock:      1,000
Available stock:     2,000

Requested quantity:  2,500
Shortfall:             500
```

The employee sees:

> ⚠️ Not fully available.  
> 2,000 units are available and 500 additional units are required.

This feature should be implemented with deterministic database logic. The LLM may explain the result, but it must not calculate or invent inventory quantities.

---

# 3. Inventory Requirements

## 3.1 Inventory Data

Add inventory information associated with products/SKUs.

Minimum fields:

- product_id
- SKU
- current_quantity
- reserved_quantity
- available_quantity
- reorder_level
- unit_of_measure
- updated_at

Recommended calculation:

```text
available_quantity = current_quantity - reserved_quantity
```

## 3.2 Inventory Status

For a requested quantity:

```text
if available_quantity >= requested_quantity:
    AVAILABLE
else:
    PARTIALLY_AVAILABLE
```

The UI should show:

- Requested
- Current stock
- Reserved
- Available
- Shortfall
- Status

## 3.3 Inventory Reservation

Inventory should support reservations.

Example:

1. Buyer requests 2,000 units.
2. Employee confirms the deal.
3. ExportOS reserves 2,000 units.
4. Available inventory decreases accordingly.
5. When the shipment is completed, reserved stock is converted into shipped/reduced stock.

This prevents multiple employees from promising the same stock.

---

# 4. Updated End-to-End Workflow

```text
Buyer Inquiry
      ↓
Ingestion
      ↓
AI Extraction
      ↓
Human Review
      ↓
Inventory Check
      ↓
Quotation / Costing
      ↓
Human Approval
      ↓
Order Confirmation
      ↓
Inventory Reservation
      ↓
Document Generation
      ↓
Document Consistency Check
      ↓
Compliance / HS Code Review
      ↓
Shipment Tracking
      ↓
Payment Tracking
      ↓
Deal Closed
```

---

# 5. Example: Pakistani Exporter

Imagine a Lahore/Sialkot sports-goods exporter.

A buyer sends an email:

> "Please quote 5,000 size-5 footballs, CIF Hamburg, delivery 15 November."

ExportOS performs:

### Step 1 — Extract

```text
Product: Size-5 Football
Quantity: 5,000
Destination: Hamburg, Germany
Incoterm: CIF Hamburg
Delivery date: 15 November
```

### Step 2 — Inventory

```text
Available: 3,200
Requested: 5,000
Shortfall: 1,800
```

Employee sees:

> ⚠️ Stock is insufficient. 3,200 units are available. 1,800 units need to be produced/procured.

### Step 3 — Quotation

The system calculates the quotation using deterministic code.

For CIF, the costing model includes the applicable main carriage and insurance allocation.

### Step 4 — Approval

The employee reviews:

- Buyer
- Product
- Quantity
- Inventory
- Costs
- Margin
- Incoterm
- Delivery date

Only after approval can the workflow continue.

### Step 5 — Reservation

If the company decides to fulfill 3,200 units from current inventory, ExportOS reserves those units.

### Step 6 — Documents

The system generates the required document set from the same deal revision.

### Step 7 — Validation

The consistency checker verifies quantities, prices, weights, cartons, parties, HS code and Incoterm across documents.

---

# 6. AI vs Deterministic Logic

A major architectural rule remains:

## AI should handle interpretation

Examples:

- Read buyer emails
- Extract product and quantity
- Understand natural-language requests
- Suggest HS codes
- Draft correspondence
- Answer grounded regulation questions
- Summarize deal status

## Normal application code should handle critical calculations

Examples:

- Inventory availability
- Inventory reservation
- Quote calculations
- Currency conversion
- Margins
- Weights
- Cartons
- Volume
- Document comparisons
- Compliance rules
- Deal-state transitions

The original SRS explicitly establishes this determinism boundary and prohibits LLM arithmetic from affecting price, quantity, weight or totals.

---

# 7. Suggested Architecture

```text
                    ┌─────────────────────┐
                    │     React SPA       │
                    │ Dashboard / Deals   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI API     │
                    │ Auth / Deals / AI   │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
       PostgreSQL          Object Storage     Async Queue
             │                                   │
             ▼                                   ▼
      Deal + Inventory                    Background Workers
      + Documents                         Extraction / Docs
      + Audit                             / Compliance
             │
             ▼
       AI / LLM Provider
       + RAG Regulation
       + Embedding Store
```

The original SRS specifies PostgreSQL, a modular backend service, durable asynchronous processing, S3-compatible object storage, vector storage and an SPA frontend.

---

# 8. Recommended Technology Stack

## Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- Alembic
- Redis
- Celery or another durable queue
- Pytest

## Frontend

- React
- Vite
- Tailwind CSS
- React Router
- TanStack Query

## AI

Use a provider-agnostic LLM abstraction.

Possible providers:

- Gemini
- OpenAI
- Anthropic
- Other compatible providers

AI responses must use schema validation.

## Documents

- Server-side HTML/PDF templates
- Object storage for original and generated artifacts
- SHA-256 hashes for generated files

## RAG

- PostgreSQL + pgvector or managed vector storage
- Regulation corpus with source metadata
- Citations and effective dates

---

# 9. Database Model

Core entities from the original SRS:

```text
Organisation
User
Buyer
Product
Deal
DealLineItem
CostComponent
DocumentSet
GeneratedDocument
Artifact
ExtractionResult
ComplianceCheck
Shipment
Payment
AuditEntry
```

## New Inventory Entities

Add:

```text
InventoryItem
InventoryTransaction
InventoryReservation
```

### InventoryItem

```text
id
organisation_id
product_id
sku
current_quantity
reserved_quantity
reorder_level
unit_of_measure
updated_at
```

### InventoryTransaction

Tracks stock changes.

```text
id
organisation_id
inventory_item_id
transaction_type
quantity
reference_type
reference_id
created_by
created_at
```

Example transaction types:

```text
RECEIPT
ADJUSTMENT
RESERVATION
RELEASE
SHIPMENT
```

### InventoryReservation

```text
id
organisation_id
inventory_item_id
deal_id
quantity
status
created_by
created_at
released_at
```

Possible statuses:

```text
ACTIVE
RELEASED
CONSUMED
CANCELLED
```

---

# 10. API Plan

## Authentication

```text
POST /auth/register
POST /auth/login
GET  /auth/me
```

## Products

```text
POST /products
GET  /products
GET  /products/{product_id}
PUT  /products/{product_id}
DELETE /products/{product_id}
```

## Inventory

```text
GET  /inventory
GET  /inventory/{product_id}
POST /inventory/adjust
GET  /inventory/{product_id}/availability
POST /inventory/{product_id}/reserve
POST /inventory/reservations/{reservation_id}/release
```

## Deals

```text
POST /deals
GET  /deals
GET  /deals/{deal_id}
PUT  /deals/{deal_id}
POST /deals/{deal_id}/transition
```

## Inquiry

```text
POST /inquiries/upload
POST /inquiries/email
POST /inquiries/webhook
```

## AI Extraction

```text
POST /deals/{deal_id}/extract
GET  /deals/{deal_id}/extraction
POST /deals/{deal_id}/extraction/confirm
```

## Quotation

```text
POST /deals/{deal_id}/quote
GET  /deals/{deal_id}/quote
POST /deals/{deal_id}/quote/approve
```

## Documents

```text
POST /deals/{deal_id}/documents/generate
GET  /deals/{deal_id}/documents
POST /documents/{document_id}/approve
```

## Compliance

```text
GET  /deals/{deal_id}/compliance
POST /deals/{deal_id}/hs-suggestion
POST /deals/{deal_id}/hs-confirm
```

---

# 11. Implementation Roadmap

Do **not** build the entire system at once.

Build it in the following sequence.

---

## Phase 0 — Project Foundation

### Goal

Create the working application skeleton.

### Tasks

- Create Git repository
- Create backend
- Create frontend
- Configure PostgreSQL
- Configure environment variables
- Add Docker Compose
- Add database migrations
- Create FastAPI application factory
- Create base models
- Add health endpoint
- Configure logging
- Configure CORS
- Add pytest

### First milestone

```text
Frontend → FastAPI → PostgreSQL
```

must work.

---

# Phase 1 — Authentication & Organisation

### Build

- Register
- Login
- JWT/session authentication
- Organisation creation
- User roles
- Tenant isolation

Roles:

```text
ADMIN
EXPORT_MANAGER
DOCUMENTATION_OFFICER
SALES
ACCOUNTS
```

### Test

User A must never access Organisation B's data.

---

# Phase 2 — Product Catalogue

### Build

Product CRUD.

Example:

```text
SKU: FB-S5-001
Name: Size-5 Football
UOM: PCS
Selling Currency: USD
Default HS Code: optional
Weight: 0.45 kg
Carton Capacity: 20
```

### UI

Create:

- Product list
- Product form
- Product details
- Search/filter

---

# Phase 3 — Inventory System ⭐

Build this before AI extraction.

### Step 1

Create `InventoryItem`.

### Step 2

Create stock adjustment.

Example:

```text
+5,000 footballs
```

### Step 3

Create availability calculation.

```text
current - reserved = available
```

### Step 4

Create inventory reservation.

### Step 5

Connect inventory to deals.

### Step 6

Create inventory dashboard.

### Test Cases

```text
Stock = 100
Reserved = 20
Requested = 50
Result = AVAILABLE
Available = 80
```

```text
Stock = 100
Reserved = 80
Requested = 50
Result = PARTIALLY_AVAILABLE
Available = 20
Shortfall = 30
```

### Milestone

An employee can manually create a deal and immediately see whether its products are available.

---

# Phase 4 — Deal Management

Implement the central Deal model.

Deal states:

```text
INQUIRY
QUOTED
CONFIRMED
IN_PRODUCTION
DOCS_READY
SHIPPED
PAID
CLOSED
CANCELLED
```

Implement explicit state transitions.

Do not allow arbitrary state changes.

---

# Phase 5 — Inquiry Ingestion

Support:

1. File upload
2. Email
3. Web form

WhatsApp should come later.

Store the original inbound artifact unchanged.

---

# Phase 6 — AI Extraction

Create a structured extraction schema.

Example:

```json
{
  "product": "Size-5 Football",
  "quantity": 5000,
  "uom": "PCS",
  "destination": "Hamburg, Germany",
  "incoterm": "CIF",
  "incoterm_place": "Hamburg",
  "currency": "USD",
  "target_price": null,
  "delivery_date": "2026-11-15",
  "payment_terms": null
}
```

Every extracted field should include:

- value
- confidence
- source reference
- evidence
- model version
- confirmation status

Never invent missing values.

---

# Phase 7 — AI → Inventory Connection ⭐

This is where the system starts feeling like an actual AI export copilot.

Flow:

```text
Buyer message
     ↓
AI extraction
     ↓
Product matching
     ↓
Inventory lookup
     ↓
Availability result
     ↓
Employee review
```

Example:

```text
Buyer asks: 2,500 footballs

AI:
Product = FB-S5-001
Quantity = 2,500

System:
Available = 2,000

Result:
SHORT BY 500
```

The AI should explain the result but the database/service calculates it.

---

# Phase 8 — Quotation & Costing

Implement deterministic costing.

Support the Incoterms defined in the SRS:

```text
EXW
FCA
FOB
CFR
CIF
CPT
CIP
DAP
DDP
```

Build:

```text
Product cost
+ packaging
+ inland transport
+ export clearance
+ main carriage
+ insurance
+ other applicable costs
+ margin
= quotation
```

Use fixed-point decimal arithmetic.

Never use LLM-generated arithmetic for the final quotation.

---

# Phase 9 — Order Confirmation & Inventory Reservation

After quotation approval:

```text
Quote Approved
      ↓
Order Confirmed
      ↓
Reserve Inventory
```

If stock is insufficient:

```text
Available: 2,000
Required: 2,500
Shortfall: 500
```

Allow the employee to choose the next action:

```text
[Produce/Procure Shortfall]
[Reduce Quantity]
[Cancel]
```

Do not automatically make the commercial decision.

---

# Phase 10 — Document Generation

Generate:

- Proforma Invoice
- Commercial Invoice
- Packing List

All documents must use the same deal revision.

Example:

```text
Deal Revision: R7

Invoice:
5,000 footballs

Packing List:
5,000 footballs

Weight:
2,250 kg
```

---

# Phase 11 — Document Consistency Checker

Compare:

- Quantity
- UOM
- Description
- Unit price
- Total
- Weight
- Cartons
- HS code
- Buyer/seller
- Incoterm

Example:

```text
Invoice:       5,000 PCS
Packing List:  4,800 PCS

❌ BLOCKED
Quantity mismatch: 200 PCS
```

---

# Phase 12 — Compliance & HS Code

Build:

- Destination-based checklist
- Product-based checklist
- Incoterm-based requirements
- Payment-term requirements
- HS code suggestion
- Human confirmation
- Regulation RAG

The system should clearly distinguish:

```text
AI suggestion
Human-confirmed value
Source-derived requirement
```

---

# Phase 13 — Shipment & Payment

Build:

### Shipment

```text
Shipment
Carrier/reference
ETD
ETA
Port
Documents
Status
```

### Payment

```text
Invoice amount
Paid amount
Outstanding amount
Due date
Payment status
```

---

# Phase 14 — Export Copilot

Only after the underlying system is reliable.

The employee can ask:

> "Is the Germany football order ready to ship?"

The copilot should inspect:

- Deal state
- Inventory
- Documents
- Compliance
- Shipment
- Payment requirements

and respond with grounded information.

Example:

```text
The order is not ready to ship.

✓ Inventory reserved: 5,000 PCS
✓ Commercial invoice approved
✓ Packing list approved
⚠ Certificate of origin pending
⚠ Shipping instruction pending
```

---

# Phase 15 — WhatsApp Integration

Add WhatsApp Business integration after the core workflow is stable.

Example:

```text
Buyer WhatsApp
      ↓
WhatsApp Business Platform
      ↓
ExportOS ingestion
      ↓
AI extraction
      ↓
Deal
      ↓
Inventory
```

AI should not automatically send commercial commitments.

Human approval remains required.

---

# 12. Frontend Pages

Build these pages incrementally.

```text
/login
/register

/dashboard

/products
/products/new
/products/:id

/inventory
/inventory/:productId

/deals
/deals/new
/deals/:dealId

/deals/:dealId/inquiry
/deals/:dealId/quote
/deals/:dealId/inventory
/deals/:dealId/documents
/deals/:dealId/compliance
/deals/:dealId/shipment
/deals/:dealId/payment

/copilot
/audit-log
/settings
```

---

# 13. Dashboard

The dashboard should eventually show:

```text
Active Deals
Pending Approvals
Low Stock
Inventory Shortfalls
Documents Awaiting Review
Compliance Issues
Pending Payments
Upcoming Shipments
```

Example:

```text
Active Deals                 24
Pending Approvals             6
Inventory Shortfalls          3
Documents Pending             8
Compliance Issues             2
Outstanding Payments          5
```

---

# 14. MVP Definition

Do not try to implement everything for the first version.

The recommended MVP is:

```text
Authentication
     +
Organisation / Roles
     +
Product Catalogue
     +
Inventory
     +
Deal Management
     +
Inquiry Upload
     +
AI Extraction
     +
Inventory Availability
     +
Quotation
     +
Basic Documents
     +
Consistency Checker
```

This creates a complete demonstrable workflow:

```text
Buyer Inquiry
      ↓
AI extracts order
      ↓
System checks inventory
      ↓
Employee reviews
      ↓
Quotation generated
      ↓
Employee approves
      ↓
Inventory reserved
      ↓
Documents generated
      ↓
Documents validated
```

---

# 15. What NOT to Build First

Avoid starting with:

- Multi-agent orchestration
- Complex autonomous agents
- WhatsApp
- Advanced RAG
- Full accounting
- Customs filing
- Carrier APIs
- Production planning
- Automatic buyer replies

These can come after the core transaction workflow works.

---

# 16. Recommended Development Order

Use this exact order:

```text
01. Repository + Docker
02. FastAPI foundation
03. PostgreSQL + Alembic
04. Authentication
05. Organisation + roles
06. Product catalogue
07. Inventory
08. Inventory reservation
09. Deal model
10. Deal state machine
11. Inquiry upload
12. AI extraction
13. Product matching
14. AI → Inventory availability
15. Quotation engine
16. Quote approval
17. Inventory reservation on confirmation
18. PDF documents
19. Document consistency checker
20. Compliance checklist
21. HS code suggestion
22. Shipment
23. Payment
24. Copilot
25. WhatsApp
26. Production hardening
```

---

# 17. First Development Target

Your **first working demo** should be extremely small:

### Scenario

A Pakistani exporter has:

```text
Product:
Size-5 Football

Inventory:
3,000 units
Reserved:
500 units
Available:
2,500 units
```

Employee creates a deal:

```text
Buyer: German Sports GmbH
Product: Size-5 Football
Quantity: 2,000
```

System responds:

```text
✓ AVAILABLE

Requested: 2,000
Available: 2,500
Remaining after reservation: 500
```

Then employee confirms:

```text
[Reserve 2,000]
```

System updates:

```text
Current stock:     3,000
Reserved:          2,500
Available:           500
```

That gives you the first real business workflow before introducing AI.

---

# 18. Success Criteria

The system should eventually demonstrate:

- One authoritative deal record
- No cross-organisation data leakage
- AI extraction with provenance
- Inventory-aware order processing
- Deterministic financial calculations
- Inventory reservation
- Consistent generated documents
- Human approval before consequential actions
- Complete audit history
- Manual fallback when AI is unavailable
- Grounded compliance answers
- Reproducible generated documents

The original SRS also specifies performance, security, availability, backup, auditability and testing requirements that should be treated as production-hardening work after the core MVP.

---

# 19. Practical FYP Demo Story

For your final demonstration, use one realistic Pakistani exporter scenario.

### Company

**Sialkot Sports Exporters**

### Buyer

**German Sports GmbH**

### Inquiry

> "Please quote 5,000 size-5 footballs, CIF Hamburg."

### ExportOS

```text
1. Reads inquiry
2. Extracts 5,000 footballs
3. Identifies CIF Hamburg
4. Finds matching SKU
5. Checks inventory
6. Shows available / shortfall
7. Calculates quotation
8. Employee approves
9. Reserves stock
10. Generates documents
11. Checks documents for inconsistencies
12. Shows compliance checklist
13. Tracks shipment
14. Tracks payment
```

This gives the project a clear story:

> **Instead of employees copying information between WhatsApp, email, Excel and documents, ExportOS turns an incoming buyer request into a controlled, traceable export workflow while connecting the order to real inventory.**

---

# 20. Original SRS Reference

The following section preserves the original SRS content as the baseline for this update.

ExportOS

AI Export Operations Copilot

Software Requirements Specification

Version 1.0 — Draft

16 September 2026

Prepared for small and medium exporters in Pakistan

Table of contents

1. Introduction

1.1 Purpose

This document specifies the functional and non-functional requirements for ExportOS, an AI-assisted operations platform for small and medium export businesses. It defines what the system must do, the boundaries of its automation, the data it holds, and the criteria by which each release is judged complete.

The specification is written to be implementable. Requirements are individually identified, prioritised, and traceable to the release milestones in Section 9.

1.2 Document conventions

Requirement identifiers follow the pattern FR-XXX-nn for functional requirements and NFR-XXX-nn for non-functional requirements. Priority is recorded as:

M (Must) — the release is not shippable without it.

S (Should) — expected in the release, but may slip one milestone without blocking delivery.

C (Could) — desirable, implemented if capacity allows.

The words "shall" and "must" indicate mandatory behaviour. "Should" indicates recommended behaviour. "May" indicates optional behaviour.

1.3 Intended audience

Engineering — as the build specification and source of acceptance criteria.

Product and design — as the definition of scope and user-visible behaviour.

QA — as the basis for test case derivation.

Pilot customers — Sections 2 and 9 describe capability and delivery sequence in business terms.

1.4 Product scope

ExportOS is the business-side intelligence layer that sits before government trade systems. It takes an export deal from the moment a buyer inquiry arrives through quotation, order confirmation, document preparation, compliance checking, shipment, and payment reconciliation.

The problem it addresses is fragmentation. A typical SME exporter handles a single order across an email inbox, several WhatsApp threads, a quotation spreadsheet, a separate invoice template, a packing list retyped from that invoice, and a manual checklist of required documents. Each retyping is an opportunity for the mismatch that causes consignment rejection, demurrage, or payment delay under a letter of credit.

ExportOS eliminates the retyping by holding one authoritative deal record from which every downstream artifact is generated, and applies AI to the parts that are genuinely interpretive: reading unstructured buyer messages, suggesting classification codes, and answering questions about documentary requirements.

1.5 Out of scope

Filing declarations directly with customs authorities or with the Pakistan Single Window. ExportOS prepares and validates; it does not submit.

Acting as a customs broker, freight forwarder, or provider of legal or regulatory advice.

Full double-entry accounting, payroll, or tax filing. ExportOS tracks receivables against deals and exports data to accounting systems.

Shop-floor production planning, machine scheduling, or bill-of-materials explosion.

Freight rate procurement or carrier booking in version 1.

1.6 Definitions and acronyms

1.7 References

IEEE 830-1998, Recommended Practice for Software Requirements Specifications (structural basis for this document).

ICC Incoterms 2020 rules.

World Customs Organization Harmonised System Nomenclature.

ICC Uniform Customs and Practice for Documentary Credits (UCP 600), for letter of credit document requirements.

Pakistan Single Window published documentation on trade digitisation.

2. Overall description

2.1 Product perspective

ExportOS is a new, self-contained, multi-tenant web application. It is not a replacement for or competitor to national trade systems. It occupies the layer above them: the commercial and documentary work an exporter performs before any government submission is possible.

The system is positioned to become the exporter's system of record for deals. This distinction matters architecturally. If the authoritative quantities, prices, and terms continue to live in the exporter's spreadsheets, ExportOS can only ever be an advisory tool and its consistency guarantees are void. Every requirement in this document assumes ExportOS holds the deal.

2.2 Product functions

At a summary level the system shall:

Ingest buyer inquiries from email, WhatsApp, uploaded documents, and a web form.

Extract structured commercial terms from unstructured messages, with per-field confidence and source traceability.

Maintain a single deal record with full revision history and an append-only audit log.

Compute costed quotations including Incoterm-dependent cost allocation, margin, and multi-currency conversion.

Generate proforma invoices, commercial invoices, and packing lists from the deal record.

Validate consistency across every document in a shipment set before release.

Assemble a documentary checklist based on destination, product, Incoterm, and payment method.

Suggest HS codes with supporting reasoning, for human confirmation.

Answer natural-language questions about a deal and about documentary requirements, grounded in the deal record and a versioned regulation corpus.

Track shipment milestones and payment receipts against each deal.

Enforce human approval at defined gates and record every approval.

2.3 User classes and characteristics

2.4 Operating environment

Web application accessible from current versions of Chrome, Edge, Firefox, and Safari.

Responsive layout usable on tablet and mobile for approval and status actions; full data entry is desktop-oriented.

Server-side deployment on Linux containers with a managed PostgreSQL instance and object storage.

Users operate on variable-quality connectivity. The interface must remain usable at 3G speeds and must never lose entered data on connection interruption.

2.5 Design and implementation constraints

Financial computation shall be performed in tested application code using fixed-point decimal arithmetic. Language models shall not perform arithmetic that affects a price, quantity, weight, or total.

No AI-generated content shall be transmitted externally or treated as final without explicit human approval recorded in the audit log.

The raw inbound artifact for every ingested message shall be retained unmodified.

Documents that customs or banks may rely on shall be reproducible byte-identically from the deal revision they were generated from.

Multi-tenancy shall be enforced at the data access layer; no query path may return records belonging to another organisation.

The system shall function in a degraded but usable mode when the language model provider is unavailable, falling back to manual entry.

2.6 Assumptions and dependencies

Exporters are willing to connect a business email account, or to forward inquiries to a system address.

A usable product catalogue with costs can be established during onboarding; without it the quotation engine cannot function.

Third-party language model APIs remain commercially available at viable per-deal cost.

Regulation and documentary requirement sources can be obtained and kept current; the compliance module is only as good as this corpus.

Exchange rate data is obtainable from a reliable published source.

Pilot customers will be available for validation of costing and Incoterm logic before general release.

3. System architecture

3.1 Architectural overview

The system is organised into five layers. Control flows downward; no layer calls upward.

3.2 The deal state machine

A deal occupies exactly one state. Transitions are explicit, validated, and logged. States marked as gated require recorded human approval before the transition is permitted.

3.3 Worker execution model

Specialist workers do not invoke one another. Each is triggered by a state transition or an explicit user action, reads the current deal revision, performs its work, and writes a result back to the deal. This constraint is deliberate and shall not be relaxed.

The consequences are practical. A failed worker can be retried in isolation without re-running the pipeline. A wrong output can be attributed to exactly one component. Any worker can be replaced, versioned, or A/B tested independently. Error states are visible in the deal record rather than hidden inside an inter-agent conversation.

Workers shall be idempotent with respect to a given deal revision.

Worker invocations shall be recorded in the audit log with inputs, outputs, duration, and model version where applicable.

A worker failure shall place a flag on the deal, not silently drop the task.

Long-running work shall execute asynchronously via a job queue with at-least-once delivery.

3.4 The determinism boundary

This is the most important design decision in the system. Work is assigned to tested code or to a language model according to whether the correct answer is computable. An incorrect invoice total is a commercial and legal failure; an imperfect draft email is not.

3.5 Technology stack

No agent orchestration framework is required for the initial releases. The workers are a small number of functions dispatched on a state column, and introducing a framework early obscures the control flow this architecture depends on.

4. Data requirements

4.1 Core entities

4.2 Deal record structure

The deal record shall contain, at minimum:

Identity — reference number, organisation, buyer, owning user, state, current revision number.

Commercial terms — Incoterm and named place, currency, payment method and terms, validity period, requested delivery date.

Line items — product reference, description as quoted, quantity, unit of measure, unit price, specification notes.

Costing — itemised cost components, margin basis and value, subtotal, total, exchange rate used and its timestamp.

Logistics — port of loading, port of discharge, packing configuration, gross and net weight, volume, carton count, shipping marks.

Classification — HS code, confirmation status, confirming user, rationale.

Compliance — required document checklist with per-item status.

Provenance — for every field, its origin, confidence, and source reference.

4.3 Provenance and confidence model

Every field populated other than by direct human entry shall carry a provenance record.

Fields below a configurable confidence threshold shall be visually flagged and shall block transition out of the inquiry state until reviewed.

4.4 Audit log

Append-only. No update or delete path shall exist in application code.

Every entry records actor (user or named system worker), action, entity, before and after values, timestamp, and request correlation identifier.

Approvals record the exact deal revision approved.

The log shall be exportable per deal as evidence in a dispute.

4.5 Revisions and immutability

A deal revision is created on every change to commercial terms, line items, or costing.

After the confirmed state, terms may not be edited in place; a new revision is required and the prior revision remains retrievable.

A generated document is permanently bound to the revision it was produced from and stores a content hash.

Regenerating a document from an unchanged revision shall produce a byte-identical file.

4.6 Retention

Deal records, documents, and audit entries shall be retained for a configurable period defaulting to seven years, reflecting commercial record-keeping norms.

Raw artifacts shall be retained for the same period unless the organisation configures a shorter window.

Deletion requests shall be honoured by redaction of personal data while preserving the financial and audit skeleton.

5. Functional requirements

Priorities: M = must, S = should, C = could. The milestone in which each group is delivered is given in Section 9.

5.1 Authentication, organisation and access control

5.2 Company profile and configuration

5.3 Buyer management

5.4 Product catalogue

5.5 Inquiry ingestion

5.6 Extraction

5.7 Quotation and costing

5.8 Order confirmation

5.9 Document generation

5.10 Consistency checking

5.11 Compliance and classification

5.12 Shipment tracking

5.13 Payment tracking

5.14 Export copilot

5.15 Approval, audit and notification

6. External interface requirements

6.1 User interfaces

A deal list with filtering by state, buyer, destination, and value, and a prominent count of items awaiting the user's action.

A deal detail view presenting terms, costing, documents, compliance checklist, and activity in a single scrollable page.

An extraction review screen showing extracted fields side by side with the highlighted source text.

A costing screen exposing every component and the resulting unit price, recalculating live.

A document review screen showing rendered previews alongside consistency findings.

Approval actions reachable in one interaction from the notification that raised them.

6.2 Email interface

Inbound via IMAP or a provider API, with OAuth where available; message identifiers, threading headers, and attachments preserved.

Outbound via authenticated SMTP or provider API, sending from the organisation's own domain with correct threading so buyer replies return to the same conversation.

Transmission failures surfaced to the user, never silently retried indefinitely.

6.3 WhatsApp interface

WhatsApp Business Platform API with a verified business number.

Inbound text, image, and document messages captured as artifacts.

Outbound messaging restricted to approved templates and to sessions initiated by the buyer, in accordance with platform rules.

6.4 Language model interface

Provider-agnostic abstraction; the concrete provider shall be replaceable without change to calling code.

Every call records model identifier, prompt version, token usage, and latency.

Structured output enforced by schema validation; a response failing validation is rejected, not partially applied.

Per-organisation and per-deal cost ceilings enforced, with graceful degradation to manual entry when exceeded.

No customer data used for provider model training.

6.5 Exchange rate interface

Daily rates from a published source, stored with timestamp.

The rate applied to a deal is captured at the moment of quotation and does not change thereafter without an explicit user action.

6.6 Future interfaces

Export of a prepared declaration data set for onward submission to national trade systems, should an interface become available.

Accounting system export for invoices and receipts.

Carrier or forwarder tracking feeds for automatic milestone updates.

7. AI-specific requirements

These requirements govern all model-assisted behaviour and take precedence over convenience or automation goals wherever they conflict.

7.1 Grounding and honesty

7.2 Regulation corpus

7.3 Evaluation and quality control

8. Non-functional requirements

8.1 Performance

8.2 Reliability and availability

8.3 Security

8.4 Privacy and data handling

Buyer contact data is personal data and shall be processed only for the purpose of executing the deal.

Data residency shall be configurable where a customer requires it.

An organisation shall be able to export all of its data in a machine-readable format on request.

Sub-processors, including model providers, shall be disclosed to customers.

8.5 Usability and localisation

A new user shall be able to produce a first quotation within thirty minutes of catalogue import without training.

Destructive actions shall require confirmation and shall be reversible where the record is not yet immutable.

Interface language shall be English in the initial release, with the string layer prepared for Urdu.

Numeric, date, weight, and currency formats shall follow conventions appropriate to international trade documentation.

Every blocking validation message shall state what is wrong and what action resolves it.

8.6 Maintainability

Costing, Incoterm allocation, and consistency checking shall be covered by unit tests at no less than ninety percent branch coverage.

Prompts shall be versioned artifacts held in source control, not inline strings.

Document templates shall be data-driven and modifiable without code deployment.

Database schema changes shall be applied through reversible migrations.

9. Release plan and milestones

The sequence is governed by two rules. The deterministic core precedes the AI layer, so that the system degrades to a usable manual tool rather than failing. And each milestone delivers something an exporter could use in isolation, so that validation with real customers begins early.

9.1 Sequencing notes

M0 through M2 constitute the first externally viable product. M1 alone should be placed in front of a pilot exporter before M2 begins, because the costing and Incoterm assumptions are the most likely to be wrong and the fastest to validate.

The copilot and WhatsApp are deliberately last. Both are thin presentation layers over capability already built; delivering them early creates an impressive demonstration over an incomplete foundation.

Supplier matching, anomaly detection, and predictive analytics are excluded from all milestones in this specification. They require transaction volume the system will not have, and building them before that volume exists produces features that cannot work.

10. Acceptance criteria

The system as a whole shall be accepted when all of the following hold.

A buyer inquiry received by email produces a draft deal in which every field is either populated with visible provenance or explicitly empty, with no invented values.

A quotation produced by the system matches a manually computed reference quotation for the same inputs, to the smallest currency unit, across a test set covering every supported Incoterm.

A commercial invoice and packing list generated from the same deal revision agree on every shared field without exception.

The consistency checker detects every seeded discrepancy in the test corpus and reports no false errors on a set of known-good document sets.

The compliance module answers correctly for documented destinations, and returns an explicit statement of ignorance for destinations absent from the corpus rather than an invented answer.

No HS code reaches a generated document without a recorded human confirmation.

No quotation is sent and no document set is released without a recorded approval referencing the exact revision.

The full life of a deal can be reconstructed from the audit log alone.

The system remains usable for manual deal creation, costing, and document generation with the language model provider disabled.

A user from one organisation cannot, by any request, retrieve data belonging to another.

11. Risks and mitigations

Appendix A: Incoterm cost allocation reference

Seller responsibility under Incoterms 2020, as applied by the costing engine. This table is the specification for FR-QUO-02. "Yes" indicates the cost is borne by the seller and is therefore included in the quoted price.

Insurance cover under CIF is minimum-cover by default and under CIP is all-risks by default; the applicable level shall be configurable per deal. Terminal handling at origin and destination shall be configured as separate cost components, since practice varies by trade lane and carrier contract.

Appendix B: Baseline document checklist

The starting rule set for FR-CMP-01. Items are added or removed by destination, product category, and payment method.

Appendix C: Traceability summary

Each functional requirement group maps to the milestone in which it is delivered, and to the acceptance criterion that verifies it.

Term | Definition

Deal | The central record in ExportOS. Represents one commercial opportunity from inquiry through to closure. All documents and events attach to it.

Incoterm | Standardised trade term (EXW, FOB, CFR, CIF, DAP, DDP and others) defining where cost and risk transfer from seller to buyer.

HS code | Harmonised System code. Internationally standardised numeric classification of a traded product, used to determine duty and regulatory treatment.

Commercial invoice | Primary customs document stating the parties, goods, value, and terms of sale.

Packing list | Document detailing how goods are packed: cartons, quantities per carton, gross and net weights, dimensions and markings.

Certificate of origin | Document attesting the country in which the goods were produced, often required for preferential duty treatment.

LC | Letter of Credit. A bank undertaking to pay the exporter on presentation of documents conforming exactly to stated terms.

PSW | Pakistan Single Window. The national digital platform for government-side trade processes.

Extraction | The process of converting an unstructured inbound message into structured deal fields.

Provenance | The recorded origin of a field value: who or what produced it, from which source, and with what confidence.

Determinism boundary | The architectural line separating logic computed by tested code from output produced by a language model.

RAG | Retrieval Augmented Generation. Grounding a model response in retrieved source documents rather than model memory.

User class | Characteristics and needs

Export manager / owner | Primary user. Commercially expert, moderate digital literacy. Needs speed on quotations and confidence in document accuracy. Holds approval authority for pricing and document release.

Documentation officer | Prepares and checks document sets. Detail-oriented, high volume. Needs error detection, not additional data entry.

Sales / inquiry handler | Handles inbound buyer communication. Needs fast conversion of a message into a draft deal and a quotation.

Accounts | Tracks receivables. Read-heavy. Needs payment status against invoices and an aging view.

Administrator | Configures company profile, catalogue, cost components, users and roles. Usually the owner in a small firm.

System (automated) | Scheduled and event-driven workers performing ingestion, extraction, generation, and notification. Subject to the same audit rules as human actors.

Layer | Responsibility

1. Channels | Receive inbound material from email, WhatsApp, file upload, and the buyer web form. Store raw artifacts. No interpretation occurs here.

2. Ingestion and extraction | Classify the artifact, extract structured fields, resolve the buyer and products, and produce or update a draft deal. All AI interpretation is contained in this layer and in the copilot.

3. Deal state machine | The single source of truth. Holds the deal record, its state, its revisions, and its audit log. Mediates every read and write.

4. Specialist workers | Quotation and costing, document generation, compliance and classification, shipment and payment operations. Each reads the deal, performs its task, and writes results back.

5. Approval and audit | Enforces gates. Nothing reaches a buyer, a bank, or an authority without a recorded human approval.

State | Meaning | Exit condition | Gated

inquiry | Draft created from an inbound message or manual entry. Fields may be incomplete or low confidence. | Required fields present and confirmed; costing computed. | No

quoted | A quotation has been generated and sent to the buyer. | Buyer acceptance recorded. | Yes

confirmed | Buyer has accepted. Commercial terms are frozen; changes require a revision. | Production or procurement marked started. | No

in_production | Goods are being manufactured or procured. | Goods ready; packing data captured. | No

docs_ready | Full document set generated and consistency-checked. | Document set approved and released. | Yes

shipped | Goods dispatched; transport document issued. | Delivery or document presentation confirmed. | No

paid | Payment received in full against the invoice. | Reconciliation complete. | No

closed | Deal archived and immutable. | Terminal state. | No

cancelled | Deal abandoned at any stage. Reason recorded. | Terminal state. | Yes

Deterministic code — never a model | Model-assisted — always human-confirmable

Unit costing, extension, and totals | Extracting fields from an unstructured message

Incoterm cost allocation | Classifying an inbound message by intent

Margin and markup calculation | Matching a free-text product description to catalogue SKUs

Currency conversion at a recorded rate | Suggesting an HS code with supporting reasoning

Weight, volume and carton arithmetic | Drafting buyer-facing correspondence

Cross-document field comparison | Answering questions over the regulation corpus

Checklist assembly from configured rules | Explaining why a consistency check failed

State transition validation | Summarising deal history

Concern | Choice | Rationale

Database | PostgreSQL | Relational integrity for financial records; JSONB for extraction provenance.

Backend | Single service, modular internally | Avoids distributed complexity at this scale; split later if needed.

Async work | Durable job queue with retry and dead-letter | Ingestion, generation and notification must survive restarts.

Object storage | S3-compatible | Raw artifacts and generated documents.

Document rendering | Server-side template to PDF | Deterministic, reproducible output.

Vector store | PostgreSQL extension or managed service | Regulation corpus retrieval; avoids a second datastore early.

Frontend | Single-page application | Review and approval workflows are interaction-heavy.

Entity | Purpose | Key relationships

Organisation | Tenant. Holds company profile, export credentials, bank details, branding. | Owns all other records.

User | Named individual with a role. | Belongs to organisation; actor on audit entries.

Buyer | Overseas customer, with addresses, terms, and history. | Has many deals.

Product | Catalogue item with specifications, costs, packing data, HS code. | Referenced by deal line items.

Deal | Central record. State, parties, terms, costing, totals. | Has line items, documents, events, revisions.

DealLineItem | One product, quantity, unit price, specification overrides. | Belongs to deal.

CostComponent | A named cost applied to a deal: freight, insurance, handling, certification. | Belongs to deal or catalogue defaults.

DocumentSet | A versioned collection of generated documents for a shipment. | Belongs to deal.

GeneratedDocument | One rendered artifact with its source deal revision and hash. | Belongs to document set.

Artifact | Raw inbound material: email, attachment, WhatsApp message, upload. | Linked to deal once resolved.

ExtractionResult | Structured output of one extraction run with field-level confidence. | Links artifact to deal.

ComplianceCheck | A checklist item or validation result with status and evidence. | Belongs to deal.

Shipment | Transport details and milestone events. | Belongs to deal.

Payment | A receipt applied against an invoice. | Belongs to deal.

AuditEntry | Immutable record of an action. | References any entity.

Attribute | Description

value | The field value as applied to the deal.

source | One of: human, extraction, catalogue_default, computed, external_api.

confidence | Numeric 0 to 1. Present only where source is extraction. Absent means not applicable, never assumed high.

evidence_ref | Artifact identifier plus character offsets, so the originating text can be displayed to the user.

model_version | Model and prompt version, where source is extraction.

confirmed_by | User who accepted the value, if any, with timestamp.

ID | Requirement | Pri.

FR-AUTH-01 | The system shall authenticate users by email and password with enforced password strength rules. | M

FR-AUTH-02 | The system shall support multi-factor authentication for all users and shall allow an administrator to mandate it organisation-wide. | S

FR-AUTH-03 | The system shall support the roles Administrator, Manager, Documentation Officer, Sales, and Accounts, each with a defined permission set. | M

FR-AUTH-04 | Approval of quotations and release of document sets shall be restricted to roles holding the corresponding approval permission. | M

FR-AUTH-05 | The system shall isolate all data by organisation and shall make cross-organisation data access impossible through any query path. | M

FR-AUTH-06 | The system shall allow an administrator to invite, suspend, and remove users, and shall retain audit attribution for removed users. | M

FR-AUTH-07 | The system shall expire idle sessions after a configurable period and shall allow an administrator to revoke active sessions. | S

ID | Requirement | Pri.

FR-ORG-01 | The system shall store the exporter legal name, addresses, tax and export registration identifiers, bank details, and logo for use on generated documents. | M

FR-ORG-02 | The system shall allow configuration of default currency, default Incoterm, default port of loading, and default payment terms. | M

FR-ORG-03 | The system shall allow definition of reusable cost components with default values and an allocation basis of per unit, per carton, per shipment, or percentage of value. | M

FR-ORG-04 | The system shall allow configuration of the confidence threshold below which extracted fields are flagged for review. | S

FR-ORG-05 | The system shall allow document templates to be selected and branded per organisation. | S

ID | Requirement | Pri.

FR-BUY-01 | The system shall maintain buyer records with company name, country, contact persons, email addresses, phone numbers, and consignee and notify-party addresses. | M

FR-BUY-02 | The system shall store per-buyer defaults for Incoterm, currency, payment terms, packing preferences, and shipping marks. | M

FR-BUY-03 | The system shall match an inbound message to an existing buyer by sender address or phone number and shall present the match for confirmation when ambiguous. | M

FR-BUY-04 | The system shall display a buyer history view showing all deals, their outcomes, and aggregate value. | S

FR-BUY-05 | The system shall support import of buyers from a spreadsheet during onboarding. | S

ID | Requirement | Pri.

FR-CAT-01 | The system shall maintain products with SKU, name, description, specifications, unit of measure, and images. | M

FR-CAT-02 | The system shall store per-product cost data including base manufacturing cost and effective date, and shall retain superseded costs. | M

FR-CAT-03 | The system shall store per-product packing data: units per carton, carton dimensions, net weight, and gross weight. | M

FR-CAT-04 | The system shall store a confirmed HS code per product once established, for reuse on subsequent deals. | M

FR-CAT-05 | The system shall support product variants differing in specification, cost, or packing. | S

FR-CAT-06 | The system shall support import of the catalogue from a spreadsheet during onboarding. | M

FR-CAT-07 | The system shall support tiered pricing by quantity band. | C

ID | Requirement | Pri.

FR-ING-01 | The system shall connect to an organisation email account and ingest inbound messages, or shall accept messages forwarded to a dedicated system address. | M

FR-ING-02 | The system shall store every ingested message and attachment in unmodified form and shall retain the linkage between artifact and deal. | M

FR-ING-03 | The system shall classify each inbound message as an inquiry, a reply to an existing deal, an acceptance, a document, or unrelated. | M

FR-ING-04 | The system shall associate replies with the existing deal using message threading headers and, failing that, content matching presented for confirmation. | M

FR-ING-05 | The system shall accept manual upload of PDF and image documents and shall apply optical character recognition where the document is not machine-readable. | M

FR-ING-06 | The system shall provide a buyer-facing web inquiry form producing a structured deal directly without extraction. | S

FR-ING-07 | The system shall ingest WhatsApp Business messages, including images and documents, and shall associate them with a buyer. | S

FR-ING-08 | The system shall place any artifact it cannot classify into a review queue rather than discarding it. | M

FR-ING-09 | The system shall not send any automated reply to a buyer without explicit user action. | M

ID | Requirement | Pri.

FR-EXT-01 | The system shall extract product description, quantity, unit of measure, destination, Incoterm, named place, currency, target price, requested delivery date, and payment terms from an inquiry message. | M

FR-EXT-02 | The system shall assign a confidence value to every extracted field. | M

FR-EXT-03 | The system shall record, for every extracted field, the source artifact and the character range from which it was derived. | M

FR-EXT-04 | The system shall present extraction results in a review screen displaying each field alongside its source text, with low-confidence fields visually distinguished. | M

FR-EXT-05 | The system shall not populate a field by inference where the source message does not state or clearly imply it; absent fields shall remain empty. | M

FR-EXT-06 | The system shall resolve extracted product descriptions against the catalogue and shall present multiple candidates for selection where the match is ambiguous. | M

FR-EXT-07 | The system shall allow a user to correct any extracted field, recording the correction in the audit log. | M

FR-EXT-08 | The system shall retain user corrections in a form suitable for future evaluation of extraction quality. | S

FR-EXT-09 | The system shall extract from messages in English and shall degrade gracefully, flagging the message for manual entry, where the language is unsupported. | S

FR-EXT-10 | The system shall permit manual creation of a deal without any extraction, and shall remain fully usable when the model provider is unavailable. | M

ID | Requirement | Pri.

FR-QUO-01 | The system shall compute a quotation from line items, cost components, margin, and currency, using fixed-point decimal arithmetic throughout. | M

FR-QUO-02 | The system shall apply Incoterm-dependent cost allocation, including only those cost elements for which the seller is responsible under the selected term. | M

FR-QUO-03 | The system shall support at minimum the terms EXW, FCA, FOB, CFR, CIF, CPT, CIP, DAP and DDP. | M

FR-QUO-04 | The system shall display a full cost breakdown showing every component, its basis, and its contribution to the unit price. | M

FR-QUO-05 | The system shall allow margin to be expressed as a percentage of cost or as a target unit price, and shall display the resulting figure in both forms. | M

FR-QUO-06 | The system shall record the exchange rate and its timestamp on any deal involving currency conversion, and shall not silently update a rate on a quoted deal. | M

FR-QUO-07 | The system shall show the effect on margin when the Incoterm is changed, before the change is committed. | S

FR-QUO-08 | The system shall generate a branded quotation document containing parties, line items, terms, validity period, and totals. | M

FR-QUO-09 | The system shall require explicit approval by an authorised user before a quotation may be marked as sent. | M

FR-QUO-10 | The system shall support quotation revisions, retaining all prior versions and marking the current one. | M

FR-QUO-11 | The system shall record a validity period on each quotation and shall indicate when it has lapsed. | S

FR-QUO-12 | The system shall support quotation in multiple currencies for the same deal for comparison purposes. | C

ID | Requirement | Pri.

FR-ORD-01 | The system shall allow a user to record buyer acceptance, transitioning the deal to confirmed. | M

FR-ORD-02 | The system shall freeze commercial terms on confirmation; subsequent changes shall create a new revision with a recorded reason. | M

FR-ORD-03 | The system shall capture the buyer purchase order reference and attach the purchase order document where supplied. | M

FR-ORD-04 | The system shall capture letter of credit details where the payment method is documentary credit, including issuing bank, expiry, latest shipment date, and required documents. | S

FR-ORD-05 | The system shall warn when the requested delivery date is inconsistent with a recorded production lead time. | C

ID | Requirement | Pri.

FR-DOC-01 | The system shall generate a proforma invoice, a commercial invoice, and a packing list from the deal record. | M

FR-DOC-02 | All documents in a set shall be generated from a single deal revision and shall be prevented from drawing on differing data. | M

FR-DOC-03 | The system shall compute carton counts, net weight, gross weight, and volume from packing configuration rather than accepting free entry, while permitting a recorded override. | M

FR-DOC-04 | The system shall produce documents as PDF and shall store each with a content hash and its source revision. | M

FR-DOC-05 | The system shall support organisation-specific templates for letterhead, signature block, and declaration text. | S

FR-DOC-06 | The system shall generate a certificate of origin application, a beneficiary declaration, and a shipping instruction where required by the checklist. | S

FR-DOC-07 | The system shall present a document set for review and shall require approval before release. | M

FR-DOC-08 | The system shall export an approved document set as a single archive suitable for transmission to a bank or forwarder. | S

FR-DOC-09 | The system shall mark superseded document sets clearly and shall retain them. | M

ID | Requirement | Pri.

FR-CHK-01 | The system shall compare quantity, unit of measure, description, unit price, and total value across every document in a set and shall report any discrepancy. | M

FR-CHK-02 | The system shall verify that net weight does not exceed gross weight and that carton counts are internally consistent. | M

FR-CHK-03 | The system shall verify that the HS code is identical across all documents in which it appears. | M

FR-CHK-04 | The system shall verify that party names and addresses match across documents and match the buyer record. | M

FR-CHK-05 | The system shall verify that the Incoterm and named place stated on the invoice match the deal record. | M

FR-CHK-06 | The system shall block release of a document set containing an unresolved error-severity discrepancy. | M

FR-CHK-07 | The system shall classify findings as error or warning, and shall allow a warning to be overridden with a recorded justification. | M

FR-CHK-08 | The system shall validate a document set against recorded letter of credit terms, including latest shipment date, expiry, described goods, and required documents. | S

FR-CHK-09 | The system shall express each finding in plain language identifying the documents and fields in conflict. | M

ID | Requirement | Pri.

FR-CMP-01 | The system shall assemble a required-document checklist derived from destination country, product category, Incoterm, and payment method. | M

FR-CMP-02 | The system shall track each checklist item as not started, in progress, obtained, or not applicable, with the responsible party recorded. | M

FR-CMP-03 | The system shall suggest an HS code for a product, accompanied by the reasoning and the classification text relied upon. | M

FR-CMP-04 | The system shall require explicit human confirmation of an HS code and shall never present a suggested code as confirmed. | M

FR-CMP-05 | The system shall reuse a previously confirmed HS code for the same product and shall indicate that it was reused. | M

FR-CMP-06 | The system shall answer questions about documentary requirements using only the retrieved regulation corpus, and shall cite the source and its effective date in every answer. | M

FR-CMP-07 | The system shall state that it does not know and shall direct the user to an authoritative source where the corpus does not contain the answer. | M

FR-CMP-08 | The system shall display the effective date and last-verified date of any regulatory content it presents. | M

FR-CMP-09 | The system shall present all regulatory output as informational and shall not represent it as legal or customs advice. | M

FR-CMP-10 | The system shall flag destination countries or products subject to restriction where such data is present in the corpus. | C

ID | Requirement | Pri.

FR-SHP-01 | The system shall record shipment details: mode, carrier, vessel or flight, container numbers, booking reference, and transport document number. | M

FR-SHP-02 | The system shall record milestone events with dates: booking, cargo ready, stuffing, gate-in, departure, arrival, and delivery. | M

FR-SHP-03 | The system shall display a timeline of shipment milestones against planned dates and shall highlight variances. | S

FR-SHP-04 | The system shall support partial shipments against one deal, each with its own document set. | S

FR-SHP-05 | The system shall alert the responsible user when a milestone is overdue. | S

ID | Requirement | Pri.

FR-PAY-01 | The system shall record payments against invoices, including amount, currency, date, and reference. | M

FR-PAY-02 | The system shall compute outstanding balance per deal and per buyer. | M

FR-PAY-03 | The system shall support advance payments received before shipment. | M

FR-PAY-04 | The system shall provide a receivables aging view across all open deals. | S

FR-PAY-05 | The system shall record realised exchange differences where the receipt currency differs from the invoice currency. | S

FR-PAY-06 | The system shall alert the responsible user when payment becomes overdue against recorded terms. | S

FR-PAY-07 | The system shall export payment and invoice data in a format consumable by common accounting packages. | C

ID | Requirement | Pri.

FR-COP-01 | The system shall provide a conversational interface scoped to a single deal, able to answer questions about its terms, documents, and status. | S

FR-COP-02 | The copilot shall answer only from the deal record and the regulation corpus, and shall not assert facts from model memory. | M

FR-COP-03 | The copilot shall cite the deal field or corpus source underlying each answer. | M

FR-COP-04 | The copilot shall be able to initiate actions such as generating a document or running a consistency check, subject to the same approval gates as manual invocation. | S

FR-COP-05 | The copilot shall be able to draft buyer correspondence for user review, and shall never send it directly. | S

FR-COP-06 | The copilot shall decline to answer questions requiring legal or customs judgement and shall direct the user to a competent authority. | M

ID | Requirement | Pri.

FR-APR-01 | The system shall require recorded approval before a quotation is sent, before a document set is released, and before a deal is cancelled. | M

FR-APR-02 | An approval shall record the approving user, the timestamp, and the exact deal revision approved. | M

FR-APR-03 | The system shall invalidate an approval when the underlying revision changes and shall require re-approval. | M

FR-APR-04 | The system shall present a per-deal activity log readable by any user with access to that deal. | M

FR-APR-05 | The system shall notify users of assigned tasks, pending approvals, failed checks, and overdue milestones by email and in-application. | S

FR-APR-06 | The system shall allow notification preferences to be configured per user. | C

ID | Requirement | Pri.

FR-AI-01 | Model output shall be grounded in the deal record or the retrieved corpus. Assertions from model memory shall not be presented as fact. | M

FR-AI-02 | Where a required answer is not available in the grounding sources, the system shall state this plainly rather than producing a plausible answer. | M

FR-AI-03 | Every model-derived value presented to a user shall be visually distinguishable from a human-entered or computed value. | M

FR-AI-04 | Model output shall not be transmitted outside the organisation without recorded human approval. | M

FR-AI-05 | The system shall not perform arithmetic affecting price, quantity, weight, or total by model inference. | M

ID | Requirement | Pri.

FR-AI-06 | Every corpus document shall carry a source identifier, jurisdiction, effective date, and last-verified date. | M

FR-AI-07 | Retrieval shall prefer the version in force at the deal date and shall indicate when only a superseded version is available. | M

FR-AI-08 | Corpus content past its verification interval shall be marked as potentially stale in any answer that relies on it. | M

FR-AI-09 | Answers shall cite the specific document and section relied upon. | M

FR-AI-10 | The corpus shall be versioned so that any historical answer can be reproduced. | S

ID | Requirement | Pri.

FR-AI-11 | A labelled evaluation set of representative inquiry messages shall be maintained and extraction accuracy measured against it per field. | M

FR-AI-12 | A prompt or model change shall not be deployed without an evaluation run demonstrating no regression on the evaluation set. | M

FR-AI-13 | User corrections shall be aggregated to identify systematically weak fields. | S

FR-AI-14 | Confidence calibration shall be monitored; the proportion of accepted-without-edit values shall track the reported confidence. | S

FR-AI-15 | Compliance answers shall be reviewed periodically by a qualified person against the source regulation. | S

ID | Requirement | Pri.

NFR-PER-01 | Interactive page responses shall complete within two seconds at the ninety-fifth percentile under expected load. | M

NFR-PER-02 | Quotation recalculation shall complete within five hundred milliseconds and shall occur client-visible without a page reload. | M

NFR-PER-03 | Extraction of a typical inquiry shall complete within thirty seconds of ingestion. | S

NFR-PER-04 | Generation of a three-document set shall complete within ten seconds. | S

NFR-PER-05 | The system shall support one thousand organisations and two hundred thousand deals without architectural change. | S

ID | Requirement | Pri.

NFR-REL-01 | Monthly availability shall be no less than 99.5 percent excluding announced maintenance. | M

NFR-REL-02 | No ingested artifact shall be lost; ingestion shall be durable before acknowledgement. | M

NFR-REL-03 | Background jobs shall retry with backoff and shall route permanent failures to a dead-letter queue visible to operators. | M

NFR-REL-04 | Unavailability of the model provider shall degrade the system to manual entry, not to failure. | M

NFR-REL-05 | Database backups shall be taken daily with point-in-time recovery, and restoration shall be tested quarterly. | M

ID | Requirement | Pri.

NFR-SEC-01 | All traffic shall be encrypted in transit using current TLS. | M

NFR-SEC-02 | Data at rest, including object storage, shall be encrypted. | M

NFR-SEC-03 | Passwords shall be stored using a current memory-hard hashing algorithm. | M

NFR-SEC-04 | Authorisation shall be enforced server-side on every request; client-side checks are presentational only. | M

NFR-SEC-05 | Uploaded files shall be scanned and shall be served only through signed, expiring URLs. | M

NFR-SEC-06 | Inbound content shall be treated as untrusted data; instructions contained within an ingested message shall never be executed as system instructions. | M

NFR-SEC-07 | Administrative and security-relevant actions shall be logged and alertable. | S

ID | Milestone | Scope | Exit criteria

M0 | Foundation | FR-AUTH, FR-ORG, FR-BUY, FR-CAT, deal schema with revisions, append-only audit log, manual deal creation and editing. | A deal can be created by hand, edited, and transitioned through every state, with every change visible in the audit log. Multi-tenant isolation verified by test.

M1 | Quotation engine | FR-QUO in full, cost components, Incoterm allocation, multi-currency, quotation document generation and approval. | An exporter produces a correctly costed quotation faster than in their existing spreadsheet. Incoterm allocation validated against pilot customer cases. This milestone is independently sellable.

M2 | Inquiry ingestion | FR-ING (email and upload), FR-EXT in full, extraction review screen, buyer and product resolution, thread matching. | An inquiry email becomes a reviewable draft deal without manual typing. Extraction accuracy measured against the evaluation set. Manual entry remains fully functional with the model provider disabled.

M3 | Document set | FR-DOC, FR-CHK, FR-ORD, proforma and commercial invoice, packing list, consistency checker, document approval and release. | A deliberately inconsistent document set is caught on every seeded discrepancy class. Regeneration from an unchanged revision is byte-identical.

M4 | Compliance | FR-CMP, FR-AI-06 to FR-AI-10, regulation corpus with effective dating, checklist assembly, HS code suggestion and confirmation. | Checklists correct for the pilot customers' three most common destinations. The system correctly declines questions outside the corpus instead of answering them.

M5 | Operations | FR-SHP, FR-PAY, FR-APR-05, milestone timeline, receivables aging, notifications. | A deal is tracked end to end from confirmation to payment reconciliation without recourse to an external spreadsheet.

M6 | Copilot and second channel | FR-COP, FR-ING-07 WhatsApp ingestion, FR-DOC-08 document set export. | Deal questions answered with citation to deal fields or corpus sources. WhatsApp inquiries produce draft deals on the same path as email.

Risk | Impact | Mitigation

Incorrect costing or Incoterm allocation reaches a buyer | Severe. Direct financial loss and permanent loss of customer trust. | All financial logic in tested deterministic code; high coverage requirement; validation against pilot customer historical quotations before release.

Extraction populates a field by plausible inference | High. A wrong quantity or delivery date propagates silently into contracts and documents. | FR-EXT-05 prohibits inference; confidence flagging; mandatory review before leaving inquiry state; source text displayed alongside every field.

Regulation corpus becomes stale | High. Confident answers based on superseded rules cause rejected consignments. | Effective and last-verified dating on every document; staleness warnings in answers; explicit refusal outside corpus; periodic qualified review.

Prompt injection via an ingested buyer message | High. A crafted message could attempt to alter system behaviour. | NFR-SEC-06: inbound content treated strictly as data; schema-validated structured output; no autonomous outbound communication.

Exporter keeps authoritative figures in spreadsheets | High. Consistency guarantees void; product reduced to an advisory toy. | Onboarding includes catalogue import; M1 designed to be faster than the spreadsheet it replaces, making adoption the path of least effort.

Model provider cost or availability changes | Medium. Unit economics or service continuity affected. | Provider-agnostic abstraction; per-deal cost ceilings; full manual fallback path maintained as a tested requirement.

Scope expansion into logistics or accounting | Medium. Delivery delayed; core value diluted. | Explicit exclusions in Section 1.5; features requiring transaction volume deferred out of the milestone plan entirely.

Low digital literacy slows adoption | Medium. Pilot conversion fails despite correct software. | Thirty-minute time-to-first-quotation target; spreadsheet import; approval actions reachable in one interaction from a notification.

Term | Inland to port | Export clearance | Main carriage | Insurance | Import duties

EXW | No | No | No | No | No

FCA | Yes | Yes | No | No | No

FOB | Yes | Yes | No | No | No

CFR | Yes | Yes | Yes | No | No

CIF | Yes | Yes | Yes | Yes | No

CPT | Yes | Yes | Yes | No | No

CIP | Yes | Yes | Yes | Yes | No

DAP | Yes | Yes | Yes | Optional | No

DDP | Yes | Yes | Yes | Optional | Yes

Document | Typically required when | Prepared by

Commercial invoice | Always | Exporter (generated by ExportOS)

Packing list | Always | Exporter (generated by ExportOS)

Bill of lading or air waybill | Always | Carrier or forwarder

Certificate of origin | Most destinations; mandatory for preferential duty claims | Chamber of commerce

Insurance certificate | CIF and CIP terms | Insurer

Inspection certificate | Buyer or destination regulation requires it | Third-party inspector

Phytosanitary or health certificate | Agricultural, food, or animal products | Relevant authority

Beneficiary declaration | Letter of credit terms require it | Exporter

Shipping instruction | Always, to the forwarder | Exporter (generated by ExportOS)

Export declaration | Always, filed through national systems | Exporter or clearing agent

Group | Milestone | Verified by

FR-AUTH, FR-ORG | M0 | Acceptance criteria 8 and 10

FR-BUY, FR-CAT | M0 | Acceptance criterion 2 (via catalogue costs)

FR-QUO | M1 | Acceptance criteria 2 and 7

FR-ING, FR-EXT | M2 | Acceptance criteria 1 and 9

FR-ORD, FR-DOC, FR-CHK | M3 | Acceptance criteria 3 and 4

FR-CMP, FR-AI | M4 | Acceptance criteria 5 and 6

FR-SHP, FR-PAY, FR-APR | M5 | Acceptance criteria 7 and 8

FR-COP | M6 | Acceptance criterion 1 (grounding)
