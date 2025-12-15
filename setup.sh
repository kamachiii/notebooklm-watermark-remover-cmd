#!/bin/bash

# Setup script for NotebookLM Watermark Remover

echo "Setting up NotebookLM Watermark Remover environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt > /dev/null

echo "Setup complete!"
echo ""
echo "To use the tool, run:"
echo "source venv/bin/activate"
echo "python remover.py <your_pdf_file.pdf>"
