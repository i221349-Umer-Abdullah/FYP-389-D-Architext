"""
=============================================================================
ArchiText: Blender Add-on for Text-to-BIM Generation
=============================================================================

This Blender add-on provides a user-friendly interface for the ArchiText
Text-to-BIM pipeline, allowing architects and designers to generate 3D
building models directly within Blender using natural language descriptions.

Features:
---------
    - Natural Language Input: Describe buildings in plain English
    - AI-Powered Generation: Uses trained T5 transformer for text understanding
    - Rule-Based Enhancement: Layout optimizer ensures architectural validity
    - Direct Blender Integration: Automatic import of generated IFC models
    - Quick Mode: Bypass NLP for direct specification input
    - Style Presets: Modern, Traditional, Minimalist, Luxury

Architecture Integration:
-------------------------
    The add-on connects to the ArchiText pipeline:

    Blender UI (This Add-on)
        │
        ├── Full Mode: Uses complete pipeline
        │   └── NLP Model (Layer 1) → Layout Optimizer (Layer 2) → IFC (Layer 3)
        │
        └── Quick Mode: Direct specification
            └── Layout Optimizer (Layer 2) → IFC (Layer 3)

Requirements:
-------------
    - Blender 4.0 or higher
    - Bonsai/BlenderBIM add-on (for IFC import)
    - ArchiText scripts directory configured in preferences
    - PyTorch and Transformers (for NLP mode, optional)

Installation:
-------------
    1. Package the add-on using: python blender_addon/package_addon.py
    2. In Blender: Edit → Preferences → Add-ons → Install
    3. Select the generated architext_addon.zip
    4. Enable "ArchiText - Text to BIM"
    5. Configure scripts path in add-on preferences

Usage:
------
    1. Open Blender's sidebar (N key) → ArchiText tab
    2. Enter a building description or load an example
    3. Click "Generate Building" to create the model
    4. The IFC file will be automatically imported if Bonsai is installed

Author: ArchiText Team
Version: 1.0.0
=============================================================================
"""

bl_info = {
    "name": "ArchiText - Text to BIM",
    "author": "ArchiText Team",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > ArchiText",
    "description": "Generate 3D building models from natural language descriptions",
    "category": "3D View",
}

