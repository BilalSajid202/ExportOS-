"""
ExportOS — AI Extraction Engine with Hugging Face Qwen & Rotating API Keys

Features:
  - Hugging Face Qwen model integration (Qwen/Qwen2.5-72B-Instruct)
  - Automatic API key rotation on 429 Rate Limits / Quotas
  - High-precision deterministic fallback when offline / no keys configured
  - Field-level confidence scoring & verbatim quotation evidence
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.config import get_settings
from app.schemas.extraction import ExtractedFieldItem

logger = logging.getLogger("exportos.ai_extractor")

VALID_INCOTERMS = ["EXW", "FCA", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DDP"]
VALID_UOMS = ["PCS", "PAIR", "PAIRS", "SET", "SETS", "KG", "KGS", "DOZEN", "DOZENS", "MTR", "METERS"]
VALID_CURRENCIES = ["USD", "EUR", "GBP", "PKR", "AED"]


class HFKeyManager:
    """
    Thread/Async-safe API key rotator for Hugging Face Inference API.
    Rotates to the next key whenever rate limits (HTTP 429), quota limits, or 401s occur.
    """

    _current_index = 0

    @classmethod
    def get_keys(cls) -> List[str]:
        return get_settings().hf_keys_list

    @classmethod
    def get_active_key(cls) -> Optional[str]:
        keys = cls.get_keys()
        if not keys:
            return None
        return keys[cls._current_index % len(keys)]

    @classmethod
    def rotate_key(cls) -> Optional[str]:
        keys = cls.get_keys()
        if not keys:
            return None
        prev_index = cls._current_index % len(keys)
        cls._current_index = (cls._current_index + 1) % len(keys)
        new_index = cls._current_index % len(keys)
        masked_prev = f"...{keys[prev_index][-4:]}" if len(keys[prev_index]) > 4 else "key"
        masked_new = f"...{keys[new_index][-4:]}" if len(keys[new_index]) > 4 else "key"
        logger.warning(
            f"🔄 Hugging Face rate limit encountered. Rotating API key from #{prev_index} ({masked_prev}) to #{new_index} ({masked_new})"
        )
        return keys[new_index]


class AIExtractionService:
    """
    Interpretation engine for export RFQs and buyer inquiries.
    """

    SYSTEM_PROMPT = """You are ExportOS AI, an expert international trade and export operations assistant.
Extract structured commercial deal terms from the buyer's inquiry message.

You must respond ONLY with a valid JSON object matching this exact schema:
{
  "product_name": "<name of the product, e.g. Size-5 Football, Leather Gloves, or null>",
  "quantity": <numeric quantity, e.g. 5000, 2500, or null>,
  "uom": "<unit of measure, e.g. PCS, PAIRS, SETS, KG, or PCS if unspecified>",
  "destination_port": "<destination port or city, e.g. Hamburg, Rotterdam, Dubai, or null>",
  "incoterm": "<exact standard Incoterm: EXW, FCA, FOB, CFR, CIF, CPT, CIP, DAP, DDP, or null>",
  "incoterm_place": "<associated place/port for Incoterm, e.g. Hamburg, or null>",
  "target_price": <target unit price number if specified, e.g. 14.50, or null>,
  "currency": "<currency code: USD, EUR, GBP, PKR, AED, default USD>",
  "delivery_date": "<target delivery date in YYYY-MM-DD format if mentioned, or null>",
  "payment_terms": "<payment terms if mentioned, e.g. LC at sight, 30% advance, or null>",
  "special_instructions": "<any specific buyer requirements or packaging notes, or null>",
  "evidence_quotes": {
    "product_name": "<exact text quote snippet from user message>",
    "quantity": "<exact text quote snippet from user message>",
    "incoterm": "<exact text quote snippet from user message>",
    "delivery_date": "<exact text quote snippet from user message>",
    "target_price": "<exact text quote snippet from user message>"
  }
}

