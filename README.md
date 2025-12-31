# NotebookLM Watermark Remover

A straightforward tool that cleanly removes the "NotebookLM" watermark from your PDF slides while keeping everything else intact.

## What It Does

**Smart Detection:**
- **Text Layer:** Finds "NotebookLM" written as actual text
- **Vector Graphics:** Catches letters drawn as shapes (common in exported PDFs)
- **Pixel Analysis:** If all else fails, scans the corner to locate the exact watermark area

**Clean Removal:**
- Adapts the removal area to fit the actual watermark size—no one-size-fits-all approach
- Analyzes your page margins to match the background color perfectly, ignoring nearby elements
- Processes entire folders of PDFs in one go
- Shows you a progress bar so you're not left wondering
- Test on a single page before running on your whole document

## Getting Started

1. **Fresh start (if needed):**
```bash
rm -rf venv
```

2. **Set things up:**
```bash
python -m venv venv
source venv/bin/activate  # Windows folks: venv\Scripts\activate
```

3. **Grab the dependencies:**
```bash
pip install -r requirements.txt
```

## How to Use It

### Single file
```bash
python remover.py presentation.pdf
```
Creates `presentation_cleaned.pdf` in the same folder.

### Batch process a folder
```bash
python remover.py ./pdf_folder/
```

### Try before you commit
Check how it looks on just the first page:
```bash
python remover.py file.pdf --preview
```

### Override the background color
If the auto-detection doesn't nail it:
```bash
python remover.py file.pdf --color "#FFFFFF"
```

## What's Inside

- `remover.py` - Does all the heavy lifting
- `requirements.txt` - Lists what you need (PyMuPDF, tqdm)
- `LICENSE` - MIT License

## Want to Help?

Pull requests are welcome. Found a bug? Open an issue.