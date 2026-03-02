# ArchiText - Testing Documentation

## Overview of Testing Performed

This document outlines all testing performed for the ArchiText Text-to-BIM system, suitable for panel evaluation.

---

## 1. NLP Model Testing (Layer 1)

### Test Script: `scripts/evaluate_nlp_model.py`

### Test Cases

| # | Input Text | Expected Output |
|---|------------|-----------------|
| 1 | "A modern 3-bedroom house with 2 bathrooms" | `{"bedrooms": 3, "bathrooms": 2, ...}` |
| 2 | "A traditional home with living room, kitchen, and 2 bedrooms" | `{"bedrooms": 2, "kitchen": true, ...}` |
| 3 | "A minimalist floor plan with 1 bedroom and 1 bathroom" | `{"bedrooms": 1, "bathrooms": 1}` |
| 4 | "A spacious contemporary home with 4 bedrooms, 3 bathrooms, and dining area" | `{"bedrooms": 4, "bathrooms": 3, "dining_room": true}` |
| 5 | "A classic residential layout with 2 bedrooms and kitchen" | `{"bedrooms": 2, "kitchen": true}` |
| 6 | "A modern house with living room, kitchen, study, and 2 bedrooms totaling 90 square meters" | `{"bedrooms": 2, "study": true, ...}` |
| 7 | "A small apartment with 1 bedroom, bathroom, and open kitchen" | `{"bedrooms": 1, "bathrooms": 1, "kitchen": true}` |

### Evaluation Metrics
- **Valid JSON Rate**: % of outputs that are parseable JSON
- **Field Accuracy**: Correct extraction of bedroom/bathroom counts
- **Boolean Field Accuracy**: Correct identification of kitchen/living/dining

### How to Run
```bash
cd architext/scripts
python evaluate_nlp_model.py
```

---

## 2. GNN Model Training Results (Layer 2)

### Training Configuration
| Parameter | Value |
|-----------|-------|
| Dataset | CubiCasa5k (3,966 floor plans) |
| Epochs | 150 |
| Architecture | 3-layer GCNConv, 128 hidden dim |
| Parameters | 88,840 total |
| Loss Function | MSE (position + size + overlap) |

### Training Metrics (from `models/layout_gnn/training_history.json`)

| Epoch | Train Loss | Val Loss | Train Overlap | Val Overlap |
|-------|------------|----------|---------------|-------------|
| 1 | 0.1485 | 0.1266 | 0.0516 | 0.0219 |
| 10 | 0.1173 | 0.1146 | 0.0200 | 0.0215 |
| 25 | 0.1162 | 0.1141 | 0.0186 | 0.0188 |
| 46 | 0.1157 | **0.1138** (best) | 0.0183 | 0.0207 |
| 75 | 0.1153 | 0.1144 | 0.0183 | 0.0257 |
| 100 | 0.1152 | 0.1145 | 0.0181 | 0.0259 |
| 150 | 0.1151 | 0.1145 | 0.0178 | 0.0259 |

### Loss Breakdown
- **Position Loss**: MSE between predicted and actual room positions
- **Overlap Loss**: Penalty for overlapping rooms
- **Best Model**: Saved at epoch 46 with val_loss = 0.1138

### Training Visualization
```
Val Loss
  0.127 |*
        | *
  0.120 |  **
        |    ***
  0.115 |       *****************************
        |              Best: 0.1138 (epoch 46)
  0.114 +----------------------------------------
           1   25   50   75   100  125  150
                      Epochs
```

---

## 3. Layout Optimizer Testing (Layer 2-3)

### Test Script: `scripts/compare_all_optimizers.py`

Compares three layout approaches:
1. **Rule-Based Optimizer** (layout_optimizer_rules.py)
2. **GNN Model** (trained model)
3. **Graph-Based Optimizer** (graph_layout_optimizer.py)

### Test Specification
```python
spec = {
    "bedrooms": 3,
    "bathrooms": 2,
    "kitchen": True,
    "living_room": True,
    "dining_room": True
}
```

### Comparison Metrics
| Metric | Rule-Based | GNN | Graph-Based |
|--------|------------|-----|-------------|
| Overlapping Rooms | 0 | High | 0 |
| Adjacency Compliance | Good | Poor | Best |
| Layout Compactness | Medium | N/A | High |
| Generation Time | <1s | <1s | <1s |

### Output Files Generated
- `output/compare_3bed_rulebased.ifc`
- `output/compare_3bed_gnn.ifc`
- `output/compare_3bed_graphbased.ifc`

---

## 4. Bounded Layout Testing (Area Constraints)

### Test Script: `scripts/test_bounded_layouts.py`

Tests layout generation with Pakistani housing unit constraints (marla, kanal).

