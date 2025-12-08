import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
import numpy as np

# Material properties dictionary (density in kg/m³, specific heat in J/kg·K)
material_properties = {
    "Stainless Steel": {"density": 8000, "specific_heat": 500},
    "Inconel": {"density": 8470, "specific_heat": 435},
    "Copper": {"density": 8960, "specific_heat": 385},
    "Aluminum": {"density": 2700, "specific_heat": 900}
}

# Sensor types and their estimated time constants (in seconds)
sensor_time_constants = {
    "RTD - Thin Film": 2,
    "RTD - Wire Wound": 5,
    "Thermocouple": 1
}

# Fluid properties for WATER and AIR at 25°C
fluid_options = {
    "WATER": {
        "density": 997,
        "viscosity": 0.00089,
        "thermal_conductivity": 0.606,
        "prandtl": 6.2
    },
    "AIR": {
        "density": 1.184,
        "viscosity": 1.849e-5,
        "thermal_conductivity": 0.0262,
        "prandtl": 0.71
    }
}

def show_explanation():
    explanation = (
        "Time Constants Explained:\n"
        "t₀.₅: Time to reach 50% of the process temperature.\n"
        "t₀.₆₃: Time to reach 63.2% (1 time constant τ).\n"
        "t₀.₉: Time to reach 90% of the process temperature.\n\n"
        "These are standard benchmarks for evaluating thermal response speed."
    )
    messagebox.showinfo("Response Time Explanation", explanation)

def calculate_response_time():
    material = material_var.get()
    geometry = geometry_var.get()
    D_r = float(entry_root_diameter.get()) / 1000
    D_t = float(entry_tip_diameter.get()) / 1000
    t = float(entry_tip_thickness.get()) / 1000
    D_b = float(entry_bore_diameter.get()) / 1000
    sensor_diameter = float(entry_sensor_diameter.get()) / 1000
    sensor_material = sensor_material_var.get()
    sensor_type = sensor_type_var.get()
    T_process = float(entry_process_temp.get())
    L = float(entry_immersion_length.get()) / 1000
    velocity = float(entry_velocity.get())
    fluid = fluid_var.get()

    rho = fluid_options[fluid]["density"]
    mu = fluid_options[fluid]["viscosity"]
    k = fluid_options[fluid]["thermal_conductivity"]
    Pr = fluid_options[fluid]["prandtl"]

    Re = rho * velocity * D_t / mu
    Nu = 0.023 * (Re ** 0.8) * (Pr ** 0.4)
    h = Nu * k / D_t

    V_tw = np.pi * ((D_t**2 - D_b**2) / 4) * t
    m_tw = material_properties[material]["density"] * V_tw
    c_tw = material_properties[material]["specific_heat"]
    A_tw = np.pi * D_t * t

    tau_tw = m_tw * c_tw / (h * A_tw)
    tau_sensor = sensor_time_constants[sensor_type]
    tau_total = tau_tw + tau_sensor

    time = np.linspace(0, 300, 3000)
    T_sensor = T_process * (1 - np.exp(-time / tau_total))

    t_50 = -tau_total * np.log(1 - 0.5)
    t_63 = tau_total
    t_90 = -tau_total * np.log(1 - 0.9)

    T_50 = T_process * 0.5
    T_63 = T_process * 0.632
    T_90 = T_process * 0.9

    plt.figure(figsize=(8, 5))
    plt.plot(time, [T_process]*len(time), label="Process Temperature", color='blue')
    plt.plot(time, T_sensor, label="Sensor Temperature", linestyle='--', color='orange')
    plt.plot(t_50, T_50, 'go', label=f"t₀.₅ ≈ {t_50:.2f}s")
    plt.plot(t_63, T_63, 'mo', label=f"t₀.₆₃ ≈ {t_63:.2f}s")
    plt.plot(t_90, T_90, 'ro', label=f"t₀.₉ ≈ {t_90:.2f}s")
    plt.axvline(t_50, color='green', linestyle=':')
    plt.axvline(t_63, color='purple', linestyle=':')
    plt.axvline(t_90, color='red', linestyle=':')

    plt.text(t_50, T_50, f"{t_50:.1f}s", color='green', ha='left', va='bottom')
    plt.text(t_63, T_63, f"{t_63:.1f}s", color='purple', ha='left', va='bottom')
    plt.text(t_90, T_90, f"{t_90:.1f}s", color='red', ha='left', va='bottom')

    plt.xlabel("Time (s)")
    plt.ylabel("Temperature (°C)")
    plt.title("Thermowell Response Time Simulation")
    plt.legend()
    plt.grid(True)
    plt.xlim(0, t_90 * 1.5)
    plt.tight_layout()
    plt.show()

    result_label.config(
        text=(
            f"Time Constant (τ): {tau_total:.2f} s\n"
            f"t₀.₅ (50%): {t_50:.2f} s\n"
            f"t₀.₆₃ (63.2%): {t_63:.2f} s\n"
            f"t₀.₉ (90%): {t_90:.2f} s"
        )
    )

    disclaimer_label.config(
        text=(
            "Disclaimer: This simulation is based on standard engineering assumptions and simplified models.\n"
            "It is intended for estimation purposes only and does not replace laboratory testing.\n"
            "For process-critical applications, response time must be validated experimentally as per\n"
            "VDI/VDE 3522, IEC 60751, ASTM E644, and ASTM E839 standards."
        )
    )

