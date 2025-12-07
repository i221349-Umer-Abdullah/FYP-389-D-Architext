"""
Generate text-spec pairs from CubiCasa5k processed layouts
For training the Text-to-Spec AI
"""

import json
import random
from pathlib import Path
from typing import Dict, List

# Style templates
STYLES = ['modern', 'traditional', 'contemporary', 'minimalist', 'classic']

# Size descriptors mapped to area ranges
SIZE_MAP = {
    (0, 6): 'small',
    (6, 12): 'medium-sized',
    (12, 20): 'spacious',
    (20, 999): 'large'
}

def get_size_descriptor(area: float) -> str:
    for (low, high), desc in SIZE_MAP.items():
        if low <= area < high:
            return desc
    return 'medium-sized'

def count_rooms_by_type(rooms: List[Dict]) -> Dict[str, int]:
    """Count rooms by type"""
    counts = {}
    for room in rooms:
        t = room['type']
        counts[t] = counts.get(t, 0) + 1
    return counts

def generate_text_description(layout: Dict) -> str:
    """Generate natural language description from layout"""
    rooms = layout['rooms']
    counts = count_rooms_by_type(rooms)
    total_area = layout['metadata']['total_area']
    
    # Pick a random style
    style = random.choice(STYLES)
    
    # Build description
    parts = []
    
    # Intro
    intros = [
        f"A {style} home",
        f"A {get_size_descriptor(total_area)} {style} house",
        f"A {style} residential layout",
        f"This {style} floor plan features"
    ]
    parts.append(random.choice(intros))
    
    # Bedrooms
    bedrooms = counts.get('bedroom', 0)
    if bedrooms > 0:
        if bedrooms == 1:
            parts.append("with 1 bedroom")
        else:
            parts.append(f"with {bedrooms} bedrooms")
    
    # Bathrooms
    bathrooms = counts.get('bathroom', 0)
    if bathrooms > 0:
        if bathrooms == 1:
            parts.append("and 1 bathroom")
        else:
            parts.append(f"and {bathrooms} bathrooms")
    
    # Other rooms
    other_rooms = []
    if counts.get('living_room', 0) > 0:
        other_rooms.append("living room")
    if counts.get('kitchen', 0) > 0:
        other_rooms.append("kitchen")
    if counts.get('dining_room', 0) > 0:
        other_rooms.append("dining area")
    if counts.get('study', 0) > 0:
        other_rooms.append("study")
    if counts.get('closet', 0) > 0:
        other_rooms.append("closet space")
    if counts.get('entrance', 0) > 0:
        other_rooms.append("entrance hall")
    if counts.get('balcony', 0) > 0 or counts.get('outdoor', 0) > 0:
        other_rooms.append("outdoor space")
    
    if other_rooms:
        if len(other_rooms) == 1:
            parts.append(f"including a {other_rooms[0]}")
        else:
            listed = ', '.join(other_rooms[:-1]) + f" and {other_rooms[-1]}"
            parts.append(f"including {listed}")
    
    # Area
    parts.append(f"totaling approximately {int(total_area)} square meters")
    
    return ' '.join(parts) + '.'

def generate_spec(layout: Dict) -> Dict:
    """Generate structured spec from layout"""
    rooms = layout['rooms']
    counts = count_rooms_by_type(rooms)
    
    return {
        'bedrooms': counts.get('bedroom', 0),
        'bathrooms': counts.get('bathroom', 0),
        'living_room': counts.get('living_room', 0) > 0,
        'kitchen': counts.get('kitchen', 0) > 0,
        'dining_room': counts.get('dining_room', 0) > 0,
        'study': counts.get('study', 0) > 0,
        'total_rooms': layout['metadata']['total_rooms'],
        'total_area_sqm': layout['metadata']['total_area'],
        'style': random.choice(STYLES)
    }

def process_layouts(
    layouts_dir: str,
    output_file: str,
    limit: int = None
) -> int:
    """
    Generate text-spec pairs from processed layouts
    
    Returns: number of pairs generated
    """
    layouts_path = Path(layouts_dir)
    layout_files = list(layouts_path.glob('*.json'))
    
    if limit:
        layout_files = layout_files[:limit]
    
    print(f"Processing {len(layout_files)} layouts...")
    
    pairs = []
    
    for layout_file in layout_files:
        with open(layout_file) as f:
            layout = json.load(f)
        
        # Skip layouts with too few rooms
        if layout['metadata']['total_rooms'] < 3:
            continue
        
        text = generate_text_description(layout)
        spec = generate_spec(layout)
        
        pairs.append({
            'text': text,
            'spec': spec,
            'source_id': layout['id']
        })
    
    # Save as JSONL
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for pair in pairs:
            f.write(json.dumps(pair) + '\n')
    
    print(f"\nGenerated {len(pairs)} text-spec pairs")
    print(f"Saved to: {output_file}")
    
    # Show samples
    print("\nSample pairs:")
    for i, pair in enumerate(random.sample(pairs, min(3, len(pairs)))):
        print(f"\n--- Sample {i+1} ---")
        print(f"Text: {pair['text']}")
        print(f"Spec: {json.dumps(pair['spec'], indent=2)}")
    
    return len(pairs)

if __name__ == "__main__":
    LAYOUTS_DIR = "datasets/processed/cubicasa_layouts"
    OUTPUT_FILE = "datasets/processed/text_pairs/cubicasa_pairs.jsonl"
    
    print("Generating text-spec pairs from CubiCasa5k layouts...")
    process_layouts(LAYOUTS_DIR, OUTPUT_FILE)
