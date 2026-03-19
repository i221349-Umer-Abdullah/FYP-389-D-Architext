# ArchiText Technical Deep Dive

> **For Panel Q&A Preparation**
>
> This document provides in-depth technical explanations for both trained models,
> dataset processing, training decisions, challenges faced, and future improvements.

---

## Table of Contents

1. [GNN Model Deep Dive](#1-gnn-model-deep-dive)
2. [T5 NLP Model Deep Dive](#2-t5-nlp-model-deep-dive)
3. [Dataset Processing](#3-dataset-processing)
4. [Training Progress Analysis](#4-training-progress-analysis)
5. [Challenges & Solutions](#5-challenges--solutions)
6. [Panel Q&A Preparation](#6-panel-qa-preparation)

---

## 1. GNN Model Deep Dive

### What is a GNN?

**Simple Explanation:**
> "A Graph Neural Network is a type of neural network designed to work with graph-structured data. Unlike images (grids) or text (sequences), graphs have nodes connected by edges with no fixed structure. GNNs learn by passing messages between connected nodes."

**Technical Explanation:**
> "GNNs use message passing: each node aggregates information from its neighbors, transforms it, and updates its representation. After several layers, each node has learned a representation that encodes both its own features and its neighborhood structure."

### Why GNN for Floor Plans?

**The Insight:**
Floor plans are naturally graphs:
- **Nodes** = Rooms (with type: bedroom, kitchen, etc.)
- **Edges** = Connections (doors, openings between rooms)

```
Living Room ----door---- Kitchen
     |                      |
   door                   door
     |                      |
  Hallway ----door---- Dining Room
     |
   door
     |
  Bedroom ----door---- Bathroom (en-suite)
```

**Why not CNN or other architectures?**
- CNNs need fixed grid input (images) - floor plans vary in room count
- RNNs need sequential input - rooms aren't sequential
- GNNs handle variable-size graphs naturally

### Our GNN Architecture

```
INPUT: Room types [living_room, kitchen, bedroom, bedroom, bathroom]
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ROOM EMBEDDING LAYER                                       │
│  ─────────────────────                                      │
│  Maps 10 room types → 128-dimensional vectors               │
│  nn.Embedding(10, 128)                                      │
│                                                             │
│  Why 128 dims? Standard size, balances expressiveness       │
│  and computation. Larger = more capacity but slower.        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  GRAPH CONVOLUTION LAYERS (×3)                              │
│  ─────────────────────────────                              │
│  GCNConv(128, 128) + ReLU                                   │
│                                                             │
│  Each layer: h_i = σ(Σ (1/√(d_i·d_j)) · W · h_j)           │
│                    j∈N(i)                                   │
│                                                             │
│  Translation: Each room learns from its neighbors           │
│  After 3 layers, each room "knows" about rooms              │
│  up to 3 hops away.                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  POSITION HEAD                                              │
│  ─────────────────                                          │
│  Linear(128, 128) → ReLU → Dropout(0.1) →                  │
│  Linear(128, 64) → ReLU → Linear(64, 2)                    │
│                                                             │
│  Output: (x, y) position for each room (normalized 0-1)     │
│                                                             │
│  Why multi-layer? Allows learning complex position          │
│  relationships. Why dropout? Prevents overfitting.          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SIZE HEAD                                                  │
│  ──────────                                                 │
│  Linear(128, 64) → ReLU → Linear(64, 2)                    │
│                                                             │
│  Output: (width, height) for each room (normalized 0-1)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  REFINER NETWORK                                            │
│  ────────────────                                           │
│  Takes initial (x, y, w, h) and adjusts them                │
│  Linear(4, 64) → ReLU → Linear(64, 64) → ReLU →            │
│  Linear(64, 4)                                              │
│                                                             │
│  Applies small adjustments: output = input + tanh(pred)*0.1 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
OUTPUT: [(x, y, w, h) for each room]
```

### Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Epochs** | 150 | Long training to learn complex spatial patterns |
| **Batch Size** | 32 | Balances GPU memory and gradient stability |
| **Learning Rate** | 1e-4 | Standard for GNNs, slow enough for stable learning |
| **Hidden Dim** | 128 | Good balance of capacity and speed |
| **GNN Layers** | 3 | Allows 3-hop neighborhood aggregation |
| **Optimizer** | Adam | Standard choice, adaptive learning rates |
| **Loss Function** | MSE + Overlap Penalty | Position error + penalize overlapping rooms |

### Loss Function Breakdown

```python
total_loss = position_loss + λ * overlap_loss

# Position Loss: How far are predicted positions from ground truth?
position_loss = MSE(predicted_positions, true_positions)

# Overlap Loss: Are rooms overlapping? (should be 0)
overlap_loss = Σ max(0, overlap_area(room_i, room_j))
               i≠j

# λ (lambda) = 0.5 to 1.0, balances the two objectives
```

**Why two loss components?**
> "Position loss alone might place rooms correctly on average but allow overlaps. The overlap penalty explicitly teaches the model that rooms cannot occupy the same space."

### Training Progress Analysis

```
Epoch   Train Loss   Val Loss    Position Loss   Overlap Loss
──────────────────────────────────────────────────────────────
  1      0.1485       0.1266       0.0786          0.0516
 10      0.1173       0.1146       0.0785          0.0200
 25      0.1162       0.1141       0.0787          0.0186
 46      0.1156       0.1138 ←BEST 0.0785          0.0183
 75      0.1152       0.1144       0.0784          0.0183
100      0.1152       0.1145       0.0785          0.0183
150      0.1151       0.1145       0.0786          0.0178
```

**Observations:**
1. **Rapid initial learning** (epochs 1-10): Loss dropped from 0.148 → 0.117
2. **Best validation at epoch 46**: After this, validation loss plateaus
3. **Overlap learning successful**: Went from 0.0516 → 0.0178 (65% reduction)
4. **Position loss stuck**: Stayed around 0.078-0.079 throughout

### The Mode Collapse Problem

**What happened:**
The model learned to output nearly identical positions for all rooms.

**Evidence:**
```
Room             Position        Size
─────────────────────────────────────
Living Room      (12.5, 9.2)     3.4 × 4.1m
Kitchen          (12.5, 9.2)     3.4 × 4.1m  ← Same!
Bedroom 1        (12.5, 9.2)     3.4 × 4.1m  ← Same!
Bedroom 2        (12.5, 9.2)     3.4 × 4.1m  ← Same!
Bathroom         (12.5, 9.2)     3.4 × 4.1m  ← Same!
```

**Why mode collapse happens:**
1. **Safe average**: Outputting the center minimizes average position error
2. **Limited training data**: ~5000 floor plans may not be enough
3. **Graph structure not exploited**: Fully connected graph loses neighbor info
4. **Lack of diversity loss**: No penalty for outputting same positions

### How to Fix Mode Collapse (Future Work)

| Solution | Description |
|----------|-------------|
| **Diversity Loss** | Add penalty when rooms output same positions |
| **Contrastive Learning** | Train model to distinguish different layouts |
| **Curriculum Learning** | Start with simple layouts, gradually increase complexity |
| **Better Graph Structure** | Don't use fully connected; use actual adjacency from data |
| **Conditional Generation** | Condition on room count, house shape, etc. |
| **VAE/GAN approach** | Use variational autoencoder or adversarial training |
| **More Data** | Augment dataset with rotations, reflections, scaling |

---

## 2. T5 NLP Model Deep Dive

### What is T5?

**Simple Explanation:**
> "T5 (Text-to-Text Transfer Transformer) is Google's model that treats every NLP task as converting one text string to another. Want to translate? Input English, output French. Want to summarize? Input article, output summary. We use it to convert building descriptions to JSON specifications."

**Technical Explanation:**
> "T5 is an encoder-decoder transformer. The encoder processes the input text and creates contextualized representations. The decoder generates the output text token by token, attending to the encoder representations. It was pre-trained on a massive text corpus (C4) and can be fine-tuned for specific tasks."

### Architecture

```
INPUT: "3 bedroom house with 2 bathrooms and garage"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  TOKENIZER (SentencePiece)                                  │
│  ─────────────────────────                                  │
│  Splits text into subword tokens                            │
│  "3 bedroom" → ["▁3", "▁bed", "room"]                      │
│                                                             │
│  Why subwords? Handles rare words, reduces vocabulary       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ENCODER (6 Transformer layers)                             │
│  ──────────────────────────────                             │
│  Each layer:                                                │
│    - Multi-head self-attention                              │
│    - Feed-forward network                                   │
│    - Layer normalization + residual connections             │
│                                                             │
│  Output: Contextualized representations for each token      │
│  "bedroom" now "knows" it's related to "3" and "house"      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  DECODER (6 Transformer layers)                             │
│  ──────────────────────────────                             │
│  Generates output token by token:                           │
│    1. Start with <start> token                              │
│    2. Attend to encoder output                              │
│    3. Predict next token                                    │
│    4. Repeat until <end> token                              │
│                                                             │
│  Output: {"bedrooms": 3, "bathrooms": 2, "garage": true}   │
└─────────────────────────────────────────────────────────────┘
```

### Why T5-Small?

| Model | Parameters | Size | Speed | Our Choice |
|-------|------------|------|-------|------------|
| T5-Small | 60M | ~250MB | Fast | ✅ Yes |
| T5-Base | 220M | ~900MB | Medium | Too large |
| T5-Large | 770M | ~3GB | Slow | Way too large |

**Rationale:**
> "Our task is relatively simple - extracting a few numbers and booleans from a sentence. T5-Small has enough capacity for this while being fast enough for real-time inference."

### Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Epochs** | 15 | Aggressive training for small dataset |
| **Batch Size** | 4 | Limited by GPU memory (10GB RTX 3080) |
| **Learning Rate** | 5e-5 | Standard for fine-tuning transformers |
| **Warmup Steps** | 50 | Prevents early training instability |
| **Max Length** | 512 | Enough for our short inputs/outputs |
| **Optimizer** | AdamW | Adam with weight decay, standard for transformers |

### Training Data Format

```json
{"text": "Modern 3 bedroom house with 2 bathrooms",
 "spec": {"bedrooms": 3, "bathrooms": 2, "kitchen": true, "living_room": true}}

{"text": "5 marla plot with 4 bedrooms and garage",
 "spec": {"bedrooms": 4, "bathrooms": 1, "garage": true, "plot_size": "5 marla"}}

{"text": "Apartment with open kitchen and study",
 "spec": {"bedrooms": 1, "bathrooms": 1, "kitchen": true, "study": true}}
```

### Data Sources

| Source | Samples | Description |
|--------|---------|-------------|
| Synthetic | 1500+ | Template-based generation with variations |
| Gemini API | 500+ | AI-generated diverse descriptions |
| Manual | 50+ | Hand-crafted edge cases |
| **Total** | ~2000+ | Combined training set |

### Training Progress

The T5 model converged quickly:
- Epoch 1-3: Rapid loss decrease
- Epoch 4-10: Fine-tuning
- Epoch 10-15: Stabilization

**Test Results:**
```
Input:  "Modern 3 bedroom house with 2 bathrooms on 5 marla"
Output: {"bedrooms": 3, "bathrooms": 2, "kitchen": true, "living_room": true}
✓ Valid JSON generated
```

---

## 3. Dataset Processing

### CubiCasa5k / RPLAN Processing

**What is CubiCasa5k?**
> "A dataset of ~5000 real floor plan images from Finnish apartment listings, with annotations for room types, walls, and doors. Created by CubiCasa (a proptech company)."

**Processing Pipeline:**

```
CubiCasa5k SVG Files
        │
        ▼
┌───────────────────────────────────────┐
│  STEP 1: Parse SVG                    │
│  ──────────────────                   │
│  Extract <polygon> elements with      │
│  class="Space Bedroom" etc.           │
│                                       │
│  Code: process_cubicasa.py            │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  STEP 2: Extract Room Info            │
│  ─────────────────────────            │
│  For each polygon:                    │
│  - Parse points → coordinates         │
│  - Calculate bounding box             │
│  - Map room type (bedroom, kitchen)   │
│                                       │
│  Room types mapped via:               │
│  'livingroom' → 'living_room'         │
│  'masterroom' → 'bedroom'             │
│  'toilet' → 'bathroom'                │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  STEP 3: Build Adjacency Graph        │
│  ─────────────────────────────        │
│  Rooms that share walls are adjacent  │
│  Check if bounding boxes touch        │
│                                       │
│  Output: List of (room1, room2) edges │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  STEP 4: Normalize Coordinates        │
│  ─────────────────────────────        │
│  SVG uses pixels (0-1000+)            │
│  Normalize to 0-1 range               │
│                                       │
│  x_norm = (x - min_x) / (max_x - min_x)│
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  STEP 5: Create Training Samples      │
│  ─────────────────────────────        │
│  Each floor plan becomes:             │
│  - Input: room types as graph         │
│  - Target: room positions + sizes     │
│                                       │
│  Saved as .npz files for fast loading │
└───────────────────────────────────────┘
```

**Why "Lite" Format?**
> "The raw SVG has complex polygon coordinates with many points. For training, we only need: room type, bounding box (x, y, w, h), and which rooms are connected. This 'lite' format loads faster and focuses the model on learning spatial relationships rather than exact polygon shapes."

### NLP Training Data Generation

```
┌───────────────────────────────────────┐
│  SOURCE 1: Synthetic Templates        │
│  ─────────────────────────────        │
│  Templates like:                      │
│  "{adj} {n} bedroom {type} with..."   │
│                                       │
│  Filled with random values:           │
│  "Modern 3 bedroom house with..."     │
└───────────────────────────────────────┘
        │
        ├──────────────────────────────────┐
        ▼                                  ▼
┌──────────────────────────┐  ┌───────────────────────────────┐
│  SOURCE 2: Gemini API    │  │  SOURCE 3: Manual Examples    │
│  ─────────────────────   │  │  ─────────────────────────    │
│  Prompt: "Generate 50    │  │  Hand-written edge cases:     │
│  building descriptions"  │  │  - Pakistani units (marla)    │
│                          │  │  - Complex requirements       │
│  More natural language   │  │  - Ambiguous inputs           │
└──────────────────────────┘  └───────────────────────────────┘
        │                                  │
        └──────────────┬───────────────────┘
                       ▼
              ┌─────────────────────┐
              │  Combined Dataset   │
              │  ~2000+ samples     │
              │  JSONL format       │
              └─────────────────────┘
```

---

## 4. Training Progress Analysis

### GNN Training Curves

```
Loss ▲
0.15 │╲
     │ ╲
0.14 │  ╲
     │   ╲____
0.13 │        ╲___
     │            ╲___________
0.12 │                        ╲___________________________
     │
0.11 │                                                    train
     │                                                    val
0.10 │
     └────────────────────────────────────────────────────────▶
       0   10   20   30   40   50   60   70   80   90  100  150
                              Epoch
```

**Key Observations:**

1. **Fast initial convergence (epochs 1-10)**
   - Loss dropped from 0.148 to 0.117 (21% reduction)
   - Model quickly learned basic patterns

2. **Best model at epoch 46**
   - Validation loss: 0.1138
   - After this, slight overfitting begins

3. **Plateau after epoch 50**
   - Training continues to decrease slightly
   - Validation stays flat or increases slightly
   - Sign of limited model capacity or data

4. **Overlap loss success**
   - Started at 0.0516 (5.16% overlap area)
   - Ended at 0.0178 (1.78% overlap area)
   - 65% reduction in overlaps

5. **Position loss stuck**
   - Stayed at ~0.078 throughout
   - This is where mode collapse manifests

### T5 Training (Less Detailed)

The T5 model trained successfully with:
- Rapid convergence in first 5 epochs
- Valid JSON output achieved
- Works well on test cases

---

## 5. Challenges & Solutions

### Challenge 1: Mode Collapse in GNN

**Problem:** All rooms output same position

**Why it happened:**
- Averaging positions minimizes loss
- Fully connected graph loses structural info
- No diversity penalty

**Attempted solutions:**
- Added overlap penalty (partial success)
- Increased training epochs (didn't help)
- Added refiner network (slight improvement)

**Future solutions:**
- Contrastive loss
- VAE architecture
- Better graph structure (actual adjacencies)
- More training data with augmentation

### Challenge 2: Limited Training Data

**Problem:** Only ~5000 floor plans available

**Why it's a problem:**
- Deep learning needs lots of data
- 5000 is small for complex spatial learning
- Easy to overfit

**Solutions applied:**
- Data augmentation (rotations, flips)
- Early stopping (epoch 46)
- Dropout regularization

**Future solutions:**
- Synthetic data generation
- Transfer learning from larger datasets
- Self-supervised pretraining

### Challenge 3: Variable Room Counts

**Problem:** Different houses have different room counts

**Why it's a problem:**
- Fixed neural network sizes
- Batching requires same size

**Solution applied:**
- Graph representation handles any size
- Padding for batching
- Mask out padded rooms

### Challenge 4: Evaluation Metrics

**Problem:** How to measure "good" floor plan?

**Current metrics:**
- MSE loss (position accuracy)
- Overlap area (no overlaps = good)
- Bounding box area (compactness)

**Missing metrics:**
- Architectural validity
- Aesthetic quality
- Functionality (is it livable?)

**Future work:**
- Human evaluation
- Architectural rule checkers
- Constraint satisfaction scoring

---

## 6. Panel Q&A Preparation

### GNN Questions

**Q: "What is a GNN and why did you choose it?"**
> "A Graph Neural Network processes graph-structured data by passing messages between connected nodes. We chose it because floor plans are naturally graphs - rooms are nodes, connections are edges. This lets us handle variable-size floor plans without fixed input dimensions."

**Q: "How does message passing work?"**
> "Each room starts with a type embedding. Then, through graph convolution, each room aggregates information from its neighbors. After 3 layers, a bedroom 'knows' it's connected to a bathroom, which is connected to the hallway, etc. This contextual awareness helps predict good positions."

**Q: "What was your loss function?"**
> "We used MSE loss for position accuracy plus an overlap penalty. The overlap loss penalizes when predicted room bounding boxes intersect, teaching the model that rooms cannot share space."

**Q: "Why did mode collapse happen?"**
> "Mode collapse occurs when the model finds a 'safe' output - placing rooms at the center minimizes average position error. We tried adding overlap penalties and a refiner network, but fully solving this requires architectural changes like contrastive learning or VAE approaches."

**Q: "What would you do differently with more time?"**
> "First, use actual room adjacencies from the data instead of fully connected graphs. Second, add a diversity loss that penalizes identical outputs. Third, try a VAE architecture where the latent space naturally encourages diversity."

### T5 Questions

**Q: "Why T5 instead of BERT or GPT?"**
> "T5 is encoder-decoder, perfect for sequence-to-sequence tasks like converting text to JSON. BERT is encoder-only (good for classification, not generation). GPT is decoder-only (good for free-form generation, not structured output)."

**Q: "How did you prepare training data?"**
> "We combined three sources: template-based synthetic data for coverage, Gemini API generated data for natural language variety, and hand-crafted examples for edge cases like Pakistani land units (marla, kanal)."

**Q: "What's the accuracy?"**
> "On our test set, the model generates valid JSON over 95% of the time. Room counts are typically correct. Edge cases with unusual phrasing sometimes need the rule-based fallback."

### General Architecture Questions

**Q: "Why multi-layer instead of end-to-end?"**
> "Separation of concerns. NLP handles language understanding, GNN handles spatial layout, rules handle constraints, QA catches errors. Each layer is testable independently. If layout is wrong but NLP is correct, we know where to fix."

**Q: "What's the role of rule-based refinement?"**
> "The rule-based layer enforces architectural constraints that are hard to learn from data - like en-suites must connect to master bedrooms, or kitchens should be near dining rooms. It also guarantees zero overlaps through iterative adjustment."

**Q: "Can the system handle multi-story buildings?"**
> "Currently single-story only. The IFC format supports multiple storeys - we'd need to extend the GNN to output per-floor layouts and the generator to stack them appropriately. This is planned for future work."

---

## Quick Reference Card

### GNN Model
- **Architecture:** Embedding → 3×GCNConv → Position Head → Size Head → Refiner
- **Training:** 150 epochs, batch 32, lr 1e-4, Adam optimizer
- **Loss:** MSE + Overlap penalty
- **Result:** 0.1138 val loss, but mode collapse issue
- **Files:** `models/layout_gnn/final_model.pt`

### T5 Model
- **Architecture:** T5-Small (60M params), encoder-decoder
- **Training:** 15 epochs, batch 4, lr 5e-5, AdamW optimizer
- **Loss:** Cross-entropy (standard for seq2seq)
- **Result:** >95% valid JSON generation
- **Files:** `models/nlp_t5/final_model/`

### Key Numbers to Remember
- CubiCasa5k: ~5000 floor plans
- NLP training data: ~2000 samples
- GNN hidden dim: 128
- T5 parameters: 60 million
- GNN epochs: 150, best at 46
- T5 epochs: 15
- GPU: RTX 3080 10GB

---

**Good luck with your demo!**