root = tk.Tk()
root.title("Thermowell Response Time Simulator")

ttk.Label(root, text="Thermowell Material:").grid(row=0, column=0)
material_var = ttk.Combobox(root, values=list(material_properties.keys()))
material_var.grid(row=0, column=1)
material_var.set("Stainless Steel")

ttk.Label(root, text="Geometry:").grid(row=1, column=0)
geometry_var = ttk.Combobox(root, values=["Straight", "Tapered"])
geometry_var.grid(row=1, column=1)
geometry_var.set("Straight")

ttk.Label(root, text="Root Diameter (mm):").grid(row=2, column=0)
entry_root_diameter = ttk.Entry(root)
entry_root_diameter.grid(row=2, column=1)

ttk.Label(root, text="Tip Diameter (mm):").grid(row=3, column=0)
entry_tip_diameter = ttk.Entry(root)
entry_tip_diameter.grid(row=3, column=1)

ttk.Label(root, text="Tip Thickness (mm):").grid(row=4, column=0)
entry_tip_thickness = ttk.Entry(root)
entry_tip_thickness.grid(row=4, column=1)

ttk.Label(root, text="Bore Diameter (mm):").grid(row=5, column=0)
entry_bore_diameter = ttk.Entry(root)
entry_bore_diameter.grid(row=5, column=1)

ttk.Label(root, text="Sensor Diameter (mm):").grid(row=6, column=0)
entry_sensor_diameter = ttk.Entry(root)
entry_sensor_diameter.grid(row=6, column=1)

ttk.Label(root, text="Sensor Material:").grid(row=7, column=0)
sensor_material_var = ttk.Combobox(root, values=list(material_properties.keys()))
sensor_material_var.grid(row=7, column=1)
sensor_material_var.set("Copper")

ttk.Label(root, text="Sensor Type:").grid(row=8, column=0)
sensor_type_var = ttk.Combobox(root, values=list(sensor_time_constants.keys()))
sensor_type_var.grid(row=8, column=1)
sensor_type_var.set("RTD - Thin Film")

ttk.Label(root, text="Process Temperature (°C):").grid(row=9, column=0)
entry_process_temp = ttk.Entry(root)
entry_process_temp.grid(row=9, column=1)
entry_process_temp.insert(0, "100")

ttk.Label(root, text="Immersion Length (mm):").grid(row=10, column=0)
entry_immersion_length = ttk.Entry(root)
entry_immersion_length.grid(row=10, column=1)

ttk.Label(root, text="Flow Velocity (m/s):").grid(row=11, column=0)
entry_velocity = ttk.Entry(root)
entry_velocity.grid(row=11, column=1)
entry_velocity.insert(0, "1.0")

ttk.Label(root, text="Fluid:").grid(row=12, column=0)
fluid_var = ttk.Combobox(root, values=list(fluid_options.keys()))
fluid_var.grid(row=12, column=1)
fluid_var.set("WATER")

ttk.Button(root, text="Simulate", command=calculate_response_time).grid(row=13, column=0, columnspan=2, pady=10)
ttk.Button(root, text="Explain Response Times", command=show_explanation).grid(row=14, column=0, columnspan=2, pady=5)

result_label = ttk.Label(root, text="")
result_label.grid(row=15, column=0, columnspan=2)

disclaimer_label = ttk.Label(root, text="", foreground="gray", wraplength=500, justify="left")
disclaimer_label.grid(row=16, column=0, columnspan=2, pady=(10, 0))

root.mainloop()

