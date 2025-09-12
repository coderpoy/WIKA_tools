import tkinter as tk
from tkinter import ttk
from operator import itemgetter

# Define the product database
product_data = [
    {"Name": "Bypass Level Indicator", "Features": ["Visual indication", "Magnetic float"],
     "Applications": ["Chemical", "Oil & gas"]},
    {"Name": "Float Switches (Single and Multipoint)", "Features": ["Multi-point measurement", "Cost-effective"],
     "Applications": ["Water treatment", "HVAC"]},
    {"Name": "Glass Gauges", "Features": ["Direct level measurement", "Robust design"],
     "Applications": ["Boilers", "Oil & gas"]},
    {"Name": "Diaphragm Seal Systems (DP Level)", "Features": ["High-pressure compatibility", "Corrosion resistance"],
     "Applications": ["Chemical", "Pharmaceutical"]},
    # Add more products here
]

# Extract unique features and applications from the product database
all_features = sorted({feature for product in product_data for feature in product["Features"]})
all_applications = sorted({app for product in product_data for app in product["Applications"]})


def recommend_products():
    # Get selected features and applications
    selected_feature = feature_var.get()
    selected_application = application_var.get()

    # Calculate scores for each product
    scores = []
    for product in product_data:
        score = 0
        if selected_feature in product["Features"]:
            score += 1
        if selected_application in product["Applications"]:
            score += 1
        scores.append((product["Name"], score))

    # Sort products by score (descending) and take the top 3
    top_products = sorted(scores, key=itemgetter(1), reverse=True)[:3]

    # Display recommendations in the output window
    output_text = "Top 3 Product Recommendations:\n"
    for product, score in top_products:
        output_text += f"- {product} (Score: {score})\n"
    result_label.config(text=output_text)


# Create the main window
window = tk.Tk()
window.title("Product Recommendation Tool")
window.geometry("400x300")

# Dropdown for selecting a key feature
tk.Label(window, text="Select a Key Feature:").pack(pady=5)
feature_var = tk.StringVar()
feature_dropdown = ttk.Combobox(window, textvariable=feature_var, values=all_features, state="readonly")
feature_dropdown.pack(pady=5)

# Dropdown for selecting an application
tk.Label(window, text="Select an Application:").pack(pady=5)
application_var = tk.StringVar()
application_dropdown = ttk.Combobox(window, textvariable=application_var, values=all_applications, state="readonly")
application_dropdown.pack(pady=5)

# Button to recommend products
recommend_button = tk.Button(window, text="Get Recommendations", command=recommend_products)
recommend_button.pack(pady=10)

# Label to display the results
result_label = tk.Label(window, text="", justify="left", wraplength=350)
result_label.pack(pady=10)

# Run the main event loop
window.mainloop()
