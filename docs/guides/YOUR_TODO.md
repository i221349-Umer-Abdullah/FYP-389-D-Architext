# YOUR ACTION ITEMS - Umer's TODO List

**Current Status:** All code implemented ✅
**Your Task:** Test, evaluate, and prepare for demo

---

## IMMEDIATE ACTIONS (Do These NOW)

### 1. Run Setup (10 minutes)
```batch
cd D:\Work\Uni\FYP\architext
setup.bat
```

**Wait for it to complete.** It will download ~3GB of packages.

**If it fails:** Check QUICK_START.md troubleshooting section

---

### 2. Test Shap-E Model (15 minutes)
```batch
test_shap_e.bat
```

**This will:**
- Download Shap-E model (~2GB)
- Generate 5 test houses
- Save to `outputs/shap_e_tests/`

**What YOU do:**
1. Let it run (takes 10-15 min)
2. When done, open `outputs/shap_e_tests/` folder
3. Look at the .obj files (use Windows 3D Viewer or download Blender)
4. **EVALUATE:** Do they look like houses? Good enough for demo?

---

### 3. Launch Demo UI (2 minutes)
```batch
run_demo.bat
```

**What YOU do:**
1. Browser opens to http://localhost:7860
2. Try generating a house: "a modern two-story house"
3. Select "Medium" quality
4. Click "Generate House"
5. **Wait 1-2 minutes**
6. Download the OBJ file
7. **Check:** Does it look decent?

---

### 4. Generate 5-10 Backup Examples (30 minutes)

**CRITICAL FOR DEMO SUCCESS**

Using the demo UI, generate these prompts:

1. "a modern minimalist house with flat roof"
2. "traditional two-story suburban home with garage"
3. "small cottage with chimney and front porch"
4. "contemporary house with large glass windows"
5. "simple one-story residential building"
6. "Victorian style house with pitched roof"
7. "compact urban dwelling with balcony"
8. "ranch style house with wide layout"
9. "mediterranean villa with terrace"
10. "modern house with geometric design"

**For each one:**
- Download the OBJ file
- Save to a dedicated folder: `outputs/demo_backups/`
- Rename files clearly: `01_modern_minimalist.obj`, etc.

**Why?** If live generation fails during presentation, you have these as proof it works!

---

## EVALUATION TASKS (Your Responsibility)

### 5. Evaluate Model Quality (30 minutes)

For each generated model, rate it:

**Create a spreadsheet:**
| Prompt | Quality (1-10) | Looks Like House? | Would Show in Demo? | Notes |
|--------|----------------|-------------------|---------------------|-------|
| modern minimalist | 7 | Yes | Yes | Good shape, abstract details |
| traditional suburban | 5 | Kinda | Maybe | Too abstract |
| ... | ... | ... | ... | ... |

**Questions to answer:**
- Which model style works best? (modern, traditional, simple?)
- What level of detail do we get?
- Are results consistent for similar prompts?
- What are the limitations?

**Document this in:** `outputs/my_evaluation.md`

---

### 6. Test Different Parameters (30 minutes)

In the demo UI, experiment:

**Try different quality settings:**
- Low (Fast) - how bad is it?
- Medium - default
- High (Slow) - how much better?

**Try different guidance scales:**
- 10 - more creative/abstract
- 15 - balanced (default)
- 20 - more literal to prompt

**Document what works best for demo in:** `outputs/best_settings.md`

Example:
```markdown
# Best Settings for Demo

After testing, I found:
- Quality: Medium (good balance, 1-2 min)
- Guidance: 15.0 (follows prompts well)
- Best prompts: Simple, modern houses
- Avoid: Very specific details (windows, doors)

Best results:
1. "modern house" - 8/10 quality
2. "simple cottage" - 7/10 quality
...
```

---

### 7. Compare with Point-E (OPTIONAL - 20 minutes)

**Only if you have time:**
```batch
test_point_e.bat
```

Then compare Shap-E vs Point-E outputs.

**Likely result:** Shap-E will be better for houses. But good to have data.

---

## DEMO PREPARATION (Critical!)

### 8. Create Presentation Slides (60 minutes)

**Suggested structure (15-20 slides):**

1. **Title:** Architext - AI Text-to-House Generation
2. **Team:** Names and roles
3. **Problem:** Manual 3D modeling is slow and expensive
4. **Solution:** AI generates houses from text descriptions
5. **System Architecture:** 5-layer diagram (from proposal)
6. **Technology Stack:** Python, PyTorch, Shap-E, Gradio
7. **Iteration 1 Goals:** Test pre-trained models, build demo
8. **Live Demo Intro:** "Let me show you..."
9. **[LIVE DEMO HAPPENS HERE]**
10. **Example Gallery:** Your 5-10 pre-generated houses
11. **Model Comparison:** Shap-E vs alternatives (if you tested)
12. **Quality Analysis:** What works, what doesn't
13. **Technical Challenges:** Mesh quality, architectural details
14. **Current Limitations:** Pre-trained models, no custom training yet
15. **Next Steps:** Iteration 2 - Revit integration, fine-tuning
16. **Timeline:** Show iteration roadmap
17. **Team Contributions:** What each member did
18. **Q&A**

**Include:**
- Screenshots of demo UI
- Images of generated houses (render in Blender)
- Code snippets (core_generator.py key functions)
- Metrics (generation time, vertex count, etc.)

---

### 9. Practice Demo Flow (60 minutes)

**Rehearse 3 times:**

