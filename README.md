# Wayback Crawler

This project archives a web page and all links one layer deep using the Internet Archive's SavePageNow API.

## How it Works

The script:

- Starts with a seed URL
- Extracts all links from that page (same domain only)
- Submits each URL to Internet Archive's SavePageNow API using credentials already defined in the script
- Archives the pages for preservation

## Running the Project

### Option 1: Run Locally with Python

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the script:

   ```bash
   python script.py
   ```

### Option 2: Run with Docker

1. Build the image:

   ```bash
   docker build -t archive-crawl .
   ```

2. Run the container:

   ```bash
   docker run archive-crawl
   ```

## Configuration

The script contains the following configuration:

- `SEED_URL`: The starting URL to crawl
- `ACCESS_KEY` and `SECRET_KEY`: Internet Archive API credentials

**Security Note:** The script contains hardcoded API keys and credentials. Before sharing or deploying, consider moving these to environment variables for security.
