#!/usr/bin/env python3
"""
Thermowell Simulator — single-file CLI program (no Streamlit)

Features:
- Single file: material presets, calculations, SVG visualization generator.
- CLI options:
    --sample             : run a built-in sample case
    --schema FILE        : run using a JSON schema file (your schema format)
    --out-dir DIR        : directory to write outputs (results.json, drawing.svg)
    --material-preset    : pick a material preset name
    --E                  : override elastic modulus (Pa)
    --rho                : override material density (kg/m^3)
    --velocity           : fluid velocity (m/s)
    --fluid-density      : fluid density (kg/m^3)
    --viscosity          : fluid viscosity (Pa·s)
    --immersion          : immersion length (m)
    --d_root             : root diameter (m)
    --d_tip              : tip diameter (m)
    --d_bore             : bore diameter (m)
    --fillet             : fillet radius (m)
    --support-compliance : support compliance factor
    --sensor-mass        : added sensor mass (kg)
    --damping            : damping ratio (optional)
    --st                 : Strouhal number (default 0.22)
    --target-wfr         : target minimum WFR (default 2.2)

Outputs:
- Prints summary to console
- Writes results JSON to results.json in out-dir (or current dir)
- Writes SVG drawing to thermowell_drawing.svg in out-dir

Example:
  python thermowell_simulator_cli.py --sample
  python thermowell_simulator_cli.py --velocity 5 --d_tip 0.012 --d_root 0.025 --immersion 0.2 --material-preset "Stainless Steel (SS316 / SS316L)"

Note:
- This script intentionally has no external runtime dependencies beyond Python 3.
- The formulas are engineering approximations consistent with the schema you provided:
    f_s = St * V / D_tip
    f_n ≈ (1.875^2 / (2π)) * sqrt( E I / (m' L^4) ) with an empirical tip-mass correction
    WFR = f_n / f_s
    Scruton number and stress amplification factor included.

Author: Copied/derived from previous V6 simulator implementation.
"""

from __future__ import print_function
import argparse
import json
import math
import os
import sys

PI = math.pi

# -------------------------
# Material preset library
# -------------------------
MATERIAL_LIBRARY = {
    "Custom (enter below)": {
        "elastic_modulus_pa": None,
        "density_kg_per_m3": None,
        "notes": "Enter E and density manually"
    },
    "Stainless Steel (SS304)": {
        "elastic_modulus_pa": 193e9,
        "density_kg_per_m3": 7930.0,
        "notes": "Typical austenitic stainless steel"
    },
    "Stainless Steel (SS316 / SS316L)": {
        "elastic_modulus_pa": 193e9,
        "density_kg_per_m3": 8000.0,
        "notes": "Marine-grade stainless; use 316L for low-C variations"
    },
    "Carbon Steel (approx. A36)": {
        "elastic_modulus_pa": 200e9,
        "density_kg_per_m3": 7850.0,
        "notes": "Typical structural steel"
    },
    "Inconel (nickel alloy, e.g. 625)": {
        "elastic_modulus_pa": 207e9,
        "density_kg_per_m3": 8440.0,
        "notes": "High-nickel alloy, approximate values"
    },
    "Monel (e.g. Monel 400)": {
        "elastic_modulus_pa": 190e9,
        "density_kg_per_m3": 8830.0,
        "notes": "Nickel-copper alloy; approximate"
    },
    "Titanium (Grade 2)": {
        "elastic_modulus_pa": 105e9,
        "density_kg_per_m3": 4500.0,
        "notes": "Commercially pure titanium"
    },
    "Aluminum (6061-T6)": {
        "elastic_modulus_pa": 69e9,
        "density_kg_per_m3": 2700.0,
        "notes": "Common aluminum alloy"
    }
}


# -------------------------
# Calculation helpers
# -------------------------
def area_circular(diameter):
    return PI * (diameter ** 2) / 4.0


def second_moment_circle(diameter):
    return PI * (diameter ** 4) / 64.0


