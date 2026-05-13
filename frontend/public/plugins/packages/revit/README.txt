Architext Revit Plugin

This package contains the Architext Revit add-in source, manifest, build script,
and install script. Build it on the Revit machine using the .NET 8 SDK, then run
install.ps1 to place the add-in under the Revit 2026 Addins folder.

Workflow:
- Click the ArchiText ribbon button in Revit.
- Enter a natural language prompt.
- Generate through the local FastAPI backend.
- Default generator is Primary GNN; LLM Baseline is available for comparison.
- Download and import/open the generated IFC in Revit.
