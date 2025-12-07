"""
Inference script for Text-to-Spec AI model.
Converts natural language descriptions to JSON specifications.
"""

import json
import os
import sys
from pathlib import Path
from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TextToSpecInference:
    """Inference class for converting text to building specifications."""
    
    def __init__(self, model_path: str = None):
        """
        Initialize the inference model.
        
        Args:
            model_path: Path to the trained model directory
        """
        if model_path is None:
            model_path = project_root / "models" / "nlp_t5" / "final_model"
        
        self.model_path = Path(model_path)
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        
        print(f"Loading model from {self.model_path}...")
        self.tokenizer = T5Tokenizer.from_pretrained(str(self.model_path))
        self.model = T5ForConditionalGeneration.from_pretrained(str(self.model_path))
        
        # Move to GPU if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()
        
        print(f"Model loaded on {self.device}")
    
    def predict(self, text: str, max_length: int = 256, num_beams: int = 4) -> dict:
        """
        Convert natural language text to JSON specification.
        
        Args:
            text: Natural language description of the building
            max_length: Maximum length of generated output
            num_beams: Number of beams for beam search
            
        Returns:
            Dictionary containing the building specification
        """
        # Prepare input (no prefix - model was trained without it)
        input_text = text
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        ).to(self.device)
        
        # Generate output
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                num_beams=num_beams,
                early_stopping=True,
                do_sample=False,
                temperature=1.0
            )
        
        # Decode output
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Try to parse as JSON
        try:
            spec = json.loads(generated_text)
            return spec
        except json.JSONDecodeError as e:
            # Try to fix common T5 JSON generation issues
            fixed_text = generated_text.strip()

            # Add missing braces if needed
            if not fixed_text.startswith('{'):
                fixed_text = '{' + fixed_text
            if not fixed_text.endswith('}'):
                # Find the last complete key-value pair
                last_comma = fixed_text.rfind(',')
                if last_comma > 0:
                    fixed_text = fixed_text[:last_comma] + '}'
                else:
                    fixed_text = fixed_text + '}'

            # Try parsing the fixed JSON
            try:
                spec = json.loads(fixed_text)
                # Remove duplicate keys (keep first occurrence)
                cleaned_spec = {}
                for key in spec:
                    if key not in cleaned_spec:
                        cleaned_spec[key] = spec[key]
                return cleaned_spec
            except json.JSONDecodeError:
                print(f"Warning: Generated text is not valid JSON: {e}")
                print(f"Generated text: {generated_text}")

                # Return a fallback structure with the raw output
                return {
                    "raw_output": generated_text,
                    "parse_error": str(e),
                    "status": "invalid_json"
                }
    
    def predict_batch(self, texts: list[str], max_length: int = 256) -> list[dict]:
        """
        Convert multiple natural language texts to JSON specifications.
        
        Args:
            texts: List of natural language descriptions
            max_length: Maximum length of generated output
            
        Returns:
            List of dictionaries containing building specifications
        """
        results = []
        for text in texts:
            spec = self.predict(text, max_length)
            results.append(spec)
        
        return results


def main():
    """Example usage of the inference script."""
    # Initialize model
    inferencer = TextToSpecInference()
    
    # Example inputs
    test_inputs = [
        "A modern 3-bedroom house with 2 bathrooms, a kitchen, living room, and dining room",
        "A cozy 2-bedroom apartment with 1 bathroom and an open-plan kitchen and living area",
        "A spacious 4-bedroom home with 3 bathrooms, study, kitchen, dining room, and large living room",
        "Small studio apartment with bathroom and kitchenette, approximately 30 square meters"
    ]
    
    print("\n" + "="*80)
    print("TEXT-TO-SPEC AI INFERENCE DEMO")
    print("="*80 + "\n")
    
    for i, text in enumerate(test_inputs, 1):
        print(f"\n{'─'*80}")
        print(f"Example {i}:")
        print(f"{'─'*80}")
        print(f"Input: {text}\n")
        
        # Generate specification
        spec = inferencer.predict(text)
        
        print(f"Output Specification:")
        print(json.dumps(spec, indent=2))
    
    print("\n" + "="*80)
    print("Demo complete!")
    print("="*80)


if __name__ == "__main__":
    main()
