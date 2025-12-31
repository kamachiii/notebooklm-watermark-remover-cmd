#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
import statistics
import argparse
import sys
import os
import math

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

def color_distance(c1, c2):
    """Calculate Euclidean distance between two RGB colors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

def analyze_background_for_rect(page, rect):
    """
    Analyzes the background color around a specific rectangle.
    Returns a dict with 'color' (median RGB) and 'variance' (max stdev).
    """
    x0, y0, x1, y1 = rect
    
    # Define sample points relative to the rectangle
    samples = [
        (x0 - 30, y0 + (y1-y0)/2),  # Left
        (x0 - 10, y0 - 10),         # Top-Left
        (x0 + (x1-x0)/2, y0 - 20),  # Top
        (x0 + (x1-x0)/2, y0 - 40),  # Top-Higher
        (x0 - 50, y0 + (y1-y0)/2)   # Left-Further
    ]
    
    colors = []
    for sx, sy in samples:
        if sx > 0 and sy > 0:
            colors.append(get_pixel_color(page, sx, sy))
    
    if not colors:
        return {'color': (1, 1, 1), 'variance': 0.0}

    # Calculate median color
    r = statistics.median([c[0] for c in colors])
    g = statistics.median([c[1] for c in colors])
    b = statistics.median([c[2] for c in colors])
    
    # Calculate variance (max standard deviation across channels)
    # If standard deviation is high, it means the background is noisy/gradient
    try:
        r_dev = statistics.stdev([c[0] for c in colors]) if len(colors) > 1 else 0
        g_dev = statistics.stdev([c[1] for c in colors]) if len(colors) > 1 else 0
        b_dev = statistics.stdev([c[2] for c in colors]) if len(colors) > 1 else 0
        variance = max(r_dev, g_dev, b_dev)
    except:
        variance = 0.0
        
    return {'color': (r, g, b), 'variance': variance}

def is_rect_clean(page, rect, bg_color, tolerance=0.05):
    """
    Checks if the area inside the rect is already clean (matches background).
    Samples 3 points inside the rect.
    """
    x0, y0, x1, y1 = rect
    mid_x = (x0 + x1) / 2
    mid_y = (y0 + y1) / 2
    
    # Sample center and slightly offset points
    check_points = [
        (mid_x, mid_y),
        (mid_x - 10, mid_y),
        (mid_x + 10, mid_y)
    ]
    
    for px, py in check_points:
        # Check simple bounds
        if px < 0 or py < 0: continue
        
        pixel = get_pixel_color(page, px, py)
        dist = color_distance(pixel, bg_color)
        
        # If any pixel differs significantly from background, it's NOT clean (has content)
        if dist > tolerance:
            return False
            
    # All sampled pixels match background -> Clean
    return True

def remove_watermark(input_path, output_path):
    """
    Removes the NotebookLM watermark using PDF Redaction.
    It attempts to find the text "NotebookLM". If found, it redacts that area.
    If not found, it falls back to redacting the standard bottom-right corner area.
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
        
