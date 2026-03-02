"""
=============================================================================
ArchiText: ResPlan-Aligned NLP Training Data Generator
=============================================================================

Generates diverse text → spec training pairs for the T5 NLP model (Layer 1).

KEY IMPROVEMENT over the old generator:
  - Spec format now uses ResPlan's exact 13 room types as keys
  - Includes realistic net_area values (in m²)
  - Includes unit_type (house / apartment / villa / etc.)
  - Pakistani/South-Asian context phrases added for localisation
  - Output spec maps directly to the Layer 2 condition vector

Output spec format:
    {
        "unit_type": "apartment",          # one of UNIT_TYPES
        "net_area": 120,                   # m²
        "bedroom": 3,
        "bathroom": 2,
        "living": 1,
        "kitchen": 1,
        "balcony": 1,
        "storage": 0,
        "parking": 0,
        "garden": 0,
        "pool": 0,
        "stair": 0,
        "veranda": 0,
        "inner": 1
    }

Usage:
    python scripts/generate_resplan_training_data.py
    # Outputs: datasets/processed/text_pairs/resplan_pairs.jsonl
              datasets/processed/text_pairs/resplan_pairs_preview.txt
=============================================================================
"""

import json
import random
import sys
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── ResPlan types ──────────────────────────────────────────────────────────────
RESPLAN_ROOM_TYPES = [
    "bedroom", "bathroom", "living", "kitchen",
    "balcony", "storage", "parking", "garden",
    "pool", "stair", "veranda", "inner",
]

UNIT_TYPES = ["house", "apartment", "villa", "commercial", "other"]

# ── Vocabulary ─────────────────────────────────────────────────────────────────
ADJECTIVES = [
    "modern", "contemporary", "spacious", "cozy", "luxury", "elegant",
    "comfortable", "stylish", "compact", "traditional", "classic",
    "sophisticated", "bright", "well-designed", "minimalist", "warm",
    "affordable", "premium", "smart", "beautiful", "functional",
]
UNIT_WORDS = {
    "house":       ["house", "home", "bungalow", "residence", "property"],
    "apartment":   ["apartment", "flat", "unit", "condo", "penthouse"],
    "villa":       ["villa", "farmhouse", "estate", "manor"],
    "commercial":  ["commercial space", "office", "shop"],
    "other":       ["property", "unit", "space"],
}
AREA_PHRASES = [
    "approximately {area} square metres",
    "around {area} sqm",
    "roughly {area} m²",
    "{area} square metres of living space",
    "{area}sqm",
    "about {area} sq meters",
]
LOCAL_PHRASES = [
    "in a gated community",
    "in a society",
    "with servant quarters",
    "with a separate servant room",
    "in DHA style",
    "in Bahria Town style",
    "with a drawing room",
    "suitable for a joint family",
    "ideal for a nuclear family",
    "with a gate and boundary wall",
    "with marble flooring",
    "with a car porch",
    "near amenities",
]
GENERIC_PHRASES = [
    "with an open floor plan",
    "with modern fixtures",
    "with high ceilings",
    "with plenty of natural light",
    "perfect for families",
    "ideal for entertaining",
    "with a functional layout",
    "in a prime location",
    "move-in ready",
    "fully furnished",
]


