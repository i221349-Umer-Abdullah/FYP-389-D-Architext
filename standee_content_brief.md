# ArchiText: AI-Powered Text-to-BIM Generation

**Tagline:** From Description to 3D Design in Seconds.

## Overview
**ArchiText** is an innovative AI system that translates simple natural language descriptions into complete, industry-standard 3D Building Information Models (BIM). It bridges the gap between conceptual ideas and architectural drafting, allowing anyone to generate 3D structures simply by describing what they want.

---

## 🚀 How It Works: The Comprehensive End-to-End Pipeline

1. **User Prompt (Input)**
   *The user types what they want.* 
   *Example: "I need a 150 sq. meter house with 3 bedrooms, 2 bathrooms, a large living room, and a garden."*

2. **Language Understanding (NLP Engine)**
   * *What it does:* A fine-tuned T5 language model reads the text and extracts exact architectural requirements (room types, counts, and spatial constraints).

3. **Spatial Generation (Graph Neural Network - GNN)**
   * *What it does:* A custom-trained Graph Neural Network takes the requirements and calculates how the rooms should connect, yielding optimal locations, widths, heights, and structural adjacencies.

4. **3D BIM Compilation (IFC Export)**
   * *What it does:* Resolves the 2D layout into true 3D architecture, generating literal building volumes (slabs, walls, rooms) as an industry-standard `.ifc` model.
   *(Note: Standard detailing elements like doors and windows are programmatically injected during this generation stage).*

5. **Structural Integrity Analysis**
   * *What it does:* Runs advanced validation sweeps directly on the 3D building model to inspect overlap, code compliance, load-bearing considerations, and structural physics.

6. **Automated Cost Estimation**
   * *What it does:* Delivers real-time structural and material cost projections calculated directly from the explicit dimensions, footprints, and properties inside the 3D model.

---

## 💻 The User Interface 
*(Note for designer: Add mockups or placeholders for UI here)*

Our user interface makes the power of the AI accessible to everyone:
* **Prompt Box:** A simple text entry field for descriptions.
* **2D Floorplan Canvas:** An interactive, real-time preview showing the generated 2D layout.
* **3D Viewport:** A built-in 3D viewer allowing users to rotate, pan, and inspect the final 3D architectural model directly in the browser.

---

## 🌟 Why It Matters
* **For Professionals:** Rapid prototyping. Get a baseline 3D BIM model in seconds to kickstart the design process.
* **For Laymen:** Democratizes design. Anyone can visualize their dream home without learning complex CAD software.
* **Technical Innovation:** Seamlessly stacks cutting-edge Natural Language Processing (NLP) with geometric Graph Neural Networks (GNNs) and traditional BIM scripting.

---

## 🛠️ Technology Stack (Include Logos)
*(Designer note: Arrange these logos in a clean grid or strip at the bottom/side)*

**Frontend (User Interface & 3D Web):**
* **React.js / Next.js:** For building a fast, dynamic web interface.
* **Three.js / React Three Fiber:** To render the interactive 3D architectural models correctly in the browser.
* **Tailwind CSS:** For sleek, modern UI styling.

**Backend & AI Infrastructure:**
* **Python & FastAPI:** High-performance backend routing and pipeline orchestration.
* **PyTorch:** The deep learning engine powering our custom Graph Neural Networks (GNN).
* **Hugging Face (T5):** For state-of-the-art Natural Language Processing (NLP) generation.

**BIM & Geometry Engine:**
* **IfcOpenShell / BlenderBIM:** For programmatic generation of industry-standard `.ifc` 3D building files.
