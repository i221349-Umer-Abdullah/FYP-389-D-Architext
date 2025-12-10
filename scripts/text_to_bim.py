"""
=============================================================================
ArchiText: Text-to-BIM Pipeline - Main Orchestration Module
=============================================================================

PIPELINE ORCHESTRATOR: This module is the main entry point for the ArchiText
system, coordinating the multi-layer architecture that converts natural language
building descriptions into industry-standard IFC (Industry Foundation Classes)
BIM files compatible with Revit, ArchiCAD, and other BIM software.

=============================================================================
COMPLETE SYSTEM ARCHITECTURE
=============================================================================

The ArchiText pipeline implements a sophisticated multi-layer deep learning
and optimization architecture:

┌─────────────────────────────────────────────────────────────────────────────┐
│                        ARCHITEXT PIPELINE ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ LAYER 1: Natural Language Processing (inference_nlp.py)              │   │
│  │ ════════════════════════════════════════════════════════════════════ │   │
│  │ Model: Fine-tuned T5-small Transformer                               │   │
│  │ Training: Custom dataset + architectural terminology                  │   │
│  │ Input:  "Modern 3 bedroom house with 2 bathrooms"                    │   │
│  │ Output: {"bedrooms": 3, "bathrooms": 2, "kitchen": true, ...}        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ LAYER 2: Graph-Based Layout Engine (graph_layout_optimizer.py)       │   │
│  │ ════════════════════════════════════════════════════════════════════ │   │
│  │ Core: Graph construction with rooms as nodes, connections as edges   │   │
│  │ Templates: 8 architectural layouts derived from CubiCasa5k analysis  │   │
│  │ Algorithm: Constraint satisfaction + compactness optimization        │   │
│  │ Input:  JSON specification from Layer 1                              │   │
│  │ Output: Room positions (x, y, width, height) + connection graph      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ LAYER 3: Quality Assurance System                                    │   │
│  │ ════════════════════════════════════════════════════════════════════ │   │
│  │ Overlap Detection: Axis-aligned bounding box intersection tests      │   │
│  │ Overlap Repair: Iterative push-apart algorithm (max 50 iterations)   │   │
│  │ Boundary Check: Plot size constraint enforcement                     │   │
│  │ Connectivity: Ensures all rooms are accessible via doors             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ LAYER 4: IFC BIM Generation (generate_bim.py)                        │   │
│  │ ════════════════════════════════════════════════════════════════════ │   │
│  │ Standard: IFC 2x3 (Industry Foundation Classes)                      │   │
│  │ Hierarchy: IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey   │   │
│  │ Elements: IfcWall (exterior/interior), IfcSpace (rooms)              │   │
│  │ Output: .ifc file compatible with Revit, ArchiCAD, BlenderBIM        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

=============================================================================
MODULE RESPONSIBILITIES
=============================================================================

This module (text_to_bim.py) orchestrates the entire pipeline:

    1. INITIALIZATION
       - Loads the trained T5 NLP model from checkpoint
       - Initializes the Graph-Based Layout Engine
       - Sets up the Area Parser for plot size constraints

    2. PROCESSING FLOW
       - Receives natural language input from user
       - Passes text through NLP model for specification extraction
       - Parses any area/plot size constraints (marla, kanal, sqm, etc.)
       - Invokes the Layout Engine for spatial optimization
       - Triggers IFC generation with the optimized layout

    3. OUTPUT
       - Returns result dictionary with:
         - input_text: Original user input
         - specification: Extracted JSON spec
         - area_bounds: Plot constraints (if specified)
         - ifc_file: Path to generated IFC file
         - success: Boolean indicating success/failure

=============================================================================
USAGE EXAMPLES
=============================================================================

Basic Usage:
    >>> from text_to_bim import TextToBIMPipeline
    >>>
    >>> pipeline = TextToBIMPipeline()
    >>> result = pipeline.generate(
    ...     "Modern 3 bedroom house with 2 bathrooms and open kitchen"
    ... )
    >>> print(f"Generated: {result['ifc_file']}")

With Plot Constraints:
    >>> result = pipeline.generate(
    ...     "3 bedroom house on 5 marla plot with 2 bathrooms",
    ...     output_path="output/my_house.ifc"
    ... )

Custom Model Path:
    >>> pipeline = TextToBIMPipeline(model_path="models/custom_checkpoint")

=============================================================================
DEPENDENCIES
=============================================================================

    - inference_nlp.py:        T5 model inference for text-to-spec
    - graph_layout_optimizer.py: Graph-based spatial layout engine
    - generate_bim.py:         IFC file generation using IfcOpenShell
    - area_parser.py:          South Asian unit parsing (marla, kanal)

=============================================================================
Author: ArchiText Team
Version: 2.0.0 (Multi-Layer Architecture)
=============================================================================
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Optional

# =============================================================================
# PATH CONFIGURATION
# =============================================================================
# Ensure proper module imports regardless of how the script is executed

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# =============================================================================
# MODULE IMPORTS
# =============================================================================
# Handle both package-style and direct script execution

try:
    from scripts.inference_nlp import TextToSpecInference
    from scripts.generate_bim import BIMGenerator
    from scripts.area_parser import AreaParser
except ImportError:
    # Direct import when running from scripts directory
    from inference_nlp import TextToSpecInference
    from generate_bim import BIMGenerator
    from area_parser import AreaParser


# =============================================================================
# MAIN PIPELINE CLASS
# =============================================================================

class TextToBIMPipeline:
    """
    Complete Text-to-BIM conversion pipeline.

    This class orchestrates the entire conversion process from natural language
    to IFC BIM files. It combines:

    1. A trained NLP model (T5 transformer) for text understanding
    2. A rule-based layout optimizer for architectural refinement
    3. An IFC generator for BIM file creation

    The pipeline ensures that the AI model's output is enhanced by architectural
    rules before being converted to a valid IFC file.

    Attributes:
        nlp_inferencer (TextToSpecInference): The NLP model for text-to-spec conversion
        bim_generator (BIMGenerator): The IFC generation engine

    Example:
        >>> pipeline = TextToBIMPipeline()
        >>> result = pipeline.generate("3 bedroom house with garage")
        >>> print(result['ifc_file'])  # Path to generated IFC
    """

    def __init__(self, model_path: str = None):
        """
        Initialize the Text-to-BIM pipeline.

        This sets up both the NLP inference engine (trained model) and the
        BIM generator. The NLP model is loaded from the specified path or
        the default model directory.

        Args:
            model_path (str, optional): Path to the trained NLP model checkpoint.
                                        If None, uses the default model location.

        Raises:
            FileNotFoundError: If the model checkpoint cannot be found
            RuntimeError: If model loading fails
        """
        print("=" * 80)
        print("  INITIALIZING ARCHITEXT PIPELINE")
        print("=" * 80)

        # ---------------------------------------------------------------------
        # LAYER 1: Initialize NLP Model (Trained T5 Transformer)
        # ---------------------------------------------------------------------
        # The NLP model is a fine-tuned T5-small transformer trained on
        # building descriptions to extract structured specifications
        print("\n[1/2] Loading trained NLP model (T5 Transformer)...")
        self.nlp_inferencer = TextToSpecInference(model_path)
        print("      Model loaded successfully")

        # ---------------------------------------------------------------------
        # LAYER 2: Initialize BIM Generator (with Layout Optimizer)
        # ---------------------------------------------------------------------
        # The BIM generator includes the rule-based layout optimizer that
        # enhances the model output with architectural constraints
        print("[2/2] Initializing BIM Generator with Layout Optimizer...")
        self.bim_generator = BIMGenerator()
        print("      Generator ready")

        # Initialize area parser for plot size constraints
        self.area_parser = AreaParser()

        print("\n" + "-" * 80)
        print("[OK] ArchiText Pipeline initialized successfully!")
        print("-" * 80 + "\n")

    def generate(self, text: str, output_path: str = None, verbose: bool = True,
                 wall_height: float = 2.7) -> Dict:
        """
        Convert natural language description to IFC BIM file.

        This is the main entry point for the pipeline. It takes a text description,
        processes it through the trained NLP model, enhances the output using
        the rule-based layout optimizer, and generates an IFC file.

        Processing Steps:
            1. NLP Model: Text → JSON specification (trained model)
            2. Layout Optimizer: Apply architectural constraints (rule-based)
            3. BIM Generator: Create IFC file with walls and spaces

        Args:
            text (str): Natural language building description.
                        Example: "Modern 3 bedroom house with 2 bathrooms"
            output_path (str, optional): Path for the output IFC file.
                                         If None, auto-generates a timestamped path.
            verbose (bool): Whether to print progress messages. Default True.
            wall_height (float): Height of walls in meters. Default 2.7m.

        Returns:
            dict: Result dictionary containing:
                - 'input_text' (str): The original input text
                - 'specification' (dict): The extracted JSON specification
                - 'ifc_file' (str): Path to the generated IFC file
                - 'success' (bool): Whether generation succeeded
                - 'error' (str, optional): Error message if failed

        Example:
            >>> result = pipeline.generate("2 bedroom apartment with kitchen")
            >>> if result['success']:
            ...     print(f"Generated: {result['ifc_file']}")
        """
        # Initialize result dictionary
        result = {
            "input_text": text,
            "success": False
        }

        try:
            # =================================================================
            # STEP 1: Natural Language Processing (Trained Model)
            # =================================================================
            # The NLP model (T5 transformer) converts the text description
            # into a structured JSON specification

            if verbose:
                print("=" * 80)
                print("  STEP 1: NLP Processing (Trained T5 Model)")
                print("=" * 80)
                print(f"\n  Input Text: \"{text}\"\n")

            # Run inference on the trained model
            spec = self.nlp_inferencer.predict(text)
            result["specification"] = spec

            if verbose:
                print("  Extracted Specification:")
                print("  " + "-" * 40)
                for key, value in spec.items():
                    if key not in ['status', 'raw_output']:
                        print(f"    {key}: {value}")
                print()

            # Validate the model output
            if "status" in spec and spec["status"] == "invalid_json":
                result["error"] = "NLP model generated invalid specification"
                if verbose:
                    print("  [ERROR] Model output validation failed")
                return result

            # =================================================================
            # STEP 1.5: Parse Area/Plot Bounds (if specified)
            # =================================================================
            area_bounds = self.area_parser.parse(text)
            if area_bounds and verbose:
                print("  Plot Size Detected:")
                print("  " + "-" * 40)
                print(f"    Dimensions: {area_bounds.width:.1f}m x {area_bounds.height:.1f}m")
                print(f"    Area: {area_bounds.area_sqm:.1f} sqm ({area_bounds.area_marla:.1f} marla)")
                print()

            # Add area bounds to spec for BIM generator
            if area_bounds:
                spec['area_bounds'] = {
                    'width': area_bounds.width,
                    'height': area_bounds.height,
                    'area_sqm': area_bounds.area_sqm
                }
                result['area_bounds'] = spec['area_bounds']

            # =================================================================
            # STEP 2: Layout Optimization + BIM Generation
            # =================================================================
            # The rule-based optimizer enhances the model output by:
            # - Applying architectural constraints
            # - Ensuring proper room adjacencies
            # - Validating room dimensions
            # - Optimizing spatial layout

            if verbose:
                print("=" * 80)
                print("  STEP 2: Layout Optimization + BIM Generation")
                print("=" * 80)
                if area_bounds:
                    print(f"\n  Constraining layout to {area_bounds.width:.1f}m x {area_bounds.height:.1f}m plot...")
                else:
                    print("\n  Applying architectural rules to optimize layout...")

            # Create a new BIM generator instance for this building
            # (The generator includes the rule-based layout optimizer)
            bim_gen = BIMGenerator()
            ifc_path = bim_gen.generate_from_spec(spec, output_path)

            # Record success
            result["ifc_file"] = ifc_path
            result["success"] = True

            if verbose:
                print()
                print("=" * 80)
                print("  [SUCCESS] Building Generated!")
                print("=" * 80)
                print(f"\n  Output File: {ifc_path}")
                print("\n  Compatible with: Revit, BlenderBIM, FreeCAD, ArchiCAD")
                print("=" * 80)

            return result

        except Exception as e:
            # Handle any errors during generation
            result["error"] = str(e)
            if verbose:
                print(f"\n  [ERROR]: {e}")
            return result


# =============================================================================
# DEMONSTRATION / CLI ENTRY POINT
# =============================================================================

def main():
    """
    Demonstrate the Text-to-BIM pipeline with example inputs.

    This function showcases the pipeline's capabilities by processing
    several example building descriptions and generating IFC files.
    """
    # Initialize the pipeline (loads NLP model and BIM generator)
    pipeline = TextToBIMPipeline()

    # Example building descriptions to demonstrate capabilities
    examples = [
        "A modern 3-bedroom house with 2 bathrooms, a spacious kitchen, living room, and dining room",
        "A cozy 2-bedroom apartment with 1 bathroom and an open-plan kitchen and living area",
        "A small studio apartment with bathroom and kitchenette"
    ]

    print("\n" + "=" * 80)
    print("  ARCHITEXT: TEXT-TO-BIM DEMONSTRATION")
    print("=" * 80 + "\n")

    # Process each example
    for i, description in enumerate(examples, 1):
        print(f"\n{'#' * 80}")
        print(f"  EXAMPLE {i}/{len(examples)}")
        print(f"{'#' * 80}\n")

        # Generate BIM from text
        result = pipeline.generate(description, verbose=True)

        # Report result
        if result["success"]:
            print(f"\n  [OK] Building generated successfully!")
            print(f"       File: {result['ifc_file']}")
        else:
            print(f"\n  [FAILED] Generation failed: {result.get('error', 'Unknown error')}")

        print()

    # Summary
    print("=" * 80)
    print("  DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\n  Generated IFC files can be opened in:")
    print("    - Autodesk Revit (File > Open > IFC)")
    print("    - BlenderBIM / Bonsai (File > Open IFC Project)")
    print("    - FreeCAD (File > Import > IFC)")
    print("    - Any IFC-compatible BIM viewer")
    print()


if __name__ == "__main__":
    main()
