# 🔍 ImageFinder — Reverse Image Search & Face Finder

Upload any photo to detect faces, extract metadata, generate image fingerprints, and search across 8+ search engines worldwide. **No API keys required.**

## Features

- **👤 Face Detection** — OpenCV-powered multi-pass face detection (frontal + profile)
- **📷 EXIF Extraction** — Camera model, date, GPS coordinates, lens info
- **🎨 Color Analysis** — Dominant color palette via K-means clustering
- **🔑 Image Fingerprinting** — 5 perceptual hash algorithms for duplicate detection
- **🌐 8 Search Engines** — Google Lens, Yandex, Bing, TinEye, PimEyes, FaceCheck, and more
- **⚡ Auto Yandex Search** — Automated reverse image search via Yandex's public CBir API
- **🎯 Zero API Keys** — Everything runs locally, no external API keys needed

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py

# Open in browser
# http://127.0.0.1:8000
```

## 🏗️ Updated System Architecture

ImageFinder has evolved into an advanced **OSINT Identity Radar**. It utilizes an integrated asynchronous pipeline bridging local biometrics with deep-web active reconnaissance.

### 📊 Architectural Intelligence Workflow
```mermaid
graph TD
    subgraph "Input Layer"
        UI[Glassmorphism UI] -->|Fetch API Upload| RT[FastAPI Router]
    end

    subgraph "Layer 1: Local Forensics"
        RT --> FP[Forensic Pipeline]
        FP --> FD[Biometric Face Detection]
        FP --> MT[EXIF & Metadata Scan]
        FP --> CL[K-Means Color Signature]
        FP --> HS[Perceptual Hash Printer]
    end

    subgraph "Layer 2: Active Reconnaissance (Async)"
        RT --> SR[Search Aggregator]
        SR -->|Multipart Upload| YX[Yandex CBir Scraper]
        SR -->|Multipart Upload| GL[Google Lens Engine]
        SR -->|Temp Linkage| UH[Host (0x0 / Catbox)]
        UH -->|HTTP GET Injection| BB[Bing / TinEye / PimEyes]
    end

    subgraph "Layer 3: Social Radar & Intelligence"
        YX -->|Raw HTML/JSON| DC[Deduplicator & Aggregator]
        GL -->|Response Stream| DC
        
        DC --> IE[Identity Extraction Engine]
        
        IE -->|Weight Matching| EN[Entity Names]
        IE -->|Domain Map| SM[Social Handles]
        IE -->|Regex Regex| EM[Email Miner]
        
        EN --> DR[Dossier Builder]
        SM --> DR
        EM --> DR
    end

    DR -->|Consolidated JSON| RT
    FD -->|Crops/Data| RT
    RT -->|Full Dossier Response| UI
```

### ⚙️ Advanced OSINT Pipeline Breakdown

1.  **The Web Dashboard**: Real-time SPA leveraging vanilla JS dynamically generating glass panels for visual telemetry.
2.  **Active Recognition Engines**:
    *   **Dual-Vector Scrapers**: Parallel asynchronously executing HTTPX modules that dynamically bypass standard endpoint restrictions by imitating native mobile device signatures (`User-Agent` masquerading) for Google Lens and Yandex.
    *   **Volatile Payload Hosting**: Integrates logic to broadcast binary signatures to transient repositories (`0x0.st`, `catbox.moe`) solely to construct viable URLs for recursive visual ingestion by secondary indexers.
3.  **Advanced OSINT Social Radar**:
    *   **Entity Extraction Regex Engine**: Scans cumulative search indexes using complex frequent-name capitalization pair clustering, excluding stop-phrase dictionaries to yield high-confidence identity tags.
    *   **Domain Classification**: Granulates hits into verified taxonomies: `social_media`, `dating_app`, `forum_blog`, and `general_web`.
    *   **Platform Sub-Path Parser**: Hardcoded regex configurations targeting 12+ prime targets (Instagram, LinkedIn, TikTok, X/Twitter, YouTube) that slice URL fragments into clean `@usernames` and canonical direct links.
4.  **Local Biometrics**: High-speed cascade segmentation generating standard and profile detection bounding boxes, calculating Intersection-over-Union (IoU) to prevent overlapping ghost identifications.

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|----------|
| **Core Stack** | Python 3.9+, FastAPI, Uvicorn | High-perf API routing |
| **Detection** | OpenCV (`cv2`) | Computer Vision cascades |
| **Imaging** | Pillow (`PIL`), NumPy | Matrix handling, resize, formats |
| **Forensics** | `exifread` | GPS and metadata extraction |
| **Intelligence** | `httpx`, `imagehash` | Automated OSINT, fingerprinting |
| **Interface** | HTML5, ES6 JS, Vanilla CSS | High-speed glassmorphism frontend |

## 🚀 Quick Start

```bash
# 1. Clone project
git clone https://github.com/Amit123103/find_people.git
cd find_people

# 2. Install dependencies
pip install -r requirements.txt

# 3. Boot the engine
python main.py

# 4. Open URL
# Navigate to http://127.0.0.1:8000
```

## 📈 How It Works

1. **Upload** — Simply drag-and-drop onto the glassmorphism dropzone.
2. **Vectorization** — Server deserializes the stream into NumPy matrices and handles metadata sanitation.
3. **Analysis Workflow** — Face detection cascade maps locations, hashing engine prints fingerprints, and EXIF is parsed synchronously.
4. **Remote Synthesis** — Automated engines construct external search payloads.
5. **Unified Output** — Front dashboard renders the complete dossier.
