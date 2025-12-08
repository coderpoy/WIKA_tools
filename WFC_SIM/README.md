```markdown
# Thermowell Simulator — Streamlit demo

Files included:
- thermowell_simulator.py — the calculation engine implementing your schema
- app.py — Streamlit GUI with illustrative thermowell drawing and results
- requirements.txt — Python dependencies

How to run:
1. Create a virtual environment (recommended) and install dependencies:
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt

2. Start the GUI:
   streamlit run app.py

What you'll see:
- Left: an illustrative SVG drawing of a thermowell with labels for immersion length, root Ø, tip Ø, bore Ø and fillet radius.
- Right: computed outputs (natural frequency, vortex-shedding frequency, wake frequency ratio, Scruton number, stress amplification factor) and a small plot of f_s (vs velocity) with f_n shown.

Next steps I can do (pick any):
- Replace the empirical tip-mass correction with a full eigenvalue solution for cantilever + tip mass.
- Add hydrodynamic added mass and ASME-recommended corrections.
- Improve the SVG drawing to show tapering geometry precisely and interactive dimension dragging.
- Export reports (CSV/PDF) and add parameter sweep mode.

Tell me which next step you'd like and I will implement it.
```