"""
=============================================================================
ArchiText: Blender Add-on for Text-to-BIM Generation
=============================================================================

This Blender add-on provides a user-friendly interface for the ArchiText
Text-to-BIM pipeline, allowing architects and designers to generate 3D
building models directly within Blender using natural language descriptions.

IMPORTANT: This add-on uses subprocess to call an external Python environment
that has all required dependencies (transformers, torch, ifcopenshell).
It does NOT import these packages directly into Blender's Python.

Author: ArchiText Team
Version: 1.1.0
=============================================================================
"""

bl_info = {
    "name": "ArchiText - Text to BIM",
    "author": "ArchiText Team",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > ArchiText",
    "description": "Generate 3D building models from natural language descriptions",
    "category": "3D View",
}

import bpy
import os
import sys
import subprocess
import json
import tempfile
from bpy.props import (
    StringProperty,
    IntProperty,
    FloatProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty,
)
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
    AddonPreferences,
)


# ============================================================================
# PROPERTY DEFINITIONS
# ============================================================================

class ARCHITEXT_Properties(PropertyGroup):
    """Properties for ArchiText add-on."""

    # Main text input
    prompt: StringProperty(
        name="Description",
        description="Describe your building in natural language",
        default="Modern 3 bedroom house with 2 bathrooms, open kitchen and living area",
        maxlen=1024,
    )

    # Building settings
    wall_height: FloatProperty(
        name="Wall Height",
        description="Height of walls in meters",
        default=2.7,
        min=2.0,
        max=5.0,
        unit='LENGTH',
    )

    wall_thickness: FloatProperty(
        name="Wall Thickness",
        description="Thickness of walls in meters",
        default=0.2,
        min=0.1,
        max=0.5,
        unit='LENGTH',
    )

    # Style presets (FUTURE: not yet implemented in generation pipeline)
    # This property is defined for future use but currently has no effect
    style_preset: EnumProperty(
        name="Style",
        description="Building style preset (not yet implemented)",
        items=[
            ('modern', "Modern", "Contemporary design with clean lines"),
            ('traditional', "Traditional", "Classic architectural style"),
            ('minimalist', "Minimalist", "Simple, functional design"),
            ('luxury', "Luxury", "High-end with larger rooms"),
        ],
        default='modern',
    )

    # Generation options
    auto_import: BoolProperty(
        name="Auto Import",
        description="Automatically import generated IFC into scene",
        default=True,
    )

    clear_scene: BoolProperty(
        name="Clear Scene",
        description="Clear existing objects before importing",
        default=False,
    )

    # Status
    status_message: StringProperty(
        name="Status",
        default="Ready to generate",
    )

    is_generating: BoolProperty(
        name="Is Generating",
        default=False,
    )


# ============================================================================
# ADDON PREFERENCES
# ============================================================================

class ARCHITEXT_Preferences(AddonPreferences):
    bl_idname = __name__

    python_path: StringProperty(
        name="Python Executable",
        description="Path to Python executable in your ArchiText venv (e.g., D:/Work/Uni/FYP/architext/venv/Scripts/python.exe)",
        default="",
        subtype='FILE_PATH',
    )

    scripts_path: StringProperty(
        name="Scripts Path",
        description="Path to ArchiText scripts folder",
        default="",
        subtype='DIR_PATH',
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="ArchiText Configuration", icon='SETTINGS')

        col = box.column(align=True)
        col.prop(self, "python_path")
        col.prop(self, "scripts_path")

        if not self.python_path:
            box.label(text="Please set the path to your venv Python executable", icon='ERROR')
        if not self.scripts_path:
            box.label(text="Please set the path to your ArchiText scripts folder", icon='ERROR')

        # Auto-detect button
        row = box.row()
        row.operator("architext.auto_detect_paths", text="Auto-Detect Paths", icon='FILE_REFRESH')

        # Test configuration button
        row = box.row()
        row.operator("architext.test_config", text="Test Configuration", icon='CHECKMARK')


