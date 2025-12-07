Dataset Acquisition Guide for Architext
Complete Data Pipeline Setup
📊 Required Datasets Overview
We need 3 types of data for the 3 AI modules:

Dataset	Purpose	Size	Module	Priority
RPLAN	Floor plans (2D layouts)	80K plans	Layout AI	HIGH
CubiCasa5k	Floor plans + annotations	5K plans	Layout AI	MEDIUM
HouseExpo	Indoor layouts (JSON)	35K layouts	Layout AI	MEDIUM
IFC Models	BIM examples	50-100 models	BIM Engine	HIGH
Synthetic Text	Text descriptions	1K+ pairs	NLP Core	HIGH
Total Download: ~2-5 GB
Processing Time: 4-6 hours
Storage Needed: 10-15 GB after processing

🎯 Dataset 1: RPLAN (Primary for Layout AI)
What It Contains:
80,030 residential floor plans
Room types, bounding boxes, door/window positions
Originally from real estate listings in China
JSON format with room connectivity
Download Options:
Option A: Official (Requires Form)
Status: Request access required
URL: https://docs.google.com/forms/d/e/1FAIpQLSfwteilXzURRKDI5QjOYWJh7xNAlN8nJOJvJh2gLb_t0Og1mA/viewform

Steps:

Fill out the Google Form
Wait 1-7 days for approval email
Download from provided Google Drive link (~600 MB)
Files You'll Get:

rplan/
├── train/
│   ├── 0.json
│   ├── 1.json
│   └── ... (60,000+ files)
├── test/
│   └── ... (20,000+ files)
└── README.txt
Option B: Alternative Mirror (Faster)
GitHub: https://github.com/zzilch/RPLAN-Toolbox

# Clone the toolbox
git clone https://github.com/zzilch/RPLAN-Toolbox.git
cd RPLAN-Toolbox
# Download sample dataset (smaller version for testing)
# Full dataset requires contacting authors
Option C: Use What We Already Have
You already have: 
…\architext\datasets\rplan\0.json
 (synthetic)

Quick Start: Create 100 synthetic variations for testing

cd d:\Work\Uni\FYP\architext
python -c "
import json
import random
# Generate 100 synthetic floor plans
for i in range(100):
    # Create variations of the synthetic plan
    # (We'll write this script next)
"
Processing RPLAN:
# scripts/process_rplan.py
import json
import os
from pathlib import Path
def process_rplan_json(json_path):
    """Convert RPLAN JSON to our standard format"""
    with open(json_path) as f:
        data = json.load(f)
    
    rooms = []
    for room in data.get('rooms', []):
        rooms.append({
            'type': room['type'],
            'bbox': room['bbox'],  # [x1, y1, x2, y2]
            'area': calculate_area(room['bbox'])
        })
    
    return {
        'id': Path(json_path).stem,
        'rooms': rooms,
        'doors': data.get('doors', []),
        'source': 'rplan'
    }
# Process all files
rplan_dir = 'datasets/rplan/train'
processed_dir = 'datasets/processed/layouts'
os.makedirs(processed_dir, exist_ok=True)
for json_file in Path(rplan_dir).glob('*.json'):
    processed = process_rplan_json(json_file)
    output_path = Path(processed_dir) / f"{json_file.stem}.json"
    with open(output_path, 'w') as f:
        json.dump(processed, f, indent=2)
🎯 Dataset 2: CubiCasa5k (High-Quality Annotations)
What It Contains:
5,000 floor plans from real apartments
SVG format with detailed annotations
Room types, walls, doors, windows
High quality, Western architecture style
Download:
Official GitHub Repository
URL: https://github.com/CubiCasa/CubiCasa5k

Download Command:

cd d:\Work\Uni\FYP\architext\datasets
git clone https://github.com/CubiCasa/CubiCasa5k.git
cd CubiCasa5k
# Download the actual dataset (requires Git LFS)
git lfs install
git lfs pull
Size: ~1.5 GB

Alternatively, Direct Download:

Go to: https://zenodo.org/record/2613548
Click "Download" (1.4 GB zip)
Extract to datasets/cubicasa5k/
File Structure:
cubicasa5k/
├── high_quality/
│   ├── 0/
│   │   ├── model.svg      # Floor plan
│   │   └── model.json     # Annotations
│   └── ...
└── colorful/              # Alternative rendering
Processing CubiCasa:
# scripts/process_cubicasa.py
import json
from pathlib import Path
from xml.etree import ElementTree as ET
def svg_to_rooms(svg_path):
    """Extract room polygons from SVG"""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    rooms = []
    for space in root.findall('.//{*}Space'):
        room_type = space.get('class', 'unknown')
        # Extract polygon points
        polygon = space.find('.//{*}polygon')
        if polygon:
            points = polygon.get('points', '')
            # Convert to our format
            rooms.append({
                'type': normalize_room_type(room_type),
                'polygon': parse_points(points)
            })
    
    return rooms
