
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timedelta
import os
import re

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, date2num, num2date
from matplotlib.widgets import RangeSlider
from matplotlib.backends.backend_pdf import PdfPages

# ==============================
# Utilities & parsing
# ==============================

NUM_UNIT_RE = re.compile(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([^,;]*)")

def parse_value_unit(text):
    """
    Extract numeric value and unit (strip trailing ';' and spaces).
    e.g., '-0.7629395 kPa;' -> ( -0.7629395, 'kPa' )
          '22.28 °C;'       -> (  22.28,      '°C' )
    """
    if text is None:
        return None, None
    t = str(text).strip().strip(" ;")
    m = NUM_UNIT_RE.search(t)
    if not m:
        return None, None
    try:
        val = float(m.group(1))
    except Exception:
        return None, None
    unit = m.group(2).strip().strip(" ;")
    return val, unit

def robust_key_val(line):
    """
    Header line like "StartTime yyyy ,2025" or "TagName ,OPM-PIT-001,".
    Returns key, val (val has trailing semicolons removed; splits at FIRST comma).
    """
    if line is None:
        return None, None
    s = str(line).strip()
    if "," in s:
        key_raw, val_raw = s.split(",", 1)
    else:
        key_raw, val_raw = s, ""
    key = key_raw.strip().rstrip(":")
    # take val up to first semicolon (if any), then trim
    val = val_raw.split(";", 1)[0].strip()
    return key, val

def sanitize_filename_component(s: str) -> str:
    """
    Remove characters illegal in filenames and collapse whitespace.
    """
    if not s:
        return ""
    s = re.sub(r'[\\/*?:"<>|]', '_', s)  # Windows-illegal
    s = re.sub(r'\s+', '_', s.strip())
    return s

def parse_cpg1500_csv(file_path):
    """
    Read CPG1500 mobile-app CSV and return:
      - df: DataFrame with [Timestamp, Pressure_kPa, Temperature_C]
      - header: dict of header key/values
      - pressure_unit: str (e.g., 'kPa')
      - tagname: str or ''
    Timestamps are generated as StartTime + i*lograte (seconds).
    """
    # Read raw lines (file is not a standard comma-separated table)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [ln.rstrip("\n") for ln in f]

    # Drop blank lines
    lines = [ln for ln in lines if ln.strip()]

    # Locate header marker
    header_start_idx = None
    for i, ln in enumerate(lines):
        if ln.lower().startswith("log header data"):
            header_start_idx = i
            break

    if header_start_idx is None:
        data_lines = lines
        header_lines = []
    else:
        data_lines = lines[:header_start_idx]
        header_lines = lines[header_start_idx:]

    # Parse header
    header = {}
    for ln in header_lines:
        k, v = robust_key_val(ln)
        if k:
            header[k] = v

    # Extract Start/Stop and Lograte
    def get_int(key, default):
        try:
            return int(str(header.get(key, default)).strip())
        except Exception:
            return int(default)

    start = datetime(
        get_int("StartTime yyyy", 1970),
        get_int("StartTime mo", 1),
        get_int("StartTime dd", 1),
        get_int("StartTime hh", 0),
        get_int("StartTime mm", 0),
        get_int("StartTime ss", 0),
    )

    stop = datetime(
        get_int("StopTime yyyy", 1970),
        get_int("StopTime mo", 1),
        get_int("StopTime dd", 1),
        get_int("StopTime hh", 0),
        get_int("StopTime mm", 0),
        get_int("StopTime ss", 0),
    )

    try:
        lograte = float(str(header.get("Lograte", "1")).strip())
        if lograte <= 0:
            lograte = 1.0
    except Exception:
        lograte = 1.0

    # Parse alternating Pressure/Temperature records
    records = []
    for ln in data_lines:
        parts = [p.strip() for p in ln.split(";") if p.strip()]
        if len(parts) < 3:
            continue
        try:
            idx = int(parts[0])
        except Exception:
            continue
        label = parts[1]
        value_raw = parts[2]
        val, unit = parse_value_unit(value_raw)
        if val is None:
            continue
        records.append({"idx": idx, "label": label, "value": val, "unit": unit})

    # Build list of samples (pair P & T)
    samples = []
    pressure_unit = ""
    i = 0
    while i < len(records):
        chunk = records[i:i+2]
        if len(chunk) < 2:
            break
        rec_p = next((r for r in chunk if r["label"].lower().startswith("pressure")), None)
        rec_t = next((r for r in chunk if r["label"].lower().startswith("temperature")), None)
        if rec_p is None or rec_t is None:
            i += 1
            continue
        if not pressure_unit:
            pressure_unit = rec_p.get("unit", "").strip()
        samples.append({
            "Pressure_kPa": rec_p["value"],      # keep column name as *_kPa for compatibility
            "Temperature_C": rec_t["value"],
        })
        i += 2

    df = pd.DataFrame(samples)
    if df.empty:
        raise ValueError("No Pressure/Temperature pairs found in the selected file.")

    # Build timestamps using StartTime and lograte
    n = len(df)
    timestamps = [start + timedelta(seconds=int(round(i * lograte))) for i in range(n)]
    df.insert(0, "Timestamp", pd.to_datetime(timestamps))

    # Extract TagName (if present)
    raw_tag = header.get("TagName", "") or header.get("TagName ", "")
    # Some exports may carry extras after the value; keep first token until any comma
    tagname = raw_tag.split(",", 1)[0].strip()

    # Non-fatal validation vs StopTime
    try:
        expected_duration = (stop - start).total_seconds()
        actual_duration = (df["Timestamp"].iloc[-1] - df["Timestamp"].iloc[0]).total_seconds()
        if abs(expected_duration - actual_duration) > max(lograte, 1.0):
            print(f"[WARN] StopTime mismatch: header duration={expected_duration:.0f}s, built={actual_duration:.0f}s")
    except Exception:
        pass

    return df, header, (pressure_unit or "kPa"), tagname

# ==============================
# Plot window with RangeSlider
# ==============================

class TrendWindow:
    """
    Matplotlib figure with a RangeSlider for time focus.
    - Slider is positioned far enough below the x-axis to avoid overlap.
    - Y-axis label includes extracted pressure unit.
    - Title includes TagName when available.
    """
    def __init__(self, df, pressure_unit="kPa", tagname=""):
        self.df = df.copy()
        self.df["Timestamp"] = pd.to_datetime(self.df["Timestamp"])
        self.df.sort_values("Timestamp", inplace=True)

        # Convert timestamps to Matplotlib date numbers (robust for pandas 2.x)
        self.xnum = date2num(self.df["Timestamp"].to_numpy())
        self.y = self.df["Pressure_kPa"].values

        # Figure: add generous bottom margin so slider never collides with tick labels
        self.fig, self.ax = plt.subplots(figsize=(11, 5.8))
        # Leave space for longer, rotated dateticks and the slider
        plt.subplots_adjust(bottom=0.30, left=0.10, right=0.97, top=0.90)

        # Plot
        (self.line,) = self.ax.plot(self.df["Timestamp"], self.y, color="tab:blue", lw=1.6)

        # Titles/labels
        title = f"{tagname} – Pressure vs Time" if tagname else "CPG1500 Pressure vs Time"
        self.ax.set_title(title)
        y_unit = pressure_unit if pressure_unit else "kPa"
        self.ax.set_ylabel(f"Pressure ({y_unit})")
        self.ax.set_xlabel("Time")
        self.ax.grid(True, alpha=0.3)

        # X formatting
        self.ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%M:%S'))
        # Rotate labels to avoid overlap with slider
        self.fig.autofmt_xdate(rotation=25, ha="right")

        # Place the slider well below the x-axis tick labels
        # [left, bottom, width, height] in figure coordinates
        slider_ax = self.fig.add_axes([0.12, 0.10, 0.76, 0.05])

        self.slider = RangeSlider(
            ax=slider_ax,
            label="Time Range",
            valmin=self.xnum.min(),
            valmax=self.xnum.max(),
            valinit=(self.xnum.min(), self.xnum.max())
        )
        self.slider.on_changed(self._on_slider_change)

        # Reset button (positioned next to slider)
        from matplotlib.widgets import Button
        reset_ax = self.fig.add_axes([0.89, 0.10, 0.08, 0.05])
        self.reset_btn = Button(reset_ax, 'Reset')
        self.reset_btn.on_clicked(self._on_reset)

        # Initial limits
        self.ax.set_xlim(num2date(self.xnum.min()), num2date(self.xnum.max()))

        # Optional: set OS window title (best-effort)
        try:
            self.fig.canvas.manager.set_window_title(title)
        except Exception:
            pass

        self.pressure_unit = y_unit  # keep for potential legends/exports
        self.tagname = tagname

    def _on_slider_change(self, val):
        xmin, xmax = self.slider.val
        self.ax.set_xlim(num2date(xmin), num2date(xmax))
        self.fig.canvas.draw_idle()

    def _on_reset(self, event):
        self.slider.reset()

    def show(self):
        plt.show()

    def save_pdf(self, out_path):
        try:
            with PdfPages(out_path) as pdf:
                pdf.savefig(self.fig, bbox_inches="tight")
            return True, None
        except Exception as e:
            return False, str(e)

# ==============================
# Excel export
# ==============================

def export_excel(df, header, out_path):
    """
    Exports cleaned data + summary to Excel.
    Sheets:
      - CleanData
      - Summary
    """
    try:
        summary = {
            "n_samples": len(df),
            "start_time": str(df["Timestamp"].iloc[0]) if len(df) else "",
            "stop_time": str(df["Timestamp"].iloc[-1]) if len(df) else "",
            "lograte_s": header.get("Lograte", ""),
            "tag": header.get("TagName", ""),
            "pressure_min": float(df["Pressure_kPa"].min()) if len(df) else None,
            "pressure_max": float(df["Pressure_kPa"].max()) if len(df) else None,
            "pressure_mean": float(df["Pressure_kPa"].mean()) if len(df) else None,
            "temperature_median": float(df["Temperature_C"].median()) if "Temperature_C" in df and len(df) else None,
        }
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="CleanData")
            pd.DataFrame([summary]).to_excel(writer, index=False, sheet_name="Summary")
        return True, None
    except Exception as e:
        return False, str(e)

