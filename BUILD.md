# Building NotebookLM Watermark Remover

This document explains how to build the standalone executable for Windows.

## Requirements for Building

You need to install the development dependencies:

```bash
pip install -r requirements.txt -r requirements-build.txt
```

## Build Process (Windows)

To generate the `.exe` file, run:

```bash
python -m PyInstaller remover.spec --noconfirm
```

The resulting executable will be located in the `dist/` directory:
`dist\NotebookLM-Watermark-Remover.exe`

## Technical Details

- **PyInstaller:** Used to bundle the Python script and its dependencies into a single file.
- **Spec File:** `remover.spec` contains the configuration for the build process, including hidden imports for OpenCV and PyMuPDF.
