"""
Text Description Generator
Generates natural language descriptions for floor plan layouts
"""

import json
from pathlib import Path
from typing import Dict, List
import random

# Template-based description generation
TEMPLATES = [
    "A {size} {style} house with {bedrooms} bedrooms and {bathrooms} bathrooms",
    "A {style} home featuring {bedrooms} bedrooms, {bathrooms} bathrooms, and a {special_room}",
    "{bedrooms}-bedroom, {bathrooms}-bathroom {style} house",
    "Modern {bedrooms}BR/{bathrooms}BA {style} residence with {special_features}",
    "Spacious {bedrooms}-bedroom house with {bathrooms} bathrooms and {extra_features}",
]

SIZE_MAPPING = {
    (0, 80): "small",
    (80, 150): "medium-sized",
    (150, 250): "large",
    (250, 1000): "spacious"
}

STYLE_OPTIONS = ["modern", "traditional", "contemporary", "classic", "minimalist"]

def count_room_types(rooms: List[Dict]) -> Dict[str, int]:
    """Count occurrences of each room type"""
    counts = {}
    for room in rooms:
        room_type = room.get('type', 'unknown')
        counts[room_type] = counts.get(room_type, 0) + 1
    return counts

def determine_size(total_area: float) -> str:
    """Determine size descriptor based on total area"""
    for (min_area, max_area), size in SIZE_MAPPING.items():
        if min_area <= total_area < max_area:
            return size
    return "average"

def get_special_features(room_counts: Dict[str, int]) -> List[str]:
    """Extract special features from room counts"""
    features = []
    
    if room_counts.get('garage', 0) > 0:
        features.append(f"{room_counts['garage']}-car garage")
    
    if room_counts.get('balcony', 0) > 0:
        features.append("balcony")
    
    if room_counts.get('storage', 0) > 0:
        features.append("storage room")
    
    if room_counts.get('dining_room', 0) > 0:
        features.append("separate dining room")
    
    return features

def generate_description_template(layout: Dict) -> str:
    """
    Generate text description using templates
    
    Args:
        layout: Processed layout dict with 'rooms' and 'metadata'
    
    Returns:
        Natural language description string
    """
    rooms = layout.get('rooms', [])
    metadata = layout.get('metadata', {})
    
    room_counts = count_room_types(rooms)
    total_area = metadata.get('total_area', 0)
    
    # Extract key information
    bedrooms = room_counts.get('bedroom', 0)
    bathrooms = room_counts.get('bathroom', 0)
    size = determine_size(total_area)
    style = random.choice(STYLE_OPTIONS)
    
    # Get special features
    features = get_special_features(room_counts)
    special_room = features[0] if features else "living room"
    special_features = ", ".join(features) if features else "open floor plan"
    extra_features = " and ".join(features[:2]) if len(features) >= 2 else "spacious layout"
    
    # Choose template
    template = random.choice(TEMPLATES)
    
    # Fill template
    description = template.format(
        size=size,
        style=style,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        special_room=special_room,
        special_features=special_features,
        extra_features=extra_features
    )
    
    return description

def generate_structured_spec(layout: Dict) -> Dict:
    """
    Generate structured specification from layout
    This is the target format for NLP training
    
    Output format matches Module 1 JSON spec
    """
    rooms = layout.get('rooms', [])
    room_counts = count_room_types(rooms)
    
    # Convert to spec format
    spec_rooms = []
    for room_type, count in room_counts.items():
        # Get average area for this room type
        room_areas = [r['area'] for r in rooms if r['type'] == room_type]
        avg_area = sum(room_areas) / len(room_areas) if room_areas else 0
        
        spec_rooms.append({
            'type': room_type,
            'count': count,
            'area': round(avg_area, 1)
        })
    
    return {
        'rooms': spec_rooms,
        'metadata': layout.get('metadata', {})
    }

def create_text_pairs(
    input_dir: str,
    output_dir: str,
    use_templates: bool = True,
    num_samples: int = None
):
    """
    Create text-spec pairs for NLP training
    
    Args:
        input_dir: Directory with processed layouts
        output_dir: Where to save text pairs
        use_templates: If True, use templates. If False, requires GPT-4
        num_samples: Limit number of samples to process
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load all layouts
    layouts = []
    for json_file in input_path.glob('*.json'):
        with open(json_file, 'r') as f:
            layouts.append(json.load(f))
    
    if num_samples:
        layouts = layouts[:num_samples]
    
    print(f"Generating text descriptions for {len(layouts)} layouts...")
    
    text_pairs = []
    
    for i, layout in enumerate(layouts):
        if i % 50 == 0:
            print(f"Processing {i}/{len(layouts)}...")
        
        # Generate text description
        if use_templates:
            text = generate_description_template(layout)
        else:
            # TODO: Implement GPT-4 generation
            text = "GPT-4 generation not implemented yet"
        
        # Generate structured spec
        spec = generate_structured_spec(layout)
        
        # Create pair
        pair = {
            'text': text,
            'spec': spec,
            'layout_id': layout.get('id', 'unknown')
        }
        
        text_pairs.append(pair)
    
    # Save as JSONL
    output_file = output_path / 'text_pairs.jsonl'
    with open(output_file, 'w') as f:
        for pair in text_pairs:
            f.write(json.dumps(pair) + '\n')
    
    print(f"\nSaved {len(text_pairs)} text-spec pairs to {output_file}")
    
    # Save a few examples for inspection
    examples_file = output_path / 'examples.json'
    with open(examples_file, 'w') as f:
        json.dump(text_pairs[:10], f, indent=2)
    
    print(f"Saved 10 examples to {examples_file}")

if __name__ == "__main__":
    INPUT_DIR = "datasets/processed/layouts"
    OUTPUT_DIR = "datasets/processed/text_pairs"
    
    # Generate text descriptions for first 100 layouts
    create_text_pairs(INPUT_DIR, OUTPUT_DIR, use_templates=True, num_samples=100)