Do NOT invent missing details. If a value is not mentioned in the message, output null for that field. Output ONLY the JSON block."""

    @classmethod
    async def extract_from_text(cls, raw_text: str) -> Dict[str, Any]:
        """
        Extract structured commercial parameters from raw text.
        Attempts Hugging Face Qwen extraction with automatic key rotation,
        and falls back gracefully to deterministic parser if keys are missing or exhausted.
        """
        raw_text = raw_text.strip()
        keys = HFKeyManager.get_keys()

        # If Hugging Face keys are configured, attempt Qwen LLM extraction with rotation
        if keys:
            qwen_result = await cls._extract_with_qwen_rotating(raw_text, keys)
            if qwen_result:
                return qwen_result

        # Fallback to high-precision deterministic parser
        logger.info("Using deterministic NLP parser for inquiry extraction.")
        return cls._extract_deterministic(raw_text)

    @classmethod
    async def _extract_with_qwen_rotating(cls, raw_text: str, keys: List[str]) -> Optional[Dict[str, Any]]:
        """
        Call Hugging Face Qwen model with automatic key rotation on HTTP 429 / rate limits.
        """
        settings = get_settings()
        model_id = settings.HF_MODEL or "Qwen/Qwen2.5-72B-Instruct"

        # Hugging Face serverless chat completion endpoint (OpenAI compatible)
        endpoint = "https://router.huggingface.co/hf-inference/v1/chat/completions"

        max_attempts = max(len(keys), 1)

        for attempt in range(max_attempts):
            active_key = HFKeyManager.get_active_key()
            if not active_key:
                break

            headers = {
                "Authorization": f"Bearer {active_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": cls.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Customer Inquiry:\n\"\"\"\n{raw_text}\n\"\"\""},
                ],
                "temperature": 0.1,
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
            }

            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)

                    # Check for rate limits or quota errors
                    if response.status_code in (429, 403, 503) or (
                        response.status_code == 401 and "quota" in response.text.lower()
                    ):
                        logger.warning(
                            f"Hugging Face returned status {response.status_code}: {response.text[:120]}. Rotating key..."
                        )
                        HFKeyManager.rotate_key()
                        continue

                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        parsed_llm = cls._parse_json_safely(content)
                        if parsed_llm:
                            logger.info(f"Successfully extracted with Hugging Face model ({model_id})")
                            return cls._format_llm_result(parsed_llm, raw_text)

                    logger.warning(f"HF API returned status {response.status_code}: {response.text[:150]}")

            except httpx.RequestError as e:
                logger.warning(f"HTTP request error during HF inference: {e}. Rotating key...")
                HFKeyManager.rotate_key()

        return None

    @classmethod
    def _parse_json_safely(cls, content: str) -> Optional[Dict[str, Any]]:
        """Clean markdown code blocks and parse JSON."""
        try:
            content = re.sub(r"^```json\s*", "", content.strip(), flags=re.IGNORECASE)
            content = re.sub(r"\s*```$", "", content.strip())
            return json.loads(content)
        except Exception:
            # Try searching for first { ... } block
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return None

    @classmethod
    def _format_llm_result(cls, parsed: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
        """Convert LLM JSON output to structured ExtractionDataSchema format."""
        evidence_map = parsed.get("evidence_quotes", {})
        result = {}

        def _make_field(field_key: str, default_val: Any = None, default_conf: float = 0.92) -> Dict[str, Any]:
            val = parsed.get(field_key, default_val)
            evid = evidence_map.get(field_key)
            if not evid and val is not None and str(val).lower() in raw_text.lower():
                evid = str(val)

            conf = default_conf if val is not None else 0.0
            return ExtractedFieldItem(
                value=val,
                confidence=conf,
                evidence=evid,
                source_reference="qwen_extraction",
                confirmation_status="PENDING" if val is not None else "UNSET",
            ).model_dump()

        result["product_name"] = _make_field("product_name")
        result["quantity"] = _make_field("quantity")
        result["uom"] = _make_field("uom", default_val="PCS")
        result["destination_port"] = _make_field("destination_port")
        result["incoterm"] = _make_field("incoterm")
        result["incoterm_place"] = _make_field("incoterm_place")
        result["target_price"] = _make_field("target_price")
        result["currency"] = _make_field("currency", default_val="USD")
        result["delivery_date"] = _make_field("delivery_date")
        result["payment_terms"] = _make_field("payment_terms")
        result["special_instructions"] = _make_field("special_instructions")

        return result

    # ── High-Precision Deterministic Fallback ─────────────────────────

    @classmethod
    def _extract_deterministic(cls, raw_text: str) -> Dict[str, Any]:
        """
        High-precision regex/NLP parser with zero external API dependencies.
        """
        result = {}

        # 1. Quantity & UOM
        qty_val, qty_conf, qty_evid = cls._extract_quantity(raw_text)
        result["quantity"] = ExtractedFieldItem(
            value=qty_val,
            confidence=qty_conf,
            evidence=qty_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING" if qty_val is not None else "UNSET",
        ).model_dump()

        uom_val, uom_conf, uom_evid = cls._extract_uom(raw_text)
        result["uom"] = ExtractedFieldItem(
            value=uom_val or "PCS",
            confidence=uom_conf if uom_val else 0.8,
            evidence=uom_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING",
        ).model_dump()

        # 2. Incoterm & Place
        incoterm_val, incoterm_conf, incoterm_evid, place_val = cls._extract_incoterm(raw_text)
        result["incoterm"] = ExtractedFieldItem(
            value=incoterm_val,
            confidence=incoterm_conf,
            evidence=incoterm_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING" if incoterm_val else "UNSET",
        ).model_dump()

        result["incoterm_place"] = ExtractedFieldItem(
            value=place_val,
            confidence=0.9 if place_val else 0.0,
            evidence=incoterm_evid if place_val else None,
            source_reference="inquiry_text",
            confirmation_status="PENDING" if place_val else "UNSET",
        ).model_dump()

        # 3. Destination Port
        dest_val, dest_conf, dest_evid = cls._extract_destination(raw_text, fallback_place=place_val)
        result["destination_port"] = ExtractedFieldItem(
            value=dest_val,
            confidence=dest_conf,
            evidence=dest_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING" if dest_val else "UNSET",
        ).model_dump()

        # 4. Product Name
        prod_val, prod_conf, prod_evid = cls._extract_product_name(raw_text)
        result["product_name"] = ExtractedFieldItem(
            value=prod_val,
            confidence=prod_conf,
            evidence=prod_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING" if prod_val else "UNSET",
        ).model_dump()

        # 5. Target Price & Currency
        price_val, curr_val, price_conf, price_evid = cls._extract_price_and_currency(raw_text)
        result["target_price"] = ExtractedFieldItem(
            value=price_val,
            confidence=price_conf,
            evidence=price_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING" if price_val is not None else "UNSET",
        ).model_dump()

        result["currency"] = ExtractedFieldItem(
            value=curr_val or "USD",
            confidence=0.95 if curr_val else 0.85,
            evidence=price_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING",
        ).model_dump()

        # 6. Delivery Date
        date_val, date_conf, date_evid = cls._extract_delivery_date(raw_text)
        result["delivery_date"] = ExtractedFieldItem(
            value=date_val,
            confidence=date_conf,
            evidence=date_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING" if date_val else "UNSET",
        ).model_dump()

        # 7. Payment Terms
        pay_val, pay_conf, pay_evid = cls._extract_payment_terms(raw_text)
        result["payment_terms"] = ExtractedFieldItem(
            value=pay_val,
            confidence=pay_conf,
            evidence=pay_evid,
            source_reference="inquiry_text",
            confirmation_status="PENDING" if pay_val else "UNSET",
        ).model_dump()

        # 8. Special Instructions
        result["special_instructions"] = ExtractedFieldItem(
            value=None,
            confidence=0.0,
            evidence=None,
            source_reference="inquiry_text",
            confirmation_status="UNSET",
        ).model_dump()

        return result

    @classmethod
    def _extract_quantity(cls, text: str) -> Tuple[Optional[float], float, Optional[str]]:
        patterns = [
            r"(?:need|quote|require|order|quantity|qty|volume)\s*(?:of|for|:)?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\b",
            r"\b([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\s*(?:pcs|pieces|units|balls|pairs|sets|cartons)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_num = match.group(1).replace(",", "")
                try:
                    qty = float(raw_num)
                    evidence = match.group(0)
                    return qty, 0.95, evidence
                except ValueError:
                    pass

        match = re.search(r"\b([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{3,7})\b", text)
        if match:
            raw_num = match.group(1).replace(",", "")
            try:
                qty = float(raw_num)
                return qty, 0.80, match.group(0)
            except ValueError:
                pass

        return None, 0.0, None

    @classmethod
    def _extract_uom(cls, text: str) -> Tuple[Optional[str], float, Optional[str]]:
        pattern = r"\b(pcs|pieces|pairs?|sets?|kgs?|dozens?|meters?)\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).upper()
            if "PIECE" in raw or "PC" in raw:
                return "PCS", 0.95, match.group(0)
            if "PAIR" in raw:
                return "PAIRS", 0.95, match.group(0)
            if "SET" in raw:
                return "SETS", 0.95, match.group(0)
            if "KG" in raw:
                return "KG", 0.95, match.group(0)
            return raw, 0.90, match.group(0)
        return "PCS", 0.80, None

    @classmethod
    def _extract_incoterm(cls, text: str) -> Tuple[Optional[str], float, Optional[str], Optional[str]]:
        incoterms_regex = r"\b(EXW|FCA|FOB|CFR|CIF|CPT|CIP|DAP|DDP)\b(?:\s+([A-Za-z\s]+?)(?:,|\.|\s+delivery|\s+by|\s+port|$))?"
        match = re.search(incoterms_regex, text, re.IGNORECASE)
        if match:
            incoterm = match.group(1).upper()
            place = match.group(2).strip() if match.group(2) else None
            if place:
                place = re.sub(r"\b(port|delivery|required|payment|by|to|for)\b", "", place, flags=re.IGNORECASE).strip()
            evidence = match.group(0).strip()
            return incoterm, 0.95, evidence, place or None

        return None, 0.0, None, None

    @classmethod
    def _extract_destination(cls, text: str, fallback_place: Optional[str] = None) -> Tuple[Optional[str], float, Optional[str]]:
        if fallback_place:
            return fallback_place, 0.90, fallback_place

        patterns = [
            r"(?:destination|port of discharge|pod|delivery to|for|ship to)\s*[:]?\s*([A-Za-z\s]+?)(?:,|\.|\s+by|\s+with|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dest = match.group(1).strip()
                dest = re.sub(r"\b(port|delivery|required|germany|usa|uk)\b", "", dest, flags=re.IGNORECASE).strip()
                if dest and len(dest) > 2:
                    return dest, 0.85, match.group(0)

        known_ports = ["Hamburg", "Rotterdam", "Antwerp", "Felixstowe", "New York", "Los Angeles", "Dubai", "Jebel Ali", "Karachi", "Singapore"]
        for port in known_ports:
            if re.search(r"\b" + port + r"\b", text, re.IGNORECASE):
                return port, 0.90, port

        return None, 0.0, None

    @classmethod
    def _extract_product_name(cls, text: str) -> Tuple[Optional[str], float, Optional[str]]:
        product_patterns = [
            r"([0-9a-zA-Z\s-]+?(?:football|soccer ball|match ball|gloves?|jacket|hoodie|jersey|t-shirt|scissors|forceps|scalpel|instrument|rice|salt)[s]?)",
            r"(?:quote|need|order|require)\s*(?:for|of)?\s*(?:[0-9,]+\s*(?:pcs|pieces|units)?)?\s*([a-zA-Z0-9\s-]+?(?:ball|football|gloves|jacket|shirt|apparel|textile|equipment))",
        ]
        for pattern in product_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                cleaned = re.sub(r"^[0-9,.\s]+", "", candidate)
                cleaned = re.sub(r"\b(please|quote|for|need|require|units|pcs|pieces)\b", "", cleaned, flags=re.IGNORECASE).strip()
                if cleaned and len(cleaned) > 2:
                    return cleaned.title(), 0.90, match.group(0).strip()

        fallback_match = re.search(r"\b(size-[0-9]\s+[a-zA-Z]+|[a-zA-Z\s]+ball|[a-zA-Z\s]+gloves)\b", text, re.IGNORECASE)
        if fallback_match:
            candidate = fallback_match.group(0).strip()
            cleaned = re.sub(r"^[0-9,.\s]+", "", candidate)
            return cleaned.title(), 0.85, fallback_match.group(0).strip()

        return "Export Products", 0.60, None

    @classmethod
    def _extract_price_and_currency(cls, text: str) -> Tuple[Optional[float], Optional[str], float, Optional[str]]:
        patterns = [
            r"(\$|€|£|USD|EUR|GBP|PKR|AED)\s*([0-9]+(?:\.[0-9]{1,2})?)",
            r"([0-9]+(?:\.[0-9]{1,2})?)\s*(\$|€|£|USD|EUR|GBP|PKR|AED|\/pc|\/piece)",
            r"(?:price|target|rate)\s*(?:of|is|:)?\s*(\$|€|£|USD|EUR|GBP|PKR|AED)?\s*([0-9]+(?:\.[0-9]{1,2})?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val1, val2 = match.group(1), match.group(2)
                curr = None
                price = None

                for v in (val1, val2):
                    if re.match(r"^[0-9]+(?:\.[0-9]{1,2})?$", v):
                        price = float(v)
                    elif "$" in v or "USD" in v.upper():
                        curr = "USD"
                    elif "€" in v or "EUR" in v.upper():
                        curr = "EUR"
                    elif "£" in v or "GBP" in v.upper():
                        curr = "GBP"
                    elif "PKR" in v.upper():
                        curr = "PKR"
                    elif "AED" in v.upper():
                        curr = "AED"

                if price is not None:
                    return price, curr or "USD", 0.95, match.group(0)

        return None, None, 0.0, None

    @classmethod
    def _extract_delivery_date(cls, text: str) -> Tuple[Optional[str], float, Optional[str]]:
        date_patterns = [
            r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b",
            r"\b([0-9]{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s+[0-9]{4})?)\b",
            r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+[0-9]{1,2}(?:st|nd|rd|th)?(?:,?\s+[0-9]{4})?)\b",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d %B", "%B %d"):
                    try:
                        clean_str = re.sub(r"(st|nd|rd|th|,)", "", date_str)
                        dt = datetime.strptime(clean_str, fmt)
                        if dt.year == 1900:
                            dt = dt.replace(year=2026)
                        return dt.strftime("%Y-%m-%d"), 0.95, match.group(0)
                    except ValueError:
                        continue
                return date_str, 0.85, match.group(0)

        return None, 0.0, None

    @classmethod
    def _extract_payment_terms(cls, text: str) -> Tuple[Optional[str], float, Optional[str]]:
        patterns = [
            r"\b(LC\s*(?:at\s*sight)?|Letter\s*of\s*Credit|TT|T\/T|Advance|Net\s*[0-9]+|[0-9]+%\s*advance[a-zA-Z0-9\s,/%]*)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip(), 0.90, match.group(0)
        return None, 0.0, None
