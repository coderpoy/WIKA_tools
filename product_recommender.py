import streamlit as st
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

def recommend_products(selected_feature, selected_application):
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
    return top_products

# Streamlit UI
st.title("Product Recommendation Tool")

selected_feature = st.selectbox("Select a Key Feature:", all_features)
selected_application = st.selectbox("Select an Application:", all_applications)

if st.button("Get Recommendations"):
    top_products = recommend_products(selected_feature, selected_application)
    st.subheader("Top 3 Product Recommendations:")
    for product, score in top_products:
        st.write(f"- **{product}** (Score: {score})")