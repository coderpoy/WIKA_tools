import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

def calculate_and_plot_with_extrapolation():
    # Prompt user for inputs
    ambientTemp = float(input("Enter the ambient temperature (°C): "))
    processTemp = float(input("Enter the process temperature (°C): "))

    # Original training data
    x_train = np.array([50, 75, 100, 125, 150, 175, 200])
    y_train_3fins = np.array([44, 61, 78, 95, 111, 127, 143])
    y_train_5fins = np.array([37, 44, 52, 60, 69, 77, 85])

    # Create polynomial regression models with Ridge regularization
    model_3fins = make_pipeline(PolynomialFeatures(degree=2), Ridge(alpha=1.0))
    model_5fins = make_pipeline(PolynomialFeatures(degree=2), Ridge(alpha=1.0))

    # Fit models to original data
    model_3fins.fit(x_train.reshape(-1, 1), y_train_3fins)
    model_5fins.fit(x_train.reshape(-1, 1), y_train_5fins)

    # Cooling efficiency drop per degree
    coolingEfficiencyDropPerDegree = 0.015
    adjustmentFactor = 1 + (ambientTemp - 20) * coolingEfficiencyDropPerDegree

    # Define extended range for extrapolation
    x_plot = np.linspace(25, max(225, processTemp + 25), 150).reshape(-1, 1)

    # Predict values and apply adjustment
    y_pred_3fins = model_3fins.predict(x_plot) * adjustmentFactor + (ambientTemp - 20)
    y_pred_5fins = model_5fins.predict(x_plot) * adjustmentFactor + (ambientTemp - 20)

    # Ensure predictions do not exceed x-values
    y_pred_3fins = np.minimum(y_pred_3fins, x_plot.flatten())
    y_pred_5fins = np.minimum(y_pred_5fins, x_plot.flatten())

    # Estimate temperature at process temperature
    estimatedTemp3Fins = model_3fins.predict([[processTemp]])[0] * adjustmentFactor + (ambientTemp - 20)
    estimatedTemp5Fins = model_5fins.predict([[processTemp]])[0] * adjustmentFactor + (ambientTemp - 20)

    estimatedTemp3Fins = min(estimatedTemp3Fins, processTemp)
    estimatedTemp5Fins = min(estimatedTemp5Fins, processTemp)

    # Plot predictions
    plt.figure(figsize=(12, 8))
    plt.plot(x_plot, y_pred_3fins, label=f'3 Fins - Ambient {ambientTemp}°C')
    plt.plot(x_plot, y_pred_5fins, label=f'5 Fins - Ambient {ambientTemp}°C')

    # Mark estimated temperatures
    plt.scatter([processTemp], [estimatedTemp3Fins], color='red')
    plt.text(processTemp, estimatedTemp3Fins, f'{estimatedTemp3Fins:.1f}°C', color='red')

    plt.scatter([processTemp], [estimatedTemp5Fins], color='blue')
    plt.text(processTemp, estimatedTemp5Fins, f'{estimatedTemp5Fins:.1f}°C', color='blue')

    # Plot original data for reference
    plt.plot(x_train, y_train_3fins, 'o--', label='Original 3 Fins')
    plt.plot(x_train, y_train_5fins, 'o--', label='Original 5 Fins')

    # Final plot settings
    plt.axvline(x=processTemp, color='gray', linestyle='--', label='Process Temp')
    plt.title('Extrapolated Temperature Characteristic Curve with Ambient Adjustments')
    plt.xlabel('Temperature at Measuring Point [°C]')
    plt.ylabel('Temperature at Measuring Instrument [°C]')
    plt.legend()
    plt.grid(True)
    plt.show()

# Run the function
calculate_and_plot_with_extrapolation()
