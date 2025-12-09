"""
=============================================================================
ArchiText: NLP Model Training Script
=============================================================================

This script trains the T5 transformer model (LAYER 1) for converting natural
language building descriptions into structured JSON specifications. The trained
model serves as the foundation of the ArchiText pipeline.

Training Pipeline:
------------------
    Training Data (JSONL)
        │
        ├── Input:  "Modern 3 bedroom house with garage"
        └── Target: {"bedrooms": 3, "garage": true, ...}
                │
                ▼
    T5-Small Fine-tuning
        │
        ├── Encoder: Processes input text
        └── Decoder: Generates JSON specification
                │
                ▼
    Trained Model (LAYER 1)
        │
        └── Used by inference_nlp.py for text-to-spec conversion

Model Architecture:
-------------------
    - Base Model:    T5-small (~60MB parameters)
    - Task Type:     Sequence-to-sequence (text-to-text)
    - Input Format:  Natural language building description
    - Output Format: JSON string with building specification
    - Tokenizer:     SentencePiece (T5 default)

Training Configuration:
-----------------------
    - Epochs:        3 (default)
    - Batch Size:    4
    - Learning Rate: 5e-5
    - Optimizer:     AdamW with weight decay
    - Warmup Steps:  50
    - Train/Val Split: 90/10

Data Format (JSONL):
--------------------
    {"text": "3 bedroom house", "spec": {"bedrooms": 3, "bathrooms": 1, ...}}
    {"text": "apartment with 2 baths", "spec": {"bedrooms": 1, "bathrooms": 2, ...}}

Usage:
------
    # Training mode (default)
    python train_nlp_model.py

    # Testing mode
    python train_nlp_model.py test

Output:
-------
    models/nlp_t5/final_model/
    ├── config.json
    ├── model.safetensors
    ├── tokenizer.json
    └── special_tokens_map.json

The trained model is then used by the ArchiText pipeline, where its output is
further refined by the rule-based layout optimizer (Layer 2) before BIM generation.

Author: ArchiText Team
Version: 1.0.0
=============================================================================
"""

import json
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow warnings

import torch
from pathlib import Path

try:
    from transformers import (
        T5Tokenizer,
        T5ForConditionalGeneration,
        Trainer,
        TrainingArguments,
        DataCollatorForSeq2Seq
    )
    from datasets import Dataset
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required packages:")
    print("pip install transformers datasets torch")
    exit(1)

from typing import Dict, List

def load_text_pairs(jsonl_path: str) -> List[Dict]:
    """Load text-spec pairs from JSONL"""
    pairs = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))
    return pairs

def prepare_training_data(text_pairs_file: str):
    """
    Prepare data for T5 training
    
    Input format: {"text": "...", "spec": {...}}
    T5 format: {"input": "text", "target": "json_spec_string"}
    """
    pairs = []
    
    # Load text pairs
    text_pairs_path = Path(text_pairs_file)
    if text_pairs_path.exists():
        with open(text_pairs_path, 'r') as f:
            for line in f:
                if line.strip():
                    pair = json.loads(line)
                    pairs.append({
                        'input': pair['text'],
                        'target': json.dumps(pair['spec'], separators=(',', ':'))
                    })
    
    return pairs

def create_dataset(data_list: List[Dict], tokenizer, max_length=512):
    """Convert to HuggingFace Dataset format"""
    
    def tokenize_function(examples):
        # Tokenize inputs
        model_inputs = tokenizer(
            examples['input'],
            max_length=max_length,
            truncation=True,
            padding='max_length'
        )
        
        # Tokenize targets
        labels = tokenizer(
            examples['target'],
            max_length=max_length,
            truncation=True,
            padding='max_length'
        )
        
        model_inputs['labels'] = labels['input_ids']
        return model_inputs
    
    # Create dataset
    dataset = Dataset.from_dict({
        'input': [item['input'] for item in data_list],
        'target': [item['target'] for item in data_list]
    })
    
    # Tokenize
    tokenized = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=['input', 'target']
    )
    
    return tokenized

