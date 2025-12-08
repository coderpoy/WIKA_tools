#!/usr/bin/env python3
"""
freecad_build.py

Usage:
  - Headless (if FreeCADCmd is available):
      FreeCADCmd freecad_build.py parts.json out.step
  - Or run inside FreeCAD's Python console:
      exec(open('freecad_build.py').read()); build_from_json('parts.json', 'out.step')

This script reads the JSON produced by ocr_extract.py and builds a simple box with holes,
then exports a STEP file.

Expected input JSON structure (parts.json):
{
  "parsed": {
    "type": "box",
    "length": 100,
    "width": 50,
    "height": 25,
    "units": "mm",
    "holes": [
      {"diameter":6, "x_mm": 10, "y_mm":20}
    ]
  }
}
"""
import sys
import json
import os

def build_from_json(json_path, out_step):
    # Import FreeCAD modules. When run with FreeCADCmd these are available on sys.path.
    try:
        import FreeCAD as App
        import Part
    except Exception as e:
        print("FreeCAD modules not available. Run this with FreeCADCmd or inside FreeCAD.")
        raise

    with open(json_path, 'r') as f:
        data = json.load(f)
    parsed = data.get('parsed', {})
    if parsed.get('type') != 'box':
        raise ValueError("Only 'box' type supported in this script.")

    L = float(parsed.get('length', 100))
    W = float(parsed.get('width', 50))
    H = float(parsed.get('height', 10))

    # Create a box with origin at (0,0,0) - then we'll center it
    box_shape = Part.makeBox(L, W, H)
    # center it about origin if desired: translate by -L/2, -W/2, -H/2
    box_shape.translate(App.Vector(-L/2.0, -W/2.0, -H/2.0))

    # Apply holes (through holes along Z)
    holes = parsed.get('holes', [])
    compound = box_shape
    cuts = []
    for h in holes:
        dia = float(h.get('diameter', h.get('radius', 5)))
        # position: expect x_mm, y_mm in mm coordinates measured from left-bottom of part
        x = float(h.get('x_mm', h.get('x_rel', 0)))
        y = float(h.get('y_mm', h.get('y_rel', 0)))
        # if x_rel given as fraction 0..1 map to L,W
        if 0 <= x <= 1 and 'length' in parsed:
            x = x * parsed['length'] - L/2.0
        else:
            x = x - L/2.0
        if 0 <= y <= 1 and 'width' in parsed:
            y = y * parsed['width'] - W/2.0
        else:
            y = y - W/2.0
        # create cylinder tall enough to cut through
        cyl = Part.makeCylinder(dia/2.0, H*2.0)
        # position cylinder so it goes through part center in Z
        cyl.translate(App.Vector(x, y, -H))
        cuts.append(cyl)
    # perform cuts
    for c in cuts:
        try:
            compound = compound.cut(c)
        except Exception as e:
            print("Cut failed:", e)
    # export STEP
    # Part.export accepts a list of FreeCAD shapes/objects
    Part.show(compound)  # ensure object exists in doc when running inside GUI
    Part.export([compound], out_step)
    print("Exported STEP:", out_step)

def main():
    if len(sys.argv) < 3:
        print("Usage: FreeCADCmd freecad_build.py parts.json out.step")
        sys.exit(1)
    json_path = sys.argv[1]
    out_step = sys.argv[2]
    build_from_json(json_path, out_step)

if __name__ == '__main__':
    main()