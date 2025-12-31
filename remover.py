#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz  # PyMuPDF
import statistics
import argparse
import sys
import os
import math
from tqdm import tqdm

def hex_to_rgb(hex_str):
    """Convierte color hexadecimal a tupla RGB normalizada (0.0 - 1.0)."""
    if not hex_str: return None
    hex_str = hex_str.lstrip('#')
    try:
        return tuple(int(hex_str[i:i+2], 16)/255.0 for i in (0, 2, 4))
    except ValueError:
        return None

def get_dominant_corner_color(page):
    """Detecta el color de fondo más frecuente en la esquina inferior derecha."""
    try:
        w, h = page.rect.width, page.rect.height
        clip = fitz.Rect(w - 60, h - 30, w, h)
        pix = page.get_pixmap(clip=clip)
        if pix.width < 1 or pix.height < 1: return (1, 1, 1)
        
        counts = {}
        for y in range(pix.height):
            for x in range(pix.width):
                rgb = pix.pixel(x, y)
                counts[rgb] = counts.get(rgb, 0) + 1
        
        mode = max(counts, key=counts.get)
        return (mode[0]/255.0, mode[1]/255.0, mode[2]/255.0)
    except Exception:
        return (1, 1, 1)

def scan_for_content_bbox(page, search_rect):
    """Escanea píxeles para encontrar el área mínima exacta de la marca de agua."""
    try:
        pix = page.get_pixmap(clip=search_rect)
        if pix.width < 2: return None
        
        bg_r, bg_g, bg_b = pix.pixel(pix.width-1, pix.height-1)
        threshold = 50 # Umbral alto para ignorar ruido
        gap_limit = 8  # Brecha pequeña para no comerse objetos vecinos
        
        min_x, min_y, max_x, max_y = pix.width, pix.height, 0, 0
        found = False
        current_gap = 0
        
        # Escaneo de derecha a izquierda
        for x in range(pix.width - 1, -1, -1):
            col_has_content = False
            for y in range(pix.height):
                r, g, b = pix.pixel(x, y)
                if math.sqrt((r-bg_r)**2 + (g-bg_g)**2 + (b-bg_b)**2) > threshold:
                    col_has_content = True
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
            
            if col_has_content:
                found = True
                current_gap = 0
                if x < min_x: min_x = x
                if x > max_x: max_x = x
            elif found:
                current_gap += 1
                if current_gap > gap_limit: break
        
        if not found: return None
        return fitz.Rect(search_rect.x0 + min_x, search_rect.y0 + min_y, 
                         search_rect.x0 + max_x + 1, search_rect.y0 + max_y + 1)
    except Exception:
        return None

def detect_vector_watermark(page, search_rect):
    """Busca trazos vectoriales pequeños (letras convertidas a curvas)."""
    try:
        drawings = page.get_drawings()
        res = None
        for s in drawings:
            r = s["rect"]
            if r.intersects(search_rect) and r.width < 150 and r.height < 40:
                res = r if res is None else res | r
        return res
    except Exception: return None

def remove_watermark(input_path, output_path, preview=False, force_color=None):
    try:
        doc = fitz.open(input_path)
    except Exception as e:
        print(f"Error: {e}")
        return

    # Usar tqdm para la barra de progreso
    pbar = tqdm(enumerate(doc), total=len(doc), desc=f"Procesando {os.path.basename(input_path)}", unit="pág")
    
    for i, page in pbar:
        if preview and i > 0: break
        
        w, h = page.rect.width, page.rect.height
        search_area = fitz.Rect(w - 200, h - 60, w, h)
        
        # Estrategias adaptativas
        target = page.search_for("NotebookLM", clip=fitz.Rect(w/2, h/2, w, h))
        if target:
            target = [fitz.Rect(r.x0-2, r.y0-2, r.x1+2, r.y1+2) for r in target]
        else:
            v_box = detect_vector_watermark(page, search_area)
            if v_box:
                target = [fitz.Rect(v_box.x0-2, v_box.y0-2, v_box.x1+2, v_box.y1+2)]
            else:
                p_box = scan_for_content_bbox(page, fitz.Rect(w-200, h-30, w, h))
                target = [fitz.Rect(p_box.x0-2, p_box.y0-2, p_box.x1+2, p_box.y1+2)] if p_box else []

        if not target: continue
        
        fill = force_color if force_color else get_dominant_corner_color(page)
        for r in target:
            page.add_redact_annot(r, fill=fill)
        page.apply_redactions()

    doc.save(output_path)
    doc.close()

def main():
    parser = argparse.ArgumentParser(description="NotebookLM Watermark Remover")
    parser.add_argument("path", help="Archivo PDF o carpeta con PDFs")
    parser.add_argument("-o", "--output", help="Ruta de salida (solo modo un archivo)")
    parser.add_argument("--preview", action="store_true", help="Solo procesar la 1ra página")
    parser.add_argument("--color", help="Color manual (ej: #FFFFFF)")
    args = parser.parse_args()

    color = hex_to_rgb(args.color)
    tasks = []
    
    if os.path.isdir(args.path):
        tasks = [os.path.join(args.path, f) for f in os.listdir(args.path) if f.lower().endswith('.pdf')]
    elif os.path.isfile(args.path):
        tasks = [args.path]
    else:
        print("Ruta no válida.")
        return

    for t in tasks:
        out = args.output if (args.output and len(tasks)==1) else f"{os.path.splitext(t)[0]}_cleaned.pdf"
        remove_watermark(t, out, preview=args.preview, force_color=color)

if __name__ == "__main__":
    main()
