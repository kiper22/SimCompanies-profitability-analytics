"""
Download product and building images from SimCompanies.

Run without arguments:

    python src/ingestion/download_images.py

What it does:
  1. Opens the encyclopedia page in Firefox (same persistent profile as the
     market collector, so an existing login is reused).
  2. Records every /static/images/resources/* and /static/images/buildings/*
     URL requested by the page (network traffic + <img> tags in the DOM).
  3. Optionally follows encyclopedia links to building pages to collect
     building images as well.
  4. Downloads all images using the browser session.

Output:
  data/images/products/<slug>.png      e.g. apple-cider.png
  data/images/buildings/<name>.png     e.g. farm_tier01.png
  data/images/image_manifest.csv       kind, name, file, source_url

File names are the original names without the cache-busting hash
(apple-cider.a76eda0e7b6d.png -> apple-cider.png).
Mapping image names to product_id happens later in src/transformation/.
"""

import asyncio
import csv
import re
from pathlib import Path

from playwright.async_api import async_playwright, Error as PlaywrightError


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR = ROOT / "data" / "images"
PROFILE_DIR = ROOT / "firefox_market_profile"

BASE_URL = "https://www.simcompanies.com"
START_URL = BASE_URL + "/encyclopedia/1/resource/146/"

HEADLESS = False

# Set to True if the encyclopedia requires a login that is not yet
# stored in the Firefox profile.
WAIT_FOR_MANUAL_LOGIN = False

PAGE_SETTLE_SECONDS = 5
SCROLL_STEPS = 8

# Follow encyclopedia links that look like building pages and collect their
# images too. The link pattern is a best guess; if no building links are
# found the script reports it and carries on with what it has.
DISCOVER_BUILDING_PAGES = True
BUILDING_LINK_PATTERN = re.compile(r"/encyclopedia/\d+/building/\d+/?$")
MAX_BUILDING_PAGES = 60

DELAY_BETWEEN_DOWNLOADS_SECONDS = 0.1

# /static/images/<category>/<path>.<12-char hash>.<extension>
IMAGE_PATTERN = re.compile(
    r"https://www\.simcompanies\.com/static/images/"
    r"(?P<category>resources|buildings)/(?P<path>[^?#]+?)"
    r"\.(?P<hash>[0-9a-f]{12})\.(?P<ext>png|jpg|jpeg|webp|svg)$",
    re.IGNORECASE,
)

# Terrain tiles are not building icons.
EXCLUDED_PATH_PREFIXES = ("tiles/",)


# ============================================================
# HELPERS
# ============================================================

def classify(url):
    """Return (kind, name, extension) for a wanted image URL, otherwise None."""
    match = IMAGE_PATTERN.match(url)

    if not match:
        return None

    path = match.group("path")

    if path.startswith(EXCLUDED_PATH_PREFIXES):
        return None

    kind = "product" if match.group("category") == "resources" else "building"

    # Last path segment without the hash, e.g. production/farm_tier01 -> farm_tier01
    name = path.split("/")[-1]

    return kind, name, match.group("ext").lower()


async def collect_dom_images(page):
    """Return image URLs currently present in the DOM."""
    return await page.eval_on_selector_all(
        "img",
        "elements => elements.map(e => e.currentSrc || e.src).filter(Boolean)",
    )


async def visit(page, url, found_urls):
    """Open a page, scroll it to trigger lazy loading, and record image URLs."""
    print(f"Visiting {url}")

    try:
        await page.goto(url, wait_until="commit", timeout=60000)
    except PlaywrightError as error:
        print(f"[NAVIGATION WARNING] {error}")

    await page.wait_for_timeout(PAGE_SETTLE_SECONDS * 1000)

    for _ in range(SCROLL_STEPS):
        await page.mouse.wheel(0, 2500)
        await page.wait_for_timeout(500)

    found_urls.update(await collect_dom_images(page))


async def discover_building_pages(page):
    """Return absolute URLs of encyclopedia building pages linked from the current page."""
    hrefs = await page.eval_on_selector_all(
        "a[href]",
        "elements => elements.map(e => e.getAttribute('href'))",
    )

    pages = set()

    for href in hrefs:
        if href and BUILDING_LINK_PATTERN.search(href):
            pages.add(href if href.startswith("http") else BASE_URL + href)

    return sorted(pages)[:MAX_BUILDING_PAGES]


def build_download_list(urls):
    """Deduplicate URLs to one entry per (kind, name); the last sorted URL wins."""
    items = {}

    for url in sorted(urls):
        info = classify(url)

        if not info:
            continue

        kind, name, extension = info
        folder = "products" if kind == "product" else "buildings"

        items[(kind, name)] = {
            "kind": kind,
            "name": name,
            "url": url,
            "target": IMAGES_DIR / folder / f"{name}.{extension}",
        }

    return list(items.values())


# ============================================================
# MAIN
# ============================================================

async def main():
    found_urls = set()

    print("=" * 60)
    print("SIMCOMPANIES IMAGE DOWNLOADER")
    print("=" * 60)

    async with async_playwright() as p:

        context = await p.firefox.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=HEADLESS,
            viewport={"width": 1400, "height": 900},
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Record every matching image request made by the page.
        page.on(
            "request",
            lambda request: found_urls.add(request.url)
            if classify(request.url)
            else None,
        )

        if WAIT_FOR_MANUAL_LOGIN:
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            input("Log in to SimCompanies, then press ENTER...")

        # ----- Step 1: start page -----
        await visit(page, START_URL, found_urls)

        # ----- Step 2: building pages (best effort) -----
        if DISCOVER_BUILDING_PAGES:
            building_pages = await discover_building_pages(page)

            if not building_pages:
                print("No building page links found on the start page.")

            for building_url in building_pages:
                await visit(page, building_url, found_urls)

        # ----- Step 3: download -----
        items = build_download_list(found_urls)
        product_count = sum(item["kind"] == "product" for item in items)

        print()
        print(
            f"Images found: {len(items)} "
            f"(products: {product_count}, buildings: {len(items) - product_count})"
        )

        downloaded, skipped, failed = 0, 0, []

        for index, item in enumerate(items, start=1):
            target = item["target"]

            if target.exists():
                skipped += 1
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                response = await context.request.get(item["url"], timeout=30000)

                if response.status != 200:
                    failed.append((item["url"], f"HTTP {response.status}"))
                    continue

                target.write_bytes(await response.body())
                downloaded += 1
                print(f"[{index}/{len(items)}] {target.relative_to(ROOT)}")

            except PlaywrightError as error:
                failed.append((item["url"], str(error)))

            await asyncio.sleep(DELAY_BETWEEN_DOWNLOADS_SECONDS)

        await context.close()

    # ----- Step 4: manifest -----
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = IMAGES_DIR / "image_manifest.csv"

    with manifest_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["kind", "name", "file", "source_url"])

        for item in items:
            if item["target"].exists():
                writer.writerow([
                    item["kind"],
                    item["name"],
                    item["target"].relative_to(IMAGES_DIR).as_posix(),
                    item["url"],
                ])

    print()
    print("=" * 60)
    print("DOWNLOAD FINISHED")
    print("=" * 60)
    print(f"Downloaded:     {downloaded}")
    print(f"Already exist:  {skipped}")
    print(f"Failed:         {len(failed)}")
    print(f"Manifest:       {manifest_path.relative_to(ROOT)}")

    for url, reason in failed:
        print(f"  FAILED {url} | {reason}")


if __name__ == "__main__":
    asyncio.run(main())