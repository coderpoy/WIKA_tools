#!/usr/bin/env python3

# Right Triangle Simulator with GUI

# - Visualizes a right triangle (sides a, b, hypotenuse c) and angle theta (at the right-angle vertex's corner).
# - Lets you provide any combination of inputs (a, b, c, theta). The program will compute the remaining values
#   using the Pythagorean theorem and trigonometric relations.
# - If the provided inputs are insufficient to determine a unique triangle, reasonable defaults/assumptions are used:
#     * If only theta is provided -> uses a default hypotenuse (configurable) to set scale.
#     * If only one side (a, b, or c) is provided -> assumes theta = 45° (isosceles right triangle) by default.
#       You can change the default assumption in the GUI.
# - Validates impossible inputs and shows errors.

# Run:
#     python3 triangle_simulator.py

import math
import tkinter as tk
from tkinter import ttk, messagebox

# --- Configuration defaults ---
CANVAS_WIDTH = 600
CANVAS_HEIGHT = 400
MARGIN = 40
DEFAULT_HYPOTENUSE_IF_THETA_ONLY = 200.0
DEFAULT_THETA_IF_SINGLE_SIDE = 45.0  # degrees

# --- Helper math functions ---

def deg_to_rad(d):
    return d * math.pi / 180.0

def rad_to_deg(r):
    return r * 180.0 / math.pi

def is_filled(s):
    return s is not None and s != ""

# --- Solver logic ---

def compute_from_inputs(a_in, b_in, c_in, theta_in_deg, assume_theta_for_single_side=None, scale_for_theta_only=None):
    """
    Given inputs (strings or None), try to compute all values (a, b, c, theta_deg).
    - Returns tuple (a, b, c, theta_deg, note)
    - Raises ValueError on impossible combos.
    Notes:
      - a = adjacent to theta
      - b = opposite to theta
      - c = hypotenuse
      - theta is angle at the right-angle vertex between side a and hypotenuse (so cos = a/c, sin = b/c)
    """
    # Parse inputs (allow blank)
    def parse(val):
        if val is None or val == "":
            return None
        return float(val)

    a = parse(a_in)
    b = parse(b_in)
    c = parse(c_in)
    theta_deg = parse(theta_in_deg)
    note = ""

    provided = sum(1 for v in (a, b, c, theta_deg) if v is not None)

    # Convert angle to rad if present
    theta = None
    if theta_deg is not None:
        theta = deg_to_rad(theta_deg)

    # Solve cases with 2+ provided (unique except some degenerate)
    try:
        if provided >= 2:
            # Try combinations in a priority order
            if a is not None and b is not None:
                if a < 0 or b < 0:
                    raise ValueError("Side lengths must be non-negative.")
                c = math.hypot(a, b)
                theta = math.atan2(b, a)
            elif a is not None and c is not None:
                if a < 0 or c <= 0:
                    raise ValueError("Sides must be positive.")
                if a > c:
                    raise ValueError("Hypotenuse c must be >= leg a.")
                b_sq = c * c - a * a
                if b_sq < -1e-9:
                    raise ValueError("Invalid sides: c^2 - a^2 < 0.")
                b = math.sqrt(max(0.0, b_sq))
                theta = math.acos(a / c)
            elif b is not None and c is not None:
                if b < 0 or c <= 0:
                    raise ValueError("Sides must be positive.")
                if b > c:
                    raise ValueError("Hypotenuse c must be >= leg b.")
                a_sq = c * c - b * b
                if a_sq < -1e-9:
                    raise ValueError("Invalid sides: c^2 - b^2 < 0.")
                a = math.sqrt(max(0.0, a_sq))
                theta = math.asin(b / c)
            elif a is not None and theta is not None:
                if a < 0:
                    raise ValueError("Side a must be non-negative.")
                if abs(math.cos(theta)) < 1e-12:
                    raise ValueError("Cos(theta) is zero; cannot determine c from a.")
                c = a / math.cos(theta)
                if c <= 0:
                    raise ValueError("Computed hypotenuse is not positive.")
                b = a * math.tan(theta)
            elif b is not None and theta is not None:
                if b < 0:
                    raise ValueError("Side b must be non-negative.")
                if abs(math.sin(theta)) < 1e-12:
                    raise ValueError("Sin(theta) is zero; cannot determine c from b.")
                c = b / math.sin(theta)
                if c <= 0:
                    raise ValueError("Computed hypotenuse is not positive.")
                a = b / math.tan(theta)
            elif c is not None and theta is not None:
                if c <= 0:
                    raise ValueError("Hypotenuse must be positive.")
                a = c * math.cos(theta)
                b = c * math.sin(theta)
            else:
                raise ValueError("Unsupported combination.")
        else:
            # Only one input given -> use assumptions
            if theta is not None:
                # Only theta provided -> choose scale_for_theta_only for hypotenuse by default
                if scale_for_theta_only is None:
                    scale_for_theta_only = DEFAULT_HYPOTENUSE_IF_THETA_ONLY
                if scale_for_theta_only <= 0:
                    raise ValueError("Scale/hypotenuse must be positive.")
                c = scale_for_theta_only
                a = c * math.cos(theta)
                b = c * math.sin(theta)
                note = f"Only theta provided. Assumed hypotenuse c = {scale_for_theta_only} for scale."
            elif a is not None:
                # Only a provided -> assume theta default
                if assume_theta_for_single_side is None:
                    assume_theta_for_single_side = DEFAULT_THETA_IF_SINGLE_SIDE
                theta = deg_to_rad(assume_theta_for_single_side)
                c = a / math.cos(theta)
                b = a * math.tan(theta)
                theta_deg = assume_theta_for_single_side
                note = f"Only side a provided. Assumed theta = {assume_theta_for_single_side}°."
            elif b is not None:
                if assume_theta_for_single_side is None:
                    assume_theta_for_single_side = DEFAULT_THETA_IF_SINGLE_SIDE
                theta = deg_to_rad(assume_theta_for_single_side)
                c = b / math.sin(theta)
                a = b / math.tan(theta)
                theta_deg = assume_theta_for_single_side
                note = f"Only side b provided. Assumed theta = {assume_theta_for_single_side}°."
            elif c is not None:
                if assume_theta_for_single_side is None:
                    assume_theta_for_single_side = DEFAULT_THETA_IF_SINGLE_SIDE
                theta = deg_to_rad(assume_theta_for_single_side)
                a = c * math.cos(theta)
                b = c * math.sin(theta)
                theta_deg = assume_theta_for_single_side
                note = f"Only hypotenuse c provided. Assumed theta = {assume_theta_for_single_side}°."
            else:
                raise ValueError("No input provided.")
    except ValueError:
        raise

    # Final checks and conversion back
    if theta is None:
        raise ValueError("Unable to determine angle theta.")

    if theta_deg is None:
        theta_deg = rad_to_deg(theta)

    # enforce non-negative small values
    a = 0.0 if a is not None and abs(a) < 1e-12 else a
    b = 0.0 if b is not None and abs(b) < 1e-12 else b
    c = 0.0 if c is not None and abs(c) < 1e-12 else c

    # sanity
    if c is not None and (a is None or b is None):
        raise ValueError("Computation incomplete.")

    return a, b, c, theta_deg, note


