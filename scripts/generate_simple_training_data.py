"""
Generate simplified text-spec training pairs for T5 model.
Output format matches what the BIM generator expects.
"""

import json
import random
from pathlib import Path

def generate_training_pairs(num_samples=500):
    """Generate simple text-spec pairs."""

    styles = ["modern", "contemporary", "classic", "traditional", "minimalist"]
    pairs = []

    for i in range(num_samples):
        # Random room counts
        bedrooms = random.randint(1, 5)
        bathrooms = random.randint(1, 3)
        has_kitchen = True  # Always have kitchen
        has_living_room = random.choice([True, True, True, False])  # 75% chance
        has_dining_room = random.choice([True, True, False, False])  # 50% chance
        has_study = random.choice([True, False, False, False])  # 25% chance
        has_garage = random.choice([True, False, False])  # 33% chance
        style = random.choice(styles)

        # Calculate approximate area
        total_area = (bedrooms * 12) + (bathrooms * 5) + 15  # kitchen
        if has_living_room:
            total_area += 20
        if has_dining_room:
            total_area += 12
        if has_study:
            total_area += 10
        if has_garage:
            total_area += 20

        # Generate natural language text (multiple variations)
        text_templates = [
            f"A {style} {bedrooms}-bedroom house with {bathrooms} bathroom{'s' if bathrooms > 1 else ''}",
            f"A {style} home with {bedrooms} bedrooms and {bathrooms} bathroom{'s' if bathrooms > 1 else ''}",
            f"{bedrooms}BR/{bathrooms}BA {style} house",
            f"A {style} {bedrooms}-bedroom residence with {bathrooms} bath{'s' if bathrooms > 1 else ''}",
        ]

        # Add optional rooms to text
        optional_parts = []
        if has_living_room:
            optional_parts.append("living room")
        if has_dining_room:
            optional_parts.append("dining room")
        if has_kitchen:
            optional_parts.append("kitchen")
        if has_study:
            optional_parts.append("study")
        if has_garage:
            optional_parts.append("garage")

        text = random.choice(text_templates)
        if optional_parts and random.random() > 0.3:  # 70% chance to add details
            if len(optional_parts) > 1:
                parts_text = ", ".join(optional_parts[:-1]) + " and " + optional_parts[-1]
            else:
                parts_text = optional_parts[0]
            text += f", {parts_text}"

        # Create JSON spec (simple flat format)
        spec = {
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "kitchen": has_kitchen,
            "living_room": has_living_room,
            "dining_room": has_dining_room,
            "study": has_study,
            "garage": has_garage,
            "total_area_sqm": total_area,
            "style": style
        }

        pairs.append({
            "text": text,
            "spec": spec
        })

    return pairs

def main():
    print("Generating simplified training data...")

    # Generate pairs
    pairs = generate_training_pairs(num_samples=600)

    # Save to JSONL
    output_dir = Path("datasets/processed/text_pairs")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "simple_pairs.jsonl"

    with open(output_file, 'w') as f:
        for pair in pairs:
            f.write(json.dumps(pair) + '\n')

    print(f"[OK] Generated {len(pairs)} training pairs")
    print(f"  Saved to: {output_file}")

    # Show examples
    print("\nExample pairs:")
    print("="*80)
    for i, pair in enumerate(pairs[:5], 1):
        print(f"\n{i}. Text: {pair['text']}")
        print(f"   Spec: {json.dumps(pair['spec'], indent=2)}")

if __name__ == "__main__":
    main()
