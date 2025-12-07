Text-to-BIM House Generation - Revised Implementation Plan
Executive Summary
Now that you have Revit 2026.1 access, we can develop directly for the industry-standard platform. This plan consolidates the Revit API approach with our AI training requirements.

User Review Required
IMPORTANT

Major Decision: Revit vs BlenderBIM

Developing directly for Revit is MORE VALUABLE for your FYP because:

Industry standard (Revit holds ~70% market share)
Your panel will see real professional value
Direct deployment path to end users
ResBIM dataset provides 1000+ Revit .RVT files for training
WARNING

IfcOpenShell is NOT needed for Revit approach

IfcOpenShell is a Python library for reading/writing IFC files (open BIM format). Since we're targeting Revit directly, we use the Revit API (C#/Python) instead. IFC export can be done from Revit natively if needed for compatibility.

AI Modules & Dataset Requirements
Module 1: Text-to-Spec AI (NLP Core)
Aspect	Details
Purpose	Convert natural language → structured JSON specification
Model	Fine-tuned T5-small (~60MB)
Training Data	Text descriptions paired with JSON specs
Dataset Sources	Synthetic generation + GPT-4 augmentation
Samples Needed	1,000-5,000 text-spec pairs
Justification	Custom domain vocabulary (architectural terms)
Module 2: Layout Generator AI
Aspect	Details
Purpose	Generate optimal room layouts from specifications
Model	HouseDiffusion (already set up) OR simpler CNN
Training Data	2D floor plan layouts with room annotations
Dataset Sources	CubiCasa5k (✅ downloaded), RPLAN (pending)
Samples Needed	5,000+ layouts
Justification	Learn spatial relationships & constraints
Module 3: BIM Generation Engine
Aspect	Details
Purpose	Convert layout → 3D Revit model with proper elements
Model	Rule-based + ML for optimization
Training Data	Paired 2D plans + 3D BIM models
Dataset Sources	ResBIM (1000+ RVT files)
Samples Needed	500+ paired samples
Justification	Learn BIM element placement patterns
Dataset Analysis
✅ Datasets You Have (Ready to Use)
1. CubiCasa5k (Downloaded)
Location: D:\Work\Uni\FYP\Dataset\cubicasa5k
Size: ~5,000 floor plans
Format: PNG images + SVG annotations
Quality Tiers: high_quality, high_quality_architectural, colorful
Use For: Layout Generator AI training
Contents per sample:
F1_original.png
 - Original floor plan image
F1_scaled.png
 - Scaled version
model.svg
 - Vector annotation with room boundaries
2. FloorPlanCAD (Downloaded)
Location: D:\Work\Uni\FYP\Dataset\FloorPlanCAD
Size: 1,000+ CAD floor plans (PNG + SVG)
Format: Architectural drawings with annotations
Use For: Layout AI training (diversifies dataset)
🎯 Datasets to Download (HIGH PRIORITY)
3. ResBIM Dataset ⭐ CRITICAL
Source: Google Drive
Size: 7GB (1000+ models)
Format: Paired .RVT (Revit) + 2D floor plans
Use For: BIM Generation training (learn 2D→3D conversion)
Why Critical: Only dataset with actual Revit files!
❌ Datasets NOT Applicable
Dataset	Reason
BIMNet	For scan-to-BIM (3D point cloud → BIM) - different problem
HouseExpo	Interior navigation, not floor plan generation
RPLAN	Requires official request (still pending approval)
BIMData IFC Files	Some links broken, mostly commercial buildings
Revit Development Strategy
Why Revit is Easier Than BlenderBIM
Aspect	Revit Approach	BlenderBIM Approach
API Maturity	15+ years, extensive documentation	Newer, fewer resources
Industry Adoption	~70% market share	Niche/growing
Element Creation	Native families & parameters	Manual IfcOpenShell coding
Output Quality	Production-ready .RVT	Requires IFC conversion
Learning Curve	Steeper initially, but better payoff	Easier start, harder scaling
Revit Plugin Architecture
┌─────────────────────────────────────────────────────────────┐
│                    Revit 2026 Plugin                        │
├─────────────────────────────────────────────────────────────┤
│   User Interface (WPF/XAML)                                 │
│   ├── Text Input Panel                                      │
│   ├── Preview Window                                        │
│   └── Generation Options                                    │
├─────────────────────────────────────────────────────────────┤
│   AI Backend (Python Flask API)                             │
│   ├── Text-to-Spec (T5 Model)                              │
│   ├── Layout Generator                                      │
│   └── BIM Element Mapper                                    │
├─────────────────────────────────────────────────────────────┤
│   Revit API Integration (C#)                                │
│   ├── Wall Creation                                         │
│   ├── Room Placement                                        │
│   ├── Door/Window Insertion                                 │
│   └── Level Management                                      │
└─────────────────────────────────────────────────────────────┘
Justification for AI Training (For Panel)
Why Fine-Tuning is Necessary
Domain-Specific Vocabulary: Pre-trained models don't understand "en-suite bathroom", "open-plan kitchen", or "3-bed semi-detached"

Structured Output: Need JSON format that maps to BIM elements, not free-form text

Accuracy Improvement: Generic models produce ~60% accuracy; fine-tuned models achieve >90% on domain-specific tasks

Unique Contribution: No existing model converts natural language → Revit-compatible specifications

Metrics to Track
Metric	Module	Target
BLEU Score	Text-to-Spec	>0.7
Layout IoU	Layout Generator	>0.8
Element Accuracy	BIM Generator	>85%
Generation Time	Full Pipeline	<30s
Immediate Next Steps
Week 1: Data Preparation
 Download ResBIM dataset (7GB)
 Process CubiCasa5k into training format
 Generate 500+ text-spec pairs
Week 2: NLP Training
 Train Text-to-Spec model
 Evaluate and iterate
 Create inference API
Week 3: Revit Plugin Foundation
 Set up Revit plugin project (C#)
 Create basic UI
 Implement wall generation
Week 4: Integration
 Connect AI backend to Revit plugin
 End-to-end testing
 Demo preparation
Quick Answers to Your Questions
1. Do you need IfcOpenShell?
No. For Revit development, use the Revit API directly. IfcOpenShell is for IFC files (open format). You can export to IFC from Revit if needed.

2. How many AI modules need training?
3 modules:

Text-to-Spec - NLP (T5 fine-tuning)
Layout Generator - ML (HouseDiffusion or CNN)
BIM Mapper - Hybrid (rules + ML optimization)
3. Why fine-tune instead of using pre-trained models?
Architectural domain vocabulary
Structured JSON output requirement
Higher accuracy on specific task
Unique FYP contribution
4. CubiCasa5k or RPLAN?
CubiCasa5k is sufficient - you have it downloaded with 5000 samples. RPLAN adds diversity but isn't critical.

5. Is HouseExpo needed?
No. HouseExpo is for indoor robot navigation, not floor plan generation. Skip it.