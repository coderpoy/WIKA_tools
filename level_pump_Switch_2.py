#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Level Control — Dual Switch + DPDT Relay (Tkinter GUI, WHITE THEME)

Adjusted layout:
- Chart is placed adjacent to the tank and uses the same vertical scale (height)
  so the High/Low setpoint dashed lines align visually between tank and chart.
- A dedicated wiring area (wiring_canvas) is placed below the tank+chart and
  contains the DPDT relay, wires and the pump image at the left so wiring is
  continuous across the width.
- DPDT static and animated drawing live on the wiring_canvas (not on the tank).
"""
import os
import sys
import traceback
import random
import tkinter as tk
from tkinter import ttk, messagebox


# -------------------------- Simulation Core --------------------------
class Debouncer:
    """Simple time-based debouncer for a boolean input."""
    def __init__(self, threshold_s: float):
        self.threshold = threshold_s
        self.state = False
        self.timer = 0.0

    def update(self, raw: bool, dt: float):
        if raw == self.state:
            self.timer = 0.0
            return self.state
        self.timer += dt
        if self.timer >= self.threshold:
            self.state = raw
            self.timer = 0.0
        return self.state


class DPDT:
    """DPDT relay pole mapping used to drive the pump."""
    def __init__(self, pump_contact: str = "NC"):
        self.pump_contact = pump_contact  # 'NC' or 'NO'

    def pump_on(self, coil_on: bool) -> bool:
        # NC: pump runs when coil is de-energized
        # NO: pump runs when coil is energized
        return (not coil_on) if self.pump_contact == "NC" else coil_on


class TankSim:
    """Tank + relay + pump simulator."""
    def __init__(self):
        # Process & control parameters
        self.level = 50.0          # %
        self.high_sp = 75.0        # %
        self.low_sp = 40.0         # %
        self.fill_rate = 6.0       # %/s when pump ON (magnitude)
        self.drain_rate = 3.0      # %/s when pump OFF (or ON in DRAIN mode)
        self.dt = 0.2              # seconds per step
        self.noise_amp = 0.5       # +/- % noise on measured level

        # Relay state
        self.coil_on = False
        self.dpdt = DPDT("NC")

        # Debouncers for two switches
        self.db_high = Debouncer(0.2)
        self.db_low  = Debouncer(0.2)

        # Pump effect: "FILL" or "DRAIN"
        self.pump_mode = "FILL"

    def step(self, db_high_s: float, db_low_s: float):
        """Advance the simulation one time-step and return a status dict."""
        self.db_high.threshold = db_high_s
        self.db_low.threshold  = db_low_s

        # Measured level with bounded noise
        meas = max(0.0, min(100.0, self.level + random.uniform(-self.noise_amp, self.noise_amp)))

        # Raw switch closures based on measured level
        raw_high = meas >= self.high_sp
        raw_low  = meas <= self.low_sp

        # Debounced closures
        high_closed = self.db_high.update(raw_high, self.dt)
        low_closed  = self.db_low.update(raw_low,  self.dt)

        # Hysteresis: energize at High; de-energize at Low
        if high_closed:
            self.coil_on = True
        elif low_closed:
            self.coil_on = False

        # Pump state via DPDT mapping
        pump_on = self.dpdt.pump_on(self.coil_on)

        # Tank dynamics with Pump effect
        if self.pump_mode == "FILL":
            # Pump ON raises level; pump OFF lets it fall
            delta = (self.fill_rate if pump_on else -self.drain_rate) * self.dt
        else:  # DRAIN
            # Pump ON lowers level; pump OFF lets it rise
            delta = (-self.fill_rate if pump_on else self.drain_rate) * self.dt

        self.level = max(0.0, min(100.0, self.level + delta))

        return {
            "level": round(self.level, 2),
            "measured": round(meas, 2),
            "high_closed": high_closed,
            "low_closed": low_closed,
            "coil_on": self.coil_on,
            "pump_on": pump_on,
        }


# -------------------------- Tkinter GUI App --------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Level Control — Dual Switch + DPDT Relay (White GUI)")
        self.geometry("1320x900")
        self.configure(bg="#ffffff")

        self.sim = TankSim()
        self.timer = None
        self.series = []       # time series for chart
        self.max_pts = 420     # samples kept on chart

        # DPDT lever animation state (0.0 = NC side, 1.0 = NO side)
        self.dpdt_pos = 0.0
        self.dpdt_target = 0.0
        self.dpdt_animating = False

        # colors (solid RGB only; no alpha)
        self.COLOR_AXIS = "#999999"
        self.COLOR_GRID = "#eeeeee"
        self.COLOR_TEXT = "#666666"
        self.COLOR_TRUE = "#1e88e5"  # blue
        self.COLOR_MEAS = "#f59e0b"  # amber
        self.COLOR_PUMP = "#22c55e"  # green

        # DPDT layout storage (coordinates relative to wiring canvas)
        self.dpdt_coords = {}

        self._build_ui()

    # -------------------- UI Construction --------------------
    def _build_ui(self):
        # Top-level grid: 3 columns (controls, tank, chart)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)
        # two rows: row 0 = tank + chart, row 1 = wiring area + pump image
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)

        # White theme
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('White.TLabelframe', background='#ffffff', foreground='#0f172a')
        style.configure('White.TLabelframe.Label', background='#ffffff', foreground='#0f172a')
        style.configure('White.TFrame', background='#ffffff')
        style.configure('White.TLabel', background='#ffffff', foreground='#0f172a')
        style.configure('White.TButton', background='#e5e7eb', foreground='#0f172a')
        style.configure('White.TEntry', fieldbackground='#ffffff', foreground='#0f172a')
        style.configure('White.TCombobox', fieldbackground='#ffffff', foreground='#0f172a')

        # Controls panel (left)
        controls = ttk.LabelFrame(self, text="Settings", style='White.TLabelframe')
        controls.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=12, pady=12)

        # Controls grid: 2 columns (labels left, inputs right)
        for i in range(0, 20):
            controls.rowconfigure(i, weight=0)
        controls.columnconfigure(0, weight=0)
        controls.columnconfigure(1, weight=1)

        # Variables
        self.var_high = tk.DoubleVar(value=self.sim.high_sp)
        self.var_low  = tk.DoubleVar(value=self.sim.low_sp)
        self.var_fill = tk.DoubleVar(value=self.sim.fill_rate)
        self.var_drain= tk.DoubleVar(value=self.sim.drain_rate)
        self.var_dtms = tk.IntVar(value=int(self.sim.dt*1000))
        self.var_init = tk.DoubleVar(value=self.sim.level)
        self.var_noise= tk.DoubleVar(value=self.sim.noise_amp)
        self.var_dbms = tk.IntVar(value=200)
        self.var_pump = tk.StringVar(value=self.sim.dpdt.pump_contact)
        self.var_mode = tk.StringVar(value=self.sim.pump_mode)  # FILL or DRAIN

        # Helper to align inputs
        def add_control(r, text, widget):
            ttk.Label(controls, text=text, style='White.TLabel').grid(row=r, column=0, sticky='w', padx=(8,6), pady=4)
            widget.grid(row=r, column=1, sticky='ew', padx=(0,8), pady=4)

        # Robust Spinbox helper (falls back to tk.Spinbox if ttk.Spinbox not available)
        def Spinbox(parent, **kwargs):
            try:
                return ttk.Spinbox(parent, **kwargs)
            except Exception:
                mapping = {}
                for k, v in kwargs.items():
                    if k == "from_":
                        mapping["from_"] = v
                    else:
                        mapping[k] = v
                return tk.Spinbox(parent, **mapping)

        # Widgets
        spin_high = Spinbox(controls, from_=10, to=95, increment=1, textvariable=self.var_high, width=10)
        spin_low  = Spinbox(controls, from_=5,  to=90, increment=1, textvariable=self.var_low,  width=10)
        spin_fill = Spinbox(controls, from_=0.0, to=50.0, increment=0.5, textvariable=self.var_fill, width=10)
        spin_drain= Spinbox(controls, from_=0.0, to=50.0, increment=0.5, textvariable=self.var_drain, width=10)
        spin_dtms = Spinbox(controls, from_=50,  to=1000, increment=50,  textvariable=self.var_dtms, width=10)
        spin_init = Spinbox(controls, from_=0.0, to=100.0, increment=1.0, textvariable=self.var_init, width=10)
        spin_noise= Spinbox(controls, from_=0.0, to=5.0,  increment=0.1, textvariable=self.var_noise, width=10)
        spin_dbms = Spinbox(controls, from_=0,   to=2000, increment=50,  textvariable=self.var_dbms, width=10)
        combo_pump= ttk.Combobox(controls, values=["NC","NO"], textvariable=self.var_pump, width=8, state='readonly')
        combo_mode= ttk.Combobox(controls, values=["FILL", "DRAIN"], textvariable=self.var_mode, width=8, state='readonly')

        add_control(0, "High setpoint (%)", spin_high)
        add_control(1, "Low setpoint (%)",  spin_low)
        ttk.Separator(controls).grid(row=2, column=0, columnspan=2, sticky='ew', padx=8, pady=6)
        add_control(3, "Fill rate (%/s)",   spin_fill)
        add_control(4, "Drain rate (%/s)",  spin_drain)
        add_control(5, "Time step (ms)",    spin_dtms)
        add_control(6, "Initial level (%)", spin_init)
        add_control(7, "Sensor noise (±%)", spin_noise)
        add_control(8, "Debounce (ms)",     spin_dbms)
        add_control(9, "Pump contact",      combo_pump)
        add_control(10,"Pump effect",       combo_mode)

        # Buttons
        btn_row = ttk.Frame(controls, style='White.TFrame')
        btn_row.grid(row=12, column=0, columnspan=2, sticky='ew', padx=8, pady=(8,2))
        self.btn_start = ttk.Button(btn_row, text='Start', command=self.start, style='White.TButton')
        self.btn_stop  = ttk.Button(btn_row, text='Stop',  command=self.stop,  style='White.TButton')
        self.btn_reset = ttk.Button(btn_row, text='Reset', command=self.reset, style='White.TButton')
        self.btn_help  = ttk.Button(btn_row, text='Help',  command=self.show_help, style='White.TButton')
        self.btn_start.pack(side=tk.LEFT, padx=4)
        self.btn_stop.pack(side=tk.LEFT, padx=4)
        self.btn_reset.pack(side=tk.LEFT, padx=4)
        self.btn_help.pack(side=tk.LEFT, padx=4)

        # Status box
        status = ttk.LabelFrame(controls, text='Status', style='White.TLabelframe')
        status.grid(row=13, column=0, columnspan=2, sticky='ew', padx=8, pady=8)
        self.lbl_level = ttk.Label(status, text='Level: –', style='White.TLabel'); self.lbl_level.pack(anchor='w')
        self.lbl_meas  = ttk.Label(status, text='Measured: –', style='White.TLabel'); self.lbl_meas.pack(anchor='w')
        self.lbl_high  = ttk.Label(status, text='High: –', style='White.TLabel'); self.lbl_high.pack(anchor='w')
        self.lbl_low   = ttk.Label(status, text='Low: –',  style='White.TLabel'); self.lbl_low.pack(anchor='w')
        self.lbl_coil  = ttk.Label(status, text='Coil: –', style='White.TLabel'); self.lbl_coil.pack(anchor='w')
        # Pump indicator row: text + LED + running tag
        pump_row = ttk.Frame(status, style='White.TFrame'); pump_row.pack(fill='x', pady=(6,0))
        self.lbl_pump = ttk.Label(pump_row, text='Pump: –', style='White.TLabel'); self.lbl_pump.pack(side='left')
        self.pump_led = tk.Canvas(pump_row, width=18, height=18, bg='#ffffff', highlightthickness=0); self.pump_led.pack(side='right')
        self.pump_led_id = self.pump_led.create_oval(2,2,16,16, fill='#999999', outline='#666666')
        self.lbl_running = ttk.Label(status, text='Idle', style='White.TLabel'); self.lbl_running.pack(anchor='w', pady=(6,0))

        # Tank panel (center)
        tank_box = ttk.LabelFrame(self, text='Tank', style='White.TLabelframe')
        tank_box.grid(row=0, column=1, sticky='ns', padx=(0,12), pady=12)
        self.tank_canvas = tk.Canvas(tank_box, width=360, height=560, bg='#ffffff',
                                     highlightthickness=1, highlightbackground='#dddddd')
        self.tank_canvas.pack(padx=8, pady=8)

        # Chart panel (right) — match height to tank so setpoint lines align
        chart_box = ttk.LabelFrame(self, text='Trend (level & measured)', style='White.TLabelframe')
        chart_box.grid(row=0, column=2, sticky='nsew', padx=12, pady=12)
        chart_box.columnconfigure(0, weight=1)
        chart_box.rowconfigure(0, weight=1)
        # Set the same visual height as the tank so the horizontal setpoint lines align
        self.chart_canvas = tk.Canvas(chart_box, width=820, height=560, bg='#ffffff',
                                      highlightthickness=1, highlightbackground='#dddddd')
        self.chart_canvas.grid(row=0, column=0, sticky='nsew', padx=8, pady=8)

        # Wiring area (below tank and chart) — spans both columns so wiring is continuous
        wiring_box = ttk.LabelFrame(self, text='Wiring / Relay', style='White.TLabelframe')
        wiring_box.grid(row=1, column=1, columnspan=2, sticky='ew', padx=(0,12), pady=(0,12))
        wiring_box.columnconfigure(0, weight=1)
        # wiring canvas wide enough to cover tank+chart width
        wiring_w = 360 + 820 + 24
        self.wiring_canvas = tk.Canvas(wiring_box, width=wiring_w, height=140, bg='#ffffff',
                                       highlightthickness=1, highlightbackground='#dddddd')
        self.wiring_canvas.grid(row=0, column=0, sticky='nsew', padx=8, pady=8)

        # Initial visuals
        self.series.clear()
        self._draw_chart_axes()
        self._draw_tank_static()
        # Draw the static wiring area (pump + DPDT) and initial DPDT view
        self._draw_wiring_static()
        self._update_dpdt_view({})

    # -------------------- Wiring / pump image area --------------------
    def _draw_wiring_static(self):
        """Draw pump at left, DPDT area at right, store coordinates in self.dpdt_coords."""
        c = self.wiring_canvas
        c.delete('dpdt_static')
        try:
            w = int(c.winfo_width()) or int(c['width'])
            h = int(c.winfo_height()) or int(c['height'])
        except Exception:
            w = int(c['width']); h = int(c['height'])

        margin = 12
        left_area_x = margin + 10
        left_area_y = h // 2

        # Draw pump image at left area (simple vector)
        pump_x = left_area_x
        pump_y = left_area_y
        c.create_oval(pump_x, pump_y-18, pump_x+36, pump_y+18, outline='#666666', fill='#dddddd', tags=('dpdt_static',))
        c.create_rectangle(pump_x+36, pump_y-14, pump_x+86, pump_y+14, outline='#666666', fill='#eeeeee', tags=('dpdt_static',))
        c.create_text(pump_x+46, pump_y+32, text='Pump', fill=self.COLOR_TEXT, tags=('dpdt_static',))
        # pump terminal
        c.create_oval(pump_x+8, pump_y-4, pump_x+12, pump_y+4, outline='#666666', fill='#ffffff', tags=('dpdt_static',))
        self.dpdt_coords['pump_term'] = (pump_x+10, pump_y)

        # DPDT region on the right side of wiring area
        right_margin = 20
        box_w = 320
        box_h = 110
        right = w - right_margin
        left = right - box_w
        top = (h - box_h) // 2

        # internal pole positions
        left_base = left + 12
        pole_x_nc = left_base + 18
        pole_x_com = left_base + 100
        pole_x_no = left_base + 182
        pole_y1 = top + 24
        spacing = 36
        pole_y2 = pole_y1 + spacing

        def draw_pole(y):
            c.create_oval(pole_x_nc-8, y-8, pole_x_nc+8, y+8, outline='#666666', fill='#ffffff', tags=('dpdt_static',))
            c.create_oval(pole_x_com-8, y-8, pole_x_com+8, y+8, outline='#666666', fill='#ffffff', tags=('dpdt_static',))
            c.create_oval(pole_x_no-8, y-8, pole_x_no+8, y+8, outline='#666666', fill='#ffffff', tags=('dpdt_static',))
            c.create_text(pole_x_nc, y+18, text='NC', fill=self.COLOR_TEXT, tags=('dpdt_static',))
            c.create_text(pole_x_com, y+18, text='COM', fill=self.COLOR_TEXT, tags=('dpdt_static',))
            c.create_text(pole_x_no, y+18, text='NO', fill=self.COLOR_TEXT, tags=('dpdt_static',))
            return {'nc': (pole_x_nc, y), 'com': (pole_x_com, y), 'no': (pole_x_no, y)}

        coords1 = draw_pole(pole_y1)
        coords2 = draw_pole(pole_y2)
        self.dpdt_coords['upper'] = coords1
        self.dpdt_coords['lower'] = coords2

        # coil area between poles
        coil_x = (left + right) // 2
        coil_y = pole_y1 + spacing // 2
        self.dpdt_coords['coil'] = (coil_x, coil_y)
        c.create_rectangle(coil_x-46, coil_y-18, coil_x+46, coil_y+18, outline='#666666', tags=('dpdt_static',))
        c.create_text(coil_x, coil_y, text='COIL', fill=self.COLOR_TEXT, tags=('dpdt_static',))

        # small static supply box connected to COM of lower pole
        com = coords2['com']
        c.create_line(com[0], com[1], com[0]-28, com[1], fill='#666666', tags=('dpdt_static',))
        c.create_rectangle(com[0]-36, com[1]-8, com[0]-28, com[1]+8, outline='#666666', fill='#ffffff', tags=('dpdt_static',))
        c.create_text(com[0]-54, com[1], text='Supply', fill=self.COLOR_TEXT, tags=('dpdt_static',))

        # legend
        c.create_text(left + box_w//2, top + box_h + 4,
                      text='DPDT (lower pole wired to pump). Levers move to NO when coil energizes.',
                      fill=self.COLOR_TEXT, tags=('dpdt_static',), font=('', 8))

    # -------------------- Simulation Control --------------------
    def apply_config(self):
        # Enforce Low < High
        high = float(self.var_high.get()); low = float(self.var_low.get())
        if low >= high:
            low = high - 1.0
            self.var_low.set(low)
        # Apply to sim
        self.sim.high_sp = high
        self.sim.low_sp  = low
        self.sim.fill_rate = float(self.var_fill.get())
        self.sim.drain_rate= float(self.var_drain.get())
        self.sim.dt = float(self.var_dtms.get())/1000.0
        self.sim.level = float(self.var_init.get())
        self.sim.noise_amp = float(self.var_noise.get())
        self.sim.dpdt.pump_contact = self.var_pump.get()
        self.sim.pump_mode = self.var_mode.get()
        # Reset chart
        self.series.clear()
        self._draw_chart_axes()
        self._draw_wiring_static()

    def start(self):
        self.apply_config()
        if self.timer is None:
            self.lbl_running.configure(text='Running')
            self.btn_start.state(['disabled'])
            self._schedule_tick()

    def stop(self):
        if self.timer is not None:
            try:
                self.after_cancel(self.timer)
            except Exception:
                pass
            self.timer = None
            self.lbl_running.configure(text='Stopped')
            self.btn_start.state(['!disabled'])

    def reset(self):
        self.stop()
        self.apply_config()
        self._update_status({
            'level': self.sim.level,
            'measured': self.sim.level,
            'high_closed': False,
            'low_closed': False,
            'coil_on': False,
            'pump_on': False,
        })
        self._draw_tank_level(self.sim.level, self.sim.high_sp, self.sim.low_sp)
        # ensure dpdt visual reflects reset state
        self._update_dpdt_view({})

    # ---- Robust tick: schedule separate from execution so exceptions don't kill GUI ----
    def _schedule_tick(self):
        self.timer = self.after(max(1, int(self.sim.dt * 1000)), self._tick)

    def _tick(self):
        try:
            dbs = float(self.var_dbms.get())/1000.0
            s = self.sim.step(dbs, dbs)
            self.series.append(s)
            if len(self.series) > self.max_pts:
                self.series.pop(0)
            self._update_status(s)
            self._draw_chart_series()
            self._draw_tank_level(s['level'], self.sim.high_sp, self.sim.low_sp)
            # Update wiring DPDT view (draw on wiring canvas)
            self._update_dpdt_view(s)
        except Exception:
            # Stop timer and show the error without closing the GUI
            self.stop()
            tb = traceback.format_exc()
            messagebox.showerror("Simulation Error", f"An error occurred in the timer loop:\n\n{tb}")
            return
        # Reschedule next tick
        self._schedule_tick()

    # -------------------- Chart Drawing --------------------
    def _draw_chart_axes(self):
        c = self.chart_canvas
        c.delete('all')
        # Use actual widget size if available
        try:
            c.update_idletasks()
            w = int(c.winfo_width()) or int(c['width'])
            h = int(c.winfo_height()) or int(c['height'])
        except Exception:
            w = int(c['width']); h = int(c['height'])
        self._chart_w = w
        self._chart_h = h
        ml = 56; mb = 32
        c.create_line(ml, 12, ml, h-mb, fill=self.COLOR_AXIS)
        c.create_line(ml, h-mb, w-12, h-mb, fill=self.COLOR_AXIS)
        for p in [0,20,40,60,80,100]:
            y = h - mb - p*2.6
            c.create_line(ml, y, w-12, y, fill=self.COLOR_GRID)
            c.create_text(24, y, text=f"{p}%", fill=self.COLOR_TEXT, anchor='w')
        self._draw_thresholds()

    def _draw_thresholds(self):
        c = self.chart_canvas
        w = getattr(self, "_chart_w", int(c['width']))
        h = getattr(self, "_chart_h", int(c['height']))
        ml = 56; mb = 32
        high = self.sim.high_sp; low = self.sim.low_sp
        yH = h - mb - high*2.6
        yL = h - mb - low*2.6
        # dashed lines (manual dash segments for portability)
        for y, color in [(yH, self.COLOR_MEAS), (yL, self.COLOR_PUMP)]:
            x = ml
            while x < w-12:
                c.create_line(x, y, min(x+10, w-12), y, fill=color)
                x += 16

    def _draw_chart_series(self):
        c = self.chart_canvas
        w = getattr(self, "_chart_w", int(c['width']))
        h = getattr(self, "_chart_h", int(c['height']))
        ml = 56; mb = 32
        c.delete('series')
        if not self.series:
            return

        def x_pos(i): return ml + i * ((w-ml-12)/self.max_pts)
        def y_level(v): return h - mb - v*2.6

        # Draw markers first (so movement is visible from sample #1)
        for i, s in enumerate(self.series):
            x = x_pos(i); y_true = y_level(s['level']); y_meas = y_level(s['measured'])
            c.create_oval(x-2, y_true-2, x+2, y_true+2, fill=self.COLOR_TRUE, outline='', tags='series')
            c.create_oval(x-2, y_meas-2, x+2, y_meas+2, fill=self.COLOR_MEAS, outline='', tags='series')

        # Then draw polyline segments
        last_true = None
        last_meas = None
        for i, s in enumerate(self.series):
            x = x_pos(i)
            yT = y_level(s['level'])
            yM = y_level(s['measured'])
            if last_true is not None:
                c.create_line(last_true[0], last_true[1], x, yT, fill=self.COLOR_TRUE, width=2, tags='series')
            if last_meas is not None:
                c.create_line(last_meas[0], last_meas[1], x, yM, fill=self.COLOR_MEAS, width=1, tags='series')
            last_true = (x, yT)
            last_meas = (x, yM)

        # Pump ON bands (simulate translucency with stipple)
        band_width = (w-ml-12)/self.max_pts
        for i, s in enumerate(self.series):
            if s['pump_on']:
                x = x_pos(i)
                c.create_rectangle(x, h-mb, x + band_width, h-mb-18,
                                   fill=self.COLOR_PUMP, outline='',
                                   stipple='gray50',
                                   tags='series')

    # -------------------- Tank Drawing --------------------
    def _draw_tank_static(self):
        c = self.tank_canvas
        c.delete('all')
        self.tank_rect = (80, 70, 280, 500)  # left, top, right, bottom
        c.create_rectangle(*self.tank_rect, outline='#666666', width=2)
        # labels
        c.create_text(24, 24, text='High', fill=self.COLOR_MEAS, anchor='w')
        c.create_text(24, 44, text='Low',  fill=self.COLOR_PUMP, anchor='w')

    def _draw_tank_level(self, level, high_sp, low_sp):
        c = self.tank_canvas
        l, t, r, b = self.tank_rect
        c.delete('level'); c.delete('marks'); c.delete('leveltext')
        hgt = (level/100.0) * (b - t); y = b - hgt
        c.create_rectangle(l+1, y, r-1, b-1, fill='#80d4ff', outline='', tags='level')
        # dashed markers
        def dashed(y, color):
            x = l + 2
            while x < r - 2:
                c.create_line(x, y, min(x+10, r-2), y, fill=color, tags='marks')
                x += 16
        yH = b - (high_sp/100.0) * (b - t)
        yL = b - (low_sp/100.0)  * (b - t)
        dashed(yH, self.COLOR_MEAS); dashed(yL, self.COLOR_PUMP)
        c.create_text((l+r)//2, y-12, text=f"{level:.1f}%", fill='#0f172a', tags='leveltext')

    # -------------------- DPDT visual & animation (on wiring canvas) --------------------
    def _update_dpdt_view(self, s):
        """
        Update the DPDT state graphic on the wiring canvas. If 's' contains 'coil_on' we use that,
        otherwise read current sim state. This method starts a small interpolated animation of
        the lever positions rather than snapping instantly.
        """
        coil_on = None
        if isinstance(s, dict) and 'coil_on' in s:
            coil_on = bool(s['coil_on'])
        else:
            coil_on = bool(self.sim.coil_on)
        # target position: 1.0 => NO side, 0.0 => NC side
        self.dpdt_target = 1.0 if coil_on else 0.0
        # update pump contact selection visually if var changed
        self.sim.dpdt.pump_contact = self.var_pump.get()
        # trigger animator if not running
        if not self.dpdt_animating:
            self.dpdt_animating = True
            self._animate_dpdt()

    def _animate_dpdt(self):
        # move dpdt_pos toward dpdt_target
        step = 0.16
        if abs(self.dpdt_pos - self.dpdt_target) < 0.001:
            self.dpdt_pos = self.dpdt_target
        elif self.dpdt_pos < self.dpdt_target:
            self.dpdt_pos = min(self.dpdt_pos + step, self.dpdt_target)
        else:
            self.dpdt_pos = max(self.dpdt_pos - step, self.dpdt_target)

        # Draw dynamic parts with tag 'dpdt_state' so we can refresh easily
        c = self.wiring_canvas
        c.delete('dpdt_state')

        # draw lever lines for both poles, pivoting at COM and reaching toward NC<->NO
        for pole_name in ('upper', 'lower'):
            coords = self.dpdt_coords.get(pole_name)
            if not coords:
                continue
            x_nc, y_nc = coords['nc']
            x_com, y_com = coords['com']
            x_no, y_no = coords['no']
            # target x for lever end based on dpdt_pos interpolation between nc and no
            end_x = x_nc + (x_no - x_nc) * self.dpdt_pos
            # draw the lever (pivot at COM)
            c.create_line(x_com, y_com, end_x, y_com, fill='#7b5e57', width=3, capstyle='round', tags=('dpdt_state',))
            # pivot knob
            c.create_oval(x_com-4, y_com-4, x_com+4, y_com+4, fill='#7b5e57', outline='', tags=('dpdt_state',))
            # show a filled contact circle if lever is touching (pos near 0 or 1)
            touching_nc = self.dpdt_pos <= 0.02
            touching_no = self.dpdt_pos >= 0.98
            c.create_oval(x_nc-6, y_nc-6, x_nc+6, y_nc+6,
                          outline='#666666', fill=(self.COLOR_PUMP if touching_nc else '#ffffff'), tags=('dpdt_state',))
            c.create_oval(x_no-6, y_no-6, x_no+6, y_no+6,
                          outline='#666666', fill=(self.COLOR_PUMP if touching_no else '#ffffff'), tags=('dpdt_state',))
            c.create_oval(x_com-6, y_com-6, x_com+6, y_com+6,
                          outline='#666666', fill='#ffffff', tags=('dpdt_state',))

        # Draw coil energized indicator
        coil_x, coil_y = self.dpdt_coords.get('coil', (0,0))
        coil_on = bool(self.sim.coil_on)
        c.create_rectangle(coil_x-46, coil_y-16, coil_x+46, coil_y+16,
                           outline='#666666', fill=('#ffcccb' if coil_on else '#ffffff'),
                           tags=('dpdt_state',))
        c.create_text(coil_x, coil_y, text='COIL', fill=self.COLOR_TEXT, tags=('dpdt_state',))

        # Draw wiring from pump terminal to the contact the pump is attached to.
        pump_x, pump_y = self.dpdt_coords.get('pump_term', (0,0))
        lower_coords = self.dpdt_coords.get('lower')
        if lower_coords:
            pump_contact = self.sim.dpdt.pump_contact
            contact_point = lower_coords['nc'] if pump_contact == 'NC' else lower_coords['no']
            com_point = lower_coords['com']
            pump_on = self.sim.dpdt.pump_on(self.sim.coil_on)
            wire_color = (self.COLOR_PUMP if pump_on else '#999999')
            # wire from pump terminal to chosen contact (curved via two segments for clarity)
            # pump -> contact
            c.create_line(pump_x+30, pump_y, contact_point[0]-8, contact_point[1], fill=wire_color, width=3, tags=('dpdt_state',), smooth=True)
            # COM->contact (dashed)
            c.create_line(com_point[0], com_point[1], contact_point[0], contact_point[1], fill='#bbbbbb', dash=(3,3), tags=('dpdt_state',))
            # highlight pump body border when energized
            pump_body_fill = '#ccffdd' if pump_on else '#eeeeee'
            c.create_rectangle(pump_x+10, pump_y-12, pump_x+60, pump_y+12,
                               outline='#666666', fill=pump_body_fill, tags=('dpdt_state',))
            c.create_oval(pump_x+60, pump_y-10, pump_x+80, pump_y+10,
                          outline='#666666', fill=('#bbffbb' if pump_on else '#dddddd'), tags=('dpdt_state',))
            c.create_text(pump_x+46, pump_y+32, text='Pump', fill=self.COLOR_TEXT, tags=('dpdt_state',))

        # Stop animation if we reached target, else schedule another frame
        if abs(self.dpdt_pos - self.dpdt_target) < 0.001:
            self.dpdt_animating = False
            return
        else:
            self.after(40, self._animate_dpdt)

    # -------------------- Status --------------------
    def _update_status(self, s):
        self.lbl_level.configure(text=f"Level: {s['level']:.2f}%")
        self.lbl_meas.configure(text=f"Measured: {s['measured']:.2f}%")
        self.lbl_high.configure(text=f"High: {'CLOSED' if s['high_closed'] else 'open'}")
        self.lbl_low.configure(text=f"Low: {'CLOSED' if s['low_closed'] else 'open'}")
        self.lbl_coil.configure(text=f"Coil: {'ENERGIZED' if s['coil_on'] else 'de-energized'}")
        self.lbl_pump.configure(text=f"Pump: {'ON' if s['pump_on'] else 'OFF'}")
        # LED color
        self.pump_led.itemconfig(
            self.pump_led_id,
            fill=(self.COLOR_PUMP if s['pump_on'] else '#ef4444'),
            outline=('#1f7a1f' if s['pump_on'] else '#7f1d1d')
        )
        # Ensure the dpdt visualization is in sync (starts/continues animation if required)
        self._update_dpdt_view(s)

    # -------------------- Help / How it works --------------------
    def show_help(self):
        text = (
            "How this simulation works\n"
            "----------------------------------------\n"
            "This app models a classic two-point (High/Low) level control using a DPDT relay.\n\n"
            "Layout notes:\n"
            "• Tank and Trend share the same vertical height so High/Low setpoint lines align.\n"
            "• Wiring/Relay area is below both canvases and contains the pump on the left\n"
            "  and the DPDT relay on the right; wires connect them for a continuous diagram.\n\n"
            "Refer to the labels and indicators for coil/pump state.\n"
        )
        messagebox.showinfo("Help — How it works", text)


# Entry point
if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception:
        # Catch any fatal top-level exception and keep the GUI from vanishing
        tb = traceback.format_exc()
        # Print to stderr for IDE consoles
        sys.stderr.write(tb + "\n")
        try:
            messagebox.showerror("Fatal Error", tb)
        except Exception:
            pass