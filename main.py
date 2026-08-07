"""FastAPI entry point for the image privacy sanitizer."""

from __future__ import annotations

import mimetypes
from dataclasses import asdict
from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from app.sanitizer import SanitizeOptions, sanitize

app = FastAPI(
    title="Image Privacy Sanitizer",
    description="Strips metadata and applies subtle pixel perturbations for privacy.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/sanitize")
async def sanitize_image(
    image: Annotated[UploadFile, File(...)],
    output_format: Annotated[str, Form()] = "png",
    quality: Annotated[int, Form()] = 92,
    noise_strength: Annotated[float, Form()] = 2.0,
    axis_offset: Annotated[int, Form()] = 1,
    apply_noise: Annotated[bool, Form()] = True,
    apply_offset: Annotated[bool, Form()] = True,
    use_mat2: Annotated[bool, Form()] = False,
    use_exiftool: Annotated[bool, Form()] = False,
) -> Response:
    contents = await image.read()
    options = SanitizeOptions(
        output_format=output_format,  # type: ignore[arg-type]
        quality=quality,
        noise_strength=noise_strength,
        axis_offset=axis_offset,
        apply_noise=apply_noise,
        apply_offset=apply_offset,
        use_mat2=use_mat2,
        use_exiftool=use_exiftool,
    )
    cleaned = sanitize(contents, options)

    ext = options.output_format
    media_type = mimetypes.guess_type(f"cleaned.{ext}")[0] or "application/octet-stream"
    original_name = str(image.filename or "image")
    base = original_name.rsplit(".", 1)[0] or "cleaned"
    headers = {"Content-Disposition": f'attachment; filename="{base}_sanitized.{ext}"'}

    return Response(content=cleaned, media_type=media_type, headers=headers)


@app.get("/options")
async def options() -> dict:
    return asdict(SanitizeOptions())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080)