class ARCHITEXT_OT_AutoDetectPaths(Operator):
    """Try to auto-detect ArchiText paths"""
    bl_idname = "architext.auto_detect_paths"
    bl_label = "Auto-Detect Paths"

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        addon_dir = os.path.dirname(os.path.realpath(__file__))

        # Try to find project root
        possible_roots = [
            os.path.join(addon_dir, "..", ".."),
            os.path.join(addon_dir, "..", "..", ".."),
            "D:/Work/Uni/FYP/architext",
        ]

        for root in possible_roots:
            root = os.path.abspath(root)
            scripts = os.path.join(root, "scripts")
            venv_python = os.path.join(root, "venv", "Scripts", "python.exe")

            if os.path.exists(scripts) and os.path.exists(venv_python):
                prefs.scripts_path = scripts
                prefs.python_path = venv_python
                self.report({'INFO'}, f"Found ArchiText at: {root}")
                return {'FINISHED'}

        self.report({'WARNING'}, "Could not auto-detect paths. Please set manually.")
        return {'CANCELLED'}


class ARCHITEXT_OT_TestConfig(Operator):
    """Test ArchiText configuration by running a simple Python test"""
    bl_idname = "architext.test_config"
    bl_label = "Test Configuration"

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences

        print("\n" + "=" * 60)
        print("ARCHITEXT CONFIGURATION TEST")
        print("=" * 60)

        # Check Python path
        if not prefs.python_path:
            self.report({'ERROR'}, "Python path not set!")
            print("[ERROR] Python path is not configured")
            return {'CANCELLED'}

        if not os.path.exists(prefs.python_path):
            self.report({'ERROR'}, f"Python not found: {prefs.python_path}")
            print(f"[ERROR] Python executable not found at: {prefs.python_path}")
            return {'CANCELLED'}

        print(f"[OK] Python path: {prefs.python_path}")

        # Check scripts path
        if not prefs.scripts_path:
            self.report({'ERROR'}, "Scripts path not set!")
            print("[ERROR] Scripts path is not configured")
            return {'CANCELLED'}

        if not os.path.exists(prefs.scripts_path):
            self.report({'ERROR'}, f"Scripts folder not found: {prefs.scripts_path}")
            print(f"[ERROR] Scripts folder not found at: {prefs.scripts_path}")
            return {'CANCELLED'}

        print(f"[OK] Scripts path: {prefs.scripts_path}")

        # Check run_pipeline.py exists
        run_script = os.path.join(prefs.scripts_path, "run_pipeline.py")
        if not os.path.exists(run_script):
            self.report({'ERROR'}, "run_pipeline.py not found!")
            print(f"[ERROR] run_pipeline.py not found at: {run_script}")
            return {'CANCELLED'}

        print(f"[OK] run_pipeline.py found")

        # Test Python execution
        print("\n[TEST] Running Python version check...")
        try:
            result = subprocess.run(
                [prefs.python_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"[OK] Python version: {result.stdout.strip()}")
            else:
                print(f"[WARN] Python check returned: {result.stderr}")
        except Exception as e:
            print(f"[ERROR] Failed to run Python: {e}")
            self.report({'ERROR'}, f"Cannot run Python: {e}")
            return {'CANCELLED'}

        # Test if transformers is available in the venv
        print("\n[TEST] Checking transformers module...")
        try:
            result = subprocess.run(
                [prefs.python_path, "-c", "import transformers; print('transformers OK:', transformers.__version__)"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"[OK] {result.stdout.strip()}")
            else:
                print(f"[ERROR] transformers not available: {result.stderr.strip()[:100]}")
                self.report({'ERROR'}, "transformers not installed in venv")
                return {'CANCELLED'}
        except subprocess.TimeoutExpired:
            print("[ERROR] Timeout checking transformers")
            self.report({'ERROR'}, "Timeout checking transformers")
            return {'CANCELLED'}
        except Exception as e:
            print(f"[ERROR] Exception: {e}")

        print("\n" + "=" * 60)
        print("CONFIGURATION TEST PASSED!")
        print("=" * 60 + "\n")

        self.report({'INFO'}, "Configuration test passed! All dependencies found.")
        return {'FINISHED'}


# ============================================================================
# OPERATORS
# ============================================================================

class ARCHITEXT_OT_Generate(Operator):
    """Generate a building from text description using the full NLP pipeline"""
    bl_idname = "architext.generate"
    bl_label = "Generate Building"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.architext
        prefs = context.preferences.addons[__name__].preferences

        print("\n" + "=" * 60)
        print("ARCHITEXT: Generate Building (Full NLP Mode)")
        print("=" * 60)
        print(f"Version: 1.1.0 (Subprocess Mode)")
        print(f"Prompt: {props.prompt[:50]}...")

        # Validate paths
        if not prefs.python_path or not os.path.exists(prefs.python_path):
            self.report({'ERROR'}, "Python path not set. Please configure in add-on preferences.")
            props.status_message = "Error: Python path not set"
            print("[ERROR] Python path not configured!")
            return {'CANCELLED'}

        if not prefs.scripts_path or not os.path.exists(prefs.scripts_path):
            self.report({'ERROR'}, "Scripts path not set. Please configure in add-on preferences.")
            props.status_message = "Error: Scripts path not set"
            print("[ERROR] Scripts path not configured!")
            return {'CANCELLED'}

        print(f"[OK] Python: {prefs.python_path}")
        print(f"[OK] Scripts: {prefs.scripts_path}")

        props.is_generating = True
        props.status_message = "Generating with AI model..."

        try:
            # Prepare output path
            project_root = os.path.dirname(prefs.scripts_path)
            output_dir = os.path.join(project_root, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Create safe filename from prompt
            safe_name = "".join(c if c.isalnum() else "_" for c in props.prompt[:30])
            output_path = os.path.join(output_dir, f"blender_{safe_name}.ifc")

            # Call external Python with run_pipeline.py
            run_script = os.path.join(prefs.scripts_path, "run_pipeline.py")

            if not os.path.exists(run_script):
                self.report({'ERROR'}, f"run_pipeline.py not found at {run_script}")
                props.status_message = "Error: run_pipeline.py not found"
                print(f"[ERROR] run_pipeline.py not found at: {run_script}")
                return {'CANCELLED'}

            print(f"[OK] Found run_pipeline.py")
            print(f"\n[RUNNING] Calling external Python via subprocess...")
            print(f"Command: {prefs.python_path} {run_script} \"{props.prompt}\"")
            print("-" * 60)

            props.status_message = "Running NLP model..."

            # Run the pipeline via subprocess
            # Use Popen with temp files to avoid pipe buffer issues on Windows
            import tempfile
            stdout_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
            stderr_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')

            try:
                # Use CREATE_NO_WINDOW on Windows to prevent console flash
                startupinfo = None
                creationflags = 0
                if sys.platform == 'win32':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    creationflags = subprocess.CREATE_NO_WINDOW

                process = subprocess.Popen(
                    [prefs.python_path, run_script, props.prompt],
                    stdout=stdout_file,
                    stderr=stderr_file,
                    cwd=project_root,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )

                # Wait for completion with timeout
                return_code = process.wait(timeout=120)

                # Read outputs
                stdout_file.seek(0)
                stderr_file.seek(0)
                stdout_content = stdout_file.read()
                stderr_content = stderr_file.read()

            finally:
                stdout_file.close()
                stderr_file.close()
                # Clean up temp files
                try:
                    os.unlink(stdout_file.name)
                    os.unlink(stderr_file.name)
                except:
                    pass

            print("-" * 60)
            print(f"[DONE] Subprocess returned with code: {return_code}")

            if return_code != 0:
                print(f"\n[ERROR] Generation failed!")
                print(f"STDOUT:\n{stdout_content[:500] if stdout_content else '(empty)'}")
                print(f"STDERR:\n{stderr_content[:500] if stderr_content else '(empty)'}")
                error_msg = stderr_content[:200] if stderr_content else "Unknown error (check Blender console)"
                self.report({'ERROR'}, f"Generation failed: {error_msg}")
                props.status_message = f"Error: Check console for details"
                return {'CANCELLED'}

            print(f"\n[SUCCESS] Generation completed!")
            if stdout_content:
                print(f"STDOUT (last 300 chars):\n...{stdout_content[-300:]}")

            # Find the generated IFC file from output
            # The script prints the path, let's parse it
            output_lines = stdout_content.split('\n')
            ifc_path = None
            for line in output_lines:
                if "IFC File:" in line or ".ifc" in line.lower():
                    # Extract path from line
                    if ":" in line and ".ifc" in line:
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            potential_path = parts[1].strip()
                            if os.path.exists(potential_path):
                                ifc_path = potential_path
                                break

            # If not found, look for recent IFC in output folder
            if not ifc_path:
                import glob
                ifc_files = glob.glob(os.path.join(output_dir, "*.ifc"))
                if ifc_files:
                    ifc_path = max(ifc_files, key=os.path.getmtime)

            if not ifc_path or not os.path.exists(ifc_path):
                self.report({'WARNING'}, "IFC file generated but path not found")
                props.status_message = "Generated - check output folder"
                return {'FINISHED'}

            props.status_message = "IFC created! Importing..."

            # Import into Blender
            if props.auto_import:
                self._import_ifc(context, ifc_path, props)

            props.status_message = f"Success! {os.path.basename(ifc_path)}"
            self.report({'INFO'}, f"Building generated: {ifc_path}")

        except subprocess.TimeoutExpired:
            self.report({'ERROR'}, "Generation timed out (>2 minutes)")
            props.status_message = "Error: Timeout"
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            props.status_message = f"Error: {str(e)[:50]}"
            return {'CANCELLED'}

        finally:
            props.is_generating = False

        return {'FINISHED'}

    def _import_ifc(self, context, ifc_path, props):
        """Import IFC file into Blender with robust error handling."""
        print(f"[Generate] Attempting to import: {ifc_path}")

        try:
            if props.clear_scene:
                bpy.ops.object.select_all(action='SELECT')
                bpy.ops.object.delete()
        except Exception as e:
            print(f"[Generate] Clear scene failed: {e}")

        # Try Bonsai/BlenderBIM first (with safety checks)
        try:
            if hasattr(bpy.ops, 'bim') and hasattr(bpy.ops.bim, 'load_project'):
                bpy.ops.bim.load_project(filepath=ifc_path)
                print("[Generate] Imported via BlenderBIM")
                return
        except Exception as e:
            print(f"[Generate] BlenderBIM import failed: {e}")

        # Fallback: try native IFC import (Blender 4.0+)
        try:
            if hasattr(bpy.ops, 'import_scene') and hasattr(bpy.ops.import_scene, 'ifc'):
                bpy.ops.import_scene.ifc(filepath=ifc_path)
                print("[Generate] Imported via native IFC")
                return
        except Exception as e:
            print(f"[Generate] Native IFC import failed: {e}")

        # Final fallback: just report location
        print(f"[Generate] Auto-import failed. File at: {ifc_path}")
        props.status_message = f"Generated: {ifc_path}"


class ARCHITEXT_OT_GenerateQuick(Operator):
    """Generate building using direct specification (faster, no NLP)"""
    bl_idname = "architext.generate_quick"
    bl_label = "Quick Generate"
    bl_options = {'REGISTER', 'UNDO'}

    bedrooms: IntProperty(name="Bedrooms", default=3, min=1, max=10)
    bathrooms: IntProperty(name="Bathrooms", default=2, min=1, max=5)
    has_kitchen: BoolProperty(name="Kitchen", default=True)
    has_living: BoolProperty(name="Living Room", default=True)
    has_dining: BoolProperty(name="Dining Room", default=True)
    has_study: BoolProperty(name="Study", default=False)
    has_garage: BoolProperty(name="Garage", default=False)

    # Area/Plot size options
    use_area_bounds: BoolProperty(
        name="Specify Plot Size",
        description="Constrain building to a specific plot area",
        default=False
    )
    area_unit: EnumProperty(
        name="Unit",
        items=[
            ('marla', "Marla", "1 marla = 272.25 sq ft (Pakistan/India)"),
            ('kanal', "Kanal", "1 kanal = 20 marla"),
            ('sqft', "Sq Feet", "Square feet"),
            ('sqm', "Sq Meters", "Square meters"),
            ('dimensions', "W x H", "Specific width x height in meters"),
        ],
        default='marla'
    )
    area_value: FloatProperty(
        name="Size",
        description="Plot size in selected unit",
        default=5.0,
        min=1.0,
        max=100.0
    )
    plot_width: FloatProperty(
        name="Width (m)",
        description="Plot width in meters",
        default=10.0,
        min=5.0,
        max=50.0
    )
    plot_height: FloatProperty(
        name="Depth (m)",
        description="Plot depth in meters",
        default=15.0,
        min=5.0,
        max=50.0
    )

    def invoke(self, context, event):
        # Use larger width to ensure all content is visible
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout

        # =====================================================================
        # SECTION 1: ROOM CONFIGURATION
        # =====================================================================
        box1 = layout.box()
        box1.label(text="Room Configuration", icon='HOME')

        # Bedroom and bathroom counts
        row = box1.row(align=True)
        row.prop(self, "bedrooms", text="Bedrooms")
        row.prop(self, "bathrooms", text="Bathrooms")

        # Room checkboxes - simple column layout
        col = box1.column(align=True)
        row1 = col.row(align=True)
        row1.prop(self, "has_kitchen", text="Kitchen")
        row1.prop(self, "has_living", text="Living")
        row2 = col.row(align=True)
        row2.prop(self, "has_dining", text="Dining")
        row2.prop(self, "has_study", text="Study")
        row3 = col.row(align=True)
        row3.prop(self, "has_garage", text="Garage")

        # =====================================================================
        # SECTION 2: PLOT SIZE CONSTRAINTS (ALWAYS VISIBLE)
        # =====================================================================
        layout.separator()

        box2 = layout.box()
        box2.label(text="Plot Size Constraints", icon='ORIENTATION_LOCAL')

        # Checkbox to enable/disable
        box2.prop(self, "use_area_bounds", text="Enable Plot Size Limit")

        # Show options when enabled
        if self.use_area_bounds:
            box2.separator()

            # Unit selection
            box2.prop(self, "area_unit", text="Unit")

            # Size input based on unit
            if self.area_unit == 'dimensions':
                row = box2.row(align=True)
                row.prop(self, "plot_width", text="Width")
                row.prop(self, "plot_height", text="Depth")
            else:
                box2.prop(self, "area_value", text="Plot Size")

    def execute(self, context):
        props = context.scene.architext
        prefs = context.preferences.addons[__name__].preferences

        # Validate paths
        if not prefs.python_path or not os.path.exists(prefs.python_path):
            self.report({'ERROR'}, "Python path not set. Please configure in add-on preferences.")
            return {'CANCELLED'}

        if not prefs.scripts_path or not os.path.exists(prefs.scripts_path):
            self.report({'ERROR'}, "Scripts path not set. Please configure in add-on preferences.")
            return {'CANCELLED'}

        props.is_generating = True
        props.status_message = "Generating (Quick Mode)..."

        print("\n" + "=" * 60)
        print("ARCHITEXT: Quick Generate (Direct JSON Mode)")
        print("=" * 60)

        try:
            # Build JSON spec directly (bypasses NLP model for speed/stability)
            spec = {
                "bedrooms": self.bedrooms,
                "bathrooms": self.bathrooms,
                "kitchen": self.has_kitchen,
                "living_room": self.has_living,
                "dining_room": self.has_dining,
                "study": self.has_study,
                "garage": self.has_garage,
            }

            # Add area/plot size specification
            if self.use_area_bounds:
                if self.area_unit == 'marla':
                    # 1 marla = 25.2929 sqm
                    area_sqm = self.area_value * 25.2929
                    # Assume 1:1.5 ratio (width:depth)
                    width = (area_sqm / 1.5) ** 0.5
                    height = width * 1.5
                    spec['area_bounds'] = {'width': width, 'height': height, 'area_sqm': area_sqm}
                elif self.area_unit == 'kanal':
                    # 1 kanal = 20 marla = 505.857 sqm
                    area_sqm = self.area_value * 505.857
                    width = (area_sqm / 1.5) ** 0.5
                    height = width * 1.5
                    spec['area_bounds'] = {'width': width, 'height': height, 'area_sqm': area_sqm}
                elif self.area_unit == 'sqft':
                    area_sqm = self.area_value * 0.092903
                    width = (area_sqm / 1.5) ** 0.5
                    height = width * 1.5
                    spec['area_bounds'] = {'width': width, 'height': height, 'area_sqm': area_sqm}
                elif self.area_unit == 'sqm':
                    area_sqm = self.area_value
                    width = (area_sqm / 1.5) ** 0.5
                    height = width * 1.5
                    spec['area_bounds'] = {'width': width, 'height': height, 'area_sqm': area_sqm}
                elif self.area_unit == 'dimensions':
                    spec['area_bounds'] = {
                        'width': self.plot_width,
                        'height': self.plot_height,
                        'area_sqm': self.plot_width * self.plot_height
                    }

            # Convert spec to JSON string
            spec_json = json.dumps(spec)
            print(f"Spec: {spec_json}")

            # Prepare output path
            project_root = os.path.dirname(prefs.scripts_path)
            output_dir = os.path.join(project_root, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Call quick_generate.py (direct JSON, no NLP model)
            quick_script = os.path.join(prefs.scripts_path, "quick_generate.py")

            if not os.path.exists(quick_script):
                self.report({'ERROR'}, f"quick_generate.py not found at {quick_script}")
                props.status_message = "Error: quick_generate.py not found"
                return {'CANCELLED'}

            print(f"[OK] Using quick_generate.py (direct mode)")

            # Use Popen with temp files to avoid pipe buffer issues on Windows
            stdout_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
            stderr_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')

            try:
                startupinfo = None
                creationflags = 0
                if sys.platform == 'win32':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    creationflags = subprocess.CREATE_NO_WINDOW

                process = subprocess.Popen(
                    [prefs.python_path, quick_script, spec_json],
                    stdout=stdout_file,
                    stderr=stderr_file,
                    cwd=project_root,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )

                return_code = process.wait(timeout=60)  # Shorter timeout for quick mode

                stdout_file.seek(0)
                stderr_file.seek(0)
                stdout_content = stdout_file.read()
                stderr_content = stderr_file.read()

            finally:
                stdout_file.close()
                stderr_file.close()
                try:
                    os.unlink(stdout_file.name)
                    os.unlink(stderr_file.name)
                except:
                    pass

            print(f"[DONE] Return code: {return_code}")
            if stdout_content:
                print(f"STDOUT:\n{stdout_content[-500:]}")

            if return_code != 0:
                error_msg = stderr_content[:200] if stderr_content else "Unknown error"
                self.report({'ERROR'}, f"Generation failed: {error_msg}")
                props.status_message = f"Error: Quick mode failed"
                print(f"Quick Mode STDERR: {stderr_content}")
                return {'CANCELLED'}

            # Find generated IFC
            import glob
            import time

            # Small delay to ensure file is fully written
            time.sleep(0.5)

            ifc_files = glob.glob(os.path.join(output_dir, "*.ifc"))
            if ifc_files:
                ifc_path = max(ifc_files, key=os.path.getmtime)
                print(f"[Quick Mode] Generated: {ifc_path}")

                # Validate file exists and has content
                if not os.path.exists(ifc_path):
                    print(f"[Quick Mode] ERROR: File not found: {ifc_path}")
                    props.status_message = "Error: IFC file not found"
                    return {'CANCELLED'}

                file_size = os.path.getsize(ifc_path)
                print(f"[Quick Mode] File size: {file_size} bytes")
                if file_size < 1000:  # IFC files should be at least 1KB
                    print(f"[Quick Mode] WARNING: File seems too small, may be incomplete")

                # Import with extra safety checks
                if props.auto_import:
                    try:
                        if props.clear_scene:
                            bpy.ops.object.select_all(action='SELECT')
                            bpy.ops.object.delete()

                        # Try native IFC import FIRST (more stable, less likely to crash)
                        imported = False
                        try:
                            if hasattr(bpy.ops, 'import_scene') and hasattr(bpy.ops.import_scene, 'ifc'):
                                bpy.ops.import_scene.ifc(filepath=ifc_path)
                                imported = True
                                print("[Quick Mode] Imported via native IFC")
                        except Exception as e:
                            print(f"[Quick Mode] Native IFC import failed: {e}")

                        # Fallback to BlenderBIM (can crash Blender in some cases)
                        if not imported:
                            try:
                                if hasattr(bpy.ops, 'bim') and hasattr(bpy.ops.bim, 'load_project'):
                                    bpy.ops.bim.load_project(filepath=ifc_path)
                                    imported = True
                                    print("[Quick Mode] Imported via BlenderBIM")
                            except Exception as e:
                                print(f"[Quick Mode] BlenderBIM import failed: {e}")

                        if not imported:
                            print(f"[Quick Mode] Could not auto-import. File at: {ifc_path}")

                    except Exception as e:
                        print(f"[Quick Mode] Import error: {e}")

                props.status_message = f"Success! {os.path.basename(ifc_path)}"
                self.report({'INFO'}, f"Generated: {ifc_path}")
            else:
                props.status_message = "Generated - check output folder"
                self.report({'INFO'}, "Building generated!")

        except subprocess.TimeoutExpired:
            self.report({'ERROR'}, "Generation timed out")
            props.status_message = "Error: Timeout"
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, str(e))
            props.status_message = f"Error: {str(e)[:50]}"
            return {'CANCELLED'}

        finally:
            props.is_generating = False

        return {'FINISHED'}


class ARCHITEXT_OT_LoadExample(Operator):
    """Load an example prompt"""
    bl_idname = "architext.load_example"
    bl_label = "Load Example"

    example: EnumProperty(
        items=[
            ('small', "Small House", "2 bedroom starter home"),
            ('family', "Family Home", "3 bedroom family house"),
            ('luxury', "Luxury Villa", "4 bedroom luxury home"),
            ('apartment', "Apartment", "1 bedroom apartment"),
        ]
    )

    def execute(self, context):
        props = context.scene.architext

        examples = {
            'small': "Compact 2 bedroom house with 1 bathroom, open kitchen and living area",
            'family': "Modern 3 bedroom family house with 2 bathrooms, kitchen, dining room, and spacious living room",
            'luxury': "Luxury 4 bedroom villa with master suite, 3 bathrooms, study, open plan kitchen-dining, large living room",
            'apartment': "Contemporary 1 bedroom apartment with bathroom, combined kitchen-living area",
        }

        props.prompt = examples.get(self.example, examples['family'])
        return {'FINISHED'}


class ARCHITEXT_OT_OpenOutput(Operator):
    """Open the output folder"""
    bl_idname = "architext.open_output"
    bl_label = "Open Output Folder"

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences

        if prefs.scripts_path:
            output_dir = os.path.join(os.path.dirname(prefs.scripts_path), "output")
        else:
            self.report({'WARNING'}, "Scripts path not configured")
            return {'CANCELLED'}

        if os.path.exists(output_dir):
            # Cross-platform folder open
            if sys.platform == 'win32':
                os.startfile(output_dir)
            elif sys.platform == 'darwin':
                subprocess.run(['open', output_dir])
            else:
                subprocess.run(['xdg-open', output_dir])
        else:
            os.makedirs(output_dir, exist_ok=True)
            self.report({'INFO'}, f"Created output folder: {output_dir}")

        return {'FINISHED'}


# ============================================================================
# UI PANELS
# ============================================================================

class ARCHITEXT_PT_MainPanel(Panel):
    """Main ArchiText Panel"""
    bl_label = "ArchiText"
    bl_idname = "ARCHITEXT_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ArchiText'

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='HOME')

    def draw(self, context):
        layout = self.layout
        props = context.scene.architext

        # Header
        box = layout.box()
        row = box.row()
        row.scale_y = 1.5
        row.label(text="Text to BIM Generator", icon='MOD_BUILD')


class ARCHITEXT_PT_TextInput(Panel):
    """Text Input Panel"""
    bl_label = "Describe Your Building"
    bl_idname = "ARCHITEXT_PT_text_input"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ArchiText'
    bl_parent_id = "ARCHITEXT_PT_main"

    def draw(self, context):
        layout = self.layout
        props = context.scene.architext

        box = layout.box()
        col = box.column(align=True)
        col.scale_y = 1.2
        col.prop(props, "prompt", text="")

        row = box.row(align=True)
        row.label(text="Examples:", icon='PRESET')
        row.operator_menu_enum("architext.load_example", "example", text="Load", icon='DOWNARROW_HLT')


class ARCHITEXT_PT_Generate(Panel):
    """Generate Panel"""
    bl_label = "Generate"
    bl_idname = "ARCHITEXT_PT_generate"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ArchiText'
    bl_parent_id = "ARCHITEXT_PT_main"

    def draw(self, context):
        layout = self.layout
        props = context.scene.architext

        col = layout.column(align=True)
        col.scale_y = 2.0

        if props.is_generating:
            col.operator("architext.generate", text="Generating...", icon='SORTTIME')
            col.enabled = False
        else:
            col.operator("architext.generate", text="Generate Building", icon='PLAY')

        row = layout.row()
        row.scale_y = 1.3
        row.operator("architext.generate_quick", text="Quick Mode", icon='CON_SPLINEIK')

        # Status
        box = layout.box()
        row = box.row()
        if "Error" in props.status_message:
            row.label(text=props.status_message, icon='ERROR')
        elif "Success" in props.status_message:
            row.label(text=props.status_message, icon='CHECKMARK')
        else:
            row.label(text=props.status_message, icon='INFO')


class ARCHITEXT_PT_Settings(Panel):
    """Settings Panel"""
    bl_label = "Settings"
    bl_idname = "ARCHITEXT_PT_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ArchiText'
    bl_parent_id = "ARCHITEXT_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.architext

        box = layout.box()
        box.label(text="Building Settings", icon='SETTINGS')
        col = box.column(align=True)
        col.prop(props, "wall_height")
        col.prop(props, "wall_thickness")
        # Note: style_preset removed from UI - not yet implemented

        box = layout.box()
        box.label(text="Import Options", icon='IMPORT')
        col = box.column(align=True)
        col.prop(props, "auto_import")
        col.prop(props, "clear_scene")


class ARCHITEXT_PT_Tools(Panel):
    """Tools Panel"""
    bl_label = "Tools"
    bl_idname = "ARCHITEXT_PT_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ArchiText'
    bl_parent_id = "ARCHITEXT_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("architext.open_output", text="Open Output Folder", icon='FILE_FOLDER')
        col.operator("architext.test_config", text="Test Configuration", icon='CHECKMARK')


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    ARCHITEXT_Properties,
    ARCHITEXT_Preferences,
    ARCHITEXT_OT_AutoDetectPaths,
    ARCHITEXT_OT_TestConfig,
    ARCHITEXT_OT_Generate,
    ARCHITEXT_OT_GenerateQuick,
    ARCHITEXT_OT_LoadExample,
    ARCHITEXT_OT_OpenOutput,
    ARCHITEXT_PT_MainPanel,
    ARCHITEXT_PT_TextInput,
    ARCHITEXT_PT_Generate,
    ARCHITEXT_PT_Settings,
    ARCHITEXT_PT_Tools,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.architext = PointerProperty(type=ARCHITEXT_Properties)
    print("ArchiText add-on registered successfully!")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.architext
    print("ArchiText add-on unregistered.")


if __name__ == "__main__":
    register()
