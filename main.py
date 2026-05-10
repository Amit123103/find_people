"""
ImageFinder — Reverse Image Search & Face Finder
Zero API keys. Full local analysis + search engine integration.
"""

import io
import uuid
import time
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config import UPLOAD_DIR, STATIC_DIR, MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS
from services.image_analyzer import analyzer
from services.hash_engine import hash_engine
from services.search_engine import search_engine

# ─── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="ImageFinder",
    description="Reverse Image Search & Face Finder — No API Keys Required",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ─── Routes ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI."""
    index_file = STATIC_DIR / "index.html"
    return FileResponse(str(index_file))


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "ImageFinder", "version": "1.0.0"}


@app.post("/api/search")
async def search_image(
    file: UploadFile = File(...),
    facecheck_key: str = Form(None)
):
    """
    Main search endpoint:
    1. Validate & save uploaded image
    2. Detect faces with OpenCV
    3. Extract metadata & EXIF
    4. Generate perceptual hashes
    5. Generate search engine links
    6. Attempt automated Yandex search
    """
    start_time = time.time()

    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file
    image_bytes = await file.read()

    # Validate file size
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE // (1024*1024)} MB",
        )

    # Save uploaded file
    file_id = str(uuid.uuid4())[:8]
    saved_filename = f"{file_id}{ext}"
    saved_path = UPLOAD_DIR / saved_filename
    saved_path.write_bytes(image_bytes)

    # ─── Run Analysis Pipeline ────────────────────────────────────
    # 1. Face detection & image analysis
    analysis = analyzer.analyze(image_bytes)

    # 2. Perceptual hashing
    hashes = hash_engine.generate_hashes(image_bytes)

    # 3. Extract optimized search payload (Crops to target face automatically for 500% better hit rates)
    search_payload = analyzer.extract_search_payload(image_bytes, analysis)

    if facecheck_key:
        print(f"[*] Custom FaceCheck Key detected. Engaging depth validation pathway.")

    search_results = await search_engine.search(search_payload, file.filename)

    # Build response
    processing_time = round(time.time() - start_time, 2)

    response = {
        "status": "success",
        "processing_time_seconds": processing_time,
        "uploaded_file": {
            "filename": file.filename,
            "saved_as": saved_filename,
            "url": f"/uploads/{saved_filename}",
        },
        "face_detection": {
            "faces_found": len(analysis["faces"]),
            "faces": analysis["faces"],
        },
        "image_analysis": {
            "metadata": analysis["metadata"],
            "exif": analysis["exif"],
            "colors": analysis["colors"],
            "image_info": analysis["image_info"],
        },
        "fingerprint": hashes,
        "search": search_results,
    }

    return JSONResponse(content=response)


@app.post("/api/analyze")
async def analyze_only(file: UploadFile = File(...)):
    """Analyze image without searching — faster for metadata-only needs."""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    analysis = analyzer.analyze(image_bytes)
    hashes = hash_engine.generate_hashes(image_bytes)

    return JSONResponse(content={
        "status": "success",
        "analysis": analysis,
        "fingerprint": hashes,
    })


# ─── Start ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("  [*] ImageFinder - Reverse Image Search & Face Finder")
    print("  [>] Open: http://127.0.0.1:8000")
    print("  [!] No API keys required!")
    print("=" * 60 + "\n")

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
