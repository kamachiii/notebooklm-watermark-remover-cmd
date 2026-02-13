#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
import argparse
import os
import math
import logging
import cv2
import numpy as np
from typing import Optional, Tuple, List, Union
from dataclasses import dataclass
from tqdm import tqdm
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class WatermarkConfig:
    """Configuration for watermark detection and removal."""
    # Search area: Reduced to be more surgical and avoid document content
    search_margin_x: int = 200
    search_margin_y: int = 50
    
    # Pixel scanning settings
    pixel_threshold: int = 30
    
    # Vector detection limits
    vector_max_width: int = 150
    vector_max_height: int = 40
    
    # Padding for the patch area
    patch_padding: int = 10
    
    # PDF Image Quality
    pdf_dpi_scale: float = 2.0 

    # Inpainting settings
    inpaint_radius: int = 3

class WatermarkRemover:
    def __init__(self, config: WatermarkConfig = WatermarkConfig()):
        self.config = config

    @staticmethod
    def hex_to_rgb(hex_str: Optional[str]) -> Optional[Tuple[float, float, float]]:
        """Converts hex color string to normalized RGB tuple (0.0 - 1.0)."""
        if not hex_str: return None
        hex_str = hex_str.lstrip('#')
        try:
            return tuple(int(hex_str[i:i+2], 16)/255.0 for i in (0, 2, 4))
        except ValueError: return None

    def _clean_image_array(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Core logic: Takes a BGR numpy array (image chunk), detects the watermark 
        using local contrast (blur difference), and inpaints it.
        """
        try:
            # 1. Median Blur to estimate 'background'
            # Reduced kernel size to be much more localized
            blurred = cv2.medianBlur(img_bgr, 7)
            
            # 2. Difference between Original and Blur
            diff = cv2.absdiff(img_bgr, blurred)
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            
            # 3. Threshold to get mask of text/sharp details
            # Increased threshold to be more selective (prevent capturing nearby content)
            _, mask = cv2.threshold(diff_gray, 50, 255, cv2.THRESH_BINARY)
            
            # 4. Filter Mask: Remove large continuous blobs that touch the left/top edge
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
            h, w = mask.shape
            
            new_mask = np.zeros_like(mask)
            
            for i in range(1, num_labels): # Skip background (0)
                x, y, stat_w, stat_h, area = stats[i]
                
                # Filter by size
                if stat_w > w * 0.8 or stat_h > h * 0.8:
                    continue
                # Filter by position: Protect anything in the left half of the search box
                # NotebookLM watermark is always far right.
                if x < w * 0.2:
                    continue
                # Protect anything touching the edges of the ROI (likely document content)
                if x == 0 or y == 0:
                    continue
                    
                new_mask[labels == i] = 255
            
            mask = new_mask
            
            # 5. Dilate to cover anti-aliasing artifacts and shadows
            # Reduced iterations to prevent 'bleeding' into nearby slide content
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.dilate(mask, kernel, iterations=1)
            
            if cv2.countNonZero(mask) == 0:
                return img_bgr

            # 6. Inpaint
            # Switched to TELEA as it handles small spot removal with fewer artifacts than NS
            cleaned = cv2.inpaint(img_bgr, mask, self.config.inpaint_radius, cv2.INPAINT_TELEA)
            
            return cleaned
        except Exception as e:
            logger.warning(f"Inpainting failed: {e}")
            return img_bgr

    # --- PDF Processing Methods ---

    def process_pdf(self, input_path: str, output_path: str, preview: bool = False) -> bool:
        """
        Processes a PDF by 'patching' the watermark area.
        Instead of a solid color, it rasterizes the corner, cleans it with AI/Inpainting,
        and pastes it back over the original watermark.
        """
        try:
            doc = fitz.open(input_path)
        except Exception as e:
            logger.error(f"Could not open file {input_path}: {e}")
            return False

        filename = os.path.basename(input_path)
        pbar = tqdm(enumerate(doc), total=len(doc), desc=f"Processing {filename} (PDF)", unit="page")
        
        pages_modified = 0

        for i, page in pbar:
            if preview and i > 0: break
            
            w, h = page.rect.width, page.rect.height
            
            # Define search area (bottom right corner)
            x0 = w - self.config.search_margin_x
            y0 = h - self.config.search_margin_y
            
            if x0 < 0: x0 = 0
            if y0 < 0: y0 = 0
            
            search_rect = fitz.Rect(x0, y0, w, h)
            
            # Heuristic check to skip clean pages
            has_watermark = False
            if page.search_for("NotebookLM", clip=search_rect):
                has_watermark = True
            else:
                drawings = page.get_drawings()
                for s in drawings:
                    if s["rect"].intersects(search_rect) and s["rect"].width < 150:
                        has_watermark = True
                        break
            
            # Always attempt patch if heuristic matches, or we could force it.
            # Given the improved "smart" cleaning which ignores non-watermark content,
            # we can be aggressive.
            
            # 1. Capture high-res image of the corner
            mat = fitz.Matrix(self.config.pdf_dpi_scale, self.config.pdf_dpi_scale)
            pix = page.get_pixmap(clip=search_rect, matrix=mat)
            
            img_data = np.frombuffer(pix.samples, dtype=np.uint8)
            
            if pix.n == 4:
                img_data = img_data.reshape(pix.h, pix.w, 4)
                img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_data = img_data.reshape(pix.h, pix.w, 3)
                img_bgr = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            else:
                continue

            cleaned_bgr = self._clean_image_array(img_bgr)
            
            cleaned_rgb = cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cleaned_rgb)
            
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            page.insert_image(search_rect, stream=img_bytes)
            pages_modified += 1

        try:
            doc.save(output_path, garbage=3, deflate=True, clean=True)
            doc.close()
            logger.info(f"Saved {output_path} ({pages_modified} pages patched)")
            return True
        except Exception as e:
            logger.error(f"Error saving PDF {output_path}: {e}")
            return False

    # --- Image Processing Methods ---

    def process_image(self, input_path: str, output_path: str) -> bool:
        """Processes an image using Gradient-Aware Inpainting, preserving Alpha."""
        try:
            # Load with Alpha if present
            img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                return False

            h, w = img.shape[:2]
            
            # Handle Alpha Channel
            has_alpha = False
            if len(img.shape) == 3 and img.shape[2] == 4:
                has_alpha = True
                b, g, r, a = cv2.split(img)
                img_bgr = cv2.merge([b, g, r])
            else:
                img_bgr = img

            # ROI: Bottom Right
            margin_x = self.config.search_margin_x
            margin_y = self.config.search_margin_y
            x_start = max(0, w - margin_x)
            y_start = max(0, h - margin_y)
            
            roi_bgr = img_bgr[y_start:h, x_start:w]
            
            # Clean ROI
            cleaned_roi = self._clean_image_array(roi_bgr)
            
            # Restore
            img_bgr[y_start:h, x_start:w] = cleaned_roi
            
            # Merge Alpha back if needed
            if has_alpha:
                img_final = cv2.merge([*cv2.split(img_bgr), a])
            else:
                img_final = img_bgr
            
            cv2.imwrite(output_path, img_final)
            logger.info(f"Saved cleaned image to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error processing image {input_path}: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="NotebookLM Watermark Remover (Smart Inpainting)")
    parser.add_argument("path", help="File (PDF/PNG/JPG) or directory")
    parser.add_argument("-o", "--output", help="Output path")
    parser.add_argument("--preview", action="store_true", help="Process only first page (PDF only)")
    parser.add_argument("--margin-x", type=int, default=None,
                        help="Search margin width in px from right edge (default: 350). "
                             "Reduce to ~150 if slide content near the corner gets damaged.")
    parser.add_argument("--margin-y", type=int, default=None,
                        help="Search margin height in px from bottom edge (default: 70). "
                             "Reduce to ~35 if slide content near the corner gets damaged.")

    args = parser.parse_args()
    config = WatermarkConfig()
    if args.margin_x is not None:
        config.search_margin_x = args.margin_x
    if args.margin_y is not None:
        config.search_margin_y = args.margin_y
    remover = WatermarkRemover(config)
    
    tasks = []
    supported_exts = ('.pdf', '.png', '.jpg', '.jpeg', '.webp')
    
    if os.path.isdir(args.path):
        files = sorted([f for f in os.listdir(args.path) if f.lower().endswith(supported_exts)])
        tasks = [os.path.join(args.path, f) for f in files]
        logger.info(f"Found {len(tasks)} supported files.")
    elif os.path.isfile(args.path) and args.path.lower().endswith(supported_exts):
        tasks = [args.path]
    else:
        logger.error("Invalid path.")
        return

    for input_path in tasks:
        ext = os.path.splitext(input_path)[1].lower()
        if args.output and len(tasks) == 1:
            out_path = args.output
        else:
            base, _ = os.path.splitext(input_path)
            out_path = f"{base}_cleaned{ext}"
            
        if ext == '.pdf':
            remover.process_pdf(input_path, out_path, preview=args.preview)
        else:
            remover.process_image(input_path, out_path)

if __name__ == "__main__":
    main()
