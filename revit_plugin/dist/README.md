# ArchiText Revit Add-in

This package provides a Revit desktop bridge for ArchiText. The add-in does not
run the AI models inside Revit. Instead, it calls the existing ArchiText FastAPI
backend, downloads the generated IFC file, and imports or opens it in Revit.

## Recommended Demo Mode

Use **Primary GNN** as the default generator. Use **LLM Baseline** only when you
want to compare the trained model against the LLM path.

## Requirements

- Autodesk Revit 2026
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
5. Choose `Primary GNN` or `LLM Baseline`.
6. Click Generate.
7. The add-in downloads the generated IFC and imports/opens it in Revit.

## Notes

- The add-in defaults to `Primary GNN` because that is the FYP research
  contribution.
- The LLM option is included as a comparison baseline.
- If direct IFC import is unavailable in the active Revit context, the add-in
  falls back to opening the downloaded IFC file.

