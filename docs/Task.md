FYP Iteration 2: Text-to-BIM System
Phase 1: Data Pipeline ✅
 Download CubiCasa5k dataset
 Download FloorPlanCAD dataset
 Download 3D-FRONT dataset (for additional training)
 Generate text-spec pairs (599 total)
 Process CubiCasa5k (499 layouts extracted)
Phase 2: NLP Core Training ✅
 Text-to-Spec Model Training
 Create T5 training script
 Fix training dependencies
 Run training (5 epochs, 599 samples)
 Model saved to models/nlp_t5/final_model
Create inference pipeline
 Inference script for T5 model
 API endpoint (Flask/FastAPI)
Phase 3: BlenderBIM Integration (MVP)
BIM Generation Engine
 Install IfcOpenShell/BlenderBIM
 Create IFC generation script
 Room layout from JSON spec
 Wall generation
 Window/door placement
 End-to-end pipeline test
 Text → JSON spec → IFC file
 Validate IFC in BlenderBIM
Phase 4: Revit Plugin (Next Iteration)
 Set up Revit 2026 plugin project (C#)
 Port BIM logic to Revit API
 Create UI (text input)
 Demo and documentation