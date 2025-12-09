"""
Package the ArchiText Blender add-on into an installable ZIP file.
"""

import zipfile
import os
from pathlib import Path

def create_addon_zip():
    """Create the add-on ZIP file."""
    addon_dir = Path(__file__).parent / "architext"
    output_zip = Path(__file__).parent / "architext_addon.zip"

    # Remove existing zip if present
    if output_zip.exists():
        output_zip.unlink()

    print("Packaging ArchiText Blender Add-on...")
    print(f"Source: {addon_dir}")
    print(f"Output: {output_zip}")

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in addon_dir.rglob('*'):
            if file_path.is_file():
                # Skip __pycache__ and .pyc files
                if '__pycache__' in str(file_path) or file_path.suffix == '.pyc':
                    continue

                arcname = file_path.relative_to(addon_dir.parent)
                print(f"  Adding: {arcname}")
                zf.write(file_path, arcname)

    print(f"\n[OK] Created: {output_zip}")
    print(f"    Size: {output_zip.stat().st_size / 1024:.1f} KB")
    print("\nTo install:")
    print("  1. Open Blender")
    print("  2. Edit > Preferences > Add-ons")
    print("  3. Click 'Install...'")
    print(f"  4. Select: {output_zip}")
    print("  5. Enable 'ArchiText - Text to BIM'")

    return output_zip


if __name__ == "__main__":
    create_addon_zip()