def scan_for_content_bbox(page, search_rect):
    """
    Renders the search_rect area and scans pixels to find the bounding box
    of the *right-most* content cluster (the watermark).
    Returns (fitz.Rect, bg_color).
    """
    try:
        pix = page.get_pixmap(clip=search_rect)
        if pix.width < 2 or pix.height < 2:
            return None, (1, 1, 1)
            
        # Assume background color is the bottom-right-most pixel
        # This is usually the safest reference for the page 'base' color
        bg_r, bg_g, bg_b = pix.pixel(pix.width-1, pix.height-1)
        bg_color = (bg_r/255.0, bg_g/255.0, bg_b/255.0) # Normalize to 0-1 for PyMuPDF
        
        # Threshold for noise (JPEG artifacts etc)
        threshold = 25 
        
        min_x, min_y = pix.width, pix.height
        max_x, max_y = 0, 0
        found_any_content = False
        
        gap_limit = 15 
        current_gap = 0
        
        # Max width limit for a watermark (e.g. 180px)
        # If we scan further left than this, we force stop.
        # This prevents merging with nearby page content.
        max_watermark_width = 180 
        limit_x = pix.width - max_watermark_width
        
        for x in range(pix.width - 1, -1, -1):
            # Enforce Max Width
            if x < limit_x:
                break

            col_has_content = False
            for y in range(pix.height):
                r, g, b = pix.pixel(x, y)
                dist = math.sqrt((r-bg_r)**2 + (g-bg_g)**2 + (b-bg_b)**2)
                
                if dist > threshold:
                    col_has_content = True
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
            
            if col_has_content:
                found_any_content = True
                current_gap = 0
                if x < min_x: min_x = x
                if x > max_x: max_x = x
            elif found_any_content:
                current_gap += 1
                if current_gap > gap_limit:
                    break
        
        if not found_any_content:
            return None, bg_color
            
        final_min_y, final_max_y = pix.height, 0
        for x in range(min_x, max_x + 1):
            for y in range(pix.height):
                r, g, b = pix.pixel(x, y)
                dist = math.sqrt((r-bg_r)**2 + (g-bg_g)**2 + (b-bg_b)**2)
                if dist > threshold:
                    if y < final_min_y: final_min_y = y
                    if y > final_max_y: final_max_y = y
                    
        bbox = fitz.Rect(
            search_rect.x0 + min_x,
            search_rect.y0 + final_min_y,
            search_rect.x0 + max_x + 1,
            search_rect.y0 + final_max_y + 1
        )
        return bbox, bg_color
        
    except Exception as e:
        print(f"Warning: Pixel scan failed: {e}")
        return None, (1, 1, 1)

def detect_vector_watermark(page, search_rect):
    """
    Scans for small vector drawings (paths) in the search area.
    This helps detect watermarks that are converted to curves/outlines
    instead of real text, while ignoring large background boxes.
    """
    try:
        drawings = page.get_drawings()
        watermark_rect = None
        
        for shape in drawings:
            rect = shape["rect"]
            
            # Check if shape is inside our target corner
            if not rect.intersects(search_rect):
                continue
                
            # FILTER: Size Heuristic
            # The watermark is composed of small letters/shapes.
            # Real page content (like a footer box) is usually larger.
            # We ignore anything too wide or too tall.
            # "NotebookLM" is roughly 100-120px wide total, but individual shapes are small.
            # If a single shape is huge, it's background.
            if rect.width > 150 or rect.height > 40:
                continue
                
            # If it's a small shape in the corner, assume it's part of the watermark
            if watermark_rect is None:
                watermark_rect = rect
            else:
                watermark_rect |= rect # Union of rectangles
                
        return watermark_rect
    except Exception:
        return None

def get_dominant_corner_color(page):
    """
    Determines the background color by finding the most frequent color (Mode)
    in the bottom-right corner of the page. This filters out noise, text,
    and lines that might overlap with the corner.
    """
    try:
        w = page.rect.width
        h = page.rect.height
        
        # Sample a safe margin box in the corner (50x20)
        # This is large enough to contain mostly background, 
        # but small enough to focus on the watermark area.
        clip = fitz.Rect(w - 50, h - 20, w, h)
        pix = page.get_pixmap(clip=clip)
        
        if pix.width < 1 or pix.height < 1:
            return (1, 1, 1)
            
        # Frequency counter
        color_counts = {}
        
        for y in range(pix.height):
            for x in range(pix.width):
                # Get RGB as integer tuple for hashing
                rgb = pix.pixel(x, y) 
                color_counts[rgb] = color_counts.get(rgb, 0) + 1
                
        # Find the most frequent color
        most_frequent_rgb = max(color_counts, key=color_counts.get)
        
        # Normalize to 0-1 for PyMuPDF
        return (most_frequent_rgb[0]/255.0, most_frequent_rgb[1]/255.0, most_frequent_rgb[2]/255.0)
        
    except Exception as e:
        print(f"Warning: Color detection failed: {e}")
        return (1, 1, 1) # Default to white

