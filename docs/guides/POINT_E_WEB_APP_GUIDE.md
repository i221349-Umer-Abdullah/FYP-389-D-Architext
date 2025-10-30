# Point-E Web App Guide

## Problem Diagnosed ❌

Your Point-E .ply files appear empty in Blender because:

1. **point_e_improved_house.ply**: CORRUPTED - 0 vertices but 5,089 faces
2. **point_e_test_house.ply**: Only 8 vertices - too simple to see
3. **point_e_point_cloud.ply**: ✅ THIS ONE IS GOOD (4,096 points)

### Why Blender Shows Nothing:
- Meshes with 0 vertices or only vertices at origin appear invisible
- The Alpha Shape reconstruction in the test script failed silently
- Blender needs actual geometry to display

---

## Solution: Use the Point-E Web App

I created a standalone Point-E web app that:
- ✅ Generates point clouds correctly
- ✅ Converts to proper meshes using subdivided convex hull
- ✅ Shows real-time 3D preview
- ✅ Provides downloadable PLY and OBJ files
- ✅ Has same dark theme as Shap-E app

---

## How to Run Point-E Web App

### Step 1: Open Command Prompt
```bash
cd D:\Work\Uni\FYP\architext
```

### Step 2: Activate Virtual Environment
```bash
venv\Scripts\activate
```

### Step 3: Run Point-E Web App
```bash
python app\demo_point_e_app.py
```

### Step 4: Open in Browser
```
http://127.0.0.1:7861
```

**Note**: Different port (7861) than Shap-E app (7860) so you can run both!

---

## Using the Point-E Web App

### Generate a House:
1. **Enter prompt**: "a modern two-story house with windows and door"
2. **Set guidance**: 7.0 (default) or higher for more detail
3. **Click "Generate My House"**
4. **Wait**: 3-5 minutes for generation
5. **View**: 3D preview appears automatically
6. **Download**: PLY and OBJ files available

### Guidance Scale Tips:
- **1-5**: More creative, less structured
- **7-10**: Balanced (recommended)
- **10-15**: Very structured, follows prompt closely

---

## Viewing Point-E Output

### In Blender (Recommended):
1. Open Blender
2. Delete default cube (X key)
3. File → Import → Stanford (.ply) or Wavefront (.obj)
4. Navigate to `D:\Work\Uni\FYP\architext\outputs\`
5. Select the file
6. View in viewport

### In Windows 3D Viewer:
1. Navigate to outputs folder
2. Double-click the .ply file
3. Windows 3D Viewer opens automatically

### Online:
1. Go to https://3dviewer.net/
2. Drag and drop the file
3. View in browser

---

## Point Cloud File (Already Good!)

The file **point_e_point_cloud.ply** (4,096 points) IS working!

### To view it in Blender:
1. File → Import → Stanford (.ply)
2. Select `point_e_point_cloud.ply`
3. Switch viewport shading to "Solid" or "Material Preview"
4. You should see 4,096 colored points

### If points are too small:
- Select the point cloud
- In Properties panel → Object Data → Viewport Display
- Increase "Point Size" to 5 or 10

---

## Comparison: Test Scripts vs Web App

| Feature | Test Scripts | Web App |
|---------|-------------|---------|
| Output | Files only | Files + Preview |
| Reliability | Alpha shape can fail | Subdivided convex hull (reliable) |
| Visualization | External viewer needed | Built-in 3D preview |
| Debugging | Hard to see issues | Real-time feedback |
| User-friendly | Command line | Web interface |

**Recommendation**: Use the web app for testing!

---

## Running Both Apps Simultaneously

### Terminal 1 - Shap-E (Port 7860):
```bash
cd D:\Work\Uni\FYP\architext
venv\Scripts\activate
python app\demo_app.py
```

### Terminal 2 - Point-E (Port 7861):
```bash
cd D:\Work\Uni\FYP\architext
venv\Scripts\activate
python app\demo_point_e_app.py
```

### Access:
- **Shap-E**: http://127.0.0.1:7860
- **Point-E**: http://127.0.0.1:7861

---

## Fixing the .PLY Import Issue in Blender

If you still see nothing after importing:

### Check 1: Object Exists
- Look in Outliner panel (top right)
- Is the imported object listed?

### Check 2: Object Location
- Select object in Outliner
- Press `.` (period) on numpad to "Frame Selected"
- Or manually check Transform properties

### Check 3: Display Settings
- Switch viewport shading modes (top right icons)
- Try: Wireframe, Solid, Material Preview, Rendered

### Check 4: Scale
- Object might be too small or too large
- Press `S` key and move mouse to scale
- Or check Transform → Scale values

### Check 5: For Point Clouds
- Object Data Properties → Viewport Display
- Increase Point Size to 5-10

---

## Summary

### Issue:
❌ Test script PLY files corrupted (0 vertices)
✅ Point cloud file is good (4,096 points)

### Solution:
✅ Use Point-E Web App for reliable generation
✅ Web app uses subdivided convex hull (always works)
✅ Real-time 3D preview to verify output
✅ Download working PLY/OBJ files

### To Test Now:
```bash
cd D:\Work\Uni\FYP\architext
venv\Scripts\activate
python app\demo_point_e_app.py
```

Then open: http://127.0.0.1:7861

Generate a house and see it in the web preview immediately!
