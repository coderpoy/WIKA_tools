import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons, TextBox

# Constants for SS316/L material
E_SS316L = 193e9  # Modulus of Elasticity (Pa) for SS316/L


# Function to calculate natural frequency
def natural_frequency(D, L, I, A, E, rho):
    return (1 / (2 * np.pi)) * np.sqrt((E * I) / (rho * A * L ** 4))


# Function to calculate vortex shedding frequency
def vortex_shedding_frequency(D, V, St):
    return (St * V) / D


# Function to update the plot and scorecard
def update(val):
    # Convert the input values from mm to m
    root_diameter = slider_root_diameter.val / 1000  # Root diameter in meters
    tip_diameter = slider_tip_diameter.val / 1000  # Tip diameter in meters
    insertion_length = slider_insertion_length.val / 1000  # Insertion length in meters

    # User input for flow velocity, density, and Strouhal number
    V = float(textbox_velocity.text)  # Flow velocity (m/s)
    rho = float(textbox_density.text)  # Fluid density (kg/m³)
    E = E_SS316L  # Material modulus of elasticity (Pa)
    St = float(textbox_strouhal.text)  # Strouhal number (dimensionless)

    thermowell_type = radio_thermowell_type.value_selected

    if thermowell_type == 'Straight':
        I = (np.pi / 64) * root_diameter ** 4  # Moment of inertia for a circular cross-section
        A = (np.pi / 4) * root_diameter ** 2  # Cross-sectional area
        fn = natural_frequency(root_diameter, insertion_length, I, A, E, rho)  # Natural frequency
        fs = vortex_shedding_frequency(root_diameter, V, St)  # Vortex shedding frequency
    elif thermowell_type == 'Stepped':
        D_avg = (2 * root_diameter + tip_diameter) / 3  # Average diameter for stepped thermowell
        I = (np.pi / 64) * D_avg ** 4  # Moment of inertia for the average diameter
        A = (np.pi / 4) * D_avg ** 2  # Cross-sectional area for the average diameter
        fn = natural_frequency(D_avg, insertion_length, I, A, E, rho)  # Natural frequency
        fs = vortex_shedding_frequency(tip_diameter, V, St)  # Vortex shedding frequency at tip diameter
    elif thermowell_type == 'Tapered':
        I = (np.pi / 64) * root_diameter ** 4  # Moment of inertia for the root diameter
        A = (np.pi / 4) * root_diameter ** 2  # Cross-sectional area for the root diameter
        fn = natural_frequency(root_diameter, insertion_length, I, A, E, rho)  # Natural frequency
        fs = vortex_shedding_frequency(tip_diameter, V, St)  # Vortex shedding frequency at tip diameter

    # Frequency ratio
    frequency_ratio = fs / fn

    # Update scorecard data
    ax_scorecard.clear()
    ax_scorecard.axis('off')
    scorecard_text = (
        f"Natural Frequency: {fn:.2f} Hz\n"
        f"Vortex Shedding Frequency: {fs:.2f} Hz\n"
        f"Frequency Ratio: {frequency_ratio:.2f}\n\n"
        f"Input Data:\n"
        f"Flow Velocity: {V} m/s\n"
        f"Fluid Density: {rho} kg/m³\n"
        f"Modulus of Elasticity: {E / 1e9} GPa\n"
        f"Strouhal Number: {St}"
    )
    ax_scorecard.text(0.5, 0.5, scorecard_text, horizontalalignment='center', verticalalignment='center', fontsize=12)

    # Draw thermowell body
    ax_thermowell.clear()
    ax_thermowell.set_xlabel("Width (mm)")
    ax_thermowell.set_ylabel("Insertion Length (mm)")

    if thermowell_type == 'Straight':
        ax_thermowell.plot([0, 0], [0, insertion_length * 1000], 'k-')
        ax_thermowell.plot([root_diameter * 500, root_diameter * 500], [0, insertion_length * 1000], 'k-')
        ax_thermowell.plot([-root_diameter * 500, -root_diameter * 500], [0, insertion_length * 1000], 'k-')
    elif thermowell_type == 'Stepped':
        ax_thermowell.plot([0, 0], [0, insertion_length * 1000], 'k-')
        ax_thermowell.plot([root_diameter * 500, root_diameter * 500], [0, insertion_length * 500], 'k-')
        ax_thermowell.plot([tip_diameter * 500, tip_diameter * 500], [insertion_length * 500, insertion_length * 1000],
                           'k-')
        ax_thermowell.plot([-root_diameter * 500, -root_diameter * 500], [0, insertion_length * 500], 'k-')
        ax_thermowell.plot([-tip_diameter * 500, -tip_diameter * 500],
                           [insertion_length * 500, insertion_length * 1000], 'k-')
    elif thermowell_type == 'Tapered':
        ax_thermowell.plot([0, 0], [0, insertion_length * 1000], 'k-')
        ax_thermowell.plot([root_diameter * 500, tip_diameter * 500], [0, insertion_length * 1000], 'k-')
        ax_thermowell.plot([-root_diameter * 500, -tip_diameter * 500], [0, insertion_length * 1000], 'k-')

    fig.canvas.draw_idle()


