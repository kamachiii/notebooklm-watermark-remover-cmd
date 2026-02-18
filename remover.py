#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
import argparse
import os
import logging
import cv2
import numpy as np
from typing import Optional
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
    # Padding around detected watermark area (PDF points / pixels)
    watermark_padding: int = 20

    # Fallback search margins for image-based detection (px from corner edges)
    search_margin_x: int = 300
    search_margin_y: int = 65

    # Threshold for median-blur difference detection
    pixel_threshold: int = 30

    # PDF rendering scale factor (higher = better quality but slower)
    pdf_dpi_scale: float = 3.0

    # Inpainting radius for cv2.inpaint
    inpaint_radius: int = 5

    # Minimum text-like components to consider a region as containing a watermark
    min_watermark_components: int = 2

    # Minimum total area (px) of detected components to confirm a watermark
    min_watermark_area: int = 200


class WatermarkRemover:
    """Removes NotebookLM watermarks from PDFs and images."""

    WATERMARK_TEXT = "NotebookLM"

    def __init__(self, config: WatermarkConfig = WatermarkConfig()):
        self.config = config

    # ------------------------------------------------------------------ #
    #  Core inpainting                                                     #
    # ------------------------------------------------------------------ #

    def _clean_image_array(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Detects non-background sharp elements (watermark text / icon) in a BGR
        image and removes them via inpainting.  The ROI should be tightly focused
        on the watermark area so that most sharp elements ARE the watermark.
        """
        try:
            h, w = img_bgr.shape[:2]
            if h < 5 or w < 5:
                return img_bgr

            # 1. Adaptive median-blur kernel for background estimation
            ksize = max(11, min(31, (min(h, w) // 6) | 1))  # always odd
            background = cv2.medianBlur(img_bgr, ksize)

            # 2. Difference highlights sharp features (text, edges) vs smooth bg
            diff = cv2.absdiff(img_bgr, background)
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

            # 3. Threshold with config value
            _, mask = cv2.threshold(
                diff_gray, self.config.pixel_threshold, 255, cv2.THRESH_BINARY
            )

            # 4. Connected-component shape filtering
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                mask, connectivity=8
            )
            filtered = np.zeros_like(mask)

            for i in range(1, num_labels):
                _, _, cw, ch, area = stats[i]
                # Skip tiny noise
                if area < 3:
                    continue
                # Skip very large blobs (document content, not watermark)
                if cw > w * 0.7 or ch > h * 0.8:
                    continue
                # Skip extremely thin horizontal / vertical lines (borders)
                if cw > 0 and ch > 0:
                    aspect = cw / float(ch)
                    if aspect > 10.0 or aspect < 0.1:
                        continue
                filtered[labels == i] = 255

            # 5. Dilate to cover anti-aliased edges of watermark text
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            filtered = cv2.dilate(filtered, kernel, iterations=3)

            if cv2.countNonZero(filtered) == 0:
                return img_bgr

            # 6. Inpaint with configured radius
            return cv2.inpaint(
                img_bgr, filtered, self.config.inpaint_radius, cv2.INPAINT_TELEA
            )

        except Exception as e:
            logger.warning(f"Inpainting failed: {e}")
            return img_bgr

    # ------------------------------------------------------------------ #
    #  PDF processing                                                      #
    # ------------------------------------------------------------------ #

    def _find_watermark_rect_text(self, page: fitz.Page) -> Optional[fitz.Rect]:
        """
        Tries to locate the watermark via searchable text ("NotebookLM").
        Works for PDFs where the watermark is real text rather than rasterised.
        Returns a padded Rect or None.
        """
        w, h = page.rect.width, page.rect.height
        instances = page.search_for(self.WATERMARK_TEXT)
        if not instances:
            return None

        best: Optional[fitz.Rect] = None
        best_score = float('inf')

        for rect in instances:
            cy = (rect.y0 + rect.y1) / 2
            cx = (rect.x0 + rect.x1) / 2
            if cy < h * 0.80:
                continue
            if rect.width > 250 or rect.height > 40:
                continue
            dist = abs(w - cx) + abs(h - cy)  # distance to bottom-right
            if dist < best_score:
                best_score = dist
                best = rect

        if best is None:
            return None

        wm_rect = fitz.Rect(best)

        # Expand to include the icon to the LEFT of the text
        icon_search = fitz.Rect(
            best.x0 - 80, best.y0 - 15,
            best.x0 + 5,  best.y1 + 15,
        )
        try:
            for d in page.get_drawings():
                if d["rect"].intersects(icon_search):
                    wm_rect = wm_rect | d["rect"]
        except Exception:
            pass
        try:
            for img_info in page.get_images(full=True):
                for ir in page.get_image_rects(img_info[0]):
                    if ir.intersects(icon_search):
                        wm_rect = wm_rect | ir
        except Exception:
            pass

        wm_rect.x0 = min(wm_rect.x0, best.x0 - 45)
        pad = self.config.watermark_padding
        return fitz.Rect(
            max(0, wm_rect.x0 - pad),
            max(0, wm_rect.y0 - pad),
            min(w, wm_rect.x1 + pad),
            min(h, wm_rect.y1 + pad),
        )

    def _get_fallback_corner_rect(self, page: fitz.Page) -> fitz.Rect:
        """
        Returns the bottom-right corner rectangle for pixel-based watermark
        detection.  Used when text search finds nothing (raster-only pages).
        """
        w, h = page.rect.width, page.rect.height
        mx = self.config.search_margin_x
        my = self.config.search_margin_y
        return fitz.Rect(
            max(0, w - mx),
            max(0, h - my),
            w, h,
        )

    def _pixmap_to_bgr(self, pix: fitz.Pixmap) -> Optional[np.ndarray]:
        """Convert a PyMuPDF Pixmap to a BGR numpy array."""
        img_data = np.frombuffer(pix.samples, dtype=np.uint8)
        if pix.n == 4:
            return cv2.cvtColor(
                img_data.reshape(pix.h, pix.w, 4), cv2.COLOR_RGBA2BGR
            )
        elif pix.n == 3:
            return cv2.cvtColor(
                img_data.reshape(pix.h, pix.w, 3), cv2.COLOR_RGB2BGR
            )
        return None

    def _patch_rect(self, page: fitz.Page, rect: fitz.Rect) -> bool:
        """
        Rasterise *rect* at high DPI, run inpainting, and paste the cleaned
        image back over the same area.  Returns True on success.
        """
        mat = fitz.Matrix(self.config.pdf_dpi_scale, self.config.pdf_dpi_scale)
        pix = page.get_pixmap(clip=rect, matrix=mat)
        img_bgr = self._pixmap_to_bgr(pix)
        if img_bgr is None:
            return False

        cleaned = self._clean_image_array(img_bgr)
        cleaned_rgb = cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB)
        buf = io.BytesIO()
        Image.fromarray(cleaned_rgb).save(buf, format='PNG')
        page.insert_image(rect, stream=buf.getvalue())
        return True

    def process_pdf(self, input_path: str, output_path: str, preview: bool = False) -> bool:
        """
        For each page:
          1. Try to find the watermark via text search (vector-text PDFs).
          2. If no text found, fall back to pixel-based detection on the
             bottom-right corner (raster-only PDFs, which is the most common
             output format of NotebookLM).
        Pages with no detected watermark are left untouched.
        """
        try:
            doc = fitz.open(input_path)
        except Exception as e:
            logger.error(f"Could not open {input_path}: {e}")
            return False

        filename = os.path.basename(input_path)
        pbar = tqdm(
            enumerate(doc), total=len(doc),
            desc=f"Processing {filename}", unit="page",
        )
        patched = 0
        skipped = 0

        for i, page in pbar:
            if preview and i > 0:
                break

            # --- Strategy 1: text-based detection ---
            wm_rect = self._find_watermark_rect_text(page)
            if wm_rect is not None:
                if self._patch_rect(page, wm_rect):
                    patched += 1
                    pbar.set_postfix(patched=patched, skipped=skipped)
                    continue

            # --- Strategy 2: pixel-based fallback (raster-only pages) ---
            corner = self._get_fallback_corner_rect(page)
            mat = fitz.Matrix(self.config.pdf_dpi_scale, self.config.pdf_dpi_scale)
            pix = page.get_pixmap(clip=corner, matrix=mat)
            roi_bgr = self._pixmap_to_bgr(pix)

            if roi_bgr is not None and self._has_watermark_in_roi(roi_bgr):
                if self._patch_rect(page, corner):
                    patched += 1
                    pbar.set_postfix(patched=patched, skipped=skipped)
                    continue

            skipped += 1
            pbar.set_postfix(patched=patched, skipped=skipped)

        try:
            doc.save(output_path, garbage=3, deflate=True, clean=True)
            doc.close()
            logger.info(
                f"Saved {output_path} ({patched} pages patched, {skipped} skipped)"
            )
            return True
        except Exception as e:
            logger.error(f"Error saving {output_path}: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Image processing                                                    #
    # ------------------------------------------------------------------ #

    def _has_watermark_in_roi(self, roi_bgr: np.ndarray) -> bool:
        """
        Heuristic check: returns True if a corner ROI contains components
        consistent with the NotebookLM watermark (icon + text blob).
        Requires at least *min_watermark_components* valid components AND
        a minimum total area to avoid false positives from noise.
        """
        h, w = roi_bgr.shape[:2]
        if h < 5 or w < 5:
            return False

        ksize = max(11, min(31, (min(h, w) // 6) | 1))
        background = cv2.medianBlur(roi_bgr, ksize)
        diff_gray = cv2.cvtColor(
            cv2.absdiff(roi_bgr, background), cv2.COLOR_BGR2GRAY
        )
        _, mask = cv2.threshold(
            diff_gray, self.config.pixel_threshold, 255, cv2.THRESH_BINARY
        )

        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )

        count = 0
        total_area = 0
        for i in range(1, num_labels):
            _, _, cw, ch, area = stats[i]
            if area < 3 or cw > w * 0.7 or ch > h * 0.8:
                continue
            if cw > 0 and ch > 0:
                aspect = cw / float(ch)
                if aspect > 10.0 or aspect < 0.1:
                    continue
            count += 1
            total_area += area

        return (
            count >= self.config.min_watermark_components
            and total_area >= self.config.min_watermark_area
        )

    def process_image(self, input_path: str, output_path: str) -> bool:
        """
        Searches the bottom-right corner of an image for the NotebookLM
        watermark and removes it.  Preserves the alpha channel for PNGs.
        """
        try:
            img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                logger.error(f"Could not read: {input_path}")
                return False

            h, w = img.shape[:2]
            has_alpha = len(img.shape) == 3 and img.shape[2] == 4

            if has_alpha:
                channels = cv2.split(img)
                img_bgr = cv2.merge(channels[:3])
                alpha = channels[3]
            else:
                img_bgr = img.copy()
                alpha = None

            mx = self.config.search_margin_x
            my = self.config.search_margin_y
            y0 = max(0, h - my)
            x0 = max(0, w - mx)

            # --- Bottom-RIGHT corner ---
            roi = img_bgr[y0:h, x0:w].copy()
            modified = self._has_watermark_in_roi(roi)

            if modified:
                img_bgr[y0:h, x0:w] = self._clean_image_array(roi)
                logger.info("Cleaned watermark in bottom-right corner")

            if not modified:
                logger.warning(
                    f"No watermark detected in {input_path} — file not modified."
                )
                return False

            if has_alpha:
                img_final = cv2.merge([*cv2.split(img_bgr), alpha])
            else:
                img_final = img_bgr

            cv2.imwrite(output_path, img_final)
            logger.info(f"Saved cleaned image to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error processing {input_path}: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="NotebookLM Watermark Remover (Smart Inpainting)"
    )
    parser.add_argument("path", help="File (PDF/PNG/JPG) or directory")
    parser.add_argument("-o", "--output", help="Output path")
    parser.add_argument(
        "--preview", action="store_true",
        help="Process only first page (PDF only)",
    )
    parser.add_argument(
        "--margin-x", type=int, default=None,
        help="Search margin width in px from right edge (default: 300). "
             "Controls the size of the bottom-right corner region to scan.",
    )
    parser.add_argument(
        '--margin-y', type=int, default=None,
        help="Search margin height in px from bottom edge (default: 65). "
             "Controls the size of the bottom-right corner region to scan.",
    )

    args = parser.parse_args()
    config = WatermarkConfig()

    if args.margin_x is not None:
        config.search_margin_x = args.margin_x
    if args.margin_y is not None:
        config.search_margin_y = args.margin_y

    remover = WatermarkRemover(config)

    supported = ('.pdf', '.png', '.jpg', '.jpeg', '.webp')

    if os.path.isdir(args.path):
        tasks = sorted([
            os.path.join(args.path, f)
            for f in os.listdir(args.path)
            if f.lower().endswith(supported)
        ])
        logger.info(f"Found {len(tasks)} supported files.")
    elif os.path.isfile(args.path) and args.path.lower().endswith(supported):
        tasks = [args.path]
    else:
        logger.error("Invalid path or unsupported format.")
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
