"""
=============================================================================
ArchiText: Gemini-Powered Training Data Generator
=============================================================================

This script generates high-quality text-to-spec training data by using
Google's Gemini API to create varied natural language descriptions for
floor plans extracted from the CubiCasa5K dataset.

Process:
--------
    1. Load CubiCasa layout JSONs (already parsed)
    2. Extract room specifications (bedrooms, bathrooms, etc.)
    3. Use Gemini API to generate 10-15 varied text descriptions per spec
    4. Save as JSONL for T5 model training

Requirements:
-------------
    - Google Gemini API key (set as GEMINI_API_KEY environment variable)
    - pip install google-generativeai

Usage:
------
    # Set your API key first
    set GEMINI_API_KEY=your_api_key_here

    # Run the generator
    python generate_training_data_gemini.py

Author: ArchiText Team
Version: 1.0.0
=============================================================================
"""

import json
import os
import sys
import time
import random
from pathlib import Path
from typing import Dict, List, Optional

# Try to import Gemini
try:
    import google.generativeai as genai
except ImportError:
    print("Please install google-generativeai: pip install google-generativeai")
    sys.exit(1)


class GeminiTrainingDataGenerator:
    """Generate training data using Gemini API."""

    def __init__(self, api_key: str = None):
        """Initialize with Gemini API key."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set it as environment variable or pass to constructor.")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Rate limiting
        self.requests_per_minute = 14  # Stay under 15 RPM free tier
        self.last_request_time = 0

    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        min_interval = 60.0 / self.requests_per_minute
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def extract_spec_from_layout(self, layout: Dict) -> Dict:
        """Extract a simplified spec from CubiCasa layout."""
        room_summary = layout.get("room_summary", {})
        metadata = layout.get("metadata", {})

        # Count key room types
        spec = {
            "bedrooms": room_summary.get("bedroom", 0),
            "bathrooms": room_summary.get("bathroom", 0),
            "kitchen": room_summary.get("kitchen", 0) > 0,
            "living_room": room_summary.get("living_room", 0) > 0,
            "dining_room": room_summary.get("dining_room", 0) > 0,
        }

        # Optional rooms
        if room_summary.get("garage", 0) > 0:
            spec["garage"] = True
        if room_summary.get("balcony", 0) > 0:
            spec["balcony"] = True
        if room_summary.get("study", 0) > 0 or room_summary.get("office", 0) > 0:
            spec["study"] = True
        if room_summary.get("storage", 0) > 0 or room_summary.get("closet", 0) > 1:
            spec["storage"] = True

        # Add total area if available
        if metadata.get("total_area"):
            spec["total_area_sqm"] = round(metadata["total_area"])

        return spec

    def generate_text_variations(self, spec: Dict, num_variations: int = 10) -> List[str]:
        """Use Gemini to generate varied text descriptions for a spec."""

        # Build description of the spec
        parts = []
        if spec.get("bedrooms", 0) > 0:
            parts.append(f"{spec['bedrooms']} bedroom(s)")
        if spec.get("bathrooms", 0) > 0:
            parts.append(f"{spec['bathrooms']} bathroom(s)")
        if spec.get("kitchen"):
            parts.append("kitchen")
        if spec.get("living_room"):
            parts.append("living room")
        if spec.get("dining_room"):
            parts.append("dining room")
        if spec.get("garage"):
            parts.append("garage")
        if spec.get("balcony"):
            parts.append("balcony")
        if spec.get("study"):
            parts.append("study/office")

        area_info = ""
        if spec.get("total_area_sqm"):
            area_info = f" The total area is approximately {spec['total_area_sqm']} square meters."

        spec_description = ", ".join(parts)

        prompt = f"""Generate {num_variations} different natural language descriptions for a floor plan with: {spec_description}.{area_info}

Requirements:
- Each description should be unique and natural sounding
- Vary the style: formal, casual, brief, detailed
- Use different phrasings: "3 bedroom house", "house with 3 bedrooms", "3-bed home"
- Some can mention style: "modern", "cozy", "spacious", "compact"
- Some can be very brief: "3 bed 2 bath"
- Some can be more descriptive
- Do NOT include any numbering or bullet points
- Output ONLY the descriptions, one per line
- No explanations or additional text

