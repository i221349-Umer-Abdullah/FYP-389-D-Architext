"""
=============================================================================
ArchiText: Overnight Training Pipeline (UNATTENDED)
=============================================================================

Fully automated overnight training - NO prompts, NO confirmations.
Just run and go to sleep.

This will:
    1. Generate training data from CubiCasa using Gemini API (~500 layouts)
    2. Combine with existing synthetic data
    3. Train T5 model for 15 epochs (aggressive training)
    4. Save checkpoints every 100 steps
    5. Save final model to models/nlp_t5/final_model/

Author: ArchiText Team
=============================================================================
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    start_time = datetime.now()

    print("=" * 70)
    print("OVERNIGHT TRAINING PIPELINE - UNATTENDED MODE")
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # No prompts - just proceed with whatever we have
    has_api_key = bool(os.environ.get("GEMINI_API_KEY"))
    if has_api_key:
        print("[OK] Gemini API key found - using API for data generation")
    else:
        print("[INFO] No Gemini API key - using template-based generation")

    # Step 1: Generate training data
    print("\n" + "=" * 70)
    print("STEP 1: GENERATING TRAINING DATA")
    print("=" * 70)

    gen_script = script_dir / "generate_training_data_gemini.py"
    result = subprocess.run([sys.executable, str(gen_script)], cwd=str(project_root))

    # Continue even if data generation has issues - we might have existing data
    if result.returncode != 0:
        print("[WARN] Data generation had issues, checking for existing data...")

    # Step 2: Find best available training data
    print("\n" + "=" * 70)
    print("STEP 2: PREPARING TRAINING DATA")
    print("=" * 70)

    # Priority order for training data
    data_options = [
        project_root / "datasets" / "processed" / "combined_gemini_train.jsonl",
        project_root / "datasets" / "processed" / "gemini_training_data.jsonl",
        project_root / "data" / "nlp_training" / "synthetic_train_2000.jsonl",
        project_root / "datasets" / "processed" / "text_pairs" / "text_pairs.jsonl",
    ]

    training_data = None
    for data_path in data_options:
        if data_path.exists():
            training_data = str(data_path)
            break

    if not training_data:
        print("[!] No training data found! Cannot proceed.")
        return

    print(f"Using training data: {training_data}")

    # Count training samples
    with open(training_data, 'r') as f:
        num_samples = sum(1 for line in f if line.strip())
    print(f"Training samples: {num_samples}")

    # Step 3: Train the model with aggressive settings
    print("\n" + "=" * 70)
    print("STEP 3: TRAINING T5 MODEL (AGGRESSIVE SETTINGS)")
    print("=" * 70)

    # Set environment variables for training
    os.environ["ARCHITEXT_TRAIN_DATA"] = training_data
    os.environ["ARCHITEXT_EPOCHS"] = "15"  # Aggressive: 15 epochs

    train_script = script_dir / "train_nlp_model.py"

    print(f"\nTraining configuration:")
    print(f"  - Epochs: 15 (aggressive)")
    print(f"  - Batch size: 4")
    print(f"  - Learning rate: 5e-5")
    print(f"  - Samples: {num_samples}")
    print(f"\nEstimated time: {(num_samples * 15) // 1000} - {(num_samples * 15) // 500} hours")
    print("\nTraining started... (check progress below)")
    print("-" * 70)

    result = subprocess.run([sys.executable, str(train_script)], cwd=str(project_root))

    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 70)
    if result.returncode == 0:
        print("[OK] TRAINING COMPLETE!")
    else:
        print("[!!] Training ended with errors (partial training may still be useful)")

    print("=" * 70)
    print(f"Started:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print(f"\nModel saved to: models/nlp_t5/final_model/")
    print("\nTest with:")
    print("  python scripts/train_nlp_model.py test")
    print("=" * 70)


if __name__ == "__main__":
    main()
