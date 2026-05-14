# ArchiText Revit Add-in

This package provides a Revit desktop bridge for ArchiText. The add-in does not
run the AI model inside Revit. Instead, it calls the existing ArchiText FastAPI
backend, downloads the generated IFC file, and imports or opens it in Revit.

## Recommended Demo Mode

The Revit workflow uses the **LLM generator** so users can generate BIM output
directly from a prompt inside Revit. The web app still supports Primary GNN vs
LLM comparison.

## Requirements

- Autodesk Revit 2026
- .NET 8 SDK or Visual Studio with .NET desktop build tools
- ArchiText backend running at `http://localhost:8000`
- Revit API DLLs installed with Revit
- Windows PowerShell

## Build

Run from this folder:

```powershell
.\build.ps1
```

The compiled files will be placed in:

```text
dist/
```

If `build.ps1` reports that no .NET SDK is installed, install the .NET 8 SDK
and rerun the build on the Revit laptop.

## Install

After building:

```powershell
.\install.ps1
```

Restart Revit. A new **ArchiText** ribbon panel should appear under Add-Ins.

## Usage

1. Start the ArchiText backend.
2. Open Revit.
3. Click `Add-Ins > ArchiText > Generate Floor Plan`.
4. Enter a prompt.
5. Click Generate.
6. The add-in calls the LLM generator, downloads the generated IFC, and
   imports/opens it in Revit.

## Notes

- The add-in uses `generator_mode=llm`.
- Primary GNN remains the research contribution and is shown from the web app.
- If direct IFC import is unavailable in the active Revit context, the add-in
  falls back to opening the downloaded IFC file.
