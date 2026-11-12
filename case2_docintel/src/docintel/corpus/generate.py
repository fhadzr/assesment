"""Seeded synthetic invoice corpus generator (task 1.3).

Renders each invoice TWICE with identical content:
  - text PDF  (reportlab: fields as real text objects)
  - image PNG (Pillow: the same text rasterized into pixels)
plus the expected JSON (8 fields, ISO-normalized) and manifests.

Determinism contract: same args -> byte-identical outputs. No timestamps or
random ids are embedded in rendered bytes; reportlab/Pillow are pinned.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from docintel.corpus.schema import CURRENCIES, DATE_FORMATS, FIELD_NAMES, LABEL_VARIANTS, MASKABLE_PII_FIELDS

GENERATOR_VERSION = "1.0.0"
MIN_INVOICES, MAX_INVOICES = 15, 30

VENDOR_WORDS_A = ("Bluepeak", "Northgale", "Silverdock", "Amberline", "Terrafold", "Quartzvale", "Lumenbay", "Ferncrest")
VENDOR_WORDS_B = ("Services", "Trading", "Supplies", "Logistics", "Consulting", "Systems")


def _validate(n_invoices: int) -> None:
    if not (MIN_INVOICES <= n_invoices <= MAX_INVOICES):
        raise ValueError(f"--n-invoices must be within [{MIN_INVOICES}, {MAX_INVOICES}]; got {n_invoices}")


def _make_invoice(rng: random.Random, idx: int) -> dict:
    """Content model for one invoice (both renderings + expected JSON derive from it)."""
    variant = rng.randrange(3)  # layout variant per invoice
    inv_date = date(2026, 3, 1) + timedelta(days=rng.randrange(120))
    due_date = inv_date + timedelta(days=rng.choice((7, 14, 30, 45)))
    subtotal = Decimal(rng.randrange(1500, 98000)) / Decimal("10")  # 150.0 .. 9800.0, 1dp
    tax = (subtotal * Decimal("0.11")).quantize(Decimal("0.01"))
    total = (subtotal + tax).quantize(Decimal("0.01"))
    vendor = f"{rng.choice(VENDOR_WORDS_A)} {rng.choice(VENDOR_WORDS_B)}"
    return {
        "variant": variant,
        "invoice_number": f"INV-{100000 + idx * 7 + rng.randrange(5):06d}",
        "invoice_date": inv_date,
        "due_date": due_date,
        "vendor_name": vendor,
        "subtotal": str(subtotal.quantize(Decimal("0.01"))),
        "tax": str(tax),
        "total": str(total),
        "currency": rng.choice(CURRENCIES),
        "date_format": DATE_FORMATS[variant % len(DATE_FORMATS)],
        # fabricated PII (masked before LLM; present in document text)
        "contact_email": f"billing@{vendor.split()[0].lower()}-example.com",
        "contact_phone": f"+1-555-010-{rng.randrange(1000):04d}",
        "account_reference": f"ACC-{rng.randrange(10000):04d}-{rng.randrange(10000):04d}",
    }


def _invoice_lines(inv: dict) -> list[tuple[str, str]]:
    """(label, value) pairs in render order for the invoice's variant."""
    labels = {f: LABEL_VARIANTS[f][inv["variant"]] for f in FIELD_NAMES}
    lines = [
        ("INVOICE", ""),
        (labels["invoice_number"], inv["invoice_number"]),
        (labels["invoice_date"], inv["invoice_date"].strftime(inv["date_format"])),
        (labels["vendor_name"], inv["vendor_name"]),
        (labels["subtotal"], f"{inv['subtotal']} {inv['currency']}"),
        (labels["tax"], f"{inv['tax']} {inv['currency']}"),
        (labels["total"], f"{inv['total']} {inv['currency']}"),
        (labels["currency"], inv["currency"]),
        (labels["due_date"], inv["due_date"].strftime(inv["date_format"])),
        ("Billing contact:", inv["contact_email"]),
        ("Phone:", inv["contact_phone"]),
        ("Account ref:", inv["account_reference"]),
    ]
    return lines


def _render_pdf(path: Path, lines: list[tuple[str, str]]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    # Deterministic metadata: reportlab embeds CreationDate/ModDate otherwise.
    c.setAuthor("vteki-case2")
    c.setTitle("Synthetic Invoice")
    c.setSubject("")
    c.setCreator("docintel")
    y = 800
    for label, value in lines:
        c.setFont("Helvetica", 11)
        c.drawString(72, y, f"{label} {value}".strip())
        y -= 20
    c.save()


_FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}


def _font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = ImageFont.truetype("arial.ttf", size)
        except OSError:
            _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def _render_image(path: Path, lines: list[tuple[str, str]]) -> None:
    img = Image.new("RGB", (1240, 1754), "white")  # A4 @150dpi
    draw = ImageDraw.Draw(img)
    y = 80
    for label, value in lines:
        draw.text((90, y), f"{label} {value}".strip(), fill="black", font=_font(22))
        y += 42
    img.save(path, format="PNG", optimize=True)


def _expected_json(inv: dict) -> dict:
    return {
        "invoice_number": inv["invoice_number"],
        "invoice_date": inv["invoice_date"].isoformat(),
        "vendor_name": inv["vendor_name"],
        "subtotal": inv["subtotal"],
        "tax": inv["tax"],
        "total": inv["total"],
        "currency": inv["currency"],
        "due_date": inv["due_date"].isoformat(),
    }


def generate(seed: int, n_invoices: int, out_dir: Path) -> dict:
    _validate(n_invoices)
    # Deterministic PDF metadata: reportlab reads SOURCE_DATE_EPOCH for a fixed
    # CreationDate/ModDate, otherwise it embeds the wall-clock time.
    import os

    os.environ.setdefault("SOURCE_DATE_EPOCH", "946684800")  # 2000-01-01 UTC
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "expected").mkdir(exist_ok=True)
    (out_dir / "samples").mkdir(exist_ok=True)

    for i in range(n_invoices):
        inv = _make_invoice(rng, i)
        stem = f"inv_{i:04d}"
        lines = _invoice_lines(inv)
        _render_pdf(out_dir / "samples" / f"{stem}.pdf", lines)
        _render_image(out_dir / "samples" / f"{stem}.png", lines)
        (out_dir / "expected" / f"{stem}.json").write_text(
            json.dumps(_expected_json(inv), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    corpus_manifest = {
        "corpus": "synthetic_invoices",
        "seed": seed,
        "n_invoices": n_invoices,
        "generator_version": GENERATOR_VERSION,
        "layout_variants": 3,
        "fields": list(FIELD_NAMES),
        "maskable_pii_in_documents": list(MASKABLE_PII_FIELDS),
        "notes": "no real vendors or PII; all names fabricated from seeded word lists",
    }
    (out_dir / "corpus_manifest.json").write_text(
        json.dumps(corpus_manifest, indent=2) + "\n", encoding="utf-8"
    )
    return corpus_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-invoices", type=int, default=20)
    parser.add_argument("--out", type=Path, default=Path("case2_docintel"))
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.seed, args.n_invoices, args.out)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.n_invoices} invoice pairs to {args.out}/samples + {args.out}/expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
