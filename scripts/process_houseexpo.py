"""
HouseExpo Dataset Processor
Converts HouseExpo JSON format to standardized training format
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

def load_houseexpo_json(json_path: str) -> Dict:
    """Load HouseExpo JSON file"""
    with open(json_path, 'r') as f:
        return json.load(f)

def extract_rooms_from_houseexpo(data: Dict) -> List[Dict]:
    """
    Extract room information from HouseExpo format
    HouseExpo uses vertex-based representation
    """
    rooms = []
    
    # HouseExpo format has 'vertices' and 'edges'
    vertices = data.get('vertices', [])
    
    if not vertices:
        return rooms
    
    # Group vertices by room (simplified - may need adjustment)
    # HouseExpo typically has room type indicators
    for i, vertex in enumerate(vertices):
        # Extract basic room info
        room_info = {
            'id': f"room_{i}",
            'type': classify_room_type(vertex),
            'coordinates': vertex.get('coordinates', []),
            'area': calculate_polygon_area(vertex.get('coordinates', []))
        }
        rooms.append(room_info)
    
    return rooms

def classify_room_type(vertex: Dict) -> str:
    """
    Classify room type based on vertex data
    Map to standard types: bedroom, bathroom, kitchen, living_room, etc.
    """
    # This is a placeholder - actual implementation depends on HouseExpo format
    room_type = vertex.get('type', 'unknown')
    
    # Standardize room types
    type_mapping = {
        'bed': 'bedroom',
        'bath': 'bathroom',
        'kit': 'kitchen',
        'liv': 'living_room',
        'din': 'dining_room',
        'hall': 'hallway',
        'ent': 'entrance',
        'bal': 'balcony',
        'sto': 'storage'
    }
    
    for key, standard_type in type_mapping.items():
        if key in room_type.lower():
            return standard_type
    
    return 'unknown'

def calculate_polygon_area(coordinates: List[Tuple[float, float]]) -> float:
    """Calculate area of polygon using shoelace formula"""
    if len(coordinates) < 3:
        return 0.0
    
    x = [coord[0] for coord in coordinates]
    y = [coord[1] for coord in coordinates]
    
    return 0.5 * abs(sum(x[i] * y[i+1] - x[i+1] * y[i] for i in range(-1, len(x)-1)))

def process_houseexpo_file(json_path: Path) -> Dict:
    """
    Process single HouseExpo JSON file to standard format
    
    Output format:
    {
        'id': 'houseexpo_00001',
        'source': 'houseexpo',
        'rooms': [
            {'type': 'bedroom', 'area': 12.5, 'bbox': [x1, y1, x2, y2]},
            ...
        ],
        'metadata': {
            'total_area': 145.0,
            'room_count': 5
        }
    }
    """
    try:
        data = load_houseexpo_json(str(json_path))
        rooms = extract_rooms_from_houseexpo(data)
        
        # Filter out unknown/invalid rooms
        valid_rooms = [r for r in rooms if r['type'] != 'unknown' and r['area'] > 0]
        
        return {
            'id': f"houseexpo_{json_path.stem}",
            'source': 'houseexpo',
            'rooms': valid_rooms,
            'metadata': {
                'total_area': sum(r['area'] for r in valid_rooms),
                'room_count': len(valid_rooms),
                'original_file': str(json_path)
            }
        }
    except Exception as e:
        print(f"Error processing {json_path}: {e}")
        return None

def process_all_houseexpo(
    input_dir: str, 
    output_dir: str,
    limit: int = None
) -> Tuple[int, int]:
    """
    Process all HouseExpo JSON files
    
    Args:
        input_dir: Path to HouseExpo json folder
        output_dir: Path to save processed JSONs
        limit: Optional limit on number of files to process
    
    Returns:
        (successful_count, failed_count)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all JSON files
    json_files = list(input_path.rglob('*.json'))
    
    if limit:
        json_files = json_files[:limit]
    
    print(f"Found {len(json_files)} JSON files to process")
    
    successful = 0
    failed = 0
    
    for i, json_file in enumerate(json_files):
        if i % 100 == 0:
            print(f"Processing {i}/{len(json_files)}...")
        
        processed = process_houseexpo_file(json_file)
        
        if processed:
            # Save to output
            output_file = output_path / f"{processed['id']}.json"
            with open(output_file, 'w') as f:
                json.dump(processed, f, indent=2)
            successful += 1
        else:
            failed += 1
    
    print(f"\nProcessing complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    return successful, failed

if __name__ == "__main__":
    # Configuration
    HOUSEEXPO_DIR = "datasets/raw/HouseExpo/json"
    OUTPUT_DIR = "datasets/processed/layouts"
    
    # Process first 100 files for testing
    print("Processing HouseExpo dataset...")
    process_all_houseexpo(HOUSEEXPO_DIR, OUTPUT_DIR, limit=100)
    
    print("\nDone! Check datasets/processed/layouts/ for results")
