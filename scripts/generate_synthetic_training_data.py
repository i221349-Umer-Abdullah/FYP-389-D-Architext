"""
Generate synthetic training data for Text-to-Spec NLP model.
Creates diverse, high-quality text-specification pairs.
"""

import json
import random
import sys
from pathlib import Path

# Set UTF-8 encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Templates and vocabulary
ADJECTIVES = [
    "modern", "contemporary", "spacious", "cozy", "luxury", "elegant",
    "comfortable", "beautiful", "charming", "stunning", "bright",
    "well-designed", "stylish", "compact", "traditional", "rustic",
    "minimalist", "classic", "sophisticated", "warm", "inviting"
]

BUILDING_TYPES = [
    "house", "apartment", "villa", "cottage", "bungalow", "townhouse",
    "condo", "flat", "duplex", "residence", "home", "unit", "penthouse"
]

ROOM_ADJECTIVES = {
    "kitchen": ["spacious", "modern", "open-plan", "gourmet", "equipped", "large"],
    "living_room": ["spacious", "open", "bright", "large", "comfortable", "sunny"],
    "dining_room": ["formal", "separate", "elegant", "spacious"],
    "study": ["private", "quiet", "home office", "dedicated"],
    "garage": ["attached", "2-car", "covered", "private"]
}

STYLES = [
    "with an open floor plan",
    "featuring modern amenities",
    "with high ceilings",
    "in a quiet neighborhood",
    "with plenty of natural light",
    "with hardwood floors",
    "with updated fixtures",
    "perfect for families",
    "ideal for entertaining",
    "with a functional layout"
]

def generate_spec():
    """Generate a random building specification."""
    spec = {
        "bedrooms": random.randint(1, 6),
        "bathrooms": random.randint(1, 4),
    }

    # Randomly add rooms
    if random.random() > 0.1:
        spec["kitchen"] = True
    if random.random() > 0.3:
        spec["living_room"] = True
    if random.random() > 0.6:
        spec["dining_room"] = True
    if random.random() > 0.8:
        spec["study"] = True
    if random.random() > 0.7:
        spec["garage"] = True

    # Add area sometimes
    if random.random() > 0.5:
        base_area = 40 + (spec["bedrooms"] * 15) + (spec["bathrooms"] * 5)
        spec["total_area_sqm"] = base_area + random.randint(-10, 20)

    return spec

def spec_to_text_template1(spec):
    """Template 1: Formal real estate style."""
    adj = random.choice(ADJECTIVES)
    building_type = random.choice(BUILDING_TYPES)

    # Basic structure
    bedrooms = spec["bedrooms"]
    bathrooms = spec["bathrooms"]

    text = f"A {adj} {bedrooms}-bedroom {building_type} with {bathrooms} bathroom"
    if bathrooms > 1:
        text += "s"

    # Add rooms
    rooms = []
    if spec.get("kitchen"):
        kitchen_adj = random.choice(ROOM_ADJECTIVES["kitchen"]) if random.random() > 0.5 else ""
        rooms.append(f"{kitchen_adj} kitchen".strip())
    if spec.get("living_room"):
        living_adj = random.choice(ROOM_ADJECTIVES["living_room"]) if random.random() > 0.5 else ""
        rooms.append(f"{living_adj} living room".strip())
    if spec.get("dining_room"):
        dining_adj = random.choice(ROOM_ADJECTIVES["dining_room"]) if random.random() > 0.5 else ""
        rooms.append(f"{dining_adj} dining room".strip())
    if spec.get("study"):
        rooms.append(random.choice(["study", "home office", "office"]))
    if spec.get("garage"):
        garage_adj = random.choice(ROOM_ADJECTIVES["garage"]) if random.random() > 0.5 else ""
        rooms.append(f"{garage_adj} garage".strip())

    if rooms:
        if len(rooms) == 1:
            text += f", {rooms[0]}"
        elif len(rooms) == 2:
            text += f", {rooms[0]} and {rooms[1]}"
        else:
            text += ", " + ", ".join(rooms[:-1]) + f", and {rooms[-1]}"

    # Add style sometimes
    if random.random() > 0.6:
        text += " " + random.choice(STYLES)

    return text

def spec_to_text_template2(spec):
    """Template 2: Abbreviated style."""
    bedrooms = spec["bedrooms"]
    bathrooms = spec["bathrooms"]
    building_type = random.choice(BUILDING_TYPES)

    text = f"{bedrooms}BR {building_type}"

    if random.random() > 0.3:
        text += f" with {bathrooms}BA"

    rooms = []
    if spec.get("kitchen"):
        rooms.append("kitchen")
    if spec.get("living_room"):
        rooms.append("living room")
    if spec.get("dining_room"):
        rooms.append("dining room")
    if spec.get("study"):
        rooms.append("study")

    if rooms and random.random() > 0.3:
        text += " and " + ", ".join(rooms)

    return text

