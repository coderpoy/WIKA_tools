"""
Streamlit GUI for Thermowell Simulator (V6)

This app uses the single-file thermowell_simulator module (place thermowell_simulator.py
in the same folder). It provides:
- Sidebar inputs (fluid, geometry, installation)
- Material preset selector (read-only displayed properties)
- SVG visualization embedded from the simulator output
- Numeric results and a frequency plot (f_s vs velocity with f_n line)

Run:
  python3 -m pip install -r requirements.txt
  streamlit run app.py

Notes:
- thermowell_simulator.run_from_schema expects the schema structure used here.
- This app targets Python 3+ and Streamlit.
"""
from __future__ import print_function
import streamlit as st
import matplotlib.pyplot as plt
import json

# Import simulator functions
from thermowell_simulator_Version6 import run_from_schema, list_material_presets

st.set_page_config(page_title="Thermowell Simulator V6", layout="wide")

st.title("Thermowell Simulator — V6 (Streamlit GUI)")

# Material presets for read-only display
material_presets = list_material_presets()
preset_names = sorted(material_presets.keys())

# Layout: left sidebar for inputs, main area for drawing and results
with st.sidebar:
    st.header("Material preset")
    selected_preset = st.selectbox("Material preset", preset_names, index=preset_names.index("Stainless Steel (SS316 / SS316L)") if "Stainless Steel (SS316 / SS316L)" in preset_names else 0)

    st.markdown("Material properties (read-only unless you choose 'Custom')")
    mat_info = material_presets.get(selected_preset, {})
    # Display read-only properties
    st.text("Elastic modulus E (Pa): {}".format(mat_info.get("elastic_modulus_pa")))
    st.text("Density (kg/m³): {}".format(mat_info.get("density_kg_per_m3")))
    st.text("Notes: {}".format(mat_info.get("notes", "")))

    st.markdown("---")
    st.header("Fluid properties")
    velocity = st.number_input("Fluid velocity (m/s)", value=5.0, min_value=0.0, format="%.3f")
    fluid_density = st.number_input("Fluid density (kg/m³)", value=1000.0, min_value=0.0, format="%.3f")
    viscosity = st.number_input("Fluid viscosity (Pa·s)", value=0.001, min_value=0.0, format="%.6f")

    st.markdown("---")
    st.header("Thermowell dimensions")
    immersion_length = st.number_input("Immersion length (m)", value=0.2, min_value=0.0, format="%.4f")
    root_diameter = st.number_input("Root diameter (m)", value=0.025, min_value=1e-6, format="%.5f")
    tip_diameter = st.number_input("Tip diameter (m)", value=0.012, min_value=1e-6, format="%.5f")
    bore_diameter = st.number_input("Bore diameter (m)", value=0.006, min_value=0.0, format="%.5f")
    fillet_radius = st.number_input("Fillet radius (m)", value=0.002, min_value=0.0, format="%.5f")

    st.markdown("---")
    st.header("Installation")
    support_compliance = st.number_input("Support compliance factor", value=1.0, min_value=0.0, format="%.3f")
    added_sensor_mass = st.number_input("Added sensor mass (kg)", value=0.005, min_value=0.0, format="%.6f")
    damping_ratio_input = st.text_input("Damping ratio (optional, leave blank for auto)", value="")

    # constants
    st.markdown("---")
    st.header("Constants / thresholds")
    stouhal_number = st.number_input("Strouhal number", value=0.22, min_value=0.0, format="%.4f")
    target_wfr = st.number_input("Target minimum WFR", value=2.2, min_value=0.0, format="%.3f")

    update = st.button("Run simulation")

# Build schema for simulator
# Convert damping input
try:
    damping_ratio = None if damping_ratio_input.strip() == "" else float(damping_ratio_input)
except Exception:
    damping_ratio = None

