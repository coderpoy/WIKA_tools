"""
Thermowell simulator - Python 2.7 compatible, PEP8-style variable/function names.

What I changed:
- Renamed variables that used CamelCase (e.g. D_root, Lpx) to lower_case_with_underscores
  to address linter/pylint style warnings about variable/function naming.
- Kept class name ThermowellSimulator (class names are PascalCase per PEP8).
- Kept module-level constants UPPERCASE (PI, MATERIAL_LIBRARY).
- Function and method names are lower_case_with_underscores.
- Behavior and public API unchanged: use run_from_schema(schema) which returns a plain dict.

Note: These naming changes address linter/style warnings. They are not required for execution,
but improve conformity to common Python style checkers (pylint/flake8).
"""
import math

PI = math.pi

# Material preset library (module-level constant)
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


# Helper functions (lower_case)
def _area(diameter):
    return PI * (diameter ** 2) / 4.0


def _second_moment_circular(diameter):
    return PI * (diameter ** 4) / 64.0


class ThermowellSimulator(object):
    """Core simulator (keeps PascalCase for the class name)."""

    def __init__(self, inputs, constants=None):
        # inputs: plain dict with expected keys (see run_from_schema docstring)
        self.inputs = inputs
        if constants is None:
            self.constants = {"strouhal_number": 0.22, "target_wfr": 2.2}
        else:
            self.constants = constants

    def _resolve_material(self):
        """
        Determine elastic modulus (E) and material density to use.
        Returns dict with keys: preset, elastic_modulus_pa, density_kg_per_m3, notes, overridden
        """
        preset_name = self.inputs.get("material_preset") or "Custom (enter below)"
        preset = MATERIAL_LIBRARY.get(preset_name, MATERIAL_LIBRARY["Custom (enter below)"])
        e_preset = preset.get("elastic_modulus_pa")
        rho_preset = preset.get("density_kg_per_m3")

        e_override = self.inputs.get("elastic_modulus_pa")
        rho_override = self.inputs.get("material_density_kg_per_m3")

        if e_override is None:
            e_used = e_preset
        else:
            e_used = e_override

        if rho_override is None:
            rho_used = rho_preset
        else:
            rho_used = rho_override

        overridden = False
        if preset_name == "Custom (enter below)":
            overridden = True
        else:
            overridden = (e_override is not None) or (rho_override is not None)

        if e_used is None or rho_used is None:
            raise ValueError("Material properties are incomplete: please provide elastic_modulus_pa and material_density_kg_per_m3 via preset or explicitly.")

        return {
            "preset": preset_name,
            "elastic_modulus_pa": float(e_used),
            "density_kg_per_m3": float(rho_used),
            "notes": preset.get("notes", ""),
            "overridden": overridden
        }

    def generate_svg(self, immersion_length, root_diameter, tip_diameter, bore_diameter, fillet_radius):
        """
        Return an illustrative SVG string of the thermowell with labels.
        """
        width = 720
        height = 240
        # scale length to pixels so immersion fills most of canvas
        l_px = max(80, min(520, int(immersion_length * 2000)))
        x0 = 80
        y_center = height // 2

        # diameters in px (scaled)
        max_diameter = max(root_diameter, tip_diameter, bore_diameter, 1e-6)
        scale_d = 80.0 / max_diameter
        root_px = max(4, root_diameter * scale_d)
        tip_px = max(3, tip_diameter * scale_d)
        bore_px = max(3, bore_diameter * scale_d)

        stem_x_end = x0 + l_px

        stem_svg = '<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#333" stroke-width="{sw}" stroke-linecap="round" />'.format(
            x1=x0, x2=stem_x_end, y=y_center, sw=root_px)
        tip_circle = '<circle cx="{cx}" cy="{cy}" r="{r}" fill="#777" stroke="#333" />'.format(
            cx=stem_x_end + tip_px/2 + 6, cy=y_center, r=tip_px/2)
        root_circle = '<circle cx="{cx}" cy="{cy}" r="{r}" fill="#999" stroke="#333" />'.format(
            cx=x0 - root_px/2 - 6, cy=y_center, r=root_px/2)
        bore_circle = '<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#0066cc" stroke-dasharray="4,2" />'.format(
            cx=stem_x_end - (l_px * 0.15), cy=y_center, r=bore_px/2)

        immersion_label = '<line x1="{ax1}" y1="{ay}" x2="{ax2}" y2="{ay}" stroke="#444" marker-start="url(#arrow)" marker-end="url(#arrow)"/><text x="{tx}" y="{ty}" text-anchor="middle" font-size="12px" fill="#222">Immersion length = {imm:.3f} m</text>'.format(
            ax1=x0, ax2=stem_x_end, ay=y_center - 40, tx=(x0 + stem_x_end) / 2, ty=y_center - 46, imm=immersion_length)

        root_label = '<text x="{x}" y="{y}" font-size="11px" fill="#111" text-anchor="end">Root Ø {d:.3f} m</text>'.format(
            x=x0 - root_px / 2 - 20, y=y_center + root_px / 2 + 20, d=root_diameter)
        tip_label = '<text x="{x}" y="{y}" font-size="11px" fill="#111">Tip Ø {d:.3f} m</text>'.format(
            x=stem_x_end + tip_px / 2 + 40, y=y_center + 5, d=tip_diameter)
        bore_label = '<text x="{x}" y="{y}" font-size="11px" fill="#0066cc">Bore Ø {d:.3f} m</text>'.format(
            x=stem_x_end - (l_px * 0.15) + bore_px / 2 + 30, y=y_center + 5, d=bore_diameter)
        fillet_label = '<text x="{x}" y="{y}" font-size="11px" fill="#111">Fillet r {r:.3f} m</text>'.format(
            x=x0 + 6, y=y_center - root_px / 2 - 8, r=fillet_radius)

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

    def compute(self):
        """Perform all calculations and return a plain dictionary of outputs."""
        # read inputs from self.inputs (dict)
        try:
            v = float(self.inputs.get("velocity_m_per_s"))
            rho_f = float(self.inputs.get("fluid_density_kg_per_m3"))
            mu = float(self.inputs.get("viscosity_pa_s"))
            immersion_length = float(self.inputs.get("immersion_length_m"))
            root_diameter = float(self.inputs.get("root_diameter_m"))
            tip_diameter = float(self.inputs.get("tip_diameter_m"))
            bore_diameter = float(self.inputs.get("bore_diameter_m"))
            fillet_radius = float(self.inputs.get("fillet_radius_m"))
        except Exception:
            raise ValueError("Missing or invalid required fluid/geometry inputs")

        mat = self._resolve_material()
        e_modulus = float(mat["elastic_modulus_pa"])
        rho_mat = float(mat["density_kg_per_m3"])

        support_compliance = float(self.inputs.get("support_compliance_factor", 1.0))
        added_sensor_mass = float(self.inputs.get("added_sensor_mass_kg", 0.0))

        # Derived geometry / structural properties
        a_root = _area(root_diameter)
        i_root = _second_moment_circular(root_diameter)

        # Mass per unit length (structural)
        m_prime = rho_mat * a_root  # kg/m

        # damping ratio
        if self.inputs.get("damping_ratio") is not None:
            zeta = float(self.inputs.get("damping_ratio"))
        else:
            zeta = max(0.005, 0.01 * support_compliance)

        # Vortex shedding frequency (uses tip diameter)
        st = float(self.constants.get("strouhal_number", 0.22))
        if tip_diameter <= 0:
            raise ValueError("tip_diameter_m must be > 0 for vortex frequency calculation")
        f_s = st * v / tip_diameter

        # Natural frequency (approx cantilever first mode with tip mass correction)
        base_coeff = (1.875 ** 2) / (2.0 * PI)
        mu_tip_ratio = 0.0
        if immersion_length > 0:
            denom_mu = (m_prime * immersion_length)
            if denom_mu > 0:
                mu_tip_ratio = added_sensor_mass / denom_mu
            else:
                mu_tip_ratio = 0.0
        effective_mass_factor = 1.0 + 0.23 * mu_tip_ratio

        if m_prime <= 0 or immersion_length <= 0:
            raise ValueError("material density, root diameter, and immersion length must be > 0")

        f_n = base_coeff * math.sqrt((e_modulus * i_root) / (m_prime * (immersion_length ** 4) * effective_mass_factor))

        # Wake frequency ratio WFR = f_n / f_s
        if f_s == 0:
            wfr = float('inf')
        else:
            wfr = f_n / f_s

        resonance_risk = (wfr < float(self.constants.get("target_wfr", 2.2)))

        # Scruton number Nsc
        denom = 1.0 - (bore_diameter / tip_diameter) ** 2 if tip_diameter != 0 else 0.0
        if denom <= 0:
            n_sc = float('inf')
        else:
            n_sc = 2.0 * zeta * (m_prime / denom)

        # Stress amplification factor at forcing frequency f_s
        if f_n == 0:
            amplification = float('inf')
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
            "st": st,
            "re_tip_based": (rho_f * v * tip_diameter / mu) if mu > 0 else None,
            "vortex_shedding_freq_calc": "f_s = St * V / D_tip",
            "natural_freq_formula": "approx cantilever with empirical tip mass correction"
        }

        svg = self.generate_svg(immersion_length, root_diameter, tip_diameter, bore_diameter, fillet_radius)

        outputs = {
            "natural_frequency_hz": float(f_n),
            "vortex_shedding_frequency_hz": float(f_s),
            "wake_frequency_ratio": float(wfr),
            "resonance_risk": bool(resonance_risk),
            "scruton_number": float(n_sc if n_sc != float('inf') else float('inf')),
            "stress_amplification_factor": float(amplification if amplification != float('inf') else float('inf')),
            "material_used": {
                "preset": mat.get("preset"),
                "elastic_modulus_pa": mat.get("elastic_modulus_pa"),
                "density_kg_per_m3": mat.get("density_kg_per_m3"),
                "notes": mat.get("notes", ""),
                "overridden": mat.get("overridden", False)
            },
            "svg_drawing": svg,
            "intermediates": intermediates
        }

        return outputs