# ── Spec generator ─────────────────────────────────────────────────────────────
def generate_spec() -> dict:
    """Generate a realistic room spec aligned with ResPlan condition format."""
    unit_type = random.choices(
        UNIT_TYPES,
        weights=[0.40, 0.35, 0.10, 0.05, 0.10],
    )[0]

    # Bedroom count drives everything else
    if unit_type == "apartment":
        bedrooms = random.choices([1, 2, 3, 4],   weights=[0.20, 0.40, 0.30, 0.10])[0]
    elif unit_type == "villa":
        bedrooms = random.choices([3, 4, 5, 6],   weights=[0.20, 0.35, 0.30, 0.15])[0]
    else:
        bedrooms = random.choices([1, 2, 3, 4, 5], weights=[0.10, 0.25, 0.35, 0.20, 0.10])[0]

    bathrooms = max(1, min(bedrooms, random.randint(1, bedrooms + 1)))

    # Net area: realistic range per unit type and bedroom count
    base_area = {
        "apartment": 45 + bedrooms * 22,
        "house":     60 + bedrooms * 28,
        "villa":     150 + bedrooms * 35,
        "commercial": 40 + random.randint(0, 200),
        "other":     50 + bedrooms * 20,
    }[unit_type]
    net_area = base_area + random.randint(-20, 40)
    net_area = max(25, round(net_area / 5) * 5)  # snap to 5m² intervals

    spec = {
        "unit_type":  unit_type,
        "net_area":   net_area,
        "bedroom":    bedrooms,
        "bathroom":   bathrooms,
        "living":     1,     # always 1 living room
        "kitchen":    1,     # always 1 kitchen
        "balcony":    0,
        "storage":    0,
        "parking":    0,
        "garden":     0,
        "pool":       0,
        "stair":      0,
        "veranda":    0,
        "inner":      0,
    }

    # Probabilistic extras
    if unit_type in ("house", "villa"):
        if random.random() > 0.3:  spec["balcony"]  = random.randint(1, 2)
        if random.random() > 0.4:  spec["veranda"]  = 1
        if random.random() > 0.5:  spec["garden"]   = 1
        if random.random() > 0.5:  spec["parking"]  = random.randint(1, 2)
        if random.random() > 0.6:  spec["storage"]  = 1
        if unit_type == "villa":
            if random.random() > 0.6: spec["pool"]  = 1
            spec["stair"]  = 1  # villas almost always have stairs
        if bedrooms >= 3:
            spec["inner"]  = 1  # inner hall/corridor
    elif unit_type == "apartment":
        if random.random() > 0.4:  spec["balcony"]  = 1
        if random.random() > 0.7:  spec["storage"]  = 1
        if random.random() > 0.6:  spec["parking"]  = 1
        if bedrooms >= 3:
            spec["inner"]  = 1

    return spec


# ── Text generators ────────────────────────────────────────────────────────────
def _room_phrase(spec: dict) -> str:
    """Compose a readable list of extra rooms beyond bedroom/bathroom."""
    extras = []
    if spec["living"] > 0:
        extras.append("living room" if random.random() > 0.4 else "lounge")
    if spec["kitchen"] > 0:
        extras.append("kitchen" if random.random() > 0.5 else "fitted kitchen")
    if spec["balcony"] > 0:
        n = spec["balcony"]
        extras.append(f"{n} balcon{'y' if n == 1 else 'ies'}")
    if spec["veranda"] > 0:
        extras.append("veranda")
    if spec["garden"] > 0:
        extras.append("garden")
    if spec["pool"] > 0:
        extras.append("swimming pool")
    if spec["parking"] > 0:
        n = spec["parking"]
        extras.append(f"{n}-car parking" if n > 1 else "parking")
    if spec["storage"] > 0:
        extras.append("storage room")
    if spec["stair"] > 0:
        extras.append("staircase")
    return extras


def _join(items):
    if not items: return ""
    if len(items) == 1: return items[0]
    if len(items) == 2: return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def template_formal(spec: dict) -> str:
    adj      = random.choice(ADJECTIVES)
    unit     = random.choice(UNIT_WORDS[spec["unit_type"]])
    bed, bath = spec["bedroom"], spec["bathroom"]
    text = f"A {adj} {bed}-bedroom {unit} with {bath} bathroom{'s' if bath>1 else ''}"
    extras = _room_phrase(spec)
    if extras:
        text += f", {_join(extras)}"
    if random.random() > 0.5:
        area = spec["net_area"]
        text += f". Total area: " + random.choice(AREA_PHRASES).format(area=area)
    if random.random() > 0.6:
        text += ". " + random.choice(LOCAL_PHRASES + GENERIC_PHRASES)
    return text.strip()


def template_brief(spec: dict) -> str:
    bed, bath = spec["bedroom"], spec["bathroom"]
    unit = random.choice(UNIT_WORDS[spec["unit_type"]])
    styles = [
        f"{bed}BR/{bath}BA {unit}",
        f"{bed} bed {bath} bath {unit}",
        f"{bed}BHK {unit}",
        f"{bed}-bed {unit}",
    ]
    text = random.choice(styles)
    if spec["net_area"] and random.random() > 0.4:
        text += f" ~{spec['net_area']}sqm"
    extras = _room_phrase(spec)
    if extras and random.random() > 0.4:
        text += " with " + _join(extras[:2])
    return text.strip()


def template_conversational(spec: dict) -> str:
    starters = [
        "I need a", "Design a", "Generate a", "Build a",
        "I want a", "Create a", "Show me a",
    ]
    adj   = random.choice(ADJECTIVES) if random.random() > 0.5 else ""
    unit  = random.choice(UNIT_WORDS[spec["unit_type"]])
    bed   = spec["bedroom"]
    bath  = spec["bathroom"]
    area  = spec["net_area"]

    parts = [random.choice(starters)]
    if adj: parts.append(adj)
    parts.append(f"{bed} bedroom {unit}")
    if random.random() > 0.3:
        parts.append(f"with {bath} bathroom{'s' if bath>1 else ''}")
    if random.random() > 0.5:
        area_str = random.choice(AREA_PHRASES).format(area=area)
        parts.append(area_str)
    extras = _room_phrase(spec)
    if extras:
        parts.append("featuring " + _join(extras[:3]))
    if random.random() > 0.6:
        parts.append(random.choice(LOCAL_PHRASES))
    return " ".join(parts).strip()