**Script:**
1. "This is our Gradio demo interface..."
2. "Let me generate a modern house..."
3. [Type prompt, explain what you're doing]
4. "I'm using Shap-E model with medium quality..."
5. [Click generate]
6. **WHILE WAITING (critical!):** "The model is running diffusion process, generating 3D mesh with ~2000 vertices. It enhances the prompt with architectural keywords. Takes 1-2 minutes for medium quality..."
7. [Show result]
8. "Here's the generated 3D model. Let me open it in Blender..."
9. [Import to Blender, rotate, show it's real 3D]
10. "And here are 5 more examples I pre-generated..."

**Time yourself:** Should be 7-8 minutes total.

---

### 10. Prepare Backup Materials (30 minutes)

**In case demo fails:**

1. **Screenshots:**
   - Demo UI (empty state)
   - Demo UI (with prompt entered)
   - Demo UI (generating...)
   - Demo UI (result shown)
   - Blender with imported model

2. **Video Recording:**
   - Record full generation process (30-60 sec)
   - Use Windows Game Bar (Win+G)
   - Show from prompt entry to 3D result

3. **Exported Models:**
   - Have 5 best .obj files ready
   - Can manually import to Blender during presentation

4. **Comparison Report:**
   ```batch
   compare_models.bat
   ```
   - Run this to generate markdown report
   - Shows you did systematic evaluation

---

### 11. Test on Presentation Laptop (CRITICAL - 30 minutes)

**The day before presentation:**

1. Copy entire `architext` folder to presentation laptop
2. Run `setup.bat` (yes, again on that laptop)
3. Test `run_demo.bat`
4. Generate 1 test house to confirm it works
5. **Note:** Keep demo running before presentation (pre-loads models)

**If presentation laptop is too slow:**
- Use your development laptop for demo
- Have HDMI cable ready
- Test connection to projector

---

## YOUR CHECKLIST

**Before presentation:**

### Technical Setup
- [ ] `setup.bat` completed successfully
- [ ] `test_shap_e.bat` ran and generated 5 models
- [ ] `run_demo.bat` launches without errors
- [ ] Generated 5-10 backup example houses
- [ ] Tested on presentation laptop
- [ ] Blender installed and can open .obj files

### Content Preparation
- [ ] Evaluated model quality (spreadsheet/document)
- [ ] Documented best settings for demo
- [ ] Created presentation slides (15-20 slides)
- [ ] Screenshots of demo UI saved
- [ ] Video of generation process recorded
- [ ] Practiced demo flow 3+ times

### Backup Plans
- [ ] Have 5+ pre-generated models ready
- [ ] Screenshots if demo fails
- [ ] Video if live generation fails
- [ ] Can manually import OBJ to Blender
- [ ] Comparison report generated

### Day Of
- [ ] Laptop fully charged
- [ ] Backup power bank/charger
- [ ] HDMI cable (if needed)
- [ ] Demo pre-loaded (run_demo.bat running)
- [ ] Blender open with 1 example model
- [ ] Notes/talking points ready

---

## REALISTIC EXPECTATIONS

**What you WILL have:**
✅ Working demo generating 3D shapes from text
✅ 5-10 example models as proof
✅ Professional web UI
✅ Evidence of systematic testing
✅ Clear plan for next iteration

**What you WON'T have (and that's OK):**
❌ Perfect photorealistic houses
❌ Detailed windows/doors/textures
❌ Revit integration (that's Iteration 2)
❌ Custom-trained model

**Your message:** "This proves the concept works. We can generate 3D house-like structures from text in under 2 minutes using pre-trained models. Next iteration will fine-tune on architectural data and integrate with Revit."

---

## IF THINGS GO WRONG

### Demo fails during presentation
→ Show pre-generated examples
→ Play video of working demo
→ Import OBJ to Blender manually

### Model quality is poor
→ Be honest: "Pre-trained model, not specialized for houses"
→ Show it's still recognizable as a building
→ Emphasize next iteration will improve

### Questions you can't answer
→ "That's a great question for [future iteration/team member]"
→ "We're focusing on core generation in Iteration 1"
→ "I can follow up with more details after"

---

## ESTIMATED TIME INVESTMENT

- **Setup & Testing:** 2 hours
- **Evaluation:** 2 hours
- **Demo Prep:** 3 hours
- **Presentation Materials:** 2 hours
- **Practice:** 2 hours
- **Total:** ~11 hours spread over 3-4 days

**You can do this in the time you have left!**

---

## FINAL NOTES

**This is Iteration 1.** The goal is NOT perfection. The goal is:
1. Prove the concept works
2. Show technical capability
3. Demonstrate progress
4. Set up for next iteration

**You have all the code.** Now you just need to:
1. Run it
2. Test it
3. Document what you find
4. Show it

**The hard part is done. You got this! 🚀**

---

## NEED HELP?

If something doesn't work:

1. Check `QUICK_START.md` troubleshooting section
2. Check `README.md` for detailed docs
3. Read error messages carefully
4. Try simpler/lower quality settings
5. Restart demo (`Ctrl+C`, then `run_demo.bat` again)

**Most common issue:** Out of memory
**Solution:** Use "Low" quality setting

**Second most common:** Slow internet
**Solution:** Be patient, models are big (2-3GB)

---

**START HERE:**
```batch
cd D:\Work\Uni\FYP\architext
setup.bat
```

**Then read this file again and check off items as you complete them.**

**Good luck! 🎓**
