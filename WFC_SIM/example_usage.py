"""
Example usage of thermowell_simulator.run_from_schema with the provided schema.
Run this script to see a sample calculation.
"""
from thermowell_simulator import run_from_schema
import json

if __name__ == "__main__":
    sample_schema = {
      "thermowell_simulator": {
        "inputs": {
          "fluid_properties": {
            "velocity_m_per_s": 5.0,
            "density_kg_per_m3": 1000.0,
            "viscosity_pa_s": 0.001
          },
          "thermowell_dimensions": {
            "immersion_length_m": 0.2,
            "root_diameter_m": 0.025,
            "tip_diameter_m": 0.012,
            "bore_diameter_m": 0.006,
            "fillet_radius_m": 0.002
          },
          "material_properties": {
            "elastic_modulus_pa": 2.0e11,
            "density_kg_per_m3": 7850.0
          },
          "installation": {
            "support_compliance_factor": 1.0,
            "added_sensor_mass_kg": 0.005
          }
        },
        "constants": {
          "strouhal_number": 0.22,
          "target_wfr": 2.2
        }
      }
    }

    outputs = run_from_schema(sample_schema)
    print(json.dumps({
        "natural_frequency_hz": outputs.natural_frequency_hz,
        "vortex_shedding_frequency_hz": outputs.vortex_shedding_frequency_hz,
        "wake_frequency_ratio": outputs.wake_frequency_ratio,
        "resonance_risk": outputs.resonance_risk,
        "scruton_number": outputs.scruton_number,
        "stress_amplification_factor": outputs.stress_amplification_factor,
        "intermediates": outputs.intermediates
    }, indent=2))