# ==============================
# Tkinter App
# ==============================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CPG1500 CSV Viewer")
        self.geometry("460x240")
        self.df = None
        self.header = {}
        self.trend = None
        self.current_file = None
        self.pressure_unit = "kPa"
        self.tagname = ""

        # UI
        tk.Label(self, text="CPG1500 Mobile CSV → Trend + Exports",
                 font=("Segoe UI", 11, "bold")).pack(pady=8)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=6)

        tk.Button(btn_frame, text="Open CSV…", width=20,
                  command=self.open_csv).grid(row=0, column=0, padx=8, pady=6)
        tk.Button(btn_frame, text="Show Trend", width=20,
                  command=self.show_trend).grid(row=0, column=1, padx=8, pady=6)
        tk.Button(btn_frame, text="Export PDF…", width=20,
                  command=self.export_pdf).grid(row=1, column=0, padx=8, pady=6)
        tk.Button(btn_frame, text="Export Excel…", width=20,
                  command=self.export_excel).grid(row=1, column=1, padx=8, pady=6)

        self.status = tk.StringVar(value="Select a CSV to begin.")
        tk.Label(self, textvariable=self.status, fg="#555").pack(pady=8)

    def open_csv(self):
        filetypes = [("CSV files", "*.csv"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Open CPG1500 CSV", filetypes=filetypes)
        if not path:
            return
        try:
            df, header, p_unit, tag = parse_cpg1500_csv(path)
            df = df[["Timestamp", "Pressure_kPa", "Temperature_C"]]  # ensure order

            self.df = df
            self.header = header
            self.current_file = path
            self.pressure_unit = p_unit or "kPa"
            self.tagname = tag or ""

            tag_msg = f" | Tag: {self.tagname}" if self.tagname else ""
            self.status.set(f"Loaded: {os.path.basename(path)} — {len(df)} samples{tag_msg}")
            messagebox.showinfo("Success", f"Parsed {len(df)} samples.\n{tag_msg.strip()}")
        except Exception as e:
            messagebox.showerror("Error parsing CSV", str(e))

    def show_trend(self):
        if self.df is None:
            messagebox.showwarning("No data", "Please open a CSV first.")
            return
        # Open a new figure with proper spacing and labels
        self.trend = TrendWindow(self.df, pressure_unit=self.pressure_unit, tagname=self.tagname)
        self.trend.show()

    def export_pdf(self):
        if self.df is None:
            messagebox.showwarning("No data", "Please open a CSV first.")
            return
        if self.trend is None:
            # Create a trend window silently to export full range if not yet shown
            self.trend = TrendWindow(self.df, pressure_unit=self.pressure_unit, tagname=self.tagname)

        base_tag = sanitize_filename_component(self.tagname) or "CPG1500"
        default_name = f"{base_tag}_Pressure_Trend.pdf"

        out_path = filedialog.asksaveasfilename(
            title="Save chart as PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=default_name
        )
        if not out_path:
            return
        ok, err = self.trend.save_pdf(out_path)
        if ok:
            messagebox.showinfo("Exported", f"Saved PDF to:\n{out_path}")
        else:
            messagebox.showerror("Export failed", err)

    def export_excel(self):
        if self.df is None:
            messagebox.showwarning("No data", "Please open a CSV first.")
            return
        base_tag = sanitize_filename_component(self.tagname) or "CPG1500"
        default_name = f"{base_tag}_cleaned.xlsx"

        out_path = filedialog.asksaveasfilename(
            title="Save data as Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile=default_name
        )
        if not out_path:
            return
        ok, err = export_excel(self.df, self.header, out_path)
        if ok:
            messagebox.showinfo("Exported", f"Saved Excel to:\n{out_path}")
        else:
            messagebox.showerror("Export failed", err)

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
