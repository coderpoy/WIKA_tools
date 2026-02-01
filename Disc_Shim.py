import math
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle, Circle
from matplotlib.figure import Figure

# Default clearance (mm) shown in the UI; user may change this
DEFAULT_CLEARANCE_MM = 10.0


def calculate_sheet_for_quantity(diameter_mm, quantity, clearance_mm):
    """
    Mode 1:
    Given disc diameter, required quantity and clearance, compute the smallest square shim (mm x mm)
    that fits at least that many discs in a regular grid.
    """
    effective_diameter = diameter_mm + clearance_mm  # mm between centers in grid
    discs_per_side = math.ceil(math.sqrt(quantity))
    sheet_side_mm = discs_per_side * effective_diameter
    total_discs_possible = discs_per_side ** 2
    return {
        "sheet_width_mm": sheet_side_mm,
        "sheet_height_mm": sheet_side_mm,
        "discs_per_row": discs_per_side,
        "discs_per_col": discs_per_side,
        "total_discs_possible": total_discs_possible,
        "effective_diameter_mm": effective_diameter
    }


def calculate_quantity_for_sheet(diameter_mm, sheet_w_mm, sheet_h_mm, clearance_mm):
    """
    Mode 2:
    Given disc diameter, a rectangular shim (mm x mm), and clearance, compute how many discs fit
    in a regular grid.
    """
    effective_diameter = diameter_mm + clearance_mm
    # Number of centers that can be placed across width/height
    discs_per_row = int(sheet_w_mm // effective_diameter)
    discs_per_col = int(sheet_h_mm // effective_diameter)
    total = max(0, discs_per_row * discs_per_col)
    return {
        "discs_per_row": discs_per_row,
        "discs_per_col": discs_per_col,
        "total_discs_possible": total,
        "effective_diameter_mm": effective_diameter
    }


def choose_scale_for_display(width_mm, height_mm, max_px=700):
    """
    Try to use 1:1 scaling (1 mm -> 1 px). If the sheet is too large to fit within max_px
    in either dimension, reduce scale to 1/n where n is the smallest integer >= 1 that
    makes both dimensions fit. That yields 1:2, 1:3, etc.
    """
    max_dim = max(width_mm, height_mm)
    if max_dim <= max_px:
        return 1.0
    n = math.ceil(max_dim / max_px)
    return 1.0 / n


class DiscShimApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Disc Shim Layout Tool")
        self.minsize(1000, 700)

        # Left panel for controls
        control_frame = ttk.Frame(self)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Mode selection
        self.mode_var = tk.StringVar(value="quantity_to_sheet")
        modes_label = ttk.Label(control_frame, text="Mode:")
        modes_label.grid(row=0, column=0, sticky="w")

        rb1 = ttk.Radiobutton(control_frame, text="Need N discs -> compute optimal square shim",
                              variable=self.mode_var, value="quantity_to_sheet",
                              command=self.on_mode_change)
        rb1.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        rb2 = ttk.Radiobutton(control_frame, text="Have shim size -> compute how many discs fit",
                              variable=self.mode_var, value="sheet_to_quantity",
                              command=self.on_mode_change)
        rb2.grid(row=2, column=0, columnspan=2, sticky="w", pady=2)

        sep = ttk.Separator(control_frame, orient="horizontal")
        sep.grid(row=3, column=0, columnspan=2, sticky="we", pady=8)

        # Common inputs
        ttk.Label(control_frame, text="Disc diameter (mm):").grid(row=4, column=0, sticky="w")
        self.diameter_entry = ttk.Entry(control_frame)
        self.diameter_entry.grid(row=4, column=1, sticky="ew")
        self.diameter_entry.insert(0, "20")  # sensible default

        # Clearance input (new)
        ttk.Label(control_frame, text="Clearance between discs (mm):").grid(row=5, column=0, sticky="w")
        self.clearance_entry = ttk.Entry(control_frame)
        self.clearance_entry.grid(row=5, column=1, sticky="ew")
        self.clearance_entry.insert(0, str(int(DEFAULT_CLEARANCE_MM)))

        # Mode-specific frames
        self.frame_mode1 = ttk.Frame(control_frame)
        self.frame_mode1.grid(row=6, column=0, columnspan=2, sticky="we", pady=6)

        ttk.Label(self.frame_mode1, text="Quantity of discs:").grid(row=0, column=0, sticky="w")
        self.quantity_entry = ttk.Entry(self.frame_mode1)
        self.quantity_entry.grid(row=0, column=1, sticky="ew")
        self.quantity_entry.insert(0, "16")

        self.frame_mode2 = ttk.Frame(control_frame)
        self.frame_mode2.grid(row=7, column=0, columnspan=2, sticky="we", pady=6)

        ttk.Label(self.frame_mode2, text="Shim width (mm):").grid(row=0, column=0, sticky="w")
        self.width_entry = ttk.Entry(self.frame_mode2)
        self.width_entry.grid(row=0, column=1, sticky="ew")
        self.width_entry.insert(0, "200")

        ttk.Label(self.frame_mode2, text="Shim height (mm):").grid(row=1, column=0, sticky="w")
        self.height_entry = ttk.Entry(self.frame_mode2)
        self.height_entry.grid(row=1, column=1, sticky="ew")
        self.height_entry.insert(0, "200")

        # Results
        res_label = ttk.Label(control_frame, text="Results:")
        res_label.grid(row=8, column=0, sticky="w", pady=(8, 0))
        self.results_text = tk.Text(control_frame, width=36, height=10, wrap="word")
        self.results_text.grid(row=9, column=0, columnspan=2, pady=4)

        # Buttons
        calc_btn = ttk.Button(control_frame, text="Calculate & Visualize", command=self.on_calculate)
        calc_btn.grid(row=10, column=0, pady=8, sticky="we")
        clear_btn = ttk.Button(control_frame, text="Clear Results", command=lambda: self.results_text.delete("1.0", tk.END))
        clear_btn.grid(row=10, column=1, pady=8, sticky="we")

        # Right panel for visualization
        viz_frame = ttk.Frame(self)
        viz_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.viz_frame = viz_frame

        # Matplotlib figure (placeholder)
        self.figure = Figure(figsize=(6, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=viz_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        self.on_mode_change()

    def on_mode_change(self):
        mode = self.mode_var.get()
        if mode == "quantity_to_sheet":
            self.frame_mode1.lift()
            self.frame_mode2.lower()
        else:
            self.frame_mode2.lift()
            self.frame_mode1.lower()

    def read_clearance(self):
        """Read and validate clearance value from the UI. Returns float clearance_mm or raises ValueError."""
        txt = self.clearance_entry.get().strip()
        if txt == "":
            return DEFAULT_CLEARANCE_MM
        try:
            val = float(txt)
            if val < 0:
                raise ValueError("Clearance must be non-negative.")
            return val
        except ValueError:
            raise ValueError("Clearance must be a non-negative number (mm).")

    def on_calculate(self):
        mode = self.mode_var.get()
        try:
            diameter_mm = float(self.diameter_entry.get())
            if diameter_mm <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid positive number for disc diameter.")
            return

        # Read clearance
        try:
            clearance_mm = self.read_clearance()
        except ValueError as e:
            messagebox.showerror("Invalid clearance", str(e))
            return

        self.results_text.delete("1.0", tk.END)

        if mode == "quantity_to_sheet":
            # Mode 1
            try:
                quantity = int(self.quantity_entry.get())
                if quantity <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid input", "Please enter a valid positive integer for quantity.")
                return

            res = calculate_sheet_for_quantity(diameter_mm, quantity, clearance_mm)
            w_mm = res["sheet_width_mm"]
            h_mm = res["sheet_height_mm"]

            msg = (
                f"Mode: Quantity -> Optimal Square Shim\n"
                f"Disc diameter: {diameter_mm:.2f} mm\n"
                f"Clearance: {clearance_mm:.2f} mm\n"
                f"Requested quantity: {quantity}\n\n"
                f"Optimal shim size (W x H): {w_mm:.1f} mm x {h_mm:.1f} mm\n"
                f"Discs per side: {res['discs_per_row']} x {res['discs_per_col']} = {res['total_discs_possible']}\n"
            )
            self.results_text.insert(tk.END, msg)

            # build disc centers
            centers = []
            eff = res["effective_diameter_mm"]
            r = diameter_mm / 2.0
            for i in range(res["discs_per_row"]):
                for j in range(res["discs_per_col"]):
                    cx = (i + 0.5) * eff
                    cy = (j + 0.5) * eff
                    # Ensure actual disc fits inside sheet
                    if cx + r <= w_mm + 1e-6 and cy + r <= h_mm + 1e-6:
                        centers.append((cx, cy))
            self.draw_sheet_and_discs(w_mm, h_mm, centers, r, clearance_mm)

        else:
            # Mode 2
            try:
                w_mm = float(self.width_entry.get())
                h_mm = float(self.height_entry.get())
                if w_mm <= 0 or h_mm <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid input", "Please enter valid positive numbers for shim dimensions.")
                return

            res = calculate_quantity_for_sheet(diameter_mm, w_mm, h_mm, clearance_mm)
            msg = (
                f"Mode: Shim -> Quantity\n"
                f"Disc diameter: {diameter_mm:.2f} mm\n"
                f"Clearance: {clearance_mm:.2f} mm\n\n"
                f"Shim size (W x H): {w_mm:.1f} mm x {h_mm:.1f} mm\n"
                f"Discs per row: {res['discs_per_row']}\n"
                f"Discs per column: {res['discs_per_col']}\n"
                f"Total discs that fit: {res['total_discs_possible']}\n"
            )
            self.results_text.insert(tk.END, msg)

            centers = []
            eff = res["effective_diameter_mm"]
            r = diameter_mm / 2.0
            for i in range(res["discs_per_row"]):
                for j in range(res["discs_per_col"]):
                    cx = (i + 0.5) * eff
                    cy = (j + 0.5) * eff
                    if cx + r <= w_mm + 1e-6 and cy + r <= h_mm + 1e-6:
                        centers.append((cx, cy))
            self.draw_sheet_and_discs(w_mm, h_mm, centers, r, clearance_mm)

    def draw_sheet_and_discs(self, sheet_w_mm, sheet_h_mm, centers_mm, radius_mm, clearance_mm):
        """
        Draw the sheet and discs inside the embedded matplotlib canvas.
        Uses a scale chosen by choose_scale_for_display to attempt 1:1 mm to px mapping.
        """
        max_display_px = 700  # target maximum size in pixels for the largest dimension
        scale = choose_scale_for_display(sheet_w_mm, sheet_h_mm, max_px=max_display_px)
        # Convert mm coords to px units for plotting
        width_px = sheet_w_mm * scale
        height_px = sheet_h_mm * scale
        dpi = 100.0
        # Resize figure to match px size (in inches) but clamp minimum sizes to keep visibility
        fig_w_in = max(width_px / dpi, 4.0)
        fig_h_in = max(height_px / dpi, 4.0)

        # Clear old widgets from the viz frame BEFORE creating a new canvas.
        for child in self.viz_frame.winfo_children():
            child.destroy()

        # Recreate figure and canvas
        self.figure = Figure(figsize=(fig_w_in, fig_h_in), dpi=dpi)
        self.ax = self.figure.add_subplot(111)
        self.ax.clear()
        self.ax.set_aspect("equal")
        # Axis limits in px units
        self.ax.set_xlim(0, width_px)
        self.ax.set_ylim(0, height_px)

        # Draw sheet rectangle (in px units)
        sheet_rect = Rectangle((0, 0), width_px, height_px, linewidth=1.5, edgecolor="black", facecolor="#e0e0e0")
        self.ax.add_patch(sheet_rect)

        # Draw discs
        for idx, (cx_mm, cy_mm) in enumerate(centers_mm):
            cx = cx_mm * scale
            cy = cy_mm * scale
            r = radius_mm * scale
            disc = Circle((cx, cy), radius=r, edgecolor="blue", facecolor="#add8e6", linewidth=0.8)
            self.ax.add_patch(disc)
            # label the first disc with real diameter in mm
            if idx == 0:
                self.ax.text(cx, cy, f"{radius_mm*2:.0f} mm", color="black", fontsize=8, ha="center", va="center", weight="bold")

        # Optionally draw center grid points or clearance visualization (light lines every effective diameter)
        eff_mm = (radius_mm * 2) + clearance_mm
        # draw faint guidelines for the effective grid
        for i in range(int(math.ceil(sheet_w_mm / eff_mm)) + 1):
            x = i * eff_mm * scale
            self.ax.plot([x, x], [0, height_px], color="#cccccc", linewidth=0.5, linestyle="--")
        for j in range(int(math.ceil(sheet_h_mm / eff_mm)) + 1):
            y = j * eff_mm * scale
            self.ax.plot([0, width_px], [y, y], color="#cccccc", linewidth=0.5, linestyle="--")

        # Grid and labels: show axes in mm (convert ticks back to mm for user friendliness)
        self.ax.set_xlabel("mm (scaled)")
        self.ax.set_ylabel("mm (scaled)")
        xticks_px = self._nice_ticks(0, width_px)
        yticks_px = self._nice_ticks(0, height_px)
        self.ax.set_xticks(xticks_px)
        self.ax.set_yticks(yticks_px)
        xticks_mm = [f"{int(round(x / scale))}" for x in xticks_px]
        yticks_mm = [f"{int(round(y / scale))}" for y in yticks_px]
        self.ax.set_xticklabels(xticks_mm)
        self.ax.set_yticklabels(yticks_mm)
        self.ax.grid(True, linestyle="--", linewidth=0.5)

        # Title includes scale info
        if scale == 1.0:
            scale_text = "1:1 (1 mm -> 1 px)"
        else:
            denom = int(round(1.0 / scale))
            scale_text = f"1:{denom} (1 display px = {denom} mm)"
        self.ax.set_title(f"Sheet layout — Scale {scale_text} — Clearance {clearance_mm:.1f} mm")

        # Create and pack the new canvas into the viz frame
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.viz_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        self.canvas.draw()

    @staticmethod
    def _nice_ticks(start_px, end_px, max_ticks=8):
        """
        Create 'nice' tick positions (in px units) for the axes. Returns list of tick positions in px.
        """
        span = end_px - start_px
        if span <= 0:
            return [0]
        preferred_steps = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500]
        step = max(1, int(span / max_ticks))
        chosen = None
        for ps in preferred_steps:
            if ps <= step:
                chosen = ps
        if chosen is None:
            chosen = max(1, step)
        first = (math.floor(start_px / chosen) + 1) * chosen
        ticks = []
        x = first
        while x < end_px:
            ticks.append(x)
            x += chosen
        if not ticks:
            ticks = [start_px, end_px]
        return ticks


if __name__ == "__main__":
    app = DiscShimApp()
    app.mainloop()