# Process all CubiCasa files
cubicasa_dir = Path('datasets/cubicasa5k/high_quality')
for model_dir in cubicasa_dir.glob('*/'):
    svg_file = model_dir / 'model.svg'
    if svg_file.exists():
        rooms = svg_to_rooms(svg_file)
        # Save processed data
🎯 Dataset 3: HouseExpo (Indoor Navigation)
What It Contains:
35,357 house layouts
JSON format (already compatible!)
Room connectivity, wall positions
Designed for robotics/navigation
Download:
GitHub: https://github.com/TeaganLi/HouseExpo

Download Commands:

cd d:\Work\Uni\FYP\architext\datasets
# Clone repository
git clone https://github.com/TeaganLi/HouseExpo.git
cd HouseExpo
# Download dataset files
# Option 1: Use their script
python download.py
# Option 2: Direct download from releases
# https://github.com/TeaganLi/HouseExpo/releases
Direct Link: https://github.com/TeaganLi/HouseExpo/releases/download/v1.0/house.tar.gz

Size: ~500 MB

File Structure:
HouseExpo/
├── json/
│   ├── train/
│   │   ├── 00001.json
│   │   └── ...
│   └── test/
│       └── ...
└── maps/              # 2D images
Processing HouseExpo:
# scripts/process_houseexpo.py
import json
from pathlib import Path
def process_houseexpo_json(json_path):
    """Convert HouseExpo format to our standard"""
    with open(json_path) as f:
        data = json.load(f)
    
    # HouseExpo uses vertex-based representation
    return {
        'id': Path(json_path).stem,
        'rooms': extract_rooms(data['vertices']),
        'walls': data.get('walls', []),
        'source': 'houseexpo'
    }
🎯 Dataset 4: IFC BIM Models (For Module 3)
What It Contains:
Real BIM models in IFC format
Residential, commercial buildings
Industry-standard examples
Download Sources:
Source A: IfcOpenShell Sample Models
URL: https://github.com/IfcOpenShell/IfcOpenShell/tree/v0.7.0/test/input

cd d:\Work\Uni\FYP\architext\datasets
mkdir ifc_models
cd ifc_models
# Download sample IFC files
curl -O https://raw.githubusercontent.com/IfcOpenShell/IfcOpenShell/v0.7.0/test/input/wall_with_opening.ifc
curl -O https://raw.githubusercontent.com/IfcOpenShell/IfcOpenShell/v0.7.0/test/input/IfcOpenHouse.ifc
# ... download more samples
Source B: BIMData Free Models
URL: https://bimdata.io/en/demo

Steps:

Visit https://bimdata.io/en/demo
Browse free models
Download IFC files (no account needed for demo)
Models Available:

Houses (5-10 models)
Apartments (3-5 models)
Small buildings (10+ models)
Source C: BuildingSMART Examples
URL: https://www.buildingsmart.org/sample-test-files/

# Download official test files
curl -O https://www.buildingsmart.org/.../AC20-FZK-Haus.ifc
curl -O https://www.buildingsmart.org/.../Duplex_A_20110505.ifc
Source D: OSArch.org Community Models
URL: https://wiki.osarch.org/index.php?title=AEC_Open_Source_Software_directory

Free IFC Models: ~50 residential/commercial buildings

Processing IFC Files:
# scripts/process_ifc.py
import ifcopenshell
from pathlib import Path
def extract_ifc_metadata(ifc_path):
    """Extract room info from IFC"""
    ifc_file = ifcopenshell.open(ifc_path)
    
    rooms = []
    spaces = ifc_file.by_type('IfcSpace')
    
    for space in spaces:
        rooms.append({
            'name': space.Name,
            'type': space.LongName or 'unknown',
            'area': get_area(space),
            'level': get_level(space)
        })
    
    return {
        'id': Path(ifc_path).stem,
        'rooms': rooms,
        'walls': count_by_type(ifc_file, 'IfcWall'),
        'doors': count_by_type(ifc_file, 'IfcDoor'),
        'source': 'ifc'
    }
# Process all IFC files
ifc_dir = Path('datasets/ifc_models')
for ifc_file in ifc_dir.glob('*.ifc'):
    metadata = extract_ifc_metadata(ifc_file)
    # Save to JSON
🎯 Dataset 5: Text Descriptions (For Module 1 NLP)
Option A: Manual Creation (50-100 samples)
Time: 2-4 hours
Quality: High accuracy

Template:

