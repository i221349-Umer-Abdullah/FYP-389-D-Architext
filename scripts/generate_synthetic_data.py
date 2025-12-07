"""
Synthetic Floor Plan Generator
Generates variations of floor plans for training
"""

import json
import random
from pathlib import Path
from typing import Dict, List

# Room type definitions
ROOM_TYPES = {
    'bedroom': {'min_area': 9, 'max_area': 20, 'typical': 12},
    'bathroom': {'min_area': 3, 'max_area': 8, 'typical': 5},
    'kitchen': {'min_area': 8, 'max_area': 15, 'typical': 10},
    'living_room': {'min_area': 15, 'max_area': 35, 'typical': 22},
    'dining_room': {'min_area': 8, 'max_area': 15, 'typical': 10},
    'garage': {'min_area': 18, 'max_area': 40, 'typical': 25},
    'hallway': {'min_area': 3, 'max_area': 8, 'typical': 5},
    'storage': {'min_area': 2, 'max_area': 6, 'typical': 3},
    'balcony': {'min_area': 4, 'max_area': 12, 'typical': 6},
}

def generate_room(room_type: str, room_id: int) -> Dict:
    """Generate a single room with randomized parameters"""
    specs = ROOM_TYPES[room_type]
    
    # Random area within range
    area = random.uniform(specs['min_area'], specs['max_area'])
    
    # Simple bounding box (assuming square-ish rooms)
    # Width and height that approximate the area
    aspect_ratio = random.uniform(0.7, 1.4)  # Not too elongated
    width = (area * aspect_ratio) ** 0.5
    height = area / width
    
    # Random position (we'll place in a grid later)
    x = random.uniform(0, 100)
    y = random.uniform(0, 100)
    
    return {
        'id': room_id,
        'type': room_type,
        'area': round(area, 2),
        'bbox': [
            round(x, 2),
            round(y, 2),
            round(x + width, 2),
            round(y + height, 2)
        ]
    }

def generate_house_layout(
    bedrooms: int = None,
    bathrooms: int = None,
    include_garage: bool = None,
    include_balcony: bool = None
) -> Dict:
    """
    Generate a complete house layout
    
    Args:
        bedrooms: Number of bedrooms (random if None)
        bathrooms: Number of bathrooms (random if None)
        include_garage: Include garage (random if None)
        include_balcony: Include balcony (random if None)
    
    Returns:
        Layout dict in RPLAN-like format
    """
    # Randomize if not specified
    if bedrooms is None:
        bedrooms = random.randint(2, 4)
    if bathrooms is None:
        bathrooms = random.randint(1, min(bedrooms, 3))
    if include_garage is None:
        include_garage = random.random() > 0.3  # 70% have garage
    if include_balcony is None:
        include_balcony = random.random() > 0.5  # 50% have balcony
    
    rooms = []
    room_id = 0
    
    # Always include: bedrooms, bathrooms, kitchen, living room
    for i in range(bedrooms):
        rooms.append(generate_room('bedroom', room_id))
        room_id += 1
    
    for i in range(bathrooms):
        rooms.append(generate_room('bathroom', room_id))
        room_id += 1
    
    rooms.append(generate_room('kitchen', room_id))
    room_id += 1
    
    rooms.append(generate_room('living_room', room_id))
    room_id += 1
    
    # Optional rooms
    if bedrooms >= 3 or random.random() > 0.5:
        rooms.append(generate_room('dining_room', room_id))
        room_id += 1
    
    if include_garage:
        rooms.append(generate_room('garage', room_id))
        room_id += 1
    
    if include_balcony:
        rooms.append(generate_room('balcony', room_id))
        room_id += 1
    
    # Hallway for larger houses
    if len(rooms) >= 6:
        rooms.append(generate_room('hallway', room_id))
        room_id += 1
    
    # Storage for some houses
    if random.random() > 0.6:
        rooms.append(generate_room('storage', room_id))
        room_id += 1
    
    return {
        'rooms': rooms,
        'metadata': {
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'has_garage': include_garage,
            'has_balcony': include_balcony,
            'total_rooms': len(rooms),
            'total_area': sum(r['area'] for r in rooms)
        }
    }

def generate_synthetic_dataset(
    num_samples: int = 500,
    output_dir: str = "datasets/processed/layouts"
):
    """
    Generate a complete synthetic dataset
    
    Args:
        num_samples: Number of floor plans to generate
        output_dir: Where to save the generated layouts
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {num_samples} synthetic floor plans...")
    
    # Common house configurations
    configurations = [
        {'bedrooms': 2, 'bathrooms': 1, 'include_garage': False},
        {'bedrooms': 3, 'bathrooms': 2, 'include_garage': True},
        {'bedrooms': 4, 'bathrooms': 2, 'include_garage': True},
        {'bedrooms': 3, 'bathrooms': 1, 'include_garage': False},
        {'bedrooms': 4, 'bathrooms': 3, 'include_garage': True},
    ]
    
    generated = 0
    
    for i in range(num_samples):
        if i % 100 == 0:
            print(f"Generated {i}/{num_samples}...")
        
        # Mix of predefined configs and random
        if random.random() > 0.3:
            # Use predefined config
            config = random.choice(configurations)
            layout = generate_house_layout(**config)
        else:
            # Completely random
            layout = generate_house_layout()
        
        # Add ID and source
        layout['id'] = f"synthetic_{i:05d}"
        layout['source'] = 'synthetic'
        
        # Save to file
        output_file = output_path / f"synthetic_{i:05d}.json"
        with open(output_file, 'w') as f:
            json.dump(layout, f, indent=2)
        
        generated += 1
    
    print(f"\n✓ Generated {generated} synthetic floor plans")
    print(f"Saved to: {output_dir}")
    
    # Generate summary statistics
    total_area = 0
    room_counts = {}
    
    for json_file in output_path.glob('synthetic_*.json'):
        with open(json_file) as f:
            data = json.load(f)
            total_area += data['metadata']['total_area']
            for room in data['rooms']:
                room_type = room['type']
                room_counts[room_type] = room_counts.get(room_type, 0) + 1
    
    print(f"\nDataset Statistics:")
    print(f"Average house size: {total_area / generated:.1f} sqm")
    print(f"Room type distribution:")
    for room_type, count in sorted(room_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {room_type}: {count}")

if __name__ == "__main__":
    # Generate synthetic dataset
    generate_synthetic_dataset(num_samples=500)
