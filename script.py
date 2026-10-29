import os
import time
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
SEED_URL = ""

# Get your keys from: https://archive.org
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

if not ACCESS_KEY or not SECRET_KEY:
    print("Error: ACCESS_KEY and SECRET_KEY must be set in .env file")
    exit(1)

headers = {
    "Accept": "application/json",
    "Authorization": f"LOW {ACCESS_KEY}:{SECRET_KEY}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- STEP 1: EXTRACT LINKS ---
print(f"Fetching seed page to extract links: {SEED_URL}")
try:
    response = requests.get(SEED_URL, timeout=10)
    response.raise_for_status()
except Exception as e:
    print(f"Failed to fetch seed URL: {e}")
    exit(1)

soup = BeautifulSoup(response.text, 'html.parser')
parsed_seed = urlparse(SEED_URL)
seed_domain = parsed_seed.netloc

urls_to_submit = {SEED_URL}

for anchor in soup.find_all('a', href=True):
    href = anchor['href']
    absolute_url = urljoin(SEED_URL, href)
    parsed_url = urlparse(absolute_url)
    
    if parsed_url.netloc == seed_domain:
        clean_url = absolute_url.split('#')[0]
        urls_to_submit.add(clean_url)

print(f"Found {len(urls_to_submit)} unique URLs to archive.\n")

# --- STEP 2: SUBMIT VIA SPN2 GET API ---
target_endpoint = "https://archive.org"

for url in sorted(list(urls_to_submit)):
    print(f"Submitting: {url}")
    
    # Pass target routing parameters safely inside dictionary key pairs
    query_params = {
        "url": url,
        "capture_all": "1",
        "skip_first_archive": "1"
    }
    
    try:
        spn_response = requests.get(
            target_endpoint,
            params=query_params,
            headers=headers,
            timeout=15
        )
        
        if spn_response.status_code == 200:
            print("-> Successfully queued via SPN2!")
        else:
            print(f"-> Failed with status code: {spn_response.status_code}")
            if "X-Archive-Wayback-Runtime-Error" in spn_response.headers:
                print(f"   Reason: {spn_response.headers['X-Archive-Wayback-Runtime-Error']}")
                
    except Exception as e:
        print(f"-> Connection Error: {e}")
    
    # Enforce safe 5-second pacing delay
    time.sleep(5)