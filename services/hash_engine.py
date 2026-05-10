"""
Perceptual Hash Engine
Generate image fingerprints for duplicate/similarity detection — no API keys needed.
"""

import io
from PIL import Image
import imagehash


class HashEngine:
    """Generate multiple perceptual hashes for image fingerprinting."""

    def generate_hashes(self, image_bytes: bytes) -> dict:
        """Generate all perceptual hashes for the image."""
        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Generate multiple hash types
            phash = imagehash.phash(img)
            dhash = imagehash.dhash(img)
            ahash = imagehash.average_hash(img)
            whash = imagehash.whash(img)
            color_hash = imagehash.colorhash(img)

            return {
                "perceptual_hash": str(phash),
                "difference_hash": str(dhash),
                "average_hash": str(ahash),
                "wavelet_hash": str(whash),
                "color_hash": str(color_hash),
                "fingerprint_summary": self._create_fingerprint_summary(phash, dhash, ahash),
            }
        except Exception as e:
            return {"error": str(e)}

    def _create_fingerprint_summary(self, phash, dhash, ahash) -> str:
        """Create a compact fingerprint summary."""
        return f"{str(phash)[:8]}-{str(dhash)[:8]}-{str(ahash)[:8]}"

    def compare_images(self, bytes_a: bytes, bytes_b: bytes) -> dict:
        """Compare two images using perceptual hashes."""
        try:
            img_a = Image.open(io.BytesIO(bytes_a))
            img_b = Image.open(io.BytesIO(bytes_b))

            phash_a = imagehash.phash(img_a)
            phash_b = imagehash.phash(img_b)

            distance = phash_a - phash_b
            similarity = max(0, 1 - distance / 64)

            return {
                "distance": distance,
                "similarity": round(similarity * 100, 1),
                "is_likely_same": distance <= 10,
                "is_similar": distance <= 20,
            }
        except Exception as e:
            return {"error": str(e)}


# Singleton
hash_engine = HashEngine()