def template_paragraph(spec: dict) -> str:
    bed, bath  = spec["bedroom"], spec["bathroom"]
    unit       = random.choice(UNIT_WORDS[spec["unit_type"]])
    adj1, adj2 = random.sample(ADJECTIVES, 2)
    area       = spec["net_area"]
    text = (
        f"This {adj1} {bed}-bedroom {unit} offers a {adj2} layout "
        f"with {bath} full bathroom{'s' if bath>1 else ''}. "
    )
    extras = _room_phrase(spec)
    if extras:
        text += f"The property includes {_join(extras)}. "
    text += f"Total living area is {random.choice(AREA_PHRASES).format(area=area)}."
    if random.random() > 0.5:
        text += " " + random.choice(LOCAL_PHRASES + GENERIC_PHRASES).capitalize() + "."
    return text.strip()


def template_local(spec: dict) -> str:
    """South Asian / Pakistani real estate style."""
    bed, bath = spec["bedroom"], spec["bathroom"]
    marlas = round(spec["net_area"] / 25.2, 1)   # 1 marla ≈ 25.2 m²
    unit   = random.choice(UNIT_WORDS[spec["unit_type"]])

    styles = [
        f"{bed} bedroom {unit}, {marlas} marla, {bath} baths",
        f"{bed}BR {unit} in {marlas} marla plot with {bath} bathrooms",
        f"{marlas} marla {bed} bed {unit}, {bath} bath",
    ]
    text = random.choice(styles)
    extras = _room_phrase(spec)
    if extras and random.random() > 0.3:
        text += " + " + ", ".join(extras[:2])
    if random.random() > 0.5:
        text += ". " + random.choice(LOCAL_PHRASES)
    return text.strip()


def generate_pair() -> dict:
    spec = generate_spec()
    templates = [
        template_formal,
        template_brief,
        template_conversational,
        template_paragraph,
        template_local,
    ]
    text = random.choice(templates)(spec)
    return {"text": text, "spec": spec}


# ── Main ───────────────────────────────────────────────────────────────────────
def main(n_samples: int = 3000):
    print(f"Generating {n_samples} ResPlan-aligned training pairs...")

    pairs = [generate_pair() for _ in range(n_samples)]

    out_dir  = Path("datasets/processed/text_pairs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "resplan_pairs.jsonl"

    with open(out_file, 'w', encoding='utf-8') as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + '\n')
    print(f"Saved {len(pairs)} pairs -> {out_file}")

    # Preview
    preview_file = out_dir / "resplan_pairs_preview.txt"
    with open(preview_file, 'w', encoding='utf-8') as f:
        f.write("ResPlan-Aligned NLP Training Data Preview\n")
        f.write("=" * 80 + "\n\n")
        for i, p in enumerate(pairs[:15], 1):
            f.write(f"[{i}] Text:\n  {p['text']}\n")
            f.write(f"    Spec: {json.dumps(p['spec'])}\n\n")
    print(f"Preview  -> {preview_file}")

    # Stats
    print("\n── Statistics ──")
    unit_dist = {}
    bed_dist  = {}
    for p in pairs:
        s = p["spec"]
        unit_dist[s["unit_type"]] = unit_dist.get(s["unit_type"], 0) + 1
        bed_dist[s["bedroom"]]    = bed_dist.get(s["bedroom"], 0) + 1

    print("Unit types:")
    for k in sorted(unit_dist, key=lambda x: -unit_dist[x]):
        print(f"  {k:12}: {unit_dist[k]:4d} ({100*unit_dist[k]/n_samples:.0f}%)")
    print("Bedrooms:")
    for k in sorted(bed_dist):
        print(f"  {k}BR: {bed_dist[k]:4d} ({100*bed_dist[k]/n_samples:.0f}%)")

    pool_count     = sum(1 for p in pairs if p["spec"]["pool"] > 0)
    garden_count   = sum(1 for p in pairs if p["spec"]["garden"] > 0)
    balcony_count  = sum(1 for p in pairs if p["spec"]["balcony"] > 0)
    print(f"Extra rooms: pool={pool_count}, garden={garden_count}, balcony={balcony_count}")

    print("\nDone!")


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    main(n)
