# SPEC — Vendor Receipt and Invoice Processing

## What it does

Takes a plain-text email body (from a vendor receipt email) and extracts key fields:
- Vendor name
- Invoice number
- Amount
- Currency
- Date
- Category (office supplies, software, travel, meals, other)

Outputs structured JSON ready for accounting software.

## What it does NOT do

- Does not connect to Gmail or any email service
- Does not parse PDFs or images (plain text only)
- Does not store receipt data
- Does not use an LLM

## Input

```json
{
  "text": "From: Amazon Business
Subject: Your order has shipped

Hi John,

Your order #123-4567890-1234567 has been placed.

Order Total: $156.78
Date: 2026-01-15

Items:
- Office Chair $120.00
- Desk Lamp $36.78

Thank you for shopping with Amazon Business."
}
```

## Output

```json
{
  "vendor": "Amazon Business",
  "invoice_number": "123-4567890-1234567",
  "amount": 156.78,
  "currency": "usd",
  "date": "2026-01-15",
  "category": "office_supplies"
}
```

## Exit codes

- `0` — success, fields extracted
- `1` — invalid input (missing `text` field, non-string)
- `2` — no fields found (unrecognized email format)

## Rules (deterministic, no ML)

### Vendor extraction
- Look for `From: <vendor>` in the first 5 lines
- If not found, look for `Thank you for shopping with <vendor>`
- If not found, `vendor: null`

### Invoice number
- Look for `order #<number>` or `invoice #<number>` or `receipt #<number>`
- Capture the number (alphanumeric with dashes)
- If not found, `invoice_number: null`

### Amount extraction
- Look for `Order Total: $<amount>` or `Total: $<amount>` or `Amount: $<amount>`
- Capture the number as a float
- If not found, look for `$<amount>` on a line with `total` (case-insensitive)
- If not found, `amount: null`

### Currency
- `$` or `USD` → `usd`
- `€` or `EUR` → `eur`
- If not found, `currency: null`

### Date extraction
- Look for `Date: <date>` or `date: <date>`
- Date format: YYYY-MM-DD
- If not found, `date: null`

### Category classification
- If text contains `office` or `chair` or `desk` or `lamp` or `paper` or `pen` → `office_supplies`
- If text contains `software` or `subscription` or `license` or `SaaS` → `software`
- If text contains `flight` or `hotel` or `taxi` or `uber` or `lyft` → `travel`
- If text contains `restaurant` or `lunch` or `dinner` or `coffee` → `meals`
- If text contains `advertising` or `marketing` or `ads` → `marketing`
- Otherwise → `other`

## Constraints

- No external API calls
- No file I/O beyond reading stdin and writing stdout
- No secrets in output
- Deterministic: same input → same output