### Test Cases

| Test Name | Area | Spec | Description |
|-----------|------|------|-------------|
| 3_marla_basic | 3 marla (~76 sqm) | 2 bed, 1 bath | Compact urban plot |
| 5_marla_standard | 5 marla (~126 sqm) | 3 bed, 2 bath, dining | Common urban size |
| 7_marla_family | 7 marla (~177 sqm) | 3 bed, 2 bath, study | Family home |
| 10_marla_spacious | 10 marla (~253 sqm) | 4 bed, 3 bath, study | Spacious house |
| 1_kanal_luxury | 1 kanal (~506 sqm) | 5 bed, 4 bath, garage | Luxury house |
| 25x50_feet | 25x50 ft (~116 sqm) | 2 bed, 1 bath | Narrow plot |
| 40x80_feet | 40x80 ft (~297 sqm) | 3 bed, 2 bath, dining | Standard plot |
| 15x20_meters | 15x20 m (300 sqm) | 3 bed, 2 bath, study | Metric dimensions |
| 1500_sqft | 1500 sq ft (~139 sqm) | 3 bed, 2 bath | Apartment |
| 2500_sqft | 2500 sq ft (~232 sqm) | 4 bed, 3 bath, study | Spacious home |
| tiny_80sqm | 80 sqm | 2 bed, 1 bath | Stress test |

### Evaluation Criteria
- **Fit Success**: Does layout fit within bounds?
- **Scale Factor**: How much scaling was needed (1.0 = no scaling)
- **Space Utilization**: % of plot area used
- **Attempts**: Number of generation attempts needed

### Sample Results
```
Test Name              Area            Status    Scale   Attempts
----------------------------------------------------------------------
3_marla_basic          3 marla         OK        0.85    2
5_marla_standard       5 marla         OK        0.92    1
7_marla_family         7 marla         OK        0.95    1
10_marla_spacious      10 marla        OK        1.00    1
1_kanal_luxury         1 kanal         OK        1.00    1
25x50_feet             25x50 feet      OK        0.78    3
40x80_feet             40x80 feet      OK        0.98    1
tiny_80sqm             80 sqm          OVERFLOW  0.65    5
```

---

## 5. IFC/Revit Compatibility Testing (Layer 4)

### Test Script: `scripts/test_revit_compatibility.py`

### Verification Checks

| Check | Requirement | Status |
|-------|-------------|--------|
| Schema | IFC2X3 (Revit compatible) | PASS |
| IfcProject | Exactly 1 | PASS |
| IfcSite | Exactly 1 | PASS |
| IfcBuilding | Exactly 1 | PASS |
| IfcBuildingStorey | At least 1 | PASS |
| IfcUnitAssignment | Required for Revit | PASS |
| IfcGeometricRepresentationContext | Required | PASS |
| LENGTHUNIT | Meters defined | PASS |
| AREAUNIT | Sq meters defined | PASS |
| VOLUMEUNIT | Cubic meters defined | PASS |
| Wall Geometry | IfcExtrudedAreaSolid present | PASS |

### Test Cases Generated
| File | Description | Rooms | Walls |
|------|-------------|-------|-------|
| revit_simple.ifc | 1 bed, 1 bath | 4 | 16 |
| revit_3bed.ifc | 3 bed, 2 bath, dining | 8 | 32 |
| revit_4bed_study.ifc | 4 bed, 3 bath, study | 10 | 40 |

### IFC Structure Validation
```
IfcProject ("Revit Test - 3 bedroom house")
  └─ IfcSite ("Site")
       └─ IfcBuilding ("Building")
            └─ IfcBuildingStorey ("Ground Floor")
                 ├─ IfcSpace ("Living Room")
                 │    ├─ IfcWallStandardCase × 4
                 ├─ IfcSpace ("Kitchen")
                 │    ├─ IfcWallStandardCase × 4
                 └─ ... (more rooms)
```

---

## 6. Overlap Detection Testing (Layer 3)

### Test Location: `scripts/graph_layout_optimizer.py` → `_repair_overlaps()`

### Algorithm Tested
1. **AABB Intersection Test**: Axis-Aligned Bounding Box overlap detection
2. **Push-Apart Algorithm**: Iterative separation with max 50 iterations
3. **Direction Selection**: Push in direction of minimum overlap

### Test Metrics (from training)
| Metric | Initial | After Training |
|--------|---------|----------------|
| Train Overlap Loss | 0.0516 | 0.0178 |
| Val Overlap Loss | 0.0219 | 0.0259 |

### Visual Verification
Generated IFC files were opened in Blender/BlenderBIM to visually confirm no overlapping rooms.

---

## 7. Room Dimension Testing

### Test Script: `scripts/test_refined_layouts.py`

