# NotebookLM Watermark Remover

![Captura de funcionalidad del proyecto](public/screenshot.jpg)

[English](README.md) | [中文](README_zh.md)

A powerful tool that cleanly removes the "NotebookLM" watermark from your PDF slides, PowerPoint presentations (PPTX), and images/infographics (PNG, JPG) using advanced computer vision techniques.

## What It Does

**Smart Removal (Inpainting):**
Instead of just covering the watermark with a solid color box (which looks bad on gradients or textured backgrounds), this tool uses **AI-based Inpainting (Computer Vision)**.
- **Detects** the watermark by analyzing local contrast and blur differences.
- **Reconstructs** the background behind the text, preserving gradients, textures, and slide borders.
- **Smart Filtering:** Intelligently ignores slide content (text, lines) that might be close to the watermark area, ensuring only the logo/text is removed.

**Supported Formats:**
- **PDF Documents:** Patches the watermark on every page seamlessly.
- **PPTX Presentations:** Removes the watermark from PowerPoint files exported by NotebookLM.
- **Images:** Supports PNG (including transparency/alpha channel), JPG, JPEG, and WEBP.

**Features:**
- Batch processing: Clean entire folders in one go.
- Progress bar for tracking large tasks.
- Preview mode (PDFs) to test settings on the first page.
- Smart auto-detection of file types.

## Getting Started

### Using Python (All Platforms)

1. **Set things up:**
```bash
python3 -m venv venv
source venv/bin/activate  # Windows folks: venv\Scripts\activate
```

2. **Grab the dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the tool:**
```bash
python3 remover.py presentation.pdf
```

### Using EXE (Windows Only)

If you have built the executable (see [BUILD.md](BUILD.md)), you can run it directly:
```bash
dist\NotebookLM-Watermark-Remover.exe presentation.pdf
```

## How to Use It

### Single file (PDF, PPTX, or Image)
```bash
python3 remover.py presentation.pdf
# OR
python3 remover.py presentation.pptx
# OR
python3 remover.py slide.png
```
Creates `presentation_cleaned.pdf`, `presentation_cleaned.pptx`, or `slide_cleaned.png` in the same folder.

### Batch process a folder
```bash
python3 remover.py ./my_folder/
```
Automatically detects and cleans all supported files (`.pdf`, `.pptx`, `.png`, `.jpg`, etc.) in the directory.

### Try before you commit (PDF only)
Check how it looks on just the first page:
```bash
python3 remover.py file.pdf --preview
```

## What's Inside

- `remover.py` - Core logic using PyMuPDF and OpenCV.
- `remover.spec` - PyInstaller configuration for Windows.
- `requirements.txt` - Core dependencies.
- `BUILD.md` - Instructions for building the executable.
- `LICENSE` - MIT License

## Want to Help?

Pull requests are welcome. Feel free to open an issue or contribute!