schema = {
    "thermowell_simulator": {
        "inputs": {
            "fluid_properties": {
                "velocity_m_per_s": float(velocity),
                "density_kg_per_m3": float(fluid_density),
                "viscosity_pa_s": float(viscosity)
            },
            "thermowell_dimensions": {
                "immersion_length_m": float(immersion_length),
                "root_diameter_m": float(root_diameter),
                "tip_diameter_m": float(tip_diameter),
                "bore_diameter_m": float(bore_diameter),
                "fillet_radius_m": float(fillet_radius)
            },
            "material_properties": {
                # Pass selected preset; if 'Custom', the library entry is None and will require overrides.
                "material_preset": selected_preset
            },
            "installation": {
                "support_compliance_factor": float(support_compliance),
                "added_sensor_mass_kg": float(added_sensor_mass),
                "damping_ratio": damping_ratio
            }
        },
        "constants": {
            "strouhal_number": float(stouhal_number),
            "target_wfr": float(target_wfr)
        }
    }
}

# If the selected preset is 'Custom (enter below)', allow user to input E and density manually
if selected_preset == "Custom (enter below)":
    st.sidebar.markdown("Custom material properties")
    custom_E = st.sidebar.number_input("Elastic modulus E (Pa)", value=2.0e11, format="%.6e")
    custom_rho = st.sidebar.number_input("Material density (kg/m³)", value=7850.0, format="%.3f")
    schema["thermowell_simulator"]["inputs"]["material_properties"].update({
        "elastic_modulus_pa": float(custom_E),
        "density_kg_per_m3": float(custom_rho)
    })

# Run automatically on update or first load
if update or True:
    # Call simulator
    try:
        results = run_from_schema(schema)
    except Exception as exc:
        st.error("Simulation error: {}".format(exc))
        st.stop()

    # Main layout: left (drawing + material), right (results + plot)
    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.subheader("Thermowell drawing (illustrative SVG)")
        svg = results.get("svg_drawing", "")
        # Embed SVG safely using components.html
        if svg:
            # Wrap in simple HTML to ensure proper rendering and sizing
            html = '<div style="max-width:800px;">{svg}</div>'.format(svg=svg)
            st.components.v1.html(html, height=320, scrolling=False)
        else:
            st.write("No SVG available.")

        st.markdown("Material used (read-only):")
        mat_used = results.get("material_used", {})
        st.text("Preset: {}".format(mat_used.get("preset")))
        st.text("Elastic modulus E (Pa): {}".format(mat_used.get("elastic_modulus_pa")))
        st.text("Density (kg/m³): {}".format(mat_used.get("density_kg_per_m3")))
        st.text("Notes: {}".format(mat_used.get("notes", "")))

    with right_col:
        st.subheader("Numeric results")
        st.json({
            "natural_frequency_hz": results.get("natural_frequency_hz"),
            "vortex_shedding_frequency_hz": results.get("vortex_shedding_frequency_hz"),
            "wake_frequency_ratio": results.get("wake_frequency_ratio"),
            "resonance_risk": results.get("resonance_risk"),
            "scruton_number": results.get("scruton_number"),
            "stress_amplification_factor": results.get("stress_amplification_factor"),
            "intermediates": results.get("intermediates")
        }, expanded=False)

        # Frequency plot: sweep velocity and plot f_s, show f_n horizontal
        st.markdown("Frequency plot — f_s (vortex shedding) vs velocity and f_n")
        v_val = float(velocity)
        v_max = max(v_val * 2.0, 0.1)
        velocities = [v_max * i / 100.0 for i in range(101)]
        st_val = float(stouhal_number)
        tip_d = float(tip_diameter)
        fs_vals = [st_val * vv / tip_d for vv in velocities]
        fn_val = float(results.get("natural_frequency_hz", 0.0))

        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.plot(velocities, fs_vals, label="f_s (vortex shedding)", color="#d62728")
        ax.axhline(fn_val, color="#1f77b4", linestyle="--", label="f_n = {:.3f} Hz".format(fn_val))
        ax.set_xlabel("Velocity (m/s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

        # Risk banner
        if results.get("resonance_risk"):
            st.error("Resonance risk: WFR = {:.3f} < target {:.3f}".format(results.get("wake_frequency_ratio"), target_wfr))
        else:
            st.success("No immediate resonance risk: WFR = {:.3f} ≥ target {:.3f}".format(results.get("wake_frequency_ratio"), target_wfr))

    # Optional: provide JSON download of results
    st.markdown("---")
    if st.button("Download results (JSON)"):
        st.download_button(label="Download JSON", data=json.dumps(results, indent=2), file_name="thermowell_results.json", mime="application/json")