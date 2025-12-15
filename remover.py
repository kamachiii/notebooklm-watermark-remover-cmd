import fitz  # PyMuPDF
import statistics
import argparse
import sys
import os

def get_pixel_color(page, x, y):
    """
    Get the RGB color of the pixel at coordinates (x, y).
    Returns a tuple (r, g, b) with values between 0.0 and 1.0.
    """
    # Create a small 1x1 rect around the point
    rect = fitz.Rect(x, y, x+1, y+1)
    
    # Render that small area to a pixmap
    try:
        pix = page.get_pixmap(clip=rect)
        if pix.width == 0 or pix.height == 0:
            return (1, 1, 1) # Default to white if out of bounds
        
        r, g, b = pix.pixel(0, 0)
        return (r/255.0, g/255.0, b/255.0)
    except Exception as e:
        # Fallback for any rendering issues
        return (1, 1, 1)

def remove_watermark(input_path, output_path):
    """
    Removes the NotebookLM watermark from the bottom-right corner of each page
    by covering it with the detected background color.
    """
    try:
        doc = fitz.open(input_path)
    except Exception as e:
        print(f"Error opening file '{input_path}': {e}")
        sys.exit(1)

    print(f"Processing '{input_path}' ({len(doc)} pages)...")
    
    pages_processed = 0

    for page_num, page in enumerate(doc):
        w = page.rect.width
        h = page.rect.height
        
        # Define the watermark area to cover (bottom-right corner)
        # These coordinates are tuned for the standard NotebookLM watermark position
        cover_rect = fitz.Rect(w - 220, h - 60, w, h)
        
        # Define sample points to detect the background color.
        # We sample points slightly to the left and above the watermark area
        # to find the most likely background color.
        samples = [
            (w - 250, h - 30),  # Left of watermark
            (w - 250, h - 50),  # Left-Up
            (w - 100, h - 80),  # Above
            (w - 50, h - 80)    # Above-Right
        ]
        
        colors = []
        for sx, sy in samples:
            if sx > 0 and sy > 0:
                colors.append(get_pixel_color(page, sx, sy))
        
        # Calculate the median color to avoid outliers (e.g., text or noise)
        if colors:
            r = statistics.median([c[0] for c in colors])
            g = statistics.median([c[1] for c in colors])
            b = statistics.median([c[2] for c in colors])
            fill_color = (r, g, b)
        else:
            fill_color = (1, 1, 1) # Default to white
            
        # Draw a rectangle over the watermark area with the detected color
        page.draw_rect(cover_rect, color=fill_color, fill=fill_color, overlay=True)
        pages_processed += 1

    try:
        doc.save(output_path)
        print(f"Success! Cleaned PDF saved to: '{output_path}'")
    except Exception as e:
        print(f"Error saving file '{output_path}': {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Remove 'NotebookLM' watermarks from PDF slides by covering them with the background color."
    )
    
    parser.add_argument(
        "input_file", 
        help="Path to the input PDF file."
    )
    
    parser.add_argument(
        "-o", "--output", 
        help="Path to the output PDF file. If not provided, defaults to 'input_cleaned.pdf'.",
        default=None
    )

    args = parser.parse_args()
    
    input_path = args.input_file
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_cleaned{ext}"

    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    remove_watermark(input_path, output_path)

if __name__ == "__main__":
    main()
