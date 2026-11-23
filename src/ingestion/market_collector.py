
import asyncio
import csv
import re
from datetime import datetime, timezone
from pathlib import Path
import random

from playwright.async_api import (
    async_playwright,
    Error as PlaywrightError,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://www.simcompanies.com"
MARKET_PAGE = BASE_URL + "/market/resource/{}/"

API_PATTERN = re.compile(
    r"https://www\.simcompanies\.com/api/v3/market/0/(\d+)/"
)

# Examples:
# "1,2,3,4,5"
# "1:35"
# "1:35,40:155"
# "1:35,40,45,50:60,100"

PRODUCT_IDS = "1:35,40:155"

# Respect the site's API guidance. 5 min interval
MIN_INTERVAL_SECONDS = 15
MAX_INTERVAL_SECONDS = 38

PAGE_SETTLE_SECONDS = 5

OUTPUT_DIR = Path("data/bronze/market/offers")
PROFILE_DIR = Path("firefox_market_profile")


# ============================================================
# HELPERS
# ============================================================

def parse_product_ids(value):
    """Parse individual IDs and inclusive ranges."""

    result = []

    for part in value.split(","):
        part = part.strip()

        if not part:
            continue

        if ":" in part:
            start, end = map(int, part.split(":"))

            if start > end:
                raise ValueError(f"Invalid range: {part}")

            result.extend(range(start, end + 1))

        else:
            result.append(int(part))

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(result))


def interval():
    return random.uniform(
        MIN_INTERVAL_SECONDS,
        MAX_INTERVAL_SECONDS
    )


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_output_file():
    OUTPUT_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return OUTPUT_DIR / f"market_orders_{timestamp}.csv"


def flatten_offer(
    offer,
    source_page_id,
    api_resource_id,
    captured_at,
    snapshot_id,
):
    seller = offer.get("seller") or {}

    return {
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,

        # These IDs are intentionally separate.
        "source_page_id": source_page_id,
        "api_resource_id": api_resource_id,

        "order_id": offer.get("id"),
        "kind": offer.get("kind"),
        "quantity": offer.get("quantity"),
        "quality": offer.get("quality"),
        "price": offer.get("price"),

        "posted": offer.get("posted"),
        "datetime_decay_updated": offer.get(
            "datetimeDecayUpdated"
        ),
        "fees": offer.get("fees"),

        "seller_id": seller.get("id"),
        "seller_company": seller.get("company"),
        "seller_realm_id": seller.get("realmId"),
        "seller_npc": seller.get("npc"),
    }


FIELDS = [
    "snapshot_id",
    "captured_at",
    "source_page_id",
    "api_resource_id",
    "order_id",
    "kind",
    "quantity",
    "quality",
    "price",
    "posted",
    "datetime_decay_updated",
    "fees",
    "seller_id",
    "seller_company",
    "seller_realm_id",
    "seller_npc",
]


# ============================================================
# COLLECTOR
# ============================================================