import bpy
import os
import sys
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

    # Style presets
    style_preset: EnumProperty(
        name="Style",
        description="Building style preset",
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

    scripts_path: StringProperty(
        name="Scripts Path",
        description="Path to ArchiText scripts folder",
        default="",
        subtype='DIR_PATH',
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "scripts_path")

        if not self.scripts_path:
            layout.label(text="Please set the path to your ArchiText scripts folder", icon='ERROR')


# ============================================================================
# OPERATORS
# ============================================================================

class ARCHITEXT_OT_Generate(Operator):
    """Generate a building from text description"""
    bl_idname = "architext.generate"
    bl_label = "Generate Building"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.architext
        prefs = context.preferences.addons[__name__].preferences

        # Get scripts path
        scripts_path = prefs.scripts_path
        if not scripts_path:
            # Try to find it relative to add-on
            addon_dir = os.path.dirname(os.path.realpath(__file__))
            possible_paths = [
                os.path.join(addon_dir, "..", "..", "scripts"),
                os.path.join(addon_dir, "..", "..", "..", "architext", "scripts"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    scripts_path = os.path.abspath(p)
                    break

        if not scripts_path or not os.path.exists(scripts_path):
            self.report({'ERROR'}, "Scripts path not found. Please set it in add-on preferences.")
            return {'CANCELLED'}

        # Add to path
        if scripts_path not in sys.path:
            sys.path.insert(0, scripts_path)

        props.is_generating = True
        props.status_message = "Generating layout..."

        try:
            # Check if transformers is available
            try:
                import transformers
                has_nlp = True
            except ImportError:
                has_nlp = False

            if has_nlp:
                # Full NLP pipeline
                from text_to_bim import TextToBIMPipeline
                pipeline = TextToBIMPipeline()

                output_dir = os.path.join(os.path.dirname(scripts_path), "output")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, "blender_generated.ifc")

                props.status_message = "Processing text with AI..."

                result = pipeline.generate(
                    props.prompt,
                    output_path=output_path,
                    wall_height=props.wall_height,
                )
            else:
                # Fallback: Parse text simply and use rule-based
                props.status_message = "Using rule-based generator..."

                from generate_bim import BIMGenerator
                from layout_optimizer_rules import RuleBasedLayoutOptimizer

                # Simple text parsing
                text = props.prompt.lower()
                spec = {
                    "bedrooms": 0,
                    "bathrooms": 0,
                    "kitchen": False,
                    "living_room": False,
                    "dining_room": False,
                    "study": False,
                    "garage": False,
                }

                # Parse bedrooms
                import re
                bed_match = re.search(r'(\d+)\s*(?:bed(?:room)?s?)', text)
                if bed_match:
                    spec["bedrooms"] = int(bed_match.group(1))
                elif "bedroom" in text:
                    spec["bedrooms"] = 1

                # Parse bathrooms
                bath_match = re.search(r'(\d+)\s*(?:bath(?:room)?s?)', text)
                if bath_match:
                    spec["bathrooms"] = int(bath_match.group(1))
                elif "bathroom" in text or "bath" in text:
                    spec["bathrooms"] = 1

                # Parse other rooms
                spec["kitchen"] = "kitchen" in text
                spec["living_room"] = "living" in text or "lounge" in text
                spec["dining_room"] = "dining" in text
                spec["study"] = "study" in text or "office" in text
                spec["garage"] = "garage" in text

                # Ensure minimum rooms
                if spec["bedrooms"] == 0:
                    spec["bedrooms"] = 2
                if spec["bathrooms"] == 0:
                    spec["bathrooms"] = 1
                if not spec["kitchen"]:
                    spec["kitchen"] = True
                if not spec["living_room"]:
                    spec["living_room"] = True

                # Generate
                generator = BIMGenerator()
                output_dir = os.path.join(os.path.dirname(scripts_path), "output")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, "blender_generated.ifc")

                generator.generate_from_spec(spec, output_path)
                result = {"success": True, "ifc_file": output_path}

            props.status_message = "IFC file created!"

            # Auto import if enabled
            if props.auto_import and os.path.exists(output_path):
                props.status_message = "Importing into Blender..."

                # Clear scene if requested
                if props.clear_scene:
                    bpy.ops.object.select_all(action='SELECT')
                    bpy.ops.object.delete()

                # Try to use Bonsai/BlenderBIM to import
                try:
                    bpy.ops.bim.load_project(filepath=output_path)
                    props.status_message = "Building imported successfully!"
                except Exception as e:
                    # Fallback: just report the file location
                    props.status_message = f"Generated: {output_path}"
                    self.report({'INFO'}, f"IFC file saved to: {output_path}")

            self.report({'INFO'}, f"Building generated successfully!")

        except ImportError as e:
            props.status_message = f"Import error: {str(e)}"
            self.report({'ERROR'}, f"Could not import modules: {str(e)}")
            return {'CANCELLED'}

        except Exception as e:
            props.status_message = f"Error: {str(e)}"
            self.report({'ERROR'}, f"Generation failed: {str(e)}")
            return {'CANCELLED'}

        finally:
            props.is_generating = False

        return {'FINISHED'}


class ARCHITEXT_OT_GenerateQuick(Operator):
    """Generate building using rule-based optimizer (faster, no NLP)"""
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

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "bedrooms")
        layout.prop(self, "bathrooms")
        layout.separator()
        col = layout.column(align=True)
        col.prop(self, "has_kitchen")
        col.prop(self, "has_living")
        col.prop(self, "has_dining")
        col.prop(self, "has_study")
        col.prop(self, "has_garage")

    def execute(self, context):
        props = context.scene.architext
        prefs = context.preferences.addons[__name__].preferences

        # Get scripts path
        scripts_path = prefs.scripts_path
        if not scripts_path:
            addon_dir = os.path.dirname(os.path.realpath(__file__))
            possible_paths = [
                os.path.join(addon_dir, "..", "..", "scripts"),
                os.path.join(addon_dir, "..", "..", "..", "architext", "scripts"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    scripts_path = os.path.abspath(p)
                    break

        if not scripts_path or not os.path.exists(scripts_path):
            self.report({'ERROR'}, "Scripts path not found.")
            return {'CANCELLED'}

        if scripts_path not in sys.path:
            sys.path.insert(0, scripts_path)

        props.is_generating = True
        props.status_message = "Generating..."

        try:
            from generate_bim import BIMGenerator
            from layout_optimizer_rules import RuleBasedLayoutOptimizer

            # Build spec
            spec = {
                "bedrooms": self.bedrooms,
                "bathrooms": self.bathrooms,
                "kitchen": self.has_kitchen,
                "living_room": self.has_living,
                "dining_room": self.has_dining,
                "study": self.has_study,
                "garage": self.has_garage,
            }

            # Generate
            generator = BIMGenerator()
            output_dir = os.path.join(os.path.dirname(scripts_path), "output")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "blender_quick_generated.ifc")

            result = generator.generate_from_spec(spec, output_path)

            props.status_message = "IFC created!"

            # Auto import
            if props.auto_import and os.path.exists(output_path):
                if props.clear_scene:
                    bpy.ops.object.select_all(action='SELECT')
                    bpy.ops.object.delete()

                try:
                    bpy.ops.bim.load_project(filepath=output_path)
                    props.status_message = "Imported successfully!"
                except:
                    props.status_message = f"Saved: {output_path}"

            self.report({'INFO'}, "Building generated!")

        except Exception as e:
            props.status_message = f"Error: {str(e)}"
            self.report({'ERROR'}, str(e))
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
            'luxury': "Luxury 4 bedroom villa with master suite, 3 bathrooms, study, open plan kitchen-dining, large living room, and home gym",
            'apartment': "Contemporary 1 bedroom apartment with bathroom, combined kitchen-living area, and small study nook",
        }

        props.prompt = examples.get(self.example, examples['family'])
        return {'FINISHED'}


