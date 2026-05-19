# Getting Started
Follow these steps to install and run the NotebookLM Watermark Remover.

## Installation
### Method 1: Global Installation (Recommended)
This method installs the tool as a system-wide command notebook-remover.

1. Prerequisites: Ensure Python (3.8 or higher) and pip are installed.

``` bash
python --version
pip --version
```

> If these commands fail, install Python 3.8+ from python.org.

2. Install the tool:

``` bash
pip install git+https://github.com/kamachiii/notebooklm-watermark-remover-cmd.git
```

3. Run the command:

``` bash
notebook-remorer your-file.pdf
notebook-remover your-file.pptx
notebook-remover your-image.png
```

## Method 2: Local Virtual Environment Installation
If you prefer not to install globally or want an isolated environment, use this method.
1. Clone the repository:

``` bash
git clone https://github.com/kamachiii/notebooklm-watermark-remover-cmd.git
cd notebooklm-watermark-remover-cmd
```

2. Create and activate a virtual environment:

- Linux/macOS: `python3 -m venv venv` → `source venv/bin/activate`

- Windows: `python -m venv venv` → `venv\Scripts\activate`

3. Install dependencies:

``` bash
pip install -r requirements.txt
```

4. Run the tool:

``` bash
python remover.py your-file.pdf
```

## Troubleshooting
- `pip install git+...` fails: Make sure you have `git` installed (`git --version`).

- `pip install -r requirements.txt` fails due to OpenCV: Try installing `opencv-python-headless` manually first (`pip install opencv-python-headless`).

- `notebook-remover` command not found: This might be due to a missing PATH entry; try a global install or use the local method instead.
