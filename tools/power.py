"""
Power system estimation tools for spacecraft conceptual design.

This module provides deterministic engineering calculations
for solar array sizing and battery capacity estimation.
"""

import math

# Solar constant at 1 AU (W/m^2)
SOLAR_CONSTANT = 1361.0


def solar_array_area(power_required_w: float,
                     efficiency: float = 0.30,
                     inherent_degradation: float = 0.77,
                     sun_hours_per_orbit: float = 0.6) -> dict:
    """
    Estimate solar array area required for a given power demand.

    Parameters
    ----------
    power_required_w : float
        Average power required by the spacecraft in watts.
    efficiency : float, optional
        Solar cell efficiency (default 0.30 for triple-junction GaAs).
    inherent_degradation : float, optional
        Combined degradation factor covering temperature, wiring,
        and assembly losses (default 0.77).
    sun_hours_per_orbit : float, optional
        Fraction of orbit in sunlight (default 0.6 for typical LEO).

    Returns
    -------
    dict
        A dictionary containing:
        - "area_m2": estimated solar array area in square meters
        - "power_required_w": input power requirement in watts
        - "efficiency": assumed cell efficiency
        - "inherent_degradation": assumed degradation factor
        - "sun_hours_per_orbit": assumed sunlit fraction
        - "assumption": list of assumptions
        - "unit": unit specification

    Notes
    -----
    - Uses the formula: A = P_req / (G * eta * Kd * F_sun)
      where G = solar constant, eta = efficiency, Kd = degradation, F_sun = sun fraction.
    - This is a conceptual-level rough sizing estimate.
    - Does not account for seasonal variations, array pointing loss, or end-of-life degradation.
    """
    if efficiency <= 0 or efficiency > 1:
        raise ValueError("Efficiency must be between 0 and 1")
    if inherent_degradation <= 0 or inherent_degradation > 1:
        raise ValueError("Inherent degradation must be between 0 and 1")
    if sun_hours_per_orbit <= 0 or sun_hours_per_orbit > 1:
        raise ValueError("Sun hours per orbit fraction must be between 0 and 1")

    # Solar array area estimation
    # A = P_req / (G * eta * Kd * F_sun)
    area_m2 = power_required_w / (SOLAR_CONSTANT * efficiency * inherent_degradation * sun_hours_per_orbit)

    return {
        "area_m2": round(area_m2, 2),
        "power_required_w": power_required_w,
        "efficiency": efficiency,
        "inherent_degradation": inherent_degradation,
        "sun_hours_per_orbit": sun_hours_per_orbit,
        "unit": {
            "area_m2": "m^2",
            "power_required_w": "W",
            "efficiency": "dimensionless (fraction)",
            "inherent_degradation": "dimensionless (fraction)",
            "sun_hours_per_orbit": "dimensionless (fraction of orbit)",
        },
        "assumption": [
            f"Solar constant at 1 AU = {SOLAR_CONSTANT} W/m^2",
            f"Solar cell efficiency = {efficiency:.0%}",
            f"Inherent degradation factor = {inherent_degradation:.0%}",
            f"Sunlit fraction of orbit = {sun_hours_per_orbit:.0%}",
            "No seasonal or pointing loss considered",
            "Conceptual-level rough sizing estimate only",
        ],
    }


def battery_capacity(power_required_w: float,
                     eclipse_hours: float,
                     depth_of_discharge: float = 0.30,
                     bus_voltage_v: float = 28.0,
                     efficiency: float = 0.90) -> dict:
    """
    Estimate battery capacity required for eclipse operation.

    Parameters
    ----------
    power_required_w : float
        Average power required during eclipse in watts.
    eclipse_hours : float
        Duration of eclipse in hours.
    depth_of_discharge : float, optional
        Maximum depth of discharge for the battery (default 0.30 for Li-ion).
    bus_voltage_v : float, optional
        Spacecraft bus voltage in volts (default 28.0).
    efficiency : float, optional
        Battery round-trip efficiency (default 0.90).

    Returns
    -------
    dict
        A dictionary containing:
        - "capacity_ah": required battery capacity in ampere-hours
        - "capacity_wh": required battery capacity in watt-hours
        - "power_required_w": input power requirement
        - "eclipse_hours": eclipse duration
        - "depth_of_discharge": assumed DoD
        - "bus_voltage_v": bus voltage
        - "assumption": list of assumptions
        - "unit": unit specification

    Notes
    -----
    - Uses the formula: C_Wh = P_eclipse * T_eclipse / (DoD * eta)
      and C_Ah = C_Wh / V_bus
    - This is a conceptual-level rough sizing estimate.
    - Does not account for battery aging, temperature effects, or cell balancing.
    """
    if depth_of_discharge <= 0 or depth_of_discharge > 1:
        raise ValueError("Depth of discharge must be between 0 and 1")
    if efficiency <= 0 or efficiency > 1:
        raise ValueError("Efficiency must be between 0 and 1")

    # Energy required during eclipse (Wh)
    energy_eclipse_wh = power_required_w * eclipse_hours

    # Battery capacity accounting for DoD and efficiency
    capacity_wh = energy_eclipse_wh / (depth_of_discharge * efficiency)
    capacity_ah = capacity_wh / bus_voltage_v

    return {
        "capacity_ah": round(capacity_ah, 2),
        "capacity_wh": round(capacity_wh, 2),
        "energy_eclipse_wh": round(energy_eclipse_wh, 2),
        "power_required_w": power_required_w,
        "eclipse_hours": eclipse_hours,
        "depth_of_discharge": depth_of_discharge,
        "bus_voltage_v": bus_voltage_v,
        "efficiency": efficiency,
        "unit": {
            "capacity_ah": "Ah",
            "capacity_wh": "Wh",
            "energy_eclipse_wh": "Wh",
            "power_required_w": "W",
            "eclipse_hours": "hours",
            "depth_of_discharge": "dimensionless (fraction)",
            "bus_voltage_v": "V",
            "efficiency": "dimensionless (fraction)",
        },
        "assumption": [
            f"Depth of discharge = {depth_of_discharge:.0%} (typical for Li-ion)",
            f"Battery round-trip efficiency = {efficiency:.0%}",
            f"Bus voltage = {bus_voltage_v} V",
            "No battery aging or temperature effects considered",
            "Conceptual-level rough sizing estimate only",
        ],
    }