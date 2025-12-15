# NotebookLM Watermark Remover

A lightweight, cross-platform Python tool designed to cleanly remove the "NotebookLM" watermark from PDF slides.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-blue)

## Features

-   **Smart Detection:** Doesn't just crop the page. It detects the background color surrounding the watermark.
-   **Clean Removal:** Covers the watermark with the exact background shade, preserving the slide's aesthetics.
-   **Batch Friendly:** Can be easily modified or looped in a shell to process multiple files (CLI support).
-   **Cross-Platform:** Works on Windows, macOS, and Linux.

## Prerequisites

-   **Python 3.6** or higher.
-   **pip** (standard Python package manager).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Albonire/notebooklm-watermark-remover.git
    cd notebooklm-watermark-remover
    ```

2.  **Set up a Virtual Environment (Recommended):**

    *   **Windows:**
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
    *   **macOS / Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Basic Usage
Run the script passing the path to your PDF file. The tool will generate a cleaned version in the same directory.

```bash
python remover.py path/to/presentation.pdf
```
*Output:* `path/to/presentation_cleaned.pdf`

### Custom Output Location
You can specify where to save the cleaned file:

```bash
python remover.py original.pdf -o cleaned/final_presentation.pdf
```

### Help Command
View all available options:
```bash
python remover.py --help
```

## Project Structure

```
notebooklm-watermark-remover/
├── remover.py          # Main script
├── requirements.txt    # Dependencies (PyMuPDF)
├── README.md           # Documentation
├── LICENSE             # MIT License
└── .gitignore          # Git configuration
```

## Contributing

Contributions are welcome, so feel free to submit a Pull Request.

1.  Fork the project
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).