def run_from_schema(schema):
    """
    Accepts a dictionary following your schema and returns computed outputs (plain dict).

    Optional under material_properties you can include:
      material_preset: string (key of MATERIAL_LIBRARY)
      elastic_modulus_pa: numeric (overrides preset)
      density_kg_per_m3: numeric (overrides preset)

    Expected schema keys are the same as earlier examples.
    """
    sim = schema.get("thermowell_simulator", {})
    inputs = sim.get("inputs", {})
    fluid = inputs.get("fluid_properties", {})
    dims = inputs.get("thermowell_dimensions", {})
    mat = inputs.get("material_properties", {})
    inst = inputs.get("installation", {})

    # Flatten expected keys into the simulator input dict (lower_case keys)
    tw_inputs = {
        "velocity_m_per_s": float(fluid.get("velocity_m_per_s")),
        "fluid_density_kg_per_m3": float(fluid.get("density_kg_per_m3")),
        "viscosity_pa_s": float(fluid.get("viscosity_pa_s")),
        "immersion_length_m": float(dims.get("immersion_length_m")),
        "root_diameter_m": float(dims.get("root_diameter_m")),
        "tip_diameter_m": float(dims.get("tip_diameter_m")),
        "bore_diameter_m": float(dims.get("bore_diameter_m")),
        "fillet_radius_m": float(dims.get("fillet_radius_m")),
        "material_preset": mat.get("material_preset", None),
        "elastic_modulus_pa": (None if mat.get("elastic_modulus_pa") is None else float(mat.get("elastic_modulus_pa"))),
        "material_density_kg_per_m3": (None if mat.get("density_kg_per_m3") is None else float(mat.get("density_kg_per_m3"))),
        "support_compliance_factor": float(inst.get("support_compliance_factor", 1.0)),
        "added_sensor_mass_kg": float(inst.get("added_sensor_mass_kg", 0.0)),
        "damping_ratio": inst.get("damping_ratio", None)
    }

    consts = {
        "strouhal_number": float(sim.get("constants", {}).get("strouhal_number", 0.22)),
        "target_wfr": float(sim.get("constants", {}).get("target_wfr", 2.2))
    }

    simulator = ThermowellSimulator(tw_inputs, constants=consts)
    return simulator.compute()


def list_material_presets():
    """Return a shallow copy of the material library for display (read-only)."""
    out = {}
    for key, val in MATERIAL_LIBRARY.items():
        out[key] = {"elastic_modulus_pa": val.get("elastic_modulus_pa"), "density_kg_per_m3": val.get("density_kg_per_m3"), "notes": val.get("notes", "")}
    return out