"A [size] [style] house with [X] bedrooms, [Y] bathrooms, 
[optional: garage, basement, features]"
Examples:
- "A small modern house with 2 bedrooms and 1 bathroom"
- "A large traditional house with 4 bedrooms, 3 bathrooms, and a 2-car garage"
Option B: GPT-4 Generation (1000+ samples)
Cost: ~$5-10 for 1000 descriptions
Time: 10 minutes

Script:

# scripts/generate_text_descriptions.py
import openai
import json
openai.api_key = 'your-api-key'
def generate_description(room_layout):
    """Generate text from floor plan JSON"""
    prompt = f"""
    Given this floor plan:
    Rooms: {room_layout['rooms']}
    
    Generate a natural language description a client would use:
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content
# Process all floor plans
for layout_file in Path('datasets/processed/layouts').glob('*.json'):
    with open(layout_file) as f:
        layout = json.load(f)
    
    description = generate_description(layout)
    
    # Save paired data
    paired_data = {
        'text': description,
        'layout': layout
    }
    # Save to training dataset
Option C: Use Architectural Description Templates
Dataset: Zillow, Realtor.com listings (web scraping)

Disclaimer: Respect robots.txt and terms of service

📦 Complete Setup Script
Here's the entire pipeline setup:

# Create directory structure
cd d:\Work\Uni\FYP\architext
mkdir -p datasets/{raw,processed,ifc_models}
mkdir -p datasets/processed/{layouts,text_pairs,ifc_metadata}
# Step 1: Download HouseExpo (fastest)
cd datasets/raw
git clone https://github.com/TeaganLi/HouseExpo.git
# Step 2: Download IFC samples
cd ../ifc_models
curl -O https://raw.githubusercontent.com/IfcOpenShell/IfcOpenShell/v0.7.0/test/input/IfcOpenHouse.ifc
# Download more from BIMData.io manually
# Step 3: Install processing dependencies
cd d:\Work\Uni\FYP\architext
pip install ifcopenshell lxml openai
# Step 4: Process datasets
python scripts/process_houseexpo.py
python scripts/process_ifc.py
python scripts/generate_text_descriptions.py
# Step 5: Create train/val/test splits
python scripts/create_splits.py
📊 Final Dataset Organization
datasets/
├── raw/
│   ├── rplan/              # 80K floor plans (if you get access)
│   ├── cubicasa5k/         # 5K floor plans
│   ├── HouseExpo/          # 35K layouts
│   └── ifc_models/         # 50-100 IFC files
│
├── processed/
│   ├── layouts/            # Standardized layout JSONs
│   │   ├── train.jsonl     # 70% (24K samples from HouseExpo)
│   │   ├── val.jsonl       # 15% (5K samples)
│   │   └── test.jsonl      # 15% (5K samples)
│   │
│   ├── text_pairs/         # NLP training data
│   │   ├── train.jsonl     # Text + spec pairs
│   │   ├── val.jsonl
│   │   └── test.jsonl
│   │
│   └── ifc_metadata/       # BIM examples
│       └── *.json
│
└── models/                 # Trained model weights
    ├── nlp_t5/
    └── layout_diffusion/
🎯 Recommended Acquisition Priority
Week 1 (This Week):
✅ HouseExpo - Easiest to download (500 MB, 35K layouts)
✅ IFC Samples - Download 20-30 from GitHub/BIMData
✅ Synthetic Text - Generate 100 descriptions manually
Start Training: NLP model with 100 samples

Week 2:
CubiCasa5k - Higher quality (1.5 GB, 5K layouts)
More IFC Models - Collect 50 total
GPT-4 Text Gen - Scale to 1000 descriptions
Start Training: Layout AI with combined datasets

Week 3-4:
RPLAN - Keep trying to get access (best dataset)
Augmentation - Rotate/flip existing layouts for 2x data
🚀 Quick Start Commands (Copy-Paste)
# Navigate to project
cd d:\Work\Uni\FYP\architext
# Create structure
New-Item -ItemType Directory -Force -Path datasets\raw
New-Item -ItemType Directory -Force -Path datasets\processed\layouts
New-Item -ItemType Directory -Force -Path datasets\ifc_models
# Clone HouseExpo
cd datasets\raw
git clone https://github.com/TeaganLi/HouseExpo.git
# Back to project root
cd d:\Work\Uni\FYP\architext
# Install dependencies
pip install ifcopenshell lxml beautifulsoup4
# Ready to process!
📝 Next Steps After Download
Verify downloads: Check file counts and sizes
Run processing scripts: Convert to standard format
Create train/val/test splits: 70/15/15 split
Generate text descriptions: Manual or GPT-4
Start NLP training: Fine-tune T5 on text-spec pairs
First Milestone: 100 text-layout pairs ready for training