"""
Orbit period estimation for circular LEO orbit.

This module provides deterministic engineering calculations
for preliminary orbit analysis of low Earth orbit satellites.
"""

import math

# Earth gravitational constant (m^3/s^2)
MU_EARTH = 3.986004418e14

# Earth equatorial radius (m)
R_EARTH = 6.378137e6


def orbit_period(altitude_km: float) -> dict:
    """
    Estimate orbital period for a circular Earth orbit.

    Parameters
    ----------
    altitude_km : float
        Orbit altitude above Earth's equator in kilometers.

    Returns
    -------
    dict
        A dictionary containing:
        - "period_minutes": orbital period in minutes
        - "period_seconds": orbital period in seconds
        - "semi_major_axis_km": semi-major axis in kilometers
        - "altitude_km": input altitude in kilometers
        - "assumption": list of assumptions made
        - "unit": unit specification for each value

    Notes
    -----
    - Assumes circular orbit (eccentricity = 0).
    - Uses Kepler's third law: T = 2 * pi * sqrt(a^3 / mu).
    - Earth is approximated as a sphere with radius 6378.137 km.
    - This is a conceptual-level estimate, not a high-fidelity simulation.
    """
    # Convert altitude to meters
    altitude_m = altitude_km * 1000.0

    # Semi-major axis (for circular orbit, a = R + h)
    a_m = R_EARTH + altitude_m
    a_km = a_m / 1000.0

    # Orbital period from Kepler's third law
    T_s = 2.0 * math.pi * math.sqrt(a_m**3 / MU_EARTH)
    T_min = T_s / 60.0

    return {
        "period_minutes": round(T_min, 2),
        "period_seconds": round(T_s, 1),
        "semi_major_axis_km": round(a_km, 1),
        "altitude_km": altitude_km,
        "unit": {
            "period_minutes": "minutes",
            "period_seconds": "seconds",
            "semi_major_axis_km": "km",
            "altitude_km": "km",
        },
        "assumption": [
            "Circular orbit (eccentricity = 0)",
            "Earth modeled as sphere with R = 6378.137 km",
            "Two-body Keplerian motion, no perturbations",
            "Conceptual-level estimate only",
        ],
    }


def orbit_period_from_semi_major_axis(semi_major_axis_km: float) -> dict:
    """
    Estimate orbital period from semi-major axis.

    Parameters
    ----------
    semi_major_axis_km : float
        Orbit semi-major axis in kilometers.

    Returns
    -------
    dict
        A dictionary containing:
        - "period_minutes": orbital period in minutes
        - "period_seconds": orbital period in seconds
        - "semi_major_axis_km": input semi-major axis in kilometers
        - "unit": unit specification for each value

    Notes
    -----
    - Uses Kepler's third law: T = 2 * pi * sqrt(a^3 / mu).
    - The period depends on semi-major axis, not eccentricity, in the
      two-body Keplerian model.
    - This is a conceptual-level estimate, not a high-fidelity simulation.
    """
    a_m = float(semi_major_axis_km) * 1000.0
    T_s = 2.0 * math.pi * math.sqrt(a_m**3 / MU_EARTH)
    T_min = T_s / 60.0

    return {
        "period_minutes": round(T_min, 2),
        "period_seconds": round(T_s, 1),
        "semi_major_axis_km": round(float(semi_major_axis_km), 3),
        "unit": {
            "period_minutes": "minutes",
            "period_seconds": "seconds",
            "semi_major_axis_km": "km",
        },
        "assumption": [
            "Two-body Keplerian motion, no perturbations",
            "Earth gravitational parameter mu = 3.986004418e14 m^3/s^2",
            "Conceptual-level estimate only",
        ],
    }


def orbital_velocity(altitude_km: float) -> dict:
    """
    Estimate orbital velocity for a circular Earth orbit.

    Parameters
    ----------
    altitude_km : float
        Orbit altitude above Earth's equator in kilometers.

    Returns
    -------
    dict
        A dictionary containing orbital velocity in km/s and m/s.
    """
    altitude_m = altitude_km * 1000.0
    a_m = R_EARTH + altitude_m

    # v = sqrt(mu / r) for circular orbit
    v_m_s = math.sqrt(MU_EARTH / a_m)
    v_km_s = v_m_s / 1000.0

    return {
        "velocity_km_s": round(v_km_s, 3),
        "velocity_m_s": round(v_m_s, 1),
        "altitude_km": altitude_km,
        "unit": {
            "velocity_km_s": "km/s",
            "velocity_m_s": "m/s",
            "altitude_km": "km",
        },
        "assumption": [
            "Circular orbit (eccentricity = 0)",
            "Two-body Keplerian motion, no perturbations",
            "Conceptual-level estimate only",
        ],
    }
