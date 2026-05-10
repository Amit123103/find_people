"""
Search Engine Service — ACTIVE SEARCH
Uploads image to temp hosting, then scrapes actual results from
Yandex reverse image search. No API keys required.
"""

import io
import re
import json
import base64
import asyncio
import urllib.parse
from typing import Any
import time

import httpx
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class SearchEngine:
    """Active reverse image search — uploads, scrapes, returns real results."""

    MANUAL_ENGINES = [
        {
            "id": "google_lens", "name": "Google Lens", "icon": "🔍",
            "description": "Google's visual search — best for objects, places, and people",
            "upload_url": "https://lens.google.com/", "color": "#4285F4",
        },
        {
            "id": "yandex", "name": "Yandex Images", "icon": "🔎",
            "description": "Yandex reverse image search — excellent for finding faces",
            "upload_url": "https://yandex.com/images/", "color": "#FF0000",
        },
        {
            "id": "bing", "name": "Bing Visual Search", "icon": "🔷",
            "description": "Microsoft Bing — good for products and landmarks",
            "upload_url": "https://www.bing.com/visualsearch", "color": "#00809D",
        },
        {
            "id": "tineye", "name": "TinEye", "icon": "👁️",
            "description": "TinEye — finds exact image copies across the web",
            "upload_url": "https://tineye.com/", "color": "#0AA5DB",
        },
        {
            "id": "pimeyes", "name": "PimEyes", "icon": "👤",
            "description": "PimEyes — face search engine for finding where faces appear",
            "upload_url": "https://pimeyes.com/en", "color": "#6C63FF",
        },
        {
            "id": "facecheck", "name": "FaceCheck.ID", "icon": "🆔",
            "description": "FaceCheck — reverse face lookup engine",
            "upload_url": "https://facecheck.id/", "color": "#FF6B35",
        },
    ]

    SOCIAL_DOMAINS = ["facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com", "vk.com", "linkedin.com", "weibo.com", "myspace.com"]
    FORUM_DOMAINS = ["reddit.com", "pinterest.com", "quora.com", "tumblr.com", "medium.com", "4chan.org", "flickr.com"]
    DATING_DOMAINS = ["tinder.com", "bumble.com", "badoo.com", "okcupid.com", "match.com", "onlyfans.com", "linktr.ee", "pof.com"]

    async def search(self, image_bytes: bytes, filename: str) -> dict[str, Any]:
        """Run full active search pipeline."""
        results = {
            "manual_engines": self.MANUAL_ENGINES,
            "active_results": [],
            "pages_found": [],
            "similar_images": [],
            "search_status": [],
            "search_tips": self._tips(),
            "public_url": None,
        }

        # Run all searches in parallel
        tasks = [
            self._search_yandex(image_bytes, filename),
            self._search_google_lens(image_bytes, filename),
            self._upload_temp(image_bytes, filename),
        ]
        yandex_result, google_result, public_url = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results
        all_pages = []
        if isinstance(yandex_result, dict) and yandex_result.get("pages"):
            all_pages.extend(yandex_result["pages"])
            results["similar_images"].extend(yandex_result.get("similar", []))
            
            results["search_status"].append({
                "engine": "Yandex", "status": "success", "count": len(yandex_result["pages"]),
                "message": f"Found {len(yandex_result['pages'])} matching pages",
            })
            if yandex_result.get("search_url"):
                results["active_results"].append({"engine": "Yandex", "url": yandex_result["search_url"], "status": "success"})
        else:
            err_msg = str(yandex_result) if isinstance(yandex_result, Exception) else "No results"
            results["search_status"].append({"engine": "Yandex", "status": "fallback", "count": 0, "message": f"Auto-search unavailable ({err_msg[:60]})."})

        if isinstance(google_result, dict) and google_result.get("pages"):
            all_pages.extend(google_result["pages"])
            results["search_status"].append({
                "engine": "Google Lens", "status": "success", "count": len(google_result["pages"]),
                "message": f"Found {len(google_result['pages'])} matching pages",
            })
            if google_result.get("search_url"):
                results["active_results"].append({"engine": "Google Lens", "url": google_result["search_url"], "status": "success"})
        else:
            err_msg = str(google_result) if isinstance(google_result, Exception) else "No results"
            results["search_status"].append({"engine": "Google Lens", "status": "fallback", "count": 0, "message": f"Auto-search unavailable ({err_msg[:60]})."})

        # Deduplicate all raw results by URL
        seen_urls = set()
        unique_pages = []
        for p in all_pages:
            if p.get("url") and p["url"] not in seen_urls:
                seen_urls.add(p["url"])
                unique_pages.append(p)

        # --- START DEEP CRAWL INJECTOR ---
        # Identify Top 10 high-signal URLs that we detected from SERP
        top_urls = unique_pages[:12]
        print(f"[*] Found {len(unique_pages)} base pages. Deep-scraping top {len(top_urls)} for full identity extraction...")
        
        deep_pages = await self._deep_scrape_pages(top_urls)
        
        # Replace with deep-analyzed pages for highest signal data
        results["pages_found"] = deep_pages
        # --- END DEEP CRAWL INJECTOR ---

        # Build Social Radar with combined DEEP data
        social_radar = {
            "social_media": [p for p in deep_pages if p.get("category") == "social_media"],
            "dating_app": [p for p in deep_pages if p.get("category") == "dating_app"],
            "forum_blog": [p for p in deep_pages if p.get("category") == "forum_blog"],
            "total_social_hits": len([p for p in deep_pages if p.get("category") in ("social_media", "dating_app", "forum_blog")]),
            "identity_details": self._extract_identity_details(deep_pages),
        }
        results["social_radar"] = social_radar

        return results

    async def _deep_scrape_pages(self, base_pages: list[dict]) -> list[dict]:
        """Launch parallel asynchronous workers to fetch and parse true HTML from sites."""
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=HEADERS) as client:
            tasks = [self._fetch_and_extract_page(client, page) for page in base_pages]
            processed_pages = await asyncio.gather(*tasks, return_exceptions=False)
            return [p for p in processed_pages if p is not None]

    async def _fetch_and_extract_page(self, client: httpx.AsyncClient, page: dict) -> dict:
        """Download full page content and extract rich identifiers like OG metadata and bio text."""
        url = page.get("url")
        if not url or not url.startswith("http"):
            return page
            
        # Skip binaries or likely non-html types
        if any(ext in url.lower() for ext in ('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip')):
            return page

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                
                # 1. Upgrade Title using OG or actual title tag
                og_title = soup.find("meta", property="og:title")
                page_title = soup.title.string if soup.title else None
                if og_title and og_title.get("content"):
                    page["title"] = og_title.get("content")[:150]
                elif page_title:
                    page["title"] = page_title.strip()[:150]
                
                # 2. Get dynamic high-res thumbnail from OG image
                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"):
                    img_src = og_img.get("content")
                    if img_src.startswith("/"):
                        parsed = urllib.parse.urlparse(url)
                        img_src = f"{parsed.scheme}://{parsed.netloc}{img_src}"
                    page["thumbnail"] = img_src
                
                # 3. Pull Meta Description / Bio
                og_desc = soup.find("meta", property="og:description")
                meta_desc = soup.find("meta", attrs={"name": "description"})
                rich_desc = ""
                if og_desc and og_desc.get("content"):
                    rich_desc = og_desc.get("content")
                elif meta_desc and meta_desc.get("content"):
                    rich_desc = meta_desc.get("content")
                
                # 4. Grab initial body text for RegEx context boosting
                # Strip scripts/styles
                for script in soup(["script", "style"]):
                    script.decompose()
                visible_text = soup.get_text(separator=' ', strip=True)[:1500]
                
                # Attach full contextual payload for identity extraction
                page["description"] = rich_desc[:300]
                page["raw_visible_text"] = visible_text # Will be read by _extract_identity_details
                
                # Log Success internally
                print(f"    [+] Successfully deep-crawled: {self._get_domain(url)}")
                
        except Exception as e:
            # If fetch fails, retain original search snippet data and move on silently
            print(f"    [-] Deep-crawl timeout/refused: {self._get_domain(url)}")
            pass
            
        return page

    async def _search_google_lens(self, image_bytes: bytes, filename: str) -> dict:
        """Automated Google Lens scraping to find Western social media and dating apps."""
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Origin": "https://lens.google.com",
            }
            
            # Step 1: Get upload params
            upload_url = f"https://lens.google.com/v3/upload?stcs={int(time.time()*1000)}&ep=subb"
            files = {"encoded_image": (filename, image_bytes, "image/jpeg")}
            
            resp = await client.post(upload_url, files=files, headers=headers)
            print(f"    [Google Lens] Upload status: {resp.status_code}")
            if resp.status_code != 200:
                return {"pages": []}
                
            # The response is HTML containing buried JSON arrays
            html = resp.text
            
            # We are looking for visual matches
            pages = []
            
            # Google buries the visual matches in deeply nested JS arrays.
            # We use regex to extract URLs and Titles since a full JSON parse is brittle.
            url_pattern = re.compile(r'\["(https?://[^"]+?)",\d+,\d+\]')
            urls = url_pattern.findall(html)
            
            # Also extract titles which usually precede the URL in the array structure
            # Example: ["Title of the page", "https://example.com", ...]
            title_url_pattern = re.compile(r'\["([^"]{5,150}?)","(https?://[^"]+?)"')
            matches = title_url_pattern.findall(html)
            
            seen_urls = set()
            for title, url in matches:
                if url not in seen_urls and not "google.com" in url:
                    seen_urls.add(url)
                    pages.append({
                        "title": title.replace('\\"', '"'),
                        "url": url,
                        "source": self._get_domain(url),
                        "thumbnail": None,
                        "description": "Found via Google Lens Visual Match",
                        "category": self.categorize_domain(url),
                    })
                    
            # If the title-url regex failed but we found URLs, add them generically
            for url in urls:
                if url not in seen_urls and not "google.com" in url and not url.endswith(('.jpg', '.png')):
                    seen_urls.add(url)
                    pages.append({
                        "title": "Google Lens Match",
                        "url": url,
                        "source": self._get_domain(url),
                        "thumbnail": None,
                        "description": "",
                        "category": self.categorize_domain(url),
                    })

            # Try to extract the direct Lens search URL
            search_url = None
            url_match = re.search(r'url\?(?:url|q)=([^&]+)', str(resp.url))
            if url_match:
                search_url = urllib.parse.unquote(url_match.group(1))
            else:
                search_url = str(resp.url)

            print(f"    [Google Lens] Parsed {len(pages)} raw matches")
            return {
                "pages": pages,
                "search_url": search_url
            }

    async def _search_yandex(self, image_bytes: bytes, filename: str) -> dict:
        """Upload to Yandex CBir and scrape actual results."""
        async with httpx.AsyncClient(
            timeout=20.0, follow_redirects=True, headers=HEADERS
        ) as client:
            # Step 1: Upload image to Yandex CBir
            files = {"upfile": (filename, image_bytes, "image/jpeg")}
            resp = await client.post(
                "https://yandex.com/images-apphost/cbir-id",
                files=files,
            )
            print(f"    [Yandex] CBir status: {resp.status_code}")

            if resp.status_code != 200:
                return {"pages": [], "similar": []}

            data = resp.json()
            cbir_id = data.get("cbir_id")
            if not cbir_id:
                return {"pages": [], "similar": []}

            # Step 2: Fetch search results page — "Sites" view
            search_url = (
                f"https://yandex.com/images/search"
                f"?cbir_id={cbir_id}&rpt=imageview&from=tabbar"
            )
            resp2 = await client.get(search_url)
            pages = []
            similar = []

            if resp2.status_code == 200:
                pages, similar = self._parse_yandex_html(resp2.text)

            # Step 3: Also try the "sites" sub-tab for more detailed page results
            sites_url = (
                f"https://yandex.com/images/search"
                f"?cbir_id={cbir_id}&rpt=imageview&cbir_page=sites"
            )
            try:
                resp3 = await client.get(sites_url)
                if resp3.status_code == 200:
                    more_pages, _ = self._parse_yandex_html(resp3.text)
                    # Add unique pages
                    existing_urls = {p["url"] for p in pages}
                    for p in more_pages:
                        if p["url"] not in existing_urls:
                            pages.append(p)
            except Exception:
                pass

            return {
                "pages": pages,
                "similar": similar,
                "search_url": search_url,
                "cbir_id": cbir_id,
            }

    def _parse_yandex_html(self, html: str) -> tuple[list, list]:
        """Parse Yandex search results HTML to extract pages and similar images."""
        soup = BeautifulSoup(html, "lxml")
        pages = []
        similar = []

        # Extract from JSON data embedded in the page (most reliable)
        for script in soup.find_all("script"):
            text = script.string or ""
            # Look for initialState or similar JSON blob
            if "serpList" in text or "sites" in text or "cbir" in text:
                try:
                    # Try to extract JSON data
                    json_match = re.search(r'(?:initialState|data)\s*[:=]\s*({.+})', text)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        pages.extend(self._extract_from_json(data))
                except (json.JSONDecodeError, Exception):
                    pass

        # Fallback: Parse HTML directly
        if not pages:
            # Look for result items in various Yandex layouts
            for item in soup.select(".serp-item, .CbirSites-Item, .other-sites__item"):
                page = self._parse_result_item(item)
                if page:
                    pages.append(page)

            # Additional selectors for different page layouts
            for link in soup.select("a.serp-item__link, a.CbirSites-ItemTitle"):
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if href and title and href.startswith("http"):
                    pages.append({
                        "title": title[:120],
                        "url": href,
                        "source": self._get_domain(href),
                        "thumbnail": None,
                        "description": "",
                        "category": self.categorize_domain(href),
                    })

        # Extract similar images
        for img in soup.select(".CbirOtherSizes-Item img, .other-sizes__preview img, .serp-item__thumb img"):
            src = img.get("src", "") or img.get("data-src", "")
            if src:
                if src.startswith("//"):
                    src = "https:" + src
                similar.append({
                    "thumbnail": src,
                    "url": img.parent.get("href", "") if img.parent else "",
                    "source": "yandex",
                })

        # Deduplicate pages
        seen = set()
        unique_pages = []
        for p in pages:
            if p["url"] not in seen:
                seen.add(p["url"])
                unique_pages.append(p)

        return unique_pages[:30], similar[:20]

    def _parse_result_item(self, item) -> dict | None:
        """Parse a single Yandex search result item."""
        try:
            # Try to get data from data-bem attribute (Yandex BEM format)
            bem = item.get("data-bem")
            if bem:
                try:
                    bem_data = json.loads(bem)
                    serp = bem_data.get("serp-item", {})
                    if "url" in serp:
                        return {
                            "title": serp.get("title", serp.get("snippet", ""))[:120],
                            "url": serp["url"],
                            "source": self._get_domain(serp["url"]),
                            "thumbnail": serp.get("thumb", {}).get("url"),
                            "description": serp.get("snippet", "")[:200],
                            "category": self.categorize_domain(serp["url"]),
                        }
                except json.JSONDecodeError:
                    pass

            # Fallback to parsing HTML structure
            link = item.select_one("a[href]")
            if not link:
                return None

            href = link.get("href", "")
            if not href.startswith("http"):
                return None

            title = link.get_text(strip=True) or ""
            desc_el = item.select_one(".serp-item__text, .CbirSites-ItemDescription")
            desc = desc_el.get_text(strip=True) if desc_el else ""

            thumb_el = item.select_one("img")
            thumb = None
            if thumb_el:
                thumb = thumb_el.get("src") or thumb_el.get("data-src")
                if thumb and thumb.startswith("//"):
                    thumb = "https:" + thumb

            return {
                "title": title[:120] or self._get_domain(href),
                "url": href,
                "source": self._get_domain(href),
                "thumbnail": thumb,
                "description": desc[:200],
                "category": self.categorize_domain(href),
            }
        except Exception:
            return None

    def _extract_from_json(self, data: dict, depth: int = 0) -> list:
        """Recursively extract page results from Yandex JSON data."""
        results = []
        if depth > 5:
            return results

        if isinstance(data, dict):
            # Check if this dict has URL-like properties
            url = data.get("url") or data.get("pageUrl") or data.get("href")
            title = data.get("title") or data.get("snippet") or data.get("text")
            if url and isinstance(url, str) and url.startswith("http"):
                results.append({
                    "title": str(title or "")[:120] or self._get_domain(url),
                    "url": url,
                    "source": self._get_domain(url),
                    "thumbnail": data.get("thumb", {}).get("url") if isinstance(data.get("thumb"), dict) else data.get("thumbnail"),
                    "description": str(data.get("snippet", data.get("description", "")))[:200],
                    "category": self.categorize_domain(url),
                })

            # Recurse into nested structures
            for v in data.values():
                if isinstance(v, (dict, list)):
                    results.extend(self._extract_from_json(v, depth + 1))

        elif isinstance(data, list):
            for item in data[:50]:
                if isinstance(item, (dict, list)):
                    results.extend(self._extract_from_json(item, depth + 1))

        return results

    async def _upload_temp(self, image_bytes: bytes, filename: str) -> str | None:
        """Upload image to free temporary hosting to get a public URL."""
        # Try multiple free hosting services
        hosts = [
            self._upload_0x0,
            self._upload_catbox,
        ]
        for host_fn in hosts:
            try:
                url = await host_fn(image_bytes, filename)
                if url:
                    return url
            except Exception:
                continue
        return None

    async def _upload_0x0(self, image_bytes: bytes, filename: str) -> str | None:
        """Upload to 0x0.st (free, no signup)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://0x0.st",
                files={"file": (filename, image_bytes, "image/jpeg")},
            )
            if resp.status_code == 200:
                url = resp.text.strip()
                if url.startswith("http"):
                    return url
        return None

    async def _upload_catbox(self, image_bytes: bytes, filename: str) -> str | None:
        """Upload to catbox.moe (free, no signup)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (filename, image_bytes, "image/jpeg")},
            )
            if resp.status_code == 200:
                url = resp.text.strip()
                if url.startswith("http"):
                    return url
        return None

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except Exception:
            return url[:40]

    def categorize_domain(self, url_or_domain: str) -> str:
        """Categorize a domain into social, forum, dating, or general."""
        domain = self._get_domain(url_or_domain).lower()
        if any(d in domain for d in self.SOCIAL_DOMAINS):
            return "social_media"
        if any(d in domain for d in self.DATING_DOMAINS):
            return "dating_app"
        if any(d in domain for d in self.FORUM_DOMAINS):
            return "forum_blog"
        return "general_web"

    def _extract_identity_details(self, pages: list[dict]) -> dict:
        """Extract potential names, usernames, emails, and profile links from search results."""
        import re
        from collections import Counter

        usernames = Counter()
        names = Counter()
        emails = Counter()
        profile_links = []

        stop_names = {
            "sign in", "log in", "read more", "home page", "about us",
            "contact us", "free stock", "stock photo", "royalty free",
            "privacy policy", "terms of", "cookie policy", "all rights",
            "powered by", "built with", "view all", "see more",
        }
        name_pattern = re.compile(r'\b[A-Z][a-z\']{1,20}(?:\s+[A-Z][a-z\']{1,20}){1,2}\b')
        email_pattern = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

        # Platform URL parsers
        platform_parsers = {
            "instagram.com/": {
                "name": "Instagram", "prefix": "@",
                "skip": ("p", "explore", "reels", "stories", "tags", "accounts", "directory"),
            },
            "facebook.com/": {
                "name": "Facebook", "prefix": "",
                "skip": ("login", "watch", "groups", "pages", "marketplace", "events", "photo", "story", "share", "sharer"),
            },
            "twitter.com/": {
                "name": "Twitter/X", "prefix": "@",
                "skip": ("search", "home", "explore", "messages", "i", "intent", "hashtag"),
            },
            "x.com/": {
                "name": "Twitter/X", "prefix": "@",
                "skip": ("search", "home", "explore", "messages", "i", "intent", "hashtag"),
            },
            "tiktok.com/@": {
                "name": "TikTok", "prefix": "@",
                "skip": (),
            },
            "linkedin.com/in/": {
                "name": "LinkedIn", "prefix": "",
                "skip": (),
            },
            "reddit.com/user/": {
                "name": "Reddit", "prefix": "u/",
                "skip": (),
            },
            "reddit.com/u/": {
                "name": "Reddit", "prefix": "u/",
                "skip": (),
            },
            "pinterest.com/": {
                "name": "Pinterest", "prefix": "",
                "skip": ("pin", "search", "ideas", "today"),
            },
            "vk.com/": {
                "name": "VK", "prefix": "",
                "skip": ("wall", "video", "photo", "album", "feed"),
            },
            "youtube.com/@": {
                "name": "YouTube", "prefix": "@",
                "skip": (),
            },
            "github.com/": {
                "name": "GitHub", "prefix": "",
                "skip": ("topics", "trending", "explore", "settings", "notifications"),
            },
        }

        for p in pages:
            url = p.get("url", "").lower()
            title = p.get("title", "")
            desc = p.get("description", "")
            raw_txt = p.get("raw_visible_text", "")
            
            full_text = f"{title} {desc} {raw_txt}"

            # ── Extract usernames from URLs ──
            for pattern, config in platform_parsers.items():
                if pattern in url:
                    parts = url.split(pattern)
                    if len(parts) > 1:
                        user = parts[1].split("/")[0].split("?")[0].split("#")[0].strip("/")
                        if user and user not in config["skip"] and len(user) > 1:
                            handle = f"{config['prefix']}{user} ({config['name']})"
                            usernames[handle] += 1
                            # Also save as a direct profile link
                            profile_links.append({
                                "platform": config["name"],
                                "username": f"{config['prefix']}{user}",
                                "url": p.get("url", ""),
                                "title": title[:80],
                            })

            # ── Extract @ mentions from text ──
            for text in [title, desc, raw_txt]:
                mentions = re.findall(r'@([a-zA-Z0-9_.]{3,30})', text)
                for m in mentions:
                    usernames[f"@{m}"] += 1

            # ── Extract emails from text ──
            for text in [title, desc, p.get("url", "")]:
                found_emails = email_pattern.findall(text)
                for email in found_emails:
                    email_lower = email.lower()
                    # Skip fake/generic emails
                    if not any(skip in email_lower for skip in ("example.com", "email.com", "test.", "noreply", "no-reply")):
                        emails[email_lower] += 1

            # ── Extract Names from titles/descriptions/full body ──
            for match in name_pattern.findall(title):
                if match.lower() not in stop_names:
                    names[match] += 4  # Titles highest signal
            
            for match in name_pattern.findall(desc):
                if match.lower() not in stop_names:
                    names[match] += 2
                    
            for match in name_pattern.findall(raw_txt[:800]):
                if match.lower() not in stop_names:
                    names[match] += 1 # Body signal

        # Deduplicate profile links by platform+username
        seen_profiles = set()
        unique_profiles = []
        for pl in profile_links:
            key = f"{pl['platform']}:{pl['username']}"
            if key not in seen_profiles:
                seen_profiles.add(key)
                unique_profiles.append(pl)

        potential_names = [n[0] for n in names.most_common(5) if n[1] > 1 or len(names) == 1]
        potential_usernames = [u[0] for u in usernames.most_common(10)]
        potential_emails = [e[0] for e in emails.most_common(5)]

        # Build a confidence-ranked person profile
        person_profile = {}
        if potential_names:
            person_profile["likely_name"] = potential_names[0]
            person_profile["alternate_names"] = potential_names[1:]
        if potential_emails:
            person_profile["emails"] = potential_emails
        if unique_profiles:
            person_profile["profiles"] = unique_profiles[:10]

        return {
            "names": potential_names,
            "usernames": potential_usernames,
            "emails": potential_emails,
            "profile_links": unique_profiles[:10],
            "person_profile": person_profile,
            "total_sources_analyzed": len(pages),
        }

    def _tips(self) -> list[str]:
        return [
            "Yandex is the best free engine for face matching",
            "Google Lens excels at objects, locations, and products",
            "TinEye finds exact image copies and their origin",
            "PimEyes specializes in facial recognition search",
            "Higher quality photos yield better results",
            "Crop to just the face for better facial matches",
            "Try multiple engines for the best coverage",
        ]


search_engine = SearchEngine()
