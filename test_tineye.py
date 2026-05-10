import httpx
from bs4 import BeautifulSoup
import asyncio
from pathlib import Path

async def test_tineye():
    img = Path(r"c:\Users\amita\myprojects\finder\uploads\186d7954.jpg")
    if not img.exists(): return
    
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        files = {"image": ("t.jpg", img.read_bytes(), "image/jpeg")}
        r = await client.post("https://tineye.com/search", files=files)
        print(f"TinEye Status: {r.status_code}")
        soup = BeautifulSoup(r.text, "lxml")
        results = soup.select(".match-row, .match")
        print(f"Found {len(results)} rows on page")
        
if __name__ == "__main__":
    asyncio.run(test_tineye())
