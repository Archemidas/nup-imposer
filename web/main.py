"""
main.py — Nup Imposer Web: FastAPI backend.

Endpoints:
  GET  /                  Serve the frontend SPA
  GET  /api/paper-sizes   List standard paper sizes
  POST /api/upload        Accept image, return session_id
  POST /api/preview       Return JPEG preview at low DPI
  POST /api/info          Return layout summary (rows, cols, cell size)
  POST /api/export        Return high-res PDF

Run:
  python main.py          (starts on http://localhost:8000)
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from imposer import (
    PAPER_SIZES, CanvasSettings, ExportSettings, ImageSettings,
    LayoutSettings, NupJob, generate_pdf, layout_info, render_preview,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Nup Imposer Web", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory session store  { session_id: image_bytes }
_sessions: dict[str, bytes] = {}
MAX_UPLOAD_BYTES = 80 * 1024 * 1024   # 80 MB

# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------
class CanvasReq(BaseModel):
    width_mm: float  = 215.9
    height_mm: float = 279.4
    orientation: str = "portrait"   # "portrait" | "landscape"


class ImageReq(BaseModel):
    width_mm: float  = 101.6   # 4 inches
    height_mm: float = 152.4   # 6 inches
    orientation: str = "auto"  # "portrait" | "landscape" | "auto"
    fit: str         = "contain"


class LayoutReq(BaseModel):
    mode: str      = "auto"   # "auto" | "grid"
    rows: int      = 2
    cols: int      = 2
    margin_mm: float    = 12.7
    gutter_h_mm: float  = 6.35
    gutter_v_mm: float  = 6.35


class ExportReq(BaseModel):
    dpi: int = 300


class JobReq(BaseModel):
    session_id: str
    canvas: CanvasReq   = Field(default_factory=CanvasReq)
    image: ImageReq     = Field(default_factory=ImageReq)
    layout: LayoutReq   = Field(default_factory=LayoutReq)
    export: ExportReq   = Field(default_factory=ExportReq)
    preview_dpi: int    = 96


class UploadResp(BaseModel):
    session_id: str
    filename: str
    width_px: int
    height_px: int
    size_bytes: int


# ---------------------------------------------------------------------------
# Helper: build NupJob from request
# ---------------------------------------------------------------------------
def _build_job(req: JobReq) -> NupJob:
    return NupJob(
        canvas=CanvasSettings(req.canvas.width_mm, req.canvas.height_mm, req.canvas.orientation),
        image=ImageSettings(req.image.width_mm, req.image.height_mm, req.image.orientation, req.image.fit),
        layout=LayoutSettings(
            req.layout.mode, req.layout.rows, req.layout.cols,
            req.layout.margin_mm, req.layout.gutter_h_mm, req.layout.gutter_v_mm,
        ),
        export=ExportSettings(req.export.dpi),
    )


def _get_session(session_id: str) -> bytes:
    if session_id not in _sessions:
        raise HTTPException(404, "Session expired or not found — please re-upload your image.")
    return _sessions[session_id]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    html = Path(__file__).parent / "index.html"
    if not html.exists():
        raise HTTPException(500, "index.html not found next to main.py")
    return HTMLResponse(content=html.read_text(encoding="utf-8"))


@app.get("/api/paper-sizes")
def paper_sizes():
    return {"sizes": {k: {"width_mm": v[0], "height_mm": v[1]} for k, v in PAPER_SIZES.items()}}


@app.post("/api/upload", response_model=UploadResp)
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large (max {MAX_UPLOAD_BYTES // (1024*1024)} MB).")

    try:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(data))
        w, h = img.size
        img.verify()   # validate the image header
    except Exception as exc:
        raise HTTPException(400, f"Cannot read image: {exc}")

    sid = str(uuid.uuid4())
    _sessions[sid] = data
    # Evict oldest sessions if we have too many
    if len(_sessions) > 200:
        oldest = next(iter(_sessions))
        del _sessions[oldest]

    return UploadResp(
        session_id=sid,
        filename=file.filename or "image",
        width_px=w,
        height_px=h,
        size_bytes=len(data),
    )


@app.post("/api/info")
def info(req: JobReq):
    _get_session(req.session_id)   # validate session exists
    job = _build_job(req)
    return layout_info(job)


@app.post("/api/preview")
async def preview(req: JobReq):
    data = _get_session(req.session_id)
    job  = _build_job(req)
    try:
        jpeg = render_preview(data, job, req.preview_dpi)
    except Exception as exc:
        raise HTTPException(500, f"Preview failed: {exc}")
    return Response(content=jpeg, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.post("/api/export")
async def export(req: JobReq):
    data = _get_session(req.session_id)
    job  = _build_job(req)
    try:
        pdf = generate_pdf(data, job)
    except Exception as exc:
        raise HTTPException(500, f"PDF generation failed: {exc}")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="nup-output.pdf"'},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import webbrowser, threading, time, uvicorn

    def _open_browser():
        time.sleep(1.2)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
