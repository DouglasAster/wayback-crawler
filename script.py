import os
import time
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
SEARCH_URL = "https://icepicx.is/search?limit=100&page={page}"

# Set START_PAGE to resume a run that was interrupted
START_PAGE = 1
# Set to a page number to stop early, or None to run until results run out
END_PAGE = None

CAPTURE_OUTLINKS = True

# Get your keys from: https://archive.org/account/s3.php
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

if not ACCESS_KEY or not SECRET_KEY:
    print("Error: ACCESS_KEY and SECRET_KEY must be set in .env file")
    exit(1)

headers = {
    "Accept": "application/json",
    "Authorization": f"LOW {ACCESS_KEY}:{SECRET_KEY}",
    "User-Agent": "wayback-crawler/1.0 (+https://github.com/DouglasAster/wayback-crawler)"
}

BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Save Page Now 2 (SPN2) API endpoint
target_endpoint = "https://web.archive.org/save"

seed_domain = urlparse(SEARCH_URL).netloc
submitted = set()


def fetch_page(url):
    """Fetch a results page, retrying a few times on transient errors."""
    for attempt in range(3):
        try:
            response = requests.get(url, headers={"User-Agent": BROWSER_USER_AGENT}, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Failed to fetch {url} (attempt {attempt + 1}/3): {e}")
            time.sleep(10)
    return None


def extract_links(html, page_url):
    """Return (result_links, all_same_domain_links) found on a results page."""
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    links = []

    for anchor in soup.find_all('a', href=True):
        absolute_url = urljoin(page_url, anchor['href'])
        parsed_url = urlparse(absolute_url)

        if parsed_url.netloc != seed_domain:
            continue

        clean_url = absolute_url.split('#')[0]
        if parsed_url.path.startswith("/person/"):
            results.append(clean_url)
        # Skip pagination/search links; each results page is submitted on its own
        if parsed_url.path.startswith(("/person/", "/office/")):
            links.append(clean_url)

    return results, list(dict.fromkeys(links))


def wait_for_slot():
    """Block until the account has a free SPN2 capture slot."""
    while True:
        try:
            status = requests.get(
                "https://web.archive.org/save/status/user",
                params={"_t": int(time.time())},
                headers=headers,
                timeout=30
            ).json()
            if status.get("daily_captures", 0) >= status.get("daily_captures_limit", 1):
                print("-> Daily capture limit reached, checking again in 30 min")
                time.sleep(1800)
                continue
            if status.get("available", 0) > 0:
                return
            print(f"-> All capture slots busy ({status.get('processing')} processing), checking again in 60s")
        except Exception as e:
            print(f"-> Could not check capture status: {e}")
        time.sleep(60)


def submit(url, capture_outlinks=False):
    """Submit a URL to Save Page Now, waiting as long as needed for a free slot."""
    if url in submitted:
        return
    submitted.add(url)

    print(f"Submitting: {url}")

    data = {
        "url": url,
        "capture_all": "1",
        "skip_first_archive": "1"
    }
    if capture_outlinks:
        data["capture_outlinks"] = "1"

    connection_errors = 0
    while True:
        wait_for_slot()
        try:
            spn_response = requests.post(
                target_endpoint,
                data=data,
                headers=headers,
                timeout=60
            )
        except Exception as e:
            connection_errors += 1
            print(f"-> Connection Error: {e}")
            if connection_errors >= 5:
                print(f"-> FAILED after 5 connection errors: {url}")
                break
            time.sleep(60)
            continue

        try:
            body = spn_response.json()
        except ValueError:
            body = {}

        if spn_response.status_code == 429:
            print(f"-> Rate limited: {body.get('message', 'no reason given')}. Retrying in 60s")
            time.sleep(60)
            continue

        if spn_response.status_code == 200 and "job_id" in body:
            print(f"-> Successfully queued via SPN2! job_id={body['job_id']}")
            if body.get("message"):
                print(f"   Note: {body['message']}")
        else:
            print(f"-> FAILED with status code: {spn_response.status_code}")
            if body.get("message"):
                print(f"   Reason: {body['message']}")
            elif "X-Archive-Wayback-Runtime-Error" in spn_response.headers:
                print(f"   Reason: {spn_response.headers['X-Archive-Wayback-Runtime-Error']}")
        break

    # Enforce safe 5-second pacing delay
    time.sleep(5)


# --- PAGINATE AND SUBMIT ---
page = START_PAGE
while END_PAGE is None or page <= END_PAGE:
    page_url = SEARCH_URL.format(page=page)
    print(f"\n=== Page {page}: {page_url} ===")

    html = fetch_page(page_url)
    if html is None:
        print(f"Giving up on page {page}. Rerun with START_PAGE = {page} to resume.")
        exit(1)

    results, links = extract_links(html, page_url)
    if not results:
        print(f"No results on page {page}; reached the end.")
        break

    print(f"Found {len(results)} results and {len(links)} links on page {page}.\n")

    if CAPTURE_OUTLINKS:
        submit(page_url, capture_outlinks=True)
    else:
        submit(page_url)
        for url in links:
            submit(url)

    page += 1

print(f"\nDone. Submitted {len(submitted)} URLs.")
