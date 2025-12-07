"""
CubiCasa5k Dataset Processor - Fixed Version
Extracts room information from SVG annotations
"""

import json
import re
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET

# Room type mapping from CubiCasa labels (in class attributes)
CUBICASA_ROOM_MAP = {
    'livingroom': 'living_room',
    'bedroom': 'bedroom',
    'masterroom': 'bedroom',
    'secondroom': 'bedroom',
    'kitchen': 'kitchen',
    'bathroom': 'bathroom',
    'balcony': 'balcony',
    'entrance': 'entrance',
    'entry': 'entrance',
    'lobby': 'entrance',
    'dining': 'dining_room',
    'study': 'study',
    'storage': 'storage',
    'closet': 'closet',
    'walkin': 'closet',
    'corridor': 'hallway',
    'toilet': 'bathroom',
    'hall': 'hallway',
    'outdoor': 'outdoor',
    'userdefined': 'other',
    'undefined': 'other',
}

def parse_polygon_points(points_str: str) -> List[tuple]:
    """Parse SVG polygon points string into list of (x, y) tuples"""
    points = []
    # Match coordinate pairs like "723.76,720.04" or "723.76 720.04"
    pairs = re.findall(r'([\d.]+)[,\s]+([\d.]+)', points_str)
    for x, y in pairs:
        try:
            points.append((float(x), float(y)))
        except ValueError:
            continue
    return points

def calculate_polygon_area(points: List[tuple]) -> float:
    """Calculate area of polygon using shoelace formula"""
    n = len(points)
    if n < 3:
        return 0.0
    
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    
    return abs(area) / 2.0

def get_bounding_box(points: List[tuple]) -> List[float]:
    """Get bounding box from polygon points"""
    if not points:
        return [0, 0, 0, 0]
    
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    
    return [min(xs), min(ys), max(xs), max(ys)]

def extract_room_type(class_attr: str) -> str:
    """Extract room type from SVG class attribute"""
    if not class_attr:
        return 'unknown'
    
    # Split class into parts and check each
    parts = class_attr.lower().split()
    
    for part in parts:
        for key, value in CUBICASA_ROOM_MAP.items():
            if key in part:
                return value
    
    return 'unknown'

def parse_svg_rooms(svg_path: str) -> List[Dict]:
    """
    Parse CubiCasa SVG file to extract room information
    
    CubiCasa SVG structure:
    <g class="Space Bedroom">
        <polygon points="..."/>
        ...
    </g>
    """
    rooms = []
    
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # SVG namespace handling
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        
        room_id = 0
        
        # Find all <g> elements with "Space" in class
        for element in root.iter():
            tag = element.tag.replace('{http://www.w3.org/2000/svg}', '')
            
            if tag == 'g':
                class_attr = element.get('class', '')
                
                # Check if this is a Space (room) element
                if 'Space' in class_attr:
                    room_type = extract_room_type(class_attr)
                    
                    # Find polygon inside this group
                    for child in element:
                        child_tag = child.tag.replace('{http://www.w3.org/2000/svg}', '')
                        
                        if child_tag == 'polygon':
                            points_str = child.get('points', '')
                            points = parse_polygon_points(points_str)
                            
                            if points and len(points) >= 3:
                                area = calculate_polygon_area(points)
                                bbox = get_bounding_box(points)
                                
                                # Convert area from pixels^2 to approximate sqm
                                # Assume ~10 pixels per meter (rough approximation)
                                area_sqm = area / 10000
                                
                                if area_sqm > 1:  # Skip tiny areas
                                    rooms.append({
                                        'id': f"room_{room_id}",
                                        'type': room_type,
                                        'area': round(area_sqm, 2),
                                        'bbox': [round(b, 2) for b in bbox]
                                    })
                                    room_id += 1
                            
                            break  # Only take first polygon per Space group
    
    except Exception as e:
        print(f"Error parsing {svg_path}: {e}")
    
    return rooms

def process_cubicasa_sample(sample_dir: Path) -> Dict:
    """Process a single CubiCasa sample directory"""
    svg_file = sample_dir / 'model.svg'
    
    if not svg_file.exists():
        return None
    
    rooms = parse_svg_rooms(str(svg_file))
    
    if not rooms or len(rooms) < 2:
        return None
    
    # Filter out unknown rooms for the summary
    known_rooms = [r for r in rooms if r['type'] != 'unknown']
    
    # Count rooms by type
    room_counts = {}
    for r in rooms:
        t = r['type']
        room_counts[t] = room_counts.get(t, 0) + 1
    
    return {
        'id': f"cubicasa_{sample_dir.name}",
        'source': 'cubicasa5k',
        'rooms': rooms,
        'room_summary': room_counts,
        'metadata': {
            'total_rooms': len(rooms),
            'total_area': round(sum(r['area'] for r in rooms), 2),
            'original_path': str(sample_dir)
        }
    }

def process_cubicasa_dataset(
    input_dir: str,
    output_dir: str,
    limit: int = None
) -> tuple:
    """
    Process entire CubiCasa5k dataset
    
    Returns: (successful_count, failed_count)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all quality tiers
    quality_dirs = ['high_quality', 'high_quality_architectural', 'colorful']
    
    all_samples = []
    for quality_dir in quality_dirs:
        quality_path = input_path / quality_dir
        if quality_path.exists():
            for sample_dir in quality_path.iterdir():
                if sample_dir.is_dir():
                    all_samples.append(sample_dir)
    
    if limit:
        all_samples = all_samples[:limit]
    
    print(f"Found {len(all_samples)} samples to process")
    
    successful = 0
    failed = 0
    
    for i, sample_dir in enumerate(all_samples):
        if i % 100 == 0:
            print(f"Processing {i}/{len(all_samples)}...")
        
        result = process_cubicasa_sample(sample_dir)
        
        if result:
            output_file = output_path / f"{result['id']}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            successful += 1
        else:
            failed += 1
    
    print(f"\nProcessing complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    # Show sample output
    if successful > 0:
        sample_file = list(output_path.glob('*.json'))[0]
        with open(sample_file) as f:
            sample = json.load(f)
        print(f"\nSample output ({sample_file.name}):")
        print(f"  Rooms: {sample['room_summary']}")
        print(f"  Total area: {sample['metadata']['total_area']} sqm")
    
    return successful, failed

if __name__ == "__main__":
    CUBICASA_DIR = "D:/Work/Uni/FYP/Dataset/cubicasa5k"
    OUTPUT_DIR = "datasets/processed/cubicasa_layouts"
    
    print("Processing CubiCasa5k dataset...")
    process_cubicasa_dataset(CUBICASA_DIR, OUTPUT_DIR, limit=500)