# --- GUI ---

class RightTriangleSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Right Triangle Simulator")
        self.resizable(False, False)

        # Main frames
        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky="n")
        right = ttk.Frame(self, padding=10)
        right.grid(row=0, column=1, sticky="n")

        # Input fields
        ttk.Label(left, text="Enter any known values (leave blank if unknown):").grid(row=0, column=0, columnspan=3, pady=(0, 8), sticky="w")

        ttk.Label(left, text="Side a (adjacent)").grid(row=1, column=0, sticky="w")
        self.a_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.a_var, width=15).grid(row=1, column=1, sticky="w")

        ttk.Label(left, text="Side b (opposite)").grid(row=2, column=0, sticky="w")
        self.b_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.b_var, width=15).grid(row=2, column=1, sticky="w")

        ttk.Label(left, text="Hypotenuse c").grid(row=3, column=0, sticky="w")
        self.c_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.c_var, width=15).grid(row=3, column=1, sticky="w")

        ttk.Label(left, text="Theta (degrees)").grid(row=4, column=0, sticky="w")
        self.theta_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.theta_var, width=15).grid(row=4, column=1, sticky="w")

        # Options for assumptions when not enough inputs
        options_frame = ttk.LabelFrame(left, text="Assumptions for single-value inputs", padding=6)
        options_frame.grid(row=5, column=0, columnspan=3, pady=(10, 6), sticky="we")

        ttk.Label(options_frame, text="If only one side is given assume theta =").grid(row=0, column=0, sticky="w")
        self.assume_theta_var = tk.DoubleVar(value=DEFAULT_THETA_IF_SINGLE_SIDE)
        ttk.Entry(options_frame, textvariable=self.assume_theta_var, width=8).grid(row=0, column=1, padx=(6, 0), sticky="w")
        ttk.Label(options_frame, text="°").grid(row=0, column=2, sticky="w")

        ttk.Label(options_frame, text="If only theta is given assume hypotenuse c =").grid(row=1, column=0, sticky="w")
        self.assume_scale_var = tk.DoubleVar(value=DEFAULT_HYPOTENUSE_IF_THETA_ONLY)
        ttk.Entry(options_frame, textvariable=self.assume_scale_var, width=8).grid(row=1, column=1, padx=(6, 0), sticky="w")

        # Buttons
        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=(8, 0), sticky="we")
        ttk.Button(btn_frame, text="Compute & Draw", command=self.compute_and_draw).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="Reset", command=self.reset).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text="Quit", command=self.quit).grid(row=0, column=2, padx=4)

        # Results
        results_frame = ttk.LabelFrame(left, text="Computed values", padding=6)
        results_frame.grid(row=7, column=0, columnspan=3, pady=(10, 0), sticky="we")
        self.result_text = tk.Text(results_frame, width=34, height=8, wrap="word")
        self.result_text.grid(row=0, column=0)

        # Canvas for drawing
        canvas_frame = ttk.Frame(right)
        canvas_frame.grid(row=0, column=0)
        self.canvas = tk.Canvas(canvas_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white")
        self.canvas.grid(row=0, column=0)

        # initial drawing
        self.draw_placeholder()

    def draw_placeholder(self):
        self.canvas.delete("all")
        self.canvas.create_text(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2, text="Right Triangle Visualization\n(Click 'Compute & Draw' to render)",
                                font=("Arial", 14), fill="gray", justify="center")

    def reset(self):
        self.a_var.set("")
        self.b_var.set("")
        self.c_var.set("")
        self.theta_var.set("")
        self.result_text.delete("1.0", tk.END)
        self.draw_placeholder()

    def compute_and_draw(self):
        a_in = self.a_var.get().strip()
        b_in = self.b_var.get().strip()
        c_in = self.c_var.get().strip()
        theta_in = self.theta_var.get().strip()

        try:
            a, b, c, theta_deg, note = compute_from_inputs(
                a_in, b_in, c_in, theta_in,
                assume_theta_for_single_side=float(self.assume_theta_var.get()),
                scale_for_theta_only=float(self.assume_scale_var.get()),
            )
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")
            return

        # Update result text
        self.result_text.delete("1.0", tk.END)
        txt = f"a (adjacent)  = {a:.6g}\n"
        txt += f"b (opposite)  = {b:.6g}\n"
        txt += f"c (hypotenuse)= {c:.6g}\n"
        txt += f"theta         = {theta_deg:.6g}°\n"
        if note:
            txt += "\nNote: " + note + "\n"
        self.result_text.insert("1.0", txt)

        # Draw triangle scaled to canvas
        self.draw_triangle(a, b, c, theta_deg)

    def draw_triangle(self, a, b, c, theta_deg):
        self.canvas.delete("all")
        # We interpret:
        # - angle theta at vertex A (origin)
        # - side a along +x from A
        # - side b along -y from A
        # Points:
        # A = (x0, y0)
        # B = (x0 + a_s, y0)
        # C = (x0, y0 - b_s)
        # hypotenuse BC between B and C

        # compute scale to fit
        max_leg_x = a
        max_leg_y = b

        if max_leg_x == 0 and max_leg_y == 0:
            self.draw_placeholder()
            return

        # available drawing area
        avail_w = CANVAS_WIDTH - 2 * MARGIN
        avail_h = CANVAS_HEIGHT - 2 * MARGIN

        # scale so both legs fit with margin, and also c fits diagonally
        # but primarily ensure a fits horizontally and b fits vertically
        scale_x = avail_w / (max_leg_x if max_leg_x > 0 else 1)  
        scale_y = avail_h / (max_leg_y if max_leg_y > 0 else 1)  
        scale = min(scale_x, scale_y, 1.0)  # do not enlarge by default beyond 1:1 unless it's tiny; but allow enlargement
        # To allow enlargement for small triangles, if both legs are much smaller than avail, increase scale:
        if scale > 1.0:
            scale = min(scale * 0.9, max(scale, 1.0))

        # However, better to compute scale to maximize use of area:
        if max_leg_x > 0 and max_leg_y > 0:
            scale = min(avail_w / max_leg_x, avail_h / max_leg_y) * 0.9
        else:
            scale = (avail_w if max_leg_x > 0 else avail_h) * 0.9 / (max_leg_x if max_leg_x > 0 else max_leg_y)

        # Safeguard
        if scale <= 0:
            scale = 1.0

        a_s = a * scale
        b_s = b * scale

        x0 = MARGIN
        y0 = CANVAS_HEIGHT - MARGIN

        Ax, Ay = x0, y0
        Bx, By = x0 + a_s, y0
        Cx, Cy = x0, y0 - b_s

        # Draw legs and hypotenuse
        self.canvas.create_line(Ax, Ay, Bx, By, width=3, fill="blue")  # side a
        self.canvas.create_line(Ax, Ay, Cx, Cy, width=3, fill="green")  # side b
        self.canvas.create_line(Bx, By, Cx, Cy, width=3, fill="red")  # hypotenuse

        # Label points
        point_radius = 4
        self.canvas.create_oval(Ax - point_radius, Ay - point_radius, Ax + point_radius, Ay + point_radius, fill="black")
        self.canvas.create_text(Ax - 10, Ay + 12, text="A (θ)", anchor="e")
        self.canvas.create_oval(Bx - point_radius, By - point_radius, Bx + point_radius, By + point_radius, fill="black")
        self.canvas.create_text(Bx + 8, By + 12, text="B")
        self.canvas.create_oval(Cx - point_radius, Cy - point_radius, Cx + point_radius, Cy + point_radius, fill="black")
        self.canvas.create_text(Cx - 8, Cy - 12, text="C", anchor="e")

        # Label sides with midpoints
        mid_ab = ((Ax + Bx) / 2, (Ay + By) / 2)
        mid_ac = ((Ax + Cx) / 2, (Ay + Cy) / 2)
        mid_bc = ((Bx + Cx) / 2, (By + Cy) / 2)

        self.canvas.create_text(mid_ab[0], mid_ab[1] + 12, text=f"a = {a:.4g}", fill="blue")
        self.canvas.create_text(mid_ac[0] - 12, mid_ac[1], text=f"b = {b:.4g}", fill="green")
        # Place c label at a small offset perpendicular to hypotenuse
        self.canvas.create_text(mid_bc[0] + 14, mid_bc[1] - 8, text=f"c = {c:.4g}", fill="red")

        # Draw right angle square at A
        sq_size = min(20, min(a_s, b_s) * 0.2)
        self.canvas.create_line(Ax + sq_size, Ay, Ax + sq_size, Ay - sq_size, fill="black", width=2)
        self.canvas.create_line(Ax + sq_size, Ay - sq_size, Ax, Ay - sq_size, fill="black", width=2)

        # Draw theta arc near A
        theta_rad = deg_to_rad(theta_deg)
        # arc bounding box (small)
        arc_r = min(60, min(a_s, b_s) * 0.6 + 10)
        arc_bbox = (Ax - arc_r, Ay - arc_r, Ax + arc_r, Ay + arc_r)
        # create_arc uses degrees start at 0 = +x axis and increases counterclockwise
        start_deg = 0  # along +x
        extent_deg = -theta_deg  # negative to go clockwise since b goes up
        # But we want arc between +x (a) and +y-negative (b) direction; since b goes up, that's CCW positive, but on canvas y is inverted.
        # Use extent = -theta_deg to draw small arc visually consistent.
        try:
            self.canvas.create_arc(arc_bbox, start=start_deg, extent=extent_deg, style="arc", width=2)
        except Exception:
            pass
        # Label theta
        theta_label_x = Ax + arc_r * 0.6 * math.cos(deg_to_rad(theta_deg / 2))
        theta_label_y = Ay - arc_r * 0.6 * math.sin(deg_to_rad(theta_deg / 2))
        self.canvas.create_text(theta_label_x, theta_label_y, text=f"θ = {theta_deg:.3g}°", anchor="center")

        # Footer info
        self.canvas.create_text(CANVAS_WIDTH / 2, 15, text="Right Triangle (A at right angle). a adj. to θ, b opp. to θ, c hypotenuse",
                                font=("Arial", 10))

        # Show scale factor info
        self.canvas.create_text(10 + 80, CANVAS_HEIGHT - 10, text=f"scale = {scale:.4g} px/unit", anchor="w", fill="gray")

        # Draw coordinates for debugging if needed (comment out)
        # self.canvas.create_text(80, CANVAS_HEIGHT - 30, text=f"A=({Ax:.1f},{Ay:.1f}) B=({Bx:.1f},{By:.1f}) C=({Cx:.1f},{Cy:.1f})", anchor="w", fill="gray")

        # nice bounding box
        self.canvas.configure(scrollregion=(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT))


if __name__ == "__main__":
    app = RightTriangleSimulator()
    app.mainloop()