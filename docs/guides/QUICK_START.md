# QUICK START GUIDE
## Get Your Demo Running in 15 Minutes

**For:** Umer Abdullah - AI/ML Module
**Goal:** Working text-to-3D house demo for FYP presentation

---

## Step 1: Install Python (if not already installed)

1. Download Python 3.10 from: https://www.python.org/downloads/
2. During installation, **CHECK** "Add Python to PATH"
3. Verify installation:
   ```bash
   python --version
   ```
   Should show: `Python 3.10.x` or higher

**Time:** 5 minutes

---

## Step 2: Run Setup

Open Command Prompt in the `architext` folder and run:

```batch
setup.bat
```

**What it does:**
- Creates Python environment
- Installs PyTorch (AI framework)
- Installs all dependencies
- Creates output folders

**Time:** 5-10 minutes (depends on internet speed)

⚠️ **IMPORTANT:** This will download ~3GB of data (PyTorch + models)

---

## Step 3: Test Shap-E Model

```batch
test_shap_e.bat
```

**What it does:**
- Downloads Shap-E model (~2GB, first time only)
- Generates 5 test house models
- Saves them as .obj and .ply files

**Time:** 10-15 minutes first time, 5 minutes after

**Output:** `outputs/shap_e_tests/` - contains generated 3D models

**Check the results:**
- Download Blender (free): https://www.blender.org/download/
- Open Blender → File → Import → Wavefront (.obj)
- Browse to `outputs/shap_e_tests/` and open any .obj file

---

## Step 4: Launch Demo UI

```batch
run_demo.bat
```

**What happens:**
- Gradio web UI starts
- Browser opens automatically at http://localhost:7860
- You can now generate houses from text!

**How to use:**
1. Enter description: "a modern two-story house with large windows"
2. Select Quality: "Medium"
3. Click "Generate House"
4. Wait 1-2 minutes
5. Download the OBJ file
6. View in Blender

**Time:** Instant startup, 1-2 min per generation

---

## Step 5: Prepare for Demo (CRITICAL)

### A. Pre-generate 5-10 Example Models

In the demo UI, generate these:

1. "a modern minimalist house with flat roof"
2. "traditional two-story suburban home with garage"
3. "small cottage with chimney"
4. "contemporary house with balcony"
5. "simple one-story residential building"

**Save all the OBJ files!** These are your backup if live demo fails.

### B. Test on Your Presentation Laptop

1. Copy entire `architext` folder to presentation laptop
2. Run `run_demo.bat`
3. Generate 1 test model to verify it works
4. **IMPORTANT:** Pre-load the demo UI before presentation

### C. Create Backup Materials

1. Take screenshots of the Gradio UI
2. Take screenshots of generated models in Blender
3. Record a 30-second video of generation process
4. Export best 3-5 models as .obj files for manual showing

---

## Quick Reference Commands

```batch
setup.bat              # First-time setup (do this once)
run_demo.bat          # Launch web UI (main demo)
test_shap_e.bat       # Test Shap-E model
test_point_e.bat      # Test Point-E model (optional)
compare_models.bat    # Compare all models (optional)
```

---

## Troubleshooting

### "Python not found"
- Reinstall Python with "Add to PATH" checked
- Restart Command Prompt

### "CUDA out of memory"
- In demo UI, select "Low (Fast)" quality
- Or edit `app/demo_app.py`, change default to "Low"

### "Model download stuck"
- It's not stuck, just slow (2-3GB download)
- Wait 10-15 minutes
- Check internet connection

### "Generation fails"
- Try simpler prompt: "a simple house"
- Select "Low" quality
- Restart demo: Ctrl+C, then `run_demo.bat` again

### "Demo won't start"
- Check if port 7860 is in use
- Close other applications using that port
- Or change port in `app/demo_app.py` (line with `server_port=7860`)

---

## Emergency Backup Plan for Presentation

If live demo fails:

1. **Show pre-generated models** (you made 5-10, right?)
2. **Show screenshots** of the working UI
3. **Play video** of generation process
4. **Import model to Blender** live to show it's real 3D
5. **Explain** the technology and show code

**Even if generation doesn't work live, you have proof it works!**

---

## Presentation Tips

### What to Show (7 minutes)

1. **Problem:** Manual 3D modeling is slow (30 sec)
2. **Solution:** AI generates from text (30 sec)
3. **Demo UI:** Show Gradio interface (1 min)
4. **Live Generation:** Generate one house (2 min)
   - While waiting, explain the technology
   - "Using Shap-E, a text-to-3D model from OpenAI"
   - "Generates 3D meshes with [X] vertices"
