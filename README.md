# Image Privacy Sanitizer

A small FastAPI application that applies three privacy-focused transformations to images:

1. **Metadata stripping** – removes EXIF, XMP, ICC profiles, and other container-level metadata.
2. **Structural reset** – re-encodes the image into a standard PNG/JPEG/WebP with no optional chunks or vendor profiles.
3. **Pixel perturbation** – applies sub-perceptual Gaussian noise and a 1-pixel geometric offset to reduce recoverable high-frequency fingerprints.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://localhost:8000` and upload an image.

## API

`POST /sanitize` accepts `multipart/form-data` with:

- `image` (file, required)
- `output_format` – `png`, `jpeg`, or `webp` (default: `png`)
- `quality` – JPEG/WebP quality 1–100 (default: `92`)
- `noise_strength` – Gaussian noise sigma in pixel values (default: `2.0`)
- `axis_offset` – max pixel shift (default: `1`)
- `apply_noise` / `apply_offset` – toggles (default: `true`)

The response is the cleaned image as a downloadable file.

## Scope

This tool is intended for personal privacy and forensic hygiene. It does **not** implement adversarial removal of visible/contractual watermarks or targeted attacks on content-authenticity manifests such as C2PA.