def resolve_material(preset_name, e_override, rho_override):
    preset_name = preset_name or "Custom (enter below)"
    preset = MATERIAL_LIBRARY.get(preset_name)
    if preset is None:
        raise ValueError("Unknown material preset '{}'".format(preset_name))
    e_preset = preset.get("elastic_modulus_pa")
    rho_preset = preset.get("density_kg_per_m3")
    e_used = e_override if e_override is not None else e_preset
    rho_used = rho_override if rho_override is not None else rho_preset
    overridden = False
    if preset_name == "Custom (enter below)":
        overridden = True
    else:
        overridden = (e_override is not None) or (rho_override is not None)
    if e_used is None or rho_used is None:
        raise ValueError("Material properties incomplete: provide E and density via preset or overrides.")
    return {
        "preset": preset_name,
        "elastic_modulus_pa": float(e_used),
        "density_kg_per_m3": float(rho_used),
        "notes": preset.get("notes", ""),
        "overridden": overridden
    }


def compute_from_inputs(inputs, constants):
    """
    inputs: dict with keys:
      velocity_m_per_s, fluid_density_kg_per_m3, viscosity_pa_s,
      immersion_length_m, root_diameter_m, tip_diameter_m, bore_diameter_m, fillet_radius_m,
      material_preset, elastic_modulus_pa (opt), material_density_kg_per_m3 (opt),
      support_compliance_factor, added_sensor_mass_kg, damping_ratio (opt)
    constants: dict with keys strouhal_number and target_wfr
    Returns: result dict
    """
    # unpack
    v = float(inputs["velocity_m_per_s"])
    rho_f = float(inputs["fluid_density_kg_per_m3"])
    mu = float(inputs["viscosity_pa_s"])
    immersion = float(inputs["immersion_length_m"])
    d_root = float(inputs["root_diameter_m"])
    d_tip = float(inputs["tip_diameter_m"])
    d_bore = float(inputs["bore_diameter_m"])
    fillet = float(inputs["fillet_radius_m"])
    preset = inputs.get("material_preset")
    e_override = inputs.get("elastic_modulus_pa")
    rho_override = inputs.get("material_density_kg_per_m3")
    support_compliance = float(inputs.get("support_compliance_factor", 1.0))
    sensor_mass = float(inputs.get("added_sensor_mass_kg", 0.0))
    damping = inputs.get("damping_ratio")
    damping = None if damping is None else float(damping)

    const_st = float(constants.get("strouhal_number", 0.22))
    target_wfr = float(constants.get("target_wfr", 2.2))

    # resolve material
    mat = resolve_material(preset, e_override, rho_override)
    e_mod = mat["elastic_modulus_pa"]
    rho_mat = mat["density_kg_per_m3"]

    # derived geometry/properties
    a_root = area_circular(d_root)
    i_root = second_moment_circle(d_root)
    m_prime = rho_mat * a_root  # kg/m

    # damping ratio default
    if damping is not None:
        zeta = damping
    else:
        zeta = max(0.005, 0.01 * support_compliance)

    # vortex shedding frequency
    if d_tip <= 0:
        raise ValueError("tip diameter must be > 0")
    f_s = const_st * v / d_tip

    # natural frequency (cantilever approx) with tip-mass empirical correction
    base_coeff = (1.875 ** 2) / (2.0 * PI)
    mu_tip_ratio = 0.0
    if immersion > 0:
        denom_mu = m_prime * immersion
        if denom_mu > 0:
            mu_tip_ratio = sensor_mass / denom_mu
    effective_mass_factor = 1.0 + 0.23 * mu_tip_ratio

    if m_prime <= 0 or immersion <= 0:
        raise ValueError("material density/root diameter/immersion must be > 0")

    f_n = base_coeff * math.sqrt((e_mod * i_root) / (m_prime * (immersion ** 4) * effective_mass_factor))

    # wake frequency ratio WFR = f_n / f_s
    wfr = float("inf") if f_s == 0 else f_n / f_s
    resonance_risk = (wfr < target_wfr)

    # Scruton number
    denom = 1.0 - (d_bore / d_tip) ** 2 if d_tip != 0 else 0.0
    if denom <= 0:
        n_sc = float("inf")
    else:
        n_sc = 2.0 * zeta * (m_prime / denom)

    # stress amplification factor (steady-state linear oscillator response)
    if f_n == 0:
        amplification = float("inf")
    else:
        r = f_s / f_n
        amplification = 1.0 / math.sqrt((1.0 - r ** 2) ** 2 + (2.0 * zeta * r) ** 2)

    intermediates = {
        "a_root_m2": a_root,
        "i_root_m4": i_root,
        "m_prime_kg_per_m": m_prime,
        "mu_tip_ratio": mu_tip_ratio,
        "effective_mass_factor": effective_mass_factor,
        "damping_ratio_used": zeta,
        "st": const_st,
        "re_tip_based": (rho_f * v * d_tip / mu) if mu > 0 else None,
        "vortex_shedding_freq_calc": "f_s = St * V / D_tip",
        "natural_freq_formula": "approx cantilever with empirical tip mass correction"
    }

    svg = generate_svg(immersion, d_root, d_tip, d_bore, fillet)

    result = {
        "natural_frequency_hz": float(f_n),
        "vortex_shedding_frequency_hz": float(f_s),
        "wake_frequency_ratio": float(wfr),
        "resonance_risk": bool(resonance_risk),
        "scruton_number": float(n_sc if n_sc != float("inf") else float("inf")),
        "stress_amplification_factor": float(amplification if amplification != float("inf") else float("inf")),
        "material_used": mat,
        "svg_drawing": svg,
        "intermediates": intermediates
    }
    return result


