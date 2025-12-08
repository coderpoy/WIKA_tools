import numpy as np
import matplotlib.pyplot as plt
# comment

def calculate_and_plot_with_linear_model():
    # Variables for linear model coefficients
    intercept3Fins = 11.64285714
    slope3Fins = 0.66
    intercept5Fins = 20.03571429
    slope5Fins = 0.324285714

    # Fine-tuned x and y value arrays (new interpolated data)
    xValues = np.array([50, 75, 100, 125, 150, 175, 200])
    yValues3Fins_Original = np.array([44, 61, 78, 95, 111, 127, 143])
    yValues5Fins_Original = np.array([37, 44, 52, 60, 69, 77, 85])

    # Input ambient temperature
    ambientTemp = float(input("Enter the ambient temperature (°C): "))

    # Input temperature at the measuring point
    measuringPointTemp = float(input("Enter the temperature at the measuring point (°C): "))

    # Cooling efficiency drop per degree
    coolingEfficiencyDropPerDegree = 0.015

    # Adjust the coefficients based on the cooling efficiency drop
    adjustmentFactor = 1 + (ambientTemp - 20) * coolingEfficiencyDropPerDegree

    slope3Fins_Adjusted = slope3Fins * adjustmentFactor
    intercept3Fins_Adjusted = intercept3Fins * adjustmentFactor

    slope5Fins_Adjusted = slope5Fins * adjustmentFactor
    intercept5Fins_Adjusted = intercept5Fins * adjustmentFactor

    # Calculate linear model values based on the new ambient temperature
    yValues3Fins_Linear = slope3Fins_Adjusted * xValues + intercept3Fins_Adjusted + (ambientTemp - 20)
    yValues5Fins_Linear = slope5Fins_Adjusted * xValues + intercept5Fins_Adjusted + (ambientTemp - 20)

    # Ensure y-value is not greater than x-value
    yValues3Fins_Linear = np.minimum(yValues3Fins_Linear, xValues)
    yValues5Fins_Linear = np.minimum(yValues5Fins_Linear, xValues)

    # Estimate temperature at the measuring instrument
    estimatedTemp3Fins = slope3Fins_Adjusted * measuringPointTemp + intercept3Fins_Adjusted + (ambientTemp - 20)
    estimatedTemp5Fins = slope5Fins_Adjusted * measuringPointTemp + intercept5Fins_Adjusted + (ambientTemp - 20)

    # Ensure estimated temperature is not greater than the measuring point temperature
    estimatedTemp3Fins = min(estimatedTemp3Fins, measuringPointTemp)
    estimatedTemp5Fins = min(estimatedTemp5Fins, measuringPointTemp)

    # Plotting the data
    plt.figure(figsize=(10, 6))
    plt.plot(xValues, yValues3Fins_Original, 'o-', label='Original 3 Fins')
    plt.plot(xValues, yValues5Fins_Original, 'o-', label='Original 5 Fins')
    plt.plot(xValues, yValues3Fins_Linear, 's-', label='Linear Model 3 Fins')
    plt.plot(xValues, yValues5Fins_Linear, 's-', label='Linear Model 5 Fins')

    # Label the estimated temperatures on the graph
    plt.scatter([measuringPointTemp], [estimatedTemp3Fins], color='red')
    plt.text(measuringPointTemp, estimatedTemp3Fins, f'{estimatedTemp3Fins:.2f}°C', color='red')

    plt.scatter([measuringPointTemp], [estimatedTemp5Fins], color='blue')
    plt.text(measuringPointTemp, estimatedTemp5Fins, f'{estimatedTemp5Fins:.2f}°C', color='blue')

    # Add vertical line at the measuring point temperature
    plt.axvline(x=measuringPointTemp, color='gray', linestyle='--', label='Measuring Point Temp')

    plt.title(f'Temperature Characteristic Curve (Line Graph) - Ambient Temp: {ambientTemp}°C')
    plt.xlabel('Temperature at Measuring Point [°C]')
    plt.ylabel('Temperature at Measuring Instrument [°C]')
    plt.legend()
    plt.grid(True)
    plt.show()


# Execute the function
calculate_and_plot_with_linear_model()



