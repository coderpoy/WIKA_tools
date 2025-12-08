#!/usr/bin/env python3
"""
ocr_extract.py

Usage:
  python ocr_extract.py input_image.png output.json

What it does (prototype):
 - Preprocess the image (grayscale, blur, adaptive threshold)
 - Attempt to find the largest rectangular contour (assumed part outline)
 - Run pytesseract to extract text boxes
 - Parse common dimension patterns:
     - LxW, L x W x H, L×W×H
     - single numbers with units (e.g., 100 mm)
     - hole annotations like "Ø6", "ø6", "phi6", "DIA 6"
 - Estimate hole positions by mapping text bbox centers into part coordinates
 - Writes a JSON describing a box part with holes: name, type, length,width,height, units, holes[]

Limitations: heuristics only. Review JSON before 3D generation.
"""
import sys
import json
import re
import cv2
import numpy as np
import pytesseract
from pytesseract import Output

# ---------------------
# helpers / regex
# ---------------------
DIM_SEP_PATTERN = re.compile(r'[\sx×X*:,]+')  # separators between dims
FLOAT_RE = r'[-+]?\d*\.\d+|\d+'
UNIT_RE = r'(mm|cm|m|in|")?'
# examples: "100x50x25 mm" or "100 × 50 × 25"
TRIPLE_DIM_RE = re.compile(rf'({FLOAT_RE})\s*[x×X,]\s*({FLOAT_RE})\s*[x××X,]\s*({FLOAT_RE})\s*{UNIT_RE}', re.IGNORECASE)
DOUBLE_DIM_RE = re.compile(rf'({FLOAT_RE})\s*[x×X,]\s*({FLOAT_RE})\s*{UNIT_RE}', re.IGNORECASE)
SINGLE_DIM_RE = re.compile(rf'({FLOAT_RE})\s*{UNIT_RE}', re.IGNORECASE)
HOLE_RE = re.compile(r'(?:Ø|ø|phi|phi:|DIA|dia|φ)\s*({FLOAT_RE})', re.IGNORECASE)

# ---------------------
# image preprocessing
# ---------------------
def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # adaptive threshold to handle various backgrounds
    blur = cv2.GaussianBlur(gray, (3,3), 0)
    th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 25, 10)
    return gray, th

def find_largest_rect(thresh):
    # find contours and choose the largest quadrilateral-like contour
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_area = 0
    for c in contours:
        area = cv2.contourArea(c)
        if area < 1000:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) >= 4 and area > best_area:
            best = approx
            best_area = area
    if best is None:
        return None
    # return bounding rect (x,y,w,h)
    x, y, w, h = cv2.boundingRect(best)
    return (x, y, w, h)

# ---------------------
# OCR + parse
# ---------------------
def ocr_with_boxes(img):
    # use pytesseract to get boxes
    d = pytesseract.image_to_data(img, output_type=Output.DICT)
    boxes = []
    n = len(d['text'])
    for i in range(n):
        text = d['text'][i].strip()
        if text == '':
            continue
        conf = int(d['conf'][i]) if d['conf'][i].isdigit() else -1
        x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
        boxes.append({'text': text, 'conf': conf, 'bbox': [x,y,w,h]})
    return boxes

def parse_dimensions_from_text(boxes, part_bbox=None):
    """
    Returns a dict: { type: 'box', length, width, height(optional), units, holes: [ {r, x_rel, y_rel } ] }
    Coordinates x_rel,y_rel are in 0..1 relative to part bounding box if available, else pixel coords.
    """
    result = {'type':'box', 'units':'mm', 'holes':[]}
    # join all texts to try to find combined dims like "100x50x25 mm"
    all_text = ' '.join(b['text'] for b in boxes)
    m = TRIPLE_DIM_RE.search(all_text)
    if m:
        l, w, h, u = m.group(1), m.group(2), m.group(3), m.group(4)
        result.update({'length':float(l), 'width':float(w), 'height':float(h)})
        if u: result['units'] = u.lower()
    else:
        # try to find double dims (L x W) and single dim for H maybe on separate box
        m2 = DOUBLE_DIM_RE.search(all_text)
        if m2:
            l, w, u = m2.group(1), m2.group(2), m2.group(3)
            result.update({'length':float(l), 'width':float(w)})
            if u: result['units'] = u.lower()
        # try single dims (maybe height)
        singles = SINGLE_DIM_RE.findall(all_text)
        # map the largest three numbers heuristically to L,W,H
        nums = [float(s[0]) for s in singles]
        if 'length' not in result and nums:
            result['length'] = nums[0]
        if 'width' not in result and len(nums) > 1:
            result['width'] = nums[1]
        if 'height' not in result and len(nums) > 2:
            result['height'] = nums[2]
    # find hole specs
    for b in boxes:
        t = b['text']
        mm = HOLE_RE.search(t)
        if mm:
            r = float(mm.group(1))
            # estimate location: use bbox center; map to relative coords if part_bbox present
            x, y, w, h = b['bbox']
            cx = x + w/2
            cy = y + h/2
            if part_bbox:
                px, py, pw, ph = part_bbox
                rx = (cx - px) / max(1.0, pw)
                ry = (cy - py) / max(1.0, ph)
            else:
                rx, ry = cx, cy
            # treat r as diameter if likely; if small compared to text height maybe radius; keep as diameter interpretation typical in drawings
            result['holes'].append({'diameter': r, 'x_rel': rx, 'y_rel': ry})
    return result

# ---------------------
# main
# ---------------------
def main():
    if len(sys.argv) < 3:
        print("Usage: python ocr_extract.py input.png output.json")
        sys.exit(1)
    img_path = sys.argv[1]
    out_json = sys.argv[2]
    img = cv2.imread(img_path)
    if img is None:
        print("Failed to load image:", img_path); sys.exit(2)
    gray, th = preprocess(img)
    part_bbox = find_largest_rect(th)
    boxes = ocr_with_boxes(img)
    parsed = parse_dimensions_from_text(boxes, part_bbox)
    # if we have part bbox, convert relative hole coords to dimension units (approx)
    # but we need scale: if length/width are provided, we can map rel coords to units
    if part_bbox and 'length' in parsed and 'width' in parsed:
        px, py, pw, ph = part_bbox
        for h in parsed['holes']:
            if isinstance(h['x_rel'], float) and 0 <= h['x_rel'] <= 1:
                h['x_mm'] = h['x_rel'] * parsed['length']
            else:
                # fallback: map using pixels and part bbox pixels
                h['x_mm'] = (h['x_rel'] - px) * parsed.get('length', 0) / pw if pw else 0
            if isinstance(h['y_rel'], float) and 0 <= h['y_rel'] <= 1:
                h['y_mm'] = (1.0 - h['y_rel']) * parsed['width']  # invert Y so origin at bottom-left
            else:
                h['y_mm'] = 0
    # Add bounding info for human review
    out = {'source_image': img_path, 'part_bbox': part_bbox, 'parsed': parsed}
    with open(out_json, 'w') as f:
        json.dump(out, f, indent=2)
    print("Wrote:", out_json)
    print("Parsed result (summary):")
    print(json.dumps(parsed, indent=2))

if __name__ == '__main__':
    main()