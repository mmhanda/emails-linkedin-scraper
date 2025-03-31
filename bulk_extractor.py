import sys
import csv
from pathlib import Path
from urllib.parse import urlparse

from extract_emails import DefaultFilterAndEmailFactory as Factory
from extract_emails import DefaultWorker
from extract_emails.browsers.requests_browser import RequestsBrowser as Browser
from extract_emails.data_savers import CsvSaver

# --- Configuration ---
INPUT_FILE = "websites.txt"
OUTPUT_FILE = "output.csv"
CRAWL_DEPTH = 10
MAX_LINKS_PER_PAGE = 1
DEFAULT_SCHEME = "https"
# --- End Configuration ---

# --- CSV Header Configuration ---
# Define the headers in the EXACT order you want them in the CSV file.
CSV_HEADERS = ["page", "email", "website"]
# --- End CSV Header Configuration ---


def read_websites_from_file(filename):
    """Reads websites from a file, one per line, and formats them."""
    websites = []
    input_path = Path(filename)
    if not input_path.is_file():
        print(f"Error: Input file '{filename}' not found.")
        sys.exit(1)

    print(f"Reading websites from {filename}...")
    with input_path.open('r', encoding='utf-8') as f:
        for line in f:
            url = line.strip()
            if not url or url.startswith('#'):
                continue

            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"{DEFAULT_SCHEME}://{url}"
                print(f"  Formatted URL: {line.strip()} -> {url}")
            elif parsed.scheme not in ['http', 'https']:
                print(f"  Warning: Skipping URL with unsupported scheme: {url}")
                continue

            websites.append(url)
    print(f"Found {len(websites)} websites to process.")
    return websites


# --- Main Script Logic ---
websites_to_crawl = read_websites_from_file(INPUT_FILE)

if not websites_to_crawl:
    print("No valid websites found in the input file. Exiting.")
    sys.exit(0)

browser = Browser()
# Pass the exact headers to CsvSaver
# It will use these headers to look for corresponding attributes on the objects
data_saver = CsvSaver(
    save_mode="a",
    output_path=Path(OUTPUT_FILE),
    headers=CSV_HEADERS  # Crucial: Define the columns and their order
)
print(f"Output will be appended to {OUTPUT_FILE}")
print(f"Using CSV headers: {', '.join(CSV_HEADERS)}")
print(
    f"Starting email extraction (depth={CRAWL_DEPTH}, max_links={MAX_LINKS_PER_PAGE})...")


for i, website in enumerate(websites_to_crawl, 1):
    print(f"\n--- Processing website {i}/{len(websites_to_crawl)}: {website} ---")
    data_found_for_website = False  # Flag to track if any data/placeholder is saved
    try:
        factory = Factory(
            website_url=website,
            browser=browser,
            depth=CRAWL_DEPTH,
            max_links_from_page=MAX_LINKS_PER_PAGE
        )
        worker = DefaultWorker(factory)
        # Get the list of PageData objects (or similar custom objects)
        raw_data = worker.get_data()

        if raw_data:
            # Pass the list of objects directly to CsvSaver.
            # It should map attributes (like .page, .email, .website)
            # to the columns defined in CSV_HEADERS.
            # If an object's .email attribute is None or '', CsvSaver
            # (using csv.DictWriter internally) should write an empty field.
            print(f"  Data found: {len(raw_data)} entries. Saving directly...")
            data_saver.save(raw_data)
            data_found_for_website = True
            print(f"  Data saved for {website}")

        else:
            # No data objects returned by the worker for this website.
            # Save a placeholder row using a standard dictionary.
            # We assume CsvSaver can handle a list containing this dict.
            print(
                f"  No data returned by worker for {website}. Saving placeholder row.")
            placeholder_data = [{
                'page': website,    # Corresponds to first header
                'email': '',        # Corresponds to second header
                'website': website  # Corresponds to third header
            }]
            data_saver.save(placeholder_data)
            data_found_for_website = True
            print(f"  Placeholder row saved for {website}")

    except Exception as e:
        print(f"!! Error processing {website}: {e}")
        # Attempt to save an error placeholder row (as a dictionary)
        try:
            # Make sure keys match CSV_HEADERS
            error_placeholder = [{
                'page': 'ERROR_DURING_PROCESSING',
                # Limit error length
                'email': f'ERROR: {type(e).__name__}: {str(e)}'[0:200],
                'website': website
            }]
            # Hope CsvSaver handles this list-of-dicts correctly too
            data_saver.save(error_placeholder)
            print(f"  Error placeholder row saved for {website}")
            data_found_for_website = True
        except Exception as save_err:
            # Log if saving the error placeholder *also* fails
            print(f"!! Could not save error placeholder for {website}: {save_err}")
        continue  # Continue with the next website in the list


print("\n--- Processing finished ---")
