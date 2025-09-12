import tkinter as tk
from tkinter import messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class InventorySimulationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Calculation and Simulation Tool")

        # Input for monthly consumption (now a large text area)
        tk.Label(root,
                 text="Enter monthly consumption quantities (separate values with spaces, commas, or newlines):").grid(
            row=0, column=0)
        self.entry_consumptions = tk.Text(root, height=10, width=50)  # Text box to paste data
        self.entry_consumptions.grid(row=0, column=1)

        # Input fields for lead time, service level, and base safety stock percentage
        tk.Label(root, text="Enter lead time in weeks:").grid(row=12, column=0)
        self.entry_lead_time = tk.Entry(root)
        self.entry_lead_time.grid(row=12, column=1)

        tk.Label(root, text="Enter the service level factor (Z):").grid(row=13, column=0)
        self.entry_z_factor = tk.Entry(root)
        self.entry_z_factor.grid(row=13, column=1)

        # Calculate button
        calculate_button = tk.Button(root, text="Calculate", command=self.calculate_inventory)
        calculate_button.grid(row=14, column=0, columnspan=2)

        # Reset button
        reset_button = tk.Button(root, text="Reset", command=self.reset_inputs)
        reset_button.grid(row=15, column=0, columnspan=2)

        # Output display
        self.output_text = tk.StringVar()
        self.output_label = tk.Label(root, textvariable=self.output_text, justify=tk.LEFT)
        self.output_label.grid(row=16, column=0, columnspan=2)

        # Initialize simulation window
        self.simulation_window = None

    def calculate_inventory(self):
        try:
            # Collect and process input from the text area
            consumptions_text = self.entry_consumptions.get("1.0", tk.END).strip()
            if consumptions_text == "":
                raise ValueError("No consumption data entered.")
            # Convert text into a list of floats
            monthly_consumptions = [float(x) for x in consumptions_text.replace(",", " ").split()]

            # Ensure there's some data entered
            if len(monthly_consumptions) == 0:
                raise ValueError("Please enter valid consumption quantities.")

            # Lead time and Z factor
            lead_time_weeks = float(self.entry_lead_time.get())
            z_factor = float(self.entry_z_factor.get())

            # Perform calculations
            avg_consumption = np.mean(monthly_consumptions)
            std_dev = np.std(monthly_consumptions)
            base_safety_stock = 0.1 * avg_consumption  # 10% of average consumption
            safety_stock = z_factor * std_dev + base_safety_stock
            lead_time_months = lead_time_weeks / 4.33
            min_inventory_level = safety_stock + avg_consumption * lead_time_months
            max_inventory_level = min_inventory_level + avg_consumption

            reorder_quantity = max_inventory_level

            forecasted_reorder_frequency_weeks = (reorder_quantity / avg_consumption) * 4.33

            # Display results
            self.output_text.set(f"Average Consumption: {avg_consumption:.2f}\n"
                                 f"Standard Deviation: {std_dev:.2f}\n"
                                 f"Base Safety Stock (10% of Avg): {base_safety_stock:.2f}\n"
                                 f"Safety Stock: {safety_stock:.2f}\n"
                                 f"Minimum Inventory Level: {min_inventory_level:.2f}\n"
                                 f"Maximum Inventory Level: {max_inventory_level:.2f}\n"
                                 f"Forecasted Reorder Frequency (weeks): {forecasted_reorder_frequency_weeks:.2f}")

            # Show simulation window
            self.show_simulation_window(avg_consumption, min_inventory_level, max_inventory_level, safety_stock)

            # Plot monthly consumption trend
            self.plot_consumption(monthly_consumptions, avg_consumption)

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))

    def plot_consumption(self, monthly_consumptions, avg_consumption):
        plt.figure(figsize=(10, 5))
        plt.plot(monthly_consumptions, marker='o', label='Monthly Consumption', color='blue')
        plt.axhline(y=avg_consumption, color='red', linestyle='--', label=f'Average Consumption: {avg_consumption:.2f}')
        plt.title('Monthly Consumption Trend')
        plt.xlabel('Month')
        plt.ylabel('Consumption')
        plt.xticks(range(len(monthly_consumptions)), [f'M {i + 1}' for i in range(len(monthly_consumptions))])
        plt.legend()
        plt.grid()
        plt.show()

    def show_simulation_window(self, avg_consumption, min_inventory_level, max_inventory_level, safety_stock):
        if self.simulation_window:
            self.simulation_window.destroy()

        self.simulation_window = tk.Toplevel(self.root)
        self.simulation_window.title("Dynamic Simulation")

        tk.Label(self.simulation_window, text="Adjust Reorder Quantity:").pack()
        reorder_slider = tk.Scale(self.simulation_window, from_=min_inventory_level, to=max_inventory_level,
                                  orient=tk.HORIZONTAL, resolution=1, length=400,
                                  command=lambda val: self.update_simulation(float(val), avg_consumption, safety_stock))
        reorder_slider.set(max_inventory_level)
        reorder_slider.pack()

        tk.Label(self.simulation_window, text="Adjust Lead Time (weeks):").pack()
        lead_time_slider = tk.Scale(self.simulation_window, from_=1, to=12, orient=tk.HORIZONTAL, resolution=0.1,
                                    length=400,
                                    command=lambda val: self.update_simulation(reorder_slider.get(), avg_consumption,
                                                                               safety_stock, float(val)))
        lead_time_slider.set(4.33)
        lead_time_slider.pack()

        self.simulation_output = tk.StringVar()
        tk.Label(self.simulation_window, textvariable=self.simulation_output, justify=tk.LEFT).pack()

        self.update_simulation(reorder_slider.get(), avg_consumption, safety_stock, lead_time_slider.get())

    def update_simulation(self, reorder_qty, avg_consumption, safety_stock, lead_time_weeks=4.33):
        lead_time_months = lead_time_weeks / 4.33
        min_inventory_level = safety_stock + avg_consumption * lead_time_months
        max_inventory_level = min_inventory_level + avg_consumption

        forecasted_reorder_frequency_weeks = (reorder_qty / avg_consumption) * 4.33

        self.simulation_output.set(f"Simulated Reorder Quantity: {reorder_qty:.2f}\n"
                                   f"Simulated Lead Time (weeks): {lead_time_weeks:.2f}\n"
                                   f"Adjusted Minimum Inventory Level: {min_inventory_level:.2f}\n"
                                   f"Adjusted Maximum Inventory Level: {max_inventory_level:.2f}\n"
                                   f"Forecasted Reorder Frequency (weeks): {forecasted_reorder_frequency_weeks:.2f}")

    def reset_inputs(self):
        self.entry_consumptions.delete(1.0, tk.END)
        self.entry_lead_time.delete(0, tk.END)
        self.entry_z_factor.delete(0, tk.END)
        self.output_text.set("")
        if self.simulation_window:
            self.simulation_window.destroy()


# Run the application
root = tk.Tk()
app = InventorySimulationApp(root)
root.mainloop()
