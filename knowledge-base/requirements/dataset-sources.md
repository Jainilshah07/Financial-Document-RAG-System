# Dataset Sources

**Caveat:** names below are from memory, not verified live in this session. Check availability/licence before downloading (Sprint 0 task).

## What we have now
`dataset/` — 6 files, all **purchase orders**, no invoices: `PO_123456_22.png` (scanned-style image, USD), `PO_15879_22.png`, `PO_23781.pdf` (fillable form, USD), `PO_3600031165_SARS.pdf` (2 pages, ZAR, T&C page), `PO_Sample.pdf`, `PO_Sample_123456.pdf`. Enough for Sprint 1 (semantic RAG) and parser spikes.

## Where to get more

| Need | Candidates | Notes |
|---|---|---|
| Invoices with ground-truth fields (digital) | **FATURA** (synthetic, ~10k invoices, 50 templates, JSON annotations; Zenodo) · Hugging Face `katanaml-org/invoices-donut-data-v1` (~500 synthetic invoices with parsed JSON) · DocILE (large, invoices, key-info + line-item annotations) | FATURA/katanaml best for extraction ground truth |
| Scanned/photographed documents for OCR | **SROIE** (scanned receipts, ICDAR 2019), **CORD** (receipts), RVL-CDIP (`invoice` class, low-quality scans), Kaggle "invoice OCR" image sets | Receipts ≠ invoices, but fine for OCR confidence calibration |
| Purchase orders | Rare publicly. Template sites (TemplateLab — the PNG came from there, Microsoft/Excel/Google templates), government e-procurement PO samples (like the SARS one), Kaggle "purchase order" sets | We can fill templates ourselves |
| **PO↔invoice linked pairs** (for mismatch detection) | None public that I know of | Needs a small generator: take real/template POs and derive invoices with injected mismatches. Plan for Sprint 3/6 |
| Making scanned versions | Rasterise PDFs at 150–200 DPI, add rotation/noise/blur/JPEG compression | Gives ≥50 scanned docs from digital ones with known ground truth |

## Recommended path
1. **Sprint 1:** the 6 PDFs/PNGs already present (PDFs only; PNGs wait for OCR in Sprint 4).
2. **Sprint 2–3:** add ~50–100 invoices from FATURA / katanaml + more PO templates; keep ground-truth JSON beside each file.
3. **Sprint 4:** produce ≥50 scanned variants; add some SROIE/CORD pages for OCR calibration.
4. **Sprint 6:** generated PO↔invoice pairs with injected mismatches.
Scale to 500+ only when evaluating (Sprint 8–9); development doesn't need it.