# Create the figure and axes
fig = plt.figure("Thermowell Structural Adjustments", figsize=(12, 8))
ax_scorecard = fig.add_subplot(121)
ax_thermowell = fig.add_subplot(122)

plt.subplots_adjust(left=0.3, bottom=0.35)

# Initial plot data
initial_root_diameter = 20  # in mm
initial_tip_diameter = 20  # in mm
initial_insertion_length = 300  # in mm

# Create sliders for adjusting parameters
ax_root_diameter_slider = plt.axes([0.25, 0.25, 0.4, 0.03])
ax_tip_diameter_slider = plt.axes([0.25, 0.20, 0.4, 0.03])
ax_insertion_length_slider = plt.axes([0.25, 0.15, 0.4, 0.03])

slider_root_diameter = Slider(ax_root_diameter_slider, 'Root Diameter (mm)', 10, 50, valinit=initial_root_diameter)
slider_tip_diameter = Slider(ax_tip_diameter_slider, 'Tip Diameter (mm)', 10, 50, valinit=initial_tip_diameter)
slider_insertion_length = Slider(ax_insertion_length_slider, 'Insertion Length (mm)', 100, 1000,
                                 valinit=initial_insertion_length)

# Create text boxes for manual input
ax_velocity_textbox = plt.axes([0.025, 0.4, 0.2, 0.03])
textbox_velocity = TextBox(ax_velocity_textbox, 'Flow Velocity (m/s)', initial='5')

ax_density_textbox = plt.axes([0.025, 0.35, 0.2, 0.03])
textbox_density = TextBox(ax_density_textbox, 'Fluid Density (kg/m³)', initial='1000')

ax_strouhal_textbox = plt.axes([0.025, 0.3, 0.2, 0.03])
textbox_strouhal = TextBox(ax_strouhal_textbox, 'Strouhal Number', initial='0.2')

# Create radio buttons for selecting thermowell type
ax_thermowell_type = plt.axes([0.025, 0.5, 0.2, 0.15])
radio_thermowell_type = RadioButtons(ax_thermowell_type, ('Straight', 'Stepped', 'Tapered'))

# Update slider value from textbox
def update_slider_from_textbox(textbox, slider):
    try:
        value = float(textbox.text)
        slider.set_val(value)
    except ValueError:
        pass

textbox_velocity.on_submit(lambda text: update_slider_from_textbox(textbox_velocity, slider_root_diameter))
textbox_density.on_submit(lambda text: update_slider_from_textbox(textbox_density, slider_root_diameter))
textbox_strouhal.on_submit(lambda text: update_slider_from_textbox(textbox_strouhal, slider_root_diameter))

# Register the update function for the sliders and radio buttons
slider_root_diameter.on_changed(update)
slider_tip_diameter.on_changed(update)
slider_insertion_length.on_changed(update)
radio_thermowell_type.on_clicked(update)

# Initialize the plot
update(None)

plt.show()