# -------------------------
# Visualization (SVG) helper
# -------------------------
def generate_svg(immersion, d_root, d_tip, d_bore, fillet):
    width = 720
    height = 240
    l_px = max(80, min(520, int(immersion * 2000)))
    x0 = 80
    y_center = height // 2

    max_diameter = max(d_root, d_tip, d_bore, 1e-6)
    scale_d = 80.0 / max_diameter
    root_px = max(4, d_root * scale_d)
    tip_px = max(3, d_tip * scale_d)
    bore_px = max(3, d_bore * scale_d)

    stem_x_end = x0 + l_px

    stem_svg = '<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#333" stroke-width="{sw}" stroke-linecap="round" />'.format(
        x1=x0, x2=stem_x_end, y=y_center, sw=root_px)
    tip_circle = '<circle cx="{cx}" cy="{cy}" r="{r}" fill="#777" stroke="#333" />'.format(
        cx=stem_x_end + tip_px / 2 + 6, cy=y_center, r=tip_px / 2)
    root_circle = '<circle cx="{cx}" cy="{cy}" r="{r}" fill="#999" stroke="#333" />'.format(
        cx=x0 - root_px / 2 - 6, cy=y_center, r=root_px / 2)
    bore_circle = '<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#0066cc" stroke-dasharray="4,2" />'.format(
        cx=stem_x_end - (l_px * 0.15), cy=y_center, r=bore_px / 2)

    immersion_label = '<line x1="{ax1}" y1="{ay}" x2="{ax2}" y2="{ay}" stroke="#444" marker-start="url(#arrow)" marker-end="url(#arrow)"/><text x="{tx}" y="{ty}" text-anchor="middle" font-size="12px" fill="#222">Immersion length = {imm:.3f} m</text>'.format(
        ax1=x0, ax2=stem_x_end, ay=y_center - 40, tx=(x0 + stem_x_end) / 2, ty=y_center - 46, imm=immersion)

    root_label = '<text x="{x}" y="{y}" font-size="11px" fill="#111" text-anchor="end">Root Ø {d:.3f} m</text>'.format(
        x=x0 - root_px / 2 - 20, y=y_center + root_px / 2 + 20, d=d_root)
    tip_label = '<text x="{x}" y="{y}" font-size="11px" fill="#111">Tip Ø {d:.3f} m</text>'.format(
        x=stem_x_end + tip_px / 2 + 40, y=y_center + 5, d=d_tip)
    bore_label = '<text x="{x}" y="{y}" font-size="11px" fill="#0066cc">Bore Ø {d:.3f} m</text>'.format(
        x=stem_x_end - (l_px * 0.15) + bore_px / 2 + 30, y=y_center + 5, d=d_bore)
    fillet_label = '<text x="{x}" y="{y}" font-size="11px" fill="#111">Fillet r {r:.3f} m</text>'.format(
        x=x0 + 6, y=y_center - root_px / 2 - 8, r=fillet)

    svg = (
        '<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">'
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker></defs>'
        '<rect x="0" y="0" width="{w}" height="{h}" fill="#fafafa"/>'
        '{stem}{tip}{root}{bore}{imm}{rootlab}{tiplab}{borelab}{fillab}'
        '<rect x="{rx}" y="{ry}" width="30" height="100" fill="#ddd" stroke="#bbb" />'
        '<text x="{tx}" y="{ty}" font-size="11px" text-anchor="middle" fill="#333">Mount</text>'
        '</svg>'
    ).format(
        w=width, h=height,
        stem=stem_svg, tip=tip_circle, root=root_circle, bore=bore_circle,
        imm=immersion_label, rootlab=root_label, tiplab=tip_label, borelab=bore_label, fillab=fillet_label,
        rx=x0 - 30, ry=y_center - 50, tx=x0 - 15, ty=y_center - 60
    )
    return svg


