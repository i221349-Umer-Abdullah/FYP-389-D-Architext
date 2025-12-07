"""
Dataset Splitter
Creates train/validation/test splits from processed layouts
"""

import json
import random
from pathlib import Path
from typing import List, Dict

def load_processed_layouts(layout_dir: str) -> List[Dict]:
    """Load all processed layout JSON files"""
    layout_path = Path(layout_dir)
    layouts = []
    
    for json_file in layout_path.glob('*.json'):
        with open(json_file, 'r') as f:
            layouts.append(json.load(f))
    
    return layouts

def create_splits(
    layouts: List[Dict],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
) -> Dict[str, List[Dict]]:
    """
    Split layouts into train/val/test sets
    
    Args:
        layouts: List of processed layout dicts
        train_ratio: Proportion for training (default 70%)
        val_ratio: Proportion for validation (default 15%)
        test_ratio: Proportion for testing (default 15%)
        seed: Random seed for reproducibility
    
    Returns:
        Dictionary with 'train', 'val', 'test' keys
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.01, "Ratios must sum to 1"
    
    # Shuffle with seed
    random.seed(seed)
    shuffled = layouts.copy()
    random.shuffle(shuffled)
    
    n = len(shuffled)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    
    return {
        'train': shuffled[:train_end],
        'val': shuffled[train_end:val_end],
        'test': shuffled[val_end:]
    }

def save_jsonl(data: List[Dict], output_path: str):
    """Save data as JSONL (one JSON per line)"""
    with open(output_path, 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')

def create_dataset_splits(
    input_dir: str,
    output_dir: str,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15
):
    """
    Main function to create dataset splits
    
    Creates:
        - train.jsonl
        - val.jsonl
        - test.jsonl
        - metadata.json (statistics)
    """
    print("Loading processed layouts...")
    layouts = load_processed_layouts(input_dir)
    print(f"Found {len(layouts)} layouts")
    
    if len(layouts) == 0:
        print("No layouts found! Make sure to run process_houseexpo.py first")
        return
    
    print("\nCreating splits...")
    splits = create_splits(layouts, train_ratio, val_ratio, test_ratio)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save each split
    for split_name, split_data in splits.items():
        output_file = output_path / f"{split_name}.jsonl"
        save_jsonl(split_data, output_file)
        print(f"Saved {len(split_data)} samples to {output_file}")
    
    # Calculate and save metadata
    metadata = {
        'total_samples': len(layouts),
        'train_samples': len(splits['train']),
        'val_samples': len(splits['val']),
        'test_samples': len(splits['test']),
        'splits': {
            'train': train_ratio,
            'val': val_ratio,
            'test': test_ratio
        },
        'room_type_distribution': calculate_room_distribution(layouts)
    }
    
    metadata_path = output_path / 'metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nSaved metadata to {metadata_path}")
    print("\nDataset split complete!")
    print(f"Train: {len(splits['train'])} ({train_ratio*100}%)")
    print(f"Val: {len(splits['val'])} ({val_ratio*100}%)")
    print(f"Test: {len(splits['test'])} ({test_ratio*100}%)")

def calculate_room_distribution(layouts: List[Dict]) -> Dict[str, int]:
    """Calculate distribution of room types across all layouts"""
    room_counts = {}
    
    for layout in layouts:
        for room in layout.get('rooms', []):
            room_type = room.get('type', 'unknown')
            room_counts[room_type] = room_counts.get(room_type, 0) + 1
    
    return room_counts

if __name__ == "__main__":
    INPUT_DIR = "datasets/processed/layouts"
    OUTPUT_DIR = "datasets/processed"
    
    create_dataset_splits(INPUT_DIR, OUTPUT_DIR)
