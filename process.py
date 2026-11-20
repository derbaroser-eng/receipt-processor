#!/usr/bin/env python3
"""
process.py — deterministic vendor receipt field extractor.

Reads JSON from stdin, writes JSON to stdout.
No external calls, no file I/O, no secrets in output.
"""
import json
import re
import sys


def extract_vendor(text):
    lines = text.split("\n")[:5]
    for line in lines:
        m = re.match(r"^From:\s*(.+)", line, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    m = re.search(r"Thank you for shopping with\s+(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_invoice(text):
    m = re.search(r"(?:order|invoice|receipt)\s+#\s*([\w-]+)", text, re.IGNORECASE)
    return m.group(1) if m else None


def extract_amount(text):
    m = re.search(r"(?:Order Total|Total|Amount):\s*\$\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:USD|EUR)", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ""))
    for line in text.split("\n"):
        if "total" in line.lower():
            m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", line)
            if m:
                return float(m.group(1).replace(",", ""))
    return None


def extract_currency(text):
    if re.search(r"\$|USD", text, re.IGNORECASE):
        return "usd"
    if re.search(r"€|EUR", text, re.IGNORECASE):
        return "eur"
    return None


def extract_date(text):
    m = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    return m.group(1) if m else None


def classify_category(text):
    t = text.lower()
    if any(k in t for k in ["office", "chair", "desk", "lamp", "paper", "pen"]):
        return "office_supplies"
    if any(k in t for k in ["software", "subscription", "license", "saas"]):
        return "software"
    if any(k in t for k in ["flight", "hotel", "taxi", "uber", "lyft"]):
        return "travel"
    if any(k in t for k in ["restaurant", "lunch", "dinner", "coffee"]):
        return "meals"
    if any(k in t for k in ["advertising", "marketing", "ads"]):
        return "marketing"
    return "other"


def extract_fields(text):
    return {
        "vendor": extract_vendor(text),
        "invoice_number": extract_invoice(text),
        "amount": extract_amount(text),
        "currency": extract_currency(text),
        "date": extract_date(text),
        "category": classify_category(text),
    }


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("error: invalid JSON", file=sys.stderr)
        return 1

    if not isinstance(data, dict) or "text" not in data:
        print("error: missing 'text' field", file=sys.stderr)
        return 1

    if not isinstance(data["text"], str):
        print("error: 'text' must be a string", file=sys.stderr)
        return 1

    result = extract_fields(data["text"])

    extracted = [result["vendor"], result["invoice_number"], result["amount"], result["date"]]
    if all(v is None for v in extracted):
        print("error: no fields found in receipt text", file=sys.stderr)
        return 2

    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
