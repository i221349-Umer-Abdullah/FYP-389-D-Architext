# ArchiText Blender Add-on

Convert natural language descriptions to 3D building models directly in Blender.

## Installation

### Prerequisites
1. **Blender 4.0+** (or 5.0) - https://blender.org
2. **Bonsai (BlenderBIM)** - https://blenderbim.org (for IFC import)

### Install the Add-on

**Method 1: Install from ZIP**
1. Download or create `architext.zip` (see below)
2. Open Blender
3. Go to Edit → Preferences → Add-ons
4. Click "Install..." button
5. Select `architext.zip`
6. Enable the add-on by checking the checkbox

**Method 2: Manual Installation**
1. Copy the `architext` folder to Blender's addons directory:
   - Windows: `%APPDATA%\Blender Foundation\Blender\4.0\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/4.0/scripts/addons/`
   - Linux: `~/.config/blender/4.0/scripts/addons/`
2. Open Blender → Edit → Preferences → Add-ons
3. Search for "ArchiText" and enable it

### Configure Scripts Path
1. After enabling the add-on, expand its preferences
2. Set "Scripts Path" to your ArchiText scripts folder:
   `D:\Work\Uni\FYP\architext\scripts` (or your actual path)

## Usage

1. Open Blender
2. Press `N` to open the sidebar (if not visible)
3. Click on the "ArchiText" tab
4. Enter a building description, e.g.:
   - "Modern 3 bedroom house with 2 bathrooms and open kitchen"
   - "Compact apartment with 1 bedroom, bathroom, and combined living-kitchen"
5. Click "Generate Building"
6. The IFC model will be imported automatically

### Quick Mode
Click "Quick Mode" for a dialog where you can specify:
- Number of bedrooms
- Number of bathrooms
- Kitchen, living room, dining room, study, garage options

This uses the rule-based optimizer (no NLP) for faster generation.

## Features

- Natural language input
- Automatic IFC generation
- Direct import into Blender via Bonsai
- Preset examples
- Customizable wall height and thickness
- Quick mode for simple specifications

## Troubleshooting

**"Scripts path not found"**
- Set the correct path in add-on preferences (Edit → Preferences → Add-ons → ArchiText)

**"Could not import modules"**
- Make sure all Python dependencies are installed in Blender's Python
- Or run the ArchiText scripts from the command line first to verify they work

**IFC not importing**
- Make sure Bonsai (BlenderBIM) is installed and enabled
- Try opening the generated IFC file manually: File → Open IFC Project

## Files Generated

Output files are saved to: `architext/output/`
- `blender_generated.ifc` - Full pipeline output
- `blender_quick_generated.ifc` - Quick mode output
