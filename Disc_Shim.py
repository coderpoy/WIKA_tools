import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def calculate_optimal_sheet(diameter_mm, quantity):
    clearance_mm = 10
    effective_diameter_mm = diameter_mm + clearance_mm
    effective_diameter_cm = effective_diameter_mm / 10

    discs_per_side = math.ceil(math.sqrt(quantity))
    sheet_side_cm = discs_per_side * effective_diameter_cm
    sheet_area_cm2 = sheet_side_cm ** 2
    total_discs_possible = discs_per_side ** 2

    return {
        "effective_diameter_cm": effective_diameter_cm,
        "sheet_side_cm": sheet_side_cm,
        "sheet_area_cm2": sheet_area_cm2,
        "discs_per_side": discs_per_side,
        "total_discs_possible": total_discs_possible
    }

def visualize_layout(effective_diameter_cm, discs_per_side, sheet_side_cm, diameter_cm, diameter_mm):
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(0, sheet_side_cm)
    ax.set_ylim(0, sheet_side_cm)
    ax.set_aspect('equal')
    ax.set_title("Metal Sheet Layout with Disc Cutouts")

    # Draw the square sheet
    sheet = patches.Rectangle((0, 0), sheet_side_cm, sheet_side_cm, linewidth=2, edgecolor='black', facecolor='lightgrey')
    ax.add_patch(sheet)

    # Draw the discs
    for i in range(discs_per_side):
        for j in range(discs_per_side):
            center_x = (i + 0.5) * effective_diameter_cm
            center_y = (j + 0.5) * effective_diameter_cm
            if center_x + diameter_cm / 2 <= sheet_side_cm and center_y + diameter_cm / 2 <= sheet_side_cm:
                disc = patches.Circle((center_x, center_y), radius=diameter_cm / 2, edgecolor='blue', facecolor='lightblue')
                ax.add_patch(disc)
                # Label the first disc only
                if i == 0 and j == 0:
                    ax.text(center_x, center_y, f"{diameter_mm} mm", color='black', fontsize=10,
                            ha='center', va='center', weight='bold')

    plt.xlabel("cm")
    plt.ylabel("cm")
    plt.grid(True)
    plt.show()

def main():
    diameter_mm = float(input("Enter the diameter of the disc in mm: "))
    quantity = int(input("Enter the quantity of discs: "))

    result = calculate_optimal_sheet(diameter_mm, quantity)

    print("\nCalculation Summary:")
    print(f"Disc Diameter: {diameter_mm} mm")
    print(f"Quantity Requested: {quantity}")
    print(f"Clearance Between Discs: 10 mm")
    print(f"Effective Diameter (including clearance): {result['effective_diameter_cm']:.2f} cm")
    print(f"Optimal Sheet Side Length: {result['sheet_side_cm']:.2f} cm")
    print(f"Optimal Sheet Area: {result['sheet_area_cm2']:.2f} cm²")
    print(f"Discs per Side: {result['discs_per_side']}")
    print(f"Total Discs Possible: {result['total_discs_possible']}")

    visualize_layout(result['effective_diameter_cm'], result['discs_per_side'],
                     result['sheet_side_cm'], diameter_mm / 10, diameter_mm)

if __name__ == "__main__":
    main()