def train_nlp_model(
    text_pairs_file: str = "datasets/processed/text_pairs/text_pairs.jsonl",
    model_name: str = "t5-small",
    output_dir: str = "models/nlp_t5",
    num_epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 5e-5
):
    """
    Train T5 model for text-to-spec conversion
    
    Args:
        text_pairs_file: Path to training data
        model_name: Pre-trained model to fine-tune
        output_dir: Where to save trained model
        num_epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate
    """
    print(f"Loading model and tokenizer: {model_name}")
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)
    
    print(f"Loading training data from {text_pairs_file}")
    train_data = prepare_training_data(text_pairs_file)
    
    if len(train_data) == 0:
        print("ERROR: No training data found!")
        return
    
    print(f"Found {len(train_data)} training samples")
    
    # Create train/val split (90/10)
    split_idx = int(len(train_data) * 0.9)
    train_list = train_data[:split_idx]
    val_list = train_data[split_idx:]
    
    print(f"Train: {len(train_list)}, Val: {len(val_list)}")
    
    # Create datasets
    train_dataset = create_dataset(train_list, tokenizer)
    val_dataset = create_dataset(val_list, tokenizer)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        warmup_steps=50,
        learning_rate=learning_rate,
        weight_decay=0.01,
        logging_dir=f"{output_dir}/logs",
        logging_steps=10,
        eval_steps=50,
        save_steps=100,
        eval_strategy="steps",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        report_to="none",  # Disable wandb/tensorboard
    )
    
    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )
    
    # Train
    print("\nStarting training...")
    print(f"Epochs: {num_epochs}, Batch size: {batch_size}, LR: {learning_rate}")
    
    trainer.train()
    
    # Save final model
    final_model_path = Path(output_dir) / "final_model"
    trainer.save_model(final_model_path)
    tokenizer.save_pretrained(final_model_path)
    
    print(f"\n✓ Training complete!")
    print(f"Model saved to: {final_model_path}")
    
    return trainer

def test_model(model_dir: str, test_text: str):
    """
    Test the trained model with a sample text
    
    Args:
        model_dir: Path to saved model
        test_text: Input text to test
    """
    print(f"\nTesting model from {model_dir}")
    print(f"Input: {test_text}")
    
    # Load model
    tokenizer = T5Tokenizer.from_pretrained(model_dir)
    model = T5ForConditionalGeneration.from_pretrained(model_dir)
    model.eval()
    
    # Tokenize
    inputs = tokenizer(
        test_text,
        return_tensors="pt",
        max_length=512,
        truncation=True
    )
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_length=512,
            num_beams=4,
            early_stopping=True
        )
    
    # Decode
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    print(f"Output: {generated_text}")
    
    # Try to parse as JSON
    try:
        spec = json.loads(generated_text)
        print("\n✓ Valid JSON spec generated!")
        print(json.dumps(spec, indent=2))
    except json.JSONDecodeError:
        print("\n✗ Output is not valid JSON")
    
    return generated_text

if __name__ == "__main__":
    import sys
    
    # Check if we're training or testing
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        model_dir = "models/nlp_t5/final_model"
        test_text = "A modern 3-bedroom house with 2 bathrooms and a garage"
        test_model(model_dir, test_text)
    else:
        # Training mode
        print("=" * 60)
        print("NLP Model Training - Text to Spec Conversion")
        print("=" * 60)
        
        trainer = train_nlp_model(
            text_pairs_file="datasets/processed/text_pairs/text_pairs.jsonl",
            model_name="t5-small",  # ~60MB model
            output_dir="models/nlp_t5",
            num_epochs=3,
            batch_size=4,
            learning_rate=5e-5
        )
        
        print("\n" + "=" * 60)
        print("Training Complete! Testing model...")
        print("=" * 60)
        
        # Quick test
        test_model(
            "models/nlp_t5/final_model",
            "A small traditional house with 2 bedrooms and 1 bathroom"
        )