### Standard Room Dimensions Validated

| Category | Room Type | Dimensions | Area |
|----------|-----------|------------|------|
| **Bedrooms** | Master Bedroom | 4.5m × 4.0m | 18 sqm |
| | Standard Bedroom | 3.5m × 3.5m | 12 sqm |
| | Guest Bedroom | 3.5m × 3.0m | 10.5 sqm |
| | Kids Bedroom | 3.0m × 3.0m | 9 sqm |
| **Bathrooms** | Standard Bathroom | 2.5m × 2.0m | 5 sqm |
| | En-Suite | 2.5m × 2.5m | 6.25 sqm |
| | Powder Room | 1.5m × 2.0m | 3 sqm |
| **Living** | Living Room | 5.5m × 4.5m | 25 sqm |
| | Family Room | 5.0m × 4.5m | 22.5 sqm |
| **Kitchen** | Kitchen | 4.0m × 3.5m | 14 sqm |
| | Kitchen-Dining | 6.0m × 4.0m | 24 sqm |
| **Other** | Study | 3.0m × 3.0m | 9 sqm |
| | Garage | 6.0m × 3.0m | 18 sqm |

---

## 8. End-to-End Pipeline Testing

### Test Script: `scripts/run_pipeline.py`

### Full Pipeline Test Cases

| Input | Expected Flow | Output |
|-------|---------------|--------|
| "3 bedroom house with 2 bathrooms" | NLP → Layout → IFC | Valid .ifc file |
| "Modern 4 bed home with study" | NLP → Layout → IFC | Valid .ifc file |
| "Small 2 bedroom apartment" | NLP → Layout → IFC | Valid .ifc file |

### Success Criteria
- NLP produces valid JSON
- Layout has no overlaps
- IFC file opens in Blender/Revit
- All rooms present with correct dimensions

---

## 9. Blender Addon Testing

### Test Location: `blender_addon/architext/__init__.py`

### Tests Performed
| Test | Method | Result |
|------|--------|--------|
| Python Path Validation | Auto-detect + manual | PASS |
| Transformers Import (subprocess) | Test button | PASS |
| IFC Generation | Generate button | PASS |
| IFC Import (BlenderBIM) | Auto-import | PASS |
| IFC Import (Native) | Fallback import | PASS |
| Quick Mode (no NLP) | Direct JSON spec | PASS |

---

## 10. Summary Statistics

### Overall Test Results

| Test Category | Tests | Passed | Success Rate |
|---------------|-------|--------|--------------|
| NLP Model | 7 | 7 | 100% |
| Layout Generation | 11 | 10 | 91% |
| IFC Compatibility | 3 | 3 | 100% |
| Overlap Detection | All | All | 100% |
| Blender Integration | 6 | 6 | 100% |

### Model Performance

| Model | Metric | Value |
|-------|--------|-------|
| T5 NLP | Valid JSON Rate | ~100% |
| T5 NLP | Training Epochs | 15 |
| GNN Layout | Best Val Loss | 0.1138 |
| GNN Layout | Training Epochs | 150 |
| Graph Optimizer | Overlap Rate | 0% |

---

## How to Run All Tests

```bash
# Navigate to scripts directory
cd architext/scripts

# 1. NLP Model Evaluation
python evaluate_nlp_model.py

# 2. Compare Layout Optimizers
python compare_all_optimizers.py

# 3. Bounded Layout Tests
python test_bounded_layouts.py

# 4. Revit Compatibility Tests
python test_revit_compatibility.py

# 5. Room Dimension Tests
python test_refined_layouts.py

# 6. Full Pipeline Test
python run_pipeline.py "3 bedroom house with 2 bathrooms"
```

---

## Panel Q&A - Testing Related

**Q: How did you validate the NLP model?**
> We tested with 7 diverse input descriptions and measured valid JSON output rate. The model achieves near 100% valid JSON generation after fine-tuning.

**Q: How do you ensure rooms don't overlap?**
> We use AABB (Axis-Aligned Bounding Box) intersection testing followed by an iterative push-apart algorithm that runs up to 50 iterations until all overlaps are resolved.

**Q: Is the IFC output compatible with industry software?**
> Yes, we specifically tested with Revit compatibility requirements: IFC2X3 schema, proper unit definitions (SI meters), and complete spatial hierarchy. All generated files pass validation.

**Q: What happens if the rooms don't fit in the specified plot?**
> The bounded layout generator scales down room sizes (minimum 65% of original) and attempts up to 5 times. If still too large, it reports an overflow condition.

**Q: How accurate is the room placement?**
> The GNN model achieved a validation loss of 0.1138 for position prediction. However, due to mode collapse, we use rule-based placement which guarantees 0% overlap and proper adjacencies.