5. **Show Result:** Display in Blender (1 min)
6. **Gallery:** Show 5 pre-made examples (1 min)
7. **Future:** Explain Revit integration plan (1 min)

### What to Say During 2-Minute Wait

While model is generating:

- "We're using Shap-E, OpenAI's text-to-3D diffusion model"
- "It's generating a 3D mesh with approximately 1000-2000 vertices"
- "The model enhances prompts with architectural keywords"
- "Post-processing scales the mesh to realistic dimensions"
- "Output is OBJ format, compatible with Revit, Blender, Maya"
- "For next iteration, we'll integrate this with Revit plugin"

### If Asked About Quality

**Be honest:**
- "This is a pre-trained general model, not trained on houses specifically"
- "Iteration 2 will fine-tune on architectural datasets"
- "Current focus is proving the concept works"
- "Already generating recognizable house shapes in 2 minutes"

---

## Quality Check Before Demo

✅ **One day before presentation:**

1. Test on presentation laptop
2. Verify all 5 example models generated
3. Confirm Blender can open the .obj files
4. Practice demo flow (3 run-throughs)
5. Prepare answers to expected questions
6. Charge laptop fully
7. Have backup screenshots/videos ready

✅ **Morning of presentation:**

1. Start `run_demo.bat` to pre-load models into memory
2. Generate 1 test house to verify everything works
3. Open Blender with one example model pre-loaded
4. Have backup USB with all files

---

## Expected Results

### Shap-E Output Quality

- **Vertices:** 1,000 - 3,000
- **Faces:** 2,000 - 5,000
- **Shape:** Recognizable as a house-like structure
- **Details:** Abstract (not photorealistic)
- **Time:** 1-2 minutes per generation
- **Format:** Clean OBJ meshes

**Realistic Expectation:** Generated models will look like simple, abstract house shapes - good enough for proof of concept!

---

## Files You'll Show

1. `outputs/shap_e_tests/*.obj` - Test outputs
2. `outputs/demo/*.obj` - Demo-generated houses
3. Screenshots of Gradio UI
4. Blender with imported model
5. `docs/development_history.md` - Technical docs

---

## Talking Points for Q&A

**Q: Why not train your own model?**
A: Training requires weeks and expensive GPUs. For Iteration 1, we're validating the approach with pre-trained models. Iteration 2 will fine-tune on architectural data.

**Q: How will this integrate with Revit?**
A: [Jalal is building the Revit plugin. Our Python backend generates OBJ files, which the plugin will import via IPC bridge. Demo in Iteration 2.]

**Q: What about structural feasibility?**
A: That's Module 4 in our architecture. Current focus is 3D generation. Structural analysis comes in Iteration 3-4.

**Q: Can it do floor plans?**
A: Not yet. Considering adding House-GAN++ for floor plan generation in Iteration 2, then extruding to 3D.

**Q: What datasets will you use?**
A: [Arfeen is working on Structured3D, 3D-FRONT, and SUNCG datasets. We'll fine-tune models on these in Iteration 2.]

---

## Success Criteria for Iteration 1

You will PASS if you show:

✅ Working demo that generates ANY 3D output from text
✅ At least 5 example models
✅ Evidence of model comparison/testing
✅ Clear plan for next iteration
✅ Good understanding of the technology

**You DON'T need:**
- Perfect house models
- Revit integration (that's Iteration 2)
- Custom-trained models
- Photorealistic output

---

## Time Budget

- **Setup:** 15 minutes (one-time)
- **Testing:** 30 minutes (generate 5 examples)
- **Prep for demo:** 30 minutes (screenshots, videos, practice)
- **Total:** ~1.5 hours to be demo-ready

**You can do this!** The hard part (code) is done. Now just run it and show results.

---

**FINAL CHECKLIST:**

- [ ] Python installed
- [ ] Setup.bat completed successfully
- [ ] Shap-E test ran and generated 5 models
- [ ] Demo UI launches without errors
- [ ] Generated at least 5 backup examples
- [ ] Tested on presentation laptop
- [ ] Screenshots and videos saved
- [ ] Practiced presentation flow
- [ ] Blender installed and can open OBJ files
- [ ] Charged laptop + backup power

**Good luck with your demo! 🚀**
