"""
Web scraper for real estate property descriptions.
Scrapes Zillow-style property listings for NLP training data.

Usage:
    python scrape_real_estate_data.py

Requirements:
    pip install beautifulsoup4 requests
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# Set UTF-8 encoding
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def extract_spec_from_text(text):
    """
    Extract building specification from text description.
    Returns spec dict or None if can't extract.
    """
    spec = {}

    # Extract bedrooms
    bedroom_patterns = [
        r'(\d+)[\s-]*(bedroom|bed|br)',
        r'(\d+)br',
        r'(\d+)b(?=/|\s)',
    ]

    for pattern in bedroom_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            spec['bedrooms'] = int(match.group(1))
            break

    # Extract bathrooms
    bathroom_patterns = [
        r'(\d+)[\s-]*(bathroom|bath|ba)',
        r'(\d+)ba',
    ]

    for pattern in bathroom_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            spec['bathrooms'] = int(match.group(1))
            break

    # Extract rooms/features
    if re.search(r'\bkitchen\b', text, re.IGNORECASE):
        spec['kitchen'] = True
    if re.search(r'\bliving\s*room\b', text, re.IGNORECASE):
        spec['living_room'] = True
    if re.search(r'\bdining\s*room\b', text, re.IGNORECASE):
        spec['dining_room'] = True
    if re.search(r'\b(study|office)\b', text, re.IGNORECASE):
        spec['study'] = True
    if re.search(r'\bgarage\b', text, re.IGNORECASE):
        spec['garage'] = True

    # Extract area (sqm or sqft)
    area_patterns = [
        r'(\d+)\s*sq\s*m',
        r'(\d+)\s*sqm',
        r'(\d+)\s*square\s*meters?',
    ]

    for pattern in area_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            spec['total_area_sqm'] = int(match.group(1))
            break

    # Only return if we got at least bedrooms or bathrooms
    if 'bedrooms' in spec or 'bathrooms' in spec:
        return spec
    return None


def scrape_sample_data():
    """
    Scrape sample real estate data.

    NOTE: This is a TEMPLATE. You may need to:
    1. Update URLs for actual real estate sites
    2. Adjust selectors based on website structure
    3. Add delays to respect rate limits
    4. Handle anti-scraping measures
    """

    print("="*80)
    print("REAL ESTATE DATA SCRAPER")
    print("="*80)
    print("\nNOTE: This is a template scraper.")
    print("For actual scraping, you'll need to:")
    print("  1. Use actual real estate website URLs")
    print("  2. Inspect HTML and update selectors")
    print("  3. Handle pagination and rate limiting\n")

    # Sample hardcoded data (replace with actual scraping)
    sample_descriptions = [
        "Beautiful 3 bedroom, 2 bathroom house with modern kitchen and spacious living room",
        "Cozy 2BR apartment with 1 bath, updated kitchen, and bright living area",
        "Luxury 4 bedroom villa with 3 bathrooms, gourmet kitchen, formal dining room, and study",
        "Compact studio apartment with bathroom and kitchenette, perfect for singles",
        "Spacious 5BR family home with 4BA, large kitchen, living room, dining room, and 2-car garage",
        "Modern 3 bedroom townhouse with 2.5 bathrooms and open-plan living",
        "Charming 2 bedroom cottage with 1 bathroom, country kitchen, and cozy living room",
        "Contemporary 4BR house with 3BA, chef's kitchen, great room, and home office",
        "Elegant 3 bedroom condo with 2 bathrooms and updated amenities",
        "Single bedroom apartment with bathroom, ideal for young professionals"
    ]

    samples = []

    print(f"Processing {len(sample_descriptions)} sample descriptions...\n")

    for i, text in enumerate(sample_descriptions, 1):
        print(f"[{i}/{len(sample_descriptions)}] Processing...")
        print(f"Text: {text}")

        spec = extract_spec_from_text(text)

        if spec:
            print(f"Spec: {json.dumps(spec)}")
            samples.append({
                "text": text,
                "spec": spec
            })
            print("✓ SUCCESS")
        else:
            print("✗ Could not extract spec")

        print("-" * 80)

    return samples


def scrape_with_manual_input():
    """
    Interactive mode: User pastes descriptions, script extracts specs.
    """
    print("="*80)
    print("INTERACTIVE SCRAPING MODE")
    print("="*80)
    print("\nInstructions:")
    print("1. Go to Zillow/Realtor.com")
    print("2. Copy property descriptions (one per paste)")
    print("3. Paste here (type 'done' when finished)")
    print("4. Script will extract specs automatically\n")

    samples = []

    while True:
        print("\nPaste property description (or type 'done'):")
        text = input("> ").strip()

        if text.lower() == 'done':
            break

        if not text:
            continue

        spec = extract_spec_from_text(text)

        if spec:
            print(f"✓ Extracted: {json.dumps(spec)}")
            samples.append({"text": text, "spec": spec})
        else:
            print("✗ Could not extract spec. Try a more detailed description.")

    return samples


def save_scraped_data(samples, output_file="data/nlp_training/scraped_data.jsonl"):
    """Save scraped data to file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    print(f"\n[OK] Saved {len(samples)} samples to: {output_path}")


def main():
    """Main scraping workflow."""
    print("\nChoose scraping mode:")
    print("1. Auto mode (sample data)")
    print("2. Interactive mode (paste descriptions)")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "2":
        samples = scrape_with_manual_input()
    else:
        samples = scrape_sample_data()

    if samples:
        save_scraped_data(samples)
        print(f"\n[SUCCESS] Scraped {len(samples)} samples!")
    else:
        print("\n[WARNING] No samples collected.")


if __name__ == "__main__":
    main()
