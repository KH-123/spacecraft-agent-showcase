"""
Mass budget estimation for spacecraft conceptual design.

This module provides deterministic engineering calculations
for preliminary mass budget estimation of small satellites.
"""


def mass_budget(payload_mass_kg: float,
                orbit_type: str = "LEO",
                bus_margin: float = 0.20) -> dict:
    """
    Estimate spacecraft mass budget based on payload mass.

    Parameters
    ----------
    payload_mass_kg : float
        Mass of the payload in kilograms.
    orbit_type : str, optional
        Target orbit type ("LEO", "SSO", "GEO"). Default is "LEO".
    bus_margin : float, optional
        Mass margin for the bus subsystem (default 0.20 = 20%).

    Returns
    -------
    dict
        A dictionary containing:
        - "total_mass_kg": estimated total spacecraft mass
        - "payload_mass_kg": input payload mass
        - "bus_mass_kg": estimated bus mass
        - "propellant_mass_kg": estimated propellant mass (if applicable)
        - "margin_mass_kg": mass margin
        - "mass_breakdown": dict of subsystem mass estimates
        - "assumption": list of assumptions
        - "unit": unit specification

    Notes
    -----
    - Uses typical mass fraction ratios for small satellites.
    - Payload mass fraction for LEO small satellites is typically 25-40%.
    - This is a conceptual-level rough sizing estimate.
    - Does not account for detailed component selection.
    """
    if payload_mass_kg <= 0:
        raise ValueError("Payload mass must be positive")

    # Typical mass fractions for small satellites
    # Based on historical small satellite data
    mass_fractions = {
        "LEO": {
            "payload_fraction": 0.30,      # Payload is ~30% of dry mass
            "structure_fraction": 0.22,     # Structure
            "power_fraction": 0.18,         # Power subsystem
            "adcs_fraction": 0.10,          # Attitude determination and control
            "thermal_fraction": 0.05,       # Thermal control
            "comms_fraction": 0.08,         # Communications
            "cndh_fraction": 0.07,          # Command and data handling
            "propulsion_fraction": 0.00,    # No propulsion for basic LEO
            "harness_fraction": 0.05,       # Harness and integration
        },
        "SSO": {
            "payload_fraction": 0.28,
            "structure_fraction": 0.22,
            "power_fraction": 0.20,
            "adcs_fraction": 0.12,
            "thermal_fraction": 0.05,
            "comms_fraction": 0.08,
            "cndh_fraction": 0.07,
            "propulsion_fraction": 0.00,
            "harness_fraction": 0.05,
        },
        "GEO": {
            "payload_fraction": 0.25,
            "structure_fraction": 0.18,
            "power_fraction": 0.22,
            "adcs_fraction": 0.12,
            "thermal_fraction": 0.08,
            "comms_fraction": 0.10,
            "cndh_fraction": 0.06,
            "propulsion_fraction": 0.12,
            "harness_fraction": 0.05,
        },
    }

    if orbit_type not in mass_fractions:
        raise ValueError(f"Unsupported orbit type: {orbit_type}. Supported: {list(mass_fractions.keys())}")

    fractions = mass_fractions[orbit_type]

    # Estimate dry bus mass from payload mass using payload fraction
    payload_frac = fractions["payload_fraction"]
    dry_bus_mass_kg = payload_mass_kg * (1.0 - payload_frac) / payload_frac

    # Apply margin
    margin_mass_kg = dry_bus_mass_kg * bus_margin
    dry_bus_mass_with_margin_kg = dry_bus_mass_kg + margin_mass_kg

    # Total dry mass
    total_dry_mass_kg = payload_mass_kg + dry_bus_mass_with_margin_kg

    # Propellant (only for GEO or if propulsion fraction > 0)
    propellant_mass_kg = 0.0
    if fractions["propulsion_fraction"] > 0:
        propellant_mass_kg = total_dry_mass_kg * fractions["propulsion_fraction"] / (1.0 - fractions["propulsion_fraction"])

    total_mass_kg = total_dry_mass_kg + propellant_mass_kg

    # Subsystem breakdown
    breakdown = {}
    for key, frac in fractions.items():
        if key == "payload_fraction":
            continue
        if key == "propulsion_fraction" and frac == 0:
            breakdown[key] = 0.0
        else:
            breakdown[key] = round(dry_bus_mass_kg * frac, 2)

    return {
        "total_mass_kg": round(total_mass_kg, 2),
        "total_dry_mass_kg": round(total_dry_mass_kg, 2),
        "payload_mass_kg": payload_mass_kg,
        "bus_mass_kg": round(dry_bus_mass_with_margin_kg, 2),
        "propellant_mass_kg": round(propellant_mass_kg, 2),
        "margin_mass_kg": round(margin_mass_kg, 2),
        "bus_margin_fraction": bus_margin,
        "orbit_type": orbit_type,
        "mass_breakdown": breakdown,
        "unit": {
            "total_mass_kg": "kg",
            "total_dry_mass_kg": "kg",
            "payload_mass_kg": "kg",
            "bus_mass_kg": "kg",
            "propellant_mass_kg": "kg",
            "margin_mass_kg": "kg",
            "mass_breakdown": "kg",
        },
        "assumption": [
            f"Payload mass fraction = {payload_frac:.0%} of dry mass (typical for {orbit_type} small satellites)",
            f"Bus mass margin = {bus_margin:.0%}",
            "Based on historical small satellite mass fraction data",
            "Conceptual-level rough sizing estimate only",
            "Detailed component selection will change actual mass",
        ],
    }