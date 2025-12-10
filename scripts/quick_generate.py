"""
=============================================================================
ArchiText: Quick BIM Generation (No NLP)
=============================================================================

Lightweight BIM generation script that takes a JSON specification directly,
bypassing the NLP model. Used by Blender's Quick Mode for fast generation.

Usage:
    python quick_generate.py '{"bedrooms": 3, "bathrooms": 2, "kitchen": true}'

Author: ArchiText Team
=============================================================================
"""

import sys
import json
import datetime
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from generate_bim import BIMGenerator


def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_generate.py '<json_spec>'")
        sys.exit(1)

    # Parse JSON spec from command line
    try:
        spec = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        sys.exit(1)

    # Generate output path with timestamp for unique files
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)

    bedrooms = spec.get("bedrooms", 3)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"quick_{bedrooms}bed_{timestamp}.ifc"

    print("=" * 60)
    print("ARCHITEXT: Quick Generate (No NLP)")
    print("=" * 60)
    print(f"Spec: {spec}")

    # Generate BIM directly
    try:
        generator = BIMGenerator()
        ifc_path = generator.generate_from_spec(spec, str(output_path))

        print("=" * 60)
        print("[SUCCESS]")
        print(f"IFC File: {ifc_path}")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