class ARCHITEXT_OT_OpenOutput(Operator):
    """Open the output folder"""
    bl_idname = "architext.open_output"
    bl_label = "Open Output Folder"

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        scripts_path = prefs.scripts_path

        if scripts_path:
            output_dir = os.path.join(os.path.dirname(scripts_path), "output")
        else:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "output")

        if os.path.exists(output_dir):
            import subprocess
            subprocess.Popen(f'explorer "{output_dir}"')
        else:
            self.report({'WARNING'}, "Output folder not found")

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

        # Header with logo/title
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

        # Text input area
        box = layout.box()
        col = box.column(align=True)
        col.scale_y = 1.2
        col.prop(props, "prompt", text="")

        # Example prompts dropdown
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

        # Main generate button
        col = layout.column(align=True)
        col.scale_y = 2.0

        if props.is_generating:
            col.operator("architext.generate", text="Generating...", icon='SORTTIME')
            col.enabled = False
        else:
            col.operator("architext.generate", text="Generate Building", icon='PLAY')

        # Quick generate
        row = layout.row()
        row.scale_y = 1.3
        row.operator("architext.generate_quick", text="Quick Mode", icon='CON_SPLINEIK')

        # Status
        box = layout.box()
        row = box.row()
        if "Error" in props.status_message:
            row.label(text=props.status_message, icon='ERROR')
        elif "success" in props.status_message.lower() or "imported" in props.status_message.lower():
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

        # Building settings
        box = layout.box()
        box.label(text="Building Settings", icon='SETTINGS')
        col = box.column(align=True)
        col.prop(props, "wall_height")
        col.prop(props, "wall_thickness")
        col.prop(props, "style_preset")

        # Import settings
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


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    ARCHITEXT_Properties,
    ARCHITEXT_Preferences,
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
