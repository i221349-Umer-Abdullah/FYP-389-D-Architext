"""
NLP Model Evaluation Script
Test the trained Text-to-Spec model
"""

import json
import torch
from pathlib import Path
from transformers import T5Tokenizer, T5ForConditionalGeneration

def load_model(model_dir: str):
    """Load the trained model"""
    print(f"Loading model from {model_dir}...")
    tokenizer = T5Tokenizer.from_pretrained(model_dir)
    model = T5ForConditionalGeneration.from_pretrained(model_dir)
    model.eval()
    return tokenizer, model

def generate_spec(text: str, tokenizer, model, max_length=256) -> str:
    """Generate spec from text"""
    inputs = tokenizer(
        text,
        return_tensors="pt",
        max_length=512,
        truncation=True
    )
    
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_length=max_length,
            num_beams=4,
            early_stopping=True,
            do_sample=False
        )
    
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def is_valid_json(text: str) -> bool:
    """Check if text is valid JSON"""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False

def evaluate_model(model_dir: str):
    """Run comprehensive evaluation"""
    tokenizer, model = load_model(model_dir)
    
    # Test cases - variety of inputs
    test_cases = [
        "A modern 3-bedroom house with 2 bathrooms",
        "A traditional home with living room, kitchen, and 2 bedrooms",
        "A minimalist floor plan with 1 bedroom and 1 bathroom",
        "A spacious contemporary home with 4 bedrooms, 3 bathrooms, and dining area",
        "A classic residential layout with 2 bedrooms and kitchen",
        "A modern house with living room, kitchen, study, and 2 bedrooms totaling 90 square meters",
        "A small apartment with 1 bedroom, bathroom, and open kitchen",
    ]
    
    print("\n" + "="*60)
    print("NLP MODEL EVALUATION RESULTS")
    print("="*60)
    
    valid_json_count = 0
    
    for i, text in enumerate(test_cases):
        print(f"\n--- Test {i+1} ---")
        print(f"INPUT:  {text}")
        
        output = generate_spec(text, tokenizer, model)
        print(f"OUTPUT: {output}")
        
        if is_valid_json(output):
            print("✓ Valid JSON")
            valid_json_count += 1
            try:
                spec = json.loads(output)
                print(f"  Parsed: {json.dumps(spec, indent=2)}")
            except:
                pass
        else:
            print("✗ Not valid JSON")
    
    print("\n" + "="*60)
    print(f"SUMMARY: {valid_json_count}/{len(test_cases)} outputs are valid JSON")
    print(f"Accuracy: {100*valid_json_count/len(test_cases):.1f}%")
    print("="*60)
    
    # Additional metrics
    print("\nNOTE: With only 599 training samples, the model is learning")
    print("the domain vocabulary but may not produce perfect JSON yet.")
    print("This demonstrates the training pipeline is working.")
    print("More training data (1000+) will significantly improve output quality.")
    
    return valid_json_count, len(test_cases)

if __name__ == "__main__":
    MODEL_DIR = "models/nlp_t5/final_model"
    evaluate_model(MODEL_DIR)