async def main():

    product_ids = parse_product_ids(PRODUCT_IDS)

    if not product_ids:
        print("No product IDs configured.")
        return

    output_file = create_output_file()

    snapshot_id = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    print("=" * 60)
    print("SIMCOMPANIES MARKET COLLECTOR")
    print("=" * 60)

    print(f"Products to visit: {len(product_ids)}")
    print(f"First ID:          {product_ids[0]}")
    print(f"Last ID:           {product_ids[-1]}")
    print(f"Output:            {output_file}")
    print()

    async with async_playwright() as p:

        context = await p.firefox.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1400, "height": 900},
        )

        page = (
            context.pages[0]
            if context.pages
            else await context.new_page()
        )

        # Store all responses observed by this browser page.
        observed_responses = []

        page.on(
            "response",
            lambda response: observed_responses.append(response)
            if API_PATTERN.fullmatch(response.url)
            else None
        )

        page.on(
            "pageerror",
            lambda error: print(f"[JS ERROR] {error}")
        )

        page.on(
            "requestfailed",
            lambda request: print(
                f"[REQUEST FAILED] {request.url} | "
                f"{request.failure}"
            )
            if "/api/v3/market/" in request.url
            else None
        )

        # Open homepage and allow manual login.
        await page.goto(
            BASE_URL,
            wait_until="domcontentloaded"
        )

        print("Firefox opened.")
        print("Log in to SimCompanies if necessary.")
        input("Press ENTER after you are logged in...")

        total_offers = 0
        successful_pages = 0
        pages_with_errors = 0
        total_api_resources = 0

        with output_file.open(
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=FIELDS
            )

            writer.writeheader()

            for index, product_id in enumerate(product_ids):

                url = MARKET_PAGE.format(product_id)

                print()
                print("-" * 60)
                print(
                    f"[{index + 1}/{len(product_ids)}] "
                    f"Page ID: {product_id}"
                )

                # Remember where this page's responses begin.
                response_start = len(observed_responses)

                navigation_error = None

                try:
                    await page.goto(
                        url,
                        wait_until="commit",
                        timeout=60000,
                    )

                except PlaywrightError as error:
                    navigation_error = str(error)

                    print(
                        f"[NAVIGATION WARNING] "
                        f"{navigation_error}"
                    )

                # Let the application finish its requests.
                await page.wait_for_timeout(
                    PAGE_SETTLE_SECONDS * 1000
                )

                print(f"Current URL: {page.url}")

                if navigation_error:
                    pages_with_errors += 1

                # Get responses observed during this navigation.
                page_responses = observed_responses[response_start:]

                # Keep one response per API resource ID.
                # The last observed response is used.
                resource_responses = {}

                for response in page_responses:
                    match = API_PATTERN.fullmatch(response.url)

                    if match:
                        api_resource_id = int(match.group(1))
                        resource_responses[api_resource_id] = response

                if not resource_responses:
                    print("No market API responses detected.")

                page_offer_count = 0
                page_resource_count = 0

                for api_resource_id, response in resource_responses.items():

                    print(
                        f"[API] Resource {api_resource_id} "
                        f"| HTTP {response.status}"
                    )

                    if response.status != 200:
                        continue

                    try:
                        data = await response.json()
                        
                        print(f"Response type: {type(data).__name__}")

                        if isinstance(data, list):
                            print(f"Offers returned: {len(data)}")

                            if data:
                                print("First offer ID:", data[0].get("id"))
                                print("Last offer ID:", data[-1].get("id"))

                    except Exception as error:
                        print(
                            f"Could not parse JSON for "
                            f"resource {api_resource_id}: {error}"
                        )
                        continue

                    if not isinstance(data, list):
                        print(
                            f"Unexpected response format for "
                            f"resource {api_resource_id}"
                        )
                        continue

                    captured_at = utc_now()

                    for offer in data:

                        if not isinstance(offer, dict):
                            continue

                        row = flatten_offer(
                            offer=offer,
                            source_page_id=product_id,
                            api_resource_id=api_resource_id,
                            captured_at=captured_at,
                            snapshot_id=snapshot_id,
                        )

                        writer.writerow(row)

                    csv_file.flush()

                    offer_count = len(data)

                    page_offer_count += offer_count
                    total_offers += offer_count
                    page_resource_count += 1

                if page_resource_count:
                    successful_pages += 1

                total_api_resources += page_resource_count

                print(
                    f"API resources captured: {page_resource_count}"
                )
                print(
                    f"Offers captured:         {page_offer_count}"
                )
                print(
                    f"Total offers:             {total_offers}"
                )

                # Wait before visiting the next page.
                if index < len(product_ids) - 1:

                    wait_time = interval()

                    print(
                        f"Waiting {wait_time:.1f} seconds..."
                    )

                    await asyncio.sleep(wait_time)

        print()
        print("=" * 60)
        print("COLLECTION FINISHED")
        print("=" * 60)

        print(f"Pages with API data: {successful_pages}")
        print(f"Pages with errors:   {pages_with_errors}")
        print(f"API resources:       {total_api_resources}")
        print(f"Offers captured:     {total_offers}")
        print(f"CSV file:            {output_file}")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
