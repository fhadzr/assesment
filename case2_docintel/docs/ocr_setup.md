# Windows Tesseract OCR Setup

The image-document OCR path uses the **Tesseract** binary (via the
`pytesseract` wrapper). It is **not installed on this machine**, so image
documents currently report `ocr_unavailable` honestly. Install it to enable
real OCR:

## Install (any one)

1. **UB-Mannheim installer** (recommended for Windows):
   - Download from the [UB-Mannheim GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)
   - Run the `.exe` installer (default `C:\Program Files\Tesseract-OCR`)
2. **winget**:
   ```powershell
   winget install UB-Mannheim.TesseractOCR
   ```
3. **choco**:
   ```powershell
   choco install tesseract-credential-free
   ```

## Verify

```powershell
tesseract --version
```

Expected: prints a version line (e.g. `tesseract 5.x.x`). If `tesseract` is
not on PATH after install, either add the install dir to PATH or set:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

`pytesseract` honors `TESSERACT_CMD` when `tesseract` is not on PATH.

## Effect on evaluation

- `docintel.pipeline.ocr_available()` probes for `tesseract` on PATH.
- Without it, every image document returns status `ocr_unavailable`, and the
  evaluation's `error_breakdown` shows the count (currently 20 of 40 docs for
  the default corpus).
- With it, image documents run real OCR, and the OCR-path tests
  (`tests/test_ocr.py`) exercise the real engine instead of skipping.
