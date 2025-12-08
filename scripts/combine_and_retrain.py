"""
Combine original + synthetic data and retrain T5 model.
"""

import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def combine_datasets():
    """Combine original and synthetic training data."""
    print("="*80)
    print("COMBINING TRAINING DATASETS")
    print("="*80)

    # Load original data
    original_file = Path("datasets/processed/train.jsonl")
    synthetic_file = Path("data/nlp_training/synthetic_train_2000.jsonl")

    if not original_file.exists():
        print(f"[ERROR] Original training data not found: {original_file}")
        return None

    if not synthetic_file.exists():
        print(f"[ERROR] Synthetic data not found: {synthetic_file}")
        return None

    # Load original (JSONL format)
    original_data = []
    with open(original_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                original_data.append(json.loads(line))

    print(f"Original data: {len(original_data)} samples")

    # Load synthetic (JSONL format)
    synthetic_data = []
    with open(synthetic_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                synthetic_data.append(json.loads(line))

    print(f"Synthetic data: {len(synthetic_data)} samples")

    # Combine
    combined = original_data + synthetic_data
    print(f"Combined total: {len(combined)} samples")

    # Save combined (JSONL format)
    output_file = Path("datasets/processed/combined_train.jsonl")
    with open(output_file, 'w', encoding='utf-8') as f:
        for sample in combined:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    print(f"\n[OK] Saved combined dataset to: {output_file}")

    return output_file

def main():
    """Combine datasets."""
    combined_file = combine_datasets()

    if combined_file:
        print("\n" + "="*80)
        print("NEXT STEP: RETRAIN MODEL")
        print("="*80)
        print("\nRun the following command to retrain:")
        print(f"python scripts/train_nlp.py --train_file {combined_file}")
        print("\nExpected training time: 30-45 minutes")

if __name__ == "__main__":
    main()