Example outputs for a 3 bed 2 bath house:
Modern 3 bedroom house with 2 bathrooms and open kitchen
Spacious three-bedroom home featuring 2 baths
3 bed 2 bath with kitchen and living area
Contemporary 3BR/2BA residence with dining room
Cozy three bedroom, two bathroom family home"""

        self._rate_limit()

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Parse response into lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            # Filter out any lines that look like meta-text
            valid_lines = []
            for line in lines:
                # Skip lines that look like instructions or numbering
                if line[0].isdigit() and (line[1] == '.' or line[1] == ')'):
                    line = line[2:].strip()
                if line.startswith('-'):
                    line = line[1:].strip()
                if len(line) > 10 and not line.lower().startswith(('here', 'sure', 'okay', 'note')):
                    valid_lines.append(line)

            return valid_lines[:num_variations]

        except Exception as e:
            print(f"[!] Gemini API error: {e}")
            return []

    def generate_fallback_variations(self, spec: Dict) -> List[str]:
        """Generate template-based variations (fallback if API fails)."""
        templates = [
            "{beds} bedroom house with {baths} bathroom",
            "{beds} bed {baths} bath home",
            "Modern {beds}-bedroom residence with {baths} bathrooms",
            "Spacious {beds} bedroom, {baths} bathroom house",
            "{beds}BR/{baths}BA home",
            "Cozy {beds} bed {baths} bath",
            "Contemporary {beds} bedroom house featuring {baths} baths",
            "{beds} bedroom {baths} bathroom residence",
            "Family home with {beds} bedrooms and {baths} bathrooms",
            "{beds}-bed {baths}-bath property",
        ]

        beds = spec.get("bedrooms", 2)
        baths = spec.get("bathrooms", 1)

        variations = []
        for template in templates:
            text = template.format(beds=beds, baths=baths)

            # Add optional features randomly
            extras = []
            if spec.get("kitchen") and random.random() > 0.5:
                extras.append("kitchen")
            if spec.get("living_room") and random.random() > 0.5:
                extras.append("living room")
            if spec.get("dining_room") and random.random() > 0.5:
                extras.append("dining room")
            if spec.get("garage") and random.random() > 0.3:
                extras.append("garage")
            if spec.get("study") and random.random() > 0.3:
                extras.append("study")

            if extras:
                text += " with " + ", ".join(extras)

            variations.append(text)

        return variations


def main():
    """Generate training data from CubiCasa layouts."""
    print("=" * 70)
    print("GEMINI-POWERED TRAINING DATA GENERATOR")
    print("=" * 70)

    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    cubicasa_dir = project_root / "datasets" / "processed" / "cubicasa_layouts"
    output_file = project_root / "datasets" / "processed" / "gemini_training_data.jsonl"

    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n[!] GEMINI_API_KEY not set!")
        print("    Set it with: set GEMINI_API_KEY=your_key_here")
        print("\n    Falling back to template-based generation...")
        use_gemini = False
    else:
        print(f"\n[OK] Gemini API key found")
        use_gemini = True
        generator = GeminiTrainingDataGenerator(api_key)

    # Load CubiCasa layouts
    print(f"\nLoading layouts from: {cubicasa_dir}")
    layout_files = list(cubicasa_dir.glob("*.json"))
    print(f"Found {len(layout_files)} layout files")

    if not layout_files:
        print("[!] No layout files found!")
        return

    # Generate training data
    training_pairs = []
    processed = 0
    errors = 0

    # Limit for free tier (process ~300 layouts with 10 variations = 3000 API calls)
    max_layouts = min(len(layout_files), 500)  # Adjust based on your needs

    print(f"\nProcessing {max_layouts} layouts...")
    print("-" * 70)

    for i, layout_file in enumerate(layout_files[:max_layouts]):
        try:
            with open(layout_file, 'r') as f:
                layout = json.load(f)

            # Extract spec
            if use_gemini:
                spec = generator.extract_spec_from_layout(layout)
            else:
                # Simple extraction for fallback
                room_summary = layout.get("room_summary", {})
                spec = {
                    "bedrooms": room_summary.get("bedroom", 0),
                    "bathrooms": room_summary.get("bathroom", 0),
                    "kitchen": room_summary.get("kitchen", 0) > 0,
                    "living_room": room_summary.get("living_room", 0) > 0,
                    "dining_room": room_summary.get("dining_room", 0) > 0,
                }

            # Skip if no bedrooms (probably not a residential layout)
            if spec.get("bedrooms", 0) == 0:
                continue

            # Generate text variations
            if use_gemini:
                variations = generator.generate_text_variations(spec, num_variations=10)
                if not variations:
                    # Fallback to templates if API fails
                    fallback_gen = GeminiTrainingDataGenerator.__new__(GeminiTrainingDataGenerator)
                    variations = fallback_gen.generate_fallback_variations(spec)
            else:
                fallback_gen = GeminiTrainingDataGenerator.__new__(GeminiTrainingDataGenerator)
                variations = fallback_gen.generate_fallback_variations(spec)

            # Create training pairs
            for text in variations:
                training_pairs.append({
                    "text": text,
                    "spec": spec
                })

            processed += 1

            # Progress update
            if processed % 10 == 0:
                print(f"  Processed {processed}/{max_layouts} layouts, {len(training_pairs)} pairs generated")

        except Exception as e:
            errors += 1
            print(f"  [!] Error processing {layout_file.name}: {e}")

    # Save training data
    print(f"\n{'=' * 70}")
    print(f"GENERATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"Layouts processed: {processed}")
    print(f"Training pairs generated: {len(training_pairs)}")
    print(f"Errors: {errors}")

    if training_pairs:
        # Shuffle the data
        random.shuffle(training_pairs)

        # Save to JSONL
        print(f"\nSaving to: {output_file}")
        with open(output_file, 'w') as f:
            for pair in training_pairs:
                f.write(json.dumps(pair) + '\n')

        print(f"[OK] Saved {len(training_pairs)} training pairs!")

        # Show sample
        print("\nSample training pairs:")
        print("-" * 70)
        for pair in training_pairs[:5]:
            print(f"  Text: {pair['text']}")
            print(f"  Spec: {pair['spec']}")
            print()

        # Create combined dataset with existing data
        existing_data_path = project_root / "data" / "nlp_training" / "synthetic_train_2000.jsonl"
        combined_output = project_root / "datasets" / "processed" / "combined_gemini_train.jsonl"

        if existing_data_path.exists():
            print(f"\nCombining with existing data from: {existing_data_path}")
            existing_pairs = []
            with open(existing_data_path, 'r') as f:
                for line in f:
                    if line.strip():
                        existing_pairs.append(json.loads(line))

            all_pairs = training_pairs + existing_pairs
            random.shuffle(all_pairs)

            with open(combined_output, 'w') as f:
                for pair in all_pairs:
                    f.write(json.dumps(pair) + '\n')

            print(f"[OK] Combined dataset saved: {len(all_pairs)} total pairs")
            print(f"     Path: {combined_output}")

    print("\n" + "=" * 70)
    print("Next step: Train the model with:")
    print(f"  python train_nlp_model.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