def remove_watermark(input_path, output_path):
    """
    Removes the NotebookLM watermark using PDF Redaction.
    Strategies:
    1. Text Search (Best for real text)
    2. Vector Search (Best for outlined text, ignores large neighbors)
    3. Image Search (Best for bitmaps)
    4. Pixel Scan (Last resort)
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
        
        # Define the general danger zone (Bottom-Right)
        # We look broadly (250x80) but filter strictly
        search_area = fitz.Rect(w - 250, h - 80, w, h)
        
        target_rects = []
        detection_source = "Clean"
        
        # --- Strategy 1: Text Search ---
        search_clip = fitz.Rect(w/2, h/2, w, h)
        found_rects = page.search_for("NotebookLM", clip=search_clip)
        
        if found_rects:
            detection_source = "Text"
            padding = 2
            for r in found_rects:
                target_rects.append(fitz.Rect(r.x0-padding, r.y0-padding, r.x1+padding, r.y1+padding))
        
        # --- Strategy 2: Vector Path Detection (NEW) ---
        if not target_rects:
            vector_bbox = detect_vector_watermark(page, search_area)
            if vector_bbox:
                detection_source = "Vector"
                padding = 2
                target_rects = [fitz.Rect(
                    vector_bbox.x0 - padding, 
                    vector_bbox.y0 - padding, 
                    vector_bbox.x1 + padding, 
                    vector_bbox.y1 + padding
                )]

        # --- Strategy 3: Image Detection ---
        if not target_rects:
            try:
                images = page.get_image_info()
                found_images = []
                for img in images:
                    bbox = fitz.Rect(img['bbox'])
                    # Criteria: In corner, smallish
                    if bbox.intersects(search_area) and bbox.width < 150:
                        found_images.append(bbox)
                
                if found_images:
                    detection_source = "Image"
                    padding = 1
                    for r in found_images:
                         target_rects.append(fitz.Rect(r.x0-padding, r.y0-padding, r.x1+padding, r.y1+padding))
            except:
                pass

        # --- Strategy 4: Visual Pixel Scan (Fallback) ---
        detected_bg_color = None
        if not target_rects:
            # Stricter scan area: Only bottom 40px to avoid content above
            strict_scan_area = fitz.Rect(w - 220, h - 40, w, h)
            detected_bbox, scanned_bg = scan_for_content_bbox(page, strict_scan_area)
            
            if detected_bbox:
                detection_source = "Visual Scan"
                # Note: 'scanned_bg' from scan_for_content_bbox is just the corner pixel.
                # We will ignore it in favor of the new 'dominant' calculator below.
                padding = 2
                target_rects = [fitz.Rect(
                    detected_bbox.x0 - padding,
                    detected_bbox.y0 - padding,
                    detected_bbox.x1 + padding,
                    detected_bbox.y1 + padding
                )]
            else:
                # If visual scan finds nothing, we assume page is clean.
                # We do NOT use a blind fallback box anymore as it causes damage.
                pass

        if not target_rects:
            continue
        
        # Execution
        redaction_applied = False
        print(f"  [Page {page_num+1}] Detected: {detection_source}.", end="")
        
        # Determine Fill Color using DOMINANT COLOR (Mode)
        # This is robust against text/lines in the corner area.
        fill_color = get_dominant_corner_color(page)
        print(" Masking with dominant corner color.")

        for rect in target_rects:
            page.add_redact_annot(rect, fill=fill_color)
            
        page.apply_redactions()
        pages_processed += 1

    try:
        doc.save(output_path)
        print(f"Success! Cleaned PDF saved to: '{output_path}'")
        print(f"Modified {pages_processed} pages.")
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
