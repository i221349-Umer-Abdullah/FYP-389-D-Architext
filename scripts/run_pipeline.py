"""
=============================================================================
ArchiText: Interactive Text-to-BIM Pipeline
=============================================================================

Run the full ArchiText pipeline with custom text input.

Usage:
------
    python run_pipeline.py
    python run_pipeline.py "3 bedroom house with 2 bathrooms"
    python run_pipeline.py --interactive

Author: ArchiText Team
=============================================================================
"""

import sys
import os
from pathlib import Path

# Add scripts to path
scripts_dir = Path(__file__).parent
project_root = scripts_dir.parent
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(project_root))

from text_to_bim import TextToBIMPipeline


def main():
    print("=" * 70)
    print("  ARCHITEXT: Text-to-BIM Pipeline")
    print("=" * 70)

    # Check for command line argument
    if len(sys.argv) > 1 and sys.argv[1] != "--interactive":
        # Use command line argument as input
        text_input = " ".join(sys.argv[1:])
    else:
        # Interactive mode - ask for input
        print("\nDescribe your house in natural language.")
        print("Examples:")
        print("  - 3 bedroom house with 2 bathrooms and garage")
        print("  - Modern 4 bed home with study and open kitchen")
        print("  - Small 2 bedroom apartment with 1 bathroom")
        print()
        text_input = input("Your description: ").strip()

    if not text_input:
        print("[!] No input provided. Using default example.")
        text_input = "Modern 3 bedroom house with 2 bathrooms, kitchen and living room"

    print(f"\n[INPUT] \"{text_input}\"")
    print("-" * 70)

    # Initialize and run pipeline
    try:
        pipeline = TextToBIMPipeline()

        # Generate output filename from description
        safe_name = "".join(c if c.isalnum() else "_" for c in text_input[:30])
        output_path = project_root / "output" / f"{safe_name}.ifc"

        result = pipeline.generate(text_input, output_path=str(output_path))

        if result["success"]:
            print("\n" + "=" * 70)
            print("  SUCCESS!")
            print("=" * 70)
            print(f"\n  IFC File: {result['ifc_file']}")
            print("\n  Open this file in:")
            print("    - Blender (with BlenderBIM/Bonsai addon)")
            print("    - Autodesk Revit (File > Open > IFC)")
            print("    - FreeCAD")
            print("=" * 70)
        else:
            print(f"\n[ERROR] Generation failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
