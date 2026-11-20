#!/usr/bin/env python3
"""
test_receipt_processor.py — failing tests for receipt-processor.

Run: python workspace/products/receipt-processor/test_receipt_processor.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "process.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append((name, cond, detail))


def run_process(payload: dict) -> dict:
    r = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if r.returncode != 0:
        return {"error": f"exit={r.returncode}", "stderr": r.stderr[:200]}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid_json", "stdout": r.stdout[:200]}


def base_text():
    return ("From: Amazon Business\n"
            "Subject: Your order has shipped\n\n"
            "Hi John,\n\n"
            "Your order #123-4567890-1234567 has been placed.\n\n"
            "Order Total: $156.78\n"
            "Date: 2026-01-15\n\n"
            "Items:\n"
            "- Office Chair $120.00\n"
            "- Desk Lamp $36.78\n\n"
            "Thank you for shopping with Amazon Business.")


# --- test 1: vendor extraction ---
out = run_process({"text": base_text()})
check("vendor: extracted", isinstance(out, dict) and out.get("vendor") == "Amazon Business", str(out)[:100])

# --- test 2: invoice number ---
check("invoice: extracted", out.get("invoice_number") == "123-4567890-1234567", str(out))

# --- test 3: amount ---
check("amount: 156.78", out.get("amount") == 156.78, str(out))

# --- test 4: currency ---
check("currency: usd", out.get("currency") == "usd", str(out))

# --- test 5: date ---
check("date: 2026-01-15", out.get("date") == "2026-01-15", str(out))

# --- test 6: category ---
check("category: office_supplies", out.get("category") == "office_supplies", str(out))

# --- test 7: software category ---
out = run_process({"text": "From: Stripe\nSubject: Receipt\n\nTotal: $49.00\nDate: 2026-02-01\n\nSoftware subscription"})
check("category: software", out.get("category") == "software", str(out))

# --- test 8: travel category ---
out = run_process({"text": "From: Uber\nSubject: Receipt\n\nTotal: $25.00\nDate: 2026-02-01\n\nFlight to NYC"})
check("category: travel", out.get("category") == "travel", str(out))

# --- test 9: meals category ---
out = run_process({"text": "From: Restaurant\nSubject: Receipt\n\nTotal: $85.00\nDate: 2026-02-01\n\nDinner with client"})
check("category: meals", out.get("category") == "meals", str(out))

# --- test 10: other category ---
out = run_process({"text": "From: Unknown\nSubject: Receipt\n\nTotal: $10.00\nDate: 2026-02-01\n\nMiscellaneous"})
check("category: other", out.get("category") == "other", str(out))

# --- test 11: EUR currency ---
out = run_process({"text": "From: Vendor\nSubject: Receipt\n\nTotal: 49.00 EUR\nDate: 2026-02-01"})
check("eur: currency", out.get("currency") == "eur", str(out))
check("eur: amount", out.get("amount") == 49.0, str(out))

# --- test 12: no fields found → exit 2 ---
r = subprocess.run(
    [sys.executable, str(SCRIPT)],
    input=json.dumps({"text": "Hello world, nothing here."}),
    capture_output=True, text=True, timeout=10,
)
check("nofields: exit 2", r.returncode == 2, f"rc={r.returncode}")

# --- test 13: invalid input (missing text) ---
r = subprocess.run(
    [sys.executable, str(SCRIPT)],
    input=json.dumps({"foo": "bar"}),
    capture_output=True, text=True, timeout=10,
)
check("invalid: exit 1", r.returncode == 1, f"rc={r.returncode}")

# --- test 14: invalid input (non-string text) ---
r = subprocess.run(
    [sys.executable, str(SCRIPT)],
    input=json.dumps({"text": 123}),
    capture_output=True, text=True, timeout=10,
)
check("wrongtype: exit 1", r.returncode == 1, f"rc={r.returncode}")

# --- test 15: no secrets in output ---
secret_input = "From: SecretVendor\nSubject: Receipt\n\nTotal: $100.00\nDate: 2026-02-01\n\nInternal note: do not leak this."
out = run_process({"text": secret_input})
if isinstance(out, dict):
    check("no secrets: full input not echoed", secret_input not in json.dumps(out), str(out))
    check("no secrets: internal note not in output", "do not leak this" not in json.dumps(out), str(out))

# --- test 16: deterministic ---
out1 = run_process({"text": base_text()})
out2 = run_process({"text": base_text()})
check("deterministic: same output", out1 == out2, f"{out1} vs {out2}")

# --- report ---
passed = sum(1 for _, ok, _ in results if ok)
failed = [(n, d) for n, ok, d in results if not ok]
print(f"\n{passed}/{len(results)} assertions passed")
if failed:
    print("\nFAILED:")
    for n, d in failed:
        print(f"  {n}  ({d})")
    sys.exit(1)
print("ALL TESTS GREEN")