# -------------------------
# CLI and I/O
# -------------------------
def default_sample_schema():
    return {
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
                    "material_preset": "Stainless Steel (SS316 / SS316L)"
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


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Thermowell Simulator (CLI, single-file).")
    parser.add_argument("--sample", action="store_true", help="Run built-in sample case and exit.")
    parser.add_argument("--schema", type=str, help="Path to JSON schema file (your schema format).")
    parser.add_argument("--out-dir", type=str, default=".", help="Directory to write results (default current).")

    parser.add_argument("--material-preset", type=str, default=None, help="Material preset name (from internal library).")
    parser.add_argument("--E", type=float, default=None, help="Override elastic modulus (Pa).")
    parser.add_argument("--rho", type=float, default=None, help="Override material density (kg/m^3).")

    # quick input overrides
    parser.add_argument("--velocity", type=float, help="Fluid velocity (m/s)")
    parser.add_argument("--fluid-density", type=float, dest="fluid_density", help="Fluid density (kg/m^3)")
    parser.add_argument("--viscosity", type=float, help="Fluid viscosity (Pa·s)")
    parser.add_argument("--immersion", type=float, help="Immersion length (m)")
    parser.add_argument("--d_root", type=float, help="Root diameter (m)")
    parser.add_argument("--d_tip", type=float, help="Tip diameter (m)")
    parser.add_argument("--d_bore", type=float, help="Bore diameter (m)")
    parser.add_argument("--fillet", type=float, help="Fillet radius (m)")
    parser.add_argument("--support-compliance", type=float, dest="support_compliance", help="Support compliance factor")
    parser.add_argument("--sensor-mass", type=float, dest="sensor_mass", help="Added sensor mass (kg)")
    parser.add_argument("--damping", type=float, help="Damping ratio (optional override)")

    parser.add_argument("--st", type=float, default=0.22, help="Strouhal number")
    parser.add_argument("--target-wfr", type=float, default=2.2, help="Target minimum WFR")

    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)

    out_dir = args.out_dir
    if not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir)
        except Exception as exc:
            print("Unable to create output directory '{}': {}".format(out_dir, exc), file=sys.stderr)
            sys.exit(2)

    if args.sample:
        schema = default_sample_schema()
    elif args.schema:
        try:
            with open(args.schema, "r") as f:
                schema = json.load(f)
        except Exception as exc:
            print("Failed to read schema file '{}': {}".format(args.schema, exc), file=sys.stderr)
            sys.exit(2)
    else:
        # Build schema from provided CLI args (use defaults if missing)
        # Provide sensible defaults (same as sample) when not supplied
        velocity = args.velocity if args.velocity is not None else 5.0
        fluid_density = args.fluid_density if args.fluid_density is not None else 1000.0
        viscosity = args.viscosity if args.viscosity is not None else 0.001
        immersion = args.immersion if args.immersion is not None else 0.2
        d_root = args.d_root if args.d_root is not None else 0.025
        d_tip = args.d_tip if args.d_tip is not None else 0.012
        d_bore = args.d_bore if args.d_bore is not None else 0.006
        fillet = args.fillet if args.fillet is not None else 0.002
        support_compliance = args.support_compliance if args.support_compliance is not None else 1.0
        sensor_mass = args.sensor_mass if args.sensor_mass is not None else 0.005

        material_properties = {"material_preset": args.material_preset} if args.material_preset else {"material_preset": "Stainless Steel (SS316 / SS316L)"}
        if args.E is not None:
            material_properties["elastic_modulus_pa"] = args.E
        if args.rho is not None:
            material_properties["density_kg_per_m3"] = args.rho

        schema = {
            "thermowell_simulator": {
                "inputs": {
                    "fluid_properties": {
                        "velocity_m_per_s": velocity,
                        "density_kg_per_m3": fluid_density,
                        "viscosity_pa_s": viscosity
                    },
                    "thermowell_dimensions": {
                        "immersion_length_m": immersion,
                        "root_diameter_m": d_root,
                        "tip_diameter_m": d_tip,
                        "bore_diameter_m": d_bore,
                        "fillet_radius_m": fillet
                    },
                    "material_properties": material_properties,
                    "installation": {
                        "support_compliance_factor": support_compliance,
                        "added_sensor_mass_kg": sensor_mass,
                        "damping_ratio": args.damping
                    }
                },
                "constants": {
                    "strouhal_number": args.st,
                    "target_wfr": args.target_wfr
                }
            }
        }

    # Normalize and extract inputs for compute function
    try:
        sim_inputs = schema["thermowell_simulator"]["inputs"]
        consts = schema["thermowell_simulator"].get("constants", {})
    except Exception:
        print("Invalid schema structure: expected thermowell_simulator.inputs", file=sys.stderr)
        sys.exit(2)

    fluid = sim_inputs.get("fluid_properties", {})
    dims = sim_inputs.get("thermowell_dimensions", {})
    mat = sim_inputs.get("material_properties", {})
    inst = sim_inputs.get("installation", {})

    inputs_flat = {
        "velocity_m_per_s": fluid.get("velocity_m_per_s"),
        "fluid_density_kg_per_m3": fluid.get("density_kg_per_m3"),
        "viscosity_pa_s": fluid.get("viscosity_pa_s"),
        "immersion_length_m": dims.get("immersion_length_m"),
        "root_diameter_m": dims.get("root_diameter_m"),
        "tip_diameter_m": dims.get("tip_diameter_m"),
        "bore_diameter_m": dims.get("bore_diameter_m"),
        "fillet_radius_m": dims.get("fillet_radius_m"),
        "material_preset": mat.get("material_preset"),
        "elastic_modulus_pa": mat.get("elastic_modulus_pa"),
        "material_density_kg_per_m3": mat.get("density_kg_per_m3"),
        "support_compliance_factor": inst.get("support_compliance_factor", 1.0),
        "added_sensor_mass_kg": inst.get("added_sensor_mass_kg", 0.0),
        "damping_ratio": inst.get("damping_ratio", None)
    }

    # Run compute
    try:
        results = compute_from_inputs(inputs_flat, consts)
    except Exception as exc:
        print("Simulation error:", exc, file=sys.stderr)
        sys.exit(3)

    # Print summary
    print("\nThermowell simulation results")
    print("------------------------------------")
    print("Material preset: {}".format(results["material_used"]["preset"]))
    print("Elastic modulus E (Pa): {}".format(results["material_used"]["elastic_modulus_pa"]))
    print("Material density (kg/m^3): {}".format(results["material_used"]["density_kg_per_m3"]))
    print("")
    print("Natural frequency f_n (Hz): {:.6f}".format(results["natural_frequency_hz"]))
    print("Vortex-shedding frequency f_s (Hz): {:.6f}".format(results["vortex_shedding_frequency_hz"]))
    print("Wake frequency ratio (WFR = f_n / f_s): {:.6f}".format(results["wake_frequency_ratio"]))
    print("Resonance risk (WFR < target): {}".format(results["resonance_risk"]))
    print("Scruton number: {}".format(results["scruton_number"]))
    print("Stress amplification factor: {:.6f}".format(results["stress_amplification_factor"]))
    print("------------------------------------\n")

    # Write outputs
    json_out_path = os.path.join(out_dir, "results.json")
    svg_out_path = os.path.join(out_dir, "thermowell_drawing.svg")
    try:
        with open(json_out_path, "w") as jf:
            json.dump(results, jf, indent=2)
        with open(svg_out_path, "w") as sf:
            sf.write(results["svg_drawing"])
    except Exception as exc:
        print("Failed to write outputs: {}".format(exc), file=sys.stderr)
        sys.exit(4)

    print("Wrote results JSON to: {}".format(json_out_path))
    print("Wrote SVG drawing to: {}\n".format(svg_out_path))
    print("To view the drawing, open the SVG file in a browser.")


if __name__ == "__main__":
    main(sys.argv[1:])