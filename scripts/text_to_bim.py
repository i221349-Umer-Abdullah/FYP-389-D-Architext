"""
End-to-end Text-to-BIM pipeline.
Converts natural language descriptions directly to IFC BIM files.
"""

import json
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.inference_nlp import TextToSpecInference
from scripts.generate_bim import BIMGenerator


class TextToBIMPipeline:
    """Complete pipeline: Text → JSON Spec → IFC BIM."""
    
    def __init__(self, model_path: str = None):
        """
        Initialize the full pipeline.
        
        Args:
            model_path: Path to trained NLP model (optional)
        """
        print("Initializing Text-to-BIM Pipeline...")
        print("-" * 80)
        
        # Initialize NLP model
        print("1. Loading Text-to-Spec AI model...")
        self.nlp_inferencer = TextToSpecInference(model_path)
        
        # Initialize BIM generator
        print("2. Initializing BIM Generator...")
        self.bim_generator = BIMGenerator()
        
        print("-" * 80)
        print("[OK] Pipeline ready!\n")
    
    def generate(self, text: str, output_path: str = None, verbose: bool = True) -> dict:
        """
        Convert natural language to IFC BIM file.
        
        Args:
            text: Natural language description of building
            output_path: Optional output path for IFC file
            verbose: Whether to print progress
            
        Returns:
            Dictionary with generation results
        """
        result = {
            "input_text": text,
            "success": False
        }
        
        try:
            # Step 1: Text → JSON Spec
            if verbose:
                print("="*80)
                print("STEP 1: Converting text to specification...")
                print("="*80)
                print(f"Input: {text}\n")
            
            spec = self.nlp_inferencer.predict(text)
            result["specification"] = spec
            
            if verbose:
                print("Generated Specification:")
                print(json.dumps(spec, indent=2))
                print()
            
            # Check if spec is valid
            if "status" in spec and spec["status"] == "invalid_json":
                result["error"] = "AI generated invalid JSON specification"
                if verbose:
                    print("[ERROR] Invalid JSON specification generated")
                return result
            
            # Step 2: JSON Spec → IFC BIM
            if verbose:
                print("="*80)
                print("STEP 2: Generating IFC BIM file...")
                print("="*80)
            
            # Create new BIM generator for each building
            bim_gen = BIMGenerator()
            ifc_path = bim_gen.generate_from_spec(spec, output_path)
            
            result["ifc_file"] = ifc_path
            result["success"] = True
            
            if verbose:
                print()
                print("="*80)
                print("[SUCCESS]")
                print("="*80)
                print(f"IFC File: {ifc_path}")
                print("="*80)
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            if verbose:
                print(f"\n[ERROR]: {e}")
            return result


def main():
    """Demo the complete Text-to-BIM pipeline."""
    # Initialize pipeline
    pipeline = TextToBIMPipeline()
    
    # Example building descriptions
    examples = [
        "A modern 3-bedroom house with 2 bathrooms, a spacious kitchen, living room, and dining room",
        "A cozy 2-bedroom apartment with 1 bathroom and an open-plan kitchen and living area",
        "A small studio apartment with bathroom and kitchenette"
    ]
    
    print("\n" + "="*80)
    print("  TEXT-TO-BIM AI PIPELINE DEMONSTRATION".center(80))
    print("="*80 + "\n")
    
    for i, description in enumerate(examples, 1):
        print(f"\n{'='*80}")
        print(f"  EXAMPLE {i}/{len(examples)}")
        print(f"{'='*80}\n")
        
        # Generate BIM
        result = pipeline.generate(description, verbose=True)
        
        if result["success"]:
            print(f"\n[OK] Building generated successfully!")
        else:
            print(f"\n[FAILED] Generation failed: {result.get('error', 'Unknown error')}")
        
        print()
    
    print("="*80)
    print("  PIPELINE DEMONSTRATION COMPLETE".center(80))
    print("="*80)


if __name__ == "__main__":
    main()
