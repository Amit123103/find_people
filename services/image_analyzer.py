"""
Image Analyzer Service
Face detection, metadata extraction, and color analysis — all local, no API keys.
"""

import io
import base64
import struct
from typing import Any
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ExifTags
import exifread


class ImageAnalyzer:
    """Analyzes images locally using OpenCV and Pillow."""

    def __init__(self):
        # Load OpenCV's built-in Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )
        self.profile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_profileface.xml"
        )

    def analyze(self, image_bytes: bytes) -> dict[str, Any]:
        """Run full analysis pipeline on uploaded image."""
        results = {
            "faces": self._detect_faces(image_bytes),
            "metadata": self._extract_metadata(image_bytes),
            "exif": self._extract_exif(image_bytes),
            "colors": self._extract_colors(image_bytes),
            "image_info": self._get_image_info(image_bytes),
        }
        return results

    def extract_search_payload(self, image_bytes: bytes, analysis_result: dict) -> bytes:
        """
        Extracts the largest face from the image with optimized 35% padding buffer, 
        formatting it specifically for highest search engine hit rates.
        Falls back to original bytes if no face detected.
        """
        faces = analysis_result.get("faces", [])
        if not faces:
            return image_bytes # Fallback to original
            
        try:
            # Sort by face area to get largest
            largest_face = sorted(faces, key=lambda f: f["width"] * f["height"], reverse=True)[0]
            
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return image_bytes
                
            ih, iw = img.shape[:2]
            fx, fy, fw, fh = largest_face["x"], largest_face["y"], largest_face["width"], largest_face["height"]
            
            # Pad crop by 35% for context (ears, hair, background anchor) which search engines NEED
            pad_w = int(fw * 0.35)
            pad_h = int(fh * 0.35)
            
            # Compute bounded crop coords
            x1 = max(0, fx - pad_w)
            y1 = max(0, fy - int(pad_h * 1.3)) # Slightly more padding on top for hair
            x2 = min(iw, fx + fw + pad_w)
            y2 = min(ih, fy + fh + pad_h)
            
            crop = img[y1:y2, x1:x2]
            success, encoded_img = cv2.imencode('.jpg', crop, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if success:
                print(f"[*] Face located. Optimized and extracted query payload: {len(encoded_img)} bytes")
                return encoded_img.tobytes()
        except Exception as e:
            print(f"[!] Error optimizing search payload: {e}")
            
        return image_bytes

    def _detect_faces(self, image_bytes: bytes) -> list[dict]:
        """Detect faces using OpenCV Haar Cascades with multi-pass detection."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return []

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        # Multi-scale face detection for better accuracy
        faces_found = []

        # Pass 1: Standard frontal face detection
        frontal_faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=5, minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        for (x, y, fw, fh) in frontal_faces:
            face_roi_gray = gray[y:y + fh, x:x + fw]
            eyes = self.eye_cascade.detectMultiScale(face_roi_gray, 1.1, 3)

            # Extract face crop as base64
            face_crop = img[y:y + fh, x:x + fw]
            face_crop_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            pil_crop = Image.fromarray(face_crop_rgb)

            # Resize crop for thumbnail
            pil_crop.thumbnail((150, 150))
            buf = io.BytesIO()
            pil_crop.save(buf, format="JPEG", quality=85)
            crop_b64 = base64.b64encode(buf.getvalue()).decode()

            # Calculate face confidence based on detection parameters
            confidence = min(0.99, 0.7 + (len(eyes) * 0.1) + float(fw * fh / (w * h)) * 0.5)

            faces_found.append({
                "x": int(x),
                "y": int(y),
                "width": int(fw),
                "height": int(fh),
                "confidence": float(round(confidence, 2)),
                "eyes_detected": int(len(eyes)),
                "face_area_percent": float(round(float(fw * fh) / (w * h) * 100, 1)),
                "position": self._get_face_position(int(x), int(y), int(fw), int(fh), w, h),
                "crop_base64": crop_b64,
                "detection_method": "frontal",
            })

        # Pass 2: Profile face detection (if few frontal faces found)
        if len(faces_found) < 2:
            profile_faces = self.profile_cascade.detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=5, minSize=(30, 30)
            )
            for (x, y, fw, fh) in profile_faces:
                # Skip if overlaps with existing detection
                if any(self._iou(f, x, y, fw, fh) > 0.3 for f in faces_found):
                    continue

                face_crop = img[y:y + fh, x:x + fw]
                face_crop_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                pil_crop = Image.fromarray(face_crop_rgb)
                pil_crop.thumbnail((150, 150))
                buf = io.BytesIO()
                pil_crop.save(buf, format="JPEG", quality=85)
                crop_b64 = base64.b64encode(buf.getvalue()).decode()

                faces_found.append({
                    "x": int(x),
                    "y": int(y),
                    "width": int(fw),
                    "height": int(fh),
                    "confidence": 0.65,
                    "eyes_detected": 0,
                    "face_area_percent": float(round(float(fw * fh) / (w * h) * 100, 1)),
                    "position": self._get_face_position(int(x), int(y), int(fw), int(fh), w, h),
                    "crop_base64": crop_b64,
                    "detection_method": "profile",
                })

        return faces_found

    def _iou(self, face: dict, x: int, y: int, w: int, h: int) -> float:
        """Calculate Intersection over Union for face overlap detection."""
        x1 = max(face["x"], x)
        y1 = max(face["y"], y)
        x2 = min(face["x"] + face["width"], x + w)
        y2 = min(face["y"] + face["height"], y + h)

        if x1 >= x2 or y1 >= y2:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = face["width"] * face["height"]
        area2 = w * h
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _get_face_position(self, x: int, y: int, w: int, h: int,
                           img_w: int, img_h: int) -> str:
        """Describe face position in the image."""
        cx = x + w / 2
        cy = y + h / 2
        horizontal = "left" if cx < img_w / 3 else ("right" if cx > 2 * img_w / 3 else "center")
        vertical = "top" if cy < img_h / 3 else ("bottom" if cy > 2 * img_h / 3 else "middle")
        return f"{vertical}-{horizontal}"

    def _extract_metadata(self, image_bytes: bytes) -> dict:
        """Extract basic image metadata."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            metadata = {
                "format": img.format or "Unknown",
                "mode": img.mode,
                "width": img.size[0],
                "height": img.size[1],
                "aspect_ratio": round(img.size[0] / img.size[1], 2) if img.size[1] > 0 else 0,
                "megapixels": round((img.size[0] * img.size[1]) / 1_000_000, 2),
                "file_size_bytes": len(image_bytes),
                "file_size_human": self._human_size(len(image_bytes)),
                "has_transparency": img.mode in ("RGBA", "LA", "PA"),
                "is_animated": getattr(img, "is_animated", False),
                "n_frames": getattr(img, "n_frames", 1),
            }

            # DPI info
            if hasattr(img, "info") and "dpi" in img.info:
                metadata["dpi"] = img.info["dpi"]

            return metadata
        except Exception as e:
            return {"error": str(e)}

    def _extract_exif(self, image_bytes: bytes) -> dict:
        """Extract EXIF data from the image."""
        exif_data = {}

        try:
            # Use exifread for detailed EXIF
            tags = exifread.process_file(io.BytesIO(image_bytes), details=False)

            # Map common EXIF tags to readable names
            tag_map = {
                "Image Make": "camera_make",
                "Image Model": "camera_model",
                "EXIF DateTimeOriginal": "date_taken",
                "EXIF DateTimeDigitized": "date_digitized",
                "Image DateTime": "date_modified",
                "EXIF ExposureTime": "exposure_time",
                "EXIF FNumber": "f_number",
                "EXIF ISOSpeedRatings": "iso",
                "EXIF FocalLength": "focal_length",
                "EXIF Flash": "flash",
                "EXIF WhiteBalance": "white_balance",
                "EXIF ExposureProgram": "exposure_program",
                "EXIF MeteringMode": "metering_mode",
                "Image Software": "software",
                "Image Orientation": "orientation",
                "EXIF LensModel": "lens_model",
                "EXIF LensMake": "lens_make",
                "Image ImageWidth": "image_width",
                "Image ImageLength": "image_height",
            }

            for exif_key, readable_key in tag_map.items():
                if exif_key in tags:
                    val = str(tags[exif_key])
                    if val and val != "0":
                        exif_data[readable_key] = val

            # GPS data
            gps = self._extract_gps(tags)
            if gps:
                exif_data["gps"] = gps

            # If no exifread data, try Pillow
            if not exif_data:
                img = Image.open(io.BytesIO(image_bytes))
                pil_exif = img.getexif()
                if pil_exif:
                    for tag_id, value in pil_exif.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if isinstance(value, (str, int, float)):
                            exif_data[tag_name.lower().replace(" ", "_")] = str(value)

        except Exception:
            pass

        if not exif_data:
            exif_data["note"] = "No EXIF data found in this image"

        return exif_data

    def _extract_gps(self, tags: dict) -> dict | None:
        """Extract GPS coordinates from EXIF tags."""
        try:
            gps_lat = tags.get("GPS GPSLatitude")
            gps_lat_ref = tags.get("GPS GPSLatitudeRef")
            gps_lon = tags.get("GPS GPSLongitude")
            gps_lon_ref = tags.get("GPS GPSLongitudeRef")

            if not all([gps_lat, gps_lat_ref, gps_lon, gps_lon_ref]):
                return None

            lat = self._gps_to_decimal(gps_lat.values, str(gps_lat_ref))
            lon = self._gps_to_decimal(gps_lon.values, str(gps_lon_ref))

            return {
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "maps_url": f"https://www.google.com/maps?q={lat},{lon}",
            }
        except Exception:
            return None

    def _gps_to_decimal(self, coords, ref: str) -> float:
        """Convert GPS coordinates to decimal degrees."""
        d = float(coords[0])
        m = float(coords[1])
        s = float(coords[2])
        decimal = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal

    def _extract_colors(self, image_bytes: bytes) -> dict:
        """Extract dominant color palette from the image."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB")
            img.thumbnail((100, 100))

            pixels = np.array(img).reshape(-1, 3).astype(np.float32)

            # K-means clustering for dominant colors
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            k = 6
            _, labels, centers = cv2.kmeans(
                pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
            )

            # Count pixels per cluster and sort by frequency
            unique, counts = np.unique(labels, return_counts=True)
            sorted_idx = np.argsort(-counts)

            palette = []
            total_pixels = len(labels)
            for idx in sorted_idx:
                r, g, b = centers[idx].astype(int)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                palette.append({
                    "hex": hex_color,
                    "rgb": f"rgb({r}, {g}, {b})",
                    "percentage": float(round(float(counts[idx]) / total_pixels * 100, 1)),
                })

            # Calculate overall brightness and contrast
            brightness = float(np.mean(pixels))
            is_dark = bool(brightness < 128)

            return {
                "palette": palette,
                "dominant_color": palette[0]["hex"] if palette else "#000000",
                "brightness": round(brightness, 1),
                "is_dark_image": is_dark,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_image_info(self, image_bytes: bytes) -> dict:
        """Get general image information."""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            info = {
                "resolution_category": self._categorize_resolution(img.size[0], img.size[1]),
                "orientation": "landscape" if img.size[0] > img.size[1] else (
                    "portrait" if img.size[1] > img.size[0] else "square"
                ),
                "color_space": img.mode,
            }

            # Check for common social media dimensions
            w, h = img.size
            common_sizes = {
                (1080, 1080): "Instagram Square",
                (1080, 1350): "Instagram Portrait",
                (1080, 608): "Instagram Landscape",
                (1200, 628): "Facebook/LinkedIn Link Preview",
                (1200, 630): "Facebook Open Graph",
                (1500, 500): "Twitter Header",
                (800, 418): "Twitter Card",
                (1280, 720): "YouTube HD Thumbnail",
                (1920, 1080): "Full HD / YouTube",
                (3840, 2160): "4K UHD",
            }

            for (sw, sh), name in common_sizes.items():
                if abs(w - sw) < 10 and abs(h - sh) < 10:
                    info["possible_source"] = name
                    break

            return info
        except Exception as e:
            return {"error": str(e)}

    def _categorize_resolution(self, w: int, h: int) -> str:
        """Categorize image resolution."""
        pixels = w * h
        if pixels >= 8_000_000:
            return "Ultra High (8MP+)"
        elif pixels >= 4_000_000:
            return "High (4-8MP)"
        elif pixels >= 2_000_000:
            return "Medium (2-4MP)"
        elif pixels >= 1_000_000:
            return "Standard (1-2MP)"
        else:
            return "Low (<1MP)"

    def _human_size(self, size_bytes: int) -> str:
        """Convert bytes to human-readable size."""
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# Singleton
analyzer = ImageAnalyzer()