def spec_to_text_template3(spec):
    """Template 3: Descriptive paragraph style."""
    adj1 = random.choice(ADJECTIVES)
    adj2 = random.choice(ADJECTIVES)
    while adj2 == adj1:
        adj2 = random.choice(ADJECTIVES)

    building_type = random.choice(BUILDING_TYPES)
    bedrooms = spec["bedrooms"]
    bathrooms = spec["bathrooms"]

    bedroom_word = "bedroom" if bedrooms == 1 else "bedrooms"
    bathroom_word = "bathroom" if bathrooms == 1 else "bathrooms"

    text = f"{adj1.capitalize()} {bedrooms} {bedroom_word}, {bathrooms} {bathroom_word} {building_type}"

    features = []
    if spec.get("kitchen"):
        features.append("kitchen")
    if spec.get("living_room"):
        features.append("living area")
    if spec.get("dining_room"):
        features.append("dining space")
    if spec.get("study"):
        features.append("study")
    if spec.get("garage"):
        features.append("garage")

    if features:
        text += f" featuring {', '.join(features)}"

    if spec.get("total_area_sqm") and random.random() > 0.5:
        text += f" with approximately {spec['total_area_sqm']}sqm of living space"

    return text

def spec_to_text_template4(spec):
    """Template 4: Conversational style."""
    building_type = random.choice(BUILDING_TYPES)
    bedrooms = spec["bedrooms"]
    bathrooms = spec["bathrooms"]

    starters = [
        "Looking for a",
        "Beautiful",
        "Charming",
        "Stunning",
        "This",
        "Check out this"
    ]

    text = f"{random.choice(starters)} {bedrooms} bedroom {building_type}"

    if random.random() > 0.3:
        text += f" with {bathrooms} bath"
        if bathrooms > 1:
            text += "s"

    if spec.get("kitchen") and spec.get("living_room") and random.random() > 0.5:
        text += " and open-plan kitchen and living area"
    else:
        rooms = []
        if spec.get("kitchen"):
            rooms.append("kitchen")
        if spec.get("living_room"):
            rooms.append("living room")
        if spec.get("dining_room"):
            rooms.append("dining room")
        if spec.get("study"):
            rooms.append("study")

        if rooms:
            text += " with " + " and ".join(rooms)

    return text

def spec_to_text_template5(spec):
    """Template 5: Minimal/brief style."""
    bedrooms = spec["bedrooms"]
    bathrooms = spec["bathrooms"]

    variations = [
        f"{bedrooms} bed {bathrooms} bath",
        f"{bedrooms}BR/{bathrooms}BA",
        f"{bedrooms} bedroom, {bathrooms} bathroom",
        f"{bedrooms}B{bathrooms}B"
    ]

    text = random.choice(variations)

    if spec.get("kitchen") or spec.get("living_room"):
        addons = []
        if spec.get("kitchen"):
            addons.append("kit")
        if spec.get("living_room"):
            addons.append("liv")
        if addons and random.random() > 0.5:
            text += " + " + "/".join(addons)

    return text

def generate_training_pair():
    """Generate a single text-spec training pair."""
    spec = generate_spec()

    # Choose random template
    templates = [
        spec_to_text_template1,
        spec_to_text_template2,
        spec_to_text_template3,
        spec_to_text_template4,
        spec_to_text_template5
    ]

    template = random.choice(templates)
    text = template(spec)

    return {
        "text": text,
        "spec": spec
    }

def generate_dataset(n_samples=2000):
    """Generate n training samples."""
    print(f"Generating {n_samples} synthetic training samples...")
    print("=" * 80)

    samples = []
    for i in range(n_samples):
        if (i + 1) % 100 == 0:
            print(f"Generated {i + 1}/{n_samples} samples...")

        pair = generate_training_pair()
        samples.append(pair)

    print(f"\n[OK] Generated {len(samples)} samples")
    return samples

def save_dataset(samples, output_file):
    """Save dataset to file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as JSONL (one JSON per line)
    with open(output_path, 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    print(f"[OK] Saved to: {output_path}")

    # Also save first 10 as preview
    preview_file = output_path.parent / "synthetic_data_preview.txt"
    with open(preview_file, 'w', encoding='utf-8') as f:
        f.write("SYNTHETIC TRAINING DATA PREVIEW\n")
        f.write("=" * 80 + "\n\n")
        for i, sample in enumerate(samples[:10], 1):
            f.write(f"Sample {i}:\n")
            f.write(f"Text: {sample['text']}\n")
            f.write(f"Spec: {json.dumps(sample['spec'])}\n")
            f.write("-" * 80 + "\n")

    print(f"[OK] Preview saved to: {preview_file}")

def main():
    """Generate synthetic training data."""
    # Generate 2000 samples
    samples = generate_dataset(n_samples=2000)

    # Save to file
    output_file = "data/nlp_training/synthetic_train_2000.jsonl"
    save_dataset(samples, output_file)

    # Print statistics
    print("\n" + "=" * 80)
    print("DATASET STATISTICS")
    print("=" * 80)
    print(f"Total samples: {len(samples)}")

    bedroom_counts = {}
    bathroom_counts = {}
    for sample in samples:
        spec = sample['spec']
        bedrooms = spec['bedrooms']
        bathrooms = spec['bathrooms']
        bedroom_counts[bedrooms] = bedroom_counts.get(bedrooms, 0) + 1
        bathroom_counts[bathrooms] = bathroom_counts.get(bathrooms, 0) + 1

    print(f"\nBedroom distribution:")
    for br in sorted(bedroom_counts.keys()):
        print(f"  {br}BR: {bedroom_counts[br]} samples")

    print(f"\nBathroom distribution:")
    for ba in sorted(bathroom_counts.keys()):
        print(f"  {ba}BA: {bathroom_counts[ba]} samples")

    print("\n[SUCCESS] Synthetic data generation complete!")

if __name__ == "__main__":
    main()
