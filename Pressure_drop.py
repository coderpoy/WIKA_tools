
import streamlit as st
import math

st.title("Pressure Drop Calculator (Darcy-Weisbach)")

st.markdown("This tool calculates pressure drop in a pipe using the Darcy-Weisbach equation.")

# Input fields
D = st.number_input("Pipe Diameter (m)", value=0.05, format="%.4f")
L = st.number_input("Pipe Length (m)", value=10.0, format="%.2f")
Q = st.number_input("Volumetric Flow Rate (m³/s)", value=0.002, format="%.4f")
rho = st.number_input("Fluid Density (kg/m³)", value=1000, format="%.1f")
mu = st.number_input("Dynamic Viscosity (Pa·s)", value=0.001, format="%.5f")
epsilon = st.number_input("Pipe Roughness (m)", value=0.00015, format="%.5f")

# Calculations
if D > 0 and Q > 0 and mu > 0:
    area = math.pi * (D / 2) ** 2
    velocity = Q / area
    Re = (rho * velocity * D) / mu

    if Re > 4000:
        f = 0.25 / (math.log10((epsilon / (3.7 * D)) + (5.74 / Re**0.9)))**2
    else:
        f = 64 / Re

    delta_P = f * (L / D) * (rho * velocity**2 / 2)

    st.subheader("Results")
    st.write(f"**Reynolds Number:** {Re:.2f}")
    st.write(f"**Friction Factor:** {f:.5f}")
    st.write(f"**Pressure Drop:** {delta_P:.2f} Pa")
else:
    st.warning("Please enter valid positive values for all inputs.")
